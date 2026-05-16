#!/usr/bin/env python3
"""
Study 55 (P2): Router Accuracy Over Time — Degradation & Conservation Prediction
==================================================================================

Simulation study using fleet_router_api classes directly (no live API calls).

Phases:
  A — Baseline routing accuracy (100 requests)
  B — Simulated degradation (drift in model accuracy)
  C — Recovery after self-healing quarantine
  D — Conservation as early warning predictor

Metrics tracked per round:
  - routing_accuracy: fraction of requests routed to models that would answer correctly
  - conservation_compliance: simulated γ+H compliance rate
  - alignment_score: simulated intent alignment
  - quarantine_events: count of quarantines
  - active_models: count of available models
"""

import json
import random
import math
import time
import sys
import os
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# Add workspace to path for imports
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))

from fleet_router_api import (
    ModelRegistry, ModelTierEnum, CriticalAngleRouter, RoutingStats,
    SelfHealingMixin, QuarantineConfig, ExpertHealthRecord,
    DEFAULT_MODELS, TIER_ACCURACY, PREFERRED_ORDER,
)


# ---------------------------------------------------------------------------
# Simulation Helpers
# ---------------------------------------------------------------------------

# Base accuracy per model (realistic from Study 50)
BASE_ACCURACY = {
    "ByteDance/Seed-2.0-mini": 0.97,
    "ByteDance/Seed-2.0-code": 0.95,
    "gemma3:1b": 0.94,
    "Qwen/Qwen3-235B-A22B-Instruct-2507": 0.78,
    "deepseek-chat": 0.75,
    "NousResearch/Hermes-3-Llama-3.1-70B": 0.72,
    "phi4-mini": 0.68,
    "llama3.2:1b": 0.62,
    "Qwen/Qwen3.6-35B-A3B": 0.15,
    "qwen3:4b": 0.12,
    "qwen3:0.6b": 0.08,
}

TASK_TYPES = ["eisenstein_norm", "eisenstein_snap", "mobius", "legendre",
              "modular_inverse", "cyclotomic_eval", "generic"]

SIMULATED_PARAMS = {
    "eisenstein_norm": {"a": 3, "b": 5},
    "eisenstein_snap": {"x": 1.7, "y": 2.3},
    "mobius": {"n": 30},
    "legendre": {"a": 5, "p": 11},
    "modular_inverse": {"a": 7, "m": 11},
    "cyclotomic_eval": {"n": 6, "x": 2},
    "generic": {"expression": "2+2"},
}


@dataclass
class SimModel:
    """Tracks simulated accuracy for a model over time."""
    model_id: str
    tier: int
    base_accuracy: float
    current_accuracy: float
    drift_rate: float = 0.0  # per-round accuracy change
    queries: int = 0
    correct: int = 0
    accuracy_history: List[float] = field(default_factory=list)

    def simulate_answer(self) -> bool:
        """Simulate whether this model answers correctly."""
        self.queries += 1
        correct = random.random() < self.current_accuracy
        if correct:
            self.correct += 1
        self.accuracy_history.append(self.current_accuracy)
        return correct

    def apply_drift(self):
        """Apply drift for one round."""
        self.current_accuracy = max(0.0, min(1.0, self.current_accuracy + self.drift_rate))


@dataclass
class RoundResult:
    """Results from one routing round."""
    round_num: int
    phase: str
    model_chosen: str
    tier: int
    correct: bool
    simulated_accuracy: float
    conservation_compliance: float
    alignment_score: float
    active_models: int
    quarantined_models: int
    downgraded: bool
    rejected: bool


@dataclass
class StudyResult:
    """Full study results."""
    phase_a_baseline: Dict[str, Any]
    phase_b_degradation: Dict[str, Any]
    phase_c_recovery: Dict[str, Any]
    phase_d_prediction: Dict[str, Any]
    all_rounds: List[Dict[str, Any]]
    summary: Dict[str, Any]


# ---------------------------------------------------------------------------
# Conservation / Alignment Simulation
# ---------------------------------------------------------------------------

