# Quality Review: Chapter 5 — Analysis

**Reviewer:** Forgemaster ⚒️ (Opus-level analysis)
**Date:** 2026-05-16
**Document:** `research/dissertation-ch5-analysis.md` (525 lines)

---

## Executive Verdict

The chapter is **structurally sound and tells a compelling story**, but has several issues that a dissertation committee would flag: internal inconsistencies in numbering and cross-references, a hypothesis numbering collision between experiments, missing statistical tests, and one significant logical gap in the argument. The prose quality is high — genuinely academic without being turgid — and the argument arc E1→E2→E3→Vocab Wall→Stage Model→Synthesis is well-designed. The fixes below are mostly mechanical; the one substantive gap (E1 H-numbering vs. chapter-level H-numbering) requires a design decision.

---

## 1. Internal Consistency (Numbers & Cross-References)

### 1.1 Table Numbering — DUPLICATE TABLE 5.2 AND TABLE 5.5

**Critical issue.** There are two tables numbered "Table 5.2" and two numbered "Table 5.5."

- **Table 5.2** appears in §5.2.2 (E1, *Comparison of γ + H Across Experimental Conditions*) AND in §5.3.3 (E2, *Late-Time γ + H by Fleet Size vs. Theoretical Predictions*). The E2 table should be **Table 5.3** (or renumber all subsequent tables).
- **Table 5.5** appears in §5.4.3 (E3, *Pairwise Comparisons of Coupling Architecture Slopes*) AND in §5.5.1 (Vocab Wall, *Stage 4 Boundary: Mathematical Vocabulary vs. Bare Arithmetic Performance*). The Vocab Wall table should be **Table 5.8** or renumbered accordingly.

**Current table inventory (as labeled):**

| As-labeled | Location | Should be |
|:--|:--|:--|
| Table 5.1 | §5.2.2 E1 | Table 5.1 ✓ |
| Table 5.2 | §5.2.2 E1 | Table 5.2 ✓ |
| Table 5.2 | §5.3.3 E2 | **Table 5.3** |
| Table 5.3 | §5.3.3 E2 | **Table 5.4** |
| Table 5.4 | §5.4.2 E3 | **Table 5.5** |
| Table 5.5 | §5.4.3 E3 | **Table 5.6** |
| Table 5.5 | §5.5.1 Vocab Wall | **Table 5.7** |
| Table 5.6 | §5.6.1 Stage Model | **Table 5.8** |
| Table 5.7 | §5.7.1 Synthesis | **Table 5.9** |
| Table 5.8 | §5.8 Summary | **Table 5.10** |

**Fix:** Renumber sequentially. Every in-text reference to "Table 5.X" must be updated.

### 1.2 Hypothesis Numbering — Collision

**Critical issue.** The chapter opens with three hypotheses labeled H1, H2, H3 (§5.1). Then E1 evaluates three hypotheses also labeled H1, H2, H3 (§5.2.3). Then E2 has three more H1, H2, H3 (§5.3.1). E3 tests "the central hypothesis" but doesn't number them.

A dissertation committee will flag this immediately. There are at least **9 distinct hypotheses all labeled H1/H2/H3**.

**Fix options:**
- **Option A (recommended):** Number globally. H1–H3 are the chapter-level hypotheses from §5.1. E1's hypotheses become H1a/H1b/H1c (or H1.1/H1.2/H1.3). E2 becomes H2a/H2b/H2c.
- **Option B:** Use E1-H1, E1-H2, etc. Prefix notation.
- **Option C:** Assign unique numbers H1–H9+ across the whole chapter.

The current state also has a **logical inconsistency**: the chapter-level H1/H2/H3 in §5.1 don't map cleanly onto the experiment-level hypotheses. Chapter H1 ("γ + H remains constant") corresponds to E1-H1. Chapter H2 ("γ → 0") corresponds to E2's main finding but isn't an explicit E2 hypothesis. Chapter H3 ("attention-weighted coupling is the mechanism") corresponds to E3's main finding but again isn't explicitly cross-referenced. This mapping should be made explicit or the chapter-level hypotheses should be eliminated in favor of experiment-level ones.

