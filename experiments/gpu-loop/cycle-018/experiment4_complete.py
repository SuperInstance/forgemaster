"""
EXPERIMENT 4: Complete bound verification
For 100 trajectories, verify: |I(x_{t+1}) - I(x_t)| ≤ C₁·||[D,C]||·I(x) + C₂·||x - x*||²

The invariant change along a trajectory step:
ΔI = I(Ax) - I(x) = ε(x) = x^T Q x where Q = A^T P A - P

For nominal (D): Q = -I, so ΔI = -||x||^2 (pure contraction)
With coupling C: Q = A^T P A - P = (D+C)^T P (D+C) - P
  = D^T P D + D^T P C + C^T P D + C^T P C - P
  = (D^T P D - P) + (D^T P C + C^T P D) + C^T P C
  = -I + coupling_terms

So the coupling adds to the residual in a structured way.
"""
import numpy as np
import json

np.random.seed(789)

n = 4
N_trials = 500
N_steps = 30

results_list = []

for trial in range(N_trials):
    d_eigs = np.random.uniform(-0.85, 0.85, n)
    D = np.diag(d_eigs)
    
    coupling_strength = np.random.uniform(0.01, 0.25)
    C = np.random.randn(n, n) * coupling_strength
    C = C * (1 - np.eye(n))
    
    A = D + C
    
    # Lyapunov for nominal D
    P = np.eye(n)
    for _ in range(200):
        P = D.T @ P @ D + np.eye(n)
    
    # Commutator
    comm = D @ C - C @ D
    comm_norm = np.linalg.norm(comm, 2)
    
    # Residual matrix
    Q = A.T @ P @ A - P
    Q_norm = np.linalg.norm(Q, 2)
    
    x = np.random.randn(n) * 2.0
    
    for step in range(N_steps):
        I_t = x.T @ P @ x
        x_next = A @ x
        I_next = x_next.T @ P @ x_next
        delta_I = abs(I_next - I_t)
        dist_fp = np.linalg.norm(x)
        
        if dist_fp < 1e-10:
            x = x_next
            continue
        
        # RHS terms
        term1 = comm_norm * I_t  # C₁·||[D,C]||·I(x)
        term2_coeff = I_t  # or ||x-x*||^2
        
        if comm_norm > 1e-10:
            ratio_full = delta_I / (comm_norm * I_t + dist_fp**2) if (comm_norm * I_t + dist_fp**2) > 1e-10 else 0
            ratio_coupling = delta_I / (comm_norm * I_t) if comm_norm * I_t > 1e-10 else 0
            ratio_residual = delta_I / (dist_fp**2) if dist_fp**2 > 1e-10 else 0
        else:
            ratio_full = 0
            ratio_coupling = 0
            ratio_residual = delta_I / (dist_fp**2) if dist_fp**2 > 1e-10 else 0
        
        results_list.append({
            'trial': trial,
            'step': step,
            'delta_I': float(delta_I),
            'I_t': float(I_t),
            'dist_fp': float(dist_fp),
            'comm_norm': float(comm_norm),
            'coupling_strength': float(coupling_strength),
            'ratio_full': float(ratio_full),
            'ratio_coupling': float(ratio_coupling),
            'ratio_residual': float(ratio_residual)
        })
        
        x = x_next

# Analyze the complete bound
ratios_full = [r['ratio_full'] for r in results_list if r['ratio_full'] > 0]
ratios_coupling = [r['ratio_coupling'] for r in results_list if r['ratio_coupling'] > 0]
ratios_residual = [r['ratio_residual'] for r in results_list if r['ratio_residual'] > 0]

# The bound: |ΔI| ≤ C₁·||[D,C]||·I(x) + C₂·||x-x*||²
# Find empirical C₁ and C₂ that make this hold

# For each point, we need: delta_I ≤ C₁·comm_norm·I_t + C₂·dist_fp²
# This is a 2D linear program. Find min (C₁, C₂) such that all constraints hold.

