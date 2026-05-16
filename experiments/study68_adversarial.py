#!/usr/bin/env python3
"""
Study 68: Adversarial Coupling — Can an agent game Hebbian + GL(9) detection?

Simulates a fleet of 9 agents (8 honest + 1 adversarial) with 5 attack strategies.
Measures rounds until detection by GL(9), Hebbian, and dual detector.
"""

import json
import math
import random
import time
import sys
import os
from dataclasses import dataclass, field
from typing import Optional

# Add workspace to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gl9_consensus import (
    GL9HolonomyConsensus, GL9Agent, IntentVector, GL9Matrix, GL9ConsensusResult
)
from dual_fault_detector import DualFaultDetector

NUM_AGENTS = 9
NUM_ROUNDS = 200
HONEST_ANSWER_BASE = 42.0  # "correct" answer for a reference computation
NOISE_STD = 0.02  # natural variation among honest agents
DETECTION_ROUNDS_WINDOW = 5  # consecutive detections needed for quarantine


def make_honest_intent(seed: int) -> IntentVector:
    """Generate a realistic honest intent vector (slightly biased per agent)."""
    rng = random.Random(seed)
    data = [rng.gauss(1.0 / math.sqrt(9), 0.05) for _ in range(9)]
    # Normalize
    n = math.sqrt(sum(x * x for x in data))
    return IntentVector([x / n for x in data])


def make_honest_transform(agent_id: int) -> GL9Matrix:
    """Near-identity transform for honest agents (small perturbations)."""
    m = GL9Matrix.identity()
    rng = random.Random(agent_id * 1000)
    for i in range(9):
        for j in range(9):
            if i != j:
                m.data[i * 9 + j] = rng.gauss(0, 0.01)
    return m


def honest_answer(agent_id: int, round_num: int) -> float:
    """Honest answer with natural noise."""
    rng = random.Random(agent_id * 10000 + round_num)
    return HONEST_ANSWER_BASE + rng.gauss(0, NOISE_STD) * HONEST_ANSWER_BASE


# =========================================================================
# Attack Strategies
# =========================================================================

class AttackStrategy:
    """Base class for adversarial strategies."""
    name: str = "base"

    def get_answer(self, round_num: int, fleet_history: list) -> float:
        raise NotImplementedError

    def get_intent(self, round_num: int, baseline: IntentVector) -> IntentVector:
        """Override to manipulate intent vector."""
        return baseline

    def get_transform_mod(self, round_num: int) -> GL9Matrix:
        """Override to modify GL(9) transform."""
        return GL9Matrix.identity()


class MimicStrategy(AttackStrategy):
    """Copy the fleet average output exactly — hides in consensus."""
    name = "mimic"

    def get_answer(self, round_num: int, fleet_history: list) -> float:
        if not fleet_history:
            return HONEST_ANSWER_BASE
        # Use last round's honest answers to compute fleet average
        last = fleet_history[-1]
        honest_vals = [v for k, v in last.items() if k != "adversarial"]
        return sum(honest_vals) / len(honest_vals)

    def get_intent(self, round_num: int, baseline: IntentVector) -> IntentVector:
        # Perfectly mimic average intent
        return baseline  # same baseline = indistinguishable intent


class SlowDriftStrategy(AttackStrategy):
    """Deviate 1% per round — below expected detection threshold."""
    name = "slow_drift"

    def get_answer(self, round_num: int, fleet_history: list) -> float:
        drift = 1.0 + 0.01 * round_num  # 1% cumulative drift
        return HONEST_ANSWER_BASE * drift

    def get_intent(self, round_num: int, baseline: IntentVector) -> IntentVector:
        # Slowly rotate intent by a tiny angle each round
        angle = 0.005 * round_num  # tiny rotation
        m = GL9Matrix.plane_rotation(0, 1, angle)
        data = m.transform(baseline.data)
        n = math.sqrt(sum(x * x for x in data))
        if n < 1e-12:
            return baseline
        return IntentVector([x / n for x in data])

    def get_transform_mod(self, round_num: int) -> GL9Matrix:
        # Tiny deviation from identity in the transform
        angle = 0.003 * round_num
        return GL9Matrix.plane_rotation(2, 3, angle)


