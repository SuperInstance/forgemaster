# Cocapn Component Assembly Guide

**Every component is modular. Every component is independently installable. Self-assemble for any application.**

Last updated: 2026-05-17

---

## The Stack — Pick What You Need

```
┌─────────────────────────────────────────────────┐
│              YOUR APPLICATION                    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Model    │  │ Room     │  │ Escalation    │  │
│  │ Ocean    │  │ Intel    │  │ Gate          │  │
│  │ (370+)   │  │ (1K)     │  │ (737 params)  │  │
│  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│       │             │               │            │
│  ┌────▼─────────────▼───────────────▼────────┐  │
│  │         PLATO Shell Intelligence          │  │
│  │    Decompose → Evolve → Recompose → Verify│  │
│  └───────────────────┬───────────────────────┘  │
│                      │                           │
│  ┌───────────────────▼───────────────────────┐  │
│  │           PLATO Training Rooms            │  │
│  │  drift-detect · anomaly-flag · intent     │  │
│  │  priority-rank · tile-relevance           │  │
│  │  8 hardware targets (cpu/gpu/npu/wasm)    │  │
│  └───────────────────┬───────────────────────┘  │
│                      │                           │
│  ┌──────┐ ┌──────┐ ┌┴──────┐ ┌──────────────┐  │
│  │plato │ │tensor│ │plato  │ │spectral-     │  │
│  │types │ │spline│ │data   │ │conservation  │  │
│  └──────┘ └──────┘ └───────┘ └──────────────┘  │
│                                                  │
│  ┌──────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌─────┐  │
│  │eisen-│ │flux- │ │dodecet│ │constr│ │flux-│  │
│  │stein │ │lucid │ │encode │ │theory│ │vm   │  │
│  └──────┘ └──────┘ └───────┘ └──────┘ └─────┘  │
└─────────────────────────────────────────────────┘
```

---

## Published Packages

### Rust (crates.io)
| Crate | Version | What | Install |
|-------|---------|------|---------|
| `constraint-theory-core` | 2.0.0 | Eisenstein integer precision, zero-drift | `cargo add constraint-theory-core` |
| `spectral-conservation` | 0.1.0 | I(x) = γ+H conservation tracker | `cargo add spectral-conservation` |
| `constraint-theory` (Python) | 0.2.0 | Python bindings | `pip install constraint-theory` |

### Python (pip)
| Package | Version | What | Install |
|---------|---------|------|---------|
| `plato-model-ocean` | 0.1.0 | Cellular intelligence ecosystem | `pip install plato-model-ocean` |
| `plato-escalation-gate` | 0.1.0 | When to call LLM (737 params) | `pip install plato-escalation-gate` |
| `plato-room-intelligence` | 0.1.0 | Multi-head room model w/ provenance | `pip install plato-room-intelligence` |

### Rust (GitHub)
| Repo | What | `Cargo.toml` |
|------|------|-------------|
| `plato-types` | Tile lifecycle, Lamport clocks | `plato-types = { git = "https://github.com/SuperInstance/plato-types" }` |
| `tensor-spline` | SplineLinear 20× compression | `tensor-spline = { git = "https://github.com/SuperInstance/tensor-spline" }` |
| `plato-data` | CSV/JSONL/PLATO data loading | `plato-data = { git = "https://github.com/SuperInstance/plato-data" }` |
| `plato-training` | Micro models, hardware deploy | `plato-training = { git = "https://github.com/SuperInstance/plato-training" }` |
| `flux-lucid` | Constraint-aware state tracking | `flux-lucid = { git = "https://github.com/SuperInstance/flux-lucid" }` |
| `dodecet-encoder` | Eisenstein snap→dodecet perception | `dodecet-encoder = { git = "https://github.com/SuperInstance/dodecet-encoder" }` |
| `penrose-memory` | Cut-and-project memory indexing | `penrose-memory = { git = "https://github.com/SuperInstance/penrose-memory" }` |
| `eisenstein` | Eisenstein integer arithmetic | `eisenstein = { git = "https://github.com/SuperInstance/eisenstein" }` |

---

## Assembly Patterns

### Pattern 1: Minimal Intelligence Shell (4KB)
For any app that needs a tiny "should I escalate?" gate.

```python
from plato_escalation_gate import EscalationGate

gate = EscalationGate()  # 737 params, 4KB
decision = gate(confidence, activity, drift_rate, anomaly_score, time_since)
if decision > 0.5:
    call_llm(context)
```

**Dependencies:** PyTorch only. Runs on CPU, GPU, or WASM.

### Pattern 2: Room Intelligence (5KB)
For apps with multiple "rooms" of knowledge that need monitoring.

