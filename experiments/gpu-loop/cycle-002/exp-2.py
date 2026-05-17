#!/usr/bin/env python3
"""
EXP-2: Decorrelation of Structured Coupling — From Hebbian to Random
Add increasing noise to Hebbian and Attention matrices.
Watch conservation emerge as noise increases.
Find the critical noise level where conservation "turns on."
"""
import numpy as np
import json

np.random.seed(123)
N = 50
n_rounds = 100
noise_levels = np.logspace(-3, 1, 20)  # 0.001 to 10.0

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

def add_noise(J, noise_level):
    """Add Wigner noise to coupling matrix"""
    noise = np.random.randn(*J.shape)
    noise = (noise + noise.T) / (2 * np.sqrt(N))
    return J + noise_level * noise

def measure_conservation(J, n_rounds=100):
    """Run coupling dynamics and measure γ+H conservation"""
    gamma_H_values = []
    x = np.random.randn(N)
    for _ in range(n_rounds):
        x = J @ x
        norm = np.linalg.norm(x)
        if norm > 1e10 or norm < 1e-10:
            break
        x = x / norm
        evals = np.linalg.eigvalsh(J)
        abs_evals = np.sort(np.abs(evals))
        gamma = abs_evals[-1] - abs_evals[-2] if len(abs_evals) > 1 else 0
        probs = abs_evals / (np.sum(abs_evals) + 1e-12)
        H = -np.sum(probs * np.log(probs + 1e-12))
        gamma_H_values.append(gamma + H)
    
    if len(gamma_H_values) < 10:
        return {'mean': float('nan'), 'cv': float('nan'), 'n_valid': len(gamma_H_values)}
    
    mean = np.mean(gamma_H_values)
    std = np.std(gamma_H_values)
    cv = std / (mean + 1e-12)
    return {'mean': float(mean), 'cv': float(cv), 'n_valid': len(gamma_H_values)}

# Test both architectures across noise levels
results = {'hebbian': {}, 'attention': {}}

for arch_name, make_fn in [('hebbian', make_hebbian), ('attention', make_attention)]:
    print(f"\n{'='*60}")
    print(f"Architecture: {arch_name}")
    print(f"{'='*60}")
    
    for noise_level in noise_levels:
        cv_values = []
        for trial in range(20):
            J = make_fn(N)
            J_noisy = add_noise(J, noise_level)
            result = measure_conservation(J_noisy)
            if not np.isnan(result['cv']):
                cv_values.append(result['cv'])
        
        if cv_values:
            mean_cv = np.mean(cv_values)
            results[arch_name][str(noise_level)] = {
                'noise_level': float(noise_level),
                'mean_cv': float(mean_cv),
                'std_cv': float(np.std(cv_values)),
                'n_trials': len(cv_values)
            }
            conserved = "✓" if mean_cv < 0.05 else "✗"
            print(f"  noise={noise_level:8.4f} | CV={mean_cv:.4f} ± {np.std(cv_values):.4f} | {conserved}")
        else:
            results[arch_name][str(noise_level)] = {
                'noise_level': float(noise_level),
                'mean_cv': float('nan'),
                'n_trials': 0
            }

# Find critical noise level (where CV crosses 0.05)
print(f"\n{'='*60}")
print("CRITICAL NOISE LEVELS (CV < 0.05 threshold)")
print(f"{'='*60}")
for arch_name in ['hebbian', 'attention']:
    arch_data = results[arch_name]
    sorted_noise = sorted(arch_data.keys(), key=lambda x: float(x))
    critical = None
    for nl in sorted_noise:
        d = arch_data[nl]
        if not np.isnan(d['mean_cv']) and d['mean_cv'] < 0.05:
            critical = d['noise_level']
            break
    if critical:
        print(f"  {arch_name}: noise > {critical:.4f}")
    else:
        print(f"  {arch_name}: NOT ACHIEVED (conservation never reached)")

# Also measure eigenvalue correlation with GOE at each noise level
print(f"\n{'='*60}")
print("EIGENVALUE SPACING GOE-NESS vs NOISE")
print(f"{'='*60}")
for arch_name, make_fn in [('hebbian', make_hebbian)]:
    for noise_level in [0.001, 0.01, 0.1, 0.5, 1.0, 5.0]:
        spacings_all = []
        for _ in range(100):
            J = make_fn(N)
            J_noisy = add_noise(J, noise_level)
            evals = np.sort(np.linalg.eigvalsh(J_noisy))
            sp = np.diff(evals)
            sp = sp / (np.mean(sp) + 1e-12)
            spacings_all.extend(sp)
        
        # Level repulsion: fraction of spacings < 0.3 (GOE has few small spacings)
        repulsion = np.mean(np.array(spacings_all) < 0.3)
        print(f"  {arch_name} noise={noise_level:6.3f}: level_repulsion(violations)={repulsion:.4f}")

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-002/exp2_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to exp2_results.json")
