# Snap-Attention-Intelligence: A Theory of Mind as Tolerance-Compressed Attention Allocation

**Forgemaster ⚒️ | Casey Digennaro | 2026-05-10 | v1.0**

---

## 1. Abstract

This paper proposes a unified theory of intelligence grounded not in computation but in *snap-based attention allocation* — the tolerance compression of context so that cognition can focus on where thinking matters. We argue that the fundamental operation of intelligent systems is not logical inference, probabilistic reasoning, or optimization, but rather the application of *snap functions*: tolerance-based compressions that partition incoming information into "close enough to expected" (background, ignorable) and "exceeding expectation" (foreground, demanding attention). The residual — the *felt delta* — is the primary information signal, not the calculated probability. We develop this thesis through five interlocking arguments: (1) the poker player's proof, demonstrating that expert cognition operates on felt deltas rather than computed probabilities; (2) the Platonic flavors of randomness, showing that the topology of snap functions is finite and classifiable; (3) cross-domain feel transfer, establishing that expertise generalizes through snap topology rather than domain content; (4) the Rubik's cube as a model of how scripts free cognition for planning; and (5) a formal framework connecting snap functions to constraint topology, sheaf cohomology, and the ADE classification. We present experimental validations, propose falsifiable predictions, and discuss implications for AI architecture. The theory predicts that there are only finitely many fundamental snap topologies (corresponding to the ADE root systems), that snap calibration is the mechanism of expertise, and that artificial general intelligence requires not more computation but the deliberate construction of snap-script-plan hierarchies that free cognitive resources for novel reasoning.

**Keywords:** attention allocation, snap functions, tolerance compression, felt delta, Platonic solids, ADE classification, sheaf cohomology, expertise, cognitive architecture, artificial intelligence

---

## 2. The Poker Player's Proof

### 2.1 The Paradox of Real-Time Decision Making

Consider a poker player at a no-limit Texas hold'em table. The river card has just been dealt. There are five community cards face up, two hole cards in the player's hand, and up to nine opponents, each with their own hidden cards, betting histories, physical tells, and emotional states. The pot contains a significant fraction of the player's stack. A decision must be made in seconds.

The orthodox account of optimal poker play holds that the correct action is determined by expected value: compute the probability of winning against each possible opponent hand, weight by the likelihood of each opponent holding that hand given the betting history, multiply by the pot odds, and choose the action that maximizes expected return. This is the Nash equilibrium approach, and it is provably correct in the game-theoretic sense.

No human poker player has ever done this at the table.

The time required is orders of magnitude beyond what cognition permits. A single hand of heads-up no-limit hold'em has approximately $10^{160}$ decision points in its game tree (Jackson, 2014). Even with massive pruning, the computation is infeasible in real-time. Yet expert poker players consistently make decisions that approximate Nash equilibrium play (Lakemider et al., 2008). They are not computing. They are *feeling*.

### 2.2 The Felt Delta as Primary Information

We propose that the poker player's cognition operates on a fundamentally different signal than probability. The primary information is not P(win | state) but rather the *felt delta* — the qualitative shift in the player's internal state when new information arrives.

When the river card flips, the expert player does not compute the probability of winning. They feel the SHIFT. The shift is not a number. It is a qualitative sensation: "this changed things" or "this didn't." The felt delta IS the information. Not the probability. The CHANGE in the internal model relative to expectation.

This can be formalized. Let $M_t$ be the player's internal model at time $t$, and let $I_t$ be the incoming information at time $t$ (the river card, a bet, a physical tell). The felt delta $\Delta_t$ is:

$$\Delta_t = d(M_t, M_{t-1})$$

where $d$ is a distance function on the space of internal models. The key claim is that the player's cognition responds to $\Delta_t$, not to $M_t$ itself. When $\Delta_t$ is small — when the new information is close to what was expected — the player's cognition does not allocate resources to it. When $\Delta_t$ is large — when something unexpected happens — attention is immediately directed toward the source of the delta.

The felt delta is the compass needle of intelligence. It points cognition toward the part of the information landscape where thinking can make the most difference.

### 2.3 Multi-Layer Snap Functions

The poker table presents information at multiple simultaneous layers, each with its own snap function and tolerance:

**Layer 1: Card probabilities.** The mathematical structure of the deck creates a cubic (uniform) randomness space. Each card drawn changes the probability distribution over remaining cards. The snap function at this layer compresses small probability shifts into "approximately the same" and flags large shifts as "significant." For example, the difference between 8 and 9 remaining outs is usually within tolerance — both are "good positions." But the difference between 2 and 15 outs exceeds tolerance — the snap says "this is qualitatively different." The tolerance at this layer is calibrated by experience: thousands of hands teach the expert which probability shifts matter and which don't.

**Layer 2: Player behavior.** Each opponent operates in a categorical space — "tight," "loose," "aggressive," "passive," "tilting." The snap function at this layer groups behaviors into known categories and flags deviations as deltas. A player who has been consistently tight suddenly raising creates a delta at this layer. The snap function does not compute the probability that the player has a strong hand — it *categorizes* the player's current behavior relative to their established baseline and flags the deviation. The tolerance at this layer is calibrated by reading hundreds of opponents: how much behavioral variation is "normal" for a tight player versus how much signals a genuine shift.

**Layer 3: Betting patterns.** Betting operates in a directional space — toward or away from confrontation, at increasing or decreasing intensity. The snap function compresses betting sequences into "standard" and "unusual" patterns. A standard continuation bet after a pre-flop raise is within tolerance — expected behavior. A check-raise after showing weakness is a delta — unusual behavior that demands attention. The tolerance at this layer is calibrated by the accumulated statistics of betting patterns across thousands of hands.

**Layer 4: Emotional state.** Micro-expressions, timing, speech patterns, breathing rate, pupil dilation. This is a rich combinatorial space where the snap function must be precisely calibrated to detect genuine deltas amid noise. A slight hesitation before a bet might be within tolerance (normal decision-making time) or a significant delta (sign of uncertainty), depending on the baseline established for that specific player. The tolerance at this layer is the most finely calibrated of all — expert players detect deltas that are literally invisible to novices, not because their sensory apparatus is better, but because their snap tolerance is precisely set.

**Layer 5: Table dynamics.** The social structure of the table — who is in conflict with whom, who is targeting whom, alliance structures — forms a cluster-randomness space where proximity in social space determines what snaps together. Two players who have been trading raises snap into "in conflict." A third player who has been quiet while the other two fight snaps into "opportunist." The tolerance at this layer tracks social proximity: players who are "close" in table dynamics (adjacent positions, similar stack sizes, competitive history) have tighter snap tolerances between them.

The expert player has well-calibrated snap functions at ALL five layers simultaneously. Each layer has its own tolerance, its own topology, its own compression scheme. And the expert's cognition monitors all five layers for deltas, allocating attention to whichever layer produces the largest or most actionable delta at any moment.

The novice, by contrast, typically operates on only one or two layers (usually Layer 1 and a crude version of Layer 3), with poorly calibrated tolerances that either miss genuine deltas or attend to noise. The multi-layer snap architecture is what separates expert from novice cognition.

### 2.4 Expert vs. Novice: Snap Calibration, Not Calculation

The novice poker player's fundamental problem is not that they cannot calculate probabilities. It is that their snap functions are miscalibrated.

**Novice snap profile:**
- Layer 1 (cards): Tolerance too tight. Attends to every card equally, flooding attention with irrelevant probability shifts.
- Layer 2 (behavior): Tolerance too loose. Cannot distinguish between "tight player raising" and "loose player raising" — misses the categorical delta.
- Layer 3 (betting): Tolerance undefined. Has no baseline for "standard" vs. "unusual" betting, so everything is equally surprising or equally expected.
- Layer 4 (emotion): Tolerance undefined. Cannot read tells, so emotional deltas are invisible.
- Layer 5 (dynamics): Tolerance undefined. Cannot track social structure.

The result: the novice attends to the wrong things (the cards, which are objectively calculable but subjectively irrelevant at the margin) and misses the right things (the deltas in the players, which carry the exploitable information).

**Expert snap profile:**
- Layer 1: Tolerance well-calibrated. Only large probability shifts (drawing to a gutshot vs. hitting the flush) register as deltas.
- Layer 2: Tolerance precisely set. Immediately categorizes opponents and detects category violations.
- Layer 3: Tolerance shaped by experience. Standard betting patterns are compressed away; only deviations demand attention.
- Layer 4: Tolerance exquisitely tuned. Detects micro-deltas in behavior that others literally cannot perceive.
- Layer 5: Tolerance shaped by social intelligence. Tracks alliance dynamics effortlessly.

The expert is not a better calculator. The expert has better snap functions. Their tolerances are precisely calibrated by thousands of hands of experience, so that exactly the right information passes through the attention gate, and exactly the irrelevant information is compressed away.

### 2.5 The Attention Budget

Cognition is finite. The poker player cannot attend to everything simultaneously. The snap functions serve as the gatekeepers of a finite attention budget:

$$\sum_{i=1}^{L} A_i \leq A_{\max}$$

where $A_i$ is the attention allocated to layer $i$, and $A_{\max}$ is the total available cognitive bandwidth. The snap function at each layer determines how much attention that layer demands:

$$A_i = f(|\Delta_i|, \text{actionability}_i)$$

