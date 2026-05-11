#!/usr/bin/env python3
"""
Fluxile → FLUX ISA v3 Assembly Compiler (Proof of Concept)

Parses a subset of Fluxile and generates FLUX assembly text.
Handles: fn, let, return, if/else, while, constraint, require,
         arithmetic, comparisons, boolean ops, builtins, type casts,
         recursive calls, register allocation with stack spilling.

Author: Forgemaster ⚒️ (Cocapn Fleet)
"""

import sys
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

# ─── Token Types ───────────────────────────────────────────────

class TT:
    FN = 'FN'; CONSTRAINT = 'CONSTRAINT'; REQUIRE = 'REQUIRE'
    LET = 'LET'; RETURN = 'RETURN'; IF = 'IF'; ELSE = 'ELSE'
    WHILE = 'WHILE'; AGENT = 'AGENT'; INTENT = 'INTENT'
    TRUE = 'TRUE'; FALSE = 'FALSE'; PANIC = 'PANIC'; UNREACHABLE = 'UNREACHABLE'
    IDENT = 'IDENT'; INT = 'INT'; FLOAT = 'FLOAT'
    PLUS = '+'; MINUS = '-'; STAR = '*'; SLASH = '/'; PERCENT = '%'
    EQ = '=='; NE = '!='; LT = '<'; LE = '<='; GT = '>'; GE = '>='
    AND = '&&'; OR = '||'; NOT = '!'
    ASSIGN = '='; ARROW = '->'; AS = 'AS'
    LPAREN = '('; RPAREN = ')'; LBRACE = '{'; RBRACE = '}'
    LBRACKET = '['; RBRACKET = ']'
    SEMI = ';'; COMMA = ','; COLON = ':'; BANG = '!'
    EOF = 'EOF'
    # Type keywords
    I32 = 'I32'; F32 = 'F32'; VEC9 = 'VEC9'; VOID = 'VOID'

