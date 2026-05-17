#!/usr/bin/env python3
"""
Cycle 10: Stress Test the Convergent Theory
Conservation quality = eigenvector stability × activation contractivity

5 experiments:
1. Eigenvector rotation × CV correlation (sweep coupling structure)
2. Activation contractivity sweep (7 activations)
3. Deliberate eigenvector destabilization (noise on eigenvectors)
4. Scale verification (N=5,10,20,50)
5. Counterexample search (low rotation + high CV, or vice versa)
"""

import numpy as np
from scipy.linalg import eig, svd
from scipy.stats import pearsonr, spearmanr
import json
import os

np.random.seed(42)

OUTDIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# ACTIVATIONS AND THEIR PROPERTIES
# ============================================================
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

def swish(x):
    return x * sigmoid(x)

def hard_tanh(x):
    return np.clip(x, -1, 1)

def softplus(x):
    return np.log1p(np.exp(-np.clip(x, -30, 30))) + np.clip(x, -30, 30)

def leaky_relu(x, alpha=0.01):
    return np.where(x > 0, x, alpha * x)

ACTIVATIONS = {
    'hard_tanh': (hard_tanh, 1.0, 'bounded'),
    'tanh': (np.tanh, 1.0, 'bounded'),
    'sigmoid': (sigmoid, 0.25, 'bounded'),
    'swish': (swish, 1.1, 'unbounded'),
    'softplus': (softplus, float('inf'), 'unbounded'),
    'relu': (lambda x: np.maximum(0, x), float('inf'), 'unbounded'),
    'leaky_relu': (leaky_relu, float('inf'), 'unbounded'),
}

# ============================================================
# COUPLING GENERATORS
# ============================================================
def make_random(n, scale=1.0):
    """GOE random matrix"""
    m = np.random.randn(n, n) * scale / np.sqrt(n)
    return (m + m.T) / 2

