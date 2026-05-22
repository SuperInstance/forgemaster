"""ASCII/Rich charts for fleet visualization."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"
BLOCK_CHARS = " ▏▎▍▌▋▊▉█"
HEAT_CHARS = " ░▒▓█"


def sparkline(values: list[float], width: int = 40) -> str:
    """Render a sparkline from numeric values, down/up-sampled to *width* chars."""
    if not values:
        return ""
    sampled = _resample(values, width)
    lo, hi = min(sampled), max(sampled)
    rng = hi - lo or 1.0
    chars = []
    for v in sampled:
        idx = int((v - lo) / rng * (len(SPARKLINE_CHARS) - 1))
        chars.append(SPARKLINE_CHARS[max(0, min(idx, len(SPARKLINE_CHARS) - 1))])
    return "".join(chars)


def bar_chart(labels: list[str], values: list[float], width: int = 30, max_bar: int = 20) -> str:
    """Render a horizontal bar chart with labels."""
    if not values:
        return ""
    lo = min(min(values), 0)
    hi = max(values)
    rng = hi - lo or 1.0
    lines = []
    for label, v in zip(labels, values):
        bar_len = int((v - lo) / rng * max_bar)
        bar_len = max(0, min(bar_len, max_bar))
        bar = BLOCK_CHARS[-1] * bar_len
        lines.append(f"{label:>12s} │{bar:<{max_bar}s}│ {v:+.3f}s")
    return "\n".join(lines)


def heat_map(matrix: list[list[float]], row_labels: list[str] | None = None,
             col_labels: list[str] | None = None) -> str:
    """Render a heat-map for a latency matrix."""
    if not matrix:
        return ""
    n_rows = len(matrix)
    n_cols = max(len(r) for r in matrix) if matrix else 0
    flat = [v for row in matrix for v in row]
    lo, hi = min(flat), max(flat)
    rng = hi - lo or 1.0
    lines: list[str] = []
    if col_labels:
        header = " " * 12 + " ".join(f"{l:^5s}" for l in col_labels[:n_cols])
        lines.append(header)
    for i, row in enumerate(matrix):
        lbl = (row_labels[i] if row_labels and i < len(row_labels) else str(i)).rjust(12)
        cells = []
        for j in range(n_cols):
            v = row[j] if j < len(row) else 0.0
            idx = int((v - lo) / rng * (len(HEAT_CHARS) - 1))
            cells.append(HEAT_CHARS[max(0, min(idx, len(HEAT_CHARS) - 1))] * 2)
        lines.append(f"{lbl} {''.join(cells)}")
    return "\n".join(lines)


def _resample(values: list[float], target: int) -> list[float]:
    """Down/up-sample *values* to *target* points via averaging."""
    if len(values) == target:
        return list(values)
    out: list[float] = []
    step = len(values) / target
    for i in range(target):
        start = int(i * step)
        end = min(int((i + 1) * step), len(values))
        chunk = values[start:end]
        out.append(sum(chunk) / len(chunk) if chunk else 0.0)
    return out
