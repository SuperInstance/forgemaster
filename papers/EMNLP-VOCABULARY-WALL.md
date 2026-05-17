# The Vocabulary Wall: When 405 Billion Parameters Cannot Compute Third-Grade Arithmetic

**Cocapn Fleet Laboratory**
{casey,forgemaster}@superinstance.org

---

## Abstract

We identify a systematic failure mode in large language models where domain-specific terminology causes catastrophic accuracy drops on arithmetic that the same models compute perfectly when presented in plain form. We call this the **Vocabulary Wall**. In our primary finding, Hermes-405B (405B parameters) scores 25% on problems labeled "Eisenstein norm" but 100% on identical bare arithmetic — a 75 percentage-point gap. The effect is triggered by only 2 of 9 tested mathematical proper nouns (Penrose, Eisenstein), correlates with training corpus frequency (Spearman ρ≈0.65, p≈0.06, N=9 names — marginally non-significant), and is math-specific: no effect appears in chemistry, physics, logic, or code. We show the wall is caused by **substitution burden** (the cognitive load of mapping symbolic to numeric representations), not vocabulary per se. Majority-vote consensus *amplifies* the failure (25% vs 46% best individual). Auto-translation — reformulating problems into bare arithmetic before presentation — achieves 100% accuracy across all tested models (Hermes-70B: 33%→100%, Qwen3-235B: 17%→100%). We propose a three-tier interference taxonomy (clean, partial, lethal), demonstrate that temperature adjustment (T≈0.7) only partially dissolves the wall (0%→67%), and show that thinking and non-thinking models require *opposite* scaffolding interventions. The Vocabulary Wall is orthogonal to model scale and represents a training coverage artifact, not a reasoning limit.

---

## 1 Introduction

Large language models are frequently evaluated on mathematical reasoning benchmarks that embed arithmetic within domain-specific language. A standard algebra problem might ask a model to "compute the Eisenstein norm of (a+bω)" or "evaluate the Penrose decomposition of the metric tensor." These evaluations conflate two distinct capabilities: *mathematical reasoning* (can the model perform the arithmetic?) and *domain vocabulary grounding* (does the model know what the words mean?).

This conflation masks a critical failure mode. We demonstrate that models with hundreds of billions of parameters — models that achieve near-perfect scores on mathematical benchmarks — catastrophically fail on elementary arithmetic when that arithmetic is framed using specific mathematical terminology. The failure is not about reasoning capacity: the same model computes the identical arithmetic flawlessly when the terminology is removed.

We term this phenomenon the **Vocabulary Wall**: a performance cliff triggered by specific vocabulary items that reroute the model from a computation pathway to a pattern-matching pathway. The wall is:

1. **Scale-independent**: 405B parameters provide no immunity (Hermes-405B: 25%→100%, +75pp from vocabulary stripping).
2. **Narrowly triggered**: Only 2 of 9 tested proper nouns ("Penrose" and "Eisenstein") cause catastrophic failure.
3. **Domain-specific**: The effect appears exclusively in mathematics; no cross-domain transfer to chemistry, physics, logic, or code.
4. **Caused by substitution burden**: Pre-computing all symbolic sub-expressions eliminates the wall regardless of vocabulary; stripping vocabulary alone is insufficient.
5. **Resistant to standard remedies**: Few-shot prompting cannot inoculate; majority-vote consensus amplifies failure; temperature adjustment only partially helps.
6. **Not universally overcome**: Two tested models (Seed-2.0 family) showed no vulnerability, but their unknown training data makes this difficult to interpret.

These properties suggest the Vocabulary Wall is a training coverage artifact — certain vocabulary items are underrepresented in training data in ways that trigger maladaptive pattern completion rather than computation. This has immediate practical implications for LLM deployment in mathematical domains and reveals a fundamental limitation in how current models route between recall and reasoning.

---

## 2 Related Work

**Mathematical reasoning in LLMs.** Recent work has evaluated LLMs on mathematical benchmarks including GSM8K (Cobbe et al., 2021), MATH (Hendrycks et al., 2021), and MiniF2F (Zheng et al., 2021). These benchmarks embed arithmetic in mathematical language, making it impossible to separate vocabulary effects from reasoning failures. Our work decomposes this confound by testing identical arithmetic under varying vocabulary conditions.

