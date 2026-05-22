"""3-Agent Metronome Demo — SuperInstance Fleet

Runs for 1000 ticks (simulated), shows bounded drift, cadence calling,
constraint checking, and one sunset/inheritance cycle.
"""

import random
import numpy as np

from metronome_core import PlatoTileStore
from network_bus import NetworkBus, Message, MessageType
from agents.forgemaster import ForgemasterAgent
from agents.oracle1 import Oracle1Agent
from agents.kimi1 import Kimi1Agent
from dashboard import Dashboard

# Deterministic seed for reproducibility
random.seed(42)
np.random.seed(42)

TOTAL_TICKS = 1000
SUNSET_TICK = 300  # Forgemaster retires at tick 300

# Simulated fleet state (would come from sensors in production)
def make_fleet_state(forgemaster, oracle1, kimi1, tick):
    """Generate simulated telemetry for constraint checking."""
    # Normal state with occasional violations
    t = tick * 0.01
    base = {
        "clearance": 150 + 5 * np.sin(t),
        "velocity": 280 + 10 * np.sin(t * 0.7),
        "altitude": 500 + 20 * np.sin(t * 0.3),
        "g_load": 1.5 + 0.5 * np.sin(t * 1.3),
        "fuel": max(5, 80 - tick * 0.05),
        "pitch_rate": 10 + 5 * np.sin(t * 0.9),
        "roll_rate": 15 + 8 * np.sin(t * 0.6),
        "yaw_rate": 8 + 4 * np.sin(t * 1.1),
        "aoa": 5 + 3 * np.sin(t * 0.8),
        "thrust": 120 + 20 * np.sin(t * 0.5),
        "engine_temp": 900 + 100 * np.sin(t * 0.4),
        "cabin_pressure": 1.0 + 0.05 * np.sin(t * 0.2),
        "mach": 0.8 + 0.2 * np.sin(t * 0.7),
        "battery": max(10, 90 - tick * 0.03),
        "vibration": 2 + 1 * np.sin(t * 1.5),
        "signal_strength": -70 + 10 * np.sin(t * 0.3),
        "lat_error": 1 + 0.5 * np.sin(t * 0.9),
        "lon_error": 1 + 0.5 * np.sin(t * 0.8),
        "vert_error": 0.5 + 0.3 * np.sin(t * 1.2),
        "comms_rate": 10 + 2 * np.sin(t * 0.1),
        "wind_shear": 5 + 3 * np.sin(t * 0.6),
        "visibility": 1500 + 500 * np.sin(t * 0.2),
    }

    # Inject violations for specific agents at specific times
    oracle1_state = dict(base)
    kimi1_state = dict(base)

    # Oracle1 occasionally dips below min_clearance
    if 50 < tick < 80:
        oracle1_state["clearance"] = 80  # below 100 min

    # Kimi1 gets high vibration around tick 200
    if 190 < tick < 220:
        kimi1_state["vibration"] = 6.0  # above 5.0 max

    # Low fuel warning late in the run
    if tick > 700:
        oracle1_state["fuel"] = 4.0  # below 5% min

    forgemaster_state = dict(base)
    forgemaster_state["local_time"] = float(forgemaster.metronome.clock.local_time)
    oracle1_state["local_time"] = float(oracle1.metronome.clock.local_time)
    kimi1_state["local_time"] = float(kimi1.metronome.clock.local_time)

    return {
        "forgemaster": forgemaster_state,
        "oracle1": oracle1_state,
        "kimi1": kimi1_state,
    }


def run_demo():
    print("=" * 60)
    print("3-Agent Metronome Demo — SuperInstance Fleet")
    print("=" * 60)
    print()

    # Initialize shared infrastructure
    tile_store = PlatoTileStore()
    bus = NetworkBus(latency_ms=0, packet_loss=0.005, reorder_prob=0.002)

    # Create agents
    forgemaster = ForgemasterAgent(bus, tile_store)
    oracle1 = Oracle1Agent(bus, tile_store)
    kimi1 = Kimi1Agent(bus, tile_store)

    agents = {
        "forgemaster": forgemaster,
        "oracle1": oracle1,
        "kimi1": kimi1,
    }

    dashboard = Dashboard()
    cadence_caller = "forgemaster"
    sunset_done = False

    print(f"Starting {TOTAL_TICKS}-tick simulation...")
    print(f"Sunset scheduled at tick {SUNSET_TICK}")
    print()

    for tick in range(TOTAL_TICKS):
        # Generate fleet state
        fleet_state = make_fleet_state(forgemaster, oracle1, kimi1, tick)

        # Each agent ticks
        violations = forgemaster.tick(fleet_state)
        holonomy = oracle1.tick(fleet_state)
        nerve = kimi1.tick(fleet_state)

        # Flush network
        bus.flush()

        # Calculate max drift across all agents
        max_drift = max(
            abs(a.metronome.clock.drift_float)
            for a in agents.values()
        )

        # Dashboard update
        dashboard.render(
            tick=tick,
            agents=agents,
            cadence_caller=cadence_caller,
            violations=violations,
            max_drift=max_drift,
            holonomy=holonomy,
        )

        # Sunset/inheritance at scheduled tick
        if tick == SUNSET_TICK and not sunset_done:
            print(f"\n>>> SUNSET: {cadence_caller} retires → oracle1 inherits\n")
            forgemaster.sunset()
            bus.flush()
            # Oracle1 picks up inheritance on next tick
            sunset_done = True
            cadence_caller = "oracle1"

        # Verify Tensor-MIDI round-trip periodically
        if tick % 100 == 0 and tick > 0:
            test_msg = Message(
                msg_type=MessageType.TENSOR_MIDI,
                sender="test",
                payload={"data": "round_trip_test", "tick": str(tick)},
                tick=tick,
            )
            encoded = test_msg.encode()
            decoded = Message.decode(encoded)
            assert decoded.msg_type == test_msg.msg_type
            assert decoded.sender == test_msg.sender
            assert decoded.payload["data"] == "round_trip_test"

    # Final dashboard
    dashboard.summary()

    # Final verification
    max_drift_final = max(
        abs(a.metronome.clock.drift_float) for a in agents.values()
    )

    print(f"\nFinal max drift: {max_drift_final:.6f}")
    print(f"Drift bounded: {'YES ✓' if max_drift_final < 0.5 else 'NO ✗'}")
    print(f"Sunset/inheritance: {'completed ✓' if sunset_done else 'pending'}")
    print(f"Forge violations caught: {forgemaster.total_violations}")

    tile_store.close()
    print("\nDemo complete.")


if __name__ == "__main__":
    run_demo()
