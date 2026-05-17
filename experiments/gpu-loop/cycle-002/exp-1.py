#!/usr/bin/env python3
"""
EXP-1: Eigenvalue Spacing Distribution — The Smoking Gun
Tests whether random/Hebbian/Attention coupling produce GOE vs Poisson eigenvalue statistics.
Wigner surmise: P(s) = (π/2)·s·exp(-π·s²/4) for GOE
Poisson: P(s) = exp(-s)
If conservation correlates with GOE spacing, we've found the mechanism.
"""
import numpy as np
import json

np.random.seed(42)
N = 50  # Matrix size
n_samples = 200

def wigner_surmise(s):
    """GOE eigenvalue spacing distribution (Wigner surmise)"""
    return (np.pi / 2) * s * np.exp(-np.pi * s**2 / 4)

def poisson_spacing(s):
    """Poisson (uncorrelated) eigenvalue spacing"""
    return np.exp(-s)

def get_unfolded_spacings(eigenvalues):
    """Get normalized eigenvalue spacings (unfolded)"""
    sorted_evals = np.sort(np.real(eigenvalues))
    spacings = np.diff(sorted_evals)
    mean_spacing = np.mean(spacings)
    if mean_spacing == 0:
        return np.array([])
    return spacings / mean_spacing

def compute_spacing_stats(spacings):
    """Compute statistics of spacing distribution"""
    if len(spacings) == 0:
        return {'mean': 0, 'std': 0, 'goe_ks': 1.0, 'poisson_ks': 1.0, 'brody_beta': 0}
    # KS test against GOE
    s_bins = np.linspace(0, 4, 50)
    hist, _ = np.histogram(spacings, bins=s_bins, density=True)
    centers = (s_bins[:-1] + s_bins[1:]) / 2
    goe_theory = wigner_surmise(centers)
    poisson_theory = poisson_spacing(centers)
    # Normalize
    goe_theory /= np.trapz(goe_theory, centers)
    poisson_theory /= np.trapz(poisson_theory, centers)
    
    goe_cdf = np.cumsum(goe_theory) * (centers[1] - centers[0])
    data_cdf = np.cumsum(hist) * (centers[1] - centers[0])
    poisson_cdf = np.cumsum(poisson_theory) * (centers[1] - centers[0])
    
    goe_ks = np.max(np.abs(data_cdf - goe_cdf))
    poisson_ks = np.max(np.abs(data_cdf - poisson_cdf))
    
    # Brody parameter (beta): ratio of mean to expected GOE mean
    # GOE mean spacing ~ 1.0 by construction
    brody_beta = np.mean(spacings) / 1.0  # normalized, so ~1 for GOE
    
    return {
        'mean': float(np.mean(spacings)),
        'std': float(np.std(spacings)),
        'goe_ks': float(goe_ks),
        'poisson_ks': float(poisson_ks),
        'brody_beta': float(brody_beta),
        'n_spacings': len(spacings),
        'fraction_below_0.5': float(np.mean(spacings < 0.5))
    }

def make_hebbian_matrix(N):
    """Hebbian coupling: J_ij = v_i · v_j for random patterns"""
    n_patterns = 5
    patterns = np.random.randn(n_patterns, N)
    J = patterns.T @ patterns / n_patterns
    np.fill_diagonal(J, 0)
    return (J + J.T) / 2  # symmetrize

def make_attention_matrix(N):
    """Attention-like coupling: softmax of query-key products"""
    Q = np.random.randn(N, N//4)
    K = np.random.randn(N, N//4)
    scores = Q @ K.T / np.sqrt(N//4)
    J = np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)
    return (J + J.T) / 2  # symmetrize

def make_random_matrix(N):
    """Wigner random matrix"""
    J = np.random.randn(N, N)
    return (J + J.T) / (2 * np.sqrt(N))

# Collect spacings for each architecture
results = {}

for arch_name, matrix_fn in [('random', make_random_matrix), 
                                ('hebbian', make_hebbian_matrix),
                                ('attention', make_attention_matrix)]:
    all_spacings = []
    for _ in range(n_samples):
        J = matrix_fn(N)
        evals = np.linalg.eigvalsh(J)
        spacings = get_unfolded_spacings(evals)
        all_spacings.extend(spacings)
    
    all_spacings = np.array(all_spacings)
    stats = compute_spacing_stats(all_spacings)
    
    # Also compute γ+H conservation for 100 rounds
    cv_values = []
    for _ in range(50):
        J = matrix_fn(N)
        evals = np.linalg.eigvalsh(J)
        gamma = np.max(np.abs(evals)) - np.sort(np.abs(evals))[-2] if len(evals) > 1 else 0
        H = -np.sum(np.abs(evals) / np.sum(np.abs(evals)) * np.log(np.abs(evals) / np.sum(np.abs(evals)) + 1e-12))
        cv_values.append(gamma + H)
    
    stats['gamma_H_mean'] = float(np.mean(cv_values))
    stats['gamma_H_cv'] = float(np.std(cv_values) / (np.mean(cv_values) + 1e-12))
    stats['architecture'] = arch_name
    results[arch_name] = stats

# Print results
print("=" * 70)
print("EXP-1: Eigenvalue Spacing Distribution Analysis")
print("=" * 70)
print(f"Matrix size N={N}, {n_samples} samples per architecture\n")

for arch, stats in results.items():
    goe_label = "GOE" if stats['goe_ks'] < stats['poisson_ks'] else "POISSON"
    print(f"{arch.upper():12s} | KS(GOE)={stats['goe_ks']:.4f} | KS(Poisson)={stats['poisson_ks']:.4f} | → {goe_label}")
    print(f"             | spacing mean={stats['mean']:.4f} std={stats['std']:.4f} | frac<0.5={stats['fraction_below_0.5']:.4f}")
    print(f"             | γ+H mean={stats['gamma_H_mean']:.4f} CV={stats['gamma_H_cv']:.4f}")
    print()

# Correlation: GOE-ness vs conservation
print("CORRELATION: GOE-ness (1 - KS_GOE) vs Conservation (1/CV)")
for arch, stats in results.items():
    goe_score = 1 - stats['goe_ks']
    cons_score = 1 / (stats['gamma_H_cv'] + 0.01)
    print(f"  {arch}: GOE-score={goe_score:.4f}, Conservation-score={cons_score:.2f}")

# Save
with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-002/exp1_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to exp1_results.json")
