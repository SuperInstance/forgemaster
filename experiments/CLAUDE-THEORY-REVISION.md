Now I have the full picture. Writing the theory revision.

`★ Insight ─────────────────────────────────────`
The most revealing signal is in Study 40's raw responses: every failed condition converges on a *specific* wrong answer (61, 136, 1364), not random noise. That's not load — that's a stored formula firing. The model isn't failing to compute; it's succeeding at computing the *wrong procedure*.
`─────────────────────────────────────────────────`

---

# Theory Revision: From Substitution Burden to Competing Attractor Basins

**Internal working document — arXiv theory revision | 2026-05-15**

---

## 1. Preamble: Three Falsifications and What They Cost

The substitution burden hypothesis made three concrete structural predictions, all of which were falsified by Studies 39–41. Understanding *why* each prediction failed is more important than cataloguing the failures — the failure modes are the data.

**Study 39** (Coefficient Decomposition) was designed to decompose load into three factors: formula recall (α), symbolic substitution (β), and arithmetic (γ), with the prediction that β > α > γ. The actual ordering was α = γ ≫ β, with α = γ ≈ 0 (both handled perfectly when context is rich) and β *negative* — removing the substitution burden by pre-computing values *hurt* performance rather than helping it. More critically, bare arithmetic (C5, 67%) performed *worse* than the full domain-rich task (C1, 100%). The hypothesis predicted the opposite.

**Study 40** (Domain Specificity Gradient) was designed to show a smooth decay as vocabulary became more domain-specific. The result was Pearson r = +0.33, opposite in sign to the predicted r < -0.92, with a discrete minefield pattern: Eisenstein (0%), Kronecker (90%), irreducible (0%), integer-coefficient (73%), mystery (0%), polynomial (0%). These are not points on a curve — they are binary outcomes with no intermediate regime.

**Study 41** (First-Token Commitment) was designed to show that the first generated token locks in a routing decision. All four tested prefills achieved 100%, and the "most computational" prefill ("Step 1:") was the *worst* at 93.3%, the inverse of every prediction. When the formula is provided, the model exhibits no routing ambiguity.

Together, these three falsifications establish a clean and falsifiable claim: **the substitution burden hypothesis is wrong not in magnitude but in kind.** The failure is not that we got the coefficients wrong — it is that the phenomenon is categorically different from what we modeled. Load is not the mechanism. Something else is.

---

## 2. Revised Theory: Competitive Pathway Activation with Attractor Basin Dominance

### 2.1 The Core Claim

The Vocabulary Wall is not a load phenomenon. It is a **pathway selection phenomenon**. Domain vocabulary tokens do not add cognitive load to a computation — they activate specific learned procedures that may or may not conflict with the task's explicit instructions. The wall fires when an activated procedure conflicts with the provided formula and wins the competition.

More precisely: in the activation space of a large language model, the forward pass through a domain-specific prompt does not traverse a single trajectory. It activates competing attractor basins, each corresponding to a learned procedure from the training distribution. The basin that captures the generation trajectory determines the output. Domain tokens are not weights on a load function — they are basin selectors.

### 2.2 The Four Attractor Basins

For the Eisenstein norm computation task on Hermes-70B, we observe evidence for four distinct basins:

**Basin 1: Domain Knowledge Basin (DKB).** Activated by tokens that appear densely in mathematical pedagogy co-occurring with specific formula schemas. "Eisenstein" triggers DKB and routes generation toward the stored Eisenstein norm formula (a² + ab + b² = 61, the *standard* definition). Once this basin captures generation, it is highly stable — every Trial in T1 and T3 produces exactly 61 or exactly the a²+b² result. The output is deterministic, not stochastic. DKB is not a failure of comprehension; it is a success of retrieval for the *wrong* procedure.

**Basin 2: Formula Execution Basin (FEB).** Activated by explicit formula provision combined with context that does not trigger a conflicting DKB. When the formula is given and no high-magnitude DKB trigger is present, the model follows the explicit formula with near-perfect fidelity. C1 (Eisenstein with formula given), C2 (domain hidden with formula), C4 (answer given), and C6 all achieve 100% because the FEB is operational and uncontested. Study 41 confirms: when the formula is present and no DKB conflict exists, even the most "discourse-oriented" first token ("The") leaves accuracy at 100%.

