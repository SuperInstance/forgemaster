#!/usr/bin/env python3
"""Study 64 v2: Shell Shock Recovery Dynamics Simulation.

Revised model: compliance = conservation compliance rate (from fleet health),
not per-expert accuracy threshold. The fleet starts at ~89% compliance (γ+H
conserved), and shell shock occurs when conservation compliance drops below 85%.

Key insight from source code:
- fleet_unified_health.py: compliance_rate from Hebbian kernel, tracks γ+H
- dual_fault_detector.py: quarantine needs BOTH signals in low-conservation mode
- fleet_router_api.py: conservation filter blocks non-Tier-1 when compliance < 85%
"""

import json
import time
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

random.seed(42)


# ---------------------------------------------------------------------------
# Conservation Model
# ---------------------------------------------------------------------------

def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


@dataclass
class Expert:
    expert_id: str
    tier: int
    base_accuracy: float
    current_accuracy: float = 0.0
    intent_vector: List[float] = field(default_factory=lambda: [0.0] * 9)
    baseline_intent: List[float] = field(default_factory=lambda: [0.0] * 9)
    weight: float = 1.0
    quarantined: bool = False
    active: bool = True
    consecutive_faults: int = 0
    consecutive_clean: int = 0

    def __post_init__(self):
        self.current_accuracy = self.base_accuracy
        self.intent_vector = [random.gauss(0.5, 0.15) for _ in range(9)]
        self.baseline_intent = self.intent_vector[:]


class Fleet:
    """Simulated 9-expert fleet with conservation dynamics."""

    def __init__(self):
        self.experts = [
            Expert("Seed-2.0-mini",  tier=1, base_accuracy=0.97),
            Expert("Seed-2.0-code",  tier=1, base_accuracy=0.95),
            Expert("gemma3:1b",      tier=1, base_accuracy=0.94),
            Expert("Qwen3-235B",     tier=2, base_accuracy=0.78),
            Expert("Hermes-70B",     tier=2, base_accuracy=0.75),
            Expert("phi4-mini",      tier=2, base_accuracy=0.72),
            Expert("llama3.2:1b",    tier=2, base_accuracy=0.68),
            Expert("Qwen3.6-35B",    tier=3, base_accuracy=0.25),
            Expert("qwen3:4b",       tier=3, base_accuracy=0.20),
        ]
        # Conservation baseline (γ+H)
        self.gamma = 0.0
        self.H = 0.0
        self.gamma_plus_H = 0.0
        self.predicted_gamma_H = 0.0  # what γ+H should be (baseline)
        self._compute_conservation()
        self.predicted_gamma_H = self.gamma_plus_H  # lock baseline

    def _compute_conservation(self):
        """Compute γ (fleet alignment) and H (state coherence)."""
        active = [e for e in self.experts if e.active and not e.quarantined]
        if not active:
            self.gamma = 0.0
            self.H = 0.0
            self.gamma_plus_H = 0.0
            return

        # γ = mean pairwise cosine similarity of intent vectors
        sims = []
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                sims.append(cosine_sim(active[i].intent_vector, active[j].intent_vector))
        self.gamma = sum(sims) / len(sims) if sims else 0.0

        # H = weighted accuracy coherence (inverse of accuracy spread)
        accs = [e.current_accuracy for e in active]
        mean_acc = sum(accs) / len(accs)
        var = sum((a - mean_acc) ** 2 for a in accs) / len(accs)
        # Normalize: max variance ~0.25 (acc in [0,1]), so H = 1 - var/0.25
        self.H = max(0.0, 1.0 - var / 0.25)

        self.gamma_plus_H = self.gamma + self.H

    def conservation_compliance(self) -> float:
        """Fraction of recent conservation checks where γ+H was conserved.
        In simulation, this = how close γ+H is to predicted.
        Returns 1.0 when perfectly conserved, lower when violated.
        """
        if self.predicted_gamma_H < 1e-6:
            return 1.0
        deviation = abs(self.gamma_plus_H - self.predicted_gamma_H)
        max_dev = 0.3  # typical range
        compliance = max(0.0, 1.0 - deviation / max_dev)
        return compliance

    def avg_accuracy(self) -> float:
        active = [e for e in self.experts if e.active and not e.quarantined]
        if not active:
            return 0.0
        return sum(e.current_accuracy for e in active) / len(active)

    def active_count(self) -> int:
        return sum(1 for e in self.experts if e.active and not e.quarantined)

    def quarantined_count(self) -> int:
        return sum(1 for e in self.experts if e.quarantined)

    def update(self):
        self._compute_conservation()


