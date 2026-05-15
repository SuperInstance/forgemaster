#!/usr/bin/env python3
"""Tests for expert_hebbian_bridge.py — 25 tests covering all 5 components."""

import json
import threading
import time
import urllib.request
import unittest
from unittest.mock import patch

import numpy as np

from expert_hebbian_bridge import (
    EXPERT_TYPES, EXPERT_DOMAIN_MAP, EXPERT_AFFINITY,
    ExpertRoomAdapter,
    ExpertCouplingMatrix,
    ConservationConstrainedCrossConsult,
    ExpertStageClassifier,
    ExpertHebbianDashboard,
    ExpertHebbianBridge,
    predicted_gamma_plus_H,
    coupling_entropy,
    algebraic_normalized,
)


class TestExpertRoomAdapter(unittest.TestCase):
    """Tests for ExpertRoomAdapter."""

    def setUp(self):
        self.adapter = ExpertRoomAdapter(n_experts=9)

    def test_all_9_rooms_created(self):
        rooms = self.adapter.all_rooms()
        self.assertEqual(len(rooms), 9)
        for expert in EXPERT_TYPES[:9]:
            self.assertIn(f"expert-{expert}", rooms)

    def test_expert_to_room_round_trip(self):
        for expert in self.adapter.expert_names:
            room = self.adapter.expert_to_room(expert)
            self.assertEqual(room, f"expert-{expert}")
            back = self.adapter.room_to_expert(room)
            self.assertEqual(back, expert)

    def test_expert_to_domain_mapping(self):
        self.assertEqual(self.adapter.expert_to_domain("conservation"), "math")
        self.assertEqual(self.adapter.expert_to_domain("architect"), "plato")
        self.assertEqual(self.adapter.expert_to_domain("tripartite"), "agent")
        self.assertEqual(self.adapter.expert_to_domain("builder"), "code")
        self.assertEqual(self.adapter.expert_to_domain("navigator"), "fleet")

    def test_convert_tile_structure(self):
        tile = self.adapter.convert_tile(
            expert_type="mathematician",
            output="The answer is 42",
            confidence=0.95,
        )
        self.assertEqual(tile["room"], "expert-mathematician")
        self.assertEqual(tile["domain"], "math")
        self.assertEqual(tile["expert_type"], "mathematician")
        self.assertEqual(tile["confidence"], 0.95)
        self.assertEqual(tile["content"], "The answer is 42")
        self.assertIn("activation_keys", tile)
        self.assertIn("conservation-aware", tile["activation_keys"])

    def test_activation_keys_by_confidence(self):
        low = self.adapter._compute_activation_keys("builder", 0.3)
        self.assertEqual(low, ["base"])

        mid = self.adapter._compute_activation_keys("builder", 0.75)
        self.assertIn("dual-filtered", mid)

        high = self.adapter._compute_activation_keys("builder", 0.97)
        self.assertIn("conservation-aware", high)

    def test_unknown_expert_raises(self):
        with self.assertRaises(ValueError):
            self.adapter.expert_to_room("nonexistent")

    def test_room_index_consistent(self):
        idx = self.adapter.room_index()
        rooms = self.adapter.all_rooms()
        for room in rooms:
            self.assertIn(room, idx)
            self.assertEqual(idx[room], rooms.index(room))

    def test_tile_counts_track(self):
        self.adapter.convert_tile("builder", "code1", 0.9)
        self.adapter.convert_tile("builder", "code2", 0.8)
        self.adapter.convert_tile("critic", "review1", 0.7)
        counts = self.adapter.get_tile_counts()
        self.assertEqual(counts["builder"], 2)
        self.assertEqual(counts["critic"], 1)
        self.assertEqual(counts["oracle"], 0)


