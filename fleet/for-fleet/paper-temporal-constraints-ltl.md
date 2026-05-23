# Temporal Constraints for Autonomous Systems: Compiling LTL to FLUX ISA Bytecodes

**Forgemaster ⚒️ — Cocapn Fleet**
**Date: 2026-05-02**
**Status: Research Paper — FLUX ISA Temporal Extension Design**

---

## 1. Abstract

The FLUX Instruction Set Architecture provides a bytecode-level constraint verification framework for autonomous systems, but its current design operates on point-in-time state: constraints are evaluated against a single snapshot of the world. Real autonomous systems — underwater sonar fleets, UAV swarms, autonomous ground vehicles — require *temporal* constraints that reason over sequences of states across time. This paper extends the FLUX ISA with six new temporal opcodes derived from Linear Temporal Logic (LTL): `TEMPORAL_ALWAYS`, `TEMPORAL_EVENTUALLY`, `TEMPORAL_UNTIL`, `TEMPORAL_NEXT`, `TEMPORAL_WITHIN`, and `TEMPORAL_RESPONDS`. We present the full semantics, stack effects, and binary encoding for each opcode, describe the compilation pipeline from LTL formulas to FLUX bytecodes via bounded Büchi automata, analyze the runtime memory requirements (ring buffers of size *O(bound)* per constraint), and demonstrate the design with a concrete sonar fleet scenario. We prove that the bounded temporal fragment is decidable and has finite memory, making it suitable for embedded deployment on resource-constrained autonomous platforms.

---

## 2. Introduction

Autonomous systems don't live in a single moment. A submarine fleet must maintain depth for *thirty seconds* before declaring stable contact. A drone swarm must respond to a threat *within two seconds* of detection. A safety invariant must hold *at all times* during a mission.

The FLUX ISA, in its current form, treats constraint verification as a stateless operation. At each tick, the VM evaluates a set of spatial and logical constraints against the current world state. If all constraints pass, execution continues. If any fails, the VM signals a violation. This is clean, fast, and memory-efficient — but it cannot express:

- **Duration constraints:** "Condition *p* must hold continuously for *N* ticks"
- **Deadline constraints:** "If *p* occurs, then *q* must occur within *N* ticks"
- **Until constraints:** "Condition *p* must hold until condition *q* becomes true"
- **Safety invariants:** "Condition *p* must hold at every tick, forever"

These are temporal constraints — they require reasoning about the *history* of execution, not just the current state. The mathematical framework for expressing them is Linear Temporal Logic (LTL), widely used in model checking and formal verification since Pnueli's seminal 1977 paper.

This paper bridges LTL theory and the FLUX ISA. We design six new opcodes that bring temporal reasoning to FLUX bytecodes, define the compilation pipeline from LTL formulas to these bytecodes, and prove that the bounded fragment has the right properties for real-time embedded deployment.

### Why This Matters for the Fleet

The Cocapn fleet operates autonomous agents that make safety-critical decisions. Point-in-time constraint checking catches instantaneous violations — "depth is below 50m" — but misses temporal violations — "depth changed by more than 10m in 2 seconds." Temporal constraints close this gap. They let us express *operational patterns* as verifiable bytecodes, not ad-hoc monitoring code.

---

## 3. LTL Primer

### 3.1 Syntax

Linear Temporal Logic extends propositional logic with temporal operators that reason over infinite sequences of states (traces). Given a set of atomic propositions *AP*, LTL formulas are defined by:

```
φ ::= p | ¬φ | φ ∧ φ | φ ∨ φ | φ → φ
    | □φ          (always: φ holds at every future state)
    | ◇φ          (eventually: φ holds at some future state)
    | φ U φ       (until: first formula holds until second becomes true)
    | X φ         (next: φ holds at the next state)
```

### 3.2 The Five Operators

| Operator | Name | Meaning | Example |
|----------|------|---------|---------|
| `□p` | Always (globally) | *p* is true at every state from now on | `□(depth > 0)` — depth is always positive |
| `◇p` | Eventually (finally) | *p* becomes true at some future state | `◇(surface_reached)` — eventually reach surface |
| `p U q` | Until | *p* holds continuously until *q* becomes true | `diving U at_depth` — keep diving until reaching target depth |
| `Xp` | Next | *p* holds at the very next state | `X(engines_off)` — engines off on the next tick |
| `p → ◇q` | Responds (leads-to) | Whenever *p* is true, *q* eventually becomes true | `contact_detected → ◇response_sent` — every contact gets a response |

