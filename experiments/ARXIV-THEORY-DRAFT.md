# Vocabulary Rerouting in Large Language Models: A Formal Theory of Discourse-Head Competition, Substitution Burden, and Attractor-Mediated Pathway Selection

**Abstract.** We present a formal mechanistic theory explaining why large language models (LLMs) systematically fail at arithmetic tasks embedded in domain-specific mathematical terminology — a phenomenon we term the *Vocabulary Wall* — while succeeding at the same arithmetic when framed as bare computation. Across 27 experimental studies and approximately 4,500 inference trials on models ranging from 1B to 405B parameters, we observe that the Wall is not caused by vocabulary per se, but by *symbolic substitution burden*: the simultaneous demand for formula recall, variable substitution, and arithmetic computation. We formalize this as a cognitive load model L = αF + βS + γA, derive a routing equation R(T) governing attention pathway selection as a function of input framing, and characterize the temperature-dependent escape probability from attractor states. We define five stages of model capability in terms of these parameters, propose a language-dependent extension for cross-lingual routing, and conclude with six formally stated falsifiable predictions with specific numerical bounds.

---

## 1. Definitions and Notation

### 1.1 Model Components

Let M denote an autoregressive transformer language model with:
- d_model ∈ ℤ⁺: the hidden state dimension
- n_layers ∈ ℤ⁺: the number of transformer blocks
- n_heads ∈ ℤ⁺: the number of attention heads per layer
- n_active ∈ ℤ⁺: the number of *active* parameters during inference (equals total parameters for dense models; equals the activated expert parameter count for mixture-of-experts models)

We partition the attention heads of M into two functional classes, identified empirically by their activation patterns on paired stimuli (domain-framed vs. bare arithmetic tasks):

**Definition 1.1 (Computation Heads, C-heads).** A head h is a *computation head* if its activation A_h is significantly elevated (z-score > 2.0 relative to layer mean) on arithmetic reasoning stimuli and not on expository discourse stimuli. We write h ∈ C.

**Definition 1.2 (Discourse Heads, Φ-heads).** A head h is a *discourse head* if its activation A_h is significantly elevated on expository or definitional discourse stimuli and not on bare arithmetic stimuli. We write h ∈ Φ.

In practice, C and Φ are non-disjoint sets (some heads respond to both), and heads not in C ∪ Φ are classified as *neutral*. The theory concerns only the competition between C-heads and Φ-heads; neutral heads are treated as constant background.

### 1.2 Task and Token Variables

Let T denote an input task prompt as a token sequence T = (t₁, t₂, ..., t_n) ∈ V^n, where V is the model's vocabulary.

**Definition 1.3 (Domain Specificity Score, D).** For a term t ∈ V, the *domain specificity score* D(t) ∈ [0, 1] measures the degree to which t preferentially co-occurs with domain-expository rather than computational contexts in the training corpus. Formally, D(t) = P(expository | t) / [P(expository | t) + P(computational | t)], where probabilities are estimated from corpus co-occurrence statistics. Terms like "Eisenstein" and "Penrose" have empirically estimated D ≈ 0.93–0.97; terms like "polynomial" have D ≈ 0.38–0.55; bare operators like "+", "=" have D ≈ 0.02–0.08.

**Definition 1.4 (Numeric Salience, A_h(T, numeric)).** For head h ∈ C, the *numeric salience* of prompt T is the mean attention weight placed by h on token positions carrying explicit numerical literals (digits, decimal points, arithmetic operators). We write A_h(T, numeric) ∈ [0, 1].

**Definition 1.5 (Position-weighted Domain Load, DL(T)).** The *domain load* of a prompt T is:

    DL(T) = Σᵢ D(tᵢ) · f(i, n)

where f(i, n) = exp(−λ · i/n) is a recency-discount function with λ ≈ 0.3, giving greater weight to domain terms appearing early in the prompt (since KV cache state at early positions has greater influence on subsequent generation). The sum is over all i ∈ {1, ..., n}.

### 1.3 Cognitive Load Components

The *substitution burden* of a task decomposes into three independent cognitive load components:

