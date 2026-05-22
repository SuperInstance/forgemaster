"""Kimi1 agent — nerve grid compute rooms with GPU metrics."""

import numpy as np
from metronome_core import MetronomeAgent, PlatoTileStore
from network_bus import NetworkBus, Message, MessageType


class Kimi1Agent:
    """Nerve grid compute agent with 10 simplified rooms."""

    def __init__(self, bus: NetworkBus, tile_store: PlatoTileStore):
        self.agent_id = "kimi1"
        self.metronome = MetronomeAgent(
            self.agent_id,
            drift_rate=0.0002,
            tile_store=tile_store,
        )
        self.bus = bus
        self.bus.register(self.agent_id)
        # 10 nerve grid rooms — each has a small compute state
        self.rooms = {f"room_{i}": np.zeros(8) for i in range(10)}
        self.gpu_throughput = 0.0
        self.constraint_updates: list[str] = []

    def tick(self, fleet_state: dict) -> dict:
        """Run nerve grid computation and report metrics."""
        self.metronome.tick()
        msgs = self.bus.receive(self.agent_id)

        # Process cadence calls — correct clock toward caller
        for msg in msgs:
            if msg.msg_type == MessageType.CADENCE_CALL:
                from fractions import Fraction
                cadence = Fraction(msg.payload["cadence"])
                drift = cadence - self.metronome.clock.local_time
                if abs(drift) > self.metronome.clock.deadband:
                    self.metronome.correct(drift * Fraction(9, 10))
            elif msg.msg_type == MessageType.CONSTRAINT_VIOLATION:
                self.constraint_updates.append(msg.payload.get("violation", ""))

        # Nerve grid computation: each room does a small matrix multiply
        total_ops = 0
        for room_id in self.rooms:
            # Simulated compute: random projection
            matrix = np.random.randn(8, 8) * 0.1
            self.rooms[room_id] = self.rooms[room_id] @ matrix
            total_ops += 64  # 8x8 multiply

        # GPU throughput: ops per tick
        self.gpu_throughput = float(total_ops)

        # Keep only last 10 constraint updates
        self.constraint_updates = self.constraint_updates[-10:]

        # Report nerve metric
        self.bus.send(Message(
            msg_type=MessageType.NERVE_METRIC,
            sender=self.agent_id,
            payload={
                "gpu_throughput": f"{self.gpu_throughput:.1f}",
                "rooms": str(len(self.rooms)),
                "constraint_updates": str(len(self.constraint_updates)),
            },
            tick=self.metronome.tick_count,
        ))

        return {
            "agent_id": self.agent_id,
            "gpu_throughput": self.gpu_throughput,
            "rooms_active": len(self.rooms),
            "constraint_updates": len(self.constraint_updates),
        }

    def drift_report(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "drift": self.metronome.clock.drift_float,
            "local_time": float(self.metronome.clock.local_time),
            "tick": self.metronome.tick_count,
        }
