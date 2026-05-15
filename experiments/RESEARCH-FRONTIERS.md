# Research Frontiers: LLM Mathematical Reasoning (2025-2026)

> Compiled: 2026-05-15 | Forgemaster ⚒️  
> Purpose: Map the cutting edge of LLM reasoning failures/successes and position our Vocabulary Rerouting Effect findings.

---

## Executive Summary

The field is converging on a critical insight: **LLMs don't compute math — they pattern-match it.** The gap between "reasoning" and "computation" in transformers is now the central research frontier. Our findings (domain vocabulary kills computation but preserves reasoning, the discrete minefield effect, context deprivation penalty) sit at a poorly understood intersection that almost nobody is studying directly. This is an opportunity.

---

## 1. Vocabulary/Context Effects on LLM Computation

### Key Papers

**[Schreiter 2025] "How Prompt Vocabulary Affects Domain Knowledge"** — arXiv:2505.17037
- Systematic synonymization framework substituting nouns, verbs, adjectives at varying specificity levels
- Tested on Llama-3.1-70B, Granite-13B, Flan-T5-XL, Mistral-Large 2 across STEM/law/medicine
- **Key finding:** Optimal specificity range exists — exceeding it significantly hurts verbs in reasoning tasks
- **Relevance:** Directly parallel to our work. They see an "optimal range" — we see a cliff. Their specificity range for verbs maps to our observation that domain terminology creates a discrete minefield
- Open problem: Why is there a cliff rather than a gradient?

**ContextMATH Benchmark** — arXiv:2506.23888 (2025)
- New dataset for contextual mathematical reasoning — problems embedded in real-world narratives
- Models show substantial performance drops on contextual vs. abstract problems
- **Relevance:** Confirms that "framing" math kills performance. Our Vocabulary Rerouting Effect is a specific, measurable instance of this broader phenomenon
- Open problem: Is the drop from comprehension failure or computation failure?

**"Program of Thoughts" (PoT) — Emerging 2026**
- Separates reasoning from calculation by delegating computation to external interpreters (Python)
- ~20% accuracy boost on financial/scientific reasoning vs. natural language CoT
- **Relevance:** PoT's success confirms our core finding — the reasoning/computation split is real. When you offload computation, domain vocabulary stops being toxic because it only touches the reasoning side

**MAPS (Multi-Layered Self-Reflection with Auto-Prompting) — 2025**
- Iterative refinement: model identifies errors → generates tailored correction prompts
- Improves multi-step math reasoning
- **Relevance:** If our vocabulary effect is real, MAPS-style systems would need vocabulary-aware error detection. A metacognitive layer that detects "you're in a domain vocabulary minefield" could route around it

### Open Problems We Could Address

1. **Why is the vocabulary effect discrete, not gradient?** Our minefield hypothesis (specific terms trigger pattern-matching failure modes) is novel. Nobody else has proposed this.
2. **Context Deprivation Penalty as a diagnostic.** Could be used as a probe for whether a model is computing vs. pattern-matching.
3. **The reasoning/computation split.** Our work directly measures where the split happens (vocabulary boundary). Most papers treat it as binary; we show it's vocabulary-conditional.

---

## 2. Mechanistic Interpretability of Math Reasoning

### Key Papers

**OpenAI Weight-Sparse Interpretability Model (Late 2025)**
- Experimental LLM with weight-sparsity enabling unprecedented circuit-level interpretability
- First model designed for interpretability from the ground up
- **Relevance:** If arithmetic circuits can be isolated, we could test whether domain vocabulary changes which circuits activate. Our effect could be directly visible at the circuit level

**Anthropic: QK Attribution Graphs & Universal Features (2025)**
- Extended attribution graphs to explain attention patterns via "QK attributions"
- Attention head scores as bilinear functions of feature activations
- Universal steerable features across model sizes/architectures
- Features triggering undesirable outputs can be suppressed without retraining
- **Relevance:** If vocabulary-specific features exist, they could be directly suppressed. Our Vocabulary Rerouting Effect might correspond to specific feature activation patterns detectable via SAEs