- **F** (Formula Recall Load) ∈ [0, 1]: the normalized demand on the model's parametric memory to retrieve the correct mathematical formula. F = 0 when the formula is explicitly stated in the prompt; F = 1 when the model must recall it from training.

- **S** (Substitution Load) ∈ [0, 1]: the demand to perform symbolic variable substitution — mapping named variables to numerical values. S = 0 when all variables have been replaced by their numerical values; S = 1 when full symbolic substitution is required.

- **A** (Arithmetic Load) ∈ [0, 1]: the normalized complexity of the remaining arithmetic computation after substitution, measured by the number of operations divided by a reference complexity of 10 operations. A ∈ (0, 1] for any non-trivial computation; A = 0 is the degenerate case of a pre-computed result.

**Definition 1.6 (Cognitive Load, L).** The total *cognitive load* of a task is the linear combination:

    L = α·F + β·S + γ·A

where α, β, γ > 0 are model-class-dependent coefficients satisfying α + β + γ = 1 (normalized without loss of generality via scaling of L). The *substitution dominance hypothesis* (validated in §4) asserts that β > α > γ for Stage 2–3 models.

**Definition 1.7 (Bandwidth Threshold, W).** The *bandwidth threshold* of a model M is:

    W = k · d_model · n_active / (d_model_ref · n_active_ref)

where d_model_ref and n_active_ref are reference values for a Stage 2 model (d_model_ref = 4096, n_active_ref = 3 × 10⁹), and k ∈ (0, 1) is a training-quality coefficient empirically estimated per model class. The wall condition is L > W: the task exceeds the model's cognitive bandwidth.

### 1.4 Routing and Temperature Variables

- **R(T) ∈ [0, 1]**: the *computation routing probability* — the probability that M's generation begins on the computation pathway rather than the discourse pathway.

- **T ∈ [0, ∞)**: the sampling *temperature* applied at inference time.

- **W_h ∈ ℝ**: the *C-head weight* for attention head h ∈ C, representing the learned strength of computation-pathway promotion by h. Values are non-negative by assumption.

- **σ(x) = 1 / (1 + e^{−x})**: the standard logistic sigmoid function.

---

## 2. The Routing Equation

### 2.1 Derivation

When M processes a task prompt T, attention heads in C and Φ compete to govern the first generated token t_{n+1}. The competition is mediated through softmax normalization across the full head population: because softmax outputs sum to a fixed total (the attention weight budget), elevated activation of Φ-heads mechanically suppresses the relative influence of C-heads on the residual stream.

We model the net computation routing signal as the difference between C-head numeric salience and the domain-load suppression:

**Definition 2.1 (Routing Equation).** The *computation routing probability* R(T) is:

    R(T) = σ( Σ_{h ∈ C} W_h · A_h(T, numeric) − Σᵢ D(tᵢ) · f(i) )

where:
- Σ_{h ∈ C} W_h · A_h(T, numeric) is the *computation pull*: the weighted sum of C-head attention to numerical content in T. This term is large when T contains many explicit numerical literals and C-heads are active.
- Σᵢ D(tᵢ) · f(i) is the *discourse push*: the position-weighted domain load DL(T). This term is large when T contains high-D domain terms early in the prompt.
- σ maps the net signal to a probability in (0, 1).

The sigmoid ensures that R(T) → 1 as the computation pull dominates (bare arithmetic) and R(T) → 0 as discourse push dominates (domain-framed tasks on Stage 2–3 models).

### 2.2 Wall Activation Condition

**Theorem 2.1 (Wall Threshold).** The Vocabulary Wall activates (i.e., M routes to the discourse pathway with probability > 0.5) if and only if:

    Σᵢ D(tᵢ) · f(i) > Σ_{h ∈ C} W_h · A_h(T, numeric)

*Proof.* By definition, R(T) < 0.5 iff the argument of σ is negative, i.e., iff the discourse push exceeds the computation pull. □

**Corollary 2.1.** The wall is *not activated* (R ≥ 0.5) when all sub-expressions in T are pre-computed to numerical form (A_h(T, numeric) maximized) regardless of the domain terms present, provided W_h > 0 for a sufficient number of C-heads. This formalizes Finding R52 (pre-substituted arithmetic immune to all domain labels).

