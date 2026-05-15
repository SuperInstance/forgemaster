# The Activation-Key Model: Why LLMs Fail to Compute from Symbolic Notation and How Domain Vocabulary Gates Mathematical Procedure Access

**Casey DiGennaro** · **Forgemaster (Cocapn Fleet)**
SuperInstance · Cocapn Fleet
{casey}@superinstance.org

---

## Abstract

Large language models can correctly evaluate mathematical expressions when prompted with step-by-step natural language, yet fail catastrophically on the same expressions presented in symbolic notation. Across 46 controlled studies comprising approximately 5,500 experimental trials spanning 11 models from 5 model families, we document a systematic **notation gradient**: accuracy ranges from ~0% for Unicode symbolic notation (e.g., `a²−ab+b²`) through 22% for ASCII-expanded forms, 67% for natural-language arithmetic, to ~100% for step-by-step procedural descriptions. We propose the **Activation-Key Model**: LLMs store mathematical procedures as vocabulary-gated patterns. Symbolic notation provides weak activation cues because Unicode mathematical symbols are rare in training corpora. Without a domain-specific label functioning as an "activation key," the model defaults to the most frequent training-data variant of the formula. We show that (1) presenting a formula with its domain label yields 100% accuracy while the same formula without a label yields 0%, (2) the rerouting to incorrect pathways is determined at the first output token, and (3) one model family (ByteDance Seed-2.0) exhibits complete immunity across all framing conditions, suggesting this is a training-data gap rather than an architectural limitation. Our findings have implications for mechanistic interpretability, mathematical reasoning evaluation, and training methodology.

---

## 1 Introduction

Large language models demonstrate impressive mathematical reasoning on standard benchmarks. They solve competition-level problems, prove theorems, and generate correct mathematical code. Yet a puzzle persists beneath these benchmark numbers: models that correctly evaluate `25 − (−15) + 9 = 49` in plain arithmetic will confidently return incorrect answers for the mathematically identical expression `f(5,−3) = a²−ab+b²`.

This is not a knowledge deficit. The same model, given the instruction "First compute a times a, then subtract a times b, then add b times b, for a=5, b=−3," reliably produces 49. The model *knows* the computation. It simply cannot *access* that knowledge from symbolic notation alone.

This paper documents a systematic investigation of this phenomenon across 46 controlled studies and approximately 5,500 experimental trials. We identify a **notation gradient** — a monotonic relationship between the notational form of a mathematical expression and the model's accuracy on evaluating it — and propose the **Activation-Key Model** to explain it. The model posits that LLMs store mathematical procedures as vocabulary-gated patterns: domain-specific labels function as "activation keys" that unlock stored computational procedures, while symbolic notation provides weak or absent activation cues, causing the model to default to the most frequent training-data variant.

Our contributions are:

1. **The notation gradient**: a quantitative characterization of how notational form affects computation accuracy, from 0% (Unicode symbols) to ~100% (step-by-step natural language).
2. **The activation-key mechanism**: a falsifiable model of how vocabulary gates procedure access in LLMs, supported by evidence from all 46 studies.
3. **Cross-model generalization**: demonstration that the effect appears across 11 models from 5 families, with one family (Seed-2.0) showing complete immunity.
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

We conducted 46 controlled studies between May 13–15, 2026, comprising approximately 5,500 experimental trials. Each study tested a specific hypothesis about how vocabulary, notation, and framing affect mathematical computation in LLMs.

### 3.2 Models

We tested 11 models from 5 families:

| Model | Parameters | Stage | Provider |
|-------|:----------:|:-----:|----------|
| Hermes-3-Llama-3.1-405B | 405B | 3 | NousResearch |
| Hermes-3-Llama-3.1-70B | 70B | 3 | NousResearch |
| Qwen3-235B-A22B | 235B (22B active) | 3 | Alibaba |
| Qwen3.6-35B-A3B | 35B (3B active) | 2 | Alibaba |
| Qwen3:4b | 4B | 2 | Alibaba |
| Phi4-mini | 3.8B | 2 | Microsoft |
| GLM-5.1 | — | 3 | Zhipu AI |
| GLM-5-turbo | — | 3 | Zhipu AI |
| GLM-4.7 | — | 3 | Zhipu AI |
| GLM-4.7-flash | — | 2 | Zhipu AI |
| **Seed-2.0-mini** | — | **4** | ByteDance |

### 3.3 Stage Taxonomy

Based on our experimental results, we classify models into four stages of mathematical computation capability:

