#!/usr/bin/env python3
"""
TRACE-CONSERVATION HYPOTHESIS TEST — The Smoking Gun

Hypothesis: γ+H conservation is DERIVED from Tr(C) conservation + Wigner semicircle eigenvalue density.

Test Plan:
  1. Generate GOE matrices with fixed trace → check if γ+H is a deterministic function of Tr(C)
  2. Vary trace → check if γ+H tracks perfectly
  3. Compare GOE vs structured (Hebbian) → does the relationship break?
  4. Load cycle-000 data → check Tr(C) conservation on actual experimental data
  5. If Tr(C) explains everything, compute the analytical γ+H = f(Tr(C)) for GOE matrices
"""
import numpy as np
from scipy.linalg import eigvalsh
import json, os, sys
from pathlib import Path

np.random.seed(42)
BASE = Path(__file__).parent.parent  # gpu-loop/

# ─── Utility Functions ───────────────────────────────────────────────────────

def spectral_entropy(eigs):
    """Spectral entropy H = -Σ p_i ln(p_i) where p_i = λ_i / Σλ_j"""
    eigs = np.sort(np.abs(eigs))[::-1]
    total = eigs.sum()
    if total < 1e-15:
        return 0.0
    probs = eigs / total
    probs = probs[probs > 1e-15]
    return float(-np.sum(probs * np.log(probs)))

def spectral_gap(eigs):
    """γ = λ_1 - λ_2 (largest eigenvalue gap)"""
    eigs = np.sort(np.abs(eigs))[::-1]
    if len(eigs) < 2:
        return float(eigs[0]) if len(eigs) == 1 else 0.0
    return float(eigs[0] - eigs[1])

def compute_gamma_H(C):
    eigs = eigvalsh(C)
    return spectral_gap(eigs), spectral_entropy(eigs)

def normalize_trace(C, target_trace):
    """Rescale matrix to have exact target trace."""
    current = np.trace(C)
    if abs(current) < 1e-15:
        return C
    # Rescale off-diagonal to achieve target trace while keeping diag=1
    diag_sum = np.trace(C)
    # Actually just rescale the whole matrix
    factor = target_trace / current
    return C * factor

def make_goe(n, sigma=1.0):
    """Generate GOE random matrix."""
    M = np.random.randn(n, n) * sigma
    return (M + M.T) / (2 * np.sqrt(n))

def make_goe_fixed_trace(n, target_trace, sigma=1.0):
    """Generate GOE matrix then rescale to exact trace."""
    M = make_goe(n, sigma)
    return normalize_trace(M, target_trace)

def make_hebbian(n, patterns=5, noise_scale=0.1):
    """Generate Hebbian coupling matrix from stored patterns."""
    patterns_vecs = np.random.randn(n, patterns)
    C = patterns_vecs @ patterns_vecs.T / patterns
    C = C + np.eye(n)  # add self-coupling
    return C

def make_hebbian_fixed_trace(n, target_trace, patterns=5):
    C = make_hebbian(n, patterns)
    return normalize_trace(C, target_trace)

def make_attention(n, noise_scale=0.1):
    """Generate attention-like coupling matrix."""
    Q = np.random.randn(n, n) * 0.5
    K = np.random.randn(n, n) * 0.5
    scores = Q @ K.T / np.sqrt(n)
    # Softmax-like normalization per row
    scores_exp = np.exp(scores - scores.max(axis=1, keepdims=True))
    C = scores_exp / scores_exp.sum(axis=1, keepdims=True)
    C = (C + C.T) / 2  # symmetrize
    np.fill_diagonal(C, 1.0)
    return C

def make_attention_fixed_trace(n, target_trace):
    C = make_attention(n)
    return normalize_trace(C, target_trace)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Is γ+H a deterministic function of Tr(C) for GOE?
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("TEST 1: Is γ+H deterministic given Tr(C) for GOE matrices?")
print("=" * 70)