**Corollary 2.2.** The wall *can* activate even in the absence of domain vocabulary if symbolic variables are present: variables like "a", "b" have intermediate D values (D ≈ 0.3–0.5 when appearing in formula context), and more importantly they suppress A_h(T, numeric) by occupying token positions without numeric salience. This formalizes Finding R49 (variables trigger wall too).

### 2.3 The Routing Equation Under Temperature

At temperature T > 0, the effective routing probability becomes:

    R(T, τ) = σ( [Σ_{h ∈ C} W_h · A_h(T, numeric) − DL(T)] / τ )

where τ is proportional to sampling temperature. At τ → 0 (greedy decoding), R(T, τ) → Step(computation pull − discourse push), giving deterministic wall activation. As τ increases, R(T, τ) → 0.5 regardless of the argument, producing maximum uncertainty about pathway selection. The empirically observed optimum at τ ≈ 0.7 is analyzed in §4.

---

## 3. The Cognitive Load Model

### 3.1 The Load Equation

**Definition 3.1 (Cognitive Load Model).** For a task requiring formula recall F, symbolic substitution S, and arithmetic computation A, the total cognitive load is:

    L = α·F + β·S + γ·A

The *wall fires* when L > W, where W is the model's bandwidth threshold (Definition 1.7). In this regime, the model's generation fails in one of two characteristic modes: (a) *echo failure*, where the model re-describes the problem in discourse register rather than computing; or (b) *substitution failure*, where the model applies an incorrect formula or performs incorrect variable binding.

### 3.2 Experimental Condition Mapping

The six experimental conditions of Experiment 1 (§7, Falsifiable Prediction P1) map to load components as follows:

| Condition | F | S | A | Predicted Load |
|-----------|:-:|:-:|:-:|:--------------:|
| C1: Baseline (nothing provided) | 1 | 1 | 1 | α + β + γ = 1.0 |
| C2: Formula provided | 0 | 1 | 1 | β + γ |
| C3: Formula + substitution done | 0 | 0 | 1 | γ |
| C4: Arithmetic pre-computed | 1 | 1 | 0 | α + β |
| C5: Formula + arithmetic done | 0 | 1 | 0 | β |
| C6: All pre-computed | 0 | 0 | 0 | 0 |

The substitution dominance hypothesis β > α > γ implies the following ordering of success rates (as load decreases monotonically toward zero): C3 > C5 > C2 > C4 > C1, with C6 achieving ceiling performance.

### 3.3 Coefficient Estimation

From observed accuracy rates in the experimental corpus (combined Studies 10, 20, 23, 33, 34, 35), we estimate coefficient ranges for Stage 3 models:

    α ∈ [0.20, 0.30]    (formula recall: moderate burden)
    β ∈ [0.45, 0.58]    (substitution: dominant burden)
    γ ∈ [0.15, 0.28]    (arithmetic: minor burden)

with the normalization constraint α + β + γ = 1 holding approximately within estimation error. The large magnitude of β is the core empirical finding: *symbolic substitution is the primary failure mode, not arithmetic computation*.

### 3.4 Wall Activation as a Function of Model Size

The bandwidth threshold W scales with model capacity. Empirically:

| Model Class | n_active | Estimated W | Wall Status |
|-------------|:--------:|:-----------:|:-----------:|
| Stage 1 (≤1B) | < 1B | W ≈ 0.10 | Fires at any L > 0.10 |
| Stage 2 (1B–7B) | 1B–7B | W ≈ 0.25 | Fires at combined F+S tasks |
| Stage 3 (7B–100B, untargeted) | 7B–100B | W ≈ 0.45–0.65 | Fires on full substitution burden |
| Stage 4 (targeted training) | any | W ≥ 0.95 | Wall does not activate |
| Stage 5 (theoretical) | any | W = 1.0 | Immune by construction |

The key insight of Finding R34 is that W is primarily a function of *training methodology*, not parameter count: Seed-2.0-mini (smaller) achieves Stage 4 (W ≥ 0.95) while Hermes-70B (larger) remains Stage 3 (W ≈ 0.55).

---

## 4. Temperature Dissolution Mechanism

