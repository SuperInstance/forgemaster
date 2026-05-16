#!/usr/bin/env python3
"""Tests for ConservationReweightMixin (Study 64 findings).

Covers:
- Conservation gap computation and recovery rate scaling
- Expert reweighting based on conservation contribution
- Hebbian disabling under fleet stress
- Reweight-first / quarantine-second flow in SelfHealingMixin
- Exponential scaling of recovery rate with gap magnitude
- Weight bounds (never zero, never exceeds max)
- 5-round reweighting before quarantine escalation
- API endpoint functionality
"""

import sys
import os
import time
import pytest

# Ensure workspace is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_router_api import (
    ConservationReweightMixin,
    SelfHealingMixin,
    ModelRegistry,
    ModelTierEnum,
    QuarantineConfig,
    ReweightRecord,
    create_app,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry():
    """Create a registry with test models."""
    reg = ModelRegistry()
    for i in range(6):
        mid = f"expert-{i}"
        tier = ModelTierEnum.TIER_1_DIRECT if i < 3 else ModelTierEnum.TIER_2_SCAFFOLDED
        reg.register(mid, tier)
    return reg


@pytest.fixture
def reweight_mixin(registry):
    """Create a ConservationReweightMixin with test registry."""
    return ConservationReweightMixin(registry)


@pytest.fixture
def healing_with_reweight(registry):
    """Create SelfHealingMixin wired to ConservationReweightMixin."""
    reweight = ConservationReweightMixin(registry)
    healing = SelfHealingMixin(registry, reweight_mixin=reweight)
    reweight.healing_mixin = healing
    return healing, reweight


@pytest.fixture
def app():
    """Create test FastAPI app."""
    from fastapi.testclient import TestClient
    application = create_app()
    return TestClient(application)


# ===========================================================================
# 1. Conservation Gap & Recovery Rate
# ===========================================================================

class TestConservationGap:
    def test_healthy_fleet_zero_gap(self, reweight_mixin):
        """100% compliance → 0 gap → 0 recovery rate."""
        result = reweight_mixin.check_conservation_recovery(1.0)
        assert result["conservation_gap"] == 0.0
        assert result["recovery_rate"] == 0.0

    def test_small_gap_low_recovery(self, reweight_mixin):
        """Small gap → small recovery rate (quadratic scaling)."""
        # 10% gap → gap² × 3 = 0.03
        result = reweight_mixin.check_conservation_recovery(0.9)
        assert result["conservation_gap"] == pytest.approx(0.1, abs=0.001)
        assert result["recovery_rate"] == pytest.approx(0.03, abs=0.01)

    def test_large_gap_high_recovery(self, reweight_mixin):
        """Large gap → high recovery rate (exponential scaling)."""
        # 50% gap → 0.5² × 3 = 0.75
        result = reweight_mixin.check_conservation_recovery(0.5)
        assert result["conservation_gap"] == pytest.approx(0.5, abs=0.001)
        assert result["recovery_rate"] == pytest.approx(0.75, abs=0.05)

    def test_full_gap_max_recovery(self, reweight_mixin):
        """100% gap → recovery rate clamps to 1.0."""
        result = reweight_mixin.check_conservation_recovery(0.0)
        assert result["conservation_gap"] == pytest.approx(1.0, abs=0.001)
        assert result["recovery_rate"] == pytest.approx(1.0, abs=0.05)

    def test_gap_monotonic_scaling(self, reweight_mixin):
        """Recovery rate increases monotonically with gap."""
        rates = []
        for compliance in [1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.0]:
            result = reweight_mixin.check_conservation_recovery(compliance)
            rates.append(result["recovery_rate"])
        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1], \
                f"Recovery rate not monotonic: {rates[i-1]} → {rates[i]}"


# ===========================================================================
# 2. Expert Reweighting
# ===========================================================================

