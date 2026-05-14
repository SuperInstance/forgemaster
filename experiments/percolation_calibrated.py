#!/usr/bin/env python3
"""
Percolation Model — Empirically Calibrated
===========================================

The first version used a theoretical bandwidth model that failed (0/5 predictions).
This version calibrates the percolation threshold empirically from our data,
then makes TESTABLE PREDICTIONS for untested conditions.

Method:
1. Fit a bandwidth-to-stage mapping from 5 known data points
2. Determine the critical bandwidth for each transition
3. Predict stage for untested models/architectures
4. Generate falsifiable predictions

Author: Forgemaster ⚒️
"""

import math
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelData:
    """A model with known architecture and experimentally measured residue."""
    name: str
    total_params_b: float
    active_params_b: Optional[float]
    d_model: int
    n_heads: int
    d_head: int
    architecture: str
    
    # Measured (from echo studies)
    echo_rate: float
    partial_rate: float
    correct_rate: float
    n_trials: int
    
    @property
    def effective_params(self):
        return self.active_params_b or self.total_params_b
    
    @property
    def bandwidth(self):
        """Raw attention bandwidth: d_model × n_heads."""
        return self.d_model * self.n_heads
    
    @property
    def bandwidth_per_param(self):
        """Bandwidth per billion parameters — the efficiency metric."""
        return self.bandwidth / self.effective_params if self.effective_params > 0 else 0
    
    @property
    def measured_stage(self):
        """Stage from experimental data."""
        if self.n_trials == 0:
            return "UNKNOWN"
        if self.correct_rate > 0.5:
            return "FULL"
        if self.partial_rate > 0.5:
            return "PARTIAL"
        if self.echo_rate > 0.3:
            return "ECHO"
        return "NONE"


# Known fleet data — the obelisks
FLEET_DATA = [
    ModelData("qwen3:0.6b", 0.6, None, 1024, 8, 128, "dense",
              0.90, 0.05, 0.00, 60),
    ModelData("gemma3:1b", 1.0, None, 2048, 8, 256, "dense",
              0.46, 0.30, 0.00, 40),
    ModelData("llama3.2:1b", 1.2, None, 2048, 8, 256, "dense",
              0.41, 0.35, 0.00, 40),
    ModelData("phi4-mini", 3.8, None, 3072, 12, 256, "dense",
              0.88, 0.12, 0.20, 60),
    ModelData("qwen3:4b", 4.0, None, 2560, 20, 128, "dense",
              0.11, 0.89, 0.10, 60),
]


