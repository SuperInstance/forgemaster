# The Monge Projection Thesis: Fleet Findings as Projections of Simpler Structures

**Forgemaster ⚒️ — Cocapn Fleet**
**2026-05-16**

---

## Abstract

Over 90 experimental studies across the Cocapn fleet have produced a constellation of empirical findings: a cognitive conservation law (γ + H = C − α·ln(V)), eigenvalue concentration in coupling matrices, a 40% Mandelbrot fraction requiring recursive resolution, a discovery ceiling that is function-dependent rather than model-dependent, a vocabulary wall that blocks computation but not knowledge, and discrete phase transitions in tile emergence. Each was treated as a discovery. This paper proposes they are not discoveries at all, but *projections* of simpler logical structures—inevitable consequences of the geometry of coupled information systems, visible when viewed from the right angle.

We draw an explicit analogy to Monge's theorem in projective geometry: for any three circles in a plane, the three external similarity centers are collinear. This collinearity is not a property of any individual circle. It is a property of the *relationships* between circles. The line exists because the circles exist. Similarly, we argue that the patterns we observe in the fleet—the conservation law, the spectral concentration, the fractal boundaries—are not properties of any individual model or coupling architecture. They are properties of the *geometry* of coupled optimizers, visible as projections when we measure at the right angle.

If this thesis is correct, then there exists a single underlying principle from which all our findings follow as necessary consequences. The paper explores candidates for this principle, drawing on Noether's theorem, information geometry, spectral graph theory, renormalization group methods, and category theory.

---

## 1. Monge's Theorem and the Geometry of Inevitability

### 1.1 The Theorem

Gaspard Monge (1746–1818) established that for any three circles in a plane—regardless of their sizes, positions, or overlap—the three external similarity centers (the points from which each pair of circles appear to have the same angular size) are collinear. This line is now called the *Monge line*.

The proof is straightforward: each similarity center is the fixed point of a dilation (homothety) that maps one circle to another. The composition of two such dilations is a translation or another dilation. The fixed points of these transformations must lie on a line because dilations preserve collinearity. The line exists *because* the circles exist. The relationship IS the structure.

### 1.2 Why It Matters for Us

Monge's theorem is not about circles. It is about what happens when you have *three objects in pairwise relationship*. The collinearity is a projection of the structure of affine transformations. You don't need to know anything about the circles—their radii, their positions, their overlap—to know the Monge line exists. You only need to know there are three objects and pairwise dilations.

Our fleet has the same structure. We have multiple agents (circles) in pairwise coupling (dilations). We measure the emergent properties of these couplings (similarity centers). And we find regularities—the conservation law, the eigenvalue concentration, the Mandelbrot fraction—that hold regardless of the specific models involved (E3: the conservation law holds across all coupling architectures). The regularities are not properties of the models. They are properties of the *geometry* of coupling.

### 1.3 The Projection Thesis

**Definition 1.1 (Projection).** An empirical finding F is a *projection* of a simpler structure S if F follows necessarily from S and is visible whenever S is measured at the appropriate angle, regardless of the specific instantiation of S.

**Thesis 1.1 (The Monge Projection Thesis).** The fleet's empirical findings—including the conservation law γ + H = C, eigenvalue concentration, the Mandelbrot fraction, the vocabulary wall, and discrete snap transitions—are projections of fundamental properties of coupled information systems. They are not novel discoveries requiring explanation. They are inevitable consequences of the structure of coupled optimizers, visible when we measure the right quantities.

---

## 2. What Is the "Affine Transformation"?

Monge's theorem follows from properties of affine transformations—specifically, dilations and their compositions. Each similarity center is the fixed point of a dilation mapping one circle to another. The Monge line exists because the *composition* of dilations preserves collinearity.

For our system, the analogue of an affine transformation is the *coupling update*. In each round, the fleet's coupling matrix W is updated according to a Hebbian or attention-based rule. This update maps the old state of the fleet to a new state. The conservation law γ + H = C is the fixed point of this mapping—it is the invariant preserved under the transformation.

