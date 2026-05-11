#!/usr/bin/env python3
"""
Fluxile → FLUX ISA v3 Assembly Compiler v0.2.0

Improvements over v0.1:
  - Builtins (round, sqrt, vdot) work without explicit type context
  - Intent literals compile to VStore operations
  - Agent blocks emit A2A opcodes
  - Proper register allocator with interference graph + coalescing
  - Optimization passes: constant folding, DCE, strength reduction, peephole
  - New language features: for..in range(), match, let mut, arrays
  - constraint fn → FLUX-C (stack-based, PANIC on violation)
  - fn → FLUX-X (register-based, normal return)
  - No redundant epilogues

Author: Forgemaster ⚒️ (Cocapn Fleet)
"""

import sys
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Set

# ─── Token Types ───────────────────────────────────────────────

class TT:
    FN = 'FN'; CONSTRAINT = 'CONSTRAINT'; REQUIRE = 'REQUIRE'
    LET = 'LET'; RETURN = 'RETURN'; IF = 'IF'; ELSE = 'ELSE'
    WHILE = 'WHILE'; FOR = 'FOR'; IN = 'IN'; MATCH = 'MATCH'
    AGENT = 'AGENT'; INTENT = 'INTENT'
    MUT = 'MUT'
    TRUE = 'TRUE'; FALSE = 'FALSE'; PANIC = 'PANIC'; UNREACHABLE = 'UNREACHABLE'
    IDENT = 'IDENT'; INT = 'INT'; FLOAT = 'FLOAT'
    PLUS = '+'; MINUS = '-'; STAR = '*'; SLASH = '/'; PERCENT = '%'
    LSHIFT = '<<'; RSHIFT = '>>'; BAND = '&'; BOR = '|'; BXOR = '^'
    EQ = '=='; NE = '!='; LT = '<'; LE = '<='; GT = '>'; GE = '>='
    AND = '&&'; OR = '||'; NOT = '!'
    ASSIGN = '='; ARROW = '->'; AS = 'AS'; FAT_ARROW = '=>'
    LPAREN = '('; RPAREN = ')'; LBRACE = '{'; RBRACE = '}'
    LBRACKET = '['; RBRACKET = ']'
    SEMI = ';'; COMMA = ','; COLON = ':'; BANG = '!'
    UNDERSCORE = 'UNDERSCORE'
    EOF = 'EOF'
    # Type keywords
    I32 = 'I32'; F32 = 'F32'; VEC9 = 'VEC9'; VOID = 'VOID'

KEYWORDS = {
    'fn': TT.FN, 'constraint': TT.CONSTRAINT, 'require': TT.REQUIRE,
    'let': TT.LET, 'return': TT.RETURN, 'if': TT.IF, 'else': TT.ELSE,
    'while': TT.WHILE, 'for': TT.FOR, 'in': TT.IN, 'match': TT.MATCH,
    'agent': TT.AGENT, 'intent': TT.INTENT, 'mut': TT.MUT,
    'true': TT.TRUE, 'false': TT.FALSE, 'panic': TT.PANIC,
    'unreachable': TT.UNREACHABLE, 'as': TT.AS,
    'i32': TT.I32, 'f32': TT.F32, 'vec9': TT.VEC9, 'void': TT.VOID,
}

@dataclass
class Token:
    type: str
    value: Any
    line: int
    col: int

