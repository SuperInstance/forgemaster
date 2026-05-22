"""MetronomeClient — the main entry point for fleet clock synchronization.

Provides a simple API:
    client = MetronomeClient(FleetConfig(name="fleet-1", peers=["host:port"]))
    client.start()
    t = client.now()          # → Fraction
    client.stop()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional

from metronome_sync.fraction_clock import FractionClock
from metronome_sync.ptp import (
    PtpMode,
    PeerSample,
    OffsetEstimator,
    compute_offset,
    weighted_offsets,
)
from metronome_sync.topology import build_laman, peer_map, is_laman
from metronome_sync.sunset import SunsetPayload, sunset, inherit, PlatoTile, tiles_from_history


@dataclass
class FleetConfig:
    """Configuration for a MetronomeClient."""
    name: str = "default"
    peers: List[str] = field(default_factory=list)
    delta: Fraction = Fraction(1, 10)       # correction deadband
    mode: PtpMode = PtpMode.PTP
    node_id: int = 0
    drift_rate: float = 0.0
    tick_interval: float = 0.01             # seconds between ticks
    correction_gain: Fraction = Fraction(1, 2)  # gentle = 50%


class MetronomeClient:
    """Anti-fragile PTP clock sync client for distributed agent fleets."""

    def __init__(self, config: FleetConfig):
        self.config = config
        self._clock = FractionClock(
            drift_rate=Fraction(config.drift_rate).limit_denominator(1_000_000)
        )
        self._estimator = OffsetEstimator()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._peers: Dict[str, Fraction] = {}   # peer -> last known offset
        self._tick_count = 0
        self._correction_count = 0
        self._history: list[tuple[int, Fraction, Fraction]] = []

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Start the clock ticker thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the clock."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _tick_loop(self) -> None:
        while self._running:
            with self._lock:
                self._clock.tick()
                self._tick_count += 1
                # Record history (keep last 1000)
                self._history.append((self._tick_count, self._clock.local_time, self._clock.drift))
                if len(self._history) > 1000:
                    self._history = self._history[-1000:]
            time.sleep(self.config.tick_interval)

    # -- time access -------------------------------------------------------

    def now(self) -> Fraction:
        """Current local time as exact Fraction."""
        with self._lock:
            return self._clock.local_time

    def true_time(self) -> Fraction:
        """Current true time (before drift)."""
        with self._lock:
            return self._clock.true_time

    def drift(self) -> Fraction:
        """Current drift offset."""
        with self._lock:
            return self._clock.drift

    # -- corrections -------------------------------------------------------

    def correct(self, delta: Fraction) -> None:
        """Apply a clock correction."""
        with self._lock:
            self._clock.correct(delta)
            self._correction_count += 1

    def correct_toward(self, reference: Fraction) -> None:
        """Correct toward a reference time, respecting deadband and gain."""
        with self._lock:
            delta = reference - self._clock.local_time
            if abs(delta) > self.config.delta:
                self._clock.correct(delta * self.config.correction_gain)
                self._correction_count += 1

    def apply_ptp_offset(self, local_time: Fraction, remote_time: Fraction, rtt: Fraction) -> Fraction:
        """Compute and apply a PTP offset correction.

        Returns the estimated offset.
        """
        offset = compute_offset(local_time, remote_time, rtt, self.config.mode)
        ema = self._estimator.update(offset)
        # Apply EMA as correction (negate because offset means we're behind)
        self.correct(-ema)
        return offset

    def apply_peer_samples(self, samples: list[PeerSample]) -> Fraction:
        """Compute weighted offset from peer samples and apply."""
        combined = weighted_offsets(samples, self.config.mode)
        if combined != 0:
            self.correct(-combined)
        return combined

    # -- fleet status ------------------------------------------------------

    def fleet_status(self) -> Dict:
        """Return a snapshot of this client's state."""
        with self._lock:
            return {
                "name": self.config.name,
                "node_id": self.config.node_id,
                "mode": self.config.mode.name,
                "local_time": str(self._clock.local_time),
                "true_time": str(self._clock.true_time),
                "drift": str(self._clock.drift),
                "drift_rate": str(self._clock.drift_rate),
                "tick_count": self._tick_count,
                "corrections": self._correction_count,
                "ema_offset": str(self._estimator.value),
                "peers_known": len(self._peers),
                "running": self._running,
            }

    # -- sunset/inheritance ------------------------------------------------

    def sunset(self) -> List[PlatoTile]:
        """Produce PLATO tiles for graceful retirement."""
        payload = SunsetPayload(
            true_time=self._clock.true_time,
            offset=self._clock.offset,
            drift_rate=self._clock.drift_rate,
            deadband=self.config.delta,
            tick_count=self._tick_count,
            correction_mode="GENTLE" if self.config.correction_gain < Fraction(1) else "AGGRESSIVE",
        )
        tiles = tiles_from_history(self.config.name, self._history[-100:])
        # Add sunset tile
        tiles.append(PlatoTile(
            tick=self._tick_count,
            agent_id=self.config.name,
            key="sunset",
            value=str(payload.to_dict()),
        ))
        return tiles

    def inherit_from(self, payload: SunsetPayload) -> None:
        """Inherit calibration from a retiring node."""
        with self._lock:
            cal = inherit(payload)
            self._clock.true_time = cal["true_time"]
            self._clock.offset = cal["offset"]
            self._clock.drift_rate = cal["drift_rate"]

    # -- topology ----------------------------------------------------------

    @staticmethod
    def build_fleet_topology(n_agents: int, seed: int = 42) -> Dict:
        """Build a Laman topology for n_agents."""
        verts, edges = build_laman(n_agents, seed)
        return {
            "n": n_agents,
            "vertices": verts,
            "edges": list(edges),
            "peers": peer_map(edges),
            "is_rigid": is_laman(n_agents, edges),
        }
