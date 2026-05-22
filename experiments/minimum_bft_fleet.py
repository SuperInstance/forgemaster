#!/usr/bin/env python3
"""Experiment 24: Minimum BFT Fleet Size.

Test whether N = 3f+1 is the tight bound for convergence under Byzantine faults.
Uses reputation+trimmed mean filter from earlier experiments.

Configurations:
- f=1: N = 3, 4, 5, 7
- f=2: N = 5, 6, 7, 10
- f=3: N = 8, 9, 10, 13

10 trials each, 500 ticks. Fully connected graph.
"""
import json
import random
import os
import math
from statistics import median, mean

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
RESULTS_PATH = os.path.join(RESULTS_DIR, "experiment24_min_bft.json")

random.seed(42)


class MetronomeAgent:
    def __init__(self, idx, epsilon=0.01, delta=0.0625):
        self.idx = idx
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.byzantine = False
        self.neighbors = []
        self.converged_tick = None
        # Each agent has a slightly different drift rate
        self.drift_rate = epsilon * (idx % 7 - 3) / 20.0
        # Reputation tracking
        self.peer_dev_sq = {}
        self.peer_count = {}

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        if self.byzantine:
            # Byzantine: random noise, trying to disrupt consensus
            return self.local_clock + float(random.randint(-500, 500))
        return self.local_clock

    def _peer_variance(self, peer_idx):
        if peer_idx not in self.peer_count or self.peer_count[peer_idx] < 2:
            return 0.0
        return self.peer_dev_sq[peer_idx] / self.peer_count[peer_idx]

    def correct(self):
        if not self.neighbors:
            return
        peer_reports = []
        for neighbor, _ in self.neighbors:
            reported = neighbor.report_clock()
            peer_reports.append((neighbor.idx, reported))
            deviation = reported - self.local_clock
            pidx = neighbor.idx
            if pidx not in self.peer_dev_sq:
                self.peer_dev_sq[pidx] = 0.0
                self.peer_count[pidx] = 0
            alpha = 0.3
            self.peer_dev_sq[pidx] = (1 - alpha) * self.peer_dev_sq[pidx] + alpha * deviation * deviation
            self.peer_count[pidx] = min(self.peer_count[pidx] + 1, 100)

        peer_vars = {pidx: self._peer_variance(pidx) for pidx, _ in peer_reports}
        all_vars = sorted(peer_vars.values())
        fleet_median_var = all_vars[len(all_vars) // 2] if all_vars else 1.0

        # Reputation weights
        weights = {}
        for pidx, reported in peer_reports:
            pvar = peer_vars[pidx]
            if pvar > 2.0 * max(fleet_median_var, 0.001):
                weights[pidx] = 0.01
            else:
                weights[pidx] = 1.0 / (1.0 + pvar)

        # Trimmed mean on weighted reports
        weighted = [(reported, weights[pidx]) for pidx, reported in peer_reports if weights[pidx] > 0.01]
        if len(weighted) < 1:
            weighted = [(reported, 1.0) for _, reported in peer_reports]

        weighted.sort(key=lambda x: x[0])
        trim = max(1, len(weighted) // 4)
        if len(weighted) > 2 * trim:
            weighted = weighted[trim:-trim]

        total_w = sum(w for _, w in weighted)
        if total_w < 1e-9:
            return
        avg = sum(r * w for r, w in weighted) / total_w

        correction = self.delta * (avg - self.local_clock)
        self.local_clock += correction


def run_trial(N, f, ticks=500, convergence_threshold=0.1):
    """Run a single trial. Returns (converged, convergence_tick, max_drift)."""
    agents = [MetronomeAgent(i) for i in range(N)]

    # Assign f Byzantine agents
    byz_indices = random.sample(range(N), f)
    for i in byz_indices:
        agents[i].byzantine = True

    # Fully connected graph
    for a in agents:
        a.neighbors = [(b, 1.0) for b in agents if b is not a]

    converged = False
    convergence_tick = None
    max_drift = 0.0

    for t in range(1, ticks + 1):
        for a in agents:
            a.tick(t)
        for a in agents:
            a.correct()

        # Check convergence among honest agents only
        honest = [a for a in agents if not a.byzantine]
        if len(honest) < 2:
            continue
        clocks = [a.local_clock for a in honest]
        drift = max(clocks) - min(clocks)
        max_drift = max(max_drift, drift)

        if drift < convergence_threshold:
            if not converged:
                converged = True
                convergence_tick = t
        else:
            converged = False
            convergence_tick = None

    return converged, convergence_tick, max_drift


def main():
    configs = [
        (1, [3, 4, 5, 7]),
        (2, [5, 6, 7, 10]),
        (3, [8, 9, 10, 13]),
    ]

    results = {"experiment": 24, "hypothesis": "N=3f+1 is the tight BFT bound", "configurations": []}

    for f, N_values in configs:
        f_config = {"f": f, "tight_bound": 3 * f + 1, "tests": []}
        for N in N_values:
            trials_data = []
            convergence_ticks = []
            convergence_count = 0
            max_drifts = []

            for trial in range(10):
                converged, conv_tick, max_drift = run_trial(N, f, ticks=500)
                trials_data.append({
                    "trial": trial,
                    "converged": converged,
                    "convergence_tick": conv_tick,
                    "max_drift": round(max_drift, 6),
                })
                if converged:
                    convergence_count += 1
                    convergence_ticks.append(conv_tick)
                max_drifts.append(max_drift)

            test_result = {
                "N": N,
                "f": f,
                "is_tight_bound": N == 3 * f + 1,
                "convergence_rate": convergence_count / 10,
                "avg_convergence_tick": round(mean(convergence_ticks), 1) if convergence_ticks else None,
                "max_drift_across_trials": round(max(max_drifts), 6),
                "avg_max_drift": round(mean(max_drifts), 6),
                "trials": trials_data,
            }
            f_config["tests"].append(test_result)
            status = "✓" if convergence_count > 5 else "✗"
            print(f"  f={f} N={N} (tight={3*f+1}): {convergence_count}/10 converged {status}")

        results["configurations"].append(f_config)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RESULTS_PATH, "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")

    # Summary
    print("\n=== Summary ===")
    for f_config in results["configurations"]:
        f = f_config["f"]
        print(f"\nf={f} (tight bound: N={3*f+1}):")
        for t in f_config["tests"]:
            bound_mark = " ← tight" if t["is_tight_bound"] else ""
            above = " (above tight)" if t["N"] > 3 * f + 1 else ""
            below = " (BELOW tight!)" if t["N"] < 3 * f + 1 else ""
            print(f"  N={t['N']}: {t['convergence_rate']*100:.0f}% converged, "
                  f"avg tick={t['avg_convergence_tick']}, max drift={t['max_drift_across_trials']}"
                  f"{bound_mark}{above}{below}")


if __name__ == "__main__":
    main()
