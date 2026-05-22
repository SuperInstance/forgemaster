#!/usr/bin/env python3
"""Experiment 35: Long-Term Stability — 100,000 ticks with sunset/inheritance cycles

HYPOTHESIS: Drift stays bounded over 100K ticks with zero accumulation.
  Inheritance is self-correcting — each sunset/inheritance event does not
  introduce permanent drift bias.

NOVEL ALTERNATIVE: If drift accumulates linearly or exponentially, the
  correction mechanism has a leak that must be identified.

PROTOCOL:
- N=10 agents, Laman topology (Henneberg type-I), latency=5 ticks
- Run for 100,000 ticks (simulating ~28 hours at 1kHz)
- Every 10,000 ticks: one random agent sunsets, a new agent joins (inheritance)
- 10 sunset/inheritance cycles over the full run
- Measure:
  - Drift over time (per-tick max, mean)
  - Sunset/inheritance overhead (drift spike magnitude and recovery time)
  - Long-term drift accumulation (trend line slope)
  - Correction magnitude over time (should stay bounded)
- Save to experiments/results/experiment35_long_term.json
"""

import json
import math
import os
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

# --- Configuration ---
N_AGENTS = 10
TOTAL_TICKS = 100_000
LATENCY = 5              # ticks of message latency
SUNSET_INTERVAL = 10_000  # every 10K ticks, sunset one agent
DELTA = 5.0              # convergence threshold
TRUE_VALUE = 100.0       # target calibration value
ALPHA = 0.3              # learning rate
SUNSET_EVENTS = TOTAL_TICKS // SUNSET_INTERVAL  # 10 events


def build_laman_graph(n, seed=42):
    """Henneberg type-I construction for a Laman graph (2N-3 edges)."""
    rng = random.Random(seed)
    edges = set()
    edges.add((0, 1)); edges.add((0, 2)); edges.add((1, 2))
    for v in range(3, n):
        candidates = list(range(v))
        pick = rng.sample(candidates, min(2, len(candidates)))
        for u in pick:
            edges.add((min(u, v), max(u, v)))
    # Ensure at least 2n-3 edges by adding more if needed
    target = 2 * n - 3
    all_possible = [(i, j) for i in range(n) for j in range(i+1, n)]
    rng.shuffle(all_possible)
    for e in all_possible:
        if len(edges) >= target:
            break
        edges.add(e)
    return list(edges)


def adjacency(n, edges):
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


class Agent:
    """Agent with estimate θ, message pipeline for latency simulation."""
    def __init__(self, idx, estimate=None):
        self.idx = idx
        self.estimate = estimate if estimate is not None else TRUE_VALUE + random.uniform(-20, 20)
        self.pipeline = []  # outgoing messages in transit: [(tick_sent, value)]
        self.incoming = []  # received messages this tick

    def send(self, tick):
        """Queue current estimate into the latency pipeline."""
        self.pipeline.append((tick + LATENCY, self.estimate))

    def receive(self, tick):
        """Pull all messages that have arrived by this tick."""
        arrived = [(t, v) for t, v in self.pipeline if t <= tick]
        self.pipeline = [(t, v) for t, v in self.pipeline if t > tick]
        return arrived

    def report(self):
        return self.estimate


