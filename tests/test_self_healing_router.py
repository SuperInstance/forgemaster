#!/usr/bin/env python3
"""
Tests for SelfHealingMixin wired into fleet_router_api.

Study 63 integration: intent drift + answer consensus → quarantine/restore.
"""

import sys
import os
import time
import math
import pytest

# Ensure workspace on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_router_api import (
    SelfHealingMixin,
    QuarantineConfig,
    ExpertHealthRecord,
    ModelRegistry,
    ModelTierEnum,
    create_app,
    _cosine_sim,
)
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_intent(seed: float = 1.0) -> list:
    """Generate a 9D intent vector from a seed."""
    return [seed * (i + 1) / 9.0 for i in range(9)]


def drifted_intent(base: list, drift: float = 0.5) -> list:
    """Shift a base intent vector by drift in a perpendicular direction."""
    # Use alternating signs to reduce cosine similarity
    signs = [1 if i % 2 == 0 else -1 for i in range(9)]
    return [v + drift * signs[i] * (i + 1) for i, v in enumerate(base)]


def register_experts(registry: ModelRegistry, n: int = 8) -> list:
    """Register n tier-1 experts, return their IDs."""
    ids = []
    for i in range(n):
        eid = f"expert_{i}"
        registry.register(eid, ModelTierEnum.TIER_1_DIRECT)
        ids.append(eid)
    return ids


# ---------------------------------------------------------------------------
# 1. Cosine similarity utility
# ---------------------------------------------------------------------------

class TestCosineSim:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        assert _cosine_sim(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        assert _cosine_sim(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self):
        v = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        assert _cosine_sim(v, [-x for x in v]) == pytest.approx(-1.0, abs=1e-6)

    def test_zero_vector(self):
        assert _cosine_sim([0.0] * 9, [1.0] * 9) == 0.0

    def test_short_vectors_padded(self):
        # cosine_sim doesn't pad — just uses what's given
        result = _cosine_sim([1.0, 2.0], [1.0, 2.0])
        assert result == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 2. SelfHealingMixin — basic health checks
# ---------------------------------------------------------------------------

class TestCheckExpertHealth:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        self.healing = SelfHealingMixin(self.registry)

    def test_first_check_sets_baseline(self):
        intent = make_intent(1.0)
        result = self.healing.check_expert_health("expert_0", intent, 42.0)
        assert result["action"] == "healthy"
        rec = self.healing._get_record("expert_0")
        assert rec.baseline_set is True
        assert rec.baseline_intent == intent

    def test_healthy_expert_stays_healthy(self):
        intent = make_intent(1.0)
        for _ in range(5):
            result = self.healing.check_expert_health("expert_0", intent, 42.0)
        assert result["action"] == "healthy"
        assert result["intent_flag"] is False
        assert result["answer_flag"] is False

    def test_intent_drift_flagged(self):
        base = make_intent(1.0)
        # Set baseline
        self.healing.check_expert_health("expert_0", base, 42.0)
        # Drift significantly
        drifted = drifted_intent(base, drift=10.0)
        result = self.healing.check_expert_health("expert_0", drifted, 42.0)
        assert result["intent_flag"] is True

    def test_answer_outlier_flagged(self):
        self.healing.check_expert_health("expert_0", make_intent(), 42.0)
        fleet = [10.0, 10.5, 9.8, 10.2, 10.1]
        result = self.healing.check_expert_health(
            "expert_0", make_intent(), 100.0, fleet_answers=fleet
        )
        assert result["answer_flag"] is True
        assert result["relative_error"] > 0.5

    def test_answer_within_consensus(self):
        fleet = [10.0, 10.5, 9.8, 10.2, 10.1]
        result = self.healing.check_expert_health(
            "expert_0", make_intent(), 10.0, fleet_answers=fleet
        )
        assert result["answer_flag"] is False


# ---------------------------------------------------------------------------
# 3. Quarantine logic
# ---------------------------------------------------------------------------

class TestQuarantine:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        self.healing = SelfHealingMixin(self.registry)

    def _trigger_fault(self, expert_id: str, fleet: list = None):
        """Force both signals to flag."""
        base = make_intent(1.0)
        self.healing.check_expert_health(expert_id, base, 10.0)
        drifted = drifted_intent(base, drift=50.0)
        fleet_answers = fleet or [10.0, 10.5, 9.8]
        return self.healing.check_expert_health(
            expert_id, drifted, 1000.0, fleet_answers=fleet_answers
        )

    def test_requires_two_consecutive_detections(self):
        # First detection: flagged but not quarantined
        r1 = self._trigger_fault("expert_0")
        assert r1["fault_detected"] is True
        assert r1["action"] == "healthy"  # first strike, not yet quarantined

        # Second detection: quarantine
        r2 = self._trigger_fault("expert_0")
        assert r2["action"] == "quarantined"

    def test_quarantine_marks_unavailable(self):
        self._trigger_fault("expert_0")
        self._trigger_fault("expert_0")
        entry = self.registry.get("expert_0")
        assert entry.available is False

    def test_quarantine_increments_count(self):
        self._trigger_fault("expert_0")
        self._trigger_fault("expert_0")
        rec = self.healing._get_record("expert_0")
        assert rec.quarantine_count == 1

    def test_single_detection_no_quarantine(self):
        r = self._trigger_fault("expert_0")
        assert r["action"] != "quarantined"
        rec = self.healing._get_record("expert_0")
        assert rec.quarantined is False


# ---------------------------------------------------------------------------
# 4. Fleet protection (min 4 active)
# ---------------------------------------------------------------------------

class TestFleetProtection:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 5)  # 5 experts, min_active=4
        config = QuarantineConfig(min_active_experts=4, consecutive_for_quarantine=1)
        self.healing = SelfHealingMixin(self.registry, config)
        # Initialize health records for all experts so fleet protection works
        for eid in self.ids:
            self.healing.check_expert_health(eid, make_intent(), 10.0)

    def _quarantine_one(self, expert_id: str):
        base = make_intent(1.0)
        self.healing.check_expert_health(expert_id, base, 10.0)
        drifted = drifted_intent(base, drift=50.0)
        self.healing.check_expert_health(
            expert_id, drifted, 1000.0, fleet_answers=[10.0, 10.5]
        )

    def test_cannot_quarantine_below_minimum(self):
        # Quarantine first expert (5→4 active in registry)
        self._quarantine_one("expert_0")
        assert not self.registry.get("expert_0").available
        # 4 available in registry
        avail = sum(1 for e in self.registry._models.values() if e.available)
        assert avail == 4

        # Try to quarantine second (would go to 3, below min)
        self._quarantine_one("expert_1")
        rec = self.healing._get_record("expert_1")
        assert rec.quarantined is False  # blocked by fleet protection

    def test_flagged_but_protected_action(self):
        self._quarantine_one("expert_0")
        base = make_intent(1.0)
        self.healing.check_expert_health("expert_1", base, 10.0)
        r = self.healing.check_expert_health(
            "expert_1", drifted_intent(base, 50.0), 1000.0,
            fleet_answers=[10.0, 10.5],
        )
        assert r["action"] == "flagged_but_protected"


