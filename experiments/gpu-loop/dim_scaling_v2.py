#!/usr/bin/env python3
"""
Dimensional Scaling Experiment v2 — with noise to prevent trivial convergence.
CV(I) ~ 1/N conjecture test.

Key fix: add noise σ=0.1 to prevent Hebbian/random from collapsing to 0.
Also scale random coupling by 2.0 for non-trivial dynamics.
"""

import numpy as np
from scipy import linalg
from scipy.stats import linregress
import warnings, json
warnings.filterwarnings('ignore')

np.random.seed(42)

NOISE_STD = 0.1
SCALE_RANDOM = 2.0  # spectral radius scaling for random coupling
TAU = 1.0
STEPS = 50
SAMPLES = 10
Ns = [5, 10, 20, 50, 100]

def attention_coupling(x, tau=1.0):
    N = len(x)
    logits = np.outer(x, x) / (tau * np.sqrt(N))
    logits -= logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(logits)
    C = exp_logits / exp_logits.sum(axis=1, keepdims=True)
    return C

def hebbian_coupling(x):
    N = len(x)
    return np.outer(x, x) / N

def random_coupling(N):
    M = np.random.randn(N, N)
    M = (M + M.T) / (2 * np.sqrt(N))
    return M * SCALE_RANDOM

def compute_I(C):
    C_sym = (C + C.T) / 2.0
    eigvals = np.real(linalg.eigvalsh(C_sym))
    eigvals = np.sort(eigvals)[::-1]
    gamma = eigvals[0] - eigvals[1] if len(eigvals) > 1 else eigvals[0]
    pos = eigvals[eigvals > 1e-12]
    if len(pos) == 0:
        return gamma, 0.0, gamma
    p = pos / pos.sum()
    H = -np.sum(p * np.log(np.maximum(p, 1e-30)))
    return gamma, H, gamma + H

def run_trajectory(arch, N, steps, noise_std=NOISE_STD):
    x = np.random.randn(N) * 0.5
    I_vals = []
    
    if arch == 'random':
        C = random_coupling(N)
    
    for t in range(steps):
        if arch == 'attention':
            C = attention_coupling(x, tau=TAU)
        elif arch == 'hebbian':
            C = hebbian_coupling(x)
        # else: C already set for random (static)
        
        _, _, I = compute_I(C)
        I_vals.append(I)
        
        x = np.tanh(C @ x) + np.random.randn(N) * noise_std
    
    return np.array(I_vals)

def cv(values):
    m = np.mean(values)
    if abs(m) < 1e-15:
        return 0.0
    return np.std(values) / abs(m)

# Run experiment
results = {}
raw_data = {}  # store actual I trajectories for analysis

for arch in ['random', 'attention', 'hebbian']:
    for N in Ns:
        cvs = []
        traj_means = []
        traj_stds = []
        for s in range(SAMPLES):
            I_vals = run_trajectory(arch, N, STEPS)
            c = cv(I_vals)
            cvs.append(c)
            traj_means.append(np.mean(I_vals))
            traj_stds.append(np.std(I_vals))
        
        results[(arch, N)] = cvs
        raw_data[(arch, N)] = {
            'cv_mean': np.mean(cvs),
            'cv_std': np.std(cvs),
            'I_mean': np.mean(traj_means),
            'I_std': np.mean(traj_stds),
            'cvs': cvs
        }
        print(f"{arch:12s} N={N:4d}: CV={np.mean(cvs):.6f} ± {np.std(cvs):.6f} | I_mean={np.mean(traj_means):.4f} ± {np.mean(traj_stds):.4f}")

print("\n" + "="*70)
print("POWER LAW FITS: CV = a * N^b")
print("="*70)

