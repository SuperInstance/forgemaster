## 5.4 Experiment 3: Coupling Architecture Comparison

The preceding experiments established that the conservation law τ(E) ∝ V^β is a robust, scale-sensitive property of the collective system and that its negative slope is inversely related to fleet size N. A critical question remains unresolved: *what properties of the coupling mechanism produce the negative slope?* Two plausible mechanisms present themselves. The first, drawn from biological neural systems, is Hebbian plasticity—strengthening connections between co-active units. The second, inspired by machine learning attention mechanisms, is selective spectral concentration—routing information through channels weighted by output similarity. Experiment 3 isolates the coupling architecture variable to determine which mechanism, if either, is necessary and sufficient for the conservation law's decreasing slope.

### 5.4.1 Method

Four coupling architectures were implemented within the same collective inference framework used in Experiments 1 and 2. All other parameters were held constant: vocabulary sizes V ∈ {5, 10, 20, 30, 50}, 50 independent seeded runs per condition, and 200 learning steps per run. The Bonferroni-corrected significance threshold was set at α = 0.00417 to account for the six pairwise comparisons among four architectures.

The four architectures were defined as follows. **Hebbian coupling** implemented classical Hebbian plasticity with decay: ΔC_ij = η·xᵢxⱼ − λ·C_ij, where η = 0.01 and λ = 0.01. Connections strengthened between simultaneously active units and decayed otherwise, producing a coupling matrix that reflected accumulated co-activation statistics. **Attention-weighted coupling** applied a softmax function over output similarity scores, combined with a 70/30 momentum blend that preserved 70% of the prior coupling state and incorporated 30% new information at each step. This architecture concentrated spectral mass on channels with high output similarity. **Random Erdős–Rényi (ER) coupling** maintained a fixed-density random graph, rewiring 30% of edges at each learning step while preserving the overall connection density. This controlled for the effect of dynamic coupling without any learning or selection mechanism. **No coupling (None)** regenerated a fully random coupling matrix at each step, providing a baseline in which no persistence, learning, or selection occurred.

For each architecture, the slope β of log(τ) against log(V) was estimated via ordinary least squares regression, with 95% confidence intervals computed using heteroscedasticity-robust standard errors (White, 1980). Pairwise comparisons of slopes were conducted using two-tailed independent-samples *t*-tests with Bonferroni correction. Effect sizes were quantified using Cohen's *d*.

### 5.4.2 Results

Table 5.4 presents the regression parameters for each coupling architecture. The results reveal a stark bifurcation: only the attention-weighted architecture produced a decreasing slope, while the remaining three architectures all exhibited increasing slopes.

**Table 5.4**

*Regression Parameters for Coupling Architecture Slope Comparison*

| Architecture | Intercept | Slope (β) | R² | 95% CI (β) | Direction |
|:---|:---|:---|:---|:---|:---|
| Hebbian | 1.316 | +0.055 | 0.363 | [+0.049, +0.061] | Increasing |
| Attention | 1.228 | −0.127 | 0.854 | [−0.131, −0.123] | Decreasing |
| Random ER | 1.108 | +0.117 | 0.893 | [+0.114, +0.120] | Increasing |
| None | 1.012 | +0.136 | 0.943 | [+0.133, +0.138] | Increasing |

*Note.* Slopes estimated via OLS regression of log(τ) on log(V), V ∈ {5, 10, 20, 30, 50}. All *p* < .001. Bonferroni-corrected α = 0.00417.

The attention-weighted architecture yielded a slope of −0.127 (R² = .854), the only negative slope among the four conditions. Notably, this value closely approximates the theoretical fleet law slope of −0.159, differing by only 0.032 absolute units. In contrast, Hebbian coupling produced a weakly increasing slope of +0.055 with notably lower explanatory power (R² = .363), suggesting that co-activation-based plasticity does not systematically organize the coupling matrix with respect to vocabulary scale. The two random baselines—Random ER (+0.117) and None (+0.136)—exhibited the strongest increasing slopes and the highest R² values (.893 and .943, respectively), confirming that unstructured coupling produces a consistent positive relationship between τ and V.

[Figure 5.5 about here]

*Figure 5.5. Slope of log(τ) against log(V) for four coupling architectures. Error bars represent 95% confidence intervals across 50 seeded runs. Only attention-weighted coupling (red) produces a decreasing slope, while Hebbian (blue), Random ER (gray), and None (black) all produce increasing slopes.*

### 5.4.3 Pairwise Comparisons

