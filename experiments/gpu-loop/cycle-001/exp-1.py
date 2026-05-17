"""
EXP-1: Asymmetric Coupling — Direction-Dependent Precision Translation
The biggest gap from Cycle 0. Agent A (FP64) sends to B (INT8) with LOSSY quantization.
Agent B (INT8) sends to A (FP64) with LOSSLESS expansion. This makes J asymmetric.
Question: Does the conservation law survive asymmetric coupling?
"""
import numpy as np
import json

np.random.seed(42)

def quantize(x, bits):
    """Quantize array to signed integer with given bits."""
    if bits >= 64:
        return x
    levels = 2 ** (bits - 1)
    x_clip = np.clip(x, -1.0, 1.0)
    x_q = np.round(x_clip * (levels - 1)) / (levels - 1)
    return x_q

def compute_spectral_props(M, label=""):
    """Compute spectral gap and spectral entropy."""
    eigenvalues = np.linalg.eigvalsh(M) if np.allclose(M, M.T) else np.sort(np.abs(np.linalg.eigvals(M)))
    eigenvalues = eigenvalues[eigenvalues > 1e-12]
    if len(eigenvalues) < 2:
        return {"gamma": 0, "H": 0, "gamma_plus_H": 0, "n_eigs": len(eigenvalues)}
    
    gamma = eigenvalues[-1] - eigenvalues[-2]  # spectral gap
    probs = eigenvalues / eigenvalues.sum()
    H = -np.sum(probs * np.log(probs + 1e-30))
    return {"gamma": float(gamma), "H": float(H), "gamma_plus_H": float(gamma + H), 
            "n_eigs": len(eigenvalues)}

N = 20  # matrix size
ROUNDS = 200
N_AGENTS = 5
results = {}

configs = {
    "symmetric_fp32": {"precisions": [32]*N_AGENTS, "asymmetric": False},
    "symmetric_mixed": {"precisions": [64, 32, 16, 8, 8], "asymmetric": False},
    "asymmetric_fp32_int8": {"precisions": [32, 32, 8, 8, 8], "asymmetric": True},
    "asymmetric_fp64_int4": {"precisions": [64, 64, 4, 4, 4], "asymmetric": True},
    "asymmetric_extreme": {"precisions": [64, 32, 16, 4, 2], "asymmetric": True},
}

for config_name, config in configs.items():
    precs = config["precisions"]
    asymmetric = config["asymmetric"]
    
    # Initialize coupling weights
    W = np.random.randn(N_AGENTS, N_AGENTS) * 0.1
    np.fill_diagonal(W, 0)
    
    gamma_h_trace = []
    is_symmetric_trace = []
    asymmetry_metric_trace = []
    
    for r in range(ROUNDS):
        # Each agent produces a state vector
        states = np.random.randn(N_AGENTS, N) * 0.5
        
        # Build coupling matrix
        J = np.zeros((N, N))
        for i in range(N_AGENTS):
            for j in range(N_AGENTS):
                if i == j:
                    continue
                
                contrib = np.outer(states[i], states[j]) * W[i, j] / ROUNDS
                
                if asymmetric:
                    # Agent i sends to j: quantize at SENDER's precision
                    # This means J[i,j] sees precision of agent i (row)
                    # But agent j receives at its own precision
                    send_prec = precs[i]
                    recv_prec = precs[j]
                    
                    # Quantize at sender precision
                    contrib = quantize(contrib, send_prec)
                    # If receiver has lower precision, also quantize at receiver precision
                    # This models the "perception" of the receiver
                    if recv_prec < send_prec:
                        contrib = quantize(contrib, recv_prec)
                else:
                    # Symmetric: both agents communicate at the LOWER of their precisions
                    min_prec = min(precs[i], precs[j])
                    contrib = quantize(contrib, min_prec)
                
                J += contrib
        
        # Make J symmetric (average J and J^T) for symmetric configs
        if not asymmetric:
            J = (J + J.T) / 2
        
        props = compute_spectral_props(J, config_name)
        gamma_h_trace.append(props["gamma_plus_H"])
        is_symmetric_trace.append(float(np.max(np.abs(J - J.T))))
        asymmetry_metric_trace.append(float(np.linalg.norm(J - J.T, 'fro') / (np.linalg.norm(J, 'fro') + 1e-30)))
    
    trace = np.array(gamma_h_trace)
    asym = np.array(asymmetry_metric_trace)
    results[config_name] = {
        "gamma_plus_H_mean": float(np.mean(trace)),
        "gamma_plus_H_std": float(np.std(trace)),
        "gamma_plus_H_cv": float(np.std(trace) / (np.mean(trace) + 1e-30)),
        "asymmetry_mean": float(np.mean(asym)),
        "max_asymmetry": float(np.max(is_symmetric_trace)),
        "first_50_cv": float(np.std(trace[:50]) / (np.mean(trace[:50]) + 1e-30)),
        "last_100_cv": float(np.std(trace[100:]) / (np.mean(trace[100:]) + 1e-30)),
        "conserved": "Yes" if float(np.std(trace) / (np.mean(trace) + 1e-30)) < 0.10 else "No",
    }

# Check: does asymmetric coupling produce complex eigenvalues?
print("EXP-1: ASYMMETRIC COUPLING")
print("=" * 60)
print(f"{'Config':<30} {'γ+H mean':>10} {'γ+H std':>10} {'CV':>10} {'Asymmetry':>12} {'Conserved':>10}")
print("-" * 82)
for name, r in results.items():
    print(f"{name:<30} {r['gamma_plus_H_mean']:>10.4f} {r['gamma_plus_H_std']:>10.4f} {r['gamma_plus_H_cv']:>10.4f} {r['asymmetry_mean']:>12.6f} {r['conserved']:>10}")

# Key comparison
sym_cv = results["symmetric_fp32"]["gamma_plus_H_cv"]
sym_mixed_cv = results["symmetric_mixed"]["gamma_plus_H_cv"]
asym_cv = results["asymmetric_fp32_int8"]["gamma_plus_H_cv"]
asym_extreme_cv = results["asymmetric_extreme"]["gamma_plus_H_cv"]

print(f"\nKEY COMPARISON:")
print(f"  Symmetric FP32 CV:         {sym_cv:.4f}")
print(f"  Symmetric Mixed CV:        {sym_mixed_cv:.4f}")
print(f"  Asymmetric FP32/INT8 CV:   {asym_cv:.4f}")
print(f"  Asymmetric Extreme CV:     {asym_extreme_cv:.4f}")

if asym_cv > 3 * sym_cv:
    print("  → ASYMMETRIC COUPLING BREAKS CONSERVATION")
elif asym_cv > 1.5 * sym_cv:
    print("  → ASYMMETRIC COUPLING WEAKENS CONSERVATION")
else:
    print("  → ASYMMETRIC COUPLING PRESERVES CONSERVATION")

with open("results_exp1.json", "w") as f:
    json.dump(results, f, indent=2)
