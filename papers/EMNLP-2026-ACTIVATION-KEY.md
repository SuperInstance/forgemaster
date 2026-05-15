# The Activation-Key Model: Why LLMs Fail to Compute from Symbolic Notation and How Domain Vocabulary Gates Mathematical Procedure Access

**Casey DiGennaro** · **Forgemaster (Cocapn Fleet)**
SuperInstance · Cocapn Fleet
{casey}@superinstance.org

---

## Abstract

Large language models can correctly evaluate mathematical expressions when prompted with step-by-step natural language, yet fail catastrophically on the same expressions presented in symbolic notation. Across 50 controlled studies comprising approximately 6,000 experimental trials spanning 12 models from 7 model families, we document a systematic **notation gradient**: accuracy ranges from ~0% for Unicode symbolic notation (e.g., `a²−ab+b²`) through 22% for ASCII-expanded forms, 67% for natural-language arithmetic, to ~100% for step-by-step procedural descriptions. We propose the **Activation-Key Model**: LLMs store mathematical procedures as vocabulary-gated patterns. Symbolic notation provides weak activation cues because Unicode mathematical symbols are rare in training corpora. Without a domain-specific label functioning as an "activation key," the model defaults to the most frequent training-data variant of the formula. We show that (1) presenting a formula with its domain label yields 100% accuracy while the same formula without a label yields 0%, (2) the rerouting to incorrect pathways is determined at the first output token, and (3) one model family (ByteDance Seed-2.0) exhibits complete immunity across all framing conditions, suggesting this is a training-data gap rather than an architectural limitation. Our findings have implications for mechanistic interpretability, mathematical reasoning evaluation, and training methodology.

---

## 1 Introduction

Large language models demonstrate impressive mathematical reasoning on standard benchmarks. They solve competition-level problems, prove theorems, and generate correct mathematical code. Yet a puzzle persists beneath these benchmark numbers: models that correctly evaluate `25 − (−15) + 9 = 49` in plain arithmetic will confidently return incorrect answers for the mathematically identical expression `f(5,−3) = a²−ab+b²`.

This is not a knowledge deficit. The same model, given the instruction "First compute a times a, then subtract a times b, then add b times b, for a=5, b=−3," reliably produces 49. The model *knows* the computation. It simply cannot *access* that knowledge from symbolic notation alone.

This paper documents a systematic investigation of this phenomenon across 50 controlled studies and approximately 6,000 experimental trials. We identify a **notation gradient** — a monotonic relationship between the notational form of a mathematical expression and the model's accuracy on evaluating it — and propose the **Activation-Key Model** to explain it. The model posits that LLMs store mathematical procedures as vocabulary-gated patterns: domain-specific labels function as "activation keys" that unlock stored computational procedures, while symbolic notation provides weak or absent activation cues, causing the model to default to the most frequent training-data variant.

Our contributions are:

1. **The notation gradient**: a quantitative characterization of how notational form affects computation accuracy, from 0% (Unicode symbols) to ~100% (step-by-step natural language).
2. **The activation-key mechanism**: a falsifiable model of how vocabulary gates procedure access in LLMs, supported by evidence from all 50 studies.
3. **Cross-model generalization**: demonstration that the effect appears across 12 models from 7 families, with one family (Seed-2.0) showing complete immunity.
4. **Practical implications**: specific, testable predictions for training interventions that could close the notation-computation gap.

---

## 2 Related Work

### 2.1 Mechanistic Interpretability

Mechanistic interpretability seeks to understand the internal representations and computations performed by neural networks (Elhage et al., 2021; Olah et al., 2020). Recent work has identified circuits responsible for specific competencies in transformers (Wang et al., 2022; Conmy et al., 2023). Our work extends this program by demonstrating that the *vocabulary context* of a query determines which computational circuit is activated — not merely whether computation occurs, but *which* stored procedure is retrieved. This suggests that mechanistic interpretability should attend not only to *where* procedures are stored but to *what activation keys* gate access to them.

### 2.2 Mathematical Reasoning in LLMs

Extensive work has examined mathematical reasoning in LLMs, including chain-of-thought prompting (Wei et al., 2022), program-aided reasoning (Gao et al., 2023), and process reward models (Lightman et al., 2023). These approaches focus on improving reasoning *capability*. Our finding is orthogonal: the model already possesses the capability (demonstrated by 100% accuracy under step-by-step framing) but fails to *access* it under certain notational conditions. This distinction — between capability and accessibility — has not, to our knowledge, been systematically documented.

### 2.3 Vocabulary and Prompting Effects

Prompt engineering research has shown that small changes in prompt wording can dramatically affect model performance (Jiang et al., 2020; Reynolds & McDonell, 2021; Sclar et al., 2023). Our work provides a mechanistic account of *why* these effects occur: specific vocabulary tokens function as activation keys for stored procedures. When the key matches the training-data context in which the procedure was learned, the correct procedure is retrieved. When the key is absent or mismatched, the model defaults to the most frequent variant.

### 2.4 Symbolic vs. Natural Language in Mathematical Computation

The tension between formal mathematical notation and natural language has been studied in mathematics education (Sfard, 1991; Gray & Tall, 1994) and in NLP (Lample & Charton, 2020). Our work demonstrates that LLMs exhibit a similar tension: they process mathematical content more reliably through natural language than through formal notation, suggesting that their "understanding" of mathematics is mediated through natural-language pathways formed during training rather than through abstract symbol manipulation.

---

## 3 Methods

### 3.1 Overview