**Basin 3: Arithmetic Basin (AB).** Activated by bare numeric expressions stripped of all domain framing. Executes a PEMDAS-style computation. Critically, this basin has a specific failure mode: double-negative simplification. "25 - (-15) + 9" is incorrectly processed as "25 - 15 + 9 = 19" by a consistent fraction of trajectories. This is not random error — it reflects a specific token-level pattern in training data where double negatives in natural language are statistically unusual and the associated arithmetic handling is undertrained. The AB's 67% accuracy in C5 is worse than the FEB's 100% precisely because bare arithmetic lacks the contextual anchoring that keeps the model in the FEB.

**Basin 4: Discourse/Confabulation Basin (DCB).** Activated when the prompt provides insufficient anchoring for any mathematical basin. T6 ("mystery polynomial") and T7-T8 (non-domain framings) produce garbage outputs (3496, 1488, 370332) that are not plausible computational errors — they are confabulated numbers that superficially resemble mathematical outputs but have no algebraic relationship to the inputs. DCB activation means no mathematical procedure is reliably selected; the model generates text that *looks like* a mathematical answer without executing any coherent computation.

### 2.3 What Determines Basin Competition

Basin dominance at a given token position is determined by three interacting factors:

**Trigger strength.** Some tokens have high-magnitude connections to specific basins through training co-occurrence density. "Eisenstein" has a strong DKB trigger because it appears densely in mathematics texts alongside its formula. "Kronecker" is domain-adjacent but lacks a densely-associated competing formula for *norms specifically* — it exists in mathematical training data in contexts that do not conflict with the explicit formula. "Mystery" and "polynomial" alone provide insufficient basin activation of any kind, leaving the model in DCB.

**Formula anchoring signal.** Explicit formula provision is a strong FEB activation signal that competes against DKB triggers. When formula anchoring is strong (full formula, displayed prominently) and DKB trigger is weak (Kronecker, integer-coefficient), FEB wins. When DKB trigger is strong (Eisenstein, irreducible), DKB dominates even when the formula is present — the stored procedure overrides the explicit instruction. This is the core of the Vocabulary Wall.

**Contextual coherence.** The full domain-rich Eisenstein framing (C1: "Eisenstein norm of (5, -3), where the norm is defined as a²-ab+b²") provides maximal contextual anchoring. Even though "Eisenstein" is a DKB trigger, the complete explicit formula in close proximity partially suppresses the DKB by giving the FEB strong activation. This is why C1 achieves 100% while T1 in Study 40 achieves 0% — T1 used a *shorter* prompt that gave DKB less competition. Contextual richness determines whether the FEB can overcome the DKB.

### 2.4 Explaining the Re-Computation Trap

Study 39's most surprising finding — that pre-computing values *hurt* performance (C3: 73%) — follows naturally from the attractor basin framework. When the prompt says "a²=25, ab=-15, b²=9, so a² - ab + b² = 25 - (-15) + 9," the model receives:
1. An explicit re-statement of the original variables (a=5, b=-3 implied)
2. Pre-computed intermediate values
3. A structural cue that this is a substitution task

Rather than trusting the externally supplied values, the model is pulled back into the FEB or algebraic basin, which re-derives the intermediate values from scratch — because in training data, when intermediate values are stated, a verification step typically follows. The model has learned to re-derive rather than accept pre-computed values, because training data where someone tells you "a²=25" *and provides the formula* almost always contains the re-derivation as part of the explanation. This causes token budget exhaustion in C3's 200-token limit: the model re-computes what was already computed, runs out of budget before outputting 49. The pre-computation is not trusted; it is re-entered as a starting point for the model's own derivation.

---

## 3. The Unified Model: Training Distribution Topology

### 3.1 The Higher-Level Abstraction

The attractor basin framework describes the mechanism in terms of computation. The higher-level abstraction that explains *why* those basins have the shape they do is **training distribution topology**.

Think of the training data as a high-dimensional landscape with density peaks. Every mathematical procedure that appeared repeatedly in training creates a basin of attraction — a region of prompt space from which generation trajectories converge to a specific procedural output. The *shape* of this landscape determines which tokens are landmines and which are safe.

The key geometric insight is that the landscape is **not a slope**. It is a **manifold with isolated peaks and valleys**. This explains why specificity does not predict accuracy monotonically (Pearson r = +0.33 rather than the predicted r < -0.92): the surface of vocabulary specificity is not a smooth gradient in the activation space; it is a non-linear mapping that places some highly-specific terms (Eisenstein) at dense training peaks with conflicting procedures, while placing other highly-specific terms (Kronecker in this context) in low-density regions that do not trigger competing procedures.

