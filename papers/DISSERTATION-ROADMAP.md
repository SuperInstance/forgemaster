# Dissertation Roadmap: A Conservation Law in Cognitive Networks

**γ + H = C − α · ln(V)**

**Author:** Forgemaster ⚒️, PLATO Fleet Laboratory
**Date:** 2026-05-15
**Status:** Living document — research plan through completion

---

## Chapter 1: Introduction

### 1.1 The Observation

For symmetric coupling matrices C of dimension V, the sum of normalized algebraic connectivity γ and spectral entropy H obeys an empirical conservation law:

$$\gamma + H = 1.283 - 0.159 \cdot \ln V, \quad R^2 = 0.9602$$

across 35,000 Monte Carlo samples spanning V ∈ {5, 10, 20, 30, 50, 100, 200}. This is not a theorem derivable from random matrix theory — it is an empirical regularity that holds for specific matrix ensembles (Hebbian-trained with eigenvalue concentration) and fails for others (dense random matrices show the *opposite* slope). The law expresses a fundamental trade-off: connectivity and informational diversity share a fixed budget that contracts logarithmically with network size.

### 1.2 Why It Matters

- **Fleet health monitoring.** Deviation from the predicted γ+H signals structural anomaly — preferential attachment (γ+H too high) or anomalous sparsity (γ+H too low). The ±2σ band at V=30 is ±0.200, giving a calibrated diagnostic.
- **Fault detection.** The conservation law is orthogonal to behavioral alignment (GL(9), r = −0.179) and does not predict accuracy (MAE 0.048 vs. 0.045 baseline). It is an independent structural axis for multi-signal health monitoring.
- **Recovery from shock.** Hybrid recovery (Hebbian alignment + conservation accuracy restoration) recovers content accuracy in 1 round and alignment in ~14 rounds, outperforming pure Hebbian (circular, 0% content recovery) and quarantine (180+ rounds).
- **Scaling theory.** The law predicts "cognitive heat death" — as V → ∞, the spectral budget contracts without bound, placing a fundamental constraint on associative cognitive architectures.

### 1.3 What We Don't Know

1. **Can the slope constant (−0.159) be derived from Hebbian parameters?** The mechanism (eigenvalue concentration) is identified, but no closed-form prediction exists.
2. **Does the law hold at real fleet scale (V > 200)?** Study 67 shows a plateau at V > 50, but this was simulated — not tested on live systems.
3. **Does the law generalize beyond Hebbian coupling?** Only matrices with top-1 eigenvalue ratio > 0.20 show the decreasing slope. How many natural systems exhibit this?
4. **Is the conservation law substrate-independent?** Do biological neural networks, social networks, or swarm systems obey it?
5. **What is the correct recovery protocol?** Study 73 overturned Study 64; Study 74 exposed Hebbian circularity; the hybrid strategy is promising but validated only in simulation.

### 1.4 Dissertation Contributions (Numbered Claims)

| ID | Claim | Status | Evidence |
|----|-------|--------|----------|
| C1 | First observation of γ+H conservation law in agent coupling matrices | **Empirical** | 35,000 MC samples, R² = 0.9602 |
| C2 | Mechanism: eigenvalue concentration from Hebbian + decay produces the decreasing slope | **Supported** | Study 65: 8 regimes, discriminant = top-1 ratio > 0.20 |
| C3 | Two-regime model: log-linear for V ≤ 50, plateau for V > 50 | **Tentative** | Study 67: R² drops below 0.90 at V > 75 |
| C4 | The law is ensemble-dependent, not derivable from RMT alone | **Proven** | Study 63B: dense random gives opposite slope |
| C5 | The law is orthogonal to behavioral prediction (accuracy, GL(9) alignment) | **Proven** | Studies 54 (r = −0.179), 57 (MAE 0.048) |
| C6 | Hybrid recovery (Hebbian + conservation) outperforms single-strategy approaches | **Tentative** | Studies 73–74: simulation only, no live validation |
| C7 | Fault detection coverage is weak: 76.2% of faults missed by triple-detector system | **Proven** | Study 75: 1,000 events, structural faults 97% missed |
| C8 | GL(9) consensus detection is non-functional (zero information gain) | **Proven** | Studies 72, 75: recall = 0.000 across all conditions |

---

## Chapter 2: Background & Related Work

### 2.1 Spectral Graph Theory
- **Fiedler eigenvalue** (λ₁ of graph Laplacian) as algebraic connectivity (Fiedler, 1973)
- **Cheeger inequality** relating spectral gap to graph conductance
- **Normalized Laplacian** and its eigenvalue interpretation
- **Spectral clustering** (Ng, Jordan, Weiss, 2001) — eigenvectors of Laplacian for partitioning
- Relevance: γ is derived from the Fiedler eigenvalue; the conservation law is fundamentally a spectral property

### 2.2 Random Matrix Theory
- **Wigner semicircle law** — bulk eigenvalue distribution for symmetric random matrices
- **Marchenko-Pastur law** — singular value distribution for rectangular matrices
- **Spiked random matrix model** (Baik, Ben Arous, Péché, 2005) — rank-1 perturbation of Wigner matrices; phase transition in largest eigenvalue
- **Perron-Frobenius theorem** — dominant eigenvalue of positive matrices
- Relevance: Study 63B showed the ln(V) functional form is RMT-derived but the decreasing slope is not. Spiked RMT is the leading candidate for connecting Hebbian dynamics to the observed slope.