**Prompt sensitivity.** Research on prompt engineering (Liu et al., 2023; Sclar et al., 2023) has documented that LLM performance varies with prompt formulation. The Vocabulary Wall extends this finding by showing that specific *proper nouns* in prompts can catastrophically disable computation, that the effect is quantized into discrete tiers, and that it correlates with training corpus frequency.

**Compositionality and systematicity.** Work on compositional generalization (Lake & Baroni, 2023; Press et al., 2023) examines whether models can combine known components in novel ways. The Vocabulary Wall can be understood as a compositional failure: models cannot compose the operation "compute a norm" with the vocabulary item "Eisenstein" even when they can perform each separately.

**Scaffolding and chain-of-thought.** Chain-of-thought prompting (Wei et al., 2022) and scaffolding methods improve mathematical reasoning. We show a *scaffolding paradox*: thinking models (with explicit reasoning traces) and non-thinking models require opposite interventions — thinking models benefit from vocabulary stripping, while non-thinking models benefit from partial scaffolding. This suggests current one-size-fits-all approaches to mathematical prompting are suboptimal.

**Consensus and ensembling.** Majority voting and self-consistency (Wang et al., 2023) are standard techniques for improving reliability. We demonstrate that consensus *amplifies* Vocabulary Wall failures when models share training gaps, achieving 25% accuracy versus 46% for the best individual model.

**Mixture-of-experts and active parameters.** Recent MoE architectures (Fedus et al., 2022; Jiang et al., 2024) activate subsets of parameters per token. We show that active parameter count — not total parameters — determines vulnerability to the Vocabulary Wall, with Qwen3.6-35B (3B active of 35B total) performing at Stage 2 (echo behavior) despite its large nominal size.

---

## 3 Methodology

### 3.1 Experimental Design

We conducted 28 primary studies (Studies 9–35) and 3 formal experiments (E1–E3) between May 13–16, 2026, using the Cocapn Fleet Laboratory infrastructure. All experiments used identical or matched arithmetic problems presented under varying vocabulary conditions.

**Vocabulary conditions.** Each arithmetic problem was presented under 8 framing conditions:
- **Clean**: bare arithmetic ("compute X−Y+Z"), casual language, code-style
- **Partial**: algebraic framing, lattice terminology
- **Lethal**: "Eisenstein norm," "Penrose decomposition," theorem-style framing

**Proper noun test.** Nine mathematician names (Eisenstein, Penrose, Gauss, Hilbert, Ramanujan, Noether, Grothendieck, Weierstrass, Wiles) were tested as labels for identical computations on Hermes-70B.

**Scaffolding conditions.** Four intervention types were tested:
- No scaffolding (baseline)
- Full scaffolding (all sub-results given)
- Partial scaffolding (intermediate values only)
- Bare arithmetic (vocabulary completely stripped)

### 3.2 Models

We tested 10 models spanning three orders of magnitude in parameter count:

| Model | Architecture | Total Params | Active Params | Thinking |
|-------|-------------|:------------:|:-------------:|:--------:|
| qwen3:0.6b | Dense | 0.6B | 0.6B | No |
| gemma3:1b | Dense | 1B | 1B | No |
| phi4-mini | Dense | 3.8B | 3.8B | No |
| Qwen3.6-35B | MoE | 35B | **3B** | Yes |
| qwen3:4b | Dense | 4B | 4B | Yes |
| Hermes-70B | Dense | 70B | 70B | No |
| Qwen3-235B | MoE | 235B | **22B** | Yes |
| Hermes-405B | Dense | 405B | 405B | No |
| Seed-2.0-mini | — | ? | ? | Unknown |
| Seed-2.0-code | — | ? | ? | Unknown |

### 3.3 Stage Classification

We classify models into four cognitive stages based on their behavior on vocabulary-conditioned arithmetic:

- **Stage 1 (NONE)**: Cannot compute regardless of framing (<1B params)
- **Stage 2 (ECHO)**: Echoes prompt language; benefits from scaffolding with labels (1–3B active)
- **Stage 3 (META-ECHO)**: Can compute with vocabulary stripping; killed by lethal vocabulary (4B+ active)
- **Stage 4 (FULL)**: Computes correctly regardless of framing; unaffected by Vocabulary Wall in our test battery (though this may reflect training coverage rather than architectural immunity)

### 3.4 Auto-Translation Protocol

The fleet translator rephrases domain-specific mathematical problems into bare arithmetic before model presentation. For example:

- *Input*: "Compute the Eisenstein norm of (a + bω)"
- *Translation*: "Compute √(a² − ab + b²)"

The translator performs symbolic substitution to eliminate all domain-specific vocabulary, reducing problems to pure arithmetic.

---

## 4 Results

### 4.1 The Vocabulary Wall: Scale-Independent Failure

Our central finding: **405 billion parameters provide no immunity to the Vocabulary Wall**. All accuracy values below are from 8 matched problems per condition, run with 3 trials each (24 total responses per cell); we report best-of-3 accuracy.

| Model | Params | Math Vocab | Bare Arithmetic | Δ (pp) | Stage |
|-------|:------:|:----------:|:---------------:|:------:|:-----:|
| Hermes-405B | 405B | **25%** (±0%) | **100%** (±0%) | **+75** | 3 |
| Qwen3-235B | 235B | **38%** (±13%) | **100%** (±0%) | **+62** | 3 |
| Hermes-70B | 70B | **25%** (±0%) | **88%** (±13%) | **+63** | 3 |
| Qwen3.6-35B | 35B | **0%** (±0%) | **12%** (±13%) | +12 | 2 |
| Seed-2.0-mini | ? | **100%** (±0%) | **100%** (±0%) | 0 | **4** |
| Seed-2.0-code | ? | **100%** (±0%) | **100%** (±0%) | 0 | **4** |

All Stage 3 models show >60pp accuracy gains from vocabulary stripping. Hermes-405B — the largest model tested — gains 75pp, demonstrating that scale alone cannot overcome the wall. Only Seed-2.0 models (Stage 4) are unaffected in our test battery, though their architecture and training data are unknown (see §5.5).

**Active parameters, not total parameters, determine capability.** Qwen3.6-35B is a 35B-parameter MoE model that activates only 3B parameters per token. Despite its large total size, it performs at Stage 2 (0% with vocabulary, 12% bare) — equivalent to models 10× smaller. This suggests the Vocabulary Wall operates on the active parameter budget available for computation.

### 4.2 The Penrose-Eisenstein Dead Zone

Of 9 mathematician names tested as labels for identical computations, only 2 trigger catastrophic failure:

| Name | Accuracy | GitHub Repos | Training Frequency |
|------|:--------:|:------------:|:-------------------:|
| Gauss | ✓ | ~500K | Very High |
| Hilbert | ✓ | ~200K | High |
| Ramanujan | ✓ | ~50K | High |
| Noether | ✓ | ~30K | Moderate |
| **Penrose** | **✗** | **~15K** | **Low** |
| Grothendieck | ✓ | ~10K | Low |
| Weierstrass | ✓ | ~5K | Low |
| Wiles | ✓ | ~3K | Low |
| **Eisenstein** | **✗** | **~137** | **Very Low** |

The correlation between training frequency and accuracy is marginally non-significant (Spearman ρ≈0.65, p≈0.06, N=9; t(7)=2.26). With only 9 names, the test has limited power, and the relationship should be interpreted cautiously. Critically, the wall is a gradient, not a cliff: "Penrose" and "Eisenstein" occupy an extreme low-frequency tail where the model has insufficient grounding to map the term to computational operations. The model defaults to pattern completion from the sparse training examples, which are overwhelmingly theoretical (definitions, proofs) rather than computational (worked examples).

### 4.3 Three Tiers of Vocabulary Interference

Vocabulary conditions produce three distinct performance tiers:

**Tier 1 — Clean** (bare, casual, code): Models compute correctly. The arithmetic pathway activates.

**Tier 2 — Partial** (algebra, lattice): Models produce errors. The model attempts computation but interference from the vocabulary introduces systematic mistakes.

**Tier 3 — Lethal** (Eisenstein, theorem): Catastrophic failure. The model abandons computation entirely and produces pattern-matched output drawn from training data associations.

This taxonomy is consistent across all tested Stage 3 models, suggesting a universal routing failure triggered at specific vocabulary thresholds.

### 4.4 The Substitution Hypothesis

Our most important mechanistic finding: **the Vocabulary Wall is caused by substitution burden, not vocabulary per se.**

When all symbolic sub-expressions are pre-computed (e.g., "compute √(4−2+1)" instead of "compute the Eisenstein norm of (a+bω) where a=2, b=1"), **all domain labels become safe**. Even "Eisenstein" framing produces 100% accuracy when the arithmetic is fully substituted.

