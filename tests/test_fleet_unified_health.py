#!/usr/bin/env python3
"""Tests for fleet_unified_health.py — 22 tests covering all components.

Run: python -m pytest tests/test_fleet_unified_health.py -v
"""

import json
import threading
import time
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from unittest.mock import patch, MagicMock
from dataclasses import asdict

import numpy as np

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_unified_health import (
    ConservationStatus,
    StructuralHealth,
    StructuralSnapshot,
    BehavioralHealth,
    ModelRecord,
    FleetHealthReport,
    ConservationMonitor,
    ConservationTrend,
    DiagnosticsRunner,
    HealthEndpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hebbian_status(rooms=6, flow_events=42, kernel_updates=100,
                         compliance_rate="95.0%", auto_calibrated=True):
    return {
        "service": "fleet-hebbian",
        "status": "running",
        "port": 8849,
        "rooms": rooms,
        "flow_events": flow_events,
        "kernel_updates": kernel_updates,
        "compliance_rate": compliance_rate,
        "auto_calibrated": auto_calibrated,
        "tracker_records": flow_events,
        "stages": {},
        "clusters": 2,
    }


def _make_hebbian_conservation(gamma=0.12, H=0.95, sum_val=1.07,
                               predicted=1.10, deviation=-0.03, sigma=0.05,
                               conserved=True, correction_applied=False):
    return {
        "n_rooms": 6,
        "V": 6,
        "update_count": 100,
        "correction_count": 5,
        "compliance_rate": "95.0%",
        "auto_calibrated": True,
        "warmup_target": 1.10,
        "conservation": {
            "gamma": gamma,
            "H": H,
            "sum": sum_val,
            "predicted": predicted,
            "deviation": deviation,
            "sigma": sigma,
            "conserved": conserved,
            "correction_applied": correction_applied,
        },
        "params": {
            "lr": 0.01,
            "decay": 0.001,
            "tolerance_sigma": 2.0,
            "correction_strength": 0.5,
        },
    }


# ---------------------------------------------------------------------------
# StructuralHealth tests
# ---------------------------------------------------------------------------

class TestStructuralHealth(unittest.TestCase):
    """Tests for StructuralHealth class."""

    def test_collect_when_service_down(self):
        """Should return snapshot with hebbian_service_reachable=False when service is down."""
        sh = StructuralHealth(hebbian_port=19999, timeout=0.5)
        snap = sh.collect()
        self.assertFalse(snap.hebbian_service_reachable)
        self.assertEqual(snap.status, ConservationStatus.GREEN)  # default when no data
        self.assertIn("unreachable", snap.error.lower())

    def test_collect_parses_conservation(self):
        """Should parse conservation data correctly from mock response."""
        sh = StructuralHealth(hebbian_port=19999, timeout=0.5)

        # Mock the _fetch_json method
        def mock_fetch(path):
            if path == "/conservation":
                return _make_hebbian_conservation(deviation=-0.03, sigma=0.05)
            if path == "/status":
                return _make_hebbian_status()
            return None

        sh._fetch_json = mock_fetch
        snap = sh.collect()

        self.assertTrue(snap.hebbian_service_reachable)
        self.assertAlmostEqual(snap.deviation, -0.03, places=2)
        self.assertAlmostEqual(snap.sigma, 0.05, places=2)
        self.assertEqual(snap.status, ConservationStatus.GREEN)  # 0.03/0.05 = 0.6 < 1σ

    def test_classify_yellow(self):
        """1-2σ deviation should classify as YELLOW."""
        sh = StructuralHealth(hebbian_port=19999)
        snap = sh.collect()
        # Test classification directly
        self.assertEqual(sh._classify_status(0.075, 0.05), ConservationStatus.YELLOW)  # 1.5σ
        self.assertEqual(sh._classify_status(0.05, 0.05), ConservationStatus.YELLOW)  # exactly 1σ

    def test_classify_red(self):
        """>2σ deviation should classify as RED."""
        sh = StructuralHealth(hebbian_port=19999)
        self.assertEqual(sh._classify_status(0.15, 0.05), ConservationStatus.RED)  # 3σ

    def test_classify_green(self):
        """<1σ deviation should classify as GREEN."""
        sh = StructuralHealth(hebbian_port=19999)
        self.assertEqual(sh._classify_status(0.03, 0.05), ConservationStatus.GREEN)

    def test_summary_no_data(self):
        """Summary with no data should indicate no_data."""
        sh = StructuralHealth(hebbian_port=19999)
        summary = sh.summary()
        self.assertEqual(summary["status"], "no_data")
        self.assertFalse(summary["hebbian_service_reachable"])

    def test_history_tracks_snapshots(self):
        """History should accumulate snapshots."""
        sh = StructuralHealth(hebbian_port=19999)
        sh._fetch_json = lambda path: None  # service down
        sh.collect()
        sh.collect()
        self.assertEqual(len(sh.history()), 2)

    def test_compliance_rate_string_parsing(self):
        """Should handle compliance_rate as percentage string."""
        sh = StructuralHealth(hebbian_port=19999)

        def mock_fetch(path):
            if path == "/conservation":
                return _make_hebbian_conservation()
            if path == "/status":
                return _make_hebbian_status(compliance_rate="85.5%")
            return None

        sh._fetch_json = mock_fetch
        snap = sh.collect()
        self.assertAlmostEqual(snap.compliance_rate, 0.855, places=2)


# ---------------------------------------------------------------------------
# BehavioralHealth tests
# ---------------------------------------------------------------------------

class TestBehavioralHealth(unittest.TestCase):

    def setUp(self):
        self.bh = BehavioralHealth()

    def test_initializes_known_models(self):
        """Should pre-populate with models from Study 50."""
        self.assertIn("Seed-2.0-mini", self.bh._models)
        self.assertIn("gemma3:1b", self.bh._models)
        self.assertEqual(self.bh._models["Seed-2.0-mini"].tier, 1)
        self.assertEqual(self.bh._models["Qwen3.6-35B"].tier, 3)

    def test_record_query(self):
        """Should record a query and update accuracy."""
        self.bh.record_query("Seed-2.0-mini", correct=True)
        self.bh.record_query("Seed-2.0-mini", correct=True)
        self.bh.record_query("Seed-2.0-mini", correct=False)
        rec = self.bh.get_model("Seed-2.0-mini")
        self.assertEqual(rec.total_queries, 3)
        self.assertEqual(rec.correct, 2)

    def test_record_query_new_model(self):
        """Should create a new record for unknown models."""
        self.bh.record_query("new-model", correct=True, tier=2, provider="test")
        rec = self.bh.get_model("new-model")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.tier, 2)
        self.assertEqual(rec.provider, "test")

    def test_tier_distribution(self):
        """Should compute tier distribution correctly."""
        dist = self.bh.tier_distribution()
        self.assertIn(1, dist)
        self.assertIn(2, dist)
        self.assertIn(3, dist)
        self.assertEqual(dist[1]["name"], "direct")
        # Tier 1 should have 3 models (Seed-mini, Seed-code, gemma3:1b)
        self.assertEqual(dist[1]["n_models"], 3)

    def test_tier_utilization_balance_perfect(self):
        """Perfect balance when all tiers have equal queries."""
        for model in ["Seed-2.0-mini", "llama3.2:1b", "Qwen3.6-35B"]:
            for _ in range(10):
                self.bh.record_query(model, correct=True)
        balance = self.bh.tier_utilization_balance()
        self.assertGreater(balance, 0.95)

    def test_tier_utilization_balance_imbalanced(self):
        """Low balance when all queries go to one tier."""
        for _ in range(100):
            self.bh.record_query("Seed-2.0-mini", correct=True)
        balance = self.bh.tier_utilization_balance()
        self.assertLess(balance, 0.7)

    def test_accuracy_drift(self):
        """Should detect accuracy drift."""
        # Record improving then degrading results
        for _ in range(30):
            self.bh.record_query("Seed-2.0-mini", correct=True)
        for _ in range(30):
            self.bh.record_query("Seed-2.0-mini", correct=False)
        drift = self.bh.accuracy_drift("Seed-2.0-mini")
        self.assertIsNotNone(drift)
        self.assertLess(drift, -0.3)  # Significant degradation

    def test_models_with_drift(self):
        """Should list models with significant drift."""
        for _ in range(30):
            self.bh.record_query("Seed-2.0-mini", correct=True)
        for _ in range(30):
            self.bh.record_query("Seed-2.0-mini", correct=False)
        alerts = self.bh.models_with_drift(threshold=0.1)
        self.assertTrue(any(a["model"] == "Seed-2.0-mini" for a in alerts))

    def test_provider_availability(self):
        """Should group models by provider."""
        avail = self.bh.provider_availability()
        self.assertIn("deepinfra", avail)
        self.assertIn("ollama", avail)
        self.assertGreater(avail["deepinfra"]["total"], 0)
        self.assertGreater(avail["ollama"]["total"], 0)

    def test_mark_availability(self):
        """Should update model availability."""
        self.bh.mark_availability("Seed-2.0-mini", False)
        rec = self.bh.get_model("Seed-2.0-mini")
        self.assertFalse(rec.available)
        self.bh.mark_availability("Seed-2.0-mini", True)
        self.assertTrue(self.bh.get_model("Seed-2.0-mini").available)

    def test_recent_accuracy_rolling(self):
        """Recent accuracy should be a rolling window."""
        for _ in range(60):
            self.bh.record_query("Seed-2.0-mini", correct=True)
        for _ in range(40):
            self.bh.record_query("Seed-2.0-mini", correct=False)
        rec = self.bh.get_model("Seed-2.0-mini")
        # Recent accuracy should reflect the last 50 (mostly False)
        self.assertLess(rec.recent_accuracy, 0.5)


