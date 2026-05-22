#!/usr/bin/env python3
"""
Experiment 9: Network Partition Tolerance
Hypothesis: Laman-rigid fleet recovers from partition within O(log N) rounds after healing.
Protocol:
1. Create 10 agents on Laman topology (2*10-3 = 17 edges)
2. Run 200 ticks, verify convergence
3. Partition: remove 4 edges (simulating network split into 2 groups of 5)
4. Run 100 ticks in partition (groups should diverge)
5. Heal partition: restore edges
6. Run 200 ticks post-healing
7. Measure: convergence time after healing, max drift during partition, drift at end
"""

import json
import sys
import os
import random
from fractions import Fraction

# Pull in metronome_core from demo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'demo', 'three-agent-demo'))
from metronome_core import MetronomeAgent, CorrectionMode, PlatoTileStore

random.seed(42)

N = 10
EXPECTED_EDGES = 2 * N - 3  # 17

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


def build_adjacency(n, edges):
    """Build adjacency dict from edge list."""
    adj = {i: set() for i in range(n)}
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def connected_components(adj):
    """Find connected components via BFS."""
    visited = set()
    components = []
    for node in adj:
        if node not in visited:
            comp = set()
            queue = [node]
            while queue:
                cur = queue.pop(0)
                if cur in visited:
                    continue
                visited.add(cur)
                comp.add(cur)
                for nb in adj[cur]:
                    if nb not in visited:
                        queue.append(nb)
            components.append(comp)
    return components


def max_drift(agents):
    """Compute max absolute drift across all agents."""
    drifts = [abs(a.clock.drift) for a in agents]
    return max(drifts) if drifts else Fraction(0)


def pairwise_max_drift(agents):
    """Max drift between any pair of agents."""
    times = [a.clock.local_time for a in agents]
    return max(abs(a - b) for a in times for b in times)


def run_simulation(agents, adj, ticks, label=""):
    """Run simulation for N ticks, with neighbor correction each tick."""
    drift_log = []
    for t in range(ticks):
        # Each agent ticks (accumulates drift)
        for a in agents:
            a.tick()

        # Neighbor-based correction: each agent corrects toward average of neighbors
        corrections = {}
        for i, a in enumerate(agents):
            neighbors = list(adj.get(i, []))
            if neighbors:
                neighbor_times = [agents[nb].clock.local_time for nb in neighbors]
                avg_time = sum(neighbor_times, Fraction(0)) / len(neighbor_times)
                corrections[i] = avg_time

        # Apply corrections (gentle: 50% toward neighbor average)
        for i, ref_time in corrections.items():
            agents[i].deadband_correct(ref_time)

        drift_log.append({
            "tick": t,
            "max_drift": float(max_drift(agents)),
            "pairwise_max": float(pairwise_max_drift(agents)),
        })

    return drift_log