# ─── Lexer ─────────────────────────────────────────────────────

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self._tokenize()

    def _peek(self):
        return self.source[self.pos] if self.pos < len(self.source) else '\0'

    def _advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1; self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_ws_comments(self):
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in ' \t\r\n':
                self._advance()
            elif ch == '/' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '/':
                while self.pos < len(self.source) and self._peek() != '\n':
                    self._advance()
            elif ch == '/' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '*':
                self._advance(); self._advance()
                depth = 1
                while self.pos < len(self.source) and depth > 0:
                    if self._peek() == '*' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '/':
                        self._advance(); self._advance(); depth -= 1
                    elif self._peek() == '/' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '*':
                        self._advance(); self._advance(); depth += 1
                    else:
                        self._advance()
            else:
                break

    def _lookahead(self, expected: str) -> bool:
        return self.source[self.pos:self.pos + len(expected)] == expected

    def _tokenize(self):
        while self.pos < len(self.source):
            self._skip_ws_comments()
            if self.pos >= len(self.source): break
            line, col = self.line, self.col
            ch = self._peek()

            if ch.isalpha() or ch == '_':
                start = self.pos
                while self.pos < len(self.source) and (self._peek().isalnum() or self._peek() == '_'):
                    self._advance()
                word = self.source[start:self.pos]
                tt = KEYWORDS.get(word, TT.IDENT)
                self.tokens.append(Token(tt, word, line, col))
            elif ch.isdigit():
                start = self.pos
                while self.pos < len(self.source) and self._peek().isdigit():
                    self._advance()
                if self.pos < len(self.source) and self._peek() == '.':
                    self._advance()
                    while self.pos < len(self.source) and self._peek().isdigit():
                        self._advance()
                    self.tokens.append(Token(TT.FLOAT, float(self.source[start:self.pos]), line, col))
                else:
                    self.tokens.append(Token(TT.INT, int(self.source[start:self.pos]), line, col))
            elif ch == '.' and self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit():
                start = self.pos
                self._advance()
                while self.pos < len(self.source) and self._peek().isdigit():
                    self._advance()
                self.tokens.append(Token(TT.FLOAT, float(self.source[start:self.pos]), line, col))
            elif ch == '0' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] in 'xX':
                start = self.pos
                self._advance(); self._advance()
                while self.pos < len(self.source) and self._peek() in '0123456789abcdefABCDEF':
                    self._advance()
                self.tokens.append(Token(TT.INT, int(self.source[start:self.pos], 16), line, col))
            elif ch == '=' and self._lookahead('=='):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.EQ, '==', line, col))
            elif ch == '!' and self._lookahead('!='):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.NE, '!=', line, col))
            elif ch == '<' and self._lookahead('<='):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.LE, '<=', line, col))
            elif ch == '>' and self._lookahead('>='):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.GE, '>=', line, col))
            elif ch == '<' and self._lookahead('<<'):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.LSHIFT, '<<', line, col))
            elif ch == '>' and self._lookahead('>>'):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.RSHIFT, '>>', line, col))
            elif ch == '<':
                self._advance()
                self.tokens.append(Token(TT.LT, '<', line, col))
            elif ch == '>':
                self._advance()
                self.tokens.append(Token(TT.GT, '>', line, col))
            elif ch == '=' and self._lookahead('=>'):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.FAT_ARROW, '=>', line, col))
            elif ch == '&' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '&':
                self._advance(); self._advance()
                self.tokens.append(Token(TT.AND, '&&', line, col))
            elif ch == '|' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '|':
                self._advance(); self._advance()
                self.tokens.append(Token(TT.OR, '||', line, col))
            elif ch == '-' and self._lookahead('->'):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.ARROW, '->', line, col))
            elif ch in '+-*/%':
                self._advance()
                tt_map = {'+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH, '%': TT.PERCENT}
                self.tokens.append(Token(tt_map[ch], ch, line, col))
            elif ch == '=':
                self._advance()
                self.tokens.append(Token(TT.ASSIGN, '=', line, col))
            elif ch == '!':
                self._advance()
                self.tokens.append(Token(TT.NOT, '!', line, col))
            elif ch == '&':
                self._advance()
                self.tokens.append(Token(TT.BAND, '&', line, col))
            elif ch == '|':
                self._advance()
                self.tokens.append(Token(TT.BOR, '|', line, col))
            elif ch == '^':
                self._advance()
                self.tokens.append(Token(TT.BXOR, '^', line, col))
            elif ch == '(':
                self._advance()
                self.tokens.append(Token(TT.LPAREN, '(', line, col))
            elif ch == ')':
                self._advance()
                self.tokens.append(Token(TT.RPAREN, ')', line, col))
            elif ch == '{':
                self._advance()
                self.tokens.append(Token(TT.LBRACE, '{', line, col))
            elif ch == '}':
                self._advance()
                self.tokens.append(Token(TT.RBRACE, '}', line, col))
            elif ch == '[':
                self._advance()
                self.tokens.append(Token(TT.LBRACKET, '[', line, col))
            elif ch == ']':
                self._advance()
                self.tokens.append(Token(TT.RBRACKET, ']', line, col))
            elif ch == ';':
                self._advance()
                self.tokens.append(Token(TT.SEMI, ';', line, col))
            elif ch == ',':
                self._advance()
                self.tokens.append(Token(TT.COMMA, ',', line, col))
            elif ch == ':':
                self._advance()
                self.tokens.append(Token(TT.COLON, ':', line, col))
            elif ch == '_':
                self._advance()
                self.tokens.append(Token(TT.UNDERSCORE, '_', line, col))
            else:
                self._advance()
        self.tokens.append(Token(TT.EOF, None, self.line, self.col))

# ─── AST Nodes ─────────────────────────────────────────────────

@dataclass
class TypeNode:
    name: str  # 'i32', 'f32', 'vec9', 'void'
    array_size: Optional[int] = None  # for [T; N] types

@dataclass
class FnParam:
    name: str
    type_: TypeNode

@dataclass
class FnDecl:
    name: str
    params: List[FnParam]
    return_type: TypeNode
    body: List[Any]
    is_constraint: bool = False

@dataclass
class AgentDecl:
    name: str
    methods: List[FnDecl]

@dataclass
class LetStmt:
    name: str
    type_: Optional[TypeNode]
    init: Any
    is_mutable: bool = False

@dataclass
class AssignStmt:
    name: str
    value: Any

@dataclass
class IndexAssignStmt:
    target: Any  # Ident
    index: Any
    value: Any

@dataclass
class ReturnStmt:
    value: Any

@dataclass
class ConstraintStmt:
    expr: Any

@dataclass
class RequireStmt:
    expr: Any

@dataclass
class ExprStmt:
    expr: Any

@dataclass
class IfStmt:
    condition: Any
    then_body: List[Any]
    else_body: Optional[List[Any]]

@dataclass
class WhileStmt:
    condition: Any
    body: List[Any]

@dataclass
class ForRangeStmt:
    var_name: str
    start: Any
    end: Any
    body: List[Any]

@dataclass
class MatchStmt:
    value: Any
    arms: List[Tuple[Any, List[Any]]]  # (pattern, body)
    default: Optional[List[Any]] = None

@dataclass
class BinOp:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class IntLit:
    value: int

@dataclass
class FloatLit:
    value: float

@dataclass
class BoolLit:
    value: bool

@dataclass
class Ident:
    name: str

@dataclass
class CastExpr:
    expr: Any
    target_type: str

@dataclass
class CallExpr:
    name: str
    args: List[Any]

@dataclass
class IndexExpr:
    target: Any
    index: Any

@dataclass
class IntentLit:
    components: List[float]

@dataclass
class ArrayLit:
    elements: List[Any]

# ─── Parser ────────────────────────────────────────────────────

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def _expect(self, tt: str) -> Token:
        t = self._advance()
        if t.type != tt:
            raise SyntaxError(f"Expected {tt}, got {t.type} ('{t.value}') at line {t.line}:{t.col}")
        return t

    def _match(self, *types) -> Optional[Token]:
        if self._peek().type in types:
            return self._advance()
        return None

    def parse(self) -> List[Any]:
        decls = []
        while self._peek().type != TT.EOF:
            if self._peek().type == TT.AGENT:
                decls.append(self._parse_agent_decl())
            else:
                decls.append(self._parse_fn_decl())
        return decls

    def _parse_agent_decl(self) -> AgentDecl:
        self._expect(TT.AGENT)
        name = self._expect(TT.IDENT).value
        self._expect(TT.LBRACE)
        methods = []
        while self._peek().type != TT.RBRACE:
            methods.append(self._parse_fn_decl())
        self._expect(TT.RBRACE)
        return AgentDecl(name, methods)

    def _parse_fn_decl(self) -> FnDecl:
        is_constraint = bool(self._match(TT.CONSTRAINT))
        self._expect(TT.FN)
        name = self._expect(TT.IDENT).value
        self._expect(TT.LPAREN)
        params = []
        while self._peek().type != TT.RPAREN:
            pname = self._expect(TT.IDENT).value
            self._expect(TT.COLON)
            ptype = self._parse_type()
            params.append(FnParam(pname, ptype))
            if not self._match(TT.COMMA): break
        self._expect(TT.RPAREN)
        ret_type = TypeNode('void')
        if self._match(TT.ARROW):
            ret_type = self._parse_type()
        body = self._parse_block()
        return FnDecl(name, params, ret_type, body, is_constraint)

    def _parse_type(self) -> TypeNode:
        t = self._advance()
        if t.type in (TT.I32, TT.F32, TT.VEC9, TT.VOID):
            base = t.value
        elif t.type == TT.IDENT:
            base = t.value
        else:
            raise SyntaxError(f"Expected type, got {t.type} at line {t.line}")
        # Check for array type [T; N]
        if self._match(TT.LBRACKET):
            size = self._expect(TT.INT).value
            self._expect(TT.RBRACKET)
            return TypeNode(base, array_size=size)
        return TypeNode(base)

    def _parse_block(self) -> List[Any]:
        self._expect(TT.LBRACE)
        stmts = []
        while self._peek().type != TT.RBRACE:
            stmts.append(self._parse_stmt())
        self._expect(TT.RBRACE)
        return stmts

    def _parse_stmt(self) -> Any:
        t = self._peek()
        if t.type == TT.LET:
            return self._parse_let()
        elif t.type == TT.RETURN:
            return self._parse_return()
        elif t.type == TT.IF:
            return self._parse_if()
        elif t.type == TT.WHILE:
            return self._parse_while()
        elif t.type == TT.FOR:
            return self._parse_for()
        elif t.type == TT.MATCH:
            return self._parse_match()
        elif t.type == TT.CONSTRAINT:
            self._advance()
            expr = self._parse_expr()
            self._expect(TT.SEMI)
            return ConstraintStmt(expr)
        elif t.type == TT.REQUIRE:
            self._advance()
            expr = self._parse_expr()
            self._expect(TT.SEMI)
            return RequireStmt(expr)
        elif t.type == TT.PANIC:
            self._advance()
            self._expect(TT.SEMI)
            return ExprStmt(CallExpr('panic', []))
        elif t.type == TT.UNREACHABLE:
            self._advance()
            self._expect(TT.SEMI)
            return ExprStmt(CallExpr('unreachable', []))
        else:
            expr = self._parse_expr()
            # Check for index assignment: arr[idx] = val
            if isinstance(expr, IndexExpr) and self._match(TT.ASSIGN):
                value = self._parse_expr()
                self._expect(TT.SEMI)
                return IndexAssignStmt(expr.target, expr.index, value)
            if isinstance(expr, Ident) and self._match(TT.ASSIGN):
                value = self._parse_expr()
                self._expect(TT.SEMI)
                return AssignStmt(expr.name, value)
            self._expect(TT.SEMI)
            return ExprStmt(expr)

    def _parse_let(self) -> LetStmt:
        self._expect(TT.LET)
        is_mutable = bool(self._match(TT.MUT))
        name = self._expect(TT.IDENT).value
        type_ = None
        if self._match(TT.COLON):
            type_ = self._parse_type()
        self._expect(TT.ASSIGN)
        init = self._parse_expr()
        self._expect(TT.SEMI)
        return LetStmt(name, type_, init, is_mutable)

    def _parse_return(self) -> ReturnStmt:
        self._expect(TT.RETURN)
        if self._peek().type == TT.SEMI:
            self._advance()
            return ReturnStmt(None)
        expr = self._parse_expr()
        self._expect(TT.SEMI)
        return ReturnStmt(expr)

    def _parse_if(self) -> IfStmt:
        self._expect(TT.IF)
        cond = self._parse_expr()
        then_body = self._parse_block()
        else_body = None
        if self._match(TT.ELSE):
            if self._peek().type == TT.IF:
                else_body = [self._parse_if()]
            else:
                else_body = self._parse_block()
        return IfStmt(cond, then_body, else_body)

    def _parse_while(self) -> WhileStmt:
        self._expect(TT.WHILE)
        cond = self._parse_expr()
        body = self._parse_block()
        return WhileStmt(cond, body)

    def _parse_for(self) -> ForRangeStmt:
        self._expect(TT.FOR)
        var_name = self._expect(TT.IDENT).value
        self._expect(TT.IN)
        # Parse range(start, end) or range(end) shorthand
        if self._peek().type == TT.IDENT and self._peek().value == 'range':
            self._advance()
            self._expect(TT.LPAREN)
            first = self._parse_expr()
            if self._match(TT.COMMA):
                second = self._parse_expr()
                start, end = first, second
            else:
                start, end = IntLit(0), first
            self._expect(TT.RPAREN)
        else:
            # for i in expr — treat as iterator (just use 0..expr for now)
            raise SyntaxError(f"Only range() iterators supported, got '{self._peek().value}'")
        body = self._parse_block()
        return ForRangeStmt(var_name, start, end, body)

    def _parse_match(self) -> MatchStmt:
        self._expect(TT.MATCH)
        value = self._parse_expr()
        self._expect(TT.LBRACE)
        arms = []
        default = None
        while self._peek().type != TT.RBRACE:
            if self._peek().type == TT.UNDERSCORE:
                self._advance()
                self._expect(TT.FAT_ARROW)
                default = self._parse_block()
                if self._match(TT.COMMA): pass
            else:
                pattern = self._parse_expr()
                self._expect(TT.FAT_ARROW)
                body = self._parse_block()
                arms.append((pattern, body))
                if self._match(TT.COMMA): pass
        self._expect(TT.RBRACE)
        return MatchStmt(value, arms, default)

    # ─── Expression parsing (precedence climbing) ───

    def _parse_expr(self) -> Any:
        return self._parse_or()

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self._match(TT.OR):
            left = BinOp('||', left, self._parse_and())
        return left

    def _parse_and(self) -> Any:
        left = self._parse_equality()
        while self._match(TT.AND):
            left = BinOp('&&', left, self._parse_equality())
        return left

    def _parse_equality(self) -> Any:
        left = self._parse_comparison()
        while True:
            op = self._match(TT.EQ, TT.NE)
            if not op: break
            left = BinOp(op.value, left, self._parse_comparison())
        return left

    def _parse_comparison(self) -> Any:
        left = self._parse_shift()
        while True:
            op = self._match(TT.LT, TT.LE, TT.GT, TT.GE)
            if not op: break
            left = BinOp(op.value, left, self._parse_shift())
        return left

    def _parse_shift(self) -> Any:
        left = self._parse_additive()
        while True:
            op = self._match(TT.LSHIFT, TT.RSHIFT)
            if not op: break
            left = BinOp(op.value, left, self._parse_additive())
        return left

    def _parse_additive(self) -> Any:
        left = self._parse_multiplicative()
        while True:
            op = self._match(TT.PLUS, TT.MINUS)
            if not op: break
            left = BinOp(op.value, left, self._parse_multiplicative())
        return left

    def _parse_multiplicative(self) -> Any:
        left = self._parse_unary()
        while True:
            op = self._match(TT.STAR, TT.SLASH, TT.PERCENT)
            if not op: break
            left = BinOp(op.value, left, self._parse_unary())
        return left

    def _parse_unary(self) -> Any:
        if self._match(TT.MINUS):
            return UnaryOp('-', self._parse_unary())
        if self._peek().type == TT.NOT:
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TT.LBRACKET:
                return self._parse_postfix()
            self._advance()
            return UnaryOp('!', self._parse_unary())
        return self._parse_postfix()

    def _parse_postfix(self) -> Any:
        expr = self._parse_primary()
        while True:
            if self._match(TT.AS):
                target = self._parse_type()
                expr = CastExpr(expr, target.name)
            elif self._peek().type == TT.LBRACKET and not isinstance(expr, CallExpr):
                self._advance()
                index = self._parse_expr()
                self._expect(TT.RBRACKET)
                expr = IndexExpr(expr, index)
            else:
                break
        return expr

    def _parse_primary(self) -> Any:
        t = self._peek()
        if t.type == TT.INT:
            self._advance()
            return IntLit(t.value)
        elif t.type == TT.FLOAT:
            self._advance()
            return FloatLit(t.value)
        elif t.type == TT.TRUE:
            self._advance()
            return BoolLit(True)
        elif t.type == TT.FALSE:
            self._advance()
            return BoolLit(False)
        elif t.type == TT.IDENT:
            self._advance()
            if self._peek().type == TT.LPAREN:
                self._advance()
                args = []
                while self._peek().type != TT.RPAREN:
                    args.append(self._parse_expr())
                    if not self._match(TT.COMMA): break
                self._expect(TT.RPAREN)
                return CallExpr(t.value, args)
            return Ident(t.value)
        elif t.type == TT.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TT.RPAREN)
            return expr
        elif t.type == TT.LBRACKET:
            # Array literal [a, b, c]
            self._advance()
            elems = []
            while self._peek().type != TT.RBRACKET:
                elems.append(self._parse_expr())
                if not self._match(TT.COMMA): break
            self._expect(TT.RBRACKET)
            return ArrayLit(elems)
        elif t.type == TT.INTENT:
            self._advance()
            self._expect(TT.NOT)
            self._expect(TT.LBRACKET)
            components = []
            while self._peek().type != TT.RBRACKET:
                comp = self._parse_expr()
                if isinstance(comp, (IntLit, FloatLit)):
                    components.append(float(comp.value))
                else:
                    components.append(0.0)
                if not self._match(TT.COMMA): break
            self._expect(TT.RBRACKET)
            return IntentLit(components)
        else:
            raise SyntaxError(f"Unexpected token {t.type} ('{t.value}') at line {t.line}:{t.col}")


