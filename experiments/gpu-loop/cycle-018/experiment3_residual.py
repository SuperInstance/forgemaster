"""
EXPERIMENT 3: Residual bound
For 100 trajectories, compute:
  - ε(x) = K[I](x) - I(x) (the Koopman residual)
  - ||x - x*|| (distance to fixed point)
Check if |ε(x)| ≤ C₂ · ||x - x*||

K[I](x) = I(Ax) = (Ax)^T P (Ax), I(x) = x^T P x
ε(x) = x^T (A^T P A - P) x = x^T Q x where Q = A^T P A - P
For the Lyapunov equation, P - A^T P A = I, so Q = -I.
Thus ε(x) = -||x||^2 and ||x - x*|| = ||x|| (fixed point at origin).
So |ε(x)| = ||x||^2 = ||x - x*||^2.
This is quadratic, not linear! The bound should be |ε(x)| ≤ C₂ · ||x - x*||^2.

But with coupling perturbation C, the residual changes.
Let's check both linear and quadratic bounds.
"""
import numpy as np
import json

np.random.seed(456)

n = 4
N_trials = 1000
N_steps = 50  # trajectory length

results_list = []

for trial in range(N_trials):
    # Decoupled stable system
    d_eigs = np.random.uniform(-0.8, 0.8, n)
    D = np.diag(d_eigs)
    
    # Coupling perturbation
    coupling_strength = np.random.uniform(0.01, 0.2)
    C = np.random.randn(n, n) * coupling_strength
    C = C * (1 - np.eye(n))
    
    # Full system
    A = D + C
    
    # Lyapunov matrix for nominal (D)
    P = np.eye(n)
    for _ in range(200):
        P = D.T @ P @ D + np.eye(n)
    
    # Residual: ε(x) = I(Ax) - I(x) = x^T (A^T P A - P) x
    Q = A.T @ P @ A - P
    Q_eigenvalues = np.linalg.eigvalsh(Q)
    
    # Generate trajectory
    x = np.random.randn(n) * 3.0
    for step in range(N_steps):
        dist_to_fp = np.linalg.norm(x)
        residual = x.T @ Q @ x  # ε(x)
        abs_residual = abs(residual)
        
        if dist_to_fp > 1e-10:
            ratio_linear = abs_residual / dist_to_fp
            ratio_quadratic = abs_residual / (dist_to_fp ** 2)
        else:
            continue
        
        results_list.append({
            'trial': trial,
            'step': step,
            'dist_to_fp': float(dist_to_fp),
            'residual': float(residual),
            'abs_residual': float(abs_residual),
            'ratio_linear': float(ratio_linear),
            'ratio_quadratic': float(ratio_quadratic),
            'coupling_strength': float(coupling_strength)
        })
        
        x = A @ x  # advance

linear_ratios = [r['ratio_linear'] for r in results_list]
quadratic_ratios = [r['ratio_quadratic'] for r in results_list]

# For the nominal case (D only), Q = -I, so |ε| = ||x||^2
# Linear bound: ||x||^2 / ||x|| = ||x|| → unbounded as ||x|| grows
# Quadratic bound: ||x||^2 / ||x||^2 = 1 → constant

# With coupling, we expect similar behavior near the fixed point
# Near x*: |ε(x)| ~ ||Q|| · ||x||^2 (quadratic dominates)

# Filter to near fixed point (dist < 1) for linear bound analysis
near_fp = [r for r in results_list if r['dist_to_fp'] < 1.0]
far_fp = [r for r in results_list if r['dist_to_fp'] >= 1.0]

C2_linear_near = max(r['ratio_linear'] for r in near_fp) if near_fp else 0
C2_quadratic = max(r['ratio_quadratic'] for r in results_list)

results = {
    'experiment': 'Residual bound',
    'n': n,
    'N_trials': N_trials,
    'N_steps': N_steps,
    'total_points': len(results_list),
    'Q_eigenvalues_sample': [float(e) for e in Q_eigenvalues],
    'linear_bound': {
        'C2_near_fp': float(C2_linear_near),
        'note': 'Linear bound only valid near fixed point; diverges far from it'
    },
    'quadratic_bound': {
        'C2_empirical_max': float(C2_quadratic),
        'C2_empirical_99th': float(np.percentile(quadratic_ratios, 99)),
        'C2_empirical_median': float(np.median(quadratic_ratios)),
        'note': '|ε(x)| ≤ C₂ · ||x - x*||² — quadratic bound is the correct scaling'
    },
    'percentiles_quadratic': {
        'p50': float(np.percentile(quadratic_ratios, 50)),
        'p90': float(np.percentile(quadratic_ratios, 90)),
        'p95': float(np.percentile(quadratic_ratios, 95)),
        'p99': float(np.percentile(quadratic_ratios, 99)),
        'max': float(C2_quadratic)
    }
}

print(json.dumps(results, indent=2))

with open('experiment3_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print(f"EXPERIMENT 3 SUMMARY")
print(f"{'='*60}")
print(f"Quadratic bound C₂ (max): {C2_quadratic:.6f}")
print(f"Quadratic bound C₂ (99th): {np.percentile(quadratic_ratios, 99):.6f}")
print(f"Linear bound near fp: {C2_linear_near:.6f}")
print(f"KEY FINDING: Residual scales quadratically with ||x-x*||")
print(f"|ε(x)| ≤ {C2_quadratic:.4f} · ||x - x*||²")
