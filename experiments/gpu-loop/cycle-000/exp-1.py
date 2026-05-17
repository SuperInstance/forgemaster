#!/usr/bin/env python3
"""
EXP-1: Precision-Dependent Conservation Constants (H1)
Does the coupling constant C shift with mixed precision?
Tests: C_heterogeneous > C_homogeneous?
"""
import numpy as np
from scipy.linalg import eigvalsh
from scipy.stats import entropy
import json, os

np.random.seed(42)
N_AGENTS = 5
N_ROUNDS = 200
RESULTS = {}

def quantize_matrix(M, precision):
    """Simulate precision by quantizing matrix entries."""
    if precision == 'FP64':
        return M.copy()
    elif precision == 'FP32':
        return np.float32(M).astype(np.float64)
    elif precision == 'FP16':
        return np.float16(M).astype(np.float64)
    elif precision == 'INT8':
        # Scale to [-128, 127], quantize, scale back
        scale = 127.0 / max(np.abs(M).max(), 1e-10)
        M_int = np.round(M * scale).clip(-128, 127)
        return M_int / scale
    elif precision == 'INT4':
        scale = 7.0 / max(np.abs(M).max(), 1e-10)
        M_int = np.round(M * scale).clip(-7, 7)
        return M_int / scale
    return M.copy()

def compute_gamma_H(C):
    """Compute spectral gap gamma and entropy H from coupling matrix."""
    eigs = eigvalsh(C)
    eigs = np.sort(np.abs(eigs))[::-1]  # descending by magnitude
    total = eigs.sum()
    if total < 1e-15:
        return 0.0, 0.0
    probs = eigs / total
    probs = probs[probs > 1e-15]
    H = float(-np.sum(probs * np.log(probs)))
    gamma = float(eigs[0] - eigs[1]) if len(eigs) > 1 else float(eigs[0])
    return gamma, H

def simulate_fleet(precisions, n_rounds=N_ROUNDS):
    """Simulate a fleet with given precision mix."""
    n = len(precisions)
    gammas, Hs = [], []
    # Initial coupling matrix
    C = np.random.randn(n, n) * 0.1
    C = (C + C.T) / 2  # symmetric
    np.fill_diagonal(C, 1.0)
    
    for r in range(n_rounds):
        # Each agent updates based on coupling
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Coupling update with noise scaled by precision
                    noise = np.random.randn() * 0.01
                    C[i, j] = C[i, j] * 0.95 + 0.05 * (C[j, i] + noise)
        # Make symmetric
        C = (C + C.T) / 2
        np.fill_diagonal(C, 1.0)
        
        # Quantize each agent's row/col to its precision
        C_quant = C.copy()
        for i, prec in enumerate(precisions):
            row = C_quant[i, :].copy()
            col = C_quant[:, i].copy()
            # Quantize the agent's perspective
            row_q = quantize_matrix(row.reshape(1, -1), prec).flatten()
            C_quant[i, :] = row_q
            C_quant[:, i] = row_q  # symmetric update
        np.fill_diagonal(C_quant, 1.0)
        C = C_quant
        
        g, h = compute_gamma_H(C)
        gammas.append(g)
        Hs.append(h)
    
    return gammas, Hs, C

# === CONFIGURATIONS ===
configs = {
    'homo_FP64': ['FP64'] * N_AGENTS,
    'homo_FP32': ['FP32'] * N_AGENTS,
    'homo_FP16': ['FP16'] * N_AGENTS,
    'homo_INT8': ['INT8'] * N_AGENTS,
    'hetero_gradual': ['FP64', 'FP32', 'FP16', 'FP16', 'INT8'],
    'hetero_extreme': ['FP64', 'FP64', 'INT8', 'INT8', 'INT4'],
    'hetero_balanced': ['FP32', 'FP32', 'FP16', 'INT8', 'INT8'],
}

all_results = {}
for name, precs in configs.items():
    gammas, Hs, final_C = simulate_fleet(precs)
    gh = [g + h for g, h in zip(gammas, Hs)]
    gh_arr = np.array(gh[50:])  # skip transient
    
    all_results[name] = {
        'precisions': precs,
        'mean_gh': float(np.mean(gh_arr)),
        'std_gh': float(np.std(gh_arr)),
        'cv_gh': float(np.std(gh_arr) / max(np.mean(gh_arr), 1e-10)),
        'mean_gamma': float(np.mean(gammas[50:])),
        'mean_H': float(np.mean(Hs[50:])),
        'final_gamma': float(gammas[-1]),
        'final_H': float(Hs[-1]),
        'gh_trajectory_last10': [round(x, 4) for x in gh[-10:]],
    }
    print(f"{name}: γ+H = {np.mean(gh_arr):.4f} ± {np.std(gh_arr):.4f} (CV={np.std(gh_arr)/max(np.mean(gh_arr),1e-10):.4f})")

# Conservation law fit: γ+H = C - α·ln(V_eff)
# V_eff = average distinguishable states per agent
V_eff = {
    'homo_FP64': 4.5e15, 'homo_FP32': 8.4e6, 'homo_FP16': 1024, 'homo_INT8': 256,
    'hetero_gradual': np.exp(np.mean([np.log(4.5e15), np.log(8.4e6), np.log(1024), np.log(1024), np.log(256)])),
    'hetero_extreme': np.exp(np.mean([np.log(4.5e15), np.log(4.5e15), np.log(256), np.log(256), np.log(16)])),
    'hetero_balanced': np.exp(np.mean([np.log(8.4e6), np.log(8.4e6), np.log(1024), np.log(256), np.log(256)])),
}

print("\n=== Conservation Constant Comparison ===")
for name in all_results:
    C_val = all_results[name]['mean_gh'] + np.log(V_eff[name])
    all_results[name]['C_estimate'] = C_val
    all_results[name]['V_eff'] = V_eff[name]
    print(f"{name}: C ≈ {C_val:.4f} (V_eff = {V_eff[name]:.2e})")

# Key test: is C_hetero > C_homo?
homo_Cs = [all_results[k]['C_estimate'] for k in all_results if k.startswith('homo_')]
hetero_Cs = [all_results[k]['C_estimate'] for k in all_results if k.startswith('hetero_')]
print(f"\nHomo C mean: {np.mean(homo_Cs):.4f}")
print(f"Hetero C mean: {np.mean(hetero_Cs):.4f}")
print(f"C_hetero > C_homo? {np.mean(hetero_Cs) > np.mean(homo_Cs)}")

with open(os.path.join(os.path.dirname(__file__), 'results_exp1.json'), 'w') as f:
    json.dump(all_results, f, indent=2)
print("\nResults saved to results_exp1.json")
