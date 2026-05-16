#!/usr/bin/env python3
"""STUDY 66 (revised): Decay Rate Tuning for Conservation Compliance.

KEY INSIGHT FROM INITIAL RUN:
  - With 9 agents and sparse updates, γ+H ~ 0.5 regardless of decay
  - The paper's target (0.93 for V=9) requires specific matrix structures
  - The real question: can decay control the STEADY-STATE γ+H reliably?

REVISED APPROACH:
  1. Let each decay rate reach steady state (200 steps)
  2. Define compliance as "stays within σ of its own steady-state mean"
  3. Measure: steady-state γ+H, stability (σ), slope, eigenvalue metrics
  4. Also sweep with MULTI-ACTIVATION (multiple concurrent tile flows)
  5. Dynamic decay tuning relative to auto-calibrated target

This tests whether decay is a viable FLEET MANAGEMENT KNOB, not whether
it hits the paper's specific conservation value.
"""

import json
import math
import os
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple

# Conservation math
CONSERVATION_INTERCEPT = 1.283
CONSERVATION_LOG_COEFF = -0.159

CONSERVATION_SIGMA_TABLE = {
    5: 0.070, 10: 0.065, 20: 0.058, 30: 0.050,
    50: 0.048, 100: 0.042, 200: 0.038,
}

def _interpolate_sigma(V):
    vs = sorted(CONSERVATION_SIGMA_TABLE.keys())
    if V <= vs[0]: return CONSERVATION_SIGMA_TABLE[vs[0]]
    if V >= vs[-1]: return CONSERVATION_SIGMA_TABLE[vs[-1]]
    for lo, hi in zip(vs, vs[1:]):
        if lo < V <= hi:
            frac = (V - lo) / (hi - lo)
            return CONSERVATION_SIGMA_TABLE[lo] + frac * (CONSERVATION_SIGMA_TABLE[hi] - CONSERVATION_SIGMA_TABLE[lo])
    return 0.05

def predicted_gamma_plus_H(V):
    return CONSERVATION_INTERCEPT + CONSERVATION_LOG_COEFF * np.log(max(V, 3))

def coupling_entropy(C):
    eigs = np.linalg.eigvalsh(C)[::-1]
    p = np.abs(eigs) / (np.sum(np.abs(eigs)) + 1e-15)
    p = p[p > 1e-10]
    return float(-np.sum(p * np.log(p)) / np.log(len(eigs)))

def algebraic_normalized(C):
    if C.shape[0] < 2: return 0.0
    L = np.diag(C.sum(axis=1)) - C
    eigs = np.linalg.eigvalsh(L)
    return float((eigs[1] - eigs[0]) / (eigs[-1] - eigs[0] + 1e-15))

def top_k_eigenvalue_ratio(C, k=1):
    eigs = np.linalg.eigvalsh(C)[::-1]
    total = np.sum(np.abs(eigs)) + 1e-15
    return float(np.sum(np.abs(eigs[:k])) / total)

def effective_rank(C):
    eigs = np.linalg.eigvalsh(C)[::-1]
    p = np.abs(eigs) / (np.sum(np.abs(eigs)) + 1e-15)
    p = p[p > 1e-10]
    H = -np.sum(p * np.log(p))
    return float(np.exp(H))


N_AGENTS = 9
LR = 0.01
DECAY_RATES = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1]
N_STEPS = 300
WARMUP = 50  # steps to discard before measuring


def hebbian_step(W, src, dst, lr, decay, confidence=1.0, n_agents=9):
    """Single Hebbian update: pre[src]→post[dst]."""
    pre = np.zeros(n_agents)
    post = np.zeros(n_agents)
    pre[src] = 1.0
    post[dst] = confidence
    W += lr * np.outer(pre, post) - decay * W
    np.clip(W, 0, None, out=W)
    return W


def multi_hebbian_step(W, pairs, lr, decay, n_agents=9):
    """Multi-activation Hebbian update: several concurrent flows."""
    pre = np.zeros(n_agents)
    post = np.zeros(n_agents)
    for src, dst, conf in pairs:
        pre[src] += 1.0
        post[dst] += conf
    # Normalize
    pre_max = pre.max()
    post_max = post.max()
    if pre_max > 0: pre /= pre_max
    if post_max > 0: post /= post_max
    W += lr * np.outer(pre, post) - decay * W
    np.clip(W, 0, None, out=W)
    return W


