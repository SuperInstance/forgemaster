"""
EXPERIMENT 1: Lipschitz constant L_I
For 100 pairs (x,y), compute |I(x)-I(y)| and check if |I(x)-I(y)| ≤ L_I · ||x-y||
I(x) = x^T P x where P is the Lyapunov matrix (positive definite).
For a quadratic I(x) = x^T P x, the Lipschitz constant is bounded by 2·||P||·R
where R is the max norm in the domain.
"""
import numpy as np
import json

np.random.seed(42)

n = 4  # state dimension
# Generate a stable system matrix A (spectral radius < 1)
A = np.random.randn(n, n) * 0.3
eigvals = np.linalg.eigvals(A)
sr = max(abs(eigvals))
if sr >= 1:
    A = A / (sr + 0.1)

# Lyapunov equation: P = A^T P A + I  =>  P = I + A^T P A
# Solve iteratively
P = np.eye(n)
for _ in range(200):
    P = A.T @ P @ A + np.eye(n)

# Verify P is positive definite
eigP = np.linalg.eigvalsh(P)
assert min(eigP) > 0, "P not positive definite"

def I(x):
    return x.T @ P @ x

# Domain radius
R = 5.0
N_pairs = 1000

ratios = []
violations = 0
details = []

for _ in range(N_pairs):
    x = np.random.randn(n) * R
    y = np.random.randn(n) * R
    
    diff_I = abs(I(x) - I(y))
    diff_norm = np.linalg.norm(x - y)
    
    if diff_norm < 1e-12:
        continue
    
    ratio = diff_I / diff_norm
    ratios.append(ratio)
    
    if diff_I > 0:
        details.append({
            'diff_I': float(diff_I),
            'diff_norm': float(diff_norm),
            'ratio': float(ratio)
        })

empirical_L = max(ratios)
mean_ratio = np.mean(ratios)
median_ratio = np.median(ratios)

# Theoretical bound: |I(x)-I(y)| = |x^T P x - y^T P y|
# = |(x-y)^T P (x+y)| ≤ ||P|| · ||x-y|| · ||x+y||
# ≤ ||P|| · ||x-y|| · 2R (since ||x||,||y|| ≤ R)
# So L_I_theory = 2 * ||P||_2 * R = 2 * max(svd(P)) * R
P_norm = np.linalg.norm(P, 2)
L_theory = 2 * P_norm * (2 * R)  # ||x+y|| ≤ 2R

results = {
    'experiment': 'Lipschitz constant L_I',
    'n': n,
    'domain_radius': R,
    'P_spectral_norm': float(P_norm),
    'P_eigenvalues': [float(e) for e in eigP],
    'N_pairs': N_pairs,
    'empirical_L_I': float(empirical_L),
    'mean_ratio': float(mean_ratio),
    'median_ratio': float(median_ratio),
    'theoretical_L_I': float(L_theory),
    'bound_holds': bool(empirical_L <= L_theory + 1e-10),
    'tightness_ratio': float(empirical_L / L_theory),
    'sample_ratios_percentiles': {
        'p50': float(np.percentile(ratios, 50)),
        'p90': float(np.percentile(ratios, 90)),
        'p95': float(np.percentile(ratios, 95)),
        'p99': float(np.percentile(ratios, 99)),
        'max': float(max(ratios))
    }
}

print(json.dumps(results, indent=2))

# Save
with open('experiment1_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print(f"EXPERIMENT 1 SUMMARY")
print(f"{'='*60}")
print(f"Empirical L_I: {empirical_L:.6f}")
print(f"Theoretical bound: {L_theory:.6f}")
print(f"Bound holds: {empirical_L <= L_theory + 1e-10}")
print(f"Tightness (empirical/theoretical): {empirical_L/L_theory:.4f}")
