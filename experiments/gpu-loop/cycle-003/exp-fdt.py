#!/usr/bin/env python3
"""
Fluctuation-Dissipation Theorem Test for Coupled Agent Systems — v2
===================================================================

CORRECTED INTERPRETATION:
  γ = spectral gap of W (STATIC property of coupling matrix)
  H = spectral entropy of W (STATIC property of coupling matrix)  
  C = γ + H (conserved across architectures/precisions)

FDT test: The DYNAMICS of state x(t) under coupling W should satisfy:
  1. Fluctuation amplitude ⟨|x|²⟩ ∝ γ (thermal energy = kT)
  2. Relaxation time τ ∝ 1/γ (dissipation rate)
  3. Fluctuation autocorrelation shape determined by γ (FDT proper)
  4. If γ↔T, then for an ensemble of matrices: C = γ+H should behave like F = TS

Three levels of FDT testing:
  Level 1: Ensemble thermodynamics — across many W matrices, does C = γ+H behave like F(T,S)?
  Level 2: Dynamic FDT — within one W, does ⟨δx(t)δx(0)⟩ relate to γ as kT·χ(t)?
  Level 3: Architecture comparison — which architectures satisfy FDT most completely?

Author: Forgemaster ⚒️ (research subagent)
Date: 2026-05-17
"""

import numpy as np
from numpy.linalg import eigvalsh, eigh
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
np.random.seed(42)

RESULTS_DIR = Path(__file__).parent
RESULTS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Matrix Generation (same as cycles 0-1)
# ============================================================================

def make_random_coupling(N):
    """GOE random matrix."""
    A = np.random.randn(N, N)
    return (A + A.T) / (2 * np.sqrt(N))

