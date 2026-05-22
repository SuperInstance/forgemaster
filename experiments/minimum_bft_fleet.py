#!/usr/bin/env python3
"""Experiment 24: Minimum BFT Fleet Size.

Test the N >= 3f+1 bound for our architecture specifically.
- For f=1: test N = 3, 4, 5, 6, 7
- For f=2: test N = 6, 7, 8, 9, 10
- For f=3: test N = 9, 10, 11, 12, 13

Uses reputation+trimmed mean filter from Exp 16/11.
Each config: 10 trials, 500 ticks, measure convergence rate and max drift.

Hypothesis: N=3f+1 is tight (N=4 works for f=1, N=7 for f=2, N=10 for f=3).
If N=3f+1 converges but N=3f fails → bound is tight.
If N=3f+1 fails → our filters need more agents than theoretical minimum.
"""
import json
import random
import os
from statistics import median

random.seed(42)


class MetronomeAgent:
    def __init__(self, idx, epsilon=0.01, delta=0.0625):
        self.idx = idx
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.byzantine = False
        self.neighbors = []
        self.drift_rate = epsilon * (idx - 4) / 20.0
        # Reputation tracking
        self.peer_dev_sq = {}
        self.peer_count = {}

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        if self.byzantine:
            return float(random.randint(0, 1000))
        return self.local_clock

    def _peer_variance(self, peer_idx):
        if peer_idx not in self.peer_count or self.peer_count[peer_idx] < 2:
            return 0.0
        n = self.peer_count[peer_idx]
        return self.peer_dev_sq[peer_idx] / n

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
            new_sq = deviation * deviation
            self.peer_dev_sq[pidx] = (1 - alpha) * self.peer_dev_sq[pidx] + alpha * new_sq
            self.peer_count[pidx] = min(self.peer_count[pidx] + 1, 100)

        peer_vars = {pidx: self._peer_variance(pidx) for pidx, _ in peer_reports}
        all_vars = sorted(peer_vars.values())
        fleet_median_var = all_vars[len(all_vars) // 2]

        reputation_weights = {}
        for pidx, var in peer_vars.items():
            if fleet_median_var > 0.001 and var > 2.0 * fleet_median_var:
                ratio = var / max(fleet_median_var, 0.001)
                reputation_weights[pidx] = max(0.01, 1.0 / (1.0 + ratio))
            else:
                reputation_weights[pidx] = 1.0

        values = [r for _, r in peer_reports]
        report_range = max(values) - min(values)
        if report_range > 4.0 * self.delta:
            trusted = [(pidx, r) for pidx, r in peer_reports
                       if abs(r - self.local_clock) < 2.0 * self.delta]
            if not trusted:
                return
            peer_reports = trusted
            values = [r for _, r in peer_reports]

        report_values = sorted(peer_reports, key=lambda x: x[1])
        n = len(report_values)
        if n >= 6:
            trim = n // 4
            trimmed = report_values[trim:-trim]
        else:
            trimmed = report_values

        if not trimmed:
            trimmed = report_values

        total_weight = 0.0
        weighted_sum = 0.0
        for pidx, reported in trimmed:
            w = reputation_weights.get(pidx, 1.0)
            weighted_sum += reported * w
            total_weight += w

        if total_weight > 0:
            consensus = weighted_sum / total_weight
        else:
            consensus = median([r for _, r in trimmed])

        error = consensus - self.local_clock
        if abs(error) > self.delta:
            self.local_clock += error * 0.5


def build_laman_topology(n):
    """Build a Laman-rigid (2n-3 edge) graph via Henneberg construction."""
    if n < 2:
        return []
    edges = []
    # Start with triangle for n>=3, edge for n==2
    if n >= 3:
        for i in range(3):
            for j in range(i + 1, 3):
                edges.append((i, j))
        start = 3
    else:
        edges.append((0, 1))
        start = 2
    for k in range(start, n):
        targets = random.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges


def run_single_trial(N, f, trial_seed):
    """Run one trial with N agents, f byzantine. Returns trial result."""
    random.seed(trial_seed)

    agents = [MetronomeAgent(i) for i in range(N)]
    edges = build_laman_topology(N)

    for i, j in edges:
        agents[i].neighbors.append((agents[j], 1.0))
        agents[j].neighbors.append((agents[i], 1.0))

    for i in range(f):
        agents[i].byzantine = True

    max_drifts = []
    convergence_tick = None
    consecutive_stable = 0

    for tick in range(1, 501):
        for a in agents:
            a.tick(tick)

        for a in agents:
            if not a.byzantine:
                a.correct()

        honest = [a for a in agents if not a.byzantine]
        honest_clocks = [a.local_clock for a in honest]
        ideal_clock = float(tick)
        drifts = [abs(c - ideal_clock) for c in honest_clocks]
        max_drift = max(drifts)
        max_drifts.append(max_drift)

        if max_drift < 0.0625:
            consecutive_stable += 1
            if consecutive_stable >= 10 and convergence_tick is None:
                convergence_tick = tick - 9
        else:
            consecutive_stable = 0

    return {
        "converged": convergence_tick is not None,
        "convergence_tick": convergence_tick if convergence_tick else 501,
        "peak_drift": round(max(max_drifts), 6),
        "final_drift": round(max_drifts[-1], 6),
        "mean_drift": round(sum(max_drifts) / len(max_drifts), 6)
    }


def run_experiment():
    configs = [
        {"f": 1, "N_values": [3, 4, 5, 6, 7]},
        {"f": 2, "N_values": [6, 7, 8, 9, 10]},
        {"f": 3, "N_values": [9, 10, 11, 12, 13]},
    ]

    num_trials = 10
    results = {}

    for config in configs:
        f = config["f"]
        for N in config["N_values"]:
            key = f"f{f}_N{N}"
            satisfies_bound = N >= 3 * f + 1

            trials = []
            for t in range(num_trials):
                trial = run_single_trial(N, f, 42 + t * 1000 + f * 100 + N)
                trials.append(trial)

            convergence_rate = sum(1 for tr in trials if tr["converged"]) / num_trials
            avg_peak_drift = sum(tr["peak_drift"] for tr in trials) / num_trials
            avg_final_drift = sum(tr["final_drift"] for tr in trials) / num_trials
            avg_mean_drift = sum(tr["mean_drift"] for tr in trials) / num_trials
            converged_ticks = [tr["convergence_tick"] for tr in trials if tr["converged"]]
            avg_conv_tick = sum(converged_ticks) / len(converged_ticks) if converged_ticks else 501

            results[key] = {
                "f": f,
                "N": N,
                "honest": N - f,
                "satisfies_bound": satisfies_bound,
                "theoretical_min": 3 * f + 1,
                "convergence_rate": convergence_rate,
                "avg_convergence_tick": round(avg_conv_tick, 2),
                "avg_peak_drift": round(avg_peak_drift, 6),
                "avg_final_drift": round(avg_final_drift, 6),
                "avg_mean_drift": round(avg_mean_drift, 6),
                "trials": trials
            }

    # Save results
    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/experiment24_min_bft.json", "w") as fp:
        json.dump(results, fp, indent=2)

    # Print report
    print("=" * 120)
    print("EXPERIMENT 24: Minimum BFT Fleet Size — N >= 3f+1 Bound Test")
    print("Filter: Reputation-Weighted Trimmed Mean | Topology: Laman-rigid (Henneberg)")
    print("=" * 120)
    print(f"{'f':>3} | {'N':>3} | {'Honest':>6} | {'N>=3f+1':>7} | {'Conv Rate':>9} | "
          f"{'Avg Conv':>8} | {'Peak Drift':>10} | {'Final Drift':>11} | {'Mean Drift':>10}")
    print("-" * 120)

    for config in configs:
        f = config["f"]
        print(f"--- f={f} (theoretical min N={3*f+1}) ---")
        for N in config["N_values"]:
            key = f"f{f}_N{N}"
            r = results[key]
            bound_str = "YES" if r["satisfies_bound"] else "NO"
            print(f"{r['f']:>3} | {r['N']:>3} | {r['honest']:>6} | {bound_str:>7} | "
                  f"{r['convergence_rate']:>9.1%} | "
                  f"{r['avg_convergence_tick']:>8.1f} | "
                  f"{r['avg_peak_drift']:>10.4f} | "
                  f"{r['avg_final_drift']:>11.4f} | "
                  f"{r['avg_mean_drift']:>10.4f}")
        print()

    print("=" * 120)

    # Analysis
    print("\nANALYSIS: Tightness of N=3f+1 Bound")
    print("-" * 60)
    for f_val in [1, 2, 3]:
        below = f"f{f_val}_N{3*f_val}"
        at = f"f{f_val}_N{3*f_val+1}"
        above = f"f{f_val}_N{3*f_val+2}"

        cr_below = results[below]["convergence_rate"] if below in results else None
        cr_at = results[at]["convergence_rate"] if at in results else None
        cr_above = results[above]["convergence_rate"] if above in results else None

        print(f"\nf={f_val}: N=3f={3*f_val}, N=3f+1={3*f_val+1}, N=3f+2={3*f_val+2}")
        if cr_below is not None:
            print(f"  N=3f   ({3*f_val:>2} agents): convergence = {cr_below:.1%}")
        if cr_at is not None:
            print(f"  N=3f+1 ({3*f_val+1:>2} agents): convergence = {cr_at:.1%}")
        if cr_above is not None:
            print(f"  N=3f+2 ({3*f_val+2:>2} agents): convergence = {cr_above:.1%}")

        if cr_at is not None and cr_below is not None:
            if cr_at > cr_below:
                print(f"  → Bound IS tight: N=3f+1 converges ({cr_at:.0%}) while N=3f does not ({cr_below:.0%})")
            elif cr_at > 0 and cr_below > 0:
                print(f"  → Bound NOT tight: even N=3f converges ({cr_below:.0%})")
            else:
                print(f"  → N=3f+1 fails to converge ({cr_at:.0%}): filters need more agents than theoretical minimum")

    print(f"\nResults saved to experiments/results/experiment24_min_bft.json")


if __name__ == "__main__":
    run_experiment()
