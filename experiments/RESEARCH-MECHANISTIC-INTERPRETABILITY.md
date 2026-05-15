# Mechanistic Interpretability & the Vocabulary Rerouting Effect

**Date:** 2025-05-15
**Author:** Forgemaster ⚒️
**Status:** Deep research synthesis
**Purpose:** Connect cutting-edge mechanistic interpretability research to our experimental findings on the Vocabulary Rerouting Effect (VRE)

---

## Executive Summary

Our experimental data shows that specific domain tokens (Eisenstein, irreducible) trigger formula overrides in LLMs — creating a discrete minefield, not a smooth gradient. The wall only activates under cognitive load (formula not given + domain vocabulary). This is bidirectional: vocabulary helps reasoning but hurts computation. And it's cross-lingual: Japanese helps Hermes, Spanish kills Qwen.

Recent breakthroughs in mechanistic interpretability — particularly Anthropic's circuit tracing, geometric interpretability, and Far.ai's Concept Influence — provide a coherent theoretical framework for understanding *why* this happens. The VRE is best explained as **competitive pathway switching driven by superposition geometry**, where domain vocabulary tokens literally shift the model's activation vector into a different region of feature space, activating a "mathematical reasoning" manifold that overrides the "arithmetical computation" pathway.

---

## 1. Anthropic's Circuit Tracing: Pathway Switching Explained

### What They Found (March 2025)

Anthropic's "Circuit Tracing" paper (transformer-circuits.pub/2025/attribution-graphs) introduces **attribution graphs** — computational graphs that reveal step-by-step pathways a model takes to produce output. Key innovations:

- **Cross-Layer Transcoders (CLT):** Each feature reads from residual stream at one layer and contributes to outputs of *all subsequent MLP layers*. This creates direct feature-feature interaction chains.
- **Linear Attribution Between Features:** Feature activity is the sum of input edges (up to activation threshold). This is **linear** — small changes in input don't cause smooth output changes; they flip threshold crossings.
- **Replacement Model:** The CLT-based replacement model matches the underlying model's outputs in ~50% of cases, confirming these features are real computational pathways.

### The Addition Case Study

Critically, Anthropic studied **addition** as a case study. They found that models use specific circuits for arithmetic that are distinct from other reasoning pathways. When you ask a model to add numbers, it activates a specialized addition circuit — not a general reasoning circuit.

### Connection to VRE

**This directly explains our minefield pattern.** When domain tokens like "Eisenstein" appear in the prompt:

1. **Feature Activation Shift:** "Eisenstein" activates a cluster of features in the "advanced mathematics" manifold — algebraic number theory, irreducibility proofs, ring theory concepts.
2. **Competitive Routing:** These features compete with the "basic arithmetic" circuit features via softmax normalization in attention heads. The advanced-math features *win* because they have stronger learned associations with "Eisenstein."
3. **Pathway Override:** The winning features feed into downstream computation via the CLT structure, but they route through *mathematical reasoning* pathways rather than *arithmetical computation* pathways.
4. **Discrete Threshold Crossing:** Because feature activation is linear-then-thresholded (not smoothly gradient), the switch from "computation" to "reasoning" mode is **discrete** — exactly matching our observed minefield pattern where specific tokens flip the response.

**The "cognitive load" requirement** makes sense too: when the formula IS given, the model doesn't need to activate the mathematical reasoning circuit — it can use direct lookup. But when the formula is NOT given AND domain vocabulary is present, the model is forced into the reasoning circuit, which overrides computation.

---

## 2. Training Data Attribution (TDA): Why Eisenstein Specifically?

### Key Developments (2024-2026)