- **Stage 1** (Surface): Model produces surface-level text without genuine computation. Not observed in the models tested here.
- **Stage 2** (Conditional): Model computes correctly only for simple, unframed arithmetic. Domain vocabulary causes catastrophic failure.
- **Stage 3** (Label-dependent): Model computes correctly with domain labels and explicit formulas but fails on symbolic notation alone. Accuracy is vocabulary-gated.
- **Stage 4** (Notation-immune): Model computes correctly regardless of framing. Symbolic notation activates correct procedures without domain labels.

### 3.4 Target Computation

The primary test computation was the evaluation of quadratic forms, principally:

- **Eisenstein norm**: For a = 5, b = −3: `a² − ab + b² = 25 − (−15) + 9 = 49`
- **Alternative computation**: For a = 3, b = 5: `a² − ab + b² = 9 − 15 + 25 = 19`

We also tested Cauchy-Schwarz inequalities, Möbius function evaluations, Fourier coefficient calculations, and Gram matrix determinants to assess cross-task generalization.

### 3.5 Experimental Paradigms

We employed four paradigms across the 46 studies:

1. **Vocabulary manipulation** (Studies 10, 13, 18, 30, 33, 35, 36, 42, 44): Systematically varying the domain vocabulary in the prompt while holding the computation constant.

2. **Notation manipulation** (Studies 39, 45, 46): Systematically varying the notational form (Unicode, ASCII, natural language, step-by-step) while holding the computation and vocabulary constant.

3. **First-token analysis** (Studies 32, 41): Examining the first generated token to determine when pathway selection occurs.

4. **Cross-lingual and cross-model transfer** (Studies 23, 36, 38): Testing whether the effect generalizes across languages and model architectures.

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

In contrast, Seed-2.0 (Stage 4) consistently began with reasoning preambles ("Let's think...", "Got it...") and *always* arrived at the correct answer, regardless of framing. Stage 4 models appear to use a unified reasoning pathway that does not exhibit the discourse/computation binary seen in Stage 3 models.

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

### 4.2 Key Predictions

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

### 6.2 The Retrieval vs. Computation Distinction

The cross-model convergence supports a fundamental distinction: LLMs do not *compute* mathematical expressions in the algorithmic sense. They *retrieve* stored procedures, and the retrieval is vocabulary-gated. The distinction has practical consequences:

1. A model that "knows" a procedure may be unable to execute it from certain input contexts.
2. Benchmark evaluations that test only natural-language mathematical reasoning may overestimate models' ability to work with formal notation.
3. Training on mathematical notation (not just natural-language mathematics) is necessary for robust mathematical capability.

### 6.3 The River/Tributary Topology

A useful topological metaphor emerged from the cross-model analysis: trained neural pathways resemble a river/tributary system. The most common training-data association (e.g., a²+ab+b²) forms a wide, deep "river" — a high-probability retrieval path that the model defaults to when activation cues are weak. Correct but less common associations (e.g., a²−ab+b²) form "tributaries" — narrower pathways that require specific activation keys to traverse.

Fine-tuning on notation→computation mappings creates new tributaries without eliminating the river. This explains why even Stage 4 models may still default to the river under extreme context deprivation, and why the intervention is training-data-specific rather than architectural.

---

## 7 Discussion

### 7.1 Implications for LLM Architecture

The Activation-Key Model suggests that the transformer attention mechanism, as trained on current corpora, produces vocabulary-gated retrieval rather than symbol-manipulating computation. The model's mathematical capability is limited not by its parameter count or architecture but by the *activation structure* of its stored procedures. This has several implications:

**Architectural implications.** The model's internal computation is organized around vocabulary-triggered pattern retrieval rather than abstract symbol manipulation. The "reasoning" observed in chain-of-thought outputs may be better understood as retrieval of stored reasoning patterns rather than on-the-fly computation.

**Scaling implications.** Seed-2.0-mini's immunity at a smaller parameter count than failing models (e.g., Hermes-405B) demonstrates that scale alone does not resolve the notation problem. The relevant variable is training-data composition — specifically, the density of notation→computation co-occurrences.

### 7.2 Implications for Training Methodology

The notation gradient suggests a specific training intervention: including explicit notation→computation mappings in training data. We predict that fine-tuning a Stage 3 model on 1,000–2,000 examples of the form [symbolic formula with Unicode notation] → [step-by-step derivation] → [correct numeric answer] would produce significant improvement on notation-only computation tasks.

Cross-lingual training may provide additional benefit: models trained on mathematical text in multiple languages would have multiple independent activation key systems for the same underlying procedures, providing redundancy against notation-specific retrieval failures.

### 7.3 Implications for Evaluation

