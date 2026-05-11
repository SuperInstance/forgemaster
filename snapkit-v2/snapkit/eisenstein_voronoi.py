"""
A₂ lattice Voronoï cell nearest-neighbor snap — OPTIMIZED.

Changes from baseline:
  - Inlined distance computation (squared distance, no hypot call)
  - Precomputed constants: SQRT3, INV_SQRT3, HALF_SQRT3
  - Batch operations
  - Type hints on signatures only
"""

import math
from typing import List, Tuple

SQRT3 = math.sqrt(3)
INV_SQRT3 = 1.0 / SQRT3
HALF_SQRT3 = 0.5 * SQRT3


def eisenstein_to_real(a: int, b: int) -> Tuple[float, float]:
    return (a - b * 0.5, b * HALF_SQRT3)


def snap_distance(x: float, y: float, a: int, b: int) -> float:
    """Euclidean distance from (x, y) to Eisenstein integer (a, b)."""
    dx = x - (a - b * 0.5)
    dy = y - (b * HALF_SQRT3)
    return math.hypot(dx, dy)


def eisenstein_snap_naive(x: float, y: float) -> Tuple[int, int]:
    b = round(y * 2.0 * INV_SQRT3)
    a = round(x + b * 0.5)
    return (a, b)


def eisenstein_snap_voronoi(x: float, y: float) -> Tuple[int, int]:
    """Snap (x, y) to the true nearest Eisenstein integer.

    OPTIMIZED: Squared-distance comparison (no sqrt), inlined distance,
    precomputed constants.
    """
    b0 = round(y * 2.0 * INV_SQRT3)
    a0 = round(x + b0 * 0.5)

    best_dist_sq = float('inf')
    best_a = a0
    best_b = b0

    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            a = a0 + da
            b = b0 + db
            dx = x - (a - b * 0.5)
            dy = y - (b * HALF_SQRT3)
            d_sq = dx * dx + dy * dy
            if d_sq < best_dist_sq - 1e-24:
                best_dist_sq = d_sq
                best_a = a
                best_b = b
            elif abs(d_sq - best_dist_sq) < 1e-24:
                if (abs(a), abs(b)) < (abs(best_a), abs(best_b)):
                    best_a = a
                    best_b = b

    return (best_a, best_b)


def eisenstein_snap_batch(points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    """Vectorized snap for multiple points."""
    return [eisenstein_snap_voronoi(x, y) for x, y in points]