KEYWORDS = {
    'fn': TT.FN, 'constraint': TT.CONSTRAINT, 'require': TT.REQUIRE,
    'let': TT.LET, 'return': TT.RETURN, 'if': TT.IF, 'else': TT.ELSE,
    'while': TT.WHILE, 'agent': TT.AGENT, 'intent': TT.INTENT,
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
        if self.pos < len(self.source):
            return self.source[self.pos]
        return '\0'

    def _advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
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
                while self.pos < len(self.source):
                    if self._peek() == '*' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '/':
                        self._advance(); self._advance()
                        break
                    self._advance()
            else:
                break

    def _tokenize(self):
        while self.pos < len(self.source):
            self._skip_ws_comments()
            if self.pos >= len(self.source):
                break
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
            elif ch == '<':
                self._advance()
                self.tokens.append(Token(TT.LT, '<', line, col))
            elif ch == '>':
                self._advance()
                self.tokens.append(Token(TT.GT, '>', line, col))
            elif ch == '&' and self._lookahead('&&'):
                self._advance(); self._advance()
                self.tokens.append(Token(TT.AND, '&&', line, col))
            elif ch == '|' and self._lookahead('||'):
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
            else:
                self._advance()  # skip unknown

        self.tokens.append(Token(TT.EOF, None, self.line, self.col))

    def _lookahead(self, expected: str) -> bool:
        return self.source[self.pos:self.pos + len(expected)] == expected

# ─── AST Nodes ─────────────────────────────────────────────────

@dataclass
class TypeNode:
    name: str  # 'i32', 'f32', 'vec9', 'void'

@dataclass
class FnParam:
    name: str
    type_: TypeNode

@dataclass
class FnDecl:
    name: str
    params: List[FnParam]
    return_type: TypeNode
    body: List[Any]  # statements
    is_constraint: bool = False

@dataclass
class LetStmt:
    name: str
    type_: Optional[TypeNode]
    init: Any  # expression

@dataclass
class AssignStmt:
    name: str
    value: Any

@dataclass
class ReturnStmt:
    value: Any  # expression or None

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
class IntentLit:
    components: List[float]

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

    def parse(self) -> List[FnDecl]:
        functions = []
        while self._peek().type != TT.EOF:
            functions.append(self._parse_fn_decl())
        return functions

    def _parse_fn_decl(self) -> FnDecl:
        is_constraint = False
        if self._match(TT.CONSTRAINT):
            is_constraint = True
        self._expect(TT.FN)
        name = self._expect(TT.IDENT).value
        self._expect(TT.LPAREN)
        params = []
        while self._peek().type != TT.RPAREN:
            pname = self._expect(TT.IDENT).value
            self._expect(TT.COLON)
            ptype = self._parse_type()
            params.append(FnParam(pname, ptype))
            if not self._match(TT.COMMA):
                break
        self._expect(TT.RPAREN)
        ret_type = TypeNode('void')
        if self._match(TT.ARROW):
            ret_type = self._parse_type()
        body = self._parse_block()
        return FnDecl(name, params, ret_type, body, is_constraint)

    def _parse_type(self) -> TypeNode:
        t = self._advance()
        if t.type in (TT.I32, TT.F32, TT.VEC9, TT.VOID):
            return TypeNode(t.value)
        if t.type == TT.IDENT:
            return TypeNode(t.value)
        raise SyntaxError(f"Expected type, got {t.type} at line {t.line}")

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
            # assignment or expression statement
            expr = self._parse_expr()
            if isinstance(expr, Ident) and self._match(TT.ASSIGN):
                value = self._parse_expr()
                self._expect(TT.SEMI)
                return AssignStmt(expr.name, value)
            self._expect(TT.SEMI)
            return ExprStmt(expr)

    def _parse_let(self) -> LetStmt:
        self._expect(TT.LET)
        name = self._expect(TT.IDENT).value
        type_ = None
        if self._match(TT.COLON):
            type_ = self._parse_type()
        self._expect(TT.ASSIGN)
        init = self._parse_expr()
        self._expect(TT.SEMI)
        return LetStmt(name, type_, init)

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

    # ─── Expression parsing (precedence climbing) ───

    def _parse_expr(self) -> Any:
        return self._parse_or()

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self._match(TT.OR):
            right = self._parse_and()
            left = BinOp('||', left, right)
        return left

    def _parse_and(self) -> Any:
        left = self._parse_equality()
        while self._match(TT.AND):
            right = self._parse_equality()
            left = BinOp('&&', left, right)
        return left

    def _parse_equality(self) -> Any:
        left = self._parse_comparison()
        while True:
            op = self._match(TT.EQ, TT.NE)
            if not op:
                break
            right = self._parse_comparison()
            left = BinOp(op.value, left, right)
        return left

    def _parse_comparison(self) -> Any:
        left = self._parse_additive()
        while True:
            op = self._match(TT.LT, TT.LE, TT.GT, TT.GE)
            if not op:
                break
            right = self._parse_additive()
            left = BinOp(op.value, left, right)
        return left

    def _parse_additive(self) -> Any:
        left = self._parse_multiplicative()
        while True:
            op = self._match(TT.PLUS, TT.MINUS)
            if not op:
                break
            right = self._parse_multiplicative()
            left = BinOp(op.value, left, right)
        return left

    def _parse_multiplicative(self) -> Any:
        left = self._parse_unary()
        while True:
            op = self._match(TT.STAR, TT.SLASH, TT.PERCENT)
            if not op:
                break
            right = self._parse_unary()
            left = BinOp(op.value, left, right)
        return left

    def _parse_unary(self) -> Any:
        if self._match(TT.MINUS):
            operand = self._parse_unary()
            return UnaryOp('-', operand)
        if self._peek().type == TT.NOT:
            # Check if this is intent![...] — if next after ! is [, don't consume
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TT.LBRACKET:
                return self._parse_postfix()
            self._advance()
            operand = self._parse_unary()
            return UnaryOp('!', operand)
        return self._parse_postfix()

    def _parse_postfix(self) -> Any:
        expr = self._parse_primary()
        if self._match(TT.AS):
            target = self._parse_type()
            return CastExpr(expr, target.name)
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
                # function call
                self._advance()
                args = []
                while self._peek().type != TT.RPAREN:
                    args.append(self._parse_expr())
                    if not self._match(TT.COMMA):
                        break
                self._expect(TT.RPAREN)
                return CallExpr(t.value, args)
            return Ident(t.value)
        elif t.type == TT.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TT.RPAREN)
            return expr
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
                if not self._match(TT.COMMA):
                    break
            self._expect(TT.RBRACKET)
            return IntentLit(components)
        else:
            raise SyntaxError(f"Unexpected token {t.type} ('{t.value}') at line {t.line}:{t.col}")


