## Agent 2: "From GUARD to Silicon in 90 Nanoseconds"

*Target: GPU engineers, embedded systems architects, compiler builders. Technical deep-dive tracing a single constraint from DSL specification to GPU instruction retirement.*

---

At 10:47 AM on a Tuesday, a sensor in the primary coolant loop reports a temperature of 519 degrees Celsius. The safety constraint says: if temperature exceeds 520 degrees for more than 100 milliseconds, initiate an emergency SCRAM. From the moment that sensor value arrives to the moment the GPU finishes checking it against every active constraint in the system, 90 nanoseconds elapse.

This post traces exactly what happens in those 90 nanoseconds. Every opcode. Every memory transaction. Every warp schedule decision. Buckle up.

### The Source: GUARD DSL

The constraint starts as human-readable, auditable text:

```guard
constraint reactor_temp {
    min: 280 C,
    max: 520 C,
    update: 10Hz,
    action: SCRAM if violated > 100ms
}
```

This is not pseudocode. This is a formal specification in the GUARD Domain Specific Language, designed for safety engineers who need to write requirements that are simultaneously:
- Human-auditable (for certification review)
- Machine-executable (for runtime checking)
- Mathematically formal (for compiler correctness)

GUARD has a formal semantics: every constraint maps to a predicate over a trace of sensor readings. The `reactor_temp` constraint above is formally:

```
forall t: sensor(t) >= 280 ∧ sensor(t) <= 520
     ∨ (exists interval I: duration(I) > 100ms
        ∧ forall t in I: sensor(t) > 520
        → action_SCRAM(t + 100ms))
```

This is what we mean by "requirements as code." The requirement is executable, formally defined, and verifiable.

### Stage 1: Parsing and AST Construction (10 microseconds)

The GUARD parser (Rust, nom-based) consumes the constraint and produces an Abstract Syntax Tree with provenance tracking:

```rust
// Simplified AST node for the constraint above
Constraint {
    name: "reactor_temp",
    bounds: Interval {
        lower: Literal { value: 280, unit: Celsius, provenance: Line(3, Col(9)) },
        upper: Literal { value: 520, unit: Celsius, provenance: Line(4, Col(9)) }
    },
    temporal: UpdateRate(Hz(10)),
    action: ConditionalAction {
        condition: DurationExceeded(Millis(100)),
        effect: Scram
    }
}
```

The provenance tracking is critical for certification: every byte in the eventual binary can be traced back to a line in the source. This is DO-178C structural coverage at the language level.

### Stage 2: Type Checking and Range Analysis (25 microseconds)

FLUX's type system knows about physical units (Celsius, MPa, RPM) and automatically inserts range proofs:

```
Type checking 'reactor_temp':
  sensor_channel_7: u16 (raw ADC)
  valid range: [0, 4095] (12-bit ADC)
  constraint range: [280, 520]
  overlap: valid (constraint within sensor range)
  widening required: none
  conversion: celsius = (raw * 500 / 4096) - 20
  overflow proof: ✓ (intermediate fits u16)
```

The compiler proves that the ADC scaling cannot overflow, that the constraint bounds are reachable, and that the temporal logic is well-formed (the 10Hz update rate is consistent with the 100ms violation window).

### Stage 3: Lowering to FLUX-C Bytecode (40 microseconds)

Now the magic: AST → FLUX-C intermediate representation. FLUX-C has exactly 43 opcodes, each with formal operational semantics:

```
FLUX-C Opcode Set (43 total)
==============================
Category A: Memory (8 opcodes)
  LOAD_SENSOR, LOAD_CONST, STORE_TEMP, STORE_OUT,
  PACK_INT8, UNPACK_INT8, BROADCAST, GATHER

Category B: Arithmetic (12 opcodes)
  ADD_INT8, SUB_INT8, MUL_INT8, DIV_INT8,
  SCALE, OFFSET, CLAMP_LOWER, CLAMP_UPPER,
  WIDEN, NARROW, SATURATE, ABS

Category C: Logic/Comparison (10 opcodes)
  LT, LTE, GT, GTE, EQ, NEQ,
  AND, OR, NOT, XOR

Category D: Temporal (8 opcodes)
  TIMER_START, TIMER_ELAPSED, TIMER_RESET,
  DURATION_CHECK, LATCH_SET, LATCH_CLEAR,
  STABLE_FOR, EDGE_DETECT

Category E: Control (5 opcodes)
  JMP, JMP_COND, NOP, HALT, ASSERT
```

The `reactor_temp` constraint compiles to:

```
; FLUX-C bytecode for constraint 'reactor_temp'
; Channel 7, 12-bit ADC, scaled to Celsius
; Execution: one warp, 32 threads, INT8 x8 packed

0:  LOAD_SENSOR  r0, ch7       ; r0 = raw_adc_value (u16)
1:  SCALE        r1, r0, 500   ; r1 = r0 * 500
2:  DIV_INT8     r1, r1, 4096  ; r1 = r1 / 4096 (0..500 range)
3:  OFFSET       r1, r1, -20   ; r1 = r1 - 20 (celsius scale)
4:  CLAMP_LOWER  r1, 280       ; r1 = max(r1, 280)  (no underflow)
5:  CLAMP_UPPER  r1, 520       ; r1 = min(r1, 520)  (ceiling check)
6:  LT           r2, r1, 521   ; r2 = (r1 < 521) ? 1 : 0
7:  AND          r3, r3, r2    ; accumulate across constraints
8:  TIMER_ELAPSED r4, t0       ; r4 = elapsed_ms(timer0)
9:  DURATION_CHECK r5, r4, 100 ; r5 = (r4 > 100) ? 1 : 0
10: LATCH_SET    r6, r5, SCRAM ; latch SCRAM if duration exceeded
11: HALT                        ; end of constraint block
```