All six pairwise comparisons reached statistical significance at the Bonferroni-corrected threshold, with extraordinarily large effect sizes (Cohen's *d* ranging from −24.92 to +10.36). Table 5.5 presents the full comparison matrix.

**Table 5.5**

*Pairwise Comparisons of Coupling Architecture Slopes*

| Comparison | Δ Slope | Cohen's *d* | *p* (corrected) |
|:---|:---|:---|:---|
| Hebbian vs. Attention | +0.182 | 10.36 | < 10⁻⁷² |
| Attention vs. Random ER | −0.244 | −18.99 | < 10⁻⁹⁷ |
| Attention vs. None | −0.263 | −24.92 | < 10⁻¹⁰⁸ |
| Hebbian vs. Random ER | −0.062 | −2.95 | < 10⁻²⁵ |
| Hebbian vs. None | −0.081 | −5.50 | < 10⁻⁴⁶ |
| Random ER vs. None | −0.019 | −4.77 | < 10⁻⁴¹ |

*Note.* Δ Slope = slope(Architecture 1) − slope(Architecture 2). Positive values indicate Architecture 1 has a steeper increasing slope. Bonferroni-corrected α = 0.00417.

The comparison between attention-weighted and no-coupling baselines is particularly instructive. The attention architecture differed from the None condition by −0.263 slope units (Cohen's *d* = −24.92, *p* < 10⁻¹⁰⁸), constituting the largest effect in the comparison set. This enormous effect size reflects a fundamental qualitative difference: one mechanism decreases with scale while the other increases. The Hebbian–Attention comparison (+0.182, *d* = 10.36, *p* < 10⁻⁷²) is similarly decisive, demonstrating that these two learning-inspired architectures produce categorically different scaling behaviors despite both updating the coupling matrix based on agent activity.

Among the increasing-slope architectures, systematic differences emerged. Hebbian coupling (+0.055) produced a significantly flatter slope than both Random ER (+0.117; Δ = −0.062, *d* = −2.95) and None (+0.136; Δ = −0.081, *d* = −5.50), indicating that Hebbian plasticity partially dampens the positive scaling effect, though it does not reverse it. The difference between Random ER and None (Δ = −0.019, *d* = −4.77, *p* < 10⁻⁴¹) confirms that even modest structural persistence (70% edge retention in ER) measurably moderates the increasing slope.

[Figure 5.6 about here]

*Figure 5.6. Pairwise slope differences with 95% confidence intervals. All six comparisons are significant at Bonferroni-corrected α = 0.00417. The attention architecture diverges from all others with large negative effect sizes.*

### 5.4.4 Mechanism Analysis

The results permit a clear dissociation between two candidate mechanisms for the conservation law's negative slope. Hebbian plasticity, which strengthens connections proportional to co-activation frequency, fails to produce the decreasing slope. The Hebbian coupling matrix accumulates a record of which agent pairs have been simultaneously active, but this accumulated record does not concentrate spectral mass in a way that compensates for increasing vocabulary size. The low R² (.363) of the Hebbian regression further suggests that co-activation statistics are weakly related to vocabulary scale, producing a coupling matrix that is essentially uninformative with respect to the τ–V relationship.

The attention-weighted architecture succeeds where Hebbian plasticity fails because it performs a fundamentally different operation. Rather than strengthening connections based on input correlation, the softmax-over-similarity mechanism concentrates coupling weight on channels whose outputs are already similar. This creates a positive feedback loop: agents with similar outputs receive stronger coupling, which further aligns their outputs on subsequent steps. The momentum blend (70/30) ensures that this concentration proceeds gradually rather than collapsing prematurely, maintaining exploration capacity while progressively organizing the coupling spectrum.

The critical insight is that the conservation law's negative slope reflects *spectral concentration*, not *learning* per se. Any architecture that concentrates spectral mass—routing information preferentially through high-similarity channels—will produce a decreasing τ–V relationship. The attention mechanism is one instantiation of this principle. Hebbian plasticity, despite being a learning rule, does not concentrate spectral mass; it distributes it according to co-activation statistics, which are only weakly related to output similarity. The Random ER and None conditions confirm the baseline: without any concentration mechanism, τ increases with V as expected from the combinatorial expansion of the output space.

The proximity of the attention slope (−0.127) to the theoretical fleet law slope (−0.159) merits emphasis. The attention architecture was not tuned to match the fleet law; the 70/30 momentum blend and softmax temperature were selected on architectural rather than empirical grounds. The close correspondence suggests that the fleet law's negative slope emerges naturally from any mechanism that concentrates spectral mass in proportion to output similarity, and that the attention architecture approximates the efficient concentration rate.

### 5.4.5 Implications

The results of Experiment 3 carry three implications for the theory of collective inference systems. First, the negative slope of the conservation law is not a generic property of adaptive coupling. It emerges specifically from architectures that concentrate spectral mass based on output similarity, ruling out the alternative hypothesis that any form of learning or adaptation suffices. The Hebbian architecture is adaptive—it updates the coupling matrix based on agent activity—yet produces a positive slope indistinguishable in direction from random baselines.

Second, the dissociation between Hebbian and attention mechanisms suggests that the conservation law reflects a *routing* principle rather than a *memory* principle. Hebbian coupling functions as a distributed memory of co-activation patterns. Attention-weighted coupling functions as a dynamic router that directs information flow toward channels with aligned outputs. Only the routing architecture produces the scale-compensating decrease in τ. This distinction has practical consequences for the design of multi-agent systems: effective coordination requires not merely learning which agents are related, but actively concentrating communication bandwidth on agents whose outputs are already converging.

Third, the gradient from None (+0.136) through Random ER (+0.117) to Hebbian (+0.055) to Attention (−0.127) suggests a continuous spectrum of spectral concentration. The conservation law's negative slope may be achievable by any architecture along this spectrum that crosses the zero-slope threshold, with the magnitude of the negative slope increasing as spectral concentration intensifies. This predicts that the fleet law slope of −0.159 could be matched or exceeded by architectures with stronger concentration mechanisms—for example, attention with lower temperature or higher momentum retention.