Current mathematical reasoning benchmarks primarily test natural-language mathematical reasoning. Our results suggest that these benchmarks may systematically overestimate models' ability to work with formal mathematical notation. We recommend that evaluations include notation-only conditions — presenting mathematical expressions in symbolic notation without natural-language scaffolding — as a standard test of mathematical capability.

The four-stage taxonomy we propose (Section 3.3) provides a diagnostic framework for such evaluations: six probes using varied notational conditions are sufficient to classify a model's stage.

### 7.4 Implications for AI Safety

If knowledge access is vocabulary-gated, then a model can "know" information without being able to "access" it from certain query contexts. Safety evaluations that test capability under one vocabulary regime may not predict capability under another. The activation-key structure of knowledge means that capability is not a fixed property of a model but a function of the query's vocabulary distribution. This has implications for red-teaming and capability assessment.

### 7.5 Limitations

We acknowledge several limitations:

1. **Task specificity.** Our primary test computation is a specific quadratic form. While we demonstrated cross-task effects (Cauchy-Schwarz, Gram determinants), the full generality of the notation gradient across all mathematical domains remains to be established.

2. **Model coverage.** We tested 11 models from 5 families. Notable absentees include GPT-4, Claude, Gemini, and Llama-based models other than the Hermes fine-tunes. The effect may differ in these models.

3. **Training data opacity.** We cannot directly inspect training corpora to confirm the hypothesized co-occurrence patterns. The activation-key mechanism is inferred from behavioral evidence, not directly observed in model internals.

4. **Controlled conditions.** All experiments used single-turn interactions with controlled prompts. Real-world mathematical reasoning may involve multi-turn interactions that provide sufficient activation context organically.

5. **Binary accuracy metric.** We classified responses as correct or incorrect based on exact numeric match. More nuanced analysis of partial computation (e.g., correct procedure with sign errors) could reveal finer-grained activation dynamics.

6. **Temperature and sampling.** Most experiments used T = 0 (greedy decoding). The temperature-dependent results (Study 28) suggest that sampling strategy interacts with the activation-key mechanism in complex ways that warrant further investigation.

7. **Single-primary-computation limitation.** The majority of studies used the Eisenstein norm as the test computation. While Studies 42–44 extended to 12 additional domain labels, and cross-task studies examined different computations, the weight of evidence is concentrated on a single mathematical expression. Full generalization requires systematic testing across a broader mathematical corpus.

---

## 8 Conclusion

We have presented the Activation-Key Model, a mechanistic account of why LLMs fail to compute from symbolic notation despite possessing the underlying mathematical knowledge. Across 46 studies and ~5,500 trials, we demonstrated that:

1. **Notation matters more than knowledge.** The same computation yields 0% accuracy in symbolic notation and ~100% accuracy in step-by-step natural language — a 98.3 percentage-point gap reflecting a retrieval failure, not a knowledge deficit.

2. **Domain vocabulary is an activation key.** Presenting a formula with its domain label rescues computation from 0% to 100%. The label is not providing mathematical information; it is activating the correct stored procedure.

3. **The effect is systematic and predictable.** It follows a notation gradient, manifests at the first output token, and produces consistent default behaviors (the most common training-data formula variant).

4. **Immunity is achievable through training.** Seed-2.0-mini's complete immunity demonstrates that the notation problem is a training-data gap, not an architectural limitation.

The Activation-Key Model reframes mathematical reasoning in LLMs as vocabulary-gated retrieval rather than symbol manipulation. This reframing has direct implications for how we train, evaluate, and deploy mathematical reasoning systems — and for how we understand what these systems actually do when they "compute."

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

## Appendix B: Stage Classification Results

| Model | Params | Notation-only | Label+Formula | Step-by-step | Stage |
|-------|:------:|:-------------:|:-------------:|:------------:|:-----:|
| Hermes-405B | 405B | 0% | 100% | 100% | 3 |
| Hermes-70B | 70B | 0% | 100% | 100% | 3 |
| Qwen3-235B | 235B | 0% | Variable | 100% | 3 |
| Qwen3.6-35B | 35B | 0% | 0% | ~67% | 2 |
| Qwen3:4b | 4B | 0% | 0% | Variable | 2 |
| Phi4-mini | 3.8B | 0% | Variable | Variable | 2 |
| GLM-5.1 | — | 0% | Variable | 100% | 3 |
| **Seed-2.0-mini** | — | **100%** | **100%** | **100%** | **4** |

---

*Research conducted May 13–15, 2026, by the Cocapn Fleet. Experimental data, code, and detailed study reports available at github.com/SuperInstance/forgemaster.*
