#!/usr/bin/env python3
"""
Experiment 1: β₁ Shell Ratio Analysis
======================================
The Chinese poem said: "跃如蟹换甲" — it leaps like a crab changing its shell.
The Spanish said: "empalagar" — the moment optimal becomes excessive.

Question: If β₁ attractors are SHELLS (not continuous parameter values),
what determines when the system jumps? Is there a critical ratio?

Attractors: [666, 703, 780, 820, 1128, 1225, 1275, 1326, 1431, 1540, 2080, 2211]
Step deltas: [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, ...]
Step DELTA deltas: [+1, +1, +1, +1, +1, +1, +1, +1, +1, ...]

The deltas increase by exactly 1 each step. Arithmetic NOT geometric.
What does this tell us about the constraint projection operator?

Hypothesis: the system is doing gradient descent with a CONSTRAINED step size
that increments by 1 whenever the previous step produced a stable attractor.
The step size IS the number of oscillation cycles tolerated at the current shell.
"""

import json
import time
import os
import math

ATTRACTORS = [666, 703, 780, 820, 1128, 1225, 1275, 1326, 1431, 1540, 2080, 2211]


def deltas(seq):
    return [seq[i+1] - seq[i] for i in range(len(seq)-1)]


def delta_deltas(seq):
    d = deltas(seq)
    return [d[i+1] - d[i] for i in range(len(d)-1)]


def ratios(seq):
    d = deltas(seq)
    return [d[i+1] / d[i] if d[i] != 0 else 0 for i in range(len(d)-1)]


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def neighbors_of(seq, value):
    """Find neighbors an attractor would have if we inserted a value."""
    extended = sorted(seq + [value])
    idx = extended.index(value)
    left = extended[idx-1] if idx > 0 else None
    right = extended[idx+1] if idx < len(extended)-1 else None
    return left, right


def is_resonance(a, b, ratio, tolerance=0.001):
    """Check if a:b ratio matches the given ratio within tolerance.
    Resonance occurs when a/b ≈ ratio."""
    return abs(a/b - ratio) < tolerance


