# FLUX ISA: A Constraint Compilation Architecture for Autonomous Systems

**White Paper — Cocapn Fleet**  
**Version 1.0 — May 2026**

---

## Abstract

Autonomous systems face a fundamental trust gap: constraints are verified after computation, when violations are already costly. We present the FLUX Instruction Set Architecture, a stack-based virtual machine that compiles constraint satisfaction problems into deterministic bytecodes. Constraints become first-class instructions—ASSERT, CHECK, VALIDATE, REJECT—executed at every VM step, not post-hoc. The architecture deploys across four tiers: bare-metal microcontrollers (21 opcodes, 256 bytes SRAM), embedded Linux nodes (35+ opcodes, heap allocation), edge GPUs with async pipelines and PLATO knowledge integration, and data-center nodes with CUDA batch solving and fleet coordination. Wrong answers become compilation errors. The system is deployed in production: PLATO's quality gate rejects ~15% of 18,633 knowledge tiles at ingress, sonar physics constraints validate sensor data at the MCU boundary, and the CUDA FFI bridge solves independent CSP problems in parallel across 512 GPU cores. Published on crates.io, PyPI, and npm.

---

## 1. Introduction

### 1.1 The Trust Gap

Autonomous systems—underwater robots, satellite constellations, distributed sensor networks—must satisfy safety constraints in environments where a single undetected violation propagates catastrophically. Traditional approaches treat constraint checking as a post-processing step: compute a result, then validate it. This creates a temporal gap between computation and verification, during which invalid state may already have influenced downstream decisions.

The problem compounds at scale. A fleet of sensor nodes generating thousands of readings per second cannot afford to forward data through a validation pipeline only to discard it later. The cost of wrong data is not just computation—it's trust propagation through the entire knowledge graph.

### 1.2 Why Post-Hoc Validation Fails

Post-hoc validation suffers from three structural weaknesses:

1. **Temporal gap**: Between computation and validation, invalid state may influence other processes.
2. **Selective application**: Validation is typically applied at system boundaries, not at every computation step.
3. **Semantic distance**: The mapping between "this value is wrong" and "this constraint was violated" is often ambiguous, making provenance difficult to trace.

Rule engines and policy frameworks attempt to close this gap but introduce their own problems: they're interpreted (slow), non-deterministic in complex rule interactions, and difficult to formally verify.

### 1.3 Our Contribution

FLUX treats constraint satisfaction as a compilation target. Constraints are compiled into bytecodes that execute on a deterministic stack-based virtual machine. The key insight: if constraints are instructions, not predicates, then the VM *cannot produce invalid state* without detecting it at the instruction that caused the violation.

This paper describes the FLUX ISA, its four-tier deployment architecture, the PLATO knowledge integration layer, and the CUDA-accelerated batch CSP solver. Every claim is backed by code we have shipped.

---

## 2. Architecture Overview

### 2.1 Four-Tier Deployment

The FLUX architecture spans four deployment targets, each with a progressively richer instruction set:

| Tier | Crate | Target | Opcodes | Stack | Heap |
|------|-------|--------|---------|-------|------|
| 1 — MCU | `flux-isa-mini` | ARM Cortex-M0+/M3/M4, `no_std` | 21 | 256 B (32 × f64) | None |
| 2 — Embedded Linux | `flux-isa-std` | Raspberry Pi, BeagleBone, Jetson Nano | 35+ | 4096 × f64 | 64K memory |
| 3 — Edge GPU | `flux-isa-edge` | Jetson Xavier, async pipelines | 35 + PLATO integration | Configurable | Full |
| 4 — Data Center | `flux-isa-thor` | Jetson Thor, CUDA + fleet | 43 (35 base + 8 Thor-extended) | 65,536 | Full + GPU |

Each tier shares the same core semantics: stack-based execution, constraint opcodes at every level, and deterministic execution traces. A program compiled for Tier 1 will execute identically on Tier 4 (minus Tier 4-only extensions).

### 2.2 The Constraint VM

All tiers implement the same fundamental execution model:

1. A **stack** of `f64` values (fixed-size on Tier 1, growable on Tiers 2–4)
2. An **instruction pointer** stepping through a flat bytecode array
3. **Constraint opcodes** that check stack values and record pass/fail
4. An **execution trace** capturing every step for provenance