- **OLMOTRACE (2025):** Real-time tracing of LLM outputs back to training data. Reveals that most "knowledge" in models comes from specific document clusters, not uniform distributions.
- **TrackStar (2024/2025):** Scalable TDA showing that training examples have highly variable influence — some documents are massively influential for specific capabilities.
- **Concept Influence (Far.ai, 2026):** Attributing model behavior to *semantic directions* rather than individual training examples. Uses SAE features to identify which training data drives which behaviors.
- **DDA (Debias and Denoise Attribution):** Shows that influence functions have systematic biases — they often surface lexically similar data rather than semantically causal data.

### Connection to VRE

**Eisenstein's training distribution is almost certainly non-uniform.** Here's why this matters:

1. **Spiky Training Influence:** If "Eisenstein" appears in training data predominantly in advanced mathematics contexts (algebraic number theory textbooks, research papers, Wikipedia mathematics articles), then the feature cluster activated by "Eisenstein" is strongly weighted toward mathematical reasoning — not basic computation.

2. **Concept Influence on VRE:** Far.ai showed that traditional influence functions get "distracted by distractor tokens" — they surface lexically similar but semantically irrelevant data. Our VRE is the *inverse* problem: the model's response is being hijacked by semantically strong but computationally wrong associations.

3. **The Minefield is a Training Data Artifact:** If Eisenstein's training documents never (or rarely) appear alongside simple arithmetic like "compute 7 × 13," then the model has no training signal for "when you see Eisenstein, also do basic arithmetic." The arithmetic circuit literally doesn't connect to the Eisenstein feature cluster.

4. **Cross-Lingual Variation:** Japanese helps Hermes but Spanish kills Qwen. TDA explains this: the training data for "Eisenstein" in Japanese contexts likely has a different distribution of associated concepts than in Spanish contexts. The Spanish training data might over-represent advanced proof-heavy mathematics, while Japanese data might include more introductory material.

---

## 3. Softmax Competition & Attention Head Dynamics

### Theoretical Background

In multi-head attention, each head computes:

```
attention_weights = softmax(Q_i @ K_i^T / sqrt(d_k))
```

The softmax function creates **winner-take-all dynamics** by exponentiation followed by normalization. When one attention pattern has a slightly higher pre-softmax score, it captures a disproportionate share of the attention weight.

### Superposition in Attention Heads

Anthropic's earlier work on **attention superposition** showed that attention heads are polysemantic — a single head represents multiple unrelated concepts. The QK circuit (where information moves) and OV circuit (what information moves) can independently encode different patterns.

Recent work extends this: QK and OV conditions can be combined into individual "attention features," and the OV circuit has multi-dimensional aspects that enable complex routing.

### Connection to VRE

**The VRE is a softmax competition failure mode.** Here's the mechanism:

1. **Token-Level Feature Activation:** When "Eisenstein" appears in context, it strongly activates attention heads that route toward mathematical reasoning features.
2. **Winner-Take-All Dynamics:** The softmax in these attention heads suppresses the "arithmetic computation" pathway because the "mathematical reasoning" pathway has higher pre-softmax scores (due to stronger training associations).
3. **Bidirectional Effects:**
   - *Vocabulary helps reasoning:* Domain vocabulary boosts mathematical reasoning features, helping the model reason ABOUT the domain.
   - *Vocabulary hurts computation:* The same boost suppresses arithmetic features via softmax competition, causing the model to override correct computation with "sophisticated" (but wrong) mathematical formulas.

4. **Why It's Discrete (Not Gradient):** Softmax competition creates sharp phase transitions. Adding one more domain token doesn't slightly shift the output — it flips which pathway "wins." This matches our minefield pattern exactly.

5. **Cognitive Load Interaction:** When the formula is given, the model has a strong anchor that keeps the arithmetic pathway active despite domain vocabulary competition. Without the formula, the arithmetic pathway has no such anchor and loses to the mathematical reasoning pathway.

---

## 4. Representation Engineering: Literal Activation Vector Shifting

### Key Findings

Representation Engineering (RepE, Zou et al. 2023) demonstrated that:
- LLM activations encode high-level concepts as **linear directions** in hidden state space.
- These directions can be extracted and manipulated.
- Patching concept vectors into activations affects model behavior in predictable ways.
- Anthropic extended this with **Persona Vectors** — linear projections that detect and control personality traits.