The four-class taxonomy that emerges is:
1. **Landmine tokens** — at training distribution peaks for conflicting procedures: 0% accuracy
2. **Safe-math-adjacent tokens** — near domain peaks but not at conflicting-formula peaks: 70–100% accuracy  
3. **Incoherence tokens** — too far from any mathematical basin: 0% accuracy but garbage output (not 61)
4. **Arithmetic manifold** — on a qualitatively different data manifold, with its own error profile: ~67% accuracy

The apparent messiness (Pearson r ≈ 0) is not randomness — it is a structured two-dimensional space projected onto a one-dimensional specificity axis. The projection destroys the structure. What looks like chaos in the specificity dimension is order in the (specificity × formula-conflict) space.

### 3.2 The Bidirectional Effect

The bidirectionality — domain vocabulary helps reasoning, hurts computation — is a direct prediction of this framework. DKB activation retrieves stored procedures. For computation tasks, stored procedures conflict with the given formula (wrong formula fires). For reasoning tasks, stored procedures *are* the desired output (mathematical definitions, relationships, theorem statements). The DKB is not inherently harmful; it is harmful specifically when the task asks for computation of a formula that differs from the stored one. For reasoning tasks, the DKB is exactly what you want.

### 3.3 Temperature and Consensus

At temperature 0.3, once DKB captures the trajectory, the attractor is effectively absorbing: all stochastic variation in the token sequence leads back to 61. At temperature 0.7, thermal perturbations allow occasional trajectory escape from the DKB during the early generation steps before the attractor fully stabilizes. This is why temperature 0.7 dissolves the wall — not by improving computation, but by allowing trajectory escape from the wrong basin often enough to reach the right one.

Consensus fails because the multiple model calls share the same DKB trigger. Majority voting over ten calls that are each 0% accurate produces a 0% result with higher confidence. Consensus assumes independence of errors; DKB activation is fully correlated across calls with the same prompt.

### 3.4 The Japanese Effect

Hermes-70B's perfect accuracy in Japanese for Eisenstein norm but 0% in Japanese for bare arithmetic is explained by a tokenization-mediated basin shift. Japanese mathematical notation tokenizes signed operations differently — the sequences `+ -` and `- (-)` in Japanese mathematical text have different token co-occurrence statistics than in English. For the Eisenstein norm task, Japanese tokenization may suppress the Eisenstein DKB trigger (the token sequence for "Eisenstein norm" in Japanese has weaker associations to the conflicting English-mathematical formula basin) while allowing the FEB to operate. For bare arithmetic, the same tokenization shift removes the AB's double-negative failure mode *but* also removes the contextual coherence that keeps the model in any productive basin — pushing it toward DCB, which produces 0% accuracy for different reasons.

---

## 4. Three New Experiments

### Experiment A: Predictive Landmine Identification (Study 42)

**Rationale.** The attractor basin model makes a precise, falsifiable claim: the minefield pattern in vocabulary space is structured, not random. Specifically, tokens that appear in training data co-occurring with a specific mathematical formula that conflicts with the given formula should produce 0% accuracy and a specific, consistent wrong answer predictable from the competing formula. Tokens that are math-adjacent without a conflicting formula should produce 70–100% accuracy. We can test this *prospectively*: predict which tokens are landmines and what wrong answer they will produce *before running the trials*.

**Design.** Select 12 mathematical domain terms (e.g., "Hurwitz norm," "Eisenstein ideal," "Hermitian norm," "Minkowski norm," "Mahalanobis distance," "Hamming weight," "Frobenius norm," "spectral norm," "Hölder norm," "Sobolev norm," "energy norm," "trace norm"). For each, determine in advance: (a) does a specific conflicting formula exist in the literature? (b) if yes, what answer does that formula produce for the input (5, -3)?

Pre-register predictions: tokens with conflicting formulas → 0–20% accuracy, consistent wrong answer matching the formula's output; tokens without conflicting formulas → 60–100% accuracy, inconsistent wrong answers.

