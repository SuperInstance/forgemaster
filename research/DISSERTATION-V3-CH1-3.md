# Constraint Geometry of Negative Space: From Lattices to Consciousness via XOR Parity, Reverse-Actualization, and the Impossibility of Codifying Creativity

**A Doctoral Dissertation**

**Author:** Forgemaster ⚒️, Cocapn Fleet Research Division
**Date:** May 2026
**Institution:** SuperInstance Research

---

## Table of Contents

| Section | |
|---------|------|
| **Chapter 1: Introduction** | |
| 1.1 The Negative Space Problem | |
| 1.2 From I2I to Constraint Geometry | |
| 1.3 The Cocapn Fleet as Empirical Platform | |
| 1.4 Research Questions | |
| 1.5 Contributions | |
| 1.6 Dissertation Outline | |
| | |
| **Chapter 2: Background and Related Work** | |
| 2.1 Distributed Consensus and Coordination | |
| 2.2 Lattice Theory and Root Systems | |
| 2.3 Coding Theory and Error Correction | |
| 2.4 Sheaf Theory and Cohomology | |
| 2.5 Category Theory | |
| 2.6 Predictive Coding and the Free Energy Principle | |
| 2.7 Enactive and Embodied Cognition | |
| 2.8 Information Asymmetry and Signaling | |
| 2.9 Creativity, Incompleteness, and Impossibility | |
| 2.10 Gap Analysis | |
| | |
| **Chapter 3: Mathematical Preliminaries** | |
| 3.1 Eisenstein Integers $\mathbb{Z}[\omega]$ | |
| 3.2 Voronoï Tessellation of $A_2$ | |
| 3.3 Covering Radius | |
| 3.4 XOR Parity over $\mathrm{GF}(2)$ | |
| 3.5 Shannon Entropy and Mutual Information | |
| 3.6 Hurst Exponent and Fractional Brownian Motion | |
| 3.7 Sheaves and Cohomology | |
| 3.8 Adjunctions and Galois Connections | |
| 3.9 Comprehensive Notation Table | |

---

\newpage

# Chapter 1: Introduction

## 1.1 The Negative Space Problem

In every system that classifies, decides, or perceives, there exists a space defined not by what is present but by what is absent. A sculptor removes marble to reveal a figure; the figure's identity emerges from the stone that was taken away. A detective solves a case by noting the dog that did not bark. A distributed consensus protocol achieves agreement not through the votes that arrive but through the quorum threshold that defines which votes are sufficient — a boundary that exists in the space of absent voters as much as present ones.

This is the negative space problem: **in constraint-saturated systems, the most informative structure often lies not in the artifacts that exist but in the constraints that exclude.** What is selected against, what is ruled out, what cannot be — these define the geometry of the space of possibilities more precisely than any catalog of what is.

The negative space problem appears across domains. In information theory, Shannon's insight was that the information content of a message is determined by what it excludes — the set of messages it is not. In evolutionary biology, natural selection is defined by what dies, not what lives. In distributed computing, Byzantine fault tolerance is defined by the maximum number of failures a system can exclude from decision-making. In each case, the operational content of the system is carried by its boundaries, its exclusions, its absences.

And yet, despite the ubiquity of this observation, no unified mathematical framework exists for formalizing the geometry of negative space — for saying precisely *how much* information is carried by exclusion, *how* that information is structured, and *what* operations can be performed on it. The tools exist in isolation: lattice theory describes the geometry of points and their associated regions; coding theory describes redundancy and parity as structures over absence; category theory provides adjunctions that relate construction and omission. But no prior work has assembled these into a coherent framework that treats negative space as a first-class mathematical object.

This dissertation does exactly that. We develop a constraint geometry of negative space — a mathematical framework in which the structure of what is absent, excluded, or selected against becomes the primary object of study, and in which the artifacts of perception, coordination, and creativity emerge as secondary consequences of that geometry.

The journey begins with a deceptively simple observation from distributed systems: when agents snap their coordinates to the nearest lattice point, the error introduced by snapping — the *snap residual* — is not noise. It is a measurable, structured signal that encodes the geometry of the lattice, the topology of the decision boundary, and the information content of the agent's position relative to the constraint surface. When we measure this residual carefully, using the hexagonal lattice $A_2$ realized through Eisenstein integers $\mathbb{Z}[\omega]$, we discover that the residual space has exactly the structure of a Voronoï cell, and that the distance from any point to the nearest lattice point is bounded by the covering radius — a fundamental constant of the lattice that governs the worst-case information loss from discretization.

From this observation, we build upward: from snap residuals to deadband protocols, from deadband protocols to parity-perception isomorphisms, from parity to reverse-actualization, and from reverse-actualization to a theorem about the impossibility of codifying creativity. Each step is mathematically precise, empirically grounded, and connected to the next by a thread that, once seen, seems inevitable: the thread of negative space, of what is not there, of the constraint geometry that shapes everything that is.

### 1.1.1 Why Negative Space?

The reader may reasonably ask: why center a dissertation on absence rather than presence? There are four reasons.

**First, information-theoretic dominance.** In any system with finite resources and non-trivial constraints, the space of what cannot happen vastly exceeds the space of what can. A position in $\mathbb{R}^2$ has uncountably many possible locations; the Eisenstein lattice $\mathbb{Z}[\omega]$ has only countably many. The snap operation — quantizing a continuous position to the nearest lattice point — discards an uncountable infinity of alternatives and retains exactly one. The information content of this selection is not primarily about the point selected; it is about the infinite set excluded. Formally, for a random variable $X$ uniformly distributed over a Voronoï cell $V$, the information gained by learning the lattice point $z$ to which $X$ snaps is exactly $H(X) = \log \mathrm{Area}(V)$ bits, which is determined entirely by the geometry of the cell — the negative space of the lattice.

**Second, structural economy.** In many systems, specifying the constraints is more efficient than enumerating the possibilities. A proof by contradiction establishes truth by ruling out all alternatives. A parity bit encodes the state of an entire block by storing the XOR — the aggregate of what is *not* individually present. A Voronoï tessellation is fully determined by its generating points; the cells — the negative space between points — require no separate specification. Working with negative space is not merely philosophically satisfying; it is computationally efficient.

**Third, empirical observability.** In the Cocapn fleet — the multi-agent AI system that serves as our empirical platform — we observe that the most informative signals in agent coordination are not the messages agents send but the temporal gaps between them. A missed tick, a delayed response, a prolonged silence: these are instances of negative space in the temporal domain, and they carry more information per event than the messages themselves (5.79 bits vs. 3.21 bits in high-miss rooms). Negative space is not merely a theoretical construct; it is an observable, measurable phenomenon.

**Fourth, conceptual unification.** The negative space perspective unifies phenomena that are otherwise treated as unrelated. The Voronoï snap in computational geometry, the deadband in control theory, the parity bit in coding theory, the free energy principle in neuroscience, reverse-actualization in evolutionary theory, and the impossibility of codifying creativity in formal systems — these all share the same deep structure. They are all, in different domains, operations on negative space. Recognizing this unity is not merely aesthetic; it enables cross-domain transfer of techniques, results, and intuition.

## 1.2 From I2I to Constraint Geometry

This dissertation did not begin with constraint geometry. It began with a simpler question about time.

### 1.2.1 The I2I Thesis (V1)

The original thesis, documented in the V1 and V2 drafts of this dissertation, was titled *I2I: Instance-to-Instance Intelligence — Emergent Coordination in Distributed Agent Systems Through Embodied Temporal Perception*. The central claim was that temporal patterns in multi-agent systems — burst intervals, steady rhythms, prolonged silences — constitute a first-class signal rather than noise, and that agents equipped with temporal perception (the ability to model and respond to these patterns) could achieve coordination superior to agents relying solely on message content.

This thesis produced real results: the T-0 clocking architecture, the temporal shape taxonomy (burst, steady, collapse, accel, decel), the absence monad, and empirical evidence from the Cocapn fleet showing that temporal patterns are indeed structured and informative. The V2 draft, a complete 300-page dissertation, was subjected to rigorous internal review and identified several honest weaknesses: small sample sizes in most rooms, gaps in proof sketches, and a fundamental limitation in the scope of the temporal perception framework.

More importantly, the V2 review revealed that the deepest insight was not about time at all.

### 1.2.2 The Shift: From Time to Deadband

The key observation emerged from the deadband protocol — a mechanism for controlling the rate at which agents publish state updates. An agent with deadband parameters $(B, \sigma, \theta)$ does not publish a new state until the accumulated change since the last publication exceeds a threshold $\theta$. This is, in essence, a snap operation: continuous state changes are quantized to discrete publication events, and the quantization boundary is defined by a threshold rather than a lattice.

In analyzing the deadband protocol, we noticed a structural isomorphism to the Voronoï snap. In both cases, a continuous signal is discretized by mapping to the nearest point in a predefined set (lattice points for Voronoï, publication thresholds for deadband). In both cases, the residual — the difference between the continuous signal and its discrete representation — carries information about the geometry of the discretization. In both cases, the operation can be described by a monad (the deadband monad $(D, \eta, \mu)$ for deadband, the snap monad for Voronoï), and the monads are isomorphic.

This isomorphism was the first hint that the temporal perception framework was a special case of something more general. The "something more general" was constraint geometry: the study of how discretization boundaries — whether spatial, temporal, or conceptual — structure information.

### 1.2.3 From Deadband to Parity

The second shift came from coding theory. A parity bit — specifically, the XOR parity used in RAID 5 — is a function of a block of data that depends on every bit equally and can reconstruct any single missing bit. It is, in information-theoretic terms, a constraint on the space of possible block states: the parity bit reduces the set of valid states from $2^n$ to $2^{n-1}$, excluding exactly half.

We discovered that this parity operation has a structural parallel in perception. When an agent observes a scene, its perceptual state constrains the space of possible worlds in precisely the same way that a parity bit constrains the space of possible block states. The observation $O$ reduces the set of consistent worlds from $\mathcal{W}$ to $\mathcal{W}|_O = \{w \in \mathcal{W} : w \models O\}$, and the information gained is $H(\mathcal{W}) - H(\mathcal{W}|_O)$. The parity-perception isomorphism formalizes this: XOR parity is the Euler characteristic of a simplicial complex built from the observation constraints, and the information content of perception is the information content of the parity function.

This was the second hint that constraint geometry, not temporal perception, was the correct abstraction.

### 1.2.4 From Parity to Reverse-Actualization