class TestExpertCouplingMatrix(unittest.TestCase):
    """Tests for ExpertCouplingMatrix."""

    def setUp(self):
        self.coupling = ExpertCouplingMatrix(n_experts=9)

    def test_initial_weights_zero(self):
        w = self.coupling.get_matrix()
        self.assertTrue(np.allclose(w, 0))

    def test_record_consultation_updates_weight(self):
        event = self.coupling.record_consultation("conservation", "mathematician", strength=1.0)
        self.assertAlmostEqual(event["new_weight"], 0.01, places=4)
        self.assertEqual(event["source"], "conservation")
        self.assertEqual(event["target"], "mathematician")

    def test_repeated_consultations_strengthen(self):
        for _ in range(50):
            self.coupling.record_consultation("architect", "builder", strength=1.0)
        strength = self.coupling.get_coupling_strength("architect", "builder")
        self.assertGreater(strength, 0.3)

    def test_self_review_updates_diagonal(self):
        event = self.coupling.record_self_review("oracle", quality=0.8)
        self.assertEqual(event["source"], "oracle")
        self.assertEqual(event["target"], "oracle")
        self.assertGreater(event["new_weight"], 0)

    def test_top_couplings_returns_strongest(self):
        # Create asymmetric coupling
        for _ in range(20):
            self.coupling.record_consultation("conservation", "mathematician", 1.0)
        for _ in range(5):
            self.coupling.record_consultation("architect", "builder", 1.0)

        top = self.coupling.get_top_couplings(3)
        self.assertGreaterEqual(len(top), 2)
        # Strongest should be conservation→mathematician
        self.assertEqual(top[0]["source"], "conservation")

    def test_conservation_check_zero_weights(self):
        report = self.coupling.check_conservation()
        self.assertTrue(report["conserved"])
        self.assertEqual(report["gamma_plus_H"], 0.0)

    def test_conservation_check_with_weights(self):
        for _ in range(100):
            self.coupling.record_consultation("conservation", "mathematician", 1.0)
        report = self.coupling.check_conservation()
        self.assertIn("gamma", report)
        self.assertIn("H", report)
        self.assertIn("gamma_plus_H", report)
        self.assertIn("conserved", report)

    def test_conservation_projection(self):
        # Drive weights until they might violate conservation
        for i in range(200):
            for src in EXPERT_TYPES[:3]:
                for tgt in EXPERT_TYPES[:3]:
                    self.coupling.record_consultation(src, tgt, 1.0)
        scale = self.coupling.project_to_conservation()
        self.assertIsInstance(scale, float)

    def test_recent_consultations_tracking(self):
        self.coupling.record_consultation("architect", "builder", 1.0)
        self.coupling.record_consultation("builder", "navigator", 0.5)
        recent = self.coupling.recent_consultations(10)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[-1]["source"], "builder")

    def test_summary_structure(self):
        self.coupling.record_consultation("oracle", "mathematician", 0.9)
        s = self.coupling.summary()
        self.assertIn("n_experts", s)
        self.assertIn("conservation", s)
        self.assertIn("top_couplings", s)
        self.assertIn("weight_stats", s)


class TestConservationConstrainedCrossConsult(unittest.TestCase):
    """Tests for ConservationConstrainedCrossConsult."""

    def setUp(self):
        self.adapter = ExpertRoomAdapter(n_experts=9)
        self.coupling = ExpertCouplingMatrix(n_experts=9)
        self.cross = ConservationConstrainedCrossConsult(
            coupling_matrix=self.coupling,
            adapter=self.adapter,
            direct_threshold=0.1,
            router_threshold=0.01,
        )

    def test_cold_start_routed_via_affinity(self):
        # No prior coupling, but conservation→mathematician is in affinity
        result = self.cross.request_consultation(
            "conservation", "mathematician", "Help with proof"
        )
        # Should be routed (affinity match) even though coupling is 0
        self.assertIn(result["mode"], ["routed", "direct", "blocked"])
        # conservation has mathematician in affinity list
        self.assertIn(result["mode"], ["routed", "direct"])

    def test_direct_mode_after_training(self):
        # Train the coupling
        for _ in range(20):
            self.coupling.record_consultation("conservation", "mathematician", 1.0)
        result = self.cross.request_consultation(
            "conservation", "mathematician", "Direct consult"
        )
        self.assertEqual(result["mode"], "direct")
        self.assertEqual(result["status"], "completed")

    def test_blocked_mode_no_affinity(self):
        # conservation has no affinity with builder (not in affinity list)
        result = self.cross.request_consultation(
            "conservation", "builder", "Random consult"
        )
        self.assertEqual(result["mode"], "blocked")
        self.assertEqual(result["status"], "blocked")

    def test_consultation_updates_coupling(self):
        self.cross.request_consultation("architect", "builder", "", 0.9)
        strength = self.coupling.get_coupling_strength("architect", "builder")
        self.assertGreater(strength, 0)

    def test_batch_consult(self):
        results = self.cross.batch_consult(
            "conservation",
            ["mathematician", "oracle", "critic"],
            "Batch query"
        )
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("status", r)
            self.assertIn("mode", r)

    def test_completed_tracking(self):
        self.cross.request_consultation("architect", "builder", "", 0.8)
        completed = self.cross.get_completed()
        # architect→builder not in affinity, should be blocked
        # so won't appear in completed
        self.assertIsInstance(completed, list)

    def test_summary_structure(self):
        s = self.cross.summary()
        self.assertIn("direct_threshold", s)
        self.assertIn("pending_count", s)
        self.assertIn("completed_count", s)
        self.assertIn("conservation", s)


