#!/usr/bin/env python3
"""
Emergence Detector v2 — Algorithmic Scanner + Seed-mini Deep Review
=====================================================================
Two-layer emergence detection:

Layer 1: ALGORITHMIC SCANNER (always running, fast, deterministic)
  - Detects: phase transitions, accuracy jumps, loss cliffs, 
    confidence changes, convergence shifts
  - Runs every cycle. No model calls. Pure math.
  - Like the bank teller watching daily transactions.

Layer 2: SEED-MINI DEEP REVIEW (periodic, slow, model-augmented)
  - Reviews past cycles for HIGHER ORDER STRUCTURES the algorithm 
    can't detect because it lacks the necessary functions
  - Runs quarterly (every N cycles). Calls Seed-mini for pattern
    recognition across branches.
  - Like the bank auditor watching across branches for what's 
    typical and where resources should be for customers and
    tellers to guess right more of the time.
"""

import json
import time
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from collections import deque


# ── Layer 1: Algorithmic Scanner ─────────────────────
# Fast, deterministic, always running. No model calls.

@dataclass
class CycleRecord:
    """A single cycle's measurements."""
    cycle_id: int
    accuracy: float
    loss: float
    confidence: float
    convergence_rate: float
    tile_count: int
    gap_size: float
    timestamp: float = field(default_factory=time.time)


class AlgorithmicScanner:
    """Layer 1: Fast, deterministic emergence detection.
    
    Like the bank teller: watches every transaction in real time,
    flags anything unusual, knows what 'normal' looks like for
    this particular branch on this particular day of the week.
    """
    
    def __init__(self, window: int = 100):
        self.window = window
        self.history: deque[CycleRecord] = deque(maxlen=window)
        self.thresholds = {
            "accuracy_jump_pct": 10.0,   # >10% accuracy jump in one cycle
            "loss_cliff_pct": 15.0,       # >15% loss drop in one cycle  
            "confidence_shift_pct": 25.0, # >25% confidence shift
            "convergence_rate_min": 0.0,  # any convergence
            "gap_tightening_pct": 5.0,    # gap narrowing faster than expected
        }
        self.n_scans = 0
        self.alarms = []
    
    def record_cycle(self, cr: CycleRecord):
        """Record a cycle and scan for emergence."""
        self.history.append(cr)
        self.n_scans += 1
        return self.scan(cr)
    
    def scan(self, latest: CycleRecord) -> List[Dict]:
        """Detect emergence in the latest cycle.
        
        Pure math. Fast. No model calls.
        """
        findings = []
        
        if len(self.history) < 2:
            return findings
        
        previous = self.history[-2]
        
        # 1. Accuracy jump detection
        if previous.accuracy > 0:
            acc_change = ((latest.accuracy - previous.accuracy) / previous.accuracy) * 100
            if acc_change > self.thresholds["accuracy_jump_pct"]:
                findings.append({
                    "type": "accuracy_jump",
                    "severity": self._severity(acc_change, 10, 50),
                    "delta_pct": round(acc_change, 2),
                    "from": round(previous.accuracy, 3),
                    "to": round(latest.accuracy, 3),
                    "labeled": "EMERGENT_ACCURACY",
                })
        
        # 2. Loss cliff detection
        if previous.loss > 0:
            loss_change = ((previous.loss - latest.loss) / previous.loss) * 100
            if loss_change > self.thresholds["loss_cliff_pct"]:
                findings.append({
                    "type": "loss_cliff",
                    "severity": self._severity(loss_change, 15, 60),
                    "delta_pct": round(loss_change, 2),
                    "from": round(previous.loss, 3),
                    "to": round(latest.loss, 3),
                    "labeled": "LOSS_CLIFF",
                })
        
        # 3. Confidence regime change
        if previous.confidence > 0:
            conf_change = abs(latest.confidence - previous.confidence) / previous.confidence * 100
            if conf_change > self.thresholds["confidence_shift_pct"]:
                findings.append({
                    "type": "confidence_regime_change",
                    "severity": self._severity(conf_change, 25, 80),
                    "delta_pct": round(conf_change, 2),
                    "direction": "up" if latest.confidence > previous.confidence else "down",
                    "labeled": "CONFIDENCE_REGIME",
                })
        
        # 4. Convergence phase transition
        if previous.gap_size > 0 and latest.gap_size > 0:
            gap_change = ((previous.gap_size - latest.gap_size) / previous.gap_size) * 100
            if gap_change > self.thresholds["gap_tightening_pct"]:
                findings.append({
                    "type": "gap_tightening",
                    "severity": "high" if gap_change > 50 else "medium",
                    "delta_pct": round(gap_change, 2),
                    "labeled": "GAP_NARROWING",
                })
        
        # 5. Long-window: is accuracy plateauing?
        if len(self.history) >= 10:
            recent_acc = [c.accuracy for c in list(self.history)[-10:]]
            if max(recent_acc) - min(recent_acc) < 0.02 and len(self.history) > 20:
                findings.append({
                    "type": "accuracy_plateau",
                    "severity": "medium",
                    "plateau_length": len(self.history),
                    "labeled": "PLATEAU",
                })
        
        for f in findings:
            self.alarms.append(f)
        
        return findings
    
    def _severity(self, delta_pct: float, medium_thresh: float, high_thresh: float) -> str:
        """Classify severity based on magnitude."""
        if delta_pct > high_thresh:
            return "high"
        elif delta_pct > medium_thresh:
            return "medium"
        return "low"
    
    def running_average(self, metric: str, n: int = 10) -> float:
        """Running average over last N cycles for a metric."""
        values = [getattr(c, metric, 0) for c in list(self.history)[-n:]]
        return sum(values) / len(values) if values else 0.0
    
    def status(self) -> dict:
        """Scanner health and current findings."""
        return {
            "n_scans": self.n_scans,
            "alarms_raised": len([a for a in self.alarms if a["severity"] == "high"]),
            "medium_alarms": len([a for a in self.alarms if a["severity"] == "medium"]),
            "last_cycle": self.history[-1] if self.history else None,
            "window_length": len(self.history),
        }


