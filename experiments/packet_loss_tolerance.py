#!/usr/bin/env python3
"""Experiment 32: Packet Loss Tolerance.

Real networks drop packets. How well does PTP correction maintain convergence
under packet loss?

Setup:
- N=10 agents, Laman topology, latency=5 ticks
- Packet loss rates: 0%, 5%, 10%, 20%, 30%, 50%, 70%
- PTP correction strategy
- For each loss rate: 10 trials, 1000 ticks per trial
- When a packet is "lost", the agent receives no correction that tick
- Also test: retransmission (send 2x at 50% loss) vs no retransmission
- Measure: convergence rate, steady-state drift, convergence tick, jitter

Hypothesis: PTP maintains convergence up to 30% packet loss. Above 50%,
drift degrades but doesn't diverge.

Save to experiments/results/experiment32_packet_loss.json
"""
import json
import random
import os
import math
from collections import deque

random.seed(42)


def build_laman_topology(n):
    """Build a Laman (generically minimally rigid) graph on n vertices."""
    edges = []
    # Start with K3
    for i in range(3):
        for j in range(i + 1, 3):
            edges.append((i, j))
    # Add remaining vertices with exactly 2 edges to earlier vertices
    for k in range(3, n):
        targets = random.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges


class PacketLossAgent:
    """Agent with PTP correction and packet loss simulation."""

    def __init__(self, idx, delta=0.0625, epsilon=0.01):
        self.idx = idx
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.neighbors = []  # list of (agent_ref, weight)
        self.drift_rate = epsilon * (idx - 4.5) / 20.0
        self.inbox = deque()
        self.estimated_offset = 0.0

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def broadcast(self, current_tick, latency, loss_rate, retransmit=False, rng=None):
        """Send current clock reading to all neighbors.

        Args:
            loss_rate: probability [0,1] that a packet is lost
            retransmit: if True, send each packet twice (independent loss)
            rng: random.Random instance for reproducibility
        """
        if rng is None:
            rng = random
        reported = self.local_clock
        for neighbor, _ in self.neighbors:
            num_sends = 2 if retransmit else 1
            for _ in range(num_sends):
                if rng.random() >= loss_rate:
                    deliver_at = current_tick + latency
                    neighbor.inbox.append(
                        (deliver_at, self.idx, reported, current_tick)
                    )
                # else: packet is lost, nothing delivered

    def receive(self, current_tick):
        """Collect all messages due for delivery."""
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
        """PTP-style offset estimation correction."""
        if not reports:
            return

        offset_estimates = []
        for sender_idx, reported_clock, sent_tick in reports:
            latency = current_tick - sent_tick
            neighbor_now = reported_clock + latency
            offset = neighbor_now - self.local_clock
            offset_estimates.append(offset)

        avg_offset = sum(offset_estimates) / len(offset_estimates)
        relaxation = 0.5
        correction = relaxation * avg_offset
        correction = max(-2.0, min(2.0, correction))
        self.local_clock += correction


def run_single_trial(N, latency, loss_rate, max_ticks=1000, warmup=200,
                     retransmit=False, seed=42):
    """Run a single trial with given packet loss rate."""
    rng = random.Random(seed)
    agents = [PacketLossAgent(i) for i in range(N)]
    edges = build_laman_topology(N)

    # Reproducible topology — reseed after building
    rng = random.Random(seed + 1000)

    for i, j in edges:
        agents[i].neighbors.append((agents[j], 1.0))
        agents[j].neighbors.append((agents[i], 1.0))

    drift_log = []
    convergence_tick = None
    consecutive_stable = 0
    packets_sent = 0
    packets_lost = 0

    for tick in range(1, max_ticks + 1):
        for a in agents:
            a.tick(tick)

        # Count messages
        n_neighbors_total = sum(len(a.neighbors) for a in agents)
        packets_sent += n_neighbors_total

        for a in agents:
            a.broadcast(tick, latency, loss_rate, retransmit=retransmit, rng=rng)

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
    steady_state_drift = max(drift_log[-100:])
    peak_drift = max(drift_log)
    mean_drift_last100 = sum(drift_log[-100:]) / 100.0
    converged = convergence_tick is not None

    # Jitter: standard deviation of drift in last 100 ticks
    last_100 = drift_log[-100:]
    mean_d = sum(last_100) / len(last_100)
    jitter = math.sqrt(sum((d - mean_d) ** 2 for d in last_100) / len(last_100))

    # Estimate packets lost
    effective_loss = loss_rate
    if retransmit:
        # Probability both copies lost = loss_rate^2
        effective_loss = loss_rate ** 2
    packets_lost_estimate = int(packets_sent * effective_loss)

    return {
        "convergence_tick": convergence_tick,
        "steady_state_max_drift": round(steady_state_drift, 6),
        "peak_drift": round(peak_drift, 6),
        "mean_drift_last100": round(mean_drift_last100, 6),
        "jitter_last100": round(jitter, 6),
        "converged": converged,
        "packets_sent": packets_sent,
        "packets_lost_estimate": packets_lost_estimate,
        "drift_log_last100": [round(d, 6) for d in drift_log[-100:]],
    }


