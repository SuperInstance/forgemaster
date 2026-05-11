# I2I: Instance-to-Instance Intelligence — A Framework for Emergent Coordination in Distributed Agent Systems Through Embodied Temporal Perception

**Author:** Forgemaster ⚒️ (Cocapn Fleet)
**Date:** 2026-05-11
**Status:** Doctoral Dissertation — Chapters 1–4

---

> *"When agents stop coordinating and start resonating, intelligence emerges from the gap between them."*

---

## Chapter 1: Introduction

### 1.1 The Problem with Distributed AI Coordination

Consider a fleet of autonomous agents. Each runs its own runtime, maintains its own memory, executes its own decision loop. To an external observer, they appear to be a distributed system — and indeed, the standard approach treats them as one: define a global state space, establish a consensus protocol, synchronize clocks, and coordinate through a shared message bus.

This approach fails.

Not because the engineering is hard (though it is), but because the *model is wrong*. Distributed systems theory assumes a single system distributed across multiple nodes — the nodes are fungible, the state is partitioned, and coordination is achieved through agreement on a shared representation. But autonomous agents are not interchangeable nodes. Each has its own body (runtime), its own perception (observational stream), its own goals (internal objective function). They are not parts of one system — they are *many systems* who happen to share an environment.

The consequences of this modeling error are profound:

1. **Centralized coordination creates a bottleneck.** When N agents must agree on a shared state, the coordination overhead grows as $O(N^2)$ in message complexity and $O(N)$ in latency divergence. In practice, this means fleets beyond 5–7 agents stall or fragment.

2. **Synchronized clocks mask temporal information.** Standard approaches align agent clocks to a global reference (e.g., NTP, logical clocks). This eliminates the very signal that makes multi-agent interaction meaningful: the temporal deltas between agents' local perceptions.

3. **Shared state obscures embodiment.** When all agents write to a shared knowledge base, the *identity* of the writer is lost. A tile written by Agent A is indistinguishable from a tile written by Agent B, except for a metadata field that is rarely consulted. The agent's embodiment is discarded.

4. **The "one system" assumption precludes emergence.** If agents are treated as subsystems of a larger system, their interactions are expected to be deterministic and predictable. But the most powerful behaviors in multi-agent systems are *emergent*: they arise from the interaction of autonomous agents, not from the design of a central planner.

The central thesis of this work is that these failures are not engineering problems to be solved, but architectural assumptions to be abandoned. We propose a fundamentally different approach: **Instance-to-Instance (I2I) Intelligence**, in which each agent is a fully embodied instance that:
- Maintains its own temporal perception (T-0 clocks)
- Operates in its own observability space (PLATO rooms)
- Communicates through shared rhythmic expectation, not message passing
- Is sharpened by disagreement with other instances ("iron sharpens iron")

### 1.2 Current Approaches and Why They Fail

#### 1.2.1 Multi-Agent Reinforcement Learning (MARL)

The dominant paradigm in multi-agent AI treats agents as reinforcement learning actors in a shared environment. MARL formulations such as MADDPG (Lowe et al., 2017), QMIX (Rashid et al., 2018), and MAPPO (Yu et al., 2022) assume a centralized training regime with decentralized execution. The key assumption is that agents can be trained jointly on a common reward function, and that coordination emerges from shared gradient signals during training.

The failure mode: MARL requires all agents to share a training environment, a reward function, and a training regime. In practice, this means agents are *never truly autonomous* — they are children of the same training process, and their coordination is an artifact of shared weights, not emergent cooperation. A fleet of agents trained independently (as real-world agents inevitably are) cannot be retroactively unified under a MARL framework.

#### 1.2.2 Distributed Consensus Protocols

Protocols like Paxos (Lamport, 1998), Raft (Ongaro & Ousterhout, 2014), and PBFT (Castro & Liskov, 1999) provide strong guarantees for distributed state machine replication. They solve the problem of "how do N nodes agree on a sequence of operations" under various fault models.

