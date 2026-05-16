#!/usr/bin/env python3
"""Study 65: What makes the Hebbian ensemble produce a DECREASING slope?

Simulates 6 matrix generation regimes across V=3..50, computing γ, H, and γ+H
for each. Identifies which structural property inverts the slope direction.
"""

import json
import numpy as np
from scipy import linalg as la
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import laplacian
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# ── Spectral metrics (matching the paper's definitions) ──────────────────

def compute_gamma(C):
    """Normalized algebraic connectivity from Laplacian of coupling matrix C."""
    n = C.shape[0]
    if n < 2:
        return 0.0
    L = np.diag(C.sum(axis=1)) - C
    eigvals = np.sort(np.real(la.eigvals(L)))
    lam0, lam1, lamn = eigvals[0], eigvals[1], eigvals[-1]
    denom = lamn - lam0
    if denom < 1e-12:
        return 0.0
    return (lam1 - lam0) / denom

def compute_H(C):
    """Spectral entropy of coupling matrix C."""
    n = C.shape[0]
    if n < 2:
        return 0.0
    eigvals = np.sort(np.real(la.eigvals(C)))[::-1]  # descending
    abs_eig = np.abs(eigvals)
    total = abs_eig.sum()
    if total < 1e-12:
        return 0.0
    p = abs_eig / total
    p = p[p > 1e-15]  # avoid log(0)
    H_raw = -np.sum(p * np.log(p))
    H_norm = H_raw / np.log(n) if np.log(n) > 0 else 0.0
    return np.clip(H_norm, 0.0, 1.0)

# ── Matrix generation regimes ────────────────────────────────────────────

def gen_random_dense(V):
    """Baseline: symmetric dense U[0,1]"""
    A = np.random.uniform(0, 1, (V, V))
    return (A + A.T) / 2

def gen_hebbian(V, n_steps=None):
    """Hebbian STDP: outer product learning with decay.
    
    Simulates V agents with random activation patterns.
    Repeated co-activation strengthens connections (fire together, wire together).
    """
    if n_steps is None:
        n_steps = max(200, V * 20)
    
    lr = 0.01
    decay = 0.001
    W = np.random.uniform(0, 0.05, (V, V))
    W = (W + W.T) / 2
    
    for _ in range(n_steps):
        # Random activation pattern — sparse, only ~30% active
        x = np.random.binomial(1, 0.3, V).astype(float)
        # STDP update: ΔW = lr * x * x^T - decay * W
        delta = lr * np.outer(x, x) - decay * W
        W += delta
        # Enforce symmetry and non-negativity
        W = np.maximum(0, (W + W.T) / 2)
    
    # Normalize to [0,1] range
    if W.max() > 1e-10:
        W /= W.max()
    return W

