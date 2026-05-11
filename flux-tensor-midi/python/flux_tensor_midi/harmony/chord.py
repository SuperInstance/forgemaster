"""
Chord quality analysis for FluxVector harmony.

Evaluates how well a set of FluxVectors forms a coherent chord:
consonance, quality (major/minor/dim/aug), and voice leading cost.
"""

from __future__ import annotations
import math
from typing import Sequence
from flux_tensor_midi.core.flux import FluxVector


class ChordQuality:
    """Musical chord quality classification."""
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    SUSPENDED = "suspended"
    SEVENTH = "seventh"
    NINTH = "ninth"
    UNKNOWN = "unknown"


# Consonance ratios (frequency ratios of intervals)
# 1:1 = unison, 3:2 = perfect fifth, 4:3 = perfect fourth,
# 5:4 = major third, 6:5 = minor third, 8:5 = minor sixth
INTERVAL_CONSONANCE: dict[int, float] = {
    0: 1.0,   # unison
    1: 0.6,   # minor second (dissonant)
    2: 0.7,   # major second
    3: 0.8,   # minor third
    4: 0.9,   # major third
    5: 0.95,  # perfect fourth
    6: 0.5,   # tritone (most dissonant)
    7: 0.95,  # perfect fifth
    8: 0.8,   # minor sixth
    9: 0.85,  # major sixth
    10: 0.6,  # minor seventh
    11: 0.7,  # major seventh
    12: 1.0,  # octave
}


class HarmonyState:
    """Represents the harmonic relationship between multiple FluxVectors.

    Parameters
    ----------
    vectors : Sequence[FluxVector]
        The chord as a set of FluxVectors.
    """

    def __init__(self, vectors: Sequence[FluxVector]):
        self._vectors = tuple(vectors)

    @property
    def vectors(self) -> tuple[FluxVector, ...]:
        return self._vectors

    @property
    def size(self) -> int:
        return len(self._vectors)

    # ---- consonance ----

    def consonance(self) -> float:
        """Overall consonance of the chord (0–1).

        Computes pairwise interval consonance based on
        the most active channel in each vector.
        """
        if len(self._vectors) < 2:
            return 1.0

        total = 0.0
        pairs = 0
        for i in range(len(self._vectors)):
            for j in range(i + 1, len(self._vectors)):
                # Find the most active channel pair
                best = 0.0
                for ci in range(9):
                    for cj in range(9):
                        if self._vectors[i][ci] == 0 or self._vectors[j][cj] == 0:
                            continue
                        interval = abs(ci - cj)
                        weight = (
                            self._vectors[i].salience[ci]
                            * self._vectors[j].salience[cj]
                        )
                        cons = INTERVAL_CONSONANCE.get(interval % 12, 0.5)
                        best = max(best, cons * weight)
                total += best
                pairs += 1

        return total / max(pairs, 1)

    # ---- quality ----

    def quality(self) -> str:
        """Classify the chord quality from the active channels."""
        active = self._active_channels()
        if len(active) < 2:
            return ChordQuality.UNKNOWN

        as_sorted = sorted(active)

        # Normalize to [0, 12) range
        bass = as_sorted[0]
        intervals = sorted({(n - bass) % 12 for n in as_sorted})

        # Check common chord types
        if {0, 4, 7}.issubset(intervals):
            return ChordQuality.MAJOR
        if {0, 3, 7}.issubset(intervals):
            return ChordQuality.MINOR
        if {0, 3, 6}.issubset(intervals):
            return ChordQuality.DIMINISHED
        if {0, 4, 8}.issubset(intervals):
            return ChordQuality.AUGMENTED
        if {0, 2, 7}.issubset(intervals) or {0, 5, 7}.issubset(intervals):
            return ChordQuality.SUSPENDED
        if {0, 4, 7, 10}.issubset(intervals):
            return ChordQuality.SEVENTH
        if len(intervals) >= 5:
            return ChordQuality.NINTH

        return ChordQuality.UNKNOWN

    # ---- voice leading ----

    def voice_leading_cost(self, target: HarmonyState) -> float:
        """Voice leading cost to transition to another chord.

        Uses the minimum sum of salience-weighted distances
        between the two sets of active vectors.
        """
        if not self._vectors or not target._vectors:
            return 0.0

        total_cost = 0.0
        m, n = len(self._vectors), len(target._vectors)
        # Simplified: pair vectors by index, pad with zero vectors
        for i in range(max(m, n)):
            v1 = self._vectors[i] if i < m else FluxVector.zero()
            v2 = target._vectors[i] if i < n else FluxVector.zero()
            total_cost += v1.distance_to(v2, weighted=True)

        return total_cost

    # ---- helpers ----

    def _active_channels(self, threshold: float = 0.01) -> set[int]:
        """Get the set of active channel indices across all vectors."""
        active: set[int] = set()
        for v in self._vectors:
            for i, val in enumerate(v.values):
                if abs(val) > threshold:
                    active.add(i)
        return active

    def correlation(self) -> float:
        """Mean pairwise cosine correlation between vectors."""
        if len(self._vectors) < 2:
            return 1.0

        total = 0.0
        pairs = 0
        for i in range(len(self._vectors)):
            for j in range(i + 1, len(self._vectors)):
                total += self._vectors[i].cosine_similarity(self._vectors[j])
                pairs += 1

        return total / max(pairs, 1)

    def __repr__(self) -> str:
        return (
            f"HarmonyState(size={self.size}, "
            f"quality={self.quality()}, "
            f"consonance={self.consonance():.3f}, "
            f"correlation={self.correlation():.3f})"
        )
