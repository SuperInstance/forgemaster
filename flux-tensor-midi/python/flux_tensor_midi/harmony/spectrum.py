"""
Spectral analysis of FluxVector sequences.

Treats a sequence of FluxVectors as a time series and computes
spectral features: dominant frequency, spectral centroid,
spectral flux, and autocorrelation.
"""

from __future__ import annotations
import math
from typing import Sequence
from flux_tensor_midi.core.flux import FluxVector


def spectral_centroid(vectors: Sequence[FluxVector], channel: int = 0) -> float:
    """Spectral centroid of a single channel across time.

    Higher centroid = faster harmonic changes.

    Parameters
    ----------
    vectors : Sequence[FluxVector]
        Ordered sequence of FluxVectors.
    channel : int, default=0
        Channel to analyze.

    Returns
    -------
    float
        Weighted mean frequency bin (0 = DC).
    """
    if not vectors:
        return 0.0

    values = [v[channel] for v in vectors]
    centroid = sum(i * abs(values[i]) for i in range(len(values)))

    total_magnitude = sum(abs(v) for v in values)
    if total_magnitude == 0.0:
        return 0.0

    return centroid / total_magnitude


def spectral_flux(vectors: Sequence[FluxVector]) -> float:
    """Spectral flux: average rate of change across all channels.

    Higher flux = more harmonic motion.
    """
    if len(vectors) < 2:
        return 0.0

    total_flux = 0.0
    for i in range(1, len(vectors)):
        total_flux += vectors[i].distance_to(vectors[i - 1])

    return total_flux / (len(vectors) - 1)


def salience_weighted_flux(vectors: Sequence[FluxVector]) -> float:
    """Spectral flux weighted by salience."""
    if len(vectors) < 2:
        return 0.0

    total_flux = 0.0
    for i in range(1, len(vectors)):
        total_flux += vectors[i].distance_to(vectors[i - 1], weighted=True)

    return total_flux / (len(vectors) - 1)


def dominant_channel(vectors: Sequence[FluxVector]) -> int:
    """Find the channel with the highest mean absolute value.

    Returns -1 if no vectors.
    """
    if not vectors:
        return -1

    means = [0.0] * 9
    for v in vectors:
        for i in range(9):
            means[i] += abs(v[i])

    n = len(vectors)
    for i in range(9):
        means[i] /= n

    max_mean = max(means)
    if max_mean == 0.0:
        return -1

    return means.index(max_mean)


def autocorrelation(vectors: Sequence[FluxVector], max_lag: int = 4) -> list[float]:
    """Autocorrelation of the magnitude sequence.

    Helps detect periodicity in harmonic activity.

    Parameters
    ----------
    vectors : Sequence[FluxVector]
    max_lag : int, default=4
        Maximum lag to compute.

    Returns
    -------
    list[float]
        Correlation values for lag 0..max_lag.
    """
    magnitudes = [v.magnitude for v in vectors]
    n = len(magnitudes)

    if n < 2:
        return [1.0] * (max_lag + 1) if magnitudes else [0.0] * (max_lag + 1)

    mean = sum(magnitudes) / n
    variance = sum((x - mean) ** 2 for x in magnitudes)
    if variance == 0:
        return [1.0] + [0.0] * max_lag

    results: list[float] = []
    for lag in range(min(max_lag + 1, n)):
        if lag == 0:
            results.append(1.0)
        else:
            cov = sum(
                (magnitudes[i] - mean) * (magnitudes[i + lag] - mean)
                for i in range(n - lag)
            )
            results.append(cov / variance)

    # Pad with zeros if not enough data
    while len(results) <= max_lag:
        results.append(0.0)

    return results