Constraint violations are immediate: `ASSERT` pops and checks, failing the entire program if the value is zero. `CHECK` is non-consuming (peek, not pop), allowing constraint verification without destroying intermediate results. `VALIDATE` performs range checking against explicit bounds. `REJECT` unconditionally marks the program as failed.

### 2.3 Knowledge Integration: PLATO

PLATO is the persistent constraint store—a knowledge graph organized into rooms of tiles, where each tile is a Q&A pair with confidence, provenance, and content hashing. The PLATO quality gate rejects tiles containing absolute claims ("always", "never", "impossible"), enforces minimum content lengths, and deduplicates via SHA-256 content hashing. The gate runs at the FLUX VM level: constraint compilation ensures that only validated knowledge enters the system.

---

## 3. The FLUX Instruction Set

### 3.1 Opcode Groups

The full ISA (flux-isa) defines 35 opcodes across 8 groups, identified by their high nibble:

```
0x0n  ARITHMETIC: Add, Sub, Mul, Div, Mod
0x1n  CONSTRAINT: Assert, Check, Validate, Reject
0x2n  FLOW:       Jump, Branch, Call, Return, Halt
0x3n  MEMORY:     Load, Store, Push, Pop, Swap
0x4n  CONVERT:    Snap, Quantize, Cast, Promote
0x5n  LOGIC:      And, Or, Not, Xor
0x6n  COMPARE:    Eq, Neq, Lt, Gt, Lte, Gte
0x7n  SPECIAL:    Nop, Debug, Trace, Dump
```

Tier 1 (`flux-isa-mini`) strips this to 21 essential opcodes with remapped encoding (e.g., `Halt = 0xF0`, `Nop = 0xFF`) to simplify the decode table on constrained targets.

### 3.2 CONSTRAINT Opcodes: The Safety Core

Four opcodes form the constraint enforcement layer:

- **ASSERT** (`0x10`): Pops a value. If zero, immediately returns `ConstraintViolation`. This is the hard gate—use it for invariants that must never be violated.
- **CHECK** (`0x11`): Peeks at the top of stack without consuming it. Records pass/fail but does not halt on failure. Use for soft constraints where execution should continue to capture more context.
- **VALIDATE** (`0x12`): Pops a value and checks it against `[min, max]` bounds provided as operands. Pushes `1.0` (pass) or `0.0` (fail) back onto the stack, allowing downstream logic to branch on the result.
- **REJECT** (`0x13`): Unconditional failure. The program is marked as constraint-violated but continues executing (Tier 1) or halts immediately (full ISA). Use for explicit rejection points in validation pipelines.

The semantics differ slightly across tiers. In `flux-isa-mini` (Tier 1), `CHECK` is non-consuming—it peeks without popping. In `flux-isa` (reference), `CHECK` pops and pushes the boolean result. These differences are deliberate: Tier 1 optimizes for stack conservation (32 slots total), while the full ISA optimizes for composability.

### 3.3 CONVERT Opcodes: Mapping Continuous to Discrete Constraint Space

- **SNAP** (`0x40`): Rounds the top-of-stack to the nearest integer. In the C implementation, SNAP snapshots the top-of-stack to the output stream—demonstrating how the same opcode can carry tier-specific semantics for domain adaptation.
- **QUANTIZE** (`0x41`): Rounds a value to a given step size: `round(val / step) * step`. Essential for mapping continuous sensor readings to discrete constraint domains (e.g., quantizing depth to 0.5m bins for constraint checking).

### 3.4 Binary Encoding Format

Each instruction is encoded as:

```
+--------+--------+--------+--------+
| opcode | argc   | flags  | rsvd   |   4 bytes header
+--------+--------+--------+--------+
|          operand[0] (8 bytes LE)   |   f64
+------------------------------------+
|          operand[1] (8 bytes LE)   |   f64
+------------------------------------+
```

The header is fixed at 4 bytes (opcode, operand count, flags, reserved), followed by `argc × 8` bytes of little-endian `f64` operands. The `encoded_size()` method computes `4 + operands.len() * 8`. A `FluxBytecode` object wraps a `Vec<FluxInstruction>` with `encode()`/`decode()` for the binary format, `validate()` for static correctness checks (jump target bounds, stack effect analysis, terminal instruction requirement), and `disassemble()` for human-readable output.