# ---------------------------------------------------------------------------
# 5. Recovery protocol
# ---------------------------------------------------------------------------

class TestRecovery:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        config = QuarantineConfig(
            consecutive_for_quarantine=1,
            clean_for_restore=3,
            progressive_rounds=[3, 6, 0],  # short for testing
        )
        self.healing = SelfHealingMixin(self.registry, config)

    def _quarantine(self, expert_id: str):
        base = make_intent(1.0)
        self.healing.check_expert_health(expert_id, base, 10.0)
        self.healing.check_expert_health(
            expert_id, drifted_intent(base, 50.0), 1000.0,
            fleet_answers=[10.0, 10.5],
        )

    def test_auto_restore_after_clean_rounds(self):
        self._quarantine("expert_0")
        assert self.healing._get_record("expert_0").quarantined is True

        # 3 consecutive clean checks → auto-restore
        for _ in range(3):
            r = self.healing.check_expert_health("expert_0", make_intent(1.0), 10.0)
        assert r["action"] == "restored"

    def test_restore_resets_clean_counter(self):
        self._quarantine("expert_0")
        rec = self.healing._get_record("expert_0")
        assert rec.quarantined is True

        for _ in range(3):
            self.healing.check_expert_health("expert_0", make_intent(1.0), 10.0)

        rec = self.healing._get_record("expert_0")
        assert rec.quarantined is False
        assert rec.consecutive_clean == 0

    def test_manual_restore(self):
        self._quarantine("expert_0")
        result = self.healing.restore_expert("expert_0")
        assert result["status"] == "restored"
        assert self.healing._get_record("expert_0").quarantined is False

    def test_manual_restore_not_quarantined(self):
        result = self.healing.restore_expert("expert_0")
        assert result["status"] == "not_quarantined"

    def test_progressive_penalty(self):
        # First quarantine → 3 rounds
        self._quarantine("expert_0")
        assert self.healing._get_record("expert_0").quarantine_rounds_remaining == 3

        # Restore
        self.healing.restore_expert("expert_0")

        # Second quarantine → 6 rounds
        self._quarantine("expert_0")
        assert self.healing._get_record("expert_0").quarantine_rounds_remaining == 6

    def test_tick_recovery(self):
        self._quarantine("expert_0")
        rec = self.healing._get_record("expert_0")
        rounds = rec.quarantine_rounds_remaining

        results = self.healing.tick_recovery()
        rec = self.healing._get_record("expert_0")
        assert rec.quarantine_rounds_remaining == rounds - 1


