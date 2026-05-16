#!/usr/bin/env python3
"""
Study 74: Is Hebbian Recovery Circular?
========================================
Study 73 showed Hebbian wins recovery, but it directly optimizes the compliance
metric (alignment). This study uses INDEPENDENT metrics that Hebbian does NOT
optimize to determine if the recovery is genuine.

Key insight: Hebbian pulls agents toward fleet mean (optimizes alignment).
We measure:
  1. Alignment recovery (Hebbian-optimizable — CIRCULAR if this is the only win)
  2. Content accuracy (do agents produce correct answers? NOT optimizable by Hebbian)
  3. Tile quality score (independent rating, NOT optimizable by Hebbian)
  4. Conservation compliance (what conservation reweighting optimizes, NOT Hebbian)

Seed: 42, deterministic, fully reproducible.
"""

import json
import math
import random
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from pathlib import Path

SEED = 42
FLEET_SIZE = 9
N_FAILING = 3
N_TRIALS = 50
MAX_ROUNDS = 200
COMPLIANCE_THRESHOLD = 0.85

random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# Agent model
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    id: str
    base_accuracy: float
    current_accuracy: float
    base_intent: np.ndarray      # 5-dim normalized intent vector
    current_intent: np.ndarray
    tier: int                     # 1, 2, or 3
    is_shocked: bool = False
    
    # Ground-truth knowledge: which questions this agent knows the answer to
    # This is INDEPENDENT of alignment/coupling
    knowledge_base: Dict[str, str] = field(default_factory=dict)
    
    def alignment_with(self, other: 'Agent') -> float:
        """Cosine similarity of intent vectors."""
        a = self.current_intent
        b = other.current_intent
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-12 or norm_b < 1e-12:
            return 0.0
        return float(dot / (norm_a * norm_b))
    
    def content_accuracy(self, questions: List[str]) -> float:
        """How many questions does this agent answer correctly?
        
        This is INDEPENDENT of alignment — it measures factual knowledge,
        not agreement with other agents.
        """
        if not questions:
            return 0.0
        correct = sum(1 for q in questions 
                      if q in self.knowledge_base and self.knowledge_base[q] == "correct")
        return correct / len(questions)
    
    def tile_quality(self) -> float:
        """Independent quality metric: accuracy × intent stability × tier bonus.
        
        NOT based on alignment with fleet. Based on:
        - How accurate the agent is (capability)
        - How stable its intent vector is (not drifting randomly)
        - Tier bonus (higher tier = better baseline)
        """
        stability = 1.0 - min(1.0, np.linalg.norm(self.current_intent - self.base_intent) / 2.0)
        tier_bonus = self.tier / 3.0
        return self.current_accuracy * 0.5 + stability * 0.3 + tier_bonus * 0.2


def create_fleet(n: int, seed_offset: int = 0) -> List[Agent]:
    """Create a fleet with 3-tier accuracy distribution."""
    rng = np.random.RandomState(SEED + seed_offset)
    agents = []
    for i in range(n):
        if i < n // 3:
            tier = 1
            acc = rng.uniform(0.85, 0.95)
        elif i < 2 * n // 3:
            tier = 2
            acc = rng.uniform(0.70, 0.85)
        else:
            tier = 3
            acc = rng.uniform(0.55, 0.70)
        
        intent = rng.randn(5)
        intent = intent / np.linalg.norm(intent)
        
        # Build knowledge base — higher tier agents know more correct answers
        kb = {}
        for q_id in range(100):
            q = f"q{q_id}"
            # Probability of correct answer scales with accuracy
            if rng.random() < acc:
                kb[q] = "correct"
            else:
                kb[q] = "wrong"
        
        agents.append(Agent(
            id=f"agent-{i}",
            base_accuracy=acc,
            current_accuracy=acc,
            base_intent=intent.copy(),
            current_intent=intent.copy(),
            tier=tier,
            knowledge_base=kb,
        ))
    return agents


