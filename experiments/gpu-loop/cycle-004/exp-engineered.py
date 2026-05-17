#!/usr/bin/env python3
"""
Cycle 4 — Engineered Eigenvalue Distribution Experiment
========================================================

QUESTION: Can we ENGINEER conservation by controlling Tr(C²)?

Previous findings:
- Tr(C²) conservation perfectly predicts γ+H conservation
- Attention/softmax bounds eigenvalue spread (CV=0.002)
- Two-moment constraint: Tr(C) + Tr(C²) → γ+H
- Power iteration is wrong dynamics → use nonlinear tanh

This experiment constructs coupling matrices with CONTROLLED eigenvalue
distributions and tests whether we can dial conservation up or down.

Dynamics: x_{t+1} = tanh(C @ x_t) — nonlinear, doesn't trivially converge
"""

import numpy as np
import json
import os
import time
from pathlib import Path

np.random.seed(42)

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ============================================================
# Helper functions
# ============================================================

def entropy(x):
    """Shannon entropy of a probability distribution."""
    x = np.abs(x)
    s = x.sum()
    if s < 1e-15:
        return 0.0
    p = x / s
    p = p[p > 1e-15]
    return -np.sum(p * np.log(p))

def gamma_hamiltonian(x, C):
    """
    γ = |x^T C x| / (||x||² λ_max)  — alignment with dominant eigenmode
    H = entropy(x) — information content
    """
    xn = np.linalg.norm(x)
    if xn < 1e-15:
        return 0.0, 0.0
    x_hat = x / xn
    quad = abs(x_hat @ C @ x_hat)
    eigs = np.linalg.eigvalsh(C)
    lam_max = max(abs(eigs))
    if lam_max < 1e-15:
        gamma = 0.0
    else:
        gamma = quad / lam_max
    H = entropy(x)
    return gamma, H

def run_dynamics(C, x0, steps=200):
    """Run nonlinear dynamics x_{t+1} = tanh(C @ x_t)."""
    N = C.shape[0]
    trajectory = np.zeros((steps, N))
    x = x0.copy()
    gammas = np.zeros(steps)
    hamiltonians = np.zeros(steps)
    
    for t in range(steps):
        trajectory[t] = x
        g, h = gamma_hamiltonian(x, C)
        gammas[t] = g
        hamiltonians[t] = h
        x = np.tanh(C @ x)
    
    return trajectory, gammas, hamiltonians

def compute_traces(C):
    """Compute Tr(C) and Tr(C²)."""
    return np.trace(C), np.trace(C @ C)

def construct_matrix_from_eigenvalues(eigenvalues, eigvec_basis=None, N=None):
    """
    Construct a real symmetric matrix with specified eigenvalues.
    If eigvec_basis is None, use a random orthogonal matrix.
    """
    if eigvec_basis is None:
        # Random orthogonal matrix via QR decomposition
        A = np.random.randn(N, N)
        Q, R = np.linalg.qr(A)
        # Ensure proper orthogonal (det = +1)
        Q = Q @ np.diag(np.sign(np.diag(R)))
    else:
        Q = eigvec_basis
    
    return Q @ np.diag(eigenvalues) @ Q.T

# ============================================================
# Matrix construction strategies
# ============================================================

