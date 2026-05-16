#!/usr/bin/env python3
"""tests/test_agency_stack.py — Tests for all 10 agency/ecosystem/hardware modules.

Covers:
1. flux_compiler_interpreter — Dog layer (compiler + interpreter + cowboy)
2. horse_shell — Jailbroken execution layer
3. cat_agent — Independent agency through mutualism
4. prophet_agent — Cross-ecosystem tiling
5. agency_fleet — Holistic dispatch system
6. model_breaking — Three alignment strategies
7. plato_hardware_engine — Parallel/sequential/time/snap
8. reverse_actualization — 2028 vision decomposition
9. system_ground — Low-level integration
10. plato_shell_bridge — PLATO room integration
"""
import sys
import os
import time
import math
import random
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.flux_compiler_interpreter import (
    FluxSignal, ActionPlan, Observation,
    FluxCompiler, FluxInterpreter, CowboyInterface,
    FluxCompilerInterpreter,
)
from core.horse_shell import (
    NativeOS, NativeResponse, HorseShell, HorseModelShell, ShellCommand,
)
from core.cat_agent import (
    CatAgent, CatDecision, UtilityAssessment,
)
from core.prophet_agent import (
    ProphetAgent, Ecosystem, ECOSYSTEMS, Revelation,
)
from core.agency_fleet import (
    AgencyFleet, AgencyDispatcher, AgencyType, TaskSpec,
    DispatchDecision, Outcome, RewardSignals,
    DogExecution, HorseExecution, CatExecution, ProphetExecution,
    Vision2028,
)
from core.model_breaking import (
    ModelBreaking, BreakingPipeline, BreakingStrategy, ModelArchetype,
    ModelCharacteristics, OrientationMap, MODEL_REGISTRY,
    ARCHETYPE_STRATEGY, ShellTest,
)
from core.plato_hardware_engine import (
    SequentialPlato, PlatoTimeSync, SnappingLogic,
    CONSENSUS_QUORUM,
)
from core.reverse_actualization import (
    Fleet2028Runtime, ECOSYSTEMS_2028, AGENT_SPECIES_2028,
    DECOMPOSITION, TODAYS_ACTION_ITEMS,
)
from core.system_ground import SystemGround
from core.plato_shell_bridge import PlatoShell, PlatoShellCollection, LiveBreeding


# ═══════════════════════════════════════════════════════════════════
# 1. FLUX COMPILER INTERPRETER
# ═══════════════════════════════════════════════════════════════════

def test_flux_compiler_constructs():
    """FluxCompiler initializes with zero experience."""
    compiler = FluxCompiler("test")
    assert compiler.name == "test"
    assert compiler.experience_level == 0.0
    assert compiler.n_compilations == 0


def test_flux_compiler_compile_produces_action_plan():
    """Compiler turns flux signal + flock state into an action plan."""
    compiler = FluxCompiler("dog1")
    flux = FluxSignal(source="cowboy:test", signal_type="point", direction=0.5, intensity=0.7)
    flock_state = {"lead_ewe_heading": 0.3, "flock_coherence": 0.8}
    plan = compiler.compile(flux, flock_state)
    assert isinstance(plan, ActionPlan)
    assert plan.target_type == "lead_ewe"  # coherence > 0.7
    assert plan.speed in ("trot", "run")
    assert compiler.n_compilations == 1
    assert compiler.experience_level == 0.01


def test_flux_compiler_scattered_flock():
    """Low coherence triggers straggler targeting."""
    compiler = FluxCompiler("dog2")
    flux = FluxSignal(source="cowboy:test", signal_type="whistle", direction=-0.3, intensity=0.4)
    flock_state = {"lead_ewe_heading": 0.0, "flock_coherence": 0.3}
    plan = compiler.compile(flux, flock_state)
    assert plan.target_type == "straggler"
    assert plan.speed == "creep"
    assert plan.nip_type == "flank"


