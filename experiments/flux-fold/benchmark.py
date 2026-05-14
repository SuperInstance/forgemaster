"""
flux-fold/benchmark.py — Benchmark runner for fold-based snap vs Eisenstein snap.

Tests:
  - Covering radius: max distance from a random point to its nearest lattice point
  - Throughput: snaps per second (Python reference)
  - Consensus distribution: how many fold orders agree on the result
  - Comparison vs Eisenstein (Z[ζ₃]) baseline

Usage:
  python benchmark.py                    # Run all benchmarks
  python benchmark.py --n 5 --n 12       # Specific orders only
  python benchmark.py --points 5000      # Fewer points for faster run
  python benchmark.py --save-results     # Save to JSON
"""

from __future__ import annotations

import math
import random
import time
import json
import argparse
import sys
import os
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vm import (
    cyclotomic_basis, basis_pairs, fold_orders,
    eisenstein_snap, overcomplete_snap, 
    permutational_fold_snap, exhaustive_min_snap,
    consensus_analysis
)

SQRT3 = math.sqrt(3)
EISENSTEIN_BOUND = 1.0 / SQRT3


def _overcomplete_snap_detail(x: float, y: float, n: int) -> Tuple[float, float, float]:
    """
    Overcomplete snap: project onto ALL basis pairs, take minimum distance.
    This is the gold standard — the true nearest lattice point.
    """
    pairs = basis_pairs(n)
    best_dist_sq = float('inf')
    best_snap = (x, y)
    
    for i, j, vi, vj in pairs:
        vi_r, vi_i = vi.real, vi.imag
        vj_r, vj_i = vj.real, vj.imag
        
        det = vi_r * vj_i - vi_i * vj_r
        if abs(det) < 1e-15:
            continue
        
        a = (x * vj_i - y * vj_r) / det
        b = (vi_r * y - vi_i * x) / det
        
        a_int = round(a)
        b_int = round(b)
        
        for da in [-1, 0, 1]:
            for db in [-1, 0, 1]:
                aa = a_int + da
                bb = b_int + db
                snap_r = aa * vi_r + bb * vj_r
                snap_i = aa * vi_i + bb * vj_i
                d_sq = (snap_r - x)**2 + (snap_i - y)**2
                if d_sq < best_dist_sq:
                    best_dist_sq = d_sq
                    best_snap = (snap_r, snap_i)
    
    return (best_snap[0], best_snap[1], math.sqrt(best_dist_sq))


def _fold_min_snap(x: float, y: float, n: int) -> Tuple[float, float, float, int]:
    """
    Try all fold orders, return the best result.
    Returns (snap_x, snap_y, min_distance, total_orders_tested).
    """
    orders = fold_orders(n)
    best_d = float('inf')
    best_snap = (x, y)
    
    for perm, _ in orders:
        sx, sy, d = permutational_fold_snap(x, y, n, perm)
        if d < best_d:
            best_d = d
            best_snap = (sx, sy)
    
    return (best_snap[0], best_snap[1], best_d, len(orders))


# ─── Benchmark suite ─────────────────────────────────────────────

