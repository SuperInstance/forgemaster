#!/usr/bin/env python3
"""
Lyapunov Monotonicity Test for Spectral First Integral I(x) = γ(x) + H(x)

Question: Is I(x) monotonically non-increasing along trajectories?
If yes → genuine Lyapunov function (dynamics always move toward LOWER I)
If no → first integral (conserved) but not Lyapunov (Hamiltonian-like, no dissipation in I)
"""

import numpy as np
from scipy.linalg import eigvalsh
import json

np.random.seed(42)

N = 20  # dimension

def compute_spectral_first_integral(C):
    """Compute I = γ + H from eigenvalues of symmetrized C."""
    C_sym = 0.5 * (C + C.T)
    eigs = np.sort(np.real(eigvalsh(C_sym)))[::-1]
    eigs_pos = np.maximum(eigs, 1e-15)  # avoid log(0)
    
    # Spectral gap
    gamma = eigs_pos[0] - eigs_pos[1]
    
    # Participation entropy
    total = np.sum(eigs_pos)
    if total < 1e-15:
        return gamma, 0.0, gamma
    p = eigs_pos / total
    p = p[p > 1e-15]
    H = -np.sum(p * np.log(p))
    
    I = gamma + H
    return gamma, H, I

def simulate_trajectory(activation, coupling_fn, x0, T=50, noise_sigma=0.05):
    """Run x_{t+1} = σ(C(x_t) x_t) + noise for T steps, tracking I(x_t)."""
    x = x0.copy()
    trajectory = {
        'I': [], 'gamma': [], 'H': [],
        'x_norm': [], 'delta_I': [],
    }
    
    for t in range(T):
        C = coupling_fn(x)
        gamma, H, I = compute_spectral_first_integral(C)
        trajectory['I'].append(I)
        trajectory['gamma'].append(gamma)
        trajectory['H'].append(H)
        trajectory['x_norm'].append(np.linalg.norm(x))
        
        if t > 0:
            trajectory['delta_I'].append(I - trajectory['I'][-2])
        
        # Step dynamics
        y = C @ x
        if activation == 'tanh':
            x = np.tanh(y)
        elif activation == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-y))
        elif activation == 'swish':
            x = y / (1.0 + np.exp(-y))  # x * sigmoid(x)
        elif activation == 'softsign':
            x = y / (1.0 + np.abs(y))
        elif activation == 'relu':
            x = np.maximum(0, y)
        elif activation == 'leaky_relu':
            x = np.where(y > 0, y, 0.01 * y)
        
        # Add small noise to keep dynamics non-trivial
        x += noise_sigma * np.random.randn(N)
    
    return trajectory

# --- Coupling Functions ---
def make_attention_coupling(tau=1.0):
    def coupling(x):
        scores = np.outer(x, x) / (tau * np.sqrt(N))
        scores -= np.max(scores, axis=1, keepdims=True)  # stability
        exp_scores = np.exp(scores)
        C = exp_scores / exp_scores.sum(axis=1, keepdims=True)
        return C
    return coupling

def make_hebbian_coupling():
    def coupling(x):
        return np.outer(x, x) / N
    return coupling

def make_random_coupling(scale=1.5):
    R = np.random.randn(N, N) * scale / np.sqrt(N)
    return lambda x: R  # static but state-dependent interface

def make_hybrid_coupling(alpha=0.5):
    R = np.random.randn(N, N) * 1.5 / np.sqrt(N)
    def coupling(x):
        hebbian = np.outer(x, x) / N
        return alpha * hebbian + (1 - alpha) * R
    return coupling

# --- Main Experiment ---
configs = {
    'attention_tau1': {'activation': 'tanh', 'coupling': make_attention_coupling(1.0)},
    'attention_tau05': {'activation': 'tanh', 'coupling': make_attention_coupling(0.5)},
    'attention_tau2': {'activation': 'tanh', 'coupling': make_attention_coupling(2.0)},
    'hebbian': {'activation': 'tanh', 'coupling': make_hebbian_coupling()},
    'random': {'activation': 'tanh', 'coupling': make_random_coupling(1.5)},
    'hybrid_05': {'activation': 'tanh', 'coupling': make_hybrid_coupling(0.5)},
}

# Test different activations with attention
for act in ['sigmoid', 'swish', 'softsign', 'relu', 'leaky_relu']:
    configs[f'attention_{act}'] = {'activation': act, 'coupling': make_attention_coupling(1.0)}

n_samples = 10
T = 50

results = {}

