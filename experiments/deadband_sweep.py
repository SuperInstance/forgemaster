#!/usr/bin/env python3
"""Experiment 38: Deadband Sweep — find the optimal δ (deadband threshold).

HYPOTHESIS: δ=0.1 is optimal — balances convergence speed with 80% reduction in corrections.

PROTOCOL:
- N=10 agents, Laman topology (Henneberg type-I), latency=5 ticks, gain=0.4 (optimal from Exp 37)
- Deadband δ: 0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0
- For each δ: 10 trials, 1000 ticks
- Measure: convergence tick, steady-state drift, correction count, communication savings
- The deadband suppresses correction MESSAGES — a node only sends a correction to a neighbor
  if its offset from that neighbor has changed by more than δ since the last correction sent.
  This models real PTP announce/sync message suppression.

Save to experiments/results/experiment38_deadband.json
"""

import json
import math
import random
import numpy as np
from pathlib import Path
from collections import defaultdict

random.seed(42)
np.random.seed(42)

# === Configuration ===
N_AGENTS = 10
LATENCY = 5
TICKS = 1000
TRIALS = 10
GAIN = 0.4  # optimal from Exp 37
DELTA_CONV = 1.0  # convergence threshold
CONVERGENCE_WINDOW = 50

DEADBANDS = [0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]


def henneberg_type1(n, seed=42):
    rng = random.Random(seed)
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]
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


class Agent:
    def __init__(self, idx, drift_rate=0.01, initial_offset=0.0):
        self.idx = idx
        self.clock = float(idx) * 10.0 + initial_offset
        self.drift_rate = drift_rate * ((idx - 4.5) / 4.5)
        self.neighbors = []

    def tick(self):
        self.clock += 1.0 + self.drift_rate


def run_trial(deadband, edges, adj, trial_seed):
    """Run a single trial with deadband-based message suppression.
    
    Deadband model: Each agent tracks the last clock value it sent to each neighbor.
    A new message is only sent if the clock has changed by more than δ since the last send.
    This is how real PTP devices suppress unnecessary announce messages.
    """
    rng = random.Random(trial_seed)

    agents = [Agent(i, initial_offset=rng.uniform(-5, 5)) for i in range(N_AGENTS)]
    for i, a in enumerate(agents):
        a.neighbors = adj[i]

    # Message queue: (arrival_tick, sender_idx, reported_clock)
    message_queue = []

    # Last sent clock value per (sender, receiver) pair
    last_sent = {}  # (sender, receiver) -> clock_value_sent

    # Tracking
    max_drift_history = []
    convergence_tick = None
    converged_count = 0
    messages_sent = 0
    messages_suppressed = 0
    total_exchange_opportunities = 0
    corrections_applied = 0

    for tick in range(TICKS):
        # Tick all clocks
        for a in agents:
            a.tick()

        # Message exchange phase with deadband suppression
        for a in agents:
            for nb_idx in a.neighbors:
                total_exchange_opportunities += 1
                current_clock = a.clock
                key = (a.idx, nb_idx)

                if key in last_sent:
                    # Only send if clock changed by more than δ
                    if abs(current_clock - last_sent[key]) > deadband:
                        message_queue.append((tick + LATENCY, a.idx, nb_idx, current_clock))
                        last_sent[key] = current_clock
                        messages_sent += 1
                    else:
                        messages_suppressed += 1
                else:
                    # First message always sent
                    message_queue.append((tick + LATENCY, a.idx, nb_idx, current_clock))
                    last_sent[key] = current_clock
                    messages_sent += 1

        # Deliver arrived messages and apply corrections
        arrived_this_tick = [(arr, sender, receiver, val) for arr, sender, receiver, val in message_queue if arr == tick]
        # Keep future messages
        message_queue = [(arr, sender, receiver, val) for arr, sender, receiver, val in message_queue if arr > tick]

        # Collect latest report per (receiver, sender) pair
        latest_reports = {}  # receiver -> list of (sender, reported_clock)
        for arr, sender, receiver, val in arrived_this_tick:
            if receiver not in latest_reports:
                latest_reports[receiver] = []
            latest_reports[receiver].append((sender, val))

        # Apply corrections
        for recv_idx, reports in latest_reports.items():
            if reports:
                neighbor_avg = sum(val for _, val in reports) / len(reports)
                diff = neighbor_avg - agents[recv_idx].clock
                agents[recv_idx].clock += GAIN * diff
                corrections_applied += 1

        # Measure pairwise drift
        clocks = [a.clock for a in agents]
        max_drift = max(clocks) - min(clocks)
        max_drift_history.append(max_drift)

        # Convergence detection
        if max_drift < DELTA_CONV:
            converged_count += 1
            if convergence_tick is None:
                sustained = all(
                    max_drift_history[i] < DELTA_CONV
                    for i in range(max(0, tick - CONVERGENCE_WINDOW + 1), tick + 1)
                )
                if sustained and tick >= CONVERGENCE_WINDOW:
                    convergence_tick = tick - CONVERGENCE_WINDOW + 1
        else:
            converged_count = 0

    # Steady-state metrics
    ss_drift = np.mean(max_drift_history[-200:])
    ss_jitter = np.std(max_drift_history[-200:])

    # Communication savings
    comm_savings = messages_suppressed / max(total_exchange_opportunities, 1)

    return {
        "convergence_tick": convergence_tick,
        "steady_state_drift": float(ss_drift),
        "jitter": float(ss_jitter),
        "messages_sent": messages_sent,
        "messages_suppressed": messages_suppressed,
        "total_exchange_opportunities": total_exchange_opportunities,
        "comm_savings": float(comm_savings),
        "corrections_applied": corrections_applied,
    }