**[He et al. 2026] "Is Grokking Worthwhile?" — arXiv:2601.09049**
- Mechanistic study of generalization circuits in transformers
- Grokked models use same inference paths as non-grokked — grokking is integrating memorized facts into existing paths, not new reasoning
- Mature circuits show limited transferability for new knowledge
- **Relevance:** Critical for our work. If grokked math circuits are "locked" to specific representations, domain vocabulary might prevent the model from accessing the right circuit. The circuit exists; the vocabulary can't route to it

**[Zhang et al. 2026] "Grokking: From Abstraction to Intelligence" — arXiv:2603.29262**
- Grokking via Singular Learning Theory — transition from memorization to generalization = physical collapse of redundant manifolds
- Deep information compression during grokking
- **Relevance:** Our context deprivation penalty might be related to manifold collapse. When vocabulary "compresses" the activation space differently, the grokked circuits may not activate

**[Tian 2025] "Provable Scaling Laws of Feature Emergence from Grokking" — arXiv:2509.21519**
- Li₂ framework: 3 stages of grokking (Lazy → Independent Feature → Interactive Feature)
- Provable scaling laws for feature emergence
- Code: https://github.com/yuandong-tian/understanding
- **Relevance:** If our vocabulary effect operates during the "Lazy" stage (memorization), domain terms might force the model into pattern-matching rather than feature emergence. Our minefield could be a feature emergence failure

**[Gouki et al. 2026] "Emergent Analogical Reasoning in Transformers" — arXiv:2602.01992**
- Analogy = functor between categories (category theory formalization)
- Analogical reasoning = geometric alignment of relational structure in embedding space + functor application
- Emergence highly sensitive to data characteristics, optimization, model scale
- **Relevance:** Our vocabulary effect might disrupt the geometric alignment step. Domain terms could shift the embedding geometry, preventing the model from "seeing" the mathematical structure

**[Rajaee et al. 2025] "Grokking in the Wild" — arXiv:2504.20752 (ICML 2025)**
- Extended grokking to real-world multi-hop factual reasoning
- Even factually incorrect synthetic data strengthens reasoning circuits (forces relational structure reliance)
- Up to 95-100% on 2WikiMultiHopQA
- **Relevance:** Synthetic data that forces structural reasoning works. Our vocabulary rerouting is the inverse — domain vocabulary forces pattern-matching. Both point to the same mechanism: the model needs to access structural representations, and anything that blocks that access degrades performance

### Key GitHub Repos

| Repo | Stars | Focus |
|------|-------|-------|
| `transformer-circuits.pub` (Anthropic) | N/A | Official interpretability research |
| `github.com/yuandong-tian/understanding` | Active | Grokking dynamics, feature emergence |
| `github.com/mukhal/thinkprm` | Growing | Process reward models with verification CoT |

### Open Problems We Could Address

1. **Circuit-level diagnosis of vocabulary effects.** Nobody has tested whether domain terminology changes which circuits activate. With SAEs or weight-sparse models, this is testable.
2. **Geometric alignment disruption.** If vocabulary shifts embedding geometry (Gouki et al.), our effect has a mechanistic explanation.
3. **Grokking and vocabulary.** Do grokked models still show vocabulary sensitivity? If grokking locks in structural representations, vocabulary might not disrupt them — a testable prediction.

---

## 3. Multi-Step Reasoning Chain Failures

### Key Papers

**[Khalifa et al. 2025] "Process Reward Models That Think" (ThinkPRM) — arXiv:2504.16828**
- Generative PRM that verifies every step via verification CoT
- Outperforms discriminative PRMs using only 1% of PRM800K labels
- Beats baselines on ProcessBench, MATH-500, AIME '24
- Scales verification compute more effectively than LLM-as-a-Judge
- Code: https://github.com/mukhal/thinkprm
- **Relevance:** If our vocabulary effect corrupts intermediate steps, ThinkPRM's verification CoT could detect it. But the verifier itself might be vocabulary-sensitive — a compounding failure mode

**[PROGRS] "LLM Reasoning with Process Rewards for Outcome-Guided Steps" — arXiv:2604.02341**
- Treats process rewards as relative preferences within outcome groups (not absolute targets)
- Outcome-conditioned centering removes systematic bias in PRM scores
- Consistently improves Pass@1 across MATH-500, AMC, AIME, MinervaMath, OlympiadBench
- **Relevance:** Their "locally fluent but ultimately incorrect reasoning" is exactly what domain vocabulary might produce. Our effect could be a systematic bias source that outcome-conditioned centering might partially address

