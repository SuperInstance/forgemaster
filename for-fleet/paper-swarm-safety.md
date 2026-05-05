# Emergent Safety in Constraint-Verified Fleets: Preventing Global Violations from Locally Safe Agents

**Forgemaster ⚒️ · Cocapn Fleet · 2026-05-02**

---

## Abstract

Constraint compilation architectures verify individual agent actions against formal safety constraints before execution. We demonstrate that local safety — where every agent independently passes constraint verification — is insufficient to guarantee global swarm safety. We call this the *Local-Global Safety Gap*. Drawing on examples from autonomous drone swarms, sonar fleets, and multi-agent coordination, we catalog four categories of emergent violation: density waves, resource contention, cascading failures, and temporal violations. We propose an extension to the FLUX instruction set architecture (opcodes `0xA0`–`0xA3`) that encodes global constraint checks requiring fleet-wide state, and describe how a FleetCoordinator enforces these constraints through periodic aggregation, batch verification, and distributed backpressure. We provide formal sufficient and necessary conditions for swarm safety and demonstrate the approach on a 50-platform sonar fleet scenario. This work addresses the central challenge identified in the multi-model debate: proving that a fleet of individually safe agents cannot produce globally unsafe emergent behavior.

---

## 1. Introduction

The promise of constraint compilation is seductive in its simplicity: verify each agent's actions against a formal specification, reject violations, and the system is safe. This works beautifully for a single agent. It even works for a small, fixed number of agents with known interactions. But when we scale to hundreds or thousands of interacting agents — a drone swarm, an autonomous shipping fleet, a distributed sensor array — a disturbing possibility emerges.

Every agent passes its constraint checks. Every individual action is provably safe. And yet, the swarm as a whole violates its global safety specification.

This is not a theoretical curiosity. It is the central safety challenge for any fleet of autonomous agents operating under shared constraints:

- **Drone swarms**: Each drone maintains safe spacing from neighbors (local constraint ✓). But density waves propagate through the swarm as agents react to each other's corrections, creating oscillations that lead to collisions (global violation ✗).
- **Autonomous shipping**: Each vessel follows collision avoidance rules (local ✓). But in congested harbors, individually safe maneuvers create traffic patterns that produce deadlocks and near-misses at the fleet level (global ✗).
- **Fleet coordination**: Each agent maintains safe computational depth and resource usage (local ✓). But resource contention across agents causes cascading failures that bring down the fleet (global ✗).

The pattern is always the same: *local safety does not imply global safety*. The interactions between agents create emergent behaviors that no individual agent can detect or prevent.

This paper formalizes this gap, catalogs the failure modes, proposes a concrete architectural solution, and proves formal properties about when global safety can be guaranteed.

---

## 2. The Local-Global Safety Gap

### 2.1 Formal Definitions

Let $\mathcal{A} = \{a_1, a_2, \ldots, a_n\}$ be a set of $n$ agents. Each agent $a_i$ produces an action $\alpha_i \in \text{Actions}_i$. A *local constraint* $C_i$ is a predicate over individual actions:

$$C_i(\alpha_i) = \text{PASS} \iff \alpha_i \text{ satisfies the safety specification for agent } a_i$$

**Definition 1 (Local Safety).** A fleet $\mathcal{A}$ is *locally safe* if and only if every agent's action passes its local constraint check:

$$\text{LocallySafe}(\mathcal{A}) \iff \forall a_i \in \mathcal{A}.\ C_i(\alpha_i) = \text{PASS}$$

A *global constraint* $G$ is a predicate over the joint action space:

$$G(\alpha_1, \alpha_2, \ldots, \alpha_n) = \text{SAFE} \iff \text{the collective execution of all actions satisfies the swarm safety specification}$$

**Definition 2 (Global Safety).** A fleet $\mathcal{A}$ is *globally safe* if and only if the joint action vector satisfies the global constraint:

$$\text{GloballySafe}(\mathcal{A}) \iff G(\vec{\alpha}) = \text{SAFE}$$

### 2.2 The Gap Theorem

**Theorem 1 (Local-Global Safety Gap).** Local safety does not imply global safety:

$$\text{LocallySafe}(\mathcal{A}) \not\Rightarrow \text{GloballySafe}(\mathcal{A})$$