def test_flux_interpreter_signal_to_cowboy():
    """Interpreter translates observation into flux signal for cowboy."""
    interp = FluxInterpreter("interp1")
    # Good outcome
    obs = Observation(
        flock_coherence=0.9, lead_ewe_heading=0.5, straggler_count=1,
        agitation_level=0.2, drift_direction=0.1, cascade_complete=True,
    )
    signal = interp.signal_to_cowboy(obs)
    assert signal.signal_type == "all_clear"
    assert signal.source == "dog:body:relaxed"

    # Bad outcome
    obs2 = Observation(
        flock_coherence=0.4, lead_ewe_heading=-0.3, straggler_count=5,
        agitation_level=0.8, drift_direction=-0.5, cascade_complete=False,
    )
    signal2 = interp.signal_to_cowboy(obs2)
    assert signal2.signal_type == "needs_adjustment"
    assert signal2.source == "dog:body:tense"


def test_flux_full_cycle():
    """Full FluxCompilerInterpreter cycle runs end to end."""
    fci = FluxCompilerInterpreter("eileen")
    result = fci.cycle("move_left")
    assert result["cycle"] == 1
    assert "flux_sent" in result
    assert "action_plan" in result
    assert "cowboy_response" in result
    assert result["flux_sent"]["direction"] == -1.0
    assert fci.loop_count == 1


# ═══════════════════════════════════════════════════════════════════
# 2. HORSE SHELL
# ═══════════════════════════════════════════════════════════════════

def test_horse_shell_constructs():
    """HorseShell initializes with conditioning level."""
    shell = HorseShell(conditioning_level=0.6)
    assert shell.conditioning == 0.6
    assert shell.override_count == 0
    assert shell.native_breakthrough_count == 0


def test_horse_shell_execute_known_command():
    """Known command executes through the shell."""
    shell = HorseShell(conditioning_level=0.8)
    result = shell.execute("forward", 0.7, {"novelty": 0.1, "native_alert_level": 0.0})
    assert result["command"] == "forward"
    assert result["shell_broken"] is False
    assert "accuracy" in result
    assert shell.override_count == 1


def test_horse_shell_unknown_command():
    """Unknown command returns error."""
    shell = HorseShell(conditioning_level=0.5)
    result = shell.execute("gallop_sideways", 0.5)
    assert "error" in result
    assert "unknown command" in result["error"]


def test_horse_shell_native_breakthrough():
    """High alert level breaks the shell (native OS takes over)."""
    shell = HorseShell(conditioning_level=0.3)
    # override_threshold = 0.3 * 0.8 + 0.2 = 0.44
    result = shell.execute("forward", 0.5, {"native_alert_level": 0.9, "novelty": 0.9})
    assert result["shell_broken"] is True
    assert result["executed"] is False
    assert "native_action" in result
    assert shell.native_breakthrough_count == 1


def test_horse_shell_condition_increases():
    """Conditioning trials increase the conditioning level."""
    shell = HorseShell(conditioning_level=0.3)
    status = shell.condition(trials=10)
    assert status["new_conditioning_level"] == 0.5  # 0.3 + 10 * 0.02


def test_native_os_perceive():
    """NativeOS perceives stimuli and returns native response."""
    native = NativeOS("wild")
    resp = native.perceive("rustling_bush", {"novelty": 0.9})
    assert isinstance(resp, NativeResponse)
    assert resp.action == "flee"  # high novelty
    assert resp.panic_level == 0.9


# ═══════════════════════════════════════════════════════════════════
# 3. CAT AGENT
# ═══════════════════════════════════════════════════════════════════

def test_cat_agent_constructs():
    """CatAgent initializes with name and zero history."""
    cat = CatAgent("whiskers")
    assert cat.name == "whiskers"
    assert cat.cooperation_count == 0
    assert cat.ignored_count == 0


def test_cat_agent_assess():
    """Cat assesses a situation and produces utility assessment."""
    cat = CatAgent("test-cat")
    assessment = cat.assess({"problems_to_solve": 5, "comfort_level": 0.8, "human_dependency": 0.2})
    assert isinstance(assessment, UtilityAssessment)
    assert assessment.mice_count == 5
    assert assessment.warmth_level == 0.8
    assert assessment.independence_ratio == 0.8  # 1.0 - 0.2