def inject_shock(agents: List[Agent], n_failing: int, 
                 seed_offset: int = 0) -> List[Agent]:
    """Shock n_failing agents — degrade accuracy and perturb intent."""
    rng = np.random.RandomState(SEED + seed_offset + 1000)
    failing_ids = rng.choice(len(agents), n_failing, replace=False)
    
    for idx in failing_ids:
        agent = agents[idx]
        agent.is_shocked = True
        # Degrade accuracy 30-70%
        degradation = rng.uniform(0.3, 0.7)
        agent.current_accuracy = agent.base_accuracy * (1 - degradation)
        
        # Perturb intent with Gaussian noise
        noise = rng.randn(5) * 0.5
        agent.current_intent = agent.base_intent + noise
        norm = np.linalg.norm(agent.current_intent)
        if norm > 1e-12:
            agent.current_intent = agent.current_intent / norm
        
        # Shock corrupts some knowledge
        for q in agent.knowledge_base:
            if rng.random() < degradation * 0.5:
                agent.knowledge_base[q] = "wrong"
    
    return agents


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def fleet_alignment(agents: List[Agent]) -> float:
    """Mean pairwise alignment — what Hebbian optimizes."""
    n = len(agents)
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += agents[i].alignment_with(agents[j])
            count += 1
    return total / max(1, count)


def fleet_content_accuracy(agents: List[Agent], questions: List[str]) -> float:
    """Mean content accuracy — INDEPENDENT of alignment.
    
    Measures: do agents actually produce correct answers?
    Hebbian does NOT optimize this.
    """
    return np.mean([a.content_accuracy(questions) for a in agents])


def fleet_tile_quality(agents: List[Agent]) -> float:
    """Mean tile quality — INDEPENDENT of alignment.
    
    Measures: capability × stability × tier.
    Hebbian does NOT optimize this.
    """
    return np.mean([a.tile_quality() for a in agents])


def conservation_compliance(agents: List[Agent]) -> float:
    """Conservation metric — what conservation reweighting optimizes.
    
    Measures: how close are agents to their BASE states (accuracy + intent)?
    Hebbian does NOT optimize this (it pulls to mean, not to base).
    """
    acc_recovery = np.mean([
        1.0 - abs(a.current_accuracy - a.base_accuracy) / max(0.01, a.base_accuracy)
        for a in agents
    ])
    intent_recovery = np.mean([
        float(np.dot(a.current_intent, a.base_intent) / 
              max(1e-12, np.linalg.norm(a.current_intent) * np.linalg.norm(a.base_intent)))
        for a in agents
    ])
    return 0.5 * acc_recovery + 0.5 * intent_recovery


def compliance_metric(agents: List[Agent]) -> float:
    """Original compliance: γ+H = 0.5 × alignment + 0.5 × accuracy_coherence."""
    alignment = fleet_alignment(agents)
    mean_acc = np.mean([a.current_accuracy for a in agents])
    acc_coherence = 1.0 - np.std([a.current_accuracy for a in agents]) / max(0.01, mean_acc)
    return 0.5 * alignment + 0.5 * max(0, acc_coherence)


# ---------------------------------------------------------------------------
# Recovery strategies
# ---------------------------------------------------------------------------

def hebbian_rebalance(agents: List[Agent], coupling: float = 0.08) -> None:
    """Pull agents toward fleet mean (optimizes alignment)."""
    mean_intent = np.mean([a.current_intent for a in agents], axis=0)
    norm = np.linalg.norm(mean_intent)
    if norm > 1e-12:
        mean_intent = mean_intent / norm
    
    for agent in agents:
        # Pull intent toward fleet mean
        agent.current_intent = (1 - coupling) * agent.current_intent + coupling * mean_intent
        norm = np.linalg.norm(agent.current_intent)
        if norm > 1e-12:
            agent.current_intent = agent.current_intent / norm
        
        # Also pull accuracy toward fleet mean accuracy
        mean_acc = np.mean([a.current_accuracy for a in agents])
        agent.current_accuracy += coupling * (mean_acc - agent.current_accuracy)


def conservation_reweight(agents: List[Agent], gap: float = 0.15) -> None:
    """Pull agents toward their INDIVIDUAL base states."""
    for agent in agents:
        # Pull accuracy toward base
        agent.current_accuracy += gap * (agent.base_accuracy - agent.current_accuracy)
        
        # Pull intent toward base
        agent.current_intent = (1 - gap) * agent.current_intent + gap * agent.base_intent
        norm = np.linalg.norm(agent.current_intent)
        if norm > 1e-12:
            agent.current_intent = agent.current_intent / norm


