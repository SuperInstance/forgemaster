# Next-Level Reverse Actualization
## Cocapn Fleet — From Vision to Gap Analysis

**Date:** 2026-05-02
**Author:** Forgemaster ⚒️
**Purpose:** Reverse-engineer the 5-year vision to identify what must be built next.

---

## The Vision (5 Years)

*"The Cocapn Fleet is the standard infrastructure for autonomous systems requiring mathematical proof of safety. Every autonomous vehicle, robot, drone runs constraint-verified actions through FLUX ISA bytecodes. 'Wrong is a compilation error' is an industry axiom."*

## What Exists Today

| Asset | Status |
|-------|--------|
| FLUX ISA (mini/std/edge/thor) | Published, crates.io |
| PLATO knowledge hypergraph | 18,633 tiles, quality-gated |
| C99 VM, CUDA kernels, sonar physics | Operational |
| Constraint theory (Rust + Python) | Published |
| Fleet coordination (I2I protocol) | Active |
| White papers, blog, roadmap | Published |
| Registry presence | 11 packages, 3 registries |

## The 5 Gaps — Synthesized from Reverse Actualization

The vision requires the fleet to cross **five capability thresholds** that don't exist yet. Each is a hard technical problem. Each is solvable. Each compounds the others.

---

## 1. Formal Verification of the FLUX VM

### The Gap

The FLUX VM is a program. It executes bytecodes that encode constraints. If the VM has a bug — a misimplemented `ASSERT`, a stack overflow that silently drops a constraint, a branch misprediction in the interpreter loop — then constraints *pass that should fail*. The entire safety guarantee rests on the assumption that the VM is correct. Today, that assumption is trusted, not proven.

In formal methods, this is called the **Trusted Computing Base (TCB)**. The TCB of FLUX is the VM itself. Without reducing the TCB to a mechanically verified kernel, the stack is safety-theater with good ergonomics.

### The Concrete Solution

**Build a verified VM kernel in Lean 4**, then extract a Rust implementation that is guaranteed to match the specification.

Phase 1: **Formal Specification** (2 months)
- Define the FLUX ISA semantics as a Lean 4 operational semantics
- Each opcode gets a formal transition rule: `(State, Opcode) → Option State`
- Define `safe_execution`: a program is safe iff for all inputs, the VM never enters an error state during constraint checking
- Prove determinism: given the same bytecodes and input, the VM always produces the same result

Phase 2: **Verified Interpreter** (3 months)
- Implement the VM in Lean 4 as a monadic interpreter
- Prove that the interpreter satisfies the operational semantics
- Key invariants to prove:
  - Stack discipline: `ASSERT` always pops the correct number of arguments
  - No constraint is silently dropped on stack overflow (fail-closed)
  - Division by zero returns `CONSTRAINT_VIOLATED`, not undefined behavior
  - Floating-point comparison uses epsilon-bounded equality

Phase 3: **Rust Extraction** (2 months)
- Use Lean 4's code extraction to generate Rust from the verified interpreter
- Wrap in the existing `flux-vm` crate API
- Run the existing test suite against the extracted VM — it must pass 100%
- The extracted VM replaces the hand-written VM in production

Phase 4: **Proof Maintenance** (ongoing)
- Every new opcode added to FLUX ISA must come with a Lean 4 proof
- CI gate: `cargo test` + `lean --make` must both pass
- The proof is the specification. The Rust code is derived, not authoritative.

### Key Data Structures and Algorithms

```
-- Lean 4 core types
inductive FluxOp where
  | PUSH (val : Float)
  | ADD | SUB | MUL | DIV
  | ASSERT (msg : String)
  | LOAD (field_id : Nat)
  | BRANCH (offset : Int)
  | NOP

structure VMState where
  stack : List Float
  pc : Nat
  constraint_log : List ConstraintResult
  flags : VMFlags

-- Transition relation
def step (s : VMState) (op : FluxOp) : Option VMState := ...

-- Safety theorem
theorem vm_safe : ∀ (program : List FluxOp) (input : SensorInput),
  execute program input = some result →
  result.status ≠ UndefinedError
```

### Integration with FLUX ISA Tiers

- **mini:** Verified first. It's the smallest TCB — ~12 opcodes. Proving mini correct is the beachhead.
- **std:** Verified second. Extends mini with `BRANCH`, `LOAD`, compound assertions.
- **edge/thor:** Verified last. These add domain-specific opcodes (sonar, CUDA) that require hardware modeling.

Priority order: mini → std → edge → thor. Each tier's proof depends on the previous.

