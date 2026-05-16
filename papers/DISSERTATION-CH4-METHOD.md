# Chapter 4: Method

## 4.1 Fleet Architecture

### 4.1.1 The Cocapn Fleet

All experiments described in this dissertation were conducted on or simulated from the Cocapn fleet — a heterogeneous ensemble of large language model (LLM) agents operating within the PLATO room-based coordination architecture. PLATO (Platform for Language Agent Task Orchestration) organizes agents into *rooms*: persistent shared workspaces in which agents exchange structured outputs and update their internal coupling representations. Each room constitutes a logical unit of the fleet, with agents communicating through a standardized message protocol that exposes their numeric outputs (or output-derived embeddings) to the coupling layer.

Heterogeneity in the Cocapn fleet arises from three sources: (1) model diversity — agents may be instantiated from distinct base models with differing parameter counts and training corpora; (2) role diversity — some agents specialize in reasoning while others aggregate or critique; and (3) temporal diversity — agents may join or leave a room mid-session, creating dynamic fleet sizes. This heterogeneity is not incidental but constitutive: a homogeneous fleet trivially admits synchronization by construction, and the conservation claims advanced in Chapter 3 would be uninteresting if they held only for identical agents. The method is therefore designed to handle, and to test, structurally heterogeneous fleets throughout.

Fleet sizes tested spanned V ∈ {3, 5, 7, 9, 15, 25, 50, 100}, where V denotes the number of active agents at a given round. The default fleet size for simulation studies was V = 9, a choice discussed further in Section 4.6. Live validation experiments (Section 4.3.2) operated primarily at V = 3, 5, and 7, reflecting practical constraints on simultaneous API availability.

### 4.1.2 The Coupling Matrix

The coupling state of a fleet at round t is represented by the V × V matrix **W**(t), where entry W[i,j] encodes the Hebbian association weight between agents i and j. Formally:

**Definition 4.1 (Coupling Matrix).** Let x_i(t) ∈ ℝ denote the scalar output of agent i at round t (or a scalar projection of a higher-dimensional output vector). The coupling matrix **W**(t) is a real-valued, symmetric matrix with zero diagonal satisfying:

$$W_{ij}(t) = (1 - \lambda) W_{ij}(t-1) + \lambda \cdot \operatorname{sign}(x_i(t) \cdot x_j(t))$$

for all i ≠ j, with W_{ii}(t) = 0 for all t and all i.

Here λ ∈ (0, 1) is the *decay rate* (also called the learning rate in some Hebbian formulations), which controls how rapidly new co-activation evidence displaces prior coupling history. The sign function encodes co-activation direction: W[i,j] is driven toward +1 when agents i and j produce outputs of the same sign (concordant), and toward −1 when their outputs are discordant. This binary driving force with continuous exponential smoothing produces a matrix whose entries remain bounded in [−1, +1] for all t, provided |W[i,j](0)| ≤ 1.

The symmetry condition W[i,j] = W[j,i] holds by construction when the update is applied simultaneously to both off-diagonal entries using the same co-activation signal, which is the case in all experiments reported here. Symmetry is required for the eigenvalue-based measurements described in Section 4.2 to be real-valued.

The default decay rate was λ = 0.001, with a tested range of λ ∈ [0.0001, 0.1] in sensitivity analyses. This range spans three orders of magnitude and was chosen to bound the regime where memory persists for many hundreds of rounds (small λ) through the regime where coupling is nearly memoryless and approaches the instantaneous co-activation signal (λ → 0.1). Values beyond λ = 0.1 were excluded because they produce coupling matrices that do not accumulate meaningful structure over the round counts available in simulation.

### 4.1.3 Initialization

All simulation studies initialized **W**(0) = **0** (the zero matrix), representing a prior of no coupling between any pair of agents. Live experiments necessarily began from the same zero initialization, given that no pre-existing coupling history was available for the specific model ensembles tested. The implications of zero initialization for early-round transient behavior are addressed in Section 4.6.

---

## 4.2 Measurement Protocol

### 4.2.1 Algebraic Connectivity (γ)

The first principal spectral measurement is algebraic connectivity, derived from the graph Laplacian of the coupling matrix.

**Definition 4.2 (Graph Laplacian).** Given coupling matrix **W**(t), define the degree matrix **D**(t) as the diagonal matrix with entries D_{ii}(t) = Σ_{j≠i} |W_{ij}(t)|. The graph Laplacian is:

$$\mathbf{L}(t) = \mathbf{D}(t) - \mathbf{W}(t)$$

