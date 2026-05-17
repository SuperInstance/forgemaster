"""Supplementary analysis: γ-H correlation and cross-instance variation."""

import numpy as np
from scipy import linalg
import json
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

N = 20
n_rounds = 200
n_samples = 50

def random_coupling(N, seed=None):
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((N, N))
    return (A + A.T) / (2 * np.sqrt(N))

def hebbian_coupling(N, n_patterns=None, seed=None):
    rng = np.random.default_rng(seed)
    if n_patterns is None:
        n_patterns = max(1, N // 4)
    patterns = rng.choice([-1, 1], size=(n_patterns, N))
    J = patterns.T @ patterns / N
    np.fill_diagonal(J, 0)
    return J

def attention_coupling(N, d_head=None, seed=None):
    rng = np.random.default_rng(seed)
    if d_head is None:
        d_head = max(1, N // 4)
    Q = rng.standard_normal((N, d_head)) / np.sqrt(d_head)
    K = rng.standard_normal((N, d_head)) / np.sqrt(d_head)
    scores = Q @ K.T / np.sqrt(d_head)
    scores_max = scores.max(axis=1, keepdims=True)
    exp_scores = np.exp(scores - scores_max)
    J = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    return J

def evolve_detailed(J, x0, n_rounds=200):
    """Return γ, H, γ+H trajectories."""
    x = x0.copy().astype(np.float64)
    x = x / np.linalg.norm(x)
    eigenvalues, eigenvectors = linalg.eigh(J)
    v1 = eigenvectors[:, -1]
    
    gammas, entropies, gh_values = [], [], []
    for r in range(n_rounds):
        x = J @ x
        norm = np.linalg.norm(x)
        if norm < 1e-15 or np.any(np.isnan(x)):
            break
        x = x / norm
        
        overlap = np.abs(np.dot(x, v1))
        gamma = 1.0 - overlap**2
        p = x**2
        p = p[p > 1e-15]
        H = -np.sum(p * np.log(p))
        
        gammas.append(gamma)
        entropies.append(H)
        gh_values.append(gamma + H)
    
    return np.array(gammas), np.array(entropies), np.array(gh_values)

print("=" * 70)
print("Supplementary Analysis")
print("=" * 70)

# 1. Within-instance: γ-H correlation (should be -1 for perfect conservation)
print("\n--- Within-Instance: γ vs H Correlation ---")
for arch_name, gen_func in [('random', lambda s: random_coupling(N, seed=s)),
                              ('hebbian', lambda s: hebbian_coupling(N, seed=s)),
                              ('attention', lambda s: attention_coupling(N, seed=s))]:
    corr_list = []
    for sample in range(20):
        J = gen_func(sample * 100 + 42)
        x0 = np.random.default_rng(sample * 100 + 99).standard_normal(N)
        gammas, entropies, gh_vals = evolve_detailed(J, x0, n_rounds=200)
        if len(gammas) < 50:
            continue
        # Use first 100 rounds (transient)
        r = np.corrcoef(gammas[:100], entropies[:100])[0, 1]
        corr_list.append(r)
    
    print(f"  {arch_name}: γ-H correlation = {np.mean(corr_list):.4f} ± {np.std(corr_list):.4f}")

# 2. Cross-instance: C value variation
print("\n--- Cross-Instance: C(=γ+H) Variation ---")
for arch_name, gen_func in [('random', lambda s: random_coupling(N, seed=s)),
                              ('hebbian', lambda s: hebbian_coupling(N, seed=s)),
                              ('attention', lambda s: attention_coupling(N, seed=s))]:
    c_values = []
    for sample in range(50):
        J = gen_func(sample * 100 + 42)
        x0 = np.random.default_rng(sample * 100 + 99).standard_normal(N)
        _, _, gh_vals = evolve_detailed(J, x0, n_rounds=200)
        if len(gh_vals) < 50:
            continue
        # Use mean of last 100 rounds as C estimate
        c_values.append(np.mean(gh_vals[-100:]))
    
    c_arr = np.array(c_values)
    cv_cross = np.std(c_arr) / np.abs(np.mean(c_arr))
    print(f"  {arch_name}: C = {np.mean(c_arr):.4f} ± {np.std(c_arr):.4f}, cross-instance CV = {cv_cross:.4f}")

# 3. Trajectory inspection (first few rounds)
print("\n--- Trajectory Sample (first 20 rounds) ---")
for arch_name, gen_func in [('random', lambda: random_coupling(N, seed=42)),
                              ('hebbian', lambda: hebbian_coupling(N, seed=42)),
                              ('attention', lambda: attention_coupling(N, seed=42))]:
    J = gen_func()
    x0 = np.random.default_rng(99).standard_normal(N)
    gammas, entropies, gh_vals = evolve_detailed(J, x0, n_rounds=200)
    print(f"\n  {arch_name} (γ, H, γ+H):")
    for i in [0, 1, 2, 5, 10, 20, 50, 100, 150, 199]:
        if i < len(gammas):
            print(f"    round {i:3d}: γ={gammas[i]:.6f}, H={entropies[i]:.6f}, γ+H={gh_vals[i]:.6f}")

# 4. Convergence speed to top eigenvector
print("\n--- Convergence Speed (rounds to γ < 0.01) ---")
for arch_name, gen_func in [('random', lambda s: random_coupling(N, seed=s)),
                              ('hebbian', lambda s: hebbian_coupling(N, seed=s)),
                              ('attention', lambda s: attention_coupling(N, seed=s))]:
    conv_rounds = []
    for sample in range(30):
        J = gen_func(sample * 100 + 42)
        x0 = np.random.default_rng(sample * 100 + 99).standard_normal(N)
        gammas, _, _ = evolve_detailed(J, x0, n_rounds=200)
        # Find first round where gamma < 0.01
        below = np.where(gammas < 0.01)[0]
        if len(below) > 0:
            conv_rounds.append(below[0])
        else:
            conv_rounds.append(200)
    print(f"  {arch_name}: convergence round = {np.mean(conv_rounds):.1f} ± {np.std(conv_rounds):.1f}")

print("\nDone.")