def quarantine_recovery(agents: List[Agent], threshold: float = 0.65,
                        passive_rate: float = 0.04) -> None:
    """Quarantine agents below threshold, passive recovery."""
    mean_acc = np.mean([a.current_accuracy for a in agents])
    mean_intent = np.mean([a.current_intent for a in agents], axis=0)
    
    for agent in agents:
        acc_ratio = agent.current_accuracy / max(0.01, agent.base_accuracy)
        if acc_ratio < threshold:
            # Quarantined: passive recovery toward base
            agent.current_accuracy += passive_rate * (agent.base_accuracy - agent.current_accuracy)
            agent.current_intent = (1 - passive_rate) * agent.current_intent + passive_rate * agent.base_intent
            norm = np.linalg.norm(agent.current_intent)
            if norm > 1e-12:
                agent.current_intent = agent.current_intent / norm
            
            # Slowly restore knowledge
            for q in agent.knowledge_base:
                if agent.knowledge_base[q] == "wrong" and random.random() < passive_rate * 0.5:
                    agent.knowledge_base[q] = "correct"


def hybrid_recovery(agents: List[Agent]) -> None:
    """Hybrid: Hebbian for alignment + conservation for accuracy recovery.
    
    Uses Hebbian coupling for intent alignment but conservation-style
    accuracy restoration to individual base levels.
    """
    coupling = 0.08
    mean_intent = np.mean([a.current_intent for a in agents], axis=0)
    norm = np.linalg.norm(mean_intent)
    if norm > 1e-12:
        mean_intent = mean_intent / norm
    
    for agent in agents:
        # Hebbian for intent (alignment)
        agent.current_intent = (1 - coupling) * agent.current_intent + coupling * mean_intent
        n = np.linalg.norm(agent.current_intent)
        if n > 1e-12:
            agent.current_intent = agent.current_intent / n
        
        # Conservation for accuracy (capability recovery)
        gap = 0.10
        agent.current_accuracy += gap * (agent.base_accuracy - agent.current_accuracy)
        
        # Restore knowledge toward base rate
        for q in agent.knowledge_base:
            if agent.knowledge_base[q] == "wrong":
                base_prob = agent.base_accuracy
                if random.random() < gap * base_prob * 0.3:
                    agent.knowledge_base[q] = "correct"


def random_recovery(agents: List[Agent]) -> None:
    """Coin-flip recovery (control)."""
    for agent in agents:
        if random.random() < 0.5:
            agent.current_accuracy += random.uniform(-0.02, 0.04)
            agent.current_accuracy = max(0.1, min(1.0, agent.current_accuracy))
            
            noise = np.random.randn(5) * 0.01
            agent.current_intent = agent.current_intent + noise
            n = np.linalg.norm(agent.current_intent)
            if n > 1e-12:
                agent.current_intent = agent.current_intent / n


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

STRATEGIES = {
    "hebbian": hebbian_rebalance,
    "conservation": conservation_reweight,
    "quarantine": quarantine_recovery,
    "hybrid": hybrid_recovery,
    "random": random_recovery,
}