fit_results = {}
for arch in ['random', 'attention', 'hebbian']:
    mean_cvs = [np.mean(results[(arch, N)]) for N in Ns]
    log_N = np.log(Ns)
    log_CV = np.log(np.maximum(mean_cvs, 1e-15))
    
    slope, intercept, r_value, p_value, std_err = linregress(log_N, log_CV)
    b = slope
    a = np.exp(intercept)
    R2 = r_value**2
    
    # Test specific functional forms
    inv_N = [1.0/n for n in Ns]
    r_inv, _, r_inv_val, _, _ = linregress(inv_N, mean_cvs)
    
    inv_N2 = [1.0/n**2 for n in Ns]
    r_inv2, _, r_inv2_val, _, _ = linregress(inv_N2, mean_cvs)
    
    logN_N = [np.log(n)/n for n in Ns]
    r_logN, _, r_logN_val, _, _ = linregress(logN_N, mean_cvs)
    
    print(f"\n{arch}:")
    print(f"  Power law:  CV = {a:.6f} × N^{b:.4f}  (R²={R2:.4f})")
    print(f"  Linear 1/N:  R² = {r_inv_val**2:.4f}")
    print(f"  Linear 1/N²: R² = {r_inv2_val**2:.4f}")
    print(f"  Linear ln(N)/N: R² = {r_logN_val**2:.4f}")
    
    fit_results[arch] = {
        'a': a, 'b': b, 'R2': R2,
        'R2_inv_N': r_inv_val**2,
        'R2_inv_N2': r_inv2_val**2,
        'R2_logN_N': r_logN_val**2
    }

# === DETAILED TABLE ===
print("\n" + "="*70)
print("FULL RESULTS TABLE")
print("="*70)
print(f"{'Arch':12s} {'N':>4s} | {'CV_mean':>10s} {'CV_std':>10s} | {'I_mean':>10s} {'I_std':>10s} | CV(Hebbian)=CV(||x||²)")
print("-"*80)
for arch in ['random', 'attention', 'hebbian']:
    for N in Ns:
        d = raw_data[(arch, N)]
        print(f"{arch:12s} {N:4d} | {d['cv_mean']:10.6f} {d['cv_std']:10.6f} | {d['I_mean']:10.4f} {d['I_std']:10.4f}")
    print()

# === RMT CONNECTION ===
print("="*70)
print("RANDOM MATRIX THEORY CONNECTION")
print("="*70)

# For GOE random matrices: eigenvalue spacing follows Wigner surmise
# As N → ∞, the empirical spectral distribution converges to Wigner semicircle
# The spectral gap for GOE matrices scales as ~ 2*sqrt(2N) - 2*sqrt(2N) + O(N^{-2/3})
# The fluctuations around the edge follow Tracy-Widom distribution
# CV of the top eigenvalue should decrease as N grows (concentration of measure)

for N in Ns:
    # Generate many GOE matrices, compute spectral gap statistics
    gaps = []
    entropies = []
    I_values = []
    for _ in range(100):
        M = np.random.randn(N, N)
        M = (M + M.T) / (2 * np.sqrt(N))
        M *= SCALE_RANDOM
        eigvals = np.sort(np.real(linalg.eigvalsh(M)))[::-1]
        gamma = eigvals[0] - eigvals[1]
        pos = eigvals[eigvals > 1e-12]
        if len(pos) > 0:
            p = pos / pos.sum()
            H = -np.sum(p * np.log(np.maximum(p, 1e-30)))
        else:
            H = 0
        gaps.append(gamma)
        entropies.append(H)
        I_values.append(gamma + H)
    
    cv_gap = np.std(gaps) / np.mean(gaps)
    cv_H = np.std(entropies) / np.mean(entropies)
    cv_I = np.std(I_values) / np.mean(I_values)
    print(f"N={N:4d}: CV(gamma)={cv_gap:.4f} CV(H)={cv_H:.4f} CV(I)={cv_I:.4f} | mean_gap={np.mean(gaps):.4f} mean_H={np.mean(entropies):.4f}")

# Save
output = {
    'Ns': Ns,
    'architectures': ['random', 'attention', 'hebbian'],
    'results': {f"{arch}_{N}": results[(arch, N)] for arch in ['random', 'attention', 'hebbian'] for N in Ns},
    'fit_results': fit_results,
    'params': {'noise': NOISE_STD, 'scale_random': SCALE_RANDOM, 'tau': TAU, 'steps': STEPS, 'samples': SAMPLES}
}
with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/dim_scaling_results_v2.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nResults saved to dim_scaling_results_v2.json")
