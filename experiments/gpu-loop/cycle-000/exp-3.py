#!/usr/bin/env python3
"""
EXP-3: Conservation Law Breakdown at Critical Precision Ratios (H5)
Where does γ+H stop being conserved?
Sweeps precision ratios systematically.
"""
import numpy as np
from scipy.linalg import eigvalsh
from scipy.stats import entropy
import json, os

np.random.seed(777)
N_AGENTS = 5
N_ROUNDS = 200

def quantize(M, bits):
    """Quantize to specified number of bits (mantissa bits for float simulation)."""
    if bits >= 52: return M.copy()  # FP64
    if bits >= 23: return np.float32(M).astype(np.float64)  # FP32
    if bits >= 10: return np.float16(M).astype(np.float64)  # FP16
    
    # Custom bit precision: 2^bits levels
    n_levels = 2 ** bits
    scale = (n_levels / 2 - 1) / max(np.abs(M).max(), 1e-10)
    M_q = np.round(M * scale).clip(-(n_levels/2 - 1), n_levels/2 - 1) / scale
    return M_q

def compute_gh(C):
    eigs = np.abs(eigvalsh(C))
    total = eigs.sum()
    if total < 1e-15: return 0.0, 0.0
    probs = eigs / total
    probs = probs[probs > 1e-15]
    H = float(-np.sum(probs * np.log(probs)))
    eigs_sorted = np.sort(eigs)[::-1]
    gamma = float(eigs_sorted[0] - eigs_sorted[1]) if len(eigs_sorted) > 1 else 0.0
    return gamma, H

def simulate_fleet_mixed(hi_bits, lo_bits, n_agents=N_AGENTS, n_rounds=N_ROUNDS):
    """Simulate fleet with 2 hi-precision + 3 lo-precision agents."""
    bits_per_agent = [hi_bits]*2 + [lo_bits]*3
    
    C = np.eye(n_agents) + np.random.randn(n_agents, n_agents) * 0.05
    C = (C + C.T) / 2
    np.fill_diagonal(C, 1.0)
    
    gh_history = []
    for r in range(n_rounds):
        # Coupling dynamics
        noise = np.random.randn(n_agents, n_agents) * 0.01
        C = C * 0.98 + noise * 0.02
        C = (C + C.T) / 2
        np.fill_diagonal(C, 1.0)
        
        # Per-agent quantization
        for i, bits in enumerate(bits_per_agent):
            row = C[i, :].copy()
            row_q = quantize(row.reshape(1, -1), bits).flatten()
            C[i, :] = row_q
            C[:, i] = row_q
        C = (C + C.T) / 2
        np.fill_diagonal(C, 1.0)
        
        g, h = compute_gh(C)
        gh_history.append(g + h)
    
    return gh_history

# Precision ratio sweep
# Ratios from 1:1 (homo) to extreme (FP64 vs 2-bit)
configs = [
    ('FP32_vs_FP32', 23, 23),      # ratio 1:1
    ('FP32_vs_FP16', 23, 10),       # ratio ~8K:1
    ('FP32_vs_8bit', 23, 7),        # ratio ~65K:1  
    ('FP64_vs_FP16', 52, 10),       # ratio ~4M:1
    ('FP64_vs_8bit', 52, 7),        # ratio ~17T:1
    ('FP64_vs_4bit', 52, 4),        # ratio ~281T:1
    ('FP64_vs_2bit', 52, 2),        # ratio ~extreme
    ('FP64_vs_1bit', 52, 1),        # ratio ~max
]

results = {}
for name, hi, lo in configs:
    ratio = 2**hi / max(2**lo, 1)
    
    # Run 5 trials for stability
    all_gh = []
    for trial in range(5):
        gh = simulate_fleet_mixed(hi, lo)
        all_gh.append(gh)
    
    # Average across trials
    mean_gh = np.mean(all_gh, axis=0)
    last100 = mean_gh[-100:]
    
    cv = float(np.std(last100) / max(np.mean(last100), 1e-10))
    
    results[name] = {
        'hi_bits': hi, 'lo_bits': lo,
        'ratio': float(ratio),
        'mean_gh': float(np.mean(last100)),
        'std_gh': float(np.std(last100)),
        'cv_gh': cv,
        'conservation_holds': cv < 0.10,
        'gh_last5': [round(x, 4) for x in mean_gh[-5:].tolist()],
    }
    
    status = "✓ CONSERVED" if cv < 0.10 else ("~ MARGINAL" if cv < 0.20 else "✗ BROKEN")
    print(f"{name} (ratio={ratio:.1e}): CV={cv:.4f} {status}")

# Find critical ratio
print("\n=== Critical Precision Ratio ===")
for name, data in results.items():
    print(f"  {name}: ratio={data['ratio']:.1e}, CV={data['cv_gh']:.4f}, conserved={data['conservation_holds']}")

# Check if λ₁-λ₂ gap relates to breakdown
print("\n=== Eigenvalue Gap Analysis ===")
for name, hi, lo in configs:
    bits = [hi]*2 + [lo]*3
    C = np.eye(N_AGENTS) + np.random.randn(N_AGENTS, N_AGENTS) * 0.1
    C = (C + C.T) / 2
    for i, b in enumerate(bits):
        row = C[i, :].copy()
        row_q = quantize(row.reshape(1, -1), b).flatten()
        C[i, :] = row_q; C[:, i] = row_q
    C = (C + C.T) / 2; np.fill_diagonal(C, 1.0)
    eigs = np.sort(np.abs(eigvalsh(C)))[::-1]
    gap = eigs[0] - eigs[1]
    q_step = 1.0 / (2**lo - 1) if lo < 23 else 1e-8
    gap_resolved = gap > q_step
    print(f"  {name}: λ₁-λ₂ gap={gap:.6f}, quant_step={q_step:.6f}, resolved={gap_resolved}")

with open(os.path.join(os.path.dirname(__file__), 'results_exp3.json'), 'w') as f:
    json.dump(results, f, indent=2)
print("\nResults saved to results_exp3.json")
