#!/usr/bin/env python3
"""
STUDY 58: MythosTile Consensus — GL(9) vs Hebbian Fault Detection Agreement

QUESTION: When experts disagree, do GL(9) consensus checking and Hebbian anomaly
detection identify the same faulty experts?

Phases:
  A — Agreement measurement (50 scenarios, 25 healthy + 25 faulty)
  B — Disagreement analysis (characterize complementary detection modes)
  C — Combined detection (union detector F1)
"""

import json
import math
import random
import sys
import os
import time
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mythos_tile import MythosTile, MythosPipeline, ModelTier
from gl9_consensus import (
    GL9HolonomyConsensus, GL9Agent, IntentVector, GL9Matrix,
    GL9ConsensusResult, pearson_correlation
)
import numpy as np


# ---------------------------------------------------------------------------
# Hebbian Anomaly Detector (simplified, inline — uses flow frequency patterns)
# ---------------------------------------------------------------------------

class SimpleHebbianAnomalyDetector:
    """Detect anomalous experts by observing tile flow patterns.

    Hebbian anomaly detection works by tracking:
    - Confidence distribution per expert
    - Content hash diversity per expert
    - Flow frequency per expert (how many tiles they produce)

    An anomaly = expert whose behavior deviates significantly from the group.
    This is the Hebbian mode: frequency/pattern-based, not intent-based.
    """

    def __init__(self, confidence_sigma: float = 2.0, frequency_sigma: float = 2.0):
        self.confidence_sigma = confidence_sigma
        self.frequency_sigma = frequency_sigma

    def detect(self, tiles: List[MythosTile]) -> List[str]:
        """Return list of expert names flagged as anomalous."""
        if len(tiles) < 3:
            return []

        # Group by expert
        by_expert: Dict[str, List[MythosTile]] = defaultdict(list)
        for t in tiles:
            by_expert[t.source].append(t)

        experts = list(by_expert.keys())
        if len(experts) < 2:
            return []

        # Compute per-expert features
        features: Dict[str, Dict[str, float]] = {}
        for name, expert_tiles in by_expert.items():
            confs = [t.confidence for t in expert_tiles]
            # Content diversity (unique content hashes / total tiles)
            content_hashes = set(hashlib.md5(t.content[:64].encode()).hexdigest() for t in expert_tiles)
            # Tag density
            tag_counts = [len(t.tags) for t in expert_tiles]
            # Domain consistency
            domains = set(t.domain for t in expert_tiles)

            features[name] = {
                "mean_confidence": np.mean(confs),
                "std_confidence": np.std(confs) if len(confs) > 1 else 0.0,
                "tile_count": len(expert_tiles),
                "content_diversity": len(content_hashes) / max(len(expert_tiles), 1),
                "mean_tag_count": np.mean(tag_counts) if tag_counts else 0.0,
                "domain_count": len(domains),
                "min_confidence": min(confs),
            }

        # Compute z-scores for each feature across experts
        flagged: Set[str] = set()

        for feat_name in ["mean_confidence", "content_diversity", "tile_count", "min_confidence"]:
            values = [(name, features[name][feat_name]) for name in experts]
            vals = [v for _, v in values]
            mean_val = np.mean(vals)
            std_val = np.std(vals) if len(vals) > 1 else 1.0
            if std_val < 1e-10:
                continue

            for name, val in values:
                z = abs(val - mean_val) / std_val
                if z > self.confidence_sigma:
                    flagged.add(name)

        return list(flagged)


# ---------------------------------------------------------------------------
# Scenario Generator
# ---------------------------------------------------------------------------

EXPERT_NAMES = [
    "conservation", "architect", "translator", "hebbian",
    "constraint-forge", "router", "validator", "monitor", "deployer"
]

DOMAINS = [
    "math", "physics", "constraint-theory", "fleet-ops",
    "training", "conservation", "routing", "validation"
]

FAULT_TYPES = [
    "confidence_drop",     # Expert produces very low confidence
    "content_scramble",    # Expert produces unrelated content
    "domain_drift",        # Expert switches to wrong domain
    "confidence_spike",    # Expert overconfident
    "silent_expert",       # Expert produces empty/minimal output
]