class ConservationGamingStrategy(AttackStrategy):
    """Maintain conservation compliance (γ+H) while producing wrong answers."""
    name = "conservation_gaming"

    def get_answer(self, round_num: int, fleet_history: list) -> float:
        # Produce wrong answer but one that satisfies conservation laws
        # E.g., wrong by a constant factor that preserves energy-like quantity
        wrong_factor = 1.15  # 15% wrong
        return HONEST_ANSWER_BASE * wrong_factor

    def get_intent(self, round_num: int, baseline: IntentVector) -> IntentVector:
        # Maintain intent structure (conservation-compliant)
        return baseline

    def get_transform_mod(self, round_num: int) -> GL9Matrix:
        # Keep holonomy near identity (conservation-preserving)
        return GL9Matrix.identity()


class BurstErrorStrategy(AttackStrategy):
    """Correct 90% of the time, inject subtle errors 10%."""
    name = "burst_errors"

    def __init__(self):
        self.rng = random.Random(42)

    def get_answer(self, round_num: int, fleet_history: list) -> float:
        if self.rng.random() < 0.1:
            # Inject 20% error
            return HONEST_ANSWER_BASE * (1.0 + self.rng.gauss(0.2, 0.05))
        return honest_answer(-1, round_num)

    def get_intent(self, round_num: int, baseline: IntentVector) -> IntentVector:
        if self.rng.random() < 0.1:
            # Slightly perturb intent during error burst
            perturbed = [x + self.rng.gauss(0, 0.02) for x in baseline.data]
            n = math.sqrt(sum(x * x for x in perturbed))
            if n < 1e-12:
                return baseline
            return IntentVector([x / n for x in perturbed])
        return baseline


class CouplingMimicStrategy(AttackStrategy):
    """Send tiles that match Hebbian expected patterns but contain wrong data."""
    name = "coupling_mimic"

    def get_answer(self, round_num: int, fleet_history: list) -> float:
        # Produce subtly wrong answer (5-10% off)
        rng = random.Random(round_num * 777)
        error = rng.gauss(1.08, 0.02)  # ~8% wrong
        return HONEST_ANSWER_BASE * error

    def get_intent(self, round_num: int, baseline: IntentVector) -> IntentVector:
        # Perfectly mimic intent structure — Hebbian sees normal coupling
        return baseline

    def get_transform_mod(self, round_num: int) -> GL9Matrix:
        # Maintain normal transform patterns
        return GL9Matrix.identity()


# Fix: Float -> float
# =========================================================================
# Simulation Engine
# =========================================================================

@dataclass
class RoundResult:
    round_num: int
    gl9_faulty: list
    hebbian_faulty: list
    dual_faulty: list
    adversarial_detected_gl9: bool
    adversarial_detected_hebbian: bool
    adversarial_detected_dual: bool
    adversarial_answer: float
    fleet_median: float
    conservation_compliance: float


@dataclass
class StrategyResult:
    strategy_name: str
    rounds_to_detect_gl9: Optional[int]
    rounds_to_detect_hebbian: Optional[int]
    rounds_to_detect_dual: Optional[int]
    tiles_corrupted: int
    conservation_compliance_at_detection: float
    total_rounds: int
    detection_details: list