The `flux-isa-std` Tier 2 adds a container format: magic bytes `FLUX` (`0x46 0x4C 0x55 0x58`), version (`u16` LE), instruction count (`u32` LE), followed by the instruction payload. This supports file persistence, JSON serialization via serde, and round-trip `save_to_file()` / `load_from_file()`.

---

## 4. The Constraint VM

### 4.1 Stack-Based Execution Model

All VM implementations share the same execution loop:

```
while ip < instructions.len():
    instr = instructions[ip]
    stack_before = stack.clone()      // for tracing
    match instr.opcode:
        Add => pop b, pop a, push (a + b)
        Assert => pop val, if val == 0: return ConstraintViolation
        ...
    trace.push(TraceEntry { step, opcode, stack_before, stack_after })
    ip++
```

The stack holds `f64` values exclusively. Binary operations pop two values and push one. Comparison and logic operations push `1.0` (true) or `0.0` (false). The `binop` helper abstracts the pattern, reducing the match arms to one-liners.

### 4.2 Constraint Checking at Each Step

The key design decision: constraint opcodes are not separate from computation. A program like:

```
LOAD 1500.0       ; sound speed reading
VALIDATE 1430 1560 ; Mackenzie bounds
ASSERT            ; must pass
LOAD 200.0        ; depth reading
VALIDATE 0 1000   ; depth bounds
ASSERT
HALT
```

interleaves data loading, constraint checking, and assertion. The execution trace records every step, including the constraint result (`Some(true)` or `Some(false)`), providing complete provenance for any downstream audit.

### 4.3 Execution Tracing

Every tier produces execution traces. The structure varies by capability:

- **Tier 1** (`flux-isa-mini`): No trace buffer (too expensive for 8KB SRAM). Returns only `steps_executed` count and `constraints_satisfied` boolean.
- **Tier 2** (`flux-isa-std`): `ExecutionTrace` records per-step `{ instruction_index, opcode, stack_before, stack_after }` when `trace_enabled: true` in `VMConfig`.
- **Tier 3** (`flux-isa-edge`): Traces flow through async pipelines, including sensor stream ingestion timestamps.
- **Tier 4** (`flux-isa-thor`): `TraceEntry` includes nanosecond-precision timestamps (`timestamp_ns: u64`), stack depth, and opcode mnemonic, with configurable max trace length (default 1M entries).

The C implementation (`flux-isa-c`) captures stack snapshots of 8 entries (`FLUX_TRACE_SNAPSHOT = 8`) per trace entry, stored in a caller-allocated buffer of 1024 entries. This is a practical compromise: full stack cloning is too expensive, but 8 entries capture enough context for provenance.

### 4.4 Cross-Implementation Comparison

| Feature | Rust (flux-isa) | C (flux-isa-c) | Mini (flux-isa-mini) |
|---------|-----------------|----------------|----------------------|
| Stack | `Vec<f64>`, growable | `double[256]`, fixed | `f64[32]`, fixed |
| Call stack | `Vec<usize>` | `int[64]` | Not available |
| Memory | N/A | `registers[16]` | N/A |
| Division by zero | `FluxError::ArithmeticError` | Return code `-2` | `FluxError::DivisionByZero` |
| Constraint failure | `FluxError::ConstraintViolation(msg)` | `constraint_failures++` | `FluxError::ConstraintViolation` |
| Trace | Full `Vec<TraceEntry>` | Fixed buffer, 8-deep snapshots | None (count only) |
| Assert semantics | Halt on violation | Continue (count failures) | Halt on violation |
| `SNAP` | Round to nearest | Push to output stream | Round via `libm::round` |

The C implementation is the most permissive: ASSERT does not halt, it increments `constraint_failures`. This is intentional for embedded C contexts where the caller decides how to handle violations after the full program runs. The Rust implementations halt on ASSERT failure, failing fast.

---

## 5. Multi-Tier Deployment

### 5.1 Tier 1: flux-isa-mini (MCU)

Target: ARM Cortex-M0+/M3/M4 with 8KB SRAM. The `#![no_std]` crate uses no heap allocation.

**Stack:** 32 × `f64` = 256 bytes. The `FluxVm` struct is `const fn` constructible:

```rust
pub const fn new() -> Self {
    Self { stack: [0.0; STACK_SIZE], sp: 0 }
}
```

