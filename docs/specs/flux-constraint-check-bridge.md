# FLUX-X ⟷ FLUX-C Bridge Specification
## `CONSTRAINT_CHECK` — TrustZone-Style Secure Monitor Call

**Status:** Draft  
**Date:** 2026-05-03  
**Based on:** ARM TrustZone SMC model, DO-254 DAL-A TCB requirements  
**Prerequisites:** `flux-isa` (FLUX-X, 247-opcode register machine), `flux-vm` (FLUX-C, 43-opcode stack machine)

---

## 1. Overview

FLUX-X (the 247-opcode register machine) executes general fleet compute: tensor ops, agent coordination, PLATO bridges. FLUX-C (the 43-opcode stack machine) is the formally-verified, certifiable Constraint VM that evaluates GUARD invariants at runtime.

`CONSTRAINT_CHECK` is the **only** mechanism by which FLUX-X can invoke FLUX-C. It is modeled on the ARM TrustZone `SMC` (Secure Monitor Call):

- FLUX-X issues `CONSTRAINT_CHECK` in privileged mode.
- Execution traps to the **FLUX Monitor**, a minimal trusted switch logic.
- The Monitor saves FLUX-X context, validates the request, dispatches FLUX-C, and returns or faults.
- FLUX-C **cannot** call back into FLUX-X. It has no `RET_TO_X` opcode; its only exit path is `HALT`, which signals the Monitor.

This document specifies the opcode encoding, calling convention, context switch, fault handling, and security invariants.

---

## 2. Opcode Encoding

### 2.1 `CONSTRAINT_CHECK` — FLUX-X System Opcode

```
31      24 23     20 19     16 15      8 7       0
+----------+---------+---------+----------+----------+
|  0xF0    |  FLAGS  |  RESV   |  INPUTS  |   RESV   |
+----------+---------+---------+----------+----------+
|  Opcode  |  [3:0]  |  (0x0)  |  [3:0]   |  (0x00)  |
+----------+---------+---------+----------+----------+
```

| Field | Bits | Description |
|-------|------|-------------|
| `Opcode` | 31:24 | `0xF0` — privileged system call into FLUX-C. Illegal in user/untrusted FLUX-X mode. |
| `FLAGS` | 23:20 | Bit 3 = `ASYNC` (0 = blocking, 1 = post result to interrupt queue). Bits 2:0 = Reserved (MBZ). |
| `RESV` | 19:16 | Must Be Zero. Decoders must fault if non-zero (anti-spoofing). |
| `INPUTS` | 15:8 | Input count minus one. `0x0` = 1 input register used, `0xE` = 15 inputs, `0xF` = 16 inputs (R0 used as input, no explicit constraint_id in R0 — see §3.2). |
| `RESV` | 7:0 | Must Be Zero. |

**Total opcode space consumed:** 1 byte (`0xF0`). The remaining 24 bits are reserved for future hardening (e.g., capability selectors, domain IDs).

### 2.2 Privilege Check

`CONSTRAINT_CHECK` executes only when FLUX-X `FLAGS.PRIV` == 1. In non-privileged mode the instruction raises `FAULT_ILLEGAL_OPCODE` (FLUX-X local fault) and the local fault handler runs — the bridge is **never** entered.

---

## 3. Bridge Protocol

### 3.1 Register Calling Convention (FLUX-X side)

Before issuing `CONSTRAINT_CHECK`, the caller sets up registers according to the **FLUX Bridge ABI**:

| Register | Direction | Purpose |
|----------|-----------|---------|
| `R0` | In | `constraint_id` (u8). Index into the **Constraint Dispatch Table (CDT)**. |
| `R1` | In/Out | Input 0 (before call). After call: **result code** (see §3.4). |
| `R2` | In/Out | Input 1 (before call). After call: **fault detail** (constraint-specific sub-code or 0). |
| `R3`–`R15` | In | Input 2 through input 14 (as needed by `INPUTS` field). |

**Total inputs:** Up to 15 values in `R1`–`R15`, plus `R0` as the constraint selector.

