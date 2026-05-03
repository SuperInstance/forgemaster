# Multi-Agent Delegation — When One Constraint Isn't Enough

## The Problem: Single-Agent Safety is Insufficient

A self-driving car has:
- A perception model (detects objects)
- A planning model (chooses path)
- A control model (steers/brakes)
- A safety monitor (checks all outputs)

Each model produces outputs that affect the others. The perception model says "pedestrian at 10m." The planner says "accelerate." The safety monitor says "stop."

Who wins? In traditional systems, the last writer wins. In FLUX, **constraints win**.

## The Delegate AST Node

The Universal Constraint AST represents delegation as a first-class operation:

```rust
DelegateNode {
    source: "safety_monitor",
    target: "planner",
    constraint: BoundNode { ... },
    protocol: CoIterate,  // collaborative, not fire-and-forget
}
```

This says: "The safety monitor delegates a constraint to the planner. They collaborate (CoIterate) to find a plan that satisfies the constraint."

### Delegation Protocols

| Protocol | Behavior | Use When |
|----------|----------|----------|
| `Tell` | Source tells target the constraint. No response expected. | Advisory constraints |
| `Ask` | Source asks target to evaluate. Expects yes/no. | Quick validation checks |
| `CoIterate` | Source and target iterate together until convergence. | Complex negotiation |
| `Fork` | Target evaluates independently. Source continues. | Parallel verification |
| `Branch` | Target chooses between alternative constraints. | Decision trees |

## Example 1: Tell (Advisory)

The safety monitor tells the planner about a speed limit:

```guard
constraint speed_limit @priority(HARD) {
    tell("planner", range(0, 50))
}
```

Compiles to FLUX-C:
```
00 32        PUSH 50         // limit
1D 00 32     BITMASK_RANGE 0 50
1B           ASSERT
1A           HALT
```

The planner receives the constraint and must respect it. No negotiation. Hard constraints are non-negotiable.

## Example 2: Ask (Validation)

The planner asks the safety monitor to validate a path:

```guard
constraint path_validation @priority(SOFT) {
    ask("safety_monitor", path)
    checkpoint()
    revert_on_timeout(100)
}
```

Compiles to:
```
2C           CHECKPOINT      // save state before asking
...          // send path to safety_monitor via A2A protocol
2F 64        WAIT 100        // wait up to 100 cycles for response
2D 00        REVERT 0        // if timeout, revert to checkpoint
1A           HALT
```

CHECKPOINT + WAIT + REVERT = async request with deterministic timeout. If the safety monitor doesn't respond, the planner uses the checkpoint state (last-known-good path).

## Example 3: CoIterate (Negotiation)

Two agents negotiate on a shared constraint:

```guard
constraint joint_safety @priority(HARD) {
    coiterate("perception", "planner",
        constraint: range(0, 100),
        max_rounds: 5,
        convergence: drift < 1.0)
}
```

The AST captures:
```rust
CoIterateNode {
    agents: ["perception", "planner"],
    constraint: BoundNode::Range(0, 100),
    max_rounds: 5,
    convergence: DriftNode { threshold: 1.0 },
}
```

Each round:
1. Perception proposes a value
2. Planner checks if it satisfies the constraint
3. If yes, done. If no, planner proposes counter-value
4. Check convergence (DRIFT < threshold)
5. If 5 rounds without convergence, fault with `CoIterateDivergence`

**This is mathematically equivalent to constraint propagation** — the same algorithm used in CSP solvers, but applied to live agent negotiation.

## Example 4: Fork (Parallel Verification)

Two independent safety checks run in parallel:

```guard
constraint dual_verification @priority(HARD) {
    fork([
        ("altitude_check", range(0, 15000)),
        ("airspace_check", whitelist(allowed_zones))
    ])
    join(any_pass=false)  // ALL must pass
}
```

Fork creates parallel execution branches. Each branch runs its constraint independently. `join(any_pass=false)` means ALL branches must pass. If any branch faults, the whole constraint faults.

This is how you get **N-version programming** at the constraint level — two independent implementations of the same safety check, both must agree.

## The A2A Signal Protocol

FLUX uses Oracle1's A2A (Agent-to-Agent) Signal Protocol for inter-agent communication:

| Signal | Opcode | Meaning |
|--------|--------|---------|
| TELL | 0x40 | One-way constraint declaration |
| ASK | 0x41 | Request evaluation |
| BRANCH | 0x42 | Choose between alternatives |
| FORK | 0x43 | Create parallel evaluation |
| JOIN | 0x44 | Merge parallel results |
| YIELD | 0x45 | Temporarily release execution |
| MERGE | 0x46 | CRDT-merge concurrent results |

These opcodes are in the FLUX-X ISA (general compute), not FLUX-C (certified enclave). The certified enclave handles single-agent constraints; the general ISA handles multi-agent coordination.

## Constraint Isolation Guarantee

When Agent A delegates to Agent B:

1. A's state is CHECKPOINT'd
2. B receives only the constraint (not A's full state)
3. B evaluates independently in its own SANDBOX
4. B's response is the only data that crosses back to A
5. A REVERTs to checkpoint, applies B's response

This means:
- A cannot corrupt B (sandbox isolation)
- B cannot corrupt A (checkpoint revert)
- The only communication channel is the constraint response
- Side-channel attacks are impossible by construction

## Try It

```rust
use flux_vm::FluxVM;
use flux_ast::{DelegateNode, CoIterate};

// Define delegation
let delegation = DelegateNode::new(
    "safety_monitor",
    "planner",
    BoundNode::range(0, 100),
    Protocol::CoIterate { max_rounds: 5 },
);

// Compile to FLUX bytecode
let bytecode = delegation.compile();

// Execute on VM
let mut vm = FluxVM::new(1000);
let result = vm.execute(&bytecode, 0);
```

## Next

- [Universal AST](/learn/ast) — single source of truth for all constraint representations
- [CRDT Merge](/learn/crdt) — distributed constraint reconciliation
- [Formal Verification](/learn/formal) — prove delegation protocols are correct
