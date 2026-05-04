"""
GUARD → FLUX-C Compiler (guard2mask)

Compiles GUARD constraint specifications into FLUX-C bytecode.
GUARD is a declarative constraint language; FLUX-C is a stack-based bytecode VM.

Bytecode opcodes:
  0x1A  HALT       — stop execution
  0x1B  EVAL       — evaluate and push result
  0x1D  RANGE      — range check (lo, hi follow as immediates)
  0x26  BOOL_AND   — pop two bools, push AND
  0x27  BOOL_OR    — pop two bools, push OR
  0x28  BOOL_NOT   — pop bool, push NOT
"""

import re
from dataclasses import dataclass
from typing import Union

# ── Opcodes ──────────────────────────────────────────────────────────────────

OP_RANGE   = 0x1D
OP_EVAL    = 0x1B
OP_HALT    = 0x1A
OP_AND     = 0x26
OP_OR      = 0x27
OP_NOT     = 0x28

# ── AST nodes ────────────────────────────────────────────────────────────────

@dataclass
class RangeCheck:
    var: str
    lo: float
    hi: float

@dataclass
class BoolBinOp:
    op: str          # "and" | "or"
    left: object
    right: object

@dataclass
class BoolNot:
    operand: object

@dataclass
class LetExpr:
    name: str
    value: float
    body: object

@dataclass
class Constraint:
    name: str
    priority: str
    body: object

# ── Tokenizer ────────────────────────────────────────────────────────────────

TOKEN_RE = re.compile(r"""
    \s*(?:
        (constraint|with|priority|let|in|and|or|not)   # keywords
        |([A-Za-z_]\w*)                                # identifiers
        |([0-9]+(?:\.[0-9]*)?)                         # numbers
        |([\[\]{},])                                   # punctuation
        |(//[^\n]*)                                     # line comment
    )
""", re.VERBOSE)

KEYWORDS = {"constraint", "with", "priority", "let", "in", "and", "or", "not"}

def tokenize(source: str) -> list[tuple]:
    """Return list of (type, value) tokens."""
    tokens = []
    for m in TOKEN_RE.finditer(source):
        if m.group(5):        # comment — skip
            continue
        if m.group(1):        # keyword
            tokens.append(("KW", m.group(1)))
        elif m.group(2):      # identifier
            tokens.append(("ID", m.group(2)))
        elif m.group(3):      # number
            tokens.append(("NUM", float(m.group(3))))
        elif m.group(4):      # punctuation
            tokens.append(("PUNCT", m.group(4)))
    return tokens

# ── Parser (recursive descent) ───────────────────────────────────────────────

class Parser:
    def __init__(self, tokens: list[tuple]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> tuple | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self) -> tuple:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, ttype: str, value=None) -> tuple:
        tok = self.advance()
        if tok[0] != ttype or (value is not None and tok[1] != value):
            raise SyntaxError(f"Expected ({ttype}, {value!r}), got {tok}")
        return tok

    # ── Top-level: one or more constraints ───────────────────────────────

    def parse_all(self) -> list[Constraint]:
        constraints = [self.parse_constraint()]
        while self.peek() is not None:
            constraints.append(self.parse_constraint())
        return constraints

    def parse_constraint(self) -> Constraint:
        self.expect("KW", "constraint")
        _, name = self.expect("ID")
        self.expect("KW", "with")
        self.expect("KW", "priority")
        _, prio = self.advance()  # could be ID or KW like "HIGH"
        self.expect("PUNCT", "{")
        body = self.parse_expr()
        self.expect("PUNCT", "}")
        return Constraint(name, str(prio), body)

    # ── Expression grammar ───────────────────────────────────────────────

    def parse_expr(self) -> object:
        """expr = or_expr"""
        return self.parse_or()

    def parse_or(self) -> object:
        left = self.parse_and()
        while self.peek() == ("KW", "or"):
            self.advance()
            left = BoolBinOp("or", left, self.parse_and())
        return left

    def parse_and(self) -> object:
        left = self.parse_not()
        while self.peek() == ("KW", "and"):
            self.advance()
            left = BoolBinOp("and", left, self.parse_not())
        return left

    def parse_not(self) -> object:
        if self.peek() == ("KW", "not"):
            self.advance()
            return BoolNot(self.parse_not())
        return self.parse_atom()

    def parse_atom(self) -> object:
        # let binding
        if self.peek() == ("KW", "let"):
            return self.parse_let()
        # range check: <var> in [<lo>, <hi>]
        _, var = self.expect("ID")
        self.expect("KW", "in")
        self.expect("PUNCT", "[")
        _, lo = self.expect("NUM")
        self.expect("PUNCT", ",")
        _, hi = self.expect("NUM")
        self.expect("PUNCT", "]")
        return RangeCheck(var, lo, hi)

    def parse_let(self) -> LetExpr:
        self.expect("KW", "let")
        _, name = self.expect("ID")
        self.expect("PUNCT", ",")   # simplified: expect comma before value
        _, val = self.expect("NUM")
        self.expect("KW", "in")
        body = self.parse_expr()
        return LetExpr(name, val, body)