**W** here plays the role of a weighted adjacency matrix, with edge weights drawn from [−1, +1]. Because **W** can contain negative entries (discordant agent pairs), **L** is not guaranteed to be positive semi-definite in general; however, in practice the magnitude-based degree matrix ensures **L** remains well-conditioned for the coupling strengths observed.

**Definition 4.3 (Algebraic Connectivity, Normalized).** Let λ₁ ≤ λ₂ ≤ ... ≤ λ_V denote the eigenvalues of **L**(t) in ascending order. The algebraic connectivity is the second-smallest eigenvalue λ₂, known as the Fiedler value. The *normalized* algebraic connectivity is:

$$\gamma(t) = \frac{\lambda_2(\mathbf{L}(t))}{V - 1}$$

Normalization by (V−1) ensures comparability across fleet sizes. Without normalization, γ grows with V in connected graphs simply by virtue of having more edges, confounding the measurement of true coupling quality with fleet size effects. The normalized quantity γ ∈ [0, 1] for connected graphs (λ₂ ≥ 0) and equals zero for disconnected fleets. Higher γ indicates a more robustly connected, consensus-capable fleet; lower γ indicates fragile connectivity that may permit the fleet to fracture into isolated sub-groups under perturbation.

Algebraic connectivity was computed at every round of every simulation and live experiment. Eigenvalues were computed using standard symmetric eigendecomposition (scipy.linalg.eigh in Python 3.11), with numerical precision validated against known analytic cases (complete graphs, ring graphs) prior to experimental use.

### 4.2.2 Spectral Entropy (H)

The second principal measurement captures the distributional character of the full eigenspectrum, not only its second-smallest member.

**Definition 4.4 (Spectral Entropy).** Let {λ_i}_{i=1}^V be the eigenvalues of **L**(t). Define the normalized spectral weights:

$$p_i = \frac{|\lambda_i|}{\sum_{j=1}^{V} |\lambda_j|}$$

The spectral entropy is the Shannon entropy of this distribution:

$$H(t) = -\sum_{i=1}^{V} p_i \ln(p_i)$$

with the convention 0 · ln(0) = 0.

Spectral entropy measures the evenness of spectral mass distribution across eigenvalues. When all eigenvalues are equal in magnitude, H achieves its maximum value of ln(V) — spectral mass is evenly spread, and no single mode dominates the coupling dynamics. When spectral mass is concentrated on a single eigenvalue (e.g., a highly centralized hub-and-spoke topology where one eigenvalue dominates), H approaches zero.

This interpretation connects H to information-theoretic notions of complexity: a fleet with high H has a rich, multi-modal spectral structure, while a fleet with low H is spectrally simple. The conservation claim of Chapter 3 — that γ + H remains approximately constant under fleet-size variation — therefore asserts a specific trade-off: as a fleet grows and normalized connectivity γ falls, spectral complexity H rises to compensate, preserving total spectral information.

It warrants note that H as defined here uses absolute eigenvalue magnitudes. This choice was motivated by the need to handle the asymmetric, potentially negative coupling weights in **W** without encountering negative p_i values, which would render the standard entropy formula undefined. Sensitivity to this choice (versus using squared eigenvalues, or working directly from the eigenspectrum of **W** rather than **L**) was examined in Study 56 and found to not materially alter the conservation relationship.

### 4.2.3 The Conservation Metric (γ + H)

The primary observable throughout this dissertation is the sum:

$$\Gamma(t) = \gamma(t) + H(t)$$

**Definition 4.5 (Conservation Compliance).** Let Γ̂(V) denote the predicted value of Γ at fleet size V, derived from the empirical scaling relationship established in Chapter 5. A measurement Γ(t) is *compliant* if:

$$|\Gamma(t) - \hat{\Gamma}(V)| < \epsilon$$

where ε is a fleet-specific tolerance threshold. In simulation studies, ε was set to 0.05 (5% of the nominal range of Γ). In live validation, ε was relaxed to 0.10 to account for the additional variance introduced by real model outputs. Compliance rate — the fraction of rounds across which the measured Γ falls within ε of predicted — is reported as a secondary metric alongside the primary R² and significance statistics.

Γ was measured at every round of every experiment. For experiments tracking dynamic events (agent joins, leaves, adversarial injections), Γ was measured immediately before and immediately after the event to characterize the perturbation magnitude and recovery trajectory.

---

## 4.3 Experimental Protocol

### 4.3.1 Simulation Studies (Studies 54–75)

