"""
Experiment 26: Embedding Dimension for Agent Calibration
HYPOTHESIS: Agent calibration lives in a low-dimensional manifold (d < 10) regardless of drift rate σ.

WHAT THIS CONSTRAINS: The memoir compression theorem from Exp 15. If calibration state lives in d << full_dim
dimensions, we only need d tiles per checkpoint — not full state vectors.

PROTOCOL:
1. Run single agent for 10,000 ticks, record full state history
2. Compute SVD of state matrix (tick × feature)
3. Plot singular value spectrum: how many dimensions capture 90%, 95%, 99%, 99.9% of variance?
4. Test: embed calibration in d = 3, 5, 10, 20 dimensions — can we still predict drift?
5. Test: does embedding dimension depend on drift rate σ?
6. Save to experiments/results/experiment26_embedding.json
"""

import json
import math
import os
import random
import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Simulated agent calibration dynamics ──────────────────────────────────

class CalibrationAgent:
    """Simulates an agent whose state evolves with drift, corrections, and noise."""
    def __init__(self, dim=8, drift_scale=0.01, noise_scale=0.02, lr=0.05):
        self.dim = dim
        self.state = np.random.randn(dim) * 0.1
        self.target = np.random.randn(dim)
        self.lr = lr
        self.noise_scale = noise_scale
        self.drift_scale = drift_scale
        self.history = []

    def tick(self):
        drift = np.random.randn(self.dim) * self.drift_scale
        self.state += drift

        dist = np.linalg.norm(self.state - self.target)
        obs = dist + np.random.randn() * self.noise_scale

        correction = -self.lr * (self.state - self.target) + np.random.randn(self.dim) * self.noise_scale
        self.state += correction

        post_drift = np.linalg.norm(self.state - self.target)

        self.history.append({
            'state': self.state.copy(),
            'observation': float(obs),
            'correction': float(np.linalg.norm(correction)),
            'drift': float(post_drift),
        })
        return self.history[-1]


# ── Core experiment functions ─────────────────────────────────────────────

def compute_variance_thresholds(singular_values):
    """Find how many dimensions needed for each variance threshold."""
    total_var = np.sum(singular_values ** 2)
    cumvar = np.cumsum(singular_values ** 2) / total_var
    thresholds = {}
    for pct in [0.90, 0.95, 0.99, 0.999]:
        idx = np.searchsorted(cumvar, pct)
        thresholds[f"{int(pct*100)}%"] = int(idx) + 1  # 1-indexed count
    return thresholds, cumvar


def embed_and_predict(state_matrix, drift_values, d_embed):
    """Project to d dimensions, train linear predictor, measure drift prediction error."""
    n = state_matrix.shape[0]
    train_end = int(n * 0.8)

    # SVD on training portion only
    U, s, Vt = np.linalg.svd(state_matrix[:train_end], full_matrices=False)
    # Project full matrix to d dimensions
    projection = Vt[:d_embed].T  # (dim, d)
    embedded = state_matrix @ projection  # (n, d)

    # Simple linear regression: embedded state -> next drift
    X_train = embedded[:train_end - 1]
    y_train = drift_values[1:train_end]

    # Solve via normal equations
    X_with_bias = np.column_stack([X_train, np.ones(len(X_train))])
    try:
        w = np.linalg.lstsq(X_with_bias, y_train, rcond=None)[0]
    except np.linalg.LinAlgError:
        return float('inf'), 0.0

    # Evaluate on test set
    X_test = embedded[train_end - 1:n - 1]
    y_test = drift_values[train_end:n]
    X_test_b = np.column_stack([X_test, np.ones(len(X_test))])
    y_pred = X_test_b @ w

    mae = float(np.mean(np.abs(y_pred - y_test)))
    # Accuracy: fraction of predictions within 20% of true drift
    tolerance = np.maximum(np.abs(y_test) * 0.2, 0.05)  # min tolerance to avoid div-by-zero issues
    accuracy = float(np.mean(np.abs(y_pred - y_test) < tolerance))

    return mae, accuracy


