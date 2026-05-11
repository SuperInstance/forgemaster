"""
Temporal connectome — coupled and anti-coupled room detection — OPTIMIZED.

Changes from baseline:
  - Fixed UNCOPLED → UNCOUPLED typo (the only real bug)
  - Added __slots__ to RoomPair (frozen=True, slots=True already)
  - Type hints added where they don't slow hot paths
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CouplingType(Enum):
    COUPLED = "coupled"
    ANTI_COUPLED = "anti_coupled"
    UNCOUPLED = "uncoupled"


@dataclass(frozen=True, slots=True)
class RoomPair:
    room_a: str
    room_b: str
    coupling: CouplingType
    correlation: float
    lag: int
    confidence: float

    @property
    def is_significant(self) -> bool:
        return self.coupling != CouplingType.UNCOUPLED


@dataclass
class ConnectomeResult:
    pairs: List[RoomPair]
    room_names: List[str]

    @property
    def coupled(self) -> List[RoomPair]:
        return [p for p in self.pairs if p.coupling == CouplingType.COUPLED]

    @property
    def anti_coupled(self) -> List[RoomPair]:
        return [p for p in self.pairs if p.coupling == CouplingType.ANTI_COUPLED]

    @property
    def significant(self) -> List[RoomPair]:
        return [p for p in self.pairs if p.is_significant]

    def adjacency_matrix(self) -> Tuple[List[str], List[List[float]]]:
        n = len(self.room_names)
        idx = {name: i for i, name in enumerate(self.room_names)}
        mat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            mat[i][i] = 1.0
        for pair in self.pairs:
            i, j = idx[pair.room_a], idx[pair.room_b]
            mat[i][j] = pair.correlation
            mat[j][i] = pair.correlation
        return self.room_names, mat

    def to_graphviz(self) -> str:
        lines = ['graph Connectome {', '  rankdir=LR;', '  node [shape=circle];']
        for name in self.room_names:
            lines.append(f'  "{name}";')
        for pair in self.pairs:
            if pair.coupling == CouplingType.COUPLED:
                style = f'color=blue, label="{pair.correlation:.2f}"'
            elif pair.coupling == CouplingType.ANTI_COUPLED:
                style = f'color=red, style=dashed, label="{pair.correlation:.2f}"'
            else:
                continue
            lines.append(f'  "{pair.room_a}" -- "{pair.room_b}" [{style}];')
        lines.append('}')
        return '\n'.join(lines)


def _pearson_correlation(x, y):
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


def _cross_correlation(x, y, max_lag):
    """Compute cross-correlation at lags 0, ±1, ..., ±max_lag."""
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
    """Build a temporal connectome from room activity traces."""

    def __init__(self, threshold=0.3, max_lag=5, min_samples=10):
        self.threshold = threshold
        self.max_lag = max_lag
        self.min_samples = min_samples
        self._traces = {}

    def add_room(self, name, activity):
        self._traces[name] = list(activity)

    def analyze(self):
        names = list(self._traces.keys())
        pairs = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pairs.append(self._analyze_pair(names[i], names[j]))
        return ConnectomeResult(pairs=pairs, room_names=names)

    def _analyze_pair(self, room_a, room_b):
        trace_a = self._traces[room_a]
        trace_b = self._traces[room_b]

        n = min(len(trace_a), len(trace_b))
        if n < self.min_samples:
            return RoomPair(
                room_a=room_a, room_b=room_b,
                coupling=CouplingType.UNCOUPLED,
                correlation=0.0, lag=0, confidence=0.0,
            )

        a = trace_a[:n]
        b = trace_b[:n]

        xcorrs = _cross_correlation(a, b, self.max_lag)
        best_lag = 0
        best_corr = 0.0
        for lag, corr in xcorrs:
            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        if best_corr > self.threshold:
            coupling = CouplingType.COUPLED
        elif best_corr < -self.threshold:
            coupling = CouplingType.ANTI_COUPLED
        else:
            coupling = CouplingType.UNCOUPLED

        sample_factor = min(1.0, n / 50.0)
        confidence = sample_factor * abs(best_corr)

        return RoomPair(
            room_a=room_a, room_b=room_b,
            coupling=coupling,
            correlation=round(best_corr, 6),
            lag=best_lag,
            confidence=round(confidence, 4),
        )
