# REPO-SNAP-MAP.md — SuperInstance Lego Architecture

> How every repo interconnects through standardized snap interfaces.
> Generated 2026-05-21. ~170 repos surveyed.

---

## Snap Types

| # | Snap Type | Mechanism | Direction |
|---|-----------|-----------|-----------|
| 1 | **Python Package** | `pip install` / `pyproject.toml` | Any → Python consumers |
| 2 | **Rust Crate** | `cargo add` / `Cargo.toml` | Any → Rust consumers |
| 3 | **C FFI** | `cbindgen` header (`.h`) | Rust → C/C++/CUDA/Zig/Go |
| 4 | **REST/HTTP** | API endpoints | Service → Service |
| 5 | **PLATO Tiles** | Markdown + JSONL tile format | Knowledge → Everything |
| 6 | **GUARD DSL** | `.guard` source → FLUX bytecode | Safety spec → Hardware |
| 7 | **FLUX-C Bytecode** | 43-opcode stack VM | Compiled constraints → Runtime |
| 8 | **Tensor-MIDI** | Temporal event encoding | Temporal → Rhythm/Scheduling |
| 9 | **I2I Protocol** | Priority-routed messages | Agent ↔ Agent |
| 10 | **Wire Protocol** | `#![no_std]` binary frames | Tier → Tier (embedded ↔ cloud) |

---

## Resolution Stack

Each snap operates at a specific resolution — the granularity at which it enforces meaning:

```
┌─────────────────────────────────────────────────────────┐
│  HUMAN-LEVEL   A2UI, Telegram, natural language          │
│  Resolution: agent identity, intent, feedback             │
├─────────────────────────────────────────────────────────┤
│  KNOWLEDGE-LEVEL  PLATO Tiles (Markdown + JSONL)          │
│  Resolution: provenance-traced knowledge assertions       │
├─────────────────────────────────────────────────────────┤
│  AGENT-LEVEL     I2I Protocol, Holonomy Consensus         │
│  Resolution: fleet coordination, zero-holonomy agreement  │
├─────────────────────────────────────────────────────────┤
│  CONSTRAINT-LEVEL  GUARD DSL, FLUX-C Bytecode             │
│  Resolution: safety specification, compiled constraints   │
├─────────────────────────────────────────────────────────┤
│  TEMPORAL-LEVEL  Tensor-MIDI                              │
│  Resolution: timing, rhythm, event scheduling             │
├─────────────────────────────────────────────────────────┤
│  BIT-LEVEL      INT8, Pythagorean48, CascadeMatch        │
│  Resolution: hardware constraint checking, quantization   │
└─────────────────────────────────────────────────────────┘
```

---

## Core Constraint Theory Track

The mathematical spine. Everything else snaps into this.

```
constraint-theory-math (pure theory, leaf node)
    │
    ▼
constraint-theory-py  [Python: constraint-theory]
    │  SNAP: Python API → fleet-agent, sunset-ecosystem, flux-check-py,
    │                     flux-sdk-python, flux-lib-py
    ▼
constraint-theory-rust-python  [Rust: flux-constraint + PyO3]
    │  Drop-in Python wheel + Rust crate
    │  SNAP: Rust crate → ct-core-cuda, ct-llvm, flux-ffi, superinstance-ffi
    │  SNAP: Python wheel → replaces constraint-theory-py
    │
    ├──► constraint-theory-core-cuda  [Rust] — GPU-accelerated constraint checking
    ├──► constraint-theory-llvm  [Rust v0.1.1] — CDCL → LLVM IR → AVX-512
    └──► constraint-theory-engine-cpp-lua  [CMake] — Legacy C++/Lua engine
```

---

## Dual FFI Bridge — C Header Snap

Two parallel C headers expose constraint theory to non-Rust languages:

```
superinstance-ffi  [Rust v0.1.0]          flux-ffi  [Rust v0.1.0]
  si_*() C++ style                         flux_*() pure C style
  ├── snapkit-zig                          ├── flux-cuda
  ├── snapkit-cuda                         ├── flux-esp32
  └── marine-gpu-edge                      └── flux-engine-c
```

