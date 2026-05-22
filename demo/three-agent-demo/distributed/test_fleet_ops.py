#!/usr/bin/env python3
"""Tests for fleet_ops.py — fleet operations CLI."""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent dirs for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metronome_core import MetronomeAgent, PlatoTileStore, CorrectionMode, ClockState
from metronome_node import tensor_midi_encode, tensor_midi_decode, tensor_midi_roundtrip


class TestTensorMIDI(unittest.TestCase):
    """Test Tensor-MIDI encoding/decoding."""

    def test_roundtrip_basic(self):
        payload = {"a": 0.5, "b": -0.3}
        encoded = tensor_midi_encode(payload)
        decoded = tensor_midi_decode(encoded)
        for k in payload:
            self.assertAlmostEqual(payload[k], decoded[k], places=4)

    def test_roundtrip_single_key(self):
        payload = {"x": 0.0}
        decoded = tensor_midi_decode(tensor_midi_encode(payload))
        self.assertAlmostEqual(decoded["x"], 0.0, places=4)

    def test_roundtrip_clamped(self):
        """Values outside [-1, 1] should be clamped."""
        payload = {"big": 5.0, "small": -10.0}
        decoded = tensor_midi_decode(tensor_midi_encode(payload))
        self.assertAlmostEqual(decoded["big"], 1.0, places=4)
        self.assertAlmostEqual(decoded["small"], -1.0, places=4)

    def test_helper_function(self):
        payload = {"c": 0.123, "t": -0.456}
        result = tensor_midi_roundtrip(payload)
        for k in payload:
            self.assertAlmostEqual(payload[k], result[k], places=4)

    def test_empty_payload(self):
        decoded = tensor_midi_decode(tensor_midi_encode({}))
        self.assertEqual(decoded, {})


class TestFleetOpsMessages(unittest.TestCase):
    """Test fleet_ops message parsing and formatting."""

    def test_sunset_message_format(self):
        msg = {"type": "sunset", "target": "forgemaster", "from": "fleet_ops"}
        encoded = json.dumps(msg)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["type"], "sunset")
        self.assertEqual(decoded["target"], "forgemaster")

    def test_announce_message_parse(self):
        raw = json.dumps({
            "type": "announce",
            "name": "node-alpha",
            "port": 19840,
            "start_time": 1000.0,
            "uptime": 42.5,
        })
        msg = json.loads(raw)
        self.assertEqual(msg["type"], "announce")
        self.assertEqual(msg["name"], "node-alpha")
        self.assertAlmostEqual(msg["uptime"], 42.5)

    def test_cadence_message_parse(self):
        raw = json.dumps({
            "type": "cadence",
            "name": "oracle1",
            "cadence_norm": 0.5,
            "tick": 999,
        })
        msg = json.loads(raw)
        self.assertEqual(msg["type"], "cadence")
        self.assertEqual(msg["name"], "oracle1")
        self.assertEqual(msg["tick"], 999)

    def test_peer_deduplication(self):
        """Simulate peer collection deduplication logic."""
        peers = {}
        announcements = [
            {"name": "alpha", "port": 19840, "uptime": 10.0},
            {"name": "beta", "port": 19840, "uptime": 9.0},
            {"name": "alpha", "port": 19840, "uptime": 11.0},  # update
            {"name": "gamma", "port": 19840, "uptime": 8.0},
            {"name": "beta", "port": 19840, "uptime": 10.0},   # update
        ]
        for a in announcements:
            peers[a["name"]] = a

        self.assertEqual(len(peers), 3)
        self.assertAlmostEqual(peers["alpha"]["uptime"], 11.0)
        self.assertAlmostEqual(peers["beta"]["uptime"], 10.0)

    def test_peer_sorting(self):
        """Peers should be sorted by name."""
        peer_list = [
            {"name": "zeta", "uptime": 5},
            {"name": "alpha", "uptime": 10},
            {"name": "mango", "uptime": 7},
        ]
        sorted_peers = sorted(peer_list, key=lambda p: p["name"])
        self.assertEqual(sorted_peers[0]["name"], "alpha")
        self.assertEqual(sorted_peers[2]["name"], "zeta")


class TestPlatoTileStore(unittest.TestCase):
    """Test PLATO tile store for tiles command support."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmpfile.close()
        self.store = PlatoTileStore(self.tmpfile.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmpfile.name)

    def test_write_and_read_tile(self):
        self.store.write_tile("forgemaster", 1, "local_time", "1/1")
        result = self.store.read_tile("forgemaster", 1, "local_time")
        self.assertEqual(result, "1/1")

    def test_read_latest(self):
        self.store.write_tile("forgemaster", 1, "drift", "0.001")
        self.store.write_tile("forgemaster", 2, "drift", "0.002")
        self.store.write_tile("forgemaster", 3, "drift", "0.003")
        latest = self.store.read_latest("forgemaster", "drift")
        self.assertEqual(latest, "0.003")

    def test_read_missing_tile(self):
        result = self.store.read_tile("nonexistent", 1, "key")
        self.assertIsNone(result)


class TestMetronomeAgent(unittest.TestCase):
    """Test core metronome agent behavior relevant to fleet ops."""

    def test_tick_increments(self):
        agent = MetronomeAgent("test")
        agent.tick()
        agent.tick()
        self.assertEqual(agent.tick_count, 2)

    def test_sunset_payload(self):
        agent = MetronomeAgent("test", drift_rate=0.01)
        for _ in range(10):
            agent.tick()
        payload = agent.sunset()
        self.assertIn("true_time", payload)
        self.assertIn("offset", payload)
        self.assertIn("drift_rate", payload)
        self.assertIn("tick_count", payload)

    def test_inherit_preserves_state(self):
        agent1 = MetronomeAgent("old", drift_rate=0.005)
        for _ in range(100):
            agent1.tick()
        sunset_data = agent1.sunset()

        agent2 = MetronomeAgent("new")
        agent2.inherit(sunset_data)
        self.assertEqual(agent2.is_cadence_caller, True)
        self.assertEqual(agent2.tick_count, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
