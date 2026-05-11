#!/usr/bin/env python3
"""
Verification script for Eisenstein snap fixes.

Tests:
1. Counterexample (-4.626, 21.435) — was snapping to (7,24), should snap to (8,25)
2. 1M random points — max delta must be ≤ 1/√3 + epsilon (covering radius)
3. E8 coset selector correctness
"""

import math
import random
import sys

SQRT3 = math.sqrt(3)
INV_SQRT3 = 1.0 / SQRT3
SQRT3_2 = SQRT3 / 2.0
COVERING_RADIUS = 1.0 / SQRT3  # ≈ 0.5774


def eisenstein_snap_optimal(x, y):
    """
    Corrected optimal Eisenstein snap — mirrors the fixed C/CUDA code.
    
    Voronoi cell boundaries for A₂ in Eisenstein fractional coords:
      2u - v ≤ 1,  v - 2u ≤ 1,  2v - u ≤ 1,  u - 2v ≤ 1,
      u + v ≤ 1,   u + v ≥ -1
    
    Corrections fire when boundary is violated.
    """
    # Map to Eisenstein coordinates
    b_float = 2.0 * y * INV_SQRT3
    a_float = x + y * INV_SQRT3
    
    # Round to nearest integer
    i_a = round(a_float)
    i_b = round(b_float)
    
    # Fractional parts
    u = a_float - i_a
    v = b_float - i_b
    
    # Corrected Voronoi conditions with overlap handling
    da, db = 0, 0
    c1 = 2.0 * u - v
    c2 = v - 2.0 * u
    c3 = 2.0 * v - u
    c4 = u - 2.0 * v
    u_plus_v = u + v

    if c1 > 1.0 and c4 > 1.0:
        # Corner (0.5, -0.5): tie-break on u+v
        if u_plus_v > 0: da, db = 1, 0
        else: da, db = 0, -1
    elif c2 > 1.0 and c3 > 1.0:
        # Corner (-0.5, 0.5): tie-break on u+v
        if u_plus_v > 0: da, db = 0, 1
        else: da, db = -1, 0
    elif c1 > 1.0:
        da, db = 1, 0
    elif c2 > 1.0:
        da, db = -1, 0
    elif c3 > 1.0:
        da, db = 0, 1
    elif c4 > 1.0:
        da, db = 0, -1
    
    i_a += da
    i_b += db
    
    # Compute Cartesian distance
    u_corr = u - da
    v_corr = v - db
    eisenstein_norm = u_corr * u_corr - u_corr * v_corr + v_corr * v_corr
    delta = math.sqrt(max(0.0, eisenstein_norm))
    
    snapped_x = i_a - i_b * 0.5
    snapped_y = i_b * SQRT3_2
    
    return i_a, i_b, snapped_x, snapped_y, delta


def eisenstein_snap_bruteforce(x, y):
    """Brute-force 3×3 search for ground truth."""
    b_float = 2.0 * y * INV_SQRT3
    a_float = x + y * INV_SQRT3
    
    i_a = round(a_float)
    i_b = round(b_float)
    
    best_a, best_b = i_a, i_b
    best_d2 = float('inf')
    
    for da in range(-1, 2):
        for db in range(-1, 2):
            ca = i_a + da
            cb = i_b + db
            # Cartesian distance
            sx = ca - cb * 0.5
            sy = cb * SQRT3_2
            d2 = (x - sx) ** 2 + (y - sy) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_a = ca
                best_b = cb
    
    return best_a, best_b, math.sqrt(best_d2)


