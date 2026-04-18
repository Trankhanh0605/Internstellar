from parser import p_term
from interpreter import interpret
from printer import pp_term

def run(inp: str) -> tuple[str, int]:
    ast = p_term(inp)
    result, steps = interpret(True, ast)
    return pp_term(result), steps

def test(name: str, inp: str, expected: str):
    got, steps = run(inp)
    status = "✅ PASS" if got == expected else "❌ FAIL"
    print(f"{status} | {name}")
    if got != expected:
        print(f"       expected: {expected}")
        print(f"       got:      {got}")
    else:
        print(f"       steps: {steps}")

# Booleans
test("true",  "T", "T")
test("false", "F", "F")

# Integers
test("integer 1337", "I/6", "I/6")

# String
test("hello world", "SB%,,/}Q/2,$", "SB%,,/}Q/2,$")

# Unary ops
test("negate",   "U- I$", "U- I$")   # -3 re-encodes as U- I$
test("bool not", "U! T",  "F")

# Binary ops
test("addition",      "B+ I# I$",  "I&")    # 2+3=5
test("string concat", "B. S4% S34", "S4%34")

# Conditional
test("if true",   "? T I! I\"",        "I!")    # picks true branch
test("if false",  "? B> I# I$ S9%3 S./", "S./") # 2>3 is false → "no"

# Function application
test("lambda app", "B$ B$ L# L$ v# B. SB%,,/ S}Q/2,$ IK", "SB%,,/}Q/2,$")

# Big recursion test from spec section 3.10 — expects 16 (= I1), 109 steps
big = "B$ B$ L\" B$ L# B$ v\" B$ v# v# L# B$ v\" B$ v# v# L\" L# ? B= v# I! I\" B$ L$ B+ B$ v\" v$ B$ v\" v$ B- v# I\" I%"
test("fibonacci-like (expect 16, 109 steps)", big, "I1")
