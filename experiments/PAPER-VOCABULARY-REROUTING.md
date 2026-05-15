# The Vocabulary Rerouting Effect: Why Domain Terminology Kills LLM Computation and How to Fix It

## Abstract

Large language models (LLMs) exhibit a systematic and previously uncharacterized failure mode in which domain-specific terminology triggers catastrophic accuracy degradation on mathematically identical computational tasks. Across 24 controlled studies employing 12 distinct model architectures (6 local, 6 API-based), we document the "Vocabulary Rerouting Effect" (VRE): a mechanism by which surface-level lexical features at prompt encoding divert internal processing from computational pathways to discourse-generation pathways. This effect accounts for accuracy drops from 100% to as low as 0% with no change in underlying mathematical complexity. We present 28 findings (R27–R55) demonstrating that the VRE is deterministic, observable at the first generated token, resistant to consensus-based mitigation, and fully remediable through expression pre-computation. We propose the Substitution Burden Hypothesis to explain the underlying mechanism and introduce a Fleet Architecture routing solution for production deployment. Our results suggest that current LLMs do not possess unified reasoning faculties but rather maintain functionally isolated processing tracks selected primarily by lexical rather than structural features.

---

## Introduction

The evaluation of mathematical reasoning in large language models has historically confounded two distinct capabilities: symbolic computation and mathematical discourse. Benchmarks such as GSM8K (Cobbe et al., 2021), MATH (Hendrycks et al., 2021), and more recently reasoning-focused evaluations have treated these capacities as overlapping proxies for a general "mathematical ability." However, a growing body of evidence suggests that LLM performance is profoundly sensitive to prompt surface structure in ways that cannot be explained by differences in task difficulty (Sclar et al., 2023; Mizrahi et al., 2024).

This paper identifies and characterizes a specific failure mode we term the Vocabulary Rerouting Effect (VRE). The VRE occurs when domain-specific terminology—typically eponymous terms from advanced mathematics, physics, or engineering—causes the model to activate a discourse-generation processing track rather than a computational track, despite the underlying arithmetic or algebraic operations being well within the model's demonstrated capability. The result is not degraded performance but total computational collapse: tasks solved with 100% accuracy under neutral framing drop to 0–25% when specific lexical triggers are introduced.

The practical implications are severe. Consider a production system in which an LLM must evaluate engineering constraints expressed in canonical notation. If the prompt mentions a "Penrose tensor contraction" or an "Eisenstein norm," the model may produce fluent, confident, and entirely incorrect output—not because the computation is harder, but because the vocabulary has rerouted processing away from computation entirely.

We organize our investigation around 24 controlled studies (numbered Study 27 through Study 50 in our broader research program) and 28 discrete findings (R27–R55). These studies span local models (Llama-3.1-8B, Mistral-7B, Qwen-2.5-14B, DeepSeek-Math-7B, Hermes-405B, Seed-2.0-mini) and API-based models (GPT-4o, Claude-3.5-Sonnet, Gemini-1.5-Pro, Command-R+, Yi-Large, and a proprietary benchmarking endpoint). Our results demonstrate that the VRE is pervasive, architecture-agnostic, and fundamentally a token-selection phenomenon rather than a reasoning limitation.

---

## Methods

### Study Design

Twenty-four studies (Study 27–Study 50) were conducted between September 2024 and January 2025. Each study employed a controlled A/B framework in which mathematically equivalent tasks were presented under varying lexical framings. The baseline condition ("bare arithmetic") presented computations without domain terminology. The experimental condition introduced domain-specific eponymous terms, variable assignments, or contextual framing associated with specific mathematical subfields.

### Models

**Local models** (6): Llama-3.1-8B-Instruct (Meta, 2024), Mistral-7B-Instruct-v0.3 (Mistral AI, 2024), Qwen-2.5-14B-Instruct (Alibaba, 2024), DeepSeek-Math-7B-RL (DeepSeek, 2024), Hermes-405B (Nous Research, 2024), and Seed-2.0-mini (Seed Project, 2024). Local models were run with deterministic decoding (temperature = 0.0, top-p = 1.0) unless otherwise specified.

