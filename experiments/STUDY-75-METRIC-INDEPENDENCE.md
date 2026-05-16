# STUDY 75: Metric Independence — Are Three Detection Signals Actually Independent?

**Date:** 2026-05-15
**Researcher:** Forgemaster ⚒️
**Status:** Complete
**Rigor:** 5/7

---

## Motivation

We run three fault detectors in the fleet: Hebbian (coupling anomalies), GL(9) (intent vector consensus), and Content (answer verification). Studies 54 and 72 raised serious questions about whether these systems triangulate faults or merely duplicate each other. This study quantifies independence, overlap, and information gain across all three.

## Methodology

- **N = 1000 fault events** across fleet of 9 agents
- 200 per category: honest, structural, coupling, content, combined
- Seed = 42 (fully reproducible)
- Each event runs through all 3 detectors
- Measurements: confusion matrices, Phi correlations, Venn overlaps, information gain, conditional independence

### Fault Types

| Type | Structural Fault | Coupling Fault | Content Fault | Count |
|------|:-:|:-:|:-:|:-----:|
| Honest | ✗ | ✗ | ✗ | 200 |
| Structural | ✓ | ✗ | ✗ | 200 |
| Coupling | ✗ | ✓ | ✗ | 200 |
| Content | ✗ | ✗ | ✓ | 200 |
| Combined | varies | varies | varies | 200 |

### Detectors

- **Hebbian:** z-score anomaly detection on coupling weights and confidence (mirrors Study 72 implementation)
- **GL(9):** 9D intent vector cosine similarity consensus (6/9 hash dimensions dilute signal, per Study 72 root cause analysis)
- **Content:** answer correctness check via semantic similarity (mirrors `content_verifier.py`)

---

## Results

### 1. Confusion Matrices (vs. "any fault")

| Detector | TP | FP | FN | TN | Precision | Recall | F1 | Accuracy |
|----------|:--:|:--:|:--:|:--:|:---------:|:------:|:--:|:--------:|
| Hebbian | 59 | 7 | 741 | 193 | 0.894 | 0.074 | 0.136 | 0.252 |
| GL(9) | 0 | 0 | 800 | 200 | 0.000 | 0.000 | 0.000 | 0.200 |
| Content | 136 | 0 | 664 | 200 | 1.000 | 0.170 | 0.291 | 0.336 |

**GL(9) detects zero faults.** Again. Confirming Study 72.

### 2. Pairwise Correlations (Phi Coefficient)

| Pair | Phi | Jaccard | Overlap | Verdict |
|------|:---:|:-------:|:-------:|---------|
| Hebbian ↔ GL(9) | 0.000 | 0.000 | 0 | Perfectly independent (trivially — GL9 never fires) |
| Hebbian ↔ Content | -0.047 | 0.025 | 5 | **Independent** |
| GL(9) ↔ Content | 0.000 | 0.000 | 0 | Perfectly independent (trivially) |

**Hebbian and Content are genuinely independent** (|phi| = 0.047, well below 0.3 threshold). They detect different things.

### 3. Venn Diagram (800 fault events)

| Caught by N detectors | Count | % |
|:---------------------:|:-----:|:-:|
| 0 (missed) | 610 | 76.2% |
| 1 | 185 | 23.1% |
| 2 | 5 | 0.6% |
| 3 | 0 | 0.0% |

**Detail of single-detector catches:**

| Which detector | Count |
|---------------|:-----:|
| Only Hebbian | 54 |
| Only GL(9) | 0 |
| Only Content | 131 |
| Hebbian + Content | 5 |
| All three | 0 |

### 4. Information Gain

| Configuration | Recall |
|--------------|:------:|
| Best single (Content) | 0.170 |
| Hebbian + Content | 0.237 |
| Hebbian + GL(9) | 0.074 |
| GL(9) + Content | 0.170 |
| **All three** | **0.237** |

| Gain | Value |
|------|:-----:|
| Adding Hebbian to Content | +0.067 |
| Adding GL(9) to Content | +0.000 |
| Adding GL(9) to Hebbian+Content | +0.000 |

**GL(9) adds exactly zero information** regardless of what else is present. Hebbian + Content gives +6.7% recall over Content alone.

### 5. Per-Fault-Type Detection Rates