> **Rationale:** TrustZone SMC uses X0–X7 for arguments and returns results in X0–X3. FLUX-X has more registers, so we map the first two result slots to R1/R2 for efficient constraint-intensive code, while keeping R0 as the immutable selector.

### 3.2 Special Case: INPUTS = 0xF (16 inputs)

When `INPUTS = 0xF`, `R0` is **not** interpreted as a `constraint_id`. Instead:
- `R0` = Input 0.
- The `constraint_id` is implicit: it is the **hash of the next 8 bytes of FLUX-X instruction stream**, or a value loaded into the **Bridge Descriptor Register (BDR)** prior to the call.

This mode exists for hot-path constraints that are called so frequently that saving the `constraint_id` load is worth the encoding complexity. It is optional for implementations.

### 3.3 Register-to-Stack Mapping (Monitor action)

When the Monitor takes the trap:

1. **Validate `constraint_id`** against the CDT. Invalid IDs raise `FAULT_INVALID_CONSTRAINT` → Safe State (§4.2).
2. **Save FLUX-X context** to the Secure Context Block (§5).
3. **Initialize FLUX-C**:
   - Reset FLUX-C SP to `0`.
   - Zero the FLUX-C stack (256 bytes) to prevent data leakage between calls.
   - Set FLUX-C PC to `CDT[constraint_id].entry_addr`.
   - Set FLUX-C gas to `CDT[constraint_id].max_gas`.
4. **Marshal inputs** from FLUX-X to FLUX-C stack:

```
FLUX-X Register     Monitor Action                    FLUX-C Stack (after)
─────────────────────────────────────────────────────────────────────────────
R1 (64-bit)    →  push low 8 bytes as double      [0]  = input 0
R2 (64-bit)    →  push low 8 bytes as double      [1]  = input 1
...            →  ...                             ...
Rn (64-bit)    →  push low 8 bytes as double      [n-1] = input n-1
```

- Values are transferred as **IEEE-754 double-precision** (8 bytes each).
- FLUX-C SP is advanced by `input_count × 8`.
- The FLUX-C stack is 256 bytes → maximum 32 doubles. Since FLUX-X has only 15 argument registers, the maximum transfer is 15 doubles = 120 bytes, well within bounds. The remaining 136 bytes are available for FLUX-C scratch computation.

> **Note:** If FLUX-C operates on 1-byte cells (as in `flux-hardware/vm/flux_vm.rs`), the Monitor packs each 64-bit double into the 8-byte little-endian cell sequence `[b0..b7]`. The constraint bytecode for that variant is compiled accordingly. The bridge spec is agnostic to cell width; it transfers 64-bit values and the FLUX-C implementation defines their interpretation.

### 3.4 FLUX-C Entry Convention

Constraint bytecode compiled for the bridge **must not** begin with `PUSH` instructions for its inputs. The inputs are already on the stack. The bytecode starts immediately with constraint logic (e.g., `LTE`, `AND`, `ASSERT`).

On normal completion, FLUX-C **must**:
1. Leave **exactly one** value on the stack: the result word.
2. Execute `HALT`.

Result word semantics:

| Stack Top Value | Meaning |
|-----------------|---------|
| `0x00` or `0.0` | Constraint **violated** (FAIL). |
| `0x01` or non-zero | Constraint **satisfied** (PASS). |
| `0x02`–`0x0F` | Reserved for future extended result codes. |

If FLUX-C halts with an empty stack or more than one value, the Monitor raises `FAULT_BRIDGE_PROTOCOL` → Safe State.

### 3.5 Return to FLUX-X (Normal Path)

When FLUX-C halts normally:

1. Monitor reads the result word from FLUX-C stack top.
2. Monitor restores FLUX-X registers from the SCB, **except**:
   - `R1` = result code (`0x00` PASS, `0x01` FAIL, or extended code).
   - `R2` = `0x00` (no fault detail on normal path).
   - `FLAGS` is restored with `FLAGS.SAFE` = 0.
3. Monitor restores FLUX-X PC to the instruction after `CONSTRAINT_CHECK`.
4. FLUX-X resumes.

This is a **synchronous, blocking** return. The caller finds the result in R1.