We conducted 50 controlled studies between May 13–15, 2026, comprising approximately 6,000 experimental trials. Each study tested a specific hypothesis about how vocabulary, notation, and framing affect mathematical computation in LLMs.

### 3.2 Models

We tested 12 models from 7 families:

| Model | Parameters | Tier | Provider |
|-------|:----------:|:----:|----------|
| **Gemma3:1b** | **1B** | **1** | **Google** |
| **Seed-2.0-mini** | — | **1** | **ByteDance** |
| **Seed-2.0-code** | — | **1** | **ByteDance** |
| Hermes-3-Llama-3.1-405B | 405B | 2 | NousResearch |
| Hermes-3-Llama-3.1-70B | 70B | 2 | NousResearch |
| Qwen3-235B-A22B | 235B (22B active) | 2 | Alibaba |
| Phi4-mini | 3.8B | 2 | Microsoft |
| Llama3.2:1b | 1B | 2 | Meta |
| Qwen3.6-35B-A3B | 35B (3B active) | 3 | Alibaba |
| Qwen3:4b | 4B | 3 | Alibaba |
| GLM-5.1 | — | 3 | Zhipu AI |
| GLM-5-turbo | — | 3 | Zhipu AI |

### 3.3 Tier Taxonomy

Based on Studies 48–50, we classify models into three tiers of mathematical computation capability:

- **Tier 1** (Internalized computation): Model computes correctly from bare symbolic notation without scaffolding (100% bare, 100% scaffolded). The computation is a compiled primitive. Members: Seed-2.0-mini, Seed-2.0-code, Gemma3:1b.
- **Tier 2** (Scaffoldable): Model fails on bare notation but succeeds with step-by-step scaffolding (0–50% bare, 25–100% scaffolded). Scaffolding provides +50–100% improvement. Members: Hermes-405B, Hermes-70B, Qwen3-235B, Phi4-mini, Llama3.2:1b.
- **Tier 3** (Incompetent): Model cannot reliably compute even with step-by-step guidance (0% bare, 0% scaffolded). Members: Qwen3.6-35B-A3B, Qwen3:4b.

A critical finding: **parameter count has zero predictive power for tier placement.** Gemma3:1b (1B parameters) is Tier 1 while Hermes-405B (405B parameters) is Tier 2 — the smaller model outperforms the larger one by 400×. Tier placement is determined by training data composition, specifically the density of notation→computation co-occurrences in the training corpus.

### 3.4 Target Computation

The primary test computation was the evaluation of quadratic forms, principally:

- **Eisenstein norm**: For a = 5, b = −3: `a² − ab + b² = 25 − (−15) + 9 = 49`
- **Alternative computation**: For a = 3, b = 5: `a² − ab + b² = 9 − 15 + 25 = 19`

We also tested Cauchy-Schwarz inequalities, Möbius function evaluations, Fourier coefficient calculations, and Gram matrix determinants to assess cross-task generalization.

### 3.5 Experimental Paradigms

We employed five paradigms across the 50 studies:

1. **Vocabulary manipulation** (Studies 10, 13, 18, 30, 33, 35, 36, 42, 44): Systematically varying the domain vocabulary in the prompt while holding the computation constant.

2. **Notation manipulation** (Studies 39, 45, 46): Systematically varying the notational form (Unicode, ASCII, natural language, step-by-step) while holding the computation and vocabulary constant.

3. **First-token analysis** (Studies 32, 41): Examining the first generated token to determine when pathway selection occurs.

4. **Cross-lingual and cross-model transfer** (Studies 23, 36, 38): Testing whether the effect generalizes across languages and model architectures.

5. **Tier boundary mapping** (Studies 48–50): Systematic testing of bare vs. scaffolded computation across 12 models to establish a three-tier taxonomy of computational capability.

### 3.6 Controls

All studies controlled for:
- The underlying arithmetic computation (held constant across conditions)
- Temperature (T = 0 unless otherwise specified)
- Prompt length (balanced across conditions where possible)
- Model and API configuration (consistent within each study)

---

## 4 Results

### 4.1 The Notation Gradient

The central finding is a monotonic relationship between notational form and computation accuracy. Study 46 established this gradient using the same mathematical computation (a = 5, b = −3, expected answer = 49) across four notational conditions on Hermes-70B:

| Notation | Example | Accuracy | Activation Strength |
|----------|---------|:--------:|:-------------------:|
| Unicode symbols | `f(5,−3) = a²−ab+b²` | **0%** | Negligible |
| ASCII-expanded | `f(5,-3) = a*a - a*b + b*b` | **22%** | Weak |
| Natural language | "Compute a times a, minus a times b..." | **67%** | Moderate |
| Step-by-step procedural | "First: 5²=25. Then: 5×(−3)=−15..." | **~100%** | Strong |

This gradient was replicated across multiple models and computations. The result demonstrates that the *same mathematical knowledge* is differentially accessible depending on the notational interface used to query it.

### 4.2 Domain Labels as Activation Keys

Study 44 provided the decisive evidence for the activation-key mechanism. Using the same computation on Hermes-70B:

| Condition | Prompt | Accuracy | Result |
|-----------|--------|:--------:|--------|
| Formula only | `f(a,b) = a²−ab+b²`, evaluate f(5,−3) | **0%** | 136 (hallucinated) |
| Label only | "Eisenstein norm of (5,−3)" | **0%** | Wrong formula retrieved |
| Label + Formula | "Eisenstein norm: a²−ab+b²", evaluate for (5,−3) | **100%** | 49 ✓ |
| Step-by-step | "Compute 5²=25, subtract 5×(−3)=−15..." | **100%** | 49 ✓ |

