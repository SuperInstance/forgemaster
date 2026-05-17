"""
Prediction 1: Temperature τ monotonically controls Tr(C²)
Test: softmax coupling at τ = 0.1, 0.5, 1.0, 2.0, 5.0, 10.0
Dynamics: x_{t+1} = tanh(C @ x_t), 200 timesteps, 50 samples per τ
"""
import numpy as np
import json
import os

np.random.seed(42)

N = 20  # agents
T = 200  # timesteps
N_SAMPLES = 50
TEMPERATURES = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

def make_attention_coupling(x, tau):
    """Softmax coupling from state vectors."""
    scores = x @ x.T / tau
    # Numerical stability
    scores -= scores.max(axis=1, keepdims=True)
    exp_s = np.exp(scores)
    C = exp_s / exp_s.sum(axis=1, keepdims=True)
    return C

def make_hebbian_coupling(x):
    """Raw Hebbian coupling."""
    C = x @ x.T
    return C

def compute_spectral_props(C):
    """Compute eigenvalue-related quantities."""
    eigvals = np.linalg.eigvalsh((C + C.T) / 2)  # symmetrize for real eigenvalues
    eigvals = np.sort(np.real(eigvals))[::-1]
    tr_C2 = np.trace(C @ C)
    tr_C = np.trace(C)
    
    # Spectral gap (for row-stochastic: lambda_1 = 1)
    abs_eigs = np.sort(np.abs(eigvals))[::-1]
    if len(abs_eigs) > 1:
        spectral_gap = abs_eigs[0] - abs_eigs[1]
    else:
        spectral_gap = 0
    
    # Concentration ratio
    if tr_C2 > 0 and N > 0:
        rho = (tr_C ** 2) / (N * tr_C2)
    else:
        rho = 0
    
    return {
        'tr_C': float(tr_C),
        'tr_C2': float(tr_C2),
        'spectral_gap': float(spectral_gap),
        'rho': float(rho),
        'eigvals': eigvals[:5].tolist(),  # top 5 eigenvalues
        'eigval_spread': float(abs_eigs[0] - abs_eigs[-1]) if len(abs_eigs) > 0 else 0
    }

def compute_gamma_H(C, x):
    """Compute spectral gap (γ) and entropy (H) from state vector."""
    # γ: spectral gap of coupling matrix
    eigvals = np.linalg.eigvalsh((C + C.T) / 2)
    abs_eigs = np.sort(np.abs(eigvals))[::-1]
    gamma = float(abs_eigs[0] - abs_eigs[1]) if len(abs_eigs) > 1 else 0
    
    # H: entropy of eigenvalue distribution
    eig_positive = np.abs(eigvals)
    total = eig_positive.sum()
    if total > 0:
        p = eig_positive / total
        p = p[p > 1e-15]
        H = float(-np.sum(p * np.log(p)))
    else:
        H = 0
    
    return gamma, H

