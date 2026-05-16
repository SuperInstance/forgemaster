#!/usr/bin/env python3
"""Study 57: Conservation as Training Predictor

Does γ+H at fleet size V predict how well a new agent will perform?

Simulation-based — no API calls.
"""

import json
import math
import os
import numpy as np
from collections import defaultdict

# ── Conservation law parameters ──
C_INTERCEPT = 1.283
C_LOG_COEFF = -0.159
SIGMA_TABLE = {5: 0.070, 10: 0.065, 20: 0.058, 30: 0.050,
               50: 0.048, 100: 0.042, 200: 0.038}


def interpolate_sigma(V):
    vs = sorted(SIGMA_TABLE.keys())
    if V <= vs[0]: return SIGMA_TABLE[vs[0]]
    if V >= vs[-1]: return SIGMA_TABLE[vs[-1]]
    for lo, hi in zip(vs, vs[1:]):
        if lo < V <= hi:
            frac = (V - lo) / (hi - lo)
            return SIGMA_TABLE[lo] + frac * (SIGMA_TABLE[hi] - SIGMA_TABLE[lo])
    return 0.05


def predicted_gh(V):
    return C_INTERCEPT + C_LOG_COEFF * math.log(max(V, 3))


def coupling_entropy(C):
    eigs = np.linalg.eigvalsh(C)[::-1]
    p = np.abs(eigs) / (np.sum(np.abs(eigs)) + 1e-15)
    p = p[p > 1e-10]
    return float(-np.sum(p * np.log(p)) / np.log(len(eigs)))


def algebraic_normalized(C):
    if C.shape[0] < 2:
        return 0.0
    L = np.diag(C.sum(axis=1)) - C
    eigs = np.linalg.eigvalsh(L)
    return float((eigs[1] - eigs[0]) / (eigs[-1] - eigs[0] + 1e-15))


def compute_gh(C):
    return algebraic_normalized(C) + coupling_entropy(C)


# ── Simulation Parameters ──
N_AGENTS = 20
FLEET_SIZES = [3, 5, 7, 9, 11, 15, 20]
N_BOOTSTRAPS = 100
EMBED_DIM = 64
SEED = 42

rng = np.random.RandomState(SEED)

# ── Step 1: Generate 20 agents with random embeddings ──
# Each agent has an embedding vector — simulates a "knowledge space"
agent_embeddings = rng.randn(N_AGENTS, EMBED_DIM)
agent_embeddings /= np.linalg.norm(agent_embeddings, axis=1, keepdims=True)

# Agent "true accuracy" — derived from embedding norm alignment to a random task vector
# This simulates that each agent has inherent capability
task_vector = rng.randn(EMBED_DIM)
task_vector /= np.linalg.norm(task_vector)
true_accuracies = np.array([max(0.1, min(1.0, 0.5 + 0.4 * np.dot(agent_embeddings[i], task_vector)))
                            for i in range(N_AGENTS)])

# ── Step 2 & 3: For each fleet size, predict incoming agent accuracy ──

def build_coupling_matrix(indices, embeddings):
    """Build coupling matrix from agent embeddings (cosine similarity)."""
    n = len(indices)
    C = np.zeros((n, n))
    for i, ii in enumerate(indices):
        for j, jj in enumerate(indices):
            if i != j:
                C[i, j] = max(0, np.dot(embeddings[ii], embeddings[jj]))
    return C


def predict_conservation(gh, V):
    """Predict incoming agent accuracy from conservation law state.

    Higher γ+H → more coherent fleet → better integration → higher accuracy.
    We use: predicted_accuracy = sigmoid(α * (gh - gh_predicted) + β)
    where gh_predicted is the expected γ+H for size V.
    
    The DEVIATION from conservation captures structural surplus/deficit.
    A fleet with surplus (above predicted) has room for knowledge integration.
    """
    gh_pred = predicted_gh(V)
    deviation = gh - gh_pred  # positive = surplus
    # Map deviation to accuracy prediction
    # Normalize by σ for the fleet size
    sigma = interpolate_sigma(V)
    z_score = deviation / (sigma + 1e-10)
    # Predict accuracy: baseline 0.5 + bonus from structural surplus
    predicted = 0.5 + 0.15 * np.tanh(z_score * 0.5)
    return max(0.1, min(0.95, predicted))


def predict_baseline_avg(fleet_accuracies):
    """Baseline: predict incoming agent = average fleet accuracy."""
    return np.mean(fleet_accuracies)


def predict_random(rng):
    """Random prediction."""
    return rng.uniform(0.2, 0.9)


# ── Run experiment ──
results_by_size = {}