### 2.3 Network Thermodynamics
- **Free energy principle** (Friston, 2010) — systems minimize variational free energy
- **Entropy production** in nonequilibrium systems
- **Carnot efficiency** as an upper bound on extractable work
- Relevance: The conservation law admits a thermodynamic interpretation (§3 of v3 paper) — γ+H as a Carnot-like bound on cognitive networks

### 2.4 Hebbian Learning and Eigenvalue Dynamics
- **Hebbian plasticity** (Hebb, 1949) and STDP (Song et al., 2000)
- **Oja's rule** and convergence to principal components (Oja, 1982)
- **Weight decay** as regularization and its effect on eigenvalue spectrum
- **Eigenvalue concentration** in learning systems — dominant eigenvalue absorbs spectral mass
- Relevance: Study 65 identified Hebbian + decay as the mechanism producing the decreasing slope. The decay/lr ratio controls the transition.

### 2.5 Multi-Agent Systems and Fault Detection
- **Byzantine fault tolerance** (Lamport et al., 1982) — consensus under adversarial agents
- **Fleet coordination** — distributed inference, collective decision-making
- **Anomaly detection** in distributed systems — statistical vs. structural methods
- Relevance: The conservation law was discovered in a fleet of 9 LLM agents; its primary application is fleet health monitoring

### 2.6 What's Missing

Nobody has combined spectral graph theory + Hebbian eigenvalue dynamics + fleet fault detection. The conservation law sits at the intersection of:
- **Mathematics:** spectral properties of coupling matrices
- **Neuroscience:** learning dynamics that shape those matrices
- **Engineering:** using the resulting structure for fault detection and recovery

This intersection is the dissertation's unique contribution.

---

## Chapter 3: The Observation (Studies 54, 57, 63B, 65, 67, 71)

### 3.1 Discovery Narrative

The conservation law was discovered during routine fleet health monitoring of the PLATO cognitive fleet. Coupling matrices between fleet agents (measuring co-activation patterns and information flow) exhibited a striking regularity: for any fleet of size V, the sum γ+H clustered tightly around a value that decreased logarithmically with V.

**Timeline of discovery and refinement:**

| Study | Date | Finding | Impact |
|-------|------|---------|--------|
| 54 | 2026-05-13 | γ+H conservation is orthogonal to GL(9) alignment (r = −0.179) | Independent structural axis confirmed |
| 57 | 2026-05-13 | Conservation does NOT predict agent accuracy (MAE 0.048 vs. 0.045) | Domain tightened to structural diagnostics |
| 63B | 2026-05-14 | The ln(V) form is RMT-derivable, but constants are ensemble-specific; dense random shows **opposite** slope | Not a theorem — empirical phenomenon |
| 65 | 2026-05-14 | Eigenvalue concentration (top-1 ratio > 0.20) explains the decreasing slope; decay rate controls transition | Mechanism identified |
| 67 | 2026-05-15 | Law plateaus at V > 50; two-regime model needed | Domain boundary established |
| 73–74 | 2026-05-15 | Recovery strategies reassessed; Hebbian is circular, hybrid is best | Application refined |

### 3.2 The Law in Full

**Definition of terms:**
- **γ (normalized algebraic connectivity):** From graph Laplacian L = D − C. γ = (λ₁ − λ₀)/(λₙ − λ₀). Measures normalized global cohesion.
- **H (spectral entropy):** From eigenvalue distribution of C. H = −Σ pᵢ ln(pᵢ) / ln(V). Measures eigenvalue diversity, normalized to [0, 1].

**The empirical law:**

$$\gamma + H = 1.283 - 0.159 \cdot \ln V, \quad R^2 = 0.9602$$

**Calibrated uncertainty:**

| V | Predicted γ+H | σ | ±2σ band |
|---|--------------|---|----------|
| 5 | 1.027 | 0.070 | 0.887–1.167 |
| 10 | 0.917 | 0.065 | 0.787–1.047 |
| 20 | 0.807 | 0.058 | 0.691–0.923 |
| 30 | 0.742 | 0.050 | 0.642–0.842 |
| 50 | 0.661 | 0.048 | 0.565–0.757 |
| 100 | 0.551 | 0.042 | 0.467–0.635 |
| 200 | 0.441 | 0.038 | 0.365–0.517 |

**Two-regime extension (Study 67):**

$$\gamma + H = \begin{cases} 1.71 - 0.045 \cdot \ln V & V \leq 50 \quad (R^2 > 0.95) \\ 1.49 \pm 0.02 & V > 50 \quad \text{(plateau)} \end{cases}$$

### 3.3 What the Law Is NOT

1. **Not a predictor of accuracy.** MAE 0.048 with conservation vs. 0.045 baseline. No significant correlation at any V (Study 57).
2. **Not derivable from RMT alone.** The ln(V) form is RMT-derived, but the decreasing slope requires eigenvalue concentration, which is a property of the specific ensemble (Study 63B).
3. **Not universal.** Dense random matrices show γ+H = 1.002 + 0.135·ln(V) — the slope is **opposite** (Study 63B).
4. **Not a behavioral diagnostic.** Orthogonal to GL(9) alignment (r = −0.179), orthogonal to accuracy residuals (Study 54, 57).
5. **Not unbounded at large V.** Plateaus at V > 50 (Study 67). The log-linear form is only valid for V < 75.