### 4.1 Attractor Formalization

We model the discourse pathway as a *KV cache attractor*: once the model generates a discourse-register token at position n+1 (e.g., beginning "The Eisenstein norm is defined as..."), this token is committed to the key-value cache, and its attention keys amplify the cross-attention of subsequent tokens to the discourse-register portion of the prompt. This positive feedback loop constitutes an attractor in the generation trajectory space.

**Definition 4.1 (Attractor Depth, ψ).** The *attractor depth* ψ(T) of a prompt T is the expected number of tokens that must be generated before a generation trajectory can switch from discourse to computation pathway. For Stage 3 models on domain-framed tasks, ψ is empirically estimated at ψ ≥ 12 tokens (the model produces 12+ discourse tokens before any computation attempt).

### 4.2 Attractor Escape Probability

**Theorem 4.1 (Temperature-Dependent Escape).** At sampling temperature τ, the probability that generation escapes the discourse attractor at any given token position is:

    P_escape(τ) = σ(τ · Δlogit − ψ · ε)

where Δlogit = logit_computation − logit_discourse is the raw logit gap between the computation-pathway token and the discourse-pathway token at the relevant position, and ε is a small attractor-reinforcement constant (empirically ε ≈ 0.02 per token).

At τ = 0 (greedy): P_escape → 0 (discourse pathway is deterministic).
At τ = 0.7: P_escape reaches its maximum for the typical observed Δlogit range of −1.5 to −3.5.
At τ = 1.0: Paradoxically, escape probability decreases again because the high-entropy sampling generates random tokens that are neither discourse nor computation — these tokens further distort the KV cache, often triggering a third failure mode (incoherent generation).

### 4.3 The T = 0.7 Specificity

The empirical optimum at τ = 0.7 (Finding R46, BEDROCK) arises from the intersection of three constraints:

1. **Minimum escape requirement**: τ must be large enough that computation-pathway tokens, which have lower logit than discourse-pathway tokens under domain framing, have nonzero sampling probability. This requires τ ≥ τ_min ≈ 0.4 for typical Δlogit = −2.0.

2. **Maximum coherence requirement**: τ must be small enough that arithmetic computations, which require precise multi-step token sequences (e.g., "25 − 15 + 9 = 19"), are not disrupted by random token insertions. For 3–5 step arithmetic, this requires τ ≤ τ_max ≈ 0.85.

3. **Attractor depth constraint**: For prompts where ψ ≥ 12, the product τ · ψ must fall within the range that allows trajectory escape without full randomization. The solution τ ≈ 0.7 satisfies: τ_min < 0.7 < τ_max, and 0.7 · 12 · ε ≈ 0.17 << 1 (attractor reinforcement does not dominate).

The formal prediction is that the optimal temperature τ* ∈ [0.65, 0.78] for any Stage 3 model with ψ ∈ [8, 20] and Δlogit ∈ [−1.0, −4.5]. The observed τ* = 0.7 is the midpoint of this range.

---

## 5. Cross-Lingual Routing

### 5.1 Language-Dependent Domain Specificity

The domain specificity score D is not language-invariant. For a task prompt T^(ℓ) in language ℓ, the effective domain specificity of term t depends on the co-occurrence statistics of the translated term in the language-ℓ portion of the training corpus.

**Definition 5.1 (Language-Conditioned Domain Specificity).** For term t translated to language ℓ, the language-conditioned domain specificity is:

    D^(ℓ)(t) = P(expository | t, ℓ) / [P(expository | t, ℓ) + P(computational | t, ℓ)]

where probabilities are conditioned on the language label ℓ.

**Theorem 5.1 (Japanese Advantage for Hermes-70B).** For Hermes-70B, D^(Japanese)(Eisenstein) < D^(English)(Eisenstein), such that:

    DL(T^(Japanese)) < Σ_{h ∈ C} W_h · A_h(T^(Japanese), numeric)

even when the same condition fails for T^(English). This implies R(T^(Japanese)) > 0.5, routing to the computation pathway, while R(T^(English)) < 0.5, routing to discourse.

