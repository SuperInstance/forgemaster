# FLUX Temporal Opcodes — ISA v3.0 Design

## The Problem

Traditional error handling (try/catch, Result types) is **spatial** — it handles failures at the point they occur. But autonomous agent coordination produces **temporal** failures:

- Agent doesn't respond within deadline → not a crash, a timeout
- Partial response from multi-agent consensus → not invalid, just incomplete
- Constraint satisfaction drifts over time → not violated yet, but trending toward violation
- Agent responds but too late → response is valid but stale

These are **temporal failures**, and try/catch can't express them. You can't `catch` a timeout at the instruction level — you have to build a whole event loop, timer system, and state machine at the application layer. That's exactly the kind of software that fails DO-254 audits.

## The Design: Temporal Opcodes as First-Class ISA Primitives

FLUX v3.0 adds temporal opcodes that make timeout, checkpoint, revert, and drift-detection **instruction-level operations** — no application-level event loop needed.

### The Key Insight

A constraint VM already has a gas counter (deterministic execution bound) and a program counter (where you are in execution). Adding **temporal awareness** means:

1. **Cycle counter** — how many real clock cycles since constraint execution started
2. **Checkpoint stack** — saved VM states you can revert to
3. **Deadline register** — absolute cycle count by which execution MUST complete
4. **Watch register** — signal being monitored for change within a window

These are registers, not data structures. They're part of the VM state, formally verifiable, and their behavior is defined per-opcode in the ISA spec.

## Temporal Opcodes

### T0: TICK — Push current cycle count
```
TICK → ( -- cycle_count:u32 )
```
Reads the hardware cycle counter. Used to establish temporal baselines.

### T1: DEADLINE set — Set absolute deadline
```
DEADLINE cycles → ( -- )
```
Sets the deadline register. If `cycle_count > deadline` at any point, triggers `TIMEOUT_FAULT` instead of the normal `GAS_EXHAUSTED`. This is different from gas — gas bounds *computation*, deadline bounds *wall-clock time waiting for external events*.

### T2: CHECKPOINT push — Save VM state
```
CHECKPOINT → ( -- checkpoint_id:u8 )
```
Snapshots the current VM state (stack, memory, PC, gas) onto a checkpoint stack (max 8 deep). Returns a checkpoint ID. This is the ISA-level equivalent of a transaction begin.

### T3: REVERT id — Roll back to checkpoint
```
REVERT checkpoint_id → ( -- )
```
Restores VM state to the checkpoint. Stack, memory, gas — everything. The VM state after REVERT is *identical* to the state at the corresponding CHECKPOINT. This is the ISA-level equivalent of a transaction rollback.

Critical: REVERT does NOT trigger a fault. It's a *soft failure* — "this path didn't work, try another." The constraint VM can CHECKPOINT, attempt a remote constraint check, and REVERT if the remote agent doesn't respond.

### T4: WATCH signal, timeout — Monitor external signal
```
WATCH signal_ref timeout_cycles → ( -- watch_id:u8 )
```
Registers a watch on an external signal (from another agent, sensor, etc.). If the signal doesn't change within `timeout_cycles`, triggers `WATCH_EXPIRED` (soft fault, not hard fault).

This is the instruction-level timeout primitive. No event loop. No callback. The VM itself tracks whether the watched signal changed.

### T5: WAIT watch_id — Block until watched signal changes
```
WAIT watch_id → ( -- new_value )
```
Suspends VM execution until the watched signal changes or expires. If the signal changes before timeout, pushes the new value. If timeout fires first, pushes `0` and sets `watch_expired` flag.

The caller checks the flag:
```
WATCH remote.altitude 1000    // watch for 1000 cycles
WAIT 0                         // block until change or timeout
DUP
JZ handle_timeout              // 0 = timed out
// ... use new value
```

### T6: ELAPSED — Time since checkpoint
```
ELAPSED checkpoint_id → ( -- cycles:u32 )
```
Pushes the number of cycles elapsed since the given checkpoint was created. Used for temporal guards: "if more than N cycles have passed since we started this check, switch to degraded mode."

### T7: DRIFT signal, checkpoint — Detect constraint drift
```
DRIFT signal_ref checkpoint_id → ( -- delta:f64 )
```
Computes the difference between the signal's current value and its value at the checkpoint. Not a violation — just the drift. The constraint program can branch on drift magnitude:

```
DRIFT velocity cp0
DUP
PUSH 10        // threshold
GT
JZ stable
PUSH 50        // higher threshold
GT
JZ warning
GUARD_TRAP     // hard violation — drift too large
stable:
// ... normal execution
warning:
// ... switch to degraded mode
```

This is **predictive constraint enforcement** — catch violations BEFORE they happen.

## State Machine: How Temporal Opcodes Interact

```
IDLE → CHECKPOINT → (attempt remote check)
                         │
                    ┌─────┴──────┐
                    │            │
              SUCCESS         TIMEOUT/FAIL
                    │            │
                    │        REVERT to checkpoint
                    │            │
                    │        (try degraded mode)
                    │            │
                    │        ┌───┴───┐
                    │        │       │
                    │    SUCCESS  TIMEOUT
                    │        │       │
                    │        │   DEADLINE_FAULT
                    │        │       │
                    ▼        ▼       ▼
                 HALT      HALT   GUARD_TRAP
```