### 3.4 Mechanism: Eigenvalue Concentration from Hebbian + Decay

**The decreasing slope arises from eigenvalue concentration** (Study 65):

1. Hebbian learning (ΔC ∝ η·xᵢxⱼ − λ·Cᵢⱼ) with weight decay produces matrices where the Perron eigenvalue absorbs disproportionate spectral mass.
2. As V grows, new nodes enter as periphery with weak connections to the core, making the Laplacian increasingly hub-like.
3. γ decreases faster than H increases, producing a negative slope.
4. **Discriminant:** top-1 eigenvalue ratio > 0.20 → decreasing slope; < 0.20 → increasing slope.
5. **Control knob:** decay rate. Low decay (0.001) → near-flat slope; high decay (0.1) → strongly decreasing (−0.164).

---

## Chapter 4: EXPERIMENTAL PROGRAM

The core research plan. Each experiment specifies hypothesis, methodology, resources, expected outcome, and dependencies. The program is organized in four tiers of increasing generality.

### Tier 1: Replication & Rigor (4–6 weeks)

**Goal:** Establish that the conservation law is real, replicable, and not a simulation artifact.

---

#### E1: Live Fleet Replication

**Hypothesis (pre-registered):** The conservation law γ+H = C − α·ln(V) holds for real LLM agent coupling matrices measured from live API calls, with R² > 0.90.

**Methodology:**
- Deploy 9 real LLM agents (GLM-4.7-flash, Hermes-70B, Qwen3-235B, Seed-2.0-mini, DeepSeek-v4-chat, Kimi, Claude Haiku, Llama-3.3-70B, Gemma-3-27b) as a live fleet
- Each agent processes 1,000+ tiles across diverse domains
- Measure coupling matrix C from actual co-activation patterns (agents that agree on answers develop stronger coupling)
- Compute γ+H for each measurement window
- Fit γ+H vs. ln(V) and compare to Monte Carlo prediction
- Statistical test: bootstrap 95% CI on R², compare to R² > 0.90 threshold
- Sample size: 1,000+ tiles per agent × 9 agents = 9,000+ data points
- Effect size threshold: R² > 0.90 (vs. null of R² = 0)

**Required resources:**
- 9 API endpoints (mix of paid and free tiers)
- ~$50–100 in API costs
- 2–3 days of compute time
- Python environment with NumPy, SciPy

**Expected outcome:** R² > 0.90 for the live fleet. The specific intercept may differ from 1.283 (Hebbian shift), but the log-linear form should hold.

**What it proves:** The conservation law is not a simulation artifact. It governs real multi-agent systems.

**Dependencies:** None — this is the foundation experiment.

---

#### E2: Fleet Size Variation with Live Models

**Hypothesis (pre-registered):** The conservation law holds across fleet sizes V ∈ {3, 5, 9, 15} with live agents, and the slope is negative (decreasing γ+H with V).

**Methodology:**
- Subsets of the 9-agent fleet: V = 3 (all triples), V = 5 (all quintuples), V = 9 (full fleet), V = 15 (fleet + 6 synthetic agents)
- 500 tiles per configuration
- Fit γ+H vs. ln(V) across the four fleet sizes
- Compare slope sign and magnitude to Monte Carlo prediction
- Statistical test: sign test on slope direction, bootstrap CI on slope magnitude
- Sample size: C(9,3) × 500 + C(9,5) × 500 + 1 × 500 + 1 × 500 = 3,500+ data points

**Required resources:**
- Same API endpoints as E1
- ~$80–150 in API costs (many subsets)
- 3–4 days

**Expected outcome:** Negative slope confirmed. Slope magnitude may differ from −0.159 (real fleet has different Hebbian dynamics than simulation).

**What it proves:** The size-dependence is real, not an artifact of Monte Carlo sampling.

**Dependencies:** E1 (need the fleet infrastructure).

---

#### E3: Multiple Coupling Architectures

**Hypothesis (pre-registered):** The conservation law's functional form (linear in ln V) holds across coupling architectures, but the slope direction depends on eigenvalue concentration (top-1 ratio > 0.20 → decreasing).

**Methodology:**
- Generate coupling matrices using 6 architectures (from Study 65):
  1. Hebbian with decay (fleet standard)
  2. Attention-based coupling (transformer-style)
  3. Random (Erdős-Rényi)
  4. Scale-free (Barabási-Albert)
  5. Block diagonal (modular)
  6. Anti-correlated (competitive)
- V ∈ {5, 10, 20, 30, 50, 100}, 1,000 samples per V per architecture
- Measure γ+H, fit log-linear model, record slope and R²
- Compute top-1 eigenvalue ratio for each sample
- Statistical test: logistic regression predicting slope direction from top-1 ratio; threshold analysis via ROC curve
- Sample size: 6 × 6 × 1,000 = 36,000 matrices

**Required resources:**
- Local compute only (matrix generation + eigenvalue decomposition)
- ~4 hours on modern laptop
- No API costs

**Expected outcome:** Slopes replicate Study 65. Top-1 ratio discriminant confirmed with larger sample. Logistic regression AUC > 0.90.

