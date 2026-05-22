#!/usr/bin/env python3
"""Experiment 11: Byzantine Fault Tolerance in a Laman-rigid fleet."""
import json
import random
import os
from fractions import Fraction
from statistics import median

random.seed(42)

class MetronomeAgent:
    def __init__(self, idx, epsilon=Fraction(1, 100), delta=Fraction(1, 16)):
        self.idx = idx
        self.local_clock = Fraction(0)
        self.epsilon = epsilon  # max drift rate per tick
        self.delta = delta      # deadband threshold
        self.byztantine = False
        self.neighbors = []     # list of (agent, edge_weight)
        self.converged_tick = None
        # Each agent has a fixed drift direction
        self.drift_rate = epsilon * Fraction(idx - 4, 20)  # varies by agent

    def tick(self, tick_num):
        """Advance local clock with natural drift."""
        self.local_clock += Fraction(1, 1) + self.drift_rate

    def report_clock(self):
        """What this agent sends to neighbors."""
        if self.byztantine:
            # Byzantine: report a random clock value
            return Fraction(random.randint(0, 1000), 1)
        return self.local_clock

    def correct(self):
        """Apply corrections from neighbors using median filter."""
        if not self.neighbors:
            return
        # Collect neighbor clock readings
        reports = [neighbor.report_clock() for neighbor, _ in self.neighbors]

        # Median filter: discard outliers beyond 2*MAD from median
        if len(reports) > 2:
            med = median(reports)
            abs_devs = [abs(r - med) for r in reports]
            mad = median(abs_devs)
            threshold = max(2 * mad, self.delta)  # at least delta
            filtered = [r for r in reports if abs(r - med) <= threshold]
            if filtered:
                reports = filtered

        # Compute consensus from filtered reports
        consensus = median(reports)

        # Apply correction: move toward consensus if beyond deadband
        error = consensus - self.local_clock
        if abs(error) > self.delta:
            # Apply dampened correction
            self.local_clock += error * Fraction(1, 2)

def build_laman_topology(n):
    """Build a Laman graph on n agents with 2n-3 edges."""
    edges = []
    # Start with triangle on first 3 nodes
    for i in range(3):
        for j in range(i + 1, 3):
            edges.append((i, j))
    # Add remaining nodes: connect each to 2 existing
    for k in range(3, n):
        targets = random.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges

def run_experiment():
    N = 10
    expected_edges = 2 * N - 3  # 17

    results = []

    for f in [0, 1, 2, 3]:
        # Verify Byzantine condition
        assert N >= 3 * f + 1, f"Cannot tolerate f={f} with N={N}"

        # Build fresh agents and topology
        agents = [MetronomeAgent(i) for i in range(N)]
        edges = build_laman_topology(N)

        # Build neighbor lists
        for i, j in edges:
            agents[i].neighbors.append((agents[j], Fraction(1, 1)))
            agents[j].neighbors.append((agents[i], Fraction(1, 1)))

        # Mark first f agents as Byzantine
        for i in range(f):
            agents[i].byztantine = True

        max_drifts = []
        convergence_tick = None
        consecutive_stable = 0

        for tick in range(1, 501):
            # Step 1: each agent ticks
            for a in agents:
                a.tick(tick)

            # Step 2: exchange and correct
            for a in agents:
                if not a.byztantine:
                    a.correct()

            # Measure drift among honest agents (deviation from ideal tick count)
            honest = [a for a in agents if not a.byztantine]
            honest_clocks = [a.local_clock for a in honest]
            ideal_clock = Fraction(tick, 1)
            drifts = [abs(c - ideal_clock) for c in honest_clocks]
            max_drift = float(max(drifts))
            max_drifts.append(max_drift)

            # Check convergence: max drift < delta
            if max_drift < float(Fraction(1, 16)):
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

    # Save results
    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/experiment11_byzantine.json", "w") as fp:
        json.dump(results, fp, indent=2)

    # Print ASCII table
    print("=" * 90)
    print("EXPERIMENT 11: Byzantine Fault Tolerance in Laman-Rigid Fleet")
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