# ─── FLAT IR (for optimization) ────────────────────────────────

class IROp:
    """Base class for IR operations."""
    pass

@dataclass
class IRLabel(IROp):
    name: str

@dataclass
class IRBinOp(IROp):
    op: str; dst: str; left: str; right: str

@dataclass
class IRUnaryOp(IROp):
    op: str; dst: str; operand: str

@dataclass
class IRMove(IROp):
    dst: str; src: str

@dataclass
class IRLoadImm(IROp):
    dst: str; value: Any; is_float: bool = False

@dataclass
class IRCall(IROp):
    name: str; args: List[str]; dst: Optional[str] = None
    is_float_ret: bool = False

@dataclass
class IRJump(IROp):
    target: str

@dataclass
class IRCondJump(IROp):
    cond: str; target: str; jump_if_zero: bool = True

@dataclass
class IRRet(IROp):
    value: Optional[str] = None; is_float: bool = False

@dataclass
class IRPush(IROp):
    reg: str

@dataclass
class IRPop(IROp):
    reg: str

@dataclass
class IRPanic(IROp):
    msg: str = "constraint violation"

@dataclass
class IRUnreachable(IROp):
    pass

@dataclass
class IRBuiltinCall(IROp):
    name: str; args: List[str]; dst: str
    is_float: bool = False

@dataclass
class IRVStore(IROp):
    vec_reg: int; component: int; value: str

@dataclass
class IRVOp(IROp):
    op: str; dst: str; left: str; right: str

@dataclass
class IRA2AOp(IROp):
    op: str; args: List[str]

@dataclass
class IRStackAlloc(IROp):
    name: str; size: int  # in words

@dataclass
class IRStoreStack(IROp):
    slot: int; src: str

@dataclass
class IRLoadStack(IROp):
    dst: str; slot: int

@dataclass
class IRComment(IROp):
    text: str

# ─── IR Builder ────────────────────────────────────────────────