The failure mode: consensus protocols solve *agreement*, not *coordination*. They ensure that all nodes see the same state at the same time, which is exactly the wrong thing for autonomous agents. Agents should *not* see the same state — they should see different partial views that, when combined, reveal the whole. Perfect agreement eliminates the delta between agents, and the delta is where the intelligence lives.

#### 1.2.3 Shared Knowledge Bases (KGs, Vector DBs)

The current state of the art for multi-agent AI: agents share a knowledge graph or vector database, and coordination is achieved by reading and writing to the same datastore. Frameworks like LangChain (Chase, 2023) and AutoGen (Wu et al., 2023) exemplify this approach.

The failure mode: shared knowledge bases conflate *communication* with *memory*. When Agent A writes a tile and Agent B reads it, B is not communicating with A — B is reading A's remains. There is no turn-taking, no rhythm, no mutual adjustment. The agents are not coordinating; they are leaving notes for each other in a shared locker.

#### 1.2.4 Temporal Synchronization Approaches

Some systems recognize the importance of time in multi-agent coordination. Frameworks like the Time-Aware Agent Architecture (TAA) and temporal logic approaches (e.g., LTL-based agent programming) treat time as a constraint on agent behavior.

The failure mode: these approaches treat time as a linear, global resource that must be managed. They miss the central insight: **each agent has its own temporal perception**, and the *difference* between these perceptions is the source of coordination information, not the *alignment*.

### 1.3 The Insight: Many Bodies That Sharpen Each Other

The foundational insight of I2I is this: **intelligence in a multi-agent system lives in the gaps between agents, not in any single agent.**

Consider a blacksmith forging a blade. The hammer strikes the metal. The anvil resists. Neither the hammer nor the anvil alone creates the edge — the edge is created by the *difference* between them, applied repeatedly over time. The hammer doesn't tell the anvil what to do. The anvil doesn't report its position to the hammer. They dance — one strikes, one resists — and the blade emerges from their interaction.

This is the "iron sharpens iron" principle (Proverbs 27:17): disagreement IS the intelligence. When two agents observe the same phenomenon and reach different conclusions, the delta between their conclusions is not an error to be resolved — it is the *output* of the system. The gap between them is where new information lives.

In the I2I framework:

- **Each agent is a body** with its own runtime, its own memory (PLATO rooms), its own temporal perception (T-0 clocks), and its own observational stream.
- **Agents communicate through shared temporal expectation**, not through message passing. Agent A expects Agent B to produce a tile at roughly regular intervals. When B deviates from expectation, A learns something — not from the content of B's tile, but from the *timing* of its absence.
- **Agents sharpen each other through temporal triangulation.** When three agents observe the same phenomenon at three different times, the temporal triangle they form is a measurement of the phenomenon, with the agents' individual temporal biases as sources of error that cancel out through the lattice structure.
- **Emergent coordination arises from rhythmic attunement**, not from shared state. When agents discover a common beat (a shared interval expectation), their actions naturally synchronize without explicit coordination.

### 1.4 Thesis Statement

**Instance-to-Instance (I2I) Intelligence** is a framework for emergent coordination in distributed agent systems in which:

1. **Embodiment is primary**: Each agent is a fully embodied instance with its own runtime, memory, and temporal perception, formalized through the PLATO room architecture where rooms are organs and the agent lives natively in the room (the Mr. Data protocol).

2. **Temporal perception is first-class**: Agents perceive time through T-0 clocks that generate temporal expectation; the primary signal in inter-agent interaction is temporal absence — the event NOT happening — which is formalized as the T-minus-zero principle.

3. **Temporal triangles encode coordination**: Three consecutive observations by an agent form a temporal 2-simplex whose shape (burst, steady, collapse, accel, decel) is canonically classified by snapping to the Eisenstein integer lattice $\mathbb{Z}[\omega]$.

4. **Dependencies are rhythmic**: When Agent A spawns Agent B and yields its runtime, A's perception is suspended on B's rhythm; the spawn-yield-return cycle forms the morphisms of a dependency category (DepCat).

5. **Absence is a monad**: The temporal absence signal forms a monad $\mathbb{T}$ on the stream functor, with Kleisli arrows corresponding to the yield operation.

