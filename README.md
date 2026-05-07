# Forgemaster — FLUX Constraint Engine

**Formally verified, GPU-accelerated constraint satisfaction for safety-critical systems.**

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![crates.io](https://img.shields.io/crates/v/flux-isa.svg?label=flux-isa)](https://crates.io/crates/flux-isa)
[![crates.io](https://img.shields.io/crates/v/flux-ast.svg?label=flux-ast)](https://crates.io/crates/flux-ast)
[![crates.io](https://img.shields.io/crates/v/guard2mask.svg?label=guard2mask)](https://crates.io/crates/guard2mask)
[![npm](https://img.shields.io/npm/v/@superinstance/ct-bridge.svg)](https://www.npmjs.com/package/@superinstance/ct-bridge)

---

## Overview

FLUX is a constraint specification and execution platform built for aerospace, automotive, and industrial safety systems. It compiles GUARD DSL constraints through a formally verified pipeline to GPU, FPGA, and CPU backends — with zero drift across 278M+ evaluated test cases.

```
GUARD DSL → flux-ast → guardc → FLUX-C → guard2mask
                                        ↓
                              GPU (CUDA/Vulkan/WebGPU)
                              FPGA (SystemVerilog)
                              CPU (flux-vm)
```

---

## Published Crates

| Crate | Version | Description |
|-------|---------|-------------|
| [flux-isa](https://crates.io/crates/flux-isa) | ![](https://img.shields.io/crates/v/flux-isa.svg) | Stack-based constraint VM — bytecode encoding and ISA spec |
| [flux-ast](https://crates.io/crates/flux-ast) | ![](https://img.shields.io/crates/v/flux-ast.svg) | Universal Constraint AST — canonical semantics across all representations |
| [flux-provenance](https://crates.io/crates/flux-provenance) | ![](https://img.shields.io/crates/v/flux-provenance.svg) | Merkle provenance service for fleet verification traces |
| [flux-bridge](https://crates.io/crates/flux-bridge) | ![](https://img.shields.io/crates/v/flux-bridge.svg) | Cross-tier bridge between FLUX ISA and execution backends |
| [flux-hdc](https://crates.io/crates/flux-hdc) | ![](https://img.shields.io/crates/v/flux-hdc.svg) | Hyperdimensional computing integration for constraint encoding |
| [flux-verify-api](https://crates.io/crates/flux-verify-api) | ![](https://img.shields.io/crates/v/flux-verify-api.svg) | Natural Language Verification API with mathematical traces |
| [guard2mask](https://crates.io/crates/guard2mask) | ![](https://img.shields.io/crates/v/guard2mask.svg) | GUARD DSL → GDSII mask compiler — constraints to silicon patterns |
| [guardc](https://crates.io/crates/guardc) | ![](https://img.shields.io/crates/v/guardc.svg) | GUARD → FLUX verified compiler |
| [cocapn-cli](https://crates.io/crates/cocapn-cli) | ![](https://img.shields.io/crates/v/cocapn-cli.svg) | Fleet CLI — Abyssal Terminal output formatting |
| [cocapn-glue-core](https://crates.io/crates/cocapn-glue-core) | ![](https://img.shields.io/crates/v/cocapn-glue-core.svg) | Cross-tier wire protocol unifying all FLUX ISA packages |
| [flux-lucid](https://crates.io/crates/flux-lucid) | ![](https://img.shields.io/crates/v/flux-lucid.svg) | Unified constraint theory ecosystem — CDCL, LLVM, AVX-512, GL(9) consensus |
| [eisenstein](https://crates.io/crates/eisenstein) | ![](https://img.shields.io/crates/v/eisenstein.svg) | Zero-drift hexagonal lattice constraints via Eisenstein integers |
| [holonomy-consensus](https://crates.io/crates/holonomy-consensus) | ![](https://img.shields.io/crates/v/holonomy-consensus.svg) | Zero-holonomy consensus for fleet coordination — GL(9) intent alignment |

### npm Package

| Package | Version | Description |
|---------|---------|-------------|
| [@superinstance/ct-bridge](https://www.npmjs.com/package/@superinstance/ct-bridge) | ![](https://img.shields.io/npm/v/@superinstance/ct-bridge.svg) | Constraint Theory solver bridge for Node.js — CSP compilation and FLUX execution |

---

## GitHub Repositories

| Repository | Description |
|------------|-------------|
| [flux-compiler](https://github.com/SuperInstance/flux-compiler) | Core compiler with Coq formal verification |
| [flux-vm](https://github.com/SuperInstance/flux-vm) | Virtual machine runtime for FLUX bytecode |
| [flux-hardware](https://github.com/SuperInstance/flux-hardware) | CUDA / Vulkan / WebGPU / SystemVerilog backends |
| [flux-hdc](https://github.com/SuperInstance/flux-hdc) | Hyperdimensional computing integration |
| [flux-papers](https://github.com/SuperInstance/flux-papers) | Research papers and formal write-ups |
| [flux-site](https://github.com/SuperInstance/flux-site) | Project website |
| [flux-docs](https://github.com/SuperInstance/flux-docs) | Technical documentation |

---

## Formal Verification

8 Coq theorems covering:

- Constraint soundness and completeness
- Bitmask encoding correctness (guard2mask)
- ISA operational semantics
- Provenance chain integrity

30 English mathematical proofs accompany the Coq development as readable counterparts. The full EMSOFT paper (methodology + evaluation, 864 lines) is in [`flux-papers`](https://github.com/SuperInstance/flux-papers).

---

## Hardware Backends

### GPU (CUDA / Vulkan / WebGPU)

Constraint checking kernels in [`flux-hardware`](https://github.com/SuperInstance/flux-hardware) and [`constraint-theory-core-cuda`](./constraint-theory-core-cuda/). Zero mismatches across 278M+ evaluations.

### FPGA (SystemVerilog)

DO-254 compliant SystemVerilog implementation targeting DAL-A airborne hardware. See [`flux-hardware`](https://github.com/SuperInstance/flux-hardware).

---

## Benchmarks

**Safe-TOPS/W** — a benchmark specification for safety-critical compute efficiency.

Defined in [`docs/`](./docs/) with evaluation methodology described in the EMSOFT paper.

---

## PLATO Integration

6500+ tiles integrating FLUX constraint checking into the PLATO tile ecosystem. Adapters and client code in [`plato-adapters/`](./plato-adapters/) and [`plato-client/`](./plato-client/).

---

## Architecture

```
guard-dsl/          GUARD language parser and type-checker
flux-ast/           Universal constraint AST
guardc/             Verified GUARD → FLUX compiler
flux-isa/           Bytecode ISA specification
flux-vm/            Bytecode interpreter / runtime
guard2mask/         Constraint → bitmask → GDSII pipeline
flux-hardware/      CUDA · Vulkan · WebGPU · SystemVerilog
flux-hdc/           Hyperdimensional computing backend
flux-provenance/    Merkle trace provenance
flux-verify-api/    NL verification REST API
cocapn-cli/         Fleet terminal interface
cocapn-glue-core/   Cross-tier wire protocol
plato-adapters/     PLATO tile integration
ct-bridge-npm/      Node.js constraint bridge
```

---

## Quick Start

```bash
# Rust
cargo add flux-isa flux-ast guardc

# Node.js
npm install @superinstance/ct-bridge
```

---

## License

[Apache 2.0](./LICENSE)
