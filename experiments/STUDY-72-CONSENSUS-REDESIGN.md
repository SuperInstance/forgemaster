# STUDY 72: MythosTile Consensus — Redesign of Study 58

**Date:** 2026-05-15
**Researcher:** Forgemaster ⚒️
**Redesign of:** Study 58 (2/7 rigor, flagged by Study 69 audit)
**Status:** Complete

---

## Motivation

Study 69 audited 15 studies (54–68) and rated Study 58 at **2/7 rigor** — the lowest score alongside Studies 63 and 64. Critical issues:

1. **N=5 per fault type** — severely underpowered
2. **No random seed** — not reproducible
3. **No baseline control** — no random detector to compare against
4. **No multiple-comparisons correction** — 5 fault types tested without correction
5. **Three fault types showed 0% detection for both methods** — possible bug, never investigated

This redesign addresses every flagged issue.

---

## Design Changes (Study 58 → Study 72)

| Issue | Study 58 | Study 72 |
|-------|----------|----------|
| Fleet sizes | V=9 only | V ∈ {5, 9, 15, 25} |
| Trials per condition | 1 | 50 |
| Control condition | None | Random detector (30% flag rate) |
| Multiple comparisons | No correction | Bonferroni (α = 0.0042 for 12 comparisons) |
| Effect sizes | None | Cohen's d for all comparisons |
| Reproducibility | No seed, no code | Seed=42, full simulation code included |
| Fault injection | Partially described | 5 fault types fully documented |

---

## Methodology

### Fleet Generation
- Each trial: generate a fleet of V experts
- 50% of trials are **faulty** (30% of experts are injected with faults)
- 50% of trials are **healthy** (all experts healthy — for false positive rate)
- Fault types: `confidence_drop`, `confidence_spike`, `content_scramble`, `domain_drift`, `subtle_bias`
- Domains: math, code, science, logic, language (randomly chosen per trial)

### Detectors

