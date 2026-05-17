#!/usr/bin/env python3
"""
EXP-5: Simulated Annealing via Precision Heterogeneity (H4)
Does a precision annealing schedule improve convergence?
INT8 → FP16 → FP32 over 100 rounds vs static FP32.
"""
import numpy as np
from scipy.linalg import eigvalsh
import json, os

np.random.seed(999)
N_AGENTS = 5
N_ROUNDS = 150

def quantize(M, bits):
    if bits >= 52: return M.copy()
    if bits >= 23: return np.float32(M).astype(np.float64)
    if bits >= 10: return np.float16(M).astype(np.float64)
    n_levels = 2 ** bits
    scale = (n_levels/2 - 1) / max(np.abs(M).max(), 1e-10)
    return np.round(M * scale).clip(-(n_levels/2-1), n_levels/2-1) / scale

def compute_gh(C):
    eigs = np.abs(eigvalsh(C))
    total = eigs.sum()
    if total < 1e-15: return 0.0, 0.0
    probs = eigs / total
    probs = probs[probs > 1e-15]
    H = float(-np.sum(probs * np.log(probs)))
    eigs_sorted = np.sort(eigs)[::-1]
    gamma = float(eigs_sorted[0] - eigs_sorted[1])
    return gamma, H

def get_bits_for_round(r, total, schedule):
    """Return per-agent bit counts based on schedule."""
    frac = r / total
    n = N_AGENTS
    if schedule == 'static_fp32':
        return [23] * n
    elif schedule == 'static_mixed':
        return [23, 23, 10, 7, 7]
    elif schedule == 'anneal_up':
        # INT8 → FP16 → FP32: precision increases over time
        if frac < 0.33:
            return [7] * n
        elif frac < 0.66:
            return [10] * n
        else:
            return [23] * n
    elif schedule == 'anneal_down':
        # FP32 → FP16 → INT8: precision decreases (negative control)
        if frac < 0.33:
            return [23] * n
        elif frac < 0.66:
            return [10] * n
        else:
            return [7] * n
    elif schedule == 'gradual_anneal':
        # Smooth transition
        bits = int(7 + (23 - 7) * frac)
        return [bits] * n
    return [23] * n

schedules = ['static_fp32', 'static_mixed', 'anneal_up', 'anneal_down', 'gradual_anneal']

# Target coupling: a known "good" coupling matrix
target = np.array([
    [1.0, 0.8, 0.3, 0.1, 0.5],
    [0.8, 1.0, 0.6, 0.2, 0.4],
    [0.3, 0.6, 1.0, 0.7, 0.3],
    [0.1, 0.2, 0.7, 1.0, 0.6],
    [0.5, 0.4, 0.3, 0.6, 1.0],
])

results = {}
for sched in schedules:
    C = np.eye(N_AGENTS) + np.random.randn(N_AGENTS, N_AGENTS) * 0.1
    C = (C + C.T) / 2; np.fill_diagonal(C, 1.0)
    
    gh_history = []
    error_history = []
    cv_history = []
    running_gh = []
    
    for r in range(N_ROUNDS):
        bits = get_bits_for_round(r, N_ROUNDS, sched)
        
        # Coupling update: move toward target + noise
        noise = np.random.randn(N_AGENTS, N_AGENTS) * 0.02
        C = C * 0.95 + target * 0.05 + noise * 0.02
        C = (C + C.T) / 2; np.fill_diagonal(C, 1.0)
        
        # Per-agent quantization
        for i, b in enumerate(bits):
            row = C[i, :].copy()
            row_q = quantize(row.reshape(1, -1), b).flatten()
            C[i, :] = row_q; C[:, i] = row_q
        C = (C + C.T) / 2; np.fill_diagonal(C, 1.0)
        
        g, h = compute_gh(C)
        gh_history.append(g + h)
        running_gh.append(g + h)
        
        # Error from target coupling
        error = float(np.linalg.norm(C - target, 'fro'))
        error_history.append(error)
        
        # Running CV (last 20 rounds)
        if len(running_gh) >= 20:
            window = running_gh[-20:]
            cv = np.std(window) / max(np.mean(window), 1e-10)
            cv_history.append(cv)
    
    # Convergence: round where CV first drops below 0.05
    convergence_round = None
    for i, cv in enumerate(cv_history):
        if cv < 0.05:
            convergence_round = i + 20  # offset by window
            break
    
    results[sched] = {
        'final_error': float(error_history[-1]),
        'convergence_round': convergence_round,
        'mean_gh_last50': float(np.mean(gh_history[-50:])),
        'cv_last50': float(np.std(gh_history[-50:]) / max(np.mean(gh_history[-50:]), 1e-10)),
        'error_trajectory': [round(e, 4) for e in error_history[::10]],
        'gh_trajectory': [round(g, 4) for g in gh_history[::10]],
    }
    
    conv_str = f"round {convergence_round}" if convergence_round else "NOT converged"
    print(f"{sched}: error={error_history[-1]:.4f}, convergence={conv_str}, CV={results[sched]['cv_last50']:.4f}")

print("\n=== Key Comparison ===")
anneal = results.get('anneal_up', {})
static = results.get('static_fp32', {})
print(f"Anneal-up convergence: {anneal.get('convergence_round', 'N/A')}")
print(f"Static-FP32 convergence: {static.get('convergence_round', 'N/A')}")
print(f"Anneal-up final error: {anneal.get('final_error', 'N/A'):.4f}")
print(f"Static-FP32 final error: {static.get('final_error', 'N/A'):.4f}")

if anneal.get('convergence_round') and static.get('convergence_round'):
    speedup = static['convergence_round'] / anneal['convergence_round']
    print(f"Speedup: {speedup:.1f}×")

with open(os.path.join(os.path.dirname(__file__), 'results_exp5.json'), 'w') as f:
    json.dump(results, f, indent=2)
print("\nResults saved to results_exp5.json")