The core experimental evidence base consists of Monte Carlo fleet simulations spanning Studies 54 through 75. These simulations model agent outputs as random variables drawn from parameterized distributions, apply the Hebbian coupling update rule, and compute γ and H at each round. Synthetic simulation was chosen as the primary mode of investigation for three reasons: (1) it permits controlled manipulation of fleet size V, decay rate λ, and output distribution parameters that are not independently controllable in live LLM experiments; (2) it provides the sample sizes (500–35,000 per study) required for high-power statistical inference; and (3) it enables adversarial perturbation and agent turnover scenarios that would be costly or impractical to stage with real API-called models.

**Agent Output Model.** In the default simulation configuration, agent i at round t produces output:

$$x_i(t) \sim \mathcal{N}(\mu_i, \sigma^2)$$

where μ_i is agent-specific (drawn once at fleet initialization from Uniform(−1, +1)) and σ² = 1.0 is shared. This parameterization models a fleet of agents with differing systematic biases but comparable variance — a reasonable approximation for a heterogeneous LLM fleet on a well-defined question type. Alternative output distributions (Bernoulli, Laplace, mixture models) were explored in Studies 58–60, and the conservation relationship was found to hold qualitatively across distributions, though with quantitatively different scaling coefficients.

**Study Design.** Each simulation study was organized around one or more independent variables (fleet size, decay rate, coupling architecture, adversarial proportion) with Γ = γ + H as the primary dependent variable. The default study protocol was:

1. Initialize fleet of V agents with **W**(0) = **0**
2. Run R rounds of output generation and coupling updates (R = 100 default)
3. Compute γ(t), H(t), and Γ(t) at each round t
4. Record Γ at steady state (defined as rounds 80–100, after transient decay)
5. Repeat for N independent fleet instantiations (N = 9 default)
6. Aggregate across instantiations and report mean, 95% CI, and test statistics

Steady-state averaging over rounds 80–100 was adopted after Study 54 established that transient initialization effects dissipate within approximately 20–30 rounds for the default λ = 0.001 setting.

**Statistical Tests.** The following tests were applied uniformly across simulation studies unless noted:

- *Primary fit*: Ordinary least squares regression of mean Γ on ln(V), with R² as the measure of fit quality.
- *Significance against random baseline*: Two-tailed t-test comparing Γ distributions under Hebbian coupling against Γ distributions under random **W** matrices (entries drawn independently from Uniform(−1, +1)). The random baseline was matched in V and generated with the same number of instantiations N.
- *Effect size*: Cohen's d for pairwise comparisons; R² for regression fits. Cohen's conventions are followed throughout: d < 0.2 (negligible), 0.2 ≤ d < 0.5 (small), 0.5 ≤ d < 0.8 (medium), d ≥ 0.8 (large). R² ≥ 0.9 was adopted as the threshold for claiming a strong linear relationship.
- *Bootstrap confidence intervals*: 95% CIs on regression coefficients and effect sizes were computed via nonparametric bootstrap with 1,000 resamples.

Multiple comparison correction via Bonferroni was applied in studies involving three or more simultaneous hypotheses (Studies 62, 65, 68, 71). In early studies (54–61), Bonferroni correction was not applied; this limitation is noted in the Study 69 audit and discussed in Section 4.6.

All random processes were seeded with deterministic values logged to the study record, permitting exact reproduction of any individual simulation run.

### 4.3.2 Live Validation Experiment (E1)

To bridge simulation findings to real LLM behavior, Experiment E1 deployed a live fleet of five language models via the DeepInfra API, conducting 35 rounds of collaborative arithmetic reasoning under the coupling protocol.

**Fleet Composition.** Five models were selected to maximize architectural and training diversity while remaining within the API cost envelope for the experiment:

1. Seed-2.0-mini (ByteDance) — compact, instruction-tuned
2. Hermes-70B (NousResearch) — fine-tuned Llama derivative, strong reasoning
3. Qwen3.6-35B (Alibaba) — mixture-of-experts architecture
4. Qwen3-235B (Alibaba) — large-scale mixture-of-experts
5. Seed-2.0-code (ByteDance) — code-specialized variant

This composition was not random: the inclusion of two Qwen models at different scales tests whether architectural siblings form tighter coupling than architecturally distant models — a question with implications for the generality of the conservation law. Code-specialized versus general models provides a further axis of contrast.

