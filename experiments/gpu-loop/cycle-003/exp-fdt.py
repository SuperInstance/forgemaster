#!/usr/bin/env python3
"""
Fluctuation-Dissipation Theorem Test for Coupled Agent Systems
==============================================================

Tests whether the thermodynamic mapping holds:
  γ (spectral gap) ↔ Temperature (T)
  H (entropy)      ↔ Entropy (S)
  C (γ + H)        ↔ Free Energy (F)

The Fluctuation-Dissipation Theorem (FDT) states:
  ⟨δA(t)δA(0)⟩ = kT · χ(t)

where the autocorrelation of fluctuations relates to the linear response
function through temperature.

If FDT holds for our system, then:
  1. ⟨δγ(t)δγ(0)⟩ should predict the H response function
  2. C = γ + H should hold with the same thermodynamic consistency
  3. The effective "temperature" kT should be extractable and architecture-dependent

Author: Forgemaster ⚒️ (research subagent)
Date: 2026-05-17
"""

import numpy as np
from numpy.linalg import eigvalsh
from scipy.linalg import expm
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
np.random.seed(42)

RESULTS_DIR = Path(__file__).parent
RESULTS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Matrix Generation
# ============================================================================

def make_random_coupling(N):
    """GOE random matrix (Wigner). Maximal eigenvalue repulsion."""
    A = np.random.randn(N, N)
    return (A + A.T) / (2 * np.sqrt(N))

