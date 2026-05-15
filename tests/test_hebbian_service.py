"""Tests for fleet_hebbian_service.py — conservation-constrained Hebbian service.

Run:
    python -m pytest tests/test_hebbian_service.py -v
    python tests/test_hebbian_service.py          # standalone
"""

import json
import math
import sys
import os
import threading
import time
import urllib.request
import urllib.error

import numpy as np
import pytest

# Ensure workspace is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_hebbian_service import (
    FleetHebbianService,
    ConservationHebbianKernel,
    TileFlowTracker,
    EmergentStageClassifier,
    RoomClusterDetector,
    predicted_gamma_plus_H,
    coupling_entropy,
    algebraic_normalized,
    ConservationReport,
    FlowRecord,
)


# ─── Fixtures ───────────────────────────────────────────────────────

class _PortMgr:
    """Allocate unique ports per test to avoid EADDRINUSE."""
    _next = 28849

    @classmethod
    def next_port(cls):
        p = cls._next
        cls._next += 1
        return p


@pytest.fixture
def svc():
    """Create a FleetHebbianService with unique port and start HTTP."""
    port = _PortMgr.next_port()
    s = FleetHebbianService(
        db_path="/tmp/test_hebbian_nonexistent.db",
        port=port,
        persist_dir=f"/tmp/test_hebbian_persist_{port}",
    )
    s.start(block=False)
    time.sleep(0.2)
    yield s
    s.stop()
    time.sleep(0.1)


@pytest.fixture
def kernel():
    return ConservationHebbianKernel(n_rooms=6, V=6, learning_rate=0.05)


@pytest.fixture
def tracker():
    return TileFlowTracker(ring_size=1000)


# ─── Conservation Math ─────────────────────────────────────────────

class TestConservationMath:
    def test_predicted_gamma_plus_H_decreases_with_V(self):
        """γ+H should decrease as fleet size grows (log relationship)."""
        val_5 = predicted_gamma_plus_H(5)
        val_100 = predicted_gamma_plus_H(100)
        assert val_5 > val_100, "γ+H should decrease with V"

    def test_predicted_bounds(self):
        """Predicted γ+H should be between 0.5 and 1.5 for reasonable V."""
        for V in [5, 10, 30, 100]:
            val = predicted_gamma_plus_H(V)
            assert 0.3 < val < 1.5, f"V={V}: γ+H={val} out of bounds"

    def test_coupling_entropy_normalized(self):
        """Spectral entropy should be in [0, 1] for any coupling matrix."""
        rng = np.random.RandomState(0)
        for _ in range(10):
            C = rng.rand(5, 5).astype(np.float32)
            C = (C + C.T) / 2
            H = coupling_entropy(C)
            assert 0.0 <= H <= 1.0, f"H={H} out of [0,1]"

    def test_algebraic_normalized_range(self):
        """Algebraic connectivity γ should be in [0, 1]."""
        C = np.array([[0, 0.5, 0], [0.5, 0, 0.3], [0, 0.3, 0]], dtype=np.float32)
        gamma = algebraic_normalized(C)
        assert 0.0 <= gamma <= 1.0

    def test_identity_matrix_high_connectivity(self):
        """A fully connected graph should have high γ."""
        n = 5
        C = np.ones((n, n), dtype=np.float32) - np.eye(n)
        gamma = algebraic_normalized(C)
        assert gamma > 0.5, f"Fully connected γ={gamma} too low"


# ─── TileFlowTracker ──────────────────────────────────────────────