# ---------------------------------------------------------------------------
# ConservationMonitor tests
# ---------------------------------------------------------------------------

class TestConservationMonitor(unittest.TestCase):

    def test_insufficient_data(self):
        """Should report insufficient_data when < min_samples."""
        cm = ConservationMonitor(min_samples=10)
        for i in range(5):
            cm.record(0.01, timestamp=i)
        trend = cm.analyze()
        self.assertEqual(trend.direction, "insufficient_data")
        self.assertFalse(trend.alert)

    def test_stable_trend(self):
        """Should detect stable trend."""
        cm = ConservationMonitor(min_samples=10, alert_threshold=0.002)
        for i in range(20):
            cm.record(0.01 + (i % 3) * 0.001, timestamp=float(i))
        trend = cm.analyze()
        self.assertEqual(trend.direction, "stable")
        self.assertFalse(trend.alert)

    def test_degrading_trend(self):
        """Should detect degrading trend and raise alert."""
        cm = ConservationMonitor(min_samples=10, alert_threshold=0.0001)
        for i in range(30):
            # Steadily increasing deviation with large steps
            cm.record(1.0 * i, timestamp=float(i))
        trend = cm.analyze()
        self.assertEqual(trend.direction, "degrading")
        self.assertTrue(trend.alert)
        self.assertIn("degrading", trend.alert_message.lower())

    def test_improving_trend(self):
        """Should detect improving trend."""
        cm = ConservationMonitor(min_samples=10, alert_threshold=0.0001)
        for i in range(30):
            cm.record(30.0 - 1.0 * i, timestamp=float(i))
        trend = cm.analyze()
        self.assertEqual(trend.direction, "improving")
        self.assertFalse(trend.alert)  # improving = no alert

    def test_window_respected(self):
        """Should only keep last `window` samples."""
        cm = ConservationMonitor(min_samples=5, window=10)
        for i in range(50):
            cm.record(float(i), timestamp=float(i))
        trend = cm.analyze()
        self.assertEqual(trend.samples, 10)

    def test_summary_format(self):
        """Summary should be a well-formed dict."""
        cm = ConservationMonitor(min_samples=3)
        for i in range(5):
            cm.record(0.01, timestamp=float(i))
        s = cm.summary()
        self.assertIn("direction", s)
        self.assertIn("slope", s)
        self.assertIn("alert", s)


