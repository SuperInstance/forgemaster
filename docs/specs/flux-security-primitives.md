# FLUX Security Primitives — VM-Level Memory Safety

## Design Thought #3: Developer-Kernel Symbiosis

The review says: "If the OS can rewrite itself, your language needs Security Primitives that are hardware-enforced."

This is correct. FLUX OS breaks the user/kernel boundary — the kernel IS the compiler.
That means the constraint VM must be the security boundary, not the OS.

## The Problem

Traditional security relies on privilege levels:
- User mode → can't touch kernel memory
- Kernel mode → can touch everything
- MMU enforces the boundary

FLUX OS has no MMU. The VM IS the memory controller.
So security primitives must be IN THE ISA, not AROUND IT.

## Security Opcodes (v3.0, alongside temporal)

### S0: SANDBOX_ENTER — Enter isolated execution domain
```
SANDBOX_ENTER domain_id → ( -- )
```
Creates an isolated memory domain. All subsequent memory accesses
are restricted to the sandbox's allocated region. Stack is shared
(across domains), but memory is partitioned.

### S1: SANDBOX_EXIT — Leave isolated execution domain
```
SANDBOX_EXIT → ( -- )
```
Returns to the parent domain. Restores memory access permissions.
Any attempt to access memory outside the current domain triggers
`SandboxViolation` fault.

### S2: CAP_GRANT — Grant capability to memory region
```
CAP_GRANT domain_id start len perm → ( -- cap_id )
```
Creates a capability token that grants access to a memory region
[start, start+len) with permissions (READ=1, WRITE=2, EXEC=4).
Capabilities are unforgeable — they're checked by the VM, not by code.

### S3: CAP_REVOKE — Revoke capability
```
CAP_REVOKE cap_id → ( -- )
```
Revokes a capability. Any subsequent access using this cap_id fails.
This is the "time-of-check-to-time-of-use" (TOCTOU) protection —
capabilities can be revoked at any time, and revoked caps are immediately
invalid.

### S4: MEM_GUARD — Set memory range guard
```
MEM_GUARD start end perm → ( -- guard_id )
```
Sets a hardware-style memory guard on [start, end). Any access
violating perm triggers `MemoryGuardFault`. This is the VM-level
equivalent of ARM's MPU (Memory Protection Unit).

### S5: PROVE — Assert invariant at this point
```
PROVE invariant_id → ( -- )
```
Marks an invariant that MUST hold at this program point.
The VM checks the invariant at runtime (like ASSERT) but also
records it for static analysis. The compiler can use PROVE markers
to generate formal verification obligations.

### S6: AUDIT_PUSH — Push audit record
```
AUDIT_PUSH event_type → ( -- )
```
Records an audit event. The event is appended to a append-only
audit log (CRDT-merged across agents). Audit records are immutable —
once pushed, they cannot be modified or deleted.

### S7: SEAL — Make memory region read-only
```
SEAL start len → ( -- )
```
Makes a memory region permanently read-only. No subsequent instruction
(including kernel-mode code) can modify sealed memory. This is the
VM-level equivalent of Linux's `mprotect` with PROT_READ only,
but it CANNOT be reversed — sealed is forever within the execution.

## Why These Are Hardware-Enforced

These aren't software checks that can be bypassed with a pointer cast.
They're VM-level invariants:

1. **SANDBOX** — The VM's memory access function checks domain membership
   BEFORE any read/write. No way to skip the check.

2. **CAP_GRANT/REVOKE** — Capabilities are VM-internal tokens.
   Code sees a cap_id (integer), but the VM maintains the actual
   permission mapping. Forging a cap_id does nothing — the VM's
   internal table is the authority.

3. **MEM_GUARD** — Hardware MPU mapped to VM memory access.
   On FPGA, this is a range comparator in the memory bus.
   On ASIC, it's a gate that physically disconnects write lines.

4. **SEAL** — Permanent flag in VM memory metadata.
   Once set, the VM's memory access function rejects ALL writes.
   Even if the program counter somehow reaches a STORE instruction,
   the memory controller rejects it.