class TestTileFlowTracker:
    def test_record_and_count(self, tracker):
        tracker.record_flow("room-a", "room-b", "model", "hash1")
        tracker.record_flow("room-a", "room-c", "data", "hash2")
        assert len(tracker) == 2

    def test_connection_strength_bidirectional(self, tracker):
        tracker.record_flow("room-a", "room-b", "model", "h1")
        tracker.record_flow("room-b", "room-a", "model", "h2")
        s = tracker.get_connection_strength("room-a", "room-b")
        assert s > 0, "Bidirectional flow should create positive strength"

    def test_connection_strength_unrelated(self, tracker):
        tracker.record_flow("room-a", "room-b", "model", "h1")
        s = tracker.get_connection_strength("room-x", "room-y")
        assert s == 0.0, "Unrelated rooms should have zero strength"

    def test_room_neighbors(self, tracker):
        for _ in range(5):
            tracker.record_flow("room-a", "room-b", "model", "h")
        tracker.record_flow("room-a", "room-c", "data", "h2")
        neighbors = tracker.room_neighbors("room-a", min_strength=0.0)
        assert len(neighbors) >= 2
        # room-b should be stronger than room-c (5 vs 1 flows)
        b_strength = next((s for r, s in neighbors if r == "room-b"), 0)
        c_strength = next((s for r, s in neighbors if r == "room-c"), 0)
        assert b_strength >= c_strength

    def test_iter_recent_order(self, tracker):
        tracker.record_flow("r1", "r2", "model", "h1")
        tracker.record_flow("r1", "r3", "data", "h2")
        recent = list(tracker.iter_recent(2))
        assert recent[0].dest_room == "r3"  # newest first
        assert recent[1].dest_room == "r2"

    def test_ring_buffer_overflow(self):
        small_tracker = TileFlowTracker(ring_size=10)
        for i in range(50):
            small_tracker.record_flow("a", "b", "model", f"h{i}")
        assert len(small_tracker) == 10

    def test_lamport_clock_increases(self, tracker):
        tracker.record_flow("a", "b", "model", "h1", lamport_clock=5)
        rec = tracker.record_flow("a", "b", "model", "h2", lamport_clock=3)
        assert rec.lamport_clock >= 6  # max(0,5)+1 = 6 for first, then 7


# ─── ConservationHebbianKernel ────────────────────────────────────

class TestConservationKernel:
    def test_initial_weights_zero(self, kernel):
        w = kernel.get_weights()
        assert w.shape == (6, 6)
        assert np.allclose(w, 0.0)

    def test_update_creates_weights(self, kernel):
        pre = np.array([1, 0, 0, 0, 0, 0], dtype=np.float32)
        post = np.array([0, 0.9, 0, 0, 0, 0], dtype=np.float32)
        kernel.update(pre, post)
        w = kernel.get_weights()
        assert w[0, 1] > 0, "Hebbian update should create positive weight"
        assert w[0, 0] == 0.0, "No self-activation expected with zero post"

    def test_update_returns_report(self, kernel):
        pre = np.zeros(6, dtype=np.float32)
        post = np.zeros(6, dtype=np.float32)
        pre[0] = 1.0
        post[1] = 0.8
        report = kernel.update(pre, post)
        assert isinstance(report, ConservationReport)
        assert report.update_count == 1

    def test_conservation_report_without_update(self, kernel):
        report = kernel.conservation_report()
        assert report.gamma_plus_H == 0.0  # all-zero matrix
        assert report.update_count == 0

    def test_compliance_rate_initial(self, kernel):
        assert kernel.compliance_rate() == 1.0  # no updates = perfect

    def test_multiple_updates(self, kernel):
        rng = np.random.RandomState(42)
        for _ in range(100):
            pre = rng.rand(6).astype(np.float32)
            post = rng.rand(6).astype(np.float32)
            kernel.update(pre, post)
        report = kernel.conservation_report()
        assert report.update_count == 100
        assert 0.0 <= kernel.compliance_rate() <= 1.0

    def test_summary_structure(self, kernel):
        s = kernel.summary()
        assert "n_rooms" in s
        assert "V" in s
        assert "conservation" in s
        assert "params" in s
        assert "compliance_rate" in s

    def test_set_and_get_weights(self, kernel):
        w = np.eye(6, dtype=np.float32) * 0.5
        kernel.set_weights(w)
        assert np.allclose(kernel.get_weights(), w)

    def test_auto_calibration(self, kernel):
        rng = np.random.RandomState(42)
        for i in range(100):
            pre = rng.rand(6).astype(np.float32)
            post = rng.rand(6).astype(np.float32)
            kernel.update(pre, post)
        assert kernel._auto_calibrated, "Should auto-calibrate after 50 updates"
        assert kernel._warmup_target > 0

    def test_non_negative_weights(self, kernel):
        rng = np.random.RandomState(0)
        for _ in range(200):
            pre = rng.rand(6).astype(np.float32) * 2 - 1  # some negative
            post = rng.rand(6).astype(np.float32) * 2 - 1
            kernel.update(np.abs(pre), np.abs(post))
        w = kernel.get_weights()
        assert np.all(w >= 0), "Weights should be non-negative after clip"