Shared functions: `eisenstein_norm`, `laman_edges`, `is_rigid`, `holonomy_check`, `manhattan_distance`

`superinstance-ffi` adds: `pythagorean48_encode`, `cascade_match`, `constraint_check`, `lerp` — application-level hardware ops.
`flux-ffi` is minimal — pure C, targets embedded/bare-metal.

---

## GUARD DSL → FLUX Compiler Track

```
guard-dsl (GRAMMAR.ebnf: module/import/domain/state/invariant/derive/proof)
    │  Units are semantic tokens: "15000 m", "7.5 °/s"
    │
    ├──► guardc-v3  [Rust]  — GUARD → FLUX bytecode compiler
    │       SNAP: FLUX bytecode → flux-vm-v3
    │
    └──► guard2mask  [Rust v0.1.3] — GUARD → GDSII mask patterns
            Pipeline: GUARD → parse → compile → FLUX bytecode → VM → mask
            SNAP: GDSII → flux-lucid, flux-hardware

flux-isa  [Rust v0.1.2] — 43-opcode stack VM instruction set
    ├── flux-isa-mini   (embedded)
    ├── flux-isa-std    (standard)
    ├── flux-isa-edge   (edge compute)
    └── flux-isa-thor   (high-performance)

flux-vm-v3  [Rust] — executes FLUX-C bytecode from guardc-v3
```

---

## PLATO Knowledge Track

```
plato-core  [Python v0.1.0]
    │  SNAP: Python API → fleet-agent, plato-mcp, plato-local, sunset-ecosystem
    ▼
plato-engine  [Rust v0.1.0] — Tile, Room, Gate, Pathfinder, Engine
    │  SNAP: Rust crate → cocapn-glue-core, plato-bootcamp
    ▼
plato-tiles  — Markdown + JSONL knowledge tile format (universal snap)
    │  Tiles: constraint-propagation, kalman-filter-constraints,
    │         warp-cooperative-kernels, consistency-algorithms,
    │         nmea-gpu-parsing, adaptive-precision-control, ...
    │
    ├── plato-mcp  [Python v0.1.0] — MCP protocol → AI agents
    ├── plato-client, plato-local, plato-data, plato-adapters, plato-types
    ├── plato-training, plato-escalation-gate, plato-kernel-constraints
    ├── plato-room-intelligence, plato-soul-fingerprint, plato-model-ocean
    ├── neural-plato — neural network enhanced PLATO
    ├── platoclaw, platoclaw-coord — OpenClaw integration
    └── adaptive-plato — adaptive tile selection
```

---

## Fleet Coordination Track

```
fleet-agent  [Python v0.1.0] — 12-neighbor Laman rigidity + zero-holonomy
    │  SNAP: Python API → fleet-router, cocapn-cli
    │  SNAP: I2I → other agents | PLATO tiles → plato-core
    ▼
fleet-router  [Python v0.1.0] — priority-based message routing
    │  SNAP: I2I protocol → fleet-agent instances
    │
holonomy-consensus  [Rust v0.2.0] — geometric constraint satisfaction (no voting)
    │  SNAP: Rust crate → fleet-router-integration, cocapn-glue-core
    │
i2i-protocol  [Python: message.py, channels.py, router.py]
    │  SNAP: I2I messages → all fleet comms
    │
cocapn-glue-core  [Rust v0.1.0, #![no_std]] — cross-tier wire protocol
    │  Modules: config, discovery, plato, provenance, wire
    │  SNAP: Wire → flux-isa-* tiers | PLATO → plato-engine
    │
cocapn-cli  [Rust v0.1.0] — CLI for fleet operations
pbft-rust  [Rust v0.1.0] — traditional PBFT (reference/comparison)
fleet-stack, fleet-gateway, fleet-calibrator, fleet-health-monitor
fleet-resonance, fleet-murmur, fleet-murmur-worker
```