class TestExpertReweighting:
    def test_reweight_reduces_weight(self, reweight_mixin):
        """Expert with low contribution gets reduced weight."""
        expert_scores = {"expert-0": {"alignment": 0.3, "accuracy": 0.4}}
        result = reweight_mixin.check_conservation_recovery(0.7, expert_scores)
        weight = reweight_mixin.get_expert_weight("expert-0")
        assert weight < 1.0, f"Weight should decrease, got {weight}"

    def test_reweight_high_contributor_stays_high(self, reweight_mixin):
        """Expert with high contribution maintains weight near 1.0."""
        expert_scores = {"expert-0": {"alignment": 1.0, "accuracy": 0.99}}
        result = reweight_mixin.check_conservation_recovery(0.9, expert_scores)
        weight = reweight_mixin.get_expert_weight("expert-0")
        assert weight >= 0.9, f"High contributor weight too low: {weight}"

    def test_manual_reweight_expert(self, reweight_mixin):
        """Manual reweight_expert() adjusts weight based on gap."""
        result = reweight_mixin.reweight_expert("expert-0", gap=0.5)
        assert "old_weight" in result
        assert "new_weight" in result
        weight = reweight_mixin.get_expert_weight("expert-0")
        assert weight < 1.0, f"Weight should decrease with gap=0.5"

    def test_weight_never_zero(self, reweight_mixin):
        """Weight should never drop to zero — capacity preserved."""
        # Multiple rounds of aggressive reweighting
        for _ in range(20):
            reweight_mixin.reweight_expert("expert-0", gap=1.0)
        weight = reweight_mixin.get_expert_weight("expert-0")
        assert weight >= ConservationReweightMixin.MAX_WEIGHT_RANGE[0], \
            f"Weight dropped to {weight}, below minimum {ConservationReweightMixin.MAX_WEIGHT_RANGE[0]}"

    def test_weight_never_exceeds_max(self, reweight_mixin):
        """Weight should never exceed max range."""
        for _ in range(10):
            reweight_mixin.reweight_expert("expert-0", gap=0.0)
        weight = reweight_mixin.get_expert_weight("expert-0")
        assert weight <= ConservationReweightMixin.MAX_WEIGHT_RANGE[1], \
            f"Weight exceeded max: {weight}"

    def test_get_all_weights(self, reweight_mixin):
        """get_all_weights returns dict of expert weights."""
        reweight_mixin.reweight_expert("expert-0", gap=0.3)
        reweight_mixin.reweight_expert("expert-1", gap=0.5)
        weights = reweight_mixin.get_all_weights()
        assert "expert-0" in weights
        assert "expert-1" in weights

    def test_reset_expert_weight(self, reweight_mixin):
        """Reset returns weight to 1.0."""
        reweight_mixin.reweight_expert("expert-0", gap=0.8)
        assert reweight_mixin.get_expert_weight("expert-0") < 1.0
        result = reweight_mixin.reset_expert_weight("expert-0")
        assert result["new_weight"] == 1.0
        assert reweight_mixin.get_expert_weight("expert-0") == 1.0


# ===========================================================================
# 3. Hebbian Control Under Stress
# ===========================================================================

class TestHebbianControl:
    def test_hebbian_enabled_when_healthy(self, reweight_mixin):
        """Hebbian enabled when compliance >= 85%."""
        reweight_mixin.check_conservation_recovery(0.90)
        assert reweight_mixin.is_hebbian_enabled() is True

    def test_hebbian_disabled_under_stress(self, reweight_mixin):
        """Hebbian disabled when compliance < 85% (Study 64)."""
        reweight_mixin.check_conservation_recovery(0.70)
        assert reweight_mixin.is_hebbian_enabled() is False

    def test_hebbian_reenabled_on_recovery(self, reweight_mixin):
        """Hebbian re-enabled when compliance recovers above 85%."""
        reweight_mixin.check_conservation_recovery(0.70)
        assert reweight_mixin.is_hebbian_enabled() is False
        reweight_mixin.check_conservation_recovery(0.90)
        assert reweight_mixin.is_hebbian_enabled() is True

    def test_hebbian_at_boundary(self, reweight_mixin):
        """Exactly 85% → Hebbian enabled (>= threshold)."""
        reweight_mixin.check_conservation_recovery(0.85)
        assert reweight_mixin.is_hebbian_enabled() is True

    def test_hebbian_just_below_boundary(self, reweight_mixin):
        """84.9% → Hebbian disabled."""
        reweight_mixin.check_conservation_recovery(0.849)
        assert reweight_mixin.is_hebbian_enabled() is False

    def test_status_reflects_hebbian_state(self, reweight_mixin):
        """Status endpoint reflects Hebbian state."""
        reweight_mixin.check_conservation_recovery(0.70)
        status = reweight_mixin.get_status()
        assert status["hebbian_enabled"] is False
        reweight_mixin.check_conservation_recovery(0.90)
        status = reweight_mixin.get_status()
        assert status["hebbian_enabled"] is True