# ── Code generator ───────────────────────────────────────────────────────────

def codegen(node) -> list[int]:
    """Recursively emit FLUX-C bytecode for an AST node."""
    if isinstance(node, RangeCheck):
        return [OP_RANGE, _f2b(node.lo), _f2b(node.hi), OP_EVAL, OP_HALT]

    if isinstance(node, BoolBinOp):
        left_bc  = codegen(node.left)
        right_bc = codegen(node.right)
        op = OP_AND if node.op == "and" else OP_OR
        # strip trailing HALT from sub-expressions, combine, append single HALT
        return left_bc[:-1] + right_bc[:-1] + [op, OP_HALT]

    if isinstance(node, BoolNot):
        inner = codegen(node.operand)
        return inner[:-1] + [OP_NOT, OP_HALT]

    if isinstance(node, LetExpr):
        # let bindings are inline constants; just compile the body
        return codegen(node.body)

    if isinstance(node, Constraint):
        return codegen(node.body)

    raise TypeError(f"Unknown AST node: {type(node)}")


def _f2b(v: float) -> int:
    """Encode a small integer float as a single byte (0–255)."""
    iv = int(v)
    if iv != v or not (0 <= iv <= 255):
        raise ValueError(f"Immediate value {v} out of byte range")
    return iv


# ── Compiler facade ──────────────────────────────────────────────────────────

_OPCODE_NAMES = {
    OP_RANGE: "RANGE", OP_EVAL: "EVAL", OP_HALT: "HALT",
    OP_AND: "BOOL_AND", OP_OR: "BOOL_OR", OP_NOT: "BOOL_NOT",
}

class GuardCompiler:
    """GUARD → FLUX-C bytecode compiler."""

    def compile(self, source: str) -> list[int]:
        """Compile GUARD source to a flat bytecode list."""
        tokens = tokenize(source)
        parser = Parser(tokens)
        constraints = parser.parse_all()
        # concatenate bytecode for all constraints
        bc: list[int] = []
        for c in constraints:
            bc.extend(codegen(c))
        return bc

    def compile_file(self, path: str) -> list[int]:
        """Read a .guard file and compile it."""
        with open(path) as f:
            return self.compile(f.read())

    def disassemble(self, bytecode: list[int]) -> str:
        """Produce human-readable disassembly of bytecode."""
        lines: list[str] = []
        i = 0
        while i < len(bytecode):
            op = bytecode[i]
            name = _OPCODE_NAMES.get(op, f"0x{op:02X}")
            if op == OP_RANGE:
                lo = bytecode[i + 1]
                hi = bytecode[i + 2]
                lines.append(f"{i:04d}  RANGE  {lo}, {hi}")
                i += 3
            else:
                lines.append(f"{i:04d}  {name}")
                i += 1
        return "\n".join(lines)


# ── Built-in tests ───────────────────────────────────────────────────────────

def _run_tests():
    c = GuardCompiler()

    # Test 1: simple range
    bc = c.compile("constraint c1 with priority HIGH { x in [0, 100] }")
    assert bc == [OP_RANGE, 0, 100, OP_EVAL, OP_HALT], f"T1 failed: {bc}"

    # Test 2: AND of two ranges
    bc = c.compile("constraint c2 with priority MED { x in [0, 50] and y in [10, 90] }")
    expected = [OP_RANGE, 0, 50, OP_EVAL, OP_RANGE, 10, 90, OP_EVAL, OP_AND, OP_HALT]
    assert bc == expected, f"T2 failed: {bc}"

    # Test 3: OR of two ranges
    bc = c.compile("constraint c3 with priority LOW { x in [0, 10] or x in [90, 100] }")
    expected = [OP_RANGE, 0, 10, OP_EVAL, OP_RANGE, 90, 100, OP_EVAL, OP_OR, OP_HALT]
    assert bc == expected, f"T3 failed: {bc}"

    # Test 4: NOT a range
    bc = c.compile("constraint c4 with priority HIGH { not x in [40, 60] }")
    assert bc == [OP_RANGE, 40, 60, OP_EVAL, OP_NOT, OP_HALT], f"T4 failed: {bc}"

    # Test 5: mixed AND / OR / NOT
    src = "constraint c5 with priority HIGH { x in [0, 50] and not y in [10, 20] or z in [5, 15] }"
    bc = c.compile(src)
    expected = [
        OP_RANGE, 0, 50, OP_EVAL,           # x in [0,50]
        OP_RANGE, 10, 20, OP_EVAL, OP_NOT,  # not y in [10,20]
        OP_AND,                              # AND
        OP_RANGE, 5, 15, OP_EVAL,           # z in [5,15]
        OP_OR, OP_HALT,
    ]
    assert bc == expected, f"T5 failed: {bc}"

    print("All 5 tests passed ✓")
    # Show disassembly of test 5
    print("\nDisassembly of T5:")
    print(c.disassemble(bc))


if __name__ == "__main__":
    _run_tests()