### 3.6 Async Mode (`FLAGS.ASYNC` = 1)

In async mode, the Monitor does not immediately restore FLUX-X context. Instead:
1. FLUX-X continues executing (the Monitor performs a context switch to a ready FLUX-X thread, or resumes the caller with `FLAGS.BRIDGE_PENDING` = 1).
2. When FLUX-C completes, the Monitor posts an **Bridge Completion Interrupt** to FLUX-X.
3. The interrupt handler reads result from a **Bridge Completion Queue (BCQ)** in protected memory.

Async mode is required for constraints that may yield (e.g., sensor-polling constraints in `flux-isa-edge`).

---

## 4. Error Handling & Safe State Transition

### 4.1 FLUX-C Fault Taxonomy

During FLUX-C execution, any of the following faults immediately terminate the constraint evaluation:

| Fault | Source | FLUX-X Result |
|-------|--------|---------------|
| `StackUnderflow` | `flux-hardware` / `flux-isa-c` | Safe State (§4.2) |
| `StackOverflow` | `flux-hardware` / `flux-isa-c` | Safe State |
| `GasExhausted` | Gas counter decremented to 0 | Safe State |
| `AssertFailed` | `ASSERT` opcode pops 0 | Safe State |
| `GuardTrap` | `GUARD_TRAP` opcode (0x20) | Safe State |
| `CallStackOverflow` | `CALL` nested too deep | Safe State |
| `CallStackUnderflow` | `RET` with empty call stack | Safe State |
| `InvalidMemoryAccess` | `LOAD`/`STORE` out of bounds | Safe State |
| `BridgeProtocolViolation` | Monitor-detected protocol error | Safe State |

**Rule:** Any fault inside FLUX-C is **unrecoverable** at the call site. The Monitor does not attempt to resume the calling FLUX-X thread normally. This is a core security invariant: if the TCB cannot evaluate the constraint correctly, the system cannot be trusted to continue the operation that depended on it.

### 4.2 Safe State Transition (Critical Path)

When a fault occurs:

```
1. FLUX-C execution stops immediately (PC frozen, SP frozen).
2. MONITOR logs fault to Provenance Ring Buffer (append-only, 128 entries):
     Entry: { timestamp, constraint_id, fault_code, pc_snapshot, gas_remaining }
3. MONITOR sanitizes FLUX-X architectural state:
     R0  ← 0x00 (sanitized, not used for fault info to avoid confusion with constraint_id)
     R1  ← fault_code (from table above)
     R2  ← constraint_id that caused the fault
     R3  ← FLUX-C PC at fault
     R4  ← gas_remaining
     R5–R15 ← 0x0000_0000_0000_0000  (zeroized to prevent data leakage)
     F0–F15 ← +0.0  (zeroized)
4. MONITOR sets FLUX-X FLAGS:
     FLAGS.SAFE     = 1   (safe mode active)
     FLAGS.PRIV     = 1   (handler runs privileged)
     FLAGS.INT_MASK = 1   (interrupts masked until handler acknowledges)
     FLAGS.BRIDGE   = 0   (bridge no longer busy)
5. MONITOR forces PC to Safe State Vector (SSV):
     PC ← SSV_ADDR (fixed at link time, typically 0xFFFF_0000)
6. FLUX-X resumes at SSV.
```

**Safe State Vector (SSV):**

The SSV is a trusted FLUX-X routine, burned into ROM or loaded and locked by the bootloader. It **must**:

1. Acknowledge the fault by writing `0x01` to the **Bridge Fault Acknowledge Register** (BFAR). This re-enables interrupts.
2. Enter **actuator-safe defaults** (implementation-defined, e.g., throttle 0%, brakes engaged, payload clamps locked).
3. Emit a **Safe-State Heartbeat** to the fleet watchdog.
4. Optionally attempt **graded recovery** (e.g., if fault was `GasExhausted` and a retry counter < `MAX_RETRY`, issue a lighter constraint check). If recovery fails or is not implemented, halt or loop in safe state.

The SSV is **not** allowed to return to the faulting code path. The original FLUX-X PC is lost (intentionally). The only way to exit safe state is a full system reset or an explicit secure re-initialization sequence.