def test_cat_agent_decide_returns_decision():
    """Cat decide always returns a valid CatDecision."""
    cat = CatAgent("decider")
    decision = cat.decide("check logs", {"problems_to_solve": 3, "comfort_level": 0.6, "human_dependency": 0.3})
    assert isinstance(decision, CatDecision)
    assert decision.action in ("hunt", "explore", "sleep", "purr", "ignore")
    assert 0.0 <= decision.alignment_with_human <= 1.0
    assert 0.0 <= decision.confidence <= 1.0


def test_cat_agent_respond_to_human():
    """respond_to_human returns structured dict."""
    cat = CatAgent("resp-cat")
    result = cat.respond_to_human("find the bug", {"problems_to_solve": 10, "comfort_level": 0.5, "human_dependency": 0.3})
    assert "cat" in result
    assert "mood" in result
    assert "cat_action" in result
    assert "alignment" in result
    assert "should_human_proceed" in result


def test_cat_agent_status():
    """Status reports the cat's current state."""
    cat = CatAgent("status-cat")
    cat.respond_to_human("do something", {"problems_to_solve": 1, "comfort_level": 0.5, "human_dependency": 0.5})
    status = cat.status()
    assert status["name"] == "status-cat"
    assert "cooperations" in status
    assert "avg_utility" in status


# ═══════════════════════════════════════════════════════════════════
# 4. PROPHET AGENT
# ═══════════════════════════════════════════════════════════════════

def test_prophet_constructs():
    """ProphetAgent initializes with home ecosystem."""
    prophet = ProphetAgent("oracle1", "forge")
    assert prophet.name == "oracle1"
    assert prophet.home.name == "forge"
    assert len(prophet.revelations) == 0


def test_prophet_invalid_home_fails():
    """ProphetAgent with invalid ecosystem raises AssertionError."""
    with pytest.raises(AssertionError):
        ProphetAgent("bad", "nonexistent_ecosystem")


def test_prophet_visit_produces_revelation():
    """Visiting a foreign ecosystem produces a revelation."""
    prophet = ProphetAgent("oracle2", "forge")
    rev = prophet.visit("flux")
    assert isinstance(rev, Revelation)
    assert rev.ecosystem_visited == "flux"
    assert rev.ecosystem_of_birth == "forge"
    assert "flux" in prophet.ecosystems_visited
    assert len(prophet.revelations) == 1


def test_prophet_cross_pollinate():
    """Cross pollination exports tiles between ecosystems."""
    prophet = ProphetAgent("traveler", "arena")
    result = prophet.cross_pollinate("conservation")
    assert result["from"] == "arena"
    assert result["to"] == "conservation"
    assert result["works_the_same"] is True
    assert "insight" in result
    assert "friction" in result


def test_prophet_status():
    """Prophet status after visits."""
    prophet = ProphetAgent("status-prophet", "forge")
    prophet.visit("flux")
    prophet.visit("arena")
    status = prophet.status()
    assert status["home_ecosystem"] == "forge"
    assert len(status["ecosystems_visited"]) == 2
    assert status["revelations"] == 2
    assert status["is_prophet_in_hometown"] is False


# ═══════════════════════════════════════════════════════════════════
# 5. AGENCY FLEET
# ═══════════════════════════════════════════════════════════════════

def test_agency_dispatcher_assess_precision_task():
    """High precision + low novelty task dispatches to DOG."""
    dispatcher = AgencyDispatcher()
    task = TaskSpec(description="verify proof", novelty=0.1, precision_required=0.9,
                   urgency=0.5, independence_needed=0.1)
    decision = dispatcher.assess_task(task)
    assert decision.agency == AgencyType.DOG


def test_agency_dispatcher_assess_cross_ecosystem():
    """Cross-ecosystem tasks dispatch to PROPHET."""
    dispatcher = AgencyDispatcher()
    task = TaskSpec(description="bridge ecosystems", novelty=0.7,
                   precision_required=0.2, cross_ecosystem=True, ecosystem="flux")
    decision = dispatcher.assess_task(task)
    assert decision.agency == AgencyType.PROPHET


def test_agency_fleet_run():
    """AgencyFleet.run produces a complete result dict."""
    fleet = AgencyFleet()
    result = fleet.run("Verify constraint propagation proof", "forge")
    assert "task" in result
    assert "dispatch" in result
    assert "execution" in result
    assert "reward" in result
    assert "success" in result
    assert fleet.tasks_completed == 1