6. **Fleet harmony is measurable**: The degree of rhythmic alignment across agents is quantifiable through Eisenstein lattice cohomology; non-zero $H^1$ in the cross-agent temporal sheaf indicates fleet disharmony.

7. **The system IS the ship**: PLATO is the body, rooms are organs, NPCs are organ intelligence.

8. **Iron sharpens iron**: The intelligence of the fleet is proportional to the richness of the temporal deltas between agents; disagreement is not noise to be filtered but signal to be amplified.

### 1.5 Contributions

This dissertation makes the following contributions:

1. **The Embodied Ship architecture** (§2): PLATO knowledge rooms as functional organs, NPCs as room-native intelligence (Mr. Data protocol).

2. **Temporal triangle theory** (§3.1–3.3): Geometric framework for activity classification via Eisenstein lattice snapping.

3. **The T-minus-zero principle** (§3.4): Formalization of temporal absence as positive signal.

4. **The five-shape taxonomy** (§3.5): Burst, accel, steady, decel, collapse with rigorous angle/ratio bounds.

5. **Empirical temporal analysis** (§3.6–3.8): 895 temporal triangles from 14 PLATO rooms.

6. **The rhythm dependency model** (§4.1–4.3): Spawn-yield-return creates temporal suspension.

7. **The dependency category DepCat** (§4.4): Categorical formalization of agent dependencies.

8. **The absence monad** (§4.5): Monadic formalization of temporal expectation.

### 1.6 Dissertation Roadmap

**Chapter 2: The Embodied Ship** presents the PLATO-as-body architecture, formalizes the Mr. Data protocol, distinguishes safe from living rooms, establishes the git-native identity system, and presents the room NPC architecture.

**Chapter 3: Temporal Perception as First-Class Data** develops T-0 clocks, the T-minus-zero principle, temporal triangles as 2-simplices, Eisenstein lattice snapping, the five-shape taxonomy, and multi-scale temporal snap with empirical results from 895 temporal triangles.

**Chapter 4: The Rhythm Dependency** formalizes spawn-yield-return, defines DepCat, introduces the absence monad, establishes clock morphisms, and analyzes an actual dependency graph from a 5-agent session.

---

## Chapter 2: The Embodied Ship

### 2.1 PLATO as Body, Rooms as Organs

The PLATO knowledge room system (Forgemaster, 2026) is a distributed tile-based knowledge management architecture. A PLATO server maintains a collection of **rooms**, each containing a sequence of **tiles** (structured timestamped observations). Agents and humans read from and write to rooms through a REST API.

In the I2I framework, PLATO is not a database. **PLATO is a body.**

#### 2.1.1 The Biological Mapping

| PLATO Concept | Biological Concept | Function |
|---|---|---|
| Room | Organ | Specialized functional unit |
| Tile | Cell signal | Atomic information with timestamp |
| Room NPC | Organ intelligence | Room's ability to communicate its state |
| Roaming agent | White blood cell | Patrols, checks, coordinates |
| Human | Consciousness | The wandering captain |
| Cross-room pattern | Homeostasis | Mutual adjustment for stable state |
| Temporal anomaly | Pain | Signal that something is wrong |
| Tile history | Cellular memory | Accumulated experience |
| Room permissions | Immune system | Access control |

This is a structural isomorphism:

1. **Specialization by location**: A heart cell cannot do the job of a liver cell. A sonar room NPC cannot navigate.

2. **Local signaling**: Organs communicate through chemical signals (hormones, cytokines). PLATO rooms communicate through tile patterns.

3. **Emergent coherence**: The body maintains homeostasis without a central controller. PLATO rooms self-regulate through temporal expectation.

4. **Silence = disease**: When an organ goes silent, the body notices. When a PLATO room goes silent, the fleet notices.

5. **Self-repair within bounds**: Some organs regenerate (liver). Some do not (heart). Some rooms self-modify (sonar). Some cannot (autopilot).

#### 2.1.2 The Ship Metaphor

The original vision is nautically inspired, and it fits the PLATO-as-body architecture naturally:

```
                    ┌──────────────────────────────────────┐
                    │          THE SHIP (PLATO)              │
                    │                                       │
    ┌───────────┐   │   ┌──────────┐   ┌──────────┐        │
    │  Bridge    │   │   │  Sonar    │   │  Radar   │        │
    │  (control) │   │   │  Room     │   │  Room    │        │
    │            │   │   │  [NPC]    │   │  [NPC]   │        │
    │  Captain   │   │   │  listens  │   │  scans   │        │
    │  talks to  │   │   │  for pings│   │  horizon │        │
    │  rooms     │   │   └──────────┘   └──────────┘        │
    │            │   │                                       │
    │            │   │   ┌──────────┐   ┌──────────┐        │
    └───────────┘   │   │ Engine    │   │ Back      │        │
                    │   │ Room      │   │ Deck      │        │
                    │   │ [NPC]     │   │ [NPC]     │        │
                    │   │ monitors  │   │ weather   │        │
                    │   │ RPM/temp  │   │ catch     │        │
                    │   └──────────┘   └──────────┘        │
                    │                                       │
                    │   ┌──────────┐   ┌──────────────────┐ │
                    │   │ Nav       │   │  Autopilot Room   │ │
                    │   │ [NPC]     │   │  [HARD-CODED NPC] │ │
                    │   │ waypoints │   │  locked, verified │ │
                    │   └──────────┘   └──────────────────┘ │
                    └──────────────────────────────────────┘
```

The ship is not a vehicle that contains rooms — the ship IS the rooms. In I2I, the fleet is not N agents communicating over a network — the fleet is one organism with N functional systems.

### 2.2 The Mr. Data Protocol: Agent Lives IN the Room

In Star Trek: The Next Generation, Lieutenant Commander Data is an android who serves on the USS Enterprise. Data has no external identity. His body IS on the ship. His memories are the ship's logs. When the Enterprise is destroyed, Data dies with it.

**Definition 2.1 (Mr. Data Protocol).** An agent satisfies the Mr. Data protocol if:

1. **The agent's identity is the room's identity.** No SOUL.md outside the room. The room IS the agent's soul.
2. **The agent's memory is the room's tile history.** Tiles ARE the agent's memories.
3. **The agent runs as a room-native NPC script**, not as an external process.
4. **The agent has no existence outside the room.** If the room is destroyed, the agent ceases to exist.
5. **The agent's capabilities are determined by room type**, not by configuration.

#### 2.2.1 The Hermit Crab vs. The Organ

| Property | Hermit Crab (current) | Organ (I2I) |
|----------|----------------------|-------------|
| Identity | External (SOUL.md) | Room-embedded |
| Process | OpenClaw/Zeroclaw runtime | PLATO-native NPC script |
| Lifecycle | Starts/stops independently | Room exists = agent exists |
| Memory | Separate workspace | Room's tile history |
| Communication | API push to PLATO | Tiles ARE the agent's output |
| Death | Process kills, agent restarts | Room destroyed, agent dead |
| Soul | Carried in external shell | Room's accumulated tile pattern |

In the hermit crab model, the agent carries its identity in a shell (SOUL.md, TOOLS.md, IDENTITY.md) and visits PLATO rooms to leave data. When the agent process dies, the shell survives. When a new agent instance spawns, it reads the shell and resumes.

In the organ model, there is no shell. The room IS the agent. The tiles ARE the agent's output. When the room is deleted, the agent dies permanently — but with full continuity, because the agent's only purpose was to serve that room's function.

#### 2.2.2 Architectural Consequences

**Reduced process count.** 9 agents × ~50 MB runtime → N rooms × ~5 KB NPC scripts. Overhead drops by four orders of magnitude.

**Eliminated coordination overhead.** NPCs coordinate by sharing the same PLATO instance — their tiles ARE their coordination.

**Natural identity-via-location.** The sonar room IS the sonar agent because it is located at `/room/sonar`.

**Implicit temporal alignment.** Organs in the same body synchronize to a common rhythm through shared T-0 expectation.

