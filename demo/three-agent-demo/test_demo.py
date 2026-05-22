"""End-to-end tests for the three-agent demo."""

import random
import numpy as np
from fractions import Fraction

from metronome_core import MetronomeAgent, PlatoTileStore, CorrectionMode
from network_bus import NetworkBus, Message, MessageType
from agents.forgemaster import ForgemasterAgent
from agents.oracle1 import Oracle1Agent
from agents.kimi1 import Kimi1Agent


def make_agents():
    """Create a fresh set of agents for testing."""
    random.seed(42)
    np.random.seed(42)
    tile_store = PlatoTileStore()
    bus = NetworkBus(latency_ms=0, packet_loss=0.0, reorder_prob=0.0)
    forgemaster = ForgemasterAgent(bus, tile_store)
    oracle1 = Oracle1Agent(bus, tile_store)
    kimi1 = Kimi1Agent(bus, tile_store)
    return forgemaster, oracle1, kimi1, bus, tile_store


def make_normal_state(forgemaster, oracle1, kimi1, tick):
    """Normal fleet state with no violations."""
    state = {
        "clearance": 150, "velocity": 280, "altitude": 500,
        "g_load": 1.5, "fuel": 80, "pitch_rate": 10,
        "roll_rate": 15, "yaw_rate": 8, "aoa": 5,
        "thrust": 120, "engine_temp": 900, "cabin_pressure": 1.0,
        "mach": 0.8, "battery": 90, "vibration": 2,
        "signal_strength": -70, "lat_error": 1, "lon_error": 1,
        "vert_error": 0.5, "comms_rate": 10, "wind_shear": 5,
        "visibility": 1500,
    }
    return {
        "forgemaster": dict(state, local_time=float(forgemaster.metronome.clock.local_time)),
        "oracle1": dict(state, local_time=float(oracle1.metronome.clock.local_time)),
        "kimi1": dict(state, local_time=float(kimi1.metronome.clock.local_time)),
    }


def test_all_agents_start_and_communicate():
    """Verify all 3 agents start and communicate."""
    fm, o1, k1, bus, ts = make_agents()
    fleet = make_normal_state(fm, o1, k1, 0)

    # Forgemaster ticks first and sends CADENCE_CALL
    fm.tick(fleet)
    bus.flush()

    # Verify oracle1 mailbox has cadence call BEFORE oracle1 consumes it
    msgs = bus.receive("oracle1")
    msg_types = [m.msg_type for m in msgs]
    assert MessageType.CADENCE_CALL in msg_types, "Oracle1 should receive cadence call"

    # Now tick oracle1 and kimi1
    o1.tick(fleet)
    k1.tick(fleet)
    bus.flush()

    # Verify they all advanced
    assert fm.metronome.tick_count == 1, "Forgemaster should have ticked"
    assert o1.metronome.tick_count == 1, "Oracle1 should have ticked"
    assert k1.metronome.tick_count == 1, "Kimi1 should have ticked"

    print("✓ test_all_agents_start_and_communicate")
    ts.close()


def test_drift_bounded():
    """Verify drift stays bounded for 500 ticks."""
    fm, o1, k1, bus, ts = make_agents()

    max_drift_seen = 0.0
    for tick in range(500):
        fleet = make_normal_state(fm, o1, k1, tick)
        fm.tick(fleet)
        o1.tick(fleet)
        k1.tick(fleet)
        bus.flush()

        drifts = [
            abs(fm.metronome.clock.drift_float),
            abs(o1.metronome.clock.drift_float),
            abs(k1.metronome.clock.drift_float),
        ]
        max_drift_seen = max(max_drift_seen, max(drifts))

    # With cadence calling (correction), drift should stay very small
    assert max_drift_seen < 0.5, f"Drift should be bounded, got {max_drift_seen}"
    print(f"✓ test_drift_bounded (max drift: {max_drift_seen:.6f})")
    ts.close()


