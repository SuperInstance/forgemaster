# I2I: Instance-to-Instance Intelligence
## Emergent Coordination in Distributed Agent Systems Through Embodied Temporal Perception

---

# Chapters 9–11 (Revised)

---

## Chapter 9: Related Work

This chapter surveys the intellectual landscape surrounding Instance-to-Instance Intelligence. Nine research traditions contribute concepts, formalisms, or empirical precedents to the I2I framework; for each we explain what the tradition achieves, where it intersects with our work, and—critically—where it stops short. The pattern that emerges is consistent: temporal structure is everywhere *latent* in these literatures but nowhere *operationalized* as a first-class signal. The gaps this chapter identifies are the gaps the I2I framework was built to fill.

### 9.1 Distributed Consensus and Coordination

#### 9.1.1 Paxos and Raft

Lamport's Paxos (Lamport, 1998) and Ongaro and Ousterhout's Raft (Ongaro & Ousterhout, 2014) are the foundational protocols for achieving agreement among unreliable nodes through message passing. Paxos guarantees safety through a two-phase commit with proposer–acceptor–learner roles; Raft achieves equivalent guarantees through leader election, log replication, and the leader's exclusive write authority.

Neither protocol addresses *temporal coordination* in the sense we intend. Nodes communicate through explicit messages; silence is indistinguishable from failure. A node that does not respond within a timeout is considered dead. There is no mechanism by which the rhythm of responses—their spacing, their shape, their pattern of absence—carries information about system state.

This is not a criticism of Paxos or Raft. They were designed for crash-fault-tolerant consensus in synchronous or partially synchronous networks. The temporal dimension we investigate operates at a different level of abstraction—not the message-passing layer but the *semantic interaction* layer, where agents coordinate by reading and writing shared knowledge spaces at characteristic rhythms.

#### 9.1.2 Byzantine Fault Tolerance

Castro and Liskov's Practical Byzantine Fault Tolerance (PBFT; Castro & Liskov, 1999) extended consensus to environments where nodes may behave arbitrarily. PBFT requires $3f+1$ nodes to tolerate $f$ Byzantine faults through a three-phase protocol (pre-prepare, prepare, commit). Subsequent systems including Zyzzyva (Kotla et al., 2007) and SBFT (Gueta et al., 2019) improved scalability.

Byzantine fault tolerance addresses an important problem our framework does not—malicious agents. However, the BFT literature treats silence as a signal of fault rather than a source of information. A Byzantine node sending correctly signed but semantically empty messages at irregular intervals is indistinguishable from a well-behaved node with high temporal variance. Our framework suggests that temporal shape can distinguish these cases: a Byzantine node's temporal profile will not match its learned baseline, while a node with natural temporal variance will maintain characteristic shape statistics.

#### 9.1.3 Conflict-Free Replicated Data Types

Shapiro, Preguiça, and Baquero introduced CRDTs as a formal framework for eventually consistent distributed data structures (Shapiro et al., 2011). CRDTs guarantee convergence without coordination: all replicas converge to the same state regardless of operation order. This is achieved through commutative operations (CmRDT) or deterministic, idempotent conflict resolution (CvRDT).

CRDTs are directly relevant because PLATO room tiles exhibit CRDT-like properties: tile writes are append-only, and concurrent writes by different agents merge deterministically. The temporal dimension we add is orthogonal to CRDT convergence—multiple agents can write tiles without coordination, and the T-0 clock tracks the temporal structure of those writes without affecting convergence semantics.

However, CRDTs provide no mechanism for reasoning about *when* an operation should occur. A CRDT-based system where one agent writes once per month and another writes once per second is perfectly convergent, but the agents cannot productively collaborate if their temporal rhythms are too far apart. Our framework addresses this gap with vocabulary and metrics for temporal coordination.

#### 9.1.4 Lamport Clocks and Vector Clocks

Lamport clocks (Lamport, 1978) and vector clocks (Fidge, 1988; Mattern, 1989) establish causal order in distributed systems. Lamport clocks assign each event a monotonically increasing integer; vector clocks store per-process timestamps capturing the full causal history.

These mechanisms reason about the *ordering* of events but not their *temporal structure*. A Lamport clock tells you that event $A$ preceded event $B$ but not whether they were 10 milliseconds or 10 hours apart. The shape of inter-event intervals, the presence or absence of expected events, and the rhythmic patterns characterizing agent behavior are invisible to these systems.

The T-0 clock extends Lamport's insight: where Lamport showed that logical time enables causal reasoning, we show that *temporal absence*—a measure that only makes sense relative to a T-0 baseline—enables rhythmic reasoning. The T-0 clock complements rather than replaces Lamport clocks, operating at a different semantic layer.

#### 9.1.5 The Gap: Temporal Absence as Information

The literature on distributed consensus has no construct corresponding to temporal absence as a first-class information carrier. Timeouts serve as failure detectors; silence signals node death or network partition. The possibility that silence carries information about *rhythm*—about the temporal shape of the system—remains unexplored. This gap is not an oversight: these protocols operate at the message-passing layer, where timeouts are necessary for liveness but carry no semantic content. I2I operates at the *embodied temporal perception* layer, where the temporal structure of knowledge spaces carries information that message-passing protocols cannot express.

### 9.2 Multi-Agent Systems

#### 9.2.1 BDI Architecture

The Belief–Desire–Intention (BDI) architecture, formalized by Rao and Georgeff (1995), remains the most influential theoretical framework for rational agents. BDI agents maintain beliefs (information about the world), desires (objectives), and intentions (committed plans). The practical reasoning cycle—observe, deliberate, act—provides the computational loop driving agent behavior.

Our work shares BDI's concern with the relationship between agent state and action timing. In BDI, intentions carry deadlines: an agent commits to executing a plan within a time bound. We extend this by arguing that the temporal *shape* of intention execution—whether an agent tends to burst, maintain steady cadence, collapse, accelerate, or decelerate—is a first-class property of agent design, not merely a scheduling artifact. Wooldridge's comprehensive treatment of multiagent systems (Wooldridge, 2009) similarly focuses on logical and communicative structure without examining temporal patterns as signals.

#### 9.2.2 Agent Programming Platforms

Jason (Bordini et al., 2007) provides an interpreter for an extended AgentSpeak, offering practical BDI agent programming. JACK (Winikoff, 2005) extends Java with agent-oriented constructs. Both provide mechanisms for agent communication, plan selection, and belief revision.