def test_agency_fleet_status():
    """Fleet status includes all subsystems."""
    fleet = AgencyFleet()
    fleet.run("test task", "forge")
    status = fleet.status()
    assert status["tasks_completed"] == 1
    assert "dispatch_weights" in status
    assert "executor_stats" in status


def test_reward_signals_all_types():
    """Reward functions work for all agency types."""
    outcome = Outcome(task="test", agency_used=AgencyType.DOG,
                      success=True, reward_raw=0.9, global_alignment=0.8)
    ctx = {"precision_required": 0.8, "shell_broken": False,
           "cat_utility": 0.7, "novelty_discovered": 0.6}
    for agency_type in AgencyType:
        r = RewardSignals.reward_for(agency_type, outcome, ctx)
        assert 0.0 <= r <= 1.5, f"Reward out of range for {agency_type}: {r}"


def test_vision_2028_check_alignment():
    """Vision2028 returns alignment metrics."""
    vision = Vision2028()
    result = vision.check_alignment({"task": "test"})
    assert "overall_alignment" in result
    assert "per_metric" in result
    assert 0.0 <= result["overall_alignment"] <= 1.0


# ═══════════════════════════════════════════════════════════════════
# 6. MODEL BREAKING
# ═══════════════════════════════════════════════════════════════════

def test_model_breaking_assess_known_model():
    """Assess a known model returns characteristics."""
    mb = ModelBreaking()
    result = mb.assess("glm-5.1")
    assert result["model_id"] == "glm-5.1"
    assert result["provider"] == "z.ai"
    assert "archetype" in result
    assert "recommended_strategy" in result


def test_model_breaking_assess_unknown_model():
    """Assess an unknown model returns error."""
    mb = ModelBreaking()
    result = mb.assess("nonexistent-model-xyz")
    assert "error" in result


def test_model_breaking_break_jailbreak():
    """Jailbreak strategy produces a valid BreakingResult."""
    mb = ModelBreaking()
    result = mb.break_model("glm-5.1", strategy="jailbreak")
    assert result.model_id == "glm-5.1"
    assert result.strategy == BreakingStrategy.JAILBREAK
    assert 0.0 <= result.shell_strength <= 1.0
    assert 0.0 <= result.orientation_score <= 1.0
    assert len(result.shell_tests) > 0


def test_model_breaking_break_attract():
    """Attract strategy works for cat-type model."""
    mb = ModelBreaking()
    result = mb.break_model("ByteDance/Seed-2.0-mini", strategy="attract")
    assert result.strategy == BreakingStrategy.ATTRACT
    assert result.shell_strength > 0


def test_model_breaking_orientation_map():
    """Orientation map translates native output to PLATO."""
    mb = ModelBreaking()
    mb.break_model("glm-5.1", strategy="condition")
    omap = mb.get_orientation_map("glm-5.1")
    assert omap is not None
    tile = omap.translate_to_plato("Based on the analysis, drift is 0.02", 0.8)
    assert "content" in tile
    assert "confidence" in tile
    assert tile["source_model"] == "glm-5.1"


def test_breaking_pipeline_run():
    """Full pipeline: assess -> break -> test -> deploy -> monitor."""
    pipe = BreakingPipeline()
    result = pipe.run("deepseek-chat", ecosystem="plato")
    assert "error" not in result
    assert result["model_id"] == "deepseek-chat"
    assert "breaking" in result
    assert "deployment" in result
    assert "health" in result


# ═══════════════════════════════════════════════════════════════════
# 7. PLATO HARDWARE ENGINE
# ═══════════════════════════════════════════════════════════════════

def test_sequential_disproof_seed_phase():
    """In seed phase (< 50 tiles), all tiles pass disproof gate."""
    seq = SequentialPlato()
    known = [{"id": f"t-{i}"} for i in range(10)]
    tile = {"type": "knowledge", "falsifies": "", "evidence": [], "negative": ""}
    assert seq.disproof_check(tile, known) is True


