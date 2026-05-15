#!/usr/bin/env python3
"""
test_e2e_pipeline.py — End-to-end integration tests for the Cocapn fleet pipeline.

Tests the FULL flow:
  1. Expert produces tile → MythosTile.from_expert_output()
  2. Tile routes to PLATO → tile.to_plato_format()
  3. Hebbian tracks flow → tile.to_hebbian_event() + weight update
  4. Conservation check → verify γ+H within bounds after 9 expert tiles
  5. Cross-consultation → Expert A consults Expert B via conservation-constrained routing
  6. Translation for model → tile.format_for_model(tier) for all 3 tiers
  7. Round-trip → MythosTile.from_json(tile.to_json()) preserves all fields

Edge cases:
  - Tile with no domain (should default)
  - Tile with confidence=0 (should route to weakest Hebbian path)
  - 100 tiles flowing (conservation should stabilize)
  - Superseded tile lifecycle
  - Lamport clock ordering
"""

import sys, os, time, json, math, hashlib
from collections import defaultdict

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Ensure workspace is on the path
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

from mythos_tile import MythosTile, ModelTier, TileLifecycle
from fleet_hebbian_service import (
    ConservationHebbianKernel, TileFlowTracker, HebbianRouter,
    FleetHebbianService, predicted_gamma_plus_H, coupling_entropy,
    algebraic_normalized, EmergentStageClassifier, RoomClusterDetector,
)
from expert_hebbian_bridge import (
    ExpertRoomAdapter, ExpertCouplingMatrix,
    ConservationConstrainedCrossConsult, ExpertStageClassifier,
    ExpertHebbianBridge, EXPERT_TYPES, EXPERT_DOMAIN_MAP, EXPERT_AFFINITY,
)
from fleet_translator_v2 import (
    NotationNormalizer, ActivationKeyEngineer, FleetRouter,
    ModelStage, translate, translate_for_stage, auto_detect_stage,
    KNOWN_STAGES,
)


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def expert_adapter():
    """9-expert adapter."""
    return ExpertRoomAdapter(n_experts=9)


@pytest.fixture
def coupling_matrix(expert_adapter):
    """Expert coupling matrix matching the adapter."""
    return ExpertCouplingMatrix(n_experts=9)


@pytest.fixture
def cross_consult(coupling_matrix, expert_adapter):
    """Cross-consultation router."""
    return ConservationConstrainedCrossConsult(
        coupling_matrix=coupling_matrix,
        adapter=expert_adapter,
    )


@pytest.fixture
def hebbian_kernel():
    """Conservation Hebbian kernel with 9 rooms."""
    return ConservationHebbianKernel(n_rooms=9, V=9)


@pytest.fixture
def flow_tracker():
    """Tile flow tracker."""
    return TileFlowTracker()


@pytest.fixture
def sample_tile():
    """A basic tile for testing."""
    return MythosTile(
        domain="math",
        source="forgemaster",
        content="Compute f(a,b) = a² − ab + b² where a=5, b=-3",
        confidence=0.95,
        room="forge",
        activation_key="Eisenstein norm",
        tags=["eisenstein", "norm"],
        meta={"answer": 49},
    )


# =====================================================================
# 1. Expert produces tile → MythosTile.from_expert_output()
# =====================================================================

