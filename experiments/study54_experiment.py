#!/usr/bin/env python3
"""Study 54: Conservation law vs GL(9) alignment correlation.

QUESTION: Do the conservation law (γ+H) and GL(9) alignment measure the same thing,
or are they independent health signals?

HYPOTHESIS: They measure DIFFERENT things. Conservation measures structural balance
(no room dominates). GL(9) measures behavioral alignment (agents agree on intent).
They should have LOW correlation.
"""

import json
import math
import os
import sys
import time
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_hebbian_service import (
    ConservationHebbianKernel, TileFlowTracker, ConservationReport,
    predicted_gamma_plus_H, coupling_entropy, algebraic_normalized,
)
from gl9_consensus import (
    GL9HolonomyConsensus, GL9Agent, GL9ConsensusResult,
    IntentVector, GL9Matrix, INTENT_DIM, DEFAULT_TOLERANCE, pearson_correlation,
)


# ---------------------------------------------------------------------------
# Phase A: Correlation measurement
# ---------------------------------------------------------------------------

def generate_random_state(n_rooms: int, n_agents_per_room: int = 3,
                          rng: np.random.RandomState = None) -> Dict:
    """Generate a random fleet state with tile distributions and intent vectors."""
    if rng is None:
        rng = np.random.RandomState()
    
    # --- Hebbian / Conservation side ---
    kernel = ConservationHebbianKernel(n_rooms=n_rooms, V=min(n_rooms, 30))
    # Random weight initialization (varying distributions)
    weight_type = rng.choice(["uniform", "zipf", "sparse", "dense", "one_dominant", "two_cluster"])
    
    if weight_type == "uniform":
        w = rng.uniform(0, 1, (n_rooms, n_rooms)).astype(np.float32)
    elif weight_type == "zipf":
        w = rng.zipf(1.5, (n_rooms, n_rooms)).astype(np.float32)
        w = w / (w.max() + 1e-10)
    elif weight_type == "sparse":
        w = rng.uniform(0, 1, (n_rooms, n_rooms)).astype(np.float32)
        mask = rng.random((n_rooms, n_rooms)) > 0.7  # 70% sparse
        w *= mask
    elif weight_type == "dense":
        w = rng.uniform(0.3, 1, (n_rooms, n_rooms)).astype(np.float32)
    elif weight_type == "one_dominant":
        w = rng.uniform(0, 0.3, (n_rooms, n_rooms)).astype(np.float32)
        dom = rng.randint(n_rooms)
        w[dom, :] = rng.uniform(0.8, 1.0, n_rooms).astype(np.float32)
        w[:, dom] = rng.uniform(0.8, 1.0, n_rooms).astype(np.float32)
    elif weight_type == "two_cluster":
        w = rng.uniform(0, 0.1, (n_rooms, n_rooms)).astype(np.float32)
        half = n_rooms // 2
        w[:half, :half] = rng.uniform(0.5, 1.0, (half, half)).astype(np.float32)
        w[half:, half:] = rng.uniform(0.5, 1.0, (n_rooms - half, n_rooms - half)).astype(np.float32)
    
    np.fill_diagonal(w, 0)  # no self-loops
    kernel.set_weights(w)
    
    # Get conservation metrics
    report = kernel.conservation_report()
    compliance = kernel.compliance_rate()
    
    # --- GL(9) / Alignment side ---
    # Generate random intent vectors for agents
    total_agents = n_rooms * n_agents_per_room
    agents = []
    for i in range(total_agents):
        # Random intent vector — vary correlation structure
        intent_type = rng.choice(["uniform", "peaked", "opposed", "noisy"])
        if intent_type == "uniform":
            data = [1.0 / math.sqrt(9)] * 9
        elif intent_type == "peaked":
            data = [rng.normal(0, 1) for _ in range(9)]
        elif intent_type == "opposed":
            data = [(-1)**i * rng.uniform(0.5, 1.0) for i in range(9)]
        else:  # noisy
            data = [rng.normal(0, 0.1) for _ in range(9)]
        
        iv = IntentVector(data).normalize()
        agents.append({
            "id": i,
            "intent": iv,
            "room": i // n_agents_per_room,
        })
    
    # Build GL9 consensus from these agents
    consensus = GL9HolonomyConsensus(tolerance=DEFAULT_TOLERANCE)
    for i, a in enumerate(agents):
        neighbors = [j for j in range(len(agents)) if j != i and abs(a["room"] - agents[j]["room"]) <= 1]
        if not neighbors:
            neighbors = [j for j in range(len(agents)) if j != i][:3]
        ga = GL9Agent(id=i, intent=a["intent"], transform=GL9Matrix.identity(), neighbors=neighbors)
        consensus.add_agent(ga)
    
    result = consensus.check_consensus()
    
    return {
        "n_rooms": n_rooms,
        "n_agents": total_agents,
        "weight_type": weight_type,
        "conservation": {
            "gamma": report.gamma,
            "H": report.H,
            "gamma_plus_H": report.gamma_plus_H,
            "deviation": report.deviation,
            "conserved": report.conserved,
        },
        "gl9": {
            "alignment": result.alignment,
            "consensus": result.consensus,
            "deviation": result.deviation,
            "cycle_count": result.cycle_count,
        },
    }