### 4.3 Fault Code Mapping

FLUX-X fault codes (delivered in R1 during safe state):

```
0x10  FAULT_STACK_UNDERFLOW
0x11  FAULT_STACK_OVERFLOW
0x12  FAULT_GAS_EXHAUSTED
0x13  FAULT_ASSERT_FAILED
0x14  FAULT_GUARD_TRAP
0x15  FAULT_CALL_STACK_OVERFLOW
0x16  FAULT_CALL_STACK_UNDERFLOW
0x17  FAULT_INVALID_MEMORY_ACCESS
0x18  FAULT_BRIDGE_PROTOCOL
0x19  FAULT_INVALID_CONSTRAINT_ID
0x1A  FAULT_CDT_LOCK_VIOLATION
0x1B  FAULT_BRIDGE_NESTED_CALL
0x1C  FAULT_UNPRIVILEGED_CALL
```

These are distinct from FLUX-C internal `Fault` enum values to prevent accidental collision with constraint result codes.

---

## 5. Context Switching

### 5.1 Secure Context Block (SCB)

The SCB resides in **Monitor-private RAM**, inaccessible to both FLUX-X and FLUX-C via normal load/store. It is accessed only by the Monitor logic.

```c
struct scb_flux_x {
    uint64_t r[16];          // R0–R15
    uint64_t f[16];          // F0–F15 (if FLUX-X has float regs)
    uint32_t pc;             // Return PC (instruction after CONSTRAINT_CHECK)
    uint16_t flags;          // FLUX-X FLAGS snapshot
    uint16_t fpsr;           // Floating-point status
    uint8_t  constraint_id;  // ID of the in-flight constraint
    uint8_t  input_count;    // Number of inputs marshaled
    uint8_t  reserved[6];    // Padding to 256-byte alignment
};
// Total: 256 + 256 + 4 + 2 + 2 + 1 + 1 + 6 = 528 bytes
```

**Save/Restore Invariants:**
- On bridge entry: **all** registers are saved. FLUX-C must not be able to infer FLUX-X state.
- On normal return: all registers restored exactly, except R1/R2 overwritten with result.
- On fault: registers are **not** restored from SCB. Instead, sanitized values are injected (§4.2).

### 5.2 FLUX-C Context

FLUX-C context is simpler and is **not** preserved across bridge calls. Each `CONSTRAINT_CHECK` starts FLUX-C from a clean slate:

- Stack is zeroed.
- Call stack is reset.
- PC is loaded from CDT.
- Gas is loaded from CDT.
- `guard_reg` is set to `constraint_id` (for `LOAD_GUARD` opcode).
- `last_check_passed` is initialized to `true`.

This eliminates an entire class of re-entrancy bugs and covert channels.

### 5.3 Re-entrancy Lock

The Monitor maintains a 1-bit `BRIDGE_BUSY` flag. If FLUX-X issues `CONSTRAINT_CHECK` while `BRIDGE_BUSY` == 1, the Monitor immediately triggers Safe State with `FAULT_BRIDGE_NESTED_CALL` (0x1B). Constraints cannot be nested; they must complete before another is issued.

> **Exception:** If FLUX-X supports interrupts and an ISR attempts `CONSTRAINT_CHECK`, the same fault occurs. ISRs must not evaluate constraints directly; they should post a deferred constraint request to a queue.

---

## 6. Security Model — Preventing Bypass

### 6.1 Threat Model

The attacker controls arbitrary FLUX-X code (general compute layer). The attacker aims to:
1. **Bypass constraints:** Execute a safety-critical operation without FLUX-C approval.
2. **Tamper with constraints:** Modify FLUX-C bytecode or CDT to weaken safety checks.
3. **DoS the bridge:** Exhaust gas, overflow stack, or nest calls to deadlock the system.
4. **Leak data:** Use FLUX-C as a side-channel to read FLUX-X secrets.
5. **Escape sandbox:** Get FLUX-C to execute arbitrary code outside its sandbox.

### 6.2 Defenses

#### 6.2.1 Physical/Memory Firewall