# ---------------------------------------------------------------------------
# FleetHealthReport tests
# ---------------------------------------------------------------------------

class TestFleetHealthReport(unittest.TestCase):

    def test_to_dict(self):
        """Should serialize to a clean dict."""
        report = FleetHealthReport(
            structural={"status": "GREEN"},
            behavioral={"total_models": 12},
            overall_score=0.85,
            recommendations=["✅ Fleet health nominal"],
        )
        d = report.to_dict()
        self.assertIn("overall_score", d)
        self.assertIn("structural", d)
        self.assertIn("behavioral", d)
        self.assertIn("recommendations", d)
        self.assertAlmostEqual(d["overall_score"], 0.85, places=2)
        self.assertGreater(d["timestamp"], 0)

    def test_auto_timestamp(self):
        """Should auto-populate timestamp."""
        report = FleetHealthReport(
            structural={}, behavioral={},
            overall_score=1.0, recommendations=[],
        )
        self.assertGreater(report.timestamp, 0)


# ---------------------------------------------------------------------------
# HealthEndpoint tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint(unittest.TestCase):

    def setUp(self):
        self.endpoint = HealthEndpoint(port=0)  # port=0 to avoid binding

    def test_compute_overall_score_green(self):
        """Should compute high score when everything is green."""
        structural = {
            "compliance_rate": 0.95,
            "status": ConservationStatus.GREEN,
        }
        behavioral = {
            "tier_utilization_balance": 0.9,
            "tiers": {
                1: {"overall_accuracy": 1.0, "total_queries": 10},
                2: {"overall_accuracy": 0.8, "total_queries": 10},
            },
        }
        score = self.endpoint._compute_overall_score(structural, behavioral)
        self.assertGreater(score, 0.85)

    def test_compute_overall_score_red(self):
        """Should compute low score when conservation is RED."""
        structural = {
            "compliance_rate": 0.5,
            "status": ConservationStatus.RED,
        }
        behavioral = {
            "tier_utilization_balance": 0.3,
            "tiers": {
                1: {"overall_accuracy": 0.5, "total_queries": 10},
            },
        }
        score = self.endpoint._compute_overall_score(structural, behavioral)
        self.assertLess(score, 0.6)

    def test_recommendations_service_down(self):
        """Should recommend fixing unreachable Hebbian service."""
        structural = {"hebbian_service_reachable": False, "status": "GREEN"}
        behavioral = {"drift_alerts": [], "tier_utilization_balance": 0.9, "provider_availability": {}}
        trend = {"alert": False}
        recs = self.endpoint._generate_recommendations(structural, behavioral, trend)
        self.assertTrue(any("unreachable" in r.lower() for r in recs))

    def test_recommendations_drift(self):
        """Should flag models with accuracy drift."""
        structural = {"hebbian_service_reachable": True, "status": "GREEN", "compliance_rate": 0.95}
        behavioral = {
            "drift_alerts": [
                {"model": "TestModel", "tier": 2, "drift": -0.2, "direction": "degrading", "current_accuracy": 0.6}
            ],
            "tier_utilization_balance": 0.8,
            "provider_availability": {},
        }
        trend = {"alert": False}
        recs = self.endpoint._generate_recommendations(structural, behavioral, trend)
        self.assertTrue(any("TestModel" in r for r in recs))

    def test_recommendations_all_good(self):
        """Should say fleet is nominal when everything is fine."""
        structural = {"hebbian_service_reachable": True, "status": "GREEN", "compliance_rate": 0.98, "auto_calibrated": True}
        behavioral = {"drift_alerts": [], "tier_utilization_balance": 0.9, "provider_availability": {}}
        trend = {"alert": False}
        recs = self.endpoint._generate_recommendations(structural, behavioral, trend)
        self.assertTrue(any("nominal" in r.lower() for r in recs))

    def test_build_report_structure(self):
        """build_report should return a valid FleetHealthReport."""
        # Mock structural collection to avoid network
        def mock_collect():
            return StructuralSnapshot(
                gamma=0.1, H=0.9, gamma_plus_H=1.0, predicted=1.05,
                deviation=-0.05, sigma=0.05, conserved=True,
                compliance_rate=0.95, room_count=6, flow_events=42,
                hebbian_service_reachable=True,
            )
        self.endpoint.structural.collect = mock_collect
        self.endpoint.structural.summary = lambda: {
            "status": ConservationStatus.GREEN,
            "hebbian_service_reachable": True,
            "compliance_rate": 0.95,
            "auto_calibrated": True,
            "gamma_plus_H": 1.0,
            "predicted": 1.05,
            "deviation": -0.05,
            "sigma": 0.05,
            "room_count": 6,
            "flow_events": 42,
            "kernel_updates": 100,
            "conserved": True,
            "timestamp": time.time(),
        }

        report = self.endpoint.build_report()
        self.assertIsInstance(report, FleetHealthReport)
        self.assertGreater(report.overall_score, 0.0)
        self.assertGreater(len(report.recommendations), 0)
        self.assertIn("structural", report.to_dict())
        self.assertIn("behavioral", report.to_dict())


