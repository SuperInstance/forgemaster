"""
EXP-5: C(precision) Functional Form — Is the Conservation Constant Really Invariant?
Cycle 0 showed C varies from 7.2 (INT8) to 37.7 (FP64). That's 5× range.
"Substrate-invariant" is too strong. What's the ACTUAL relationship between precision and C?
Question: Does C(bits) follow a smooth curve, and if so what is it?
"""
import numpy as np
import json
from scipy import stats

np.random.seed(1010)

def quantize(x, bits):
    if bits >= 64:
        return x
    levels = 2 ** (bits - 1)
    return np.round(np.clip(x, -1, 1) * (levels - 1)) / (levels - 1)

def estimate_C(N, N_AGENTS, bits, ROUNDS=300):
    """Estimate conservation constant C for given bit precision."""
    gamma_h_values = []
    
    for r in range(ROUNDS):
        states = np.random.randn(N_AGENTS, N) * 0.5
        for i in range(N_AGENTS):
            states[i] = quantize(states[i], bits)
        
        W = np.random.randn(N_AGENTS, N_AGENTS) * 0.1
        np.fill_diagonal(W, 0)
        
        J = np.zeros((N, N))
        for i in range(N_AGENTS):
            for j in range(N_AGENTS):
                if i != j:
                    J += np.outer(states[i], states[j]) * W[i, j] / ROUNDS
        
        J = (J + J.T) / 2
        eigenvalues = np.linalg.eigvalsh(J)
        eigenvalues = eigenvalues[eigenvalues > 1e-12]
        
        if len(eigenvalues) >= 2:
            gamma = eigenvalues[-1] - eigenvalues[-2]
            probs = eigenvalues / eigenvalues.sum()
            H = -np.sum(probs * np.log(probs + 1e-30))
            gamma_h_values.append(gamma + H)
    
    if len(gamma_h_values) < 10:
        return None
    
    trace = np.array(gamma_h_values)
    return {
        "C_mean": float(np.mean(trace)),
        "C_std": float(np.std(trace)),
        "C_cv": float(np.std(trace) / (np.mean(trace) + 1e-30)),
        "C_median": float(np.median(trace)),
        "bits": bits,
        "log2_C": float(np.log2(np.mean(trace))),
    }

N = 20
N_AGENTS = 5
bit_range = [2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 23, 32, 52, 64]
results = {}

for bits in bit_range:
    print(f"  Testing {bits}-bit...")
    r = estimate_C(N, N_AGENTS, bits)
    if r:
        results[f"{bits}bit"] = r
        print(f"    C = {r['C_mean']:.4f} ± {r['C_std']:.4f} (CV = {r['C_cv']:.4f})")
    else:
        print(f"    FAILED")

print("\n\nEXP-5: C(bits) FUNCTIONAL FORM")
print("=" * 70)
print(f"{'Bits':>6} {'C mean':>10} {'C std':>10} {'CV':>10} {'log₂(C)':>10}")
print("-" * 46)
for name, r in results.items():
    print(f"{r['bits']:>6} {r['C_mean']:>10.4f} {r['C_std']:>10.4f} {r['C_cv']:>10.4f} {r['log2_C']:>10.4f}")

# Fit functional forms
bits_list = [r['bits'] for r in results.values()]
c_list = [r['C_mean'] for r in results.values()]

if len(bits_list) > 3:
    # Linear fit: C = a + b*bits
    slope_lin, intercept_lin, r_lin, _, _ = stats.linregress(bits_list, c_list)
    
    # Log fit: C = a + b*ln(bits)
    log_bits = np.log(bits_list)
    slope_log, intercept_log, r_log, _, _ = stats.linregress(log_bits, c_list)
    
    # Exponential fit: C = a * exp(b*bits)
    try:
        slope_exp, intercept_exp, r_exp, _, _ = stats.linregress(bits_list, np.log(c_list))
    except:
        r_exp = 0
    
    # Power fit: C = a * bits^b
    try:
        slope_pow, intercept_pow, r_pow, _, _ = stats.linregress(np.log(bits_list), np.log(c_list))
    except:
        r_pow = 0
    
    print(f"\nFIT COMPARISON:")
    print(f"  Linear (C = a + b·bits):      R² = {r_lin**2:.4f}")
    print(f"  Log (C = a + b·ln(bits)):      R² = {r_log**2:.4f}")
    print(f"  Exponential (C = a·exp(b·bits)): R² = {r_exp**2:.4f}")
    print(f"  Power (C = a·bits^b):           R² = {r_pow**2:.4f}")
    
    best = max([(r_lin**2, "Linear"), (r_log**2, "Log"), (r_exp**2, "Exponential"), (r_pow**2, "Power")])
    print(f"\n  BEST FIT: {best[1]} (R² = {best[0]:.4f})")
    
    # Key question: is C constant?
    c_range = max(c_list) - min(c_list)
    c_mean = np.mean(c_list)
    print(f"\n  C range: {min(c_list):.3f} — {max(c_list):.3f} (span = {c_range:.3f})")
    print(f"  Relative variation: {c_range/c_mean*100:.1f}%")
    if c_range / c_mean < 0.10:
        print("  → C is approximately CONSTANT (substrate-invariant)")
    elif c_range / c_mean < 0.30:
        print("  → C varies MODERATELY with precision")
    else:
        print("  → C varies SIGNIFICANTLY with precision — NOT substrate-invariant")

with open("results_exp5.json", "w") as f:
    json.dump(results, f, indent=2)
