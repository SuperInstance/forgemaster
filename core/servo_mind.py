#!/usr/bin/env python3
"""core/servo_mind.py — The encoder feedback processor for PLATO tiles.

The servo-mind closes the loop that was always open:
  - TileStore collects win/loss outcomes (encoder ticks)
  - FeedbackProcessor reads them and computes parameter adjustments (signal processor)
  - MetaConstraints adapt their own thresholds from enforcement history (adaptive PID)
  - TransferFunctionModel learns the actual query→outcome mapping (Bode plot)
  - ServoMind orchestrates the cycle (the controller)

THE METAPHOR:
  A servo with an encoder doesn't just move — it knows where it IS.
  The encoder measures the GAP between commanded and actual.
  That gap IS the system's self-knowledge.
  Each correction teaches the system about its own dynamics.

THE INSIGHT:
  The original code was good enough for the job (fixed-gain PID).
  This new code learns new jobs by learning its own system better.
  Pressure in the system is a FILTER with FEEDBACK — like an encoder
  on a servo where the servo IS the arm of the robot.

THE FIVE DIMENSIONS:
  X, Y, Z — space (where in the lattice)
  T       — time (Lamport clock ordering)
  S       — scale (room ↔ tile folding)
  This module operates on S — it adjusts the system's own parameters,
  which changes how rooms fold/unfold, how tiles get named, and how
  constraints evolve.

Usage:
    from core.servo_mind import ServoMind
    mind = ServoMind(store)
    mind.cycle()  # one encoder reading + adaptation
    mind.run(n=100)  # continuous operation
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


# ─── FeedbackProcessor — reads encoder signal, outputs adjustments ────────────

@dataclass
class FeedbackSnapshot:
    """One reading from the encoder — a moment in the system's self-knowledge."""
    timestamp: float
    tile_count: int
    total_wins: int
    total_losses: int
    overall_win_rate: float
    recent_win_rate: float  # last N outcomes
    cancer_alert: bool
    cancer_message: str
    avg_confidence: float
    std_confidence: float
    type_distribution: Dict[str, int]


@dataclass
class ParameterAdjustment:
    """An adjustment to a system parameter, derived from encoder feedback."""
    parameter: str
    old_value: float
    new_value: float
    reason: str
    confidence: float  # how confident the adjustment is (0-1)


