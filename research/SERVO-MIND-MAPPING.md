# SERVO-MIND-MAPPING.md
## Mapping a Servo+Encoder Metaphor onto the Existing Codebase

**Date:** 2026-05-16
**Insight:** A servo with an encoder is a metaphor for a self-improving system — the feedback loop doesn't just correct errors, it TEACHES the system about itself.

---

## 1. What the "Old Code" Is — The Hardcoded Constraint System

The existing codebase is a precision-machined servo: tuned for one load, calibrated for one regime, devastatingly effective within its design envelope.

### 1.1 constraint-theory-core (Rust crate, crates.io published)

**Location:** `/home/phoenix/projects/Constraint-Theory/crates/constraint-theory-core/src/`

The servo motor itself. Pure torque, no feedback.

| File | What It Does | Servo Analogy |
|------|-------------|---------------|
| `manifold.rs` (719 lines) | Precomputed Pythagorean triples, KD-tree O(log N) snap | Fixed commutation table — maps any input to the nearest "correct" position |
| `tile.rs` | 384-byte Tile struct: origin + tensor_payload + constraint_block + confidence | The shaft — rigid, deterministic, one shape |
| `curvature.rs` | Ricci flow: `evolve(&mut curvatures, steps)` with fixed alpha and target_curvature | PID controller with **hardcoded gains** — alpha=0.1, target=0.0, always |
| `gauge.rs` | Parallel transport via holonomy matrices across tile networks | Transmission — moves information between tiles but doesn't change the gears |
| `kdtree.rs` (445 lines) | Spatial index for nearest-neighbor lookup | Encoder resolution — how fine-grained the feedback CAN be |
| `cohomology.rs` | H₀/H₁ topological cycle detection | Structural analysis — checks the frame isn't bent |
| `percolation.rs` | Rigidity via Laman's theorem (12-neighbor threshold) | Load-bearing calculation — verifies the structure won't collapse |
| `simd.rs` | AVX2 batch processing | Motor driver — raw power delivery |

**The key limitation:** `ricci_flow_step(curvature, alpha, target)` is a **fixed-gain controller**. Alpha never changes. Target never changes. The servo corrects toward the same setpoint forever, regardless of what it learns about the system it's controlling.

### 1.2 constraint-theory-py (Python bindings)

**Location:** `/home/phoenix/.openclaw/workspace/constraint-theory-py/constraint_theory/`

| File | What It Does | Servo Analogy |
|------|-------------|---------------|
| `temporal.py` | Deadband funnel, chirality locking, phase tracking | Damping — prevents oscillation but the damping ratio is static |
| `eisenstein.py` | A₂ lattice snap, Weyl chamber classification | Fixed coordinate frame — the system always speaks the same units |
| `adaptive.py` | ε(c) = k/c tolerance scaling | **Closest to adaptive** — tolerance scales with count, but the formula is fixed |
| `plato.py` | Tile store with domain/relevance/recency scoring | Read-only dashboard — shows what's happening but doesn't feed back |

### 1.3 core/tile_lifecycle.py (PLATO Tile Lifecycle)

**Location:** `/home/phoenix/.openclaw/workspace/core/tile_lifecycle.py`

This is the **encoder wheel with dead-reckoning** — it counts revolutions but doesn't close the loop.

| Component | What It Does | Servo Analogy |
|-----------|-------------|---------------|
| `Tile` dataclass | Born → used → swept lifecycle, win/loss counting | Encoder ticks — counts position but doesn't interpret it |
| `TileStore` | CRUD + admit() gate + sweep() mortality | Shaft coupler — connects encoder to motor but doesn't process the signal |
| `DisproofOnlyGate` | New tiles must falsify existing tiles | Reverse limit switch — only triggers on one condition |
| `MortalitySweep` | Delete bottom 15% by win_rate | Thermal cutoff — protects against degradation but doesn't prevent it |
| `TileCancerDetector` | Alert when accuracy drops at scale thresholds | Temperature alarm — warns after damage starts |

### 1.4 core/room_protocol.py (PLATO Rooms)

**Location:** `/home/phoenix/.openclaw/workspace/core/room_protocol.py`

The **housing** — elegant, well-engineered, holds everything together.