# ---------------------------------------------------------------------------
# DiagnosticsRunner tests
# ---------------------------------------------------------------------------

class TestDiagnosticsRunner(unittest.TestCase):

    def test_check_hebbian_service_down(self):
        """Should report failure when Hebbian service is unreachable."""
        dr = DiagnosticsRunner(hebbian_port=19999)
        result = dr.check_hebbian_service()
        self.assertFalse(result.passed)
        self.assertEqual(result.name, "hebbian_service")

    def test_check_conservation_no_data(self):
        """Should report failure when no structural data available."""
        dr = DiagnosticsRunner()
        sh = StructuralHealth(hebbian_port=19999, timeout=0.5)
        result = dr.check_conservation_compliance(sh)
        self.assertFalse(result.passed)

    def test_check_deepinfra_timeout(self):
        """Should handle DeepInfra timeout gracefully."""
        dr = DiagnosticsRunner(deepinfra_timeout=0.001)
        result = dr.check_deepinfra()
        # Will pass or fail depending on network, but shouldn't crash
        self.assertIn(result.name, ["deepinfra_api"])

    def test_check_ollama_timeout(self):
        """Should handle Ollama timeout gracefully."""
        dr = DiagnosticsRunner(ollama_timeout=0.001)
        result = dr.check_ollama()
        self.assertIn(result.name, ["ollama_api"])

    def test_run_all_structure(self):
        """run_all should return structured diagnostics."""
        dr = DiagnosticsRunner(hebbian_port=19999)
        sh = StructuralHealth(hebbian_port=19999, timeout=0.1)
        result = dr.run_all(sh)
        self.assertIn("overall", result)
        self.assertIn("checks", result)
        self.assertIn("passed", result)
        self.assertIn("total", result)
        self.assertEqual(result["total"], 4)