5. **PROVE** — Dual-use: runtime assertion + static analysis marker.
   The compiler extracts PROVE markers and generates Coq verification
   obligations. The VM checks them at runtime as defense-in-depth.

## Capability-Based Security Model

The security model is capability-based, not identity-based:

```
Agent A wants to read memory[1000..2000]
  │
  ├── Does Agent A have CAP_GRANT for [1000..2000] with READ?
  │     YES → allow
  │     NO  → MemoryGuardFault
  │
  └── Is [1000..2000] in Agent A's SANDBOX domain?
        YES → allow (sandbox membership implies read)
        NO  → check capabilities
```

This is the same model as seL4's capabilities:
- No ambient authority (no "root" access)
- All access requires explicit capability grant
- Capabilities can be delegated (but only to lesser permissions)
- Revocation is immediate and non-revocable

## Connection to Universal AST

The AST's DelegateNode compiles to security primitives:

```rust
// DelegateNode { source: "A", target: "B", constraint, protocol: Sync }
// compiles to:
SANDBOX_ENTER 1              // enter delegation domain
CAP_GRANT 1 1000 256 1       // grant B read access to constraint data
AUDIT_PUSH 0x01              // log delegation start
// ... remote constraint check ...
CAP_REVOKE 0                 // revoke capability (one-time use)
SANDBOX_EXIT                 // return to parent domain
AUDIT_PUSH 0x02              // log delegation complete
```

The capability is granted for exactly one constraint check,
then immediately revoked. This is the principle of least authority
(POLA) at the ISA level.

## Liquid Types Analogy

The review mentions Liquid Types. Here's the connection:

Liquid Types extend Rust's type system with refinement predicates:
```rust
fn velocity(v: i32) -> i32 { v } // where v >= 0 && v <= 300
```

FLUX implements this at the VM level:
```
PUSH velocity_value
MEM_GUARD 0x0000 0xFFFF 5  // only READ+EXEC, no WRITE
PROVE 0                     // invariant 0: bounds check
BITMASK_RANGE 0 300
ASSERT
```

The MEM_GUARD prevents modification of the constraint program itself
(self-modifying code protection). The PROVE marker generates the
formal verification obligation. The ASSERT is the runtime check.

Three layers of safety:
1. **Static**: PROVE generates Coq lemma
2. **VM**: MEM_GUARD prevents tampering
3. **Runtime**: ASSERT catches violations

## Implementation Status

| Opcode | Hex | Status | Purpose |
|--------|-----|--------|---------|
| SANDBOX_ENTER | 0x32 | Spec | Enter isolated memory domain |
| SANDBOX_EXIT | 0x33 | Spec | Leave isolated memory domain |
| CAP_GRANT | 0x34 | Spec | Grant memory capability |
| CAP_REVOKE | 0x35 | Spec | Revoke memory capability |
| MEM_GUARD | 0x36 | Spec | Set memory range guard |
| PROVE | 0x37 | Spec | Assert invariant + static analysis |
| AUDIT_PUSH | 0x38 | Spec | Append immutable audit record |
| SEAL | 0x39 | Spec | Permanently seal memory region |

These are the next opcodes to implement after the temporal set (0x2A-0x31).
The encoding follows the same pattern as FLUX-C: fixed opcode byte,
variable operands, 1 gas per opcode (3 for CAP_GRANT, 5 for SEAL).

## The Answer to the Review's Question

> "Should we focus next on the security primitives for the FLUX OS microkernel
> or the bytecode compression strategy for the ISA v3.0?"

**Both.** Security primitives (0x32-0x39) define WHAT the VM protects.
Bytecode compression (.fluxb binary format) defines HOW efficiently
protection rules are expressed. They're complementary:

- Security without compression = correct but slow (can't fit in FPGA BRAM)
- Compression without security = fast but unsafe (no memory protection)
- Both together = safe AND efficient (capabilities fit in 4-byte instructions)

Priority: implement security opcodes in the VM first (provable),
then compress the bytecode format (optimization, not correctness).
