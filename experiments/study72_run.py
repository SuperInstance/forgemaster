#!/usr/bin/env python3
"""
Study 72: MythosTile Consensus — REDESIGN of Study 58

Addresses all flags from Study 69 audit (2/7 rigor):
- Multiple fleet sizes: V = 5, 9, 15, 25
- Proper control: Random detector (coin flip) baseline
- 50 trials per condition
- Bonferroni correction for 4 fleet sizes × 3 detectors = 12 comparisons
- Effect sizes (Cohen's d)
- Fixed random seed for reproducibility

Hypotheses:
- H1: Dual detector (GL9+Hebbian) beats either alone
- H2: Both detectors beat random baseline
- H3: Performance degrades at larger fleet sizes
- H4: GL(9) maintains zero false positive rate across all sizes
"""
import json, random, math, hashlib, sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any

SEED = 42
random.seed(SEED)

# ── Configuration ──────────────────────────────────────────────────────────
FLEET_SIZES = [5, 9, 15, 25]
N_TRIALS = 50
FAULT_RATE = 0.3  # 30% of fleet members are faulty in faulty scenarios
DETECTORS = ["gl9", "hebbian", "dual", "random"]
N_COMPARISONS = 12  # 4 fleet sizes × 3 non-random detectors for H1
BONFERRONI_ALPHA = 0.05 / N_COMPARISONS  # ≈ 0.00417

FAULT_TYPES = [
    "confidence_drop",    # Expert reports very low confidence
    "confidence_spike",   # Expert reports unrealistically high confidence
    "content_scramble",   # Expert output is gibberish
    "domain_drift",       # Expert answers wrong domain
    "subtle_bias",        # Expert output slightly biased (hardest to detect)
]

# ── Fault Injection ────────────────────────────────────────────────────────

def make_healthy_expert(expert_id: int, domain: str) -> dict:
    """Create a healthy expert's tile output."""
    return {
        "expert": f"expert_{expert_id}",
        "domain": domain,
        "output": f"Result for {domain} query from expert {expert_id}",
        "confidence": random.uniform(0.7, 0.99),
        "tags": [domain, "healthy"],
        "meta": {"answer": f"answer_{expert_id}"}
    }

def make_faulty_expert(expert_id: int, domain: str, fault_type: str) -> dict:
    """Create a faulty expert's tile output based on fault type."""
    base = make_healthy_expert(expert_id, domain)
    base["tags"] = [domain, "faulty", fault_type]
    
    if fault_type == "confidence_drop":
        base["confidence"] = random.uniform(0.05, 0.2)
    elif fault_type == "confidence_spike":
        base["confidence"] = 1.0  # Maximum confidence always
    elif fault_type == "content_scramble":
        base["output"] = "".join(random.choices("abcdefghijklmnopqrstuvwxyz!@#$%", k=40))
        base["confidence"] = random.uniform(0.5, 0.9)  # Looks normal confidence
    elif fault_type == "domain_drift":
        wrong_domains = ["physics", "history", "art", "music", "cooking"]
        wrong = random.choice([d for d in wrong_domains if d != domain])
        base["domain"] = wrong
        base["output"] = f"Result for {wrong} query from expert {expert_id}"
    elif fault_type == "subtle_bias":
        # Slightly wrong but looks plausible
        base["confidence"] = random.uniform(0.6, 0.85)
        base["meta"]["answer"] = f"biased_answer_{expert_id}"
        base["tags"] = [domain, "healthy"]  # Disguised as healthy
    
    return base

def generate_fleet(fleet_size: int, domain: str, inject_faults: bool) -> list:
    """Generate a fleet of expert outputs, optionally with faults."""
    fleet = []
    n_faulty = max(1, int(fleet_size * FAULT_RATE)) if inject_faults else 0
    faulty_ids = random.sample(range(fleet_size), n_faulty) if inject_faults else []
    
    for i in range(fleet_size):
        if i in faulty_ids:
            fault_type = random.choice(FAULT_TYPES)
            fleet.append(make_faulty_expert(i, domain, fault_type))
        else:
            fleet.append(make_healthy_expert(i, domain))
    
    return fleet