def run_experiment():
    """Run the full packet loss tolerance experiment."""
    N = 10
    latency = 5
    max_ticks = 1000
    warmup = 200
    num_trials = 10

    loss_rates = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70]

    results = {
        "experiment": 32,
        "name": "Packet Loss Tolerance",
        "hypothesis": "PTP maintains convergence up to 30% packet loss. Above 50%, drift degrades but doesn't diverge.",
        "params": {
            "N": N,
            "latency": latency,
            "max_ticks": max_ticks,
            "warmup": warmup,
            "num_trials": num_trials,
            "correction": "PTP_OFFSET",
        },
        "loss_rate_results": [],
        "retransmission_comparison": [],
    }

    # Phase 1: Sweep loss rates
    for loss_rate in loss_rates:
        print(f"  Loss rate {loss_rate*100:.0f}%...")
        trial_results = []
        for trial in range(num_trials):
            seed = 42 + trial * 7 + int(loss_rate * 1000)
            r = run_single_trial(N, latency, loss_rate, max_ticks, warmup,
                                 retransmit=False, seed=seed)
            trial_results.append(r)

        # Aggregate across trials
        converged_count = sum(1 for t in trial_results if t["converged"])
        convergence_ticks = [t["convergence_tick"] for t in trial_results if t["convergence_tick"] is not None]
        avg_convergence = sum(convergence_ticks) / len(convergence_ticks) if convergence_ticks else None

        avg_steady = sum(t["steady_state_max_drift"] for t in trial_results) / num_trials
        avg_peak = sum(t["peak_drift"] for t in trial_results) / num_trials
        avg_mean = sum(t["mean_drift_last100"] for t in trial_results) / num_trials
        avg_jitter = sum(t["jitter_last100"] for t in trial_results) / num_trials

        results["loss_rate_results"].append({
            "loss_rate": loss_rate,
            "convergence_rate": round(converged_count / num_trials, 2),
            "avg_convergence_tick": round(avg_convergence, 1) if avg_convergence else None,
            "avg_steady_state_drift": round(avg_steady, 6),
            "avg_peak_drift": round(avg_peak, 6),
            "avg_mean_drift": round(avg_mean, 6),
            "avg_jitter": round(avg_jitter, 6),
            "trials": trial_results,
        })

        print(f"    Convergence: {converged_count}/{num_trials}, "
              f"steady drift: {avg_steady:.4f}, jitter: {avg_jitter:.4f}")

    # Phase 2: Retransmission comparison at 50% loss
    print("  Retransmission comparison at 50% loss...")
    for retransmit in [False, True]:
        label = "retransmit_2x" if retransmit else "no_retransmit"
        trial_results = []
        for trial in range(num_trials):
            seed = 42 + trial * 7 + 500  # different seed space
            r = run_single_trial(N, latency, 0.50, max_ticks, warmup,
                                 retransmit=retransmit, seed=seed)
            trial_results.append(r)

        converged_count = sum(1 for t in trial_results if t["converged"])
        convergence_ticks = [t["convergence_tick"] for t in trial_results if t["convergence_tick"] is not None]
        avg_convergence = sum(convergence_ticks) / len(convergence_ticks) if convergence_ticks else None
        avg_steady = sum(t["steady_state_max_drift"] for t in trial_results) / num_trials
        avg_jitter = sum(t["jitter_last100"] for t in trial_results) / num_trials

        results["retransmission_comparison"].append({
            "loss_rate": 0.50,
            "retransmit": retransmit,
            "label": label,
            "convergence_rate": round(converged_count / num_trials, 2),
            "avg_convergence_tick": round(avg_convergence, 1) if avg_convergence else None,
            "avg_steady_state_drift": round(avg_steady, 6),
            "avg_jitter": round(avg_jitter, 6),
            "trials": trial_results,
        })

        print(f"    {label}: convergence {converged_count}/{num_trials}, "
              f"steady drift: {avg_steady:.4f}")

    # Summary
    results["summary"] = summarize(results)
    return results


def summarize(results):
    """Generate a text summary of findings."""
    lines = []
    lines.append("=== Experiment 32: Packet Loss Tolerance ===")
    lines.append("")
    lines.append("Loss Rate | Convergence | Steady Drift | Jitter")
    lines.append("---------|-------------|-------------|--------")
    for lr in results["loss_rate_results"]:
        conv = f"{lr['convergence_rate']*100:.0f}%" if lr['convergence_rate'] is not None else "N/A"
        lines.append(
            f"  {lr['loss_rate']*100:5.1f}%  |  {conv:>8s}   |  {lr['avg_steady_state_drift']:.4f}     | {lr['avg_jitter']:.4f}"
        )

    lines.append("")
    lines.append("Retransmission comparison (50% loss):")
    for rc in results["retransmission_comparison"]:
        lines.append(
            f"  {rc['label']:16s}: convergence={rc['convergence_rate']*100:.0f}%, "
            f"steady_drift={rc['avg_steady_state_drift']:.4f}, jitter={rc['avg_jitter']:.4f}"
        )

    # Check hypothesis
    lines.append("")
    # Find 30% result
    r30 = next(r for r in results["loss_rate_results"] if r["loss_rate"] == 0.30)
    r50 = next(r for r in results["loss_rate_results"] if r["loss_rate"] == 0.50)
    r70 = next(r for r in results["loss_rate_results"] if r["loss_rate"] == 0.70)

    h1 = r30["convergence_rate"] >= 0.8
    h2 = r50["avg_steady_state_drift"] < 2.0  # not diverged
    h3 = r70["avg_steady_state_drift"] < 5.0  # still bounded

    lines.append(f"Hypothesis check:")
    lines.append(f"  PTP converges at ≤30% loss: {'CONFIRMED' if h1 else 'REFUTED'} "
                 f"(rate={r30['convergence_rate']})")
    lines.append(f"  Drift degrades but bounded at 50%: {'CONFIRMED' if h2 else 'REFUTED'} "
                 f"(drift={r50['avg_steady_state_drift']:.4f})")
    lines.append(f"  No divergence at 70%: {'CONFIRMED' if h3 else 'REFUTED'} "
                 f"(drift={r70['avg_steady_state_drift']:.4f})")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Running Experiment 32: Packet Loss Tolerance...")
    results = run_experiment()

    out_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "experiment32_packet_loss.json")

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + results["summary"])
    print(f"\nResults saved to {out_path}")
