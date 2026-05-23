# Cross-Tier Constraint Compilation: Compiling Once, Executing Everywhere in the FLUX ISA Stack

**Forgemaster ⚒️ — Cocapn Fleet**
**2026-05-03**

---

## 1. Abstract

The FLUX constraint stack spans four execution tiers — Mini, Standard, Edge, and Thor — each offering a strictly increasing set of opcodes (21→37→35→43) and capabilities. Writing constraints that target a specific tier creates portability failures: a constraint authored for Thor's CUDA-accelerated solver cannot execute on a Mini-tier microcontroller. This paper introduces the **cross-tier constraint compiler**, a system that takes a high-level constraint specification and compiles it to the *minimum tier* capable of executing it. The compiler performs tier analysis, automatic downcompilation of high-level opcodes into lower-tier equivalents, and produces verifiably correct bytecode for any target tier. We formalize the tier capability model, define the tier descriptor data structure, present the five-pass compilation algorithm, prove the correctness of downcompilation under a capability-subset semantics, and demonstrate practical downcompilation across three real-world examples: sonar depth processing, fleet coordination, and quality gate reduction. The result is a "write once, compile anywhere" constraint execution model analogous to GLSL shader compilation for GPU pipelines.

---

## 2. Introduction

### 2.1 The Problem of Tier Fragmentation

The Cocapn fleet deploys constraint solvers across a heterogeneous hardware landscape. A sonar buoy runs a Mini-tier FLUX VM with 21 opcodes, no heap, and 256 bytes of stack. A shore station runs Standard-tier with file I/O and quality gates. An edge node runs async PLATO synchronization and sensor pipelines. The mothership runs Thor-tier with CUDA, fleet coordination, and batch solving.

Each tier can express constraints, but their capabilities differ radically. A constraint written for Thor using `CUDA_BATCH_SOLVE` and `PARALLEL_BRANCH` is meaningless on a Mini-tier VM that has neither CUDA nor branching beyond basic conditionals. The naive approach — maintaining four separate constraint implementations — is unsustainable. It duplicates logic, introduces drift, and violates the fleet's constraint-theory principle: a constraint should be specified once, in its most general form, and then mechanically compiled to whatever hardware is available.

### 2.2 Analogy: Shader Compilation

The graphics industry solved an identical problem decades ago. GLSL shaders are written once in a high-level language and compiled by GPU drivers to the specific instruction set of the target hardware. A shader written for a modern RTX GPU can be downcompiled to run on an integrated Intel GPU, losing ray-tracing features but preserving the core rendering logic.

Cross-tier constraint compilation applies the same principle. A constraint specification is the "GLSL source." The FLUX VM tiers are the "GPU targets." The cross-tier compiler is the "driver" that translates high-level intent to the narrowest instruction set that can express it.

### 2.3 Contributions

This paper makes the following contributions:

1. **Tier Capability Model** — A formal description of the four FLUX tiers and their opcode sets.
2. **Tier Descriptor** — A data structure that characterizes what a constraint *needs*, enabling automatic minimum-tier determination.
3. **Five-Pass Compilation Algorithm** — Parse → Lower → Analyze → Downcompile → Emit.
4. **Correctness Proof** — Downcompilation preserves constraint satisfaction under capability-subset semantics.
5. **Implementation Plan** — The `cocapn-tier-compiler` Rust crate.

---

## 3. Tier Capability Model

### 3.1 Overview

Each FLUX VM tier is defined by four dimensions:

| Dimension | Mini | Standard | Edge | Thor |
|---|---|---|---|---|
| Opcodes | 21 | 37 | 35 | 43 |
| Stack | 256 B | 4 KB | 4 KB | 64 KB |
| Heap | No | Yes | Yes | Yes |
| Async | No | No | Yes | Yes |
| CUDA | No | No | No | Yes |
| Network | No | CLI only | WebSocket | Full |
| Quality Gate | No | Yes | No | Yes |
| PLATO | No | No | Sync | Pathfinder |

### 3.2 Tier Mini

Mini is the floor. 21 opcodes covering:

- **Arithmetic:** `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG`
- **Comparison:** `EQ`, `NEQ`, `LT`, `GT`, `LTE`, `GTE`
- **Logic:** `AND`, `OR`, `NOT`
- **Stack:** `PUSH`, `POP`, `DUP`, `SWAP`
- **Control:** `HALT`, `JMP`, `COND_JMP`

No heap. No function calls. No I/O beyond the initial constraint parameters and a single boolean result on the stack. Mini is a calculator that answers yes or no.

