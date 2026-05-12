"""Shared Eisenstein snap function for the test corpus."""

import math

SQRT3 = math.sqrt(3)
COVERING_RADIUS = 1.0 / SQRT3


def eisenstein_to_cart(a: int, b: int) -> tuple[float, float]:
    """Convert Eisenstein (a,b) to Cartesian (x,y)."""
    return a - b / 2.0, b * SQRT3 / 2.0


def snap_error(x: float, y: float, a: int, b: int) -> float:
    """Euclidean distance from (x, y) to Eisenstein lattice point (a, b)."""
    lx, ly = eisenstein_to_cart(a, b)
    return math.sqrt((x - lx) ** 2 + (y - ly) ** 2)


def eisenstein_snap(x: float, y: float) -> tuple[int, int]:
    """Snap Cartesian (x, y) to nearest Eisenstein integer (a, b).
    
    Uses deterministic tie-breaking: prefers smaller a, then smaller b.
    """
    b_float = 2.0 * y / SQRT3
    a_float = x + y / SQRT3
    
    a_lo = math.floor(a_float)
    b_lo = math.floor(b_float)
    
    # Check all 4 floor/ceil candidates
    best_a, best_b = None, None
    best_err = float('inf')
    
    for da in (0, 1):
        for db in (0, 1):
            ca = a_lo + da
            cb = b_lo + db
            err = snap_error(x, y, ca, cb)
            if err < best_err - 1e-15:
                best_a, best_b = ca, cb
                best_err = err
            elif abs(err - best_err) < 1e-15:
                # Tie-break: prefer smaller a, then smaller b
                if (ca, cb) < (best_a, best_b):
                    best_a, best_b = ca, cb
    
    # Check ±1 neighborhood of best
    for da in range(-1, 2):
        for db in range(-1, 2):
            ca = best_a + da
            cb = best_b + db
            err = snap_error(x, y, ca, cb)
            if err < best_err - 1e-15:
                best_a, best_b = ca, cb
                best_err = err
            elif abs(err - best_err) < 1e-15:
                if (ca, cb) < (best_a, best_b):
                    best_a, best_b = ca, cb
    
    return best_a, best_b