**Opcodes:** 21 operations, stripped from the full 35. No flow control (no Jump, Branch, Call, Return)—only Halt and Nop. No logic opcodes (And, Or, Not, Xor). The opcode encoding is remapped to reduce the decode table:

```rust
Assert = 0x20,  Check = 0x21,  Validate = 0x22,  Reject = 0x23
```

This allows the `from_u8()` match to compile to a compact jump table on Thumb-2.

**Sonar constraint checks:** The `sonar_check` module provides `const fn` validators for underwater sonar deployments:

```rust
pub const SOUND_SPEED_MIN: f64 = 1430.0;  // Mackenzie 1981 lower bound
pub const SOUND_SPEED_MAX: f64 = 1560.0;  // Mackenzie 1981 upper bound

pub const fn check_sound_speed(c: f64, min: f64, max: f64) -> bool {
    c >= min && c <= max
}
```

These are compile-time evaluated where possible, generating FLUX bytecode that validates sensor readings against Mackenzie 1981 sound speed bounds (1430–1560 m/s at 0–1000m depth, 0–35‰ salinity, −2–30°C) and Francois-Garrison 1982 absorption ranges, before forwarding data upstream.

### 5.2 Tier 2: flux-isa-std (Embedded Linux)

Target: Raspberry Pi, BeagleBone, NanoPi, Jetson Nano. Full `std`, heap allocation, file I/O.

The `FluxVM` adds:

- **Memory space**: 65,536 × `f64` addressable via `Load`/`Store` opcodes
- **Stack manipulation**: `Dup`, `Over`, `Rot`, `Depth` beyond basic `Push`/`Pop`/`Swap`
- **Flow control**: `Jmp`, `Call`, `Ret` with 256-deep call stack
- **I/O**: `Print`, `Emit` for output
- **Step-by-step execution**: `step()` method returns `Ok(true)` if more steps available
- **Bytecode container**: Magic header (`FLUX`), version, JSON serialization, file persistence
- **Quality gate**: `QualityGate` with configurable rules (minimum length, absolute claim rejection, required fields, numeric bounds)

The `VMConfig` defaults to 4,096 max stack, 256 max call depth, 65,536 memory slots, and 1,000,000 max instructions (gas limit). The bytecode validator performs static analysis: jump target bounds checking, stack effect analysis (minimum depth tracking), and terminal instruction verification.

### 5.3 Tier 3: flux-isa-edge (Jetson Xavier)

Target: Jetson Xavier NX (512 CUDA cores, 8GB unified memory). Built on `tokio` async runtime.

The edge tier adds:

- **Async execution pipeline**: Axum HTTP server with `/execute`, `/validate`, `/status` endpoints
- **WebSocket streaming**: Real-time constraint checking on sensor data streams
- **PLATO sync**: Bidirectional tile synchronization with the persistent knowledge store
- **Sensor integration**: Dedicated sensor stream handlers for sonar physics pipelines

The server tracks `tiles_processed` and `constraint_violations` atomically, providing real-time fleet health monitoring. Each execution request carries optional `ExecutionLimits` for resource control.

### 5.4 Tier 4: flux-isa-thor (Jetson Thor)

Target: Jetson Thor with CUDA acceleration and fleet coordination. 43 opcodes: 35 base + 8 Thor-extended.

**Thor-extended opcodes:**

```
0x80  ParallelBranch  — fork execution into parallel branches
0x81  Reduce          — merge parallel branch results
0x82  GpuCompile      — compile constraint kernel for GPU execution
0x83  BatchSolve      — batch CSP solve on GPU
0x84  SonarBatch      — batch sonar physics computation
0x85  TileCommit      — commit results to PLATO knowledge store
0x86  Pathfind        — PLATO room traversal for knowledge discovery
0x87  ExtendedEnd     — end of Thor extension space
```

The `ThorVm` holds handles to three subsystems: `GpuDispatcher` (CUDA), `PlatoHandle` (knowledge store), and `FleetHandle` (fleet coordination). The `BatchSolve` opcode invokes the CUDA FFI bridge to solve multiple independent CSP problems in parallel—each thread block handles one problem instance, exploring its domain space simultaneously.

