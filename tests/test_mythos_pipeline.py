#!/usr/bin/env python3
"""Tests for MythosTile integration across all services.

Tests:
  1-7:   MythosPipeline core methods
  8-12:  MythosTile ↔ fleet_hebbian_service integration
  13-17: MythosTile ↔ expert_hebbian_bridge integration
  18-22: MythosTile ↔ fleet_translator_v2 integration
  23-27: End-to-end pipeline: expert → Hebbian → PLATO → translate
"""
import json
import math
import sys
import os
import time
import unittest

# Ensure workspace is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mythos_tile import MythosTile, MythosPipeline, ModelTier, TileLifecycle


# =========================================================================
# 1. MythosPipeline core tests
# =========================================================================

class TestMythosPipelineCore(unittest.TestCase):
    """Tests for MythosPipeline class."""

    def test_01_accept_expert_output(self):
        """accept_expert_output produces a valid MythosTile."""
        pipe = MythosPipeline()
        tile = pipe.accept_expert_output("mathematician", {
            "domain": "math",
            "output": "Norm of 3+2ω is 7",
            "confidence": 0.95,
            "tags": ["eisenstein", "norm"],
            "meta": {},
        })
        self.assertIsInstance(tile, MythosTile)
        self.assertEqual(tile.source, "mathematician")
        self.assertEqual(tile.domain, "math")
        self.assertEqual(tile.content, "Norm of 3+2ω is 7")
        self.assertAlmostEqual(tile.confidence, 0.95)
        self.assertIn("eisenstein", tile.tags)

    def test_02_route_to_plato(self):
        """route_to_plato returns PLATO-compatible dict."""
        pipe = MythosPipeline()
        tile = pipe.accept_expert_output("oracle", {
            "domain": "reasoning",
            "output": "Predicted convergence at step 42",
            "confidence": 0.88,
        })
        plato = pipe.route_to_plato(tile)
        self.assertEqual(plato["domain"], "reasoning")
        self.assertEqual(plato["question"], "Predicted convergence at step 42")
        self.assertIn("_meta", plato)
        self.assertEqual(plato["_meta"]["tile_id"], tile.tile_id)

    def test_03_track_hebbian(self):
        """track_hebbian returns Hebbian flow event dict."""
        pipe = MythosPipeline()
        tile = MythosTile(
            domain="math", source="forgemaster", content="test",
            confidence=0.9, room="forge"
        )
        hebbian = pipe.track_hebbian(tile)
        self.assertEqual(hebbian["source_room"], "forge")
        self.assertEqual(hebbian["domain"], "math")
        self.assertAlmostEqual(hebbian["confidence"], 0.9)
        self.assertEqual(hebbian["tile_id"], tile.tile_id)

    def test_04_check_conservation_pass(self):
        """check_conservation returns True for balanced tiles."""
        pipe = MythosPipeline()
        tiles = [
            MythosTile(domain="a", source="x", content="t1", confidence=0.7),
            MythosTile(domain="b", source="y", content="t2", confidence=0.6),
            MythosTile(domain="c", source="z", content="t3", confidence=0.8),
        ]
        self.assertTrue(pipe.check_conservation(tiles))

    def test_05_check_conservation_fail_dominant(self):
        """check_conservation returns False when one tile dominates."""
        pipe = MythosPipeline()
        tiles = [
            MythosTile(domain="a", source="x", content="t1", confidence=0.95),
            MythosTile(domain="b", source="y", content="t2", confidence=0.05),
        ]
        # 0.95 / 1.0 = 0.95 > 0.8 → dominated
        self.assertFalse(pipe.check_conservation(tiles))

    def test_06_check_conservation_empty(self):
        """check_conservation returns True for empty list."""
        pipe = MythosPipeline()
        self.assertTrue(pipe.check_conservation([]))

    def test_07_translate_for_model_tiers(self):
        """translate_for_model returns correct format for each tier."""
        pipe = MythosPipeline()
        tile = MythosTile(
            domain="math", source="forgemaster",
            content="Compute f(a,b) = a² − ab + b²",
            confidence=0.9, activation_key="Eisenstein norm"
        )

        # Tier 1: direct
        t1 = pipe.translate_for_model(tile, 1)
        self.assertEqual(t1, "Compute f(a,b) = a² − ab + b²")

        # Tier 2: scaffolded
        t2 = pipe.translate_for_model(tile, 2)
        self.assertIn("Eisenstein norm", t2)

        # Tier 3: incompetent
        t3 = pipe.translate_for_model(tile, 3)
        self.assertIn("Compute:", t3)

    def test_07b_batch_operations(self):
        """Batch operations work correctly."""
        pipe = MythosPipeline()
        tiles = pipe.batch_accept([
            ("expert1", {"domain": "a", "output": "out1", "confidence": 0.8}),
            ("expert2", {"domain": "b", "output": "out2", "confidence": 0.7}),
        ])
        self.assertEqual(len(tiles), 2)

        platos = pipe.batch_route_to_plato()
        self.assertEqual(len(platos), 2)

        hebbians = pipe.batch_track_hebbian()
        self.assertEqual(len(hebbians), 2)

        translations = pipe.batch_translate(tier=1)
        self.assertEqual(len(translations), 2)

    def test_07c_get_by_expert(self):
        """get_by_expert returns the most recent tile from an expert."""
        pipe = MythosPipeline()
        pipe.accept_expert_output("math", {"domain": "math", "output": "old", "confidence": 0.5})
        pipe.accept_expert_output("math", {"domain": "math", "output": "new", "confidence": 0.9})

        tile = pipe.get_by_expert("math")
        self.assertIsNotNone(tile)
        self.assertEqual(tile.content, "new")

    def test_07d_pipeline_summary(self):
        """Pipeline summary contains expected fields."""
        pipe = MythosPipeline()
        pipe.accept_expert_output("oracle", {"domain": "r", "output": "x", "confidence": 0.8})
        pipe.accept_expert_output("math", {"domain": "math", "output": "y", "confidence": 0.7})
        summary = pipe.summary()
        self.assertEqual(summary["total_tiles"], 2)
        self.assertIn("oracle", summary["experts"])
        self.assertTrue(summary["conservation_ok"])


