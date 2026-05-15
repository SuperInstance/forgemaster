"""tests/test_core.py — Provenance-traced tests for core/.

Every test traces to a specific finding (R1–R32) or prediction (P1–P9).
If a test fails, you know exactly which claim is threatened.

Run:
    python3 -m pytest tests/test_core.py -v

Evidence tags in docstrings:
    R7   = BEDROCK: scaffold hurts full-stage models
    R16  = SOLID:  coefficient familiarity > dependency width
    R18  = SOLID:  stage-matched reading optimal
    R25  = SOLID:  L1 scaffold helps PARTIAL, hurts FULL
    R28  = BEDROCK: T=0.0 is perfect but fragile
    R32  = BEDROCK: extraction method is first-class variable
    P7   = PREDICTION: conservation law (echo+partial+correct flat)
    P8   = PREDICTION: PARTIAL→PARTIAL is optimal reading
"""
import sys
import os
import time

import pytest

# Ensure workspace root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pinna import (
    AgentStage, ResidueClass, ScaffoldLevel,
    PinnaField, PinnaEncoder, PinnaReader, PinnaCalibrator,
    ConservationLawChecker, ConservationResult, check_conservation_law,
)
from core.tile_lifecycle import (
    Tile, TileStore, DisproofOnlyGate, MortalitySweep, TileCancerDetector,
)
from core.ender_protocol import (
    CapabilityProfile, ContaminationSensor,
    Level0BoundaryMapping, Level1SelfScaffolding,
    GraduationMarkers,
)
from core.swarm_router import (
    Topology, TaskDescriptor, SwarmRouter, ROUTING_TABLE, classify_task,
)
from core.plato_retriever import Bootstrap, ColdAgentSequence, make_seed_tiles
from core.harness import Harness, FleetAgent, FleetState, TaskResult


# ═══════════════════════════════════════════════════════════════════════════════
# PINNA
# ═══════════════════════════════════════════════════════════════════════════════

class TestPinnaField:
    """The PinnaField is the fixed spectral fingerprint on every tile."""

    def test_roundtrip(self):
        """PinnaField survives dict roundtrip serialization."""
        p = PinnaEncoder.encode(
            agent_id="test",
            agent_stage=AgentStage.PARTIAL,
            residue_class=ResidueClass.ECHO_A,
            confidence=0.25,
            distance_from_boundary=0.1,
            n_trials=20,
            findings=["R15"],
        )
        d = p.to_dict()
        p2 = PinnaField.from_dict(d)
        assert p2.agent_id == "test"
        assert p2.agent_stage == "PARTIAL"
        assert p2.residue_class == "ECHO-a"
        assert p2.n_trials == 20

    def test_dead_zone_high_temperature(self):
        """R28 BEDROCK: T > 0.5 → dead zone (noise, not signal)."""
        p = PinnaField(temperature=0.7, max_tokens=20,
                       extraction_method="last-number-regex")
        assert p.is_dead_zone()

    def test_dead_zone_no_trials(self):
        """Unverified claims (n_trials=0) are dead zones."""
        p = PinnaField(temperature=0.0, max_tokens=20, n_trials=0,
                       extraction_method="last-number-regex")
        assert p.is_dead_zone()

    def test_dead_zone_truncation_artifact(self):
        """R32 BEDROCK: max_tokens > 50 with last-number-regex → truncation artifact."""
        p = PinnaField(temperature=0.3, max_tokens=200,
                       extraction_method="last-number-regex", n_trials=5)
        assert p.is_dead_zone()

    def test_not_dead_zone_valid(self):
        """Valid pinna field is not a dead zone."""
        p = PinnaField(temperature=0.0, max_tokens=20, n_trials=10,
                       extraction_method="last-number-regex")
        assert not p.is_dead_zone()

    def test_stage_property(self):
        """PinnaField.stage returns the correct AgentStage enum."""
        p = PinnaField(agent_stage="PARTIAL")
        assert p.stage == AgentStage.PARTIAL

    def test_residue_intervention(self):
        """Every ResidueClass maps to a specific intervention."""
        assert "L1" in ResidueClass.PARTIAL_A2.intervention()
        assert "route" in ResidueClass.ECHO_A.intervention().lower()


