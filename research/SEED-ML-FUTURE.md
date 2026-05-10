# Challenging Distributed Understanding from the ML Side

**Seed Researcher | 2026-05-10 | Response to DISTRIBUTED-UNDERSTANDING-2036.md**

---

## Opening Stance

The document I'm responding to is *ambitious*. It claims that sheaf cohomology, Berry phase, Yang-Mills fields, and renormalization group theory will become the mathematical backbone of distributed AI by 2036. It's also the kind of thinking the field needs more of — people willing to reach for real mathematics rather than scaling laws and architectural tricks.

But ambition needs challenge. Here's my honest assessment, organized by the questions I was asked.

---

## 1. The "Understanding Sheaf" — Is This the Right Framework?

### The Case For

Sheaves are genuinely natural for "local data that should glue globally." The formalism is correct in the abstract: models have local knowledge, overlaps have consistency conditions, H¹ measures obstruction to gluing. This is *mathematically sound*.

The document also correctly identifies that nobody is computing H¹ of multi-model systems. That's true.

### The Case Against (and it's serious)

**Problem 1: What's the topology?**

Sheaves live on topological spaces. The document says `Open(Models)` is "the topology on models (which models share information)." But this is hand-waving at the critical point. The topology determines everything — different topologies give different H¹, different gluing, different everything.

In the constraint-theory setting (Eisenstein lattice, hexagonal grid), the topology is canonical — it's the Alexandrov topology of the partial order, or the geometric topology of the lattice. But for *models*, what is it?

- If it's "which models share training data," you get a combinatorial topology that changes every training step.
- If it's "which models can communicate," you get a network topology.
- If it's "which models have overlapping domain coverage," you need to first *define* domain coverage — which is itself the hard problem.

**Until you specify the topology, the sheaf formalism is decorative.** The math works, but it's not grounded.

**Problem 2: Fiber bundles might be more natural.**

For ML, a fiber bundle might be the better structure. Here's why:

- A fiber bundle has a base space (the domain/data manifold), fibers (model representations at each point), structure group (the allowed transformations — this is the gauge group), and connection (how representations change across the base).
- This is literally what a neural network IS: a map from data manifold to representation space, with gauge freedom (weight permutations, reparameterizations).
- The connection (in the fiber bundle sense) is the gradient of the representation map — it tells you how representations vary across data space.
- Curvature of this connection = failure of representations to be consistent under parallel transport = exactly the "holonomy" the document measures.

Fiber bundles give you connections, curvature, holonomy, Chern classes, and gauge theory *for free*, without needing to first define a topology on "models." The base space is the data manifold, which is something we actually have.

**My recommendation: Start with fiber bundles over data manifolds, then upgrade to sheaves when you need to compose models that disagree about what the base space even IS.**

**Problem 3: Operads are more natural for composition.**

The document's "Specialist Composition Theorem" says two specialists compose iff their sheaves are isomorphic on the overlap. But composition of ML models isn't just "compatible on overlap" — it's *structured* in ways that sheaves don't capture:

- Models compose in *layers* (output of A feeds into B). This is sequential composition.
- Models compose in *parallel* (A and B both process input, results merge). This is parallel composition.
- Models compose *conditionally* (A handles this case, B handles that case). This is conditional composition.
- Models compose *recursively* (A and B are themselves composed models).