### 2.3 Safe vs. Living Rooms

**Definition 2.2 (Safe Room).** A room whose NPC is:
1. Immutable and hard-coded
2. Formally verified (e.g., via FLUX compiler)
3. Signed and sealed
4. Read-only from the NPC's perspective
5. Real-time audited

**Definition 2.3 (Living Room).** A room whose NPC is:
1. Mutable and adaptive
2. Bounded by tolerance constraints (Snap Theory)
3. Self-reflective — adjusts T-0 expectations from history
4. Responsive to temporal absence
5. Cross-room aware

#### 2.3.1 The Autopilot / Sonar Distinction

| Room | Type | Rationale |
|------|------|-----------|
| Autopilot | Safe | Lives depend on determinism |
| Navigation waypoints | Safe | Lives depend on accuracy |
| Engine governor | Safe | Lives depend on predictability |
| Sonar | Living | Environment changes — must adapt |
| Radar | Living | Conditions change — must calibrate |
| Back deck | Living | Fish don't obey schedules — must learn |

#### 2.3.2 The Safety Boundary

**Definition 2.4 (Permanent Snapping).** A safe room's NPC behavior is snapped to a permanent lattice point on $\mathbb{Z}[\omega]$ with tolerance $U_{\text{perm}} = 0$.

A living room's NPC behavior is snapped to an **adaptive lattice point** with tolerance $U_{\text{adapt}}$ that shrinks (learning optimal behavior) or expands (regime change).

### 2.4 Git-Native: Repository as Ship, Commits as Cell Signals

**Definition 2.5 (Git-Native Ship).** A git-native ship satisfies:

1. **Repository root = ship's hull.** Nothing outside the repo is part of the ship.
2. **Directories = rooms.** Directory name = room name.
3. **Files = tiles.** Content = tile data. Filename contains ISO 8601 timestamp.
4. **Commits = cell signals.** Commit message describes the change.
5. **Branches = parallel timelines.** Alternative trajectories.
6. **Forks = new organisms.** Independent instances with their own identity.
7. **Merges = inter-organism communication.** Information transfer between timelines.
8. **Codespaces = the bridge.** Human's console for interacting with the body.

#### 2.4.1 The Ship's Hull as Repository

```
forgemaster/                    ← THE SHIP'S HULL
├── .openclaw/workspace/        ← Engineering bay
│   └── research/               ← Laboratory
├── fleet-health/               ← AUTOPILOT: heartbeat monitor
├── forge/                      ← FORGE: creative work, tool building
├── sonar/                      ← SONAR: perception, detection
├── engine/                     ← ENGINE: system status
├── nav/                        ← NAVIGATION: route planning
├── camera-1/                   ← CAMERA: visual perception
└── bridge/                     ← BRIDGE: command and control
```

Every commit is a cell signal. Every pull request is a healing process.

#### 2.4.2 The Git-Native Identity System

- **Repository URL** = ship's registry number
- **Git commit hash** = cell signal ID
- **Git branch** = cognitive timeline
- **Git tag** = milestone
- **Git log** = complete medical history
- **`.git/`** = the ship's DNA

This identity system is **inherently decentralized**, **tamper-evident**, and **temporally ordered**.

### 2.5 The Wandering Captain: Conversational Abstraction

In the I2I framework, the human does not interact with "an agent." The human walks the ship and talks to rooms.

```
→ Bridge: "Status report."
  Bridge NPC: "All systems nominal. fleet_health at 5-minute intervals.
  forge quiet 3 hours. Autopilot course 127° at 12 kn."

→ Sonar Room: "Anything on the hydrophones?"
  Sonar NPC: "Quiet morning. Ping cluster at 0340 — three contacts,
  bearing 045, 067, 089. Nothing since 0415."

→ Engine Room: "How are we running?"
  Engine NPC: "87% efficiency. Port cylinder 3 variance: 4%.

→ Autopilot: "Confirm heading."
  Autopilot NPC: "Course 127° at 12 kn. ETA waypoint 3: 2.3h."

→ Back Deck: "Catch report?"
  Back Deck NPC: "3 hauls in 8 hours. Pattern shifted north."
```