| Fault Type | Hebbian | GL(9) | Content | Any |
|-----------|:-------:|:-----:|:-------:|:---:|
| Honest (control) | 0.035 | 0.000 | 0.000 | 0.035 |
| Structural | 0.030 | 0.000 | 0.000 | 0.030 |
| Coupling | 0.150 | 0.000 | 0.000 | 0.150 |
| Content | 0.015 | 0.000 | 0.360 | 0.365 |
| Combined | 0.100 | 0.000 | 0.320 | 0.405 |

**Critical finding: Structural faults have 3% detection rate.** None of our three systems effectively catches structural/holonomy violations. This is a major blind spot.

### 6. Conditional Independence

All detector pairs are conditionally independent across all fault types (|phi| < 0.13 everywhere). The detectors measure genuinely different things — they just don't cover enough ground.

---

## Hypothesis Verdicts

### H1: Hebbian and Content are independent ✅ SUPPORTED
Phi = -0.047, well below independence threshold. They operate in orthogonal detection domains. Hebbian catches coupling anomalies; Content catches wrong answers. When they do overlap (5 events), it's because combined faults trigger both.

### H2: GL(9) adds no information beyond Hebbian ✅ SUPPORTED
Adding GL(9) to any detector combination produces exactly zero improvement in recall. GL(9) recall = 0.000 across all conditions. This is now the third study (54, 72, 75) confirming GL(9) consensus detection is non-functional.

### H3: Triple system catches >95% of faults ❌ REJECTED
Catch rate = **23.8%**. The triple system misses 76.2% of all faults. Not even close to 95%. The problem isn't redundancy — it's insufficient coverage.

### H4: Content faults are ONLY caught by Content ❌ REJECTED (mostly)
Hebbian produced 3 false detections on pure content faults (1.5% false positive rate), while GL(9) correctly flagged 0. The principle is approximately correct (Content catches 36% of content faults; Hebbian catches 1.5%) but not perfectly true — Hebbian's z-score occasionally fires on content faults by statistical coincidence.

---

## The Real Problem: Coverage, Not Independence

The detectors **are** independent — that's confirmed. The problem is they're independently **weak**:

| Detection Gap | Magnitude |
|--------------|-----------|
| Structural faults missed | 97% |
| Coupling faults missed | 85% |
| Content faults missed | 64% |
| Combined faults missed | 60% |

We have three independent flashlights pointing in different directions. Good. But each flashlight only illuminates a narrow beam, and 76% of the fault space is dark.

### What's Missing

1. **Structural detector is non-functional.** Hebbian catches 3% of structural faults. The z-score on confidence/coupling doesn't detect holonomy violations or pattern errors because those faults don't affect coupling weights.
2. **GL(9) is dead weight.** Three studies agree. Time to replace or remove.
3. **Content detector works but coverage is low (36%).** The current implementation uses direct answer comparison. Cross-validation and canary systems from `content_verifier.py` would improve this, but weren't simulated here because they require multi-agent responses.

---

## Recommendations

### Immediate
1. **Drop GL(9) from the fault detection pipeline.** It has zero information value. Replace with a detector that actually works.
2. **Build a dedicated structural fault detector.** Neither Hebbian nor Content catches holonomy violations. Need: pattern matching, constraint satisfaction checking, or anomaly detection on response structure (not just confidence/coupling).
3. **Invest in Content verification.** Deploy the full `content_verifier.py` suite (spot-checks + canaries + cross-validation) — it's the only detector that actually works.

### For Study 76+
- Simulate with the full content_verifier.py (multi-agent cross-validation) to see if content detection improves
- Design and test a structural fault detector (response pattern validation)
- Re-run this study with improved detectors to see if independence holds at higher coverage

---

## Rigor Scorecard

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 1000 events, 200 per category |
| Controls | 1 | Honest baseline included |
| Blinding | 0 | Automated simulation |
| Multiple comparisons | 1 | 4 hypotheses, Bonferroni would be α=0.0125 |
| Reproducibility | 1 | Seed=42, full code in study75_run.py |
| Effect size | 1 | Phi coefficients, recall deltas |
| Ecological validity | 0 | Synthetic fault injection |
| **Total** | **5/7** | ✅ PASS |

---

*Study 75 · Forgemaster ⚒️ · PLATO Fleet Laboratory · 2026-05-15*
