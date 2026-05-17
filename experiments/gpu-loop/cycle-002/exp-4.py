#!/usr/bin/env python3
"""
EXP-4: Designing Coupling Matrices That Conserve
Can we engineer structured matrices with GOE-like eigenvalue statistics?
Approach: Take a structured matrix (Hebbian/Attention), project its eigenvalues
onto GOE spacing, then reconstruct.
"""
import numpy as np
import json

np.random.seed(789)
N = 50
n_trials = 30

def make_hebbian(N):
    patterns = np.random.randn(5, N)
    J = patterns.T @ patterns / 5
    np.fill_diagonal(J, 0)
    return (J + J.T) / 2

def make_attention(N):
    Q = np.random.randn(N, N//4)
    K = np.random.randn(N, N//4)
    scores = Q @ K.T / np.sqrt(N//4)
    J = np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)
    return (J + J.T) / 2

def make_random(N):
    J = np.random.randn(N, N)
    return (J + J.T) / (2 * np.sqrt(N))

def goe_eigenvalues(N, n_samples=1):
    """Generate eigenvalues from GOE ensemble"""
    evals_list = []
    for _ in range(n_samples):
        J = np.random.randn(N, N)
        J = (J + J.T) / (2 * np.sqrt(N))
        evals_list.append(np.sort(np.linalg.eigvalsh(J)))
    return evals_list

def project_to_goe_spacing(eigenvalues):
    """Project eigenvalues to have GOE-like spacing while preserving rank order and scale.
    
    Strategy: Sort eigenvalues, compute GOE-appropriate spacing pattern,
    redistribute eigenvalues to match GOE spacing.
    """
    sorted_evals = np.sort(eigenvalues)
    n = len(sorted_evals)
    
    # Generate GOE eigenvalue spacing pattern
    goe_evals = np.sort(np.linalg.eigvalsh((np.random.randn(n, n) + np.random.randn(n, n).T) / (2 * np.sqrt(n))))
    
    # Match the scale: preserve the eigenvalue range
    data_range = sorted_evals[-1] - sorted_evals[0]
    goe_range = goe_evals[-1] - goe_evals[0]
    if goe_range < 1e-12:
        return eigenvalues
    
    goe_scaled = (goe_evals - goe_evals[0]) / goe_range * data_range + sorted_evals[0]
    
    return goe_scaled

def reconstruct_matrix(original_J, new_eigenvalues):
    """Reconstruct matrix with new eigenvalues but original eigenvectors."""
    evals, evecs = np.linalg.eigh(original_J)
    return evecs @ np.diag(new_eigenvalues) @ evecs.T

def measure_conservation(J, n_rounds=80):
    """Measure γ+H CV"""
    evals = np.linalg.eigvalsh(J)
    abs_evals = np.sort(np.abs(evals))
    
    gh_values = []
    x = np.random.randn(N)
    for _ in range(n_rounds):
        x = J @ x
        norm = np.linalg.norm(x)
        if norm > 1e10 or norm < 1e-10:
            x = np.random.randn(N)
            continue
        x = x / norm
        gamma = abs_evals[-1] - abs_evals[-2] if len(abs_evals) > 1 else 0
        probs = abs_evals / (np.sum(abs_evals) + 1e-12)
        H = -np.sum(probs * np.log(probs + 1e-12))
        gh_values.append(gamma + H)
    
    mean = np.mean(gh_values)
    cv = np.std(gh_values) / (mean + 1e-12)
    return float(cv), float(mean)

def measure_goe_ks(evals):
    """KS statistic against Wigner surmise"""
    sorted_evals = np.sort(evals)
    spacings = np.diff(sorted_evals)
    mean_sp = np.mean(spacings)
    if mean_sp < 1e-12:
        return 1.0
    spacings = spacings / mean_sp
    
    # Empirical CDF
    n = len(spacings)
    s_sorted = np.sort(spacings)
    ecdf = np.arange(1, n+1) / n
    
    # GOE CDF (Wigner surmise)
    goe_cdf = 1 - np.exp(-np.pi * s_sorted**2 / 4)
    
    ks = np.max(np.abs(ecdf - goe_cdf))
    return float(ks)

# Test configurations
print("=" * 80)
print("EXP-4: Designing Coupling Matrices That Conserve")
print("=" * 80)

methods = [
    ('random_baseline', 'random', False),
    ('hebbian_original', 'hebbian', False),
    ('hebbian_goe_projected', 'hebbian', True),
    ('attention_original', 'attention', False),
    ('attention_goe_projected', 'attention', True),
]

results = {}
print(f"{'Method':25s} | {'CV':8s} | {'GOE_KS':8s} | {'Conserved':10s}")
print("-" * 70)

for name, arch, project in methods:
    cv_values = []
    goe_ks_values = []
    
    for _ in range(n_trials):
        if arch == 'random':
            J = make_random(N)
        elif arch == 'hebbian':
            J = make_hebbian(N)
        else:
            J = make_attention(N)
        
        if project:
            evals = np.linalg.eigvalsh(J)
            new_evals = project_to_goe_spacing(evals)
            J = reconstruct_matrix(J, new_evals)
        
        cv, mean_gh = measure_conservation(J)
        if not np.isnan(cv):
            cv_values.append(cv)
        
        evals = np.linalg.eigvalsh(J)
        goe_ks_values.append(measure_goe_ks(evals))
    
    mean_cv = np.mean(cv_values) if cv_values else float('nan')
    mean_goe = np.mean(goe_ks_values)
    conserved = "✓" if mean_cv < 0.05 else "✗"
    
    results[name] = {
        'mean_cv': float(mean_cv) if not np.isnan(mean_cv) else None,
        'mean_goe_ks': float(mean_goe),
        'n_valid': len(cv_values)
    }
    
    cv_str = f"{mean_cv:.4f}" if not np.isnan(mean_cv) else "NaN"
    print(f"{name:25s} | {cv_str:8s} | {mean_goe:8.4f} | {conserved:10s}")

# Additional test: random eigenvalue injection
print(f"\n{'='*70}")
print("HYBRID: Structured + Random Eigenvalue Fraction")
print(f"{'='*70}")

for mix_ratio in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
    cv_values = []
    for _ in range(20):
        J_struct = make_hebbian(N)
        J_rand = make_random(N)
        J = (1 - mix_ratio) * J_struct + mix_ratio * J_rand
        J = (J + J.T) / 2  # ensure symmetry
        cv, _ = measure_conservation(J)
        if not np.isnan(cv):
            cv_values.append(cv)
    
    mean_cv = np.mean(cv_values) if cv_values else float('nan')
    conserved = "✓" if mean_cv < 0.05 else "✗"
    cv_str = f"{mean_cv:.4f}" if not np.isnan(mean_cv) else "NaN"
    print(f"  mix_ratio={mix_ratio:.1f} | CV={cv_str} | {conserved}")
    results[f'hebbian_mix_{mix_ratio:.1f}'] = {'mix_ratio': float(mix_ratio), 'mean_cv': float(mean_cv) if not np.isnan(mean_cv) else None}

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-002/exp4_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to exp4_results.json")