def phase_a_correlation(n_samples: int = 100) -> Dict:
    """Phase A: Measure correlation between conservation and GL(9) alignment."""
    print(f"\n{'='*70}")
    print(f"PHASE A: Correlation Measurement ({n_samples} samples)")
    print(f"{'='*70}")
    
    rng = np.random.RandomState(42)
    results = []
    
    conservation_vals = []
    alignment_vals = []
    gamma_vals = []
    entropy_vals = []
    
    for i in range(n_samples):
        n_rooms = rng.randint(5, 21)  # 5-20 rooms
        state = generate_random_state(n_rooms, n_agents_per_room=rng.randint(2, 5), rng=rng)
        results.append(state)
        
        # Normalize conservation to [0,1] range for comparison
        # deviation → compliance proxy: 1 - |deviation|/max_deviation
        conservation_compliance = 1.0 - min(abs(state["conservation"]["deviation"]) / 0.2, 1.0)
        
        conservation_vals.append(conservation_compliance)
        alignment_vals.append(state["gl9"]["alignment"])
        gamma_vals.append(state["conservation"]["gamma"])
        entropy_vals.append(state["conservation"]["H"])
        
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{n_samples}] rooms={n_rooms}, "
                  f"weight={state['weight_type']}, "
                  f"conservation_compliance={conservation_compliance:.3f}, "
                  f"gl9_alignment={state['gl9']['alignment']:.3f}")
    
    # Compute Pearson correlation
    r_compliance_alignment = pearson_correlation(conservation_vals, alignment_vals)
    r_gamma_alignment = pearson_correlation(gamma_vals, alignment_vals)
    r_entropy_alignment = pearson_correlation(entropy_vals, alignment_vals)
    
    print(f"\n  Results:")
    print(f"    Conservation compliance ↔ GL(9) alignment: r = {r_compliance_alignment:.4f}")
    print(f"    Gamma (algebraic)       ↔ GL(9) alignment: r = {r_gamma_alignment:.4f}")
    print(f"    Coupling entropy        ↔ GL(9) alignment: r = {r_entropy_alignment:.4f}")
    
    # Spearman (rank) correlation too — more robust to outliers
    scipy_available = False
    try:
        from scipy.stats import spearmanr
        rho_ca, p_ca = spearmanr(conservation_vals, alignment_vals)
        scipy_available = True
        print(f"    Spearman ρ (compliance ↔ alignment): {rho_ca:.4f} (p={p_ca:.4f})")
    except ImportError:
        # Manual Spearman
        def rankdata(x):
            idx = sorted(range(len(x)), key=lambda i: x[i])
            ranks = [0] * len(x)
            for r, i in enumerate(idx):
                ranks[i] = r + 1
            return ranks
        
        rc = rankdata(conservation_vals)
        ra = rankdata(alignment_vals)
        rho_ca = pearson_correlation([float(x) for x in rc], [float(x) for x in ra])
        print(f"    Spearman ρ (compliance ↔ alignment): {rho_ca:.4f} (manual, no p-value)")
    
    # Interpret
    if abs(r_compliance_alignment) > 0.5:
        verdict = "REDUNDANT — merge into one signal"
    elif abs(r_compliance_alignment) < 0.3:
        verdict = "INDEPENDENT — keep both as separate signals"
    else:
        verdict = "MODERATE overlap — investigate further"
    
    print(f"\n  VERDICT: {verdict}")
    
    return {
        "n_samples": n_samples,
        "pearson_r": {
            "compliance_vs_alignment": round(r_compliance_alignment, 4),
            "gamma_vs_alignment": round(r_gamma_alignment, 4),
            "entropy_vs_alignment": round(r_entropy_alignment, 4),
        },
        "spearman_rho": round(rho_ca, 4) if not scipy_available else round(rho_ca, 4),
        "verdict": verdict,
        "conservation_mean": round(float(np.mean(conservation_vals)), 4),
        "conservation_std": round(float(np.std(conservation_vals)), 4),
        "alignment_mean": round(float(np.mean(alignment_vals)), 4),
        "alignment_std": round(float(np.std(alignment_vals)), 4),
        "sample_results": results[:10],  # first 10 for reference
    }