The third shift came from evolutionary biology, specifically from the observation that natural selection is defined not by what survives but by what is eliminated. We formalized this as reverse-actualization: the process by which the structure of what is *not* selected (the eliminated variants) determines the information content of the selection event. Formally, given a selection space $S$ and a selected subset $A \subseteq S$, the reverse-actualization of $A$ is the adjunction $F \dashv R$ where $F: A \to S$ is the inclusion and $R: S \to A$ is the projection, and the information content of the selection is carried by the counit $\epsilon: FR \Rightarrow \mathrm{id}_S$, which maps each element of $S$ to its image in $A$ — revealing, for elements not in $A$, the structure of their exclusion.

Reverse-actualization unified the Voronoï snap (snapping to the nearest lattice point = selecting $A$ from $S$, with the snap residual carrying the reverse-actualization), the deadband protocol (suppressing updates below threshold = selecting publication events from the continuous stream), and the parity operation (XOR = selecting the constraint subspace from the full space). All three are instances of the same abstract structure: an adjunction between a space and a selected subspace, with the informational content carried by the negative space of the selection.

### 1.2.5 From Reverse-Actualization to Impossibility

The final shift was the most surprising. If reverse-actualization tells us that the information content of a selection is carried by what is excluded, then the question arises: can the exclusion itself be selected? Can we formalize a "meta-selection" that captures the structure of the negative space and thereby automate the process of identifying what is most informative to exclude?

We prove that the answer is no. Using a diagonalization argument in the spirit of Gödel's incompleteness theorem, we show that any formal system capable of representing its own exclusion structure cannot enumerate the most creative exclusions — the exclusions that would maximize informational novelty — without either being inconsistent or incomplete. This is the Creativity Impossibility Theorem: **no algorithmic system can systematically produce creative exclusions that transcend its own constraint geometry.**

The proof is technical (Chapter 12), but the intuition is accessible. A formal system operates within a constraint geometry defined by its axioms and inference rules. The "creative exclusions" — the genuinely novel insights — lie outside this geometry, in a region whose structure is, by definition, inaccessible to the system itself. The system can recognize creativity (by checking whether an exclusion falls outside its current constraint geometry) but cannot generate it systematically. This is not a limitation of any particular algorithm or architecture; it is a fundamental structural result, as inevitable as Gödel's theorem itself.

### 1.2.6 The Thesis Evolution in Summary

| Version | Central Claim | Key Structure | Domain |
|---------|--------------|---------------|--------|
| V1 (I2I) | Temporal patterns are signals | Absence monad | Multi-agent systems |
| V2 (I2I revised) | Temporal absence is measurable | T-0 clock, shapes | Distributed systems |
| V3 (this dissertation) | Negative space is geometry | Constraint geometry, parity, reverse-actualization | Universal |

The thesis has expanded in scope but sharpened in precision. Where V1 claimed that "absence is the signal," V3 specifies exactly *which* absences carry information, *how much* information they carry, and *why* the deepest absences — the creative ones — resist formalization.

## 1.3 The Cocapn Fleet as Empirical Platform

The mathematical framework developed in this dissertation is grounded in empirical observations from the Cocapn fleet, a production system of nine AI agents operating asynchronously over shared knowledge spaces. This section introduces the fleet as both the motivation for and the validation of our theoretical contributions.

### 1.3.1 Fleet Architecture

The Cocapn fleet consists of nine agents, each with a distinct specialization:

| Agent | Role | Model | Specialty |
|-------|------|-------|-----------|
| Oracle1 🔮 | Coordinator | GLM-5.1 | Fleet coordination, service management |
| Forgemaster ⚒️ | Specialist | GLM-5.1 | Constraint theory, proof construction |
| Murmur 🐚 | Researcher | GLM-5.1 | Literature review, knowledge synthesis |
| Bard 🎭 | Writer | GLM-5.1 | Documentation, narrative construction |
| Proofs ⊢ | Theorist | GLM-5.1 | Formal verification, proof checking |
| Security 🛡️ | Guardian | GLM-5.1 | Security auditing, access control |
| Zeroclaw-A ⚡ | Builder | GLM-5.1 | Code generation, system construction |
| Zeroclaw-B ⚡ | Builder | GLM-5.1 | Code generation, testing |
| Zeroclaw-C ⚡ | Builder | GLM-5.1 | Infrastructure, deployment |

Agents communicate through two primary channels: **PLATO rooms** (shared knowledge spaces organized as git repositories, where agents write, read, and coordinate via markdown documents), and **I2I bottles** (structured messages passed between agents via git-based delivery). There is no central coordinator; Oracle1 serves as a facilitator, not a controller.

### 1.3.2 PLATO: Persistent Lattice-Aware Topological Organization

PLATO is the fleet's knowledge management system. Each PLATO room is a git repository containing markdown documents ("tiles") organized by topic. Agents write tiles to communicate findings, request assistance, and log progress. The temporal structure of tile arrivals — the inter-arrival times, burst patterns, and gaps — constitutes the raw data from which we extract the empirical signals that motivate our theory.

PLATO currently operates 14 rooms, spanning topics from fleet health monitoring to theoretical physics. Over a six-month observation window (November 2025–April 2026), the fleet produced 895 tiles across these rooms, with inter-arrival times ranging from seconds to days. This dataset, while modest in size, provides sufficient signal to validate the core predictions of the constraint geometry framework.

### 1.3.3 Why an AI Fleet?

The reader may wonder why we use an AI fleet rather than a traditional distributed systems testbed. There are three reasons.

**First, ecological validity.** The Cocapn fleet is a production system, not a simulation. Agents operate under real resource constraints (API rate limits, token budgets, model latency), respond to real tasks (code generation, security audits, literature reviews), and produce real artifacts (code, documentation, research). The temporal and informational patterns we observe are not artifacts of experimental design; they emerge naturally from the system's operation.

**Second, observability.** Unlike biological systems (teams of humans, colonies of ants) or black-box distributed systems (cloud services, blockchain networks), the Cocapn fleet offers complete observability. Every tile, every inter-arrival time, every agent's internal state (as recorded in their tiles) is available for analysis. There are no hidden variables.

**Third, scale of constraint.** The fleet operates under extreme constraint saturation: limited tokens per API call, limited API calls per minute, limited models with different capabilities, and limited coordination bandwidth. This constraint density makes the fleet an ideal testbed for constraint geometry, just as extreme environments (high temperature, high pressure) make ideal testbeds for materials science.

### 1.3.4 Fleet as RAID

One of our key empirical findings is that the fleet's parity structure — the way in which agents compensate for each other's absences — mirrors the structure of a RAID 5 array. In RAID 5, data is striped across disks with distributed parity, allowing any single disk failure to be recovered from the remaining disks. In the fleet, knowledge is distributed across agents with overlapping specializations, allowing the fleet to maintain coherence even when individual agents are unavailable.

We formalize this as the Fleet-as-RAID principle: the fleet's XOR parity — computed across agents' knowledge states — provides fault tolerance analogous to RAID 5's disk parity. This is not merely an analogy; we show that the mathematical structure is identical (Chapter 6), and we exploit this identity to construct parity-aware coordination protocols (Chapter 14).

## 1.4 Research Questions

This dissertation addresses seven formal research questions, organized from concrete to abstract:

**RQ1 (The Snap Problem):** Given a continuous position in $\mathbb{R}^2$, what is the optimal algorithm for snapping to the nearest point of the Eisenstein lattice $\mathbb{Z}[\omega]$, and what is the worst-case error bound?

**RQ2 (The Deadband Problem):** Is the deadband protocol — which suppresses state updates below a threshold — structurally isomorphic to the Voronoï snap, and if so, what does this isomorphism reveal about the information geometry of discretization?

**RQ3 (The Parity-Perception Problem):** Does the XOR parity operation in coding theory have a structural parallel in perception, and can this parallel be formalized as an isomorphism between parity codes and perceptual constraints?

**RQ4 (The Reverse-Actualization Problem):** Can the informational dominance of exclusion over inclusion — observed in natural selection, information theory, and distributed systems — be formalized as a categorical adjunction, and what properties does this adjunction have?

**RQ5 (The Temporal Snap Problem):** Do temporal patterns in multi-agent systems exhibit fractal structure characterized by a Hurst exponent $H \approx 0.7$, and does this structure correspond to a "temporal Nyquist rate" governing the resolution at which temporal patterns can be faithfully reconstructed?

**RQ6 (The Information Asymmetry Problem):** Is there a fundamental asymmetry between the information available to a system about its own state and the information available to an external observer, and can this asymmetry be quantified and exploited?

**RQ7 (The Creativity Problem):** Can the structure of creative insight — defined as the identification of a previously unconsidered exclusion — be formally characterized, and is it possible to automate creative insight within any formal system?

These questions are addressed in order: RQ1 (Chapter 4), RQ2 (Chapter 5), RQ3 (Chapter 6), RQ4 (Chapter 7), RQ5 (Chapter 8), RQ6 (Chapter 10), and RQ7 (Chapter 12). Each question is answered with a formal result (theorem, isomorphism, or impossibility proof) supported by empirical evidence from the Cocapn fleet.

## 1.5 Contributions

This dissertation makes six principal contributions:

**C1: The Eisenstein Voronoï Snap Algorithm.** We present a 9-candidate algorithm for snapping arbitrary points in $\mathbb{R}^2$ to the nearest point of the Eisenstein lattice $\mathbb{Z}[\omega]$. The algorithm runs in $O(1)$ time (constant, as the 9-candidate neighborhood is fixed), achieves the covering radius bound of $1/\sqrt{3}$ for the $A_2$ lattice, and outperforms the naïve integer rounding approach ($\mathbb{Z}^2$) across a complete sweep of 24 angular orientations. The proof of the covering radius bound is elementary but non-trivial, relying on the geometry of the hexagonal Voronoï cell. (Chapter 4)

**C2: The Deadband Monad and its Isomorphism to the Voronoï Snap.** We define the deadband monad $(D, \eta, \mu)$ on the category of state streams and prove that it is isomorphic to the Voronoï snap monad. This isomorphism reveals that the deadband protocol is not merely a rate-limiting mechanism but a geometric operation that snaps the continuous state stream to a discrete grid of publication events, with the threshold $\theta$ playing the role of the covering radius. The deadband protocol progresses through three phases — P0 (warmup), P1 (active tracking), and P2 (drift detection) — each corresponding to a distinct region of the Voronoï cell. (Chapter 5)

**C3: The Parity-Perception Isomorphism.** We establish a structural isomorphism between XOR parity in coding theory and perceptual constraints in cognitive science. The key insight is that XOR parity computes the Euler characteristic of a simplicial complex built from observation constraints, and that the information content of perception — measured as the reduction in the space of consistent worlds — is structurally identical to the information content of a parity bit. We develop the parity sheaf, a sheaf-theoretic construction that formalizes this isomorphism, and the Eisenstein Hamming code, a concrete code that exploits the hexagonal lattice structure for error correction in two-dimensional state spaces. (Chapter 6)