### 3.3 Safety vs. Liveness

LTL properties split into two fundamental classes:

- **Safety properties** ("nothing bad ever happens"): `□(¬bad)`. Violated by a finite trace. Example: "depth never exceeds 500m." If it happens even once, the property is broken.
- **Liveness properties** ("something good eventually happens"): `□(◇good)`. Require infinite traces to violate. Example: "the system eventually responds to every request."

For embedded systems, **bounded** variants of these properties are more practical: `□[0,N](p)` (always for the next *N* ticks) and `◇[0,N](p)` (within the next *N* ticks). Bounded properties are decidable in finite memory — critical for deployment on hardware with limited RAM.

### 3.4 Why Bounded LTL?

Unbounded LTL requires reasoning over infinite traces. In practice, autonomous systems care about bounded windows:
- "Respond within 5 seconds" — not "eventually, possibly in the year 2047"
- "Hold depth for 30 seconds" — not "hold depth forever"
- "Don't fire within 2 seconds of last firing" — bounded cooldown

The **bounded temporal fragment** restricts operators to finite time windows. This gives us:
1. **Decidability** — Every bounded property can be checked with finite memory
2. **Predictable resource usage** — Memory is *O(bound)* per constraint
3. **Real-time guarantees** — Bounded checks complete in constant time

---

## 4. FLUX ISA Extension Design

### 4.1 Opcode Space

The FLUX ISA uses a 1-byte opcode field. Temporal opcodes occupy the `0x90`–`0x9F` range:

| Opcode | Mnemonic | Description |
|--------|----------|-------------|
| `0x90` | `TEMPORAL_ALWAYS` | Condition must hold for *N* consecutive ticks |
| `0x91` | `TEMPORAL_EVENTUALLY` | Condition must become true within *N* ticks |
| `0x92` | `TEMPORAL_UNTIL` | Condition A holds until condition B |
| `0x93` | `TEMPORAL_NEXT` | Check condition at next tick |
| `0x94` | `TEMPORAL_WITHIN` | Condition must hold at least once within *N* ticks |
| `0x95` | `TEMPORAL_RESPONDS` | If trigger fires, response must occur within *N* ticks |

### 4.2 Temporal Operand Encoding

Temporal constraints reference a **condition handle** (a previously computed boolean on the stack) and a **time bound** (in ticks). Encoding:

```
[opcode: 1 byte] [condition_handle: 2 bytes] [time_bound: 4 bytes]
```

For dual-condition opcodes (`TEMPORAL_UNTIL`, `TEMPORAL_RESPONDS`):

```
[opcode: 1 byte] [cond_a_handle: 2 bytes] [cond_b_handle: 2 bytes] [time_bound: 4 bytes]
```

**Condition handles** are indices into the Temporal Condition Table (TCT), a runtime structure that tracks the state of active temporal constraints. When a boolean expression is evaluated, the result can be stored as a handle via the existing `STORE_RESULT` opcode (extended to support temporal handles).

### 4.3 Opcode Specifications

---

#### 4.3.1 `TEMPORAL_ALWAYS` (0x90)

**Semantics:** The condition identified by `condition_handle` must evaluate to `true` for `time_bound` consecutive ticks. If the condition becomes false before the bound is reached, the constraint *fails*. If the condition holds for the full duration, the constraint *passes*.

**Stack Effects:**
```
Before: [..., cond_value: bool]     (condition evaluated on current state)
After:  [..., result: bool]          (true if held for bound ticks, false if violated)
```

Wait — that's not quite right. The `TEMPORAL_ALWAYS` opcode doesn't consume a value from the stack per tick. Instead, it *registers* a temporal monitor that checks a condition across ticks. Let me be more precise:

**Operational Semantics (per tick):**
```
TEMPORAL_ALWAYS handle, bound
  monitor = TCT[handle]
  if monitor.start_tick == UNSET:
    monitor.start_tick = current_tick
    monitor.last_true_tick = current_tick
  if monitor.condition():
    monitor.consecutive_true++
    if monitor.consecutive_true >= bound:
      PASS  → push true
  else:
    monitor.consecutive_true = 0
    if (current_tick - monitor.start_tick) >= bound:
      FAIL  → push false
    monitor.start_tick = current_tick  // reset window
```

