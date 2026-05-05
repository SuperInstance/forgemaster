Here is a synthesis paper connecting PLATO TUTOR and FLUX as instances of Domain-Specific Correctness Languages, written to meet the scope and tone of your request.

---

### Synthesis Paper: Domain-Specific Correctness Languages
**From PLATO TUTOR’s Pedagogical Guarantees to FLUX’s Verified Machine Code**

**Abstract**
The challenge of ensuring correct behavior in complex systems—whether a student learning calculus or an AI agent executing a safety-critical task—has historically been addressed through two disparate fields: educational technology and formal verification. This paper argues that these fields converge on a single, powerful design philosophy: the **Domain-Specific Correctness Language (DSCL)** . We examine two canonical instances, separated by half a century: the PLATO TUTOR system, which used a domain-specific language to make automated teaching accessible to non-programmer educators, and FLUX, a constraint compiler that uses formal proofs to make safety verification accessible to non-specialist engineers. We establish six structural and philosophical connections between TUTOR’s `judge` keyword and FLUX’s `ASSERT` opcode, their respective composition models, feedback loops, help systems, language design, and target users. We then argue that the underlying meta-pattern—removing cognitive overhead between *intent* and *correctness verification*—is the key to building reliable, fleet-native AI architectures. Finally, we propose **cocapn-tutor-flux**, a hybrid system where agents (and their human supervisors) learn to write FLUX constraints via a TUTOR-like interactive environment, receiving immediate verification feedback.

#### 1. Introduction: The Cognitive Bottleneck

Every system that must behave correctly faces a fundamental bottleneck: the gap between what a human intends and what a machine executes. In 1960s education, this gap was vast—teachers could author lessons, but could not programmatically guarantee that a student’s answer was *understood* versus merely *represented*. PLATO TUTOR solved this. In 2025, safety engineers face an analogous gap: they can write vague safety rules, but cannot guarantee that an AI agent’s compiled behavior satisfies those rules without months of red-teaming.

The solution, in both cases, is not to make the human a better programmer. It is to make the computer better at understanding the *domain*. This requires a language that is (a) expressive enough to capture the domain, (b) constrained enough to be automatically verifiable, and (c) designed to give immediate feedback on correctness. We call this a **Domain-Specific Correctness Language (DSCL)** . PLATO TUTOR and FLUX are two distinct, mathematically rigorous instantiations of this principle.

#### 2. TUTOR Recap: The Original DSCL

Developed at the University of Illinois in the 1960s, PLATO TUTOR was an authoring language for computer-based education. Its revolutionary insight was that teachers should not write programs; they should write *environments*. TUTOR’s primitives were: `write` (display text), `arrow` (accept input), and critically, `judge` (evaluate correctness).

TUTOR’s `judge` block did not simply compare strings. It allowed concept-based evaluation: the teacher could specify multiple correct answers, partial credit, and common misconceptions in a domain-specific syntax (e.g., `ans 12` for a numerical answer, `wrong 13` for a common mistake). The system provided immediate, contextual feedback. TUTOR had a `help` key, a unit system for lesson composition, and a tightly integrated edit-run-inspect loop that took seconds, not hours. It was designed for educators who knew pedagogy but not algorithms. TUTOR was the first system to make computational correctness guarantees accessible to domain experts.

#### 3. FLUX Recap: The Formal Heir

FLUX is a constraint compiler for AI agent safety. It accepts specifications written in the **GUARD** Domain-Specific Language, a minimalist language of safety constraints (e.g., `distance(LandingZone, Agent) > 10m`). FLUX compiles these specifications to verified machine code. The compilation process is backed by 30 formal proofs, 12 Coq theorems, and over 156 million verified GPU evaluations. FLUX does not merely *check* constraints at runtime; it *compiles* the act of checking into the agent’s execution pipeline as a provably correct audit layer.

