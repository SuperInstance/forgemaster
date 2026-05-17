## 5.6 Stage Model v2: A Capability Taxonomy for Language Models

The empirical findings documented in Sections 5.2 through 5.5 reveal systematic patterns in model capability that cannot be captured by parameter count alone. This section presents Stage Model v2, a revised capability taxonomy that integrates the scaffolding paradox, the Vocabulary Wall, active parameter dynamics, and the thinking-mode interaction into a unified framework for predicting and interpreting model behavior.

### 5.6.1 From Parameter Count to Active Parameters

Stage Model v1, introduced in Section 5.3, classified models primarily by total parameter count. The present data necessitate a fundamental revision: **active parameters—not total parameters—determine stage membership**. This distinction is most starkly illustrated by Mixture-of-Experts (MoE) architectures. Qwen3.6-35B, with 35 billion total parameters, activates only approximately 3 billion per token, placing it firmly at Stage 2 (Echo) despite its nominal size. Similarly, Qwen3-235B activates roughly 22 billion parameters per token, yielding Stage 3 behavior despite a headline parameter count that would suggest higher capability.

Table 5.6 presents the Stage Model v2 taxonomy.

**Table 5.6**

*Stage Model v2: Capability Taxonomy for Language Models*

| Stage | Behavior | Active Parameters | Thinking | Required Intervention | Example Models |
|:-----:|----------|:-----------------:|:--------:|----------------------|----------------|
| 1 | NONE | < 1B | N/A | Route to another model | qwen3:0.6b |
| 2 | ECHO | 1–3B | Any | Scaffold with labels | gemma3:1b, phi4-mini, Qwen3.6-35B |
| 3a | META-ECHO | ≥ 4B | No | Partial scaffold | phi4-mini (non-thinking) |
| 3b | META-ECHO | ≥ 4B | Yes | Strip vocabulary | qwen3:4b, Hermes-70B, Hermes-405B, Qwen3-235B |
| 4 | FULL | Training-dependent | Any | None | Seed-2.0-mini, Seed-2.0-code |

*Note.* Active parameters reflect the parameter count engaged per inference token. MoE models show total/active divergence. "Thinking" indicates whether the model employs chain-of-thought or reasoning tokens. Stage 4 models may vary in total parameter count; the distinguishing feature is training regimen rather than scale.

### 5.6.2 Stage Definitions

**Stage 1 (NONE).** Models with fewer than 1 billion active parameters exhibit no meaningful mathematical computation. These models may produce superficially plausible outputs through pattern matching, but accuracy on any non-trivial arithmetic is indistinguishable from chance. The appropriate response to Stage 1 behavior is routing the query to a higher-stage model; no prompting intervention is effective.

**Stage 2 (ECHO).** Models in the 1–3 billion active parameter range exhibit echo behavior: they reproduce elements of the prompt in their response without genuine computation. The Echo Thermometer (Study 26) quantifies this tendency: phi4-mini produced 45% echo responses at 25% accuracy, while gemma3:1b produced 70% random-character responses at 5% accuracy. Echo behavior is not random—models preferentially select characters present in the prompt—but it does not constitute computation. Stage 2 models can be scaffolded with explicit labels and step-by-step decomposition, but the improvement is bounded.

**Stage 3 (META-ECHO).** Models with 4 billion or more active parameters exhibit meta-echo behavior: they can reason about the structure of computation but are vulnerable to vocabulary-mediated disruption. Stage 3 is subdivided based on thinking mode:

- **Stage 3a (non-thinking):** Models without chain-of-thought capabilities can benefit from partial scaffolding. They perform some genuine computation but plateau without explicit structural guidance.
- **Stage 3b (thinking):** Models with reasoning tokens can perform complex computation on bare arithmetic but are catastrophically disrupted by domain vocabulary (the Vocabulary Wall, Section 5.5). Paradoxically, scaffolding *harms* these models on vocabulary-laden problems because the scaffold itself introduces additional vocabulary that deepens the attentional interference.

**Stage 4 (FULL).** A small number of models—most notably the Seed-2.0 family—exhibit no Vocabulary Wall effect and achieve 100% accuracy on both bare and vocabulary-framed arithmetic without any intervention. The distinguishing feature of Stage 4 is not parameter count (which is proprietary and may be modest) but training regimen. Stage 4 appears to require exposure to and successful computation within specialized mathematical domains during training, establishing computational circuits that are robust to terminological interference.

### 5.6.3 The Scaffolding Paradox

