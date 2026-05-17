## 5.5 The Vocabulary Wall: When Domain Terminology Disables Computation

The preceding sections established that model capability varies systematically with scale and task framing. This section documents a more disconcerting finding: that domain-specific vocabulary can catastrophically disable arithmetic computation that the same model performs flawlessly in the absence of such terminology. We term this phenomenon the **Vocabulary Wall**—a barrier that is neither purely linguistic nor purely computational, but emerges from the interaction between specialized terminology and the model's parametric knowledge during inference.

### 5.5.1 Discovery and Characterization

The Vocabulary Wall was first identified during Studies 18–19 (R39–R40), when models that correctly computed simple arithmetic expressions (e.g., `3 + 5`, `norm(2 + 7i)`) produced catastrophically incorrect results when the identical arithmetic was embedded in domain-specific framing (e.g., "Eisenstein norm of (a + bω)"). This failure is not a gradual degradation: it is a binary collapse from perfect or near-perfect performance to near-zero accuracy.

Table 5.5 presents the Stage 4 Boundary results across six models, isolating the effect of mathematical vocabulary on arithmetic computation.

**Table 5.5**

*Stage 4 Boundary: Mathematical Vocabulary vs. Bare Arithmetic Performance*

| Model | Parameters | Active Parameters | Math Vocabulary Accuracy | Bare Arithmetic Accuracy | Stage |
|-------|-----------:|------------------:|:------------------------:|:------------------------:|:-----:|
| Qwen3.6-35B | 35B (MoE) | 3B | 0% | 12% | 2 |
| Hermes-70B | 70B | 70B | 25% | 88% | 3 |
| Qwen3-235B | 235B (MoE) | 22B | 38% | 100% | 3 |
| Hermes-405B | 405B | 405B | 25% | 100% | 3 |
| Seed-2.0-mini | — | — | 100% | 100% | 4 |
| Seed-2.0-code | — | — | 100% | 100% | 4 |

*Note.* MoE = Mixture of Experts. Active parameters reflect the expert subset engaged per token. Dashes indicate proprietary parameter counts. Math Vocabulary items required identical arithmetic to Bare Arithmetic items but were framed using specialized terminology (e.g., "Eisenstein norm" vs. "absolute value"). N = 48 items per condition per model.

The critical observation is the divergence between columns: Hermes-405B computes bare arithmetic at 100% accuracy, yet when the same computations are framed in mathematical vocabulary, accuracy drops to 25%. This 75-percentage-point collapse occurs despite no change in the underlying arithmetic operations required. The model's failure is not computational but terminological.

### 5.5.2 Three Tiers of Vocabulary Interference

Study 18 (R39) systematically varied the terminological framing of arithmetic problems, revealing a three-tier interference structure:

- **Tier 1 (Clean):** Bare numbers, casual language, and code-style notation produced consistently correct results across all tested models. Phrases such as "compute," "calculate," and "what is" fell into this tier.
- **Tier 2 (Partial):** Algebraic and lattice-framed problems produced errors at rates significantly above baseline but below catastrophic failure. Terms such as "algebraic norm" and "lattice vector" triggered partial interference, suggesting that these terms activate parametric knowledge that competes with—but does not fully suppress—computational circuits.
- **Tier 3 (Lethal):** Terms including "Eisenstein" and "theorem" triggered catastrophic failure. Models did not merely produce incorrect answers; they produced confidently stated nonsense, often combining correct terminology with fundamentally wrong arithmetic.

This three-tier structure suggests that the Vocabulary Wall operates through interference between semantic associations and computational pathways. When a term activates rich parametric knowledge (Eisenstein integers, theorems, proofs), the model's attention mechanisms are drawn toward associative completion rather than stepwise computation.

### 5.5.3 The Penrose-Eisenstein Dead Zone

To determine whether the Wall is a general property of mathematical proper nouns, Study 19 (R40) tested nine mathematician-name stimuli across Stage 3 models. Only two—"Penrose" and "Eisenstein"—consistently triggered the Wall. Names such as "Gauss," "Euler," and "Fibonacci" produced no significant degradation relative to baseline.