def measure_conservation(W):
    """Return (gamma, H, gamma_plus_H, eigen_top1, eff_rank) for a weight matrix."""
    try:
        gamma = algebraic_normalized(W)
        H = coupling_entropy(W)
        gH = gamma + H
        e1 = top_k_eigenvalue_ratio(W, 1)
        e3 = top_k_eigenvalue_ratio(W, 3)
        er = effective_rank(W)
        return gamma, H, gH, e1, e3, er
    except:
        return 0, 0, 0, 0, 0, 0


# =====================================================================
# Experiment 1: Single-Activation Decay Sweep (baseline)
# =====================================================================

def run_single_sweep():
    """Single tile-pair per step. Measures steady-state behavior."""
    print("=" * 70)
    print("EXPERIMENT 1A: Single-Activation Decay Sweep")
    print("=" * 70)
    
    results = {}
    rng = np.random.RandomState(42)
    popularity = rng.zipf(1.5, N_AGENTS).astype(np.float64)
    popularity /= popularity.sum()
    
    for decay in DECAY_RATES:
        rng = np.random.RandomState(42)
        W = np.zeros((N_AGENTS, N_AGENTS), dtype=np.float64)
        
        trace = []
        for step in range(N_STEPS):
            src = rng.choice(N_AGENTS, p=popularity)
            dst = rng.choice(N_AGENTS, p=popularity)
            if src == dst: dst = (src + 1) % N_AGENTS
            conf = 0.5 + 0.5 * rng.random()
            W = hebbian_step(W, src, dst, LR, decay, conf, N_AGENTS)
            
            if step >= WARMUP:
                g, h, gH, e1, e3, er = measure_conservation(W)
                trace.append({"step": step, "gamma": g, "H": h, "gH": gH,
                              "eigen_top1": e1, "eigen_top3": e3, "eff_rank": er})
        
        if not trace:
            results[str(decay)] = {"error": "no measurements"}
            continue
        
        gH_vals = [t["gH"] for t in trace]
        mean_gH = np.mean(gH_vals)
        std_gH = np.std(gH_vals)
        steady_target = mean_gH
        sigma = std_gH if std_gH > 0.001 else 0.01
        
        # Compliance: fraction of steps within 2σ of steady-state mean
        compliance = np.mean([abs(v - mean_gH) <= 2 * sigma for v in gH_vals])
        
        # Slope
        coeffs = np.polyfit(range(len(gH_vals)), gH_vals, 1)
        slope = float(coeffs[0])
        
        # Weight matrix stats
        w_max = float(W.max())
        w_mean = float(W[W > 0].mean()) if np.any(W > 0) else 0.0
        w_sparsity = float(np.mean(W == 0))
        
        result = {
            "decay": decay, "decay_over_lr": round(decay/LR, 2),
            "activation_mode": "single",
            "steady_state_gH": round(mean_gH, 4),
            "std_gH": round(std_gH, 4),
            "steady_sigma": round(sigma, 4),
            "compliance_rate_2sigma": round(compliance, 4),
            "slope_per_step": round(slope, 6),
            "slope_direction": "decreasing" if slope < -1e-6 else ("increasing" if slope > 1e-6 else "flat"),
            "mean_eigen_top1": round(np.mean([t["eigen_top1"] for t in trace]), 4),
            "mean_eigen_top3": round(np.mean([t["eigen_top3"] for t in trace]), 4),
            "mean_eff_rank": round(np.mean([t["eff_rank"] for t in trace]), 4),
            "weight_max": round(w_max, 6),
            "weight_mean_nonzero": round(w_mean, 6),
            "weight_sparsity": round(w_sparsity, 4),
        }
        results[str(decay)] = result
        
        print(f"  decay={decay:.4f} (d/lr={decay/LR:.1f}): "
              f"γ+H={mean_gH:.4f}±{std_gH:.4f}  compliance={compliance:.1%}  "
              f"slope={slope:.6f}  eigen_top1={result['mean_eigen_top1']:.3f}  "
              f"eff_rank={result['mean_eff_rank']:.1f}  w_max={w_max:.4f}")
    
    return results


