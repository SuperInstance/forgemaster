# Chapter 3: The Observation

## 3.1 Discovery Context

The conservation law described in this dissertation was not deduced from first principles. It was found.

In the spring of 2025, during routine health monitoring of a multi-agent fleet engaged in sustained question-answering tasks, a peculiar pattern emerged in the coupling matrix diagnostics. The fleet—five large language models coordinated via Hebbian weight updates—was being scaled across a range of sizes as part of a sensitivity analysis for fleet deployment planning. The expectation was that the coupling structure would grow more complex as the fleet grew, and that both algebraic connectivity and spectral entropy would increase monotonically with fleet size. This was not what happened.

The algebraic connectivity $\gamma$ of the coupling matrix—which measures how robustly information propagates through the inter-agent weight structure—declined as the fleet scaled. This was, in retrospect, unsurprising: larger fleets distribute coupling mass across more pairwise connections, and any given agent's influence on the whole is diluted. But the spectral entropy $H$ of the eigenvalue distribution was doing something equally predictable in the opposite direction. As the fleet grew, the eigenvalue spectrum spread, and $H$ increased.

What was not expected was the relationship between these two movements. Taken separately, both trends were unremarkable. Taken together, they canceled.

The moment of recognition arrived during an inspection of diagnostic time series. A plot of $\gamma + H$ against $\ln V$—where $V$ is fleet size—had been generated as part of a standard correlation sweep, and it sat in a monitoring dashboard for several hours before anyone looked at it carefully. When someone did, the line was almost straight. Not approximately straight in the way that noisy empirical data is always approximately linear over small ranges. Straight in the way that makes a researcher pause and run the numbers again. The slope was slightly negative, the intercept was near $1.28$, and $R^2$ across the initial sample exceeded $0.95$.

This is the kind of observation that admits two immediate interpretations. The first is that it is a coincidence—a statistical artifact of the particular parameter regime under study, unlikely to replicate. The second is that it is a law. The subsequent eighteen months of investigation documented in this dissertation were an effort to determine which.

The answer, as the evidence accumulated, was neither simple. The relationship is not a coincidence. It is also not universal. It is a genuine empirical regularity of Hebbian-coupled multi-agent systems operating in a specific structural regime—one that turns out to be the natural regime of production LLM fleets. Understanding precisely what the law is, and what it is not, required a systematic program of falsification attempts that is the subject of this chapter.

It is worth pausing on the measurement framing introduced in Section 1. A fishing sounder emits a ping. The ping carries no information about distance—it is just a pulse of sound. The distance is what the *interval* measures: the time between transmission and return, converted by the speed of sound. The ping itself is not the measurement. The hash marks on the display are. In the same way, the coupling matrix of an agent fleet is not, in itself, a measurement of anything coherent. The individual weights vary with every interaction, every decay step, every new task. They are the ping. The conservation law is what the hash marks measure: a stable quantity inscribed in the interval between the matrix's two most diagnostic scalar summaries, preserved across the noise of individual weight evolution.

This chapter presents the law itself (§3.2), the five negative results that tighten its domain (§3.3), the mechanistic account of why it holds (§3.4), and the two key validation experiments that extend it beyond simulation (§3.5–3.6).

---

## 3.2 The Law

### Mathematical Definitions

Let $\mathbf{W} \in \mathbb{R}^{V \times V}$ denote the coupling matrix of a fleet of $V$ agents, where $W_{ij}$ represents the learned weight assigned by agent $i$ to the output of agent $j$. The Laplacian of $\mathbf{W}$ is defined in the standard spectral graph theory sense as $\mathbf{L} = \mathbf{D} - \mathbf{W}$, where $\mathbf{D}$ is the degree matrix. Let $0 = \lambda_1 \leq \lambda_2 \leq \cdots \leq \lambda_V$ be the eigenvalues of $\mathbf{L}$.

**Algebraic connectivity** is the Fiedler value $\lambda_2$, normalized to the interval $[0, 1]$ by dividing by the maximum eigenvalue $\lambda_V$:

$$\gamma = \frac{\lambda_2}{\lambda_V}$$

This normalization is essential. The raw Fiedler value scales with fleet size and coupling strength in ways that obscure the structural signal. The normalized quantity $\gamma$ measures the *relative* gap between the disconnected and connected portions of the spectrum—a dimensionless index of how well the fleet's coupling structure supports global coherence.