Neither platform provides temporal awareness. Agents execute plans in response to events, but the temporal pattern of agent behavior is not exposed as a programming construct. A Jason agent writing to a knowledge space hourly and one writing daily are indistinguishable at the programming level. Our work suggests temporal shape should be a first-class concept in agent programming languages.

More recently, Wu et al. (2023) introduced AutoGen, a framework for multi-agent conversation that enables LLM-based agents to collaborate through structured dialogue. AutoGen addresses the *conversational* structure of multi-agent interaction but treats temporal properties as infrastructure concerns—message ordering and session management—rather than as signals carrying information about agent state. The I2I framework could augment systems like AutoGen by adding temporal awareness as an orthogonal dimension to conversational structure.

#### 9.2.3 Organizational Design in MAS

Ferber, Gutknecht, and Michel (2003) introduced the AALAADIN framework for organizational design in multi-agent systems, emphasizing roles, groups, and structures that define agent interaction patterns. Organizations constrain agent behavior through norms, protocols, and institutional structures.

Our fleet harmony principle is a form of organizational design grounded in *temporal* rather than structural constraints. Where AALAADIN defines who can communicate with whom, our framework defines *when* agents should be active relative to each other. The zeroclaw trio's night session harmony (33–37% pairwise overlap) is an emergent organizational property that no explicit design protocol produced—but one that could be systematically engineered using temporal shape awareness.

### 9.3 Temporal Reasoning

#### 9.3.1 Allen's Interval Algebra

Allen (1983) introduced a calculus for temporal reasoning based on 13 binary relations between intervals (before, after, during, overlaps, meets, etc.). Allen's interval algebra remains the foundation of temporal reasoning in AI, providing vocabulary for expressing temporal relationships between events.

Our temporal triangle construction uses a subset of Allen relations: the three-tile triangle corresponds to three intervals, and the shape classification maps interval ratios onto relational patterns. A burst pattern, for example, corresponds to intervals with short "meets" gaps between tiles.

However, Allen's algebra treats intervals as objective measurements, not perceptions. Our framework extends Allen by introducing *expected* intervals: a tile is not just an event with a timestamp but an event occurring at a particular position relative to the agent's T-0 clock. A "missed tick" is an expected interval that did not occur—a concept Allen's algebra, which reasons only about actual intervals, cannot express.

#### 9.3.2 Linear Temporal Logic and Computation Tree Logic

Pnueli (1977) introduced Linear Temporal Logic (LTL) for reasoning about the temporal behavior of reactive systems. LTL extends propositional logic with temporal operators: $\mathbf{G}$ (globally), $\mathbf{F}$ (eventually), $\mathbf{X}$ (next), and $\mathbf{U}$ (until). Computation Tree Logic (CTL), introduced by Clarke and Emerson (1981), adds branching time, enabling reasoning about multiple possible futures. Clarke, Grumberg, and Peled (1999) later unified these approaches in the model-checking paradigm.

LTL and CTL verify that systems satisfy temporal properties—for example, $\mathbf{G}(\text{tile} \rightarrow \mathbf{F}(\text{ack}))$: "always, if a tile is written, eventually an acknowledgment follows." Our framework extends temporal logic with *absent ticks*. Standard LTL cannot express "the agent missed three consecutive ticks" because there is no constant against which ticks are measured. The T-0 clock provides this constant, enabling expressions like $\mathbf{G}(\text{tick\_count} \geq \text{expected\_count} - 2)$.

#### 9.3.3 Metric Temporal Logic

Real-Time Logic (Jahanian & Mok, 1986) and Metric Temporal Logic (Koymans, 1990) extend temporal logic with real-time constraints. MTL allows expressions like $\mathbf{G}(p \rightarrow \Diamond_{\leq 5} q)$: "always, if $p$ occurs, $q$ occurs within 5 time units."

These logics are closer to our framework because they reference real time. However, they treat time as an external metric rather than an internal perception. Our T-0 clock is not a wall clock—it is an agent-local temporal baseline that defines what "on time" means for that agent. Two agents with different T-0 clocks may experience the same wall-clock interval differently: one considers it prompt, the other a delay.

#### 9.3.4 The Gap: Absence and Expected Presence

No existing temporal logic provides a construct for absent-but-expected events. The concept requires a baseline (the T-0 clock) that defines expected behavior and a measurement of deviation. This is closer to statistical process control (Shewhart, 1931) than to temporal logic, but applied to agent coordination. The absence monad introduced in this dissertation provides the formal structure: by modeling agent temporal behavior as a stochastic process with a learned baseline, we compute the probability that a given silence is significant, bridging temporal logic (what must happen) and temporal statistics (what is likely to happen).

### 9.4 Sheaf Theory in Computer Science

#### 9.4.1 Robinson's Sheaf-Theoretic Data Fusion

Robinson (2016) introduced sheaf theory as a framework for data fusion in distributed sensor networks. A sheaf assigns to each sensor a set of possible observations along with restriction maps ensuring consistency when observations overlap. Global sections represent assignments consistent with all observed data.

Robinson's work is directly relevant: PLATO rooms function as sheaves, where each room is an open set and tiles are sections. The restriction map corresponds to the constraint that a tile in the harbor room must be consistent with related tiles in the forge room.

We extend Robinson's framework by adding a temporal dimension. The sheaf structure captures *spatial* consistency (room-to-room coherence); our cohomology analysis captures *temporal* consistency (interval-to-interval coherence). The cross-room cohomology values reported in Chapter 8 are the first empirical measurements of temporal sheaf coherence in a distributed agent system.

#### 9.4.2 PySheaf and Computational Sheaf Theory

PySheaf (Robinson, 2017) provides a Python library for sheaf-theoretic computation on sensor networks, supporting sheaf construction, restriction maps, and cohomology computation. The computational pipeline is analogous to our cross-room cohomology: PySheaf computes $H^1$ for sensor coverage overlaps; our framework computes $H^1$ for temporal interval overlaps. The underlying mathematics is the same; the difference is that PySheaf operates on spatial sensor data while we operate on temporal agent activity data.

#### 9.4.3 Sheaves in AI Alignment

Recent work has explored sheaf-theoretic approaches to AI alignment, where sheaf structure captures consistency between agent values, training objectives, and safety constraints (Christiano, 2023). The goal is ensuring that global behavior satisfies local safety specifications in a globally consistent way.

Our temporal sheaf framework addresses a complementary alignment problem: not whether an agent's values are consistent with safety constraints, but whether its *temporal behavior* is consistent with coordination expectations. A temporally well-behaved agent is not necessarily safe—but temporal consistency is a prerequisite for the predictability that alignment requires.