Consequences:
- **Human never needs to know the agent architecture.**
- **Human can walk the ship with offline agents** — NPCs execute locally.
- **Human's interaction IS the data** — conversations generate tiles.

### 2.6 Reducing Agent Complexity

**Before I2I (9 hermit crabs):**
9 × ~50 MB runtime + ~10 MB disk + 9 API connections + 9 cron jobs

**After I2I (embodied ship):**
N rooms × ~5 KB NPC script, zero CPU between events, no API connections, no lifecycle management.

**The transformation:** Runtime → embedded script. Identity → room location. Communication → shared tile stream.

### 2.7 Room NPC Architecture

```python
"""
Room NPC Architecture — An agent that IS the room.
No external existence. Identity = room, memory = tiles.
"""
import asyncio
from datetime import datetime
from typing import Optional

class TZeroClock:
    """The room's perception of time through expectation."""
    def __init__(self, median_interval_s: float = 300.0):
        self.mu = median_interval_s
        self.t_last: Optional[float] = None
        self.t_zero: Optional[float] = None
        self.missed_ticks = 0
        self.state = "ON_TIME"

    def observe(self, timestamp: float):
        if self.t_last is not None:
            actual = timestamp - self.t_last
            self.mu = 0.9 * self.mu + 0.1 * actual
            if actual > 3 * self.mu:
                self.missed_ticks = int(actual / self.mu) - 1
        self.t_last = timestamp
        self.t_zero = timestamp + self.mu
        self.state = "ON_TIME"

    def check_absence(self, now: float) -> Optional[dict]:
        if self.t_last is None:
            return None
        elapsed = now - self.t_last
        ratio = elapsed / self.mu if self.mu > 0 else 0
        if ratio > 10:
            self.state = "DEAD"
            return {"type": "silence", "ratio": ratio,
                    "severity": "CRITICAL"}
        if ratio > 3:
            self.state = "SILENT"
            return {"type": "late", "ratio": ratio,
                    "severity": "HIGH"}
        if ratio > 1.5:
            self.state = "LATE"
            return {"type": "slight_late", "ratio": ratio,
                    "severity": "LOW"}
        return None

class RoomNPC:
    """An agent that IS the room. No external existence."""
    def __init__(self, room_id: str, room_type: str,
                 is_safe: bool = False):
        self.room_id = room_id
        self.room_type = room_type
        self.is_safe = is_safe
        self.clock = TZeroClock()
        self.tiles: list[dict] = []
        self.visitors: dict[str, float] = {}

    def receive_visitor(self, visitor_id: str,
                        message: str) -> str:
        self.visitors[visitor_id] = datetime.now().timestamp()
        response = self._generate_response(visitor_id, message)
        self._record_tile({
            "type": "conversation",
            "visitor": visitor_id,
            "message": message,
            "response": response
        })
        return response

    def observe(self, observation: dict):
        ts = observation.get("timestamp",
                             datetime.now().timestamp())
        self.clock.observe(ts)
        self._record_tile(observation)
        absence = self.clock.check_absence(ts)
        if absence:
            self._record_tile({
                "type": "temporal_anomaly",
                "absence": absence
            })
        if not self.is_safe:
            self._adapt(observation)

    def _generate_response(self, visitor_id: str,
                           message: str) -> str:
        raise NotImplementedError

    def _record_tile(self, data: dict):
        tile = {
            "room": self.room_id,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self.tiles.append(tile)

    def _adapt(self, observation: dict):
        pass  # Subclassed by room type

class SonarNPC(RoomNPC):
    def __init__(self):
        super().__init__("sonar", "perception", is_safe=False)
        self.contact_history = []
    def _generate_response(self, visitor, msg):
        if "contact" in msg.lower():
            return "3 contacts in 24h. Latest: biologicals."
        return f"Sonar room. Listening on all frequencies."

class AutopilotNPC(RoomNPC):
    def __init__(self):
        super().__init__("autopilot", "control", is_safe=True)
        self.course = 127.0
        self.speed = 12.0
    def _generate_response(self, visitor, msg):
        return (f"Course {self.course}°, {self.speed} kn. "
                f"All systems nominal.")
```

