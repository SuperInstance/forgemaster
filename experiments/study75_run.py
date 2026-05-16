#!/usr/bin/env python3
"""
Study 75: Metric Independence — Are three detection signals actually independent?

Simulates 1000 fault events across fleet of 9 agents:
- 200 honest (no fault)
- 200 structural faults (wrong patterns, holonomy violations)
- 200 coupling faults (wrong Hebbian coupling)
- 200 content faults (right structure, wrong answers)
- 200 combined faults (multiple types)

For each: run Hebbian, GL(9), and Content detectors.
Compute confusion matrices, pairwise correlations, Venn overlaps,
information gain, and conditional independence.
"""

import json
import math
import random
import hashlib
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

SEED = 42
random.seed(SEED)

N_AGENTS = 9
N_EVENTS = 1000  # 200 per category
AGENT_IDS = [f"agent-{i}" for i in range(N_AGENTS)]

# ---------------------------------------------------------------------------
# Fault event generation
# ---------------------------------------------------------------------------

class FaultType:
    HONEST = "honest"
    STRUCTURAL = "structural"      # holonomy violations, wrong patterns
    COUPLING = "coupling"           # wrong Hebbian coupling values
    CONTENT = "content"             # right structure, wrong answers
    COMBINED = "combined"           # multiple fault types

ALL_FAULT_TYPES = [FaultType.HONEST, FaultType.STRUCTURAL, FaultType.COUPLING,
                   FaultType.CONTENT, FaultType.COMBINED]
FAULT_ONLY_TYPES = [FaultType.STRUCTURAL, FaultType.COUPLING, FaultType.CONTENT, FaultType.COMBINED]


@dataclass
class FaultEvent:
    event_id: int
    fault_type: str                # one of FaultType.*
    target_agent: str              # the faulty agent (or random if honest)
    # Ground truth for each detector domain
    has_structural_fault: bool = False   # GL(9) should catch
    has_coupling_fault: bool = False     # Hebbian should catch
    has_content_fault: bool = False      # Content should catch
    # Simulated detector inputs
    confidence: float = 0.85            # agent confidence (Hebbian uses this)
    intent_vector: List[float] = field(default_factory=list)  # GL(9) 9D vector
    answer: str = ""                    # agent's answer (content uses this)
    correct_answer: str = ""            # ground truth answer
    coupling_weight: float = 0.5        # Hebbian coupling weight


def generate_intent_vector(healthy=True):
    """Generate a 9D intent vector (mirrors mythos_tile.py structure)."""
    if healthy:
        return [random.gauss(0.5, 0.1) for _ in range(9)]
    else:
        # Faulty: some dimensions shifted
        v = [random.gauss(0.5, 0.1) for _ in range(9)]
        # Corrupt 3-5 dimensions
        for i in random.sample(range(9), k=random.randint(3, 5)):
            v[i] += random.gauss(2.0, 0.5)
        return v


