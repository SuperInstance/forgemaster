#!/usr/bin/env python3
"""Experiment 19: Multi-Generation Sunset Dynamics

HYPOTHESIS: Drift grows linearly with generation count (each handoff loses calibration).
NOVEL ALTERNATIVE: If drift stays bounded → inheritance is self-correcting.

PROTOCOL:
- N=10 agents, Laman topology (Henneberg type-I)
- 5 generations of sunset/inheritance:
  - Each gen: run 200 ticks, sunset an agent, inherit to new agent
- Measure: drift at end of each gen, calibration quality (θ vs optimal), convergence speed
- Inheritance: new agent copies neighbors' averaged calibration state as initial estimate

KEY QUESTION: Does drift compound across generations, or does the Laman structure
self-correct during each generation's run?
"""

import json
import math
import os
import random
import statistics
from collections import defaultdict
from pathlib import Path

# --- Configuration ---
N_AGENTS = 10
TICKS_PER_GEN = 200
N_GENERATIONS = 5
DELTA = 5.0         # convergence threshold
TRUE_VALUE = 100.0  # target calibration value
ALPHA = 0.3         # learning rate
TRIALS = 10


def build_laman_graph(n, seed=42):
    """Henneberg type-I construction for a Laman graph (2N-3 edges)."""
    rng = random.Random(seed)
    edges = set()
    # K3 base
    edges.add((0, 1)); edges.add((0, 2)); edges.add((1, 2))
    for v in range(3, n):
        candidates = list(range(v))
        pick = rng.sample(candidates, min(2, len(candidates)))
        for u in pick:
            edges.add((min(u, v), max(u, v)))
    return list(edges)


def adjacency(n, edges):
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


class Agent:
    """Agent with estimate θ and calibration state."""
    def __init__(self, idx, estimate=None, is_byzantine=False):
        self.idx = idx
        self.is_byzantine = is_byzantine
        self.estimate = estimate if estimate is not None else TRUE_VALUE + random.uniform(-20, 20)
        self.history = []          # per-tick estimates
        self.tick_count = 0

    def report(self):
        return self.estimate

    def step(self, neighbor_reports, accepted):
        """Update estimate toward accepted consensus value."""
        self.estimate = self.estimate + ALPHA * (accepted - self.estimate)
        self.history.append(self.estimate)
        self.tick_count += 1


