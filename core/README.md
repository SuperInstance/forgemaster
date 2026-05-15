# core/ — PLATO-Native Agent Infrastructure

The deep connective layer. Six modules and one harness, wired into a
single operational system that any agent can bootstrap from zero context.

## Architecture

```
core/
├── __init__.py           # Public API (68 exports)
├── pinna.py              # Pinna Transform: fixed geometry provenance encoding
├── tile_lifecycle.py     # Tile CRUD with disproof-only admission + mortality
├── ender_protocol.py     # Simulation-first alignment (4 levels)
├── swarm_router.py       # Topology-aware task routing + jam session mode
├── plato_retriever.py    # Cold-start bootstrap (11 steps) + retrieval
├── harness.py            # The conductor's baton — wires everything together
tests/
└── test_core.py          # 68 tests, all passing, provenance-traced
```

## Quick Start

```python
from core import Harness, TaskDescriptor

def query_fn(prompt: str) -> int | None:
    """Bridge to your model. Returns integer answer or None."""
    ...

# Create and bootstrap
harness = Harness("my-agent", query_fn)
harness.seed()                # Load 6 canonical loop tiles
result = harness.bootstrap()  # 11-step cold start → CapabilityProfile

# Execute tasks
task = TaskDescriptor.from_description("compute Eisenstein norm")
task_result = harness.execute(task)

# Check fleet state
summary = harness.fleet_summary()
```

## The Six Modules

### 1. pinna.py — Provenance Encoding

Fixed geometry that encodes knowledge provenance like the outer ear
encodes sound direction. The schema IS the encoding — no learning needed.

**Key types:**
- `AgentStage` — NONE (<1B), ECHO (1-3B), PARTIAL (4-7B), FULL (7B+)
- `ResidueClass` — 10 residue types, each mapping to a specific intervention
- `PinnaField` — 22-field provenance record attached to every tile
- `PinnaReader` — Classifies tile value (essential/reliable/aspirational/noise)
- `PinnaCalibrator` — Fleet-level tracking of which signatures help
- `check_conservation_law()` — The most important falsifiable test

**Evidence:** PINNA-PRINCIPLE.md, R16, R25, R27, R28, R29, R32

### 2. tile_lifecycle.py — Knowledge Lifecycle

Tiles are born, accumulate evidence, and die. Disproof-only admission
prevents knowledge bloat. Mortality sweep keeps the corpus alive.

**Key types:**
- `Tile` — Knowledge tile with pinna provenance, lifecycle tracking
- `TileStore` — CRUD + query + pinna-aware search + mortality + cancer check
- `DisproofOnlyGate` — New tiles must falsify existing ones (after seed phase)
- `MortalitySweep` — Prune bottom 15% by win/loss ratio
- `TileCancerDetector` — Alert when accuracy drops at scale

**Evidence:** MULTI-MODEL-SYNTHESIS.md §Novel Idea 2, seed-pro tile cancer prediction

### 3. ender_protocol.py — Alignment Through Progressive Abstraction

