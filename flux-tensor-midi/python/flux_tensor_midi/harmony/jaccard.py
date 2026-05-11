"""
Jaccard similarity for FluxVector comparisons.

Jaccard index measures overlap between two sets.  Applied to
FluxVector space, it tells us how much two rooms' harmonic
content shares.
"""

from __future__ import annotations
import math
from flux_tensor_midi.core.flux import FluxVector


def jaccard_index(
    a: FluxVector,
    b: FluxVector,
    threshold: float = 0.01,
) -> float:
    """Jaccard similarity between two FluxVectors.

    Considers a channel "active" if its value is above threshold.

    Parameters
    ----------
    a, b : FluxVector
    threshold : float, default=0.01
        Minimum value to consider a channel active.

    Returns
    -------
    float
        Jaccard index (0 = disjoint, 1 = identical active sets).
    """
    active_a = {i for i, v in enumerate(a.values) if abs(v) > threshold}
    active_b = {i for i, v in enumerate(b.values) if abs(v) > threshold}

    intersection = active_a & active_b
    union = active_a | active_b

    if not union:
        return 1.0  # both silent = perfect agreement

    return len(intersection) / len(union)


def weighted_jaccard(
    a: FluxVector,
    b: FluxVector,
) -> float:
    """Weighted Jaccard using min/max of salience-weighted values.

    Treats each channel as having a magnitude; the index is
    sum(min(a_i, b_i)) / sum(max(a_i, b_i)).

    Returns 1.0 if both are all-zero.
    """
    a_vals = [v * s for v, s in zip(a.values, a.salience)]
    b_vals = [v * s for v, s in zip(b.values, b.salience)]

    numerator = sum(min(av, bv) for av, bv in zip(a_vals, b_vals))
    denominator = sum(max(av, bv) for av, bv in zip(a_vals, b_vals))

    if denominator == 0.0:
        return 1.0

    return numerator / denominator


def jaccard_distance(a: FluxVector, b: FluxVector, threshold: float = 0.01) -> float:
    """Jaccard distance = 1 - Jaccard index."""
    return 1.0 - jaccard_index(a, b, threshold)