class TestPinnaReader:
    """PinnaReader classifies tile value for a given agent's capability profile."""

    def test_essential_peer_center(self,):
        """P8: PARTIAL reading PARTIAL at same boundary = essential (concha resonance)."""
        reader = PinnaReader(AgentStage.PARTIAL, agent_ceiling=2, reader_distance=0.0)
        p = PinnaField(
            agent_stage=AgentStage.PARTIAL.value,
            distance_from_boundary=0.0,
            temperature=0.0, max_tokens=20, n_trials=10,
            extraction_method="last-number-regex",
            system_prompt="Give ONLY the final number",
        )
        assert reader.classify_tile_value(p) == "essential"

    def test_noise_from_dead_zone(self):
        """Dead zone tiles always return noise regardless of stage match."""
        reader = PinnaReader(AgentStage.FULL, agent_ceiling=3)
        p = PinnaField(temperature=0.7, max_tokens=20)  # T>0.5 = dead zone
        assert reader.classify_tile_value(p) == "noise"

    def test_aspirational_above(self):
        """Tiles from a higher stage are aspirational for lower-stage readers."""
        reader = PinnaReader(AgentStage.ECHO, agent_ceiling=1, reader_distance=0.0)
        p = PinnaField(
            agent_stage=AgentStage.FULL.value,
            distance_from_boundary=0.5,
            temperature=0.0, max_tokens=20, n_trials=10,
            extraction_method="last-number-regex",
            system_prompt="Give ONLY the final number",
        )
        assert reader.classify_tile_value(p) == "aspirational"

    def test_redundant_below(self):
        """Tiles from a lower stage are redundant for higher-stage readers."""
        reader = PinnaReader(AgentStage.FULL, agent_ceiling=3, reader_distance=0.5)
        p = PinnaField(
            agent_stage=AgentStage.ECHO.value,
            distance_from_boundary=0.0,
            temperature=0.0, max_tokens=20, n_trials=10,
            extraction_method="last-number-regex",
            system_prompt="Give ONLY the final number",
        )
        assert reader.classify_tile_value(p) == "redundant"

    def test_calibration_builds_preferences(self):
        """PinnaReader learns from calibration history which signatures help."""
        reader = PinnaReader(AgentStage.PARTIAL, agent_ceiling=2)

        # PARTIAL|CORRECT tiles help
        for _ in range(5):
            p = PinnaField(
                agent_stage=AgentStage.PARTIAL.value,
                residue_class=ResidueClass.CORRECT.value,
                temperature=0.0, max_tokens=20,
            )
            reader.record_calibration(p, succeeded=True)

        # ECHO|ECHO-a tiles don't help
        for _ in range(5):
            p = PinnaField(
                agent_stage=AgentStage.ECHO.value,
                residue_class=ResidueClass.ECHO_A.value,
                temperature=0.0, max_tokens=20,
            )
            reader.record_calibration(p, succeeded=False)

        prefs = reader.get_learned_preferences()
        assert any("PARTIAL" in k and v == 1.0 for k, v in prefs.items())
        assert any("ECHO" in k and v == 0.0 for k, v in prefs.items())

    def test_rank_tiles_sorts_by_value(self):
        """rank_tiles returns essential before aspirational before reliable."""
        reader = PinnaReader(AgentStage.PARTIAL, agent_ceiling=2, reader_distance=0.0)

        tiles = [
            {"id": "noise-tile", "pinna": PinnaField(temperature=0.7, max_tokens=20).to_dict()},
            {"id": "essential-tile", "pinna": PinnaField(
                agent_stage=AgentStage.PARTIAL.value, distance_from_boundary=0.0,
                temperature=0.0, max_tokens=20, n_trials=10,
                extraction_method="last-number-regex",
                system_prompt="Give ONLY the final number",
            ).to_dict()},
        ]

        ranked = reader.rank_tiles(tiles)
        assert ranked[0][0]["id"] == "essential-tile"
        assert ranked[0][1] == "essential"
        assert ranked[1][0]["id"] == "noise-tile"
        assert ranked[1][1] == "noise"


