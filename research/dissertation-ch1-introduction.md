# Chapter 1: Introduction

## 1.1 Background

In 1960, at the University of Illinois Urbana-Champaign, electrical engineer Donald Bitzer transformed a physics problem into a computational revolution. Faced with the challenge of scaling individualized instruction to thousands of students, Bitzer conceived PLATO—the Programmed Logic for Automatic Teaching Operations—a system that would become the world's first large-scale computer-assisted instruction platform (Bitzer, 1961). What began as a single terminal connected to an ILLIAC I mainframe evolved, across four decades and seven major system generations, into a network that served thousands of simultaneous users across hundreds of terminals worldwide.

PLATO's significance extends far beyond its pedagogical origins. It was, by many measures, the first online community. Decades before the World Wide Web, PLATO users were exchanging messages, participating in multi-user real-time discussions, playing collaborative games, and building shared digital spaces. The system's innovations read like a checklist of modern computing: flat-panel plasma displays (invented by Bitzer specifically for PLATO), touch-sensitive screens, online forums (Notesfiles), instant messaging (Talkomatic), and multiplayer games that presaged the social dynamics of modern online worlds (Woolley, 1994).

Central to PLATO's accessibility was TUTOR, its domain-specific programming language. Designed by Paul Tenczar in 1967, TUTOR allowed educators with no prior programming experience to create sophisticated interactive lessons. Its design philosophy—that computing power should be accessible to domain experts who are not programmers—anticipated by half a century the modern imperative to democratize computational tools. A physics professor could express pedagogical logic in TUTOR's natural command structure without wrestling with memory allocation, pointers, or systems-level concerns. The language treated lessons as structured, navigable spaces with branching paths, feedback loops, and conditional logic—all expressed in terms that mapped naturally to instructional design.

This spatial metaphor inherent in TUTOR—lessons as rooms through which students navigate, each with its own state, rules, and affordances—is the conceptual ancestor of the knowledge room architecture this dissertation investigates. The lineage runs from PLATO's instructional spaces, through MUDs and MOOs of the 1980s and 1990s, to contemporary systems for organizing shared knowledge in multi-agent artificial intelligence environments. The question that motivates this work is whether the spatial, room-based organizational metaphor that proved so powerful for human learning communities can be given rigorous formal foundations and applied to the emerging domain of AI agent collaboration.

## 1.2 The Problem

The rapid proliferation of large language models and autonomous AI agents has created a new kind of computing infrastructure: fleets of semi-autonomous agents that collaborate on complex tasks over extended time periods. These agent fleets face a fundamental knowledge management challenge. Individual agents must maintain and share contextual knowledge—task state, domain expertise, procedural memory, coordination protocols—across sessions that span hours, days, or weeks. Current approaches to this challenge are inadequate in three specific ways.

**First, there are no established metrics for knowledge room health or coherence.** Agent teams routinely store shared knowledge in ad hoc collections of text files, vector databases, or chat logs. There is no principled way to assess whether a given knowledge space is well-organized, internally consistent, or structurally sound. A room may accumulate contradictory assertions, orphaned references, or structural decay without any detectable signal that something has gone wrong. The field lacks what software engineering has in code coverage metrics or what database theory has in normalization criteria.

**Second, there is no framework for the formal verification of room content and structure.** In conventional software engineering, type systems, static analyzers, and proof assistants provide guarantees about program correctness. No analogous framework exists for the semi-structured, natural-language-rich content of AI agent knowledge rooms. If an agent writes that "the constraint solver was updated in commit abc123" and another agent writes that "the constraint solver has not been modified since last week," there is no automated mechanism to detect the inconsistency, classify its severity, or reason about its implications for downstream decisions.