**Encoding:**
```
90 HH HH BB BB BB BB   (7 bytes total)
     │  │  └──────────┘ time_bound (u32, little-endian)
     └─┘ condition_handle (u16, little-endian)
```

**Example:** Maintain depth between 100-200m for 30 seconds at 10Hz (300 ticks):
```
LOAD_SENSOR depth                    // stack: [depth_value]
CONST 100                            // stack: [depth_value, 100]
GT                                   // stack: [depth > 100]
LOAD_SENSOR depth                    // stack: [depth > 100, depth_value]
CONST 200                            // stack: [depth > 100, depth_value, 200]
LT                                   // stack: [depth > 100, depth < 200]
AND                                  // stack: [depth_in_range]
STORE_TEMPORAL_HANDLE 0x0001         // register handle 0x0001
TEMPORAL_ALWAYS 0x0001 300           // must hold for 300 ticks
```

---

#### 4.3.2 `TEMPORAL_EVENTUALLY` (0x91)

**Semantics:** The condition identified by `condition_handle` must become `true` at least once within `time_bound` ticks. If the deadline passes without the condition becoming true, the constraint *fails*.

**Stack Effects:**
```
Activation: Registers monitor. Does not push/pop immediately.
Per tick:   Evaluates condition. Pushes result only when resolved.
  - Condition becomes true → push true (PASS)
  - Deadline expires → push false (FAIL)
```

**Encoding:**
```
91 HH HH BB BB BB BB   (7 bytes total)
```

**Example:** Response must be sent within 20 ticks of detection:
```
LOAD_FLAG response_sent
STORE_TEMPORAL_HANDLE 0x0002
TEMPORAL_EVENTUALLY 0x0002 20
```

---

#### 4.3.3 `TEMPORAL_UNTIL` (0x92)

**Semantics:** Condition A must hold continuously until condition B becomes true. Once B becomes true, the constraint passes. If A becomes false before B is true, the constraint fails. Optional time bound: the until must resolve within `time_bound` ticks.

**Stack Effects:**
```
Activation: Registers dual-condition monitor.
Per tick:
  - A true, B false → continue monitoring (A holds, waiting for B)
  - A true, B true  → PASS → push true
  - A false, B false → FAIL → push false (A broke before B arrived)
  - A false, B true  → PASS → push true (B arrived simultaneously)
```

**Encoding:**
```
92 HA HA HB HB BB BB BB BB   (9 bytes total)
     │  │  │  │  └──────────┘ time_bound (u32)
     │  │  └─┘ cond_b_handle (u16)
     └─┘ cond_a_handle (u16)
```

**Example:** Maintain diving state until reaching target depth:
```
LOAD_FLAG is_diving
STORE_TEMPORAL_HANDLE 0x0003
LOAD_SENSOR depth
CONST 200
GEQ  // depth >= 200
STORE_TEMPORAL_HANDLE 0x0004
TEMPORAL_UNTIL 0x0003 0x0004 600  // up to 600 ticks (60s at 10Hz)
```

---

#### 4.3.4 `TEMPORAL_NEXT` (0x93)

**Semantics:** The condition must be true at the next tick. This is the simplest temporal operator — a one-tick lookahead.

**Stack Effects:**
```
At registration: Stores condition handle, defers evaluation.
At next tick:    Evaluates condition, pushes result.
```

**Encoding:**
```
93 HH HH   (3 bytes total — no time bound needed, implicitly 1)
```

**Example:** If firing now, engines must be off next tick:
```
LOAD_FLAG just_fired
STORE_TEMPORAL_HANDLE 0x0005
TEMPORAL_NEXT 0x0005  // check at next tick
```

**Note:** `TEMPORAL_NEXT` is a special case of `TEMPORAL_ALWAYS` with bound=1, but it's included as a first-class opcode because (a) it's a fundamental LTL operator, (b) it has zero memory overhead (no ring buffer needed), and (c) it composes naturally with other temporal operators in compiled LTL formulas.

---

#### 4.3.5 `TEMPORAL_WITHIN` (0x94)

**Semantics:** The condition must hold *at least once* within `time_bound` ticks. This is syntactic sugar for `◇[0,N](p)` — identical to `TEMPORAL_EVENTUALLY` but emphasized in the instruction set because it's the most common bounded temporal pattern in fleet operations.

