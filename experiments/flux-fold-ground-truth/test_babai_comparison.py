#!/usr/bin/env python3
"""
test_babai_comparison.py — GROUND TRUTH: Compare against Babai's nearest plane algorithm.

Babai's nearest plane algorithm is the STANDARD polynomial-time algorithm
for finding a "nearby" lattice point. It's used in:
  - Lattice-based cryptography (Gentry's FHE, NIST PQC finalists)
  - LLL-reduced basis nearest neighbor
  - Approximate CVP (closest vector problem)

For an LLL-reduced basis, Babai guarantees the nearest plane distance
is within a factor of 2^{d/2} of optimal. For dim=2, that's within 2x.

We compare permutational folding against:
  1. Babai's nearest plane on a 2D hexagonal basis
  2. Babai on ALL basis pairs (our overcomplete approach without the folding)
  3. Babai + LLL reduction

If permutational folding can't beat Babai on its worst day, the concept
is DOA for applications like cryptography.

Author: Forgemaster ⚒️
Date: 2026-05-14
"""

import math
import random
import sys
import json
import time
from typing import Dict, List, Tuple
from itertools import product

import numpy as np

sys.path.insert(0, "/home/phoenix/.openclaw/workspace/experiments/flux-fold")
from vm import (
    cyclotomic_basis, basis_pairs, eisenstein_snap, overcomplete_snap,
    permutational_fold_snap, fold_orders, exhaustive_min_snap
)


# ─── Babai's Nearest Plane Algorithm ─────────────────────────────

def babai_nearest_plane(
    x: float, y: float, 
    b1: Tuple[float, float], b2: Tuple[float, float]
) -> Tuple[float, float, float]:
    """
    Babai's nearest plane algorithm for a 2D lattice basis.
    
    Given a lattice basis (b1, b2) and a target point (x, y),
    find a nearby lattice point.
    
    For 2D, the algorithm is:
    1. Compute the Gram-Schmidt orthogonalization
    2. Project the target onto each basis vector, rounding in the
       orthogonalized basis
    
    Returns (snapped_x, snapped_y, distance).
    """
    # Basis vectors as numpy arrays
    b1_arr = np.array([b1[0], b1[1]], dtype=np.float64)
    b2_arr = np.array([b2[0], b2[1]], dtype=np.float64)
    t = np.array([x, y], dtype=np.float64)
    
    # Gram-Schmidt
    b1_star = b1_arr.copy()
    # b2* = b2 - proj_{b1*}(b2)
    mu21 = np.dot(b2_arr, b1_star) / np.dot(b1_star, b1_star)
    b2_star = b2_arr - mu21 * b1_star
    
    # Nearest plane: project onto b2* first, round, subtract, project onto b1*
    # Make sure b2_star is nonzero
    b2_star_norm_sq = np.dot(b2_star, b2_star)
    
    if b2_star_norm_sq < 1e-20:
        # Degenerate basis (collinear)
        c = round(np.dot(t, b1_arr) / np.dot(b1_arr, b1_arr))
        f = c * b1_arr
        return (float(f[0]), float(f[1]), float(np.linalg.norm(t - f)))
    
    # Step 1: project onto b2*, round
    c2 = round(np.dot(t, b2_star) / b2_star_norm_sq)
    
    # Step 2: subtract, project onto b1*, round
    t_prime = t - c2 * b2_arr
    c1 = round(np.dot(t_prime, b1_star) / np.dot(b1_star, b1_star))
    
    # Reconstruct
    coeffs = np.array([c1, c2], dtype=np.float64)
    result = c1 * b1_arr + c2 * b2_arr
    
    dist = float(np.linalg.norm(t - result))
    return (float(result[0]), float(result[1]), dist)


