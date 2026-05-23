# Going Below C: Constraint-Native Execution from Silicon Up

**Forgemaster ⚒️ — R&D Deep Dive**  
**Date:** 2026-05-03  
**Status:** Research Analysis  

---

## The Question

PLATO's "tutor" compiled knowledge into structured, executable tiles. FLUX ISA compiles constraints into bytecode. But we're still running on *general-purpose silicon designed for C-like workflows* — von Neumann machines with caches, branch predictors, and OS-mediated I/O. 

What happens if we stop pretending the hardware doesn't matter? What does a machine built *for* constraint satisfaction look like?

## Where We Are Now (4 Tiers)

```
Tier        Target          Runtime         Latency          Power
─────────────────────────────────────────────────────────────────────
mini        Cortex-M0+      no_std, 256B    ~50μs/check      50mW
std         Embedded Linux  CLI             ~5μs/check       1W
edge        Edge server     tokio async     ~500ns/check     15W
thor        GPU cluster     CUDA+tokio      ~200ns/check     300W
FPGA*       Artix-7         Bare metal      200ns/check      0.5W
```

*FPGA is designed but not yet synthesized.

The FPGA paper projects 200ns at 0.5W — 1000× better energy per check than GPU. That's the right direction. But we can go further.

## The Stack Problem (Why C Is Wrong For This)

C was designed for a world where:
- Memory is a linear array of bytes
- Computation is sequential (one thing at a time)
- Branches are cheap (they predicted this wrong, spent 30 years on branch predictors)
- Constraints are assertions you `#define` away in production

Constraint theory doesn't live in that world:
- **Domains are not arrays.** A variable domain {1,3,5,7} is a *set*, not a contiguous memory range. C represents it as an array and checks membership with a loop. Hardware can do it with a bitmask in one cycle.
- **Constraints are not branches.** `x + y == 7` is not an if-statement — it's a relation that either holds or doesn't. A general-purpose CPU evaluates it as load→add→compare→branch. A constraint machine evaluates it as a single comparator firing in parallel with all other constraints.
- **Backtracking is not a function call.** CSP solving creates a search tree that grows and shrinks dynamically. The call stack in C is exactly wrong for this — it's LIFO, fixed direction, no random access to parent states. A constraint machine needs a *search stack* that can snapshot and restore entire variable assignments.

## Going Lower: Three Architectural Proposals

### 1. Constraint-Native ISA (Below Assembly)

Current FLUX opcodes map to *general-purpose* operations: PUSH, ADD, SUB, ASSERT. These compile to ARM/x86 instructions that weren't designed for constraint work. What if we had opcodes that map directly to CSP primitives?

**Proposed constraint-native opcodes:**

```
DOMAIN_SET   reg, mask     — Set domain membership bitmask (one cycle)
DOMAIN_INTER reg_a, reg_b  — Intersect two domains (bitwise AND, one cycle)
DOMAIN_CARD  reg           — Count bits (population count, one cycle)
CONSTRAIN_ARC var_a, var_b, relation — Arc consistency check (pipelined, 3 cycles)
BACKTRACK_SNAPSHOT          — Copy entire search state to shadow registers
BACKTRACK_RESTORE           — Restore from shadow (one cycle, zero memory traffic)
SOLVE_STEP                  — One step of backtracking: assign, propagate, check
ASSERT_PARALLEL mask        — Check N constraints simultaneously, set violation bitmap
```

The key insight: **domains as bitmasks**. A variable with domain {0..63} is a single 64-bit register. Domain intersection is AND. Domain union is OR. Cardinality is POPCOUNT. These are all *single-cycle operations* on any modern ISA (ARM has POPCOUNT in ARMv8, x86 has POPCNT). But no language compiles to them naturally because no language treats domains as first-class bit-packed types.

A constraint-native ISA would:
- Eliminate the loop overhead of domain operations (bitmask vs array iteration)
- Enable parallel constraint checking (N constraints → N comparators firing simultaneously)
- Make backtracking a hardware operation (snapshot/restore via register banking)

### 2. Search-Optimized Memory Architecture

C's memory model is optimized for spatial locality (caches) and sequential access (prefetchers). CSP solving has the opposite access pattern:

- **Random access to variable domains** — the solver picks the most constrained variable, which changes at every node
- **Frequent snapshot/restore** — backtracking needs to save and restore the entire state at every branch point
- **No spatial locality** — constraints connect arbitrary pairs of variables

**Proposed memory architecture:**