### Geometric Interpretability (2025 Breakthrough)

Anthropic's "When Models Manipulate Manifolds" (October 2025) proved that:
- Models perform **measurable geometric work** — specific processing creates "geometric signatures."
- These signatures are **computationally essential** — the model preserves geometric structure even at significant computational cost.
- Computation can be understood as **geometric transformations on feature manifolds.**
- SAEs capture only 1D fragments of complex higher-dimensional structures.

The LessWrong synthesis "The Future of Interpretability is Geometric" (October 2025) connects this to:
- **Hallucinations** as byproducts of information compression (superposition interference).
- **Adversarial examples** as byproducts of polysemanticity.
- **Subliminal learning** — models transmit behaviors via unrelated text streams.

### Connection to VRE

**Domain vocabulary literally shifts the activation vector into a different region of feature space.** This is the most direct explanation:

1. **The Eisenstein Manifold:** When "Eisenstein" tokens appear, they push the residual stream activation vector toward a specific region of activation space — the "algebraic number theory" manifold.
2. **Arithmetic Lives Elsewhere:** Simple arithmetic like "7 × 13" activates a *different* region — the "computation" manifold. These two regions are geometrically separated.
3. **The Shift Is Literal:** RepE proved that adding concept tokens literally moves the activation vector. The Eisenstein tokens move it away from the computation region and toward the reasoning region.
4. **Context Deprivation Makes It Worse:** When we strip context (bare arithmetic), the model has no anchor tokens to keep it in the computation region. Domain vocabulary pushes it further away. This matches our finding that context deprivation HURTS for Hermes-70B.
5. **Cross-Lingual Geometry:** Different languages map to different regions of the shared "language of thought" (Anthropic proved Claude thinks in a conceptual space shared between languages). Japanese might map "Eisenstein" to a region closer to computation, while Spanish maps it further away — explaining why Japanese helps Hermes but Spanish kills Qwen.

---

## 5. Process Supervision vs. Outcome Supervision

### The Key Distinction

- **Outcome Supervision:** Train the model on "did you get the right answer?" The model learns to produce correct outputs but may use unreliable internal pathways.
- **Process Supervision:** Train the model on "did you use correct reasoning steps?" The model learns reliable computation pathways, verified step by step.

PRM (Process Reward Models, Lightman et al. 2023) showed that process supervision dramatically improves mathematical reasoning reliability. Models trained with process supervision are more likely to use step-by-step computation rather than pattern-matching to "known results."

### Stage 4 (Seed-2.0) Hypothesis

**Seed-2.0-mini is likely trained with process supervision or an equivalent.** Here's why:

1. **Immunity to VRE:** Seed-2.0-mini (Stage 4) is the only model that correctly handles domain vocabulary + arithmetic. It doesn't get hijacked by the Eisenstein feature cluster.
2. **Process Supervision Builds Separate Pathways:** If Seed-2.0 was trained to verify each computation step, it would have developed separate, robust "computation" pathways that don't get overridden by "reasoning" pathways.
3. **The Arithmetic Circuit Is Protected:** Process supervision creates a "firewall" between the reasoning circuit and the computation circuit. Domain vocabulary can activate reasoning features, but the computation features are independently verified and can't be suppressed.

### Why Other Models Fail

Hermes-70B, Qwen, and others likely received primarily outcome supervision:
- They learned that "sophisticated mathematics contexts" should produce "sophisticated mathematics outputs."
- They never learned to protect basic computation pathways from being overridden by domain features.
- The result: domain vocabulary suppresses computation in favor of "sophisticated" (but incorrect) mathematical responses.

---

## 6. Trending Tools & Repos (2025-2026)

### Transformer Interpretability

