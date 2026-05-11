"""
Temporal connectome — coupled and anti-coupled room detection.

A temporal connectome maps the coupling relationships between rooms
in the Cocapn fleet. Two rooms are:

  - **Coupled** (in-phase): their activity patterns rise and fall together.
    Correlation > threshold.
  - **Anti-coupled** (anti-phase): when one room is active, the other
    quiets. Correlation < -threshold.
  - **Uncoupled**: no significant correlation.

This module provides tools to detect these relationships from temporal
activity traces, building a connectome graph of the fleet.

Algorithm:
  1. Compute cross-correlation between each pair of room activity traces.
  2. Classify pairs by correlation sign and magnitude.
  3. Estimate coupling lag (which room leads, which follows).
  4. Output the connectome as a graph of room pairs.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CouplingType(Enum):
    """Classification of coupling between two rooms."""
    COUPLED = "coupled"             # positive correlation above threshold
    ANTI_COUPLED = "anti_coupled"   # negative correlation below -threshold
    UNCOUPLED = "uncoupled"         # no significant correlation


@dataclass(frozen=True, slots=True)
class RoomPair:
    """A pair of rooms with their coupling relationship."""
    room_a: str
    room_b: str
    coupling: CouplingType
    correlation: float          # Pearson correlation coefficient
    lag: int                    # lag in samples (positive = room_b leads room_a)
    confidence: float           # [0, 1] based on sample count and correlation strength

    @property
    def is_significant(self) -> bool:
        return self.coupling != CouplingType.UNCOPLED


@dataclass
class ConnectomeResult:
    """Complete connectome analysis result."""
    pairs: List[RoomPair]
    room_names: List[str]

    @property
    def coupled(self) -> List[RoomPair]:
        """All coupled (in-phase) pairs."""
        return [p for p in self.pairs if p.coupling == CouplingType.COUPLED]

    @property
    def anti_coupled(self) -> List[RoomPair]:
        """All anti-coupled pairs."""
        return [p for p in self.pairs if p.coupling == CouplingType.ANTI_COUPLED]

    @property
    def significant(self) -> List[RoomPair]:
        """All pairs with significant coupling."""
        return [p for p in self.pairs if p.is_significant]

    def adjacency_matrix(self) -> Tuple[List[str], List[List[float]]]:
        """Build a correlation adjacency matrix.

        Returns:
            (room_names, matrix) where matrix[i][j] = correlation between rooms i and j.
        """
        n = len(self.room_names)
        idx = {name: i for i, name in enumerate(self.room_names)}
        mat = [[0.0] * n for _ in range(n)]

        for i in range(n):
            mat[i][i] = 1.0  # self-correlation

        for pair in self.pairs:
            i, j = idx[pair.room_a], idx[pair.room_b]
            mat[i][j] = pair.correlation
            mat[j][i] = pair.correlation

        return self.room_names, mat

    def to_graphviz(self) -> str:
        """Render connectome as Graphviz DOT format."""
        lines = ['graph Connectome {']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=circle];')

        for name in self.room_names:
            lines.append(f'  "{name}";')

        for pair in self.pairs:
            if pair.coupling == CouplingType.COUPLED:
                style = f'color=blue, label="{pair.correlation:.2f}"'
            elif pair.coupling == CouplingType.ANTI_COUPLED:
                style = f'color=red, style=dashed, label="{pair.correlation:.2f}"'
            else:
                continue  # skip uncoupled
            lines.append(f'  "{pair.room_a}" -- "{pair.room_b}" [{style}];')

        lines.append('}')
        return '\n'.join(lines)


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient between two sequences."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = 0.0
    var_x = 0.0
    var_y = 0.0
    for i in range(n):
        dx = x[i] - mean_x
        dy = y[i] - mean_y
        cov += dx * dy
        var_x += dx * dx
        var_y += dy * dy

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-15:
        return 0.0
    return cov / denom


def _cross_correlation(
    x: List[float], y: List[float], max_lag: int
) -> List[Tuple[int, float]]:
    """Compute cross-correlation at lags 0, ±1, ..., ±max_lag.

    Returns list of (lag, correlation) pairs.
    """
    n = len(x)
    results = []

    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            xx = x[:n - lag] if lag < n else []
            yy = y[lag:] if lag < n else []
        else:
            xx = x[-lag:] if -lag < n else []
            yy = y[:n + lag] if -lag < n else []

        if len(xx) < 3:
            results.append((lag, 0.0))
        else:
            results.append((lag, _pearson_correlation(xx, yy)))

    return results


class TemporalConnectome:
    """Build a temporal connectome from room activity traces.

    Usage:
        tc = TemporalConnectome(threshold=0.3, max_lag=5)
        tc.add_room("bridge", activity=[0.1, 0.5, 0.8, ...])
        tc.add_room("engineering", activity=[0.2, 0.6, 0.7, ...])
        result = tc.analyze()
        for pair in result.coupled:
            print(f"{pair.room_a} <-> {pair.room_b}: r={pair.correlation:.3f}")
    """

    def __init__(
        self,
        threshold: float = 0.3,
        max_lag: int = 5,
        min_samples: int = 10,
    ):
        """
        Args:
            threshold: Absolute correlation threshold for coupling classification.
            max_lag: Maximum lag to test in cross-correlation (samples).
            min_samples: Minimum number of samples required for analysis.
        """
        self.threshold = threshold
        self.max_lag = max_lag
        self.min_samples = min_samples
        self._traces: Dict[str, List[float]] = {}

    def add_room(self, name: str, activity: List[float]) -> None:
        """Register an activity trace for a room.

        Args:
            name: Room identifier.
            activity: Time series of activity levels.
        """
        self._traces[name] = list(activity)

    def analyze(self) -> ConnectomeResult:
        """Analyze all room pairs and build the connectome.

        Returns:
            ConnectomeResult with all detected coupling relationships.
        """
        names = list(self._traces.keys())
        pairs: List[RoomPair] = []

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pair = self._analyze_pair(names[i], names[j])
                pairs.append(pair)

        return ConnectomeResult(pairs=pairs, room_names=names)

    def _analyze_pair(self, room_a: str, room_b: str) -> RoomPair:
        """Analyze coupling between two rooms."""
        trace_a = self._traces[room_a]
        trace_b = self._traces[room_b]

        # Align to same length
        n = min(len(trace_a), len(trace_b))
        if n < self.min_samples:
            return RoomPair(
                room_a=room_a,
                room_b=room_b,
                coupling=CouplingType.UNCOPLED,
                correlation=0.0,
                lag=0,
                confidence=0.0,
            )

        a = trace_a[:n]
        b = trace_b[:n]

        # Cross-correlation to find optimal lag
        xcorrs = _cross_correlation(a, b, self.max_lag)
        best_lag = 0
        best_corr = 0.0
        for lag, corr in xcorrs:
            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        # Classify coupling
        if best_corr > self.threshold:
            coupling = CouplingType.COUPLED
        elif best_corr < -self.threshold:
            coupling = CouplingType.ANTI_COUPLED
        else:
            coupling = CouplingType.UNCOPLED

        # Confidence based on sample count and correlation magnitude
        # Using a simplified Fisher z-transformation approximation
        sample_factor = min(1.0, n / 50.0)  # ramps up to 1.0 at 50 samples
        corr_factor = abs(best_corr)
        confidence = sample_factor * corr_factor

        return RoomPair(
            room_a=room_a,
            room_b=room_b,
            coupling=coupling,
            correlation=round(best_corr, 6),
            lag=best_lag,
            confidence=round(confidence, 4),
        )