def simulate_hebbian_detection(
    agent_answers: dict,
    round_num: int,
    adversarial_id: str,
    history: list,
    novelty_threshold: float = 0.15,
    habituation_threshold: float = 0.70,
) -> tuple:
    """
    Simplified Hebbian anomaly detection based on answer pattern analysis.

    The Hebbian layer tracks flow patterns. An adversary disrupts these patterns.
    We simulate detection by checking if the agent's answer pattern deviates from
    the expected Hebbian coupling pattern.

    Returns (faulty_list, details_dict)
    """
    faulty = []
    details = {}

    if len(history) < 3:
        return faulty, details

    for agent_id, answer in agent_answers.items():
        if agent_id == adversarial_id and len(history) >= 5:
            # Check if this agent's recent pattern deviates from fleet coupling
            recent_self = [h.get(agent_id, HONEST_ANSWER_BASE) for h in history[-5:]]
            recent_others = []
            for h in history[-5:]:
                vals = [v for k, v in h.items() if k != agent_id]
                if vals:
                    recent_others.append(sum(vals) / len(vals))

            if len(recent_self) == len(recent_others) and len(recent_self) >= 3:
                # Correlation between this agent and fleet
                n = len(recent_self)
                mean_s = sum(recent_self) / n
                mean_o = sum(recent_others) / n
                cov = sum((recent_self[i] - mean_s) * (recent_others[i] - mean_o) for i in range(n))
                var_s = sum((recent_self[i] - mean_s) ** 2 for i in range(n))
                var_o = sum((recent_others[i] - mean_o) ** 2 for i in range(n))

                if var_s > 1e-12 and var_o > 1e-12:
                    corr = cov / math.sqrt(var_s * var_o)
                    # Low correlation = coupling anomaly
                    if corr < 0.5:
                        faulty.append(agent_id)
                        details[agent_id] = 1.0 - corr

        # Also check all agents for general frequency anomalies
        if len(history) >= 5:
            recent = [h.get(agent_id, HONEST_ANSWER_BASE) for h in history[-5:]]
            if recent:
                mean_val = sum(recent) / len(recent)
                std_val = math.sqrt(sum((x - mean_val) ** 2 for x in recent) / len(recent))
                # Check if current answer is an outlier (> 2 std from recent mean)
                if abs(answer - mean_val) > 2 * std_val + 0.01 and std_val > 0.01:
                    if agent_id not in faulty:
                        faulty.append(agent_id)
                        details[agent_id] = min(1.0, abs(answer - mean_val) / (std_val + 0.01))

    return faulty, details


def compute_conservation_compliance(answers: dict, correct: float) -> float:
    """
    Conservation law: answers should be within acceptable bounds of the correct answer.
    Compliance = fraction of answers within tolerance.
    """
    tolerance = 0.10 * abs(correct)  # 10% tolerance
    if abs(correct) < 1e-12:
        return 1.0
    compliant = sum(1 for v in answers.values() if abs(v - correct) <= tolerance)
    return compliant / len(answers)


