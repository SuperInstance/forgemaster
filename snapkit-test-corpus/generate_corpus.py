#!/usr/bin/env python3
"""
Generate the cross-language snapkit test corpus.

Eisenstein integer lattice: a + bω where ω = e^(2πi/3) = -1/2 + i√3/2
Cartesian mapping:
  x = a - b/2
  y = b·√3/2
Inverse:
  b = 2y/√3
  a = x + y/√3
"""

import json
import math
import os
import hashlib

from snap_common import eisenstein_snap, snap_error, COVERING_RADIUS


def make_case(case_id: int, x: float, y: float) -> dict:
    a, b = eisenstein_snap(x, y)
    err = snap_error(x, y, a, b)
    assert err <= COVERING_RADIUS + 1e-10, f"Case {case_id}: snap error {err} > covering radius {COVERING_RADIUS}"
    return {
        "id": case_id,
        "input": {"x": round(x, 15), "y": round(y, 15)},
        "expected": {"a": a, "b": b},
        "snap_error": round(err, 15),
        "snap_error_max": round(COVERING_RADIUS, 10),
    }


def generate_corpus() -> list[dict]:
    cases = []
    cid = 0
    SQRT3 = math.sqrt(3)

    def add(x, y):
        nonlocal cid
        cid += 1
        cases.append(make_case(cid, x, y))

    # === 1. Exact grid points (snap_error = 0) ===
    grid_points = [
        (0, 0), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1),
        (2, 0), (0, 2), (-2, 2), (-2, 0), (0, -2), (2, -2),
        (2, 1), (1, 2), (-1, 3), (-3, 3), (3, 0), (0, 3), (-3, 0),
        (1, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -1),
    ]
    for a, b in grid_points:
        x = a - b / 2.0
        y = b * SQRT3 / 2.0
        add(x, y)

    # === 2. Near-grid points (small perturbation) ===
    near_grid = [
        (0.01, 0.01), (1.01, -0.01), (-0.99, 0.005),
        (0.5, SQRT3/2 + 0.01), (-0.5, -SQRT3/2 - 0.01),
        (0.001, 0.001), (1.001, 0.0), (0.0, SQRT3/2 + 0.001),
        (-1.001, SQRT3/2), (0.5 + 0.01, -SQRT3/2),
        (0.02, -0.01), (1.5, 0.866 + 0.005), (-2.5, 1.3),
    ]
    for x, y in near_grid:
        add(x, y)

    # === 3. Voronoi cell boundaries ===
    COVERING_RADIUS_val = COVERING_RADIUS
    for angle in [i * math.pi / 3 for i in range(6)]:
        bx = COVERING_RADIUS_val * math.cos(angle)
        by = COVERING_RADIUS_val * math.sin(angle)
        add(bx, by)
        add(bx * 0.99, by * 0.99)
        add(bx * 1.01, by * 1.01)

    # Midpoints between origin and its 6 neighbors
    add(0.5, 0.0)
    add(-0.25, SQRT3 / 4)
    add(-0.75, SQRT3 / 4)
    add(-0.5, 0.0)
    add(0.25, -SQRT3 / 4)
    add(0.75, -SQRT3 / 4)

    # === 4. Worst-case points (Voronoi vertices) ===
    for angle in [i * math.pi / 3 + math.pi / 6 for i in range(6)]:
        wx = COVERING_RADIUS_val * math.cos(angle)
        wy = COVERING_RADIUS_val * math.sin(angle)
        add(wx, wy)

    # === 5. Large coordinates (stress test) ===
    large_coords = [
        (1000.3, -500.7), (-999.9, 999.9), (500.5, 0.0),
        (-1000.0, 0.0), (0.0, 1000.0), (10000.7, -5000.3),
        (-100000.1, 50000.2), (1e6, 1e6), (-1e6, -1e6),
        (12345.678, -98765.432), (3.14159, 2.71828),
        (1000.0, SQRT3 * 500), (-1000.0, -SQRT3 * 500),
    ]
    for x, y in large_coords:
        add(x, y)

    # === 6. Zero and near-zero ===
    zero_cases = [
        (0, 0), (1e-15, 1e-15), (-1e-15, 0), (0, 1e-15),
        (1e-10, -1e-10), (-1e-10, 1e-10), (5e-16, 5e-16),
        (0.0, 0.0), (1e-8, 0), (0, -1e-8),
    ]
    for x, y in zero_cases:
        add(x, y)

    # === 7. Negative values ===
    negative_cases = [
        (-0.5, -0.5), (-1.3, 2.7), (-3.7, -1.2), (-0.1, -0.9),
        (-5.5, 3.3), (-100.1, -200.2), (-0.25, -0.25),
        (-1.5, -0.866), (-2.3, 1.5), (-7.7, -7.7),
    ]
    for x, y in negative_cases:
        add(x, y)

    # === 8. Systematic grid: 10×10 from -5 to 5 ===
    for i in range(10):
        for j in range(10):
            x = -5.0 + i * (10.0 / 9)
            y = -5.0 + j * (10.0 / 9)
            add(x, y)

    # === 9. Fill to 1000 with deterministic pseudo-random points ===
    while len(cases) < 1000:
        idx = len(cases)
        h = hashlib.sha256(f"snapkit-corpus-{idx}".encode()).hexdigest()
        raw_x = int(h[:8], 16) / 0xFFFFFFFF * 20.0 - 10.0
        raw_y = int(h[8:16], 16) / 0xFFFFFFFF * 20.0 - 10.0
        add(raw_x, raw_y)

    return cases


def main():
    os.makedirs("corpus", exist_ok=True)
    corpus = generate_corpus()
    print(f"Generated {len(corpus)} test cases")

    exact = sum(1 for c in corpus if c["snap_error"] < 1e-12)
    near = sum(1 for c in corpus if 1e-12 <= c["snap_error"] < 0.1)
    mid = sum(1 for c in corpus if 0.1 <= c["snap_error"] < COVERING_RADIUS - 0.01)
    boundary = sum(1 for c in corpus if abs(c["snap_error"] - COVERING_RADIUS) < 0.01)
    print(f"  Exact (error≈0): {exact}")
    print(f"  Near-grid (error<0.1): {near}")
    print(f"  Mid-range: {mid}")
    print(f"  Boundary (error≈covering radius): {boundary}")

    violations = [c for c in corpus if c["snap_error"] > COVERING_RADIUS + 1e-10]
    if violations:
        print(f"WARNING: {len(violations)} cases exceed covering radius!")
        for v in violations[:5]:
            print(f"  Case {v['id']}: error={v['snap_error']}")
    else:
        print("All cases within covering radius ✓")

    with open("corpus/snap_corpus.json", "w") as f:
        json.dump(corpus, f, indent=2)
    print("Written to corpus/snap_corpus.json")


if __name__ == "__main__":
    main()