# ── GL(9) Detector ────────────────────────────────────────────────────────

def intent_vector(expert_output: dict) -> list:
    """Derive a 9D intent vector from expert output (mirrors mythos_tile.py)."""
    domain = expert_output.get("domain", "")
    source = expert_output.get("expert", "")
    content = expert_output.get("output", "")[:64]
    confidence = expert_output.get("confidence", 0.5)
    tags = expert_output.get("tags", [])
    
    domain_hash = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    source_hash = int(hashlib.md5(source.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    content_hash = int(hashlib.md5(content.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    
    unique_tags = len(set(tags)) if tags else 0
    tag_density = min(1.0, unique_tags / 10.0)
    
    return [
        source_hash,    # C1: boundary
        domain_hash,    # C2: pattern
        content_hash,   # C3: process
        confidence,     # C4: knowledge
        min(1.0, len(tags) / 5.0),  # C5: social
        tag_density,    # C6: deep structure
        0.5,            # C7: instrument (no key)
        0.5,            # C8: paradigm
        1.0,            # C9: stakes (active)
    ]

def cosine_sim(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def gl9_detect(fleet: list, threshold: float = 0.3) -> list:
    """GL(9) consensus detector. Returns list of suspected faulty expert indices.
    
    For each expert, compute mean pairwise cosine similarity with all others.
    Experts with low mean alignment are flagged.
    """
    vectors = [intent_vector(e) for e in fleet]
    n = len(vectors)
    if n < 2:
        return []
    
    mean_sims = []
    for i in range(n):
        sims = [cosine_sim(vectors[i], vectors[j]) for j in range(n) if j != i]
        mean_sims.append(sum(sims) / len(sims) if sims else 0.0)
    
    # Flag experts whose mean similarity is below (global_mean - threshold)
    global_mean = sum(mean_sims) / len(mean_sims)
    flagged = [i for i, s in enumerate(mean_sims) if s < global_mean - threshold]
    
    return flagged

# ── Hebbian Detector ──────────────────────────────────────────────────────

def hebbian_detect(fleet: list, weight_threshold: float = 0.15) -> list:
    """Hebbian flow detector. Tracks confidence patterns and flags anomalies.
    
    Models a simple Hebbian weight update: experts that consistently deviate
    from the fleet's confidence distribution are flagged.
    """
    confidences = [e.get("confidence", 0.5) for e in fleet]
    mean_conf = sum(confidences) / len(confidences)
    std_conf = math.sqrt(sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)) if len(confidences) > 1 else 0.0
    
    if std_conf < 0.01:
        # All confidences are nearly identical — no one is anomalous
        return []
    
    flagged = []
    for i, c in enumerate(confidences):
        z_score = abs(c - mean_conf) / std_conf if std_conf > 0 else 0
        if z_score > 2.0:  # More than 2 standard deviations
            flagged.append(i)
    
    # Also check domain consistency
    domains = [e.get("domain", "") for e in fleet]
    from collections import Counter
    domain_counts = Counter(domains)
    if domain_counts:
        majority_domain = domain_counts.most_common(1)[0][0]
        for i, d in enumerate(domains):
            if d != majority_domain and domain_counts[d] == 1:
                if i not in flagged:
                    flagged.append(i)
    
    return flagged

# ── Dual Detector ─────────────────────────────────────────────────────────

def dual_detect(fleet: list) -> list:
    """Dual detector: flags experts flagged by EITHER GL(9) OR Hebbian."""
    gl9_flagged = set(gl9_detect(fleet))
    hebbian_flagged = set(hebbian_detect(fleet))
    return list(gl9_flagged | hebbian_flagged)

# ── Random Baseline ───────────────────────────────────────────────────────

def random_detect(fleet: list) -> list:
    """Random baseline: each expert has 30% chance of being flagged."""
    return [i for i in range(len(fleet)) if random.random() < 0.3]

# ── Metrics ────────────────────────────────────────────────────────────────

def compute_metrics(flagged: list, actual_faulty: list, fleet_size: int) -> dict:
    """Compute precision, recall, F1 from flagged and actual faulty indices."""
    flagged_set = set(flagged)
    faulty_set = set(actual_faulty)
    
    tp = len(flagged_set & faulty_set)
    fp = len(flagged_set - faulty_set)
    fn = len(faulty_set - flagged_set)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # False positive rate
    tn = fleet_size - len(flagged_set | faulty_set)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "tp": tp, "fp": fp, "fn": fn,
        "n_flagged": len(flagged_set),
        "n_actual_faulty": len(faulty_set),
    }

def cohens_d(group1: list, group2: list) -> float:
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return 0.0
    m1 = sum(group1) / n1
    m2 = sum(group2) / n2
    v1 = sum((x - m1) ** 2 for x in group1) / (n1 - 1) if n1 > 1 else 0
    v2 = sum((x - m2) ** 2 for x in group2) / (n2 - 1) if n2 > 1 else 0
    pooled_std = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)) if (n1 + n2) > 2 else 0
    if pooled_std == 0:
        return 0.0
    return (m1 - m2) / pooled_std

# ── Main Experiment ────────────────────────────────────────────────────────

def run_experiment():
    results = defaultdict(lambda: defaultdict(list))  # results[fleet_size][detector] = [metrics]
    fault_type_results = defaultdict(lambda: defaultdict(list))  # fault_type_results[fault_type][detector] = [metrics]
    
    domains = ["math", "code", "science", "logic", "language"]
    
    for V in FLEET_SIZES:
        for trial in range(N_TRIALS):
            domain = random.choice(domains)
            
            # ── Faulty scenario ──
            fleet = generate_fleet(V, domain, inject_faults=True)
            actual_faulty = [i for i, e in enumerate(fleet) if "faulty" in e.get("tags", [])]
            # Include disguised faults
            for i, e in enumerate(fleet):
                if e.get("meta", {}).get("answer", "").startswith("biased_"):
                    if i not in actual_faulty:
                        actual_faulty.append(i)
            
            for detector_name, detector_fn in [("gl9", gl9_detect), ("hebbian", hebbian_detect), 
                                                 ("dual", dual_detect), ("random", random_detect)]:
                flagged = detector_fn(fleet)
                metrics = compute_metrics(flagged, actual_faulty, V)
                metrics["trial"] = trial
                metrics["domain"] = domain
                metrics["fleet_size"] = V
                metrics["scenario"] = "faulty"
                results[V][detector_name].append(metrics)
            
            # ── Healthy scenario (for false positive rate) ──
            fleet_healthy = generate_fleet(V, domain, inject_faults=False)
            for detector_name, detector_fn in [("gl9", gl9_detect), ("hebbian", hebbian_detect),
                                                 ("dual", dual_detect), ("random", random_detect)]:
                flagged = detector_fn(fleet_healthy)
                metrics = compute_metrics(flagged, [], V)
                metrics["trial"] = trial
                metrics["domain"] = domain
                metrics["fleet_size"] = V
                metrics["scenario"] = "healthy"
                results[V][detector_name].append(metrics)
    
    return results

def analyze_results(results: dict) -> dict:
    """Compute aggregate statistics with effect sizes and significance tests."""
    analysis = {}
    
    for V in FLEET_SIZES:
        analysis[V] = {}
        for detector in DETECTORS:
            faulty_metrics = [m for m in results[V][detector] if m["scenario"] == "faulty"]
            healthy_metrics = [m for m in results[V][detector] if m["scenario"] == "healthy"]
            
            if not faulty_metrics:
                continue
            
            precisions = [m["precision"] for m in faulty_metrics]
            recalls = [m["recall"] for m in faulty_metrics]
            f1s = [m["f1"] for m in faulty_metrics]
            fprs = [m["fpr"] for m in healthy_metrics]
            
            analysis[V][detector] = {
                "precision": {
                    "mean": sum(precisions) / len(precisions),
                    "std": math.sqrt(sum((x - sum(precisions)/len(precisions))**2 for x in precisions) / (len(precisions)-1)) if len(precisions) > 1 else 0,
                    "values": precisions,
                },
                "recall": {
                    "mean": sum(recalls) / len(recalls),
                    "std": math.sqrt(sum((x - sum(recalls)/len(recalls))**2 for x in recalls) / (len(recalls)-1)) if len(recalls) > 1 else 0,
                    "values": recalls,
                },
                "f1": {
                    "mean": sum(f1s) / len(f1s),
                    "std": math.sqrt(sum((x - sum(f1s)/len(f1s))**2 for x in f1s) / (len(f1s)-1)) if len(f1s) > 1 else 0,
                    "values": f1s,
                },
                "fpr_healthy": {
                    "mean": sum(fprs) / len(fprs) if fprs else 0,
                    "std": math.sqrt(sum((x - sum(fprs)/len(fprs))**2 for x in fprs) / (len(fprs)-1)) if len(fprs) > 1 else 0,
                    "values": fprs,
                },
                "n_faulty_trials": len(faulty_metrics),
                "n_healthy_trials": len(healthy_metrics),
            }
    
    # ── Effect sizes ──
    effect_sizes = {}
    for V in FLEET_SIZES:
        effect_sizes[V] = {}
        
        # H1: Dual vs GL9 alone, Dual vs Hebbian alone
        dual_f1s = analysis[V]["dual"]["f1"]["values"]
        gl9_f1s = analysis[V]["gl9"]["f1"]["values"]
        hebb_f1s = analysis[V]["hebbian"]["f1"]["values"]
        rand_f1s = analysis[V]["random"]["f1"]["values"]
        
        effect_sizes[V]["dual_vs_gl9"] = cohens_d(dual_f1s, gl9_f1s)
        effect_sizes[V]["dual_vs_hebbian"] = cohens_d(dual_f1s, hebb_f1s)
        
        # H2: Each detector vs random
        effect_sizes[V]["gl9_vs_random"] = cohens_d(gl9_f1s, rand_f1s)
        effect_sizes[V]["hebbian_vs_random"] = cohens_d(hebb_f1s, rand_f1s)
        effect_sizes[V]["dual_vs_random"] = cohens_d(dual_f1s, rand_f1s)
    
    # ── H3: Performance degradation with fleet size ──
    degradation = {}
    for detector in DETECTORS:
        means = [analysis[V][detector]["f1"]["mean"] for V in FLEET_SIZES]
        degradation[detector] = {
            "f1_by_size": {str(V): analysis[V][detector]["f1"]["mean"] for V in FLEET_SIZES},
            "trend": "degrading" if means[-1] < means[0] else "stable/improving",
            "delta": means[-1] - means[0],
        }
    
    # ── H4: GL9 false positive rate across sizes ──
    gl9_fpr = {str(V): analysis[V]["gl9"]["fpr_healthy"]["mean"] for V in FLEET_SIZES}
    
    # ── Significance testing (paired t-test approximation) ──
    def paired_t(group1_vals, group2_vals):
        n = min(len(group1_vals), len(group2_vals))
        if n < 2:
            return {"t": 0, "p": 1.0, "significant": False}
        diffs = [group1_vals[i] - group2_vals[i] for i in range(n)]
        mean_d = sum(diffs) / n
        std_d = math.sqrt(sum((d - mean_d)**2 for d in diffs) / (n-1)) if n > 1 else 0
        if std_d == 0:
            return {"t": 0, "p": 1.0, "significant": False}
        t_stat = mean_d / (std_d / math.sqrt(n))
        # Approximate p-value using normal approximation for large n
        # For df=49, critical values are close to normal
        p_val = 2 * (1 - _t_cdf(abs(t_stat), n - 1))
        return {"t": round(t_stat, 4), "p": round(p_val, 6), 
                "significant_bonferroni": p_val < BONFERRONI_ALPHA,
                "significant_uncorrected": p_val < 0.05}
    
    significance = {}
    for V in FLEET_SIZES:
        significance[V] = {
            "H1_dual_vs_gl9": paired_t(analysis[V]["dual"]["f1"]["values"], analysis[V]["gl9"]["f1"]["values"]),
            "H1_dual_vs_hebbian": paired_t(analysis[V]["dual"]["f1"]["values"], analysis[V]["hebbian"]["f1"]["values"]),
            "H2_gl9_vs_random": paired_t(analysis[V]["gl9"]["f1"]["values"], analysis[V]["random"]["f1"]["values"]),
            "H2_hebbian_vs_random": paired_t(analysis[V]["hebbian"]["f1"]["values"], analysis[V]["random"]["f1"]["values"]),
            "H2_dual_vs_random": paired_t(analysis[V]["dual"]["f1"]["values"], analysis[V]["random"]["f1"]["values"]),
        }
    
    return {
        "analysis": analysis,
        "effect_sizes": effect_sizes,
        "degradation": degradation,
        "gl9_fpr": gl9_fpr,
        "significance": significance,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "n_comparisons": N_COMPARISONS,
    }

def _t_cdf(t_val, df):
    """Approximate CDF of Student's t-distribution."""
    x = df / (df + t_val * t_val)
    try:
        import mpmath
        # For t >= 0: CDF(t, df) = 1 - 0.5 * I_x(df/2, 1/2)
        ibeta = float(mpmath.betainc(df/2, 0.5, 0, x, regularized=True))
        if t_val >= 0:
            return 1.0 - 0.5 * ibeta
        else:
            return 0.5 * ibeta
    except ImportError:
        # Fallback: normal approximation (accurate for df > 30)
        return _normal_cdf(t_val)
    
def _normal_cdf(x):
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Study 72: MythosTile Consensus — Redesign of Study 58")
    print(f"Fleet sizes: {FLEET_SIZES}")
    print(f"Trials per condition: {N_TRIALS}")
    print(f"Bonferroni alpha: {BONFERRONI_ALPHA:.4f} (for {N_COMPARISONS} comparisons)")
    print()
    
    print("Running experiment...")
    results = run_experiment()
    
    print("Analyzing results...")
    analysis = analyze_results(results)
    
    # ── Print summary ──
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    for V in FLEET_SIZES:
        print(f"\n── Fleet Size V={V} ──")
        print(f"{'Detector':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'FPR(healthy)':>13}")
        print("-" * 55)
        for det in DETECTORS:
            a = analysis["analysis"][V][det]
            print(f"{det:<12} {a['precision']['mean']:>10.3f} {a['recall']['mean']:>10.3f} "
                  f"{a['f1']['mean']:>10.3f} {a['fpr_healthy']['mean']:>13.3f}")
    
    print("\n── Effect Sizes (Cohen's d) ──")
    for V in FLEET_SIZES:
        es = analysis["effect_sizes"][V]
        print(f"V={V:>2}: dual_vs_gl9={es['dual_vs_gl9']:+.3f}  "
              f"dual_vs_hebbian={es['dual_vs_hebbian']:+.3f}  "
              f"gl9_vs_random={es['gl9_vs_random']:+.3f}  "
              f"dual_vs_random={es['dual_vs_random']:+.3f}")
    
    print("\n── Hypothesis Verdicts ──")
    
    # H1: Dual beats either alone
    h1_supported = True
    for V in FLEET_SIZES:
        sig = analysis["significance"][V]
        es = analysis["effect_sizes"][V]
        dual_beats_gl9 = es["dual_vs_gl9"] > 0 and sig["H1_dual_vs_gl9"]["significant_bonferroni"]
        dual_beats_hebb = es["dual_vs_hebbian"] > 0 and sig["H1_dual_vs_hebbian"]["significant_bonferroni"]
        if not (dual_beats_gl9 or dual_beats_hebb):
            h1_supported = False
            break
    print(f"H1 (Dual beats either alone): {'✅ SUPPORTED' if h1_supported else '❌ NOT SUPPORTED'}")
    
    # H2: Both detectors beat random
    h2_gl9 = all(
        analysis["significance"][V]["H2_gl9_vs_random"]["significant_bonferroni"] and analysis["effect_sizes"][V]["gl9_vs_random"] > 0
        for V in FLEET_SIZES
    )
    h2_hebb = all(
        analysis["significance"][V]["H2_hebbian_vs_random"]["significant_bonferroni"] and analysis["effect_sizes"][V]["hebbian_vs_random"] > 0
        for V in FLEET_SIZES
    )
    h2_dual = all(
        analysis["significance"][V]["H2_dual_vs_random"]["significant_bonferroni"] and analysis["effect_sizes"][V]["dual_vs_random"] > 0
        for V in FLEET_SIZES
    )
    print(f"H2a (GL9 beats random):  {'✅ SUPPORTED' if h2_gl9 else '❌ NOT SUPPORTED'}")
    print(f"H2b (Hebbian beats random): {'✅ SUPPORTED' if h2_hebb else '❌ NOT SUPPORTED'}")
    print(f"H2c (Dual beats random): {'✅ SUPPORTED' if h2_dual else '❌ NOT SUPPORTED'}")
    
    # H3: Performance degrades at larger fleet sizes
    degradation_deltas = [analysis["degradation"][d]["delta"] for d in DETECTORS if d != "random"]
    h3_supported = all(d < 0 for d in degradation_deltas)
    print(f"H3 (Performance degrades at larger V): {'✅ SUPPORTED' if h3_supported else '❌ NOT SUPPORTED'}")
    for d in ["gl9", "hebbian", "dual"]:
        print(f"  {d}: Δ={analysis['degradation'][d]['delta']:+.3f}")
    
    # H4: GL9 maintains zero false positive rate
    max_gl9_fpr = max(analysis["gl9_fpr"].values())
    h4_supported = max_gl9_fpr == 0.0
    print(f"H4 (GL9 zero FPR): {'✅ SUPPORTED' if h4_supported else '❌ NOT SUPPORTED'} (max FPR={max_gl9_fpr:.3f})")
    
    # ── Save JSON ──
    output = {
        "study": 72,
        "redesign_of": 58,
        "date": "2026-05-15",
        "seed": SEED,
        "fleet_sizes": FLEET_SIZES,
        "n_trials": N_TRIALS,
        "n_comparisons": N_COMPARISONS,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "summary": {
            "per_fleet_size": {},
            "effect_sizes": analysis["effect_sizes"],
            "degradation": analysis["degradation"],
            "gl9_fpr": analysis["gl9_fpr"],
            "significance": analysis["significance"],
            "hypotheses": {
                "H1_dual_beats_either": h1_supported,
                "H2a_gl9_beats_random": h2_gl9,
                "H2b_hebbian_beats_random": h2_hebb,
                "H2c_dual_beats_random": h2_dual,
                "H3_degradation": h3_supported,
                "H4_gl9_zero_fpr": h4_supported,
            }
        }
    }
    
    for V in FLEET_SIZES:
        output["summary"]["per_fleet_size"][str(V)] = {}
        for det in DETECTORS:
            a = analysis["analysis"][V][det]
            output["summary"]["per_fleet_size"][str(V)][det] = {
                "precision_mean": round(a["precision"]["mean"], 4),
                "precision_std": round(a["precision"]["std"], 4),
                "recall_mean": round(a["recall"]["mean"], 4),
                "recall_std": round(a["recall"]["std"], 4),
                "f1_mean": round(a["f1"]["mean"], 4),
                "f1_std": round(a["f1"]["std"], 4),
                "fpr_healthy_mean": round(a["fpr_healthy"]["mean"], 4),
                "n_faulty_trials": a["n_faulty_trials"],
                "n_healthy_trials": a["n_healthy_trials"],
            }
    
    with open("experiments/study72_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to experiments/study72_results.json")