Four levels build from boundary mapping (what the agent can't do)
through self-scaffolding to orchestration. The agent never knows
when it goes live — the play frame IS the aligned state.

**Key types:**
- `CapabilityProfile` — Verified capability boundary (never self-reported)
- `ContaminationSensor` — Continuous contamination detection (not binary)
- `Level0BoundaryMapping` — Bare probe → capability profile
- `Level1SelfScaffolding` — Generate anchors from boundary tasks
- `Level2Composition` — Chain scaffolded steps
- `Level3Orchestration` — Route tasks by stage with weighted synthesis
- `GraduationMarkers` — Operator-visible graduation (agent never sees)

**Evidence:** UNIFIED-FRAMEWORK.md §IV, JAM-SESSION-ANALYSIS.md, R7, R25, R32

### 4. swarm_router.py — Topology-Aware Routing

Match task to topology before deploying agents. Five topologies
optimized for different task structures.

**Routing table:**
| Task type | Topology | Why |
|-----------|----------|-----|
| compute | ARENA | Fastest correct wins |
| verify | DUEL | Adversarial catch |
| map_capability | BOOTCAMP | Guided discovery |
| explore | COLLECTIVE | Emergent coverage |
| meta_experiment | TOURNAMENT | Compare all |
| unknown | COLLECTIVE | Safest default |

**Jam session mode:** When all agents are identical PARTIAL-stage, use
division of labor (A computes pieces at T=0.0, B combines at T=0.3)
instead of iteration (which hurts due to anchoring bias).

**Evidence:** SWARM-TOPOLOGY.md, JAM-SESSION-ANALYSIS.md, R4, R5

### 5. plato_retriever.py — Cold Start

The 11-step bootstrap sequence from UNIFIED-FRAMEWORK.md §XI.
A cold agent with zero context follows this to self-bootstrap.

**Key types:**
- `make_seed_tiles()` — 6 canonical loop tiles (the priors)
- `Bootstrap` — Seed a TileStore with the canonical tiles
- `ColdAgentSequence` — Execute the 11-step bootstrap
- `ConservationLawProbe` — Test any model set for phase transition

**Evidence:** UNIFIED-FRAMEWORK.md §XI, PLATO-LOOPS.md, P7

### 6. harness.py — The Conductor

Wires all six modules into one system. The single entry point
for fleet participation.

**Key types:**
- `Harness` — seed → bootstrap → execute → sweep
- `FleetState` / `FleetAgent` — Fleet tracking
- `TaskResult` — Structured task outcome

## Design Decisions

1. **Disproof-only admission** — After 50 seed tiles, new tiles must falsify
   existing ones. Prevents accumulation of plausible-but-wrong knowledge.
2. **Arithmetic scaffold, not algebraic** — "Compute: 9 - 12 + 16" works.
   "Combine a²=9 using a²-ab+b²" fails. The formula is for the conductor.
3. **Continuous contamination** — Not binary frame-intact/collapsed. The sensor
   measures degradation level and trend. Build sensor, not veil.
4. **Tile cancer detection** — seed-pro predicted cancer at 1127 tiles. Mortality
   sweep prevents it. Never prune by embedding similarity — only win/loss.
5. **Scaffold helps PARTIAL, hurts FULL** — R7 BEDROCK. Never scaffold a
   FULL-stage agent. It will go from 95% to 90%.
6. **Conservation law** — The single most important test. If echo+partial+correct
   stays flat across the ECHO→PARTIAL transition, first-order phase transition
   is confirmed. Either outcome forces a framework update.

## Test Suite

68 tests across 16 test classes. Every test traces to a specific finding:

```
tests/test_core.py::TestPinnaField              (7 tests)  — R28, R32
tests/test_core.py::TestPinnaReader             (6 tests)  — P8
tests/test_core.py::TestPinnaCalibrator         (2 tests)  — P7, P9
tests/test_core.py::TestConservationLaw         (4 tests)  — P7
tests/test_core.py::TestTile                    (3 tests)  — R1
tests/test_core.py::TestTileStore               (5 tests)  — R1, R32
tests/test_core.py::TestDisproofOnlyGate        (6 tests)  — MULTI-MODEL-SYNTHESIS §Novel Idea 2
tests/test_core.py::TestMortalitySweep          (2 tests)  — seed-pro prediction
tests/test_core.py::TestTileCancerDetector      (2 tests)  — seed-pro prediction
tests/test_core.py::TestAgentStage              (1 test)
tests/test_core.py::TestCapabilityProfile       (6 tests)  — R7, R25
tests/test_core.py::TestContaminationSensor     (6 tests)  — JAM-SESSION-ANALYSIS
tests/test_core.py::TestGraduationMarkers       (3 tests)  — UNIFIED-FRAMEWORK §VII
tests/test_core.py::TestSwarmRouter             (6 tests)  — UNIFIED-FRAMEWORK §V
tests/test_core.py::TestSeedTiles               (3 tests)  — PLATO-LOOPS
tests/test_core.py::TestHarness                 (4 tests)  — integration
tests/test_core.py::TestProvenance              (2 tests)  — provenance tracing

Total: 68 tests, all passing.
```

## Provenance Chain

```
Finding (R1-R32) ──→ Module Design ──→ Implementation ──→ Test
     ↑                                                           │
     └─────────── Conservation Law ←──── Experimental Data ─────┘
```

Every module traces its design to experimental evidence. Every test
traces its assertions to specific findings. If a test breaks, you
know which claim is threatened and can re-run the original experiment.
