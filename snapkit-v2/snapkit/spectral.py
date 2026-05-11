"""
Spectral analysis — entropy, Hurst exponent, autocorrelation — OPTIMIZED.

Changes from baseline:
  - Autocorrelation: local variable caching, pre-computed inv_n and inv_r0
  - Hurst exponent: reduced allocation, inline min/max in cumulative deviations
  - Added __slots__ to SpectralSummary
  - Batch operations
  - Type hints on signatures only (not in hot body — CPython 3.10 overhead)
  - Precomputed constants (1/e, log(2))
"""

import math
from typing import List, Optional
from dataclasses import dataclass


def entropy(data: List[float], bins: int = 10) -> float:
    """Compute Shannon entropy via histogram binning."""
    n = len(data)
    if n < 2:
        return 0.0

    # Inline min/max for speed
    min_val = data[0]
    max_val = data[0]
    for x in data:
        if x < min_val:
            min_val = x
        elif x > max_val:
            max_val = x

    if max_val == min_val:
        return 0.0

    inv_range = bins / (max_val - min_val)
    counts = [0] * bins

    for x in data:
        idx = int((x - min_val) * inv_range)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1

    inv_n = 1.0 / n
    inv_log2 = 1.0 / math.log(2)
    h = 0.0
    for c in counts:
        if c > 0:
            p = c * inv_n
            h -= p * math.log(p) * inv_log2

    return h


def autocorrelation(
    data: List[float],
    max_lag: Optional[int] = None,
) -> List[float]:
    """Compute normalized autocorrelation.

    OPTIMIZED: Single-pass centering, local variable caching, pre-computed inv_r0.
    """
    n = len(data)
    if n < 2:
        return [1.0]

    if max_lag is None:
        max_lag = n // 2
    max_lag = min(max_lag, n - 1)

    inv_n = 1.0 / n
    mean = sum(data) * inv_n

    # Center and compute variance in one pass
    centered = [x - mean for x in data]
    r0 = 0.0
    for x in centered:
        r0 += x * x
    r0 *= inv_n

    if r0 == 0:
        return [1.0] + [0.0] * max_lag

    inv_r0 = 1.0 / r0
    result = [0.0] * (max_lag + 1)

    c = centered  # local reference avoids global lookup
    for lag in range(max_lag + 1):
        rk = 0.0
        limit = n - lag
        for t in range(limit):
            rk += c[t] * c[t + lag]
        result[lag] = rk * inv_n * inv_r0

    return result


def hurst_exponent(data: List[float]) -> float:
    """Estimate Hurst exponent via R/S analysis.

    OPTIMIZED: Inline min/max in cumulative deviations, geometric size progression.
    """
    n = len(data)
    if n < 20:
        return 0.5

    inv_n = 1.0 / n
    mean_val = sum(data) * inv_n
    centered = [x - mean_val for x in data]

    # Geometric progression of test sizes
    test_sizes = []
    s = 16
    while s <= n // 2:
        test_sizes.append(s)
        s = s * 2 if s * 2 <= n // 2 else int(s * 1.5)
        if s == test_sizes[-1]:
            break

    if not test_sizes:
        if n >= 8:
            test_sizes = [n // 4]
        else:
            test_sizes = [n]
        test_sizes = [s for s in test_sizes if s >= 4]

    sizes = []
    rs_values = []

    _log = math.log
    _sqrt = math.sqrt

    for size in test_sizes:
        if size < 4 or size > n:
            continue

        num_subseries = n // size
        if num_subseries < 1:
            continue

        inv_size = 1.0 / size
        rs_sum = 0.0
        rs_count = 0

        for i in range(num_subseries):
            start = i * size
            sub = centered[start: start + size]
            sub_mean = sum(sub) * inv_size

            # Inline cumulative deviations with min/max tracking
            running = 0.0
            cum_min = 0.0
            cum_max = 0.0
            for x in sub:
                running += x - sub_mean
                if running < cum_min:
                    cum_min = running
                elif running > cum_max:
                    cum_max = running

            r = cum_max - cum_min

            var = 0.0
            for x in sub:
                d = x - sub_mean
                var += d * d
            var *= inv_size

            if var > 1e-20:
                rs_sum += r / _sqrt(var)
                rs_count += 1

        if rs_count > 0:
            avg_rs = rs_sum / rs_count
            if avg_rs > 0:
                sizes.append(size)
                rs_values.append(avg_rs)

    if len(sizes) < 2:
        return 0.5

    # Linear regression on log-log
    n_pts = len(sizes)
    log_n = [_log(s) for s in sizes]
    log_rs = [_log(r) for r in rs_values]

    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x2 = 0.0

    for i in range(n_pts):
        lx = log_n[i]
        ly = log_rs[i]
        sum_x += lx
        sum_y += ly
        sum_xy += lx * ly
        sum_x2 += lx * lx

    denom = n_pts * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.5

    h = (n_pts * sum_xy - sum_x * sum_y) / denom
    return max(0.0, min(1.0, h))


@dataclass
class SpectralSummary:
    """Summary of spectral analysis on a signal."""
    __slots__ = ('entropy_bits', 'hurst', 'autocorr_lag1',
                 'autocorr_decay', 'is_stationary')

    entropy_bits: float
    hurst: float
    autocorr_lag1: float
    autocorr_decay: float
    is_stationary: bool


def spectral_summary(
    data: List[float],
    bins: int = 10,
    max_lag: Optional[int] = None,
) -> SpectralSummary:
    """Compute a complete spectral summary of a signal."""
    h = entropy(data, bins)
    hurst_val = hurst_exponent(data)
    acf = autocorrelation(data, max_lag)

    acf_lag1 = acf[1] if len(acf) > 1 else 0.0

    # Precomputed 1/e
    decay_lag = float(len(acf))
    threshold = 0.36787944117144233
    for i in range(1, len(acf)):
        if abs(acf[i]) < threshold:
            decay_lag = float(i)
            break

    is_stationary = (0.4 <= hurst_val <= 0.6) and abs(acf_lag1) < 0.3

    return SpectralSummary(
        entropy_bits=h,
        hurst=hurst_val,
        autocorr_lag1=acf_lag1,
        autocorr_decay=decay_lag,
        is_stationary=is_stationary,
    )


def spectral_batch(
    series_list: List[List[float]],
    bins: int = 10,
    max_lag: Optional[int] = None,
) -> List[SpectralSummary]:
    """Compute spectral summary for multiple time series."""
    return [spectral_summary(data, bins, max_lag) for data in series_list]