def trimmed_mean(values, trim_frac=0.25):
    """Discard top/bottom 25%, average rest."""
    vals = sorted(values)
    n = len(vals)
    if n == 0:
        return TRUE_VALUE
    trim = max(1, int(n * trim_frac))
    trimmed = vals[trim:n - trim] if trim < n - trim else vals
    if not trimmed:
        return vals[n // 2]
    return sum(trimmed) / len(trimmed)


def run_experiment(seed=42):
    """Run the full 100K-tick experiment."""
    rng = random.Random(seed)
    edges = build_laman_graph(N_AGENTS, seed=seed)
    adj = adjacency(N_AGENTS, edges)

    # Initialize agents
    agents = {}
    for i in range(N_AGENTS):
        agents[i] = Agent(i, estimate=TRUE_VALUE + rng.uniform(-20, 20))

    # Tracking data structures
    # Sample every 100 ticks to keep data manageable
    SAMPLE_INTERVAL = 100
    drift_samples = []          # [(tick, max_drift, mean_drift)]
    correction_samples = []     # [(tick, mean_correction_magnitude)]

    # Per-sunset-event tracking
    sunset_events = []          # [(event_num, tick, agent_sunset, drift_before, drift_peak, recovery_ticks)]

    # Event queue: which ticks have a sunset
    sunset_ticks = list(range(SUNSET_INTERVAL, TOTAL_TICKS + 1, SUNSET_INTERVAL))
    sunset_idx = 0
    next_agent_id = N_AGENTS    # for assigning IDs to new agents

    # Pre-drift phase: let initial noise settle for first few ticks
    # (Not counted in the experiment — warm-up is part of the run)

    prev_estimates = {i: agents[i].estimate for i in agents}

    start_time = time.time()

    for tick in range(TOTAL_TICKS):
        # --- Sunset / Inheritance Event ---
        if sunset_idx < len(sunset_ticks) and tick == sunset_ticks[sunset_idx]:
            # Pick a random agent to sunset
            active = list(agents.keys())
            sunset_agent_idx = rng.choice(active)
            sunset_agent = agents[sunset_agent_idx]
            neighbors_of_sunset = adj[sunset_agent_idx]

            # Measure drift before sunset
            drifts_before = {idx: abs(a.estimate - TRUE_VALUE) for idx, a in agents.items()}
            max_drift_before = max(drifts_before.values())

            # Remove agent and its edges
            del agents[sunset_agent_idx]
            # Remove from adjacency
            for n in list(adj[sunset_agent_idx]):
                adj[n].discard(sunset_agent_idx)
            del adj[sunset_agent_idx]

            # Create new agent with inherited estimate
            neighbor_estimates = [agents[n].estimate for n in neighbors_of_sunset if n in agents]
            if neighbor_estimates:
                inherited = statistics.mean(neighbor_estimates)
            else:
                inherited = TRUE_VALUE + rng.uniform(-10, 10)

            new_id = next_agent_id
            next_agent_id += 1
            agents[new_id] = Agent(new_id, estimate=inherited)

            # Reconnect new agent: connect to 2 of the sunset agent's former neighbors
            # (Henneberg type-I style re-insertion)
            reconnect_targets = [n for n in neighbors_of_sunset if n in agents]
            if len(reconnect_targets) < 2:
                # Add random other agents
                others = [i for i in agents if i != new_id and i not in reconnect_targets]
                rng.shuffle(others)
                reconnect_targets.extend(others[:2 - len(reconnect_targets)])

            for t in reconnect_targets[:2]:
                adj[new_id].add(t)
                adj[t].add(new_id)
                edges.append((min(new_id, t), max(new_id, t)))

            # Ensure new agent has at least 2 connections (Laman min)
            if len(adj[new_id]) < 2:
                others = [i for i in agents if i != new_id and i not in adj[new_id]]
                rng.shuffle(others)
                for o in others[:2 - len(adj[new_id])]:
                    adj[new_id].add(o)
                    adj[o].add(new_id)

            # Track this sunset event (we'll fill in recovery data later)
            sunset_events.append({
                "event_num": sunset_idx + 1,
                "tick": tick,
                "sunset_agent": sunset_agent_idx,
                "new_agent": new_id,
                "drift_before": max_drift_before,
                "inherited_estimate": inherited,
                "drift_peak": None,
                "recovery_ticks": None,
            })
            sunset_idx += 1

        # --- Communication with latency ---
        # Each agent sends its current estimate
        for idx, agent in agents.items():
            agent.send(tick)

        # Each agent receives what's arrived
        received = {}
        for idx, agent in agents.items():
            arrived = agent.receive(tick)
            received[idx] = [v for _, v in arrived]

        # --- Update estimates ---
        new_estimates = {}
        corrections = {}
        for idx, agent in agents.items():
            neighbors = adj[idx]
            neighbor_vals = []
            for n in neighbors:
                if n in agents:
                    msgs = received.get(n, [])
                    if msgs:
                        neighbor_vals.extend(msgs if isinstance(msgs, list) else [msgs])

            if neighbor_vals:
                accepted = trimmed_mean(neighbor_vals)
            else:
                accepted = agent.estimate

            correction = ALPHA * (accepted - agent.estimate)
            new_est = agent.estimate + correction
            new_estimates[idx] = new_est
            corrections[idx] = abs(correction)

        # Apply updates synchronously
        for idx, agent in agents.items():
            agent.estimate = new_estimates[idx]

        # --- Sampling ---
        if tick % SAMPLE_INTERVAL == 0:
            drifts = {idx: abs(a.estimate - TRUE_VALUE) for idx, a in agents.items()}
            max_drift = max(drifts.values()) if drifts else 0
            mean_drift = statistics.mean(drifts.values()) if drifts else 0
            mean_correction = statistics.mean(corrections.values()) if corrections else 0

            drift_samples.append({
                "tick": tick,
                "max_drift": round(max_drift, 6),
                "mean_drift": round(mean_drift, 6),
            })
            correction_samples.append({
                "tick": tick,
                "mean_correction": round(mean_correction, 6),
            })

        # --- Update sunset recovery tracking ---
        for evt in sunset_events:
            if evt["drift_peak"] is None:
                drifts_now = {idx: abs(a.estimate - TRUE_VALUE) for idx, a in agents.items()}
                max_drift_now = max(drifts_now.values()) if drifts_now else 0
                if max_drift_now > evt["drift_before"] * 1.01:  # drift spiked
                    evt["drift_peak"] = max_drift_now
            if evt["recovery_ticks"] is None and evt["drift_peak"] is not None:
                drifts_now = {idx: abs(a.estimate - TRUE_VALUE) for idx, a in agents.items()}
                max_drift_now = max(drifts_now.values()) if drifts_now else 0
                if max_drift_now <= evt["drift_before"] * 1.05:  # recovered to within 5%
                    evt["recovery_ticks"] = tick - evt["tick"]

        # Progress indicator every 10K ticks
        if tick % 10_000 == 0:
            elapsed = time.time() - start_time
            print(f"  Tick {tick:>6d}/{TOTAL_TICKS} | elapsed: {elapsed:.1f}s")

    elapsed = time.time() - start_time

    # --- Compute long-term drift accumulation ---
    # Linear regression on max_drift over time
    ticks_arr = [s["tick"] for s in drift_samples]
    max_drifts_arr = [s["max_drift"] for s in drift_samples]
    n_samples = len(ticks_arr)
    if n_samples > 1:
        x_mean = sum(ticks_arr) / n_samples
        y_mean = sum(max_drifts_arr) / n_samples
        ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(ticks_arr, max_drifts_arr))
        ss_xx = sum((x - x_mean) ** 2 for x in ticks_arr)
        slope = ss_xy / ss_xx if ss_xx > 0 else 0
        intercept = y_mean - slope * x_mean
        # R-squared
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(ticks_arr, max_drifts_arr))
        ss_tot = sum((y - y_mean) ** 2 for y in max_drifts_arr)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    else:
        slope = intercept = r_squared = 0

    # --- Summary statistics ---
    final_drifts = {idx: abs(a.estimate - TRUE_VALUE) for idx, a in agents.items()}
    final_max_drift = max(final_drifts.values())
    final_mean_drift = statistics.mean(final_drifts.values())

    all_max_drifts = [s["max_drift"] for s in drift_samples]
    all_mean_corrections = [s["mean_correction"] for s in correction_samples]

    # Check if any sunset events didn't recover
    for evt in sunset_events:
        if evt["drift_peak"] is None:
            evt["drift_peak"] = evt["drift_before"]  # no spike detected
        if evt["recovery_ticks"] is None:
            evt["recovery_ticks"] = -1  # never recovered within experiment

    result = {
        "experiment": "experiment35_long_term_stability",
        "config": {
            "n_agents": N_AGENTS,
            "total_ticks": TOTAL_TICKS,
            "latency": LATENCY,
            "sunset_interval": SUNSET_INTERVAL,
            "sunset_events": SUNSET_EVENTS,
            "alpha": ALPHA,
            "delta": DELTA,
            "true_value": TRUE_VALUE,
            "seed": seed,
        },
        "summary": {
            "final_max_drift": round(final_max_drift, 6),
            "final_mean_drift": round(final_mean_drift, 6),
            "peak_drift_overall": round(max(all_max_drifts), 6),
            "min_drift_overall": round(min(all_max_drifts), 6),
            "drift_trend_slope": slope,           # positive = accumulation
            "drift_trend_intercept": intercept,
            "drift_trend_r_squared": r_squared,
            "accumulation_detected": abs(slope) > 1e-6,
            "mean_correction_magnitude": round(statistics.mean(all_mean_corrections), 6),
            "max_correction_magnitude": round(max(all_mean_corrections), 6),
            "correction_bounded": max(all_mean_corrections) < 1.0,
            "elapsed_seconds": round(elapsed, 2),
            "n_active_agents": len(agents),
        },
        "sunset_events": sunset_events,
        "drift_samples": drift_samples,
        "correction_samples": correction_samples,
        "hypothesis_confirmed": abs(slope) < 1e-6 and final_max_drift < DELTA * 2,
    }

    return result