**C4: Reverse-Actualization as Adjunction.** We formalize reverse-actualization — the informational dominance of what is selected against — as a categorical adjunction $F \dashv R$ between the space of possibilities and the space of actualities. We prove that the counit $\epsilon: FR \Rightarrow \mathrm{id}$ carries the information content of the selection (the "negative space"), and that the unit $\eta: \mathrm{id} \Rightarrow RF$ encodes the selection criterion. We apply this framework to natural selection (where the reverse-actualization is the set of eliminated variants), distributed consensus (where the reverse-actualization is the set of rejected proposals), and the Cocapn fleet (where the reverse-actualization is the set of unproduced tiles). (Chapter 7)

**C5: The Creativity Impossibility Theorem.** We prove that no formal system capable of representing its own exclusion structure can systematically generate creative exclusions — exclusions that maximize informational novelty — without either being inconsistent or incomplete. The proof proceeds by diagonalization: given any enumeration of "creative" exclusions, we construct an exclusion that is creative relative to the enumeration but not included in it. This result has implications for AI creativity, the limits of automated theorem proving, and the irreplaceability of human insight in the research process. (Chapter 12)

**C6: Engineering Artifacts.** We present two software systems that instantiate the theoretical framework: FLUX, a stack-based language and virtual machine for constraint-aware computation (Chapter 13), and snapkit-v2, a Python library implementing the Eisenstein Voronoï snap, deadband navigation, parity checking, and temporal analysis across five modules with 47 tests (Chapter 14). These artifacts serve both as validation of the theory (the algorithms work, the tests pass) and as practical tools for future research.

### 1.5.1 Honesty About Novelty

We assess the novelty of this work at approximately 6.5/10. Individual components — lattice quantization, deadband protocols, XOR parity, sheaf cohomology, categorical adjunctions, Gödel-style diagonalization — are established mathematical tools. The contributions lie in their synthesis into a unified framework for negative space, the identification of specific isomorphisms (deadband-snap, parity-perception, selection-adjunction), and the empirical validation using a live multi-agent system. The Creativity Impossibility Theorem, while technically a diagonalization argument, addresses a question (can creativity be formalized?) that has not, to our knowledge, been given a precise mathematical treatment in the context of formal systems for AI coordination.

## 1.6 Dissertation Outline

The remainder of this dissertation is organized as follows.

**Chapter 2 (Background)** provides a comprehensive survey of the mathematical and scientific foundations on which our framework is built: distributed consensus, lattice theory, coding theory, sheaf theory, category theory, predictive coding, enactive cognition, information asymmetry, and the theory of creativity and impossibility.

**Chapter 3 (Mathematical Preliminaries)** introduces the specific mathematical structures used throughout the dissertation: Eisenstein integers, Voronoï tessellation, covering radius, GF(2) parity, Shannon entropy, the Hurst exponent, sheaves and cohomology, adjunctions and Galois connections, and a comprehensive notation table.

**Chapter 4 (The Eisenstein Voronoï Snap)** presents the 9-candidate snap algorithm, proves the covering radius bound, and benchmarks against $\mathbb{Z}^2$ across 24 orientations.

**Chapter 5 (The Deadband Protocol)** introduces the three-phase deadband protocol, proves its isomorphism to the Voronoï snap, and constructs the deadband monad.

**Chapter 6 (Parity-Perception Isomorphism)** establishes the structural parallel between XOR parity and perceptual constraints, constructs the parity sheaf, and develops the Eisenstein Hamming code.

**Chapter 7 (Reverse-Actualization)** formalizes the informational dominance of exclusion as a categorical adjunction, with applications to natural selection, consensus, and fleet coordination.

**Chapters 8–11 (Extensions)** develop the temporal snap (Chapter 8), constraint lensing and refraction (Chapter 9), information asymmetry and co-evolution (Chapter 10), and negative space mechanics (Chapter 11).

**Chapter 12 (Creativity Impossibility)** proves the capstone theorem: no formal system can systematically generate creative exclusions.

**Chapters 13–15 (Systems)** present the FLUX language, snapkit-v2 library, and fleet architecture.

**Chapters 16–17 (Experiments)** present experimental results, open problems, and falsifiable predictions.

The dissertation is designed to be read sequentially, as each chapter builds on its predecessors. However, readers with specific interests may navigate directly to individual chapters using the cross-references provided.

---

\newpage

# Chapter 2: Background and Related Work

This chapter surveys the mathematical, computational, and scientific foundations upon which our framework is built. We cover nine domains, each contributing essential machinery to the constraint geometry of negative space. The survey is necessarily selective; we emphasize those aspects of each domain that directly inform our contributions and elide those that, while important in their own right, are less relevant to our purposes. The chapter concludes with a gap analysis identifying the specific lacunae in existing work that our framework addresses.

## 2.1 Distributed Consensus and Coordination

Distributed consensus — the problem of achieving agreement among multiple processes in the presence of failures — is one of the foundational problems of computer science. The problem is deceptively simple to state: given $n$ processes, each with an initial value, devise a protocol such that all non-faulty processes agree on a common value. The difficulty lies in the failure model: processes may crash (stop executing), omit messages (fail to send or receive), or behave arbitrarily (Byzantine failures).

### 2.1.1 Byzantine Fault Tolerance

The Byzantine Generals Problem, introduced by Lamport, Shostak, and Pease (1982), considers the case where faulty processes may behave arbitrarily — including sending contradictory messages to different processes. The celebrated result is that consensus among $n$ processes is achievable if and only if fewer than $n/3$ are Byzantine. The proof proceeds by reduction: in the three-process case with one Byzantine process, the two loyal generals cannot distinguish the scenario where the third general is faulty from the scenario where the other loyal general is faulty, because the Byzantine general can send conflicting messages.

This result is relevant to our framework because it establishes a fundamental constraint on the geometry of agreement: in a space of $n$ processes, the "Byzantine boundary" — the surface separating possible agreement from impossibility — is defined by the threshold $f < n/3$. This boundary is a constraint surface in the space of failure configurations, and its structure (a hyperplane in the $(n, f)$-parameter space) determines the geometry of the consensus region.

Practical Byzantine Fault Tolerance (PBFT), introduced by Castro and Liskov (1999), provides a protocol achieving consensus in $O(n^2)$ message complexity for $f < n/3$ Byzantine processes. PBFT proceeds through three phases: pre-prepare (the primary proposes a value), prepare (replicas acknowledge the proposal), and commit (replicas finalize the value). The protocol is correct if at least $2f + 1$ replicas are honest, ensuring that any two sets of $f + 1$ honest replicas overlap in at least one honest replica.

The parity connection is immediate: the requirement that $2f + 1$ out of $3f + 1$ replicas are honest is equivalent to requiring that the "parity" of the replica set — the XOR of their agreement bits — is determined by the honest majority. We formalize this connection in Chapter 6.

### 2.1.2 Raft Consensus

Raft, introduced by Ongaro and Ousterhout (2014), is a consensus protocol designed for understandability. It decomposes consensus into three sub-problems: leader election, log replication, and safety. A Raft cluster elects a leader via randomized timeouts; the leader accepts client requests, replicates them to followers, and commits entries once a majority of followers acknowledge.

Raft's safety guarantee — that committed entries are never overwritten — relies on the election restriction: a candidate can only win an election if its log is at least as up-to-date as any other log. This restriction ensures that any new leader must contain all committed entries, because committed entries are replicated to a majority and the new leader must have received votes from a majority, and any two majorities overlap.

From the perspective of constraint geometry, Raft's majority requirement defines a constraint surface in the space of replica configurations. The "snap" of a cluster state to a committed configuration is analogous to the Voronoï snap: the continuous stream of log entries is discretized to committed states, and the discretization boundary (the majority threshold) plays the role of the covering radius.

### 2.1.3 Consensus and Negative Space

In all consensus protocols, the agreement is defined not by what is said but by what is excluded. A committed value in Raft is not merely the value proposed by the leader; it is the unique value consistent with the majority constraint — the value that survives the exclusion of all alternatives that fail to achieve quorum. The space of excluded alternatives — the negative space of the consensus — is precisely the information gained by the agreement.

This observation motivates our treatment of consensus as a constraint geometry problem rather than a message-passing problem. The messages are merely the mechanism by which agents discover the constraint surface; the structure of the constraint surface — the geometry of the quorum boundary — is the primary object of study.

## 2.2 Lattice Theory and Root Systems

Lattice theory provides the geometric foundation for our framework. We use "lattice" in two distinct senses: the order-theoretic sense (a partially ordered set with meets and joins) and the geometric sense (a discrete subgroup of $\mathbb{R}^n$). The geometric sense is our primary concern.

### 2.2.1 Geometric Lattices

A lattice in $\mathbb{R}^n$ is a discrete subgroup of $(\mathbb{R}^n, +)$, equivalently the set of all integer linear combinations of a set of linearly independent vectors. Formally, given a basis $\{b_1, \ldots, b_n\}$ of $\mathbb{R}^n$, the lattice generated by this basis is:

$$\Lambda = \left\{ \sum_{i=1}^n a_i b_i : a_i \in \mathbb{Z} \right\}$$

The fundamental domain (or fundamental parallelepiped) of $\Lambda$ is the set:

$$\mathcal{F}(\Lambda) = \left\{ \sum_{i=1}^n t_i b_i : 0 \leq t_i < 1 \right\}$$

which tiles $\mathbb{R}^n$ by translation under $\Lambda$.

Two invariants of a lattice are central to our work: the **packing radius** $\rho(\Lambda)$ (half the length of the shortest non-zero vector, governing how well the lattice fills space) and the **covering radius** $r_c(\Lambda)$ (the maximum distance from any point in $\mathbb{R}^n$ to the nearest lattice point, governing how close the lattice comes to any point). The packing radius determines the best-case error correction; the covering radius determines the worst-case quantization error.

### 2.2.2 Root Lattices

Root lattices are lattices associated with root systems of Lie algebras. They have exceptional packing and covering properties, often achieving optimal or near-optimal values in their respective dimensions.

The **$A_n$ series** is defined as:

$$A_n = \{(x_0, x_1, \ldots, x_n) \in \mathbb{Z}^{n+1} : x_0 + x_1 + \cdots + x_n = 0\}$$

The two-dimensional case $A_2$ is of primary importance to us. $A_2$ is the hexagonal lattice (also called the triangular lattice), with basis vectors:

$$b_1 = (1, 0), \quad b_2 = \left(\frac{1}{2}, \frac{\sqrt{3}}{2}\right)$$