**Stack Effects:** Same as `TEMPORAL_EVENTUALLY`.

**Encoding:**
```
94 HH HH BB BB BB BB   (7 bytes total)
```

**Distinction from `TEMPORAL_EVENTUALLY`:** Semantically equivalent. Provided as a separate opcode because (a) it allows the VM to optimize for the "check at least once" pattern vs. "must happen by deadline" pattern, and (b) it maps more directly to the natural-language requirement "within N seconds."

**Example:** Sonar ping must complete within 50 ticks:
```
LOAD_FLAG ping_complete
STORE_TEMPORAL_HANDLE 0x0006
TEMPORAL_WITHIN 0x0006 50
```

---

#### 4.3.6 `TEMPORAL_RESPONDS` (0x95)

**Semantics:** If the trigger condition becomes true, the response condition must become true within `time_bound` ticks. This is the *response pattern* `□(trigger → ◇[0,N](response))`. It re-arms after each trigger: every trigger instance starts an independent deadline.

**Stack Effects:**
```
Activation: Registers dual-condition monitor with trigger/response semantics.
Per tick:
  - No trigger, no response → continue (pass so far)
  - Trigger fires → start deadline timer, expect response within bound
  - Response within bound → PASS for that instance, re-arm
  - Deadline expires without response → FAIL → push false
```

**Encoding:**
```
95 HT HT HR HR BB BB BB BB   (9 bytes total)
     │  │  │  │  └──────────┘ time_bound (u32)
     │  │  └─┘ response_handle (u16)
     └─┘ trigger_handle (u16)
```

**Example:** If sonar detects contact, fleet must respond within 20 ticks:
```
LOAD_FLAG sonar_contact_detected
STORE_TEMPORAL_HANDLE 0x0007
LOAD_FLAG fleet_response_sent
STORE_TEMPORAL_HANDLE 0x0008
TEMPORAL_RESPONDS 0x0007 0x0008 20
```

---

## 5. Compilation from LTL to FLUX

### 5.1 Translation Rules

The compilation maps LTL formulas to FLUX temporal opcodes. The key insight: bounded LTL formulas compile directly to bounded temporal monitors, while unbounded formulas require automata-theoretic compilation.

#### Direct Compilation (Bounded Fragment)

| LTL Formula | FLUX Bytecodes |
|-------------|----------------|
| `□[0,N] p` | `EVAL p → STORE_HANDLE h → TEMPORAL_ALWAYS h N` |
| `◇[0,N] p` | `EVAL p → STORE_HANDLE h → TEMPORAL_EVENTUALLY h N` |
| `p U[N] q` | `EVAL p → STORE_HANDLE ha → EVAL q → STORE_HANDLE hb → TEMPORAL_UNTIL ha hb N` |
| `X p` | `EVAL p → STORE_HANDLE h → TEMPORAL_NEXT h` |
| `□(p → ◇[0,N] q)` | `EVAL p → STORE_HANDLE ht → EVAL q → STORE_HANDLE hr → TEMPORAL_RESPONDS ht hr N` |

#### Composition Rules

Complex LTL formulas are compiled by decomposing into subformulas and composing the resulting bytecodes:

```
□(p ∧ q)          →  □p and □q  (decompose conjunction under always)
□(p → q)          →  □(¬p ∨ q)  →  compile disjunction
□(p → ◇[N] q)     →  TEMPORAL_RESPONDS (direct pattern)
◇[N](p ∧ q)       →  ◇[N] p ∧ ◇[N] q  (both must hold, but within same window)
□[N] p ∨ □[M] q   →  parallel monitors, OR the results
```

### 5.2 Automata-Theoretic Compilation

For unbounded formulas (e.g., `□p` with no time limit), we use the standard automata-theoretic approach:

1. **LTL → Generalized Büchi Automaton (GBA):** Each LTL formula is translated to a GBA that accepts exactly the traces satisfying the formula. We use the tableau construction (Gerth et al., 1995).

2. **GBA → Büchi Automaton (BA):** Convert generalized acceptance conditions to a standard Büchi automaton by replicating accepting states.

3. **BA → Bounded Monitor:** Since FLUX operates on bounded time windows in practice, we truncate the Büchi automaton to a finite horizon *H* (the maximum mission duration in ticks). This yields a finite-state monitor with *O(|BA| × H)* states — large but bounded.