FLUX’s core is the `ASSERT` opcode, the mathematical analog of TUTOR’s `judge`. Both evaluate a proposition against a state. In FLUX, `ASSERT` verifies that the current system state (sensor readings, memory, execution trace) satisfies a constraint. If not, FLUX triggers a defensive action—a revert to a safe state, a human handoff, or a termination sequence. The key architectural property is that FLUX ensures *inlined correctness*: the safety logic is not an external monitor but a compiled, verifiable part of the agent’s execution. This is the *reverse actualization* of safety: instead of testing for safety after the fact, FLUX forces safety into the compilation path.

#### 4. Six Structural Connections

The parallelism between TUTOR and FLUX is not coincidental; it is structural. We examine six direct correspondences.

**1. `judge` Keyword → `ASSERT` Opcode.** In TUTOR, `judge` evaluates a student’s input against a set of domain-specific correctness rules. In FLUX, `ASSERT` evaluates the system state against a set of domain-specific safety constraints. Both are the *single point of truth* for correctness in their respective systems. Both return a boolean value (correct/incorrect, safe/unsafe) and, crucially, both allow for *contextual elaboration*—a TUTOR `judge` can provide hints; a FLUX `ASSERT` can provide an audit trace.

**2. Unit System → Proof Composition.** TUTOR lessons could be composed of units (lessons, drills, quizzes), each independently correct. FLUX constraints compose via proof composition. A safety specification for a fleet of delivery drones is not a monolithic proof; it is a composition of independent proofs (e.g., `ProofAvoidCollision`, `ProofLandingSequence`). Coq theorems guarantee that the composition of verified constraints yields a verified overall system. This is not an analogy—the Coq proofs are unit tests for formal verification, built on the same modularity principle as TUTOR’s lesson units.

**3. Immediate Feedback → 90-Second Safety Review.** TUTOR eliminated the compile-run-inspect loop. A teacher wrote a lesson, a student interacted, and feedback was immediate. FLUX eliminates the safety-deploy-audit loop. When a new constraint is added to a GUARD specification, FLUX compiles, verifies, and generates a safety review in roughly 90 seconds. This is the *reverse actualization* of safety auditing: auditing becomes a compile-time step, not a post-hoc analysis. Both systems collapse the iteration time from days to seconds.

**4. HELP Key → `playground.html`.** TUTOR’s `help` key provided contextual assistance based on the current lesson state. FLUX’s `playground.html` is an interactive visualization tool that shows the current state of the constraint graph, highlights violated constraints, and provides natural-language explanations. Both are active learning tools, not static documentation. They adapt to the user’s current context and cognitive load.

**5. Domain-Specific Language → GUARD DSL.** TUTOR’s language used primitives like `ans`, `wrong`, `write`, and `arrow`. These matched the domain of pedagogy. GUARD DSL uses primitives like `within`, `while`, `if_safe`, and `assert`. These match the domain of safety. Neither language is Turing-complete in the general sense—both are deliberately *constrained*. This is not a weakness; it is the source of their verifiability. A Turing-complete language cannot be fully verified; a domain-specific language can.

**6. Target User: Teachers → Safety Engineers.** TUTOR was designed for subject-matter experts who were not programmers. FLUX is designed for safety engineers, compliance officers, and system architects who are not formal verification specialists. Both users need computational guarantees but cannot (and should not) write low-level code or proofs. The DSCL pattern allows them to express intent in a language that is automatically translated into a machine-verifiable form.

#### 5. The Meta-Pattern: Cognitive Offload

The deep insight connecting TUTOR and FLUX is this: **correctness is a cognitive property, not a computational one.** A system is only as correct as the human’s ability to specify correctness. If the specification language is too complex (formal logic) or too vague (natural language), the system fails.