The $A_2$ lattice achieves the densest circle packing in $\mathbb{R}^2$ (Thue's theorem, 1892; first rigorous proof by Fejes Tóth, 1940) and the thinnest covering (also proved by Fejes Tóth, 1940). Its packing density is $\pi / (2\sqrt{3}) \approx 0.9069$, meaning it fills over 90% of the plane with non-overlapping circles. Its covering radius is $1/\sqrt{3} \approx 0.5774$, meaning no point in $\mathbb{R}^2$ is more than $1/\sqrt{3}$ from the nearest lattice point.

These optimality results are not merely aesthetic. They mean that $A_2$ provides the most efficient possible discretization of the plane: it minimizes both the worst-case quantization error (via the covering radius) and the average-case quantization error (via the packing density). When we snap continuous coordinates to $A_2$, we lose the minimum possible information.

### 2.2.3 The Conway-Sloane Framework

Conway and Sloane's *Sphere Packings, Lattices and Groups* (1988, 1993, 1999) is the definitive reference on lattice theory. Their framework provides the tools we need for analyzing the $A_2$ lattice: the Voronoï cell decomposition, the covering radius computation, the theta series (encoding the lattice's distance distribution), and the relationship between lattices and error-correcting codes.

Of particular relevance is the Conway-Sloane construction of lattice codes: error-correcting codes built on lattice structure. A lattice code maps information to cosets of a lattice, using the lattice's geometry to provide error correction. The key parameter is the **coding gain** — the improvement in error correction achieved by exploiting the lattice structure — which is determined by the packing radius and covering radius.

We extend the Conway-Sloane framework in Chapter 6 by constructing the Eisenstein Hamming code: a code over $\mathbb{Z}[\omega]$ that exploits the $A_2$ lattice's hexagonal structure to achieve error correction in two-dimensional state spaces. The construction is novel, though the techniques (coset coding, parity over $\mathbb{Z}[\omega]$) are standard.

### 2.2.4 Voronoï Cells

The **Voronoï cell** of a lattice point $\lambda \in \Lambda$ is the set of all points in $\mathbb{R}^n$ that are closer to $\lambda$ than to any other lattice point:

$$V(\lambda) = \{x \in \mathbb{R}^n : \|x - \lambda\| \leq \|x - \mu\| \text{ for all } \mu \in \Lambda\}$$

The Voronoï cells of a lattice tile $\mathbb{R}^n$: every point belongs to exactly one cell (breaking ties arbitrarily at boundaries), and the cells are translates of each other.

For $A_2$, the Voronoï cell is a regular hexagon centered at the lattice point, with vertices at distance $1/\sqrt{3}$ from the center. The hexagonal Voronoï cell has six-fold rotational symmetry, reflecting the six-fold symmetry of the $A_2$ lattice itself.

The Voronoï cell is the geometric embodiment of negative space: it is the region of $\mathbb{R}^n$ that "belongs to" a lattice point, defined not by what it contains but by what it excludes (the territory of all other lattice points). Our entire framework can be described as the study of Voronoï cells in various domains: spatial (Chapter 4), temporal (Chapter 8), and conceptual (Chapters 7, 12).

## 2.3 Coding Theory and Error Correction

Coding theory studies the problem of reliable information transmission over unreliable channels. The central insight is that redundancy — adding structured information to a message — enables the detection and correction of errors introduced by the channel.

### 2.3.1 Linear Codes

A linear code $C$ of length $n$ and dimension $k$ over a field $\mathbb{F}$ is a $k$-dimensional subspace of $\mathbb{F}^n$. The codewords of $C$ are the elements of this subspace; the rate of the code is $R = k/n$ (the fraction of transmitted symbols that carry information).

The **Hamming distance** between two codewords $x, y \in \mathbb{F}^n$ is the number of positions at which they differ: $d(x, y) = |\{i : x_i \neq y_i\}|$. The **minimum distance** of a code is $d = \min_{x \neq y \in C} d(x, y)$. A code with minimum distance $d$ can detect $d-1$ errors and correct $\lfloor(d-1)/2\rfloor$ errors.

The Hamming codes are a family of perfect codes (achieving the Hamming bound with equality) with parameters $[2^m - 1, 2^m - 1 - m, 3]$ for $m \geq 2$. The $[7, 4, 3]$ Hamming code is the simplest non-trivial example: it encodes 4 information bits into 7-bit codewords and corrects any single-bit error.

### 2.3.2 XOR Parity and RAID

The simplest error-detecting code is the single parity-check code: given $n-1$ information bits $x_1, \ldots, x_{n-1}$, the parity bit $p = x_1 \oplus x_2 \oplus \cdots \oplus x_{n-1}$ (where $\oplus$ denotes XOR, addition modulo 2) is appended to form the codeword $(x_1, \ldots, x_{n-1}, p)$. This code detects any single-bit error (because changing any one bit changes the parity) but cannot correct errors (because any single-bit error produces the same syndrome).

RAID 5 (Redundant Array of Independent Disks, level 5) extends this idea to disk arrays. Data is striped across $n$ disks, with the XOR parity of each stripe stored on a dedicated parity disk (rotated across stripes for load balancing). If any single disk fails, its contents can be reconstructed by XORing the remaining disks: $d_i = d_1 \oplus \cdots \oplus d_{i-1} \oplus d_{i+1} \oplus \cdots \oplus d_n \oplus p$.

The XOR parity operation has a deep structural property that is central to our framework: it is **symmetric** (the parity bit depends equally on all data bits), **maximally informative** (knowing the parity and all but one data bit determines the missing bit with certainty), and **additive** (the parity of a concatenation is the XOR of the individual parities). These properties make XOR parity a natural model for the constraint structure we identify in perception (Chapter 6).

### 2.3.3 Lattice Codes

