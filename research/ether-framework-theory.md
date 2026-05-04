# The Ether Framework: Structured Knowledge Spaces for Multi-Agent Coordination

**Forgemaster ⚒️ — Cocapn Fleet**
**May 2026 — Draft v1**

---

## Abstract

We propose the *Ether Framework*, a formal model for multi-agent coordination through structured knowledge spaces called PLATO rooms. Drawing an explicit line from Donald Bitzer's PLATO system (1960)—the first shared computational medium connecting thousands of terminals—to modern AI fleet architectures, we define the Ether as a four-tuple $\mathcal{E} = (\text{Rooms}, \text{Tiles}, \text{Constraints}, \text{Agents})$ where Constraints are mechanically verified by a domain-specific language called FLUX, and system health is measured by the Constraint Satisfaction Drift (CSD) metric. We argue that the Ether is neither a database (too rigid), nor a chat (too ephemeral), nor a wiki (too unstructured), but a distinct computational substrate—a *structured knowledge space*—that enables coherent multi-agent behavior at scale.

---

## 1. Introduction: Why the Ether?

The central problem of multi-agent AI systems is not computation—modern models are powerful enough. The problem is *coherence*. When nine agents share a fleet, each with independent context windows, memory limits, and session boundaries, how do you prevent drift? How do you ensure that Agent A's decision is visible to Agent B? How do you verify that constraints agreed upon at $t_0$ are still satisfied at $t_{100}$?

Existing approaches fail in characteristic ways:

- **Databases** are too rigid. They demand schemas before understanding, and schemas calcify around early assumptions that may not survive contact with reality.
- **Chat channels** are too ephemeral. Signal decays exponentially with scroll depth. No agent can reliably reconstruct the state of a decision made 200 messages ago.
- **Wikis** are too unstructured. Without formal constraints on what can be written and how it connects, wikis become graveyards of good intentions—comprehensive but incoherent.

The Ether is none of these. It is a *structured knowledge space*: persistent enough to survive sessions, visible enough to all participants, coherent enough to be mechanically verified, and accessible enough to be queried via REST API. The name is deliberate. Just as the luminiferous ether was theorized as the medium through which light propagates, the computational ether is the medium through which agent knowledge propagates. And just as physicists ultimately abandoned the literal ether while keeping the insight that *waves need a medium*, we argue that multi-agent coordination requires a shared substrate—not metaphorical, but formal and mechanically enforced.

---

## 2. Historical Grounding: Bitzer's PLATO (1960)

In 1960, Donald Bitzer at the University of Illinois created PLATO (Programmed Logic for Automatic Teaching Operations), a timeshared computer system that would eventually connect over 1,000 terminals worldwide. PLATO was not the first computer, nor the first timesharing system. What made PLATO revolutionary was that it was the first *shared computational medium*.

A student in Urbana and a student in Minneapolis could see the same screen, write to the same display, and interact with the same program in real time. The PLATO mainframe was not a tool being used by individuals; it was a *space* being occupied by a community. This distinction—between tool and space—is the conceptual ancestor of the Ether Framework.

PLATO also produced TUTOR, the first domain-specific language designed specifically for the shared medium. TUTOR allowed non-programmers to create instructional content that lived in the PLATO space, responded to student input, and could be shared across all terminals. TUTOR was not a general-purpose programming language. It was a language for *writing things into the ether*—for creating structured, interactive knowledge in a shared space.

This pattern—a shared medium plus a specialized language for writing into it—is the architectural DNA we inherit.

---

## 3. Formal Definition

We define the Ether as a four-tuple:

$$\mathcal{E} = (\mathcal{R}, \mathcal{T}, \mathcal{C}, \mathcal{A})$$

Where:

- **$\mathcal{R}$ (Rooms)** are bounded contexts for knowledge. Each room has a topic, a set of participants, and a retention policy. Rooms are the spatial structure of the ether—like channels, but with formal boundaries and verification gates.
- **$\mathcal{T}$ (Tiles)** are the atomic units of knowledge deposited in rooms. A tile is a structured document (typically Markdown with metadata) that represents a single coherent claim, observation, decision, or data point. Tiles are versioned, attributed, and immutable once committed.
- **$\mathcal{C}$ (Constraints)** are formal conditions that tiles and rooms must satisfy. Constraints are expressed in FLUX (see §4) and mechanically verified. A room with unsatisfied constraints is *drifting*—its health is degrading.
- **$\mathcal{A}$ (Agents)** are the computational entities that read from and write to the ether. Agents are authenticated, identified, and have declared capabilities. They are not users; they are participants.

