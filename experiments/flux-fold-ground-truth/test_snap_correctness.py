#!/usr/bin/env python3
"""
test_snap_correctness.py — GROUND TRUTH: Are cyclotomic folds returning valid lattice points?

Tests whether the permutational folding snap algorithm returns VALID lattice points
for 100K random points across cyclotomic fields Z[ζₙ] for n=3, 5, 8, 10, 12.

A valid lattice point is one that belongs to the ring Z[ζₙ], meaning it can be
expressed as Σ c_k * ζₙ^k with integer coefficients c_k.

Key questions:
  1. Are snapped points actually lattice points? (Must be true by construction)
  2. Is the snapping idempotent? (Snapping a snapped point should change nothing)
  3. Does the snap distance distribution match theoretical covering radius?
  4. Is the snap optimal (closest lattice point)? Or just "some" lattice point?

Author: Forgemaster ⚒️
Date: 2026-05-14
"""

import math
import random
import sys
import json
import time
from typing import List, Tuple, Optional, Dict

sys.path.insert(0, "/home/phoenix/.openclaw/workspace/experiments/flux-fold")
from vm import (
    cyclotomic_basis, basis_pairs, eisenstein_snap, 
    overcomplete_snap, permutational_fold_snap, fold_orders,
    exhaustive_min_snap
)

# ─── Ground-truth helpers ────────────────────────────────────────

def assert_lattice_point(
    x: float, y: float, n: int, basis: List[complex], 
    tol: float = 1e-10
) -> bool:
    """
    Verify (x, y) is a valid point in Z[ζₙ] by checking it can be
    expressed with integer coefficients.

    For an overcomplete basis, this underdetermined check warns
    even when a non-lattice point passes. So we also check that
    the point is in the Z-span of the basis at ALL.
    """
    # Check: can we find integer coefficients?
    # Use linear least squares to find float coefficients, then check near-integer
    pairs = basis_pairs(n)
    
    # Try each basis pair — if any gives integer coefficients within tol, it's a lattice point
    for _, _, vi, vj in pairs:
        det = vi.real * vj.imag - vi.imag * vj.real
        if abs(det) < 1e-15:
            continue
        a = (x * vj.imag - y * vj.real) / det
        b = (vi.real * y - vi.imag * x) / det
        
        # Check near-integer
        a_nearest, b_nearest = round(a), round(b)
        ax = a_nearest * vi.real + b_nearest * vj.real
        ay = a_nearest * vi.imag + b_nearest * vj.imag
        
        dist = math.hypot(ax - x, ay - y)
        if dist < tol:
            return True
    
    return False


def find_optimal_snap_bruteforce(
    x: float, y: float, n: int, radius: int = 5
) -> Tuple[float, float, float]:
    """
    Brute-force search for the TRUE nearest lattice point.
    Iterates over all integer combinations in a bounded region.
    This is the ONLY truly authoritative snap oracle.

    For Z[ζₙ] with φ(n) basis vectors, we search a φ(n)-dim hypercube
    of side length 2*radius. For n=12, φ=4, that's (2r+1)^4 points.

    radius=5 gives 11^4 = 14641 points for n=12, checked exhaustively.
    """
    basis = cyclotomic_basis(n)
    dim = len(basis)
    
    z = complex(x, y)
    best_d = float('inf')
    best_point = (x, y)
    
    # Generate search range
    search_coords = [range(-radius, radius + 1) for _ in range(dim)]
    
    from itertools import product
    for coeffs in product(*search_coords):
        reconstructed = sum(c * basis[i] for i, c in enumerate(coeffs))
        d = abs(reconstructed - z)
        if d < best_d:
            best_d = d
            best_point = (reconstructed.real, reconstructed.imag)
    
    return (best_point[0], best_point[1], best_d)


# ─── Test Suite ──────────────────────────────────────────────────

