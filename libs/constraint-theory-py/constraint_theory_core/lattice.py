"""lattice.py — Eisenstein lattice operations.

Eisenstein lattice: ω = e^{2πi/3} = (-1/2, √3/2)
A point (x, y) maps to Eisenstein integer (a, b) where:
    x = a + b·(-1/2)
    y = b·(√3/2)

Covering radius ρ = 1/√3 ≈ 0.5774 (radius of the fundamental hexagon).
"""

import math
from typing import Tuple

__all__ = ["snap", "covering_radius", "eins_round", "eins_distance"]

_ω_re = -0.5
_ω_im = math.sqrt(3) / 2.0


def eins_round(x: float, y: float) -> Tuple[int, int]:
    """Round a point to the nearest Eisenstein integer (a, b)."""
    a_f = x - y * _ω_re / _ω_im
    b_f = y / _ω_im
    a0 = round(a_f)
    b0 = round(b_f)

    best_a, best_b, best_err = a0, b0, float("inf")
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            ca = a0 + da
            cb = b0 + db
            cx = ca + cb * _ω_re
            cy = cb * _ω_im
            err = math.hypot(x - cx, y - cy)
            if err < best_err:
                best_a, best_b, best_err = ca, cb, err
    return (int(best_a), int(best_b))


def eins_distance(a: int, b: int, x: float, y: float) -> float:
    """Euclidean distance from Eisenstein integer (a, b) to point (x, y)."""
    cx = a + b * _ω_re
    cy = b * _ω_im
    return math.hypot(x - cx, y - cy)


def snap(x: float, y: float) -> Tuple[int, int, float]:
    """Snap a 2-D point to the nearest Eisenstein lattice point.

    Returns:
        (a, b, error): lattice coords and the Euclidean snap error.
    """
    a, b = eins_round(x, y)
    error = eins_distance(a, b, x, y)
    return (a, b, error)


def covering_radius() -> float:
    """Covering radius of the Eisenstein (A₂) lattice.

    ρ = 1/√3 ≈ 0.5774 — every point is within this distance of a lattice point.
    """
    return 1.0 / math.sqrt(3)