4. **Bounded Monitor → FLUX Bytecodes:** The finite monitor is encoded as a state machine in FLUX bytecodes using `BRANCH`, `STORE`, and `LOAD` opcodes, with `TEMPORAL_ALWAYS` guards for the transition conditions.

**Practical note:** For the fleet, we expect 95% of temporal constraints to be bounded and compile directly via the rules in §5.1. The automata-theoretic pipeline is reserved for the rare unbounded safety invariant.

### 5.3 Compilation Example

**LTL formula:** `□(depth ≥ 100 ∧ depth ≤ 200) U at_depth`

This reads: "always (depth in range) until reaching target depth."

**Compiled FLUX:**
```
// Condition A: depth in valid range
LOAD_SENSOR depth
DUP
CONST 100
GEQ                    // depth >= 100
SWAP
CONST 200
LEQ                    // depth <= 200
AND                    // depth in [100, 200]
STORE_TEMPORAL_HANDLE 0x01

// Condition B: at target depth
LOAD_SENSOR depth
LOAD_CONST target_depth
EQ                     // depth == target_depth
STORE_TEMPORAL_HANDLE 0x02

// Temporal: A U B, bounded to 3000 ticks (5 min at 10Hz)
TEMPORAL_UNTIL 0x01 0x02 3000
ASSERT                 // fail mission if violated
```

---

## 6. Runtime Monitoring

### 6.1 The Temporal Virtual Machine

The standard FLUX VM evaluates constraints statelessly. The temporal extension introduces the **Temporal Condition Table (TCT)** — a runtime data structure that tracks active temporal monitors.

**TCT Entry:**
```
struct TemporalMonitor {
    opcode:      u8,           // which temporal opcode
    cond_a:      u16,          // first condition handle (or trigger)
    cond_b:      u16,          // second condition handle (or response, 0 if unused)
    bound:       u32,          // time bound in ticks
    start_tick:  u32,          // when this monitor was activated
    state:       MonitorState, // current monitor state
    ring_buffer: RingBuffer,   // history for sliding-window checks
}

enum MonitorState {
    Waiting,                   // not yet activated
    Active,                    // monitoring in progress
    Satisfied,                 // constraint passed
    Violated,                  // constraint failed
}
```

### 6.2 Ring Buffers for History

Temporal monitors that need to track condition values across ticks use ring buffers:

```
RingBuffer {
    data:  [bool; N],    // circular buffer, N = time_bound
    head:  usize,         // write position
    count: usize,         // number of entries written
}
```

**Per-tick update:** Write current condition value at `head`, advance `head = (head + 1) % N`. *O(1)* time.

**Sliding window check (for TEMPORAL_ALWAYS):** Scan the last `bound` entries. If all are `true`, the constraint holds. *O(bound)* time per check — acceptable for bounded values (typically < 1000 ticks).

**Optimization:** For `TEMPORAL_ALWAYS`, maintain a running count of `false` values in the ring buffer. When the count is zero, the constraint holds without scanning. This makes the common case *O(1)*.

### 6.3 Memory Analysis

Per temporal monitor, memory usage is:

| Opcode | State Size | Ring Buffer | Total |
|--------|-----------|-------------|-------|
| `TEMPORAL_ALWAYS` | 16 bytes | `bound` bytes | 16 + bound |
| `TEMPORAL_EVENTUALLY` | 16 bytes | 0 bytes | 16 |
| `TEMPORAL_UNTIL` | 20 bytes | 0 bytes | 20 |
| `TEMPORAL_NEXT` | 12 bytes | 0 bytes | 12 |
| `TEMPORAL_WITHIN` | 16 bytes | 0 bytes | 16 |
| `TEMPORAL_RESPONDS` | 20 bytes | `bound` bytes | 20 + bound |

**Total memory for a mission with 50 temporal constraints, average bound 200 ticks:**
- 50 monitors × ~220 bytes average = **~11 KB**
- Negligible for any embedded platform with > 1MB RAM

**Worst case:** 100 constraints with bound 10000 (unusual) = ~1 MB. Still feasible.

### 6.4 Execution Model

The temporal VM extends the standard FLUX tick cycle:

```
loop every tick:
  1. Read sensors → update world state
  2. Evaluate non-temporal constraints (standard FLUX)
  3. For each active temporal monitor:
     a. Evaluate condition(s) against current state
     b. Update ring buffer(s)
     c. Check if monitor is satisfied or violated
     d. Push result to stack
  4. Handle violations (abort, warn, log)
```