# ---------------------------------------------------------------------------
# Shell Shock Scenarios
# ---------------------------------------------------------------------------

def inject_single_drift(fleet: Fleet):
    """One top expert's accuracy drops 50% and intent drifts."""
    e = fleet.experts[0]
    e.current_accuracy *= 0.5
    e.intent_vector = [v + random.gauss(0, 0.4) for v in e.baseline_intent]


def inject_pair_misalignment(fleet: Fleet):
    """Two top experts diverge in opposite directions."""
    e1, e2 = fleet.experts[0], fleet.experts[1]
    e1.current_accuracy *= 0.55
    e2.current_accuracy *= 0.60
    e1.intent_vector = [v + 0.5 for v in e1.baseline_intent]
    e2.intent_vector = [v - 0.5 for v in e2.baseline_intent]


def inject_cascading_failure(fleet: Fleet):
    """Expert 0 fails hard → neighbors 1-3 degrade moderately."""
    fleet.experts[0].current_accuracy *= 0.3
    fleet.experts[0].intent_vector = [v + random.gauss(0, 0.6) for v in fleet.experts[0].baseline_intent]
    for i in [1, 2, 3]:
        fleet.experts[i].current_accuracy *= 0.65
        fleet.experts[i].intent_vector = [v + random.gauss(0, 0.3) for v in fleet.experts[i].baseline_intent]


def inject_full_stress(fleet: Fleet):
    """All 9 experts degrade simultaneously."""
    for e in fleet.experts:
        e.current_accuracy *= random.uniform(0.35, 0.65)
        e.intent_vector = [v + random.gauss(0, 0.35) for v in e.baseline_intent]


SCENARIOS = {
    "single_drift": inject_single_drift,
    "pair_misalignment": inject_pair_misalignment,
    "cascading_failure": inject_cascading_failure,
    "full_fleet_stress": inject_full_stress,
}


# ---------------------------------------------------------------------------
# Recovery Strategies
# ---------------------------------------------------------------------------

def strategy_quarantine_wait(fleet: Fleet, round_num: int) -> List[str]:
    """A: Quarantine + wait (Study 63 approach).
    
    Quarantine experts with accuracy < 60% OR intent drift > 30%.
    Restore after 3 clean rounds. Slow passive recovery for quarantined experts.
    """
    actions = []
    
    # Compute fleet mean for intent checking
    active = [e for e in fleet.experts if e.active and not e.quarantined]
    if active:
        mean_intent = [sum(e.intent_vector[i] for e in active) / len(active) for i in range(9)]
    else:
        mean_intent = [0.5] * 9
    
    for e in fleet.experts:
        if e.quarantined:
            # Slow passive recovery while quarantined
            e.current_accuracy = min(e.base_accuracy, e.current_accuracy + e.base_accuracy * 0.04)
            e.consecutive_clean += 1
            e.consecutive_faults = 0
            
            if e.consecutive_clean >= 5 and e.current_accuracy >= e.base_accuracy * 0.8:
                e.quarantined = False
                e.active = True
                e.intent_vector = e.baseline_intent[:]
                e.consecutive_clean = 0
                actions.append(f"restore:{e.expert_id}")
            continue
        
        # Check for fault
        intent_sim = cosine_sim(e.intent_vector, mean_intent)
        accuracy_fault = e.current_accuracy < e.base_accuracy * 0.65
        intent_fault = intent_sim < 0.75
        
        if accuracy_fault or intent_fault:
            e.consecutive_faults += 1
            e.consecutive_clean = 0
            if e.consecutive_faults >= 2 and fleet.active_count() > 4:
                e.quarantined = True
                e.active = False
                actions.append(f"quarantine:{e.expert_id}")
        else:
            e.consecutive_faults = 0
            e.consecutive_clean += 1
        
        # Natural recovery for active experts
        diff = e.base_accuracy - e.current_accuracy
        e.current_accuracy += diff * 0.06
        e.intent_vector = [v + (bv - v) * 0.04 for v, bv in zip(e.intent_vector, e.baseline_intent)]
    
    return actions