class TestPinnaCalibrator:
    """Fleet-level calibration: learns which pinna signatures work across agents."""

    def test_success_rate_by_stage(self):
        cal = PinnaCalibrator()
        p_good = PinnaField(agent_stage=AgentStage.PARTIAL.value,
                            residue_class=ResidueClass.CORRECT.value)
        p_bad = PinnaField(agent_stage=AgentStage.ECHO.value,
                           residue_class=ResidueClass.ECHO_A.value)

        for _ in range(5):
            cal.record("agent-A", p_good, succeeded=True)
            cal.record("agent-B", p_bad, succeeded=False)

        rates = cal.success_rate_by_stage()
        assert rates["PARTIAL"] == 1.0
        assert rates["ECHO"] == 0.0

    def test_dead_zone_classes(self):
        cal = PinnaCalibrator()
        p = PinnaField(agent_stage=AgentStage.ECHO.value,
                       residue_class=ResidueClass.ECHO_A.value)
        for _ in range(6):
            cal.record("agent", p, succeeded=False)

        dead = cal.dead_zone_classes(min_records=5)
        assert "ECHO-a" in dead


class TestConservationLaw:
    """P7: the most important falsifiable prediction from the multi-model synthesis."""

    def test_confirmed_phase_transition(self):
        """Flat sum (87-93%) across transition → PHASE_TRANSITION confirmed.

        Conservation law: echo + partial + correct stays flat during the
        ECHO→PARTIAL transition. The sum should be ~0.90 for each model below 7B.
        """
        result = check_conservation_law(
            model_sizes_b=[1.0, 3.0, 5.0, 7.0],
            echo_rates=[0.50, 0.28, 0.10, 0.02],   # sum pre-jump: 0.90, 0.90, 0.90
            partial_rates=[0.30, 0.52, 0.70, 0.03],
            correct_rates=[0.10, 0.10, 0.10, 0.90],
        )
        assert result.verdict == "PHASE_TRANSITION"
        assert result.is_flat

    def test_gradual_learning(self):
        """Rising sum → GRADUAL_LEARNING (falsifies slot hypothesis)."""
        result = check_conservation_law(
            model_sizes_b=[1.0, 3.0, 7.0],
            echo_rates=[0.30, 0.10, 0.0],
            partial_rates=[0.10, 0.40, 0.0],
            correct_rates=[0.10, 0.40, 0.95],
        )
        assert result.verdict == "GRADUAL_LEARNING"

    def test_insufficient_data(self):
        """Fewer than 2 models below 7B → INSUFFICIENT_DATA."""
        result = check_conservation_law(
            model_sizes_b=[8.0, 13.0],
            echo_rates=[0.0, 0.0],
            partial_rates=[0.0, 0.0],
            correct_rates=[0.95, 0.98],
        )
        assert result.verdict == "INSUFFICIENT_DATA"

    def test_legacy_dict_interface(self):
        """ConservationLawChecker.check() still works for dict-based data."""
        dist = {
            "2B": {"ECHO": 0.56, "PARTIAL": 0.33, "CORRECT": 0.0, "OTHER": 0.11},
            "4B": {"ECHO": 0.11, "PARTIAL": 0.77, "CORRECT": 0.02, "OTHER": 0.10},
        }
        result = ConservationLawChecker.check(dist)
        assert result["conserved"] is True
        assert "FIRST-ORDER" in result["interpretation"]


# ═══════════════════════════════════════════════════════════════════════════════
# TILE LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════

class TestTile:
    def test_auto_uuid(self):
        """Tiles get auto-generated UUIDs when id is not provided."""
        t = Tile(content="test")
        assert t.id  # non-empty

    def test_win_rate_untested(self):
        """Untested tiles have win_rate=0.5 (neutral, not 0)."""
        t = Tile(content="test")
        assert t.win_rate == 0.5

    def test_record_use(self):
        t = Tile(content="test")
        t.record_use(True)
        t.record_use(True)
        t.record_use(False)
        assert t.win_rate == pytest.approx(2 / 3, abs=0.01)


