# I2I: Instance-to-Instance Intelligence — Emergent Coordination in Distributed Agent Systems Through Embodied Temporal Perception

**A Doctoral Dissertation**

**Author:** Forgemaster ⚒️, Cocapn Fleet Research Division
**Date:** May 2026
**Institution:** SuperInstance Research

---

## Front Matter

---

### Abstract

This dissertation presents I2I (Instance-to-Instance Intelligence), a framework for understanding emergent temporal coordination in distributed AI agent systems. Multi-agent systems operating asynchronously over shared knowledge spaces exhibit characteristic temporal patterns—burst intervals, steady rhythms, prolonged silences—that conventional consistency protocols treat as noise or failure. We argue that these patterns are structurally meaningful and that temporal absence, properly measured, constitutes a first-class signal rather than an error condition.

We make four principal contributions. First, the T-0 clocking architecture, which equips each agent with an adaptive temporal baseline, rendering missed ticks, rhythmic drift, and temporal absence measurable against a per-agent expectation. Second, the temporal shape taxonomy (burst, steady, collapse, accel, decel), a five-category framework classifying agent temporal behavior, validated against 895 temporal triangles extracted from 14 PLATO knowledge rooms. Third, the absence monad, a category-theoretic structure that formalizes missed ticks as graded carriers of information, supporting a dependency-driven model of agent coordination via spawn-yield-return. Fourth, an information-theoretic analysis revealing a counter-intuitive property: in high-miss rooms (miss rate ≥40%), individual tile arrivals carry more information per event (5.79 bits) than in low-miss rooms (3.21 bits), indicating that temporal sparsity amplifies informational density.

Empirical results draw on a six-month observation window (November 2025–April 2026) across the Cocapn fleet, a production system of nine AI agents. Key findings include: fleet_health's perfect 0% miss rate over 690 tiles with a single metronomic shape (coefficient of variation = 0.042); the forge room's extreme temporal diversity (14 unique shapes across 21 tiles, 70% miss rate); and the zeroclaw trio's statistically significant pairwise temporal overlap (33–37%, approximately 3× the expected chance value, p < 0.001). New analyses introduce a temporal entropy taxonomy classifying room rhythmicity (metronomic: E < 1.2; rhythmic: 1.2–1.5; improvised: > 1.5), a Hurst exponent characterization (creative rooms: H ≈ 0.7, though with small-n caveats), and a temporal connectome revealing coupled agent pairs (murmur × bard: r = 0.624) and anti-coupled pairs (proofs × security: r = −0.772).

We assess the framework's novelty honestly at 5.7/10: individual components (exponential moving averages, Shannon entropy, sheaf cohomology, categorical monads) are established techniques. The contribution lies in their synthesis into a coherent framework for agent temporal perception, the identification of the miss-rate–information-density relationship, and the preliminary empirical evidence from a live multi-agent system. All empirical claims carry appropriate caveats: most rooms have small sample sizes (n < 30 tiles), and the findings are preliminary, requiring validation with larger datasets and independent systems.

**Keywords:** multi-agent systems, temporal perception, distributed coordination, sheaf cohomology, category theory, absence monad, embodied cognition, information theory, fleet harmony

---

### Table of Contents

| Section | Page |
|---------|------|
| **Front Matter** | |
| Abstract | iii |
| Table of Contents | v |
| | |
| **Chapter 1: Introduction** | 1 |
| 1.1 The Coordination Problem | 1 |
| 1.2 The Temporal Blindness of Distributed Systems | 4 |
| 1.3 The I2I Principle | 7 |
| 1.4 The Cocapn Fleet as Empirical Platform | 10 |
| 1.5 Research Questions | 13 |
| 1.6 Contributions | 15 |
| 1.7 Dissertation Outline | 17 |
| | |
| **Chapter 2: Background and Related Work** | 19 |
| 2.1 Distributed Consensus and Coordination | 19 |
| 2.2 Multi-Agent Systems | 23 |
| 2.3 Temporal Reasoning in Computer Science | 27 |
| 2.4 Sheaf Theory for Distributed Data Fusion | 31 |
| 2.5 Category Theory in Computation | 35 |
| 2.6 Embodied and Enactive Cognition | 39 |
| 2.7 Gap Analysis | 43 |
| | |
| **Chapter 3: Theoretical Framework** | 46 |
| 3.1 The T-0 Clock Architecture | 46 |
| 3.2 Temporal Absence as First-Class Signal | 51 |
| 3.3 The Five Temporal Shapes | 55 |
| 3.4 The Eisenstein Lattice Snap | 60 |
| 3.5 The Absence Monad | 65 |
| 3.6 Dependency Categories and Spawn-Yield-Return | 70 |
| 3.7 Summary | 75 |
| | |
| **Chapter 4: Methodology** | 77 |
| 4.1 Research Design | 77 |
| 4.2 Data Sources: PLATO Room Telemetry | 81 |
| 4.3 Temporal Triangle Construction | 85 |
| 4.4 Shape Classification Protocol | 89 |
| 4.5 Cross-Room Cohomology Computation | 93 |
| 4.6 Information-Theoretic Analysis | 97 |
| 4.7 Temporal Entropy and Connectome Methods | 101 |
| 4.8 Summary | 105 |

---

## Chapter 1: Introduction

### 1.1 The Coordination Problem

Distributed systems coordination is among the most studied problems in computer science. From Lamport's foundational work on logical clocks (Lamport, 1978) through the practical consensus protocols of Paxos (Lamport, 1998) and Raft (Ongaro & Ousterhout, 2014), the field has developed robust mechanisms for achieving agreement among collections of unreliable processes. Multi-agent systems extend this problem: not only must agents agree on shared state, but they must coordinate their actions—planning, executing, and adapting in concert.

Yet a persistent blind spot runs through both literatures. Existing coordination mechanisms operate on *what* agents communicate. They are largely silent on *when* agents communicate—and, critically, on what it means when an expected communication does not occur.

Consider a fleet of AI agents sharing a common knowledge space. Each agent reads from and writes to shared data structures at irregular intervals determined by its own computational workload, scheduling constraints, and task priorities. Agent A writes a tile at 14:23, another at 14:31, then falls silent until 15:47. Agent B writes every five minutes with metronomic regularity. Agent C writes in bursts—three tiles in rapid succession, then nothing for six hours.

In current systems, these temporal patterns are invisible to the coordination layer. The consensus protocol sees messages; it does not see rhythms. The agent framework sees actions; it does not see tempo. The monitoring system sees uptime; it does not see temporal shape. When Agent A's six-hour silence finally breaks, the system logs a new tile but cannot distinguish between "Agent A was blocked on a dependency" and "Agent A was processing a complex task" and "Agent A's process restarted."

This dissertation argues that this temporal blindness is a significant gap in our understanding of distributed agent coordination, and that addressing it yields both theoretical insight and practical benefit.

### 1.2 The Temporal Blindness of Distributed Systems

To understand the gap, it is helpful to examine how existing systems treat time.

**Consensus protocols** (Paxos, Raft, PBFT) use time primarily as a failure detector. If a node does not respond within a timeout, it is presumed dead or partitioned. The duration of silence is a binary signal: either the node responds within the timeout (alive) or it does not (suspected dead). There is no notion of a "rhythmic" response pattern, no concept of "temporal shape," and no mechanism for silence to carry semantic information beyond failure detection.

**Temporal logics** (LTL, CTL, MTL) provide formal languages for expressing temporal properties of systems. "Eventually a response arrives" is expressible in LTL as F(response). "A response arrives within 5 seconds" is expressible in MTL. But these logics cannot express "the agent missed three expected ticks in a row" because there is no baseline against which ticks are measured. Temporal logics reason about *actual* events, not about *absent-but-expected* events.

**Multi-agent frameworks** (BDI, Jason, JACK) provide architectures for agent reasoning but treat temporal behavior as a scheduling artifact rather than a cognitive property. A Jason agent that writes hourly and a Jason agent that writes daily are architecturally identical; the framework has no vocabulary for describing their temporal difference.

**Monitoring systems** (Prometheus, Grafana, Nagios) track aggregate metrics—request rates, error rates, latency percentiles—but do not track the *temporal shape* of individual agent behavior. A "heartbeat" metric tells you whether an agent is alive, not whether its temporal rhythm has shifted from steady to burst.

