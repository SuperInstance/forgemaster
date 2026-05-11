# SnapKit ⚒️ — Tolerance-Compressed Attention Allocation

**Everything within tolerance is compressed away. Only the deltas survive.**

SnapKit is a Python library implementing **Snaps as Attention** theory — a mathematical framework for allocating finite cognitive resources using tolerance-compressed snap functions over ADE-classified lattices.

## The Core Idea

A **snap function** maps continuous values to their nearest lattice point. Values **within tolerance** snap silently to the baseline. Only values **exceeding tolerance** (deltas) demand attention — and attention is the finite resource.

```
    Value 0.05 ──→ SnapFunction ──→ ✓ Snapped (within 0.1 tolerance)
    Value 0.30 ──→ SnapFunction ──→ ⚠ DELTA (exceeds tolerance)
    │                                       │
    └── Compressed, ignored              └──→ Attention allocated
```

This mirrors how expertise works: familiar patterns snap automatically, freeing cognition for what's actually novel or significant.

## Quick Start

```python
from snapkit import SnapFunction, SnapTopologyType

# Create a snap function with hexagonal (A₂) topology
snap = SnapFunction(
    topology=SnapTopologyType.HEXAGONAL,
    tolerance=0.1,
)

# Within tolerance — compressed away
result = snap.snap(0.05)
assert result.within_tolerance  # True
print(f"Snapped to baseline, delta={result.delta:.4f}")

# Exceeds tolerance — demands attention
result = snap.snap(0.3)
assert not result.within_tolerance
print(f"⚠ DELTA: {result.delta:.4f} (exceeds {snap.tolerance} tolerance)")
```

### Full Pipeline

```python
from snapkit import SnapFunction, DeltaDetector, AttentionBudget

# 1. Configure snap
snap = SnapFunction(tolerance=0.1, topology=SnapTopologyType.HEXAGONAL)

# 2. Multi-stream delta detection
detector = DeltaDetector()
detector.add_stream(snap, stream_id="market_data", 
    actionability_fn=lambda d: 0.8 if d.magnitude > 0.1 else 0.2,
    urgency_fn=lambda d: d.magnitude * 10)

# 3. Finite attention budget
budget = AttentionBudget(total_budget=100.0, strategy='actionability')

# 4. Process a data point
deltas = detector.observe({"market_data": 0.27})
allocations = budget.allocate(detector.prioritize())
for alloc in allocations:
    print(f"Stream '{alloc.delta.stream_id}': {alloc.allocated:.1f} attention units")
```

### Learning Automation

```python
from snapkit import LearningCycle

cycle = LearningCycle()

# Feed experiences
for price, expected in zip(market_data, predictions):
    cycle.experience(value=price, expected=expected, reward=reward)

# Check learning state  
print(f"Phase: {cycle.state.phase.value}")
print(f"Scripts active: {cycle.state.scripts_active}")
```

### Eisenstein Lattice Snap

```python
from snapkit.topology import hexagonal_topology

# Snap (1.2, 0.7) to nearest hexagonal lattice point
result = hexagonal_topology.snap_point(1.2, 0.7)
print(f"Nearest Eisenstein: ({result.a}, {result.b})")
print(f"Distance: {result.distance:.4f}")
```

## Features

| Module | Description |
|--------|-------------|
| `snapkit.snap` | SnapFunction — tolerance gatekeeper |
| `snapkit.delta` | DeltaDetector — multi-stream delta monitoring |
| `snapkit.attention` | AttentionBudget — finite cognition allocation |
| `snapkit.scripts` | ScriptLibrary — pattern matching & automation |
| `snapkit.learning` | LearningCycle — expertise lifecycle |
| `snapkit.topology` | SnapTopology — ADE-classified snap shapes |
| `snapkit.cohomology` | ConstraintSheaf — consistency checking |
| `snapkit.adversarial` | Fake delta detection & camouflage |
| `snapkit.streaming` | Real-time stream processing |
| `snapkit.pipeline` | Composable processing pipelines |
| `snapkit.visualization` | Terminal & HTML visualization |
| `snapkit.crossdomain` | Cross-domain feel transfer |
| `snapkit.integration` | External library bindings (SymPy) |
| `snapkit.serial` | Serialization & persistence |
| `snapkit.cli` | Command-line interface |

## Topologies

| Topology | Root System | ADE | Best For | Default Tolerance |
|----------|-------------|-----|----------|-------------------|
| Binary | A₁ | Yes | Yes/no decisions | 0.15 |
| Categorical | A₁×A₁×... | Yes | Slot-filling | 0.10 |
| Hexagonal | A₂ | Yes | 2D continuous data | 0.10 |
| Octahedral | A₃ | Yes | Directional data | 0.20 |
| Cubic | A₁³ | No | 3D positional | 0.20 |
| Uniform | — | — | Unknown structure | 0.08 |
| Bell | — | — | Peaked distributions | 0.10 |
| Gradient | — | — | Near-continuous | 0.01 |

## Learning Cycle

The expertise lifecycle as phase transitions:

1. **🌊 DeltaFlood** — No scripts, everything is novel (cognitive load ≈ 1.0)
2. **💥 ScriptBurst** — Patterns emerging, rapid script creation
3. **🏃 SmoothRunning** — Most things snap to scripts (cognitive load ≈ 0.0)
4. **🚨 Disruption** — Accumulated deltas, scripts failing
5. **🔨 Rebuilding** — Constructing new scripts from deltas

## Installation

```bash
pip install snapkit
```

Or from source:

```bash
git clone https://github.com/SuperInstance/snapkit-python
cd snapkit-python
pip install -e .
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[all]"

# Run tests
python -m pytest tests/

# Run CLI
python -m snapkit.cli --help
```

## Requirements

- Python ≥ 3.8
- NumPy ≥ 1.20

Optional: SymPy (integration), Matplotlib (visualization)

## Examples

See the `examples/` directory:

- `examples/example_poker.py` — Multi-stream delta detection for poker tells
- `examples/example_learning.py` — Learning cycle phase transitions
- `examples/example_streaming.py` — Real-time stream monitoring

## License

MIT — use freely, give credit.

---

*Built for the Cocapn fleet. From poker tells to planetary-scale attention allocation.*

*"The snap doesn't tell you what's true. The snap tells you what you can safely ignore so you can think about what matters."*