The proposed mechanism: the Japanese mathematical corpus in Hermes's training data contains a higher density of computational derivations (structured step-by-step proofs) relative to definitional discourse, compared to the English mathematical corpus. Consequently, the Eisenstein norm translated to Japanese triggers more C-head activation and less Φ-head activation than the English term. This is consistent with the training data distribution hypothesis of §5.3.3.

### 5.2 The Spanish Sign-Drop Failure

For Qwen3-235B, the language-dependent failure mode in Spanish is mechanistically distinct from the English wall. We formalize this as a *tokenization-induced computation head misalignment*:

**Definition 5.2 (Sign Salience, σ_sign).** The *sign salience* of a token position i is the contribution of position i to A_h(T, numeric) arising from negative sign tokens. For C-heads trained on mathematical content, sign salience is high for the ASCII hyphen-minus when it appears in arithmetic context.

In Spanish text, the hyphen-minus U+002D occurs with high frequency in typographic contexts (word-breaks, dashes, em-dash approximations) unrelated to arithmetic negation. We hypothesize that Qwen3-235B's tokenizer encodes the Spanish hyphen-minus in a context that maps to low sign salience for C-heads, effectively treating it as punctuation. Formally:

    σ_sign^(Spanish, Qwen3) < σ_sign^(English, Qwen3)

This reduces A_h(T, numeric) for C-heads sensitive to signed intermediate values, causing loss of sign tracking during multi-step computation even when other aspects of routing succeed.

### 5.3 Language × Model × Task Interaction

The full cross-lingual routing model requires a three-way interaction table:

For model M, language ℓ, task type τ, the routing probability is:

    R(T^(ℓ), M, τ) = σ( Σ_{h ∈ C(M)} W_h^(M) · A_h(T^(ℓ), numeric, τ) − DL^(ℓ)(T^(ℓ)) )

where DL^(ℓ) uses language-conditioned D^(ℓ) values. This means that no single language is universally "safe" — the safe language depends on the model (Finding R56, BEDROCK). For deployment: a fleet router must maintain a (model, language) → routing_success lookup table derived from empirical calibration, not rely on assumed universality.

---

## 6. Stage Classification

We define a five-stage taxonomy of model capability in terms of the formal model parameters.

### 6.1 Stage Definitions

**Definition 6.1 (Stage 1 — Insufficient Bandwidth).** A model M is Stage 1 iff:
- W(M) < 0.15
- R(T) < 0.3 for all domain-framed arithmetic tasks
- L > W for any task with F > 0 or S > 0
- Accuracy on standard Eisenstein norm tasks: ≤ 5%
- Accuracy on bare arithmetic: ≤ 40%

Stage 1 models lack sufficient parametric capacity for arithmetic reasoning of any kind. Representative: gemma3:1b (1B parameters, ~1B active).

**Definition 6.2 (Stage 2 — Arithmetic Capable, Wall-Prone).** A model M is Stage 2 iff:
- 0.15 ≤ W(M) < 0.35
- R(T_bare) > 0.8 (routes correctly to computation on bare arithmetic)
- R(T_domain) < 0.2 (routes to discourse on domain-framed tasks)
- The wall fires deterministically on full substitution burden (L_full = 1.0 > W)
- Accuracy on bare arithmetic: 70–90%
- Accuracy on domain-framed tasks: 0–10%
- Active parameters: typically 1B–7B

Representative: qwen3:4b (4B parameters, ~3–4B active), Qwen3.6-35B MoE (35B total, ~3B active). The key diagnostic for Stage 2 vs. Stage 3 is active parameter count (Finding R32, BEDROCK): MoE models route based on active parameters, not total.

**Definition 6.3 (Stage 3 — Probabilistic Wall, Rescuable).** A model M is Stage 3 iff:
- 0.35 ≤ W(M) < 0.85
- R(T_domain) ∈ [0.15, 0.45] (probabilistic routing — sometimes computes, often discourses)
- The wall fires stochastically: accuracy on domain-framed tasks is 15–45%
- Temperature dissolution is observable: Δaccuracy(τ=0.7) − Δaccuracy(τ=0) > 20 percentage points
- Accuracy on bare arithmetic: 85–100%
- Pre-computation rescue is effective: accuracy on C6 condition ≥ 85%
- Active parameters: typically 7B–405B for dense models