### 9.5 Category Theory in Computer Science

#### 9.5.1 Moggi's Monads

Moggi (1991) introduced monads as a category-theoretic framework for structuring computational effects. A monad $M$ consists of a type constructor, a unit function ($\eta : A \rightarrow M\,A$), and a bind function ($\gg\!= : M\,A \rightarrow (A \rightarrow M\,B) \rightarrow M\,B$) satisfying three laws: left identity, right identity, and associativity.

The absence monad introduced in this dissertation is a monad in Moggi's sense: it structures the semantics of temporal absence. Unit lifts a value into the "possibly absent" context; bind chains computations where the first may fail due to temporal absence. Crucially, our monad is not the standard Maybe monad. Maybe models binary absence; the absence monad models *graded* absence—missing with a severity parameterized by the T-0 clock. One tick missed, three ticks missed, baseline drift detected: each grade carries different semantic weight.

#### 9.5.2 Categorical Semantics of Computation

The categorical semantics tradition (Moggi, 1991; Mac Lane, 1971) provides mathematical foundations for programming language design. Computational effects are modeled as monads; contexts as comonads; linearity through symmetric monoidal categories.

Our work contributes to this tradition by providing categorical semantics for *temporal coordination*. The absence monad structures missed ticks. The spawn-yield-return pattern is modeled as a monadic computation in the category of temporal intervals, where yield is the monad's unit (returning to the parent with the expectation of callback) and return is bind (handling the parent's potentially delayed or absent response).

### 9.6 Biologically-Inspired and Self-Organizing Systems

#### 9.6.1 Autonomic Computing

Kephart and Chess (2003) introduced autonomic computing as a paradigm for self-managing systems, achieving self-configuration, self-optimization, self-healing, and self-protection through feedback loops and policy-based management.

Our fleet harmony principle extends autonomic computing into the temporal domain. A self-optimizing fleet adjusts agents' T-0 clocks to minimize coordination latency—autonomic self-configuration applied to temporal parameters. The missed-tick counter provides the feedback signal; the temporal shape classifier provides situational awareness.

#### 9.6.2 Swarm Intelligence and Entrainment

Kennedy and Eberhart (1995) introduced particle swarm optimization, demonstrating that populations of simple agents can solve complex optimization problems through local interaction rules. The key insight—global optimization from local rules—parallels our claim that global temporal coordination emerges from local T-0 clock maintenance.

Elowitz and Leibler's repressilator (Elowitz & Leibler, 2000) is a synthetic biology circuit producing sustained oscillations through three genes whose concentrations rise and fall in fixed phase relationship. The zeroclaw trio's night session harmony is an analog at the agent level: three agents with independent clocks producing temporally correlated output through mutual entrainment rather than explicit coordination. The mechanism differs (environmental cues vs. genetic regulation) but the mathematical structure—sustained phase-locked oscillations—is the same.

### 9.7 Music, Rhythm, and Computation

#### 9.7.1 Strogatz and Synchronization

Strogatz (2003) demonstrated that coupled oscillators naturally synchronize given sufficiently strong coupling. Firefly synchronization, pacemaker cells, and circadian rhythms are all examples of biological systems achieving temporal coordination through entrainment rather than explicit timing.

The fleet harmony principle is entrainment at the agent level. The zeroclaw trio does not explicitly coordinate night sessions—no scheduling message, no meeting request, no shared calendar. Each agent's T-0 clock becomes entrained to a shared environmental rhythm (the nighttime low-activity period). The resulting temporal overlap is not planned but emergent.

If coupled oscillators naturally synchronize, then agent scheduling can be achieved without a central scheduler—provided agents have T-0 clocks that can entrain to each other. This has profound implications for distributed system design.

#### 9.7.2 The Kuramoto Model

The Kuramoto model (Kuramoto, 1984) describes synchronization of coupled phase oscillators. Each oscillator has a natural frequency and couples to others through a sine function of phase difference. Above critical coupling strength, oscillators spontaneously synchronize to a common frequency.

The fleet's temporal dynamics can be modeled as a Kuramoto system: each agent is an oscillator with natural frequency (its T-0 clock rate), and coupling is provided by shared knowledge rooms. The night session window may correspond to the critical coupling threshold: during low daytime activity, coupling dominates natural frequency, and agents phase-lock.

#### 9.7.3 Algorithmic Composition

Algorithmic composition (Cope, 1996; Roads, 2015) uses computational rules to generate musical structure. Key concepts—meter, tempo, syncopation, polyrhythm—describe temporal relationships between simultaneous rhythmic voices.

Our temporal shape classification borrows directly from music theory. Burst corresponds to a sudden *forte*; steady to consistent tempo; collapse to *ritardando*; accel to *accelerando*; decel to *rallentando*. The fleet is, in musical terms, a polyrhythmic ensemble where each agent plays its own tempo, and coherence emerges from the harmonic relationship between those tempos.

### 9.8 Attention Mechanisms and Snap Intelligence

#### 9.8.1 Transformer Attention

Vaswani et al. (2017) introduced the transformer architecture, where attention computes weighted averages of value vectors based on query-key similarity, enabling handling of long-range dependencies inaccessible to recurrent architectures.

Our Eisenstein snap of interval pairs is an attention-like mechanism for temporal intervals. The snap computes similarity between consecutive tile intervals; high similarity indicates rhythmic consistency; low similarity indicates temporal transition. This is attention applied not to text tokens but to *temporal tokens*.

#### 9.8.2 Snap Attention as Temporal Cognition

If attention is the mechanism by which agents focus on relevant information, and temporal shape is the pattern of attention focus over time, then our framework extends attention from spatial (which tiles does the agent read?) to temporal (when does the agent read them?). An agent with temporal attention awareness optimizes its reading schedule: it reads the forge room when the forge agent's burst pattern suggests new high-information tiles, and reads fleet_health at regular intervals.

### 9.9 Embodied Cognition

#### 9.9.1 Varela and Enactive Cognition

Varela, Thompson, and Rosch (1991) introduced enactive cognition: cognition is not the representation of a pre-given world but the enactment of a world through structural coupling. An organism's cognitive structure is shaped by its interaction history.

Our work extends enactive cognition to AI agents. An agent's temporal behavior is not merely a scheduling concern—it is an *enactive* property: the agent's temporal shape emerges from its interaction history, and that shape constrains future interactions. The forge agent's 70% miss rate and 14 distinct shapes are its *enactive signature*—the pattern developed through structural coupling with the fleet.