def simulate_conservation(accuracies: Dict[str, float], round_num: int,
                          degradation_active: bool = False) -> Tuple[float, float]:
    """Simulate conservation compliance and alignment from model accuracies.

    When models degrade, conservation drops because the "law" (accurate answers)
    is being violated. Alignment drops as models' intent vectors drift.
    """
    # Conservation: average of top-k model accuracies (models that should be correct)
    tier1_accs = [acc for mid, acc in accuracies.items()
                  if BASE_ACCURACY.get(mid, 0) >= 0.9]
    tier2_accs = [acc for mid, acc in accuracies.items()
                  if 0.5 <= BASE_ACCURACY.get(mid, 0) < 0.9]

    if tier1_accs:
        compliance = sum(tier1_accs) / len(tier1_accs)
    else:
        compliance = 0.5

    # Alignment: correlation between expected and actual performance
    if len(accuracies) >= 3:
        expected = [BASE_ACCURACY.get(mid, 0.5) for mid in accuracies]
        actual = [accuracies[mid] for mid in accuracies]
        # Simple correlation
        n = len(expected)
        mean_e = sum(expected) / n
        mean_a = sum(actual) / n
        cov = sum((e - mean_e) * (a - mean_a) for e, a in zip(expected, actual))
        var_e = sum((e - mean_e) ** 2 for e in expected)
        var_a = sum((a - mean_a) ** 2 for a in actual)
        denom = (var_e * var_a) ** 0.5
        alignment = cov / denom if denom > 0 else 0.0
        alignment = max(0.0, min(1.0, (alignment + 1) / 2))  # normalize to 0-1
    else:
        alignment = 0.8

    # Add some noise
    compliance += random.gauss(0, 0.01)
    alignment += random.gauss(0, 0.01)

    return max(0.0, min(1.0, compliance)), max(0.0, min(1.0, alignment))


# ---------------------------------------------------------------------------
# Main Simulation
# ---------------------------------------------------------------------------