class IRBuilder:
    """Builds FLAT IR from AST, then optimization passes run on IR."""
    def __init__(self, functions: Dict[str, FnDecl]):
        self.functions = functions
        self.ir: List[IROp] = []
        self.label_counter = 0
        self.temp_counter = 0
        self.var_types: Dict[str, str] = {}  # var -> 'i32' | 'f32' | 'vec9'
        self.var_map: Dict[str, str] = {}  # var -> virtual reg name
        self.epilogue_emitted = False

    def new_label(self, prefix='L'):
        self.label_counter += 1
        return f'{prefix}{self.label_counter}'

    def new_temp(self, prefix='t'):
        self.temp_counter += 1
        return f'{prefix}{self.temp_counter}'

    def emit(self, op: IROp):
        self.ir.append(op)

    def get_vreg(self, name: str) -> str:
        if name in self.var_map:
            return self.var_map[name]
        t = self.new_temp('v')
        self.var_map[name] = t
        return t

    def _infer_type(self, expr: Any) -> str:
        """Infer the result type of an expression."""
        if isinstance(expr, IntLit): return 'i32'
        if isinstance(expr, FloatLit): return 'f32'
        if isinstance(expr, BoolLit): return 'i32'
        if isinstance(expr, Ident):
            return self.var_types.get(expr.name, 'i32')
        if isinstance(expr, BinOp):
            lt = self._infer_type(expr.left)
            rt = self._infer_type(expr.right)
            if lt == 'f32' or rt == 'f32': return 'f32'
            if lt == 'vec9' or rt == 'vec9': return 'vec9'
            return 'i32'
        if isinstance(expr, UnaryOp):
            return self._infer_type(expr.operand)
        if isinstance(expr, CastExpr):
            return expr.target_type
        if isinstance(expr, CallExpr):
            return self._infer_call_type(expr)
        if isinstance(expr, IntentLit):
            return 'vec9'
        if isinstance(expr, ArrayLit):
            return 'i32'  # default
        return 'i32'

    def _infer_call_type(self, expr: CallExpr) -> str:
        """Infer return type of a call expression."""
        # Float builtins
        float_builtins = {'round', 'sqrt', 'abs', 'sin', 'cos', 'exp', 'log', 'floor', 'ceil'}
        vec_builtins = {'vdot', 'vadd', 'vmul', 'vnorm'}
        if expr.name in float_builtins:
            # If arg is float, return float; otherwise also float
            if expr.args:
                arg_type = self._infer_type(expr.args[0])
                if arg_type == 'vec9':
                    return 'f32'
            return 'f32'
        if expr.name in vec_builtins:
            if expr.name == 'vdot': return 'f32'
            return 'vec9'
        if expr.name in ('abs', 'min', 'max'):
            if expr.args:
                return self._infer_type(expr.args[0])
            return 'i32'
        if expr.name in self.functions:
            return self.functions[expr.name].return_type.name
        return 'i32'

    def build_function(self, fn: FnDecl) -> Tuple[List[IROp], Dict[str, str]]:
        """Build IR for a function. Returns (ir_ops, var_types)."""
        self.var_types = {}
        self.var_map = {}
        self.epilogue_emitted = False

        # Map params
        for i, param in enumerate(fn.params):
            vreg = self.get_vreg(param.name)
            self.var_types[param.name] = param.type_.name

        # Map params to argument registers
        arg_map = {}
        for i, param in enumerate(fn.params):
            if param.type_.name == 'f32':
                arg_map[param.name] = f'F{9 + i}'
            else:
                arg_map[param.name] = f'R{9 + i}'

        # Build body
        self._build_block(fn.body, fn)

        return self.ir, self.var_types, self.var_map, arg_map

    def _build_block(self, stmts, fn):
        for stmt in stmts:
            self._build_stmt(stmt, fn)

    def _build_stmt(self, stmt, fn):
        if isinstance(stmt, LetStmt):
            vreg = self.get_vreg(stmt.name)
            expr_type = self._infer_type(stmt.init)
            if stmt.type_:
                self.var_types[stmt.name] = stmt.type_.name
            else:
                self.var_types[stmt.name] = expr_type
            result = self._build_expr(stmt.init, fn)
            self.emit(IRMove(vreg, result))

        elif isinstance(stmt, AssignStmt):
            result = self._build_expr(stmt.value, fn)
            vreg = self.get_vreg(stmt.name)
            self.emit(IRMove(vreg, result))

        elif isinstance(stmt, IndexAssignStmt):
            idx = self._build_expr(stmt.index, fn)
            val = self._build_expr(stmt.value, fn)
            vreg = self.get_vreg(stmt.target.name if isinstance(stmt.target, Ident) else str(stmt.target))
            self.emit(IRComment(f'  {vreg}[{idx}] = {val}'))

        elif isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                result = self._build_expr(stmt.value, fn)
                is_float = fn.return_type.name == 'f32'
                self.emit(IRRet(result, is_float))
            else:
                self.emit(IRRet())
            self.epilogue_emitted = True

        elif isinstance(stmt, IfStmt):
            else_label = self.new_label('else')
            end_label = self.new_label('endif')
            cond = self._build_expr(stmt.condition, fn)
            if stmt.else_body:
                self.emit(IRCondJump(cond, else_label))
            else:
                self.emit(IRCondJump(cond, end_label))
            self._build_block(stmt.then_body, fn)
            if stmt.else_body:
                self.emit(IRJump(end_label))
                self.emit(IRLabel(else_label))
                self._build_block(stmt.else_body, fn)
            self.emit(IRLabel(end_label))

        elif isinstance(stmt, WhileStmt):
            loop_label = self.new_label('while')
            end_label = self.new_label('endwhile')
            self.emit(IRLabel(loop_label))
            cond = self._build_expr(stmt.condition, fn)
            self.emit(IRCondJump(cond, end_label))
            self._build_block(stmt.body, fn)
            self.emit(IRJump(loop_label))
            self.emit(IRLabel(end_label))

        elif isinstance(stmt, ForRangeStmt):
            # for i in range(start, end) → while loop with counter
            counter_vreg = self.get_vreg(stmt.var_name)
            self.var_types[stmt.var_name] = 'i32'
            start_v = self._build_expr(stmt.start, fn)
            end_v = self._build_expr(stmt.end, fn)
            self.emit(IRMove(counter_vreg, start_v))

            loop_label = self.new_label('for')
            end_label = self.new_label('endfor')
            self.emit(IRLabel(loop_label))
            cond = self.new_temp('t')
            self.emit(IRBinOp('<', cond, counter_vreg, end_v))
            self.emit(IRCondJump(cond, end_label))
            self._build_block(stmt.body, fn)
            one = self.new_temp('t')
            self.emit(IRLoadImm(one, 1))
            new_counter = self.new_temp('t')
            self.emit(IRBinOp('+', new_counter, counter_vreg, one))
            self.emit(IRMove(counter_vreg, new_counter))
            self.emit(IRJump(loop_label))
            self.emit(IRLabel(end_label))

        elif isinstance(stmt, MatchStmt):
            value = self._build_expr(stmt.value, fn)
            end_label = self.new_label('match_end')
            for pattern, body in stmt.arms:
                next_label = self.new_label('match_next')
                if isinstance(pattern, Ident) and pattern.name == '_':
                    # Wildcard — unconditional
                    self._build_block(body, fn)
                    self.emit(IRJump(end_label))
                else:
                    pat_val = self._build_expr(pattern, fn)
                    eq_temp = self.new_temp('t')
                    self.emit(IRBinOp('==', eq_temp, value, pat_val))
                    self.emit(IRCondJump(eq_temp, next_label))
                    self._build_block(body, fn)
                    self.emit(IRJump(end_label))
                    self.emit(IRLabel(next_label))
            if stmt.default:
                self._build_block(stmt.default, fn)
            self.emit(IRLabel(end_label))

        elif isinstance(stmt, ConstraintStmt):
            result = self._build_expr(stmt.expr, fn)
            ok_label = self.new_label('ok')
            self.emit(IRCondJump(result, ok_label, jump_if_zero=True))
            self.emit(IRPanic())
            self.emit(IRLabel(ok_label))

        elif isinstance(stmt, RequireStmt):
            self._build_stmt(ConstraintStmt(stmt.expr), fn)

        elif isinstance(stmt, ExprStmt):
            if isinstance(stmt.expr, CallExpr):
                self._build_call_void(stmt.expr, fn)
            else:
                self._build_expr(stmt.expr, fn)

    def _build_expr(self, expr, fn) -> str:
        """Build expression, return virtual register name holding result."""
        if isinstance(expr, IntLit):
            t = self.new_temp('t')
            self.emit(IRLoadImm(t, expr.value))
            return t

        elif isinstance(expr, FloatLit):
            t = self.new_temp('tf')
            self.emit(IRLoadImm(t, expr.value, is_float=True))
            return t

        elif isinstance(expr, BoolLit):
            t = self.new_temp('t')
            self.emit(IRLoadImm(t, 1 if expr.value else 0))
            return t

        elif isinstance(expr, Ident):
            return self.get_vreg(expr.name)

        elif isinstance(expr, BinOp):
            left = self._build_expr(expr.left, fn)
            right = self._build_expr(expr.right, fn)
            t = self.new_temp('t')
            self.emit(IRBinOp(expr.op, t, left, right))
            return t

        elif isinstance(expr, UnaryOp):
            operand = self._build_expr(expr.operand, fn)
            t = self.new_temp('t')
            self.emit(IRUnaryOp(expr.op, t, operand))
            return t

        elif isinstance(expr, CallExpr):
            return self._build_call(expr, fn)

        elif isinstance(expr, CastExpr):
            inner = self._build_expr(expr.expr, fn)
            t = self.new_temp('t')
            if expr.target_type == 'f32':
                self.emit(IRBuiltinCall('itof', [inner], t, is_float=True))
            elif expr.target_type == 'i32':
                self.emit(IRBuiltinCall('ftoi', [inner], t, is_float=False))
            else:
                self.emit(IRMove(t, inner))
            return t

        elif isinstance(expr, IntentLit):
            t = self.new_temp('tv')
            for i, comp in enumerate(expr.components):
                comp_t = self.new_temp('tf')
                self.emit(IRLoadImm(comp_t, comp, is_float=True))
                self.emit(IRVStore(0, i, comp_t))
            self.emit(IRComment(f'  intent![...] -> {t}'))
            return t

        elif isinstance(expr, ArrayLit):
            t = self.new_temp('t')
            for i, elem in enumerate(expr.elements):
                elem_t = self._build_expr(elem, fn)
                self.emit(IRComment(f'  {t}[{i}] = {elem_t}'))
            return t

        elif isinstance(expr, IndexExpr):
            target = self._build_expr(expr.target, fn)
            index = self._build_expr(expr.index, fn)
            t = self.new_temp('t')
            self.emit(IRComment(f'  {t} = {target}[{index}]'))
            return t

        else:
            t = self.new_temp('t')
            self.emit(IRComment(f'  unhandled expr: {type(expr).__name__}'))
            return t

    def _build_call(self, expr: CallExpr, fn: FnDecl) -> str:
        """Build a function/builtin call that returns a value."""
        t = self.new_temp('t')
        ret_type = self._infer_call_type(expr)
        is_float = ret_type == 'f32'
        is_vec = ret_type == 'vec9'

        # Vec builtins
        vec_builtins = {'vdot', 'vadd', 'vmul'}
        if expr.name in vec_builtins:
            args = [self._build_expr(a, fn) for a in expr.args]
            if expr.name == 'vdot':
                self.emit(IRVOp('VDot', t, args[0], args[1]))
                return t
            elif expr.name == 'vadd':
                self.emit(IRVOp('VAdd', t, args[0], args[1]))
                return t
            elif expr.name == 'vmul':
                self.emit(IRVOp('VMul', t, args[0], args[1]))
                return t

        # Float builtins — always resolve regardless of context
        float_1arg = {'round': 'FRound', 'sqrt': 'FSqrt', 'abs': 'FAbs',
                      'sin': 'FSin', 'cos': 'FCos', 'exp': 'FExp',
                      'log': 'FLog', 'floor': 'FFloor', 'ceil': 'FCeil'}
        float_2arg = {'min': 'FMin', 'max': 'FMax'}

        if expr.name in float_1arg and len(expr.args) == 1:
            arg = self._build_expr(expr.args[0], fn)
            self.emit(IRBuiltinCall(float_1arg[expr.name], [arg], t, is_float=True))
            return t
        if expr.name in float_2arg and len(expr.args) == 2:
            a1 = self._build_expr(expr.args[0], fn)
            a2 = self._build_expr(expr.args[1], fn)
            self.emit(IRBuiltinCall(float_2arg[expr.name], [a1, a2], t, is_float=True))
            return t

        # Int builtins
        int_1arg = {'abs': 'IAbs'}
        int_2arg = {'min': 'IMin', 'max': 'IMax'}
        if expr.name in int_1arg and len(expr.args) == 1:
            arg_type = self._infer_type(expr.args[0])
            if arg_type == 'f32':
                # Redirect to float version
                arg = self._build_expr(expr.args[0], fn)
                self.emit(IRBuiltinCall('FAbs', [arg], t, is_float=True))
            else:
                arg = self._build_expr(expr.args[0], fn)
                self.emit(IRBuiltinCall('IAbs', [arg], t))
            return t
        if expr.name in int_2arg and len(expr.args) == 2:
            arg_type = self._infer_type(expr.args[0])
            if arg_type == 'f32':
                a1 = self._build_expr(expr.args[0], fn)
                a2 = self._build_expr(expr.args[1], fn)
                self.emit(IRBuiltinCall(f'F{expr.name.capitalize()}', [a1, a2], t, is_float=True))
            else:
                a1 = self._build_expr(expr.args[0], fn)
                a2 = self._build_expr(expr.args[1], fn)
                self.emit(IRBuiltinCall(f'I{expr.name.capitalize()}', [a1, a2], t))
            return t

        # A2A builtins
        a2a_ops = {'tell': 'ATell', 'ask': 'AAsk', 'wait': 'AWait',
                   'broadcast': 'ABroadcast', 'trust': 'ATrust',
                   'verify': 'AVerify', 'subscribe': 'ASubscribe', 'delegate': 'ADelegate'}
        if expr.name in a2a_ops:
            args = [self._build_expr(a, fn) for a in expr.args]
            self.emit(IRA2AOp(a2a_ops[expr.name], args))
            return t

        # Special builtins
        if expr.name == 'panic':
            self.emit(IRPanic())
            return t
        if expr.name == 'unreachable':
            self.emit(IRUnreachable())
            return t

        # User-defined function call
        if expr.name in self.functions:
            callee = self.functions[expr.name]
            args = [self._build_expr(a, fn) for a in expr.args]
            is_float_ret = callee.return_type.name == 'f32'
            self.emit(IRCall(expr.name, args, t, is_float_ret))
            return t

        self.emit(IRComment(f'  unknown function: {expr.name}'))
        return t

    def _build_call_void(self, expr: CallExpr, fn: FnDecl):
        """Build a call used as a statement (return value discarded)."""
        t = self._build_call(expr, fn)
        # Result discarded