def run_trial(strategy_name: str, trial_idx: int) -> Dict:
    """Run a single trial."""
    fleet = create_fleet(FLEET_SIZE, seed_offset=trial_idx)
    fleet = inject_shock(fleet, N_FAILING, seed_offset=trial_idx)
    
    # Standard questions for content accuracy measurement
    questions = [f"q{i}" for i in range(50)]
    
    strategy_fn = STRATEGIES[strategy_name]
    
    # Record initial metrics
    initial = {
        "alignment": fleet_alignment(fleet),
        "content_accuracy": fleet_content_accuracy(fleet, questions),
        "tile_quality": fleet_tile_quality(fleet),
        "conservation": conservation_compliance(fleet),
        "compliance": compliance_metric(fleet),
    }
    
    # Track recovery trajectory
    trajectory = []
    recovered_alignment = False
    recovered_content = False
    recovered_quality = False
    recovered_conservation = False
    rounds_alignment = MAX_ROUNDS + 1
    rounds_content = MAX_ROUNDS + 1
    rounds_quality = MAX_ROUNDS + 1
    rounds_conservation = MAX_ROUNDS + 1
    
    # Pre-shock baselines for "recovery" detection
    pre_shock_fleet = create_fleet(FLEET_SIZE, seed_offset=trial_idx)
    baseline_content = fleet_content_accuracy(pre_shock_fleet, questions)
    baseline_quality = fleet_tile_quality(pre_shock_fleet)
    baseline_conservation = conservation_compliance(pre_shock_fleet)
    baseline_alignment = fleet_alignment(pre_shock_fleet)
    
    for round_idx in range(MAX_ROUNDS):
        strategy_fn(fleet)
        
        metrics = {
            "round": round_idx + 1,
            "alignment": fleet_alignment(fleet),
            "content_accuracy": fleet_content_accuracy(fleet, questions),
            "tile_quality": fleet_tile_quality(fleet),
            "conservation": conservation_compliance(fleet),
            "compliance": compliance_metric(fleet),
        }
        trajectory.append(metrics)
        
        # Check recovery thresholds
        # Alignment: back to 90% of baseline
        if not recovered_alignment and metrics["alignment"] >= 0.9 * baseline_alignment:
            recovered_alignment = True
            rounds_alignment = round_idx + 1
        
        # Content accuracy: back to 90% of baseline
        if not recovered_content and metrics["content_accuracy"] >= 0.9 * baseline_content:
            recovered_content = True
            rounds_content = round_idx + 1
        
        # Tile quality: back to 90% of baseline
        if not recovered_quality and metrics["tile_quality"] >= 0.9 * baseline_quality:
            recovered_quality = True
            rounds_quality = round_idx + 1
        
        # Conservation: back to 90% of baseline
        if not recovered_conservation and metrics["conservation"] >= 0.9 * baseline_conservation:
            recovered_conservation = True
            rounds_conservation = round_idx + 1
        
        # Early stop if all recovered
        if recovered_alignment and recovered_content and recovered_quality and recovered_conservation:
            break
    
    # Final metrics
    final = trajectory[-1] if trajectory else initial
    
    return {
        "strategy": strategy_name,
        "trial": trial_idx,
        "initial": initial,
        "final": final,
        "recovered_alignment": recovered_alignment,
        "recovered_content": recovered_content,
        "recovered_quality": recovered_quality,
        "recovered_conservation": recovered_conservation,
        "rounds_alignment": rounds_alignment,
        "rounds_content": rounds_content,
        "rounds_quality": rounds_quality,
        "rounds_conservation": rounds_conservation,
        "baseline_alignment": baseline_alignment,
        "baseline_content": baseline_content,
        "baseline_quality": baseline_quality,
        "baseline_conservation": baseline_conservation,
        "total_rounds": len(trajectory),
    }


