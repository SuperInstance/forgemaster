#!/usr/bin/env python3
"""
Experiment 17: Edge Augmentation Effects
Questions:
1. How does adding extra edges beyond Laman minimum affect convergence?
2. Is there diminishing returns after 20% augmentation?
3. How does augmentation affect spectral gap and message overhead?

Protocol:
- N=20, base Laman topology (2*20-3 = 37 edges)
- Augmentation levels: 0%, 10%, 20%, 50%, 100%
- For each level, run 500 ticks with Fraction-based consensus
- Measure: convergence tick, max drift, messages/tick, spectral gap
"""
import json
import math
import random
import sys
import time
from fractions import Fraction

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

random.seed(42)

# ============================================================
# Topology builders
# ============================================================

def henneberg_type1(n):
    """Build minimal Laman graph via Henneberg type-I construction."""
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]
    for v in range(3, n):
        targets = random.sample(range(v), min(2, v))
        while len(targets) < 2:
            targets.append(random.randint(0, v - 1))
        edges.append((v, targets[0]))
        edges.append((v, targets[1]))
    return edges


def augment_edges(base_edges, n, frac):
    """Add frac*100% extra random edges beyond the base Laman set."""
    if frac == 0:
        return list(base_edges)
    existing = set(tuple(sorted(e)) for e in base_edges)
    num_new = max(1, int(len(base_edges) * frac))
    new_edges = []
    attempts = 0
    while len(new_edges) < num_new and attempts < num_new * 50:
        u, v = random.sample(range(n), 2)
        key = tuple(sorted((u, v)))
        if key not in existing:
            existing.add(key)
            new_edges.append((u, v))
        attempts += 1
    return list(base_edges) + new_edges


def build_adjacency(edges, n):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


# ============================================================
# Spectral gap computation
# ============================================================

def compute_spectral_gap(edges, n):
    """Compute spectral gap (second-smallest eigenvalue of Laplacian)."""
    row, col = [], []
    for u, v in edges:
        row.extend([u, v])
        col.extend([v, u])
    data = [1.0] * len(row)
    A = sparse.csr_matrix((data, (row, col)), shape=(n, n))
    degrees = np.array(A.sum(axis=1)).flatten()
    L = sparse.diags(degrees) - A
    # Find the two smallest eigenvalues
    try:
        eigenvalues, _ = eigsh(L, k=2, which='SM')
        eigenvalues = sorted(eigenvalues)
        # eigenvalues[0] should be ~0, eigenvalues[1] is spectral gap
        return float(eigenvalues[1])
    except Exception:
        return -1.0


# ============================================================
# Simulation engine
# ============================================================

def simulate(n, edges, max_ticks=500, convergence_threshold=Fraction(1, 100), deadband=Fraction(1, 1000)):
    adj = build_adjacency(edges, n)
    states = [Fraction(i * 100, n) for i in range(n)]

    convergence_tick = None
    total_messages = 0
    max_drifts = []

    t0 = time.time()

    for tick in range(1, max_ticks + 1):
        tick_messages = 0
        new_states = list(states)

        for node in range(n):
            neighbors = adj[node]
            if not neighbors:
                continue
            received = []
            for nb in neighbors:
                drift = abs(states[nb] - states[node])
                if drift > deadband:
                    received.append(states[nb])
                    tick_messages += 1

            if received:
                total = states[node] + sum(received)
                count = 1 + len(received)
                new_states[node] = total / count

        states = new_states
        total_messages += tick_messages

        min_val = min(states)
        max_val = max(states)
        max_drift = max_val - min_val
        max_drifts.append(float(max_drift))

        if max_drift < convergence_threshold and convergence_tick is None:
            convergence_tick = tick

    wall_time = time.time() - t0
    final_max_drift = max_drifts[-1] if max_drifts else 0
    avg_messages_per_tick = total_messages / max_ticks if max_ticks > 0 else 0

    return {
        "convergence_tick": convergence_tick,
        "max_drift_final": round(final_max_drift, 8),
        "avg_messages_per_tick": round(avg_messages_per_tick, 2),
        "total_messages": total_messages,
        "wall_time_s": round(wall_time, 4),
    }


# ============================================================
# Main experiment
# ============================================================

