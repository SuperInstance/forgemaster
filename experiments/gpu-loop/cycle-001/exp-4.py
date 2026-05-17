"""
EXP-4: Architecture × Precision Interaction
E4 showed architecture strongly affects γ+H. Cycle 0 tested precision with (probably) one architecture.
Question: Does the conservation law's response to precision depend on coupling architecture?
"""
import numpy as np
import json

np.random.seed(789)

def hebbian_coupling(states, N_AGENTS, N):
    """Hebbian coupling: outer product sum."""
    J = np.zeros((N, N))
    for i in range(N_AGENTS):
        J += np.outer(states[i], states[i])
    return J / N_AGENTS

def attention_coupling(states, N_AGENTS, N):
    """Attention-like coupling: softmax-weighted."""
    scores = states @ states.T / np.sqrt(N)
    # Simplified softmax
    scores = scores - scores.max(axis=1, keepdims=True)
    weights = np.exp(scores) / np.exp(scores).sum(axis=1, keepdims=True)
    J = weights @ states
    return (J @ states.T) / N_AGENTS

def random_coupling(states, N_AGENTS, N):
    """Random Wigner coupling."""
    return np.random.randn(N, N) * 0.1 / np.sqrt(N)

def quantize(x, bits):
    if bits >= 32:
        return x
    levels = 2 ** (bits - 1)
    return np.round(np.clip(x, -1, 1) * (levels - 1)) / (levels - 1)

N = 20
ROUNDS = 200
N_AGENTS = 5

architectures = {
    "hebbian": hebbian_coupling,
    "attention": attention_coupling,
    "random": random_coupling,
}

precision_configs = {
    "fp32": [32] * N_AGENTS,
    "int8": [8] * N_AGENTS,
    "mixed_fp32_int8": [32, 32, 8, 8, 8],
    "mixed_extreme": [64, 32, 16, 8, 4],
}

results = {}

for arch_name, arch_fn in architectures.items():
    for prec_name, precs in precision_configs.items():
        config_key = f"{arch_name}_{prec_name}"
        gamma_h_trace = []
        
        for r in range(ROUNDS):
            states = np.random.randn(N_AGENTS, N) * 0.5
            
            # Quantize states per agent precision
            for i in range(N_AGENTS):
                states[i] = quantize(states[i], precs[i])
            
            J = arch_fn(states, N_AGENTS, N)
            J = (J + J.T) / 2  # symmetrize
            
            eigenvalues = np.linalg.eigvalsh(J)
            eigenvalues = eigenvalues[eigenvalues > 1e-12]
            
            if len(eigenvalues) < 2:
                continue
            
            gamma = eigenvalues[-1] - eigenvalues[-2]
            probs = eigenvalues / eigenvalues.sum()
            H = -np.sum(probs * np.log(probs + 1e-30))
            gamma_h_trace.append(gamma + H)
        
        if len(gamma_h_trace) < 10:
            results[config_key] = {"status": "FAILED"}
            continue
        
        trace = np.array(gamma_h_trace)
        results[config_key] = {
            "status": "OK",
            "gamma_plus_H_mean": float(np.mean(trace)),
            "gamma_plus_H_std": float(np.std(trace)),
            "gamma_plus_H_cv": float(np.std(trace) / (np.mean(trace) + 1e-30)),
            "conserved": "Yes" if float(np.std(trace) / (np.mean(trace) + 1e-30)) < 0.10 else "No",
        }

print("EXP-4: ARCHITECTURE × PRECISION")
print("=" * 80)
print(f"{'Config':<35} {'γ+H mean':>10} {'γ+H std':>10} {'CV':>10} {'Conserved':>10}")
print("-" * 75)
for name, r in results.items():
    if r["status"] == "OK":
        print(f"{name:<35} {r['gamma_plus_H_mean']:>10.4f} {r['gamma_plus_H_std']:>10.4f} {r['gamma_plus_H_cv']:>10.4f} {r['conserved']:>10}")

# Architecture-level analysis: does architecture change precision sensitivity?
print("\nARCHITECTURE SENSITIVITY:")
for arch in ["hebbian", "attention", "random"]:
    fp32_mean = results.get(f"{arch}_fp32", {}).get("gamma_plus_H_mean", 0)
    int8_mean = results.get(f"{arch}_int8", {}).get("gamma_plus_H_mean", 0)
    mixed_mean = results.get(f"{arch}_mixed_fp32_int8", {}).get("gamma_plus_H_mean", 0)
    
    fp32_cv = results.get(f"{arch}_fp32", {}).get("gamma_plus_H_cv", 0)
    mixed_cv = results.get(f"{arch}_mixed_fp32_int8", {}).get("gamma_plus_H_cv", 0)
    
    cv_change = (mixed_cv - fp32_cv) / (fp32_cv + 1e-10) * 100
    
    print(f"  {arch}: FP32 γ+H={fp32_mean:.3f}, INT8 γ+H={int8_mean:.3f}, "
          f"Mixed γ+H={mixed_mean:.3f}, CV change={cv_change:+.1f}%")

with open("results_exp4.json", "w") as f:
    json.dump(results, f, indent=2)