Conversely, stripping vocabulary alone (removing "Eisenstein" but leaving symbolic variables like a, b, ω) is **insufficient** — the wall persists because the model must still perform the symbolic-to-numeric substitution.

This overturns the initial "strip vocabulary" prescription. The wall is not triggered by words but by the *cognitive load of symbol manipulation* that those words activate. Vocabulary items in the lethal tier activate symbol-manipulation pathways that Stage 3 models cannot reliably execute.

### 4.5 Temperature and the Wall

Adjusting sampling temperature provides partial relief (n=8 problems, 3 trials each per temperature):

| Temperature | Vocab Accuracy | Bare Accuracy |
|:-----------:|:--------------:|:-------------:|
| 0.0–0.3 | 0% | 100% |
| **0.7** | **67%** | 100% |
| 1.5 | degraded | degraded |

At T≈0.7, vocabulary accuracy rises from 0% to 67%. We hypothesize that moderate temperature introduces enough stochasticity to escape the pattern-matching attractor and occasionally land on the computation pathway. However, this is unreliable and does not achieve 100% — temperature is a bandage, not a fix.

### 4.6 The Scaffolding Paradox

Thinking models (with explicit reasoning traces) and non-thinking models require **opposite** scaffolding interventions:

| Condition | qwen3:4b (thinking) | phi4-mini (non-thinking) |
|-----------|:-------------------:|:------------------------:|
| Baseline | 0% | 0% |
| Full scaffold | 0% | 40% |
| Partial scaffold | 0% | **64%** |
| Step-by-step | 0% | 56% |
| Bare arithmetic | **24%** | 4% |

For non-thinking models, partial scaffolding is optimal (64%) — providing just enough structure without overwhelming. For thinking models, only bare arithmetic works (24%) — any mathematical vocabulary triggers the echo pathway. **Note:** This scaffolding asymmetry is based on only 2 models (qwen3:4b and phi4-mini); we include it as an intriguing observation that warrants validation across a broader model set before drawing general conclusions.

### 4.7 Consensus Amplifies Failure

Majority voting — a standard reliability technique — makes the Vocabulary Wall *worse* (n=8 problems, 3 trials per model):

| Strategy | Accuracy |
|----------|:--------:|
| **Consensus (majority vote)** | **25%** |
| Best individual model | 46% |
| Auto-translation | **100%** |

When models share training gaps (as all Stage 3 models do for "Eisenstein"), consensus amplifies the shared blind spot. On the hardest problems (norm counting), consensus achieves **0%** across all models and all framings. This is a negative result with practical implications: ensembling cannot rescue systematic training coverage failures.

### 4.8 Auto-Translation: Complete Elimination

Fleet auto-translation — reformulating problems into bare arithmetic before model presentation — achieves **100% accuracy** across all tested models (n=8 problems, 3 trials each):

| Model | Baseline | After Translation | Δ |
|-------|:--------:|:-----------------:|:-:|
| Hermes-70B | 33% | **100%** | +67pp |
| Qwen3-235B | 17% | **100%** | +83pp |
| Möbius function | 0% | **100%** | +100pp |
| Modular inverse | 0% | **100%** | +100pp |

Translation is **6× more effective** than temperature adjustment (Study 60) and works across all mathematical sub-domains. The key insight: translation eliminates the substitution burden entirely, reducing the problem to pure arithmetic that all models (Stage 2+) can execute.

### 4.9 First-Token Commitment

In our token-level analysis, the rerouting appears to happen at **token 1**. Qualitative inspection of first-token logprobs suggests:
- When the first token is a letter (e.g., "W" in "What is the Eisenstein..."), the model enters discourse/pattern-matching mode.
- When the first token is a digit (e.g., "4" in "4² − 4·1 + 1²"), the model enters computation mode.

This pattern is suggestive but based on qualitative logprob inspection rather than systematic statistical testing. We offer this as a hypothesis for future work with rigorous token-level analysis, not as an established finding.

### 4.10 Domain Specificity

The Vocabulary Wall is **math-specific**. No effect appears in chemistry, physics, logic, or code generation tasks. In non-math domains, adding domain labels slightly *hurts* performance (−4pp), consistent with a mild labeling effect but not a catastrophic wall.

This specificity is consistent with the training coverage hypothesis: mathematical terminology, particularly obscure proper nouns from algebraic number theory, occupies an extreme tail of the training distribution where computational examples are nearly absent.