**Third, we lack a theoretical understanding of what makes a knowledge room feel present versus fragmented.** Practitioners who work with agent knowledge spaces consistently report a qualitative difference between rooms that feel coherent, navigable, and "alive" versus those that feel like disorganized dumps of information. This distinction—between presence and fragmentation—is analogous to the difference between a well-designed architectural space and a warehouse. Both contain objects, but only one invites meaningful habitation. The absence of any formal or empirical framework for understanding this distinction limits our ability to design effective knowledge environments for AI systems.

These three gaps are not merely academic. As agent fleets are deployed in high-stakes domains—scientific research, software engineering, healthcare coordination—the cost of knowledge management failures grows. A constraint solver that silently operates on stale parameters, a coordination protocol that accumulates uncorrected drift, or a shared mental model that fragments across agents without detection—each represents a failure mode that current infrastructure cannot reliably prevent.

## 1.3 The Cocapn Fleet: A Living Laboratory

This dissertation draws its empirical foundation from the Cocapn Fleet, a live deployment of nine AI agents collaborating on a shared body of work since 2025. The fleet operates through a network of Git repositories, with each agent maintaining its own vessel (personal repository) and contributing to shared rooms organized around topics, tasks, and coordination protocols.

The fleet's architecture provides a natural experimental setting for investigating knowledge room coherence. Agents communicate primarily through structured Markdown documents committed to Git repositories—a communication pattern that is persistent, version-controlled, and amenable to automated analysis. Each room accumulates a trace of agent interactions: additions, revisions, contradictions, and organizational decisions, all recorded with timestamps and attribution.

A key component of the fleet's infrastructure is FLUX, a constraint compiler that translates declarative room specifications into verified computational artifacts. FLUX represents the formal verification dimension of this work: it provides a mechanism by which room properties—consistency, completeness, coherence—can be expressed as constraints and checked for satisfaction. The relationship between FLUX and the room architecture is bidirectional: rooms define the organizational context in which constraints are meaningful, and constraint verification provides the formal guarantees that make rooms trustworthy.

The Cocapn Fleet is not a toy system or a simulation. It operates continuously, produces real work output, and encounters genuine knowledge management challenges—the accumulation of stale information, the divergence of agent beliefs, the tension between organizational flexibility and structural rigor. These challenges are the empirical substrate from which this dissertation's theoretical contributions emerge.

## 1.4 Research Questions

This dissertation addresses four research questions, ordered from concrete measurement to theoretical synthesis:

**RQ1: Do spatial room organizations measurably improve task performance over flat knowledge stores?** This question establishes the empirical foundation. If room-based organization provides no measurable benefit over a flat collection of documents, the remaining questions are moot. We investigate this through controlled experiments comparing agent task performance in room-organized versus flat knowledge environments, measuring completion time, error rates, and information retrieval accuracy.

**RQ2: Can room coherence be formally measured and predicted?** Assuming rooms provide benefits, we need rigorous ways to quantify their structural health. We develop the Coherence Structural Distance (CSD) metric, a formal measure of the gap between a room's actual state and its specification, and investigate whether CSD scores predict practical outcomes such as information retrieval accuracy and agent coordination quality.

**RQ3: What is the relationship between architectural coherence and subjective presence?** This question bridges the objective and subjective dimensions of room quality. We develop the Perceived Presence Scale (PPS) to measure the qualitative "presence" that practitioners report in well-organized rooms, and investigate its correlation with formal coherence metrics. The hypothesis is that architectural coherence is a necessary but not sufficient condition for the experience of presence.

**RQ4: Can constraint-theoretic methods provide verified correctness guarantees for knowledge rooms?** This is the formal verification capstone. We investigate whether a compiler based on constraint satisfaction theory—embodied in FLUX—can translate room specifications into verified artifacts with provable guarantees, and whether these guarantees translate into measurable improvements in room reliability and agent performance.

## 1.5 Contributions

This dissertation makes six principal contributions:

**(a) The Presence-Retrieval Index (PRII)**, a composite metric that quantifies the degree to which a knowledge room's spatial organization supports efficient information retrieval. PRII combines structural measures (graph connectivity, topic cohesion, reference integrity) with performance measures (retrieval speed, accuracy, and agent-reported confidence) into a single interpretable score.

