# Fluxile Language Specification

**Version:** 0.2.0
**Status:** Active
**Author:** Forgemaster ⚒️ (Cocapn Fleet)
**Date:** 2026-05-11
**Compiles to:** FLUX ISA v3 bytecode (FLUX-X / FLUX-C layers)

---

## 1. Design Philosophy

Fluxile is a higher-level language that compiles to FLUX ISA v3 bytecode. It sits above raw FLUX assembly the way Rust sits above LLVM IR — providing ergonomic syntax, type safety, and domain-native constructs while remaining close enough to the metal that you can reason about generated code.

### Principles

1. **Constraint-native.** Constraints are not assertions bolted on after the fact — `constraint` and `require` are first-class keywords with defined compilation semantics (constraint violations compile to `PANIC`).

2. **Agent-native.** `agent` blocks compile to FLUX A2A opcodes. No FFI, no shim layer — the language speaks fleet protocol directly.

3. **Lattice-native.** Eisenstein integer arithmetic and snapping are built-in operations with known FLUX-X lowering patterns.

4. **Intent-native.** The `intent` type is a 9-dimensional float vector that maps directly to FLUX vector registers (V0–V15). Intent operations compile to VDot, VAdd, VMul.

5. **Zero magic.** Every Fluxile construct has a defined lowering to FLUX assembly. No runtime, no GC, no hidden allocations. What you write is what executes.

---

## 2. Lexical Structure

### 2.1 Keywords

```
fn return let if else while for in match
constraint require agent tell ask wait
intent snap round sqrt abs min max
true false panic unreachable
i32 f32 vec9 void
```

### 2.2 Identifiers

Alphanumeric + underscore, starting with letter or underscore.

### 2.3 Literals

- **Integer:** `42`, `-7`, `0xFF`
- **Float:** `3.14`, `-0.5`, `1.0e10`
- **Bool:** `true`, `false`

### 2.4 Operators

| Precedence | Operators | Associativity |
|-----------|-----------|---------------|
| 1 (highest) | `()` grouping, `[]` subscript | — |
| 2 | Unary `-`, `!` | Right |
| 3 | `*`, `/`, `%` | Left |
| 4 | `+`, `-` | Left |
| 5 | `<`, `<=`, `>`, `>=` | Left |
| 6 | `==`, `!=` | Left |
| 7 | `&&` | Left |
| 8 | `\|\|` | Left |

### 2.5 Comments

- Line comments: `// ...`
- Block comments: `/* ... */`

---

## 3. Types

| Type | FLUX Mapping | Description |
|------|-------------|-------------|
| `i32` | GP register (R0–R15) | 32-bit signed integer |
| `f32` | FP register (F0–F15) | 32-bit IEEE 754 float |
| `bool` | GP register (0 or 1) | Boolean |
| `void` | — | No return value |
| `vec9` | Vector register (V0–V15) | 9-component float vector (intent) |
| `(T1, T2)` | Multiple registers | Tuple / multiple return values |

### Type Inference

`let` bindings infer types from the right-hand side. Explicit annotations override inference.

```fluxile
let x = 42;          // inferred i32
let y: f32 = 3.14;   // explicit f32
let z = x as f32;    // cast i32 → f32
```

---

## 4. Functions

### 4.1 Declaration

```fluxile
fn name(param1: type1, param2: type2) -> return_type {
    body
}
```

**FLUX lowering:**
- First two i32 params → R9 (A0), R10 (A1)
- First two f32 params → F9 (FA0), F10 (FA1)
- Extra params → stack spill
- Return value → R8 (i32) or F8 (f32)
- Body compiles with standard prologue/epilogue (Push FP, Mov FP SP, ... Ret)

### 4.2 Constraint Functions

```fluxile
constraint fn check_bounds(val: i32, min: i32, max: i32) {
    require min <= val;
    require val <= max;
}
```

**`require` semantics:** Compiles to comparison + `JumpIfNot` to `PANIC`. If the condition is false, the VM panics. This is a hard constraint violation — not recoverable.

**`constraint` keyword on a function:** Marks the function as a constraint function. The compiler adds implicit panic-on-violation epilogue and prevents fall-through.

---

## 5. Statements

### 5.1 Let Binding

```fluxile
let x = expr;          // immutable
let y: f32 = expr;     // immutable with type annotation
let mut z = expr;      // mutable
let mut w: i32 = expr; // mutable with type annotation
```

