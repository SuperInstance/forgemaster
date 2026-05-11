"""
Eisenstein integer snap algorithm — OPTIMIZED.

Changes from baseline:
  - Removed lazy import from eisenstein_round (was importing every call)
  - Added __slots__ to EisensteinInteger (already had it)
  - Added batch operations
  - Type hints throughout
  - Precomputed constants
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

from snapkit.eisenstein_voronoi import eisenstein_snap_voronoi

# Fundamental constants — precomputed once
SQRT3: float = math.sqrt(3)
HALF_SQRT3: float = 0.5 * SQRT3
OMEGA: complex = complex(-0.5, HALF_SQRT3)
OMEGA_CONJ: complex = complex(-0.5, -HALF_SQRT3)

# Basis vectors
E1: complex = complex(1, 0)
E2: complex = OMEGA


@dataclass(frozen=True, slots=True)
class EisensteinInteger:
    """An Eisenstein integer a + bω where a, b ∈ Z."""
    a: int
    b: int

    @property
    def complex(self) -> complex:
        """Convert to Cartesian complex number."""
        return complex(self.a - 0.5 * self.b, HALF_SQRT3 * self.b)

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
        a, b = self.a, self.b
        c, d = other.a, other.b
        return EisensteinInteger(a * c - b * d, a * d + b * c - b * d)

    def conjugate(self) -> "EisensteinInteger":
        """Galois conjugate: (a+b) - bω."""
        return EisensteinInteger(self.a + self.b, -self.b)

    def __repr__(self) -> str:
        return f"EisensteinInteger({self.a}, {self.b})"

    @classmethod
    def from_complex(cls, z: complex) -> "EisensteinInteger":
        """Convert a complex number to the nearest Eisenstein integer."""
        return eisenstein_round(z)


def _to_eisenstein_coords(z: complex) -> Tuple[float, float]:
    """Convert Cartesian (x, y) to Eisenstein coordinates (a, b)."""
    b_float: float = 2.0 * z.imag / SQRT3
    a_float: float = z.real + b_float * 0.5
    return a_float, b_float


def eisenstein_round_naive(z: complex) -> EisensteinInteger:
    """Naive rounding (legacy, kept for comparison)."""
    a_float, b_float = _to_eisenstein_coords(z)
    a_floor: int = math.floor(a_float)
    b_floor: int = math.floor(b_float)

    best: EisensteinInteger = EisensteinInteger(a_floor, b_floor)
    best_dist: float = float("inf")
    tied: List[Tuple[int, int, int, int]] = []

    for da in (0, 1):
        for db in (0, 1):
            a = a_floor + da
            b = b_floor + db
            cand_z: complex = EisensteinInteger(a, b).complex
            dist: float = abs(z - cand_z)
            if dist < best_dist - 1e-9:
                best_dist = dist
                tied = [(abs(a), abs(b), a, b)]
            elif abs(dist - best_dist) < 1e-9:
                tied.append((abs(a), abs(b), a, b))

    tied.sort()
    return EisensteinInteger(tied[0][2], tied[0][3])


def eisenstein_round(z: complex) -> EisensteinInteger:
    """Round a complex number to the nearest Eisenstein integer.

    OPTIMIZED: No lazy import — uses top-level import.
    """
    a, b = eisenstein_snap_voronoi(z.real, z.imag)
    return EisensteinInteger(a, b)


def eisenstein_snap(
    z: complex,
    tolerance: float = 0.5,
) -> Tuple[EisensteinInteger, float, bool]:
    """Snap a complex number to the nearest Eisenstein lattice point."""
    nearest: EisensteinInteger = eisenstein_round(z)
    distance: float = abs(z - nearest.complex)
    is_snap: bool = distance <= tolerance
    return nearest, distance, is_snap


def eisenstein_snap_batch(
    points: List[complex],
    tolerance: float = 0.5,
) -> List[Tuple[EisensteinInteger, float, bool]]:
    """Vectorized snap for multiple complex points."""
    return [eisenstein_snap(z, tolerance) for z in points]


def eisenstein_distance(z1: complex, z2: complex) -> float:
    """Compute the Eisenstein lattice distance between two complex numbers."""
    diff: complex = z1 - z2
    nearest: EisensteinInteger = eisenstein_round(diff)
    residual: float = abs(diff - nearest.complex)
    return math.sqrt(nearest.norm_squared) + residual


def eisenstein_fundamental_domain(z: complex) -> Tuple[EisensteinInteger, "EisensteinInteger"]:
    """Reduce z to its canonical representative in the fundamental domain."""
    units: List[EisensteinInteger] = [
        EisensteinInteger(1, 0),
        EisensteinInteger(0, 1),
        EisensteinInteger(-1, 1),
        EisensteinInteger(-1, 0),
        EisensteinInteger(0, -1),
        EisensteinInteger(1, -1),
    ]
    target_angle: float = math.pi / 6

    best_unit: EisensteinInteger = units[0]
    best_angle: float = float("inf")

    for u in units:
        rotated: complex = z * u.conjugate().complex
        angle: float = abs(math.atan2(rotated.imag, rotated.real) - target_angle)
        if angle < best_angle:
            best_angle = angle
            best_unit = u

    return best_unit, eisenstein_round(z * best_unit.conjugate().complex)