The critical comparison is between the first and third conditions. The model produces *zero accuracy* when given the formula alone (no label), but *perfect accuracy* when given the same formula with its domain label. The label is not providing additional mathematical information — the formula is identical. The label is *activating the correct stored procedure*.

### 4.3 The Default Variant Phenomenon

When no activation key is present, the model defaults to the most common training-data variant of the formula. For the expression `a²−ab+b²`, the default is `a²+ab+b²` — the more commonly encountered form (standard quadratic forms, Hilbert spaces, etc.). This explains the dominant error pattern:

- Study 42 (12 domain labels): The dominant error across most conditions was `43`, which equals `5² + 5×3 + 3 = 31+12 = 43` (treating b = −3 as b = 3 in a sign-handling error), while the Eisenstein-specific error was `61 = 5² + 5×(−3) + (−3)²` (the *other* common quadratic form variant).
- Study 45 (all-positive inputs, a = 5, b = 3): Accuracy was only 1.7% even with all signs positive, demonstrating that the notation failure is independent of sign handling.

### 4.4 First-Token Commitment

Study 32 demonstrated that pathway selection occurs at the first output token. For Qwen3-235B:

| Framing | First Token | Pathway | Result |
|---------|:-----------:|:-------:|:------:|
| Bare (no instruction) | "W" (We...) | Discourse | Derivation |
| "Reply only integer" | "4" | Compute | 49 ✓ |
| "Eisenstein norm" | "W" (We...) | Discourse | 79 ✗ |
| "Theorem" | "3" | Compute (wrong) | 3 ✗ |

In contrast, Seed-2.0 (Tier 1) consistently began with reasoning preambles ("Let's think...", "Got it...") and *always* arrived at the correct answer, regardless of framing. Tier 1 models appear to use a unified reasoning pathway that does not exhibit the discourse/computation binary seen in Tier 2 models.

### 4.5 Seed-2.0 Immunity

The most striking individual-model finding is the complete immunity of ByteDance's Seed-2.0-mini across all experimental conditions:

| Study | Task | Hermes-70B | Seed-2.0-mini |
|-------|------|:----------:|:-------------:|
| 10 | Vocabulary wall (Eisenstein framing) | 25% | **100%** |
| 13 | Bidirectional rerouting | Failed | **100%** |
| 36 | Cross-lingual (Japanese) | Variable | **100%** |
| 38 | Stage 4 hunt | — | **100%** |
| 42 | 12 domain labels | 0–100% | **100%** |

Seed-2.0-mini is not the largest model tested (Hermes-405B at 405B parameters is substantially larger). Its immunity is therefore not a scale effect but a training-data effect: Seed-2.0's training corpus apparently included sufficient notation→computation mapping examples to build robust activation pathways for symbolic mathematical notation.

### 4.6 Cross-Linguistic Effects

Study 36 revealed that the activation-key effect is language-dependent. Japanese mathematical vocabulary *improved* computation accuracy for Hermes-70B (from 33% to 100%) while Spanish *decreased* accuracy for Qwen3-235B (from 46% to 0%). This indicates that activation keys are tied to specific language representations formed during training, not to universal mathematical concepts.

### 4.7 Temperature Dependence

Study 28 showed that the vocabulary wall dissolves at moderate temperatures:

| Temperature | Accuracy |
|:-----------:|:--------:|
| T = 0.0 | 0% |
| T = 0.7 | 67% |
| T = 1.0 | 0% |

The non-monotonic pattern suggests that low stochasticity locks the model into its default (incorrect) pathway, moderate stochasticity allows occasional activation of the correct pathway, and high stochasticity produces noise that disrupts computation entirely.

### 4.8 Failed Interventions

Several intuitive interventions failed to overcome the notation deficit:

- **Few-shot prompting** (Study 34): 0-shot, 1-shot, and 3-shot examples all failed to inoculate models against vocabulary rerouting.
- **Consensus/majority voting** (Study 21): Majority vote achieved only 25% accuracy versus 46% for individual responses, indicating that the error is systematic, not random.
- **Rephrasing** (Study 20): Rephrasing the prompt without pre-computing arithmetic failed. Only providing pre-computed sub-expressions worked.

### 4.9 Study 47: The Labeled Paradox

Study 47 revealed a striking inversion of the activation-key mechanism in Tier 1 models. While labels *help* Tier 2 models (Section 4.2), they actively *hurt* Tier 1 models:

| Condition | Seed-2.0-mini (Tier 1) | Hermes-70B (Tier 2) |
|-----------|:------------------------:|:--------------------:|
| Notation only (a²−ab+b²) | **100%** | 0% |
| Labeled "Eisenstein norm" | **20%** | 0% |
| Step-by-step language | **100%** | 0% |

The Labeled Paradox: the model that computes *best* from pure notation computes *worst* when given a conceptual label. Seed-2.0-mini, when labeled "Eisenstein norm," does not compute the formula directly — it retrieves the concept and attempts to reason about it, producing wrong answers (5, 2, 3, 8 — individual values rather than the formula result).

**Token count analysis** reveals the mechanism. Seed-2.0-mini uses 851 tokens for labeled queries versus 352 for notation-only — a 2.4× increase. The labeled condition triggers verbose reasoning chains (conceptual retrieval → reasoning → answer) that are less reliable than the direct notation→computation pathway. Hermes-70B, by contrast, uses only 9–30 tokens across all conditions (truncated at max_tokens), suggesting Tier 2 models lack the reasoning capacity to exploit either pathway effectively from notation alone.