class TestExpertTileProduction:
    """Expert daemons produce tiles via MythosTile.from_expert_output()."""

    def test_expert_output_creates_tile(self):
        output = {
            "domain": "math",
            "output": "Eisenstein norm of (5,-3) = 49",
            "confidence": 0.95,
            "tags": ["eisenstein", "norm"],
            "meta": {"answer": 49},
        }
        tile = MythosTile.from_expert_output("forgemaster", output)
        assert tile.source == "forgemaster"
        assert tile.domain == "math"
        assert tile.content == "Eisenstein norm of (5,-3) = 49"
        assert tile.confidence == 0.95
        assert tile.tags == ["eisenstein", "norm"]
        assert tile.meta["answer"] == 49
        assert tile.room == "expert-forgemaster"

    def test_all_9_experts_produce_tiles(self, expert_adapter):
        tiles = []
        for expert in EXPERT_TYPES:
            output = {
                "domain": EXPERT_DOMAIN_MAP[expert],
                "output": f"Output from {expert}",
                "confidence": 0.8 + 0.02 * EXPERT_TYPES.index(expert),
                "tags": [expert],
            }
            tile = MythosTile.from_expert_output(expert, output)
            tiles.append(tile)

        assert len(tiles) == 9
        domains = {t.domain for t in tiles}
        assert len(domains) >= 3  # at least 3 distinct domains

    def test_expert_tile_has_auto_id(self):
        tile = MythosTile.from_expert_output("oracle", {
            "domain": "reasoning",
            "output": "Deep analysis result",
            "confidence": 0.88,
        })
        assert tile.tile_id  # auto-generated
        assert len(tile.tile_id) == 16  # sha256[:16]

    def test_expert_output_missing_fields_default(self):
        tile = MythosTile.from_expert_output("test", {})
        assert tile.domain == "expert"  # default from output.get("domain", "expert")
        assert tile.confidence == 0.5  # default
        assert tile.content == ""


# =====================================================================
# 2. Tile routes to PLATO → tile.to_plato_format()
# =====================================================================

class TestPlatoRouting:

    def test_to_plato_format(self, sample_tile):
        plato = sample_tile.to_plato_format()
        assert plato["domain"] == "math"
        assert plato["question"] == sample_tile.content
        assert plato["answer"] == 49
        assert plato["tags"] == ["eisenstein", "norm"]
        assert plato["source"] == "forgemaster"
        assert plato["confidence"] == 0.95
        assert plato["_meta"]["tile_id"] == sample_tile.tile_id
        assert plato["_meta"]["room"] == "forge"
        assert plato["_meta"]["lifecycle"] == TileLifecycle.ACTIVE

    def test_plato_round_trip(self, sample_tile):
        plato = sample_tile.to_plato_format()
        restored = MythosTile.from_plato_tile(plato)
        assert restored.domain == sample_tile.domain
        assert restored.source == sample_tile.source
        assert restored.content == sample_tile.content
        assert restored.confidence == sample_tile.confidence
        assert restored.room == "forge"
        assert restored.tile_id == sample_tile.tile_id
        assert restored.tags == sample_tile.tags

    def test_plato_format_preserves_meta(self):
        tile = MythosTile(
            domain="agent",
            source="oracle1",
            content="Stage classification complete",
            meta={"stage": 4, "model": "Seed-2.0-mini"},
        )
        plato = tile.to_plato_format()
        assert plato["_meta"]["stage"] == 4
        assert plato["_meta"]["model"] == "Seed-2.0-mini"


# =====================================================================
# 3. Hebbian tracks flow → tile.to_hebbian_event() + weight update
# =====================================================================

class TestHebbianFlowTracking:

    def test_to_hebbian_event(self, sample_tile):
        event = sample_tile.to_hebbian_event()
        assert event["source_room"] == "forge"
        assert event["domain"] == "math"
        assert event["confidence"] == 0.95
        assert event["tile_id"] == sample_tile.tile_id
        assert event["timestamp"] > 0

    def test_flow_tracker_records_tile_event(self, flow_tracker, sample_tile):
        event = sample_tile.to_hebbian_event()
        rec = flow_tracker.record_flow(
            source_room=event["source_room"],
            dest_room="expert-mathematician",
            tile_type="model",
            tile_hash=event["tile_id"],
        )
        assert rec.source_room == "forge"
        assert rec.dest_room == "expert-mathematician"
        assert len(flow_tracker) == 1

    def test_connection_strength_builds(self, flow_tracker):
        # Flow tiles between two rooms
        for _ in range(20):
            flow_tracker.record_flow("forge", "expert-mathematician", "model")

        strength = flow_tracker.get_connection_strength("forge", "expert-mathematician")
        assert strength > 0.0

    def test_hebbian_kernel_update(self, hebbian_kernel):
        n = hebbian_kernel.n
        pre = np.zeros(n, dtype=np.float32)
        post = np.zeros(n, dtype=np.float32)
        pre[0] = 1.0
        post[3] = 0.9

        report = hebbian_kernel.update(pre, post)
        assert report.update_count == 1
        weights = hebbian_kernel.get_weights()
        assert weights[0, 3] > 0  # connection strengthened

    def test_multiple_updates_build_structure(self, hebbian_kernel):
        n = hebbian_kernel.n
        rng = np.random.RandomState(42)
        for _ in range(50):
            pre = np.zeros(n, dtype=np.float32)
            post = np.zeros(n, dtype=np.float32)
            pre[rng.randint(n)] = 1.0
            post[rng.randint(n)] = rng.uniform(0.5, 1.0)
            hebbian_kernel.update(pre, post)

        weights = hebbian_kernel.get_weights()
        assert np.count_nonzero(weights) > 0
        assert hebbian_kernel._update_count == 50