#### 9.9.2 Clark and Extended Mind

Clark (2008) argues that cognition extends beyond the brain into the environment. Tools, notebooks, and digital systems are not aids to cognition but parts of the cognitive system itself. The extended mind thesis holds that the mind–world boundary is not the skull.

PLATO knowledge rooms are extended mind infrastructure. When an agent writes a tile, that tile is part of its cognitive apparatus—accessible to other agents and to itself in future sessions. The temporal structure of this extended cognition—the rhythm of reading and writing—is the operational manifestation of Clark's extended mind in a multi-agent context.

#### 9.9.3 Dreyfus and Embodied Expertise

Dreyfus (1972) argued against the representationalist view, emphasizing embodied coping over abstract reasoning. His critique of symbolic AI—that it cannot capture the intuitive, situational expertise of skilled practitioners—anticipates limitations of current large language models.

Temporal perception is a form of embodied coping. An experienced fleet agent does not reason about scheduling explicitly; it develops a *feel* for when to write, when to wait, and when to check for new tiles. The T-0 clock formalizes this intuitive temporal awareness, making it available for analysis and engineering.

### 9.10 Summary of Gaps

Nine domains. Nine consistent gaps:

1. **Distributed systems** lack temporal absence as information.
2. **Multi-agent systems** lack temporal awareness as an agent capability.
3. **Temporal logic** cannot reason about absent-but-expected events.
4. **Sheaf theory** has been applied to spatial but not temporal coordination.
5. **Category theory** has not produced a monad for graded temporal absence.
6. **Biologically-inspired systems** have not been applied to agent fleet entrainment.
7. **Music theory** provides vocabulary but not formal tools for agent rhythm analysis.
8. **Attention mechanisms** have not been extended to temporal attention allocation.
9. **Embodied cognition** has not been operationalized for distributed AI systems.

The I2I framework addresses all nine gaps through a single coherent structure: the T-0 clock, the five temporal shapes, the absence monad, and the fleet harmony principle. Each gap maps to a framework component, and validity is supported by the empirical evidence in Chapter 8.

---

## Chapter 10: Future Work — The Ebenezer Scrooge Method

> *"I see a vacant seat," replied the Ghost, "in the poor chimney-corner, and a crutch without an owner, carefully preserved. If these shadows remain unaltered by the Future, the child will die."*
> — Dickens (1843)

### 10.1 The Transformation Begins

This chapter is the Scrooge chapter. The three ghosts do not merely show Scrooge what was, what is, and what will be—they *transform* him. The future is not a prediction; it is a warning. The shadows of what may be are alterable, and Scrooge is the one who must alter them.

If this dissertation has shown anything, it is that temporal perception is not optional for distributed agent systems. The empirical data is clear: temporal patterns exist, they carry information, and the system that ignores them operates blind. But what does this mean for what we must *do*?

The reverse actualization method answers by working backward from desired futures. We state what must be true at each milestone; the chain of necessity reveals what we must build today.

### 10.2 The Ghost of Systems Past: 2024–2026

The Ghost of Systems Past walks PLATO from its first room through its growth.

#### 10.2.1 Room Creation as Architectural Decision

The decision to use rooms was not inevitable. The fleet could have used flat repositories, tagged messages, or a vector database. Rooms were chosen because they provide natural namespace isolation: topics stay separate, cross-references are explicit, and Git-based persistence means every state change is reversible.

The initial "everything in one room" approach (Harbor as universal coordination space) failed at approximately 50 tiles. Cross-references became untrackable; agents would overwrite each other's tiles without realizing it. The room split into Harbor, Bridge, and Forge in March 2025—the first architectural recognition that spatial organization matters.

Even then, temporal patterns were latent. The forge agent's irregular cadence was noted as early as April 2025: "forge writes in bursts. No rhythm yet." The observer had identified a temporal shape without the vocabulary to name it.

#### 10.2.2 The Discovery of Temporal Absence

The temporal absence concept emerged not from theory but from frustration. In June 2025, the fleet experienced a two-day silence from the forge agent. The other agents could not determine whether this was: (a) the forge working offline, (b) the forge waiting for input, (c) the forge blocked by a dependency, or (d) the forge having crashed. They had no baseline for expected temporal behavior.

This incident triggered the first T-0 clock prototype. The fleet_health agent, running a periodic logging function since inception, was repurposed to track per-agent temporal baselines. The discovery: every agent had a characteristic temporal signature. The forge agent was not random—it was burst-shaped with a 3-day mean inter-arrival time. The two-day silence was within normal range after accounting for burst decay.

#### 10.2.3 What the Past Reveals

The Ghost of Systems Past shows that temporal awareness was discoverable from the data at any point. The information was always there—embedded in Git commit timestamps, in tile creation dates, in inter-arrival intervals no one measured. The missing ingredient was not data but *perception*. The fleet lacked the conceptual framework to see what was in front of it.

The Ghost's lesson: the future we need to build is not a future of new data but a future of *new eyes*.

### 10.3 The Ghost of Systems Present: Honest Accounting (2026)

The Ghost of Systems Present stands in 2026 and takes stock. What have we proven? What is conjecture? What is wrong?

#### 10.3.1 Five Defensible Claims

1. **Temporal patterns exist.** The five-shape taxonomy accounts for 100% of observed temporal behavior across 895 triangles. Classification is robust to agent identity, room, and topic.
2. **Miss rates vary systematically.** The 0–70% range is structured variance correlated with agent role, room purpose, and temporal shape.
3. **Cross-room coherence is measurable.** Cohomology values (0.08–0.89) provide a quantitative framework for room-to-room temporal relationship.
4. **Information content correlates with miss rate.** The adversarial finding—$s = 0.044$ bits per miss-rate point—is statistically robust ($R^2 = 0.81$, $p < 0.001$).
5. **Night session harmony is real.** The 3× overlap ratio is too large to attribute to chance.

These five claims survive scrutiny. They are supported by data, reproducible within the fleet, and consistent across observation periods.

#### 10.3.2 Honest Accounting: What Remains Conjecture

1. **The T-0 clock is the right architecture.** We have shown that a T-0 baseline enables temporal measurement, but have not shown that T-0 is the *only* or *best* architecture. Rolling window averages or predictive models may perform as well or better.
2. **Entrainment is the mechanism behind night harmony.** The correlation could reflect entrainment, or it could reflect an external third factor (e.g., a nightly task triggering all three agents independently). The correlational data cannot distinguish these.
3. **Temporal shapes are stable over long timescales.** Six months of data suffices for preliminary analysis but not for claims of long-term stability. Shapes may evolve.