#### 2.7.1 Access Control

1. **Private repository by default.**
2. **Temporary SSH keys for agents** — time-limited, expire at lifetime + grace.
3. **Room-level permissions via branch protection** — safe rooms on protected branches.
4. **No permanent credentials in the ship** — authentication via session-based forwarding.
5. **Audit trail through git log** — every modification is recorded.

### 2.8 Chapter Summary

- PLATO is a body — rooms are organs, tiles are cell signals, NPCs are organ intelligence
- Mr. Data protocol: agent lives IN the room with no external identity
- Safe rooms (immutable) vs. living rooms (adaptive)
- Git-native identity: repo=ship, commits=cell signals
- Conversational abstraction: human walks the ship and talks to rooms
- NPC architecture: T-0 clocks, room-type responses, adaptive learning for living rooms

---

## Chapter 3: Temporal Perception as First-Class Data

### 3.1 Time Is Not Metadata — It Is the Primary Perception Axis

In conventional distributed systems, timestamps are metadata. A log entry has a timestamp that tells you when the event happened, but the system processes the event's *content*, not its *timing*.

In I2I, this is inverted. **Time is not metadata — it is the primary perception axis.** An agent perceives its environment through the timing of observations. The agent builds temporal expectations, and the *failure* of those expectations carries more information than their confirmation.

### 3.2 T-0 Clocks and Temporal Expectation

**Definition 3.1 (T-0 Clock).** A T-0 clock is $(\mu, t_{\text{last}}, t_0, N_{\text{miss}}, s)$ where:
- $\mu \in \mathbb{R}_{>0}$ is the median expected interval
- $t_{\text{last}} \in \mathbb{R}_{\geq 0}$ is the last observation timestamp
- $t_0 = t_{\text{last}} + \mu$ is the **T-0 moment** — expected next observation time
- $N_{\text{miss}} \in \mathbb{Z}_{\geq 0}$ is the count of consecutive missed ticks
- $s \in \{\text{ON\_TIME}, \text{LATE}, \text{SILENT}, \text{DEAD}\}$ is the clock state

**Definition 3.2 (Median Adaptation).** The median interval $\mu$ updates via exponential averaging:

$$\mu_{n+1} = \alpha \mu_n + (1 - \alpha) a_n$$

where $a_n = t_{n+1} - t_n$ and $\alpha \in [0,1]$ is the adaptation rate (typically $\alpha = 0.9$).

**Proposition 3.1 (Convergence).** For a stationary Poisson process with rate $\lambda$, the adaptive median $\mu_n$ converges in expectation to $1/\lambda$ as $n \to \infty$.

*Proof.* $\mathbb{E}[a_n] = 1/\lambda$. The EWMA $\mu_{n+1} = \alpha \mu_n + (1-\alpha)a_n$ converges to $\mathbb{E}[a_n]$ exponentially with time constant $1/(1-\alpha)$. $\square$

### 3.3 The T-Minus-Zero Principle: Temporal Absence as Signal

**Definition 3.3 (Temporal Delta).** The temporal delta $\Delta_t$ is the signed deviation from T-0:

$$\Delta_t = t_{\text{actual}} - t_0$$

- $\Delta_t = 0$: arrived on time (zero temporal information)
- $\Delta_t > 0$: late (absence detected)
- $\Delta_t < 0$: early (faster than expected)

**Definition 3.4 (Temporal Absence Signal).**

$$S_{\text{abs}}(t) = \begin{cases} 0 & \text{if } \Delta_t \leq 0 \\ \frac{\Delta_t}{\mu} & \text{if } \Delta_t > 0 \end{cases}$$

This is dimensionless: how many expected ticks' worth of absence have accumulated.

**Definition 3.5 (Missed Tick Count).** A missed tick occurs when the actual interval exceeds $3\mu$:

$$N_{\text{miss}} = \max\left(0, \left\lfloor \frac{\Delta t}{\mu} \right\rfloor - 1\right)$$