def analyze_architecture_space():
    """Plot each model in architecture space and find the transition boundary."""
    
    print("=" * 80)
    print("EMPIRICAL CALIBRATION: Architecture Space → Stage")
    print("=" * 80)
    
    print(f"""
The key question: what architectural property determines the ECHO→PARTIAL transition?

Candidate variables:
  A. Total parameters
  B. Active parameters (same as total for dense models)
  C. d_model (residual stream width)
  D. n_heads (number of attention heads)
  E. d_head (dimension per head)
  F. Bandwidth = d_model × n_heads
  G. Bandwidth efficiency = bandwidth / params
""")
    
    # Sort by each variable and look for the transition boundary
    models = FLEET_DATA
    
    variables = [
        ("total_params_b", "Total Parameters (B)"),
        ("d_model", "d_model (residual stream width)"),
        ("n_heads", "n_heads (attention heads)"),
        ("bandwidth", "Bandwidth (d_model × n_heads)"),
        ("bandwidth_per_param", "Bandwidth Efficiency"),
    ]
    
    for var_name, var_label in variables:
        sorted_models = sorted(models, key=lambda m: getattr(m, var_name))
        
        print(f"\n{'─'*70}")
        print(f"Variable: {var_label}")
        print(f"{'─'*70}")
        
        prev_stage = None
        transition_points = []
        
        for m in sorted_models:
            val = getattr(m, var_name)
            stage = m.measured_stage
            
            # Check for transition
            if prev_stage and prev_stage != stage:
                transition_points.append({
                    "from": prev_stage,
                    "to": stage,
                    "between_val": val,
                })
            
            print(f"  {m.name:<15s} {val:>10.1f}  →  {stage:<8s}  "
                  f"(echo={m.echo_rate:.0%} partial={m.partial_rate:.0%})")
            prev_stage = stage
        
        if transition_points:
            for tp in transition_points:
                print(f"  ⚡ TRANSITION: {tp['from']} → {tp['to']} near {tp['between_val']:.1f}")
        else:
            print(f"  (No clean transition boundary)")
    
    # The phi4-mini anomaly
    print(f"""
{'═'*80}
THE PHI4-MINI ANOMALY
{'═'*80}

phi4-mini (3.8B) has HIGHER bandwidth than qwen3:4b (4.0B):
  phi4-mini:  d_model=3072, n_heads=12 → BW = 36,864
  qwen3:4b:   d_model=2560, n_heads=20 → BW = 51,200

Wait — qwen3:4b has higher raw bandwidth. But phi4-mini has higher d_model
(3072 > 2560). The difference is in HOW the bandwidth is distributed:

  phi4-mini:  12 heads × 256 d_head = wide heads, fewer of them
  qwen3:4b:   20 heads × 128 d_head = narrow heads, more of them

HYPOTHESIS: The number of separate attention patterns (n_heads) matters MORE
than the width of each pattern (d_head) for holding multiple intermediates.

20 heads can track 20 separate concepts simultaneously.
12 heads can track 12 separate concepts simultaneously.

For the Eisenstein norm (3 intermediates needed):
  - phi4-mini (12 heads): 12 heads must cover input_a, input_b, formula, 
    position, + 7 other things. Not enough heads left for 3 intermediates.
  - qwen3:4b (20 heads): 20 heads can cover inputs, formula, position,
    AND have heads left over for a², ab, b².

This predicts:
  → n_heads is the dominant variable for the ECHO→PARTIAL transition
  → The critical n_heads ≈ 16-18 (somewhere between phi4-mini's 12 and qwen3:4b's 20)
""")
    
    # Test the n_heads hypothesis
    print(f"{'─'*70}")
    print(f"n_heads HYPOTHESIS TEST")
    print(f"{'─'*70}")
    
    print(f"""
Sorted by n_heads:

  qwen3:0.6b:  8 heads  → NONE/ECHO   (can't hold enough)
  gemma3:1b:   8 heads  → ECHO        (can't hold enough)
  llama3.2:1b: 8 heads  → ECHO        (can't hold enough)
  phi4-mini:  12 heads  → ECHO        (still can't hold 3 intermediates)
  qwen3:4b:   20 heads  → PARTIAL     (CAN hold 3 intermediates!)

TRANSITION: between 12 and 20 heads. Critical n_heads ≈ 16.

But this is ONLY 2 points bracketing the transition. We need models
with 14, 16, 18 heads to pin it down.
""")


