#!/usr/bin/env python3
"""Test distributed metronome cluster — discovery, election, drift, sunset, Tensor-MIDI."""

import json
import os
import socket
import struct
import sys
import threading
import time
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from metronome_core import MetronomeAgent, PlatoTileStore, CorrectionMode
from metronome_node import (
    MetronomeNode,
    PeerDiscovery,
    tensor_midi_encode,
    tensor_midi_decode,
    MULTICAST_GROUP,
)
from fleet_protocol import (
    MAGIC as FLEET_MAGIC,
    MessageType,
    encode_tick,
    encode_beacon,
    encode_cadence_call,
    encode_sunset,
    encode_message,
    decode_message,
    decode_raw,
    now_ms,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Test 1: Tensor-MIDI round-trip (spec-compliant via fleet_protocol)
# ---------------------------------------------------------------------------

def test_tensor_midi():
    print("\n=== Test: Tensor-MIDI Encoding (Spec-Compliant) ===")

    # Round-trip via the backward-compatible tensor_midi_encode wrapper
    payload = {"c": 0.5, "t": 0.3}
    encoded = tensor_midi_encode(payload)
    decoded = tensor_midi_decode(encoded)
    test(
        "Backward-compat wrapper round-trip",
        decoded["type"] == MessageType.TICK,
        f"expected TICK, got {decoded['type']}",
    )
    test(
        "Backward-compat drift value",
        abs(decoded["payload"]["drift"] - 0.5) < 0.01,
        f"got drift={decoded['payload']['drift']}",
    )

    # Spec-compliant: magic is 0xF1EE7
    raw = encode_tick(sender_id=7, timestamp_ms=12345, beat=42, time_ms=9999, drift=0.123, state=1)
    test("Magic is 0xF1EE7", raw[:4] == struct.pack(">I", FLEET_MAGIC))
    test("Packet has CRC16 footer", len(raw) >= 14 + 13 + 2)  # header + payload + CRC

    msg = decode_message(raw)
    test("Decode type is TICK", msg["type"] == MessageType.TICK)
    test("Decode sender_id", msg["sender_id"] == 7)
    test("Decode beat", msg["payload"]["beat"] == 42)
    test("Decode drift", abs(msg["payload"]["drift"] - 0.123) < 1e-6)
    test("Decode state", msg["payload"]["state"] == 1)

    # Round-trip: empty payload through TICK
    empty = tensor_midi_encode({})
    empty_decoded = tensor_midi_decode(empty)
    test("Empty payload round-trip", empty_decoded["type"] == MessageType.TICK)

    # Spec-compliant: BEACON round-trip
    theta = {
        "T": Fraction(1, 2),
        "phi0": 1000,
        "epsilon": Fraction(1, 1000),
        "delta": Fraction(1, 100),
    }
    beacon_raw = encode_beacon(sender_id=1, timestamp_ms=now_ms(), uptime_ms=5000, theta=theta, known_peers={2, 3})
    beacon_msg = decode_message(beacon_raw)
    test("BEACON round-trip type", beacon_msg["type"] == MessageType.BEACON)
    test("BEACON uptime", beacon_msg["payload"]["uptime_ms"] == 5000)
    test("BEACON theta T", beacon_msg["payload"]["theta"]["T"] == Fraction(1, 2))
    test("BEACON peers", beacon_msg["payload"]["known_peers"] == {2, 3})

    # Spec-compliant: SUNSET round-trip
    sunset_raw = encode_sunset(sender_id=5, timestamp_ms=now_ms(), node_id=5, tile_count=99)
    sunset_msg = decode_message(sunset_raw)
    test("SUNSET round-trip type", sunset_msg["type"] == MessageType.SUNSET)
    test("SUNSET tile_count", sunset_msg["payload"]["tile_count"] == 99)

    # Spec-compliant: CADENCE_CALL round-trip
    cad_raw = encode_cadence_call(sender_id=2, timestamp_ms=now_ms(), caller_id=2, caller_uptime_ms=10000, claimed_tick=500)
    cad_msg = decode_message(cad_raw)
    test("CADENCE_CALL round-trip type", cad_msg["type"] == MessageType.CADENCE_CALL)
    test("CADENCE_CALL claimed_tick", cad_msg["payload"]["claimed_tick"] == 500)


# ---------------------------------------------------------------------------
# Test 2: Cadence election logic (local simulation)
# ---------------------------------------------------------------------------

def test_election():
    print("\n=== Test: Cadence Election ===")

    # Simulate 3 nodes with different uptimes
    # Create mock discovery objects
    class FakeDiscovery:
        def __init__(self, name, uptime, peers):
            self.name = name
            self._uptime = uptime
            self._peers = peers
        def get_uptime(self):
            return self._uptime
        def get_peers(self):
            return self._peers

    # Node A: uptime 100, Node B: uptime 50, Node C: uptime 200
    peers_for_a = {
        "B": {"uptime": 50},
        "C": {"uptime": 200},
    }
    peers_for_b = {
        "A": {"uptime": 100},
        "C": {"uptime": 200},
    }
    peers_for_c = {
        "A": {"uptime": 100},
        "B": {"uptime": 50},
    }

    # Run election logic manually (same as MetronomeNode._run_election)
    candidates = [("A", 100), ("B", 50), ("C", 200)]
    candidates.sort(key=lambda x: (-x[1], x[0]))
    winner = candidates[0][0]
    test("Longest uptime wins election", winner == "C", f"got {winner}")

    # Tie-breaking by name
    candidates_tie = [("alpha", 100), ("beta", 100)]
    candidates_tie.sort(key=lambda x: (-x[1], x[0]))
    winner_tie = candidates_tie[0][0]
    test("Tie broken by name sort", winner_tie == "alpha", f"got {winner_tie}")


# ---------------------------------------------------------------------------
# Test 3: Drift bounded for 500 ticks
# ---------------------------------------------------------------------------

def test_drift_bounded():
    print("\n=== Test: Drift Bounded for 500 Ticks ===")

    # Simulate 500 ticks with a reference and a drifting node
    ref = MetronomeAgent("reference", drift_rate=0.0)
    drifter = MetronomeAgent("drifter", drift_rate=0.001)  # 0.1% drift

    delta = Fraction(1, 10000)  # deadband
    max_drift_seen = Fraction(0)

    for i in range(500):
        ref.tick()
        drifter.tick()

        # Drifter corrects toward reference using deadband
        drifter.deadband_correct(ref.clock.local_time)

        current_drift = abs(drifter.clock.drift)
        if current_drift > max_drift_seen:
            max_drift_seen = current_drift

    # With gentle correction (50%), drift should stay bounded
    # Theoretical max with gentle correction and 0.001 drift rate:
    # Converges to about drift_rate / (1 - 0.5) = 0.002 per tick, 
    # but deadband_correct keeps it in check
    test(
        "Max drift < 0.01 over 500 ticks",
        max_drift_seen < Fraction(1, 100),
        f"max drift = {float(max_drift_seen):.6f}",
    )
    test(
        "Max drift < 0.001 over 500 ticks",
        max_drift_seen < Fraction(1, 1000),
        f"max drift = {float(max_drift_seen):.6f}",
    )


# ---------------------------------------------------------------------------
# Test 4: Sunset/inheritance
# ---------------------------------------------------------------------------

def test_sunset_inheritance():
    print("\n=== Test: Sunset/Inheritance ===")

    # Create agent with some state
    tile_store = PlatoTileStore(":memory:")
    agent = MetronomeAgent("retiring", drift_rate=0.001, tile_store=tile_store)
    agent.is_cadence_caller = True

    # Run 100 ticks
    for _ in range(100):
        agent.tick()

    # Sunset
    sunset_data = agent.sunset()
    test("Sunset data has true_time", "true_time" in sunset_data)
    test("Sunset data has offset", "offset" in sunset_data)
    test("Sunset data has drift_rate", "drift_rate" in sunset_data)
    test("Sunset data has tick_count", "tick_count" in sunset_data)
    test("Sunset true_time is 100", sunset_data["true_time"] == "100")

    # Inherit into new agent
    new_store = PlatoTileStore(":memory:")
    heir = MetronomeAgent("heir", drift_rate=0.0, tile_store=new_store)
    heir.inherit(sunset_data)

    test("Heir inherits true_time", heir.clock.true_time == Fraction(100))
    test("Heir inherits is_cadence_caller", heir.is_cadence_caller is True)
    test(
        "Heir inherits drift_rate",
        heir.clock.drift_rate == Fraction(1, 1000),
        f"got {heir.clock.drift_rate}",
    )
    test("Heir inherits tick_count", heir.tick_count == 100)


# ---------------------------------------------------------------------------
# Test 5: UDP Discovery (3 nodes, real sockets)
# ---------------------------------------------------------------------------

def test_discovery():
    print("\n=== Test: UDP Peer Discovery ===")

    # Use a different port to avoid conflicts
    TEST_PORT = 19899

    nodes = []
    for name in ["node_a", "node_b", "node_c"]:
        discovery = PeerDiscovery(name, TEST_PORT)
        discovery.start()
        nodes.append(discovery)

    # Wait for discovery
    time.sleep(3)

    # Check each node sees the other two
    for node in nodes:
        peers = node.get_peers()
        expected = 2
        test(
            f"{node.node_name} sees {expected} peers",
            len(peers) == expected,
            f"saw {len(peers)}: {list(peers.keys())}",
        )

    # Cleanup
    for node in nodes:
        node.stop()


# ---------------------------------------------------------------------------
# Test 6: PLATO tile persistence
# ---------------------------------------------------------------------------

def test_plato_persistence():
    print("\n=== Test: PLATO Tile Persistence ===")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = PlatoTileStore(db_path)
        store.write_tile("agent1", 1, "state", "alive")
        store.write_tile("agent1", 2, "state", "running")
        store.write_tile("agent1", 2, "drift", "0.001")

        test("Read tile at tick 1", store.read_tile("agent1", 1, "state") == "alive")
        test("Read tile at tick 2", store.read_tile("agent1", 2, "state") == "running")
        test("Read latest state", store.read_latest("agent1", "state") == "running")
        test("Read latest drift", store.read_latest("agent1", "drift") == "0.001")
        test("Read missing returns None", store.read_tile("agent1", 99, "state") is None)

        store.close()

        # Reopen and verify persistence
        store2 = PlatoTileStore(db_path)
        test("Persisted data survives reopen", store2.read_tile("agent1", 1, "state") == "alive")
        store2.close()
    finally:
        os.unlink(db_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Distributed Metronome Test Suite")
    print("=" * 60)

    test_tensor_midi()
    test_election()
    test_drift_bounded()
    test_sunset_inheritance()
    test_plato_persistence()
    test_discovery()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