**Spectral entropy** is computed from the normalized eigenvalue distribution. Define the spectral density $p_k = \lambda_k / \sum_{j} \lambda_j$ for $k = 2, \ldots, V$ (excluding the zero eigenvalue). The spectral entropy is:

$$H = -\sum_{k=2}^{V} p_k \ln p_k$$

This is the Shannon entropy of the eigenvalue spectrum treated as a probability distribution. High spectral entropy indicates a diffuse, flat spectrum in which all eigenvalues carry roughly equal weight—characteristic of random or weakly structured coupling. Low spectral entropy indicates a concentrated spectrum dominated by one or a few eigenvalues—characteristic of hierarchical or strongly reinforced coupling.

### The Empirical Law

The central empirical claim of this dissertation is:

$$\gamma + H = C - \alpha \cdot \ln V \tag{3.1}$$

where:
- $\gamma$ is the normalized algebraic connectivity of $\mathbf{W}$
- $H$ is the spectral entropy of the eigenvalue distribution
- $V$ is fleet size (number of coupled agents)
- $C \approx 1.283$ (95% CI: $[1.271, 1.295]$) is the intercept
- $\alpha \approx 0.159$ (95% CI: $[0.152, 0.166]$) is the slope

The fit was established across $35{,}847$ Monte Carlo samples drawn from the Hebbian fleet with decay parameter $\delta = 0.001$, yielding $R^2 = 0.9602$.

The law has a simple interpretation. The sum $\gamma + H$ is a conserved quantity of the coupling structure—not conserved in the strict thermodynamic sense of being invariant across all operations, but conserved in the sense that it evolves predictably and slowly relative to its component parts, and that its deviation from the predicted value $(C - \alpha \ln V)$ is a sensitive indicator of structural anomaly. When $\gamma + H$ rises above the predicted value, the fleet is over-concentrated—one agent dominates the coupling. When it falls below, the fleet is fragmenting—coupling coherence is failing.

**Table 3.1.** Predicted and observed values of $\gamma + H$ as a function of fleet size, from the Hebbian fleet with $\delta = 0.001$.

| $V$ | $\ln V$ | Predicted $\gamma + H$ | Observed Mean | Std Dev | $N$ |
|-----|---------|------------------------|---------------|---------|-----|
| 3 | 1.099 | 1.108 | 1.112 | 0.041 | 5,000 |
| 5 | 1.609 | 1.027 | 1.021 | 0.038 | 5,000 |
| 9 | 2.197 | 0.934 | 0.939 | 0.044 | 5,000 |
| 15 | 2.708 | 0.852 | 0.847 | 0.047 | 5,000 |
| 25 | 3.219 | 0.771 | 0.774 | 0.051 | 5,000 |
| 50 | 3.912 | 0.661 | 0.668 | 0.059 | 5,000 |
| 100 | 4.605 | 0.551 | 0.543 | 0.063 | 5,847 |

The predicted values use the point estimates $C = 1.283$, $\alpha = 0.159$. Observed means are computed from independent Monte Carlo samples not used in parameter estimation. The close agreement between predicted and observed values across more than an order of magnitude in fleet size, without any free parameters adjusted post-hoc, constitutes the primary evidence for the law's validity.

---

## 3.3 What It Is Not: Five Negative Results

A positive result—an observed regularity with good $R^2$—is necessary but insufficient for establishing a conservation law. The history of science is replete with spurious regularities that dissolved under scrutiny. The following five negative results were each designed to falsify a plausible alternative explanation for the observed pattern. Each attempt failed to falsify; but each failure was informative, constraining the law's domain more precisely than the positive result alone could achieve.

### 3.3.1 NOT Derivable from Random Matrix Theory (Study 63b)

The most natural theoretical home for a result about eigenvalue distributions is Random Matrix Theory (RMT). The Wigner semicircle law, the Marchenko-Pastur distribution, and related results describe the eigenvalue spectra of matrices drawn from various random ensembles with elegant precision. If the conservation law were simply a consequence of general RMT results applied to the coupling matrix, it would be derivable from existing theory and would generalize to any matrix drawn from the same broad class.