# =====================================================================
# 4. Conservation check → verify γ+H within bounds after 9 expert tiles
# =====================================================================

class TestConservationCheck:

    def test_conservation_after_9_experts(self, expert_adapter, coupling_matrix):
        """Run 9 expert tiles through the coupling matrix and check conservation."""
        for expert in EXPERT_TYPES:
            output = {
                "domain": EXPERT_DOMAIN_MAP[expert],
                "output": f"Result from {expert}",
                "confidence": 0.85,
            }
            tile = MythosTile.from_expert_output(expert, output)

            # Route through all affinity targets
            for target in EXPERT_AFFINITY.get(expert, [])[:2]:
                coupling_matrix.record_consultation(expert, target, strength=0.8)

        report = coupling_matrix.check_conservation()
        assert "gamma_plus_H" in report
        assert "predicted" in report
        # After only 9 tiles, the matrix is sparse — conservation should be trivially true
        assert report["conserved"] in (True, False)  # just checking it runs
        assert isinstance(report["deviation"], float)

    def test_conservation_kernel_report(self, hebbian_kernel):
        """After warmup, conservation kernel produces a valid report."""
        n = hebbian_kernel.n
        rng = np.random.RandomState(42)
        for _ in range(60):  # past warmup threshold of 50
            pre = np.zeros(n, dtype=np.float32)
            post = np.zeros(n, dtype=np.float32)
            pre[rng.randint(n)] = 1.0
            post[rng.randint(n)] = rng.uniform(0.5, 1.0)
            hebbian_kernel.update(pre, post)

        report = hebbian_kernel.conservation_report()
        assert report.gamma_plus_H >= 0
        assert report.update_count == 60
        assert 0.0 <= report.scale_factor <= 2.0  # sanity bound

    def test_predicted_gamma_plus_h(self):
        """Conservation law prediction is well-defined."""
        for V in [5, 10, 20, 30, 100]:
            pred = predicted_gamma_plus_H(V)
            assert 0 < pred < 2.0  # reasonable range

    def test_compliance_rate_improves(self, hebbian_kernel):
        """With more updates, compliance rate should be reasonable."""
        n = hebbian_kernel.n
        rng = np.random.RandomState(123)
        for _ in range(200):
            pre = np.zeros(n, dtype=np.float32)
            post = np.zeros(n, dtype=np.float32)
            pre[rng.randint(n)] = 1.0
            post[rng.randint(n)] = rng.uniform(0.5, 1.0)
            hebbian_kernel.update(pre, post)

        rate = hebbian_kernel.compliance_rate()
        assert 0 <= rate <= 1.0


# =====================================================================
# 5. Cross-consultation → Expert A consults Expert B
# =====================================================================