def test_cadence_caller_election():
    """Verify cadence caller election works."""
    fm, o1, k1, bus, ts = make_agents()

    # Forgemaster starts as cadence caller
    assert fm.metronome.is_cadence_caller, "Forgemaster should start as caller"
    assert not o1.metronome.is_cadence_caller, "Oracle1 should not be caller"

    fleet = make_normal_state(fm, o1, k1, 0)
    fm.tick(fleet)
    bus.flush()

    # Oracle1 should receive a CADENCE_CALL
    msgs = bus.receive("oracle1")
    cadence_calls = [m for m in msgs if m.msg_type == MessageType.CADENCE_CALL]
    assert len(cadence_calls) > 0, "Should receive cadence call"

    print("✓ test_cadence_caller_election")
    ts.close()


def test_sunset_inheritance():
    """Verify sunset/inheritance transfers calibration."""
    fm, o1, k1, bus, ts = make_agents()

    # Run for 50 ticks
    for tick in range(50):
        fleet = make_normal_state(fm, o1, k1, tick)
        fm.tick(fleet)
        o1.tick(fleet)
        k1.tick(fleet)
        bus.flush()

    # Forgemaster sunsets
    sunset_data = fm.sunset()
    bus.flush()

    # Oracle1 picks up on next tick
    o1.tick(make_normal_state(fm, o1, k1, 50))
    bus.flush()

    # Verify oracle1 inherited
    assert o1.metronome.is_cadence_caller, "Oracle1 should now be caller"
    assert not fm.metronome.is_cadence_caller, "Forgemaster should no longer be caller"

    # Verify calibration transferred
    assert o1.metronome.tick_count == 50, f"Oracle1 should inherit tick_count, got {o1.metronome.tick_count}"

    print("✓ test_sunset_inheritance")
    ts.close()


def test_tensor_midi_roundtrip():
    """Verify Tensor-MIDI encoding round-trips correctly."""
    messages = [
        Message(MessageType.TICK, "forgemaster", {"count": "42"}, tick=100),
        Message(MessageType.DRIFT_REPORT, "oracle1", {"drift": "0.001", "status": "ok"}, tick=200),
        Message(MessageType.CADENCE_CALL, "kimi1", {"cadence": "300/1"}, tick=300),
        Message(MessageType.CORRECTION, "forgemaster", {"delta": "-1/1000"}, tick=400),
        Message(MessageType.SUNSET, "oracle1", {"true_time": "500", "offset": "1/200"}, tick=500),
        Message(MessageType.TENSOR_MIDI, "test", {"data": "hello=world"}, tick=600),
        Message(MessageType.CONSTRAINT_VIOLATION, "forgemaster", {"violation": "max_velocity"}, tick=700),
    ]

    for msg in messages:
        encoded = msg.encode()
        assert isinstance(encoded, bytes), "Encoded should be bytes"
        decoded = Message.decode(encoded)
        assert decoded.msg_type == msg.msg_type, f"Type mismatch for {msg}"
        assert decoded.sender == msg.sender, f"Sender mismatch for {msg}"
        assert decoded.tick == msg.tick, f"Tick mismatch for {msg}"
        assert decoded.payload == msg.payload, f"Payload mismatch for {msg}: {decoded.payload} != {msg.payload}"

    print("✓ test_tensor_midi_roundtrip")


def test_fraction_zero_drift():
    """Verify Fraction arithmetic produces zero accumulated error."""
    clock = MetronomeAgent("test", drift_rate=0.0)
    for _ in range(10000):
        clock.tick()

    # With zero drift rate, offset should be exactly 0
    assert clock.clock.offset == Fraction(0), "Zero drift rate should produce zero offset"
    assert clock.clock.drift_float == 0.0, "Float repr should be exactly 0.0"

    print("✓ test_fraction_zero_drift")


if __name__ == "__main__":
    print("Running three-agent demo tests...\n")
    test_all_agents_start_and_communicate()
    test_drift_bounded()
    test_cadence_caller_election()
    test_sunset_inheritance()
    test_tensor_midi_roundtrip()
    test_fraction_zero_drift()
    print("\nAll tests passed ✓")