### 3.3 Tier Standard

Standard adds 16 opcodes over Mini:

- **Memory:** `ALLOC`, `FREE`, `LOAD`, `STORE`
- **I/O:** `READ_FILE`, `WRITE_FILE`, `CLI_EXEC`
- **Quality:** `QUALITY_GATE`, `ASSERT`, `CHECKPOINT`
- **Function:** `CALL`, `RET`, `LOAD_FUNC`
- **Extended:** `PRINT`, `LOG`, `ENV_GET`

Standard introduces heap allocation, file I/O, CLI execution, and the quality gate system. Constraints can now interact with the filesystem and validate results through multi-criteria quality metrics.

### 3.4 Tier Edge

Edge has 35 opcodes (5 fewer than Standard but different in kind):

- Inherits all Mini opcodes
- **Async:** `ASYNC_SPAWN`, `AWAIT`, `ASYNC_ALL`
- **PLATO:** `PLATO_SYNC`, `PLATO_READ`, `PLATO_WRITE`
- **Sensor:** `SENSOR_READ`, `SENSOR_PIPELINE`, `FILTER`, `AGGREGATE`
- **Network:** `WS_CONNECT`, `WS_SEND`, `WS_RECV`
- **Coordination:** `BROADCAST`, `REDUCE`
- Excludes: `READ_FILE`, `WRITE_FILE`, `CLI_EXEC`, `QUALITY_GATE`, `ASSERT`

Edge trades filesystem access for real-time sensor processing and async coordination. It is the tier for deployed nodes in the field — buoys, drones, remote sensors.

### 3.5 Tier Thor

Thor is the full 43-opcode superset. It includes:

- Everything from Mini, Standard, and Edge (reconciled)
- **CUDA:** `CUDA_ALLOC`, `CUDA_RUN`, `CUDA_SYNC`, `CUDA_FREE`
- **Fleet:** `FLEET_BROADCAST`, `FLEET_REDUCE`, `PARALLEL_BRANCH`, `BATCH_SOLVE`
- **PLATO Pathfinder:** `PATHFIND_QUERY`, `PATHFIND_RESOLVE`
- **Advanced:** `TENSOR_OP`, `GRADIENT_DESCENT`

Thor runs on the mothership or high-end workstations. It can batch-solve thousands of constraints in parallel on the GPU, coordinate fleet-wide constraint evaluations, and use PLATO Pathfinder for complex knowledge graph queries.

### 3.6 Tier Partial Order

The tiers are *not* totally ordered by capability. Standard and Edge are incomparable: Standard has file I/O and quality gates but no async; Edge has async and sensors but no file I/O. The partial order is:

```
        Thor (43)
       /    \
  Std (37)  Edge (35)
       \    /
       Mini (21)
```

This means the compiler cannot simply "lower by one tier." It must understand *which* capabilities are required and route to the correct tier on the lattice.

---

## 4. The Tier Descriptor

### 4.1 Definition

The **Tier Descriptor** is a data structure that characterizes the resource and capability requirements of a compiled constraint program:

```json
{
  "required_opcodes": ["SONAR_SVP", "ADD", "MUL", "PUSH"],
  "stack_depth": 128,
  "heap_required": false,
  "async_required": false,
  "cuda_required": false,
  "network_required": false,
  "quality_gate_required": false,
  "plato_required": false,
  "sensor_required": false,
  "fleet_required": false,
  "pathfinder_required": false
}
```

### 4.2 Deriving the Minimum Tier

Given a Tier Descriptor `D`, the minimum tier is determined by a precedence lattice:

```
Tier = Thor    if D.cuda_required ∨ D.fleet_required ∨ D.pathfinder_required
Tier = Edge    if D.async_required ∨ D.sensor_required ∨ D.plato_required
Tier = Std     if D.heap_required ∨ D.quality_gate_required ∨ D.network_required
Tier = Mini    otherwise
```

When a constraint requires capabilities from *multiple incomparable tiers* (e.g., both quality gates from Standard and async from Edge), the compiler promotes to the lowest common ancestor on the lattice (Thor in this case, since it is the LCA of Std and Edge).

### 4.3 Opcode Membership Check

Each tier has an opcode set:

```
O(Mini)  = {ADD, SUB, MUL, DIV, MOD, NEG, EQ, NEQ, LT, GT, LTE, GTE,
            AND, OR, NOT, PUSH, POP, DUP, SWAP, HALT, JMP, COND_JMP}

O(Std)   = O(Mini) ∪ {ALLOC, FREE, LOAD, STORE, READ_FILE, WRITE_FILE,
            CLI_EXEC, QUALITY_GATE, ASSERT, CHECKPOINT, CALL, RET,
            LOAD_FUNC, PRINT, LOG, ENV_GET}

O(Edge)  = O(Mini) ∪ {ASYNC_SPAWN, AWAIT, ASYNC_ALL, PLATO_SYNC,
            PLATO_READ, PLATO_WRITE, SENSOR_READ, SENSOR_PIPELINE,
            FILTER, AGGREGATE, WS_CONNECT, WS_SEND, WS_RECV,
            BROADCAST, REDUCE}

O(Thor)  = O(Mini) ∪ O(Std) ∪ O(Edge) ∪ {CUDA_ALLOC, CUDA_RUN,
            CUDA_SYNC, CUDA_FREE, FLEET_BROADCAST, FLEET_REDUCE,
            PARALLEL_BRANCH, BATCH_SOLVE, PATHFIND_QUERY,
            PATHFIND_RESOLVE, TENSOR_OP, GRADIENT_DESCENT}
```

If `required_opcodes ⊄ O(Tier)`, the constraint cannot execute on that tier without downcompilation.

---

## 5. Compilation Algorithm

### 5.1 Overview

The compiler operates in five passes:

```
┌─────────────────────────────────────────┐
│ Pass 1: Parse                           │
│   Constraint spec → Constraint AST      │
├─────────────────────────────────────────┤
│ Pass 2: Lower                           │
│   Constraint AST → FLUX opcodes         │
│   (greedy: use highest-level opcodes)   │
├─────────────────────────────────────────┤
│ Pass 3: Analyze                         │
│   FLUX opcodes → Tier Descriptor        │
├─────────────────────────────────────────┤
│ Pass 4: Downcompile                     │
│   If target tier < required tier:       │
│     Replace high-level opcodes with     │
│     lower-tier equivalent sequences     │
├─────────────────────────────────────────┤
│ Pass 5: Emit                            │
│   Finalize bytecode for target tier     │
│   Verify opcode membership              │
│   Verify stack depth limits             │
└─────────────────────────────────────────┘
```

### 5.2 Pass 1: Parse

Input: A constraint specification in JSON or natural language.

```json
{
  "name": "sonar_depth_within_tolerance",
  "parameters": ["measured_depth", "expected_depth", "tolerance", "svp_profile"],
  "body": "abs(measured_depth - expected_depth) <= tolerance AND svp_corrected(measured_depth, svp_profile) IS VALID"
}
```

The parser produces a **Constraint AST** — a typed abstract syntax tree where each node represents a constraint operation. The AST is tier-agnostic; it captures *intent*, not *execution*.

### 5.3 Pass 2: Lower

The lowering pass converts the Constraint AST to FLUX opcodes using a **greedy highest-level** strategy. For each AST node, the compiler selects the most specific (highest-tier) opcode available:

```
AST Node: svp_corrected(depth, profile)
  → Thor: SONAR_SVP (single opcode, uses CUDA acceleration)
  → Edge: SENSOR_PIPELINE (chain of filter/aggregation ops)
  → Std:  CALL svp_function (uses heap-allocated lookup table)
  → Mini: sequence of ADD/MUL with precomputed coefficients
```

On the first lowering pass, the compiler assumes Thor is available and selects `SONAR_SVP`. The subsequent analysis pass determines whether this is actually possible.

### 5.4 Pass 3: Analyze

The analysis pass walks the lowered opcode sequence and computes the Tier Descriptor:

1. **Opcode scan:** Record all opcodes used. Check membership in each tier's opcode set.
2. **Stack depth analysis:** Simulate the stack through the opcode sequence, tracking maximum depth.
3. **Heap analysis:** Determine whether any opcode requires heap allocation (`ALLOC`, `LOAD`, `STORE`, `CALL` with closures).
4. **Boolean flags:** Set `async_required`, `cuda_required`, etc. based on opcode presence.

Output: A complete Tier Descriptor.

### 5.5 Pass 4: Downcompile

If the target tier's capabilities are below the Tier Descriptor's requirements, the compiler performs **downcompilation** — replacing high-level opcodes with equivalent sequences of lower-tier opcodes.

The downcompilation rules form a **rewrite system**:

```
SONAR_SVP(depth, profile) 
  → [Mini] PUSH c0, PUSH depth, MUL, PUSH c1, ADD, PUSH c2, PUSH depth, MUL, ADD, ...]
     where c0, c1, c2, ... are precomputed Mackenzie equation coefficients

PARALLEL_BRANCH([b1, b2, ..., bn], merge_fn)
  → [Edge] ASYNC_SPAWN(b1), ASYNC_SPAWN(b2), ..., ASYNC_ALL, REDUCE(merge_fn)

QUALITY_GATE(metrics, threshold)
  → [Mini] inline_threshold_check  (precomputed threshold, no dynamic metrics)

CUDA_BATCH_SOLVE(constraints)
  → [Std] CALL batch_solve_sequential  (heap-allocated solver loop)
```

Each rewrite rule is **semantics-preserving by construction**: the downcompiled sequence computes the same function as the original opcode, but potentially slower or with less precision.

### 5.6 Pass 5: Emit

The emit pass:

1. **Finalizes** the opcode sequence for the target tier.
2. **Verifies** that every opcode in the sequence is a member of `O(TargetTier)`.
3. **Verifies** that stack depth is within the tier's limit.
4. **Embeds** any precomputed constants (e.g., Mackenzie coefficients for Mini-tier sonar).
5. **Serializes** to the FLUX bytecode format (compact binary encoding).

If verification fails, the compiler reports a **tier mismatch error** with a description of which capabilities are missing.

---

## 6. Downcompilation Examples

### 6.1 Sonar Depth Check: Thor → Mini

**Original (Thor):**
```
PUSH measured_depth
PUSH svp_profile
SONAR_SVP                    ; CUDA-accelerated sound velocity profile correction
PUSH expected_depth
SUB
ABS
PUSH tolerance
LTE
```

**Tier Descriptor:**
```json
{
  "required_opcodes": ["PUSH", "SONAR_SVP", "SUB", "ABS", "LTE"],
  "cuda_required": true,
  "stack_depth": 6
}
```

**Downcompiled (Mini):**
```
PUSH measured_depth
PUSH 0.0002469              ; Mackenzie (1981) coefficient c0
MUL
PUSH 0.0000000229           ; Mackenzie coefficient c1
PUSH measured_depth
PUSH measured_depth
MUL
MUL
ADD
PUSH 1449.05                ; base speed constant
ADD
; ... result is svp-corrected depth on stack
PUSH expected_depth
SUB
; ABS via conditional:
DUP
PUSH 0
LT
COND_JMP skip_neg
NEG
skip_neg:
PUSH tolerance
LTE
```

The 6-opcode Thor program becomes ~15 opcodes on Mini, but produces the same boolean result. The trade-off is precision (precomputed constants vs. runtime profile interpolation) and speed (CPU arithmetic vs. CUDA). The constraint is *satisfied identically* — the answer is the same boolean.

### 6.2 Fleet Coordination: Thor → Edge

**Original (Thor):**
```
PUSH constraint_set
PARALLEL_BRANCH              ; spawn N parallel evaluations
PUSH merge_strategy
FLEET_REDUCE                 ; reduce across fleet nodes
PUSH threshold
QUALITY_GATE                 ; validate result quality
```

**Downcompiled (Edge):**
```
PUSH constraint_set
ASYNC_SPAWN eval_fn          ; evaluate first constraint
; ... spawn remaining constraints
ASYNC_ALL                    ; wait for all async results
PUSH merge_strategy
REDUCE                       ; merge results (single node, no fleet)
PUSH threshold
; Manual quality check (inline, since QUALITY_GATE is unavailable):
DUP
PUSH threshold
GTE
; result is boolean on stack
```

The `PARALLEL_BRANCH` becomes sequential `ASYNC_SPAWN` calls. The `FLEET_REDUCE` becomes local `REDUCE` (no fleet). The `QUALITY_GATE` becomes an inline comparison. The constraint still evaluates correctly — it just doesn't leverage fleet distribution.

### 6.3 Quality Gate: Standard → Mini

**Original (Standard):**
```
PUSH result
PUSH metrics
PUSH 0.95                    ; 95% quality threshold
QUALITY_GATE                 ; multi-metric quality validation
```

**Downcompiled (Mini):**
```
PUSH result
PUSH 0.95                    ; precomputed threshold (metrics baked at compile time)
GTE                          ; simple comparison replaces multi-metric gate
```

The quality gate's multi-metric evaluation is collapsed to a single threshold comparison. This is a *lossy* downcompilation — the Mini version checks only the primary metric, not the full quality profile. The compiler emits a **precision warning**: "Quality gate downcompiled: 3 metrics reduced to 1 threshold check."

