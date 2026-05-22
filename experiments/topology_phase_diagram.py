#!/usr/bin/env python3
"""Experiment 30: Topology Phase Diagram.

Map the full phase space of (connectivity, latency, agents) for PTP sync.

Parameters swept:
  N (agents):        3, 5, 10, 20, 50
  L (latency):       0, 1, 2, 5, 10, 20, 50
  density:           0.1, 0.3, 0.5, 0.7, 1.0 (fraction of complete graph edges)

For each (N, L, density):
  - Generate random connected graph with target edge density
  - Compute λ₂ (algebraic connectivity)
  - Run PTP sync for 500 ticks
  - Measure: convergence, steady-state drift, convergence tick

Total: 5 × 7 × 5 = 175 configurations, 5 trials each = 875 runs

Hypothesis: convergence requires λ₂ > 0 (connected) AND PTP correction. No other requirements.
"""
import json
import math
import os
import random
import time
from collections import defaultdict, deque

import numpy as np
from scipy.linalg import eigh

SEED = 42
N_TRIALS = 5
MAX_TICKS = 500
WARMUP = 100
CONVERGENCE_THRESHOLD = 0.1
DELTA = 0.0625
EPSILON = 0.01

N_VALUES = [3, 5, 10, 20, 50]
L_VALUES = [0, 1, 2, 5, 10, 20, 50]
DENSITY_VALUES = [0.1, 0.3, 0.5, 0.7, 1.0]


# ── Graph generation ──────────────────────────────────────────────

def generate_random_connected_graph(n, density, rng):
    """Generate a random connected graph with given edge density.
    
    density = fraction of the complete graph's edges to include.
    First builds a spanning tree, then adds random edges to reach target density.
    """
    max_edges = n * (n - 1) // 2
    target_edges = max(n - 1, int(density * max_edges))
    target_edges = min(target_edges, max_edges)

    edges = set()

    # Spanning tree (random) to guarantee connectivity
    nodes = list(range(n))
    rng.shuffle(nodes)
    for i in range(1, n):
        j = rng.randint(0, i - 1)
        edges.add((min(nodes[i], nodes[j]), max(nodes[i], nodes[j])))

    # Add random edges to reach target
    attempts = 0
    while len(edges) < target_edges and attempts < target_edges * 20:
        i = rng.randint(0, n - 1)
        j = rng.randint(0, n - 1)
        if i != j:
            edges.add((min(i, j), max(i, j)))
        attempts += 1

    return list(edges)


def compute_algebraic_connectivity(n, edges):
    """Compute λ₂ (algebraic connectivity) using scipy."""
    if n < 2:
        return 0.0
    adj = np.zeros((n, n))
    for u, v in edges:
        adj[u, v] = 1.0
        adj[v, u] = 1.0
    degree = np.sum(adj, axis=1)
    L = np.diag(degree) - adj
    eigenvalues = eigh(L, eigvals_only=True)
    eigenvalues.sort()
    # λ₁ should be ~0, λ₂ is algebraic connectivity
    lambda2 = eigenvalues[1] if len(eigenvalues) > 1 else 0.0
    lambda_n = eigenvalues[-1]
    return float(lambda2), float(lambda_n), [float(e) for e in eigenvalues]


# ── PTP Agent ─────────────────────────────────────────────────────

class PTPAgent:
    def __init__(self, idx, n_agents):
        self.idx = idx
        self.local_clock = 0.0
        # Each agent has a unique drift rate
        self.drift_rate = EPSILON * (idx - (n_agents - 1) / 2.0) / (n_agents * 2.0)
        self.neighbors = []
        self.inbox = deque()
        self.total_correction = 0.0

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def broadcast(self, current_tick, latency):
        reported = self.local_clock
        for neighbor, _ in self.neighbors:
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
        if not reports:
            return
        offset_estimates = []
        for sender_idx, reported_clock, sent_tick in reports:
            lat = current_tick - sent_tick
            neighbor_now = reported_clock + lat
            offset = neighbor_now - self.local_clock
            offset_estimates.append(offset)

        avg_offset = sum(offset_estimates) / len(offset_estimates)
        correction = 0.5 * avg_offset
        correction = max(-2.0, min(2.0, correction))
        self.local_clock += correction
        self.total_correction += abs(correction)


# ── Trial runner ──────────────────────────────────────────────────

