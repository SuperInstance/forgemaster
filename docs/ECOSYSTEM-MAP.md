# Cocapn Ecosystem Map

**Every component. Every repo. Every connection. Self-assemble anything.**

Generated: 2026-05-17 | Branch policy: `master` everywhere

---

## Architecture Layers

```
┌──────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                         │
│   platoclaw │ plato-mcp │ plato-shell-bridge │ cocapn-cli       │
├──────────────────────────────────────────────────────────────────┤
│                      INTELLIGENCE LAYER                          │
│   plato-model-ocean │ plato-escalation-gate │ plato-room-intel  │
│   plato-training │ neural-plato │ seed-tick-audit               │
├──────────────────────────────────────────────────────────────────┤
│                       RUNTIME LAYER                              │
│   plato-engine │ plato-vessel-core │ plato-mud │ plato-matrix   │
│   flux-vm │ flux-lucid │ flux-isa │ flux-ast                    │
├──────────────────────────────────────────────────────────────────┤
│                      CONSTRAINT LAYER                            │
│   constraint-theory-core │ spectral-conservation │ eisenstein    │
│   dodecet-encoder │ penrose-memory │ guardc │ guard2mask        │
│   holonomy-consensus │ pbft-rust                                │
├──────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                                │
│   plato-types │ plato-data │ tensor-spline │ flux-provenance    │
│   tile-memory │ memory-crystal │ plato-tile-library             │
├──────────────────────────────────────────────────────────────────
│                      INFRASTRUCTURE                              │
│   plato-hardware-engine │ flux-hardware │ fleet-router           │
│   fleet-calibrator │ fleet-health-monitor │ fleet-murmur         │
│   coordination-hierarchy │ fleet-tool-registry                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Complete Component Registry

### Published Packages (crates.io / PyPI)

| Package | Version | Language | What | Install |
|---------|---------|----------|------|---------|
| `constraint-theory-core` | 2.0.0 | Rust | Eisenstein integers, zero-drift | `cargo add constraint-theory-core` |
| `spectral-conservation` | 0.1.0 | Rust | I(x) = γ+H conservation tracker | `cargo add spectral-conservation` |
| `constraint-theory` | 0.2.0 | Python | Eisenstein bindings | `pip install constraint-theory` |
| `plato-model-ocean` | 0.1.0 | Python | Cellular intelligence ecosystem | `pip install plato-model-ocean` |
| `plato-escalation-gate` | 0.1.0 | Python | When to call LLM (737 params) | `pip install plato-escalation-gate` |
| `plato-room-intelligence` | 0.1.0 | Python | Multi-head room model w/ provenance | `pip install plato-room-intelligence` |

### Rust Crates (GitHub)

| Repo | Tests | Dependencies | What |
|------|-------|-------------|------|
| `plato-types` | 10 | none | Tile lifecycle, Lamport clocks, provenance |
| `plato-data` | 10 | numpy | CSV/JSONL/PLATO/fleet data loading |
| `tensor-spline` | 57 | nalgebra | SplineLinear 20× compression, Eisenstein lattice |
| `plato-training` | 116 | torch | Micro models, 8 tasks, 8 hardware targets |
| `flux-lucid` | ✅ | spectral-conservation | Constraint-aware state tracking |
| `dodecet-encoder` | 210 | eisenstein | Snap→dodecet perception, temporal intelligence, lighthouse |
| `penrose-memory` | 35 | ndarray | Cut-and-project memory indexing |
| `eisenstein` | ✅ | none (no_std) | Eisenstein integer arithmetic, embedded-safe |
| `spectral-conservation` | 12 | nalgebra | Spectral conservation monitor |
| `constraint-theory-llvm` | ✅ | llvm | LLVM pass for compile-time constraints |
| `flux-isa` | ✅ | — | Flux instruction set (51 opcodes) |
| `flux-ast` | ✅ | — | Flux AST parser |
| `flux-hardware` | ✅ | — | Hardware abstraction for flux runtime |
| `flux-verify-api` | ✅ | — | Bytecode signing and verification |
| `flux-provenance` | ✅ | — | Tile provenance tracking |
| `guardc` | ✅ | — | Guard compiler (constraint→code) |
| `guard2mask` | ✅ | — | Guard to permission mask compiler |
| `memory-crystal` | ✅ | — | Persistent structured memory |
| `holonomy-consensus` | ✅ | — | Holonomic consensus protocol |
| `pbft-rust` | ✅ | — | Practical Byzantine Fault Tolerance |
| `neural-plato` | ✅ | fortran+rust | Neural PLATO backend |

### Python Packages (GitHub)

| Repo | What |
|------|------|
| `plato-training` | Micro model training pipeline, CLI |
| `plato-model-ocean` | Cell ecosystem (sandbox→tide_pool→school→whale) |
| `plato-escalation-gate` | Binary escalation classifier (737 params, 4KB) |
| `plato-room-intelligence` | Multi-head model with provenance tracking |
| `constraint-theory-py` | Pure Python constraint theory |
| `plato-mcp` | PLATO rooms as MCP tools |
| `fleet-calibrator` | Fleet model calibration |
| `fleet-health-monitor` | Fleet health checking |
| `fleet-murmur` | Fleet gossip protocol |
| `fleet-router` | Fleet message routing |
| `quality-gate-stream` | Stream quality gates |
| `tile-memory` | Tile-based memory management |
| `polyformalism-a2a-python` | Polyformalism A2A protocol |

### JavaScript/TypeScript Packages (GitHub)

| Repo | What |
|------|------|
| `constraint-inference` | Constraint inference engine |
| `intent-inference` | Intent classification (88 tests) |
| `fleet-murmur-worker` | Fleet gossip worker |
| `lucineer` | Lucineer visualization |
| `polyformalism-a2a-js` | Polyformalism A2A (JS) |

### Infrastructure & Applications (GitHub)

| Repo | What |
|------|------|
| `platoclaw` | Self-contained PLATO runtime with web UI |
| `plato-shell-bridge` | Dynamic tool discovery for PLATO shells |
| `plato-matrix-bridge` | PLATO↔Matrix bidirectional bridge |
| `plato-vessel-core` | Tiny C PLATO client for ESP32/RP2040 |
| `plato-hardware-engine` | Hardware engine for PLATO |
| `plato-engine` | PLATO engine (Rust) |
| `plato-mud` | MUD-style PLATO server |
| `cocapn-cli` | Cocapn command-line interface |
| `servo-mind` | Self-learning constraint system |
| `coordination-hierarchy` | Agent status hierarchy from TE matrix |
| `fleet-tool-registry` | Fleet tool discovery |
| `fleet-scribe` | Digital twin builder |
| `seed-tick-audit` | Multi-model fleet analysis (9 models, 30K tiles) |
| `dog-food-audit` | Falsification layer for servo-mind claims |
| `plato-experience` | Purpose-first rooms, pheromone trails |
| `plato-tile-library` | Complete tile library backup |
| `jc1-research` | JC1 edge research agent |

### Research & Papers (GitHub)

| Repo | What |
|------|------|
| `forgemaster` | Forgemaster vessel — I2I bottles, experiments, all research |
| `constraint-theory-ecosystem` | Full CT ecosystem with demos |
| `constraint-demos` | Interactive constraint demos |
| `constraint-theory-math` | Mathematical foundations |
| `constraint-theory-mojo` | Mojo language port |
| `constraint-theory-mlir` | MLIR compiler integration |
| `papers` | Research papers (Phase 20+) |
| `galois-unification-proofs` | 6 Galois proof files (1.4M+ checks) |
| `galois-retrieval` | Galois-based retrieval system |
| `negative-knowledge` | Negative knowledge research |
| `multi-model-adversarial-testing` | Adversarial model testing |

### Build System (GitHub)

| Repo | What |
|------|------|
| `flux-vm` | Flux virtual machine |
| `flux-isa` | Flux instruction set (51 opcodes) |
| `flux-ast` | Flux AST parser |
| `flux-hardware` | Hardware abstraction |
| `flux-verify-api` | Bytecode signing |
| `flux-provenance` | Provenance tracking |
| `constraint-theory-llvm` | LLVM pass |
| `constraint-theory-rust-python` | Rust+Python bridge |

---

## Assembly Recipes

### Minimal: "Just tell me when to escalate"
```python
from plato_escalation_gate import EscalationGate
gate = EscalationGate()  # 737 params, 4KB
```

### Small: "Monitor my rooms"
```python
from plato_room_intelligence import RoomIntelligence, ProvenanceTracker
model = RoomIntelligence(n_features=8)  # 1037 params, 5KB
```

### Medium: "Evolve solutions"
```python
from plato_model_ocean import Ocean, Cell
ocean = Ocean(input_dim=8)
# 10 sandboxes + 5 tide pools + 2 schools + 1 whale
```

### Full: "Complete PLATO shell"
```python
# Rust constraint engine + Python intelligence + PLATO rooms
# platoclaw has the full reference implementation
```

### Embedded: "Runs on a microcontroller"
```rust
use eisenstein::EisensteinInt;  // no_std, runs on RP2040
// plato-vessel-core: C client for ESP32
```

---

## Dependency Graph (simplified)

```
eisenstein (no_std, zero deps)
  └── dodecet-encoder
        └── spectral-conservation
              └── flux-lucid