class FeedbackProcessor:
    """Reads tile outcomes and computes parameter adjustments.

    This is the signal processor between encoder and motor driver.
    It takes the raw outcome stream and produces actionable parameter changes.

    The encoder signal = TileStore._outcome_log + win/loss counts + cancer state
    The motor driver = constraint parameters (mortality_rate, confidence_thresholds, etc.)
    This processor is the wiring between them.
    """

    def __init__(
        self,
        window_size: int = 100,       # how many recent outcomes to consider
        adaptation_rate: float = 0.1,  # how fast to adjust (learning rate)
        min_samples: int = 20,         # minimum outcomes before adapting
    ):
        self.window_size = window_size
        self.adaptation_rate = adaptation_rate
        self.min_samples = min_samples
        self.history: List[FeedbackSnapshot] = []
        self.adjustments: List[ParameterAdjustment] = []

    def snapshot(self, store) -> FeedbackSnapshot:
        """Take one reading from the encoder."""
        stats = store.stats()
        outcomes = store._outcome_log

        # Recent outcomes (last window_size)
        recent = outcomes[-self.window_size:] if outcomes else []
        recent_wins = sum(1 for _, _, s in recent if s)
        recent_total = len(recent)
        recent_wr = recent_wins / recent_total if recent_total > 0 else 0.5

        # Confidence distribution
        confidences = [t.confidence for t in store.tiles.values()] if store.tiles else [0.5]
        avg_conf = sum(confidences) / len(confidences)
        std_conf = (sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)) ** 0.5

        # Type distribution
        type_dist: Dict[str, int] = defaultdict(int)
        for t in store.tiles.values():
            type_dist[t.type] += 1

        # Cancer state
        cancer = store.cancer_check()

        snap = FeedbackSnapshot(
            timestamp=time.time(),
            tile_count=stats["total_tiles"],
            total_wins=stats["total_wins"],
            total_losses=stats["total_losses"],
            overall_win_rate=stats["overall_win_rate"],
            recent_win_rate=recent_wr,
            cancer_alert=cancer["alert"],
            cancer_message=cancer["message"],
            avg_confidence=avg_conf,
            std_confidence=std_conf,
            type_distribution=dict(type_dist),
        )
        self.history.append(snap)
        return snap

    def process(self, store, current_params: dict) -> List[ParameterAdjustment]:
        """Process encoder signal and compute parameter adjustments.

        This is the control law: given what happened, what should change?
        """
        snap = self.snapshot(store)
        adjustments: List[ParameterAdjustment] = []

        # Need minimum samples before we start adapting
        total_outcomes = snap.total_wins + snap.total_losses
        if total_outcomes < self.min_samples:
            return adjustments

        # ── Mortality rate adaptation ──
        # Healthy system: recent WR > 0.7 → lower mortality (keep more)
        # Struggling system: recent WR < 0.4 → raise mortality (prune harder)
        # Cancer detected: aggressive pruning
        current_mortality = current_params.get("mortality_rate", 0.15)

        if snap.cancer_alert:
            target_mortality = 0.30  # aggressive sweep when cancer detected
            reason = f"CANCER: {snap.cancer_message[:60]}"
        elif snap.recent_win_rate > 0.7:
            target_mortality = 0.10  # healthy, prune gently
            reason = f"Healthy corpus (WR={snap.recent_win_rate:.2f}), gentle sweep"
        elif snap.recent_win_rate < 0.4:
            target_mortality = 0.25  # struggling, prune harder
            reason = f"Low WR ({snap.recent_win_rate:.2f}), aggressive sweep"
        else:
            target_mortality = 0.15  # neutral
            reason = f"Normal WR ({snap.recent_win_rate:.2f}), standard sweep"

        new_mortality = current_mortality + self.adaptation_rate * (target_mortality - current_mortality)
        new_mortality = max(0.05, min(0.40, new_mortality))  # clamp

        if abs(new_mortality - current_mortality) > 0.001:
            adjustments.append(ParameterAdjustment(
                parameter="mortality_rate",
                old_value=current_mortality,
                new_value=round(new_mortality, 4),
                reason=reason,
                confidence=min(1.0, total_outcomes / 100),
            ))

        # ── Confidence floor adaptation ──
        # If avg confidence is high but recent WR is low → confidence is miscalibrated
        # Lower the floor to allow more tiles through (system needs diversity)
        current_floor = current_params.get("confidence_floor", 0.0)
        if snap.avg_confidence > 0.8 and snap.recent_win_rate < 0.5:
            # Confidence is inflated — it's lying
            target_floor = snap.avg_confidence - 0.2
            new_floor = current_floor + self.adaptation_rate * (target_floor - current_floor)
            adjustments.append(ParameterAdjustment(
                parameter="confidence_floor",
                old_value=current_floor,
                new_value=round(new_floor, 4),
                reason=f"Confidence ({snap.avg_confidence:.2f}) misaligned with WR ({snap.recent_win_rate:.2f})",
                confidence=0.6,
            ))
        elif snap.avg_confidence < 0.3 and snap.recent_win_rate > 0.6:
            # Confidence is too conservative — good tiles being underweighted
            target_floor = max(0.0, snap.avg_confidence - 0.1)
            new_floor = current_floor + self.adaptation_rate * (target_floor - current_floor)
            adjustments.append(ParameterAdjustment(
                parameter="confidence_floor",
                old_value=current_floor,
                new_value=round(new_floor, 4),
                reason=f"Low confidence ({snap.avg_confidence:.2f}) but high WR ({snap.recent_win_rate:.2f})",
                confidence=0.5,
            ))

        # ── Ricci flow alpha adaptation ──
        # When WR is declining, increase alpha (evolve faster to escape local optimum)
        # When WR is stable/high, decrease alpha (conserve what works)
        current_alpha = current_params.get("ricci_alpha", 0.1)
        if len(self.history) >= 3:
            wr_trend = self.history[-1].recent_win_rate - self.history[-3].recent_win_rate
            if wr_trend < -0.1:
                target_alpha = min(0.3, current_alpha + 0.05)
                reason = f"WR declining ({wr_trend:+.2f}), increase evolution speed"
            elif wr_trend > 0.1:
                target_alpha = max(0.01, current_alpha - 0.02)
                reason = f"WR improving ({wr_trend:+.2f}), conserve current state"
            else:
                target_alpha = current_alpha
                reason = "WR stable, maintain alpha"
            
            new_alpha = current_alpha + self.adaptation_rate * (target_alpha - current_alpha)
            if abs(new_alpha - current_alpha) > 0.001:
                adjustments.append(ParameterAdjustment(
                    parameter="ricci_alpha",
                    old_value=round(current_alpha, 4),
                    new_value=round(new_alpha, 4),
                    reason=reason,
                    confidence=0.7,
                ))

        self.adjustments.extend(adjustments)
        return adjustments

    def summary(self) -> dict:
        """Summarize the feedback processor state."""
        if not self.history:
            return {"status": "no_data", "snapshots": 0}
        latest = self.history[-1]
        return {
            "status": "active",
            "snapshots": len(self.history),
            "latest_wr": round(latest.recent_win_rate, 3),
            "latest_tile_count": latest.tile_count,
            "cancer_alert": latest.cancer_alert,
            "total_adjustments": len(self.adjustments),
            "last_adjustments": [
                {"param": a.parameter, f"from": a.old_value, "to": a.new_value, "reason": a.reason}
                for a in self.adjustments[-5:]
            ],
        }