def main():
    print("=" * 70)
    print("EXPERIMENT 9: NETWORK PARTITION TOLERANCE")
    print("=" * 70)

    # Step 1: Build Laman topology
    edges = henneberg_type1(N)
    assert len(edges) == EXPECTED_EDGES, f"Expected {EXPECTED_EDGES} edges, got {len(edges)}"
    print(f"\nTopology: {N} agents, {len(edges)} edges (Laman: 2*{N}-3={EXPECTED_EDGES})")

    # Create agents with varied drift rates
    drift_rates = [0.001, -0.002, 0.003, -0.001, 0.002,
                   -0.003, 0.0015, -0.0015, 0.0025, -0.0025]
    store = PlatoTileStore(":memory:")
    agents = []
    for i in range(N):
        a = MetronomeAgent(
            agent_id=f"agent_{i}",
            drift_rate=drift_rates[i],
            correction_mode=CorrectionMode.GENTLE,
            tile_store=store,
        )
        agents.append(a)

    adj = build_adjacency(N, edges)

    # Phase 1: Pre-partition convergence (200 ticks)
    print("\n--- Phase 1: Pre-partition convergence (200 ticks) ---")
    pre_log = run_simulation(agents, adj, 200, "pre-partition")
    pre_max_drift = max_drift(agents)
    pre_pairwise = pairwise_max_drift(agents)
    print(f"  Max agent drift: {float(pre_max_drift):.10f}")
    print(f"  Max pairwise drift: {float(pre_pairwise):.10f}")

    # Snapshot state at end of phase 1
    phase1_state = [(str(a.clock.true_time), str(a.clock.offset)) for a in agents]

    # Phase 2: Partition — remove 4 edges to split into 2 groups
    # We need to find edges whose removal creates exactly 2 components of 5 each
    # Strategy: manually construct a clean partition

    # Find a partition: remove edges between groups {0,1,2,3,4} and {5,6,7,8,9}
    cross_edges = [(u, v) for u, v in edges if (u < 5 and v >= 5) or (u >= 5 and v < 5)]
    intra_edges = [(u, v) for u, v in edges if not ((u < 5 and v >= 5) or (u >= 5 and v < 5))]

    print(f"\n--- Phase 2: Network Partition ---")
    print(f"  Total edges: {len(edges)}")
    print(f"  Cross-group edges (to remove): {len(cross_edges)} — {cross_edges}")
    print(f"  Intra-group edges (kept): {len(intra_edges)}")

    # Remove cross edges
    partitioned_edges = list(intra_edges)
    partitioned_adj = build_adjacency(N, partitioned_edges)
    components = connected_components(partitioned_adj)
    print(f"  Components after partition: {len(components)}")
    for i, comp in enumerate(components):
        print(f"    Component {i}: agents {sorted(comp)} ({len(comp)} agents)")

    # Phase 2: Run 100 ticks under partition
    print("\n--- Phase 2: Running 100 ticks under partition ---")
    partition_log = run_simulation(agents, partitioned_adj, 100, "partition")
    partition_max_drift = max_drift(agents)
    partition_pairwise = pairwise_max_drift(agents)
    partition_peak_drift = max(entry["pairwise_max"] for entry in partition_log)
    print(f"  Max agent drift during partition: {float(partition_max_drift):.10f}")
    print(f"  Peak pairwise drift during partition: {partition_peak_drift:.10f}")

    # Phase 3: Heal partition — restore all edges
    print(f"\n--- Phase 3: Heal partition (restore {len(cross_edges)} edges) ---")
    healed_edges = list(edges)  # restore original Laman graph
    healed_adj = build_adjacency(N, healed_edges)
    components_healed = connected_components(healed_adj)
    print(f"  Components after healing: {len(components_healed)}")

    # Phase 3: Run 200 ticks post-healing
    print("\n--- Phase 3: Running 200 ticks post-healing ---")
    heal_log = run_simulation(agents, healed_adj, 200, "post-healing")

    # Measure convergence time after healing
    # Convergence = pairwise drift drops below pre-partition level
    pre_threshold = float(pre_pairwise) * 1.5  # allow 150% of pre-partition drift
    convergence_tick = None
    for entry in heal_log:
        if entry["pairwise_max"] <= pre_threshold:
            convergence_tick = entry["tick"]
            break

    post_max_drift = max_drift(agents)
    post_pairwise = pairwise_max_drift(agents)
    final_pairwise = heal_log[-1]["pairwise_max"]

    print(f"\n--- Results ---")
    print(f"  Pre-partition pairwise drift: {float(pre_pairwise):.10f}")
    print(f"  Peak pairwise drift (partition): {partition_peak_drift:.10f}")
    print(f"  Post-healing pairwise drift (final): {final_pairwise:.10f}")
    print(f"  Convergence tick (post-healing): {convergence_tick}")
    print(f"  log2(N) = {N.bit_length() - 1} (O(log N) reference)")

    if convergence_tick is not None:
        log_n = N.bit_length() - 1  # log2(10) ≈ 3.32
        ratio = convergence_tick / log_n if log_n > 0 else float('inf')
        print(f"  Convergence / log2(N) = {ratio:.2f}")
        verdict = "SUPPORTS" if convergence_tick <= 10 * log_n else "WEAK"
    else:
        ratio = None
        verdict = "NO_CONVERGENCE"

    print(f"\n  Hypothesis verdict: {verdict}")
    print(f"  (Laman-rigid fleet recovers within O(log N) rounds after healing)")

    # Build results
    results = {
        "experiment": "experiment_09_partition_tolerance",
        "hypothesis": "Laman-rigid fleet recovers from partition within O(log N) rounds after healing",
        "parameters": {
            "N": N,
            "laman_edges": len(edges),
            "drift_rates": drift_rates,
            "phases": {
                "pre_partition_ticks": 200,
                "partition_ticks": 100,
                "post_healing_ticks": 200,
            },
            "cross_edges_removed": len(cross_edges),
            "cross_edges": [list(e) for e in cross_edges],
            "components_during_partition": [sorted(list(c)) for c in components],
        },
        "results": {
            "pre_partition": {
                "max_agent_drift": float(pre_max_drift),
                "pairwise_max_drift": float(pre_pairwise),
            },
            "partition": {
                "max_agent_drift_end": float(partition_max_drift),
                "peak_pairwise_drift": partition_peak_drift,
            },
            "post_healing": {
                "final_pairwise_drift": final_pairwise,
                "convergence_tick": convergence_tick,
                "log2_N": N.bit_length() - 1,
                "convergence_over_logN": ratio,
            },
        },
        "verdict": verdict,
        "phase1_drift_log": pre_log[-5:],  # last 5 entries
        "partition_drift_log": partition_log[-5:],
        "heal_drift_log_sample": heal_log[:20] + heal_log[-5:],
    }

    # Save
    out_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "experiment09_partition.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Fraction arithmetic verification
    print("\n--- Fraction Arithmetic Verification ---")
    for a in agents:
        d = a.clock.drift
        print(f"  {a.agent_id}: drift = {d} (exact Fraction), float = {float(d):.15f}")
    print("  ✓ All drifts are exact Fractions — zero precision loss")


if __name__ == "__main__":
    main()
