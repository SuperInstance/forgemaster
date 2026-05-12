#!/usr/bin/env python3
"""Empirical Rock Hunter — Tests for Cocapn constraint theory claims."""

import sys
sys.path.insert(0, '/home/phoenix/.openclaw/workspace/snapkit-v2')

import math
import random

from snapkit.eisenstein_voronoi import (
    eisenstein_snap_voronoi,
    eisenstein_to_real,
    snap_distance,
    eisenstein_snap_naive,
)

random.seed(42)

results = []

# ============================================================
# ROCK 1: Does the 0.70 alignment threshold actually hold?
# ============================================================
print("=" * 60)
print("ROCK 1: 0.70 alignment threshold")
print("=" * 60)

max_error = 0
errors = []
for _ in range(200000):
    x = random.uniform(-50, 50)
    y = random.uniform(-50, 50)
    a, b = eisenstein_snap_voronoi(x, y)
    err = snap_distance(x, y, a, b)
    errors.append(err)
    if err > max_error:
        max_error = err

covering_radius = 1 / math.sqrt(3)
errors_sorted = sorted(errors)

print(f"Covering radius (1/√3): {covering_radius:.6f}")
print(f"Max snap error observed: {max_error:.6f}")
print(f"P99: {errors_sorted[int(0.99*len(errors))]:.6f}")
print(f"P999: {errors_sorted[int(0.999*len(errors))]:.6f}")
print(f"P9999: {errors_sorted[int(0.9999*len(errors))]:.6f}")
print(f"Errors >= 0.70: {sum(1 for e in errors if e >= 0.70)}")
print(f"Errors >= 0.5774 (covering radius): {sum(1 for e in errors if e >= covering_radius)}")
print(f"Errors >= 0.5770: {sum(1 for e in errors if e >= 0.5770)}")
print(f"Errors >= 0.50: {sum(1 for e in errors if e >= 0.50)}")

# Theoretical max error = covering radius exactly
# Count how close observed max gets to theoretical max
print(f"\nMax error / covering radius = {max_error / covering_radius:.6f}")
print(f"Theoretical max is covering radius = {covering_radius:.6f}")

r1_pass = "PASS" if max_error <= covering_radius + 1e-10 else "FAIL"
print(f"\nVerdict: {r1_pass}")
results.append(("Rock 1: 0.70 threshold", r1_pass,
    f"Max error = {max_error:.6f}, covering radius = {covering_radius:.6f}. "
    f"0.70 is above covering radius, so it's trivially never reached. "
    f"The 'convergence at 0.70' is meaningless — it's like setting a fire alarm at 200°F in a system that never exceeds 100°F."))


# ============================================================
# ROCK 2: Comonad idempotency near Voronoi boundaries
# ============================================================
print("\n" + "=" * 60)
print("ROCK 2: Comonad idempotency (double-snap = single-snap)")
print("=" * 60)

boundary_fails = 0
total_boundary_tests = 100000
for i in range(total_boundary_tests):
    # Generate a point near Voronoi boundary
    a1, b1 = random.randint(-10, 10), random.randint(-10, 10)
    
    # Pick a neighbor direction
    directions = [(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)]
    da, db = random.choice(directions)
    a2, b2 = a1 + da, b1 + db
    
    # Midpoint between two lattice points = boundary
    x1, y1 = eisenstein_to_real(a1, b1)
    x2, y2 = eisenstein_to_real(a2, b2)
    mx = (x1 + x2) / 2 + random.gauss(0, 0.0001)
    my = (y1 + y2) / 2 + random.gauss(0, 0.0001)
    
    r1_a, r1_b = eisenstein_snap_voronoi(mx, my)
    # Snap the result point
    r1x, r1y = eisenstein_to_real(r1_a, r1_b)
    r2_a, r2_b = eisenstein_snap_voronoi(r1x, r1y)
    
    if (r1_a, r1_b) != (r2_a, r2_b):
        boundary_fails += 1
        if boundary_fails <= 5:
            print(f"  FAIL: ({mx:.6f}, {my:.6f}) -> ({r1_a},{r1_b}) -> ({r2_a},{r2_b})")

# Also test general idempotency
general_fails = 0
for _ in range(200000):
    x = random.uniform(-100, 100)
    y = random.uniform(-100, 100)
    a1, b1 = eisenstein_snap_voronoi(x, y)
    x2, y2 = eisenstein_to_real(a1, b1)
    a2, b2 = eisenstein_snap_voronoi(x2, y2)
    if (a1, b1) != (a2, b2):
        general_fails += 1

print(f"Boundary idempotency failures: {boundary_fails}/{total_boundary_tests}")
print(f"General idempotency failures: {general_fails}/200000")