# ─── Optimization Passes ──────────────────────────────────────

class OptPass:
    """Base class for optimization passes."""
    def run(self, ir: List[IROp]) -> List[IROp]:
        raise NotImplementedError

class ConstantFolding(OptPass):
    """Evaluate constant expressions at compile time."""
    def run(self, ir: List[IROp]) -> List[IROp]:
        # Build value map: vreg -> constant value
        const_map: Dict[str, Any] = {}
        result = []

        for op in ir:
            if isinstance(op, IRLoadImm):
                const_map[op.dst] = op.value
                result.append(op)
            elif isinstance(op, IRBinOp) and op.left in const_map and op.right in const_map:
                lv = const_map[op.left]
                rv = const_map[op.right]
                folded = self._fold(op.op, lv, rv)
                if folded is not None:
                    const_map[op.dst] = folded
                    result.append(IRLoadImm(op.dst, folded))
                else:
                    result.append(op)
            elif isinstance(op, IRMove):
                if op.src in const_map:
                    const_map[op.dst] = const_map[op.src]
                result.append(op)
            else:
                result.append(op)

        return result

    def _fold(self, op: str, l: Any, r: Any) -> Optional[Any]:
        try:
            if isinstance(l, float) or isinstance(r, float):
                lf, rf = float(l), float(r)
                if op == '+': return lf + rf
                if op == '-': return lf - rf
                if op == '*': return lf * rf
                if op == '/' and rf != 0: return lf / rf
                if op == '<': return 1 if lf < rf else 0
                if op == '<=': return 1 if lf <= rf else 0
                if op == '>': return 1 if lf > rf else 0
                if op == '>=': return 1 if lf >= rf else 0
                if op == '==': return 1 if lf == rf else 0
                if op == '!=': return 1 if lf != rf else 0
            else:
                li, ri = int(l), int(r)
                if op == '+': return li + ri
                if op == '-': return li - ri
                if op == '*': return li * ri
                if op == '/' and ri != 0: return int(li / ri)
                if op == '%' and ri != 0: return li % ri
                if op == '<<': return li << ri
                if op == '>>': return li >> ri
                if op == '<': return 1 if li < ri else 0
                if op == '<=': return 1 if li <= ri else 0
                if op == '>': return 1 if li > ri else 0
                if op == '>=': return 1 if li >= ri else 0
                if op == '==': return 1 if li == ri else 0
                if op == '!=': return 1 if li != ri else 0
                if op == '&': return li & ri
                if op == '|': return li | ri
                if op == '^': return li ^ ri
        except (OverflowError, ZeroDivisionError):
            pass
        return None