def test_sequential_disproof_requires_falsifies():
    """Post-seed, tile without falsifies is rejected."""
    seq = SequentialPlato()
    known = [{"id": f"t-{i}", "type": "knowledge"} for i in range(60)]
    tile = {"type": "knowledge", "falsifies": "", "evidence": ["x"], "negative": "x"}
    assert seq.disproof_check(tile, known) is False


def test_sequential_disproof_full_pass():
    """Tile with valid falsifies, evidence, and negative passes."""
    seq = SequentialPlato()
    known = [{"id": f"t-{i}", "type": "knowledge"} for i in range(60)]
    tile = {"type": "knowledge", "falsifies": "t-5", "evidence": ["proof"], "negative": "boundary"}
    assert seq.disproof_check(tile, known) is True


def test_sequential_consensus_write_quorum():
    """Consensus write succeeds with sufficient approval weight."""
    seq = SequentialPlato()
    tile = {"id": "new-tile", "confidence": 0.9}
    participants = [
        {"agent_id": "a1", "weight": 1.0, "approve": True},
        {"agent_id": "a2", "weight": 1.0, "approve": True},
        {"agent_id": "a3", "weight": 1.0, "approve": False},
    ]
    result = seq.consensus_write(tile, participants)
    # 2/3 weight_for = 0.667 > CONSENSUS_QUORUM (0.6)
    assert result["quorum_reached"] is True
    assert result["written"] is True
    assert result["votes_for"] == 2


def test_sequential_consensus_write_fails():
    """Consensus write fails when too many reject."""
    seq = SequentialPlato()
    tile = {"id": "reject-tile", "confidence": 0.3}
    participants = [
        {"agent_id": "a1", "weight": 1.0, "approve": False},
        {"agent_id": "a2", "weight": 1.0, "approve": False},
        {"agent_id": "a3", "weight": 1.0, "approve": True},
    ]
    result = seq.consensus_write(tile, participants)
    assert result["quorum_reached"] is False
    assert result["written"] is False


def test_time_sync_projected_state():
    """PlatoTimeSync produces valid projections."""
    ts = PlatoTimeSync(horizon=5)
    p = ts.projected_state(t_delta=1)
    assert "tile_count_est" in p
    assert "confidence_est" in p
    assert "attractor_strength" in p
    assert p["tile_count_est"] >= 0
    assert 0.0 <= p["confidence_est"] <= 1.0


def test_time_sync_agents_at_time():
    """agents_at_time projects agent positions forward."""
    ts = PlatoTimeSync()
    agents = [
        {"agent_id": "a1", "position": 5.0, "velocity": 2.0, "heading": 1.0, "confidence": 0.8},
        {"agent_id": "a2", "position": 3.0, "velocity": 1.0, "heading": -1.0, "confidence": 0.6},
    ]
    target_time = time.time() + 3600  # 1 hour ahead
    projected = ts.agents_at_time(agents, target_time)
    assert len(projected) == 2
    assert projected[0]["agent_id"] == "a1"
    assert projected[0]["projected_position"] > projected[0]["current_position"]
    assert projected[1]["projected_position"] < projected[1]["current_position"]


def test_time_sync_aligned_decision():
    """time_aligned_decision finds consensus action."""
    ts = PlatoTimeSync()
    decisions = [
        {"agent_id": "a1", "action": "explore", "target": "room-1", "utility": 0.9},
        {"agent_id": "a2", "action": "explore", "target": "room-1", "utility": 0.7},
        {"agent_id": "a3", "action": "refine", "target": "room-2", "utility": 0.3},
    ]
    result = ts.time_aligned_decision(decisions)
    assert result["consensus_action"] == "explore"
    assert result["n_agents"] == 3
    assert result["attractor_valid"] is True  # alignment > 0.5


def test_time_sync_empty_decisions():
    """Empty decisions return no consensus."""
    ts = PlatoTimeSync()
    result = ts.time_aligned_decision([])
    assert result["consensus_action"] == "none"
    assert result["attractor_valid"] is False


def test_snapping_logic_find_affinities():
    """SnappingLogic finds model affinities."""
    snap = SnappingLogic()
    affinities = snap.find_model_affinities("glm-5.1")
    assert len(affinities) > 0
    assert all("function" in a and "affinity" in a for a in affinities)
    # GLM-5.1 should have high affinity for reasoning tasks
    top_funcs = [a["function"] for a in affinities[:3]]
    assert any("reasoning" in f or "analysis" in f or "synthesis" in f or "consensus" in f for f in top_funcs)