def make_hebbian(n, scale=1.0):
    """Random pattern Hebbian"""
    k = max(3, n // 2)
    patterns = np.random.randn(k, n)
    m = patterns.T @ patterns / k * scale
    return m

def make_attention(n, tau=1.0):
    """Softmax attention coupling"""
    # Random key-query matrix
    W = np.random.randn(n, n) / np.sqrt(n)
    logits = W @ W.T / tau
    logits -= logits.max(axis=1, keepdims=True)
    exp_l = np.exp(logits)
    return exp_l / exp_l.sum(axis=1, keepdims=True)

def make_random_row_stoch(n, scale=1.0):
    """Random row-stochastic matrix"""
    m = np.random.randn(n, n) * scale
    m = np.exp(m) / np.exp(m).sum(axis=1, keepdims=True)
    return m

def make_rank_r(n, r=2, scale=1.0):
    """Rank-r random matrix with controlled eigenvector rotation"""
    U = np.linalg.qr(np.random.randn(n, r))[0]
    S = np.random.randn(r) * scale
    V = np.linalg.qr(np.random.randn(n, r))[0]
    return U @ np.diag(S) @ V.T + 0.01 * np.random.randn(n, n)

def make_mixed(n, alpha, scale=1.0):
    """Interpolation: alpha*random + (1-alpha)*hebbian"""
    r = make_random(n, scale)
    h = make_hebbian(n, scale)
    return alpha * r + (1 - alpha) * h

# ============================================================
# STATE-DEPENDENT COUPLING
# ============================================================
def coupling_sd_attention(x, tau=1.0):
    """State-dependent softmax attention"""
    n = len(x)
    logits = np.outer(x, x) / (tau * n)
    logits -= logits.max(axis=1, keepdims=True)
    exp_l = np.exp(logits)
    return exp_l / exp_l.sum(axis=1, keepdims=True)

def coupling_sd_hebbian(x, scale=1.0):
    """State-dependent Hebbian: x x^T"""
    return scale * np.outer(x, x) / len(x)

def coupling_sd_random(x, scale=1.0):
    """State-dependent random (resampled each step)"""
    return make_random(len(x), scale)

# ============================================================
# DYNAMICS AND MEASUREMENT
# ============================================================
def compute_gamma_H(C):
    """Compute spectral gap γ and participation entropy H from eigenvalues"""
    try:
        C_sym = (C + C.T) / 2  # Symmetrize for numerical stability
        eigs = np.real(np.linalg.eigvalsh(C_sym))
    except np.linalg.LinAlgError:
        eigs = np.abs(np.linalg.svd(C, compute_uv=False))
    eigs_pos = np.abs(eigs)
    total = eigs_pos.sum()
    if total < 1e-12:
        return 0.0, 0.0
    eigs_sorted = np.sort(eigs_pos)[::-1]
    gamma = (eigs_sorted[0] - eigs_sorted[1]) / (eigs_sorted[0] + 1e-12)
    p = eigs_pos / total
    p = p[p > 1e-12]
    H = -np.sum(p * np.log(p))
    return gamma, H

def measure_eigvec_rotation(C1, C2):
    """Measure rotation of top eigenvector between two coupling matrices"""
    try:
        v1 = np.linalg.eigh((C1 + C1.T)/2)[1][:, -1]
        v2 = np.linalg.eigh((C2 + C2.T)/2)[1][:, -1]
    except np.linalg.LinAlgError:
        _, _, Vt1 = np.linalg.svd((C1 + C1.T)/2)
        _, _, Vt2 = np.linalg.svd((C2 + C2.T)/2)
        v1 = Vt1[0]
        v2 = Vt2[0]
    cos_angle = np.abs(np.clip(np.dot(v1, v2), -1, 1))
    return np.degrees(np.arccos(cos_angle))

def run_dynamics(coupling_func, activation, n, steps=200, noise=0.1, x0=None):
    """Run nonlinear dynamics and return trajectory data"""
    if x0 is None:
        x = np.random.randn(n) * 0.5
    else:
        x = x0.copy()
    
    trajectory = []
    gamma_H_values = []
    rotations = []
    norms = []
    prev_C = coupling_func(x)
    
    for t in range(steps):
        C = coupling_func(x)
        x_new = activation(C @ x) + noise * np.random.randn(n)
        
        g, h = compute_gamma_H(C)
        gamma_H_values.append(g + h)
        
        if t > 0:
            rot = measure_eigvec_rotation(prev_C, C)
            rotations.append(rot)
        
        norms.append(np.linalg.norm(x))
        trajectory.append(x.copy())
        prev_C = C
        x = x_new
    
    gh = np.array(gamma_H_values)
    cv = np.std(gh) / (np.mean(gh) + 1e-12) if np.mean(gh) > 1e-12 else float('inf')
    
    return {
        'gamma_H': gh,
        'cv': cv,
        'mean_gh': np.mean(gh),
        'std_gh': np.std(gh),
        'rotations': np.array(rotations),
        'mean_rotation': np.mean(rotations) if rotations else 0,
        'mean_norm': np.mean(norms),
        'trajectory': trajectory,
    }

# ============================================================
# EXPERIMENT 1: Eigenvector Rotation × CV Correlation
# ============================================================
def exp1_rotation_cv_correlation():
    """Sweep from random to structured coupling, measure rotation vs CV"""
    print("=" * 60)
    print("EXPERIMENT 1: Eigenvector Rotation × CV Correlation")
    print("=" * 60)
    
    results = []
    n = 20
    steps = 200
    noise = 0.1
    n_samples = 30
    
    # Sweep coupling types with varying structure
    configs = []
    
    # A) Mixed coupling: alpha from 0 (Hebbian) to 1 (random)
    for alpha in np.linspace(0, 1, 11):
        label = f"mixed_α={alpha:.1f}"
        configs.append((label, lambda x, a=alpha: make_mixed(len(x), a)))
    
    # B) Attention with varying temperature
    for tau in [0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]:
        label = f"attention_τ={tau}"
        configs.append((label, lambda x, t=tau: coupling_sd_attention(x, t)))
    
    # C) State-dependent Hebbian
    configs.append(("sd_hebbian", lambda x: coupling_sd_hebbian(x)))
    
    # D) Random resampled
    configs.append(("random_resampled", lambda x: coupling_sd_random(x)))
    
    for label, cfunc in configs:
        sample_results = []
        for s in range(n_samples):
            act = np.tanh  # standard tanh for this experiment
            res = run_dynamics(cfunc, act, n, steps, noise)
            sample_results.append(res)
        
        mean_cv = np.mean([r['cv'] for r in sample_results])
        mean_rot = np.mean([r['mean_rotation'] for r in sample_results])
        mean_norm = np.mean([r['mean_norm'] for r in sample_results])
        
        results.append({
            'config': label,
            'mean_cv': mean_cv,
            'mean_rotation': mean_rot,
            'mean_norm': mean_norm,
        })
        print(f"  {label:30s} CV={mean_cv:.4f}  rot={mean_rot:.2f}°  ||x||={mean_norm:.2f}")
    
    # Correlation analysis
    cvs = np.array([r['mean_cv'] for r in results])
    rots = np.array([r['mean_rotation'] for r in results])
    norms = np.array([r['mean_norm'] for r in results])
    
    r_rot_cv, p_rot_cv = pearsonr(rots, cvs)
    r_norm_cv, p_norm_cv = pearsonr(norms, cvs)
    
    # Log-transformed rotation (since relationship may be nonlinear)
    log_rots = np.log1p(rots)
    r_logrot_cv, p_logrot_cv = pearsonr(log_rots, cvs)
    
    print(f"\n  Pearson r(rotation, CV) = {r_rot_cv:.4f} (p={p_rot_cv:.6f})")
    print(f"  Pearson r(log(rotation), CV) = {r_logrot_cv:.4f} (p={p_logrot_cv:.6f})")
    print(f"  Pearson r(norm, CV) = {r_norm_cv:.4f} (p={p_norm_cv:.6f})")
    
    # Check for threshold: is there a rotation below which CV is always low?
    low_rot = [r for r in results if r['mean_rotation'] < 5.0]
    high_rot = [r for r in results if r['mean_rotation'] >= 5.0]
    if low_rot and high_rot:
        print(f"\n  Rotation < 5°: mean CV = {np.mean([r['mean_cv'] for r in low_rot]):.4f} (n={len(low_rot)})")
        print(f"  Rotation ≥ 5°: mean CV = {np.mean([r['mean_cv'] for r in high_rot]):.4f} (n={len(high_rot)})")
    
    # Linearity check: fit rotation → CV
    from numpy.polynomial import polynomial as P_fit
    coeffs_linear = np.polyfit(rots, cvs, 1)
    preds_linear = np.polyval(coeffs_linear, rots)
    ss_res = np.sum((cvs - preds_linear)**2)
    ss_tot = np.sum((cvs - np.mean(cvs))**2)
    r2_linear = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    coeffs_quad = np.polyfit(rots, cvs, 2)
    preds_quad = np.polyval(coeffs_quad, rots)
    ss_res_q = np.sum((cvs - preds_quad)**2)
    r2_quad = 1 - ss_res_q / ss_tot if ss_tot > 0 else 0
    
    print(f"\n  Linear fit R² = {r2_linear:.4f}")
    print(f"  Quadratic fit R² = {r2_quad:.4f}")
    print(f"  Linear threshold: relationship is {'LINEAR' if r2_linear > 0.7 else 'NON-LINEAR'}")
    
    return results, {'r_rot_cv': r_rot_cv, 'r_logrot_cv': r_logrot_cv, 'r2_linear': r2_linear, 'r2_quad': r2_quad}


# ============================================================
# EXPERIMENT 2: Activation Contractivity Sweep
# ============================================================
def exp2_activation_sweep():
    """Compare activations with different Lipschitz constants"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Activation Contractivity Sweep")
    print("=" * 60)
    
    n = 20
    steps = 200
    noise = 0.1
    n_samples = 30
    
    results = []
    
    for act_name, (act_func, lipschitz, bounded) in ACTIVATIONS.items():
        sample_cvs = []
        sample_norms = []
        sample_rots = []
        
        for s in range(n_samples):
            # State-dependent attention coupling
            res = run_dynamics(
                lambda x: coupling_sd_attention(x, tau=1.0),
                act_func, n, steps, noise
            )
            sample_cvs.append(res['cv'])
            sample_norms.append(res['mean_norm'])
            sample_rots.append(res['mean_rotation'])
        
        mean_cv = np.mean(sample_cvs)
        mean_norm = np.mean(sample_norms)
        mean_rot = np.mean(sample_rots)
        
        results.append({
            'activation': act_name,
            'lipschitz': lipschitz,
            'bounded': bounded,
            'mean_cv': mean_cv,
            'mean_norm': mean_norm,
            'mean_rotation': mean_rot,
            'std_cv': np.std(sample_cvs),
        })
        print(f"  {act_name:12s}  L={str(lipschitz):>5s}  bounded={bounded:4s}  "
              f"CV={mean_cv:.4f}±{np.std(sample_cvs):.4f}  ||x||={mean_norm:.2f}  rot={mean_rot:.2f}°")
    
    # Correlation analysis
    cvs = np.array([r['mean_cv'] for r in results])
    lipschitz = np.array([r['lipschitz'] if r['lipschitz'] != float('inf') else 100 for r in results])
    norms = np.array([r['mean_norm'] for r in results])
    rots = np.array([r['mean_rotation'] for r in results])
    
    # Bounded vs unbounded t-test
    bounded_cvs = [r['mean_cv'] for r in results if r['bounded'] == 'bounded']
    unbounded_cvs = [r['mean_cv'] for r in results if r['bounded'] == 'unbounded']
    
    r_norm_cv, p_norm_cv = pearsonr(norms, cvs)
    r_rot_cv, p_rot_cv = pearsonr(rots, cvs)
    
    print(f"\n  Pearson r(norm, CV) = {r_norm_cv:.4f} (p={p_norm_cv:.6f})")
    print(f"  Pearson r(rotation, CV) = {r_rot_cv:.4f} (p={p_rot_cv:.6f})")
    print(f"  Bounded mean CV = {np.mean(bounded_cvs):.4f}, Unbounded mean CV = {np.mean(unbounded_cvs):.4f}")
    
    # The key prediction: CV ∝ state_norm ∝ 1/contractivity
    print(f"\n  Prediction check: smaller norm → better conservation")
    sorted_r = sorted(results, key=lambda r: r['mean_norm'])
    for r in sorted_r:
        marker = "✓" if r['mean_cv'] < 0.06 else "✗"
        print(f"    {marker} {r['activation']:12s}  ||x||={r['mean_norm']:.2f}  CV={r['mean_cv']:.4f}")
    
    return results


# ============================================================
# EXPERIMENT 3: Deliberate Eigenvector Destabilization
# ============================================================
def exp3_eigvec_destabilization():
    """Add controlled noise to eigenvectors and measure CV response"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Eigenvector Destabilization")
    print("=" * 60)
    
    n = 20
    steps = 200
    noise = 0.1
    n_samples = 20
    
    noise_levels = [0.0, 0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
    
    results = []
    
    for sigma_ev in noise_levels:
        sample_cvs = []
        sample_rots = []
        
        for s in range(n_samples):
            def coupling_noisy(x, sig=sigma_ev):
                # Start with attention coupling
                C = coupling_sd_attention(x, tau=1.0)
                # Add noise that rotates eigenvectors
                # Perturb with random symmetric noise
                E = np.random.randn(n, n) * sig
                E = (E + E.T) / 2
                return C + E
            
            res = run_dynamics(coupling_noisy, np.tanh, n, steps, noise)
            sample_cvs.append(res['cv'])
            sample_rots.append(res['mean_rotation'])
        
        mean_cv = np.mean(sample_cvs)
        mean_rot = np.mean(sample_rots)
        
        results.append({
            'noise_sigma': sigma_ev,
            'mean_cv': mean_cv,
            'std_cv': np.std(sample_cvs),
            'mean_rotation': mean_rot,
        })
        print(f"  σ_ev={sigma_ev:6.3f}  CV={mean_cv:.4f}±{np.std(sample_cvs):.4f}  rot={mean_rot:.2f}°")
    
    # Check: does CV track noise magnitude?
    sigmas = np.array([r['noise_sigma'] for r in results])
    cvs = np.array([r['mean_cv'] for r in results])
    rots = np.array([r['mean_rotation'] for r in results])
    
    r_sigma_cv, p_sigma_cv = pearsonr(sigmas, cvs)
    r_sigma_rot, p_sigma_rot = pearsonr(sigmas, rots)
    r_rot_cv, p_rot_cv = pearsonr(rots, cvs)
    
    print(f"\n  r(σ, CV) = {r_sigma_cv:.4f} (p={p_sigma_cv:.6f})")
    print(f"  r(σ, rotation) = {r_sigma_rot:.4f} (p={p_sigma_rot:.6f})")
    print(f"  r(rotation, CV) = {r_rot_cv:.4f} (p={p_rot_cv:.6f})")
    
    # Check linearity
    log_sigmas = np.log1p(sigmas)
    r_logsig_cv, _ = pearsonr(log_sigmas, cvs)
    print(f"  r(log(σ), CV) = {r_logsig_cv:.4f}")
    
    # Mediation analysis: σ → rotation → CV
    # If r(σ, CV) drops when controlling for rotation, rotation mediates
    from numpy.linalg import lstsq
    X = np.column_stack([sigmas, rots])
    coeffs, _, _, _ = lstsq(X, cvs, rcond=None)
    print(f"\n  Multiple regression CV ~ σ + rotation: coeff_σ={coeffs[0]:.4f}, coeff_rot={coeffs[1]:.6f}")
    
    return results


# ============================================================
# EXPERIMENT 4: Scale Verification (N=5,10,20,50)
# ============================================================
def exp4_scale_verification():
    """Test eigenvector rotation predictor across matrix sizes"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Scale Verification")
    print("=" * 60)
    
    sizes = [5, 10, 20, 50]
    steps = 200
    noise = 0.1
    n_samples = 25
    
    coupling_types = {
        'attention_sd': lambda x: coupling_sd_attention(x, tau=1.0),
        'hebbian_sd': lambda x: coupling_sd_hebbian(x),
        'random_resampled': lambda x: coupling_sd_random(x),
    }
    
    results = []
    
    for n in sizes:
        print(f"\n  N={n}:")
        for ctype, cfunc in coupling_types.items():
            sample_cvs = []
            sample_rots = []
            sample_norms = []
            
            for s in range(n_samples):
                res = run_dynamics(cfunc, np.tanh, n, steps, noise)
                sample_cvs.append(res['cv'])
                sample_rots.append(res['mean_rotation'])
                sample_norms.append(res['mean_norm'])
            
            mean_cv = np.mean(sample_cvs)
            mean_rot = np.mean(sample_rots)
            mean_norm = np.mean(sample_norms)
            
            results.append({
                'N': n,
                'coupling': ctype,
                'mean_cv': mean_cv,
                'mean_rotation': mean_rot,
                'mean_norm': mean_norm,
            })
            print(f"    {ctype:20s}  CV={mean_cv:.4f}  rot={mean_rot:.2f}°  ||x||={mean_norm:.2f}")
    
    # Cross-size correlation: rotation → CV
    all_rots = np.array([r['mean_rotation'] for r in results])
    all_cvs = np.array([r['mean_cv'] for r in results])
    
    r_rot_cv, p_rot_cv = pearsonr(all_rots, all_cvs)
    print(f"\n  Cross-size r(rotation, CV) = {r_rot_cv:.4f} (p={p_rot_cv:.6f})")
    
    # Per-size check: does ranking hold?
    for n in sizes:
        size_results = [r for r in results if r['N'] == n]
        sorted_by_rot = sorted(size_results, key=lambda r: r['mean_rotation'])
        sorted_by_cv = sorted(size_results, key=lambda r: r['mean_cv'])
        rank_match = [r['coupling'] for r in sorted_by_rot] == [r['coupling'] for r in sorted_by_cv]
        print(f"  N={n}: rotation ranking matches CV ranking: {rank_match}")
        if not rank_match:
            print(f"    By rotation: {[r['coupling'] for r in sorted_by_rot]}")
            print(f"    By CV:       {[r['coupling'] for r in sorted_by_cv]}")
    
    return results


# ============================================================
# EXPERIMENT 5: Counterexample Search
# ============================================================
def exp5_counterexample_search():
    """Try to find: low rotation + high CV, or high rotation + low CV"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 5: Counterexample Search")
    print("=" * 60)
    
    n = 20
    steps = 200
    noise = 0.1
    n_samples = 20
    
    counterexamples = []
    all_cases = []
    
    # Strategy 1: Low eigenvector rotation but try to get high CV
    print("\n  Strategy 1: Low rotation, try to inflate CV")
    
    # 1a) Near-identity coupling (no rotation) but with oscillatory forcing
    for beta in [0.0, 0.1, 0.3, 0.5, 1.0]:
        def coupling_near_identity(x, b=beta):
            I = np.eye(len(x))
            perturbation = b * np.random.randn(len(x), len(x)) * 0.01
            perturbation = (perturbation + perturbation.T) / 2
            return I + perturbation
        
        sample_cvs = []
        sample_rots = []
        for s in range(n_samples):
            res = run_dynamics(coupling_near_identity, np.tanh, n, steps, noise)
            sample_cvs.append(res['cv'])
            sample_rots.append(res['mean_rotation'])
        
        mean_cv = np.mean(sample_cvs)
        mean_rot = np.mean(sample_rots)
        print(f"    β={beta:.1f}:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
        all_cases.append({'name': f'near_identity_β={beta}', 'cv': mean_cv, 'rot': mean_rot})
        if mean_rot < 2.0 and mean_cv > 0.1:
            counterexamples.append(('LOW ROT + HIGH CV', f'near_identity_β={beta}', mean_rot, mean_cv))
    
    # 1b) Diagonal coupling with varying diagonal entries
    for spread in [0.1, 0.5, 1.0, 3.0, 5.0]:
        def coupling_diag_spread(x, sp=spread):
            d = np.random.randn(len(x)) * sp
            return np.diag(d)
        
        sample_cvs = []
        sample_rots = []
        for s in range(n_samples):
            res = run_dynamics(coupling_diag_spread, np.tanh, n, steps, noise)
            sample_cvs.append(res['cv'])
            sample_rots.append(res['mean_rotation'])
        
        mean_cv = np.mean(sample_cvs)
        mean_rot = np.mean(sample_rots)
        print(f"    diag_spread={spread}:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
        all_cases.append({'name': f'diag_spread={spread}', 'cv': mean_cv, 'rot': mean_rot})
        if mean_rot < 2.0 and mean_cv > 0.1:
            counterexamples.append(('LOW ROT + HIGH CV', f'diag_spread={spread}', mean_rot, mean_cv))
    
    # Strategy 2: High eigenvector rotation but try to keep CV low
    print("\n  Strategy 2: High rotation, try to suppress CV")
    
    # 2a) Rapid rotation but with swish (contractive)
    for scale_factor in [1.0, 2.0, 3.0]:
        def coupling_hebbian_scaled(x, sf=scale_factor):
            c = sf * np.outer(x, x) / len(x)
            # Ensure positive semi-definite
            return c
        
        sample_cvs = []
        sample_rots = []
        for s in range(n_samples):
            try:
                res = run_dynamics(coupling_hebbian_scaled, swish, n, steps, noise)
                sample_cvs.append(res['cv'])
                sample_rots.append(res['mean_rotation'])
            except Exception:
                sample_cvs.append(float('nan'))
                sample_rots.append(float('nan'))
        
        mean_cv = np.nanmean(sample_cvs)
        mean_rot = np.nanmean(sample_rots)
        print(f"    hebbian_swish_sf={scale_factor}:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
        all_cases.append({'name': f'hebbian_swish_sf={scale_factor}', 'cv': mean_cv, 'rot': mean_rot})
        if mean_rot > 10.0 and mean_cv < 0.02:
            counterexamples.append(('HIGH ROT + LOW CV', f'hebbian_swish_sf={scale_factor}', mean_rot, mean_cv))
    
    # 2b) Random resampled with swish
    sample_cvs = []
    sample_rots = []
    for s in range(n_samples):
        res = run_dynamics(lambda x: coupling_sd_random(x), swish, n, steps, noise)
        sample_cvs.append(res['cv'])
        sample_rots.append(res['mean_rotation'])
    mean_cv = np.mean(sample_cvs)
    mean_rot = np.mean(sample_rots)
    print(f"    random_swish:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
    all_cases.append({'name': 'random_swish', 'cv': mean_cv, 'rot': mean_rot})
    if mean_rot > 10.0 and mean_cv < 0.02:
        counterexamples.append(('HIGH ROT + LOW CV', 'random_swish', mean_rot, mean_cv))
    
    # 2c) Random resampled with hard_tanh (L=1, bounded)
    sample_cvs = []
    sample_rots = []
    for s in range(n_samples):
        res = run_dynamics(lambda x: coupling_sd_random(x), hard_tanh, n, steps, noise)
        sample_cvs.append(res['cv'])
        sample_rots.append(res['mean_rotation'])
    mean_cv = np.mean(sample_cvs)
    mean_rot = np.mean(sample_rots)
    print(f"    random_hard_tanh:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
    all_cases.append({'name': 'random_hard_tanh', 'cv': mean_cv, 'rot': mean_rot})
    if mean_rot > 10.0 and mean_cv < 0.02:
        counterexamples.append(('HIGH ROT + LOW CV', 'random_hard_tanh', mean_rot, mean_cv))
    
    # 2d) Rotating rank-2 coupling with strong contractivity
    for sf in [0.5, 1.0, 2.0]:
        def coupling_rotating_rank2(x, sf2=sf):
            n = len(x)
            theta = sf2 * np.random.randn()
            R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
            base = np.random.randn(n, 2)
            rotated = base @ R.T
            return rotated @ rotated.T / n
        
        sample_cvs = []
        sample_rots = []
        for s in range(n_samples):
            res = run_dynamics(coupling_rotating_rank2, swish, n, steps, noise)
            sample_cvs.append(res['cv'])
            sample_rots.append(res['mean_rotation'])
        mean_cv = np.mean(sample_cvs)
        mean_rot = np.mean(sample_rots)
        print(f"    rotating_rank2_swish_sf={sf}:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
        all_cases.append({'name': f'rotating_rank2_swish_sf={sf}', 'cv': mean_cv, 'rot': mean_rot})
        if mean_rot > 10.0 and mean_cv < 0.02:
            counterexamples.append(('HIGH ROT + LOW CV', f'rotating_rank2_swish_sf={sf}', mean_rot, mean_cv))
    
    # Strategy 3: Adversarial — engineered to break the theory
    print("\n  Strategy 3: Adversarial constructions")
    
    # 3a) Coupling that switches between two fixed matrices (step function)
    for switch_period in [5, 10, 20]:
        def coupling_switching(x, period=switch_period):
            n = len(x)
            if not hasattr(coupling_switching, 'count'):
                coupling_switching.count = 0
            coupling_switching.count += 1
            if (coupling_switching.count // period) % 2 == 0:
                return make_attention(n, tau=1.0)
            else:
                return make_attention(n, tau=0.5)
        
        sample_cvs = []
        sample_rots = []
        for s in range(n_samples):
            coupling_switching.count = 0  # Reset counter
            res = run_dynamics(coupling_switching, np.tanh, n, steps, noise)
            sample_cvs.append(res['cv'])
            sample_rots.append(res['mean_rotation'])
        mean_cv = np.mean(sample_cvs)
        mean_rot = np.mean(sample_rots)
        print(f"    switching_period={switch_period}:  CV={mean_cv:.4f}  rot={mean_rot:.2f}°")
        all_cases.append({'name': f'switching_period={switch_period}', 'cv': mean_cv, 'rot': mean_rot})
    
    # Summary
    print(f"\n  COUNTEREXAMPLES FOUND: {len(counterexamples)}")
    for ce in counterexamples:
        print(f"    {ce[0]}: {ce[1]}  rotation={ce[2]:.2f}°  CV={ce[3]:.4f}")
    
    if not counterexamples:
        print("  ✗ NO COUNTEREXAMPLES FOUND — theory is robust")
    else:
        print("  ✓ COUNTEREXAMPLES FOUND — theory needs refinement")
    
    return counterexamples, all_cases


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("CYCLE 10: Stress Testing the Convergent Theory")
    print("Theory: Conservation quality = eigenvector stability × activation contractivity")
    print("=" * 60)
    
    exp1_results, exp1_stats = exp1_rotation_cv_correlation()
    exp2_results = exp2_activation_sweep()
    exp3_results = exp3_eigvec_destabilization()
    exp4_results = exp4_scale_verification()
    exp5_counter, exp5_all = exp5_counterexample_search()
    
    # Save all results
    save_data = {
        'exp1_rotation_cv': {
            'configs': exp1_results,
            'stats': {k: float(v) if not isinstance(v, float) else v 
                      for k, v in exp1_stats.items()},
        },
        'exp2_activation': exp2_results,
        'exp3_destabilization': exp3_results,
        'exp4_scale': exp4_results,
        'exp5_counterexamples': {
            'found': exp5_counter,
            'all_cases': exp5_all,
        },
    }
    
    # Handle numpy types for JSON
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            elif isinstance(obj, (np.floating,)):
                return float(obj)
            elif isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            elif isinstance(obj, float) and np.isnan(obj):
                return None
            elif isinstance(obj, float) and np.isinf(obj):
                return str(obj)
            return super().default(obj)
    
    with open(os.path.join(OUTDIR, 'raw_data.json'), 'w') as f:
        json.dump(save_data, f, indent=2, cls=NumpyEncoder)
    
    print("\n" + "=" * 60)
    print("ALL EXPERIMENTS COMPLETE")
    print(f"Raw data saved to {os.path.join(OUTDIR, 'raw_data.json')}")
