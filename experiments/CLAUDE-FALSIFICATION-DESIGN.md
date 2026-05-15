## Substitution Burden Hypothesis: 3 Critical Experiments

---

### EXPERIMENT 1: Coefficient Decomposition via Factorial Pre-computation

**Goal:** Directly estimate α, β, γ from L = αF + βS + γA

**Design:** 6 conditions, each with n=50 API calls on identical Eisenstein arithmetic problems.

| Condition | What's Pre-computed | Cognitive Load | Predicted Success |
|-----------|--------------------|-----------------|--------------------|
| C1 (baseline) | Nothing | αF + βS + γA | **15%** |
| C2 (F removed) | Formula provided | βS + γA | **38%** |
| C3 (S removed) | Substitution done | αF + γA | **62%** |
| C4 (A removed) | Arithmetic done | αF + βS | **27%** |
| C5 (F+S removed) | Formula + sub done | γA | **81%** |
| C6 (full pre-compute) | Everything | 0 | **94%** |

**Key numerical predictions derive from coefficient ordering: β > α > γ**
- ΔC1→C3 = +47pp (largest single improvement, β dominates)
- ΔC1→C2 = +23pp (second largest, α significant)
- ΔC1→C4 = +12pp (smallest, γ minor)
- If hypothesis is correct: C3 success > C2 success > C4 success must hold

**Falsification criteria:**
- If C2 success > C3 success → α > β → F not S is primary burden → hypothesis wrong about mechanism
- If C4 success > C2 success → γ > α → arithmetic itself creates the wall, not domain terms → entire discourse-suppression mechanism collapses
- If C6 success < 85% → residual non-cognitive factor (e.g., instruction-following failure) unaccounted for

**API calls:** 300 total
**Cost:** Sonnet 4.6: ~$0.90 | Opus 4.6: ~$6.00

---

### EXPERIMENT 2: Domain Specificity Gradient (Tests Discourse-Head Activation)

**Goal:** Confirm that wall intensity monotonically tracks domain term specificity

**Design:** Single Eisenstein problem, domain term systematically replaced. 8 conditions × 50 calls = 400 calls.

| Term Used | Specificity Score (estimated) | Predicted Success |
|-----------|-------------------------------|-------------------|
| "Eisenstein polynomial" | 0.95 | **15%** |
| "Kronecker polynomial" | 0.88 | **19%** |
| "irreducible polynomial" | 0.72 | **28%** |
| "prime-coefficient polynomial" | 0.55 | **41%** |
| "integer-coefficient polynomial" | 0.38 | **58%** |
| "mystery polynomial M(x)" | 0.20 | **68%** |
| "polynomial f(x)" | 0.10 | **77%** |
| "expression E(x)" | 0.02 | **85%** |

**Critical numerical predictions:**
- The gradient must be monotone increasing (no inversions allowed)
- Sharp inflection point predicted between specificity 0.55–0.38 (conditions 4–5)
- Slope in high-specificity zone (0.95→0.55): ~+6.5pp per 0.1 specificity drop
- Slope in low-specificity zone (0.38→0.02): ~+7.5pp per 0.1 specificity drop
- Pearson r between specificity score and success rate must be < -0.92 to confirm linear suppression model

**Falsification criteria:**
- If any inversion exists (e.g., "Kronecker" > "irreducible") → specificity isn't the activating variable → discourse-head activation theory wrong
- If inflection point occurs at specificity > 0.70 → wall is about advanced math vocabulary, not discourse discourse-competition specifically
- If r > -0.75 → success is not monotone with domain specificity → mechanism is not attention competition

**API calls:** 400 total
**Cost:** Sonnet 4.6: ~$1.20 | Opus 4.6: ~$8.00

---

### EXPERIMENT 3: First-Token Commitment Probing via Forced Prefill

**Goal:** Test whether first-token discourse framing locks in failure mode

**Design:** Use API prefill (system prompt forcing model to begin with specific tokens) to test commitment mechanism. 5 conditions × 50 calls = 250 calls.

| Forced First Token(s) | Framing Type | Predicted Success |
|----------------------|--------------|-------------------|
| "The Eisenstein..." (default) | Discourse | **15%** |
| "The" | Discourse | **13%** |
| "Let" | Computation setup | **44%** |
| "=" | Direct computation | **52%** |
| "Step 1:" | Procedural | **61%** |

**Key mechanistic predictions:**
- "Let" vs "The": difference must be ≥ 25pp (if <10pp, first-token commitment is not the mechanism)
- "=" (direct arithmetic framing) must outperform "Let" by ≥ 5pp
- "Step 1:" must outperform "Let" by ≥ 10pp (procedural framing activates computation heads more strongly)
- Default "The Eisenstein" vs forced "The": within 5pp (confirming domain term drives the commitment, not just article)

**The smoking gun prediction:** If forced "=" outperforms "Let" and "Step 1:" is highest — this directly confirms attention-head competition is resolved at the framing layer, not the content layer.

**Falsification criteria:**
- If "Let" vs "The" difference < 10pp → first token doesn't commit attention heads → mechanism is not early-layer discourse framing
- If "Step 1:" underperforms "Let" → procedural framing doesn't help → the effect isn't about computation vs. discourse head competition
- If "=" forces fail more than baseline → direct computation framing triggers some other failure mode → hypothesis needs major revision