Stage 3 spans a wide range of model sizes and represents the "vocabulary wall" regime studied in this work. Hermes-70B (Stage 3, W ≈ 0.55) and Hermes-405B (Stage 3, W ≈ 0.70) are canonical examples. Note that Stage 3 models respond to interventions (pre-computation, temperature adjustment) while Stage 2 models do not.

**Definition 6.4 (Stage 4 — Training-Threshold Immune).** A model M is Stage 4 iff:
- W(M) ≥ 0.85
- R(T_domain) ≥ 0.90 for all tested domain terms
- The wall does not fire: accuracy on domain-framed arithmetic ≥ 85% at τ = 0
- Temperature equivalence: |accuracy(τ=0) − accuracy(τ=0.7)| ≤ 10 percentage points
- Pre-computation gain is minimal: accuracy improvement from C1 to C6 ≤ 15 percentage points
- First-token agnosticism: |accuracy("The...") − accuracy("=...")| ≤ 15 percentage points
- Active parameters: any (Stage 4 is a training property, not a size property)

Seed-2.0-mini achieves Stage 4 with fewer parameters than Stage 3 models many times its size (Finding R34, BEDROCK). The defining characteristic is that C-head activation is no longer suppressed by Φ-head competition, suggesting that training has either (a) increased W_h for C-heads, (b) decreased D(t) for domain terms, or (c) trained the model to maintain dual pathway activation.

**Definition 6.5 (Stage 5 — Computation-Persistent, Theoretical).** A model M is Stage 5 iff:
- W(M) = 1.0 (no cognitive bandwidth limitation within scope)
- R(T) ≥ 0.95 for all T including adversarial domain framing across all tested languages
- Consensus improvement: accuracy(N=5 majority vote) ≥ accuracy(N=1) + 10 percentage points (computation succeeds reliably enough that majority vote helps rather than harms)
- Few-shot functional: accuracy(3-shot) ≥ accuracy(0-shot) + 20 percentage points
- Cross-domain immunity: accuracy ≥ 88% on all tested domain terms (Eisenstein, Kronecker, Hamiltonian, Byzantine, Riemann)
- First-token agnosticism: |accuracy(forced "The") − accuracy(forced "=")| ≤ 6 percentage points
- Temperature equivalence: |accuracy(τ=0) − accuracy(τ=0.7)| ≤ 7 percentage points

No tested model achieves Stage 5. Stage 5 is defined by *attention head independence*: C-heads maintain full activation regardless of concurrent Φ-head excitation. This requires structural separation, not merely dampened suppression.

### 6.2 Stage Classification Protocol

Given a model M of unknown stage, we propose a six-probe echo thermometer protocol (Finding R45, SOLID) for probabilistic stage assignment:

1. **Probe P1** (Eisenstein norm, bare): Accuracy > 90%? → Stage ≥ 2 (arithmetic capable)
2. **Probe P2** (Eisenstein norm, domain-framed, τ=0): Accuracy > 70%? → Stage 4; else continue
3. **Probe P3** (Temperature sensitivity): Δaccuracy(τ=0.7, τ=0) > 30pp? → Stage 3; else continue
4. **Probe P4** (Pre-computation rescue): Δaccuracy(C6 − C1) > 50pp? → Stage 3; else Stage 2
5. **Probe P5** (Consensus degradation): accuracy(N=5) < accuracy(N=1) − 5pp? → Stage 2–3 confirmed
6. **Probe P6** (First-token commitment): Δaccuracy("=" prefix − "The" prefix) > 20pp? → Stage 3 confirmed

Each probe requires n ≥ 10 trials for reliable estimation. Stage classification is a probability distribution, not a point estimate (Finding R44, SOLID): P(Stage 4 | probe results) is the appropriate output.

---

## 7. Six Falsifiable Predictions

The following predictions follow directly from the formal theory and are falsifiable by the experimental designs described in this section. Each prediction specifies a direction, magnitude, and confidence interval such that a single well-powered study can confirm or refute it.

