"""Metronome core: zero-drift clock sync using Pythagorean Fraction arithmetic."""

import sqlite3
import os
from fractions import Fraction
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class CorrectionMode(Enum):
    GENTLE = auto()
    AGGRESSIVE = auto()


@dataclass
class ClockState:
    """Agent's local clock state using exact Fraction arithmetic."""
    # True time as Fraction (never floats)
    true_time: Fraction = Fraction(0)
    # Local offset (drift accumulator)
    offset: Fraction = Fraction(0)
    # Drift rate: how fast local clock diverges (Fraction of true time per tick)
    drift_rate: Fraction = Fraction(0)
    # Last correction applied
    last_correction: Fraction = Fraction(0)
    # Correction mode
    correction_mode: CorrectionMode = CorrectionMode.GENTLE
    # Deadband: don't correct if drift < this
    deadband: Fraction = Fraction(1, 10000)  # 0.0001 ticks

    @property
    def local_time(self) -> Fraction:
        return self.true_time + self.offset

    @property
    def drift(self) -> Fraction:
        return self.offset

    @property
    def drift_float(self) -> float:
        return float(self.offset)


class PlatoTileStore:
    """SQLite-backed PLATO tile persistence for the demo."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                agent_id TEXT,
                tick INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (agent_id, tick, key)
            )
        """)
        self.conn.commit()

    def write_tile(self, agent_id: str, tick: int, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO tiles (agent_id, tick, key, value) VALUES (?, ?, ?, ?)",
            (agent_id, tick, key, value),
        )
        self.conn.commit()

    def read_tile(self, agent_id: str, tick: int, key: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT value FROM tiles WHERE agent_id=? AND tick=? AND key=?",
            (agent_id, tick, key),
        ).fetchone()
        return row[0] if row else None

    def read_latest(self, agent_id: str, key: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT value FROM tiles WHERE agent_id=? AND key=? ORDER BY tick DESC LIMIT 1",
            (agent_id, key),
        ).fetchone()
        return row[0] if row else None

    def close(self):
        self.conn.close()


class MetronomeAgent:
    """Core metronome agent with zero-drift Fraction arithmetic."""

    def __init__(
        self,
        agent_id: str,
        drift_rate: float = 0.0,
        correction_mode: CorrectionMode = CorrectionMode.GENTLE,
        tile_store: Optional[PlatoTileStore] = None,
    ):
        self.agent_id = agent_id
        self.clock = ClockState(
            drift_rate=Fraction(drift_rate).limit_denominator(1000000),
            correction_mode=correction_mode,
        )
        self.tile_store = tile_store or PlatoTileStore()
        self.is_cadence_caller = False
        self.tick_count = 0

    def tick(self):
        """Advance one tick. Local clock accumulates drift."""
        self.clock.true_time += Fraction(1)
        # Drift accumulation: offset grows by drift_rate each tick
        self.clock.offset += self.clock.drift_rate
        self.tick_count += 1
        # Persist state
        self._persist()

    def correct(self, correction: Fraction):
        """Apply a clock correction."""
        self.clock.offset += correction
        self.clock.last_correction = correction

    def deadband_correct(self, reference_time: Fraction):
        """Correct toward reference time if drift exceeds deadband."""
        drift = reference_time - self.clock.local_time
        if abs(drift) > self.clock.deadband:
            if self.clock.correction_mode == CorrectionMode.GENTLE:
                # Apply 50% correction (gentle nudge)
                self.correct(drift * Fraction(1, 2))
            else:
                # Full correction (aggressive snap)
                self.correct(drift)

    def get_cadence(self) -> Fraction:
        """Get this agent's current cadence (local time as Fraction)."""
        return self.clock.local_time

    def sunset(self) -> dict:
        """Prepare sunset payload — all calibration data for inheritance."""
        return {
            "true_time": str(self.clock.true_time),
            "offset": str(self.clock.offset),
            "drift_rate": str(self.clock.drift_rate),
            "deadband": str(self.clock.deadband),
            "tick_count": str(self.tick_count),
            "correction_mode": self.clock.correction_mode.name,
        }

    def inherit(self, data: dict):
        """Inherit calibration from a retiring cadence caller."""
        self.clock.true_time = Fraction(data["true_time"])
        self.clock.offset = Fraction(data["offset"])
        self.clock.drift_rate = Fraction(data["drift_rate"])
        self.clock.deadband = Fraction(data["deadband"])
        self.tick_count = int(data["tick_count"])
        self.clock.correction_mode = CorrectionMode[data["correction_mode"]]
        self.is_cadence_caller = True

    def _persist(self):
        self.tile_store.write_tile(
            self.agent_id, self.tick_count, "local_time", str(self.clock.local_time)
        )
        self.tile_store.write_tile(
            self.agent_id, self.tick_count, "drift", str(self.clock.drift)
        )
        self.tile_store.write_tile(
            self.agent_id, self.tick_count, "drift_float", str(self.clock.drift_float)
        )