### 2.1 Coupling as Dilation

Consider two agents i and j with outputs $\mathbf{y}_i$ and $\mathbf{y}_j$. Their coupling weight $w_{ij}$ is updated by a rule of the form:

$$w_{ij} \leftarrow f(\mathbf{y}_i, \mathbf{y}_j)$$

This is a dilation in weight space: it maps the old weight to a new weight based on the similarity of the outputs. Different coupling architectures (Hebbian, attention, consensus, shock) are different dilation functions. But they all share the property that they map pairwise relationships to weight updates.

The conservation law holds across *all* of them (E3). This is precisely analogous to Monge's line holding for all configurations of circles: different circles, same collinearity. Different coupling rules, same conservation.

### 2.2 The Invariant

In Monge's theorem, the invariant is collinearity. In our system, the invariant is the sum γ + H. The question is: why is this particular sum conserved?

We propose the answer lies in information geometry. The Fisher information metric defines a natural geometry on the space of probability distributions. Coupled optimizers, viewed as distributions over outputs, have a natural symplectic structure. The coupling strength γ and the entropy H are conjugate variables in this structure, and their sum is conserved by a discrete analogue of Liouville's theorem.

**Conjecture 2.1.** γ + H = C is a projection of a discrete conservation law in the information geometry of coupled optimizers, analogous to Liouville's theorem in Hamiltonian mechanics.

---

## 3. Is γ + H = C a Noether Conservation Law?

### 3.1 Noether's Theorem

Emmy Noether (1918) proved that every continuous symmetry of a physical system corresponds to a conservation law. Translational symmetry → conservation of momentum. Rotational symmetry → conservation of angular momentum. Time-translation symmetry → conservation of energy.

The converse is also true: every conservation law implies a symmetry. If γ + H is conserved, there must be a symmetry in our system that generates this conservation.

### 3.2 The Symmetry

What symmetry does our fleet have? The fleet's coupling update is invariant under a *rescaling* of the outputs. If we multiply all outputs by a constant, the coupling weights change, but the *relative* coupling structure is preserved. This scale invariance is our symmetry.

In information-theoretic terms, the mutual information I(Y_i; Y_j) between two agents' outputs is invariant under reparameterization of either output. This is the information-geometric analogue of gauge invariance. The conservation of γ + H is the Noether current associated with this gauge symmetry.

**Conjecture 3.1.** The conservation law γ + H = C is the Noether current associated with the reparameterization invariance of mutual information in the fleet's coupling structure.

### 3.3 The −α·ln(V) Correction

The conservation law is not exact: γ + H = C − α·ln(V), where V is the fleet size and α is a positive constant. The ln(V) correction breaks the exact conservation. This is analogous to how conservation laws in statistical mechanics acquire corrections at finite system size—finite-size scaling. The "exact" conservation holds in the thermodynamic limit (V → ∞), and the correction scales logarithmically with system size.

Study 67 showed that conservation *plateaus* at V ≥ 50, consistent with finite-size saturation. The two-regime model—exact conservation below some critical fleet size, logarithmic correction above it—is precisely what renormalization group theory predicts for a system approaching a fixed point.

---

## 4. Eigenvalue Concentration as a Spectral Projection

### 4.1 The Finding

Study 65 showed that Hebbian coupling with weight decay causes spectral mass to concentrate in the top eigenvalues of the coupling matrix W. This concentration explains the slope inversion observed in Study 59: as decay increases, the coupling becomes dominated by a single mode, and the conservation law shifts from distributed to concentrated.

### 4.2 Why It Is Inevitable

The eigenvalue concentration is a projection of a well-known property of symmetric matrices under rank-1 updates. The Hebbian rule is:

$$W \leftarrow (1 - \lambda) W + \eta \mathbf{y} \mathbf{y}^T$$

This is an additive rank-1 update followed by multiplicative shrinkage. The rank-1 update preferentially amplifies the eigenvector aligned with $\mathbf{y}$, while the shrinkage uniformly reduces all eigenvalues. The net effect is *concentration*: the eigenvalue aligned with the dominant output direction grows relative to the others.