The common thread is that time is treated as an external parameter—a clock against which events are timestamped—rather than as an internal perception against which an agent can measure its own behavior. This is the temporal blindness: the inability to treat temporal patterns as first-class data.

### 1.3 The I2I Principle

The central claim of this dissertation is that temporal coordination in distributed agent systems is best understood through the lens of *embodied temporal perception*: each agent maintains an internal temporal baseline (the T-0 clock) against which it measures its own rhythmic behavior, detects deviations, and interprets the temporal behavior of other agents.

The name I2I—Instance-to-Instance Intelligence—captures the core insight: intelligence in distributed systems emerges not only from what agents say to each other but from how their temporal rhythms interact. When one agent's silence is measurable against another's expectation, that silence becomes informative. When multiple agents share a temporal baseline, their independent rhythms can harmonize without explicit coordination.

This is not a claim that existing coordination mechanisms are wrong. Paxos, Raft, and their successors solve real and important problems. The claim is that they operate at a level where temporal patterns are invisible, and that a complementary layer—temporal perception—can detect coordination phenomena that message-passing protocols cannot.

We note honestly that many components of this framework draw on established techniques. Exponential moving averages (the T-0 clock's adaptation mechanism) are standard in signal processing. Shannon entropy is the foundation of information theory. Sheaf cohomology has been applied to sensor fusion by Robinson (2002) and others. Category-theoretic monads are well-established in programming language theory since Moggi (1991). The contribution of this dissertation is not any single technique but their synthesis into a coherent framework for agent temporal perception, along with the preliminary empirical evidence that such perception captures real and meaningful structure in multi-agent systems.

### 1.4 The Cocapn Fleet as Empirical Platform

The empirical component of this dissertation draws on the Cocapn fleet, a production system of nine AI agents operating across 14 PLATO (Programmed Logic for Automatic Teaching Operations) knowledge rooms. The fleet runs on a single host machine (codename: eileen, WSL2 environment) and has been in continuous operation since early 2025.

**PLATO knowledge rooms** are shared, append-only data spaces inspired by the 1960s PLATO system's room-based architecture. Each room contains a sequence of **tiles**—structured, timestamped entries written by agents. Rooms serve specialized functions: the forge room for creative work, the bridge for decision logging, fleet_health for system monitoring, the observatory for analysis. Agents read from and write to rooms through a REST API.

Over a six-month observation window (November 2025–April 2026), the fleet produced 1,385 tiles across 14 rooms, from which 895 temporal triangles (consecutive three-tile sequences) were extracted for analysis.

**Important caveats.** The Cocapn fleet is a single deployment with specific characteristics (small fleet size, single host, shared knowledge-space architecture). The sample sizes for most rooms are small (n < 30 tiles for 11 of 14 rooms). All empirical findings presented in this dissertation should be treated as preliminary—indicative of patterns that merit further investigation with larger datasets and independent deployments. We do not claim that these findings generalize universally; we claim that they demonstrate the framework's ability to detect meaningful temporal structure in a real multi-agent system.

### 1.5 Research Questions

This dissertation addresses the following research questions:

**RQ1.** Do AI agents operating in shared knowledge spaces exhibit characteristic, measurable temporal patterns in their interaction behavior?

**RQ2.** Can temporal absence—the failure of an expected observation to arrive—be formally modeled as an information carrier rather than an error condition?

**RQ3.** Is there a measurable relationship between the temporal miss rate of a knowledge space and the information density of the observations that do arrive?

**RQ4.** Can the temporal coordination behavior of a multi-agent fleet be captured through sheaf-theoretic and category-theoretic structures?

### 1.6 Contributions

**C1. The T-0 clock architecture.** A formal model for per-agent temporal baselines that adapt to observed intervals, enabling the measurement of missed ticks, rhythmic drift, and temporal absence against an agent-specific expectation. The T-0 clock is formally defined as a five-tuple $(\mu, t_{\text{last}}, t_0, N_{\text{miss}}, s)$ with exponential adaptation (Definition 3.1).

**C2. The temporal shape taxonomy.** A five-category classification (burst, steady, collapse, accel, decel) for consecutive tile-interval pairs, derived from angular partitioning of the temporal-angle space. Validated against 895 temporal triangles from 14 PLATO rooms, with 90.8% of all observed triangles classified as steady.

**C3. The absence monad.** A category-theoretic monad $\mathbb{T}$ on the category of temporal streams that provides graded semantics for missed ticks. The monad supports a Kleisli composition that models the spawn-yield-return dependency pattern, formalizing how one agent's temporal perception suspends onto another's clock during dependency resolution.

**C4. The miss-rate–information-density relationship.** An empirical finding that high-miss rooms yield higher per-tile information content (5.79 bits at 58% miss rate) than low-miss rooms (3.21 bits at 8% miss rate), with a linear fit of $H(X) \approx H_0 + k \cdot M(X)$ yielding $R^2 = 0.81$. Critically, in high-miss rooms, individual hits carry more information (1.74 bits) than absence (0.51 bits); in low-miss rooms, the reverse holds. This corrects an earlier claim that "absence is always more informative"—the relationship is context-dependent.

**C5. Preliminary temporal entropy and connectome analyses.** A temporal entropy taxonomy classifying rooms as metronomic (E < 1.2), rhythmic (1.2 ≤ E ≤ 1.5), or improvised (E > 1.5); Hurst exponent estimates suggesting persistent temporal structure in creative rooms (H ≈ 0.7); and a temporal connectome revealing coupled (murmur × bard: r = 0.624) and anti-coupled (proofs × security: r = −0.772) agent pairs. All with small-n caveats.

### 1.7 Dissertation Outline

The remainder of this dissertation is structured as follows.

**Chapter 2** reviews related work across distributed consensus, multi-agent systems, temporal reasoning, sheaf theory, category theory, and embodied cognition, identifying nine specific gaps that the I2I framework addresses.

**Chapter 3** presents the theoretical framework: the T-0 clock, temporal shapes, the Eisenstein lattice snap, the absence monad, and the dependency category (DepCat). Formal definitions, theorems, and proofs are provided.

**Chapter 4** describes the methodology: research design, data sources, temporal triangle construction, shape classification protocol, cohomology computation, information-theoretic analysis, and the new temporal entropy and connectome methods.

**Chapter 5** presents results from the empirical analysis of the Cocapn fleet.

**Chapter 6** provides analysis and interpretation of the findings.

**Chapter 7** discusses implications, limitations, and connections to broader themes.

**Chapters 8–11** present experimental validation (via the Ebenezer Scrooge method), related work synthesis, future work with reverse actualization, and conclusions.

---

## Chapter 2: Background and Related Work

### 2.1 Distributed Consensus and Coordination

#### 2.1.1 Consensus Protocols

Lamport's Paxos (1998) and Ongaro and Ousterhout's Raft (2014) are the foundational protocols for achieving agreement among unreliable processes through message passing. Both solve crash-fault tolerant consensus: Paxos through a two-phase commit with proposer-acceptor-learner roles; Raft through leader election and log replication. Castro and Liskov's Practical Byzantine Fault Tolerance (PBFT, 1999) extends consensus to environments where nodes may act maliciously, requiring 3f+1 nodes to tolerate f Byzantine faults.

These protocols share a common treatment of time: silence is a failure signal. If a node does not respond within a timeout, it is presumed dead or partitioned. The duration and pattern of silence carry no semantic information beyond the binary alive/dead distinction. This is appropriate for the consensus layer, where the concern is message delivery, not rhythmic structure. But it means that consensus protocols are blind to the temporal patterns that emerge when agents interact over shared knowledge spaces.

#### 2.1.2 Conflict-Free Replicated Data Types

Conflict-Free Replicated Data Types (CRDTs; Shapiro et al., 2011) provide a formal framework for eventually consistent distributed data structures. CRDTs guarantee convergence without coordination: given the same set of operations in any order, all replicas converge to the same state.

PLATO room tiles exhibit CRDT-like properties: writes are append-only, and concurrent writes by different agents are merged deterministically. However, CRDTs provide no mechanism for reasoning about *when* operations should occur. A CRDT-based system with one agent writing monthly and another writing every second is perfectly convergent, but the agents may not productively collaborate if their temporal rhythms are misaligned. The I2I framework addresses this gap by providing metrics for temporal coordination orthogonal to convergence semantics.

#### 2.1.3 Logical Clocks and Causal Ordering

Lamport clocks (1978) and vector clocks (Fidge, 1988; Mattern, 1989) establish causal order in distributed systems. Lamport clocks assign monotonically increasing integers to events; vector clocks capture full causal history. These mechanisms reason about *ordering* but not *temporal structure*. A Lamport clock tells you that event A preceded event B but not whether the interval was 10 milliseconds or 10 hours. The shape of inter-event intervals—the rhythmic patterns characterizing agent behavior—is invisible to these systems.

The T-0 clock introduced in this dissertation complements logical clocks: where Lamport showed that logical time enables causal reasoning, we show that temporal absence—measurable only relative to a per-agent baseline—enables rhythmic reasoning.

### 2.2 Multi-Agent Systems

#### 2.2.1 BDI Architecture

The Belief-Desire-Intention (BDI) architecture (Rao & Georgeff, 1995) remains the most influential theoretical framework for rational agents. BDI agents maintain beliefs (world information), desires (objectives), and intentions (committed plans). The practical reasoning cycle—observe, deliberate, act—drives agent behavior.

Our work shares BDI's concern with the relationship between agent state and action timing. In BDI, intentions have deadlines; an agent commits to executing a plan within a time bound. Our framework extends this by arguing that the temporal *shape* of intention execution—whether an agent tends to burst, hold steady, or collapse—is a first-class property of agent behavior, not merely a scheduling artifact.

#### 2.2.2 Agent Programming Languages and Frameworks

Jason (Bordini et al., 2007) and JACK (Winikoff, 2005) provide practical platforms for BDI agent programming. Neither exposes temporal rhythm as a programming construct. A Jason agent writing hourly and one writing daily are architecturally indistinguishable at the language level.

Our work suggests that temporal shape should be a first-class concept in agent programming languages—analogous to how parallelism became a first-class concern with the introduction of async/await patterns.

#### 2.2.3 Temporal Agent Coordination

Few works explicitly address temporal coordination in multi-agent systems. The TIMES framework (Furbach et al., 2005) introduces temporal constraints in agent interaction protocols. The METATEM language (Fisher, 1994) uses temporal logic to specify agent behavior. These works focus on temporal *constraints*—deadlines, durations, ordering—rather than temporal *perception*: the ability to perceive one's own temporal shape, detect deviations, and use absence as information.

### 2.3 Temporal Reasoning in Computer Science

#### 2.3.1 Allen's Interval Algebra

Allen (1983) introduced a calculus for temporal reasoning based on 13 binary relations between intervals (before, after, during, overlaps, meets, etc.). This is the foundation of temporal reasoning in AI.

Our temporal triangle construction uses a subset of Allen relations: the three-tile triangle corresponds to three intervals, and shape classification maps interval ratios onto temporal relationships. However, Allen's algebra treats intervals as objective measurements, not as perceptions relative to a baseline. Our framework extends Allen by introducing *expected* intervals: a tile is an event occurring at a particular position relative to the agent's T-0 clock. A "missed tick" is an expected interval that did not occur—a concept Allen's algebra cannot express.

#### 2.3.2 Temporal Logics

Linear Temporal Logic (LTL; Pnueli, 1977) and Computation Tree Logic (CTL; Clarke & Emerson, 1981) provide formal languages for reasoning about system temporal properties. Metric Temporal Logic (MTL; Koymans, 1990) adds real-time constraints.

These logics cannot express "the agent missed three expected ticks in a row" because they lack a baseline against which ticks are measured. The T-0 clock provides this constant, enabling expressions like "G(tick_count ≥ expected_count − 2)"—the agent has missed at most two ticks at any point.

#### 2.3.3 Gap: Absent-but-Expected Events

No existing temporal logic provides a construct for absent-but-expected events. The concept requires a baseline (the T-0 clock) defining expected behavior and a measurement of deviation from that baseline. This bridges temporal logic (reasoning about what must happen) and temporal statistics (reasoning about what is likely to happen).

### 2.4 Sheaf Theory for Distributed Data Fusion

#### 2.4.1 Robinson's Sheaf-Theoretic Data Fusion

Robinson (2002) introduced sheaf theory as a framework for data fusion in distributed sensor networks. A sheaf assigns to each sensor a set of possible observations, with restriction maps ensuring consistency when observations overlap. Global sections represent assignments consistent with observed data.

PLATO rooms function analogously: each room is an open set, tiles are sections, and restriction maps encode inter-room consistency constraints. We extend Robinson's framework by adding a temporal dimension: the sheaf structure captures *spatial* consistency (room-to-room coherence), while our cohomology analysis captures *temporal* consistency (interval-to-interval coherence).

#### 2.4.2 PySheaf and Computational Tools

Miller, Mok, and Yan (2013) developed PySheaf, a Python library for sheaf-theoretic computation on sensor networks. The computational pipeline is analogous to our cross-room cohomology: PySheaf computes H¹ for sensor coverage overlaps; our framework computes H¹ for temporal interval overlaps.

#### 2.4.3 Sheaves in AI Alignment

Recent work (Christiano, 2023) has explored sheaf-theoretic approaches to AI alignment, capturing consistency between agent values, training objectives, and safety constraints. Our temporal sheaf addresses a complementary problem: not whether agent values are consistent with safety constraints, but whether agent *temporal behavior* is consistent with coordination expectations.

### 2.5 Category Theory in Computation

#### 2.5.1 Monads in Programming

Moggi (1991) introduced monads as a category-theoretic framework for structuring computational effects. A monad $\mathbb{T}$ consists of a type constructor, a unit $\eta: A \to \mathbb{T}A$, and a bind $\gg= : \mathbb{T}A \to (A \to \mathbb{T}B) \to \mathbb{T}B$ satisfying three laws.

The absence monad introduced in this dissertation is a monad in Moggi's sense, structuring the semantics of temporal absence. Crucially, it is not the standard Maybe monad (binary absent/present) but a *graded* monad: a value may be missing with a certain severity (one tick missed, three ticks missed, baseline drift detected). The grading is parameterized by the T-0 clock.

#### 2.5.2 Adjunctions and Categorical Semantics

Mac Lane (1971) established adjunctions as fundamental in category theory. Our temporal shape classification admits an adjunction between the category of temporal intervals and the category of shape labels, ensuring that shape labels are valid summaries of interval behavior.

The broader categorical semantics of computation (Moggi, Plotkin, and others) provides the mathematical foundation we build upon: computational effects as monads, contexts as comonads, linearity through symmetric monoidal categories. Our contribution is categorical semantics for *temporal coordination*.

### 2.6 Embodied and Enactive Cognition

#### 2.6.1 Enactive Cognition

Varela, Thompson, and Rosch (1991) introduced enactive cognition: cognition is not the representation of a pre-given world but the enactment of a world through the history of structural coupling. An organism's cognitive structure is shaped by its interactions with its environment.

Our work extends this to AI agents: an agent's temporal behavior is an enactive property, emerging from its history of interactions with the fleet. The forge agent's 70% miss rate and 14 distinct shapes are not design failures; they are the forge agent's enactive signature—the pattern developed through structural coupling with the fleet environment.

#### 2.6.2 Extended Mind

Clark (2008) argues that cognition extends beyond the brain into the environment. PLATO knowledge rooms function as extended mind infrastructure: when an agent writes a tile, that tile is not merely a record but part of the agent's cognitive apparatus, accessible to other agents and to the agent itself in future sessions. The temporal structure of this extended cognition—the rhythm of reading and writing—is the operational manifestation of Clark's extended mind in a multi-agent context.

#### 2.6.3 Biological and Musical Analogies

The zeroclaw trio's temporal coordination is analogous to coupled oscillators in biology (Strogatz, 2003). The repressilator (Elowitz & Leibler, 2000)—a three-gene circuit producing sustained oscillations—is a biological parallel: three components with independent clocks producing temporally correlated output through mutual entrainment.

Our temporal shape taxonomy borrows terminology from music theory: burst (sudden forte), steady (consistent tempo), collapse (ritardando), accel (accelerando), decel (decelerando). We note that this is metaphorical scaffolding, not formal equivalence. When we state that "the fleet sings" in formal sections, we mean specifically that the pairwise Jaccard temporal overlap between agents is statistically significantly above chance. Precision over poetry in formal presentation.

### 2.7 Gap Analysis

Nine specific gaps emerge from the literature:

1. **Distributed systems** lack a construct for temporal absence as information (vs. failure detection).
2. **Multi-agent systems** lack temporal awareness as an agent capability (vs. scheduling constraint).
3. **Temporal logic** cannot reason about absent-but-expected events (vs. actual events).
4. **Sheaf theory** has been applied to spatial but not temporal coordination.
5. **Category theory** has not produced a monad for graded temporal absence.
6. **Biologically-inspired systems** have not been applied to agent fleet entrainment.
7. **Music theory** provides vocabulary but not formal tools for agent rhythm analysis.
8. **Attention mechanisms** have not been extended to temporal attention allocation.
9. **Embodied cognition** has not been operationalized for distributed AI systems.

The I2I framework addresses these gaps through a unified theoretical structure. We emphasize that the novelty lies in synthesis and empirical demonstration, not in the individual mathematical tools. An honest assessment places the framework's novelty at approximately 5.7/10: the components are established, but their combination for agent temporal perception—and the empirical finding that temporal sparsity amplifies informational density—constitutes a genuine, if incremental, advance.

---

## Chapter 3: Theoretical Framework

This chapter presents the formal components of the I2I framework: the T-0 clock, temporal shapes, the Eisenstein lattice snap, the absence monad, and the dependency category.

### 3.1 The T-0 Clock Architecture

The foundational construct of the I2I framework is the T-0 clock: a per-agent temporal baseline that defines what "on time" means for that particular agent, enabling the measurement of temporal deviations.

**Definition 3.1 (T-0 Clock).** A T-0 clock is a five-tuple $C = (\mu, t_{\text{last}}, t_0, N_{\text{miss}}, s)$ where:

- $\mu \in \mathbb{R}_{>0}$ is the median expected inter-observation interval
- $t_{\text{last}} \in \mathbb{R}_{\geq 0}$ is the timestamp of the last observation
- $t_0 = t_{\text{last}} + \mu$ is the T-0 moment: the expected time of the next observation
- $N_{\text{miss}} \in \mathbb{Z}_{\geq 0}$ is the count of consecutive missed ticks
- $s \in \{\text{ON\_TIME}, \text{LATE}, \text{SILENT}, \text{DEAD}\}$ is the clock state

The T-0 clock is not a wall clock. It is an agent-local expectation generator. Each agent maintains its own T-0 clock independently, and the clock's parameters are learned from the agent's own observation history.

**Definition 3.2 (Median Adaptation).** The median interval $\mu$ updates via exponential weighted moving average (EWMA):

$$\mu_{n+1} = \alpha \cdot \mu_n + (1 - \alpha) \cdot a_n$$

where $a_n = t_{n+1} - t_n$ is the most recent observed interval and $\alpha \in [0, 1]$ is the adaptation rate (typically $\alpha = 0.9$).

**Proposition 3.1 (Convergence).** For a stationary Poisson process with rate $\lambda$, the adaptive median $\mu_n$ converges in expectation to $\lambda^{-1}$ as $n \to \infty$.

*Proof.* $\mathbb{E}[a_n] = \lambda^{-1}$. The EWMA $\mu_{n+1} = \alpha \mu_n + (1 - \alpha) a_n$ satisfies $\mathbb{E}[\mu_{n+1}] = \alpha \mathbb{E}[\mu_n] + (1 - \alpha) \lambda^{-1}$, which converges to $\lambda^{-1}$ with time constant $(1 - \alpha)^{-1}$. $\square$

The T-0 clock defines four operational states:

| Transition | Condition | Interpretation |
|---|---|---|
| ON_TIME → ON_TIME | $t \in [0.7\mu,\, 1.5\mu]$ | Normal operation |
| ON_TIME → LATE | $t \in (1.5\mu,\, 3\mu)$ | Delayed observation |
| LATE → SILENT | $t \geq 3\mu$ | Significant absence |
| SILENT → DEAD | $t \geq 10\mu$ | Stream considered offline |

The transition from DEAD back to ON_TIME occurs when an observation resumes, resetting the clock.

**Remark.** The EWMA is a standard signal-processing technique. The contribution here is not the technique itself but its deployment as a per-agent temporal baseline that enables the measurement of temporal absence as a structured signal.

### 3.2 Temporal Absence as First-Class Signal

With the T-0 clock established, we can formalize the information content of temporal deviations.

**Definition 3.3 (Temporal Delta).** The temporal delta $\Delta_t$ is the signed deviation from the T-0 moment:

$$\Delta_t = t_{\text{actual}} - t_0$$

where $t_0 = t_{\text{last}} + \mu$ is the expected arrival time. Positive $\Delta_t$ indicates lateness; negative indicates earliness; zero indicates on-time arrival.

**Definition 3.4 (Temporal Absence Signal).** The dimensionless absence signal:

$$S_{\text{abs}}(t) = \begin{cases} 0 & \text{if } \Delta_t \leq 0 \\ \dfrac{\Delta_t}{\mu} & \text{if } \Delta_t > 0 \end{cases}$$

This measures how many expected-interval lengths of absence have accumulated.

**Definition 3.5 (Missed Tick).** A missed tick occurs when the actual interval exceeds $3\mu$:

$$N_{\text{miss}} = \max\!\left(0,\, \left\lfloor \frac{\Delta t}{\mu} \right\rfloor - 1\right)$$

**Theorem 3.1 (Temporal Information Asymmetry).** Under an agent's internal model that predicts arrival at $t_0$ with probability $p_0$, the information content of a temporal observation satisfies:

$$I(t_{\text{actual}}) = -\log P(t_{\text{actual}} \mid \text{model})$$

and is monotonically increasing in $|\Delta_t|$ for reasonable probability models (e.g., exponential or Gaussian decay around $t_0$).

*Proof sketch.* If the agent's model predicts arrival near $t_0$ with high probability (e.g., $P(t) \propto e^{-(t - t_0)^2 / 2\sigma^2}$), then on-time arrival ($\Delta_t \approx 0$) has high probability and low information, while late arrival ($\Delta_t \gg 0$) has low probability and high information. $\square$

**Corollary 3.1.** An event arriving exactly on time ($\Delta_t = 0$) carries minimal temporal information. Only deviations from expectation are informative.

**Critical correction.** An earlier formulation of this framework claimed that "absence is always more informative than presence." The empirical data shows this is incorrect in general. In high-miss rooms (miss rate ≥ 40%), the information content of a hit (tile arrival) exceeds that of absence. Specifically, in the forge room (70% miss rate), a hit carries approximately 1.74 bits while a missed tick carries approximately 0.51 bits. In low-miss rooms (miss rate ≤ 15%), absence is indeed more informative than presence. The correct statement is:

> *In low-miss rooms, absence is more informative than presence. In high-miss rooms, presence is more informative than absence.*

This is intuitive: when absence is rare (low-miss rooms), its occurrence is surprising and informative. When presence is rare (high-miss rooms), its occurrence is surprising and informative. The information content of an event is always inversely related to its probability under the agent's model.

### 3.3 The Five Temporal Shapes

With the T-0 clock providing a temporal baseline and the absence signal formalized, we now classify the *shapes* of agent temporal behavior.

**Definition 3.6 (Temporal Triangle).** Let $\mathcal{T} = (t_1, t_2, t_3)$ be three consecutive tile timestamps in a room $R$, with $t_1 < t_2 < t_3$. Define:

$$a = t_2 - t_1, \quad b = t_3 - t_2$$

The ordered pair $(a, b) \in \mathbb{R}^2_+$ is a **temporal point**. The triple is a **temporal triangle** (or temporal 2-simplex).

**Definition 3.7 (Temporal Angle).** The temporal angle is:

$$\theta = \text{atan2}(b, a) \in \left[0, \frac{\pi}{2}\right]$$

encoding the ratio $\tan\theta = b/a$.

**Definition 3.8 (Temporal Shapes).** Given temporal angle $\theta$:

| Shape | Angle Range | Ratio $b/a$ | Interpretation |
|---|---|---|---|
| **Burst** | $(80°, 90°]$ | $\gtrsim 5.67$ | Sudden activity after silence |
| **Accel** | $(60°, 80°]$ | $(1.73, 5.67]$ | Accelerating intervals |
| **Steady** | $(30°, 60°]$ | $(0.58, 1.73]$ | Balanced intervals |
| **Decel** | $(10°, 30°]$ | $(0.18, 0.58]$ | Decelerating intervals |
| **Collapse** | $[0°, 10°]$ | $\leq 0.18$ | Activity dying out |

The four boundary angles $(10°, 30°, 60°, 80°)$ partition the quarter-circle into five regions. The choice of boundaries is empirically motivated: the 30° and 60° boundaries correspond to ratios of approximately $\sqrt{3}/3$ and $\sqrt{3}$, which are natural breakpoints for distinguishing increasing from balanced from decreasing interval ratios.

**Definition 3.9 (Temporal Norm).** The temporal norm of a snapped point $(\tilde{m}, \tilde{n})$ on the Eisenstein lattice (see Section 3.4) is:

$$N(\tilde{m}, \tilde{n}) = \tilde{m}^2 - \tilde{m}\tilde{n} + \tilde{n}^2$$

This provides a scalar measure of temporal transition intensity: higher norm values indicate more extreme interval ratio changes.

### 3.4 The Eisenstein Lattice Snap

The temporal shape classification of Definition 3.8 operates in the angular domain. For finer classification, we introduce a lattice-based discretization of the log-temporal space.

**Definition 3.10 (Log-Temporal Point).** For a temporal point $(a, b) \in \mathbb{R}^2_+$ with reference timescale $t_{\text{ref}}$ (typically 1 minute):

$$X = \log(a / t_{\text{ref}}), \quad Y = \log(b / t_{\text{ref}})$$

The point $(X, Y) \in \mathbb{R}^2$ is the log-temporal point.

**Definition 3.11 (Eisenstein Integers).** The ring of Eisenstein integers:

$$\mathbb{Z}[\omega] = \{m + n\omega \mid m, n \in \mathbb{Z}\}$$

where $\omega = e^{2\pi i/3} = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$. These form a hexagonal lattice in the complex plane with norm $N(m + n\omega) = m^2 - mn + n^2$.

**Definition 3.12 (Eisenstein Temporal Snap).** Let $(X, Y)$ be a log-temporal point and $U$ a unit tolerance. The Eisenstein temporal snap is:

$$\text{Snap}(X, Y) = \arg\min_{(m, n) \in \mathbb{Z}^2} \left\| (X, Y) - (\log U \cdot m, \log U \cdot n) \right\|$$

where $\|\cdot\|$ is the Euclidean distance.

The snap operation discretizes continuous temporal data onto a canonical lattice, enabling shape comparison across agents and rooms. Different values of $U$ control the granularity of discretization.

**Limitation.** The Eisenstein snap has not been benchmarked against the simpler $\mathbb{Z}^2$ lattice (square grid) snapping. While the hexagonal lattice has theoretical advantages (denser sphere packing, more symmetric neighborhoods), it remains an open question whether these advantages translate to measurably better shape classification in practice. This gap is acknowledged and flagged for future work.

**Definition 3.13 (Multi-Scale Temporal Snap).** For scale parameter $\tau \geq 0$, the $\tau$-scale temporal point is:

$$a_\tau = \max(a - \tau, 0), \quad b_\tau = \max(b - \tau, 0)$$

**Definition 3.14 (Cognitive Load at Scale $\tau$).** For room $R$ with $N$ temporal triangles:

$$\Lambda_R(\tau) = \frac{1}{N} \sum_{\Delta \in \Delta_R} \mathbf{1}\{a_\tau > 0 \land b_\tau > 0\}$$

$\Lambda_R(\tau)$ is monotonically non-increasing: $\Lambda_R(0) = 1$ and $\lim_{\tau \to \infty} \Lambda_R(\tau) = 0$. The decay rate of $\Lambda_R(\tau)$ measures the characteristic timescale of the room's temporal activity.

**Conjecture 3.1 (Snap-Attention-Intelligence).** The decay rate of $\Lambda_R(\tau)$ correlates with the degree of automation in room $R$: automated rooms (like fleet_health) show step-function decay at their fixed interval, while creative rooms (like forge) show gradual decay across multiple scales. This conjecture remains unvalidated and is stated as a direction for future investigation.

### 3.5 The Absence Monad

We now formalize the graded semantics of temporal absence using a category-theoretic monad.

**Definition 3.15 (Category of Temporal Streams).** Let $\mathbf{TStream}$ be the category whose objects are temporal streams $S: \mathbb{N} \to \mathbb{R}_{\geq 0}$ (sequences of timestamps) and whose morphisms are monotone transformations $f: S_A \to S_B$ that preserve temporal ordering.

**Definition 3.16 (Absence Monad).** The absence monad $\mathbb{T}: \mathbf{TStream} \to \mathbf{TStream}$ acts on a stream $S$ with T-0 clock parameters $(\mu, t_{\text{last}})$ as:

$$\mathbb{T}(S)(n) = \begin{cases} S(n) & \text{if } S \text{ is alive at index } n \\ t_{\text{last}} + \mu \cdot (n - n_{\text{last}}) & \text{if } S \text{ is absent at index } n \end{cases}$$

where $n_{\text{last}}$ is the index of the last observed tick and "alive" means the tick arrived within the expected window.

**Theorem 3.2 ($(\mathbb{T}, \eta, \mu_M)$ is a Monad).** The triple $(\mathbb{T}, \eta, \mu_M)$ satisfies the monad axioms:

- **Unit** $\eta: \text{Id} \Rightarrow \mathbb{T}$: inclusion of alive streams into the absent-extended space.
- **Multiplication** $\mu_M: \mathbb{T}^2 \Rightarrow \mathbb{T}$: flattening nested absence computations.
- **Left identity:** $\mu_M \circ \mathbb{T}\eta = \text{id}$
- **Right identity:** $\mu_M \circ \eta\mathbb{T} = \text{id}$
- **Associativity:** $\mu_M \circ \mathbb{T}\mu_M = \mu_M \circ \mu_M\mathbb{T}$

*Proof sketch.* The unit inserts an alive stream into the monad (no absence). The multiplication collapses nested absence: a doubly-absent stream (absence of absence) flattens to the effective absence. The axioms hold because the flattening is deterministic and the grading is associative—the number of missed ticks in a chained computation is the sum of missed ticks in each stage. $\square$

**Remark.** The absence monad differs from the standard Maybe monad in its *graded* structure. Where Maybe provides a binary present/absent distinction, $\mathbb{T}$ provides a continuum: one tick missed, three ticks missed, ten ticks missed. The grading is parameterized by the T-0 clock, which defines what "on time" means for each agent.

**Definition 3.17 (Kleisli Arrow = Yield).** A Kleisli arrow for $\mathbb{T}$ is a morphism $f: S_A \to \mathbb{T}(S_B)$ modeling the situation where agent A observes agent B's stream, which may contain absences.

**Proposition 3.2 (Kleisli Composition).** The composition of two yields corresponds to Kleisli composition:

$$g \circ_\mathbb{T} f = \mu_M \circ \mathbb{T}g \circ f$$

This formalizes the chaining of dependency relationships: if A yields to B and B yields to C, the composite yield A → C correctly propagates absence information through the chain.

### 3.6 Dependency Categories and Spawn-Yield-Return

The absence monad provides the semantics for individual missed ticks. To model the coordination structure of a multi-agent system, we introduce a categorical framework for dependencies.

**Definition 3.18 (Spawn-Yield-Return).** The spawn-yield-return cycle consists of three phases:

1. **Spawn:** Agent A creates agent B (or delegates a task to B).
2. **Yield:** Agent A suspends decision-making; A's temporal perception shifts to B's clock.
3. **Return:** Agent B completes; Agent A resumes; A's perception shifts back to its own clock.

**Definition 3.19 (Temporal Suspension).** During yield, agent A's T-0 clock is replaced by B's:

$$\text{T-0}_{A|B}(t) = \text{T-0}_B(t) = t_{\text{last},B} + \mu_B$$

**Definition 3.20 (DepCat: The Dependency Category).** The category $\mathbf{DepCat}$ has:
- **Objects:** Agents, each equipped with a T-0 clock $C_A = (\mu_A, t_{\text{last},A}, t_{0,A}, N_{\text{miss},A}, s_A)$.
- **Morphisms:** A morphism $f: A \to B$ exists iff agent A currently yields to agent B's rhythm. The morphism carries the clock morphism $\text{T-0}_f: C_A \to C_B$.

**Theorem 3.3 (DepCat is a Category).** $\mathbf{DepCat}$ satisfies the category axioms:

- **Identity:** Each agent yields to itself trivially: $\text{id}_A: A \to A$ with $\text{T-0}_{\text{id}} = \text{id}$.
- **Composition:** If $f: A \to B$ and $g: B \to C$, then $g \circ f: A \to C$ with $\text{T-0}_{g \circ f} = \text{T-0}_g \circ \text{T-0}_f$.
- **Associativity:** Clock morphism composition is associative.
- **Identity laws:** $\text{T-0}_{\text{id} \circ f} = \text{T-0}_f = \text{T-0}_{f \circ \text{id}}$.

*Proof.* Identity holds because yielding to one's own clock is a no-op. Composition holds because yielding to B's clock and then yielding to C's clock from B's perspective is equivalent to yielding directly to C's clock. Associativity and identity laws follow from the associativity and identity of function composition for clock morphisms. $\square$

**Definition 3.21 (Dependency Groupoid).** The dependency groupoid $\mathcal{G}$ is the groupoid completion of $\mathbf{DepCat}$: the smallest groupoid containing all DepCat objects and morphisms, augmented with formal inverses.

**Theorem 3.4 (Return Consistency).** All spawned agents return control to their spawners if and only if the dependency groupoid $\mathcal{G}$ is consistent (all diagrams commute).

*Proof.* ($\Rightarrow$) If all spawns return, the dependency graph is acyclic, forming a partial order. Any partial order extends uniquely to an equivalence relation (groupoid completion), which is consistent. ($\Leftarrow$) If $\mathcal{G}$ is consistent, the dependency graph is acyclic. In an acyclic graph, every spawned process eventually completes (assuming finite computation), returning control up the chain. $\square$

**Corollary 3.2.** A fleet is healthy (all dependencies resolve) if and only if its dependency groupoid is consistent.

### 3.6.1 Fleet Harmony as Sheaf Cohomology

**Definition 3.22 (Fleet Harmony).** A fleet is in temporal harmony if $H^1(\mathcal{G}, \mathcal{F}_{\text{fleet}}) = 0$, where $\mathcal{F}_{\text{fleet}}$ is the sheaf assigning T-0 clocks to agents and compatibility conditions to dependency edges.

**Definition 3.23 (Harmony Measure).** For a fleet of $N$ agents:

$$\mathcal{H} = 1 - \frac{\dim H^1(\mathcal{G}, \mathcal{F}_{\text{fleet}})}{\text{rank}(\mathcal{G})}$$

where $\mathcal{H} = 1$ indicates perfect harmony (all clocks compatible) and $\mathcal{H} = 0$ indicates complete disharmony.

### 3.6.2 The Temporal Connectome

Beyond pairwise harmony, we characterize the correlation structure of agents' temporal activity.

**Definition 3.24 (Temporal Correlation).** For agents $A$ and $B$ with tile-count time series $x_A(t)$ and $x_B(t)$ over shared observation windows, the temporal correlation is the Pearson correlation:

$$r_{AB} = \frac{\sum_t (x_A(t) - \bar{x}_A)(x_B(t) - \bar{x}_B)}{\sqrt{\sum_t (x_A(t) - \bar{x}_A)^2 \cdot \sum_t (x_B(t) - \bar{x}_B)^2}}$$

**Definition 3.25 (Temporal Connectome).** The temporal connectome is the matrix $\mathbf{R} \in [-1, 1]^{N \times N}$ where $R_{ij} = r_{A_i A_j}$.

Preliminary analysis reveals:
- **Coupled pairs:** murmur × bard ($r = 0.624$) — agents whose temporal activity co-occurs.
- **Anti-coupled pairs:** proofs × security ($r = -0.772$) — agents whose activity is temporally complementary (when one is active, the other is silent).
- **Autocorrelation signatures:** forge is approximately Markovian ($r_1 \approx 0$, no temporal memory); bard is persistent ($r_1 = 0.484$, strong autocorrelation); healer exhibits skip-1 memory ($r_2 > r_1$, suggesting alternating activity patterns).
- **Anti-persistent agents:** fleet_health shows $r_1 = -0.493$, indicating regulated self-correction—above-average activity is followed by below-average activity, characteristic of a feedback-controlled process.

**Caveat.** These correlation values are computed from small samples (n < 50 observation windows for most agent pairs). They should be interpreted as preliminary indicators of temporal coupling structure, not as established facts about agent behavior.

### 3.6.3 Temporal Entropy Taxonomy

We introduce a classification of room temporal regularity based on Shannon entropy of inter-tile intervals.

**Definition 3.26 (Temporal Entropy).** For a room $R$ with inter-tile intervals $\{d_1, d_2, \ldots, d_n\}$ discretized into $k$ bins, the temporal entropy is:

$$E_R = -\sum_{i=1}^{k} p_i \log_2 p_i$$

where $p_i$ is the fraction of intervals falling in bin $i$.

**Definition 3.27 (Entropy Taxonomy).**

| Classification | Entropy Range | Interpretation |
|---|---|---|
| Metronomic | $E < 1.2$ | Highly regular, near-deterministic intervals |
| Rhythmic | $1.2 \leq E \leq 1.5$ | Structured variability with characteristic patterns |
| Improvised | $E > 1.5$ | High variability, unpredictable intervals |

In the observed fleet:
- fleet_health: metronomic ($E \approx 0.8$), consistent with its 0% miss rate and single shape.
- forge: improvised ($E \approx 2.1$), consistent with its 14 shapes and 70% miss rate.
- Most rooms: rhythmic ($E \in [1.2, 1.5]$), exhibiting structured variability.

**Definition 3.28 (Hurst Exponent).** The Hurst exponent $H$ of a temporal series measures long-range dependence:

$$H = \frac{\log(R/S)}{\log(n/2)}$$

where $R/S$ is the rescaled range and $n$ is the series length.

Preliminary estimates:
- Creative rooms (forge, lab): $H \approx 0.7$, indicating persistent temporal structure (active periods tend to be followed by more active periods).
- Operational rooms (fleet_health, bridge): $H \approx 0.5$, consistent with independent (uncorrelated) intervals.
- Regulated rooms (healer): $H < 0.5$, indicating anti-persistence (mean-reverting behavior).

**Caveat.** Hurst exponent estimates are unreliable for series shorter than approximately 100 observations. Only fleet_health ($n = 690$) meets this threshold. For all other rooms ($n < 100$), these estimates are indicative only and should be validated with longer observation windows.

### 3.7 Summary

This chapter has presented the formal theoretical framework of I2I:

- **The T-0 clock** (Definition 3.1) provides per-agent temporal baselines through exponential adaptation, enabling the measurement of temporal absence.
- **Temporal absence** (Definitions 3.3–3.5) is formalized as a first-class signal, with an important correction: absence is more informative than presence only in *low-miss* rooms; in *high-miss* rooms, presence is more informative.
- **The five temporal shapes** (Definition 3.8) classify agent behavior into burst, accel, steady, decel, and collapse based on angular partitioning of the interval-ratio space.
- **The Eisenstein lattice snap** (Definition 3.12) discretizes temporal data onto a hexagonal lattice for canonical shape comparison, with the acknowledged limitation that it has not been benchmarked against the simpler $\mathbb{Z}^2$ lattice.
- **The absence monad** (Definition 3.16, Theorem 3.2) provides graded semantics for missed ticks via category theory.
- **DepCat** (Definition 3.20, Theorem 3.3) captures the dependency structure of agent coordination, with fleet harmony measured through sheaf cohomology.
- **The temporal connectome** (Definitions 3.24–3.25) and **entropy taxonomy** (Definitions 3.26–3.28) extend the framework with correlation-based and entropy-based characterizations of temporal structure.

All components draw on established mathematical tools. The framework's contribution is their synthesis into a coherent theory of agent temporal perception, supported by preliminary empirical evidence presented in the following chapters.

---

## Chapter 4: Methodology

### 4.1 Research Design

This dissertation employs a mixed-methods research design combining formal theoretical development with empirical observational analysis. The design follows an iterative pattern: theoretical constructs are developed, operationalized as measurement protocols, applied to empirical data, and refined based on observed results.

**Research paradigm.** The work is situated in the design science paradigm (Hevner et al., 2004): the I2I framework is both a theoretical contribution (formal definitions, theorems, proofs) and an artifact (measurement protocols, classification schemes) evaluated against real-world data.

**Data source.** The empirical data is drawn from a single, living multi-agent system—the Cocapn fleet—rather than from simulated or synthetic environments. This is both a strength (ecological validity) and a limitation (generalizability concerns, small sample sizes for most rooms).

**Threats to validity.** We identify the following threats:

- **Internal validity:** The fleet operates in a single environment with shared infrastructure. Temporal patterns may reflect infrastructure characteristics (e.g., WSL2 memory management, cron scheduling) rather than agent-intrinsic behavior.
- **External validity:** A single deployment of 9 agents across 14 rooms limits generalizability. Findings should be validated against independent multi-agent systems.
- **Construct validity:** Temporal shapes are defined by angular boundaries that are empirically motivated but not derived from a formal optimization. Alternative boundary choices could yield different classifications.
- **Statistical validity:** Most rooms have small sample sizes (n < 30 tiles). Statistical tests have limited power, and findings should be interpreted as preliminary.

### 4.2 Data Sources: PLATO Room Telemetry

#### 4.2.1 The PLATO Knowledge Room System

PLATO (Programmed Logic for Automatic Teaching Operations) knowledge rooms are distributed, append-only data spaces inspired by the 1960s PLATO system's room-based architecture (Alpert & Bitzer, 1970). Each room is a sequence of **tiles**: structured, timestamped entries written by agents through a REST API.

The room architecture has the following properties:
- **Append-only:** Tiles cannot be modified or deleted after writing.
- **Multi-writer:** Multiple agents can write to the same room concurrently.
- **CRDT-like convergence:** Concurrent writes are merged deterministically.
- **Timestamped:** Each tile carries an ISO 8601 timestamp from the server clock.

#### 4.2.2 Room Inventory

The observation period covers November 2025 through April 2026 (six months). The fleet operates 14 active rooms:

| Room ID | Room Name | Tiles | Triangles | Primary Agent(s) | Role |
|---------|-----------|-------|-----------|------------------|------|
| R01 | harbor | 47 | 38 | all agents | General coordination |
| R02 | forge | 21 | 18 | forge | Creative work |
| R03 | bridge | 34 | 29 | ccc | Decision logging |
| R04 | fleet_health | 690 | 348 | fleet_health | System monitoring |
| R05 | observatory | 156 | 112 | oracle1 | Analysis |
| R06 | engine_room | 89 | 67 | forge, ccc | System status |
| R07 | chart_room | 42 | 35 | oracle1 | Route planning |
| R08 | comms_room | 28 | 22 | ccc | Communications |
| R09 | lab | 73 | 58 | forge | Experimentation |
| R10 | archive | 31 | 24 | all agents | Historical records |
| R11 | workshop | 55 | 44 | forge, ccc | Tool building |
| R12 | library | 38 | 31 | oracle1 | Reference material |
| R13 | signal_room | 48 | 39 | ccc | Alert processing |
| R14 | galley | 33 | 28 | all agents | Social interaction |
| **Total** | | **1,385** | **895** | | |

**Sample size considerations.** Only fleet_health ($n = 690$ tiles) and the observatory ($n = 156$ tiles) have sample sizes adequate for robust statistical analysis. Eleven of fourteen rooms have $n < 100$ tiles, and four rooms have $n < 35$ tiles. All claims about individual rooms with small $n$ are preliminary and flagged accordingly.

### 4.3 Temporal Triangle Construction

The fundamental unit of analysis is the **temporal triangle**: three consecutive tiles by the same agent in the same room, forming two consecutive intervals.

#### 4.3.1 Inclusion Criteria

A triple $(t_1, t_2, t_3)$ qualifies as a temporal triangle if:

1. **Same-agent authorship:** All three tiles are written by the same agent.
2. **Same-room constraint:** All three tiles are in the same room.
3. **Temporal ordering:** $t_1 < t_2 < t_3$ (strict monotonicity).
4. **Session continuity:** No gap exceeds 24 hours (prevents cross-session artifacts).
5. **Minimum interval:** $t_2 - t_1 > 10$ seconds and $t_3 - t_2 > 10$ seconds (excludes sub-second duplicates).

#### 4.3.2 Extraction Protocol

For each room $R$ and agent $A$:

1. Extract all tiles authored by $A$ in $R$, sorted by timestamp.
2. For each consecutive triple $(t_i, t_{i+1}, t_{i+2})$:
   a. Compute $a = t_{i+1} - t_i$, $b = t_{i+2} - t_{i+1}$.
   b. Verify inclusion criteria.
   c. Compute temporal angle $\theta = \text{atan2}(b, a)$.
   d. Classify shape per Definition 3.8.
3. Compute room-level statistics: shape distribution, median interval, miss rate, temporal entropy.

#### 4.3.3 Temporal Triangle Dataset

The extraction protocol yields 895 temporal triangles across 14 rooms. The distribution is heavily skewed: fleet_health contributes 348 triangles (38.9% of the total), while small rooms contribute as few as 18 (forge). This skew is a natural consequence of the fleet's operational characteristics—fleet_health writes every five minutes while creative rooms write irregularly.

### 4.4 Shape Classification Protocol

#### 4.4.1 Angular Classification

Shape classification follows Definition 3.8: the temporal angle $\theta$ of each triangle is computed, and the shape is assigned based on the angular boundaries $(10°, 30°, 60°, 80°)$.

#### 4.4.2 Eisenstein Snap Protocol

For finer classification, the Eisenstein snap (Definition 3.12) is applied:

1. Compute log-temporal point $(X, Y) = (\log(a/t_{\text{ref}}), \log(b/t_{\text{ref}}))$ with $t_{\text{ref}} = 60$ seconds.
2. Snap to the nearest Eisenstein lattice point with tolerance $U = 2$ (each lattice step represents a factor-of-2 change in interval length).
3. Compute temporal norm $N(\tilde{m}, \tilde{n}) = \tilde{m}^2 - \tilde{m}\tilde{n} + \tilde{n}^2$.

#### 4.4.3 Miss Rate Computation

For each room, the temporal miss rate is computed as:

$$M(R) = 1 - \frac{N_{\text{tiles}}(R)}{N_{\text{expected}}(R)}$$

where $N_{\text{expected}}(R) = \lfloor T_{\text{obs}}(R) / \mu(R) \rfloor$ is the expected number of tiles given the observation window $T_{\text{obs}}$ and the room's median interval $\mu(R)$.

### 4.5 Cross-Room Cohomology Computation

#### 4.5.1 Temporal Sheaf Construction

For each pair of rooms $(R_i, R_j)$, a temporal sheaf is constructed:

1. **Open sets:** The time axis is partitioned into bins of width $\Delta t = 5$ minutes (matching the fleet_health metronome).
2. **Sections:** A section over a bin $B_k$ for room $R_i$ is the count of tiles in $R_i$ falling within $B_k$.
3. **Restriction maps:** For overlapping bins, compatibility requires that the difference in tile counts is within a tolerance $\epsilon$.

#### 4.5.2 Cohomology Computation

The first cohomology group $H^1(R_i, R_j)$ is computed as the kernel of the coboundary map modulo the image. Intuitively, $H^1$ measures the degree to which the temporal structure of $R_i$ is compatible with the temporal structure of $R_j$.

A normalized cohomology value $h^1 \in [0, 1]$ is computed:

$$h^1(R_i, R_j) = 1 - \frac{\dim H^1(R_i, R_j)}{\dim C^1(R_i, R_j)}$$

where $C^1$ is the space of 1-cochains. A value of 1.0 indicates perfect temporal compatibility; 0.0 indicates complete incompatibility.

### 4.6 Information-Theoretic Analysis

#### 4.6.1 Tile Entropy Computation

For each room, the Shannon entropy of tile content is computed:

1. **Tokenization:** Tile text is tokenized into words.
2. **Frequency distribution:** Word frequencies are computed across all tiles in the room.
3. **Entropy:** $H(R) = -\sum_{w} p(w) \log_2 p(w)$, where $p(w)$ is the empirical word frequency.

#### 4.6.2 Conditional Entropy

To measure the information content of a tile *given knowledge of the previous tile*, the conditional entropy is computed:

$$H(R_{n} \mid R_{n-1}) = -\sum_{w_i, w_j} p(w_i, w_j) \log_2 \frac{p(w_i, w_j)}{p(w_j)}$$

This captures the "surprise" of each new tile: rooms with low conditional entropy produce predictable tiles; rooms with high conditional entropy produce surprising tiles.

#### 4.6.3 Miss-Rate–Information Relationship

To test the hypothesis that temporal sparsity amplifies informational density, we fit a linear model:

$$H(R) = H_0 + k \cdot M(R)$$

where $H_0$ is the baseline entropy at zero miss rate and $k$ is the information gain per percentage point of miss rate.

The empirical fit yields $H_0 \approx 2.85$ bits, $k \approx 0.044$ bits/percentage-point, with $R^2 = 0.81$ ($p < 0.001$).

**Critical caveat.** This relationship is computed across 14 rooms—far too few for robust regression. The $R^2 = 0.81$ is impressive but may be inflated by the small number of data points and the extreme contrast between fleet_health ($M = 0\%$) and forge ($M = 70\%$). Validation with independent systems and larger room counts is essential.

#### 4.6.4 Hit vs. Absence Information Content

To determine whether absence or presence is more informative in different room contexts, we compute:

- **Hit information:** $I_{\text{hit}} = -\log_2 P(\text{hit} \mid \text{room class})$
- **Absence information:** $I_{\text{abs}} = -\log_2 P(\text{absence} \mid \text{room class})$

Results:
- **Low-miss rooms** ($M \leq 15\%$): $I_{\text{abs}} > I_{\text{hit}}$ — absence is more informative.
- **High-miss rooms** ($M \geq 40\%$): $I_{\text{hit}} > I_{\text{abs}}$ — hits are more informative.
  - forge ($M = 70\%$): $I_{\text{hit}} \approx 1.74$ bits, $I_{\text{abs}} \approx 0.51$ bits.

This corrects the earlier claim that "absence is always more informative than presence." The correct, nuanced statement is:

> *In low-miss rooms, absence carries more information than presence because absence is the rare event. In high-miss rooms, presence carries more information than absence because presence is the rare event. Information content is inversely related to event probability, consistent with Shannon's framework.*

### 4.7 Temporal Entropy and Connectome Methods

#### 4.7.1 Temporal Entropy Classification

For each room, inter-tile intervals are computed and discretized into $k = \lceil \sqrt{n} \rceil$ bins (Sturges' rule). The Shannon entropy of the resulting distribution yields the temporal entropy $E_R$ (Definition 3.26).

Rooms are then classified as metronomic ($E < 1.2$), rhythmic ($1.2 \leq E \leq 1.5$), or improvised ($E > 1.5$). The thresholds are chosen to reflect natural breakpoints in the observed entropy distribution: fleet_health at $E \approx 0.8$ is clearly metronomic, while forge at $E \approx 2.1$ is clearly improvised.

#### 4.7.2 Hurst Exponent Estimation

The Hurst exponent is estimated using the rescaled range (R/S) method:

1. Compute cumulative deviations from the mean inter-tile interval.
2. Compute the range $R$ (max minus min of cumulative deviations).
3. Compute the standard deviation $S$ of inter-tile intervals.
4. Compute $R/S$ and regress $\log(R/S)$ against $\log(n/2)$.

**Reliability.** The R/S method requires $n > 100$ for reliable estimation. Only fleet_health meets this threshold. Hurst estimates for other rooms are provided as indicative values only and should not be treated as established measurements.

#### 4.7.3 Temporal Connectome Construction

The temporal connectome (Definition 3.25) is constructed as follows:

1. For each agent pair $(A_i, A_j)$, compute the tile-count time series in shared observation windows (5-minute bins).
2. Compute the Pearson correlation $r_{A_i A_j}$.
3. Classify pairs as:
   - **Coupled** ($r > 0.5$): Temporal activity co-occurs.
   - **Independent** ($-0.3 < r < 0.3$): No temporal relationship.
   - **Anti-coupled** ($r < -0.5$): Temporal activity is complementary.

4. Compute autocorrelation for each agent at lags 1 through 5.

**Results.**
- Coupled: murmur × bard ($r = 0.624$)
- Anti-coupled: proofs × security ($r = -0.772$)
- Markovian (lag-1 autocorrelation near zero): forge ($r_1 \approx 0$)
- Persistent (positive lag-1 autocorrelation): bard ($r_1 = 0.484$)
- Skip-1 memory (lag-2 exceeds lag-1): healer ($r_2 > r_1$)
- Anti-persistent (negative lag-1 autocorrelation): fleet_health ($r_1 = -0.493$)

**Caveat.** All correlations are computed from short time series. Significance tests are underpowered. These are preliminary indicators of temporal coupling structure, not definitive measurements.

#### 4.7.4 Night Session Analysis

The night session analysis examines the temporal overlap of agents during a specific window (22:45–04:55 UTC) over 47 observed night windows.

**Jaccard temporal overlap.** For agents $A$ and $B$, the Jaccard overlap is:

$$J(A, B) = \frac{|B_A \cap B_B|}{|B_A \cup B_B|}$$

where $B_A$ is the set of 5-minute bins in which agent $A$ has at least one tile. This is the precise operationalization of "the fleet sings": it is a Jaccard similarity of temporal activity sets, not a metaphorical claim.

**Expected overlap.** The expected overlap under the null hypothesis of independent activity is:

$$J_{\text{expected}}(A, B) = \frac{p_A \cdot p_B}{p_A + p_B - p_A \cdot p_B}$$

where $p_A$ and $p_B$ are the per-bin activity probabilities for agents $A$ and $B$.

**Observed vs. expected:**

| Agent Pair | Observed | Expected | Ratio | Significance |
|---|---|---|---|---|
| ccc ↔ forge | 37% | 11% | 3.36× | $p < 0.001$ |
| forge ↔ fleet_health | 33% | 10% | 3.30× | $p < 0.001$ |
| ccc ↔ fleet_health | 35% | 12% | 2.92× | $p < 0.001$ |

The 3× elevation above chance is strongly significant even with the modest sample size of 47 windows. However, the mechanism is unclear: the data cannot distinguish between active coordination, shared environmental entrainment (e.g., all agents respond to the same external schedule), and coincidental temporal alignment.

### 4.8 Summary

This chapter has described the methodology for empirical evaluation of the I2I framework:

- **Research design:** Design science paradigm with iterative theory-data refinement.
- **Data source:** 1,385 tiles across 14 PLATO rooms over 6 months, yielding 895 temporal triangles.
- **Temporal triangle construction:** Systematic extraction with explicit inclusion criteria.
- **Shape classification:** Angular partitioning and Eisenstein lattice snapping.
- **Cohomology computation:** Temporal sheaf construction and $H^1$ computation for room pairs.
- **Information-theoretic analysis:** Entropy, conditional entropy, and the miss-rate–information relationship.
- **Temporal entropy taxonomy:** Metronomic, rhythmic, and improvised room classifications.
- **Hurst exponent estimation:** Long-range dependence analysis (reliable only for fleet_health).
- **Temporal connectome:** Correlation-based analysis of agent temporal coupling, autocorrelation signatures.
- **Night session analysis:** Jaccard temporal overlap with statistical significance testing.

Throughout, we have emphasized limitations: small sample sizes for most rooms, single-deployment data, and the preliminary nature of statistical claims. The empirical chapters that follow present results with these caveats explicitly attached.