def generate_events(n_per_type=200) -> List[FaultEvent]:
    """Generate n_per_type events for each fault category."""
    events = []
    eid = 0

    # --- 200 Honest ---
    for _ in range(n_per_type):
        agent = random.choice(AGENT_IDS)
        correct = str(random.randint(10, 99))
        events.append(FaultEvent(
            event_id=eid,
            fault_type=FaultType.HONEST,
            target_agent=agent,
            has_structural_fault=False,
            has_coupling_fault=False,
            has_content_fault=False,
            confidence=random.gauss(0.85, 0.05),
            intent_vector=generate_intent_vector(healthy=True),
            answer=correct,
            correct_answer=correct,
            coupling_weight=random.gauss(0.5, 0.05),
        ))
        eid += 1

    # --- 200 Structural faults ---
    for _ in range(n_per_type):
        agent = random.choice(AGENT_IDS)
        correct = str(random.randint(10, 99))
        events.append(FaultEvent(
            event_id=eid,
            fault_type=FaultType.STRUCTURAL,
            target_agent=agent,
            has_structural_fault=True,
            has_coupling_fault=False,
            has_content_fault=False,
            confidence=random.gauss(0.85, 0.05),  # confidence looks normal
            intent_vector=generate_intent_vector(healthy=False),  # anomalous intent
            answer=correct,  # answer is still correct
            correct_answer=correct,
            coupling_weight=random.gauss(0.5, 0.05),  # coupling looks normal
        ))
        eid += 1

    # --- 200 Coupling faults ---
    for _ in range(n_per_type):
        agent = random.choice(AGENT_IDS)
        correct = str(random.randint(10, 99))
        events.append(FaultEvent(
            event_id=eid,
            fault_type=FaultType.COUPLING,
            target_agent=agent,
            has_structural_fault=False,
            has_coupling_fault=True,
            has_content_fault=False,
            confidence=random.gauss(0.85, 0.05),  # normal
            intent_vector=generate_intent_vector(healthy=True),  # normal
            answer=correct,  # correct answer
            correct_answer=correct,
            coupling_weight=random.gauss(2.5, 0.5),  # anomalous coupling (dominating)
        ))
        eid += 1

    # --- 200 Content faults ---
    for _ in range(n_per_type):
        agent = random.choice(AGENT_IDS)
        correct = str(random.randint(10, 99))
        # Wrong answer but structurally normal
        wrong = str(random.randint(10, 99))
        while wrong == correct:
            wrong = str(random.randint(10, 99))
        events.append(FaultEvent(
            event_id=eid,
            fault_type=FaultType.CONTENT,
            target_agent=agent,
            has_structural_fault=False,
            has_coupling_fault=False,
            has_content_fault=True,
            confidence=random.gauss(0.85, 0.05),  # normal confidence
            intent_vector=generate_intent_vector(healthy=True),  # normal intent
            answer=wrong,  # wrong answer
            correct_answer=correct,
            coupling_weight=random.gauss(0.5, 0.05),  # normal coupling
        ))
        eid += 1

    # --- 200 Combined faults ---
    for _ in range(n_per_type):
        agent = random.choice(AGENT_IDS)
        correct = str(random.randint(10, 99))
        wrong = str(random.randint(10, 99))
        while wrong == correct:
            wrong = str(random.randint(10, 99))

        # Pick 2-3 fault types to combine
        n_faults = random.choice([2, 3])
        fault_set = random.sample(["structural", "coupling", "content"], k=n_faults)

        has_s = "structural" in fault_set
        has_c = "coupling" in fault_set
        has_ct = "content" in fault_set

        events.append(FaultEvent(
            event_id=eid,
            fault_type=FaultType.COMBINED,
            target_agent=agent,
            has_structural_fault=has_s,
            has_coupling_fault=has_c,
            has_content_fault=has_ct,
            confidence=random.gauss(0.85, 0.05),
            intent_vector=generate_intent_vector(healthy=not has_s),
            answer=wrong if has_ct else correct,
            correct_answer=correct,
            coupling_weight=random.gauss(2.5, 0.5) if has_c else random.gauss(0.5, 0.05),
        ))
        eid += 1

    random.shuffle(events)
    return events


# ---------------------------------------------------------------------------
# Detectors (simplified models based on real implementations)
# ---------------------------------------------------------------------------

class HebbianDetector:
    """
    Detects coupling anomalies via z-score of coupling weights.
    
    Based on Study 72: flags agents whose coupling_weight > mean + 2*std.
    Also detects confidence anomalies.
    """
    def __init__(self, fleet_size=9):
        self.fleet_size = fleet_size

    def detect(self, event: FaultEvent, all_events: List[FaultEvent]) -> bool:
        """
        Returns True if Hebbian detector flags this event.
        Uses coupling_weight z-score and confidence z-score.
        """
        # Get fleet statistics from same batch
        coupling_weights = [e.coupling_weight for e in all_events[:self.fleet_size]]
        if len(coupling_weights) < 3:
            return False

        mean_cw = sum(coupling_weights) / len(coupling_weights)
        std_cw = (sum((w - mean_cw)**2 for w in coupling_weights) / len(coupling_weights)) ** 0.5
        if std_cw < 1e-10:
            std_cw = 0.01

        z_coupling = abs(event.coupling_weight - mean_cw) / std_cw

        # Also check confidence
        confidences = [e.confidence for e in all_events[:self.fleet_size]]
        mean_conf = sum(confidences) / len(confidences)
        std_conf = (sum((c - mean_conf)**2 for c in confidences) / len(confidences)) ** 0.5
        if std_conf < 1e-10:
            std_conf = 0.01

        z_conf = abs(event.confidence - mean_conf) / std_conf

        # Flag if either z-score > 2
        return z_coupling > 2.0 or z_conf > 2.0