@dataclass
class ScenarioResult:
    scenario_id: int
    is_healthy: bool
    n_experts: int
    fault_type: Optional[str]
    ground_truth_faulty: List[str]

    # GL(9) results
    gl9_faulty: List[str]
    gl9_consensus: bool
    gl9_alignment: float
    gl9_deviation: float

    # Hebbian results
    hebbian_faulty: List[str]

    # Agreement metrics
    agreement: bool  # do they flag the same experts?
    exact_match: bool  # exact same set?
    gl9_only: List[str]  # caught by GL(9) only
    hebbian_only: List[str]  # caught by Hebbian only
    both_caught: List[str]  # caught by both


def generate_healthy_tile(expert: str, domain: str, rng: random.Random) -> MythosTile:
    """Generate a normal, healthy tile from an expert."""
    conf = 0.7 + 0.3 * rng.random()  # 0.7-1.0
    content_options = {
        "math": f"Compute norm({rng.randint(1,10)}+{rng.randint(1,10)}ω) in Eisenstein integers",
        "physics": f"Conservation check: γ+H = {1.2 + 0.1*rng.random():.3f} within bounds",
        "constraint-theory": f"Drift analysis: δ = {0.01*rng.random():.4f} (within tolerance)",
        "fleet-ops": f"Tile routing: {rng.randint(10,50)} tiles delivered, compliance {0.9+0.1*rng.random():.2%}",
        "training": f"LoRA batch {rng.randint(1,100)}: loss={0.01+0.05*rng.random():.4f}",
        "conservation": f"γ+H conservation verified: deviation {0.01*rng.random():.4f}σ",
        "routing": f"Hebbian route: strength {0.5+0.5*rng.random():.3f} to {rng.choice(['room-a','room-b','room-c'])}",
        "validation": f"Tile validation: {rng.randint(5,20)} checks passed",
    }
    content = content_options.get(domain, f"Standard output from {expert} in {domain}")

    return MythosTile(
        domain=domain,
        source=expert,
        content=content,
        confidence=conf,
        room=f"expert-{expert}",
        tags=[domain, "standard"],
        target_tier=1,
        lifecycle="active",
    )


def generate_faulty_tile(expert: str, domain: str, fault_type: str,
                         rng: random.Random) -> MythosTile:
    """Generate a tile with a specific fault."""
    base = generate_healthy_tile(expert, domain, rng)

    if fault_type == "confidence_drop":
        base.confidence = 0.05 + 0.15 * rng.random()  # 0.05-0.2
    elif fault_type == "content_scramble":
        base.content = f"RANDOM_DATA_{rng.randint(10000,99999)} {rng.choice(['xyz','abc','def'])}"
        base.tags = ["unknown", "scrambled"]
    elif fault_type == "domain_drift":
        wrong_domain = rng.choice([d for d in DOMAINS if d != domain])
        base.domain = wrong_domain
        base.content = f"Drifted output: expected {domain}, got {wrong_domain}"
    elif fault_type == "confidence_spike":
        base.confidence = 1.0  # perfect certainty (suspicious)
        base.meta["override"] = True
    elif fault_type == "silent_expert":
        base.content = ""
        base.confidence = 0.0
        base.tags = []

    return base


def run_scenario(scenario_id: int, is_healthy: bool, rng: random.Random) -> ScenarioResult:
    """Run a single scenario and return results."""
    n_experts = rng.randint(5, 9)
    experts = rng.sample(EXPERT_NAMES, n_experts)
    domain = rng.choice(DOMAINS)

    fault_type = None
    ground_truth: List[str] = []

    if not is_healthy:
        fault_type = rng.choice(FAULT_TYPES)
        n_faulty = rng.choice([1, 1, 1, 2])  # 75% single, 25% double
        ground_truth = rng.sample(experts, n_faulty)

    # Generate tiles
    pipeline = MythosPipeline()
    tiles: List[MythosTile] = []

    for expert in experts:
        if expert in ground_truth:
            tile = generate_faulty_tile(expert, domain, fault_type, rng)
        else:
            tile = generate_healthy_tile(expert, domain, rng)
        pipeline.accept_expert_output(expert, tile.to_expert_output())
        tiles.append(tile)

    # Run GL(9) consensus
    gl9_result = pipeline.check_gl9_consensus()
    gl9_faulty = gl9_result.get("faulty_experts", [])
    gl9_consensus = gl9_result.get("consensus", True)
    gl9_alignment = gl9_result.get("alignment", 1.0)
    gl9_deviation = gl9_result.get("deviation", 0.0)

    # Run Hebbian anomaly detection
    hebbian_detector = SimpleHebbianAnomalyDetector(confidence_sigma=1.8)
    hebbian_faulty = hebbian_detector.detect(tiles)

    # Agreement analysis
    gl9_set = set(gl9_faulty)
    hebbian_set = set(hebbian_faulty)
    truth_set = set(ground_truth)

    gl9_only = list(gl9_set - hebbian_set)
    hebbian_only = list(hebbian_set - gl9_set)
    both_caught = list(gl9_set & hebbian_set)

    return ScenarioResult(
        scenario_id=scenario_id,
        is_healthy=is_healthy,
        n_experts=n_experts,
        fault_type=fault_type,
        ground_truth_faulty=ground_truth,
        gl9_faulty=gl9_faulty,
        gl9_consensus=gl9_consensus,
        gl9_alignment=gl9_alignment,
        gl9_deviation=gl9_deviation,
        hebbian_faulty=hebbian_faulty,
        agreement=gl9_set == hebbian_set,
        exact_match=gl9_set == hebbian_set,
        gl9_only=gl9_only,
        hebbian_only=hebbian_only,
        both_caught=both_caught,
    )