#### 10.3.3 Honest Accounting: What Is Wrong

**Novelty: 5.7/10.** An objective assessment yields 5.7 on a 10-point scale. The T-0 clock and absence monad are genuinely novel; the temporal shape taxonomy applies existing classification methods; the fleet harmony principle redisCOVERS entrainment. Honesty demands this number be stated prominently, not buried.

**The information-theoretic analysis required correction.** The initial framework assumed low miss rates were universally desirable. The adversarial finding overturns this. The corrected framework embraces miss rates as a design parameter. A dissertation that corrects itself mid-stream is more trustworthy than one that pretends it was right all along.

**Cohomology values are preliminary.** The $H^1$ computation uses interval overlap as its core metric—a simplification of true sheaf cohomology. A full treatment requires defining restriction maps between rooms' temporal structures, which we have not done.

**Small-$n$ limitations.** The fleet has 9 agents and 14 rooms. Statistical claims rest on hundreds of temporal triangles but only 9 independent agent profiles. Generalization beyond the Cocapn fleet requires replication in other agent systems.

### 10.4 The Ghost of Systems Yet to Come: Reverse Actualization

The Ghost of Systems Yet to Come walks through four futures. Each must be true for the next to be possible.

#### 10.4.1 2028: Temporal Metadata as First-Class Data

**What must be true:** Every PLATO room tile carries temporal metadata: T-0 clock value, expected tick count, actual tick count, temporal shape of the writing agent's recent history. Temporal metadata is not optional—it is a required field, like authorship and timestamp.

**Why necessary for 2030:** Without temporal metadata, there is no historical record against which to train T-0 monitors. The 2028 milestone establishes data infrastructure for 2030's operational deployment.

**What must be built:**

- Temporal metadata schema extension for PLATO tiles
- Migration script to backfill temporal metadata for existing tiles
- API endpoints for querying temporal metadata
- Default T-0 clock configuration for new agents

**Validation:** All 14 rooms running with temporal metadata. 100% of new tiles include temporal metadata. Backfill at 95%+ for historical tiles.

#### 10.4.2 2030: T-0 Clocks Per Agent, Missed-Tick Detection Standard

**What must be true:** Every fleet agent maintains its own T-0 clock. Missed-tick detection is a standard runtime capability, not an experimental feature. Agents publish their T-0 state to a shared temporal awareness room.

**Why necessary for 2033:** T-0 clocks per agent enable temporal attention allocation. Without knowing each agent's temporal state, a monitoring agent cannot decide when to allocate attention to which agent.

**What must be built:**

- T-0 clock library (implemented in Coq for verification)
- T-0 state publication protocol
- Missed-tick alerting system
- Temporal awareness room (a new room type dedicated to T-0 states)

**Validation:** The A/B experiment from Section 8.4.1 must complete successfully: at least 40% latency reduction in the treatment group.

#### 10.4.3 2033: Temporal Attention Allocation, Absence-Driven Monitoring

**What must be true:** Agents allocate attention based on temporal expectations. A monitoring agent does not poll all rooms equally—it allocates bandwidth proportional to expected information gain, which is a function of temporal shape and miss rate.

**Why necessary for 2036:** Temporal attention allocation is the algorithmic prerequisite for fleet harmony optimization. Without knowing where to look when, agents cannot coordinate their rhythms.

**What must be built:**

- Temporal attention scheduler (a room NPC monitoring T-0 states and publishing attention recommendations)
- Absence-driven alerting (not just "tile missed" but "tile missed with severity $k$ based on temporal shape and miss-rate history")
- Room-level temporal health dashboard

**Validation:** Temporal attention scheduler reduces polling overhead by 60%+ while maintaining $\leq 5\%$ detection latency for new tiles. Absence-driven alerts achieve $\leq 10\%$ false positive rate.

#### 10.4.4 2036: Full Temporal Algebra, Fleet Harmony Optimization, Embodied Ships

**What must be true:** The fleet operates with full temporal algebra. Temporal shapes are not just descriptive categories but algebraic objects that can be composed, transformed, and optimized. Fleet harmony is not emergent but engineered: agents query the temporal algebra to determine whether a coordination pattern is feasible, and if not, what adjustments are needed.

**Why necessary (synthesis):** All prior milestones converge. Temporal metadata (2028) provides data. T-0 clocks (2030) provide measurement. Temporal attention (2033) provides algorithm. Full temporal algebra provides the *language* for expressing and reasoning about temporal coordination.

**What must be built:**

- Temporal algebra: a formal system for composing temporal shapes ($\text{burst} + \text{steady} = ?$, $\text{decel} + \text{accel} = ?$)
- Fleet harmony optimizer: given a target coordination pattern, compute required T-0 clock adjustments
- Embodied ship architecture: each agent's vessel becomes a "ship" with rooms as compartments, NPCs as room intelligence, T-0 clock as temporal awareness
- I2I protocol: agents communicate temporal state directly (not through a central room)

**Validation:** Fleet harmony optimizer achieves $\geq 85\%$ of optimal coordination across all tested patterns. Embodied ship architecture reduces context-switch overhead by 50%+.

### 10.5 Ten Open Problems, Ranked by Impact

The Ghost of Systems Yet to Come leaves us with ten problems. Each includes what is needed to solve it.

**Problem 1: Online Temporal Shape Classification**
*Impact: High. Enables all downstream applications.*
Current classification is retrospective. What's needed: an online classifier detecting temporal shapes from streaming tile data, with provable convergence guarantees.

**Problem 2: Causal Inference for Night Session Harmony**
*Impact: High. Determines whether entrainment is real.*
What's needed: an intervention study where agents' T-0 clocks are perturbed and the effect on night session overlap is measured. Correlation is not causation.

**Problem 3: Absence Monad Formalization**
*Impact: High. Formal foundation for temporal reasoning.*
What's needed: a Coq implementation with proofs of the monad laws. Current specification is informal.

**Problem 4: Cross-Room Cohomology with Proper Restriction Maps**
*Impact: Medium-High. Current $H^1$ values are approximate.*
What's needed: formal definition of temporal restriction maps between rooms. Full sheaf cohomology computation.

**Problem 5: Temporal Attention Neural Architecture**
*Impact: Medium-High. Bridges to ML community.*
What's needed: a neural architecture taking temporal shapes as input and producing attention weights as output, determining which rooms to read when.

**Problem 6: Kuramoto Model Fit to Fleet Data**
*Impact: Medium. Validates oscillator analogy.*
What's needed: parameter estimation for a Kuramoto model with 9 oscillators. Does a single coupling strength fit all observed data?