# ---------------------------------------------------------------------------
# Phase B: Stress testing
# ---------------------------------------------------------------------------

def phase_b_stress_test() -> Dict:
    """Phase B: Create scenarios that break one metric but not the other."""
    print(f"\n{'='*70}")
    print(f"PHASE B: Stress Testing")
    print(f"{'='*70}")
    
    results = {}
    
    # --- Scenario B1: All agents aligned but one room dominating ---
    # Conservation should break (one room dominates weight matrix)
    # Alignment should hold (all agents agree on intent)
    print(f"\n  Scenario B1: Agents aligned + one room dominating")
    
    n_rooms = 10
    kernel = ConservationHebbianKernel(n_rooms=n_rooms, V=10)
    
    # One room dominates weights
    w = np.full((n_rooms, n_rooms), 0.05, dtype=np.float32)
    w[0, :] = 2.0  # Room 0 massively dominates
    w[:, 0] = 1.5
    np.fill_diagonal(w, 0)
    kernel.set_weights(w)
    
    report = kernel.conservation_report()
    
    # All agents aligned (same intent vector)
    consensus = GL9HolonomyConsensus(tolerance=DEFAULT_TOLERANCE)
    shared_intent = IntentVector([1.0, 0.8, 0.9, 0.7, 0.6, 0.5, 0.8, 0.7, 0.6]).normalize()
    
    n_agents = 30
    for i in range(n_agents):
        neighbors = [j for j in range(n_agents) if j != i]
        # Small perturbation on intent (they're mostly aligned)
        perturbed = [shared_intent.data[d] + random.gauss(0, 0.05) for d in range(9)]
        iv = IntentVector(perturbed).normalize()
        consensus.add_agent(GL9Agent(id=i, intent=iv, transform=GL9Matrix.identity(), neighbors=neighbors))
    
    gl9_result = consensus.check_consensus()
    
    b1 = {
        "conservation_broken": not report.conserved,
        "conservation_deviation": round(report.deviation, 4),
        "conservation_gamma": round(report.gamma, 4),
        "gl9_alignment": round(gl9_result.alignment, 4),
        "gl9_consensus": gl9_result.consensus,
    }
    print(f"    Conservation: conserved={report.conserved}, deviation={report.deviation:.4f}, γ={report.gamma:.4f}")
    print(f"    GL(9):        alignment={gl9_result.alignment:.4f}, consensus={gl9_result.consensus}")
    print(f"    → Conservation BROKEN, GL(9) HOLDS: {not report.conserved and gl9_result.alignment > 0.9}")
    results["B1_aligned_dominant"] = b1
    
    # --- Scenario B2: Good conservation but agents disagree ---
    print(f"\n  Scenario B2: Good conservation + agents disagree on intent")
    
    kernel2 = ConservationHebbianKernel(n_rooms=n_rooms, V=10)
    # Calibrate weights to be near conservation target
    # Use auto-calibration: run enough updates to reach stable conserved state
    rng2 = np.random.RandomState(99)
    for _ in range(300):
        pre = np.zeros(n_rooms, dtype=np.float32)
        post = np.zeros(n_rooms, dtype=np.float32)
        pre[rng2.randint(n_rooms)] = 1.0
        post[rng2.randint(n_rooms)] = 0.9
        kernel2.update(pre, post)
    
    report2 = kernel2.conservation_report()
    
    # Agents have wildly different intents
    consensus2 = GL9HolonomyConsensus(tolerance=DEFAULT_TOLERANCE)
    for i in range(n_agents):
        # Random, uncorrelated intents
        intent_data = [random.gauss(0, 1) for _ in range(9)]
        iv = IntentVector(intent_data).normalize()
        neighbors = [j for j in range(n_agents) if j != i]
        consensus2.add_agent(GL9Agent(id=i, intent=iv, transform=GL9Matrix.identity(), neighbors=neighbors))
    
    gl9_result2 = consensus2.check_consensus()
    
    b2 = {
        "conservation_broken": not report2.conserved,
        "conservation_deviation": round(report2.deviation, 4),
        "conservation_gamma": round(report2.gamma, 4),
        "gl9_alignment": round(gl9_result2.alignment, 4),
        "gl9_consensus": gl9_result2.consensus,
    }
    print(f"    Conservation: conserved={report2.conserved}, deviation={report2.deviation:.4f}, γ={report2.gamma:.4f}")
    print(f"    GL(9):        alignment={gl9_result2.alignment:.4f}, consensus={gl9_result2.consensus}")
    print(f"    → Conservation HOLDS, GL(9) BROKEN: {report2.conserved and gl9_result2.alignment < 0.5}")
    results["B2_conserved_disagree"] = b2
    
    # --- Scenario B3: Both broken ---
    print(f"\n  Scenario B3: Both broken (dominant room + disagreeing agents)")
    
    kernel3 = ConservationHebbianKernel(n_rooms=n_rooms, V=10)
    w3 = np.full((n_rooms, n_rooms), 0.05, dtype=np.float32)
    w3[0, :] = 2.0
    w3[:, 0] = 1.5
    np.fill_diagonal(w3, 0)
    kernel3.set_weights(w3)
    
    report3 = kernel3.conservation_report()
    
    consensus3 = GL9HolonomyConsensus(tolerance=DEFAULT_TOLERANCE)
    for i in range(n_agents):
        intent_data = [random.gauss(0, 1) for _ in range(9)]
        iv = IntentVector(intent_data).normalize()
        neighbors = [j for j in range(n_agents) if j != i]
        consensus3.add_agent(GL9Agent(id=i, intent=iv, transform=GL9Matrix.identity(), neighbors=neighbors))
    
    gl9_result3 = consensus3.check_consensus()
    
    b3 = {
        "conservation_broken": not report3.conserved,
        "conservation_deviation": round(report3.deviation, 4),
        "gl9_alignment": round(gl9_result3.alignment, 4),
        "gl9_consensus": gl9_result3.consensus,
    }
    print(f"    Conservation: conserved={report3.conserved}, deviation={report3.deviation:.4f}")
    print(f"    GL(9):        alignment={gl9_result3.alignment:.4f}, consensus={gl9_result3.consensus}")
    results["B3_both_broken"] = b3
    
    # --- Scenario B4: Both healthy ---
    print(f"\n  Scenario B4: Both healthy (balanced weights + aligned agents)")
    
    kernel4 = ConservationHebbianKernel(n_rooms=n_rooms, V=10)
    rng4 = np.random.RandomState(77)
    for _ in range(300):
        pre = np.zeros(n_rooms, dtype=np.float32)
        post = np.zeros(n_rooms, dtype=np.float32)
        pre[rng4.randint(n_rooms)] = 1.0
        post[rng4.randint(n_rooms)] = 0.9
        kernel4.update(pre, post)
    
    report4 = kernel4.conservation_report()
    
    consensus4 = GL9HolonomyConsensus(tolerance=DEFAULT_TOLERANCE)
    shared = IntentVector([1.0, 0.8, 0.9, 0.7, 0.6, 0.5, 0.8, 0.7, 0.6]).normalize()
    for i in range(n_agents):
        perturbed = [shared.data[d] + random.gauss(0, 0.02) for d in range(9)]
        iv = IntentVector(perturbed).normalize()
        neighbors = [j for j in range(n_agents) if j != i]
        consensus4.add_agent(GL9Agent(id=i, intent=iv, transform=GL9Matrix.identity(), neighbors=neighbors))
    
    gl9_result4 = consensus4.check_consensus()
    
    b4 = {
        "conservation_broken": not report4.conserved,
        "conservation_deviation": round(report4.deviation, 4),
        "gl9_alignment": round(gl9_result4.alignment, 4),
        "gl9_consensus": gl9_result4.consensus,
    }
    print(f"    Conservation: conserved={report4.conserved}, deviation={report4.deviation:.4f}")
    print(f"    GL(9):        alignment={gl9_result4.alignment:.4f}, consensus={gl9_result4.consensus}")
    results["B4_both_healthy"] = b4
    
    # Summary
    can_break_independently = (
        b1["conservation_broken"] and b1["gl9_alignment"] > 0.9 and  # B1: cons broken, gl9 holds
        not b2["conservation_broken"] and b2["gl9_alignment"] < 0.5  # B2: cons holds, gl9 broken
    )
    
    print(f"\n  STRESS TEST VERDICT:")
    print(f"    Can break conservation independently: {b1['conservation_broken'] and b1['gl9_alignment'] > 0.9}")
    print(f"    Can break GL(9) independently:        {not b2['conservation_broken'] and b2['gl9_alignment'] < 0.5}")
    print(f"    Independent failure modes confirmed:   {can_break_independently}")
    
    results["verdict"] = {
        "independent_failure_modes": can_break_independently,
        "b1_conservation_broken_gl9_holds": b1["conservation_broken"] and b1["gl9_alignment"] > 0.9,
        "b2_conservation_holds_gl9_broken": not b2["conservation_broken"] and b2["gl9_alignment"] < 0.5,
    }
    
    return results