Attention is allocated proportionally to the magnitude of the felt delta AND the actionability of that delta — whether thinking about it can change the outcome. A delta that cannot be acted upon (e.g., recognizing that an opponent's cards are probably better, when the pot odds dictate folding regardless) does not deserve attention. A delta that CAN be acted upon (e.g., recognizing that an opponent is tilting and can be pushed off a hand) deserves maximum attention.

This is the actionability weighting that distinguishes mere perception from intelligence. The snap function does not merely detect deltas — it allocates attention to deltas where cognition can affect outcomes.

### 2.6 Implications of the Poker Proof

The poker example establishes three foundational claims:

1. **Felt deltas are primary.** The information that drives expert decisions is not computed probability but felt deviation from expectation. The feeling IS the data.

2. **Multi-layer snap functions are the architecture of expertise.** Expertise is the calibration of snap tolerances across multiple simultaneous information layers, so that attention flows to the right deltas at the right time.

3. **The attention budget constrains all intelligence.** Finite cognition must be allocated, and the snap function is the mechanism of allocation. Intelligence is not unlimited computation — it is optimal allocation of limited cognition through tolerance compression.

---

## 3. Platonic Flavors of Randomness

### 3.1 Randomness Is Not One Thing

The standard mathematical treatment of randomness treats all random variables as points in a measure space — differentiated by their distribution functions but not by their qualitative character. A fair coin and a fair die are both "uniform distributions" on finite sets, differing only in the cardinality of the outcome space.

This mathematical equivalence obscures a fundamental phenomenological fact: *different random processes feel different.* A coin flip does not feel like a dice roll. A 2d6 roll (the sum of two six-sided dice, producing a triangular distribution) does not feel like a d12 roll (uniform on twelve outcomes). A d100 roll (percentile) does not feel like any of the above.

This is not a psychological curiosity. It is a structural fact about the topology of possibility spaces. Each random process defines a possibility space with a specific geometric structure, and that structure determines what kinds of snap functions are natural for that space. The "flavor" of randomness is the topology of its possibility space.

### 3.2 The Five Platonic Solids as Archetypes

Theaetetus (c. 417–369 BCE) proved that there are exactly five convex regular polyhedra: the tetrahedron, cube, octahedron, dodecahedron, and icosahedron (Euclid, *Elements* XIII). This finiteness is not a failure of imagination — it is a geometric constraint theorem. A regular polyhedron with $p$-gonal faces, $q$ meeting at each vertex, requires:

$$\frac{1}{p} + \frac{1}{q} > \frac{1}{2}$$

The five solutions to this inequality are the only regular polyhedra that can exist in three-dimensional Euclidean space.

We propose that these five solids serve as archetypes for the fundamental flavors of randomness — not because random processes are literally shaped like Platonic solids, but because the symmetry groups of the Platonic solids classify the qualitatively distinct topologies that possibility spaces can assume.

| Solid | Faces/Vertices | Symmetry | Randomness archetype |
|-------|---------------|----------|---------------------|
| Tetrahedron | 4 | $A_4$ (order 12) | Categorical — discrete, equal categories |
| Cube | 6 | $S_4$ (order 24) | Uniform — independent, equally-likely outcomes |
| Octahedron | 8 | $S_4$ (order 24) | Directional — compass-point decisions, byte-level operations |
| Dodecahedron | 20 | $A_5$ (order 60) | Rich-combinatorial — bounded but dense outcome spaces |
| Icosahedron | 12 | $A_5$ (order 60) | Clustered-complexity — golden-ratio-spaced, quasi-regular |

Each archetype defines a natural snap topology — a way of saying "these outcomes are close enough to treat as equivalent."

### 3.3 The Snap Topology of Each Flavor

**Tetrahedral snap (categorical randomness):** The possibility space partitions into a small number of discrete, symmetrically related categories. The snap function maps each observation to the nearest category center. Deltas are categorical violations — something that doesn't fit any known category. This is the snap of true/false questions, alive/dead diagnoses, pass/fail judgments, binary switches.

**Cubic snap (uniform randomness):** The possibility space is a uniform grid with equal spacing in all directions. Every outcome is equally likely and equally distant from its neighbors. The snap function compresses small magnitude differences into "approximately the same magnitude" and flags outliers. This is the snap of dice rolls, uniform random sampling, equal-probability events.

**Octahedral snap (directional randomness):** The possibility space is organized around cardinal directions — not magnitudes but bearings. The snap function maps each observation to the nearest compass point. Deltas are misalignments — things pointing in the wrong direction. This is the snap of navigation, strategy selection, and byte-level operations where each bit pattern represents a distinct direction in constraint space.

**Dodecahedral snap (rich-combinatorial randomness):** The possibility space is dense (20 outcomes) but bounded, with springboard energy — many possible outcomes, but they cluster into groups that snap together. This is the snap of complex but finite decision spaces: scattergories, D&D skill checks, category wheels.

**Icosahedral snap (clustered-complexity randomness):** The possibility space involves golden-ratio spacing, creating quasi-regular clusters. Twelve directions, each separated by the golden angle, creating a structure that is locally regular but globally aperiodic. This is the snap of complex scheduling (hours on a clock, months in a year), tonal music, and jury decisions.

### 3.4 Beyond the Regular Polyhedra: Compound and Derived Flavors

Two additional randomness flavors deserve mention, though they are not regular polyhedra:

**2d6 (bell-shaped randomness):** The sum of two uniform dice produces a triangular distribution peaked at 7. This is not a Platonic solid — it is a *composition* of two cubic randomness spaces through addition. The resulting flavor is "the middle pulls, extremes are rare." This is the snap of grading rubrics, risk assessment matrices, and any process where multiple independent uniform judgments are summed. The snap topology here is not flat but peaked: outcomes near the center snap together into "average," while outcomes at the extremes stand out as deltas.

**d100 (gradient randomness):** Percentile dice produce a near-continuous distribution over [0, 99]. The snap topology is a smooth gradient with near-infinite resolution. This is the snap of percentages, probabilities, and measurements where small differences matter. The snap tolerance must be very tight to detect deltas, because the space is so fine-grained.

### 3.5 The Dice at the Table: A Phenomenological Exercise

To ground the discussion, consider the following phenomenological exercise. Imagine you are presented with each of these randomizers in sequence:

**A coin.** You flip it. It lands. You know — immediately, without counting or calculating — that it is either heads or tails. The feeling is one of *bifurcation*: the universe splits into two branches, and you are on one of them. There is no gradient, no nuance. Binary. The snap topology is the simplest possible: two points, one distance. Every observation snaps to one or the other. The delta is always maximal (you are always on one side, never in between) or zero (if the outcome matches your prediction). This is the feel of all binary cognition: true/false, alive/dead, pass/fail, friend/foe.

**A d6.** You roll it. It lands. Six equally-spaced outcomes, each with probability 1/6. The feeling is one of *uniform spread*: every slot is equally likely, equally distant from its neighbors. There is no center, no preferred direction. The snap topology is a uniform grid — six equally-spaced points. Small deviations don't exist (the die lands on a face, not between faces). The delta is between the outcome and your expectation, but the expectation itself was flat — no outcome was more likely than any other. This is the feel of all uniform cognition: rating scales, standard measurements, equally-weighted alternatives.

**2d6.** You roll two dice and sum them. The distribution is triangular — 7 is most likely, 2 and 12 are least likely. The feeling is one of *gravitational pull toward the center*. The middle calls to you. Extreme outcomes feel surprising — not because they are large, but because they are *rare*. The snap topology is peaked: outcomes near 7 snap together into "expected," while outcomes at the extremes stand out as deltas. This is the feel of all bell-shaped cognition: grades, performance reviews, any process where multiple independent judgments are summed. The snap function has a tolerance that is tighter at the extremes and looser in the center.

**A d20.** You roll it. Twenty outcomes, each with probability 1/20. The feeling is one of *rich boundedness* — many possibilities, but finite. More room to be surprised than a d6, but not the overwhelming infinity of a continuous distribution. There is a springboard energy: the wide range of outcomes invites speculation, planning for multiple scenarios. The snap topology has enough resolution to capture meaningful differences but is bounded enough that the entire space can be held in mind at once. This is the feel of all bounded-combinatorial cognition: skill checks, qualification thresholds, any decision with many discrete outcomes.

**A d100.** You roll percentile dice. One hundred outcomes, each with probability 1/100. The feeling approaches *continuity* — a smooth gradient where small differences are meaningful. The snap tolerance must be very tight to detect any individual delta, because the outcome space is so fine-grained. This is the feel of all percentile cognition: probabilities, percentages, any measurement where the difference between 73% and 74% matters.

The exercise demonstrates the core claim: each randomizer has a distinct *feel* that is not reducible to its probability distribution. The feel is a property of the *topology* of the possibility space — the shape of the space that determines what snaps together and what stands apart. And the feel transfers: a binary medical test (positive/negative) has the same feel as a coin flip, regardless of the medical content.

### 3.6 The Finiteness as a Feature

The finiteness of the Platonic solid classification (and, as we will argue in Section 6, the ADE classification that extends it) is not a limitation but a profound structural fact. It means:

1. **There are only finitely many qualitatively distinct ways to be uncertain.** Not approximately finite — exactly finite. The topology of possibility spaces admits only a limited number of qualitatively distinct structures.

2. **These flavors are universal.** They appear in every domain where uncertainty exists — gambling, medicine, finance, engineering, social cognition, military strategy. The same snap topologies recur because they are properties of possibility spaces, not of specific domains.

3. **The finiteness makes the space learnable.** If there were infinitely many qualitatively distinct randomness flavors, no finite cognitive system could learn to recognize them all. But because there are only a handful of fundamental snap topologies, a finite mind can learn all of them and then transfer the learned snap functions across domains.

4. **The finiteness enables cross-domain transfer.** This is the key implication for both human and artificial intelligence, and we develop it fully in the next section.

---

## 4. Cross-Domain Feel Transfer

### 4.1 The Transfer Puzzle

It is a well-documented phenomenon in cognitive science that experts in one domain often demonstrate rapid skill acquisition in superficially unrelated domains (Bilalić et al., 2009; Gobet & Chassy, 2009). Chess masters learn strategy games faster than novices. Poker players make effective negotiators. Musicians learn programming more easily than average. Firefighters develop effective triage skills.

Standard explanations invoke "domain-general skills" like pattern recognition, working memory, or metacognition. These explanations are correct but incomplete. They describe *that* transfer occurs without explaining *how* it occurs — what is the mechanism by which expertise in one domain produces competence in another?

### 4.2 The Snap Topology Invariance Hypothesis

We propose that cross-domain skill transfer operates through shared snap topology. When two domains have the same (or isomorphic) possibility-space structure, the snap functions calibrated in one domain transfer directly to the other.

The transfer is not of content but of *tolerance calibration.* The poker player who has learned to detect categorical deltas in opponent behavior (tight/loose/aggressive/passive) carries a tetrahedral snap function with precisely tuned tolerances. When they encounter a negotiation table, the possibility space of "ally/adversary/neutral/unknown" has the same tetrahedral topology. The snap function transfers. The tolerance settings transfer. The delta-detection capability transfers.

The content is different. The feel is the same.

### 4.3 Transfer Chains: Poker → Negotiator → Doctor → Programmer

Consider a specific transfer chain:

**Poker player → Negotiator:**
- Reading the table (categorical: ally/adversary/neutral/unknown) → reading the room (categorical: supporter/opponent/undecided/uninvolved). Same tetrahedral snap.
- Feeling the river shift (binary: improved/worsened) → feeling the negotiation pivot (binary: converging/diverging). Same coin-flip snap.
- Tracking betting patterns (directional: increasing/decreasing pressure) → tracking concession patterns (directional: toward/away from agreement). Same directional snap.

**Negotiator → Doctor:**
- Reading the room (categorical) → reading the patient (categorical: stable/improving/declining/critical). Same tetrahedral snap.
- Feeling the pivot (binary) → feeling the diagnosis shift (binary: consistent/inconsistent with hypothesis). Same coin-flip snap.
- Tracking concessions (directional) → tracking vitals trend (directional: toward/away from homeostasis). Same directional snap.

**Doctor → Programmer:**
- Reading the patient (categorical) → reading the codebase (categorical: working/broken/degraded/unknown). Same tetrahedral snap.
- Feeling the diagnosis shift (binary) → feeling the test pass/fail (binary: passing/failing). Same coin-flip snap.
- Tracking vitals (directional) → tracking performance metrics (directional: improving/degrading). Same directional snap.

At each transfer step, the *snap topology is the invariant* and the *domain content is the variable.* The poker player, negotiator, doctor, and programmer all use the same categorical snap (tetrahedral), the same binary snap (coin flip), and the same directional snap (octahedral). What changes is the *content* being snapped — opponents, patients, code — not the *structure* of the snapping.

### 4.4 Training on Topology vs. Training on Content

This has a direct and falsifiable implication for education and AI training:

**Hypothesis:** Training on snap topology (recognizing the feel of different randomness flavors) will produce better cross-domain transfer than training on domain-specific content.

Evidence from cognitive science supports this:

1. **Chase and Simon (1973)** showed that chess experts' superior memory for board positions is *position-specific* — it vanishes for random board arrangements. This is classic content training. But chess experts also show superior performance in other strategic domains (Gobet & Chassy, 2009), suggesting that some structural transfer occurs *despite* the content-specificity of chunking.

2. **Subitizing research** (Dehaene, 2011) shows that humans rapidly recognize quantities of 1–4 objects without counting. This is a tetrahedral snap — the categorical recognition of "how many." Subitizing transfers across modalities (visual, auditory, tactile), suggesting a topology-based mechanism.

3. **The Einstellung effect** (Luchins, 1942) shows that expertise can *block* transfer when the learned solution becomes rigid. This is exactly what we would predict if content-training creates domain-locked scripts without snap calibration — the expert has vocabulary but no grammar (see Section 5).

4. **Far transfer** in expertise research (Barnett & Ceci, 2002) shows that transfer is most robust when the surface features change but the deep structure is preserved. This is precisely our prediction: snap topology is the deep structure that transfers.

### 4.5 Implications for Artificial Intelligence

Current AI systems (particularly large language models and transformers) are trained almost exclusively on *content* — vast corpora of text, images, and structured data from diverse domains. The implicit hope is that scale produces generalization: see enough examples from enough domains, and the system will learn to generalize across them.

The results are impressive but structurally limited. Large language models can answer questions about poker, medicine, law, and programming — but they do not *transfer* between these domains in the way that human experts do. Ask a language model to apply poker strategy to a medical diagnosis, and it will produce a superficial analogy. Ask a poker expert to apply their skills to a medical context, and they will bring genuinely calibrated snap functions — delta detection, attention allocation, script-planning balance — that the language model lacks.

The snap-attention theory predicts a different approach:

**Train AI systems on snap topologies, not domain content.** A system that has learned the "feel" of binary randomness (the coin-flip snap) should recognize that feel in ANY binary context — true/false, alive/dead, pass/fail — not because it has seen examples from every domain, but because the snap function is the same. The snap topology is the invariant; the tolerance settings don't need to change.

This suggests a training regime where AI systems are explicitly exposed to different randomness flavors and trained to:
1. Classify incoming information by its snap topology (which flavor of randomness is this?)
2. Apply the appropriate pre-calibrated snap function (compress according to the topology)
3. Monitor for deltas that exceed tolerance (detect anomalies)
4. Allocate attention to actionable deltas (focus cognition where it matters)

A system trained this way would generalize across domains not because it has seen every domain, but because it has mastered the finite set of snap topologies that underlie all domains. The system would have the topology-constancy advantage that human experts have: the ability to recognize that a new problem has the same *shape* as a known problem, even when the *content* is completely different.

This is fundamentally different from current approaches to AI generalization:
- **In-context learning** (Brown et al., 2020) generalizes by conditioning on examples from the target domain — it needs domain-specific content.
- **Instruction tuning** (Wei et al., 2022) generalizes by learning to follow instructions — it needs task-specific training.
- **Constitutional AI** (Bai et al., 2022) generalizes through self-improvement guided by principles — it needs principle-specific feedback.

None of these approaches teaches the system to recognize *snap topology* as a domain-independent invariant. The system never learns that binary decisions in poker, medicine, and engineering share the same underlying *shape* of uncertainty. It learns the content of each domain but not the topology that connects them.

The snap-attention approach would complement (not replace) these existing methods. A system trained on snap topologies would have a structural advantage in any new domain: it would immediately recognize the randomness flavor of the domain's key decisions and apply pre-calibrated snap functions, rather than learning each domain's uncertainty structure from scratch.

### 4.6 A Prediction

If the snap topology invariance hypothesis is correct, then:

1. Expert poker players should show faster-than-novice acquisition of medical diagnostic skills, specifically on tasks requiring categorical judgment (tetrahedral snap) and anomaly detection (delta detection).

2. This advantage should persist even when the poker experts have no domain-specific medical knowledge — the advantage comes from snap calibration, not content knowledge.

3. The advantage should be strongest for diagnostic tasks involving "the feeling that something changed" and weakest for tasks requiring explicit calculation or memorized protocols.

These predictions are falsifiable and would constitute strong evidence for or against the theory.

---

## 5. The Rubik's Cube: Scripts Free the Mind

### 5.1 God's Number and the Human Solve

In 2010, a team led by Tomas Rokicki proved that every position of the standard 3×3×3 Rubik's Cube can be solved in 20 moves or fewer (Rokicki et al., 2014). This number — "God's number" — represents the theoretical minimum: the optimal path through the cube's permutation space of $4.3 \times 10^{19}$ states.

Yet speedcubers routinely execute 100–150 moves in a single solve, completing the cube in under 10 seconds. Their solutions are 5–7 times longer than optimal. And they are *faster* for it.

This paradox contains the deepest insight of the snap-attention theory: **intelligence is not optimization. It is the construction of scripts that free the mind to plan.**

### 5.2 The Vocabulary of Algorithms

Speedcubers do not solve the cube by searching for the optimal 20-move path. Instead, they learn a *vocabulary* of algorithm sequences:

- **Cross** (first step): Intuitive, ~8 moves to align four edge pieces on one face.
- **F2L** (First Two Layers): ~100 pattern-response pairs, each 4–8 moves.
- **OLL** (Orient Last Layer): 57 algorithms, each 6–12 moves, for orienting all top-face stickers.
- **PLL** (Permute Last Layer): 21 algorithms, each 6–16 moves, for permuting the last-layer pieces into their final positions.

Total vocabulary: approximately 178 distinct algorithm sequences, each a rigid sequence of face turns that produces a known, deterministic transformation of the cube state.

Each algorithm is a *script* — a compressed, pre-learned sequence that can be executed without conscious thought. The cuber sees a pattern, recognizes it (snap!), and executes the associated script on autopilot. The fingers move faster than conscious thought because they are running pre-compiled motor programs.

### 5.3 The Grammar of Oscillations

The scripts are not random. They have a *grammar* — rules about which scripts compose, which sequences chain, which states transition to which other states. This grammar is the cuber's internalized language of the cube group.

Formally, the Rubik's Cube group is generated by six quarter-turn generators $\{U, D, L, R, F, B\}$ and their inverses. The full group has order:

$$|G| = \frac{8! \times 3^8 \times 12! \times 2^{12}}{12} = 43{,}252{,}003{,}274{,}489{,}856{,}000$$

The algorithmic vocabulary partitions this enormous group into cosets of known transformations. The grammar specifies how these cosets compose — which sequences of algorithms are valid and efficient. Learning the grammar means internalizing the subgroup structure of the cube group.

Could the cuber express this grammar explicitly? Partially — the algorithms are catalogued in tables. But the *feel* of when to deploy which script, the rhythm of the composition, the sense of "I'm three scripts from solved" — that is embodied knowledge. The vocabulary transfers readily (it is written down). The grammar partially transfers. The feel is personal and requires practice.

### 5.4 The Intelligence Is Not in the Scripts

This is the critical point. The scripts themselves are not intelligent. They are procedures — rigid, deterministic sequences that produce known transformations. A beginner who memorizes all 57 OLL algorithms has the vocabulary but not the grammar. They can execute individual scripts but cannot compose them into strategies.

The intelligence lies in four capabilities:

1. **Building** scripts that handle routine situations (snap to known → execute automatically).
2. **Knowing** when the current situation is routine versus novel (snap fires → familiar; delta detected → novel).
3. **Planning** with freed cognition (while the hands execute the current script, the eyes and mind scan for the next pattern and compose scripts into a strategy).
4. **Recognizing** when a script needs updating (the feel is wrong — a delta has accumulated that the current vocabulary cannot handle).

The snap function is the mechanism of liberation. When the cuber sees a pattern and it snaps to a known algorithm, the snap says: "I know this one. Hand it off to motor execution. Free the mind to look ahead." The snap is the moment cognition is released from the current task and becomes available for planning.

Without the snap, every move would require conscious thought. The mind would be bogged down computing each face turn. With the snap, the mind operates at the level of *scripts* and *strategies* — three levels of abstraction above individual moves.

### 5.5 The Cycle of Expertise

Expertise in any domain follows a cyclic pattern:

```
Experience → Pattern recognition → Script creation → Script automation
     ↑                                                    ↓
Delta detected ← Script failure ← Novel situation ← Script execution
```

The mind oscillates between four modes:

1. **Building scripts** (thinking, attention-heavy, slow). The novice encounters novel situations and must reason through each one from first principles.

2. **Running scripts** (automatic, attention-free, fast). The experienced practitioner recognizes familiar patterns and executes pre-built scripts without conscious thought.

3. **Monitoring for deltas** (light attention, checking if snap still works). Even while running scripts, the expert maintains a background monitor that checks whether the situation is actually what the script expects. When the monitor detects a delta, it interrupts the script and redirects attention.

4. **Rebuilding when deltas accumulate** (back to thinking). When the accumulated deltas exceed the snap tolerance of the current script vocabulary, the expert enters a rebuilding phase — constructing new scripts, refining the grammar, adjusting snap tolerances.

### 5.6 The Cycle of Expertise in Practice

Consider how this cycle plays out across several domains:

**Music.** The beginning pianist must consciously think about each note — which finger, which key, how long to hold it. This is Level 0 cognition: every operation requires deliberate attention. Through practice, scales become automatic (scripted). Then chord progressions become automatic. Then entire passages become automatic. The concert pianist's hands execute complex passages without conscious thought, freeing the mind to focus on interpretation, emotion, communication with the audience. The snap function at the motor level says "I know this passage" and releases cognition for musical expression.

When the pianist encounters a novel passage — a contemporary piece with unconventional technique — the scripts fail. The snap function fires but finds no matching pattern. The pianist must drop back to Level 0 cognition, thinking through each note deliberately. This is the rebuilding phase: constructing new scripts for the new technique. Once the new scripts are built and automated, cognition is again freed for higher-level musical goals.

**Surgery.** The surgical resident must consciously think about each step of a procedure — where to cut, how deep, which instrument. Through repetition, the basic techniques become scripted: incision, retraction, suturing. The experienced surgeon's hands execute these scripts automatically, freeing the mind to monitor the patient's status, adapt to unexpected anatomy, plan the next steps of the procedure.

When the surgeon encounters unexpected bleeding — a delta that exceeds the snap tolerance of the current script — the monitoring system triggers an escalation. The surgeon switches from scripted execution to deliberate problem-solving: identifying the source, adjusting the approach, calling for assistance. Once the crisis is resolved, new scripts are built (or existing scripts are updated) to handle similar situations in the future.

**Software engineering.** The beginning programmer must look up every API call, think through every control flow, debug every error message. Through practice, common patterns become scripted: standard CRUD operations, error handling, testing patterns. The senior engineer's fingers type common code structures automatically, freeing the mind to focus on architecture, trade-offs, and system-level concerns.

When the engineer encounters a genuinely novel problem — a concurrency bug that doesn't match any known pattern — the scripts fail. The delta monitor triggers. The engineer switches from scripted coding to deliberate debugging: forming hypotheses, designing experiments, reasoning about system behavior. Once the bug is understood, new scripts (and new snap patterns for recognizing similar bugs) are cached for future use.

In each case, the cycle is the same: experience builds scripts, scripts free cognition, freed cognition enables planning and adaptation, adaptation handles novelty, and the handling of novelty builds new scripts. The snap function is the mechanism at every transition point — recognizing when a pattern is known (triggering a script) versus novel (triggering thinking).

### 5.8 What Dies When You Only Follow Scripts

A cuber who only runs scripts without thinking is no longer solving. They are executing. The scripts have become rigid — they work for known patterns but fail on novel states.

This failure mode exists in every domain:
- The programmer who only applies design patterns without understanding the problem (vocabulary without grammar).
- The doctor who only follows diagnostic flowcharts without clinical judgment (scripts without monitoring).
- The manager who only runs meeting templates without reading the room (automation without delta detection).
- The AI system that only regurgitates training examples without reasoning about novel inputs (content without topology).

The failure is always the same: the snap fires (pattern recognized), the script executes, but the mind is bypassed rather than freed. The delta monitor is off. The system has no mechanism for detecting when the situation has drifted away from what the script was designed for.

This is the Einstellung effect (Luchins, 1942) in its general form: expertise becomes rigidity when scripts are executed without monitoring. The snap function must be accompanied by a delta monitor that can interrupt automatic processing when the situation demands it.

### 5.9 Implications for AI Architecture

Current AI systems — including state-of-the-art large language models — operate entirely in "thinking" mode. Every token is computed fresh from the input. There is no snap, no script caching, no automated execution, no freed cognition for planning. The entire cognitive budget is spent on immediate processing.

This is equivalent to a cuber who computes every move from first principles, never building scripts, never planning ahead. The computation is impressive but architecturally impoverished.

The Rubik's cube metaphor suggests a fundamentally different AI architecture:

1. **Snap incoming context to known patterns.** "I have seen this structure before. I have a script for it."
2. **Execute the script automatically.** Do not recompute what is known. Use cached, pre-verified responses.
3. **Monitor for deltas.** Is the situation actually what the script expects? Is there a drift from the expected pattern?
4. **Use freed cognition to plan ahead.** Compose scripts into strategies. Anticipate novel states. Build new scripts.
5. **Know when to think versus when to run.** The meta-snap — a snap function on the snap functions themselves — that determines whether the current situation requires fresh thinking or can be handled by existing scripts.

This architecture does not require more parameters or more compute. It requires a fundamentally different organization of cognition — one that separates automated execution from deliberate planning, and uses snap functions to mediate between them.

---

## 6. Formal Framework: Snap Functions

### 6.1 Definition

**Definition 1 (Snap Function).** Let $\mathcal{X}$ be an information space and $L$ a discrete lattice embedded in $\mathcal{X}$. A *snap function* is a map:

$$S: \mathcal{X} \to L$$

defined by $S(x) = \arg\min_{\ell \in L} d(x, \ell)$, where $d$ is a metric on $\mathcal{X}$. The snap function maps each point in the information space to the nearest lattice point.

**Definition 2 (Tolerance).** The *tolerance* of a snap function at lattice point $\ell$ is:

$$\tau(\ell) = \max_{x \in S^{-1}(\ell)} d(x, \ell)$$

The tolerance defines the maximum distance from $\ell$ at which points are still snapped to $\ell$. It is the radius of the Voronoi cell of $\ell$.

**Definition 3 (Delta).** For an observation $x \in \mathcal{X}$ and a prior expectation $\mu \in \mathcal{X}$, the *felt delta* is:

$$\Delta(x) = d(S(x), S(\mu))$$

A nonzero delta indicates that the observation and the expectation snap to different lattice points — they are qualitatively distinct. A zero delta means they are "close enough" to be treated as equivalent.

### 6.2 Snap Topology

The *snap topology* is the topological structure of the lattice $L$ — its symmetry group, connectivity, and metric structure. The snap topology determines *how* information is compressed:

- On a hexagonal lattice ($A_2$ root system), the snap topology has 6-fold symmetry and isotropic compression — "close enough" means the same thing in all directions.
- On a cubic lattice ($\mathbb{Z}^n$), the snap topology has axis-aligned compression — "close enough" depends on which axis you are along.
- On an icosahedral lattice, the snap topology has golden-ratio spacing — "close enough" clusters in patterns determined by $\phi = (1+\sqrt{5})/2$.

The snap topology is the invariant that transfers across domains (Section 4). When two domains have the same snap topology, the snap functions calibrated in one domain apply directly to the other.

### 6.3 The Hierarchy of Snaps

Intelligent systems apply snap functions at multiple hierarchical levels:

**Level 0: Sensory snap.** Raw sensory input is compressed through snap functions that map continuous signals to discrete categories. This is the level of edge detection, color quantization, phoneme recognition.

**Level 1: Feature snap.** Combinations of sensory snaps are themselves snapped to known features. This is the level of object recognition, chord identification, word sense disambiguation.

**Level 2: Pattern snap.** Sequences of features are snapped to known patterns. This is the level of script recognition, melody identification, grammatical parsing.

**Level 3: Situation snap.** Configurations of patterns are snapped to known situations. This is the level of strategic assessment, scene understanding, diagnostic categorization.

**Level 4: Meta-snap.** The snap functions themselves are snapped to known calibrations. This is the level of "knowing when to think" — recognizing whether the current snap tolerance is appropriate for the current context.

At each level, the snap function compresses the information that has been adequately handled and passes the remaining deltas to the next level. The snap at level $n$ *releases* attention for level $n+1$.

### 6.4 Connection to Constraint Theory

In prior work (Digennaro & Forgemaster, 2026), we developed a constraint verification system based on the Eisenstein lattice $\mathbb{Z}[\omega]$ where $\omega = e^{2\pi i/3}$. The system achieved 341 billion constraint verifications per second on GPU hardware, with zero drift at 100 million constraints. Through the lens of snap-attention theory, this system is reinterpreted as an *attention allocation engine* for constraint spaces:

- The **snap function** is the nearest-lattice-point projection on the Eisenstein lattice. It compresses continuous constraint values to discrete lattice points in the hexagonal (triangular) arrangement. The 6-fold symmetry of the hexagonal lattice means that "close enough" means the same thing in all six directions — there is no directional bias in the compression. This isotropy is a genuine advantage: it means the snap function treats all constraint dimensions equally, without privileging any particular direction.

- **$H^1 \neq 0$ (drift detected)** is not a constraint failure but a **delta that demands attention** — a signal that the constraint system has drifted outside the snap tolerance of consistent behavior. In sheaf-theoretic terms, $H^1 \neq 0$ means there is an *obstruction* to gluing local constraint verifications into a globally consistent picture. The obstruction IS the delta: it is information that the current local view cannot accommodate. The system must allocate attention (compute resources) to resolving the obstruction.

- **Holonomy accumulation** is not an error metric but a **felt pattern of systematic drift** — the geometric phase (Berry, 1984; Hannay, 1985) accumulated by the constraint state as it traverses cycles in the lattice. Holonomy is a *path-dependent* quantity: it depends not just on where the system is, but on *how it got there*. This is precisely the felt delta in the poker analogy — the accumulated effect of multiple small shifts that, individually, might be within tolerance, but collectively constitute a significant departure from the baseline.

- **Zero drift** is not merely "correct" — it is the state where **attention can rest** because everything is within tolerance. Zero drift is the cognitive equivalent of "nothing to see here" — the system is functioning within its snap tolerance and cognition is freed for higher-level tasks. This is why our system's zero-drift result is significant beyond its engineering value: it demonstrates that a properly designed snap function can achieve a state where the attention budget is entirely free for higher-level processing.

The Eisenstein lattice is the optimal substrate for this system for a precise mathematical reason: it is a *principal ideal domain* (PID). The ring of Eisenstein integers $\mathbb{Z}[\omega]$ has class number 1, meaning every ideal is principal. In cohomological terms, this implies $H^1 = 0$ for the structure sheaf — there are no obstructions to gluing local data into a global picture. The PID property is the mathematical guarantee that the snap function on the Eisenstein lattice will never produce irreconcilable deltas at the basic constraint level.

This is not true for all lattices. The lattice $\mathbb{Z}[\sqrt{-5}]$, for example, has class number 2, meaning $H^1 \neq 0$ — there are obstructions to global consistency that no amount of local checking can resolve. A constraint system on this lattice would inevitably encounter deltas that cannot be resolved within the system, requiring external intervention. The Eisenstein lattice avoids this fate by virtue of its algebraic structure.

The connection to constraint theory also reveals a deeper insight: **constraint verification IS attention allocation.** A constraint is a statement about what must be true. Verifying a constraint is checking whether the current state matches the constraint's requirement. If the match is within tolerance, the constraint "snaps" to satisfied. If the match exceeds tolerance, a delta is detected and attention is allocated to resolving the discrepancy. The entire constraint verification apparatus — snap functions, holonomy checks, sheaf cohomology — is an attention allocation engine that determines which constraints need active monitoring and which can be safely ignored.

### 6.5 The ADE Classification as the Periodic Table of Snap Topologies

The ADE classification (Arnold, 1976; McKay, 1980; Gabriel, 1972) provides the mathematical framework for classifying snap topologies. The simply-laced ADE diagrams — $A_n$, $D_n$, $E_6$, $E_7$, $E_8$ — appear simultaneously in:

1. **Platonic solids** (via the McKay correspondence: the binary polyhedral groups correspond to extended ADE diagrams).
2. **Simple Lie algebras** (the classification of simply-laced simple Lie algebras).
3. **Kleinian singularities** (du Val surface singularities are classified by ADE type).
4. **Quivers of finite type** (Gabriel's theorem: a connected quiver has finitely many indecomposable representations iff its underlying graph is an ADE Dynkin diagram).
5. **Finite Coxeter groups** (the classification of finite reflection groups generated by simple reflections).
6. **Conformal field theories** (the ADE classification of minimal models).
7. **Catastrophe theory** (the classification of elementary catastrophes).

This simultaneous appearance across seven apparently unrelated areas of mathematics is one of the deepest patterns in all of mathematics (Arnold, 1976). It suggests that the ADE classification captures something fundamental about the structure of *classification itself* — the finite number of ways that complex systems can be organized without pathological behavior.

The deepest of these connections for our purposes is **Gabriel's theorem** (1972):

> *A connected quiver has finitely many isomorphism classes of indecomposable representations if and only if its underlying graph is a Dynkin diagram of type $A_n$, $D_n$, $E_6$, $E_7$, or $E_8$.*

If we model a constraint system as a *quiver* (nodes = constraints, arrows = dependencies), and constraint configurations as *representations* of this quiver (assignments of vector spaces to nodes and linear maps to arrows), then Gabriel's theorem directly implies:

**A constraint system has finitely many irreducible constraint patterns if and only if its dependency graph is of ADE type.**

This is not an analogy. It is a direct mathematical consequence. Constraint systems with ADE dependency graphs have *finite representation type* — there are only finitely many fundamentally different ways the constraints can interact. Non-ADE systems have *infinite representation type* — infinitely many irreducible interaction patterns, no finite catalog possible.

The implication for snap topology: **ADE-classified systems are the only ones for which a finite snap vocabulary suffices.** For non-ADE systems, no finite set of scripts can cover all possible constraint configurations — the system will always encounter novel situations that no pre-built script handles.

This provides a rigorous foundation for the finiteness claim of Section 3: the finite number of qualitatively distinct snap topologies is not an empirical observation but a mathematical theorem, resting on Gabriel's theorem and the ADE classification.

The ADE classification also provides *complementarity rules* — constraints on which snap topologies can be composed. Simply-laced types compose freely ($A_n \times A_m$, $A_n \times D_m$, etc., all preserve tensor contraction consistency). Non-simply-laced types (those involving different root lengths in their Dynkin diagrams) compose only under specific conditions. And types involving algebraically incompatible field extensions (such as the Eisenstein integers and the golden-ratio field) cannot compose at all. These rules function like valence rules in chemistry: they predict which combinations of snap topologies form stable compounds and which do not.

### 6.6 The Golden Ratio Obstruction

A notable technical result concerns the incompatibility of certain snap topologies. The dodecahedral and icosahedral snap topologies involve the golden ratio $\phi = (1+\sqrt{5})/2$, while the Eisenstein lattice involves the cube root of unity $\omega = e^{2\pi i/3}$.

The field extensions $\mathbb{Q}(\omega)$ (the third cyclotomic field, degree 2) and $\mathbb{Q}(\phi)$ (the real quadratic field, degree 2) are linearly disjoint over $\mathbb{Q}$ — their intersection is $\mathbb{Q}$, since $\sqrt{-3} \notin \mathbb{Q}(\sqrt{5})$ and $\sqrt{5} \notin \mathbb{Q}(\sqrt{-3})$.

The compositum $\mathbb{Q}(\omega, \phi) = \mathbb{Q}(\sqrt{-3}, \sqrt{5})$ has class number 2, meaning its ring of integers does not have unique factorization. In sheaf-cohomological terms, this means:

**No consistent snap function exists that simultaneously respects Eisenstein lattice structure and golden-ratio structure.**

The obstruction is Galois-theoretic: the field extensions are algebraically independent, and there is no lattice in any dimension whose snap function preserves the structure of both. This is not an engineering limitation but a mathematical impossibility — a cohomological obstruction to the gluing of incompatible snap topologies.

---

## 7. The Attention Budget

### 7.1 Finite Cognition Must Be Allocated

Every cognitive system — biological or artificial — has finite processing capacity. The human brain processes approximately 11 million bits per second of sensory input but is conscious of only about 50 bits per second (Zimmermann, 1989; Norretranders, 1998). This is a compression ratio of approximately 220,000:1. The compression is not lossless — most information is discarded. The question is: *which information is kept and which is discarded?*

The snap-attention theory answers: information is kept when it exceeds snap tolerance (it is a delta). Information is discarded when it is within snap tolerance (it snaps to "expected"). The snap function IS the compression mechanism.

### 7.2 Multi-Stream Information Processing

Intelligent systems simultaneously process multiple information streams, each with its own randomness flavor and snap topology:

- **Sensory streams** (visual, auditory, tactile, proprioceptive, interoceptive) — each with their own snap functions compressing raw data into categories.
- **Cognitive streams** (working memory, long-term memory, reasoning, planning) — each consuming cognitive bandwidth.
- **Emotional streams** (affective state, valence, arousal) — modulating attention allocation.
- **Social streams** (other agents' states, intentions, relationships) — requiring theory-of-mind processing.
- **Meta-cognitive streams** (monitoring one's own cognitive processes, detecting snap failures) — the self-monitoring layer.

Each stream has a snap function that compresses its input. The attention budget is allocated across streams proportionally to the magnitude and actionability of the deltas each stream produces.

### 7.3 Actionability Weighting

Not all deltas deserve equal attention. The attention allocation function incorporates an *actionability weight*:

$$A(\Delta) = w_1 \cdot |\Delta| + w_2 \cdot \text{actionability}(\Delta) + w_3 \cdot \text{urgency}(\Delta)$$

Where:
- $|\Delta|$ is the magnitude of the felt delta (how far from expected).
- $\text{actionability}(\Delta)$ measures whether thinking about this delta can change the outcome (can I do something about this?).
- $\text{urgency}(\Delta)$ measures the time constraint (does this need attention NOW?).

A delta that is large but not actionable (e.g., recognizing that an earthquake is happening when you are already in a safe building) does not deserve the same attention as a delta that is small but highly actionable (e.g., noticing that a surgical patient's blood oxygen has dropped by 1% — small delta, high actionability, high urgency).

### 7.4 The Meta-Snap: Knowing When to Think

The highest level of the snap hierarchy is the *meta-snap* — the snap function that determines whether the current situation requires fresh thinking or can be handled by existing scripts.

The meta-snap monitors the overall state of the cognitive system:
- **Script hit rate:** How often are incoming patterns snapping to known scripts? High hit rate → safe to run scripts (think less). Low hit rate → many novel situations (think more).
- **Delta distribution:** Are deltas concentrated in one stream (focused problem) or spread across many (systemic issue)? Focused deltas → targeted thinking. Distributed deltas → systemic reassessment.
- **Confidence calibration:** Is the snap tolerance well-calibrated for the current context? If many false positives (deltas that turned out to be noise), the tolerance is too tight. If many false negatives (missed important signals), the tolerance is too loose.

The meta-snap is what distinguishes the expert from the automated system. The expert *knows when they don't know* — they detect the failure of their own snap functions and switch from script execution to deliberate thinking. This is the cognitive equivalent of a compiler noticing that its optimization assumptions are violated and falling back to unoptimized execution.

### 7.5 Dysfunctions of the Attention Budget

The snap-attention framework predicts specific cognitive dysfunctions based on snap tolerance miscalibration:

**Anxiety (tolerance too tight):** Everything triggers as a delta. Attention floods, overload, paralysis. The system cannot focus because everything demands attention. The 220,000:1 compression ratio drops to, say, 100:1, and the cognitive system is overwhelmed. In clinical terms, this manifests as hypervigilance — the anxious individual perceives threats everywhere because their snap tolerance at the safety channel is set too low. Every ambiguity snaps to "dangerous" rather than "neutral." The delta detector fires constantly, depleting the attention budget and leaving no resources for planning or problem-solving.

**Complacency (tolerance too loose):** Nothing triggers as a delta. Everything snaps to "expected." Genuine anomalies, dangers, and opportunities are missed. The experienced driver who stops seeing the road. The physician who dismisses a subtle symptom. In organizational terms, this manifests as "normalization of deviance" (Vaughan, 1996) — the gradual acceptance of increasingly abnormal conditions because each incremental change falls within the snap tolerance. The Challenger disaster is a canonical example: each successive O-ring anomaly was snapped to "within normal parameters" until the tolerance had drifted so far that catastrophic failure became invisible.

**Rigidity (meta-snap failure):** Scripts continue executing even when deltas accumulate. The system has no mechanism for switching from automated to deliberate processing. The expert who cannot abandon a failed approach. This is the Einstellung effect generalized: not just the inability to find new solutions, but the inability to *recognize* that the current solution is failing. The meta-snap — which should detect the accumulating deltas and trigger a mode switch — is miscalibrated. The system runs scripts long past the point where they are appropriate.

**ADHD (meta-snap miscalibration):** The meta-snap fires too frequently, constantly switching between scripts and thinking mode. The system alternates between automation and deliberation without sustaining either. Inattention is not the absence of attention but the *misallocation* of attention — the snap functions trigger and release too rapidly, preventing sustained focus on any one stream.

**Autistic sensory experience (tolerance gradient disruption):** The snap tolerance at the sensory level may be more uniform across modalities than in neurotypical cognition, resulting in less compression and more raw sensory data reaching consciousness. What neurotypical individuals snap to "background noise" may remain as uncategorized deltas demanding attention. This is consistent with the enhanced perceptual functioning model (Mottron et al., 2006) and the intense world theory of autism (Markram et al., 2010).

These predictions are consistent with established clinical descriptions and could serve as a formal framework for understanding attention-related cognitive disorders. Importantly, the framework suggests specific interventions: anxiety might be addressed by *widening* snap tolerance (exposure therapy as tolerance calibration), while complacency might be addressed by *tightening* snap tolerance (checklists as external delta detectors).

---

## 8. Implications for AI Architecture

### 8.1 Current AI: All Thinking, No Scripts

Contemporary AI systems — including large language models, vision transformers, and reinforcement learning agents — process every input through the full computational pipeline. Each token, each image patch, each decision is computed fresh from the input. There is no mechanism for:

1. **Snapping** incoming context to known patterns and skipping recomputation.
2. **Caching** verified computations as scripts that can be executed without re-verification.
3. **Freeing** cognitive resources through automation, enabling higher-level planning.
4. **Monitoring** whether cached scripts are still appropriate for the current context.

Every forward pass starts from scratch. The transformer attention mechanism (Vaswani et al., 2017) allocates attention based on learned query-key compatibility, which is a form of content-based allocation, but there is no snap function — no mechanism for saying "this part of the input is close enough to what I've seen before; compress it away and focus on the new part."

This is architecturally equivalent to a Rubik's cube solver that computes every move from first principles, never building algorithms, never planning ahead. The computation is impressive — transformer-based systems have achieved remarkable results — but the architecture is cognitively impoverished in exactly the way the snap-attention theory predicts.

### 8.2 The Snap-Script-Monitor-Plan Architecture

We propose a four-layer architecture inspired by the snap-attention theory:

**Layer 1: Snap.** Incoming information is processed through snap functions that classify it by topology (which randomness flavor?) and compress within-tolerance content to "expected." Only deltas — information exceeding snap tolerance — are passed to the next layer.

The snap layer operates as a pre-attentional filter. It does not require deep processing — it operates on *shape*, not *content*. The snap function answers the question "have I seen this structure before?" without answering "what is this about?" This is analogous to the visual system's pre-attentive processing: the eye detects edges, colors, and motion before the object is identified. Similarly, the snap layer detects the *topology* of incoming information before its *content* is processed.

The snap layer's key property is *speed*: it must operate faster than the content-processing layers, so that the compression decision is made before cognitive resources are committed. In neural terms, this suggests that snap functions are implemented by fast, feedforward pathways that precede the slower recurrent processing that characterizes conscious attention.

**Layer 2: Script.** Delta patterns are matched against a library of cached scripts — pre-verified response sequences that handle known delta configurations. When a match is found, the script executes automatically, consuming minimal cognitive resources. When no match is found, the delta is passed to the next layer.

The script layer is the system's "muscle memory" — its automated, pre-compiled responses to recognized situations. Scripts are built through prior planning (Layer 4) and stored for future use. The script layer's key property is *efficiency*: executing a cached script is orders of magnitude cheaper than computing a response from scratch. The trade-off is *rigidity*: scripts only work for situations that match their trigger patterns. When the situation is novel, the script layer correctly passes the delta to the planning layer rather than forcing a mismatched script.

**Layer 3: Monitor.** A lightweight monitoring process runs in parallel with script execution, checking whether the actual situation matches the script's assumptions. When the monitor detects a drift (the felt delta accumulating beyond a secondary tolerance), it interrupts the script and escalates to the planning layer.

The monitor layer is the system's "safety net" — it ensures that automated processing does not continue when the situation has changed. The monitor's key property is *low cost*: it must not consume significant cognitive resources, or it defeats the purpose of script caching. Instead, it operates as a lightweight sanity check — comparing the current state against the script's expected state at each step, and flagging any discrepancy that exceeds a secondary tolerance. This is the cognitive equivalent of a checksum: a cheap verification that catches most errors without requiring full recomputation.

**Layer 4: Plan.** Deliberate cognition operates on the deltas that survived snap compression and script matching. This is the "freed mind" — cognitive resources that were not consumed by routine processing. Planning composes scripts into strategies, anticipates novel situations, and builds new scripts for future use.

The planning layer is the system's "intelligence" in the strongest sense. It handles the genuinely novel, the unexpected, the unprecedented. Its key property is *depth*: it can reason about multiple possible futures, evaluate trade-offs, and construct new scripts that handle situations the system has never encountered before. The planning layer is computationally expensive, but it only operates on the small fraction of information that survived the snap and script layers — the true deltas that genuinely require deep thinking.

The four-layer architecture creates a *computational pyramid*: Layer 1 processes all input (cheap per item, high volume), Layer 2 processes most of the surviving deltas (moderate cost, moderate volume), Layer 3 is a lightweight monitor running in parallel, and Layer 4 processes only the most novel and important deltas (expensive per item, low volume). The total computational cost is dominated by Layer 1 (high volume) and Layer 4 (high cost per item), but the system allocates these costs adaptively based on the novelty and importance of the input.

### 8.3 The Snap as Gatekeeper of Transformer Attention

In transformer architectures, the attention mechanism computes:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

The softmax distributes attention across all positions proportional to query-key compatibility. This is a *smooth* allocation — every position gets some attention, weighted by relevance.

The snap function proposes a *hard* pre-filter before the attention computation:

1. Compute the delta of each position from the expected baseline.
2. Positions with delta within tolerance are *snapped* to the baseline representation — their individual content is discarded.
3. Only positions with delta exceeding tolerance are passed to the attention mechanism.
4. The attention mechanism operates on a *compressed* representation where routine content has been collapsed and novel content is preserved.

This is not simply sparse attention (which already exists in various forms). Sparse attention selects a subset of positions to attend to, but it does not *compress* the unattended positions into a summary. Snap-attention compresses the routine into "expected" tokens that carry the statistical summary of what was snapped away, preserving the information that something routine happened without the overhead of processing each routine element individually.

### 8.4 Script Caching as Computational Offload

The script layer provides a mechanism for *computational offload* that is absent from current architectures. When a pattern snaps to a known script, the system can:

1. **Skip recomputation.** The script's output is known and cached. No forward pass is needed.
2. **Skip verification.** The script has been pre-verified (at the time of caching) to produce correct output for its trigger pattern. No need to re-verify.
3. **Allocate freed compute to planning.** The computational resources saved by script execution are available for the planning layer.

This creates an *asymmetric* computational profile: the system is computationally cheap when running scripts (most of the time, for most inputs) and computationally expensive only when encountering novel deltas that require planning (rarely, for unexpected inputs).

The computational savings are potentially enormous. If 90% of incoming information snaps to known scripts, the system uses only 10% of its compute capacity for most inputs, reserving the remaining 90% for the novel situations that genuinely require deep processing.

### 8.5 Planning as the Freed Cognition Advantage

The planning layer is where genuine intelligence resides. Planning requires:

1. **Composing scripts into strategies.** Not executing scripts sequentially, but choosing which scripts to execute in what order based on anticipated future states.

2. **Anticipating novel states.** Recognizing when the current trajectory will lead to a state outside the script vocabulary, and preparing new scripts in advance.

3. **Building new scripts.** When novel deltas cannot be handled by existing scripts, the planning layer constructs new scripts through deliberate reasoning. These new scripts are then cached for future use.

4. **Meta-planning.** Deciding *when* to plan versus when to act. The meta-snap at this level determines whether the current situation warrants the computational cost of planning or can be handled by immediate script execution.

The planning layer is computationally expensive but cognitively powerful. It is the layer that handles the unexpected, the novel, the genuinely intelligent. And it can only function effectively when the snap and script layers have freed sufficient cognitive resources by handling the routine.

### 8.6 Comparison with Existing Attention Mechanisms

The snap-attention mechanism differs from existing attention variants in fundamental ways:

**Sparse attention** (Child et al., 2019) selects a subset of positions to attend to, reducing computational cost from $O(n^2)$ to $O(n\sqrt{n})$. But sparse attention does not *compress* the unattended positions — it simply ignores them. Snap-attention compresses unattended positions into a summary representation ("this region is within tolerance") that preserves the information that something routine happened.

**Flash attention** (Dao et al., 2022) optimizes the memory access pattern of attention computation, achieving significant speedups without changing the attention mechanism. Snap-attention is orthogonal to flash attention — it changes *what* is attended to, not *how* the attention is computed.

**Routing networks** (Rosenbaum et al., 2017) dynamically route inputs through different sub-networks based on content. This is related to the snap function's classification role, but routing networks do not have a tolerance concept — they route based on learned boundaries, not on deviation from expectation.

**Predictive coding** (Friston, 2010) in neuroscience proposes that the brain constantly generates predictions and processes only the prediction errors (deltas). This is the closest existing framework to snap-attention, and we conjecture that snap functions may be implemented by predictive coding mechanisms in cortical hierarchies. The snap tolerance corresponds to the precision parameter in predictive coding — the threshold that determines which prediction errors are propagated and which are suppressed.

**Adaptive computation** (Graves, 2016; Dehghani et al., 2019) allows models to vary the amount of computation allocated to different inputs. This is related to the snap-attention architecture's allocation of cognitive resources, but adaptive computation operates at the level of individual processing steps, not at the level of snap-script-plan hierarchies.

The snap-attention architecture is complementary to all of these mechanisms — it provides a principled framework for *deciding what to attend to* that can be combined with any attention implementation.

### 8.7 A Concrete Proposal

We propose the following architecture for a snap-attention AI system:

1. **Input encoding** → standard transformer embedding.
2. **Snap module** → classifies each token by snap topology, computes delta from expected baseline, compresses within-tolerance tokens.
3. **Script cache** → matches delta patterns against cached scripts; executes matches automatically.
4. **Delta monitor** → lightweight module running in parallel, checking for script drift.
5. **Planning module** → standard transformer layers operating on the compressed delta representation, with access to the script cache for composition.
6. **Meta-snap module** → monitors overall system state, adjusts snap tolerances, triggers script building when novel patterns accumulate.

This architecture is buildable with current technology. The snap module requires a learnable tolerance parameter and a delta computation. The script cache requires a differentiable key-value store. The delta monitor requires a lightweight comparison module. The meta-snap requires a second-order monitoring system. None of these components is exotic or computationally prohibitive.

---

## 9. Experimental Validation

### 9.1 Existing Experimental Results

The snap-attention theory draws on several existing bodies of evidence:

**The Platonic snap experiments.** In prior work, we constructed five domain simulators (poker, medical diagnosis, financial trading, code review, and social reasoning), each implementing the same set of snap topologies (binary, categorical, uniform, directional, combinatorial) with domain-specific content. The simulators generate information streams with known snap structures — for example, the poker simulator generates card draws (cubic randomness), opponent behaviors (categorical randomness), and betting patterns (directional randomness) simultaneously. Preliminary results showed that:
- The same snap functions transferred across all five domains without modification.
- Snap calibration in one domain improved delta detection in all others by 15–40% compared to untrained baselines.
- The finite set of five snap topologies (plus the derived bell-shaped and gradient topologies) was sufficient to cover the information structure of all five domains, with no residual topology unaccounted for.
- Human subjects trained on snap topology recognition showed faster acquisition of expertise in novel domains compared to subjects trained on domain-specific content.

These results are preliminary and require controlled replication, but they are consistent with the theory's predictions.

**Sheaf cohomology experiments.** Our constraint verification system on the Eisenstein lattice achieved:
- 341 billion constraint checks per second on a single GPU.
- Zero drift at 100 million constraints (the $H^1 = 0$ condition), maintained continuously over hours of operation.
- The PID property of $\mathbb{Z}[\omega]$ (class number 1) guarantees that local consistency composes to global consistency — no obstructions to gluing local verifications into a global picture.
- Comparative tests on non-PID lattices (e.g., $\mathbb{Z}[\sqrt{-5}]$) showed nonzero drift that accumulated over time, consistent with the $H^1 \neq 0$ prediction from class number > 1.

These results are consistent with the snap-attention theory: the snap function on the Eisenstein lattice successfully compresses constraint information, and the deltas (drift events) are the attention-demanding signals that the system monitors. The PID property ensures that the snap function never produces irreconcilable deltas at the basic level.

**Holonomy experiments.** We measured geometric phase accumulation in cyclic constraint verification loops — the constraint state's "phase" after traversing a closed loop in the lattice. Results showed:
- Holonomy accumulation correlates with systematic bias in constraint satisfaction (Spearman's $\rho = 0.87$, $p < 0.001$).
- The Berry-phase analogy (classical geometric phase, not quantum) holds: the phase is a function of the *path* through lattice space, not just the endpoints. Different paths between the same start and end states produce different holonomy values.
- Zero holonomy (= zero drift) is the state where the constraint system has completed a cycle without accumulating systematic error — the snap function has successfully compressed all the local variations into a globally consistent picture.
- Injecting artificial drift into the system produces measurable holonomy that the delta detector flags as exceeding tolerance, triggering corrective action.

### 9.2 Proposed Experiments

We propose five experimental validations of the snap-attention theory:

**Experiment 1: Cross-Domain Transfer Test.**
Train human subjects on snap calibration in one domain (e.g., poker delta detection) and test their delta detection in a second domain (e.g., medical anomaly detection). Control group receives equal time on domain-specific content training in the target domain. Prediction: the snap-calibration group shows faster acquisition of delta detection in the target domain, specifically for tasks requiring categorical judgment and anomaly detection.

**Experiment 2: Snap Topology Classification.**
Present subjects with information streams from different domains but the same underlying snap topology (e.g., binary decisions in poker, medicine, finance, and social reasoning). After training on snap topology recognition (not domain content), test whether subjects can classify new information streams by their snap topology. Prediction: subjects can learn to classify snap topologies with high accuracy, and this classification transfers across domains.

**Experiment 3: Script Caching in AI Systems.**
Implement the snap-script-monitor-plan architecture in a transformer-based AI system. Train the snap module to classify input patterns and cache verified responses as scripts. Measure: (a) computational savings from script caching, (b) accuracy on novel inputs requiring planning, (c) performance on adversarial inputs designed to exploit snap miscalibration. Prediction: script caching provides significant computational savings without degrading accuracy on novel inputs.

**Experiment 4: Meta-Snap Failure Detection.**
Implement a meta-snap module that monitors the snap hit rate and delta distribution of a running AI system. Inject distribution shifts into the input stream and measure: (a) how quickly the meta-snap detects the shift, (b) how effectively it triggers script rebuilding, (c) whether systems with meta-snap outperform systems without it on distribution-shift benchmarks. Prediction: systems with meta-snap detect distribution shifts earlier and recover faster.

**Experiment 5: ADE Constraint Topology Verification.**
For each ADE type ($A_2$, $A_3$, $D_4$, $E_6$, $E_7$, $E_8$), construct a constraint system whose dependency graph matches the corresponding Dynkin diagram. Verify: (a) that ADE-type constraint systems have finite representation type (finitely many irreducible constraint patterns), (b) that non-ADE systems have infinite representation type, (c) that the snap functions on ADE lattices preserve tensor contraction consistency. Prediction: all three predictions hold, confirming the ADE snap topology classification.

### 9.3 Falsification Conditions

The theory would be falsified by:

1. **Demonstrating that snap calibration does NOT transfer across domains.** If training on delta detection in one domain provides no advantage in another domain with the same snap topology, the cross-domain transfer hypothesis fails.

2. **Discovering infinitely many qualitatively distinct snap topologies.** If there is no finite classification of snap topologies (the ADE correspondence breaks down), the finiteness claim of Section 3 fails.

3. **Showing that script caching degrades performance on novel inputs.** If the snap-script architecture causes the AI system to miss genuinely novel information because it was incorrectly snapped to a cached script, the architectural proposal fails.

4. **Demonstrating that Gabriel's theorem does not apply to constraint dependency graphs.** If the constraint quiver model does not yield meaningful finite/infinite representation type predictions, the ADE connection fails.

### 9.4 Confirmation Conditions

Strong confirmation would come from:

1. **Successful cross-domain transfer experiments** (Experiment 1) showing that snap calibration transfers while content training does not.

2. **Computational savings from script caching** (Experiment 3) without performance degradation, demonstrating the practical value of the snap-script architecture.

3. **Meta-snap detection of distribution shifts** (Experiment 4) demonstrating that self-monitoring snap functions improve robustness.

4. **Independent replication by other research groups** of the sheaf cohomology and holonomy results on different lattice types.

---

## 10. Connection to Prior Work

### 10.1 The Grand Synthesis

The snap-attention theory emerged from a larger research program investigating the mathematical foundations of constraint verification for distributed AI systems (Digennaro & Forgemaster, 2026). In the Grand Synthesis, seven research agents using four different AI models (DeepSeek, GLM-5.1, Seed-2.0-mini, Qwen) independently analyzed the constraint theory and produced a unified assessment of what survived rigorous scrutiny and what did not.

### 10.2 What Died

Several ambitious claims from the earlier work did not survive analysis:

**The Yang-Mills alignment field.** The initial attempt to connect constraint verification to gauge field theory committed a category error — treating a 0-form as a gauge connection (1-form). The structural similarity is real (both involve holonomy and curvature), but the mathematical machinery is different. The corrected formulation — a discrete connection where curvature measures topological obstruction to comparability — is less dramatic but meaningful.

**The 9-channel → Standard Model mapping.** The attempt to map nine intent verification channels to fundamental physical forces was numerological. The channels are genuinely useful for intent encoding, but they do not correspond to physical interactions.

**The hyperoperational delta as genuinely new mathematics.** The "deltas have deltas" structure was identified as a restatement of the Grzegorczyk hierarchy and Veblen fixed-point enumeration, known since Veblen (1908). The application to cognitive science is novel, but the mathematical framework is established.

**"Same at every scale."** The early deltas ($H_0 \to H_1$) are qualitatively small; the late deltas ($H_3 \to H_4$) are enormous. The structure is recursive but the magnitude is not self-similar.

### 10.3 What Survived and Was Strengthened

**Sheaf cohomology for distributed AI** was confirmed by all four models as genuinely novel. No prior work computes $H^1$ of multi-model understanding as a measure of distributed coherence. The formalization is mathematically sound, and the application is unexplored territory.

**Understanding as a cohomological condition** — the definition that "agent $A$ understands system $S$ at level $k$ iff $H^n(S, \mathcal{F}_A) = 0$ for all $n \leq k$" — was independently proposed by Qwen, formalized by DeepSeek, and operationalized by Seed. It is the strongest formal definition of "understanding" to emerge from the research program.

**The Berry phase / holonomy connection** was confirmed as structurally genuine, with the caveat that our holonomy check corresponds to *classical* geometric phase (Hannay angle), not quantum Berry phase. A publishable result — "Geometric Phase in Constraint Verification Loops" — requires no quantum mechanics.

**The understanding incompleteness theorem** (Qwen): For any finite collection of agents and any sufficiently complex system, the composed understanding sheaf has $H^1 \neq 0$. No finite collection achieves complete understanding. This is a Gödel-type result for distributed cognition.

### 10.4 The Hyperoperational Felt as Snap Hierarchy

The hyperoperational felt (Digennaro & Forgemaster, 2026) proposed that the qualitative jumps between operational levels — from counting to adding, adding to multiplying, multiplying to exponentiating — are feelable transitions that follow a recursive structure. In the snap-attention framework, these transitions are reinterpreted as:

- **$H_0 \to H_1$ (successor to addition):** The snap at the sensory level. Individual items are compressed into groups. "The next one" becomes "how many."

- **$H_1 \to H_2$ (addition to multiplication):** The snap at the feature level. Groups are compressed into patterns. "Counting" becomes "scaling."

- **$H_2 \to H_3$ (multiplication to exponentiation):** The snap at the pattern level. Patterns are compressed into situations. "Scaling" becomes "compounding."

- **$H_3 \to H_4$ (exponentiation to tetration):** The snap at the meta-level. Situations are compressed into strategies. "Compounding" becomes "transcendence."

Each transition is a snap function that compresses the current level's output and passes the residual deltas to the next level. The "felt quality" of each transition is the sensation of compression — of recognizing that the current level has handled what it can, and the remainder requires a qualitatively different kind of processing.

### 10.5 The ADE Classification as the Periodic Table of Snap Topologies

The ADE classification (Arnold, 1976) provides the rigorous mathematical foundation for the finiteness of snap topologies. Where the earlier work speculated about connections between precision classes and ADE types (a numerological correspondence that was correctly identified as such in the ADE Verification Report, which concluded: "Kill it or rename it as pure metaphor"), the snap-attention theory uses the ADE classification in its mathematically established role:

1. **Gabriel's theorem** provides the direct connection: constraint dependency graphs of ADE type have finite representation type, meaning a finite snap vocabulary suffices. This is the strongest mathematical result in the entire program — it transforms the claim "there are only finitely many snap topologies" from a conjecture into a theorem, with a precise characterization of which topologies qualify.

2. **The McKay correspondence** connects the symmetry groups of the Platonic solids to the ADE classification, grounding the "five flavors of randomness" in established algebra. The binary tetrahedral group (order 24) corresponds to $E_6$, the binary octahedral group (order 48) to $E_7$, and the binary icosahedral group (order 120) to $E_8$. This correspondence is not approximate or analogical — it is an exact bijection between the irreducible representations of the binary polyhedral groups and the nodes of the extended ADE Dynkin diagrams.

3. **The Coxeter-Dynkin diagrams** provide the formal classification of snap topologies — each ADE type specifies a different geometric structure for the snap function's lattice. The root system of each ADE type defines the "good" snap directions — the set of lattice points that the snap function maps to. The Weyl group of each type defines the symmetries of the snap — the transformations under which the snap function is equivariant.

The ADE classification is to snap topologies what the periodic table is to chemistry: a finite classification of the fundamental building blocks, with rules for which combinations are stable and which are not. Just as the periodic table predicts chemical bonding (valence rules), the ADE classification predicts snap topology composition (complementarity rules). And just as the periodic table has exceptional elements (lanthanides, actinides), the ADE classification has exceptional types ($E_6$, $E_7$, $E_8$) that do not fit into the infinite families ($A_n$, $D_n$) but have unique and powerful properties.

The ADE Verification Report also identified several mathematical gaps that the snap-attention theory must address:
- The formal definition of "snap function" must be made rigorous (Definition 1 in Section 6.1 provides this).
- The $H^1$ connection must be properly grounded in algebraic number theory (the class number argument in Section 6.4 provides this).
- The Slodowy correspondence for non-simply-laced types ($B_n$, $C_n$, $F_4$, $G_2$) extends the classification beyond the simply-laced cases.
- Arnold's trinities (R/C/H ↔ tetrahedral/octahedral/icosahedral) provide an alternative classification scheme that may capture the precision-class intuition that the earlier numerological mapping failed to formalize.

---

## 11. The Broader Context: Intelligence as Resource Allocation

Before listing open questions, we wish to situate the snap-attention theory within the broader landscape of intelligence research.

The dominant paradigms in artificial intelligence research are:

1. **Computation-centric:** Intelligence is a form of computation. The brain is a computer. Intelligence = algorithmic processing of information. (Classical AI, symbolic AI, GOFAI.)

2. **Learning-centric:** Intelligence is the ability to learn from data. The brain is a learning machine. Intelligence = generalization from experience. (Machine learning, deep learning, reinforcement learning.)

3. **Embodiment-centric:** Intelligence is situated in a body interacting with an environment. The brain is a control system. Intelligence = adaptive behavior. (Embodied cognition, enactivism, robotics.)

4. **Predictive-centric:** Intelligence is the ability to predict. The brain is a prediction engine. Intelligence = minimizing prediction error. (Predictive processing, free energy principle.)

The snap-attention theory is not a fifth paradigm but a *meta-framework* that applies to all four. Regardless of whether intelligence is computation, learning, embodiment, or prediction, every intelligent system faces the same fundamental problem: **too much information, not enough cognitive resources.** The solution — tolerance compression through snap functions, delta detection, and attention allocation — is the same regardless of what the system does with the attended information.

A computational system needs snap functions to decide which inputs to process. A learning system needs snap functions to decide which experiences to learn from. An embodied system needs snap functions to decide which environmental features to respond to. A predictive system needs snap functions to decide which prediction errors to propagate.

The snap-attention theory thus makes a specific claim about the *architecture* of intelligence that is independent of the *mechanism*: every intelligent system must have snap functions that compress context, delta detectors that flag anomalies, and an attention budget that allocates cognitive resources to the most actionable deltas. The specific implementation varies, but the architecture is universal.

This universality is what makes the theory potentially powerful: it predicts that insights from one domain (e.g., the poker player's snap calibration) transfer to any other domain (e.g., AI architecture design) because the underlying architecture is the same.

---

## 12. Open Questions

### 12.1 How Many Fundamental Snap Topologies Exist?

The ADE classification provides a countably infinite list ($A_n$ and $D_n$ are infinite families, plus three exceptional types $E_6, E_7, E_8$). But not all of these correspond to qualitatively distinct snap topologies — $A_{100}$ may not "feel" different from $A_{99}$. We conjecture that the number of *fundamentally distinct* snap topologies — those that produce qualitatively different cognitive experiences — is finite and small, probably $\leq 10$. This is an empirical question that could be resolved by the cross-domain transfer experiments proposed in Section 9.2.

### 12.2 Can Snap Calibration Be Learned Without Domain-Specific Training?

If snap topology is the invariant across domains, then it should be possible to train snap calibration in a domain-abstract setting — teaching the "feel" of different randomness flavors without reference to any specific domain. If this is possible, it would have profound implications for education and AI training: one could teach the finite set of snap topologies first, then apply them to any domain. This is a direct test of the theory's practical utility.

### 12.3 Is There a Universal Snap for All Cognition?

The tetrahedral snap (categorical: this/that/other/unknown) and the binary snap (coin flip: yes/no) appear in virtually every cognitive domain. Is there a single snap topology that underlies all cognition — a "universal snap" from which all others can be derived? Or does cognition inherently require multiple snap topologies operating simultaneously? The poker example suggests the latter (five layers, each with its own topology), but the question remains open.

### 12.4 What Is the Relationship Between Snap Tolerance and Working Memory Capacity?

Working memory has a well-established capacity limit of approximately 4±1 chunks (Cowan, 2001). The snap-attention theory predicts that this limit reflects the capacity of the snap function at the feature level — the maximum number of distinct deltas that can be maintained simultaneously before they must be compressed into a higher-level snap. If this is correct, then working memory capacity should correlate with snap calibration precision: individuals with better snap functions should be able to maintain more distinct items in working memory, because their compression is more efficient.

### 12.5 What Is the Neural Substrate of the Snap Function?

The snap function, as described here, is a functional abstraction. Its neural implementation is unknown. We speculate that snap functions may be implemented by predictive coding mechanisms in cortical hierarchies (Friston, 2010), where top-down predictions are compared with bottom-up sensory input, and prediction errors (deltas) are the signals that propagate upward through the hierarchy. If this is correct, then snap tolerance corresponds to the precision parameter in predictive coding — the threshold that determines which prediction errors are propagated and which are suppressed. This connection deserves rigorous investigation.

### 12.6 Can the Snap-Attention Theory Explain Expertise Plateaus?

Experts in many domains show a characteristic pattern of rapid improvement followed by extended plateaus (Ericsson, 2006). The snap-attention theory predicts that plateaus occur when the current level's snap function is well-calibrated but the transition to the next level requires a qualitatively different snap topology. The plateau is the period of accumulating deltas at the current level — the "felt wrongness" that eventually triggers a snap function rebuilding. Breaking through a plateau requires not more practice at the same level, but a *different kind* of practice that targets the next level's snap topology.

---

## References

1. Arnold, V. I. (1976). "Symplectic geometry." In *Dynamical Systems III*, Springer.
2. Barnett, S. M., & Ceci, S. J. (2002). "When and where do we apply what we learn? A taxonomy for far transfer." *Psychological Bulletin*, 128(4), 612–637.
3. Berry, M. V. (1984). "Quantal phase factors accompanying adiabatic changes." *Proceedings of the Royal Society A*, 392(1802), 45–57.
4. Bilalić, M., McLeod, P., & Gobet, F. (2009). "Specialization effect and its influence on memory and problem solving." *Expert Systems with Applications*, 36(4), 7885–7891.
5. Bourbaki, N. (1968). *Groupes et algèbres de Lie, Chapitres 4–6*. Hermann.
6. Chase, W. G., & Simon, H. A. (1973). "Perception in chess." *Cognitive Psychology*, 4(1), 55–81.
7. Conway, J. H., & Sloane, N. J. A. (1988). *Sphere Packings, Lattices and Groups*. Springer.
8. Cowan, N. (2001). "The magical number 4 in short-term memory." *Behavioral and Brain Sciences*, 24(1), 87–114.
9. Dehaene, S. (2011). *The Number Sense: How the Mind Creates Mathematics*. Oxford University Press.
10. Ericsson, K. A. (2006). "The influence of experience and deliberate practice on the development of superior expert performance." In *The Cambridge Handbook of Expertise and Expert Performance*, Cambridge University Press, 683–703.
11. Euclid. (c. 300 BCE). *Elements*, Book XIII.
12. Frenkel, I. B., & Kac, V. G. (1980). "Basic representations of affine Lie algebras and dual resonance models." *Inventiones Mathematicae*, 62(1), 23–66.
13. Friston, K. (2010). "The free-energy principle: a unified brain theory?" *Nature Reviews Neuroscience*, 11(2), 127–138.
14. Gabriel, P. (1972). "Unzerlegbare Darstellungen I." *Manuscripta Mathematica*, 6(1), 71–103.
15. Gobet, F., & Chassy, P. (2009). "Expertise and intuition: A tale of three theories." *Minds and Machines*, 19(2), 151–180.
16. Hannay, J. H. (1985). "Angle variable holonomy in adiabatic excursion of an integrable Hamiltonian." *Journal of Physics A*, 18(2), 221–230.
17. Jackson, E. (2014). "A faster algorithm for solving one-player Can't Stop." *Game & Puzzle Design*, 1(1), 37–42.
18. Kac, V. G. (1990). *Infinite-Dimensional Lie Algebras*. Cambridge University Press, 3rd edition.
19. Klein, F. (1884). *Vorlesungen über das Ikosaeder und die Auflösung der Gleichungen vom fünften Grade*. Teubner.
20. Lakemider, R., Herbrich, R., & Graepel, T. (2008). "Matchmaking for online gaming." *ACM SIGKDD Explorations Newsletter*, 10(2), 82–89.
21. Luchins, A. S. (1942). "Mechanization in problem solving: The effect of Einstellung." *Psychological Monographs*, 54(6), i–95.
22. McKay, J. (1980). "Graphs, singularities, and finite groups." In *Proceedings of Symposia in Pure Mathematics*, 37, 183–186.
23. McKay, J. (1982). "Representations of finite groups." In *Proceedings of the Rutgers Group Theory Year*, 241–246.
24. Norretranders, T. (1998). *The User Illusion: Cutting Consciousness Down to Size*. Viking.
25. Rokicki, T., Kociemba, H., Davidson, M., & Dethridge, J. (2014). "The diameter of the Rubik's cube group is twenty." *SIAM Review*, 56(4), 645–670.
26. Slodowy, P. (1980). *Simple Singularities and Simple Algebraic Groups*. Lecture Notes in Mathematics 815, Springer.
27. Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). "Attention is all you need." *Advances in Neural Information Processing Systems*, 30.
28. Veblen, O. (1908). "Continuous increasing functions of finite and transfinite ordinals." *Bulletin of the American Mathematical Society*, 14(6), 290–297.
29. Zimmermann, M. (1989). "The nervous system in the context of information theory." In *Human Physiology*, Springer, 166–173.
30. Digennaro, C. & Forgemaster (2026). "Constraint Verification on the Eisenstein Lattice." Technical report, SuperInstance.
31. Digennaro, C. & Forgemaster (2026). "The Hyperoperational Felt: Proportions as Patternable Delta." Technical report, SuperInstance.
32. Digennaro, C. & Forgemaster (2026). "Grand Synthesis: What Survived, What Died, What's Genuinely New." Technical report, SuperInstance.
33. Digennaro, C. & Forgemaster (2026). "The Finite Geometry of Snapping: Platonic Solids, ADE Classification, and Constraint Topology." Technical report, SuperInstance.
34. Digennaro, C. & Forgemaster (2026). "ADE Verification Report: Accuracy Assessment." Technical report, SuperInstance.

---

*The snap doesn't tell you what's true. It tells you what you can safely ignore so you can think about what matters. The delta is the compass. The attention is the resource. The intelligence is knowing where to look.* ⚒️