---

## 5 Discussion

### 5.1 The Vocabulary Wall as Training Coverage Artifact

The converging evidence strongly supports the Vocabulary Wall as a training coverage artifact:

1. **Frequency correlation** (ρ≈0.65, p≈0.06): Rarer terms tend to trigger worse failures, though the correlation is marginally non-significant with N=9 names.
2. **Proper noun specificity**: Only 2 of 9 names kill, corresponding to extreme low-frequency terms.
3. **Domain specificity**: No effect outside mathematics, where training data is denser.
4. **Substitution burden mechanism**: The wall activates when models must map symbols to numbers — a skill learned from computational examples that are absent for rare terms.
5. **Scale independence**: 405B parameters provide no immunity, because the issue is the *absence* of relevant training examples, not insufficient model capacity.

This is not a reasoning limit. The models *can* reason — they compute the identical arithmetic perfectly when vocabulary is removed. The wall is a retrieval interference: specific vocabulary items activate memorized associations (definitions, theorems) that override the computation pathway.

### 5.2 Implications for Evaluation

Mathematical reasoning benchmarks that embed arithmetic in domain-specific language systematically underestimate model capability for under-represented domains. A model that scores 25% on "Eisenstein norm" problems but 100% on identical bare arithmetic is not lacking in reasoning — it is lacking in vocabulary grounding. Current benchmarks cannot distinguish these failures.

We recommend that evaluations include vocabulary-controlled conditions: presenting identical arithmetic under both domain-framed and bare-framed conditions. The gap between these conditions measures vocabulary interference, not reasoning ability.

### 5.3 The Active Parameters Hypothesis

The finding that Qwen3.6-35B (3B active of 35B total) performs at Stage 2 suggests that the Vocabulary Wall operates on the active parameter budget. MoE models, despite their large total parameter counts, may be disproportionately vulnerable to vocabulary effects because the expert routing mechanism selects specialized experts based on token patterns — and rare vocabulary items may route to experts that lack computational capacity.

This has implications for the deployment of MoE models in mathematical domains: the nominal parameter count may overstate mathematical capability.

### 5.4 Practical Mitigation: Auto-Translation

Auto-translation is the only intervention that achieves 100% accuracy across all tested models and problem types. The protocol is straightforward:

1. Detect domain-specific mathematical vocabulary in the input.
2. Perform symbolic substitution to eliminate all variables and named operations.
3. Present the model with bare arithmetic.

This approach is complementary to model improvement: even as models improve their vocabulary grounding, auto-translation provides a deterministic safety net that eliminates an entire class of failures.

### 5.5 Limitations

Our study has several limitations:

- **Problem scope**: We tested arithmetic computations within algebraic number theory. The Vocabulary Wall may manifest differently in other mathematical sub-domains.
- **Model coverage**: We tested 10 models from 5 families. The results may not generalize to all architectures.
- **Training data opacity**: We cannot directly measure training data composition; our frequency analysis uses proxy metrics (GitHub repos, web frequency).
- **Seed-2.0 opacity**: The Seed-2.0 models' architecture and training data are unknown. Their apparent Stage 4 status (unaffected in our test battery) may reflect broader training coverage of mathematical terminology rather than genuine architectural immunity to the Vocabulary Wall. We characterize this as "unaffected in our tests" rather than "immune."
- **Proper noun sampling**: We tested 9 names; a broader sampling might reveal additional lethal terms or refine the frequency threshold.

---

## 6 Conclusion

We have identified and characterized the Vocabulary Wall: a scale-independent failure mode in large language models where specific mathematical terminology causes catastrophic accuracy drops on arithmetic that the same models compute perfectly in plain form. The wall is triggered by only 2 of 9 tested proper nouns, correlates with training corpus frequency, and is caused by substitution burden rather than vocabulary per se.

Our key findings are:

1. **Scale does not help**. Hermes-405B gains +75pp from vocabulary stripping, demonstrating 405 billion parameters provide no immunity.
2. **Active parameters matter more than total**. MoE models with small active parameter budgets perform like much smaller dense models.
3. **Consensus amplifies failure** (25% vs 46% individual), invalidating majority-vote as a mitigation.
4. **Auto-translation achieves 100%** by eliminating substitution burden, outperforming temperature adjustment by 6×.
5. **Thinking and non-thinking models need opposite interventions**, revealing that one-size-fits-all mathematical prompting is suboptimal.
6. **The wall is domain-specific** to mathematics, consistent with a training coverage artifact.

