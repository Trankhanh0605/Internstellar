from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import (
    CHARS,
    CHARS_DECODED,
    TBinOp,
    TBool,
    TIf,
    TInt,
    TLam,
    TString,
    TUnOp,
    TVar,
    Term,
)


@dataclass(frozen=True)
class ParseError(Exception):
    kind: str
    index: int | None = None
    ch: str | None = None

    def __str__(self) -> str:
        if self.kind == "UnexpectedChar":
            return f"UnexpectedChar({self.ch!r}, {self.index})"
        if self.kind == "UnusedInput":
            return f"UnusedInput({self.index})"
        return "UnexpectedEOF"

def decode_base94(body: str) -> int: 
    res=0
    for ch in body: 
        digit=CHARS.index(ch)
        res=res*94+digit
    return res

def decode_string(body: str) -> str: 
    res=""
    for ch in body: 
        res+=CHARS_DECODED[CHARS.index(ch)]
    return res

def p_term(inp: str) -> Term:
    # TODO
    tokens = inp.split()  # Split into tokens by whitespace
    if not tokens: 
        raise ParseError("UnexpectedEOF")

    term, pos=_parse_term(tokens,0)
    if pos<len(tokens): 
        raise ParseError("UnusedInput", pos) # Use token position, not character index
    return term
    
# Tokenize ONCE at the top

# Then index into the token list, not the character string
def _parse_term(tokens: list[str], pos: int) -> tuple[Term, int]:
    # Parse a term from the token list starting at position pos
    # Return (parsed_term, next_position)
    
    if pos>=len(tokens): 
        raise ParseError("UnexpectedEOF")

    token=tokens[pos]
    
    if not tokens: 
        raise ParseError("UnexpectedEOF")
    
    indicator=token[0]
    body=token[1:]
    
    if indicator=="I": 
        if not body: 
            raise ParseError("UnexpectedEOF")
        value=decode_base94(body)
        return TInt(value), pos+1 # Move to next token
    
    elif indicator=="S": 
        value=decode_string(body)
        return TString(value), pos+1

    elif indicator == 'T':
        return TBool(True), pos + 1

    elif indicator == 'F':
        return TBool(False), pos + 1