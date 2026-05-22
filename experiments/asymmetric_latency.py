#!/usr/bin/env python3
"""Experiment 36: Asymmetric Latency — PTP under send/receive delay mismatch.

Real networks have different send/receive delays. PTP correction measures RTT
but assumes symmetric delay. How much does asymmetry hurt?

Tests:
- Standard PTP (assumes symmetric delay) at various asymmetry ratios
- PTP with asymmetry correction (two-timestamp method estimating one-way delay)
- Symmetric baseline for comparison

Asymmetry ratio α = send_latency / receive_latency
Base latency = 5 ticks (so α=3 means send=7.5, receive=2.5)
"""
import json
import math
import os
import random
from collections import defaultdict

random.seed(42)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "experiment36_asymmetric.json")

N_AGENTS = 10
TOTAL_TICKS = 10000
BASE_LATENCY = 5.0
ASYMMETRY_RATIOS = [1.0, 1.5, 2.0, 3.0, 5.0, 10.0]


def generate_laman_graph(n, seed=42):
    """Generate a Laman (2,3)-sparse graph using Henneberg construction."""
    rng = random.Random(seed)
    edges = set()
    adj = defaultdict(set)

    # Start with triangle K3
    for i in range(3):
        for j in range(i + 1, 3):
            edges.add((i, j))
            adj[i].add(j)
            adj[j].add(i)

    for k in range(3, n):
        # Pick 2 existing nodes
        nodes = list(range(k))
        rng.shuffle(nodes)
        u, v = nodes[0], nodes[1]
        edges.add((u, k))
        edges.add((v, k))
        adj[u].add(k)
        adj[k].add(u)
        adj[v].add(k)
        adj[k].add(v)

    # Add extra edges to reach 2n-3
    target = 2 * n - 3
    attempts = 0
    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(all_pairs)
    idx = 0
    while len(edges) < target and idx < len(all_pairs):
        e = all_pairs[idx]
        if e not in edges:
            edges.add(e)
            adj[e[0]].add(e[1])
            adj[e[1]].add(e[0])
        idx += 1

    return edges, adj


class MetronomeAgent:
    """Agent with local clock drift and PTP-style correction."""

    def __init__(self, idx, epsilon=0.01, delta=0.0625):
        self.idx = idx
        self.epsilon = epsilon
        self.delta = delta
        self.local_clock = 0.0
        self.drift_rate = epsilon * (idx - N_AGENTS / 2) / (N_AGENTS / 2)
        self.neighbors = []
        # For corrected PTP: track per-peer one-way delay estimates
        self.peer_owd_estimates = {}

    def tick(self):
        self.local_clock += 1.0 + self.drift_rate


class Message:
    """A network message with separate send and receive timestamps."""

    def __init__(self, sender_idx, send_time, payload, send_delay, recv_delay):
        self.sender_idx = sender_idx
        self.send_time = send_time  # sender's clock at send
        self.payload = payload
        self.send_delay = send_delay  # ticks in transit (sender→receiver direction)
        self.recv_delay = recv_delay  # not used for this direction, stored for bookkeeping
        self.arrival_tick = None  # set when injected
        self.recv_time = None  # receiver's clock at receipt