Compiles to: evaluate expr, store in allocated register or stack slot. `mut` is tracked at compile time for future mutability checks.

### 5.2 Assignment

```fluxile
x = expr;
```

Compiles to: evaluate expr, write to previously allocated location.

### 5.3 Return

```fluxile
return expr;
```

Compiles to: evaluate expr → R8 (or F8), then epilogue + `Ret`.

### 5.4 Expression Statement

```fluxile
expr;
```

Evaluate and discard result.

---

## 6. Expressions

### 6.1 Arithmetic

| Fluxile | FLUX Opcode |
|---------|-------------|
| `a + b` (i32) | `IAdd Rd, Ra, Rb` |
| `a - b` (i32) | `ISub Rd, Ra, Rb` |
| `a * b` (i32) | `IMul Rd, Ra, Rb` |
| `a / b` (i32) | `IDiv Rd, Ra, Rb` |
| `a % b` (i32) | `IMod Rd, Ra, Rb` |
| `a + b` (f32) | `FAdd Rd, Ra, Rb` |
| `a - b` (f32) | `FSub Rd, Ra, Rb` |
| `a * b` (f32) | `FMul Rd, Ra, Rb` |
| `a / b` (f32) | `FDiv Rd, Ra, Rb` |

### 6.2 Comparisons

| Fluxile | FLUX Opcode |
|---------|-------------|
| `a == b` (i32) | `ICmpEq Rd, Ra, Rb` |
| `a != b` (i32) | `ICmpNe Rd, Ra, Rb` |
| `a < b` (i32) | `ICmpLt Rd, Ra, Rb` |
| `a <= b` (i32) | `ICmpLe Rd, Ra, Rb` |
| `a > b` (i32) | `ICmpGt Rd, Ra, Rb` |
| `a >= b` (i32) | `ICmpGe Rd, Ra, Rb` |
| `a == b` (f32) | `FCmpEq Rd, Ra, Rb` |
| `a < b` (f32) | `FCmpLt Rd, Ra, Rb` |
| (etc.) | Corresponding `FCmp*` |

### 6.3 Built-in Functions

| Fluxile | FLUX Lowering |
|---------|---------------|
| `round(x)` | `FRound` |
| `sqrt(x)` | `FSqrt` |
| `abs(x)` (i32) | `IAbs` |
| `abs(x)` (f32) | `FAbs` |
| `min(a, b)` | `IMin` / `FMin` |
| `max(a, b)` | `IMax` / `FMax` |
| `vdot(a, b)` | `VDot` |
| `vadd(a, b)` | `VAdd` |
| `vmul(a, b)` | `VMul` |

### 6.4 Type Casts

```fluxile
let x = y as f32;  // IToF
let n = f as i32;  // FToI
```

---

## 7. Control Flow

### 7.1 If/Else

```fluxile
if condition {
    // then block
} else {
    // else block
}
```

Compiles to: evaluate condition, `JumpIfNot` to else block, then jump over else.

### 7.2 While Loop

```fluxile
while condition {
    body
}
```

Compiles to: label, evaluate condition, `JumpIfNot` to end, body, `Jump` back to label.

### 7.3 For Loop (Range)

```fluxile
for i in range(n) {
    body
}
for i in range(start, end) {
    body
}
```

Compiles to a `while` loop with a counter variable:
1. `i = start` (or `0`)
2. `while i < end { body; i = i + 1; }`

### 7.4 Match Expression

```fluxile
match value {
    0 => { return 1; },
    1 => { return 2; },
    _ => { return 3; },
}
```

Compiles to chained `ICmpEq` + `JumpIfNot` comparisons. Wildcard `_` arm is unconditional (always matches).

---

## 8. Constraint System

### 8.1 Inline Constraints

```fluxile
constraint a * a + b * b >= 0;
```

Compiles to: evaluate expression, compare, `JumpIfNot` to `PANIC`.

### 8.2 Require Statements

```fluxile
require condition;
```

Same as inline constraint but only for use inside `constraint fn`.

### 8.3 Constraint Functions

```fluxile
constraint fn name(params) {
    require cond1;
    require cond2;
    // implicit: if any require failed, PANIC
    // if all passed, return normally
}
```

---

## 9. Agent Blocks

### 9.1 Agent Declaration