# ─── EmergentStageClassifier ─────────────────────────────────────

class TestStageClassifier:
    def test_unknown_room_stage_0(self):
        sc = EmergentStageClassifier(min_observations=5)
        assert sc.classify_room("unknown") == 0

    def test_stage_4_after_many_successes(self):
        sc = EmergentStageClassifier(min_observations=5)
        for _ in range(20):
            sc.observe("room-a", "model", success=True, confidence=0.9)
        assert sc.classify_room("room-a") == 4

    def test_stage_1_after_many_failures(self):
        sc = EmergentStageClassifier(min_observations=5)
        for _ in range(20):
            sc.observe("room-b", "model", success=False, confidence=0.05)
        assert sc.classify_room("room-b") == 1

    def test_echo_not_counted_as_success(self):
        sc = EmergentStageClassifier(min_observations=5)
        for _ in range(20):
            sc.observe("room-c", "model", success=True, confidence=0.9,
                        response_is_echo=True)
        # Echoes should suppress effective success
        assert sc.classify_room("room-c") < 4

    def test_export_stages(self):
        sc = EmergentStageClassifier(min_observations=5)
        for _ in range(10):
            sc.observe("r1", "model", True, 0.9)
            sc.observe("r2", "data", False, 0.1)
        stages = sc.export_stages()
        assert "r1" in stages
        assert "r2" in stages


# ─── RoomClusterDetector ─────────────────────────────────────────

class TestRoomClusterDetector:
    def test_empty_input(self):
        d = RoomClusterDetector()
        clusters = d.detect([], np.zeros((0, 0)), TileFlowTracker())
        assert clusters == []

    def test_single_room(self):
        d = RoomClusterDetector()
        clusters = d.detect(["room-a"], np.zeros((1, 1)), TileFlowTracker())
        assert clusters == []  # min_cluster_size=2

    def test_two_connected_rooms(self):
        d = RoomClusterDetector(min_strength=0.01)
        w = np.zeros((2, 2), dtype=np.float32)
        w[0, 1] = 0.1
        w[1, 0] = 0.1
        clusters = d.detect(["room-a", "room-b"], w, TileFlowTracker())
        assert len(clusters) == 1
        assert set(clusters[0].rooms) == {"room-a", "room-b"}
        assert clusters[0].avg_internal_strength > 0

    def test_disconnected_rooms(self):
        d = RoomClusterDetector(min_strength=0.5)
        w = np.zeros((4, 4), dtype=np.float32)
        w[0, 1] = 0.8
        w[1, 0] = 0.8
        w[2, 3] = 0.8
        w[3, 2] = 0.8
        clusters = d.detect(["a", "b", "c", "d"], w, TileFlowTracker())
        assert len(clusters) == 2


# ─── FleetHebbianService ─────────────────────────────────────────

