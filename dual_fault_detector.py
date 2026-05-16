"""
dual_fault_detector — Combined GL(9) + Hebbian fault detection for fleet.

Study 54: Conservation and GL(9) are orthogonal (r=-0.179) → 2-signal health
Study 58: GL(9) and Hebbian are complementary (60% agreement) → both needed
Study 63: Self-healing uses this detector to trigger quarantine
Study 72: Original hash-based GL(9) has zero precision/recall → replaced with
         SemanticGL9Consensus using real semantic features

Architecture:
  Semantic GL(9): detects intent divergence via embedding sim, entropy, KL div,
                  confidence calibration, domain consistency, temporal drift
  Hebbian: detects frequency anomalies (content_scramble, domain_drift)
  Combined: union for max recall, intersection for max precision
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

from gl9_consensus import (
    SemanticGL9Consensus, ExpertObservation, FleetContext,
    compute_fleet_context, compute_semantic_intent,
)


class FaultType(Enum):
    NONE = "none"
    CONFIDENCE_DROP = "confidence_drop"
    SILENT_EXPERT = "silent_expert"
    CONTENT_SCRAMBLE = "content_scramble"
    DOMAIN_DRIFT = "domain_drift"
    CONFIDENCE_SPIKE = "confidence_spike"
    UNKNOWN = "unknown"


class DetectionSource(Enum):
    GL9 = "gl9"
    HEBBIAN = "hebbian"
    BOTH = "both"


@dataclass
class FaultReport:
    expert_id: str
    fault_type: FaultType
    source: DetectionSource
    confidence: float
    timestamp: float = field(default_factory=time.time)
    details: str = ""

    @property
    def is_reliable(self) -> bool:
        """Both detectors agree → high reliability."""
        return self.source == DetectionSource.BOTH


@dataclass
class DualDetectionResult:
    faults: list[FaultReport] = field(default_factory=list)
    gl9_faults: list[str] = field(default_factory=list)
    hebbian_faults: list[str] = field(default_factory=list)
    agreement_rate: float = 0.0
    recommendation: str = ""


class DualFaultDetector:
    """
    Combined GL(9) + Hebbian fault detection.
    
    Study 58 findings:
    - GL(9): F1=0.424, zero FP, best at confidence_drop + silent_expert
    - Hebbian: F1=0.208, catches content_scramble + domain_drift
    - Intersection: perfect precision (1.0)
    - Union: preserves GL(9)'s recall + Hebbian's unique catches
    
    Usage:
        detector = DualFaultDetector()
        result = detector.detect(gl9_consensus_result, hebbian_anomalies)
        if result.faults:
            for fault in result.faults:
                if fault.is_reliable:  # both detectors agree
                    router.quarantine(fault.expert_id)
    """
    
    def __init__(self,
                 gl9_weight: float = 0.7,
                 hebbian_weight: float = 0.3,
                 quarantine_threshold: float = 0.6,
                 use_semantic_gl9: bool = True,
                 gl9_similarity_threshold: float = 0.3):
        self.gl9_weight = gl9_weight
        self.hebbian_weight = hebbian_weight
        self.quarantine_threshold = quarantine_threshold
        self.use_semantic_gl9 = use_semantic_gl9
        self._semantic_gl9 = SemanticGL9Consensus(
            tolerance=0.5,
            similarity_threshold=gl9_similarity_threshold,
        )
        self._history: list[DualDetectionResult] = []
    
    def detect(self,
               gl9_faulty: Optional[list[str]] = None,
               hebbian_anomalies: Optional[list[str]] = None,
               gl9_details: Optional[dict] = None,
               hebbian_details: Optional[dict] = None) -> DualDetectionResult:
        """
        Combine GL(9) and Hebbian fault detection results.

        Args:
            gl9_faulty: List of expert IDs flagged by GL(9)
            hebbian_anomalies: List of expert IDs flagged by Hebbian
            gl9_details: Optional dict of {expert_id: deviation}
            hebbian_details: Optional dict of {expert_id: anomaly_score}

        Returns:
            DualDetectionResult with combined fault reports
        """
        gl9_set = set(gl9_faulty or [])
        heb_set = set(hebbian_anomalies or [])
        
        # Agreement analysis
        agreement = gl9_set & heb_set
        total_flagged = gl9_set | heb_set
        agreement_rate = len(agreement) / len(total_flagged) if total_flagged else 1.0
        
        faults = []
        
        # Experts flagged by BOTH → high confidence
        gl9_det = gl9_details or {}
        heb_det = hebbian_details or {}
        for expert_id in agreement:
            confidence = self.gl9_weight + self.hebbian_weight
            faults.append(FaultReport(
                expert_id=expert_id,
                fault_type=FaultType.UNKNOWN,
                source=DetectionSource.BOTH,
                confidence=min(confidence, 1.0),
                details=f"GL9 deviation: {gl9_det.get(expert_id, 'N/A')}, "
                        f"Hebbian anomaly: {heb_det.get(expert_id, 'N/A')}"
            ))
        
        # Experts flagged by GL(9) only
        for expert_id in gl9_set - heb_set:
            dev = gl9_details.get(expert_id, 0) if gl9_details else 0
            fault_type = (FaultType.CONFIDENCE_DROP if dev > 2.0 
                         else FaultType.SILENT_EXPERT if dev < 0.01
                         else FaultType.UNKNOWN)
            faults.append(FaultReport(
                expert_id=expert_id,
                fault_type=fault_type,
                source=DetectionSource.GL9,
                confidence=self.gl9_weight,
                details=f"GL9 deviation: {dev:.3f}"
            ))
        
        # Experts flagged by Hebbian only
        for expert_id in heb_set - gl9_set:
            score = hebbian_details.get(expert_id, 0) if hebbian_details else 0
            fault_type = (FaultType.CONTENT_SCRAMBLE if score > 0.8
                         else FaultType.DOMAIN_DRIFT if score > 0.5
                         else FaultType.UNKNOWN)
            faults.append(FaultReport(
                expert_id=expert_id,
                fault_type=fault_type,
                source=DetectionSource.HEBBIAN,
                confidence=self.hebbian_weight,
                details=f"Hebbian anomaly score: {score:.3f}"
            ))
        
        # Recommendation
        reliable_faults = [f for f in faults if f.is_reliable]
        if reliable_faults:
            recommendation = f"QUARANTINE: {len(reliable_faults)} experts confirmed faulty by both detectors"
        elif faults:
            max_conf = max(f.confidence for f in faults)
            if max_conf >= self.quarantine_threshold:
                recommendation = f"INVESTIGATE: {len(faults)} experts flagged, max confidence {max_conf:.2f}"
            else:
                recommendation = f"MONITOR: {len(faults)} weak signals, below quarantine threshold"
        else:
            recommendation = "HEALTHY: no faults detected"
        
        result = DualDetectionResult(
            faults=faults,
            gl9_faults=list(gl9_set),
            hebbian_faults=list(heb_set),
            agreement_rate=agreement_rate,
            recommendation=recommendation,
        )
        self._history.append(result)
        return result
    
    def detect_observations(
        self,
        observations: list[ExpertObservation],
        hebbian_anomalies: Optional[list[str]] = None,
        hebbian_details: Optional[dict] = None,
    ) -> DualDetectionResult:
        """
        One-step detection using ExpertObservation objects.

        Runs SemanticGL9 on the observations, combines with Hebbian results.
        This is the preferred API for production use.

        Args:
            observations: List of ExpertObservation from fleet experts
            hebbian_anomalies: Optional list of expert IDs flagged by Hebbian
            hebbian_details: Optional dict of {expert_id: anomaly_score}

        Returns:
            DualDetectionResult with combined fault reports
        """
        gl9_faulty, gl9_devs = self._semantic_gl9.detect_with_details(observations)
        return self.detect(
            gl9_faulty=gl9_faulty,
            hebbian_anomalies=hebbian_anomalies,
            gl9_details=gl9_devs,
            hebbian_details=hebbian_details,
        )

    def should_quarantine(self, expert_id: str) -> tuple[bool, str]:
        """Check if an expert should be quarantined based on detection history."""
        if not self._history:
            return False, "no history"
        
        latest = self._history[-1]
        for fault in latest.faults:
            if fault.expert_id == expert_id:
                if fault.is_reliable:
                    return True, "confirmed by both detectors"
                if fault.confidence >= self.quarantine_threshold:
                    return True, f"confidence {fault.confidence:.2f} >= threshold"
                return False, f"confidence {fault.confidence:.2f} < threshold"
        return False, "not flagged"
    
    @property
    def history(self) -> list[DualDetectionResult]:
        return self._history
    
    @property 
    def stats(self) -> dict:
        if not self._history:
            return {"detections": 0}
        total = len(self._history)
        with_faults = sum(1 for h in self._history if h.faults)
        reliable = sum(1 for h in self._history 
                      for f in h.faults if f.is_reliable)
        return {
            "total_detections": total,
            "detections_with_faults": with_faults,
            "reliable_faults": reliable,
            "fault_rate": with_faults / total if total else 0,
        }
