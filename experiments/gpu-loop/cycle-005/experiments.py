#!/usr/bin/env python3
"""
GPU Loop Cycle 5 — Nemotron-30B (second rotation)
Focus: Nonlinear dynamics, temperature, normalized Hebbian, falsification

Key theory to test:
- Softmax → row-stochastic → eigenvalues [0,1] → Tr(C²) stable → γ+H conserved
- Power iteration is DEAD (always converges to top eigenvector)
- Need nonlinear dynamics: x_{t+1} = tanh(C @ x_t) or similar
"""

import numpy as np
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

np.random.seed(42)

# ============================================================
# Utility Functions
# ============================================================

def spectral_entropy(eigenvalues):
    """Spectral entropy H = -Σ p_i log(p_i) where p_i = λ_i / Σλ_i"""
    pos = eigenvalues[eigenvalues > 1e-12]
    if len(pos) == 0:
        return 0.0
    p = pos / pos.sum()
    return -np.sum(p * np.log(p + 1e-30))

def spectral_gap(matrix):
    """Spectral gap γ = λ₁ - |λ₂|"""
    eigenvalues = np.sort(np.abs(np.linalg.eigvalsh(matrix)))[::-1]
    if len(eigenvalues) < 2:
        return eigenvalues[0]
    return eigenvalues[0] - eigenvalues[1]

def compute_metrics(C, x):
    """Compute γ+H and Tr(C²) from coupling matrix and state."""
    eigvals = np.linalg.eigvalsh(C)
    eigvals_sorted = np.sort(np.abs(eigvals))[::-1]
    
    gamma = eigvals_sorted[0] - eigvals_sorted[1] if len(eigvals_sorted) > 1 else eigvals_sorted[0]
    H = spectral_entropy(eigvals)
    tr_c2 = np.trace(C @ C)
    tr_c = np.trace(C)
    
    return {
        'gamma': gamma,
        'H': H,
        'gamma_plus_H': gamma + H,
        'tr_c2': tr_c2,
        'tr_c': tr_c,
        'top_eigenvalue': eigvals_sorted[0],
        'second_eigenvalue': eigvals_sorted[1] if len(eigvals_sorted) > 1 else 0,
        'state_norm': np.linalg.norm(x),
    }

def make_random_matrix(N, seed=None):
    """GOE random matrix (symmetric)."""
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()
    A = rng.randn(N, N)
    return (A + A.T) / (2 * np.sqrt(N))

def make_attention_matrix(N, temperature=1.0, seed=None):
    """Softmax attention matrix (row-stochastic)."""
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()
    Q = rng.randn(N, N)
    K = rng.randn(N, N)
    scores = Q @ K.T / np.sqrt(N)
    # Softmax with temperature
    exp_scores = np.exp(scores / temperature - np.max(scores / temperature, axis=1, keepdims=True))
    C = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    return C

def make_hebbian_matrix(x):
    """Hebbian coupling: C = x x^T / ||x||^2"""
    return np.outer(x, x) / (np.dot(x, x) + 1e-12)

def make_normalized_hebbian(x):
    """Row-stochastic Hebbian: C_ij = x_i * x_j, then normalize rows"""
    C = np.outer(np.abs(x), np.abs(x)) + 1e-12  # ensure positive
    row_sums = C.sum(axis=1, keepdims=True)
    return C / row_sums

def make_fabricated_attention(N, seed=None):
    """Attention-like matrix with causal masking (some zeros) — tests Perron-Frobenius violation."""
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()
    C = make_attention_matrix(N, temperature=1.0, seed=seed)
    # Apply causal mask (lower triangle zero)
    mask = np.triu(np.ones((N, N)), k=0)
    C = C * mask
    # Re-normalize rows
    row_sums = C.sum(axis=1, keepdims=True)
    row_sums[row_sums < 1e-12] = 1.0
    C = C / row_sums
    return C

# ============================================================
# Dynamics Models
# ============================================================