def babai_all_pairs(
    x: float, y: float, n: int
) -> Tuple[Tuple[float, float], float, int]:
    """
    Apply Babai's algorithm to EVERY basis pair in the cyclotomic field.
    Take the minimum distance across all pairs.
    
    This is the "all-pairs" Babai approach — one could call this
    the overcomplete-Babai. We compare its results against permutational folding.
    
    Returns (best_point, best_distance, pair_count).
    """
    pairs = basis_pairs(n)
    best_d = float('inf')
    best_point = (x, y)
    
    for _, _, vi, vj in pairs:
        b1 = (vi.real, vi.imag)
        b2 = (vj.real, vj.imag)
        sx, sy, d = babai_nearest_plane(x, y, b1, b2)
        if d < best_d:
            best_d = d
            best_point = (sx, sy)
    
    return (best_point[0], best_point[1], best_d, len(pairs))


def lll_reduce_2d(
    b1: Tuple[float, float], b2: Tuple[float, float]
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    LLL lattice basis reduction for 2D (Lagrange's algorithm).
    
    Given a basis (b1, b2), produce an LLL-reduced basis.
    For 2D, this is just Gaussian lattice reduction (Lagrange's algorithm):
    while |b2| < |b1|, swap and subtract.
    """
    v1 = np.array([b1[0], b1[1]], dtype=np.float64)
    v2 = np.array([b2[0], b2[1]], dtype=np.float64)
    
    # Sort by norm
    if np.linalg.norm(v2) < np.linalg.norm(v1):
        v1, v2 = v2, v1
    
    # Gaussian reduction iteration
    max_iter = 100
    for _ in range(max_iter):
        m = round(np.dot(v1, v2) / np.dot(v1, v1))
        v2 = v2 - m * v1
        
        # Re-sort
        if np.linalg.norm(v2) < np.linalg.norm(v1):
            v1, v2 = v2, v1
        else:
            break
    
    # Ensure positive orientation (optional)
    return (
        (float(v1[0]), float(v1[1])),
        (float(v2[0]), float(v2[1])),
    )


def babai_on_lll_basis(
    x: float, y: float, n: int
) -> Tuple[float, float, float]:
    """
    Apply Babai on LLL-reduced basis pairs.
    
    The hypothesis: LLL reduction might give tighter results than
    raw basis pairs, since Babai is guaranteed on reduced bases.
    
    For each basis pair:
      1. LLL-reduce the pair
      2. Apply Babai nearest plane
      3. Take the minimum across all pairs
    """
    pairs = basis_pairs(n)
    best_d = float('inf')
    best_point = (x, y)
    
    for _, _, vi, vj in pairs:
        # LLL-reduce the basis pair
        b1 = (vi.real, vi.imag)
        b2 = (vj.real, vj.imag)
        
        try:
            b1_lll, b2_lll = lll_reduce_2d(b1, b2)
        except Exception:
            continue
        
        sx, sy, d = babai_nearest_plane(x, y, b1_lll, b2_lll)
        if d < best_d:
            best_d = d
            best_point = (sx, sy)
    
    return (best_point[0], best_point[1], best_d)


# ─── Round-off algorithm ────────────────────────────────────────

def round_off(
    x: float, y: float, 
    b1: Tuple[float, float], b2: Tuple[float, float]
) -> Tuple[float, float, float]:
    """
    The simplest nearest-integer algorithm: solve for coefficients in
    the given basis and round directly.
    
    This is what our overcomplete algorithm does per pair, without
    the 3x3 search.
    """
    v1 = np.array([b1[0], b1[1]])
    v2 = np.array([b2[0], b2[1]])
    t = np.array([x, y])
    
    # Solve 2x2: a * v1 + b * v2 = t
    M = np.column_stack([v1, v2])
    det = M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]
    
    if abs(det) < 1e-20:
        return (x, y, float('inf'))
    
    a = (t[0] * v2[1] - t[1] * v2[0]) / det
    b = (v1[0] * t[1] - v1[1] * t[0]) / det
    
    a_round, b_round = round(a), round(b)
    result = a_round * v1 + b_round * v2
    
    dist = float(np.linalg.norm(t - result))
    return (float(result[0]), float(result[1]), dist)


# ─── Tests ───────────────────────────────────────────────────────

def test_babai_vs_permutational_fold(n: int, num_trials: int = 5000) -> dict:
    """
    COMPARISON: Babai nearest plane (raw pairs) vs permutational folding.
    
    Which gives tighter snap? By how much?
    """
    random.seed(42)
    
    babai_raw_wins = 0
    babai_lll_wins = 0
    perm_fold_wins = 0
    overcomplete_wins = 0
    ties = 0
    
    babai_dists = []
    babai_lll_dists = []
    perm_fold_dists = []
    overcomplete_dists = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Babai on raw pairs
        _, _, d_babai, _ = babai_all_pairs(x, y, n)
        
        # Babai on LLL-reduced pairs
        _, _, d_lll = babai_on_lll_basis(x, y, n)
        
        # Permutational fold (min across all orders)
        _, _, _, _, all_fold_dists = exhaustive_min_snap(x, y, n)
        d_fold = min(all_fold_dists)
        
        # Overcomplete (min across all basis pairs, 3x3 search)
        _, _, d_oc = overcomplete_snap(x, y, n)
        
        babai_dists.append(d_babai)
        babai_lll_dists.append(d_lll)
        perm_fold_dists.append(d_fold)
        overcomplete_dists.append(d_oc)
        
        # Tally wins
        min_overall = min(d_babai, d_lll, d_fold, d_oc)
        if abs(d_fold - min_overall) < 1e-12:
            perm_fold_wins += 1
        if abs(d_oc - min_overall) < 1e-12:
            overcomplete_wins += 1
        if abs(d_babai - min_overall) < 1e-12:
            babai_raw_wins += 1
        if abs(d_lll - min_overall) < 1e-12:
            babai_lll_wins += 1
    
    return {
        "test": "babai_vs_permutational_fold",
        "n": n,
        "num_trials": num_trials,
        "head_to_head": {
            "babai_raw_pairs": {
                "mean_dist": sum(babai_dists) / len(babai_dists),
                "max_dist": max(babai_dists),
                "wins": babai_raw_wins,
                "win_pct": 100.0 * babai_raw_wins / num_trials,
            },
            "babai_lll_reduced": {
                "mean_dist": sum(babai_lll_dists) / len(babai_lll_dists),
                "max_dist": max(babai_lll_dists),
                "wins": babai_lll_wins,
                "win_pct": 100.0 * babai_lll_wins / num_trials,
            },
            "permutational_fold": {
                "mean_dist": sum(perm_fold_dists) / len(perm_fold_dists),
                "max_dist": max(perm_fold_dists),
                "wins": perm_fold_wins,
                "win_pct": 100.0 * perm_fold_wins / num_trials,
            },
            "overcomplete_snap": {
                "mean_dist": sum(overcomplete_dists) / len(overcomplete_dists),
                "max_dist": max(overcomplete_dists),
                "wins": overcomplete_wins,
                "win_pct": 100.0 * overcomplete_wins / num_trials,
            },
        }
    }


def test_round_off_vs_perm_fold(n: int, num_trials: int = 5000) -> dict:
    """
    COMPARISON: Simple round-off on each basis pair vs permutational folding.
    
    The round-off algorithm is the trivial approach: solve the linear system
    and round. Our algorithm adds a 3x3 neighborhood search.
    
    This isolates the benefit of the 3x3 search vs the benefit of the 
    overcomplete basis itself.
    """
    random.seed(42)
    
    round_off_better = 0
    fold_better = 0
    
    round_off_dists = []
    fold_dists = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Round-off on all pairs (minimum)
        pairs = basis_pairs(n)
        best_round_d = float('inf')
        for _, _, vi, vj in pairs:
            b1 = (vi.real, vi.imag)
            b2 = (vj.real, vj.imag)
            _, _, d = round_off(x, y, b1, b2)
            best_round_d = min(best_round_d, d)
        round_off_dists.append(best_round_d)
        
        # Permutational fold
        _, _, _, _, all_fold = exhaustive_min_snap(x, y, n)
        d_fold = min(all_fold)
        fold_dists.append(d_fold)
        
        if d_fold < best_round_d - 1e-12:
            fold_better += 1
        elif best_round_d < d_fold - 1e-12:
            round_off_better += 1
    
    return {
        "test": "round_off_vs_perm_fold",
        "n": n,
        "num_trials": num_trials,
        "round_off_best_pair": {
            "mean": sum(round_off_dists) / len(round_off_dists),
            "max": max(round_off_dists),
        },
        "permutational_fold_best": {
            "mean": sum(fold_dists) / len(fold_dists),
            "max": max(fold_dists),
        },
        "fold_improves_round_off": fold_better,
        "round_off_better_than_fold": round_off_better,
        "fold_improvement_pct": 100.0 * fold_better / num_trials,
    }


def test_babai_failure_modes(n: int, num_trials: int = 3000) -> dict:
    """
    Find cases where Babai's nearest plane fails (gives suboptimal result).
    
    Babai guarantees distance ≤ 2^{d/2} * optimal, where d is the dimension.
    For 2D, that's ≤ 2x optimal.
    
    For OVERCOMPLETE Babai (best across all pairs), we hope to do better.
    
    We find the POINTS where Babai on every pair is worse than the
    exhaustive 3x3 search that permutational folding enables.
    """
    random.seed(42)
    
    bad_for_babai = []  # Points where Babai is > 2x optimal
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Get optimal via 3x3 search (our best approximation)
        _, _, _, _, all_fold = exhaustive_min_snap(x, y, n)
        d_optimal = min(all_fold)
        
        # Babai on all pairs
        _, _, d_babai, _ = babai_all_pairs(x, y, n)
        
        # How far from optimal?
        ratio = d_babai / d_optimal if d_optimal > 1e-15 else 1.0
        
        if ratio > 2.0:
            bad_for_babai.append((x, y, d_babai, d_optimal, ratio))
    
    bad_for_babai.sort(key=lambda p: p[4], reverse=True)
    
    return {
        "test": "babai_failure_modes",
        "n": n,
        "num_trials": num_trials,
        "babai_failures_over_2x": len(bad_for_babai),
        "failure_rate_percent": 100.0 * len(bad_for_babai) / num_trials,
        "worst_failures": [
            {"x": p[0], "y": p[1], "babai_dist": p[2], "optimal_dist": p[3], "ratio": p[4]}
            for p in bad_for_babai[:10]
        ],
    }


def test_algorithm_speed(n: int, num_trials: int = 1000) -> dict:
    """
    Speed comparison: how fast is each algorithm?
    
    The metric that matters: how many lattice points can we check per second?
    
    Algorithms compared:
      1. Eisenstein snap (baseline, ~9 operations)
      2. Babai on a single pair (fast, ~20 ops per pair)
      3. Babai on all pairs (one pass)
      4. Overcomplete snap: all pairs with 3x3 search
      5. Permutational fold: all fold orders
      6. Brute-force: exhaustive search over φ(n)-dim hypercube
    """
    import time
    
    random.seed(42)
    
    # Generate test points
    test_points = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(min(num_trials, 500))]
    
    benchmarks = {}
    
    # 1. Eisenstein
    start = time.time()
    for x, y in test_points:
        eisenstein_snap(x, y)
    elapsed = time.time() - start
    benchmarks["eisenstein_snap"] = {
        "total_seconds": elapsed,
        "per_point_ms": 1000 * elapsed / len(test_points),
    }
    
    # 2. Round-off on first pair
    pairs = basis_pairs(n)
    if pairs:
        _, _, vi, vj = pairs[0]
        b1 = (vi.real, vi.imag)
        b2 = (vj.real, vj.imag)
        start = time.time()
        for x, y in test_points:
            round_off(x, y, b1, b2)
        elapsed = time.time() - start
        benchmarks["round_off_single_pair"] = {
            "total_seconds": elapsed,
            "per_point_ms": 1000 * elapsed / len(test_points),
        }
    
    # 3. Babai on all pairs
    start = time.time()
    for x, y in test_points:
        babai_all_pairs(x, y, n)
    elapsed = time.time() - start
    benchmarks["babai_all_pairs"] = {
        "total_seconds": elapsed,
        "per_point_ms": 1000 * elapsed / len(test_points),
    }
    
    # 4. Overcomplete snap (3x3 per pair)
    start = time.time()
    for x, y in test_points:
        overcomplete_snap(x, y, n)
    elapsed = time.time() - start
    benchmarks["overcomplete_snap"] = {
        "total_seconds": elapsed,
        "per_point_ms": 1000 * elapsed / len(test_points),
    }
    
    # 5. Permutational fold (all orders)
    start = time.time()
    for x, y in test_points:
        _, _, _, _, all_fold = exhaustive_min_snap(x, y, n)
    elapsed = time.time() - start
    benchmarks["permutational_fold_all"] = {
        "total_seconds": elapsed,
        "per_point_ms": 1000 * elapsed / len(test_points),
    }
    
    return {
        "test": "algorithm_speed",
        "n": n,
        "num_test_points": len(test_points),
        "num_basis_vectors": len(cyclotomic_basis(n)),
        "num_basis_pairs": len(basis_pairs(n)),
        "benchmarks": benchmarks,
    }


def run_all_tests() -> Dict:
    """Run all Babai comparison tests."""
    print("=" * 60)
    print("GROUND TRUTH: Babai & Competitive Algorithm Comparison")
    print("=" * 60)
    
    results = {
        "metadata": {
            "suite": "flux-fold-ground-truth",
            "author": "Forgemaster ⚒️",
            "date": "2026-05-14",
            "description": "Compare permutational folding against Babai, LLL, and round-off algorithms",
        },
        "tests": {}
    }
    
    for n in [3, 5, 8, 10, 12]:
        phi_n = len(cyclotomic_basis(n))
        print(f"\n{'='*60}")
        print(f"FIELD Z[ζ_{n}] (φ={phi_n})")
        print(f"{'='*60}")
        
        # Test 1: Babai vs Permutational Fold
        print(f"\n--- Test 1: Babai vs Perm Fold (n={n})...")
        start = time.time()
        r1 = test_babai_vs_permutational_fold(n, num_trials=5000)
        r1["runtime_seconds"] = time.time() - start
        h = r1["head_to_head"]
        print(f"  Babai raw mean: {h['babai_raw_pairs']['mean_dist']:.4f}, wins: {h['babai_raw_pairs']['win_pct']:.1f}%")
        print(f"  Babai LLL mean: {h['babai_lll_reduced']['mean_dist']:.4f}, wins: {h['babai_lll_reduced']['win_pct']:.1f}%")
        print(f"  Perm fold mean: {h['permutational_fold']['mean_dist']:.4f}, wins: {h['permutational_fold']['win_pct']:.1f}%")
        print(f"  Overcomplete mean: {h['overcomplete_snap']['mean_dist']:.4f}, wins: {h['overcomplete_snap']['win_pct']:.1f}%")
        results["tests"][f"z{n}_babai_comparison"] = r1
        
        # Test 2: Round-off vs Perm Fold
        print(f"\n--- Test 2: Round-Off vs Perm Fold (n={n})...")
        start = time.time()
        r2 = test_round_off_vs_perm_fold(n, num_trials=5000)
        r2["runtime_seconds"] = time.time() - start
        print(f"  Fold improves round-off: {r2['fold_improvement_pct']:.2f}%")
        print(f"  Round-off mean: {r2['round_off_best_pair']['mean']:.4f}")
        print(f"  Fold mean: {r2['permutational_fold_best']['mean']:.4f}")
        results["tests"][f"z{n}_round_off_comparison"] = r2
        
        # Test 3: Babai failure modes
        print(f"\n--- Test 3: Babai Failure Modes (n={n})...")
        start = time.time()
        r3 = test_babai_failure_modes(n, num_trials=3000)
        r3["runtime_seconds"] = time.time() - start
        print(f"  Babai failures >2x optimal: {r3['failure_rate_percent']:.3f}%")
        results["tests"][f"z{n}_babai_failures"] = r3
        
        # Test 4: Speed comparison
        print(f"\n--- Test 4: Algorithm Speed (n={n})...")
        start = time.time()
        r4 = test_algorithm_speed(n, num_trials=1000)
        r4["runtime_seconds"] = time.time() - start
        for name, bench in r4["benchmarks"].items():
            print(f"  {name:35s}: {bench['per_point_ms']:.4f} ms/point")
        results["tests"][f"z{n}_speed"] = r4
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    
    outpath = "/home/phoenix/.openclaw/workspace/experiments/flux-fold-ground-truth/results_babai.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"Results written to: {outpath}")
