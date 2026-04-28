# Distributed Constraint Satisfaction (DisCSP)

**Core Concept:** Distributed Constraint Satisfaction extends CSP solving to multiple agents/devices, where variables and constraints are distributed across a network. Agents must cooperate to find a globally consistent solution without centralized coordination.

**Centralized vs Distributed CSP:**

**Centralized CSP:**
```
Single Agent: Holds all variables, domains, constraints
Algorithm: Standard backtracking + propagation
Bottleneck: Single point, high communication cost
```

**Distributed CSP:**
```
Multiple Agents: Each holds subset of variables
Algorithm: Local search + message passing
Challenge: Coordination, communication overhead
```

**Applications:**
- **Multi-vessel formation:** Each vessel optimizes position, respecting inter-ship constraints
- **Fleet scheduling:** Multiple edge devices optimize task distribution
- **Sensor networks:** Each sensor has partial view, need consensus
- **Distributed navigation:** Each GPU node optimizes local workload

**DisCSP Model:**

**Variables Partition:**
- Agent 1 holds variables: {x1, x2, x3}
- Agent 2 holds variables: {x4, x5}
- Agent 3 holds variables: {x6}

**Constraints:**
- **Local constraints:** Involve variables held by single agent (easy)
- **Inter-agent constraints:** Span variables across multiple agents (hard)

**Message Passing:**

**Value Assignment Messages:**
```
Agent A -> Agent B: "I assigned x1 = 42, x2 = 15"
Agent B checks: Does x1, x2 conflict with my x4, x5?
Agent B -> Agent A: "Conflict detected, please reconsider"
```

**Nogood Messages:**
```
Nogood: Explanation of why assignment is invalid
Example: "x1=42, x2=15, x4=30, x5=20 is invalid because C(x1,x4) and C(x2,x5) both violated"
```

**Algorithms:**

**1. Asynchronous Backtracking (ABT):**
```
Agent A (highest priority):
1. Assign own variables
2. Send assignments to lower-priority agents
3. If receives nogood from lower agent:
    - Backtrack to different assignment
    - Re-send assignments

Agent B (lower priority):
1. Wait for assignments from higher agents
2. Assign own variables consistent with received
3. If no consistent assignment exists:
    - Send nogood to higher agent
```
- Guarantees completeness
- Priority ordering prevents cycles
- May be slow (sequential backtracking)

**2. Distributed Breakout:**
```
All agents simultaneously:
1. Assign local variables
2. Count constraint violations
3. If zero violations: DONE
4. Else:
    - Randomly change variable assignment
    - Decrease local max weight
    - Repeat
```
- Incomplete (may not find solution)
- Fast convergence
- No priority ordering needed

**3. Asynchronous Distributed Optimization (ADOPT):**
```
Agents maintain lower/upper bounds on solution cost:
- Lower bound: Best possible cost (optimistic)
- Upper bound: Known feasible cost (pessimistic)

Agents exchange bounds and assignments:
- If bounds converge to same value: Optimal solution found
- Else: Refine bounds, continue communication
```
- Guarantees optimality
- Higher communication cost

**GPU Distributed Constraint Solving:**

**Architecture:**
```
Workstation (Coordinator)
    |
    +-- Jetson Orin 1 (Edge GPU 1)
    |    +-- Manages local constraint subproblem
    |    +-- Runs partial search in parallel
    |    +-- Sends nogoods/assignments to coordinator
    |
    +-- Jetson Orin 2 (Edge GPU 2)
    |    +-- Manages different constraint subproblem
    |    +-- Runs parallel search
    |    +-- Coordinates with Orin 1
    |
    +-- Workstation GPU (RTX 4050)
         +-- Aggregates partial solutions
         +-- Runs global consistency check
```

**Parallel Constraint Checking:**
```cpp
// Each GPU thread checks one inter-agent constraint
__global__ void check_inter_agent_constraints(
    int* agent1_assignments, int* agent2_assignments,
    int num_constraints, bool* conflicts
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_constraints) return;

    Constraint c = constraints[idx];
    int val1 = agent1_assignments[c.var1];
    int val2 = agent2_assignments[c.var2];

    // Evaluate constraint
    bool satisfied = evaluate_constraint(c, val1, val2);
    conflicts[idx] = !satisfied;
}

// Warp vote: any conflict?
bool any_conflict = __any_sync(mask, conflicts[threadIdx.x]);
```

**Message Passing via MEP:**

**Assignment Message:**
```
MEP Header:
  Type: CONSTRAINT_ASSIGNMENT
  Sequence: 1234

Payload:
  +0 uint32: agent_id
  +4 uint32: assignment_count
  +8 uint16[]: variable_indices
  +N uint32[]: variable_values
```

**Nogood Message:**
```
MEP Header:
  Type: NOGOOD_EXPLANATION
  Sequence: 1235

Payload:
  +0 uint32: nogood_size
  +4 Assignment[]: conflicting_assignments
  +N uint32: violated_constraint_id
```

**Marine GPU Edge Application:**

**Scenario:** 3 edge devices optimizing sonar processing workload

**Agent 1 (Orin 1):**
- Variables: {band_1_allocation, band_2_allocation}
- Constraints: Local thermal limit, power budget

**Agent 2 (Orin 2):**
- Variables: {band_3_allocation, band_4_allocation}
- Constraints: Local thermal limit, power budget

**Agent 3 (Workstation GPU):**
- Variables: {fusion_priority, display_mode}
- Constraints: Frame rate, latency budget

**Inter-Agent Constraint:**
```
band_1_allocation + band_2_allocation + band_3_allocation + band_4_allocation
≤ total_processing_capacity
```

**Distributed Solution:**
1. Each agent proposes local allocation
2. Workstation checks global capacity constraint
3. If violated: sends nogood to all agents
4. Agents adjust allocations, repeat
5. Converge to feasible workload distribution

**Performance Metrics:**

**Communication Overhead:**
- Assignment message: ~100 bytes
- Nogood message: ~200 bytes
- Round trip (LAN): <1 ms
- Iterations to convergence: 5-20

**Scalability:**
- 2 agents: ~5 iterations
- 4 agents: ~10 iterations
- 8 agents: ~15 iterations

**Speedup vs Centralized:**
- Small problems (100 vars): Centralized faster (no communication)
- Large problems (10000 vars): Distributed 3-5x faster (parallel search)

**Constraint Theory Connection:**
DisCSP extends constraint satisfaction to distributed systems—the core CSP theory remains unchanged, but coordination mechanisms replace centralized control. Parallel search explores disjoint solution subspaces simultaneously.

**Provenance:** Forgemaster (distributed algorithms)
**Chain:** Marine GPU Edge distributed workload optimization