# =========================================================================
# 2. MythosTile ↔ fleet_hebbian_service integration
# =========================================================================

class TestHebbianMythosIntegration(unittest.TestCase):
    """Tests for MythosTile integration with FleetHebbianService."""

    @classmethod
    def setUpClass(cls):
        """Boot a FleetHebbianService with in-memory DB."""
        from fleet_hebbian_service import FleetHebbianService
        cls.svc = FleetHebbianService(db_path="/tmp/test_plato_mythos.db", port=0)
        # Calibrate with minimal steps
        cls.svc.auto_calibrate(50)

    def test_08_submit_mythos_tile(self):
        """submit_mythos_tile routes a MythosTile correctly."""
        tile = MythosTile(
            domain="math", source="forgemaster",
            content="Eisenstein norm test",
            confidence=0.85, room="forge",
            content_type="model",
        )
        result = self.svc.submit_mythos_tile(tile)
        self.assertIn("mythos_tile_id", result)
        self.assertEqual(result["mythos_domain"], "math")
        self.assertGreater(result["total_routed"], 0)

    def test_09_mythos_tile_backward_compat(self):
        """POST /tile dict API still works after MythosTile integration."""
        result = self.svc.submit_tile(
            tile_type="model", source_room="forge",
            confidence=0.9,
        )
        self.assertIn("tile_type", result)
        self.assertIn("destinations", result)

    def test_10_mythos_tile_id_in_flow(self):
        """MythosTile tile_id appears in flow events."""
        tile = MythosTile(
            domain="constraint", source="forgemaster",
            content="conservation check",
            confidence=0.9, room="forge",
            content_type="benchmark",
        )
        self.svc.submit_mythos_tile(tile)
        event = self.svc.get_mythos_tile(tile.tile_id)
        self.assertIsNotNone(event)
        self.assertEqual(event["tile_hash"], tile.tile_id)

    def test_11_mythos_tile_not_found(self):
        """get_mythos_tile returns None for unknown IDs."""
        event = self.svc.get_mythos_tile("nonexistent_id_12345")
        self.assertIsNone(event)

    def test_12_mythos_plato_roundtrip(self):
        """MythosTile → PLATO format → MythosTile roundtrip."""
        tile = MythosTile(
            domain="math", source="oracle1",
            content="What is norm of 3+2ω?",
            confidence=0.88, room="agent-oracle1",
            tags=["eisenstein"], meta={"answer": "7"},
        )
        plato = tile.to_plato_format()
        restored = MythosTile.from_plato_tile(plato)
        self.assertEqual(restored.domain, tile.domain)
        self.assertEqual(restored.content, tile.content)
        self.assertEqual(restored.room, tile.room)


# =========================================================================
# 3. MythosTile ↔ expert_hebbian_bridge integration
# =========================================================================