r2_pass = "PASS" if boundary_fails == 0 and general_fails == 0 else "FAIL"
print(f"\nVerdict: {r2_pass}")
results.append(("Rock 2: Comonad idempotency", r2_pass,
    f"Boundary: {boundary_fails}/{total_boundary_tests}, General: {general_fails}/200000"))


# ============================================================
# ROCK 3: Tonnetz map preserves distances?
# ============================================================
print("\n" + "=" * 60)
print("ROCK 3: Tonnetz map distance preservation")
print("=" * 60)

def tonnetz_map(a, b):
    return (7 * a + 4 * b) % 12

# Test: are Eisenstein neighbors mapped to Tonnetz neighbors?
# Eisenstein neighbors are at distance 1 (adjacent in A2 lattice)
neighbor_fails = 0
total_neighbor_tests = 0
large_vld_cases = []

for _ in range(10000):
    a, b = random.randint(-10, 10), random.randint(-10, 10)
    t1 = tonnetz_map(a, b)
    
    for da, db in [(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)]:
        na, nb = a + da, b + db
        t2 = tonnetz_map(na, nb)
        # Voice-leading distance (circular on Z12)
        vld = min(abs(t2 - t1), 12 - abs(t2 - t1))
        total_neighbor_tests += 1
        if vld > 4:  # More than a major third
            neighbor_fails += 1
            if len(large_vld_cases) < 5:
                large_vld_cases.append(f"  ({a},{b})+({da},{db}): T({a},{b})={t1}, T({na},{nb})={t2}, VLD={vld}")

print(f"Eisenstein neighbors tested: {total_neighbor_tests}")
print(f"Neighbors with VLD > 4 (major third): {neighbor_fails}")
for case in large_vld_cases:
    print(case)

# Check VLD distribution
vld_counts = {}
for _ in range(10000):
    a, b = random.randint(-10, 10), random.randint(-10, 10)
    t1 = tonnetz_map(a, b)
    for da, db in [(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)]:
        na, nb = a + da, b + db
        t2 = tonnetz_map(na, nb)
        vld = min(abs(t2 - t1), 12 - abs(t2 - t1))
        vld_counts[vld] = vld_counts.get(vld, 0) + 1

print(f"\nVLD distribution across Eisenstein neighbors:")
total_vld = sum(vld_counts.values())
for vld in sorted(vld_counts.keys()):
    print(f"  VLD={vld}: {vld_counts[vld]} ({100*vld_counts[vld]/total_vld:.1f}%)")

# Check: is the map injective on a fundamental domain?
# The kernel of (7a + 4b) mod 12
kernel_points = 0
for a in range(-6, 7):
    for b in range(-6, 7):
        if tonnetz_map(a, b) == 0:
            kernel_points += 1
            
print(f"\nKernel size (points mapping to 0 in [-6,6]x[-6,6]): {kernel_points}")
print(f"Expected if surjective with period 12: ~169/12 ≈ {169/12:.1f}")

# Check if different Eisenstein points map to same Tonnetz value (non-injectivity)
collision_map = {}
for a in range(-20, 21):
    for b in range(-20, 21):
        t = tonnetz_map(a, b)
        if t not in collision_map:
            collision_map[t] = []
        collision_map[t].append((a, b))

print(f"\nPreimage sizes (how many (a,b) map to each Tonnetz value):")
sizes = [len(v) for v in collision_map.values()]
print(f"  Min: {min(sizes)}, Max: {max(sizes)}, Mean: {sum(sizes)/len(sizes):.1f}")

r3_pass = "PASS" if neighbor_fails == 0 else "FAIL"
print(f"\nVerdict: {r3_pass}")
results.append(("Rock 3: Tonnetz distance", r3_pass,
    f"Neighbor VLD > 4: {neighbor_fails}/{total_neighbor_tests}. "
    f"VLD distribution: {dict(sorted(vld_counts.items()))}"))


# ============================================================
# ROCK 4: Cross-language edge case stress test
# ============================================================
print("\n" + "=" * 60)
print("ROCK 4: Edge case stress test")
print("=" * 60)

# Large coordinates
edge_fails = 0
large_cases = [
    (1e15, 1e15), (-1e15, -1e15), (1e15, -1e15),
    (-1e15, 1e15), (1e12, 1e12), (-1e12, -1e12),
]
print("Large coordinate tests:")
for x, y in large_cases:
    try:
        a, b = eisenstein_snap_voronoi(x, y)
        # Verify idempotency
        rx, ry = eisenstein_to_real(a, b)
        a2, b2 = eisenstein_snap_voronoi(rx, ry)
        ok = (a == a2 and b == b2)
        print(f"  ({x:.0e}, {y:.0e}) -> ({a}, {b}), idempotent: {ok}")
        if not ok:
            edge_fails += 1
    except Exception as e:
        print(f"  ({x:.0e}, {y:.0e}) -> ERROR: {e}")
        edge_fails += 1

