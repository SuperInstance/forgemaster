#!/usr/bin/env python3
"""Study 73: Shell Shock Recovery — Proper Controls & Statistics

Redesign of Study 64 (rated 2/7 rigor by Study 69).
Fixes: multiple fleet sizes, shock severities, 4 strategies, 50 trials/condition,
       Cohen's d, Bonferroni correction, proper random seeding.
"""

import json
import math
import random
import statistics
from collections import defaultdict
from itertools import product

SEED = 42
FLEET_SIZES = [5, 9, 15, 25]
SHOCK_SEVERITIES = [1, 3, 5]  # agents failing simultaneously
N_TRIALS = 50
MAX_ROUNDS = 200
COMPLIANCE_THRESHOLD = 0.85

STRATEGIES = ["conservation_reweight", "quarantine", "hebbian", "random_recovery"]


def make_fleet(V, rng):
    """Create a fleet of V experts with realistic accuracies and intents."""
    # Tier distribution: ~1/3 T1, ~1/3 T2, ~1/3 T3
    experts = []
    for i in range(V):
        tier = min(3, int(i * 3 / V) + 1)
        if tier == 1:
            base_acc = rng.uniform(0.85, 0.95)
        elif tier == 2:
            base_acc = rng.uniform(0.70, 0.85)
        else:
            base_acc = rng.uniform(0.55, 0.70)
        # Intent vector: 5-dim unit-ish vector
        intent = [rng.gauss(0, 1) for _ in range(5)]
        mag = math.sqrt(sum(x*x for x in intent)) or 1.0
        intent = [x/mag for x in intent]
        experts.append({
            "accuracy": base_acc,
            "base_accuracy": base_acc,
            "intent": intent,
            "base_intent": intent[:],
            "active": True,
            "quarantine_rounds": 0,
            "clean_rounds": 0,
        })
    return experts


def compute_conservation(experts):
    """Compute conservation metric γ+H for the fleet."""
    active = [e for e in experts if e["active"]]
    if len(active) < 2:
        return 0.0
    
    # γ: alignment with mean intent
    n = len(active)
    mean_intent = [sum(e["intent"][j] for e in active) / n for j in range(5)]
    
    alignments = []
    for e in active:
        dot = sum(a*b for a,b in zip(e["intent"], mean_intent))
        mag_e = math.sqrt(sum(x*x for x in e["intent"])) or 1e-9
        mag_m = math.sqrt(sum(x*x for x in mean_intent)) or 1e-9
        alignments.append(dot / (mag_e * mag_m))
    gamma = sum(alignments) / len(alignments)
    
    # H: accuracy coherence (normalized std of accuracies)
    accs = [e["accuracy"] for e in active]
    if len(accs) < 2 or max(accs) == min(accs):
        H = 1.0
    else:
        acc_std = statistics.stdev(accs)
        H = max(0, 1.0 - acc_std / 0.3)  # normalize: 0.3 std → H=0
    
    return 0.5 * gamma + 0.5 * H


def apply_shock(experts, n_failing, rng):
    """Shock n_failing agents simultaneously."""
    n_failing = min(n_failing, len(experts))
    targets = rng.sample(range(len(experts)), n_failing)
    for idx in targets:
        e = experts[idx]
        # Degrade accuracy 30-70%
        degradation = rng.uniform(0.3, 0.7)
        e["accuracy"] = e["base_accuracy"] * (1 - degradation)
        # Perturb intent
        perturb = [rng.gauss(0, 0.5) for _ in range(5)]
        e["intent"] = [a + b for a, b in zip(e["base_intent"], perturb)]
        mag = math.sqrt(sum(x*x for x in e["intent"])) or 1e-9
        e["intent"] = [x/mag for x in e["intent"]]
    return targets