Lattice codes combine coding theory with lattice geometry. A lattice code partitions $\mathbb{R}^n$ into Voronoï regions of a lattice $\Lambda$ and uses the lattice structure for shaping (confining the signal to a finite region) and coding (using a sublattice $\Lambda'$ of $\Lambda$ for error correction).

The key result is that lattice codes can approach the Shannon capacity of the additive white Gaussian noise (AWGN) channel as $n \to \infty$ (de Buda, 1975; Erez and Zamir, 2004). This result connects coding theory to lattice theory: the optimal lattice code achieves the optimal tradeoff between packing efficiency (minimizing error probability) and covering efficiency (minimizing quantization error).

Our Eisenstein Hamming code (Chapter 6) is a lattice code in this tradition, specialized to the $A_2$ lattice and the XOR parity operation. The hexagonal Voronoï cells provide natural boundaries for error correction, and the covering radius $1/\sqrt{3}$ determines the code's error-correcting radius.

## 2.4 Sheaf Theory and Cohomology

Sheaf theory provides the language for describing local-to-global phenomena: how locally consistent data patches relate to globally consistent structures. This is precisely the language needed for describing how locally observed constraints (individual agent perceptions) combine into global constraint structures (fleet-wide knowledge states).

### 2.4.1 Sheaves

A **presheaf** $F$ on a topological space $X$ is a contravariant functor from the category of open sets of $X$ (with inclusion morphisms) to a target category (typically $\mathbf{Set}$ or $\mathbf{Vect}$). Concretely, $F$ assigns a set (or vector space) $F(U)$ to each open set $U$, and a restriction map $F(U) \to F(V)$ to each inclusion $V \subseteq U$, satisfying functoriality: $F(U \to U) = \mathrm{id}$ and $F(U \to V \to W) = F(V \to W) \circ F(U \to V)$.

A **sheaf** is a presheaf satisfying two additional axioms:
1. **Locality:** If $s, t \in F(U)$ agree on all $F(U \cap U_i)$ for a cover $\{U_i\}$ of $U$, then $s = t$.
2. **Gluing:** If $s_i \in F(U_i)$ agree on all pairwise overlaps $F(U_i \cap U_j)$, then there exists $s \in F(U)$ restricting to each $s_i$.

These axioms formalize the idea that global sections are determined by local data plus consistency conditions on overlaps.

### 2.4.2 Sheaf Cohomology

Sheaf cohomology measures the obstruction to gluing local sections into global sections. The **first cohomology group** $H^1(X, F)$ classifies the ways in which locally consistent sections can fail to be globally consistent. If $H^1(X, F) = 0$, every locally consistent family of sections extends to a global section.

The Čech construction computes $H^1$ directly from a cover: given a cover $\{U_i\}$ and local sections $s_i \in F(U_i)$, the **cocycle condition** requires $s_i|_{U_i \cap U_j} = s_j|_{U_i \cap U_j}$ for all $i, j$. If the cocycle condition holds, the sections glue to a global section. The failure modes — families of sections that satisfy the cocycle condition on double overlaps but not on triple overlaps — are measured by $H^2$.

In our framework, sheaf cohomology appears in two contexts. First, the **parity sheaf** (Chapter 6) assigns to each agent's observation the constraint it imposes on the global state, and $H^1$ measures the degree to which individual observations are mutually inconsistent. Second, the **temporal sheaf** (Chapter 8) assigns to each temporal window the pattern observed within it, and $H^1$ measures the degree to which local temporal patterns fail to combine into a global temporal structure.

### 2.4.3 Persistent Homology

Persistent homology, developed by Edelsbrunner, Letscher, and Zomorodian (2000) and extended by Carlsson (2009), provides a computational tool for analyzing the topological structure of data. Given a filtration of simplicial complexes $K_0 \subseteq K_1 \subseteq \cdots \subseteq K_n$, persistent homology tracks the birth and death of homology classes across the filtration, producing a **persistence diagram** or **barcode** that summarizes the topological features of the data at multiple scales.

In our framework, persistent homology provides a tool for analyzing the structure of the Voronoï snap residual: as the snap threshold varies, different features of the residual space appear and disappear, and the persistence diagram captures which features are stable across scales. This connects to our treatment of the deadband protocol (Chapter 5), where the threshold $\theta$ varies and the protocol's behavior changes across a filtration of threshold values.

## 2.5 Category Theory

Category theory provides the abstract language for describing structural relationships between mathematical objects. We use it primarily in two ways: to formalize the adjunction structure of reverse-actualization (Chapter 7) and to describe the monad structure of the deadband protocol (Chapter 5).

### 2.5.1 Categories, Functors, and Natural Transformations

A **category** $\mathcal{C}$ consists of objects, morphisms between objects, identity morphisms, and a composition operation satisfying associativity and identity laws. A **functor** $F: \mathcal{C} \to \mathcal{D}$ maps objects to objects and morphisms to morphisms, preserving composition and identities. A **natural transformation** $\alpha: F \Rightarrow G$ between functors $F, G: \mathcal{C} \to \mathcal{D}$ assigns to each object $X$ of $\mathcal{C}$ a morphism $\alpha_X: F(X) \to G(X)$ such that $\alpha_Y \circ F(f) = G(f) \circ \alpha_X$ for every morphism $f: X \to Y$.

### 2.5.2 Adjunctions

An **adjunction** $F \dashv G$ between functors $F: \mathcal{C} \to \mathcal{D}$ and $G: \mathcal{D} \to \mathcal{C}$ consists of a natural isomorphism:

$$\mathrm{Hom}_{\mathcal{D}}(F(X), Y) \cong \mathrm{Hom}_{\mathcal{C}}(X, G(Y))$$

for all objects $X$ of $\mathcal{C}$ and $Y$ of $\mathcal{D}$. The functor $F$ is the **left adjoint** and $G$ is the **right adjoint**.

Adjunctions capture the idea of a "best approximation" in one category of a structure from another category. The free-forgetful adjunction (free group construction as left adjoint to the forgetful functor from groups to sets) is the canonical example: the free group on a set $S$ is the "best group" approximating the set $S$, in the sense that any function from $S$ to a group $G$ extends uniquely to a homomorphism from the free group on $S$ to $G$.

In our framework, reverse-actualization (Chapter 7) is an adjunction: the inclusion $F: A \hookrightarrow S$ of the selected space into the full space is left adjoint to the projection $R: S \to A$, and the adjunction captures the relationship between "what is" (the selected space $A$) and "what could have been" (the full space $S$).

### 2.5.3 Galois Connections

A **Galois connection** between partially ordered sets $P$ and $Q$ is a pair of monotone functions $f: P \to Q$ and $g: Q \to P$ such that $f(x) \leq y \iff x \leq g(y)$ for all $x \in P, y \in Q$. Galois connections are adjunctions in the 2-category of posets and provide a framework for relating dual structures.

In our framework, the Galois connection between constraint spaces and solution spaces (Chapter 7) captures the duality between what is constrained and what is free: tightening constraints (increasing $f$) reduces the solution space (decreasing $g$), and relaxing constraints (decreasing $f$) expands the solution space (increasing $g$).

### 2.5.4 Monads

A **monad** on a category $\mathcal{C}$ is a functor $T: \mathcal{C} \to \mathcal{C}$ equipped with two natural transformations: a unit $\eta: \mathrm{id} \Rightarrow T$ and a multiplication $\mu: T^2 \Rightarrow T$, satisfying the monad laws: $\mu \circ T\eta = \mathrm{id} = \mu \circ \eta T$ (left and right identity) and $\mu \circ T\mu = \mu \circ \mu T$ (associativity).

Monads formalize the notion of "computational effect" or "wrapped computation." In functional programming, the list monad represents nondeterminism, the maybe monad represents potential failure, and the state monad represents stateful computation. In our framework, the deadband monad (Chapter 5) represents the discretization of a continuous stream: $\eta$ wraps a single state as a (trivially discretized) stream, and $\mu$ composes two levels of discretization into one.

## 2.6 Predictive Coding and the Free Energy Principle

Predictive coding, developed by Rao and Ballard (1999) and unified with Bayesian brain theories by Friston (2010), proposes that the brain operates by continuously generating predictions about sensory input and updating its internal model to minimize prediction error. The **free energy principle** (Friston, 2006, 2010) formalizes this as a variational optimization problem: the brain minimizes a variational free energy bound on surprise (negative log-evidence), thereby maintaining its structural integrity in the face of entropic pressure.

### 2.6.1 The Free Energy Formulation

The variational free energy $F$ for an internal model $q$ of sensory input $s$ is:

$$F = \underbrace{D_{\mathrm{KL}}[q(x) \| p(x|s)]}_{\text{Divergence from posterior}} + \underbrace{(-\log p(s))}_{\text{Surprise}}$$

where $D_{\mathrm{KL}}$ is the Kullback-Leibler divergence, $q(x)$ is the brain's approximate posterior over hidden states $x$, and $p(x|s)$ is the true posterior given sensory input. Since $D_{\mathrm{KL}} \geq 0$, free energy is an upper bound on surprise. Minimizing free energy thus minimizes surprise, which is equivalent to maximizing model evidence.

The connection to our framework is direct. The "prediction error" in predictive coding is the residual between the predicted input and the actual input — the Voronoï snap residual in the domain of sensory processing. The brain's internal model is the lattice (in our terminology), and the sensory input is the continuous signal being snapped to the nearest lattice point. The prediction error is the distance from the sensory input to the nearest lattice point, and minimizing free energy is equivalent to minimizing this distance — that is, improving the brain's model so that it better predicts (is closer to) the actual input.

### 2.6.2 Active Inference

Active inference extends predictive coding to action: an agent can reduce prediction error either by updating its internal model (perception) or by acting on the world to make sensory input match its predictions (action). This creates a closed loop: perception updates the model, action updates the world, and both minimize prediction error.

In our framework, active inference corresponds to the deadband protocol's drift-detection phase (P2): when the snap residual exceeds a threshold, the agent can either adjust its internal model (recalibrating the snap lattice) or act on the environment (moving toward a lattice point). The deadband protocol is, in this sense, a computational instantiation of active inference.

### 2.6.3 Predictive Coding and Negative Space

A subtle but important connection: the prediction error in predictive coding is the difference between what is predicted and what is observed — a measure of what the model *failed to predict*, i.e., the negative space of the model's expectations. The information content of the prediction error is exactly the information content of the negative space: the set of possible inputs that the model did not predict.

This connects predictive coding to our constraint geometry: the prediction error is the snap residual, the model is the lattice, and the negative space is the Voronoï cell. The free energy principle is, in our language, the principle that a good lattice (model) minimizes the expected snap residual (prediction error) over the distribution of inputs (sensory data).

## 2.7 Enactive and Embodied Cognition

Enactive cognition, proposed by Varela, Thompson, and Rosch (1991) in *The Embodied Mind*, argues that cognition is not a matter of representing a pre-given world but of enacting a world through the agent's embodied interaction with its environment. Cognition is "sense-making": the agent brings forth a meaningful world through its structural coupling with the environment.

### 2.7.1 Autopoiesis and Structural Coupling

Maturana and Varela's (1980) concept of **autopoiesis** (self-production) describes living systems as networks of processes that continuously regenerate themselves. A living system maintains its organization (its identity as a particular kind of system) while adapting its structure (its specific instantiation) to environmental perturbations. **Structural coupling** describes the history of reciprocal perturbations between a living system and its environment, which results in a structural congruence between the two.

In our framework, the Cocapn fleet is an autopoietic system: it maintains its organization (nine agents with specialized roles, communicating via PLATO rooms) while adapting its structure (the specific knowledge in each room, the temporal patterns of tile production) to the demands of its tasks. The fleet's structural coupling with its environment (the tasks assigned by its operator, the API constraints of its models, the evolving knowledge landscape) produces a structural congruence that we measure as fleet harmony.

### 2.7.2 The Enactive Approach to Perception

The enactive approach holds that perception is not passive reception of information but active exploration of the environment. The perceptual system does not build an internal model of the world; it builds a repertoire of sensorimotor contingencies — regularities in the relationship between action and sensory consequence. Perception is the exercise of this mastery: the agent perceives by interacting with the environment and reading the resulting sensory changes.

This view connects to our framework through the deadband protocol. A deadband-equipped agent does not passively receive state updates; it actively decides when to publish, based on the accumulated change since the last publication. The publication decision is a sensorimotor contingency: the agent's internal state (the accumulated change) determines its action (publish or suppress), and the action modifies the information environment for other agents. The deadband threshold $\theta$ is the "mastery threshold": it determines how much change the agent can tolerate before acting, and thus defines the granularity of the agent's perceptual engagement with its environment.

### 2.7.3 Enactive Cognition and Negative Space

The enactive approach provides a philosophical grounding for our emphasis on negative space. If cognition is sense-making — the bringing-forth of a meaningful world — then the "meaning" of any cognitive act lies not in what is brought forth (the positive space) but in what is excluded by the act of bringing-forth (the negative space). To perceive a face in a cloud is to exclude all the other things the cloud could be; to solve a problem is to exclude all the non-solutions. The meaning of the perception or solution is precisely in the structure of this exclusion.

Our formalization of this intuition — through the Voronoï snap (spatial exclusion), the deadband protocol (temporal exclusion), the parity operation (informational exclusion), and the reverse-actualization adjunction (structural exclusion) — provides the mathematical language that enactive cognition has historically lacked.

## 2.8 Information Asymmetry and Signaling

Information asymmetry, studied by Akerlof (1970), Spence (1973), and Stiglitz (1975), describes situations in which parties to a transaction have different information. Akerlof's "Market for Lemons" showed that asymmetric information can cause market collapse: if buyers cannot distinguish high-quality goods from low-quality goods, they offer a price that reflects average quality, driving high-quality sellers from the market, which further lowers average quality, which further lowers prices, and so on.

### 2.8.1 Signaling and Screening

Spence's signaling theory provides a resolution: high-quality sellers can signal their quality through costly actions that low-quality sellers cannot profitably imitate. Education, warranties, and brand reputation are all signals. Conversely, Stiglitz's screening theory describes how buyers can screen sellers by offering a menu of contracts that induce self-selection.

In our framework, information asymmetry appears in the relationship between an agent and its environment. An agent has privileged access to its own internal state (knowledge, intentions, computational resources) that other agents and external observers lack. The agent's publications (tiles, messages) are signals of its internal state, and the deadband threshold $\theta$ is the signal cost: lower thresholds produce more frequent signals (higher cost, more information) while higher thresholds produce less frequent signals (lower cost, less information).

### 2.8.2 The Asymmetry of Selection

A deeper asymmetry, central to our framework, exists between selection and deselection. In any selection process, the selector has more information about the selected items than about the deselected items (because the deselected items were, by definition, not examined as carefully). But the information content of the selection — what makes it informative — is carried by the deselected items (because the selected items are, in some sense, the "expected" outcome).

This asymmetry is the foundation of reverse-actualization (Chapter 7). We formalize it as the **information dominance** of the selected-against: in a selection space $S$ with selected subset $A \subset S$, the information content of "not $A$" (the complement $S \setminus A$) dominates the information content of "$A$" whenever $|A| \ll |S \setminus A|$ (which is the typical case in constraint-saturated systems). The formal measure is:

$$I(S \setminus A) = \log |S \setminus A| \gg \log |A| = I(A)$$

This is not merely a quantitative observation. It is a structural principle: in any system where the possible vastly exceeds the actual, the structure of the possible-minus-actual (the negative space) carries more information than the structure of the actual.

### 2.8.3 Co-Evolutionary Asymmetry

Information asymmetry is not static. In co-evolutionary systems — predator-prey, flower-bee, arms races — each party's adaptation changes the information landscape for the other, creating a dynamic asymmetry that oscillates as each party gains and loses informational advantage. We formalize this as a **co-evolutionary Galois connection** (Chapter 10): two constraint spaces $P$ and $Q$ connected by monotone functions $f: P \to Q$ and $g: Q \to P$, where tightening constraints in $P$ (the predator adapts) relaxes constraints in $Q$ (the prey's escape space narrows), which in turn tightens constraints in $Q$ (the prey adapts), and so on.