```fluxile
agent Name {
    fn method() {
        // agent code
    }
}
```

### 9.2 A2A Operations

| Fluxile | FLUX Opcode | Semantics |
|---------|-------------|-----------|
| `tell(target, data)` | `ATell` | Fire-and-forget |
| `ask(target, query)` | `AAsk` | Blocking request-response |
| `wait(condition)` | `AWait` | Block until condition |
| `broadcast(data)` | `ABroadcast` | Send to all agents |
| `trust(agent, level)` | `ATrust` | Set trust level |
| `verify(agent)` | `AVerify` | Check trust level |
| `subscribe(channel)` | `ASubscribe` | Join channel |
| `delegate(agent, code)` | `ADelegate` | Remote execution |

### 9.3 Intent Literals

```fluxile
let i = intent![0.8, 0.3, 0.5, 0.1, 0.9, 0.2, 0.4, 0.7, 0.6];
```

Compiles to: 9 `VStore` operations loading components into a vector register.

---

## 10. Eisenstein Operations

### 10.1 Snap

```fluxile
let (a, b) = snap(x, y);
```

**Algorithm:**
1. `a = round(x)`
2. `b = round(y - a * 0.5)`
3. Verify `a + b*ω` lies on Eisenstein lattice

**FLUX lowering:** `FRound`, `FSub`, `FMul`, constraint check via `FCmpGt` + `PANIC`.

---

## 11. Compilation Pipeline

```
Fluxile Source (.fx)
       ↓
   Lexer (tokens)
       ↓
   Parser (AST)
       ↓
   Type Checker
       ↓
   IR Generation (FLAT IR)
       ↓
   Register Allocation (linear scan)
       ↓
   Code Emission (FLUX assembly text)
       ↓
   FLUX ISA v3 Assembly (.fluxasm)
```

---

## 12. Example Programs

### Factorial

```fluxile
fn factorial(n: i32) -> i32 {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}
```

### Eisenstein Snap

```fluxile
fn eisenstein_snap(x: f32, y: f32) -> (i32, i32) {
    let a = round(x) as i32;
    let b = round(y - x * 0.5) as i32;
    constraint a * a + b * b >= 0;
    return (a, b);
}
```

### Constraint Check

```fluxile
constraint fn check_bounds(val: i32, min: i32, max: i32) {
    require min <= val;
    require val <= max;
}

fn test() -> i32 {
    let x = 42;
    check_bounds(x, 0, 100);
    return x;
}
```

### Intent Alignment

```fluxile
fn cosine_similarity(a: vec9, b: vec9) -> f32 {
    let dot = vdot(a, b);
    let norm_a = sqrt(vdot(a, a));
    let norm_b = sqrt(vdot(b, b));
    constraint norm_a > 0 && norm_b > 0;
    return dot / (norm_a * norm_b);
}
```

---

## 13. Compilation Pipeline

```
Fluxile Source (.fx)
       ↓
   Lexer (tokens)
       ↓
   Parser (AST)
       ↓
   IR Builder (FLAT IR)
       ↓
   Optimization Passes:
     - Constant Folding
     - Strength Reduction (x*2 → x<<1, x*4 → x<<2, x/2 → x>>1)
     - Dead Code Elimination
     - Peephole Optimization
       ↓
   Register Allocation (graph coloring + coalescing)
       ↓
   Code Emission (FLUX assembly, FLUX-X or FLUX-C layer)
       ↓
   FLUX ISA v3 Assembly (.fluxasm)
```

### Optimization Levels

- **Level 0:** No optimization — direct lowering
- **Level 1:** Basic constant folding + DCE
- **Level 2 (default):** Full pipeline — folding, strength reduction, DCE, peephole, multi-pass

### Register Allocation

- Chaitin-Briggs graph coloring with copy coalescing
- 8 GP registers (R0–R7), 8 FP registers (F0–F7)
- Interference graph built via backward liveness analysis
- Move coalescing merges non-interfering copy pairs
- Automatic stack spilling when all registers are live

### Constraint Compilation (FLUX-C)

`constraint fn` functions compile to the FLUX-C layer:
- Stack-based evaluation for deterministic verification
- `require` violations compile to `PANIC`
- Can be independently verified without executing function body
- Separately emitted bytecode for safety-critical auditing

---

*Fluxile: Forge high-level intent into low-level FLUX.*