FLUX-X and FLUX-C operate in **separate physical or strongly-MPU-partitioned address spaces**:

| Region | Owner | Access from FLUX-X | Access from FLUX-C |
|--------|-------|-------------------|-------------------|
| FLUX-X RAM (general) | FLUX-X | RW | **None** |
| FLUX-X ROM (code) | Bootloader | RX | **None** |
| FLUX-C Stack (256 B) | Monitor | **None** | RW |
| FLUX-C Bytecode | Bootloader | **None** | RX |
| CDT (Constraint Dispatch Table) | Bootloader | **None** | R |
| Monitor RAM (SCB, BCQ) | Monitor | **None** | **None** |
| Provenance Ring Buffer | Monitor | R (append-only view) | **None** |

The MPU is configured by the bootloader and **locked** (write-once). FLUX-X cannot remap FLUX-C memory, and FLUX-C cannot see FLUX-X memory. The Monitor is the only entity that can read both worlds, and it only does so through the narrow `CONSTRAINT_CHECK` protocol.

#### 6.2.2 One-Way Gate Enforcement

FLUX-C is **architecturally incapable** of calling back into FLUX-X:

- FLUX-C has no `SMC`, `SVC`, or `CALL_X` opcode.
- FLUX-C `CALL` and `JUMP` opcodes are sandboxed: the Monitor validates that the target address lies within `[CDT[constraint_id].entry_addr, CDT[constraint_id].end_addr]`. Any attempt to jump outside this range raises `FAULT_INVALID_MEMORY_ACCESS`.
- FLUX-C `HALT` does not return to a caller; it yields control to the Monitor.
- The Monitor ignores any FLUX-C state that claims to be a "return address" to FLUX-X.

#### 6.2.3 CDT Integrity

The Constraint Dispatch Table is an array of fixed-size records:

```c
struct cdt_entry {
    uint16_t entry_addr;   // Start of bytecode in FLUX-C code space
    uint16_t end_addr;     // One past last valid byte
    uint8_t  input_slots;  // Expected number of inputs (1-16)
    uint8_t  reserved;
    uint32_t max_gas;      // Gas budget for this constraint
    uint32_t crc32;        // Integrity check over bytecode region
};
```

- The CDT is located at a fixed address in **read-only memory**.
- At boot, the Monitor verifies the CRC32 of every CDT entry against its bytecode region. If any mismatch, the system refuses to exit reset.
- FLUX-X can only supply an 8-bit `constraint_id`. The Monitor bounds-checks it against `CDT_SIZE`. Out-of-bounds IDs raise `FAULT_INVALID_CONSTRAINT_ID`.
- The CDT cannot be modified at runtime. There is no "loadable constraint" mechanism in the DAL-A TCB.

#### 6.2.4 Gas Bounding & DoS Prevention

- Each CDT entry carries its own `max_gas`. The Monitor initializes FLUX-C gas from this value.
- FLUX-X **cannot** specify gas. If it could, it would pass `0xFFFFFFFF` and open a DoS window.
- Gas is decremented by the Monitor on every FLUX-C instruction fetch, before decode. Gas exhaustion is a fault → Safe State.
- The minimum gas for any constraint is `32`. Constraints with `max_gas < 32` are rejected at boot.

#### 6.2.5 Privilege Separation

- `CONSTRAINT_CHECK` is a **privileged opcode**. In unprivileged FLUX-X mode, it raises `FAULT_UNPRIVILEGED_CALL`.
- Only the FLUX-X supervisor (fleet scheduler, safety executive) runs in privileged mode.
- This prevents untrusted agent bytecode from flooding the bridge with constraint checks.

#### 6.2.6 Timing Side-Channel Mitigation

Constraint evaluation time can leak information about inputs (e.g., a branch based on a secret value takes longer). To mitigate:

- **Fixed-latency mode (optional):** The Monitor pads FLUX-C execution to the `max_gas` bound. FLUX-X always sees `CONSTRAINT_CHECK` take exactly `max_gas + monitor_overhead` cycles, regardless of actual path.
- **Power-of-2 bucketing:** Execution times are quantized to the next power of two. The Monitor spins or yields until the bucket expires.