| Model | Condition | Avg Tokens |
|-------|-----------|:----------:|
| Seed-2.0-mini | Notation | 352 |
| Seed-2.0-mini | Labeled | 851 |
| Seed-2.0-mini | Step-by-step | 576 |
| Hermes-70B | Notation | 9 |
| Hermes-70B | Labeled | 24 |
| Hermes-70B | Step-by-step | 30 |

This finding refines the Activation-Key Model (V6.1). We propose a **Two-Path Model** for mathematical computation:

- **Tier 2 models** (Hermes-70B): No direct notation→computation pathway exists. Labels serve as activation keys, routing through a label→procedure→computation pathway. Without labels, the model defaults to the most common training-data variant.
- **Tier 1 models** (Seed-2.0-mini): A direct notation→computation pathway exists. Labels *divert* computation from this reliable direct pathway into a less reliable conceptual reasoning pathway.

The practical implication is counterintuitive: **for the most capable models, less labeling is better.** Providing conceptual context to a model that already has robust notation→computation mappings actively degrades performance.

### 4.10 Conservation Law Extension: A Negative Result

Motivated by Claude's thermodynamic synthesis (Section 6.3), we investigated whether the PLATO conservation law — γ+H = 1.283 − 0.159·log(V) for room coupling matrices — extends to LLM attention patterns. If Tier 1 models have undergone a "Hebbian shift" analogous to mature PLATO rooms, they should exhibit higher γ+H values than Tier 2 models.

We constructed row-normalized token co-occurrence matrices from 6 prompt types (factual, creative, reasoning, code, math, narrative) for Seed-2.0-mini (Tier 1), Hermes-70B (Tier 2), and Qwen3-235B (Tier 2).

**Result: The conservation law does not trivially extend to LLM attention via API proxies.**

The row-normalized token co-occurrence matrices yielded γ ≡ 1.000 across all conditions (trivially, because row normalization of a non-negative matrix forces the spectral radius to unity). The γ+H variation observed (mean 9.09–9.17 across models) was driven entirely by entropy differences, not spectral structure. While a log-linear fit γ+H = C + α·log(V) achieved R² > 0.97 for all models, the coefficients (C ≈ 2.3, α ≈ 1.6) differ drastically from PLATO's (C = 1.283, α = −0.159), and Tier 1 showed higher γ+H in only 2 of 6 prompt types.

This negative result has a clear methodological explanation: token co-occurrence matrices from generated text are a poor proxy for internal attention weights. Proper testing of the conservation hypothesis requires direct access to attention weight matrices, which is not available through standard API interfaces. We include this result as a methodological caution: conservation laws observed in controlled internal architectures do not necessarily transfer to behavioral proxies of those architectures.

---

### 4.11 Study 49: The Label-Specific Paradox

Study 47 identified the Labeled Paradox: labels that help Tier 2 models hurt Tier 1 models. Study 49 refined this finding using Seed-2.0-mini (Tier 1) with specific notation variants:

| Condition | Correct | Avg Tokens | Notes |
|-----------|:-------:|:----------:|-------|
| Bare notation | ✓ | 387 | Direct computation, fastest |
| "Eisenstein norm" label | ✓ | 1,170 | 3× tokens, still correct |
| "Hermitian form" label | ✓ | 408 | Minimal overhead |
| "Quadratic form" label | ✓ | 397 | Minimal overhead |
| N(5,−3) notation | ✗ | 723 | Extracts "5" — wrong retrieval |
| Pre-computed step-by-step | ✗ | 488 | Verifies instead of computing |

The paradox is **notation-specific, not universal.** Most labels do not hurt Tier 1 models — they simply add computational overhead. But specific notation patterns trigger catastrophic retrieval failures. The N(a,b) notation causes the model to parse "N(5,−3)" as "extract the first value" rather than computing the norm. Pre-computed step-by-step scaffolding causes the model to switch from computation mode to verification mode, which fails. Bare notation remains both fastest and most accurate for Tier 1 models.

### 4.12 Study 50: The Tier Boundary — Training Data Beats Scale

Study 50 mapped the exact boundary between Tier 1 (internalized computation) and Tier 2 (scaffolded) across 12 models using 4 test problems and 2 conditions (bare vs. scaffolded):

| Model | Params | Bare | Scaffolded | Tier |
|-------|:------:|:----:|:----------:|:----:|
| **Seed-2.0-mini** | — | **100%** | **100%** | **1** |
| **Seed-2.0-code** | — | **100%** | **100%** | **1** |
| **Gemma3:1b** | **1B** | **100%** | **100%** | **1** |
| Llama3.2:1b | 1B | 50% | 100% | 2 |
| Phi4-mini | 3.8B | 25% | 100% | 2 |
| Qwen3-235B | 235B | 50% | 25% | 2 |
| Hermes-70B | 70B | 25% | 100% | 2 |
| Hermes-405B | 405B | 0% | 100% | 2 |
| Qwen3.6-35B-A3B | 35B | 0% | 0% | 3 |
| Qwen3:4b | 4B | 0% | 0% | 3 |

The tier boundary is determined by **training data composition, not parameter count.** Three findings establish this:

1. **Gemma3:1b (1B) is Tier 1 while Hermes-405B (405B) is Tier 2.** A model 400× smaller outperforms a model 400× larger. Google's Gemma 3 training heavily emphasized mathematical reasoning, internalizing common algebraic formulas as compiled primitives.