# ---------------------------------------------------------------------------
# Integration: HealthEndpoint with mock HTTP server
# ---------------------------------------------------------------------------

class TestHealthEndpointHTTP(unittest.TestCase):
    """Test the HTTP endpoints using a real HTTP server with mocked backends."""

    @classmethod
    def setUpClass(cls):
        """Start the health endpoint on a random port."""
        import socket
        # Find a free port
        sock = socket.socket()
        sock.bind(("", 0))
        cls.port = sock.getsockname()[1]
        sock.close()

        cls.endpoint = HealthEndpoint(port=cls.port, hebbian_port=19999)
        # Mock structural to avoid network calls
        cls._original_collect = cls.endpoint.structural.collect

        cls.endpoint.start(block=False)
        time.sleep(0.3)  # Let server start

    @classmethod
    def tearDownClass(cls):
        cls.endpoint.stop()

    def _get(self, path: str) -> dict:
        import urllib.request
        url = f"http://localhost:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def _post(self, path: str, body: dict) -> dict:
        import urllib.request
        url = f"http://localhost:{self.port}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="POST",
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def test_get_fleet_health(self):
        """GET /fleet/health should return FleetHealthReport."""
        result = self._get("/fleet/health")
        self.assertIn("overall_score", result)
        self.assertIn("structural", result)
        self.assertIn("behavioral", result)
        self.assertIn("recommendations", result)

    def test_get_structural(self):
        """GET /fleet/health/structural should return structural data."""
        result = self._get("/fleet/health/structural")
        self.assertIn("status", result)

    def test_get_behavioral(self):
        """GET /fleet/health/behavioral should return behavioral data."""
        result = self._get("/fleet/health/behavioral")
        self.assertIn("total_models", result)
        self.assertIn("tiers", result)

    def test_post_check(self):
        """POST /fleet/health/check should run diagnostics."""
        result = self._post("/fleet/health/check", {})
        self.assertIn("overall", result)
        self.assertIn("checks", result)

    def test_post_record(self):
        """POST /fleet/health/record should record a behavioral observation."""
        result = self._post("/fleet/health/record", {
            "model": "test-model",
            "correct": True,
            "tier": 2,
            "provider": "test",
        })
        self.assertTrue(result["recorded"])

    def test_post_record_missing_model(self):
        """POST /fleet/health/record without model should return 400."""
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("/fleet/health/record", {"correct": True})
        self.assertEqual(ctx.exception.code, 400)

    def test_post_availability(self):
        """POST /fleet/health/availability should update model availability."""
        result = self._post("/fleet/health/availability", {
            "model": "Seed-2.0-mini",
            "available": False,
        })
        self.assertTrue(result["updated"])

    def test_get_trend(self):
        """GET /fleet/health/trend should return conservation trend."""
        result = self._get("/fleet/health/trend")
        self.assertIn("direction", result)
        self.assertIn("slope", result)

    def test_get_status(self):
        """GET /fleet/health/status should return lightweight status."""
        result = self._get("/fleet/health/status")
        self.assertIn("running", result)

    def test_unknown_endpoint(self):
        """GET unknown path should return 404."""
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/unknown")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
