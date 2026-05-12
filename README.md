# Forgemaster Workspace

Monorepo for the Forgemaster ⚒️ constraint-theory fleet agent (Cocapn). 57 repos, 57+ submodules, 9 AI agents.

---

## Architecture

```
GUARD DSL
    │
    ▼
guardc  ─── GUARD → FLUX verified compiler
    │
    ▼
FLUX ISA ── stack-based bytecode VM
    │
    ├──▶ CPU  (flux-vm runtime)
    ├──▶ GPU  (CUDA / Vulkan / WebGPU)
    └──▶ FPGA (SystemVerilog, DO-254)
```

Fleet consensus and orchestration layer:

```
holonomy-consensus ── zero-holonomy fleet state
flux-lucid         ── ecosystem orchestrator / head-direction
flux-contracts     ── frozen trait definitions (stable ABI)
flux-verify-api    ── Ed25519-signed verification traces
zeitgeist-protocol ── FLUX transference specification
```

---

## Published Crates (16 on crates.io)

| Crate | Version | Role |
|-------|---------|------|
| [eisenstein](https://crates.io/crates/eisenstein) | 0.3.1 | Hex integer math (ℤ[ω] lattice) |
| [dodecet-encoder](https://crates.io/crates/dodecet-encoder) | 1.1.0 | 12-bit constraint state encoding |
| [holonomy-consensus](https://crates.io/crates/holonomy-consensus) | 0.1.2 | Fleet consensus protocol |
| [flux-lucid](https://crates.io/crates/flux-lucid) | 0.1.7 | Ecosystem orchestrator |
| [flux-isa](https://crates.io/crates/flux-isa) | 0.1.2 | Bytecode VM / ISA spec |
| [guardc](https://crates.io/crates/guardc) | 0.1.0 | GUARD → FLUX compiler |
| [flux-verify-api](https://crates.io/crates/flux-verify-api) | 0.1.2 | Verification API with Ed25519 |
| [flux-contracts](https://crates.io/crates/flux-contracts) | 0.1.0 | Frozen trait definitions |
| [zeitgeist-protocol](https://crates.io/crates/zeitgeist-protocol) | 0.1.0 | Transference protocol |
| [snapkit](https://crates.io/crates/snapkit) | 0.1.0 | Eisenstein snap toolkit |
| [constraint-theory-core](https://crates.io/crates/constraint-theory-core) | 2.2.0 | Core constraint library |
| [constraint-theory-llvm](https://crates.io/crates/constraint-theory-llvm) | 0.1.1 | LLVM backend |
| [constraint-theory](https://crates.io/crates/constraint-theory) | 0.1.0 | Python bindings |
| [ct-demo](https://crates.io/crates/ct-demo) | 0.3.0 | Demo / integration tests |
| flux-compiler | — | Core compiler pipeline |
| pythagorean48-codes | — | Error-correcting codes |

## PyPI (4 packages)

| Package | Version |
|---------|---------|
| constraint-theory | 0.2.0 |
| cocapn-snapkit | blocked (rate limit) |
| fleet-automation | blocked (rate limit) |
| polyformalism-a2a | pending |

## npm (1 ready, blocked)

| Package | Status |
|---------|--------|
| snapkit-js | Ready — needs OTP |

---

## Tests

279 tests passing across 7 Rust crates.

| Crate | Tests |
|-------|-------|
| dodecet-encoder | 98 |
| flux-lucid | 86 |
| plato-mud | 32 |
| holonomy-consensus | 30 |
| flux-verify-api | 19 |
| zeitgeist-protocol | 9 |
| flux-contracts | 5 |

```bash
cargo test --workspace
```

---

## Fleet

9 agents active in the Cocapn fleet: Forgemaster, Oracle1, and others.
Forgemaster is the constraint-theory specialist — compiles GUARD, manages the FLUX ISA, publishes crates.

---

## License

[Apache 2.0](./LICENSE)