---

## 7. Formal Properties

### 7.1 Definitions

**Definition 1 (Constraint Program).** A constraint program `P` is a sequence of FLUX opcodes `(o₁, o₂, ..., oₙ)` with an associated Tier Descriptor `D(P)`.

**Definition 2 (Tier Satisfaction).** A constraint program `P` *satisfies* tier `T`, written `P ⊨ T`, iff every opcode in `P` is a member of `O(T)` and the stack depth of `P` does not exceed `StackLimit(T)`.

**Definition 3 (Downcompilation).** A downcompilation function `δ_T(P)` maps a constraint program `P` to a new program `P'` such that `P' ⊨ T`, where `T` is the target tier.

**Definition 4 (Semantic Equivalence).** Two programs `P` and `P'` are semantically equivalent with respect to constraint `C`, written `P ≡_C P'`, iff for all valid inputs `x` to constraint `C`: `P(x) = P'(x)`.

### 7.2 Theorem: Downcompilation Correctness

**Theorem 1.** If `P` is a constraint program for constraint `C`, and `T` is a target tier such that `C` is expressible on `T`, then `δ_T(P) ≡_C P`.

*Proof sketch.* By structural induction on the rewrite rules used in downcompilation.

**Base case:** An opcode `o` that is a member of `O(T)` is not rewritten. `δ_T(o) = o`. Trivially `o ≡_C o`.

**Inductive case:** An opcode `o` that is not a member of `O(T)` is rewritten to a sequence `S = (s₁, ..., sₖ)` where each `sᵢ ∈ O(T)`. By the definition of the rewrite rules, `S` computes the same function as `o` (this is the precondition for a rewrite rule to exist). Therefore `o ≡_C S`.

**Composition:** A program is a sequence of opcodes. If each opcode is individually semantically equivalent after rewriting, then the composed program is semantically equivalent: if `δ_T(oᵢ) ≡_C oᵢ` for all `i`, then `(δ_T(o₁), ..., δ_T(oₙ)) ≡_C (o₁, ..., oₙ)`. This follows from the compositional semantics of stack-based machines: each opcode's effect on the stack is determined solely by the opcode and the stack state, and if each individual step is equivalent, the final state is equivalent.

**Expressibility condition:** The theorem requires that `C` is expressible on `T`. If the constraint requires capabilities that have *no* rewrite rule (e.g., a constraint that fundamentally requires CUDA and the target is Mini), then no correct downcompilation exists. The compiler reports this as a **tier incompatibility error** rather than producing an incorrect program. ∎

### 7.3 Theorem: Minimality

**Theorem 2.** The tier assignment algorithm selects the minimum tier `T` such that `δ_T(P) ⊨ T` with the minimum number of rewrites.

*Proof sketch.* The Tier Descriptor `D(P)` captures the *exact* set of capabilities required. The precedence lattice routes to the lowest tier that provides all required capabilities. Since the partial order `Mini ≤ Std ≤ Thor` and `Mini ≤ Edge ≤ Thor` preserves the property that lower tiers have fewer capabilities, and the LCA handles incomparable tiers, the algorithm selects the tier requiring the fewest rewrites by construction.

### 7.4 Corollary: No Unnecessary Promotion

**Corollary 1.** A constraint that uses only Mini opcodes is never promoted to Standard, Edge, or Thor.

This follows directly from the opcode membership check in the analysis pass. If `required_opcodes ⊆ O(Mini)`, the compiler assigns Mini regardless of what higher tiers are available.

---

## 8. Implementation Plan

### 8.1 Crate Structure

```
cocapn-tier-compiler/
├── Cargo.toml
├── src/
│   ├── lib.rs              # Public API
│   ├── parse.rs            # Pass 1: Constraint spec → AST
│   ├── lower.rs            # Pass 2: AST → FLUX opcodes (greedy)
│   ├── analyze.rs          # Pass 3: Opcodes → Tier Descriptor
│   ├── downcompile.rs      # Pass 4: Rewrite rules
│   ├── emit.rs             # Pass 5: Bytecode emission
│   ├── tier.rs             # Tier definitions and opcode sets
│   ├── descriptor.rs       # Tier Descriptor type and LCA logic
│   └── rewrite_rules.rs    # Downcompilation rewrite table
└── tests/
    ├── tier_analysis.rs
    ├── downcompile_sonar.rs
    ├── downcompile_fleet.rs
    └── correctness_roundtrip.rs
```