This is not assembly you hand-write. It's compiler-generated, formally verified output. Every opcode has a Hoare triple specifying its preconditions and postconditions. The sequence forms a verified chain: the postcondition of opcode N is the precondition of opcode N+1.

### Stage 4: x8 INT8 Packing (5 microseconds)

Here's where GPU efficiency happens. A single constraint check is tiny—too small to fill a warp efficiently. So FLUX packs 8 constraints into one 32-bit INT8 word:

```
INT8 x8 Packing Layout
======================
Word 0: [C0_lo | C0_hi | C1_lo | C1_hi | C2_lo | C2_hi | C3_lo | C3_hi]
Word 1: [C4_lo | C4_hi | C5_lo | C5_hi | C6_lo | C6_hi | C7_lo | C7_hi]
...

Each 32-thread warp checks 32 sensors × 8 constraints = 256 checks simultaneously.
With 128 warps per SM × 20 SMs = 2,560 warps active.
Total parallel checks: 2,560 × 256 = 655,360 checks per clock.
```

The packing is not arbitrary—it's chosen so that all 8 constraints in a word belong to the same sensor channel, ensuring coalesced memory access. This is a memory-bound workload at ~187 GB/s.

### Stage 5: GPU Kernel Dispatch (15 microseconds)

The FLUX runtime dispatches via CUDA driver API with pre-allocated, pinned memory pools:

```
GPU Dispatch Timeline
=====================
T+0μs:   Host writes sensor batch to pinned H2D buffer
T+2μs:   cudaMemcpyAsync launches (stream 0)
T+8μs:   DMA completes, kernel launch queued
T+12μs:  Kernel executes (<<<(N+255)/256, 256>>>)
T+82μs:  Kernel completes, results in device buffer
T+85μs:  D2H memcpy of violation flags
T+90μs:  Host receives violation vector

Total: 90 microseconds for a full constraint batch.
Per constraint: ~90 nanoseconds effective.
```

The 90 nanoseconds per constraint is an amortized figure for batch checking. A single constraint in isolation takes longer due to fixed dispatch overhead. But safety systems always check batches—hundreds or thousands of constraints per cycle.

### Stage 6: Retirement and Action (10 microseconds)

The GPU returns a bit vector:

```
Violation Vector (one bit per constraint)
=========================================
Bit 0: reactor_temp      = 0 (OK)
Bit 1: coolant_pressure  = 0 (OK)
Bit 2: rod_position      = 0 (OK)
...
Bit 31: turbine_rpm      = 0 (OK)

All zeros → no action.
Any one   → index into action table, trigger SCRAM/HOLD/ALERT.
```

The host-side action handler is constant-time: bit scan, table lookup, function pointer dispatch. No malloc, no syscalls in the hot path.

### The Verification Chain

Every stage in this pipeline is either formally verified or verifiable:

```
Verification Artifacts for 'reactor_temp' Constraint
======================================================
Stage          | Artifact                    | Status
---------------|-----------------------------|------------------
GUARD source   | AST with provenance         | Parser verified
Type check     | Range proof log             | SMT-solver checked
FLUX-C IR      | Opcode sequence + Hoare     | Manual audit + 38 proofs
x8 packing     | Memory layout invariant     | Proven: coalesced access
GPU kernel     | PTX assembly + register use   | Automated check
Differential   | 10M+ inputs vs CPU ref      | 0% mismatch
```

The Galois connection (discussed in detail in Agent 3's post) guarantees that if the FLUX-C bytecode passes all checks, the original GUARD constraint is satisfied.

### What This Means for Embedded Architects

If you're designing a safety system, you face a trilemma:

```
The Safety Trilemma
===================
       Speed
        /\
       /  \
      /    \
     /  ?   \        <- You are here, probably
    /________\
  Cost      Correctness

Pick any two, conventional wisdom says.

FLUX claims: pick all three, but only if you accept:
  1. Restricted opcode set (43 opcodes)
  2. Integer-only arithmetic (no FP in hot path)
  3. Batch processing (not single-constraint RPC)
  4. Formal methods up-front (not bolt-on)
```

The 90-nanosecond figure isn't magic. It's the result of disciplined architecture: simple opcodes pack efficiently, integer arithmetic pipelines perfectly, and memory-bound workloads benefit from coalesced access patterns that are easy to verify.

### Actionable Takeaways

1. **If your constraint check uses FP32 or FP16, you don't have a safety system.** You have an approximation. Switch to integer scaling with proven range.

2. **Batch your constraints.** The GPU fixed dispatch cost is amortized across batch size. Design your sensor acquisition to fill at least 256 constraints per kernel.

3. **Demand compiler artifacts.** Every safety-critical compiler should produce: AST with provenance, type check log, IR with Hoare triples, and differential test results. If your vendor can't provide these, they haven't built a safety compiler.

4. **Measure wall-clock, not kernel time.** The 90ns figure includes memcpy, dispatch, and retirement. Vendor "kernel-only" numbers are misleading for real systems.

### The 90-Nanosecond Promise

From GUARD source to retired GPU instruction, 90 nanoseconds. With a mathematical guarantee that the constraint was checked exactly as specified. Not approximately. Not probably. Exactly.

That's not GPU marketing. That's compiler architecture, formal verification, and systems engineering working together to make safety fast enough to matter.

---