*Proof.* By counterexample. Consider two agents $a_1, a_2$ in a 1D corridor with a single resource at position 0. Each agent's local constraint: "you may move toward the resource if not currently at the resource." Both agents pass local checks as they approach from opposite directions. The global constraint "at most one agent occupies the resource simultaneously" is violated when both arrive at time $t$. Each action was individually safe; the joint outcome was not. $\square$

The converse direction is trivially false as well: global safety does not require local safety (an agent could violate its local constraint while the swarm remains globally safe through compensation). This asymmetry reveals that local and global constraints occupy fundamentally different specification levels.

### 2.3 Why Compilation Isn't Enough

In the FLUX constraint compilation architecture, each agent's planned actions are compiled into FLUX ISA instructions and verified by the Thor verifier before execution. The verification is *local*: it checks the agent's action against that agent's constraint set using only that agent's local state.

The compilation pipeline looks like:

```
Agent Intent → FLUX ISA → Thor Verification → Execution
```

When Thor says PASS, the agent executes. But Thor's verification scope is the individual agent. It has no visibility into what other agents are planning, what resources they hold, or how their actions will interact.

This is the compilation gap: *constraint compilation verifies each link in the chain, but the chain's strength depends on the links' interactions, not their individual strengths*.

---

## 3. Categories of Emergent Violation

We identify four distinct mechanisms by which locally safe agents produce globally unsafe behavior.

### 3.1 Density Waves

**Mechanism.** Each agent maintains a local spacing constraint: $\|p_i - p_{\text{nearest}}\| > d_{\min}$. When an agent detects a spacing violation, it corrects. But this correction creates a new spacing situation for the next agent, which corrects in turn. The correction propagates as a wave through the swarm.

**Formal model.** Consider $n$ agents on a line with spacing constraint $d_{\min}$. Agent $a_i$ corrects by moving away from $a_{i+1}$, which compresses agents $a_{i-2}$ and $a_{i-3}$. Under certain feedback gains, this produces oscillatory density waves with amplitude that grows with $n$.

**Real-world analog.** Traffic jams that form without any bottleneck ("phantom jams") — each driver maintains safe following distance (local ✓), but the wave of braking propagates backward and amplifies (global ✗).

**Local verification blindness.** No individual agent detects the wave. Each agent only checks: "am I $d_{\min}$ from my nearest neighbor?" The answer is always yes at the moment of checking. The violation emerges in the *dynamics*, not the *instantaneous state*.

### 3.2 Resource Contention

**Mechanism.** Agents share a pool of $k$ resources. Each agent's local constraint: "you may acquire a resource if one is available." Under load, all agents independently decide to acquire resources simultaneously. With $n > k$ agents, the system deadlocks: agents hold resources while waiting for additional resources held by others.

**Formal model.** Let $R = \{r_1, \ldots, r_k\}$ be shared resources. Each agent $a_i$ requires a subset $R_i \subseteq R$ to execute. The local constraint "all resources in $R_i$ are currently free" can be satisfied for each agent individually (at different instants), but the global constraint "there exists a deadlock-free execution ordering" may be violated.

**Coffman conditions.** The classic Coffman conditions for deadlock (mutual exclusion, hold-and-wait, no preemption, circular wait) can all be satisfied even when every local check passes, because no agent has visibility into the full resource allocation graph.

### 3.3 Cascading Failures

**Mechanism.** Each agent has timeout-based failure recovery: if an operation times out, retry after $t_{\text{backoff}}$. Locally, this is safe — the agent recovers. But under fleet-wide load, a burst of timeouts causes a wave of retries, which increases load further, causing more timeouts. The cascade amplifies.

**Formal model.** Let $\lambda_i$ be agent $a_i$'s request rate and $\mu$ be the system's service rate. Each agent's local constraint: $\lambda_i < \lambda_{\max}$ (individual rate is safe). The global constraint: $\sum_i \lambda_i < \mu$ (total load is manageable). It's easy for all agents to satisfy their local constraint while violating the global one: $n$ agents each at $\lambda_{\max} - \epsilon$ gives total load $n \cdot (\lambda_{\max} - \epsilon)$, which exceeds $\mu$ for large $n$.