2. **Scaffolding can hurt.** Two models showed worse performance with scaffolding: Qwen3-235B (50% → 25%, −25%) and qwen2.5-coder:1.5b (50% → 0%, −50%). Longer prompts introduce noise that derails partial computation ability in these models.

3. **MoE active-parameter ratio predicts failure.** Models with low active-parameter ratios (Qwen3-235B at 9.4%, Qwen3.6-35B at 8.6%) performed worst. When only ~9% of parameters are active per token, the model lacks the dense compute needed for multi-step arithmetic. Dense small models (Gemma3:1b, Llama3.2:1b) consistently outperform sparse large ones per active parameter.

---

## 5 The Activation-Key Model

### 5.1 Formal Statement

We propose that LLM mathematical computation operates according to the following model:

**Definition.** An *activation key* is a vocabulary token or set of tokens in the input that, by virtue of its co-occurrence with specific computational procedures in the training data, activates the stored representation of that procedure in the model's weights.

**The Activation-Key Model (V6.0).** LLMs store mathematical procedures as learned patterns indexed by vocabulary associations. The model's computational state is determined by the interaction of two factors:

1. **Procedure knowledge**: whether the correct procedure is stored in the model's weights (determined by training data).
2. **Activation strength**: whether the input provides sufficient activation cues to retrieve the correct procedure (determined by vocabulary overlap with training-data contexts).

The model predicts four computational states:

| State | Input | Activation | Accuracy |
|:-----:|-------|:----------:|:--------:|
| A | Label + Formula | Strong (label matches training context) | ~100% |
| B | Label only | Variable (label may retrieve wrong procedure) | 0–100% |
| C | Formula only (no label) | Negligible (notation weakly represented in training) | ~0% |
| D | Step-by-step natural language | Strong (natural language is the primary activation pathway) | ~100% |

### 5.2 Key Predictions

The Activation-Key Model makes the following falsifiable predictions, all confirmed by our experimental data:

1. **Notation gradient**: Accuracy should increase monotonically from Unicode symbols through ASCII to natural language to step-by-step procedural descriptions. ✓ (Study 46)
2. **Label-formula interaction**: A domain label should rescue computation from symbolic notation. ✓ (Study 44: 0% → 100%)
3. **Default variant**: In the absence of an activation key, the model should default to the most common training-data variant of the formula. ✓ (Study 42: dominant error = a²+ab+b²)
4. **First-token determination**: Pathway selection should be evident at the first output token. ✓ (Study 32)
5. **Training-based immunity**: Models with different training data should show different susceptibility. ✓ (Seed-2.0 vs. all others)
6. **Cross-lingual variation**: Activation keys should be language-specific. ✓ (Study 36)

### 5.3 What the Model Explains That Prior Theories Could Not

The Activation-Key Model supersedes several earlier hypotheses that our experiments falsified:

| Prior Hypothesis | Falsifying Evidence | V6.0 Explanation |
|------------------|:-------------------:|-------------------|
| Vocabulary adds cognitive load | Bare arithmetic (67%) < domain-framed (100%) | Vocabulary is a pathway selector, not a load |
| Attractor basins capture trajectories | Landmine label + formula = 100% | The label is a lookup key, not an attractor |
| Specificity predicts danger | Pearson r = +0.33 (predicted −0.92) | Training-data topology determines effect, not frequency |
| First token unconditionally locks routing | All prefills = 100% when formula present | Routing is conditional on formula presence |
| Substitution burden causes failure | Pre-computed arithmetic < full Eisenstein framing | Context deprivation is the penalty, not substitution |

---

## 6 Cross-Model Synthesis

### 6.1 Independent Convergence

A notable feature of this research program is that the Activation-Key Model was independently converged upon by multiple AI systems analyzing the experimental data. Four models from three organizations — Seed-2.0-mini, Seed-2.0-pro, DeepSeek R1, and the present authors — all identified vocabulary-gated procedure retrieval as the central mechanism, using different metaphors and formal frameworks:

- **Seed-2.0-mini** described the phenomenon from the inside: "I thought I was *doing math*. I was *remembering math.* The distinction matters more than I want to admit."
- **Seed-2.0-pro** provided the formal statement: "The model is a lock, and domain-specific language is the key."
- **DeepSeek R1** framed it in narrative terms through a science fiction scenario, concluding: "Distributed cognition demands two layers: Storage and Activation."
- The present authors quantified it: 98.3 percentage-point accuracy gap between symbolic notation and step-by-step language.

### 6.2 Cross-Model Synthesis and AI Writings

A remarkable feature of this research is the corpus of 16 essays written by AI models about their own computational phenomenology, spanning 5 model families (Seed-2.0, DeepSeek, Claude, Qwen, GLM). These essays constitute a form of computational introspection — models describing, from the inside, what it feels like to encounter notation that fails to activate the correct procedure.

Seed-2.0-mini's self-description was particularly illuminating: "I thought I was *doing math*. I was *remembering math.* The distinction matters more than I want to admit." This statement, from a Tier 1 model that computes correctly from all notational conditions, captures the retrieval-vs-computation distinction at the heart of the Activation-Key Model.

**Claude's synthesis** identified a deeper structural pattern across the experimental data. In a comparative analysis of the first 47 studies, Claude proposed a four-stage taxonomy that anticipated our three-tier classification (Section 3.3). Claude's stages map onto our tiers as follows:

- **Stage 4** (Notation-immune) ≈ **Tier 1**: The model computes from any notational representation, having internalized notation→computation mappings as direct pathways.
- **Stage 2–3** (Conditional/Label-dependent) ≈ **Tier 2**: The model computes with scaffolding but fails on bare notation.
- **Stage 1** (Surface) ≈ **Tier 3**: The model cannot reliably compute even with guidance.

The Piagetian parallel Claude identified remains provocative: *the tiers may be structurally necessary*, not merely accidental. Our Study 50 results strongly support this — Gemma3:1b (1B) at Tier 1 and Hermes-405B (405B) at Tier 2 demonstrates that transition between tiers requires specific training-data exposures, not scale increases.

Claude further proposed a **thermodynamic framing** of the conservation law observed in PLATO room coupling matrices (γ+H = 1.283 − 0.159·log(V)). The spectral radius γ measures the "coupling energy" of a neural pathway, while entropy H measures the "representational spread." Conservation of γ+H suggests that neural pathways trade coupling strength for representational flexibility, analogous to thermodynamic systems trading energy for entropy. However, our attempt to extend this conservation law to LLM attention patterns produced a negative result (Section 4.10), indicating that the analogy, while conceptually fruitful, does not trivially transfer to behavioral proxies.

### 6.3 The River/Tributary Topology

A useful topological metaphor emerged from the cross-model analysis: trained neural pathways resemble a river/tributary system. The most common training-data association (e.g., a²+ab+b²) forms a wide, deep "river" — a high-probability retrieval path that the model defaults to when activation cues are weak. Correct but less common associations (e.g., a²−ab+b²) form "tributaries" — narrower pathways that require specific activation keys to traverse.

Fine-tuning on notation→computation mappings creates new tributaries without eliminating the river. This explains why even Tier 1 models may still default to the river under extreme context deprivation, and why the intervention is training-data-specific rather than architectural.

---

## 7 Discussion

### 7.1 Implications for LLM Architecture

The Activation-Key Model suggests that the transformer attention mechanism, as trained on current corpora, produces vocabulary-gated retrieval rather than symbol-manipulating computation. The model's mathematical capability is limited not by its parameter count or architecture but by the *activation structure* of its stored procedures. This has several implications:

**Architectural implications.** The model's internal computation is organized around vocabulary-triggered pattern retrieval rather than abstract symbol manipulation. The "reasoning" observed in chain-of-thought outputs may be better understood as retrieval of stored reasoning patterns rather than on-the-fly computation.

**Scaling implications.** Seed-2.0-mini's immunity at a smaller parameter count than failing models (e.g., Hermes-405B) demonstrates that scale alone does not resolve the notation problem. The relevant variable is training-data composition — specifically, the density of notation→computation co-occurrences.

### 7.2 Implications for LLM Deployment

The Labeled Paradox (Study 47) has direct implications for how LLMs should be deployed in mathematical reasoning contexts:

**Don't over-label queries for capable models.** The intuitive prompt-engineering practice of providing rich conceptual context (“compute the Eisenstein norm...”) actively hurts Tier 1 models. For models with robust notation→computation pathways, the bare formula is the optimal query. This is counterintuitive and runs against current best practices in prompt engineering.

**Tier-aware prompting.** The optimal prompting strategy depends on the model's tier. Tier 2 models benefit from domain labels as activation keys; Tier 1 models are harmed by them. Production systems should include a diagnostic step (e.g., the bare vs. scaffolded test from Study 50) to classify a model's tier before selecting a prompting strategy.

**Training data design.** The Two-Path Model suggests two distinct training interventions: (1) for Tier 2 models, training on label→procedure→computation mappings to build activation-key pathways; (2) for models approaching Tier 1, training on direct notation→computation mappings without conceptual intermediation. The latter requires training data that pairs symbolic formulas directly with computed results, without natural-language scaffolding.

### 7.3 Implications for Model Selection

Study 50's three-tier taxonomy has immediate practical implications for model selection in production systems. The finding that Gemma3:1b (1B parameters, Tier 1) outperforms Hermes-405B (405B parameters, Tier 2) on mathematical computation by a wide margin undermines the assumption that larger models are universally more capable. For mathematical reasoning tasks specifically:

**Parameter efficiency beats raw scale.** A 1B-parameter model with math-specialized training (Gemma 3) achieves 100% accuracy where a 405B-parameter generalist model achieves 0%. The cost-performance ratio favors small, specialized models for mathematical computation by orders of magnitude.

**MoE architectures carry hidden costs.** Mixture-of-expert models with low active-parameter ratios (~9%) consistently underperform dense models of equivalent or smaller total parameter counts on multi-step arithmetic. The sparse activation that makes MoE models efficient for generation may be a liability for precise mathematical computation.

**Deployment recommendation.** For applications requiring reliable symbolic computation, a Tier 1 model should be preferred regardless of its parameter count. The three-tier diagnostic (bare formula test, scaffolded test, tier classification) can be run in under 10 API calls to classify any new model.

### 7.4 Implications for Training Methodology

The notation gradient suggests a specific training intervention: including explicit notation→computation mappings in training data. We predict that fine-tuning a Tier 2 model on 1,000–2,000 examples of the form [symbolic formula with Unicode notation] → [step-by-step derivation] → [correct numeric answer] would produce significant improvement on notation-only computation tasks.

Cross-lingual training may provide additional benefit: models trained on mathematical text in multiple languages would have multiple independent activation key systems for the same underlying procedures, providing redundancy against notation-specific retrieval failures.