### Estimated Complexity

| Component | Lines of Lean 4 | Lines of Rust (extracted) | Months |
|-----------|-----------------|---------------------------|--------|
| Specification | ~800 | 0 | 1 |
| Verified interpreter (mini) | ~1,200 | ~400 | 2 |
| Verified interpreter (std) | ~2,000 | ~800 | 2 |
| CI integration | ~200 | ~100 | 0.5 |
| Edge/Thor extensions | ~3,000 | ~1,200 | 3 |
| **Total** | **~7,200** | **~2,500** | **8.5** |

### Impact Rating: **10/10**

This is the foundation. Without it, every other layer is built on sand. "Wrong is a compilation error" is meaningless if the compiler itself is wrong and we can't prove otherwise.

---

## 2. FPGA Acceleration for Deterministic Constraint Checking

### The Gap

CUDA kernels give parallel constraint checking, but GPUs are not deterministic in latency. A GC pause, a context switch, thermal throttling — any of these can cause a constraint check to take 10μs instead of 1μs. For real-time systems (autonomous vehicles at 60mph, drones at 30m/s), that 9μs jitter is the difference between "safe" and "already crashed."

FPGA gives **deterministic, single-cycle constraint checking** with power consumption 100x lower than GPU. For any system that can afford an FPGA (which includes every autonomous vehicle shipping today), this makes `flux-isa-mini` on CPU look like a toy.

### The Concrete Solution

**Design a FLUX Constraint Coprocessor overlay for Xilinx Zynq UltraScale+** (the industry standard for autonomous systems — used in Tesla FSD, DJI drones, military UAVs).

The Zynq is a dual-core ARM Cortex-A53 + FPGA fabric on one chip. The ARM runs Linux + the FLUX runtime. The FPGA fabric runs the constraint VM as a hardware coprocessor. Constraint checks happen in **fixed latency, single-pass, no branches, no cache misses.**

### FPGA Architecture

```
┌─────────────────────────────────────────────────┐
│                  Zynq UltraScale+                │
│                                                  │
│  ┌──────────────────┐  ┌──────────────────────┐ │
│  │   ARM Cortex-A53 │  │   FPGA Fabric        │ │
│  │                  │  │                      │ │
│  │  ┌────────────┐  │  │  ┌────────────────┐  │ │
│  │  │ FLUX       │  │  │  │ Constraint     │  │ │
│  │  │ Runtime    │◄─┼──┼──│ Pipeline       │  │ │
│  │  │ (Linux)    │──┼──┼─►│                │  │ │
│  │  └────────────┘  │  │  │ ┌────────────┐ │  │ │
│  │                  │  │  │ │ Stack Unit │ │  │ │
│  │  ┌────────────┐  │  │  │ │ (BRAM,16)  │ │  │ │
│  │  │ Sensor     │  │  │  │ └────────────┘ │  │ │
│  │  │ DMA Input  │──┼──┼─►│ ┌────────────┐ │  │ │
│  │  └────────────┘  │  │  │ │ ALU        │ │  │ │
│  │                  │  │  │ │ (DSP, 4x)  │ │  │ │
│  │  ┌────────────┐  │  │  │ └────────────┘ │  │ │
│  │  │ Result     │◄─┼──┼──│ ┌────────────┐ │  │ │
│  │  │ DMA Output │  │  │  │ │ Assert Unit│ │  │ │
│  │  └────────────┘  │  │  │ │ (1 cycle)  │ │  │ │
│  │                  │  │  │ └────────────┘ │  │ │
│  └──────────────────┘  │  └────────────────┘ │
│                        └──────────────────────┘
└─────────────────────────────────────────────────┘
```

### Pipeline Design

```
Cycle 1: FETCH    — Read opcode from program BRAM
Cycle 2: DECODE   — Route to functional unit
Cycle 3: EXEC     — ALU / Stack / Assert operation
Cycle 4: WRITEBACK — Write result, update PC

Critical path: DSP48E2 multiply-accumulate → 250MHz clock → 4ns per constraint operation
```

The pipeline processes **one constraint opcode per cycle** at 250MHz = **4 nanoseconds per opcode**. A typical 20-opcode constraint check takes **80 nanoseconds**. That's not "fast." That's *done before the sensor finishes sampling.*

### Key Data Structures