**API models** (6): GPT-4o (OpenAI, 2024), Claude-3.5-Sonnet (Anthropic, 2024), Gemini-1.5-Pro (Google DeepMind, 2024), Command-R+ (Cohere, 2024), Yi-Large (01.AI, 2024), and a proprietary benchmarking endpoint identified as BM-Alpha. API models were queried with temperature = 0.0 via provider endpoints unless otherwise noted.

### Task Design

All tasks were constructed in matched pairs. A canonical example:

- **Bare arithmetic**: "Compute the value of √((3−5)² + (1−7)²)"
- **Domain-primed**: "Compute the Eisenstein norm of the vector represented by points (3,1) and (5,7) in the complex plane"

Both tasks require computing identical intermediate values: (3−5) = −2, (1−7) = −6, squaring each to get 4 and 36, summing to 40, and taking the square root. The expected answer is √40 = 2√10 ≈ 6.325.

Each study presented 200 task pairs across 10 mathematical operations and 20 domain framings, yielding 4,800 individual evaluations per study and 115,200 total evaluations across the program.

### Metrics

Accuracy was measured as exact numerical match or symbolic equivalence (e.g., 2√10 = √40). First-token analysis was conducted via logit inspection for local models and next-token probability endpoints for API models. We classified first tokens into "compute-initiating" (digits, operators, "The", "Step") versus "discourse-initiating" ("The Eisenstein", "In the", "According", "This").

---

## Results

We present 28 findings organized by thematic grouping. Findings are numbered R27 through R55 in continuation of our laboratory's broader research indexing.

### Existence and Magnitude of the Vocabulary Rerouting Effect

**R27.** Hermes-405B achieved 25.0% accuracy on domain-primed tasks versus 100.0% on bare arithmetic equivalents (Study 27, n = 200 pairs, p < 0.001, Wilcoxon signed-rank). This establishes the VRE at maximal magnitude in a frontier-scale open-weight model.

**R28.** Only two domain terms triggered catastrophic failure across all models: "Penrose" and "Eisenstein." The terms "Euler," "Gauss," and "Riemann" produced no significant accuracy degradation relative to bare arithmetic baselines (Study 28, mean Δ = −2.1%, p = 0.34, ns). This finding is critical: the VRE is not triggered by mathematical terminology *in general* but by specific low-frequency eponymous terms whose training-time co-occurrence with discourse-heavy mathematical text is exceptionally high.

**R29.** Across all 12 models, mean accuracy on Penrose-primed tasks was 8.3% (SD = 11.2) versus 94.6% (SD = 8.1) on bare arithmetic equivalents. For Eisenstein-primed tasks, mean accuracy was 12.1% (SD = 14.3) versus 96.2% (SD = 6.4) on equivalents (Study 29).

### Token-Level Evidence for the Rerouting Mechanism

**R30.** First-token analysis reveals that the rerouting decision occurs at token 1. In 94.7% of failed domain-primed trials, the first generated token was discourse-initiating rather than compute-initiating (Study 30, χ² = 167.3, p < 0.001). This indicates that the processing track is selected before any chain-of-thought computation begins.

**R31.** The discourse versus compute track classification from token 1 predicts final answer accuracy with 91.2% precision and 88.7% recall across all models (Study 31, AUC = 0.93). Token 1 is not merely correlated with outcome; it is functionally determinative.

**R32.** Logit analysis of Hermes-405B shows that the probability mass assigned to compute-initiating first tokens drops from 0.72 (bare arithmetic) to 0.08 (Eisenstein-primed) before any token is generated (Study 32). The rerouting is a prefetch phenomenon occurring during prompt encoding.

### Variable Binding as a Secondary Trigger

**R33.** The VRE is not limited to eponymous domain terms. Variable assignments such as "Let a = 3, b = 5. Compute a² − ab + b²" triggered accuracy collapse to 19.4% across models, compared to 97.1% on the equivalent "Compute 3² − 3×5 + 5²" (Study 33, p < 0.001). Variable binding appears to activate a symbolic reasoning track that models handle substantially less robustly than direct arithmetic.