# ===========================================================================
# 4. Reweight-First / Quarantine-Second
# ===========================================================================

class TestReweightFirstFlow:
    def test_fault_triggers_reweight_not_quarantine(self, healing_with_reweight):
        """First fault detection → reweight, not quarantine."""
        healing, reweight = healing_with_reweight
        # Create consistent fault: low intent similarity + wrong answer
        result = healing.check_expert_health(
            expert_id="expert-0",
            intent_vector=[0.1] * 9,
            answer=42.0,
            fleet_answers=[100.0, 101.0, 99.0],
        )
        # First detection shouldn't quarantine
        assert result["action"] != "quarantined"

    def test_repeated_faults_reweight_before_quarantine(self, healing_with_reweight):
        """Multiple faults reweight before escalating to quarantine."""
        healing, reweight = healing_with_reweight
        # Set baseline first with healthy observation
        healing.check_expert_health(
            expert_id="expert-0",
            intent_vector=[1.0] * 9,
            answer=100.0,
            fleet_answers=[100.0, 101.0, 99.0],
        )
        # Now introduce faults
        for i in range(3):
            result = healing.check_expert_health(
                expert_id="expert-0",
                intent_vector=[0.1] * 9,
                answer=42.0,
                fleet_answers=[100.0, 101.0, 99.0],
            )
        # Should have been reweighted, not quarantined
        assert result["action"] in ("reweighted", "flagged_but_protected", "healthy")
        weight = reweight.get_expert_weight("expert-0")
        # If reweighted, weight should have changed
        if result["action"] == "reweighted":
            assert weight < 1.0

    def test_quarantine_after_reweight_exhaustion(self, healing_with_reweight):
        """After 5 rounds of failed reweighting, quarantine kicks in."""
        healing, reweight = healing_with_reweight
        # Simulate 5 failed reweight rounds
        rec = reweight._get_record("expert-0")
        rec.consecutive_reweight_failures = 5
        assert reweight.should_quarantine("expert-0") is True

    def test_should_not_quarantine_fresh_expert(self, reweight_mixin):
        """Fresh expert with no reweight history should not be quarantined."""
        assert reweight_mixin.should_quarantine("unknown-expert") is False

    def test_consecutive_failures_reset_on_improvement(self, reweight_mixin):
        """Reset failures counter when weight improves."""
        rec = reweight_mixin._get_record("expert-0")
        rec.consecutive_reweight_failures = 4
        # A reweight that improves weight (gap=0 means contribution=1.0)
        reweight_mixin.reweight_expert("expert-0", gap=0.0)
        # Internal: new_weight > old_weight should reset failures
        # But gap=0 with default weight 1.0 means weight stays, so let's set up properly
        reweight_mixin._expert_weights["expert-0"] = 0.5
        rec.consecutive_reweight_failures = 4
        reweight_mixin.reweight_expert("expert-0", gap=0.0)
        assert rec.consecutive_reweight_failures == 0


# ===========================================================================
# 5. Exponential Scaling Behavior
# ===========================================================================

class TestExponentialScaling:
    def test_larger_gap_more_aggressive(self, reweight_mixin):
        """Larger conservation gap → more aggressive weight reduction."""
        # Expert with same contribution, different gaps
        reweight_mixin.reset_expert_weight("expert-a")
        reweight_mixin.reset_expert_weight("expert-b")

        scores = {"expert-a": {"alignment": 0.5, "accuracy": 0.5},
                  "expert-b": {"alignment": 0.5, "accuracy": 0.5}}

        # Small gap
        reweight_mixin.check_conservation_recovery(0.9, {"expert-a": scores["expert-a"]})
        # Large gap
        reweight_mixin.check_conservation_recovery(0.5, {"expert-b": scores["expert-b"]})

        wa = reweight_mixin.get_expert_weight("expert-a")
        wb = reweight_mixin.get_expert_weight("expert-b")
        # Larger gap should produce more aggressive reweighting
        assert wb <= wa, f"Large gap weight ({wb}) should be <= small gap weight ({wa})"


# ===========================================================================
# 6. API Endpoints
# ===========================================================================