def gen_hebbian_clustered(V, n_clusters=None, n_steps=None):
    """Hebbian with community structure — agents in same cluster co-activate more.
    
    This models the PLATO fleet where rooms in the same module interact heavily.
    """
    if n_clusters is None:
        n_clusters = max(2, V // 5)
    if n_steps is None:
        n_steps = max(300, V * 25)
    
    lr = 0.01
    decay = 0.001
    W = np.random.uniform(0, 0.02, (V, V))
    W = (W + W.T) / 2
    
    # Assign agents to clusters
    assignments = np.random.randint(0, n_clusters, V)
    
    for _ in range(n_steps):
        # Pick a random cluster to activate
        active_cluster = np.random.randint(0, n_clusters)
        x = np.zeros(V)
        # Agents in active cluster: high activation probability
        for i in range(V):
            if assignments[i] == active_cluster:
                x[i] = np.random.binomial(1, 0.7)
            else:
                x[i] = np.random.binomial(1, 0.05)  # rare cross-cluster
        
        delta = lr * np.outer(x, x) - decay * W
        W += delta
        W = np.maximum(0, (W + W.T) / 2)
    
    if W.max() > 1e-10:
        W /= W.max()
    return W

def gen_sparse_random(V, p=0.3):
    """Erdős–Rényi sparse random graph with edge probability p."""
    A = np.random.uniform(0, 1, (V, V))
    mask = np.random.binomial(1, p, (V, V))
    A *= mask
    return (A + A.T) / 2

def gen_block_diagonal(V, n_blocks=None):
    """Block diagonal (modular structure)."""
    if n_blocks is None:
        n_blocks = max(2, V // 5)
    
    W = np.zeros((V, V))
    block_size = V // n_blocks
    
    for b in range(n_blocks):
        start = b * block_size
        end = start + block_size if b < n_blocks - 1 else V
        size = end - start
        block = np.random.uniform(0, 1, (size, size))
        block = (block + block.T) / 2
        W[start:end, start:end] = block
    
    # Add weak inter-block connections
    for i in range(V):
        for j in range(i+1, V):
            if W[i,j] == 0 and np.random.random() < 0.05:
                val = np.random.uniform(0, 0.1)
                W[i,j] = W[j,i] = val
    
    return W

def gen_scale_free(V, m=3):
    """Scale-free network via preferential attachment (Barabási-Albert)."""
    # Start with a small complete graph
    W = np.zeros((V, V))
    initial = min(m + 1, V)
    for i in range(initial):
        for j in range(i+1, initial):
            val = np.random.uniform(0.3, 1.0)
            W[i,j] = W[j,i] = val
    
    # Degree tracking for preferential attachment
    degrees = W.sum(axis=1)
    
    for new_node in range(initial, V):
        # Preferential attachment: pick m existing nodes weighted by degree
        existing = np.arange(new_node)
        deg = degrees[:new_node]
        if deg.sum() < 1e-10:
            targets = np.random.choice(existing, min(m, new_node), replace=False)
        else:
            prob = deg / deg.sum()
            targets = np.random.choice(existing, min(m, new_node), replace=False, p=prob)
        
        for t in targets:
            val = np.random.uniform(0.3, 1.0)
            W[new_node, t] = W[t, new_node] = val
        
        degrees = W.sum(axis=1)
    
    if W.max() > 1e-10:
        W /= W.max()
    return W

def gen_anticorrelated(V, n_groups=None):
    """Anti-correlated: negative correlations between some groups.
    
    Some agents are inhibitory — their coupling suppresses others.
    Modeled as mixed-sign correlations but kept non-negative by shifting.
    """
    if n_groups is None:
        n_groups = max(2, V // 4)
    
    # Generate base correlation structure
    assignments = np.random.randint(0, n_groups, V)
    W = np.zeros((V, V))
    
    for i in range(V):
        for j in range(i+1, V):
            if assignments[i] == assignments[j]:
                # Same group: positive correlation
                W[i,j] = np.random.uniform(0.5, 1.0)
            else:
                # Different groups: weak or negative (shifted to small positive)
                W[i,j] = np.random.uniform(0.0, 0.15)
    
    W = (W + W.T) / 2
    return W

def gen_rank1_plus_noise(V, noise_scale=0.1):
    """Approximately rank-1 (like a fully Hebbian-converged matrix).
    
    Dominant eigenvector captures most of the structure.
    """
    # Rank-1 component: outer product of a positive vector
    v = np.random.uniform(0.5, 1.5, V)
    W = np.outer(v, v)
    # Add small noise
    W += noise_scale * np.random.randn(V, V)
    W = np.maximum(0, (W + W.T) / 2)
    if W.max() > 1e-10:
        W /= W.max()
    return W

# ── Main experiment ──────────────────────────────────────────────────────

REGIMES = {
    "random_dense": gen_random_dense,
    "hebbian": gen_hebbian,
    "hebbian_clustered": gen_hebbian_clustered,
    "sparse_random": gen_sparse_random,
    "block_diagonal": gen_block_diagonal,
    "scale_free": gen_scale_free,
    "anticorrelated": gen_anticorrelated,
    "rank1_plus_noise": gen_rank1_plus_noise,
}

V_RANGE = list(range(3, 51))
N_SAMPLES = 30  # per (regime, V) combination

results = defaultdict(list)
summary = {}

print("Study 65: Ensemble Slope Analysis")
print("=" * 60)

for regime_name, gen_fn in REGIMES.items():
    print(f"\n--- Regime: {regime_name} ---")
    regime_data = []
    
    for V in V_RANGE:
        gammas, entropies, sums = [], [], []
        
        for sample in range(N_SAMPLES):
            try:
                W = gen_fn(V)
                g = compute_gamma(W)
                h = compute_H(W)
                gammas.append(g)
                entropies.append(h)
                sums.append(g + h)
            except Exception as e:
                continue
        
        if not gammas:
            continue
        
        mean_g = np.mean(gammas)
        mean_h = np.mean(entropies)
        mean_sum = np.mean(sums)
        
        regime_data.append({
            "V": V,
            "gamma_mean": mean_g,
            "H_mean": mean_h,
            "gammaH_mean": mean_sum,
            "gamma_std": np.std(gammas),
            "H_std": np.std(entropies),
            "gammaH_std": np.std(sums),
            "n_samples": len(gammas),
        })
    
    # Fit slope of γ+H vs ln(V)
    if len(regime_data) >= 5:
        Vs = np.array([d["V"] for d in regime_data])
        lnV = np.log(Vs)
        gammaH = np.array([d["gammaH_mean"] for d in regime_data])
        gammas_arr = np.array([d["gamma_mean"] for d in regime_data])
        Hs = np.array([d["H_mean"] for d in regime_data])
        
        # Fit γ+H = intercept + slope * ln(V)
        coeffs = np.polyfit(lnV, gammaH, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
        
        # R²
        y_pred = np.polyval(coeffs, lnV)
        ss_res = np.sum((gammaH - y_pred) ** 2)
        ss_tot = np.sum((gammaH - np.mean(gammaH)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        
        # Also fit γ and H separately
        g_coeffs = np.polyfit(lnV, gammas_arr, 1)
        h_coeffs = np.polyfit(lnV, Hs, 1)
        
        summary[regime_name] = {
            "slope_gammaH": float(slope),
            "intercept_gammaH": float(intercept),
            "r2_gammaH": float(r2),
            "slope_gamma": float(g_coeffs[0]),
            "slope_H": float(h_coeffs[0]),
            "direction": "DECREASING" if slope < 0 else "INCREASING",
        }
        
        print(f"  γ+H slope: {slope:+.4f}  intercept: {intercept:.4f}  R²: {r2:.4f}  [{summary[regime_name]['direction']}]")
        print(f"  γ slope: {g_coeffs[0]:+.4f}   H slope: {h_coeffs[0]:+.4f}")
    else:
        print(f"  Not enough data points")
    
    results[regime_name] = regime_data

# ── Structural analysis of regimes ──────────────────────────────────────

print("\n\n" + "=" * 60)
print("STRUCTURAL PROPERTIES AT V=30")
print("=" * 60)

structural = {}
for regime_name, gen_fn in REGIMES.items():
    props = defaultdict(list)
    for _ in range(50):
        W = gen_fn(30)
        
        # Sparsity
        props["sparsity"].append(np.mean(W == 0))
        
        # Eigenvalue concentration (how much mass in top eigenvalue)
        eigvals = np.sort(np.real(la.eigvals(W)))[::-1]
        total = np.abs(eigvals).sum()
        if total > 1e-10:
            props["top1_ratio"].append(np.abs(eigvals[0]) / total)
            props["top3_ratio"].append(np.sum(np.abs(eigvals[:3])) / total)
        else:
            props["top1_ratio"].append(0)
            props["top3_ratio"].append(0)
        
        # Effective rank (participation ratio)
        p = np.abs(eigvals) / total if total > 1e-10 else np.zeros_like(eigvals)
        p = p[p > 1e-15]
        if len(p) > 0:
            erank = 1.0 / np.sum(p**2)
        else:
            erank = 0
        props["effective_rank"].append(erank)
        
        # Variance of entries
        props["entry_var"].append(np.var(W))
        
        # Gini coefficient of entries
        flat = np.sort(W.ravel())
        n = len(flat)
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * flat) - (n + 1) * np.sum(flat)) / (n * np.sum(flat)) if np.sum(flat) > 0 else 0
        props["gini"].append(gini)
        
        # Compute γ+H
        props["gammaH"].append(compute_gamma(W) + compute_H(W))
    
    structural[regime_name] = {k: float(np.mean(v)) for k, v in props.items()}
    print(f"\n  {regime_name}:")
    print(f"    Sparsity:     {structural[regime_name]['sparsity']:.3f}")
    print(f"    Top-1 ratio:  {structural[regime_name]['top1_ratio']:.3f}")
    print(f"    Top-3 ratio:  {structural[regime_name]['top3_ratio']:.3f}")
    print(f"    Eff. rank:    {structural[regime_name]['effective_rank']:.1f}")
    print(f"    Entry var:    {structural[regime_name]['entry_var']:.4f}")
    print(f"    Gini:         {structural[regime_name]['gini']:.3f}")
    print(f"    Mean γ+H:     {structural[regime_name]['gammaH']:.4f}")

# ── Hypothesis testing ──────────────────────────────────────────────────

print("\n\n" + "=" * 60)
print("HYPOTHESIS TESTING")
print("=" * 60)

decreasing = [name for name, s in summary.items() if s["slope_gammaH"] < 0]
increasing = [name for name, s in summary.items() if s["slope_gammaH"] >= 0]

print(f"\nDECREASING slope regimes: {decreasing}")
print(f"INCREASING slope regimes: {increasing}")

# Check which structural properties distinguish decreasing from increasing
if decreasing and increasing:
    dec_struct = {k: np.mean([structural[r][k] for r in decreasing]) 
                  for k in structural[decreasing[0]].keys()}
    inc_struct = {k: np.mean([structural[r][k] for r in increasing]) 
                  for k in structural[increasing[0]].keys()}
    
    print("\n  Property averages:")
    print(f"  {'Property':<20} {'DECREASING':>12} {'INCREASING':>12} {'Δ':>10}")
    for k in dec_struct:
        d = dec_struct[k]
        i = inc_struct[k]
        delta = d - i
        marker = " <<<" if abs(delta) > 0.05 * max(abs(d), abs(i), 0.01) else ""
        print(f"  {k:<20} {d:>12.4f} {i:>12.4f} {delta:>+10.4f}{marker}")

# ── Save results ─────────────────────────────────────────────────────────

output = {
    "summary": summary,
    "structural": structural,
    "raw_data": {k: v for k, v in results.items()},
}

with open("/home/phoenix/.openclaw/workspace/experiments/study65_results.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to experiments/study65_results.json")

# ── Vary Hebbian parameters to find the critical point ──────────────────

print("\n\n" + "=" * 60)
print("HEBBIAN PARAMETER SWEEP (V=3..50)")
print("=" * 60)

# Test different learning rates and decay rates
hebbian_configs = [
    {"lr": 0.001, "decay": 0.001, "label": "lr=0.001"},
    {"lr": 0.005, "decay": 0.001, "label": "lr=0.005"},
    {"lr": 0.01,  "decay": 0.001, "label": "lr=0.01 (default)"},
    {"lr": 0.05,  "decay": 0.001, "label": "lr=0.05"},
    {"lr": 0.1,   "decay": 0.001, "label": "lr=0.1"},
    {"lr": 0.01,  "decay": 0.01,  "label": "decay=0.01"},
    {"lr": 0.01,  "decay": 0.1,   "label": "decay=0.1"},
]

for config in hebbian_configs:
    lr, decay = config["lr"], config["decay"]
    label = config["label"]
    data_points = []
    
    for V in V_RANGE:
        sums = []
        for _ in range(20):
            # Inline Hebbian generation with specific params
            n_steps = max(200, V * 20)
            W = np.random.uniform(0, 0.05, (V, V))
            W = (W + W.T) / 2
            for _ in range(n_steps):
                x = np.random.binomial(1, 0.3, V).astype(float)
                delta = lr * np.outer(x, x) - decay * W
                W += delta
                W = np.maximum(0, (W + W.T) / 2)
            if W.max() > 1e-10:
                W /= W.max()
            sums.append(compute_gamma(W) + compute_H(W))
        
        data_points.append({"V": V, "gammaH": np.mean(sums)})
    
    Vs = np.array([d["V"] for d in data_points])
    lnV = np.log(Vs)
    gammaH = np.array([d["gammaH"] for d in data_points])
    coeffs = np.polyfit(lnV, gammaH, 1)
    slope = coeffs[0]
    
    print(f"  {label:<25} slope: {slope:+.4f}  {'DECREASING' if slope < 0 else 'INCREASING'}")

# ── Test: what if we control effective rank? ────────────────────────────

print("\n\n" + "=" * 60)
print("EFFECTIVE RANK CONTROL")
print("=" * 60)

for target_rank_frac in [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
    data_points = []
    for V in V_RANGE:
        sums = []
        for _ in range(20):
            # Generate a matrix with controlled effective rank
            # Use rank-targeted construction
            rank = max(1, int(V * target_rank_frac))
            U = np.random.randn(V, rank)
            s = np.random.uniform(0.5, 1.5, rank)
            W = U @ np.diag(s) @ U.T
            W = np.maximum(0, (W + W.T) / 2)
            if W.max() > 1e-10:
                W /= W.max()
            sums.append(compute_gamma(W) + compute_H(W))
        
        data_points.append({"V": V, "gammaH": np.mean(sums)})
    
    Vs = np.array([d["V"] for d in data_points])
    lnV = np.log(Vs)
    gammaH = np.array([d["gammaH"] for d in data_points])
    coeffs = np.polyfit(lnV, gammaH, 1)
    slope = coeffs[0]
    
    print(f"  rank_frac={target_rank_frac:.1f} (rank≈{max(1,int(3*target_rank_frac))}..{int(50*target_rank_frac)})  slope: {slope:+.4f}  {'DECREASING' if slope < 0 else 'INCREASING'}")

print("\nDone.")