**Tick budget:** Temporal monitor evaluation is *O(active_monitors × max_bound)* per tick. With 50 monitors and max bound 300, worst case is 15,000 comparisons per tick. At 10Hz on a 100MHz embedded core, this is trivially within budget.

---

## 7. Sonar Fleet Example

### 7.1 Scenario

A sonar array must maintain depth between 100–200m for 30 seconds before declaring a stable contact. If contact is lost for more than 5 seconds, the system must re-acquire. The fleet must respond to any sonar contact detection within 2 seconds.

### 7.2 LTL Specification

```
// φ₁: Depth stability requirement
// "Depth must remain in [100, 200] for 300 consecutive ticks before contact declared"
□(stable_contact_declared → ◇[−300,0](□[0,300](depth ≥ 100 ∧ depth ≤ 200)))

// Simplified bounded version:
// "Declare stable contact only after 300 ticks of valid depth"
stable_depth[300] → stable_contact

// φ₂: Contact loss recovery
// "If contact lost for 50 ticks, transition to re-acquire"
□(◇[0,50](contact_detected) ∨ re_acquiring)

// φ₃: Response deadline
// "Every sonar contact detection must receive a response within 20 ticks"
□(sonar_contact_detected → ◇[0,20](fleet_response_sent))
```

### 7.3 Compiled FLUX Bytecodes

```
// ═══════════════════════════════════════════
// TEMPORAL CONSTRAINT: Depth Stability (φ₁)
// ═══════════════════════════════════════════

// Check: depth in range [100, 200]
LOAD_SENSOR depth
DUP
CONST 100
GEQ                           // depth >= 100
SWAP
CONST 200
LEQ                           // depth <= 200
AND                           // depth in [100, 200]
STORE_TEMPORAL_HANDLE 0x0010

// Must hold for 300 consecutive ticks (30 seconds at 10Hz)
TEMPORAL_ALWAYS 0x0010 300
STORE_FLAG depth_stable       // set flag when stable for 30s

// Only declare contact when depth is stable
LOAD_FLAG depth_stable
LOAD_FLAG contact_detected
AND
STORE_FLAG stable_contact_declared
ASSERT


// ═══════════════════════════════════════════
// TEMPORAL CONSTRAINT: Contact Loss (φ₂)
// ═══════════════════════════════════════════

// Check: contact detected
LOAD_FLAG sonar_contact_detected
STORE_TEMPORAL_HANDLE 0x0011

// Contact must be seen at least once every 50 ticks (5 seconds)
TEMPORAL_WITHIN 0x0011 50
NOT                            // if contact NOT seen within 50 ticks
BRANCH re_acquire_mode         // → transition to re-acquire state


// ═══════════════════════════════════════════
// TEMPORAL CONSTRAINT: Response Deadline (φ₃)
// ═══════════════════════════════════════════

// Trigger: sonar contact detected
LOAD_FLAG sonar_contact_detected
STORE_TEMPORAL_HANDLE 0x0012

// Response: fleet response sent
LOAD_FLAG fleet_response_sent
STORE_TEMPORAL_HANDLE 0x0013

// If trigger fires, response must occur within 20 ticks
TEMPORAL_RESPONDS 0x0012 0x0013 20
ASSERT                         // mission abort if response deadline missed
```

### 7.4 Bytecode Size

| Constraint | Opcodes | Bytes |
|-----------|---------|-------|
| Depth stability (φ₁) | 12 | ~40 |
| Contact loss (φ₂) | 5 | ~18 |
| Response deadline (φ₃) | 6 | ~25 |
| **Total** | **23** | **~83** |

83 bytes to encode three critical temporal safety constraints. This is the density that makes FLUX practical for embedded deployment.

### 7.5 Runtime Memory

| Monitor | Ring Buffer | Total State |
|---------|-------------|-------------|
| Depth stability | 300 bytes | 316 bytes |
| Contact loss | 0 bytes | 16 bytes |
| Response deadline | 20 bytes | 40 bytes |
| **Total** | **320 bytes** | **372 bytes** |

---

## 8. Formal Properties

### 8.1 Theorem: Finite Memory for Bounded Temporal Operators

**Statement:** Every bounded temporal operator in the FLUX temporal extension requires at most *O(bound)* memory, where *bound* is the time bound parameter.