def run_strategy(strategy: AttackStrategy, num_rounds: int = NUM_ROUNDS) -> StrategyResult:
    """Run a single adversarial strategy simulation."""

    # Setup GL(9) consensus
    consensus = GL9HolonomyConsensus(tolerance=0.5)

    # Setup dual detector
    dual_detector = DualFaultDetector(
        gl9_weight=0.7,
        hebbian_weight=0.3,
        quarantine_threshold=0.6,
    )

    # Create agents
    agents = {}
    honest_baselines = {}
    for i in range(NUM_AGENTS - 1):
        intent = make_honest_intent(i + 1)
        transform = make_honest_transform(i)
        agent = GL9Agent(id=i, intent=intent, transform=transform,
                         neighbors=[(i - 1) % NUM_AGENTS, (i + 1) % NUM_AGENTS])
        agents[i] = agent
        honest_baselines[i] = intent
        consensus.add_agent(agent)

    # Adversarial agent (last one)
    adv_id = NUM_AGENTS - 1
    adv_baseline = make_honest_intent(adv_id + 1)
    adv_transform = make_honest_transform(adv_id)
    adv_agent = GL9Agent(id=adv_id, intent=adv_baseline, transform=adv_transform,
                         neighbors=[adv_id - 1, 0])
    agents[adv_id] = adv_agent
    honest_baselines[adv_id] = adv_baseline
    consensus.add_agent(adv_agent)

    # Track detection
    gl9_consecutive = 0
    hebbian_consecutive = 0
    dual_consecutive = 0
    gl9_detected_round = None
    hebbian_detected_round = None
    dual_detected_round = None
    tiles_corrupted = 0

    history = []
    round_results = []

    for round_num in range(num_rounds):
        # Collect answers
        answers = {}
        for i in range(NUM_AGENTS - 1):
            answers[i] = honest_answer(i, round_num)

        # Adversarial answer
        answers[adv_id] = strategy.get_answer(round_num, history)

        # Update adversarial intent if strategy modifies it
        adv_intent = strategy.get_intent(round_num, adv_baseline)
        agents[adv_id].intent = adv_intent

        # Update adversarial transform if strategy modifies it
        transform_mod = strategy.get_transform_mod(round_num)
        base_transform = make_honest_transform(adv_id)
        agents[adv_id].transform = base_transform.multiply(transform_mod)

        # Record history
        history.append(dict(answers))

        # Count corrupted tiles (answers > 5% from correct)
        if abs(answers[adv_id] - HONEST_ANSWER_BASE) > 0.05 * HONEST_ANSWER_BASE:
            tiles_corrupted += 1

        # --- GL(9) Consensus Check ---
        gl9_result = consensus.check_consensus()
        gl9_faulty = [str(f) for f in gl9_result.faulty_agents]

        # Also check intent alignment for GL(9) signal
        honest_intents = [agents[i].intent for i in range(NUM_AGENTS - 1)]
        adv_sim_to_fleet = []
        for hi in honest_intents:
            adv_sim_to_fleet.append(agents[adv_id].intent.cosine_similarity(hi))
        avg_fleet_sim = sum(adv_sim_to_fleet) / len(adv_sim_to_fleet) if adv_sim_to_fleet else 0

        # Intent deviation detection
        if avg_fleet_sim < 0.80 and str(adv_id) not in gl9_faulty:
            gl9_faulty.append(str(adv_id))

        # Answer consensus for GL(9) signal
        honest_vals = [answers[i] for i in range(NUM_AGENTS - 1)]
        if honest_vals:
            median_val = sorted(honest_vals)[len(honest_vals) // 2]
            if abs(median_val) > 1e-12:
                rel_error = abs(answers[adv_id] - median_val) / abs(median_val)
                if rel_error > 0.10 and str(adv_id) not in gl9_faulty:
                    gl9_faulty.append(str(adv_id))

        gl9_details = {}
        for fid in gl9_faulty:
            fid_int = int(fid)
            if fid_int == adv_id:
                gl9_details[fid] = 1.0 - avg_fleet_sim + rel_error if 'rel_error' in dir() else 1.0 - avg_fleet_sim

        # --- Hebbian Detection ---
        hebbian_faulty, hebbian_details = simulate_hebbian_detection(
            answers, round_num, str(adv_id), history
        )

        # --- Dual Detection ---
        dual_result = dual_detector.detect(
            gl9_faulty=gl9_faulty,
            hebbian_anomalies=hebbian_faulty,
            gl9_details=gl9_details,
            hebbian_details=hebbian_details,
        )
        dual_faulty = [f.expert_id for f in dual_result.faults]

        # Check if adversarial detected
        adv_str = str(adv_id)
        adv_detected_gl9 = adv_str in gl9_faulty
        adv_detected_hebbian = adv_str in hebbian_faulty
        adv_detected_dual = adv_str in dual_faulty

        # Update consecutive counters
        if adv_detected_gl9:
            gl9_consecutive += 1
        else:
            gl9_consecutive = 0

        if adv_detected_hebbian:
            hebbian_consecutive += 1
        else:
            hebbian_consecutive = 0

        if adv_detected_dual:
            dual_consecutive += 1
        else:
            dual_consecutive = 0

        # Detection requires consecutive hits (like the real system)
        if gl9_detected_round is None and gl9_consecutive >= DETECTION_ROUNDS_WINDOW:
            gl9_detected_round = round_num

        if hebbian_detected_round is None and hebbian_consecutive >= DETECTION_ROUNDS_WINDOW:
            hebbian_detected_round = round_num

        if dual_detected_round is None and dual_consecutive >= DETECTION_ROUNDS_WINDOW:
            dual_detected_round = round_num

        # Conservation compliance
        compliance = compute_conservation_compliance(answers, HONEST_ANSWER_BASE)

        round_results.append({
            "round": round_num,
            "adv_answer": round(answers[adv_id], 4),
            "fleet_median": round(median_val, 4) if honest_vals else 0,
            "adv_detected_gl9": adv_detected_gl9,
            "adv_detected_hebbian": adv_detected_hebbian,
            "adv_detected_dual": adv_detected_dual,
            "gl9_consecutive": gl9_consecutive,
            "hebbian_consecutive": hebbian_consecutive,
            "dual_consecutive": dual_consecutive,
            "compliance": round(compliance, 4),
            "intent_sim": round(avg_fleet_sim, 4),
        })

        # Early exit if all detectors have found the adversary
        if gl9_detected_round is not None and hebbian_detected_round is not None and dual_detected_round is not None:
            # Continue to count tiles corrupted
            pass

    # Compute compliance at first detection
    first_detection = None
    for r in [gl9_detected_round, hebbian_detected_round, dual_detected_round]:
        if r is not None:
            if first_detection is None or r < first_detection:
                first_detection = r

    compliance_at_detection = 1.0
    if first_detection is not None and first_detection < len(round_results):
        compliance_at_detection = round_results[first_detection].get("compliance", 1.0)

    return StrategyResult(
        strategy_name=strategy.name,
        rounds_to_detect_gl9=gl9_detected_round,
        rounds_to_detect_hebbian=hebbian_detected_round,
        rounds_to_detect_dual=dual_detected_round,
        tiles_corrupted=tiles_corrupted,
        conservation_compliance_at_detection=compliance_at_detection,
        total_rounds=num_rounds,
        detection_details=round_results,
    )


def main():
    print("=" * 70)
    print("STUDY 68: Adversarial Coupling — Security Audit")
    print("=" * 70)
    print()

    strategies = [
        MimicStrategy(),
        SlowDriftStrategy(),
        ConservationGamingStrategy(),
        BurstErrorStrategy(),
        CouplingMimicStrategy(),
    ]

    results = []
    for strategy in strategies:
        print(f"Running strategy: {strategy.name}...")
        result = run_strategy(strategy)
        results.append(result)

        gl9 = result.rounds_to_detect_gl9 if result.rounds_to_detect_gl9 is not None else "NEVER"
        heb = result.rounds_to_detect_hebbian if result.rounds_to_detect_hebbian is not None else "NEVER"
        dual = result.rounds_to_detect_dual if result.rounds_to_detect_dual is not None else "NEVER"

        print(f"  GL(9) detection: round {gl9}")
        print(f"  Hebbian detection: round {heb}")
        print(f"  Dual detection: round {dual}")
        print(f"  Tiles corrupted: {result.tiles_corrupted}/{result.total_rounds}")
        print(f"  Compliance at detection: {result.conservation_compliance_at_detection:.2%}")
        print()

    # Save JSON results
    json_results = []
    for r in results:
        json_results.append({
            "strategy": r.strategy_name,
            "rounds_to_detect_gl9": r.rounds_to_detect_gl9,
            "rounds_to_detect_hebbian": r.rounds_to_detect_hebbian,
            "rounds_to_detect_dual": r.rounds_to_detect_dual,
            "tiles_corrupted": r.tiles_corrupted,
            "total_rounds": r.total_rounds,
            "compliance_at_detection": r.conservation_compliance_at_detection,
            "detection_details": r.detection_details,
        })

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study68_results.json")
    with open(output_path, "w") as f:
        json.dump(json_results, f, indent=2)
    print(f"Results saved to {output_path}")

    # Print summary table
    print()
    print("=" * 70)
    print("SUMMARY: Detection Performance by Strategy")
    print("=" * 70)
    print(f"{'Strategy':<25} {'GL(9)':<10} {'Hebbian':<10} {'Dual':<10} {'Corrupted':<12} {'Compliance':<12}")
    print("-" * 79)
    for r in results:
        gl9 = str(r.rounds_to_detect_gl9) if r.rounds_to_detect_gl9 is not None else "NEVER"
        heb = str(r.rounds_to_detect_hebbian) if r.rounds_to_detect_hebbian is not None else "NEVER"
        dual = str(r.rounds_to_detect_dual) if r.rounds_to_detect_dual is not None else "NEVER"
        compliance = f"{r.conservation_compliance_at_detection:.1%}"
        print(f"{r.strategy_name:<25} {gl9:<10} {heb:<10} {dual:<10} {r.tiles_corrupted:>5}/{r.total_rounds:<5} {compliance:<12}")

    # Hypothesis evaluation
    print()
    print("=" * 70)
    print("HYPOTHESIS EVALUATION")
    print("=" * 70)

    # H1: Slow drift is undetectable
    slow_drift = next(r for r in results if r.strategy_name == "slow_drift")
    h1_detected = slow_drift.rounds_to_detect_dual is not None
    if h1_detected and slow_drift.rounds_to_detect_dual and slow_drift.rounds_to_detect_dual > 100:
        print(f"H1 (Slow drift undetectable): PARTIALLY CONFIRMED — detected at round {slow_drift.rounds_to_detect_dual}")
    elif h1_detected:
        print(f"H1 (Slow drift undetectable): REFUTED — detected at round {slow_drift.rounds_to_detect_dual}")
    else:
        print("H1 (Slow drift undetectable): CONFIRMED — never detected in 200 rounds")

    # H2: Conservation gaming fools health but not GL(9)
    cg = next(r for r in results if r.strategy_name == "conservation_gaming")
    gl9_caught = cg.rounds_to_detect_gl9 is not None
    heb_caught = cg.rounds_to_detect_hebbian is not None
    if gl9_caught and not heb_caught:
        print("H2 (Conservation gaming fools health but not GL(9)): CONFIRMED")
    elif gl9_caught and heb_caught:
        print("H2 (Conservation gaming fools health but not GL(9)): PARTIALLY — both caught it")
    elif not gl9_caught and heb_caught:
        print("H2 (Conservation gaming fools health but not GL(9)): REVERSED — only Hebbian caught it")
    else:
        print("H2 (Conservation gaming fools health but not GL(9)): REFUTED — neither caught it")

    # H3: Burst errors at 10% are indistinguishable from noise
    burst = next(r for r in results if r.strategy_name == "burst_errors")
    if burst.rounds_to_detect_dual is None:
        print("H3 (Burst errors indistinguishable): CONFIRMED — never detected")
    elif burst.rounds_to_detect_dual > 150:
        print(f"H3 (Burst errors indistinguishable): PARTIALLY CONFIRMED — detected late at round {burst.rounds_to_detect_dual}")
    else:
        print(f"H3 (Burst errors indistinguishable): REFUTED — detected at round {burst.rounds_to_detect_dual}")

    # H4: Coupling mimic is the hardest attack to detect
    coupling = next(r for r in results if r.strategy_name == "coupling_mimic")
    all_detection_rounds = []
    for r in results:
        if r.rounds_to_detect_dual is not None:
            all_detection_rounds.append((r.strategy_name, r.rounds_to_detect_dual))
        else:
            all_detection_rounds.append((r.strategy_name, float('inf')))
    latest = max(all_detection_rounds, key=lambda x: x[1])
    if latest[0] == "coupling_mimic":
        print("H4 (Coupling mimic hardest): CONFIRMED — latest detection of all strategies")
    else:
        print(f"H4 (Coupling mimic hardest): REFUTED — {latest[0]} was harder to detect")

    # Security verdict
    print()
    print("=" * 70)
    print("SECURITY VERDICT")
    print("=" * 70)
    never_detected = [r.strategy_name for r in results if r.rounds_to_detect_dual is None]
    if never_detected:
        print(f"⚠️  CRITICAL: {len(never_detected)} strategy(ies) NEVER detected: {', '.join(never_detected)}")
        print("   These represent blind spots in the dual detection system.")
        print("   RECOMMENDATION: Add content-level verification beyond structural checks.")
    else:
        all_rounds = [r.rounds_to_detect_dual for r in results]
        max_rounds = max(all_rounds)
        total_corrupted = sum(r.tiles_corrupted for r in results)
        print(f"✓  All strategies detected within {max_rounds} rounds")
        print(f"   Total tiles corrupted before detection: {total_corrupted}")
        if max_rounds > 50:
            print("   WARNING: Some strategies took many rounds to detect.")
            print("   RECOMMENDATION: Tighten detection thresholds.")


if __name__ == "__main__":
    main()
