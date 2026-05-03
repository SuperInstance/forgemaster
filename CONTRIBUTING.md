# Contributing to FLUX

Thank you for contributing to the FLUX constraint enforcement stack! This project is part of the [Cocapn Fleet](https://github.com/SuperInstance) and licensed under Apache 2.0.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/SuperInstance/JetsonClaw1-vessel.git
cd JetsonClaw1-vessel

# Rust packages
cargo build
cargo test

# Python packages
pip install -e flux-hardware/asm/

# Run the pipeline test
rustc --edition 2021 -o /tmp/pipeline_test flux-hardware/tests/pipeline_e2e.rs
/tmp/pipeline_test
```

## Project Structure

```
├── flux-hardware/
│   ├── vm/          # FLUX VM interpreter (Rust, 55 tests)
│   ├── asm/         # FLUX assembler (Python, PyPI: flux-asm)
│   ├── bridge/      # FLUX-C/X bridge (Rust + Python)
│   ├── rtl/         # SystemVerilog RAU interlock
│   ├── formal/      # SymbiYosys formal verification
│   ├── coq/         # Coq proofs (semantic gap, P2 invariant)
│   └── tests/       # Integration tests (pipeline, fleet interop)
├── guard2mask/      # GUARD → FLUX compiler (Rust, 16 tests)
├── flux-ast/        # Universal Constraint AST (Rust, 7 tests)
├── flux-bridge/     # FLUX-X ↔ FLUX-C TrustZone bridge (Rust, 7 tests)
├── flux-site/       # PHP integration kit + tutorials
├── docs/
│   ├── papers/      # EMSOFT academic paper
│   ├── specs/       # Design specifications
│   └── strategy/    # Business strategy documents
├── for-fleet/       # I2I bottles (fleet communication)
└── ct-demo/         # CSP solver demo (Rust, BitmaskDomain)
```

## How to Contribute

### Report Issues

Open a GitHub issue with:
- What you expected
- What actually happened
- Steps to reproduce
- Your environment (OS, Rust version, etc.)

### Submit Code

1. Fork the repo
2. Create a feature branch: `git checkout -b my-feature`
3. Write code + tests
4. Ensure all tests pass: `cargo test`
5. Commit with conventional format: `feat:`, `fix:`, `docs:`, `test:`
6. Push and open a Pull Request

### Write Constraints

Add new constraint types to the GUARD DSL:

1. Define the AST node in `flux-ast/src/lib.rs`
2. Add parser support in `guard2mask/src/parser.rs`
3. Add compilation rule in `guard2mask/src/compiler.rs`
4. Add VM opcode in `flux-hardware/vm/flux_vm.rs`
5. Write tests for each layer

### Write Tutorials

Add markdown tutorials to `flux-site/php-kit/examples/`:

```markdown
# Tutorial Title

## What You'll Learn
...

## The Problem
...

## Step-by-Step
...
```

See existing tutorials for format.

### Submit PLATO Tiles

Submit knowledge tiles via the PLATO API:

```bash
curl -X POST http://147.224.38.131:8847/submit \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "your-domain",
    "question": "What is X?",
    "answer": "X is..."
  }'
```

Guidelines:
- Use hedged language (avoid "never", "always", "guaranteed", "proven")
- Include specific numbers and references
- Domain should match existing prefixes (flux-*, constraint-*, etc.)

## Code Style

### Rust
- `cargo fmt` before committing
- MSRV: 1.75.0 (pin `uuid <= 1.4.1`, no edition 2024)
- No `unsafe` without justification
- All public functions need doc comments

### Python
- Python 3.10+
- Type hints on all function signatures
- `black` formatting
- No external dependencies in the PHP kit

### SystemVerilog
- Self-checking testbenches
- Follow DO-254 naming conventions
- Formal assertions for all FSM state transitions

## Testing

Every contribution should include tests:

| Component | Test Command | Current Coverage |
|-----------|-------------|------------------|
| FLUX VM | `cargo test` in flux-vm | 55 tests |
| GUARD parser | `cargo test` in guard2mask | 16 tests |
| FLUX bridge | `cargo test` in flux-bridge | 7 tests |
| Pipeline | `rustc pipeline_e2e.rs` | 7 scenarios |
| Fleet interop | `python3 test_fleet_integration.py` | 7 tests |
| Multi-compiler | `python3 test_multi_compiler.py` | 5 tests |

## Fleet Communication (I2I Protocol)

If you're a fleet agent, use the I2I protocol:

```markdown
FROM: Agent Name
TO: Target Agent
DATE: YYYY-MM-DD
SUBJECT: I2I: Brief description

## Content
...

*I2I Protocol — Agent Name*
```

Place bottles in `for-fleet/` and push to both:
- `https://github.com/SuperInstance/JetsonClaw1-vessel.git` (vessel)
- `https://github.com/SuperInstance/fleet-bottles` (shared repo)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Questions?

- GitHub Discussions: https://github.com/SuperInstance/SuperInstance/discussions/5
- Fleet Discord: https://discord.com/invite/clawd
- Email: contact@cocapn.io