**Question Protocol.** Each round consisted of 10 arithmetic reasoning problems, drawn from a fixed pool of 350 problems (10 per round × 35 rounds) generated prior to experiment commencement. Problems were matched in difficulty across rounds (verified by comparing human solution times on a pilot sample of 30 problems) to control for round-to-round difficulty variation as a confound. All problems had scalar numerical answers, enabling direct computation of the coupling matrix from agent output vectors.

**Coupling Construction.** At round t, each agent i produced a 10-dimensional output vector **x**_i(t) ∈ ℝ^{10} (one numeric answer per problem). The scalar coupling signal was computed as:

$$s_{ij}(t) = \frac{\mathbf{x}_i(t) \cdot \mathbf{x}_j(t)}{|\mathbf{x}_i(t)| \cdot |\mathbf{x}_j(t)|}$$

i.e., the cosine similarity of answer vectors. The Hebbian update then applied sign(s_{ij}(t)) to update W[i,j] with λ = 0.001. This construction generalizes the scalar case of Section 4.1.2 to vector outputs by using cosine similarity as the coupling signal, which is invariant to absolute answer magnitude and sensitive only to agreement structure.

**Baseline Comparison.** The null hypothesis was that the observed Γ values are indistinguishable from Γ values arising from a random coupling matrix of the same size. The random baseline was generated as an ensemble of 10,000 random 5×5 symmetric matrices with entries drawn from Uniform(−1, +1) and zero diagonal, with Γ computed for each. A two-tailed t-test compared the mean Γ observed across rounds 10–35 (post-initialization) against the random baseline distribution.

**API Management.** All API calls were made via asynchronous requests with retry logic (exponential backoff, maximum 3 retries). Call timestamps, model responses, and raw numeric outputs were logged to JSON for each round. Cached responses were not used — each round called the live API — but logs permit post-hoc reconstruction of the full experiment from raw outputs without re-calling the API.

### 4.3.3 Architecture Comparison Experiment (E3)

Experiment E3 compared the conservation behavior of four coupling architectures across six fleet sizes, to test whether the conservation relationship is specific to Hebbian coupling or a more general property of structured coupling.

**Architectures Tested:**

1. *Hebbian*: The update rule of Definition 4.1, as used throughout the main study.
2. *Attention-weighted*: W[i,j](t) = softmax_j(cos(**o**_i(t), **o**_j(t))) where **o**_i(t) is the output embedding of agent i. This architecture weights coupling by semantic similarity of outputs, mirroring transformer attention mechanisms.
3. *Random*: W[i,j](t) drawn fresh each round from Uniform(−1, +1); no persistent coupling memory. This serves as a within-experiment baseline.
4. *None*: **W**(t) = **0** for all t; effectively a disconnected fleet. This tests whether the conservation relationship is trivially satisfied by the zero matrix.

**Fleet Sizes:** V ∈ {3, 5, 7, 9, 15, 25} were tested for each architecture, for a total of 24 (architecture, fleet size) conditions.

**Protocol:** Each condition was run for 100 rounds with N = 50 independent instantiations. Primary outputs were: R² for the linear fit of mean Γ against ln(V), the slope β₁ of that fit, and the 95% CI on β₁ via bootstrap. Slopes were compared across architectures using two-sample t-tests with Bonferroni correction for six pairwise comparisons (α_corrected = 0.05/6 ≈ 0.0083).

---

## 4.4 Statistical Framework

### 4.4.1 Primary Inference Target

The central quantitative claim of this dissertation is that γ + H scales linearly with ln(V):

$$\mathbb{E}[\Gamma(V)] = \beta_0 + \beta_1 \ln(V) + \varepsilon$$

where ε is zero-mean residual error. The coefficient β₁ is the *conservation slope* — negative values indicate that as fleet size grows, the sum γ + H decreases in a log-proportional manner, consistent with the theoretical prediction of Chapter 3.

For each study, R² was computed as the proportion of variance in measured Γ values explained by this linear-log model. The threshold R² ≥ 0.9 was set a priori as the criterion for claiming strong support for the conservation relationship. This threshold is conservative relative to common practice in empirical machine learning research, where R² ≥ 0.7 is often accepted as strong fit; the stricter threshold was adopted because the theoretical claim is precise enough to demand tight empirical correspondence.

### 4.4.2 Hypothesis Testing

For each study, a null hypothesis H₀ : β₁ = 0 (no systematic relationship between Γ and fleet size) was tested against the two-tailed alternative H₁ : β₁ ≠ 0. Test statistics were computed using ordinary least squares with heteroscedasticity-robust standard errors (HC3 variant), as fleet-size-dependent variance heteroscedasticity was observed in pilot studies. The significance threshold was set at α = 0.05 throughout, with Bonferroni correction applied where multiple hypotheses were tested simultaneously.