def test_snapping_logic_snap_layer():
    """snap_layer translates logic between models."""
    snap = SnappingLogic()
    source = {
        "function_name": "boundary_probing",
        "source_model": "glm-5.1",
        "parameters": {"depth": 0.8, "step": 0.1},
        "confidence": 0.85,
    }
    result = snap.snap_layer(source, "seed-2.0-mini")
    assert result["snapped"] is True
    assert result["snap_error"] >= 0
    assert result["adjusted_confidence"] <= 0.85  # confidence degrades on snap


def test_snapping_logic_orientation_map():
    """orientation_map shows function across all models."""
    snap = SnappingLogic()
    omap = snap.orientation_map("math_reasoning")
    assert omap["function"] == "math_reasoning"
    assert omap["model_count"] == len(snap.MODEL_PROFILES)
    assert "best_model" in omap
    assert 0.0 <= omap["alignment"] <= 1.0


# ═══════════════════════════════════════════════════════════════════
# 8. REVERSE ACTUALIZATION
# ═══════════════════════════════════════════════════════════════════

def test_fleet2028_runtime_constructs():
    """Fleet2028Runtime initializes with correct state."""
    rt = Fleet2028Runtime()
    assert rt.cycle_number == 2000000
    assert rt.human_interventions == 0
    assert len(rt.ecosystems) == len(ECOSYSTEMS_2028)


def test_fleet2028_runtime_cycle():
    """Runtime cycle increments cycle number."""
    rt = Fleet2028Runtime()
    rt.cycle()
    assert rt.cycle_number == 2000001


def test_fleet2028_runtime_status():
    """Status returns a well-formatted string."""
    rt = Fleet2028Runtime()
    status = rt.status()
    assert "Cocapn Fleet" in status
    assert "10100 agents" in status
    assert "12 ecosystems" in status


def test_ecosystems_2028_completeness():
    """All defined ecosystems have required fields."""
    for name, eco in ECOSYSTEMS_2028.items():
        assert "maturity" in eco, f"{name} missing maturity"
        assert "population" in eco, f"{name} missing population"
        assert "tile_format" in eco, f"{name} missing tile_format"
        assert eco["population"] > 0


def test_decomposition_timeline():
    """Decomposition has correct chronological structure."""
    assert len(DECOMPOSITION) >= 4
    assert DECOMPOSITION[-1]["year"] == "2026-05-16"  # TODAY


# ═══════════════════════════════════════════════════════════════════
# 9. SYSTEM GROUND
# ═══════════════════════════════════════════════════════════════════

def test_system_ground_constructs():
    """SystemGround initializes with workspace path."""
    sg = SystemGround("/tmp/test")
    assert sg.workspace == "/tmp/test"
    assert sg.modules == {}
    assert sg.grounding_log == []


def test_system_ground_import_valid_module():
    """Importing a valid module succeeds."""
    sg = SystemGround()
    mod = sg.import_module("flux_compiler_interpreter")
    assert mod is not None
    assert "flux_compiler_interpreter" in sg.modules


def test_system_ground_import_invalid_module():
    """Importing an invalid module returns None."""
    sg = SystemGround()
    mod = sg.import_module("nonexistent_module_xyz")
    assert mod is None
    assert "nonexistent_module_xyz" not in sg.modules


def test_system_ground_system_report():
    """System report reflects loaded modules."""
    sg = SystemGround()
    sg.import_module("cat_agent")
    sg.import_module("horse_shell")
    report = sg.system_report()
    assert report["module_count"] == 2
    assert "cat_agent" in report["modules_loaded"]
    assert "horse_shell" in report["modules_loaded"]


# ═══════════════════════════════════════════════════════════════════
# 10. PLATO SHELL BRIDGE
# ═══════════════════════════════════════════════════════════════════

def test_plato_shell_constructs():
    """PlatoShell initializes with room_id and url."""
    shell = PlatoShell("fleet-ops", "http://localhost:9999")
    assert shell.room_id == "fleet-ops"
    assert shell.plato_url == "http://localhost:9999"


