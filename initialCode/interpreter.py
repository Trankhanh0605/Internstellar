from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import TBinOp, TBool, TIf, TInt, TLam, TString, TUnOp, TVar, Term, CHARS, CHARS_DECODED
from printer import encode_string, to_base94


MAX_STEPS = 10_000_000


class InterpreterError(Exception):
    pass


class BetaReductionLimit(InterpreterError):
    pass


class ScopeError(InterpreterError):
    pass


class TypeError_(InterpreterError):
    pass


class ArithmeticError_(InterpreterError):
    pass


class UnknownUnOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown unary operator: {op}")
        self.op = op


class UnknownBinOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown binary operator: {op}")
        self.op = op


@dataclass
class VInt:
    value: int


@dataclass
class VBool:
    value: bool


@dataclass
class VString:
    value: str


@dataclass
class VClosure:
    var: int
    body: Term
    env: dict[int, "Thunk"]


Value = VInt | VBool | VString | VClosure


@dataclass
class Thunk:
    kind: str
    value: Value | None = None
    steps: int = 0
    term: Term | None = None
    env: dict[int, "Thunk"] | None = None

def eval_unop(op: str, val: Value) -> Value: 
    if op=='-': 
        if not isinstance(val, VInt): 
            raise TypeError_("- expectes integer")
        return VInt(-val.value)
    
    elif op=='!': 
        if not isinstance(val, VBool):
            raise TypeError_("! expects boolean")
        return VBool(not val.value)
    
    elif op=='#': # String to integer
        if not isinstance(val, VString): 
            raise TypeError_("# expects string")
        res=0
        for ch in val.value: 
            if ch not in CHARS_DECODED: 
                raise ValueError(f"Invalid character in string: {ch!r}")
            digit=CHARS_DECODED.index(ch)
            res=res*94+digit
        return VInt(res)
    
    elif op=='$': # Integer to String
        if not isinstance(val, VInt): 
            raise TypeError_("$ expects integer")
        
        if val.value<0: 
            raise ValueError("Cannot convert negative integer to string")
        
        b94=to_base94(val.value)
        res=""
        for ch in b94: 
            # ch is in CHARS, find its index, map to CHARS_DECODED
            digit=CHARS.index(ch)
            res+=CHARS_DECODED[digit]
            
        return VString(res)
    
def eval_binop(op: str, left: Value, right: Value) -> Value: 
    if op == '+':
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"+ expects integers")
        return VInt(left.value + right.value)

    elif op == '-':
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"- expects integers")
        return VInt(left.value - right.value)

    elif op == '*':
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"* expects integers")
        return VInt(left.value * right.value)
    
    elif op=='/': 
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"/ expects integers")
        if right.value==0: 
            raise ArithmeticError_("Division by zero")
        res=int(left.value / right.value)
        return VInt(res)
    
    elif op == '%': 
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"% expects integers")
        if right.value == 0:
            raise ArithmeticError_("Modulo by zero")
        a,b = left.value, right.value
        res=a-int(a/b) * b
        return VInt(res)
    
    elif op == '<':
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"< expects integers")
        return VBool(left.value < right.value)

    elif op == '>':
        if not isinstance(left, VInt) or not isinstance(right, VInt):
            raise TypeError_(f"> expects integers")
        return VBool(left.value > right.value)

    elif op == '=':
        # Can compare same types (ints with ints, bools with bools)
        if isinstance(left, VInt) and isinstance(right, VInt):
            return VBool(left.value == right.value)
        elif isinstance(left, VBool) and isinstance(right, VBool):
            return VBool(left.value == right.value)
        else:
            raise TypeError_(f"= cannot compare different types")
        
    elif op == '|':
        if not isinstance(left, VBool) or not isinstance(right, VBool):
            raise TypeError_(f"| expects booleans")
        return VBool(left.value or right.value)

    elif op == '&':
        if not isinstance(left, VBool) or not isinstance(right, VBool):
            raise TypeError_(f"& expects booleans")
        return VBool(left.value and right.value)
    
    elif op == '.':
        if not isinstance(left, VString) or not isinstance(right, VString):
            raise TypeError_(f". expects strings")
        return VString(left.value + right.value)
    
    elif op == 'T':  # Take first N characters
        if not isinstance(left, VInt) or not isinstance(right, VString):
            raise TypeError_(f"T expects integer and string")
        n = left.value
        if n < 0:
            n = 0
        return VString(right.value[:n])

    elif op == 'D':  # Drop first N characters
        if not isinstance(left, VInt) or not isinstance(right, VString):
            raise TypeError_(f"D expects integer and string")
        n = left.value
        if n < 0:
            n = 0
        return VString(right.value[n:])
    
    else: 
        raise UnknownBinOp(op)

def _to_term(v: Value) -> Term:
    if isinstance(v, VInt):
        return TInt(v.value)
    if isinstance(v, VBool):
        return TBool(v.value)
    if isinstance(v, VString):
        return TString(v.value)
    if isinstance(v, VClosure):
        return TLam(v.var, v.body)
    raise TypeError(f"Unknown value type: {type(v).__name__}")


def interpret(check_max: bool, term: Term) -> tuple[Term, int]:
    steps = 0
    
    def eval_term(t: Term, env: dict[int, Thunk]) -> Value:
        
        nonlocal steps
        
        if isinstance(t, TInt): 
            return VInt(t.value)
        
        elif isinstance(t, TString): 
            return VString(t.value)
        
        elif isinstance(t, TBool): 
            return VBool(t.value)
        
        elif isinstance(t, TVar):
            # Look up variable in environment
            if t.value not in env:
                raise ScopeError(f"Undefined variable: {t.value}")
            thunk = env[t.value]
            # If the thunk is already evaluated, return the value
            if thunk.kind == "value":
                return thunk.value
            # Otherwise, evaluate the term
            else:
                value = eval_term(thunk.term, thunk.env)
                return value
        
        elif isinstance(t, TLam):
            # Create a closure (capture the environment)
            return VClosure(t.var, t.body, env)
        
        elif isinstance(t, TUnOp):
            # Evaluate the operand, then apply the operator
            operand_value = eval_term(t.term, env)
            return eval_unop(t.op, operand_value)
        
        elif isinstance(t, TBinOp):
            if t.op=='$': 
                func=eval_term(t.left, env)
                if not isinstance(func, VClosure):
                    raise TypeError_("$ expects a function on the left side")
                
                steps+=1
                if check_max and steps>MAX_STEPS: 
                    raise BetaReductionLimit("Exceeded maximum beta reductions")
                
                # Wrap the argument as an unevaluated thunk (call-by-name)
                arg_thunk=Thunk(kind="thunk", term=t.right, env=env)
                
                # New environment: closure's captured env + the new argument binding
                new_env = {**func.env, func.var: arg_thunk}
                
                # Evaluate the function body in the new environment
                return eval_term(func.body, new_env)
    
            else:
                # All other binary ops — evaluate both sides eagerly
                left_value = eval_term(t.left, env)
                right_value = eval_term(t.right, env)
                return eval_binop(t.op, left_value, right_value)
        
        elif isinstance(t, TIf):
            # Evaluate condition (lazy for branches)
            cond_value = eval_term(t.cond, env)
            if not isinstance(cond_value, VBool):
                raise TypeError_("If condition must be boolean")
            # Only evaluate the appropriate branch
            if cond_value.value:
                return eval_term(t.true_branch, env)
            else:
                return eval_term(t.false_branch, env)
        
        else:
            raise TypeError(f"Unknown term type: {type(t).__name__}")

    result = eval_term(term, {})
    return _to_term(result), steps