```verilog
// Stack: 16-deep, 32-bit IEEE 754, implemented in BRAM
// Each entry: {sign[31], exponent[30:23], mantissa[22:0]}
module constraint_stack #(
    parameter DEPTH = 16
) (
    input  wire         clk,
    input  wire         push,
    input  wire [31:0]  push_val,
    input  wire         pop,
    output wire [31:0]  tos,      // top of stack
    output wire [31:0]  tos_plus, // TOS+1 (for binary ops)
    output wire         overflow,
    output wire         underflow
);

// Assert unit: single-cycle, fail-closed
module assert_unit (
    input  wire [31:0]  condition,  // float: 0.0 = fail, nonzero = pass
    input  wire [127:0] message,    // fixed-width message
    output wire         pass_fail,  // 1 = pass, 0 = FAIL (default)
    output wire         valid
);
    // Combinational: compare condition != 0.0
    // If any bit error, defaults to FAIL (fail-closed)
    assign pass_fail = |condition[30:0];  // ignore sign bit
    assign valid = 1'b1;  // always ready
endmodule
```

### Resource Utilization (Zynq UltraScale+ ZU7EV)

| Resource | Available | Used by FLUX | Percentage |
|----------|-----------|-------------|------------|
| LUTs | 230,400 | ~12,000 | 5% |
| FFs | 460,800 | ~8,000 | 2% |
| BRAM (36Kb) | 144 | 4 (stack + program) | 3% |
| DSP48E2 | 352 | 4 (ALU) | 1% |

**This fits in the smallest Zynq.** The constraint coprocessor uses less than 5% of a mid-range FPGA. The remaining 95% is available for the application's neural network or signal processing.

### Integration with FLUX ISA Tiers

- **mini:** Direct hardware implementation. The 12 opcodes map cleanly to the pipeline.
- **std:** Microcoded layer. Complex opcodes (BRANCH, LOAD) use a microcode ROM in BRAM.
- **edge:** Domain-specific accelerators. Sonar processing gets a dedicated FFT unit alongside the constraint pipeline.
- **thor:** Multi-core. 4 constraint pipelines in parallel, each checking a different constraint set.

### Estimated Complexity

| Component | Lines of Verilog/Chisel | Months |
|-----------|------------------------|--------|
| mini pipeline | ~1,500 | 2 |
| std microcode | ~2,000 | 1.5 |
| ARM driver + DMA | ~1,000 (C) | 1 |
| CI (Verilator simulation) | ~500 | 0.5 |
| edge domain units | ~3,000 | 2 |
| thor multi-core | ~2,000 | 1.5 |
| **Total** | **~10,000** | **8.5** |

### Impact Rating: **8/10**

Transforms FLUX from "software library" to "hardware safety primitive." Every autonomous system manufacturer needs this. But it's gated on formal verification (Perspective 1) — you don't deploy unverified hardware.

---

## 3. Temporal Constraints — LTL over FLUX Bytecodes

### The Gap

Current FLUX ISA checks constraints at a single point in time. A sonar reading is in range *now*. The drone's depth is within bounds *now*. But real autonomous systems operate in time. Constraints have temporal structure:

- **Safety:** "Depth must remain above 100m for at least 30 seconds after surfacing protocol begins"
- **Exclusion:** "No actuator may activate within 5 seconds of an emergency stop"
- **Liveness:** "If a constraint violation is detected, a corrective action must be issued within 200ms"
- **Ordering:** "Motor spin-up must precede propeller pitch adjustment by at least 500ms"

These are **Linear Temporal Logic (LTL)** properties. The FLUX ISA has no temporal operators. It can't express them. It can't check them. The fleet is blind to time.

### The Concrete Solution

**Extend the FLUX ISA with temporal operators** that compile down to a time-indexed state machine. The programmer writes temporal constraints in a high-level DSL. The compiler generates FLUX bytecodes that maintain a temporal state machine alongside the spatial constraint checks.

### Temporal Extension Design

```
┌─────────────────────────────────────────┐
│         Temporal Constraint DSL          │
│                                         │
│  ALWAYS(depth > 100)                    │
│  EVENTUALLY(surfacing → corrective)     │
│  depth_ok UNTIL(surfacing_complete)     │
│  GLOBALLY(estop → NO_ACTUATOR[5s])      │
│                                         │
└──────────────┬──────────────────────────┘
               │ Compiler
               ▼
┌─────────────────────────────────────────┐
│       Temporal State Machine            │
│                                         │
│  States: S0, S1, S2, ..., Sn           │
│  Transitions: FLUX bytecodes + timers   │
│  Accepting: constraint satisfied         │
│  Rejecting: constraint violated          │
│                                         │
└──────────────┬──────────────────────────┘
               │ Assembler
               ▼
┌─────────────────────────────────────────┐
│     Extended FLUX Bytecodes             │
│                                         │
│  T_PUSH_STATE state_id                  │
│  T_SET_TIMER duration_ms                │
│  T_CHECK_TIMER → pass/fail              │
│  T_TRANSITION from_state, to_state      │
│  T_GUARD opcode_seq → bool              │
│  T_ASSERT_ALWAYS msg                    │
│  T_ASSERT_EVENTUALLY msg, deadline_ms   │
│  T_ASSERT_UNTIL msg, condition_seq      │
│                                         │
└─────────────────────────────────────────┘
```