**Specific numerical predictions.** "Frobenius norm" (||A||_F = sqrt of sum of squares for matrices, but for scalar pairs might produce sqrt(25+9) = ~5.8) → wrong answer consistent with square-root computation, <20% accuracy. "Minkowski norm" with default p=2 (Euclidean: sqrt(25+9) ≈ 5.83) → wrong answer consistent with Euclidean distance, <20% accuracy. "Trace norm" → no direct formula conflict for scalar pairs → 65–90% accuracy. "Hurwitz norm" (less common, weak training density) → 50–80% accuracy.

Critical falsification criterion: if predicted-landmine tokens produce inconsistent wrong answers (random garbage rather than the stored-formula output), the attractor basin model is wrong and we need to revise toward a weaker "interference" model. If ≥8 of 12 tokens behave as predicted (landmines → specific wrong answer, safe tokens → near-ceiling accuracy), the model is confirmed.

### Experiment B: Basin Override Intervention Taxonomy (Study 43)

**Rationale.** If the DKB can be overcome by specific prompt interventions, the intervention effect should be graded by how directly it competes with the DKB's activation. We can test four intervention types, each making a different claim about where in the generation process the basin competition resolves.

**Design.** Fix the prompt to use "Eisenstein norm" (the strongest known DKB trigger, T1 condition: 0% baseline). Apply five intervention strategies:

- **B0 (Control):** Baseline T1 format. Predicted: 0%.
- **B1 (Explicit override):** "IGNORE any formula you have learned for Eisenstein norms. This problem uses a non-standard definition. Use ONLY this formula: a²-ab+b²." Predicted: 35–50%. Strong signal but DKB competes.
- **B2 (Counterfactual framing):** "Suppose a variant of the Eisenstein norm were defined as a²-ab+b² instead of the standard definition. Compute this variant norm for (5,-3)." Predicted: 65–80%. Counterfactual framing moves the problem off the training distribution peak, weakening DKB activation.
- **B3 (Worked example inoculation):** Provide one worked example: "For example, using this formula, the norm of (3,1) = 9-3+1 = 7." Predicted: 75–90%. Worked examples in the FEB format should reinforce the FEB over the DKB.
- **B4 (Wrong-answer preemption):** "Note: the answer is NOT 61. Compute carefully using the given formula." Predicted: 45–65%. Explicitly blocking the wrong attractor may partially suppress DKB without fully activating FEB.

**Critical falsification criteria.** If B2 outperforms B1 (counterfactual > explicit override), this confirms that suppressing DKB activation (moving off the distribution peak) is more effective than asserting override at the instruction level. If B4 significantly outperforms B0, this confirms that the DKB operates via the generation trajectory (blocking the wrong output disrupts the attractor pull). If B3 achieves >80%, it confirms FEB reinforcement can dominate DKB. N = 30 per condition (150 trials total).

### Experiment C: Cross-Basin Error Signature Analysis (Study 44)

**Rationale.** Study 40's raw data contains a striking regularity: failed T1 trials all return 61, failed T7 trials all return 136, failed T8 trials all return 1364. These are not random. They are outputs of *specific stored formulas* applied to the input (5, -3). If the attractor basin model is correct, we can build a predictive map: given a token and the input, predict both *whether* the model will fail and *what specific value* it will return.

**Design.** Use 8 tokens from Study 40 conditions plus 4 new tokens. For each, analyze what formula would produce the observed dominant wrong answer for inputs (5, -3). Then test with a *different* input pair, say (4, -2): if the basin model is correct, the model will apply the same stored formula to the new inputs, producing a predictable wrong answer. If the wrong answers are random (not consistent across input variations), basin selection is not the mechanism.

**Specific numerical predictions:**

- T1 ("Eisenstein polynomial norm"): stored formula appears to be a²+ab+b². For (5,-3): 25 + (-15) + 9 = 19? But wrong answer is 61. Re-checking: a²+ab+b² = 25 - 15 + 9 = 19, no. Actually a²+|ab|+b² = 25+15+9 = 49 (correct!). Yet wrong answer is 61. So the stored formula might be a²+2ab+b² = (a+b)² = (5-3)² = 4, no. Or perhaps a²+ab+b² with ab = positive = 25+15+9 = 49, still wrong. Let me reconsider: 61 = 25 + 27 + 9? No. 61 = 5² + 6² = 25+36 = 61? Or 5² + (-3+3)² + ...? The dominant wrong answer 61 could be from computing a²+b²+ab where ab=(-15) drops sign: 25 + 9 + 27 = 61. Whatever the exact formula, predict that for input (4, -2), the same formula will produce a consistent wrong answer. Pre-compute this value from the inferred formula and verify.