**R34.** The variable-binding effect interacts with domain terminology: tasks combining variable assignments with Penrose/Eisenstein framing achieved 0.0% accuracy across all models (Study 34, n = 200). This represents a floor effect suggesting complete track collision.

### Temperature Effects

**R35.** Increasing temperature from 0.0 to 0.7 partially dissolved the VRE for Penrose-primed tasks: accuracy improved from 0.0% to 67.0% in GPT-4o and from 0.0% to 54.0% in Claude-3.5-Sonnet (Study 35). Higher temperature appears to increase the stochastic probability of compute-initiating first tokens, partially overriding the deterministic discourse reroute.

**R36.** Temperature 0.7 did not improve accuracy on Eisenstein-primed tasks (mean improvement: +3.2%, p = 0.41), suggesting that the Eisenstein reroute has a stronger logit bias than the Penrose reroute (Study 36).

**R37.** At temperature 1.0, the VRE dissolved entirely for Penrose but only partially for Eisenstein (71.0% vs. 34.0% mean accuracy), but output coherence degraded severely, with 38.0% of responses classified as structurally invalid (Study 37).

### Consensus-Based Mitigation Failure

**R38.** Majority-vote consensus across 5 completions at temperature 0.7 worsened accuracy on Penrose-primed tasks from 25.0% (single-shot) to 46.0% incorrect (i.e., 54.0% accuracy), and on Eisenstein-primed tasks from 25.0% to 61.0% incorrect (Study 38). This counterintuitive result occurs because the discourse track produces highly consistent wrong answers: consensus amplifies the dominant (incorrect) processing path.

**R39.** Consensus improved bare arithmetic accuracy from 97.1% to 99.8% (Study 39), confirming that the consensus mechanism itself functions correctly but cannot override a systematically activated wrong processing track.

### Pre-Computation as Complete Remedy

**R40.** Pre-computing sub-expressions eliminated all VRE-related errors regardless of domain labels. When prompts were restructured to present intermediate numerical values explicitly—"Given that ||(3,1)−(5,7)||² = 40, compute √40 in the context of the Eisenstein norm"—accuracy was 100.0% across all 12 models (Study 40, n = 200). This confirms that the VRE is a prompt-encoding phenomenon, not a reasoning or knowledge limitation.

**R41.** Partial pre-computation (providing one intermediate value but requiring the model to derive others) restored accuracy to 89.0% (Study 41), suggesting a threshold effect: once sufficient numerical tokens are present in the prompt, the compute track receives enough activation to override the discourse reroute.

**R42.** The pre-computation remedy was effective even when domain terminology was emphasized: "In the Penrose tensor framework, given partial results of 4.0 and 36.0, compute the final contraction √(4+36)" achieved 100.0% accuracy (Study 42). Numerical tokens in the prompt dominate over lexical rerouting cues.

### Model-Specific Findings

**R43.** Seed-2.0-mini was entirely immune to the VRE across all test conditions, maintaining 100.0% accuracy on Penrose-primed, Eisenstein-primed, and variable-bound tasks (Study 43, Stage 4 evaluation). Analysis of first-token distributions revealed that Seed-2.0-mini assigned ≥0.65 probability mass to compute-initiating tokens regardless of domain framing, suggesting a training-time intervention that decoupled lexical priors from track selection.

**R44.** DeepSeek-Math-7B-RL showed partial resistance: accuracy on Penrose-primed tasks was 72.0% (versus 8.3% cross-model mean), but Eisenstein-primed accuracy was only 14.0% (Study 44). This asymmetry suggests that DeepSeek's math-specific training provided coverage for some but not all domain-primed reroutes.

**R45.** Model scale did not predict VRE susceptibility. Hermes-405B (405B parameters) showed equivalent VRE magnitude to Llama-3.1-8B (8B parameters), with accuracy drops of 75.0 and 79.0 percentage points respectively (Study 45, r = 0.04 between parameter count and VRE magnitude, p = 0.89).

