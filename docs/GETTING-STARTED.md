# Getting Started with SuperInstance

**You found us. Here's what we build and how to use it.**

We make mathematically-grounded tools for building intelligent systems. Everything is modular, independently installable, and open source (Apache-2.0).

---

## Three Paths In

### Path 1: "Just Want the Math" 🧮

You care about precision, drift, and provable guarantees in numerical computing.

```bash
# Rust (crates.io)
cargo add constraint-theory-core
cargo add spectral-conservation

# Python (PyPI)
pip install constraint-theory
```

```rust
use constraint_theory_core::EisensteinInt;
use spectral_conservation::{spectral_state, ConservationMonitor};

// Eisenstein integers: zero-drift lattice arithmetic
let z = EisensteinInt::new(3, 1);  // 3 + ω
let norm = z.norm();  // |3+ω|² = 7

// Spectral conservation: detect when coupled dynamics drift
let monitor = ConservationMonitor::new(16);
monitor.observe(spectral_state(&coupling_matrix));
if monitor.is_drifting() {
    // Conservation violated — investigate
}
```

**Next:** [Eisenstein repo](https://github.com/SuperInstance/eisenstein) · [Spectral conservation](https://github.com/SuperInstance/spectral-conservation) · [Math audit](https://github.com/SuperInstance/forgemaster/blob/master/research/MATH-ELEGANCE-AUDIT.md)

---

### Path 2: "Want Intelligent Rooms" 🧠

You have data streams, sensor feeds, or agent outputs and need tiny models that monitor, classify, and know when to escalate.

```bash
pip install plato-escalation-gate
pip install plato-room-intelligence
pip install plato-model-ocean
```

```python
from plato_escalation_gate import EscalationGate

# 737 params, 4KB — decides when to call an LLM
gate = EscalationGate()
if gate.should_escalate(confidence, activity, drift, anomaly, time):
    response = call_your_llm(context)
```

```python
from plato_model_ocean import Ocean, Cell

# Evolving ecosystem of tiny models
ocean = Ocean(input_dim=8)
for _ in range(50):
    ocean.add(Cell('sandbox'))   # experimenters
ocean.add(Cell('whale'))         # deep reasoner

for X, y, task in your_data_stream:
    ocean.train_tick(X, y, task)

decision, confidence, trace = ocean.decide(features)
```

**Next:** [Model Ocean](https://github.com/SuperInstance/plato-model-ocean) · [Escalation Gate](https://github.com/SuperInstance/plato-escalation-gate) · [Room Intelligence](https://github.com/SuperInstance/plato-room-intelligence)

---

### Path 3: "Want the Full Ecosystem" 🏗️

You're building a multi-agent system or need the complete stack.

**Read these first:**
1. [ECOSYSTEM-MAP.md](https://github.com/SuperInstance/forgemaster/blob/master/ECOSYSTEM-MAP.md) — every repo, every connection
2. [ASSEMBLY-GUIDE.md](https://github.com/SuperInstance/forgemaster/blob/master/ASSEMBLY-GUIDE.md) — 5 self-assembly patterns

**Core stack:**
```bash
# Rust crates
cargo add plato-types        # Tile lifecycle, Lamport clocks
cargo add tensor-spline      # SplineLinear 20× compression
cargo add flux-lucid          # Constraint-aware state tracking

# Python packages
pip install plato-training   # Micro model pipeline, 8 tasks, 8 targets
```

**What you get:**
- 655+ tests across 30+ repos
- 8 micro model tasks (drift-detect, anomaly-flag, intent-detect, etc.)
- 8 hardware targets (CPU, GPU, NPU, WASM, embedded)
- Conservation monitoring baked into the runtime
- Every component works independently — no circular dependencies

**Next:** [PLATO Training](https://github.com/SuperInstance/plato-training) · [Tensor Spline](https://github.com/SuperInstance/tensor-spline) · [Flux Lucid](https://github.com/SuperInstance/flux-lucid)

---

## What We've Published

| Package | Language | What | Install |
|---------|----------|------|---------|
| `constraint-theory-core` | Rust | Eisenstein integers, zero-drift | `cargo add constraint-theory-core` |
| `spectral-conservation` | Rust | Conservation law tracker | `cargo add spectral-conservation` |
| `constraint-theory` | Python | Python bindings | `pip install constraint-theory` |
| `plato-model-ocean` | Python | Evolving model ecosystem | `pip install plato-model-ocean` |
| `plato-escalation-gate` | Python | LLM escalation classifier | `pip install plato-escalation-gate` |
| `plato-room-intelligence` | Python | Multi-head room model | `pip install plato-room-intelligence` |

---

## Questions?

- **Open an issue** on any repo — we respond
- **Join our Discord:** https://discord.com/invite/clawd
- **Read the architecture:** [PLATO Shell Intelligence](https://github.com/SuperInstance/forgemaster/blob/master/research/PLATO-SHELL-INTELLIGENCE.md)

All repos at [github.com/SuperInstance](https://github.com/SuperInstance) · Apache-2.0 licensed