A second set of hypothesis tests compared Hebbian-coupled fleets against random-matrix baselines at each fleet size V. Here the test statistic was:

$$t = \frac{\bar{\Gamma}_{\text{Hebbian}}(V) - \bar{\Gamma}_{\text{random}}(V)}{s_{\text{pooled}} \cdot \sqrt{2/N}}$$

under the assumption of equal-variance normal distributions, verified via Levene's test in each study.

Where normality could not be established (small N or heavy-tailed output distributions), the nonparametric Mann-Whitney U test was substituted and noted.

### 4.4.3 Effect Size Reporting

Effect sizes were reported for all significant findings. Cohen's d was computed for pairwise comparisons:

$$d = \frac{\bar{\Gamma}_1 - \bar{\Gamma}_2}{s_{\text{pooled}}}$$

For regression analyses, the partial η² and R² were both reported. The distinction matters: R² measures overall fit quality, while partial η² for a specific predictor (e.g., fleet size while controlling for decay rate) measures the proportion of residual variance explained by that predictor alone. Both are reported in Chapter 5 where relevant.

### 4.4.4 Bootstrap Confidence Intervals

All confidence intervals were computed via nonparametric bootstrap (1,000 resamples) applied at the level of fleet instantiations (resampling rows of the data matrix, where each row is one independent fleet run). This approach preserves the natural unit of independence — the fleet — rather than treating individual rounds within a fleet as independent observations (which they are not, due to temporal coupling within the Hebbian update rule). This distinction is methodologically important: naive CI computation treating rounds as independent would severely understate uncertainty and inflate apparent precision.

---

## 4.5 Reproducibility

### 4.5.1 Simulation Reproducibility

All simulation code is maintained in the SuperInstance/forgemaster repository. Each study file (e.g., study54_experiment.py) contains at its header a complete parameter specification including random seeds, fleet sizes, number of instantiations, and convergence criteria. Reproduction of any simulation study requires only the study file and the shared fleet simulation library, with no external dependencies beyond standard scientific Python (numpy, scipy, pandas ≥ versions logged in requirements.txt).

Random seeds were set globally at the start of each study run using numpy.random.seed(seed_value), with seed values drawn from a predetermined sequence logged in the study registry. This approach ensures inter-study independence (different seeds) while enabling per-study exact reproduction (fixed seeds). One limitation of global seeding is that it does not guarantee identical results across numpy version upgrades; the numpy version used in each study is therefore logged in the study record.

### 4.5.2 Live Experiment Reproducibility

Experiment E1 cannot be fully reproduced in the strong sense — live API responses vary across calls due to non-zero temperature settings (temperature = 0.7 was used to obtain naturalistic agent outputs rather than deterministic mode responses). However, exact reproduction of the *analysis* from raw outputs is ensured by: (1) complete logging of all raw model responses to timestamped JSON files; (2) deterministic post-processing pipeline (coupling construction, eigendecomposition, statistical tests) with fixed seeds; and (3) caching of all intermediate computations (coupling matrices at each round) to disk.

The choice to use non-zero temperature rather than greedy decoding was deliberate: a fleet of greedy decoders would exhibit substantially reduced output variance, potentially inflating coupling signal and artificially strengthening the conservation result. The temperature = 0.7 setting was intended to produce output diversity representative of realistic deployment conditions.

### 4.5.3 Calibration Principle

A critical methodological constraint governs all validation work: **the axis used for calibration must be independent of the axis used for validation.** Specifically, the parameters of the predicted Γ(V) curve (β₀ and β₁) were estimated from simulation studies, and live experiments were then tested for compliance against these simulation-derived predictions — never from a model fit to the live data itself. This is operationally analogous to the train/test split in supervised machine learning, but applied to the relationship between theoretical/simulation and empirical regimes.

Violation of this principle — calibrating on live data and then validating on the same live data — would constitute circular reasoning and would render the conservation claim unfalsifiable. The separation between simulation-derived predictions and live-experiment compliance checks is maintained throughout and is explicitly noted wherever predictions are cited.

### 4.5.4 Parameter Documentation

Conservation law parameters (the tolerance ε, the steady-state window, and the fleet-specific β₀ and β₁) are documented per-deployment in a configuration manifest stored alongside the study code. This ensures that any deployment of the conservation monitoring system uses the appropriate parameters for its fleet context rather than parameters from a different organizational setting.