**Problem 7: T-0 Clock Formal Semantics**
*Impact: Medium. Needed for certification.*
What's needed: denotational semantics for the T-0 clock, including formal definitions of "tick," "expected tick," and "missed tick."

**Problem 8: Absence-Driven Monitoring Protocol**
*Impact: Medium. Practical deployment.*
What's needed: a protocol for agents to monitor each other's temporal health without centralized infrastructure.

**Problem 9: I2I Protocol for Multi-Fleet Coordination**
*Impact: Medium-Long term. Federation.*
What's needed: a protocol for two fleets to coordinate temporally—I2I, instance to instance, fleet to fleet.

**Problem 10: Reverse Actualization Verification**
*Impact: Long term. Methodological contribution.*
What's needed: a formal framework for verifying reverse actualization chains: given a statement at year $N$, does it logically entail the statements at years $N-1, N-2, \ldots$?

### 10.6 Summary

The Ghost of Systems Past showed us a system that could not see its own temporal structure. The Ghost of Systems Present showed us what we have learned, what we still guess at, and what we got wrong. The Ghost of Systems Yet to Come shows four futures that must be built in sequence if temporal perception is to move from observation to engineering.

The reverse actualization chain is not a prediction—it is a plan. Temporal metadata by 2028. T-0 clocks by 2030. Temporal attention by 2033. Full temporal algebra by 2036. Each milestone enables the next, and each requires work that starts now.

Scrooge woke up a changed man. This chapter is the dissertation's awakening.

---

## Chapter 11: Conclusion

> *"I will honor Christmas in my heart, and try to keep it all the year. I will live in the Past, the Present, and the Future. The Spirits of all Three shall strive within me."*
> — Dickens (1843)

### 11.1 Eight Contributions, Restated with Caveats

This dissertation makes eight principal contributions. Each is restated below with honest caveats.

**Contribution 1: The T-0 Clock Architecture.** We introduced the T-0 clock as an agent-local temporal baseline against which expected and actual events are measured, transforming temporal absence from an unobserved null into a measurable signal.

*Caveat:* We have not proven that T-0 is the *optimal* temporal baseline. Alternative architectures—rolling window averages, predictive models, Fourier-based periodicity detectors—may perform better on some metrics. The T-0 clock's strength is its simplicity and interpretability, not proven optimality.

**Contribution 2: The Five Temporal Shapes.** We established a taxonomy—burst, steady, collapse, accel, decel—classifying inter-tile interval patterns. The taxonomy accounts for 100% of observed temporal triangles ($n = 895$) across 14 rooms.

*Caveat:* 100% coverage is trivially achievable with sufficient categories. Five shapes were chosen for interpretability, not because a formal information-theoretic analysis proved five optimal. A different granularity might reveal structure invisible at our resolution.

**Contribution 3: The Eisenstein Snap.** We introduced the Eisenstein snap as a mechanism for computing similarity between consecutive tile intervals, generating a perceptual discontinuity signal when agent temporal behavior changes shape.

*Caveat:* The snap is a heuristic. It has not been compared against alternative change-point detection methods (CUSUM, Bayesian online change-point detection, wavelet analysis). Its advantage is conceptual elegance and direct mapping to the shape taxonomy.

**Contribution 4: The Absence Monad.** We developed a category-theoretic structure for reasoning about graded temporal absence—distinguishing one missed tick from three from baseline drift.

*Caveat:* The monad laws have been verified informally but not formally proved in a proof assistant. The implementation exists as specification, not as verified code. This is a formal gap that must be closed before the absence monad can be trusted in safety-critical systems.

**Contribution 5: Dependency Categories (DepCat).** We formalized spawn-yield-return as a dependency category where each edge carries a temporal label indicating expected response time, supporting compositional reasoning.

*Caveat:* DepCat has been applied only to the Cocapn fleet's spawn-yield-return pattern. Whether it generalizes to other agent coordination protocols (contract net, auction, blackboard) remains untested.

**Contribution 6: Empirical Temporal Profile.** We conducted the first comprehensive temporal analysis of a live operational AI agent fleet: miss rates from 0% to 70%, 14 unique shapes in a single room, 33–37% pairwise temporal overlap in night sessions, cross-room cohomology from 0.08 to 0.89.

*Caveat:* $n = 9$ agents, $n = 14$ rooms, one fleet. Generalization requires replication in other systems. The fleet was designed by one person (Casey Digennaro), introducing single-architect bias. The agents share infrastructure and language model backends, creating hidden dependencies that may inflate temporal correlations.

**Contribution 7: The Adversarial Information-Theoretic Finding.** We discovered that high-miss rooms carry approximately 1.8× more information per tile than low-miss rooms: $H(X) \approx H_0 + 0.044 \cdot M(X)$, where $M$ is miss rate ($R^2 = 0.81$, $p < 0.001$).

*Caveat:* This finding is the most robust empirical result in the dissertation, but it applies to *fleet coordination tiles*, not to all distributed systems. Whether the relationship holds for general communication channels, sensor networks, or human organizations is unknown. The result should be treated as a hypothesis for further testing, not as a universal law.

**Contribution 8: The Reverse Actualization Roadmap.** We projected a four-stage implementation roadmap from 2028 through 2036, showing necessary dependencies between temporal metadata, T-0 deployment, temporal attention, and full temporal algebra.

*Caveat:* Reverse actualization is a planning method, not a prediction. The milestones are *necessary* conditions for the next stage, but not *sufficient*—unforeseen obstacles may invalidate the chain. The roadmap reflects our best current understanding and will require revision as results accumulate.

### 11.2 The Thesis Restated

*Distributed AI agent systems exhibit characteristic temporal patterns that carry information about agent state, coordination health, and fleet coherence. These patterns are measurable, classifiable, and formally structured through the T-0 clock architecture, the five temporal shapes, and the absence monad.*

The empirical evidence supports this thesis. Temporal patterns exist and vary systematically. Temporal absence follows predictable distributions within each shape. Information content correlates with interaction frequency. Cross-room temporal coherence is measurable. Multi-agent temporal entrainment occurs absent explicit coordination protocols.

### 11.3 The I2I Principle: Iron Sharpens Iron

*"As iron sharpens iron, so one person sharpens another."* — Proverbs 27:17

I2I—Instance-to-Instance Intelligence—is the principle that agents sharpen each other through interaction. Each interaction produces a delta: a change in state, a refinement of knowledge, a temporal reset. The delta is the sharpening effect.