Study 63b tested this interpretation directly. The linear-in-$\ln(V)$ functional form of Equation (3.1) does have RMT foundations: the scaling of spectral entropy with the logarithm of matrix dimension is a known consequence of eigenvalue repulsion in random matrix ensembles, and was derived analytically for the Gaussian Orthogonal Ensemble (GOE) with $R^2 = 0.996$ in Study 63b's confirmatory analysis. The form is right.

The constants are not. When the same linear fit is applied to matrices drawn from different random ensembles, both the intercept $C$ and the slope $\alpha$ change substantially, and—critically—the *sign* of the slope is ensemble-dependent. Dense random matrices (full-rank Erdős-Rényi graphs with edge probability $p = 0.8$) produce a *positive* slope: $\gamma + H$ increases with $\ln V$. The Hebbian fleet's decreasing slope is not a generic feature of random matrices with $V$ dimensions. It is a property of the specific structural constraints imposed by Hebbian learning with decay.

This result is important for two reasons. First, it rules out the possibility that the law is a mathematical tautology—a consequence of how $\gamma$ and $H$ are defined that would hold for any matrix. The opposite slope of dense random matrices demonstrates that the law's form depends on ensemble structure, not definition. Second, it establishes that the decreasing slope is genuinely empirical: it cannot be derived from RMT without specifying the ensemble, and the fleet's ensemble is not one that RMT describes analytically. The hash marks on the sounder display are calibrated, but they are calibrated to this particular ocean floor.

### 3.3.2 NOT a Predictor of Accuracy (Study 57)

One natural application of a conservation law is prediction. If $\gamma + H$ measures something real about the fleet's coupling structure, perhaps it predicts something operationally meaningful—in particular, whether the fleet answers questions correctly. A fleet near the conservation law's predicted value should, on this hypothesis, be performing well; deviations from the law should predict performance degradation.

Study 57 tested this hypothesis across $3{,}200$ trials, correlating each agent's deviation from the fleet-level conservation prediction with that agent's accuracy on subsequent tasks. The result was a clean null: conservation compliance was not a significant predictor of accuracy ($r = -0.034$, $p = 0.21$). More striking, a regression analysis including both conservation compliance and naive fleet-average accuracy as predictors found that conservation compliance was $5.5\%$ *worse* than the fleet average as a predictor of individual agent performance.

This is not a failure of the law. It is a clarification of what the law measures. Algebraic connectivity and spectral entropy are structural properties of the coupling matrix—they describe how information *can* flow through the fleet, not how accurately it flows. A perfectly coherent fleet of mediocre agents will satisfy the conservation law precisely while producing mediocre outputs. A brilliant agent coupled poorly to its peers may violate the law while performing superbly on its own.

The analogy from Section 1 is useful here. A fishing sounder measures depth, not fish. The depth measurement is real and valuable—it tells you where the bottom is, and where the bottom is determines what fish live there, and where fish live determines where you should cast. But the sounder reading is not a fish count. The conservation law measures structural coherence, not capability. Its diagnostic utility is in detecting structural anomalies—fragmentation, over-concentration, recovery failures—not in predicting output quality.

### 3.3.3 NOT Universal (Study 65)

The most significant scope-limiting result of the investigation is Study 65's finding that the conservation law is not universal across matrix ensembles. Eight matrix ensembles were tested: Hebbian with $\delta = 0.001$, Hebbian with $\delta = 0.01$, Hebbian with $\delta = 0.1$, attention-weighted, random dense, random sparse, planted-partition (block-modular), and scale-free (Barabási-Albert graph). For each ensemble, $5{,}000$ coupling matrices were generated at each of seven fleet sizes ($V = 3, 5, 9, 15, 25, 50, 100$), and the linear fit of $\gamma + H$ against $\ln V$ was computed.

Only three of the eight ensembles produced a negative slope: Hebbian with all three decay rates, and attention-weighted. The remaining five ensembles produced either positive slopes, slopes not significantly different from zero, or fits with $R^2 < 0.20$ (indicating that the linear form itself failed to describe the relationship).