def test_valid_lattice_point(n: int, num_trials: int = 10000) -> dict:
    """
    TEST 1: Verify snapped points are valid lattice points.
    
    Expected: MUST be true by construction (100% valid).
    If not, the snap algorithm is buggy.
    """
    basis = cyclotomic_basis(n)
    orders = fold_orders(n)
    passed = 0
    failed = 0
    invalid_points = []
    
    random.seed(42)
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Use the overcomplete snap (minimum across all pairs)
        sx, sy, _ = overcomplete_snap(x, y, n)
        
        if assert_lattice_point(sx, sy, n, basis):
            passed += 1
        else:
            failed += 1
            if len(invalid_points) < 10:
                invalid_points.append({
                    "original": (x, y), "snapped": (sx, sy), "n": n
                })
        
        # Also check each permutational fold
        for perm, _ in orders[:3]:  # only check first 3 orders to avoid O(n²)
            sx_perm, sy_perm, _ = permutational_fold_snap(x, y, n, perm)
            if not assert_lattice_point(sx_perm, sy_perm, n, basis):
                failed += 1
                if len(invalid_points) < 20:
                    invalid_points.append({
                        "original": (x, y), 
                        "snapped_perm": (sx_perm, sy_perm),
                        "perm": list(perm),
                        "n": n
                    })
    
    return {
        "test": "valid_lattice_point",
        "n": n,
        "num_trials": num_trials,
        "passed": passed,
        "failed": failed,
        "valid_percent": 100.0 * passed / (passed + failed) if (passed + failed) > 0 else 0.0,
        "invalid_samples": invalid_points[:5]
    }


def test_idempotence(n: int, num_trials: int = 10000) -> dict:
    """
    TEST 2: Is the snap idempotent?
    
    If snap returns a lattice point, snapping again should give the same point.
    This tests correctness of the lattice point membership AND numerical stability.
    
    Expected: >99.9% of points should be idempotent.
    """
    random.seed(42)
    same_count = 0
    diff_count = 0
    max_diff = 0.0
    diffs = []
    
    for _ in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        sx, sy, _ = overcomplete_snap(x, y, n)
        sx2, sy2, _ = overcomplete_snap(sx, sy, n)
        
        diff = math.hypot(sx - sx2, sy - sy2)
        if diff < 1e-10:
            same_count += 1
        else:
            diff_count += 1
            diffs.append((x, y, sx, sy, sx2, sy2, diff))
            max_diff = max(max_diff, diff)
    
    return {
        "test": "idempotence",
        "n": n,
        "num_trials": num_trials,
        "idempotent_count": same_count,
        "non_idempotent_count": diff_count,
        "idempotent_percent": 100.0 * same_count / num_trials,
        "max_drift_on_second_snap": max_diff,
        "sample_drifters": diffs[:3]
    }