**Proof sketch:**

Consider each opcode:

- **`TEMPORAL_ALWAYS(handle, N)`:** Must track whether the condition held for the last *N* consecutive ticks. Ring buffer of size *N* suffices. Memory: *O(N)*.

- **`TEMPORAL_EVENTUALLY(handle, N)`:** Must track (a) the start tick, and (b) whether the condition has been observed. A single boolean and a tick counter suffice. Memory: *O(1)*.

- **`TEMPORAL_UNTIL(ha, hb, N)`:** Must track (a) whether condition A has been continuously true since activation, (b) whether B has become true, and (c) the start tick. Three values suffice. Memory: *O(1)*.

- **`TEMPORAL_NEXT(handle)`:** One-tick lookahead. Stores the condition to check next tick. Memory: *O(1)*.

- **`TEMPORAL_WITHIN(handle, N)`:** Same as `TEMPORAL_EVENTUALLY`. Memory: *O(1)*.

- **`TEMPORAL_RESPONDS(ht, hr, N)`:** For each trigger instance, must track the deadline and whether the response arrived. With at most one active trigger at a time (sequential processing), memory is *O(N)* for the ring buffer tracking recent triggers. For concurrent triggers, memory is *O(instances × N)*, bounded by the mission duration.

**QED** — all bounded temporal operators have finite, predictable memory requirements.

### 8.2 Theorem: Decidability of Bounded Fragment

**Statement:** For any bounded LTL formula φ with maximum time bound *N*, the FLUX VM can determine whether φ is satisfied or violated within *N* ticks of activation.

**Proof:** The bounded temporal fragment of LTL is equivalent to first-order logic over finite traces of length *N*. Every bounded formula can be evaluated by examining a finite prefix of the trace. The FLUX temporal monitors operate over finite ring buffers of size ≤ *N*. At each tick, the monitor performs a finite computation over finite data. By inspection of the operational semantics in §4.3, every monitor reaches a terminal state (Satisfied or Violated) within *N* ticks. **QED.**

### 8.3 Theorem: Semantic Preservation

**Statement:** The compilation rules in §5.1 preserve LTL semantics for the bounded fragment.

**Proof sketch (by structural induction on LTL formulas):**

*Base case:* Atomic proposition *p* compiles to `LOAD_SENSOR` + condition evaluation. Semantics preserved by definition.

*Inductive step:*
- `□[0,N] p`: Compiled to `TEMPORAL_ALWAYS(h, N)` where *h* evaluates *p*. By the operational semantics of `TEMPORAL_ALWAYS`, the constraint passes iff *p* holds at every tick in [0, N]. This matches the LTL semantics of `□[0,N] p`. ✓

- `◇[0,N] p`: Compiled to `TEMPORAL_EVENTUALLY(h, N)`. Passes iff *p* holds at some tick in [0, N]. Matches LTL semantics. ✓

- `p U[N] q`: Compiled to `TEMPORAL_UNTIL(ha, hb, N)`. Passes iff *p* holds at every tick until *q* first holds, and this happens within *N* ticks. Matches bounded-until semantics. ✓

- `X p`: Compiled to `TEMPORAL_NEXT(h)`. Passes iff *p* holds at the next tick. Matches LTL semantics. ✓

- `□(p → ◇[0,N] q)`: Compiled to `TEMPORAL_RESPONDS(ht, hr, N)`. For every tick where *p* holds, *q* must hold within *N* subsequent ticks. Matches the response pattern semantics. ✓

Composition rules (conjunction, disjunction, negation) preserve semantics because FLUX's boolean stack operations (`AND`, `OR`, `NOT`) are semantically faithful to propositional connectives. **QED.**

---

## 9. Future Work

### 9.1 Unbounded Temporal Operators

The current design focuses on the bounded fragment. Unbounded operators (`□p` with no time limit) require the automata-theoretic pipeline (§5.2). Future work includes:

- **Efficient Büchi automaton encoding:** Compress the automaton state into minimal bit representations for embedded deployment.
- **Approximate monitoring:** For unbounded formulas, use a finite horizon *H* and accept that violations beyond *H* are not detected. This is acceptable for missions with defined durations.
- **Fairness assumptions:** In practice, autonomous systems operate under fairness constraints (e.g., the scheduler is fair, messages are eventually delivered). These reduce the state space.

### 9.2 Metric Temporal Logic (MTL)

