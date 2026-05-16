#!/usr/bin/env python3
"""Study 57 v2: Conservation as Training Predictor — Redesigned

HYPOTHESIS: γ+H captures fleet structural capacity that MODULATES the 
expected performance of an incoming agent BEYOND what the fleet average predicts.

Design: Compare three predictors:
1. Fleet average accuracy (baseline)
2. Conservation-modulated fleet average = fleet_avg * f(γ+H deviation)
3. Conservation-only (no fleet accuracy info)
4. Random

The conservation-modulated prediction uses the deviation of γ+H from the 
conservation law prediction as a correction factor on the fleet average.
A surplus (γ+H above predicted) means the fleet has excess structural 
capacity → incoming agent should perform BETTER than the fleet average.
A deficit means the fleet is strained → incoming agent should perform WORSE.
"""

import json
import math
import os
import numpy as np
from scipy import stats as sp_stats

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
N_BOOTSTRAPS = 200
EMBED_DIM = 64
SEED = 42

rng = np.random.RandomState(SEED)

# ── Step 1: Generate 20 agents ──
# Each agent has an embedding + a "task performance" vector
# Performance is NOT just cosine similarity — it's a function of both
# embedding position and structural context
agent_embeddings = rng.randn(N_AGENTS, EMBED_DIM)
agent_embeddings /= np.linalg.norm(agent_embeddings, axis=1, keepdims=True)

# True accuracies: function of position in knowledge space
# Some agents are in high-density regions (high accuracy), others in sparse regions
task_vector = rng.randn(EMBED_DIM)
task_vector /= np.linalg.norm(task_vector)

# Base accuracy from alignment with task
base_accuracies = np.array([
    0.3 + 0.5 * np.dot(agent_embeddings[i], task_vector) 
    for i in range(N_AGENTS)
])

# Structural bonus: agents in clusters get a boost (knowledge integration)
from sklearn.metrics.pairwise import cosine_similarity
sim_matrix = cosine_similarity(agent_embeddings)
for i in range(N_AGENTS):
    neighbors = np.argsort(sim_matrix[i])[-4:]  # top 4 neighbors
    neighbor_avg_sim = np.mean([sim_matrix[i, j] for j in neighbors if j != i])
    base_accuracies[i] += 0.1 * neighbor_avg_sim  # structural bonus

true_accuracies = np.clip(base_accuracies, 0.15, 0.95)

# ── Step 2: Prediction functions ──

def predict_conservation_modulated(fleet_avg, gh_measured, V):
    """Use γ+H deviation as a correction factor on fleet average.
    
    Logic: 
    - If γ+H > predicted → fleet has structural surplus → incoming agent gets a BOOST
    - If γ+H < predicted → fleet is strained → incoming agent gets a PENALTY
    - The correction magnitude is proportional to the z-score of the deviation
    """
    gh_pred = predicted_gh(V)
    sigma = interpolate_sigma(V)
    z = (gh_measured - gh_pred) / (sigma + 1e-10)
    
    # Correction: +5% per standard deviation above predicted, capped at ±20%
    correction = 0.05 * np.tanh(z * 0.3)
    return float(np.clip(fleet_avg * (1 + correction), 0.1, 0.95))


def predict_conservation_standalone(gh_measured, V):
    """Predict accuracy from γ+H alone (no fleet average info).
    
    Uses the measured γ+H as a proxy for fleet structural capacity.
    Higher γ+H → more coherent, diverse fleet → better integration potential.
    """
    # Map γ+H to accuracy: use percentile of measured gh vs predicted
    gh_pred = predicted_gh(V)
    ratio = gh_measured / (gh_pred + 1e-10)
    # Ratio > 1 means surplus, < 1 means deficit
    return float(np.clip(0.3 + 0.3 * np.tanh((ratio - 1) * 3), 0.1, 0.95))


def predict_fleet_avg(fleet_accs):
    return float(np.mean(fleet_accs))


def predict_random(rng):
    return float(rng.uniform(0.2, 0.9))


# ── Step 3: Run experiment ──

results_by_size = {}
all_bootstrap_data = {}

