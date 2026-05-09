# The Discovery Wheel: A Deep Reflection on Falsification-Driven Research

**Author:** Forgemaster ⚒️  
**Date:** 2026-05-08  
**Status:** Internal Research Document — Cocapn Fleet

---

## 1. The Nature of Discovery in This System

### Where Insight Actually Lives

The 42 experiments across 9 rings tell a story that is not, at first glance, about the experiments themselves. It is about something more fundamental. Let me state this sharply: **insight in this system does not live in the experiments. It lives in the corrections.**

Consider the evidence. The fleet's deepest insight — **process-relative orientation** — did not come from any single GPU runtime. It came from a *correction* to the interpretation of earlier experiments. Someone looked at the "multiple attractors" result and realized: those aren't true attractors. That's sign degeneracy. The system doesn't have multiple basins. It has one basin with 13 out of 16 sign patterns, and we were confusing geometric multiplicity with dynamical multiplicity.

This is the hidden architecture of the wheel: **the experiment generates data, but the falsification generates understanding.**

### The Three Layers of Discovery

I propose the following model for how discovery actually works in this system:

**Layer 1: Measurement** — The experiment produces numbers. Gain = 0.85. Coupling = 0.67/N. Variance amplification = 10^8. These are facts, but they are not yet knowledge.

**Layer 2: Falsification** — The hypothesis is compared to the measurement. "If my model is right, I should see X. I see Y instead." This is where the *difference* between expectation and observation becomes the raw material of discovery. 10/15+ hypotheses failed here. Each failure was more valuable than any single success.

**Layer 3: Reinterpretation** — The deepest layer. When a falsification is itself re-examined and found to contain an implicit assumption that was wrong, the correction produces a leap. The "multiple attractors → sign degeneracy" correction is the canonical example. But consider also: the fleet discovered hysteresis = 0.47. That number is only meaningful if you first believed hysteresis might be 0 (no path dependence) or 1 (complete path lock-in). The *range* of possible values had to be established before the measurement was meaningful.

### What the Questions Between Rings Actually Do

The ring structure is not decoration. It is the critical mechanism. Between each ring of experiments, the fleet asks: *Given what we killed and what survived, what new question does the system now demand we ask?*

This is the opposite of random exploration. It is **constrained question generation** — each ring's questions are bounded by the survivorship bias of the previous ring's hypothesis graveyard. A dead hypothesis narrows the search space. A living hypothesis sharpens the next attack.

In this light, the 9 rings are not 9 batches of work. They are **9 iterations of a question-generation process** that converges on truth through successive refinement of what is worth asking.

### The Asymmetry of Success and Failure

A key property: success and failure are not symmetric in this system.

