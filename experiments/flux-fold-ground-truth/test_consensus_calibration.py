#!/usr/bin/env python3
"""
test_consensus_calibration.py — GROUND TRUTH: Is consensus calibrated uncertainty?

The hypothesis: low consensus among fold orders predicts high snap error.
If true, we can use agreement counts as a FREE uncertainty signal.

The hard questions:
  1. Is the correlation real, or is it an artifact of poor snap choices?
  2. Is the calibration sharp? (Does k/24 really mean 95th-percentile?)
  3. Does it beat simpler uncertainty estimates (e.g., residual magnitude)?
  4. Can we predict which fold orders to use via consensus?

Author: Forgemaster ⚒️
Date: 2026-05-14
"""

import math
import random
import sys
import json
import time
from typing import Dict, List, Tuple
from collections import defaultdict

sys.path.insert(0, "/home/phoenix/.openclaw/workspace/experiments/flux-fold")
from vm import (
    cyclotomic_basis, overcomplete_snap, permutational_fold_snap, fold_orders,
    exhaustive_min_snap, basis_pairs
)

# ─── Consensus calibration ──────────────────────────────────────

def test_consensus_error_correlation(n: int, num_trials: int = 5000) -> dict:
    """
    TEST 1: Is low fold-order consensus correlated with high snap error?
    
    For each point:
      - Compute snap distance (error)
      - Compute number of fold orders agreeing on the best result
      - Are they correlated? (Pearson r, rank correlation)
    """
    orders = fold_orders(n)
    total_orders = len(orders)
    
    random.seed(42)
    data_points = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Fold results for all orders
        fold_dists = []
        for perm, _ in orders:
            _, _, d = permutational_fold_snap(x, y, n, perm)
            fold_dists.append(d)
        
        min_d = min(fold_dists)
        winners = sum(1 for d in fold_dists if abs(d - min_d) < 1e-12)
        
        # Also compute the second-best agreement (are we close to consensus?)
        sorted_d = sorted(fold_dists)
        # Secondary consensus: how many land in the top 10%?
        threshold = sorted_d[max(1, total_orders // 10)]
        top10_count = sum(1 for d in fold_dists if d <= threshold)
        
        # Also compute variance of fold distances
        mean_d = sum(fold_dists) / len(fold_dists)
        var_d = sum((d - mean_d) ** 2 for d in fold_dists) / len(fold_dists)
        
        data_points.append({
            "x": x, "y": y,
            "snap_error": min_d,
            "consensus_count": winners,
            "consensus_ratio": winners / total_orders,
            "top10_agreement": top10_count / total_orders,
            "fold_variance": var_d,
            "fold_mean": mean_d,
        })
    
    # Correlation analysis
    errors = [d["snap_error"] for d in data_points]
    consensuses = [d["consensus_ratio"] for d in data_points]
    variances = [d["fold_variance"] for d in data_points]
    
    # Binned analysis: for each consensus level, what's the error?
    consensus_bins = defaultdict(list)
    for d in data_points:
        # Bin by consensus ratio (0-1 in 0.1 intervals)
        bin_key = round(d["consensus_ratio"] * 10) / 10
        consensus_bins[bin_key].append(d["snap_error"])
    
    binned_errors = {}
    for bin_key, errs in sorted(consensus_bins.items()):
        binned_errors[f"{bin_key:.1f}"] = {
            "count": len(errs),
            "mean_error": sum(errs) / len(errs),
            "max_error": max(errs),
            "p95_error": sorted(errs)[int(0.95 * len(errs))],
        }
    
    # Calibration test: does low consensus predict high error?
    # Check: what percentile error does the lowest-consensus bin have?
    low_consensus_points = [d for d in data_points if d["consensus_ratio"] < 0.5]
    high_consensus_points = [d for d in data_points if d["consensus_ratio"] > 0.8]
    
    low_mean = sum(d["snap_error"] for d in low_consensus_points) / len(low_consensus_points) if low_consensus_points else 0
    high_mean = sum(d["snap_error"] for d in high_consensus_points) / len(high_consensus_points) if high_consensus_points else 0
    
    # Pearson-like correlation (rank-based, more robust)
    from statistics import correlation
    # Use rank correlation via sorted positions
    error_ranks = [sorted(errors).index(e) for e in errors]
    cons_ranks = [sorted(consensuses).index(c) for c in consensuses]
    
    n = len(error_ranks)
    mean_er = n / 2
    mean_cr = n / 2
    
    # Spearman rank correlation
    num = sum((e - mean_er) * (c - mean_cr) for e, c in zip(error_ranks, cons_ranks))
    denom_e = math.sqrt(sum((e - mean_er)**2 for e in error_ranks))
    denom_c = math.sqrt(sum((c - mean_cr)**2 for c in cons_ranks))
    
    spearman_r = num / (denom_e * denom_c) if denom_e * denom_c > 0 else 0
    
    return {
        "test": "consensus_error_correlation",
        "n": n,
        "num_trials": num_trials,
        "spearman_rank_correlation_r": spearman_r,
        "negative_correlation_expected": spearman_r < 0,  # lower consensus → higher error
        "low_consensus_mean_error": low_mean,
        "high_consensus_mean_error": high_mean,
        "error_ratio_low_to_high": low_mean / high_mean if high_mean > 0 else float('inf'),
        "binned_errors": binned_errors,
        "calibration_quality": {
            "monotonic_decreasing": all(
                binned_errors.get(f"{k:.1f}", {}).get("mean_error", 0) >=
                binned_errors.get(f"{(k+1)/10:.1f}", {}).get("mean_error", 0)
                for k in range(0, 9)
            ) if len(binned_errors) >= 2 else False,
        }
    }


def test_residual_vs_consensus(n: int, num_trials: int = 5000) -> dict:
    """
    TEST 2: Is consensus better than a naive residual-based uncertainty estimate?
    
    Compare:
      - Consensus uncertainty: 1 - (agreement count / total orders)
      - Residual uncertainty: fold variance across orders
      - Distance uncertainty: distance to second-best fold result
    
    Which predicts actual snap error best?
    """
    orders = fold_orders(n)
    total_orders = len(orders)
    
    random.seed(42)
    comparisons = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        # Get all fold results
        fold_dists = []
        for perm, _ in orders:
            _, _, d = permutational_fold_snap(x, y, n, perm)
            fold_dists.append(d)
        
        # Sorted for analysis
        sorted_d = sorted(fold_dists)
        min_d = sorted_d[0]
        second_min_d = sorted_d[1] if len(sorted_d) > 1 else min_d
        
        # Consensus
        winners = sum(1 for d in fold_dists if abs(d - min_d) < 1e-12)
        consensus = winners / total_orders
        
        # Residual-based: sum of fold residuals
        # (This is the remaining magnitude after sequential projection)
        residuals = []
        for perm, _ in orders:
            _, _, d = permutational_fold_snap(x, y, n, perm)
            residuals.append(d)
        mean_residual = sum(residuals) / len(residuals)
        max_residual = max(residuals)
        
        # Gap-based: distance between best and second-best
        gap = abs(sorted_d[0] - sorted_d[1]) if len(sorted_d) > 1 else 0
        
        # Which predicts actual error?
        comparisons.append({
            "actual_error": min_d,
            "consensus_uncertainty": 1 - consensus,
            "residual_mean": mean_residual,
            "residual_max": max_residual,
            "gap_to_second_best": gap,
        })
    
    # For each uncertainty measure, compute the rank correlation with actual error
    def rank_corr(actual: List[float], predicted: List[float]) -> float:
        """Spearman rank correlation between actual and predicted."""
        n = len(actual)
        if n < 10:
            return 0.0
        actual_ranks = [sorted(actual).index(v) for v in actual]
        pred_ranks = [sorted(predicted).index(v) for v in predicted]
        mean_ar = n / 2
        mean_pr = n / 2
        num = sum((a - mean_ar) * (p - mean_pr) for a, p in zip(actual_ranks, pred_ranks))
        denom_a = math.sqrt(sum((a - mean_ar)**2 for a in actual_ranks))
        denom_p = math.sqrt(sum((p - mean_pr)**2 for p in pred_ranks))
        return num / (denom_a * denom_p) if denom_a * denom_p > 0 else 0
    
    actuals = [c["actual_error"] for c in comparisons]
    consensus_unc = [c["consensus_uncertainty"] for c in comparisons]
    residual_max = [c["residual_max"] for c in comparisons]
    gap_to_second = [c["gap_to_second_best"] for c in comparisons]
    
    return {
        "test": "residual_vs_consensus",
        "n": n,
        "num_trials": num_trials,
        "rank_correlations": {
            "consensus_uncertainty": rank_corr(actuals, consensus_unc),
            "residual_max": rank_corr(actuals, residual_max),
            "gap_to_second_best": rank_corr(actuals, gap_to_second),
        },
        "best_predictor": max(
            ["consensus", "residual", "gap"],
            key=lambda x: {
                "consensus": rank_corr(actuals, consensus_unc),
                "residual": rank_corr(actuals, residual_max),
                "gap": rank_corr(actuals, gap_to_second),
            }[x]
        ),
    }


def test_consensus_calibration_curve(n: int, num_trials: int = 10000) -> dict:
    """
    TEST 3: The calibration curve.
    
    A well-calibrated uncertainty estimate means:
      - When C=80% (4/5 orders agree), the true error is below some threshold 80% of the time
      - When C=50%, the true error exceeds a threshold 50% of the time
    
    We construct the calibration curve: for each consensus level k/N,
    what's the empirical probability that the actual snap error is
    in the top 10% of errors?
    """
    orders = fold_orders(n)
    total_orders = len(orders)
    
    random.seed(42)
    data_by_consensus = defaultdict(list)
    all_errors = []
    
    for i in range(num_trials):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        fold_dists = []
        for perm, _ in orders:
            _, _, d = permutational_fold_snap(x, y, n, perm)
            fold_dists.append(d)
        
        min_d = min(fold_dists)
        all_errors.append(min_d)
        
        winners = sum(1 for d in fold_dists if abs(d - min_d) < 1e-12)
        consensus_key = winners  # raw count, not ratio
        
        data_by_consensus[consensus_key].append(min_d)
    
    # Determine error thresholds
    sorted_all = sorted(all_errors)
    p90_threshold = sorted_all[int(0.90 * len(sorted_all))]
    p95_threshold = sorted_all[int(0.95 * len(sorted_all))]
    p99_threshold = sorted_all[int(0.99 * len(sorted_all))]
    
    calibration_points = {}
    for k in sorted(data_by_consensus.keys()):
        errs = data_by_consensus[k]
        calibration_points[str(k)] = {
            "count": len(errs),
            "pct_above_p90": 100.0 * sum(1 for e in errs if e > p90_threshold) / len(errs),
            "pct_above_p95": 100.0 * sum(1 for e in errs if e > p95_threshold) / len(errs),
            "pct_above_p99": 100.0 * sum(1 for e in errs if e > p99_threshold) / len(errs),
            "mean_error": sum(errs) / len(errs),
            "max_error": max(errs),
        }
    
    return {
        "test": "consensus_calibration_curve",
        "n": n,
        "num_trials": num_trials,
        "total_fold_orders": total_orders,
        "error_thresholds": {
            "p90": p90_threshold,
            "p95": p95_threshold,
            "p99": p99_threshold,
        },
        "calibration": calibration_points,
        "summary": {
            "low_consensus_high_error_rate": (
                sum(1 for d in data_by_consensus.get(1, []) if d > p95_threshold) /
                max(1, len(data_by_consensus.get(1, [])))
            * 100) if 1 in data_by_consensus else 0,
            "high_consensus_low_error_rate": (
                sum(1 for d in data_by_consensus.get(total_orders, []) if d < p90_threshold) /
                max(1, len(data_by_consensus.get(total_orders, [])))
            * 100) if total_orders in data_by_consensus else 0,
        }
    }


def test_consensus_edge_cases(n: int, num_trials: int = 3000) -> dict:
    """
    TEST 4: Edge cases where consensus might fail.
    
    Specific cases to check:
      - Points near lattice points (should have high consensus, low error)
      - Points near cell boundaries (should have low consensus, high error)
      - Points in symmetric configurations (consensus might be artificially high)
      - Computational corner cases (numerical precision, periodic boundaries)
    """
    orders = fold_orders(n)
    total_orders = len(orders)
    
    # Test cases
    test_cases = []
    
    # 1. Near known lattice points (should be high consensus)
    basis = cyclotomic_basis(n)
    for c0 in range(-2, 3):
        for c1 in range(-2, 3):
            if len(basis) >= 2:
                z_lattice = c0 * basis[0] + c1 * basis[1]
                # Small perturbation
                for dx in [1e-6, 0.001, 0.01, 0.1]:
                    test_cases.append({
                        "x": z_lattice.real + dx,
                        "y": z_lattice.imag + dx * 0.5,
                        "category": "near_lattice",
                        "expected_consensus": "high" if dx < 0.01 else "medium"
                    })
    
    # 2. Near Voronoi cell boundaries
    cell_midpoints = [
        (0.3, 0.3), (-0.3, 0.5), (0.5, -0.3), (-0.4, -0.4),
        (0.7, 0.1), (-0.6, 0.7), (0.8, -0.5), (-0.7, -0.2),
    ]
    for cx, cy in cell_midpoints:
        test_cases.append({
            "x": cx, "y": cy,
            "category": "cell_boundary",
            "expected_consensus": "low"
        })
    
    # 3. Known bad regions from previous experiments
    # (Regions where permutational folding showed worst agreement)
    known_bad = [
        (2.5, 1.8), (-1.3, -2.7), (3.7, -1.2), (-3.4, 0.9),
        (0.0, 0.0),  # Exactly at origin
        (1.0, 0.0),  # On an axis
        (0.0, 1.0),  # On another axis
    ]
    for cx, cy in known_bad:
        test_cases.append({
            "x": cx, "y": cy,
            "category": "known_bad",
            "expected_consensus": "unknown"
        })
    
    # Now test all cases
    results = []
    for tc in test_cases:
        x, y = tc["x"], tc["y"]
        fold_dists = []
        for perm, _ in orders:
            _, _, d = permutational_fold_snap(x, y, n, perm)
            fold_dists.append(d)
        
        min_d = min(fold_dists)
        winners = sum(1 for d in fold_dists if abs(d - min_d) < 1e-10)
        
        results.append({
            **tc,
            "snap_error": min_d,
            "consensus_count": winners,
            "consensus_ratio": winners / total_orders,
        })
    
    # Analyze by category
    by_category = defaultdict(list)
    for r in results:
        by_category[r["category"]].append(r)
    
    category_stats = {}
    for cat, items in by_category.items():
        consensus_ratios = [i["consensus_ratio"] for i in items]
        errors = [i["snap_error"] for i in items]
        category_stats[cat] = {
            "count": len(items),
            "mean_consensus": sum(consensus_ratios) / len(consensus_ratios),
            "mean_error": sum(errors) / len(errors),
            "max_error": max(errors),
        }
    
    return {
        "test": "consensus_edge_cases",
        "n": n,
        "num_test_cases": len(test_cases),
        "category_stats": category_stats,
        "worst_case": max(results, key=lambda r: r["snap_error"]) if results else None,
    }


def run_all_tests() -> Dict:
    """Run all consensus calibration tests."""
    print("=" * 60)
    print("GROUND TRUTH: Consensus Calibration Tests")
    print("=" * 60)
    
    results = {
        "metadata": {
            "suite": "flux-fold-ground-truth",
            "author": "Forgemaster ⚒️",
            "date": "2026-05-14",
            "description": "Is fold-order consensus a calibrated uncertainty signal?",
        },
        "tests": {}
    }
    
    for n in [3, 5, 8, 10, 12]:
        phi_n = len(cyclotomic_basis(n))
        print(f"\n{'='*60}")
        print(f"FIELD Z[ζ_{n}] (φ={phi_n})")
        print(f"{'='*60}")
        
        # Test 1: Correlation
        print(f"\n--- Test 1: Consensus-Error Correlation (n={n})...")
        start = time.time()
        r1 = test_consensus_error_correlation(n, num_trials=5000)
        r1["runtime_seconds"] = time.time() - start
        print(f"  Spearman r: {r1['spearman_rank_correlation_r']:.4f}  "
              f"(neg expected: {r1['negative_correlation_expected']})")
        print(f"  Low-consensus mean: {r1['low_consensus_mean_error']:.4f}, "
              f"High-consensus mean: {r1['high_consensus_mean_error']:.4f}")
        print(f"  Ratio L/H: {r1['error_ratio_low_to_high']:.2f}x")
        results["tests"][f"z{n}_consensus_corr"] = r1
        
        # Test 2: Residual vs Consensus
        print(f"\n--- Test 2: Residual vs Consensus (n={n})...")
        start = time.time()
        r2 = test_residual_vs_consensus(n, num_trials=5000)
        r2["runtime_seconds"] = time.time() - start
        print(f"  Consensus rank corr: {r2['rank_correlations']['consensus_uncertainty']:.4f}")
        print(f"  Residual max rank corr: {r2['rank_correlations']['residual_max']:.4f}")
        print(f"  Gap rank corr: {r2['rank_correlations']['gap_to_second_best']:.4f}")
        print(f"  Best predictor: {r2['best_predictor']}")
        results["tests"][f"z{n}_predictor_comparison"] = r2
        
        # Test 3: Calibration curve
        print(f"\n--- Test 3: Calibration Curve (n={n})...")
        start = time.time()
        r3 = test_consensus_calibration_curve(n, num_trials=10000)
        r3["runtime_seconds"] = time.time() - start
        print(f"  Calibration points: {len(r3['calibration'])} consensus levels")
        print(f"  P90 error threshold: {r3['error_thresholds']['p90']:.4f}")
        print(f"  P95 error threshold: {r3['error_thresholds']['p95']:.4f}")
        results["tests"][f"z{n}_calibration_curve"] = r3
        
        # Test 4: Edge cases
        print(f"\n--- Test 4: Edge Cases (n={n})...")
        start = time.time()
        r4 = test_consensus_edge_cases(n, num_trials=3000)
        r4["runtime_seconds"] = time.time() - start
        print(f"  Test cases: {r4['num_test_cases']}")
        for cat, stats in r4["category_stats"].items():
            print(f"  {cat}: consensus={stats['mean_consensus']:.2%}, "
                  f"error={stats['mean_error']:.4f}")
        results["tests"][f"z{n}_edge_cases"] = r4
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    
    outpath = "/home/phoenix/.openclaw/workspace/experiments/flux-fold-ground-truth/results_consensus.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"Results written to: {outpath}")