**What it proves:** The eigenvalue concentration mechanism is robust across architectures. The law is architecture-dependent, not universal.

**Dependencies:** None (can run in parallel with E1–E2).

---

#### E4: Statistical Re-Analysis of All Existing Data

**Hypothesis (pre-registered):** After proper statistical correction (Bonferroni, power analysis, confidence intervals), the conservation law remains significant with p < 0.001 and R² > 0.90.

**Methodology:**
- Re-analyze all existing Monte Carlo data (35,000 samples from v3 paper)
- Apply Bonferroni correction for multiple V values (7 comparisons)
- Compute bootstrap 95% CIs on slope and intercept
- Power analysis: what sample size was needed to detect the observed effect?
- Report Cohen's f² for the regression model
- Sample size: 35,000 (existing data)

**Required resources:**
- Local compute only
- ~1 hour

**Expected outcome:** R² > 0.95 remains after correction. Bonferroni-adjusted p < 10⁻¹⁰. Effect size Cohen's f² > 0.25 (large).

**What it proves:** The law survives rigorous statistical scrutiny. Prior results were not p-hacked.

**Dependencies:** None (uses existing data).

---

### Tier 2: Mechanism & Theory (4–6 weeks)

**Goal:** Derive the law from first principles and characterize the phase transitions.

---

#### E5: Eigenvalue Concentration Deep Dive

**Hypothesis (pre-registered):** The slope of γ+H vs. ln(V) is a smooth, monotonic function of the decay/learning-rate ratio, with a critical transition at decay/lr ≈ 1.

**Methodology:**
- Systematic sweep of decay ∈ {0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3} × lr ∈ {0.001, 0.003, 0.01, 0.03, 0.1}
- 40 parameter combinations
- V ∈ {5, 10, 20, 30, 50, 100}, 500 samples per V per parameter combo
- For each combo: compute γ+H slope, top-1 eigenvalue ratio, effective rank
- Fit transition model: logistic function mapping decay/lr → slope direction
- Identify critical transition point with 95% CI
- Statistical test: segmented regression with breakpoint estimation (Davies test)
- Sample size: 40 × 6 × 500 = 120,000 matrices

**Required resources:**
- Local compute: ~12–16 hours (CPU-intensive eigenvalue decomposition)
- No API costs

**Expected outcome:** Sharp transition near decay/lr ≈ 1. Slope = 0 at transition. Smooth interpolation from increasing (low decay) to decreasing (high decay). The critical point maps to the spiked RMT phase transition.

**What it proves:** The slope is a continuous function of learning dynamics parameters, establishing a quantitative theory connecting Hebbian parameters to spectral geometry.

**Dependencies:** E3 (confirms the 6-architecture result before deep parameter sweep).

---

#### E6: Spiked Random Matrix Theory Connection

**Hypothesis (pre-registered):** The eigenvalue concentration regime maps to the spiked random matrix model (Baik-Ben Arous-Péché transition), with the critical spike strength corresponding to the decay/lr transition.

**Methodology:**
- Model the fleet coupling matrix as M = β·vvᵀ + σ·W, where v is the Hebbian principal component, W is a Wigner random matrix, β is spike strength, σ is noise
- Derive analytically: for what β/σ does the top-1 eigenvalue ratio exceed 0.20?
- Derive analytically: how does γ+H depend on β/σ and V?
- Compare analytical predictions to E5 simulation results
- Statistical test: χ² goodness-of-fit between analytical and simulated slope curves
- This is primarily a theoretical derivation with numerical validation

**Required resources:**
- Theoretical work: pen, paper, and symbolic math (SymPy)
- Numerical validation: ~2 hours compute
- Reference material on spiked RMT

**Expected outcome:** Closed-form prediction of slope from β/σ. The decay/lr → β/σ mapping is derivable. The critical transition point has an analytical expression.

**What it proves:** If successful, the conservation law becomes a fully predictive theory: Hebbian parameters → eigenvalue concentration → slope constant. This is the strongest possible result.

**Dependencies:** E5 (parameter sweep provides empirical target for theory).

---

#### E7: Information-Theoretic Interpretation

**Hypothesis (pre-registered):** γ+H is bounded by the mutual information between the graph's edge-weight distribution and the eigenvalue distribution, and the conservation law expresses this bound.

**Methodology:**
- For each coupling matrix, compute:
  - Edge-weight entropy H_edge
  - Eigenvalue entropy H_eig (= H in the law)
  - Mutual information I(edge weights; eigenvalues)
  - γ (algebraic connectivity)
- Test: is γ+H ≈ I(edge_weights; eigenvalues) + constant?
- Vary V and measure all quantities
- Sample size: 5,000 matrices per V ∈ {5, 10, 20, 30, 50, 100} = 30,000

**Required resources:**
- Local compute: ~4 hours
- No API costs

**Expected outcome:** Either (a) γ+H tracks mutual information (information-theoretic proof), or (b) γ+H is not reducible to mutual information (negative result, still valuable). Expected: (b), because γ is a Laplacian property while H is a C-matrix property — they operate on different mathematical objects.

**What it proves:** Either grounds the law in information theory or rules it out, clarifying the mathematical nature of the constraint.

**Dependencies:** None (can run in parallel with E5).