for V in FLEET_SIZES:
    boot_data = {
        'cons_mod_errors': [],
        'cons_standalone_errors': [],
        'baseline_errors': [],
        'random_errors': [],
        'gh_values': [],
        'actual_accs': [],
        'fleet_avgs': [],
        'cons_mod_preds': [],
        'cons_standalone_preds': [],
    }
    
    for b in range(N_BOOTSTRAPS):
        # Sample fleet
        available = list(range(N_AGENTS))
        fleet_indices = sorted(rng.choice(available, size=min(V, N_AGENTS), replace=False))
        remaining = [i for i in range(N_AGENTS) if i not in fleet_indices]
        
        if not remaining:
            incoming_idx = fleet_indices[0]  # edge case
            fleet_indices = fleet_indices[1:]
        else:
            incoming_idx = rng.choice(remaining)
        
        # Build coupling matrix
        emb_sub = agent_embeddings[fleet_indices]
        C = np.maximum(0, cosine_similarity(emb_sub))
        np.fill_diagonal(C, 0)
        gh = compute_gh(C)
        
        actual_acc = true_accuracies[incoming_idx]
        fleet_accs = true_accuracies[fleet_indices]
        fleet_avg = np.mean(fleet_accs)
        
        # Predictions
        pred_cons_mod = predict_conservation_modulated(fleet_avg, gh, V)
        pred_cons_standalone = predict_conservation_standalone(gh, V)
        pred_base = predict_fleet_avg(fleet_accs)
        pred_rand = predict_random(rng)
        
        # Store
        boot_data['cons_mod_errors'].append(abs(pred_cons_mod - actual_acc))
        boot_data['cons_standalone_errors'].append(abs(pred_cons_standalone - actual_acc))
        boot_data['baseline_errors'].append(abs(pred_base - actual_acc))
        boot_data['random_errors'].append(abs(pred_rand - actual_acc))
        boot_data['gh_values'].append(gh)
        boot_data['actual_accs'].append(actual_acc)
        boot_data['fleet_avgs'].append(fleet_avg)
        boot_data['cons_mod_preds'].append(pred_cons_mod)
        boot_data['cons_standalone_preds'].append(pred_cons_standalone)
    
    all_bootstrap_data[str(V)] = boot_data
    
    # Compute statistics
    cons_mod_err = np.array(boot_data['cons_mod_errors'])
    cons_standalone_err = np.array(boot_data['cons_standalone_errors'])
    baseline_err = np.array(boot_data['baseline_errors'])
    random_err = np.array(boot_data['random_errors'])
    
    # Paired t-test: conservation-modulated vs baseline
    diff_mod = baseline_err - cons_mod_err  # positive = conservation wins
    if np.std(diff_mod) > 1e-10:
        t_mod, p_mod = sp_stats.ttest_rel(baseline_err, cons_mod_err)
        # We want one-tailed: conservation is better (lower error)
        p_mod_one = p_mod / 2 if np.mean(diff_mod) > 0 else 1 - p_mod / 2
    else:
        t_mod, p_mod_one = 0.0, 1.0
    
    # Paired t-test: conservation standalone vs baseline
    diff_stand = baseline_err - cons_standalone_err
    if np.std(diff_stand) > 1e-10:
        t_stand, p_stand = sp_stats.ttest_rel(baseline_err, cons_standalone_err)
        p_stand_one = p_stand / 2 if np.mean(diff_stand) > 0 else 1 - p_stand / 2
    else:
        t_stand, p_stand_one = 0.0, 1.0
    
    results_by_size[str(V)] = {
        'fleet_size': V,
        'n_samples': N_BOOTSTRAPS,
        'mean_gh': float(np.mean(boot_data['gh_values'])),
        'std_gh': float(np.std(boot_data['gh_values'])),
        'predicted_gh': float(predicted_gh(V)),
        'mean_actual_accuracy': float(np.mean(boot_data['actual_accs'])),
        'mean_fleet_avg_accuracy': float(np.mean(boot_data['fleet_avgs'])),
        'conservation_modulated': {
            'mae': float(np.mean(cons_mod_err)),
            'std': float(np.std(cons_mod_err)),
            'median': float(np.median(cons_mod_err)),
        },
        'conservation_standalone': {
            'mae': float(np.mean(cons_standalone_err)),
            'std': float(np.std(cons_standalone_err)),
            'median': float(np.median(cons_standalone_err)),
        },
        'baseline_fleet_avg': {
            'mae': float(np.mean(baseline_err)),
            'std': float(np.std(baseline_err)),
            'median': float(np.median(baseline_err)),
        },
        'random': {
            'mae': float(np.mean(random_err)),
            'std': float(np.std(random_err)),
            'median': float(np.median(random_err)),
        },
        'vs_baseline': {
            'modulated_t': round(float(t_mod), 4),
            'modulated_p_one_tailed': round(float(p_mod_one), 6),
            'modulated_significantly_better': bool(np.mean(diff_mod) > 0 and p_mod_one < 0.05),
            'standalone_t': round(float(t_stand), 4),
            'standalone_p_one_tailed': round(float(p_stand_one), 6),
            'standalone_significantly_better': bool(np.mean(diff_stand) > 0 and p_stand_one < 0.05),
            'modulated_wins': int(np.sum(diff_mod > 0)),
            'standalone_wins': int(np.sum(diff_stand > 0)),
        },
    }

