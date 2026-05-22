#!/usr/bin/env python3
"""Experiment 37: Correction Gain Sweep — find the optimal correction gain α.

HYPOTHESIS: Optimal gain is 0.5 (critically damped). Below = slow convergence. Above = oscillation.
MATHEMATICAL PREDICTION: α* = 2/(λ₂+λₙ) from spectral theory — test if this matches.

PROTOCOL:
- N=10 agents, Laman topology (Henneberg type-I), latency=5 ticks
- Correction gain (α): 0.1 through 1.0 (step 0.1)
- For each gain: 10 trials, 1000 ticks
- Measure: convergence tick, steady-state drift, overshoot (max drift spike), jitter

Save to experiments/results/experiment37_gain_sweep.json
"""

import json
import math
import os
import random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)

# === Configuration ===
N_AGENTS = 10
LATENCY = 5
TICKS = 1000
TRIALS = 10
DELTA = 1.0  # convergence threshold (max pairwise drift)
CONVERGENCE_WINDOW = 50  # ticks of sustained convergence to confirm

GAINS = [round(0.1 * i, 1) for i in range(1, 11)]  # 0.1 to 1.0


def henneberg_type1(n, seed=42):
    """Build minimal Laman graph via Henneberg type-I construction."""
    rng = random.Random(seed)
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]  # K3
    for v in range(3, n):
        targets = rng.sample(range(v), min(2, v))
        while len(targets) < 2:
            targets.append(rng.randint(0, v - 1))
        edges.append((v, targets[0]))
        edges.append((v, targets[1]))
    return edges


def build_adjacency(edges, n):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def compute_laplacian_eigenvalues(edges, n):
    """Compute eigenvalues of the graph Laplacian."""
    L = np.zeros((n, n))
    for u, v in edges:
        L[u, v] -= 1
        L[v, u] -= 1
        L[u, u] += 1
        L[v, v] += 1
    eigenvalues = np.sort(np.linalg.eigvalsh(L))
    return eigenvalues


def spectral_optimal_gain(edges, n):
    """Compute α* = 2/(λ₂+λₙ) from spectral theory."""
    eigs = compute_laplacian_eigenvalues(edges, n)
    lambda2 = eigs[1]  # Fiedler value (algebraic connectivity)
    lambda_n = eigs[-1]
    if lambda2 + lambda_n == 0:
        return None
    return 2.0 / (lambda2 + lambda_n)


class Agent:
    def __init__(self, idx, drift_rate=0.01, initial_offset=0.0):
        self.idx = idx
        self.clock = float(idx) * 10.0 + initial_offset  # start spread out
        self.drift_rate = drift_rate * ((idx - 4.5) / 4.5)  # spread drift rates
        self.neighbors = []

    def tick(self):
        self.clock += 1.0 + self.drift_rate


def run_trial(gain, edges, adj, trial_seed):
    """Run a single trial with given correction gain."""
    rng = random.Random(trial_seed)

    agents = [Agent(i, initial_offset=rng.uniform(-5, 5)) for i in range(N_AGENTS)]
    for i, a in enumerate(agents):
        a.neighbors = adj[i]

    # Latency buffer: each agent stores reports from neighbors with delay
    # report_queue[agent_idx] = list of (report_value, tick_received)
    report_buffer = {i: [] for i in range(N_AGENTS)}  # pending corrections
    # History: agent -> neighbor -> deque of reports
    report_history = {i: {} for i in range(N_AGENTS)}

    max_drift_history = []
    convergence_tick = None
    converged_count = 0
    overshoot = 0.0

    for tick in range(TICKS):
        # Tick all clocks
        for a in agents:
            a.tick()

        # Exchange and buffer reports (with latency)
        for a in agents:
            for nb_idx in a.neighbors:
                report = agents[nb_idx].clock
                if nb_idx not in report_history[a.idx]:
                    report_history[a.idx][nb_idx] = []
                report_history[a.idx][nb_idx].append((tick + LATENCY, report))

        # Apply corrections from buffered reports
        for a in agents:
            corrections = []
            for nb_idx in a.neighbors:
                if nb_idx in report_history[a.idx]:
                    # Get all reports that have arrived by now
                    arrived = [(t, val) for t, val in report_history[a.idx][nb_idx] if t <= tick]
                    if arrived:
                        latest_report = arrived[-1][1]
                        corrections.append(latest_report)

            if corrections:
                neighbor_avg = sum(corrections) / len(corrections)
                diff = neighbor_avg - a.clock
                a.clock += gain * diff

            # Clean up old buffered reports
            for nb_idx in list(report_history[a.idx].keys()):
                report_history[a.idx][nb_idx] = [
                    (t, val) for t, val in report_history[a.idx][nb_idx]
                    if t > tick - LATENCY * 2
                ]

        # Measure pairwise drift
        clocks = [a.clock for a in agents]
        max_drift = max(clocks) - min(clocks)
        max_drift_history.append(max_drift)

        if max_drift > overshoot:
            overshoot = max_drift

        # Check convergence
        if max_drift < DELTA:
            converged_count += 1
            if converged_count >= CONVERGENCE_WINDOW and convergence_tick is None:
                convergence_tick = tick - CONVERGENCE_WINDOW + 1
        else:
            converged_count = 0

    # Compute steady-state drift (last 100 ticks)
    steady_state_drift = np.mean(max_drift_history[-100:]) if len(max_drift_history) >= 100 else np.mean(max_drift_history)

    # Compute jitter (std of drift in steady state)
    jitter = float(np.std(max_drift_history[-100:])) if len(max_drift_history) >= 100 else float(np.std(max_drift_history))

    return {
        "convergence_tick": convergence_tick,
        "steady_state_drift": float(steady_state_drift),
        "overshoot": float(overshoot),
        "jitter": float(jitter),
        "max_drift_final": float(max_drift_history[-1]),
    }