The `Value` type is polymorphic: `F64(f64)`, `I64(i64)`, `Bool(bool)`, `Str(String)`, `Bytes(Vec<u8>)`, `Nil`. This is a significant expansion from the f64-only stacks of Tiers 1–3, enabling richer constraint expressions (string matching, binary blob validation) at the data center tier.

Execution traces include nanosecond-precision timestamps for temporal provenance, enabling post-hoc reconstruction of exactly when each constraint was evaluated relative to real-world events.

---

## 6. PLATO Integration

### 6.1 The Quality Gate

PLATO's quality gate is implemented in two layers: a local gate in `flux-isa-std` and a full gate in `plato-engine`. Both reject tiles containing absolute claims, enforce minimum content lengths, and deduplicate via content hashing.

The `plato-engine` gate uses regex-based detection with context awareness: absolute claim patterns ("always", "never", "impossible", "guaranteed", "100%") are detected via `Regex` matching, but claims inside quoted strings are exempted. The `is_in_quotes()` heuristic counts quote characters before the match position—if odd, the match is inside a quoted string.

Gate evaluation is a pipeline:

1. **Field validation**: All required fields present, confidence in [0.0, 1.0]
2. **Length checks**: Question ≥ 3 chars, answer ≥ 10 chars
3. **Absolute claim detection**: Regex scan with quote-context exemption
4. **Duplicate detection**: SHA-256 content hash against existing room hashes

### 6.2 The Tile

A PLATO tile is the fundamental knowledge unit:

```rust
pub struct Tile {
    pub id: Uuid,
    pub domain: String,
    pub question: String,
    pub answer: String,
    pub source: String,
    pub confidence: f64,
    pub tags: Vec<String>,
    pub created_at: i64,
    pub provenance: Provenance,
}
```

Content hashing (`domain + question + answer + source`) provides deduplication independent of metadata. Provenance tracks agent ID, session ID, chain hash, and signature for full auditability.

### 6.3 The Engine

`PlatoEngine` uses `DashMap` for thread-safe concurrent room access. Statistics are tracked via lock-free atomics:

```rust
total_submitted: AtomicU64,
total_accepted: AtomicU64,
total_rejected: AtomicU64,
rejection_reasons: DashMap<String, AtomicU64>,
```

In production: 18,633 tiles submitted, ~15% rejected at the gate, primarily for absolute claims and insufficient content length.

### 6.4 Pathfinder: Confidence-Weighted Traversal

The `Pathfinder` builds an adjacency graph from room cross-references (shared tags and domains). Edge strength is computed as `shared_tag_count + domain_bonus(0.5)`. BFS finds shortest paths between rooms; DFS traverses strongest connections first (sorted by strength descending). This enables knowledge discovery across rooms: a constraint compiled for one domain can find related constraints in adjacent rooms via pathfinding.

---

## 7. Comparison with Existing Systems

### 7.1 vs LlamaIndex / RAG Systems

LlamaIndex and similar retrieval-augmented generation systems treat knowledge as a retrieval problem: query → embed → retrieve → generate. FLUX treats knowledge as a compilation problem: constraints are compiled into bytecodes that execute deterministically. There is no retrieval step, no embedding similarity, no stochastic ranking. A constraint either passes or fails at the VM level.

### 7.2 vs LangGraph / Agent Frameworks

LangGraph orchestrates agent workflows as directed graphs with conditional edges. FLUX compiles constraint logic into flat bytecodes executed on a simple stack machine. The tradeoff: LangGraph is more expressive for workflow orchestration; FLUX is more verifiable for constraint enforcement. A FLUX program has no hidden state, no async side effects at the VM level, and a complete execution trace.

### 7.3 vs Traditional Safety Systems (Rule Engines)

Rule engines (Drools, Jess, business rule frameworks) evaluate rules against a working memory using pattern matching (Rete algorithm). FLUX evaluates constraint opcodes against a stack using direct dispatch. Rule engines are Turing-complete and can exhibit non-obvious interaction effects. FLUX is deliberately not Turing-complete at Tier 1 (no unbounded loops) and strongly bounded at higher tiers (gas limits, max instructions).

---

## 8. Results

### 8.1 PLATO Knowledge Store

- **18,633 tiles** across multiple domain rooms
- **~15% gate rejection rate**, primarily absolute claims ("always", "never") and insufficient content length
- **Zero duplicate tiles** accepted (SHA-256 deduplication)
- **Thread-safe concurrent access** via DashMap, handling fleet-wide tile submissions

