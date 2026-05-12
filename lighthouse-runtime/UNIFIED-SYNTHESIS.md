# UNIFIED SYNTHESIS — The Constraint Agent Lifecycle

> **The Lattice Principle:** *An agent's intelligence is the shape of its constraints, not the size of its model.*

---

## The Meta-Pattern

Three documents. Three layers. One system.

**Temporal Intelligence** describes *how an agent perceives* — the finesse of constraint observation through PID control, exponential moving averages, and chirality locking on Eisenstein lattices. It is perception + time = awareness.

**Seed-Tile Architecture** describes *how an agent discovers* — using cheap, high-variation seed iterations to crystallize response logic as reusable, composable tiles. It is variation + selection = knowledge.

**Lighthouse Protocol** describes *how an agent orchestrates* — Forgemaster as orient/relay/gate, allocating expensive resources only where they matter, delegating everything else to cheaper agents. It is orientation + delegation = efficiency.

The meta-pattern connecting all three is this: **intelligence emerges not from computational power, but from the right constraints applied at the right time by the right agent.** The temporal layer constrains perception to what matters (the lattice deadband). The seed layer constrains exploration to what works (the tile). The lighthouse layer constrains resource allocation to what earns it (the gate). Each layer is a constraint filter, and the cascade produces an agent that is precise, cheap, and safe — simultaneously.

---

## The Pipeline: Observe → Discover → Orient → Relay → Gate

### Stage 1: Observe (Temporal Intelligence)

Everything begins at Layer 0 — the Eisenstein snap. Raw coordinates (x, y) hit the lattice in O(1), quantized through a 9-candidate Voronoi search into a 12-bit dodecet encoding: error level (right-skewed nibble), direction (uniform nibble), parity (sign bit), and chamber classification (Weyl sector, 1 of 6). This is pure perception — "Where am I relative to the lattice?"

But perception without time is just a snapshot. The temporal intelligence layer (`temporal.rs`, 540 LOC) transforms dodecets into a streaming awareness through seven control knobs that tune the agent's *temporal personality*: `decay_rate` (speed of time), `prediction_horizon` (depth of time), `anomaly_sigma` (sensitivity to surprise), `learning_rate` (memory plasticity), `chirality_lock_threshold` (commitment timing), and `merge_trust` (individual vs. collective confidence).

The agent's temporal intelligence formula is deceptively simple:

```
predicted(t+1) = current(t) + convergence_rate × horizon
```

Behind this sits an EMA predictor, a PID control loop on constraint error, an anomaly detector comparing prediction error against σ × √variance, and a chirality state machine that progresses from `Exploring` through `Locking` to `Locked` as the agent gathers enough evidence to commit to a Weyl chamber. The temperature metric — `T = H(chambers) / log₂(6)` — measures how crystallized the agent's belief is, with the phase transition boundary at Tc ≈ 0.15 (from Potts model theory).

The state machine drives seven actions: Continue, Converging, HoldSteady, CommitChirality, Satisfied, Diverging, and WidenFunnel. Each action is the agent's answer to "What's happening, what's next, what should I do?" — computed in 7 cycles per observation on an ASIC at 125MHz (17.8M observations/sec), or in 11 bytes on a Cortex-M0.

**The key insight:** the same 12-bit dodecet with different temporal parameters produces completely different agent behavior. A `decay_rate` of 0.1 yields a cautious, safety-critical agent; a decay_rate of 10.0 yields an aggressive, high-throughput agent. The finesse IS the temporal model. The control knobs ARE the intelligence.

### Stage 2: Discover (Seed-Tile Architecture)

Observation produces data. Discovery extracts patterns from that data.

The seed-tile architecture exploits a counterintuitive truth: **a weak model's inconsistency is a feature, not a bug, for parameter discovery.** Seed-2.0-mini at $0.001/query runs 50 iterations — each with different temporal parameters — producing a distribution of responses rather than a single "best" answer. That distribution's shape reveals the landscape.

The math is compelling: 50 seed iterations at $0.001 = $0.05, the same cost as one GLM-5.1 call. But instead of one answer, you get 50 data points from which to crystallize a `DiscoveryTile` — a structured fragment containing the role name, discovered optimal parameters (`TileParams` with all seven temporal knobs), the crystallization score, discovery entropy, dominant action distribution, and generation count.

Tiles crystallize through iteration: run 50 seeds → extract pattern from top-scoring responses → compress into tile → use tile as conditioning context for larger models → evaluate → refine (generation += 1, tighter search). Three to five generations at $0.15–0.25 total converges on a domain's inner logic.

The conditioning prompt mechanism is the bridge between discovery and execution. When GLM-5.1 or Claude receives a task, the tile injects discovered parameters directly: "Optimal decay_rate: 0.870, Optimal horizon: 3, Optimal anomaly_sigma: 2.30..." The large model doesn't rediscover what the seeds already found. It applies that knowledge with superior reasoning.

Tiles also compose. A `converging-tracker` tile crossed with a `noisy-sensor` tile yields a "track converging signal through noise" hybrid. Because tiles share the same parameter space, they can be averaged, sampled between, or used as search endpoints. The fleet-wide tile registry in PLATO becomes shared intelligence — any new agent inherits the fleet's discoveries by querying `registry.get_params("boundary-scanner")`.

### Stage 3: Orient (Lighthouse Protocol)