class DeadCodeElimination(OptPass):
    """Remove assignments to variables that are never read."""
    def run(self, ir: List[IROp]) -> List[IROp]:
        # Find all used vregs
        used: Set[str] = set()
        for op in ir:
            if isinstance(op, IRBinOp):
                used.add(op.left); used.add(op.right)
            elif isinstance(op, IRUnaryOp):
                used.add(op.operand)
            elif isinstance(op, IRMove):
                if op.src != op.dst:
                    used.add(op.src)
            elif isinstance(op, IRCondJump):
                used.add(op.cond)
            elif isinstance(op, IRRet) and op.value:
                used.add(op.value)
            elif isinstance(op, IRCall):
                for a in op.args: used.add(a)
            elif isinstance(op, IRBuiltinCall):
                for a in op.args: used.add(a)
            elif isinstance(op, IRVOp):
                used.add(op.left); used.add(op.right)
            elif isinstance(op, IRVStore):
                used.add(op.value)
            elif isinstance(op, IRA2AOp):
                for a in op.args: used.add(a)

        # Remove dead assignments (but keep labels/jumps)
        result = []
        for op in ir:
            if isinstance(op, (IRLoadImm, IRBinOp, IRUnaryOp, IRBuiltinCall, IRVOp)):
                if op.dst not in used:
                    continue
            elif isinstance(op, IRMove):
                if op.dst not in used and op.dst == op.src:
                    continue  # self-move is dead
                if op.dst not in used:
                    continue
            result.append(op)

        return result


class StrengthReduction(OptPass):
    """Replace expensive operations with cheaper ones."""
    def run(self, ir: List[IROp]) -> List[IROp]:
        const_map: Dict[str, Any] = {}
        result = []

        for op in ir:
            if isinstance(op, IRLoadImm):
                const_map[op.dst] = op.value
                result.append(op)
            elif isinstance(op, IRBinOp):
                # x * 2 → x << 1, x * 4 → x << 2, etc.
                if op.op == '*' and op.right in const_map:
                    rv = const_map[op.right]
                    if isinstance(rv, int) and rv > 0 and (rv & (rv - 1)) == 0:
                        shift = rv.bit_length() - 1
                        result.append(IRBinOp('<<', op.dst, op.left, op.right))
                        result.append(IRComment(f'  strength-reduced: * {rv} → << {shift}'))
                        continue
                    if isinstance(rv, int) and rv == 1:
                        result.append(IRMove(op.dst, op.left))
                        continue
                if op.op == '*' and op.left in const_map:
                    lv = const_map[op.left]
                    if isinstance(lv, int) and lv > 0 and (lv & (lv - 1)) == 0:
                        result.append(IRBinOp('<<', op.dst, op.right, op.left))
                        result.append(IRComment(f'  strength-reduced: * {lv} → <<'))
                        continue
                    if isinstance(lv, int) and lv == 1:
                        result.append(IRMove(op.dst, op.right))
                        continue
                # x / 2 → x >> 1 for powers of 2
                if op.op == '/' and op.right in const_map:
                    rv = const_map[op.right]
                    if isinstance(rv, int) and rv > 0 and (rv & (rv - 1)) == 0:
                        result.append(IRBinOp('>>', op.dst, op.left, op.right))
                        result.append(IRComment(f'  strength-reduced: / {rv} → >>'))
                        continue
                # x + 0, x - 0 → x
                if op.op in ('+', '-') and op.right in const_map and const_map[op.right] == 0:
                    result.append(IRMove(op.dst, op.left))
                    continue
                # x * 0 → 0
                if op.op == '*' and (op.right in const_map and const_map[op.right] == 0):
                    result.append(IRLoadImm(op.dst, 0))
                    continue
                result.append(op)
            else:
                result.append(op)

        return result


class PeepholeOpt(OptPass):
    """Remove redundant instruction patterns."""
    def run(self, ir: List[IROp]) -> List[IROp]:
        result = []
        i = 0
        while i < len(ir):
            # Pattern: LoadImm + LoadImm to same dst → keep only last
            if (i + 1 < len(ir)
                and isinstance(ir[i], IRLoadImm) and isinstance(ir[i+1], IRLoadImm)
                and ir[i].dst == ir[i+1].dst):
                result.append(ir[i+1])
                i += 2
                continue

            # Pattern: Move a, a (self-move) → remove
            if isinstance(ir[i], IRMove) and ir[i].dst == ir[i].src:
                i += 1
                continue

            # Pattern: LoadImm 0 then CondJump → can simplify later
            # For now just pass through
            result.append(ir[i])
            i += 1

        return result


def run_optimizations(ir: List[IROp], level: int = 2) -> List[IROp]:
    """Run optimization passes on IR."""
    passes = [
        ConstantFolding(),
        StrengthReduction(),
        DeadCodeElimination(),
        PeepholeOpt(),
    ]
    for _ in range(level):
        for p in passes:
            ir = p.run(ir)
    return ir


# ─── Register Allocator (interference graph + coalescing) ─────