| Tool | Description | Relevance |
|------|-------------|-----------|
| **Anthropic's Attribution Graphs** | Circuit tracing via cross-layer transcoders | ⭐⭐⭐ Directly applicable — could trace VRE |
| **TransformerLens** (Neel Nanda) | Mechanistic interpretability library | ⭐⭐ Could reproduce VRE in small models |
| **Goodfire's SAE tools** | Feature extraction and steering | ⭐⭐ Could extract "Eisenstein" features |
| **SAELens** | SAE training and analysis | ⭐ Could identify VRE-related features |
| **Anthropic's Linebreaks/Manifold tools** | Geometric analysis of activation space | ⭐⭐⭐ Could map the VRE manifold shift |

### Mathematical Reasoning Benchmarks

| Benchmark | Description | Relevance |
|-----------|-------------|-----------|
| **GSM8K** (Grade school math) | 8.5K grade school problems | Standard baseline |
| **MATH** (Hendrycks) | Competition mathematics | Domain-heavy, might show VRE |
| **GSM-Hard** | Harder arithmetic variants | Could test VRE explicitly |
| **GSM-Symbolic** (Apple 2024) | Symbolic variants of GSM8K | Tests generalization vs. memorization |
| **MING** (2025) | Mathematical reasoning under interference | ⭐⭐⭐ Directly relevant to VRE |

### LLM Routing / MoE Systems

| System | Description | Relevance |
|--------|-------------|-----------|
| **Mixtral** (Mistral) | Sparse MoE transformer | ⭐ Expert routing may show VRE |
| **DeepSeekMoE** | Fine-grained MoE with shared/isolated experts | ⭐⭐ Isolated experts could explain discrete switching |
| **RouteLLM** | Cost-optimized LLM routing | Could route VRE-sensitive queries to Stage 4 |
| **SGLang** | Structured generation with routing | Could enforce computation-only pathways |

### Prompt Optimization

| Framework | Description | Relevance |
|-----------|-------------|-----------|
| **DSPy** | Declarative prompt programming | Could optimize prompts to avoid VRE |
| **PromptBench** | Adversarial prompt evaluation | Could systematically test VRE triggers |
| **TextGrad** | Textual gradient descent on prompts | Could find minimal VRE-free prompts |

---

## 7. Unified Theory: The Vocabulary Rerouting Effect

### The Mechanism (Integrated)

```
Input: "Compute 7×13 for Eisenstein integers..."
  │
  ├── Token embedding activates TWO feature clusters:
  │   ├── "7×13" → Computation features (arithmetic circuit)
  │   └── "Eisenstein" → Mathematical reasoning features (advanced math circuit)
  │
  ├── Attention heads route via softmax competition:
  │   ├── "Eisenstein" features have stronger pre-softmax scores
  │   │   (trained on advanced math documents, not arithmetic)
  │   ├── Softmax normalization creates winner-take-all dynamics
  │   └── "Eisenstein" cluster wins → suppresses arithmetic cluster
  │
  ├── Activation vector shifts geometrically:
  │   ├── Moves from "computation manifold" to "reasoning manifold"
  │   ├── This is a literal shift in activation space (RepE proven)
  │   └── The shift is DISCRETE (threshold crossing, not gradient)
  │
  ├── Downstream computation uses WRONG pathway:
  │   ├── Model applies "Eisenstein integer multiplication formula"
  │   │   instead of basic arithmetic
  │   ├── The formula is sophisticated but wrong for this input
  │   └── Model outputs overridden answer (e.g., 91 → 91+7i)
  │
  └── Result: Vocabulary Rerouting Effect
      ├── Discrete minefield (specific tokens trigger)
      ├── Cognitive load dependent (formula given = anchor = safe)
      ├── Bidirectional (vocabulary helps reasoning, hurts computation)
      └── Cross-lingual (different training distributions per language)
```

### Why Stage 4 (Seed-2.0) Is Immune