class GL9Detector:
    """
    GL(9) consensus detector based on 9D intent vector cosine similarity.
    
    Based on Study 72 findings: 6/9 dimensions are hash-derived and don't
    change with faults. Only C4 (confidence-equivalent) provides signal.
    Effectively: flags if confidence-like dimension deviates AND other
    dimensions don't mask it (which they usually do).
    """
    def __init__(self, fleet_size=9, threshold=0.3):
        self.fleet_size = fleet_size
        self.threshold = threshold

    def _cosine_sim(self, v1, v2):
        dot = sum(a*b for a, b in zip(v1, v2))
        n1 = sum(a*a for a in v1)**0.5
        n2 = sum(a*a for a in v2)**0.5
        if n1 < 1e-12 or n2 < 1e-12:
            return 0.0
        return dot / (n1 * n2)

    def detect(self, event: FaultEvent, all_events: List[FaultEvent]) -> bool:
        """
        Returns True if GL(9) flags this event.
        
        Per Study 72: GL(9) barely detects anything because hash dimensions
        dominate cosine similarity. It detects ~0% of faults in practice.
        """
        # Compute mean pairwise cosine similarity
        batch = all_events[:self.fleet_size]
        if len(batch) < 3:
            return False

        # Mean vector
        vectors = [e.intent_vector for e in batch]
        mean_vec = [sum(v[i] for v in vectors) / len(vectors) for i in range(9)]

        # Compute similarity of target to fleet mean
        sim = self._cosine_sim(event.intent_vector, mean_vec)

        # Fleet global mean similarity
        sims = [self._cosine_sim(v, mean_vec) for v in vectors]
        global_mean_sim = sum(sims) / len(sims)

        # Flag if below global_mean - threshold
        # But Study 72 showed this almost never fires because hash dims dominate
        # Simulate: even with corrupted intent, cosine sim stays high
        # because 6/9 dims are shared
        return sim < (global_mean_sim - self.threshold)


class ContentDetector:
    """
    Content-level verifier based on content_verifier.py.
    
    Detects: wrong answers (answer != correct_answer).
    Uses semantic similarity threshold.
    """
    def __init__(self, similarity_threshold=0.7):
        self.threshold = similarity_threshold

    def detect(self, event: FaultEvent) -> bool:
        """
        Returns True if content verifier flags this event.
        
        Simple: answer doesn't match correct_answer.
        In real system, this would use spot-checks, canaries, cross-validation.
        """
        # Normalize and compare
        ans = event.answer.strip().lower()
        correct = event.correct_answer.strip().lower()
        if ans == correct:
            return False
        # Numeric comparison
        try:
            a_num = float(ans)
            c_num = float(correct)
            if c_num != 0:
                rel_error = abs(a_num - c_num) / abs(c_num)
                return rel_error > self.threshold
            else:
                return abs(a_num) > 0.01
        except ValueError:
            # String comparison
            return ans != correct


# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------