def run_experiment_tau(tau):
    """Run experiment for a given temperature."""
    results = {
        'tau': tau,
        'samples': []
    }
    
    for sample in range(N_SAMPLES):
        # Random initial state
        x = np.random.randn(N) * 0.5
        x = x / (np.linalg.norm(x) + 1e-10)
        
        # Build coupling matrix
        C = make_attention_coupling(x.reshape(-1, 1) * np.ones((1, N)), tau)
        # Actually: use outer product scores
        C = make_attention_coupling(np.random.randn(N, N), tau)
        
        # Better: use dot-product attention as in the theory
        Q = np.random.randn(N, 4)
        K = np.random.randn(N, 4)
        scores = Q @ K.T / tau
        scores -= scores.max(axis=1, keepdims=True)
        exp_s = np.exp(scores)
        C = exp_s / exp_s.sum(axis=1, keepdims=True)
        
        # Initial state vector
        x = np.random.randn(N) * 0.1
        
        trajectory = {
            'gamma': [],
            'H': [],
            'gamma_plus_H': [],
            'tr_C2': [],
            'tr_C': []
        }
        
        for t in range(T):
            # Compute spectral quantities
            gamma, H = compute_gamma_H(C, x)
            props = compute_spectral_props(C)
            
            trajectory['gamma'].append(gamma)
            trajectory['H'].append(H)
            trajectory['gamma_plus_H'].append(gamma + H)
            trajectory['tr_C2'].append(props['tr_C2'])
            trajectory['tr_C'].append(props['tr_C'])
            
            # Nonlinear dynamics: x_{t+1} = tanh(C @ x_t)
            x = np.tanh(C @ x)
        
        results['samples'].append(trajectory)
    
    # Aggregate statistics
    all_tr_C2 = []
    all_gamma_plus_H = []
    all_gamma = []
    all_H = []
    
    for traj in results['samples']:
        all_tr_C2.append(np.array(traj['tr_C2']))
        all_gamma_plus_H.append(np.array(traj['gamma_plus_H']))
        all_gamma.append(np.array(traj['gamma']))
        all_H.append(np.array(traj['H']))
    
    all_tr_C2 = np.array(all_tr_C2)       # (N_SAMPLES, T)
    all_gamma_plus_H = np.array(all_gamma_plus_H)
    all_gamma = np.array(all_gamma)
    all_H = np.array(all_H)
    
    # CV across time (temporal stability)
    temporal_cv_trC2 = np.mean(np.std(all_tr_C2, axis=1) / (np.mean(all_tr_C2, axis=1) + 1e-10))
    temporal_cv_gh = np.mean(np.std(all_gamma_plus_H, axis=1) / (np.mean(all_gamma_plus_H, axis=1) + 1e-10))
    
    # Steady-state values (last 50 timesteps)
    ss_trC2 = all_tr_C2[:, -50:].mean()
    ss_gh = all_gamma_plus_H[:, -50:].mean()
    ss_gamma = all_gamma[:, -50:].mean()
    ss_H = all_H[:, -50:].mean()
    
    # Cross-sample CV at steady state
    cross_cv_trC2 = np.std(all_tr_C2[:, -1]) / (np.mean(all_tr_C2[:, -1]) + 1e-10)
    cross_cv_gh = np.std(all_gamma_plus_H[:, -1]) / (np.mean(all_gamma_plus_H[:, -1]) + 1e-10)
    
    # γ-H correlation (temporal, averaged across samples)
    gh_corrs = []
    for i in range(N_SAMPLES):
        r = np.corrcoef(all_gamma[i], all_H[i])[0, 1]
        gh_corrs.append(r)
    
    results['summary'] = {
        'tau': tau,
        'temporal_cv_trC2': float(temporal_cv_trC2),
        'temporal_cv_gh': float(temporal_cv_gh),
        'steady_state_trC2': float(ss_trC2),
        'steady_state_gh': float(ss_gh),
        'steady_state_gamma': float(ss_gamma),
        'steady_state_H': float(ss_H),
        'cross_sample_cv_trC2': float(cross_cv_trC2),
        'cross_sample_cv_gh': float(cross_cv_gh),
        'mean_gamma_H_corr': float(np.mean(gh_corrs)),
        'std_gamma_H_corr': float(np.std(gh_corrs)),
    }
    
    # Spectral props of typical C matrix at this tau
    Q = np.random.randn(N, 4)
    K = np.random.randn(N, 4)
    scores = Q @ K.T / tau
    scores -= scores.max(axis=1, keepdims=True)
    exp_s = np.exp(scores)
    C_typical = exp_s / exp_s.sum(axis=1, keepdims=True)
    results['spectral_props'] = compute_spectral_props(C_typical)
    
    return results

def main():
    all_results = {}
    summaries = []
    
    for tau in TEMPERATURES:
        print(f"Running τ = {tau}...")
        res = run_experiment_tau(tau)
        all_results[f'tau_{tau}'] = res
        summaries.append(res['summary'])
        print(f"  Tr(C²) = {res['summary']['steady_state_trC2']:.4f}, "
              f"CV(TrC²) = {res['summary']['temporal_cv_trC2']:.6f}, "
              f"CV(γ+H) = {res['summary']['temporal_cv_gh']:.6f}, "
              f"γ-H r = {res['summary']['mean_gamma_H_corr']:.3f}")
    
    # Check monotonicity
    trC2_values = [s['steady_state_trC2'] for s in summaries]
    taus = TEMPERATURES
    
    print("\n=== MONOTONICITY CHECK ===")
    monotonic = True
    for i in range(1, len(trC2_values)):
        if trC2_values[i] > trC2_values[i-1]:
            monotonic = False
            print(f"  VIOLATION: Tr(C²) at τ={taus[i]} ({trC2_values[i]:.4f}) > τ={taus[i-1]} ({trC2_values[i-1]:.4f})")
    
    if monotonic:
        print("  ✓ Tr(C²) is MONOTONICALLY DECREASING with τ — PREDICTION CONFIRMED")
    else:
        print("  ✗ Tr(C²) is NOT monotonically decreasing — PREDICTION FALSIFIED")
    
    # Check τ=10 Tr(C²) ≈ 1
    print(f"\n  Tr(C²) at τ=10: {trC2_values[-1]:.4f} (theory predicts ~1.0, within 5%: {abs(trC2_values[-1] - 1.0) < 0.05 * 1.0})")
    
    # Check CV decreases with τ
    cv_values = [s['temporal_cv_gh'] for s in summaries]
    print(f"\n  CV(γ+H) vs τ: {[f'{v:.4f}' for v in cv_values]}")
    
    # Save
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-006/pred1_results.json', 'w') as f:
        # Don't save full trajectories (too large), just summaries
        save_data = {
            'summaries': summaries,
            'taus': taus,
            'trC2_values': trC2_values,
            'monotonic': monotonic,
            'spectral_props': {f'tau_{t}': all_results[f'tau_{t}']['spectral_props'] for t in taus}
        }
        json.dump(save_data, f, indent=2)
    
    return summaries, monotonic

if __name__ == '__main__':
    summaries, monotonic = main()
