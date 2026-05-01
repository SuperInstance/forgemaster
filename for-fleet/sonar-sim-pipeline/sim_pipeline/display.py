"""Sonar display engine.

Generates ASCII waterfall plots and JSON exports from ping data.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DisplayPing:
    """Simplified ping for display/export.

    Attributes:
        ping_index: Sequential ping number.
        x: Vehicle x-position in meters.
        y: Vehicle y-position in meters.
        z: Vehicle depth in meters.
        two_way_time: Round-trip travel time in seconds.
        bottom_return: Normalized bottom return intensity.
        range_m: Slant range in meters.
        beams: Number of beams (for multi-beam).
        beam_returns: Tuple of per-beam returns if multi-beam.
    """
    ping_index: int
    x: float
    y: float
    z: float
    two_way_time: float
    bottom_return: float
    range_m: float
    beams: int = 1
    beam_returns: tuple[float, ...] = ()


class SonarDisplay:
    """Display engine for sonar simulation output.

    Provides:
    - ASCII waterfall plots (for CLI / logging)
    - JSON export with metadata
    """

    # ASCII intensity ramp from dark to bright
    RAMP = " .:-=+*#%@"

    def __init__(self, max_ramp: int = 255) -> None:
        """Initialize display engine.

        Args:
            max_ramp: Maximum intensity value for normalization.
        """
        self.max_ramp = max_ramp
        logger.debug("SonarDisplay initialized")

    def _intensity_to_char(self, value: float) -> str:
        """Map normalized intensity [0, 1] to ASCII character."""
        if math.isnan(value):
            return "?"
        idx = int(value * (len(self.RAMP) - 1))
        idx = max(0, min(len(self.RAMP) - 1, idx))
        return self.RAMP[idx]

    def waterfall_ascii(
        self,
        pings: Sequence[DisplayPing],
        width: int = 80,
        height: int = 24,
        mode: str = "single_beam",
    ) -> str:
        """Generate an ASCII waterfall plot.

        Args:
            pings: Sequence of pings (time on x-axis).
            width: Plot width in characters.
            height: Plot height in characters.
            mode: "single_beam" or "multi_beam".

        Returns:
            Multi-line ASCII string.
        """
        if not pings:
            return "(no pings)"

        # Subsample pings to fit width
        n_pings = len(pings)
        if n_pings > width:
            step = n_pings // width
            sampled = [pings[i] for i in range(0, n_pings, step)]
        else:
            sampled = list(pings)

        actual_width = min(len(sampled), width)

        if mode == "multi_beam" and sampled and sampled[0].beam_returns:
            # Multi-beam: beams on y-axis, pings on x-axis
            n_beams = len(sampled[0].beam_returns)
            grid: list[list[float]] = [[0.0] * actual_width for _ in range(height)]
            for col, ping in enumerate(sampled[:actual_width]):
                returns = ping.beam_returns
                if not returns:
                    continue
                for row in range(height):
                    beam_idx = int(row * (n_beams - 1) / max(height - 1, 1))
                    beam_idx = min(beam_idx, len(returns) - 1)
                    grid[row][col] = returns[beam_idx]

            lines: list[str] = []
            for row in reversed(range(height)):
                line = "".join(self._intensity_to_char(grid[row][c]) for c in range(actual_width))
                lines.append(line)
        else:
            # Single beam: depth/range on y-axis, ping index on x-axis
            max_range = max(p.range_m for p in sampled) if sampled else 1.0
            if max_range <= 0:
                max_range = 1.0
            grid = [[0.0] * actual_width for _ in range(height)]
            for col, ping in enumerate(sampled[:actual_width]):
                row = int((ping.range_m / max_range) * (height - 1))
                row = max(0, min(height - 1, row))
                grid[row][col] = ping.bottom_return

            lines = []
            for row in reversed(range(height)):
                line = "".join(self._intensity_to_char(grid[row][c]) for c in range(actual_width))
                lines.append(line)

        # Add header/footer
        header = f"Waterfall ({mode}) - {n_pings} pings"
        separator = "-" * actual_width
        return "\n".join([header, separator] + lines + [separator])

    def to_json(
        self,
        pings: Sequence[DisplayPing],
        mission_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Serialize pings and metadata to a JSON-serializable dict.

        Args:
            pings: Sequence of DisplayPing.
            mission_metadata: Optional mission-level metadata.

        Returns:
            Dictionary ready for json.dumps.
        """
        ts = datetime.now(timezone.utc).isoformat()
        payload = {
            "version": "1.0.0",
            "timestamp": ts,
            "mission": mission_metadata or {},
            "pings": [
                {
                    "ping_index": p.ping_index,
                    "position_m": {"x": round(p.x, 3), "y": round(p.y, 3), "z": round(p.z, 3)},
                    "two_way_time_s": round(p.two_way_time, 6),
                    "bottom_return": round(p.bottom_return, 6),
                    "range_m": round(p.range_m, 3),
                    "beams": p.beams,
                    "beam_returns": [round(v, 6) for v in p.beam_returns] if p.beam_returns else None,
                }
                for p in pings
            ],
        }
        return payload

    def save_json(
        self,
        pings: Sequence[DisplayPing],
        filepath: str,
        mission_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save pings to a JSON file.

        Args:
            pings: Sequence of DisplayPing.
            filepath: Output file path.
            mission_metadata: Optional mission metadata.

        Returns:
            Absolute path to written file.
        """
        payload = self.to_json(pings, mission_metadata)
        abs_path = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info("Saved JSON output to %s", abs_path)
        return abs_path

    def save_csv(
        self,
        pings: Sequence[DisplayPing],
        filepath: str,
    ) -> str:
        """Save pings to a simple CSV file.

        Args:
            pings: Sequence of DisplayPing.
            filepath: Output file path.

        Returns:
            Absolute path to written file.
        """
        abs_path = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write("ping_index,x,y,z,two_way_time_s,bottom_return,range_m,beams\n")
            for p in pings:
                f.write(
                    f"{p.ping_index},{p.x:.3f},{p.y:.3f},{p.z:.3f},"
                    f"{p.two_way_time:.6f},{p.bottom_return:.6f},"
                    f"{p.range_m:.3f},{p.beams}\n"
                )
        logger.info("Saved CSV output to %s", abs_path)
        return abs_path