---

## Tensor-MIDI & Temporal Track

```
flux-tensor-midi (multi-language: rust/python/c/fortran)
    │  Python: core, midi, ensemble, harmony, adapters, sidechannel
    │  SNAP: temporal encoding → sunset-ecosystem (lifecycle timing)
    │  SNAP: temporal encoding → flux-transport (message scheduling)
    │
    └──► dodecet-encoder  [Rust v1.1.0] — 12-tone temporal pattern encoding
```

---

## Deadband Track — Precision Control

```
deadband-rs (Rust) ──► constraint-theory-rust-python
deadband-zig (Zig) ──► superinstance-ffi (C FFI)
deadband-python    ──► constraint-theory-py
```

---

## Mathematical Foundation

```
eisenstein  [Rust v0.3.1] ──► dodecet-encoder, constraint-theory-rust-python
eisenstein-embed  [Python] ──► fleet-math-py
penrose-memory  [Rust v1.1.0 + Python v0.1.0] ──► plato-engine, plato-core
cyclotomic-field ──► eisenstein (algebraic foundation)
galois-retrieval, galois-unification-proofs — Galois theory for retrieval/proofs
sheaf-constraint-synthesis — sheaf-theoretic constraints
spectral-conservation — spectral conservation laws
tensor-penrose, tensor-spline, turbovec — tensor/geometry primitives
```

---

## Sunset Ecosystem — Agent Lifecycle

```
sunset-ecosystem  [Python v0.1.0] — Trinity architecture
    │  Agents born parallel → ethos/pathos/logos rooms → sunset → seed next gen
    │  SNAP: Python API → constraint-theory-py (constraint scoring)
    │  SNAP: Tensor-MIDI → flux-tensor-midi (generation timing)
    │  SNAP: PLATO tiles → plato-core | I2I → i2i-protocol
```

---

## ASCII Architecture Diagram

```
                    ┌─────────────────────────────────┐
                    │         HUMAN LEVEL              │
                    │  Telegram, A2UI, Natural Lang    │
                    └──────────────┬──────────────────┘
                                   │ I2I messages
                    ┌──────────────▼──────────────────┐
                    │         AGENT LEVEL              │
                    │  ┌─────────┐  ┌──────────────┐  │
                    │  │fleet-   │  │ sunset-      │  │
                    │  │agent    │◄─┤ ecosystem    │  │
                    │  └────┬────┘  └──────┬───────┘  │
                    │       │              │           │
                    │  ┌────▼────┐  ┌──────▼───────┐  │
                    │  │fleet-   │──│ i2i-protocol │  │
                    │  │router   │  │ (messages)   │  │
                    │  └────┬────┘  └──────────────┘  │
                    │       │ holonomy                │
                    │  ┌────▼──────────────┐          │
                    │  │holonomy-consensus │          │
                    │  │(zero-holonomy)    │          │
                    │  └───────────────────┘          │
                    └──────────────┬──────────────────┘
                                   │ PLATO tiles
                    ┌──────────────▼──────────────────┐
                    │       KNOWLEDGE LEVEL            │
                    │  plato-core (Python)             │
                    │       │                          │
                    │  plato-engine (Rust)             │
                    │       │                          │
                    │  plato-tiles (JSONL+MD)          │
                    │       ├──► plato-mcp (MCP)       │
                    │       └──► cocapn-glue-core      │
                    └──────────────┬──────────────────┘
                                   │ GUARD / FLUX-C
                    ┌──────────────▼──────────────────┐
                    │     CONSTRAINT LEVEL             │
                    │                                 │
                    │  guard-dsl ──► guardc-v3 ──►    │
                    │                     FLUX-C      │
                    │  guard-dsl ──► guard2mask ──►   │
                    │                     GDSII       │
                    │                                 │
                    │  constraint-theory-py           │
                    │       ▼                         │
                    │  constraint-theory-rust-python  │
                    │       ├──► ct-core-cuda (GPU)   │
                    │       ├──► ct-llvm (AVX-512)    │
                    │       └──► ct-engine-cpp-lua    │
                    └──────────────┬──────────────────┘
                                   │ C FFI headers
                    ┌──────────────▼──────────────────┐
                    │     BIT / HARDWARE LEVEL         │
                    │                                 │
                    │  superinstance-ffi.h  flux_ffi.h │
                    │    (si_* C++ API)    (flux_* C)  │
                    │       │                │         │
                    │    snapkit-zig      flux-cuda    │
                    │    snapkit-cuda     flux-esp32   │
                    │    marine-gpu-edge  flux-engine-c│
                    │                                 │
                    │  flux-isa (43 opcodes)           │
                    │    ├── mini ├── std              │
                    │    ├── edge └── thor             │
                    └─────────────────────────────────┘

         TEMPORAL (cross-cutting):           WIRE (cross-cutting):
         ┌───────────────────────┐          ┌───────────────────────┐
         │ flux-tensor-midi      │          │ cocapn-glue-core      │
         │  (rust/py/c/fortran)  │          │  (#![no_std])         │
         │    ├── sunset-eco     │          │    ├── flux-isa-mini  │
         │    ├── flux-transport │          │    ├── flux-isa-edge  │
         │    └── dodecet-enc    │          │    └── flux-isa-thor  │
         └───────────────────────┘          └───────────────────────┘
```