def simulate_round_conservation(experts, gap, rng):
    """Conservation reweighting: scale recovery by conservation gap."""
    recovery_rate = min(0.30, 0.05 + 0.8 * gap)  # aggressive for large gaps
    intent_coupling = min(0.35, 0.05 + 0.7 * gap)
    
    for e in experts:
        if not e["active"]:
            continue
        # Pull accuracy toward base
        e["accuracy"] += recovery_rate * (e["base_accuracy"] - e["accuracy"])
        # Pull intent toward base
        e["intent"] = [
            i + intent_coupling * (b - i)
            for i, b in zip(e["intent"], e["base_intent"])
        ]
        mag = math.sqrt(sum(x*x for x in e["intent"])) or 1e-9
        e["intent"] = [x/mag for x in e["intent"]]
        # Small noise
        e["accuracy"] += rng.gauss(0, 0.01)
        e["accuracy"] = max(0.1, min(1.0, e["accuracy"]))


def simulate_round_quarantine(experts, rng):
    """Pure quarantine: remove bad agents, passive recovery."""
    passive_rate = 0.04  # 4% passive recovery per round
    
    # Quarantine agents below threshold
    for e in experts:
        if e["accuracy"] < 0.65 * e["base_accuracy"]:
            e["active"] = False
            e["quarantine_rounds"] = 0
        if not e["active"]:
            e["quarantine_rounds"] += 1
            e["accuracy"] += passive_rate * (e["base_accuracy"] - e["accuracy"])
            e["intent"] = [
                i + 0.03 * (b - i)
                for i, b in zip(e["intent"], e["base_intent"])
            ]
            mag = math.sqrt(sum(x*x for x in e["intent"])) or 1e-9
            e["intent"] = [x/mag for x in e["intent"]]
            # Restore after 5 clean rounds with 80%+ accuracy
            if e["accuracy"] >= 0.8 * e["base_accuracy"]:
                e["clean_rounds"] += 1
                if e["clean_rounds"] >= 5:
                    e["active"] = True
                    e["clean_rounds"] = 0
            else:
                e["clean_rounds"] = 0
    
    # Fleet protection: keep at least ceil(V/3) active
    active_count = sum(1 for e in experts if e["active"])
    min_active = max(2, len(experts) // 3)
    if active_count < min_active:
        # Force-activate least-degraded
        inactive = [(i, e) for i, e in enumerate(experts) if not e["active"]]
        inactive.sort(key=lambda x: x[1]["accuracy"], reverse=True)
        for i, e in inactive[:min_active - active_count]:
            e["active"] = True
            e["clean_rounds"] = 0


def simulate_round_hebbian(experts, rng):
    """Hebbian rebalancing: pull toward fleet mean."""
    active = [e for e in experts if e["active"]]
    if len(active) < 2:
        return
    
    n = len(active)
    mean_acc = sum(e["accuracy"] for e in active) / n
    mean_intent = [sum(e["intent"][j] for e in active) / n for j in range(5)]
    mag_m = math.sqrt(sum(x*x for x in mean_intent)) or 1e-9
    mean_intent = [x/mag_m for x in mean_intent]
    
    coupling = 0.08
    for e in active:
        e["accuracy"] += coupling * (mean_acc - e["accuracy"])
        e["intent"] = [
            i + coupling * (m - i)
            for i, m in zip(e["intent"], mean_intent)
        ]
        mag = math.sqrt(sum(x*x for x in e["intent"])) or 1e-9
        e["intent"] = [x/mag for x in e["intent"]]
        e["accuracy"] += rng.gauss(0, 0.01)
        e["accuracy"] = max(0.1, min(1.0, e["accuracy"]))


def simulate_round_random(experts, rng):
    """Random recovery: coin-flip which agents to help each round."""
    for e in experts:
        if rng.random() < 0.5:
            # Help this agent: partial recovery
            recovery = rng.uniform(0.02, 0.15)
            e["accuracy"] += recovery * (e["base_accuracy"] - e["accuracy"])
            coupling = rng.uniform(0.01, 0.10)
            e["intent"] = [
                i + coupling * (b - i)
                for i, b in zip(e["intent"], e["base_intent"])
            ]
            mag = math.sqrt(sum(x*x for x in e["intent"])) or 1e-9
            e["intent"] = [x/mag for x in e["intent"]]
        e["accuracy"] += rng.gauss(0, 0.01)
        e["accuracy"] = max(0.1, min(1.0, e["accuracy"]))


def run_trial(V, n_failing, strategy, trial_seed):
    """Run one trial. Returns (rounds_to_recovery, tiles_lost, final_compliance)."""
    rng = random.Random(trial_seed)
    experts = make_fleet(V, rng)
    
    # Measure baseline compliance
    baseline_compliance = compute_conservation(experts)
    
    # Apply shock
    apply_shock(experts, n_failing, rng)
    
    tiles_lost = 0
    for round_num in range(1, MAX_ROUNDS + 1):
        compliance = compute_conservation(experts)
        
        # Count tiles lost (low-accuracy outputs)
        for e in experts:
            if e["active"] and rng.random() > e["accuracy"]:
                tiles_lost += 1
        
        if compliance >= COMPLIANCE_THRESHOLD:
            return {
                "rounds": round_num,
                "tiles_lost": tiles_lost,
                "final_compliance": compliance,
                "recovered": True,
            }
        
        # Compute gap for conservation strategy
        gap = max(0, COMPLIANCE_THRESHOLD - compliance)
        
        if strategy == "conservation_reweight":
            simulate_round_conservation(experts, gap, rng)
        elif strategy == "quarantine":
            simulate_round_quarantine(experts, rng)
        elif strategy == "hebbian":
            simulate_round_hebbian(experts, rng)
        elif strategy == "random_recovery":
            simulate_round_random(experts, rng)
    
    # Did not recover
    compliance = compute_conservation(experts)
    return {
        "rounds": MAX_ROUNDS,
        "tiles_lost": tiles_lost,
        "final_compliance": compliance,
        "recovered": compliance >= COMPLIANCE_THRESHOLD,
    }


def cohens_d(group_a, group_b):
    """Compute Cohen's d effect size."""
    n1, n2 = len(group_a), len(group_b)
    if n1 < 2 or n2 < 2:
        return None
    m1, m2 = statistics.mean(group_a), statistics.mean(group_b)
    s1, s2 = statistics.variance(group_a), statistics.variance(group_b)
    pooled_std = math.sqrt(((n1-1)*s1 + (n2-1)*s2) / (n1+n2-2))
    if pooled_std == 0:
        return float('inf') if m1 != m2 else 0.0
    return (m1 - m2) / pooled_std


def welch_t_test(group_a, group_b):
    """Welch's t-test returning t-statistic and p-value (two-tailed)."""
    n1, n2 = len(group_a), len(group_b)
    if n1 < 2 or n2 < 2:
        return None, None
    m1, m2 = statistics.mean(group_a), statistics.mean(group_b)
    s1, s2 = statistics.variance(group_a), statistics.variance(group_b)
    se = math.sqrt(s1/n1 + s2/n2)
    if se == 0:
        return None, None
    t = (m1 - m2) / se
    # Approximate p-value using normal approximation (good enough for n>=30)
    # For precise p, we'd use scipy, but let's keep it dependency-free
    # Using a simple approximation
    df = (s1/n1 + s2/n2)**2 / ((s1/n1)**2/(n1-1) + (s2/n2)**2/(n2-1))
    # t-distribution → normal approximation for large df
    z = abs(t)
    # Approximate p from normal CDF
    p = 2.0 * (1.0 - _normal_cdf(z))
    return t, p


def _normal_cdf(z):
    """Approximate normal CDF using error function."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def main():
    rng = random.Random(SEED)
    all_results = {}
    conditions = list(product(FLEET_SIZES, SHOCK_SEVERITIES, STRATEGIES))
    
    print(f"Study 73: Shell Shock Recovery (Redesign)")
    print(f"Conditions: {len(conditions)} × {N_TRIALS} trials = {len(conditions) * N_TRIALS} total runs")
    print(f"Max rounds per trial: {MAX_ROUNDS}")
    print()
    
    for V, n_failing, strategy in conditions:
        key = f"V{V}_F{n_failing}_{strategy}"
        # Cap n_failing at V
        actual_failing = min(n_failing, V)
        
        trial_results = []
        for trial in range(N_TRIALS):
            trial_seed = rng.randint(0, 2**31)
            result = run_trial(V, actual_failing, strategy, trial_seed)
            trial_results.append(result)
        
        all_results[key] = {
            "V": V,
            "n_failing": actual_failing,
            "strategy": strategy,
            "n_trials": N_TRIALS,
            "trials": trial_results,
        }
        
        recovered = [r for r in trial_results if r["recovered"]]
        rounds = [r["rounds"] for r in trial_results]
        tiles = [r["tiles_lost"] for r in trial_results]
        
        print(f"V={V:2d} F={actual_failing} {strategy:25s}: "
              f"recovery={len(recovered)}/{N_TRIALS} "
              f"mean_rounds={statistics.mean(rounds):6.1f} "
              f"mean_tiles={statistics.mean(tiles):6.1f}")
    
    print("\n" + "="*80)
    print("STATISTICAL ANALYSIS")
    print("="*80)
    
    # Aggregate across all conditions for strategy comparison
    strategy_rounds = defaultdict(list)
    strategy_tiles = defaultdict(list)
    strategy_recovered = defaultdict(list)
    
    for key, data in all_results.items():
        for trial in data["trials"]:
            strategy_rounds[data["strategy"]].append(trial["rounds"])
            strategy_tiles[data["strategy"]].append(trial["tiles_lost"])
            strategy_recovered[data["strategy"]].append(trial["recovered"])
    
    print("\n--- Overall Strategy Comparison (all conditions pooled) ---")
    print(f"{'Strategy':25s} {'Mean Rounds':>12s} {'Mean Tiles':>12s} {'Recovery %':>12s}")
    for strat in STRATEGIES:
        rounds = strategy_rounds[strat]
        tiles = strategy_tiles[strat]
        rec = strategy_recovered[strat]
        print(f"{strat:25s} {statistics.mean(rounds):12.1f} {statistics.mean(tiles):12.1f} {100*sum(rec)/len(rec):11.1f}%")
    
    # Pairwise Cohen's d (rounds to recovery)
    print("\n--- Pairwise Cohen's d (rounds to recovery) ---")
    n_comparisons = len(STRATEGIES) * (len(STRATEGIES) - 1) // 2
    bonferroni_alpha = 0.05 / n_comparisons
    print(f"Bonferroni-corrected α = {bonferroni_alpha:.4f} ({n_comparisons} pairwise comparisons)")
    print(f"{'Comparison':55s} {'Cohen d':>8s} {'t-stat':>8s} {'p-value':>10s} {'Significant':>12s}")
    
    pairwise_results = []
    for i, s1 in enumerate(STRATEGIES):
        for s2 in STRATEGIES[i+1:]:
            rounds1 = strategy_rounds[s1]
            rounds2 = strategy_rounds[s2]
            d = cohens_d(rounds1, rounds2)
            t_stat, p_val = welch_t_test(rounds1, rounds2)
            sig = "***" if p_val and p_val < bonferroni_alpha else "ns"
            pairwise_results.append({
                "comparison": f"{s1} vs {s2}",
                "d": d, "t": t_stat, "p": p_val, "sig": sig
            })
            print(f"{s1:25s} vs {s2:25s} {d:8.3f} {t_stat or 0:8.2f} {(p_val or 1):10.6f} {sig:>12s}")
    
    # Breakdown by fleet size
    print("\n--- Recovery Rounds by Fleet Size ---")
    print(f"{'V':>3s} {'Strategy':25s} {'Mean':>8s} {'Std':>8s} {'Median':>8s} {'Recovery%':>10s}")
    for V in FLEET_SIZES:
        for strat in STRATEGIES:
            rounds_list = []
            rec_list = []
            for key, data in all_results.items():
                if data["V"] == V and data["strategy"] == strat:
                    for trial in data["trials"]:
                        rounds_list.append(trial["rounds"])
                        rec_list.append(trial["recovered"])
            if rounds_list:
                rec_pct = 100 * sum(rec_list) / len(rec_list)
                print(f"{V:3d} {strat:25s} {statistics.mean(rounds_list):8.1f} "
                      f"{statistics.stdev(rounds_list):8.1f} "
                      f"{statistics.median(rounds_list):8.1f} {rec_pct:9.1f}%")
    
    # Breakdown by shock severity
    print("\n--- Recovery Rounds by Shock Severity ---")
    print(f"{'F':>3s} {'Strategy':25s} {'Mean':>8s} {'Std':>8s} {'Recovery%':>10s}")
    for F in SHOCK_SEVERITIES:
        for strat in STRATEGIES:
            rounds_list = []
            rec_list = []
            for key, data in all_results.items():
                if data["n_failing"] == F and data["strategy"] == strat:
                    for trial in data["trials"]:
                        rounds_list.append(trial["rounds"])
                        rec_list.append(trial["recovered"])
            if rounds_list:
                rec_pct = 100 * sum(rec_list) / len(rec_list)
                print(f"{F:3d} {strat:25s} {statistics.mean(rounds_list):8.1f} "
                      f"{statistics.stdev(rounds_list):8.1f} {rec_pct:9.1f}%")
    
    # HYPOTHESIS TESTING
    print("\n" + "="*80)
    print("HYPOTHESIS TESTING")
    print("="*80)
    
    # H1: Conservation beats all others (d > 0.8)
    print("\nH1: Conservation reweighting beats all others (Cohen's d > 0.8)")
    h1_results = {}
    for s2 in ["quarantine", "hebbian", "random_recovery"]:
        d = cohens_d(strategy_rounds["conservation_reweight"], strategy_rounds[s2])
        t, p = welch_t_test(strategy_rounds["conservation_reweight"], strategy_rounds[s2])
        h1_results[s2] = {"d": d, "p": p}
        d_str = f"{d:.3f}" if d is not None else "N/A"
        p_str = f"{p:.6f}" if p is not None else "N/A"
        print(f"  vs {s2}: d = {d_str}, p = {p_str} {'✅' if d is not None and d < -0.8 else '❌'}")
    h1_supported = all(v["d"] is not None and v["d"] < -0.8 for v in h1_results.values())
    print(f"  H1 Verdict: {'SUPPORTED ✅' if h1_supported else 'NOT SUPPORTED ❌'}")
    
    # H2: Hebbian worse than quarantine under stress
    print("\nH2: Hebbian rebalancing is worse than quarantine under stress")
    # "Under stress" = high severity (F=5) or large fleet (V>=15)
    hebbian_stress = []
    quarantine_stress = []
    for key, data in all_results.items():
        if data["n_failing"] >= 3 and data["V"] >= 9:
            for trial in data["trials"]:
                if data["strategy"] == "hebbian":
                    hebbian_stress.append(trial["rounds"])
                elif data["strategy"] == "quarantine":
                    quarantine_stress.append(trial["rounds"])
    d_h2 = cohens_d(hebbian_stress, quarantine_stress)
    t_h2, p_h2 = welch_t_test(hebbian_stress, quarantine_stress)
    h2_supported = d_h2 is not None and d_h2 > 0.8  # hebbian > quarantine means positive d (worse)
    print(f"  Hebbian stress mean: {statistics.mean(hebbian_stress):.1f}")
    print(f"  Quarantine stress mean: {statistics.mean(quarantine_stress):.1f}")
    d_str = f"{d_h2:.3f}" if d_h2 is not None else "N/A"
    p_str = f"{p_h2:.6f}" if p_h2 is not None else "N/A"
    print(f"  Cohen's d = {d_str}, p = {p_str}")
    print(f"  H2 Verdict: {'SUPPORTED ✅' if h2_supported else 'NOT SUPPORTED ❌ (Hebbian is BETTER!)' }")
    
    # H3: Recovery time scales with fleet size
    print("\nH3: Recovery time scales with fleet size")
    fleet_means = {}
    for V in FLEET_SIZES:
        rounds_all = []
        for key, data in all_results.items():
            if data["V"] == V:
                for trial in data["trials"]:
                    rounds_all.append(trial["rounds"])
        fleet_means[V] = statistics.mean(rounds_all)
        print(f"  V={V:2d}: mean = {fleet_means[V]:.1f} rounds")
    # Check monotonic increase
    monotonic = all(fleet_means[v1] <= fleet_means[v2] 
                    for v1, v2 in zip(FLEET_SIZES, FLEET_SIZES[1:]))
    # Correlation
    xs = FLEET_SIZES
    ys = [fleet_means[v] for v in FLEET_SIZES]
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / n
    sx = math.sqrt(sum((x-mx)**2 for x in xs) / n)
    sy = math.sqrt(sum((y-my)**2 for y in ys) / n)
    r = cov / (sx * sy) if sx * sy > 0 else 0
    print(f"  Pearson r = {r:.3f}")
    print(f"  Monotonic increase: {monotonic}")
    h3_supported = r > 0.5
    print(f"  H3 Verdict: {'SUPPORTED ✅' if h3_supported else 'NOT SUPPORTED ❌'}")
    
    # H4: Shock severity matters more than strategy choice
    print("\nH4: Shock severity matters more than strategy choice")
    # ANOVA-like: variance explained by severity vs strategy
    severity_groups = defaultdict(list)
    strategy_groups = defaultdict(list)
    for key, data in all_results.items():
        for trial in data["trials"]:
            severity_groups[data["n_failing"]].append(trial["rounds"])
            strategy_groups[data["strategy"]].append(trial["rounds"])
    
    # Between-group variance for severity
    all_rounds = [r for rs in severity_groups.values() for r in rs]
    grand_mean = statistics.mean(all_rounds)
    
    ss_severity = sum(
        len(group) * (statistics.mean(group) - grand_mean)**2
        for group in severity_groups.values()
    )
    ss_strategy = sum(
        len(group) * (statistics.mean(group) - grand_mean)**2
        for group in strategy_groups.values()
    )
    
    ss_total = sum((r - grand_mean)**2 for r in all_rounds)
    
    eta2_severity = ss_severity / ss_total if ss_total > 0 else 0
    eta2_strategy = ss_strategy / ss_total if ss_total > 0 else 0
    
    print(f"  η²(severity) = {eta2_severity:.4f}")
    print(f"  η²(strategy) = {eta2_strategy:.4f}")
    h4_supported = eta2_severity > eta2_strategy
    print(f"  Severity explains {eta2_severity/eta2_strategy:.1f}× more variance than strategy" if eta2_strategy > 0 else "  Strategy explains 0 variance")
    print(f"  H4 Verdict: {'SUPPORTED ✅' if h4_supported else 'NOT SUPPORTED ❌'}")
    
    # Save results
    output = {
        "study": 73,
        "redesign_of": 64,
        "date": "2026-05-15",
        "seed": SEED,
        "fleet_sizes": FLEET_SIZES,
        "shock_severities": SHOCK_SEVERITIES,
        "strategies": STRATEGIES,
        "n_trials": N_TRIALS,
        "max_rounds": MAX_ROUNDS,
        "compliance_threshold": COMPLIANCE_THRESHOLD,
        "n_comparisons_bonferroni": n_comparisons,
        "bonferroni_alpha": bonferroni_alpha,
        "conditions": {},
        "hypotheses": {
            "H1": {"claim": "Conservation beats all (d > 0.8)", "supported": h1_supported, "details": h1_results},
            "H2": {"claim": "Hebbian worse than quarantine under stress", "supported": h2_supported, 
                   "details": {"d": d_h2, "p": p_h2}},
            "H3": {"claim": "Recovery time scales with fleet size", "supported": h3_supported,
                   "details": {"r": r, "fleet_means": fleet_means}},
            "H4": {"claim": "Severity matters more than strategy", "supported": h4_supported,
                   "details": {"eta2_severity": eta2_severity, "eta2_strategy": eta2_strategy}},
        },
        "pairwise_cohens_d": pairwise_results,
    }
    
    # Summarize conditions
    for key, data in all_results.items():
        rounds = [r["rounds"] for r in data["trials"]]
        tiles = [r["tiles_lost"] for r in data["trials"]]
        recovered = sum(1 for r in data["trials"] if r["recovered"])
        output["conditions"][key] = {
            "V": data["V"],
            "n_failing": data["n_failing"],
            "strategy": data["strategy"],
            "mean_rounds": statistics.mean(rounds),
            "std_rounds": statistics.stdev(rounds),
            "median_rounds": statistics.median(rounds),
            "mean_tiles": statistics.mean(tiles),
            "recovery_rate": recovered / N_TRIALS,
        }
    
    with open("experiments/study73_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to experiments/study73_results.json")


if __name__ == "__main__":
    main()