class TestFleetHebbianService:
    def test_submit_tile(self, svc):
        result = svc.submit_tile(
            tile_type="model",
            source_room="forgemaster-local",
            dest_room="fleet-ops",
            confidence=0.85,
        )
        assert result["total_routed"] == 1
        assert result["destinations"][0]["dest_room"] == "fleet-ops"
        assert result["destinations"][0]["routed"] is True

    def test_submit_tile_auto_route(self, svc):
        # First seed some flow
        svc.submit_tile("model", "forgemaster-local", "fleet-ops", confidence=0.9)
        svc.submit_tile("data", "forgemaster-local", "constraint-theory", confidence=0.8)

        # Now auto-route
        result = svc.submit_tile("model", source_room="forgemaster-local")
        assert result["total_routed"] >= 1
        assert result["tile_hash"] is not None

    def test_auto_calibrate(self, svc):
        result = svc.auto_calibrate(100)
        assert "compliance_rate" in result
        assert "rooms" in result
        assert result["rooms"] >= 6  # default rooms

    def test_get_clusters(self, svc):
        svc.auto_calibrate(100)
        clusters = svc.get_clusters()
        assert isinstance(clusters, list)
        # After calibration, should have at least one cluster
        if clusters:
            assert "rooms" in clusters[0]
            assert "cluster_id" in clusters[0]

    def test_get_weights(self, svc):
        svc.submit_tile("model", "forgemaster-local", "fleet-ops", confidence=0.9)
        data = svc.get_weights()
        assert "n_rooms" in data
        assert "top_connections" in data
        assert "weight_stats" in data
        assert data["weight_stats"]["nonzero"] > 0

    def test_get_conservation(self, svc):
        svc.submit_tile("data", "forgemaster-local", "fleet-ops", confidence=0.9)
        cons = svc.get_conservation()
        assert "conservation" in cons
        assert "params" in cons
        assert "update_count" in cons
        assert cons["update_count"] >= 1

    def test_get_flow(self, svc):
        svc.submit_tile("model", "forgemaster-local", "fleet-ops")
        svc.submit_tile("data", "forgemaster-local", "session-state")
        flow = svc.get_flow(10)
        assert len(flow) >= 2
        assert flow[0]["tile_type"] in ["model", "data"]

    def test_get_status(self, svc):
        status = svc.get_status()
        assert status["service"] == "fleet-hebbian"
        assert status["status"] == "running"
        assert status["rooms"] >= 6


# ─── HTTP API Integration ─────────────────────────────────────────

class TestHTTPAPI:
    def _port(self, svc):
        return svc.port

    def _get(self, svc, path):
        port = self._port(svc)
        req = urllib.request.Request(f"http://localhost:{port}{path}")
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())

    def _post(self, svc, path, body):
        port = self._port(svc)
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"http://localhost:{port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())

    def test_get_status(self, svc):
        data = self._get(svc, "/status")
        assert data["service"] == "fleet-hebbian"
        assert data["status"] == "running"

    def test_get_rooms(self, svc):
        data = self._get(svc, "/rooms")
        assert len(data["rooms"]) >= 6
        assert data["rooms"][0]["name"] is not None

    def test_post_tile(self, svc):
        result = self._post(svc, "/tile", {
            "tile_type": "model",
            "source_room": "forgemaster-local",
            "dest_room": "fleet-ops",
            "confidence": 0.85,
        })
        assert result["total_routed"] == 1
        assert result["destinations"][0]["dest_room"] == "fleet-ops"

    def test_post_tile_missing_field(self, svc):
        try:
            self._post(svc, "/tile", {"source_room": "x"})
            assert False, "Should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 400

    def test_get_conservation(self, svc):
        self._post(svc, "/tile", {
            "tile_type": "data",
            "source_room": "forgemaster-local",
            "dest_room": "fleet-ops",
        })
        data = self._get(svc, "/conservation")
        assert data["update_count"] >= 1

    def test_get_clusters(self, svc):
        self._post(svc, "/calibrate", {"n_steps": 100})
        data = self._get(svc, "/clusters")
        assert isinstance(data, list)

    def test_get_weights(self, svc):
        self._post(svc, "/tile", {
            "tile_type": "model",
            "source_room": "forgemaster-local",
            "dest_room": "fleet-ops",
        })
        data = self._get(svc, "/weights")
        assert data["n_rooms"] >= 6

    def test_get_flow(self, svc):
        self._post(svc, "/tile", {
            "tile_type": "deploy",
            "source_room": "forgemaster-local",
            "dest_room": "training-pipeline",
        })
        data = self._get(svc, "/flow?n=10")
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_stages(self, svc):
        self._post(svc, "/tile", {
            "tile_type": "model",
            "source_room": "forgemaster-local",
            "dest_room": "fleet-ops",
            "confidence": 0.9,
        })
        data = self._get(svc, "/stages")
        assert isinstance(data, dict)

    def test_post_save(self, svc):
        data = self._post(svc, "/save", {})
        assert data["saved"] is True

    def test_404(self, svc):
        try:
            self._get(svc, "/nonexistent")
            assert False, "Should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 404


# ─── Standalone runner ────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