# ---------------------------------------------------------------------------
# 6. Progressive quarantine (permanent on 3rd)
# ---------------------------------------------------------------------------

class TestProgressiveQuarantine:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        config = QuarantineConfig(
            consecutive_for_quarantine=1,
            clean_for_restore=3,
            progressive_rounds=[2, 4, 0],  # 0 = permanent
        )
        self.healing = SelfHealingMixin(self.registry, config)

    def _quarantine_and_restore(self, expert_id: str):
        base = make_intent(1.0)
        self.healing.check_expert_health(expert_id, base, 10.0)
        self.healing.check_expert_health(
            expert_id, drifted_intent(base, 50.0), 1000.0,
            fleet_answers=[10.0, 10.5],
        )
        self.healing.restore_expert(expert_id)

    def test_third_offense_permanent(self):
        self._quarantine_and_restore("expert_0")
        self._quarantine_and_restore("expert_0")
        # Third offense
        self._quarantine_and_restore("expert_0")  # this restores via manual
        # Now quarantine again (3rd actual quarantine)
        self._quarantine_and_restore("expert_0")
        self._quarantine_and_restore("expert_0")
        base = make_intent(1.0)
        self.healing.check_expert_health("expert_0", base, 10.0)
        self.healing.check_expert_health(
            "expert_0", drifted_intent(base, 50.0), 1000.0,
            fleet_answers=[10.0, 10.5],
        )
        rec = self.healing._get_record("expert_0")
        assert rec.quarantine_count >= 3
        assert rec.quarantine_rounds_remaining == 0  # permanent


# ---------------------------------------------------------------------------
# 7. Conservation-aware integration
# ---------------------------------------------------------------------------

class TestConservationAware:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        self.healing = SelfHealingMixin(self.registry)

    def test_low_compliance_requires_both_signals(self):
        self.healing.set_conservation_rate(0.5)  # Below 0.85

        base = make_intent(1.0)
        self.healing.check_expert_health("expert_0", base, 10.0)

        # Only intent drift (not answer)
        r = self.healing.check_expert_health(
            "expert_0", drifted_intent(base, 50.0), 10.0,
            fleet_answers=[10.0, 10.5],
        )
        # With low compliance, only one signal → NOT flagged
        assert r["conservation_elevated"] is True
        # intent_flag is True but answer_flag False → both_flagged=False
        # With low compliance, fault_detected requires both → False
        assert r["fault_detected"] is False

    def test_high_compliance_either_signal(self):
        self.healing.set_conservation_rate(0.95)

        base = make_intent(1.0)
        self.healing.check_expert_health("expert_0", base, 10.0)

        # Only intent drift
        r = self.healing.check_expert_health(
            "expert_0", drifted_intent(base, 50.0), 10.0,
            fleet_answers=[10.0, 10.5],
        )
        assert r["fault_detected"] is True


# ---------------------------------------------------------------------------
# 8. get_active_experts / get_quarantined_experts
# ---------------------------------------------------------------------------

class TestQueryMethods:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        config = QuarantineConfig(consecutive_for_quarantine=1)
        self.healing = SelfHealingMixin(self.registry, config)
        # Initialize all health records
        for eid in self.ids:
            self.healing.check_expert_health(eid, make_intent(), 10.0)

    def _quarantine(self, eid):
        base = make_intent(1.0)
        self.healing.check_expert_health(eid, base, 10.0)
        self.healing.check_expert_health(
            eid, drifted_intent(base, 50.0), 1000.0, fleet_answers=[10.0, 10.5]
        )

    def test_active_excludes_quarantined(self):
        self._quarantine("expert_0")
        active = self.healing.get_active_experts()
        assert "expert_0" not in active
        assert len(active) == 7

    def test_quarantined_list(self):
        self._quarantine("expert_0")
        q = self.healing.get_quarantined_experts()
        assert len(q) == 1
        assert q[0]["expert_id"] == "expert_0"

    def test_get_status(self):
        self._quarantine("expert_0")
        status = self.healing.get_status()
        assert status["quarantined_count"] == 1
        assert status["active_count"] == 7
        assert "per_expert" in status
        assert "recent_detections" in status