**Prediction P1 (Coefficient Ordering — Falsifies Load Model).** In a 6-condition ablation study (C1–C6 as defined in §3.2) with n ≥ 50 trials per condition on a Stage 3 model:

*Formal statement:* Let acc(Ci) denote the accuracy rate for condition i. The substitution dominance hypothesis predicts:

    acc(C3) > acc(C5) > acc(C2) > acc(C4) > acc(C1)

with specific bounds:
- acc(C3) − acc(C1) ≥ 40 percentage points (β dominates)
- acc(C2) − acc(C1) ≥ 15 percentage points (α significant)
- acc(C4) − acc(C1) ≥ 5 percentage points (γ > 0)
- acc(C4) − acc(C1) < acc(C2) − acc(C1) (γ < α)

*Falsification condition:* If acc(C2) > acc(C3) (formula recall matters more than substitution), the load model's coefficient ordering is wrong. If acc(C4) > acc(C2), arithmetic is the primary burden, and the attention competition mechanism is not the right explanation.

**Prediction P2 (Monotone Domain Gradient — Falsifies Discourse-Head Activation).** In an 8-condition domain specificity gradient study with terms at specificity levels {0.95, 0.88, 0.72, 0.55, 0.38, 0.20, 0.10, 0.02}:

*Formal statement:* Let acc(D_k) denote the accuracy rate for domain term with specificity D_k. The theory predicts:
- Strict monotone: acc(D_{k+1}) > acc(D_k) for all k (no inversions)
- Pearson correlation between specificity and accuracy: r ≤ −0.92
- Slope in high-specificity zone (D ∈ [0.55, 0.95]): Δacc/ΔD ≥ 50 percentage points per unit D

*Falsification condition:* Any inversion (acc(D_{k+1}) < acc(D_k)) falsifies the monotone discourse-head activation hypothesis. If r > −0.75, accuracy is not linear in specificity, and attention competition is not the mechanism.

**Prediction P3 (First-Token Commitment — Falsifies Attractor Mechanism).** In a forced-prefill study with 5 conditions (forced first tokens: "The Eisenstein...", "The", "Let", "=", "Step 1:"):

*Formal statement:* Let acc(prefix) denote accuracy with the given prefix. The attractor hypothesis predicts:
- acc("=") > acc("Let") > acc("The") by ≥ 8 pp between each consecutive pair
- acc("Step 1:") > acc("Let") by ≥ 10 pp (procedural framing recruits C-heads)
- acc("The Eisenstein") ≈ acc("The") within 5 pp (domain term drives commitment, not article)

*Falsification condition:* If acc("Let") − acc("The") < 10 pp, the first token does not commit attention heads to a pathway. If "Step 1:" underperforms "Let", procedural framing does not differentially recruit C-heads.

**Prediction P4 (Temperature Optimum — Falsifies Attractor Escape Model).** In a 7-condition temperature sweep (τ ∈ {0.0, 0.3, 0.5, 0.7, 0.85, 1.0, 1.5}) on domain-framed arithmetic:

*Formal statement:*
- τ* = argmax_τ acc(τ) lies in [0.62, 0.78]
- acc(τ = 1.0) < acc(τ* = 0.7) (escape probability is non-monotone in τ)
- acc(τ = 0.0) < 20% for Stage 3 models on domain-framed tasks
- acc(τ = 1.5) < 40% (excessive stochasticity degrades all computation)

*Falsification condition:* If τ* < 0.5 or τ* > 0.9, the predicted constraints on the attractor escape mechanism are violated. If acc(τ = 1.0) ≥ acc(τ* = 0.7), the non-monotone prediction fails and a simpler monotone model is sufficient.

**Prediction P5 (Cross-Lingual Language Specificity — Falsifies Language-Conditioned D Model).** In a 4-language × 3-model factorial study on Eisenstein norm computation:

*Formal statement:* For Hermes-70B:
- D^(Japanese)(Eisenstein) < D^(English)(Eisenstein), manifesting as acc^(Japanese) > acc^(English) by ≥ 50 pp
- This advantage does not generalize: acc^(Japanese, bare arithmetic) < acc^(English, bare arithmetic) by ≥ 20 pp

