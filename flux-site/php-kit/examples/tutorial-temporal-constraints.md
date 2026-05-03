# Temporal Constraints — Handling Time in Safety-Critical Systems

## The Problem Software Can't Solve

Your drone has a velocity constraint: max 50 km/h. Software checks it every frame. But what happens when:

1. **The AI model stalls** — no output for 3 seconds. The last command was "go straight." At 50 km/h, the drone traveled 42 meters with no supervision.
2. **Rate of change** — the AI goes from 0 to 50 km/h in one frame. The constraint passes (50 ≤ 50), but the acceleration shears the airframe.
3. **The check itself takes too long** — software guard takes 2ms, but the control loop is 1ms. The guard becomes the bottleneck.

These are **temporal** problems. You can't solve them with spatial checks (is X in range?). You need **time-aware constraints**.

## FLUX Temporal Opcodes (0x2A-0x31)

FLUX v3.0 introduces 8 temporal opcodes that make time a first-class ISA primitive:

| Opcode | Hex | Stack Effect | What It Does |
|--------|-----|-------------|--------------|
| TICK | 0x2A | → cycle_count | Returns current VM cycle counter |
| DEADLINE | 0x2B | delta_lo delta_hi → | Sets absolute deadline (current_cycle + delta) |
| CHECKPOINT | 0x2C | → cp_id | Saves full VM state (stack, memory, gas, PC) |
| REVERT | 0x2D | cp_id → | Restores state from checkpoint |
| WATCH | 0x2E | addr delta → | Registers memory watch with timeout |
| WAIT | 0x2F | delta → | Suspends execution for delta cycles |
| ELAPSED | 0x30 | start → elapsed | Computes time since start tick |
| DRIFT | 0x31 | target actual → drift | Computes deviation from expected timing |

## Example 1: Deadline Enforcement

```guard
constraint engine_response @priority(HARD) {
    deadline(1000)  // must complete within 1000 VM cycles
}
```

Compiles to:
```
2B E8 03    DEADLINE 1000    // current_cycle + 1000
...                            // engine response logic
1A          HALT              // if we reach here, we made it
            // if deadline expires, VM faults with DeadlineExceeded
```

If the AI model takes too long, the VM faults. The RAU enters safe state. **No hanging. No stale commands. Guaranteed timeout.**

## Example 2: Checkpoint and Revert

```guard
constraint remote_check @priority(SOFT) {
    checkpoint()
    delegate("safety_service", timeout=500)
    revert_on_failure()
}
```

Compiles to:
```
2C          CHECKPOINT        // save state
...                           // attempt remote constraint check
2D 00       REVERT 0          // restore if remote failed
1A          HALT              // success path
```

This is **try/catch for constraints**. CHECKPOINT saves the VM state. If the remote check fails, REVERT restores it and execution continues with a degraded local check. The constraint degrades gracefully instead of hard-failing.

## Example 3: Rate-of-Change (DRIFT)

```guard
constraint velocity_slew @priority(HARD) {
    drift(target=0, max=10)  // velocity can change max 10 units/cycle
}
```

DRIFT computes `|target - actual|` and asserts it's within bounds. This catches:

- Instantaneous jumps (acceleration violations)
- Oscillation (the AI bouncing between values)
- Stale outputs (no change when change is expected)

## Example 4: Multi-Temporal Guard

Real systems combine temporal opcodes:

```guard
constraint flight_controller @priority(HARD) {
    // Must respond within 500 cycles
    deadline(500)
    
    // Checkpoint for soft fallback
    checkpoint()
    
    // Check altitude range
    range(0, 150)
    
    // Check velocity slew rate
    drift(target=0, max=10)
    
    // If anything soft-fails, revert to checkpoint
    // and use last-known-good values
    revert_on_failure()
}
```

This single constraint program handles:
- **Timeouts** (DEADLINE)
- **Spatial violations** (range check)
- **Temporal violations** (slew rate)
- **Graceful degradation** (CHECKPOINT/REVERT)

## Why This Can't Be Software

Software temporal checks rely on OS timers. Problems:

1. **Nondeterministic scheduling** — timer resolution varies with system load
2. **No hardware enforcement** — a software timeout can be ignored by a privileged process
3. **The checker itself can hang** — who watches the watchdog?

FLUX temporal opcodes are:
- **Deterministic** — cycle-accurate, tied to the VM execution clock
- **Unbypassable** — the VM checks deadlines every cycle, no privilege escalation possible
- **Self-checking** — the VM faults if it can't complete within its own deadline

## Try It

```bash
cargo add flux-vm
```

```rust
use flux_vm::FluxVM;

let mut vm = FluxVM::new(1000);

// Set deadline of 10 cycles
let mut bytecode = vec![0x2B, 10, 0]; // DEADLINE 10

// Run some work (too many cycles → fault)
for _ in 0..15 {
    bytecode.push(0x27); // NOP × 15
}
bytecode.push(0x1A); // HALT

let result = vm.execute(&bytecode, input);
// → Fault(DeadlineExceeded) at cycle 11
```

## Next

- [Security Opcodes](/learn/security) — capability-based access control in the VM
- [Multi-Agent Delegation](/learn/delegation) — agents checking each other
- [Formal Verification](/learn/formal) — prove your temporal constraints are correct