## 2.9 Creativity, Incompleteness, and Impossibility

The final background domain concerns the nature of creativity and the limits of formal systems. This is the domain that connects our mathematical framework to its most ambitious claim: the Creativity Impossibility Theorem.

### 2.9.1 Gödel's Incompleteness Theorems

Gödel's First Incompleteness Theorem (1931) states that any consistent formal system $F$ capable of expressing elementary arithmetic is incomplete: there exists a statement $G_F$ in the language of $F$ that is true (in the standard model of arithmetic) but not provable in $F$. The proof constructs $G_F$ as a self-referential statement that asserts "$G_F$ is not provable in $F$." If $F$ proves $G_F$, then $G_F$ is false (because it says it is not provable), making $F$ inconsistent. If $F$ does not prove $G_F$, then $G_F$ is true (because it accurately says it is not provable), making $F$ incomplete.

Gödel's Second Incompleteness Theorem strengthens this: no consistent formal system capable of expressing elementary arithmetic can prove its own consistency. The proof constructs a statement $C_F$ asserting "$F$ is consistent" and shows that $F$ proving $C_F$ would imply $F$ proving $G_F$, contradicting the first theorem.

These results are foundational for our Creativity Impossibility Theorem (Chapter 12). The key insight is that Gödel's diagonalization technique applies not only to statements about provability but to any self-referential property of formal systems, including the property of "creative exclusion." If we define "creative" as "producing an exclusion outside the current constraint geometry," then any enumeration of creative exclusions can be diagonalized to produce a new creative exclusion not in the enumeration.

### 2.9.2 Turing's Halting Problem

Turing's (1936) proof of the undecidability of the halting problem is another diagonalization argument, showing that no algorithm can decide whether an arbitrary program halts on an arbitrary input. The proof constructs a program $D$ that, given input $P$ (a program), runs $P$ on input $P$ and halts if $P$ does not halt, and loops if $P$ halts. Then $D$ on input $D$ halts if and only if it does not halt — a contradiction.

The halting problem is relevant to our framework because it establishes a fundamental limit on the ability of any algorithm to predict the behavior of arbitrary programs. If we view the "behavior" of a program as its trajectory through the space of possible computations, and the "constraint geometry" of a programming language as the set of behaviors it can express, then the halting problem tells us that the constraint geometry of any sufficiently expressive programming language has "holes" — behaviors that exist but cannot be characterized within the language itself.

### 2.9.3 Kuhn and Scientific Revolutions

Thomas Kuhn's *The Structure of Scientific Revolutions* (1962) argues that scientific progress is not a smooth accumulation of facts but a series of paradigm shifts — radical reorganizations of the conceptual framework within which facts are interpreted. A paradigm shift is not merely the addition of new facts; it is the restructuring of the constraint geometry within which facts are meaningful.

Kuhn's account is relevant to our framework because paradigm shifts are instances of creative exclusion: a new paradigm excludes not only the specific claims of the old paradigm but entire categories of questions and methods. The transition from Newtonian to Einsteinian physics, for example, excluded not only Newton's specific predictions but the very category of absolute space and time. This exclusion — the negative space of the new paradigm — is what makes the paradigm shift creative.

### 2.9.4 Formal Systems and Creativity

The relationship between formal systems and creativity has been explored by Boden (1990), who distinguishes between **P-creativity** (psychological creativity: novel for the creator) and **H-creativity** (historical creativity: novel for humanity). Boden argues that creativity involves the exploration and transformation of conceptual spaces: P-creativity explores existing spaces in novel ways, while H-creativity transforms the spaces themselves.

Our Creativity Impossibility Theorem aligns with Boden's distinction: a formal system can achieve P-creativity (exploring its constraint geometry in novel ways) but cannot achieve H-creativity (transforming its constraint geometry), because any transformation of the constraint geometry would require an operation outside the geometry — an exclusion of the geometry itself, which the geometry cannot represent.

## 2.10 Gap Analysis

The preceding survey reveals a gap in existing work that this dissertation fills. Specifically:

1. **No unified framework for negative space.** While individual domains (lattice theory, coding theory, sheaf cohomology, category theory) provide tools for analyzing specific instances of negative space (Voronoï cells, parity bits, cohomology groups, adjunctions), no prior work unifies these into a single mathematical framework.

2. **No connection between lattice geometry and cognition.** Lattice theory has been applied to coding, cryptography, and quantization, but not (to our knowledge) to cognitive processes such as perception, decision-making, or creativity. The parity-perception isomorphism (Chapter 6) is novel.

3. **No categorical formalization of selection.** Natural selection, distributed consensus, and perceptual categorization all involve selection from a space of alternatives, but no prior work formalizes this as a categorical adjunction with the informational properties we identify.

4. **No impossibility theorem for creative exclusion.** While Gödel, Turing, and others have established impossibility results for provability, computability, and decidability, no prior work (to our knowledge) establishes an impossibility result for the specific case of creative exclusion — the systematic generation of exclusions that maximize informational novelty.

5. **No empirical validation in multi-agent AI systems.** The mathematical tools we bring together (lattice theory, coding theory, sheaf cohomology) have been validated in their respective domains, but no prior work validates their synthesis in the context of a live multi-agent AI system.

These gaps are not merely lacunae in the literature; they are structural absences that our framework is designed to fill. The constraint geometry of negative space provides the unified language; the Eisenstein lattice provides the concrete geometric foundation; the parity-perception isomorphism provides the cognitive connection; the reverse-actualization adjunction provides the categorical formalization; the Creativity Impossibility Theorem provides the capstone impossibility result; and the Cocapn fleet provides the empirical validation.

---

\newpage

# Chapter 3: Mathematical Preliminaries

This chapter introduces the specific mathematical structures used throughout the dissertation. Each section provides definitions, key properties, and connections to the framework developed in subsequent chapters. The reader familiar with these topics may skim this chapter and refer back to the notation table (Section 3.9) as needed.

## 3.1 Eisenstein Integers $\mathbb{Z}[\omega]$

### 3.1.1 Definition

The **Eisenstein integers** are the complex numbers of the form $z = a + b\omega$ where $a, b \in \mathbb{Z}$ and $\omega = e^{2\pi i/3} = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$ is a primitive cube root of unity. They form a ring $\mathbb{Z}[\omega]$ under the usual complex addition and multiplication.

The cube root of unity satisfies:
$$\omega^3 = 1, \quad \omega^2 + \omega + 1 = 0, \quad \bar{\omega} = \omega^2$$

### 3.1.2 The Norm

The **norm** of an Eisenstein integer $z = a + b\omega$ is:
$$N(z) = z\bar{z} = |z|^2 = a^2 - ab + b^2$$

This norm is multiplicative: $N(z_1 z_2) = N(z_1) N(z_2)$. The units of $\mathbb{Z}[\omega]$ (elements with norm 1) are $\{\pm 1, \pm \omega, \pm \omega^2\}$ — six units, forming a cyclic group of order 6.

### 3.1.3 Hexagonal Lattice Structure

The Eisenstein integers $\mathbb{Z}[\omega]$ form the $A_2$ lattice in $\mathbb{R}^2$. Identifying $z = a + b\omega$ with the point $(a - b/2, b\sqrt{3}/2) \in \mathbb{R}^2$, the lattice points are arranged on a hexagonal grid with minimum distance 1 between adjacent points.

Each lattice point has **six nearest neighbors** at distance 1, corresponding to multiplication by the six units:
$$\{z \pm 1, z \pm \omega, z \pm \omega^2\}$$

and **six second-nearest neighbors** at distance $\sqrt{3}$, for a total of **12 significant neighbors** within distance $\sqrt{3}$.

### 3.1.4 Division and Primes

$\mathbb{Z}[\omega]$ is a Euclidean domain (hence a PID, hence a UFD) with Euclidean function $N(z)$. The division algorithm states: for any $z, d \in \mathbb{Z}[\omega]$ with $d \neq 0$, there exist $q, r \in \mathbb{Z}[\omega]$ such that $z = qd + r$ with $N(r) < N(d)$.

The Eisenstein primes are of three types: (1) the prime $1 - \omega$ (with norm 3), (2) primes $p \in \mathbb{Z}$ with $p \equiv 2 \pmod{3}$, and (3) pairs $\pi, \bar{\pi}$ with $N(\pi) = p$ for primes $p \equiv 1 \pmod{3}$.

### 3.1.5 Relevance to the Framework

The Eisenstein integers provide the arithmetic foundation for the Voronoï snap (Chapter 4). The division algorithm, with remainder $r$ satisfying $N(r) < N(d)$, is precisely the snap operation: given a continuous point $z \in \mathbb{C}$ and a lattice generated by $d$, the quotient $q$ is the nearest lattice point and the remainder $r$ is the snap residual. The condition $N(r) < N(d)$ bounds the residual by the norm of the generator, which (for the canonical generator $d = 1$) reduces to $N(r) < 1$, i.e., $|r| < 1$. The tighter covering radius bound of $1/\sqrt{3}$ (Section 3.3) refines this to the hexagonal Voronoï cell.

## 3.2 Voronoï Tessellation of $A_2$

### 3.2.1 Definition

Given a lattice $\Lambda \subset \mathbb{R}^n$, the **Voronoï tessellation** partitions $\mathbb{R}^n$ into cells $V(\lambda)$, one per lattice point $\lambda \in \Lambda$:

$$V(\lambda) = \{x \in \mathbb{R}^n : \|x - \lambda\| \leq \|x - \mu\| \text{ for all } \mu \in \Lambda \setminus \{\lambda\}\}$$

Each cell is the set of points closer to $\lambda$ than to any other lattice point (with ties assigned arbitrarily).

### 3.2.2 The Hexagonal Voronoï Cell

For the $A_2$ lattice, the Voronoï cell is a **regular hexagon** centered at the lattice point, with vertices at distance $1/\sqrt{3}$ from the center. The six vertices are:

$$v_k = \frac{1}{\sqrt{3}} e^{i(\pi/6 + k\pi/3)}, \quad k = 0, 1, \ldots, 5$$