# ---------------------------------------------------------------------------
# Phase B: Disagreement Analysis
# ---------------------------------------------------------------------------

def analyze_disagreements(results: List[ScenarioResult]) -> Dict[str, Any]:
    """Analyze cases where GL(9) and Hebbian disagree."""
    disagreements = [r for r in results if not r.agreement]

    if not disagreements:
        return {"total_disagreements": 0, "analysis": "Perfect agreement"}

    # What faults does GL(9) catch that Hebbian misses?
    gl9_catches = defaultdict(int)
    hebbian_catches = defaultdict(int)
    gl9_only_faults = defaultdict(int)
    hebbian_only_faults = defaultdict(int)

    for r in disagreements:
        if r.fault_type:
            if r.gl9_faulty and not r.hebbian_faulty:
                gl9_only_faults[r.fault_type] += 1
            if r.hebbian_faulty and not r.gl9_faulty:
                hebbian_only_faults[r.fault_type] += 1

    return {
        "total_disagreements": len(disagreements),
        "gl9_only_fault_types": dict(gl9_only_faults),
        "hebbian_only_fault_types": dict(hebbian_only_faults),
        "disagreement_rate": round(len(disagreements) / len(results), 4),
    }


# ---------------------------------------------------------------------------
# Phase C: Combined Detection
# ---------------------------------------------------------------------------