# ---------------------------------------------------------------------------
# 9. Detection history
# ---------------------------------------------------------------------------

class TestDetectionHistory:
    def setup_method(self):
        self.registry = ModelRegistry()
        self.ids = register_experts(self.registry, 8)
        self.healing = SelfHealingMixin(self.registry)

    def test_history_records_each_check(self):
        self.healing.check_expert_health("expert_0", make_intent(), 10.0)
        self.healing.check_expert_health("expert_0", make_intent(), 11.0)
        hist = self.healing.get_detection_history("expert_0")
        assert len(hist) == 2

    def test_global_history(self):
        self.healing.check_expert_health("expert_0", make_intent(), 10.0)
        self.healing.check_expert_health("expert_1", make_intent(), 11.0)
        hist = self.healing.get_detection_history()
        assert len(hist) == 2

    def test_history_limit(self):
        for i in range(10):
            self.healing.check_expert_health("expert_0", make_intent(), float(i))
        hist = self.healing.get_detection_history("expert_0", limit=5)
        assert len(hist) == 5


# ---------------------------------------------------------------------------
# 10. FastAPI endpoint integration
# ---------------------------------------------------------------------------

class TestEndpoints:
    def setup_method(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.healing = self.app.state.healing
        self.registry = self.app.state.registry
        # Register test experts
        for i in range(8):
            self.registry.register(f"test_expert_{i}", ModelTierEnum.TIER_1_DIRECT)

    def test_healing_status_endpoint(self):
        resp = self.client.get("/fleet/healing/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_count" in data
        assert "quarantined_count" in data

    def test_report_endpoint_healthy(self):
        resp = self.client.post("/fleet/healing/report", json={
            "expert_id": "test_expert_0",
            "intent_vector": make_intent(),
            "answer": 42.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "healthy"

    def test_report_endpoint_triggers_quarantine(self):
        config = QuarantineConfig(consecutive_for_quarantine=1)
        self.healing.config = config

        # Set baseline
        self.client.post("/fleet/healing/report", json={
            "expert_id": "test_expert_0",
            "intent_vector": make_intent(1.0),
            "answer": 10.0,
        })
        # Trigger fault
        resp = self.client.post("/fleet/healing/report", json={
            "expert_id": "test_expert_0",
            "intent_vector": drifted_intent(make_intent(1.0), 50.0),
            "answer": 1000.0,
            "fleet_answers": [10.0, 10.5, 9.8],
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["action"] == "quarantined"

    def test_restore_endpoint(self):
        config = QuarantineConfig(consecutive_for_quarantine=1)
        self.healing.config = config

        # Quarantine first
        self.client.post("/fleet/healing/report", json={
            "expert_id": "test_expert_0",
            "intent_vector": make_intent(1.0),
            "answer": 10.0,
        })
        self.client.post("/fleet/healing/report", json={
            "expert_id": "test_expert_0",
            "intent_vector": drifted_intent(make_intent(1.0), 50.0),
            "answer": 1000.0,
            "fleet_answers": [10.0, 10.5],
        })

        # Restore
        resp = self.client.post("/fleet/healing/restore", json={
            "expert_id": "test_expert_0",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "restored"

    def test_restore_not_quarantined(self):
        resp = self.client.post("/fleet/healing/restore", json={
            "expert_id": "test_expert_0",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_quarantined"

    def test_report_with_fleet_answers(self):
        resp = self.client.post("/fleet/healing/report", json={
            "expert_id": "test_expert_0",
            "intent_vector": make_intent(),
            "answer": 10.0,
            "fleet_answers": [10.0, 10.2, 9.8, 10.1],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer_flag"] is False


# ---------------------------------------------------------------------------
# 11. Existing tests still pass
# ---------------------------------------------------------------------------

class TestExistingEndpointsStillWork:
    def setup_method(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200

    def test_models_endpoint(self):
        resp = self.client.get("/models")
        assert resp.status_code == 200
        assert "models" in resp.json()

    def test_route_endpoint(self):
        resp = self.client.post("/route", json={
            "task_type": "mobius",
            "params": {"n": 6},
        })
        assert resp.status_code == 200

    def test_stats_endpoint(self):
        resp = self.client.get("/stats")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