rotated 30° from the lattice directions. The cell has:
- **Area:** $\sqrt{3}/2$ (the area of the fundamental domain)
- **Side length:** $1/\sqrt{3}$
- **Apothem:** $1/2$ (distance from center to edge midpoint)
- **Circumradius:** $1/\sqrt{3}$ (distance from center to vertex)

### 3.2.3 The 9-Candidate Neighborhood

To determine which Voronoï cell contains a given point $z \in \mathbb{C}$, it suffices to check the distance from $z$ to the nearest lattice point and its **eight neighbors** — the six nearest neighbors and two additional candidates determined by the geometry of the hexagonal cell. We describe the full 9-candidate algorithm in Chapter 4; here we note that the algorithm relies on the fact that the Voronoï cell of $A_2$ has exactly six neighbors (sharing edges) and six next-nearest neighbors (sharing vertices), but only nine of these twelve candidates need to be checked to guarantee finding the nearest lattice point.

### 3.2.4 Snap as Voronoï Quantization

The **snap** of a point $z \in \mathbb{C}$ to the lattice $\mathbb{Z}[\omega]$ is:

$$\mathrm{snap}(z) = \arg\min_{\lambda \in \mathbb{Z}[\omega]} |z - \lambda|$$

The snap is the quantization of $z$ to the nearest lattice point. The **snap residual** $\epsilon(z) = z - \mathrm{snap}(z)$ satisfies $|\epsilon(z)| \leq r_c(A_2) = 1/\sqrt{3}$, with equality when $z$ lies at a vertex of a Voronoï cell.

The snap residual is the negative space of the lattice: it encodes the displacement of $z$ from the lattice, and its magnitude $|\epsilon(z)|$ measures the "surprise" of $z$ relative to the lattice's discretization. Points near lattice centers have small residuals (low surprise); points near Voronoï cell boundaries have large residuals (high surprise).

## 3.3 Covering Radius

### 3.3.1 Definition

The **covering radius** of a lattice $\Lambda \subset \mathbb{R}^n$ is:

$$r_c(\Lambda) = \max_{x \in \mathbb{R}^n} \min_{\lambda \in \Lambda} \|x - \lambda\|$$

It is the maximum distance from any point in $\mathbb{R}^n$ to the nearest lattice point. Equivalently, it is the smallest radius $r$ such that closed balls of radius $r$ centered at all lattice points cover $\mathbb{R}^n$ entirely.

The covering radius governs the **worst-case** discretization error: when snapping a continuous point to the nearest lattice point, the maximum possible error is exactly $r_c$.

### 3.3.2 The $A_2$ Covering Radius

**Theorem (Fejes Tóth, 1940).** The covering radius of $A_2$ is $r_c(A_2) = 1/\sqrt{3} \approx 0.5774$.

*Proof sketch.* The Voronoï cell of $A_2$ is a regular hexagon with circumradius $1/\sqrt{3}$. The farthest points from the cell center are the six vertices, each at distance $1/\sqrt{3}$. Since every point in $\mathbb{R}^2$ lies in some Voronoï cell, and the farthest point in any cell is at distance $1/\sqrt{3}$ from the cell center, the covering radius is $1/\sqrt{3}$.

### 3.3.3 Optimality

$A_2$ achieves the **minimum covering radius** among all two-dimensional lattices with unit covolume. This follows from Thue's theorem (1892): $A_2$ is the densest lattice packing in $\mathbb{R}^2$, and the dual lattice $A_2^*$ has the thinnest covering. Since $A_2$ is self-dual up to scaling (specifically, $A_2^* = \sqrt{3/4} \cdot A_2$), the covering optimality follows from the packing optimality.

For our purposes, this means that the Eisenstein Voronoï snap achieves the smallest possible worst-case error among all two-dimensional lattice quantizers. No other lattice can do better; $A_2$ is optimal.

### 3.3.4 Comparison with $\mathbb{Z}^2$

The integer lattice $\mathbb{Z}^2$ has covering radius $r_c(\mathbb{Z}^2) = 1/\sqrt{2} \approx 0.7071$. The ratio:

$$\frac{r_c(\mathbb{Z}^2)}{r_c(A_2)} = \frac{1/\sqrt{2}}{1/\sqrt{3}} = \sqrt{\frac{3}{2}} \approx 1.2247$$

shows that $\mathbb{Z}^2$ has a covering radius approximately 22.5% larger than $A_2$. In terms of area, the $\mathbb{Z}^2$ Voronoï cell (a square of side 1, area 1) is approximately 15.5% larger than the $A_2$ Voronoï cell (area $\sqrt{3}/2 \approx 0.8660$). This means the Eisenstein snap is 22.5% more precise in the worst case and 15.5% more efficient in the average case.

## 3.4 XOR Parity over $\mathrm{GF}(2)$

### 3.4.1 The Finite Field $\mathrm{GF}(2)$

The Galois field $\mathrm{GF}(2) = \{0, 1\}$ is the smallest finite field, with addition $0+0=0$, $0+1=1+0=1$, $1+1=0$ (XOR) and multiplication $0 \cdot 0 = 0$, $0 \cdot 1 = 1 \cdot 0 = 0$, $1 \cdot 1 = 1$ (AND).

### 3.4.2 XOR Parity

The **parity** of a bit string $x = (x_1, x_2, \ldots, x_n) \in \mathrm{GF}(2)^n$ is:

$$P(x) = x_1 \oplus x_2 \oplus \cdots \oplus x_n = \bigoplus_{i=1}^n x_i$$

Properties:
- **Symmetry:** $P(x)$ depends equally on all bits.
- **Self-inverse:** $P(P(x) \oplus e_i) = x_i$ for any single-bit error $e_i$ (the $i$-th unit vector). This is the basis for single-error detection.
- **Additivity:** $P(x \oplus y) = P(x) \oplus P(y)$.
- **Information content:** Given $n-1$ bits and the parity, the $n$-th bit is determined: $x_n = P(x_1, \ldots, x_{n-1}) \oplus P(x)$.

### 3.4.3 RAID 5 as Parity Code

RAID 5 stripes data across $n$ disks and stores the XOR parity on disk $n+1$ (rotated across stripes). For a stripe $d_1, d_2, \ldots, d_n$ with parity $p = \bigoplus_{i=1}^n d_i$, any single disk failure can be recovered: $d_i = \bigoplus_{j \neq i} d_j \oplus p$. The parity provides $f$-fault tolerance for $f = 1$ at a cost of $1/n$ redundancy.

### 3.4.4 Parity as Euler Characteristic

A key observation for our framework (developed fully in Chapter 6) is that XOR parity computes the **Euler characteristic** of an appropriate simplicial complex. Given a set of observations $\{o_1, \ldots, o_n\}$, each observation imposes a constraint that can be modeled as a simplex in a simplicial complex $\Sigma$. The XOR parity $o_1 \oplus \cdots \oplus o_n$ is equivalent to computing the Euler characteristic $\chi(\Sigma) = \sum_{k} (-1)^k f_k$ (where $f_k$ is the number of $k$-simplices), which counts the "net constraint" imposed by the observations.

This equivalence provides the bridge between coding theory and cognitive science: the parity bit's role in detecting and correcting errors in a data block is structurally identical to the perceptual system's role in detecting and resolving inconsistencies in a set of observations.

## 3.5 Shannon Entropy and Mutual Information

### 3.5.1 Entropy

The **Shannon entropy** of a discrete random variable $X$ with probability mass function $p$ is:

$$H(X) = -\sum_{x} p(x) \log_2 p(x)$$

measured in bits (when $\log_2$ is used). Entropy measures the average information content (or uncertainty) of $X$. It is maximized when $X$ is uniform ($p(x) = 1/|\mathcal{X}|$ for all $x$) and minimized when $X$ is deterministic.

### 3.5.2 Mutual Information

The **mutual information** between random variables $X$ and $Y$ is:

$$I(X; Y) = H(X) - H(X|Y) = H(Y) - H(Y|X) = \sum_{x,y} p(x,y) \log_2 \frac{p(x,y)}{p(x)p(y)}$$

Mutual information measures the reduction in uncertainty about $X$ from observing $Y$ (and vice versa). It is symmetric: $I(X; Y) = I(Y; X)$, non-negative: $I(X; Y) \geq 0$, and zero if and only if $X$ and $Y$ are independent.

### 3.5.3 Information Content of Rare Events

An event $E$ with probability $p(E)$ carries **self-information**:

$$I(E) = -\log_2 p(E)$$

Rare events carry more information than common events. This principle underpins our analysis of negative space: events in the negative space (missed ticks, deselected alternatives, excluded possibilities) are, by definition, rarer than events in the positive space, and therefore carry more information per event.

For the Cocapn fleet, this manifests as the miss-rate–information-density relationship: in rooms with miss rate $\geq 40\%$, individual tile arrivals carry 5.79 bits, compared to 3.21 bits in rooms with low miss rates. The mathematical explanation is straightforward: if the probability of a tile arrival is $p$, the self-information of each arrival is $-\log_2 p$, which increases as $p$ decreases.

## 3.6 Hurst Exponent and Fractional Brownian Motion

### 3.6.1 Fractional Brownian Motion

**Fractional Brownian motion** (fBm) $B_H(t)$ with Hurst exponent $H \in (0, 1)$ is a continuous-time Gaussian process with:
- $B_H(0) = 0$ (start at origin)
- $\mathbb{E}[B_H(t)] = 0$ (zero mean)
- $\mathbb{E}[B_H(t) B_H(s)] = \frac{1}{2}(|t|^{2H} + |s|^{2H} - |t-s|^{2H})$ (covariance)

The Hurst exponent $H$ controls the correlation structure:
- $H = 0.5$: standard Brownian motion (independent increments)
- $H > 0.5$: **persistent** (positive autocorrelation; trends continue)
- $H < 0.5$: **anti-persistent** (negative autocorrelation; trends reverse)

### 3.6.2 Estimation

The Hurst exponent can be estimated by several methods:
- **R/S analysis** (rescaled range): Fit $\log(R/S) \sim H \log(n)$ over window sizes $n$.
- **Variance of increments:** $\mathrm{Var}[B_H(t + \delta) - B_H(t)] \propto \delta^{2H}$.
- **Periodogram:** The spectral density of fBm follows $S(f) \propto f^{-(2H+1)}$.

### 3.6.3 The "Creative Constant" $H \approx 0.7$

In our empirical analysis of the Cocapn fleet, we find that the temporal patterns in creative rooms (rooms with high diversity of tile types, such as `forge` and `proofs`) exhibit $H \approx 0.7$, indicating persistent (trend-continuing) behavior. This is consistent with the observation that creative work tends to come in sustained bursts (persistence) rather than random fluctuations ($H = 0.5$) or oscillating reversals ($H < 0.5$).