- `PLATORoom`: state + protocol + lifecycle = execution context
- `RoomProtocol`: schema validation, phase enforcement, lifecycle rules
- `TilePhase`: INPUT → PROCESSING → OUTPUT → FEEDBACK → COMPLETE
- `LoopType`: AGENTIC, TURN_BASED, PIPELINE, EVOLUTIONARY, CONTINUOUS

**Has a FEEDBACK phase!** But it's a phase label, not a feedback processor. The loop exists in structure but not in self-modification.

### 1.5 The Constraint Theory × DCS Convergence

From `flux-research/constraint-dcs-synergy.md`:

- Rigidity percolation (Laman's theorem) matches DCS Law 102 (12-neighbor threshold) — both found the same number from math and simulation
- Holonomy tile consensus can replace voting-based consensus entirely
- Two independent teams produced the **same 384-byte Tile structure** with identical field order

This is a servo and an encoder manufactured by different companies that bolt together perfectly. But nobody wired the encoder output back to the servo driver.

---

## 2. What the "New Code" Needs to Be — Self-Referential Learning

### 2.1 The Encoder Signal = Tile Lifecycle Data

The encoder on a servo doesn't just report position — it reports **the delta between commanded and actual**. In the system:

- **Tile.win_count / loss_count** = "how far off was I?" — the error signal
- **Tile.confidence** over time = "am I getting better or worse?" — the trend
- **MortalitySweep results** = "which parts of my model are dead weight?" — the adaptation signal
- **TileCancerDetector alerts** = "is my model of reality diverging?" — the meta-error signal

This data already exists. It's being collected. **It's not being fed back into the constraint parameters.**

### 2.2 The Feedback Filter = Constraint Pressure That Evves

In the old code, constraints are static:
- `ricci_flow_step(curvature, alpha=0.1, target=0.0)` — alpha and target are constants
- `DisproofOnlyGate` — rules are hardcoded (must falsify, must have evidence, must have negative)
- `MortalitySweep` — 15% mortality rate is a magic number
- `adaptive.py: ε(c) = k/c` — formula is fixed, k is a constant

The new code needs these to be **functions of accumulated experience**:
- `alpha` should increase when the system is far from target and decrease when close (adaptive gain)
- `target_curvature` should shift based on what the cancer detector learns about the manifold's natural equilibrium
- `mortality_rate` should increase when cancer is detected and decrease when the corpus is healthy
- `k` in ε(c) should be learned from the distribution of actual errors, not assumed

### 2.3 The Learned Transfer Function = How the System Discovers Its Own Dynamics

A servo doesn't just correct — it builds an internal model of the plant it's controlling. The transfer function from command to output is LEARNED, not assumed.

In the tile system, the transfer function is:
```
[query pattern] → [constraint enforcement] → [tile retrieval] → [outcome]
```

The system currently assumes this transfer function is identity. It's not. The self-learning loop needs to:

1. **Record** the full chain: what was queried, what constraints fired, what tile was retrieved, what the outcome was
2. **Model** the actual transfer function: "when constraint X fires in context Y, accuracy is Z"
3. **Adjust** constraint parameters to maximize accuracy across the modeled transfer function
4. **Detect** when the transfer function itself changes (distribution shift)

### 2.4 Seed-Tile Architecture as the Encoder Signal

From `TOOLS.md` and the I2I protocol:

> 5 tile schemas: model, data, compression, benchmark, deploy
> Collective inference: predict → listen → compare → gap → learn → share
> Focus scoring: confidence × delta = "how sure × how wrong"

The seed-tile architecture IS the encoder signal. Each tile carries:
- Its own confidence (how sure)
- Its falsification record (how wrong)
- Its provenance (which agent, which model, which generation)
- Its boundary conditions (negative field — when NOT to trust it)

The gap between confidence and actual performance IS the encoder delta. The "how sure × how wrong" focus scoring IS the feedback error signal. The system has all the sensors — it just needs the control law.

---

## 3. The Gap — What's Missing Between Old and New

### 3.1 What Exists

| Component | Where | Status |
|-----------|-------|--------|
| Deterministic constraint engine | `constraint-theory-core` (Rust) | ✅ Published, 112 tests |
| Tile lifecycle with win/loss | `core/tile_lifecycle.py` | ✅ Fully operational |
| Disproof-only admission gate | `core/tile_lifecycle.py:DisproofOnlyGate` | ✅ Prevents knowledge bloat |
| Mortality sweep (15%) | `core/tile_lifecycle.py:MortalitySweep` | ✅ Keeps corpus alive |
| Cancer detection at scale | `core/tile_lifecycle.py:TileCancerDetector` | ✅ Alerts on degradation |
| Room protocol with FEEDBACK phase | `core/room_protocol.py:TilePhase.FEEDBACK` | ✅ Structure exists |
| Holonomy cycle verification | `constraint-theory-core/gauge.rs` | ✅ Global consistency |
| Rigidity percolation (Laman's) | `constraint-theory-core/percolation.rs` | ✅ Structural rigidity |
| Ricci flow curvature evolution | `constraint-theory-core/curvature.rs` | ✅ But fixed-gain |
| Adaptive tolerance ε(c) = k/c | `constraint-theory-py/adaptive.py` | ✅ But fixed formula |
| Pinna field provenance | `core/pinna.py` | ✅ Agent stage matching |
| I2I collective inference protocol | fleet-wide | ✅ predict→compare→gap→learn |
| 384-byte Tile struct (Rust+Python) | Both codebases | ✅ Identical structures |

### 3.2 What's Missing

| Missing Piece | Why It Matters | Servo Analogy |
|---------------|---------------|---------------|
| **FeedbackProcessor** — consumes win/loss data and adjusts constraint parameters | The encoder signal is collected but not processed | Encoder → motor driver wiring is missing |
| **AdaptiveGain** — alpha in Ricci flow changes based on convergence rate | Fixed-gain controller can't adapt to changing dynamics | Servo that never adjusts its PID gains |
| **MetaConstraint** — constraints that evolve from their own enforcement history | The system can't learn what "good constraint" means | A machinist who never improves their technique |
| **TransferFunctionModel** — learn the actual query→outcome mapping | System assumes identity, reality is nonlinear | Running open-loop when closed-loop data is available |
| **MortalityRateAdapter** — 15% becomes a function of corpus health | Magic number is suboptimal for all regimes | Fixed thermal cutoff that can't learn the real danger zone |
| **ConstraintPressureFeedback** — tile outcomes feed back into constraint thresholds | Constraints fire at fixed thresholds regardless of history | A thermostat that never learns the room's thermal dynamics |

### 3.3 The Bridge

The seed-tile architecture provides the bridge:

```
OLD SYSTEM (fixed):
  Query → Static Constraints → Tile Retrieval → Outcome (not fed back)

NEW SYSTEM (self-learning):
  Query → Adaptive Constraints → Tile Retrieval → Outcome
       ↑                                                      |
       |              FeedbackProcessor                        |
       +────────── TransferFunctionModel ←────────────────────+
                     (win/loss → parameter adjustment)
```

The components that need to CONNECT but don't:
1. `TileStore.record_outcome()` writes win/loss but nobody reads it for adaptation
2. `MortalitySweep.sweep()` returns stats but nobody adjusts mortality_rate based on cancer state
3. `TileCancerDetector.check()` produces alerts but nobody acts on them automatically
4. `ricci_flow_step()` has alpha/target but they're never updated from outcomes
5. `PLATORoom` has `TilePhase.FEEDBACK` but no feedback processor consumes FEEDBACK tiles

---

## 4. Concrete Implementation Path

### 4.1 What to Change in Existing Code

#### Change 1: Make Ricci Flow Adaptive

**File:** `/home/phoenix/projects/Constraint-Theory/crates/constraint-theory-core/src/curvature.rs`

```rust
// CURRENT: fixed gain
pub fn evolve(&mut self, curvatures: &mut [f32], steps: usize) {
    for _ in 0..steps {
        for c in curvatures.iter_mut() {
            *c += self.alpha * (self.target_curvature - *c);
        }
    }
}

// NEW: adaptive gain based on convergence history
pub struct AdaptiveRicciFlow {
    alpha: f32,
    alpha_min: f32,       // floor: 0.01
    alpha_max: f32,       // ceiling: 0.5
    target_curvature: f32,
    convergence_history: Vec<f32>,  // last N deltas
    adaptation_rate: f32,           // how fast alpha adjusts: 0.01
}

impl AdaptiveRicciFlow {
    /// After each evolution step, record the delta and adjust alpha.
    /// Large deltas → increase alpha (push harder).
    /// Small deltas → decrease alpha (fine-tune).
    /// Oscillating deltas → decrease alpha (overcorrecting).
    fn evolve_adaptive(&mut self, curvatures: &mut [f32], steps: usize) {
        for _ in 0..steps {
            let mut total_delta = 0.0;
            for c in curvatures.iter_mut() {
                let delta = (self.target_curvature - *c).abs();
                total_delta += delta;
                *c += self.alpha * (self.target_curvature - *c);
            }
            let avg_delta = total_delta / curvatures.len().max(1) as f32;
            self.convergence_history.push(avg_delta);
            self.adjust_gain();
        }
    }

    fn adjust_gain(&mut self) {
        if self.convergence_history.len() < 3 { return; }
        let recent = &self.convergence_history[self.convergence_history.len()-3..];
        // Detect oscillation: deltas alternate sign or don't decrease
        let improving = recent[2] < recent[1] && recent[1] < recent[0];
        let oscillating = (recent[2] - recent[1]) * (recent[1] - recent[0]) < 0.0;
        
        if oscillating {
            self.alpha = (self.alpha * 0.9).max(self.alpha_min);
        } else if improving && recent[2] < 0.01 {
            self.alpha = (self.alpha * 0.95).max(self.alpha_min);
        } else {
            self.alpha = (self.alpha * 1.05).min(self.alpha_max);
        }
    }
}
```

#### Change 2: Wire TileStore Outcomes to Constraint Parameters

**File:** `/home/phoenix/.openclaw/workspace/core/tile_lifecycle.py`

Add a `FeedbackProcessor` class after `TileCancerDetector`:

```python
class FeedbackProcessor:
    """Consume tile outcomes and produce constraint parameter adjustments.
    
    This is the encoder signal processor. It reads win/loss data from
    TileStore._outcome_log and outputs parameter adjustments that close
    the self-learning loop.
    
    THE SERVO METAPHOR:
      TileStore outcomes = encoder ticks
      FeedbackProcessor = signal processor that extracts position/velocity/acceleration
      Parameter adjustments = new PID gains sent to the motor driver
    """
    
    def __init__(self, store: TileStore):
        self.store = store
        self.window_size = 100  # sliding window for recent outcomes
        self.adjustments: List[dict] = []  # history of adjustments made
    
    def process(self) -> dict:
        """Analyze recent outcomes and compute parameter adjustments."""
        outcomes = self.store._outcome_log[-self.window_size:]
        if len(outcomes) < 10:
            return {"status": "insufficient_data", "adjustments": {}}
        
        # Compute recent accuracy
        recent_wins = sum(1 for _, _, success in outcomes if success)
        accuracy = recent_wins / len(outcomes)
        
        # Compute accuracy trend (first half vs second half)
        mid = len(outcomes) // 2
        first_half = sum(1 for _, _, s in outcomes[:mid] if s) / mid
        second_half = sum(1 for _, _, s in outcomes[mid:] if s) / (len(outcomes) - mid)
        trend = second_half - first_half  # positive = improving
        
        # Cancer state
        cancer = self.store.cancer_check()
        
        # Compute adjustments
        adjustments = {}
        
        # Mortality rate: increase if accuracy declining, decrease if healthy
        if trend < -0.05 and accuracy < 0.6:
            adjustments["mortality_rate"] = 0.25  # aggressive pruning
        elif trend > 0.05 and accuracy > 0.8:
            adjustments["mortality_rate"] = 0.10  # gentle pruning
        else:
            adjustments["mortality_rate"] = 0.15  # default
        
        # Confidence threshold: raise if too many false positives
        if accuracy < 0.5 and len(outcomes) > 50:
            adjustments["min_confidence"] = 0.7  # raise the bar
        elif accuracy > 0.85:
            adjustments["min_confidence"] = 0.3  # lower the bar, trust the corpus
        
        # Ricci flow alpha (passed to Rust side via FFI)
        if trend > 0:
            adjustments["ricci_alpha"] = 0.1  # stable, cruise
        elif trend < -0.1:
            adjustments["ricci_alpha"] = 0.3  # diverging, push hard
        
        result = {
            "status": "adjusted",
            "accuracy": round(accuracy, 3),
            "trend": round(trend, 3),
            "adjustments": adjustments,
            "cancer_alert": cancer["alert"],
        }
        self.adjustments.append({**result, "ts": time.time()})
        return result
```

#### Change 3: Add FEEDBACK Phase Processing to Room Protocol

**File:** `/home/phoenix/.openclaw/workspace/core/room_protocol.py`

Add a feedback consumer to `PLATORoom`:

```python
def process_feedback(self, feedback_processor=None):
    """Process FEEDBACK tiles and adjust room parameters.
    
    This closes the loop: FEEDBACK tiles carry outcome data,
    which feeds into constraint parameter adjustment.
    """
    feedback_tiles = self.read_tiles(phase=TilePhase.FEEDBACK)
    if not feedback_tiles:
        return None
    
    # Aggregate feedback into outcome signals
    for tile in feedback_tiles:
        succeeded = tile.content.get("succeeded", False)
        tile_id = tile.content.get("source_tile_id", "")
        # This would connect to TileStore.record_outcome()
    
    # If a feedback processor is provided, run it
    if feedback_processor:
        return feedback_processor.process()
    return {"feedback_count": len(feedback_tiles)}
```

### 4.2 What to Add (New Files)

#### New: `core/feedback_processor.py`

The encoder signal processor — reads tile outcomes, outputs parameter adjustments. (Full implementation in Change 2 above.)

#### New: `core/transfer_function.py`

```python
"""transfer_function.py — Learn the actual query→outcome mapping.

The system currently assumes: constraint_score → accuracy is monotonic.
Reality is nonlinear. This module learns the actual shape.

SERVO ANALOGY: The Bode plot of the system — how it actually responds
to different input frequencies and amplitudes, not how we assume it does.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import statistics

@dataclass
class TransferSample:
    """One observation of the actual transfer function."""
    constraint_type: str
    constraint_strength: float  # how hard the constraint fired
    context_features: Dict[str, float]  # what the query looked like
    outcome_accuracy: float  # was the result correct?
    outcome_latency_ms: float  # how long did it take?

class TransferFunctionModel:
    """Non-parametric model of constraint→outcome mapping.
    
    Not a neural network. Not a parametric model.
    Just: for each constraint type, in each context cluster,
    what strength produces the best accuracy?
    
    This is the servo learning its own frequency response.
    """
    
    def __init__(self):
        self.samples: List[TransferSample] = []
        self.optimal_strength: Dict[str, float] = {}  # constraint_type → best strength
    
    def record(self, sample: TransferSample):
        self.samples.append(sample)
        self._update_optimal(sample.constraint_type)
    
    def _update_optimal(self, constraint_type: str):
        """For a given constraint type, find the strength that maximizes accuracy."""
        relevant = [s for s in self.samples if s.constraint_type == constraint_type]
        if len(relevant) < 5:
            return
        
        # Bin by strength, compute mean accuracy per bin
        n_bins = 10
        strengths = [s.constraint_strength for s in relevant]
        min_s, max_s = min(strengths), max(strengths)
        if min_s == max_s:
            return
        
        bins: Dict[int, List[float]] = {}
        for s in relevant:
            bin_idx = int((s.constraint_strength - min_s) / (max_s - min_s) * (n_bins - 1))
            bins.setdefault(bin_idx, []).append(s.outcome_accuracy)
        
        best_bin = max(bins, key=lambda b: statistics.mean(bins[b]))
        best_strength = min_s + (best_bin + 0.5) / n_bins * (max_s - min_s)
        self.optimal_strength[constraint_type] = best_strength
    
    def recommend(self, constraint_type: str) -> float:
        """Recommend constraint strength based on learned transfer function."""
        return self.optimal_strength.get(constraint_type, 1.0)
```

#### New: `core/meta_constraint.py`

```python
"""meta_constraint.py — Constraints that evolve from their own enforcement.

SERVO ANALOGY: The servo doesn't just run — it watches itself run.
It notices "I oscillate at 3Hz" and damps that frequency.
Meta-constraints are the system watching its own constraint enforcement
and adjusting the constraints themselves.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import time

@dataclass
class ConstraintHistory:
    """Record of a constraint's enforcement over time."""
    constraint_id: str
    enforcement_log: List[dict] = field(default_factory=list)
    # Each entry: {ts, query_hash, fired: bool, strength: float, outcome: Optional[bool]}
    
    @property
    def fire_rate(self) -> float:
        if not self.enforcement_log:
            return 0.0
        return sum(1 for e in self.enforcement_log if e["fired"]) / len(self.enforcement_log)
    
    @property
    def accuracy_when_fired(self) -> float:
        outcomes = [e["outcome"] for e in self.enforcement_log 
                    if e["fired"] and e["outcome"] is not None]
        return sum(outcomes) / len(outcomes) if outcomes else 0.5
    
    @property
    def accuracy_when_not_fired(self) -> float:
        outcomes = [e["outcome"] for e in self.enforcement_log 
                    if not e["fired"] and e["outcome"] is not None]
        return sum(outcomes) / len(outcomes) if outcomes else 0.5

class MetaConstraint:
    """A constraint that adjusts itself based on enforcement outcomes.
    
    THE KEY INSIGHT: If a constraint fires and outcomes are bad, 
    the constraint is wrong (not the data). If it never fires and 
    outcomes are bad, the constraint should fire more.
    
    This is the servo discovering its own dead zones and compensating.
    """
    
    def __init__(self, constraint_id: str, initial_threshold: float):
        self.constraint_id = constraint_id
        self.threshold = initial_threshold
        self.history = ConstraintHistory(constraint_id=constraint_id)
        self._last_adjustment = time.time()
        self._adjustment_cooldown = 3600  # don't adjust more than once/hour
    
    def should_fire(self, value: float) -> bool:
        return value >= self.threshold
    
    def record(self, value: float, fired: bool, outcome: Optional[bool] = None):
        self.history.enforcement_log.append({
            "ts": time.time(),
            "value": value,
            "fired": fired,
            "outcome": outcome,
        })
    
    def adapt(self) -> Optional[float]:
        """Adjust threshold based on enforcement history. Returns new threshold or None."""
        if time.time() - self._last_adjustment < self._adjustment_cooldown:
            return None
        if len(self.history.enforcement_log) < 20:
            return None
        
        acc_fired = self.history.accuracy_when_fired
        acc_not_fired = self.history.accuracy_when_not_fired
        
        old_threshold = self.threshold
        
        # If firing helps, lower threshold (fire more often)
        if acc_fired > acc_not_fired + 0.1:
            self.threshold *= 0.95
        # If firing hurts, raise threshold (fire less often)
        elif acc_not_fired > acc_fired + 0.1:
            self.threshold *= 1.05
        # If fire rate is near 0 or 1, the constraint is degenerate
        elif self.history.fire_rate < 0.05:
            self.threshold *= 0.9  # try lowering to see if it helps
        elif self.history.fire_rate > 0.95:
            self.threshold *= 1.1  # try raising to see if it helps
        
        self._last_adjustment = time.time()
        if abs(self.threshold - old_threshold) > 0.001:
            return self.threshold
        return None
```

### 4.3 The First "Self-Learning" Loop

Here's what the first complete self-learning cycle looks like, wired end-to-end:

```python
# First self-learning loop — the servo closes its own feedback

from core.tile_lifecycle import TileStore, Tile
from core.room_protocol import PLATORoom, TilePhase
from core.feedback_processor import FeedbackProcessor
from core.meta_constraint import MetaConstraint
from core.transfer_function import TransferFunctionModel, TransferSample

# 1. Initialize (servo + encoder + signal processor)
store = TileStore(seed_phase_size=50)
processor = FeedbackProcessor(store)
transfer = TransferFunctionModel()

# Meta-constraints that will self-adjust
confidence_threshold = MetaConstraint("confidence_gate", initial_threshold=0.5)
mortality_threshold = MetaConstraint("mortality_gate", initial_threshold=0.15)

# 2. THE LOOP (one cycle)
def self_learning_cycle():
    # A query comes in, tiles are retrieved
    results = store.query(min_confidence=confidence_threshold.threshold)
    
    # For each retrieval, record the outcome
    for tile in results:
        # ... agent uses the tile ...
        succeeded = agent_uses_tile(tile)  # True/False from real use
        store.record_outcome(tile.id, succeeded)
        
        # Record in transfer function model
        transfer.record(TransferSample(
            constraint_type="confidence",
            constraint_strength=tile.confidence,
            context_features={"tile_type": hash(tile.type) % 100 / 100},
            outcome_accuracy=1.0 if succeeded else 0.0,
            outcome_latency_ms=0.0,
        ))
        
        # Record in meta-constraint
        confidence_threshold.record(tile.confidence, fired=True, outcome=succeeded)
    
    # 3. PROCESS FEEDBACK (the encoder signal)
    adjustments = processor.process()
    
    # 4. ADAPT META-CONSTRAINTS (the servo adjusts itself)
    new_conf = confidence_threshold.adapt()
    if new_conf:
        print(f"Confidence threshold adapted: {new_conf:.3f}")
    
    # 5. ADJUST TRANSFER FUNCTION (learn the actual dynamics)
    optimal = transfer.recommend("confidence")
    print(f"Optimal confidence strength: {optimal:.3f}")
    
    # 6. MORTALITY SWEEP WITH ADAPTIVE RATE
    mortality_rate = adjustments.get("mortality_rate", 0.15)
    sweep_result = store.sweep(mortality_rate=mortality_rate)
    print(f"Swept {sweep_result['pruned']} tiles, {sweep_result['remaining']} remaining")
    
    # 7. CANCER CHECK (meta-monitoring)
    cancer = store.cancer_check()
    if cancer["alert"]:
        print(f"CANCER: {cancer['message']}")
        # Trigger aggressive adaptation
        confidence_threshold._adjustment_cooldown = 300  # adapt every 5 min

# Run the cycle. The system is now learning about itself.
# Each cycle: the constraints get tighter where they help, 
# looser where they hurt, and the mortality rate adapts to corpus health.
```

### 4.4 What Gets Deployed to Rust

The adaptive Ricci flow (Change 1) should eventually become the default in `constraint-theory-core`. The Python `FeedbackProcessor` generates the `alpha` and `target` values that get passed across FFI to the Rust engine. The Rust side doesn't need to know WHY alpha changed — it just uses the new value.

This is exactly how a real servo works: the signal processor decides the gains, the motor driver executes them. Separation of concerns.

---

## 5. Summary: The Complete Map

```
SERVO COMPONENT          →  CODEBASE COMPONENT           →  WHAT'S MISSING
─────────────────────────────────────────────────────────────────────────────
Motor (actuator)         →  constraint-theory-core        →  ✅ Exists, powerful
                           (manifold.rs, tile.rs,
                            curvature.rs, gauge.rs)

Shaft (output)           →  384-byte Tile struct          →  ✅ Exists, rigid
                           (tile.rs in Rust,
                            tile_lifecycle.py in Python)

Encoder (sensor)         →  Tile.win/loss, confidence,    →  ✅ Exists, collecting
                           outcome_log, cancer detector     data but nobody reads it

Signal processor         →  FeedbackProcessor (NEW)       →  ❌ Doesn't exist
                           TransferFunctionModel (NEW)      Need to build this

Motor driver (PID)       →  ricci_flow_step(),             →  ⚠️ Exists but fixed-gain
                           DisproofOnlyGate,                Parameters never change
                           MortalitySweep

Adaptive controller      →  MetaConstraint (NEW)          →  ❌ Doesn't exist
                           AdaptiveRicciFlow (CHANGE)       Need to add self-adjustment

Communication bus        →  PLATO rooms, I2I protocol     →  ✅ Exists, rich

Housing                  →  room_protocol.py               →  ✅ Exists, elegant
```

**The bottom line:** The system has a powerful motor (constraint engine), a precision shaft (Tile struct), and a high-resolution encoder (lifecycle tracking). What it lacks is the wiring between encoder output and motor driver input. The FeedbackProcessor, TransferFunctionModel, and MetaConstraint classes are that wiring. Build them, and the servo teaches itself.