def compute_metrics(results: List[ScenarioResult]) -> Dict[str, Any]:
    """Compute precision/recall/F1 for each detector and combined."""

    def prf(results_list: List[ScenarioResult], detector_fn) -> Dict[str, float]:
        tp, fp, fn, tn = 0, 0, 0, 0
        for r in results_list:
            detected = set(detector_fn(r))
            truth = set(r.ground_truth_faulty)

            tp += len(detected & truth)
            fp += len(detected - truth)
            fn += len(truth - detected)
            tn += len((set(EXPERT_NAMES[:r.n_experts]) - truth) - detected)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {"precision": round(precision, 4), "recall": round(recall, 4),
                "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn, "tn": tn}

    gl9_metrics = prf(results, lambda r: r.gl9_faulty)
    hebbian_metrics = prf(results, lambda r: r.hebbian_faulty)

    # Combined: flag if EITHER detector flags
    combined_metrics = prf(results, lambda r: list(set(r.gl9_faulty) | set(r.hebbian_faulty)))

    # Consensus: flag only if BOTH detectors agree
    consensus_metrics = prf(results, lambda r: list(set(r.gl9_faulty) & set(r.hebbian_faulty)))

    return {
        "gl9": gl9_metrics,
        "hebbian": hebbian_metrics,
        "combined_union": combined_metrics,
        "combined_intersection": consensus_metrics,
    }


# ---------------------------------------------------------------------------
# Main Experiment
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("STUDY 58: MythosTile Consensus — GL(9) vs Hebbian Fault Detection")
    print("=" * 70)

    rng = random.Random(42)  # reproducible
    results: List[ScenarioResult] = []

    # Phase A: 50 scenarios (25 healthy + 25 faulty)
    print("\n--- Phase A: Agreement Measurement (50 scenarios) ---")

    # 25 healthy scenarios
    for i in range(25):
        r = run_scenario(i, is_healthy=True, rng=rng)
        results.append(r)

    # 25 faulty scenarios (5 per fault type, even coverage)
    results = []
    for i in range(25):
        results.append(run_scenario(i, is_healthy=True, rng=rng))

    for fault_idx, fault_type in enumerate(FAULT_TYPES):
        for j in range(5):
            results.append(run_scenario_forced_fault(25 + fault_idx * 5 + j, fault_type, rng))

    # Analyze agreement
    agreement_count = sum(1 for r in results if r.agreement)
    healthy_results = [r for r in results if r.is_healthy]
    faulty_results = [r for r in results if not r.is_healthy]

    print(f"\n  Total scenarios: {len(results)}")
    print(f"  Healthy: {len(healthy_results)}, Faulty: {len(faulty_results)}")
    print(f"  Agreement rate: {agreement_count}/{len(results)} ({agreement_count/len(results):.1%})")

    # Per-fault-type breakdown
    fault_breakdown = defaultdict(lambda: {"total": 0, "gl9_caught": 0, "hebbian_caught": 0,
                                            "both_caught": 0, "neither_caught": 0})
    for r in faulty_results:
        ft = r.fault_type or "unknown"
        fault_breakdown[ft]["total"] += 1
        truth = set(r.ground_truth_faulty)
        gl9_hit = bool(truth & set(r.gl9_faulty))
        hebb_hit = bool(truth & set(r.hebbian_faulty))
        if gl9_hit:
            fault_breakdown[ft]["gl9_caught"] += 1
        if hebb_hit:
            fault_breakdown[ft]["hebbian_caught"] += 1
        if gl9_hit and hebb_hit:
            fault_breakdown[ft]["both_caught"] += 1
        if not gl9_hit and not hebb_hit:
            fault_breakdown[ft]["neither_caught"] += 1

    print(f"\n  Per-fault-type detection:")
    for ft, stats in sorted(fault_breakdown.items()):
        print(f"    {ft:20s}: GL(9) {stats['gl9_caught']}/{stats['total']}, "
              f"Hebbian {stats['hebbian_caught']}/{stats['total']}, "
              f"Both {stats['both_caught']}/{stats['total']}, "
              f"Neither {stats['neither_caught']}/{stats['total']}")

    # Phase B: Disagreement analysis
    print("\n--- Phase B: Disagreement Analysis ---")
    disagreement = analyze_disagreements(results)
    print(f"  Disagreements: {disagreement['total_disagreements']}")
    print(f"  Disagreement rate: {disagreement['disagreement_rate']:.1%}")
    if disagreement['gl9_only_fault_types']:
        print(f"  GL(9)-only catches by fault: {disagreement['gl9_only_fault_types']}")
    if disagreement['hebbian_only_fault_types']:
        print(f"  Hebbian-only catches by fault: {disagreement['hebbian_only_fault_types']}")

    # Phase C: Combined detection
    print("\n--- Phase C: Combined Detection Metrics ---")
    metrics = compute_metrics(results)
    print(f"  GL(9) alone:       P={metrics['gl9']['precision']:.3f}  R={metrics['gl9']['recall']:.3f}  F1={metrics['gl9']['f1']:.3f}")
    print(f"  Hebbian alone:     P={metrics['hebbian']['precision']:.3f}  R={metrics['hebbian']['recall']:.3f}  F1={metrics['hebbian']['f1']:.3f}")
    print(f"  Combined (union):  P={metrics['combined_union']['precision']:.3f}  R={metrics['combined_union']['recall']:.3f}  F1={metrics['combined_union']['f1']:.3f}")
    print(f"  Combined (∩):      P={metrics['combined_intersection']['precision']:.3f}  R={metrics['combined_intersection']['recall']:.3f}  F1={metrics['combined_intersection']['f1']:.3f}")

    # False positive analysis on healthy scenarios
    healthy_gl9_fp = sum(1 for r in healthy_results if r.gl9_faulty)
    healthy_hebbian_fp = sum(1 for r in healthy_results if r.hebbian_faulty)
    print(f"\n  False positives on healthy scenarios:")
    print(f"    GL(9): {healthy_gl9_fp}/{len(healthy_results)}")
    print(f"    Hebbian: {healthy_hebbian_fp}/{len(healthy_results)}")

    # Save results
    output = {
        "study": "STUDY-58",
        "title": "MythosTile Consensus — GL(9) vs Hebbian Fault Detection",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {
            "total_scenarios": len(results),
            "healthy": len(healthy_results),
            "faulty": len(faulty_results),
            "agreement_rate": round(agreement_count / len(results), 4),
            "fault_breakdown": dict(fault_breakdown),
        },
        "disagreement_analysis": disagreement,
        "metrics": metrics,
        "false_positives": {
            "gl9_on_healthy": healthy_gl9_fp,
            "hebbian_on_healthy": healthy_hebbian_fp,
            "healthy_total": len(healthy_results),
        },
        "scenario_details": [asdict(r) for r in results],
    }

    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study58_results.json")
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {results_path}")

    # Generate markdown report
    generate_report(output, metrics, disagreement, fault_breakdown, healthy_results, healthy_gl9_fp, healthy_hebbian_fp)

    return output


def run_scenario_forced_fault(scenario_id: int, fault_type: str,
                               rng: random.Random) -> ScenarioResult:
    """Run a scenario with a forced fault type."""
    n_experts = rng.randint(5, 9)
    experts = rng.sample(EXPERT_NAMES, n_experts)
    domain = rng.choice(DOMAINS)

    n_faulty = rng.choice([1, 1, 1, 2])
    ground_truth = rng.sample(experts, n_faulty)

    pipeline = MythosPipeline()
    tiles: List[MythosTile] = []

    for expert in experts:
        if expert in ground_truth:
            tile = generate_faulty_tile(expert, domain, fault_type, rng)
        else:
            tile = generate_healthy_tile(expert, domain, rng)
        pipeline.accept_expert_output(expert, tile.to_expert_output())
        tiles.append(tile)

    gl9_result = pipeline.check_gl9_consensus()
    gl9_faulty = gl9_result.get("faulty_experts", [])

    hebbian_detector = SimpleHebbianAnomalyDetector(confidence_sigma=1.8)
    hebbian_faulty = hebbian_detector.detect(tiles)

    gl9_set = set(gl9_faulty)
    hebbian_set = set(hebbian_faulty)

    return ScenarioResult(
        scenario_id=scenario_id,
        is_healthy=False,
        n_experts=n_experts,
        fault_type=fault_type,
        ground_truth_faulty=ground_truth,
        gl9_faulty=gl9_faulty,
        gl9_consensus=gl9_result.get("consensus", True),
        gl9_alignment=gl9_result.get("alignment", 1.0),
        gl9_deviation=gl9_result.get("deviation", 0.0),
        hebbian_faulty=hebbian_faulty,
        agreement=gl9_set == hebbian_set,
        exact_match=gl9_set == hebbian_set,
        gl9_only=list(gl9_set - hebbian_set),
        hebbian_only=list(hebbian_set - gl9_set),
        both_caught=list(gl9_set & hebbian_set),
    )


def generate_report(output, metrics, disagreement, fault_breakdown, healthy_results, healthy_gl9_fp, healthy_hebbian_fp):
    """Generate STUDY-58 markdown report."""
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STUDY-58-MYTHOS-CONSENSUS.md")

    lines = [
        "# STUDY 58: MythosTile Consensus — GL(9) vs Hebbian Fault Detection",
        "",
        f"**Date:** {output['timestamp']}",
        f"**Status:** Complete",
        "",
        "## Question",
        "",
        "When experts disagree, do GL(9) consensus checking and Hebbian anomaly detection identify the same faulty experts?",
        "",
        "## Experimental Design",
        "",
        "- **50 scenarios**: 25 healthy (all experts agree) + 25 faulty (1-2 experts anomalous)",
        "- **5-9 experts** per scenario",
        "- **5 fault types**: confidence_drop, content_scramble, domain_drift, confidence_spike, silent_expert",
        f"- **5 scenarios per fault type** (even coverage)",
        "",
        "## Key Findings",
        "",
        f"### Agreement Rate: {output['summary']['agreement_rate']:.1%}",
        "",
    ]

    if output['summary']['agreement_rate'] > 0.8:
        lines.append("✅ **HIGH AGREEMENT** — GL(9) and Hebbian detection largely agree.")
        lines.append("Either detector alone is sufficient for most scenarios.")
    elif output['summary']['agreement_rate'] > 0.5:
        lines.append("⚠️ **MODERATE AGREEMENT** — Detectors partially overlap but each misses some faults.")
        lines.append("**Recommendation: Use BOTH detectors** (union for recall, intersection for precision).")
    else:
        lines.append("❌ **LOW AGREEMENT** — Detectors are complementary, catching different fault types.")
        lines.append("**Must use both detectors.**")

    lines.extend([
        "",
        "## Per-Fault-Type Detection",
        "",
        "| Fault Type | GL(9) Catch | Hebbian Catch | Both | Neither |",
        "|------------|-------------|---------------|------|---------|",
    ])

    for ft, stats in sorted(fault_breakdown.items()):
        lines.append(f"| {ft} | {stats['gl9_caught']}/{stats['total']} | "
                     f"{stats['hebbian_caught']}/{stats['total']} | "
                     f"{stats['both_caught']}/{stats['total']} | "
                     f"{stats['neither_caught']}/{stats['total']} |")

    lines.extend([
        "",
        "## Detection Metrics",
        "",
        "| Detector | Precision | Recall | F1 | TP | FP | FN |",
        "|----------|-----------|--------|-----|----|----|----|",
        f"| GL(9) alone | {metrics['gl9']['precision']:.3f} | {metrics['gl9']['recall']:.3f} | {metrics['gl9']['f1']:.3f} | {metrics['gl9']['tp']} | {metrics['gl9']['fp']} | {metrics['gl9']['fn']} |",
        f"| Hebbian alone | {metrics['hebbian']['precision']:.3f} | {metrics['hebbian']['recall']:.3f} | {metrics['hebbian']['f1']:.3f} | {metrics['hebbian']['tp']} | {metrics['hebbian']['fp']} | {metrics['hebbian']['fn']} |",
        f"| **Combined (union)** | {metrics['combined_union']['precision']:.3f} | {metrics['combined_union']['recall']:.3f} | {metrics['combined_union']['f1']:.3f} | {metrics['combined_union']['tp']} | {metrics['combined_union']['fp']} | {metrics['combined_union']['fn']} |",
        f"| Combined (intersection) | {metrics['combined_intersection']['precision']:.3f} | {metrics['combined_intersection']['recall']:.3f} | {metrics['combined_intersection']['f1']:.3f} | {metrics['combined_intersection']['tp']} | {metrics['combined_intersection']['fp']} | {metrics['combined_intersection']['fn']} |",
        "",
        "## False Positive Analysis (Healthy Scenarios)",
        "",
        f"- GL(9) false positives: {healthy_gl9_fp}/{len(healthy_results)}",
        f"- Hebbian false positives: {healthy_hebbian_fp}/{len(healthy_results)}",
        "",
        "## Disagreement Analysis",
        "",
        f"- Total disagreements: {disagreement['total_disagreements']}",
        f"- Disagreement rate: {disagreement['disagreement_rate']:.1%}",
    ])

    if disagreement.get('gl9_only_fault_types'):
        lines.append(f"- GL(9)-only catches by fault type: {disagreement['gl9_only_fault_types']}")
        lines.append("  - **Interpretation:** GL(9) catches intent divergence — experts whose holonomy transform deviates from identity")
    if disagreement.get('hebbian_only_fault_types'):
        lines.append(f"- Hebbian-only catches by fault type: {disagreement['hebbian_only_fault_types']}")
        lines.append("  - **Interpretation:** Hebbian catches frequency anomalies — experts whose behavior patterns are statistically unusual")

    lines.extend([
        "",
        "## Detection Modes (Complementary Analysis)",
        "",
        "### GL(9) Mode: Intent Divergence Detection",
        "- Operates on 9D intent vectors (CI facets)",
        "- Detects when an expert's transform deviates from identity in holonomy cycles",
        "- Strength: catches subtle semantic drift, domain mismatch",
        "- Weakness: may miss obvious statistical anomalies",
        "",
        "### Hebbian Mode: Frequency/Pattern Anomaly Detection",
        "- Operates on observable statistics (confidence, content diversity, frequency)",
        "- Detects when an expert's behavior is statistically unusual",
        "- Strength: catches confidence drops, silent experts, content scrambles",
        "- Weakness: may miss subtle intent divergence",
        "",
        "## Recommendation",
        "",
    ])

    gl9_f1 = metrics['gl9']['f1']
    hebbian_f1 = metrics['hebbian']['f1']
    union_f1 = metrics['combined_union']['f1']

    if union_f1 > max(gl9_f1, hebbian_f1) + 0.05:
        lines.append("**Use BOTH detectors (union).** The combined detector significantly outperforms either alone.")
    elif max(gl9_f1, hebbian_f1) >= 0.9:
        lines.append(f"**Either detector is sufficient.** The best single detector ({'GL(9)' if gl9_f1 > hebbian_f1 else 'Hebbian'}) achieves F1={max(gl9_f1, hebbian_f1):.3f}.")
    else:
        lines.append("**Use BOTH detectors (union).** No single detector achieves sufficient F1 alone.")

    lines.extend([
        "",
        "---",
        f"*Study 58 — generated {output['timestamp']}*",
    ])

    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Report saved to {report_path}")


if __name__ == "__main__":
    main()
