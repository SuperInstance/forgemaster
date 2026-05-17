"""
Experiment 2: Supermartingale decay rate map
For each (architecture, activation) pair, measure exponential decay rate α from 50 samples.
"""
import numpy as np
import json
import os

np.random.seed(123)

architectures = [3, 4, 5, 6, 8, 10, 16]  # matrix sizes
activations = ['tanh', 'relu', 'sigmoid', 'leaky_relu', 'softplus', 'elu', 'linear']

def apply_activation(x, act):
    if act == 'tanh':
        return np.tanh(x)
    elif act == 'relu':
        return np.maximum(0, x)
    elif act == 'sigmoid':
        return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))
    elif act == 'leaky_relu':
        return np.where(x > 0, x, 0.01 * x)
    elif act == 'softplus':
        return np.log1p(np.exp(np.clip(x, -50, 50)))
    elif act == 'elu':
        return np.where(x > 0, x, np.exp(x) - 1)
    elif act == 'linear':
        return x
    return x

def jacobian_fn(x, W, act):
    """Numerical Jacobian of activation(Wx + b) w.r.t. x"""
    n = len(x)
    eps = 1e-6
    J = np.zeros((n, n))
    for j in range(n):
        x_plus = x.copy()
        x_minus = x.copy()
        x_plus[j] += eps
        x_minus[j] -= eps
        f_plus = apply_activation(W @ x_plus, act)
        f_minus = apply_activation(W @ x_minus, act)
        J[:, j] = (f_plus - f_minus) / (2 * eps)
    return J

SAMPLES = 50
TRAJ_LEN = 100

heatmap = {}
raw_data = []

for arch in architectures:
    for act in activations:
        alphas = []
        for s in range(SAMPLES):
            # Random contractive weight matrix
            W = np.random.randn(arch, arch) * 0.3
            # Make it contractive via spectral normalization
            eigvals = np.linalg.eigvals(W)
            spectral_radius = np.max(np.abs(eigvals))
            if spectral_radius > 0.9:
                W = W * (0.9 / spectral_radius)
            
            x = np.random.randn(arch)
            I_trajectory = []
            
            for t in range(TRAJ_LEN):
                J = jacobian_fn(x, W, act)
                # "Information" proxy: determinant-based metric
                # I(t) = |det(I - J^T J)| (distance from identity)
                M = np.eye(arch) - J.T @ J
                det_val = np.linalg.det(M)
                I_val = abs(det_val) if abs(det_val) > 1e-15 else 1e-15
                I_trajectory.append(I_val)
                x = apply_activation(W @ x, act)
            
            # Fit exponential decay: I(t) ≈ I_0 * exp(-α*t)
            I_arr = np.array(I_trajectory)
            I_arr = np.maximum(I_arr, 1e-15)
            log_I = np.log(I_arr)
            t_arr = np.arange(len(log_I))
            
            # Linear fit to log(I) vs t
            if len(t_arr) > 2:
                slope, intercept = np.polyfit(t_arr, log_I, 1)
                alpha = -slope  # decay rate
                alphas.append(max(alpha, 0))  # decay should be positive
        
        mean_alpha = np.mean(alphas) if alphas else 0
        std_alpha = np.std(alphas) if alphas else 0
        key = f"{arch}x{act}"
        heatmap[key] = {
            "architecture": arch,
            "activation": act,
            "mean_decay_rate": round(mean_alpha, 4),
            "std_decay_rate": round(std_alpha, 4),
            "samples": len(alphas),
            "alphas": [round(a, 6) for a in alphas[:10]]  # first 10 for brevity
        }
        raw_data.append((arch, act, round(mean_alpha, 4), round(std_alpha, 4)))
        print(f"  arch={arch:2d}, act={act:12s}: α={mean_alpha:.4f} ± {std_alpha:.4f}")

# Save results
outdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(outdir, "exp2_results.json"), "w") as f:
    json.dump({"experiment": "supermartingale_decay_map", "heatmap": heatmap}, f, indent=2)

print(f"\nExperiment 2 complete. {len(heatmap)} (arch, activation) pairs measured.")
print(f"Fastest decay: {max(raw_data, key=lambda x: x[2])}")
print(f"Slowest decay: {min(raw_data, key=lambda x: x[2])}")