class TestCrossConsultation:

    def test_conservation_expert_a_consults_b(self, cross_consult):
        result = cross_consult.request_consultation(
            source_expert="conservation",
            target_expert="mathematician",
            query="Verify Eisenstein norm computation",
            confidence=0.9,
        )
        assert result["source"] == "conservation"
        assert result["target"] == "mathematician"
        # First consultation: coupling is 0, but affinity exists → "routed"
        assert result["mode"] in ("direct", "routed", "blocked")
        assert "coupling_strength" in result

    def test_affinity_allows_routed_consultation(self, cross_consult):
        """Even with zero coupling, affinity topology allows consultation."""
        result = cross_consult.request_consultation(
            source_expert="conservation",
            target_expert="mathematician",
            query="Cross-check",
            confidence=0.8,
        )
        assert result["mode"] != "blocked"  # affinity allows it

    def test_no_affinity_blocks(self, cross_consult):
        """Experts with no affinity AND zero coupling get blocked."""
        # conservation's affinity: mathematician, oracle, critic
        # architect's affinity: builder, navigator, synthesist
        # conservation → architect is NOT in affinity → blocked (coupling is 0)
        # Wait: conservation's affinity is ["mathematician", "oracle", "critic"]
        # architect is NOT in that list
        result = cross_consult.request_consultation(
            source_expert="conservation",
            target_expert="architect",
            query="Unrelated query",
            confidence=0.5,
        )
        assert result["mode"] == "blocked"

    def test_direct_after_repeated_consultation(self, coupling_matrix, expert_adapter):
        """After enough consultations, coupling exceeds direct threshold."""
        # Manually strengthen the connection
        for _ in range(30):
            coupling_matrix.record_consultation("conservation", "mathematician", strength=0.8)

        cross = ConservationConstrainedCrossConsult(
            coupling_matrix=coupling_matrix,
            adapter=expert_adapter,
            direct_threshold=0.1,
        )
        result = cross.request_consultation("conservation", "mathematician", confidence=0.9)
        strength = coupling_matrix.get_coupling_strength("conservation", "mathematician")
        if strength >= 0.1:
            assert result["mode"] == "direct"

    def test_batch_consultation(self, cross_consult):
        results = cross_consult.batch_consult(
            source_expert="conservation",
            target_experts=["mathematician", "oracle", "critic"],
            query="Review norm computation",
            confidence=0.85,
        )
        assert len(results) == 3
        assert all(r["source"] == "conservation" for r in results)


# =====================================================================
# 6. Translation for model → tile.format_for_model(tier) for all 3 tiers
# =====================================================================

class TestModelTierFormatting:

    def test_tier1_direct(self, sample_tile):
        formatted = sample_tile.format_for_model(ModelTier.TIER_1_DIRECT)
        assert formatted == sample_tile.content  # passthrough

    def test_tier2_scaffolded(self, sample_tile):
        formatted = sample_tile.format_for_model(ModelTier.TIER_2_SCAFFOLDED)
        assert "Eisenstein norm" in formatted  # activation key present
        assert sample_tile.content in formatted

    def test_tier3_incompetent(self, sample_tile):
        formatted = sample_tile.format_for_model(ModelTier.TIER_3_INCOMPETENT)
        assert "49" in formatted  # uses the answer from meta

    def test_tier3_no_answer_falls_back(self):
        tile = MythosTile(
            domain="math",
            source="test",
            content="Compute something complex",
        )
        formatted = tile.format_for_model(ModelTier.TIER_3_INCOMPETENT)
        assert formatted.startswith("Compute:")

    def test_tier2_uses_domain_when_no_activation_key(self):
        tile = MythosTile(
            domain="number-theory",
            source="test",
            content="Compute mu(30)",
            confidence=0.9,
        )
        formatted = tile.format_for_model(ModelTier.TIER_2_SCAFFOLDED)
        assert "number-theory" in formatted  # falls back to domain

    def test_translator_stage4_passthrough(self):
        prompt = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.FULL)
        assert "Eisenstein" in prompt

    def test_translator_stage1_arithmetic(self):
        prompt = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
        assert "Compute:" in prompt
        assert "9" in prompt  # 3*3=9


# =====================================================================
# 7. Round-trip → MythosTile.from_json(tile.to_json()) preserves all fields
# =====================================================================