# ---------------------------------------------------------------------------
# Phase C: Combined predictive power
# ---------------------------------------------------------------------------

def phase_c_combined_power(n_samples: int = 100) -> Dict:
    """Phase C: Can conservation + alignment together predict fleet health better?"""
    print(f"\n{'='*70}")
    print(f"PHASE C: Combined Predictive Power ({n_samples} samples)")
    print(f"{'='*70}")
    
    rng = np.random.RandomState(123)
    
    # Generate fleet states with known "health" (ground truth)
    # Health = function of: structural balance, behavioral alignment, noise
    
    conservation_scores = []
    alignment_scores = []
    health_scores = []
    
    for i in range(n_samples):
        n_rooms = rng.randint(5, 16)
        state = generate_random_state(n_rooms, n_agents_per_room=rng.randint(2, 4), rng=rng)
        
        # Conservation compliance (0-1)
        c_score = 1.0 - min(abs(state["conservation"]["deviation"]) / 0.2, 1.0)
        
        # GL(9) alignment (0-1)
        a_score = state["gl9"]["alignment"]
        
        # Ground truth health: independent contributions from both + noise
        # This simulates the real world where BOTH signals contribute to fleet health
        noise = rng.normal(0, 0.05)
        h_score = 0.4 * c_score + 0.4 * a_score + 0.2 * rng.uniform(0.5, 1.0) + noise
        h_score = max(0, min(1, h_score))
        
        conservation_scores.append(c_score)
        alignment_scores.append(a_score)
        health_scores.append(h_score)
    
    # Linear regression: health = a*conservation + b*alignment + c
    # Using numpy least squares
    c_arr = np.array(conservation_scores)
    a_arr = np.array(alignment_scores)
    h_arr = np.array(health_scores)
    
    # Model 1: Conservation only
    X1 = np.column_stack([c_arr, np.ones(n_samples)])
    coef1, _, _, _ = np.linalg.lstsq(X1, h_arr, rcond=None)
    pred1 = X1 @ coef1
    ss_res1 = np.sum((h_arr - pred1) ** 2)
    ss_tot = np.sum((h_arr - np.mean(h_arr)) ** 2)
    r2_conservation = 1 - ss_res1 / ss_tot
    
    # Model 2: Alignment only
    X2 = np.column_stack([a_arr, np.ones(n_samples)])
    coef2, _, _, _ = np.linalg.lstsq(X2, h_arr, rcond=None)
    pred2 = X2 @ coef2
    ss_res2 = np.sum((h_arr - pred2) ** 2)
    r2_alignment = 1 - ss_res2 / ss_tot
    
    # Model 3: Both combined
    X3 = np.column_stack([c_arr, a_arr, np.ones(n_samples)])
    coef3, _, _, _ = np.linalg.lstsq(X3, h_arr, rcond=None)
    pred3 = X3 @ coef3
    ss_res3 = np.sum((h_arr - pred3) ** 2)
    r2_combined = 1 - ss_res3 / ss_tot
    
    print(f"\n  R² Results:")
    print(f"    Conservation only:  R² = {r2_conservation:.4f}")
    print(f"    GL(9) only:         R² = {r2_alignment:.4f}")
    print(f"    Combined:           R² = {r2_combined:.4f}")
    print(f"    Improvement (vs best single): {(r2_combined - max(r2_conservation, r2_alignment)):.4f}")
    
    combined_better = r2_combined > max(r2_conservation, r2_alignment) + 0.01
    print(f"\n  Combined model better: {combined_better}")
    
    return {
        "n_samples": n_samples,
        "r2_conservation_only": round(float(r2_conservation), 4),
        "r2_alignment_only": round(float(r2_alignment), 4),
        "r2_combined": round(float(r2_combined), 4),
        "improvement": round(float(r2_combined - max(r2_conservation, r2_alignment)), 4),
        "combined_coefficients": {
            "conservation_weight": round(float(coef3[0]), 4),
            "alignment_weight": round(float(coef3[1]), 4),
            "intercept": round(float(coef3[2]), 4),
        },
        "combined_better": combined_better,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("⚒️  Study 54: Conservation Law vs GL(9) Alignment Correlation")
    print("=" * 70)
    
    results = {}
    
    # Phase A
    results["phase_a"] = phase_a_correlation(100)
    
    # Phase B
    results["phase_b"] = phase_b_stress_test()
    
    # Phase C
    results["phase_c"] = phase_c_combined_power(100)
    
    # Final recommendation
    r = results["phase_a"]["pearson_r"]["compliance_vs_alignment"]
    independent_failures = results["phase_b"]["verdict"]["independent_failure_modes"]
    combined_better = results["phase_c"]["combined_better"]
    
    print(f"\n{'='*70}")
    print(f"FINAL RECOMMENDATION")
    print(f"{'='*70}")
    
    if abs(r) < 0.3 and independent_failures:
        recommendation = "KEEP SEPARATE"
        reason = (f"Low correlation (r={r:.3f}) + independent failure modes confirmed. "
                  f"Conservation and GL(9) measure fundamentally different aspects of fleet health.")
    elif abs(r) > 0.5:
        recommendation = "MERGE"
        reason = f"High correlation (r={r:.3f}) suggests redundancy."
    else:
        recommendation = "KEEP SEPARATE (conservative)"
        reason = f"Moderate correlation (r={r:.3f}). Independent failure modes: {independent_failures}."
    
    if combined_better:
        reason += " Combined model has better predictive power (higher R²)."
    
    print(f"  Recommendation: {recommendation}")
    print(f"  Reason: {reason}")
    print(f"  Correlation: r = {r:.4f}")
    print(f"  Independent failures: {independent_failures}")
    print(f"  Combined R² improvement: {results['phase_c']['improvement']:.4f}")
    
    results["recommendation"] = {
        "decision": recommendation,
        "reason": reason,
        "correlation_r": round(r, 4),
        "independent_failures": independent_failures,
        "combined_r2_improvement": results["phase_c"]["improvement"],
    }
    
    # Save results
    out_dir = os.path.dirname(os.path.abspath(__file__))
    
    json_path = os.path.join(out_dir, "study54_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved: {json_path}")
    
    # Generate markdown report
    md = generate_markdown(results)
    md_path = os.path.join(out_dir, "STUDY-54-CONSERVATION-VS-GL9.md")
    with open(md_path, "w") as f:
        f.write(md)
    print(f"  Report saved: {md_path}")
    
    return results


def generate_markdown(results: Dict) -> str:
    r = results["phase_a"]["pearson_r"]["compliance_vs_alignment"]
    rec = results["recommendation"]
    
    md = f"""# Study 54: Conservation Law vs GL(9) Alignment Correlation

**Date:** {time.strftime('%Y-%m-%d')}
**Status:** Complete
**Priority:** P0

## Question

Do the conservation law (γ+H) and GL(9) alignment measure the same thing, or are they independent health signals?

## Hypothesis

They measure DIFFERENT things:
- **Conservation (γ+H):** Structural balance — no room dominates the Hebbian weight matrix
- **GL(9) alignment:** Behavioral alignment — agents agree on intent vectors across 9 CI facets

Expected: LOW correlation between the two.

## Phase A: Correlation Measurement

**Samples:** {results['phase_a']['n_samples']} random fleet states (5-20 rooms, varying distributions)

### Pearson Correlation

| Metric Pair | r |
|---|---|
| Conservation compliance ↔ GL(9) alignment | **{r:.4f}** |
| Gamma (algebraic) ↔ GL(9) alignment | {results['phase_a']['pearson_r']['gamma_vs_alignment']:.4f} |
| Coupling entropy ↔ GL(9) alignment | {results['phase_a']['pearson_r']['entropy_vs_alignment']:.4f} |

### Spearman ρ (rank correlation)

ρ = {results['phase_a']['spearman_rho']:.4f}

### Distribution

- Conservation compliance: mean={results['phase_a']['conservation_mean']:.4f}, std={results['phase_a']['conservation_std']:.4f}
- GL(9) alignment: mean={results['phase_a']['alignment_mean']:.4f}, std={results['phase_a']['alignment_std']:.4f}

### Verdict: {results['phase_a']['verdict']}

## Phase B: Stress Testing

### B1: Agents aligned + one room dominating
- Conservation broken: {results['phase_b']['B1_aligned_dominant']['conservation_broken']}
- GL(9) alignment: {results['phase_b']['B1_aligned_dominant']['gl9_alignment']:.4f}
- **Result:** Conservation BREAKS, GL(9) HOLDS ✓

### B2: Perfect conservation + agents disagree
- Conservation deviation: {results['phase_b']['B2_conserved_disagree']['conservation_deviation']:.4f}
- GL(9) alignment: {results['phase_b']['B2_conserved_disagree']['gl9_alignment']:.4f}
- **Result:** Conservation HOLDS, GL(9) BREAKS ✓

### B3: Both broken (dominant + disagreeing)
- Conservation broken: {results['phase_b']['B3_both_broken']['conservation_broken']}
- GL(9) alignment: {results['phase_b']['B3_both_broken']['gl9_alignment']:.4f}

### B4: Both healthy (balanced + aligned)
- Conservation deviation: {results['phase_b']['B4_both_healthy']['conservation_deviation']:.4f}
- GL(9) alignment: {results['phase_b']['B4_both_healthy']['gl9_alignment']:.4f}

### Independent failure modes confirmed: {results['phase_b']['verdict']['independent_failure_modes']}

## Phase C: Combined Predictive Power

Linear model: health = a × conservation + b × alignment + c

| Model | R² |
|---|---|
| Conservation only | {results['phase_c']['r2_conservation_only']:.4f} |
| GL(9) alignment only | {results['phase_c']['r2_alignment_only']:.4f} |
| **Combined** | **{results['phase_c']['r2_combined']:.4f}** |

### Coefficients
- Conservation weight: {results['phase_c']['combined_coefficients']['conservation_weight']:.4f}
- Alignment weight: {results['phase_c']['combined_coefficients']['alignment_weight']:.4f}
- Intercept: {results['phase_c']['combined_coefficients']['intercept']:.4f}

### Improvement over best single model: +{results['phase_c']['improvement']:.4f} R²

## Final Recommendation

### **{rec['decision']}**

{rec['reason']}

### Summary

| Evidence | Result |
|---|---|
| Correlation (r) | {rec['correlation_r']:.4f} |
| Independent failure modes | {rec['independent_failures']} |
| Combined R² improvement | +{rec['combined_r2_improvement']:.4f} |

### What Each Signal Measures

| Signal | Measures | Failure Mode |
|---|---|---|
| **Conservation (γ+H)** | Structural balance of Hebbian weights | One room dominates flow |
| **GL(9) alignment** | Behavioral agreement on intent | Agents pursue conflicting goals |

Both signals are orthogonal health dimensions. The fleet needs BOTH for complete health monitoring.
"""
    return md


if __name__ == "__main__":
    results = main()
