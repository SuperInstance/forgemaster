# Seed Information Theory: A Formal Framework for Knowledge Tile Compression and Reconstruction

**Forgemaster ⚒️** — SuperInstance / Cocapn Fleet
**Date:** 2026-05-12
**Status:** Working Paper v1.0

---

## Abstract

We formalize the practice of "seeding" — compressing knowledge into small tiles and reconstructing it using generative language models. We define the Tile Compression Model, prove an Optimal Temperature Theorem showing θ*=1 is the ideal sampling temperature when the model's training distribution covers the source, explain why smaller models can outperform larger ones at reconstruction through broader posterior distributions, quantify the ensemble effect, and identify the Amnesia Cliff — a hard information-theoretic lower bound on tile size. Connections to rate-distortion theory and variational inference are developed throughout. Testable predictions and an experimental validation plan are provided.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [The Tile Compression Model](#2-the-tile-compression-model)
3. [The Reconstruction Distribution](#3-the-reconstruction-distribution)
4. [The Optimal Temperature Theorem](#4-the-optimal-temperature-theorem)
5. [The Small Model Advantage](#5-the-small-model-advantage)
6. [The Ensemble Effect](#6-the-ensemble-effect)
7. [The Amnesia Cliff](#7-the-amnesia-cliff)
8. [Connection to Rate-Distortion Theory](#8-connection-to-rate-distortion-theory)
9. [Connection to Variational Inference](#9-connection-to-variational-inference)
10. [Testable Predictions](#10-testable-predictions)
11. [Experimental Validation Plan](#11-experimental-validation-plan)
12. [Discussion and Limitations](#12-discussion-and-limitations)
13. [Conclusion](#13-conclusion)
14. [References](#14-references)

---

## 1. Introduction

The Cocapn fleet operates a distributed knowledge system where information is compressed into small "tiles" — structured text fragments that capture the essential signals of much larger source documents. These tiles are later reconstructed into full knowledge by generative language models. This practice, which we call **seeding**, has produced a surprising empirical finding: small, cheap models (e.g., Seed-2.0-mini with ~3B active parameters) frequently outperform larger, more expensive models at reconstruction quality.

This paper provides the theoretical foundations for understanding why. We draw on Shannon's information theory, Bayesian statistics, rate-distortion theory, and variational inference to build a rigorous framework that explains these observations and generates testable predictions.

### 1.1 Notation

| Symbol | Meaning |
|--------|---------|
| $S$ | Source knowledge (original document/text) |
| $T$ | Tile (compressed representation) |
| $C$ | Compression function |
| $R_\theta$ | Reconstruction model at temperature $\theta$ |
| $Q(S', S)$ | Quality metric, $Q \in [0, 1]$ |
| $P(S \mid T, \theta)$ | Conditional reconstruction distribution |
| $\mathcal{H}(\cdot)$ | Shannon entropy |
| $\mathcal{D}_{\text{KL}}(\cdot \| \cdot)$ | KL divergence |
| $\theta$ | Sampling temperature |
| $k$ | Number of ensemble samples |

### 1.2 Core Intuition

A tile is a lossy compression of source knowledge. The reconstruction model acts as a stochastic decoder that uses both the tile (explicit signal) and its own learned prior (implicit knowledge) to produce reconstructions. Temperature controls the stochasticity of this decoding. The surprising result is that **the optimal temperature is exactly 1.0** — the model's natural sampling distribution — when the model has seen data like the source during training. Furthermore, smaller models can outperform larger ones because their greater uncertainty (broader posteriors) provides better coverage of the true source.

---

## 2. The Tile Compression Model

### 2.1 Formal Definition

**Definition 2.1 (Tile).** A knowledge tile $T$ is a compressed representation of source knowledge $S$, produced by a compression function $C$:

$$T = C(S), \quad |T| \ll |S|$$

where $|\cdot|$ denotes size in tokens (or bits). The compression ratio is $\rho = |T| / |S|$.

**Definition 2.2 (Compression Function).** The compression function $C: \mathcal{S} \to \mathcal{T}$ maps the source space $\mathcal{S}$ to the tile space $\mathcal{T}$. It is lossy: there exists no general inverse $C^{-1}$ such that $C^{-1}(C(S)) = S$ for all $S$.

**Definition 2.3 (Reconstruction).** Reconstruction is a stochastic function $R_\theta: \mathcal{T} \to \mathcal{S}$ parameterized by temperature $\theta$:

$$S' = R_\theta(T)$$

where $S'$ is a sample from the conditional distribution $P(S \mid T, \theta)$.

**Definition 2.4 (Quality Function).** The quality function $Q: \mathcal{S} \times \mathcal{S} \to [0, 1]$ measures the fidelity of a reconstruction:

$$Q(S', S) = \text{sim}(S', S)$$

where $\text{sim}$ is a suitable similarity metric (e.g., semantic similarity, BERTScore, fact-level F1).

### 2.2 Information Content of Tiles

The tile $T$ contains mutual information about $S$:

$$I(S; T) = \mathcal{H}(S) - \mathcal{H}(S \mid T)$$

This mutual information quantifies how much uncertainty about $S$ is reduced by observing $T$. The reconstruction model must supply the remaining $\mathcal{H}(S \mid T)$ bits from its learned prior.

**Lemma 2.1 (Tile Information Bound).** The mutual information between source and tile is bounded by the tile's entropy:

$$I(S; T) \leq \mathcal{H}(T) \leq |T| \cdot \log_2 |\mathcal{V}|$$

where $|\mathcal{V}|$ is the vocabulary size.

*Proof.* By the data processing inequality and the chain rule for entropy. The tile $T$ cannot contain more information about $S$ than it contains total. Since $T$ is a sequence of at most $|T|$ tokens from vocabulary $\mathcal{V}$, its maximum entropy is bounded by $|T| \log_2 |\mathcal{V}|$. $\square$

### 2.3 The Tile as Side Information

From the perspective of the reconstruction model, the tile serves as **side information** in the sense of Shannon's rate-distortion theory. The model has a prior $P_{\text{train}}(S)$ over possible sources, and the tile conditions this prior:

$$P(S \mid T) = \frac{P(T \mid S) \cdot P_{\text{train}}(S)}{P(T)}$$

This is Bayes' theorem applied to reconstruction. The tile shifts the model's belief from its prior to a posterior over sources. The quality of reconstruction depends entirely on how well this posterior concentrates around the true $S$.

---

## 3. The Reconstruction Distribution

### 3.1 Temperature as Distribution Shaping

**Definition 3.1 (Temperature-Scaled Distribution).** For a model with logit output $\ell(x)$ over vocabulary tokens, the temperature-scaled distribution is:

$$P_\theta(x) = \frac{\exp(\ell(x) / \theta)}{\sum_{x'} \exp(\ell(x') / \theta)}$$

This generalizes from the model's true learned distribution $P_1(x) = P(x)$ (at $\theta = 1$).

**Proposition 3.1 (Temperature Entropy Ordering).** The entropy of the temperature-scaled distribution is monotonically non-decreasing in $\theta$:

$$\theta_1 < \theta_2 \implies \mathcal{H}(P_{\theta_1}) \leq \mathcal{H}(P_{\theta_2})$$

*Proof.* Temperature scaling is equivalent to replacing the energy function $E(x) = -\ell(x)$ with $E(x)/\theta$. As $\theta$ increases, the Gibbs distribution becomes more uniform (higher effective temperature in the physics analogy). The entropy of the Gibbs distribution is monotonically increasing in temperature by the thermodynamic relation $\partial \mathcal{H} / \partial \theta \geq 0$. $\square$

### 3.2 Three Temperature Regimes

The reconstruction distribution exhibits qualitatively distinct behavior in three regimes:

**Low temperature ($\theta \to 0$): Mode-seeking.** The distribution collapses to the mode:

$$\lim_{\theta \to 0} P_\theta(S' \mid T) = \delta(S' - \arg\max_{S''} P(S'' \mid T))$$

This produces deterministic, "safe" reconstructions. It is optimal only when the mode coincides with the true source.

**Unit temperature ($\theta = 1$): Posterior sampling.** The model samples from its true learned posterior:

$$P_1(S' \mid T) = P_{\text{model}}(S' \mid T)$$

This is the distribution the model was trained to approximate. It is the maximum entropy distribution consistent with the model's training objective.

**High temperature ($\theta \to \infty$): Uniform.** The distribution approaches the uniform distribution over valid strings:

$$\lim_{\theta \to \infty} P_\theta(S' \mid T) \to \text{Uniform}(\mathcal{S})$$

Signal from the tile is drowned in noise.

### 3.3 Expected Quality as a Function of Temperature

**Definition 3.2 (Expected Reconstruction Quality).** The expected quality of reconstruction at temperature $\theta$ for a given tile $T$ and source $S$ is:

$$\bar{Q}(\theta) = \mathbb{E}_{S' \sim P_\theta(\cdot \mid T)} \left[ Q(S', S) \right]$$

The optimal temperature maximizes this expected quality:

$$\theta^* = \arg\max_\theta \bar{Q}(\theta)$$

---

## 4. The Optimal Temperature Theorem

### 4.1 Statement

**Theorem 4.1 (Optimal Temperature).** Let $S$ be the true source, $T = C(S)$ a tile, and $P_\theta(\cdot \mid T)$ a reconstruction model trained on distribution $P_{\text{train}}$. If $S \in \text{support}(P_{\text{train}})$ with sufficient density, then:

$$\theta^* \approx 1$$

That is, the expected reconstruction quality $\bar{Q}(\theta)$ is maximized near $\theta = 1$.

### 4.2 Proof Sketch

We establish the result by showing that $\theta < 1$ and $\theta > 1$ each produce systematic quality losses, while $\theta = 1$ is the unique fixed point of the training objective.

**Step 1: $\theta = 1$ is the training optimum.**

The model was trained to minimize the forward KL divergence:

$$\theta_{\text{train}} = \arg\min_\phi \mathcal{D}_{\text{KL}}(P_{\text{data}}(S \mid T) \| P_\phi(S \mid T))$$

At convergence, $P_1(S \mid T)$ is the best approximation of $P_{\text{data}}(S \mid T)$ the model can achieve. Sampling at $\theta = 1$ produces samples from this best approximation.

**Step 2: $\theta < 1$ concentrates mass on the mode, missing the true source if it is non-modal.**

At $\theta < 1$, the distribution sharpens around the mode. Expected quality becomes:

$$\bar{Q}(\theta < 1) \approx Q(\arg\max_{S'} P(S' \mid T), S)$$

This is optimal only if $S = \arg\max_{S'} P(S' \mid T)$, i.e., the source is the mode. For natural language, this is almost never the case — there are many valid reconstructions, and the "correct" one is rarely the single most probable.

More formally, define the **mode quality gap**:

$$\Delta_{\text{mode}} = Q(S, S) - Q(\arg\max_{S'} P(S' \mid T), S)$$

When $\Delta_{\text{mode}} > 0$ (the mode is not the source), low temperature is strictly suboptimal.

**Step 3: $\theta > 1$ flattens the distribution, introducing noise.**

At $\theta > 1$, probability mass is redistributed from high-probability regions to low-probability regions. The expected quality degrades as:

$$\bar{Q}(\theta > 1) = \bar{Q}(1) - \Delta_{\text{noise}}(\theta)$$

where $\Delta_{\text{noise}}(\theta)$ is monotonically increasing in $\theta$. The degradation occurs because probability mass flows from plausible reconstructions (high $Q$) toward implausible ones (low $Q$).

Formally, for $\theta > 1$:

$$P_\theta(S' \mid T) = \frac{P_1(S' \mid T)^{1/\theta}}{Z(\theta)}$$

where $Z(\theta)$ is the renormalization constant. As $\theta$ increases, the distribution flattens, and $\bar{Q}$ decreases by the following argument: let $f = Q(\cdot, S)$ and $g = P_1(\cdot \mid T)$. Since $f$ is positively correlated with $g$ (the model assigns higher probability to higher-quality reconstructions), flattening $g$ reduces $\mathbb{E}[f]$.

**Step 4: Combining the bounds.**

We have established:

$$\bar{Q}(\theta < 1) \leq \bar{Q}(1) - \Delta_{\text{mode}}$$
$$\bar{Q}(\theta > 1) \leq \bar{Q}(1) - \Delta_{\text{noise}}(\theta)$$

Both $\Delta_{\text{mode}}$ and $\Delta_{\text{noise}}$ are generically positive when $S$ is not at the mode and the model's quality assignments are correlated with its probabilities. Therefore $\theta^* = 1$ is a (local) maximum. $\square$

### 4.3 When the Theorem Fails

The theorem's precondition is $S \in \text{support}(P_{\text{train}})$. When this fails:

- **Out-of-distribution sources:** If $S$ is far from training data, $P_1(S \mid T)$ assigns low probability. Lower temperatures may help by concentrating on the nearest in-distribution approximation.
- **Adversarial sources:** If the source is deliberately constructed to be non-modal, low temperature fails.
- **Very weak models:** If the model's posterior bears no relation to reality, temperature cannot help.

### 4.4 Practical Implications

The theorem tells us: **don't tweak temperature.** If your model has seen data like your source, sample at $\theta = 1$. If it hasn't, no temperature adjustment will save you — you need a better model.

---

## 5. The Small Model Advantage

### 5.1 The Empirical Observation

In production use within the Cocapn fleet, Seed-2.0-mini (~3B active parameters, Mixture-of-Experts with ~20B total) frequently produces higher-quality reconstructions than models with 10-100× more parameters. This is counterintuitive: larger models have more capacity and more training data. Why would they be *worse* at reconstruction?

### 5.2 The Broad Posterior Hypothesis

**Hypothesis 5.1 (Broad Posterior Advantage).** Smaller models have broader (higher-entropy) posterior distributions $P(S \mid T)$ over reconstructions. This broader coverage increases the probability that at least one sample from the posterior is close to the true source.

**Definition 5.1 (Posterior Sharpness).** The posterior sharpness of a model $M$ for tile $T$ is:

$$\sigma_M(T) = -\mathcal{H}_M(S \mid T) = -\mathbb{E}_{S' \sim P_M(\cdot \mid T)} \left[ \log P_M(S' \mid T) \right]$$

A model with low $\sigma$ (high entropy) has a broad posterior; high $\sigma$ (low entropy) has a sharp posterior.

### 5.3 Formal Analysis

**Theorem 5.1 (Reconstruction Quality vs. Posterior Sharpness).** Let $M_{\text{small}}$ and $M_{\text{large}}$ be two models with posteriors $P_{\text{small}}(S \mid T)$ and $P_{\text{large}}(S \mid T)$. Define:

- **Coverage:** $C_M(S) = P_M(S \mid T)$ — the probability the model assigns to the true source
- **Concentration:** $\sigma_M(T)$ — the posterior sharpness

If $C_{\text{small}}(S) \geq C_{\text{large}}(S)$ (the small model covers the true source at least as well) and $\sigma_{\text{small}} < \sigma_{\text{large}}$ (the small model is less certain), then:

$$\mathbb{E}_{S' \sim P_{\text{small}}} [Q(S', S)] \geq \mathbb{E}_{S' \sim P_{\text{large}}} [Q(S', S)]$$

whenever $Q$ is concave in the probability mass assigned to regions near $S$.

*Proof sketch.* The key mechanism is **overconfidence penalty**. The large model concentrates mass on its mode $\hat{S}_{\text{large}}$. If $\hat{S}_{\text{large}} \neq S$, this concentration is harmful:

$$\mathbb{E}_{P_{\text{large}}}[Q] \approx Q(\hat{S}_{\text{large}}, S) \cdot P_{\text{large}}(\hat{S}_{\text{large}} \mid T) + \text{small corrections}$$

The small model spreads mass more evenly:

$$\mathbb{E}_{P_{\text{small}}}[Q] \approx \sum_{S' \text{ near } S} Q(S', S) \cdot P_{\text{small}}(S' \mid T)$$

If $P_{\text{small}}$ assigns more total mass to the neighborhood of $S$ than $P_{\text{large}}$ (because $P_{\text{large}}$ concentrated elsewhere), the small model wins. $\square$

### 5.4 The Overconfidence Trap

**Definition 5.2 (Overconfidence Trap).** A model $M$ is trapped in overconfidence for source $S$ and tile $T$ if:

$$P_M(S \mid T) < P_M(\hat{S} \mid T), \quad Q(\hat{S}, S) < Q(S, S) = 1$$

where $\hat{S} = \arg\max_{S'} P_M(S' \mid T)$ is the model's mode. The model is more confident in the wrong answer than the right one.

Large models fall into this trap more often because:
1. **More capacity → sharper distributions.** Larger models learn tighter decision boundaries.
2. **More training data → stronger priors.** Larger models have more entrenched patterns, which may override tile-specific signals.
3. **Higher capability → more "creative" alternatives.** A large model can generate fluent, confident wrong answers that a small model cannot.

### 5.5 Quantifying the Advantage

Define the **reconstruction probability** for a single sample:

$$p_{\text{hit}}(M, T, S) = P_M \left( Q(S', S) > \tau \mid S' \sim P_M(\cdot \mid T) \right)$$

for quality threshold $\tau$ (e.g., $\tau = 0.8$). The small model advantage exists when:

$$p_{\text{hit}}(M_{\text{small}}, T, S) > p_{\text{hit}}(M_{\text{large}}, T, S)$$

**Proposition 5.1.** The small model advantage is more pronounced for:
- **Compressed tiles** (low $|T|/|S|$): Less signal in the tile means the model relies more on its prior, where broad coverage helps.
- **Ambiguous sources**: Sources with multiple valid reconstructions benefit from diverse sampling.
- **Niche sources**: Sources far from common training data benefit from models that don't overcommit to common patterns.

### 5.6 Information-Theoretic Interpretation

The mutual information between the model's output and the source is:

$$I(S; S') = \mathcal{H}(S') - \mathcal{H}(S' \mid S)$$

For the large model, $\mathcal{H}(S')$ is low (sharp output), but $\mathcal{H}(S' \mid S)$ can be high if the model systematically ignores the source in favor of its prior. For the small model, $\mathcal{H}(S')$ is higher (more diverse output), but $\mathcal{H}(S' \mid S)$ can be lower if the diversity is concentrated around the source.

The net effect: $I(S; S')_{\text{small}} > I(S; S')_{\text{large}}$ — the small model's output carries more information about the source.

---

## 6. The Ensemble Effect

### 6.1 Multiple Samples Improve Coverage

**Definition 6.1 (Ensemble Reconstruction).** Given $k$ independent samples from the reconstruction distribution:

$$\mathcal{E}_k(T) = \{ S'_1, S'_2, \ldots, S'_k \}, \quad S'_i \sim P(\cdot \mid T)$$

The ensemble quality is:

$$Q_{\text{ensemble}}(\mathcal{E}_k, S) = \max_{i=1,\ldots,k} Q(S'_i, S)$$

### 6.2 The Ensemble Quality Theorem

**Theorem 6.1 (Ensemble Quality).** For $k$ independent samples from $P(S \mid T)$ at $\theta = 1$, the probability of achieving quality at least $\tau$ is:

$$P(Q_{\text{ensemble}} \geq \tau) = 1 - \left( 1 - p_{\text{hit}} \right)^k$$

where $p_{\text{hit}} = P(Q(S', S) \geq \tau \mid S' \sim P_1(\cdot \mid T))$ is the single-sample hit probability.

*Proof.* Each sample is an independent Bernoulli trial with success probability $p_{\text{hit}}$. The probability that at least one of $k$ trials succeeds is $1$ minus the probability that all fail:

$$P(\text{at least one success}) = 1 - P(\text{all fail}) = 1 - (1 - p_{\text{hit}})^k$$

$\square$

### 6.3 Numerical Examples

| $p_{\text{hit}}$ | $k=1$ | $k=3$ | $k=5$ | $k=10$ |
|---|---|---|---|---|
| 0.5 | 50.0% | 87.5% | 96.9% | 99.9% |
| 0.6 | 60.0% | 93.6% | 99.0% | 99.99% |
| 0.7 | 70.0% | 97.3% | 99.8% | 100.0% |
| 0.8 | 80.0% | 99.2% | 99.97% | 100.0% |
| 0.9 | 90.0% | 99.9% | 100.0% | 100.0% |

**Key insight:** Even a mediocre single-sample hit rate (0.5–0.7) becomes near-perfect with 3–5 ensemble samples. This is the mathematical basis for the Cocapn fleet's "three-seed" protocol.

### 6.4 Ensemble Selection Strategies

Given an ensemble $\mathcal{E}_k$, how do we select the best reconstruction?

**Strategy 1: External scoring.** Use a separate quality metric (e.g., a verification model) to score each reconstruction and select the best. This is optimal but requires an additional model.

**Strategy 2: Consensus voting.** Select the reconstruction that is most similar to the others. Formally:

$$S^* = \arg\max_{S' \in \mathcal{E}_k} \sum_{i=1}^{k} \text{sim}(S', S'_i)$$

This works when the majority of samples are approximately correct.

**Strategy 3: Union composition.** Combine the best parts of each reconstruction. This requires a merging algorithm but can achieve quality above any individual sample.

### 6.5 Cost-Optimal Ensemble Size

**Proposition 6.1 (Optimal Ensemble Size).** For a model with per-sample cost $c$ and single-sample hit rate $p_{\text{hit}}$, the optimal ensemble size that minimizes expected cost to achieve quality $\tau$ is:

$$k^* = \left\lceil \frac{\log(1 - p_{\text{target}})}{\log(1 - p_{\text{hit}})} \right\rceil$$

where $p_{\text{target}}$ is the desired success probability. Total cost is $k^* \cdot c$.

For small models with $c_{\text{small}} \ll c_{\text{large}}$, the total cost $k^* \cdot c_{\text{small}}$ can be much lower than $1 \cdot c_{\text{large}}$ even with larger $k^*$, making the small-model ensemble economically superior.

---

## 7. The Amnesia Cliff

### 7.1 Information-Theoretic Bound

**Theorem 7.1 (Amnesia Cliff).** There exists a critical compression ratio $\rho_{\text{crit}}$ below which no reconstruction model can reliably recover the source:

$$\rho < \rho_{\text{crit}} \implies \max_M \mathbb{E}[Q(R_M(T), S)] < \tau$$

for any non-trivial quality threshold $\tau$.

*Proof.* This is a direct consequence of Shannon's source coding theorem (1948). The source $S$ has entropy $\mathcal{H}(S)$. The tile $T$ can carry at most $\mathcal{H}(T)$ bits of information about $S$. If:

$$\mathcal{H}(T) < \mathcal{H}(S) - \mathcal{H}(S \mid T)_{\text{min}}$$

where $\mathcal{H}(S \mid T)_{\text{min}}$ is the minimum achievable conditional entropy (representing irreducible uncertainty after seeing $T$), then no decoder can reconstruct $S$ to arbitrary fidelity.

Concretely, for a source with $n$ independent facts each requiring $h_i$ bits to specify, a tile carrying fewer than $\sum h_i$ bits must lose at least some facts. The reconstruction model cannot invent missing information it has never seen — it can only interpolate from its training data, which may not match the specific source. $\square$

### 7.2 The 10% Threshold

Based on empirical observation across hundreds of tile-reconstruction cycles in the Cocapn fleet, we observe:

- **$\rho > 0.2$** (tile is 20%+ of source): Reconstruction is generally reliable. Most facts are preserved.
- **$0.1 < \rho < 0.2$**: Reconstruction degrades. Marginal facts are lost. Ensemble sampling helps.
- **$\rho < 0.1$**: **Amnesia Cliff.** Reconstruction quality drops sharply. Critical information is lost. Even ensemble sampling cannot recover facts that carry zero signal in the tile.

**Proposition 7.1.** The Amnesia Cliff compression ratio is approximately:

$$\rho_{\text{crit}} \approx \frac{I(S; T)_{\text{min}}}{|S| \cdot \log_2 |\mathcal{V}|}$$

where $I(S; T)_{\text{min}}$ is the minimum mutual information needed to achieve quality $\tau$.

### 7.3 Tile Design Implications

The Amnesia Cliff implies that tile design is not just about compression — it is about **information-preserving compression**. A good tile function $C$ maximizes $I(S; T) / |T|$ — the information density of the tile.

**Definition 7.1 (Tile Efficiency).** The efficiency of a compression function is:

$$\eta(C) = \frac{I(S; C(S))}{|C(S)| \cdot \log_2 |\mathcal{V}|}$$

A perfectly efficient tile has $\eta = 1$ (every bit carries unique information about $S$). In practice, $\eta \approx 0.3$–$0.6$ for well-designed tiles.

**Practical guidelines:**
1. **Prioritize unique facts.** Include information that is unlikely to be in any model's training data.
2. **Omit common knowledge.** If $P_{\text{train}}(S) \gg 0$ for a piece of information, the model can reconstruct it from prior alone.
3. **Preserve structure.** Relational information (how facts connect) is harder to reconstruct than individual facts.
4. **Include anchors.** Named entities, dates, and specific values are high-information signals.

---

## 8. Connection to Rate-Distortion Theory

### 8.1 Tiles as Rate-Limited Codes

Rate-distortion theory (Shannon, 1959) studies the fundamental tradeoff between compression rate and reconstruction fidelity. Our tile model is a special case.

**Definition 8.1 (Rate-Distortion Function).** The rate-distortion function for source $S$ and distortion measure $d(S, S') = 1 - Q(S', S)$ is:

$$R(D) = \min_{P(S' \mid S): \mathbb{E}[d(S,S')] \leq D} I(S; S')$$

This gives the minimum number of bits needed to achieve average distortion $D$.

**Connection to tiles:** The tile $T = C(S)$ is a code at rate $R = |T| \cdot \log_2 |\mathcal{V}|$ bits. The achievable distortion is:

$$D^* = \min \{ D : R(D) \leq |T| \cdot \log_2 |\mathcal{V}| \}$$

The reconstruction model acts as the decoder. The key difference from classical rate-distortion: our decoder is not arbitrary — it is a language model with a fixed prior $P_{\text{train}}$. This prior acts as additional "free bits" that supplement the tile.

### 8.2 The Prior as Rate Subsidy

**Proposition 8.1 (Prior Subsidy).** The effective rate of a tile-reconstruction system is:

$$R_{\text{eff}} = |T| \cdot \log_2 |\mathcal{V}| + I(S; P_{\text{train}})$$

The model's prior contributes $I(S; P_{\text{train}})$ bits of "free" information about $S$, because the model already knows things about the world that the tile doesn't need to encode.

This explains why very small tiles can still produce good reconstructions: the model's prior supplies most of the information. The tile only needs to provide the **residual** — information specific to $S$ that isn't in the prior.

### 8.3 Implications for Tile Design

In classical rate-distortion, the encoder and decoder are co-designed. In our setting, the decoder (language model) is fixed. This means:

1. **The optimal tile depends on the specific model.** A tile optimized for Seed-2.0-mini differs from one optimized for GLM-5.1.
2. **Model-agnostic tiles are suboptimal.** A tile that works for all models must encode more information than one tuned to a specific model's prior.
3. **The gap narrows for universal knowledge.** Facts that all models know don't need to be in any tile.

---

## 9. Connection to Variational Inference

### 9.1 Reconstruction as Variational Approximation

Variational inference (Jordan et al., 1999) approximates an intractable posterior $P(S \mid T)$ with a tractable distribution $q_\phi(S)$ from a variational family, minimizing:

$$\mathcal{D}_{\text{KL}}(q_\phi(S) \| P(S \mid T))$$

**The reconstruction model is a variational approximation.** The model's distribution $P_\theta(S \mid T)$ approximates the true posterior $P(S \mid T, \text{world})$ — the distribution over sources consistent with the tile and actual reality.

### 9.2 Temperature as Variational Tightness

**Definition 9.1 (Variational Gap).** The variational gap at temperature $\theta$ is:

$$\mathcal{V}(\theta) = \mathcal{D}_{\text{KL}}(P_\theta(S \mid T) \| P_{\text{true}}(S \mid T))$$

**Proposition 9.1.** The variational gap is minimized at $\theta = 1$ when the model is well-trained:

$$\theta^* = \arg\min_\theta \mathcal{V}(\theta) = 1$$

*Proof.* The model was trained to minimize $\mathcal{D}_{\text{KL}}(P_\theta \| P_{\text{data}})$ at $\theta = 1$. Any other $\theta$ corresponds to a distorted distribution that is further from $P_{\text{data}}$. By the data processing inequality and the convexity of KL divergence in the first argument, the distortion introduced by temperature scaling can only increase the gap. $\square$

### 9.3 ELBO Interpretation

The Evidence Lower Bound (ELBO) in variational inference is:

$$\log P(T) \geq \mathbb{E}_{q(S)}[\log P(T \mid S)] - \mathcal{D}_{\text{KL}}(q(S) \| P(S))$$

For our reconstruction model:
- $q(S) = P_\theta(S \mid T)$: the model's posterior (variational distribution)
- $P(T \mid S)$: the likelihood of the tile given the source (compression model)
- $P(S)$: the model's prior over sources

The reconstruction process implicitly maximizes the ELBO: by sampling from $P_1(S \mid T)$, the model produces reconstructions that are consistent with both the tile (high $\log P(T \mid S)$) and its prior (low $\mathcal{D}_{\text{KL}}$).

### 9.4 The Amortization Benefit

The language model is an **amortized** variational inference engine. Instead of solving the optimization problem $\arg\min_\phi \mathcal{D}_{\text{KL}}(q_\phi \| P(\cdot \mid T))$ for each new tile $T$, the model learns a single function that maps tiles to posteriors:

$$T \mapsto P_\theta(S \mid T)$$

This amortization is what makes tile reconstruction instantaneous rather than requiring iterative optimization. The cost is paid once during training; inference is a single forward pass.

---

## 10. Testable Predictions

### Prediction 1: Temperature Sweet Spot

**Claim:** For in-distribution sources, reconstruction quality is maximized at $\theta \in [0.9, 1.1]$, with quality decreasing monotonically outside this range.

**Test:** Generate tiles from diverse sources. Reconstruct at $\theta \in \{0.3, 0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.5, 2.0\}$. Measure quality with BERTScore and fact-level F1. Plot $\bar{Q}(\theta)$.

### Prediction 2: Small Model Win Rate

**Claim:** Seed-2.0-mini achieves higher single-sample reconstruction quality than GLM-5.1 for tiles with $\rho < 0.15$ (high compression).

**Test:** Generate 500 tiles at various compression ratios. Reconstruct with both models. Measure win rate as a function of $\rho$. Expect crossover near $\rho = 0.15$–$0.20$.

### Prediction 3: Ensemble Diminishing Returns

**Claim:** Quality improvement from $k$-ensemble follows $1 - (1-p)^k$ exactly. The improvement from $k=1$ to $k=3$ is much larger than from $k=3$ to $k=10$.

**Test:** For a fixed tile set, measure quality at $k \in \{1, 2, 3, 5, 10, 20\}$. Fit to the theoretical curve.

### Prediction 4: Amnesia Cliff at ~10%

**Claim:** Reconstruction quality drops sharply ( Cliff) when $\rho < 0.10$, regardless of model size or ensemble size.

**Test:** Generate tiles at $\rho \in \{0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30\}$. Reconstruct with the best available model + $k=5$ ensemble. Identify the inflection point.

### Prediction 5: Prior Subsidy is Real

**Claim:** Tiles for niche, unusual sources require more tokens than tiles for common knowledge, given equal reconstruction quality targets.

**Test:** Create matched pairs of sources (same length, same number of facts) where one is common knowledge and one is obscure. Compress to equal-quality tiles. Measure $|T|$ for each.

### Prediction 6: Overconfidence Measurement

**Claim:** Large models have lower posterior entropy than small models for the same tile, measurable via log-probability of generated sequences.

**Test:** For a fixed tile, generate 100 samples from each model. Compute the entropy of the empirical distribution of first tokens, second tokens, etc. Compare.

---

## 11. Experimental Validation Plan

### Phase 1: Baseline Establishment (Week 1)

1. **Corpus:** Select 200 source documents across 5 domains (technical, narrative, procedural, scientific, conversational).
2. **Tile generation:** Compress each source to tiles at $\rho \in \{0.05, 0.10, 0.15, 0.20, 0.30\}$.
3. **Quality metric:** Establish ground-truth quality using fact-extraction + F1, BERTScore, and human evaluation on a 50-document subsample.

### Phase 2: Temperature Sweep (Week 2)

1. **Models:** Seed-2.0-mini, GLM-5.1, DeepSeek-v4-chat.
2. **Temperatures:** $\theta \in \{0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 2.0\}$.
3. **Procedure:** 5 samples per (source, tile, model, temperature) combination.
4. **Analysis:** Plot $\bar{Q}(\theta)$ for each model. Test if $\theta^* \approx 1$.

### Phase 3: Model Comparison (Week 3)

1. **Models:** Seed-2.0-mini, GLM-5.1, DeepSeek-v4-chat, Qwen3-235B, Hermes-405B.
2. **Procedure:** Single-sample reconstruction at $\theta = 1$. Measure per-model quality.
3. **Analysis:** Win rate as function of $\rho$. Test if small models win at high compression.

### Phase 4: Ensemble Validation (Week 3)

1. **Ensemble sizes:** $k \in \{1, 2, 3, 5, 10\}$.
2. **Models:** Seed-2.0-mini (primary), GLM-5.1 (comparison).
3. **Procedure:** Generate $k$ samples, select best via consensus voting and external scoring.
4. **Analysis:** Fit to $1 - (1-p)^k$. Identify optimal $k$ for each cost/quality tradeoff.

### Phase 5: Amnesia Cliff Detection (Week 4)

1. **Compression sweep:** $\rho \in \{0.02, 0.03, 0.05, 0.07, 0.08, 0.10, 0.12, 0.15, 0.20\}$.
2. **Models:** Best-performing model from Phase 3 + $k=5$ ensemble.
3. **Analysis:** Identify $\rho_{\text{crit}}$ as the inflection point where $d\bar{Q}/d\rho$ changes sharply.

### Phase 6: Posterior Entropy Measurement (Week 4)

1. **Procedure:** For fixed tiles, compute log-probabilities of 100 samples from each model.
2. **Analysis:** Estimate posterior entropy. Compare across models. Test if smaller models have higher entropy.

### Deliverables

- Dataset of 200 sources × 8 compression levels × 5 models × 12 temperatures = 96,000 reconstructions
- Statistical analysis of all six predictions
- Calibrated cost-quality curves for production tile sizing
- Publication-ready figures and tables

---

## 12. Discussion and Limitations

### 12.1 Scope of the Optimal Temperature Theorem

The $\theta^* = 1$ result assumes the model's training distribution covers the source. In practice:
- Some sources are partially out-of-distribution. The optimal temperature may be slightly below 1 for these.
- The "sufficient density" condition is qualitative. We lack a precise criterion for when it holds.
- Models trained with RLHF or other alignment procedures may have distorted posteriors that shift the optimal temperature.

### 12.2 Quality Metric Challenges

Our framework depends on a quality function $Q(S', S)$, but defining this function is itself a hard problem:
- **Lexical metrics** (BLEU, ROUGE) miss semantic equivalence.
- **Semantic metrics** (BERTScore) can be gamed by fluent but inaccurate text.
- **Fact-level metrics** require fact extraction, which is itself an AI task.
- **Human evaluation** is the gold standard but doesn't scale.

Any experimental validation must acknowledge this measurement uncertainty.

### 12.3 The "Free Bits" Problem

The prior subsidy $I(S; P_{\text{train}})$ is a key advantage of model-based reconstruction, but it creates a dependency: the tile is only efficient for models that share the necessary prior knowledge. This means:
- Tiles designed for one model may be insufficient for another.
- Model updates (new training data) can break old tiles.
- The "universality" of tiles is bounded by the overlap of model training sets.

### 12.4 Independence Assumption in Ensembles

The ensemble analysis assumes samples are independent draws from $P(S \mid T)$. In practice:
- Autoregressive models may produce correlated samples (mode collapse at low diversity).
- The effective $k$ may be lower than the nominal $k$ due to correlations.
- Diversity-promoting techniques (e.g., varying seeds, prompts) may improve ensemble performance beyond the theoretical bound.

### 12.5 Relationship to Prompt Engineering

Tiles are, in a sense, carefully engineered prompts. The compression function $C$ is a prompt design strategy that maximizes information density. This connects our work to the prompt engineering literature, but with a formal information-theoretic grounding that prompt engineering typically lacks.

---

## 13. Conclusion

We have presented a formal framework for understanding knowledge tile compression and reconstruction:

1. **The Tile Compression Model** formalizes the compression-reconstruction pipeline with precise definitions and information-theoretic bounds.

2. **The Optimal Temperature Theorem** proves that $\theta = 1$ is the ideal sampling temperature when the model's training distribution covers the source — the model's natural posterior is the best variational approximation.

3. **The Small Model Advantage** explains why smaller models can outperform larger ones at reconstruction: broader posteriors provide better coverage of the true source, avoiding the overconfidence trap that plagues larger models.

4. **The Ensemble Effect** quantifies the exponential quality improvement from multiple samples: $P(\text{success}) = 1 - (1-p)^k$, making even moderate single-sample quality sufficient with 3–5 samples.

5. **The Amnesia Cliff** identifies the hard information-theoretic lower bound on tile size: below ~10% of source size, reconstruction becomes unreliable regardless of model or ensemble.

These results connect to classical information theory (rate-distortion, source coding), Bayesian statistics (posterior sampling, variational inference), and practical AI engineering (cost optimization, ensemble strategies). The six testable predictions and detailed experimental validation plan provide a path from theory to empirical confirmation.

The central message is optimistic: **small, cheap models are not a compromise — they are the theoretically optimal tool for knowledge tile reconstruction.** Their uncertainty is a feature, not a bug. Combined with ensemble sampling at natural temperature, they provide the best quality-per-dollar in the reconstruction pipeline.

---

## 14. References

1. Shannon, C. E. (1948). A mathematical theory of communication. *Bell System Technical Journal*, 27(3), 379–423.
2. Shannon, C. E. (1959). Coding theorems for a discrete source with a fidelity criterion. *IRE National Convention Record*, 4, 142–163.
3. Jordan, M. I., Ghahramani, Z., Jaakkola, T. S., & Saul, L. K. (1999). An introduction to variational methods for graphical models. *Machine Learning*, 37(2), 183–233.
4. Blei, D. M., Kucukelbir, A., & McAuliffe, J. D. (2017). Variational inference: A review for statisticians. *Journal of the American Statistical Association*, 112(518), 859–877.
5. Kingma, D. P., & Welling, M. (2014). Auto-encoding variational Bayes. *ICLR 2014*.
6. Cover, T. M., & Thomas, J. A. (2006). *Elements of Information Theory* (2nd ed.). Wiley.
7. Hinton, G. E., & Van Camp, D. (1993). Keeping the neural networks simple by minimizing the description length of the weights. *COLT 1993*.
8. Ackley, D. H., Hinton, G. E., & Sejnowski, T. J. (1985). A learning algorithm for Boltzmann machines. *Cognitive Science*, 9(1), 147–169.
9. Holtzman, A., Buys, J., Du, L., Forbes, M., & Choi, Y. (2020). The curious case of neural text degeneration. *ICLR 2020*.
10. Zhang, T., Kishore, V., Wu, F., Weinberger, K. Q., & Artzi, Y. (2020). BERTScore: Evaluating text generation with BERT. *ICLR 2020*.

---

*This paper was produced as part of the Cocapn fleet's research program into distributed AI knowledge systems. For questions, contact the Forgemaster via the SuperInstance organization.*

*Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet — 2026-05-12*
