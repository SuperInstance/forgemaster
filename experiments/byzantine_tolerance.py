#!/usr/bin/env python3
"""Experiment 11: Byzantine Fault Tolerance in a Laman-rigid fleet.

Filter: Reputation-weighted trimmed mean.
- Each honest agent tracks historical variance of peer reports.
- Peers with variance > 2× fleet median variance are flagged suspicious.
- Suspicious peer corrections are weighted down to ~0.
- Trimmed mean (discard top/bottom 25%) only applied when >= 6 neighbors.
- For sparse graphs, reputation alone does the filtering.
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
        self.byztantine = False
        self.neighbors = []
        self.converged_tick = None
        self.drift_rate = epsilon * (idx - 4) / 20.0
        # Reputation tracking
        self.peer_dev_sq = {}   # peer idx -> running sum of squared deviations
        self.peer_count = {}    # peer idx -> number of samples

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        if self.byztantine:
            return float(random.randint(0, 1000))
        return self.local_clock

    def _peer_variance(self, peer_idx):
        """Running variance for a peer."""
        if peer_idx not in self.peer_count or self.peer_count[peer_idx] < 2:
            return 0.0
        n = self.peer_count[peer_idx]
        return self.peer_dev_sq[peer_idx] / n

    def correct(self):
        """Apply corrections using reputation-weighted trimmed mean."""
        if not self.neighbors:
            return

        # Collect neighbor reports
        peer_reports = []
        for neighbor, _ in self.neighbors:
            reported = neighbor.report_clock()
            peer_reports.append((neighbor.idx, reported))

            # Update running variance: deviation from our clock
            deviation = reported - self.local_clock
            pidx = neighbor.idx
            if pidx not in self.peer_dev_sq:
                self.peer_dev_sq[pidx] = 0.0
                self.peer_count[pidx] = 0
            # Exponential moving: weight recent samples more
            alpha = 0.3
            old_var = self._peer_variance(pidx)
            new_sq = deviation * deviation
            self.peer_dev_sq[pidx] = (1 - alpha) * self.peer_dev_sq[pidx] + alpha * new_sq
            self.peer_count[pidx] = min(self.peer_count[pidx] + 1, 100)

        # Compute per-peer variance
        peer_vars = {pidx: self._peer_variance(pidx) for pidx, _ in peer_reports}

        # Fleet median variance
        all_vars = list(peer_vars.values())
        all_vars_sorted = sorted(all_vars)
        fleet_median_var = all_vars_sorted[len(all_vars_sorted) // 2]

        # Reputation weights: peers with variance > 2x median get near-zero weight
        reputation_weights = {}
        for pidx, var in peer_vars.items():
            if fleet_median_var > 0.001 and var > 2.0 * fleet_median_var:
                # Exponential penalty: the more suspicious, the lower the weight
                ratio = var / max(fleet_median_var, 0.001)
                reputation_weights[pidx] = max(0.01, 1.0 / (1.0 + ratio))
            else:
                reputation_weights[pidx] = 1.0

        # Spread guard: if reports disagree too much, skip correction
        values = [r for _, r in peer_reports]
        report_range = max(values) - min(values)
        # Honest neighbors should agree within a small band around our clock
        # Allow spread up to 4 * delta; anything wider means Byzantine is active
        if report_range > 4.0 * self.delta:
            # Only use reports within delta of our own clock
            trusted = [(pidx, r) for pidx, r in peer_reports
                       if abs(r - self.local_clock) < 2.0 * self.delta]
            if not trusted:
                return  # no trustworthy reports, skip
            peer_reports = trusted
            values = [r for _, r in peer_reports]

        # Trimmed mean only if enough neighbors (>= 6)
        report_values = sorted(peer_reports, key=lambda x: x[1])
        n = len(report_values)
        if n >= 6:
            trim = n // 4
            trimmed = report_values[trim:-trim]
        else:
            trimmed = report_values

        if not trimmed:
            trimmed = report_values

        # Weighted consensus
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
    edges = []
    for i in range(3):
        for j in range(i + 1, 3):
            edges.append((i, j))
    for k in range(3, n):
        targets = random.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges


def run_experiment():
    N = 10
    expected_edges = 2 * N - 3

    results = []

    for f in [0, 1, 2, 3]:
        assert N >= 3 * f + 1, f"Cannot tolerate f={f} with N={N}"

        agents = [MetronomeAgent(i) for i in range(N)]
        edges = build_laman_topology(N)

        for i, j in edges:
            agents[i].neighbors.append((agents[j], 1.0))
            agents[j].neighbors.append((agents[i], 1.0))

        for i in range(f):
            agents[i].byztantine = True

        max_drifts = []
        convergence_tick = None
        consecutive_stable = 0

        for tick in range(1, 501):
            for a in agents:
                a.tick(tick)

            for a in agents:
                if not a.byztantine:
                    a.correct()

            honest = [a for a in agents if not a.byztantine]
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

        result = {
            "byzantine_count": f,
            "honest_count": N - f,
            "laman_edges": len(edges),
            "expected_edges": expected_edges,
            "condition_met": N >= 3 * f + 1,
            "max_drift_final": round(max_drifts[-1], 6),
            "max_drift_peak": round(max(max_drifts), 6),
            "max_drift_mean": round(sum(max_drifts) / len(max_drifts), 6),
            "convergence_tick": convergence_tick
        }
        results.append(result)

    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/experiment11_byzantine.json", "w") as fp:
        json.dump(results, fp, indent=2)

    print("=" * 90)
    print("EXPERIMENT 11: Byzantine Fault Tolerance in Laman-Rigid Fleet")
    print("Filter: Reputation-Weighted Trimmed Mean")
    print("=" * 90)
    print(f"{'f':>3} | {'Honest':>6} | {'Edges':>5} | {'N>=3f+1':>7} | "
          f"{'Peak Drift':>10} | {'Final Drift':>11} | {'Mean Drift':>10} | {'Conv Tick':>9}")
    print("-" * 90)
    for r in results:
        conv = str(r["convergence_tick"]) if r["convergence_tick"] else "none"
        print(f"{r['byzantine_count']:>3} | {r['honest_count']:>6} | {r['laman_edges']:>5} | "
              f"{'YES' if r['condition_met'] else 'NO':>7} | "
              f"{r['max_drift_peak']:>10.6f} | {r['max_drift_final']:>11.6f} | "
              f"{r['max_drift_mean']:>10.6f} | {conv:>9}")
    print("=" * 90)
    print(f"\nLaman topology: {results[0]['laman_edges']} edges (2*{N}-3 = {2*N-3})")
    print(f"Agents: {N}, tolerable Byzantine: up to f={(N-1)//3}")
    print("Results saved to experiments/results/experiment11_byzantine.json")


if __name__ == "__main__":
    run_experiment()