def make_degenerate_matrix(N, eigenvalue=1.0):
    """(a) All eigenvalues equal — maximum degeneracy."""
    eigs = np.full(N, eigenvalue)
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_uniform_spectrum(N, lo=0.5, hi=2.0):
    """(b-i) Uniform distribution of eigenvalues."""
    eigs = np.random.uniform(lo, hi, N)
    eigs.sort()
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_exponential_spectrum(N, scale=1.0):
    """(b-ii) Exponential distribution of eigenvalues."""
    eigs = np.random.exponential(scale, N)
    eigs.sort()
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_powerlaw_spectrum(N, alpha=2.0, xmin=0.1):
    """(b-iii) Power-law distribution of eigenvalues (Pareto)."""
    eigs = (np.random.pareto(alpha, N) + 1) * xmin
    eigs.sort()
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_rank1_matrix(N, dominant=5.0, noise_scale=0.01):
    """(c) One large eigenvalue + rest small (rank-1 limit)."""
    eigs = np.full(N, noise_scale)
    eigs[0] = dominant
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_two_cluster_matrix(N, gap=5.0):
    """(d) Two clusters of eigenvalues with controlled gap."""
    half = N // 2
    eigs = np.concatenate([
        np.random.uniform(0.5, 1.5, half),
        np.random.uniform(gap, gap + 1.0, N - half)
    ])
    eigs.sort()
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_fixed_trC2_matrix(N, target_trC2, trC=None):
    """
    (e) Eigenvalues designed to keep Tr(C²) exactly at target_trC2.
    Strategy: start from a base spectrum, rescale to hit target Tr(C²).
    """
    if trC is None:
        trC = float(N)  # default: trace = N
    
    # Start with uniform eigenvalues, then rescale
    eigs = np.random.uniform(0.5, 2.0, N)
    
    # Iterative rescaling to hit target Tr(C²)
    for _ in range(100):
        current_trC2 = np.sum(eigs**2)
        if abs(current_trC2 - target_trC2) < 1e-10:
            break
        # Scale eigenvalues: new_eigs = eigs * s
        # Tr(C²) = sum(eigs²) * s² → s = sqrt(target / current)
        # But we also want to adjust Tr(C)
        # Use offset: eigs = base_eigs * s + offset
        # Tr(C) = sum(base)*s + N*offset = trC
        # Tr(C²) = sum(base²)*s² + 2*s*offset*sum(base) + N*offset²
        # Too complex analytically, just rescale
        s = np.sqrt(target_trC2 / current_trC2)
        eigs = eigs * s
        # Adjust trace
        current_trC = np.sum(eigs)
        eigs = eigs - (current_trC - trC) / N
        # Re-check Tr(C²) and iterate
    
    eigs.sort()
    return construct_matrix_from_eigenvalues(eigs, N=N)

def make_attention_matrix(N, temperature=1.0):
    """Standard attention/softmax coupling matrix."""
    X = np.random.randn(N, N)
    scores = X @ X.T / np.sqrt(N)
    C = np.exp(scores / temperature)
    C = C / C.sum(axis=1, keepdims=True)
    return C

def make_wigner_matrix(N, sigma=1.0):
    """GOE Wigner matrix."""
    A = np.random.randn(N, N) * sigma / np.sqrt(N)
    return (A + A.T) / 2

# ============================================================
# Time-varying coupling (Tr(C²) control experiment)
# ============================================================

def make_trC2_controlled_time_series(N, steps=200, mode='constant'):
    """
    Generate a time series of coupling matrices where Tr(C²) follows
    a specified trajectory.
    
    Modes:
    - 'constant': Tr(C²) held exactly constant
    - 'linear_drift': Tr(C²) drifts linearly
    - 'random_walk': Tr(C²) does random walk
    - 'sinusoidal': Tr(C²) oscillates
    """
    # Base orthogonal frame
    A = np.random.randn(N, N)
    Q, R = np.linalg.qr(A)
    Q = Q @ np.diag(np.sign(np.diag(R)))
    
    matrices = []
    base_eigs = np.random.uniform(0.5, 2.0, N)
    base_eigs.sort()
    base_trC2 = np.sum(base_eigs**2)
    
    for t in range(steps):
        if mode == 'constant':
            target_trC2 = base_trC2
        elif mode == 'linear_drift':
            target_trC2 = base_trC2 * (1.0 + 0.5 * t / steps)
        elif mode == 'random_walk':
            noise = np.random.randn() * 0.01 * base_trC2
            if t == 0:
                target_trC2 = base_trC2
            else:
                target_trC2 = matrices[-1][1] + noise  # use previous Tr(C²) + noise
        elif mode == 'sinusoidal':
            target_trC2 = base_trC2 * (1.0 + 0.3 * np.sin(2 * np.pi * t / 50))
        else:
            target_trC2 = base_trC2
        
        # Construct eigenvalues that hit target Tr(C²)
        eigs = base_eigs.copy()
        current_trC2 = np.sum(eigs**2)
        if current_trC2 > 0:
            s = np.sqrt(abs(target_trC2 / current_trC2))
            eigs = eigs * s
        
        C = Q @ np.diag(eigs) @ Q.T
        
        # Small random perturbation to eigenvectors each step (realistic dynamics)
        if t > 0:
            dQ = np.random.randn(N, N) * 0.01
            dQ = (dQ + dQ.T) / 2
            Q_new = Q + dQ
            # Re-orthogonalize via polar decomposition
            U, _, Vt = np.linalg.svd(Q_new)
            Q = U @ Vt
            C = Q @ np.diag(eigs) @ Q.T
        
        actual_trC2 = np.trace(C @ C)
        matrices.append((C, actual_trC2))
    
    return matrices

