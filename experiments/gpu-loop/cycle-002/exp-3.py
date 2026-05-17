#!/usr/bin/env python3
"""
EXP-3: Asymmetric Coupling as Correlation Breaker
Test whether asymmetry pushes eigenvalue statistics toward GOE.
Key insight: symmetric matrices have J_ij = J_ji (correlated).
Asymmetric coupling breaks this, potentially improving GOE-ness.
"""
import numpy as np
import json

np.random.seed(456)
N = 50
n_samples = 200

def make_symmetric_random(N):
    """Standard Wigner (symmetric random)"""
    J = np.random.randn(N, N)
    return (J + J.T) / (2 * np.sqrt(N))

def make_asymmetric_random(N, asymmetry=0.5):
    """Random matrix with controlled asymmetry.
    asymmetry=0 → fully symmetric
    asymmetry=1 → fully independent upper/lower triangles
    """
    J_upper = np.random.randn(N, N) / np.sqrt(N)
    J_lower = np.random.randn(N, N) / np.sqrt(N)
    J = asymmetry * J_lower + (1 - asymmetry) * J_upper
    # Make upper triangle from J_upper, lower from J
    mask_upper = np.triu(np.ones((N, N)), k=1)
    mask_lower = np.tril(np.ones((N, N)), k=-1)
    J_final = mask_upper * J_upper + mask_lower * J
    np.fill_diagonal(J_final, np.random.randn(N) / np.sqrt(N))
    return J_final

def make_precision_asymmetric(N, high_bits=64, low_bits=4):
    """Simulate precision-dependent asymmetry.
    A→B: quantized to low_bits (lossy)
    B→A: kept at high_bits (lossless)
    """
    J = np.random.randn(N, N) / np.sqrt(N)
    # Upper triangle: high precision (near original)
    # Lower triangle: quantized (lossy)
    levels = 2**low_bits
    J_lower = np.round(J * levels) / levels
    
    mask_upper = np.triu(np.ones((N, N)), k=1)
    mask_lower = np.tril(np.ones((N, N)), k=-1)
    J_final = mask_upper * J + mask_lower * J_lower
    np.fill_diagonal(J_final, np.random.randn(N) / np.sqrt(N))
    return J_final

def measure_entry_correlation(J):
    """Correlation between upper and lower triangle entries"""
    upper = J[np.triu_indices_from(J, k=1)]
    lower = J[np.tril_indices_from(J, k=-1)]
    if len(upper) == 0:
        return 0.0
    # Pair J[i,j] with J[j,i] — same positions reflected
    upper_paired = J[np.triu_indices_from(J, k=1)]
    lower_paired = J.T[np.triu_indices_from(J, k=1)]  # J[j,i] for each J[i,j]
    corr = np.corrcoef(upper_paired, lower_paired)[0, 1]
    return float(corr)

def measure_goe_arity(evals_real):
    """How GOE-like are the eigenvalue spacings? KS distance to Wigner surmise."""
    sorted_evals = np.sort(evals_real)
    spacings = np.diff(sorted_evals)
    mean_sp = np.mean(spacings)
    if mean_sp < 1e-12:
        return 1.0
    spacings = spacings / mean_sp
    
    # Compare to Wigner surmise CDF
    s_bins = np.linspace(0, 4, 100)
    goe_pdf = (np.pi / 2) * s_bins * np.exp(-np.pi * s_bins**2 / 4)
    goe_cdf = np.cumsum(goe_pdf) / np.sum(goe_pdf)
    data_cdf = np.searchsorted(s_bins, spacings) / len(s_bins)
    
    # Simple metric: fraction of spacings in [0.5, 1.5] (GOE peak region)
    goe_peak = np.mean((spacings > 0.5) & (spacings < 1.5))
    return float(goe_peak)