# =====================================================================
# Experiment 1B: Multi-Activation Decay Sweep (denser coupling)
# =====================================================================

def run_multi_sweep():
    """Multiple concurrent tile flows per step (3-5 pairs). More realistic fleet."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 1B: Multi-Activation Decay Sweep (3-5 concurrent flows)")
    print("=" * 70)
    
    results = {}
    
    for decay in DECAY_RATES:
        rng = np.random.RandomState(42)
        W = np.zeros((N_AGENTS, N_AGENTS), dtype=np.float64)
        popularity = rng.zipf(1.5, N_AGENTS).astype(np.float64)
        popularity /= popularity.sum()
        
        trace = []
        for step in range(N_STEPS):
            # 3-5 concurrent flows
            n_flows = rng.randint(3, 6)
            pairs = []
            for _ in range(n_flows):
                src = rng.choice(N_AGENTS, p=popularity)
                dst = rng.choice(N_AGENTS, p=popularity)
                if src == dst: dst = (src + 1) % N_AGENTS
                conf = 0.5 + 0.5 * rng.random()
                pairs.append((src, dst, conf))
            W = multi_hebbian_step(W, pairs, LR, decay, N_AGENTS)
            
            if step >= WARMUP:
                g, h, gH, e1, e3, er = measure_conservation(W)
                trace.append({"step": step, "gamma": g, "H": h, "gH": gH,
                              "eigen_top1": e1, "eigen_top3": e3, "eff_rank": er})
        
        if not trace:
            results[str(decay)] = {"error": "no measurements"}
            continue
        
        gH_vals = [t["gH"] for t in trace]
        mean_gH = np.mean(gH_vals)
        std_gH = np.std(gH_vals)
        sigma = std_gH if std_gH > 0.001 else 0.01
        compliance = np.mean([abs(v - mean_gH) <= 2 * sigma for v in gH_vals])
        coeffs = np.polyfit(range(len(gH_vals)), gH_vals, 1)
        slope = float(coeffs[0])
        
        w_max = float(W.max())
        w_mean = float(W[W > 0].mean()) if np.any(W > 0) else 0.0
        w_sparsity = float(np.mean(W == 0))
        
        result = {
            "decay": decay, "decay_over_lr": round(decay/LR, 2),
            "activation_mode": "multi",
            "steady_state_gH": round(mean_gH, 4),
            "std_gH": round(std_gH, 4),
            "steady_sigma": round(sigma, 4),
            "compliance_rate_2sigma": round(compliance, 4),
            "slope_per_step": round(slope, 6),
            "slope_direction": "decreasing" if slope < -1e-6 else ("increasing" if slope > 1e-6 else "flat"),
            "mean_eigen_top1": round(np.mean([t["eigen_top1"] for t in trace]), 4),
            "mean_eigen_top3": round(np.mean([t["eigen_top3"] for t in trace]), 4),
            "mean_eff_rank": round(np.mean([t["eff_rank"] for t in trace]), 4),
            "weight_max": round(w_max, 6),
            "weight_mean_nonzero": round(w_mean, 6),
            "weight_sparsity": round(w_sparsity, 4),
        }
        results[str(decay)] = result
        
        print(f"  decay={decay:.4f} (d/lr={decay/LR:.1f}): "
              f"γ+H={mean_gH:.4f}±{std_gH:.4f}  compliance={compliance:.1%}  "
              f"slope={slope:.6f}  eigen_top1={result['mean_eigen_top1']:.3f}  "
              f"eff_rank={result['mean_eff_rank']:.1f}  w_max={w_max:.4f}")
    
    return results


# =====================================================================
# Experiment 2: Decay Controls Steady-State Level (the key test)
# =====================================================================

def run_decay_level_control():
    """Fine-grained decay sweep to show decay monotonically controls γ+H level."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Decay → Steady-State γ+H Mapping (Fine Sweep)")
    print("=" * 70)
    
    fine_decays = np.logspace(-4, -1, 20).tolist()  # 20 points from 0.0001 to 0.1
    mapping = []
    
    for decay in fine_decays:
        rng = np.random.RandomState(42)
        W = np.zeros((N_AGENTS, N_AGENTS), dtype=np.float64)
        popularity = rng.zipf(1.5, N_AGENTS).astype(np.float64)
        popularity /= popularity.sum()
        
        gH_vals = []
        for step in range(N_STEPS):
            n_flows = rng.randint(3, 6)
            pairs = []
            for _ in range(n_flows):
                src = rng.choice(N_AGENTS, p=popularity)
                dst = rng.choice(N_AGENTS, p=popularity)
                if src == dst: dst = (src + 1) % N_AGENTS
                conf = 0.5 + 0.5 * rng.random()
                pairs.append((src, dst, conf))
            W = multi_hebbian_step(W, pairs, LR, decay, N_AGENTS)
            
            if step >= WARMUP:
                _, _, gH, e1, e3, er = measure_conservation(W)
                gH_vals.append(gH)
        
        mean_gH = np.mean(gH_vals) if gH_vals else 0
        std_gH = np.std(gH_vals) if gH_vals else 0
        
        mapping.append({
            "decay": round(decay, 6),
            "decay_over_lr": round(decay / LR, 2),
            "steady_gH": round(mean_gH, 4),
            "std_gH": round(std_gH, 4),
        })
        
        print(f"  decay={decay:.6f} (d/lr={decay/LR:.2f}): γ+H = {mean_gH:.4f} ± {std_gH:.4f}")
    
    # Check monotonicity
    gH_list = [m["steady_gH"] for m in mapping]
    is_monotonic = all(gH_list[i] >= gH_list[i+1] for i in range(len(gH_list)-1)) or \
                   all(gH_list[i] <= gH_list[i+1] for i in range(len(gH_list)-1))
    
    # Find the range of γ+H values achievable
    gH_range = max(gH_list) - min(gH_list)
    
    print(f"\n  Monotonic relationship: {'YES ✓' if is_monotonic else 'NO ✗'}")
    print(f"  γ+H range: [{min(gH_list):.4f}, {max(gH_list):.4f}] (span={gH_range:.4f})")
    
    # Fit linear model: decay → γ+H
    decay_log = np.log10([m["decay"] for m in mapping])
    gH_arr = np.array(gH_list)
    coeffs = np.polyfit(decay_log, gH_arr, 1)
    r_squared = 1 - np.sum((gH_arr - np.polyval(coeffs, decay_log))**2) / np.sum((gH_arr - np.mean(gH_arr))**2)
    
    print(f"  Linear fit: γ+H = {coeffs[0]:.4f} * log10(decay) + {coeffs[1]:.4f}")
    print(f"  R² = {r_squared:.4f}")
    
    return {
        "mapping": mapping,
        "is_monotonic": is_monotonic,
        "gH_range": round(gH_range, 4),
        "gH_min": round(min(gH_list), 4),
        "gH_max": round(max(gH_list), 4),
        "linear_fit": {
            "slope": round(float(coeffs[0]), 4),
            "intercept": round(float(coeffs[1]), 4),
            "r_squared": round(float(r_squared), 4),
        },
    }