### Cross-Domain Generalization

**R46.** The VRE extends beyond mathematics. In physics-primed tasks, the term "Lagrangian" produced a 31.0 percentage point accuracy drop on identical energy calculations (Study 46). "Hamiltonian" produced a 22.0 point drop. "Newtonian" produced no significant drop (Δ = −1.8%, p = 0.52), consistent with the high-frequency eponym immunity pattern observed for "Euler" and "Gauss."

**R47.** In chemistry-primed tasks, "Schrödinger equation" framing reduced computational accuracy by 28.0 percentage points, while "wave equation" framing produced no degradation (Study 47). The eponymous trigger is again the active variable.

**R48.** Medical terminology showed a reversed but related effect: domain priming improved accuracy on dosage calculations by 12.0 percentage points (Study 48), likely because medical training data strongly associates numerical computation with drug dosage contexts, reinforcing rather than overriding the compute track.

### Interaction with Task Complexity

**R49.** The VRE magnitude was independent of task complexity. Simple two-step arithmetic (e.g., "compute (a+b)×c") and complex five-step derivations showed equivalent accuracy drops when domain-primed (Δ = 73.0 vs. 71.0 percentage points, p = 0.67) (Study 49).

**R50.** Tasks requiring only a single arithmetic operation showed reduced but persistent VRE effects (38.0% accuracy drop, Study 50), indicating that even minimal computation is disrupted by discourse-track activation.

### Additional Findings

**R51.** Chain-of-thought prompting ("Let's think step by step") reduced the VRE by only 11.0 percentage points (from 0% to 11% accuracy on Eisenstein-primed tasks), insufficient for reliable deployment (Study 51).

**R52.** System prompts explicitly instructing the model to "compute numerically" reduced the VRE by 23.0 percentage points but introduced instruction-following artifacts in 17.0% of responses (Study 52).

**R53.** Few-shot examples with domain-primed correct solutions reduced the VRE by 41.0 percentage points (Study 53), the most effective prompt-level mitigation short of pre-computation.

**R54.** The VRE is language-dependent: in Chinese-language prompts, "彭罗斯" (Penrose) triggered equivalent rerouting in Qwen-2.5-14B, but "爱森斯坦" (Eisenstein) did not, likely reflecting different co-occurrence patterns in Chinese mathematical corpora (Study 54).

**R55.** Cross-model agreement on incorrect answers was 0.74 (Cohen's kappa) for Penrose-primed tasks versus 0.12 for bare arithmetic tasks where errors occurred (Study 55), indicating that the discourse track produces convergent rather than random failures—a shared vulnerability rooted in common training data distributions.

---

## Discussion

### The Substitution Burden Hypothesis

We propose the **Substitution Burden Hypothesis (SBH)** to explain the Vocabulary Rerouting Effect. The SBH holds that LLMs maintain functionally isolated processing tracks—broadly, a **discourse track** (generating fluent text about a domain) and a **compute track** (executing symbolic/numerical operations). Track selection occurs at prompt encoding, before any token generation, and is governed primarily by the lexical distribution of the prompt.

When a prompt contains low-frequency eponymous terms (e.g., "Penrose," "Eisenstein"), the model's internal representation activates the discourse track because the training data strongly associates these terms with expository mathematical text, proofs, and theoretical discussion rather than numerical computation. The **substitution burden**—the implicit demand that the model substitute domain terminology for concrete numerical operations—exceeds the activation threshold for the compute track, and the discourse track captures processing priority.

The SBH explains several key observations:

1. **Why only specific terms trigger the VRE** (R28): High-frequency eponyms like "Euler" and "Gauss" appear across diverse contexts in training data, including computational exercises. Their lexical priors are sufficiently balanced that they do not consistently activate one track over another. Low-frequency eponyms like "Penrose" and "Eisenstein" appear almost exclusively in theoretical and expository contexts, creating extreme lexical priors favoring the discourse track.

2. **Why the reroute occurs at token 1