def main():
    edges = henneberg_type1(N_AGENTS)
    adj = build_adjacency(edges, N_AGENTS)

    print("=" * 100)
    print("EXPERIMENT 38: Deadband Sweep")
    print("=" * 100)
    print(f"Config: N={N_AGENTS}, Laman topology, latency={LATENCY}, gain={GAIN}")
    print(f"Deadbands: {DEADBANDS}")
    print(f"Trials: {TRIALS}, Ticks: {TICKS}")
    print()
    print(f"{'δ':>8} {'Conv Tick':>10} {'SS Drift':>10} {'Jitter':>10} {'Msgs Sent':>10} {'Suppressed':>11} {'Savings':>9} {'Conv':>5}")
    print("-" * 100)

    results = {}
    baseline_sent = None

    for deadband in DEADBANDS:
        trials = []
        for t in range(TRIALS):
            trial_seed = 42 + t * 1007 + int(deadband * 10000)
            result = run_trial(deadband, edges, adj, trial_seed)
            trials.append(result)

        conv_ticks = [tr["convergence_tick"] for tr in trials if tr["convergence_tick"] is not None]
        avg_conv = np.mean(conv_ticks) if conv_ticks else None
        converged_count = len(conv_ticks)
        avg_ss_drift = np.mean([tr["steady_state_drift"] for tr in trials])
        avg_jitter = np.mean([tr["jitter"] for tr in trials])
        avg_sent = np.mean([tr["messages_sent"] for tr in trials])
        avg_suppressed = np.mean([tr["messages_suppressed"] for tr in trials])
        avg_savings = np.mean([tr["comm_savings"] for tr in trials])

        if deadband == 0:
            baseline_sent = avg_sent

        savings_vs_baseline = 0.0
        if deadband > 0 and baseline_sent and baseline_sent > 0:
            savings_vs_baseline = 1.0 - (avg_sent / baseline_sent)

        key = f"{deadband:.2f}"
        results[key] = {
            "deadband": deadband,
            "avg_convergence_tick": float(avg_conv) if avg_conv is not None else None,
            "convergence_rate": converged_count / TRIALS,
            "avg_steady_state_drift": float(avg_ss_drift),
            "avg_jitter": float(avg_jitter),
            "avg_messages_sent": float(avg_sent),
            "avg_messages_suppressed": float(avg_suppressed),
            "avg_comm_savings": float(avg_savings),
            "savings_vs_baseline": float(savings_vs_baseline),
            "trials": trials,
        }

        conv_str = f"{avg_conv:.1f}" if avg_conv is not None else "NO CONV"
        print(f"{deadband:>8.2f} {conv_str:>10} {avg_ss_drift:>10.4f} {avg_jitter:>10.4f} {avg_sent:>10.0f} {avg_suppressed:>11.0f} {avg_savings:>8.1%} {converged_count:>4}/10")

    # Analysis
    print(f"\n{'=' * 100}")
    print(f"RESULTS SUMMARY")
    print(f"{'=' * 100}")

    # Find optimal: must converge, balance speed + savings
    best_deadband = None
    best_score = float('inf')
    for key, data in results.items():
        if data["avg_convergence_tick"] is not None:
            # Prefer: fast convergence + high savings + low drift
            score = (data["avg_convergence_tick"] / 500.0) + data["avg_steady_state_drift"] * 5.0 - data["savings_vs_baseline"] * 2.0
            if score < best_score:
                best_score = score
                best_deadband = data["deadband"]

    if best_deadband is not None:
        bd = results[f"{best_deadband:.2f}"]
        print(f"Optimal deadband: δ = {best_deadband}")
        print(f"  Convergence tick: {bd['avg_convergence_tick']:.1f}")
        print(f"  Convergence rate: {bd['convergence_rate']:.0%}")
        print(f"  Steady-state drift: {bd['avg_steady_state_drift']:.4f}")
        print(f"  Jitter: {bd['avg_jitter']:.4f}")
        print(f"  Messages sent: {bd['avg_messages_sent']:.0f}")
        print(f"  Communication savings: {bd['avg_comm_savings']:.1%}")
        print(f"  Savings vs baseline (δ=0): {bd['savings_vs_baseline']:.1%}")
    else:
        print("No deadband value achieved convergence!")

    # Hypothesis check
    print(f"\nHYPOTHESIS CHECK: δ=0.1 is optimal with ~80% correction reduction")
    d01 = results.get("0.10")
    if d01 and d01["avg_convergence_tick"] is not None:
        print(f"  δ=0.1 convergence: {d01['avg_convergence_tick']:.1f} ticks")
        print(f"  δ=0.1 messages sent: {d01['avg_messages_sent']:.0f}")
        print(f"  δ=0.1 comm savings: {d01['avg_comm_savings']:.1%}")
        print(f"  δ=0.1 savings vs baseline: {d01['savings_vs_baseline']:.1%}")

        if best_deadband is not None and abs(best_deadband - 0.1) < 0.05:
            print(f"  ✓ CONFIRMED — δ=0.1 is optimal")
        else:
            print(f"  ✗ REJECTED — optimal is δ={best_deadband}, not 0.1")

        if d01["savings_vs_baseline"] >= 0.7:
            print(f"  ✓ ~80% reduction: SUPPORTED ({d01['savings_vs_baseline']:.0%})")
        elif d01["savings_vs_baseline"] >= 0.5:
            print(f"  ~ 80% reduction: PARTIAL ({d01['savings_vs_baseline']:.0%})")
        else:
            print(f"  ✗ ~80% reduction: NOT SUPPORTED ({d01['savings_vs_baseline']:.0%})")
    else:
        print(f"  δ=0.1 did NOT converge — hypothesis strongly rejected")

    # Summary table
    print(f"\nDeadband analysis:")
    print(f"  {'δ':>6}  {'Status':>8}  {'Conv':>5}  {'SS Drift':>9}  {'Msgs':>8}  {'Savings':>8}  {'vs Base':>8}")
    for d in DEADBANDS:
        data = results[f"{d:.2f}"]
        status = "✓" if data["convergence_rate"] >= 0.8 else "✗"
        print(f"  {d:>6.2f}  {status:>8}  {data['convergence_rate']:>4.0%}  {data['avg_steady_state_drift']:>9.4f}  {data['avg_messages_sent']:>8.0f}  {data['avg_comm_savings']:>7.1%}  {data['savings_vs_baseline']:>7.1%}")

    # Save
    output = {
        "experiment": "experiment38_deadband_sweep",
        "description": "Deadband sweep for message suppression in Laman topology PTP consensus",
        "config": {
            "n_agents": N_AGENTS,
            "topology": "laman_henneberg_type1",
            "edges": edges,
            "latency": LATENCY,
            "gain": GAIN,
            "ticks": TICKS,
            "trials": TRIALS,
            "delta_convergence": DELTA_CONV,
            "convergence_window": CONVERGENCE_WINDOW,
            "deadbands_tested": DEADBANDS,
        },
        "results": results,
        "conclusion": {
            "optimal_deadband": best_deadband,
            "hypothesis_0_1_optimal": best_deadband is not None and abs(best_deadband - 0.1) < 0.05,
            "hypothesis_80pct_savings": d01 is not None and d01.get("savings_vs_baseline", 0) >= 0.7,
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

    out_path = out_dir / "experiment38_deadband.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, cls=NumpyEncoder)

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