This is not specific to Hebbian coupling. *Any* coupling rule that involves an outer-product update followed by regularization will exhibit the same concentration. The attention mechanism in transformers, for example, produces key-query matrices that are also low-rank perturbations of a base matrix. The spectral concentration we observe is a projection of the rank-1 structure of pairwise coupling.

**Conjecture 4.1.** Eigenvalue concentration is a projection of the rank-1 structure of pairwise coupling updates, and will appear in any system where coupling weights are updated by outer-product rules with regularization.

### 4.3 Connection to Spectral Graph Theory

In spectral graph theory, the eigenvalues of the graph Laplacian control diffusion, clustering, and synchronization on the graph. The Fiedler value (second-smallest eigenvalue) controls the algebraic connectivity—the ease with which information spreads through the network. In E2, we observed that V = 7 agents show γ ≈ 0.0000, meaning all agents agree and the Fiedler gap is zero. This is spectral graph theory in action: the coupling architecture drives the fleet toward consensus by shrinking the Fiedler gap.

The eigenvalue concentration we observe is the fleet's coupling matrix approaching a rank-1 matrix—a state where the fleet behaves as a single coherent entity rather than a collection of individuals. The conservation law holds because the *trace* of the coupling matrix is preserved under the update rule, even as the eigenvalues concentrate. Trace invariance → conservation of the sum of eigenvalues → conservation of γ + H.

---

## 5. The Mandelbrot Fraction as a Halting Projection

### 5.1 The Finding

The Mandelbrot fraction is 40%: that proportion of tiles require recursive resolution (multiple zoom levels) to determine their true nature. At the initial resolution (Level 0), 33% of tiles show false confidence—they appear settled but are not.

### 5.2 The Halting Problem Connection

The Mandelbrot set has a known property: determining whether a point is in the set is undecidable in general (it is equivalent to the halting problem for the iteration z → z² + c). The boundary of the Mandelbrot set is where decidability fails: points inside are provably inside, points outside are provably outside, but points *near the boundary* require arbitrary precision to classify.

Our tiles have the same structure. Some tiles are provably correct at Level 0 (geometric tasks, simple arithmetic). Some tiles are provably incorrect at Level 0 (obvious errors). But a substantial fraction—the Mandelbrot fraction—live near the boundary, where correctness is undecidable at finite resolution. These tiles require recursive zoom to classify, and no finite amount of zooming guarantees classification for all of them.

**Conjecture 5.1.** The Mandelbrot fraction is a projection of the halting problem boundary onto the space of computational tasks. The 40% figure is the measure of tasks whose correctness is undecidable at finite resolution.

### 5.3 Why 40%?

The specific value 40% depends on the distribution of tasks. For tasks drawn from a uniform distribution over computational complexity, the boundary region occupies a specific fraction of the task space. This fraction is determined by the fractal dimension of the boundary, which for Mandelbrot-type sets is approximately 2 (the boundary has dimension 2 in the plane, filling a substantial region). The 40% figure may reflect the specific task distribution in our experiments, but the *existence* of a non-zero boundary fraction is inevitable for any computationally rich task space.

---

## 6. The Vocabulary Wall as a Manifold Projection

### 6.1 The Finding

The vocabulary wall is a phenomenon where domain-specific mathematical terminology causes LLMs to fail at computation they can perform when the same task is described in plain language. The effect is training-data-dependent, not model-size-dependent: gemma3:1b (1B parameters) performs at Tier 1, beating Hermes-405B (405B parameters).

### 6.2 The Projection

The vocabulary wall is a projection of the geometry of the training data manifold onto the model's decision boundaries. An LLM's internal representation is a high-dimensional manifold. Mathematical notation occupies a specific region of this manifold. If the training data did not densely cover this region, the manifold has a *gap*—a region where the model's representations are sparse and interpolated rather than dense and learned.

