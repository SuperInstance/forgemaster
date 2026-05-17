#!/usr/bin/env python3
"""
EXP-5: Ternary→Binary Transition Mapping
Fine-grained sweep from 3-level (ternary) to 2-level (binary) quantization.
Is the conservation breakdown sharp (phase transition) or gradual?
Also tests intermediate quantization levels (2.5-bit, etc.)
"""
import numpy as np
import json

np.random.seed(321)
N = 50
n_rounds = 150
n_agents = 5

def quantize(value, n_levels):
    """Quantize a value to n_levels symmetric levels."""
    if n_levels < 2:
        return 0.0
    levels = np.linspace(-1, 1, n_levels)
    idx = np.argmin(np.abs(levels - value))
    return levels[idx]

def quantize_matrix(J, n_levels):
    """Quantize coupling matrix to n_levels."""
    J_norm = J / (np.max(np.abs(J)) + 1e-12)
    J_quant = np.vectorize(lambda v: quantize(v, n_levels))(J_norm)
    return J_quant * (np.max(np.abs(J)) + 1e-12)

def make_heterogeneous_fleet(N, n_agents, fp32_agents, quantized_agents, n_levels):
    """Create fleet with mixed FP32 and quantized agents."""
    # Build coupling matrix from agent interactions
    J = np.random.randn(N, N) / np.sqrt(N)
    J = (J + J.T) / 2
    
    # Quantize rows/columns corresponding to quantized agents
    agent_size = N // n_agents
    for i in range(n_agents):
        start = i * agent_size
        end = (i + 1) * agent_size
        if i >= fp32_agents:
            # This agent is quantized
            block = J[start:end, :]
            J[start:end, :] = quantize_matrix(block, n_levels)
            block_col = J[:, start:end]
            J[:, start:end] = quantize_matrix(block_col, n_levels)
    
    return (J + J.T) / 2  # re-symmetrize

def run_conservation_experiment(J, n_rounds=150):
    """Run dynamics and measure γ+H conservation."""
    evals = np.linalg.eigvalsh(J)
    abs_evals = np.sort(np.abs(evals))
    
    if np.any(np.isnan(evals)):
        return {'cv': float('nan'), 'mean': float('nan'), 'valid': False}
    
    gamma = abs_evals[-1] - abs_evals[-2] if len(abs_evals) > 1 else 0
    probs = abs_evals / (np.sum(abs_evals) + 1e-12)
    H = -np.sum(probs * np.log(probs + 1e-12))
    
    # Dynamic measurement
    gh_values = []
    x = np.random.randn(N)
    for t in range(n_rounds):
        x = J @ x
        norm = np.linalg.norm(x)
        if norm > 1e10 or norm < 1e-10 or np.any(np.isnan(x)):
            break
        x = x / norm
        gh_values.append(gamma + H)
    
    if len(gh_values) < 10:
        return {'cv': float('nan'), 'mean': float('nan'), 'valid': False, 'n_valid': len(gh_values)}
    
    mean_gh = np.mean(gh_values)
    cv = np.std(gh_values) / (mean_gh + 1e-12)
    return {'cv': float(cv), 'mean': float(mean_gh), 'valid': True, 'n_valid': len(gh_values)}

# Fine-grained sweep of quantization levels
levels_to_test = list(range(2, 20))  # 2 (binary) through 19 levels

results = {}
print("=" * 80)
print("EXP-5: Quantization Level vs Conservation")
print("=" * 80)
print(f"Config: {n_agents} agents, 2 FP32 + 3 quantized, N={N}")
print(f"\n{'Levels':8s} | {'Bits':8s} | {'CV':10s} | {'Mean γ+H':10s} | {'Conserved':10s}")
print("-" * 60)

for n_levels in levels_to_test:
    cv_values = []
    mean_values = []
    
    for trial in range(30):
        J = make_heterogeneous_fleet(N, n_agents, fp32_agents=2, quantized_agents=3, n_levels=n_levels)
        result = run_conservation_experiment(J)
        if result['valid']:
            cv_values.append(result['cv'])
            mean_values.append(result['mean'])
    
    if cv_values:
        mean_cv = np.mean(cv_values)
        mean_gh = np.mean(mean_values)
        bits = np.log2(n_levels)
        conserved = "✓" if mean_cv < 0.05 else ("~" if mean_cv < 0.15 else "✗")
        
        results[str(n_levels)] = {
            'n_levels': n_levels,
            'bits': float(bits),
            'mean_cv': float(mean_cv),
            'std_cv': float(np.std(cv_values)),
            'mean_gh': float(mean_gh),
            'n_valid': len(cv_values)
        }
        
        print(f"{n_levels:8d} | {bits:8.2f} | {mean_cv:10.4f} | {mean_gh:10.4f} | {conserved:10s}")

# Also test: gradual transition from ternary to binary
print(f"\n{'='*80}")
print("INTERPOLATION: Ternary → Binary (3-level to 2-level)")
print(f"{'='*80}")

for alpha in np.linspace(0, 1, 21):  # 0 = pure ternary, 1 = pure binary
    cv_values = []
    for trial in range(30):
        J = make_heterogeneous_fleet(N, n_agents, fp32_agents=2, quantized_agents=3, n_levels=3)
        J_binary = make_heterogeneous_fleet(N, n_agents, fp32_agents=2, quantized_agents=3, n_levels=2)
        J_interp = (1 - alpha) * J + alpha * J_binary
        
        result = run_conservation_experiment(J_interp)
        if result['valid']:
            cv_values.append(result['cv'])
    
    if cv_values:
        mean_cv = np.mean(cv_values)
        results[f'interp_{alpha:.2f}'] = {
            'alpha': float(alpha),
            'mean_cv': float(mean_cv),
            'n_valid': len(cv_values)
        }
        conserved = "✓" if mean_cv < 0.05 else ("~" if mean_cv < 0.15 else "✗")
        print(f"  α={alpha:.2f} (ternary={1-alpha:.0%}, binary={alpha:.0%}) | CV={mean_cv:.4f} | {conserved}")

# Detect sharpness of transition
print(f"\n{'='*80}")
print("TRANSITION ANALYSIS")
print(f"{'='*80}")
level_data = [(int(k), v) for k, v in results.items() if k.isdigit() and 'mean_cv' in v]
level_data.sort(key=lambda x: x[0])
if len(level_data) >= 3:
    cvs = [d[1]['mean_cv'] for d in level_data]
    max_cv_jump = max(cvs[i+1] - cvs[i] for i in range(len(cvs)-1))
    cv_range = max(cvs) - min(cvs)
    sharpness = max_cv_jump / cv_range if cv_range > 0 else 0
    print(f"  Max CV jump between consecutive levels: {max_cv_jump:.4f}")
    print(f"  CV range: {cv_range:.4f}")
    print(f"  Sharpness ratio: {sharpness:.4f}")
    print(f"  → {'SHARP transition' if sharpness > 0.3 else 'GRADUAL transition'}")

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-002/exp5_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to exp5_results.json")