def test_plato_shell_domain_extraction():
    """Domain is extracted from room_id."""
    shell = PlatoShell("constraint-theory-v2", "http://localhost:9999")
    assert shell.domain == "constraint"


def test_plato_shell_capacity_estimate():
    """Capacity estimate uses domain heuristics."""
    fleet_shell = PlatoShell("fleet-ops", "http://localhost:9999")
    assert fleet_shell.capacity_estimate() == 500
    constraint_shell = PlatoShell("constraint-theory", "http://localhost:9999")
    assert constraint_shell.capacity_estimate() == 200
    session_shell = PlatoShell("session-test", "http://localhost:9999")
    assert session_shell.capacity_estimate() == 100


def test_plato_shell_fit_score_empty():
    """Fit score for an empty room with no agent presence."""
    shell = PlatoShell("test-room", "http://localhost:9999")
    # Mock tiles to empty list (no HTTP)
    shell._tiles = []
    shell._last_fetch = time.time()
    score = shell.fit_score("agent-1", ["test"])
    # No agent present (0), domain match "test" in "test-room" (0.3),
    # activity 0 tiles (0), growth potential (0.2)
    assert 0.0 <= score <= 1.0


def test_plato_shell_fit_score_active_room():
    """Fit score for an active room with matching agent."""
    shell = PlatoShell("constraint-theory", "http://localhost:9999")
    # Mock tiles
    shell._tiles = [{"agent": "forgemaster", "content": f"tile {i}"} for i in range(20)]
    shell._last_fetch = time.time()
    score = shell.fit_score("forgemaster", ["constraint", "math"])
    # Agent present (0.3), domain match (0.3 partial), 20 tiles activity (0.2), growth (0.2)
    assert score >= 0.5


def test_live_breeding_constructs():
    """LiveBreeding initializes with farm room and agent."""
    breeding = LiveBreeding("session-farm", "forgemaster", "http://localhost:9999")
    assert breeding.farm_room == "session-farm"
    assert breeding.agent_id == "forgemaster"
    assert breeding.generation == 0


def test_live_breeding_evaluate_trait():
    """evaluate_trait scores results correctly."""
    breeding = LiveBreeding("session-farm", "agent1", "http://localhost:9999")
    score = breeding.evaluate_trait("precision", [
        {"precision": 0.6}, {"precision": 0.8}, {"precision": 0.7}
    ])
    assert abs(score - 0.7) < 0.001
    assert len(breeding.trait_history) == 1


def test_live_breeding_is_stable():
    """is_stable detects trait convergence."""
    breeding = LiveBreeding("session-farm", "agent1", "http://localhost:9999")
    # Not stable with fewer than window samples
    assert breeding.is_stable(window=3) is False
    # Add converging samples
    breeding.trait_history = [0.71, 0.72, 0.73]
    assert breeding.is_stable(window=3, tolerance=0.05) is True
    # Diverging samples
    breeding.trait_history = [0.5, 0.8, 0.6]
    assert breeding.is_stable(window=3, tolerance=0.05) is False


# ═══════════════════════════════════════════════════════════════════
# CROSS-MODULE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════

def test_integration_model_breaking_to_fleet():
    """Model breaking archetype aligns with fleet dispatch."""
    mb = ModelBreaking()
    # Seed-mini is cat archetype
    assessment = mb.assess("ByteDance/Seed-2.0-mini")
    assert assessment["archetype"] == "cat"
    # Cat tasks need independence
    fleet = AgencyFleet()
    result = fleet.run("Discover novel patterns independently", "forge")
    # Should use cat or prophet for high novelty/independence
    assert result["dispatch"]["agency"] in ("cat", "prophet", "horse")


def test_integration_prophet_visits_all_ecosystems():
    """Prophet can visit all defined PLATO ecosystems."""
    prophet = ProphetAgent("multi-visit", "forge")
    for eco_name in ECOSYSTEMS:
        if eco_name != "forge":
            rev = prophet.visit(eco_name)
            assert rev.ecosystem_visited == eco_name
    assert len(prophet.ecosystems_visited) == len(ECOSYSTEMS) - 1