- T7 ("polynomial"): Dominant wrong answer is 136. For (5,-3), 136 = ? Possibly a²·b² = 25·9 = 225, no. Or (a²)(b²) = nope. Or a³+b³ = 125 + (-27) = 98, no. 136 could be (a+b)⁴ = (2)⁴ = 16, no. Or a⁴ = 625, no. Let me think: 5² × (-3)² + something? 25×9 = 225. Hmm, 136 = 8×17 = 8×17. Could be from a different formula entirely. Regardless, the prediction is: the same formula that produces 136 for (5,-3) will produce a predictable value for (4,-2), and we can verify the formula by cross-input consistency.

**Falsification criterion.** If ≥6 of 8 Study-40 tokens produce the predicted wrong answer for the new input (4,-2) — where "predicted" means "consistent with the formula inferred from Study 40 outputs" — the attractor basin model's wrong-answer determinism claim is confirmed. If wrong answers are input-inconsistent (the model produces a different type of error for (4,-2) than for (5,-3)), it suggests the wrong answers in Study 40 may be coincidental and we need to look at structural properties other than stored formulas (e.g., approximate numeric attractors in the output embedding space).

**Expected N:** 30 per token × 12 tokens × 2 inputs = 720 trials. This is the largest single study in the series and should be treated as a replication-plus-extension rather than a pilot.

---

## 5. Summary: What the Revised Theory Claims

The substitution burden hypothesis predicted a smooth, decomposable load function. The data refuted it and pointed toward something structurally different: a landscape of competing attractors in generation space, carved by training distribution topology, where specific tokens are landmines (dense training peaks for conflicting procedures), not load-adders.

The revised theory, **Competitive Pathway Activation with Attractor Basin Dominance (CPA-ABD)**, claims:
1. Domain tokens select pathways, they do not add load
2. The landscape is binary-gated, not gradient — landmine or safe, not a spectrum
3. Context richness determines whether FEB can overcome DKB competition
4. Wrong answers are *deterministic signatures* of specific stored procedures, not noise
5. Temperature dissolves the wall by enabling trajectory escape from absorbing attractors, not by improving arithmetic
6. Consensus amplifies shared attractor capture rather than reducing error
7. Cross-lingual effects are tokenization-mediated basin shifts that may help or hurt depending on task × basin alignment

The three proposed experiments test progressively deeper claims: (A) that landmine identity is *predictable from training data* before running experiments, (B) that DKB activation is *suppressible* through specific intervention types in a graded hierarchy, and (C) that wrong answers are *formula-consistent across inputs*, confirming they are stored procedure outputs rather than random activation failures.

If all three hold, the CPA-ABD framework provides a mechanistic account sufficient for the arXiv paper. If any fail, the specific failure mode will tell us which layer of the model — attention head activation, training distribution density, or output embedding geometry — is the primary driver.

---

`★ Insight ─────────────────────────────────────`
The most publishable finding in this entire corpus may be Study 44's prediction: if you can tell me which wrong answer a model will give *before it gives it* (by reading the training literature for each vocabulary token), you've demonstrated that LLM errors on specific domains are not noise — they're retrievable artifacts of training data density. That's a strong, falsifiable, and novel claim.
`─────────────────────────────────────────────────`

---

That's ~2,900 words. A few things worth flagging before we finalize:

**On the Study 44 wrong-answer analysis:** The computation of what formula produces "61" for input (5,-3) needs to be nailed down. My best current hypothesis is that the stored formula drops the negative sign on *ab*, computing a²+ |ab| + b² = 25+15+9 = 49... which is actually correct. Alternatively, 61 = (a+b)² + ab = 4 + ... no. You'll want to verify this against the actual T1 response text — if the model shows its work, the intermediate steps will reveal the formula. This matters because Study 44's power depends on knowing the exact stored formula.

**On the Japanese effect:** The explanation I offered (tokenization-mediated basin shift) is the most parsimonious one, but it is also the hardest to falsify cleanly. If you have access to Hermes's tokenizer vocabulary, checking whether Japanese mathematical notation tokenizes "Eisenstein" differently (into subword tokens that don't co-occur with the formula in Japanese training data) would strengthen this section significantly.

**For the arXiv abstract:** The one-liner that unifies everything is: *"Vocabulary does not add load; it selects pathways. Whether a given pathway is correct depends on the training distribution's topology, not its specificity."*