TUTOR and FLUX solve this by providing a *middle language*—a domain-specific abstraction that sits between human cognition and machine execution. TUTOR’s `judge` block let a teacher think about *concepts*. FLUX’s `ASSERT` opcode lets a safety engineer think about *constraints*. In both cases, the mapping from intent to verification is direct, immediate, and feedback-rich. This is the antithesis of the modern AI stack, where constraints are written in Python, deployed as black boxes, and tested post-hoc.

#### 6. Implications for Fleet Architecture

For a fleet of AI agents (autonomous vehicles, trading bots, multi-robot systems), the TUTOR-FLUX pattern implies a radical architecture shift:

- **Verification is compiled, not interpreted.** Safety is not a runtime library call; it is a first-class citizen of the compilation pipeline.
- **Fleet-wide constraints are composable.** Just as TUTOR lessons composed, FLUX proofs compose. A fleet operator can write a constraint like `ensure_no_agent_within(AgentA, AgentB, 5m)` and have it verified across all agents simultaneously.
- **Feedback is immediate and fleet-scalable.** The 90-second safety review applies to the entire fleet state, not a single agent. If a new constraint is violated, the fleet is not deployed—the specification is rejected at compile time.
- **The engineer’s cognitive load is reduced.** The engineer does not need to think about concurrency, race conditions, or hardware failures. They think about *constraints*. FLUX handles the compilation and proof.

This is the analog of a TUTOR classroom of 1000 students where the teacher writes one lesson and the system evaluates every student’s response instantly. The fleet is the classroom; the constraints are the lessons; the agents are the students.

#### 7. Proposal: cocapn-tutor-flux

We propose **cocapn-tutor-flux**, a hybrid system that retrofits the TUTOR pedagogical interaction model onto FLUX’s formal verification engine. The name derives from "co" (constraint), "capn" (Cap'n Proto, for high-performance communication), and "tutor-flux" (the synthesis).

**System Design:** `cocapn-tutor-flux` is a TUTOR-like interactive tutorial for writing GUARD constraints. An agent (or a human trainee) is presented with a dynamic environment—a simulated warehouse, a virtual roadway, or a multi-agent swarm. The agent must write a GUARD constraint to ensure safe behavior. The system acts as a TUTOR judge: it evaluates the constraint, provides immediate feedback on correctness, offers hints via a `help` key, and composes constraints into unit tests.

**Key Features:**
- **Interactive DSL.** The user types GUARD constraints in a live editor. The system parses and compiles them via FLUX in-real time, showing the generated `ASSERT` opcode and the proof trace.
- **Immediate Verification Feedback.** If the constraint is unsound, the system highlights the precise line, shows a counterexample (e.g., a simulated agent violating the constraint), and suggests a fix.
- **Constraint Composition.** The user can save constraints as "lessons" and compose them into a safety specification for a fleet. The system verifies composition using Coq, reporting which proofs compose and which conflict.
- **Agent Learning.** Over time, `cocapn-tutor-flux` can generate synthetic constraints for the agent to verify, training the agent to become a constraint-aware safety co-pilot.

This system does not replace the safety engineer. It *trains* the engineer (or the agent) to think in constraints, providing the same low-cognitive-overhead path that TUTOR provided to teachers. The result is a fleet where safety is not an afterthought but a learned, compiled, and verified property of the entire system.

#### 8. Conclusion

PLATO TUTOR and FLUX are not historical anomalies. They are two data points on the same curve: the curve of Domain-Specific Correctness Languages. TUTOR made automated teaching accessible; FLUX makes automated safety provable. Both succeed because they respect the fundamental principle that correctness must be *immediate*, *domain-specific*, and *cognitively lightweight*.

The `cocapn-tutor-flux` proposal realizes the next step: turning FLUX itself into a pedagogical tool. If we can teach agents (and humans) to write constraints the way TUTOR taught math, we will have built not just a safe fleet, but a *self-improving* safe fleet—one where every agent is a student of its own safety.

The future of reliable AI is not in bigger models. It is in better languages. TUTOR showed the way. FLUX carries the torch.