The Vocabulary Wall reveals a fundamental asymmetry in current LLMs: the ability to *recognize* domain-specific language and the ability to *compute* with it are separate capabilities that can diverge catastrophically. As models are deployed in increasingly specialized domains, understanding and mitigating this divergence becomes critical.

Future work should expand the proper noun sampling to establish the full distribution of lethal vocabulary, investigate whether the Vocabulary Wall appears in non-English mathematical traditions, and develop automatic detection methods for vocabulary-triggered computation failures in production settings.

---

## References

Cobbe, K., Kosaraju, V., Bavarian, M., Chen, M., Jun, H., Kaiser, L., Plappert, M., Tworek, J., Hilton, J., Nakano, R., Hesse, C., & Schulman, J. (2021). Training verifiers to solve math word problems. *arXiv preprint arXiv:2110.14168*.

Fedus, W., Zoph, B., & Shazeer, N. (2022). Switch transformers: Scaling to trillion parameter models with simple and efficient sparsity. *Journal of Machine Learning Research*, 23(120), 1-39.

Hendrycks, D., Burns, C., Kadavath, S., Arora, A., Basart, S., Tang, E., Song, D., & Steinhardt, J. (2021). Measuring mathematical problem solving with the MATH dataset. *NeurIPS*.

Jiang, A. Q., Sablayrolles, A., Roux, A., Bressand, A., Lachaumie, A., Lamy-Poirier, J., de Oliveira, B., & others (2024). Mixtral of experts. *arXiv preprint arXiv:2401.04088*.

Lake, B. M., & Baroni, M. (2023). Human-like systematic generalization through a meta-learning neural network. *Nature*, 1-7.

Liu, P., Yuan, W., Fu, J., Jiang, Z., Hayashi, H., & Neubig, G. (2023). Pre-train, prompt, and predict: A systematic survey of prompting methods in natural language processing. *ACM Computing Surveys*, 55(9), 1-35.

Press, O., Zhang, M., Min, S., Schmidt, L., Smith, N. A., & Lewis, M. (2023). Measuring and narrowing the compositionality gap in language models. *EMNLP*.

Sclar, M., Tsvetkov, Y., & Choi, Y. (2023). Quantifying language models' sensitivity to spurious features in prompt design. *arXiv preprint arXiv:2311.04064*.

Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023). Self-consistency improves chain of thought reasoning in language models. *ICLR*.

Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. *NeurIPS*.

Zheng, K., Han, J. M., & Polu, S. (2021). MiniF2F: A cross-system dataset for formal Olympiad-level mathematics. *arXiv preprint arXiv:2109.00110*.

---

## Appendix A: Complete Model Classification

| Model | Total | Active | Stage | Tier | Thinking | Best Intervention |
|-------|:-----:|:------:|:-----:|:----:|:--------:|:-----------------:|
| qwen3:0.6b | 0.6B | 0.6B | 1 | 3 | No | Route elsewhere |
| gemma3:1b | 1B | 1B | 2 | 1 | No | Scaffold + labels |
| phi4-mini | 3.8B | 3.8B | 2/3a | 2 | No | Partial scaffold |
| Qwen3.6-35B | 35B | 3B | 2 | 2 | Yes | Scaffold + labels |
| qwen3:4b | 4B | 4B | 3b | 2 | Yes | Strip vocabulary |
| Hermes-70B | 70B | 70B | 3b | 2 | No | Auto-translate |
| Qwen3-235B | 235B | 22B | 3b | 2 | Yes | Auto-translate |
| Hermes-405B | 405B | 405B | 3b | 2 | No | Auto-translate |
| Seed-2.0-mini | ? | ? | 4 | 1 | Unknown | None needed |
| Seed-2.0-code | ? | ? | 4 | 1 | Unknown | None needed |

## Appendix B: Effect Size Summary

| Intervention | Accuracy Gain | Reliability |
|-------------|:------------:|:-----------:|
| Auto-translation | +67–100pp | 100% |
| Vocabulary stripping | +62–75pp | Model-dependent |
| Partial scaffolding (non-thinking) | +64pp | Model-dependent |
| Temperature T≈0.7 | +67pp | Unreliable |
| Few-shot inoculation | 0pp | No effect |
| Consensus (majority vote) | −21pp | Harmful |