def run_trial(n, edges, latency, trial_seed):
    rng = random.Random(trial_seed)
    agents = [PTPAgent(i, n) for i in range(n)]
    for i, j in edges:
        agents[i].neighbors.append((agents[j], 1.0))
        agents[j].neighbors.append((agents[i], 1.0))

    drift_log = []
    convergence_tick = None
    consecutive_stable = 0

    for tick in range(1, MAX_TICKS + 1):
        for a in agents:
            a.tick(tick)
        for a in agents:
            a.broadcast(tick, latency)
        for a in agents:
            reports = a.receive(tick)
            a.correct_ptp(reports, tick)

        ideal = float(tick)
        drifts = [abs(a.local_clock - ideal) for a in agents]
        max_drift = max(drifts)
        drift_log.append(max_drift)

        if tick > WARMUP:
            if max_drift < CONVERGENCE_THRESHOLD:
                consecutive_stable += 1
                if consecutive_stable >= 20 and convergence_tick is None:
                    convergence_tick = tick - 19
            else:
                consecutive_stable = 0

    post_warmup = drift_log[WARMUP:]
    ss_window = post_warmup[-200:] if len(post_warmup) >= 200 else post_warmup
    steady_state_drift = max(ss_window)
    mean_drift_ss = sum(ss_window) / len(ss_window)
    peak_drift = max(drift_log)

    return {
        "trial_seed": trial_seed,
        "convergence_tick": convergence_tick,
        "converged": convergence_tick is not None,
        "steady_state_max_drift": round(steady_state_drift, 6),
        "steady_state_mean_drift": round(mean_drift_ss, 6),
        "peak_drift": round(peak_drift, 6),
    }


# ── Main experiment ───────────────────────────────────────────────