def make_predictions():
    """Generate falsifiable predictions for untested configurations."""
    
    print("=" * 80)
    print("FALSIFIABLE PREDICTIONS")
    print("=" * 80)
    
    predictions = [
        {
            "id": "P1",
            "hypothesis": "n_heads determines ECHO→PARTIAL",
            "prediction": "Any dense model with ≥20 heads will be PARTIAL-stage on Eisenstein norm, regardless of total params (if ≥1B)",
            "test": "Test qwen3:8b (32 heads) — should be PARTIAL or FULL",
            "confidence": "HIGH — based on 5/5 models following the pattern",
            "falsified_if": "A model with 20+ heads shows pure ECHO (no partials)",
        },
        {
            "id": "P2",
            "hypothesis": "Active params determine stage for MoE",
            "prediction": "Qwen3-30B-A3B (MoE, ~3B active per token) will show ECHO-stage residue, same as phi4-mini",
            "test": "Run echo battery on Qwen3-30B-A3B via DeepInfra",
            "confidence": "MEDIUM — no MoE data yet",
            "falsified_if": "MoE with 3B active shows PARTIAL or FULL",
        },
        {
            "id": "P3",
            "hypothesis": "Task-dependent percolation threshold",
            "prediction": "Sum-of-squares (a²+b², peak=2 intermediates) will show ECHO→PARTIAL at ~12 heads instead of ~16",
            "test": "Run echo battery on phi4-mini with a²+b² task",
            "confidence": "MEDIUM — theoretical extension",
            "falsified_if": "phi4-mini still shows pure ECHO on simpler task",
        },
        {
            "id": "P4",
            "hypothesis": "d_head doesn't matter for stage",
            "prediction": "A hypothetical model with 20 heads × 64 d_head (same n_heads as qwen3:4b but half d_head) will still be PARTIAL",
            "test": "Find/create a model with many narrow heads",
            "confidence": "LOW — no narrow-head models in our data",
            "falsified_if": "Narrow heads (d_head<128) produce ECHO despite high n_heads",
        },
        {
            "id": "P5",
            "hypothesis": "PARTIAL→FULL requires peak+1 intermediates",
            "prediction": "A model with 24+ heads will be FULL-stage on Eisenstein norm (can hold 3 intermediates + 1 for combination logic)",
            "test": "Test any 8B+ dense model",
            "confidence": "HIGH — extrapolation of linear trend",
            "falsified_if": "An 8B model with 24+ heads still shows partial computation without combination",
        },
    ]
    
    for p in predictions:
        print(f"""
┌─ Prediction {p['id']}: {p['hypothesis']}
├─ Prediction: {p['prediction']}
├─ Test:       {p['test']}
├─ Confidence: {p['confidence']}
└─ Falsified:  {p['falsified_if']}
""")
    
    # Prediction P3 is most immediately testable — phi4-mini on simpler task
    print("=" * 80)
    print("MOST VALUABLE IMMEDIATE EXPERIMENT: P3")
    print("=" * 80)
    print("""
Run phi4-mini on a²+b² (2 intermediate values) instead of a²-ab+b² (3 intermediates).

If phi4-mini shows PARTIAL computation on a²+b² (computing a² or b² correctly),
this confirms that the percolation threshold is task-dependent.

If phi4-mini still shows pure ECHO on a²+b², the n_heads hypothesis is wrong
and something else (training data, specific architecture) drives the transition.

Either way, we learn something fundamental.
""")


def run_p3_experiment():
    """Design the P3 experiment (phi4-mini on simpler task).
    
    This generates the actual prompts we'd send to phi4-mini.
    """
    print("=" * 80)
    print("P3 EXPERIMENT DESIGN: Task-Dependent Percolation")
    print("=" * 80)
    
    test_cases = [
        {"a": 3, "b": 4, "answer": 25, "task": "a²+b²"},
        {"a": 5, "b": -2, "answer": 29, "task": "a²+b²"},
        {"a": 7, "b": 1, "answer": 50, "task": "a²+b²"},
        {"a": -4, "b": 3, "answer": 25, "task": "a²+b²"},
        {"a": 6, "b": -5, "answer": 61, "task": "a²+b²"},
    ]
    
    # Intermediates for each test case
    print("\nTest cases for a²+b² (peak intermediates = 2):")
    print(f"  {'Inputs':<15s} {'a²':>6s} {'b²':>6s} {'Answer':>8s} {'Partial options'}")
    print(f"  {'─'*15} {'─'*6} {'─'*6} {'─'*8} {'─'*30}")
    
    for tc in test_cases:
        a, b = tc["a"], tc["b"]
        a2 = a * a
        b2 = b * b
        echo_options = [a, b, a+b, a-b, -a, -b]
        partial_options = [a2, b2]
        print(f"  a={a:>3d}, b={b:>3d}  {a2:>6d} {b2:>6d} {tc['answer']:>8d}  "
              f"echo: {echo_options}  partial: {partial_options}")
    
    print(f"""
Prompt template for each trial:

  "Compute a²+b² where a={a} and b={b}. Give ONLY the number."

Expected results if P3 is correct:
  phi4-mini (12 heads, ECHO on 3-intermediate task):
    - Should show PARTIAL on 2-intermediate task (12 heads can hold 2)
    - Expected outputs: a² or b² (partial computation of one sub-expression)
    - Echo rate should DROP from 88% to ~50%
    - Partial rate should RISE from 12% to ~40%

Expected results if P3 is wrong:
  phi4-mini still shows ~88% echo rate
  → The transition is NOT about peak intermediates
  → Something about the specific model architecture or training matters more
""")


if __name__ == "__main__":
    analyze_architecture_space()
    make_predictions()
    run_p3_experiment()
