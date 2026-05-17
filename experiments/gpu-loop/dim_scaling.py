#!/usr/bin/env python3
"""
Dimensional Scaling Experiment: CV(I) ~ 1/N?
Sweeps N = 5, 10, 20, 50, 100 across 3 architectures.
For each: 10 random coupling matrices, 50-step trajectories, compute CV(I).
"""

import numpy as np
from scipy import linalg
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# --- Coupling matrix generators ---

def random_coupling(N):
    """GOE random matrix, scaled by 1/sqrt(N)"""
    M = np.random.randn(N, N)
    M = (M + M.T) / (2 * np.sqrt(N))
    return M

def attention_coupling(x, tau=1.0):
    """State-dependent attention coupling C(x) = softmax(xx^T / (tau*sqrt(N)))"""
    N = len(x)
    logits = np.outer(x, x) / (tau * np.sqrt(N))
    logits -= logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(logits)
    C = exp_logits / exp_logits.sum(axis=1, keepdims=True)
    return C

def hebbian_coupling(x):
    """State-dependent Hebbian coupling C(x) = xx^T / N"""
    N = len(x)
    return np.outer(x, x) / N

# --- Spectral quantities ---

def compute_I(C):
    """Compute I = gamma + H from coupling matrix C.
    Uses eigenvalues of (C + C^T)/2 for asymmetric matrices."""
    C_sym = (C + C.T) / 2.0
    eigvals = np.real(linalg.eigvalsh(C_sym))
    eigvals = np.sort(eigvals)[::-1]  # descending
    
    # Spectral gap: lambda_1 - lambda_2
    gamma = eigvals[0] - eigvals[1] if len(eigvals) > 1 else eigvals[0]
    
    # Participation entropy (only positive eigenvalues)
    pos = eigvals[eigvals > 1e-12]
    if len(pos) == 0:
        return gamma, 0.0, gamma
    p = pos / pos.sum()
    H = -np.sum(p * np.log(np.maximum(p, 1e-30)))
    
    I = gamma + H
    return gamma, H, I

# --- Run trajectory ---

def run_trajectory(C_func, x0, steps, coupling_type, tau=1.0):
    """Run x_{t+1} = tanh(C(x) @ x) for given steps."""
    x = x0.copy()
    I_vals = []
    
    for t in range(steps):
        if coupling_type == 'attention':
            C = attention_coupling(x, tau=tau)
        elif coupling_type == 'hebbian':
            C = hebbian_coupling(x)
        elif coupling_type == 'random':
            # Static coupling — C_func is the matrix itself
            C = C_func
        else:
            raise ValueError(f"Unknown coupling type: {coupling_type}")
        
        _, _, I = compute_I(C)
        I_vals.append(I)
        
        x = np.tanh(C @ x)
    
    return np.array(I_vals)

def compute_cv(values):
    """Coefficient of variation."""
    mean = np.mean(values)
    if abs(mean) < 1e-15:
        return 0.0
    return np.std(values) / abs(mean)

# --- Main experiment ---

Ns = [5, 10, 20, 50, 100]
samples_per_N = 10
trajectory_steps = 50
architectures = ['random', 'attention', 'hebbian']

results = {}  # (arch, N) -> list of CVs

for arch in architectures:
    for N in Ns:
        cvs = []
        for s in range(samples_per_N):
            # Random initial condition
            x0 = np.random.randn(N) * 0.5
            
            if arch == 'random':
                C = random_coupling(N)
                I_vals = run_trajectory(C, x0, trajectory_steps, 'random')
            elif arch == 'attention':
                I_vals = run_trajectory(None, x0, trajectory_steps, 'attention', tau=1.0)
            elif arch == 'hebbian':
                I_vals = run_trajectory(None, x0, trajectory_steps, 'hebbian')
            
            cv = compute_cv(I_vals)
            cvs.append(cv)
        
        results[(arch, N)] = cvs
        mean_cv = np.mean(cvs)
        std_cv = np.std(cvs)
        print(f"{arch:12s} N={N:4d}: mean_CV={mean_cv:.6f} ± {std_cv:.6f}")

print("\n" + "="*70)
print("POWER LAW FITS: CV = a * N^b")
print("="*70)

for arch in architectures:
    mean_cvs = [np.mean(results[(arch, N)]) for N in Ns]
    log_N = np.log(Ns)
    log_CV = np.log(np.maximum(mean_cvs, 1e-10))
    
    slope, intercept, r_value, p_value, std_err = linregress(log_N, log_CV)
    b = slope
    a = np.exp(intercept)
    R2 = r_value**2
    
    print(f"\n{arch}:")
    print(f"  CV = {a:.6f} * N^{b:.4f}")
    print(f"  R² = {R2:.4f}")
    print(f"  Raw CVs: {[f'{v:.6f}' for v in mean_cvs]}")
    
    # Also test 1/N fit specifically
    inv_N = [1.0/n for n in Ns]
    slope2, intercept2, r2_val, p2, se2 = linregress(inv_N, mean_cvs)
    print(f"  Linear in 1/N: R² = {r2_val**2:.4f}")
    
    # Test 1/N²
    inv_N2 = [1.0/n**2 for n in Ns]
    slope3, intercept3, r3_val, p3, se3 = linregress(inv_N2, mean_cvs)
    print(f"  Linear in 1/N²: R² = {r3_val**2:.4f}")
    
    # Test log(N)/N
    logN_over_N = [np.log(n)/n for n in Ns]
    slope4, intercept4, r4_val, p4, se4 = linregress(logN_over_N, mean_cvs)
    print(f"  Linear in ln(N)/N: R² = {r4_val**2:.4f}")

# --- Detailed per-sample output ---
print("\n" + "="*70)
print("DETAILED RESULTS TABLE")
print("="*70)
print(f"{'Arch':12s} {'N':>4s} | ", end="")
for s in range(samples_per_N):
    print(f"{'S'+str(s+1):>9s}", end=" ")
print(f"| {'Mean':>9s} {'Std':>9s}")
print("-"*140)

for arch in architectures:
    for N in Ns:
        cvs = results[(arch, N)]
        print(f"{arch:12s} {N:4d} | ", end="")
        for cv in cvs:
            print(f"{cv:9.6f}", end=" ")
        print(f"| {np.mean(cvs):9.6f} {np.std(cvs):9.6f}")
    print()

# --- Save results for plotting ---
import json
output = {
    'Ns': Ns,
    'architectures': architectures,
    'results': {f"{arch}_{N}": results[(arch, N)] for arch in architectures for N in Ns}
}
with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/dim_scaling_results.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nResults saved to dim_scaling_results.json")
