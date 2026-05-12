# flux-isa — FLUX Instruction Set Architecture

**Stack-based constraint compilation VM with bytecode encoding.**

Published on crates.io as `flux-isa` v0.1.2.

## What It Is

The FLUX ISA defines a minimal stack-based virtual machine for executing constraint checks. It's designed so that constraint programs can be compiled once and executed anywhere — GPU, CPU, FPGA, browser, or bare metal.

## Architecture (1032 lines, 5 modules)

| Module | Lines | What It Does |
|--------|-------|-------------|
| `opcode.rs` | 189 | 43-opcode instruction set (cannot loop forever) |
| `bytecode.rs` | 253 | Binary encoding and decoding |
| `instruction.rs` | 90 | Instruction representation |
| `vm.rs` | 438 | Stack-based virtual machine execution |
| `error.rs` | 45 | Error types |

## Instruction Set

The ISA has 43 opcodes covering:

- **Stack operations:** PUSH, POP, DUP, SWAP
- **Arithmetic:** ADD, SUB, MUL, DIV, MOD
- **Comparison:** EQ, NEQ, LT, GT, LTE, GTE
- **Constraint checks:** RANGE, RATE_OF_CHANGE, AND, OR, NOT
- **Control:** HALT, NOP, JUMP (bounded — cannot loop forever)
- **I/O:** LOAD, STORE, EMIT

The key design constraint: **the ISA cannot express infinite loops.** Every FLUX program terminates. This is a safety property required for certification (DO-178C, ISO 26262).

## Usage

```rust,ignore
use flux_isa::{Vm, Bytecode, Opcode};

let bytecode = Bytecode::new()
    .push(42.0)
    .push(0.0)
    .push(100.0)
    .opcode(Opcode::Range)
    .opcode(Opcode::Halt);

let mut vm = Vm::new();
let result = vm.execute(&bytecode)?;
```

## Bytecode Format

Each instruction is 1-5 bytes:
- 1 byte: opcode
- 0-4 bytes: immediate operand (f32)

Total bytecode for a typical constraint check: 5-20 bytes. Fits in a single cache line.

## Performance

The VM executes constraint checks at:
- Scalar: ~500M checks/sec (Rust, single core)
- GPU batched: ~62.2B checks/sec (RTX 4050, via CUDA kernel)
- FPGA: Design-in phase

## Ecosystem

- **guardc** — Compiler from GUARD DSL → FLUX bytecode
- **flux-vm** — Alternative VM implementation with streaming
- **flux-compiler** — Alternative compilation pipeline
- **constraint-theory-core** — The constraint math library

## License

Apache-2.0