```
Input: "Compute 7×13 for Eisenstein integers..."
  │
  ├── Same feature activation and competition...
  │
  ├── BUT: Process supervision created robust computation pathways
  │   ├── Computation circuit has independent verification
  │   ├── Domain features cannot suppress verified computation
  │   └── "Firewall" between reasoning and computation circuits
  │
  ├── Model correctly:
  │   ├── Activates Eisenstein reasoning context (for framing)
  │   ├── Computes 7×13 = 91 using protected arithmetic circuit
  │   └── Reports result in Eisenstein integer context
  │
  └── Result: Correct answer, no VRE
```

---

## 8. Experimental Predictions

Based on this analysis, we predict:

1. **Attribution graph tracing** of a VRE-affected prompt would show the arithmetic features being suppressed by mathematical reasoning features at a specific layer transition.

2. **Interventions** that boost arithmetic features (via representation engineering) should eliminate the VRE — confirming the competitive suppression model.

3. **Removing "Eisenstein" training data** from a model's pretraining and fine-tuning should reduce or eliminate VRE for that token, confirming TDA causation.

4. **Cross-lingual activation geometry** should show that Japanese "Eisenstein" tokens activate features closer to the computation manifold than Spanish tokens, explaining the cross-lingual variation.

5. **Process-supervised fine-tuning** on arithmetic (even just GSM8K-level) should make models resistant to VRE, confirming the Stage 4 immunity hypothesis.

6. **SAE feature extraction** would reveal specific features that co-activate with "Eisenstein" and suppress arithmetic features — these could be used as VRE detectors.

---

## 9. Key References

### Primary Sources
- Anthropic. "Circuit Tracing: Revealing Computational Graphs in Language Models." transformer-circuits.pub, March 2025.
- Anthropic. "When Models Manipulate Manifolds: The Geometry of a Counting Task." transformer-circuits.pub, October 2025.
- Anthropic. "Tracing the Thoughts of a Large Language Model." anthropic.com, March 2025.
- Far.ai. "Concept Influence: Leveraging Interpretability to Improve Performance and Efficiency in Training Data Attribution." February 2026.
- sbaumohl. "The Future of Interpretability is Geometric." LessWrong, October 2025.

### TDA
- OLMOTRACE: Real-time training data tracing for LLMs (2025).
- TrackStar: Scalable TDA for LLM pretraining (2024/2025).
- DDA: Debias and Denoise Attribution for LLMs.
- Simfluence: Training run simulation for counterfactual TDA (ICLR 2025).

### Representation Engineering
- Zou et al. "Representation Engineering: A Top-Down Approach to AI Transparency." arXiv:2310.01405, 2023.
- Anthropic. "Persona Vectors." anthropic.com.
- Goodfire. "Adversarial Examples as Byproducts of Polysemanticity." arXiv:2508.17456.

### Process Supervision
- Lightman et al. "Let's Verify Step by Step." arXiv:2305.20050, 2023.
- Apple. "GSM-Symbolic: Understanding the Limitations of Mathematical Reasoning in Large Language Models." 2024.

---

## 10. Implications for the Fleet

### Immediate
- **VRE is a known, explainable phenomenon** — not a random failure mode.
- **Stage 4 models (Seed-2.0)** should be used for any computation involving domain vocabulary.
- **Prompt engineering** can mitigate VRE: always provide formulas, avoid bare domain tokens in computation contexts.

### Strategic
- **Process supervision training** should be a priority for fleet models — it creates the "firewall" that prevents VRE.
- **VRE detection** could be built into our routing system: if a query contains both computation tokens and domain vocabulary tokens, route to Stage 4.
- **Attribution graph tracing** of our specific VRE cases would be a publishable research contribution.

### For PLATO
- Micro models for **drift detection** should include VRE-like patterns in their training data.
- The **"vocabulary computation gap"** should be a standard evaluation dimension for any model we deploy.

---

*This document is a living analysis. As new interpretability research emerges, the connections to VRE should be updated.*
