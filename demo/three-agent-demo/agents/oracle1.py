"""Oracle1 agent — holonomy consensus and Laman rigidity monitoring."""

from fractions import Fraction
from metronome_core import MetronomeAgent, PlatoTileStore
from network_bus import NetworkBus, Message, MessageType


class Oracle1Agent:
    """Fleet coordination agent with holonomy consensus."""

    def __init__(self, bus: NetworkBus, tile_store: PlatoTileStore):
        self.agent_id = "oracle1"
        self.metronome = MetronomeAgent(
            self.agent_id,
            drift_rate=-0.00015,  # drifts in opposite direction
            tile_store=tile_store,
        )
        self.bus = bus
        self.bus.register(self.agent_id)
        self.holonomy_ok = True
        self.laman_edges = 0
        self.fleet_size = 3
        self.drift_diagnostics: dict = {}

    def tick(self, fleet_state: dict) -> dict:
        """Run holonomy consensus check and drift diagnostics."""
        self.metronome.tick()
        msgs = self.bus.receive(self.agent_id)

        # Process cadence calls — correct clock toward caller
        for msg in msgs:
            if msg.msg_type == MessageType.CADENCE_CALL:
                cadence = Fraction(msg.payload["cadence"])
                # Aggressive snap to caller's cadence
                drift = cadence - self.metronome.clock.local_time
                if abs(drift) > self.metronome.clock.deadband:
                    # Apply 90% correction for fast convergence
                    self.metronome.correct(drift * Fraction(9, 10))
            elif msg.msg_type == MessageType.SUNSET:
                # Inherit from retiring caller
                self.metronome.inherit(msg.payload)
                self.bus.send(Message(
                    msg_type=MessageType.INHERIT,
                    sender=self.agent_id,
                    payload={"status": "inherited", "from": msg.sender},
                    tick=self.metronome.tick_count,
                ))

        # Holonomy check: all agents should agree on time modulo drift tolerance
        times = []
        for agent_id, state in fleet_state.items():
            if "local_time" in state:
                times.append(state["local_time"])
        times.append(float(self.metronome.clock.local_time))

        if len(times) >= 2:
            time_spread = max(times) - min(times)
            self.holonomy_ok = time_spread < 1.0
        else:
            self.holonomy_ok = True

        # Laman rigidity: for n agents, need >= 2n - 3 edges
        # In our fleet, each agent talks to each other = n*(n-1)/2 bidirectional edges
        n = self.fleet_size
        self.laman_edges = n * (n - 1) // 2
        min_edges = 2 * n - 3
        laman_ok = self.laman_edges >= min_edges

        # Drift diagnostics
        self.drift_diagnostics = {
            "holonomy_ok": self.holonomy_ok,
            "laman_ok": laman_ok,
            "laman_edges": self.laman_edges,
            "min_edges": min_edges,
            "drift": self.metronome.clock.drift_float,
        }

        # Broadcast holonomy report
        self.bus.send(Message(
            msg_type=MessageType.HOLOMONY_REPORT,
            sender=self.agent_id,
            payload={k: str(v) for k, v in self.drift_diagnostics.items()},
            tick=self.metronome.tick_count,
        ))

        return self.drift_diagnostics

    def drift_report(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "drift": self.metronome.clock.drift_float,
            "local_time": float(self.metronome.clock.local_time),
            "tick": self.metronome.tick_count,
        }