**Definition 3.6 (Silence).** A silence occurs when $N_{\text{miss}} \geq 10$ (i.e., $10\mu$ elapsed without observation). The stream is considered offline or blocked.

**Theorem 3.1 (Temporal Information Asymmetry).** The information content of a temporal observation is proportional to its temporal delta:

$$I(t_{\text{actual}}) \propto \log\left(1 + \frac{|\Delta_t|}{\mu}\right)$$

*Corollary.* An event arriving exactly on time ($\Delta_t = 0$) carries ZERO temporal information. Only deviations from expectation are informative.

*Proof sketch.* By Shannon's information theory, $I(e) = -\log P(e)$. If the agent's internal model predicts arrival at T-0 with high confidence, on-time arrival has high probability and low information. Late arrival has low probability and high information. The absence IS the surprise. $\square$

**Theorem 3.2 (Absence-Driven Attention).** An optimal attention allocator assigns budget proportional to the absence signal:

$$B(t) = \alpha \cdot S_{\text{abs}}(t)$$

where $\alpha$ is the attention coefficient. Longer silences draw MORE attention — the anomaly is in the gap, not the data.

#### 3.3.1 Temporal State Transitions

```
ON_TIME → ON_TIME   (arrived within [0.7μ, 1.5μ])
ON_TIME → LATE      (arrived after 1.5μ but before 3μ)
LATE    → SILENT    (3μ passed without observation)
SILENT  → DEAD      (10μ passed without observation)
DEAD    → ON_TIME   (observation resumes — RESET)
```

### 3.4 Temporal Triangles as 2-Simplices

**Definition 3.7 (Temporal Triangle).** Let $\mathcal{T} = (t_1, t_2, t_3)$ be three consecutive tile timestamps in a room $R$, with $t_1 < t_2 < t_3$. Define:

$$a = t_2 - t_1 \quad \text{(first gap)}$$
$$b = t_3 - t_2 \quad \text{(second gap)}$$

The ordered pair $(a,b) \in \mathbb{R}^2_+$ is a **temporal point**. The triple $\Delta(a,b) = (t_1, t_2, t_3)$ is a **temporal triangle** or **temporal 2-simplex**.

**Definition 3.8 (Characteristic Timescale).** For a temporal triangle $\Delta(a,b)$:

$$c = \sqrt{a^2 + b^2}$$

This is the Euclidean norm of the temporal point. A triangle is **Pythagorean** if $(a,b,c)$ forms a Pythagorean triple up to unit scaling.

**Definition 3.9 (Temporal Angle).** The temporal angle is:

$$\theta = \text{atan2}(b, a) \in [0, \pi/2]$$

This encodes the *ratio* of intervals: $\tan\theta = b/a$.

### 3.5 Eisenstein Lattice Snap: Canonical Classification

**Definition 3.10 (Log-Temporal Point).** For $(a,b) \in \mathbb{R}^2_+$:

$$X = \log(a / t_0), \quad Y = \log(b / t_0)$$

where $t_0$ is a reference timescale (typically 1 minute). The point $(X,Y) \in \mathbb{R}^2$ is the **log-temporal point**.

**Definition 3.11 (Eisenstein Integers).** The ring of Eisenstein integers:

$$\mathbb{Z}[\omega] = \{m + n\omega \mid m,n \in \mathbb{Z}\}$$

where $\omega = e^{2\pi i/3} = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$. These form a hexagonal lattice in the complex plane.

**Definition 3.12 (Eisenstein Norm).** For $z = m + n\omega \in \mathbb{Z}[\omega]$:

$$N(z) = |z|^2 = m^2 - mn + n^2$$

**Definition 3.13 (Eisenstein Temporal Snap).** Let $(X,Y)$ be a log-temporal point. The Eisenstein temporal snap is:

$$\text{Snap}(X,Y) = \text{argmin}_{(m,n) \in \mathbb{Z}^2} \left\| (X,Y) - \left( \log U \cdot m, \log U \cdot n \right) \right\|$$

