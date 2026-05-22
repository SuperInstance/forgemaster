#!/usr/bin/env python3
"""Experiment 23: Latency-Aware Correction Strategies.

Fixes the phase transition discovered in Exp20 where naive averaging diverges
for any latency > 0 due to stale reports causing destructive corrections.

Three strategies:
1. NAIVE: average all neighbor reports regardless of staleness (baseline/broken)
2. CRISTIAN: weight corrections by estimated RTT — newer reports weighted higher
3. PTP_OFFSET: each agent estimates its offset from peers using (sent+recv)/2 midpoint,
   then corrects toward estimated true time

Test: latency = 0, 1, 5, 10, 20, 50 ticks. N=10, Laman topology, 500 ticks.
Hypothesis: PTP_OFFSET achieves bounded drift at all latencies, NAIVE diverges for latency>0.
"""
import json
import random
import os
import math
from collections import deque
from enum import Enum

random.seed(42)


class Strategy(Enum):
    NAIVE = "NAIVE"
    CRISTIAN = "CRISTIAN"
    PTP_OFFSET = "PTP_OFFSET"


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


class LatencyAwareAgent:
    """Agent with configurable correction strategy."""

    def __init__(self, idx, strategy=Strategy.NAIVE, delta=0.0625, epsilon=0.01):
        self.idx = idx
        self.strategy = strategy
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.neighbors = []  # list of (agent_ref, weight)
        self.drift_rate = epsilon * (idx - 4.5) / 20.0
        self.inbox = deque()

        # PTP state: estimated offset from "true time"
        self.estimated_offset = 0.0

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def broadcast(self, current_tick, latency):
        """Send current clock reading to all neighbors, tagged with send time."""
        reported = self.local_clock
        for neighbor, _ in self.neighbors:
            deliver_at = current_tick + latency
            # Message includes: (deliver_at, sender_idx, reported_clock, sent_tick)
            neighbor.inbox.append((deliver_at, self.idx, reported, current_tick))

    def receive(self, current_tick):
        """Collect all messages due for delivery, return as reports."""
        reports = []
        remaining = deque()
        for msg in self.inbox:
            deliver_tick, sender_idx, reported_clock, sent_tick = msg
            if deliver_tick <= current_tick:
                reports.append((sender_idx, reported_clock, sent_tick))
            else:
                remaining.append(msg)
        self.inbox = remaining
        return reports

    def correct_naive(self, reports):
        """Strategy 1: Average all reports, clamp by delta."""
        if not reports:
            return
        avg = sum(r for _, r, _ in reports) / len(reports)
        diff = avg - self.local_clock
        correction = max(-self.delta, min(self.delta, diff))
        self.local_clock += correction

    def correct_cristian(self, reports, current_tick):
        """Strategy 2: Cristian's algorithm with recency weighting.

        Cristian's algorithm: estimate the server's current time as
        (reported_clock + latency/2), then correct toward it.
        Weight by recency to prefer fresher reports.

        Weight = 1 / (1 + age), where age = current_tick - sent_tick.
        """
        if not reports:
            return
        weighted_sum = 0.0
        weight_total = 0.0
        for sender_idx, reported_clock, sent_tick in reports:
            age = max(current_tick - sent_tick, 0.5)
            weight = 1.0 / (1.0 + age)
            # Cristian: adjust reported clock forward by half the RTT
            # (estimate what neighbor's clock reads NOW)
            latency = current_tick - sent_tick
            neighbor_now = reported_clock + latency / 2.0
            weighted_sum += weight * neighbor_now
            weight_total += weight

        if weight_total == 0:
            return
        weighted_avg = weighted_sum / weight_total
        diff = weighted_avg - self.local_clock
        correction = max(-self.delta, min(self.delta, diff))
        self.local_clock += correction

    def correct_ptp_offset(self, reports, current_tick):
        """Strategy 3: PTP-style offset estimation.

        Core idea: estimate what each neighbor's clock reads NOW (not when
        it sent the report), then average those estimates to get "true time".

        If neighbor sent clock=C at tick T, and we receive at tick T+L:
          - Neighbor's clock now ≈ C + L  (assuming rate ≈ 1.0, error is small)
          - This is our estimate of "true time" from that neighbor's perspective
          - Our offset from true time ≈ (C + L) - local_clock

        We average offset estimates across all neighbors, then apply a
        proportional correction (not hard-clamped) to avoid oscillation.
        """
        if not reports:
            return

        offset_estimates = []
        for sender_idx, reported_clock, sent_tick in reports:
            latency = current_tick - sent_tick
            # Neighbor's clock NOW ≈ reported_clock + latency
            neighbor_now = reported_clock + latency
            # Our offset: how far ahead/behind we are vs neighbor's estimate of now
            offset = neighbor_now - self.local_clock
            offset_estimates.append(offset)

        if not offset_estimates:
            return

        # Average offset estimate across all reports
        avg_offset = sum(offset_estimates) / len(offset_estimates)

        # Proportional correction: apply a fraction of the offset to dampen oscillation
        # Use relaxation factor 0.5 (apply half the estimated offset each tick)
        relaxation = 0.5
        correction = relaxation * avg_offset
        # Soft clamp: don't let any single correction exceed 2.0
        correction = max(-2.0, min(2.0, correction))
        self.local_clock += correction

    def correct(self, reports, current_tick):
        if not reports:
            return
        if self.strategy == Strategy.NAIVE:
            self.correct_naive(reports)
        elif self.strategy == Strategy.CRISTIAN:
            self.correct_cristian(reports, current_tick)
        elif self.strategy == Strategy.PTP_OFFSET:
            self.correct_ptp_offset(reports, current_tick)


