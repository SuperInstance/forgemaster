"""Fleet simulator for demo mode — spins up N virtual agents with PTP-like correction."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum


class AgentState(str, Enum):
    SYNCING = "SYNCING"
    LOCKED = "LOCKED"
    HOLDover = "HOLDOVER"
    DRIFTING = "DRIFTING"
    OFFLINE = "OFFLINE"


@dataclass
class Agent:
    name: str
    true_offset: float = 0.0  # seconds from master
    measured_offset: float = 0.0
    drift_rate: float = 0.0  # s/s
    jitter_ns: float = 50.0  # nanoseconds
    state: AgentState = AgentState.SYNCING
    correction_interval: float = 1.0  # seconds between PTP corrections
    history: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        self.measured_offset = self.true_offset + random.gauss(0, self.jitter_ns * 1e-9)

    def tick(self, dt: float) -> None:
        """Advance the agent's clock by *dt* seconds."""
        with self._lock:
            # Natural drift
            self.true_offset += self.drift_rate * dt + random.gauss(0, abs(self.drift_rate) * 0.01)
            # Measurement with jitter
            self.measured_offset = self.true_offset + random.gauss(0, self.jitter_ns * 1e-9)
            # Record history (keep last 200 samples)
            self.history.append(self.measured_offset)
            if len(self.history) > 200:
                self.history = self.history[-200:]
            # State machine
            abs_off = abs(self.measured_offset)
            if abs_off < 1e-6:
                self.state = AgentState.LOCKED
            elif abs_off < 1e-3:
                self.state = AgentState.SYNCING
            elif abs_off < 0.1:
                self.state = AgentState.HOLDover
            else:
                self.state = AgentState.DRIFTING

    def correct(self, factor: float = 0.8) -> None:
        """Apply PTP-style correction: step toward zero offset."""
        with self._lock:
            self.true_offset *= (1.0 - factor)
            self.drift_rate *= (1.0 - factor * 0.5)


@dataclass
class Fleet:
    agents: list[Agent] = field(default_factory=list)
    running: bool = False
    _thread: threading.Thread | None = field(default=None, repr=False)
    tick_rate: float = 0.05  # 50ms ticks
    correction_rate: float = 1.0  # PTP correction every 1s

    @classmethod
    def create(cls, n: int = 10, seed: int = 42) -> Fleet:
        """Create a fleet of *n* agents with random parameters."""
        rng = random.Random(seed)
        agents = []
        for i in range(n):
            a = Agent(
                name=f"agent-{i:02d}",
                true_offset=rng.gauss(0, 0.01),
                drift_rate=rng.gauss(0, 1e-5),
                jitter_ns=rng.uniform(10, 200),
                correction_interval=rng.uniform(0.5, 2.0),
            )
            agents.append(a)
        fleet = cls(agents=agents)
        return fleet

    def start(self) -> None:
        """Start the simulation in a background thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        last_correction = time.monotonic()
        while self.running:
            now = time.monotonic()
            for agent in self.agents:
                if agent.state != AgentState.OFFLINE:
                    agent.tick(self.tick_rate)
            # Periodic PTP correction
            if now - last_correction >= self.correction_rate:
                for agent in self.agents:
                    if agent.state != AgentState.OFFLINE:
                        agent.correct()
                last_correction = now
            time.sleep(self.tick_rate)

    def latency_matrix(self) -> list[list[float]]:
        """Compute pairwise latency matrix (simulated)."""
        n = len(self.agents)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    off_i = self.agents[i].measured_offset
                    off_j = self.agents[j].measured_offset
                    matrix[i][j] = abs(off_i - off_j) * 1000  # ms
        return matrix

    def topology_edges(self) -> list[tuple[int, int, float]]:
        """Return edges (i, j, weight) for fleet topology."""
        edges = []
        n = len(self.agents)
        for i in range(n):
            for j in range(i + 1, n):
                w = abs(self.agents[i].measured_offset - self.agents[j].measured_offset) * 1000
                if w < 1.0:  # only show tight links
                    edges.append((i, j, w))
        return edges