for V in FLEET_SIZES:
    errors = {
        'conservation': [],
        'baseline_avg': [],
        'random': [],
    }
    predictions = {
        'conservation': [],
        'baseline_avg': [],
        'random': [],
        'actual': [],
    }
    gh_values = []
    fleet_avg_accs = []

    for b in range(N_BOOTSTRAPS):
        # Sample V fleet members (with replacement from 20 agents, leaving some out)
        fleet_indices = sorted(rng.choice(N_AGENTS, size=V, replace=False))
        
        # The incoming agent is one NOT in the fleet (or a random one if all are used)
        remaining = [i for i in range(N_AGENTS) if i not in fleet_indices]
        if not remaining:
            # All 20 agents are the fleet; incoming is a random one
            incoming_idx = rng.randint(N_AGENTS)
        else:
            incoming_idx = rng.choice(remaining)
        
        # Build coupling matrix for the fleet
        C = build_coupling_matrix(fleet_indices, agent_embeddings)
        gh = compute_gh(C)
        gh_values.append(gh)
        
        # Actual accuracy of the incoming agent
        actual_acc = true_accuracies[incoming_idx]
        predictions['actual'].append(actual_acc)
        
        # Fleet member accuracies
        fleet_accs = true_accuracies[fleet_indices]
        fleet_avg = np.mean(fleet_accs)
        fleet_avg_accs.append(fleet_avg)
        
        # Method 1: Conservation prediction
        pred_cons = predict_conservation(gh, V)
        predictions['conservation'].append(pred_cons)
        errors['conservation'].append(abs(pred_cons - actual_acc))
        
        # Method 2: Baseline (fleet average)
        pred_base = predict_baseline_avg(fleet_accs)
        predictions['baseline_avg'].append(pred_base)
        errors['baseline_avg'].append(abs(pred_base - actual_acc))
        
        # Method 3: Random
        pred_rand = predict_random(rng)
        predictions['random'].append(pred_rand)
        errors['random'].append(abs(pred_rand - actual_acc))

    # Compute statistics
    results_by_size[str(V)] = {
        'n_samples': N_BOOTSTRAPS,
        'fleet_size': V,
        'mean_gh': float(np.mean(gh_values)),
        'predicted_gh': float(predicted_gh(V)),
        'gh_std': float(np.std(gh_values)),
        'mean_actual_accuracy': float(np.mean(predictions['actual'])),
        'mean_fleet_avg_accuracy': float(np.mean(fleet_avg_accs)),
        'conservation': {
            'mean_error': float(np.mean(errors['conservation'])),
            'std_error': float(np.std(errors['conservation'])),
            'median_error': float(np.median(errors['conservation'])),
            'mean_prediction': float(np.mean(predictions['conservation'])),
        },
        'baseline_avg': {
            'mean_error': float(np.mean(errors['baseline_avg'])),
            'std_error': float(np.std(errors['baseline_avg'])),
            'median_error': float(np.median(errors['baseline_avg'])),
            'mean_prediction': float(np.mean(predictions['baseline_avg'])),
        },
        'random': {
            'mean_error': float(np.mean(errors['random'])),
            'std_error': float(np.std(errors['random'])),
            'median_error': float(np.median(errors['random'])),
            'mean_prediction': float(np.mean(predictions['random'])),
        },
    }

# ── Overall summary ──
overall = {
    'conservation_mean_error': float(np.mean([r['conservation']['mean_error'] for r in results_by_size.values()])),
    'baseline_mean_error': float(np.mean([r['baseline_avg']['mean_error'] for r in results_by_size.values()])),
    'random_mean_error': float(np.mean([r['random']['mean_error'] for r in results_by_size.values()])),
}

# Pairwise comparison: in how many bootstraps does conservation beat baseline?
pairwise_wins = {str(V): 0 for V in FLEET_SIZES}
pairwise_data = {}
for V in FLEET_SIZES:
    wins = 0
    # We need to redo this comparison per-bootstrap
    # Use stored errors
    cons_errors = []
    base_errors = []
    
    rng2 = np.random.RandomState(SEED)
    for b in range(N_BOOTSTRAPS):
        fleet_indices = sorted(rng2.choice(N_AGENTS, size=V, replace=False))
        remaining = [i for i in range(N_AGENTS) if i not in fleet_indices]
        incoming_idx = rng2.choice(remaining) if remaining else rng2.randint(N_AGENTS)
        
        C = build_coupling_matrix(fleet_indices, agent_embeddings)
        gh = compute_gh(C)
        actual_acc = true_accuracies[incoming_idx]
        fleet_accs = true_accuracies[fleet_indices]
        
        pred_cons = predict_conservation(gh, V)
        pred_base = predict_baseline_avg(fleet_accs)
        
        if abs(pred_cons - actual_acc) < abs(pred_base - actual_acc):
            wins += 1
    
    pairwise_wins[str(V)] = wins
    pairwise_data[str(V)] = {
        'conservation_wins': wins,
        'baseline_wins': N_BOOTSTRAPS - wins,
        'win_rate': f"{wins/N_BOOTSTRAPS:.1%}",
    }