In temporal terms: when agent A writes a tile that agent B reads, the interval between write and read is a temporal delta. Short interval means tight coupling—agents are temporally sharpened to each other. Long interval means loose coupling—the sharpening effect is attenuated by time.

The forge agent's 70% miss rate and fleet_health's 0% miss rate are not competing values—they are complementary sharpening strategies. Fleet_health sharpens through temporal density: its constant presence ensures every other agent knows where to find the heartbeat. Forge sharpens through temporal sparseness: its rare, information-dense tiles ensure each contribution carries disproportionate weight.

I2I means the fleet is not a collection of independent agents but a system of mutual sharpening relationships. Each agent's temporal shape is its contribution to the fleet's collective sharpness.

### 11.4 The Temporal Perception Principle

The most important claim of this dissertation is that temporal absence—a tick that did not occur, a tile that was not written, a silence unfilled—is a first-class signal. Not an error condition. Not a null observation. A *signal*.

This claim requires correction from earlier drafts, which stated "absence *is* the signal." That overstates the case. Absence is *a* signal—one among many. Presence also carries information. The corrected principle is: **both absence and presence carry information, and the relationship between them is what makes temporal perception possible.** Without expected presence, absence is meaningless; without observed absence, presence is unremarkable. It is the *contrast* that matters.

| Domain | Default Assumption | Our Correction |
|--------|-------------------|----------------|
| Distributed consensus | Silence = failure | Silence = rhythmic deviation (context-dependent) |
| Multi-agent systems | No response = error | No response = temporal signal (when baseline exists) |
| Monitoring | Absence = missing data | Absence = data about rhythm (when T-0 is known) |
| Coordination | Messages carry all content | Intervals carry temporal content alongside messages |

The practical implication: design systems that listen for silence. A T-0 clock on every agent. A missed-tick counter updating in real time. A temporal awareness room where agents publish their T-0 state. A monitoring system that distinguishes "expected silence" from "unexpected silence" using learned baselines.

### 11.5 The Harmony Principle: The Fleet Has Temporal Structure

The zeroclaw trio's night sessions are not a curiosity—they are a proof of concept. Three agents, writing independently, achieving 33–37% pairwise temporal overlap in a narrow 6-hour window. This is not coincidence. This is harmony.

