"""Forgemaster agent — checks 25 aerospace constraints per tick."""

from metronome_core import MetronomeAgent, PlatoTileStore, CorrectionMode
from network_bus import NetworkBus, Message, MessageType


# 25 simplified aerospace constraints
CONSTRAINTS = [
    {"id": "min_clearance", "param": "clearance", "min": 100.0, "max": None, "unit": "m"},
    {"id": "max_velocity", "param": "velocity", "min": None, "max": 340.0, "unit": "m/s"},
    {"id": "min_altitude", "param": "altitude", "min": 50.0, "max": None, "unit": "m"},
    {"id": "max_altitude", "param": "altitude", "min": None, "max": 40000.0, "unit": "m"},
    {"id": "max_g_load", "param": "g_load", "min": None, "max": 9.0, "unit": "g"},
    {"id": "min_fuel", "param": "fuel", "min": 5.0, "max": None, "unit": "%"},
    {"id": "max_pitch_rate", "param": "pitch_rate", "min": None, "max": 60.0, "unit": "deg/s"},
    {"id": "max_roll_rate", "param": "roll_rate", "min": None, "max": 90.0, "unit": "deg/s"},
    {"id": "max_yaw_rate", "param": "yaw_rate", "min": None, "max": 45.0, "unit": "deg/s"},
    {"id": "min_aoa", "param": "aoa", "min": -5.0, "max": None, "unit": "deg"},
    {"id": "max_aoa", "param": "aoa", "min": None, "max": 20.0, "unit": "deg"},
    {"id": "min_thrust", "param": "thrust", "min": 10.0, "max": None, "unit": "kN"},
    {"id": "max_thrust", "param": "thrust", "min": None, "max": 200.0, "unit": "kN"},
    {"id": "max_temp", "param": "engine_temp", "min": None, "max": 1200.0, "unit": "K"},
    {"id": "min_pressure", "param": "cabin_pressure", "min": 0.8, "max": None, "unit": "atm"},
    {"id": "max_mach", "param": "mach", "min": None, "max": 2.5, "unit": ""},
    {"id": "min_battery", "param": "battery", "min": 10.0, "max": None, "unit": "%"},
    {"id": "max_vibration", "param": "vibration", "min": None, "max": 5.0, "unit": "g_rms"},
    {"id": "min_signal", "param": "signal_strength", "min": -90.0, "max": None, "unit": "dBm"},
    {"id": "max_lat_error", "param": "lat_error", "min": None, "max": 5.0, "unit": "m"},
    {"id": "max_lon_error", "param": "lon_error", "min": None, "max": 5.0, "unit": "m"},
    {"id": "max_vert_error", "param": "vert_error", "min": None, "max": 3.0, "unit": "m"},
    {"id": "min_comms_rate", "param": "comms_rate", "min": 1.0, "max": None, "unit": "Hz"},
    {"id": "max_wind_shear", "param": "wind_shear", "min": None, "max": 15.0, "unit": "m/s"},
    {"id": "min_vis_range", "param": "visibility", "min": 800.0, "max": None, "unit": "m"},
]


class ForgemasterAgent:
    """Constraint-checking agent for the fleet."""

    def __init__(self, bus: NetworkBus, tile_store: PlatoTileStore):
        self.agent_id = "forgemaster"
        self.metronome = MetronomeAgent(
            self.agent_id,
            drift_rate=0.0001,
            correction_mode=CorrectionMode.GENTLE,
            tile_store=tile_store,
        )
        self.metronome.is_cadence_caller = True  # starts as caller
        self.bus = bus
        self.bus.register(self.agent_id)
        self.violations: list[str] = []
        self.total_violations = 0

    def tick(self, fleet_state: dict) -> list[str]:
        """Check constraints against fleet state. Returns list of violations."""
        self.metronome.tick()
        msgs = self.bus.receive(self.agent_id)

        violations = []
        for agent_id, state in fleet_state.items():
            if agent_id == self.agent_id:
                continue
            for c in CONSTRAINTS:
                param = c["param"]
                if param not in state:
                    continue
                val = state[param]
                violated = False
                if c["min"] is not None and val < c["min"]:
                    violated = True
                if c["max"] is not None and val > c["max"]:
                    violated = True
                if violated:
                    violations.append(f"{agent_id} {c['id']}")

        self.violations = violations
        self.total_violations += len(violations)

        # Broadcast violations
        for v in violations:
            self.bus.send(Message(
                msg_type=MessageType.CONSTRAINT_VIOLATION,
                sender=self.agent_id,
                payload={"violation": v, "tick": str(self.metronome.tick_count)},
                tick=self.metronome.tick_count,
            ))

        # If cadence caller, broadcast cadence
        if self.metronome.is_cadence_caller:
            self.bus.send(Message(
                msg_type=MessageType.CADENCE_CALL,
                sender=self.agent_id,
                payload={"cadence": str(self.metronome.get_cadence())},
                tick=self.metronome.tick_count,
            ))

        return violations

    def drift_report(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "drift": self.metronome.clock.drift_float,
            "local_time": float(self.metronome.clock.local_time),
            "tick": self.metronome.tick_count,
        }

    def sunset(self) -> dict:
        self.metronome.is_cadence_caller = False
        data = self.metronome.sunset()
        self.bus.send(Message(
            msg_type=MessageType.SUNSET,
            sender=self.agent_id,
            payload=data,
            tick=self.metronome.tick_count,
        ), recipients=["oracle1"])
        return data