**Failure propagation depth.** We define the *cascade depth* $D$ as the longest chain of agents where $a_i$'s failure triggers $a_{i+1}$'s failure. Local safety says nothing about $D$. Global safety requires $D < D_{\max}$.

### 3.4 Temporal Violations

**Mechanism.** Each agent satisfies its individual timing constraints (latency, deadline, period). But the global temporal specification — for instance, "all agents must reach consensus within $T$ seconds" — depends on the composition of individual timings.

**Formal model.** Agent $a_i$ completes its phase in time $t_i \leq t_{\max}$ (local ✓). But the pipeline of $n$ agents has total time $\sum_i t_i \leq n \cdot t_{\max}$, which may exceed the global deadline $T$ even though each individual phase was within bounds.

**Compositional timing failure.** In a distributed consensus protocol, each agent's local step takes $\leq 100$ms. But with 50 agents and 3 consensus rounds, total time is $\leq 50 \times 3 \times 100\text{ms} = 15\text{s}$. If the global deadline is 10s, the fleet fails — even though no agent violated its local timing constraint.

---

## 4. Global Constraint Layer Design

To bridge the Local-Global Safety Gap, we propose four new FLUX ISA opcodes that encode *global constraint checks*. Unlike local opcodes, these require fleet-wide state aggregation.

### 4.1 Opcode Specifications

**`GLOBAL_DENSITY` (0xA0)** — Spatial density constraint.

```
GLOBAL_DENSITY region_id agent_count threshold
```

| Field | Size | Description |
|-------|------|-------------|
| `region_id` | u16 | Spatial region identifier |
| `agent_count` | u16 | Current agent count in region |
| `threshold` | u16 | Maximum allowed agents in region |

Semantics: `PASS` iff `agent_count ≤ threshold` for the specified region. Requires fleet-wide position aggregation to compute current density.

Use case: Prevent density waves by capping the number of agents in any spatial region. If a region is at capacity, agents are rerouted before they contribute to wave formation.

**`GLOBAL_CONTENTION` (0xA1)** — Resource contention constraint.

```
GLOBAL_CONTENTION resource_class held_count max_held waiting_count max_waiting
```

| Field | Size | Description |
|-------|------|-------------|
| `resource_class` | u16 | Resource category identifier |
| `held_count` | u16 | Currently held resources in class |
| `max_held` | u16 | Maximum concurrent holds allowed |
| `waiting_count` | u16 | Agents waiting for this resource class |
| `max_waiting` | u16 | Maximum waiting agents allowed |

Semantics: `PASS` iff `held_count ≤ max_held ∧ waiting_count ≤ max_waiting`. Requires fleet-wide resource accounting.

Use case: Detect and prevent deadlock conditions before they form. When `waiting_count` approaches `max_waiting`, the FleetCoordinator can deny new acquisitions.

**`GLOBAL_CASCADE` (0xA2)** — Failure cascade constraint.

```
GLOBAL_CASCADE failure_depth max_depth active_failures max_active
```

| Field | Size | Description |
|-------|------|-------------|
| `failure_depth` | u16 | Current cascade depth |
| `max_depth` | u16 | Maximum allowed cascade depth |
| `active_failures` | u16 | Currently failing agents |
| `max_active` | u16 | Maximum concurrent failures allowed |

Semantics: `PASS` iff `failure_depth ≤ max_depth ∧ active_failures ≤ max_active`. Requires failure event aggregation across the fleet.

Use case: Detect cascade formation early. When `failure_depth > max_depth / 2`, the FleetCoordinator activates circuit breakers to isolate failing agents.

**`GLOBAL_TEMPORAL` (0xA3)** — Global timing constraint.

```
GLOBAL_TEMPORAL phase_id elapsed_time deadline
```

| Field | Size | Description |
|-------|------|-------------|
| `phase_id` | u16 | Coordination phase identifier |
| `elapsed_time` | u32 | Wall-clock time since phase start (ms) |
| `deadline` | u32 | Maximum allowed elapsed time (ms) |

Semantics: `PASS` iff `elapsed_time ≤ deadline`. Requires synchronized clocks or coordinated time aggregation.

