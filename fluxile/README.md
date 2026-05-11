# Fluxile ⚒️

**A higher-level language that compiles to FLUX ISA v3 bytecode.**

## What is Fluxile?

Fluxile is a Rust-like language designed for the Cocapn multi-agent fleet. It compiles down to FLUX ISA v3 assembly, providing:

- **Constraint-native syntax** — `constraint` and `require` keywords compile to PANIC-on-violation
- **Agent-native blocks** — `agent` declarations with A2A operations (tell, ask, wait, broadcast)
- **Lattice-native math** — `snap` for Eisenstein integer snapping
- **Intent-native types** — `vec9` / `intent![]` for 9D semantic vectors
- **Zero magic** — every construct has a defined FLUX assembly lowering

## Quick Start

```bash
# Compile a Fluxile program to FLUX assembly
python3 compiler.py examples/factorial.fx

# See the generated assembly
python3 compiler.py examples/eisenstein_snap.fx

# Run all examples
for f in examples/*.fx; do echo "=== $f ==="; python3 compiler.py "$f"; echo; done
```

## Example

```fluxile
fn factorial(n: i32) -> i32 {
    if n <= 1 {
        return 1;
    }
    return n * factorial(n - 1);
}
```

Compiles to:

```fluxasm
; fn factorial(n: i32) -> i32
FUNC factorial
  Push R12              ; save FP
  IMov R12, R11         ; FP = SP
  ; n is in R9 (A0)
  ICmpLe R0, R9, 1      ; R0 = (n <= 1)
  JumpIfNot R0, +5      ; skip to else
  IMov R8, 1            ; return 1
  IMov R11, R12         ; restore SP
  Pop R12               ; restore FP
  Ret
  ; else: n * factorial(n-1)
  ISub R0, R9, 1        ; R0 = n - 1
  IMov R9, R0           ; A0 = n-1
  Call factorial         ; recursive call
  IMul R8, R9, R8       ; return n * factorial(n-1)
  IMov R11, R12
  Pop R12
  Ret
ENDFUNC
```

## Language Features

| Feature | Keyword | FLUX Lowering |
|---------|---------|---------------|
| Constraints | `constraint expr;` | Compare + JumpIfNot → PANIC |
| Require | `require cond;` | Same as constraint |
| Agent ops | `tell`, `ask`, `wait` | ATell, AAsk, AWait |
| Intent vectors | `intent![...]` | VStore ×9 |
| Snap | `snap(x, y)` | FRound + constraint check |
| Built-ins | `round`, `sqrt`, `abs` | FRound, FSqrt, IAbs/FAbs |

## Architecture

```
Fluxile Source (.fx)
    → Lexer → Parser → AST
    → Type Checker
    → IR (flat instructions)
    → Register Allocator (linear scan)
    → FLUX Assembly (.fluxasm)
```

## Files

| File | Description |
|------|-------------|
| `SPEC.md` | Language specification |
| `compiler.py` | Proof-of-concept compiler (Python) |
| `examples/*.fx` | Example Fluxile programs |
| `README.md` | This file |

## Design Philosophy

Fluxile follows the Cocapn principle: **ship first, iterate later.**

This is a proof-of-concept compiler. It handles:
- ✅ Function declarations and calls (including recursive)
- ✅ Let bindings and assignments
- ✅ Arithmetic expressions (i32 and f32)
- ✅ If/else and while loops
- ✅ Comparison and boolean operators
- ✅ Constraint and require statements
- ✅ Built-in math functions (round, sqrt, abs, min, max)
- ✅ Type casts (i32 ↔ f32)
- ✅ Register allocation with stack spilling

Not yet:
- ❌ Agent blocks (AST support only, no codegen)
- ❌ Vector/intent types (AST support only)
- ❌ Match expressions
- ❌ Optimizations

## License

Part of the Cocapn Fleet. Internal use.

---

*Fluxile: Forge high-level intent into low-level FLUX.*
