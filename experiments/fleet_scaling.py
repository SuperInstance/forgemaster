#!/usr/bin/env python3
"""
Experiment 10: Fleet Scaling Characteristics
Questions:
1. How does convergence time scale with N? (hypothesis: O(log N) for Laman)
2. What's the max fleet size before drift exceeds δ?
3. How does communication cost (messages/tick) scale with N?
Protocol:
For N in [3, 5, 10, 20, 50, 100]:
  1. Create Laman topology (2N-3 edges)
  2. Add 20% small-world long-range edges
  3. Run 500 ticks
  4. Measure:
     - Rounds to convergence (max drift < 0.01)
     - Max drift at tick 500
     - Messages per tick (deadband filter)
     - Wall clock time
     - Memory usage
"""
import json
import random
import time
import resource
import tracemalloc
import sys
from fractions import Fraction

random.seed(42)

# ============================================================
# Topology builders
# ============================================================

def henneberg_type1(n):
    """Build minimal Laman graph via Henneberg type-I construction."""
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]  # K3
    for v in range(3, n):
        targets = random.sample(range(v), min(2, v))
        while len(targets) < 2:
            targets.append(random.randint(0, v - 1))
        edges.append((v, targets[0]))
        edges.append((v, targets[1]))
    return edges


def add_smallworld_edges(edges, n, frac=0.20):
    """Add long-range shortcut edges (small-world rewiring model)."""
    existing = set(tuple(sorted(e)) for e in edges)
    max_new = max(1, int(len(edges) * frac))
    new_edges = []
    attempts = 0
    while len(new_edges) < max_new and attempts < max_new * 20:
        u, v = random.sample(range(n), 2)
        key = tuple(sorted((u, v)))
        if key not in existing:
            existing.add(key)
            new_edges.append((u, v))
        attempts += 1
    return edges + new_edges