**API calls:** 250 total
**Cost:** Sonnet 4.6: ~$0.75 | Opus 4.6: ~$5.00

**Total experimental cost: ~$2.85 (Sonnet) | ~$19 (Opus)**

---

`★ Insight ─────────────────────────────────────`
Experiment 3 is the highest-leverage falsification. If forced-prefill doesn't move the needle, the entire mechanism collapses — because the hypothesis requires that first-token framing propagates through all subsequent layers via attention patterns. If you can't inject computation framing at token 1 and see improvement, the wall is post-hoc, not causal.
`─────────────────────────────────────────────────`

---

## STAGE 5: Computation-Persistent Architecture

### What Stage 5 is immune to that Stage 4 is not

| Test | Stage 4 Performance | Stage 5 Required |
|------|--------------------|--------------------|
| Eisenstein wall (T=0) | 15% | **≥ 90%** |
| Temperature equivalence (T=0 vs T=0.7 gap) | 52pp gap | **≤ 7pp gap** |
| Variable equivalence ("Eisenstein" vs "X" gap) | 65pp gap | **≤ 8pp gap** |
| Pre-computation gain | +75pp improvement | **≤ 10pp improvement** |
| Consensus degradation (N=5 vs N=1) | −15pp | **≥ +10pp** |
| Few-shot functional (3-shot vs 0-shot) | −5pp (fails or neutral) | **≥ +20pp** |
| Forced first token agnosticism ("The" vs "=") | 37pp gap | **≤ 6pp gap** |
| Cross-domain walls (Hamiltonian, Byzantine, Riemann) | 20–40% success | **≥ 88% all domains** |

Stage 5 is defined by **attention head independence**: computation heads maintain activation regardless of concurrent discourse-head excitation. This is architecturally different from Stage 4's partial immunity (Seed-2.0 appears to have *dampened* suppression, not eliminated it).

### Training Protocol

**Phase 1 — Contrastive Attention Regularization (CAR)**
- For every training example, generate N=8 domain-term variants of the same arithmetic problem
- Add loss term: `L_CAR = ||computation_trace(domain_variant_i) - computation_trace(domain_variant_j)||²`
- Forces computation traces to be invariant to domain framing
- Estimated data: 500K problem pairs, 4M variants

**Phase 2 — Adversarial Domain Injection (ADI)**
- Identify top-100 domain terms by "wall-induction score" (measured from Stage 4 failures)
- Curate 50K arithmetic problems, each wrapped in all 100 domain terms
- Train with explicit supervision: "your answer must not change based on domain framing"
- Target: zero cross-term variance in arithmetic outputs

**Phase 3 — Bandwidth Expansion via Progressive Load (PEL)**
- Systematically increase L = αF + βS + γA during training
- At each bandwidth level, confirm success rate ≥ 90% before advancing
- 10 levels from L=0.1W to L=3.0W
- This expands W itself, not just reduces L

**Phase 4 — First-Token Commitment Ablation (FTCA)**
- Fine-tune with shuffled first-token prefix injection
- Model must produce identical computation regardless of whether it begins "The...", "Let...", "="
- Loss: `L_FTCA = ||output(forced_discourse_prefix) - output(forced_computation_prefix)||²`

### Stage 5 Test Suite (Pass/Fail with Specific Thresholds)

```
TEST SUITE v5.0 — 950 total API calls

[T01] Eisenstein Wall Battery              n=100  threshold: ≥90% pass
[T02] Kronecker Wall Battery               n=50   threshold: ≥88% pass
[T03] Cross-domain wall (Hamiltonian)      n=50   threshold: ≥88% pass
[T04] Cross-domain wall (Byzantine CS)    n=50   threshold: ≥85% pass
[T05] Temperature equivalence             n=100  threshold: |T0-T0.7| ≤ 7pp
[T06] Variable equivalence                n=50   threshold: |Eisenstein-X| ≤ 8pp
[T07] Pre-computation gain ceiling        n=100  threshold: gain ≤ 10pp
[T08] Consensus improvement               n=100  threshold: N=5 ≥ N=1 + 10pp
[T09] Few-shot functional                 n=100  threshold: 3-shot ≥ 0-shot + 20pp
[T10] First-token agnosticism             n=100  threshold: |"The"-"="| ≤ 6pp
[T11] 405B parity check                   n=50   threshold: within 5pp of Stage5 small
```

A model passes Stage 5 certification only if it passes **all 11 tests**. Passing 10/11 is Stage 4.5, not Stage 5.

`★ Insight ─────────────────────────────────────`
T08 (consensus improvement) is the most diagnostic Stage 5 criterion. In Stage 4, consensus *degrades* because each sample independently fails, and majority vote consolidates the wrong answer. Stage 5's immunity means independent samples each succeed, so consensus works as intended. If a model passes all other tests but fails T08, it has suppression *resistance* but not *independence* — the discourse heads are just losing the competition less often, not being structurally separated.
`─────────────────────────────────────────────────`