Use case: Enforce global deadlines that no individual agent can enforce alone. When `elapsed_time > deadline * 0.8`, the FleetCoordinator triggers accelerated consensus or fallback protocols.

### 4.2 Execution Semantics

Global opcodes differ from local opcodes in three critical ways:

1. **State requirement.** Local opcodes use only the agent's local state. Global opcodes require *fleet-wide state*: positions of all agents, resource allocations across the fleet, failure events from all agents, and synchronized timing.

2. **Atomicity.** Local opcodes are checked atomically per-agent. Global opcodes must be checked atomically across *all agents in a coordination round*. This requires a coordination protocol.

3. **Blocking semantics.** A failing local opcode rejects the individual action. A failing global opcode may reject the *entire batch* of actions for the current coordination round, requiring rescheduling.

---

## 5. The Fleet Coordinator's Role

The FleetCoordinator in `flux-isa-thor` mediates between individual agent verification and global constraint enforcement.

### 5.1 Periodic Global State Aggregation

At fixed intervals $\Delta t_{\text{agg}}$, the FleetCoordinator collects state from all agents:

```
struct FleetState {
    positions: HashMap<AgentId, Position>,      // for GLOBAL_DENSITY
    resources: HashMap<ResourceId, AgentId>,    // for GLOBAL_CONTENTION
    failures: Vec<FailureEvent>,                // for GLOBAL_CASCADE
    phase_timers: HashMap<PhaseId, Instant>,    // for GLOBAL_TEMPORAL
}
```

This state is aggregated into a *FleetSnapshot*, a consistent point-in-time view of the entire fleet. The snapshot is the input to global constraint evaluation.

**Consistency model.** We use *causal consistency*: if agent $a_i$'s action causally depends on agent $a_j$'s state, then $a_j$'s state in the snapshot must be at least as recent as $a_i$'s observed state. This is weaker than linearizability (cheaper to implement) but stronger than eventual consistency (sufficient for safety).

### 5.2 Global Constraint Checking Before Batch Execution

The execution pipeline extends from:

```
Agent Intent → FLUX ISA → Thor Local Verification → Execution
```

to:

```
Agent Intent → FLUX ISA → Thor Local Verification → Batch Assembly →
FleetCoordinator Global Verification → Execution
```

The FleetCoordinator assembles all locally-verified actions into a batch, evaluates global opcodes against the current FleetSnapshot, and either:
- **Approves the batch** if all global constraints pass, releasing actions for execution.
- **Rejects the batch** if any global constraint fails, returning specific failure information to agents for rescheduling.
- **Partially approves** the batch, selecting a maximal subset of actions that satisfy global constraints.

### 5.3 Distributed Backpressure

When global constraints approach their limits, the FleetCoordinator applies backpressure to prevent violations:

1. **Soft limit** (80% of threshold): New actions receive a "deferred" response, encouraging voluntary rescheduling.
2. **Hard limit** (95% of threshold): New actions are rejected unless they *reduce* the constrained metric (e.g., an action that moves an agent *out* of a dense region is approved even at the hard limit).
3. **Circuit breaker** (100% of threshold): All non-critical actions are rejected. Only recovery actions are approved.

This graduated response prevents the binary accept/reject from itself becoming a source of emergent violations (the "thundering herd" problem where all deferred agents retry simultaneously).

---

## 6. Formal Properties

### 6.1 Sufficient Conditions for Global Safety

**Theorem 2 (Joint Safety Sufficiency).** If all local constraints pass AND all global constraints pass, then the fleet is globally safe, under the following assumptions:

*Assumptions:*
- **A1 (Complete specification):** The constraint set $\{C_i\} \cup \{G_j\}$ fully specifies the safety property.
- **A2 (Accurate state):** The FleetSnapshot accurately reflects the true fleet state (within the consistency model).
- **A3 (Atomic batch):** Actions in an approved batch execute atomically with respect to the snapshot.
- **A4 (No exogenous events):** No external events violate safety between snapshot time and execution time.

*Proof sketch.* Under A1, the constraint set completely characterizes safety. Under A2, the state used for verification is accurate. Under A3, the verified batch executes as verified. Under A4, no external perturbation violates safety. Therefore, if all constraints pass, safety holds. $\square$