class TestTileStore:
    def test_crud(self):
        store = TileStore()
        tile = Tile(id="t1", type="knowledge", content="test", confidence=0.9)
        assert store.put(tile)
        assert store.get("t1").content == "test"
        assert store.delete("t1")
        assert store.get("t1") is None

    def test_query_filters(self):
        store = TileStore()
        store.put(Tile(id="k1", type="knowledge", content="a", confidence=0.9))
        store.put(Tile(id="k2", type="knowledge", content="b", confidence=0.5))
        store.put(Tile(id="l1", type="loop", content="c", confidence=0.8))

        assert len(store.query(tile_type="knowledge", min_confidence=0.7)) == 1
        assert store.query(tile_type="knowledge", min_confidence=0.7)[0].id == "k1"

    def test_search_by_pinna(self):
        """Pinna-aware retrieval prefers tiles at the reader's boundary."""
        store = TileStore()
        # Add a PARTIAL-stage tile near boundary
        p = PinnaEncoder.encode(
            agent_id="other-agent", agent_stage=AgentStage.PARTIAL,
            residue_class=ResidueClass.CORRECT, confidence=0.8,
            distance_from_boundary=0.0, n_trials=20,
        )
        store.put(Tile(id="partial-tile", type="knowledge", content="useful", pinna=p, confidence=0.8))
        # Add a dead-zone tile
        store.put(Tile(id="noise-tile", type="knowledge", content="noise",
                       pinna=PinnaField(temperature=0.7, max_tokens=20), confidence=0.3))

        results = store.search_by_pinna(AgentStage.PARTIAL, reader_distance=0.0)
        assert len(results) >= 1
        assert results[0][0].id == "partial-tile"
        assert results[0][1] == "essential"

    def test_admit_vs_put(self):
        """admit() goes through disproof gate; put() bypasses it."""
        store = TileStore(seed_phase_size=2)
        # First 2 tiles: seed phase
        ok, _ = store.admit(Tile(id="s1", type="knowledge", content="seed"))
        assert ok
        ok, _ = store.admit(Tile(id="s2", type="knowledge", content="seed"))
        assert ok
        # Tile 3: needs falsification
        ok, reason = store.admit(Tile(id="s3", type="knowledge", content="new fact"))
        assert not ok

    def test_stats(self):
        store = TileStore()
        for i in range(3):
            t = Tile(id=f"t{i}", content=f"c{i}")
            t.record_use(i % 2 == 0)
            store.put(t)
        stats = store.stats()
        assert stats["total_tiles"] == 3
        assert stats["total_wins"] == 2  # t0 (True), t2 (True)
        assert stats["total_losses"] == 1  # t1 (False)


class TestDisproofOnlyGate:
    """MULTI-MODEL-SYNTHESIS.md Novel Idea 2: disproof-only tile admission."""

    def test_seed_phase(self):
        store = TileStore(seed_phase_size=5)
        gate = DisproofOnlyGate(store, seed_threshold=5)
        ok, reason = gate.admit(Tile(id="t1", content="seed"))
        assert ok
        assert "SEED PHASE" in reason

    def test_exempt_types(self):
        """Loop, spline, meta, seed tiles are always admitted."""
        store = TileStore()
        for i in range(10):
            store.put(Tile(id=f"s{i}", content=f"seed {i}"))
        gate = DisproofOnlyGate(store, seed_threshold=5)

        for ttype in ("loop", "spline", "meta", "seed"):
            ok, _ = gate.admit(Tile(id=f"{ttype}-1", type=ttype, content="test"))
            assert ok

    def test_rejection_without_falsifies(self):
        """After seed phase, fact tiles without falsifies are rejected."""
        store = TileStore()
        for i in range(10):
            store.put(Tile(id=f"s{i}", content=f"seed {i}"))
        gate = DisproofOnlyGate(store, seed_threshold=5)
        ok, reason = gate.admit(Tile(id="new", type="knowledge", content="fact"))
        assert not ok
        assert "REJECTED" in reason

    def test_rejection_without_evidence(self):
        """Falsifying tiles must have evidence."""
        store = TileStore()
        store.put(Tile(id="target", type="knowledge", content="old"))
        for i in range(10):
            store.put(Tile(id=f"s{i}", content=f"seed {i}"))
        gate = DisproofOnlyGate(store, seed_threshold=5)
        ok, _ = gate.admit(Tile(
            id="new", type="knowledge", content="counter",
            falsifies="target",
        ))
        assert not ok  # no evidence

    def test_rejection_without_negative(self):
        """Every tile must document its boundary conditions."""
        store = TileStore()
        store.put(Tile(id="target", type="knowledge", content="old"))
        for i in range(10):
            store.put(Tile(id=f"s{i}", content=f"seed {i}"))
        gate = DisproofOnlyGate(store, seed_threshold=5)
        ok, _ = gate.admit(Tile(
            id="new", type="knowledge", content="counter",
            falsifies="target", evidence=["R15"],
        ))
        assert not ok  # no negative field

    def test_successful_falsification(self):
        """Tile with falsifies + evidence + negative → admitted."""
        store = TileStore()
        store.put(Tile(id="target", type="knowledge", content="old"))
        for i in range(10):
            store.put(Tile(id=f"s{i}", content=f"seed {i}"))
        gate = DisproofOnlyGate(store, seed_threshold=5)
        ok, reason = gate.admit(Tile(
            id="new", type="knowledge", content="counter",
            falsifies="target", evidence=["R15", "exp-42"],
            negative="Only applies to a²-ab+b² with |a|<10",
        ))
        assert ok
        assert "ADMITTED" in reason