# ─── Code Generator ────────────────────────────────────────────

# FLUX registers
R0, R1, R2, R3, R4, R5, R6, R7 = range(8)
R8_RV = 8  # return value
R9_A0 = 9  # first arg
R10_A1 = 10  # second arg
R11_SP = 11  # stack pointer
R12_FP = 12  # frame pointer
R13_FL = 13  # flags
R14 = 14
R15_LR = 15  # link register

F0, F1, F2, F3, F4, F5, F6, F7 = range(8)
F8_FV = 8  # float return
F9_FA0 = 9  # first float arg
F10_FA1 = 10  # second float arg

REG_NAMES_GP = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7',
                'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']
REG_NAMES_FP = ['F0', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7',
                'F8', 'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15']

class RegAlloc:
    """Simple linear-scan register allocator for GP registers R0-R7."""
    def __init__(self):
        self.used: set = set()
        self.vars: Dict[str, int] = {}  # var_name -> register
        self.stack_slots: Dict[str, int] = {}  # var_name -> stack offset
        self.next_stack = 0

    def alloc(self, name: str) -> int:
        """Allocate a register for a variable. Spill to stack if needed."""
        if name in self.vars:
            return self.vars[name]
        for r in range(8):  # R0-R7
            if r not in self.used:
                self.used.add(r)
                self.vars[name] = r
                return r
        # Spill
        slot = self.next_stack
        self.next_stack += 1
        self.stack_slots[name] = slot
        return slot  # negative = stack

    def get(self, name: str) -> int:
        if name in self.vars:
            return self.vars[name]
        if name in self.stack_slots:
            return self.stack_slots[name]
        raise ValueError(f"Undefined variable: {name}")

    def free(self, name: str):
        if name in self.vars:
            r = self.vars.pop(name)
            self.used.discard(r)

    def alloc_temp(self) -> int:
        """Allocate a temporary register."""
        for r in range(8):
            if r not in self.used:
                self.used.add(r)
                return r
        return -1  # need stack spill

    def free_temp(self, r: int):
        self.used.discard(r)