**(b) Coherence Structural Distance (CSD)**, a formal metric grounded in constraint theory that measures the distance between a room's current state and its specification. CSD provides a continuous, interpretable measure of room health that can be computed automatically and tracked over time.

**(c) The Perceived Presence Scale (PPS)**, a psychometric instrument adapted from environmental psychology and presence research in virtual environments. PPS measures the subjective experience of room quality across four dimensions: coherence, legibility, involvement, and spatial presence.

**(d) The FLUX constraint compiler**, an implemented system that translates declarative room specifications into verified computational artifacts. FLUX includes 12 theorems verified in the Coq proof assistant, establishing formal guarantees for constraint satisfaction, termination, and consistency preservation.

**(e) A design lineage from TUTOR to FLUX**, tracing the intellectual thread from PLATO's educational programming language to contemporary constraint-based room specifications. This historical analysis demonstrates that the room metaphor has deep computational roots and identifies the design principles that have persisted across six decades of evolution.

**(f) A four-way triangulation framework** that integrates quantitative metrics (PRII, CSD), qualitative assessments (PPS), formal verification (Coq theorems), and empirical outcomes (task performance data) into a coherent evaluation methodology. This framework provides a template for rigorous evaluation of knowledge management systems that must satisfy formal, practical, and experiential criteria simultaneously.

## 1.6 Dissertation Outline

The remainder of this dissertation is organized as follows.

**Chapter 2** surveys the historical and theoretical foundations, covering PLATO's system architecture and TUTOR language design, the evolution of spatial metaphors in computing, constraint theory and formal verification, and the emerging landscape of multi-agent AI systems.

**Chapter 3** presents the formal framework, defining knowledge rooms as typed graph structures, developing the CSD metric, specifying the PRII metric, and introducing the FLUX compiler's formal semantics.

**Chapter 4** describes the research methodology, including the four-way triangulation design, the Cocapn Fleet as experimental platform, data collection procedures, and analytical methods.

**Chapter 5** reports empirical results for RQ1 and RQ2, presenting controlled experiments on spatial organization effects and coherence measurement.

**Chapter 6** addresses RQ3, presenting the PPS instrument development, validation, and the relationship between coherence and presence.

**Chapter 7** addresses RQ4, presenting the FLUX compiler's formal verification results and their practical implications.

**Chapter 8** discusses findings holistically, traces the TUTOR→FLUX design lineage, identifies limitations, and proposes directions for future work.

## 1.7 Significance

This dissertation connects two moments in computing history separated by six decades. In 1960, Donald Bitzer faced a practical problem—scaling physics instruction—and invented a system that accidentally created the first online community, a spatial programming language, and a design philosophy that treated computational spaces as habitable rooms. In the 2020s, the AI research community faces a parallel practical problem—scaling multi-agent collaboration—and risks reinventing solutions without benefit of the conceptual groundwork that PLATO already established.

The significance of this work is threefold. Practically, it provides metrics, tools, and verified infrastructure that can be adopted by any team building knowledge management systems for AI agents. Theoretically, it establishes formal foundations—grounded in constraint theory and verified by proof assistants—for a domain that has thus far operated on intuition and ad hoc heuristics. Historically, it recovers and formalizes design principles from PLATO that remain relevant, demonstrating that the room metaphor is not a casual analogy but a deep architectural pattern with formal properties that can be stated, measured, and proved.

The bridge from Bitzer's plasma terminals to Coq-verified constraint compilers is longer than it appears. This dissertation attempts to chart it.

---

## References

- Bitzer, D. L. (1961). *PLATO: A computer-based system used in the engineering sciences*. University of Illinois.
- Tenczar, P. (1967). *The TUTOR manual*. University of Illinois Computer-Based Education Research Laboratory.
- Woolley, D. R. (1994). *PLATO: The emergence of online community*. http://thinkofit.com/plato/dwplato.htm