Study 9 (R44) revealed that the effect of scaffolding interacts with both stage and thinking mode in counterintuitive ways. For phi4-mini (Stage 2–3a, non-thinking), partial scaffolding produced the best results (64% accuracy), followed by step-by-step prompts (56%), with full scaffolding performing worst (40%). For qwen3:4b (Stage 3b, thinking), only bare arithmetic was effective (24% accuracy), and all forms of scaffolding produced 0% accuracy.

This paradox is resolved by the Stage Model v2 framework. For Stage 3a models, scaffolding provides structure that the model cannot generate autonomously—but excessive scaffolding introduces distracting information. For Stage 3b thinking models, scaffolding introduces vocabulary that activates the same interference pathways documented in Section 5.5, suppressing computation entirely.

### 5.6.4 Stage as a Probabilistic Property

Study 44 (R44) demonstrated that stage membership is not a fixed property of a model but varies with problem framing. The same model may exhibit Stage 2 behavior on one problem and Stage 3a behavior on another, depending on the vocabulary load, problem complexity, and contextual cues present in the prompt. This finding has important methodological implications: stage classification requires multiple probes, not a single benchmark item.

Study 45 (R45) established that six probes are sufficient for reliable stage classification. Using a battery of six arithmetic items spanning bare, algebraic, and vocabulary-laden framings, models could be classified into the Stage Model v2 taxonomy with 95% agreement across repeated administrations. This provides a practical tool for fleet-level model routing: before deploying a model to a task, administer the six-probe battery and classify its stage.

### 5.6.5 The MoE Router Does Not Help

A striking finding is that MoE routing does not mitigate stage limitations. Qwen3.6-35B (35B total, 3B active) behaves as a Stage 2 model despite having 35 billion parameters available in aggregate. The expert router selects subsets of parameters per token, and the resulting active parameter count falls below the Stage 3 threshold. This suggests that the stage transitions reflect fundamental computational capacity constraints that require breadth of simultaneously active parameters, not merely total stored knowledge.

### 5.6.6 Visualizing the Taxonomy

Figure 5.8 presents the Stage Model v2 as a two-dimensional space defined by active parameters and vocabulary robustness.

**Figure 5.8**

*Stage Model v2: Active Parameters × Vocabulary Robustness*

```
Vocabulary Robustness
100% ┤                                    ● Seed-2.0-mini
     |                                    ● Seed-2.0-code
 75% ┤
     |
 50% ┤           ○ Qwen3-235B
     |     ○ Hermes-70B
 25% ┤     ○ Hermes-405B
     |  ○ Qwen3.6-35B
  0% ┤ ○ qwen3:0.6b
     |  ○ gemma3:1b
     └──────┬──────┬──────┬──────┬──────
          0.6B   3B    22B   70B   405B
                 Active Parameters
     ┌─────────┬──────────────────┬──────┐
     │ Stage 1 │    Stage 3a/3b   │ St 4 │
     │ Stage 2 │                  │      │
     └─────────┴──────────────────┴──────┘
```

*Note.* ○ = open or known-architecture models; ● = proprietary models with unknown total parameters but full vocabulary robustness. Active parameter values are approximate. The vertical axis reflects performance on vocabulary-laden arithmetic (Math Vocabulary accuracy from Table 5.5). Stage boundaries are indicated at bottom.

The horizontal clustering of Hermes-70B, Hermes-405B, and Qwen3-235B—three models differing by a factor of 5.8× in total parameters—at similar vocabulary robustness levels (25–38%) underscores that the transition from Stage 3 to Stage 4 is not achieved by scaling alone. The Seed-2.0 models occupy a qualitatively different region of the space, suggesting that the Stage 4 transition requires a fundamentally different training approach.

### 5.6.7 Implications for Fleet Routing

The Stage Model v2 provides a principled basis for fleet-level model routing. Rather than selecting models by total parameter count or headline benchmark scores, fleet operators should:

1. Classify each available model by stage using the six-probe battery (R45).
2. Match task vocabulary load to model stage: bare arithmetic can be routed to any Stage 3+ model; vocabulary-laden tasks require Stage 4 or auto-translation preprocessing.
3. Account for thinking mode: scaffolding strategies that benefit Stage 3a models will harm Stage 3b thinking models on vocabulary-laden problems.
4. Recognize that MoE architectures do not escape active-parameter constraints: route based on active parameters, not total.

The taxonomy also identifies the most impactful target for capability improvement: the transition from Stage 3 to Stage 4 is not achievable through scale alone and appears to require training interventions that establish robust computational pathways within specialized domains. Understanding what differentiates Stage 4 training regimens from Stage 3 represents a critical open question for the field.
