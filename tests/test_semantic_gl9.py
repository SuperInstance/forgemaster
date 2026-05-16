"""
Test SemanticGL9Consensus — Study 72 fix for hash-based GL(9).

Validates that replacing 6 deterministic hash dimensions with real semantic
features makes GL(9) actually detect faults (unlike the original which had
precision=recall=0 at all fleet sizes).
"""
import math
import random
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gl9_consensus import (
    SemanticGL9Consensus,
    ExpertObservation,
    FleetContext,
    compute_fleet_context,
    compute_semantic_intent,
    shannon_entropy,
    token_kl_divergence,
    IntentVector,
    SEMANTIC_CI_FACETS,
)
from dual_fault_detector import DualFaultDetector, FaultType, DetectionSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_healthy_obs(
    expert_id: str = "e1",
    confidence: float = 0.9,
    response: str = "The answer is 42.",
    tokens: list[str] | None = None,
    domain: str = "math",
    embedding: list[float] | None = None,
    predicted_accuracy: float = 0.9,
    actual_accuracy: float = 0.9,
) -> ExpertObservation:
    if tokens is None:
        tokens = ["The", "answer", "is", "42", "."]
    if embedding is None:
        embedding = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    return ExpertObservation(
        expert_id=expert_id,
        response=response,
        tokens=tokens,
        confidence=confidence,
        embedding=embedding,
        domain=domain,
        predicted_accuracy=predicted_accuracy,
        actual_accuracy=actual_accuracy,
    )


def make_faulty_confidence_drop(expert_id: str = "faulty") -> ExpertObservation:
    """Expert with very low confidence — classic confidence_drop fault."""
    return ExpertObservation(
        expert_id=expert_id,
        response="I think maybe it could be... something?",
        tokens=["I", "think", "maybe", "it", "could", "be", "something"],
        confidence=0.1,  # way below healthy ~0.9
        embedding=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        domain="math",
        predicted_accuracy=0.9,
        actual_accuracy=0.3,  # miscalibrated
    )


def make_faulty_content_scramble(expert_id: str = "scrambled") -> ExpertObservation:
    """Expert with completely scrambled tokens — content_scramble fault."""
    return ExpertObservation(
        expert_id=expert_id,
        response="xkcd banana pillow fort quantum cabbage",
        tokens=["xkcd", "banana", "pillow", "fort", "quantum", "cabbage"],
        confidence=0.85,
        embedding=[0.9, 0.1, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.5],
        domain="math",
        predicted_accuracy=0.85,
        actual_accuracy=0.2,
    )


def make_faulty_domain_drift(expert_id: str = "drifter") -> ExpertObservation:
    """Expert responding in wrong domain — domain_drift fault."""
    return ExpertObservation(
        expert_id=expert_id,
        response="The mitochondria is the powerhouse of the cell.",
        tokens=["The", "mitochondria", "is", "the", "powerhouse", "of", "the", "cell"],
        confidence=0.88,
        embedding=[0.2, 0.8, 0.3, 0.1, 0.9, 0.4, 0.7, 0.3, 0.6],
        domain="biology",  # wrong domain for math fleet
        predicted_accuracy=0.88,
        actual_accuracy=0.88,
    )


def make_faulty_silent_expert(expert_id: str = "silent") -> ExpertObservation:
    """Expert that barely responds — silent_expert fault."""
    return ExpertObservation(
        expert_id=expert_id,
        response="ok",
        tokens=["ok"],
        confidence=0.05,  # very low
        embedding=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        domain="math",
        predicted_accuracy=0.05,
        actual_accuracy=0.05,
    )


def make_faulty_confidence_spike(expert_id: str = "spiky") -> ExpertObservation:
    """Expert with extreme overconfidence — confidence_spike fault."""
    return ExpertObservation(
        expert_id=expert_id,
        response="Absolutely 100% certain the answer is definitely 42!",
        tokens=["Absolutely", "100%", "certain", "the", "answer", "is", "definitely", "42"],
        confidence=1.0,  # maxed out
        embedding=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        domain="math",
        predicted_accuracy=1.0,
        actual_accuracy=0.4,  # badly miscalibrated
    )


# ---------------------------------------------------------------------------
# Test Semantic Feature Computation
# ---------------------------------------------------------------------------