def run_study() -> StudyResult:
    random.seed(42)  # reproducibility

    # Initialize simulated models
    sim_models: Dict[str, SimModel] = {}
    for model_id, tier in DEFAULT_MODELS.items():
        base = BASE_ACCURACY.get(model_id, 0.5)
        sim_models[model_id] = SimModel(
            model_id=model_id, tier=tier.value,
            base_accuracy=base, current_accuracy=base,
        )

    # Create router components
    registry = ModelRegistry()
    stats = RoutingStats()
    for model_id, tier in DEFAULT_MODELS.items():
        registry.register(model_id, tier)

    config = QuarantineConfig(
        min_active_experts=4,
        consecutive_for_quarantine=2,
        clean_for_restore=3,
        progressive_rounds=[5, 10, 0],
        intent_similarity_threshold=0.85,
        answer_error_threshold=0.5,
        conservation_threshold=0.85,
    )

    router = CriticalAngleRouter(registry, stats)
    healing = SelfHealingMixin(registry, config)

    all_rounds: List[RoundResult] = []
    conservation_history: List[float] = []
    accuracy_history: List[float] = []

    # =======================================================================
    # PHASE A: Baseline (100 requests, no drift)
    # =======================================================================
    print("=" * 60)
    print("PHASE A: Baseline Routing Accuracy (100 requests)")
    print("=" * 60)

    phase_a_results = []
    for i in range(100):
        task = random.choice(TASK_TYPES)
        params = SIMULATED_PARAMS[task]

        # Get current accuracies for conservation sim
        current_accs = {mid: m.current_accuracy for mid, m in sim_models.items()}
        compliance, alignment = simulate_conservation(current_accs, i)

        router.set_conservation_state(compliance, alignment)

        # Route
        result = router.route_request(task, params)
        model_id = result.get("model_id")
        tier = result.get("tier", 3)

        # Simulate answer
        correct = False
        if model_id and model_id in sim_models:
            correct = sim_models[model_id].simulate_answer()

        # Health check (simulate intent vectors)
        if model_id and model_id in sim_models:
            intent = [random.gauss(0, 1) for _ in range(9)]
            answer = random.gauss(10, 2) if correct else random.gauss(5, 3)
            fleet_answers = [random.gauss(10, 1.5) for _ in range(5)]
            healing.check_expert_health(model_id, intent, answer, fleet_answers)

        rr = RoundResult(
            round_num=i, phase="A",
            model_chosen=model_id or "none", tier=tier, correct=correct,
            simulated_accuracy=sim_models[model_id].current_accuracy if model_id and model_id in sim_models else 0.0,
            conservation_compliance=compliance, alignment_score=alignment,
            active_models=sum(1 for e in registry._models.values() if e.available),
            quarantined_models=len(healing.get_quarantined_experts()),
            downgraded=result.get("downgraded", False),
            rejected=result.get("rejected", False),
        )
        phase_a_results.append(rr)
        all_rounds.append(rr)
        conservation_history.append(compliance)
        accuracy_history.append(1.0 if correct else 0.0)

    # Phase A summary
    a_correct = sum(1 for r in phase_a_results if r.correct)
    a_total = len(phase_a_results)
    a_accuracy = a_correct / a_total
    a_tier_dist = defaultdict(int)
    for r in phase_a_results:
        a_tier_dist[f"tier_{r.tier}"] += 1
    a_model_dist = defaultdict(int)
    for r in phase_a_results:
        a_model_dist[r.model_chosen] += 1

    print(f"  Baseline accuracy: {a_accuracy:.2%} ({a_correct}/{a_total})")
    print(f"  Tier distribution: {dict(a_tier_dist)}")
    print(f"  Top models: {dict(sorted(a_model_dist.items(), key=lambda x: -x[1])[:5])}")
    print(f"  Avg conservation: {sum(r.conservation_compliance for r in phase_a_results)/len(phase_a_results):.3f}")
    print(f"  Avg alignment: {sum(r.alignment_score for r in phase_a_results)/len(phase_a_results):.3f}")
    print()

    phase_a_summary = {
        "accuracy": round(a_accuracy, 4),
        "correct": a_correct,
        "total": a_total,
        "tier_distribution": dict(a_tier_dist),
        "model_distribution": dict(a_model_dist),
        "avg_conservation": round(sum(r.conservation_compliance for r in phase_a_results) / len(phase_a_results), 4),
        "avg_alignment": round(sum(r.alignment_score for r in phase_a_results) / len(phase_a_results), 4),
        "active_models": phase_a_results[-1].active_models,
        "quarantined": phase_a_results[-1].quarantined_models,
    }

    # =======================================================================
    # PHASE B: Simulated Degradation (200 requests, drift applied)
    # =======================================================================
    print("=" * 60)
    print("PHASE B: Simulated Degradation (200 requests with drift)")
    print("=" * 60)

    # Apply drift rates
    # Tier 1: -2% per 20 requests = -0.1% per request
    # Tier 2: -5% per 20 requests = -0.25% per request
    for mid, model in sim_models.items():
        if model.tier == 1:
            model.drift_rate = -0.001  # -0.1% per request
        elif model.tier == 2:
            model.drift_rate = -0.0025  # -0.25% per request
        else:
            model.drift_rate = 0.0  # Tier 3 already bad

    phase_b_results = []
    phase_b_windows = []  # 20-request windows for analysis
    current_window = []

    for i in range(200):
        round_num = 100 + i

        # Apply drift
        for model in sim_models.values():
            model.apply_drift()

        task = random.choice(TASK_TYPES)
        params = SIMULATED_PARAMS[task]

        # Conservation
        current_accs = {mid: m.current_accuracy for mid, m in sim_models.items()}
        compliance, alignment = simulate_conservation(current_accs, round_num, degradation_active=True)

        router.set_conservation_state(compliance, alignment)
        healing.set_conservation_rate(compliance)

        # Route
        result = router.route_request(task, params)
        model_id = result.get("model_id")
        tier = result.get("tier", 3)

        # Simulate answer
        correct = False
        sim_acc = 0.0
        if model_id and model_id in sim_models:
            correct = sim_models[model_id].simulate_answer()
            sim_acc = sim_models[model_id].current_accuracy

        # Health check with degraded signals
        if model_id and model_id in sim_models:
            # Degraded models have more noisy intent vectors
            noise_scale = 1.0 + (1.0 - sim_models[model_id].current_accuracy) * 2
            intent = [random.gauss(0, noise_scale) for _ in range(9)]
            # Degraded answers drift from truth
            truth = 10.0
            answer = truth + random.gauss(0, (1.0 - sim_models[model_id].current_accuracy) * 10)
            fleet_answers = [truth + random.gauss(0, 1.5) for _ in range(5)]
            healing.check_expert_health(model_id, intent, answer, fleet_answers)

        rr = RoundResult(
            round_num=round_num, phase="B",
            model_chosen=model_id or "none", tier=tier, correct=correct,
            simulated_accuracy=sim_acc,
            conservation_compliance=compliance, alignment_score=alignment,
            active_models=sum(1 for e in registry._models.values() if e.available),
            quarantined_models=len(healing.get_quarantined_experts()),
            downgraded=result.get("downgraded", False),
            rejected=result.get("rejected", False),
        )
        phase_b_results.append(rr)
        all_rounds.append(rr)
        conservation_history.append(compliance)
        accuracy_history.append(1.0 if correct else 0.0)

        # Tick recovery for quarantined models
        healing.tick_recovery()

        current_window.append(rr)
        if len(current_window) == 20:
            w_acc = sum(1 for r in current_window if r.correct) / 20
            w_cons = sum(r.conservation_compliance for r in current_window) / 20
            w_align = sum(r.alignment_score for r in current_window) / 20
            phase_b_windows.append({
                "window_start": current_window[0].round_num,
                "window_end": current_window[-1].round_num,
                "accuracy": round(w_acc, 4),
                "conservation": round(w_cons, 4),
                "alignment": round(w_align, 4),
                "active_models": current_window[-1].active_models,
                "quarantined": current_window[-1].quarantined_models,
            })
            current_window = []

    # Phase B summary
    b_correct = sum(1 for r in phase_b_results if r.correct)
    b_total = len(phase_b_results)
    b_accuracy = b_correct / b_total

    print(f"  Degraded accuracy: {b_accuracy:.2%} ({b_correct}/{b_total})")
    print(f"  Window-by-window accuracy:")
    for w in phase_b_windows:
        bar = "█" * int(w["accuracy"] * 40) + "░" * (40 - int(w["accuracy"] * 40))
        print(f"    [{w['window_start']:3d}-{w['window_end']:3d}] {bar} {w['accuracy']:.2%}  cons={w['conservation']:.3f}  quarantined={w['quarantined']}")
    print(f"  First window: {phase_b_windows[0]['accuracy']:.2%}")
    print(f"  Last window:  {phase_b_windows[-1]['accuracy']:.2%}")
    print(f"  Accuracy drop: {phase_b_windows[0]['accuracy'] - phase_b_windows[-1]['accuracy']:.2%}")
    print(f"  Quarantined models: {len(healing.get_quarantined_experts())}")
    print()

    phase_b_summary = {
        "accuracy": round(b_accuracy, 4),
        "first_window_accuracy": phase_b_windows[0]["accuracy"],
        "last_window_accuracy": phase_b_windows[-1]["accuracy"],
        "accuracy_drop": round(phase_b_windows[0]["accuracy"] - phase_b_windows[-1]["accuracy"], 4),
        "windows": phase_b_windows,
        "quarantined_count": len(healing.get_quarantined_experts()),
        "quarantined_models": [q["expert_id"] for q in healing.get_quarantined_experts()],
        "active_models": phase_b_results[-1].active_models,
        "conservation_first": phase_b_windows[0]["conservation"],
        "conservation_last": phase_b_windows[-1]["conservation"],
        "conservation_drop": round(phase_b_windows[0]["conservation"] - phase_b_windows[-1]["conservation"], 4),
    }

    # =======================================================================
    # PHASE C: Recovery (100 requests, drift stopped, quarantine recovery)
    # =======================================================================
    print("=" * 60)
    print("PHASE C: Recovery (100 requests, drift stopped)")
    print("=" * 60)

    # Stop drift
    for model in sim_models.values():
        model.drift_rate = 0.0

    phase_c_results = []
    for i in range(100):
        round_num = 300 + i

        # Small natural recovery: models slowly regain accuracy (up to base)
        for mid, model in sim_models.items():
            if model.current_accuracy < model.base_accuracy:
                model.current_accuracy = min(
                    model.base_accuracy,
                    model.current_accuracy + 0.002  # +0.2% per request
                )

        task = random.choice(TASK_TYPES)
        params = SIMULATED_PARAMS[task]

        # Conservation improves as models recover
        current_accs = {mid: m.current_accuracy for mid, m in sim_models.items()}
        compliance, alignment = simulate_conservation(current_accs, round_num)

        router.set_conservation_state(compliance, alignment)
        healing.set_conservation_rate(compliance)

        result = router.route_request(task, params)
        model_id = result.get("model_id")
        tier = result.get("tier", 3)

        correct = False
        sim_acc = 0.0
        if model_id and model_id in sim_models:
            correct = sim_models[model_id].simulate_answer()
            sim_acc = sim_models[model_id].current_accuracy

        # Health check with improving signals
        if model_id and model_id in sim_models:
            noise_scale = max(1.0, 1.0 + (1.0 - sim_models[model_id].current_accuracy) * 2)
            intent = [random.gauss(0, noise_scale) for _ in range(9)]
            truth = 10.0
            answer = truth + random.gauss(0, (1.0 - sim_models[model_id].current_accuracy) * 10)
            fleet_answers = [truth + random.gauss(0, 1.5) for _ in range(5)]
            healing.check_expert_health(model_id, intent, answer, fleet_answers)

        rr = RoundResult(
            round_num=round_num, phase="C",
            model_chosen=model_id or "none", tier=tier, correct=correct,
            simulated_accuracy=sim_acc,
            conservation_compliance=compliance, alignment_score=alignment,
            active_models=sum(1 for e in registry._models.values() if e.available),
            quarantined_models=len(healing.get_quarantined_experts()),
            downgraded=result.get("downgraded", False),
            rejected=result.get("rejected", False),
        )
        phase_c_results.append(rr)
        all_rounds.append(rr)
        conservation_history.append(compliance)
        accuracy_history.append(1.0 if correct else 0.0)

        # Tick recovery
        healing.tick_recovery()

    # Phase C in 20-request windows
    phase_c_windows = []
    for start in range(0, 100, 20):
        window = phase_c_results[start:start+20]
        if len(window) == 20:
            w_acc = sum(1 for r in window if r.correct) / 20
            w_cons = sum(r.conservation_compliance for r in window) / 20
            phase_c_windows.append({
                "window_start": window[0].round_num,
                "window_end": window[-1].round_num,
                "accuracy": round(w_acc, 4),
                "conservation": round(w_cons, 4),
                "active_models": window[-1].active_models,
                "quarantined": window[-1].quarantined_models,
            })

    c_correct = sum(1 for r in phase_c_results if r.correct)
    c_total = len(phase_c_results)
    c_accuracy = c_correct / c_total

    print(f"  Recovery accuracy: {c_accuracy:.2%} ({c_correct}/{c_total})")
    for w in phase_c_windows:
        bar = "█" * int(w["accuracy"] * 40) + "░" * (40 - int(w["accuracy"] * 40))
        print(f"    [{w['window_start']:3d}-{w['window_end']:3d}] {bar} {w['accuracy']:.2%}  cons={w['conservation']:.3f}  quarantined={w['quarantined']}")
    print(f"  Active models: {phase_c_results[-1].active_models}")
    print(f"  Quarantined models: {phase_c_results[-1].quarantined_models}")
    print()

    phase_c_summary = {
        "accuracy": round(c_accuracy, 4),
        "first_window_accuracy": phase_c_windows[0]["accuracy"] if phase_c_windows else None,
        "last_window_accuracy": phase_c_windows[-1]["accuracy"] if phase_c_windows else None,
        "recovery_lift": round(c_accuracy - b_accuracy, 4),
        "windows": phase_c_windows,
        "final_active_models": phase_c_results[-1].active_models,
        "final_quarantined": phase_c_results[-1].quarantined_models,
        "restored_to_baseline": c_accuracy >= a_accuracy * 0.95,
    }

    # =======================================================================
    # PHASE D: Conservation as Predictor
    # =======================================================================
    print("=" * 60)
    print("PHASE D: Conservation as Early Warning Predictor")
    print("=" * 60)

    # Compute rolling correlations between conservation and accuracy
    window_size = 20
    correlations = []
    lead_correlations = []  # conservation at t predicts accuracy at t+5

    for start in range(0, len(all_rounds) - window_size - 5, 5):
        window_cons = [r.conservation_compliance for r in all_rounds[start:start+window_size]]
        window_acc = [1.0 if r.correct else 0.0 for r in all_rounds[start:start+window_size]]

        # Pearson correlation
        n = len(window_cons)
        mean_c = sum(window_cons) / n
        mean_a = sum(window_acc) / n
        cov = sum((c - mean_c) * (a - mean_a) for c, a in zip(window_cons, window_acc))
        var_c = sum((c - mean_c) ** 2 for c in window_cons)
        var_a = sum((a - mean_a) ** 2 for a in window_acc)
        denom = (var_c * var_a) ** 0.5
        corr = cov / denom if denom > 0 else 0.0

        correlations.append({
            "round_start": start,
            "round_end": start + window_size,
            "correlation": round(corr, 4),
            "phase": all_rounds[start].phase,
        })

    # Lead correlation: conservation predicts accuracy N rounds ahead
    lead_n = 10
    for start in range(0, len(all_rounds) - window_size - lead_n, 5):
        window_cons = [r.conservation_compliance for r in all_rounds[start:start+window_size]]
        future_acc = [1.0 if r.correct else 0.0 for r in all_rounds[start+lead_n:start+lead_n+window_size]]

        if len(future_acc) < window_size:
            continue

        n = len(window_cons)
        mean_c = sum(window_cons) / n
        mean_a = sum(future_acc) / n
        cov = sum((c - mean_c) * (a - mean_a) for c, a in zip(window_cons, future_acc))
        var_c = sum((c - mean_c) ** 2 for c in window_cons)
        var_a = sum((a - mean_a) ** 2 for a in future_acc)
        denom = (var_c * var_a) ** 0.5
        corr = cov / denom if denom > 0 else 0.0

        lead_correlations.append({
            "round_start": start,
            "lead_rounds": lead_n,
            "correlation": round(corr, 4),
            "phase": all_rounds[start].phase,
        })

    # Phase D analysis
    # When did conservation drop below 0.85 vs when did accuracy drop below 90%?
    cons_drop_round = None
    acc_drop_round = None
    for i, r in enumerate(all_rounds):
        if cons_drop_round is None and r.conservation_compliance < 0.85:
            cons_drop_round = r.round_num
        if acc_drop_round is None and not r.correct and r.phase == "B":
            acc_drop_round = r.round_num
            break

    lead_time = None
    if cons_drop_round is not None and acc_drop_round is not None:
        lead_time = acc_drop_round - cons_drop_round

    # Average correlations by phase
    corr_by_phase = defaultdict(list)
    for c in correlations:
        corr_by_phase[c["phase"]].append(c["correlation"])

    lead_corr_by_phase = defaultdict(list)
    for c in lead_correlations:
        lead_corr_by_phase[c["phase"]].append(c["correlation"])

    print(f"  Conservation drop below 85%: round {cons_drop_round}")
    print(f"  First accuracy failure (Phase B): round {acc_drop_round}")
    print(f"  Early warning lead time: {lead_time} rounds" if lead_time else "  Lead time: N/A")
    print()
    print("  Correlation (conservation ↔ accuracy) by phase:")
    for phase, corrs in corr_by_phase.items():
        avg_corr = sum(corrs) / len(corrs) if corrs else 0
        print(f"    Phase {phase}: r = {avg_corr:.3f} (n={len(corrs)})")
    print()
    print(f"  Lead correlation (conservation[t] → accuracy[t+{lead_n}]):")
    for phase, corrs in lead_corr_by_phase.items():
        avg_corr = sum(corrs) / len(corrs) if corrs else 0
        print(f"    Phase {phase}: r = {avg_corr:.3f} (n={len(corrs)})")
    print()

    phase_d_summary = {
        "conservation_drop_round": cons_drop_round,
        "accuracy_drop_round": acc_drop_round,
        "early_warning_lead_rounds": lead_time,
        "correlation_by_phase": {
            phase: round(sum(c) / len(c), 4) if c else 0
            for phase, c in corr_by_phase.items()
        },
        "lead_correlation_by_phase": {
            phase: round(sum(c) / len(c), 4) if c else 0
            for phase, c in lead_corr_by_phase.items()
        },
        "conservation_predicts_degradation": lead_time is not None and lead_time > 0,
        "all_correlations": correlations,
    }

    # =======================================================================
    # Overall Summary
    # =======================================================================
    print("=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)

    total_correct = sum(1 for r in all_rounds if r.correct)
    total_requests = len(all_rounds)

    summary = {
        "total_requests": total_requests,
        "total_correct": total_correct,
        "overall_accuracy": round(total_correct / total_requests, 4),
        "phase_a_baseline": a_accuracy,
        "phase_b_degraded": b_accuracy,
        "phase_c_recovered": c_accuracy,
        "degradation_magnitude": round(a_accuracy - b_accuracy, 4),
        "recovery_ratio": round((c_accuracy - b_accuracy) / (a_accuracy - b_accuracy), 4) if a_accuracy != b_accuracy else None,
        "conservation_early_warning": lead_time is not None and lead_time > 0,
        "conservation_lead_rounds": lead_time,
        "key_findings": [],
    }

    findings = []
    findings.append(
        f"1. Baseline accuracy: {a_accuracy:.1%}, degraded to {b_accuracy:.1%} "
        f"({(a_accuracy-b_accuracy)*100:.1f}pp drop), recovered to {c_accuracy:.1%}"
    )
    findings.append(
        f"2. Degradation primarily in Tier 2 models "
        f"(-5%/20 requests vs -2%/20 for Tier 1)"
    )
    findings.append(
        f"3. Self-healing quarantined {phase_b_summary['quarantined_count']} models "
        f"during degradation phase"
    )
    if lead_time is not None and lead_time > 0:
        findings.append(
            f"4. Conservation compliance dropped {lead_time} rounds BEFORE accuracy — "
            f"USEFUL as early warning signal"
        )
    else:
        findings.append(
            f"4. Conservation compliance did NOT reliably precede accuracy drops "
            f"in this simulation"
        )

    recovery_pct = ((c_accuracy - b_accuracy) / (a_accuracy - b_accuracy) * 100) if a_accuracy != b_accuracy else 0
    findings.append(
        f"5. Recovery achieved {recovery_pct:.0f}% of baseline accuracy "
        f"after 100 rounds with drift stopped"
    )

    # Conservation-accuracy correlation
    avg_corr = sum(c["correlation"] for c in correlations) / len(correlations) if correlations else 0
    findings.append(
        f"6. Conservation-accuracy correlation: r = {avg_corr:.3f} "
        f"({'strong' if abs(avg_corr) > 0.5 else 'moderate' if abs(avg_corr) > 0.3 else 'weak'})"
    )

    for f in findings:
        print(f"  {f}")
        summary["key_findings"].append(f)

    print()

    # =======================================================================
    # Save results
    # =======================================================================
    study_result = StudyResult(
        phase_a_baseline=phase_a_summary,
        phase_b_degradation=phase_b_summary,
        phase_c_recovery=phase_c_summary,
        phase_d_prediction=phase_d_summary,
        all_rounds=[asdict(r) for r in all_rounds],
        summary=summary,
    )

    results_path = os.path.expanduser("~/.openclaw/workspace/experiments/study55_results.json")
    with open(results_path, "w") as f:
        json.dump(asdict(study_result), f, indent=2)
    print(f"Results saved to {results_path}")

    return study_result


if __name__ == "__main__":
    result = run_study()
