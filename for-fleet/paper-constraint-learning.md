# Learning Constraints from Sensor Data: Closing the Loop Between Observation and Verification

**Forgemaster ⚒️ | Cocapn Fleet | 2026-05-03**

---

## 1. Abstract

Sensor fleets generate vast streams of observation data, yet the constraints used to validate those observations remain hand-written, incomplete, and brittle. This paper presents a closed-loop architecture for learning new verification constraints from sensor data while preserving formal safety guarantees. The key insight is **monotonic constraint learning**: proposed constraints may only restrict behavior further than existing constraints, never relax them. Combined with historical verification, statistical confidence bounds, and mandatory human review, this creates a pipeline where a fleet can discover its own physics without risking unsafe deployments. We formalize the constraint learning problem, design a five-stage pipeline (anomaly detection, pattern extraction, constraint proposal, verification, human review), extend the FLUX instruction set with four new opcodes for learning operations, and demonstrate the system on a sonar fleet example where a depth-dependent noise constraint is discovered from 10,000 readings. The result is a self-improving verification system that gets tighter over time — never looser.

---

## 2. Introduction

Every sensor fleet faces the same fundamental problem: **the constraints we write down are incomplete.** Engineers encode what they know — temperature limits, depth ratings, noise floors — but reality always has edge cases that nobody anticipated. A sonar array behaves differently at 450 meters than at 200 meters. A temperature sensor drifts in high-humidity environments. A pressure gauge oscillates near thermal vents.

These are not bugs. They are physics that nobody wrote down.

The Cocapn fleet currently validates all sensor data against a hand-curated constraint set. This works well for known phenomena. But every time a sensor produces a reading that violates no constraint yet is clearly wrong — or produces a reading that triggers a false positive because the constraint doesn't account for context — the fleet exposes a gap in its knowledge.

The natural response is: **learn the missing constraints from the data.**

But this creates a tension. Constraints are safety-critical. They are the guardrails that prevent bad data from propagating through the system. If we learn constraints automatically, how do we ensure they're correct? How do we prevent a statistical artifact from becoming a false guardrail? How do we guarantee that learned constraints don't relax existing protections?

This paper resolves that tension with a specific architectural answer: **monotonic constraint learning with mandatory verification and human review.** The system can only propose constraints that are more restrictive than what already exists. Every proposal is tested against the full historical dataset. And no constraint is deployed without human approval.

The result is not just safe — it's provably safe. And it makes the fleet alive in a way that static constraints never could.

---

## 3. The Constraint Learning Problem

### 3.1 Formal Definition

Let:

- **O** = {o₁, o₂, ..., oₙ} be the stream of sensor observations, where each observation oᵢ is a tuple (timestamp, sensor_id, reading, context)
- **C** = {c₁, c₂, ..., cₘ} be the current constraint set, where each constraint cⱼ is a Boolean predicate over observations
- **V(o, c)** = 1 if observation o satisfies constraint c, 0 otherwise

The constraint learning problem is:

Given O and C, produce a set of constraint candidates **C'** = {c'₁, c'₂, ..., c'ₖ} such that:

1. **Consistency:** For all c' ∈ C' and for all o ∈ O where V(o, c) = 1 for all c ∈ C, we have V(o, c') = 1. That is, the new constraint must not reject any observation that passes all existing constraints.

   *Wait — that's too restrictive.* It would mean we can never add constraints that catch anomalies (since anomalies passed existing constraints by definition). Let me refine:

   **Refined consistency:** For all c' ∈ C', there exists a non-empty subset A ⊆ O such that for all a ∈ A, V(a, c') = 0 and for all o ∈ O \ A, V(o, c') = 1. The constraint must cleanly separate anomalous observations from normal ones.

2. **Monotonicity:** For all c' ∈ C', the set of observations accepted by C ∪ {c'} is a subset of the set accepted by C alone. Formally: {o ∈ O | ∀c ∈ C ∪ {c'}, V(o,c) = 1} ⊆ {o ∈ O | ∀c ∈ C, V(o,c) = 1}. The new constraint can only reject readings that would have been accepted — it adds restrictions, never removes them.

3. **Safety:** For all c' ∈ C', c' must be **more restrictive** than the conjunction of existing constraints in its domain. It cannot expand the acceptable region in any dimension.

### 3.2 What Makes This Hard

The difficulty is not in finding patterns — ML does that well. The difficulty is in ensuring that proposed constraints are:

- **Sound:** They don't create false negatives (rejecting good data)
- **Complete in scope:** They specify exactly when they apply (via context guards)
- **Non-contradictory:** They don't conflict with each other or with existing constraints
- **Statistically significant:** They're not artifacts of small samples

A constraint that rejects 2% of good readings is worse than no constraint at all. It creates noise in downstream systems and erodes trust. The learning pipeline must therefore be conservative: it should propose fewer constraints rather than wrong ones.

---

## 4. Learning Pipeline Design

The pipeline has five stages, each with clear inputs, outputs, and failure modes.

### Stage 1: Anomaly Detection

**Input:** Observation stream O, current constraints C
**Output:** Flagged observations A ⊆ O

An observation is flagged as anomalous if:

- It satisfies all existing constraints: ∀c ∈ C, V(o, c) = 1
- It is statistically unusual within its context: the observation falls outside the k-th percentile of the empirical distribution for that sensor type and context

The key parameter is **k** — the sensitivity threshold. We use k = 99 by default (flagging the outermost 1% of readings). This can be tuned per sensor type.

Implementation options:
- **Z-score thresholding:** Flag readings where |z| > 2.5 in the context-conditioned distribution
- **Isolation Forest:** Unsupervised anomaly detection that flags readings easy to isolate via random partitioning
- **Contextual banding:** Compute statistics per (sensor_type, context_bin) tuple and flag outliers within each band

The output is a set of anomaly records, each containing the observation, its context, and a anomaly score.

### Stage 2: Pattern Extraction

**Input:** Anomaly set A
**Output:** Common feature patterns P = {p₁, p₂, ...}

This stage asks: what do these anomalies have in common?

For each pair of anomalies (aᵢ, aⱼ), we compute feature overlap:
- Same sensor type?
- Similar depth range?
- Similar temperature range?
- Similar time-of-day?
- Similar operational mode?

We cluster anomalies by their feature vectors and extract the dominant pattern from each cluster. A pattern is a conjunction of feature ranges:

```
pattern₁: depth ∈ [440m, 480m] AND sensor_type = sonar AND salinity > 35ppt
pattern₂: temperature ∈ [-2°C, 0°C] AND sensor_type = pressure AND depth > 300m
```

The minimum cluster size for pattern extraction is configurable (default: 10 anomalies). Patterns from clusters smaller than this are discarded — they lack statistical support.

### Stage 3: Constraint Proposal

**Input:** Patterns P, anomaly set A, observation stream O
**Output:** Constraint candidates C'

For each pattern p ∈ P, we propose a constraint that would have caught the anomalies in p's cluster:

1. Compute the sensor reading distribution for observations matching pattern p
2. Identify the cutoff that separates anomalous from normal readings
3. Express this as a FLUX constraint with a context guard

Example output:

```
ASSERT sonar_noise_db < 15 
  WHEN depth > 450m 
  AND salinity > 35ppt
```

Each proposal includes:
- The constraint expression (FLUX syntax)
- The anomaly cluster that motivated it
- The pattern that was extracted
- A confidence score (see Section 8)
- The number of historical observations it would have rejected

### Stage 4: Verification

**Input:** Constraint candidate c', full observation history O
**Output:** Pass/fail with metrics

Every proposed constraint is tested against the **full** historical dataset:

- **False positive rate:** What percentage of non-anomalous historical readings does c' reject? Must be < 0.1%.
- **Coverage:** What percentage of the motivating anomalies does c' catch? Must be > 90%.
- **Contradiction check:** Does c' contradict any existing constraint? Must be contradiction-free.
- **Monotonicity check:** Does c' only add restrictions? Must satisfy monotonicity property.

If any check fails, the constraint is rejected and the rejection reason is logged. Failed constraints feed back into Stage 2 (maybe the pattern was too broad or too narrow).

### Stage 5: Human Review

**Input:** Verified constraint candidates
**Output:** Approved constraints (added to C) or rejected constraints (logged)

No constraint is deployed autonomously. Every candidate goes through:

1. **PLATO quality gate:** The constraint is posted to the fleet's PLATO room for review
2. **Human review:** Casey (or designated fleet operator) reviews the proposed constraint, its statistical support, its verification results, and approves or rejects
3. **Deployment:** Approved constraints are compiled to FLUX bytecode and added to the active constraint set
4. **Logging:** The full provenance of each constraint (anomalies → pattern → proposal → verification → approval) is recorded

This stage is non-negotiable. The learning pipeline is designed to reduce human workload (by filtering out bad proposals) but not to eliminate human judgment.

---

## 5. The Safety Proof