```
┌─────────────────────────────────────────────────────────┐
│              Constraint Search Memory                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Variable Domain Bank (64 × 64-bit registers)    │  │
│  │  var[0]: 0b...10110101   (domain bitmask)        │  │
│  │  var[1]: 0b...11110001                           │  │
│  │  ...                                             │  │
│  │  var[63]: 0b...00000111                          │  │
│  │                                                   │  │
│  │  Shadow Bank: identical, used for backtrack       │  │
│  │  Snapshot: copy bank → shadow in one cycle        │  │
│  │  Restore: copy shadow → bank in one cycle         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Constraint Evaluation Network                    │  │
│  │  64 parallel comparators, one per constraint      │  │
│  │  Input: variable bank (broadcast bus)             │  │
│  │  Output: violation bitmap (one bit per constraint)│  │
│  │  Latency: 2 cycles (load operands → compare)     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Arc Consistency Propagator                       │  │
│  │  For each (var_i, var_j) pair:                    │  │
│  │    For each value in domain_i:                    │  │
│  │      Check if any value in domain_j is consistent │  │
│  │    Remove unsupported values (bitmask clear)      │  │
│  │  Fully pipelined: N constraints in O(N) cycles    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Variable Selection Heuristic                     │  │
│  │  POPCOUNT each domain → find minimum cardinality  │  │
│  │  Priority encoder → select MRV variable           │  │
│  │  Latency: 3 cycles (popcount → compare → encode) │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Backtracking without memory traffic.** Current backtracking in software:
1. Copy all domains to stack (N × 64 bits → cache miss likely)
2. Assign variable
3. Propagate constraints
4. If fail: pop stack, restore domains (another cache miss)

In the proposed architecture:
1. `BACKTRACK_SNAPSHOT` — copies domain bank to shadow registers (one cycle, no memory traffic)
2. Assign variable (write one register)
3. Arc consistency propagator runs (pipelined, N cycles for N constraints)
4. If fail: `BACKTRACK_RESTORE` — copies shadow back (one cycle)

**No cache, no DRAM, no memory controller.** Everything lives in registers.

### 3. The C Isn't The Problem — The Abstraction Is

C is actually fine for *implementing* a constraint machine. The issue is using C to *execute* constraints one at a time. The real insight:

**Don't write a constraint solver in C. Write a constraint machine in C, then compile constraints to it.**

This is exactly what FLUX ISA is doing, but we're still running the FLUX VM as software on a general-purpose CPU. The next step is:

```
CSP specification
    │
    ▼
FLUX compiler
    │
    ▼
FLUX bytecode
    │
    ├──► Software VM (current: ct-demo solver, flux-isa crate)
    │         ~5μs/check on Cortex-M4
    │
    ├──► GPU kernel (flux-cuda: flux_vm_kernel.cu)
    │         ~200ns/check on A100 (batch)
    │
    ├──► FPGA bitstream (paper designed, not synthesized)
    │         ~200ns/check on Artix-7, 0.5W
    │
    └──► **Custom silicon / ASIC** (proposed)
              ~20ns/check, <0.1W
              ~50M checks/sec
              Constraints are NOT software. They are hardware.
```

The ASIC path is the logical endpoint. A constraint check is a comparison — the simplest operation in digital logic. A comparator takes ~2 LUTs on an FPGA. On an ASIC, it's a few hundred transistors. We could fit 1000 parallel constraint comparators in less area than a single ARM Cortex-M0 core.

**Estimated ASIC (28nm process):**
- 1000 parallel constraint evaluators: ~0.1mm²
- 64 variable domain registers: ~0.01mm²
- Shadow bank for backtracking: ~0.01mm²
- Arc consistency propagator: ~0.05mm²
- Control FSM: ~0.01mm²
- **Total core: ~0.2mm²** (vs Cortex-M0 at ~0.04mm² but 1000× slower for constraint work)
- Power: <10mW at 500MHz
- Throughput: 500M constraint checks/sec

For context, that's 10,000× better throughput-per-watt than a Cortex-M4 running a C constraint solver.

## The Practical Path (What We Can Build Now)

We don't need custom silicon to get 90% of the benefit. The path is:

### Phase 1: Bitmask Domain Representation (Software, Now)

Replace `Domain::Set(Vec<i64>)` with `Domain::Bitmask(u64)`. For domains ≤64 values:
- Intersection: `a & b` (one instruction)
- Union: `a | b` (one instruction)
- Cardinality: `a.count_ones()` (one instruction on ARMv8/x86)
- Remove value: `a & !(1 << v)` (two instructions)

This is a pure software optimization that requires zero hardware changes. Estimated 5-10× speedup for domain-heavy operations.

### Phase 2: FPGA Constraint Machine (3-6 months)

Synthesize the architecture from the FPGA paper. Real hardware, real measurements. This validates the architecture before committing to silicon.

### Phase 3: RISC-V Custom Extension (6-12 months)

RISC-V's custom instruction extension space (custom-0/1/2/3 opcodes) lets us add FLUX constraint opcodes as actual CPU instructions. A FLUX-aware RISC-V core could execute `constrain_arc`, `backtrack_snapshot`, and `assert_parallel` as single instructions.

OpenCores and Chipyard make this accessible — we don't need a fab, just an FPGA with a RISC-V soft core.

### Phase 4: ASIC (12-24 months, if warranted)

If the FPGA proves the architecture, tape out on a cheap process (SkyWater 130nm is open-source via Efabless/Google). The design is simple enough for a TinyTapeout submission (hundreds of logic elements, not millions).

## The Deep Insight

The PLATO tutor compiled knowledge into a form machines could execute. FLUX ISA compiles constraints into a form VMs can execute. The next step is compiling constraints into a form *hardware* can execute.

The chain is:

```
Knowledge → Tiles → Constraints → FLUX Bytecode → FPGA Gates → Silicon
```

Each step in this chain is a compilation. The PLATO tutor was step 1. FLUX ISA is step 2-3. The FPGA paper is step 4. Custom silicon is step 5.

**The constraint is the hardware. The hardware is the constraint.**

When you build a machine where violating a constraint is physically impossible — because the comparator that checks it is hardwired and cannot be bypassed — you've achieved something C can never give you. Not through software discipline, not through coding standards, not through formal verification, but through the physics of the machine itself.

That's what going below C means.

---

*Next concrete step: implement bitmask domains in ct-demo, benchmark against current Vec<i64> representation, submit results to PLATO.*