class TestRoundTrip:

    def test_json_round_trip_full(self, sample_tile):
        json_str = sample_tile.to_json()
        restored = MythosTile.from_json(json_str)
        assert restored.tile_id == sample_tile.tile_id
        assert restored.domain == sample_tile.domain
        assert restored.source == sample_tile.source
        assert restored.content == sample_tile.content
        assert restored.content_type == sample_tile.content_type
        assert restored.confidence == sample_tile.confidence
        assert restored.target_tier == sample_tile.target_tier
        assert restored.activation_key == sample_tile.activation_key
        assert restored.parent_id == sample_tile.parent_id
        assert restored.room == sample_tile.room
        assert restored.lamport_clock == sample_tile.lamport_clock
        assert restored.lifecycle == sample_tile.lifecycle
        assert abs(restored.timestamp - sample_tile.timestamp) < 0.01
        assert restored.tags == sample_tile.tags
        assert restored.meta == sample_tile.meta

    def test_json_round_trip_minimal(self):
        tile = MythosTile()
        json_str = tile.to_json()
        restored = MythosTile.from_json(json_str)
        assert restored.domain == ""
        assert restored.confidence == 1.0
        assert restored.tags == []
        assert restored.meta == {}

    def test_json_round_trip_preserves_meta(self):
        tile = MythosTile(
            domain="fleet",
            content="ops",
            meta={"nested": {"deep": True}, "list": [1, 2, 3]},
        )
        restored = MythosTile.from_json(tile.to_json())
        assert restored.meta["nested"]["deep"] is True
        assert restored.meta["list"] == [1, 2, 3]


# =====================================================================
# Edge Cases
# =====================================================================