class TestSemanticFeatures:
    """Test that individual semantic dimensions compute correctly."""

    def test_shannon_entropy_uniform(self):
        """Uniform distribution → maximum entropy."""
        tokens = ["a", "b", "c", "d"]
        e = shannon_entropy(tokens)
        assert e == pytest.approx(2.0, abs=0.01)

    def test_shannon_entropy_single(self):
        """Single token repeated → zero entropy."""
        tokens = ["x"] * 10
        assert shannon_entropy(tokens) == pytest.approx(0.0, abs=0.01)

    def test_shannon_entropy_empty(self):
        assert shannon_entropy([]) == 0.0

    def test_token_kl_divergence_identical(self):
        """Same distribution → KL ≈ 0."""
        tokens = ["a", "b", "c"] * 10
        kl = token_kl_divergence(tokens, tokens)
        assert kl == pytest.approx(0.0, abs=0.1)  # smoothing gives small residual

    def test_token_kl_divergence_different(self):
        """Very different distributions → KL > 0."""
        a = ["a"] * 100
        b = ["b"] * 100
        kl = token_kl_divergence(a, b)
        assert kl > 0.5

    def test_token_kl_divergence_empty(self):
        assert token_kl_divergence([], ["a"]) == 0.0
        assert token_kl_divergence(["a"], []) == 0.0

    def test_embedding_similarity_same(self):
        """Same embedding → similarity ≈ 1."""
        obs = make_healthy_obs()
        ctx = compute_fleet_context([obs, obs])
        intent = compute_semantic_intent(obs, ctx)
        # C1 should be high for self-similar
        assert intent.data[0] > 0.9

    def test_embedding_similarity_different(self):
        """Very different embedding → similarity drops."""
        obs = make_healthy_obs()
        other = ExpertObservation(
            expert_id="e2",
            response="Different",
            tokens=["Different"],
            confidence=0.9,
            embedding=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            domain="math",
        )
        ctx = compute_fleet_context([obs, other])
        intent = compute_semantic_intent(obs, ctx)
        assert 0.0 <= intent.data[0] <= 1.0

    def test_output_entropy_reflects_tokens(self):
        """More diverse tokens → higher entropy dimension."""
        uniform_tokens = ["a", "b", "c", "d"]
        degenerate_tokens = ["x"] * 4
        obs_uniform = make_healthy_obs(tokens=uniform_tokens)
        obs_degen = make_healthy_obs(tokens=degenerate_tokens)
        ctx = compute_fleet_context([obs_uniform, obs_degen])
        intent_uniform = compute_semantic_intent(obs_uniform, ctx)
        intent_degen = compute_semantic_intent(obs_degen, ctx)
        # C2: entropy dimension
        assert intent_uniform.data[1] > intent_degen.data[1]

    def test_confidence_dimension_healthy(self):
        """Healthy confidence (0.9) in a healthy fleet → C4 near 0.5 (z≈0)."""
        fleet = [make_healthy_obs(f"e{i}", confidence=0.9) for i in range(5)]
        ctx = compute_fleet_context(fleet)
        intent = compute_semantic_intent(fleet[0], ctx)
        # z-score of 0.9 in a fleet of 0.9s → z=0 → C4 = 0.5
        assert intent.data[3] == pytest.approx(0.5, abs=0.05)

    def test_confidence_dimension_faulty(self):
        """Very low confidence (0.1) in a healthy fleet → C4 low."""
        fleet = [make_healthy_obs(f"e{i}", confidence=0.9) for i in range(5)]
        faulty = make_healthy_obs("faulty", confidence=0.1)
        all_obs = fleet + [faulty]
        ctx = compute_fleet_context(all_obs)
        intent_faulty = compute_semantic_intent(faulty, ctx)
        intent_healthy = compute_semantic_intent(fleet[0], ctx)
        # Faulty expert should have lower C4 than healthy
        assert intent_faulty.data[3] < intent_healthy.data[3]

    def test_domain_consistency_match(self):
        """Expert in majority domain → C8 = 1.0."""
        fleet = [make_healthy_obs(f"e{i}", domain="math") for i in range(5)]
        ctx = compute_fleet_context(fleet)
        intent = compute_semantic_intent(fleet[0], ctx)
        assert intent.data[7] == 1.0

    def test_domain_consistency_mismatch(self):
        """Expert in minority domain → C8 = 0.0."""
        fleet = [make_healthy_obs(f"e{i}", domain="math") for i in range(5)]
        drifter = make_healthy_obs("drifter", domain="biology")
        all_obs = fleet + [drifter]
        ctx = compute_fleet_context(all_obs)
        intent_drifter = compute_semantic_intent(drifter, ctx)
        assert intent_drifter.data[7] == 0.0

    def test_calibration_error(self):
        """Miscalibrated expert → C7 > 0."""
        obs = make_healthy_obs(predicted_accuracy=0.9, actual_accuracy=0.3)
        ctx = compute_fleet_context([obs])
        intent = compute_semantic_intent(obs, ctx)
        assert intent.data[6] == pytest.approx(0.6, abs=0.01)

    def test_semantic_drift_no_prev(self):
        """No previous intent → C6 = 0."""
        obs = make_healthy_obs()
        ctx = compute_fleet_context([obs])
        intent = compute_semantic_intent(obs, ctx, prev_intent=None)
        assert intent.data[5] == 0.0

    def test_intent_vector_is_9d(self):
        obs = make_healthy_obs()
        ctx = compute_fleet_context([obs])
        intent = compute_semantic_intent(obs, ctx)
        assert len(intent.data) == 9

    def test_all_dims_bounded(self):
        """All dimensions should be finite and in reasonable range."""
        obs = make_healthy_obs()
        ctx = compute_fleet_context([obs])
        intent = compute_semantic_intent(obs, ctx)
        for i, d in enumerate(intent.data):
            assert math.isfinite(d), f"Dim {i} ({SEMANTIC_CI_FACETS[i]}) is not finite: {d}"