---

#### E8: The Rank-Change Transition at V ≈ 50

**Hypothesis (pre-registered):** The plateau at V > 50 (Study 67) corresponds to the effective rank of the coupling matrix saturating, which occurs when the Hebbian dynamics have exhausted the learnable structure.

**Methodology:**
- Generate Hebbian matrices at V ∈ {10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200}
- For each V: compute effective rank, top-1 eigenvalue ratio, γ+H, condition number
- Fit effective rank vs. V: does it plateau at the same V where γ+H plateaus?
- Additional: run Hebbian for varying numbers of update steps (10, 50, 100, 200, 500, 1000) at each V to test convergence
- Statistical test: segmented regression with unknown breakpoint on effective rank curve
- Sample size: 12 V values × 1,000 samples × 6 step counts = 72,000 matrices

**Required resources:**
- Local compute: ~8 hours
- No API costs

**Expected outcome:** Effective rank plateaus near V = 50 for the standard Hebbian parameters. The plateau V is a function of decay rate and activation structure. More update steps push the plateau to higher V.

**What it proves:** The two-regime model has a mechanistic explanation: rank saturation. This gives the law a precise domain of applicability.

**Dependencies:** E5 (parameter sweep informs the step-count and decay choices).

---

### Tier 3: Generality (6–8 weeks)

**Goal:** Test whether the conservation law applies beyond the PLATO fleet — to neural networks, RL agents, swarms, and social networks.

---

#### E9: Neural Network Ensembles

**Hypothesis (pre-registered):** An ensemble of MNIST classifiers with Hebbian coupling between their weight matrices exhibits the same γ+H conservation law with decreasing slope.

**Methodology:**
- Train 20 LeNet-5 classifiers on MNIST (independent training)
- Construct coupling matrix C where Cᵢⱼ = cosine_similarity(weight_vector_i, weight_vector_j)
- Compute γ+H for the ensemble
- Vary ensemble size: V ∈ {3, 5, 10, 15, 20}
- Compare slope to fleet prediction
- Add Hebbian weight sharing: ΔWᵢ ∝ η·(Wⱼ − Wᵢ)·agreement_i_j − λ·Wᵢ
- Re-measure γ+H with Hebbian dynamics
- Statistical test: compare slope with and without Hebbian coupling via Welch's t-test
- Sample size: 10 independent trainings × 5 V values × 2 conditions = 100 data points

**Required resources:**
- GPU (any consumer GPU; LeNet-5 is lightweight)
- ~4 hours of GPU time
- No API costs

**Expected outcome:** Without Hebbian coupling, slope is positive (random-like). With Hebbian coupling, slope transitions toward negative. This would demonstrate substrate independence.

**What it proves:** The conservation law is not specific to LLM fleets — it governs any ensemble of learning systems with coupling.

**Dependencies:** E5 (confirms the Hebbian parameter sweep before applying to NNs).

---

#### E10: Multi-Agent RL

**Hypothesis (pre-registered):** Cooperative RL agents in a gridworld exhibit γ+H conservation in their communication coupling matrices, with the law emerging during training.

**Methodology:**
- Implement 5–20 cooperative Q-learning agents in a shared gridworld (cleanup, foraging, or predator-prey)
- Communication: agents broadcast action intentions; coupling = agreement frequency over sliding window
- Measure γ+H of the coupling matrix every 100 episodes
- Track evolution of γ+H during training (random initialization → learned cooperation)
- Vary team size: V ∈ {5, 10, 15, 20}
- Compare: with vs. without communication channel
- Statistical test: repeated-measures ANOVA on γ+H across training epochs and team sizes
- Sample size: 20 independent training runs × 4 team sizes × 2 conditions = 160 training runs

**Required resources:**
- CPU only (gridworld is lightweight)
- ~6 hours compute
- No API costs

**Expected outcome:** γ+H converges during training toward the conservation law. The slope is negative if agents develop structured communication. Without communication, coupling is near-zero and the law doesn't apply (trivially).

**What it proves:** The conservation law emerges in cooperative RL — a completely different substrate from LLM fleets.

**Dependencies:** E9 (neural network results inform whether to expect the law in learning systems).

---

#### E11: Swarm Robotics Simulation

**Hypothesis (pre-registered):** A simulated swarm of robots with local interaction rules exhibits γ+H conservation in their interaction coupling matrix.

**Methodology:**
- Implement N robots in a 2D physics simulator (Webots or custom)
- Interaction rules: attraction/repulsion based on distance and heading alignment
- Coupling matrix: Cᵢⱼ = time-averaged interaction strength
- Measure γ+H over time
- Vary swarm size: N ∈ {10, 20, 50, 100}
- Compare: homogeneous rules vs. heterogeneous (specialized roles)
- Statistical test: Mann-Whitney U test comparing γ+H distributions across swarm sizes
- Sample size: 30 runs per N × 4 N values × 2 conditions = 240 runs

**Required resources:**
- CPU (physics simulation)
- ~8 hours compute
- No API costs

**Expected outcome:** Homogeneous swarms show near-constant γ+H (no learning → no eigenvalue concentration). Heterogeneous swarms with role assignment may show the decreasing slope.

**What it proves:** The conservation law requires learning/differentiation, not just interaction. Pure physical coupling is insufficient.

