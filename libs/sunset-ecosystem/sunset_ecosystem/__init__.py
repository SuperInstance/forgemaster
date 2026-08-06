"""sunset_ecosystem — Nerve grid topology for cross-agent communication.

Provides:
  - NerveFiber: a single signal channel between agents
  - NerveTopology: a graph of nerve fibers connecting agents
  - HebbianChannel: a Hebbian-learning weighted channel
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

__all__ = ["NerveFiber", "NerveTopology", "HebbianChannel"]

__version__ = "0.1.0"


@dataclass
class NerveFiber:
    """A single nerve fiber — a directional signal channel between two endpoints.

    Attributes:
        fiber_id: Unique identifier for this fiber.
        source: Source agent name (optional, set by topology).
        target: Target agent name (optional, set by topology).
        signal_strength: Current signal strength [0.0, 1.0].
        active: Whether the fiber is currently transmitting.
    """

    fiber_id: str
    source: Optional[str] = None
    target: Optional[str] = None
    signal_strength: float = 1.0
    active: bool = True
    _signals: list = field(default_factory=list, repr=False)

    def transmit(self, signal: dict):
        """Transmit a signal along this fiber."""
        if self.active:
            self._signals.append(signal)

    def receive(self) -> Optional[dict]:
        """Receive the next signal from this fiber."""
        if self._signals:
            return self._signals.pop(0)
        return None

    def __repr__(self) -> str:
        return f"NerveFiber(id={self.fiber_id!r}, active={self.active})"


class HebbianChannel:
    """Hebbian-learning weighted channel — strengthens with correlated activity.

    "Neurons that fire together, wire together."
    """

    def __init__(self, channel_id: str, initial_weight: float = 0.5):
        self.channel_id = channel_id
        self.weight = initial_weight
        self.learning_rate = 0.01
        self._activation_count = 0

    def activate(self, source_active: bool, target_active: bool):
        """Apply Hebbian update based on correlated activity."""
        if source_active and target_active:
            self.weight = min(1.0, self.weight + self.learning_rate)
        elif source_active != target_active:
            self.weight = max(0.0, self.weight - self.learning_rate * 0.5)
        self._activation_count += 1

    def __repr__(self) -> str:
        return f"HebbianChannel(id={self.channel_id!r}, weight={self.weight:.3f})"


class NerveTopology:
    """A topology of nerve fibers connecting multiple agents.

    Manages the graph of NerveFiber connections and provides
    routing and broadcast capabilities.
    """

    def __init__(self):
        self.fibers: Dict[str, NerveFiber] = {}
        self.nodes: Set[str] = set()
        self.channels: Dict[str, HebbianChannel] = {}

    def add_node(self, name: str):
        """Add a node to the topology."""
        self.nodes.add(name)

    def add_fiber(self, fiber: NerveFiber, source: str, target: str):
        """Add a nerve fiber connecting source → target."""
        fiber.source = source
        fiber.target = target
        self.add_node(source)
        self.add_node(target)
        self.fibers[fiber.fiber_id] = fiber

    def route(self, source: str, target: str, signal: dict) -> bool:
        """Route a signal from source to target if a path exists."""
        for fiber in self.fibers.values():
            if fiber.source == source and fiber.target == target and fiber.active:
                fiber.transmit(signal)
                return True
        return False

    def broadcast(self, source: str, signal: dict):
        """Broadcast a signal from source to all connected targets."""
        for fiber in self.fibers.values():
            if fiber.source == source and fiber.active:
                fiber.transmit(signal)

    def get_fibers_from(self, node: str) -> List[NerveFiber]:
        """Get all outgoing fibers from a node."""
        return [f for f in self.fibers.values() if f.source == node]

    def get_fibers_to(self, node: str) -> List[NerveFiber]:
        """Get all incoming fibers to a node."""
        return [f for f in self.fibers.values() if f.target == node]

    def __repr__(self) -> str:
        return (
            f"NerveTopology(nodes={len(self.nodes)}, "
            f"fibers={len(self.fibers)})"
        )