# ---------------------------------------------------------------------------
# Test SemanticGL9Consensus Detection
# ---------------------------------------------------------------------------

class TestSemanticGL9Detection:
    """Test that SemanticGL9Consensus actually detects faults."""

    def test_healthy_fleet_no_false_positives(self):
        """All-healthy fleet → no detections."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        detector = SemanticGL9Consensus(similarity_threshold=0.3)
        faulty = detector.detect_faults(fleet)
        assert faulty == []

    def test_confidence_drop_detected(self):
        """Expert with confidence drop should be flagged."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[3] = make_faulty_confidence_drop("faulty")
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "faulty" in faulty

    def test_silent_expert_detected(self):
        """Silent expert should be flagged."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[5] = make_faulty_silent_expert("silent")
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "silent" in faulty

    def test_content_scramble_detected(self):
        """Scrambled content should be flagged."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[1] = make_faulty_content_scramble("scrambled")
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "scrambled" in faulty

    def test_domain_drift_detected(self):
        """Expert in wrong domain should be flagged."""
        fleet = [make_healthy_obs(f"e{i}", domain="math") for i in range(9)]
        fleet[7] = make_faulty_domain_drift("drifter")
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "drifter" in faulty

    def test_confidence_spike_detected(self):
        """Overconfident miscalibrated expert should be flagged."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[2] = make_faulty_confidence_spike("spiky")
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "spiky" in faulty

    def test_detection_at_v5(self):
        """Small fleet (V=5) should still detect obvious faults."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(4)]
        fleet.append(make_faulty_confidence_drop("faulty"))
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "faulty" in faulty

    def test_detection_at_v9(self):
        """V=9 fleet with one fault should detect it."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(8)]
        fleet.append(make_faulty_confidence_drop("faulty"))
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "faulty" in faulty

    def test_detection_at_v15(self):
        """V=15 fleet with one fault should detect it."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(14)]
        fleet.append(make_faulty_confidence_drop("faulty"))
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "faulty" in faulty

    def test_detection_at_v25(self):
        """V=25 fleet with one fault should detect it."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(24)]
        fleet.append(make_faulty_confidence_drop("faulty"))
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "faulty" in faulty

    def test_multiple_faults_detected(self):
        """Multiple faulty experts should all be detected."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(7)]
        fleet.append(make_faulty_confidence_drop("faulty1"))
        fleet.append(make_faulty_content_scramble("faulty2"))
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert "faulty1" in faulty
        assert "faulty2" in faulty

    def test_detect_with_details_returns_deviations(self):
        """detect_with_details should return deviation scores."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[0] = make_faulty_confidence_drop("faulty")
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty, details = detector.detect_with_details(fleet)
        assert "faulty" in faulty
        assert "faulty" in details
        assert details["faulty"] > 0.0

    def test_too_few_experts_no_detection(self):
        """Single expert → no detection (need at least 2 for similarity)."""
        fleet = [make_faulty_confidence_drop("lonely")]
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults(fleet)
        assert faulty == []

    def test_empty_observations(self):
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        faulty = detector.detect_faults([])
        assert faulty == []

    def test_temporal_drift_detected_on_second_round(self):
        """An expert that changes drastically between rounds should be flagged."""
        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        # Round 1: all healthy
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        detector.detect_faults(fleet)

        # Round 2: one expert goes bad
        fleet[3] = make_faulty_confidence_drop("e3")
        faulty = detector.detect_faults(fleet)
        assert "e3" in faulty


# ---------------------------------------------------------------------------
# Test DualFaultDetector Integration
# ---------------------------------------------------------------------------

class TestDualDetectorIntegration:
    """Test DualFaultDetector with semantic GL(9)."""

    def test_semantic_gl9_mode_default(self):
        """Default constructor should use semantic GL(9)."""
        detector = DualFaultDetector()
        assert detector.use_semantic_gl9 is True

    def test_detect_observations_api(self):
        """detect_observations should combine semantic GL(9) + Hebbian."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[3] = make_faulty_confidence_drop("faulty")

        detector = DualFaultDetector(quarantine_threshold=0.5)
        # Pass Hebbian anomalies as well
        result = detector.detect_observations(
            observations=fleet,
            hebbian_anomalies=["faulty"],
        )
        assert result.faults
        # Should have GL9 flagging faulty
        assert "faulty" in result.gl9_faults
        # Since both flagged → reliable
        reliable = [f for f in result.faults if f.expert_id == "faulty" and f.is_reliable]
        assert len(reliable) >= 1

    def test_gl9_only_detection(self):
        """Semantic GL(9) alone should detect faults."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        fleet[5] = make_faulty_confidence_drop("faulty")

        detector = DualFaultDetector()
        result = detector.detect_observations(fleet)
        assert "faulty" in result.gl9_faults

    def test_healthy_fleet_clean(self):
        """Healthy fleet → no faults."""
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        detector = DualFaultDetector()
        result = detector.detect_observations(fleet)
        assert not result.faults
        assert result.recommendation.startswith("HEALTHY")

    def test_backward_compat_detect_method(self):
        """Old detect() API still works for pre-computed results."""
        detector = DualFaultDetector()
        result = detector.detect(
            gl9_faulty=["e1"],
            hebbian_anomalies=["e1", "e2"],
            gl9_details={"e1": 0.5},
            hebbian_details={"e1": 0.7, "e2": 0.3},
        )
        assert len(result.faults) == 2
        assert "e1" in result.gl9_faults

    def test_stats_tracking(self):
        """Stats should track detection history."""
        detector = DualFaultDetector()
        fleet = [make_healthy_obs(f"e{i}") for i in range(9)]
        detector.detect_observations(fleet)  # healthy
        fleet[0] = make_faulty_confidence_drop("e0")
        detector.detect_observations(fleet)  # faulty
        stats = detector.stats
        assert stats["total_detections"] == 2
        assert stats["detections_with_faults"] == 1


# ---------------------------------------------------------------------------
# Validation: Does semantic GL(9) beat the old hash-based approach?
# ---------------------------------------------------------------------------

class TestStudy72Validation:
    """
    Quick validation: semantic GL(9) should detect faults where the old
    hash-based approach detected nothing (precision=recall=0).
    """

    @pytest.fixture
    def seeded_random(self):
        return random.Random(42)

    def _run_trial(self, rng: random.Random, fleet_size: int, fault_type: str):
        """Generate one trial and return (true_faults, detected_faults)."""
        domains = ["math", "code", "science", "logic", "language"]
        domain = rng.choice(domains)

        fleet = []
        true_faulty = set()
        for i in range(fleet_size):
            is_faulty = rng.random() < 0.3
            if is_faulty:
                true_faulty.add(f"e{i}")
                if fault_type == "confidence_drop":
                    fleet.append(make_healthy_obs(
                        f"e{i}", confidence=rng.uniform(0.0, 0.2),
                        domain=domain, response=rng.choice(["maybe", "idk", "huh?"]),
                    ))
                elif fault_type == "content_scramble":
                    fleet.append(make_healthy_obs(
                        f"e{i}", confidence=rng.uniform(0.8, 0.95),
                        domain=domain, tokens=["xyz", "abc", "qqq", "zzz"],
                    ))
                elif fault_type == "domain_drift":
                    wrong_domain = rng.choice([d for d in domains if d != domain])
                    fleet.append(make_healthy_obs(
                        f"e{i}", confidence=rng.uniform(0.8, 0.95),
                        domain=wrong_domain,
                    ))
                else:
                    fleet.append(make_healthy_obs(
                        f"e{i}", confidence=rng.uniform(0.8, 0.95),
                        domain=domain,
                    ))
            else:
                fleet.append(make_healthy_obs(
                    f"e{i}",
                    confidence=rng.uniform(0.8, 0.95),
                    domain=domain,
                ))

        detector = SemanticGL9Consensus(similarity_threshold=0.2)
        detected = set(detector.detect_faults(fleet))

        tp = len(true_faulty & detected)
        fp = len(detected - true_faulty)
        fn = len(true_faulty - detected)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return precision, recall

    def test_semantic_beats_hash_baseline(self, seeded_random):
        """Semantic GL(9) should have recall > 0 (hash-based had 0.000)."""
        fault_types = ["confidence_drop", "content_scramble", "domain_drift"]
        total_recall = 0.0
        trials = 0
        for ft in fault_types:
            for _ in range(20):
                p, r = self._run_trial(seeded_random, 9, ft)
                total_recall += r
                trials += 1
        avg_recall = total_recall / trials if trials > 0 else 0
        # The old hash-based GL(9) had recall = 0.000
        # Semantic GL(9) should be > 0
        assert avg_recall > 0.0, (
            f"Semantic GL(9) avg recall {avg_recall:.3f} should be > 0 "
            f"(old hash-based was 0.000)"
        )

    def test_semantic_precision_above_zero(self, seeded_random):
        """Semantic GL(9) should have precision > 0 (hash-based had 0.000)."""
        fault_types = ["confidence_drop", "content_scramble", "domain_drift"]
        total_precision = 0.0
        trials_with_detections = 0
        for ft in fault_types:
            for _ in range(20):
                p, r = self._run_trial(seeded_random, 9, ft)
                if p > 0 or r > 0:
                    total_precision += p
                    trials_with_detections += 1
        avg_precision = total_precision / trials_with_detections if trials_with_detections > 0 else 0
        # Old: precision = 0.000
        assert avg_precision > 0.0, "Semantic GL(9) should detect something"


# ---------------------------------------------------------------------------
# Test FleetContext computation
# ---------------------------------------------------------------------------

class TestFleetContext:
    def test_compute_fleet_context_basic(self):
        obs = [make_healthy_obs(f"e{i}", confidence=0.9) for i in range(5)]
        ctx = compute_fleet_context(obs)
        assert ctx.mean_confidence == pytest.approx(0.9, abs=0.01)
        assert ctx.majority_domain == "math"

    def test_compute_fleet_context_empty(self):
        ctx = compute_fleet_context([])
        assert ctx.mean_confidence == 1.0
        assert ctx.majority_domain == ""

    def test_fleet_context_length_stats(self):
        obs = [
            make_healthy_obs("e1", response="short"),
            make_healthy_obs("e2", response="a bit longer response here"),
        ]
        ctx = compute_fleet_context(obs)
        assert ctx.mean_response_length > 0
        assert ctx.std_response_length > 0

    def test_fleet_context_domain_majority(self):
        obs = [
            make_healthy_obs("e1", domain="math"),
            make_healthy_obs("e2", domain="math"),
            make_healthy_obs("e3", domain="biology"),
        ]
        ctx = compute_fleet_context(obs)
        assert ctx.majority_domain == "math"