def run_experiment(alpha, use_correction=False, seed=42):
    """Run one simulation at given asymmetry ratio.

    If use_correction=True, use two-timestamp method to estimate one-way delay
    instead of assuming RTT/2.
    """
    rng = random.Random(seed)
    edges, adj = generate_laman_graph(N_AGENTS, seed=42)

    agents = [MetronomeAgent(i) for i in range(N_AGENTS)]

    # Set up neighbor lists
    for (u, v) in edges:
        agents[u].neighbors.append(v)
        agents[v].neighbors.append(u)

    # Compute delays: send_delay and recv_delay per edge
    # alpha = send_latency / recv_latency, send + recv = 2 * BASE_LATENCY
    recv_delay = 2.0 * BASE_LATENCY / (1.0 + alpha)
    send_delay = alpha * recv_delay

    # Message queue: (arrival_tick, Message)
    pending = []

    drift_history = []  # (tick, max_drift, mean_drift)

    for tick in range(TOTAL_TICKS):
        # Deliver pending messages
        while pending and pending[0][0] <= tick:
            _, msg = pending.pop(0)
            receiver = agents[msg.receiver_idx]
            msg.recv_time = receiver.local_clock

            # PTP correction
            reported_offset = msg.payload["clock"] - msg.recv_time

            if use_correction:
                # Two-timestamp method: estimate one-way delay
                # We know send_delay (it's the network property we're simulating)
                # In practice, PTP can't know this. The "correction" here uses
                # a peer's historical RTT and assumes the minimum observed RTT
                # gives the best one-way estimate.
                # Simulate: track per-peer RTT samples, use min RTT to estimate
                # one-way as min_rtt * (send_delay / (send_delay + recv_delay))
                peer_key = (msg.receiver_idx, msg.sender_idx)
                if peer_key not in receiver.peer_owd_estimates:
                    receiver.peer_owd_estimates[peer_key] = []
                rtt = msg.send_delay + msg.recv_delay
                receiver.peer_owd_estimates[peer_key].append(rtt)
                # Use min RTT and asymmetry ratio estimate
                min_rtt = min(receiver.peer_owd_estimates[peer_key])
                # Estimate send-side delay from min RTT
                # In practice we'd estimate α from observations; here we use
                # the "known" ratio as a best-case correction
                est_send_delay = min_rtt * send_delay / (send_delay + recv_delay)
                correction = reported_offset + est_send_delay
                receiver.local_clock += receiver.delta * correction
            else:
                # Standard PTP: assumes symmetric delay (RTT/2)
                rtt = msg.send_delay + msg.recv_delay
                assumed_delay = rtt / 2.0
                correction = reported_offset + assumed_delay
                receiver.local_clock += receiver.delta * correction

        # All agents tick
        for a in agents:
            a.tick()

        # Send messages: each agent sends to each neighbor periodically
        if tick % 10 == 0:
            for a in agents:
                for nb_idx in a.neighbors:
                    # Add jitter
                    jitter = rng.uniform(-0.5, 0.5)
                    actual_send_delay = max(0.5, send_delay + jitter)
                    actual_recv_delay = max(0.5, recv_delay + jitter * 0.3)
                    arrival = tick + int(math.ceil(actual_send_delay))
                    msg = Message(
                        sender_idx=a.idx,
                        send_time=a.local_clock,
                        payload={"clock": a.local_clock},
                        send_delay=actual_send_delay,
                        recv_delay=actual_recv_delay,
                    )
                    msg.receiver_idx = nb_idx
                    msg.arrival_tick = arrival
                    pending.append((arrival, msg))
            pending.sort(key=lambda x: x[0])

        # Record drift every 100 ticks
        if tick % 100 == 0 and tick > 0:
            clocks = [a.local_clock for a in agents]
            mean_clock = sum(clocks) / len(clocks)
            max_drift = max(abs(c - mean_clock) for c in clocks)
            mean_drift = sum(abs(c - mean_clock) for c in clocks) / len(clocks)
            drift_history.append({
                "tick": tick,
                "max_drift": round(max_drift, 6),
                "mean_drift": round(mean_drift, 6),
            })

    # Final stats
    clocks = [a.local_clock for a in agents]
    mean_clock = sum(clocks) / len(clocks)
    final_max_drift = max(abs(c - mean_clock) for c in clocks)
    final_mean_drift = sum(abs(c - mean_clock) for c in clocks) / len(clocks)
    peak_drift = max(d["max_drift"] for d in drift_history) if drift_history else final_max_drift

    return {
        "alpha": alpha,
        "send_delay": round(send_delay, 4),
        "recv_delay": round(recv_delay, 4),
        "use_correction": use_correction,
        "final_max_drift": round(final_max_drift, 6),
        "final_mean_drift": round(final_mean_drift, 6),
        "peak_drift": round(peak_drift, 6),
        "drift_history": drift_history[-20:],  # last 20 samples
    }


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    results = {
        "experiment": "experiment36_asymmetric_latency",
        "config": {
            "n_agents": N_AGENTS,
            "total_ticks": TOTAL_TICKS,
            "base_latency": BASE_LATENCY,
            "asymmetry_ratios": ASYMMETRY_RATIOS,
        },
        "hypothesis": "PTP degrades gracefully — 3× asymmetry causes <2× drift increase",
        "runs": [],
        "comparison": [],
        "conclusion": None,
    }

    # Baseline: symmetric (alpha=1.0, no correction)
    baseline = run_experiment(alpha=1.0, use_correction=False, seed=42)
    baseline_drift = baseline["final_max_drift"]

    for alpha in ASYMMETRY_RATIOS:
        # Standard PTP (no correction)
        std = run_experiment(alpha=alpha, use_correction=False, seed=42)
        std["mode"] = "standard_ptp"

        # Corrected PTP
        corr = run_experiment(alpha=alpha, use_correction=True, seed=42)
        corr["mode"] = "corrected_ptp"

        results["runs"].append(std)
        results["runs"].append(corr)

        # Comparison
        std_degradation = std["final_max_drift"] / baseline_drift if baseline_drift > 0 else float("inf")
        corr_degradation = corr["final_max_drift"] / baseline_drift if baseline_drift > 0 else float("inf")
        improvement = std["final_max_drift"] / corr["final_max_drift"] if corr["final_max_drift"] > 0 else float("inf")

        results["comparison"].append({
            "alpha": alpha,
            "send_delay": std["send_delay"],
            "recv_delay": std["recv_delay"],
            "standard_max_drift": std["final_max_drift"],
            "corrected_max_drift": corr["final_max_drift"],
            "standard_degradation_vs_baseline": round(std_degradation, 4),
            "corrected_degradation_vs_baseline": round(corr_degradation, 4),
            "correction_improvement_factor": round(improvement, 4),
        })

    # Evaluate hypothesis
    alpha3 = [c for c in results["comparison"] if c["alpha"] == 3.0]
    if alpha3:
        deg = alpha3[0]["standard_degradation_vs_baseline"]
        if deg < 2.0:
            results["conclusion"] = (
                f"HYPOTHESIS CONFIRMED: At α=3.0, drift degradation is {deg:.2f}× "
                f"(under 2× threshold). PTP degrades gracefully under asymmetry."
            )
        else:
            results["conclusion"] = (
                f"HYPOTHESIS REJECTED: At α=3.0, drift degradation is {deg:.2f}× "
                f"(exceeds 2× threshold). PTP does NOT degrade gracefully."
            )

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    print(f"Experiment 36: Asymmetric Latency")
    print(f"{'α':>5} {'Send':>7} {'Recv':>7} {'StdDrift':>10} {'CorrDrift':>10} {'StdDeg':>8} {'CorrDeg':>8} {'Improv':>8}")
    print("-" * 75)
    for c in results["comparison"]:
        print(
            f"{c['alpha']:>5.1f} {c['send_delay']:>7.2f} {c['recv_delay']:>7.2f} "
            f"{c['standard_max_drift']:>10.4f} {c['corrected_max_drift']:>10.4f} "
            f"{c['standard_degradation_vs_baseline']:>8.3f} {c['corrected_degradation_vs_baseline']:>8.3f} "
            f"{c['correction_improvement_factor']:>8.3f}"
        )
    print(f"\n{results['conclusion']}")
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