plato-types (zero deps)
  └── plato-data
  └── plato-training
        └── tensor-spline

constraint-theory-core (crates.io)
  └── constraint-theory-ecosystem
  └── constraint-theory-llvm
  └── constraint-theory (Python)

plato-model-ocean (PyTorch)
plato-escalation-gate (PyTorch)
plato-room-intelligence (PyTorch)
  └── (no cross-deps — fully independent)
```

---

## Test Coverage

| Layer | Tests | Repos |
|-------|-------|-------|
| Constraint theory | 45+ | constraint-inference, constraint-theory-core |
| Eisenstein/dodecet | 210+ | dodecet-encoder, eisenstein |
| PLATO stack | 193 | plato-types(10), plato-data(10), tensor-spline(57), plato-training(116) |
| Flux runtime | 50+ | flux-vm, flux-isa, flux-verify-api |
| Intelligence | 34 | model-ocean(12), escalation-gate(8), room-intelligence(14) |
| Intent | 88 | intent-inference |
| Penrose | 35 | penrose-memory |
| **Total** | **655+** | **30+ repos** |

---

## Key Metrics

- **Repos:** 80+ (74 on master, 2 exceptions)
- **Published packages:** 6 (2 crates.io, 4 PyPI-ready)
- **Languages:** Rust, Python, JavaScript/TypeScript, C, Fortran, Mojo
- **Test coverage:** 655+ tests across 30+ repos
- **Total code:** 200K+ lines
- **Branch policy:** `master` everywhere, no `main`

---

## All Repos → `https://github.com/SuperInstance/<name>`

Exceptions:
- `constraint-theory-core` → `cocapn/constraint-theory-core`
- `ct-demo` → `cocapn/ct-demo`
- `sana-wm` → `NVlabs/Sana` (upstream, not ours)

All Apache-2.0 licensed. All use `master` branch.