def main():
    print("=" * 70)
    print("EXPERIMENT 37: CORRECTION GAIN SWEEP")
    print("=" * 70)

    # Build Laman topology
    edges = henneberg_type1(N_AGENTS, seed=42)
    adj = build_adjacency(edges, N_AGENTS)

    print(f"\nTopology: Laman (Henneberg type-I), N={N_AGENTS}, |E|={len(edges)}")
    print(f"Latency: {LATENCY} ticks")
    print(f"Ticks per trial: {TICKS}, Trials per gain: {TRIALS}")
    print(f"Convergence threshold (δ): {DELTA}")
    print(f"Convergence window: {CONVERGENCE_WINDOW} ticks")

    # Compute spectral optimal gain
    alpha_star = spectral_optimal_gain(edges, N_AGENTS)
    eigs = compute_laplacian_eigenvalues(edges, N_AGENTS)
    print(f"\nSpectral analysis:")
    print(f"  λ₂ (Fiedler value): {eigs[1]:.4f}")
    print(f"  λₙ (max eigenvalue): {eigs[-1]:.4f}")
    print(f"  α* = 2/(λ₂+λₙ) = {alpha_star:.4f}")

    # Sweep gains
    results = {}
    print(f"\n{'α':>5} {'Conv Tick':>10} {'SS Drift':>10} {'Overshoot':>10} {'Jitter':>10} {'Conv/10':>8}")
    print("-" * 60)

    for gain in GAINS:
        trials = []
        for trial in range(TRIALS):
            trial_result = run_trial(gain, edges, adj, trial_seed=42 + trial)
            trials.append(trial_result)

        # Aggregate
        conv_ticks = [t["convergence_tick"] for t in trials if t["convergence_tick"] is not None]
        avg_conv = np.mean(conv_ticks) if conv_ticks else None
        converged_count = len(conv_ticks)

        avg_ss_drift = np.mean([t["steady_state_drift"] for t in trials])
        avg_overshoot = np.mean([t["overshoot"] for t in trials])
        avg_jitter = np.mean([t["jitter"] for t in trials])

        results[str(gain)] = {
            "gain": gain,
            "avg_convergence_tick": float(avg_conv) if avg_conv is not None else None,
            "convergence_rate": converged_count / TRIALS,
            "avg_steady_state_drift": float(avg_ss_drift),
            "avg_overshoot": float(avg_overshoot),
            "avg_jitter": float(avg_jitter),
            "trials": trials,
        }

        conv_str = f"{avg_conv:.1f}" if avg_conv is not None else "NO CONV"
        print(f"{gain:>5.1f} {conv_str:>10} {avg_ss_drift:>10.4f} {avg_overshoot:>10.2f} {avg_jitter:>10.4f} {converged_count:>5}/10")

    # Find optimal
    best_gain = None
    best_score = float('inf')
    for gain_str, data in results.items():
        if data["avg_convergence_tick"] is not None:
            score = data["avg_convergence_tick"] + data["avg_jitter"] * 100
            if score < best_score:
                best_score = score
                best_gain = float(gain_str)

    print(f"\n{'=' * 70}")
    print(f"RESULTS SUMMARY")
    print(f"{'=' * 70}")
    print(f"Spectral prediction α* = {alpha_star:.4f}")
    print(f"Empirical best gain   = {best_gain}")
    print(f"Match: {'YES ✓' if best_gain and abs(best_gain - alpha_star) < 0.15 else 'NO ✗'}")

    if best_gain:
        bd = results[str(best_gain)]
        print(f"\nBest gain details:")
        print(f"  Convergence tick: {bd['avg_convergence_tick']:.1f}")
        print(f"  Convergence rate: {bd['convergence_rate']:.0%}")
        print(f"  Steady-state drift: {bd['avg_steady_state_drift']:.4f}")
        print(f"  Overshoot: {bd['avg_overshoot']:.2f}")
        print(f"  Jitter: {bd['avg_jitter']:.4f}")

    # Hypothesis check
    print(f"\nHYPOTHESIS CHECK: Optimal gain ≈ 0.5 (critically damped)")
    if best_gain:
        if best_gain <= 0.4:
            print(f"  REJECTED — optimal is {best_gain}, lower than predicted (underdamped regime)")
        elif best_gain >= 0.6:
            print(f"  REJECTED — optimal is {best_gain}, higher than predicted")
        else:
            print(f"  CONFIRMED — optimal is {best_gain}, near 0.5")

    # Save results
    output = {
        "experiment": "experiment37_gain_sweep",
        "description": "Correction gain sweep to find optimal α for Laman topology consensus",
        "config": {
            "n_agents": N_AGENTS,
            "topology": "laman_henneberg_type1",
            "edges": edges,
            "latency": LATENCY,
            "ticks": TICKS,
            "trials": TRIALS,
            "delta": DELTA,
            "convergence_window": CONVERGENCE_WINDOW,
            "gains_tested": GAINS,
        },
        "spectral_analysis": {
            "lambda_2": float(eigs[1]),
            "lambda_n": float(eigs[-1]),
            "alpha_star_predicted": float(alpha_star),
        },
        "results": results,
        "conclusion": {
            "spectral_prediction": float(alpha_star),
            "empirical_best": best_gain,
            "spectral_match": best_gain is not None and abs(best_gain - alpha_star) < 0.15,
            "hypothesis_0_5_confirmed": best_gain is not None and 0.4 <= best_gain <= 0.6,
        },
    }

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    out_path = out_dir / "experiment37_gain_sweep.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, cls=NumpyEncoder)

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