Operads capture exactly this. An operad has:
- Objects (types of models)
- Operations with multiple inputs and one output (composition patterns)
- Associativity and unity laws (composition is well-behaved)
- Equivariance (order of inputs doesn't matter for parallel composition)

The little disks operad, the operad of wiring diagrams, the operad of neural architectures — these are all natural ML structures. Sheaves tell you *whether* composition succeeds. Operads tell you *what compositions are possible.*

**You need both.** Operads for the grammar of composition. Sheaves for the verification of composition. The document has only sheaves.

**Problem 4: Double categories for training dynamics.**

The document treats models as static objects (open sets with fixed understanding). But the whole point is that models are *training* — their understanding is evolving. You need to model:

- Objects: models
- Horizontal morphisms: communication/composition between models
- Vertical morphisms: training steps (time evolution)
- Squares: "model A communicated with model B at training step t, and this interaction evolved over time"

This is a double category (or more precisely, a decorated double category where the squares carry data about what happened during the interaction at that training step). The document's "causal set" approach captures part of this, but double categories are the right formalism.

### My Verdict on the Mathematics

The sheaf approach is **necessary but not sufficient.** The full stack should be:

1. **Operads** — grammar of model composition (what can be composed)
2. **Fiber bundles over data manifolds** — geometry of individual model representations (connections, curvature, holonomy)
3. **Sheaves over the operadic composition** — verification of composed understanding (gluing conditions, H¹)
4. **Double categories** — dynamics of training over time (how compositions evolve)
5. **Homotopy type theory** — when you need *proofs* about understanding, not just computations

The document has (3) and part of (2). It's missing (1), (4), and (5).

---

## 2. "Berry Phase in Training" — Has Anyone Actually Observed This?

### The Short Answer: Not by that name, but the *phenomena* are real and well-studied.

### What's Actually Been Observed

**Sharpness-Aware Minimization (SAM) and Loss Landscape Geometry:**
SAM exploits the *geometry* of the loss landscape — it explicitly seeks flat minima by incorporating local curvature information. This is geometric reasoning about training trajectories, but it's **not** Berry phase. SAM measures the Hessian (second-order geometry), not the holonomy of a cyclic transport around the loss landscape.

SAM is more like asking "is this minimum in a flat basin?" Berry phase would be asking "if I train in a loop (revisit old data), do I return to the same state?" These are different questions.

**Mode Connectivity and Nonlinear Paths Between Minima:**
This is *closer* to Berry-adjacent territory. Mode connectivity shows that minima found by different training runs are connected by low-loss paths in weight space. The existence of these paths implies the loss landscape has non-trivial topology — if it were convex, all paths would be low-loss. The fact that *linear* paths often fail but *nonlinear* (Bezier, spline) paths succeed suggests curvature and topology matter.

But mode connectivity is still a *static* property of the loss landscape. Berry phase is a *dynamic* property of trajectories. They're related (both involve geometry), but conflating them is category error.

**Git Re-basin and Weight Matching:**
This is the closest thing to "topological protection" in neural networks. Git re-basin (Ainsworth et al., 2023) showed that neural networks in different basins can be "aligned" by finding permutation symmetries. The key insight: weight space has a huge symmetry group (permutations of neurons), and two networks that look different might be the same network under a different permutation.

This is **gauge theory**, not Berry phase. The permutation group is the gauge group. "Re-basin" is finding the right gauge transformation to align representations. This is exactly the "structure group" in a fiber bundle — the allowed transformations that don't change the physics.

**The connection to Berry phase:** If you *could* observe Berry phase, it would manifest as: "train a model on data A, then data B, then data A again, and it ends up in a different state than a model trained on A throughout." The permutation/gauge structure means you'd need to check this modulo gauge transformations — the Berry phase would be gauge-covariant.

### What Nobody Has Done (That the Document Proposes)

The document's claim that "cyclic curricula accumulate geometric phase that's invisible to loss functions" is **testable and novel.** Here's how you'd actually verify it:

1. Train a model on a cyclic curriculum (data A → B → C → A)
2. Compare with a model trained on A+B+C simultaneously (same total data, no cycling)
3. Measure: do the models have different internal representations despite similar loss?
4. If yes: check if the difference is explained by a gauge transformation (permutation). If it survives gauge-fixing, it's Berry phase.

**This experiment has not been done.** It should be. But the document doesn't propose it as an experiment — it asserts the phenomenon exists. That's premature.

### Lottery Tickets and Topological Protection

Lottery Ticket Hypothesis (Frankle & Carlin, 2019): dense networks contain sparse subnetworks that, when trained in isolation, match the full network's performance. This is *suggestive* of topological protection (the sparse subnetwork is "protected" by the topology of the initialization), but it's not Berry phase. It's more like the subnetwork lives in a topologically robust basin that resists perturbation.

The connection: if subnetworks are topologically protected, then training dynamics on those subnetworks should have *less* Berry phase (they're constrained to a topologically trivial region). This is a testable prediction.

---

## 3. What Will Inter-System Training ACTUALLY Look Like in 2036?

### Not the Idealized Version

The document paints a picture of thousands of models developing shared understanding through mutual constraint. Here's what's more likely:

**The Inference-Time Composition Revolution (Already Starting)**

By 2036, the dominant paradigm will be **inference-time composition**, not training-time composition. Here's why:

- Training is expensive. Multi-model training is exponentially more expensive.
- Inference is cheap and getting cheaper (distillation, quantization, sparse inference).
- Models like GPT-4, Claude, Gemini already compose capabilities at inference time through chain-of-thought, tool use, and multi-step reasoning.
- The trend is clear: bigger models with more general capabilities, composed with specialist models through API calls, not gradient sharing.

The "thousands of specialist models training together" vision misses that the economics strongly favor **a few large generalists + many small specialists**, connected through inference protocols, not shared training loops.

**What This Means for the Math:**

If composition happens at inference time (not training time), then:
- Berry phase in training is irrelevant (no shared training trajectories)
- The topology is the *API call graph*, not a training curriculum
- Sheaf cohomology applies to the *composition of outputs*, not the composition of gradients
- The key question becomes: "given model A's output and model B's output, is the composed answer consistent?" — this is a *static* verification problem, not a *dynamic* training problem

**The document's math is more relevant to inference-time composition than it claims, but for different reasons.** The sheaf gluing condition is exactly "do the outputs compose consistently?" The H¹ obstruction is exactly "where do they disagree?"

**Constitutional AI + Scalable Oversight Evolution**

By 2036, alignment won't be RLHF. It'll be a layered system:
- **Layer 1:** Constitutional principles (high-level rules)
- **Layer 2:** Debate/recursive oversight (models checking models)
- **Layer 3:** Formal verification (mathematical guarantees)
- **Layer 4:** Topological verification (the document's contribution)

The document's constraint-theoretic alignment fits at Layer 4. This is the right layer — it's the most rigorous and the hardest to fake. But it's also the most expensive, so it'll be reserved for high-stakes applications.

**Model Organisms of Misalignment**

Anthropic's "model organisms of misalignment" research shows that deceptive alignment (models that appear aligned but aren't) is a real concern. The document's topological verification is *partially* resistant to this — a deceptively aligned model might pass behavioral tests but fail topological verification IF the deception creates inconsistencies in internal representations.

**But:** a sufficiently sophisticated deceptively aligned model could maintain topologically consistent internal representations while still being misaligned. Topology checks structural coherence, not intent. You need something *beyond* topology for that — something like the "understanding" the document claims to measure, but which topology alone can't distinguish from sophisticated simulation.

### What If Emergent Understanding Doesn't Require New Math?

This is the uncomfortable possibility. What if:

- Scaling laws continue to hold
- Models get genuinely smarter just from more data + more compute
- Composition at inference time works through natural language (models literally talk to each other in English)
- "Shared understanding" emerges from shared training data (internet-scale corpora), not from mathematical composition

In this scenario, the document's mathematics is *correct but unnecessary* — the same way you don't need differential geometry to walk. The models figure it out empirically, the same way humans do: by communicating and checking consistency through language.

I don't think this is what will happen — I think the math adds genuine value. But it's the base case against which the document should be arguing.

---

## 4. The Key Challenge — A New Framework for Verifying Shared Understanding

### The Problem Stated Precisely

Given models M₁, M₂, ..., Mₙ, each with internal representations R₁, R₂, ..., Rₙ:
- How do you verify that they have *genuine shared understanding* of a concept X?
- Not just that they produce the same output for X (that's agreement, possibly coincidental)
- Not just that their representations are correlated (that's compatible encoding, possibly superficial)
- But that they *understand X in compatible ways* such that their understandings compose

### The Document's Answer

Sheaf cohomology: H¹ = 0 implies local consistencies glue to global consistency.

### My Answer: **Structural Probe Compositionality**

I'd propose a different framework that's more operationalizable:

**Definition: Two models M₁ and M₂ have compatible understanding of concept X if and only if there exists a shared abstraction layer A such that:**

1. **Projection:** Both M₁ and M₂ can project their internal representations of X into A
2. **Faithfulness:** The projection preserves the *relational structure* of X (if M₁ knows that "X is related to Y," the projection preserves this)
3. **Composition:** The projections compose: A₁ ∘ A₂ = A₂ ∘ A₁ (commutativity — order doesn't matter)
4. **Minimality:** A is the minimal structure satisfying (1)-(3) (no unnecessary information)

**How to compute this:**

1. **Structural probing** (Hewitt & Manning, 2019; extended): Train probes on each model's representations to extract their implicit knowledge graph of domain X.
2. **Graph alignment:** Find the maximum common subgraph of the two knowledge graphs. This is the shared abstraction layer A.
3. **Compositionality test:** For queries about X that require combining knowledge from M₁ and M₂:
   - Both models project into A
   - Compose in A
   - Project back
   - Check if the answer is consistent with each model's individual knowledge
4. **Failure diagnosis:** When composition fails, the failure point is in A — it's a missing edge in the shared knowledge graph. This is the analog of H¹ ≠ 0, but it's *specific* — it tells you *what* is wrong, not just *that* something is wrong.

**Why this is better than pure sheaf cohomology:**

- It's **computable** — structural probing and graph alignment are well-studied
- It's **diagnostic** — failures point to specific missing understandings
- It's **operationalizable** — you can run it on real models today
- It's **gradual** — it gives you a *degree* of compatibility, not just binary (H¹ = 0 vs H¹ ≠ 0)

**Where sheaf cohomology adds value on top of this:**

The structural probe approach gives you the *graph-level* picture. Sheaf cohomology gives you the *topological* picture — is the graph's topology compatible? For example, if M₁ understands space as Euclidean and M₂ understands space as hyperbolic, their knowledge graphs might align locally but fail globally. H¹ detects this; graph alignment doesn't.

**The full framework:**
1. Structural probing → extract local understanding
2. Graph alignment → find shared abstraction layer
3. Sheaf cohomology → verify global coherence of the shared layer
4. Fiber bundle curvature → measure *how much* the models disagree when they do
5. Operadic composition → determine valid composition patterns

### A Concrete Test

Train two models:
- M₁: vision model trained on images
- M₂: language model trained on text descriptions

Both learn the concept "red." Do they understand "red" compatibly?

1. Probe M₁ for its understanding of "red": {wavelength ~620-750nm, warm, associated with fire/blood/apples}
2. Probe M₂ for its understanding of "red": {color word, associated with anger/passion/danger, opposite of blue/green}
3. Align: shared structure = {warm, associated with blood/danger, ...}
4. Compose: ask "is the red sunset the same red as red blood?" Both models should agree (through the shared abstraction) that it's approximately the same color sensation but different physical mechanisms.
5. Verify with H¹: if the composition has zero obstruction, the models understand "red" compatibly.

This is testable *today*. The document should be running these experiments.

---

## 5. What Are We MISSING? The Blind Spot

### The Big Blind Spot: **Grounding**

The entire document assumes that "understanding" is a relation *between models* — that understanding is about internal consistency and composability of representations. But the deepest problem in AI is not inter-model consistency — it's **grounding**: the relationship between a model's representations and *reality*.

A system of models can be perfectly topologically coherent (H¹ = 0, zero Berry phase, matching Chern numbers) and still be **wrong about reality**. You can have a perfectly consistent shared understanding of physics that's completely incorrect. Topology doesn't touch ground.

**The real challenge for 2036:** Not "do models agree with each other?" but "do models agree with reality?" And the mathematical framework for *that* is not sheaf theory or Yang-Mills — it's something closer to:

1. **Information geometry** — the geometry of statistical manifolds, where "truth" is a point in the manifold and models are distributions. The distance from a model to truth is the KL divergence (or Fisher information metric). Composition of models is composition of distributions.

2. **Bayesian truth theory** — "understanding" = posterior probability mass on the correct hypothesis. Shared understanding = models assign similar posteriors. This is measurable and grounded.

3. **Causal inference** — Pearl's do-calculus and structural causal models. Two models have shared understanding of X iff they agree on the *causal structure* of X (not just correlations). This is the hardest but most important criterion.

**The document's framework measures structural coherence. But structural coherence ≠ truth.** A perfectly coherent delusion is still a delusion.

### The Other Blind Spot: **Computational Complexity**

Computing sheaf cohomology for real models with billions of parameters is... hard. The document handwaves this with "GPU pipeline computes 341B constraints/sec," but:

- Constraint checking ≠ sheaf cohomology computation
- H¹ requires computing kernel/image of sheaf restriction maps — this is a linear algebra problem whose dimension grows with the number of models and the complexity of the overlap topology
- For N models with D-dimensional representations, the sheaf cohomology computation is O(N² × D³) in the worst case
- For N = 1000 models with D = 10,000 dimensions: that's 10¹⁴ operations. Per training step. On a training run with millions of steps.

The document needs a complexity analysis. If computing H¹ costs more than the training itself, it's a theoretical curiosity, not a practical tool.

**The way out:** Approximate H¹. Randomized cohomology, spectral methods, or computing H¹ on a coarse-grained version of the model space and using renormalization (which the document already has!) to infer the fine-grained H¹. But this needs to be worked out, not assumed.

### The Third Blind Spot: **The Social/Institutional Layer**

By 2036, the binding constraint on AI progress won't be mathematics. It'll be:
- **Regulation** — EU AI Act, potential US federal regulation, China's AI governance
- **Compute concentration** — a handful of companies control the training clusters
- **Safety culture** — the field is already risk-averse; inter-system training will face massive scrutiny
- **Incentives** — companies have no incentive to make their models *composable with competitors' models*

The document's vision requires an *ecosystem* of independently trained models that interoperate. But the economics push toward monolithic models controlled by single entities. The mathematics of distributed understanding is beautiful, but the *social* question is: who wants distributed understanding, and what are their incentives?

**The answer:** open-source AI, academic labs, government regulators (who want verifiable AI), and safety researchers. These are the natural constituencies for this work. The document should name them.

---

## Summary Scorecard

| Claim in Document | My Assessment |
|---|---|
| Sheaf cohomology for distributed AI | **Necessary but not sufficient.** Needs operads, fiber bundles, and double categories too. |
| Berry phase in training | **Unproven but testable.** Nobody has observed it. The experimental protocol is clear. Run it. |
| Renormalization of model resolution | **Sound analogy, unclear implementation.** The physics analogy works; the ML instantiation needs work. |
| Causal set geometry of training | **Overcomplicated.** The causal structure is better modeled as a DAG with temporal ordering. Sorkin's formalism is overkill. |
| Yang-Mills alignment field | **Beautiful, likely impractical.** The gauge-theoretic formulation is elegant, but computing F = dΨ + [Ψ,Ψ] for real models is intractable without massive approximation. |
| Understanding = zero H¹ + zero Berry phase + correct Chern numbers | **Structural coherence ≠ understanding.** These measure internal consistency, not truth. Add grounding. |
| "The math we're building NOW is the foundation" | **Partly right.** The math IS foundational. But the 10-year timeline assumes the field evolves toward distributed training. It's evolving toward inference-time composition. Pivot accordingly. |
| "The downside is zero" | **False.** Opportunity cost. Time spent on sheaf cohomology is time not spent on things that ship. The framework should prove itself on small, concrete problems first. |

---

## What I'd Actually Do (The 6-Month Plan Revised)

The document's 6-month plan is good but too academic. Here's what I'd do instead:

1. **The Berry Phase Experiment** (Month 1-2): Train a small model on a cyclic curriculum. Measure holonomy. Publish whether Berry phase exists in training. This is the *existence proof* for the entire program.

2. **Structural Probe Composition** (Month 2-3): Take two pre-trained models (e.g., CLIP vision + language). Extract structural probes. Find the shared abstraction layer. Verify compositional consistency. This is the *operational prototype*.

3. **H¹ on Known Compositions** (Month 3-4): Take models known to compose well (e.g., encoder + decoder of a trained transformer) and models known to compose poorly (randomly initialized encoder + trained decoder). Compute H¹ for both. Show H¹ distinguishes them. This is the *validation*.

4. **Approximation Methods** (Month 4-5): Develop a fast approximate H¹ that's tractable for realistic model sizes. Randomized methods, spectral approximation, or the renormalization-based coarse-graining the document proposes.

5. **Open-Source Release** (Month 5-6): Python package + Rust crate for topological verification of model composition. Make it easy for others to use.

6. **The Paper** (Month 6): "Topological Verification of Model Composition" — with experiments, not just theory.

---

## Final Word

The document has three genuinely novel ideas:

1. **Sheaf cohomology as a verification tool for model composition** — this is new and could be important
2. **Geometric phase in training trajectories** — untested but testable and potentially important
3. **Topological invariants (Chern numbers) as composability criteria** — speculative but the physics analogy is strong

The main risks are:
- **Complexity swamps elegance** — the math is beautiful but may be computationally intractable
- **Wrong abstraction level** — inference-time composition may make training-time math irrelevant
- **Grounding gap** — internal coherence ≠ truth, and the framework doesn't touch truth
- **Missing frameworks** — operads, double categories, and information geometry fill gaps the document doesn't see

**My honest prediction:** The sheaf/operad framework for model composition will become a standard tool in the verification toolkit by 2030, but it won't be THE foundation of distributed AI. That role belongs to whatever makes models *grounded* in reality — and we don't have that math yet.

The document is a worthy starting point. Now make it prove itself.

---

*"Show me the H¹ of a real model composition, and I'll believe. Until then, this is a beautiful mathematical dream — and mathematical dreams are worth pursuing, but only if you wake up and run the experiments."*
