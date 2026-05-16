# STUDY 69: Wheel Audit — Experimental Rigor Review

**Date:** 2026-05-15
**Auditor:** Forgemaster ⚒️
**Scope:** Studies 54–68 (15 studies)
**Purpose:** Rate every study for experimental rigor, flag studies needing redesign, identify systematic gaps in the Cocapn Wheel.

---

## Scoring Rubric

Each criterion scored 0 or 1. Studies below 4/7 flagged for redesign.

| # | Criterion | Standard |
|---|-----------|----------|
| 1 | **Sample size** | N > 30 for statistical significance (or explicit power analysis) |
| 2 | **Controls** | Proper baseline / comparison condition |
| 3 | **Blinding** | Results judged without knowledge of expected outcome |
| 4 | **Multiple comparisons** | Corrected for multiple testing (Bonferroni, FDR, etc.) |
| 5 | **Reproducibility** | Sufficient detail to replicate from the writeup |
| 6 | **Effect size** | Reported alongside p-values (Cohen's d, R², Δpp, etc.) |
| 7 | **Ecological validity** | Simulation approximates real fleet conditions |

---

## Per-Study Ratings

### STUDY 54: Conservation Law vs GL(9) Alignment Correlation

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 100 random fleet states — adequate for correlation analysis |
| Controls | 1 | Both positive and negative stress tests (4 scenarios) |
| Blinding | 0 | Correlation computed directly — no subjective judgment, but no blinding either |
| Multiple comparisons | 0 | 3 metric pairs tested with no correction |
| Reproducibility | 1 | Parameters, formulas, and results all specified |
| Effect size | 1 | r = −0.179, R² values reported |
| Ecological validity | 1 | Fleet states sampled from realistic distributions |
| **Total** | **5/7** | ✅ PASS |

**Issues:** No multiple-comparisons correction on 3 correlation tests. Blinding not applicable (objective metrics).

---

### STUDY 55: Router Accuracy Over Time — Degradation & Conservation Prediction

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 400 rounds total — adequate for trajectory analysis |
| Controls | 1 | Three-phase design (baseline → degradation → recovery) |
| Blinding | 0 | Automated scoring — no judgment calls |
| Multiple comparisons | 0 | Multiple window comparisons without correction |
| Reproducibility | 1 | Full simulation parameters, seed=42, all configs listed |
| Effect size | 1 | Accuracy drops (75%→10%), conservation values, correlation coefficients |
| Ecological validity | ⚠️ 0 | **Pure simulation using `fleet_router_api.py` classes with synthetic accuracies — not validated against live API behavior** |
| **Total** | **4/7** | ✅ PASS (barely) |

**Issues:** Ecological validity is the main concern. The simulation uses synthetic accuracy values and degradation rates that may not match real provider behavior. The "baseline accuracy is 70%" because of a load-balancing bug — this could be a simulation artifact. The death spiral finding is valuable but needs live validation. No multiple-comparisons correction across windows.

---

### STUDY 56: Cross-Domain Transfer

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 120 trials (4 domains × 5 problems × 3 models × 2 conditions) |
| Controls | 1 | Bare vs labeled within-subjects design — clean control |
| Blinding | 0 | Automated numeric/text matching — no subjective judgment |
| Multiple comparisons | 0 | 12 model×domain cells tested, no correction |
| Reproducibility | 1 | Full methodology: temperature, max tokens, scoring criteria, rate limits |
| Effect size | 1 | Δ = −4pp overall, per-cell percentages reported |
| Ecological validity | 1 | Real API calls to DeepInfra and Ollama with actual model outputs |
| **Total** | **5/7** | ✅ PASS |

**Issues:** 5 problems per domain is thin — a single problem artifact (phys3 truncation) affects the entire domain result. No multiple-comparisons correction. The "Code shows ceiling effect" makes that domain uninformative. The experimenter error note (phys3 truncation) is honest but weakens the physics finding.

---

### STUDY 57: Conservation as Training Predictor

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 200 bootstrap samples per fleet size × 7 sizes = 1,400 samples |
| Controls | 1 | Four methods compared (conservation-modulated, standalone, fleet avg, random) |
| Blinding | 0 | Automated computation — no subjective judgment |
| Multiple comparisons | 0 | 7 fleet sizes tested without correction for the correlation analysis |
| Reproducibility | 1 | Full parameters, embedding dimensions, agent model described |
| Effect size | 1 | MAE values, R², correlation coefficients with p-values |
| Ecological validity | ⚠️ 0 | **Synthetic embeddings — agent accuracy derived from cosine similarity with random task vectors, not real model outputs** |
| **Total** | **4/7** | ✅ PASS (barely) |

**Issues:** The agent model is entirely synthetic. "Accuracy derived from cosine alignment with a random task vector" means the result could change with a different accuracy-generating mechanism. The negative result (conservation doesn't predict) is robust to this, but the specific MAE values are simulation artifacts. The V=5 trending signal (p=0.062) is correctly caveated.

---

### STUDY 58: MythosTile Consensus — GL(9) vs Hebbian Fault Detection

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | ⚠️ 0 | **50 scenarios total, 25 faulty = 5 per fault type — well below N>30 per cell** |
| Controls | 1 | 25 healthy + 25 faulty scenarios |
| Blinding | 0 | Automated detection — no subjective judgment |
| Multiple comparisons | 0 | 5 fault types compared without correction |
| Reproducibility | ⚠️ 0 | **No seed specified, fault generation mechanism not fully described** |
| Effect size | 1 | Precision, recall, F1 reported per detector |
| Ecological validity | ⚠️ 0 | **Fault types are injected manually (confidence_drop, content_scramble, etc.) — unclear how realistic these are** |
| **Total** | **2/7** | ❌ **NEEDS REDESIGN** |

**Critical issues:** Only 5 scenarios per fault type is severely underpowered. The 60% agreement rate has enormous confidence intervals at this sample size. Three fault types (confidence_spike, content_scramble, domain_drift) show 0% detection for both methods — is this a real finding or a bug? Reproducibility is weak: no random seed, fault generation code not included. Ecological validity is unclear — the fault types are simulated, not validated against real model failures. **This study's conclusions are unreliable without larger N and better documentation.**

---

### STUDY 59: Tier Taxonomy for Code Generation

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | ⚠️ 0 | **50 trials total (10 tasks × 5 models × 1 trial each) — no replication** |
| Controls | 1 | Bare-only condition matches the math tier methodology |
| Blinding | 0 | Automated assertion-based scoring |
| Multiple comparisons | 0 | 5 models × 3 difficulty levels compared without correction |
| Reproducibility | 1 | Tasks, models, scoring criteria all specified |
| Effect size | 1 | Per-model accuracy, tier group analysis, failure details |
| Ecological validity | 1 | Real API calls, real model outputs, assertion-based testing |
| **Total** | **3/7** | ❌ **NEEDS REDESIGN** |

**Critical issues:** **Zero replication** — each model sees each task exactly once. A single lucky/unlucky response determines the entire result. The 90% vs 95% Tier 1/2 difference could vanish or reverse with N>1. The failure analysis (9 failures total) is anecdotal at this sample size. This study needs at minimum 3-5 trials per cell (150-250 total) before the tier compression finding is trustworthy.

---

### STUDY 60: Temperature × Tier Interaction

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 144 trials (4 temps × 3 tiers × 4 problems × 3 trials) |
| Controls | 1 | Temperature 0.0 as baseline, within-model comparison |
| Blinding | 0 | Automated number extraction |
| Multiple comparisons | 0 | 12 temperature×tier cells compared without correction |
| Reproducibility | 1 | Prompt, scoring, models, concurrency all specified |
| Effect size | 1 | Per-cell accuracy, explicit Δ comparison with Study 28 |
| Ecological validity | 1 | Real API calls (DeepInfra + Ollama) |
| **Total** | **5/7** | ✅ PASS |

**Issues:** The discrepancy with Study 28 (67% vs 17% at T=0.7) is acknowledged but not resolved. Only 3 trials per cell is marginal — the 2/12 Hermes-70B correct at T=0.7 could be 1/12 or 3/12 with a different seed. The honest reporting of this discrepancy is a strength.

---

### STUDY 61: GSM8K Replication of Activation-Key Model

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 480 trials (20 problems × 3 conditions × 4 models × 2 trials) |
| Controls | 1 | Three-condition within-subjects (bare → notation → scaffolded) |
| Blinding | 0 | Automated number extraction |
| Multiple comparisons | 0 | 4 hypotheses × 4 models × 3 conditions — no correction |
| Reproducibility | 1 | Full problem sets, conditions, scoring methodology |
| Effect size | 1 | Δpp values, per-model breakdowns, difficulty analysis |
| Ecological validity | 1 | Real API calls to actual models |
| **Total** | **5/7** | ✅ PASS |

**Issues:** Experimenter errors acknowledged (2 wrong expected answers, corrected post-hoc). Only 2 trials per cell limits variance estimation. The scaffold-confusion finding (gemma3:1b) is novel but based on a single model — needs replication. The "Tier 1.5" proposal is provocative but premature with N=1 model showing it. Still, this is one of the best-designed studies in the set.

---

### STUDY 63: Fleet Self-Healing via GL(9) Fault Detection

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | ⚠️ 0 | **Phase A: 50 rounds with 7 faults. Phase B: 50 rounds × 3 strategies. Phase C: 8 scenarios. All underpowered.** |
| Controls | 1 | no_action baseline, three strategies compared |
| Blinding | 0 | Automated fault injection and detection |
| Multiple comparisons | 0 | 3 strategies × 4 cascade scenarios compared without correction |
| Reproducibility | ⚠️ 0 | **No seed, fault injection mechanism partially described, thresholds specified but generation code not included** |
| Effect size | 1 | Accuracy deltas, precision/recall/F1, detection latency |
| Ecological validity | ⚠️ 0 | **Simulation with synthetic expert accuracies, synthetic intent vectors — not validated against real fleet** |
| **Total** | **2/7** | ❌ **NEEDS REDESIGN** |

**Critical issues:** The sample sizes are very small — 7 faults in Phase A, 8 per strategy in Phase B, 4 cascade scenarios in Phase C. The 100% precision in Phase A is based on 5 detections out of 7 faults — the confidence interval on precision is enormous. The finding that quarantine and cross_consult produce identical results (86.78% accuracy) is suspicious — is this a bug or a real finding? Reproducibility is weak without the exact simulation code. This study's architecture is sound but its evidence base is thin.

---

### STUDY 63B: RMT Derivation of the Conservation Law

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | V ∈ {5, 10, 30, 100, 200} with Monte Carlo at each — adequate for curve fitting |
| Controls | 1 | Multiple ensembles compared (dense, sparse, Gaussian, exponential) |
| Blinding | 0 | Automated computation |
| Multiple comparisons | 0 | 5 ensembles compared without correction |
| Reproducibility | 1 | Full methodology, matrix generation, eigenvalue analysis described |
| Effect size | 1 | R² values, slope comparisons, per-ensemble parameters |
| Ecological validity | 1 | Mathematical derivation — validity is internal consistency |
| **Total** | **5/7** | ✅ PASS |

**Issues:** The **critical discrepancy** (slope direction opposite to paper's claim) is honestly reported but unresolved. This is actually a strength — negative/null results with clear explanation. The conclusion that the conservation law is "NOT a theorem derivable from RMT alone" is important and well-supported. The main risk is that the paper's original law may be based on a specific (undocumented) matrix ensemble, making comparison apples-to-oranges.

---

### STUDY 64: Shell Shock Recovery Dynamics

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | ⚠️ 0 | **4 scenarios × 3 strategies = 12 data points — no replication, no bootstrapping** |
| Controls | 1 | Three strategies compared, quarantine+wait as baseline |
| Blinding | 0 | Automated simulation |
| Multiple comparisons | 0 | 3 strategies × 4 scenarios compared without correction |
| Reproducibility | ⚠️ 0 | **Simulation described at high level but exact parameters (recovery rates, scaling functions) not fully specified** |
| Effect size | 1 | Recovery rounds, tiles lost, accuracy trajectories |
| Ecological validity | ⚠️ 0 | **Synthetic fleet with simulated degradation — recovery rates (4% passive, 26% max) are assumed, not measured** |
| **Total** | **2/7** | ❌ **NEEDS REDESIGN** |

**Critical issues:** The headline finding ("conservation reweighting is 3.1× faster") is based on 4 scenarios with no replication. The "full fleet stress recovers in 1 round" is an extreme outlier that drives the average — without it, the mean would be ~4 rounds, still good but less dramatic. Hebbian rebalancing "never converged within 100 rounds" but was it run for 100 rounds or just checked at 100? The recovery rates are free parameters chosen by the experimenter — different rates could produce different winners. This study's conclusion is plausible but not yet reliable.

---

### STUDY 65: Ensemble Slope (What Makes Hebbian Decreasing)

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 8 regimes × multiple V values, parameter sweep with 7 configurations — adequate for mechanism identification |
| Controls | 1 | 8 matrix regimes compared, random dense as baseline |
| Blinding | 0 | Automated simulation |
| Multiple comparisons | 0 | 8 regimes × parameter sweep without correction |
| Reproducibility | 1 | Full methodology, Hebbian parameters, regime definitions |
| Effect size | 1 | Slope values, R², top-1 eigenvalue ratios, effective rank |
| Ecological validity | 1 | Hebbian dynamics are well-motivated, scale-free networks are a realistic topology |
| **Total** | **5/7** | ✅ PASS |

**Issues:** The decay sweep (7 configurations) is sparse — the critical transition zone (d/lr ~ 1-10) has only a few points. The "plain Hebbian is FLAT" result (R² ≈ 0) could be noise — flat slope with zero explanatory power is not a finding, it's absence of signal. The four-hypothesis structure with explicit verdicts is a strength.

---

### STUDY 66: Decay Tuning

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | 7 decay rates × 300 steps × 2 activation modes, plus 20-rate fine sweep — adequate |
| Controls | 1 | Two activation modes, PI controller vs static tuning, binary search validation |
| Blinding | 0 | Automated simulation |
| Multiple comparisons | 0 | Multiple criteria compared without correction |
| Reproducibility | 1 | Full parameters, compliance definition, controller specs |
| Effect size | 1 | γ+H ranges, R², compliance percentages, error magnitudes |
| Ecological validity | ⚠️ 0 | **9-agent fleet with synthetic Hebbian dynamics — fleet may behave differently with real models** |
| **Total** | **4/7** | ✅ PASS (barely) |

**Issues:** The "no decay rate hits all 5 criteria" finding is honest but suggests the criteria may be poorly calibrated for the 9-agent case. The PI controller failure is well-diagnosed. The fleet-size-dependent decay policy is a reasonable extrapolation but untested at those sizes. The 0.049 achievable range is narrow — is this enough to matter operationally?

---

### STUDY 67: Scale Break (Cascade Risk at V > 20)

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | 1 | V ∈ {5, 10, 20, 30, 50, 75, 100, 150, 200} — 9 fleet sizes with multiple conditions |
| Controls | 1 | Baseline + bad coupling + adversarial conditions |
| Blinding | 0 | Automated simulation |
| Multiple comparisons | 0 | 3 hypotheses tested, rolling R² across 9 V values — no correction |
| Reproducibility | 1 | Full methodology, Hebbian parameters, fleet configurations |
| Effect size | 1 | R² degradation curve, γ+H values, deviation from paper |
| Ecological validity | ⚠️ 0 | **Simulated Hebbian fleet — no validation against real multi-agent systems** |
| **Total** | **4/7** | ✅ PASS (barely) |

**Issues:** The plateau finding is the key contribution, but it's specific to the Hebbian parameters used (lr=0.01, decay=0.001). Different parameters (per Study 65) would produce different transition points. The "bad coupling recovery" test is well-designed but the 30% bad-start assumption is arbitrary. The adversarial result (50% suppression regardless of V) is interesting but based on a single adversarial fraction (20%). More fractions needed.

---

### STUDY 68: Adversarial Coupling — Security Audit

| Criterion | Score | Notes |
|-----------|:-----:|-------|
| Sample size | ⚠️ 0 | **200 rounds × 5 strategies = 1,000 total rounds, but only 1 trial per strategy with 1 adversarial agent — no replication** |
| Controls | 1 | 8 honest + 1 adversarial, 5 strategies spanning attack space |
| Blinding | 0 | Automated detection |
| Multiple comparisons | 0 | 5 strategies × 2 detectors compared without correction |
| Reproducibility | 1 | Detection thresholds, fault definitions, strategy parameters described |
| Effect size | 1 | Detection rounds, tiles corrupted, compliance at detection |
| Ecological validity | ⚠️ 0 | **Simulated adversarial behavior — a real adversary would adapt to detection, which the simulation doesn't model** |
| **Total** | **3/7** | ❌ **NEEDS REDESIGN** |

**Critical issues:** Single trial per strategy is the main problem. The "NEVER detected" results for 3 strategies are based on 200 rounds each — a single run. Run it again and detection might happen at round 180, or never. The adversarial strategies are predetermined and static — a real adversary adapts. The Goldilocks zone (5-10% error) finding is valuable but needs replication with different fleet sizes, multiple adversarial agents, and adaptive strategies. The finding that Hebbian detected zero strategies is striking but could be a threshold calibration issue.

---

## Summary Scorecard

| Study | Sample | Controls | Blind | Multi-Comp | Repro | Effect | Eco-Val | **Total** | **Verdict** |
|-------|:------:|:--------:|:-----:|:----------:|:-----:|:------:|:-------:|:---------:|:-----------:|
| 54 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | **5/7** | ✅ Pass |
| 55 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | **4/7** | ✅ Pass |
| 56 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | **5/7** | ✅ Pass |
| 57 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | **4/7** | ✅ Pass |
| 58 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | **2/7** | ❌ Redesign |
| 59 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | **3/7** | ❌ Redesign |
| 60 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | **5/7** | ✅ Pass |
| 61 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | **5/7** | ✅ Pass |
| 63 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | **2/7** | ❌ Redesign |
| 63B | 1 | 1 | 0 | 0 | 1 | 1 | 1 | **5/7** | ✅ Pass |
| 64 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | **2/7** | ❌ Redesign |
| 65 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | **5/7** | ✅ Pass |
| 66 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | **4/7** | ✅ Pass |
| 67 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | **4/7** | ✅ Pass |
| 68 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | **3/7** | ❌ Redesign |

### Aggregate: 5 flagged for redesign (33%)

---

## Studies Needing Redesign

### ❌ STUDY 58 (2/7) — MythosTile Consensus
**What's wrong:** N=5 per fault type, no seed, unclear fault generation, zero detection for 3/5 fault types.
**Fix:** Minimum N=50 per fault type (250 faulty scenarios), include random seed, document fault injection code, validate fault types against real model failure modes.

### ❌ STUDY 59 (3/7) — Tier Taxonomy for Code
**What's wrong:** Zero replication (1 trial per cell). The tier compression finding rests on 50 data points with no variance estimate.
**Fix:** Minimum 5 trials per cell (250 total), bootstrap confidence intervals on tier differences, add more hard tasks (current hard tasks don't separate Tiers 1/2).

### ❌ STUDY 63 (2/7) — Fleet Self-Healing
**What's wrong:** Tiny sample sizes (7 faults Phase A, 8 per strategy Phase B), suspicious identical results for quarantine and cross_consult, no reproducibility.
**Fix:** Minimum 100 rounds per phase, 50+ fault injections per strategy, replicate with different seeds, investigate why quarantine == cross_consult.

### ❌ STUDY 64 (2/7) — Shell Shock Recovery
**What's wrong:** 4 scenarios with no replication, free parameters chosen post-hoc, Hebbian "never converged" finding is ambiguous.
**Fix:** Bootstrap 100+ runs per scenario, sweep recovery rate parameters, run Hebbian for 200+ rounds to confirm non-convergence, test with real degradation profiles.

### ❌ STUDY 68 (3/7) — Adversarial Coupling
**What's wrong:** Single trial per strategy, static adversaries, one fleet size, one adversarial fraction.
**Fix:** 20+ trials per strategy, adaptive adversaries, multiple fleet sizes (5, 9, 20, 50), multiple adversarial fractions (5%, 10%, 20%, 40%), test detection under different GL(9) thresholds.

---

## Systematic Gaps in the Cocapn Wheel

### 1. **No Study Validates Simulations Against Live Fleet Data** 🔴
Studies 55, 57, 58, 63, 64, 66, 67, and 68 all use pure simulation. Not one compares its synthetic results to actual model API behavior. The entire conservation/Gl(9) architecture is built on simulations that may not reflect reality.

**Missing study:** Run the fleet router on live API calls for 1,000+ requests. Measure actual conservation, alignment, and accuracy. Compare to simulation predictions.

### 2. **No Multiple-Comparisons Correction in Any Study** 🔴
All 15 studies test multiple hypotheses or compare multiple conditions without Bonferroni, FDR, or any correction. With 5-12 comparisons per study, the false positive rate is inflated across the entire program.

### 3. **No Replication of Key Findings Across Studies** 🟡
Several findings are stated once and then treated as established:
- Conservation law (Study 54: independent signals) — not replicated
- Self-healing works (Study 63) — contradicted by Study 55 (death spiral) and Study 68 (adversarial evasion)
- Decay controls slope (Study 65) — partially validated by Study 66, but with different parameters

### 4. **No Study Tests Temporal Stability** 🟡
Every study is a snapshot. None tests whether findings persist across hours, days, or model updates. The conservation law could be time-dependent in ways these cross-sectional studies miss.

### 5. **No Power Analysis** 🟡
No study reports a priori power analysis. Sample sizes appear to be chosen by convention (100 rounds, 200 rounds) rather than statistical planning.

### 6. **Blinding Is Universally Absent** 🟡
Every study uses automated scoring, making blinding technically unnecessary but also meaning no study guards against the experimenter's choice of scoring heuristic influencing results. The phys3 truncation issue in Study 56 is a perfect example — the scoring heuristic missed correct answers.

---

## Confounders We're Not Controlling

| Confounder | Affected Studies | Risk |
|------------|-----------------|------|
| **API routing variance** (DeepInfra routes to different backends) | 56, 59, 60, 61 | Results may not be reproducible across API calls to the same model |
| **Prompt sensitivity** (small wording changes shift activation) | 56, 60, 61 | The "bare" condition is one specific prompt — different bare prompts could give different baselines |
| **Temperature implementation** (providers implement sampling differently) | 60 | The T=0.7 step-function for Hermes may be a DeepInfra-specific artifact |
| **Fleet size = 9** (nearly all simulation studies use 9 agents) | 55, 57, 58, 63, 64, 66, 68 | Findings may not scale — Study 67 shows V matters, but the other studies ignore it |
| **Hebbian parameters** (lr=0.01, decay=0.001 as defaults) | 63, 64, 65, 66, 67 | These are free parameters. Studies 65-66 show they matter enormously, but most studies use fixed values |
| **Answer extraction heuristics** | 56, 60, 61 | Number extraction from free-text is fragile. phys3 truncation, Chinese characters in code, etc. |
| **Experimenter-generated problems** | 56, 59, 61 | Problems are hand-crafted, not drawn from standardized benchmarks (except GSM8K-style in 61) |

---

## Circular Reasoning Check

### 🟢 No Direct Circularity Found
No study assumes its own conclusion. All studies state a hypothesis, test it, and report whether it was confirmed or rejected.

### 🟡 Indirect Self-Reinforcement Loop
There's a concerning pattern where studies build on each other's assumptions without independent validation:

1. **Study 54** establishes conservation and GL(9) as independent → **Study 63** uses both for fault detection → **Study 64** uses conservation for recovery → **Study 66** tunes conservation parameters → **Study 68** tests the combined system.

If Study 54's independence finding is wrong (or only holds for the specific simulation parameters used), every downstream study inherits that error. The chain has no independent anchor point.

2. **Study 63B** shows the conservation law's constants depend on the matrix ensemble → **Studies 65-67** identify the Hebbian regime as the correct ensemble → but they use simulation parameters that produce the desired slope direction. There's a risk of tuning the simulation to confirm the theory rather than testing the theory against reality.

### ⚠️ The Simulation Echo Chamber
The deepest concern: **we're studying our own simulations, not the real system.** The conservation law, GL(9) alignment, Hebbian dynamics, fault detection, and recovery strategies are all properties of our simulation code. Until we validate against live fleet data, we're confirming that our simulation is internally consistent — not that it reflects reality.

---

## Recommendations

### P0: Immediate
1. **Replicate Studies 58, 59, 63, 64, 68** with adequate sample sizes (N > 30 per cell)
2. **Add Bonferroni correction** to all studies with multiple comparisons
3. **Run one live validation study** comparing simulation predictions to actual API behavior

### P1: This Week
4. **Seed all simulations** and include seeds in writeups
5. **Include simulation source code** in every study (currently missing from 58, 63, 64)
6. **Test at multiple fleet sizes** (5, 9, 20, 50) — not just 9
7. **Sweep Hebbian parameters** in studies that depend on them

### P2: Strategic
8. **Design a prospective study** that preregisters hypotheses before running simulations
9. **Build a live fleet benchmark** (1000+ real API calls) to anchor simulation parameters
10. **Test adversarial strategies adaptively** — let the adversary learn from detection results

---

## The Bottom Line

**10 of 15 studies pass (67%). 5 need redesign (33%).**

The program has a strong mathematical foundation (63B, 65) and well-designed empirical studies (56, 60, 61). The weaknesses are concentrated in the simulation-heavy operational studies (58, 63, 64) that test the fleet management layer. These are the studies most in need of larger samples and live validation.

The biggest systemic risk is the **simulation echo chamber** — we're building an increasingly elaborate theory about fleet dynamics without ever checking if real fleets behave the same way. One well-designed live validation study would be worth more than all 15 simulation studies combined.

---

*Study 69 · Forgemaster ⚒️ · PLATO Fleet Laboratory · 2026-05-15*