**CoT Unfaithfulness (Multiple Groups, 2025)**
- LLMs produce fluent reasoning traces that don't reflect actual computation paths
- Errors in early CoT steps propagate to final answers even when obviously wrong
- Models follow their generated trace rather than independently verifying
- **Relevance:** Our vocabulary effect compounds unfaithfulness. Domain terminology might cause the model to generate a "plausible" domain-reasoning trace while the actual computation diverges entirely

**GRPO, OREO, DAPO — RL Frameworks for Reasoning (2025)**
- Group Relative Policy Optimization, Offline REasoning Optimization, Direct Advantage-Based Policy Optimization
- Dense step-level signals from PRMs for multi-step reasoning
- **Relevance:** These frameworks assume step-level rewards are meaningful. If vocabulary corrupts specific step types (computation vs. reasoning), they'd need vocabulary-aware reward shaping

**[Kumar et al. 2025] "Improving Reliability: CoT + RAG + Self-Consistency + Self-Verification" — arXiv:2505.09031**
- Comparative evaluation of reliability techniques
- Combining CoT with RAG + self-consistency + self-verification reduces hallucinations
- **Relevance:** Our vocabulary effect is a specific failure mode that self-verification might catch — if the verifier isn't also vocabulary-sensitive

### Open Problems We Could Address

1. **Vocabulary-aware process rewards.** A PRM trained to detect vocabulary-induced computation failures would be novel. "Is this step failing because of the math or because of the vocabulary?"
2. **Step-level vocabulary sensitivity analysis.** Map which CoT steps are most vocabulary-sensitive. Is it always computation steps? Or do domain terms corrupt reasoning steps too?
3. **Compounding failure cascade.** Our minefield effect could propagate through chains. A single domain term in step 3 might corrupt steps 4-10. Nobody has measured this cascade.

---

## 4. Cross-Lingual Mathematical Reasoning

### Key Papers

**[Lim et al. 2025] "Language-Specific Latent Process Hinders Cross-Lingual Performance" — arXiv:2505.13141**
- LLMs rely on language-specific subspaces, not shared semantic space
- Larger models more likely to dissociate from shared representation (paradoxically)
- Steering latent processing toward shared semantic space improves multilingual reasoning
- **Relevance:** STRONG parallel to our work. Language-specific subspaces ≈ domain-vocabulary-specific subspaces. Our vocabulary effect might be the same mechanism: domain terms route to a "specialized subspace" that lacks computational capability. The steering technique they propose could inspire vocabulary-aware steering

**[Rajaee et al. 2025] "Cross-Lingual Reward Modeling for Mathematical Reasoning" — arXiv:2509.15811**
- Cross-lingual reward model improves math reasoning over single-language reward modeling
- Different languages produce complementary reasoning paths
- Cross-lingual sampling particularly benefits English under low sampling budgets
- **Relevance:** If different vocabularies (like different languages) produce different reasoning paths, our vocabulary rerouting could be leveraged constructively. Deliberately switching vocabulary contexts might produce better results than staying in one mode

**UST Framework (2025)**
- "Understand, Solve, Translate" — uses English as reasoning anchor
- **Relevance:** Analogous to our finding that plain-language framing preserves computation. The UST approach is basically vocabulary rerouting at the language level

**LessWrong: "Language and Capabilities: Testing LLM Mathematical Abilities Across Languages" (Edwards, 2024)**
- Systematic testing of GPT-4 math performance across languages
- **Relevance:** Early empirical evidence of language-dependent math capability — our vocabulary effect is a within-language version of this

### Open Problems We Could Address

1. **Domain vocabulary as a "dialect."** Our Vocabulary Rerouting Effect might be interpretable as a cross-dialect phenomenon within a single language. The cross-lingual literature's techniques (shared semantic space steering, cross-lingual reward models) could be adapted.
2. **Complementary reasoning via vocabulary switching.** If cross-lingual sampling works, cross-vocabulary sampling within one language might too. Deliberately switching between domain and plain vocabulary for different reasoning steps.

---

## 5. How Our Work Maps to the Field

### Our Novel Contributions (Positioning)