def trimmed_mean(reports, trim_frac=0.25):
    """Discard top/bottom 25%, average rest."""
    vals = sorted(v for _, v in reports)
    n = len(vals)
    if n == 0:
        return TRUE_VALUE
    trim = max(1, int(n * trim_frac))
    trimmed = vals[trim:n - trim] if trim < n - trim else vals
    if not trimmed:
        return vals[n // 2]
    return sum(trimmed) / len(trimmed)


def inherit_agent(old_agent, neighbors, agents_map):
    """Create new agent inheriting calibration state from neighbors.

    The new agent starts with the average estimate of its neighbors,
    simulating knowledge transfer from the community that surrounded
    the sunset agent.
    """
    neighbor_estimates = [agents_map[n].estimate for n in neighbors if n in agents_map]
    if neighbor_estimates:
        inherited_estimate = statistics.mean(neighbor_estimates)
    else:
        # No neighbors left — start from scratch with some noise
        inherited_estimate = TRUE_VALUE + random.uniform(-10, 10)

    return Agent(old_agent.idx, estimate=inherited_estimate)


def run_trial(seed):
    """Run one full trial: 5 generations of sunset/inheritance."""
    rng = random.Random(seed)

    # Build graph
    edges = build_laman_graph(N_AGENTS, seed=seed)
    adj = adjacency(N_AGENTS, edges)

    # Initialize agents
    agents = {}
    for i in range(N_AGENTS):
        init_est = TRUE_VALUE + rng.uniform(-20, 20)
        agents[i] = Agent(i, estimate=init_est)

    generation_results = []

    for gen in range(N_GENERATIONS):
        # --- Run Ticks ---
        converged_tick = None
        for tick in range(TICKS_PER_GEN):
            # Gather reports and update each agent
            new_estimates = {}
            for idx, agent in agents.items():
                neighbors = adj[idx]
                reports = [(n, agents[n].report()) for n in neighbors if n in agents]
                if reports:
                    accepted = trimmed_mean(reports)
                else:
                    accepted = agent.estimate
                new_estimates[idx] = agent.estimate + ALPHA * (accepted - agent.estimate)

            # Apply updates synchronously
            for idx, agent in agents.items():
                agent.estimate = new_estimates[idx]
                agent.history.append(agent.estimate)
                agent.tick_count += 1

            # Check convergence
            drifts = {idx: abs(agent.estimate - TRUE_VALUE) for idx, agent in agents.items()}
            max_drift = max(drifts.values()) if drifts else 0
            if converged_tick is None and max_drift < DELTA:
                converged_tick = tick

        # --- End-of-generation measurements ---
        drifts = {idx: abs(agent.estimate - TRUE_VALUE) for idx, agent in agents.items()}
        max_drift = max(drifts.values()) if drifts else 0
        mean_drift = statistics.mean(drifts.values()) if drifts else 0
        calibration_quality = statistics.mean(
            [abs(agent.estimate - TRUE_VALUE) / TRUE_VALUE for agent in agents.values()]
        )

        gen_result = {
            "generation": gen + 1,
            "converged": converged_tick is not None,
            "convergence_tick": converged_tick if converged_tick is not None else TICKS_PER_GEN + 1,
            "max_drift": max_drift,
            "mean_drift": mean_drift,
            "calibration_quality": calibration_quality,  # lower = better (fractional error)
            "agent_estimates": {str(idx): round(agent.estimate, 4) for idx, agent in agents.items()},
            "sunset_agent": gen,  # agent `gen` gets sunset at end of this generation
        }
        generation_results.append(gen_result)

        # --- Sunset + Inherit ---
        # Sunset agent `gen` — remove and replace with inherited newcomer
        sunset_idx = gen
        if sunset_idx in agents:
            neighbors = adj[sunset_idx]
            agents[sunset_idx] = inherit_agent(agents[sunset_idx], neighbors, agents)

    return generation_results


def main():
    all_trial_results = []
    summary_by_generation = defaultdict(lambda: {
        "max_drifts": [],
        "mean_drifts": [],
        "calibration_qualities": [],
        "convergence_ticks": [],
        "convergence_count": 0,
    })

    for trial in range(TRIALS):
        seed = 2000 + trial * 13
        trial_result = run_trial(seed)
        all_trial_results.append({"trial": trial, "seed": seed, "generations": trial_result})

        for gen_data in trial_result:
            g = gen_data["generation"]
            sbg = summary_by_generation[g]
            sbg["max_drifts"].append(gen_data["max_drift"])
            sbg["mean_drifts"].append(gen_data["mean_drift"])
            sbg["calibration_qualities"].append(gen_data["calibration_quality"])
            sbg["convergence_ticks"].append(gen_data["convergence_tick"])
            if gen_data["converged"]:
                sbg["convergence_count"] += 1

    # --- Aggregate ---
    aggregated = {}
    for g in range(1, N_GENERATIONS + 1):
        sbg = summary_by_generation[g]
        aggregated[f"gen{g}"] = {
            "avg_max_drift": statistics.mean(sbg["max_drifts"]),
            "std_max_drift": statistics.stdev(sbg["max_drifts"]) if len(sbg["max_drifts"]) > 1 else 0,
            "avg_mean_drift": statistics.mean(sbg["mean_drifts"]),
            "avg_calibration_quality": statistics.mean(sbg["calibration_qualities"]),
            "avg_convergence_tick": statistics.mean(
                [t for t in sbg["convergence_ticks"] if t <= TICKS_PER_GEN]
            ) if any(t <= TICKS_PER_GEN for t in sbg["convergence_ticks"]) else TICKS_PER_GEN + 1,
            "convergence_rate": sbg["convergence_count"] / TRIALS,
        }

    # --- Drift growth analysis ---
    drift_sequence = [aggregated[f"gen{g}"]["avg_max_drift"] for g in range(1, N_GENERATIONS + 1)]
    # Linear fit
    xs = list(range(1, N_GENERATIONS + 1))
    n_pts = len(xs)
    sum_x = sum(xs)
    sum_y = sum(drift_sequence)
    sum_xy = sum(x * y for x, y in zip(xs, drift_sequence))
    sum_x2 = sum(x * x for x in xs)
    slope = (n_pts * sum_xy - sum_x * sum_y) / (n_pts * sum_x2 - sum_x * sum_x) if n_pts > 1 else 0
    intercept = (sum_y - slope * sum_x) / n_pts if n_pts > 1 else drift_sequence[0]
    r_squared = 0
    if n_pts > 2:
        mean_y = sum_y / n_pts
        ss_tot = sum((y - mean_y) ** 2 for y in drift_sequence)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, drift_sequence))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # Determine if drift is linear or bounded
    drift_ratio = max(drift_sequence) / min(drift_sequence) if min(drift_sequence) > 0 else float('inf')
    bounded = drift_ratio < 3.0  # if max drift < 3x min drift, it's bounded
    linear_trend = abs(slope) > 0.5 and r_squared > 0.7  # meaningful linear trend

    result = {
        "conclusion": "BOUNDED (inheritance is self-correcting)" if bounded and not linear_trend
                      else "LINEAR GROWTH (each handoff loses calibration)" if linear_trend
                      else "INCONCLUSIVE",
        "hypothesis": "Drift grows linearly with generation count",
        "novel_if_bounded": bounded and not linear_trend,
        "linear_fit": {"slope": slope, "intercept": intercept, "r_squared": r_squared},
        "drift_sequence": drift_sequence,
        "drift_ratio_max_to_min": drift_ratio,
        "aggregated_by_generation": aggregated,
        "trials": all_trial_results,
    }

    # Save
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "experiment19_multigen.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Results saved to {out_path}")

    # --- ASCII Report ---
    print("\n" + "=" * 90)
    print("EXPERIMENT 19: Multi-Generation Sunset Dynamics")
    print(f"N={N_AGENTS}, Laman topology, {N_GENERATIONS} generations, {TICKS_PER_GEN} ticks/gen, {TRIALS} trials")
    print("=" * 90)
    print(f"{'Gen':>4} {'Avg Max Drift':>14} {'Std':>8} {'Avg Mean Drift':>16} {'Cal Quality':>13} {'Conv%':>7} {'Avg Conv Tick':>14}")
    print("-" * 90)
    for g in range(1, N_GENERATIONS + 1):
        d = aggregated[f"gen{g}"]
        print(f"{g:>4} {d['avg_max_drift']:>14.4f} {d['std_max_drift']:>8.4f} "
              f"{d['avg_mean_drift']:>16.4f} {d['avg_calibration_quality']:>13.6f} "
              f"{d['convergence_rate']*100:>6.0f}% {d['avg_convergence_tick']:>14.1f}")

    print("-" * 90)
    print(f"\nDrift sequence:     {[round(d, 4) for d in drift_sequence]}")
    print(f"Linear fit slope:   {slope:.6f}")
    print(f"R²:                 {r_squared:.4f}")
    print(f"Drift ratio (max/min): {drift_ratio:.2f}x")
    print(f"\nCONCLUSION: {result['conclusion']}")
    if result['novel_if_bounded']:
        print("*** NOVEL RESULT: Drift stays bounded across generations — inheritance is self-correcting! ***")
    elif linear_trend:
        print("Drift grows linearly — each handoff loses some calibration, as hypothesized.")
    else:
        print("Results are inconclusive — more generations or different parameters needed.")
    print("=" * 90)


if __name__ == "__main__":
    main()
