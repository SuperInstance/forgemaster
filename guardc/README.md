# guardc — GUARD → FLUX Verified Compiler

**Compiles GUARD constraint specifications to verified FLUX bytecode.**

GUARD is a domain-specific language for specifying safety constraints (like GD&T for software). `guardc` compiles GUARD programs into FLUX ISA bytecode that can execute on any FLUX-compatible runtime — GPU, CPU, FPGA, or browser.

## Architecture (2541 lines, 9 modules)

```
GUARD Source (DSL)
      ↓
   AST (ast.rs, 252 lines)
      ↓
   CIR — Constraint IR (cir.rs, 431 lines)
      ↓
   LCIR — Lowered CIR (lcir.rs, 263 lines)
      ↓
   Lowering (lower.rs, 635 lines)
      ↓
   Codegen → FLUX Bytecode (codegen.rs, 355 lines)
      ↓
   Proof Verification (proof.rs, 401 lines)
      ↓
   FLUX ISA Binary
```

### Pipeline Stages

| Stage | Module | Lines | What It Does |
|-------|--------|-------|-------------|
| Parse | `ast.rs` | 252 | Parse GUARD DSL into abstract syntax tree |
| Constraint IR | `cir.rs` | 431 | High-level constraint representation |
| Lowered IR | `lcir.rs` | 263 | Lowered to primitive operations |
| Lowering | `lower.rs` | 635 | CIR → LCIR transformation |
| Code Generation | `codegen.rs` | 355 | LCIR → FLUX bytecode |
| Proof | `proof.rs` | 401 | Verify compiled output matches specification |
| Compiler | `compiler.rs` | 91 | Top-level pipeline orchestration |
| Errors | `error.rs` | 79 | Error types and diagnostics |

### Verification

The proof module verifies that the compiled FLUX bytecode is a faithful translation of the original GUARD specification. This is the compilation step that makes constraint theory certifiable for DO-178C and ISO 26262.

## Usage

```rust,ignore
use guardc::Compiler;

let source = r#"
    GUARD RANGE(temperature, 0, 100)
    GUARD RATE_OF_CHANGE(temperature, 5)
"#;

let bytecode = Compiler::compile(source)?;
// bytecode can now execute on any FLUX VM
```

## Dependencies

- `flux-isa` — The FLUX instruction set and bytecode format

## Ecosystem

- **flux-isa** — Defines the bytecode format that guardc targets
- **flux-vm** — Executes the bytecode guardc produces
- **flux-compiler** — Alternative compilation pipeline
- **constraint-theory-core** — The constraint math library

## License

MIT OR Apache-2.0