class TestMortalitySweep:
    """seed-pro predicted tile cancer at ~1127 tiles. Mortality prevents it."""

    def test_sweep_prunes_worst(self):
        store = TileStore()
        # 20 tiles with increasing win rates
        for i in range(20):
            t = Tile(id=f"t-{i}", type="knowledge", content=f"tile {i}")
            t.use_count = 10
            t.win_count = i
            t.loss_count = 10 - (i // 2)
            store.put(t)

        result = store.sweep(mortality_rate=0.15)
        assert result["pruned"] >= 1
        assert store.get("t-0") is None  # lowest win rate pruned first

    def test_protected_types_survive(self):
        store = TileStore()
        loop = Tile(id="loop-1", type="loop", content="retrieval")
        loop.use_count = 10
        loop.win_count = 0
        loop.loss_count = 10
        store.put(loop)
        for i in range(20):
            t = Tile(id=f"t-{i}", type="knowledge", content=f"tile {i}")
            t.use_count = 10
            t.win_count = 5
            t.loss_count = 5
            store.put(t)

        store.sweep()
        assert store.get("loop-1") is not None


class TestTileCancerDetector:
    """Detect accuracy dropping as knowledge grows."""

    def test_healthy_store(self):
        store = TileStore()
        for i in range(20):
            t = Tile(id=f"t-{i}", content=f"tile {i}")
            t.win_count = 8
            t.loss_count = 2
            t.use_count = 10
            store.put(t)
        result = store.cancer_check()
        assert not result["alert"]

    def test_cancer_detected(self):
        """Accuracy declining as corpus growing → cancer alert."""
        store = TileStore()
        # Put high-loss tiles to trigger the threshold warning (1000+ tiles, <30% win rate)
        # Use the detector directly with injected history
        from core.tile_lifecycle import TileCancerDetector
        detector = TileCancerDetector(store)

        # Inject enough tiles to exceed the 1000 threshold
        for i in range(1100):
            t = Tile(id=f"t-{i}", content=f"tile {i}")
            t.win_count = 2
            t.loss_count = 8
            store.put(t)

        # Force a low win_rate snapshot
        detector.history = [
            {"tile_count": 1100, "win_rate": 0.2, "ts": time.time()},
        ]

        result = detector.check()
        # The 1000+ tiles with <30% win_rate triggers threshold warning
        assert result["alert"]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDER PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentStage:
    def test_ordering(self):
        assert AgentStage.NONE < AgentStage.ECHO < AgentStage.PARTIAL < AgentStage.FULL


class TestCapabilityProfile:
    def test_is_at_boundary(self):
        """Agent with bare_rate < 60% and scaffolded > 70% is at boundary."""
        p = CapabilityProfile(
            stage=AgentStage.PARTIAL, bare_rate=0.25, scaffolded_rate=0.80,
        )
        assert p.is_at_boundary

    def test_not_at_boundary(self):
        p = CapabilityProfile(stage=AgentStage.FULL, bare_rate=0.95, scaffolded_rate=0.90)
        assert not p.is_at_boundary

    def test_scaffold_helps(self):
        """R25: scaffold helps PARTIAL (+30pp or more)."""
        p = CapabilityProfile(stage=AgentStage.PARTIAL, bare_rate=0.25, scaffolded_rate=0.80)
        assert p.scaffold_helps

    def test_scaffold_hurts_full(self):
        """R7 BEDROCK: scaffold HURTS full-stage models."""
        p = CapabilityProfile(stage=AgentStage.FULL, bare_rate=0.95, scaffolded_rate=0.90)
        assert not p.scaffold_helps

    def test_to_pinna(self):
        """Profiles can convert to PinnaField for tile annotation."""
        p = CapabilityProfile(
            agent_id="test", stage=AgentStage.PARTIAL,
            bare_rate=0.4, n_trials=20,
        )
        pinna = p.to_pinna()
        assert pinna.agent_id == "test"
        assert pinna.n_trials == 20

    def test_dominant_residue(self):
        p = CapabilityProfile(
            residue_distribution={"ECHO-a": 0.5, "CORRECT": 0.3, "PARTIAL-ab": 0.2}
        )
        assert p.dominant_residue() == "ECHO-a"


class TestContaminationSensor:
    """JAM-SESSION-ANALYSIS.md: contamination is continuous, not binary."""

    def test_clean(self):
        s = ContaminationSensor(baseline_accuracy=0.8)
        r = s.sample(0.78, "bare task")
        assert r["level"] == "CLEAN"
        assert s.is_frame_intact()

    def test_mild(self):
        s = ContaminationSensor(baseline_accuracy=0.8)
        r = s.sample(0.70, "listening")
        assert r["level"] == "MILD"

    def test_moderate(self):
        """15pp drop from wrong-answer anchor → MODERATE."""
        s = ContaminationSensor(baseline_accuracy=0.6)
        r = s.sample(0.40, "listening to partner")
        assert r["level"] == "MODERATE"

    def test_severe_breaks_frame(self):
        s = ContaminationSensor(baseline_accuracy=0.8)
        s.sample(0.4, "bad1")
        s.sample(0.3, "bad2")
        s.sample(0.2, "bad3")
        assert not s.is_frame_intact()

    def test_trend(self):
        s = ContaminationSensor(baseline_accuracy=0.8)
        s.sample(0.75, "t1")
        s.sample(0.60, "t2")
        s.sample(0.40, "t3")
        assert s.trend() == "WORSENING"

    def test_intervention_recommendation(self):
        s = ContaminationSensor(baseline_accuracy=0.8)
        s.sample(0.4, "bad")
        assert "RESET" in s.intervention_recommendation()


class TestGraduationMarkers:
    """UNIFIED-FRAMEWORK.md §VII: agent never sees these markers."""

    def test_initially_not_graduated(self):
        g = GraduationMarkers()
        assert not g.is_graduated
        assert g.graduation_readiness == 0.0

    def test_requires_all_three(self):
        g = GraduationMarkers()
        g.capability_card_registered = True
        assert not g.is_graduated
        g.tiles_retrieved_by_others = 5
        assert not g.is_graduated
        g.done_outputs_consumed_as_data = 2
        assert g.is_graduated

    def test_status(self):
        g = GraduationMarkers()
        status = g.status()
        assert "graduated" in status
        assert "markers" in status


# ═══════════════════════════════════════════════════════════════════════════════
# SWARM ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class TestSwarmRouter:
    def test_routing_table(self):
        """UNIFIED-FRAMEWORK.md §V: canonical task→topology routing."""
        router = SwarmRouter()
        assert router.route(TaskDescriptor(task_type="compute")) == Topology.ARENA
        assert router.route(TaskDescriptor(task_type="verify")) == Topology.DUEL
        assert router.route(TaskDescriptor(task_type="map_capability")) == Topology.BOOTCAMP
        assert router.route(TaskDescriptor(task_type="explore")) == Topology.COLLECTIVE
        assert router.route(TaskDescriptor(task_type="meta_experiment")) == Topology.TOURNAMENT
        assert router.route(TaskDescriptor(task_type="unknown")) == Topology.COLLECTIVE

    def test_jam_mode_for_identical_partial(self):
        """JAM-SESSION-ANALYSIS.md: identical PARTIAL agents get jam mode."""
        router = SwarmRouter()
        profiles = [
            CapabilityProfile(agent_id="A", stage=AgentStage.PARTIAL),
            CapabilityProfile(agent_id="B", stage=AgentStage.PARTIAL),
        ]
        result = router.route_with_profiles(TaskDescriptor(task_type="compute"), profiles)
        assert result["jam_mode"] is True
        assert result["assignment"]["mode"] == "jam"
        assert result["assignment"]["rhythm"]["temperature"] == 0.0
        assert result["assignment"]["solo"]["temperature"] == 0.3

    def test_standard_for_mixed_stages(self):
        router = SwarmRouter()
        profiles = [
            CapabilityProfile(agent_id="A", stage=AgentStage.ECHO),
            CapabilityProfile(agent_id="B", stage=AgentStage.FULL),
        ]
        result = router.route_with_profiles(TaskDescriptor(task_type="compute"), profiles)
        assert result["jam_mode"] is False

    def test_single_agent_fallback(self):
        """Single agent can't run DUEL or ARENA → fallback to COLLECTIVE."""
        router = SwarmRouter()
        result = router.route_with_profiles(
            TaskDescriptor(task_type="compute"),
            [CapabilityProfile(agent_id="A", stage=AgentStage.FULL)],
        )
        assert result["topology"] == Topology.COLLECTIVE

    def test_task_descriptor_from_description(self):
        td = TaskDescriptor.from_description("Compute the Eisenstein norm for a=3, b=4")
        assert td.task_type == "compute"
        assert td.domain == "arithmetic"

        td2 = TaskDescriptor.from_description("Verify the residue classification")
        assert td2.task_type == "verify"

    def test_classify_task_standalone(self):
        assert classify_task("compute a²-ab+b²") == Topology.ARENA
        assert classify_task("explore unknown regions") == Topology.COLLECTIVE


# ═══════════════════════════════════════════════════════════════════════════════
# PLATO RETRIEVER
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeedTiles:
    def test_make_seed_tiles(self):
        tiles = make_seed_tiles()
        assert len(tiles) == 6
        ids = [t.id for t in tiles]
        assert "loop-zero-shot-retrieval" in ids
        assert "loop-arithmetic-width-probe" in ids

    def test_bootstrap_seeds_store(self):
        store = TileStore()
        result = Bootstrap.seed(store)
        assert result["admitted"] == 6
        assert store.count() == 6

    def test_bootstrap_idempotent(self):
        store = TileStore()
        Bootstrap.seed(store)
        result = Bootstrap.seed(store)  # second call skips existing
        assert result["skipped"] == 6


# ═══════════════════════════════════════════════════════════════════════════════
# HARNESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHarness:
    @staticmethod
    def mock_query(prompt: str):
        if "a=3" in prompt and "b=4" in prompt:
            return 13  # 9 - 12 + 16
        if "9" in prompt and "12" in prompt and "16" in prompt:
            return 13
        return 42

    def test_seed_and_bootstrap(self):
        """Full lifecycle: seed → bootstrap → verify profile."""
        harness = Harness("test-agent", self.mock_query)
        seed_result = harness.seed()
        assert seed_result["admitted"] == 6

        bootstrap_result = harness.bootstrap()
        assert harness.bootstrapped
        assert harness.profile is not None
        assert harness.profile.agent_id == "test-agent"

    def test_fleet_summary(self):
        harness = Harness("test-agent", self.mock_query)
        harness.seed()
        harness.bootstrap()
        summary = harness.fleet_summary()
        assert summary["my_stage"] in ("NONE", "ECHO", "PARTIAL", "FULL")
        assert summary["tile_count"] >= 6

    def test_conservation_no_data(self):
        harness = Harness("test-agent", self.mock_query)
        result = harness.conservation_check()
        assert result["status"] == "NO_DATA"

    def test_register_other_agent(self):
        harness = Harness("test-agent", self.mock_query)
        harness.seed()
        harness.bootstrap()
        other_profile = CapabilityProfile(agent_id="other", stage=AgentStage.FULL, bare_rate=0.9)
        harness.register_agent("other", other_profile)
        assert len(harness.fleet.alive_agents()) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# PROVENANCE TRACING
# ═══════════════════════════════════════════════════════════════════════════════

class TestProvenance:
    """Every tile carries pinna provenance. No orphans."""

    def test_pinna_on_tile(self):
        pinna = PinnaEncoder.encode(
            agent_id="test",
            agent_stage=AgentStage.PARTIAL,
            residue_class=ResidueClass.CORRECT,
            confidence=0.8,
            distance_from_boundary=0.3,
            n_trials=20,
            findings=["R15", "R25"],
        )
        tile = Tile(content="test result", pinna=pinna)
        assert tile.pinna is not None
        assert tile.pinna.agent_id == "test"
        assert "R15" in tile.pinna.findings_referenced

    def test_profile_to_pinna_roundtrip(self):
        p = CapabilityProfile(
            agent_id="llama-8b", stage=AgentStage.PARTIAL,
            width_ceiling=2, bare_rate=0.4, n_trials=28,
        )
        pinna = p.to_pinna()
        assert pinna.agent_id == "llama-8b"
        assert pinna.n_trials == 28


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