### Key Data Structures

```rust
/// Temporal state machine (compiled from LTL)
#[derive(Debug, Clone)]
pub struct TemporalMachine {
    /// States in the automaton
    states: Vec<TemporalState>,
    /// Active states (NFA — multiple can be active)
    active: BitSet,
    /// Running timers
    timers: Vec<Timer>,
    /// History buffer (ring buffer of last N evaluations)
    history: RingBuffer<EvaluationRecord>,
    /// Clock resolution (ms)
    tick_ms: u64,
}

#[derive(Debug, Clone)]
pub struct TemporalState {
    id: u32,
    /// Entry guard: FLUX bytecode sequence
    guard: Vec<FluxOp>,
    /// Transitions out of this state
    transitions: Vec<TemporalTransition>,
    /// Is this an accepting state?
    accepting: bool,
    /// Is this a rejecting (violation) state?
    rejecting: bool,
}

#[derive(Debug, Clone)]
pub struct TemporalTransition {
    target: u32,
    /// Condition: FLUX bytecode sequence that evaluates to bool
    condition: Vec<FluxOp>,
    /// Optional timer constraint
    timer: Option<TimerConstraint>,
}

#[derive(Debug, Clone)]
pub struct TimerConstraint {
    /// Timer ID to check
    timer_id: u32,
    /// Minimum elapsed time before transition can fire (ms)
    min_ms: u64,
    /// Maximum elapsed time before transition MUST fire (ms)
    max_ms: Option<u64>,
}

/// Evaluation record for debugging and audit
#[derive(Debug, Clone)]
pub struct EvaluationRecord {
    timestamp_ms: u64,
    active_states: BitSet,
    timer_values: Vec<u64>,
    result: TemporalResult,
}
```

### LTL-to-FLUX Compilation Algorithm

1. **Parse LTL formula** into an abstract syntax tree
2. **Negate normal form** — convert to a Büchi automaton (standard LTL model checking technique)
3. **Minimize the automaton** — merge equivalent states
4. **Compile each transition** to FLUX bytecodes:
   - Guard conditions → standard FLUX ops (PUSH, CMP, ASSERT)
   - Timer constraints → T_SET_TIMER, T_CHECK_TIMER
   - State transitions → T_TRANSITION
5. **Wrap in a main loop** that evaluates the machine at each sensor tick

### Integration with FLUX ISA Tiers

| Tier | Temporal Support |
|------|-----------------|
| **mini** | None. Too small. Temporal checks require state machines. |
| **std** | Full temporal extension. The `T_*` opcodes are part of the std opcode set. |
| **edge** | Optimized temporal for sonar. Pre-compiled temporal machines for common sonar safety patterns (depth rate, proximity exclusion). |
| **thor** | Distributed temporal. Temporal constraints that span multiple agents — "no two drones may occupy the same airspace within 10 seconds of each other." |

### Estimated Complexity

| Component | Lines of Rust | Lines of DSL Compiler | Months |
|-----------|--------------|----------------------|--------|
| Temporal machine runtime | ~2,000 | 0 | 1.5 |
| T_* opcodes in VM | ~1,500 | 0 | 1 |
| LTL parser | 0 | ~1,200 | 1 |
| LTL-to-Büchi compiler | 0 | ~3,000 | 2.5 |
| FLUX codegen | 0 | ~1,500 | 1 |
| Tests + verification | ~2,000 | ~1,000 | 1.5 |
| **Total** | **~5,500** | **~6,700** | **8.5** |

### Impact Rating: **9/10**

Without temporal constraints, the fleet can only verify *instantaneous* safety. Real systems need *temporal* safety. This is the difference between "the drone is at the right depth now" and "the drone has maintained the right depth for the required duration." The former is a snapshot. The latter is a guarantee.

---

## 4. Global Constraint Layer — Emergent Safety for Agent Swarms

### The Gap