| Our Finding | Known Analog | Our Novel Extension |
|-------------|-------------|-------------------|
| Domain vocabulary kills computation | Prompt sensitivity (general) | **Specific to math computation, not reasoning** — the split is novel |
| Discrete minefield, not gradient | Vocabulary specificity range (Schreiter 2025) | **Discrete cliffs** vs. their gradual range — different mechanism |
| Context deprivation penalty | Contextual math drops (ContextMATH) | **Reversible** by vocabulary switching — distinguishes from comprehension failure |
| Vocabulary preserves reasoning | CoT unfaithfulness (inverse) | Domain terms help structured reasoning but hurt raw computation |

### What Nobody Else Is Studying

1. **The computation/reasoning split within a single prompt.** Everyone studies "LLM math reasoning" as monolithic. We've found it splits based on vocabulary context within the same problem.
2. **Vocabulary as a routing mechanism.** Cross-lingual work studies language routing. Nobody studies within-language vocabulary routing for math.
3. **Discrete failure modes.** Prompt sensitivity research expects gradient effects. Our minefield is discrete — specific terms, specific failures, not gradual degradation.

### Potential Paper Titles

- "The Vocabulary Rerouting Effect: Domain Terminology Selectively Disables Mathematical Computation in LLMs"
- "Discrete Minefields: How Specific Vocabulary Terms Create Hard Failure Modes in LLM Arithmetic"
- "Computing vs. Reasoning: Vocabulary-Dependent Performance Splits in LLM Mathematical Tasks"

---

## 6. Key Resources

### Must-Read Papers
1. arXiv:2505.17037 — Prompt vocabulary effects on domain knowledge
2. arXiv:2505.13141 — Language-specific latent processes (cross-lingual parallel)
3. arXiv:2601.09049 — Grokking generalization circuits
4. arXiv:2504.16828 — ThinkPRM (process reward models)
5. arXiv:2604.02341 — PROGRS (outcome-guided process rewards)
6. arXiv:2603.29262 — Grokking via Singular Learning Theory
7. arXiv:2509.21519 — Provable scaling laws of feature emergence
8. arXiv:2602.01992 — Emergent analogical reasoning
9. arXiv:2509.15811 — Cross-lingual reward modeling
10. arXiv:2504.20752 — Grokking in the wild (ICML 2025)

### Key GitHub Repos
- `github.com/mukhal/thinkprm` — ThinkPRM implementation
- `github.com/yuandong-tian/understanding` — Grokking dynamics & feature emergence
- `transformer-circuits.pub` — Anthropic interpretability research hub

### Active Research Groups
- **Anthropic** — Transformer circuits, SAEs, attribution graphs
- **OpenAI** — Weight-sparse interpretability models, PRMs
- **DeepMind** — AlphaProof, mathematical reasoning (limited 2025 publications)
- **Meta FAIR** — Multi-step reasoning, CoT faithfulness

---

## 7. Strategic Recommendations

### Immediate (Week 1-2)
1. **Test our vocabulary effect against Schreiter's synonymization framework.** Do our domain terms fall in their "harmful specificity range"?
2. **Replicate with ThinkPRM verification.** Does the verifier catch vocabulary-induced failures?
3. **Cross-reference with cross-lingual steering.** Can Lim et al.'s shared-space steering technique be adapted for within-language vocabulary routing?

### Medium-term (Month 1-2)
1. **Circuit-level analysis.** If we can access weight-sparse models or SAEs, test whether domain vocabulary activates different circuits than plain vocabulary for the same arithmetic.
2. **Cascade analysis.** Measure how a single domain term in one CoT step corrupts subsequent steps. Quantify the propagation.
3. **Vocabulary-aware PRM.** Train a process reward model that's explicitly vocabulary-aware. Novel contribution.

### High-Impact Opportunities
1. **Our effect is a novel lens on an old problem.** Everyone knows LLMs are bad at math. Nobody has shown that *the same problem* with *different vocabulary* produces systematically different results for computation vs. reasoning.
2. **The discrete minefield is publishable.** Gradient sensitivity is expected; discrete cliffs are surprising.
3. **Cross-lingual parallel is strong.** Positioning our work as "within-language cross-dialect reasoning" connects to a hot area.