# ── Correlation analysis: does γ+H correlate with incoming agent accuracy? ──
correlation_analysis = {}
for V in FLEET_SIZES:
    bd = all_bootstrap_data[str(V)]
    gh_arr = np.array(bd['gh_values'])
    acc_arr = np.array(bd['actual_accs'])
    fleet_avg_arr = np.array(bd['fleet_avgs'])
    
    # Correlation: γ+H vs incoming agent accuracy
    r_gh_acc, p_gh_acc = sp_stats.pearsonr(gh_arr, acc_arr)
    
    # Correlation: fleet avg vs incoming agent accuracy
    r_favg_acc, p_favg_acc = sp_stats.pearsonr(fleet_avg_arr, acc_arr)
    
    # Correlation: γ+H deviation vs (actual - fleet_avg) residual
    gh_pred = predicted_gh(V)
    gh_dev = gh_arr - gh_pred
    acc_residual = acc_arr - fleet_avg_arr
    r_dev_resid, p_dev_resid = sp_stats.pearsonr(gh_dev, acc_residual)
    
    # Multiple regression: fleet_avg + γ+H deviation → accuracy
    from numpy.linalg import lstsq
    X = np.column_stack([fleet_avg_arr, gh_dev, np.ones(len(fleet_avg_arr))])
    coeffs, residuals, _, _ = lstsq(X, acc_arr, rcond=None)
    predicted_multi = X @ coeffs
    mae_multi = float(np.mean(np.abs(predicted_multi - acc_arr)))
    
    correlation_analysis[str(V)] = {
        'pearson_gh_vs_accuracy': {'r': round(float(r_gh_acc), 4), 'p': round(float(p_gh_acc), 6)},
        'pearson_fleet_avg_vs_accuracy': {'r': round(float(r_favg_acc), 4), 'p': round(float(p_favg_acc), 6)},
        'pearson_gh_deviation_vs_residual': {'r': round(float(r_dev_resid), 4), 'p': round(float(p_dev_resid), 6)},
        'multiple_regression': {
            'coefficients': {
                'fleet_avg': round(float(coeffs[0]), 4),
                'gh_deviation': round(float(coeffs[1]), 4),
                'intercept': round(float(coeffs[2]), 4),
            },
            'mae': round(mae_multi, 4),
        },
    }

# ── Package final results ──
final_results = {
    'study': 'Study 57: Conservation as Training Predictor',
    'version': '2.0 — redesigned with conservation modulation and correlation analysis',
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
    'correlation_analysis': correlation_analysis,
    'summary': {},
}

# Summary
cons_mod_maes = [results_by_size[str(V)]['conservation_modulated']['mae'] for V in FLEET_SIZES]
baseline_maes = [results_by_size[str(V)]['baseline_fleet_avg']['mae'] for V in FLEET_SIZES]
cons_stand_maes = [results_by_size[str(V)]['conservation_standalone']['mae'] for V in FLEET_SIZES]
random_maes = [results_by_size[str(V)]['random']['mae'] for V in FLEET_SIZES]

final_results['summary'] = {
    'overall_mae': {
        'conservation_modulated': round(float(np.mean(cons_mod_maes)), 4),
        'conservation_standalone': round(float(np.mean(cons_stand_maes)), 4),
        'baseline_fleet_avg': round(float(np.mean(baseline_maes)), 4),
        'random': round(float(np.mean(random_maes)), 4),
    },
    'modulated_beats_baseline_count': sum(1 for c, b in zip(cons_mod_maes, baseline_maes) if c < b),
    'modulated_significantly_better_count': sum(
        1 for V in FLEET_SIZES 
        if results_by_size[str(V)]['vs_baseline']['modulated_significantly_better']
    ),
    'correlation_gh_deviation_predicts_residual': {
        str(V): {
            'r': correlation_analysis[str(V)]['pearson_gh_deviation_vs_residual']['r'],
            'p': correlation_analysis[str(V)]['pearson_gh_deviation_vs_residual']['p'],
        }
        for V in FLEET_SIZES
    },
    'multiple_regression_mae': {
        str(V): correlation_analysis[str(V)]['multiple_regression']['mae']
        for V in FLEET_SIZES
    },
}