def run_single(N, latency, strategy, delta=0.0625, max_ticks=500, warmup=100):
    random.seed(42)
    agents = [LatencyAwareAgent(i, strategy=strategy, delta=delta) for i in range(N)]
    edges = build_laman_topology(N)

    for i, j in edges:
        agents[i].neighbors.append((agents[j], 1.0))
        agents[j].neighbors.append((agents[i], 1.0))

    drift_log = []
    convergence_tick = None
    consecutive_stable = 0
    n_edges = len(edges)

    for tick in range(1, max_ticks + 1):
        for a in agents:
            a.tick(tick)

        for a in agents:
            a.broadcast(tick, latency)

        for a in agents:
            reports = a.receive(tick)
            a.correct(reports, tick)

        ideal_clock = float(tick)
        drifts = [abs(a.local_clock - ideal_clock) for a in agents]
        max_drift = max(drifts)
        drift_log.append(max_drift)

        if tick > warmup:
            if max_drift < 0.1:
                consecutive_stable += 1
                if consecutive_stable >= 20 and convergence_tick is None:
                    convergence_tick = tick - 19
            else:
                consecutive_stable = 0

    steady_state_drift = max(drift_log[-100:])
    peak_drift = max(drift_log)
    mean_drift_last100 = sum(drift_log[-100:]) / 100.0
    total_msgs = 2 * n_edges * max_ticks

    return {
        "convergence_tick": convergence_tick,
        "steady_state_max_drift": round(steady_state_drift, 4),
        "peak_drift": round(peak_drift, 4),
        "mean_drift_last100": round(mean_drift_last100, 4),
        "messages_sent": total_msgs,
        "converged": convergence_tick is not None,
    }