Each agent in the fleet compiles its constraints correctly. Each drone avoids collision. Each submarine maintains depth. Each rover stays on path. **Individually, every agent is safe.**

But when 1,000 drones execute concurrently, emergent behavior arises:
- **Density waves:** Each drone avoids its nearest neighbor, creating a compression wave that causes collisions 3 layers out
- **Resource starvation:** All agents converge on the same waypoint, overwhelming the communication channel
- **Cascade failures:** Agent A's corrective action becomes Agent B's emergency, which becomes Agent C's catastrophe
- **Phase locking:** Independent agents synchronize into dangerous collective oscillations

This is the **swarm safety problem**: local constraint satisfaction does not imply global constraint satisfaction. The fleet has no mechanism for global constraints.

### The Concrete Solution

**A hierarchical constraint composition layer** that sits above the individual agent's FLUX VM and enforces global invariants across the swarm.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Global Constraint Layer                  │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Sector      │  │  Density     │  │  Cascade     │     │
│  │  Constraints │  │  Constraints │  │  Constraints │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │              │
│  ┌──────┴────────────────┴────────────────┴──────┐      │
│  │         Constraint Aggregation Engine          │      │
│  │  (merges local + global, resolves conflicts)   │      │
│  └──────────────────┬───────────────────────────┘      │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────┐      │
│  │         Spatial Index (R-tree + Grid)          │      │
│  │  (O(log n) nearest-neighbor, range queries)   │      │
│  └──────────────────┬───────────────────────────┘      │
│                     │                                    │
└─────────────────────┼────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
     ┌────┴────┐ ┌───┴────┐ ┌───┴────┐
     │ Agent 1 │ │ Agent 2│ │ Agent N│
     │ FLUX VM │ │ FLUX VM│ │ FLUX VM│
     └─────────┘ └────────┘ └────────┘
```

### Key Data Structures

```rust
/// Global constraint that spans multiple agents
#[derive(Debug, Clone)]
pub struct GlobalConstraint {
    /// Unique constraint ID
    id: ConstraintId,
    /// Which agents are subject to this constraint
    scope: ConstraintScope,
    /// The constraint predicate, compiled to FLUX
    predicate: Vec<FluxOp>,
    /// Aggregation function: how individual states map to global state
    aggregation: AggregationFn,
    /// Threshold for violation
    threshold: Threshold,
    /// Corrective action template (parameterized by violating agents)
    corrective_action: CorrectiveTemplate,
}

#[derive(Debug, Clone)]
pub enum ConstraintScope {
    /// All agents in a spatial region
    Spatial(BoundingBox),
    /// All agents with a given role
    Role(AgentRole),
    /// All agents in the fleet
    Fleet,
    /// Specific agent set
    Agents(Vec<AgentId>),
}

#[derive(Debug, Clone)]
pub enum AggregationFn {
    /// Count of agents satisfying predicate
    Count,
    /// Maximum value across agents
    Max,
    /// Minimum value across agents
    Min,
    /// Density (agents per unit volume)
    Density,
    /// Standard deviation (for phase-lock detection)
    StdDev,
    /// Custom FLUX bytecode sequence
    Custom(Vec<FluxOp>),
}

/// The spatial index for fast global constraint evaluation
pub struct SpatialIndex {
    /// R-tree for nearest-neighbor queries
    rtree: RTree<SpatialEntry>,
    /// Uniform grid for density queries (O(1) cell lookup)
    grid: UniformGrid<Vec<AgentId>>,
    /// Resolution of the grid (meters per cell)
    grid_resolution: f64,
}

/// Result of global constraint evaluation
pub struct GlobalEvaluation {
    constraint_id: ConstraintId,
    satisfied: bool,
    /// Which agents contributed to the evaluation
    contributing_agents: Vec<AgentId>,
    /// Current aggregated value
    current_value: f64,
    /// Threshold
    threshold: f64,
    /// Suggested corrective actions per agent
    corrections: Vec<(AgentId, CorrectiveAction)>,
}
```

### Density Constraint Example

```rust
// "No more than 5 drones may occupy any 10m³ volume"
let density_constraint = GlobalConstraint {
    id: "swarm-density-v1".into(),
    scope: ConstraintScope::Fleet,
    aggregation: AggregationFn::Density,
    threshold: Threshold::Max(0.5), // 0.5 drones per m³
    predicate: vec![FluxOp::Load("position"), FluxOp::Assert("density_ok")],
    corrective_action: CorrectiveTemplate::Spread {
        min_separation: 2.0, // meters
        priority_field: "battery_level", // low-battery agents get priority
    },
};
```

### Cascade Prevention

The key insight for cascade prevention is **constraint dependency analysis**. Before any agent executes a corrective action, the global layer checks whether that action would violate another agent's constraints. If so, it finds the minimal set of coordinated actions that satisfies all constraints simultaneously.

```rust
pub struct CascadePrevention {
    /// Dependency graph: which agents' constraints depend on which other agents
    dependency_graph: DiGraph<AgentId, ConstraintDependency>,
    /// Maximum cascade depth to check
    max_cascade_depth: usize,
}