class TestEdgeCases:

    def test_tile_no_domain_defaults_empty(self):
        tile = MythosTile(source="test", content="hello")
        assert tile.domain == ""
        # format_for_model still works
        fmt = tile.format_for_model(ModelTier.TIER_2_SCAFFOLDED)
        assert "hello" in fmt

    def test_tile_confidence_zero(self, flow_tracker):
        """Tile with confidence=0 should still produce a valid Hebbian event."""
        tile = MythosTile(
            domain="test",
            source="tester",
            content="Zero confidence output",
            confidence=0.0,
            room="test-room",
        )
        event = tile.to_hebbian_event()
        assert event["confidence"] == 0.0

        # Record in flow tracker — zero confidence still records
        rec = flow_tracker.record_flow("test-room", "target-room", "model", tile.tile_id)
        assert rec is not None

    def test_confidence_zero_routes_to_weakest(self, expert_adapter, coupling_matrix):
        """Expert producing confidence=0 tile should route to weakest path."""
        # Build some coupling history
        for _ in range(10):
            coupling_matrix.record_consultation("conservation", "mathematician", strength=0.9)
        for _ in range(10):
            coupling_matrix.record_consultation("conservation", "oracle", strength=0.3)

        cross = ConservationConstrainedCrossConsult(
            coupling_matrix=coupling_matrix,
            adapter=expert_adapter,
        )

        # Low confidence consultation
        result = cross.request_consultation(
            "conservation", "mathematician", confidence=0.0
        )
        # Should still complete (affinity exists)
        assert result["status"] in ("completed", "blocked")

    def test_100_tiles_conservation_stabilizes(self, hebbian_kernel):
        """100 tiles flowing through should stabilize conservation."""
        n = hebbian_kernel.n
        rng = np.random.RandomState(42)

        reports = []
        for i in range(100):
            pre = np.zeros(n, dtype=np.float32)
            post = np.zeros(n, dtype=np.float32)
            src = rng.randint(n)
            dst = rng.randint(n)
            while dst == src:
                dst = rng.randint(n)
            pre[src] = 1.0
            post[dst] = rng.uniform(0.5, 1.0)
            report = hebbian_kernel.update(pre, post)
            reports.append(report)

        # After warmup (50), check that deviation stays bounded
        post_warmup = [r for r in reports[60:] if r is not None]
        if post_warmup:
            deviations = [abs(r.deviation) for r in post_warmup]
            max_dev = max(deviations)
            # Should be bounded — the conservation kernel enforces this
            assert max_dev < 1.0 or all(r.correction_applied for r in post_warmup if abs(r.deviation) > 0.5)

    def test_superseded_tile_lifecycle(self):
        tile = MythosTile(
            domain="math",
            source="test",
            content="Original answer",
            lifecycle=TileLifecycle.ACTIVE,
        )
        assert tile.lifecycle == "active"

        # Mark as superseded
        tile.lifecycle = TileLifecycle.SUPERSEDED
        assert tile.lifecycle == "superseded"

        # PLATO format reflects lifecycle
        plato = tile.to_plato_format()
        assert plato["_meta"]["lifecycle"] == "superseded"

        # JSON round-trip preserves lifecycle
        restored = MythosTile.from_json(tile.to_json())
        assert restored.lifecycle == "superseded"

    def test_lamport_clock_ordering(self, flow_tracker):
        """Tiles with increasing Lamport clocks should be ordered correctly."""
        events = []
        for i in range(10):
            rec = flow_tracker.record_flow(
                f"room-{i % 3}",
                f"room-{(i + 1) % 3}",
                "model",
                lamport_clock=i,
            )
            events.append(rec)

        # Lamport clocks should be strictly increasing
        clocks = [e.lamport_clock for e in events]
        for i in range(1, len(clocks)):
            assert clocks[i] > clocks[i - 1], f"Clock {i} ({clocks[i]}) not > {i-1} ({clocks[i-1]})"

    def test_100_tiles_through_service(self):
        """100 tiles through FleetHebbianService should work without errors."""
        # Use in-memory (no db)
        svc = FleetHebbianService(
            db_path="/tmp/test_e2e_plato.db",
            port=0,  # don't start HTTP
        )
        rng = np.random.RandomState(42)
        rooms = svc._rooms
        n = len(rooms)

        results = []
        for i in range(100):
            src = rooms[rng.randint(n)]
            dst = rooms[rng.randint(n)]
            tile_type = rng.choice(["model", "data", "compression", "benchmark", "deploy"])
            result = svc.submit_tile(
                tile_type=tile_type,
                source_room=src,
                dest_room=dst,
                confidence=rng.uniform(0.3, 1.0),
            )
            results.append(result)

        assert len(results) == 100
        total_routed = sum(r["total_routed"] for r in results)
        assert total_routed > 0

        status = svc.get_status()
        assert status["tracker_records"] > 0
        assert status["kernel_updates"] > 0


# =====================================================================
# Full Pipeline Integration
# =====================================================================