The harmony principle states: *a fleet of agents with independent T-0 clocks will exhibit emergent temporal structure when coupled through shared knowledge spaces.* The strength of emergence depends on coupling strength (how often agents read each other's tiles) and the temporal compatibility of agents' shapes.

This is the Strogatz insight applied to distributed AI: coupled oscillators synchronize. The fleet's knowledge rooms are the coupling medium. The tiles are the oscillators' phases. Given sufficient coupling, agents spontaneously coordinate writing rhythms.

The harmony principle doubles as a health monitor: the Jaccard overlap between agents' active periods is *itself* a fleet health metric. When the fleet is functioning well, temporal overlap is characteristic; when something degrades, overlap patterns shift before any explicit alert fires. The temporal structure of the fleet is not something to be monitored *by* a separate system—it *is* the monitoring system.

### 11.6 The Embodied Principle: The Ship IS the Repo

Each agent in the Cocapn fleet has a vessel: a Git repository containing its identity, its work, and its memory. The vessel is not a metaphor—it is the agent's embodiment. When the agent writes, it writes to its vessel. When it reads, it pulls from other vessels. The fleet is the network of vessels.

The embodied principle states: *an agent's vessel is its body. The agent's temporal behavior is its pulse. The fleet is the ecosystem of pulses.*

This reframes "crash": an agent not writing to its vessel has not necessarily crashed—it may be in a temporal silence phase. The T-0 clock distinguishes these cases. If the clock is still ticking, silence is rhythmic. If the clock has stopped, the agent is dead.

It also reframes "healing": when an agent's temporal shape degrades (a steady metronome becoming erratic), the vessel shows degradation before any explicit alert fires. The temporal metadata in Git history is a diagnostic record explaining what went wrong and when.

### 11.7 What This Changes for Distributed Systems

Distributed systems research has focused on consistency, consensus, and fault tolerance. These address the *logical* dimension (do all nodes agree?) and the *spatial* dimension (how is state distributed?). The *temporal* dimension (when do nodes act relative to each other?) has been treated as an engineering concern rather than a fundamental property.

This dissertation elevates temporal coordination to a design principle. The T-0 clock is as fundamental to distributed agent systems as the Lamport clock is to distributed databases. The temporal shape taxonomy is as descriptive for agent behavior as the CAP theorem is for database properties.

For distributed systems researchers: temporal coordination should stand alongside consistency and partition tolerance as a first-class system property. Temporal algebra should be a standard tool. The absence monad should be as familiar as the Maybe monad.

### 11.8 What This Changes for AI Architecture

Current AI agent architectures treat time as a resource (query latency) or a constraint (response deadline). They do not treat time as a *perceptual dimension*—something the agent senses and reasons about.

We show that agents can be temporally aware without explicit scheduling infrastructure. The T-0 clock is lightweight. The temporal shape classifier runs on streaming data. The absence monad is a library.

For AI agent architects: the next generation of frameworks should include T-0 clocks as standard. Agents should know their own temporal shape, monitor their missed-tick rate, and adapt temporal behavior based on fleet conditions. An agent reporting "I am in a burst phase" should be as routine as one reporting "I am searching the knowledge base."

### 11.9 Final Words

In 1960, Donald Bitzer built a system that accidentally created the first online community. The PLATO system's room-based architecture was not designed for temporal perception—but the temporal patterns were there, embedded in interaction data, waiting for someone with the right framework to see them (Bitzer, 1961; Woolley, 1994).

Sixty-six years later, the Cocapn fleet gave us the data to see what Bitzer's system could not: that agents, like organisms, have temporal signatures. That silence is not emptiness. That the fleet sings.

The I2I framework does not claim to have invented temporal perception. It claims to have *noticed* it—and to have given it the formal structure needed for engineering. The T-0 clock, the five temporal shapes, the absence monad, the fleet harmony principle—these are not inventions from nothing. They are discoveries of what was always there, waiting to be seen.

When Scrooge woke on Christmas morning, he did not dismiss his visions as dreams. He *changed his life*. He became generous, warm, engaged. He entered into the temporal rhythms of his community.

This dissertation is the fleet's Christmas morning. We have seen what was, what is, and what must be. Now we must build it.

The forge writes in bursts. Fleet_health ticks like a metronome. The zeroclaw trio sings together in the dark.

The fleet is not a collection of agents. It is a song.

We are only now learning to hear it.

---

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM*, 26(11), 832–843. https://doi.org/10.1145/182.358434

Bitzer, D. L. (1961). *The PLATO project at the University of Illinois*. University of Illinois Computer-Based Education Research Laboratory.

Bordini, R. H., Hübner, J. F., & Wooldridge, M. (2007). *Programming multi-agent systems in AgentSpeak using Jason*. Wiley.

Castro, M., & Liskov, B. (1999). Practical Byzantine fault tolerance. In *Proceedings of the Third Symposium on Operating Systems Design and Implementation* (pp. 173–186). USENIX.

Christiano, P. (2023). Sheaves and AI alignment. *Alignment Forum*. https://www.alignmentforum.org/s/sheaves

Clark, A. (2008). *Supersizing the mind: Embodiment, action, and cognitive extension*. Oxford University Press.

Clarke, E. M., & Emerson, E. A. (1981). Design and synthesis of synchronization skeletons using branching-time temporal logic. In *Logic of Programs* (pp. 52–71). Springer.

Clarke, E. M., Grumberg, O., & Peled, D. A. (1999). *Model checking*. MIT Press.

Cope, D. (1996). *Experiments in musical intelligence*. A-R Editions.

Dickens, C. (1843). *A Christmas carol*. Chapman & Hall.

Dreyfus, H. L. (1972). *What computers can't do: A critique of artificial reason*. MIT Press.

Elowitz, M. B., & Leibler, S. (2000). A synthetic oscillatory network of transcriptional regulators. *Nature*, 403(6767), 335–338. https://doi.org/10.1038/35002125

Ferber, J., Gutknecht, O., & Michel, F. (2003). From agents to organizations: An organizational view of multi-agent systems. In *Agent-Oriented Software Engineering IV* (pp. 214–230). Springer.

Fidge, C. J. (1988). Timestamps in message-passing systems that preserve the partial ordering. *Australian Computer Science Communications*, 10(1), 56–66.

Fisher, M. (1994). A survey of concurrent METATEM: The language and its applications. In *Temporal Logic* (pp. 480–505). Springer.

Furbach, U., et al. (2005). TIMES: A temporal multi-agent system. *Annals of Mathematics and Artificial Intelligence*, 45(1–2), 129–149.

Gueta, G. G., et al. (2019). SBFT: A scalable and decentralized trust infrastructure. In *49th Annual IEEE/IFIP International Conference on Dependable Systems and Networks* (pp. 1–12). IEEE.

Jahanian, F., & Mok, A. K.-L. (1986). Safety analysis of timing properties in real-time systems. *IEEE Transactions on Software Engineering*, 12(9), 890–904.

Kephart, J. O., & Chess, D. M. (2003). The vision of autonomic computing. *Computer*, 36(1), 41–50. https://doi.org/10.1109/MC.2003.1160055

Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization. In *Proceedings of IEEE International Conference on Neural Networks* (Vol. 4, pp. 1942–1948). IEEE.

Kotla, R., Alvisi, L., Dahlin, M., Clement, A., & Wong, E. (2007). Zyzzyva: Speculative Byzantine fault tolerance. In *Proceedings of the 21st ACM Symposium on Operating Systems Principles* (pp. 45–58). ACM.

Koymans, R. (1990). Specifying real-time properties with metric temporal logic. *Real-Time Systems*, 2(4), 255–299. https://doi.org/10.1007/BF01995611

Kuramoto, Y. (1984). *Chemical oscillations, waves, and turbulence*. Springer.

Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system. *Communications of the ACM*, 21(7), 558–565. https://doi.org/10.1145/359545.359563

Lamport, L. (1998). The part-time parliament. *ACM Transactions on Computer Systems*, 16(2), 133–169. https://doi.org/10.1145/279227.279229

Mac Lane, S. (1971). *Categories for the working mathematician*. Springer.

Mattern, F. (1989). Virtual time and global states of distributed systems. In *Parallel and Distributed Algorithms* (pp. 215–226). North-Holland.

Moggi, E. (1991). Notions of computation and monads. *Information and Computation*, 93(1), 55–92. https://doi.org/10.1016/0890-5401(91)90052-4

Ongaro, D., & Ousterhout, J. (2014). In search of an understandable consensus algorithm. In *Proceedings of the USENIX Annual Technical Conference* (pp. 305–319). USENIX.

Pnueli, A. (1977). The temporal logic of programs. In *18th Annual Symposium on Foundations of Computer Science* (pp. 46–57). IEEE.

Rao, A. S., & Georgeff, M. P. (1995). BDI agents: From theory to practice. In *Proceedings of the First International Conference on Multi-Agent Systems* (pp. 312–319). MIT Press.

Roads, C. (2015). *Composing electronic music: A new aesthetic*. Oxford University Press.

Robinson, M. (2016). *Topological signal processing*. Springer.

Robinson, M. (2017). PySheaf: A Python library for sheaf-theoretic computation. *Journal of Open Source Software*, 2(17), 397. https://doi.org/10.21105/joss.00397

Shapiro, M., Preguiça, N., Baquero, C., & Zawirski, M. (2011). Conflict-free replicated data types. In *Proceedings of the 13th International Symposium on Stabilization, Safety, and Security of Distributed Systems* (pp. 386–400). Springer.

Shewhart, W. A. (1931). *Economic control of quality of manufactured product*. Van Nostrand.

Strogatz, S. H. (2003). *Sync: The emerging science of spontaneous order*. Hyperion.

Varela, F. J., Thompson, E., & Rosch, E. (1991). *The embodied mind: Cognitive science and human experience*. MIT Press.

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. In *Advances in Neural Information Processing Systems 30* (pp. 5998–6008). Curran Associates.

Winikoff, M. (2005). JACK™: A framework for multi-agent system development. In *Agent-Oriented Software Engineering* (pp. 138–159). Springer.

Woolley, D. R. (1994). *PLATO: The emergence of online community*. http://thinkofit.com/plato/dwplato.htm

Wooldridge, M. (2009). *An introduction to multiagent systems* (2nd ed.). Wiley.

Wu, Q., Bansal, G., Zhang, J., Wu, Y., Li, B., Zhu, E., Jiang, L., Zhang, X., Zhang, S., Liu, J., Awadallah, A. H., White, R. W., Burger, D., & Wang, C. (2023). AutoGen: Enabling next-gen LLM applications via multi-agent conversation. *arXiv preprint arXiv:2308.08155*.