def make_hebbian_coupling(N, n_patterns=None):
    """Hebbian coupling from stored patterns. Prone to eigenvalue degeneracy."""
    if n_patterns is None:
        n_patterns = max(3, N // 3)
    patterns = np.random.choice([-1, 1], size=(n_patterns, N))
    W = patterns.T @ patterns / N
    np.fill_diagonal(W, 0)
    return W / np.linalg.norm(W, ord=2)

def make_attention_coupling(N, d=None):
    """Attention-style coupling. Structured but non-degenerate."""
    if d is None:
        d = max(4, N // 4)
    Q = np.random.randn(N, d) / np.sqrt(d)
    K = np.random.randn(N, d) / np.sqrt(d)
    W = Q @ K.T / np.sqrt(d)
    W = (W + W.T) / 2  # symmetrize for real eigenvalues
    return W / np.linalg.norm(W, ord=2)

# ============================================================================
# State Evolution
# ============================================================================

def evolve_system(W, x0, n_steps, dt=0.01, beta=1.0):
    """
    Evolve state vector under coupling matrix W.
    
    dx/dt = -β W x + η(t)  (Langevin dynamics)
    
    Returns time series of state vectors and observables.
    """
    N = W.shape[0]
    states = np.zeros((n_steps, N))
    states[0] = x0.copy()
    
    noise_scale = np.sqrt(2 * dt)  # diffusion coefficient
    
    for t in range(1, n_steps):
        # Langevin update: drift toward equilibrium + thermal noise
        drift = -beta * W @ states[t-1] * dt
        noise = noise_scale * np.random.randn(N)
        states[t] = states[t-1] + drift + noise
    
    return states

# ============================================================================
# Observable Computation
# ============================================================================

def compute_spectral_gap(W, x):
    """
    Compute effective spectral gap γ from coupling and state.
    γ measures how strongly the current state couples to the slowest mode.
    """
    eigenvalues = eigvalsh(W)
    # Sort descending
    eigenvalues = np.sort(eigenvalues)[::-1]
    
    # Spectral gap: difference between largest and second-largest eigenvalue
    if len(eigenvalues) > 1:
        gamma = eigenvalues[0] - eigenvalues[1]
    else:
        gamma = eigenvalues[0]
    
    return max(gamma, 1e-10)

def compute_state_spectral_gap(W, x):
    """
    Compute γ from the instantaneous coupling matrix scaled by state energy.
    This gives a dynamic spectral gap that varies with time.
    """
    eigenvalues = eigvalsh(W)
    eigenvalues = np.sort(eigenvalues)[::-1]
    
    # Weight by how much the state projects onto each eigenvector
    _, eigvecs = np.linalg.eigh(W)
    # eigvecs columns are eigenvectors, sorted ascending
    eigvecs = eigvecs[:, ::-1]  # now descending
    
    projections = np.abs(eigvecs.T @ x)
    weights = projections / (np.sum(projections) + 1e-15)
    
    # Effective spectral gap weighted by state projection
    if len(eigenvalues) > 1:
        # Gap between most-occupied eigenvalue and next
        sorted_idx = np.argsort(weights)[::-1]
        i0 = sorted_idx[0]
        i1 = sorted_idx[1] if len(sorted_idx) > 1 else 0
        gamma = abs(eigenvalues[i0] - eigenvalues[i1])
    else:
        gamma = eigenvalues[0]
    
    return max(gamma, 1e-10)

def compute_entropy(W, x):
    """
    Compute entropy-like quantity from coupling matrix and state.
    
    H = -Σ pᵢ ln(pᵢ) where pᵢ are normalized eigenvalue weights of W
    This is the spectral entropy.
    """
    eigenvalues = eigvalsh(W)
    
    # Use absolute eigenvalues as "energies", compute Boltzmann weights
    abs_evals = np.abs(eigenvalues)
    total = np.sum(abs_evals)
    if total < 1e-15:
        return 0.0
    
    probs = abs_evals / total
    probs = probs[probs > 1e-15]  # avoid log(0)
    
    H = -np.sum(probs * np.log(probs))
    return H

def compute_state_entropy(W, x):
    """
    Compute dynamic entropy from state-conditioned spectral distribution.
    
    H(x) = -Σ wᵢ(x) ln(wᵢ(x)) where wᵢ are state-dependent weights.
    """
    eigenvalues, eigvecs = np.linalg.eigh(W)
    
    # State projection onto each eigenmode
    projections = np.abs(eigvecs.T @ x) ** 2  # energy in each mode
    total_energy = np.sum(projections)
    if total_energy < 1e-15:
        return np.log(len(x))
    
    weights = projections / total_energy
    weights = weights[weights > 1e-15]
    
    H = -np.sum(weights * np.log(weights))
    return H

def compute_coupling_entropy(W):
    """
    Static spectral entropy of the coupling matrix.
    H = -Σ pᵢ ln(pᵢ) from eigenvalue distribution.
    """
    eigenvalues = eigvalsh(W)
    abs_evals = np.abs(eigenvalues)
    total = np.sum(abs_evals)
    if total < 1e-15:
        return 0.0
    probs = abs_evals / total
    probs = probs[probs > 1e-15]
    return -np.sum(probs * np.log(probs))

# ============================================================================
# FDT Tests
# ============================================================================

def compute_autocorrelation(series, max_lag=None):
    """Compute normalized autocorrelation function."""
    n = len(series)
    if max_lag is None:
        max_lag = n // 4
    max_lag = min(max_lag, n // 4)
    
    series = series - np.mean(series)
    var = np.var(series)
    if var < 1e-15:
        return np.zeros(max_lag)
    
    acf = np.zeros(max_lag)
    for lag in range(max_lag):
        if lag == 0:
            acf[0] = 1.0
        else:
            acf[lag] = np.mean(series[:n-lag] * series[lag:]) / var
    
    return acf

def compute_cross_correlation(series_a, series_b, max_lag=None):
    """Compute cross-correlation between two time series."""
    n = min(len(series_a), len(series_b))
    if max_lag is None:
        max_lag = n // 4
    max_lag = min(max_lag, n // 4)
    
    a = series_a[:n] - np.mean(series_a[:n])
    b = series_b[:n] - np.mean(series_b[:n])
    
    std_a = np.std(a)
    std_b = np.std(b)
    if std_a < 1e-15 or std_b < 1e-15:
        return np.zeros(max_lag)
    
    ccf = np.zeros(max_lag)
    for lag in range(max_lag):
        ccf[lag] = np.mean(a[:n-lag] * b[lag:]) / (std_a * std_b)
    
    return ccf

def compute_response_function(perturb_series, max_lag=None):
    """
    Compute linear response function from perturbation response.
    χ(t) = ⟨δH(t)⟩ after a δγ kick at t=0.
    """
    n = len(perturb_series)
    if max_lag is None:
        max_lag = n // 4
    max_lag = min(max_lag, n // 4)
    
    # Response = mean relaxation after perturbation
    baseline = np.mean(perturb_series[-n//4:])
    response = np.zeros(max_lag)
    for lag in range(max_lag):
        response[lag] = perturb_series[lag] - baseline
    
    return response

def test_fdt(gamma_series, H_series, C_series):
    """
    Core FDT test:
    
    If γ = T and H = S, then FDT predicts:
      ⟨δγ(t)δγ(0)⟩ = kT_eff · χ_H(t)
    
    where χ_H is the H response to a γ perturbation.
    
    We test multiple predictions:
    1. γ-H cross-correlation structure
    2. Fluctuation amplitude ∝ temperature
    3. Conservation C = γ + H as thermodynamic first law
    4. Heat capacity (∂C/∂γ) consistency
    """
    results = {}
    
    # --- Test 1: γ+H Conservation (First Law) ---
    C_mean = np.mean(C_series)
    C_std = np.std(C_series)
    C_cv = C_std / C_mean if abs(C_mean) > 1e-15 else float('inf')
    results['conservation'] = {
        'C_mean': float(C_mean),
        'C_std': float(C_std),
        'C_cv': float(C_cv),
        'first_law_holds': C_cv < 0.1,  # CV < 10% means conservation
    }
    
    # --- Test 2: Autocorrelation functions ---
    max_lag = min(100, len(gamma_series) // 4)
    acf_gamma = compute_autocorrelation(gamma_series, max_lag)
    acf_H = compute_autocorrelation(H_series, max_lag)
    
    results['autocorrelation'] = {
        'gamma_decay_rate': float(-np.log(np.abs(acf_gamma[1]) + 1e-10)),
        'H_decay_rate': float(-np.log(np.abs(acf_H[1]) + 1e-10)),
        'gamma_memory': float(np.sum(np.abs(acf_gamma[:20]))),
        'H_memory': float(np.sum(np.abs(acf_H[:20]))),
    }
    
    # --- Test 3: Cross-correlation (γ → H coupling) ---
    ccf_gh = compute_cross_correlation(gamma_series, H_series, max_lag)
    ccf_hg = compute_cross_correlation(H_series, gamma_series, max_lag)
    
    # FDT predicts CCF should be asymmetric: γ leads, H follows
    results['cross_correlation'] = {
        'max_ccf_gh': float(np.max(np.abs(ccf_gh))),
        'max_ccf_hg': float(np.max(np.abs(ccf_hg))),
        'lag_max_ccf_gh': int(np.argmax(np.abs(ccf_gh))),
        'lag_max_ccf_hg': int(np.argmax(np.abs(ccf_hg))),
        'asymmetry': float(np.max(np.abs(ccf_gh)) - np.max(np.abs(ccf_hg))),
        'ccf_gh_first5': [float(x) for x in ccf_gh[:5]],
        'ccf_hg_first5': [float(x) for x in ccf_hg[:5]],
    }
    
    # --- Test 4: Effective Temperature ---
    # From equipartition: ⟨(δγ)²⟩ = kT_eff
    # From FDT: ⟨δγ(t)δγ(0)⟩ / χ(t) = kT_eff
    gamma_var = np.var(gamma_series)
    kT_eff_variance = gamma_var  # kT from variance (equipartition)
    
    # Also from C = γ + H: dH/dγ should equal -1 if perfect conservation
    # Test with linear regression
    if np.var(gamma_series) > 1e-15:
        slope_dH_dgamma = np.polyfit(gamma_series, H_series, 1)[0]
    else:
        slope_dH_dgamma = 0.0
    
    results['effective_temperature'] = {
        'kT_from_variance': float(kT_eff_variance),
        'gamma_mean': float(np.mean(gamma_series)),
        'gamma_std': float(np.std(gamma_series)),
        'H_mean': float(np.mean(H_series)),
        'H_std': float(np.std(H_series)),
        'slope_dH_dgamma': float(slope_dH_dgamma),
        'slope_is_minus_one': abs(slope_dH_dgamma + 1.0) < 0.3,
    }
    
    # --- Test 5: FDT Ratio Test ---
    # FDT: autocorrelation / response = kT
    # Use γ autocorrelation as "fluctuation" and H time derivative as "dissipation"
    dH_dt = np.diff(H_series)
    gamma_mid = gamma_series[:-1]
    
    if np.var(dH_dt) > 1e-15 and np.var(gamma_mid) > 1e-15:
        # Response function: how does H respond to γ changes?
        # If FDT holds: ⟨δγ(t)δγ(0)⟩ = kT · ⟨dH/dt(t)·δγ(0)⟩
        # Simplified: Corr(γ(t), γ(0)) / Corr(dH/dt(t), γ(0)) = kT
        
        # Cross-correlation of dH/dt with γ
        ccf_dHdt_gamma = compute_cross_correlation(dH_dt, gamma_mid, min(50, max_lag))
        
        # FDT ratio: acf_gamma(t) / ccf_dHdt_gamma(t) should = kT (constant)
        # Only use points where both are significant
        valid = (np.abs(ccf_dHdt_gamma) > 0.01) & (np.abs(acf_gamma[:len(ccf_dHdt_gamma)]) > 0.01)
        if np.sum(valid) > 2:
            fdt_ratios = acf_gamma[:len(ccf_dHdt_gamma)][valid] / ccf_dHdt_gamma[valid]
            fdt_ratio_cv = np.std(fdt_ratios) / (np.abs(np.mean(fdt_ratios)) + 1e-15)
        else:
            fdt_ratios = np.array([0.0])
            fdt_ratio_cv = float('inf')
        
        results['fdt_ratio'] = {
            'mean_ratio': float(np.mean(fdt_ratios)),
            'std_ratio': float(np.std(fdt_ratios)),
            'cv_ratio': float(fdt_ratio_cv),
            'fdt_holds': fdt_ratio_cv < 0.5,  # ratio is approximately constant
            'n_valid_points': int(np.sum(valid)),
        }
    else:
        results['fdt_ratio'] = {
            'mean_ratio': 0.0,
            'std_ratio': 0.0,
            'cv_ratio': float('inf'),
            'fdt_holds': False,
            'n_valid_points': 0,
        }
    
    # --- Test 6: Fluctuation Magnitude vs Temperature ---
    # In thermodynamics: ⟨(δT)²⟩ ∝ T² / Cv
    # If γ = T, then σ_γ² should scale with γ_mean²
    
    results['fluctuation_scaling'] = {
        'sigma_gamma': float(np.std(gamma_series)),
        'mean_gamma': float(np.mean(gamma_series)),
        'ratio_sigma_to_mean': float(np.std(gamma_series) / (np.mean(gamma_series) + 1e-15)),
        'thermodynamic_scaling': float(np.var(gamma_series) / (np.mean(gamma_series)**2 + 1e-15)),
    }
    
    # --- Test 7: Onsager Reciprocity ---
    # If the system is thermodynamic, cross-correlations should satisfy Onsager:
    # CCF(γ→H, lag) = CCF(H→γ, -lag)  [time-reversal symmetry]
    # Check if ccf_gh[lag] ≈ ccf_hg[lag] (symmetric under exchange)
    onsager_error = np.mean((ccf_gh[:20] - ccf_hg[:20])**2)
    results['onsager'] = {
        'reciprocity_error': float(onsager_error),
        'reciprocity_holds': onsager_error < 0.1,
    }
    
    return results

# ============================================================================
# Perturbation Response Test (Dynamic FDT)
# ============================================================================

def perturbation_response_test(W, n_equilibrium=1000, n_perturbed=200, 
                                perturbation_scale=0.1, dt=0.01, beta=1.0,
                                n_trials=50):
    """
    Test FDT by applying perturbations and measuring response.
    
    1. Evolve to equilibrium
    2. Apply a small perturbation to γ (modify spectral gap)
    3. Measure H(t) response
    4. Compare with γ fluctuation autocorrelation
    
    FDT predicts: ⟨δH(t)⟩_pert = β_eff · ⟨δγ(t)δγ(0)⟩
    """
    N = W.shape[0]
    
    # Equilibrium fluctuations (no perturbation)
    gamma_eq = []
    H_eq = []
    
    for trial in range(n_trials):
        x0 = np.random.randn(N)
        states = evolve_system(W, x0, n_equilibrium, dt, beta)
        
        for t in range(n_equilibrium // 2, n_equilibrium):
            gamma_eq.append(compute_state_spectral_gap(W, states[t]))
            H_eq.append(compute_state_entropy(W, states[t]))
    
    gamma_eq = np.array(gamma_eq)
    H_eq = np.array(H_eq)
    
    # Autocorrelation of equilibrium γ fluctuations
    delta_gamma = gamma_eq - np.mean(gamma_eq)
    max_lag = min(50, len(delta_gamma) // 4)
    acf_delta_gamma = compute_autocorrelation(delta_gamma, max_lag)
    
    # Perturbation response
    H_responses = np.zeros((n_trials, n_perturbed))
    
    for trial in range(n_trials):
        # Evolve to equilibrium
        x0 = np.random.randn(N)
        states_eq = evolve_system(W, x0, n_equilibrium, dt, beta)
        x_eq = states_eq[-1]
        
        # Apply perturbation: kick the state in the direction of the first eigenvector
        eigenvalues, eigvecs = np.linalg.eigh(W)
        eigvecs = eigvecs[:, ::-1]  # descending
        v1 = eigvecs[:, 0]  # top eigenvector
        
        x_perturbed = x_eq + perturbation_scale * v1 * np.linalg.norm(x_eq)
        
        # Measure H(t) after perturbation
        states_pert = evolve_system(W, x_perturbed, n_perturbed, dt, beta)
        for t in range(n_perturbed):
            H_responses[trial, t] = compute_state_entropy(W, states_pert[t])
    
    # Average response
    mean_H_response = np.mean(H_responses, axis=0)
    H_baseline = np.mean(H_eq)
    delta_H_response = mean_H_response - H_baseline
    
    # Normalize
    response_norm = np.max(np.abs(delta_H_response))
    if response_norm > 1e-15:
        delta_H_response_norm = delta_H_response / response_norm
    else:
        delta_H_response_norm = delta_H_response
    
    acf_norm = acf_delta_gamma[:len(delta_H_response_norm)]
    acf_max = np.max(np.abs(acf_norm))
    if acf_max > 1e-15:
        acf_norm = acf_norm / acf_max
    
    # FDT comparison: shape of response should match shape of fluctuation autocorrelation
    min_len = min(len(acf_norm), len(delta_H_response_norm))
    if min_len > 2:
        # Correlation between shapes
        shape_corr = np.corrcoef(acf_norm[:min_len], delta_H_response_norm[:min_len])[0, 1]
    else:
        shape_corr = 0.0
    
    return {
        'perturbation_scale': perturbation_scale,
        'n_trials': n_trials,
        'shape_correlation': float(shape_corr) if not np.isnan(shape_corr) else 0.0,
        'shape_match': abs(shape_corr) > 0.5 if not np.isnan(shape_corr) else False,
        'gamma_mean': float(np.mean(gamma_eq)),
        'gamma_std': float(np.std(gamma_eq)),
        'H_mean': float(np.mean(H_eq)),
        'H_std': float(np.std(H_eq)),
        'max_response': float(np.max(np.abs(delta_H_response))),
        'acf_gamma_first5': [float(x) for x in acf_delta_gamma[:5]],
        'response_first5': [float(x) for x in delta_H_response[:5]],
    }

# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment():
    """Run the full FDT experiment across architectures."""
    
    print("=" * 70)
    print("FLUCTUATION-DISSIPATION THEOREM TEST")
    print("GPU Constraint Experiment Loop — Cycle 3")
    print("=" * 70)
    
    all_results = {}
    
    configs = {
        'random': {'gen': make_random_coupling, 'label': 'GOE (Random)'},
        'attention': {'gen': make_attention_coupling, 'label': 'Attention'},
        'hebbian': {'gen': make_hebbian_coupling, 'label': 'Hebbian'},
    }
    
    N = 20  # system size
    n_steps = 5000  # evolution steps
    dt = 0.01
    beta = 1.0
    n_samples = 10  # number of independent samples per architecture
    
    for name, config in configs.items():
        print(f"\n{'='*60}")
        print(f"Architecture: {config['label']}")
        print(f"{'='*60}")
        
        gen = config['gen']
        
        # Accumulate time series across samples
        all_gamma = []
        all_H = []
        all_C = []
        
        for sample in range(n_samples):
            W = gen(N)
            
            # Equilibration + production
            x0 = np.random.randn(N)
            states = evolve_system(W, x0, n_steps, dt, beta)
            
            # Compute observables from production phase (skip equilibration)
            equil = n_steps // 4
            gamma_t = []
            H_t = []
            
            for t in range(equil, n_steps):
                g = compute_state_spectral_gap(W, states[t])
                h = compute_state_entropy(W, states[t])
                gamma_t.append(g)
                H_t.append(h)
            
            gamma_t = np.array(gamma_t)
            H_t = np.array(H_t)
            C_t = gamma_t + H_t
            
            all_gamma.append(gamma_t)
            all_H.append(H_t)
            all_C.append(C_t)
        
        # Concatenate across samples
        gamma_series = np.concatenate(all_gamma)
        H_series = np.concatenate(all_H)
        C_series = np.concatenate(all_C)
        
        print(f"  Samples: {n_samples}, Points per sample: {n_steps - n_steps//4}")
        print(f"  γ: mean={np.mean(gamma_series):.6f}, std={np.std(gamma_series):.6f}")
        print(f"  H: mean={np.mean(H_series):.6f}, std={np.std(H_series):.6f}")
        print(f"  C: mean={np.mean(C_series):.6f}, std={np.std(C_series):.6f}")
        
        # Run FDT tests
        print(f"\n  Running FDT tests...")
        fdt_results = test_fdt(gamma_series, H_series, C_series)
        
        # Run perturbation test
        print(f"  Running perturbation response test...")
        W_test = gen(N)
        perturb_results = perturbation_response_test(
            W_test, n_equilibrium=1000, n_perturbed=200,
            perturbation_scale=0.1, dt=dt, beta=beta, n_trials=30
        )
        
        # Summary
        print(f"\n  --- Results ---")
        print(f"  Conservation C=γ+H: CV = {fdt_results['conservation']['C_cv']:.6f} "
              f"({'HOLDS' if fdt_results['conservation']['first_law_holds'] else 'FAILS'})")
        print(f"  dH/dγ slope: {fdt_results['effective_temperature']['slope_dH_dgamma']:.4f} "
              f"(expect -1.0 for perfect conservation)")
        print(f"  Effective kT: {fdt_results['effective_temperature']['kT_from_variance']:.6f}")
        print(f"  σ_γ/γ: {fdt_results['fluctuation_scaling']['ratio_sigma_to_mean']:.4f}")
        print(f"  γ-H cross-corr: {fdt_results['cross_correlation']['max_ccf_gh']:.4f}")
        print(f"  FDT ratio constancy: CV = {fdt_results['fdt_ratio']['cv_ratio']:.4f} "
              f"({'HOLDS' if fdt_results['fdt_ratio']['fdt_holds'] else 'FAILS'})")
        print(f"  Onsager reciprocity: error = {fdt_results['onsager']['reciprocity_error']:.6f} "
              f"({'HOLDS' if fdt_results['onsager']['reciprocity_holds'] else 'FAILS'})")
        print(f"  Perturbation shape corr: {perturb_results['shape_correlation']:.4f} "
              f"({'MATCH' if perturb_results['shape_match'] else 'NO MATCH'})")
        
        all_results[name] = {
            'label': config['label'],
            'N': N,
            'n_steps': n_steps,
            'n_samples': n_samples,
            'observables': {
                'gamma_mean': float(np.mean(gamma_series)),
                'gamma_std': float(np.std(gamma_series)),
                'H_mean': float(np.mean(H_series)),
                'H_std': float(np.std(H_series)),
                'C_mean': float(np.mean(C_series)),
                'C_std': float(np.std(C_series)),
            },
            'fdt': fdt_results,
            'perturbation': perturb_results,
        }
    
    # ========================================================================
    # Comparative Analysis
    # ========================================================================
    print(f"\n{'='*70}")
    print("COMPARATIVE ANALYSIS")
    print(f"{'='*70}")
    
    print(f"\n{'Architecture':<15} {'C_cv':<12} {'dH/dγ':<10} {'kT_eff':<12} "
          f"{'FDT_CV':<10} {'Onsager':<10} {'Perturb':<10}")
    print("-" * 80)
    
    for name in ['random', 'attention', 'hebbian']:
        r = all_results[name]
        fdt = r['fdt']
        perturb = r['perturbation']
        
        print(f"{r['label']:<15} "
              f"{fdt['conservation']['C_cv']:<12.6f} "
              f"{fdt['effective_temperature']['slope_dH_dgamma']:<10.4f} "
              f"{fdt['effective_temperature']['kT_from_variance']:<12.6f} "
              f"{fdt['fdt_ratio']['cv_ratio']:<10.4f} "
              f"{fdt['onsager']['reciprocity_error']:<10.6f} "
              f"{perturb['shape_correlation']:<10.4f}")
    
    # ========================================================================
    # Thermodynamic Verdict
    # ========================================================================
    print(f"\n{'='*70}")
    print("THERMODYNAMIC VERDICT")
    print(f"{'='*70}")
    
    verdict = {}
    for name in ['random', 'attention', 'hebbian']:
        r = all_results[name]
        fdt = r['fdt']
        perturb = r['perturbation']
        
        # Score each thermodynamic criterion
        conservation_holds = fdt['conservation']['first_law_holds']
        slope_good = fdt['effective_temperature']['slope_is_minus_one']
        fdt_holds = fdt['fdt_ratio']['fdt_holds']
        onsager = fdt['onsager']['reciprocity_holds']
        perturb_match = perturb['shape_match']
        
        criteria = [conservation_holds, slope_good, fdt_holds, onsager, perturb_match]
        score = sum(criteria) / len(criteria)
        
        verdict[name] = {
            'conservation': conservation_holds,
            'slope_dH_dgamma': slope_good,
            'fdt': fdt_holds,
            'onsager': onsager,
            'perturbation_response': perturb_match,
            'thermodynamic_score': float(score),
            'is_thermodynamic': score >= 0.6,
        }
        
        status = "✓ THERMODYNAMIC" if score >= 0.6 else "✗ NOT THERMODYNAMIC"
        print(f"\n  {r['label']}: {status} (score: {score:.0%})")
        print(f"    Conservation (C=γ+H): {'✓' if conservation_holds else '✗'}")
        print(f"    dH/dγ ≈ -1: {'✓' if slope_good else '✗'} (slope={fdt['effective_temperature']['slope_dH_dgamma']:.4f})")
        print(f"    FDT ratio constant: {'✓' if fdt_holds else '✗'}")
        print(f"    Onsager reciprocity: {'✓' if onsager else '✗'}")
        print(f"    Perturbation-response match: {'✓' if perturb_match else '✗'}")
        
        if verdict[name]['is_thermodynamic']:
            kT = fdt['effective_temperature']['kT_from_variance']
            print(f"\n    → Effective temperature kT = {kT:.6f}")
            print(f"    → This system satisfies thermodynamic consistency")
    
    # ========================================================================
    # Cross-Architecture Temperature Comparison
    # ========================================================================
    print(f"\n{'='*70}")
    print("EFFECTIVE TEMPERATURE COMPARISON")
    print(f"{'='*70}")
    
    temps = {}
    for name in ['random', 'attention', 'hebbian']:
        r = all_results[name]
        kT = r['fdt']['effective_temperature']['kT_from_variance']
        gamma_mean = r['observables']['gamma_mean']
        gamma_std = r['observables']['gamma_std']
        ratio = gamma_std / gamma_mean if gamma_mean > 0 else float('inf')
        
        temps[name] = {
            'kT_variance': float(kT),
            'gamma_mean': float(gamma_mean),
            'sigma_over_gamma': float(ratio),
        }
        
        print(f"\n  {r['label']}:")
        print(f"    kT (from variance): {kT:.6f}")
        print(f"    γ mean: {gamma_mean:.6f}")
        print(f"    σ_γ / γ: {ratio:.4f}")
        print(f"    Analogy: {'hot' if ratio > 0.1 else 'cold'} system")
    
    # ========================================================================
    # Save Results
    # ========================================================================
    output = {
        'experiment': 'fdt_test',
        'cycle': 3,
        'date': '2026-05-17',
        'author': 'Forgemaster (research subagent)',
        'parameters': {
            'N': N,
            'n_steps': n_steps,
            'dt': dt,
            'beta': beta,
            'n_samples': n_samples,
        },
        'architectures': all_results,
        'verdict': verdict,
        'effective_temperatures': temps,
    }
    
    output_path = RESULTS_DIR / 'fdt-results.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nResults saved to {output_path}")
    
    return output

# ============================================================================
# Additional: Trace-Conservation Smoking Gun
# ============================================================================

def test_trace_conservation():
    """
    Test whether Tr(C) conservation explains γ+H conservation.
    
    If Tr(W) is fixed (e.g., by normalization), and the eigenvalue distribution
    follows Wigner semicircle, then γ+H may be trivially determined by Tr(W).
    """
    print(f"\n{'='*70}")
    print("TRACE-CONSERVATION SMOKING GUN TEST")
    print(f"{'='*70}")
    
    N = 20
    n_steps = 3000
    dt = 0.01
    beta = 1.0
    
    results = {}
    
    for name, gen in [('random', make_random_coupling), 
                       ('attention', make_attention_coupling),
                       ('hebbian', make_hebbian_coupling)]:
        
        trace_vals = []
        gamma_vals = []
        H_vals = []
        C_vals = []
        
        for trial in range(20):
            W = gen(N)
            x0 = np.random.randn(N)
            states = evolve_system(W, x0, n_steps, dt, beta)
            
            equil = n_steps // 2
            for t in range(equil, n_steps, 10):
                x = states[t]
                
                # Trace of coupling × state outer product
                # This measures how much total coupling energy is in the state
                trace_val = x @ W @ x
                
                g = compute_state_spectral_gap(W, x)
                h = compute_state_entropy(W, x)
                
                trace_vals.append(trace_val)
                gamma_vals.append(g)
                H_vals.append(h)
                C_vals.append(g + h)
        
        trace_vals = np.array(trace_vals)
        gamma_vals = np.array(gamma_vals)
        H_vals = np.array(H_vals)
        C_vals = np.array(C_vals)
        
        # Correlation between Tr and C
        corr_trace_C = np.corrcoef(trace_vals, C_vals)[0, 1] if np.var(C_vals) > 1e-15 else 0
        corr_trace_gamma = np.corrcoef(trace_vals, gamma_vals)[0, 1]
        corr_trace_H = np.corrcoef(trace_vals, H_vals)[0, 1]
        
        # If Tr explains C, then residual C - f(Tr) should have near-zero variance
        if np.var(trace_vals) > 1e-15:
            slope = np.polyfit(trace_vals, C_vals, 1)
            C_predicted = np.polyval(slope, trace_vals)
            residual_var = np.var(C_vals - C_predicted)
            total_var = np.var(C_vals)
            explained_fraction = 1.0 - residual_var / total_var if total_var > 0 else 0
        else:
            explained_fraction = 0
            slope = [0, 0]
        
        results[name] = {
            'corr_trace_C': float(corr_trace_C),
            'corr_trace_gamma': float(corr_trace_gamma),
            'corr_trace_H': float(corr_trace_H),
            'trace_explains_C_R2': float(explained_fraction),
            'C_cv': float(np.std(C_vals) / (np.mean(C_vals) + 1e-15)),
            'trace_cv': float(np.std(trace_vals) / (np.mean(trace_vals) + 1e-15)),
        }
        
        print(f"\n  {name}:")
        print(f"    Corr(Tr, C):  {corr_trace_C:.4f}")
        print(f"    Corr(Tr, γ):  {corr_trace_gamma:.4f}")
        print(f"    Corr(Tr, H):  {corr_trace_H:.4f}")
        print(f"    Tr explains C: R² = {explained_fraction:.4f}")
        print(f"    C CV: {results[name]['C_cv']:.4f}")
        print(f"    Tr CV: {results[name]['trace_cv']:.4f}")
    
    verdict = "TRACE EXPLAINS CONSERVATION" if any(
        r['trace_explains_C_R2'] > 0.8 for r in results.values()
    ) else "TRACE DOES NOT EXPLAIN CONSERVATION"
    
    print(f"\n  VERDICT: {verdict}")
    
    return results

# ============================================================================
# Run Everything
# ============================================================================

if __name__ == "__main__":
    print("Starting FDT experiment...\n")
    
    main_results = run_experiment()
    
    trace_results = test_trace_conservation()
    
    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE")
    print(f"{'='*70}")
    
    # Final summary
    print("\nFINAL SUMMARY:")
    for name in ['random', 'attention', 'hebbian']:
        v = main_results['verdict'][name]
        score = v['thermodynamic_score']
        label = main_results['architectures'][name]['label']
        print(f"  {label}: {score:.0%} thermodynamic "
              f"({'IS' if v['is_thermodynamic'] else 'NOT'} a thermodynamic system)")
    
    print("\n  Trace conservation explains γ+H: "
          f"{'YES' if any(r['trace_explains_C_R2'] > 0.8 for r in trace_results.values()) else 'NO'}")