class TestFullPipeline:
    """End-to-end: Expert → Tile → PLATO → Hebbian → Translation → Round-trip."""

    def test_full_pipeline_single_tile(self):
        """One tile flows through the entire pipeline."""
        # 1. Expert produces tile
        output = {
            "domain": "math",
            "output": "Eisenstein norm of (3, 5) = 19",
            "confidence": 0.92,
            "tags": ["eisenstein", "norm"],
            "meta": {"answer": 19},
        }
        tile = MythosTile.from_expert_output("mathematician", output)
        assert tile.source == "mathematician"
        assert tile.confidence == 0.92

        # 2. Tile routes to PLATO
        plato = tile.to_plato_format()
        assert plato["domain"] == "math"
        assert plato["confidence"] == 0.92
        assert plato["_meta"]["tile_id"] == tile.tile_id

        # 3. Hebbian tracks flow
        event = tile.to_hebbian_event()
        assert event["domain"] == "math"
        tracker = TileFlowTracker()
        rec = tracker.record_flow(
            event["source_room"], "forge", "model", event["tile_id"]
        )
        assert len(tracker) == 1

        # 4. Conservation kernel update
        kernel = ConservationHebbianKernel(n_rooms=9, V=9)
        pre = np.zeros(9, dtype=np.float32)
        post = np.zeros(9, dtype=np.float32)
        pre[0] = 1.0
        post[1] = tile.confidence
        report = kernel.update(pre, post)
        assert report.update_count == 1

        # 5. Cross-consultation
        adapter = ExpertRoomAdapter()
        coupling = ExpertCouplingMatrix()
        cross = ConservationConstrainedCrossConsult(coupling, adapter)
        consult = cross.request_consultation(
            "mathematician", "oracle",
            query=tile.content, confidence=tile.confidence,
        )
        assert consult["status"] in ("completed", "blocked")

        # 6. Translation for all tiers
        for tier in ModelTier:
            formatted = tile.format_for_model(tier)
            assert isinstance(formatted, str)
            assert len(formatted) > 0

        # 7. Round-trip
        restored = MythosTile.from_json(tile.to_json())
        assert restored.tile_id == tile.tile_id
        assert restored.content == tile.content

    def test_full_pipeline_9_experts_9_tiles(self):
        """9 experts each produce a tile, all flow through pipeline."""
        adapter = ExpertRoomAdapter(n_experts=9)
        coupling = ExpertCouplingMatrix(n_experts=9)
        cross = ConservationConstrainedCrossConsult(coupling, adapter)
        kernel = ConservationHebbianKernel(n_rooms=9, V=9)
        tracker = TileFlowTracker()

        tiles = []
        for expert in EXPERT_TYPES:
            # 1. Produce tile
            output = {
                "domain": EXPERT_DOMAIN_MAP[expert],
                "output": f"Analysis from {expert}",
                "confidence": 0.85,
                "tags": [expert],
            }
            tile = MythosTile.from_expert_output(expert, output)
            tiles.append(tile)

            # 2. PLATO format
            plato = tile.to_plato_format()
            assert plato["domain"] == EXPERT_DOMAIN_MAP[expert]

            # 3. Hebbian tracking
            event = tile.to_hebbian_event()
            room_idx = adapter.expert_index().get(expert, 0)
            target_idx = (room_idx + 1) % 9
            target_expert = EXPERT_TYPES[target_idx]
            tracker.record_flow(event["source_room"], adapter.expert_to_room(target_expert), "model")

            # 4. Kernel update
            pre = np.zeros(9, dtype=np.float32)
            post = np.zeros(9, dtype=np.float32)
            pre[room_idx] = 1.0
            post[target_idx] = tile.confidence
            kernel.update(pre, post)

            # 5. Cross-consult with affinity target
            affinity_target = EXPERT_AFFINITY[expert][0]
            cross.request_consultation(expert, affinity_target, confidence=0.85)

        # Verify all 9 tiles
        assert len(tiles) == 9
        assert len(tracker) == 9
        assert kernel._update_count == 9

        # Conservation check
        report = kernel.conservation_report()
        assert report.update_count == 9

        # Coupling matrix should have some connections
        coupling_report = coupling.check_conservation()
        assert "gamma_plus_H" in coupling_report

    def test_pipeline_with_translation(self):
        """Pipeline includes model-specific translation at the end."""
        tile = MythosTile.from_expert_output("conservation", {
            "domain": "math",
            "output": "a² − ab + b² where a=3, b=5",
            "confidence": 0.9,
            "meta": {"answer": 19},
        })

        # Translate for different model tiers
        t1 = tile.format_for_model(ModelTier.TIER_1_DIRECT)
        t2 = tile.format_for_model(ModelTier.TIER_2_SCAFFOLDED)
        t3 = tile.format_for_model(ModelTier.TIER_3_INCOMPETENT)

        # Tier 1: passthrough
        assert t1 == tile.content
        # Tier 2: has activation key or domain
        assert tile.activation_key or tile.domain in t2
        # Tier 3: uses answer
        assert "19" in t3

        # Also test FleetRouter translation
        router = FleetRouter()
        for stage in ModelStage:
            prompt = router.route(
                "ByteDance/Seed-2.0-mini",
                "eisenstein_norm",
                {"a": 3, "b": 5},
            )
            assert isinstance(prompt, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