def benchmark_single(n: int, num_points: int, seed: int = 42, verbose: bool = True) -> dict:
    """Run all benchmarks for a single cyclotomic order."""
    
    rng = random.Random(seed)
    basis = cyclotomic_basis(n)
    pairs = basis_pairs(n)
    orders_list = fold_orders(n)
    
    if verbose:
        print(f"\n  ── Z[ζ_{n}] — {len(basis)} basis, "
              f"{len(pairs)} pairs, {len(orders_list)} orders ──")
    
    # ── 1. Covering Radius ──
    max_d_e = 0.0
    max_d_oc = 0.0
    sum_d_e = 0.0
    sum_d_oc = 0.0
    improvements = []
    
    t0 = time.perf_counter()
    for _ in range(num_points):
        x = rng.uniform(-5, 5)
        y = rng.uniform(-5, 5)
        
        sx_e, sy_e, d_e = eisenstein_snap(x, y)
        max_d_e = max(max_d_e, d_e)
        sum_d_e += d_e
        
        sx_o, sy_o, d_o = _overcomplete_snap_detail(x, y, n)
        max_d_oc = max(max_d_oc, d_o)
        sum_d_oc += d_o
        improvements.append(d_e / d_o if d_o > 0 else 1.0)
    
    t_radius = time.perf_counter() - t0
    
    covering_radius = {
        "eisenstein_max": max_d_e,
        "eisenstein_mean": sum_d_e / num_points,
        "eisenstein_bound": EISENSTEIN_BOUND,
        "overcomplete_max": max_d_oc,
        "overcomplete_mean": sum_d_oc / num_points,
        "improvement_mean": sum(improvements) / len(improvements),
        "improvement_max": max(improvements),
        "time_seconds": t_radius,
        "time_us_per_point": t_radius * 1e6 / num_points,
    }
    
    if verbose:
        print(f"    Radius: Eisenstein max={max_d_e:.6f}, Z[ζ_{n}] max={max_d_oc:.6f}, "
              f"{covering_radius['improvement_mean']:.3f}× tighter")
    
    # ── 2. Throughput ──
    points = [(rng.uniform(-5, 5), rng.uniform(-5, 5)) for _ in range(num_points)]
    
    t0 = time.perf_counter()
    for x, y in points:
        eisenstein_snap(x, y)
    t_e = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    for x, y in points:
        _overcomplete_snap_detail(x, y, n)
    t_oc = time.perf_counter() - t0
    
    if orders_list:
        first_order = orders_list[0][0]
        t0 = time.perf_counter()
        for x, y in points:
            permutational_fold_snap(x, y, n, first_order)
        t_fold = time.perf_counter() - t0
    else:
        t_fold = float('inf')
        first_order = None
    
    throughput = {
        "eisenstein_snaps_per_sec": num_points / t_e,
        "overcomplete_snaps_per_sec": num_points / t_oc,
        "fold_snaps_per_sec": num_points / t_fold if t_fold > 0 else 0,
        "relative_to_eisenstein": (num_points / t_oc) / (num_points / t_e),
    }
    
    if verbose:
        print(f"    Throughput: Eisenstein {throughput['eisenstein_snaps_per_sec']:.0f} snaps/s, "
              f"Z[ζ_{n}] {throughput['overcomplete_snaps_per_sec']:.0f} snaps/s "
              f"({throughput['relative_to_eisenstein']:.2f}×)")
    
    # ── 3. Consensus ──
    rng = random.Random(seed + 1)
    n_consensus = min(num_points // 5, 2000)
    agreement_counts = {}
    
    for _ in range(n_consensus):
        x = rng.uniform(-5, 5)
        y = rng.uniform(-5, 5)
        
        all_dists = []
        for perm, _ in orders_list:
            _, _, d = permutational_fold_snap(x, y, n, perm)
            all_dists.append(d)
        
        min_d = min(all_dists)
        winners = sum(1 for d in all_dists if abs(d - min_d) < 1e-12)
        agreement_counts[winners] = agreement_counts.get(winners, 0) + 1
    
    total_agreed = sum(v for k, v in agreement_counts.items())
    mean_agreement = sum(k * v for k, v in agreement_counts.items()) / total_agreed if total_agreed > 0 else 0
    
    consensus = {
        "total_orders": len(orders_list),
        "points_tested": n_consensus,
        "mean_agreement": mean_agreement,
        "mean_agreement_pct": mean_agreement / len(orders_list) * 100 if len(orders_list) > 0 else 0,
        "agreement_distribution": dict(sorted(agreement_counts.items())),
    }
    
    if verbose:
        print(f"    Consensus: {consensus['mean_agreement_pct']:.1f}% mean agreement "
              f"({consensus['mean_agreement']:.1f}/{consensus['total_orders']} orders)")
    
    # ── 4. Exhaustive fold vs overcomplete ──
    rng = random.Random(seed + 2)
    n_matching = 0
    n_fold_worse = 0
    n_exhaustive = min(num_points // 2, 500)
    
    for _ in range(n_exhaustive):
        x = rng.uniform(-5, 5)
        y = rng.uniform(-5, 5)
        
        _, _, d_oc = _overcomplete_snap_detail(x, y, n)
        _, _, best_d_fold, _ = _fold_min_snap(x, y, n)
        
        if abs(best_d_fold - d_oc) < 1e-12:
            n_matching += 1
        elif best_d_fold > d_oc + 1e-12:
            n_fold_worse += 1
    
    exhaustive = {
        "points_tested": n_exhaustive,
        "matching": n_matching,
        "fold_worse": n_fold_worse,
        "accuracy_pct": n_matching / n_exhaustive * 100 if n_exhaustive > 0 else 0,
    }
    
    if verbose:
        print(f"    Exhaustive: {exhaustive['accuracy_pct']:.1f}% match overcomplete "
              f"({n_fold_worse} misses)")
    
    return {
        "n": n,
        "phi_n": len(basis),
        "num_pairs": len(pairs),
        "num_orders": len(orders_list),
        "num_points": num_points,
        "covering_radius": covering_radius,
        "throughput": throughput,
        "consensus": consensus,
        "exhaustive": exhaustive,
    }


# ─── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Flux-Fold: Benchmark overcomplete cyclotomic snap"
    )
    parser.add_argument("--n", type=int, nargs="+", default=[5, 12],
                        help="Cyclotomic orders to test")
    parser.add_argument("--points", type=int, default=5000,
                        help="Number of random points")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-results", action="store_true",
                        help="Save results to JSON")
    
    args = parser.parse_args()
    
    print("╔════════════════════════════════════════════════════╗")
    print("║  Flux-Fold Benchmark Suite                        ║")
    print("╚════════════════════════════════════════════════════╝")
    
    all_results = {}
    
    for n in args.n:
        result = benchmark_single(n, args.points, args.seed)
        all_results[str(n)] = result
    
    # Summary
    print("\n╔════════════════════════════════════════════════════╗")
    print("║  Summary                                          ║")
    print("╚════════════════════════════════════════════════════╝")
    
    print(f"\n  Eisenstein bound: {EISENSTEIN_BOUND:.6f}")
    
    for n in args.n:
        r = all_results[str(n)]
        cr = r["covering_radius"]
        tp = r["throughput"]
        ex = r["exhaustive"]
        
        print(f"\n  Z[ζ_{n}] (φ={r['phi_n']}, {r['num_pairs']} pairs, {r['num_orders']} orders):")
        print(f"    Radius:  max={cr['overcomplete_max']:.6f} "
              f"(vs {cr['eisenstein_max']:.6f} Eisenstein, "
              f"{cr['improvement_mean']:.3f}× tighter)")
        print(f"    Throughput: {tp['overcomplete_snaps_per_sec']:.0f} snaps/s "
              f"({tp['relative_to_eisenstein']:.2f}× Eisenstein)")
        print(f"    Accuracy: {ex['accuracy_pct']:.1f}% fold matches overcomplete")
        print(f"    Consensus: {r['consensus']['mean_agreement_pct']:.1f}% "
              f"({r['consensus']['mean_agreement']:.1f}/{r['consensus']['total_orders']} orders)")
    
    if args.save_results:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
        
        with open(output_path, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\n  Results saved to: {output_path}")


if __name__ == "__main__":
    main()