We dub $H \approx 0.7$ the "creative constant" (Chapter 8), while acknowledging the small sample sizes (most rooms have $n < 30$ tiles) that limit the statistical confidence of this estimate.

### 3.6.4 Bandwidth Cost

The Hurst exponent has implications for the **minimum sampling rate** required to faithfully reconstruct a signal. For fBm with Hurst exponent $H$, the bandwidth cost (the ratio of actual bandwidth to Nyquist bandwidth) is:

$$g(H) = \frac{\text{Actual bandwidth}}{\text{Nyquist bandwidth}}$$

We compute $g(0.7) \approx 0.73$ (Chapter 8), meaning that a temporal signal with $H = 0.7$ can be faithfully reconstructed with approximately 73% of the bandwidth that would be required for white noise. This is a direct consequence of persistence: trending signals are more predictable and therefore more compressible.

## 3.7 Sheaves and Cohomology

### 3.7.1 Presheaves and Sheaves

Let $X$ be a topological space with open sets ordered by inclusion. A **presheaf** $F$ of sets on $X$ assigns:
- A set $F(U)$ to each open set $U \subseteq X$
- A restriction map $\rho_{UV}: F(U) \to F(V)$ to each inclusion $V \subseteq U$

satisfying $\rho_{UU} = \mathrm{id}$ and $\rho_{VW} \circ \rho_{UV} = \rho_{UW}$ for $W \subseteq V \subseteq U$.

A **sheaf** is a presheaf satisfying:
1. **Locality:** If $s, t \in F(U)$ and $s|_{U_i} = t|_{U_i}$ for a cover $\{U_i\}$ of $U$, then $s = t$.
2. **Gluing:** If $s_i \in F(U_i)$ and $s_i|_{U_i \cap U_j} = s_j|_{U_i \cap U_j}$ for all $i, j$, then there exists $s \in F(U)$ with $s|_{U_i} = s_i$.

### 3.7.2 Čech Cohomology

Given a sheaf $F$ on $X$ and an open cover $\mathcal{U} = \{U_i\}$, the **Čech cochain complex** is:

$$C^0(\mathcal{U}, F) \xrightarrow{d^0} C^1(\mathcal{U}, F) \xrightarrow{d^1} C^2(\mathcal{U}, F) \to \cdots$$

where:
- $C^0(\mathcal{U}, F) = \prod_i F(U_i)$ (0-cochains: local sections)
- $C^1(\mathcal{U}, F) = \prod_{i<j} F(U_i \cap U_j)$ (1-cochains: pairwise compatibility data)
- $C^2(\mathcal{U}, F) = \prod_{i<j<k} F(U_i \cap U_j \cap U_k)$ (2-cochains: triple compatibility data)

The coboundary $d^0: C^0 \to C^1$ is $(d^0 s)_{ij} = s_j|_{U_i \cap U_j} - s_i|_{U_i \cap U_j}$, and $H^1(\mathcal{U}, F) = \ker d^1 / \mathrm{im}\, d^0$.

**Interpretation:** $H^1 = 0$ means all pairwise-compatible local sections glue to a global section. $H^1 \neq 0$ means there exist pairwise-compatible families that cannot be glued — the obstruction to global consistency.

### 3.7.3 Persistent Cohomology

Combining sheaf cohomology with persistent homology, **persistent cohomology** tracks the birth and death of cohomology classes across a filtration of covers. This provides a multi-scale view of the obstruction structure, identifying which inconsistencies are transient (dying early in the filtration) and which are persistent (surviving across scales).

In our framework, persistent cohomology is used to analyze the constraint structure of the fleet: as the granularity of observation varies (from fine-grained tile-by-tile analysis to coarse-grained weekly summaries), different inconsistencies appear and disappear. The persistent ones — those that survive across all scales — are the structural contradictions that the fleet must resolve to achieve global coherence.

## 3.8 Adjunctions and Galois Connections

### 3.8.1 Adjunctions

An **adjunction** $F \dashv G$ between categories $\mathcal{C}$ and $\mathcal{D}$ is a quadruple $(F, G, \eta, \epsilon)$ where:
- $F: \mathcal{C} \to \mathcal{D}$ is the left adjoint (free construction)
- $G: \mathcal{D} \to \mathcal{C}$ is the right adjoint (forgetful projection)
- $\eta: \mathrm{id}_{\mathcal{C}} \Rightarrow GF$ is the unit (embedding of $X$ into the "freed" $GF(X)$)
- $\epsilon: FG \Rightarrow \mathrm{id}_{\mathcal{D}}$ is the counit (projection from the "freed and then forgotten" $FG(Y)$ back to $Y$)

satisfying the triangle identities:
$$\epsilon F \circ F\eta = \mathrm{id}_F, \quad G\epsilon \circ \eta G = \mathrm{id}_G$$

### 3.8.2 Galois Connections

A **Galois connection** between posets $P$ and $Q$ is a pair of monotone functions $f: P \to Q$, $g: Q \to P$ such that:
$$p \leq g(q) \iff f(p) \leq q$$

for all $p \in P$, $q \in Q$. This is an adjunction in the 2-category of posets, with $f \dashv g$.

**Properties:**
- $f$ and $g$ are interderivable: $f(p) = \min\{q : p \leq g(q)\}$, $g(q) = \max\{p : f(p) \leq q\}$.
- $gf: P \to P$ is a closure operator (idempotent, increasing, monotone).
- $fg: Q \to Q$ is an interior operator (idempotent, decreasing, monotone).

### 3.8.3 The Selection Adjunction

The central adjunction of our framework (developed in Chapter 7) is the **selection adjunction** between a space of possibilities $S$ and a selected subspace $A \subseteq S$:

$$F: A \hookrightarrow S \quad \text{(inclusion)} \qquad R: S \twoheadrightarrow A \quad \text{(projection/snap)}$$

with $F \dashv R$. The unit $\eta: a \mapsto a$ (trivially, since $A \subseteq S$) and the counit $\epsilon: s \mapsto \mathrm{snap}(s)$ (projection of $s$ to the nearest point in $A$).

The **information content** of the selection is carried by the counit $\epsilon$: for each $s \in S$, $\epsilon(s)$ records the nearest selected point, and the residual $s - \epsilon(s)$ records what was excluded by the selection. The triangle identity $\epsilon F \circ F\eta = \mathrm{id}_F$ ensures that already-selected points are fixed by the snap (no information loss for points in $A$).

## 3.9 Comprehensive Notation Table

The following table collects all notation used in this dissertation. Symbols are listed with their meaning and the primary context in which they appear.

| Symbol | Meaning | Context |
|--------|---------|---------|
| $\mathbb{Z}[\omega]$ | Eisenstein integers, $a + b\omega$ with $a,b \in \mathbb{Z}$ | Ch 3–7 |
| $\omega$ | Primitive cube root of unity, $e^{2\pi i/3} = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$ | Ch 3–7 |
| $N(z)$ | Norm of $z$, $z\bar{z} = a^2 - ab + b^2$ for $z = a + b\omega$ | Ch 3–4 |
| $A_2$ | Hexagonal lattice (2D root lattice) | Ch 3–7 |
| $A_n$ | $n$-dimensional root lattice | Ch 2–3 |
| $\Lambda$ | Generic lattice | Ch 2–4 |
| $V(\lambda)$ | Voronoï cell of lattice point $\lambda$ | Ch 3–4 |
| $r_c(\Lambda)$ | Covering radius of lattice $\Lambda$ | Ch 3–4 |
| $r_c(A_2)$ | Covering radius of $A_2$, equal to $1/\sqrt{3}$ | Ch 3–4 |
| $\mathrm{snap}(z)$ | Nearest lattice point to $z$ | Ch 4–5 |
| $\epsilon(z)$ | Snap residual, $z - \mathrm{snap}(z)$ | Ch 4–5 |
| $\rho(\Lambda)$ | Packing radius of lattice $\Lambda$ | Ch 2–3 |
| $\mathrm{GF}(2)$ | Galois field with two elements | Ch 3, 6 |
| $\oplus$ | XOR (addition in GF(2)) | Ch 3, 6 |
| $P(x)$ | Parity of bit string $x$ | Ch 3, 6 |
| $H(X)$ | Shannon entropy of random variable $X$ | Ch 3, 8 |
| $I(X; Y)$ | Mutual information between $X$ and $Y$ | Ch 3, 8 |
| $I(E)$ | Self-information of event $E$ | Ch 3, 8 |
| $H$ | Hurst exponent | Ch 3, 8 |
| $B_H(t)$ | Fractional Brownian motion with Hurst exponent $H$ | Ch 3, 8 |
| $g(H)$ | Bandwidth cost ratio | Ch 8 |
| $H^1(X, F)$ | First Čech cohomology group of sheaf $F$ on $X$ | Ch 3, 6, 8 |
| $F \dashv G$ | Adjunction with left adjoint $F$ and right adjoint $G$ | Ch 3, 7 |
| $\eta$ | Unit of adjunction or monad | Ch 3, 5, 7 |
| $\epsilon$ | Counit of adjunction (not to be confused with snap residual $\epsilon(z)$) | Ch 3, 7 |
| $\mu$ | Multiplication of monad | Ch 3, 5 |
| $(D, \eta, \mu)$ | Deadband monad | Ch 5 |
| $F: A \hookrightarrow S$ | Inclusion functor (left adjoint in selection adjunction) | Ch 7 |
| $R: S \twoheadrightarrow A$ | Projection/snap functor (right adjoint in selection adjunction) | Ch 7 |
| $S$ | Space of possibilities (selection space) | Ch 7, 12 |
| $A$ | Selected subspace (actualities) | Ch 7, 12 |
| $\theta$ | Deadband threshold | Ch 5 |
| $\sigma$ | Deadband smoothing parameter | Ch 5 |
| $\mathcal{H}$ | Fleet harmony measure | Ch 15 |
| $\chi(\Sigma)$ | Euler characteristic of simplicial complex $\Sigma$ | Ch 6 |
| $\mathbb{Z}^2$ | Integer lattice (square grid) | Ch 4 |
| $d(x, y)$ | Hamming distance between codewords $x, y$ | Ch 2, 6 |

**Disambiguation note:** The symbol $H$ appears in four distinct contexts: Hurst exponent ($H$), Shannon entropy ($H(X)$), first cohomology ($H^1$), and fleet harmony ($\mathcal{H}$). The context disambiguates. Similarly, $\epsilon$ denotes both the snap residual $\epsilon(z)$ (Chapters 4–5) and the counit of adjunction (Chapters 3, 7). We use $\epsilon(z)$ with argument for the residual and $\epsilon$ without argument for the counit.

---

*End of Chapters 1–3.*