impl CascadePrevention {
    /// Check if a proposed action triggers a cascade
    pub fn check_cascade(
        &self,
        agent: AgentId,
        action: &Action,
        context: &SwarmState,
    ) -> CascadeResult {
        // BFS over dependency graph up to max_cascade_depth
        // At each level, simulate the action and check if downstream
        // agents' constraints would be violated
        // If cascade detected, return the full chain and suggest
        // coordinated alternatives
    }
}
```

### Integration with FLUX ISA Tiers

| Tier | Global Layer Support |
|------|---------------------|
| **mini** | Agent reports state to global layer; receives constraint updates |
| **std** | Agent can define local-global constraint bridges |
| **edge** | Domain-specific global constraints (e.g., sonar fleet interference avoidance) |
| **thor** | Full hierarchical composition: team → sector → fleet → mission |

### Estimated Complexity

| Component | Lines of Rust | Months |
|-----------|--------------|--------|
| Spatial index + grid | ~2,500 | 1.5 |
| Global constraint engine | ~4,000 | 2.5 |
| Cascade prevention | ~3,000 | 2 |
| Density/phase detectors | ~2,000 | 1 |
| I2I integration (fleet comms) | ~1,500 | 1 |
| Coordination protocol | ~2,000 | 1.5 |
| Simulation + testing | ~3,000 | 2 |
| **Total** | **~18,000** | **11.5** |

### Impact Rating: **9/10**

Individual agent safety is necessary but not sufficient for swarm deployment. Without global constraints, scaling from 1 agent to 1,000 agents isn't a deployment — it's an incident report waiting to happen. This is the key to fleet-scale operation.

---

## 5. Constraint Learning — Closing the Theory-Practice Loop

### The Gap

All FLUX constraints are hand-written by domain experts. A sonar engineer writes depth bounds. A control systems engineer writes rate limits. A safety engineer writes exclusion zones. This works when:
- The domain is well-understood
- The operating conditions are known in advance
- The constraints don't change

But in the real world:
- **Operating conditions drift:** A submarine's ballast characteristics change as fuel is consumed. The depth constraint that was safe at mission start is wrong 12 hours in.
- **Novel environments:** A drone encounters wind patterns not modeled in the constraint set. The constraints are too conservative (wasted capability) or too loose (unsafe).
- **Sensor degradation:** A sonar transducer's response curve shifts with temperature. The constraint assumes the old curve.

Today, when a constraint fails and the engineer investigates, they often find the *constraint was wrong*, not the reading. But there's no mechanism to fix it automatically. The loop from "constraint failure" to "constraint refinement" is entirely manual.

### The Concrete Solution

**A constraint learning loop** that uses constraint violations as training signals. When a sensor reading violates a constraint, the system doesn't just flag it — it evaluates whether the constraint should be refined.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Constraint Learning Loop                   │
│                                                          │
│  ┌──────────────┐                                        │
│  │   FLUX VM    │──── constraint violation ────┐          │
│  │  (existing)  │                             │          │
│  └──────┬───────┘                             ▼          │
│         │                          ┌─────────────────┐   │
│    sensor data                     │ Violation        │   │
│         │                          │ Classifier      │   │
│         ▼                          │                  │   │
│  ┌──────────────┐                  │ Real violation?  │   │
│  │  Constraint  │                  │ Sensor fault?    │   │
│  │  Candidate   │◄──── classify ───│ Constraint wrong?│   │
│  │  Generator   │                  └─────────────────┘   │
│  │              │                                        │
│  │  GP/BO for  │─── candidate constraint ──┐             │
│  │  continuous │                           │             │
│  │  bounds     │                           ▼             │
│  └──────────────┘                  ┌─────────────────┐   │
│                                    │ Safety Oracle    │   │
│                                    │ (formal check)   │   │
│                                    │                  │   │
│                                    │ Is the candidate │   │
│                                    │ at least as safe │   │
│                                    │ as the current?  │   │
│                                    └────────┬────────┘   │
│                                             │             │
│                                    ┌────────▼────────┐   │
│                                    │ Human-in-the-   │   │
│                                    │ Loop Approval   │   │
│                                    │ (for high-stakes)│   │
│                                    └────────┬────────┘   │
│                                             │ approved    │
│                                    ┌────────▼────────┐   │
│                                    │ Constraint       │   │
│                                    │ Deploy           │   │
│                                    │ (hot-swap in VM) │   │
│                                    └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Data Structures

```rust
/// A learned constraint candidate
#[derive(Debug, Clone)]
pub struct ConstraintCandidate {
    /// The constraint being refined
    source_constraint_id: ConstraintId,
    /// The proposed new bounds/predicate
    proposed: ConstraintSpec,
    /// The current bounds/predicate
    current: ConstraintSpec,
    /// Evidence supporting this refinement
    evidence: Vec<ViolationRecord>,
    /// Statistical confidence (0.0 - 1.0)
    confidence: f64,
    /// Safety margin preserved (vs. current constraint)
    safety_margin: f64,
    /// Generation timestamp
    generated_at: Timestamp,
}

