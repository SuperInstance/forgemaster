"""
Eisenstein integer snap algorithm.

Eisenstein integers live on the hexagonal lattice Z[ω] where ω = (-1 + i√3)/2.
Every Eisenstein integer is a + bω for a, b ∈ Z.

The snap algorithm projects an arbitrary complex number onto the nearest
Eisenstein lattice point, respecting overlapping conditions discovered
during falsification testing.

Key invariants:
  - The Eisenstein norm ∥a + bω∥² = a² - ab + b² is multiplicative.
  - The lattice has 6-fold rotational symmetry (units: ±1, ±ω, ±ω²).
  - Overlapping Voronoi cells at boundaries are resolved by preferring
    the canonical representative (smallest |a|, then smallest |b|).
"""

import math
from dataclasses import dataclass
from typing import Tuple

# Fundamental constants
OMEGA = complex(-0.5, math.sqrt(3) / 2)  # primitive cube root of unity
OMEGA_CONJ = complex(-0.5, -math.sqrt(3) / 2)
SQRT3 = math.sqrt(3)

# Basis vectors for the Eisenstein lattice in Cartesian coordinates
# e1 = 1, e2 = ω = (-1 + i√3)/2
E1 = complex(1, 0)
E2 = OMEGA


@dataclass(frozen=True, slots=True)
class EisensteinInteger:
    """An Eisenstein integer a + bω where a, b ∈ Z."""
    a: int
    b: int

    @property
    def complex(self) -> complex:
        """Convert to Cartesian complex number."""
        return complex(self.a - 0.5 * self.b, SQRT3 / 2 * self.b)

    @property
    def norm_squared(self) -> int:
        """Eisenstein norm squared: a² - ab + b². Always ≥ 0."""
        return self.a * self.a - self.a * self.b + self.b * self.b

    def __abs__(self) -> float:
        return math.sqrt(self.norm_squared)

    def __add__(self, other: "EisensteinInteger") -> "EisensteinInteger":
        return EisensteinInteger(self.a + other.a, self.b + other.b)

    def __sub__(self, other: "EisensteinInteger") -> "EisensteinInteger":
        return EisensteinInteger(self.a - other.a, self.b - other.b)

    def __mul__(self, other: "EisensteinInteger") -> "EisensteinInteger":
        # (a + bω)(c + dω) = (ac - bd) + (ad + bc - bd)ω
        a, b = self.a, self.b
        c, d = other.a, other.b
        return EisensteinInteger(a * c - b * d, a * d + b * c - b * d)

    def conjugate(self) -> "EisensteinInteger":
        """Galois conjugate: a + bω̄ = (a+b) - bω."""
        return EisensteinInteger(self.a + self.b, -self.b)

    def __repr__(self) -> str:
        return f"EisensteinInteger({self.a}, {self.b})"

    @classmethod
    def from_complex(cls, z: complex) -> "EisensteinInteger":
        """Convert a complex number to the nearest Eisenstein integer."""
        return eisenstein_round(z)


def _to_eisenstein_coords(z: complex) -> Tuple[float, float]:
    """Convert Cartesian (x, y) to Eisenstein coordinates (a, b).

    z = x + iy = a·1 + b·ω where ω = (-1 + i√3)/2
    Solving: x = a - b/2, y = b·√3/2
    Inverse: b = 2y/√3, a = x + b/2
    """
    b_float = 2.0 * z.imag / SQRT3
    a_float = z.real + b_float / 2.0
    return a_float, b_float


def eisenstein_round_naive(z: complex) -> EisensteinInteger:
    """Naive rounding (legacy, kept for comparison).

    Checks only the 4 lattice points in the unit cell surrounding z.
    Known to fail at A₂ Voronoï cell boundaries.
    """
    a_float, b_float = _to_eisenstein_coords(z)
    a_floor = math.floor(a_float)
    b_floor = math.floor(b_float)

    best = None
    best_dist = float("inf")
    tied = []

    for da in (0, 1):
        for db in (0, 1):
            a = a_floor + da
            b = b_floor + db
            cand_z = EisensteinInteger(a, b).complex
            dist = abs(z - cand_z)
            if dist < best_dist - 1e-9:
                best_dist = dist
                tied = [(abs(a), abs(b), a, b)]
            elif abs(dist - best_dist) < 1e-9:
                tied.append((abs(a), abs(b), a, b))

    tied.sort()
    return EisensteinInteger(tied[0][2], tied[0][3])


def eisenstein_round(z: complex) -> EisensteinInteger:
    """Round a complex number to the nearest Eisenstein integer.

    Uses proper A₂ Voronoï cell geometry: checks a 3×3 neighborhood
    of candidates around the naive estimate, guaranteeing snap distance
    ≤ 1/√3 (the A₂ covering radius).

    This fixes the boundary bug where naive coordinate rounding missed
    the true nearest neighbor at hexagonal cell edges.
    """
    from snapkit.eisenstein_voronoi import eisenstein_snap_voronoi

    a, b = eisenstein_snap_voronoi(z.real, z.imag)
    return EisensteinInteger(a, b)


def eisenstein_snap(
    z: complex,
    tolerance: float = 0.5,
) -> Tuple[EisensteinInteger, float, bool]:
    """Snap a complex number to the nearest Eisenstein lattice point.

    Args:
        z: The complex number to snap.
        tolerance: Maximum distance for a successful snap (in Eisenstein norm units).

    Returns:
        (snapped_point, distance, is_snap) where is_snap is True if within tolerance.
    """
    nearest = eisenstein_round(z)
    distance = abs(z - nearest.complex)
    is_snap = distance <= tolerance
    return nearest, distance, is_snap


def eisenstein_distance(z1: complex, z2: complex) -> float:
    """Compute the Eisenstein lattice distance between two complex numbers.

    This is the Euclidean distance to the nearest Eisenstein integer of
    the difference, times the Eisenstein norm of that integer.

    For the hexagonal lattice, this is simply:
        d(z1, z2) = min_{e ∈ Z[ω]} |z1 - z2 - e|

    In practice: round (z1 - z2) to the nearest Eisenstein integer,
    then compute the residual distance.
    """
    diff = z1 - z2
    nearest = eisenstein_round(diff)
    residual = abs(diff - nearest.complex)
    # Full distance includes the lattice contribution
    return nearest.norm_squared ** 0.5 + residual


def eisenstein_fundamental_domain(z: complex) -> Tuple[EisensteinInteger, "EisensteinInteger"]:
    """Reduce z to its canonical representative in the fundamental domain.

    The fundamental domain is the set {z : |z| ≤ 1, arg(z) ∈ [0, π/3]}
    modulo multiplication by units (6-fold symmetry).

    Returns (quotient, remainder) where quotient is the unit used.
    """
    units = [
        EisensteinInteger(1, 0),
        EisensteinInteger(0, 1),
        EisensteinInteger(-1, 1),
        EisensteinInteger(-1, 0),
        EisensteinInteger(0, -1),
        EisensteinInteger(1, -1),
    ]
    # Find the unit that rotates z closest to the fundamental domain angle [0, π/3]
    best_unit = units[0]
    best_z = z
    best_angle = float("inf")

    target_angle = math.pi / 6  # center of fundamental domain

    for u in units:
        rotated = z * u.conjugate().complex
        angle = abs(math.atan2(rotated.imag, rotated.real) - target_angle)
        if angle < best_angle:
            best_angle = angle
            best_unit = u
            best_z = rotated

    return best_unit, eisenstein_round(best_z)