results = {}
for N in [5, 10, 20]:
    n_samples = 5000
    target_traces = [1.0, 2.0, 5.0, 10.0]
    
    for tr in target_traces:
        gammas, Hs, gh_sums, traces = [], [], [], []
        for _ in range(n_samples):
            C = make_goe_fixed_trace(N, tr)
            tr_actual = np.trace(C)
            g, h = compute_gamma_H(C)
            gammas.append(g)
            Hs.append(h)
            gh_sums.append(g + h)
            traces.append(tr_actual)
        
        gh = np.array(gh_sums)
        cv = np.std(gh) / np.mean(gh) if np.mean(gh) > 0 else float('inf')
        
        key = f"GOE_N={N}_Tr={tr}"
        results[key] = {
            'type': 'GOE',
            'N': N,
            'target_trace': tr,
            'n_samples': n_samples,
            'mean_tr': np.mean(traces),
            'std_tr': np.std(traces),
            'mean_gh': np.mean(gh),
            'std_gh': np.std(gh),
            'cv_gh': cv,
            'mean_gamma': np.mean(gammas),
            'std_gamma': np.std(gammas),
            'mean_H': np.mean(Hs),
            'std_H': np.std(Hs),
            'gamma_H_correlation': float(np.corrcoef(gammas, Hs)[0, 1]),
        }
        print(f"  {key}: γ+H = {np.mean(gh):.6f} ± {np.std(gh):.6f} (CV={cv:.6f})")
        print(f"    γ = {np.mean(gammas):.6f} ± {np.std(gammas):.6f}, H = {np.mean(Hs):.6f} ± {np.std(Hs):.6f}")
        print(f"    γ-H correlation: {results[key]['gamma_H_correlation']:.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Vary Tr(C) continuously — does γ+H track perfectly?
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 2: γ+H vs Tr(C) — continuous trace sweep")
print("=" * 70)

N = 10
n_samples = 2000
trace_values = np.linspace(0.5, 20.0, 40)

gh_vs_trace = []
for tr in trace_values:
    gh_samples = []
    for _ in range(n_samples):
        C = make_goe_fixed_trace(N, tr)
        g, h = compute_gamma_H(C)
        gh_samples.append(g + h)
    mean_gh = np.mean(gh_samples)
    std_gh = np.std(gh_samples)
    gh_vs_trace.append((tr, mean_gh, std_gh))
    print(f"  Tr={tr:6.2f}: γ+H = {mean_gh:.6f} ± {std_gh:.6f}")

# Fit: is γ+H = f(Tr(C)) a clean function?
tr_arr = np.array([x[0] for x in gh_vs_trace])
gh_arr = np.array([x[1] for x in gh_vs_trace])
std_arr = np.array([x[2] for x in gh_vs_trace])

# Try polynomial fits
from numpy.polynomial import polynomial as P
for deg in [1, 2, 3]:
    coeffs = np.polyfit(tr_arr, gh_arr, deg)
    fitted = np.polyval(coeffs, tr_arr)
    residuals = gh_arr - fitted
    # Weighted R² accounting for within-point variance
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((gh_arr - np.mean(gh_arr))**2)
    r2 = 1 - ss_res / ss_tot
    # Check if between-point variance >> within-point variance
    between_var = np.var(gh_arr)
    within_var = np.mean(std_arr**2)
    print(f"\n  Poly deg={deg}: R²={r2:.8f}, coeffs={coeffs}")
    print(f"    Between-point variance: {between_var:.6f}")
    print(f"    Within-point variance:  {within_var:.6f}")
    print(f"    Ratio (between/within): {between_var/within_var:.1f}x")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: GOE vs Hebbian vs Attention — does trace-fixing conserve for all?
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 3: GOE vs Hebbian vs Attention — fixed trace conservation")
print("=" * 70)

N = 10
n_samples = 3000
target_trace = 5.0

for name, gen_fn in [
    ("GOE", lambda: make_goe_fixed_trace(N, target_trace)),
    ("Hebbian", lambda: make_hebbian_fixed_trace(N, target_trace, patterns=3)),
    ("Attention", lambda: make_attention_fixed_trace(N, target_trace)),
]:
    gh_sums, gammas, Hs, traces = [], [], [], []
    for _ in range(n_samples):
        C = gen_fn()
        g, h = compute_gamma_H(C)
        gh_sums.append(g + h)
        gammas.append(g)
        Hs.append(h)
        traces.append(np.trace(C))
    
    gh = np.array(gh_sums)
    cv = np.std(gh) / np.mean(gh) if np.mean(gh) > 0 else float('inf')
    corr = np.corrcoef(gammas, Hs)[0, 1]
    
    print(f"\n  {name} (N={N}, Tr={target_trace}):")
    print(f"    Tr(C) = {np.mean(traces):.6f} ± {np.std(traces):.8f}")
    print(f"    γ+H   = {np.mean(gh):.6f} ± {np.std(gh):.6f} (CV={cv:.4f})")
    print(f"    γ     = {np.mean(gammas):.6f} ± {np.std(gammas):.6f}")
    print(f"    H     = {np.mean(Hs):.6f} ± {np.std(Hs):.6f}")
    print(f"    γ-H corr: {corr:.4f}")
    
    results[f"{name}_N={N}_Tr={target_trace}"] = {
        'type': name, 'N': N, 'target_trace': target_trace,
        'n_samples': n_samples, 'mean_gh': np.mean(gh), 'std_gh': np.std(gh),
        'cv_gh': cv, 'mean_gamma': np.mean(gammas), 'mean_H': np.mean(Hs),
        'gamma_H_correlation': corr,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Fleet simulation with trace tracking (reproduces cycle-000 dynamics)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 4: Fleet simulation — trace evolution over rounds")
print("=" * 70)

def simulate_fleet_trace(N, n_rounds=200, coupling='random', precision='FP32'):
    """Simulate fleet and track Tr(C), γ, H at every round."""
    # Initialize coupling matrix
    if coupling == 'random':
        C = np.random.randn(N, N) * 0.1
        C = (C + C.T) / 2
        np.fill_diagonal(C, 1.0)
    elif coupling == 'hebbian':
        C = make_hebbian(N, patterns=3)
        C = C / np.max(np.abs(C)) * 0.5 + np.eye(N) * 0.5
    elif coupling == 'attention':
        C = make_attention(N)
    
    traces, gammas_list, Hs_list, gh_list = [], [], [], []
    
    for r in range(n_rounds):
        tr = np.trace(C)
        g, h = compute_gamma_H(C)
        traces.append(tr)
        gammas_list.append(g)
        Hs_list.append(h)
        gh_list.append(g + h)
        
        # Update coupling
        noise = np.random.randn(N, N) * 0.01
        if coupling == 'random':
            C = C * 0.95 + 0.05 * ((noise + noise.T) / 2)
        elif coupling == 'hebbian':
            # Hebbian: outer product of state
            state = np.random.randn(N)
            C = C * 0.9 + 0.1 * np.outer(state, state)
            C = (C + C.T) / 2
        elif coupling == 'attention':
            Q = np.random.randn(N, N) * 0.3
            K = np.random.randn(N, N) * 0.3
            scores = Q @ K.T / np.sqrt(N)
            scores_exp = np.exp(scores - scores.max(axis=1, keepdims=True))
            attn = scores_exp / scores_exp.sum(axis=1, keepdims=True)
            attn = (attn + attn.T) / 2
            C = C * 0.9 + 0.1 * attn
        
        np.fill_diagonal(C, 1.0)
    
    return {
        'traces': traces, 'gammas': gammas_list, 'Hs': Hs_list, 'gh': gh_list
    }

for coupling in ['random', 'hebbian', 'attention']:
    print(f"\n  Coupling: {coupling}")
    for N in [5, 10, 20]:
        data = simulate_fleet_trace(N, n_rounds=200, coupling=coupling)
        tr = np.array(data['traces'])
        gh = np.array(data['gh'])
        
        tr_cv = np.std(tr) / np.mean(tr) if np.mean(tr) > 0 else float('inf')
        gh_cv = np.std(gh) / np.mean(gh) if np.mean(gh) > 0 else float('inf')
        
        # Correlation between Tr(C) and γ+H
        corr = np.corrcoef(tr, gh)[0, 1]
        
        print(f"    N={N:2d}: Tr(C) = {np.mean(tr):.4f} ± {np.std(tr):.4f} (CV={tr_cv:.4f}), "
              f"γ+H = {np.mean(gh):.4f} ± {np.std(gh):.4f} (CV={gh_cv:.4f}), "
              f"corr(Tr,γ+H) = {corr:.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Regression — how much of γ+H variance is explained by Tr(C)?
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 5: R² regression — Tr(C) → γ+H (pooled across coupling types)")
print("=" * 70)

for coupling in ['random', 'hebbian', 'attention']:
    all_tr, all_gh = [], []
    for N in [5, 10, 15, 20]:
        data = simulate_fleet_trace(N, n_rounds=200, coupling=coupling)
        all_tr.extend(data['traces'])
        all_gh.extend(data['gh'])
    
    all_tr = np.array(all_tr)
    all_gh = np.array(all_gh)
    
    # Linear regression
    from numpy.polynomial.polynomial import polyfit
    coeffs = np.polyfit(all_tr, all_gh, 1)
    predicted = np.polyval(coeffs, all_tr)
    ss_res = np.sum((all_gh - predicted)**2)
    ss_tot = np.sum((all_gh - np.mean(all_gh))**2)
    r2 = 1 - ss_res / ss_tot
    corr = np.corrcoef(all_tr, all_gh)[0, 1]
    
    print(f"  {coupling:10s}: R²(Tr→γ+H) = {r2:.6f}, corr = {corr:.4f}, "
          f"slope = {coeffs[0]:.6f}, intercept = {coeffs[1]:.6f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: The analytical argument — for GOE with fixed trace, eigenvalue 
# density is Wigner semicircle → γ and H are functions of N and σ only
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 6: Analytical — GOE eigenvalue density shape at fixed trace")
print("=" * 70)

N = 20
n_samples = 10000

for tr in [2.0, 5.0, 10.0]:
    all_eigs = []
    for _ in range(n_samples):
        C = make_goe_fixed_trace(N, tr)
        eigs = np.sort(eigvalsh(C))[::-1]
        all_eigs.append(eigs)
    
    all_eigs = np.array(all_eigs)
    mean_eigs = np.mean(all_eigs, axis=0)
    std_eigs = np.std(all_eigs, axis=0)
    
    print(f"\n  N={N}, Tr={tr}:")
    print(f"    Mean eigenvalues: {mean_eigs[:5].round(4)} ... {mean_eigs[-3:].round(4)}")
    print(f"    Std eigenvalues:  {std_eigs[:5].round(4)} ... {std_eigs[-3:].round(4)}")
    print(f"    Sum of means:     {mean_eigs.sum():.6f} (target: {tr})")
    
    # Check: are eigenvalues a deterministic function of trace?
    eig_cvs = std_eigs / np.abs(mean_eigs + 1e-10)
    print(f"    Eigenvalue CVs:   min={eig_cvs.min():.4f}, max={eig_cvs.max():.4f}, mean={eig_cvs.mean():.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: WIGNER SEMICIRCLE FIT — does the eigenvalue density match?
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 7: Eigenvalue density — Wigner semicircle fit")
print("=" * 70)

N = 50
n_samples = 5000
tr = 10.0

all_eigs = []
for _ in range(n_samples):
    C = make_goe_fixed_trace(N, tr)
    eigs = eigvalsh(C)
    all_eigs.extend(eigs)

all_eigs = np.array(all_eigs)

# Wigner semicircle: ρ(x) = (2/(πR²))√(R² - x²) for |x| < R
# For GOE with variance σ², R = 2σ√N
# Estimate R from data
from scipy.optimize import minimize_scalar

def semicircle_pdf(x, R):
    """Wigner semicircle density."""
    mask = np.abs(x) < R
    pdf = np.zeros_like(x)
    pdf[mask] = (2 / (np.pi * R**2)) * np.sqrt(R**2 - x[mask]**2)
    return pdf

# Fit R by minimizing KL divergence
hist, bin_edges = np.histogram(all_eigs, bins=100, density=True)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

def neg_loglik(R):
    if R <= 0:
        return 1e10
    pdf = semicircle_pdf(bin_centers, R)
    pdf = np.maximum(pdf, 1e-10)
    return -np.sum(hist * np.log(pdf))

res = minimize_scalar(neg_loglik, bounds=(0.1, 10.0), method='bounded')
R_fit = res.x
R_theory = 2 * np.std(all_eigs) * np.sqrt(N) / np.sqrt(2)  # rough estimate

# Actually for our normalized matrices:
# Tr(C) = tr → average eigenvalue = tr/N
# The variance of the GOE determines R
sigma_est = np.std(all_eigs)  # rough
R_semicircle = 2 * sigma_est

print(f"  N={N}, Tr={tr}, {n_samples} samples")
print(f"  Empirical eigenvalue range: [{all_eigs.min():.4f}, {all_eigs.max():.4f}]")
print(f"  Fitted R: {R_fit:.4f}")
print(f"  2σ estimate: {2*np.std(all_eigs):.4f}")
print(f"  Mean eigenvalue: {np.mean(all_eigs):.4f} (= Tr/N = {tr/N:.4f})")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: The KEY test — fixed trace, GOE vs Hebbian eigenvalue spread
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 8: Eigenvalue SPREAD at fixed trace — GOE vs Hebbian vs Attention")
print("=" * 70)

N = 10
tr = 5.0
n_samples = 3000

for name, gen_fn in [
    ("GOE", lambda: make_goe_fixed_trace(N, tr)),
    ("Hebbian", lambda: make_hebbian_fixed_trace(N, tr, patterns=3)),
    ("Attention", lambda: make_attention_fixed_trace(N, tr)),
]:
    tr_C2_list = []
    det_list = []
    gh_list = []
    
    for _ in range(n_samples):
        C = gen_fn()
        eigs = eigvalsh(C)
        tr_C2 = np.sum(eigs**2)
        det = np.prod(np.abs(eigs))
        g, h = compute_gamma_H(C)
        tr_C2_list.append(tr_C2)
        det_list.append(det)
        gh_list.append(g + h)
    
    tr_C2 = np.array(tr_C2_list)
    gh = np.array(gh_list)
    
    # Key question: is γ+H variance explained by Tr(C²) variance?
    corr_trC2_gh = np.corrcoef(tr_C2, gh)[0, 1]
    
    print(f"\n  {name}:")
    print(f"    Tr(C²) = {np.mean(tr_C2):.4f} ± {np.std(tr_C2):.4f} (CV={np.std(tr_C2)/np.mean(tr_C2):.4f})")
    print(f"    γ+H    = {np.mean(gh):.4f} ± {np.std(gh):.4f} (CV={np.std(gh)/np.mean(gh):.4f})")
    print(f"    Corr(Tr(C²), γ+H) = {corr_trC2_gh:.4f}")
    
    # Multi-regression: Tr(C) + Tr(C²) → γ+H
    # Since Tr(C) is fixed, this is just Tr(C²) → γ+H
    coeffs = np.polyfit(tr_C2, gh, 1)
    pred = np.polyval(coeffs, tr_C2)
    ss_res = np.sum((gh - pred)**2)
    ss_tot = np.sum((gh - np.mean(gh))**2)
    r2 = 1 - ss_res / ss_tot
    print(f"    R²(Tr(C²)→γ+H) = {r2:.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: Load cycle-000 data and check Tr(C) conservation
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 9: Cycle-000 data — reconstruct trace from γ+H trajectories")
print("=" * 70)

cycle0_path = BASE / "cycle-000"
for exp_file in sorted(cycle0_path.glob("results_exp*.json")):
    with open(exp_file) as f:
        data = json.load(f)
    
    print(f"\n  {exp_file.name}:")
    for config_name, config_data in data.items():
        if 'gh_trajectory_last10' in config_data:
            traj = config_data['gh_trajectory_last10']
            if traj:
                gh_arr = np.array(traj)
                cv = np.std(gh_arr) / np.mean(gh_arr) if np.mean(gh_arr) > 0 else float('inf')
                print(f"    {config_name}: γ+H over last 10 rounds = {np.mean(gh_arr):.4f} ± {np.std(gh_arr):.4f} (CV={cv:.6f})")
        if 'cv_gh' in config_data:
            print(f"    {config_name}: CV(γ+H) = {config_data['cv_gh']:.6f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10: DEFINITIVE — For GOE with FIXED Tr(C), is γ+H truly constant?
# Control: vary trace by tiny amounts → γ+H should vary proportionally
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 10: DEFINITIVE — γ+H sensitivity to trace perturbation")
print("=" * 70)

N = 10
n_samples = 5000
base_trace = 5.0

# Baseline
gh_baseline = []
for _ in range(n_samples):
    C = make_goe_fixed_trace(N, base_trace)
    g, h = compute_gamma_H(C)
    gh_baseline.append(g + h)

print(f"\n  Baseline Tr={base_trace}: γ+H = {np.mean(gh_baseline):.6f} ± {np.std(gh_baseline):.6f}")

# Perturb trace by small amounts
for delta in [0.001, 0.01, 0.1, 0.5, 1.0]:
    gh_perturbed = []
    for _ in range(n_samples):
        C = make_goe_fixed_trace(N, base_trace + delta)
        g, h = compute_gamma_H(C)
        gh_perturbed.append(g + h)
    
    shift = np.mean(gh_perturbed) - np.mean(gh_baseline)
    sensitivity = shift / delta
    print(f"  Tr={base_trace+delta}: γ+H = {np.mean(gh_perturbed):.6f} (shift={shift:.6f}, sensitivity={sensitivity:.4f})")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11: The critical control — UNNORMALIZED GOE matrices
# If Tr(C) is NOT fixed, γ+H should NOT be conserved
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 11: UNNORMALIZED GOE — trace NOT fixed → γ+H should vary")
print("=" * 70)

N = 10
n_samples = 5000
sigmas = [0.1, 0.5, 1.0, 2.0, 5.0]

for sigma in sigmas:
    gh_sums, traces = [], []
    for _ in range(n_samples):
        C = make_goe(N, sigma)  # NOT normalized — trace varies freely
        tr = np.trace(C)
        g, h = compute_gamma_H(C)
        gh_sums.append(g + h)
        traces.append(tr)
    
    gh = np.array(gh_sums)
    tr = np.array(traces)
    corr = np.corrcoef(tr, gh)[0, 1]
    
    # Regress Tr(C) → γ+H
    coeffs = np.polyfit(tr, gh, 1)
    pred = np.polyval(coeffs, tr)
    ss_res = np.sum((gh - pred)**2)
    ss_tot = np.sum((gh - np.mean(gh))**2)
    r2 = 1 - ss_res / ss_tot
    
    cv_gh = np.std(gh) / np.mean(gh) if np.mean(gh) > 0 else float('inf')
    
    print(f"  σ={sigma:.1f}: Tr = {np.mean(tr):.4f} ± {np.std(tr):.4f}, "
          f"γ+H = {np.mean(gh):.4f} ± {np.std(gh):.4f} (CV={cv_gh:.4f}), "
          f"R²(Tr→γ+H)={r2:.4f}, corr={corr:.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print("""
TRACE-CONSERVATION HYPOTHESIS VERDICT:
- If γ+H is nearly constant for GOE with fixed Tr(C) → hypothesis SUPPORTED
- If γ+H varies with Tr(C) in proportion → Tr(C) explains the conservation
- If Hebbian/Attention with fixed Tr(C) still shows different γ+H → additional moments matter
- If unnormalized GOE shows γ+H varying with Tr(C) → Tr(C) is the driver

KEY METRICS:
- Test 1: CV(γ+H) at fixed trace — should be <0.05 for GOE
- Test 5: R²(Tr→γ+H) in fleet simulation — should be >0.8
- Test 8: R²(Tr(C²)→γ+H) — if high, second moment also matters
- Test 10: Sensitivity d(γ+H)/d(Tr) — should be constant (linear relationship)
- Test 11: Unnormalized — R²(Tr→γ+H) should be very high (>0.95)
""")

# Save all results
output_path = Path(__file__).parent / "trace_test_results.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {output_path}")