def strategy_hebbian_rebalance(fleet: Fleet, round_num: int) -> List[str]:
    """B: Hebbian rebalancing — increase coupling to stressed agents.
    
    Never quarantine. Instead, strengthen the Hebbian kernel connection
    to struggling experts, pulling them back toward the fleet mean.
    """
    actions = []
    active = [e for e in fleet.experts if e.active]
    if not active:
        return []
    
    mean_intent = [sum(e.intent_vector[i] for e in active) / len(active) for i in range(9)]
    mean_acc = sum(e.current_accuracy for e in active) / len(active)
    
    for e in fleet.experts:
        if not e.active:
            continue
        
        stress = max(0, e.base_accuracy * 0.7 - e.current_accuracy) / (e.base_accuracy * 0.7)
        stress = min(stress, 1.0)
        coupling = 0.08 + 0.25 * stress  # Hebbian coupling strength
        
        # Pull intent toward fleet mean
        e.intent_vector = [v + (mv - v) * coupling for v, mv in zip(e.intent_vector, mean_intent)]
        
        # Pull accuracy toward fleet mean + natural recovery
        acc_pull = (mean_acc - e.current_accuracy) * coupling * 0.3
        natural = (e.base_accuracy - e.current_accuracy) * 0.08
        e.current_accuracy += acc_pull + natural
        
        if stress > 0.3:
            actions.append(f"rebalance:{e.expert_id}(coupling={coupling:.2f})")
    
    return actions


def strategy_conservation_reweight(fleet: Fleet, round_num: int) -> List[str]:
    """C: Conservation-guided reweighting.
    
    Adjust weights to directly restore γ+H. Recovery rate adapts to
    the conservation gap — bigger violation = more aggressive correction.
    """
    actions = []
    active = [e for e in fleet.experts if e.active]
    if not active:
        return []
    
    fleet._compute_conservation()
    gap = fleet.predicted_gamma_H - fleet.gamma_plus_H
    gap_strength = max(0, gap) / max(fleet.predicted_gamma_H, 0.01)  # normalized gap
    
    mean_intent = [sum(e.intent_vector[i] for e in active) / len(active) for i in range(9)]
    
    for e in active:
        alignment = cosine_sim(e.intent_vector, mean_intent)
        contribution = alignment * e.current_accuracy
        e.weight = max(0.1, contribution)
        
        # Recovery rate scales with conservation gap
        recovery_rate = 0.06 + 0.20 * gap_strength
        intent_coupling = 0.06 + 0.25 * gap_strength
        
        # Accuracy recovery
        diff = e.base_accuracy - e.current_accuracy
        e.current_accuracy += diff * recovery_rate
        
        # Intent recovery toward baseline
        e.intent_vector = [v + (bv - v) * intent_coupling for v, bv in zip(e.intent_vector, e.baseline_intent)]
        
        actions.append(f"reweight:{e.expert_id}(w={e.weight:.2f},gap={gap_strength:.3f})")
    
    return actions


STRATEGIES = {
    "quarantine_wait": strategy_quarantine_wait,
    "hebbian_rebalance": strategy_hebbian_rebalance,
    "conservation_reweight": strategy_conservation_reweight,
}


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation(scenario: str, strategy: str, max_rounds: int = 100) -> Dict[str, Any]:
    fleet = Fleet()
    
    baseline_gh = fleet.gamma_plus_H
    baseline_comp = fleet.conservation_compliance()
    baseline_acc = fleet.avg_accuracy()
    
    # Inject shock
    SCENARIOS[scenario](fleet)
    fleet.update()
    
    post_gh = fleet.gamma_plus_H
    post_comp = fleet.conservation_compliance()
    post_acc = fleet.avg_accuracy()
    
    shell_shock = post_comp < 0.85
    
    strategy_fn = STRATEGIES[strategy]
    rounds_data = []
    recovered_round = None
    tiles_lost = 0
    
    for r in range(1, max_rounds + 1):
        actions = strategy_fn(fleet, r)
        fleet.update()
        
        comp = fleet.conservation_compliance()
        acc = fleet.avg_accuracy()
        gh = fleet.gamma_plus_H
        
        above_85 = comp >= 0.85
        active = fleet.active_count()
        quarantined = fleet.quarantined_count()
        
        rounds_data.append({
            "round": r, "gamma_plus_H": round(gh, 4),
            "compliance": round(comp, 4), "accuracy": round(acc, 4),
            "active": active, "quarantined": quarantined,
            "above_85": above_85,
        })
        
        if comp < 0.85:
            tiles_lost += max(1, quarantined + (9 - active))
        
        if recovered_round is None and above_85:
            recovered_round = r
        elif recovered_round is not None and not above_85 and r - recovered_round < 5:
            recovered_round = None  # relapse
    
    return {
        "scenario": scenario, "strategy": strategy,
        "shell_shock_triggered": shell_shock,
        "baseline_gh": round(baseline_gh, 4),
        "baseline_compliance": round(baseline_comp, 4),
        "baseline_accuracy": round(baseline_acc, 4),
        "post_shock_gh": round(post_gh, 4),
        "post_shock_compliance": round(post_comp, 4),
        "post_shock_accuracy": round(post_acc, 4),
        "recovery_round": recovered_round,
        "recovered": recovered_round is not None,
        "tiles_lost": tiles_lost,
        "final_gh": round(rounds_data[-1]["gamma_plus_H"], 4),
        "final_compliance": round(rounds_data[-1]["compliance"], 4),
        "final_accuracy": round(rounds_data[-1]["accuracy"], 4),
        "rounds_sample": rounds_data[::5],
    }