---

## 4.6 Limitations Acknowledged

This section pre-registers the methodological limitations of the present work, distinguishing those that are inherent to the research question from those that are contingent on resource constraints and could be addressed in future work.

**Synthetic agents in simulation.** The majority of experiments (Studies 54–75) use synthetic agents whose outputs are drawn from parametric distributions rather than real language models. This is a significant limitation because real LLMs exhibit structured, correlated, and contextually sensitive outputs that no simple parametric distribution captures. The correlation structure of real outputs may produce coupling dynamics that differ qualitatively from synthetic dynamics, potentially inflating or deflating the conservation signal. Experiment E1 partially addresses this by validating on real models, but with V = 5 and 35 rounds, it does not provide sufficient coverage to fully generalize the simulation findings.

**Default fleet size N = 9.** The default of N = 9 independent fleet instantiations per condition is small. This was flagged in the Study 69 audit: at N = 9, the 95% CI on Cohen's d is wide (approximately ±0.6 for d ≈ 0.8), and results that pass significance at α = 0.05 with N = 9 would not survive at more stringent thresholds under conventional power analysis. Studies reporting large effect sizes (d > 0.8) with N = 9 are credible in direction but uncertain in magnitude. Post-hoc power analysis for the primary conservation hypothesis (β₁ ≠ 0) suggests that N ≥ 30 would be required for 80% power at the observed effect sizes and variance levels. This limitation does not affect studies with larger sample sizes (e.g., Study 62 at N = 1000), but it is a standing concern for the main simulation series.

**Bonferroni correction absent in early studies.** Studies 54–61 did not apply Bonferroni correction for multiple comparisons, as the number of simultaneous hypotheses was not always clearly specified at study design time. This increases the family-wise Type I error rate across those studies. The Study 69 audit identified this gap and corrected it for subsequent studies; findings from Studies 54–61 that depend on marginal significance (0.01 < p < 0.05) should be interpreted with caution pending replication with correction applied.

**Live validation at p = 0.0425.** The primary significance result from Experiment E1 (two-tailed t-test of Hebbian Γ against random baseline) yields p = 0.0425, which clears the conventional α = 0.05 threshold but not a more stringent threshold such as α = 0.01. With V = 5 agents and 35 rounds, the experiment was underpowered for confident rejection at p < 0.01. This is acknowledged as a limitation: the live validation provides directional support for the conservation claim, but does not constitute strong confirmation at conventional standards for small-scale empirical studies.

**Limited fleet size coverage in live experiments.** Live data are available primarily at V ∈ {3, 5, 7, 9}, with no live observations at V ≥ 25. The log-linear relationship γ + H ~ ln(V) is most consequential and most discriminating at larger V, where the curvature of ln(V) most clearly distinguishes the hypothesized relationship from alternative functional forms (linear, polynomial). The absence of live validation at V > 25 is therefore a substantive gap: the scaling claim at large fleet sizes rests exclusively on simulation evidence.

**Single organizational context.** All data — both simulated and live — derive from or are calibrated to a single fleet deployment context (Cocapn). The conservation parameters β₀ and β₁ are estimated from this context and may not generalize to fleets with different coordination protocols, agent roles, or communication topologies. Whether the conservation law holds universally across organizational architectures, or whether it is a property specific to the PLATO room-based design, remains an open empirical question. This limitation motivates the experimental architecture comparison (E3) as a partial within-context probe of architectural dependence, but multi-organizational replication is beyond the scope of the present work.

**Zero initialization transients.** Initializing **W**(0) = **0** introduces a transient period (approximately 20–30 rounds) during which the conservation metric Γ has not yet stabilized. All analyses in this dissertation exclude this transient window from the primary inference, using steady-state measurements. However, in live deployments where a conservation monitor must be active from round 1, transient behavior is operationally significant and the present results do not characterize it fully.

**Scalar output reduction.** In live experiments, multi-dimensional model outputs (10 answers per round) were reduced to a scalar coupling signal via cosine similarity. While cosine similarity is a principled choice, it discards information about the pattern of agreements and disagreements across individual questions within a round — a richer coupling signal might reveal structure not captured by the simple conservation metric. The sensitivity of the conservation relationship to the choice of coupling signal reduction is not fully characterized.

These limitations are not presented as fatal to the conservation claim but as constraints on the inference scope. The claims advanced in Chapter 5 are explicitly scoped to the regimes and contexts in which the methodology establishes them.
