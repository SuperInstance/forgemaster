#!/usr/bin/env python3
"""Experiment 25: PTP Production Validation.

Stress-tests PTP correction under production-like conditions:
- Fixed latencies: 0, 1, 5, 10, 20, 50, 100, 200 ticks
- Variable latency: each message has random latency in [0, L]
- Burst latency: spikes to 10× normal for 50-tick windows
- Asymmetric latency: send 2× faster than receive

For each condition, run 10 trials of 2000 ticks.
Measure: convergence tick, steady-state drift, jitter (variance of drift over time).

Hypothesis: PTP maintains bounded drift (< δ) at all latencies including adversarial conditions.
"""
import json
import random
import os
import math
import time
from collections import deque
from enum import Enum

SEED = 42


class LatencyMode(Enum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"
    BURST = "BURST"
    ASYMMETRIC = "ASYMMETRIC"


def build_laman_topology(n, seed_offset=0):
    rng = random.Random(SEED + seed_offset)
    edges = []
    for i in range(3):
        for j in range(i + 1, 3):
            edges.append((i, j))
    for k in range(3, n):
        targets = rng.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges


class PTPAgent:
    """Agent with PTP-style offset correction (from Exp23)."""

    def __init__(self, idx, delta=0.0625, epsilon=0.01):
        self.idx = idx
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.neighbors = []
        self.drift_rate = epsilon * (idx - 4.5) / 20.0
        self.inbox = deque()

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def broadcast(self, current_tick, latency_fn):
        """Send current clock reading to all neighbors.
        latency_fn(tick, sender, receiver) -> int latency in ticks.
        """
        reported = self.local_clock
        for neighbor, _ in self.neighbors:
            latency = latency_fn(current_tick, self.idx, neighbor.idx)
            deliver_at = current_tick + latency
            neighbor.inbox.append((deliver_at, self.idx, reported, current_tick))

    def receive(self, current_tick):
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

    def correct_ptp(self, reports, current_tick):
        """PTP-style offset estimation with proportional correction."""
        if not reports:
            return

        offset_estimates = []
        for sender_idx, reported_clock, sent_tick in reports:
            latency = current_tick - sent_tick
            neighbor_now = reported_clock + latency
            offset = neighbor_now - self.local_clock
            offset_estimates.append(offset)

        if not offset_estimates:
            return

        avg_offset = sum(offset_estimates) / len(offset_estimates)
        relaxation = 0.5
        correction = relaxation * avg_offset
        correction = max(-2.0, min(2.0, correction))
        self.local_clock += correction


def make_latency_fn(mode, base_latency, max_ticks=2000, rng=None):
    """Create a latency function for the given mode."""

    if mode == LatencyMode.FIXED:
        def fn(tick, sender, receiver):
            return base_latency
        return fn

    elif mode == LatencyMode.VARIABLE:
        def fn(tick, sender, receiver):
            return rng.randint(0, base_latency) if base_latency > 0 else 0
        return fn

    elif mode == LatencyMode.BURST:
        # Burst windows: every 400 ticks, a 50-tick burst with 10× latency
        burst_period = 400
        burst_duration = 50
        def fn(tick, sender, receiver):
            phase = tick % burst_period
            if phase < burst_duration:
                return base_latency * 10
            return base_latency
        return fn

    elif mode == LatencyMode.ASYMMETRIC:
        # Send latency = base/2, receive latency = base (2:1 ratio)
        def fn(tick, sender, receiver):
            # Simple deterministic asymmetry: lower idx -> higher idx gets faster path
            if sender < receiver:
                return max(1, base_latency // 2)
            else:
                return base_latency
        return fn

    raise ValueError(f"Unknown mode: {mode}")


def run_trial(N, mode, base_latency, trial_seed, max_ticks=2000, warmup=200):
    """Run a single trial. Returns metrics dict."""
    rng = random.Random(trial_seed)
    agents = [PTPAgent(i) for i in range(N)]
    edges = build_laman_topology(N, seed_offset=trial_seed)

    for i, j in edges:
        agents[i].neighbors.append((agents[j], 1.0))
        agents[j].neighbors.append((agents[i], 1.0))

    latency_fn = make_latency_fn(mode, base_latency, max_ticks, rng)

    drift_log = []
    convergence_tick = None
    consecutive_stable = 0
    n_edges = len(edges)

    for tick in range(1, max_ticks + 1):
        for a in agents:
            a.tick(tick)

        for a in agents:
            a.broadcast(tick, latency_fn)

        for a in agents:
            reports = a.receive(tick)
            a.correct_ptp(reports, tick)

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

    # Compute metrics
    post_warmup = drift_log[warmup:]
    steady_state_drift = max(post_warmup[-200:])  # max over last 200 ticks
    mean_drift_ss = sum(post_warmup[-200:]) / 200.0
    peak_drift = max(drift_log)

    # Jitter: variance of drift over steady state (last 200 ticks)
    ss_window = post_warmup[-200:]
    jitter = sum((d - mean_drift_ss) ** 2 for d in ss_window) / len(ss_window)

    # Messages sent (approximate — each edge generates one message per direction per tick)
    total_msgs = 2 * n_edges * max_ticks

    return {
        "trial_seed": trial_seed,
        "convergence_tick": convergence_tick,
        "steady_state_max_drift": round(steady_state_drift, 6),
        "steady_state_mean_drift": round(mean_drift_ss, 6),
        "peak_drift": round(peak_drift, 6),
        "jitter": round(jitter, 8),
        "converged": convergence_tick is not None,
        "messages_sent": total_msgs,
    }


def run_latency_sweep(mode, latencies, n_trials=10):
    """Run trials for all latencies under a given mode."""
    results = []
    for base_lat in latencies:
        trials = []
        print(f"    L={base_lat:>3}...", end=" ", flush=True)
        for t in range(n_trials):
            trial_seed = SEED + t * 1000 + base_lat
            r = run_trial(10, mode, base_lat, trial_seed)
            r["base_latency"] = base_lat
            r["trial"] = t
            trials.append(r)

        # Aggregate
        conv_count = sum(1 for tr in trials if tr["converged"])
        avg_ss_drift = sum(tr["steady_state_max_drift"] for tr in trials) / n_trials
        max_ss_drift = max(tr["steady_state_max_drift"] for tr in trials)
        avg_jitter = sum(tr["jitter"] for tr in trials) / n_trials
        avg_peak = sum(tr["peak_drift"] for tr in trials) / n_trials
        avg_conv_tick = None
        conv_ticks = [tr["convergence_tick"] for tr in trials if tr["convergence_tick"] is not None]
        if conv_ticks:
            avg_conv_tick = round(sum(conv_ticks) / len(conv_ticks), 1)

        agg = {
            "base_latency": base_lat,
            "mode": mode.value,
            "n_trials": n_trials,
            "convergence_rate": f"{conv_count}/{n_trials}",
            "avg_steady_state_max_drift": round(avg_ss_drift, 6),
            "max_steady_state_max_drift": round(max_ss_drift, 6),
            "avg_jitter": round(avg_jitter, 8),
            "avg_peak_drift": round(avg_peak, 6),
            "avg_convergence_tick": avg_conv_tick,
            "all_bounded": max_ss_drift < 0.0625,  # bounded by δ
            "trials": trials,
        }
        results.append(agg)
        tag = "✓" if agg["all_bounded"] else "✗"
        print(f"ss_drift={avg_ss_drift:.4f}  jitter={avg_jitter:.6f}  conv={conv_count}/{n_trials}  [{tag}]")

    return results


def run_experiment():
    start_time = time.time()
    N = 10
    n_trials = 10
    max_ticks = 2000
    warmup = 200
    latencies = [0, 1, 5, 10, 20, 50, 100, 200]
    delta = 0.0625

    all_results = []
    summary = {}

    modes = [
        (LatencyMode.FIXED, "Fixed Latency"),
        (LatencyMode.VARIABLE, "Variable Latency [0, L]"),
        (LatencyMode.BURST, "Burst Latency (10× spikes)"),
        (LatencyMode.ASYMMETRIC, "Asymmetric Latency (2:1 send/recv)"),
    ]

    for mode, label in modes:
        print(f"\n{'='*60}")
        print(f"  Mode: {label}")
        print(f"{'='*60}")
        mode_results = run_latency_sweep(mode, latencies, n_trials)
        all_results.extend(mode_results)
        summary[mode.value] = {
            "label": label,
            "all_bounded": all(r["all_bounded"] for r in mode_results),
            "max_drift_across_latencies": round(
                max(r["max_steady_state_max_drift"] for r in mode_results), 6
            ),
            "worst_latency": max(
                mode_results, key=lambda r: r["max_steady_state_max_drift"]
            )["base_latency"],
        }

    # Hypothesis check
    all_bounded = all(r["all_bounded"] for r in all_results)
    # Relaxed check: bounded at < δ (0.0625) or at least < 10× δ
    all_reasonably_bounded = all(
        r["max_steady_state_max_drift"] < delta * 10 for r in all_results
    )

    hypothesis = {
        "statement": "PTP maintains bounded drift (< δ) at all latencies including adversarial conditions",
        "delta": delta,
        "strict_bounded_all_conditions": all_bounded,
        "relaxed_bounded_10delta": all_reasonably_bounded,
        "hypothesis_supported": all_bounded,
    }

    # Key findings
    key_findings = []

    # Per-mode summary
    for mode, label in modes:
        s = summary[mode.value]
        mode_results = [r for r in all_results if r["mode"] == mode.value]
        worst = max(mode_results, key=lambda r: r["max_steady_state_max_drift"])
        best = min(mode_results, key=lambda r: r["max_steady_state_max_drift"])
        key_findings.append(
            f"{label}: bounded={'YES' if s['all_bounded'] else 'NO'}, "
            f"worst drift={s['max_drift_across_latencies']:.4f} at L={s['worst_latency']}, "
            f"best drift={best['avg_steady_state_max_drift']:.4f} at L={best['base_latency']}"
        )

    # Jitter analysis
    high_jitter = [r for r in all_results if r["avg_jitter"] > 0.001]
    if high_jitter:
        key_findings.append(
            f"High jitter (>{0.001}) at {len(high_jitter)}/{len(all_results)} conditions. "
            f"Worst jitter: {max(r['avg_jitter'] for r in high_jitter):.6f} "
            f"at L={max(high_jitter, key=lambda r: r['avg_jitter'])['base_latency']} "
            f"mode={max(high_jitter, key=lambda r: r['avg_jitter'])['mode']}"
        )
    else:
        key_findings.append("Jitter remains low (<0.001) across all conditions. PTP is stable.")

    # Scalability with latency
    for mode_val in [m.value for m, _ in modes]:
        mode_results = [r for r in all_results if r["mode"] == mode_val]
        drifts_by_lat = [(r["base_latency"], r["avg_steady_state_max_drift"]) for r in mode_results]
        # Check if drift grows sublinearly
        low_lat = [d for l, d in drifts_by_lat if l <= 20]
        high_lat = [d for l, d in drifts_by_lat if l > 20]
        if low_lat and high_lat:
            avg_low = sum(low_lat) / len(low_lat)
            avg_high = sum(high_lat) / len(high_lat)
            ratio = avg_high / avg_low if avg_low > 0 else float('inf')
            # Latency grew 5-10× but drift grew how much?
            key_findings.append(
                f"{mode_val}: drift scaling = {ratio:.2f}× when latency goes from ≤20 to >20. "
                f"{'Sublinear — PTP absorbs latency well.' if ratio < 5 else 'Superlinear — PTP degrades at high latency.'}"
            )

    if hypothesis["hypothesis_supported"]:
        key_findings.append(
            "HYPOTHESIS CONFIRMED: PTP maintains drift < δ at ALL latency levels and ALL "
            "adversarial conditions (variable, burst, asymmetric). PTP is production-ready."
        )
    elif all_reasonably_bounded:
        key_findings.append(
            "HYPOTHESIS PARTIALLY SUPPORTED: PTP drift bounded at < 10δ in all conditions, "
            "but exceeds strict δ bound at some high-latency scenarios. Still very stable."
        )
    else:
        key_findings.append(
            "HYPOTHESIS REJECTED: PTP drift exceeds 10δ in some conditions. "
            "See per-condition details for breakdown."
        )

    elapsed = round(time.time() - start_time, 1)

    output = {
        "experiment": 25,
        "title": "PTP Production Validation",
        "description": "Stress-test PTP correction under fixed, variable, burst, and asymmetric latency",
        "N": N,
        "n_trials": n_trials,
        "max_ticks": max_ticks,
        "warmup_ticks": warmup,
        "delta": delta,
        "latencies": latencies,
        "modes": [m.value for m, _ in modes],
        "all_results": all_results,
        "summary_by_mode": summary,
        "hypothesis": hypothesis,
        "key_findings": key_findings,
        "elapsed_seconds": elapsed,
    }

    os.makedirs("experiments/results", exist_ok=True)
    out_path = "experiments/results/experiment25_ptp_production.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved → {out_path}")

    # Print summary table
    print(f"\n{'='*90}")
    print("PRODUCTION VALIDATION SUMMARY")
    print(f"{'='*90}")
    print(f"{'Mode':<16} {'Lat':>4} {'SS Drift':>10} {'Max SS':>10} {'Jitter':>12} {'Conv':>6} {'Bounded':>8}")
    print("-" * 90)
    for r in all_results:
        tag = "✓" if r["all_bounded"] else "✗"
        print(f"{r['mode']:<16} {r['base_latency']:>4} {r['avg_steady_state_max_drift']:>10.4f} "
              f"{r['max_steady_state_max_drift']:>10.4f} {r['avg_jitter']:>12.6f} "
              f"{r['convergence_rate']:>6} {tag:>8}")

    print(f"\n{'='*60}")
    print("HYPOTHESIS")
    print(f"{'='*60}")
    for k, v in hypothesis.items():
        print(f"  {k}: {v}")

    print(f"\n{'='*60}")
    print("KEY FINDINGS")
    print(f"{'='*60}")
    for i, f in enumerate(key_findings):
        print(f"  [{i+1}] {f}")

    print(f"\nElapsed: {elapsed}s")

    return output


if __name__ == "__main__":
    run_experiment()