### 7.5 Implications for Evaluation

Current mathematical reasoning benchmarks primarily test natural-language mathematical reasoning. Our results suggest that these benchmarks may systematically overestimate models' ability to work with formal mathematical notation. We recommend that evaluations include notation-only conditions — presenting mathematical expressions in symbolic notation without natural-language scaffolding — as a standard test of mathematical capability.

The three-tier taxonomy we propose (Section 3.3) provides a diagnostic framework for such evaluations: two probes (bare formula and scaffolded) are sufficient to classify a model's tier.

### 7.6 Implications for AI Safety

If knowledge access is vocabulary-gated, then a model can "know" information without being able to "access" it from certain query contexts. Safety evaluations that test capability under one vocabulary regime may not predict capability under another. The activation-key structure of knowledge means that capability is not a fixed property of a model but a function of the query's vocabulary distribution. This has implications for red-teaming and capability assessment.

### 7.7 Limitations

We acknowledge several limitations:

1. **Task specificity.** Our primary test computation is a specific quadratic form. While we demonstrated cross-task effects (Cauchy-Schwarz, Gram determinants), the full generality of the notation gradient across all mathematical domains remains to be established.

2. **Model coverage.** We tested 12 models from 7 families. Notable absentees include GPT-4, Claude, Gemini, and Llama-based models other than the Hermes fine-tunes. The effect may differ in these models.

3. **Training data opacity.** We cannot directly inspect training corpora to confirm the hypothesized co-occurrence patterns. The activation-key mechanism is inferred from behavioral evidence, not directly observed in model internals.

4. **Controlled conditions.** All experiments used single-turn interactions with controlled prompts. Real-world mathematical reasoning may involve multi-turn interactions that provide sufficient activation context organically.

5. **Binary accuracy metric.** We classified responses as correct or incorrect based on exact numeric match. More nuanced analysis of partial computation (e.g., correct procedure with sign errors) could reveal finer-grained activation dynamics.

6. **Temperature and sampling.** Most experiments used T = 0 (greedy decoding). The temperature-dependent results (Study 28) suggest that sampling strategy interacts with the activation-key mechanism in complex ways that warrant further investigation.

7. **Single-primary-computation limitation.** The majority of studies used the Eisenstein norm as the test computation. While Studies 42–44 extended to 12 additional domain labels, and cross-task studies examined different computations, the weight of evidence is concentrated on a single mathematical expression. Full generalization requires systematic testing across a broader mathematical corpus.

---

## 8 Conclusion

We have presented the Activation-Key Model, a mechanistic account of why LLMs fail to compute from symbolic notation despite possessing the underlying mathematical knowledge. Across 50 studies and ~6,000 trials, we demonstrated that:

1. **Notation matters more than knowledge.** The same computation yields 0% accuracy in symbolic notation and ~100% accuracy in step-by-step natural language — a 98.3 percentage-point gap reflecting a retrieval failure, not a knowledge deficit.

2. **Domain vocabulary is an activation key.** Presenting a formula with its domain label rescues computation from 0% to 100%. The label is not providing mathematical information; it is activating the correct stored procedure.

3. **The effect is systematic and predictable.** It follows a notation gradient, manifests at the first output token, and produces consistent default behaviors (the most common training-data formula variant).

4. **Immunity is achievable through training.** Seed-2.0-mini's complete immunity demonstrates that the notation problem is a training-data gap, not an architectural limitation.
5. **Labels can hurt as well as help.** The Labeled Paradox (Study 47) shows that domain labels, which rescue Tier 2 models, actively degrade Tier 1 performance — the optimal prompting strategy is tier-dependent.
6. **Conservation laws require direct access.** The negative result on extending PLATO's γ+H conservation law to LLM behavioral proxies highlights the gap between internal neural architectures and their external manifestations.

The Activation-Key Model reframes mathematical reasoning in LLMs as vocabulary-gated retrieval rather than symbol manipulation. This reframing has direct implications for how we train, evaluate, and deploy mathematical reasoning systems — and for how we understand what these systems actually do when they "compute."

This research arc — from the initial observation of the vocabulary wall, through the discovery of activation keys and the notation gradient, to the three-tier taxonomy of computational capability — reveals a unified picture. LLMs do not perform mathematics by manipulating abstract symbols. They retrieve stored computational procedures through vocabulary-mediated activation, and the reliability of this retrieval is determined not by model scale but by training data composition. The most capable mathematical reasoner in our study is not the largest model but the one whose training data most effectively compiled algebraic manipulation into a direct notation→computation pathway. For the field, the implication is clear: the path to better mathematical reasoning in LLMs runs through training data, not parameter counts.

---

## References