These mitigations are configured per-CDT entry (`flags` field) and are mandatory for constraints that operate on secret material (e.g., cryptographic key validation).

#### 6.2.7 DMA & Interrupt Isolation

- DMA engines in FLUX-X are **paused** (or their transactions are MPU-filtered) during `CONSTRAINT_CHECK` execution. A DMA transfer cannot overwrite FLUX-C bytecode or CDT while FLUX-C is running.
- External interrupts to FLUX-X are **deferred** (not lost, but held pending) during the bridge call. They are delivered after the Monitor completes. This prevents an interrupt handler from corrupting FLUX-X state while the SCB is active.
- FLUX-C itself is **non-interruptible**. It runs to completion, fault, or gas exhaustion.

---

## 7. Comparison to ARM TrustZone SMC

| TrustZone Concept | FLUX Bridge Equivalent |
|-------------------|------------------------|
| `SMC #imm` | `CONSTRAINT_CHECK` (opcode `0xF0`) |
| X0–X7 arguments | R0 = constraint_id, R1–R15 = arguments |
| EL3 Secure Monitor | FLUX Monitor (bridge switch logic) |
| SCR.NS bit | `FLAGS.SAFE` bit (0 = normal, 1 = safe state) |
| Secure world | FLUX-C (constraint VM) |
| Normal world | FLUX-X (general compute VM) |
| SMC from secure → normal | **Not implemented** (architecturally impossible) |
| Secure context save | SCB (Secure Context Block) in Monitor RAM |
| IRQ masking during SMC | Interrupts deferred, then replayed |
| Secure interrupt | Bridge Completion Interrupt (async mode) |

---

## 8. Implementation Checklist

### FLUX-X Decoder
- [ ] Add `CONSTRAINT_CHECK` (0xF0) to opcode table.
- [ ] Enforce privileged-mode execution.
- [ ] Validate reserved bits are zero.

### FLUX Monitor (Hardware or Hypervisor)
- [ ] Implement SCB save/restore.
- [ ] Implement CDT bounds-check and CRC verification.
- [ ] Implement register-to-stack marshal/unmarshal.
- [ ] Implement gas injection and step counting.
- [ ] Implement FLUX-C PC sandboxing (jump target validation).
- [ ] Implement safe state transition (sanitize, force SSV).
- [ ] Implement `BRIDGE_BUSY` lock.
- [ ] Implement Provenance Ring Buffer logging.

### FLUX-C VM
- [ ] Ensure no `CALL_X` or `SMC_RETURN` opcodes exist.
- [ ] Ensure `HALT` yields to Monitor, not to a return address.
- [ ] Support pre-pushed inputs (bridge entry convention).
- [ ] Support `GUARD_TRAP` (0x20) for explicit hard failures.
- [ ] Support `LOAD_GUARD` (0x1E) reading `guard_reg = constraint_id`.

### Toolchain (guardc / flux-asm)
- [ ] `guardc`: Emit bridge-compatible bytecode (no input PUSH prologue).
- [ ] `flux-asm`: Support `--target bridge-entry` for FLUX-C constraints.
- [ ] Linker: Generate CDT from compiled constraint modules.

### Verification
- [ ] TLA+ model: Prove that FLUX-C can never set `FLAGS.SAFE = 0`.
- [ ] Coq proof: Prove that Monitor register sanitization prevents information flow from FLUX-C to FLUX-X on fault paths.
- [ ] Fuzz test: Random FLUX-C bytecode must never escape sandbox or corrupt SCB.

---

## 9. References

- `for-fleet/2026-05-04-FM-FLUX-ISA-ALIGNMENT.i2i.md` — Original two-layer ISA proposal.
- `flux-hardware/vm/flux_vm.rs` — Reference FLUX-C VM with `GUARD_TRAP` and gas model.
- `flux-hardware/rtl/flux_checker_top.sv` — DO-254 DAL-A hardware checker with TMR and fault latches.
- `guard-dsl/SPEC.md` — GUARD constraint language specification.
- ARM Architecture Reference Manual, §G6 (Secure Monitor Call).