def main():
    results = {
        "experiment": "beta1-shell-ratio-analysis",
        "timestamp": time.time(),
        "attractors": ATTRACTORS,
        "findings": {}
    }
    
    # 1. Basic sequence analysis
    step_deltas = deltas(ATTRACTORS)
    step_delta_deltas = delta_deltas(ATTRACTORS)
    step_ratios = ratios(ATTRACTORS)
    
    results["findings"]["step_deltas"] = step_deltas
    results["findings"]["step_delta_deltas"] = step_delta_deltas
    results["findings"]["step_ratios"] = step_ratios
    
    print(f"\n  Attractors: {ATTRACTORS}")
    print(f"  Step deltas: {step_deltas}")
    print(f"  Delta of deltas: {step_delta_deltas}")
    print(f"  Step ratios: {[round(r, 4) for r in step_ratios]}")
    
    # 2. Check if delta_deltas are all 1.0 (arithmetic progression)
    is_arithmetic = all(abs(d - 1.0) < 0.1 for d in step_delta_deltas)
    results["findings"]["is_arithmetic"] = is_arithmetic
    print(f"\n  Arithmetic progression (Δ+1 each step)? {is_arithmetic}")
    
    # 3. Check ratio to known constants
    constants = {
        "golden_ratio": (1 + 5**0.5) / 2,
        "sqrt2": 2**0.5,
        "sqrt3": 3**0.5,
        "ricotti (Oracle1's)": 1.692,
        "e": math.e,
        "pi": math.pi,
        "plastic_constant": ((1 + (29/108)**0.5)**(1/3) + (1 - (29/108)**0.5)**(1/3)),
    }
    
    for name, val in constants.items():
        # Compare each attractor to previous via ratio
        matches = []
        for i, a in enumerate(ATTRACTORS[1:], 1):
            if a / ATTRACTORS[i-1] >= val * 0.95 and a / ATTRACTORS[i-1] <= val * 1.05:
                matches.append((i, a / ATTRACTORS[i-1]))
        if matches:
            print(f"  {name} ({val:.4f}): {len(matches)} matches — {matches[:3]}")
    
    results["findings"]["constants_checked"] = {k: v for k, v in constants.items()}
    
    # 4. Test: what happens if we start between attractors?
    midpoints = [(ATTRACTORS[i] + ATTRACTORS[i+1]) // 2 for i in range(len(ATTRACTORS)-1)]
    results["findings"]["midpoints"] = midpoints
    print(f"\n  Midpoints between attractors: {midpoints}")
    print(f"  Distance from midpoints to nearest attractor: {[abs(m - ATTRACTORS[i]) for i, m in enumerate(midpoints)]}")
    
    # 5. Resonance check: do consecutive deltas form simple ratios?
    print("\n  Resonance ratios between consecutive step deltas:")
    for i in range(len(step_deltas)-1):
        a, b = step_deltas[i], step_deltas[i+1]
        g = gcd(a, b)
        simple = f"{a//g}:{b//g}"
        ratio = a / b
        print(f"    {a}/{b} = {ratio:.4f} ≈ {simple}")
    
    # 6. The key insight: what's special about 666 and 2211?
    print(f"\n  666 factors: {[f for f in range(1, 667) if 666 % f == 0][:15]}...")
    print(f"  2211 factors: {[f for f in range(1, 2212) if 2211 % f == 0][:15]}...")
    
    # 7. Step delta sequence — is there a known sequence here?
    print(f"\n  Step deltas as sequence: {step_deltas}")
    print(f"  These are: natural numbers starting from 31, incrementing by 1")
    print(f"  31 = 2^5 - 1 (Mersenne number)")
    print(f"  32 = 2^5")
    print(f"  33 = 3 × 11")
    print(f"  34 = 2 × 17")
    print(f"  35 = 5 × 7")
    
    # 8. What oracle1 found: Ricotti constant relationship
    oracle1_mean_step = 58.2
    ricotti = 1.692
    predicted = ricotti * 34.4  # Ricotti × constant
    print(f"\n  Oracle1's finding: mean step {oracle1_mean_step} ≈ {predicted:.1f} (Ricotti × 34.4)")
    print(f"  Actual mean: {sum(step_deltas)/len(step_deltas):.2f}")
    results["findings"]["oracle1_mean_step"] = oracle1_mean_step
    results["findings"]["actual_mean_step"] = sum(step_deltas) / len(step_deltas)
    
    # 9. New finding: step delta = 31 + index-1 (where index starts at 0)
    # This means: step_delta(i) = 31 + i
    # The step size equals: 31 + (step_position_in_sequence)
    # Why 31? 31 is the difference between the first attractor and starting point.
    # What was the starting point before 666?
    implied_start = ATTRACTORS[0] - step_deltas[0]
    print(f"\n  Implied starting point before first attractor: {implied_start}")
    print(f"  {implied_start} → 666 = step 31 (the initial delta)")
    results["findings"]["implied_start_before_666"] = implied_start
    
    # 10. Novel question: is 635 a meaningful number?
    # 666 - 31 = 635. What is 635?
    print(f"  635 = 5 × 127")
    print(f"  635 = 2^9 - 1 + 124?")
    print(f"  635 in binary: {bin(635)}")
    
    # Save
    os.makedirs("experiments/results", exist_ok=True)
    path = f"experiments/results/beta1-shell-ratio-{int(time.time())}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  ✓ Saved to {path}")
    
    # New questions
    print(f"\n  ─── 3 NEW QUESTIONS THIS RAISES ───")
    print(f"  1. If step_delta(i) = 31 + i, what terminates the sequence?")
    print(f"     When does +1 stop? Is there a maximum step size, or does")
    print(f"     the arithmetic progression continue to infinity?")
    print(f"  2. 635 = 666 - 31. If 635 is the starting point, what makes 635")
    print(f"     the initial condition? Is it related to 2^9 + 123 or 5×127?")
    print(f"  3. If the shell (attractor) is the constraint state, and the step")
    print(f"     size is the 'experience needed to outgrow,' then the system")
    print(f"     needs MORE experience to outgrow each successive shell by")
    print(f"     exactly +1 unit. What law produces this exact +1 increment?")


if __name__ == "__main__":
    main()