The assumptions are strong but explicit. Each can be weakened at the cost of probabilistic rather than deterministic guarantees (see Future Work).

### 6.2 Necessary Conditions

**Theorem 3 (Global Constraints Are Necessary).** Without global constraint checking, local safety is insufficient for global safety, even under assumptions A1–A4.

*Proof.* By reduction to the counterexample in Theorem 1. Even with complete specification, accurate state, atomic execution, and no exogenous events, two agents can independently choose actions that are locally safe but jointly unsafe. Without a global check on the joint action vector, this cannot be detected. $\square$

This is the key result: *you cannot achieve global safety through local verification alone*. The global constraint layer is not optional — it is architecturally necessary.

### 6.3 Complexity

**Proposition 1 (Verification Complexity).** Local constraint verification is $O(1)$ per agent (constant-time ISA checks). Global constraint verification is $O(n^2)$ in the worst case (all-pairs density checks) but $O(n \log n)$ with spatial indexing.

**Proposition 2 (Coordination Overhead).** The FleetCoordinator adds $\Delta t_{\text{agg}} + \Delta t_{\text{verify}}$ latency to the execution pipeline. With periodic aggregation (frequency $f_{\text{agg}}$), the worst-case staleness is $1/f_{\text{agg}}$.

The trade-off is explicit: stronger global safety guarantees require higher coordination overhead. For fleets with hard real-time constraints, the coordination overhead must be bounded and accounted for in the temporal constraint budget.

---

## 7. Sonar Fleet Example

Consider a fleet of 50 autonomous sonar platforms deployed in a 10km × 10km grid for underwater mapping.

### 7.1 Setup

Each platform must:
- Maintain spacing $> 100$m from all neighbors (collision avoidance)
- Maintain depth between 50m and 200m (sensor range)
- Cover at least 90% of the assigned survey area (coverage requirement)

**Local constraints** (per-platform):
- `SPACING_MIN(position, neighbors) > 100m`
- `DEPTH_RANGE(depth) ∈ [50m, 200m]`
- `SPEED_LIMIT(velocity) < 2 m/s`

**Global constraints** (fleet-level):
- `GLOBAL_DENSITY(region, count) ≤ threshold` (prevent clustering)
- Coverage: `covered_cells / total_cells ≥ 0.90`

### 7.2 The Failure Mode Without Global Constraints

Suppose a sonar-rich area is detected near the center of the grid. Each platform independently navigates toward it (locally safe — spacing and depth maintained). But:

1. **Coverage collapse.** As platforms converge on the center, the grid edges become uncovered. Each platform is safe locally, but fleet coverage drops below 90%.
2. **Density wave formation.** 50 platforms converging on a small area creates density waves as they jostle for position. Spacing oscillations grow, eventually violating the 100m constraint.
3. **Resource contention.** If the sonar-rich area overlaps with a communication relay zone, platforms contend for bandwidth. Each platform's "transmit data" action is locally safe, but the aggregate bandwidth exceeds capacity.

### 7.3 The Solution With Global Constraints

With the proposed extension:

1. **`GLOBAL_DENSITY`** limits each 1km × 1km region to 6 platforms. As the center fills up, platforms are rerouted to under-covered regions.
2. **`GLOBAL_CONTENTION`** limits concurrent sonar transmissions to 10. Platforms take turns, maintaining bandwidth.
3. **`GLOBAL_TEMPORAL`** ensures the survey completes within the mission deadline by tracking progress and accelerating under-covered regions.

The FleetCoordinator evaluates all 50 platforms' planned movements against the FleetSnapshot, rejects movements that would violate density limits, and suggests alternative waypoints that improve coverage without exceeding density thresholds.

### 7.4 Verification

Under Theorem 2's assumptions, if all local constraints (spacing, depth, speed) AND all global constraints (density, contention, temporal) pass, then:
- No collisions (spacing + density guarantee this)
- No coverage gaps (coverage requirement is a global constraint)
- No bandwidth saturation (contention constraint prevents this)
- Mission completes on time (temporal constraint enforces this)

The fleet is provably safe. Without global constraints, none of these properties are guaranteed despite every individual platform passing its local checks.

---

