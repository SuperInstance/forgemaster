"""Tests for dual_fault_detector — combined GL(9) + Hebbian fault detection."""
import pytest
from dual_fault_detector import (
    DualFaultDetector, DualDetectionResult, FaultReport,
    FaultType, DetectionSource,
)


class TestDualDetector:
    def test_no_faults(self):
        d = DualFaultDetector()
        r = d.detect()
        assert len(r.faults) == 0
        assert r.recommendation.startswith("HEALTHY")

    def test_gl9_only(self):
        d = DualFaultDetector()
        r = d.detect(gl9_faulty=["expert-1"], gl9_details={"expert-1": 3.5})
        assert len(r.faults) == 1
        assert r.faults[0].source == DetectionSource.GL9
        assert r.faults[0].fault_type == FaultType.CONFIDENCE_DROP
        assert "MONITOR" in r.recommendation or "INVESTIGATE" in r.recommendation

    def test_hebbian_only(self):
        d = DualFaultDetector()
        r = d.detect(hebbian_anomalies=["expert-2"], hebbian_details={"expert-2": 0.9})
        assert len(r.faults) == 1
        assert r.faults[0].source == DetectionSource.HEBBIAN
        assert r.faults[0].fault_type == FaultType.CONTENT_SCRAMBLE

    def test_both_agree(self):
        d = DualFaultDetector()
        r = d.detect(
            gl9_faulty=["expert-3"],
            hebbian_anomalies=["expert-3"],
            gl9_details={"expert-3": 2.0},
            hebbian_details={"expert-3": 0.7},
        )
        assert len(r.faults) == 1
        assert r.faults[0].source == DetectionSource.BOTH
        assert r.faults[0].is_reliable is True
        assert r.agreement_rate == 1.0
        assert "QUARANTINE" in r.recommendation

    def test_partial_agreement(self):
        d = DualFaultDetector()
        r = d.detect(
            gl9_faulty=["a", "b"],
            hebbian_anomalies=["b", "c"],
        )
        assert len(r.faults) == 3
        both_faults = [f for f in r.faults if f.source == DetectionSource.BOTH]
        assert len(both_faults) == 1
        assert both_faults[0].expert_id == "b"
        assert r.agreement_rate == pytest.approx(1/3, abs=0.01)

    def test_silent_expert_detection(self):
        d = DualFaultDetector()
        r = d.detect(gl9_faulty=["expert-5"], gl9_details={"expert-5": 0.001})
        assert r.faults[0].fault_type == FaultType.SILENT_EXPERT

    def test_domain_drift_detection(self):
        d = DualFaultDetector()
        r = d.detect(hebbian_anomalies=["expert-6"], hebbian_details={"expert-6": 0.6})
        assert r.faults[0].fault_type == FaultType.DOMAIN_DRIFT


class TestQuarantine:
    def test_quarantine_both_agree(self):
        d = DualFaultDetector()
        d.detect(gl9_faulty=["e1"], hebbian_anomalies=["e1"])
        should, reason = d.should_quarantine("e1")
        assert should is True
        assert "both" in reason

    def test_no_quarantine_below_threshold(self):
        d = DualFaultDetector(quarantine_threshold=0.8)
        d.detect(gl9_faulty=["e2"], gl9_details={"e2": 1.0})
        should, reason = d.should_quarantine("e2")
        assert should is False

    def test_no_quarantine_not_flagged(self):
        d = DualFaultDetector()
        d.detect(gl9_faulty=["e1"])
        should, reason = d.should_quarantine("e2")
        assert should is False

    def test_quarantine_high_confidence(self):
        d = DualFaultDetector(quarantine_threshold=0.5)
        d.detect(gl9_faulty=["e3"], gl9_details={"e3": 2.0})
        should, reason = d.should_quarantine("e3")
        assert should is True


class TestHistory:
    def test_empty_stats(self):
        d = DualFaultDetector()
        assert d.stats["detections"] == 0

    def test_stats_accumulate(self):
        d = DualFaultDetector()
        d.detect()  # healthy
        d.detect(gl9_faulty=["e1"])  # fault
        d.detect(gl9_faulty=["e2"], hebbian_anomalies=["e2"])  # reliable
        stats = d.stats
        assert stats["total_detections"] == 3
        assert stats["detections_with_faults"] == 2
        assert stats["reliable_faults"] == 1

    def test_history_persists(self):
        d = DualFaultDetector()
        d.detect()
        d.detect(gl9_faulty=["e1"])
        assert len(d.history) == 2