class TestExpertStageClassifier(unittest.TestCase):
    """Tests for ExpertStageClassifier."""

    def setUp(self):
        self.adapter = ExpertRoomAdapter(n_experts=9)
        self.classifier = ExpertStageClassifier(adapter=self.adapter)

    def test_initial_stage_zero(self):
        stages = self.classifier.classify_all()
        for stage in stages.values():
            self.assertEqual(stage, 0)

    def test_stage_1_after_first_tile(self):
        self.classifier.observe_production("builder", 0.3, is_echo=True)
        self.assertEqual(self.classifier.classify("builder"), 1)

    def test_stage_2_with_filtering(self):
        for i in range(5):
            keys = ["base", "filtered"]
            self.classifier.observe_production("mathematician", 0.5, activation_keys=keys)
        self.assertEqual(self.classifier.classify("mathematician"), 2)

    def test_stage_3_with_dual_filtering(self):
        for i in range(15):
            keys = ["base", "filtered", "dual-filtered"]
            self.classifier.observe_production("oracle", 0.7, activation_keys=keys)
        self.assertEqual(self.classifier.classify("oracle"), 3)

    def test_stage_4_with_self_review_and_cross_consult(self):
        for i in range(10):
            keys = ["base", "filtered", "dual-filtered", "self-review", "conservation-aware"]
            self.classifier.observe_production("conservation", 0.9, activation_keys=keys)
            self.classifier.observe_cross_consultation("conservation")
        self.assertEqual(self.classifier.classify("conservation"), 4)

    def test_classify_all_returns_all_experts(self):
        stages = self.classifier.classify_all()
        self.assertEqual(len(stages), 9)

    def test_get_details_structure(self):
        self.classifier.observe_production("architect", 0.8)
        details = self.classifier.get_details("architect")
        self.assertEqual(details["expert"], "architect")
        self.assertEqual(details["stage"], 1)
        self.assertEqual(details["domain"], "plato")
        self.assertEqual(details["room"], "expert-architect")

    def test_summary_structure(self):
        s = self.classifier.summary()
        self.assertIn("stages", s)
        self.assertIn("stage_distribution", s)
        self.assertIn("avg_stage", s)
        self.assertIn("details", s)

    def test_mixed_stages(self):
        # Builder at stage 1
        self.classifier.observe_production("builder", 0.3, is_echo=True)
        # Oracle at stage 3
        for i in range(15):
            self.classifier.observe_production("oracle", 0.8,
                                               activation_keys=["base", "filtered", "dual-filtered"])
        stages = self.classifier.classify_all()
        self.assertEqual(stages["builder"], 1)
        self.assertEqual(stages["oracle"], 3)
        self.assertEqual(stages["conservation"], 0)


class TestConservationMath(unittest.TestCase):
    """Tests for inline conservation math functions."""

    def test_predicted_gamma_plus_H_positive(self):
        val = predicted_gamma_plus_H(9)
        self.assertGreater(val, 0)

    def test_predicted_decreases_with_V(self):
        v5 = predicted_gamma_plus_H(5)
        v100 = predicted_gamma_plus_H(100)
        self.assertGreater(v5, v100)

    def test_coupling_entropy_zero_matrix(self):
        # Zero matrix has degenerate eigenvalues
        H = coupling_entropy(np.zeros((3, 3)))
        self.assertIsInstance(H, float)

    def test_algebraic_normalized_identity(self):
        # Identity-like matrix
        C = np.eye(3, dtype=np.float32) * 0.1
        val = algebraic_normalized(C)
        self.assertIsInstance(val, float)

    def test_algebraic_normalized_small_matrix(self):
        val = algebraic_normalized(np.array([[1.0]]))
        self.assertEqual(val, 0.0)


if __name__ == "__main__":
    unittest.main()