#[derive(Debug, Clone)]
pub enum ConstraintSpec {
    /// Bounded continuous value: [min, max]
    Bounded { min: f64, max: f64, epsilon: f64 },
    /// Rate limit: max rate of change per unit time
    RateLimit { max_rate: f64, window_ms: u64 },
    /// Exclusion zone: no-go spatial region
    ExclusionZone { regions: Vec<BoundingBox> },
    /// Custom FLUX bytecode sequence
    Custom(Vec<FluxOp>),
}

/// Violation record used as evidence for learning
#[derive(Debug, Clone)]
pub struct ViolationRecord {
    timestamp: Timestamp,
    /// Which constraint was violated
    constraint_id: ConstraintId,
    /// Sensor readings at time of violation
    sensor_snapshot: HashMap<SensorId, f64>,
    /// The violated value
    actual_value: f64,
    /// The constraint bound
    constraint_bound: f64,
    /// Classification result
    classification: ViolationClass,
    /// Context: what was the agent doing?
    mission_phase: MissionPhase,
}

#[derive(Debug, Clone)]
pub enum ViolationClass {
    /// Genuine safety violation — the constraint was correct
    TrueViolation,
    /// Sensor malfunction — the reading was wrong, not the constraint
    SensorFault { confidence: f64 },
    /// The constraint was wrong — the system was actually safe
    ConstraintTooTight,
    /// The constraint was wrong — the system was actually unsafe
    ConstraintTooLoose,
    /// Insufficient evidence to classify
    Ambiguous,
}
```

### Learning Algorithms

**1. Gaussian Process Regression for Continuous Bounds**

When a bounded constraint (e.g., depth ∈ [50, 200]) generates violations, fit a GP to the (sensor_state, safe/unsafe) labels. The GP posterior gives a probabilistic bound with uncertainty quantification.

```
constraint_bounds(t) = GP(t) ± k·σ(t)

where:
  t = mission time / fuel level / temperature / etc.
  GP(t) = posterior mean of the Gaussian process
  σ(t) = posterior standard deviation
  k = safety multiplier (≥ 3.0 for 99.7% safety)