class TestEndpoints:
    def test_recovery_status_endpoint(self, app):
        """GET /fleet/recovery/status returns reweight status."""
        resp = app.get("/fleet/recovery/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "conservation_compliance" in data
        assert "hebbian_enabled" in data
        assert "experts" in data

    def test_recovery_reweight_endpoint(self, app):
        """POST /fleet/recovery/reweight triggers reweighting."""
        resp = app.post("/fleet/recovery/reweight", json={
            "conservation_compliance": 0.7,
            "expert_scores": {
                "expert-0": {"alignment": 0.5, "accuracy": 0.6},
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["conservation_gap"] > 0
        assert data["recovery_rate"] > 0

    def test_recovery_reweight_minimal(self, app):
        """POST /fleet/recovery/reweight with minimal body."""
        resp = app.post("/fleet/recovery/reweight", json={
            "conservation_compliance": 0.7,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["conservation_gap"] == pytest.approx(0.3, abs=0.01)

    def test_recovery_reset_endpoint(self, app):
        """POST /fleet/recovery/reset resets expert weight."""
        # First reweight
        app.post("/fleet/recovery/reweight/body", json={
            "conservation_compliance": 0.5,
            "expert_scores": {"expert-0": {"alignment": 0.3, "accuracy": 0.3}},
        })
        # Reset
        resp = app.post("/fleet/recovery/reset", json={"expert_id": "expert-0"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_weight"] == 1.0

    def test_healing_status_includes_reweight(self, app):
        """Self-healing status endpoint still works with reweight integration."""
        resp = app.get("/fleet/healing/status")
        assert resp.status_code == 200

    def test_health_endpoint(self, app):
        """Basic health endpoint still works."""
        resp = app.get("/health")
        assert resp.status_code == 200


# ===========================================================================
# 7. Integration Scenarios (Study 64 replication)
# ===========================================================================

class TestStudy64Scenarios:
    def test_single_drift_recovery(self, registry, reweight_mixin):
        """Single expert drifts → reweight, fleet recovers fast."""
        scores = {
            "expert-0": {"alignment": 0.5, "accuracy": 0.5},  # drifted
            "expert-1": {"alignment": 0.95, "accuracy": 0.95},
            "expert-2": {"alignment": 0.95, "accuracy": 0.95},
        }
        result = reweight_mixin.check_conservation_recovery(0.75, scores)
        # Drifted expert should have lower weight
        w0 = reweight_mixin.get_expert_weight("expert-0")
        w1 = reweight_mixin.get_expert_weight("expert-1")
        assert w0 < w1, "Drifted expert should have lower weight"

    def test_full_fleet_stress_large_gap(self, reweight_mixin):
        """Full fleet stress creates large gap → aggressive recovery."""
        scores = {
            f"expert-{i}": {"alignment": 0.4, "accuracy": 0.4}
            for i in range(6)
        }
        result = reweight_mixin.check_conservation_recovery(0.3, scores)
        # Should have high recovery rate due to large gap
        assert result["recovery_rate"] > 0.5, \
            f"Full stress should produce aggressive recovery, got {result['recovery_rate']}"
        # Hebbian should be disabled
        assert result["hebbian_enabled"] is False

    def test_capacity_never_removed(self, registry, reweight_mixin):
        """All experts remain available after reweighting — no removal."""
        scores = {
            f"expert-{i}": {"alignment": 0.1, "accuracy": 0.1}
            for i in range(6)
        }
        reweight_mixin.check_conservation_recovery(0.2, scores)
        # All experts should still be in registry and available
        for i in range(6):
            entry = registry.get(f"expert-{i}")
            assert entry is not None
            assert entry.available is True, f"expert-{i} should still be available"

    def test_recovery_rate_matches_study64(self, reweight_mixin):
        """Verify exponential scaling matches Study 64 formula: gap² × SCALE."""
        test_cases = [
            (0.85, 0.15),  # threshold
            (0.70, 0.30),  # moderate stress
            (0.50, 0.50),  # severe stress
        ]
        for compliance, expected_gap in test_cases:
            result = reweight_mixin.check_conservation_recovery(compliance)
            assert abs(result["conservation_gap"] - expected_gap) < 0.01, \
                f"Gap mismatch at compliance={compliance}: {result['conservation_gap']} vs {expected_gap}"
            # Recovery rate should be gap² × 3, clamped to [0, 1]
            expected_rate = min(1.0, expected_gap ** 2 * ConservationReweightMixin.GAP_SCALE_FACTOR)
            assert abs(result["recovery_rate"] - expected_rate) < 0.05, \
                f"Recovery rate mismatch: {result['recovery_rate']} vs {expected_rate}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
