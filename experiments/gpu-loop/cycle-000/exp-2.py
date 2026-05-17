#!/usr/bin/env python3
"""
EXP-2: Spectral Gap Persistence Across Precision Boundaries (H2)
Does heterogeneity prevent γ→0 collapse?
Tests: γ_floor > 0 in mixed-precision fleets vs γ→0 in homogeneous fleets.
"""
import numpy as np
from scipy.linalg import eigvalsh
import json, os

np.random.seed(123)
N_AGENTS = 5
N_ROUNDS = 300
RESULTS = {}

def quantize(M, precision):
    if precision == 'FP64': return M.copy()
    elif precision == 'FP32': return np.float32(M).astype(np.float64)
    elif precision == 'FP16': return np.float16(M).astype(np.float64)
    elif precision == 'INT8':
        scale = 127.0 / max(np.abs(M).max(), 1e-10)
        return np.round(M * scale).clip(-128, 127) / scale
    elif precision == 'INT4':
        scale = 7.0 / max(np.abs(M).max(), 1e-10)
        return np.round(M * scale).clip(-7, 7) / scale
    return M.copy()

def coupling_round(C, precisions, noise_scale=0.005):
    n = C.shape[0]
    for i in range(n):
        for j in range(i+1, n):
            update = noise_scale * np.random.randn()
            C[i, j] += update
            C[j, i] += update
    # Quantize per-agent
    C_q = C.copy()
    for i, prec in enumerate(precisions):
        row = C_q[i, :].copy()
        row_q = quantize(row.reshape(1, -1), prec).flatten()
        C_q[i, :] = row_q
        C_q[:, i] = row_q
    np.fill_diagonal(C_q, 1.0)
    C_q = (C_q + C_q.T) / 2
    return C_q

def spectral_gap(C):
    eigs = np.sort(np.abs(eigvalsh(C)))[::-1]
    return float(eigs[0] - eigs[1]) if len(eigs) > 1 else 0.0

configs = {
    'homo_FP32': ['FP32'] * N_AGENTS,
    'homo_FP16': ['FP16'] * N_AGENTS,
    'homo_INT8': ['INT8'] * N_AGENTS,
    'mix_FP32_FP16': ['FP32', 'FP32', 'FP16', 'FP16', 'FP16'],
    'mix_FP32_INT8': ['FP32', 'FP32', 'INT8', 'INT8', 'INT8'],
    'mix_all': ['FP32', 'FP16', 'FP16', 'INT8', 'INT8'],
}

for name, precs in configs.items():
    C = np.eye(N_AGENTS) + np.random.randn(N_AGENTS, N_AGENTS) * 0.01
    C = (C + C.T) / 2
    
    gaps = []
    for r in range(N_ROUNDS):
        C = coupling_round(C, precs)
        gaps.append(spectral_gap(C))
    
    # Fit exponential decay: γ(t) = γ₀·exp(-λt) + γ_floor
    t = np.arange(len(gaps))
    log_gaps = np.log(np.array(gaps) + 1e-15)
    
    # Use last 100 rounds as "floor" estimate
    floor_est = float(np.mean(gaps[-100:]))
    
    RESULTS[name] = {
        'precisions': precs,
        'gamma_trajectory_last20': [round(g, 6) for g in gaps[-20:]],
        'gamma_floor_last100': floor_est,
        'gamma_round_30': gaps[30],
        'gamma_round_100': gaps[100],
        'gamma_round_200': gaps[200] if len(gaps) > 200 else gaps[-1],
        'min_gamma': float(min(gaps)),
        'max_gamma': float(max(gaps)),
    }
    
    # Classify: collapsed (γ < 0.001) or persistent
    collapsed = floor_est < 0.001
    print(f"{name}: γ_floor = {floor_est:.6f} | γ@30={gaps[30]:.4f} | γ@100={gaps[100]:.4f} | collapsed={collapsed}")

# Key comparison
print("\n=== Key Finding ===")
homo_floors = [RESULTS[k]['gamma_floor_last100'] for k in RESULTS if k.startswith('homo_')]
hetero_floors = [RESULTS[k]['gamma_floor_last100'] for k in RESULTS if k.startswith('mix_')]
print(f"Homogeneous γ floor: {np.mean(homo_floors):.6f} (range: {min(homo_floors):.6f} - {max(homo_floors):.6f})")
print(f"Heterogeneous γ floor: {np.mean(hetero_floors):.6f} (range: {min(hetero_floors):.6f} - {max(hetero_floors):.6f})")
print(f"Heterogeneity prevents collapse? {np.mean(hetero_floors) > np.mean(homo_floors)}")

with open(os.path.join(os.path.dirname(__file__), 'results_exp2.json'), 'w') as f:
    json.dump(RESULTS, f, indent=2)
print("\nResults saved to results_exp2.json")