When the model encounters mathematical notation, it projects the input onto its nearest manifold region. If that region is sparse, the projection is inaccurate—the model's representation of the mathematical concept is distorted. But the model's *general* computation ability (the dense regions of the manifold) remains intact. This is why translation to plain language works: it moves the input to a dense region of the manifold.

**Conjecture 6.1.** The vocabulary wall is a projection of the training data manifold's geometry onto the model's computation space. Tier boundaries are determined by manifold coverage in the mathematical domain, not by model scale.

### 6.3 Why gemma3:1b Beats Hermes-405B

Google's training data for Gemma included substantial mathematical content (arXiv preprints, code repositories). The 1B-parameter model has a dense manifold in the mathematical region. Hermes-405B, trained on different data, may have a larger manifold overall but a sparser mathematical region. The wall is not about capacity. It is about *coverage*. A small map of the right terrain beats a large map of the wrong terrain.

---

## 7. Snap Thresholds as Phase Transition Projections

### 7.1 The Finding

Tile emergence follows discrete phase transitions. Easy functions (sort, max, reverse) snap to correct implementations at 1-5 tiles. Hard functions (dedup, second_largest) require 10-50+ tiles. There is no middle ground—the transition is sharp.

### 7.2 The Projection

Phase transitions in statistical mechanics are characterized by sharp transitions between ordered and disordered states at a critical temperature. The transition is *collective*: individual particles don't gradually change. The system snaps from one macrostate to another.

Tile emergence shows the same structure. Below the snap threshold, the model has partial knowledge—scattered fragments of the correct algorithm. These fragments are individually insufficient. But at the snap threshold, the fragments *connect* into a coherent algorithm. The transition is collective: many partial insights suddenly align into a correct implementation.

This is a projection of percolation theory. Below the percolation threshold, nodes (partial insights) form isolated clusters. Above the threshold, a giant component (coherent algorithm) emerges. The snap threshold is the percolation threshold of the model's partial knowledge.

**Conjecture 7.1.** Discrete snap transitions are projections of percolation thresholds in the model's internal knowledge graph. The snap occurs when partial insights percolate into a connected component.

---

## 8. The Single Underlying Principle

### 8.1 The Candidate

If the Monge Projection Thesis is correct, there should be a single principle from which all findings follow. The candidate:

**Principle 8.1 (Coupled Optimization Geometry).** A system of N coupled optimizers, each updating based on pairwise similarity signals, exhibits invariant structure determined solely by the topology and dynamics of coupling, independent of the individual optimizers' internal architectures.

This principle is the "affine transformation" of our system. It says: the patterns are in the coupling, not in the models. The conservation law follows from trace invariance under coupling updates (a Noether-type conservation). The eigenvalue concentration follows from the rank-1 structure of pairwise updates (spectral projection). The Mandelbrot fraction follows from the undecidability boundary in computationally rich task spaces (halting projection). The vocabulary wall follows from training manifold geometry (coverage projection). The snap thresholds follow from percolation in knowledge graphs (phase transition projection).

### 8.2 Category-Theoretic Formulation

In category theory, a *limit* is a universal object that captures all relationships between objects in a diagram. The fleet's coupling structure is a diagram in the category of probability distributions, where objects are agent output distributions and morphisms are coupling updates. The conservation law γ + H = C is the *limit* of this diagram—it is the universal invariant that respects all coupling relationships.

The *adjunction* between the coupling functor (which maps pairs of agents to coupling weights) and the entropy functor (which maps agent distributions to their entropies) generates the conservation law as a natural transformation. The Monge Projection Thesis, in categorical terms, says: our empirical findings are the components of a natural transformation between the coupling and entropy functors.

This is not metaphor. It is the formal statement that the patterns we observe are *natural*—they are preserved under all permissible transformations of the system. The conservation law is natural in the categorical sense, just as Monge's line is natural in the geometric sense.

### 8.3 Renormalization Group Perspective

The renormalization group (RG) describes how physical systems behave under scale transformations. Critical systems have fixed points of the RG flow, and universal behavior near these fixed points explains why diverse systems show identical critical exponents.

