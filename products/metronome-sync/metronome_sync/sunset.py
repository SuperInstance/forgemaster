"""Sunset and inheritance — graceful retirement of fleet nodes.

When a cadence caller (leader) retires, it produces a *sunset* payload containing
all calibration state. A successor *inherits* this state and takes over seamlessly.
"""

from __future__ import annotations

from fractions import Fraction
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class SunsetPayload:
    """Complete calibration state for handoff."""
    true_time: Fraction
    offset: Fraction
    drift_rate: Fraction
    deadband: Fraction = Fraction(1, 10000)
    tick_count: int = 0
    correction_mode: str = "GENTLE"

    def to_dict(self) -> Dict[str, str]:
        return {
            "true_time": str(self.true_time),
            "offset": str(self.offset),
            "drift_rate": str(self.drift_rate),
            "deadband": str(self.deadband),
            "tick_count": str(self.tick_count),
            "correction_mode": self.correction_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SunsetPayload":
        return cls(
            true_time=Fraction(data["true_time"]),
            offset=Fraction(data["offset"]),
            drift_rate=Fraction(data["drift_rate"]),
            deadband=Fraction(data.get("deadband", "1/10000")),
            tick_count=int(data.get("tick_count", 0)),
            correction_mode=data.get("correction_mode", "GENTLE"),
        )


@dataclass
class PlatoTile:
    """A single PLATO tile — a persisted unit of calibration knowledge."""
    tick: int
    agent_id: str
    key: str
    value: str


def sunset(clock_state: Dict[str, Fraction], tick_count: int = 0) -> SunsetPayload:
    """Create a sunset payload from clock state."""
    return SunsetPayload(
        true_time=clock_state.get("true_time", Fraction(0)),
        offset=clock_state.get("offset", Fraction(0)),
        drift_rate=clock_state.get("drift_rate", Fraction(0)),
        tick_count=tick_count,
    )


def inherit(payload: SunsetPayload) -> Dict[str, Fraction]:
    """Inherit calibration from a sunset payload.

    Returns a dict suitable for initializing a new FractionClock.
    """
    return {
        "true_time": payload.true_time,
        "offset": payload.offset,
        "drift_rate": payload.drift_rate,
        "deadband": payload.deadband,
    }


def tiles_from_history(
    agent_id: str,
    ticks: list[tuple[int, Fraction, Fraction]],
) -> list[PlatoTile]:
    """Generate PLATO tiles from tick history.

    Args:
        agent_id: The agent identifier
        ticks: List of (tick_number, local_time, drift) tuples

    Returns:
        List of PlatoTile objects for persistence
    """
    tiles = []
    for tick_num, local_time, drift in ticks:
        tiles.append(PlatoTile(tick=tick_num, agent_id=agent_id, key="local_time", value=str(local_time)))
        tiles.append(PlatoTile(tick=tick_num, agent_id=agent_id, key="drift", value=str(drift)))
    return tiles