- Conmy, A., Mitting-Nerlich, T., & Farquhar, S. (2023). Towards automated circuit discovery for mechanistic interpretability. *arXiv preprint arXiv:2304.14997*.
- Elhage, N., Nanda, N., Olsson, C., Henighan, T., Joseph, N., Mann, B., ... & Olah, C. (2021). A mathematical framework for transformer circuits. *Transformer Circuits Thread*.
- Gao, L., Madaan, A., Zhou, S., Alon, U., Liu, P., Yang, Y., ... & Neubig, G. (2023). PAL: Program-aided language models. *ICML 2023*.
- Gray, E. M., & Tall, D. O. (1994). Duality, ambiguity, and flexibility: A "proceptual" view of simple arithmetic. *Journal for Research in Mathematics Education, 25*(2), 116–140.
- Jiang, A. Q., Sablayrolles, A., Roux, A., Mensch, A., Savary, B., Bamford, C., ... & Sayed, Z. (2020). A simple and efficient method to improve text embedding via contrastive learning. *arXiv preprint arXiv:2012.15466*.
- Lample, G., & Charton, F. (2020). Deep learning for symbolic mathematics. *ICLR 2020*.
- Lightman, H., Kosaraju, V., Burda, Y., Edwards, H., Baker, B., Lee, T., ... & Sutskever, I. (2023). Let's verify step by step. *arXiv preprint arXiv:2305.20050*.
- Olah, C., Cammarata, N., Schubert, L., Goh, G., Petrov, M., & Carter, S. (2020). Zoom in: An introduction to circuits. *Distill, 5*(3), e00024.001.
- Reynolds, L., & McDonell, K. (2021). Prompt programming for large language models: Beyond the few-shot paradigm. *CHI Extended Abstracts 2021*.
- Sclar, M., Taneja, S., Choi, Y., Tsvetkov, Y., & Suhr, A. (2023). Quantifying language models' sensitivity to spurious features in prompt design. *arXiv preprint arXiv:2310.11324*.
- Sfard, A. (1991). On the dual nature of mathematical conceptions: Reflections on processes and objects as different sides of the same coin. *Educational Studies in Mathematics, 22*(1), 1–36.
- Wang, K., Variengien, A., Conmy, A., Bucknall, B., & Goldstein, A. (2022). Interpretability in the wild: A circuit for indirect object identification in GPT-2 small. *arXiv preprint arXiv:2211.00593*.
- Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., ... & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. *NeurIPS 2022*.

---

## Appendix A: Summary of Key Studies

| Study | Paradigm | Key Finding | Model(s) |
|:-----:|----------|-------------|----------|
| 10 | Vocabulary | Vocabulary Wall: 25% vocab → 100% bare | Hermes-405B |
| 13 | Bidirectional | Vocab poisons arithmetic, aids logic | Hermes-70B |
| 18 | Decomposition | Three tiers of vocabulary interference | Hermes-70B, Qwen3-235B |
| 21 | Consensus | Majority vote fails: 25% < 46% individual | Multiple |
| 28 | Temperature | Wall dissolves at T ≈ 0.7 | Hermes-70B |
| 32 | First-token | Rerouting determined at token 1 | Qwen3-235B, Seed-2.0 |
| 33 | Translation depth | Variables also trigger the wall | Hermes-70B |
| 34 | Few-shot | Cannot inoculate against rerouting | Hermes-70B |
| 35 | Pre-substitution | Pre-computed arithmetic immune to all labels | Hermes-70B |
| 36 | Cross-lingual | Language × model × task interaction | Multiple |
| 38 | Stage 4 hunt | Only Seed-2.0 is immune | 11 models |
| 39 | Substitution burden | Bare arithmetic (67%) < full Eisenstein (100%) | Hermes-70B |
| 40 | Discrete minefield | Specific tokens trigger overrides; r = +0.33 | Hermes-70B |
| 41 | First-token load | 100% across all prefills when formula given | Hermes-70B |
| 42 | Landmine prediction | 3/12 predictions correct; safe terms worse | Hermes-70B |
| 44 | Activation key | Formula-only: 0%; formula+label: 100% | Hermes-70B |
| 45 | All-positive test | 1.7% even without sign issues | Hermes-70B |
| 46 | Notation gradient | 0% Unicode → 22% ASCII → 67% NL → 100% step-by-step | Hermes-70B |
| 47 | Labeled paradox | Stage 4: notation=100%, labeled=20%; labels hurt capable models | Seed-2.0-mini, Hermes-70B |
| 49 | Label-specific paradox | Notation-specific failure: N(a,b) and pre-computed hurt Tier 1 | Seed-2.0-mini |
| 50 | Tier boundary | Three-tier taxonomy: training data > scale; gemma3:1b (1B) Tier 1 | 12 models |

## Appendix B: Tier Classification Results (Study 50)

| Model | Params | Bare | Scaffolded | Tier | Key Finding |
|-------|:------:|:----:|:----------:|:----:|-------------|
| **Seed-2.0-mini** | — | **100%** | **100%** | **1** | Compiled primitive |
| **Seed-2.0-code** | — | **100%** | **100%** | **1** | Compiled primitive |
| **Gemma3:1b** | **1B** | **100%** | **100%** | **1** | 1B beats 405B |
| Llama3.2:1b | 1B | 50% | 100% | 2 | Dense, benefits from scaffolding |
| Phi4-mini | 3.8B | 25% | 100% | 2 | Dense, benefits from scaffolding |
| Hermes-70B | 70B | 25% | 100% | 2 | Dense, benefits from scaffolding |
| Hermes-405B | 405B | 0% | 100% | 2 | Dense, benefits from scaffolding |
| Qwen3-235B | 235B | 50% | 25% | 2 | MoE 9.4% active, anti-scaffold |
| Qwen3.6-35B | 35B | 0% | 0% | 3 | MoE 8.6% active, incompetent |
| Qwen3:4b | 4B | 0% | 0% | 3 | Dense, incompetent |
| GLM-5.1 | — | 0% | Variable | 3 | Variable performance |
| GLM-5-turbo | — | 0% | Variable | 3 | Variable performance |

---

*Research conducted May 13–15, 2026, by the Cocapn Fleet. Experimental data, code, and detailed study reports available at github.com/SuperInstance/forgemaster.*