# ── Statistical significance (paired t-test via numpy) ──
significance = {}
for V in FLEET_SIZES:
    rng3 = np.random.RandomState(SEED)
    cons_errs = []
    base_errs = []
    for b in range(N_BOOTSTRAPS):
        fleet_indices = sorted(rng3.choice(N_AGENTS, size=V, replace=False))
        remaining = [i for i in range(N_AGENTS) if i not in fleet_indices]
        incoming_idx = rng3.choice(remaining) if remaining else rng3.randint(N_AGENTS)
        
        C = build_coupling_matrix(fleet_indices, agent_embeddings)
        gh = compute_gh(C)
        actual_acc = true_accuracies[incoming_idx]
        fleet_accs = true_accuracies[fleet_indices]
        
        cons_errs.append(abs(predict_conservation(gh, V) - actual_acc))
        base_errs.append(abs(predict_baseline_avg(fleet_accs) - actual_acc))
    
    cons_errs = np.array(cons_errs)
    base_errs = np.array(base_errs)
    diff = base_errs - cons_errs  # positive = conservation wins
    t_stat = float(np.mean(diff) / (np.std(diff, ddof=1) / np.sqrt(len(diff))))
    
    # Approximate p-value using normal approximation for large n
    from scipy.stats import t as t_dist
    try:
        p_value = float(2 * (1 - t_dist.cdf(abs(t_stat), df=len(diff)-1)))
    except ImportError:
        # Manual approximation
        p_value = float(min(1.0, 2 * np.exp(-0.5 * t_stat**2) / (abs(t_stat) + 1)))
    
    significance[str(V)] = {
        't_statistic': round(t_stat, 4),
        'p_value': round(p_value, 6),
        'mean_diff_base_minus_cons': round(float(np.mean(diff)), 6),
        'conservation_significantly_better': bool(p_value < 0.05 and np.mean(diff) > 0),
    }

# ── Package final results ──
final_results = {
    'study': 'Study 57: Conservation as Training Predictor',
    'hypothesis': 'The conservation law at fleet size V predicts incoming agent accuracy with lower error than the fleet average',
    'parameters': {
        'n_agents': N_AGENTS,
        'fleet_sizes': FLEET_SIZES,
        'n_bootstraps': N_BOOTSTRAPS,
        'embed_dim': EMBED_DIM,
        'seed': SEED,
    },
    'conservation_law': {
        'formula': 'γ + H = 1.283 - 0.159 ln(V)',
        'r_squared': 0.9602,
    },
    'results_by_fleet_size': results_by_size,
    'pairwise_wins': pairwise_data,
    'significance_tests': significance,
    'overall': overall,
}

# Save JSON
out_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(out_dir, 'study57_results.json')
with open(json_path, 'w') as f:
    json.dump(final_results, f, indent=2)
print(f"Results saved to {json_path}")

# ── Print summary ──
print("\n" + "="*70)
print("STUDY 57: Conservation as Training Predictor")
print("="*70)
print(f"\nConservation law: γ + H = 1.283 - 0.159 ln(V)")
print(f"Agents: {N_AGENTS}, Bootstraps: {N_BOOTSTRAPS}")
print()

print(f"{'V':>4} | {'γ+H (meas)':>10} | {'γ+H (pred)':>10} | {'Cons Err':>9} | {'Base Err':>9} | {'Rand Err':>9} | {'Cons Wins':>9} | {'p-value':>8} | {'Sig':>3}")
print("-" * 100)

for V in FLEET_SIZES:
    r = results_by_size[str(V)]
    pw = pairwise_data[str(V)]
    sig = significance[str(V)]
    marker = "✓" if sig['conservation_significantly_better'] else "✗"
    print(f"{V:>4} | {r['mean_gh']:>10.4f} | {r['predicted_gh']:>10.4f} | "
          f"{r['conservation']['mean_error']:>9.4f} | {r['baseline_avg']['mean_error']:>9.4f} | "
          f"{r['random']['mean_error']:>9.4f} | {pw['win_rate']:>9} | {sig['p_value']:>8.4f} | {marker:>3}")

print()
print(f"Overall MAE — Conservation: {overall['conservation_mean_error']:.4f} | "
      f"Baseline: {overall['baseline_mean_error']:.4f} | "
      f"Random: {overall['random_mean_error']:.4f}")

# Summary statistics
n_sig = sum(1 for s in significance.values() if s['conservation_significantly_better'])
n_cons_better = sum(1 for V in FLEET_SIZES if results_by_size[str(V)]['conservation']['mean_error'] < results_by_size[str(V)]['baseline_avg']['mean_error'])
print(f"\nConservation beats baseline in {n_cons_better}/{len(FLEET_SIZES)} fleet sizes")
print(f"Statistically significant (p < 0.05) in {n_sig}/{len(FLEET_SIZES)} fleet sizes")

if overall['conservation_mean_error'] < overall['baseline_mean_error']:
    print("\n✓ HYPOTHESIS SUPPORTED: Conservation law predicts incoming agent accuracy with lower error than fleet average")
else:
    print("\n✗ HYPOTHESIS NOT SUPPORTED: Fleet average baseline outperforms conservation prediction")