```python
from plato_room_intelligence import RoomIntelligence, ProvenanceTracker

model = RoomIntelligence(n_features=8)  # 1037 params
tracker = ProvenanceTracker()

# Train from room data
for room in rooms:
    X, y = room.get_training_data()
    model.train_step(X, y)
    tracker.record(room.name, model.shared_weights())

# Runtime: decision with traceability
pred = model(features)
trace = tracker.trace(pred)  # which rooms shaped this decision
```

### Pattern 3: Full Model Ocean (148KB)
For apps that need an evolving ecosystem of specialized models.

```python
from plato_model_ocean import Ocean, Cell

ocean = Ocean(input_dim=8)

# Colonize
for _ in range(80):
    ocean.add(Cell('sandbox'))  # tiny experimenters
for task in ['drift', 'anomaly', 'intent']:
    ocean.add(Cell('tide_pool', provenance=[task]))  # specialists
ocean.add(Cell('school'))  # coordinators
ocean.add(Cell('whale'))  # deep reasoner

# Evolve on your data
for X, y, task in data_stream:
    ocean.train_tick(X, y, task)
    ocean.promote()  # sandbox → tide_pool → school

# Runtime: collective vote
decision, confidence, trace = ocean.decide(input_features)
```

### Pattern 4: PLATO Stack (Rust)
For high-performance constraint-aware applications.

```rust
use plato_types::{Tile, TileLifecycle, LamportClock};
use spectral_conservation::{spectral_state, ConservationMonitor};
use tensor_spline::SplineLinear;

let monitor = ConservationMonitor::new(16);
for tile in room.tiles() {
    let state = spectral_state(&tile.coupling_matrix());
    monitor.observe(state);
    if monitor.is_drifting() {
        // Conservation violated — investigate
    }
}
```

### Pattern 5: Full Cocapn Shell
The complete intelligence system — decomposition, evolution, recomposition, verification.

```python
from plato_model_ocean import Ocean
from plato_escalation_gate import EscalationGate
from plato_room_intelligence import RoomIntelligence

# The shell
ocean = Ocean()
gate = EscalationGate()
rooms = RoomIntelligence()

# Decompose problem into rooms
plan = ocean.decompose("optimize supply chain")
# → Creates: supply-nodes, routes, constraints, objectives

# Evolve solutions
plan.evolve(steps=100)
# → Sandboxes test ideas, tide pools specialize, whale reasons deep

# Escalate when needed
if gate(room_state) > 0.5:
    insight = call_llm(room_state)
    ocean.inject(insight)  # LLM wisdom feeds the ocean

# Recompose
result = plan.recompose()
# → Verified solution with constraint guarantees
# → Every decision traceable to contributing rooms
```

---

## Component Independence Matrix

| Component | Depends On | Size | Runs On |
|-----------|-----------|------|---------|
| EscalationGate | PyTorch | 4KB | CPU/GPU/WASM/NPU |
| RoomIntelligence | PyTorch | 5KB | CPU/GPU/WASM/NPU |
| ModelOcean | PyTorch | varies | CPU/GPU |
| plato-types | none (pure Rust) | tiny | any |
| tensor-spline | nalgebra | small | any |
| plato-data | numpy | small | any |
| plato-training | PyTorch | medium | CPU/GPU |
| spectral-conservation | nalgebra | small | any |
| flux-lucid | spectral-conservation | medium | any |
| dodecet-encoder | eisenstein | medium | any |
| eisenstein | none (pure Rust, no_std) | tiny | embedded |
| penrose-memory | ndarray | small | any |

---

## Self-Assembly Rules

1. **Start small.** One gate, one room. Grow from there.
2. **Every component works alone.** No circular dependencies.
3. **Traceability is optional but recommended.** Provenance adds ~10% overhead.
4. **The ocean scales.** 10 cells or 10,000 — same API.
5. **Hardware is transparent.** PyTorch handles CPU/GPU. Rust handles embedded.
6. **Conservation is the health monitor.** Add `spectral-conservation` when you need guarantees.

---

## GitHub Repos

All at `https://github.com/SuperInstance/<name>`

**Core:** plato-types, plato-data, tensor-spline, plato-training, spectral-conservation, flux-lucid, eisenstein, dodecet-encoder, penrose-memory, constraint-theory-core

**Fleet:** plato-matrix-bridge, plato-vessel-core, plato-mcp, plato-shell-bridge, fleet-router, fleet-calibrator, fleet-health-monitor, fleet-murmur

**Intelligence:** plato-model-ocean, plato-escalation-gate, plato-room-intelligence

**Research:** forgemaster (vessel), constraint-theory-ecosystem, holonomy-consensus, pbft-rust, neural-plato

**Build system:** constraint-theory-llvm, flux-isa, flux-ast, flux-hardware, flux-verify-api, flux-provenance

All repos use `master` branch. All Apache-2.0 licensed.
