"""
EXPERIMENT 2: Koopman eigenvalue bound
For 100 coupling matrices, compute:
  - |1-λ_Koopman| (eigenvalue deviation from 1)
  - ||[D,C]|| (commutator norm)
Check if |1-λ| ≤ C₁ · ||[D,C]|| holds for some constant C₁.

Setup: D is a diagonal matrix (decoupled dynamics), C is a coupling perturbation.
The Koopman operator K acts on observables. For the linear case K[f](x) = f(Ax).
Eigenvalues of K (on polynomial subspace) relate to eigenvalues of A.
"""
import numpy as np
import json

np.random.seed(123)

n = 4  # state dimension
N_trials = 1000

results_list = []
max_ratio = 0
min_ratio = float('inf')
violations = 0

for trial in range(N_trials):
    # D: diagonal stable matrix (decoupled dynamics)
    d_eigs = np.random.uniform(-0.9, 0.9, n)
    D = np.diag(d_eigs)
    
    # C: coupling perturbation (small)
    coupling_strength = np.random.uniform(0.01, 0.3)
    C = np.random.randn(n, n) * coupling_strength
    # Make C off-diagonal (coupling connects different states)
    C = C * (1 - np.eye(n))
    
    # Full system: A = D + C
    A = D + C
    
    # Commutator [D, C] = DC - CD
    commutator = D @ C - C @ D
    comm_norm = np.linalg.norm(commutator, 2)
    
    # Koopman eigenvalues (for linear system, these are related to eigenvalues of A)
    # For quadratic observables I(x) = x^T P x, Koopman acts as:
    # K[I](x) = I(Ax) = x^T A^T P A x
    # So K|_quadratic = A^T ⊗ A^T acting on vec(P)
    # Eigenvalue of K on this subspace: products of eigenvalues of A
    
    A_eigvals = np.linalg.eigvals(A)
    
    # Koopman eigenvalues for degree-2 observables: λ_i * λ_j for i,j
    koopman_eigs = []
    for i in range(n):
        for j in range(i, n):
            koopman_eigs.append(A_eigvals[i] * A_eigvals[j])
    
    # The "ideal" eigenvalue is 1 (for the invariant). Check deviation from 1
    # for the eigenvalue closest to 1
    max_deviation = 0
    for ke in koopman_eigs:
        dev = abs(1 - abs(ke))  # deviation of |λ| from 1
        max_deviation = max(max_deviation, dev)
    
    # Actually, let's look at the eigenvalue closest to 1
    deviations = [abs(1 - abs(ke)) for ke in koopman_eigs]
    min_deviation = min(deviations)
    
    # Check bound: |1-λ| ≤ C₁ · ||[D,C]||
    if comm_norm > 1e-10:
        ratio_min = min_deviation / comm_norm
        ratio_max = max_deviation / comm_norm
        
        max_ratio = max(max_ratio, ratio_max)
        min_ratio = min(min_ratio, ratio_min)
        
        results_list.append({
            'trial': trial,
            'comm_norm': float(comm_norm),
            'coupling_strength': float(coupling_strength),
            'min_eigval_deviation': float(min_deviation),
            'max_eigval_deviation': float(max_deviation),
            'ratio_min': float(ratio_min),
            'ratio_max': float(ratio_max)
        })

# Analyze
ratios_max = [r['ratio_max'] for r in results_list]
ratios_min = [r['ratio_min'] for r in results_list]

empirical_C1_upper = np.percentile(ratios_max, 99)
empirical_C1_median = np.median(ratios_max)

# Check if bound holds with empirical C1
violations_upper = sum(1 for r in ratios_max if r > empirical_C1_upper * 1.1)

results = {
    'experiment': 'Koopman eigenvalue bound',
    'n': n,
    'N_trials': N_trials,
    'empirical_C1_99th_percentile': float(empirical_C1_upper),
    'empirical_C1_median': float(empirical_C1_median),
    'empirical_C1_max': float(max(ratios_max)),
    'empirical_C1_min': float(min(ratios_max)),
    'bound_summary': f'|1-λ| ≤ {empirical_C1_upper:.4f} · ||[D,C]|| (99th percentile)',
    'ratios_percentiles': {
        'p50': float(np.percentile(ratios_max, 50)),
        'p90': float(np.percentile(ratios_max, 90)),
        'p95': float(np.percentile(ratios_max, 95)),
        'p99': float(np.percentile(ratios_max, 99)),
        'max': float(max(ratios_max))
    }
}

print(json.dumps(results, indent=2))

with open('experiment2_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print(f"EXPERIMENT 2 SUMMARY")
print(f"{'='*60}")
print(f"Empirical C₁ (99th percentile): {empirical_C1_upper:.6f}")
print(f"Empirical C₁ (max): {max(ratios_max):.6f}")
print(f"Bound: |1-λ| ≤ {empirical_C1_upper:.4f} · ||[D,C]||")