# Small coordinates
print("Small coordinate tests:")
small_cases = [
    (1e-15, 1e-15), (-1e-15, 0), (0, 1e-15),
    (1e-15, -1e-15), (0, 0), (0.5, 0.5*math.sqrt(3)/2),
]
for x, y in small_cases:
    try:
        a, b = eisenstein_snap_voronoi(x, y)
        rx, ry = eisenstein_to_real(a, b)
        a2, b2 = eisenstein_snap_voronoi(rx, ry)
        ok = (a == a2 and b == b2)
        print(f"  ({x:.2e}, {y:.2e}) -> ({a}, {b}), idempotent: {ok}")
        if not ok:
            edge_fails += 1
    except Exception as e:
        print(f"  ({x:.2e}, {y:.2e}) -> ERROR: {e}")
        edge_fails += 1

# Exact Voronoi vertices (tripoints where 3 cells meet)
print("Voronoi tripoint tests:")
omega_r = -0.5
omega_i = math.sqrt(3) / 2
tripoint_fails = 0
for a in range(-5, 6):
    for b in range(-5, 6):
        # Tripoints of the A2 lattice are at the centers of the equilateral triangles
        # Three lattice points: (a,b), (a+1,b), (a,b+1) form a triangle
        # Center = centroid
        x1, y1 = eisenstein_to_real(a, b)
        x2, y2 = eisenstein_to_real(a + 1, b)
        x3, y3 = eisenstein_to_real(a, b + 1)
        cx = (x1 + x2 + x3) / 3
        cy = (y1 + y2 + y3) / 3
        
        sa, sb = eisenstein_snap_voronoi(cx, cy)
        # Should snap to one of the three vertices
        valid = (sa, sb) in [(a, b), (a+1, b), (a, b+1)]
        if not valid:
            tripoint_fails += 1
            if tripoint_fails <= 3:
                print(f"  Tripoint ({cx:.4f}, {cy:.4f}) snapped to ({sa},{sb}), expected one of {(a,b)},{(a+1,b)},{(a,b+1)}")

print(f"Tripoint failures: {tripoint_fails}")

# NaN/Inf tests
print("NaN/Inf tests:")
nan_inf_fails = 0
for val in [float('nan'), float('inf'), float('-inf')]:
    for x, y in [(val, 0), (0, val), (val, val)]:
        try:
            a, b = eisenstein_snap_voronoi(x, y)
            print(f"  ({x}, {y}) -> ({a}, {b}) [no crash but questionable]")
            nan_inf_fails += 1
        except Exception as e:
            print(f"  ({x}, {y}) -> Exception: {type(e).__name__}")

r4_pass = "PASS" if edge_fails == 0 and tripoint_fails == 0 and nan_inf_fails > 0 else "PARTIAL"
if edge_fails > 0:
    r4_pass = "FAIL"
print(f"\nVerdict: {r4_pass}")
results.append(("Rock 4: Edge cases", r4_pass,
    f"Edge fails: {edge_fails}, Tripoint fails: {tripoint_fails}, NaN/Inf handled gracefully: {nan_inf_fails > 0}"))


# ============================================================
# ROCK 5: Convergence meta-observation scrutiny
# ============================================================
print("\n" + "=" * 60)
print("ROCK 5: Convergence meta-observation scrutiny")
print("=" * 60)

# Let's check the actual papers/research for convergence claims
# We need to count convergences vs divergences

# First, let's see what's in the research directory
import os
research_dir = '/home/phoenix/.openclaw/workspace/research/'
papers = [f for f in os.listdir(research_dir) if f.endswith('.md')]
print(f"Research files: {len(papers)}")
for p in sorted(papers):
    print(f"  {p}")

# Check convergence paper
conv_file = os.path.join(research_dir, 'CONVERGENCE-PAPER.md')
if os.path.exists(conv_file):
    with open(conv_file) as f:
        content = f.read()
    print(f"\nConvergence paper length: {len(content)} chars")
    # Count convergence claims
    conv_count = content.lower().count('converge')
    print(f"'converge' mentions: {conv_count}")

# Also check the papers directory
papers_dir = '/home/phoenix/.openclaw/workspace/papers/'
if os.path.exists(papers_dir):
    papers_list = os.listdir(papers_dir)
    print(f"\nPapers directory: {len(papers_list)} files")
    for p in sorted(papers_list):
        print(f"  {p}")

results.append(("Rock 5: Convergence meta-observation", "ANALYSIS",
    "Need to count convergences vs total comparisons in the convergence paper. "
    "If 6 convergences from ~30 comparisons, that's 20% — interesting. "
    "If from 200+, it's noise. Detailed count requires reading the paper."))


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, verdict, detail in results:
    print(f"\n{name}: {verdict}")
    print(f"  {detail}")