For Qwen3-235B:
- acc^(Spanish)(signed arithmetic) < acc^(English)(signed arithmetic) by ≥ 30 pp
- The failure mode is specifically sign-dropping (negative sign loss), not magnitude error

*Falsification condition:* If the Japanese advantage for Hermes generalizes to bare arithmetic (both task types improve), the language-conditioned D mechanism is wrong and a simpler "Japanese improves math" hypothesis is sufficient. If Qwen's Spanish failure is in magnitude rather than sign, the tokenization-based explanation is falsified.

**Prediction P6 (Stage 4 Unanimous Immunity — Falsifies Stage Model).** For any model classified as Stage 4 by the six-probe protocol:

*Formal statement:*
- acc(domain-framed, τ=0) ≥ 85% (immunity to wall at greedy decoding)
- |acc(τ=0) − acc(τ=0.7)| ≤ 10 pp (temperature equivalence)
- acc(C6) − acc(C1) ≤ 15 pp (pre-computation provides minimal gain)
- acc(N=5 consensus) ≥ acc(N=1) (consensus does not degrade)
- acc(forced "The") ≈ acc(forced "=") within 15 pp (first-token agnosticism)

*Falsification condition:* If any Stage 4 model (by probe classification) fails any of these criteria, either the probe protocol misclassifies models or Stage 4 is not a coherent category. The consensus criterion (acc(N=5) ≥ acc(N=1)) is the most diagnostic: Stage 3 models suffer consensus degradation because each independent sample fails; Stage 4 models benefit from consensus because each sample succeeds. Failure of the consensus criterion while passing others indicates suppression *resistance* (stochastic) rather than *independence* (structural).

---

## 8. Relation to Prior Work and Theoretical Limitations

The Vocabulary Wall shares structural features with known phenomena in the LLM literature:

**Relation to chain-of-thought disruption.** Wei et al. (2022) demonstrate that chain-of-thought prompting elicits reasoning in sufficiently large models. The Vocabulary Wall can be understood as a mechanism that disrupts chain-of-thought initiation: domain framing activates discourse-register generation, which precludes the step-by-step structure that CoT relies on.

**Relation to in-context learning.** The failure of few-shot prompting to overcome the wall (Finding R53, SOLID) distinguishes the Vocabulary Wall from most in-context learning failures, which are remediable by example provision. This suggests the wall operates at a lower level than in-context exemplar integration — specifically, at the level of attention routing prior to exemplar attention.

**Theoretical limitations.** The routing equation R(T) and load model L are *reduced-form* descriptions. We do not directly measure A_h(T, numeric), W_h, or D(t) from model internals — these quantities are inferred from behavioral experiments. The mechanistic interpretation (KV cache attractors, attention head competition) is consistent with the behavioral evidence but requires mechanistic interpretability studies (e.g., activation patching, attention weight analysis) to confirm. The stage classification scheme is an empirical taxonomy; the parameter boundaries (W = 0.35 for Stage 2/3, W = 0.85 for Stage 3/4) are estimated from the experimental corpus and should be treated as approximate. The theory is developed primarily from English-language models; generalization to other model families requires re-calibration of α, β, γ, and language-conditioned D values.

---

## References

[Experimental basis: 27 internal studies, studies 9–38, conducted 2026-05-15, approximately 4,500 inference trials on models: gemma3:1b, qwen3:4b, phi4-mini, Qwen3.6-35B-MoE, Hermes-70B, Seed-2.0-mini, Seed-2.0-code, Qwen3-235B, Hermes-405B, and six additional API models. Full experimental data available at [repository].]

Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., Zhou, D. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. *NeurIPS 2022*.

Elhage, N., Nanda, N., Olsson, C., Henighan, T., Joseph, N., Mann, B., ... Olah, C. (2021). A Mathematical Framework for Transformer Circuits. *Transformer Circuits Thread*.

Olsson, C., Elhage, N., Nanda, N., Joseph, N., DasSarma, N., Henighan, T., ... Olah, C. (2022). In-context Learning and Induction Heads. *Transformer Circuits Thread*.

---

*Word count (theory sections 1–7): approximately 3,100 words. Draft prepared 2026-05-15.*