The key: REVERT is NOT a fault. It's a controlled rollback. The VM can attempt, fail softly, rollback, and try a different approach — all within a single constraint program, all within the gas budget.

## Comparison: Traditional vs Temporal Error Handling

| Scenario | Traditional (try/catch) | FLUX Temporal ISA |
|----------|------------------------|-------------------|
| Remote agent timeout | Application event loop + timer + callback | `WATCH` + `WAIT` + `JZ timeout` |
| State reversion | Manual state save/restore in application code | `CHECKPOINT` + `REVERT` (one instruction each) |
| Deadline enforcement | OS-level timer, SIGALRM, non-deterministic | `DEADLINE` register, cycle-accurate, deterministic |
| Drift detection | Polling loop comparing current vs previous | `DRIFT` opcode, single instruction |
| Degraded mode | if/else chain in application code | `REVERT` → branch on `ELAPSED` → alternative path |
| Certification | Must prove timer system correct | Timer IS the ISA, prove 7 opcodes correct |

## Certification Argument

DO-254 DAL A requires deterministic behavior. The temporal opcodes are deterministic:

1. **TICK**: Reads a monotonically increasing counter. Deterministic.
2. **DEADLINE**: Sets a register. Comparison is deterministic.
3. **CHECKPOINT**: Copies VM state to checkpoint stack. Deterministic.
4. **REVERT**: Copies checkpoint back to VM state. Deterministic.
5. **WATCH**: Registers a signal address + timeout. Deterministic setup.
6. **WAIT**: Blocks until signal change OR timeout. Both outcomes defined.
7. **ELAPSED**: Subtracts two counters. Deterministic.
8. **DRIFT**: Subtracts current value from checkpoint value. Deterministic.

All 8 opcodes have defined behavior for all inputs. No undefined behavior, no nondeterminism, no OS dependencies. The VM's temporal behavior is fully specified by the ISA, making it tractable for Coq verification.

## Connection to Universal AST

The `DelegateNode` and `CoIterateNode` from `flux-ast` compile to temporal opcodes:

```rust
// DelegateNode { source, target, constraint, protocol: Sync }
// compiles to:
DEADLINE 1000        // 1000 cycle deadline for remote check
CHECKPOINT           // save state in case of timeout
WATCH target.result 500  // watch for 500 cycles
PUSH target_constraint   // the constraint to check
WAIT 0               // block for result
DUP
JZ timeout_path      // timed out → soft fail
// ... check result ...
JMP done
timeout_path:
REVERT 0             // rollback to checkpoint
// ... degraded mode ...
done:
```

```rust
// CoIterateNode { agents, constraints, convergence: MaxIterations(10), ... }
// compiles to:
DEADLINE 5000
CHECKPOINT           // outer checkpoint
PUSH 0               // iteration counter
iterate:
DUP
PUSH 10
GTE
JZ continue
REVERT 0             // exceeded iterations, rollback
JMP degraded
continue:
// ... check constraints across agents ...
// ... if not converged, increment counter and loop ...
ELAPSED 0
PUSH 4500
GT
JZ iterate           // still within budget, keep iterating
REVERT 0             // running out of time, rollback
degraded:
// ... degraded mode ...
```

The AST expresses INTENT (delegate, co-iterate). The ISA provides MECHANISM (checkpoint, revert, watch, deadline). The compiler bridges them.

## Opcode Encoding (proposed)

| Opcode | Hex | Operands | Gas | Stack Effect |
|--------|-----|----------|-----|--------------|
| TICK | 0x2A | none | 1 | `( -- cycle_count )` |
| DEADLINE | 0x2B | u32 | 1 | `( cycles -- )` |
| CHECKPOINT | 0x2C | none | 3 | `( -- cp_id )` |
| REVERT | 0x2D | u8 | 5 | `( cp_id -- )` |
| WATCH | 0x2E | ref, u32 | 2 | `( signal timeout -- watch_id )` |
| WAIT | 0x2F | u8 | 1+ | `( watch_id -- value )` |
| ELAPSED | 0x30 | u8 | 1 | `( cp_id -- cycles )` |
| DRIFT | 0x31 | ref, u8 | 2 | `( signal cp_id -- delta )` |

Gas costs: CHECKPOINT and REVERT are expensive (memory copy). WATCH and WAIT interact with external signals. TICK, ELAPSED, DRIFT are cheap reads.

## What This Enables

1. **Certified multi-agent coordination**: The constraint VM can express "wait for Oracle1's response for at most 1000 cycles, then fall back to local constraint check" as a *single program*, not an event loop.

2. **Predictive constraint enforcement**: DRIFT detects violations BEFORE they happen. The system can degrade gracefully instead of hard-faulting.

3. **Transaction semantics for constraints**: CHECKPOINT/REVERT gives the VM ACID-like properties — atomic constraint evaluation with controlled rollback.

4. **Deterministic timeouts**: No OS timers, no signals, no nondeterminism. The VM itself tracks time. Fully auditable.

5. **Soft failure as a first-class concept**: Not every missed deadline is a catastrophe. REVERT + degraded mode is the ISA-level "try something else" primitive.