def make_hebbian_coupling(N, n_patterns=None):
    """Hebbian coupling from stored patterns."""
    if n_patterns is None:
        n_patterns = max(3, N // 3)
    patterns = np.random.choice([-1, 1], size=(n_patterns, N))
    W = patterns.T @ patterns / N
    np.fill_diagonal(W, 0)
    return W / np.linalg.norm(W, ord=2)

def make_attention_coupling(N, d=None):
    """Attention-style coupling."""
    if d is None:
        d = max(4, N // 4)
    Q = np.random.randn(N, d) / np.sqrt(d)
    K = np.random.randn(N, d) / np.sqrt(d)
    W = Q @ K.T / np.sqrt(d)
    W = (W + W.T) / 2
    return W / np.linalg.norm(W, ord=2)

# ============================================================================
# Static Observables (from W eigenvalues)
# ============================================================================

def compute_static_gamma(W):
    """Spectral gap: λ₁ - λ₂ (largest - second largest eigenvalue)."""
    eigs = np.sort(eigvalsh(W))[::-1]
    return max(eigs[0] - eigs[1], 1e-12)

def compute_static_entropy(W):
    """Spectral entropy: H = -Σ pᵢ ln(pᵢ) from eigenvalue distribution."""
    eigs = eigvalsh(W)
    abs_eigs = np.abs(eigs)
    total = np.sum(abs_eigs)
    if total < 1e-15:
        return 0.0
    probs = abs_eigs / total
    probs = probs[probs > 1e-15]
    return -np.sum(probs * np.log(probs))

def compute_static_C(W):
    """Conservation constant: C = γ + H."""
    return compute_static_gamma(W) + compute_static_entropy(W)

# ============================================================================
# State Evolution (Langevin dynamics)
# ============================================================================

def evolve_langevin(W, x0, n_steps, dt=0.01, beta=1.0):
    """
    Langevin dynamics: dx = -β W x dt + √(2T) dW
    Temperature T controls noise level.
    """
    N = W.shape[0]
    states = np.zeros((n_steps, N))
    states[0] = x0.copy()
    noise_scale = np.sqrt(2 * dt)
    
    for t in range(1, n_steps):
        drift = -beta * W @ states[t-1] * dt
        noise = noise_scale * np.random.randn(N)
        states[t] = states[t-1] + drift + noise
    
    return states

# ============================================================================
# LEVEL 1: Ensemble Thermodynamics
# ============================================================================

def level1_ensemble_thermodynamics(n_matrices=500, N=20):
    """
    Generate ensemble of coupling matrices.
    For each: compute γ (T), H (S), C (F = T·S... wait, F = E - TS).
    
    Actually in thermodynamics: F = E - TS (Helmholtz) or G = H - TS (Gibbs).
    Our conservation is C = γ + H. 
    
    For FDT, the key prediction is:
    - If γ plays the role of temperature, then across the ensemble,
      the VARIANCE of state fluctuations should scale with γ.
    - If H plays the role of entropy, then it should be maximized at equilibrium.
    
    More precisely: the Boltzmann distribution gives
      P(state) ∝ exp(-β E(state))
    where β = 1/(kT). The equilibrium distribution of x under W is Gaussian:
      P(x) ∝ exp(-β xᵀW x / 2)
    So the "energy" is E = xᵀWx/2 and "temperature" controls variance.
    """
    print("=" * 70)
    print("LEVEL 1: ENSEMBLE THERMODYNAMICS")
    print("=" * 70)
    
    results = {}
    
    for name, gen in [('random', make_random_coupling),
                       ('attention', make_attention_coupling),
                       ('hebbian', make_hebbian_coupling)]:
        
        gammas = []
        entropies = []
        C_vals = []
        fluct_energies = []  # ⟨xᵀWx⟩ at equilibrium
        fluct_variances = []  # ⟨|x|²⟩ at equilibrium
        relaxation_times = []  # time to reach equilibrium
        
        for i in range(n_matrices):
            W = gen(N)
            gamma = compute_static_gamma(W)
            H = compute_static_entropy(W)
            C = gamma + H
            
            gammas.append(gamma)
            entropies.append(H)
            C_vals.append(C)
            
            # Evolve and measure equilibrium fluctuations
            x0 = np.random.randn(N)
            states = evolve_langevin(W, x0, 3000, dt=0.01, beta=1.0)
            
            # Equilibrium phase (last half)
            eq_states = states[1500:]
            
            # Average energy: ⟨xᵀWx⟩
            energies = np.array([x @ W @ x for x in eq_states])
            fluct_energies.append(np.mean(energies))
            
            # State variance: ⟨|x|²⟩
            norms2 = np.sum(eq_states**2, axis=1)
            fluct_variances.append(np.mean(norms2))
            
            # Relaxation time: time for |x|² to stabilize
            # Use autocorrelation decay of state energy
            eq_energies = energies - np.mean(energies)
            if np.var(eq_energies) > 1e-15:
                acf = np.correlate(eq_energies[:200], eq_energies[:200], mode='full')
                acf = acf[len(acf)//2:]
                acf = acf / acf[0]
                # Find where ACF drops below 1/e
                threshold_idx = np.where(acf < 1/np.e)[0]
                tau = threshold_idx[0] if len(threshold_idx) > 0 else 200
            else:
                tau = 1
            relaxation_times.append(tau)
        
        gammas = np.array(gammas)
        entropies = np.array(entropies)
        C_vals = np.array(C_vals)
        fluct_energies = np.array(fluct_energies)
        fluct_variances = np.array(fluct_variances)
        relaxation_times = np.array(relaxation_times)
        
        # === Key thermodynamic tests ===
        
        # Test 1a: Conservation C = γ + H
        C_cv = np.std(C_vals) / np.mean(C_vals)
        
        # Test 1b: Fluctuation energy vs γ (thermal energy = kT?)
        # If γ = kT, then ⟨xᵀWx⟩ should be proportional to γ
        corr_energy_gamma = np.corrcoef(fluct_energies, gammas)[0, 1]
        
        # Test 1c: State variance vs γ (equipartition: ⟨x²⟩ = kT per mode)
        corr_variance_gamma = np.corrcoef(fluct_variances, gammas)[0, 1]
        
        # Test 1d: Relaxation time vs 1/γ (FDT: dissipation rate ∝ γ)
        # Avoid div by zero for Hebbian (γ→0)
        valid_gamma = gammas > 1e-8
        if np.sum(valid_gamma) > 10:
            corr_tau_inv_gamma = np.corrcoef(
                relaxation_times[valid_gamma], 
                1.0 / gammas[valid_gamma]
            )[0, 1]
        else:
            corr_tau_inv_gamma = 0.0
        
        # Test 1e: Does dH/dγ = -1 (thermodynamic consistency)?
        # From C = γ + H → H = C - γ → dH/dγ = -1 if C is constant
        if np.std(gammas) > 1e-10:
            slope_dH_dgamma = np.polyfit(gammas, entropies, 1)[0]
        else:
            slope_dH_dgamma = 0.0
        
        # Test 1f: Entropy is maximized at equilibrium?
        # Compare H of W eigenvalues to H of state energy distribution
        state_entropies = []
        for i in range(min(100, n_matrices)):
            W = gen(N)
            x0 = np.random.randn(N)
            states = evolve_langevin(W, x0, 3000, dt=0.01, beta=1.0)
            eq = states[1500:]
            energies = np.array([x @ W @ x for x in eq])
            # Energy distribution entropy
            hist, _ = np.histogram(energies, bins=30, density=True)
            hist = hist[hist > 0]
            state_entropies.append(-np.sum(hist * np.log(hist)))
        
        avg_state_entropy = np.mean(state_entropies)
        
        results[name] = {
            'gamma_mean': float(np.mean(gammas)),
            'gamma_std': float(np.std(gammas)),
            'H_mean': float(np.mean(entropies)),
            'H_std': float(np.std(entropies)),
            'C_mean': float(np.mean(C_vals)),
            'C_std': float(np.std(C_vals)),
            'C_cv': float(C_cv),
            'conservation_holds': bool(C_cv < 0.1),
            'corr_energy_gamma': float(corr_energy_gamma),
            'corr_variance_gamma': float(corr_variance_gamma),
            'corr_tau_inv_gamma': float(corr_tau_inv_gamma),
            'slope_dH_dgamma': float(slope_dH_dgamma),
            'slope_is_minus_one': bool(abs(slope_dH_dgamma + 1.0) < 0.3),
            'avg_state_entropy': float(avg_state_entropy),
            'n_matrices': n_matrices,
        }
        
        print(f"\n  {name.upper()}:")
        print(f"    γ: {np.mean(gammas):.6f} ± {np.std(gammas):.6f}")
        print(f"    H: {np.mean(entropies):.6f} ± {np.std(entropies):.6f}")
        print(f"    C: {np.mean(C_vals):.6f} ± {np.std(C_vals):.6f} (CV={C_cv:.4f})")
        print(f"    Corr(⟨xᵀWx⟩, γ): {corr_energy_gamma:.4f} (expect >0 if γ=kT)")
        print(f"    Corr(⟨|x|²⟩, γ): {corr_variance_gamma:.4f} (expect >0 if γ=kT)")
        print(f"    Corr(τ, 1/γ): {corr_tau_inv_gamma:.4f} (expect >0 if FDT)")
        print(f"    dH/dγ: {slope_dH_dgamma:.4f} (expect -1.0)")
    
    return results

# ============================================================================
# LEVEL 2: Dynamic FDT — State Fluctuations vs γ
# ============================================================================

def level2_dynamic_fdt(N=20, n_matrices=30, n_steps=5000, dt=0.01):
    """
    For each W, compute the state autocorrelation function.
    
    FDT predicts: ⟨x(t)x(0)⟩ = exp(-γ t) for the slowest mode.
    More precisely, the relaxation is governed by the eigenvalues of W.
    
    If γ = spectral gap = λ₁ - λ₂, then the slowest mode decays as exp(-γ t).
    This is the FDT prediction: fluctuation autocorrelation = response function × kT.
    
    We test:
    1. Does the slowest relaxation rate equal γ?
    2. Is the ACF shape exponential with rate γ?
    3. Does the fluctuation amplitude scale with γ?
    """
    print(f"\n{'='*70}")
    print("LEVEL 2: DYNAMIC FDT — STATE FLUCTUATION AUTOCORRELATION")
    print(f"{'='*70}")
    
    results = {}
    
    for name, gen in [('random', make_random_coupling),
                       ('attention', make_attention_coupling),
                       ('hebbian', make_hebbian_coupling)]:
        
        observed_rates = []
        predicted_gammas = []
        rate_errors = []
        acf_amplitudes = []
        
        for trial in range(n_matrices):
            W = gen(N)
            gamma = compute_static_gamma(W)
            predicted_gammas.append(gamma)
            
            # Evolve
            x0 = np.random.randn(N)
            states = evolve_langevin(W, x0, n_steps, dt, beta=1.0)
            
            # Use the state energy time series
            eq_states = states[n_steps//2:]
            energies = np.array([x @ W @ x for x in eq_states])
            
            if np.var(energies) < 1e-15:
                observed_rates.append(0)
                rate_errors.append(float('inf'))
                acf_amplitudes.append(0)
                continue
            
            # Autocorrelation of energy fluctuations
            e_fluct = energies - np.mean(energies)
            n_acf = min(500, len(e_fluct) // 2)
            acf = np.correlate(e_fluct[:n_acf*2], e_fluct[:n_acf*2], mode='full')
            acf = acf[len(acf)//2:]
            acf = acf / (acf[0] + 1e-15)
            
            # Fit exponential decay to ACF
            # ACF(t) ≈ exp(-λ t), so log(ACF) ≈ -λ t
            valid = acf[:n_acf] > 0.01
            if np.sum(valid) > 10:
                t_vals = np.arange(n_acf)[valid] * dt
                log_acf = np.log(acf[:n_acf][valid])
                slope = np.polyfit(t_vals, log_acf, 1)[0]
                observed_rate = -slope
            else:
                observed_rate = 0
            
            observed_rates.append(observed_rate)
            if gamma > 1e-8:
                rate_errors.append(abs(observed_rate - gamma) / gamma)
            else:
                rate_errors.append(0 if observed_rate < 0.01 else float('inf'))
            
            # ACF amplitude (first lag)
            acf_amplitudes.append(acf[1] if len(acf) > 1 else 0)
        
        observed_rates = np.array(observed_rates)
        predicted_gammas = np.array(predicted_gammas)
        rate_errors = np.array(rate_errors)
        
        # Correlation between observed relaxation rate and predicted γ
        valid_pred = predicted_gammas > 1e-8
        if np.sum(valid_pred) > 5:
            corr_rate_gamma = np.corrcoef(observed_rates[valid_pred], 
                                           predicted_gammas[valid_pred])[0, 1]
        else:
            corr_rate_gamma = 0.0
        
        mean_rate_error = np.mean(rate_errors[np.isfinite(rate_errors)])
        
        # FDT holds if: relaxation rate = γ (spectral gap)
        # AND the correlation between them is high
        
        results[name] = {
            'mean_observed_rate': float(np.mean(observed_rates)),
            'mean_predicted_gamma': float(np.mean(predicted_gammas)),
            'rate_gamma_correlation': float(corr_rate_gamma),
            'mean_relative_error': float(mean_rate_error),
            'fdt_prediction_matches': bool(corr_rate_gamma > 0.5 and mean_rate_error < 1.0),
            'n_samples': n_matrices,
        }
        
        print(f"\n  {name.upper()}:")
        print(f"    Predicted γ: {np.mean(predicted_gammas):.6f}")
        print(f"    Observed relaxation rate: {np.mean(observed_rates):.6f}")
        print(f"    Corr(observed_rate, γ): {corr_rate_gamma:.4f}")
        print(f"    Mean relative error: {mean_rate_error:.4f}")
        print(f"    FDT prediction: {'MATCHES' if corr_rate_gamma > 0.5 else 'NO MATCH'}")
    
    return results

# ============================================================================
# LEVEL 3: FDT via Perturbation-Response
# ============================================================================

def level3_perturbation_response(N=20, n_trials=100, n_equil=2000, 
                                   n_response=300, dt=0.01):
    """
    Apply perturbations to the system and measure response.
    
    FDT states: the LINEAR RESPONSE of the system to an external perturbation
    is determined by the EQUILIBRIUM FLUCTUATIONS.
    
    Specifically: if we perturb x → x + δx along eigenvector v₁,
    the response ⟨δE(t)⟩ should match the autocorrelation of spontaneous fluctuations.
    
    We test:
    1. Response function shape = equilibrium fluctuation autocorrelation shape
    2. Response amplitude ∝ perturbation strength (linearity)
    3. Response rate = γ (spectral gap)
    """
    print(f"\n{'='*70}")
    print("LEVEL 3: PERTURBATION-RESPONSE FDT TEST")
    print(f"{'='*70}")
    
    results = {}
    
    for name, gen in [('random', make_random_coupling),
                       ('attention', make_attention_coupling),
                       ('hebbian', make_hebbian_coupling)]:
        
        W = gen(N)
        gamma = compute_static_gamma(W)
        
        # --- Equilibrium fluctuations ---
        x0 = np.random.randn(N)
        eq_states = evolve_langevin(W, x0, n_equil, dt, beta=1.0)
        eq_energies = np.array([x @ W @ x for x in eq_states[n_equil//2:]])
        
        # Equilibrium ACF
        eq_fluct = eq_energies - np.mean(eq_energies)
        n_acf = min(200, len(eq_fluct) // 2)
        eq_acf = np.correlate(eq_fluct[:n_acf*2], eq_fluct[:n_acf*2], mode='full')
        eq_acf = eq_acf[len(eq_acf)//2:]
        eq_acf = eq_acf / (eq_acf[0] + 1e-15)
        
        # --- Perturbation response ---
        eigenvalues, eigvecs = eigh(W)
        eigvecs = eigvecs[:, ::-1]
        v1 = eigvecs[:, 0]  # top eigenvector
        
        perturbation_scales = [0.01, 0.05, 0.1, 0.2]
        response_curves = {}
        linearity_check = []
        
        for pscale in perturbation_scales:
            responses = np.zeros((n_trials, n_response))
            
            for trial in range(n_trials):
                # Equilibrate
                x0 = np.random.randn(N)
                eq = evolve_langevin(W, x0, n_equil, dt, beta=1.0)
                x_eq = eq[-1]
                
                # Perturb along v1
                x_pert = x_eq + pscale * v1 * np.linalg.norm(x_eq)
                
                # Measure response
                resp_states = evolve_langevin(W, x_pert, n_response, dt, beta=1.0)
                for t in range(n_response):
                    responses[trial, t] = resp_states[t] @ W @ resp_states[t]
            
            # Average response
            mean_response = np.mean(responses, axis=0)
            baseline = np.mean(eq_energies)
            response_curve = mean_response - baseline
            
            # Normalize for shape comparison
            max_abs = np.max(np.abs(response_curve))
            if max_abs > 1e-15:
                response_norm = response_curve / max_abs
            else:
                response_norm = np.zeros_like(response_curve)
            
            response_curves[str(pscale)] = response_norm.tolist()
            linearity_check.append(float(max_abs))
        
        # Linearity: response amplitude should be proportional to perturbation
        scales_arr = np.array(perturbation_scales)
        amps_arr = np.array(linearity_check)
        if np.var(amps_arr) > 1e-15:
            linearity_corr = np.corrcoef(scales_arr, amps_arr)[0, 1]
            linearity_slope = np.polyfit(scales_arr, amps_arr, 1)[0]
        else:
            linearity_corr = 0.0
            linearity_slope = 0.0
        
        # Shape match: normalized response should match normalized ACF
        resp_main = response_curves[str(perturbation_scales[1])]  # use mid-scale
        min_len = min(len(eq_acf), len(resp_main))
        if min_len > 10:
            shape_corr = np.corrcoef(eq_acf[:min_len], resp_main[:min_len])[0, 1]
        else:
            shape_corr = 0.0
        
        # Response rate estimation (exponential fit to response decay)
        resp_arr = np.array(resp_main)
        valid = resp_arr > 0.01
        if np.sum(valid) > 10:
            t_vals = np.arange(len(resp_arr))[valid] * dt
            log_resp = np.log(np.abs(resp_arr[valid]) + 1e-15)
            resp_rate = -np.polyfit(t_vals, log_resp, 1)[0]
        else:
            resp_rate = 0.0
        
        results[name] = {
            'gamma': float(gamma),
            'linearity_correlation': float(linearity_corr),
            'linearity_holds': bool(linearity_corr > 0.9),
            'shape_correlation_acf_response': float(shape_corr),
            'shape_match': bool(abs(shape_corr) > 0.5) if not np.isnan(shape_corr) else False,
            'response_rate': float(resp_rate),
            'rate_matches_gamma': bool(abs(resp_rate - gamma) / (gamma + 1e-10) < 0.5) if gamma > 1e-8 else False,
            'n_trials': n_trials,
        }
        
        print(f"\n  {name.upper()}:")
        print(f"    γ: {gamma:.6f}")
        print(f"    Response linearity: r={linearity_corr:.4f} {'(LINEAR)' if linearity_corr > 0.9 else '(NONLINEAR)'}")
        print(f"    ACF-Response shape match: r={shape_corr:.4f} {'(MATCH)' if abs(shape_corr) > 0.5 else '(NO MATCH)'}")
        print(f"    Response rate: {resp_rate:.4f} vs γ: {gamma:.4f}")
        print(f"    Rate matches γ: {'YES' if results[name]['rate_matches_gamma'] else 'NO'}")
    
    return results

# ============================================================================
# LEVEL 4: Cross-Architecture Thermodynamic Consistency
# ============================================================================

def level4_thermodynamic_consistency(N=20, n_ensemble=300):
    """
    For each architecture, generate ensemble and test full thermodynamic mapping.
    
    In thermodynamics:
      F = E - TS (Helmholtz free energy)
      dF = -S dT - P dV (at constant volume)
      Cp = T (∂S/∂T)_P (heat capacity)
    
    Our mapping: γ ↔ T, H ↔ S, C = γ + H ↔ ?
    
    For the mapping to be thermodynamic:
    1. ∂H/∂γ should be consistent (from C = γ + H → dH/dγ = dC/dγ - 1)
    2. If C is constant → dH/dγ = -1 (exact first law)
    3. "Heat capacity" = dH/d(ln γ) should be well-defined
    4. Clausius-Clapeyron: relationships between phases should hold
    """
    print(f"\n{'='*70}")
    print("LEVEL 4: THERMODYNAMIC CONSISTENCY CHECK")
    print(f"{'='*70}")
    
    results = {}
    
    for name, gen in [('random', make_random_coupling),
                       ('attention', make_attention_coupling),
                       ('hebbian', make_hebbian_coupling)]:
        
        gammas = []
        entropies = []
        C_vals = []
        traces = []
        
        for _ in range(n_ensemble):
            W = gen(N)
            gammas.append(compute_static_gamma(W))
            entropies.append(compute_static_entropy(W))
            C_vals.append(compute_static_gamma(W) + compute_static_entropy(W))
            traces.append(np.trace(W))
        
        gammas = np.array(gammas)
        entropies = np.array(entropies)
        C_vals = np.array(C_vals)
        traces = np.array(traces)
        
        # Test: dH/dγ
        if np.std(gammas) > 1e-10:
            dH_dgamma = np.polyfit(gammas, entropies, 1)[0]
        else:
            dH_dgamma = 0.0
        
        # Test: dC/dγ (should be 0 if C is constant)
        if np.std(gammas) > 1e-10:
            dC_dgamma = np.polyfit(gammas, C_vals, 1)[0]
        else:
            dC_dgamma = 0.0
        
        # Test: is C constant? (CV)
        C_cv = np.std(C_vals) / np.mean(C_vals) if np.mean(C_vals) > 0 else float('inf')
        
        # Test: "Heat capacity" = dH/d(ln γ) = γ · dH/dγ
        heat_capacity = np.mean(gammas) * dH_dgamma if np.mean(gammas) > 0 else 0
        
        # Test: Trace conservation (smoking gun from insights)
        corr_trace_C = np.corrcoef(traces, C_vals)[0, 1]
        
        # Test: Is C just a function of Tr(W)?
        if np.std(traces) > 1e-15:
            trace_explains_C = 1.0 - np.var(C_vals - np.polyval(np.polyfit(traces, C_vals, 1), traces)) / np.var(C_vals)
        else:
            trace_explains_C = 0.0
        
        # Thermodynamic score
        criteria = {
            'C_is_constant': C_cv < 0.1,
            'dC_dgamma_near_zero': abs(dC_dgamma) < 0.5,
            'dH_dgamma_near_minus_one': abs(dH_dgamma + 1.0) < 0.3,
            'heat_capacity_well_defined': abs(heat_capacity) < 5.0,
        }
        score = sum(criteria.values()) / len(criteria)
        
        results[name] = {
            'C_cv': float(C_cv),
            'dC_dgamma': float(dC_dgamma),
            'dH_dgamma': float(dH_dgamma),
            'heat_capacity': float(heat_capacity),
            'corr_trace_C': float(corr_trace_C),
            'trace_explains_C_R2': float(trace_explains_C),
            'criteria': {k: bool(v) for k, v in criteria.items()},
            'thermodynamic_score': float(score),
            'is_thermodynamic': bool(score >= 0.6),
        }
        
        print(f"\n  {name.upper()}:")
        print(f"    C CV: {C_cv:.4f} {'✓' if C_cv < 0.1 else '✗'}")
        print(f"    dC/dγ: {dC_dgamma:.4f} {'✓' if abs(dC_dgamma) < 0.5 else '✗'} (expect 0)")
        print(f"    dH/dγ: {dH_dgamma:.4f} {'✓' if abs(dH_dgamma + 1) < 0.3 else '✗'} (expect -1)")
        print(f"    Heat capacity: {heat_capacity:.4f}")
        print(f"    Corr(Tr(W), C): {corr_trace_C:.4f}")
        print(f"    Tr(W) explains C: R²={trace_explains_C:.4f}")
        print(f"    Thermodynamic score: {score:.0%} {'✓ THERMODYNAMIC' if score >= 0.6 else '✗ NOT THERMODYNAMIC'}")
    
    return results

# ============================================================================
# Custom JSON encoder for numpy types
# ============================================================================

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("FLUCTUATION-DISSIPATION THEOREM TEST — v2")
    print("GPU Constraint Experiment Loop — Cycle 3")
    print("Forgemaster Research Subagent")
    print("=" * 70)
    
    N = 20
    
    # Level 1: Ensemble thermodynamics
    level1 = level1_ensemble_thermodynamics(n_matrices=300, N=N)
    
    # Level 2: Dynamic FDT
    level2 = level2_dynamic_fdt(N=N, n_matrices=40, n_steps=5000)
    
    # Level 3: Perturbation response
    level3 = level3_perturbation_response(N=N, n_trials=50)
    
    # Level 4: Thermodynamic consistency
    level4 = level4_thermodynamic_consistency(N=N, n_ensemble=500)
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print(f"\n{'='*70}")
    print("FINAL SUMMARY — DOES FDT HOLD?")
    print(f"{'='*70}")
    
    summary = {}
    for name, label in [('random', 'GOE Random'), ('attention', 'Attention'), 
                         ('hebbian', 'Hebbian')]:
        
        l1 = level1[name]
        l2 = level2[name]
        l3 = level3[name]
        l4 = level4[name]
        
        # Aggregate score across all levels
        checks = [
            ('L1: Conservation C=γ+H', l1['conservation_holds']),
            ('L1: Energy∝γ (equipartition)', l1['corr_energy_gamma'] > 0.3),
            ('L1: Variance∝γ', l1['corr_variance_gamma'] > 0.3),
            ('L2: Rate=γ (FDT prediction)', l2['fdt_prediction_matches']),
            ('L3: Linear response', l3['linearity_holds']),
            ('L3: ACF=Response shape', l3['shape_match']),
            ('L3: Rate matches γ', l3['rate_matches_gamma']),
            ('L4: Thermodynamic consistency', l4['is_thermodynamic']),
        ]
        
        total = len(checks)
        passed = sum(1 for _, v in checks if v)
        score = passed / total
        
        summary[name] = {
            'label': label,
            'score': float(score),
            'passed': int(passed),
            'total': int(total),
            'is_thermodynamic': bool(score >= 0.5),
            'checks': {k: bool(v) for k, v in checks},
        }
        
        status = "✓ THERMODYNAMIC" if score >= 0.5 else "✗ NOT THERMODYNAMIC"
        print(f"\n  {label}: {status} ({passed}/{total} = {score:.0%})")
        for check_name, check_val in checks:
            print(f"    {'✓' if check_val else '✗'} {check_name}")
    
    # Overall verdict
    print(f"\n{'='*70}")
    print("OVERALL VERDICT")
    print(f"{'='*70}")
    
    thermo_architectures = [name for name, s in summary.items() if s['is_thermodynamic']]
    if thermo_architectures:
        print(f"\n  Architectures with thermodynamic behavior: {', '.join(thermo_architectures)}")
        for name in thermo_architectures:
            s = summary[name]
            print(f"    {s['label']}: score={s['score']:.0%}, kT~γ={level1[name]['gamma_mean']:.4f}")
    else:
        print("\n  No architecture shows full thermodynamic behavior.")
        print("  The conservation law C=γ+H may NOT be thermodynamic in origin.")
        print("  It may instead arise from random matrix universality (Wigner statistics).")
    
    # Key insight from trace test
    print(f"\n  Trace-Conservation Analysis:")
    for name in ['random', 'attention', 'hebbian']:
        l4n = level4[name]
        print(f"    {name}: Corr(Tr,C)={l4n['corr_trace_C']:.4f}, "
              f"Tr explains C: R²={l4n['trace_explains_C_R2']:.4f}")
    
    # Save all results
    output = {
        'experiment': 'fdt_test_v2',
        'cycle': 3,
        'date': '2026-05-17',
        'author': 'Forgemaster (research subagent)',
        'N': N,
        'level1_ensemble': level1,
        'level2_dynamic_fdt': level2,
        'level3_perturbation': level3,
        'level4_consistency': level4,
        'summary': summary,
    }
    
    output_path = RESULTS_DIR / 'fdt-results.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, cls=NumpyEncoder)
    
    print(f"\n  Results saved to {output_path}")
    
    return output

if __name__ == "__main__":
    main()