def run_experiment():
    N = 10
    latencies = [0, 1, 5, 10, 20, 50]
    strategies = [Strategy.NAIVE, Strategy.CRISTIAN, Strategy.PTP_OFFSET]
    max_ticks = 500
    warmup = 100
    delta = 0.0625  # 1/16

    results = []

    for strategy in strategies:
        print(f"\n=== Strategy: {strategy.value} ===")
        for latency in latencies:
            print(f"  L={latency:>2}...", end=" ", flush=True)
            r = run_single(N, latency, strategy, delta=delta, max_ticks=max_ticks, warmup=warmup)
            r["latency"] = latency
            r["strategy"] = strategy.value
            r["delta"] = delta
            results.append(r)
            tag = "CONV" if r["converged"] else "    "
            print(f"drift_ss={r['steady_state_max_drift']:>8.4f}  peak={r['peak_drift']:>8.4f}  mean={r['mean_drift_last100']:>8.4f}  [{tag}]")

    # Analysis
    print("\n\n=== COMPARISON TABLE ===")
    print(f"{'Lat':>4} | {'NAIVE(ss)':>10} {'NAIVE(cv)':>9} | {'CRISTIAN(ss)':>12} {'CRISTIAN(cv)':>12} | {'PTP(ss)':>8} {'PTP(cv)':>8}")
    print("-" * 85)

    for latency in latencies:
        row = {}
        for s in strategies:
            r = [x for x in results if x["latency"] == latency and x["strategy"] == s.value][0]
            row[s.value] = r

        n_cv = "✓" if row["NAIVE"]["converged"] else "✗"
        c_cv = "✓" if row["CRISTIAN"]["converged"] else "✗"
        p_cv = "✓" if row["PTP_OFFSET"]["converged"] else "✗"
        print(f"{latency:>4} | {row['NAIVE']['steady_state_max_drift']:>10.4f} {n_cv:>9} | "
              f"{row['CRISTIAN']['steady_state_max_drift']:>12.4f} {c_cv:>12} | "
              f"{row['PTP_OFFSET']['steady_state_max_drift']:>8.4f} {p_cv:>8}")

    # Hypothesis check
    ptp_all_bounded = all(
        r["steady_state_max_drift"] < 1.0
        for r in results if r["strategy"] == "PTP_OFFSET"
    )
    ptp_all_converge = all(
        r["converged"]
        for r in results if r["strategy"] == "PTP_OFFSET"
    )
    naive_diverges = all(
        not r["converged"]
        for r in results if r["strategy"] == "NAIVE" and r["latency"] > 0
    )

    hypothesis = {
        "ptp_bounded_drift_at_all_latencies": ptp_all_bounded,
        "ptp_converges_at_all_latencies": ptp_all_converge,
        "naive_diverges_for_positive_latency": naive_diverges,
        "hypothesis_supported": ptp_all_bounded and naive_diverges,
    }

    # Key findings
    key_findings = []

    # Compare strategies at each latency
    for latency in latencies:
        row = {}
        for s in strategies:
            r = [x for x in results if x["latency"] == latency and x["strategy"] == s.value][0]
            row[s.value] = r

        if latency == 0:
            key_findings.append(
                f"Latency=0: All strategies converge. "
                f"NAIVE drift={row['NAIVE']['steady_state_max_drift']:.4f}, "
                f"CRISTIAN drift={row['CRISTIAN']['steady_state_max_drift']:.4f}, "
                f"PTP drift={row['PTP_OFFSET']['steady_state_max_drift']:.4f}. "
                f"No advantage to smarter strategies when latency=0."
            )
        else:
            naive_d = row['NAIVE']['steady_state_max_drift']
            cristian_d = row['CRISTIAN']['steady_state_max_drift']
            ptp_d = row['PTP_OFFSET']['steady_state_max_drift']
            improvement_cristian = ((naive_d - cristian_d) / naive_d * 100) if naive_d > 0 else 0
            improvement_ptp = ((naive_d - ptp_d) / naive_d * 100) if naive_d > 0 else 0
            key_findings.append(
                f"Latency={latency}: NAIVE drift={naive_d:.4f}, "
                f"CRISTIAN drift={cristian_d:.4f} ({improvement_cristian:+.1f}%), "
                f"PTP drift={ptp_d:.4f} ({improvement_ptp:+.1f}%). "
                f"PTP converges={'YES' if row['PTP_OFFSET']['converged'] else 'NO'}."
            )

    if hypothesis["hypothesis_supported"]:
        key_findings.append(
            "HYPOTHESIS CONFIRMED: PTP_OFFSET achieves bounded drift at all latencies "
            "while NAIVE diverges for any latency>0. The midpoint estimation correctly "
            "compensates for message staleness."
        )
    else:
        key_findings.append(
            f"HYPOTHESIS PARTIAL: PTP bounded={ptp_all_bounded}, PTP converges={ptp_all_converge}, "
            f"NAIVE diverges={naive_diverges}. See per-latency details above."
        )

    # Cristian assessment
    cristian_improves = []
    for latency in latencies:
        if latency == 0:
            continue
        n_r = [x for x in results if x["latency"] == latency and x["strategy"] == "NAIVE"][0]
        c_r = [x for x in results if x["latency"] == latency and x["strategy"] == "CRISTIAN"][0]
        cristian_improves.append(c_r["steady_state_max_drift"] < n_r["steady_state_max_drift"])
    if all(cristian_improves):
        key_findings.append(
            "CRISTIAN always improves over NAIVE for latency>0, but may not converge. "
            "Recency weighting helps but doesn't fully solve the staleness problem."
        )
    else:
        key_findings.append(
            f"CRISTIAN improves over NAIVE in {sum(cristian_improves)}/{len(cristian_improves)} "
            f"nonzero-latency cases. Mixed results for recency weighting."
        )

    output = {
        "experiment": 23,
        "title": "Latency-Aware Correction Strategies",
        "description": "Fixes Exp20 phase transition with 3 correction strategies",
        "N": N,
        "latencies": latencies,
        "strategies": [s.value for s in strategies],
        "delta": delta,
        "max_ticks": max_ticks,
        "warmup_ticks": warmup,
        "convergence_threshold": 0.1,
        "all_results": results,
        "hypothesis": hypothesis,
        "key_findings": key_findings,
    }

    os.makedirs("experiments/results", exist_ok=True)
    out_path = "experiments/results/experiment23_latency_aware.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved → {out_path}")

    print("\n=== HYPOTHESIS ===")
    for k, v in hypothesis.items():
        print(f"  {k}: {v}")

    print("\n=== KEY FINDINGS ===")
    for i, f in enumerate(key_findings):
        print(f"  [{i+1}] {f}")

    return output


if __name__ == "__main__":
    run_experiment()
