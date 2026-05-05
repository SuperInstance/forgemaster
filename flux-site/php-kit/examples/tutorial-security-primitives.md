# Security Primitives — Capability-Based Safety in the Constraint VM

## The Problem: Ambient Authority

Traditional systems grant access based on identity. "Process X can write to memory region Y." But what happens when:

1. A model update grants the AI broader permissions than intended
2. A compromised agent inherits its creator's full access
3. Two agents share a memory region and one corrupts it for the other

This is **ambient authority** — access that exists because of who you are, not what you specifically need. The FLUX VM eliminates it.

## Capability-Based Security (seL4 Model)

FLUX v3.0 security opcodes implement capability-based access control, modeled after the seL4 microkernel:

| Opcode | Hex | Stack Effect | What It Does |
|--------|-----|-------------|--------------|
| SANDBOX_ENTER | 0x32 | domain → | Enter isolated execution domain |
| SANDBOX_EXIT | 0x33 | → | Leave sandbox, restore previous domain |
| CAP_GRANT | 0x34 | target permissions → cap_id | Grant capability to memory region |
| CAP_REVOKE | 0x35 | cap_id → | Immediately revoke capability |
| MEM_GUARD | 0x36 | addr size permissions → | Set hardware-style memory protection |
| PROVE | 0x37 | assertion → result | Zero-knowledge proof primitive |
| AUDIT_PUSH | 0x38 | event → | Push event to audit log |
| SEAL | 0x39 | addr size → | Permanently seal memory region |

## Principle: No Ambient Authority

In the FLUX VM, a newly created execution context has **zero permissions**. Every memory access, every constraint check, every delegation requires an explicit capability grant.

```
// Before: ambient authority (traditional)
AI_model.write(memory_region, value)  // allowed because AI_model has "write" permission

// After: capability-based (FLUX)
cap_id = CAP_GRANT(AI_model, memory_region, READ|WRITE)
AI_model.write(cap_id, memory_region, value)  // allowed only if cap_id is valid
CAP_REVOKE(cap_id)  // immediately invalidated
AI_model.write(cap_id, memory_region, value)  // FAULT: capability revoked
```

## Example 1: Sandboxing a Model Check

```guard
constraint model_output @priority(HARD) {
    // Enter sandbox — model output can only access approved memory
    sandbox(domain=5)
    range(0, 100)
    // Exit sandbox — restore full execution context
}
```

Compiles to:
```
32 05       SANDBOX_ENTER 5     // isolate execution
1D 00 64    BITMASK_RANGE 0 100
1B          ASSERT
33          SANDBOX_EXIT        // restore context
1A          HALT
```

The constraint check runs in an isolated memory domain. Even if the model output is adversarial, it cannot access memory outside domain 5.

## Example 2: Capability Grant/Revoke

```guard
constraint delegation @priority(HARD) {
    // Grant temporary read access for remote check
    cap = grant(target="safety_svc", permissions=READ)
    
    // Revoke immediately after check
    revoke(cap)
}
```

The capability is an unforgeable token. The target receives `cap_id` (an integer), but the VM maintains the actual permission mapping internally. The target cannot:
- Escalate permissions (READ → READ|WRITE)
- Delegate to another agent (unless explicitly allowed)
- Use the capability after revocation

Revocation is **immediate and synchronous**. No grace period, no eventual consistency.

## Example 3: Sealed Memory

```guard
constraint calibration @priority(HARD) {
    // Write calibration data
    write(0x1000, calibration_data)
    
    // Seal it permanently
    seal(0x1000, 256)
}
```

After SEAL, memory region [0x1000, 0x1000+256] is:
- **Readable** — any execution context can read it
- **Immutable** — no subsequent write can modify it
- **Permanent** — the seal cannot be removed, even by the creator

This is how calibration constants, safety parameters, and certification evidence are protected. Once sealed, not even a system update can change them without full re-certification.

## Example 4: Audit Trail

```guard
constraint critical_action @priority(HARD) {
    audit_push("constraint_check_started")
    range(0, 150)
    audit_push("range_check_passed")
    deadline(100)
    audit_push("deadline_check_passed")
}
```

Every AUDIT_PUSH writes an immutable event to the audit log with:
- Timestamp (VM cycle count)
- Event description
- Current execution context (sandbox domain, capability state)
- Stack hash (proof of execution path)

The audit log is append-only. It cannot be modified, deleted, or backdated. For certification (DO-254 DAL A), this provides the evidence trail auditors require.

## The Security Hierarchy

```
┌─────────────────────────────────┐
│  FLUX-X (247 opcodes)           │  General compute
│  ┌───────────────────────────┐  │
│  │  FLUX-C (42 opcodes)      │  │  Certified enclave
│  │  ┌─────────────────────┐  │  │
│  │  │  SANDBOX (isolated) │  │  │  Constrained execution
│  │  │  CAP_GRANT only     │  │  │  No ambient authority
│  │  │  SEALED calibration │  │  │  Immutable parameters
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

FLUX-X wraps FLUX-C (TrustZone model). FLUX-C wraps sandboxes. Each layer restricts what's possible. Certification scope is limited to FLUX-C's 42 opcodes — the security primitives enforce the boundary.

## Comparison: FLUX vs Traditional Guards

| Aspect | Software Guard | FLUX VM |
|--------|---------------|---------|
| Authority model | Ambient (process-based) | Capability-based (token-based) |
| Memory protection | OS virtual memory | Hardware-style MEM_GUARD |
| Revocation | Process kill (async) | CAP_REVOKE (sync, immediate) |
| Immutability | File permissions | SEAL (permanent, uncircumventable) |
| Audit trail | Application logging | ISA-level AUDIT_PUSH (append-only) |
| Bypass resistance | Kernel exploit | Formal verification + FPGA |

## Try It

```rust
use flux_vm::FluxVM;

let mut vm = FluxVM::new(1000);

// Sandbox a constraint check
let bytecode = vec![
    0x32, 5,        // SANDBOX_ENTER domain 5
    0x00, 42,       // PUSH 42
    0x1D, 0, 100,   // BITMASK_RANGE 0 100
    0x1B,           // ASSERT
    0x33,           // SANDBOX_EXIT
    0x1A,           // HALT
];

vm.execute(&bytecode, 0).unwrap();
// → Passed: sandbox constraint in domain 5
```

## Next

- [Temporal Constraints](/learn/temporal) — time-aware safety
- [Multi-Agent Delegation](/learn/delegation) — agents checking each other's outputs
- [Hardware Implementation](/learn/hardware) — FPGA synthesis of security primitives
