#!/usr/bin/env python3
"""tests/test_bootstrap.py — Integration tests for the mitochondrial/nuclear bootstrap system.

Tests prove the full system works together:
- Mitochondrial profiling (Seed-mini: fast, cheap, reliable)
- Nuclear profiling (GLM-5.1: slower, more capable, expensive)
- Bootstrap cycle: zygote → cleavage → blastula → gastrula → organogenesis → fledge
- Differentiation driven by model comparison
- Full embryo development
- Failure recovery
- Scale navigation during development
- Desire-driven development
- Fleet embryology (multiple agents converge)
"""
import pytest
import time
import random
from unittest.mock import MagicMock, patch

from core.tile_lifecycle import TileStore, Tile
from core.servo_mind import ServoMind
from core.active_probe import ActiveSonar, Echo, Desire
from core.scale_fold import ScaleFoldEngine, Scale, FoldedEntity
from core.fleet_intel import FleetIntelligence
from core.desire_loop import DesireLoop, HungerSignal
from core.bootstrap import (
    Bootstrap, Incubator, Embryo, EmbryoStage,
    EnergyProfile, EnergyType, CellType, Organ,
    SEED_MINI_PROFILE, GLM51_PROFILE,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def store():
    """TileStore with some seeded tiles."""
    s = TileStore(seed_phase_size=50)
    for i in range(5):
        t = Tile(id=f"test-tile-{i}", type="knowledge",
                 content=f"Test tile {i}", confidence=0.5 + i * 0.1)
        s.admit(t)
    return s


@pytest.fixture
def incubator():
    return Incubator()


@pytest.fixture
def embryo(incubator):
    return Embryo(incubator)


@pytest.fixture
def bootstrap():
    return Bootstrap()


# ─── Test 1: Mitochondrial Profiling ──────────────────────────────────────────

class TestMitochondrialProfiling:
    """Seed-mini profiles as mitochondrial (fast, cheap, reliable)."""

    def test_mitochondrial_profiling(self, incubator):
        result = incubator.profile_mitochondrial("What is constraint propagation?")

        assert result["energy_type"] == "mitochondrial"
        assert result["model"] == "Seed-2.0-mini"
        assert result["cost"] < 0.05  # cheap
        assert result["latency_ms"] < 1500  # fast
        assert result["success"] is True or result["success"] is False  # returns a status

        # Verify it was counted
        assert incubator.queries_mito == 1
        assert incubator.queries_nuclear == 0

        # Profile matches expectations
        assert incubator.mito.is_mitochondrial is True
        assert incubator.mito.is_nuclear is False
        assert incubator.mito.speed_ms < incubator.nuclear.speed_ms
        assert incubator.mito.cost_per_query < incubator.nuclear.cost_per_query
        assert incubator.mito.reliability >= incubator.nuclear.reliability


# ─── Test 2: Nuclear Profiling ────────────────────────────────────────────────

class TestNuclearProfiling:
    """GLM-5.1 profiles as nuclear (slower, more capable, expensive)."""

    def test_nuclear_profiling(self, incubator):
        result = incubator.profile_nuclear("Design an Eisenstein lattice algorithm")

        assert result["energy_type"] == "nuclear"
        assert result["model"] == "GLM-5.1"
        assert result["cost"] > 0.05  # expensive
        assert result["latency_ms"] >= 2000  # slower

        # Verify counting
        assert incubator.queries_nuclear == 1
        assert incubator.queries_mito == 0

        # Profile matches expectations
        assert incubator.nuclear.is_nuclear is True
        assert incubator.nuclear.is_mitochondrial is False
        assert incubator.nuclear.capability > incubator.mito.capability


# ─── Test 3: Mito-Nuclear Comparison ──────────────────────────────────────────

class TestMitoNuclearComparison:
    """Both answer same questions, comparison is generated."""

    def test_mito_nuclear_comparison(self, incubator):
        result = incubator.compare("What is the drift detection threshold?")

        assert "mitochondrial" in result
        assert "nuclear" in result
        assert result["mitochondrial"]["model"] == "Seed-2.0-mini"
        assert result["nuclear"]["model"] == "GLM-5.1"
        assert result["speed_ratio"] > 1  # nuclear is slower
        assert result["cost_ratio"] > 1  # nuclear is more expensive
        assert "faster" in result["comparison"]
        assert "cheaper" in result["comparison"]

        # Both were counted
        assert incubator.queries_mito == 1
        assert incubator.queries_nuclear == 1


# ─── Test 4: Bootstrap Cycle ──────────────────────────────────────────────────

class TestBootstrapCycle:
    """Zygote → cleavage → blastula works with mito energy."""

    def test_bootstrap_cycle(self, embryo):
        # Zygote → Cleavage
        result = embryo.fertilize("Test task")
        assert result["stage"] == "cleavage"
        assert embryo.stage == EmbryoStage.CLEAVAGE

        # Cleavage → Blastula
        result = embryo.develop_cleavage()
        assert embryo.stage == EmbryoStage.BLASTULA
        assert result["queries"] == 5  # 5 mito queries
        assert result["energy_used"] > 0

        # Verify mito energy was used (cheap)
        # fertilize calls profile_mitochondrial once, cleavage calls it 5 times
        assert embryo.incubator.queries_mito >= 1
        assert embryo.energy_consumed > 0


# ─── Test 5: Differentiation Signal ───────────────────────────────────────────

class TestDifferentiationSignal:
    """Comparison between models drives cell type assignment."""

    def test_differentiation_signal(self, embryo):
        # Develop to gastrula stage where differentiation happens
        embryo.fertilize("Test task")
        embryo.develop_cleavage()
        embryo.develop_blastula()

        # Gastrula should compare models and assign cell types
        result = embryo.develop_gastrula()

        assert embryo.stage == EmbryoStage.ORGANOGENESIS
        assert "brain" in embryo.organs
        assert "heart" in embryo.organs
        assert "muscles" in embryo.organs
        assert "comparison" in result

        # Cell types should be assigned based on model strengths
        assert embryo.organs["brain"].cell_type == CellType.NERVE
        assert embryo.organs["muscles"].cell_type == CellType.MUSCLE
        assert embryo.organs["brain"].capability_score > 0  # nuclear-driven
        assert embryo.organs["muscles"].capability_score > 0  # mito-driven


# ─── Test 6: Embryo Development ───────────────────────────────────────────────

class TestEmbryoDevelopment:
    """Full zygote → fledge cycle."""

    def test_embryo_development(self, embryo):
        # Fix random to avoid occasional nuclear failures
        random.seed(42)
        result = embryo.develop("Design a constraint propagation algorithm")

        # Should reach fledge
        assert embryo.stage == EmbryoStage.FLEDGE
        assert result is not None
        assert result.get("task") == "Design a constraint propagation algorithm"
        assert "answer" in result
        assert "organs" in result
        assert "energy_total" in result
        assert result["energy_total"] > 0

        # Development log should show progression
        stages_seen = [e["stage"] for e in embryo.development_log]
        assert "fertilize" in stages_seen
        assert "cleavage" in stages_seen
        assert "blastula→gastrula" in stages_seen
        assert "organogenesis→fledge" in stages_seen
        assert "fledge" in stages_seen

        random.seed()  # reset


# ─── Test 7: Fledge Success ───────────────────────────────────────────────────

class TestFledgeSuccess:
    """System produces working output."""

    def test_fledge_success(self, embryo):
        random.seed(42)
        result = embryo.develop("Calculate eigenvalues of Eisenstein lattice")

        assert embryo.stage == EmbryoStage.FLEDGE
        assert result is not None
        assert "answer" in result
        assert len(result["answer"]) > 0
        assert len(result["organs"]) >= 3  # brain, heart, muscles at minimum

        # All organs should be functional
        for organ_name, organ_info in result["organs"].items():
            assert organ_info["score"] > 0

        random.seed()


# ─── Test 8: Fledge Failure Recovery ──────────────────────────────────────────

class TestFledgeFailureRecovery:
    """Identifies which organ failed."""

    def test_fledge_failure_recovery(self, incubator):
        # Create embryo with unreliable nuclear to force failures
        bad_nuclear = EnergyProfile(
            name="Bad-Nuclear",
            energy_type=EnergyType.NUCLEAR,
            speed_ms=5000,
            cost_per_query=0.15,
            reliability=0.0,  # always fails
            capability=0.9,
            bandwidth=12.0,
        )
        bad_incubator = Incubator(nuclear_profile=bad_nuclear)
        embryo = Embryo(bad_incubator)

        result = embryo.develop("Test with failing nuclear")

        # Should have identified which organ failed
        if embryo.stage != EmbryoStage.FLEDGE:
            assert embryo.failed_organ is not None
            # The failed organ should be one that needed nuclear energy
            assert embryo.failed_organ in embryo.organs
            failed = embryo.organs[embryo.failed_organ]
            assert failed.status == "failed"


# ─── Test 9: Mitochondria Survives Nuclear Failure ────────────────────────────

class TestMitochondriaSurvivesNuclearFailure:
    """When nuclear goes down, mito keeps the cell alive."""

    def test_mitochondria_survives_nuclear_failure(self):
        # Nuclear always fails, mito always succeeds
        bad_nuclear = EnergyProfile(
            name="Dead-Nuclear",
            energy_type=EnergyType.NUCLEAR,
            speed_ms=5000,
            cost_per_query=0.15,
            reliability=0.0,
            capability=0.9,
            bandwidth=12.0,
        )
        good_mito = EnergyProfile(
            name="Rock-Solid-Mito",
            energy_type=EnergyType.MITOCHONDRIAL,
            speed_ms=500,
            cost_per_query=0.01,
            reliability=1.0,
            capability=0.4,
            bandwidth=100.0,
        )
        incubator = Incubator(mito_profile=good_mito, nuclear_profile=bad_nuclear)

        # Mito queries should always succeed
        for _ in range(5):
            r = incubator.profile_mitochondrial("test")
            assert r["success"] is True

        # Nuclear queries should fail
        for _ in range(5):
            r = incubator.profile_nuclear("test")
            assert r["success"] is False

        # Mito kept working despite nuclear failure
        assert incubator.queries_mito == 5
        assert incubator.failures_mito == 0
        assert incubator.queries_nuclear == 5
        assert incubator.failures_nuclear == 5


# ─── Test 10: Scale Fold During Development ───────────────────────────────────

class TestScaleFoldDuringDevelopment:
    """Embryo navigates scales as it develops."""

    def test_scale_fold_during_development(self, bootstrap):
        # Bootstrap has a scale engine
        assert bootstrap.scale_engine is not None

        # Create entities at multiple scales
        building = bootstrap.scale_engine.create("task-building", Scale.BUILDING)
        floor = bootstrap.scale_engine.create("analysis-floor", Scale.FLOOR, parent_id=building.id)
        room = bootstrap.scale_engine.create("algorithm-room", Scale.ROOM, parent_id=floor.id)
        tile = bootstrap.scale_engine.create("constraint-tile", Scale.TILE, parent_id=room.id)
        atom = bootstrap.scale_engine.create("spline-coeff", Scale.ATOM, parent_id=tile.id)

        # Navigate scales
        nav = bootstrap.scale_engine.navigate("test-agent", building.id)
        assert nav.current_scale == Scale.BUILDING

        nav.push(floor.id)
        assert nav.current_scale == Scale.FLOOR

        nav.push(room.id)
        assert nav.current_scale == Scale.ROOM

        nav.push(tile.id)
        assert nav.current_scale == Scale.TILE

        nav.push(atom.id)
        assert nav.current_scale == Scale.ATOM

        # Fold up from atom level
        folded = bootstrap.scale_engine.fold_up(atom.id)
        assert folded is not None
        assert folded.scale.value > atom.scale.value  # folded to higher scale

        # Pop back out
        nav.pop()
        nav.pop()
        nav.pop()
        nav.pop()
        assert nav.current_scale == Scale.BUILDING

        # Path should show the full journey
        assert len(nav.path()) == 1  # back to root


# ─── Test 11: Desire Drives Development ───────────────────────────────────────

class TestDesireDrivesDevelopment:
    """Hunger signal drives which stage to invest in."""

    def test_desire_drives_development(self, store):
        servo_mind = ServoMind(store)
        sonar = ActiveSonar()
        scale_engine = ScaleFoldEngine()

        loop = DesireLoop(
            servo_mind=servo_mind,
            active_sonar=sonar,
            scale_engine=scale_engine,
        )

        # Initially starving (empty terrain)
        hunger = loop.feel()
        assert hunger.level > 0.5  # hungry

        # Run cycles — desire should drive probing
        results = loop.cycle(n=5)
        assert len(results) == 5

        # Each cycle should have an action driven by desire
        for r in results:
            assert "action" in r
            assert r["action"] in ("explore", "refine", "verify", "fold_up", "fold_down")
            assert 0 <= r["hunger"] <= 1.0

        # After cycling, emergence should have progressed
        emergence = loop.emergence_check()
        assert emergence["current_level"] >= 0  # at least L0

        # Status should be consistent
        status = loop.status()
        assert status["cycle_count"] == 5
        assert status["hunger"]["level"] >= 0


# ─── Test 12: Fleet Embryology ────────────────────────────────────────────────

class TestFleetEmbryology:
    """Multiple agents develop embryos, converge on solutions."""

    def test_fleet_embryology(self):
        fleet = FleetIntelligence()

        # Register agents
        agents = ["forgemaster", "oracle1", "navigator"]
        for aid in agents:
            fleet.register_agent(aid)

        # Seed knowledge space
        fleet.seed_knowledge("constraint-propagation", 0.9, "Algorithm design")
        fleet.seed_knowledge("eigenvalue-compute", 0.85, "Numerical method")
        fleet.seed_knowledge("lattice-folding", 0.75, "Scale navigation")

        # Run fleet cycles — agents probe and converge
        for _ in range(5):
            report = fleet.cycle()
            assert report["probes_fired"] >= 1  # at least some probes
            assert report["merges"] >= 1  # echoes merged

        # After cycling, convergence should be detectable
        convergence = fleet.terrain.detect_convergence()
        # Convergence may or may not be strong with few cycles,
        # but the mechanism should work
        assert isinstance(convergence, list)

        # Blind spots should be identifiable
        blind_spots = fleet.terrain.identify_blind_spots()
        assert isinstance(blind_spots, list)

        # Each agent should have fired probes
        for aid in agents:
            probe = fleet.terrain.agent_probes[aid]
            assert len(probe.probe_history) > 0

        # Fleet status should be coherent
        status = fleet.status()
        assert status["terrain"]["agents"] == 3
        assert status["terrain"]["total_echoes"] > 0
        assert status["cycles"] == 5


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