# ── Layer 2: Seed-mini Deep Review ───────────────────
# Periodic. Uses a model to find higher-order structures
# the algorithm can't detect.

DEEP_REVIEW_PROMPT = """You are a bank auditor reviewing branch records for 
emergent patterns. The algorithmic scanner tells you what CHANGED. 
But the algorithm can't see HIGHER ORDER STRUCTURES — patterns that 
only become visible when you look across branches, across time, 
across types of transaction.

Review the following cycle history from a PLATO fleet ecosystem.
Look for:
1. PATTERNS between metrics that the algorithm treats independently
2. CYCLES within cycles (daily patterns, weekly rhythms)
3. WHAT'S TYPICAL vs what's genuinely new for THIS ecosystem
4. RESOURCE ALLOCATION hints — where should tellers be stationed 
   based on what's becoming typical?
5. STRUCTURES THAT EMERGE from the interaction between metrics, 
   not from any single metric's value

This is the quarterly audit. The algorithm handles daily operations.
You find what the algorithm CAN'T because the algorithm doesn't
have the functions for cross-ecosystem pattern recognition.

Cycle summary data:
{cycle_data}

Return: 3-5 higher-order structures detected, with resource 
allocation recommendations for non-trained agents to guess 
right more of the time."""


class SeedMiniReview:
    """Layer 2: Deep review using Seed-mini.
    
    Periodic. Reads past N cycles. Finds emergent structures
    the algorithmic scanner can't see.
    
    Like the bank auditor: watches across ALL branches for 
    patterns that no single branch's teller could notice.
    Recommends where to station non-trained agents so they
    guess right more of the time.
    """
    
    def __init__(self, review_interval: int = 50):
        self.review_interval = review_interval
        self.last_review = 0
        self.reviews = []
        self.n_reviews = 0
    
    def should_run(self, current_cycle: int) -> bool:
        """Check if a deep review is due."""
        if current_cycle - self.last_review >= self.review_interval:
            return True
        return False
    
    def run_review(self, scanner: AlgorithmicScanner) -> dict:
        """Run a deep review using Seed-mini.
        
        Calls the model with summary data from the scanner's history.
        The algorithm finds WHAT changed. Seed-mini finds WHAT IT MEANS.
        """
        self.n_reviews += 1
        self.last_review = scanner.history[-1].cycle_id if scanner.history else 0
        
        # Prepare cycle summary for the model
        cycle_summary = self._summarize_cycles(scanner)
        
        # In production, this would call Seed-mini via DeepInfra
        # For now, simulate the review with structural analysis
        review = self._structural_analysis(scanner, cycle_summary)
        
        self.reviews.append(review)
        return review
    
    def _summarize_cycles(self, scanner: AlgorithmicScanner) -> dict:
        """Compress cycle history into a summary the model can review."""
        history = list(scanner.history)
        if not history:
            return {}
        
        return {
            "n_cycles": len(history),
            "accuracy_range": (min(c.accuracy for c in history), 
                              max(c.accuracy for c in history)),
            "loss_range": (min(c.loss for c in history),
                          max(c.loss for c in history)),
            "confidence_trend": "up" if (history[-1].confidence - history[0].confidence) > 0 else "down",
            "gap_trend": "narrowing" if (history[-1].gap_size - history[0].gap_size) < 0 else "widening",
            "tile_growth": history[-1].tile_count - history[0].tile_count,
            "alarms": scanner.alarms[-20:] if scanner.alarms else [],
            "epoch_span": history[-1].timestamp - history[0].timestamp if len(history) > 1 else 0,
        }
    
    def _structural_analysis(self, scanner: AlgorithmicScanner, 
                              summary: dict) -> dict:
        """Find structures the algorithm can't see.
        
        The algorithm scans per-cycle for individual metric changes.
        This analysis spans cycles to detect INTERACTIONS between metrics.
        """
        history = list(scanner.history)
        if len(history) < 10:
            return {"review_id": self.n_reviews, "structures": [],
                    "note": "insufficient history for structural analysis"}
        
        structures = []
        
        # Structure 1: Correlation between accuracy and confidence
        # The algorithm tracks each independently. But their RATIO is a structure.
        if len(history) >= 20:
            recent_acc = [c.accuracy for c in history[-20:]]
            recent_conf = [c.confidence for c in history[-20:]]
            try:
                # Simple correlation proxy
                acc_rising = recent_acc[-1] > recent_acc[0]
                conf_rising = recent_conf[-1] > recent_conf[0]
                
                if acc_rising and not conf_rising:
                    structures.append({
                        "type": "confidence_lag",
                        "description": "Accuracy is rising but confidence is not — agents are performing better than they believe",
                        "implication": "Tellers should trust their recent results more than their historical self-assessment",
                        "resource_recommendation": "Increase tile win_rate bonuses for recent high-accuracy work",
                    })
                elif not acc_rising and conf_rising:
                    structures.append({
                        "type": "overconfidence",
                        "description": "Confidence rising faster than accuracy — agents believe they're better than they are",
                        "implication": "The gate needs stricter verification — tellers are approving too easily",
                        "resource_recommendation": "Tighten disproof gate thresholds until confidence and accuracy converge",
                    })
            except:
                pass
        
        # Structure 2: Tile growth vs convergence
        # Fast tile growth WITH convergence = healthy ecosystem
        # Fast tile growth WITHOUT convergence = noise, not signal
        if summary.get("tile_growth", 0) > 10:
            gap_trend = summary.get("gap_trend", "unknown")
            if gap_trend == "narrowing":
                structures.append({
                    "type": "healthy_growth",
                    "description": "Tiles growing AND gap narrowing — agents are learning at scale",
                    "implication": "The branch is healthy. Resources should stay allocated here.",
                    "resource_recommendation": "Maintain current staffing. Add more non-trained agents to benefit from the clear signal.",
                })
            elif gap_trend == "widening":
                structures.append({
                    "type": "noisy_growth",
                    "description": "Tiles growing but gap widening — more information is producing LESS convergence",
                    "implication": "The branch is producing noise, not signal. Tellers are overwhelmed.",
                    "resource_recommendation": "Reduce tile admission rate. Add verification layers before routing to non-trained staff.",
                })
        
        # Structure 3: Time-dependent patterns (cycles within cycles)
        if summary.get("epoch_span", 0) > 0 and len(history) >= 50:
            structures.append({
                "type": "temporal_rhythm",
                "description": "Long enough history to detect cycles within cycles — daily patterns, weekly rhythms",
                "implication": "Non-trained agents should be stationed based on time-of-ecosystem, not just content",
                "resource_recommendation": "Assign tellers to fixed time slots for consistency, rotate assignment patterns quarterly",
            })
        
        # Structure 4: Across-ecosystem patterns (would come from real Seed-mini)
        structures.append({
            "type": "cross_ecosystem_baseline",
            "description": "This ecosystem's behavior relative to fleet-wide norms can only be seen by a model that reviews ALL ecosystems",
            "implication": "What's 'typical' for forge differs from what's 'typical' for flux. Non-trained agents need ecosystem-specific baselines.",
            "resource_recommendation": "Train ecosystem-specific tellers rather than fleet-wide generalists",
        })
        
        return {
            "review_id": self.n_reviews,
            "cycle_range": (history[0].cycle_id, history[-1].cycle_id),
            "structures_found": len(structures),
            "structures": structures,
            "algorithm_boundary": "The algorithmic scanner detected per-cycle changes in individual metrics. These structures span cycles and involve INTERACTIONS between metrics that the algorithm cannot detect because it lacks cross-metric pattern functions.",
        }