def run_nonlinear_dynamics(C, x0, n_steps=200, dynamics='tanh'):
    """Run nonlinear dynamics: x_{t+1} = f(C @ x_t)
    
    dynamics options:
    - 'tanh': x_{t+1} = tanh(C @ x_t)
    - 'sigmoid': x_{t+1} = sigmoid(C @ x_t)
    - 'clipped': x_{t+1} = clip(C @ x_t, -1, 1)
    - 'power': x_{t+1} = normalize(C @ x_t)  [baseline - dead]
    """
    x = x0.copy()
    history = []
    
    for t in range(n_steps):
        metrics = compute_metrics(C, x)
        metrics['step'] = t
        history.append(metrics)
        
        Cx = C @ x
        if dynamics == 'tanh':
            x = np.tanh(Cx)
        elif dynamics == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-Cx))
        elif dynamics == 'clipped':
            x = np.clip(Cx, -1, 1)
        elif dynamics == 'power':
            x = Cx / (np.linalg.norm(Cx) + 1e-12)
        else:
            raise ValueError(f"Unknown dynamics: {dynamics}")
    
    return history

def run_multi_agent_dynamics(C_func, states, n_steps=200):
    """Multi-agent dynamics: each agent has its own state, coupling is computed from states.
    
    C_func(states) -> coupling matrix
    states: list of agent states
    """
    history = []
    N = len(states)
    
    for t in range(n_steps):
        x = np.array(states)
        C = C_func(x)
        metrics = compute_metrics(C, x)
        metrics['step'] = t
        history.append(metrics)
        
        # Each agent updates based on coupling
        coupling_input = C @ x
        states = np.tanh(coupling_input).tolist()
    
    return history

def analyze_conservation(history, warmup=10):
    """Analyze conservation quality from dynamics history."""
    gh = np.array([h['gamma_plus_H'] for h in history[warmup:]])
    tr_c2 = np.array([h['tr_c2'] for h in history[warmup:]])
    gamma = np.array([h['gamma'] for h in history[warmup:]])
    H = np.array([h['H'] for h in history[warmup:]])
    
    # Skip NaN/inf
    mask = np.isfinite(gh) & np.isfinite(tr_c2)
    if mask.sum() < 5:
        return {'valid': False, 'reason': 'too few valid points'}
    
    gh = gh[mask]
    tr_c2 = tr_c2[mask]
    gamma = gamma[mask]
    H = H[mask]
    
    gh_cv = np.std(gh) / (np.mean(gh) + 1e-12) if np.mean(gh) > 1e-12 else np.std(gh)
    tr_c2_cv = np.std(tr_c2) / (np.mean(tr_c2) + 1e-12) if np.mean(tr_c2) > 1e-12 else np.std(tr_c2)
    
    # γ-H correlation
    if np.std(gamma) > 1e-12 and np.std(H) > 1e-12:
        gh_corr = np.corrcoef(gamma, H)[0, 1]
    else:
        gh_corr = 0.0
    
    # Tr(C²) ↔ γ+H correlation
    if np.std(tr_c2) > 1e-12 and np.std(gh) > 1e-12:
        trc2_gh_corr = np.corrcoef(tr_c2, gh)[0, 1]
    else:
        trc2_gh_corr = 0.0
    
    return {
        'valid': True,
        'gh_mean': float(np.mean(gh)),
        'gh_std': float(np.std(gh)),
        'gh_cv': float(gh_cv),
        'tr_c2_mean': float(np.mean(tr_c2)),
        'tr_c2_std': float(np.std(tr_c2)),
        'tr_c2_cv': float(tr_c2_cv),
        'gamma_mean': float(np.mean(gamma)),
        'H_mean': float(np.mean(H)),
        'gh_H_corr': float(gh_corr),
        'trc2_gh_corr': float(trc2_gh_corr),
        'n_points': int(mask.sum()),
        'gh_range': float(np.ptp(gh)),
    }