# ─── MetaConstraint — a constraint that evolves from its own enforcement ──────

@dataclass
class EnforcementRecord:
    """One instance of a constraint being checked."""
    timestamp: float
    value: float          # the value that was checked
    fired: bool           # did the constraint trigger?
    outcome: bool         # was the result correct?
    threshold: float      # what the threshold was at the time


class MetaConstraint:
    """A constraint that learns its own optimal threshold.

    Like a servo discovering its own friction curve through use.
    The constraint doesn't just enforce — it watches itself enforce,
    and adjusts its threshold based on what actually works.

    The algorithm:
    1. Record every enforcement (value, fired, outcome, threshold)
    2. Periodically, compute: at what threshold would outcomes be maximized?
    3. Adjust threshold toward that optimum
    """

    def __init__(
        self,
        name: str,
        initial_threshold: float = 0.5,
        adaptation_rate: float = 0.05,
        min_records: int = 30,
        bounds: Tuple[float, float] = (0.0, 1.0),
        cooldown: int = 50,  # min records between adaptations
    ):
        self.name = name
        self.threshold = initial_threshold
        self.adaptation_rate = adaptation_rate
        self.min_records = min_records
        self.bounds = bounds
        self.cooldown = cooldown
        self.records: List[EnforcementRecord] = []
        self.adaptation_history: List[dict] = []
        self._last_adapt_count = 0

    def check(self, value: float) -> bool:
        """Check if value passes the constraint. Records the check."""
        fired = value >= self.threshold
        return fired

    def record(self, value: float, fired: bool, outcome: bool) -> None:
        """Record the outcome of a constraint check."""
        self.records.append(EnforcementRecord(
            timestamp=time.time(),
            value=value,
            fired=fired,
            outcome=outcome,
            threshold=self.threshold,
        ))

    def adapt(self) -> Optional[float]:
        """Compute optimal threshold from enforcement history.

        The encoder signal: for each past enforcement, was the outcome
        better when the constraint fired or when it didn't?

        We find the threshold that maximizes win_rate among fired records
        while keeping a reasonable pass rate.
        """
        if len(self.records) < self.min_records:
            return None
        if len(self.records) - self._last_adapt_count < self.cooldown:
            return None

        # Bin values and compute win_rate at each level
        n_bins = 20
        lo, hi = self.bounds
        bin_width = (hi - lo) / n_bins

        bin_wins: Dict[int, int] = defaultdict(int)
        bin_total: Dict[int, int] = defaultdict(int)

        for rec in self.records:
            if rec.fired:
                b = int((rec.value - lo) / bin_width) if bin_width > 0 else 0
                b = max(0, min(n_bins - 1, b))
                bin_total[b] += 1
                if rec.outcome:
                    bin_wins[b] += 1

        # Find the bin with best win_rate (minimum 5 samples)
        best_wr = 0.0
        best_threshold = self.threshold
        for b in range(n_bins):
            if bin_total.get(b, 0) >= 5:
                wr = bin_wins[b] / bin_total[b]
                if wr > best_wr:
                    best_wr = wr
                    best_threshold = lo + (b + 0.5) * bin_width

        # Smoothly move toward the optimal threshold
        old = self.threshold
        new = old + self.adaptation_rate * (best_threshold - old)
        new = max(self.bounds[0], min(self.bounds[1], new))

        if abs(new - old) > 0.001:
            self.threshold = new
            self._last_adapt_count = len(self.records)
            self.adaptation_history.append({
                "old": round(old, 4),
                "new": round(new, 4),
                "best_wr": round(best_wr, 3),
                "records": len(self.records),
                "ts": time.time(),
            })
            return new

        return None

    def summary(self) -> dict:
        return {
            "name": self.name,
            "threshold": round(self.threshold, 4),
            "records": len(self.records),
            "adaptations": len(self.adaptation_history),
            "last_adaptation": self.adaptation_history[-1] if self.adaptation_history else None,
        }