**GL(9) Consensus Detector:**
- Computes 9D intent vector for each expert (mirrors `mythos_tile.py`'s `_tile_to_intent`)
- Dimensions: source hash, domain hash, content hash, confidence, tag count, tag diversity, activation key, tier, lifecycle
- Flags experts whose mean pairwise cosine similarity falls below global_mean − 0.3

**Hebbian Flow Detector:**
- Flags experts whose confidence is >2σ from fleet mean
- Also flags experts in minority domains (count = 1)

**Dual Detector (GL9 + Hebbian):**
- Flags any expert flagged by EITHER detector (union)

**Random Baseline:**
- Each expert has 30% independent chance of being flagged

### Metrics
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1**: harmonic mean of precision and recall
- **FPR (False Positive Rate)**: measured on healthy-only scenarios

### Statistical Tests
- Paired t-tests (50 trials per condition, df = 49)
- Bonferroni correction: α = 0.05 / 12 = 0.0042
- Effect sizes: Cohen's d (small = 0.2, medium = 0.5, large = 0.8)

---

## Results

### Per-Fleet-Size Performance

| V | Detector | Precision | Recall | F1 | FPR (healthy) |
|---|----------|:---------:|:------:|:--:|:-------------:|
| 5 | GL(9) | 0.000 | 0.000 | 0.000 | 0.000 |
| 5 | Hebbian | 0.240 | 0.240 | 0.240 | 0.000 |
| 5 | Dual | 0.240 | 0.240 | 0.240 | 0.000 |
| 5 | Random | 0.158 | 0.260 | 0.188 | 0.252 |
| 9 | GL(9) | 0.000 | 0.000 | 0.000 | 0.000 |
| 9 | Hebbian | 0.640 | 0.440 | 0.507 | 0.016 |
| 9 | Dual | 0.640 | 0.440 | 0.507 | 0.016 |
| 9 | Random | 0.244 | 0.330 | 0.262 | 0.293 |
| 15 | GL(9) | 0.000 | 0.000 | 0.000 | 0.000 |
| 15 | Hebbian | 0.893 | 0.390 | 0.519 | 0.013 |
| 15 | Dual | 0.893 | 0.390 | 0.519 | 0.013 |
| 15 | Random | 0.251 | 0.290 | 0.258 | 0.296 |
| 25 | GL(9) | 0.000 | 0.000 | 0.000 | 0.000 |
| 25 | Hebbian | 0.975 | 0.351 | 0.504 | 0.003 |
| 25 | Dual | 0.975 | 0.351 | 0.504 | 0.003 |
| 25 | Random | 0.294 | 0.309 | 0.293 | 0.332 |

### Effect Sizes (Cohen's d)

| V | Dual vs GL9 | Dual vs Hebbian | GL9 vs Random | Dual vs Random |
|---|:-----------:|:---------------:|:-------------:|:--------------:|
| 5 | +0.79 | 0.00 | −0.79 | +0.13 |
| 9 | +1.77 | 0.00 | −1.44 | +0.72 |
| 15 | +2.97 | 0.00 | −1.81 | +1.16 |
| 25 | +4.61 | 0.00 | −2.79 | +1.39 |

### Significance Tests (with Bonferroni correction, α = 0.0042)

| V | Comparison | t | p | Significant? |
|---|-----------|:---:|:---:|:---:|
| 5 | Dual vs GL9 | 3.93 | 0.0003 | ✅ Yes |
| 5 | Hebbian vs Random | 0.68 | 0.503 | ❌ No |
| 9 | Dual vs GL9 | 8.84 | <0.0001 | ✅ Yes |
| 9 | Hebbian vs Random | 3.45 | 0.0012 | ✅ Yes |
| 15 | Dual vs GL9 | 14.83 | <0.0001 | ✅ Yes |
| 15 | Hebbian vs Random | 6.22 | <0.0001 | ✅ Yes |
| 25 | Dual vs GL9 | 23.06 | <0.0001 | ✅ Yes |
| 25 | Hebbian vs Random | 7.06 | <0.0001 | ✅ Yes |

---

## Hypothesis Verdicts

### H1: Dual detector (GL9+Hebbian) beats either alone
**✅ PARTIALLY SUPPORTED**

Dual beats GL(9) alone at every fleet size (Cohen's d: 0.79 to 4.61, all Bonferroni-significant). However, Dual = Hebbian exactly at every fleet size — GL(9) contributes **zero** additional detections. The "Dual" detector is just Hebbian in a trench coat.

**The architecture is sound in principle (union of detectors) but GL(9) provides no value in practice.**

### H2: Both detectors beat random baseline
**❌ MIXED RESULTS**

| Detector | V=5 | V=9 | V=15 | V=25 | Overall |
|----------|:---:|:---:|:----:|:----:|:-------:|
| GL(9) vs Random | **Worse** (d=−0.79) | **Worse** (d=−1.44) | **Worse** (d=−1.81) | **Worse** (d=−2.79) | ❌ GL9 worse than random |
| Hebbian vs Random | Not sig. (p=0.50) | ✅ Better (p=0.001) | ✅ Better (p<0.001) | ✅ Better (p<0.001) | ✅ At V≥9 |
| Dual vs Random | Not sig. (p=0.50) | ✅ Better (p=0.001) | ✅ Better (p<0.001) | ✅ Better (p<0.001) | ✅ At V≥9 |

**GL(9) is statistically WORSE than random** — it detects zero faults (precision = recall = 0) while random at least catches some. This is the most important negative finding.

**Hebbian beats random at V≥9** with large effect sizes (d = 0.72 to 1.39), but at V=5 the difference is not significant.

### H3: Performance degrades at larger fleet sizes
**❌ NOT SUPPORTED — OPPOSITE TREND**

Hebbian and Dual F1 *improves* from V=5 (F1=0.240) to V=9 (F1=0.507) and then plateaus. Precision increases dramatically (0.24 → 0.98) while recall decreases slightly (0.24 → 0.35).

**Why:** At larger fleet sizes, the confidence distribution has more samples, making z-score detection more reliable. The law of large numbers helps Hebbian — more experts means better statistics.

### H4: GL(9) maintains zero false positive rate across all sizes
**✅ SUPPORTED (trivially)**

GL(9) FPR = 0.000 at all fleet sizes. But this is because GL(9) detects nothing — zero true positives AND zero false positives. A detector that never fires has perfect specificity but zero sensitivity.

---

## Root Cause Analysis: Why GL(9) Fails

The GL(9) intent vector from `mythos_tile.py` uses **9 dimensions**:

| Dim | Source | Fault-sensitive? |
|-----|--------|:---:|
| C1: Boundary | MD5 hash of source name | ❌ No |
| C2: Pattern | MD5 hash of domain | ❌ Only for domain_drift |
| C3: Process | MD5 hash of content[:64] | ⚠️ Partially (content_scramble) |
| C4: Knowledge | Confidence value | ✅ Yes |
| C5: Social | Tag count / 5 | ❌ No |
| C6: Deep Structure | Unique tag count | ❌ No |
| C7: Instrument | Activation key presence | ❌ No |
| C8: Paradigm | Target tier | ❌ No |
| C9: Stakes | Lifecycle encoding | ❌ No |

**6 of 9 dimensions are deterministic hashes** that don't change with fault injection. The cosine similarity between two experts is dominated by these 6 identical dimensions, making faulty experts indistinguishable from healthy ones.

Only C4 (confidence) reliably detects faults, and the Hebbian detector already exploits it directly with z-scores. The GL(9) approach adds nothing because it dilutes the one useful signal (confidence) across 9 dimensions, 6 of which are noise.

---

## Key Findings

### 1. GL(9) Consensus Detection Is Ineffective (for this task)
The 9D intent vector approach from `mythos_tile.py` does not discriminate faulty from healthy experts. It's not just "not as good" — it's literally worse than random guessing. The hash-based dimensions provide no signal.

### 2. Hebbian Detection Works (at V≥9)
Simple z-score anomaly detection on confidence values achieves F1 = 0.50 with precision up to 0.98. This is genuinely useful for fleet fault detection.

### 3. Larger Fleets Are Easier to Monitor
Counter to H3, larger fleets provide better statistics, making anomaly detection more reliable. This is good news for fleet scaling.

### 4. The Dual Architecture Is Sound But Needs a Better GL(9)
The union-of-detectors design is correct in principle. The problem is the specific GL(9) implementation, not the architecture. If GL(9) used fault-relevant features (confidence deviation, response embedding distance, domain consistency checks) instead of hash-derived vectors, it could complement Hebbian.

### 5. Small Fleets (V=5) Are Hard to Monitor
At V=5, no detector significantly outperforms random. With only 5 experts, statistical anomaly detection doesn't have enough signal. This has operational implications: very small fleets need different monitoring strategies (perhaps rule-based rather than statistical).

---

## Comparison with Study 58

| Metric | Study 58 | Study 72 |
|--------|----------|----------|
| Fleet sizes tested | 1 (V=9) | 4 (5, 9, 15, 25) |
| Trials per condition | ~1 | 50 |
| Random baseline | None | ✅ Included |
| Bonferroni correction | No | ✅ α=0.0042 |
| Effect sizes | None | ✅ Cohen's d |
| GL(9) precision | "0.60" | **0.000** |
| GL(9) recall | "0.40" | **0.000** |

Study 58 reported GL(9) precision of 0.60 and recall of 0.40. Study 72 finds **0.000 for both**. The discrepancy is likely due to Study 58's underpowered design (N=5 per fault type) and lack of reproducibility (no seed, undocumented fault generation). With proper statistical controls, the GL(9) consensus finding disappears entirely.

---

## Rigor Scorecard (Self-Assessment)

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 50 trials per condition × 4 fleet sizes × 2 scenarios = 400 per detector |
| Controls | 1 | Random baseline, healthy scenarios for FPR |
| Blinding | 0 | Automated — no subjective judgment |
| Multiple comparisons | 1 | Bonferroni correction (α=0.0042 for 12 comparisons) |
| Reproducibility | 1 | Seed=42, full code in study72_run.py |
| Effect size | 1 | Cohen's d for all comparisons |
| Ecological validity | ⚠️ 0 | Still synthetic fault injection — needs live validation |
| **Total** | **5/7** | ✅ PASS (up from 2/7) |

---

## Recommendations

### Immediate
1. **Do not deploy GL(9) consensus detection** in its current form — it provides zero value
2. **Use Hebbian detection** for fleets of V≥9 — it's effective and low-overhead
3. **For V<9 fleets**, use rule-based monitoring (threshold on confidence, domain validation)

### GL(9) Redesign Needed
The intent vector needs fault-relevant features:
- Replace hash dimensions with **response embedding distances** (cosine sim of actual model outputs)
- Add **response length deviation** from fleet norm
- Add **domain consistency check** (binary: same domain or not)
- Keep confidence z-score (it's the only working signal)
- Add **temporal features** (how much did this expert's output change from last round?)

### Future Study
- Validate against **live fleet data** with real model failures
- Test **adaptive adversaries** that avoid confidence anomalies
- Investigate why recall plateaus at ~0.35 — are some fault types fundamentally undetectable?

---

*Study 72 · Forgemaster ⚒️ · PLATO Fleet Laboratory · 2026-05-15*
