"""
Experiment 18: Load-Drift Coupling
HYPOTHESIS: Drift is independent of constraint load (metronome and checker are decoupled).

WHAT THIS CONSTRAINS: Whether constraint checking frequency affects convergence.
If drift is load-independent, the metronome/verifier architecture is correctly decoupled.

PROTOCOL:
N=10 agents, Laman topology
Vary constraint checking frequency per tick: 1, 10, 100, 1000, 10000 checks
Simulate load by adding dummy computation per tick proportional to checks
Run 500 ticks for each load level
Measure: convergence tick, max drift, wall-clock time per tick

Save to experiments/results/experiment18_load_drift.json
Print ASCII comparison table.
"""

import json
import math
import os
import time
from pathlib import Path

# --- Configuration ---
N_AGENTS = 10
TICKS = 500
DELTA = 5.0  # convergence threshold
TRUE_VALUE = 500.0
COUPLING_STRENGTH = 0.3  # neighbor averaging weight
CHECK_FREQUENCIES = [1, 10, 100, 1000, 10000]
NOISE_STD = 50.0  # measurement noise per tick

# --- Laman graph via Henneberg type-I ---
def build_laman_graph(n):
    edges = set()
    edges.add((0, 1)); edges.add((0, 2)); edges.add((1, 2))
    import random as _r
    _r.seed(42)
    for v in range(3, n):
        candidates = list(range(v))
        _r.shuffle(candidates)
        edges.add((v, candidates[0]))
        edges.add((v, candidates[1]))
    return list(edges)

def adjacency_from_edges(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj

def simulate(n, adj, ticks, check_freq, seed=12345):
    import random
    rng = random.Random(seed)
    
    # Initialize agents with random offsets from true value
    values = [TRUE_VALUE + rng.gauss(0, 100) for _ in range(n)]
    max_drifts = []
    convergence_tick = None
    
    tick_times = []
    
    for t in range(ticks):
        t0 = time.perf_counter()
        
        # Simulate load: dummy computation proportional to check frequency
        # This models constraint checking overhead
        load = 0.0
        for _ in range(check_freq * n):
            load += math.sqrt(rng.random() + 0.001)  # dummy work
        
        # Agent consensus update (the "metronome" — always runs at same rate)
        new_values = list(values)
        for i in range(n):
            neighbors = adj[i]
            if neighbors:
                neighbor_avg = sum(values[j] for j in neighbors) / len(neighbors)
                new_values[i] = values[i] * (1 - COUPLING_STRENGTH) + neighbor_avg * COUPLING_STRENGTH
            # Add small noise to simulate measurement uncertainty
            new_values[i] += rng.gauss(0, NOISE_STD * 0.01)
        
        values = new_values
        
        # Measure drift from true value
        drifts = [abs(v - TRUE_VALUE) for v in values]
        max_drift = max(drifts)
        max_drifts.append(max_drift)
        
        if convergence_tick is None and max_drift < DELTA:
            convergence_tick = t
        
        tick_time = time.perf_counter() - t0
        tick_times.append(tick_time)
    
    return {
        "convergence_tick": convergence_tick,
        "max_drift_final": max_drifts[-1],
        "max_drift_peak": max(max_drifts),
        "avg_drift_final": sum(abs(v - TRUE_VALUE) for v in values) / n,
        "tick_time_avg_ms": (sum(tick_times) / len(tick_times)) * 1000,
        "tick_time_total_s": sum(tick_times),
        "max_drifts_sample": max_drifts[::50],  # sample every 50 ticks
    }

def main():
    edges = build_laman_graph(N_AGENTS)
    adj = adjacency_from_edges(N_AGENTS, edges)
    
    results = {}
    
    print("=" * 80)
    print("EXPERIMENT 18: Load-Drift Coupling")
    print(f"N={N_AGENTS}, ticks={TICKS}, delta={DELTA}")
    print(f"Check frequencies: {CHECK_FREQUENCIES}")
    print(f"Graph: {len(edges)} edges (Laman)")
    print("=" * 80)
    
    for freq in CHECK_FREQUENCIES:
        print(f"\n  Running check_freq={freq}...", end=" ", flush=True)
        result = simulate(N_AGENTS, adj, TICKS, freq)
        results[str(freq)] = result
        conv = result["convergence_tick"]
        conv_str = str(conv) if conv is not None else "NOT REACHED"
        print(f"converged={conv_str}, max_drift={result['max_drift_final']:.4f}, "
              f"tick_time={result['tick_time_avg_ms']:.3f}ms")
    
    # Print ASCII table
    print("\n" + "=" * 80)
    print(f"{'Check Freq':>12} | {'Conv Tick':>10} | {'Max Drift':>10} | "
          f"{'Peak Drift':>10} | {'Avg Tick (ms)':>14} | {'Total (s)':>10}")
    print("-" * 80)
    
    drifts_by_freq = []
    conv_ticks = []
    
    for freq in CHECK_FREQUENCIES:
        r = results[str(freq)]
        conv = r["convergence_tick"]
        conv_str = str(conv) if conv is not None else "NO"
        print(f"{freq:>12} | {conv_str:>10} | {r['max_drift_final']:>10.4f} | "
              f"{r['max_drift_peak']:>10.4f} | {r['tick_time_avg_ms']:>14.3f} | "
              f"{r['tick_time_total_s']:>10.3f}")
        drifts_by_freq.append(r["max_drift_final"])
        if conv is not None:
            conv_ticks.append(conv)
    
    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    drift_range = max(drifts_by_freq) - min(drifts_by_freq)
    drift_mean = sum(drifts_by_freq) / len(drifts_by_freq)
    
    print(f"  Drift range across load levels: {drift_range:.6f}")
    print(f"  Mean final drift: {drift_mean:.6f}")
    print(f"  Drift std dev: {(sum((d - drift_mean)**2 for d in drifts_by_freq) / len(drifts_by_freq))**0.5:.6f}")
    
    if drift_range < 1.0:
        print(f"\n  VERDICT: SUPPORTED — drift variation ({drift_range:.6f}) is negligible across 10,000x load range")
    else:
        print(f"\n  VERDICT: WEAK — drift variation ({drift_range:.6f}) suggests some coupling")
    
    if conv_ticks and len(set(conv_ticks)) == 1:
        print(f"  Convergence ticks identical across all load levels: {conv_ticks[0]}")
    elif conv_ticks:
        print(f"  Convergence tick range: {min(conv_ticks)} - {max(conv_ticks)}")
    
    # Save results
    out = {
        "experiment": 18,
        "name": "load_drift_coupling",
        "hypothesis": "Drift is independent of constraint load (metronome and checker are decoupled)",
        "config": {
            "n_agents": N_AGENTS,
            "ticks": TICKS,
            "delta": DELTA,
            "check_frequencies": CHECK_FREQUENCIES,
            "coupling_strength": COUPLING_STRENGTH,
            "noise_std": NOISE_STD,
            "graph_type": "Laman",
            "n_edges": len(edges),
        },
        "results": results,
        "analysis": {
            "drift_range": drift_range,
            "drift_mean": drift_mean,
            "drift_std": (sum((d - drift_mean)**2 for d in drifts_by_freq) / len(drifts_by_freq))**0.5,
            "verdict": "SUPPORTED" if drift_range < 1.0 else "WEAK",
        },
    }
    
    out_path = Path(__file__).parent / "results" / "experiment18_load_drift.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Results saved to {out_path}")

if __name__ == "__main__":
    main()