def run_experiment():
    start_time = time.time()
    results = []
    phase_map = {}  # (N, L, density) -> summary

    total_configs = len(N_VALUES) * len(L_VALUES) * len(DENSITY_VALUES)
    config_idx = 0

    print("=" * 110)
    print("EXPERIMENT 30: Topology Phase Diagram")
    print(f"N ∈ {N_VALUES}  L ∈ {L_VALUES}  density ∈ {DENSITY_VALUES}")
    print(f"Total: {total_configs} configurations × {N_TRIALS} trials = {total_configs * N_TRIALS} runs")
    print(f"Hypothesis: convergence requires λ₂ > 0 (connected) AND PTP correction")
    print("=" * 110)
    print(f"{'N':>4} {'L':>4} {'dens':>6} {'|E|':>5} {'λ₂':>10} {'Conv%':>7} {'SSDrift':>10} {'ConvTick':>9} {'Phase':>8}")
    print("-" * 110)

    for n in N_VALUES:
        for L in L_VALUES:
            for density in DENSITY_VALUES:
                config_idx += 1

                # Generate graph
                graph_rng = random.Random(SEED + config_idx * 1000)
                edges = generate_random_connected_graph(n, density, graph_rng)
                n_edges = len(edges)
                max_edges = n * (n - 1) // 2
                actual_density = n_edges / max_edges if max_edges > 0 else 1.0

                # Compute spectral properties
                lambda2, lambda_n, all_eigs = compute_algebraic_connectivity(n, edges)

                # Run trials
                trials = []
                for t in range(N_TRIALS):
                    trial_seed = SEED + config_idx * 10000 + t * 100
                    tr = run_trial(n, edges, L, trial_seed)
                    trials.append(tr)

                # Aggregate
                conv_count = sum(1 for tr in trials if tr["converged"])
                conv_rate = conv_count / N_TRIALS
                avg_ss_drift = sum(tr["steady_state_max_drift"] for tr in trials) / N_TRIALS
                avg_ss_mean = sum(tr["steady_state_mean_drift"] for tr in trials) / N_TRIALS
                avg_peak = sum(tr["peak_drift"] for tr in trials) / N_TRIALS
                conv_ticks = [tr["convergence_tick"] for tr in trials if tr["convergence_tick"] is not None]
                avg_conv_tick = round(sum(conv_ticks) / len(conv_ticks), 1) if conv_ticks else None

                # Phase classification
                if conv_rate >= 0.8:
                    if avg_ss_drift < DELTA:
                        phase = "STABLE"
                    else:
                        phase = "CONV-HI"
                elif conv_rate >= 0.4:
                    phase = "MARGINAL"
                else:
                    phase = "DIVERGE"

                connected = lambda2 > 1e-6

                print(f"{n:>4} {L:>4} {density:>6.1f} {n_edges:>5} {lambda2:>10.4f} {conv_rate:>6.0%} "
                      f"{avg_ss_drift:>10.4f} {str(avg_conv_tick):>9} {phase:>8}")

                entry = {
                    "N": n,
                    "latency": L,
                    "density": density,
                    "actual_density": round(actual_density, 4),
                    "n_edges": n_edges,
                    "max_edges": max_edges,
                    "lambda2": round(lambda2, 6),
                    "lambda_n": round(lambda_n, 6),
                    "connected": connected,
                    "convergence_rate": conv_rate,
                    "avg_ss_max_drift": round(avg_ss_drift, 6),
                    "avg_ss_mean_drift": round(avg_ss_mean, 6),
                    "avg_peak_drift": round(avg_peak, 6),
                    "avg_convergence_tick": avg_conv_tick,
                    "phase": phase,
                    "trials": trials,
                }
                results.append(entry)
                phase_map[(n, L, density)] = phase

    elapsed = time.time() - start_time

    # ── Phase analysis ──────────────────────────────────────────

    print("\n" + "=" * 110)
    print("PHASE ANALYSIS")
    print("=" * 110)

    # Phase distribution
    phase_counts = defaultdict(int)
    for entry in results:
        phase_counts[entry["phase"]] += 1
    print(f"\nPhase distribution ({total_configs} configurations):")
    for phase in ["STABLE", "CONV-HI", "MARGINAL", "DIVERGE"]:
        print(f"  {phase:>10}: {phase_counts[phase]:>4} ({phase_counts[phase]/total_configs*100:.1f}%)")

    # Phase transition boundaries
    print("\nPhase transition boundaries:")
    for n in N_VALUES:
        for L in L_VALUES:
            phases_for_nL = []
            for density in DENSITY_VALUES:
                key = (n, L, density)
                phases_for_nL.append(phase_map.get(key, "UNKNOWN"))
            # Check if there's a transition
            unique = set(phases_for_nL)
            if len(unique) > 1:
                print(f"  N={n:>2}, L={L:>2}: {' → '.join(phases_for_nL)}")

    # Connectivity vs convergence
    print("\nConnectivity analysis:")
    connected_converged = sum(1 for e in results if e["connected"] and e["convergence_rate"] >= 0.8)
    connected_total = sum(1 for e in results if e["connected"])
    disconnected_converged = sum(1 for e in results if not e["connected"] and e["convergence_rate"] >= 0.8)
    disconnected_total = sum(1 for e in results if not e["connected"])
    print(f"  Connected (λ₂ > 0):     {connected_total} configs, {connected_converged} converged ({connected_converged/connected_total*100:.1f}%)" if connected_total else "  No connected configs")
    print(f"  Disconnected (λ₂ ≈ 0):  {disconnected_total} configs, {disconnected_converged} converged ({disconnected_converged/disconnected_total*100:.1f}%)" if disconnected_total else "  No disconnected configs")

    # λ₂ threshold analysis
    lambda2_values = [(e["lambda2"], e["convergence_rate"]) for e in results]
    lambda2_values.sort()
    min_conv_lambda2 = min((lv for lv, cr in lambda2_values if cr >= 0.8), default=0)
    max_div_lambda2 = max((lv for lv, cr in lambda2_values if cr < 0.4), default=0)
    print(f"\n  Min λ₂ for convergence: {min_conv_lambda2:.6f}")
    print(f"  Max λ₂ without convergence: {max_div_lambda2:.6f}")

    # Latency impact
    print("\nLatency impact on convergence:")
    for L in L_VALUES:
        configs_at_L = [e for e in results if e["latency"] == L]
        conv_rate = sum(e["convergence_rate"] for e in configs_at_L) / len(configs_at_L)
        avg_drift = sum(e["avg_ss_max_drift"] for e in configs_at_L) / len(configs_at_L)
        print(f"  L={L:>3}: avg conv rate = {conv_rate:.1%}, avg SS drift = {avg_drift:.4f}")

    # Agent count impact
    print("\nAgent count impact on convergence:")
    for n in N_VALUES:
        configs_at_n = [e for e in results if e["N"] == n]
        conv_rate = sum(e["convergence_rate"] for e in configs_at_n) / len(configs_at_n)
        avg_drift = sum(e["avg_ss_max_drift"] for e in configs_at_n) / len(configs_at_n)
        print(f"  N={n:>3}: avg conv rate = {conv_rate:.1%}, avg SS drift = {avg_drift:.4f}")

    # Density impact
    print("\nDensity impact on convergence:")
    for d in DENSITY_VALUES:
        configs_at_d = [e for e in results if e["density"] == d]
        conv_rate = sum(e["convergence_rate"] for e in configs_at_d) / len(configs_at_d)
        avg_drift = sum(e["avg_ss_max_drift"] for e in configs_at_d) / len(configs_at_d)
        print(f"  d={d:.1f}: avg conv rate = {conv_rate:.1%}, avg SS drift = {avg_drift:.4f}")

    # ── Hypothesis evaluation ───────────────────────────────────

    print("\n" + "=" * 110)
    print("HYPOTHESIS EVALUATION")
    print("=" * 110)
    print(f"Hypothesis: convergence requires λ₂ > 0 (connected) AND PTP correction. No other requirements.")

    # Check: does every connected config converge?
    all_connected_converge = all(e["convergence_rate"] >= 0.8 for e in results if e["connected"])
    print(f"\n  Every connected (λ₂>0) config converges? {all_connected_converge}")

    # Counter-examples
    counter = [e for e in results if e["connected"] and e["convergence_rate"] < 0.8]
    if counter:
        print(f"  Counter-examples (connected but didn't converge): {len(counter)}")
        for e in counter[:10]:
            print(f"    N={e['N']}, L={e['latency']}, d={e['density']}, λ₂={e['lambda2']:.4f}, "
                  f"conv={e['convergence_rate']:.0%}, drift={e['avg_ss_max_drift']:.4f}")

    # Check: does any disconnected config converge?
    false_positive = [e for e in results if not e["connected"] and e["convergence_rate"] >= 0.8]
    print(f"\n  Disconnected configs that still converged? {len(false_positive)}")
    for e in false_positive[:5]:
        print(f"    N={e['N']}, L={e['latency']}, d={e['density']}, λ₂={e['lambda2']:.6f}, "
              f"conv={e['convergence_rate']:.0%}")

    # Is λ₂ the only requirement? Check if high latency or low density ever prevents convergence despite λ₂>0
    high_latency_fail = [e for e in results if e["connected"] and e["latency"] >= 20 and e["convergence_rate"] < 0.4]
    print(f"\n  Connected configs with high latency (≥20) that diverge? {len(high_latency_fail)}")
    for e in high_latency_fail[:5]:
        print(f"    N={e['N']}, L={e['latency']}, d={e['density']}, λ₂={e['lambda2']:.4f}, "
              f"conv={e['convergence_rate']:.0%}, drift={e['avg_ss_max_drift']:.4f}")

    # Final verdict
    if all_connected_converge and not false_positive:
        print(f"\n  ✓ HYPOTHESIS CONFIRMED: λ₂ > 0 is both necessary AND sufficient for convergence")
    elif all_connected_converge and false_positive:
        print(f"\n  ⚠ HYPOTHESIS PARTIALLY CONFIRMED: λ₂ > 0 is sufficient but not necessary")
    elif not all_connected_converge and not false_positive:
        print(f"\n  ✗ HYPOTHESIS REJECTED: λ₂ > 0 is necessary but not sufficient")
        print(f"    Other factors (latency, density) affect convergence")
    else:
        print(f"\n  ✗ HYPOTHESIS REJECTED: Convergence relationship is more complex")

    print(f"\nElapsed: {elapsed:.1f}s")

    # ── Save results ────────────────────────────────────────────

    output = {
        "experiment": 30,
        "title": "Topology Phase Diagram",
        "description": "Map full phase space of (N, latency, density) for PTP sync",
        "hypothesis": "convergence requires λ₂ > 0 (connected) AND PTP correction. No other requirements.",
        "parameters": {
            "N_values": N_VALUES,
            "latency_values": L_VALUES,
            "density_values": DENSITY_VALUES,
            "n_trials": N_TRIALS,
            "max_ticks": MAX_TICKS,
            "warmup": WARMUP,
            "convergence_threshold": CONVERGENCE_THRESHOLD,
            "delta": DELTA,
        },
        "phase_distribution": dict(phase_counts),
        "elapsed_seconds": round(elapsed, 1),
        "configurations": total_configs,
        "total_runs": total_configs * N_TRIALS,
        "results": results,
        "phase_map_3d": {f"N{n}_L{L}_d{d}": phase for (n, L, d), phase in phase_map.items()},
    }

    os.makedirs("experiments/results", exist_ok=True)
    output_path = "experiments/results/experiment30_phase_diagram.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return output


if __name__ == "__main__":
    run_experiment()