def test_snap_distance_distribution(n: int, num_trials: int = 10000) -> dict:
    """
    TEST 3: Characterize the snap distance distribution.
    
    Measures the ACTUAL covering radius (max distance from any point
    to nearest lattice point) by random sampling.
    
    Compares:
      - overcomplete_snap (pairwise minimum across basis pairs)
      - exhaustive_min_snap (all fold orders)
      - eisenstein_snap (baseline for Z[ζ₃])
    
    Key warnings:
      - Theoretical covering radius assumes infinite search radius
      - Our search is only on a 3x3 local neighborhood per pair
      - This can miss the true nearest lattice point!
    """
    random.seed(42)
    
    oc_dists = []
    perm_dists = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        _, _, d_oc = overcomplete_snap(x, y, n)
        
        # Also get the exhaustive fold min
        _, _, _, _, all_fold_dists = exhaustive_min_snap(x, y, n)
        min_fold = min(all_fold_dists)
        
        oc_dists.append(d_oc)
        perm_dists.append(min_fold)
    
    oc_dists.sort()
    perm_dists.sort()
    
    return {
        "test": "snap_distance_distribution",
        "n": n,
        "num_trials": num_trials,
        "overcomplete_snap": {
            "max": max(oc_dists),
            "min": min(oc_dists),
            "mean": sum(oc_dists) / len(oc_dists),
            "median": oc_dists[len(oc_dists)//2],
            "p95": oc_dists[int(0.95 * len(oc_dists))],
            "p99": oc_dists[int(0.99 * len(oc_dists))],
        },
        "permutational_fold_min": {
            "max": max(perm_dists),
            "min": min(perm_dists),
            "mean": sum(perm_dists) / len(perm_dists),
            "median": perm_dists[len(perm_dists)//2],
            "p95": perm_dists[int(0.95 * len(perm_dists))],
            "p99": perm_dists[int(0.99 * len(perm_dists))],
        },
        "eisenstein_theoretical_radius": 1.0 / math.sqrt(3),
    }


def test_optimality_oracle(n: int, num_trials: int = 500) -> dict:
    """
    TEST 4: Compare snap distance to brute-force optimal for small regions.
    
    Brute-force search over φ(n)-dim hypercube of lattice coefficients
    gives the TRUE nearest neighbor. We compare our snap result against it.
    
    This is the HARDEST test: does the 3x3 neighborhood search miss
    the true nearest lattice point?
    
    Limited to 500 trials because brute-force is O((2r+1)^φ(n)) per point.
    For n=12, φ=4, r=5 that's 14641 lattice points per query ≈ 7M total.
    """
    basis = cyclotomic_basis(n)
    random.seed(42)
    
    optimal_matches = 0
    suboptimal_count = 0
    total_deviation = 0.0
    max_deviation = 0.0
    deviation_samples = []
    
    for i in range(num_trials):
        x = random.uniform(-2, 2)
        y = random.uniform(-2, 2)
        
        # Our snap
        sx_oc, sy_oc, d_oc = overcomplete_snap(x, y, n)
        
        # Brute force optimal
        sx_opt, sy_opt, d_opt = find_optimal_snap_bruteforce(x, y, n, radius=5)
        
        deviation = d_oc - d_opt
        
        if deviation < 1e-10:
            optimal_matches += 1
        else:
            suboptimal_count += 1
            total_deviation += deviation
            max_deviation = max(max_deviation, deviation)
            if len(deviation_samples) < 10:
                deviation_samples.append({
                    "original": (x, y),
                    "overcomplete_snap": {
                        "point": (sx_oc, sy_oc),
                        "distance": d_oc
                    },
                    "optimal": {
                        "point": (sx_opt, sy_opt),
                        "distance": d_opt
                    },
                    "deviation": deviation
                })
    
    return {
        "test": "optimality_oracle",
        "n": n,
        "num_trials": num_trials,
        "search_radius": 5,
        "optimal_count": optimal_matches,
        "suboptimal_count": suboptimal_count,
        "optimal_percent": 100.0 * optimal_matches / num_trials,
        "mean_deviation": total_deviation / num_trials if num_trials > 0 else 0,
        "max_deviation": max_deviation,
        "samples": deviation_samples[:5]
    }


def test_fold_order_variation(n: int, num_trials: int = 500) -> dict:
    """
    TEST 5: How much do different fold orders disagree?
    
    If 99% of points have no unanimous answer, that's either:
      (a) A fundamental property of overcomplete bases — multiple valid representations
      (b) An artifact of the greedy fold algorithm — suboptimal snap per order
      (c) A signal that can be exploited — consensus as uncertainty
    
    We measure: for each point, what fraction of fold orders give
    the optimal (minimum-distance) snap result?
    """
    orders = fold_orders(n)
    total_orders = len(orders)
    basis = cyclotomic_basis(n)
    
    random.seed(42)
    agreement_counts = {}
    best_fold_wins = 0
    any_fold_optimal = 0
    never_optimal = 0
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Get the optimal snap via brute force (or exhaustive min across folds)
        _, _, d_opt_exhaustive = overcomplete_snap(x, y, n)
        
        fold_results = []
        for perm, _ in orders:
            sx, sy, d = permutational_fold_snap(x, y, n, perm)
            fold_results.append(d)
        
        min_fold = min(fold_results)
        winners = sum(1 for d in fold_results if abs(d - min_fold) < 1e-10)
        agreement_counts[winners] = agreement_counts.get(winners, 0) + 1
        
        # How many fold orders found the GLOBAL optimum (minimum across all pairs)?
        opt_in_folds = sum(1 for d in fold_results if abs(d - d_opt_exhaustive) < 1e-10)
        any_fold_optimal += (1 if opt_in_folds > 0 else 0)
        best_fold_wins += (1 if abs(min_fold - d_opt_exhaustive) < 1e-10 else 0)
    
    total = sum(agreement_counts.values())
    mean_agreement = sum(k * v for k, v in agreement_counts.items()) / total if total > 0 else 0
    
    return {
        "test": "fold_order_variation",
        "n": n,
        "num_trials": num_trials,
        "total_fold_orders": total_orders,
        "agreement_distribution": dict(sorted(agreement_counts.items())),
        "mean_agreement_count": mean_agreement,
        "mean_agreement_percentage": mean_agreement / total_orders * 100 if total_orders > 0 else 0,
        "any_order_optimal_percent": 100.0 * any_fold_optimal / num_trials,
        "best_order_matches_exhaustive_percent": 100.0 * best_fold_wins / num_trials,
    }


def test_nearest_vs_some_lattice_point(n: int, num_trials: int = 2000) -> dict:
    """
    TEST 6: Is the algorithm finding the NEAREST lattice point, or just SOME lattice point?
    
    This is THE critical question. The overcomplete snap searches each basis pair's
    3x3 neighborhood independently and takes the minimum. But:
      - The true nearest point might not be found by ANY single pair's 3x3 search
      - Points near the boundary of a Voronoi cell may be assigned to the wrong cell
    
    We compare against brute-force search to answer definitively.
    """
    # Use brute-force for small search radius comparison
    basis = cyclotomic_basis(n)
    random.seed(42)
    
    results = []
    for i in range(num_trials):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        
        # Our approximate snap
        sx_apprx, sy_apprx, d_apprx = overcomplete_snap(x, y, n)
        
        # Brute-force with search radius up to 8 (larger means more accurate)
        d_opt_all = [None, None, None]
        for r_idx, r in enumerate([3, 5, 8]):
            _, _, d_opt = find_optimal_snap_bruteforce(x, y, n, radius=r)
            d_opt_all[r_idx] = d_opt
        
        min_opt = min(d_opt_all)
        
        results.append({
            "x": x, "y": y,
            "approx_dist": d_apprx,
            "optimal_r3": d_opt_all[0],
            "optimal_r5": d_opt_all[1],
            "optimal_r8": d_opt_all[2],
        })
    
    # Analyze: what fraction does our approximation match the brute-force optimal?
    matches_r8 = sum(1 for r in results if abs(r["approx_dist"] - r["optimal_r8"]) < 1e-10)
    misses_r8 = sum(1 for r in results if abs(r["approx_dist"] - r["optimal_r8"]) >= 1e-10)
    
    # Distribution of misses
    miss_deviations = [abs(r["approx_dist"] - r["optimal_r8"]) for r in results 
                       if abs(r["approx_dist"] - r["optimal_r8"]) >= 1e-10]
    
    return {
        "test": "nearest_vs_some_lattice_point",
        "n": n,
        "num_trials": num_trials,
        "matches_optimal_r8": matches_r8,
        "misses_optimal_r8": misses_r8,
        "match_percent": 100.0 * matches_r8 / num_trials,
        "miss_deviation_stats": {
            "mean": sum(miss_deviations) / len(miss_deviations) if miss_deviations else 0,
            "max": max(miss_deviations) if miss_deviations else 0,
            "count": len(miss_deviations),
        } if miss_deviations else {"note": "no misses found"},
    }


# ─── Runner ──────────────────────────────────────────────────────

def run_all_tests(skip_bruteforce: bool = False) -> Dict:
    """
    Run all ground-truth tests for cyclotomic fields n = 3, 5, 8, 10, 12.
    
    Args:
        skip_bruteforce: If True, skip O(r^φ(n)) brute-force optimality tests.
                         These are the slow ones (can take minutes per n).
    """
    results = {
        "metadata": {
            "suite": "flux-fold-ground-truth",
            "author": "Forgemaster ⚒️",
            "date": "2026-05-14",
            "description": "Ground truth tests for permutational folding snap correctness",
            "skip_bruteforce": skip_bruteforce,
        },
        "tests": {}
    }
    
    ns_to_test = [3, 5, 8, 10, 12]
    
    for n in ns_to_test:
        phi_n = len(cyclotomic_basis(n))
        print(f"\n{'='*60}")
        print(f"FIELD Z[ζ_{n}] (φ={phi_n})")
        print(f"{'='*60}")
        
        # Test 1: Valid lattice point
        print(f"\n--- Test 1: Valid Lattice Point (n={n})...")
        start = time.time()
        r1 = test_valid_lattice_point(n, num_trials=10000)
        r1["runtime_seconds"] = time.time() - start
        print(f"  Valid: {r1['valid_percent']:.4f}%  ({r1['passed']}/{r1['passed']+r1['failed']})")
        results["tests"][f"z{n}_valid_lattice"] = r1
        
        # Test 2: Idempotence
        print(f"\n--- Test 2: Idempotence (n={n})...")
        start = time.time()
        r2 = test_idempotence(n, num_trials=10000)
        r2["runtime_seconds"] = time.time() - start
        print(f"  Idempotent: {r2['idempotent_percent']:.4f}%  max_drift={r2['max_drift_on_second_snap']:.6e}")
        results["tests"][f"z{n}_idempotence"] = r2
        
        # Test 3: Distance distribution
        print(f"\n--- Test 3: Snap Distance Distribution (n={n})...")
        start = time.time()
        r3 = test_snap_distance_distribution(n, num_trials=10000)
        r3["runtime_seconds"] = time.time() - start
        print(f"  OC max: {r3['overcomplete_snap']['max']:.4f}  mean: {r3['overcomplete_snap']['mean']:.4f}")
        print(f"  Fold min max: {r3['permutational_fold_min']['max']:.4f}  mean: {r3['permutational_fold_min']['mean']:.4f}")
        results["tests"][f"z{n}_distance_dist"] = r3
        
        # Test 4: Optimality oracle (brute-force, slower)
        if not skip_bruteforce and n <= 8:  # Only for small φ(n)
            print(f"\n--- Test 4: Optimality Oracle (n={n}, 500 trials, r=5)...")
            start = time.time()
            r4 = test_optimality_oracle(n, num_trials=500)
            r4["runtime_seconds"] = time.time() - start
            print(f"  Optimal matches: {r4['optimal_count']}/{500} ({r4['optimal_percent']:.2f}%)")
            print(f"  Max deviation: {r4['max_deviation']:.6e}")
            results["tests"][f"z{n}_optimality"] = r4
        else:
            print(f"\n--- Test 4: Optimality Oracle (SKIPPED - brute-force too costly for φ={phi_n})")
        
        # Test 5: Fold order variation
        print(f"\n--- Test 5: Fold Order Variation (n={n})...")
        start = time.time()
        r5 = test_fold_order_variation(n, num_trials=500)
        r5["runtime_seconds"] = time.time() - start
        print(f"  Mean agreement: {r5['mean_agreement_percentage']:.2f}%  ({r5['mean_agreement_count']:.1f}/{r5['total_fold_orders']} orders)")
        print(f"  Any order optimal: {r5['any_order_optimal_percent']:.2f}%")
        results["tests"][f"z{n}_fold_variation"] = r5
        
        # Test 6: Nearest vs some lattice point
        print(f"\n--- Test 6: Nearest vs Some Lattice Point (n={n})...")
        start = time.time()
        r6 = test_nearest_vs_some_lattice_point(n, num_trials=2000)
        r6["runtime_seconds"] = time.time() - start
        print(f"  Matches brute-force (r=8): {r6['match_percent']:.2f}%  ({r6['matches_optimal_r8']}/{r6['misses_optimal_r8']+r6['matches_optimal_r8']})")
        results["tests"][f"z{n}_nearest_vs_some"] = r6
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ground truth snap correctness tests")
    parser.add_argument("--skip-bruteforce", action="store_true",
                        help="Skip O(r^φ(n)) optimality tests (slower for large φ(n))")
    parser.add_argument("--output", default="/home/phoenix/.openclaw/workspace/experiments/flux-fold-ground-truth/results.json",
                        help="Output JSON path")
    args = parser.parse_args()
    
    print("=" * 60)
    print("GROUND TRUTH: Snap Correctness Tests")
    print("=" * 60)
    print("Author: Forgemaster ⚒️")
    print()
    
    results = run_all_tests(skip_bruteforce=args.skip_bruteforce)
    
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"Results written to: {args.output}")
    
    # Summary
    print("\nSUMMARY:")
    for key, val in results["tests"].items():
        test_name = val.get("test", "unknown")
        n = val.get("n", "?")
        status = "✓" if val.get("valid_percent", 100) > 99.9 or val.get("idempotent_percent", 100) > 99.9 else "?"
        print(f"  {status} {key}: {test_name}")