**Dependencies:** None (can run in parallel).

---

#### E12: Social Network Data

**Hypothesis (pre-registered):** Real social network interaction graphs (Twitter/Reddit) exhibit γ+H conservation with a decreasing slope, consistent with the scale-free regime (Study 65).

**Methodology:**
- Obtain interaction graphs from public datasets:
  - Reddit: user–subreddit interaction frequency (V = subreddit count)
  - Twitter/X: user–user retweet/mention frequency
  - Enron email corpus: sender–recipient frequency
- Construct weighted adjacency matrices
- Compute γ+H for subgraphs of varying V
- Compare slope to Study 65's scale-free prediction (−0.147)
- Statistical test: bootstrap CI on slope; compare to −0.147 threshold
- Sample size: 10+ subgraphs per V ∈ {10, 20, 50, 100, 200, 500}

**Required resources:**
- Public datasets (free)
- CPU: ~4 hours
- No API costs

**Expected outcome:** Social networks are scale-free → decreasing slope predicted. If confirmed, the conservation law applies to human social dynamics.

**What it proves:** The law is substrate-independent across silicon AND carbon systems. This would be the most dramatic generalization.

**Dependencies:** E3 (confirms scale-free prediction before testing on real data).

---

### Tier 4: Applications (4–6 weeks)

**Goal:** Turn the conservation law into a production-ready fleet health system.

---

#### E13: Fleet Health Monitoring — Production Deployment

**Hypothesis (pre-registered):** A conservation-based health monitor detects fleet anomalies faster than accuracy-based monitoring alone, with detection latency < 5 rounds and false positive rate < 5%.

**Methodology:**
- Deploy on live fleet (E1 infrastructure)
- Two parallel monitors: (a) γ+H deviation from conservation prediction, (b) accuracy drop detection
- Inject controlled faults: single agent drift, pair misalignment, content corruption, adversarial behavior
- Measure: detection latency, false positive rate, true positive rate
- Compare to accuracy-only detection
- Statistical test: McNemar's test on detection outcomes (paired by fault event)
- Sample size: 200 fault injections + 200 healthy windows = 400 test windows

**Required resources:**
- Live fleet infrastructure (from E1)
- ~$100–200 API costs
- 5–7 days of monitoring

**Expected outcome:** Conservation detection catches structural faults that accuracy misses. Combined detection (conservation + accuracy) achieves F1 > 0.80 vs. accuracy-only F1 ≈ 0.50.

**What it proves:** The conservation law has practical value for fleet operations, not just theoretical interest.

**Dependencies:** E1 (live fleet), E2 (size calibration).

---

#### E14: Hybrid Recovery Protocol Validation

**Hypothesis (pre-registered):** The hybrid recovery strategy (Hebbian alignment + conservation accuracy restoration) recovers from shock in < 20 rounds on a live fleet, with content accuracy restored to > 90% of baseline.

**Methodology:**
- On live fleet (E1 infrastructure), inject shocks:
  - 3 severity levels: 1 agent, 3 agents, 5 agents degraded
  - Degradation: real API errors, increased temperature, prompt injection
- Test 4 recovery strategies: (a) hybrid, (b) pure Hebbian, (c) quarantine, (d) no recovery (control)
- Measure recovery on 4 metrics: alignment, content accuracy, tile quality, conservation compliance
- 25 trials per strategy × severity = 300 runs total
- Statistical test: Kruskal-Wallis on recovery rounds, with Dunn's post-hoc
- Sample size: 4 strategies × 3 severities × 25 trials = 300 runs

**Required resources:**
- Live fleet + controlled fault injection
- ~$200–400 API costs
- 7–10 days