This selectivity is itself informative. "Penrose" and "Eisenstein" are terms that appear predominantly in specialized mathematical discourse and are rarely encountered in the arithmetic-heavy training data that establishes robust computational circuits. By contrast, "Gauss" and "Euler" appear across a broader range of mathematical and educational contexts, including introductory materials where arithmetic is foregrounded. The Vocabulary Wall, then, is not a property of proper nouns *per se* but of terms whose training distribution is skewed toward non-computational contexts.

### 5.5.4 Temperature Dependence

Study 28 (R46) examined whether sampling temperature could dissolve the Vocabulary Wall. Results are presented in Figure 5.7.

**Figure 5.7**

*Temperature Dissolution of the Vocabulary Wall*

```
Accuracy (%)
100 ┤ ▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪ Bare
    │ ▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪
 80 ┤ ▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪
    │
 60 ┤
    │
 40 ┤
    │
 20 ┤ ▫▫
    │ ▫▫▫
  0 ┤▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫▫ Vocab
    └──────┬──────┬──────┬──────┬──────
       0.0   0.3   0.7   1.0   1.5
                Temperature
```

*Note.* Bare arithmetic (▪) remained at 100% accuracy at temperatures 0.0 through 0.7. Vocab-conditioned accuracy (▫) was 0% at T = 0.0–0.3, rose to 67% at T = 0.7, and degraded at T = 1.5 along with bare arithmetic. Model: Hermes-70B. N = 48 per condition.

At low temperatures (0.0–0.3), the Vocabulary Wall is absolute: 0% accuracy on vocabulary-framed items, 100% on bare arithmetic. At T = 0.7, vocabulary accuracy rises to 67%, suggesting that increased stochasticity allows the model to escape the attractor basin of associative completion and access computational pathways. However, at T = 1.5, both conditions degrade, indicating that the temperature required to dissolve the Wall also compromises baseline computation.

This finding has practical implications: the Vocabulary Wall cannot be reliably circumvented through temperature tuning alone, because the temperatures that weaken the Wall also introduce stochastic errors into bare computation.

### 5.5.5 Intervention: Auto-Translation and Substitution

Two intervention strategies were evaluated. Auto-translation (R42) preprocesses vocabulary-laden prompts by replacing specialized terms with their arithmetic equivalents before presenting them to the model. This strategy achieved 100% accuracy across all tested models: Hermes-70B improved from 33% to 100%, and Qwen3-235B from 17% to 100%.

The Substitution Hypothesis (R52) provides the theoretical basis: when arithmetic is pre-substituted into the prompt (e.g., replacing "Eisenstein norm of (2 + 3ω)" with "compute √(2² − 2·3 + 3²)"), all label effects disappear. The Wall, therefore, is not a barrier of understanding but a burden of substitution—the computational cost of mapping domain terminology to its arithmetic referent during inference.

Consensus-based approaches failed (R48): ensembling multiple Stage 3 models produced only 25% accuracy on vocabulary items, compared to 46% for the best individual model. This result is consistent with the interpretation that the Wall is an attractor: if multiple models are drawn to the same wrong attractor, consensus amplifies rather than corrects the error.

### 5.5.6 Theoretical Interpretation

The Vocabulary Wall reveals a fundamental asymmetry in large language models: **parametric knowledge can inhibit procedural computation**. Models do not simply lack the ability to compute within specialized domains; rather, the activation of domain knowledge actively suppresses the computational circuits that would otherwise produce correct answers. This finding challenges the assumption that scale alone resolves capability gaps. At 405 billion parameters, Hermes-405B possesses ample capacity for both domain knowledge and computation—the failure is in the interaction between the two, not in the absence of either.

The Wall is best understood as an attentional phenomenon: specialized terms redirect processing resources toward associative retrieval at the expense of stepwise computation. Interventions that bypass this redirection—auto-translation, substitution—restore performance to ceiling, confirming that the underlying computation remains intact.