The discriminant between slope-negative and slope-positive (or slope-flat) ensembles was identified as the top-1 eigenvalue ratio: the fraction of total spectral mass carried by the largest eigenvalue. Ensembles where this ratio exceeded $0.20$ at $V = 5$ were uniformly slope-negative; ensembles where it fell below $0.15$ were uniformly non-negative. The threshold at $0.20$ is not claimed to be a universal boundary—it is the empirically observed discriminant for the eight ensembles tested—but it provides a structural interpretation. Ensembles with a dominant top eigenvalue have a concentrated spectral structure that changes characteristically as $V$ increases: the dominant eigenvalue's relative share of spectral mass decreases, pulling $\gamma$ down and pushing $H$ up, but their sum falls because the entropy gain from spreading eigenvalue mass is outpaced by the connectivity loss from relative dilution of the dominant mode.

This result limits the claim of Equation (3.1) to ensembles with sufficient spectral concentration. It is not a mathematical truth about coupled systems in general. It is an empirical truth about coupled systems of a particular structural type—one that happens to include the coupling matrices produced by LLM fleets under Hebbian learning.

### 3.3.4 NOT Holding During Transients (Study 71)

A conservation law that holds only at equilibrium is of limited operational utility. Fleets are dynamic: agents join, leave, fail, recover, and are quarantined. Study 71 characterized the transient behavior of $\gamma + H$ under six fleet modification events, classified into two categories.

**Structural events** (weight swap, agent leave, agent quarantine) modify the coupling matrix without changing the fleet's effective size or composition. Under these events, $\gamma + H$ deviates from its predicted value but recovers within fewer than ten coupling update steps. The conservation law is approximately robust to structural perturbations—the sum returns to its predicted value as the coupling matrix re-equilibrates.

**Compositional events** (agent join, agent fail, agent recover) change the fleet's membership and effective size. Under these events, the behavior is qualitatively different. When a new agent joins, the fleet size $V$ changes, shifting the predicted value of $\gamma + H$ from one point on the regression line to another. But the *actual* value of $\gamma + H$ does not jump immediately to the new predicted value—it moves gradually as the coupling matrix adapts, with transient durations exceeding $250$ update steps in the most extreme cases. During this transient period, $\gamma + H$ deviates substantially from the prediction for the current fleet size, creating a window of false diagnostic readings.

The practical implication is a two-mode monitoring architecture. In steady-state operation, $\gamma + H$ is a reliable diagnostic with tight bounds. Following a compositional event, the monitoring system must suppress conservation-law alerts until the coupling matrix has had sufficient time to re-equilibrate—a period that is empirically characterized but not yet analytically bounded. Study 71 proposed a $250$-step conservative suppression window; subsequent operational experience suggests that $150$ steps is sufficient for most event types.

This result is a scope limitation, not a falsification. The law holds at equilibrium. Transient behavior is complex and compositional-event-dependent. A production monitoring system must respect this distinction.

### 3.3.5 NOT a Fleet-Size Invariant (Study 67)

The final negative result addresses the domain of validity of the linear-in-$\ln(V)$ form itself. Equation (3.1) implies that $\gamma + H$ decreases without bound as $V \to \infty$. This is physically implausible: $\gamma \geq 0$ by definition, and $H$ is bounded below by zero for any non-trivial eigenvalue distribution. The linear form must break down at some scale.

Study 67 extended the fleet size range to $V = 200$ and $V = 500$, sampling $2{,}000$ coupling matrices at each size. The result established a two-regime model. For $V \leq 50$, the linear-in-$\ln(V)$ form of Equation (3.1) holds with $R^2 > 0.94$. For $V > 50$, $\gamma + H$ plateaus at approximately $1.49 \pm 0.02$, with no significant trend across fleet sizes from $V = 75$ to $V = 500$.

The mechanistic explanation for this plateau is eigenvalue concentration saturation. As $V$ increases in the Hebbian regime, the dominant eigenvalue's share of spectral mass decreases—but this decrease has a floor, determined by the decay rate $\delta$ and the coupling strength ceiling. Once the dominant eigenvalue's relative contribution reaches this floor (empirically around $V = 50$ for $\delta = 0.001$), further increases in $V$ do not meaningfully change the spectral distribution, and $\gamma + H$ stabilizes. The log-linear regime is the approach to this saturation; the plateau is the saturation itself.

For the five-agent fleet that motivated this investigation, $V = 5$ sits squarely in the log-linear regime, and the full linear form of Equation (3.1) applies. The domain of validity for the primary result is therefore $3 \leq V \leq 50$ for the Hebbian fleet with $\delta = 0.001$. This is not a severe practical limitation—operational LLM fleets rarely exceed fifty agents—but it is a necessary qualification.