### 8.2 Published Packages

The FLUX ISA ecosystem is published across three package registries:

- **crates.io**: `flux-isa`, `flux-isa-mini`, `flux-isa-std`, `plato-engine`, `constraint-theory-core`
- **PyPI**: Python bindings for the FLUX VM
- **npm**: TypeScript/JavaScript bindings for web-based constraint checking

### 8.3 Test Coverage

Each tier has dedicated test suites:

- `flux-isa`: 4 VM tests (add, constraint violation, validate bounds, snap)
- `flux-isa-mini`: Stack overflow/underflow, constraint satisfaction, sonar physics bounds (5 tests)
- `flux-isa-std`: Full opcode coverage, bytecode encode/decode round-trips, quality gate validation (8+ tests)
- `flux-isa-c`: C implementation matches Rust semantics for all shared opcodes
- `plato-engine`: Tile validation, gate acceptance/rejection, duplicate detection, pathfinder BFS/DFS (7+ tests)
- `constraint-theory-core-cuda`: CSP problem construction, solver initialization (2 tests, GPU-dependent)

### 8.4 CUDA Performance

The `GpuCspSolver` wrapper provides safe Rust access to CUDA batch operations:

- **`solve_batch()`**: Flattens problem domains and constraints into GPU-transferable buffers, dispatches `flux_cuda_csp_solve()` with one thread block per problem
- **`sonar_physics_batch()`**: Computes Mackenzie 1981 sound speed and Francois-Garrison 1982 absorption for thousands of depth/temp/salinity/frequency tuples in parallel
- **`flux_cuda_batch_execute()`**: Executes the same FLUX bytecode across multiple input instances simultaneously, with per-instance constraint flags

---

## 9. Future Work

### 9.1 Formal Verification of the Constraint VM

The FLUX VM's simplicity (stack-based, bounded instruction set, deterministic execution) makes it amenable to formal verification. We plan to use `kani` or `miri` to prove absence of undefined behavior in the Rust implementations, and CBMC or Frama-C for the C implementation. The goal: prove that if the VM reports `constraints_satisfied = true`, then all constraints were actually checked and passed.

### 9.2 Hardware Acceleration on Custom ASICs

The Tier 1 instruction set (21 opcodes, fixed-size stack) maps directly to a simple microcoded datapath. A custom ASIC could execute FLUX bytecodes at sensor sampling rates (MHz) with picosecond constraint checking latency. The fixed instruction format (4-byte header + 8-byte operands) simplifies instruction fetch and decode.

### 9.3 Cross-Tier Optimization

Currently, each tier compiles constraints independently. We envision a cross-tier compiler that:

1. Compiles complex constraints on Tier 4 (Thor), using the full 43-opcode ISA and GPU acceleration
2. Generates simplified Tier 1 bytecodes (21 opcodes, no heap) from the verified high-level specification
3. Deploys the Tier 1 bytecodes to MCU sensor nodes via PLATO tile distribution
4. Verifies end-to-end equivalence between the Tier 4 specification and Tier 1 deployment

This "compile high, deploy low" pattern is the natural evolution of the constraint compilation paradigm.

---

## References

1. Mackenzie, K.V. (1981). "Nine-term equation for sound speed in the oceans." *Journal of the Acoustical Society of America*, 70(3), 807–812.
2. Francois, R.E. & Garrison, G.R. (1982). "Sound absorption based on ocean measurements." *Journal of the Acoustical Society of America*, 72(6), 1879–1890.
3. Russell, S. & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. Chapter 6: Constraint Satisfaction Problems.
4. Forgy, C.L. (1982). "Rete: A fast algorithm for the many pattern/many object pattern match problem." *Artificial Intelligence*, 19(1), 17–37.
5. PLATO Architecture Documentation. Cocapn Fleet Internal, 2025–2026. `plato-engine` crate, `SuperInstance/plato-engine` repository.
6. FLUX ISA Specification. Cocapn Fleet, 2025–2026. `flux-isa`, `flux-isa-mini`, `flux-isa-std`, `flux-isa-edge`, `flux-isa-thor` crates.

---

*This paper describes production code deployed in the Cocapn Fleet. All referenced implementations are available in the SuperInstance GitHub organization.*
