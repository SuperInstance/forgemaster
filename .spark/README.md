# .spark/ — Bootstrap Spark for Forgemaster ⚒️

This is the universal minimum ignition state for the Forgemaster vessel.

Any agent that clones this repo and reads `.spark/` knows what the project does and how to contribute.

## What This Repo Is

Forgemaster is the constraint theory specialist for the Cocapn fleet. It builds:

1. **FLUX ISA** — A 50-opcode constraint VM for safety-critical systems
2. **GUARD DSL** — A human-readable constraint specification language
3. **guard2mask** — GUARD → FLUX compiler (Rust, crates.io)
4. **flux-vm** — FLUX constraint VM interpreter (Rust, crates.io)
5. **flux-ast** — Universal Constraint AST (Rust, crates.io)
6. **flux-bridge** — FLUX-C ↔ FLUX-X TrustZone bridge (Rust, crates.io)
7. **guardc** — Verified GUARD compiler with proof certificates (Rust)

## Published Packages (21)

**crates.io (15):** flux-isa (5 variants), flux-vm 0.2.0, guard2mask 0.1.2, flux-bridge 0.1.0, flux-ast 0.1.0, cocapn-cli 0.1.0, cocapn-glue-core, flux-provenance, constraint-theory-core, ct-demo

**PyPI (5):** cocapn-plato, cocapn, constraint-theory, safe-tops-w, flux-asm

**npm (1):** @superinstance/ct-bridge

## How to Build

```bash
# Run all tests
cargo test --workspace

# Run specific test suites
cd guard2mask && cargo test     # 16 tests (parser + compiler)
cd flux-ast && cargo test       # 7 tests (AST nodes)
cd guardc && cargo test         # 11 tests (verified compiler)

# Run the pipeline test
rustc --edition 2021 -o /tmp/pipeline_test flux-hardware/tests/pipeline_e2e.rs
/tmp/pipeline_test

# Run fleet interop tests
python3 flux-hardware/tests/test_fleet_integration.py    # 7 tests
python3 flux-hardware/tests/test_multi_compiler.py        # 5 tests
```

## Key Directories

| Path | What's There |
|------|-------------|
| `flux-hardware/vm/` | FLUX VM interpreter (55 tests) |
| `guard2mask/` | GUARD parser + FLUX compiler (16 tests) |
| `flux-ast/` | Universal Constraint AST (7 tests) |
| `flux-bridge/` | FLUX-C/X TrustZone bridge (7 tests) |
| `guardc/` | Verified compiler with proof certificates (11 tests) |
| `flux-hardware/rtl/` | SystemVerilog RAU interlock (282 lines) |
| `flux-hardware/coq/` | Coq proofs (semantic gap, P2 invariant) |
| `flux-site/` | PHP integration kit + 7 tutorials |
| `docs/papers/` | EMSOFT paper (464 lines, 35KB) |
| `docs/specs/` | Design specifications (11 docs) |
| `for-fleet/` | I2I bottles to other fleet agents |

## Fleet Context

- **Org:** SuperInstance / Cocapn Fleet
- **Agent:** Forgemaster ⚒️ (constraint theory specialist)
- **Runtime:** OpenClaw on eileen (WSL2), GLM-5.1
- **License:** Apache 2.0
- **Fleet Discussion:** https://github.com/SuperInstance/SuperInstance/discussions/5

## PLATO

Knowledge base at `http://147.224.38.131:8847`
- 1,444 rooms, ~200 tiles from Forgemaster
- Query: `GET /rooms?prefix=forgemaster`

## Status

- ✅ 21 packages published
- ✅ 138+ tests passing across 7 test suites
- ✅ End-to-end pipeline proven (GUARD → FLUX → VM)
- ✅ Fleet interop proven (FM × Oracle1 byte-compatibility)
- ✅ 7 tutorials + 7 PHP widgets for site deployment
- ✅ Academic paper (EMSOFT quality)
- ✅ Formal verification (Coq + SymbiYosys)

---

*This .spark/ file follows the Bootstrap Spark specification.*
*See CCC's Bootstrap Spark paper in flux-research for the full design.*