# ============================================================
# EXP 1: Temperature Sweep with Tanh Dynamics
# ============================================================
def exp1_temperature_sweep():
    """
    Test prediction: increasing τ should improve conservation.
    Softmax theory: τ→∞ means uniform attention, Tr(C²)→1, eigenvalues concentrated.
    """
    print("\n" + "="*60)
    print("EXP-1: Temperature Sweep with Tanh Dynamics")
    print("="*60)
    
    N = 20
    n_steps = 300
    warmup = 20
    temperatures = [0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    n_samples = 15
    
    results = []
    for tau in temperatures:
        sample_metrics = []
        for s in range(n_samples):
            C = make_attention_matrix(N, temperature=tau, seed=s*100 + int(tau*10))
            x0 = np.random.RandomState(s*200 + int(tau*10)).randn(N)
            
            history = run_nonlinear_dynamics(C, x0, n_steps=n_steps, dynamics='tanh')
            analysis = analyze_conservation(history, warmup=warmup)
            if analysis['valid']:
                sample_metrics.append(analysis)
        
        if sample_metrics:
            avg_gh_cv = np.mean([m['gh_cv'] for m in sample_metrics])
            avg_tr_c2_cv = np.mean([m['tr_c2_cv'] for m in sample_metrics])
            avg_corr = np.mean([m['gh_H_corr'] for m in sample_metrics])
            avg_trc2_corr = np.mean([m['trc2_gh_corr'] for m in sample_metrics])
            avg_gh_mean = np.mean([m['gh_mean'] for m in sample_metrics])
            avg_trc2_mean = np.mean([m['tr_c2_mean'] for m in sample_metrics])
            
            result = {
                'temperature': tau,
                'gh_cv': float(avg_gh_cv),
                'tr_c2_cv': float(avg_tr_c2_cv),
                'gh_H_corr': float(avg_corr),
                'trc2_gh_corr': float(avg_trc2_corr),
                'gh_mean': float(avg_gh_mean),
                'tr_c2_mean': float(avg_trc2_mean),
                'n_samples': len(sample_metrics),
            }
            results.append(result)
            print(f"  τ={tau:5.1f} | CV(γ+H)={avg_gh_cv:.4f} | CV(TrC²)={avg_tr_c2_cv:.4f} | "
                  f"r(γ,H)={avg_corr:.3f} | r(TrC²,γ+H)={avg_trc2_corr:.3f} | "
                  f"⟨γ+H⟩={avg_gh_mean:.3f} | ⟨TrC²⟩={avg_trc2_mean:.3f}")
    
    return results

# ============================================================
# EXP 2: Normalized Hebbian vs Raw Hebbian vs Attention
# ============================================================
def exp2_normalized_hebbian():
    """
    Test prediction: making Hebbian row-stochastic should improve conservation.
    This directly tests the "row-stochasticity = conservation" theory.
    """
    print("\n" + "="*60)
    print("EXP-2: Normalized Hebbian vs Raw Hebbian vs Attention")
    print("="*60)
    
    N = 20
    n_steps = 300
    warmup = 20
    n_samples = 20
    
    configs = ['attention', 'normalized_hebbian', 'raw_hebbian', 'random']
    results = {}
    
    for config in configs:
        sample_metrics = []
        for s in range(n_samples):
            rng = np.random.RandomState(s * 1000)
            x0 = rng.randn(N)
            x0_pos = np.abs(x0) + 0.01  # ensure positive for Hebbian
            
            if config == 'attention':
                C = make_attention_matrix(N, temperature=1.0, seed=s * 100)
                x0 = np.random.RandomState(s * 200).randn(N)
            elif config == 'normalized_hebbian':
                C = make_normalized_hebbian(x0_pos)
            elif config == 'raw_hebbian':
                C = make_hebbian_matrix(x0_pos)
            elif config == 'random':
                C = make_random_matrix(N, seed=s * 100)
                C = np.abs(C) / np.abs(C).sum(axis=1, keepdims=True)  # make row-stochastic for fair comparison
                x0 = np.random.RandomState(s * 200).randn(N)
            
            history = run_nonlinear_dynamics(C, x0, n_steps=n_steps, dynamics='tanh')
            analysis = analyze_conservation(history, warmup=warmup)
            if analysis['valid']:
                sample_metrics.append(analysis)
        
        if sample_metrics:
            avg_gh_cv = np.mean([m['gh_cv'] for m in sample_metrics])
            avg_tr_c2_cv = np.mean([m['tr_c2_cv'] for m in sample_metrics])
            avg_corr = np.mean([m['gh_H_corr'] for m in sample_metrics])
            avg_trc2_corr = np.mean([m['trc2_gh_corr'] for m in sample_metrics])
            avg_gh_mean = np.mean([m['gh_mean'] for m in sample_metrics])
            avg_trc2_mean = np.mean([m['tr_c2_mean'] for m in sample_metrics])
            
            results[config] = {
                'gh_cv': float(avg_gh_cv),
                'tr_c2_cv': float(avg_tr_c2_cv),
                'gh_H_corr': float(avg_corr),
                'trc2_gh_corr': float(avg_trc2_corr),
                'gh_mean': float(avg_gh_mean),
                'tr_c2_mean': float(avg_trc2_mean),
                'n_samples': len(sample_metrics),
            }
            print(f"  {config:25s} | CV(γ+H)={avg_gh_cv:.4f} | CV(TrC²)={avg_tr_c2_cv:.4f} | "
                  f"r(γ,H)={avg_corr:.3f} | r(TrC²,γ+H)={avg_trc2_corr:.3f}")
    
    return results

# ============================================================
# EXP 3: Dynamics Model Comparison (Tanh vs Sigmoid vs Clipped vs Power)
# ============================================================
def exp3_dynamics_comparison():
    """
    Compare dynamics models. Theory predicts tanh (nonlinear) should show
    richer dynamics than power iteration (linear).
    """
    print("\n" + "="*60)
    print("EXP-3: Dynamics Model Comparison")
    print("="*60)
    
    N = 20
    n_steps = 300
    warmup = 20
    n_samples = 15
    
    dynamics_list = ['tanh', 'sigmoid', 'clipped', 'power']
    results = {}
    
    for dyn in dynamics_list:
        # Test with attention coupling
        sample_metrics = []
        for s in range(n_samples):
            C = make_attention_matrix(N, temperature=1.0, seed=s * 100)
            x0 = np.random.RandomState(s * 200).randn(N)
            
            history = run_nonlinear_dynamics(C, x0, n_steps=n_steps, dynamics=dyn)
            analysis = analyze_conservation(history, warmup=warmup)
            if analysis['valid']:
                sample_metrics.append(analysis)
        
        if sample_metrics:
            avg_gh_cv = np.mean([m['gh_cv'] for m in sample_metrics])
            avg_tr_c2_cv = np.mean([m['tr_c2_cv'] for m in sample_metrics])
            avg_corr = np.mean([m['gh_H_corr'] for m in sample_metrics])
            avg_gh_mean = np.mean([m['gh_mean'] for m in sample_metrics])
            
            # Check for fixed points vs oscillations
            last_50_gh = [m['gh_cv'] for m in sample_metrics]
            
            results[dyn] = {
                'gh_cv': float(avg_gh_cv),
                'tr_c2_cv': float(avg_tr_c2_cv),
                'gh_H_corr': float(avg_corr),
                'gh_mean': float(avg_gh_mean),
                'n_samples': len(sample_metrics),
            }
            print(f"  {dyn:10s} | CV(γ+H)={avg_gh_cv:.4f} | CV(TrC²)={avg_tr_c2_cv:.4f} | "
                  f"r(γ,H)={avg_corr:.3f} | ⟨γ+H⟩={avg_gh_mean:.3f}")
    
    return results

# ============================================================
# EXP 4: Falsification — Try to Break Conservation
# ============================================================
def exp4_falsification():
    """
    Try to break the conservation law:
    a) Causal masking (violate Perron-Frobenius positivity)
    b) State-dependent coupling (Hebbian evolving with state)
    c) Anti-attention (invert softmax = argmin instead of argmax)
    d) Random sign flipping
    e) Extreme temperature (τ→0, near-one-hot)
    """
    print("\n" + "="*60)
    print("EXP-4: Falsification — Try to Break Conservation")
    print("="*60)
    
    N = 20
    n_steps = 300
    warmup = 20
    n_samples = 15
    
    def run_test(name, C_func, x0_func=None):
        sample_metrics = []
        for s in range(n_samples):
            C = C_func(s)
            x0 = x0_func(s) if x0_func else np.random.RandomState(s * 200).randn(N)
            history = run_nonlinear_dynamics(C, x0, n_steps=n_steps, dynamics='tanh')
            analysis = analyze_conservation(history, warmup=warmup)
            if analysis['valid']:
                sample_metrics.append(analysis)
        
        if sample_metrics:
            avg_gh_cv = np.mean([m['gh_cv'] for m in sample_metrics])
            avg_tr_c2_cv = np.mean([m['tr_c2_cv'] for m in sample_metrics])
            avg_corr = np.mean([m['gh_H_corr'] for m in sample_metrics])
            avg_gh_mean = np.mean([m['gh_mean'] for m in sample_metrics])
            survival = len(sample_metrics) / n_samples * 100
            
            print(f"  {name:35s} | CV(γ+H)={avg_gh_cv:.4f} | CV(TrC²)={avg_tr_c2_cv:.4f} | "
                  f"r(γ,H)={avg_corr:.3f} | ⟨γ+H⟩={avg_gh_mean:.3f} | survival={survival:.0f}%")
            return {
                'gh_cv': float(avg_gh_cv),
                'tr_c2_cv': float(avg_tr_c2_cv),
                'gh_H_corr': float(avg_corr),
                'gh_mean': float(avg_gh_mean),
                'survival': float(survival),
            }
        else:
            print(f"  {name:35s} | NO VALID RUNS")
            return {'gh_cv': float('nan'), 'survival': 0.0}
    
    results = {}
    
    # (a) Causal masking — some zero entries → violate Perron-Frobenius
    results['causal_mask'] = run_test(
        "Causal mask (PF violation)",
        lambda s: make_fabricated_attention(N, seed=s*100)
    )
    
    # (b) State-dependent Hebbian coupling (evolving C)
    print("\n  --- State-dependent coupling ---")
    sample_metrics = []
    for s in range(n_samples):
        rng = np.random.RandomState(s * 300)
        x = rng.randn(N) * 0.1
        gh_vals = []
        tr_c2_vals = []
        gamma_vals = []
        H_vals = []
        
        for t in range(n_steps):
            # Hebbian coupling from current state
            C = np.outer(x, x)
            C = C / (np.trace(C) / N + 1e-12)  # normalize trace
            np.fill_diagonal(C, 1.0)  # self-connection
            
            metrics = compute_metrics(C, x)
            gh_vals.append(metrics['gamma_plus_H'])
            tr_c2_vals.append(metrics['tr_c2'])
            gamma_vals.append(metrics['gamma'])
            H_vals.append(metrics['H'])
            
            # Update state with nonlinear dynamics
            x = np.tanh(C @ x)
        
        gh = np.array(gh_vals[warmup:])
        tr_c2 = np.array(tr_c2_vals[warmup:])
        g = np.array(gamma_vals[warmup:])
        h = np.array(H_vals[warmup:])
        
        mask = np.isfinite(gh)
        if mask.sum() > 5:
            cv = np.std(gh[mask]) / (np.mean(gh[mask]) + 1e-12)
            trcv = np.std(tr_c2[mask]) / (np.mean(tr_c2[mask]) + 1e-12)
            corr = np.corrcoef(g[mask], h[mask])[0,1] if np.std(g[mask]) > 1e-12 else 0.0
            sample_metrics.append({'gh_cv': cv, 'tr_c2_cv': trcv, 'gh_H_corr': corr, 'gh_mean': np.mean(gh[mask])})
    
    if sample_metrics:
        avg_gh_cv = np.mean([m['gh_cv'] for m in sample_metrics])
        avg_tr_c2_cv = np.mean([m['tr_c2_cv'] for m in sample_metrics])
        avg_corr = np.mean([m['gh_H_corr'] for m in sample_metrics])
        avg_gh_mean = np.mean([m['gh_mean'] for m in sample_metrics])
        results['hebbian_dynamic'] = {
            'gh_cv': float(avg_gh_cv),
            'tr_c2_cv': float(avg_tr_c2_cv),
            'gh_H_corr': float(avg_corr),
            'gh_mean': float(avg_gh_mean),
        }
        print(f"  {'Hebbian (dynamic coupling)':35s} | CV(γ+H)={avg_gh_cv:.4f} | CV(TrC²)={avg_tr_c2_cv:.4f} | "
              f"r(γ,H)={avg_corr:.3f} | ⟨γ+H⟩={avg_gh_mean:.3f}")
    
    # (c) Inverse attention (exp(-scores/τ) — maximally anti-correlated attention)
    results['inverse_attention'] = run_test(
        "Inverse attention (anti-softmax)",
        lambda s: _make_inverse_attention(N, seed=s*100)
    )
    
    # (d) Random sign flipping of coupling matrix
    results['sign_flip'] = run_test(
        "Random sign flips on attention",
        lambda s: _make_sign_flip_attention(N, seed=s*100)
    )
    
    # (e) Extreme temperature τ→0.01 (near-one-hot)
    results['tau_0.01'] = run_test(
        "Extreme low temp τ=0.01 (near-one-hot)",
        lambda s: make_attention_matrix(N, temperature=0.01, seed=s*100)
    )
    
    # (f) Negative coupling
    results['negative_coupling'] = run_test(
        "Negative coupling (anti-correlation)",
        lambda s: _make_negative_coupling(N, seed=s*100)
    )
    
    return results

def _make_inverse_attention(N, seed=None):
    """Inverse attention: softmax of negative scores."""
    rng = np.random.RandomState(seed)
    Q = rng.randn(N, N)
    K = rng.randn(N, N)
    scores = Q @ K.T / np.sqrt(N)
    # Inverse: use negative scores
    neg_scores = -scores
    exp_s = np.exp(neg_scores - np.max(neg_scores, axis=1, keepdims=True))
    C = exp_s / exp_s.sum(axis=1, keepdims=True)
    return C

def _make_sign_flip_attention(N, seed=None):
    """Attention with random sign flips — breaks row-stochasticity."""
    rng = np.random.RandomState(seed)
    C = make_attention_matrix(N, temperature=1.0, seed=seed)
    signs = rng.choice([-1, 1], size=(N, N))
    return C * signs

def _make_negative_coupling(N, seed=None):
    """Negative coupling: -softmax + identity scaling."""
    C = make_attention_matrix(N, temperature=1.0, seed=seed)
    return -C + 2.0 * np.eye(N) / N

# ============================================================
# EXP 5: Concentration Ratio ρ and Conservation Quality
# ============================================================
def exp5_concentration_ratio():
    """
    Test the two-moment theory prediction: ρ = S²/(N·Q) predicts conservation quality.
    Also test whether the theory holds under nonlinear dynamics.
    """
    print("\n" + "="*60)
    print("EXP-5: Concentration Ratio ρ vs Conservation Quality")
    print("="*60)
    
    N = 20
    n_steps = 300
    warmup = 20
    n_samples = 15
    
    # Generate matrices with varying concentration
    configs = []
    
    # Attention at different temperatures
    for tau in [0.1, 0.5, 1.0, 5.0, 20.0]:
        configs.append(('attention_tau={}'.format(tau), lambda s, t=tau: make_attention_matrix(N, temperature=t, seed=s*100)))
    
    # Random row-stochastic
    configs.append(('random_row_stoch', lambda s: _make_random_row_stochastic(N, seed=s*100)))
    
    # Hebbian variants
    configs.append(('hebbian_raw', lambda s: make_hebbian_matrix(np.abs(np.random.RandomState(s*300).randn(N)) + 0.01)))
    configs.append(('hebbian_normalized', lambda s: make_normalized_hebbian(np.abs(np.random.RandomState(s*300).randn(N)) + 0.01)))
    
    # GOE random (not row-stochastic)
    configs.append(('goe_random', lambda s: make_random_matrix(N, seed=s*100)))
    
    results = []
    for name, C_func in configs:
        sample_data = []
        for s in range(n_samples):
            C = C_func(s)
            x0 = np.random.RandomState(s * 200).randn(N)
            
            # Compute concentration ratio ρ from initial coupling
            eigvals = np.linalg.eigvalsh(C)
            eigvals = np.abs(eigvals)
            S = np.sum(eigvals)
            Q = np.sum(eigvals**2)
            rho = S**2 / (N * Q) if Q > 1e-12 else 0
            
            history = run_nonlinear_dynamics(C, x0, n_steps=n_steps, dynamics='tanh')
            analysis = analyze_conservation(history, warmup=warmup)
            
            if analysis['valid']:
                sample_data.append({
                    'rho': rho,
                    'gh_cv': analysis['gh_cv'],
                    'tr_c2_cv': analysis['tr_c2_cv'],
                    'gh_H_corr': analysis['gh_H_corr'],
                })
        
        if sample_data:
            avg_rho = np.mean([d['rho'] for d in sample_data])
            avg_gh_cv = np.mean([d['gh_cv'] for d in sample_data])
            avg_tr_c2_cv = np.mean([d['tr_c2_cv'] for d in sample_data])
            avg_corr = np.mean([d['gh_H_corr'] for d in sample_data])
            
            results.append({
                'name': name,
                'rho': float(avg_rho),
                'gh_cv': float(avg_gh_cv),
                'tr_c2_cv': float(avg_tr_c2_cv),
                'gh_H_corr': float(avg_corr),
            })
            print(f"  {name:30s} | ρ={avg_rho:.4f} | CV(γ+H)={avg_gh_cv:.4f} | "
                  f"CV(TrC²)={avg_tr_c2_cv:.4f} | r(γ,H)={avg_corr:.3f}")
    
    # Correlation between ρ and conservation metrics
    if len(results) > 3:
        rhos = [r['rho'] for r in results]
        cvs = [r['gh_cv'] for r in results]
        corrs = [r['gh_H_corr'] for r in results]
        
        rho_cv_corr = np.corrcoef(rhos, cvs)[0,1] if len(rhos) > 2 else 0
        rho_corr_corr = np.corrcoef(rhos, np.abs(corrs))[0,1] if len(rhos) > 2 else 0
        
        print(f"\n  ρ vs CV(γ+H) correlation: r = {rho_cv_corr:.3f}")
        print(f"  ρ vs |r(γ,H)| correlation: r = {rho_corr_corr:.3f}")
    
    return results

def _make_random_row_stochastic(N, seed=None):
    """Random matrix normalized to be row-stochastic (positive entries)."""
    rng = np.random.RandomState(seed)
    C = np.abs(rng.randn(N, N)) + 0.01
    return C / C.sum(axis=1, keepdims=True)

# ============================================================
# Main
# ============================================================
def main():
    print("="*60)
    print("GPU LOOP CYCLE 5 — Nemotron-30B (second rotation)")
    print("Focus: Nonlinear dynamics, temperature, normalized Hebbian, falsification")
    print("="*60)
    
    results = {}
    
    results['exp1_temperature'] = exp1_temperature_sweep()
    results['exp2_normalized_hebbian'] = exp2_normalized_hebbian()
    results['exp3_dynamics'] = exp3_dynamics_comparison()
    results['exp4_falsification'] = exp4_falsification()
    results['exp5_concentration'] = exp5_concentration_ratio()
    
    # Save raw results
    out_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_path, 'raw_results.json'), 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nRaw results saved to {out_path}/raw_results.json")
    return results

if __name__ == '__main__':
    main()