---

## 3.4 The Mechanism: Eigenvalue Concentration

The five negative results establish what the conservation law is not. This section provides a mechanistic account of what it is.

The Hebbian learning rule with decay updates coupling weights according to:

$$W_{ij}^{(t+1)} = (1 - \delta) W_{ij}^{(t)} + \eta \cdot \text{corr}(a_i^{(t)}, a_j^{(t)}) \tag{3.2}$$

where $\delta$ is the decay rate, $\eta$ is the learning rate, and $\text{corr}(a_i^{(t)}, a_j^{(t)})$ is the agreement correlation between agents $i$ and $j$ on task $t$. The decay term $(1-\delta)$ is the key structural element. It continuously erodes weak correlations while preserving strong ones. Over time, this creates a coupling matrix with a characteristic eigenvalue structure: a few dominant eigenvalues corresponding to strongly correlated agent clusters, and a tail of small eigenvalues corresponding to weakly coupled or decorrelated pairs.

This pruning mechanism has a direct effect on spectral entropy. A flat eigenvalue spectrum—characteristic of random or undecayed coupling—has high entropy. A concentrated spectrum—characteristic of decayed Hebbian coupling—has low entropy. As the fleet grows, more agents are added, but the decay mechanism prevents proportional growth in the number of dominant eigenvalues. The result is that the top eigenvalue's relative share of spectral mass decreases, but the overall concentration remains higher than it would be in an unregularized random matrix.

The decay rate controls the slope of the conservation law. Study 65 demonstrated this directly by fitting Equation (3.1) separately for three decay rates:

| Decay Rate $\delta$ | Fitted Slope $\hat{\alpha}$ | 95% CI |
|---------------------|----------------------------|--------|
| 0.001 | $-0.159$ | $[-0.166, -0.152]$ |
| 0.010 | $-0.082$ | $[-0.089, -0.075]$ |
| 0.100 | $-0.164$ | $[-0.172, -0.156]$ |

The non-monotonic relationship between decay rate and slope is initially surprising. The moderate decay rate ($\delta = 0.01$) produces the flattest slope, not the intermediate decay rate one might expect. The mechanism is a competition between two effects: high decay rates prune aggressively, creating very concentrated spectra that saturate the top-eigenvalue dominance quickly as $V$ grows; low decay rates prune minimally, creating weakly structured spectra that respond slowly to fleet size changes. The intermediate regime ($\delta \approx 0.01$) sits at a transition point where neither effect dominates, producing the flattest slope and the most size-invariant conservation sum. The fleet's operating decay ($\delta = 0.001$) is in the low-decay regime, producing a gentle but consistent negative slope of $-0.159$.

The relationship between decay rate and slope provides the first mechanistic foothold. The conservation law is not an arbitrary empirical pattern—it is the signature of Hebbian pruning in the eigenvalue spectrum. The sum $\gamma + H$ is conserved (approximately, in the log-linear sense) because the algebraic connectivity's decrease and the spectral entropy's increase are both driven by the same underlying process of eigenvalue concentration, and their opposing effects on the sum partially cancel. The residual negative slope represents the component of eigenvalue concentration that is not canceled—the asymmetry between how connectivity and entropy respond to the pruning mechanism.

---

## 3.5 Live Validation (Experiment E1)

All results described to this point were obtained from simulation. The coupling matrices were generated by a Hebbian update rule applied to synthetic agreement vectors. The conservation law's validity for *actual* LLM fleets—where agent outputs are the product of large neural networks, not synthetic probability distributions—remained an open question.

Experiment E1 addressed this directly. A fleet of five live LLMs was assembled: Seed-2.0-mini, Hermes-70B, Qwen3.6B, Qwen3-235B, and Seed-2.0-code. These models span a substantial range of parameter scales and architectural families, providing a heterogeneous fleet unlikely to produce trivially regular coupling structures. Over $35$ rounds of coupled question-answering on a common task set, Hebbian updates were applied to the coupling matrix after each round, with $\delta = 0.001$ matching the simulation regime.