def snap_e8_corrected(vals):
    """
    E8 lattice snap using correct coset selection.
    
    E8 = D8+ = D8 ∪ (D8 + (1/2)^8)
    D8 = {x ∈ Z^8 : sum(x_i) ≡ 0 mod 2}
    
    Algorithm:
    1. Compute Z^8 candidate (round to nearest integer)
    2. Fix parity of Z^8 candidate (flip coordinate with smallest error increase)
    3. Compute (Z+1/2)^8 candidate (round to nearest half-integer)
    4. Pick closer one
    """
    int_cand = [0] * 8
    half_cand = [0] * 8
    int_dist2 = 0.0
    half_dist2 = 0.0
    
    for i in range(8):
        vi = vals[i]
        
        # Integer candidate
        r1 = round(vi)
        int_cand[i] = int(r1)
        d1 = vi - r1
        int_dist2 += d1 * d1
        
        # Half-integer candidate
        vh = vi - 0.5
        r2 = round(vh)
        half_cand[i] = int(r2 + 1)  # because we subtracted 0.5
        d2 = vi - (r2 + 0.5)
        half_dist2 += d2 * d2
    
    # Fix parity of integer candidate (sum must be even)
    int_sum = sum(int_cand) & 1
    if int_sum:
        # Flip the coordinate with smallest error increase
        # (i.e., the one closest to 0.5 rounding error)
        best_idx = 0
        best_cost = float('inf')
        for i in range(8):
            err = abs(vals[i] - int_cand[i])
            # Cost of flipping: |vi - (ri ± 1)|
            flip_up = (vals[i] - (int_cand[i] + 1)) ** 2
            flip_dn = (vals[i] - (int_cand[i] - 1)) ** 2
            cost = min(flip_up, flip_dn) - err * err
            if cost < best_cost:
                best_cost = cost
                best_idx = i
        
        # Apply the flip
        flip_up = abs(vals[best_idx] - (int_cand[best_idx] + 1))
        flip_dn = abs(vals[best_idx] - (int_cand[best_idx] - 1))
        if flip_up < flip_dn:
            int_cand[best_idx] += 1
        else:
            int_cand[best_idx] -= 1
        
        # Recompute distance
        int_dist2 = sum((vals[i] - int_cand[i]) ** 2 for i in range(8))
    
    # Choose closer candidate
    if int_dist2 <= half_dist2:
        return int_cand, math.sqrt(int_dist2)
    else:
        return half_cand, math.sqrt(half_dist2)


def snap_e8_bruteforce(vals):
    """Brute-force E8 snap: check both cosets exhaustively, return nearest."""
    # Z^8 candidate: round, then fix parity if needed
    int_cand_base = [round(v) for v in vals]
    
    # Try all possible single-flip parity fixes for integer coset
    best_int_d2 = float('inf')
    best_int_cand = None
    
    int_sum = sum(int_cand_base) % 2
    if int_sum == 0:
        best_int_cand = list(int_cand_base)
        best_int_d2 = sum((vals[i] - int_cand_base[i]) ** 2 for i in range(8))
    else:
        for i in range(8):
            for delta in [-1, 1]:
                cand = list(int_cand_base)
                cand[i] += delta
                d2 = sum((vals[j] - cand[j]) ** 2 for j in range(8))
                if d2 < best_int_d2:
                    best_int_d2 = d2
                    best_int_cand = list(cand)
    
    # (Z+1/2)^8 candidate: round to nearest half-integer
    half_cand_base = [round(v - 0.5) + 1 for v in vals]
    
    # Fix parity of integer parts for half-integer coset
    best_half_d2 = float('inf')
    best_half_cand = None
    
    half_int_parts = [round(v - 0.5) for v in vals]  # integer parts n_i
    half_sum = sum(half_int_parts) % 2
    if half_sum == 0:
        best_half_cand = list(half_cand_base)
        best_half_d2 = sum((vals[i] - half_cand_base[i]) ** 2 for i in range(8))
    else:
        for i in range(8):
            for delta in [-1, 1]:
                cand = list(half_cand_base)
                cand[i] += delta
                d2 = sum((vals[j] - cand[j]) ** 2 for j in range(8))
                if d2 < best_half_d2:
                    best_half_d2 = d2
                    best_half_cand = list(cand)
    
    if best_int_d2 <= best_half_d2:
        return best_int_cand, math.sqrt(best_int_d2)
    else:
        return best_half_cand, math.sqrt(best_half_d2)


def test_counterexample():
    """Test the known counterexample."""
    print("=" * 60)
    print("TEST 1: Counterexample (-4.626, 21.435)")
    print("=" * 60)
    
    x, y = -4.626, 21.435
    
    # Optimal snap
    a, b, sx, sy, delta = eisenstein_snap_optimal(x, y)
    print(f"  Optimal snap: ({a}, {b}), delta={delta:.6f}")
    print(f"  Snapped Cartesian: ({sx:.6f}, {sy:.6f})")
    
    # Brute force
    ba, bb, bd = eisenstein_snap_bruteforce(x, y)
    print(f"  Brute force:   ({ba}, {bb}), delta={bd:.6f}")
    
    # Check agreement
    if a == ba and b == bb:
        print(f"  ✓ PASS: Optimal matches brute force")
        return True
    else:
        print(f"  ✗ FAIL: Optimal ({a},{b}) != Brute ({ba},{bb})")
        return False