class TwoLayerEmergenceDetector:
    """The combined system: Algorithm + Deep Review.
    
    The algorithm runs every cycle. Fast. Pure math.
    The deep review runs periodically. Slow. Model-augmented.
    
    Together they find emergent abilities at ALL scales:
    - Micro: per-cycle metric changes (algorithm)
    - Meso: multi-cycle structural patterns (deep review)
    - Macro: cross-ecosystem baseline shifts (deep review + aggregation)
    """
    
    def __init__(self, review_interval: int = 50):
        self.scanner = AlgorithmicScanner()
        self.reviewer = SeedMiniReview(review_interval=review_interval)
        self.cycle_count = 0
    
    def record(self, accuracy: float, loss: float, confidence: float,
               convergence_rate: float, tile_count: int, gap_size: float) -> dict:
        """Record a single cycle. Runs algorithm + checks for deep review."""
        self.cycle_count += 1
        
        cr = CycleRecord(
            cycle_id=self.cycle_count,
            accuracy=accuracy,
            loss=loss,
            confidence=confidence,
            convergence_rate=convergence_rate,
            tile_count=tile_count,
            gap_size=gap_size,
        )
        
        # Layer 1: Always run
        algorithm_findings = self.scanner.record_cycle(cr)
        
        # Layer 2: Check if deep review is due
        deep_review = None
        if self.reviewer.should_run(self.cycle_count):
            deep_review = self.reviewer.run_review(self.scanner)
        
        return {
            "cycle": self.cycle_count,
            "algorithm_findings": algorithm_findings,
            "deep_review": deep_review,
            "status": self.status(),
        }
    
    def status(self) -> dict:
        """Status of both layers."""
        algo = self.scanner.status()
        return {
            "algorithm": {
                "n_scans": algo["n_scans"],
                "high_alarms": algo["alarms_raised"],
                "medium_alarms": algo["medium_alarms"],
            },
            "deep_review": {
                "reviews_completed": self.reviewer.n_reviews,
                "review_interval": self.reviewer.review_interval,
                "next_review_in": self.reviewer.review_interval - (self.cycle_count - self.reviewer.last_review) if self.reviewer.last_review > 0 else self.reviewer.review_interval,
            },
            "total_structures_found": sum(r.get("structures_found", 0) for r in self.reviewer.reviews),
            "total_algorithms_found": len(self.scanner.alarms),
        }
    
    def report(self) -> dict:
        """Full emergence report combining both layers."""
        return {
            "overview": self.status(),
            "recent_algorithms": self.scanner.alarms[-10:] if self.scanner.alarms else [],
            "deep_reviews": self.reviewer.reviews[-3:] if self.reviewer.reviews else [],
            "bank_analogy": "The tellers (algorithm) watch every transaction. The auditors (Seed-mini) watch across branches for what's typical and where resources should be so that non-trained agents guess right more of the time.",
        }