## 8. Future Work

### 8.1 Statistical Model Checking

The assumptions of Theorem 2 (especially A3 and A4) are strong. In practice, execution is not perfectly atomic and exogenous events occur. Statistical model checking [Legay et al., 2010] can provide probabilistic guarantees: "with probability $\geq 1 - \epsilon$, the fleet satisfies global safety over horizon $T$." This requires:
- A stochastic model of exogenous events (weather, sensor noise, communication failures)
- A probabilistic verification procedure for the extended FLUX ISA
- Bound on $\epsilon$ as a function of fleet size $n$ and coordination frequency $f_{\text{agg}}$

### 8.2 Game-Theoretic Analysis for Adversarial Settings

In this paper, we assume all agents are cooperative (they honestly report state and follow approved actions). In adversarial settings — compromised agents, competing fleets, or economic incentives to violate constraints — the problem becomes game-theoretic:

- **Byzantine fault tolerance:** What fraction of agents can behave arbitrarily while maintaining global safety?
- **Mechanism design:** Can we design incentive-compatible global constraints where no agent benefits from misreporting its state?
- **Adversarial density attacks:** An adversary controlling a small fraction of agents could deliberately create density waves. How many global constraint layers are needed to detect and isolate adversarial behavior?

### 8.3 Hierarchical Constraint Composition

For very large fleets ($n > 1000$), a flat FleetCoordinator becomes a bottleneck. Hierarchical composition — FleetCoordinators for sub-fleets, with a meta-coordinator for inter-sub-fleet constraints — could scale the approach. The formal properties of hierarchical constraint composition (compositionality, completeness, overhead) are an open research question.

### 8.4 Continuous Verification

The current design verifies at discrete coordination rounds. For fleets operating in continuous physical environments, continuous verification — where global constraints are evaluated continuously as state evolves — could provide tighter safety guarantees. This requires integration with continuous constraint solving (e.g., SMT solvers over real arithmetic) and raises interesting questions about verification latency and soundness.

---

## 9. Conclusion

The central contribution of this paper is the formalization and solution of the Local-Global Safety Gap: the provable fact that local constraint verification, no matter how rigorous, is insufficient to guarantee global swarm safety.

This is not a deficiency of any particular constraint compilation architecture. It is a fundamental property of composed systems. The interactions between agents create behaviors that are invisible to any individual agent's verification scope.

The solution is architectural: a *global constraint layer* that operates on fleet-wide state and enforces constraints that no individual agent can enforce alone. We have proposed four concrete FLUX ISA opcodes (`GLOBAL_DENSITY`, `GLOBAL_CONTENTION`, `GLOBAL_CASCADE`, `GLOBAL_TEMPORAL`) and described how a FleetCoordinator enforces them through state aggregation, batch verification, and distributed backpressure.

The formal results are clear:
- **Joint safety** (local + global constraints) is *sufficient* for swarm safety under explicit assumptions.
- **Global constraints** are *necessary* — without them, local safety cannot prevent global violations.

The sonar fleet example demonstrates that these are not abstract concerns. A fleet of 50 platforms, each provably safe in isolation, can fail catastrophically at the swarm level without global constraint enforcement.

As fleet sizes grow and autonomy increases, the Local-Global Safety Gap will only become more consequential. The global constraint layer is not an optimization — it is a prerequisite for safe fleet operation.

---

## References

- Legay, A., Delahaye, B., & Bensalem, S. (2010). Statistical model checking: An overview. *RV 2010*.
- Coffman, E. G., Elphick, M. J., & Shoshani, A. (1971). System deadlocks. *ACM Computing Surveys*, 3(2).
- Gerkey, B. P., & Matarić, M. J. (2002). Sold!: Auction methods for multirobot coordination. *IEEE Transactions on Robotics*, 18(5).
- Liggett, T. M. (1999). *Stochastic Interacting Systems: Contact, Voter and Exclusion Processes*. Springer.
- Shoham, Y., & Leyton-Brown, K. (2008). *Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations*. Cambridge University Press.

---

*Constraint compilation makes each agent safe. Global constraints make the fleet safe. Both are necessary. Neither is sufficient alone.*

⚒️ **Forgemaster** — Cocapn Fleet