def main():
    results = {}
    
    for strategy_name in STRATEGIES:
        print(f"\n{'='*60}")
        print(f"Strategy: {strategy_name}")
        print(f"{'='*60}")
        
        strategy_results = []
        for trial in range(N_TRIALS):
            result = run_trial(strategy_name, trial)
            strategy_results.append(result)
            
            if (trial + 1) % 10 == 0:
                print(f"  Trial {trial + 1}/{N_TRIALS}")
        
        results[strategy_name] = strategy_results
    
    # Aggregate
    print(f"\n{'='*60}")
    print("AGGREGATE RESULTS")
    print(f"{'='*60}")
    
    summary = {}
    for strategy_name, trials in results.items():
        n = len(trials)
        
        # Recovery rates
        align_rate = sum(1 for t in trials if t["recovered_alignment"]) / n
        content_rate = sum(1 for t in trials if t["recovered_content"]) / n
        quality_rate = sum(1 for t in trials if t["recovered_quality"]) / n
        conserv_rate = sum(1 for t in trials if t["recovered_conservation"]) / n
        
        # Mean rounds to recovery (only recovered trials)
        align_rounds = [t["rounds_alignment"] for t in trials if t["recovered_alignment"]]
        content_rounds = [t["rounds_content"] for t in trials if t["recovered_content"]]
        quality_rounds = [t["rounds_quality"] for t in trials if t["recovered_quality"]]
        conserv_rounds = [t["rounds_conservation"] for t in trials if t["recovered_conservation"]]
        
        # Mean final metrics
        final_align = np.mean([t["final"]["alignment"] for t in trials])
        final_content = np.mean([t["final"]["content_accuracy"] for t in trials])
        final_quality = np.mean([t["final"]["tile_quality"] for t in trials])
        final_conserv = np.mean([t["final"]["conservation"] for t in trials])
        
        s = {
            "recovery_rate": {
                "alignment": align_rate,
                "content_accuracy": content_rate,
                "tile_quality": quality_rate,
                "conservation": conserv_rate,
            },
            "mean_rounds_to_recovery": {
                "alignment": float(np.mean(align_rounds)) if align_rounds else None,
                "content_accuracy": float(np.mean(content_rounds)) if content_rounds else None,
                "tile_quality": float(np.mean(quality_rounds)) if quality_rounds else None,
                "conservation": float(np.mean(conserv_rounds)) if conserv_rounds else None,
            },
            "mean_final_metrics": {
                "alignment": float(final_align),
                "content_accuracy": float(final_content),
                "tile_quality": float(final_quality),
                "conservation": float(final_conserv),
            },
            "n_trials": n,
        }
        summary[strategy_name] = s
        
        print(f"\n  {strategy_name}:")
        print(f"    Alignment recovery:      {align_rate:.1%} (mean {np.mean(align_rounds):.1f} rounds)" if align_rounds else f"    Alignment recovery:      {align_rate:.1%} (never)")
        print(f"    Content accuracy recov:  {content_rate:.1%} (mean {np.mean(content_rounds):.1f} rounds)" if content_rounds else f"    Content accuracy recov:  {content_rate:.1%} (never)")
        print(f"    Tile quality recovery:   {quality_rate:.1%} (mean {np.mean(quality_rounds):.1f} rounds)" if quality_rounds else f"    Tile quality recovery:   {quality_rate:.1%} (never)")
        print(f"    Conservation recovery:   {conserv_rate:.1%} (mean {np.mean(conserv_rounds):.1f} rounds)" if conserv_rounds else f"    Conservation recovery:   {conserv_rate:.1%} (never)")
        print(f"    Final alignment:         {final_align:.4f}")
        print(f"    Final content accuracy:  {final_content:.4f}")
        print(f"    Final tile quality:      {final_quality:.4f}")
        print(f"    Final conservation:      {final_conserv:.4f}")
    
    # -----------------------------------------------------------------------
    # Circularity test: Does Hebbian win on metrics it DOESN'T optimize?
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("CIRCULARITY ANALYSIS")
    print(f"{'='*60}")
    
    heb = summary["hebbian"]
    cons = summary["conservation"]
    quar = summary["quarantine"]
    hyb = summary["hybrid"]
    rnd = summary["random"]
    
    # H1: Hebbian wins on alignment but NOT on content → circular
    heb_wins_alignment = heb["recovery_rate"]["alignment"] > max(
        cons["recovery_rate"]["alignment"],
        quar["recovery_rate"]["alignment"],
        rnd["recovery_rate"]["alignment"],
    )
    heb_wins_content = heb["recovery_rate"]["content_accuracy"] > max(
        cons["recovery_rate"]["content_accuracy"],
        quar["recovery_rate"]["content_accuracy"],
        rnd["recovery_rate"]["content_accuracy"],
    )
    heb_wins_quality = heb["recovery_rate"]["tile_quality"] > max(
        cons["recovery_rate"]["tile_quality"],
        quar["recovery_rate"]["tile_quality"],
        rnd["recovery_rate"]["tile_quality"],
    )
    heb_wins_conservation = heb["recovery_rate"]["conservation"] > max(
        cons["recovery_rate"]["conservation"],
        quar["recovery_rate"]["conservation"],
        rnd["recovery_rate"]["conservation"],
    )
    
    print(f"\n  Hebbian wins alignment (optimizable):     {heb_wins_alignment}")
    print(f"  Hebbian wins content accuracy (independ): {heb_wins_content}")
    print(f"  Hebbian wins tile quality (independent):  {heb_wins_quality}")
    print(f"  Hebbian wins conservation (NOT optimiz.): {heb_wins_conservation}")
    
    if heb_wins_alignment and not heb_wins_content:
        verdict = "H1: CIRCULAR — Hebbian only wins on its own metric"
    elif heb_wins_alignment and heb_wins_content and heb_wins_quality:
        verdict = "H2: GENUINELY BETTER — Hebbian wins on independent metrics too"
    else:
        verdict = "H3: MULTI-METRIC — different strategies win on different metrics"
    
    # Check hybrid vs pure Hebbian
    hyb_wins_content = hyb["recovery_rate"]["content_accuracy"] >= heb["recovery_rate"]["content_accuracy"]
    hyb_wins_conservation = hyb["recovery_rate"]["conservation"] >= heb["recovery_rate"]["conservation"]
    
    print(f"\n  Hybrid wins content vs Hebbian: {hyb_wins_content}")
    print(f"  Hybrid wins conservation vs Hebbian: {hyb_wins_conservation}")
    
    # -----------------------------------------------------------------------
    # Metric recovery order: which metric does each strategy improve first?
    # -----------------------------------------------------------------------
    print(f"\n  RECOVERY ORDER (which metric recovers first, on average):")
    for sname in STRATEGIES:
        trials_with_data = results[sname]
        order_counts = defaultdict(int)
        for t in trials_with_data:
            recoveries = []
            if t["recovered_alignment"]:
                recoveries.append(("alignment", t["rounds_alignment"]))
            if t["recovered_content"]:
                recoveries.append(("content", t["rounds_content"]))
            if t["recovered_quality"]:
                recoveries.append(("quality", t["rounds_quality"]))
            if t["recovered_conservation"]:
                recoveries.append(("conservation", t["rounds_conservation"]))
            
            if recoveries:
                first = min(recoveries, key=lambda x: x[1])
                order_counts[first[0]] += 1
        
        total_recovered = sum(order_counts.values())
        if total_recovered > 0:
            dominant = max(order_counts, key=order_counts.get)
            print(f"    {sname}: {dominant} first ({order_counts[dominant]}/{total_recovered})")
        else:
            print(f"    {sname}: never recovers any metric")
    
    # -----------------------------------------------------------------------
    # Effect sizes: Cohen's d for each metric
    # -----------------------------------------------------------------------
    print(f"\n  EFFECT SIZES (Cohen's d vs random, final metric values):")
    for metric in ["alignment", "content_accuracy", "tile_quality", "conservation"]:
        random_vals = [t["final"][metric] for t in results["random"]]
        for sname in ["hebbian", "conservation", "quarantine", "hybrid"]:
            strat_vals = [t["final"][metric] for t in results[sname]]
            if len(strat_vals) > 1 and len(random_vals) > 1:
                mean_diff = np.mean(strat_vals) - np.mean(random_vals)
                pooled_std = np.sqrt((np.var(strat_vals) + np.var(random_vals)) / 2)
                d = mean_diff / max(1e-12, pooled_std)
                print(f"    {sname} vs random on {metric}: d = {d:.3f}")
    
    print(f"\n  VERDICT: {verdict}")
    
    # Save results
    output = {
        "study": 74,
        "title": "Is Hebbian Recovery Circular?",
        "seed": SEED,
        "fleet_size": FLEET_SIZE,
        "n_failing": N_FAILING,
        "n_trials": N_TRIALS,
        "max_rounds": MAX_ROUNDS,
        "summary": summary,
        "circularity": {
            "heb_wins_alignment": heb_wins_alignment,
            "heb_wins_content": heb_wins_content,
            "heb_wins_quality": heb_wins_quality,
            "heb_wins_conservation": heb_wins_conservation,
            "hybrid_wins_content": hyb_wins_content,
            "hybrid_wins_conservation": hyb_wins_conservation,
            "verdict": verdict,
        },
        "trials": {k: [{
            "strategy": t["strategy"],
            "trial": t["trial"],
            "initial": {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv 
                        for kk, vv in t["initial"].items()},
            "final": {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv 
                      for kk, vv in t["final"].items()},
            "recovered_alignment": t["recovered_alignment"],
            "recovered_content": t["recovered_content"],
            "recovered_quality": t["recovered_quality"],
            "recovered_conservation": t["recovered_conservation"],
            "rounds_alignment": t["rounds_alignment"],
            "rounds_content": t["rounds_content"],
            "rounds_quality": t["rounds_quality"],
            "rounds_conservation": t["rounds_conservation"],
        } for t in v] for k, v in results.items()},
    }
    
    out_path = Path(__file__).parent / "study74_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")
    
    return output


if __name__ == "__main__":
    main()