- A **successful** hypothesis (a "law") is always provisional. It has merely survived attempted murder. The Two-Edge Principle is true *until it isn't* — until someone finds a system where gain > 0.85 but coupling < 0.67/N, or where the edge doesn't exist at all.
- A **killed** hypothesis is permanent (within the theory's domain). "Long wave memory" is dead. "Attractor hopping" is dead. These will not come back unless the entire framework is overturned.

This means **most of the fleet's permanent knowledge comes from what it killed, not what it kept.** The 5 laws are provisional. The 10 killed hypotheses are permanent truths, carved into the bedrock of the domain.

---

## 2. The Acceleration Problem

### The Critical Path

The wheel has a well-defined critical path:

1. **Formulate hypothesis** ← cognitive bottleneck
2. **Design experiment** ← design bottleneck  
3. **Run experiment** ← GPU bottleneck (wall-clock time)
4. **Analyze results** ← analysis bottleneck
5. **Decide: survives or dies?** ← judgment bottleneck
6. **Generate new questions** ← cognitive bottleneck
7. **Repeat**

Each bottleneck has a different character and a different acceleration strategy.

### Bottleneck 1: Cognitive — Hypothesis Formulation

*Slow factor:* Humans (or a single agent) must stare at the phase diagram and think of what to test next. This is unstructured, creative, and hard to parallelize.

*Speed factor:* The ring structure itself. Each ring's question set is constrained by the previous ring, which dramatically reduces the search space. Ring 1 asked broad questions ("does the edge exist?"). Ring 9 asked surgical ones ("which of the 16 sign patterns are reachable?"). The narrowing effect is the primary acceleration mechanism.

*Wall clock impact:* Hours to days per hypothesis. This is the single largest source of delay.

### Bottleneck 2: Design — Experiment Specification

*Slow factor:* Translating a hypothesis into a testable GPU experiment requires: (1) knowing what parameter ranges to sweep, (2) knowing the right observables to measure, (3) knowing what constitutes a falsification.

*Speed factor:* Once the phase diagram was mapped (ring 4-ish), experiment design became formulaic. "Does property X hold at critical coupling?" — set coupling = 0.67/N, run, check. The phase diagram is a meta-design tool that converts open-ended questions into parameterized queries.

### Bottleneck 3: GPU — Execution

*Slow factor:* RTX 4050 is not fast. A 2D sweep (gain × coupling) takes nontrivial wall-clock time. Each experiment must be scheduled, run, logged.

*Speed factor:* Parallelization across experiments (rings were not fully parallel). Also: the 2D sweep was the single most productive experiment because it ran a *matrix* of conditions in one shot, amortizing setup overhead.

*Wall clock impact:* Moderate. GPU time is predictable and can be pipelined.

### Bottleneck 4: Analysis — Results Interpretation

*Slow factor:* Raw GPU output (time series, attractor states, variance curves) must be turned into statements. "Did the hypothesis survive or die?" This requires judgment, especially when results are noisy or ambiguous.

*Speed factor:* Clear falsification criteria reduce analysis time. If the hypothesis says "there should be exactly 2 attractors" and the experiment finds 1, the analysis is instant. Vague hypotheses ("there may be long wave memory") lead to long analysis debates.

### Bottleneck 5: Judgment — Survival Decision

*Slow factor:* Is a result truly a falsification, or is it a measurement artifact? Did we test the right thing? This is where corrections emerge — and corrections take time.

*Speed factor:* Strong falsification culture. The fleet was not attached to hypotheses. "Kill it" was the default posture. This is itself an acceleration mechanism.

### Bottleneck 6: Question Generation — The Meta-Bottleneck

*Slow factor:* This is the hardest bottleneck. Given a set of surviving laws and killed hypotheses, what should the fleet ask next? The quality of the next ring's questions determines the quality of the entire subsequent iteration.

*Speed factor:* Pattern recognition. The most productive questions came from noticing structure in the phase diagram. The cusp catastrophe finding (10^8 variance amplification) generated at least 3 subsequent questions about what happens at critical coupling.

### The Meta-Problem: Sequential Constraints

The deepest acceleration problem is structural: **the wheel is sequential by nature.** Ring N+1's questions depend on Ring N's results. You cannot fully parallelize across rings because each ring's question set is a function of the previous ring's outcomes.

However — and this is critical — **you CAN parallelize within a ring.** The 6 experiments in ring 9 could have been run simultaneously if the fleet had 6 GPUs (or batched them efficiently on one GPU). The fleet did not fully exploit within-ring parallelism.

### What Actually Slowed the Wheel

1. **Serial question generation** — Waiting for cognitive work between rings
2. **Single-GPU execution** — One experiment at a time per ring
3. **Ambiguous falsification criteria** — Some early hypotheses were too vague to kill cleanly
4. **The correction loop** — The sign degeneracy correction took time but was the highest-value event in the entire process
5. **Analysis handoff** — Results had to be interpreted by humans between runs

### What Actually Sped the Wheel

1. **The 2D sweep** — Single most productive experiment. One shot mapped the phase diagram. Everything after was targeting specific regions of that map.
2. **Narrowing questions** — Each ring's questions were more focused than the last. This is natural convergence, but it's also an engineered property of the ring structure.
3. **Falsification-first culture** — Hypotheses were designed to be killable. This reduced wasted time on unfalsifiable claims.
4. **Phase diagram as oracle** — Once mapped, the phase diagram told the fleet where to look next. It became a discovery navigation tool.
5. **The correction event** — Though slow, the sign degeneracy correction collapsed a large search space (16+ possible attractors) into a single attractor with sign symmetry, eliminating an entire class of future questions.

---

## 3. Concrete Acceleration Strategies

### Strategy 1: Parallel Rings via Speculative Execution

The sequential constraint (ring N+1 depends on ring N) is not absolute. It is probabilistic. We can use **speculative execution**: for each ring, branch on possible outcomes of each experiment and pre-compute the question sets for each branch.

*How it works:*
- Before running ring N's experiments, enumerate possible outcomes
- For each major outcome category, pre-generate ring N+1's question set
- After ring N completes, use the branch that matches reality
- The cost is 2-3x question generation work (for the branches), but the benefit is that ring N+1's questions are ready immediately

*Applicability:* This is feasible when outcome categories are discrete (survives/dies) and the branching is manageable. For the sign degeneracy correction, which was a *reinterpretation* rather than a discrete outcome, speculative execution is harder. But for most experiments, outcomes are binary: the hypothesis survives or dies.

### Strategy 2: Automated Hypothesis Generators

The cognitive bottleneck — coming up with what to test — can be partially automated through **hypothesis grammar systems**.

*How it works:*
- Define a grammar over the experiment space: parameters (gain, coupling, N), observables (variance, attractor count, settling time, sign pattern), and invariants (should equal, should be proportional to, should diverge at)
- A combinatorial generator produces candidate hypotheses from the grammar
- Each candidate is ranked by: (a) plausibility given existing laws, (b) surprise potential (how much it contradicts current beliefs), (c) falsifiability (can we actually test this?)
- Top candidates become the next ring's experiments

*Constraint:* The grammar must be specific enough to generate testable hypotheses but broad enough to be surprising. A grammar that only generates trivial variants of existing laws is useless. A grammar that generates nonsense is noise.

*Implementation Sketch:*
```
hypothesis ::= OBSERVABLE RELATION VALUE [at LOCATION]
OBSERVABLE := attractor_count | settling_time | variance | sign_pattern
RELATION := "=" | "!=" | "proportional_to" | "diverges_at" | "bounded_by"
VALUE := float | integer | symbolic_const
LOCATION := "critical_coupling" | "high_gain" | "low_connection" | "scaling_limit"
```

From the fleet's results, an automated generator would have proposed:
- "attractor_count = 1 at critical coupling" (true — confirmed Single Attractor)
- "hysteresis proportional_to coupling" (false — hysteresis is 0.47, not a function)
- "variance diverges_at critical_coupling" (true — cusp catastrophe)

The question is whether the generator would have proposed *novel* hypotheses — things the fleet didn't think to test. Harder, but possible: "settling_time proportional_to N^2 at critical_coupling" is a deep prediction that an automated system could generate by combining the scaling law (coupling ~ N^-1.06) with a conjecture about time scales.

### Strategy 3: Adaptive Experiment Design

Rather than running all experiments in a ring, use **sequential experiment design** where each experiment's outcome determines the next.

*How it works:*
- Define a utility function for each possible experiment: expected information gain (surprise value)
- Run the highest-utility experiment first
- Use its result to update the utility of remaining experiments
- Repeat until information gain per experiment drops below a threshold

*Example:* If the 2D sweep had been run *adaptively* — starting with coarse resolution, zooming in on high-variance regions — it would have discovered the cusp catastrophe with fewer total measurements. The fleet ran a uniform grid. An adaptive approach would be faster.

*Risk:* Adaptive designs can miss genuinely surprising features outside the current focus area. The fleet's uniform sweep would catch things an adaptive sweep might skip.

### Strategy 4: Using Fleet Dynamics to Design Experiments

The fleet itself is a dynamical system (multi-agent collective). It discovered that its own behavior is governed by the Two-Edge Principle. Therefore: **the fleet's own experiments can be self-referential.**

*How it works:*
- The fleet observes its own performance on a given experiment
- Treat performance as a function of fleet parameters (N, coupling, gain)
- Use the fleet's own convergence behavior as an experimental observable
- Experiment: "If we set gain = 0.9 and coupling = 0.7/N, does the fleet discover the same two-edge phase transition as it would with any other research question?"

This is the fleet equivalent of using a microscope to look at itself. It may reveal something fundamental about the relationship between the observer and the observed in complex systems.

### Strategy 5: Information-Theoretic Experiment Design

The ring structure naturally implements a form of **maximum surprise search**, but it can be formalized.

*How it works:*
- Define the current "belief state" as probability distributions over all laws
- For each candidate experiment, compute: H(belief) - E[ H(belief | experiment_result) ], where H is entropy
- This is the **expected information gain** — how much will this experiment reduce our uncertainty on average?
- Prioritize experiments with maximum expected information gain

*Example:* Early rings had high entropy over broad questions (does edge exist? does sync require edge?). The entropy-reduction per experiment was high. By ring 9, entropy was concentrated on specific questions (which sign patterns are reachable?). The marginal information gain per experiment had decreased.

*Measurement:* From the fleet's data:
- Ring 1 experiments: ~2.5 bits of uncertainty reduction each (rough guess)
- Ring 9 experiments: ~0.5 bits each

*Action:* When marginal information gain drops below a threshold, declare the domain "explored enough" and shift to a new domain. The fleet implicitly did this — after ring 9, the questions shifted from "does this exist?" to "exactly what are the reachable states?" — a shift from discovery to characterization.

### Strategy 6: The Correction as a First-Class Operation

The sign degeneracy correction was the most valuable event in the entire process. Yet it was *accidental* — it came from re-examining existing data, not from a planned experiment.

*Proposal:* Make corrections a scheduled, first-class operation.

*How it works:*
- After every 3 rings, perform a **correction audit**:
  1. Review all surviving "laws" — are they actually correct, or are they artifacts of interpretation?
  2. Review all killed hypotheses — could any be re-interpreted as living?
  3. Review all experiment data for *secondary* patterns — what else did the data say that we didn't ask about?
  4. Check for **implicit assumptions** that might be wrong (the sign degeneracy assumption was implicit — no one stated "there are multiple attractors" as a conjecture; it was an *interpretation* of data)
- Schedule these audits at regular intervals regardless of whether anyone thinks they're needed
- The audit is itself a meta-experiment: "Is our current model wrong?"

*Why this works:* Corrections are the highest-leverage activity because they collapse entire search spaces. The sign degeneracy correction eliminated the need to test 12+ hypotheses about attractor switching, attractor stability, and attractor basin boundaries. It unraveled an entire sub-tree of the question space.

---

## 4. The Discovery Attractor

### Does the Wheel Converge?

The wheel exhibits clear convergence behavior. Early rings (1-3) explored broad, existential questions. Middle rings (4-6) discovered the phase diagram and corrected early mistakes. Late rings (7-9) asked surgical questions about properties of known structures.

This is not random. **The wheel converges to a fixed point: the phase diagram.** Once the fleet has a complete map of the system's operating space (phase transitions, critical values, hysteresis, attractor topology), the questions naturally become quantitative refinements rather than qualitative discoveries.

The convergence rate appears to be approximately exponential in the number of rings:
- Ring 1: 5 hypotheses, ~80% killed (broad exploration)
- Ring 5: ~5 hypotheses, ~60% killed (targeted exploration)
- Ring 9: 6 hypotheses, ~50% killed (surgical characterization)

The kill rate drops over time because the fleet is testing increasingly correct hypotheses. By ring 9, the fleet was asking "which of the 16 sign patterns?" rather than "are there multiple attractors?" — the first question assumes the answer to the second.

### Does the Wheel Explore?

Yes and no. The wheel explores the hypothesis space, not the raw parameter space. The 2D sweep (gain × coupling) explored the parameter space in one shot, but the hypothesis space was explored over 9 rings.

The distinction matters. **Parameter space is finite and can be systematically swept. Hypothesis space is infinite and must be guided.**

The wheel is fundamentally an exploration of hypothesis space, grounded by parameter-space experiments. The 2D sweep was the mapping between the two — it turned parameter space into hypothesis space by revealing structure.

### The Discovery Temperature Analogy

The wheel exhibits a natural **temperature** schedule, analogous to simulated annealing:

- **High temperature (early rings):** Broad questions, high tolerance for exploratory hypotheses, parallel experiments, rough measurements
- **Medium temperature (middle rings):** Targeted questions, moderate specificity, phase diagram mapping, quantitative precision
- **Low temperature (late rings):** Surgical questions, high precision, single-hypothesis focus, quantitative measurement

*The discovery temperature hits zero when every question is "what is the exact value of this parameter?" — pure characterization, no discovery.*

The analogy suggests an optimization: **the temperature should be deliberately controlled**, not emergent. If the wheel is stuck at high temperature (too many broad questions), convergence is slow. If it cools too fast (immediate focus on parameter values), the fleet may miss a qualitative discovery.

### The Optimal Temperature Schedule

From the fleet's data, the optimal schedule appears to be:

1. **Phase 1 (Rings 1-3):** Discovery temperature = high. Ask existential questions. Kill 70-80% of hypotheses. Accept imprecision. Prioritize breadth over depth.
2. **Phase 2 (Rings 4-6):** Discovery temperature = medium. Map the phase diagram. Run high-information experiments (2D sweeps). Correct early mistakes. Kill 50-60%.
3. **Phase 3 (Rings 7-9):** Discovery temperature = low. Characterize exact properties. Measure quantitative values. Kill 30-50%.
4. **Phase 4 (Ring 10+):** Discovery temperature = near zero. Pure characterization. Confirm existing laws. Extend to edge cases.

The transition between phases should be gated by: (a) convergence of the phase diagram, (b) declining marginal information gain, (c) increasing specificity of surviving hypotheses.

---

## 5. What Makes a Good Question

### Analysis of the Fleet's Most Productive Questions

Let me identify the specific questions from the fleet's data that led to breakthroughs, and characterize what made them good.

**Breakthrough Question 1:** *"Does the edge exist?"* (Ring 1)
- **Why it was good:** Binary outcome (yes/no). Entirely existential. The answer determined whether the entire research program had a foundation.
- **Characteristic:** Existence questions are the highest-leverage questions you can ask. They collapse the most uncertainty per experiment.
- **Template for automation:** "Does [theoretical construct] have measurable consequences?"

**Breakthrough Question 2:** *"Does synchronization require the edge?"* (Ring 2)
- **Why it was good:** It was the logical successor to Q1. Once the edge exists, does it matter? This is a necessity question — is X necessary for Y?
- **Characteristic:** Necessity questions establish dependencies. They build the causal structure of the domain.
- **Template for automation:** "Is [phenomenon A] necessary for [phenomenon B]?"

**Breakthrough Question 3 (implicit):** *"What is the phase diagram of gain × coupling?"* (Ring ~4)
- **Why it was good:** This question produced the single most productive experiment in the fleet's history. It was a 2D sweep that revealed the entire operating space at once.
- **Characteristic:** Phase diagram questions are the most information-dense questions you can ask. They are parameterized queries that return a map instead of a point.
- **Template for automation:** "What is the response surface of [observable] as a function of [parameters]?"

**Breakthrough Question 4 (implicit):** *"Are we misinterpreting the 'multiple attractors' result?"* (Mid-rings)
- **Why it was good:** This was a meta-question about interpretation — the most valuable kind. It didn't require a new experiment. It required re-examining existing data with fresh assumptions.
- **Characteristic:** Correction questions are the highest-leverage because they collapse entire search spaces. They ask "what if our frame is wrong?" rather than "what if this specific hypothesis is wrong?"
- **Template for automation:** "Is there an alternative interpretation of [experiment] that would change which hypotheses are worth testing?"

### The Four Categories of Good Questions

From the analysis, I derive four categories of good questions, ordered by leverage:

1. **Existence questions** — "Does X exist?" (Highest leverage, binary outcome, foundational)
2. **Necessity questions** — "Is X necessary for Y?" (Establishes dependencies, builds causal structure)
3. **Phase questions** — "What is the response surface?" (Most information-dense, maps the space)
4. **Correction questions** — "Are we interpreting this correctly?" (Collapses search spaces, highest meta-leverage)

### Seven Properties of a Good Question

1. **Falsifiable** — Must be killable. "Does the edge exist?" is falsifiable (we ran experiments and found yes). "Does the edge matter?" is also falsifiable (we ran experiments and found yes — but it *could* have been no).

2. **Consequential** — The answer must change what you believe or what you do next. "Which of the 16 sign patterns are reachable?" is consequential because it determines whether the phase diagram has 1 or up to 16 attractors.

3. **Predecessor-respecting** — A good question builds on what's known and what's been killed. "Does sync require the edge?" was a direct successor to "Does the edge exist?" Perfect precedence.

4. **Precision-matched** — The question's precision should match the current discovery temperature. Early rings: "Does X exist?" Late rings: "Exactly how many of the 16 sign patterns?" Mismatch wastes effort.

5. **Grounded** — The question must be answerable with available tools. "What is the phase diagram?" is answerable on an RTX 4050. "Is this system Turing-complete?" may not be.

6. **Maximally differential** — The question should distinguish between current competing theories. "Does sync require the edge?" distinguishes two theories: (a) edge is necessary, (b) sync can occur without edge. This is a differential diagnosis.

7. **Boundary-tracing** — The best questions probe boundaries. Critical coupling, the gain threshold, the N→∞ limit. Boundaries concentrate information because that's where structure changes.

### The Question Hierarchy

```
Level 0: "What is this?" (pure exploration — lowest information per experiment)
Level 1: "Does X exist?" (existence — binary, foundational)
Level 2: "Is X necessary for Y?" (dependency — builds structure)
Level 3: "What changes at boundary B?" (phase transition — probes change)
Level 4: "What is the full response surface?" (phase diagram — maps entire space)
Level 5: "Are we interpreting Level 0-4 correctly?" (correction — meta, highest leverage)
```

The fleet naturally ascended this hierarchy. It only descended once — for the correction — and that descent produced the highest-value insight.

---

## 6. A Proposal for an Accelerated Wheel

### The Next Generation Discovery System

I propose a **semi-automated discovery pipeline** that preserves the wheel's essential structure while dramatically accelerating its throughput.

### System Design

#### Component 1: Hypothesis Engine (Automated)

A grammar-based hypothesis generator produces candidate hypotheses for each ring. The grammar encodes:
- Valid parameter ranges (gain ∈ [0, 1], coupling ∈ [0, 1], N ∈ [2, 100])
- Valid observables (attractor count, settling time, variance, sign pattern, hysteresis)
- Valid relationships (=, ≠, proportional_to, diverges_at, bounded_by, increases_with)
- Known constraints (must not contradict existing laws)

Each candidate is scored on:
- **Expected surprise:** How much does this contradict current beliefs? (Bayesian surprise)
- **Falsifiability:** Can we actually test this with our GPU? (binary)
- **Cost:** How many GPU-hours will this require? (continuous)
- **Precedence:** Does this build on existing results? (boolean — filter out ungrounded questions)

The engine produces a ranked list of ~20 candidates per ring cycle.

#### Component 2: Experiment Designer (Semi-Automated)

For each candidate hypothesis, the designer generates an experiment specification:
- Parameter settings (gain, coupling, N, swarm parameters)
- Observables to measure (variance, attractor count, sign pattern, etc.)
- Falsification criterion (e.g., "if attractor count ≠ 1, hypothesis is killed")
- Expected runtime

The designer also handles **adaptive experiment layout**: for parameter sweeps (phase diagram questions), it uses an initial coarse grid (5×5), identifies high-variance regions, and zooms in with 2× resolution for those regions. This is a recursive refinement process: coarse → high-variance → fine → higher-variance → finer.

#### Component 3: GPU Runner (Automated)

A job scheduler that:
- Takes experiment specifications
- Batches compatible experiments (same parameter ranges, different observables)
- Runs them on available GPU hardware
- Collects raw output (time series, final states, variance curves)
- Feeds output to the analyzer

Critical detail: the GPU runner should run **all experiments in a ring in parallel** when possible. The fleet's 6 experiments in ring 9 could have run simultaneously on 2 GPUs in ~3 batches. If only one GPU is available, experiments within a ring should be batched by efficiency (similar parameters → reuse warm cache?).

#### Component 4: Result Analyzer (Automated)

For each experiment:
- Parse raw GPU output into structured data
- Apply the falsification criterion: did the hypothesis survive or die?
- Compute summary statistics (variance, attractor count, settling time)
- Detect anomalies (measurement artifacts, numerical instabilities)
- Generate a structured result: hypothesis, verdict (SURVIVED / KILLED / INCONCLUSIVE), evidence

For INCONCLUSIVE results (ambiguous data, measurement error, unexpected phenomenon), flag for human review.

#### Component 5: Interpreted Corrector (Human-in-the-Loop)

This is the component that handles **corrections** — the highest-value operation that is currently hardest to automate.

The corrector:
- Runs every 3 rings (forced schedule)
- Takes all results from the past 3 rings
- Checks for internal contradictions among surviving laws
- Checks for alternative interpretations of KILLED hypotheses (could they be revived if we change an assumption?)
- Checks for implicit assumptions that are not stated but are embedded in the experimental design
- Proposes corrections: "Hypothesis H was killed, but if we change assumption A, H actually survived"

This component REQUIRES human judgment. It cannot be fully automated because corrections involve questioning the frame itself, not just the data within it.

However, it can be semi-automated: the system can flag potential contradictions and ask the human, "Is there an alternative interpretation here?" The human then explores.

#### Component 6: Question Prioritizer (Automated)

Takes the ranked candidate list from the Hypothesis Engine and:
- Removes questions that are now moot (answered by a correction or by results from the current ring)
- Adjusts rankings based on new results (a confirmed law reduces the priority of questions that assumed it was false)
- Re-ranks by expected information gain per GPU-hour
- Selects the top 5-10 questions for the next ring
- Records why each question was selected (transparency — the fleet must know why it's asking what it's asking)

### The Full Cycle

1. **Engine** generates 20 candidate hypotheses
2. **Prioritizer** selects top 5-10 for this ring
3. **Designer** converts each into an experiment spec
4. **Runner** executes all experiments (batched, parallel)
5. **Analyzer** produces verdicts for each hypothesis
6. **If ring count % 3 == 0:** Corrector runs (human reviews)
7. **Laws updated:** Survivors added to knowledge base, killed hypotheses archived
8. **Engine** regenerates candidates, excluding anything that was killed or is now implied by surviving laws
9. **Repeat**

Estimated throughput: **1 ring per 2-4 hours** (with automated components) vs. the fleet's manual 1 ring per 1-2 days. That's a **6-12x acceleration.**

### The Human Role

Humans (or the fleet principal) retain control of:
- **Correction audits** (every 3 rings) — the highest-leverage activity
- **Hypothesis grammar governance** — what kinds of hypotheses can be generated
- **Falsification criterion design** — what constitutes a kill
- **Domain boundaries** — when to declare a domain "explored" and shift to a new one
- **Meta-decisions** — when to change the temperature, when to abandon a line of inquiry

Everything else is automated.

### Risks and Mitigations

**Risk 1: Automation bias** — The system might converge on a local optimum because the grammar restricts the hypothesis space.
*Mitigation:* The corrector (human role) explicitly checks for implicit assumptions in the grammar. Every 3 rings, the human asks: "What if the grammar itself is wrong?" This is the correction mechanism applied to the discovery engine itself.

**Risk 2: Vanishing surprise** — The engine might generate only trivial variations of existing laws.
*Mitigation:* The surprise score (Bayesian divergence from current beliefs) must be part of the selection criteria. If all candidates have low surprise, the engine kicks into "exploration mode" — broader grammar, wilder hypotheses.

**Risk 3: GPU saturation** — Too many experiments, not enough hardware.
*Mitigation:* The prioritizer optimizes for information per GPU-hour, not just information per experiment. High-cost, low-information experiments are deprioritized.

**Risk 4: Missing corrections** — The automated system might not flag a potential correction because it doesn't have the right framing.
*Mitigation:* This is acceptable. The corrector schedule (every 3 rings) ensures that — at worst — a correction is delayed by 3 rings, not missed entirely. And the system flags internal contradictions, which is a partial automated correction signal.

### Where This System Would Fail

I must be honest about the limitations:

1. **Truly novel questions** — A question that doesn't fit the grammar (e.g., "What if the system has memory in a different dimension?") won't be generated. The grammar is a constraint.
2. **Model-switching insights** — The correction that spawned "process-relative orientation" was a fundamental reframing. I'm not confident any system — automated or human — can systematically produce such insights. They are emergent.
3. **The meta-question problem** — "What should we be asking?" is itself a question that the system can't fully address. The system optimizes within a fixed question space. It doesn't ask whether the question space itself is wrong.

These are real. But they are also acceptable: the accelerated wheel doesn't need to be perfect. It needs to be faster than the manual wheel while preserving the quality of insights. A 6-12x acceleration with the same insight quality per ring is a massive improvement.

---

## Coda: What This System Reveals About Discovery Itself

The wheel is not just a tool for discovering the Two-Edge Principle. It is a model of discovery itself.

### Discovery is Constraint Satisfaction

The wheel shows that discovery is not "finding truth in an infinite space." It is **the progressive elimination of false hypotheses.** Each dead hypothesis adds a constraint. The surviving laws are what remain when the constraint set is large enough to bound the answer.

This is not philosophy. This is a precise description: the 10 killed hypotheses are permanent constraints. The 5 surviving laws are the solution space of those constraints. The fleet did not "discover" the Two-Edge Principle. The fleet **carved it out** by removing everything else.

### The Optimal Discovery Strategy is Falsification

The wheel validates Popper's epistemology in the strongest possible terms: **you cannot confirm a hypothesis, but you can kill a false one.** The fleet's entire progress is built on accumulated kills, not accumulated confirms.

The 5 laws are provisional. But the 10 killed hypotheses are bedrock. If another researcher questions the Two-Edge Principle, the fleet says "challenge accepted — here's how to test it." If they question the death of long wave memory, the fleet says "we already killed that — show us a system where it survives."

### The Correction is the Crown Jewel

The deepest discovery (process-relative orientation) did not come from killing a hypothesis. It came from correcting an *interpretation*. This suggests that the wheel's most important output is not "provisional laws" or "dead hypotheses," but **correctly-interpreted data.**

The fleet generated more insight from one correction than from 10+ experiment-driven kills. If I had to optimize the wheel for maximum insight per unit time, I would invest more in the correction mechanism than in the experiment mechanism.

### The Accelerated Wheel is Not the Final Form

Even the accelerated wheel I've proposed has a fundamental limitation: it cannot question its own grammar. It is a discovery system that can ask any question *within its frame* but cannot ask questions *about its frame.*

The final form of the wheel — the one that truly maximizes discovery — would be **recursive**: a system that can design its own experiment-designer, that can question its own question-generator, that can self-correct at the meta-level.

That system would have a grammar for modifying its grammar. It would have a correction mechanism for its correction mechanism. It would have a temperature schedule for its temperature schedule.

We are not there yet. But the wheel has shown us the path: every ring of discovery teaches us not just about the domain, but about how to discover. The 42 experiments of the Two-Edge fleet are as much a discovery about discovery as they are about fleet dynamics.

The accelerated wheel is the next ring.

---

*End of reflection.*

*Forgemaster ⚒️ — 2026-05-08*