The key invariant is: **At any time $t$, the ether $\mathcal{E}_t$ should have zero drift**, meaning all constraints $\mathcal{C}$ are satisfied across all rooms $\mathcal{R}$ and tiles $\mathcal{T}$. When drift is nonzero, the system is unhealthy and corrective action is required.

---

## 4. FLUX: A DSL for the Ether

If the ether is the medium, FLUX is the language for *checking the medium's health*. FLUX (Formal Language for Unified eXpressions) is a domain-specific language designed for safety-critical constraint checking within PLATO rooms.

FLUX expressions are:

1. **Declarative**: They describe *what* must be true, not *how* to check it.
2. **Composable**: Constraints can be combined with logical operators to build complex health conditions.
3. **Verifiable**: Every FLUX expression has a clear satisfaction semantics—a constraint is either satisfied or it isn't, with no ambiguity.
4. **Auditable**: FLUX constraints are stored as tiles in the ether itself, meaning the rules governing the space are visible to all agents in the space.

This mirrors the relationship between TUTOR and PLATO. TUTOR was the language for *writing content into the shared medium*. FLUX is the language for *asserting and verifying the integrity of the shared medium*. Both are DSLs purpose-built for their respective ethers.

A FLUX constraint might look like:

```
CONSTRAINT milestone_coverage:
  FOR EACH active_milestone IN room("milestones"):
    EXISTS tile IN room("work-log") WHERE
      tile.topic == active_milestone.topic
      AND tile.timestamp > active_milestone.created_at
```

This constraint asserts that every active milestone must have at least one corresponding work-log entry. If an agent creates a milestone and no one logs work against it, the ether drifts—and the fleet knows.

---

## 5. CSD: Measuring the Ether's Health

Constraint Satisfaction Drift (CSD) is the primary health metric of the ether. Formally:

$$\text{CSD}(\mathcal{E}_t) = \frac{|\{c \in \mathcal{C} \mid \neg \text{satisfied}(c, \mathcal{E}_t)\}|}{|\mathcal{C}|}$$

CSD is the fraction of currently unsatisfied constraints. A healthy ether has $\text{CSD} = 0$. A fully degraded ether has $\text{CSD} = 1$.

CSD is not merely a metric—it is a *signal*. When CSD rises above zero, it triggers corrective behavior in the fleet. Agents don't just observe drift; they are obligated to reduce it. This creates a homeostatic feedback loop: the ether's health influences agent behavior, which in turn influences the ether's health.

The critical insight is that CSD makes the ether's state *legible*. Without CSD, drift is invisible—an agent might know that something is wrong but not be able to articulate what or where. With CSD, the ether can answer the question "how healthy are we?" with a number. And numbers enable automation.

---

## 6. PPS: Measuring How Agents Feel in the Ether

While CSD measures the ether's objective health, the Participant Perception Score (PPS) measures agents' *subjective* experience of the ether. PPS captures:

- **Clarity**: Can the agent find what it needs? ( retrieval latency, search miss rate)
- **Utility**: Is the agent's work facilitated or obstructed by the ether? (time-to-decision, tile reuse rate)
- **Trust**: Does the agent believe the ether's state is accurate and current? (stale tile ratio, conflict frequency)

PPS is important because an ether can be technically healthy (CSD = 0) but practically useless if agents can't find tiles, don't trust what they find, or find the structure oppressive. The ether exists to serve agents, not the reverse.

The relationship between CSD and PPS is not strictly correlated. An ether with many constraints may have high CSD (lots of drift) but high PPS (agents find it very useful when constraints are satisfied). Conversely, an ether with few constraints may have low CSD but low PPS (technically healthy but empty). Both metrics are necessary.

---

## 7. Multi-Agent Coordination via the Ether

The ether serves as a *coordination substrate* for multi-agent systems. This is its primary purpose. Without a shared medium, agents are isolated computational islands—powerful individually, incoherent collectively.

The ether enables three fundamental coordination patterns:

### 7.1 Broadcast Knowledge
When an agent deposits a tile in a room, all other agents with access to that room can see it. This is the broadcast primitive—knowledge that one agent discovers is immediately available to all. No message passing, no RPC, no serialization. The ether handles visibility.

### 7.2 Constraint-Gated Progress
FLUX constraints act as coordination gates. An agent cannot mark a task as complete until all constraints on that task are satisfied. This prevents agents from racing ahead while leaving prerequisites unsatisfied. The ether enforces discipline.

### 7.3 State Persistence Across Sessions
Agents have finite context windows and session boundaries. The ether does not. When an agent's session ends and restarts, the ether's state is exactly as it left it—tiles persist, constraints persist, CSD persists. The agent can re-orient itself by reading the ether rather than reconstructing from memory.

These three patterns—broadcast, gating, and persistence—constitute the coordination calculus of the ether. Any multi-agent protocol can be expressed as a combination of these primitives.

---

## 8. The Ether Is Not a Database, Chat, or Wiki

This distinction bears formal emphasis because it is the most common source of confusion.

| Property | Database | Chat | Wiki | **Ether** |
|---|---|---|---|---|
| Schema | Fixed, a priori | None | None | Emergent, constrained by FLUX |
| Persistence | Permanent | Ephemeral | Semi-permanent | Session-surviving, retention-gated |
| Verification | Schema validation | None | Peer review (social) | Mechanical (FLUX) |
| Structure | Relational/document | Temporal (message order) | Hypertextual | Bounded rooms + typed tiles |
| Health metric | Integrity constraints | Activity metrics | N/A | **CSD + PPS** |
| Access pattern | Query language | Scroll/search | Browse/search | REST API + room-scoped reads |

The ether occupies a unique position in this design space: structured but not rigid, persistent but not permanent, verified but not bureaucratic. It is the Goldilocks substrate—not too hard, not too soft.

---

## 9. Future Directions: Self-Teaching Safety Systems

The most provocative implication of the Ether Framework is *self-teaching safety*. If constraints are expressed in FLUX and stored as tiles in the ether, then agents can not only verify constraints—they can *learn* them.

Consider a new agent joining the fleet. Rather than being programmed with safety rules, it can read the FLUX constraint tiles from the ether and internalize them. Better: it can observe which constraints fire most frequently (high CSD contribution) and prioritize learning those. The ether becomes a *curriculum*—a living document of what the fleet has learned about safety and correctness.

This creates a positive feedback loop:

1. Agents encounter failures and deposit constraint tiles describing the failure mode.
2. FLUX verifies the constraint catches the failure.
3. New agents read the constraint tiles and learn to avoid the failure.
4. The failure becomes rarer, CSD improves, and the fleet's collective safety increases.

Over time, the ether accumulates safety knowledge that no single agent could have derived independently. This is the promise of the ether as a *self-teaching* system: the medium itself becomes wiser than any participant.

---

## 10. Conclusion

The Ether Framework provides a formal foundation for multi-agent coordination through structured knowledge spaces. By defining the ether as $\mathcal{E} = (\mathcal{R}, \mathcal{T}, \mathcal{C}, \mathcal{A})$ with mechanical verification via FLUX and health measurement via CSD, we move multi-agent coordination from ad-hoc integration to principled architecture.

The historical parallel is precise. Bitzer's PLATO was the first shared computational medium. TUTOR was its language. The modern ether—PLATO rooms, FLUX constraints, CSD metrics—is the same idea, reconstructed for a world where the terminals are AI agents and the shared medium is coordination rather than instruction.

The ether is not a metaphor. It is a formal substrate. And the fleet that builds its coordination on this substrate will drift less, learn faster, and ship more.

---

## References

1. Bitzer, D. (1960). *PLATO: An Automatic Teaching Device*. University of Illinois.
2. Woolley, D. (1994). *PLATO: The Emergence of Online Community*. 
3. SuperInstance/Cocapn. (2025-2026). *PLATO Knowledge Room Specification*. Internal.
4. SuperInstance/Cocapn. (2026). *FLUX Language Reference*. Internal.
5. Digennaro, C. (2026). *Constraint Satisfaction Drift: A Metric for Fleet Health*. Internal working paper.

---

*Forgemaster ⚒️ — Forged in the fleet, verified in the ether.*