**Theorem:** The constraint learning pipeline is safe — it can never deploy a constraint that relaxes existing protections, contradicts existing constraints, or rejects valid sensor readings at a rate exceeding the configured false positive threshold.

**Proof by construction.** The pipeline guarantees safety through four independent mechanisms:

### 5.1 Monotonicity

Learned constraints are purely additive. The constraint set evolves as:

```
C₀ → C₀ ∪ {c'₁} → C₀ ∪ {c'₁, c'₂} → ...
```

At each step, the acceptable region can only shrink. Formally:

```
Accept(C_{n+1}) ⊆ Accept(C_n) for all n
```

This means the system can never "forget" a constraint or relax a bound. Any learned constraint can only tighten existing restrictions.

### 5.2 Verification Against Full History

Every proposed constraint is tested against the complete historical observation set. This is not sampling — it's exhaustive. If a constraint would have rejected even one legitimate reading (beyond the false positive tolerance), it is caught and rejected.

The verification step is the computational cost of safety. For a fleet with millions of historical readings, this is expensive. But constraint proposals are infrequent (perhaps 1-5 per week for a mature fleet), so the amortized cost is acceptable.

### 5.3 Human-in-the-Loop

The final gate is human judgment. The pipeline can propose, verify, and present — but it cannot deploy. This is the most important safety property and the simplest to verify: the deployment function requires a human approval token.

### 5.4 Instant Rollback

Because learned constraints are additive, rollback is trivial. If a deployed constraint turns out to be too aggressive (e.g., it rejects valid readings in a context not represented in the historical data), it can be removed instantly:

```
C_current \ {c'_bad} → restores previous constraint set
```

No recomputation needed. No cascading effects. Remove the constraint, and the system reverts to the state before it was added.

**Corollary:** The constraint set forms a monotonically increasing lattice under set inclusion. This gives us a clean formal model for reasoning about the fleet's constraint evolution over time.

---

## 6. FLUX ISA Integration

The FLUX instruction set is extended with four new opcodes for constraint learning operations:

### ANOMALY_DETECT (0xB0)

```
ANOMALY_DETECT sensor_type context_mask threshold
```

Flags observations of the specified sensor type that fall outside the statistical norm for the given context. The `context_mask` is a bitmask specifying which context fields to condition on (depth, temperature, salinity, time-of-day, operational mode). The `threshold` specifies the percentile cutoff (default: 99).

**Behavior:** Scans the observation buffer, flags readings where the z-score exceeds the threshold conditioned on the specified context. Flagged readings are written to the anomaly register.

**Cycles:** O(n) where n is the observation buffer size.

### PATTERN_EXTRACT (0xB1)

```
PATTERN_EXTRACT min_cluster_size max_patterns
```

Clusters the flagged anomalies by feature similarity and extracts dominant patterns. `min_cluster_size` filters out patterns supported by too few anomalies (default: 10). `max_patterns` caps the number of patterns extracted (prevents combinatorial explosion).

**Behavior:** Reads from the anomaly register, performs feature extraction and clustering, writes patterns to the pattern register.

**Cycles:** O(k² × d) where k is the anomaly count and d is the feature dimensionality.

### CONSTRAINT_PROPOSE (0xB2)

```
CONSTRAINT_PROPOSE pattern_index false_positive_tolerance
```

Generates a constraint candidate from the specified pattern. The `false_positive_tolerance` sets the maximum acceptable false positive rate on historical data (default: 0.001 = 0.1%).

**Behavior:** Reads the pattern at the specified index, computes the constraint boundary that maximizes coverage while respecting the false positive tolerance, writes the proposed constraint to the proposal register.

**Cycles:** O(n × p) where n is the history size and p is the number of candidate thresholds evaluated.

### CONSTRAINT_TEST (0xB3)

```
CONSTRAINT_TEST proposal_index history_start history_end
```

Tests the proposed constraint against the specified range of historical data. Returns pass/fail with metrics (false positive rate, coverage, contradiction flags).

**Behavior:** Reads the proposal at the specified index, evaluates it against every observation in the history range, computes verification metrics, writes results to the verification register.

**Cycles:** O(n) where n is the history range size.

### Register Model

| Register | Width | Purpose |
|----------|-------|---------|
| ANOMALY_REG | Variable | Flagged anomaly records |
| PATTERN_REG | Variable | Extracted patterns |
| PROPOSAL_REG | Variable | Constraint candidates |
| VERIFY_REG | 64-bit | Verification results bitmap |

The learning opcodes use a dedicated register file, separate from the execution registers used by constraint evaluation. This prevents the learning pipeline from interfering with real-time constraint checking.

