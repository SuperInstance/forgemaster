"""3-Agent Metronome Demo — SuperInstance Fleet

Runs for 1000 ticks (simulated), shows bounded drift, cadence calling,
constraint checking, and one sunset/inheritance cycle.

Flags:
  --verbose   Show detailed per-agent thinking each tick
  --quick     Run only 100 ticks (fast testing)
"""

import argparse
import json
import random
import sys
import numpy as np

from metronome_core import PlatoTileStore
from network_bus import NetworkBus, Message, MessageType
from agents.forgemaster import ForgemasterAgent
from agents.oracle1 import Oracle1Agent
from agents.kimi1 import Kimi1Agent
from dashboard import Dashboard


def parse_args():
    parser = argparse.ArgumentParser(description="3-Agent Metronome Demo")
    parser.add_argument("--verbose", action="store_true", help="Show detailed per-agent thinking")
    parser.add_argument("--quick", action="store_true", help="Run only 100 ticks")
    return parser.parse_args()


# Deterministic seed for reproducibility
random.seed(42)
np.random.seed(42)


def make_fleet_state(forgemaster, oracle1, kimi1, tick):
    """Generate simulated telemetry for constraint checking."""
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

    oracle1_state = dict(base)
    kimi1_state = dict(base)

    # Oracle1 occasionally dips below min_clearance
    if 50 < tick < 80:
        oracle1_state["clearance"] = 80

    # Kimi1 gets high vibration around tick 200
    if 190 < tick < 220:
        kimi1_state["vibration"] = 6.0

    # Low fuel warning late in the run
    if tick > 700:
        oracle1_state["fuel"] = 4.0

    forgemaster_state = dict(base)
    forgemaster_state["local_time"] = float(forgemaster.metronome.clock.local_time)
    oracle1_state["local_time"] = float(oracle1.metronome.clock.local_time)
    kimi1_state["local_time"] = float(kimi1.metronome.clock.local_time)

    return {
        "forgemaster": forgemaster_state,
        "oracle1": oracle1_state,
        "kimi1": kimi1_state,
    }


def agent_thinking(forgemaster, oracle1, kimi1, violations, holonomy, nerve, tick):
    """Return per-agent thinking strings for verbose dashboard."""
    lines = []

    # Forgemaster thinking
    fm_drift = forgemaster.metronome.clock.drift_float
    fm_ticks = forgemaster.metronome.tick_count
    fm_caller = forgemaster.metronome.is_cadence_caller
    lines.append(f"  ⚒️  FORGEMASTER | drift:{fm_drift:+.6f} tick:{fm_ticks} "
                 f"caller:{'YES' if fm_caller else 'no'} "
                 f"violations:{len(violations)} total:{forgemaster.total_violations}")
    if violations:
        for v in violations[:5]:
            lines.append(f"      → constraint breach: {v}")
    else:
        lines.append(f"      → all constraints nominal ✓")

    # Oracle1 thinking
    o1_drift = oracle1.metronome.clock.drift_float
    o1_ticks = oracle1.metronome.tick_count
    h_ok = "✓" if holonomy.get("holonomy_ok") else "✗"
    l_ok = "✓" if holonomy.get("laman_ok") else "✗"
    lines.append(f"  🔮 ORACLE1     | drift:{o1_drift:+.6f} tick:{o1_ticks} "
                 f"holonomy:{h_ok} laman:{l_ok} edges:{holonomy.get('laman_edges', '?')}")
    if holonomy.get("holonomy_ok"):
        lines.append(f"      → fleet time consensus: aligned")
    else:
        lines.append(f"      → WARNING: fleet time divergence detected")

    # Kimi1 thinking
    k1_drift = kimi1.metronome.clock.drift_float
    k1_ticks = kimi1.metronome.tick_count
    k1_gpu = nerve.get("gpu_throughput", 0)
    k1_rooms = nerve.get("rooms_active", 0)
    k1_upd = nerve.get("constraint_updates", 0)
    lines.append(f"  ⚡ KIMI1       | drift:{k1_drift:+.6f} tick:{k1_ticks} "
                 f"gpu:{k1_gpu:.0f}ops rooms:{k1_rooms} updates:{k1_upd}")
    if k1_upd > 0:
        lines.append(f"      → processing {k1_upd} constraint updates from fleet")
    else:
        lines.append(f"      → nerve grid compute nominal")

    return "\n".join(lines)


def seed_tile_store(tile_store):
    """Seed PLATO tile store with 10 example tiles (simulated history)."""
    sample_tiles = [
        ("forgemaster", -10, "local_time", "-10"),
        ("forgemaster", -10, "drift", "-1/10000"),
        ("forgemaster", -9, "drift_float", "-0.0001"),
        ("oracle1", -8, "local_time", "-8"),
        ("oracle1", -8, "drift", "12/100000"),
        ("oracle1", -7, "drift_float", "0.00012"),
        ("kimi1", -6, "local_time", "-6"),
        ("kimi1", -6, "drift", "2/10000"),
        ("kimi1", -5, "drift_float", "0.0002"),
        ("forgemaster", -3, "constraint_check", "all_nominal"),
    ]
    for agent_id, tick, key, value in sample_tiles:
        tile_store.write_tile(agent_id, tick, key, value)


def run_demo():
    args = parse_args()

    total_ticks = 100 if args.quick else 1000
    sunset_tick = 30 if args.quick else 300
    verbose = args.verbose

    print("=" * 60)
    print("3-Agent Metronome Demo — SuperInstance Fleet")
    print("=" * 60)
    if verbose:
        print("Mode: VERBOSE (detailed per-agent thinking)")
    if args.quick:
        print("Mode: QUICK (100 ticks)")
    print()

    # Initialize shared infrastructure
    tile_store = PlatoTileStore()
    seed_tile_store(tile_store)
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

    print(f"Starting {total_ticks}-tick simulation...")
    print(f"Sunset scheduled at tick {sunset_tick}")
    print(f"Seeded PLATO tile store with 10 historical tiles")
    print()

    for tick in range(total_ticks):
        fleet_state = make_fleet_state(forgemaster, oracle1, kimi1, tick)

        violations = forgemaster.tick(fleet_state)
        holonomy = oracle1.tick(fleet_state)
        nerve = kimi1.tick(fleet_state)

        bus.flush()

        max_drift = max(
            abs(a.metronome.clock.drift_float)
            for a in agents.values()
        )

        # Verbose: show agent thinking every 10 ticks (or every tick if < 100 total)
        if verbose and (tick % 10 == 0 or total_ticks <= 100):
            print(f"[TICK {tick:04d}] Agent Dashboards:")
            print(agent_thinking(forgemaster, oracle1, kimi1, violations, holonomy, nerve, tick))
            print()

        dashboard.render(
            tick=tick,
            agents=agents,
            cadence_caller=cadence_caller,
            violations=violations,
            max_drift=max_drift,
            holonomy=holonomy,
        )

        if tick == sunset_tick and not sunset_done:
            print(f"\n>>> SUNSET: {cadence_caller} retires → oracle1 inherits\n")
            forgemaster.sunset()
            bus.flush()
            sunset_done = True
            cadence_caller = "oracle1"

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

    dashboard.summary()

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