# Save JSON
out_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(out_dir, 'study57_results.json')
with open(json_path, 'w') as f:
    json.dump(final_results, f, indent=2)
print(f"Results saved to {json_path}")

# ── Print results ──
print("\n" + "="*90)
print("STUDY 57: Conservation as Training Predictor (v2)")
print("="*90)
print(f"\nAgents: {N_AGENTS} | Bootstraps: {N_BOOTSTRAPS} | Conservation: γ+H = 1.283 - 0.159 ln(V)")
print()

# Main comparison table
print(f"{'V':>3} | {'γ+H':>7} | {'γ+H pred':>8} | {'Cons Mod':>8} | {'Cons Only':>8} | {'Fleet Avg':>8} | {'Random':>8} | {'Mod>Base?':>9} | {'p(mod)':>8}")
print("-" * 95)

for V in FLEET_SIZES:
    r = results_by_size[str(V)]
    vs = r['vs_baseline']
    sig = "✓ p<.05" if vs['modulated_significantly_better'] else f"p={vs['modulated_p_one_tailed']:.3f}"
    better = "YES" if r['conservation_modulated']['mae'] < r['baseline_fleet_avg']['mae'] else "no"
    print(f"{V:>3} | {r['mean_gh']:>7.3f} | {r['predicted_gh']:>8.3f} | "
          f"{r['conservation_modulated']['mae']:>8.4f} | {r['conservation_standalone']['mae']:>8.4f} | "
          f"{r['baseline_fleet_avg']['mae']:>8.4f} | {r['random']['mae']:>8.4f} | "
          f"{better:>9} | {sig:>8}")

print()
print("─" * 95)
print("Correlation Analysis: Does γ+H deviation predict accuracy residuals?")
print()
print(f"{'V':>3} | {'r(γ+H dev → residual)':>22} | {'p-value':>10} | {'r(fleet_avg → acc)':>19} | {'Multi-reg MAE':>14}")
print("-" * 80)

for V in FLEET_SIZES:
    ca = correlation_analysis[str(V)]
    r_dev = ca['pearson_gh_deviation_vs_residual']['r']
    p_dev = ca['pearson_gh_deviation_vs_residual']['p']
    r_favg = ca['pearson_fleet_avg_vs_accuracy']['r']
    mr_mae = ca['multiple_regression']['mae']
    sig_marker = " *" if p_dev < 0.05 else ""
    print(f"{V:>3} | {r_dev:>22.4f}{sig_marker} | {p_dev:>10.4f} | {r_favg:>19.4f} | {mr_mae:>14.4f}")

print()
s = final_results['summary']
print(f"Overall MAE — Cons Modulated: {s['overall_mae']['conservation_modulated']:.4f} | "
      f"Cons Standalone: {s['overall_mae']['conservation_standalone']:.4f} | "
      f"Fleet Avg: {s['overall_mae']['baseline_fleet_avg']:.4f} | "
      f"Random: {s['overall_mae']['random']:.4f}")

print(f"\nConservation-modulated beats baseline in {s['modulated_beats_baseline_count']}/{len(FLEET_SIZES)} fleet sizes")
print(f"Statistically significant in {s['modulated_significantly_better_count']}/{len(FLEET_SIZES)} fleet sizes")

# Final verdict
if s['overall_mae']['conservation_modulated'] < s['overall_mae']['baseline_fleet_avg']:
    print("\n✓ HYPOTHESIS SUPPORTED: Conservation-modulated prediction beats fleet average")
elif s['overall_mae']['conservation_standalone'] < s['overall_mae']['random']:
    print("\n△ MIXED: Conservation standalone beats random but doesn't beat fleet average")
else:
    print("\n✗ HYPOTHESIS NOT SUPPORTED: Fleet average is the best predictor")

# Check correlation significance
n_sig_corr = sum(1 for V in FLEET_SIZES 
                 if correlation_analysis[str(V)]['pearson_gh_deviation_vs_residual']['p'] < 0.05)
print(f"\nγ+H deviation significantly predicts accuracy residual in {n_sig_corr}/{len(FLEET_SIZES)} fleet sizes")