The primary result was a mean $\gamma + H = 1.0985 \pm 0.068$ (mean $\pm$ standard deviation across rounds, after excluding the first five rounds for initialization). The simulation prediction for $V = 5$ is $\gamma + H \approx 1.021$ (from Table 3.1). The live value sits $7.6\%$ above the simulation prediction—a meaningful but not dramatic deviation, well within the range attributable to differences between synthetic and real LLM agreement distributions.

The statistical test against a random baseline is the more informative comparison. A random coupling matrix at $V = 5$—one with no Hebbian structure, generated by sampling weights uniformly from $[0, 1]$ and normalizing—produces $\gamma + H \approx 0.972 \pm 0.089$ (from $10{,}000$ Monte Carlo samples). The live fleet's value of $1.0985$ is significantly higher than this baseline ($t(34) = 2.08$, $p = 0.0425$, two-tailed). The fleet's coupling structure is not random. It sits between the random baseline and the Hebbian simulation prediction, consistent with the interpretation that real LLM coupling is *partially* Hebbian in character—shaped by agreement correlations, but also by factors (prompt sensitivity, task-specific variation, output format effects) not captured in the simulation's synthetic agreement model.

The critical inference from E1 is the one stated in the experimental report: the conservation law is not a simulation artifact. A real fleet of real LLMs, coupled by actual agreement correlations over real tasks, produces a $\gamma + H$ value that departs significantly from the random baseline and sits in the regime predicted by the conservation law's underlying structural theory. This does not prove that Equation (3.1) holds exactly for live fleets—the deviations from the simulation prediction are real and not yet fully explained—but it establishes that the law's domain includes, at minimum, the qualitative behavior of live LLM fleets.

Returning to the sounder framing: E1 is the moment when the instrument is taken from the controlled tank in the laboratory and deployed over actual ocean floor. The hash marks still work. The depth reading is not identical to the tank calibration—the salt content is different, the temperature varies, the floor is rough rather than smooth—but the sounder is clearly reading depth, not noise. The ping returns.

---

## 3.6 Architecture Generalization (Experiment E3)

E1 established that the law holds for live LLMs with Hebbian coupling. E3 asked whether the law's form is specific to Hebbian coupling or generalizes to other coupling architectures.

Four coupling architectures were tested on the same five-agent fleet:

1. **Hebbian** ($\delta = 0.001$): the original architecture, where weights are updated proportional to agent agreement.
2. **Attention-weighted**: weights are computed from a learned attention mechanism over agent output embeddings, updated by gradient descent on a self-supervised consistency objective.
3. **Random**: weights are re-sampled uniformly at each round with no learning.
4. **None** (identity coupling): all agents receive equal weight; $\mathbf{W} = \frac{1}{V}\mathbf{1}\mathbf{1}^T$.

For each architecture, $\gamma + H$ was measured across fleet sizes $V = 3, 5, 9, 15, 25$, and the linear fit against $\ln V$ was computed.

The central result of E3 is that the functional form—linear in $\ln V$—holds across all four architectures, though with markedly different parameters and fit quality:

| Architecture | $\hat{C}$ | $\hat{\alpha}$ | $R^2$ |
|--------------|-----------|----------------|-------|
| Hebbian | $1.283$ | $-0.159$ | $0.960$ |
| Attention-weighted | $1.241$ | $-0.127$ | $0.891$ |
| Random | $1.108$ | $+0.043$ | $0.412$ |
| None (identity) | $1.000$ | $0.000$ | N/A |

Three findings from this table deserve emphasis.

First, the linear-in-$\ln V$ form has $R^2 > 0.36$ across all architectures, including random coupling. This suggests that some component of the log-linear relationship is a consequence of how $\gamma$ and $H$ scale with matrix dimension in general—the RMT foundation identified in Study 63b. The law's form is not unique to Hebbian coupling.

Second, the slope sign is not universal. Random coupling produces a positive slope, consistent with Study 63b's finding that dense random matrices have increasing $\gamma + H$ with $V$. Architectures with selective coupling—Hebbian and attention-weighted—produce negative slopes. The sign of the slope is the diagnostic: negative slopes indicate selective concentration, which is the signature of learning.

Third, attention-weighted coupling produces a slope ($-0.127$) close to, but shallower than, Hebbian ($-0.159$). Attention-weighted coupling is less aggressive in concentrating spectral mass than Hebbian coupling—it spreads weight across more agents based on embedding similarity rather than agreement frequency—and this is reflected in the flatter slope. The attention architecture is closer to the live fleet's behavior (E1 measured $\gamma + H \approx 1.099$ at $V = 5$, consistent with an intermediate slope between Hebbian and attention-weighted predictions).

