#!/usr/bin/env python3
"""
test_eisenstein_comparison.py — GROUND TRUTH: Head-to-head against Eisenstein.

The most important comparison: does permutational folding on cyclotomic
fields Z[ζₙ] give BETTER snap results than the standard Eisenstein snap?

We compare on identical points and report HONEST statistics.

Core metrics:
  1. MAX covering radius — the theoretical maximum distance to nearest lattice point
  2. MEAN snap distance — typical performance  
  3. P95/P99 — tail behavior
  4. Worst-case drift — largest deviation from true nearest lattice point

The metric that MATTERS: does the cyclotomic snap give a smaller distance
to the nearest lattice point? If yes, we have tighter constraint checking.
If no, the entire overcomplete approach is wasted effort.

Author: Forgemaster ⚒️
Date: 2026-05-14
"""

import math
import random
import sys
import json
import time
from typing import Dict, List, Tuple

sys.path.insert(0, "/home/phoenix/.openclaw/workspace/experiments/flux-fold")
from vm import (
    cyclotomic_basis, eisenstein_snap, overcomplete_snap, permutational_fold_snap,
    fold_orders, exhaustive_min_snap, basis_pairs
)


def test_eisenstein_vs_cyclotomic(n: int, num_trials: int = 10000) -> dict:
    """
    HEAD-TO-HEAD: Eisenstein snap vs cyclotomic snap on identical random points.
    
    Measures:
      - Both on same points
      - Which gives smaller snap distance?
      - By how much?
      - How often does cyclotomic win? Lose? Tie?
    """
    random.seed(42)
    eisenstein_dists = []
    cyclotomic_dists = []
    fold_min_dists = []
    cyclotomic_wins = 0
    eisenstein_wins = 0
    tie = 0
    cyclotomic_improvements = []
    eisenstein_improvements = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Eisenstein snap
        es = eisenstein_snap(x, y)
        e_x = es[0] - es[1] * 0.5
        e_y = es[1] * math.sqrt(3) * 0.5
        d_eisenstein = math.hypot(e_x - x, e_y - y)
        
        # Cyclotomic overcomplete snap
        oc_x, oc_y, d_cyclotomic = overcomplete_snap(x, y, n)
        
        # Permutational fold min
        _, _, _, _, all_fold_dists = exhaustive_min_snap(x, y, n)
        d_fold_min = min(all_fold_dists)
        
        eisenstein_dists.append(d_eisenstein)
        cyclotomic_dists.append(d_cyclotomic)
        fold_min_dists.append(d_fold_min)
        
        if d_cyclotomic < d_eisenstein - 1e-12:
            cyclotomic_wins += 1
            cyclotomic_improvements.append((d_eisenstein - d_cyclotomic) / d_eisenstein)
        elif d_eisenstein < d_cyclotomic - 1e-12:
            eisenstein_wins += 1
            eisenstein_improvements.append((d_cyclotomic - d_eisenstein) / d_cyclotomic)
        else:
            tie += 1
    
    eisenstein_dists.sort()
    cyclotomic_dists.sort()
    
    return {
        "test": "eisenstein_vs_cyclotomic_head_to_head",
        "n": n,
        "num_trials": num_trials,
        "eisenstein": {
            "max": max(eisenstein_dists),
            "min": min(eisenstein_dists),
            "mean": sum(eisenstein_dists) / len(eisenstein_dists),
            "median": eisenstein_dists[len(eisenstein_dists)//2],
            "p95": eisenstein_dists[int(0.95 * len(eisenstein_dists))],
            "p99": eisenstein_dists[int(0.99 * len(eisenstein_dists))],
        },
        "cyclotomic_overcomplete": {
            "max": max(cyclotomic_dists),
            "min": min(cyclotomic_dists),
            "mean": sum(cyclotomic_dists) / len(cyclotomic_dists),
            "median": cyclotomic_dists[len(cyclotomic_dists)//2],
            "p95": cyclotomic_dists[int(0.95 * len(cyclotomic_dists))],
            "p99": cyclotomic_dists[int(0.99 * len(cyclotomic_dists))],
        },
        "head_to_head": {
            "cyclotomic_wins": cyclotomic_wins,
            "eisenstein_wins": eisenstein_wins,
            "ties": tie,
            "cyclotomic_win_pct": 100.0 * cyclotomic_wins / num_trials,
            "eisenstein_win_pct": 100.0 * eisenstein_wins / num_trials,
            "mean_improvement_when_cyclotomic_wins": (
                sum(cyclotomic_improvements) / len(cyclotomic_improvements) 
                if cyclotomic_improvements else 0
            ),
            "mean_improvement_when_eisenstein_wins": (
                sum(eisenstein_improvements) / len(eisenstein_improvements)
                if eisenstein_improvements else 0
            ),
        }
    }


def test_eisenstein_best_case_for_overcomplete(n: int, num_trials: int = 5000) -> dict:
    """
    When does the overcomplete approach actually beat Eisenstein?
    
    We find the conditions where cyclotomic gives a tighter snap:
      - Near-lattice points? (shouldn't matter — both will find exact lattice point)
      - Mid-cell points? (should matter — overcomplete has denser coverage)
      - Specific barycentric coordinates?
    
    This identifies the REGIME where overcomplete is worth the extra computation.
    """
    random.seed(42)
    
    # Sample points systematically across the Voronoi cell
    # For Eisenstein, the fundamental domain is a rhombus with side length 1
    # Sample points within the hexagonal Voronoi cell
    
    best_for_cyclotomic = []
    best_for_eisenstein = []
    
    for i in range(num_trials):
        # Sample near the origin (center of a cell)
        x = random.uniform(-0.3, 0.3)
        y = random.uniform(-0.3, 0.3)
        
        es = eisenstein_snap(x, y)
        e_x = es[0] - es[1] * 0.5
        e_y = es[1] * math.sqrt(3) * 0.5
        d_e = math.hypot(e_x - x, e_y - y)
        
        oc_x, oc_y, d_oc = overcomplete_snap(x, y, n)
        
        if d_oc < d_e - 1e-12:
            best_for_cyclotomic.append({
                "x": x, "y": y, "d_e": d_e, "d_oc": d_oc
            })
        elif d_e < d_oc - 1e-6:
            best_for_eisenstein.append({
                "x": x, "y": y, "d_e": d_e, "d_oc": d_oc
            })
    
    # Now test near cell boundaries (50% offset from origin)
    # These are the points LEAST likely to be near a lattice point
    boundary_wins = {"cyclotomic": 0, "eisenstein": 0}
    
    for i in range(num_trials):
        # Points halfway between lattice points
        x = random.uniform(0.4, 0.6)
        y = random.uniform(0.4, 0.6)
        
        es = eisenstein_snap(x, y)
        e_x = es[0] - es[1] * 0.5
        e_y = es[1] * math.sqrt(3) * 0.5
        d_e = math.hypot(e_x - x, e_y - y)
        
        oc_x, oc_y, d_oc = overcomplete_snap(x, y, n)
        
        if d_oc < d_e - 1e-12:
            boundary_wins["cyclotomic"] += 1
        elif d_e < d_oc - 1e-6:
            boundary_wins["eisenstein"] += 1
    
    return {
        "test": "eisenstein_best_case_for_overcomplete",
        "n": n,
        "num_trials": num_trials,
        "near_origin_center": {
            "cyclotomic_better_than_eisenstein": len(best_for_cyclotomic),
            "eisenstein_better_than_cyclotomic": len(best_for_eisenstein),
        },
        "near_cell_boundary": {
            "cyclotomic_better_than_eisenstein": boundary_wins["cyclotomic"],
            "eisenstein_better_than_cyclotomic": boundary_wins["eisenstein"],
        },
        "sample_improvements": {
            "cyclotomic_best": sorted(
                best_for_cyclotomic, 
                key=lambda r: r["d_e"] - r["d_oc"], 
                reverse=True
            )[:5] if best_for_cyclotomic else [],
            "eisenstein_best": sorted(
                best_for_eisenstein,
                key=lambda r: r["d_oc"] - r["d_e"],
                reverse=True
            )[:5] if best_for_eisenstein else [],
        }
    }


def test_covering_radius_vs_eisenstein(n: int, num_trials: int = 20000) -> dict:
    """
    Measure the empirical covering radius of both approaches.
    
    The covering radius is the maximum distance from any point in the
    plane to the nearest lattice point. For Eisenstein it's 1/√3 ≈ 0.577.
    
    For cyclotomic fields, the theoretical covering radius depends on n:
      - Z[ζ₅]: overcomplete 4 vecs → tighter? 0.286 from previous?
      - Z[ζ₁₂]: 10 vecs → 0.373 from previous?
    
    We measure empirically by sampling uniformly in a bounded region
    and tracking the worst-case snap distance.
    
    WARNING: This is just an empirical upper bound. The true covering
    radius is the supremum over the ENTIRE plane, not just our samples.
    Our result is ≤ actual covering radius.
    """
    random.seed(42)
    
    # Eisenstein reference
    _, _, _, _, all_fold_dists_e = exhaustive_min_snap(0.3, 0.3, 3)
    
    # Actually compute Eisenstein covering radius properly
    max_d_eisenstein = 0.0
    total_d_eisenstein = 0.0
    eisenstein_dists = []
    
    max_d_cyclotomic = 0.0
    total_d_cyclotomic = 0.0
    cyclotomic_dists = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Eisenstein
        es = eisenstein_snap(x, y)
        e_x = es[0] - es[1] * 0.5
        e_y = es[1] * math.sqrt(3) * 0.5
        d_e = math.hypot(e_x - x, e_y - y)
        eisenstein_dists.append(d_e)
        max_d_eisenstein = max(max_d_eisenstein, d_e)
        total_d_eisenstein += d_e
        
        # Cyclotomic
        oc_x, oc_y, d_oc = overcomplete_snap(x, y, n)
        cyclotomic_dists.append(d_oc)
        max_d_cyclotomic = max(max_d_cyclotomic, d_oc)
        total_d_cyclotomic += d_oc
        
        if i % 5000 == 0 and i > 0:
            print(f"  ... {i}/{num_trials}: current max E={max_d_eisenstein:.4f} C={max_d_cyclotomic:.4f}")
    
    eisenstein_dists.sort()
    cyclotomic_dists.sort()
    
    return {
        "test": "empirical_covering_radius",
        "n": n,
        "num_trials": num_trials,
        "eisenstein_theoretical_radius": 1.0 / math.sqrt(3),
        "eisenstein_empirical": {
            "max_radius": max_d_eisenstein,
            "mean": total_d_eisenstein / num_trials,
            "median": eisenstein_dists[len(eisenstein_dists)//2],
            "p95": eisenstein_dists[int(0.95 * len(eisenstein_dists))],
            "p99": eisenstein_dists[int(0.99 * len(eisenstein_dists))],
        },
        "cyclotomic_empirical": {
            "max_radius": max_d_cyclotomic,
            "mean": total_d_cyclotomic / num_trials,
            "median": cyclotomic_dists[len(cyclotomic_dists)//2],
            "p95": cyclotomic_dists[int(0.95 * len(cyclotomic_dists))],
            "p99": cyclotomic_dists[int(0.99 * len(cyclotomic_dists))],
        },
        "improvement": {
            "max_radius_ratio": max_d_eisenstein / max_d_cyclotomic if max_d_cyclotomic > 0 else float('inf'),
            "mean_ratio": (total_d_eisenstein / num_trials) / (total_d_cyclotomic / num_trials) if total_d_cyclotomic > 0 else float('inf'),
        },
    }


def test_eisenstein_loses_big(n: int, num_trials: int = 10000) -> dict:
    """
    Find the points where Eisenstein performs worst and see if cyclotomic helps.
    
    The "worst" points for Eisenstein are those near the boundary of the 
    hexagonal Voronoi cell. These are where:
      - The distance to the nearest lattice point is ≈ 0.577 (the covering radius)
      - The point is equidistant from 2 or 3 lattice points
    
    Does the overcomplete approach actually help at these worst-case points?
    """
    random.seed(42)
    
    eisenstein_dists = []
    worst_eisenstein_points = []
    
    # First pass: find worst points for Eisenstein
    for i in range(num_trials * 2):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        es = eisenstein_snap(x, y)
        e_x = es[0] - es[1] * 0.5
        e_y = es[1] * math.sqrt(3) * 0.5
        d_e = math.hypot(e_x - x, e_y - y)
        
        if len(eisenstein_dists) < 1000:
            eisenstein_dists.append(d_e)
            
        if d_e > 0.5:  # Near covering radius
            worst_eisenstein_points.append((x, y, d_e))
    
    worst_eisenstein_points.sort(key=lambda p: p[2], reverse=True)
    worst_eisenstein_points = worst_eisenstein_points[:200]
    
    # Now check these worst-case points with cyclotomic
    results = []
    for x, y, d_e in worst_eisenstein_points:
        oc_x, oc_y, d_oc = overcomplete_snap(x, y, n)
        
        # Also check each basis pair individually
        pair_dists = []
        for _, _, vi, vj in basis_pairs(n):
            det = vi.real * vj.imag - vi.imag * vj.real
            if abs(det) < 1e-15:
                continue
            a = (x * vj.imag - y * vj.real) / det
            b = (vi.real * y - vi.imag * x) / det
            a_int, b_int = round(a), round(b)
            for da in [-1, 0, 1]:
                for db in [-1, 0, 1]:
                    aa = a_int + da
                    bb = b_int + db
                    rx = aa * vi.real + bb * vj.real
                    ry = aa * vi.imag + bb * vj.imag
                    d = math.hypot(rx - x, ry - y)
                    pair_dists.append(d)
        
        min_pair = min(pair_dists)
        
        results.append({
            "x": x, "y": y,
            "eisenstein_distance": d_e,
            "cyclotomic_overcomplete_distance": d_oc,
            "best_single_pair_distance": min_pair,
            "cyclotomic_improvement": d_e - d_oc,
            "cyclotomic_wins": d_oc < d_e - 1e-12,
        })
    
    # Analysis
    cyclotomic_wins_in_worst = sum(1 for r in results if r["cyclotomic_wins"])
    improvements = [r["cyclotomic_improvement"] for r in results if r["cyclotomic_wins"]]
    worsening = [r["cyclotomic_improvement"] for r in results if not r["cyclotomic_wins"] and abs(r["eisenstein_distance"] - r["cyclotomic_overcomplete_distance"]) > 1e-12]
    
    return {
        "test": "eisenstein_loses_big",
        "n": n,
        "worst_eisenstein_points_checked": len(results),
        "cyclotomic_improves_in_worst_case": cyclotomic_wins_in_worst,
        "cyclotomic_improvement_pct_in_worst": 100.0 * cyclotomic_wins_in_worst / len(results) if results else 0,
        "mean_improvement_at_worst": sum(improvements) / len(improvements) if improvements else 0,
        "mean_worsening_at_worst": abs(sum(worsening) / len(worsening)) if worsening else 0,
        "net_improvement_at_worst": sum(r["cyclotomic_improvement"] for r in results) / len(results) if results else 0,
        "sample_worst_results": sorted(results, key=lambda r: r["eisenstein_distance"], reverse=True)[:10],
    }


def run_all_tests() -> Dict:
    """Run all Eisenstein comparison tests."""
    print("=" * 60)
    print("GROUND TRUTH: Eisenstein Comparison Tests")
    print("=" * 60)
    
    results = {
        "metadata": {
            "suite": "flux-fold-ground-truth",
            "author": "Forgemaster ⚒️",
            "date": "2026-05-14",
            "description": "Honest head-to-head: cyclotomic folding vs Eisenstein snap",
        },
        "tests": {}
    }
    
    for n in [3, 5, 8, 10, 12]:
        phi_n = len(cyclotomic_basis(n))
        print(f"\n{'='*60}")
        print(f"FIELD Z[ζ_{n}] VS EISENSTEIN (φ={phi_n})")
        print(f"{'='*60}")
        
        # Test 1: Head-to-head
        print(f"\n--- Test 1: Head-to-Head (n={n})...")
        start = time.time()
        r1 = test_eisenstein_vs_cyclotomic(n, num_trials=10000)
        r1["runtime_seconds"] = time.time() - start
        h = r1["head_to_head"]
        print(f"  Cyclotomic wins: {h['cyclotomic_win_pct']:.2f}%")
        print(f"  Eisenstein wins:  {h['eisenstein_win_pct']:.2f}%")
        print(f"  Ties: {h['ties']}")
        print(f"  Mean improvement when C wins: {h['mean_improvement_when_cyclotomic_wins']:.2%}")
        print(f"  Mean improvement when E wins: {h['mean_improvement_when_eisenstein_wins']:.2%}")
        results["tests"][f"z{n}_vs_eisenstein"] = r1
        
        # Test 2: Best case for overcomplete
        print(f"\n--- Test 2: Best Case for Overcomplete (n={n})...")
        start = time.time()
        r2 = test_eisenstein_best_case_for_overcomplete(n, num_trials=5000)
        r2["runtime_seconds"] = time.time() - start
        print(f"  Near origin — C better: {r2['near_origin_center']['cyclotomic_better_than_eisenstein']}, "
              f"E better: {r2['near_origin_center']['eisenstein_better_than_cyclotomic']}")
        print(f"  Near boundary — C better: {r2['near_cell_boundary']['cyclotomic_better_than_eisenstein']}, "
              f"E better: {r2['near_cell_boundary']['eisenstein_better_than_cyclotomic']}")
        results["tests"][f"z{n}_best_case"] = r2
        
        # Test 3: Covering radius
        print(f"\n--- Test 3: Empirical Covering Radius (n={n})...")
        start = time.time()
        r3 = test_covering_radius_vs_eisenstein(n, num_trials=20000)
        r3["runtime_seconds"] = time.time() - start
        print(f"  Eisenstein max: {r3['eisenstein_empirical']['max_radius']:.4f} "
              f"(theoretical: {r3['eisenstein_theoretical_radius']:.4f})")
        print(f"  Cyclotomic max: {r3['cyclotomic_empirical']['max_radius']:.4f}")
        print(f"  Max radius ratio (E/C): {r3['improvement']['max_radius_ratio']:.3f}x")
        print(f"  Mean ratio (E/C): {r3['improvement']['mean_ratio']:.3f}x")
        results["tests"][f"z{n}_covering_radius"] = r3
        
        # Test 4: Worst-case improvement
        print(f"\n--- Test 4: Worst-Case Improvement at Boundary (n={n})...")
        start = time.time()
        r4 = test_eisenstein_loses_big(n, num_trials=10000)
        r4["runtime_seconds"] = time.time() - start
        print(f"  Cyclotomic improves worst-case Eisenstein: {r4['cyclotomic_improvement_pct_in_worst']:.2f}%")
        print(f"  Mean improvement at worst: {r4['mean_improvement_at_worst']:.4f}")
        print(f"  Net improvement: {r4['net_improvement_at_worst']:.4f}")
        results["tests"][f"z{n}_worst_case"] = r4
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    
    outpath = "/home/phoenix/.openclaw/workspace/experiments/flux-fold-ground-truth/results_eisenstein.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"Results written to: {outpath}")