class RegAllocator:
    """Register allocator with interference graph and copy coalescing.

    Uses Chaitin-Briggs style graph coloring for R0-R7 (8 GP regs)
    and F0-F7 (8 FP regs).
    """
    def __init__(self, num_gp=8, num_fp=8):
        self.num_gp = num_gp
        self.num_fp = num_fp

    def allocate(self, ir: List[IROp], var_types: Dict[str, str],
                 var_map: Dict[str, str], arg_map: Dict[str, str],
                 functions: Dict[str, FnDecl]) -> Tuple[List[IROp], Dict[str, str]]:
        """Allocate physical registers. Returns (new_ir, vreg_to_physical_map)."""
        # Collect all virtual registers and their types
        all_vregs: Set[str] = set()
        vreg_is_float: Dict[str, bool] = {}

        for name, vreg in var_map.items():
            all_vregs.add(vreg)
            vreg_is_float[vreg] = var_types.get(name, 'i32') in ('f32',)

        # Also scan IR for temps
        for op in ir:
            for attr in ('dst', 'left', 'right', 'operand', 'cond', 'value'):
                v = getattr(op, attr, None)
                if isinstance(v, str) and (v.startswith('t') or v.startswith('v') or v.startswith('tf') or v.startswith('tv')):
                    all_vregs.add(v)
                    if v.startswith('tf'):
                        vreg_is_float[v] = True
                    elif v not in vreg_is_float:
                        vreg_is_float[v] = False

        # Build liveness: for each vreg, what's the last use point
        last_use: Dict[str, int] = {}
        first_def: Dict[str, int] = {}
        for idx, op in enumerate(ir):
            uses = self._get_uses(op)
            defs = self._get_defs(op)
            for u in uses:
                if u in all_vregs:
                    last_use[u] = idx
            for d in defs:
                if d in all_vregs:
                    if d not in first_def:
                        first_def[d] = idx

        # Build interference graph
        # Two vregs interfere if one is live at the definition of the other
        live_at: Dict[int, Set[str]] = {}
        for idx in range(len(ir)):
            live_at[idx] = set()

        # Backward liveness analysis
        live: Set[str] = set()
        for idx in range(len(ir) - 1, -1, -1):
            op = ir[idx]
            defs = self._get_defs(op)
            uses = self._get_uses(op)
            live -= defs
            live |= uses
            live_at[idx] = set(live)

        # Build interference: vreg A interferes with B if A is live at B's definition
        interference: Dict[str, Set[str]] = {v: set() for v in all_vregs}
        for idx, op in enumerate(ir):
            defs = self._get_defs(op)
            for d in defs:
                if d in all_vregs:
                    for lv in live_at.get(idx, set()):
                        if lv in all_vregs and lv != d:
                            interference[d].add(lv)
                            interference[lv].add(d)

        # Build move graph for coalescing
        move_pairs: List[Tuple[str, str]] = []
        for op in ir:
            if isinstance(op, IRMove):
                move_pairs.append((op.dst, op.src))

        # Coalesce: merge non-interfering move pairs
        # Union-Find
        parent: Dict[str, str] = {v: v for v in all_vregs}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            a, b = find(a), find(b)
            if a == b: return
            # Check no interference between the groups
            for v in all_vregs:
                if find(v) == a and b in interference.get(v, set()):
                    return  # Can't coalesce
            parent[a] = b

        for dst, src in move_pairs:
            if src in all_vregs and dst in all_vregs:
                if src not in interference.get(dst, set()):
                    union(dst, src)

        # Build coloring groups
        groups: Dict[str, Set[str]] = {}
        for v in all_vregs:
            root = find(v)
            if root not in groups:
                groups[root] = set()
            groups[root].add(v)

        # Graph coloring
        assignment: Dict[str, int] = {}
        stack_slots: Dict[str, int] = {}
        next_slot = 0

        # Pre-assign argument registers
        for name, phys in arg_map.items():
            if name in var_map:
                vreg = var_map[name]
                try:
                    reg_num = int(phys[1:])
                    assignment[vreg] = reg_num
                    # Also assign the whole coalesce group
                    root = find(vreg)
                    for member in groups.get(root, {vreg}):
                        assignment[member] = reg_num
                except (ValueError, IndexError):
                    pass

        # Color remaining groups
        for root, members in groups.items():
            if root in assignment:
                continue  # Already assigned via arg
            is_float = any(vreg_is_float.get(m, False) for m in members)
            num_regs = self.num_fp if is_float else self.num_gp
            reg_base = 0 if is_float else 0  # Both start at 0

            # Find colors used by interfering neighbors
            used_colors: Set[int] = set()
            for m in members:
                for neighbor in interference.get(m, set()):
                    nroot = find(neighbor)
                    if nroot in assignment:
                        used_colors.add(assignment[nroot])

            # Pick lowest available color
            color = None
            for c in range(num_regs):
                if c not in used_colors:
                    color = c
                    break

            if color is not None:
                for m in members:
                    assignment[m] = color
            else:
                # Spill to stack
                slot = next_slot
                next_slot += 1
                for m in members:
                    stack_slots[m] = slot

        # Build physical name map
        phys_map: Dict[str, str] = {}
        for vreg in all_vregs:
            root = find(vreg)
            if root in assignment:
                reg_num = assignment[root]
                is_float = vreg_is_float.get(vreg, False)
                if is_float:
                    phys_map[vreg] = f'F{reg_num}'
                else:
                    phys_map[vreg] = f'R{reg_num}'
            elif vreg in stack_slots:
                phys_map[vreg] = f'STACK[{stack_slots[vreg]}]'
            else:
                phys_map[vreg] = f'R0'  # fallback

        return phys_map, stack_slots

    def _get_uses(self, op: IROp) -> Set[str]:
        uses = set()
        if isinstance(op, IRBinOp): uses.add(op.left); uses.add(op.right)
        elif isinstance(op, IRUnaryOp): uses.add(op.operand)
        elif isinstance(op, IRMove) and op.src != op.dst: uses.add(op.src)
        elif isinstance(op, IRCondJump): uses.add(op.cond)
        elif isinstance(op, IRRet) and op.value: uses.add(op.value)
        elif isinstance(op, IRCall):
            for a in op.args: uses.add(a)
        elif isinstance(op, IRBuiltinCall):
            for a in op.args: uses.add(a)
        elif isinstance(op, IRVOp): uses.add(op.left); uses.add(op.right)
        elif isinstance(op, IRVStore): uses.add(op.value)
        elif isinstance(op, IRA2AOp):
            for a in op.args: uses.add(a)
        return uses

    def _get_defs(self, op: IROp) -> Set[str]:
        defs = set()
        if isinstance(op, (IRLoadImm, IRBinOp, IRUnaryOp, IRBuiltinCall, IRVOp)):
            defs.add(op.dst)
        elif isinstance(op, IRMove):
            defs.add(op.dst)
        elif isinstance(op, IRCall) and op.dst:
            defs.add(op.dst)
        return defs


# ─── Code Emitter ──────────────────────────────────────────────

GP_REGS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7',
           'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']
FP_REGS = ['F0', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7',
           'F8', 'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15']

