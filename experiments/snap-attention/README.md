# snapkit ⚡ — Tolerance-Compressed Attention Allocation

**snapkit** is a production-ready Python library implementing *snap-attention theory*: the insight that cognition is a **finite budget of attention** gated by **tolerance-compressed snap functions**.

> *"The snap doesn't tell you what's true. The snap tells you what you can SAFELY IGNORE so you can think about what matters."*
> — SNAPS-AS-ATTENTION.md

## Quick Start

```bash
pip install snapkit
```

```python
from snapkit import SnapFunction, SnapTopologyType

# Create a snap function — the gatekeeper of attention
snap = SnapFunction(tolerance=0.1, topology=SnapTopologyType.HEXAGONAL)

# Values within tolerance are compressed away
result = snap.observe(0.05)
print(result)  # ✅ SNAP — compressed to baseline

# Values outside tolerance demand attention
result = snap.observe(0.3)
print(result)  # ⚠️ DELTA — demands cognitive attention
```

## Architecture

```
                       ┌──────────────────┐
                       │  Observation     │
                       │  (value)         │
                       └────────┬─────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   SnapFunction        │
                    │   (tolerance gate)    │
                    └──┬────────────┬───────┘
                       │            │
                       ▼            ▼
                 ┌──────────┐  ┌──────────┐
                 │  SNAP    │  │  DELTA   │
                 │(compress)│  │(demand   │
                 │          │  │attention)│
                 └──────────┘  └────┬─────┘
                                     │
                                     ▼
                    ┌───────────────────────┐
                    │   AttentionBudget     │
                    │  allocate(Δ×A×U×C)   │
                    └──────────┬────────────┘
                               │
                               ▼
                    ┌───────────────────────┐
                    │   ScriptLibrary       │
                    │  match→execute       │
                    └───────────────────────┘
```

## Core Concepts

### 1. SnapFunction (`snapkit.snap`)
The fundamental compression operator. Maps incoming values to "expected" (lattice point) if within tolerance. Flags as delta if outside.

```python
snap = SnapFunction(tolerance=0.1)

# Multi-dimensional snap
results = snap.snap_nd(np.array([0.42, 0.05, 0.31]))

# Adaptive tolerance — auto-adjusts based on delta rate
snap.enable_adaptive_tolerance(window=50)

# Hierarchical snap — check at multiple tolerance levels
profile = snap.hierarchical_profile(0.42)
print(profile['transition_tolerance'])  # At what tolerance this becomes a delta
```

### 2. DeltaDetector (`snapkit.delta`)
Tracks what exceeds snap tolerance, with multi-stream awareness.

```python
detector = DeltaDetector()
detector.add_stream('market', SnapFunction(tolerance=0.05))
detector.add_stream('risk', SnapFunction(tolerance=0.15))

results = detector.observe({'market': 0.42, 'risk': 0.05})
prioritized = detector.prioritize(top_k=3)

# Delta clustering
clusters = detector.delta_clusters(n_clusters=3)

# Delta forecasting
stream = detector._streams['market']
forecast = stream.delta_forecast(horizon=5)
```

### 3. AttentionBudget (`snapkit.attention`)
Finite cognitive resource allocation based on delta magnitude × actionability × urgency.

```python
budget = AttentionBudget(total=100.0, strategy='actionability')
allocations = budget.allocate(prioritized_deltas)
for alloc in allocations:
    print(f"  {alloc.delta.stream_id}: {alloc.allocated:.1f} au — {alloc.reason}")

# Multi-level: macro (which streams) + micro (which deltas)
result = budget.multi_level_allocate(macro_deltas, micro_deltas)

# Attention insights
print(budget.attention_insight())
```

### 4. ScriptLibrary (`snapkit.scripts`)
Learned patterns that execute automatically, freeing cognition.

```python
library = ScriptLibrary()

# Learn a new script
script = library.learn(
    trigger_pattern=np.array([0.4, 0.3, 0.2]),
    response={'action': 'buy', 'confidence': 0.85},
    name='buy_signal',
)

# Match against observation
match = library.find_best_match(np.array([0.42, 0.31, 0.21]))
if match and match.is_match:
    print(f"Executing: {match.script_id}")

# Compose scripts into sequences
composite = library.compose(['buy_signal', 'hedge_logic'])

# Script planning (Rubik's cube strategy)
plan = ScriptPlan('market_strategy', library)
plan.add_step('assess_volatility', fallback='wait')
plan.add_step('execute_entry', conditions={'signal': 'buy'})
```

### 5. SnapTopology (`snapkit.topology`)
The ADE classification of snap functions — which lattice determines the compression topology.

```python
from snapkit.topology import (
    hexagonal_topology, triality_topology,
    exceptional_e8, recommend_topology,
)

# Get recommended topology for data
topo = recommend_topology(data, ade_type=ADE_DATA.E8_HEXAGONAL)
print(f"Recommended: {topo.name}")

# Compare all topologies
results = {t.name: t.snap_rate(data) for t in all_topologies()}
```

### 6. LearningCycle (`snapkit.learning`)
The expertise cycle: experience → pattern → script → automation.

```python
cycle = LearningCycle()
for value in data_stream:
    state = cycle.experience(value)
    if state.phase.value == 'disruption':
        print("⚠️ Novelty detected — rebuilding scripts")
    
    if len(data_stream) % 100 == 0:
        # Replay experiences to strengthen scripts
        buffer.replay(cycle, n=50)
        # Apply forgetting for unused scripts
        cycle.apply_forgetting()
```

## Advanced Modules

### Adversarial Snap (`snapkit.adversarial`)
Real vs fake delta detection with recursive theory-of-mind.