def main():
    N = 20
    laman_edge_count = 2 * N - 3  # 37
    augmentation_levels = [0.0, 0.10, 0.20, 0.50, 1.0]
    max_ticks = 500
    num_trials = 5  # average over trials for robustness

    print("=" * 90)
    print("EXPERIMENT 17: EDGE AUGMENTATION EFFECTS")
    print(f"N={N}, Laman base edges={laman_edge_count}, max_ticks={max_ticks}, trials={num_trials}")
    print("=" * 90)

    all_results = []

    for aug_frac in augmentation_levels:
        num_extra = int(laman_edge_count * aug_frac)
        total_edges = laman_edge_count + num_extra
        print(f"\n--- Augmentation: {aug_frac*100:.0f}% ({num_extra} extra, {total_edges} total edges) ---")

        trial_results = []
        for trial in range(num_trials):
            random.seed(42 + trial)
            base = henneberg_type1(N)
            assert len(base) == laman_edge_count
            edges = augment_edges(base, N, aug_frac)

            spectral_gap = compute_spectral_gap(edges, N)
            sim = simulate(N, edges, max_ticks=max_ticks)
            sim["spectral_gap"] = round(spectral_gap, 6)
            sim["augmentation_frac"] = aug_frac
            sim["total_edges"] = len(edges)
            sim["extra_edges"] = len(edges) - laman_edge_count
            sim["trial"] = trial
            trial_results.append(sim)

            conv = sim["convergence_tick"]
            conv_str = str(conv) if conv else "NOT CONVERGED"
            print(f"  Trial {trial}: conv={conv_str}, drift={sim['max_drift_final']:.8f}, "
                  f"msgs/tick={sim['avg_messages_per_tick']}, λ₂={spectral_gap:.6f}")

        # Aggregate across trials
        avg_conv = None
        conv_values = [r["convergence_tick"] for r in trial_results if r["convergence_tick"] is not None]
        if conv_values:
            avg_conv = round(sum(conv_values) / len(conv_values), 1)

        agg = {
            "augmentation_frac": aug_frac,
            "augmentation_pct": f"{aug_frac*100:.0f}%",
            "base_laman_edges": laman_edge_count,
            "extra_edges": num_extra,
            "total_edges": total_edges,
            "avg_convergence_tick": avg_conv,
            "avg_max_drift_final": round(sum(r["max_drift_final"] for r in trial_results) / num_trials, 8),
            "avg_messages_per_tick": round(sum(r["avg_messages_per_tick"] for r in trial_results) / num_trials, 2),
            "avg_spectral_gap": round(sum(r["spectral_gap"] for r in trial_results) / num_trials, 6),
            "avg_wall_time_s": round(sum(r["wall_time_s"] for r in trial_results) / num_trials, 4),
            "trials": trial_results,
        }
        all_results.append(agg)

        agg_conv_str = str(avg_conv) if avg_conv else "NOT CONVERGED"
        print(f"  >> AVG: conv={agg_conv_str}, drift={agg['avg_max_drift_final']:.8f}, "
              f"msgs/tick={agg['avg_messages_per_tick']}, λ₂={agg['avg_spectral_gap']:.6f}")

    # ============================================================
    # Summary table
    # ============================================================
    print("\n" + "=" * 90)
    print("SUMMARY TABLE")
    print("=" * 90)
    header = f"{'Aug%':>6} {'Edges':>7} {'Extra':>6} {'ConvTick':>9} {'MaxDrift':>12} {'Msgs/Tick':>10} {'λ₂(spectral)':>14} {'Wall(s)':>9}"
    print(header)
    print("-" * len(header))
    for r in all_results:
        conv = str(r["avg_convergence_tick"]) if r["avg_convergence_tick"] else "NC"
        print(f"{r['augmentation_pct']:>6} {r['total_edges']:>7} {r['extra_edges']:>6} "
              f"{conv:>9} {r['avg_max_drift_final']:>12.8f} {r['avg_messages_per_tick']:>10.2f} "
              f"{r['avg_spectral_gap']:>14.6f} {r['avg_wall_time_s']:>9.4f}")

    # ============================================================
    # Hypothesis check
    # ============================================================
    print("\n" + "=" * 90)
    print("HYPOTHESIS CHECK: Diminishing returns after 20% augmentation?")
    print("=" * 90)

    baseline = all_results[0]
    for r in all_results[1:]:
        aug_pct = r["augmentation_pct"]
        if baseline["avg_convergence_tick"] and r["avg_convergence_tick"]:
            conv_improvement = baseline["avg_convergence_tick"] - r["avg_convergence_tick"]
            pct_improvement = conv_improvement / baseline["avg_convergence_tick"] * 100
            msg_overhead = r["avg_messages_per_tick"] - baseline["avg_messages_per_tick"]
            spectral_gain = r["avg_spectral_gap"] - baseline["avg_spectral_gap"]
            print(f"  {aug_pct}: convergence improved by {conv_improvement:.1f} ticks "
                  f"({pct_improvement:.1f}%), spectral gap +{spectral_gain:.6f}, "
                  f"message overhead +{msg_overhead:.1f}/tick")
        else:
            print(f"  {aug_pct}: did not converge in all configurations")

    # Check diminishing returns
    if len(all_results) >= 4:
        r10 = all_results[1]  # 10%
        r20 = all_results[2]  # 20%
        r50 = all_results[3]  # 50%

        if (r10["avg_convergence_tick"] and r20["avg_convergence_tick"] and r50["avg_convergence_tick"]):
            gain_10_to_20 = r10["avg_convergence_tick"] - r20["avg_convergence_tick"]
            gain_20_to_50 = r20["avg_convergence_tick"] - r50["avg_convergence_tick"]
            print(f"\n  Gain 10%→20%: {gain_10_to_20:.1f} ticks")
            print(f"  Gain 20%→50%: {gain_20_to_50:.1f} ticks")
            if gain_20_to_50 < gain_10_to_20 * 0.5:
                print("  ✓ HYPOTHESIS CONFIRMED: Diminishing returns after 20% augmentation")
            else:
                print("  ✗ HYPOTHESIS NOT CONFIRMED: Returns do not diminish after 20%")
        else:
            print("  Cannot fully evaluate (some configs did not converge)")

    # Save results
    output = {
        "experiment": "experiment17_edge_augmentation",
        "description": "Edge augmentation effects on Laman topology convergence",
        "parameters": {
            "N": N,
            "laman_edges": laman_edge_count,
            "augmentation_levels": augmentation_levels,
            "max_ticks": max_ticks,
            "num_trials": num_trials,
        },
        "summary": all_results,
    }

    outpath = "experiments/results/experiment17_augmentation.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {outpath}")


if __name__ == "__main__":
    main()