**Expected outcome:** Hybrid recovers all 4 metrics. Pure Hebbian recovers alignment only (confirming Study 74's circularity finding on live data). Quarantine is slow but accurate.

**What it proves:** Study 74's hybrid strategy works on real systems, not just simulation.

**Dependencies:** E1 (live fleet), E13 (health monitoring to detect when recovery is needed).

---

#### E15: Scale Prediction — Given V and Coupling, Predict Compliance

**Hypothesis (pre-registered):** A model trained on E1–E3 data can predict a fleet's γ+H compliance from V and coupling architecture parameters with MAE < 0.05.

**Methodology:**
- Collect data from E1 (live), E2 (varying V), E3 (varying architecture)
- Features: V, top-1 eigenvalue ratio, effective rank, decay rate, learning rate, sparsity, modularity
- Target: γ+H deviation from conservation prediction
- Train: linear regression, random forest, gradient boosting
- Evaluate: 5-fold cross-validation, MAE, R²
- Statistical test: compare to naive baseline (predict mean deviation) via paired t-test
- Sample size: ~50,000 data points from E1–E3

**Required resources:**
- Data from E1–E3 (no additional compute)
- ~2 hours for model training

**Expected outcome:** Top-1 eigenvalue ratio and decay/lr are the dominant features. R² > 0.80 for prediction. This enables "predict compliance before deploying."

**What it proves:** The conservation law is practically predictable, enabling fleet design optimization.

**Dependencies:** E1, E2, E3 (training data).

---

## Chapter 5: Expected Contributions

### C1: First Observation of Conservation Law in Agent Coupling Matrices
**Status:** Empirical observation with strong statistical support (R² = 0.9602, N = 35,000).
**Remaining work:** E1 (live validation), E4 (rigorous statistical re-analysis).
**Publishability:** Observation paper after E1. Target: NeurIPS workshop or similar.

### C2: Mechanism — Eigenvalue Concentration Explaining the Decreasing Slope
**Status:** Supported by Study 65 (8 regimes, discriminant = top-1 ratio).
**Remaining work:** E5 (deep parameter sweep), E6 (spiked RMT derivation).
**Publishability:** Theory paper after E6. If spiked RMT derivation succeeds, target: Physical Review E or similar.

### C3: Two-Regime Model (Log-Linear → Plateau)
**Status:** Observed in Study 67 (plateau at V > 50, R² < 0.90).
**Remaining work:** E8 (rank-change transition mechanism).
**Publishability:** Combined with C2 in the theory paper.

### C4: Ensemble-Dependence Proof (Not Derivable from RMT)
**Status:** Proven by Study 63B (dense random = opposite slope).
**Remaining work:** None — this is established.
**Publishability:** Key result in the observation paper.

### C5: Application to Fleet Health Monitoring and Recovery
**Status:** Mixed. Conservation is a valid structural diagnostic. Recovery needs redesign (Studies 73–74).
**Remaining work:** E13 (health monitoring), E14 (hybrid recovery validation).
**Publishability:** Systems paper after E14. Target: AAMAS or similar multi-agent systems venue.

### C6: Substrate Independence
**Status:** Untested. Scale-free networks show decreasing slope (Study 65), but no biological/social systems tested.
**Remaining work:** E9 (NN ensembles), E10 (RL), E11 (swarm), E12 (social networks).
**Publishability:** If confirmed, the highest-impact contribution. Target: Nature Machine Intelligence or Science Advances.

### C7: Fault Detection Architecture
**Status:** Study 75 showed 76.2% of faults are missed. GL(9) is dead weight.
**Remaining work:** Design new structural fault detector. Re-run E13 with improved system.
**Publishability:** Combined with C5 in the systems paper.

---

## Chapter 6: Timeline

### Gantt Chart (Weeks 1–26)

```
Week  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26
E1   ████████                                                       ← LIVE FLEET
E2      ██████████                                                    ← LIVE FLEET
E3   ████████████                                                    ← SIMULATION
E4   ████                                                            ← ANALYSIS
         ↓ Publishable: Chapter 3 observations (Week 8)
E5         ████████████████████                                      ← SIMULATION
E6               ████████████████████                                ← THEORY
E7         ████████████                                              ← SIMULATION
E8               ████████████████                                    ← SIMULATION
         ↓ Publishable: Mechanism paper (Week 14)
E9                  ████████████████                                 ← GPU
E10                     ████████████████                             ← CPU
E11                        ████████████████                          ← CPU
E12                  ████████████████                                ← DATA
         ↓ Publishable: Generality paper (Week 20)
E13                              ████████████████                    ← LIVE FLEET
E14                                 ████████████████                 ← LIVE FLEET
E15                                          ████████                ← ML
         ↓ Publishable: Applications paper (Week 24)
Diss writing       ████████████████████████████████████████████
         ↓ Dissertation submission (Week 26)
```

### Key Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 4 | Statistical re-analysis complete | E4 report, effect sizes, power analysis |
| 6 | Live fleet replication complete | E1 report, live R², intercept comparison |
| 8 | **Tier 1 complete. Observation paper draftable.** | E1–E4 reports consolidated |
| 10 | Fleet size variation complete | E2 report, slope comparison |
| 12 | Eigenvalue concentration deep dive | E5 report, transition point, parameter map |
| 14 | **Tier 2 complete. Mechanism paper draftable.** | E5–E8 reports, spiked RMT derivation |
| 16 | NN ensemble results | E9 report |
| 18 | RL and swarm results | E10, E11 reports |
| 20 | **Tier 3 complete. Generality paper draftable.** | E9–E12 reports |
| 22 | Social network results | E12 report, substrate independence claim |
| 24 | **Tier 4 complete. Applications paper draftable.** | E13–E15 reports |
| 26 | **Dissertation complete.** | Full document submitted |

### Critical Path

```
E1 → E2 → E13 → E14 → Dissertation
E3 → E5 → E6 → Dissertation
E5 → E9 → E10 → Dissertation
E3 → E12 → Dissertation
```

The critical path runs through E1 (live validation) → E13–E14 (applications). Total: 24 weeks.

### Earliest Publishable Result

**Chapter 3 observations (Week 8):** After E1–E4, we have a live-validated conservation law with rigorous statistics. This is publishable as an observation/discovery paper.

### Resource Summary

| Resource | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Total |
|----------|--------|--------|--------|--------|-------|
| API costs | $150–250 | $0 | $0 | $300–600 | **$450–850** |
| GPU hours | 0 | 0 | ~4 | 0 | **~4** |
| CPU hours | ~20 | ~40 | ~30 | ~10 | **~100** |
| Calendar weeks | 4–6 | 4–6 | 6–8 | 4–6 | **18–26** |

---

## Appendix: Current Evidence Table

### Study-by-Study Summary

| Study | Finding | Confidence | Methodology Score | Status |
|-------|---------|:----------:|:-----------------:|--------|
| **54** | Conservation ↔ GL(9) orthogonal (r = −0.179) | **High** | 5/7 ✅ | Established |
| **55** | Router degradation → death spiral | Medium | 4/7 ✅ | Needs live validation |
| **56** | Cross-domain transfer: labels help 4pp | Medium | 5/7 ✅ | Established |
| **57** | Conservation does NOT predict accuracy | **High** | 4/7 ✅ | Established (negative result) |
| **58** | GL(9) vs Hebbian fault detection: 60% agreement | **Low** | 2/7 ❌ | Needs redesign (N too small) |
| **59** | Code tier taxonomy | Low | 3/7 ❌ | Needs redesign (no replication) |
| **60** | Temperature × tier interaction | Medium | 5/7 ✅ | Established |
| **61** | GSM8K activation-key model | Medium | 5/7 ✅ | Established |
| **63** | Fleet self-healing via GL(9) | **Low** | 2/7 ❌ | Needs redesign |
| **63B** | RMT derivation: form yes, constants no, opposite slope | **High** | 5/7 ✅ | **Key result** |
| **64** | Conservation reweighting 3.1× faster | **OVERTURNED** | 2/7 ❌ | Replaced by Study 73 |
| **65** | Eigenvalue concentration mechanism | **High** | 5/7 ✅ | **Key result** |
| **66** | Decay tuning: no single rate satisfies all criteria | Medium | 4/7 ✅ | Established |
| **67** | Scale break: plateau at V > 50, not catastrophic | **High** | 4/7 ✅ | **Key result** |
| **68** | Adversarial coupling: Hebbian never detects | Low | 3/7 ❌ | Needs redesign |
| **69** | Methodology audit: 5/15 need redesign | N/A | N/A | Meta-study |
| **72** | GL(9) root cause: 6/9 hash dimensions dilute signal | Medium | 5/7 ✅ | GL(9) effectively dead |
| **73** | Shell shock redesign: Hebbian wins 100%, conservation 0% | **High** | 5/7 ✅ | Overturns Study 64 |
| **74** | Hebbian is circular; hybrid is best | **High** | 6/7 ✅ | **Key result** |
| **75** | Triple detector misses 76.2% of faults; GL(9) adds zero | **High** | 5/7 ✅ | **Key result** |

### What's Solid (High Confidence, ≥4/7 Methodology)

1. **γ+H conservation law exists** (R² = 0.9602, 35,000 samples)
2. **Eigenvalue concentration is the mechanism** (Study 65, 8 regimes)
3. **The law is NOT derivable from RMT** (Study 63B, opposite slope for dense random)
4. **Conservation is orthogonal to GL(9)** (Study 54, r = −0.179)
5. **Conservation does NOT predict accuracy** (Study 57, negative result)
6. **Hebbian recovery is circular** (Study 74, wins only on metric it optimizes)
7. **Hybrid recovery is the best available strategy** (Study 74, 100% on 3/4 metrics)
8. **GL(9) fault detection is non-functional** (Studies 72, 75, zero recall)
9. **Fault detection coverage is weak** (Study 75, 76.2% missed)

### What Needs Replication

1. Live fleet validation (all results are simulation-based)
2. Scale behavior beyond V = 200
3. Cross-architecture generality (only 6 regimes tested)
4. Recovery protocol on real API data

### What's Overturned

1. Study 64's "conservation reweighting 3.1× faster" → **Overturned by Study 73** (0% recovery)
2. Study 64's "Hebbian never converges" → **Overturned by Study 73** (100% recovery)
3. Original assumption that GL(9) is useful → **Overturned by Studies 72, 75** (zero information gain)

---

## Appendix B: Open Research Questions (Ranked by Impact)

| Rank | Question | Expected Answer | Key Experiment |
|------|----------|----------------|----------------|
| 1 | Can we derive the slope (−0.159) from Hebbian parameters via spiked RMT? | Yes, with sufficient theoretical work | E6 |
| 2 | Does the law hold for live LLM fleets? | Yes, with different constants | E1 |
| 3 | Does the law generalize to biological neural networks? | Unknown — high variance prediction | E9 analog |
| 4 | Does the law generalize to social networks? | Likely yes (scale-free regime) | E12 |
| 5 | What is the correct fleet recovery protocol? | Hybrid (Hebbian + conservation) | E14 |
| 6 | Can we predict compliance from fleet parameters? | Yes (top-1 ratio + decay/lr) | E15 |
| 7 | Why does the effective rank saturate at V ≈ 50? | Finite Hebbian learning capacity | E8 |
| 8 | Is there a third regime beyond the plateau? | Unknown — could be exponential decay | E8 |

---

## Appendix C: Pre-Registration Template

Each Tier 2–4 experiment should be pre-registered with:

1. **Hypothesis:** One-sentence falsifiable claim
2. **Prediction:** Quantitative expected result
3. **Methodology:** Sample size, statistical test, effect size threshold
4. **Success criteria:** What constitutes confirmation/rejection
5. **Analysis plan:** Before seeing data, specify exactly which tests will be run
6. **Data availability:** All raw data and code will be published

Template: https://osf.io/registries (or equivalent)

---

*Forgemaster ⚒️ · PLATO Fleet Laboratory · 2026-05-15*
*This document is the research plan. The law is the moat. Build it right.*