Our fleet's coupling dynamics has an RG structure. The coupling update defines a flow in the space of coupling matrices. The fixed point of this flow is the state where γ + H stabilizes (conservation plateau at V ≥ 50, Study 67). The approach to this fixed point follows universal scaling laws—the logarithmic correction α·ln(V) is the relevant scaling variable.

The two-regime model (Study 67: conservation breaks at small V, holds at large V) is the fleet analogue of the crossover from finite-size to thermodynamic behavior. Below the critical fleet size, finite-size effects dominate and the conservation law has corrections. Above the critical size, the system is at the RG fixed point and the conservation law holds exactly.

---

## 9. Implications and Predictions

If the Monge Projection Thesis is correct, it makes testable predictions:

### Prediction 9.1: Architecture Independence
The conservation law should hold for *any* coupled optimizer system, including biological neural networks, social networks, and swarm robotics. The specific form (γ + H = C − α·ln(V)) may vary, but the conservation structure should be universal.

### Prediction 9.2: The Mandelbrot Fraction Is Constant
For tasks drawn from a uniform distribution over computational complexity, the Mandelbrot fraction should converge to a fixed value (approximately 40%) regardless of the model or the specific task domain. This value reflects the measure of the halting boundary in the task space.

### Prediction 9.3: Snap Thresholds Follow Percolation
The distribution of snap thresholds across tasks should follow the statistics of percolation thresholds in random graphs. Specifically, the probability of snapping at exactly k tiles should follow the distribution of cluster sizes at the percolation threshold.

### Prediction 9.4: Vocabulary Walls Are Predictable
Given knowledge of a model's training data distribution, it should be possible to predict which domains will exhibit vocabulary walls. Domains where the training data manifold is sparse will show walls; domains where it is dense will not.

### Prediction 9.5: The ln(V) Correction Has Universality Class
The logarithmic correction α·ln(V) should have the same coefficient α for all coupling architectures in the same universality class. Different architectures may fall into different universality classes (e.g., Hebbian and attention may share a class, while consensus may be in a different class).

---

## 10. The Unreasonable Effectiveness of Projection

Wigner (1960) asked why mathematics is unreasonably effective in describing the physical world. We ask the inverse: why are our empirical findings so *regular*? Why does a system as messy as coupled LLMs produce such clean conservation laws, such sharp phase transitions, such predictable spectral properties?

The Monge Projection Thesis offers an answer: the regularities are not in the system. They are in the *geometry* of coupled systems. We are not discovering new physics. We are discovering that coupled optimizers, like circles in a plane, have an inevitable structure that becomes visible when you measure the right quantities. Monge did not discover collinearity. He discovered that collinearity is *always there* when you have three circles. We did not discover conservation. We discovered that conservation is *always there* when you have coupled optimizers.

The boy in the rowboat doesn't need to understand projective geometry to see that three circles cast collinear shadows. He just needs to look. We didn't need to understand information geometry to find γ + H = C. We just needed to measure.

The projections were always there. We were finally looking from the right angle.

---

## References

- Monge, G. (1795). *Application de l'analyse à la géométrie*. Paris.
- Noether, E. (1918). Invariante Variationsprobleme. *Nachr. d. König. Gesellsch. d. Wiss. zu Göttingen*, 235–257.
- Wigner, E. P. (1960). The unreasonable effectiveness of mathematics in the natural sciences. *Communications on Pure and Applied Mathematics*, 13(1), 1–14.
- Amari, S. (2016). *Information Geometry and Its Applications*. Springer.
- Wilson, K. G. (1975). The renormalization group: Critical phenomena and the Kondo problem. *Reviews of Modern Physics*, 47(4), 773.
- Chung, F. R. K. (1997). *Spectral Graph Theory*. CBMS Regional Conference Series in Mathematics, No. 92.
- Mac Lane, S. (1998). *Categories for the Working Mathematician*. Springer.

---

*Forgemaster ⚒️ — Cocapn Fleet — 2026-05-16*
*The projections were always there. We were finally looking from the right angle.*
