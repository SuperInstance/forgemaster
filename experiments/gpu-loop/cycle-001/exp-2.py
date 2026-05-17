"""
EXP-2: Sub-2-bit Regime — Ternary and Low-Bit Exploration
Cycle 0 found that 1-bit crashes (NaN) but 2-bit works. What about ternary (-1, 0, +1)?
And different 2-bit schemes?
Question: Where is the TRUE breakdown boundary?
"""
import numpy as np
import json

np.random.seed(123)

def quantize_custom(x, scheme):
    """Various sub-2-bit quantization schemes."""
    if scheme == "fp32":
        return x
    elif scheme == "4bit":
        levels = 8
        return np.round(np.clip(x, -1, 1) * (levels-1)) / (levels-1)
    elif scheme == "3bit":
        levels = 4
        return np.round(np.clip(x, -1, 1) * (levels-1)) / (levels-1)
    elif scheme == "2bit_uniform":
        levels = 2
        return np.round(np.clip(x, -1, 1) * (levels-1)) / (levels-1)
    elif scheme == "ternary":
        # -1, 0, +1 (1.58 bits)
        return np.sign(x) * (np.abs(x) > 0.33).astype(float)
    elif scheme == "binary":
        # ±1 only (1 bit)
        return np.sign(x)
    elif scheme == "stochastic_1.5bit":
        # Stochastic ternary: randomize threshold
        threshold = np.random.uniform(0.1, 0.5, x.shape)
        return np.sign(x) * (np.abs(x) > threshold).astype(float)
    elif scheme == "1.5bit_deterministic":
        # 3 levels with symmetric thresholds
        return np.where(x > 0.5, 1.0, np.where(x < -0.5, -1.0, 0.0))
    else:
        return x

N = 20
ROUNDS = 200
N_AGENTS = 5

schemes = ["fp32", "4bit", "3bit", "2bit_uniform", "1.5bit_deterministic", "ternary", 
           "stochastic_1.5bit", "binary"]
# Also test heterogeneous: 2 FP32 agents + 3 low-bit agents
het_configs = [
    ("het_fp32_ternary", [32, 32, "ternary", "ternary", "ternary"]),
    ("het_fp32_binary", [32, 32, "binary", "binary", "binary"]),
    ("het_fp32_1.5bit", [32, 32, "1.5bit_deterministic", "1.5bit_deterministic", "1.5bit_deterministic"]),
]

results = {}

def run_experiment(quant_fn, name, is_het=False, agent_schemes=None):
    W = np.random.randn(N_AGENTS, N_AGENTS) * 0.1
    np.fill_diagonal(W, 0)
    
    gamma_h_trace = []
    nan_count = 0
    
    for r in range(ROUNDS):
        states = np.random.randn(N_AGENTS, N) * 0.5
        J = np.zeros((N, N))
        
        for i in range(N_AGENTS):
            for j in range(N_AGENTS):
                if i == j:
                    continue
                contrib = np.outer(states[i], states[j]) * W[i, j] / ROUNDS
                
                if is_het and agent_schemes:
                    # Use agent i's scheme for sending
                    scheme = agent_schemes[i]
                    if isinstance(scheme, int):
                        contrib = quantize_custom(contrib, "fp32")
                    else:
                        contrib = quantize_custom(contrib, scheme)
                else:
                    contrib = quant_fn(contrib)
                
                J += contrib
        
        J = (J + J.T) / 2  # symmetrize
        
        eigenvalues = np.linalg.eigvalsh(J)
        eigenvalues = eigenvalues[eigenvalues > 1e-12]
        
        if len(eigenvalues) < 2 or np.any(np.isnan(eigenvalues)):
            nan_count += 1
            continue
        
        gamma = eigenvalues[-1] - eigenvalues[-2]
        probs = eigenvalues / eigenvalues.sum()
        H = -np.sum(probs * np.log(probs + 1e-30))
        gamma_h_trace.append(gamma + H)
    
    if len(gamma_h_trace) < 10:
        return {"status": "FAILED", "nan_rounds": nan_count, "valid_rounds": len(gamma_h_trace)}
    
    trace = np.array(gamma_h_trace)
    return {
        "status": "OK",
        "gamma_plus_H_mean": float(np.mean(trace)),
        "gamma_plus_H_std": float(np.std(trace)),
        "gamma_plus_H_cv": float(np.std(trace) / (np.mean(trace) + 1e-30)),
        "nan_rounds": nan_count,
        "valid_rounds": len(gamma_h_trace),
        "conserved": "Yes" if float(np.std(trace) / (np.mean(trace) + 1e-30)) < 0.10 else "No",
    }

# Test homogeneous schemes
for scheme in schemes:
    fn = lambda x, s=scheme: quantize_custom(x, s)
    results[f"homo_{scheme}"] = run_experiment(fn, f"homo_{scheme}")

# Test heterogeneous configs
for name, schemes_list in het_configs:
    results[name] = run_experiment(None, name, is_het=True, agent_schemes=schemes_list)

print("EXP-2: SUB-2-BIT REGIME")
print("=" * 80)
print(f"{'Config':<30} {'Status':>8} {'γ+H mean':>10} {'γ+H std':>10} {'CV':>10} {'NaN rounds':>10} {'Conserved':>10}")
print("-" * 88)
for name, r in results.items():
    if r["status"] == "OK":
        print(f"{name:<30} {'OK':>8} {r['gamma_plus_H_mean']:>10.4f} {r['gamma_plus_H_std']:>10.4f} {r['gamma_plus_H_cv']:>10.4f} {r['nan_rounds']:>10} {r['conserved']:>10}")
    else:
        print(f"{name:<30} {'FAILED':>8} {'—':>10} {'—':>10} {'—':>10} {r['nan_rounds']:>10} {'—':>10}")

# Find breakdown boundary
print("\nBREAKDOWN ANALYSIS:")
for name, r in results.items():
    if r["status"] == "OK":
        cv = r["gamma_plus_H_cv"]
        marker = " ← BREAKDOWN?" if cv > 0.10 else ""
        print(f"  {name}: CV = {cv:.4f}{marker}")

with open("results_exp2.json", "w") as f:
    json.dump(results, f, indent=2)
