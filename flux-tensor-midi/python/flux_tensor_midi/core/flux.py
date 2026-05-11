"""
FluxVector: A 9-channel tensor representing PLATO room state.

Each channel has a salience (importance) and tolerance (jitter allowed).
Inspired by the musical metaphor: 9 channels = notes in a harmonic spectrum,
salience = velocity, tolerance = pitch bend range.
"""

from __future__ import annotations
import math
from typing import Sequence


class FluxVector:
    """A 9-channel vector with per-channel salience and tolerance.

    PLATO rooms produce timestamped events.  Each event is encoded as a
    FluxVector whose channels represent aspects of the room's state.
    Salience is the strength (0–1), tolerance is the allowed jitter (ms).

    Properties
    ----------
    channels : int
        Fixed at 9.
    salience : tuple[float, ...]
        Length-9 tuple of salience values (0 ≤ s ≤ 1).
    tolerance : tuple[float, ...]
        Length-9 tuple of tolerance values in milliseconds.
    """

    _CHANNELS = 9

    def __init__(
        self,
        values: Sequence[float],
        salience: Sequence[float] | None = None,
        tolerance: Sequence[float] | None = None,
    ):
        if len(values) != self._CHANNELS:
            raise ValueError(f"FluxVector requires {self._CHANNELS} values, got {len(values)}")
        if salience is not None and len(salience) != self._CHANNELS:
            raise ValueError(f"salience must have {self._CHANNELS} elements, got {len(salience)}")
        if tolerance is not None and len(tolerance) != self._CHANNELS:
            raise ValueError(f"tolerance must have {self._CHANNELS} elements, got {len(tolerance)}")

        self._values = tuple(float(v) for v in values)
        self._salience = tuple(
            float(s) if s is not None else 1.0 for s in (salience or [1.0] * self._CHANNELS)
        )
        self._tolerance = tuple(
            float(t) if t is not None else 0.0 for t in (tolerance or [0.0] * self._CHANNELS)
        )

        # Clamp salience
        self._salience = tuple(max(0.0, min(1.0, s)) for s in self._salience)

    # ---- accessors ----

    @property
    def values(self) -> tuple[float, ...]:
        return self._values

    @property
    def salience(self) -> tuple[float, ...]:
        return self._salience

    @property
    def tolerance(self) -> tuple[float, ...]:
        return self._tolerance

    def __getitem__(self, idx: int) -> float:
        return self._values[idx]

    def __len__(self) -> int:
        return self._CHANNELS

    def __repr__(self) -> str:
        return (
            f"FluxVector({list(self._values)}, "
            f"salience={list(self._salience)}, "
            f"tolerance={list(self._tolerance)})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FluxVector):
            return NotImplemented
        return (
            self._values == other._values
            and self._salience == other._salience
            and self._tolerance == other._tolerance
        )

    def __hash__(self) -> int:
        return hash((self._values, self._salience, self._tolerance))

    # ---- operators ----

    def __add__(self, other: FluxVector) -> FluxVector:
        """Element-wise addition, weighting by minimum salience."""
        if not isinstance(other, FluxVector):
            return NotImplemented
        w = tuple(min(a, b) for a, b in zip(self._salience, other._salience))
        v = tuple(self._values[i] + other._values[i] for i in range(self._CHANNELS))
        s = tuple(max(a, b) for a, b in zip(self._salience, other._salience))
        t = tuple(max(a, b) for a, b in zip(self._tolerance, other._tolerance))
        return FluxVector(v, salience=s, tolerance=t)

    def __sub__(self, other: FluxVector) -> FluxVector:
        """Element-wise subtraction, weighting by minimum salience."""
        if not isinstance(other, FluxVector):
            return NotImplemented
        v = tuple(self._values[i] - other._values[i] for i in range(self._CHANNELS))
        s = tuple(max(a, b) for a, b in zip(self._salience, other._salience))
        t = tuple(max(a, b) for a, b in zip(self._tolerance, other._tolerance))
        return FluxVector(v, salience=s, tolerance=t)

    def __mul__(self, scalar: float) -> FluxVector:
        """Scale all values by a scalar."""
        v = tuple(x * scalar for x in self._values)
        return FluxVector(v, salience=self._salience, tolerance=self._tolerance)

    def __rmul__(self, scalar: float) -> FluxVector:
        return self.__mul__(scalar)

    # ---- norms / distance ----

    @property
    def magnitude(self) -> float:
        """Euclidean norm."""
        return math.sqrt(sum(x * x for x in self._values))

    @property
    def salience_weighted_magnitude(self) -> float:
        """Euclidean norm weighted by salience."""
        return math.sqrt(
            sum(self._salience[i] * self._values[i] * self._values[i] for i in range(self._CHANNELS))
        )

    def distance_to(self, other: FluxVector, weighted: bool = False) -> float:
        """Euclidean distance to another FluxVector.

        If weighted, use salience-weighted difference.
        """
        if not isinstance(other, FluxVector):
            raise TypeError("distance_to requires a FluxVector")
        if weighted:
            diff = tuple(
                self._salience[i] * (self._values[i] - other._values[i])
                for i in range(self._CHANNELS)
            )
        else:
            diff = tuple(self._values[i] - other._values[i] for i in range(self._CHANNELS))
        return math.sqrt(sum(d * d for d in diff))

    def dot(self, other: FluxVector) -> float:
        """Dot product, unweighted."""
        if not isinstance(other, FluxVector):
            raise TypeError("dot requires a FluxVector")
        return sum(self._values[i] * other._values[i] for i in range(self._CHANNELS))

    def cosine_similarity(self, other: FluxVector) -> float:
        """Cosine similarity (-1 to 1)."""
        mag_self = self.magnitude
        mag_other = other.magnitude
        if mag_self == 0.0 or mag_other == 0.0:
            return 0.0
        return self.dot(other) / (mag_self * mag_other)

    # ---- tolerance helpers ----

    def within_tolerance(self, other: FluxVector) -> bool:
        """True if every channel is within its tolerance of the other."""
        for i in range(self._CHANNELS):
            if abs(self._values[i] - other._values[i]) > self._tolerance[i]:
                return False
        return True

    def jitter(self, channel: int) -> float:
        """Return the allowed jitter (tolerance) for a specific channel."""
        return self._tolerance[channel]

    @classmethod
    def zero(cls, salience: Sequence[float] | None = None) -> FluxVector:
        """Create a zero FluxVector with optional salience."""
        return cls([0.0] * cls._CHANNELS, salience=salience)

    @classmethod
    def unit(cls, channel: int, salience: Sequence[float] | None = None) -> FluxVector:
        """Create a unit vector along one channel."""
        v = [0.0] * cls._CHANNELS
        v[channel] = 1.0
        return cls(v, salience=salience)