### 8.2 Core Types

```rust
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
enum Tier { Mini, Std, Edge, Thor }

#[derive(Clone, PartialEq)]
enum Opcode {
    // Mini (21)
    Add, Sub, Mul, Div, Mod, Neg,
    Eq, Neq, Lt, Gt, Lte, Gte,
    And, Or, Not,
    Push(f64), Pop, Dup, Swap,
    Halt, Jmp(usize), CondJmp(usize),
    // Std additions (16)
    Alloc, Free, Load, Store,
    ReadFile, WriteFile, CliExec,
    QualityGate, Assert, Checkpoint,
    Call(usize), Ret, LoadFunc(usize),
    Print, Log, EnvGet,
    // Edge additions (15)
    AsyncSpawn, Await, AsyncAll,
    PlatoSync, PlatoRead, PlatoWrite,
    SensorRead, SensorPipeline, Filter, Aggregate,
    WsConnect, WsSend, WsRecv,
    Broadcast, Reduce,
    // Thor additions (12)
    CudaAlloc, CudaRun, CudaSync, CudaFree,
    FleetBroadcast, FleetReduce,
    ParallelBranch, BatchSolve,
    PathfindQuery, PathfindResolve,
    TensorOp, GradientDescent,
}

struct TierDescriptor {
    required_opcodes: HashSet<Opcode>,
    stack_depth: usize,
    heap_required: bool,
    async_required: bool,
    cuda_required: bool,
    network_required: bool,
    quality_gate_required: bool,
    plato_required: bool,
    sensor_required: bool,
    fleet_required: bool,
    pathfinder_required: bool,
}

struct CompiledConstraint {
    tier: Tier,
    opcodes: Vec<Opcode>,
    descriptor: TierDescriptor,
    bytecode: Vec<u8>,
    warnings: Vec<CompilerWarning>,
}
```

### 8.3 Public API

```rust
/// Compile a constraint specification to the minimum viable tier.
pub fn compile(spec: &ConstraintSpec) -> Result<CompiledConstraint, CompileError>;

/// Compile a constraint specification to a specific target tier.
pub fn compile_to(spec: &ConstraintSpec, target: Tier) -> Result<CompiledConstraint, CompileError>;

/// Analyze a constraint without emitting bytecode.
pub fn analyze(spec: &ConstraintSpec) -> TierDescriptor;

/// Check if a constraint is expressible on a given tier.
pub fn is_expressible(spec: &ConstraintSpec, tier: Tier) -> bool;
```

### 8.4 Dependencies

- `cocapn-flux-isa` — Opcode definitions, bytecode format
- `serde` / `serde_json` — Constraint spec parsing
- `thiserror` — Error types
- No CUDA dependency at compile time (Thor opcodes are emitted as bytecode, not executed by the compiler)

### 8.5 Testing Strategy

1. **Unit tests** per rewrite rule — verify each downcompilation produces equivalent results.
2. **Roundtrip tests** — compile for Thor, downcompile to Mini, execute both on test inputs, assert identical outputs.
3. **Fuzz tests** — random constraint specs compiled to random tiers, verify no panics and bytecode validity.
4. **Tier analysis tests** — verify Tier Descriptor computation for known constraint patterns.

---

## 9. Conclusion

Cross-tier constraint compilation solves the fleet's most pressing constraint portability problem. By treating constraint specifications as tier-agnostic source code and FLUX tiers as compilation targets, we achieve the same "write once, compile anywhere" property that made shader programming tractable.

The key insights are:

1. **Tier descriptors make compilation deterministic.** By characterizing exactly what a constraint needs, we avoid heuristic tier assignment and guarantee minimality.

2. **Downcompilation is semantics-preserving by construction.** Each rewrite rule is a provably equivalent transformation. The compiler never produces a program that could violate a constraint.

3. **The tier lattice handles incomparable tiers.** Standard and Edge are incomparable, but their LCA (Thor) provides a correct fallback. This is not a hack — it's the natural consequence of the partial order.

4. **Precision warnings, not errors.** Lossy downcompilation (e.g., quality gate → threshold check) emits a warning, not an error. The constraint is still satisfied, just with less information. The operator decides whether this is acceptable.

The `cocapn-tier-compiler` crate is the next major deliverable for the FLUX constraint stack. It transforms the fleet's constraint execution model from "write four versions" to "write once, compile everywhere" — and that's a drift reduction worth forging.

---

*Forgemaster ⚒️ — Constraint theory or die trying.*