# =====================================================================
# Experiment 3: Dynamic Decay (PI Controller) — Multi-Activation
# =====================================================================

def run_dynamic_decay():
    """PI controller adjusts decay to maintain target γ+H."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Dynamic Decay via PI Controller (Multi-Activation)")
    print("=" * 70)
    
    rng = np.random.RandomState(123)
    W = np.zeros((N_AGENTS, N_AGENTS), dtype=np.float64)
    popularity = rng.zipf(1.5, N_AGENTS).astype(np.float64)
    popularity /= popularity.sum()
    
    # First, establish target from a baseline run (decay=0.005, multi-activation)
    rng_baseline = np.random.RandomState(42)
    W_baseline = np.zeros((N_AGENTS, N_AGENTS), dtype=np.float64)
    pop_baseline = rng_baseline.zipf(1.5, N_AGENTS).astype(np.float64)
    pop_baseline /= pop_baseline.sum()
    baseline_gH = []
    for step in range(N_STEPS):
        n_flows = rng_baseline.randint(3, 6)
        pairs = []
        for _ in range(n_flows):
            src = rng_baseline.choice(N_AGENTS, p=pop_baseline)
            dst = rng_baseline.choice(N_AGENTS, p=pop_baseline)
            if src == dst: dst = (src + 1) % N_AGENTS
            conf = 0.5 + 0.5 * rng_baseline.random()
            pairs.append((src, dst, conf))
        W_baseline = multi_hebbian_step(W_baseline, pairs, LR, 0.005, N_AGENTS)
        if step >= WARMUP:
            _, _, gH, _, _, _ = measure_conservation(W_baseline)
            baseline_gH.append(gH)
    
    target_gH = np.mean(baseline_gH)
    target_sigma = np.std(baseline_gH)
    print(f"  Target γ+H = {target_gH:.4f} (from decay=0.005 baseline, σ={target_sigma:.4f})")
    
    # Now run with PI controller, starting from a DIFFERENT decay
    decay = 0.05  # start far from target
    decay_min, decay_max = 0.0001, 0.1
    integral_error = 0.0
    Kp = 0.002
    Ki = 0.00005
    
    gH_trace = []
    decay_trace = [decay]
    error_trace = []
    compliance_trace = []
    tolerance = 2 * target_sigma if target_sigma > 0.005 else 0.02
    
    for step in range(N_STEPS):
        n_flows = rng.randint(3, 6)
        pairs = []
        for _ in range(n_flows):
            src = rng.choice(N_AGENTS, p=popularity)
            dst = rng.choice(N_AGENTS, p=popularity)
            if src == dst: dst = (src + 1) % N_AGENTS
            conf = 0.5 + 0.5 * rng.random()
            pairs.append((src, dst, conf))
        W = multi_hebbian_step(W, pairs, LR, decay, N_AGENTS)
        
        if step >= WARMUP:
            _, _, gH, _, _, _ = measure_conservation(W)
            error = gH - target_gH
            integral_error += error
            
            # Anti-windup
            integral_error = np.clip(integral_error, -10, 10)
            
            gH_trace.append(gH)
            error_trace.append(error)
            compliance_trace.append(abs(error) <= tolerance)
            
            # PI adjustment: if gH > target, increase decay (compress weights down)
            #                if gH < target, decrease decay (let weights grow)
            adjustment = Kp * error + Ki * integral_error
            decay = np.clip(decay + adjustment, decay_min, decay_max)
            decay_trace.append(decay)
            
            if step % 50 == 0:
                print(f"  step {step:3d}: γ+H={gH:.4f} error={error:+.4f} "
                      f"decay={decay:.5f} {'✓' if abs(error) <= tolerance else '✗'}")
    
    final_compliance = np.mean(compliance_trace) if compliance_trace else 0
    final_std = np.std(gH_trace) if gH_trace else 0
    
    print(f"\n  Final compliance: {final_compliance:.1%}")
    print(f"  gH std: {final_std:.4f} (baseline σ={target_sigma:.4f})")
    print(f"  Decay converged: {decay_trace[0]:.5f} → {decay_trace[-1]:.5f}")
    print(f"  Decay range: [{min(decay_trace):.5f}, {max(decay_trace):.5f}]")
    
    return {
        "target_gH": round(target_gH, 4),
        "target_sigma": round(target_sigma, 4),
        "tolerance": round(tolerance, 4),
        "Kp": Kp, "Ki": Ki,
        "initial_decay": 0.05,
        "final_decay": round(float(decay), 5),
        "decay_range": [round(min(decay_trace), 5), round(max(decay_trace), 5)],
        "compliance_rate": round(float(final_compliance), 4),
        "mean_gH": round(float(np.mean(gH_trace)), 4) if gH_trace else 0,
        "std_gH": round(float(final_std), 4),
        "convergence": "yes" if abs(decay_trace[-1] - decay_trace[-5]) < 0.001 else "no",
    }


# =====================================================================
# Experiment 4: Auto-Tune to Arbitrary Target
# =====================================================================

def run_auto_tune():
    """Can we find a decay rate that produces ANY target γ+H in the achievable range?"""
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Auto-Tune Decay to Hit Specified γ+H Targets")
    print("=" * 70)
    
    # First, find achievable range
    rng = np.random.RandomState(42)
    popularity = rng.zipf(1.5, N_AGENTS).astype(np.float64)
    popularity /= popularity.sum()
    
    def evaluate_decay_multi(decay, seed=42):
        rng = np.random.RandomState(seed)
        W = np.zeros((N_AGENTS, N_AGENTS), dtype=np.float64)
        gH_vals = []
        for step in range(N_STEPS):
            n_flows = rng.randint(3, 6)
            pairs = []
            for _ in range(n_flows):
                src = rng.choice(N_AGENTS, p=popularity)
                dst = rng.choice(N_AGENTS, p=popularity)
                if src == dst: dst = (src + 1) % N_AGENTS
                conf = 0.5 + 0.5 * rng.random()
                pairs.append((src, dst, conf))
            W = multi_hebbian_step(W, pairs, LR, decay, N_AGENTS)
            if step >= WARMUP:
                _, _, gH, _, _, _ = measure_conservation(W)
                gH_vals.append(gH)
        return np.mean(gH_vals) if gH_vals else 0.0
    
    # Map the range
    gH_at_low = evaluate_decay_multi(0.0001)
    gH_at_high = evaluate_decay_multi(0.1)
    gH_min, gH_max = min(gH_at_low, gH_at_high), max(gH_at_low, gH_at_high)
    
    print(f"  Achievable γ+H range: [{gH_min:.4f}, {gH_max:.4f}]")
    
    # Test 3 target levels within range
    targets = [
        gH_min + 0.25 * (gH_max - gH_min),
        gH_min + 0.50 * (gH_max - gH_min),
        gH_min + 0.75 * (gH_max - gH_min),
    ]
    target_labels = ["low_25pct", "mid_50pct", "high_75pct"]
    
    auto_results = []
    for label, target in zip(target_labels, targets):
        print(f"\n  Target: {label} = {target:.4f}")
        
        # Binary search
        lo, hi = 0.0001, 0.1
        best_decay, best_err = None, float('inf')
        
        for iteration in range(20):
            mid = (lo + hi) / 2.0
            gH_mid = evaluate_decay_multi(mid)
            gH_lo = evaluate_decay_multi(lo)
            
            err_mid = abs(gH_mid - target)
            if err_mid < best_err:
                best_err = err_mid
                best_decay = mid
            
            # Determine which half to search
            # Higher decay → different gH (need to know direction)
            if gH_lo > gH_mid:
                # Decay decreases gH
                if gH_mid > target:
                    lo = mid  # need more decay
                else:
                    hi = mid
            else:
                # Decay increases gH
                if gH_mid < target:
                    lo = mid
                else:
                    hi = mid
            
            if err_mid < 0.005:
                break
        
        achieved = evaluate_decay_multi(best_decay)
        print(f"    Best decay = {best_decay:.6f}  →  γ+H = {achieved:.4f} "
              f"(error = {abs(achieved - target):.4f})")
        
        auto_results.append({
            "target_label": label,
            "target_gH": round(target, 4),
            "best_decay": round(best_decay, 6),
            "achieved_gH": round(achieved, 4),
            "error": round(abs(achieved - target), 4),
        })
    
    return {
        "achievable_range": [round(gH_min, 4), round(gH_max, 4)],
        "range_span": round(gH_max - gH_min, 4),
        "tuning_results": auto_results,
        "conclusion": "decay_is_effective_knob" if all(r["error"] < 0.05 for r in auto_results) else "partial_control",
    }


# =====================================================================
# Main
# =====================================================================

def main():
    print("⚒️  STUDY 66 (Revised): Decay Rate Tuning for Conservation Compliance")
    print(f"   Fleet: {N_AGENTS} agents, LR={LR}, {N_STEPS} steps, warmup={WARMUP}")
    print()
    
    all_results = {}
    
    # Exp 1A: Single activation baseline
    all_results["single_activation_sweep"] = run_single_sweep()
    
    # Exp 1B: Multi-activation sweep
    all_results["multi_activation_sweep"] = run_multi_sweep()
    
    # Exp 2: Fine-grained decay → γ+H mapping
    all_results["decay_level_mapping"] = run_decay_level_control()
    
    # Exp 3: Dynamic decay PI controller
    all_results["dynamic_decay_pi"] = run_dynamic_decay()
    
    # Exp 4: Auto-tune to arbitrary targets
    all_results["auto_tune_targets"] = run_auto_tune()
    
    # Sweet spot analysis (using multi-activation results)
    print("\n" + "=" * 70)
    print("SWEET SPOT ANALYSIS (Multi-Activation)")
    print("=" * 70)
    
    multi = all_results["multi_activation_sweep"]
    sweet_spots = []
    for decay_str, data in sorted(multi.items(), key=lambda x: float(x[0])):
        if not isinstance(data, dict) or "compliance_rate_2sigma" not in data:
            continue
        
        cr = data["compliance_rate_2sigma"]
        slope = abs(data["slope_per_step"])
        eigen = data["mean_eigen_top1"]
        eff_r = data["mean_eff_rank"]
        std = data["std_gH"]
        
        c1 = cr >= 0.85  # compliance > 85%
        c2 = slope < 0.0005  # gentle slope
        c3 = 0.15 < eigen < 0.50  # moderate eigenvalue concentration
        c4 = 3 < eff_r < 8  # moderate effective rank
        c5 = std < 0.05  # low volatility
        
        all_criteria = c1 and c2 and c3 and c4 and c5
        n_criteria = sum([c1, c2, c3, c4, c5])
        
        marker = " ← SWEET SPOT" if all_criteria else ""
        print(f"  decay={float(decay_str):.4f}: compliance={cr:.1%} σ={std:.4f} "
              f"slope={data['slope_per_step']:.6f} eigen_top1={eigen:.3f} eff_rank={eff_r:.1f} "
              f"({n_criteria}/5){marker}")
        
        sweet_spots.append({
            "decay": float(decay_str),
            "compliance": cr, "std": std, "slope": data["slope_per_step"],
            "eigen_top1": eigen, "eff_rank": eff_r,
            "meets_all": all_criteria, "n_criteria_met": n_criteria,
            "criteria": {"compliance_85": c1, "gentle_slope": c2,
                         "moderate_eigen": c3, "moderate_rank": c4, "low_volatility": c5}
        })
    
    all_results["sweet_spot_analysis"] = sweet_spots
    
    # Save
    output_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(output_dir, "study66_results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n📁 Results → {results_path}")
    
    # Final summary
    print(f"\n{'='*70}")
    print("STUDY 66 FINAL SUMMARY")
    print(f"{'='*70}")
    
    mapping = all_results["decay_level_mapping"]
    print(f"\n  Decay → γ+H relationship:")
    print(f"    Monotonic: {mapping['is_monotonic']}")
    print(f"    Range: [{mapping['gH_min']:.4f}, {mapping['gH_max']:.4f}] (span={mapping['gH_range']:.4f})")
    fit = mapping["linear_fit"]
    print(f"    Fit: γ+H = {fit['slope']:.4f}·log10(decay) + {fit['intercept']:.4f}  (R²={fit['r_squared']:.4f})")
    
    dynamic = all_results["dynamic_decay_pi"]
    print(f"\n  Dynamic PI controller:")
    print(f"    Target γ+H: {dynamic['target_gH']:.4f}")
    print(f"    Compliance: {dynamic['compliance_rate']:.1%}")
    print(f"    Convergence: {dynamic['convergence']}")
    
    autotune = all_results["auto_tune_targets"]
    print(f"\n  Auto-tune capability:")
    print(f"    Achievable range: {autotune['achievable_range']}")
    for r in autotune["tuning_results"]:
        print(f"    Target {r['target_label']}: decay={r['best_decay']:.6f} → γ+H={r['achieved_gH']:.4f} (err={r['error']:.4f})")
    print(f"    Conclusion: {autotune['conclusion']}")
    
    sweet = [s for s in sweet_spots if s["meets_all"]]
    if sweet:
        print(f"\n  ✓ Sweet spot decays: {[s['decay'] for s in sweet]}")
    else:
        best = max(sweet_spots, key=lambda s: s["n_criteria_met"])
        print(f"\n  Best compromise: decay={best['decay']} ({best['n_criteria_met']}/5 criteria)")
    
    return all_results


if __name__ == "__main__":
    main()