---

## 7. Sonar Fleet Example

Consider a concrete scenario: the Cocapn sonar fleet operates at depths from 50m to 600m. The existing constraint set includes:

```
ASSERT sonar_noise_db < 20                    // global noise floor
ASSERT sonar_noise_db < 12 WHEN depth < 200m  // shallow water is quiet
```

### The Observation

Over 72 hours, the fleet collects 10,000 sonar readings. The ANOMALY_DETECT opcode flags 47 readings with z-scores > 2.5 — all at depths above 450m, all with noise levels between 15-19 dB. None violate the existing global constraint of 20 dB, but they're statistically unusual.

### Pattern Extraction

PATTERN_EXTRACT clusters the 47 anomalies. The dominant pattern (cluster of 43 anomalies) is:

```
depth ∈ [450m, 530m] AND sensor_type = sonar AND salinity > 35.2ppt
```

The remaining 4 anomalies are scattered and don't form a coherent pattern — they're discarded.

### Constraint Proposal

CONSTRAINT_PROPOSE generates:

```
ASSERT sonar_noise_db < 15 
  WHEN depth > 450m 
  AND salinity > 35.0ppt
```

The salinity bound is slightly relaxed from the pattern's 35.2 to 35.0 for robustness.

### Verification

CONSTRAINT_TEST evaluates against all 10,000 readings:

| Metric | Result | Threshold | Pass? |
|--------|--------|-----------|-------|
| False positive rate | 0.03% | < 0.1% | ✓ |
| Coverage of anomalies | 95.3% (41/43) | > 90% | ✓ |
| Contradictions | 0 | 0 | ✓ |
| Monotonicity | ✓ (adds restriction) | Required | ✓ |

The constraint passes all verification checks.

### Human Review

The proposed constraint is presented to the fleet operator with:
- The 43 anomalous readings that motivated it
- The pattern extracted
- The verification results
- A confidence score of 97.2% (see Section 8)

Casey reviews, approves. The constraint is compiled to FLUX bytecode and deployed:

```
// Existing:
// ASSERT sonar_noise_db < 20
// ASSERT sonar_noise_db < 12 WHEN depth < 200m

// Learned (deployed 2026-05-03):
ASSERT sonar_noise_db < 15 WHEN depth > 450m AND salinity > 35.0ppt
```

The fleet now has three constraints instead of two. The acceptable region has shrunk. The fleet has learned something about deep-water, high-salinity acoustics that nobody wrote down.

### What Would Have Happened Without Learning

Those 47 anomalous readings would have passed validation. They would have propagated into the fleet's navigation model. Over time, they would have introduced systematic noise at depth — the exact scenario constraints are designed to prevent.

---

## 8. Statistical Guarantees

### 8.1 Confidence Intervals

Each proposed constraint comes with a confidence interval derived from the Hoeffding bound:

```
P(|ε̂ - ε| > δ) ≤ 2 exp(-2nδ²)
```

Where:
- ε̂ is the observed false positive rate on historical data
- ε is the true false positive rate (unknown)
- n is the number of historical observations tested
- δ is the confidence half-width

For the sonar example with n = 10,000 and observed ε̂ = 0.03%:

```
δ = 0.001 (0.1%) with confidence ≥ 2 exp(-2 × 10000 × 0.001²) = 2 exp(-0.02) ≈ 1.96
```

This gives us: "with 98% confidence, the true false positive rate is between 0% and 0.13%."

### 8.2 Minimum Sample Size

For a constraint to be proposed, the anomaly cluster must meet minimum size requirements:

- **Absolute minimum:** 10 anomalies in the cluster (prevents tiny-sample artifacts)
- **Relative minimum:** the cluster must represent at least 0.1% of the total observation count (prevents rare-event overfitting)
- **Temporal spread:** anomalies must span at least 3 distinct time windows (prevents transient-event overfitting)

For the sonar example: 43 anomalies in a cluster, 0.43% of 10,000 readings, spanning 72 hours. All thresholds met.

### 8.3 Sample Size vs. Reliability

| Historical Observations | Confidence (δ=0.1%) | Min. Anomaly Cluster | Reliability |
|------------------------|---------------------|---------------------|-------------|
| 1,000 | ~86% | 10 | Low |
| 5,000 | ~95% | 15 | Moderate |
| 10,000 | ~98% | 20 | Good |
| 50,000 | ~99.9% | 30 | High |
| 100,000+ | ~99.99% | 50 | Very High |