def run_single_experiment(dim=8, drift_scale=0.01, T=10000):
    """Full experiment for one drift rate."""
    agent = CalibrationAgent(dim=dim, drift_scale=drift_scale)
    for _ in range(T):
        agent.tick()

    # Build state matrix (tick × feature)
    states = np.array([h['state'] for h in agent.history])
    drifts = np.array([h['drift'] for h in agent.history])

    # SVD analysis
    U, s, Vt = np.linalg.svd(states, full_matrices=False)
    thresholds, cumvar = compute_variance_thresholds(s)

    # Spectrum (normalized singular values)
    spectrum = (s ** 2) / np.sum(s ** 2)

    # Embedding prediction test
    embed_results = {}
    for d in [3, 5, 10, 20]:
        if d > dim:
            continue
        mae, acc = embed_and_predict(states, drifts, d)
        embed_results[str(d)] = {
            'mae': round(mae, 6),
            'accuracy': round(acc, 4),
        }

    # Full-dim baseline
    mae_full, acc_full = embed_and_predict(states, drifts, dim)
    embed_results[f"full({dim})"] = {
        'mae': round(mae_full, 6),
        'accuracy': round(acc_full, 4),
    }

    return {
        'dim': dim,
        'drift_scale': drift_scale,
        'T': T,
        'singular_values': [round(float(v), 6) for v in s],
        'normalized_spectrum': [round(float(v), 6) for v in spectrum],
        'cumulative_variance': [round(float(v), 6) for v in cumvar],
        'variance_thresholds': thresholds,
        'embedding_prediction': embed_results,
    }


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs('experiments/results', exist_ok=True)

    print("=" * 60)
    print("EXPERIMENT 26: Embedding Dimension for Agent Calibration")
    print("=" * 60)

    # Part 1: Baseline experiment (σ = 0.01)
    print("\n[1/2] Baseline: σ = 0.01, dim = 8, T = 10000")
    baseline = run_single_experiment(dim=8, drift_scale=0.01, T=10000)
    print(f"  Variance thresholds: {baseline['variance_thresholds']}")
    print(f"  Top 3 singular values: {baseline['singular_values'][:3]}")
    print(f"  Embedding results:")
    for d, r in baseline['embedding_prediction'].items():
        print(f"    d={d}: MAE={r['mae']:.4f}, accuracy={r['accuracy']:.4f}")

    # Part 2: Sweep drift rates
    drift_rates = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
    print(f"\n[2/2] Drift rate sweep: {drift_rates}")
    drift_sweep = {}
    for sigma in drift_rates:
        result = run_single_experiment(dim=8, drift_scale=sigma, T=10000)
        drift_sweep[str(sigma)] = {
            'variance_thresholds': result['variance_thresholds'],
            'top_singular_values': result['singular_values'][:4],
            'd5_accuracy': result['embedding_prediction'].get('5', {}).get('accuracy', 'N/A'),
            'd10_accuracy': result['embedding_prediction'].get('10', {}).get('accuracy', 'N/A'),
        }
        print(f"  σ={sigma}: 90% at d={result['variance_thresholds']['90%']}, "
              f"99% at d={result['variance_thresholds']['99%']}, "
              f"d5_acc={result['embedding_prediction'].get('5', {}).get('accuracy', 'N/A')}")

    # Hypothesis check
    baseline_90 = baseline['variance_thresholds']['90%']
    baseline_99 = baseline['variance_thresholds']['99%']
    d5_works = baseline['embedding_prediction'].get('5', {}).get('accuracy', 0) > 0.5

    print("\n" + "=" * 60)
    print("HYPOTHESIS CHECK")
    print("=" * 60)
    print(f"  90% variance captured in d = {baseline_90}")
    print(f"  99% variance captured in d = {baseline_99}")
    print(f"  d=5 prediction accuracy: {baseline['embedding_prediction'].get('5', {}).get('accuracy', 'N/A')}")
    print(f"  Hypothesis (d < 10): {'SUPPORTED' if baseline_99 < 10 else 'NOT SUPPORTED'}")
    print(f"  d=5 viable: {'YES' if d5_works else 'NO'}")

    # Check if dimension depends on σ
    dims_across_sigma = [drift_sweep[s]['variance_thresholds']['99%'] for s in drift_sweep]
    dim_range = max(dims_across_sigma) - min(dims_across_sigma)
    print(f"  Dimension range across σ: {min(dims_across_sigma)}-{max(dims_across_sigma)} (range={dim_range})")
    print(f"  Independent of σ: {'YES' if dim_range <= 2 else 'NO'}")

    # Save results
    output = {
        'experiment': 'embedding_dimension',
        'hypothesis': 'Agent calibration lives in a low-dimensional manifold (d < 10) regardless of drift rate σ',
        'baseline': baseline,
        'drift_sweep': drift_sweep,
        'conclusion': {
            'hypothesis_supported': baseline_99 < 10,
            'dimension_for_90pct': baseline_90,
            'dimension_for_99pct': baseline_99,
            'd5_prediction_accuracy': baseline['embedding_prediction'].get('5', {}).get('accuracy'),
            'dimension_independent_of_sigma': dim_range <= 2,
            'implication_for_memoir': f"Checkpoints need only {baseline_99} tiles instead of full {baseline['dim']}-dim state",
        },
    }

    outpath = 'experiments/results/experiment26_embedding.json'
    with open(outpath, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {outpath}")
