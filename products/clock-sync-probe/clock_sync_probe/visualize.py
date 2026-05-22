"""ASCII art timeline visualization of clock drift over time."""

from __future__ import annotations

import math
from typing import Sequence

from .probe import SyncResult


def ascii_timeline(results: Sequence[SyncResult], width: int = 60, height: int = 16) -> str:
    """Render an ASCII chart of offset over time for each strategy."""
    if not results:
        return "No results to visualize."

    lines: list[str] = []

    for result in results:
        lines.append(_render_single(result, width, height))
        lines.append("")

    # Summary
    lines.append("─" * width)
    ranked = sorted(results, key=lambda r: r.score)
    lines.append("Strategy ranking (best → worst):")
    for i, r in enumerate(ranked, 1):
        lines.append(
            f"  {i}. {r.strategy:<12}  residual={r.residual_offset_ms:6.2f}ms  "
            f"jitter={r.jitter_ms:6.2f}ms  δ={r.delta_ms:6.2f}ms  "
            f"convergence={r.convergence_ticks} ticks"
        )

    return "\n".join(lines)


def _render_single(result: SyncResult, width: int, height: int) -> str:
    """Render one strategy's offset over time as ASCII."""
    offsets = result.offsets
    if not offsets:
        return f"{result.strategy}: (no data)"

    # Downsample to `width` points
    step = max(1, len(offsets) // width)
    sampled = offsets[::step][:width]

    max_val = max(abs(v) for v in sampled) or 1.0
    # Add some headroom
    max_val *= 1.2

    chars = []
    for val in sampled:
        # Map to 0..height-1
        normalized = abs(val) / max_val
        row = int(normalized * (height - 1))
        row = min(row, height - 1)
        chars.append(row)

    # Build the chart top-down
    rows: list[str] = []
    for y in range(height - 1, -1, -1):
        line_chars = []
        for c in chars:
            if c >= y:
                line_chars.append("█")
            elif c >= y - 1:
                line_chars.append("▄")
            else:
                line_chars.append(" ")
        rows.append("".join(line_chars))

    # Y-axis labels
    max_label = f"{max_val:.1f}"
    mid_label = f"{max_val/2:.1f}"
    zero_label = "0.0"

    header = f"  {result.strategy} — offset (ms) over time"
    if len(header) > width:
        header = header[:width]

    lines = [header, "┌" + "─" * width + "┐"]
    for i, row in enumerate(rows):
        if i == 0:
            label = max_label.rjust(6)
        elif i == height // 2:
            label = mid_label.rjust(6)
        elif i == height - 1:
            label = zero_label.rjust(6)
        else:
            label = " " * 6
        lines.append(f"{label}│{row}│")
    lines.append("      └" + "─" * width + "┘")
    lines.append("       " + "^" * 4 + " time →")

    return "\n".join(lines)


def quick_summary(result: SyncResult) -> str:
    """One-line summary of a result."""
    return (
        f"[{result.strategy}] residual={result.residual_offset_ms:.2f}ms  "
        f"jitter={result.jitter_ms:.2f}ms  δ={result.delta_ms:.2f}ms  "
        f"converged@{result.convergence_ticks}ticks"
    )