# ─── TransferFunctionModel — learn the actual query→outcome mapping ───────────

@dataclass
class TransferSample:
    """One sample of the actual transfer function."""
    constraint_type: str      # which constraint was involved
    constraint_strength: float  # how strong the constraint was
    context_features: dict     # what the context looked like
    outcome_accuracy: float    # what actually happened
    outcome_latency_ms: float  # how long it took


class TransferFunctionModel:
    """Learns the actual mapping from constraint parameters to outcomes.

    The system currently ASSUMES the transfer function is identity:
      stronger constraint → better outcome.
    
    Reality is nonlinear. Some constraints help in some contexts and hurt
    in others. This model LEARNS the actual shape through observation.

    Like a servo building its Bode plot — frequency response discovered
    through use, not assumed from the datasheet.
    """

    def __init__(self):
        self.samples: List[TransferSample] = []
        self.models: Dict[str, dict] = {}  # per-constraint-type models

    def record(self, sample: TransferSample) -> None:
        """Record one observation of the transfer function."""
        self.samples.append(sample)

    def recommend(self, constraint_type: str) -> float:
        """Recommend the optimal constraint strength for a given type.

        Simple version: find the strength value with highest average accuracy.
        The system learns what ACTUALLY works, not what should work.
        """
        if constraint_type not in self.models:
            self._build_model(constraint_type)

        model = self.models.get(constraint_type, {})
        return model.get("optimal_strength", 0.5)

    def _build_model(self, constraint_type: str) -> None:
        """Build a simple model from observed samples.

        Bins constraint_strength into quantiles and finds the bin
        with highest average outcome_accuracy.
        """
        type_samples = [s for s in self.samples if s.constraint_type == constraint_type]
        if len(type_samples) < 10:
            self.models[constraint_type] = {"optimal_strength": 0.5, "samples": len(type_samples)}
            return

        # Bin by strength (quintiles)
        strengths = sorted(s.constraint_strength for s in type_samples)
        n_bins = min(5, len(strengths) // 3)  # ensure at least 3 per bin
        if n_bins < 2:
            n_bins = 2
        # Use percentile-based bin edges
        import math
        bin_edges = []
        for i in range(n_bins + 1):
            idx = int(i * (len(strengths) - 1) / n_bins)
            bin_edges.append(strengths[idx])
        # Ensure last edge covers the max
        bin_edges[-1] = strengths[-1]

        best_wr = 0.0
        best_strength = 0.5
        found = False

        for i in range(n_bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            # Use exclusive upper bound for all but the last bin to avoid duplicates
            if i < n_bins - 1:
                bin_samples = [s for s in type_samples if lo <= s.constraint_strength < hi]
            else:
                bin_samples = [s for s in type_samples if lo <= s.constraint_strength <= hi]
            if len(bin_samples) >= 3:
                avg_acc = sum(s.outcome_accuracy for s in bin_samples) / len(bin_samples)
                if avg_acc > best_wr:
                    best_wr = avg_acc
                    best_strength = (lo + hi) / 2
                    found = True

        if not found:
            # Fallback: use the median strength of the top 50% outcomes
            type_samples.sort(key=lambda s: s.outcome_accuracy, reverse=True)
            top = type_samples[:max(3, len(type_samples) // 2)]
            best_strength = sum(s.constraint_strength for s in top) / len(top)
            best_wr = sum(s.outcome_accuracy for s in top) / len(top)

        self.models[constraint_type] = {
            "optimal_strength": round(best_strength, 4),
            "best_accuracy": round(best_wr, 3),
            "samples": len(type_samples),
        }

    def summary(self) -> dict:
        return {
            "total_samples": len(self.samples),
            "constraint_types": list(self.models.keys()),
            "models": {
                k: {kk: vv for kk, vv in v.items() if kk != "raw"}
                for k, v in self.models.items()
            },
        }


# ─── ServoMind — orchestrates the self-learning loop ─────────────────────────

class ServoMind:
    """The controller that closes the servo loop.

    This is the system that makes PLATO self-aware of its own dynamics.
    It doesn't change WHAT the system does — it changes how the system
    TUNES itself based on what actually happens.

    Usage:
        from core.tile_lifecycle import TileStore
        from core.servo_mind import ServoMind

        store = TileStore()
        mind = ServoMind(store)

        # One cycle: read encoder → compute adjustments → apply
        mind.cycle()

        # Continuous: run N cycles
        mind.run(n=100)

        # Check state
        mind.status()
    """

    def __init__(self, store, params: dict = None):
        """
        Args:
            store: A TileStore instance with outcomes being recorded
            params: Initial parameters (defaults provided if None)
        """
        self.store = store
        self.params = params or {
            "mortality_rate": 0.15,
            "confidence_floor": 0.0,
            "ricci_alpha": 0.1,
            "ricci_target": 0.0,
        }

        # The three new components that close the loop
        self.processor = FeedbackProcessor()
        self.transfer = TransferFunctionModel()

        # Meta-constraints for key parameters
        self.constraints = {
            "confidence": MetaConstraint(
                "confidence", initial_threshold=0.3,
                bounds=(0.0, 1.0), cooldown=30,
            ),
            "recency": MetaConstraint(
                "recency", initial_threshold=0.5,
                bounds=(0.0, 1.0), cooldown=30,
            ),
        }

        self.cycle_count = 0
        self.start_time = time.time()

    def cycle(self) -> dict:
        """Run one self-learning cycle.

        1. READ the encoder signal (snapshot current state)
        2. PROCESS feedback into parameter adjustments
        3. ADAPT meta-constraints from their enforcement history
        4. UPDATE transfer function model with new observations
        5. APPLY adjustments to system parameters
        6. SWEEP with adaptive mortality rate

        Returns a dict with the cycle results.
        """
        self.cycle_count += 1

        # 1+2: Read encoder, process feedback
        adjustments = self.processor.process(self.store, self.params)

        # 3: Adapt meta-constraints
        constraint_adaptations = {}
        for name, constraint in self.constraints.items():
            new_threshold = constraint.adapt()
            if new_threshold is not None:
                constraint_adaptations[name] = {
                    "old": constraint.adaptation_history[-1]["old"] if constraint.adaptation_history else None,
                    "new": new_threshold,
                }

        # 5: Apply adjustments to parameters
        for adj in adjustments:
            self.params[adj.parameter] = adj.new_value

        # 6: Run mortality sweep with adaptive rate
        sweep_result = self.store.sweep(mortality_rate=self.params["mortality_rate"])

        return {
            "cycle": self.cycle_count,
            "adjustments": [
                {"param": a.parameter, "to": a.new_value, "reason": a.reason}
                for a in adjustments
            ],
            "constraint_adaptations": constraint_adaptations,
            "sweep": {
                "pruned": sweep_result["pruned"],
                "remaining": sweep_result["remaining"],
            },
            "params": dict(self.params),
        }

    def record_and_learn(
        self,
        tile_id: str,
        succeeded: bool,
        constraint_type: str = "confidence",
        constraint_strength: float = 0.5,
        context: dict = None,
    ) -> None:
        """Record an outcome AND feed it into the learning system.

        This is the main entry point for the self-learning loop.
        Every time a tile is used, call this to:
          1. Record the outcome in the tile store
          2. Record it in the transfer function model
          3. Record it in the relevant meta-constraint
        """
        # 1. Record outcome in tile
        self.store.record_outcome(tile_id, succeeded)

        # 2. Record in transfer function model
        tile = self.store.get(tile_id)
        if tile:
            self.transfer.record(TransferSample(
                constraint_type=constraint_type,
                constraint_strength=constraint_strength,
                context_features=context or {},
                outcome_accuracy=1.0 if succeeded else 0.0,
                outcome_latency_ms=0.0,
            ))

            # 3. Record in meta-constraint
            if constraint_type in self.constraints:
                self.constraints[constraint_type].record(
                    value=tile.confidence,
                    fired=tile.confidence >= self.constraints[constraint_type].threshold,
                    outcome=succeeded,
                )

    def run(self, n: int = 10, interval: float = 0.0) -> List[dict]:
        """Run N self-learning cycles.

        Args:
            n: Number of cycles to run
            interval: Seconds between cycles (0 = no delay)
        """
        results = []
        for _ in range(n):
            result = self.cycle()
            results.append(result)
            if interval > 0:
                time.sleep(interval)
        return results

    def status(self) -> dict:
        """Full status of the servo-mind system."""
        return {
            "cycle_count": self.cycle_count,
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "current_params": dict(self.params),
            "feedback": self.processor.summary(),
            "transfer": self.transfer.summary(),
            "constraints": {name: c.summary() for name, c in self.constraints.items()},
            "store_stats": self.store.stats(),
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Demonstrate the servo-mind system with synthetic data."""
    from core.tile_lifecycle import TileStore, Tile

    print("SERVO-MIND DEMO — Self-Learning Constraint System")
    print("=" * 60)

    # Create store and mind
    store = TileStore(seed_phase_size=10)
    mind = ServoMind(store)

    # Seed phase: add initial tiles
    print("\n1. SEED PHASE — Adding initial tiles...")
    for i in range(20):
        tile = Tile(
            id=f"tile-{i:03d}",
            type="knowledge",
            content=f"Knowledge tile #{i}",
            confidence=0.3 + (i * 0.03),  # 0.3 → 0.87
        )
        store.admit(tile)
    print(f"   Added {store.count()} tiles")

    # Simulate usage: record outcomes
    print("\n2. SIMULATION — Recording outcomes...")
    for cycle in range(50):
        for tile in list(store.tiles.values())[:5]:
            # Higher confidence tiles succeed more often
            prob = tile.confidence
            import random
            succeeded = random.random() < prob
            mind.record_and_learn(
                tile.id,
                succeeded,
                constraint_type="confidence",
                constraint_strength=tile.confidence,
            )

        # Run a servo-mind cycle every 10 outcomes
        if (cycle + 1) % 10 == 0:
            result = mind.cycle()
            n_adj = len(result["adjustments"])
            n_pruned = result["sweep"]["pruned"]
            print(f"   Cycle {result['cycle']:2d}: "
                  f"{n_adj} adjustments, "
                  f"{n_pruned} pruned, "
                  f"mortality={result['params']['mortality_rate']:.3f}")

    # Final status
    print("\n3. FINAL STATUS")
    status = mind.status()
    print(f"   Cycles run: {status['cycle_count']}")
    print(f"   Store: {status['store_stats']['total_tiles']} tiles, "
          f"WR={status['store_stats']['overall_win_rate']:.2f}")
    print(f"   Feedback: {status['feedback']['latest_wr']:.3f} recent WR")
    print(f"   Mortality rate: {status['current_params']['mortality_rate']:.3f}")
    print(f"   Ricci alpha: {status['current_params']['ricci_alpha']:.3f}")

    # Show constraint evolution
    print("\n4. META-CONSTRAINT EVOLUTION")
    for name, c_status in status["constraints"].items():
        print(f"   {name}: threshold={c_status['threshold']:.3f}, "
              f"{c_status['records']} records, "
              f"{c_status['adaptations']} adaptations")

    print("\n" + "=" * 60)
    print("The encoder signal is now being processed.")
    print("The servo is learning its own dynamics.")
    print("Each cycle: constraints tighten where they help,")
    print("loosen where they hurt, and mortality adapts to corpus health.")


if __name__ == "__main__":
    demo()