```python
from snapkit.adversarial import AdversarialDetector, BluffCalibration

detector = AdversarialDetector()
result = detector.observe_signal('player_1', 0.42, 1.2)
print(f"Fake: {result['classified_as_fake']}, Confidence: {result['confidence']:.2f}")

calibrator = BluffCalibration(max_depth=5)
response = calibrator.optimize_response(my_level=2, adversary_id='opponent')
```

### Real-Time Streaming (`snapkit.streaming`)
Sliding window stream processing with backpressure.

```python
from snapkit.streaming import StreamProcessor, StreamMonitor

monitor = StreamMonitor(total_budget=100.0)
monitor.add_stream('trades', snap=SnapFunction(tolerance=0.05))

for value in market_data_stream:
    monitor.observe('trades', value)
    alerts = monitor.check_alerts()
    for alert in alerts:
        print(f"⚠️ {alert.message}")

print(f"Utilization: {monitor.utilization:.1%}")
```

### Cross-Domain Transfer (`snapkit.crossdomain`)
Transfer snap topologies between domains.

```python
from snapkit.crossdomain import FeelTransfer

transfer = FeelTransfer()
poker_feel = transfer.domain_profile('poker')
driving_feel = transfer.calibrate(poker_feel, 'driving')
```

### Pipelines (`snapkit.pipeline`)
Composable processing pipelines with fluent builder.

```python
from snapkit.pipeline import PipelineBuilder

pipeline = (PipelineBuilder()
    .snap(tolerance=0.1)
    .detect()
    .prioritize(top_k=3)
    .allocate(budget_total=100.0)
    .execute()
    .build()
)

# Run values through the pipeline
for value in data_stream:
    ctx = pipeline.run(value)
    if ctx.deltas:
        print(f"Delta: {ctx.deltas[0].magnitude:.4f}")
```

### Visualization (`snapkit.visualization`)
Terminal and HTML reports with zero external dependencies.

```python
from snapkit.visualization import terminal_table, ascii_chart, html_report

# Tabular output
table = terminal_table(
    ['Stream', 'Deltas', 'Rate', 'Util'],
    [['stream_1', '12', '0.24', '0.31']],
    title="Snap Monitor Report",
)

# ASCII chart for terminal
chart = ascii_chart([0.1, 0.3, 0.2, 0.5, 0.4], width=40, height=10)

# Self-contained HTML report
with open('report.html', 'w') as f:
    f.write(html_report(data, title="SnapKit Analysis"))
```

### Serialization (`snapkit.serial`)
Save and load full library state.

```python
from snapkit.serial import save, load

# Save all state
save_all = {
    'snap': snap.to_dict(),
    'detector_state': {...},
    'budget_state': budget.statistics,
}
save(save_all, 'snap_state.json')

# Load state
loaded = load('snap_state.json')
restored = SnapFunction.from_dict(loaded['snap'])
```

## CLI

```bash
# Monitor streams in real-time
snapkit monitor --streams 5 --budget 100 --topology hexagonal

# Analyze results and generate HTML report
snapkit analyze results.json --html report.html

# Run demos
snapkit demo poker --hands 1000
snapkit demo learning --experiences 10000
snapkit demo adversarial

# Calibrate snap tolerance from data
snapkit calibrate data.json --target-rate 0.9 --output config.json

# Show version
snapkit status
```

## Installation

```bash
# From PyPI (once published)
pip install snapkit

# From source
git clone https://github.com/SuperInstance/snapkit.git
cd snapkit
pip install -e .

# With optional dependencies
pip install snapkit[sympy]    # SymPy integration
pip install snapkit[pysheaf]  # PySheaf integration
pip install snapkit[all]      # All extras
```

**Dependencies:** NumPy (required). SymPy and PySheaf are optional.

## Theory

snapkit implements the framework described in **[SNAPS-AS-ATTENTION.md](/research/SNAPS-AS-ATTENTION.md)** (Forgemaster & Digennaro, 2026).

Key theoretical results:
- **Tolerance-Compressed Attention Theorem:** Finite attention budget allocated to deltas exceeding tolerance
- **ADE Classification of Snap Topologies:** Aₙ, Dₙ, E₆/₇/₈ determine lattice geometry
- **Script Capacity Theorem:** Novelty rate determines maximum script capacity
- **Coarse-Graining Lemma:** H¹ vanishing implies snap functions are consistent sheaves

## Project Structure

```
snapkit/
├── __init__.py         # Package init, version, exports
├── snap.py             # SnapFunction — tolerance-compressed attention gate
├── delta.py            # DeltaDetector — tracks what exceeds tolerance
├── attention.py        # AttentionBudget — finite cognition allocation
├── scripts.py          # ScriptLibrary — learned automatic patterns
├── topology.py         # SnapTopology — ADE classification
├── learning.py         # LearningCycle — expertise cycle
├── cohomology.py       # ConstraintSheaf — consistency verification
├── adversarial.py      # Adversarial snap calibration
├── crossdomain.py      # Cross-domain feel transfer
├── streaming.py        # Real-time stream processing
├── visualization.py    # Terminal + HTML visualization
├── integration.py      # PySheaf/SymPy/Numpy integration
├── serial.py           # Serialization & persistence
├── pipeline.py         # Composable processing pipelines
├── cli.py              # Command-line interface
tests/
├── test_core.py        # Core module tests
├── test_advanced.py    # Advanced module tests
├── test_pipeline.py    # Pipeline tests
└── __init__.py
```

## License

MIT

## Credits

**Forgemaster ⚒️** — constraint theory specialist, Cocapn fleet
**Casey Digennaro** — creator, SuperInstance / PurplePincher.org