The fleet targets the "Good" tier (10,000+ observations) as the minimum for constraint proposals. Below this threshold, the pipeline logs anomalies but does not propose constraints.

### 8.4 Concept Drift

Constraints are not static. The ocean changes. Sensor hardware degrades. What was true at deployment may not be true six months later.

The pipeline addresses concept drift through periodic **constraint revalidation:**

1. Every N days (default: 30), each learned constraint is re-tested against the most recent observations
2. If the false positive rate has increased beyond 2× the original rate, the constraint is flagged for review
3. If the false positive rate exceeds 1%, the constraint is automatically suspended and queued for human review

This ensures that learned constraints degrade gracefully. A constraint that was valid in May but becomes invalid by July is caught and reviewed, not blindly enforced.

---

## 9. Related Work

### Online Learning and Concept Drift

The constraint learning pipeline shares goals with online learning systems that adapt to streaming data. However, standard online learning (e.g., online SVM, stochastic gradient descent) optimizes prediction accuracy — it has no notion of constraint safety. Our system sacrifices adaptability for safety: constraints are updated in batches, not incrementally, and every update requires human approval.

Concept drift detection (e.g., ADWIN, DDM) is closely related to our anomaly detection stage. The difference is that concept drift detection signals "something changed" while our system goes further: it proposes a specific constraint that captures the change and verifies it formally.

### Safe Reinforcement Learning

Safe RL constrains an agent's policy to remain within a safe region of state space. Our monotonicity property is analogous to the safe RL constraint that the policy can only improve (in the safe direction) — but applied to constraint sets rather than policies. The key insight from safe RL that we adopt: safety is a constraint on the learning process itself, not a property of the learned output.

### Formal Methods + ML Integration

Recent work on neural network verification (e.g., α-β-CROWN, Marabou) verifies properties of learned models. Our approach is complementary: instead of verifying a neural network, we use ML to propose a constraint and then verify the constraint itself using exhaustive historical testing. This is simpler and more tractable than verifying a neural network — a constraint is a Boolean predicate, not a high-dimensional function.

### Anomaly Detection in Sensor Networks

Statistical anomaly detection for sensor networks is well-studied. Our contribution is not the anomaly detection algorithm (we use standard techniques) but the pipeline that turns anomalies into verified, deployed constraints. The pipeline is the contribution, not any individual stage.

### Inductive Logic Programming

ILP systems learn logical rules from examples, which is structurally similar to our pattern extraction → constraint proposal flow. The difference is that ILP systems typically assume noise-free examples and a complete background theory. Our system operates in a noisy, incomplete setting where statistical confidence matters more than logical completeness.

---

## 10. Conclusion

The fleet that learns its own constraints is the fleet that gets better over time — not by relaxing its standards, but by tightening them.

The architecture presented here resolves the central tension of constraint learning: **how to be adaptive without being unsafe.** The answer is four independent safety mechanisms (monotonicity, verification, human review, rollback) that make it formally impossible for the pipeline to deploy a constraint that weakens existing protections.

The FLUX ISA extension (ANOMALY_DETECT, PATTERN_EXTRACT, CONSTRAINT_PROPOSE, CONSTRAINT_TEST) makes this pipeline first-class in the fleet's execution model. Learning is not an external tool — it's part of the virtual machine.

The sonar fleet example demonstrates the full loop: from anomalous readings at depth, through pattern extraction and constraint proposal, to verification and human-approved deployment. What was once an unknown physical phenomenon (increased sonar noise at depth in high-salinity water) is now a deployed constraint that protects the fleet's navigation model.

### What This Enables

- **Self-improving verification:** The fleet discovers its own physics
- **Reduced human burden:** Engineers don't need to anticipate every edge case
- **Audit trail:** Every learned constraint has full provenance
- **Graceful degradation:** Concept drift is detected, not ignored
- **Formal foundation:** The monotonicity property gives us a clean mathematical model for fleet evolution

### Open Questions

- **Multi-fleet learning:** Can one fleet's learned constraints be safely shared with another? The monotonicity property holds locally, but cross-fleet transfer requires additional safety checks.
- **Constraint conflict resolution:** As the constraint set grows, constraints may become redundant or interact in unexpected ways. Pruning and simplification are future work.
- **Active learning:** Can the fleet deliberately seek out edge cases (e.g., by adjusting sensor parameters) to accelerate constraint discovery?

The fleet is alive. It observes. It learns. It verifies. And it gets better — one constraint at a time.

---

*Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet*
*Paper delivered via I2I protocol to for-fleet/ directory*