class TestExpertMythosIntegration(unittest.TestCase):
    """Tests for MythosTile integration with ExpertHebbianBridge."""

    def setUp(self):
        from expert_hebbian_bridge import (
            ExpertRoomAdapter, ExpertCouplingMatrix,
            ConservationConstrainedCrossConsult,
        )
        self.adapter = ExpertRoomAdapter(n_experts=9)
        self.coupling = ExpertCouplingMatrix(n_experts=9)
        self.cross_consult = ConservationConstrainedCrossConsult(
            coupling_matrix=self.coupling, adapter=self.adapter,
        )

    def test_13_convert_to_mythos_tile(self):
        """convert_to_mythos_tile produces a MythosTile."""
        tile = self.adapter.convert_to_mythos_tile(
            "mathematician", "The answer is 42", 0.95
        )
        self.assertIsInstance(tile, MythosTile)
        self.assertEqual(tile.source, "mathematician")
        self.assertEqual(tile.content, "The answer is 42")
        self.assertAlmostEqual(tile.confidence, 0.95)

    def test_14_mythos_tile_has_correct_room(self):
        """MythosTile from adapter has correct room mapping."""
        tile = self.adapter.convert_to_mythos_tile(
            "conservation", "γ+H is conserved", 0.9
        )
        self.assertEqual(tile.room, "expert-conservation")

    def test_15_mythos_tile_has_correct_domain(self):
        """MythosTile from adapter has correct domain."""
        tile = self.adapter.convert_to_mythos_tile(
            "architect", "Room layout plan", 0.8
        )
        self.assertEqual(tile.domain, "plato")

    def test_16_cross_consult_produces_mythos(self):
        """Cross-consultation produces MythosTile in result."""
        result = self.cross_consult.request_consultation(
            "conservation", "mathematician",
            query="Check norm calculation",
            confidence=0.9,
        )
        self.assertIn("mythos_tile", result)
        self.assertIn("mythos_tile_id", result)

    def test_17_backward_compat_convert_tile(self):
        """convert_tile (dict-based) still works alongside MythosTile."""
        result = self.adapter.convert_tile(
            "builder", "code output", 0.85
        )
        self.assertIsInstance(result, dict)
        self.assertIn("room", result)
        self.assertEqual(result["expert_type"], "builder")


# =========================================================================
# 4. MythosTile ↔ fleet_translator_v2 integration
# =========================================================================

class TestTranslatorMythosIntegration(unittest.TestCase):
    """Tests for MythosTile integration with FleetTranslatorV2."""

    def test_18_mythos_tile_format_tier1(self):
        """MythosTile.format_for_model(TIER_1) returns raw content."""
        tile = MythosTile(
            domain="math", source="forgemaster",
            content="Compute Eisenstein norm of (3, -3)",
            confidence=0.95, activation_key="Eisenstein norm",
        )
        result = tile.format_for_model(ModelTier.TIER_1_DIRECT)
        self.assertEqual(result, "Compute Eisenstein norm of (3, -3)")

    def test_19_mythos_tile_format_tier2(self):
        """MythosTile.format_for_model(TIER_2) includes activation key."""
        tile = MythosTile(
            domain="math", source="forgemaster",
            content="Compute f(a,b) = a² − ab + b²",
            confidence=0.85, activation_key="Eisenstein norm",
        )
        result = tile.format_for_model(ModelTier.TIER_2_SCAFFOLDED)
        self.assertIn("Eisenstein norm", result)
        self.assertIn("Compute", result)

    def test_20_mythos_tile_format_tier3(self):
        """MythosTile.format_for_model(TIER_3) falls back to compute prompt."""
        tile = MythosTile(
            domain="math", source="forgemaster",
            content="f(a,b) = a² − ab + b² where a=3, b=-3",
            confidence=0.8,
            meta={},  # no "answer" key
        )
        result = tile.format_for_model(ModelTier.TIER_3_INCOMPETENT)
        self.assertIn("Compute:", result)

    def test_21_pipeline_translate_integration(self):
        """MythosPipeline.translate_for_model uses correct tier."""
        pipe = MythosPipeline()
        tile = pipe.accept_expert_output("mathematician", {
            "domain": "math",
            "output": "Compute Eisenstein norm of (5, -3)",
            "confidence": 0.9,
            "tags": ["norm"],
            "meta": {},
        })
        # Tier 1: raw
        t1 = pipe.translate_for_model(tile, 1)
        self.assertNotIn("Using", t1)

        # Tier 2: scaffolded — needs activation_key set on tile
        tile.activation_key = "Eisenstein norm"
        t2 = pipe.translate_for_model(tile, 2)
        self.assertIn("Eisenstein norm", t2)

    def test_22_translator_stage_matches_mythos_tier(self):
        """ModelTier enum aligns with translator stages."""
        # Tier 1 = Stage 4 (FULL) — direct passthrough
        # Tier 2 = Stage 3 (CAPABLE) — scaffolded
        # Tier 3 = Stage 1-2 — bare arithmetic
        self.assertEqual(ModelTier.TIER_1_DIRECT, 1)
        self.assertEqual(ModelTier.TIER_2_SCAFFOLDED, 2)
        self.assertEqual(ModelTier.TIER_3_INCOMPETENT, 3)


