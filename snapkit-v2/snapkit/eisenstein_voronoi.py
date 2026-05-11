"""
A₂ lattice Voronoï cell nearest-neighbor snap.

The Eisenstein integers Z[ω] form the A₂ root lattice in 2D.
Each Voronoï cell is a regular hexagon. Naive coordinate rounding
(round a, round b independently) can miss the true nearest lattice
point at cell boundaries.

This module implements guaranteed nearest-neighbor snap by checking
a small neighborhood of candidates around the naive estimate.

Key invariant:
    Snap distance ≤ 1/√3  (the A₂ covering radius)

Reference: Conway & Sloane, "Sphere Packings, Lattices and Groups", Ch. 2.
"""

import math
from typing import Tuple

SQRT3 = math.sqrt(3)


def eisenstein_to_real(a: int, b: int) -> Tuple[float, float]:
    """Convert Eisenstein integer (a, b) to Cartesian (x, y).

    Point is a + bω where ω = e^(2πi/3) = (-1 + i√3)/2.
    Real part: a - b/2.  Imag part: b√3/2.
    """
    return (a - b * 0.5, b * SQRT3 * 0.5)


def snap_distance(x: float, y: float, a: int, b: int) -> float:
    """Euclidean distance from (x, y) to Eisenstein integer (a, b)."""
    rx, ry = eisenstein_to_real(a, b)
    return math.hypot(x - rx, y - ry)


def eisenstein_snap_naive(x: float, y: float) -> Tuple[int, int]:
    """Naive coordinate rounding (baseline, known buggy at boundaries).

    Computes b = round(2y/√3), then a = round(x + b/2).
    This fails at A₂ Voronoï cell boundaries where the hexagonal
    geometry doesn't align with the rectangular rounding grid.
    """
    b = round(y * 2.0 / SQRT3)
    a = round(x + b * 0.5)
    return (a, b)


def eisenstein_snap_voronoi(x: float, y: float) -> Tuple[int, int]:
    """Snap (x, y) to the true nearest Eisenstein integer.

    Guarantees snap distance ≤ 1/√3 (A₂ covering radius).

    Algorithm:
        1. Compute naive candidate (a0, b0) by coordinate rounding.
        2. Check all 9 candidates in the 3×3 neighborhood
           {(a0+da, b0+db) : da, db ∈ {-1, 0, 1}}.
        3. Return the candidate with minimum Euclidean distance.

    The 3×3 neighborhood is sufficient because the naive rounding
    error in each coordinate is at most 0.5, so the true nearest
    differs by at most 1 in each coordinate from the naive candidate.

    For ties (boundary points), prefer the candidate with smallest
    |a|, then smallest |b|, ensuring deterministic results.
    """
    # Step 1: naive candidate
    b0 = round(y * 2.0 / SQRT3)
    a0 = round(x + b0 * 0.5)

    # Step 2: search 3×3 neighborhood
    best_dist = float('inf')
    best = (a0, b0)

    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            a = a0 + da
            b = b0 + db
            d = snap_distance(x, y, a, b)
            if d < best_dist - 1e-12:
                best_dist = d
                best = (a, b)
            elif abs(d - best_dist) < 1e-12:
                # Tie-break: canonical representative (smallest |a|, then |b|)
                if (abs(a), abs(b)) < (abs(best[0]), abs(best[1])):
                    best = (a, b)

    return best