def main():
    print("⚙️ Study 64 v2: Shell Shock Recovery Dynamics")
    print("=" * 60)
    
    all_results = []
    for scenario in SCENARIOS:
        for strategy in STRATEGIES:
            print(f"  {scenario:22s} × {strategy:25s} ... ", end="", flush=True)
            result = run_simulation(scenario, strategy)
            status = f"R{result['recovery_round']}" if result['recovered'] else "✗"
            print(f"{status}  tiles={result['tiles_lost']}")
            all_results.append(result)
    
    # Strategy stats
    strategy_stats = {}
    for strategy in STRATEGIES:
        sr = [r for r in all_results if r["strategy"] == strategy]
        rounds = [r["recovery_round"] for r in sr if r["recovered"]]
        strategy_stats[strategy] = {
            "avg_recovery": round(sum(rounds)/len(rounds), 1) if rounds else None,
            "recovery_rate": f"{len(rounds)}/{len(sr)}",
            "avg_tiles_lost": round(sum(r["tiles_lost"] for r in sr) / len(sr), 1),
            "avg_final_accuracy": round(sum(r["final_accuracy"] for r in sr) / len(sr), 4),
            "avg_final_compliance": round(sum(r["final_compliance"] for r in sr) / len(sr), 4),
        }
    
    output = {
        "study": "Study 64: Shell Shock Recovery Dynamics",
        "version": "2.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hypothesis": "Conservation-guided reweighting recovers fastest because it directly targets the violated constraint (γ+H)",
        "results": all_results,
        "strategy_stats": strategy_stats,
    }
    
    with open("experiments/study64_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    # Print results
    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)
    for strat, stats in strategy_stats.items():
        r = stats["avg_recovery"]
        print(f"  {strat:25s} | avg recovery: {r or 'N/A':>5} rounds | "
              f"tiles lost: {stats['avg_tiles_lost']:>5} | "
              f"final acc: {stats['avg_final_accuracy']:.4f} | "
              f"final comp: {stats['avg_final_compliance']:.4f}")
    
    print("\nRECOVERY GRID (rounds to recover, 100 max):")
    print(f"  {'Scenario':22s} | {'Quarantine':>12s} | {'Hebbian':>12s} | {'Conservation':>12s}")
    print("  " + "-" * 68)
    for scenario in SCENARIOS:
        vals = {}
        for r in all_results:
            if r["scenario"] == scenario:
                vals[r["strategy"]] = r["recovery_round"] or "✗(100+)"
        print(f"  {scenario:22s} | {str(vals.get('quarantine_wait', '?')):>12s} | "
              f"{str(vals.get('hebbian_rebalance', '?')):>12s} | "
              f"{str(vals.get('conservation_reweight', '?')):>12s}")
    
    # Hypothesis
    print("\n🔬 HYPOTHESIS CHECK:")
    cq = strategy_stats["conservation_reweight"]["avg_recovery"]
    hq = strategy_stats["hebbian_rebalance"]["avg_recovery"]
    qq = strategy_stats["quarantine_wait"]["avg_recovery"]
    
    if cq is not None and (hq is None or cq < hq) and (qq is None or cq < qq):
        print(f"  ✅ CONFIRMED: Conservation reweighting fastest ({cq} rounds)")
        print(f"     vs Hebbian {hq}, Quarantine {qq}")
    elif cq is not None and qq is not None and cq < qq:
        print(f"  ✅ PARTIAL: Conservation ({cq}) beats Quarantine ({qq})")
        if hq is not None and hq < cq:
            print(f"     but Hebbian ({hq}) is fastest overall")
    else:
        print(f"  ❌ REJECTED: Conservation reweighting ({cq}) not fastest")
        print(f"     Quarantine: {qq}, Hebbian: {hq}")
    
    print("\n✅ Results → experiments/study64_results.json")


if __name__ == "__main__":
    main()