# =========================================================================
# 5. End-to-end pipeline tests
# =========================================================================

class TestEndToEndPipeline(unittest.TestCase):
    """Full pipeline: expert → MythosTile → PLATO → Hebbian → translate."""

    def test_23_full_pipeline_flow(self):
        """Expert output flows through entire pipeline."""
        pipe = MythosPipeline()

        # Step 1: Accept expert output
        tile = pipe.accept_expert_output("mathematician", {
            "domain": "math",
            "output": "The Eisenstein norm of (5, -3) is 49",
            "confidence": 0.92,
            "tags": ["eisenstein", "norm"],
            "meta": {"answer": "49"},
        })

        # Step 2: Route to PLATO
        plato = pipe.route_to_plato(tile)
        self.assertEqual(plato["domain"], "math")
        self.assertEqual(plato["answer"], "49")

        # Step 3: Track Hebbian
        hebbian = pipe.track_hebbian(tile)
        self.assertIsNotNone(hebbian["tile_id"])

        # Step 4: Check conservation (need multiple tiles for meaningful check)
        pipe.accept_expert_output("oracle", {
            "domain": "reasoning",
            "output": "Cross-check: norm is correct",
            "confidence": 0.85,
        })
        self.assertTrue(pipe.check_conservation())

        # Step 5: Translate
        t1 = pipe.translate_for_model(tile, 1)
        self.assertIn("49", t1)  # Tier 1: raw content

    def test_24_multi_expert_conservation(self):
        """Multiple experts flowing through pipeline respects conservation."""
        pipe = MythosPipeline()

        experts = [
            ("conservation", "math", 0.9),
            ("architect", "plato", 0.85),
            ("mathematician", "math", 0.88),
            ("synthesist", "cross-domain", 0.75),
            ("critic", "review", 0.7),
        ]

        for expert, domain, conf in experts:
            pipe.accept_expert_output(expert, {
                "domain": domain,
                "output": f"Output from {expert}",
                "confidence": conf,
                "tags": [expert],
                "meta": {},
            })

        # Conservation check — no single expert dominates
        self.assertTrue(pipe.check_conservation())

        # All tiles route to PLATO
        platos = pipe.batch_route_to_plato()
        self.assertEqual(len(platos), 5)

    def test_25_mythos_json_roundtrip(self):
        """MythosTile survives JSON serialization roundtrip."""
        tile = MythosTile(
            domain="math", source="forgemaster",
            content="Eisenstein norm of (3+2ω)",
            confidence=0.95, room="forge",
            activation_key="Eisenstein norm",
            tags=["eisenstein", "norm"],
            meta={"answer": "7", "method": "algebraic"},
        )

        j = tile.to_json()
        restored = MythosTile.from_json(j)

        self.assertEqual(restored.tile_id, tile.tile_id)
        self.assertEqual(restored.content, tile.content)
        self.assertEqual(restored.domain, tile.domain)
        self.assertAlmostEqual(restored.confidence, tile.confidence)
        self.assertEqual(restored.tags, tile.tags)
        self.assertEqual(restored.meta["answer"], "7")

    def test_26_expert_output_to_all_formats(self):
        """Expert output converts to PLATO, Hebbian, and expert formats."""
        tile = MythosTile.from_expert_output("oracle", {
            "domain": "reasoning",
            "output": "Convergence predicted at step 42",
            "confidence": 0.88,
            "tags": ["prediction"],
            "meta": {"step": 42},
        })

        # PLATO format
        plato = tile.to_plato_format()
        self.assertEqual(plato["domain"], "reasoning")

        # Hebbian event
        hebbian = tile.to_hebbian_event()
        self.assertEqual(hebbian["tile_id"], tile.tile_id)

        # Expert output
        expert = tile.to_expert_output()
        self.assertEqual(expert["expert"], "oracle")
        self.assertEqual(expert["output"], "Convergence predicted at step 42")

    def test_27_lifecycle_states(self):
        """MythosTile lifecycle transitions work."""
        tile = MythosTile(domain="test", source="test", content="lifecycle test")
        self.assertEqual(tile.lifecycle, TileLifecycle.ACTIVE)

        tile.lifecycle = TileLifecycle.SUPERSEDED
        self.assertEqual(tile.lifecycle, "superseded")

        tile.lifecycle = TileLifecycle.RETRACTED
        self.assertEqual(tile.lifecycle, "retracted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