for name, cfg in configs.items():
    all_trajectories = []
    monotone_count = 0
    max_upward = 0
    all_deltas = []
    all_I_values = []
    
    for s in range(n_samples):
        x0 = np.random.randn(N) * 0.5
        traj = simulate_trajectory(cfg['activation'], cfg['coupling'], x0, T=T)
        all_trajectories.append(traj)
        
        deltas = np.array(traj['delta_I'])
        I_vals = np.array(traj['I'])
        all_deltas.extend(deltas.tolist())
        all_I_values.extend(I_vals.tolist())
        
        # Check monotonicity: is I non-increasing?
        is_monotone = np.all(deltas <= 1e-10)  # allow tiny numerical noise
        if is_monotone:
            monotone_count += 1
        
        # Max upward deviation
        upward = deltas[deltas > 0]
        if len(upward) > 0:
            max_upward = max(max_upward, np.max(upward))
    
    all_deltas = np.array(all_deltas)
    I_arr = np.array(all_I_values)
    
    frac_upward = np.mean(all_deltas > 1e-10)
    mean_upward = np.mean(all_deltas[all_deltas > 1e-10]) if np.any(all_deltas > 1e-10) else 0
    mean_downward = np.mean(all_deltas[all_deltas < -1e-10]) if np.any(all_deltas < -1e-10) else 0
    
    results[name] = {
        'monotone_frac': monotone_count / n_samples,
        'max_upward': max_upward,
        'frac_upward_steps': frac_upward,
        'mean_upward': mean_upward,
        'mean_downward': mean_downward,
        'I_mean': np.mean(I_arr),
        'I_std': np.std(I_arr),
        'I_cv': np.std(I_arr) / np.mean(I_arr) if np.mean(I_arr) > 0 else 0,
        'mean_delta': np.mean(all_deltas),
        'std_delta': np.std(all_deltas),
    }
    
    print(f"\n{'='*60}")
    print(f"Config: {name}")
    print(f"  I range: [{np.min(I_arr):.6f}, {np.max(I_arr):.6f}]")
    print(f"  I mean={np.mean(I_arr):.6f}, std={np.std(I_arr):.6f}, CV={results[name]['I_cv']:.6f}")
    print(f"  Monotone trajectories: {monotone_count}/{n_samples} ({monotone_count/n_samples*100:.0f}%)")
    print(f"  Fraction of upward steps: {frac_upward:.3f}")
    print(f"  Max upward deviation: {max_upward:.6f}")
    print(f"  Mean ΔI (upward): {mean_upward:.6f}")
    print(f"  Mean ΔI (downward): {mean_downward:.6f}")
    print(f"  Mean ΔI (overall): {np.mean(all_deltas):.6f}")

# --- Contraction Rate Analysis ---
print(f"\n{'='*60}")
print("CONTRACTION RATE ANALYSIS")
print(f"{'='*60}")

# For attention tanh, check if dI/dt ≤ -α·I
name = 'attention_tau1'
cfg = configs[name]
sample_I_series = []

for s in range(n_samples):
    x0 = np.random.randn(N) * 0.5
    traj = simulate_trajectory(cfg['activation'], cfg['coupling'], x0, T=T)
    sample_I_series.append(np.array(traj['I']))

# Compute rate of decrease
print("\nRate analysis (attention tanh):")
for s, I_s in enumerate(sample_I_series[:5]):
    deltas = np.diff(I_s)
    # Fit: delta_I ≈ -alpha * I_t
    I_t = I_s[:-1]
    valid = I_t > 0.01  # avoid division by near-zero
    if np.sum(valid) > 5:
        alpha_eff = np.mean(-deltas[valid] / I_t[valid])
        print(f"  Sample {s}: mean dI/I = {alpha_eff:.6f} (negative = decreasing)")
        # Check linear fit
        if np.std(deltas[valid]) > 1e-10:
            r_rate = np.corrcoef(-deltas[valid], I_t[valid])[0, 1]
            print(f"    correlation(-ΔI, I_t) = {r_rate:.4f}")

# --- Summary ---
print(f"\n{'='*60}")
print("SUMMARY: LYAPUNOV MONOTONICITY TEST")
print(f"{'='*60}")

# Classify each config
for name, r in sorted(results.items(), key=lambda x: x[1]['frac_upward_steps']):
    if r['monotone_frac'] == 1.0:
        verdict = "MONOTONE (Lyapunov candidate)"
    elif r['frac_upward_steps'] < 0.05:
        verdict = "NEARLY MONOTONE (<5% upward)"
    elif r['frac_upward_steps'] < 0.2:
        verdict = "MOSTLY DECREASING"
    elif r['frac_upward_steps'] < 0.4:
        verdict = "FLUCTUATING (net decrease)"
    else:
        verdict = "STRONGLY FLUCTUATING"
    
    net_direction = "decreasing" if r['mean_delta'] < 0 else "INCREASING"
    print(f"  {name:30s}: {verdict}")
    print(f"    {'':30s}  CV(I)={r['I_cv']:.4f}, frac↑={r['frac_upward_steps']:.3f}, "
          f"max↑={r['max_upward']:.6f}, net={net_direction}")

print(f"\n{'='*60}")
print("DIAGNOSIS")
print(f"{'='*60}")

# Overall conclusion
any_monotone = any(r['monotone_frac'] == 1.0 for r in results.values())
avg_frac_up = np.mean([r['frac_upward_steps'] for r in results.values()])

if any_monotone:
    print("CONCLUSION: I(x) IS monotonically non-increasing for some configurations.")
    print("I(x) is a genuine Lyapunov function in those cases.")
else:
    print("CONCLUSION: I(x) is NOT monotonically non-increasing for any configuration.")
    print("I(x) is a first integral (conserved) but NOT a Lyapunov function.")
    print("The dynamics are Hamiltonian-like: conserved quantity, no dissipation in I.")

print(f"\nAverage fraction of upward steps: {avg_frac_up:.3f}")

# Is it approximately monotone?
for name, r in results.items():
    if r['frac_upward_steps'] > 0:
        relative_up = r['mean_upward'] / r['I_mean'] if r['I_mean'] > 0 else 0
        relative_down = abs(r['mean_downward']) / r['I_mean'] if r['I_mean'] > 0 else 0
        asymmetry = (relative_down - relative_up) / (relative_down + relative_up) if (relative_down + relative_up) > 0 else 0
        results[name]['asymmetry'] = asymmetry
        results[name]['relative_up'] = relative_up
        results[name]['relative_down'] = relative_down

print("\nAsymmetry analysis (positive = net decreasing):")
for name, r in sorted(results.items(), key=lambda x: x[1].get('asymmetry', 0)):
    print(f"  {name:30s}: asymmetry={r.get('asymmetry', 0):.4f}, "
          f"rel↑={r.get('relative_up', 0):.6f}, rel↓={r.get('relative_down', 0):.6f}")