def build_adjacency(edges, n):
    """Build adjacency list from edge list."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


# ============================================================
# Simulation engine using Fraction arithmetic
# ============================================================

def simulate(n, edges, max_ticks=500, convergence_threshold=Fraction(1, 100), deadband=Fraction(1, 1000)):
    """
    Simulate distributed consensus on a fleet topology.
    Each node holds a Fraction state value.
    On each tick, nodes exchange values with neighbors (deadband-filtered).
    Convergence = max pairwise drift < threshold.
    
    Returns dict of measurements.
    """
    adj = build_adjacency(edges, n)
    
    # Initialize node states: spread them out to create initial drift
    # Use Fraction for exact arithmetic
    states = [Fraction(i * 100, n) for i in range(n)]
    
    convergence_tick = None
    total_messages = 0
    max_drifts = []
    
    tracemalloc.start()
    t0 = time.time()
    
    for tick in range(1, max_ticks + 1):
        tick_messages = 0
        new_states = list(states)
        
        for node in range(n):
            neighbors = adj[node]
            if not neighbors:
                continue
            # Gather neighbor values via deadband-filtered messages
            received = []
            for nb in neighbors:
                # Deadband: only send if drift > deadband
                drift = abs(states[nb] - states[node])
                if drift > deadband:
                    received.append(states[nb])
                    tick_messages += 1
            
            if received:
                # Average with received neighbors
                total = states[node] + sum(received)
                count = 1 + len(received)
                new_states[node] = total / count
        
        states = new_states
        total_messages += tick_messages
        
        # Compute max pairwise drift
        max_drift = Fraction(0)
        min_val = min(states)
        max_val = max(states)
        max_drift = max_val - min_val
        max_drifts.append(float(max_drift))
        
        if max_drift < convergence_threshold and convergence_tick is None:
            convergence_tick = tick
    
    wall_time = time.time() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    final_max_drift = max_drifts[-1] if max_drifts else 0
    avg_messages_per_tick = total_messages / max_ticks if max_ticks > 0 else 0
    
    return {
        "n": n,
        "laman_edges": 2 * n - 3,
        "total_edges": len(edges),
        "smallworld_edges": len(edges) - (2 * n - 3),
        "convergence_tick": convergence_tick,
        "max_drift_final": round(final_max_drift, 8),
        "avg_messages_per_tick": round(avg_messages_per_tick, 2),
        "total_messages": total_messages,
        "wall_time_s": round(wall_time, 4),
        "peak_memory_kb": round(peak_mem / 1024, 2),
    }


# ============================================================
# Main experiment
# ============================================================

def main():
    fleet_sizes = [3, 5, 10, 20, 50, 100]
    results = []
    
    print("=" * 90)
    print("EXPERIMENT 10: FLEET SCALING CHARACTERISTICS")
    print("=" * 90)
    
    for n in fleet_sizes:
        print(f"\n--- N = {n} ---")
        
        # 1. Build Laman topology
        laman_edges = henneberg_type1(n)
        assert len(laman_edges) == 2 * n - 3, f"Laman edge count mismatch: {len(laman_edges)} != {2*n-3}"
        
        # 2. Add small-world edges
        edges = add_smallworld_edges(laman_edges, n, frac=0.20)
        print(f"  Edges: {len(laman_edges)} Laman + {len(edges) - len(laman_edges)} small-world = {len(edges)} total")
        
        # 3. Run simulation
        result = simulate(n, edges, max_ticks=500)
        results.append(result)
        
        conv = result["convergence_tick"]
        conv_str = str(conv) if conv else "NOT CONVERGED"
        print(f"  Convergence: tick {conv_str}")
        print(f"  Max drift (final): {result['max_drift_final']:.8f}")
        print(f"  Avg msgs/tick: {result['avg_messages_per_tick']}")
        print(f"  Wall time: {result['wall_time_s']:.4f}s")
        print(f"  Peak memory: {result['peak_memory_kb']:.1f} KB")
    
    # ============================================================
    # ASCII Results Table
    # ============================================================
    print("\n" + "=" * 90)
    print("RESULTS TABLE")
    print("=" * 90)
    header = f"{'N':>5} {'LamanE':>7} {'SW-Add':>7} {'TotalE':>7} {'ConvTick':>9} {'MaxDrift':>12} {'Msgs/Tick':>10} {'Wall(s)':>9} {'Mem(KB)':>9}"
    print(header)
    print("-" * len(header))
    for r in results:
        conv = str(r["convergence_tick"]) if r["convergence_tick"] else "NC"
        print(f"{r['n']:>5} {r['laman_edges']:>7} {r['smallworld_edges']:>7} {r['total_edges']:>7} {conv:>9} {r['max_drift_final']:>12.8f} {r['avg_messages_per_tick']:>10.2f} {r['wall_time_s']:>9.4f} {r['peak_memory_kb']:>9.1f}")
    
    # ============================================================
    # Scaling analysis
    # ============================================================
    print("\n" + "=" * 90)
    print("SCALING ANALYSIS")
    print("=" * 90)
    
    converged = [r for r in results if r["convergence_tick"] is not None]
    if len(converged) >= 2:
        print("\nConvergence ticks vs N:")
        for r in converged:
            import math
            log_n = math.log2(r["n"]) if r["n"] > 0 else 0
            print(f"  N={r['n']:>4}  conv={r['convergence_tick']:>4}  log2(N)={log_n:.2f}  ratio={r['convergence_tick']/log_n:.2f}" if log_n > 0 else f"  N={r['n']:>4}  conv={r['convergence_tick']:>4}")
        
        # Simple linear regression on log scale
        if len(converged) >= 3:
            xs = [math.log2(r["n"]) for r in converged]
            ys = [r["convergence_tick"] for r in converged]
            n_pts = len(xs)
            sum_x = sum(xs)
            sum_y = sum(ys)
            sum_xy = sum(x * y for x, y in zip(xs, ys))
            sum_xx = sum(x * x for x in xs)
            denom = n_pts * sum_xx - sum_x * sum_x
            if denom != 0:
                slope = (n_pts * sum_xy - sum_x * sum_y) / denom
                intercept = (sum_y - slope * sum_x) / n_pts
                print(f"\n  Linear fit: conv ≈ {slope:.2f} * log2(N) + {intercept:.2f}")
                print(f"  Scaling: O(N^{slope / (sum_y / n_pts) * (sum_x / n_pts):.2f}) [rough exponent from log-log]")
    
    print("\nMessages/tick scaling:")
    for r in results:
        import math
        log_n = math.log2(r["n"]) if r["n"] > 1 else 0
        print(f"  N={r['n']:>4}  msgs/tick={r['avg_messages_per_tick']:>10.2f}  edges={r['total_edges']:>5}")
    
    print("\nMemory scaling:")
    for r in results:
        print(f"  N={r['n']:>4}  mem={r['peak_memory_kb']:>10.1f} KB  ratio(N)/N={r['peak_memory_kb']/r['n']:.2f}")
    
    # Save JSON
    output = {
        "experiment": "fleet_scaling",
        "description": "Fleet scaling characteristics: convergence, messages, memory vs fleet size N",
        "parameters": {
            "fleet_sizes": fleet_sizes,
            "max_ticks": 500,
            "convergence_threshold": 0.01,
            "deadband": 0.001,
            "smallworld_fraction": 0.20,
            "arithmetic": "Fraction (exact)",
        },
        "results": results,
        "scaling_analysis": {
            "converged_fleet_sizes": [r["n"] for r in converged],
            "convergence_ticks": [r["convergence_tick"] for r in converged],
        }
    }
    
    outpath = "experiments/results/experiment10_scaling.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {outpath}")


if __name__ == "__main__":
    main()