# Simple approach: fit C₁ from pure coupling contribution, C₂ from pure residual
# Or just find the constant that works for the combined bound.

# Direct optimization: for each point, compute required (C₁, C₂)
# C₁ ≥ (delta_I - C₂·dist²) / (comm·I)  if denominator > 0
# For simplicity, find single constant C such that delta_I ≤ C * (comm·I + dist²)

if ratios_full:
    C_combined_99 = np.percentile(ratios_full, 99)
    C_combined_max = max(ratios_full)
    C_combined_median = np.median(ratios_full)
else:
    C_combined_99 = C_combined_max = C_combined_median = 0

if ratios_residual:
    C2_residual_99 = np.percentile(ratios_residual, 99)
    C2_residual_max = max(ratios_residual)
else:
    C2_residual_99 = C2_residual_max = 0

# Now solve for optimal C₁, C₂ via least squares
# delta_I ≈ C₁ · comm_norm · I_t + C₂ · dist_fp²
A_mat = np.array([[r['comm_norm'] * r['I_t'], r['dist_fp']**2] for r in results_list])
b_vec = np.array([r['delta_I'] for r in results_list])

# Non-negative least squares
from numpy.linalg import lstsq
coeffs, residuals, rank, sv = lstsq(A_mat, b_vec, rcond=None)
C1_fit = max(0, coeffs[0])
C2_fit = max(0, coeffs[1])

# Verify with fitted constants
violations = 0
for r in results_list:
    bound = C1_fit * r['comm_norm'] * r['I_t'] + C2_fit * r['dist_fp']**2
    if r['delta_I'] > bound * (1 + 1e-6):
        violations += 1

# Make C1_fit, C2_fit slightly larger to account for all points
# Use envelope approach
C1_env = max(coeffs[0], 0) * 1.05
C2_env = max(coeffs[1], 0) * 1.05
# Verify
for r in results_list:
    bound = C1_env * r['comm_norm'] * r['I_t'] + C2_env * r['dist_fp']**2
    if r['delta_I'] > bound * (1 + 1e-6):
        C1_env *= 1.1
        C2_env *= 1.1

results = {
    'experiment': 'Complete bound verification',
    'n': n,
    'N_trials': N_trials,
    'total_points': len(results_list),
    'fitted_constants': {
        'C1': float(C1_fit),
        'C2': float(C2_fit),
        'bound': f'|ΔI| ≤ {C1_fit:.4f}·||[D,C]||·I(x) + {C2_fit:.4f}·||x-x*||²'
    },
    'envelope_constants': {
        'C1': float(C1_env),
        'C2': float(C2_env),
        'violations': int(violations)
    },
    'combined_bound': {
        'C_combined_99th': float(C_combined_99),
        'C_combined_max': float(C_combined_max),
        'bound': f'|ΔI| ≤ {C_combined_99:.4f} · (||[D,C]||·I(x) + ||x-x*||²)'
    },
    'pure_residual_C2': {
        'C2_99th': float(C2_residual_99),
        'C2_max': float(C2_residual_max)
    },
    'percentiles_ratio_full': {
        'p50': float(np.percentile(ratios_full, 50)) if ratios_full else 0,
        'p90': float(np.percentile(ratios_full, 90)) if ratios_full else 0,
        'p95': float(np.percentile(ratios_full, 95)) if ratios_full else 0,
        'p99': float(np.percentile(ratios_full, 99)) if ratios_full else 0,
    }
}

print(json.dumps(results, indent=2))

with open('experiment4_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print(f"EXPERIMENT 4 SUMMARY")
print(f"{'='*60}")
print(f"Fitted: |ΔI| ≤ {C1_fit:.4f}·||[D,C]||·I(x) + {C2_fit:.4f}·||x-x*||²")
print(f"Violations with fitted: {violations}/{len(results_list)}")
print(f"Combined: |ΔI| ≤ {C_combined_99:.4f}·(||[D,C]||·I(x) + ||x-x*||²)")
print(f"Pure residual C₂ (99th): {C2_residual_99:.4f}")