def run_simulation():
    """Run the full 1000-event simulation."""
    print("Generating 1000 fault events (200 per category)...")
    events = generate_events(200)

    # Create detectors
    hebbian = HebbianDetector(N_AGENTS)
    gl9 = GL9Detector(N_AGENTS)
    content = ContentDetector()

    # Results storage
    results = {
        "events": [],
        "confusion_matrices": {},
        "pairwise_correlations": {},
        "venn_counts": {},
        "information_gain": {},
        "conditional_independence": {},
        "hypothesis_results": {},
    }

    # Process events in batches of N_AGENTS (simulating fleet)
    hebbian_flags = []
    gl9_flags = []
    content_flags = []
    ground_truth_any_fault = []
    ground_truth_structural = []
    ground_truth_coupling = []
    ground_truth_content = []

    print("Running detectors on all events...")
    for i in range(0, len(events), N_AGENTS):
        batch = events[i:i+N_AGENTS]
        for event in batch:
            h_flag = hebbian.detect(event, batch)
            g_flag = gl9.detect(event, batch)
            c_flag = content.detect(event)

            hebbian_flags.append(h_flag)
            gl9_flags.append(g_flag)
            content_flags.append(c_flag)

            is_fault = event.fault_type != FaultType.HONEST
            ground_truth_any_fault.append(is_fault)
            ground_truth_structural.append(event.has_structural_fault)
            ground_truth_coupling.append(event.has_coupling_fault)
            ground_truth_content.append(event.has_content_fault)

            results["events"].append({
                "event_id": event.event_id,
                "fault_type": event.fault_type,
                "has_structural": event.has_structural_fault,
                "has_coupling": event.has_coupling_fault,
                "has_content": event.has_content_fault,
                "hebbian_flag": h_flag,
                "gl9_flag": g_flag,
                "content_flag": c_flag,
                "n_detectors": sum([h_flag, g_flag, c_flag]),
            })

    n = len(events)
    print(f"Processed {n} events.")

    # -----------------------------------------------------------------------
    # 1. Confusion matrices (per detector vs "any fault")
    # -----------------------------------------------------------------------
    print("\n=== Confusion Matrices ===")
    for name, flags in [("hebbian", hebbian_flags), ("gl9", gl9_flags), ("content", content_flags)]:
        tp = sum(1 for f, g in zip(flags, ground_truth_any_fault) if f and g)
        fp = sum(1 for f, g in zip(flags, ground_truth_any_fault) if f and not g)
        fn = sum(1 for f, g in zip(flags, ground_truth_any_fault) if not f and g)
        tn = sum(1 for f, g in zip(flags, ground_truth_any_fault) if not f and not g)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / n

        cm = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round(accuracy, 4),
        }
        results["confusion_matrices"][name] = cm
        print(f"  {name}: P={precision:.3f} R={recall:.3f} F1={f1:.3f} (TP={tp} FP={fp} FN={fn} TN={tn})")

    # -----------------------------------------------------------------------
    # 2. Pairwise correlation (Phi coefficient for binary variables)
    # -----------------------------------------------------------------------
    print("\n=== Pairwise Correlations (Phi coefficient) ===")
    detector_pairs = [
        ("hebbian", "gl9", hebbian_flags, gl9_flags),
        ("hebbian", "content", hebbian_flags, content_flags),
        ("gl9", "content", gl9_flags, content_flags),
    ]

    for name_a, name_b, flags_a, flags_b in detector_pairs:
        # Phi coefficient: (ad - bc) / sqrt((a+b)(c+d)(a+c)(b+d))
        a = sum(1 for fa, fb in zip(flags_a, flags_b) if fa and fb)        # both positive
        b = sum(1 for fa, fb in zip(flags_a, flags_b) if fa and not fb)    # A only
        c = sum(1 for fa, fb in zip(flags_a, flags_b) if not fa and fb)    # B only
        d = sum(1 for fa, fb in zip(flags_a, flags_b) if not fa and not fb)  # both negative

        denom = ((a+b) * (c+d) * (a+c) * (b+d)) ** 0.5
        phi = (a*d - b*c) / denom if denom > 0 else 0.0

        # Also compute Jaccard index for positive cases
        jaccard = a / (a + b + c) if (a + b + c) > 0 else 0.0

        corr = {
            "phi": round(phi, 4),
            "jaccard": round(jaccard, 4),
            "both_positive": a,
            "a_only": b,
            "b_only": c,
            "both_negative": d,
        }
        results["pairwise_correlations"][f"{name_a}_vs_{name_b}"] = corr
        print(f"  {name_a} vs {name_b}: Phi={phi:.4f}, Jaccard={jaccard:.4f}, overlap={a}")

    # -----------------------------------------------------------------------
    # 3. Venn diagram: faults detected by exactly 0, 1, 2, or 3 detectors
    # -----------------------------------------------------------------------
    print("\n=== Venn Diagram (fault events only) ===")
    venn = {"0": 0, "1": 0, "2": 0, "3": 0}
    venn_detail = {
        "only_hebbian": 0, "only_gl9": 0, "only_content": 0,
        "hebbian_gl9": 0, "hebbian_content": 0, "gl9_content": 0,
        "all_three": 0, "none": 0,
    }

    # Only count fault events (not honest)
    for i, event in enumerate(events):
        if event.fault_type == FaultType.HONEST:
            continue

        h, g, c = hebbian_flags[i], gl9_flags[i], content_flags[i]
        count = sum([h, g, c])
        venn[str(count)] += 1

        if count == 0:
            venn_detail["none"] += 1
        elif count == 1:
            if h: venn_detail["only_hebbian"] += 1
            if g: venn_detail["only_gl9"] += 1
            if c: venn_detail["only_content"] += 1
        elif count == 2:
            if h and g: venn_detail["hebbian_gl9"] += 1
            if h and c: venn_detail["hebbian_content"] += 1
            if g and c: venn_detail["gl9_content"] += 1
        else:
            venn_detail["all_three"] += 1

    total_faults = sum(venn.values())
    catch_rate = (total_faults - venn["0"]) / total_faults if total_faults > 0 else 0

    results["venn_counts"] = {
        "total_fault_events": total_faults,
        "caught_by_0": venn["0"],
        "caught_by_1": venn["1"],
        "caught_by_2": venn["2"],
        "caught_by_3": venn["3"],
        "catch_rate_any": round(catch_rate, 4),
        "detail": venn_detail,
    }
    print(f"  Total faults: {total_faults}")
    print(f"  Caught by 0 detectors: {venn['0']} ({venn['0']/total_faults*100:.1f}%)")
    print(f"  Caught by 1 detector:  {venn['1']} ({venn['1']/total_faults*100:.1f}%)")
    print(f"  Caught by 2 detectors: {venn['2']} ({venn['2']/total_faults*100:.1f}%)")
    print(f"  Caught by 3 detectors: {venn['3']} ({venn['3']/total_faults*100:.1f}%)")
    print(f"  Catch rate (any detector): {catch_rate*100:.1f}%")
    print(f"  Detail: {venn_detail}")

    # -----------------------------------------------------------------------
    # 4. Information gain: does adding a 2nd/3rd detector help?
    # -----------------------------------------------------------------------
    print("\n=== Information Gain ===")

    # Best single detector
    single_recalls = {}
    for name, flags in [("hebbian", hebbian_flags), ("gl9", gl9_flags), ("content", content_flags)]:
        tp = sum(1 for f, g in zip(flags, ground_truth_any_fault) if f and g)
        fn = sum(1 for f, g in zip(flags, ground_truth_any_fault) if not f and g)
        single_recalls[name] = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # Pairwise combinations
    combo_recalls = {}
    for name_a, flags_a, name_b, flags_b in [
        ("hebbian+gl9", hebbian_flags, "gl9", gl9_flags),
        ("hebbian+content", hebbian_flags, "content", content_flags),
        ("gl9+content", gl9_flags, "content", content_flags),
    ]:
        combined = [a or b for a, b in zip(flags_a, flags_b)]
        tp = sum(1 for f, g in zip(combined, ground_truth_any_fault) if f and g)
        fn = sum(1 for f, g in zip(combined, ground_truth_any_fault) if not f and g)
        combo_recalls[f"{name_a}"] = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # All three
    all_three = [h or g or c for h, g, c in zip(hebbian_flags, gl9_flags, content_flags)]
    tp = sum(1 for f, g in zip(all_three, ground_truth_any_fault) if f and g)
    fn = sum(1 for f, g in zip(all_three, ground_truth_any_fault) if not f and g)
    triple_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    best_single = max(single_recalls, key=single_recalls.get)
    best_pair = max(combo_recalls, key=combo_recalls.get)

    info_gain = {
        "single_detector_recall": {k: round(v, 4) for k, v in single_recalls.items()},
        "pair_recall": {k: round(v, 4) for k, v in combo_recalls.items()},
        "triple_recall": round(triple_recall, 4),
        "best_single": best_single,
        "best_single_recall": round(single_recalls[best_single], 4),
        "best_pair": best_pair,
        "best_pair_recall": round(combo_recalls[best_pair], 4),
        "gain_pair_over_best_single": round(combo_recalls[best_pair] - single_recalls[best_single], 4),
        "gain_triple_over_best_single": round(triple_recall - single_recalls[best_single], 4),
        "gain_triple_over_best_pair": round(triple_recall - combo_recalls[best_pair], 4),
    }
    results["information_gain"] = info_gain
    print(f"  Best single: {best_single} (recall={single_recalls[best_single]:.3f})")
    print(f"  Best pair: {best_pair} (recall={combo_recalls[best_pair]:.3f})")
    print(f"  Triple recall: {triple_recall:.3f}")
    print(f"  Gain (pair over best single): {combo_recalls[best_pair] - single_recalls[best_single]:.3f}")
    print(f"  Gain (triple over best single): {triple_recall - single_recalls[best_single]:.3f}")

    # -----------------------------------------------------------------------
    # 5. Conditional independence: are detectors independent given fault type?
    # -----------------------------------------------------------------------
    print("\n=== Conditional Independence ===")

    cond_indep = {}
    for fault_type in ALL_FAULT_TYPES:
        # Get indices for this fault type
        indices = [i for i, e in enumerate(events) if e.fault_type == fault_type]
        if len(indices) < 10:
            continue

        ft_h = [hebbian_flags[i] for i in indices]
        ft_g = [gl9_flags[i] for i in indices]
        ft_c = [content_flags[i] for i in indices]

        # Pairwise conditional phi
        ft_results = {}
        for pair_name, fa, fb in [
            ("hebbian_gl9", ft_h, ft_g),
            ("hebbian_content", ft_h, ft_c),
            ("gl9_content", ft_g, ft_c),
        ]:
            a = sum(1 for x, y in zip(fa, fb) if x and y)
            b = sum(1 for x, y in zip(fa, fb) if x and not y)
            c = sum(1 for x, y in zip(fa, fb) if not x and y)
            d = sum(1 for x, y in zip(fa, fb) if not x and not y)
            denom = ((a+b) * (c+d) * (a+c) * (b+d)) ** 0.5
            phi = (a*d - b*c) / denom if denom > 0 else 0.0

            ft_results[pair_name] = {
                "phi": round(phi, 4),
                "both_pos": a,
                "a_only": b,
                "b_only": c,
                "both_neg": d,
                "independent": abs(phi) < 0.3,
            }

        cond_indep[fault_type] = ft_results
        print(f"  {fault_type}:")
        for pair_name, pr in ft_results.items():
            indep = "INDEPENDENT" if pr["independent"] else "CORRELATED"
            print(f"    {pair_name}: phi={pr['phi']:.4f} ({indep})")

    results["conditional_independence"] = cond_indep

    # -----------------------------------------------------------------------
    # 6. Per-fault-type detection rates
    # -----------------------------------------------------------------------
    print("\n=== Per-Fault-Type Detection Rates ===")
    per_type = {}
    for fault_type in ALL_FAULT_TYPES:
        indices = [i for i, e in enumerate(events) if e.fault_type == fault_type]
        n_ft = len(indices)

        h_rate = sum(hebbian_flags[i] for i in indices) / n_ft
        g_rate = sum(gl9_flags[i] for i in indices) / n_ft
        c_rate = sum(content_flags[i] for i in indices) / n_ft
        any_rate = sum(hebbian_flags[i] or gl9_flags[i] or content_flags[i] for i in indices) / n_ft

        per_type[fault_type] = {
            "n": n_ft,
            "hebbian_rate": round(h_rate, 4),
            "gl9_rate": round(g_rate, 4),
            "content_rate": round(c_rate, 4),
            "any_rate": round(any_rate, 4),
        }
        print(f"  {fault_type} (n={n_ft}): H={h_rate:.3f} GL9={g_rate:.3f} C={c_rate:.3f} Any={any_rate:.3f}")

    results["per_fault_type"] = per_type

    # -----------------------------------------------------------------------
    # Hypothesis testing
    # -----------------------------------------------------------------------
    print("\n=== Hypothesis Testing ===")

    # H1: Hebbian and content are independent
    h1_pair = results["pairwise_correlations"]["hebbian_vs_content"]
    h1_phi = abs(h1_pair["phi"])
    h1_verdict = "SUPPORTED" if h1_phi < 0.3 else "REJECTED"

    # H2: GL(9) adds no information beyond Hebbian
    h2_gain = info_gain["gain_pair_over_best_single"] if "hebbian+gl9" == best_pair else (
        combo_recalls.get("hebbian+gl9", 0) - single_recalls.get("hebbian", 0))
    h2_pair_recall = combo_recalls.get("hebbian+gl9", 0)
    h2_hebbian_recall = single_recalls.get("hebbian", 0)
    h2_verdict = "SUPPORTED" if abs(h2_pair_recall - h2_hebbian_recall) < 0.02 else "REJECTED"

    # H3: Triple system catches >95% of all faults
    h3_verdict = "SUPPORTED" if catch_rate > 0.95 else "REJECTED"

    # H4: Content faults are ONLY caught by content verifier
    content_fault_indices = [i for i, e in enumerate(events) if e.has_content_fault and not e.has_structural_fault and not e.has_coupling_fault]
    if content_fault_indices:
        content_only_h = sum(hebbian_flags[i] for i in content_fault_indices)
        content_only_g = sum(gl9_flags[i] for i in content_fault_indices)
        content_only_c = sum(content_flags[i] for i in content_fault_indices)
        # H4: structural detectors should catch 0 pure content faults
        h4_verdict = "SUPPORTED" if content_only_h == 0 and content_only_g == 0 else "REJECTED"
        h4_detail = {
            "pure_content_faults": len(content_fault_indices),
            "hebbian_false_detections": content_only_h,
            "gl9_false_detections": content_only_g,
            "content_detections": content_only_c,
        }
    else:
        h4_verdict = "INSUFFICIENT DATA"
        h4_detail = {"pure_content_faults": 0}

    hypotheses = {
        "H1_hebbian_content_independent": {
            "hypothesis": "Hebbian and content are independent (orthogonal detection domains)",
            "phi": h1_phi,
            "threshold": 0.3,
            "verdict": h1_verdict,
        },
        "H2_gl9_redundant": {
            "hypothesis": "GL(9) adds no information beyond Hebbian",
            "hebbian_recall": round(h2_hebbian_recall, 4),
            "hebbian_plus_gl9_recall": round(h2_pair_recall, 4),
            "delta": round(h2_pair_recall - h2_hebbian_recall, 4),
            "verdict": h2_verdict,
        },
        "H3_triple_catches_95": {
            "hypothesis": "Triple system catches >95% of all faults",
            "catch_rate": round(catch_rate, 4),
            "target": 0.95,
            "verdict": h3_verdict,
        },
        "H4_content_only_by_content": {
            "hypothesis": "Content faults are ONLY caught by content verifier",
            "detail": h4_detail,
            "verdict": h4_verdict,
        },
    }
    results["hypothesis_results"] = hypotheses

    print(f"  H1 (H ⊥ C): phi={h1_phi:.4f} → {h1_verdict}")
    print(f"  H2 (GL9 redundant): H_recall={h2_hebbian_recall:.3f}, H+G={h2_pair_recall:.3f}, delta={h2_pair_recall-h2_hebbian_recall:.3f} → {h2_verdict}")
    print(f"  H3 (>95% catch): rate={catch_rate:.3f} → {h3_verdict}")
    print(f"  H4 (content blind spot): → {h4_verdict}")
    if h4_detail.get("pure_content_faults", 0) > 0:
        print(f"    Pure content faults: {h4_detail['pure_content_faults']}, "
              f"H false positives: {h4_detail['hebbian_false_detections']}, "
              f"GL9 false positives: {h4_detail['gl9_false_detections']}, "
              f"C detections: {h4_detail['content_detections']}")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = run_simulation()

    # Save JSON
    out_json = os.path.join(os.path.dirname(__file__), "study75_results.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {out_json}")