def print_ascii_report(result):
    """Print a readable ASCII report."""
    cfg = result["config"]
    s = result["summary"]
    events = result["sunset_events"]

    print("\n" + "=" * 70)
    print("EXPERIMENT 35: Long-Term Stability (100K Ticks)")
    print("=" * 70)
    print(f"\nConfig: N={cfg['n_agents']} agents, latency={cfg['latency']} ticks, "
          f"{cfg['total_ticks']:,} total ticks")
    print(f"Sunset events: {cfg['sunset_events']} (every {cfg['sunset_interval']:,} ticks)")
    print(f"Elapsed: {s['elapsed_seconds']:.1f}s")

    print(f"\n--- Drift Summary ---")
    print(f"  Final max drift:     {s['final_max_drift']:.6f}")
    print(f"  Final mean drift:    {s['final_mean_drift']:.6f}")
    print(f"  Peak drift overall:  {s['peak_drift_overall']:.6f}")
    print(f"  Min drift overall:   {s['min_drift_overall']:.6f}")

    print(f"\n--- Drift Accumulation (Linear Regression) ---")
    print(f"  Slope:    {s['drift_trend_slope']:.10f} per tick")
    print(f"  Intercept: {s['drift_trend_intercept']:.6f}")
    print(f"  R²:       {s['drift_trend_r_squared']:.6f}")
    print(f"  Accumulation detected: {'YES ⚠️' if s['accumulation_detected'] else 'NO ✓'}")

    print(f"\n--- Correction Magnitude ---")
    print(f"  Mean correction: {s['mean_correction_magnitude']:.6f}")
    print(f"  Max correction:  {s['max_correction_magnitude']:.6f}")
    print(f"  Bounded (<1.0):  {'YES ✓' if s['correction_bounded'] else 'NO ⚠️'}")

    print(f"\n--- Sunset/Inheritance Events ---")
    print(f"  {'Event':>5} {'Tick':>7} {'Sunset':>8} {'New':>6} {'DriftBefore':>12} {'DriftPeak':>10} {'Recovery':>9}")
    print(f"  {'─'*5} {'─'*7} {'─'*8} {'─'*6} {'─'*12} {'─'*10} {'─'*9}")
    for evt in events:
        rec_str = f"{evt['recovery_ticks']}t" if evt['recovery_ticks'] >= 0 else "NEVER"
        print(f"  {evt['event_num']:>5} {evt['tick']:>7} "
              f"{'#'+str(evt['sunset_agent']):>8} {'#'+str(evt['new_agent']):>6} "
              f"{evt['drift_before']:>12.4f} {evt['drift_peak']:>10.4f} {rec_str:>9}")

    # Drift histogram at key points
    samples = result["drift_samples"]
    key_ticks = [0, 10000, 25000, 50000, 75000, 99999]
    print(f"\n--- Drift at Key Points ---")
    print(f"  {'Tick':>7} {'MaxDrift':>10} {'MeanDrift':>10}")
    print(f"  {'─'*7} {'─'*10} {'─'*10}")
    sample_map = {s["tick"]: s for s in samples}
    for kt in key_ticks:
        # Find closest sample
        closest = min(samples, key=lambda s: abs(s["tick"] - kt))
        print(f"  {closest['tick']:>7} {closest['max_drift']:>10.6f} {closest['mean_drift']:>10.6f}")

    print(f"\n--- HYPOTHESIS ---")
    print(f"  Drift stays bounded over 100K ticks:  {'CONFIRMED ✓' if not s['accumulation_detected'] else 'REJECTED ⚠️'}")
    print(f"  Inheritance is self-correcting:        {'CONFIRMED ✓' if result['hypothesis_confirmed'] else 'NEEDS REVIEW'}")
    print(f"  Correction magnitude stays bounded:    {'CONFIRMED ✓' if s['correction_bounded'] else 'REJECTED ⚠️'}")
    print("=" * 70)


if __name__ == "__main__":
    print("Running Experiment 35: Long-Term Stability...")
    result = run_experiment(seed=42)
    print_ascii_report(result)

    # Save results
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "experiment35_long_term.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to {out_path}")