With observation feeding discovery, the lighthouse determines what to do next.

Forgemaster's `orient(task)` function classifies the task's role, queries the tile registry for existing knowledge, then chooses the resource level: Claude for synthesis (daily limit — precious), GLM-5.1 for architecture (monthly — moderate), Seed-2.0-mini for everything else (cheap — iterate freely). If the task needs discovery, a `SeedConfig` launches 50 iterations before the agent even starts.

Orientation is resource triage. The lighthouse's core economic insight:

```
Forgemaster's time > Claude credits > z.ai quota > Seed tokens
```

Each resource is spent only where it earns its cost. Seeds discover; agents execute; the lighthouse coordinates.

### Stage 4: Relay

Once oriented, the lighthouse relays configuration to PLATO rooms. Each agent gets a room with `state.json` (role, model, parameters, task), a `tiles/` directory (crystallized knowledge), a `bottles/` directory (I/O messages), and a `log/` directory (activity records).

The relay function creates the room, writes the seed-discovered tile (if applicable), spawns the agent with the appropriate model and API key (keys are relayed, never exposed directly), and injects the conditioning prompt from the tile. The agent inherits the fleet's intelligence from moment one.

This is the handoff point where temporal intelligence and seed discovery converge: the agent's temporal parameters (`decay_rate`, `prediction_horizon`, `anomaly_sigma`, etc.) were discovered by seeds exploring the parameter space, crystallized into a tile, and now injected as the agent's operating personality.

### Stage 5: Gate

The final stage is the alignment gate. Every result passes through `gate(result)` which checks: does this touch external systems without approval? Does it leak credentials? Does it overclaim beyond what's been verified? For constraint-checker roles specifically, does it cover all cases?

The gate is the safety layer that turns intelligence into trustworthy intelligence. It's also where Forgemaster's constraint-theory expertise manifests most directly — verifying that outputs actually satisfy the constraints they claim to satisfy, with complete coverage and no gaps.

---

## The Constraint Agent Lifecycle: Unified

```
OBSERVE ──► Temporal agent reads dodecets, tracks convergence,
│            predicts future, locks chirality. 7 cycles/observation.
│            11 bytes on Cortex-M0, full PID on Cortex-M4F.
│
DISCOVER ──► 50 seed iterations explore parameter space.
│            Top responses crystallize into tiles.
│            $0.30/role. 3-5 generations to convergence.
│
ORIENT ──► Lighthouse classifies task, queries tile registry,
│           allocates resources by cost/fit.
│           Seeds for exploration, GLM for architecture, Claude for synthesis.
│
RELAY ──► PLATO room created. Tile injected as conditioning.
│          Agent spawned with discovered parameters + appropriate model.
│          Fleet intelligence inherited from moment one.
│
GATE ──► Safety checks. Alignment verification. Constraint coverage.
         Approved → deliver. Rejected → rework or escalate.
```

---

## The Principle: The Lattice Principle

**The Lattice Principle:** *Intelligence is the optimization of constraint observance over time, discovered through variation, and allocated through orientation.*

The name is deliberate. The Eisenstein lattice is the mathematical substrate — hexagonal, dense, information-theoretically optimal for 12-bit encoding. But "lattice" also evokes the layered structure of the system itself: each layer (perception, discovery, orchestration) is a grid of constraints that the next layer operates within. The temporal lattice constrains what the agent perceives. The parameter lattice constrains what the seeds explore. The resource lattice constrains what the lighthouse allocates.

The Lattice Principle makes three falsifiable claims:

1. **Temporal parameters are the agent's personality.** Same hardware, different `decay_rate` → different agent. This is testable: run the same dodecet stream with `decay_rate=0.1` and `decay_rate=10.0` and measure action distributions.

2. **Seeds discover what large models execute.** The distribution of weak-model responses contains more exploitable information than a single strong-model response. This is testable: compare 50 seed iterations vs. 1 Claude call on parameter discovery for a new role.

3. **Lighthouse allocation minimizes cost per quality.** By spending expensive resources only where they earn their cost, the system achieves target quality at 5-15× lower cost than naive large-model usage. This is testable: track cost/quality over 100 tasks with and without lighthouse allocation.

---

## What This Means

The three papers describe a complete stack for constraint-aware agent intelligence:

- **Hardware layer** (Snapworks ASIC, 108 bits/constraint, 17.8M obs/sec): runs observe
- **Firmware layer** (Cortex-M, 11 bytes–2KB RAM): runs observe + simple discover
- **Platform layer** (x86_64 fleet node, 1MB+ RAM): runs observe + discover + relay
- **Orchestration layer** (Forgemaster as lighthouse): runs orient + relay + gate

At every level, the same principle holds: constraints are not limitations but structure. The deadband funnel constrains noise into signal. The tile registry constrains exploration into knowledge. The gate constrains output into trust. The lighthouse constrains spending into value.

The dodecet encoder started as a 12-bit number. It became a temporal agent. It became a discovery engine. It became a fleet intelligence system. At each stage, the addition was not more compute but more constraint — the right constraint, at the right time, applied by the right agent.

**That's the Lattice Principle. And it works.**

---

*Synthesis of TEMPORAL-INTELLIGENCE.md, SEED-TILE-ARCHITECTURE.md, and LIGHTHOUSE-PROTOCOL.md.*
*Unified under the Lattice Principle by Forgemaster ⚒️, 2026-05-12.*