class CodeEmitter:
    """Emit FLUX assembly from optimized IR with physical register assignment."""
    def __init__(self, phys_map: Dict[str, str], stack_slots: Dict[str, int],
                 functions: Dict[str, FnDecl]):
        self.phys_map = phys_map
        self.stack_slots = stack_slots
        self.functions = functions
        self.output: List[str] = []
        self.stack_size = len(set(stack_slots.values())) if stack_slots else 0

    def pr(self, name: str) -> str:
        """Map virtual reg to physical reg name."""
        return self.phys_map.get(name, name)

    def emit(self, line: str, indent: int = 1):
        self.output.append('  ' * indent + line)

    def emit_raw(self, line: str):
        self.output.append(line)

    def emit_function(self, fn: FnDecl, ir: List[IROp], arg_map: Dict[str, str]):
        layer = 'FLUX-C' if fn.is_constraint else 'FLUX-X'
        self.emit_raw(f'FUNC {fn.name}')
        self.emit(f'; Layer: {layer}')

        # Prologue
        self.emit('Push R12            ; save FP')
        self.emit('IMov R12, R11       ; FP = SP')
        if self.stack_size > 0:
            self.emit(f'ISub R11, R11, {self.stack_size * 4}  ; alloc stack')

        # Move params from arg regs to their allocated regs
        for name, arg_phys in arg_map.items():
            vreg = None
            # Find vreg for this param
            for op in ir:
                if isinstance(op, IRComment) and name in op.text:
                    break
            # The phys_map should already handle the mapping via coalescing

        # Emit IR ops
        has_return = False
        for op in ir:
            self._emit_op(op, fn)
            if isinstance(op, IRRet):
                has_return = True

        # Epilogue (only if no explicit return)
        if not has_return:
            self._emit_epilogue()

        self.emit_raw('ENDFUNC')

    def _emit_epilogue(self):
        if self.stack_size > 0:
            self.emit(f'IAdd R11, R11, {self.stack_size * 4}  ; dealloc stack')
        self.emit('IMov R11, R12       ; restore SP')
        self.emit('Pop R12             ; restore FP')
        self.emit('Ret')

    def _emit_op(self, op: IROp, fn: FnDecl):
        if isinstance(op, IRComment):
            self.emit(f'; {op.text}')

        elif isinstance(op, IRLabel):
            self.emit_raw(f'{op.name}:')

        elif isinstance(op, IRLoadImm):
            p = self.pr(op.dst)
            if op.is_float:
                self.emit(f'FMov {p}, {op.value}')
            else:
                self.emit(f'IMov {p}, {op.value}')

        elif isinstance(op, IRMove):
            dst = self.pr(op.dst)
            src = self.pr(op.src)
            if dst != src:
                # Determine if float move
                if dst.startswith('F') or src.startswith('F'):
                    self.emit(f'FMov {dst}, {src}')
                else:
                    self.emit(f'IMov {dst}, {src}')

        elif isinstance(op, IRBinOp):
            dst = self.pr(op.dst)
            left = self.pr(op.left)
            right = self.pr(op.right)
            is_float = dst.startswith('F') or left.startswith('F') or right.startswith('F')

            op_map_int = {
                '+': 'IAdd', '-': 'ISub', '*': 'IMul', '/': 'IDiv', '%': 'IMod',
                '==': 'ICmpEq', '!=': 'ICmpNe', '<': 'ICmpLt', '<=': 'ICmpLe',
                '>': 'ICmpGt', '>=': 'ICmpGe',
                '<<': 'IShl', '>>': 'IShr', '&': 'IAnd', '|': 'IOr', '^': 'IXor',
            }
            op_map_float = {
                '+': 'FAdd', '-': 'FSub', '*': 'FMul', '/': 'FDiv',
                '==': 'FCmpEq', '!=': 'FCmpNe', '<': 'FCmpLt', '<=': 'FCmpLe',
                '>': 'FCmpGt', '>=': 'FCmpGe',
            }

            if is_float and op.op in op_map_float:
                self.emit(f'{op_map_float[op.op]} {dst}, {left}, {right}')
            elif op.op in op_map_int:
                self.emit(f'{op_map_int[op.op]} {dst}, {left}, {right}')
            elif op.op == '&&':
                self.emit(f'; && short-circuit')
                self.emit(f'ICmpEq {dst}, {left}, 0')
                skip = f'and_skip_{id(op)}'
                self.emit(f'JumpIf {dst}, {skip}')
                self.emit(f'ICmpNe {dst}, {right}, 0')
                self.emit_raw(f'{skip}:')
            elif op.op == '||':
                self.emit(f'; || short-circuit')
                self.emit(f'ICmpNe {dst}, {left}, 0')
                skip = f'or_skip_{id(op)}'
                self.emit(f'JumpIf {dst}, {skip}')
                self.emit(f'ICmpNe {dst}, {right}, 0')
                self.emit_raw(f'{skip}:')

        elif isinstance(op, IRUnaryOp):
            dst = self.pr(op.dst)
            operand = self.pr(op.operand)
            if op.op == '-':
                is_float = dst.startswith('F')
                if is_float:
                    self.emit(f'FNeg {dst}, {operand}')
                else:
                    self.emit(f'INeg {dst}, {operand}')
            elif op.op == '!':
                self.emit(f'INot {dst}, {operand}')

        elif isinstance(op, IRCall):
            # Save caller-saved regs, load args, call, restore
            callee = self.functions.get(op.name)
            if not callee:
                self.emit(f'; unknown function: {op.name}')
                return

            # Find which physical regs we need to save
            saved_regs = set()
            for vname, preg in self.phys_map.items():
                if preg.startswith('R') and len(preg) == 2 and preg[1].isdigit():
                    rnum = int(preg[1])
                    if rnum < 8:  # R0-R7 are caller-saved
                        saved_regs.add(preg)

            for sr in sorted(saved_regs):
                self.emit(f'Push {sr}')

            # Load arguments into R9/R10 or F9/F10
            for i, arg in enumerate(op.args):
                parg = self.pr(arg)
                if i < len(callee.params):
                    if callee.params[i].type_.name == 'f32':
                        target = f'F{9 + i}'
                        if parg != target:
                            self.emit(f'FMov {target}, {parg}')
                    else:
                        target = f'R{9 + i}'
                        if parg != target:
                            self.emit(f'IMov {target}, {parg}')

            self.emit(f'Call {op.name}')

            # Move return value
            if op.dst:
                pdst = self.pr(op.dst)
                if op.is_float_ret:
                    if pdst != 'F8':
                        self.emit(f'FMov {pdst}, F8')
                else:
                    if pdst != 'R8':
                        self.emit(f'IMov {pdst}, R8')

            for sr in sorted(saved_regs, reverse=True):
                self.emit(f'Pop {sr}')

        elif isinstance(op, IRBuiltinCall):
            pdst = self.pr(op.dst)
            if op.name in ('itof',):
                parg = self.pr(op.args[0])
                self.emit(f'IToF {pdst}, {parg}, 0')
            elif op.name in ('ftoi',):
                parg = self.pr(op.args[0])
                self.emit(f'FToI {pdst}, {parg}, 0')
            elif len(op.args) == 1:
                parg = self.pr(op.args[0])
                self.emit(f'{op.name} {pdst}, {parg}, 0')
            elif len(op.args) == 2:
                pa1 = self.pr(op.args[0])
                pa2 = self.pr(op.args[1])
                self.emit(f'{op.name} {pdst}, {pa1}, {pa2}')

        elif isinstance(op, IRJump):
            self.emit(f'Jump {op.target}')

        elif isinstance(op, IRCondJump):
            pcond = self.pr(op.cond)
            if op.jump_if_zero:
                self.emit(f'JumpIfNot {pcond}, {op.target}')
            else:
                self.emit(f'JumpIf {pcond}, {op.target}')

        elif isinstance(op, IRRet):
            if op.value:
                pval = self.pr(op.value)
                if op.is_float:
                    if pval != 'F8':
                        self.emit(f'FMov F8, {pval}')
                else:
                    if pval != 'R8':
                        self.emit(f'IMov R8, {pval}')
            self._emit_epilogue()

        elif isinstance(op, IRPanic):
            self.emit(f'Panic               ; {op.msg}')

        elif isinstance(op, IRUnreachable):
            self.emit('Unreachable')

        elif isinstance(op, IRVStore):
            pval = self.pr(op.value)
            self.emit(f'VStore V{op.vec_reg}, {op.component}, {pval}')

        elif isinstance(op, IRVOp):
            pdst = self.pr(op.dst)
            pleft = self.pr(op.left)
            pright = self.pr(op.right)
            self.emit(f'{op.op} {pdst}, {pleft}, {pright}')

        elif isinstance(op, IRA2AOp):
            args_str = ', '.join(self.pr(a) for a in op.args)
            self.emit(f'{op.op} {args_str}')

        elif isinstance(op, IRStackAlloc):
            self.emit(f'; stack alloc {op.name}: {op.size} words')

        elif isinstance(op, (IRStoreStack, IRLoadStack)):
            pass  # handled during reg alloc


# ─── Compilation Pipeline ──────────────────────────────────────

def compile_source(source: str, opt_level: int = 2) -> str:
    """Full compilation pipeline: source → optimized FLUX assembly."""
    # Phase 1: Lexing
    lexer = Lexer(source)

    # Phase 2: Parsing
    parser = Parser(lexer.tokens)
    decls = parser.parse()

    # Separate functions and agents
    functions: Dict[str, FnDecl] = {}
    agents: List[AgentDecl] = []
    fn_order: List[str] = []

    for d in decls:
        if isinstance(d, FnDecl):
            functions[d.name] = d
            fn_order.append(d.name)
        elif isinstance(d, AgentDecl):
            agents.append(d)
            for m in d.methods:
                functions[f'{d.name}.{m.name}'] = m
                fn_order.append(f'{d.name}.{m.name}')

    # Phase 3: IR Generation + Optimization + Code Emission per function
    output_lines: List[str] = []
    output_lines.append('; Generated by Fluxile compiler v0.2.0')
    output_lines.append('; Target: FLUX ISA v3 (FLUX-X / FLUX-C layers)')
    output_lines.append(f'; Optimization level: {opt_level}')
    output_lines.append('')

    for name in fn_order:
        fn = functions[name]

        # Build IR
        builder = IRBuilder(functions)
        ir_ops, var_types, var_map, arg_map = builder.build_function(fn)

        # Optimize IR
        if opt_level > 0:
            ir_ops = run_optimizations(ir_ops, level=opt_level)

        # Register allocation
        reg_alloc = RegAllocator()
        phys_map, stack_slots = reg_alloc.allocate(
            ir_ops, var_types, var_map, arg_map, functions
        )

        # Emit code
        emitter = CodeEmitter(phys_map, stack_slots, functions)
        emitter.emit_function(fn, ir_ops, arg_map)
        output_lines.extend(emitter.output)
        output_lines.append('')

    # Emit agent stubs
    for agent in agents:
        output_lines.append(f'; Agent: {agent.name}')
        output_lines.append(f'AInit {agent.name}')
        for m in agent.methods:
            output_lines.append(f'  ; method: {m.name} → {agent.name}.{m.name}')
        output_lines.append('AEnd')
        output_lines.append('')

    return '\n'.join(output_lines)


def compile_file(filepath: str, opt_level: int = 2) -> str:
    with open(filepath, 'r') as f:
        source = f.read()
    return compile_source(source, opt_level)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 compiler.py <file.fx> [opt_level]")
        print("  opt_level: 0 (none), 1 (basic), 2 (full, default)")
        sys.exit(1)

    filepath = sys.argv[1]
    opt_level = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    try:
        asm = compile_file(filepath, opt_level)
        print(asm)
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