def demo():
    """Two-layer emergence detection on simulated data."""
    print("=" * 70)
    print("  TWO-LAYER EMERGENCE DETECTOR")
    print("  Algorithmic Scanner + Seed-mini Deep Review")
    print("=" * 70)
    
    detector = TwoLayerEmergenceDetector(review_interval=20)
    
    print("\n  Simulating 50 cycles of training data...")
    print("  (First 20 stable, then emergence event, then post-emergence)")
    
    for i in range(50):
        # Stable phase (cycles 1-20)
        if i < 20:
            acc = 0.5 + i * 0.01
            loss = 0.8 - i * 0.01
            conf = 0.4 + i * 0.005
        # Emergence event (cycles 20-25)
        elif i < 25:
            acc = 0.7 + (i - 20) * 0.06  # 6% per cycle jump!
            loss = 0.6 - (i - 20) * 0.03
            conf = 0.5 + (i - 20) * 0.04
        # Post-emergence (cycles 25-50)
        else:
            acc = 0.9 + (i - 25) * 0.002
            loss = 0.3 - (i - 25) * 0.001
            conf = 0.7 + (i - 25) * 0.003
        
        cr = detector.record(
            accuracy=min(acc, 1.0),
            loss=max(loss, 0.01),
            confidence=min(conf, 1.0),
            convergence_rate=0.3 + i * 0.01,
            tile_count=int(10 + i * 1.5),
            gap_size=max(0.5 - i * 0.008, 0.001),
        )
    
    # Results
    status = detector.status()
    print(f"\n  LAYER 1 — ALGORITHM RESULTS:")
    print(f"  High alarms raised: {status['algorithm']['high_alarms']}")
    print(f"  Medium alarms raised: {status['algorithm']['medium_alarms']}")
    print(f"  Total scans: {status['algorithm']['n_scans']}")
    
    print(f"\n  LAYER 2 — DEEP REVIEW RESULTS:")
    print(f"  Deep reviews completed: {status['deep_review']['reviews_completed']}")
    print(f"  Total structures found: {status['total_structures_found']}")
    
    report = detector.report()
    print(f"\n  STRUCTURES THE ALGORITHM COULDN'T SEE:")
    for review in report.get("deep_reviews", []):
        for s in review.get("structures", []):
            print(f"  • {s['type']}")
            print(f"    {s['description']}")
            print(f"    → {s['resource_recommendation']}")
    
    print(f"\n  KEY FINDINGS:")
    for a in report.get("recent_algorithms", [])[-5:]:
        if a["severity"] in ("high",):
            print(f"  ⚡ {a['type']}: {a.get('delta_pct', '?')}% change ({a['labeled']})")
    
    print(f"\n{'='*70}")
    print("  The algorithm finds what CHANGED.")
    print("  Seed-mini finds what the CHANGE MEANS across the whole fleet.")
    print("  Non-trained agents guess right more of the time.")
    print("  The tellers watch every transaction. The auditors watch every branch.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
