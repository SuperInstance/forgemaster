#!/usr/bin/env python3
"""Fleet Unified Health — structural + behavioral health in one endpoint.

Combines:
  - Structural health from the Hebbian service (γ+H, compliance, conservation)
  - Behavioral health from model tier distribution and accuracy tracking
  - Conservation monitor with trend detection
  - Full diagnostics with graceful degradation

Architecture:
    StructuralHealth ──► reads :8849/conservation, :8849/status
    BehavioralHealth ──► tracks model tier accuracy over time
    ConservationMonitor ──► watches γ+H trend, alerts on drift
    HealthEndpoint ──► HTTP API combining both health views

Endpoints:
    GET  /fleet/health              — full FleetHealthReport
    GET  /fleet/health/structural   — structural only
    GET  /fleet/health/behavioral   — behavioral only
    POST /fleet/health/check        — run diagnostics, return pass/fail
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
import urllib.error
from collections import deque
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Conservation status enum
# ---------------------------------------------------------------------------

class ConservationStatus:
    GREEN = "GREEN"    # < 1σ deviation
    YELLOW = "YELLOW"  # 1-2σ deviation
    RED = "RED"        # > 2σ deviation


# ---------------------------------------------------------------------------
# 1. StructuralHealth — reads from Hebbian service
# ---------------------------------------------------------------------------

@dataclass
class StructuralSnapshot:
    """Point-in-time structural health reading."""
    gamma: float = 0.0
    H: float = 0.0
    gamma_plus_H: float = 0.0
    predicted: float = 0.0
    deviation: float = 0.0
    sigma: float = 0.0
    conserved: bool = True
    compliance_rate: float = 1.0
    room_count: int = 0
    flow_events: int = 0
    kernel_updates: int = 0
    correction_applied: bool = False
    auto_calibrated: bool = False
    status: str = ConservationStatus.GREEN
    timestamp: float = 0.0
    hebbian_service_reachable: bool = False
    error: str = ""


class StructuralHealth:
    """Monitors structural health from the Hebbian service.

    Reads :8849/conservation and :8849/status endpoints.
    Gracefully degrades when services are unavailable.
    """

    def __init__(self, hebbian_host: str = "localhost", hebbian_port: int = 8849,
                 timeout: float = 3.0):
        self.host = hebbian_host
        self.port = hebbian_port
        self.timeout = timeout
        self._history: deque = deque(maxlen=1000)
        self._last: Optional[StructuralSnapshot] = None
        self._lock = threading.Lock()

    def _base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _fetch_json(self, path: str) -> Optional[dict]:
        """Fetch JSON from a service endpoint. Returns None on failure."""
        url = f"{self._base_url()}{path}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError,
                ConnectionRefusedError, TimeoutError, OSError, json.JSONDecodeError):
            return None

    def _classify_status(self, deviation: float, sigma: float) -> str:
        """Classify conservation status by deviation magnitude."""
        if sigma <= 0:
            return ConservationStatus.GREEN
        ratio = abs(deviation) / sigma
        if ratio < 1.0:
            return ConservationStatus.GREEN
        elif ratio < 2.0:
            return ConservationStatus.YELLOW
        else:
            return ConservationStatus.RED

    def collect(self) -> StructuralSnapshot:
        """Collect a structural health snapshot from the Hebbian service."""
        now = time.time()

        # Fetch conservation and status in parallel would be nice, but sequential is fine
        conservation = self._fetch_json("/conservation")
        status = self._fetch_json("/status")

        if conservation is None and status is None:
            snap = StructuralSnapshot(
                timestamp=now,
                hebbian_service_reachable=False,
                error="Hebbian service unreachable",
            )
            self._record(snap)
            return snap

        # Extract conservation data
        gamma = 0.0
        H = 0.0
        gamma_plus_H = 0.0
        predicted = 0.0
        deviation = 0.0
        sigma = 0.0
        conserved = True
        correction_applied = False

        if conservation is not None:
            cons_data = conservation.get("conservation", conservation)
            gamma = cons_data.get("gamma", 0.0)
            H = cons_data.get("H", 0.0)
            gamma_plus_H = cons_data.get("sum", cons_data.get("gamma_plus_H", 0.0))
            predicted = cons_data.get("predicted", 0.0)
            deviation = cons_data.get("deviation", 0.0)
            sigma = cons_data.get("sigma", 0.0)
            conserved = cons_data.get("conserved", True)
            correction_applied = cons_data.get("correction_applied", False)

        # Extract status data
        room_count = 0
        flow_events = 0
        kernel_updates = 0
        compliance_rate = 1.0
        auto_calibrated = False

        if status is not None:
            room_count = status.get("rooms", 0)
            flow_events = status.get("flow_events", 0)
            kernel_updates = status.get("kernel_updates", 0)
            compliance_rate = status.get("compliance_rate", 1.0)
            if isinstance(compliance_rate, str):
                compliance_rate = float(compliance_rate.rstrip("%")) / 100.0
            auto_calibrated = status.get("auto_calibrated", False)

        status_str = self._classify_status(deviation, sigma)

        snap = StructuralSnapshot(
            gamma=gamma,
            H=H,
            gamma_plus_H=gamma_plus_H,
            predicted=predicted,
            deviation=deviation,
            sigma=sigma,
            conserved=conserved,
            compliance_rate=compliance_rate,
            room_count=room_count,
            flow_events=flow_events,
            kernel_updates=kernel_updates,
            correction_applied=correction_applied,
            auto_calibrated=auto_calibrated,
            status=status_str,
            timestamp=now,
            hebbian_service_reachable=True,
        )
        self._record(snap)
        return snap

    def _record(self, snap: StructuralSnapshot):
        with self._lock:
            self._history.append(snap)
            self._last = snap

    def latest(self) -> Optional[StructuralSnapshot]:
        with self._lock:
            return self._last

    def history(self, n: int = 100) -> List[StructuralSnapshot]:
        with self._lock:
            return list(self._history)[-n:]

    def summary(self) -> Dict[str, Any]:
        snap = self.latest()
        if snap is None:
            return {"status": "no_data", "hebbian_service_reachable": False}
        return {
            "status": snap.status,
            "hebbian_service_reachable": snap.hebbian_service_reachable,
            "gamma_plus_H": round(snap.gamma_plus_H, 4),
            "predicted": round(snap.predicted, 4),
            "deviation": round(snap.deviation, 4),
            "sigma": round(snap.sigma, 4),
            "compliance_rate": round(snap.compliance_rate, 4),
            "room_count": snap.room_count,
            "flow_events": snap.flow_events,
            "kernel_updates": snap.kernel_updates,
            "conserved": snap.conserved,
            "auto_calibrated": snap.auto_calibrated,
            "timestamp": snap.timestamp,
        }


# ---------------------------------------------------------------------------
# 2. BehavioralHealth — model tier accuracy tracking
# ---------------------------------------------------------------------------

@dataclass
class ModelRecord:
    """Track accuracy for a single model over time."""
    model_name: str
    tier: int  # 1, 2, or 3
    provider: str
    total_queries: int = 0
    correct: int = 0
    recent_accuracy: float = 0.0
    last_seen: float = 0.0
    available: bool = True


class BehavioralHealth:
    """Tracks model tier distribution and accuracy over time.

    Measures:
    - Tier utilization balance (are we over-relying on one tier?)
    - Accuracy drift per model (is a model degrading?)
    - Model availability (can we reach each provider?)
    """

    # Tier boundaries from Study 50
    TIER_DEFINITIONS = {
        1: {"name": "direct", "description": "100% bare, 100% scaffolded"},
        2: {"name": "scaffolded", "description": "0-50% bare, 25-100% scaffolded"},
        3: {"name": "incompetent", "description": "0% both conditions"},
    }

    # Known models from Study 50
    KNOWN_MODELS = {
        "Seed-2.0-mini": {"tier": 1, "provider": "deepinfra"},
        "Seed-2.0-code": {"tier": 1, "provider": "deepinfra"},
        "gemma3:1b": {"tier": 1, "provider": "ollama"},
        "llama3.2:1b": {"tier": 2, "provider": "ollama"},
        "phi4-mini": {"tier": 2, "provider": "ollama"},
        "Qwen3-235B": {"tier": 2, "provider": "deepinfra"},
        "Hermes-70B": {"tier": 2, "provider": "deepinfra"},
        "Hermes-405B": {"tier": 2, "provider": "deepinfra"},
        "qwen2.5-coder:1.5b": {"tier": 2, "provider": "ollama"},
        "Qwen3.6-35B": {"tier": 3, "provider": "deepinfra"},
        "qwen3:4b": {"tier": 3, "provider": "ollama"},
        "qwen3:0.6b": {"tier": 3, "provider": "ollama"},
    }

    def __init__(self):
        self._models: Dict[str, ModelRecord] = {}
        self._accuracy_history: Dict[str, deque] = {}  # model → deque of (timestamp, accuracy)
        self._lock = threading.Lock()
        self._initialize_known_models()

    def _initialize_known_models(self):
        for name, info in self.KNOWN_MODELS.items():
            self._models[name] = ModelRecord(
                model_name=name,
                tier=info["tier"],
                provider=info["provider"],
            )
            self._accuracy_history[name] = deque(maxlen=500)

    def record_query(self, model_name: str, correct: bool,
                     tier: Optional[int] = None,
                     provider: Optional[str] = None):
        """Record a query result for a model."""
        with self._lock:
            if model_name not in self._models:
                self._models[model_name] = ModelRecord(
                    model_name=model_name,
                    tier=tier or 2,
                    provider=provider or "unknown",
                )
                self._accuracy_history[model_name] = deque(maxlen=500)

            rec = self._models[model_name]
            if tier is not None:
                rec.tier = tier
            if provider is not None:
                rec.provider = provider

            rec.total_queries += 1
            if correct:
                rec.correct += 1
            rec.last_seen = time.time()

            # Rolling accuracy (last 50 queries)
            self._accuracy_history[model_name].append((time.time(), 1.0 if correct else 0.0))
            recent = list(self._accuracy_history[model_name])[-50:]
            rec.recent_accuracy = sum(a for _, a in recent) / len(recent) if recent else 0.0

    def mark_availability(self, model_name: str, available: bool):
        """Mark a model as available or unavailable."""
        with self._lock:
            if model_name in self._models:
                self._models[model_name].available = available

    def get_model(self, model_name: str) -> Optional[ModelRecord]:
        with self._lock:
            return self._models.get(model_name)

    def tier_distribution(self) -> Dict[int, Dict[str, Any]]:
        """Get utilization statistics per tier."""
        with self._lock:
            tiers: Dict[int, Dict[str, Any]] = {}
            for tier_id in [1, 2, 3]:
                models_in_tier = [
                    m for m in self._models.values() if m.tier == tier_id
                ]
                total_queries = sum(m.total_queries for m in models_in_tier)
                total_correct = sum(m.correct for m in models_in_tier)
                n_models = len(models_in_tier)
                available = sum(1 for m in models_in_tier if m.available)

                tiers[tier_id] = {
                    "name": self.TIER_DEFINITIONS[tier_id]["name"],
                    "n_models": n_models,
                    "available": available,
                    "total_queries": total_queries,
                    "total_correct": total_correct,
                    "overall_accuracy": round(total_correct / total_queries, 4) if total_queries > 0 else 0.0,
                    "models": [m.model_name for m in models_in_tier],
                }
            return tiers

    def tier_utilization_balance(self) -> float:
        """Measure how balanced tier utilization is (0-1, 1=perfectly balanced).

        Uses entropy of query distribution across tiers.
        Maximum entropy = log(3) for 3 tiers.
        """
        with self._lock:
            tier_counts = {1: 0, 2: 0, 3: 0}
            for m in self._models.values():
                tier_counts[m.tier] += m.total_queries

            total = sum(tier_counts.values())
            if total == 0:
                return 1.0

            probs = [c / total for c in tier_counts.values() if c > 0]
            if not probs:
                return 1.0

            entropy = -sum(p * np.log(p) for p in probs)
            max_entropy = np.log(3)
            return float(entropy / max_entropy)

    def accuracy_drift(self, model_name: str, window: int = 50) -> Optional[float]:
        """Detect accuracy drift for a model.

        Compares recent accuracy to historical. Returns the drift magnitude
        (negative = degrading, positive = improving, None = insufficient data).
        """
        with self._lock:
            history = self._accuracy_history.get(model_name)
            if history is None or len(history) < window:
                return None

        hist = list(history)
        half = len(hist) // 2
        old_half = hist[:half]
        new_half = hist[half:]

        old_acc = sum(a for _, a in old_half) / len(old_half)
        new_acc = sum(a for _, a in new_half) / len(new_half)
        return new_acc - old_acc

    def models_with_drift(self, threshold: float = 0.15) -> List[Dict[str, Any]]:
        """Find models with significant accuracy drift."""
        results = []
        with self._lock:
            model_names = list(self._models.keys())

        for name in model_names:
            drift = self.accuracy_drift(name)
            if drift is not None and abs(drift) > threshold:
                rec = self._models.get(name)
                if rec:
                    results.append({
                        "model": name,
                        "tier": rec.tier,
                        "drift": round(drift, 4),
                        "direction": "degrading" if drift < 0 else "improving",
                        "current_accuracy": round(rec.recent_accuracy, 4),
                    })
        return sorted(results, key=lambda x: abs(x["drift"]), reverse=True)

    def provider_availability(self) -> Dict[str, Dict[str, Any]]:
        """Check model availability grouped by provider."""
        with self._lock:
            providers: Dict[str, Dict[str, Any]] = {}
            for m in self._models.values():
                if m.provider not in providers:
                    providers[m.provider] = {"models": [], "available": 0, "total": 0}
                providers[m.provider]["models"].append(m.model_name)
                providers[m.provider]["total"] += 1
                if m.available:
                    providers[m.provider]["available"] += 1
            return providers

    def summary(self) -> Dict[str, Any]:
        tiers = self.tier_distribution()
        return {
            "total_models": len(self._models),
            "tier_utilization_balance": round(self.tier_utilization_balance(), 4),
            "tiers": tiers,
            "drift_alerts": self.models_with_drift(),
            "provider_availability": self.provider_availability(),
        }


# ---------------------------------------------------------------------------
# 3. FleetHealthReport — unified health data
# ---------------------------------------------------------------------------

@dataclass
class FleetHealthReport:
    structural: Dict[str, Any]
    behavioral: Dict[str, Any]
    overall_score: float
    recommendations: List[str]
    timestamp: float = 0.0
    diagnostics: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 4),
            "structural": self.structural,
            "behavioral": self.behavioral,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "diagnostics": self.diagnostics,
        }


# ---------------------------------------------------------------------------
# 4. ConservationMonitor — trend detection over time
# ---------------------------------------------------------------------------

@dataclass
class ConservationTrend:
    """Analysis of conservation law over time."""
    direction: str       # "stable", "degrading", "improving"
    slope: float         # linear regression slope of deviation
    samples: int         # number of data points
    latest_deviation: float
    latest_status: str
    alert: bool          # True if degradation detected
    alert_message: str


class ConservationMonitor:
    """Watches γ+H over time and detects degradation trends.

    Uses linear regression on recent deviation samples to detect
    whether the conservation law is systematically drifting.
    """

    def __init__(self, alert_threshold: float = 0.002,
                 min_samples: int = 10, window: int = 100):
        self.alert_threshold = alert_threshold  # slope threshold for alert
        self.min_samples = min_samples
        self.window = window
        self._deviations: deque = deque(maxlen=window)
        self._timestamps: deque = deque(maxlen=window)
        self._lock = threading.Lock()

    def record(self, deviation: float, timestamp: Optional[float] = None):
        """Record a deviation observation."""
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            self._deviations.append(deviation)
            self._timestamps.append(ts)

    def analyze(self) -> ConservationTrend:
        """Analyze the current conservation trend."""
        with self._lock:
            devs = list(self._deviations)
            ts = list(self._timestamps)

        if len(devs) < self.min_samples:
            return ConservationTrend(
                direction="insufficient_data",
                slope=0.0,
                samples=len(devs),
                latest_deviation=devs[-1] if devs else 0.0,
                latest_status="UNKNOWN",
                alert=False,
                alert_message=f"Need {self.min_samples - len(devs)} more samples",
            )

        # Linear regression on deviations
        ts_arr = np.array(ts)
        devs_arr = np.array(devs)

        # Normalize timestamps to seconds from start
        ts_norm = ts_arr - ts_arr[0]
        if ts_norm[-1] == 0:
            ts_norm = np.arange(len(ts_norm), dtype=np.float64)

        # Simple linear regression
        n = len(ts_norm)
        slope = float(
            (n * np.sum(ts_norm * devs_arr) - np.sum(ts_norm) * np.sum(devs_arr))
            / (n * np.sum(ts_norm ** 2) - np.sum(ts_norm) ** 2 + 1e-15)
        )

        latest_dev = devs[-1]
        latest_status = (
            ConservationStatus.RED if abs(latest_dev) > 0.1
            else ConservationStatus.YELLOW if abs(latest_dev) > 0.05
            else ConservationStatus.GREEN
        )

        # Determine direction
        if abs(slope) < self.alert_threshold:
            direction = "stable"
        elif slope > 0:
            direction = "degrading"
        else:
            direction = "improving"

        # Alert if slope is consistently positive (degrading)
        alert = slope > self.alert_threshold and len(devs) >= self.min_samples
        alert_msg = ""
        if alert:
            alert_msg = (
                f"Conservation law degrading: deviation slope = {slope:.6f}/s "
                f"(threshold: {self.alert_threshold}). Latest deviation: {latest_dev:.4f}"
            )

        return ConservationTrend(
            direction=direction,
            slope=round(slope, 6),
            samples=len(devs),
            latest_deviation=round(latest_dev, 4),
            latest_status=latest_status,
            alert=alert,
            alert_message=alert_msg,
        )

    def summary(self) -> Dict[str, Any]:
        trend = self.analyze()
        return {
            "direction": trend.direction,
            "slope": trend.slope,
            "samples": trend.samples,
            "latest_deviation": trend.latest_deviation,
            "latest_status": trend.latest_status,
            "alert": trend.alert,
            "alert_message": trend.alert_message,
        }


# ---------------------------------------------------------------------------
# 5. DiagnosticsRunner
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticResult:
    name: str
    passed: bool
    message: str
    latency_ms: float = 0.0


class DiagnosticsRunner:
    """Runs fleet health diagnostics with graceful degradation."""

    def __init__(self, hebbian_host: str = "localhost", hebbian_port: int = 8849,
                 deepinfra_timeout: float = 5.0,
                 ollama_timeout: float = 3.0):
        self.hebbian_host = hebbian_host
        self.hebbian_port = hebbian_port
        self.deepinfra_timeout = deepinfra_timeout
        self.ollama_timeout = ollama_timeout

    def _ping_url(self, url: str, timeout: float) -> Tuple[bool, float, str]:
        """Ping a URL, return (success, latency_ms, message)."""
        start = time.monotonic()
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.monotonic() - start) * 1000
                return True, latency, f"OK ({resp.status})"
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return False, latency, str(e)[:100]

    def check_hebbian_service(self) -> DiagnosticResult:
        ok, lat, msg = self._ping_url(
            f"http://{self.hebbian_host}:{self.hebbian_port}/status",
            timeout=3.0,
        )
        return DiagnosticResult(
            name="hebbian_service",
            passed=ok,
            message=msg if ok else f"Unreachable: {msg}",
            latency_ms=round(lat, 1),
        )

    def check_conservation_compliance(self, structural: StructuralHealth) -> DiagnosticResult:
        snap = structural.latest()
        if snap is None:
            return DiagnosticResult(
                name="conservation_compliance",
                passed=False,
                message="No structural data available",
            )
        if not snap.hebbian_service_reachable:
            return DiagnosticResult(
                name="conservation_compliance",
                passed=False,
                message="Hebbian service unreachable — cannot verify",
            )
        passed = snap.status in (ConservationStatus.GREEN, ConservationStatus.YELLOW)
        return DiagnosticResult(
            name="conservation_compliance",
            passed=passed,
            message=f"Status: {snap.status}, deviation: {snap.deviation:.4f}",
        )

    def check_deepinfra(self) -> DiagnosticResult:
        ok, lat, msg = self._ping_url(
            "https://api.deepinfra.com/v1/openai/models",
            timeout=self.deepinfra_timeout,
        )
        return DiagnosticResult(
            name="deepinfra_api",
            passed=ok,
            message=msg if ok else f"Unreachable: {msg}",
            latency_ms=round(lat, 1),
        )

    def check_ollama(self) -> DiagnosticResult:
        ok, lat, msg = self._ping_url(
            "http://localhost:11434/api/tags",
            timeout=self.ollama_timeout,
        )
        return DiagnosticResult(
            name="ollama_api",
            passed=ok,
            message=msg if ok else f"Unreachable: {msg}",
            latency_ms=round(lat, 1),
        )

    def run_all(self, structural: StructuralHealth) -> Dict[str, Any]:
        """Run all diagnostics and return a structured result."""
        checks = [
            self.check_hebbian_service(),
            self.check_conservation_compliance(structural),
            self.check_deepinfra(),
            self.check_ollama(),
        ]

        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        all_passed = passed == total

        return {
            "overall": "PASS" if all_passed else "FAIL",
            "passed": passed,
            "total": total,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                }
                for c in checks
            ],
            "timestamp": time.time(),
        }


# ---------------------------------------------------------------------------
# 6. HealthEndpoint — the main orchestrator
# ---------------------------------------------------------------------------

class HealthEndpoint:
    """Unified health endpoint combining structural + behavioral health.

    HTTP Endpoints:
        GET  /fleet/health              — full FleetHealthReport
        GET  /fleet/health/structural   — structural only
        GET  /fleet/health/behavioral   — behavioral only
        POST /fleet/health/check        — run diagnostics, return pass/fail
    """

    def __init__(self, port: int = 8851,
                 hebbian_host: str = "localhost",
                 hebbian_port: int = 8849):
        self.port = port
        self.structural = StructuralHealth(hebbian_host, hebbian_port)
        self.behavioral = BehavioralHealth()
        self.conservation_monitor = ConservationMonitor()
        self.diagnostics = DiagnosticsRunner(hebbian_host, hebbian_port)
        self._running = False
        self._http_server: Optional[HTTPServer] = None
        self._last_report: Optional[FleetHealthReport] = None
        self._lock = threading.Lock()

    def _compute_overall_score(self, structural: Dict[str, Any],
                                behavioral: Dict[str, Any]) -> float:
        """Compute weighted overall health score (0-1).

        Weights:
        - Structural compliance: 40%
        - Conservation status: 25%
        - Tier utilization balance: 20%
        - Model accuracy: 15%
        """
        score = 0.0

        # Structural compliance (0-1)
        compliance = structural.get("compliance_rate", 1.0)
        if isinstance(compliance, str):
            compliance = float(compliance.rstrip("%")) / 100.0
        score += 0.40 * compliance

        # Conservation status (0-1)
        status = structural.get("status", ConservationStatus.GREEN)
        if status == ConservationStatus.GREEN:
            cons_score = 1.0
        elif status == ConservationStatus.YELLOW:
            cons_score = 0.6
        else:
            cons_score = 0.2
        score += 0.25 * cons_score

        # Tier utilization balance (0-1)
        tier_balance = behavioral.get("tier_utilization_balance", 1.0)
        score += 0.20 * tier_balance

        # Model accuracy (average across tiers)
        tiers = behavioral.get("tiers", {})
        accuracies = [t.get("overall_accuracy", 0.0) for t in tiers.values() if t.get("total_queries", 0) > 0]
        avg_accuracy = np.mean(accuracies) if accuracies else 1.0
        score += 0.15 * avg_accuracy

        return float(np.clip(score, 0.0, 1.0))

    def _generate_recommendations(self, structural: Dict[str, Any],
                                   behavioral: Dict[str, Any],
                                   trend: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on health data."""
        recs = []

        # Structural recommendations
        if not structural.get("hebbian_service_reachable", False):
            recs.append("⚠️ Hebbian service unreachable — check fleet_hebbian_service.py on :8849")

        status = structural.get("status", ConservationStatus.GREEN)
        if status == ConservationStatus.RED:
            recs.append("🔴 Conservation law violated (>2σ) — investigate kernel correction rate")
        elif status == ConservationStatus.YELLOW:
            recs.append("🟡 Conservation deviation elevated (1-2σ) — monitor for trend")

        compliance = structural.get("compliance_rate", 1.0)
        if isinstance(compliance, str):
            compliance = float(compliance.rstrip("%")) / 100.0
        if compliance < 0.8:
            recs.append(f"⚠️ Compliance rate low ({compliance:.0%}) — kernel may need recalibration")

        if not structural.get("auto_calibrated", False):
            recs.append("⚙️ Kernel not yet auto-calibrated — run POST /calibrate on :8849")

        # Behavioral recommendations
        drift_alerts = behavioral.get("drift_alerts", [])
        for alert in drift_alerts:
            recs.append(
                f"📉 {alert['model']} (Tier {alert['tier']}): accuracy {alert['direction']} "
                f"(drift={alert['drift']:+.2f}, accuracy={alert['current_accuracy']:.0%})"
            )

        tier_balance = behavioral.get("tier_utilization_balance", 1.0)
        if tier_balance < 0.5:
            recs.append(
                f"⚖️ Tier utilization imbalanced (balance={tier_balance:.2f}) — "
                f"consider redistributing queries across tiers"
            )

        provider_avail = behavioral.get("provider_availability", {})
        for provider, info in provider_avail.items():
            if info.get("available", 0) < info.get("total", 0):
                recs.append(
                    f"🔌 {provider}: {info['available']}/{info['total']} models available"
                )

        # Conservation trend recommendations
        if trend.get("alert", False):
            recs.append(f"🚨 Conservation trend alert: {trend.get('alert_message', '')}")

        if not recs:
            recs.append("✅ Fleet health nominal — all systems operational")

        return recs

    def build_report(self) -> FleetHealthReport:
        """Build a full FleetHealthReport."""
        # Collect structural health
        snap = self.structural.collect()
        structural = self.structural.summary()

        # Update conservation monitor
        self.conservation_monitor.record(snap.deviation, snap.timestamp)
        trend = self.conservation_monitor.summary()

        # Get behavioral health
        behavioral = self.behavioral.summary()

        # Compute overall score
        overall = self._compute_overall_score(structural, behavioral)

        # Generate recommendations
        recs = self._generate_recommendations(structural, behavioral, trend)

        report = FleetHealthReport(
            structural=structural,
            behavioral=behavioral,
            overall_score=overall,
            recommendations=recs,
            diagnostics={"conservation_trend": trend},
        )

        with self._lock:
            self._last_report = report

        return report

    def start(self, block: bool = True):
        """Start the HTTP API server."""
        self._running = True
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2, default=str).encode())

            def _read_body(self):
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    return json.loads(self.rfile.read(length))
                return {}

            def do_GET(self):
                if self.path == "/fleet/health":
                    report = endpoint.build_report()
                    self._json(report.to_dict())

                elif self.path == "/fleet/health/structural":
                    snap = endpoint.structural.collect()
                    self._json(endpoint.structural.summary())

                elif self.path == "/fleet/health/behavioral":
                    self._json(endpoint.behavioral.summary())

                elif self.path == "/fleet/health/trend":
                    self._json(endpoint.conservation_monitor.summary())

                elif self.path == "/fleet/health/status":
                    # Lightweight status without full report
                    snap = endpoint.structural.latest()
                    with endpoint._lock:
                        report = endpoint._last_report
                    self._json({
                        "running": endpoint._running,
                        "last_report_time": report.timestamp if report else None,
                        "overall_score": report.overall_score if report else None,
                        "structural_status": snap.status if snap else None,
                        "hebbian_reachable": snap.hebbian_service_reachable if snap else False,
                    })

                else:
                    self._json({"error": f"unknown endpoint: {self.path}"}, 404)

            def do_POST(self):
                if self.path == "/fleet/health/check":
                    # Run diagnostics
                    diag = endpoint.diagnostics.run_all(endpoint.structural)
                    # Also collect a fresh report
                    report = endpoint.build_report()
                    diag["health_report"] = report.to_dict()
                    self._json(diag)

                elif self.path == "/fleet/health/record":
                    # Record a behavioral observation
                    body = self._read_body()
                    model = body.get("model")
                    if not model:
                        self._json({"error": "missing 'model' field"}, 400)
                        return
                    endpoint.behavioral.record_query(
                        model_name=model,
                        correct=body.get("correct", True),
                        tier=body.get("tier"),
                        provider=body.get("provider"),
                    )
                    self._json({"recorded": True, "model": model})

                elif self.path == "/fleet/health/availability":
                    # Update model availability
                    body = self._read_body()
                    model = body.get("model")
                    available = body.get("available", True)
                    if not model:
                        self._json({"error": "missing 'model' field"}, 400)
                        return
                    endpoint.behavioral.mark_availability(model, available)
                    self._json({"updated": True, "model": model, "available": available})

                else:
                    self._json({"error": f"unknown endpoint: {self.path}"}, 404)

            def log_message(self, format, *args):
                pass  # suppress request logging

        class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._http_server = ThreadedHTTPServer(("0.0.0.0", self.port), Handler)
        print(f"⚕️  Fleet Unified Health Endpoint on :{self.port}")
        print(f"   Endpoints: /fleet/health /fleet/health/structural /fleet/health/behavioral")
        print(f"   POST: /fleet/health/check /fleet/health/record /fleet/health/availability")

        if block:
            try:
                self._http_server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            t = threading.Thread(target=self._http_server.serve_forever, daemon=True)
            t.start()

    def stop(self):
        self._running = False
        if self._http_server:
            self._http_server.shutdown()
        print("⚕️  Fleet Unified Health Endpoint stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fleet Unified Health Endpoint")
    parser.add_argument("--port", type=int, default=8851)
    parser.add_argument("--hebbian-port", type=int, default=8849)
    parser.add_argument("--hebbian-host", type=str, default="localhost")
    args = parser.parse_args()

    endpoint = HealthEndpoint(
        port=args.port,
        hebbian_host=args.hebbian_host,
        hebbian_port=args.hebbian_port,
    )
    endpoint.start(block=True)


if __name__ == "__main__":
    main()