def measure_conservation_from_dynamics(J, n_rounds=100):
    """Measure γ+H CV over dynamics rounds."""
    # Use eigenvalues directly for γ+H
    evals = np.linalg.eigvals(J)
    abs_evals = np.sort(np.abs(evals))
    
    gamma_values = []
    H_values = []
    x = np.random.randn(N)
    
    for _ in range(n_rounds):
        x = J @ x
        norm = np.linalg.norm(x)
        if norm > 1e10 or norm < 1e-10:
            x = x / max(norm, 1e-10)
        else:
            x = x / norm
        
        gamma = abs_evals[-1] - abs_evals[-2]
        probs = abs_evals / (np.sum(abs_evals) + 1e-12)
        H = -np.sum(probs * np.log(probs + 1e-12))
        gamma_values.append(gamma)
        H_values.append(H)
    
    gh = np.array(gamma_values) + np.array(H_values)
    mean_gh = np.mean(gh)
    cv = np.std(gh) / (mean_gh + 1e-12)
    return float(cv), float(mean_gh)

# Test configurations
configs = [
    ('symmetric_random', lambda: make_symmetric_random(N)),
    ('asym_0.2', lambda: make_asymmetric_random(N, 0.2)),
    ('asym_0.5', lambda: make_asymmetric_random(N, 0.5)),
    ('asym_0.8', lambda: make_asymmetric_random(N, 0.8)),
    ('asym_1.0', lambda: make_asymmetric_random(N, 1.0)),
    ('precision_64_8', lambda: make_precision_asymmetric(N, 64, 8)),
    ('precision_64_4', lambda: make_precision_asymmetric(N, 64, 4)),
    ('precision_64_2', lambda: make_precision_asymmetric(N, 64, 2)),
]

results = {}
print("=" * 80)
print("EXP-3: Asymmetric Coupling as Correlation Breaker")
print("=" * 80)
print(f"{'Config':20s} | {'Entry Corr':10s} | {'GOE-peak':10s} | {'γ+H CV':10s} | {'Conserved':10s}")
print("-" * 80)

for name, make_fn in configs:
    entry_corrs = []
    goe_scores = []
    cv_values = []
    
    for _ in range(n_samples):
        J = make_fn()
        entry_corrs.append(measure_entry_correlation(J))
        
        evals = np.linalg.eigvals(J)
        goe_scores.append(measure_goe_arity(np.real(evals)))
        
        cv, mean_gh = measure_conservation_from_dynamics(J, 50)
        if not np.isnan(cv) and cv < 1.0:
            cv_values.append(cv)
    
    mean_corr = np.mean(entry_corrs)
    mean_goe = np.mean(goe_scores)
    mean_cv = np.mean(cv_values) if cv_values else float('nan')
    conserved = "✓" if mean_cv < 0.05 else "✗"
    
    results[name] = {
        'entry_correlation': float(mean_corr),
        'goe_peak_score': float(mean_goe),
        'mean_cv': float(mean_cv) if not np.isnan(mean_cv) else None,
        'n_valid_trials': len(cv_values)
    }
    
    cv_str = f"{mean_cv:.4f}" if not np.isnan(mean_cv) else "NaN"
    print(f"{name:20s} | {mean_corr:10.4f} | {mean_goe:10.4f} | {cv_str:10s} | {conserved:10s}")

# Key analysis: correlation between entry correlation and conservation
print(f"\n{'='*80}")
print("CORRELATION ANALYSIS")
print(f"{'='*80}")
corrs = [results[k]['entry_correlation'] for k in results if results[k]['mean_cv'] is not None]
cvs = [results[k]['mean_cv'] for k in results if results[k]['mean_cv'] is not None]
goe = [results[k]['goe_peak_score'] for k in results if results[k]['mean_cv'] is not None]

if len(corrs) > 2:
    corr_cv = np.corrcoef(corrs, cvs)[0, 1]
    corr_goe_cv = np.corrcoef(goe, cvs)[0, 1]
    print(f"  Entry correlation vs CV: r = {corr_cv:.4f}")
    print(f"  GOE-peak score vs CV: r = {corr_goe_cv:.4f}")
    print(f"  → {'Supports' if corr_cv > 0.3 else 'Does not support'} correlation-breaking hypothesis")

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-002/exp3_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to exp3_results.json")