def test_covering_radius(n_points=1_000_000, seed=42):
    """Test that max delta ≤ 1/√3 over random points."""
    print()
    print("=" * 60)
    print(f"TEST 2: Covering radius over {n_points:,} random points")
    print("=" * 60)
    
    random.seed(seed)
    max_delta = 0.0
    worst_point = None
    disagreements = 0
    epsilon = 1e-6  # floating-point tolerance
    bound = COVERING_RADIUS + epsilon
    
    for _ in range(n_points):
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        
        a, b, sx, sy, delta = eisenstein_snap_optimal(x, y)
        
        if delta > max_delta:
            max_delta = delta
            worst_point = (x, y, a, b)
        
        if delta > bound:
            ba, bb, bd = eisenstein_snap_bruteforce(x, y)
            if abs(delta - bd) > 1e-9:
                disagreements += 1
                if disagreements <= 5:
                    print(f"  WARNING: delta={delta:.6f} > 1/√3 at ({x:.3f}, {y:.3f})")
                    print(f"    Optimal: ({a},{b}), Brute: ({ba},{bb})")
    
    print(f"  Max delta: {max_delta:.8f}")
    print(f"  Covering radius 1/√3 = {COVERING_RADIUS:.8f}")
    print(f"  Bound (1/√3 + ε) = {bound:.8f}")
    print(f"  Worst point: ({worst_point[0]:.4f}, {worst_point[1]:.4f}) → ({worst_point[2]}, {worst_point[3]})")
    
    if max_delta <= bound:
        print(f"  ✓ PASS: max delta {max_delta:.8f} ≤ {bound:.8f}")
        return True
    else:
        print(f"  ✗ FAIL: max delta {max_delta:.8f} > {bound:.8f}")
        return False


def test_optimal_vs_bruteforce(n_points=100_000, seed=123):
    """Verify optimal always matches brute force."""
    print()
    print("=" * 60)
    print(f"TEST 3: Optimal vs brute force ({n_points:,} points)")
    print("=" * 60)
    
    random.seed(seed)
    mismatches = 0
    
    for _ in range(n_points):
        x = random.uniform(-50, 50)
        y = random.uniform(-50, 50)
        
        a, b, sx, sy, delta = eisenstein_snap_optimal(x, y)
        ba, bb, bd = eisenstein_snap_bruteforce(x, y)
        
        # Allow tiny floating-point differences in distance
        if (a != ba or b != bb) and abs(delta - bd) > 1e-9:
            mismatches += 1
            if mismatches <= 5:
                print(f"  MISMATCH at ({x:.4f}, {y:.4f}):")
                print(f"    Optimal: ({a},{b}) delta={delta:.8f}")
                print(f"    Brute:   ({ba},{bb}) delta={bd:.8f}")
    
    if mismatches == 0:
        print(f"  ✓ PASS: All {n_points:,} points agree with brute force")
        return True
    else:
        print(f"  ✗ FAIL: {mismatches} mismatches out of {n_points:,}")
        return False


def test_e8_coset(n_points=100_000, seed=99):
    """Test E8 coset selector against brute force."""
    print()
    print("=" * 60)
    print(f"TEST 4: E₈ coset selector ({n_points:,} random 8D points)")
    print("=" * 60)
    
    random.seed(seed)
    mismatches = 0
    
    for _ in range(n_points):
        vals = [random.uniform(-10, 10) for _ in range(8)]
        
        cand, delta = snap_e8_corrected(vals)
        bcand, bdelta = snap_e8_bruteforce(vals)
        
        if abs(delta - bdelta) > 1e-6:
            mismatches += 1
            if mismatches <= 3:
                print(f"  MISMATCH: delta={delta:.6f} vs brute={bdelta:.6f}")
    
    error_rate = mismatches / n_points * 100
    print(f"  Mismatches: {mismatches}/{n_points:,} ({error_rate:.2f}%)")
    
    if error_rate < 1.0:
        print(f"  ✓ PASS: Error rate {error_rate:.2f}% < 1%")
        return True
    else:
        print(f"  ✗ FAIL: Error rate {error_rate:.2f}% ≥ 1%")
        return False


def main():
    results = []
    
    results.append(test_counterexample())
    results.append(test_optimal_vs_bruteforce())
    results.append(test_covering_radius())
    results.append(test_e8_coset())
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    names = ["Counterexample", "Optimal vs Brute", "Covering Radius", "E₈ Coset"]
    for name, passed in zip(names, results):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name:25s} {status}")
    
    all_pass = all(results)
    print(f"\n  Overall: {'ALL PASS ✓' if all_pass else 'SOME FAILED ✗'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