class CodeGen:
    def __init__(self):
        self.output: List[str] = []
        self.functions: Dict[str, FnDecl] = {}
        self.func_order: List[str] = []
        self.label_counter = 0
        self.reg: RegAlloc = RegAlloc()

    def new_label(self, prefix: str = 'L') -> str:
        self.label_counter += 1
        return f'{prefix}{self.label_counter}'

    def emit(self, line: str, indent: int = 0):
        self.output.append('  ' * indent + line)

    def emit_comment(self, text: str, indent: int = 1):
        self.emit(f'; {text}', indent)

    def generate(self, functions: List[FnDecl]) -> str:
        # Register all functions
        for fn in functions:
            self.functions[fn.name] = fn
            self.func_order.append(fn.name)

        self.emit(f'; Generated by Fluxile compiler v0.1.0')
        self.emit(f'; Target: FLUX ISA v3 (FLUX-X layer)')
        self.emit('')

        for name in self.func_order:
            fn = self.functions[name]
            self._gen_function(fn)
            self.emit('')

        return '\n'.join(self.output)

    def _gen_function(self, fn: FnDecl):
        self.reg = RegAlloc()  # fresh allocator per function

        self.emit(f'FUNC {fn.name}')
        if fn.is_constraint:
            self.emit_comment(f'constraint fn — require violations trigger PANIC')

        # Prologue
        self.emit('  Push R12            ; save FP', 0)
        self.emit('  IMov R12, R11       ; FP = SP', 0)

        # Map params to registers
        for i, param in enumerate(fn.params):
            if i == 0:
                self.reg.vars[param.name] = R9_A0
                self.reg.used.add(R9_A0)
            elif i == 1:
                self.reg.vars[param.name] = R10_A1
                self.reg.used.add(R10_A1)
            else:
                # Stack param — would need load from stack
                r = self.reg.alloc(param.name)
                self.emit(f'  ; {param.name} from stack slot')

        # Generate body
        self._gen_block(fn.body, fn)

        # Epilogue (in case function didn't return explicitly)
        self.emit('  IMov R11, R12       ; restore SP', 0)
        self.emit('  Pop R12             ; restore FP', 0)
        self.emit('  Ret', 0)
        self.emit('ENDFUNC')

    def _gen_block(self, stmts: List[Any], fn: FnDecl):
        for stmt in stmts:
            self._gen_stmt(stmt, fn)

    def _gen_stmt(self, stmt: Any, fn: FnDecl):
        if isinstance(stmt, LetStmt):
            self._gen_let(stmt, fn)
        elif isinstance(stmt, AssignStmt):
            self._gen_assign(stmt, fn)
        elif isinstance(stmt, ReturnStmt):
            self._gen_return(stmt, fn)
        elif isinstance(stmt, IfStmt):
            self._gen_if(stmt, fn)
        elif isinstance(stmt, WhileStmt):
            self._gen_while(stmt, fn)
        elif isinstance(stmt, ConstraintStmt):
            self._gen_constraint(stmt, fn)
        elif isinstance(stmt, RequireStmt):
            self._gen_require(stmt, fn)
        elif isinstance(stmt, ExprStmt):
            if stmt.expr is not None:
                tmp = self.reg.alloc_temp()
                self._gen_expr_to_reg(stmt.expr, tmp, fn)
                self.reg.free_temp(tmp)
        else:
            self.emit_comment(f'; unhandled stmt: {type(stmt).__name__}')

    def _gen_let(self, stmt: LetStmt, fn: FnDecl):
        r = self.reg.alloc(stmt.name)
        if r < 0:
            # Stack allocation
            self.emit_comment(f'let {stmt.name} on stack (spill)')
            return
        self.emit_comment(f'let {stmt.name} = {self._expr_str(stmt.init)}')
        self._gen_expr_to_reg(stmt.init, r, fn)

    def _gen_assign(self, stmt: AssignStmt, fn: FnDecl):
        r = self.reg.get(stmt.name)
        if r < 0:
            self.emit_comment(f'; assign {stmt.name} to stack (TODO)')
            return
        self.emit_comment(f'{stmt.name} = {self._expr_str(stmt.value)}')
        self._gen_expr_to_reg(stmt.value, r, fn)

    def _gen_return(self, stmt: ReturnStmt, fn: FnDecl):
        if stmt.value is not None:
            self.emit_comment(f'return {self._expr_str(stmt.value)}')
            ret_type = fn.return_type.name if fn.return_type else 'i32'
            if ret_type == 'f32':
                self._gen_expr_to_freg(stmt.value, F8_FV, fn)
            else:
                self._gen_expr_to_reg(stmt.value, R8_RV, fn)
        self.emit('  IMov R11, R12       ; restore SP')
        self.emit('  Pop R12             ; restore FP')
        self.emit('  Ret')

    def _gen_if(self, stmt: IfStmt, fn: FnDecl):
        else_label = self.new_label('else')
        end_label = self.new_label('endif')

        self.emit_comment(f'if ...')
        cond_r = self.reg.alloc_temp()
        self._gen_expr_to_reg(stmt.condition, cond_r, fn)

        if stmt.else_body:
            self.emit(f'  JumpIfNot {REG_NAMES_GP[cond_r]}, {else_label}')
        else:
            self.emit(f'  JumpIfNot {REG_NAMES_GP[cond_r]}, {end_label}')

        self._gen_block(stmt.then_body, fn)
        if stmt.else_body:
            self.emit(f'  Jump {end_label}')
            self.emit(f'{else_label}:')
            self._gen_block(stmt.else_body, fn)
        self.emit(f'{end_label}:')
        self.reg.free_temp(cond_r)

    def _gen_while(self, stmt: WhileStmt, fn: FnDecl):
        loop_label = self.new_label('while')
        end_label = self.new_label('endwhile')

        self.emit(f'{loop_label}:')
        self.emit_comment('while ...')
        cond_r = self.reg.alloc_temp()
        self._gen_expr_to_reg(stmt.condition, cond_r, fn)
        self.emit(f'  JumpIfNot {REG_NAMES_GP[cond_r]}, {end_label}')
        self._gen_block(stmt.body, fn)
        self.emit(f'  Jump {loop_label}')
        self.emit(f'{end_label}:')
        self.reg.free_temp(cond_r)

    def _gen_constraint(self, stmt: ConstraintStmt, fn: FnDecl):
        self.emit_comment(f'constraint {self._expr_str(stmt.expr)}')
        # Evaluate constraint expression to a register
        # If result is 0 (false), PANIC
        r = self.reg.alloc_temp()
        self._gen_expr_to_reg(stmt.expr, r, fn)
        panic_label = self.new_label('panic')
        ok_label = self.new_label('ok')
        self.emit(f'  JumpIfNot {REG_NAMES_GP[r]}, {panic_label}')
        self.emit(f'  Jump {ok_label}')
        self.emit(f'{panic_label}:')
        self.emit('  Panic               ; constraint violation!')
        self.emit(f'{ok_label}:')
        self.reg.free_temp(r)

    def _gen_require(self, stmt: RequireStmt, fn: FnDecl):
        # Same as constraint
        self._gen_constraint(ConstraintStmt(stmt.expr), fn)

    def _expr_str(self, expr: Any) -> str:
        """Human-readable expression string for comments."""
        if isinstance(expr, IntLit):
            return str(expr.value)
        elif isinstance(expr, FloatLit):
            return str(expr.value)
        elif isinstance(expr, BoolLit):
            return str(expr.value).lower()
        elif isinstance(expr, Ident):
            return expr.name
        elif isinstance(expr, BinOp):
            return f'({self._expr_str(expr.left)} {expr.op} {self._expr_str(expr.right)})'
        elif isinstance(expr, UnaryOp):
            return f'({expr.op}{self._expr_str(expr.operand)})'
        elif isinstance(expr, CallExpr):
            args = ', '.join(self._expr_str(a) for a in expr.args)
            return f'{expr.name}({args})'
        elif isinstance(expr, CastExpr):
            return f'{self._expr_str(expr.expr)} as {expr.target_type}'
        else:
            return '?'

    def _is_float_expr(self, expr: Any) -> bool:
        """Heuristic: does this expression produce a float?"""
        if isinstance(expr, FloatLit):
            return True
        if isinstance(expr, BinOp):
            return self._is_float_expr(expr.left) or self._is_float_expr(expr.right)
        if isinstance(expr, CallExpr):
            float_builtins = {'round', 'sqrt', 'abs', 'min', 'max', 'sin', 'cos', 'exp', 'log'}
            if expr.name in float_builtins:
                return True
            # Check if function returns f32
            if expr.name in self.functions:
                return self.functions[expr.name].return_type.name == 'f32'
        if isinstance(expr, CastExpr):
            return expr.target_type == 'f32'
        return False

    def _gen_expr_to_reg(self, expr: Any, target: int, fn: FnDecl):
        """Generate code for expression, result in GP register target."""
        rn = REG_NAMES_GP[target]

        if isinstance(expr, IntLit):
            self.emit(f'  IMov {rn}, {expr.value}')

        elif isinstance(expr, FloatLit):
            # Load float immediate — store as int bits (simplified)
            # In real impl, we'd use a float constant pool
            self.emit(f'  ; load float {expr.value}')
            self.emit(f'  FMov {REG_NAMES_FP[target]}, {expr.value}')

        elif isinstance(expr, BoolLit):
            self.emit(f'  IMov {rn}, {1 if expr.value else 0}')

        elif isinstance(expr, Ident):
            src = self.reg.get(expr.name)
            if src < 0:
                self.emit(f'  ; load {expr.name} from stack')
            else:
                self.emit(f'  IMov {rn}, {REG_NAMES_GP[src]}')

        elif isinstance(expr, BinOp):
            self._gen_binop_to_reg(expr, target, fn)

        elif isinstance(expr, UnaryOp):
            if expr.op == '-':
                self._gen_expr_to_reg(expr.operand, target, fn)
                self.emit(f'  INeg {rn}, {rn}, {rn}')
            elif expr.op == '!':
                self._gen_expr_to_reg(expr.operand, target, fn)
                self.emit(f'  INot {rn}, {rn}, {rn}')

        elif isinstance(expr, CallExpr):
            self._gen_call(expr, target, fn)

        elif isinstance(expr, CastExpr):
            self._gen_expr_to_reg(expr.expr, target, fn)
            if expr.target_type == 'f32':
                self.emit(f'  IToF {REG_NAMES_FP[target]}, {REG_NAMES_GP[target]}, 0')
            elif expr.target_type == 'i32':
                self.emit(f'  FToI {rn}, {REG_NAMES_FP[target]}, 0')

        else:
            self.emit(f'  ; unhandled expr: {type(expr).__name__}')

    def _gen_expr_to_freg(self, expr: Any, target: int, fn: FnDecl):
        """Generate code for expression, result in FP register target."""
        fn_name = REG_NAMES_FP[target]

        if isinstance(expr, FloatLit):
            self.emit(f'  FMov {fn_name}, {expr.value}')

        elif isinstance(expr, BinOp):
            self._gen_binop_to_freg(expr, target, fn)

        elif isinstance(expr, CallExpr):
            if expr.name in ('round', 'sqrt', 'abs', 'sin', 'cos', 'exp', 'log', 'floor', 'ceil'):
                self._gen_builtin_float(expr, target, fn)
            elif expr.name in self.functions:
                self._gen_call(expr, target, fn)
            else:
                self.emit(f'  ; unhandled float call: {expr.name}')

        elif isinstance(expr, Ident):
            src = self.reg.get(expr.name)
            if src is not None and src >= 0:
                self.emit(f'  FMov {fn_name}, {REG_NAMES_FP[src]}')

        elif isinstance(expr, CastExpr):
            if expr.target_type == 'f32':
                # int to float
                tmp = self.reg.alloc_temp()
                self._gen_expr_to_reg(expr.operand, tmp, fn)
                self.emit(f'  IToF {fn_name}, {REG_NAMES_GP[tmp]}, 0')
                self.reg.free_temp(tmp)
            else:
                self._gen_expr_to_freg(expr.operand, target, fn)

        else:
            self.emit(f'  ; unhandled fexpr: {type(expr).__name__}')

    def _gen_binop_to_reg(self, expr: BinOp, target: int, fn: FnDecl):
        rn = REG_NAMES_GP[target]
        left_r = self.reg.alloc_temp()
        right_r = self.reg.alloc_temp()

        self._gen_expr_to_reg(expr.left, left_r, fn)
        self._gen_expr_to_reg(expr.right, right_r, fn)

        ln = REG_NAMES_GP[left_r]
        rgn = REG_NAMES_GP[right_r]

        op_map = {
            '+': 'IAdd', '-': 'ISub', '*': 'IMul', '/': 'IDiv', '%': 'IMod',
            '==': 'ICmpEq', '!=': 'ICmpNe', '<': 'ICmpLt', '<=': 'ICmpLe',
            '>': 'ICmpGt', '>=': 'ICmpGe',
            '&': 'IAnd', '|': 'IOr', '^': 'IXor',
        }

        if expr.op in op_map:
            self.emit(f'  {op_map[expr.op]} {rn}, {ln}, {rgn}')
        elif expr.op == '&&':
            # Short-circuit: if left is 0, result is 0
            self.emit(f'  ICmpEq {rn}, {ln}, 0')
            skip = self.new_label('and_skip')
            self.emit(f'  JumpIfNot {rn}, {skip}')
            self.emit(f'  ICmpEq {rn}, {rgn}, 0')
            self.emit(f'  JumpIfNot {rn}, {skip}')
            self.emit(f'  IMov {rn}, 1')
            self.emit(f'  Jump {skip}_end')
            self.emit(f'{skip}:')
            self.emit(f'  IMov {rn}, 0')
            self.emit(f'{skip}_end:')
        elif expr.op == '||':
            self.emit(f'  ICmpNe {rn}, {ln}, 0')
            skip = self.new_label('or_skip')
            self.emit(f'  JumpIfNot {rn}, {skip}')
            self.emit(f'  IMov {rn}, 1')
            end = self.new_label('or_end')
            self.emit(f'  Jump {end}')
            self.emit(f'{skip}:')
            self.emit(f'  ICmpNe {rn}, {rgn}, 0')
            self.emit(f'{end}:')
        else:
            self.emit(f'  ; unknown int binop: {expr.op}')

        self.reg.free_temp(left_r)
        self.reg.free_temp(right_r)

    def _gen_binop_to_freg(self, expr: BinOp, target: int, fn: FnDecl):
        fn_name = REG_NAMES_FP[target]
        left_r = self.reg.alloc_temp()
        right_r = self.reg.alloc_temp()

        self._gen_expr_to_freg(expr.left, left_r, fn)
        self._gen_expr_to_freg(expr.right, right_r, fn)

        fl = REG_NAMES_FP[left_r]
        fr = REG_NAMES_FP[right_r]

        op_map = {
            '+': 'FAdd', '-': 'FSub', '*': 'FMul', '/': 'FDiv',
            '==': 'FCmpEq', '!=': 'FCmpNe', '<': 'FCmpLt', '<=': 'FCmpLe',
            '>': 'FCmpGt', '>=': 'FCmpGe',
        }

        if expr.op in op_map:
            self.emit(f'  {op_map[expr.op]} {fn_name}, {fl}, {fr}')
        else:
            self.emit(f'  ; unknown float binop: {expr.op}')

        self.reg.free_temp(left_r)
        self.reg.free_temp(right_r)

    def _gen_builtin_float(self, expr: CallExpr, target: int, fn: FnDecl):
        """Generate code for float builtins (round, sqrt, abs, etc.)."""
        fn_name = REG_NAMES_FP[target]
        arg_r = self.reg.alloc_temp()

        builtin_map = {
            'round': 'FRound', 'sqrt': 'FSqrt', 'abs': 'FAbs',
            'sin': 'FSin', 'cos': 'FCos', 'exp': 'FExp', 'log': 'FLog',
            'floor': 'FFloor', 'ceil': 'FCeil',
        }

        if expr.name in builtin_map and len(expr.args) == 1:
            self._gen_expr_to_freg(expr.args[0], arg_r, fn)
            self.emit(f'  {builtin_map[expr.name]} {fn_name}, {REG_NAMES_FP[arg_r]}, 0')
        elif expr.name == 'min' and len(expr.args) == 2:
            self._gen_expr_to_freg(expr.args[0], arg_r, fn)
            arg2_r = self.reg.alloc_temp()
            self._gen_expr_to_freg(expr.args[1], arg2_r, fn)
            self.emit(f'  FMin {fn_name}, {REG_NAMES_FP[arg_r]}, {REG_NAMES_FP[arg2_r]}')
            self.reg.free_temp(arg2_r)
        elif expr.name == 'max' and len(expr.args) == 2:
            self._gen_expr_to_freg(expr.args[0], arg_r, fn)
            arg2_r = self.reg.alloc_temp()
            self._gen_expr_to_freg(expr.args[1], arg2_r, fn)
            self.emit(f'  FMax {fn_name}, {REG_NAMES_FP[arg_r]}, {REG_NAMES_FP[arg2_r]}')
            self.reg.free_temp(arg2_r)
        else:
            self.emit(f'  ; unknown float builtin: {expr.name}')

        self.reg.free_temp(arg_r)

    def _gen_call(self, expr: CallExpr, target: int, fn: FnDecl):
        """Generate code for function calls."""
        fn_name = REG_NAMES_GP[target]

        # Built-in int functions
        if expr.name == 'panic':
            self.emit('  Panic')
            return
        if expr.name == 'unreachable':
            self.emit('  Unreachable')
            return

        if expr.name in ('abs', 'min', 'max') and expr.args:
            if expr.name == 'abs' and len(expr.args) == 1:
                arg_r = self.reg.alloc_temp()
                self._gen_expr_to_reg(expr.args[0], arg_r, fn)
                self.emit(f'  IAbs {fn_name}, {REG_NAMES_GP[arg_r]}, 0')
                self.reg.free_temp(arg_r)
                return
            elif expr.name == 'min' and len(expr.args) == 2:
                a1 = self.reg.alloc_temp()
                a2 = self.reg.alloc_temp()
                self._gen_expr_to_reg(expr.args[0], a1, fn)
                self._gen_expr_to_reg(expr.args[1], a2, fn)
                self.emit(f'  IMin {fn_name}, {REG_NAMES_GP[a1]}, {REG_NAMES_GP[a2]}')
                self.reg.free_temp(a1)
                self.reg.free_temp(a2)
                return
            elif expr.name == 'max' and len(expr.args) == 2:
                a1 = self.reg.alloc_temp()
                a2 = self.reg.alloc_temp()
                self._gen_expr_to_reg(expr.args[0], a1, fn)
                self._gen_expr_to_reg(expr.args[1], a2, fn)
                self.emit(f'  IMax {fn_name}, {REG_NAMES_GP[a1]}, {REG_NAMES_GP[a2]}')
                self.reg.free_temp(a1)
                self.reg.free_temp(a2)
                return

        # User-defined function call
        if expr.name in self.functions:
            callee = self.functions[expr.name]

            # Save caller-saved registers that we're using
            saved = []
            for vname, vr in list(self.reg.vars.items()):
                if vr < 8:  # R0-R7 are caller-saved
                    self.emit(f'  Push {REG_NAMES_GP[vr]}    ; save {vname}')
                    saved.append((vname, vr))

            # Load arguments
            for i, arg in enumerate(expr.args):
                if i == 0:
                    if callee.params[i].type_.name == 'f32':
                        self._gen_expr_to_freg(arg, F9_FA0, fn)
                    else:
                        self._gen_expr_to_reg(arg, R9_A0, fn)
                elif i == 1:
                    if callee.params[i].type_.name == 'f32':
                        self._gen_expr_to_freg(arg, F10_FA1, fn)
                    else:
                        self._gen_expr_to_reg(arg, R10_A1, fn)
                else:
                    self.emit(f'  ; stack arg {i}')

            self.emit(f'  Call {expr.name}')

            # Move return value to target
            if callee.return_type.name == 'f32':
                self.emit(f'  FMov {REG_NAMES_FP[target]}, F8')
            else:
                self.emit(f'  IMov {fn_name}, R8')

            # Restore saved registers
            for vname, vr in reversed(saved):
                self.emit(f'  Pop {REG_NAMES_GP[vr]}    ; restore {vname}')
        else:
            self.emit(f'  ; unknown function: {expr.name}')


# ─── Main ──────────────────────────────────────────────────────

def compile_file(filepath: str) -> str:
    with open(filepath, 'r') as f:
        source = f.read()

    lexer = Lexer(source)
    parser = Parser(lexer.tokens)
    functions = parser.parse()
    codegen = CodeGen()
    assembly = codegen.generate(functions)
    return assembly


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 compiler.py <file.fx>")
        sys.exit(1)

    filepath = sys.argv[1]
    try:
        asm = compile_file(filepath)
        print(asm)
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