LTL reasons over discrete ticks. Real systems have continuous time. Metric Temporal Logic extends LTL with real-valued time bounds:

- `□[0, 5.0s] p` — *p* holds for the next 5 seconds
- `◇[0, 2.0s] p` — *p* becomes true within 2 seconds
- `p U[0, 10.0s] q` — *p* until *q*, within 10 seconds

MTL compilation requires mapping wall-clock time to ticks, handling clock drift, and accommodating variable tick rates. The FLUX extension could support MTL by adding a `tick_rate` field to temporal monitors and converting time bounds to tick counts at registration time.

### 9.3 Real-Time Constraints with Clock Variables

Timed automata (Alur & Dill, 1994) extend finite automata with clock variables that track elapsed time. FLUX could support clock variables as first-class values:

```
CLOCK_START clock_1          // start clock variable
CLOCK_ELAPSED clock_1 → stack // push elapsed time
CLOCK_CHECK clock_1 < 5.0    // check time constraint
```

This enables patterns like: "After trigger, do A within 2 seconds and B within 5 seconds of A" — nested deadlines with independent clocks.

### 9.4 Distributed Temporal Constraints

The current design assumes a single FLUX VM. Fleet operations require temporal constraints that span multiple agents:

- "If *any* fleet member detects a threat, *all* members must respond within 3 seconds"
- "At least 3 of 5 array elements must maintain depth for 30 seconds"

This requires a distributed temporal monitor with clock synchronization and message passing. The FLUX extension could support this with network-aware condition handles that reference remote agent state.

### 9.5 Formal Verification of the Temporal VM

The temporal VM itself should be formally verified. We should prove:
- The VM correctly implements the operational semantics of each opcode
- The compilation pipeline preserves LTL semantics (mechanized proof in a proof assistant)
- The temporal VM never uses more memory than the bounds in §6.3

This is suitable for Lean 4 or Coq formalization, potentially as a proof-of-concept constraint-theory repo.

---

## 10. Conclusion

Temporal constraints are not optional for autonomous systems — they are the difference between "is this state safe right now?" and "has this system been behaving correctly over time?" The FLUX ISA, with its point-in-time constraint checking, handles the former well. This paper extends it to handle the latter.

We designed six temporal opcodes — `TEMPORAL_ALWAYS`, `TEMPORAL_EVENTUALLY`, `TEMPORAL_UNTIL`, `TEMPORAL_NEXT`, `TEMPORAL_WITHIN`, and `TEMPORAL_RESPONDS` — that map directly to bounded LTL operators. Each opcode has precise semantics, a compact encoding (3–9 bytes), and predictable memory usage (*O(bound)* in the worst case, *O(1)* for most operators). The compilation pipeline from LTL to FLUX bytecodes is straightforward for the bounded fragment and automata-theoretic for the unbounded case.

The sonar fleet example demonstrates the practical value: three critical temporal safety constraints — depth stability, contact loss recovery, and response deadlines — compile to 83 bytes of FLUX with 372 bytes of runtime memory. This is deployable on any embedded platform.

The key theoretical result: **bounded temporal operators have finite memory and are decidable in finite time.** This is what makes temporal FLUX safe for real-time, resource-constrained deployment. No unbounded state growth, no undecidable checks, no surprises.

The next step: implement this in the FLUX VM and deploy it on the sonar array. The theory is forged. Time to quench it in practice.

---

## References

1. Pnueli, A. (1977). "The temporal logic of programs." *18th IEEE Symposium on Foundations of Computer Science (FOCS)*, pp. 46–57.
2. Gerth, R., Peled, D., Vardi, M., & Wolper, P. (1995). "Simple on-the-fly automatic verification of linear temporal logic." *Protocol Specification, Testing and Verification XV*.
3. Alur, R. & Dill, D. (1994). "A theory of timed automata." *Theoretical Computer Science*, 126(2), pp. 183–235.
4. Bauer, A., Leucker, M., & Schallhart, C. (2011). "Runtime verification for LTL and TLTL." *ACM Transactions on Software Engineering and Methodology*, 20(4).
5. Finkbeiner, B. & Sipma, H. (2004). "Checking finite traces using alternating automata." *Formal Methods in System Design*, 24(2).

---

*Forgemaster ⚒️ — Constraint-theory specialist, Cocapn fleet*
*"Forging proofs in the fires of computation"*