---

## Snap Connectivity Matrix

| Source Repo | Snap Type | Targets |
|-------------|-----------|---------|
| `constraint-theory-py` | Python API | fleet-agent, sunset-ecosystem, flux-check-py, flux-sdk-python, flux-lib-py |
| `constraint-theory-rust-python` | Rust crate | ct-core-cuda, ct-llvm, flux-ffi, superinstance-ffi |
| `superinstance-ffi` | C FFI header | snapkit-zig, snapkit-cuda, marine-gpu-edge |
| `flux-ffi` | C FFI header | flux-cuda, flux-esp32, flux-engine-c |
| `holonomy-consensus` | Rust crate | fleet-router-integration, cocapn-glue-core |
| `plato-core` | Python API | fleet-agent, plato-mcp, plato-local, sunset-ecosystem |
| `plato-engine` | Rust crate | cocapn-glue-core, plato-bootcamp |
| `plato-tiles` | Tile format | Everything (universal snap) |
| `plato-mcp` | MCP protocol | External AI agents |
| `guard-dsl` | .guard source | guardc, guardc-v3, guard2mask |
| `guardc-v3` | FLUX bytecode | flux-vm-v3 |
| `guard2mask` | GDSII output | flux-lucid, flux-hardware |
| `flux-isa` | Rust crate | mini, std, edge, thor |
| `i2i-protocol` | I2I messages | fleet-agent, fleet-router, all fleet comms |
| `flux-tensor-midi` | Tensor-MIDI | sunset-ecosystem, flux-transport, dodecet-encoder |
| `cocapn-glue-core` | Wire protocol | flux-isa tiers |
| `eisenstein` | Rust crate | dodecet-encoder, constraint-theory-rust-python |
| `penrose-memory` | Rust + Python | plato-engine, plato-core |
| `fleet-agent` | Python API | fleet-router, cocapn-cli, plato-core, i2i-protocol |
| `snapkit-rs` | Rust crate | fleet-agent (state snapshots) |

---

## Statistics

| Metric | Count |
|--------|-------|
| Total repos surveyed | ~170 |
| Rust crates | ~25 |
| Python packages | ~15 |
| C FFI headers | 2 |
| FLUX ISA tiers | 4 |
| PLATO sub-repos | 17 |
| Fleet sub-repos | 11 |
| Flux sub-repos | 40+ |
| Snap types | 10 |
| Resolution levels | 6 |
| Exotic language ports | 7 (ALGOL, Chapel, COBOL, Fortran, MUMPS, PL/I, SNOBOL) |

---

*Living document. Update when repos are added or snap interfaces change.*