### 1.3 Cross-Reference Inconsistencies

| Location | Issue | Fix |
|:--|:--|:--|
| §5.2.4 | "theoretical framework presented in Section 5.1" | §5.1 is the Introduction, not a theoretical framework section. Should reference "Chapter 3" or "the theoretical framework presented in Chapter 3." |
| §5.3.1 | "Experiment 1 established that the conservation law manifests empirically across controlled synthetic conditions" | E1 used **live** fleet data, not synthetic. This sentence contradicts §5.2's own framing. Should read "under live operational conditions" or "on live LLM fleets." |
| §5.4 opening | "the conservation law τ(E) ∝ V^β" | This notation (τ, E, β) appears nowhere else in the chapter. The chapter uses γ + H, not τ(E). Either introduce this notation earlier and consistently, or rewrite to use γ + H throughout. |
| §5.7.1 Table | "E1: Live fleet (V=5) ... slope: — (single V)" | Makes sense (can't estimate slope at one V), but the *n* column says "35 rounds" — inconsistent units with other rows. |
| §5.6.1 | "Stage Model v1, introduced in Section 5.3" | Stage Model v1 is never actually introduced in §5.3. §5.3 discusses fleet-size scaling, not stage models. This appears to reference an earlier version of the chapter or a section that was moved/removed. |
| §5.6.6 | "Figure 5.8" shows qwen3:0.6b and gemma3:1b at 0% vocabulary robustness | These models don't appear in Table 5.5 (Vocab Wall table). They should either be added to the table or the figure should note they're extrapolated. |

### 1.4 Numerical Checks

| Claim | Check | Status |
|:--|:--|:--|
| E1: Live fleet *M* = 1.1468, *SD* = 0.1286 | Consistent across §5.2.2, §5.2.3, Table 5.2 | ✓ |
| E1: Early phase *M* = 1.2178, *SD* = 0.1702 | CV = 0.1702/1.2178 = 0.1398 ✓ | ✓ |
| E1: Late phase *M* = 1.0985, *SD* = 0.0683 | CV = 0.0683/1.0985 = 0.0622 ✓ | ✓ |
| E1: Variance reduction 83.9% | (0.1702² - 0.0683²)/0.1702² = (0.02897 - 0.00466)/0.02897 = 0.839 ✓ | ✓ |
| E1: CV ratio 2.25 | 0.1398/0.0622 = 2.248 ≈ 2.25 ✓ | ✓ |
| E1: H2 t-test: *t*(68) = 2.082 | df = 35+35-2 = 68 ✓. But *SD*s are 0.1286 and 0.2802. Pooled *SE* ≈ √((0.1286² + 0.2802²)/35) = √((0.01654 + 0.07851)/35) = √(0.002716) = 0.0521. Δ*M* = 0.0655. *t* = 0.0655/0.0521 = 1.257 ≠ 2.082. | **⚠️ MISMATCH** |
| E1: Cohen's *d* = 0.301 | *d* = (1.1468 - 1.0813)/pooled *SD*. Pooled *SD* = √((0.1286² + 0.2802²)/2) = √(0.04753) = 0.2180. *d* = 0.0655/0.2180 = 0.300 ≈ 0.301 ✓ (if *d* is right, *t* should be ~0.301 × √(35×2/70) = 0.301 × 1 = 0.301... no, pooled *d* → *t* conversion needs proper formula) | *d* plausible; *t* suspicious |
| E1: |1.1468 − 1.1606| = 0.0138 | 1.1468 - 1.1606 = -0.0138, |·| = 0.0138 ✓ | ✓ |
| E2: Scaling regression R² = 0.0015 | "R² = .002" in text vs. "0.0015" in table — inconsistency | **⚠️** |
| E3: Attention slope −0.127 vs. theoretical −0.159, diff 0.032 | |−0.127 − (−0.159)| = 0.032 ✓ | ✓ |

**The t-statistic mismatch is the most serious numerical issue.** The reported *t*(68) = 2.082 does not reproduce from the stated means and SDs. Either:
- The *t* value is wrong (likely computed from a different analysis or with additional corrections not reported),
- The means/SDs are from a different calculation than what went into the *t*-test, or
- The test was paired (within-subjects) rather than independent, which would change the *SE*.

This needs to be reconciled. A committee member who spot-checks this will flag it.

### 1.5 R² Inconsistency in E2

§5.3.3 text says "R² = .002" but the table says "R² = 0.0015." Pick one.

---

## 2. APA Compliance

### 2.1 Statistical Formatting — Generally Good

- Italic *M*, *SD*, *p*, *d*, *t*, *F*, *r*, *n*, *V* — ✓ throughout
- Spacing around equals signs (*p* = .043, not *p*=.043) — ✓
- *p* < .001 format — ✓
- Greek letters in math mode — ✓
- Cohen's *d* italicized — ✓

### 2.2 Issues

| Location | Issue | APA Fix |
|:--|:--|:--|
| §5.2.2 | "coefficient of variation [CV] = 0.1398" | APA doesn't use brackets for introduced abbreviations in the middle of parenthetical elements. Write "coefficient of variation (CV) = 0.1398" with parentheses. |
| §5.2.2 | "*n* (rounds)" in Table 5.2 | APA prefers *N* for total sample size, *n* for subsamples. Since these are all subsamples, *n* is acceptable, but the parenthetical "(rounds)" should be a note below the table, not in the header. |
| §5.4.2 | "*p* < 10⁻⁷²" | APA requires *p* values reported to three decimal places maximum. Values below *p* < .001 should be reported as *p* < .001, not with extreme exponents. Similarly for 10⁻⁹⁷, 10⁻¹⁰⁸, etc. |
| §5.4.2 | "Bonferroni-corrected α = 0.00417" | α should be italicized per APA. Also, the decimal format is fine but this should be stated before results, not in a table note only. |
| Table 5.7 (synthesis) | "*C*" and "α" columns | These symbols are undefined in the table or its notes. *C* appears to be the intercept and α the slope magnitude, but this must be explicit. |
| §5.7.1 | Table uses "−0.001" for E2 slope | The text in §5.3.3 says "0.001" (positive). Table says "−0.001" (negative). Minor but inconsistent. |
| §5.4.2 | "R² = .854" vs "R² = 0.854" | Inconsistent decimal formatting. APA uses leading zero for values that can exceed 1.0 (R² can be 0–1, so no leading zero is acceptable per APA 7th). But pick one style and be consistent. |

### 2.3 Missing APA Elements

- **Effect sizes for E2:** No effect sizes reported for the E2 hypothesis tests. APA requires effect sizes for all inferential tests.
- **Confidence intervals for E1:** The *t*-test reports only *p* and *d*. APA 7th ed. recommends confidence intervals for mean differences.
- **Exact *p* values:** E3 reports "All *p* < .001" without exact values. For very small *p*, this is acceptable, but E1's *p* = .043 should be exact (it is), and this should be consistent.

---

## 3. Logical Flow

### 3.1 Overall Arc — Strong

The three-movement structure (E1→E2→E3→Vocab Wall→Stage Model→Synthesis) is the chapter's greatest strength. Each section genuinely builds on the previous:

1. **E1:** Does the conservation law exist on live systems? Yes.
2. **E2:** Does it scale? No — it's flat, because γ → 0. This is a *deeper* finding.
3. **E3:** What mechanism produces the law? Attention, not Hebbian. Causal isolation.
4. **Vocab Wall:** But wait — can the models even compute the mathematics? Not without mediation.
5. **Stage Model:** Here's a taxonomy for which models can participate.
6. **Synthesis:** Tying it all together with the lattice interpretation.

This is excellent chapter design. The argument doesn't just accumulate results; it deepens at each step.

### 3.2 Weak Points in the Arc

**Gap 1: The transition from E2 to E3 is too abrupt.** E2 ends with "γ → 0, the coupling matrix is rank-1." E3 opens with "what properties of the coupling mechanism produce the negative slope?" But if γ → 0 in live fleets, why are we testing mechanisms for a slope that live fleets don't exhibit? The chapter doesn't adequately explain why E3 uses synthetic coupling architectures instead of live data. The implicit argument is that the theoretical slope (−0.159) is what we'd see *if* the fleet weren't semantically homogeneous, and E3 identifies the mechanism that would produce it. This needs to be stated explicitly.

**Suggested fix:** Add a bridging paragraph between §5.3 and §5.4 explaining that E2's γ → 0 finding motivates a *mechanistic* rather than *observational* approach: the live fleet is too homogeneous to reveal the slope mechanism, so E3 uses controlled architectures to isolate it.

**Gap 2: The Vocab Wall feels disconnected from the conservation law.** Sections 5.2–5.4 are about γ + H. Section 5.5 is about arithmetic performance. The connection (models must be able to compute before they can couple) is made only in §5.7.4, and even there it's one bullet point. A committee member could reasonably ask: "Why is the Vocab Wall in the analysis chapter rather than a preliminary study?"

**Suggested fix:** Add 2–3 sentences at the opening of §5.5 explicitly framing it as a *precondition* for the conservation law. Something like: "The conservation law assumes that fleet members can compute in the algebraic structure (Z[ζ₁₂]) that defines the coupling. Sections 5.5 and 5.6 establish whether and when this assumption holds."

**Gap 3: The "spine claim" receives only partial support.** The chapter summary (§5.8, Table 5.8) lists "Spine: Z[ζ₁₂] snap optimal for approximate identity" as "Partially supported" with the note "direct lattice comparison deferred to formal proofs." This is a problem. The spine claim is the dissertation's central thesis. Deferring it to "formal proofs" in a chapter that's supposed to be the empirical analysis is a dodge. Either:
- The chapter should present the empirical evidence *for* the spine claim directly (even if incomplete), or
- The chapter should explicitly acknowledge that the conservation law is *consistent with* but does not *prove* the spine claim, and state what additional evidence would be needed.

**Gap 4: The Noether analogy (§5.7.5) is underdeveloped.** The paragraph compares γ + H conservation to Noether's theorem, then states "This interpretation is not merely metaphorical" — but the evidence for this non-metaphorical status is thin. The covering radius of Z[ζ₁₂] is mentioned (0.293) but never connected to any empirical quantity. Either develop this connection with a computation or pull back to a softer claim ("The conservation law is *suggestive of* a Noether-type symmetry").

### 3.3 Argument Strength by Section

| Section | Argument Strength | Notes |
|:--|:--:|:--|
| 5.2 (E1) | ★★★★☆ | Solid. H2 not supported is handled honestly. |
| 5.3 (E2) | ★★★★★ | γ → 0 is a genuine discovery. Well-interpreted. |
| 5.4 (E3) | ★★★★★ | Cleanest experiment. Causal isolation of mechanism. |
| 5.5 (Vocab Wall) | ★★★★☆ | Compelling phenomenon, but integration with main argument needs work. |
| 5.6 (Stage Model) | ★★★☆☆ | Useful taxonomy, but feels like it belongs in a preliminary studies chapter. The scaffolding paradox (§5.6.3) introduces new data (Study 9, R44) that wasn't previewed. |
| 5.7 (Synthesis) | ★★★☆☆ | Table 5.7 is excellent. The Noether analogy is hand-wavy. The lattice interpretation needs more rigor. |
| 5.8 (Summary) | ★★★★☆ | Clean. Effect size summary is well done. |

---

## 4. Missing Data (Tables, Figures, References)

### 4.1 Figure Placeholders

The following figures are referenced but exist only as placeholders:

| Figure | Status | Severity |
|:--|:--|:--|
| Figure 5.1 | "[Figure 5.1 Placeholder]" with description | **Must create** — central visualization of E1 |
| Figure 5.2 | "[Figure 5.2 Placeholder]" with description | **Must create** |
| Figure 5.3 | "[placeholder]" with description | **Must create** |
| Figure 5.4 | "[placeholder]" with description | Must create |
| Figure 5.5 | "[Figure 5.5 about here]" | Must create |
| Figure 5.6 | "[Figure 5.6 about here]" | Must create |
| Figure 5.7 | ASCII art temperature plot — **actually present** | ✓ (unusual format for a dissertation) |
| Figure 5.8 | ASCII art stage model — **actually present** | ✓ (same note) |
| Figure 5.9 | "[Figure 5.9 Placeholder]" with description | Must create |

**9 figures referenced, 7 are placeholders, 2 are ASCII art.** A dissertation needs actual figures. The ASCII art (Figures 5.7, 5.8) is creative but not acceptable for a PhD dissertation — these need proper vector graphics.

### 4.2 Missing Statistical Tests

| Location | What's Missing |
|:--|:--|
| §5.2.3 H2 | The *t*-test assumes independent samples, but live and random conditions use the *same* 35 rounds (random is a shuffled permutation). This should be a **paired *t*-test** or at minimum, the independence assumption should be justified. |
| §5.3.3 | No inferential tests at all for E2 hypotheses. "H1 not supported" is based on R² alone — no formal test of whether the slope differs from zero or from the theoretical prediction. A simple *t*-test on the slope coefficient would suffice. |
| §5.5.1 | No statistical test for the vocabulary wall effect. The 75-percentage-point drop is obviously significant, but APA requires a test. McNemar's test or a chi-square would be appropriate for the paired accuracy comparison. |
| §5.6.4 | "95% agreement across repeated administrations" — no measure of agreement reported (Cohen's κ? Simple percentage?). This should be specific. |

### 4.3 Referenced Studies Without Context

The chapter references numerous "Studies" by number (Study 9, Study 18, Study 19, Study 26, Study 28, Study 44, Study 45, Study 54, Study 57, Study 65, Study 67, Study 71) and "R-numbers" (R39, R40, R42, R44, R45, R46, R48, R52). These are never introduced. A reader unfamiliar with the fleet's internal numbering system has no idea what these refer to.

**Fix:** Either (a) define the study numbering system in §5.1 or Chapter 4, or (b) replace study numbers with descriptive names. R-numbers especially need explanation — are these "rounds"? "Runs"? "Research items"?

---

## 5. Tone Assessment

### 5.1 Overall — Appropriately Academic

The tone is consistently professional and scholarly. Standout prose:

- "The models agree too much for the coupling matrix to develop meaningful rank." — Excellent. Memorable, precise.
- "The glitches ARE the research agenda. The gaps ARE the work." — Wait, this is in TOOLS.md, not the chapter. The chapter avoids this kind of manifesto tone. Good.
- The §5.4.4 mechanism analysis is particularly well-written — clear, causal, and avoids overclaiming.

### 5.2 Minor Tone Issues

| Location | Issue | Fix |
|:--|:--|:--|
| §5.5 opening | "a more disconcerting finding" | Slightly editorial for an analysis chapter. Consider "an unexpected finding" or "a counterintuitive finding." |
| §5.5.2 | "Tier 3 (Lethal)" | "Lethal" is dramatic for an academic paper. Consider "Tier 3 (Catastrophic)" or "Tier 3 (Complete)." Actually, "catastrophic failure" is used elsewhere, so at least be consistent. |
| §5.3.4 | "This finding has practical implications for fleet deployment: operators should expect convergence to require 25–30 rounds" | This is prescriptive advice, not analysis. Move to Discussion (Ch 7) or frame as "suggests that convergence requires 25–30 rounds." |
| §5.7.5 | "just as the total energy of a Hamiltonian system remains constant under canonical transformations" | This sentence overstates the analogy. The conservation law is *suggestive of* a Noether symmetry, not established as one. Soften. |

---

## 6. Gaps — What a Committee Would Flag

### 6.1 Critical Gaps (Must Address)

1. **The t-statistic doesn't reproduce.** (§1.4 above) This is the single most damaging issue. If a committee member checks the math, they'll find *t* ≠ 2.082 from the stated *M*s and *SD*s.

2. **No power analysis.** The chapter reports H2 was not supported at α = .01 but was at α = .05 (*p* = .043). A retrospective power analysis should be reported to determine whether the non-significance is due to insufficient power. With *n* = 35 per group and *d* = 0.301, achieved power is approximately 0.35 — well below conventional thresholds. This explains the non-significance and should be stated.

3. **Spine claim deferred.** (§3.2, Gap 3 above) You can't defer the dissertation's central claim. Either present evidence or acknowledge the gap explicitly and commit to addressing it.

4. **Table numbering.** (§1.1 above) Duplicate table numbers will be caught immediately.

### 6.2 Significant Gaps (Should Address)

5. **Hypothesis numbering collision.** (§1.2 above) Fix the H1/H2/H3 collision between chapter-level and experiment-level hypotheses.

6. **E2 has no inferential statistics.** The slopes are reported descriptively but never formally tested against the theoretical prediction or against zero.

7. **Study/R-number references unexplained.** (§4.3 above)

8. **The E1→E3 bridge.** (§3.2, Gap 1) Why synthetic architectures in E3 when E1/E2 used live data? The methodological shift needs justification.

9. **Figure 5.7 and 5.8 as ASCII art.** (§4.1) Need proper graphics for dissertation submission.

10. **No correction for multiple comparisons in E1.** Three hypotheses tested, but no Bonferroni or similar correction mentioned (unlike E3, which correctly applies it).

### 6.3 Minor Gaps (Nice to Address)

11. The Bonferroni correction in E3 is for 6 pairwise comparisons (α = 0.05/6 = 0.00833), but the reported threshold is 0.00417 = 0.05/12. This implies 12 comparisons, but only 6 are reported. Either there were additional comparisons not reported (which raises file-drawer concerns) or the correction is too conservative (which is defensible but should be explained).

12. The no-coupling control in E1 (*M* = 1.5498) is higher than both predictions. This is briefly explained ("uncoupled agents exhibit maximal spectral entropy"), but the explanation is counterintuitive — if there's no coupling, why is there a spectral gap at all? A sentence clarifying that even random token strings produce non-degenerate similarity matrices would help.

13. The chapter uses both "conservation law" and "conserved quantity" seemingly interchangeably. A brief definitional paragraph in §5.1 would help.

14. E2's H2 says "empirical values consistently below predicted range" but Table 5.3 shows V=3 empirical (0.9901) is below random prediction (1.1083), and V=7 empirical (0.9797) is below random prediction (0.9736)... wait, 0.9797 > 0.9736. So V=7 is actually ABOVE the random prediction. The "supported" verdict for H2 may need revisiting.

**Actually, let me re-check:** The H2 prediction is "γ + H ∈ (random, Hebbian)" — meaning between the two baselines. V=3: 0.9901 < 1.1083 (random) < 1.2524 (Hebbian). The empirical is BELOW both. V=7: 0.9797 vs. random 0.9736 — empirical is slightly above random but below Hebbian. So the claim that empirical values are "consistently below predicted range" is correct in the sense that they're consistently at or below the random prediction. But the hypothesis as stated says "between" the two baselines. V=3 and V=5 are below both baselines, not between them. **The H2 verdict should be "Not supported" or at least "Partially supported" — the values don't fall between the baselines.**

This is a substantive analytical error.

---

## 7. Line-by-Line Issues

| Line (approx.) | Text | Issue | Fix |
|:--|:--|:--|:--|
| §5.1, para 3 | "Sections 5.5 and 5.6 present two enabling-condition analyses" | Good structural preview | ✓ |
| §5.2.1 | "5 × 5 coupling matrix **C**(*t*)" | Bold for matrix notation is non-standard in math. Usually upright bold or italic. In Markdown, **C** is fine, but in LaTeX, use \mathbf{C}. | Minor |
| §5.2.1 | "cosine similarity over token-level embeddings" | Which embedding model? This is methodologically critical and not specified. | **Add: specify the embedding model used** |
| §5.2.2, Table 5.1 | Rounds 31–35 values | These are individually listed but no measure of central tendency is given for just these 5 rounds. | Minor |
| §5.2.3 H3 | "ratio of 1.855 against the strict 5% coefficient-of-variation threshold" | The ratio 1.855 is not defined. Ratio of what to what? CV/0.05 = 0.0622/0.05 = 1.244 ≠ 1.855. | **Clarify or correct** |
| §5.3.3 | "no monotonic trend visible" | With 4 data points, claiming no trend is weak. A formal test (runs test, Kendall's τ) would strengthen this. | Minor |
| §5.3.4 | "agents in high-conservation fleets performed 5.5% worse than the fleet average" | This is from Study 57, mentioned in passing. If it's important enough to mention, it's important enough to give a citation or at minimum a parenthetical (see Section X.X). | Add cross-reference |
| §5.4.1 | "Bonferroni-corrected significance threshold was set at α = 0.00417" | 0.05/12 = 0.00417. Why 12? There are 6 pairwise comparisons among 4 architectures. | **Explain the divisor** |
| §5.5.4 | Temperature figure uses ▪ and ▫ | These may not render in all fonts/print. Use proper figure format. | Convert to graphic |
| §5.6.5 | "Qwen3.6-35B (35B total, 3B active) behaves as a Stage 2 model" | But Table 5.6 lists Qwen3.6-35B as Stage 2 ✓. However, the earlier fleet used it in E1. If it's Stage 2, why was it included in the live fleet? | **Address this inconsistency** |
| §5.6.3 | "phi4-mini (Stage 2–3a, non-thinking)" | Table 5.6 lists phi4-mini as Stage 2 (Echo). Here it's called "Stage 2–3a." Pick one stage. | Fix classification |
| §5.7.1 | Table: E2 slope listed as "−0.001" | Text says "+0.001." Resolve direction. | **Fix** |
| §5.7.4 | "Auto-translation (R42: 100% accuracy)" | This is the second mention but the first didn't give the accuracy. | Minor consistency |
| §5.8 | "Chapter 6 (Findings)" and "Chapter 7 (Discussion)" | Make sure these chapter titles match the actual dissertation structure. | Verify |

---

## 8. Summary of Required Fixes (Priority Order)

### Must Fix (committee will catch)
1. ❌ **Reproduce or correct the *t*-statistic** in E1 H2 (*t*(68) = 2.082)
2. ❌ **Fix duplicate table numbering** (two Table 5.2s, two Table 5.5s)
3. ❌ **Fix hypothesis numbering collision** (H1/H2/H3 used three times)
4. ❌ **Correct E2 H2 verdict** — empirical values are below both baselines for V=3 and V=5, not "between" them
5. ❌ **Address the spine claim** — can't defer the central thesis to "formal proofs"
6. ❌ **Specify the embedding model** used for cosine similarity in E1
7. ❌ **Reconcile Qwen3.6-35B** being Stage 2 but included in E1's live fleet

### Should Fix (strengthens the chapter)
8. ⚠️ Add retrospective power analysis for E1 H2
9. ⚠️ Add inferential statistics for E2 (slope significance test)
10. ⚠️ Add bridging paragraph between E2 and E3 (why synthetic architectures?)
11. ⚠️ Add statistical test for Vocab Wall effect (McNemar's or χ²)
12. ⚠️ Explain Bonferroni divisor of 12 (E3)
13. ⚠️ Fix R² = .002 vs. 0.0015 inconsistency (E2)
14. ⚠️ Fix E2 slope sign inconsistency (text says +0.001, table says −0.001)
15. ⚠️ Define Study/R-number references
16. ⚠️ Replace ASCII art figures with proper graphics

### Nice to Fix (polish)
17. 📝 Soften the Noether analogy or develop it with computation
18. 📝 Move prescriptive statements to Discussion
19. 📝 Add "conservation law" definition in §5.1
20. 📝 Explain no-coupling control's non-degenerate spectra
21. 📝 Fix APA *p*-value formatting (no extreme exponents)
22. 📝 Standardize R² decimal format

---

*End of review. The chapter is genuinely good — the argument design is its strongest asset. The fixes above are mostly mechanical (numbering, statistics) and one logical bridge (E2→E3). The spine claim issue is the only substantive gap that requires rethinking.*