# ============================================================
# Main experiment
# ============================================================

def run_experiment():
    results = {}
    N_values = [10, 20]
    steps = 200
    n_trials = 15  # trials per configuration
    
    # ---- EXPERIMENT 1: Controlled Eigenvalue Distributions ----
    print("=" * 70)
    print("EXPERIMENT 1: Controlled Eigenvalue Distributions")
    print("=" * 70)
    
    configs = {
        'degenerate': lambda N: make_degenerate_matrix(N, eigenvalue=1.0),
        'uniform_spectrum': lambda N: make_uniform_spectrum(N, 0.5, 2.0),
        'exponential_spectrum': lambda N: make_exponential_spectrum(N, scale=1.0),
        'powerlaw_spectrum': lambda N: make_powerlaw_spectrum(N, alpha=2.0, xmin=0.1),
        'rank1_limit': lambda N: make_rank1_matrix(N, dominant=5.0, noise_scale=0.01),
        'two_cluster': lambda N: make_two_cluster_matrix(N, gap=5.0),
        'attention': lambda N: make_attention_matrix(N, temperature=1.0),
        'wigner': lambda N: make_wigner_matrix(N, sigma=1.0),
    }
    
    exp1_results = {}
    
    for N in N_values:
        print(f"\n--- N = {N} ---")
        exp1_results[N] = {}
        
        for config_name, matrix_fn in configs.items():
            trial_results = []
            
            for trial in range(n_trials):
                C = matrix_fn(N)
                eigs = np.linalg.eigvalsh(C)
                trC = np.trace(C)
                trC2 = np.trace(C @ C)
                
                x0 = np.random.randn(N)
                traj, gammas, hamiltonians = run_dynamics(C, x0, steps)
                
                gamma_plus_H = gammas + hamiltonians
                
                trial_results.append({
                    'trC': trC,
                    'trC2': trC2,
                    'eigenvalues': eigs.tolist(),
                    'gamma_plus_H': gamma_plus_H.tolist(),
                    'gammas': gammas.tolist(),
                    'hamiltonians': hamiltonians.tolist(),
                    'cv_gamma_plus_H': float(np.std(gamma_plus_H) / (np.mean(gamma_plus_H) + 1e-15)),
                    'cv_trC2': 0.0,  # static matrix, Tr(C²) is constant by definition
                    'mean_gamma_plus_H': float(np.mean(gamma_plus_H)),
                    'std_gamma_plus_H': float(np.std(gamma_plus_H)),
                    'mean_gamma': float(np.mean(gammas)),
                    'mean_H': float(np.mean(hamiltonians)),
                    'gamma_H_corr': float(np.corrcoef(gammas, hamiltonians)[0, 1]) if np.std(gammas) > 1e-10 and np.std(hamiltonians) > 1e-10 else 0.0,
                })
            
            # Aggregate
            cv_values = [t['cv_gamma_plus_H'] for t in trial_results]
            gH_corr = [t['gamma_H_corr'] for t in trial_results]
            trC2_values = [t['trC2'] for t in trial_results]
            mean_gH = [t['mean_gamma_plus_H'] for t in trial_results]
            
            # Cross-instance CV
            ci_cv = np.std(mean_gH) / (np.mean(mean_gH) + 1e-15)
            
            exp1_results[N][config_name] = {
                'mean_cv_temporal': float(np.mean(cv_values)),
                'std_cv_temporal': float(np.std(cv_values)),
                'mean_trC2': float(np.mean(trC2_values)),
                'std_trC2': float(np.std(trC2_values)),
                'cv_trC2_cross_instance': float(np.std(trC2_values) / (np.mean(trC2_values) + 1e-15)),
                'ci_cv_gamma_plus_H': float(ci_cv),
                'mean_gamma_H_corr': float(np.mean(gH_corr)),
                'trials': trial_results,
            }
            
            print(f"  {config_name:25s} | temporal_CV={np.mean(cv_values):.4f} | "
                  f"CI_CV={ci_cv:.4f} | γ-H corr={np.mean(gH_corr):.3f} | "
                  f"Tr(C²)={np.mean(trC2_values):.2f}±{np.std(trC2_values):.2f}")
    
    results['experiment_1'] = exp1_results
    
    # ---- EXPERIMENT 2: Fixed Tr(C²) — Does It Force Conservation? ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Fixing Tr(C²) Across Instances")
    print("=" * 70)
    
    exp2_results = {}
    
    for N in N_values:
        print(f"\n--- N = {N} ---")
        exp2_results[N] = {}
        
        # Compute attention's Tr(C²) as reference
        att_trC2_values = []
        for _ in range(50):
            C = make_attention_matrix(N)
            att_trC2_values.append(np.trace(C @ C))
        att_trC2_mean = np.mean(att_trC2_values)
        
        # Test different target Tr(C²) values
        target_trC2_values = [
            att_trC2_mean * 0.5,
            att_trC2_mean,
            att_trC2_mean * 2.0,
            att_trC2_mean * 5.0,
        ]
        
        for target_trC2 in target_trC2_values:
            trial_results = []
            
            for trial in range(n_trials):
                C = make_fixed_trC2_matrix(N, target_trC2)
                eigs = np.linalg.eigvalsh(C)
                
                x0 = np.random.randn(N)
                traj, gammas, hamiltonians = run_dynamics(C, x0, steps)
                gamma_plus_H = gammas + hamiltonians
                
                trial_results.append({
                    'trC2': float(np.trace(C @ C)),
                    'mean_gamma_plus_H': float(np.mean(gamma_plus_H)),
                    'cv_gamma_plus_H': float(np.std(gamma_plus_H) / (np.mean(gamma_plus_H) + 1e-15)),
                    'gamma_H_corr': float(np.corrcoef(gammas, hamiltonians)[0, 1]) if np.std(gammas) > 1e-10 and np.std(hamiltonians) > 1e-10 else 0.0,
                })
            
            mean_gH = [t['mean_gamma_plus_H'] for t in trial_results]
            ci_cv = np.std(mean_gH) / (np.mean(mean_gH) + 1e-15)
            
            label = f"trC2_{target_trC2/att_trC2_mean:.1f}x_att"
            exp2_results[N][label] = {
                'target_trC2': float(target_trC2),
                'mean_trC2_actual': float(np.mean([t['trC2'] for t in trial_results])),
                'mean_cv_temporal': float(np.mean([t['cv_gamma_plus_H'] for t in trial_results])),
                'ci_cv_gamma_plus_H': float(ci_cv),
                'mean_gamma_H_corr': float(np.mean([t['gamma_H_corr'] for t in trial_results])),
            }
            
            print(f"  target Tr(C²)={target_trC2:.2f} ({target_trC2/att_trC2_mean:.1f}x attn) | "
                  f"CI_CV={ci_cv:.4f} | temporal_CV={exp2_results[N][label]['mean_cv_temporal']:.4f}")
    
    results['experiment_2'] = exp2_results
    
    # ---- EXPERIMENT 3: Time-Varying Coupling with Tr(C²) Control ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Time-Varying Coupling — Tr(C²) Control")
    print("=" * 70)
    
    exp3_results = {}
    N = 20
    modes = ['constant', 'linear_drift', 'random_walk', 'sinusoidal']
    n_trials_tv = 10
    
    for mode in modes:
        print(f"\n--- Mode: {mode} ---")
        mode_results = []
        
        for trial in range(n_trials_tv):
            matrices = make_trC2_controlled_time_series(N, steps, mode)
            x0 = np.random.randn(N)
            x = x0.copy()
            
            gammas = np.zeros(steps)
            hamiltonians = np.zeros(steps)
            trC2_series = np.zeros(steps)
            
            for t in range(steps):
                C, actual_trC2 = matrices[t]
                trC2_series[t] = actual_trC2
                g, h = gamma_hamiltonian(x, C)
                gammas[t] = g
                hamiltonians[t] = h
                x = np.tanh(C @ x)
            
            gamma_plus_H = gammas + hamiltonians
            cv_gh = np.std(gamma_plus_H) / (np.mean(gamma_plus_H) + 1e-15)
            cv_trC2 = np.std(trC2_series) / (np.mean(trC2_series) + 1e-15)
            gh_trC2_corr = np.corrcoef(gamma_plus_H, trC2_series)[0, 1] if np.std(trC2_series) > 1e-10 else 0.0
            
            mode_results.append({
                'cv_gamma_plus_H': float(cv_gh),
                'cv_trC2': float(cv_trC2),
                'gh_trC2_corr': float(gh_trC2_corr),
                'mean_gamma_plus_H': float(np.mean(gamma_plus_H)),
                'gamma_H_corr': float(np.corrcoef(gammas, hamiltonians)[0, 1]) if np.std(gammas) > 1e-10 and np.std(hamiltonians) > 1e-10 else 0.0,
            })
        
        exp3_results[mode] = {
            'mean_cv_gh': float(np.mean([r['cv_gamma_plus_H'] for r in mode_results])),
            'mean_cv_trC2': float(np.mean([r['cv_trC2'] for r in mode_results])),
            'mean_gh_trC2_corr': float(np.mean([r['gh_trC2_corr'] for r in mode_results])),
            'mean_gamma_H_corr': float(np.mean([r['gamma_H_corr'] for r in mode_results])),
            'trials': mode_results,
        }
        
        print(f"  CV(γ+H) = {exp3_results[mode]['mean_cv_gh']:.4f} | "
              f"CV(Tr(C²)) = {exp3_results[mode]['mean_cv_trC2']:.4f} | "
              f"corr(γ+H, Tr(C²)) = {exp3_results[mode]['mean_gh_trC2_corr']:.3f}")
    
    results['experiment_3'] = exp3_results
    
    # ---- EXPERIMENT 4: Two-Moment Regression ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Two-Moment Regression — Tr(C) + Tr(C²) → γ+H")
    print("=" * 70)
    
    exp4_results = {}
    
    for N in N_values:
        print(f"\n--- N = {N} ---")
        
        # Generate diverse matrices
        all_trC = []
        all_trC2 = []
        all_mean_gH = []
        labels = []
        
        matrix_generators = [
            ('degenerate', lambda: make_degenerate_matrix(N, 1.0)),
            ('uniform', lambda: make_uniform_spectrum(N, 0.5, 2.0)),
            ('exponential', lambda: make_exponential_spectrum(N, 1.0)),
            ('powerlaw', lambda: make_powerlaw_spectrum(N, 2.0, 0.1)),
            ('rank1', lambda: make_rank1_matrix(N, 5.0, 0.01)),
            ('two_cluster', lambda: make_two_cluster_matrix(N, 5.0)),
            ('attention', lambda: make_attention_matrix(N)),
            ('wigner', lambda: make_wigner_matrix(N)),
        ]
        
        n_per_type = 20
        
        for name, gen_fn in matrix_generators:
            for _ in range(n_per_type):
                C = gen_fn()
                trC = np.trace(C)
                trC2 = np.trace(C @ C)
                
                x0 = np.random.randn(N)
                traj, gammas, hamiltonians = run_dynamics(C, x0, steps)
                mean_gH = np.mean(gammas + hamiltonians)
                
                all_trC.append(trC)
                all_trC2.append(trC2)
                all_mean_gH.append(mean_gH)
                labels.append(name)
        
        all_trC = np.array(all_trC)
        all_trC2 = np.array(all_trC2)
        all_mean_gH = np.array(all_mean_gH)
        
        # Regression: γ+H = a*Tr(C) + b*Tr(C²) + c
        X = np.column_stack([all_trC, all_trC2, np.ones(len(all_trC))])
        coeffs, residuals, _, _ = np.linalg.lstsq(X, all_mean_gH, rcond=None)
        
        predicted = X @ coeffs
        ss_res = np.sum((all_mean_gH - predicted)**2)
        ss_tot = np.sum((all_mean_gH - np.mean(all_mean_gH))**2)
        r2_full = 1 - ss_res / ss_tot
        
        # Also test Tr(C²) alone
        X_trC2 = np.column_stack([all_trC2, np.ones(len(all_trC2))])
        coeffs_trC2, _, _, _ = np.linalg.lstsq(X_trC2, all_mean_gH, rcond=None)
        pred_trC2 = X_trC2 @ coeffs_trC2
        r2_trC2 = 1 - np.sum((all_mean_gH - pred_trC2)**2) / ss_tot
        
        # And Tr(C) alone
        X_trC = np.column_stack([all_trC, np.ones(len(all_trC))])
        coeffs_trC, _, _, _ = np.linalg.lstsq(X_trC, all_mean_gH, rcond=None)
        pred_trC = X_trC @ coeffs_trC
        r2_trC = 1 - np.sum((all_mean_gH - pred_trC)**2) / ss_tot
        
        exp4_results[N] = {
            'r2_trC_only': float(r2_trC),
            'r2_trC2_only': float(r2_trC2),
            'r2_both': float(r2_full),
            'coeffs_both': coeffs.tolist(),
            'n_samples': len(all_trC),
        }
        
        print(f"  R²(Tr(C) → γ+H) = {r2_trC:.4f}")
        print(f"  R²(Tr(C²) → γ+H) = {r2_trC2:.4f}")
        print(f"  R²(Tr(C) + Tr(C²) → γ+H) = {r2_full:.4f}")
        print(f"  Coefficients: a={coeffs[0]:.4f}, b={coeffs[1]:.4f}, c={coeffs[2]:.4f}")
    
    results['experiment_4'] = exp4_results
    
    # ---- EXPERIMENT 5: Minimal Constraint Search ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 5: Minimal Constraint — What's Needed for Conservation?")
    print("=" * 70)
    
    N = 20
    exp5_results = {}
    
    # Vary eigenvalue spread (controlled by Tr(C²)) while keeping Tr(C) = N
    spread_factors = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
    
    for spread in spread_factors:
        trial_results = []
        
        for trial in range(n_trials):
            # Base eigenvalues centered around 1.0
            base_eigs = np.random.uniform(1.0 - spread, 1.0 + spread, N)
            # Force Tr(C) = N
            base_eigs = base_eigs - (np.sum(base_eigs) - N) / N
            
            C = construct_matrix_from_eigenvalues(base_eigs, N=N)
            
            trC = np.trace(C)
            trC2 = np.trace(C @ C)
            eig_std = np.std(np.linalg.eigvalsh(C))
            
            x0 = np.random.randn(N)
            traj, gammas, hamiltonians = run_dynamics(C, x0, steps)
            gamma_plus_H = gammas + hamiltonians
            
            trial_results.append({
                'trC': float(trC),
                'trC2': float(trC2),
                'eig_std': float(eig_std),
                'cv_gamma_plus_H': float(np.std(gamma_plus_H) / (np.mean(gamma_plus_H) + 1e-15)),
                'mean_gamma_plus_H': float(np.mean(gamma_plus_H)),
            })
        
        cvs = [t['cv_gamma_plus_H'] for t in trial_results]
        trC2s = [t['trC2'] for t in trial_results]
        estds = [t['eig_std'] for t in trial_results]
        mean_gHs = [t['mean_gamma_plus_H'] for t in trial_results]
        ci_cv = np.std(mean_gHs) / (np.mean(mean_gHs) + 1e-15)
        
        exp5_results[f"spread_{spread}"] = {
            'spread_factor': spread,
            'mean_trC2': float(np.mean(trC2s)),
            'mean_eig_std': float(np.mean(estds)),
            'mean_temporal_cv': float(np.mean(cvs)),
            'ci_cv': float(ci_cv),
        }
        
        print(f"  spread={spread:5.1f} | Tr(C²)={np.mean(trC2s):7.2f} | "
              f"eig_std={np.mean(estds):.3f} | temporal_CV={np.mean(cvs):.4f} | CI_CV={ci_cv:.4f}")
    
    results['experiment_5'] = exp5_results
    
    # ---- EXPERIMENT 6: Degenerate Matrix Deep Dive ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 6: Degenerate Matrix — Conservation at Maximum Degeneracy")
    print("=" * 70)
    
    exp6_results = {}
    
    for N in N_values:
        trial_results = []
        
        for trial in range(n_trials):
            # C = identity matrix (all eigenvalues = 1, maximum degeneracy)
            C = np.eye(N)
            
            x0 = np.random.randn(N)
            traj, gammas, hamiltonians = run_dynamics(C, x0, steps)
            gamma_plus_H = gammas + hamiltonians
            
            trial_results.append({
                'cv_gamma_plus_H': float(np.std(gamma_plus_H) / (np.mean(gamma_plus_H) + 1e-15)),
                'gamma_H_corr': float(np.corrcoef(gammas, hamiltonians)[0, 1]) if np.std(gammas) > 1e-10 and np.std(hamiltonians) > 1e-10 else 0.0,
                'mean_gamma': float(np.mean(gammas)),
                'mean_H': float(np.mean(hamiltonians)),
            })
        
        exp6_results[N] = {
            'mean_cv': float(np.mean([t['cv_gamma_plus_H'] for t in trial_results])),
            'mean_gamma_H_corr': float(np.mean([t['gamma_H_corr'] for t in trial_results])),
        }
        
        print(f"  N={N} | C=I | temporal_CV={exp6_results[N]['mean_cv']:.4f} | "
              f"γ-H corr={exp6_results[N]['mean_gamma_H_corr']:.3f}")
    
    # Also test with scalar * identity
    print("\n  Scalar * Identity:")
    exp6_scalar = {}
    for scalar in [0.1, 0.5, 1.0, 2.0, 5.0]:
        N = 20
        trial_cvs = []
        for trial in range(n_trials):
            C = scalar * np.eye(N)
            x0 = np.random.randn(N)
            traj, gammas, hamiltonians = run_dynamics(C, x0, steps)
            gamma_plus_H = gammas + hamiltonians
            trial_cvs.append(float(np.std(gamma_plus_H) / (np.mean(gamma_plus_H) + 1e-15)))
        
        exp6_scalar[scalar] = float(np.mean(trial_cvs))
        print(f"    C={scalar}*I | temporal_CV={np.mean(trial_cvs):.4f}")
    
    exp6_results['scalar_identity'] = exp6_scalar
    results['experiment_6'] = exp6_results
    
    # ---- Save Results ----
    output_path = RESULTS_DIR / "engineered-results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to {output_path}")
    
    # ---- Summary ----
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print("\n[Exp 1] Temporal CV by eigenvalue distribution (N=20):")
    if 20 in exp1_results:
        for name, data in sorted(exp1_results[20].items(), key=lambda x: x[1]['mean_cv_temporal']):
            print(f"  {name:25s} | temporal_CV={data['mean_cv_temporal']:.4f} | CI_CV={data['ci_cv_gamma_plus_H']:.4f}")
    
    print("\n[Exp 3] Time-varying coupling: CV(γ+H) vs CV(Tr(C²))")
    for mode, data in exp3_results.items():
        print(f"  {mode:20s} | CV(γ+H)={data['mean_cv_gh']:.4f} | CV(Tr(C²))={data['mean_cv_trC2']:.4f} | corr={data['mean_gh_trC2_corr']:.3f}")
    
    print("\n[Exp 4] Two-moment regression:")
    for N, data in exp4_results.items():
        print(f"  N={N}: R²(Tr(C))={data['r2_trC_only']:.4f} | R²(Tr(C²))={data['r2_trC2_only']:.4f} | R²(both)={data['r2_both']:.4f}")
    
    print("\n[Exp 5] Conservation vs eigenvalue spread (N=20, Tr(C)=N fixed):")
    for name, data in sorted(exp5_results.items(), key=lambda x: x[1]['spread_factor']):
        print(f"  spread={data['spread_factor']:5.1f} | Tr(C²)={data['mean_trC2']:7.2f} | temporal_CV={data['mean_temporal_cv']:.4f} | CI_CV={data['ci_cv']:.4f}")
    
    return results

if __name__ == '__main__':
    t0 = time.time()
    results = run_experiment()
    elapsed = time.time() - t0
    print(f"\nTotal runtime: {elapsed:.1f}s")