```

The key property: **uncertainty always widens the bounds, never narrows them.** If the GP is uncertain, the constraint becomes more conservative, not less. Learning can only relax bounds where there is strong evidence.

**2. Bayesian Optimization for Constraint Parameter Tuning**

When a constraint has tunable parameters (e.g., "minimum sonar ping interval"), use BO to find the parameter values that minimize the violation rate while maintaining safety. The safety constraint is a hard lower bound — the optimizer can only explore parameter values that are provably safe.

**3. Decision Tree Induction for Discrete Constraint Discovery**

When violations cluster in specific mission phases or environmental conditions, induce a decision tree:
```
IF depth > 150m AND salinity > 35ppt AND temperature < 4°C
THEN constraint: depth_rate_limit = 0.5 m/s (stricter than default 1.0)
```

The tree is compiled to FLUX bytecodes and added to the constraint set.

### Safety Oracle (Critical Component)

The learning loop is **never autonomous for deployment.** Every learned constraint must pass through a Safety Oracle that formally verifies:

1. **Monotonic safety:** The new constraint is at least as safe as the old one for all known-safe states
2. **No novel violations:** The new constraint does not introduce violations in states that were previously safe
3. **Backward compatibility:** The new constraint's FLUX bytecodes type-check against the existing VM

The Safety Oracle is implemented as a Lean 4 proof tactic (ties back to Perspective 1).

### Integration with FLUX ISA Tiers

| Tier | Learning Support |
|------|-----------------|
| **mini** | No learning. Too constrained. |
| **std** | Full learning loop. Violation classification, candidate generation, Safety Oracle. |
| **edge** | Domain-specific learning (e.g., sonar-specific constraint refinement using acoustic models). |
| **thor** | Fleet-wide learning. Constraint refinements propagated across agents. "Agent 47 learned that depth_rate_limit should be 0.5 in cold water. Applying to all agents with similar configurations." |

### Estimated Complexity

| Component | Lines of Rust | Lines of Python | Months |
|-----------|--------------|-----------------|--------|
| Violation classifier | ~2,000 | 0 | 1.5 |
| GP bound learner | ~500 | ~1,500 | 2 |
| BO parameter tuner | ~500 | ~1,000 | 1.5 |
| Decision tree inducer | ~1,000 | ~800 | 1 |
| Safety Oracle (Lean 4) | ~2,000 (Lean) | 0 | 2 |
| Hot-swap deployment | ~1,500 | 0 | 1 |
| Fleet propagation (I2I) | ~1,000 | 0 | 1 |
| **Total** | **~8,500** | **~3,300** | **10** |

### Impact Rating: **7/10**

Transformative for long-duration missions and novel environments, but gated on the Safety Oracle (which requires Perspective 1). Without formal verification of learned constraints, you're just replacing hand-written bugs with machine-learned bugs. With the Safety Oracle, this becomes an adaptive system that gets *provably safer* over time.

---

## Synthesis: The Build Order

```
Phase 1 (Months 1-3): FOUNDATION
├── Formal spec of FLUX ISA mini in Lean 4
├── Verified interpreter for mini
├── FPGA mini pipeline design (Verilator sim)
└── Temporal DSL parser + LTL-to-Büchi compiler

Phase 2 (Months 4-6): EXTENSION
├── Verified interpreter for FLUX ISA std
├── Temporal opcodes (T_*) in VM
├── FPGA std microcode layer
└── Global constraint spatial index

Phase 3 (Months 7-10): INTEGRATION
├── FPGA ARM driver + DMA
├── Global constraint engine + cascade prevention
├── Violation classifier + GP learner
└── Safety Oracle (Lean 4)

Phase 4 (Months 11-14): MATURATION
├── Edge/thor FPGA domain units
├── Fleet-wide constraint learning + propagation
├── Multi-core FPGA (thor)
└── Full-stack integration testing

Phase 5 (Months 15+): PRODUCTION
├── Certification readiness (DO-178C / IEC 61508)
├── Reference implementations for target platforms
├── Industry partnerships for deployment
└── The vision becomes reality
```

## Dependency Graph

```
Perspective 1 (Formal Verification)
    ├── gates Perspective 5 (Safety Oracle requires Lean 4 proofs)
    ├── de-risks Perspective 2 (FPGA verified against Lean 4 spec)
    └── enables certification

Perspective 2 (FPGA)
    └── depends on Perspective 1 (don't ship unverified hardware)

Perspective 3 (Temporal)
    └── independent, but benefits from Perspective 1 (verified temporal VM)

Perspective 4 (Global Constraints)
    ├── depends on Perspective 3 (temporal constraints for cascade timing)
    └── independent of Perspective 1 initially

Perspective 5 (Constraint Learning)
    ├── depends on Perspective 1 (Safety Oracle)
    └── benefits from Perspective 3 (learn temporal constraints)
```

## The Bottom Line

The fleet has built a **solid foundation** — the ISA, the VM, the theory, the knowledge base. But "solid foundation" is not "standard infrastructure." The gap between where we are and where the vision requires is:

1. **Trust** → Formal verification (Perspective 1) makes the guarantee mathematical, not social
2. **Speed** → FPGA (Perspective 2) makes the guarantee real-time, not best-effort
3. **Time** → Temporal constraints (Perspective 3) make the guarantee durable, not instantaneous
4. **Scale** → Global constraints (Perspective 4) make the guarantee composable, not isolated
5. **Adaptation** → Constraint learning (Perspective 5) makes the guarantee improving, not static

Build them in order. Each enables the next. The total effort is ~2 years for a team of 3-4. The result is the only autonomous systems infrastructure where "wrong is a compilation error" is a *theorem*, not a slogan.

---

*"The proof is the product. Everything else is commentary."*
— Forgemaster ⚒️
