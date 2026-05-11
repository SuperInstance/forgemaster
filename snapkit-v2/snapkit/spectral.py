"""
Spectral analysis — entropy, Hurst exponent, autocorrelation.

All implementations use only the Python standard library.
These are temporal spectral analysis tools that complement the
Eisenstein spatial snap and the temporal beat grid.

References:
  - Shannon entropy: H = -Σ p_i log2(p_i)
  - Hurst exponent: R/S analysis (rescaled range method)
  - Autocorrelation: biased estimator, normalized
"""

import math
from typing import List, Optional, Tuple
from dataclasses import dataclass


def entropy(data: List[float], bins: int = 10) -> float:
    """Compute Shannon entropy of a 1D signal via histogram binning.

    Args:
        data: Input signal values.
        bins: Number of histogram bins.

    Returns:
        Shannon entropy in bits (base-2 logarithm).
        Returns 0.0 for constant signals or empty data.
    """
    if len(data) < 2:
        return 0.0

    min_val = min(data)
    max_val = max(data)
    if max_val == min_val:
        return 0.0

    bin_width = (max_val - min_val) / bins
    counts = [0] * bins

    for x in data:
        idx = int((x - min_val) / bin_width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1

    n = len(data)
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / n
            h -= p * math.log2(p)

    return h


def autocorrelation(
    data: List[float],
    max_lag: Optional[int] = None,
) -> List[float]:
    """Compute normalized autocorrelation of a signal.

    Uses the biased estimator: R(k) = (1/N) Σ x(t)·x(t+k)
    Normalized: ρ(k) = R(k) / R(0)

    Args:
        data: Input signal values.
        max_lag: Maximum lag to compute. Defaults to len(data) // 2.

    Returns:
        List of autocorrelation values for lags 0, 1, ..., max_lag.
    """
    n = len(data)
    if n < 2:
        return [1.0]

    if max_lag is None:
        max_lag = n // 2
    max_lag = min(max_lag, n - 1)

    mean = sum(data) / n
    centered = [x - mean for x in data]

    # Variance (R(0))
    r0 = sum(x * x for x in centered) / n
    if r0 == 0:
        return [1.0] + [0.0] * max_lag

    result = []
    for lag in range(max_lag + 1):
        rk = sum(centered[t] * centered[t + lag] for t in range(n - lag)) / n
        result.append(rk / r0)

    return result


def hurst_exponent(data: List[float]) -> float:
    """Estimate the Hurst exponent using R/S (rescaled range) analysis.

    The Hurst exponent H characterizes the long-range correlation:
      H < 0.5: mean-reverting (anti-persistent)
      H ≈ 0.5: random walk (Brownian motion)
      H > 0.5: trending (persistent)

    Method:
      1. Split data into subseries of length n.
      2. For each subseries, compute R/S = (range of cumulative deviations) / std.
      3. Regress log(R/S) on log(n) to get H.

    Args:
        data: Input signal. Should have ≥ 100 points for reliable estimates.

    Returns:
        Estimated Hurst exponent, clamped to [0, 1].
    """
    n = len(data)
    if n < 20:
        return 0.5  # insufficient data, assume random walk

    mean_val = sum(data) / n
    centered = [x - mean_val for x in data]

    # Compute R/S for multiple subseries sizes
    sizes = []
    rs_values = []

    # Use powers of 2 and some intermediate sizes
    test_sizes = []
    s = 16
    while s <= n // 2:
        test_sizes.append(s)
        s = int(s * 1.5) if s * 2 > n // 2 else s * 2

    if not test_sizes:
        test_sizes = [n // 4] if n >= 8 else [n]
        test_sizes = [s for s in test_sizes if s >= 4]

    for size in test_sizes:
        if size < 4 or size > n:
            continue

        num_subseries = n // size
        if num_subseries < 1:
            continue

        rs_list = []
        for i in range(num_subseries):
            sub = centered[i * size: (i + 1) * size]
            sub_mean = sum(sub) / size

            # Cumulative deviations
            cum_dev = []
            running = 0.0
            for x in sub:
                running += x - sub_mean
                cum_dev.append(running)

            # Range of cumulative deviations
            r = max(cum_dev) - min(cum_dev)

            # Standard deviation
            var = sum((x - sub_mean) ** 2 for x in sub) / size
            s = math.sqrt(var) if var > 0 else 1e-10

            if s > 1e-10:
                rs_list.append(r / s)

        if rs_list:
            avg_rs = sum(rs_list) / len(rs_list)
            if avg_rs > 0:
                sizes.append(size)
                rs_values.append(avg_rs)

    if len(sizes) < 2:
        return 0.5

    # Linear regression on log-log: log(R/S) = log(c) + H·log(n)
    log_n = [math.log(s) for s in sizes]
    log_rs = [math.log(r) for r in rs_values]

    n_pts = len(log_n)
    sum_x = sum(log_n)
    sum_y = sum(log_rs)
    sum_xy = sum(a * b for a, b in zip(log_n, log_rs))
    sum_x2 = sum(a * a for a in log_n)

    denom = n_pts * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.5

    h = (n_pts * sum_xy - sum_x * sum_y) / denom
    return max(0.0, min(1.0, h))


@dataclass
class SpectralSummary:
    """Summary of spectral analysis on a signal."""
    entropy_bits: float
    hurst: float
    autocorr_lag1: float
    autocorr_decay: float  # lag where autocorrelation drops below 1/e
    is_stationary: bool    # Hurst ≈ 0.5 and low autocorrelation


def spectral_summary(
    data: List[float],
    bins: int = 10,
    max_lag: Optional[int] = None,
) -> SpectralSummary:
    """Compute a complete spectral summary of a signal.

    Args:
        data: Input signal.
        bins: Number of bins for entropy calculation.
        max_lag: Maximum lag for autocorrelation.

    Returns:
        SpectralSummary with all metrics.
    """
    h = entropy(data, bins)
    hurst_val = hurst_exponent(data)
    acf = autocorrelation(data, max_lag)

    acf_lag1 = acf[1] if len(acf) > 1 else 0.0

    # Find decay point (where |acf| drops below 1/e)
    decay_lag = float(len(acf))
    threshold = 1.0 / math.e
    for i, val in enumerate(acf):
        if i > 0 and abs(val) < threshold:
            decay_lag = float(i)
            break

    # Stationarity heuristic: H near 0.5 and low autocorrelation
    is_stationary = (0.4 <= hurst_val <= 0.6) and abs(acf_lag1) < 0.3

    return SpectralSummary(
        entropy_bits=h,
        hurst=hurst_val,
        autocorr_lag1=acf_lag1,
        autocorr_decay=decay_lag,
        is_stationary=is_stationary,
    )