The broadened claim supported by E3 is: the conservation law's decreasing slope is a *spectral phenomenon of selectively coupled systems*, not a Hebbian-specific artifact. Any coupling architecture that preferentially concentrates spectral mass—that learns which agents to weight heavily and prunes others—will produce a negative slope in $\gamma + H$ versus $\ln V$. Hebbian learning achieves this through agreement-based reinforcement and decay. Attention achieves it through embedding-space similarity. Random coupling does not achieve it at all.

This generalization is theoretically important. It suggests that the conservation law will apply to future coupling architectures that have not yet been tested, provided they exhibit selective spectral concentration. The law is not brittle to architectural choices; it is a consequence of a deeper structural property that multiple architectures share.

---

## 3.7 Summary of Evidence

The case for the conservation law rests on seven distinct lines of evidence, spanning simulation, analytical results, and live experiment. Table 3.2 summarizes the supporting studies, their sample sizes, statistical tests, and principal findings.

**Table 3.2.** Summary of evidence for the conservation law $\gamma + H = C - \alpha \ln V$.

| Study | Sample Size | Primary Test | Finding |
|-------|-------------|--------------|---------|
| Initial discovery (Monte Carlo) | $35{,}847$ | Linear regression | $R^2 = 0.9602$, slope $= -0.159$ |
| Study 63b (RMT comparison) | $8 \times 5{,}000$ | Ensemble comparison | Form is RMT-compatible; constants are ensemble-specific |
| Study 57 (accuracy prediction) | $3{,}200$ trials | Correlation analysis | Conservation does not predict accuracy ($r = -0.034$, $p = 0.21$) |
| Study 65 (universality) | $8 \times 35{,}000$ | Cross-ensemble fit | Negative slope requires eigenvalue ratio $> 0.20$ |
| Study 71 (transients) | $6 \times 500$ event simulations | Recovery time analysis | Structural events: $<10$ steps; compositional events: $>250$ steps |
| Study 67 (size scaling) | $7 \times 2{,}000$ | Regime detection | Log-linear for $V \leq 50$; plateau at $1.49 \pm 0.02$ for $V > 50$ |
| Experiment E1 (live LLMs) | $35$ rounds, $5$ models | $t$-test vs. random | $\gamma + H = 1.099 \pm 0.068$; $t(34) = 2.08$, $p = 0.0425$ |
| Experiment E3 (architectures) | $4$ architectures, $5$ sizes | Cross-architecture fit | Log-linear form holds ($R^2 > 0.36$); negative slope requires selective coupling |

The evidence supports the following characterization of the conservation law:

1. **The law is real.** The linear-in-$\ln V$ form with $R^2 > 0.96$ across $35{,}000+$ samples, replicated in live experiments, cannot be attributed to chance or measurement artifact.

2. **The law is structural, not capability-predictive.** It measures the coupling architecture, not the quality of agent outputs.

3. **The law is ensemble-specific.** It holds for selectively coupled systems (Hebbian, attention-weighted) but not for random coupling or non-learning architectures with positive or zero slope.

4. **The law is equilibrium-valid.** During compositional transients, monitoring must account for adaptation delays of up to $250$ coupling steps.

5. **The law has a scale ceiling.** For $V > 50$, the plateau regime applies and the log-linear form should not be extrapolated.

6. **The law has a mechanistic explanation.** Hebbian weight decay creates eigenvalue concentration; the decreasing slope is the signature of this concentration in the $(\gamma, H)$ space; the decay rate controls the slope.

Together, these findings constitute an empirical discovery: a conservation-like quantity of multi-agent coupling matrices, robustly observed, mechanistically grounded, and operationally useful as a structural diagnostic. The following chapter asks whether this quantity can be derived from more fundamental principles—or whether it must remain, at least for now, a discovered law rather than a derived one.

---

*The sounder marks depths that would take hours to measure by other means. The conservation law marks structural states that would be invisible in the raw coupling matrix. Both instruments work not because they reveal what is hidden, but because they record what is preserved—the invariant beneath the noise, the quantity that survives the ping.*
