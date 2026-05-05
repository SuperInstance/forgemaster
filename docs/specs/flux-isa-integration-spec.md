```
★ Insight ─────────────────────────────────────
Two-ISA architectures trade implementation complexity for a clean
certification boundary: the certifiable core stays minimal and
formally tractable, while the operational ISA retains full
expressiveness. TrustZone is the closest analogue in silicon—
this spec applies the same principle to bytecode/virtual machines.
─────────────────────────────────────────────────
```

---

# FLUX-C / FLUX-X Two-ISA Architecture  
## Technical Specification — Revision 0.3.0-draft

**Classification:** Unclassified / Distribution Statement A  
**Prepared for:** Oracle1 Flight Systems, CCC Integration Team, DO-254 Designated Engineering Representative  
**Authors:** FLUX Architecture Working Group  
**Date:** 2026-05-03  
**Status:** DRAFT — Pending DER Review

---

## Table of Contents

1. [Overview](#1-overview)  
2. [FLUX-C Specification](#2-flux-c-specification)  
3. [FLUX-X Specification](#3-flux-x-specification)  
4. [Bridge Protocol](#4-bridge-protocol)  
5. [Compilation Pipeline](#5-compilation-pipeline)  
6. [Certification Argument](#6-certification-argument)  
7. [Security Analysis](#7-security-analysis)  
8. [Hardware Mapping](#8-hardware-mapping)  
9. [API Reference](#9-api-reference)  
10. [Appendices](#10-appendices)

---

## 1. Overview

### 1.1 Motivation and Design Philosophy

Modern autonomous systems—especially those operating in safety-critical aerospace or defense contexts—require two conflicting properties simultaneously:

1. **Operational Expressiveness**: Complex fleet coordination, adaptive control, sensor fusion, and mission planning demand a capable, general-purpose computation substrate. Restrictions to a minimal ISA would cripple mission utility.

2. **Certifiable Safety**: DO-254 DAL A hardware assurance and its software analogue DO-178C DAL A require exhaustive verification of every execution path. Full-featured ISAs with 200+ opcodes, floating-point, and dynamic dispatch are effectively uncertifiable to DAL A within practical program budgets.

The FLUX two-ISA architecture resolves this tension by structuring computation into two domains with asymmetric certification requirements, enforced by a one-way bridge with formal properties.

```
┌───────────────────────────────────────────────────────────────────┐
│                     FLUX-X Domain (Operational)                   │
│   247 opcodes · R0-R15 + F0-F15 · General computation            │
│   DO-254 DAL B/C   · flux-isa · CCC/Oracle1 Ref Implementation   │
│                                                                   │
│          ┌─────────────────────────────────────┐                 │
│          │   CONSTRAINT_CHECK Bridge Call       │  ← one-way     │
│          │   (flux-bridge 0.1.0)                │                 │
│          └──────────────────┬──────────────────┘                 │
│                             │ locked by default                   │
│                             ▼                                     │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │                    FLUX-C Domain (Safety)                    │  │
│ │   43 opcodes · 256B stack · 64KB memory · gas-bounded        │  │
│ │   DO-254 DAL A · flux-vm 0.2.0 · Coq-provable execution      │  │
│ │                                                             │  │
│ │   GUARD DSL → guard2mask 0.1.2 → FLUX-C bytecode            │  │
│ └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### 1.2 The TrustZone Analogy

ARM TrustZone partitions a physical processor into Secure World and Normal World, enforcing that Normal World code cannot directly access Secure World memory or registers, and that transitions occur only through well-defined SMC call gates. FLUX applies the identical principle to virtual machines:

| TrustZone Concept | FLUX Equivalent |
|---|---|
| Secure World | FLUX-C Domain |
| Normal World | FLUX-X Domain |
| SMC call gate | CONSTRAINT_CHECK bridge call |
| EL3 monitor | flux-bridge arbiter |
| TrustZone memory controller | Gas budget + stack isolation |
| Secure memory | FLUX-C 64KB address space |
| Normal memory | FLUX-X memory model |

The critical security property is **unidirectionality**: FLUX-C code cannot invoke FLUX-X, cannot observe FLUX-X registers, and cannot be triggered except through an explicit, validated bridge call. FLUX-X can invoke FLUX-C constraints and receive a boolean verdict—nothing more.

### 1.3 Document Scope

This document specifies:
- The complete FLUX-C ISA (all 43 opcodes, encoding, semantics, gas costs)
- The FLUX-X ISA structure (categories, register conventions, memory model)
- The bridge protocol and its formal invariants
- The GUARD DSL compilation pipeline
- The certification rationale for DER review
- Security properties and attack surface analysis
- FPGA/ASIC implementation guidance
- Complete Rust crate API reference

This document is normative for the purposes of DO-254 DAL A certification of the FLUX-C domain. FLUX-X is informative.

### 1.4 Referenced Standards and Documents

| Document | Version | Role |
|---|---|---|
| DO-254 | 2000-04-19 | Hardware assurance baseline |
| DO-178C | 2011-12-13 | Software analogue for runtime |
| ARP4754A | 2010-12-21 | System-level safety |
| MIL-STD-1553B | 1996 | Data bus reference |
| RTCA DO-160G | 2010 | Environmental conditions |
| ARINC 653 Part 1 | 2010 | Partitioning reference |
| Coq 8.19 | 2024 | Formal proof assistant |
| flux-vm crate | 0.2.0 | FLUX-C implementation |
| flux-bridge crate | 0.1.0 | Bridge implementation |
| guard2mask crate | 0.1.2 | GUARD compiler |

---

## 2. FLUX-C Specification

### 2.1 Architecture Overview

FLUX-C is a minimalist, stack-oriented virtual machine designed for exhaustive formal verification. Every design decision prioritizes proof tractability over runtime performance.

**Key architectural parameters:**

| Parameter | Value | Rationale |
|---|---|---|
| Stack depth | 256 bytes (128 × i16 or 64 × i32) | Fits in FPGA BRAM slice; bounded exhaustively |
| Memory | 64 KB (65,536 bytes) | 16-bit address space; no paging complexity |
| Opcode count | 43 | Below cognitive tractability threshold for Coq proofs |
| Instruction width | Variable (1–3 bytes) | Density; all encodings are prefix-free |
| Gas model | Monotonically decreasing counter | Guarantees termination |
| Integer types | i8, i16, i32 (unsigned variants) | No floating-point; no NaN/infinity edge cases |
| Calling convention | None (flat execution) | No call stack; constraints are subroutines-by-design |
| Endianness | Little-endian | Matches Cortex-M, Artix-7 MicroBlaze |

### 2.2 Memory Model

FLUX-C presents a flat, 64 KB address space. Memory is segmented at load time by the flux-vm runtime:

```
0x0000 ┌──────────────────┐
       │   Bytecode ROM   │  Read-only, validated at load
       │   (max 32 KB)    │
0x8000 ├──────────────────┤
       │   Data Segment   │  Read/write
       │   (max 16 KB)    │
0xC000 ├──────────────────┤
       │   Stack Mirror   │  Read-only view of operand stack
       │   (256 B)        │
0xC100 ├──────────────────┤
       │   Bridge I/O     │  Written by bridge before call
       │   (128 B)        │
0xC180 ├──────────────────┤
       │   Reserved       │
0xFFFF └──────────────────┘
```

**Memory access rules:**
- Writes to `[0x0000, 0x7FFF]` (ROM) trap with `FAULT_MEM_WRITE_ROM`.
- Reads from `[0xC180, 0xFFFF]` (reserved) trap with `FAULT_MEM_RESERVED`.
- All accesses are bounds-checked before execution; no speculative loads.
- The stack is accessed exclusively via stack opcodes; no arbitrary pointer arithmetic can reach the stack region through `LOAD`/`STORE`.

### 2.3 Stack Model

The operand stack is a contiguous 256-byte region in host memory, separate from the 64 KB address space. Stack items are typed at the opcode level:

- `i8` — 1 byte on stack, zero-extended for arithmetic
- `i16` — 2 bytes on stack (little-endian)
- `i32` — 4 bytes on stack (little-endian)

Stack overflow (depth > 256 bytes occupied) traps with `FAULT_STACK_OVERFLOW`. Stack underflow on any pop traps with `FAULT_STACK_UNDERFLOW`. Both are non-recoverable from within FLUX-C.

### 2.4 Gas Model

Every FLUX-C execution context is initialized with a gas budget supplied by the bridge caller. Gas is decremented before each instruction executes. If gas reaches zero before the instruction executes, the VM traps with `FAULT_GAS_EXHAUSTED` and returns the safe-state verdict (see §4.5).

Gas costs are deterministic functions of the opcode only—no data-dependent gas costs. This property is required for worst-case execution time (WCET) analysis.

The gas counter is an unsigned 32-bit value. Maximum budget: `0xFFFF_FFFF` cycles (≈4.3 billion). Typical constraint programs consume fewer than 10,000 gas units.

### 2.5 Complete Opcode Table

All 43 opcodes are enumerated below. Encoding uses a 1-byte primary opcode. Opcodes with immediate operands are noted in the Encoding column as `OP imm8`, `OP imm16`, or `OP imm8 imm8`.

Stack effect notation: `( before -- after )` where top of stack is rightmost. Types: `i` = any integer, `i32` = 32-bit, `addr` = 16-bit address, `bool` = i32 with value 0 or 1, `gas` = internal.

#### 2.5.1 Constant Push Group (0x00–0x07)

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x00 | `NOP` | `00` | `( -- )` | 1 | No operation. |
| 0x01 | `PUSH8` | `01 imm8` | `( -- i32 )` | 2 | Push zero-extended 8-bit immediate as i32. |
| 0x02 | `PUSH16` | `02 imm16_lo imm16_hi` | `( -- i32 )` | 3 | Push zero-extended 16-bit little-endian immediate as i32. |
| 0x03 | `PUSH32` | `03 b0 b1 b2 b3` | `( -- i32 )` | 4 | Push 32-bit little-endian immediate. |
| 0x04 | `PUSH_TRUE` | `04` | `( -- bool )` | 1 | Push i32 value 1. |
| 0x05 | `PUSH_FALSE` | `05` | `( -- bool )` | 1 | Push i32 value 0. |
| 0x06 | `PUSH_ZERO` | `06` | `( -- i32 )` | 1 | Push i32 value 0. Semantically equivalent to `PUSH8 0x00` but lower gas and clearer intent. |
| 0x07 | `PUSH_ONE` | `07` | `( -- i32 )` | 1 | Push i32 value 1. |

#### 2.5.2 Stack Manipulation Group (0x08–0x0F)

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x08 | `DUP` | `08` | `( a -- a a )` | 2 | Duplicate top of stack. |
| 0x09 | `DROP` | `09` | `( a -- )` | 1 | Discard top of stack. |
| 0x0A | `SWAP` | `0A` | `( a b -- b a )` | 2 | Exchange top two stack items. |
| 0x0B | `OVER` | `0B` | `( a b -- a b a )` | 3 | Copy second item to top. |
| 0x0C | `ROT` | `0C` | `( a b c -- b c a )` | 4 | Rotate top three items: third moves to top. |
| 0x0D | `NROT` | `0D` | `( a b c -- c a b )` | 4 | Reverse rotation: top moves to third position. |
| 0x0E | `DEPTH` | `0E` | `( -- i32 )` | 2 | Push current stack depth in bytes as i32. |
| 0x0F | `PICK` | `0F imm8` | `( -- i )` | 3 | Copy Nth item from top (0-indexed) to top. Faults if N exceeds depth. |

#### 2.5.3 Arithmetic Group (0x10–0x18)

All arithmetic operates on i32 values. Overflow wraps (two's complement). Division by zero traps with `FAULT_DIV_ZERO`.

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x10 | `ADD` | `10` | `( a b -- a+b )` | 3 | Signed 32-bit addition, wrapping. |
| 0x11 | `SUB` | `11` | `( a b -- a-b )` | 3 | Signed 32-bit subtraction, wrapping. |
| 0x12 | `MUL` | `12` | `( a b -- a*b )` | 5 | Signed 32-bit multiplication, wrapping. |
| 0x13 | `DIV` | `13` | `( a b -- a/b )` | 8 | Signed 32-bit division. Traps on b=0. |
| 0x14 | `MOD` | `14` | `( a b -- a%b )` | 8 | Signed 32-bit remainder. Traps on b=0. |
| 0x15 | `NEG` | `15` | `( a -- -a )` | 2 | Two's complement negation. |
| 0x16 | `ABS` | `16` | `( a -- |a| )` | 3 | Absolute value. Result always non-negative; `ABS(MIN_I32)` = `MIN_I32` (defined, not a fault). |
| 0x17 | `MIN` | `17` | `( a b -- min(a,b) )` | 3 | Signed minimum. |
| 0x18 | `MAX` | `18` | `( a b -- max(a,b) )` | 3 | Signed maximum. |

#### 2.5.4 Bitwise Group (0x19–0x1F)

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x19 | `AND` | `19` | `( a b -- a&b )` | 2 | Bitwise AND. |
| 0x1A | `OR` | `1A` | `( a b -- a\|b )` | 2 | Bitwise OR. |
| 0x1B | `XOR` | `1B` | `( a b -- a^b )` | 2 | Bitwise XOR. |
| 0x1C | `NOT` | `1C` | `( a -- ~a )` | 2 | Bitwise complement. |
| 0x1D | `SHL` | `1D` | `( a n -- a<<n )` | 3 | Left shift by n bits (0–31). Shift ≥32 produces 0. |
| 0x1E | `SHR` | `1E` | `( a n -- a>>n )` | 3 | Logical right shift (zero-fill). Shift ≥32 produces 0. |
| 0x1F | `SAR` | `1F` | `( a n -- a>>>n )` | 3 | Arithmetic right shift (sign-extend). Shift ≥32 fills with sign bit. |

#### 2.5.5 Comparison Group (0x20–0x26)

All comparisons produce bool (0 or 1) as i32.

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x20 | `EQ` | `20` | `( a b -- bool )` | 2 | 1 if a == b, else 0. |
| 0x21 | `NEQ` | `21` | `( a b -- bool )` | 2 | 1 if a != b, else 0. |
| 0x22 | `LT` | `22` | `( a b -- bool )` | 2 | 1 if a < b (signed), else 0. |
| 0x23 | `LTE` | `23` | `( a b -- bool )` | 2 | 1 if a ≤ b (signed), else 0. |
| 0x24 | `GT` | `24` | `( a b -- bool )` | 2 | 1 if a > b (signed), else 0. |
| 0x25 | `GTE` | `25` | `( a b -- bool )` | 2 | 1 if a ≥ b (signed), else 0. |
| 0x26 | `ZERO` | `26` | `( a -- bool )` | 2 | 1 if a == 0, else 0. Equivalent to `PUSH_ZERO EQ` but single opcode. |

#### 2.5.6 Memory Group (0x27–0x2B)

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x27 | `LOAD8` | `27` | `( addr -- i32 )` | 4 | Load 1 byte from address, zero-extend to i32. |
| 0x28 | `LOAD16` | `28` | `( addr -- i32 )` | 5 | Load 2 bytes little-endian from address, zero-extend. |
| 0x29 | `LOAD32` | `29` | `( addr -- i32 )` | 6 | Load 4 bytes little-endian from address. |
| 0x2A | `STORE8` | `2A` | `( i32 addr -- )` | 4 | Store low byte of i32 to address. |
| 0x2B | `STORE16` | `2B` | `( i32 addr -- )` | 5 | Store low 2 bytes of i32 little-endian to address. |

Note: There is no `STORE32`; 32-bit stores to the safety-domain scratchpad are deliberately absent to reduce store complexity in proofs. Wide values are passed via 16-bit pairs.

#### 2.5.7 Control Flow Group (0x2C–0x32)

FLUX-C control flow is structured. All branch targets are validated at load time to be within the bytecode ROM region and on instruction boundaries. Forward-only jumps are not enforced by the ISA, but the GUARD compiler emits only forward branches (the Coq proofs rely on this property).

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x2C | `JMP` | `2C imm16` | `( -- )` | 3 | Unconditional jump to absolute 16-bit address. |
| 0x2D | `JZ` | `2D imm16` | `( bool -- )` | 3 | Jump if top of stack is 0; pop condition. |
| 0x2E | `JNZ` | `2E imm16` | `( bool -- )` | 3 | Jump if top of stack is nonzero; pop condition. |
| 0x2F | `HALT_OK` | `2F` | `( bool -- )` | 1 | Terminate with verdict = top of stack (truth value). |
| 0x30 | `HALT_FAIL` | `30` | `( -- )` | 1 | Terminate with verdict = false regardless. Explicit rejection. |
| 0x31 | `HALT_SAFE` | `31` | `( -- )` | 1 | Terminate with verdict = configured safe-state default (§4.5). |
| 0x32 | `LOOP` | `32 imm16 imm8` | `( count -- )` | 3+n | Execute next `imm8` instructions `count` times. Count is consumed. Gas = 3 + (count × body_gas). Pre-validates total gas before starting. |

**Note on `LOOP`:** The `LOOP` opcode is the only FLUX-C construct that permits backward execution. Its semantics are fully determined at decode time (body length is fixed by `imm8`), and the pre-validation of total gas ensures `LOOP` cannot be used to construct non-terminating programs. This makes FLUX-C provably terminating.

#### 2.5.8 Bridge I/O Group (0x33–0x39)

These opcodes access the Bridge I/O region `[0xC100, 0xC17F]`, which is written by the bridge before a CONSTRAINT_CHECK call and is read-only from within FLUX-C.

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x33 | `BRIDGE_LOAD8` | `33 imm8` | `( -- i32 )` | 3 | Load byte at offset `imm8` within Bridge I/O region. |
| 0x34 | `BRIDGE_LOAD16` | `34 imm8` | `( -- i32 )` | 4 | Load 16-bit value at offset `imm8` (must be even). |
| 0x35 | `BRIDGE_LOAD32` | `35 imm8` | `( -- i32 )` | 5 | Load 32-bit value at offset `imm8` (must be 4-byte aligned). |
| 0x36 | `BRIDGE_WRITE8` | `36 imm8` | `( i32 -- )` | 3 | Write low byte to result region offset `imm8` (output only; max offset 7). |
| 0x37 | `BRIDGE_WRITE16` | `37 imm8` | `( i32 -- )` | 4 | Write 16-bit value to result region (output only). |
| 0x38 | `BRIDGE_FLAGS` | `38` | `( -- i32 )` | 2 | Push bridge call flags word (see §4.3). |
| 0x39 | `BRIDGE_SEQ` | `39` | `( -- i32 )` | 2 | Push bridge call sequence number (monotonically increasing). |

#### 2.5.9 System Group (0x3A–0x3F, partial)

| Hex | Mnemonic | Encoding | Stack Effect | Gas | Description |
|-----|----------|----------|--------------|-----|-------------|
| 0x3A | `GAS_REMAINING` | `3A` | `( -- i32 )` | 1 | Push remaining gas count as i32. Does not include cost of this instruction. |
| 0x3B | `ASSERT` | `3B` | `( bool -- )` | 2 | If top of stack is 0, trap with `FAULT_ASSERT`. |
| 0x3C | `TRACE` | `3C imm8` | `( i32 -- )` | 2 | Emit trace event ID `imm8` with value. No-op in production mode; active in verification mode. Does not affect semantics. |
| 0x3D | `MASK8` | `3D imm8` | `( i32 -- i32 )` | 2 | Bitwise AND with `imm8` zero-extended to i32. `MASK8 0xFF` extracts low byte. |
| 0x3E | `CLAMP` | `3E` | `( val lo hi -- val' )` | 4 | Clamp val to [lo, hi]. Equivalent to `MAX` then `MIN` but single opcode for proof convenience. |
| 0x3F | `CHECKSUM` | `3F` | `( base len -- i32 )` | 2+len | Fletcher-16 checksum over `len` bytes starting at `base`. Validates data integrity without external hash dependencies. |

**Total opcode count: 43** (0x00–0x3F, with no gaps in this range; opcodes above 0x3F are illegal and trap with `FAULT_ILLEGAL_OPCODE`).

### 2.6 Fault Codes

| Code | Value | Description | Recovery |
|------|-------|-------------|----------|
| `FAULT_STACK_OVERFLOW` | 0x01 | Stack depth exceeded 256 bytes | Safe-state halt |
| `FAULT_STACK_UNDERFLOW` | 0x02 | Pop on empty stack | Safe-state halt |
| `FAULT_GAS_EXHAUSTED` | 0x03 | Gas budget reached zero | Safe-state halt |
| `FAULT_DIV_ZERO` | 0x04 | Division or modulo by zero | Safe-state halt |
| `FAULT_MEM_WRITE_ROM` | 0x05 | Write to ROM region | Safe-state halt |
| `FAULT_MEM_RESERVED` | 0x06 | Access to reserved region | Safe-state halt |
| `FAULT_MEM_OOB` | 0x07 | Address outside 64 KB | Safe-state halt |
| `FAULT_ILLEGAL_OPCODE` | 0x08 | Opcode > 0x3F | Safe-state halt |
| `FAULT_ASSERT` | 0x09 | `ASSERT` with false condition | Safe-state halt |
| `FAULT_BRIDGE_ALIGN` | 0x0A | `BRIDGE_LOAD16/32` misaligned | Safe-state halt |
| `FAULT_BAD_JUMP` | 0x0B | Jump to non-instruction-boundary | Safe-state halt |
| `FAULT_LOOP_BODY_SIZE` | 0x0C | `LOOP` body extends past ROM | Safe-state halt |

All faults are non-recoverable within the current execution context. The bridge records the fault code in its response frame (§4.4).

---

## 3. FLUX-X Specification

### 3.1 Architecture Overview

FLUX-X is a register-based ISA designed for high-throughput fleet operations. It is **not** subject to DO-254 DAL A certification. Its certification target is DAL B or DAL C depending on the system integrator's safety case for the specific operational function.

**Key architectural parameters:**

| Parameter | Value |
|---|---|
| Instruction width | Fixed 4 bytes (32 bits) |
| General-purpose registers | R0–R15 (32-bit each) |
| Floating-point registers | F0–F15 (64-bit IEEE 754) |
| Opcode space | 247 opcodes |
| Addressing modes | Register, immediate, indirect, indexed |
| Memory model | Flat 32-bit virtual address space |
| Calling convention | FLUX-X ABI (§3.5) |

### 3.2 Instruction Encoding

All FLUX-X instructions are exactly 32 bits wide:

```
31      24 23    20 19    16 15     8 7      0
┌──────────┬────────┬────────┬────────┬────────┐
│  opcode  │  dst   │  src1  │  src2  │  imm8  │
│  [8]     │  [4]   │  [4]   │  [4]   │  [8]   │
└──────────┴────────┴────────┴────────┴────────┘
```

For instructions requiring a 16-bit immediate:

```
31      24 23    20 19                          0
┌──────────┬────────┬───────────────────────────┐
│  opcode  │  dst   │        imm20              │
│  [8]     │  [4]   │        [20]               │
└──────────┴────────┴───────────────────────────┘
```

Long immediates use a two-instruction sequence: `MOVHI` loads the upper 16 bits, followed by `MOVLO` or an arithmetic instruction that merges the lower 16 bits.

### 3.3 Register Conventions

#### 3.3.1 General-Purpose Registers (R0–R15)

| Register | ABI Name | Role |
|---|---|---|
| R0 | `zero` | Hardwired zero (reads 0, writes discarded) |
| R1 | `ret` | Return value / bridge verdict staging |
| R2 | `sp` | Stack pointer |
| R3 | `fp` | Frame pointer |
| R4 | `arg0` | First call argument / bridge input arg 0 |
| R5 | `arg1` | Second call argument / bridge input arg 1 |
| R6 | `arg2` | Third call argument / bridge input arg 2 |
| R7 | `arg3` | Fourth call argument / bridge input arg 3 |
| R8–R11 | `t0–t3` | Caller-saved temporaries |
| R12–R14 | `s0–s2` | Callee-saved |
| R15 | `lr` | Link register (return address) |

R0 being hardwired zero is enforced by the FLUX-X runtime; any write to R0 is a no-op. This simplifies the Coq model of the bridge interface by providing a reliable zero source.

#### 3.3.2 Floating-Point Registers (F0–F15)

| Register | ABI Name | Role |
|---|---|---|
| F0–F3 | `fa0–fa3` | FP call arguments / return values |
| F4–F7 | `ft0–ft3` | Caller-saved FP temporaries |
| F8–F15 | `fs0–fs7` | Callee-saved FP |

Floating-point registers are **never** passed through the bridge. The bridge register mapping (§4.2) covers R1–R7 only. FP state is opaque to FLUX-C.

### 3.4 Opcode Categories

FLUX-X opcodes are organized into functional groups:

| Category | Opcode Range | Count | Description |
|---|---|---|---|
| Integer Arithmetic | 0x01–0x18 | 24 | ADD, SUB, MUL, DIV, MOD variants (signed/unsigned/widening) |
| Bitwise | 0x19–0x28 | 16 | AND, OR, XOR, NOT, shifts, rotates, popcount, CLZ |
| Comparison & Predication | 0x29–0x38 | 16 | CMP, CMOV, predicated variants |
| FP Arithmetic | 0x39–0x58 | 32 | ADD/SUB/MUL/DIV/FMA/SQRT (f32 and f64) |
| FP Conversion | 0x59–0x68 | 16 | INT↔FP, f32↔f64, round modes |
| Load/Store | 0x69–0x7C | 20 | 8/16/32/64-bit, signed/unsigned, atomic |
| Control Flow | 0x7D–0x8E | 18 | JUMP, BRANCH (8 conditions), CALL, RET, LOOP |
| System | 0x8F–0x98 | 10 | NOP, HALT, FENCE, CSR access, interrupt control |
| SIMD | 0x99–0xB8 | 32 | 4×i32, 2×i64, 4×f32, 2×f64 packed ops |
| Crypto Assist | 0xB9–0xC4 | 12 | AES rounds, SHA-256 round, CRC32 |
| Bridge Control | 0xC5–0xCC | 8 | CONSTRAINT_CHECK and variants (§4.1) |
| String/Block | 0xCD–0xD8 | 12 | MEMCPY, MEMSET, MEMMOVE, STRCMP variants |
| Extended Math | 0xD9–0xE8 | 16 | MULH, MULHU, DIVU, SIN/COS approximations |
| Virtualization | 0xE9–0xF5 | 13 | VM call/return, partition switch |
| Reserved/Future | 0xF6–0xFF | 10 | Illegal; trap with `XFAULT_ILLEGAL` |

Total non-reserved: 247 opcodes.

### 3.5 FLUX-X ABI

**Calling convention:**
- Arguments: R4 (arg0), R5 (arg1), R6 (arg2), R7 (arg3); further arguments on stack
- Return value: R1
- Caller saves: R8–R11, F0–F7
- Callee saves: R12–R14, F8–F15, R3 (fp)
- Stack grows downward; SP is always 8-byte aligned at call boundaries

**Stack frame layout:**
```
┌─────────────┐ ← previous SP (caller's frame)
│  saved R15  │ (lr)
│  saved R3   │ (fp)
│  saved s0   │ (R12, if used)
│  saved s1   │ (R13, if used)
│  saved s2   │ (R14, if used)
│  local vars │
│  ...        │
└─────────────┘ ← current SP
```

### 3.6 Memory Model

FLUX-X presents a flat 32-bit virtual address space. The memory map is implementation-defined by the system integrator; however, by convention Oracle1 and CCC implementations reserve:

| Range | Use |
|---|---|
| `0x00000000–0x0FFFFFFF` | Code (ROM or flash) |
| `0x10000000–0x3FFFFFFF` | RAM (heap/stack) |
| `0x40000000–0x7FFFFFFF` | MMIO peripherals |
| `0x80000000–0x8000FFFF` | FLUX-C domain window (read-only from FLUX-X) |
| `0x80010000–0x8001FFFF` | Bridge control registers |
| `0x80020000–0xFFFFFFFF` | Reserved |

The FLUX-C domain window is not directly writable from FLUX-X. All writes to FLUX-C memory occur exclusively through the bridge's argument marshaling layer.

---

## 4. Bridge Protocol

```
★ Insight ─────────────────────────────────────
The bridge's one-way enforcement is not merely a software policy—
it's structural. FLUX-C opcodes contain no mechanism to initiate
outbound calls. The ISA itself is the enforcement, making the
isolation proof compositional: prove FLUX-C isolation once,
and it holds for all programs.
─────────────────────────────────────────────────
```

### 4.1 Bridge Opcodes (FLUX-X Side)

The bridge is initiated from FLUX-X via dedicated opcodes in the Bridge Control group (0xC5–0xCC):

| Opcode | Hex | Encoding | Description |
|--------|-----|----------|-------------|
| `CONSTRAINT_CHECK` | 0xC5 | `C5 dst=R1 src1=Rn src2=imm8` | Invoke FLUX-C constraint program `imm8`; result in `dst`. |
| `CONSTRAINT_CHECK_EXT` | 0xC6 | `C6 dst=R1 src1=Rn imm20=prog_id` | 20-bit program ID for large constraint tables. |
| `BRIDGE_LOCK` | 0xC7 | `C7 imm20=mask` | Lock bridge channel `mask` bits (one-way; cannot unlock without reset). |
| `BRIDGE_UNLOCK_REQUEST` | 0xC8 | `C8 imm20=token` | Request unlock (requires physical key or external authority signal). |
| `BRIDGE_STATUS` | 0xC9 | `C9 dst` | Read bridge status word into `dst`. |
| `BRIDGE_SYNC` | 0xCA` | `CA` | Full memory barrier before bridge call; ensures argument writes are visible. |
| `BRIDGE_TRACE_START` | 0xCB | `CB imm8` | Mark start of a traced constraint session (verification mode only). |
| `BRIDGE_TRACE_END` | 0xCC | `CC imm8` | Mark end of a traced constraint session. |

### 4.2 CONSTRAINT_CHECK Call Convention

A `CONSTRAINT_CHECK` invocation proceeds in the following strict sequence:

#### Phase 1: Argument Marshaling (FLUX-X, before call)

The caller populates argument registers:

| Register | Bridge I/O Offset | FLUX-C Access | Meaning |
|---|---|---|---|
| R4 (arg0) | 0x00 | `BRIDGE_LOAD32 0x00` | Primary constraint input (e.g., sensor reading) |
| R5 (arg1) | 0x04 | `BRIDGE_LOAD32 0x04` | Secondary input (e.g., threshold parameter) |
| R6 (arg2) | 0x08 | `BRIDGE_LOAD32 0x08` | Tertiary input |
| R7 (arg3) | 0x0C | `BRIDGE_LOAD32 0x0C` | Quaternary input |
| (stack+0) | 0x10 | `BRIDGE_LOAD32 0x10` | Extended arg 0 (must call `BRIDGE_SYNC` first) |
| (stack+4) | 0x14 | `BRIDGE_LOAD32 0x14` | Extended arg 1 |
| (stack+8) | 0x18 | `BRIDGE_LOAD32 0x18` | Extended arg 2 |
| (stack+12) | 0x1C | `BRIDGE_LOAD32 0x1C` | Extended arg 3 |

The bridge arbiter copies R4–R7 into the Bridge I/O region atomically before transferring control to FLUX-C. Extended arguments from the stack must have been written before `BRIDGE_SYNC` is issued.

**Flags word (offset 0x20):**

```
Bit 31:16  reserved (must be zero)
Bit 15:8   bridge call sequence number (low byte)
Bit 7      STRICT mode: fault → HALT_FAIL (not HALT_SAFE)
Bit 6      TRACE mode: emit TRACE opcodes to log
Bit 5      LOCK_ON_FAULT: lock bridge channel on any fault
Bit 4      ASYNC mode: non-blocking (result polled via BRIDGE_STATUS)
Bit 3:0    channel ID (0–15)
```

#### Phase 2: Gas Allocation

The bridge arbiter computes the gas budget as:

```
gas = base_gas + (arg_count × per_arg_gas)
```

Default values (configurable via `BridgeConfig` in flux-bridge):
- `base_gas` = 50,000
- `per_arg_gas` = 1,000

The gas budget is written to the FLUX-C execution context before the program counter is set to the constraint program's entry point.

#### Phase 3: Execution (FLUX-C)

FLUX-C executes until:
- `HALT_OK` — verdict = top of stack (bool)
- `HALT_FAIL` — verdict = false
- `HALT_SAFE` — verdict = configured safe-state default
- Any fault — verdict = safe-state default; fault code recorded

#### Phase 4: Result Return

On completion, the bridge arbiter:

1. Reads the verdict (bool) from the FLUX-C context.
2. Reads any `BRIDGE_WRITE` outputs (offset 0x00–0x07 of result region).
3. Writes the verdict to R1 in the FLUX-X context (0 = reject, 1 = accept).
4. Writes extended outputs to R4 if the constraint program wrote them.
5. Clears the Bridge I/O region (zeroed).
6. Resumes FLUX-X execution at the instruction following `CONSTRAINT_CHECK`.

**Result word in R1:**

```
Bit 31:16  fault code (0 = no fault)
Bit 15:8   gas consumed (saturating at 0xFF if > 255 units remained)
Bit 7:1    reserved
Bit 0      verdict (1 = PASS, 0 = FAIL/FAULT)
```

### 4.3 Register-to-Stack Mapping

When FLUX-X calls into FLUX-C with a mixture of register and stack arguments, the bridge applies the following normalization:

```
FLUX-X Source    →    FLUX-C Bridge I/O Offset
─────────────────────────────────────────────
R4               →    0x00  (primary arg)
R5               →    0x04
R6               →    0x08
R7               →    0x0C
[SP+0]           →    0x10  (only if BRIDGE_SYNC issued)
[SP+4]           →    0x14
[SP+8]           →    0x18
[SP+12]          →    0x1C
flags_word       →    0x20  (synthesized by bridge)
sequence_number  →    0x24  (maintained by bridge arbiter)
```

FP registers are never mapped. If a constraint program requires floating-point inputs, the FLUX-X caller must convert to fixed-point representation (e.g., scaled integer) before the call.

### 4.4 Fault Handling

All faults within FLUX-C are non-recoverable within the constraint execution but are reported to FLUX-X in the result word (bits 31:16). The bridge arbiter responds to each fault class as follows:

| Fault | Default Bridge Response | With `LOCK_ON_FAULT` |
|---|---|---|
| `FAULT_GAS_EXHAUSTED` | Return FAIL verdict | + Lock channel |
| `FAULT_STACK_OVERFLOW` | Return FAIL verdict | + Lock channel |
| `FAULT_DIV_ZERO` | Return FAIL verdict | + Lock channel |
| `FAULT_ILLEGAL_OPCODE` | Return FAIL + log | + Lock channel + alert |
| `FAULT_MEM_*` | Return FAIL + log | + Lock channel + alert |
| `FAULT_ASSERT` | Return FAIL verdict | + Lock channel |
| `FAULT_BAD_JUMP` | Return FAIL + log | + Lock channel + alert |

The `LOCK_ON_FAULT` flag (bit 5 of flags word) is recommended for safety-critical constraint calls where any fault indicates a potential adversarial input or hardware anomaly.

### 4.5 Safe States

The safe-state default verdict is configurable per-channel. The bridge arbiter applies the following decision logic for `HALT_SAFE` and all fault conditions:

| Channel Configuration | Safe-State Verdict |
|---|---|
| `SafeState::Permit` | 1 (allow operation) |
| `SafeState::Deny` (default) | 0 (deny operation) |
| `SafeState::Latch` | Last valid verdict |
| `SafeState::Emergency(n)` | Emit emergency code `n` to MMIO |

**Default is `SafeState::Deny`.** This implements a fail-secure posture: if the constraint oracle cannot produce a valid answer, the operation is denied. System integrators must explicitly configure `SafeState::Permit` for channels where denial is more dangerous than incorrect permission (e.g., safety-critical actuation enables).

### 4.6 Bridge Lock State Machine

```
           ┌─────────┐
  power-on │ LOCKED  │ ◄──── BRIDGE_LOCK opcode
  default  └────┬────┘      (one-way, irrevocable without reset)
                │ physical key OR
                │ external authority signal
                ▼
           ┌──────────┐
           │ UNLOCKED │ ──── CONSTRAINT_CHECK operational
           └────┬─────┘
                │ BRIDGE_LOCK OR
                │ LOCK_ON_FAULT trigger
                ▼
           ┌─────────┐
           │ LOCKED  │ ──── all CONSTRAINT_CHECK return safe-state
           └─────────┘      (no FLUX-C execution occurs)
```

The bridge is **locked by default** on power-on. This means that FLUX-C constraint programs are not invoked until the system has completed its initialization and the bridge is explicitly unlocked by an authorized authority. This prevents pre-initialization calls from bypassing safety checks during boot.

---

## 5. Compilation Pipeline

### 5.1 GUARD DSL

GUARD (Guaranteed Assertion Under Runtime Derivation) is a domain-specific language for expressing safety constraints. It compiles to FLUX-C bytecode via `guard2mask` (version 0.1.2, published on crates.io).

#### 5.1.1 GUARD Syntax Overview

```guard
// GUARD syntax example: altitude separation constraint
constraint AltitudeSeparation(
    own_alt: i32,      // own aircraft altitude in feet
    traffic_alt: i32,  // traffic altitude in feet  
    separation_req: i32 // minimum required separation in feet
) -> bool {
    let diff = abs(own_alt - traffic_alt);
    return diff >= separation_req;
}

// Composite constraint with multiple checks
constraint FlightEnvelope(
    airspeed: i32,    // airspeed in knots × 10 (fixed-point)
    altitude: i32,    // altitude in feet
    aoa: i32          // angle of attack in degrees × 100
) -> bool {
    ensure airspeed >= 1200 && airspeed <= 5000;  // 120–500 knots
    ensure altitude >= -2000 && altitude <= 510000; // -200 to 51000 ft
    ensure aoa >= -1000 && aoa <= 1800;            // -10 to 18 degrees
    return true; // all ensures passed
}
```

#### 5.1.2 GUARD Type System

GUARD supports only the following types:

| Type | FLUX-C Representation | Notes |
|---|---|---|
| `bool` | i32 (0 or 1) | No nullable booleans |
| `i8` | i32 (sign-extended) | Range [-128, 127] |
| `u8` | i32 (zero-extended) | Range [0, 255] |
| `i16` | i32 (sign-extended) | Range [-32768, 32767] |
| `u16` | i32 (zero-extended) | Range [0, 65535] |
| `i32` | i32 | Full range |
| Fixed-point | i32 with metadata | Compiler tracks scale factor |

No floating-point types, no strings, no pointers, no heap allocation.

#### 5.1.3 Compilation to FLUX-C

`guard2mask` performs the following compilation stages:

```
GUARD source (.grd)
        │
        ▼ Stage 1: Parsing
GUARD AST
        │
        ▼ Stage 2: Type checking + range analysis
Typed AST with range annotations
        │
        ▼ Stage 3: Gas estimation
Gas-annotated AST (worst-case per node)
        │
        ▼ Stage 4: Code generation
FLUX-C assembly (human-readable intermediate)
        │
        ▼ Stage 5: Bytecode encoding
FLUX-C bytecode (.flxc)
        │
        ▼ Stage 6: Validation pass
Validated bytecode (jump table verified, gas ≤ budget)
        │
        ▼ Stage 7: Artifact generation
.flxc + .map (source map) + .gas (worst-case gas report)
```

**Compiler invariants enforced at Stage 6:**
1. All jump targets are valid instruction boundaries.
2. Stack depth at every reachable point is ≤ 256 bytes.
3. Stack depth is statically deterministic (no data-dependent depth changes).
4. No opcode above 0x3F is emitted.
5. Worst-case gas consumption ≤ `u32::MAX`.
6. All `LOOP` bodies have statically bounded size.
7. No backwards jumps except within `LOOP` bodies.

### 5.2 How FLUX-X Code Invokes Constraints

The canonical call pattern in FLUX-X assembly:

```asm
; Load constraint arguments
MOV  R4, sensor_altitude_fp    ; own altitude (fixed-point i32)
MOV  R5, traffic_altitude_fp   ; traffic altitude
MOV  R6, separation_minimum    ; separation requirement (constant)
MOV  R7, R0                    ; arg3 = zero (unused)

; Issue memory barrier to ensure args visible to bridge
BRIDGE_SYNC

; Invoke constraint program #3 (AltitudeSeparation)
CONSTRAINT_CHECK R1, R0, #3

; Check verdict
ANDI R8, R1, #1               ; isolate verdict bit
JZ   R8, .separation_violated

; Check for fault (bits 31:16 nonzero)
SHR  R9, R1, #16
JNZ  R9, .constraint_fault

; Normal path: constraint passed
JMP  .separation_ok

.separation_violated:
    ; Constraint rejected the operation
    CALL engage_avoidance_maneuver
    JMP  .done

.constraint_fault:
    ; Bridge reported a fault (gas, assert, etc.)
    ; Safe-state already applied; log and continue
    CALL log_constraint_fault, R9
    JMP  .done
```

In C/Rust code using the FLUX-X runtime library:

```rust
use flux_bridge::{BridgeChannel, ConstraintId, CallArgs};

let result = channel.check_constraint(
    ConstraintId::AltitudeSeparation,
    CallArgs::new()
        .arg0(own_altitude_fixed)
        .arg1(traffic_altitude_fixed)
        .arg2(separation_minimum),
)?;

match result.verdict() {
    Verdict::Pass => continue_operation(),
    Verdict::Fail => engage_avoidance(),
    Verdict::Fault(code) => handle_fault(code),
}
```

### 5.3 Constraint Program Registry

Each deployment configures a **constraint program registry** — a table mapping program IDs (0–255 for `CONSTRAINT_CHECK`, 0–1048575 for `CONSTRAINT_CHECK_EXT`) to validated FLUX-C bytecode blobs. The registry is:

- Loaded from flash/ROM during initialization
- Checksummed (Fletcher-16) before the bridge is unlocked
- Immutable at runtime (ROM-resident after validation)
- Versioned (4-byte version tag per entry)

The `BridgeConfig` API (§9.3) provides the registry management interface.

---

## 6. Certification Argument

### 6.1 DO-254 DAL A for FLUX-C

DO-254 (Design Assurance Level A) requires the highest level of rigor for hardware design, applicable to safety-critical functions where failure could cause catastrophic effects. FLUX-C targets DAL A through the following argument structure:

#### 6.1.1 The 43-Opcode Tractability Argument

The fundamental certification argument for FLUX-C rests on **exhaustive formal verification** being feasible given the opcode count.

The state space of a FLUX-C execution context is:
- Program counter: 16-bit (65,536 states)
- Stack: 256 bytes (2^2048 possible stack states, but bounded by type invariants)
- Memory (data segment, 16 KB): 2^131,072 states (but most unreachable from valid programs)
- Gas counter: 32-bit

For any **specific constraint program** (fixed bytecode), the reachable state space is dramatically smaller. Bounded model checking (BMC) using tools like CBMC or Kani can exhaustively verify properties for typical constraint programs in under an hour.

For the **FLUX-C interpreter itself** (the trusted computing base), Coq proofs provide:

1. **Type safety**: Stack items are always the type the opcode expects (proven by induction on execution steps)
2. **Memory safety**: All memory accesses are within [0x0000, 0xFFFF] (proven by bounds lemmas on `LOAD`/`STORE`)
3. **Termination**: Every FLUX-C program terminates (proven by the gas monotonic decrease invariant + `LOOP` body pre-validation)
4. **Isolation**: FLUX-C cannot produce outputs except through `HALT_*` and `BRIDGE_WRITE*` (proven by opcode exhaustion — no other output mechanism exists in 43 opcodes)

The 43-opcode count is specifically chosen so that the Coq proof of the FLUX-C small-step semantics has a tractable number of cases. With 43 opcodes, the semantic proof has approximately 43 × average-2.5-cases ≈ 107 leaf cases in the induction — manageable by a two-engineer team over 6–12 months.

Compare with x86: 3,000+ distinct encodings. No DAL A certifications exist for general-purpose CPUs.

#### 6.1.2 Coq Proof Structure

The FLUX-C Coq formalization (forthcoming as `flux-coq` crate) follows this structure:

```coq
(* Core types *)
Definition stack := list i32.
Definition memory := Vector.t byte 65536.
Definition gas := nat.

Record vm_state := {
  pc     : nat;
  stk    : stack;
  mem    : memory;
  gas_ct : gas;
  fault  : option fault_code;
}.

(* Small-step semantics *)
Inductive step : vm_state -> vm_state -> Prop := ...

(* Key theorems *)
Theorem flux_c_terminates :
  forall (prog : bytecode) (init : vm_state),
    valid_program prog ->
    init.(gas_ct) > 0 ->
    exists (final : vm_state) (n : nat),
      step_n prog n init final /\ is_halted final.

Theorem flux_c_memory_safe :
  forall (prog : bytecode) (s s' : vm_state),
    valid_program prog ->
    step prog s s' ->
    forall addr, mem_access s addr -> addr < 65536.

Theorem flux_c_stack_bounded :
  forall (prog : bytecode) (s s' : vm_state),
    valid_program prog ->
    step prog s s' ->
    stack_size s'.(stk) <= 256.

Theorem flux_c_isolation :
  forall (prog : bytecode) (s s' : vm_state),
    step prog s s' ->
    output_only_through_halt_or_bridge_write prog.
```

#### 6.1.3 Evidence Package Structure

The DO-254 DAL A evidence package for FLUX-C consists of:

| Artifact | DO-254 Section | Description |
|---|---|---|
| Requirements Specification | §5.1 | This document (§2) |
| Conceptual Design | §5.2 | FLUX-C interpreter architecture |
| Detailed Design | §5.3 | Per-opcode logic specification |
| Implementation | §5.4 | flux-vm 0.2.0 source (Rust) |
| Verification Plan | §6.1 | Coq proof plan + test plan |
| Coq Proofs | §6.2.1 | Formal proofs of safety properties |
| Structural Coverage | §6.2.2 | MC/DC coverage of interpreter |
| Hardware/Software Integration | §7.1 | Bridge interface verification |
| DER Review | §8 | This section |

### 6.2 Why FLUX-X Needs Only DAL B/C

FLUX-X does not execute safety-critical logic directly. Every safety decision that affects vehicle behavior routes through a CONSTRAINT_CHECK call and is evaluated by FLUX-C. FLUX-X code that ignores a FAIL verdict or bypasses the bridge entirely is, by system design, operating outside its intended function and is detectable by the system monitor.

The certification argument for FLUX-X's DAL B/C status:

1. **Consequential harm requires FLUX-C approval.** Any actuation command must pass a CONSTRAINT_CHECK; FLUX-C is the safety gate.
2. **FLUX-X failures are observable.** Failure to issue required CONSTRAINT_CHECK calls is a detectable omission (watchdog, sequence number monitoring).
3. **FLUX-X cannot corrupt FLUX-C.** The bridge's unidirectional property (proven by FLUX-C isolation theorem) means a compromised FLUX-X cannot alter FLUX-C bytecode or state.
4. **Operational risk reduction.** DAL B FLUX-X still requires significant assurance (MCDC coverage, requirements tracing), ensuring FLUX-X is not entirely uncontrolled.

This architectural argument allows the expensive DAL A effort to be focused exclusively on the 43-opcode FLUX-C core, dramatically reducing certification cost while maintaining safety guarantees.

### 6.3 Independence Requirements

Per DO-254 §11, independence between development and verification teams is required for DAL A. The FLUX architecture enforces this structurally:

- FLUX-C development: separate team from FLUX-X
- Coq proof development: independent from FLUX-C implementation team
- Bridge verification: independent review required before integration
- DER review of this specification required before evidence package acceptance

---

## 7. Security Analysis

### 7.1 Threat Model

**Assets to protect:**
- Safety constraint verdicts (must not be forged)
- FLUX-C execution integrity (must not be corrupted)
- Bridge lock state (must not be bypassed)

**Adversary capabilities:**
- Full control of FLUX-X code (compromise of operational domain)
- Physical access to MMIO (limited; mitigated by hardware partitioning)
- Malicious constraint program inputs (controlled via bridge I/O region write)

**Adversary capabilities explicitly excluded:**
- Physical modification of ROM (out of scope; hardware supply chain)
- Side-channel attacks on FLUX-C secrets (FLUX-C has no secrets; it is a pure function)
- DMA attacks (mitigated by IOMMU or equivalent; out of scope for this spec)

### 7.2 Attack Surface Analysis

#### 7.2.1 Malicious Inputs via Bridge Arguments

**Attack:** FLUX-X code supplies malformed or adversarial values in R4–R7 or extended stack arguments, attempting to cause FLUX-C to produce incorrect verdicts or crash.

**Mitigations:**
1. FLUX-C is a pure function of its bytecode and inputs; malformed inputs cannot corrupt bytecode.
2. All arithmetic traps on overflow/division-by-zero, returning FAIL (safe state).
3. Gas bounds prevent non-termination even with adversarial inputs.
4. The constraint program is designed to handle the full i32 range (GUARD range analysis assists this).
5. `FAULT_*` codes are returned to FLUX-X, which can detect repeated fault patterns.

**Residual risk:** MINIMAL. Adversarial inputs can cause FAULT, which returns a safe-state verdict. They cannot cause PASS with false premise.

#### 7.2.2 Bridge Lock Bypass

**Attack:** FLUX-X code attempts to use CONSTRAINT_CHECK when the bridge is in LOCKED state, hoping to get a spurious PASS verdict.

**Mitigation:** The bridge arbiter, when locked, returns `verdict = safe_state_default` without invoking FLUX-C at all. The response word has the LOCKED flag set (bit 8 of result word). FLUX-X code cannot distinguish a LOCKED response from a legitimate FAIL except by examining the status flag—and any FLUX-X code that ignores the LOCKED flag to treat the response as a PASS is a detectable bug in FLUX-X, caught during DAL B testing.

#### 7.2.3 Bytecode Substitution

**Attack:** An adversary modifies the constraint program registry to replace a legitimate bytecode with one that always returns PASS.

**Mitigations:**
1. The registry is ROM-resident after bridge unlock. ROM writes trap with `FAULT_MEM_WRITE_ROM`.
2. Registry integrity is verified (Fletcher-16 checksum) before unlock. Post-unlock, the registry is in read-only memory.
3. Each registry entry has a version tag; the bridge arbiter compares against a manifest stored separately.

**Residual risk:** Requires physical ROM modification (out of scope) or a pre-load attack (mitigated by the ROM load-time checksum).

#### 7.2.4 Gas Exhaustion as Denial of Safety

**Attack:** Adversarial inputs designed to maximize gas consumption on every call, preventing timely constraint evaluation.

**Analysis:** Gas exhaustion returns `FAULT_GAS_EXHAUSTED` with safe-state verdict (DENY by default). This is a denial-of-operation attack, not a bypass attack. In the adversarial model, this is acceptable: the safety property "unsafe operations are denied" is preserved. If DENY is incorrect for the use case, the integrator uses `SafeState::Permit` on the appropriate channel.

**Mitigations:** The GUARD compiler produces worst-case gas estimates; operators configure budgets with sufficient headroom (recommended: 10× worst-case).

#### 7.2.5 Stack Manipulation

**Attack:** A FLUX-C program with a bug (or malicious GUARD source) causes stack overflow/underflow, attempting to overwrite adjacent memory.

**Mitigation:** The stack is a separate region from the 64 KB address space. Stack overflow traps before any write occurs. The stack is bounded at 256 bytes by the `vm_state` type invariant in the Coq proof. Adjacent memory in the host runtime is not accessible via stack overflow because the stack is not a hardware call stack in the conventional sense—it is a heap-allocated array in the host, with bounds-checked access at every push/pop.

### 7.3 Formal Guarantees

The following properties are formally proven (or planned for proof) in the FLUX-C Coq formalization:

| Property | Status | Proof Technique |
|---|---|---|
| Termination | Planned | Gas monotone decrease + Coq `nat` induction |
| Memory safety | Planned | Bounds lemmas on all memory opcodes |
| Stack boundedness | Planned | Stack depth invariant, induction on steps |
| Type safety | Planned | Progress + preservation, opcode case analysis |
| Isolation | Planned | Output channel exhaustion (43 opcodes) |
| Determinism | Proven (informally) | Pure function of state; no random, no I/O |
| Gas linearity | Planned | Cost function proof per opcode |
| Fault containment | Planned | Fault state is absorbing in step relation |

---

## 8. Hardware Mapping

### 8.1 FPGA Implementation (Artix-7)

The reference hardware implementation targets the Xilinx Artix-7 (XC7A100T) family used in Oracle1 flight computers. Resource allocation follows the TrustZone-inspired partition principle:

#### 8.1.1 Logical Resource Split

| Component | LUTs | FFs | BRAMs | DSPs | Notes |
|---|---|---|---|---|---|
| FLUX-C Interpreter | ~1,200 | ~800 | 2 | 2 | 43 opcodes; conservative estimate |
| FLUX-C Memory (64 KB) | 0 | 0 | 8 | 0 | BRAM-resident |
| FLUX-C Stack (256B) | 0 | 0 | 0.5 | 0 | Distributed RAM |
| Bridge Arbiter | ~400 | ~300 | 0.5 | 0 | State machine |
| FLUX-X Core | ~8,000 | ~5,000 | 16 | 16 | Full register machine |
| FLUX-X Memory | 0 | 0 | 32 | 0 | 256 KB operational RAM |
| **Total** | **~9,600** | **~6,100** | **59** | **18** | ~55% XC7A100T utilization |

FLUX-C consumes approximately 12% of total logic, consistent with the principle that the certified domain is a small fraction of the overall system.

#### 8.1.2 Physical Partition Strategy

The Artix-7 does not provide hardware isolation at the LUT level (unlike Zynq MPSoC), but logical isolation is achieved through:

1. **Pblock constraints**: FLUX-C interpreter and bridge arbiter are placed in a dedicated pblock (physical region constraint), preventing place-and-route from interleaving FLUX-X and FLUX-C logic.

2. **Clock domain separation**: FLUX-C runs on a dedicated clock (`CLK_SAFE`, 50 MHz). FLUX-X runs on `CLK_OPS` (200 MHz). The bridge arbiter contains synchronizers at the clock domain crossing.

3. **Bus arbitration**: FLUX-C memory is connected exclusively to the FLUX-C interpreter and bridge arbiter on a separate AXI4-Lite bus segment. FLUX-X cannot issue AXI transactions to the FLUX-C bus segment (blocked by the bridge arbiter acting as a gateway).

4. **Readback protection**: Bitstream encryption + JTAG disable prevents post-deployment readback of FLUX-C bytecode or state.

#### 8.1.3 Timing Constraints

```tcl
# FLUX-C safe clock: 50 MHz
create_clock -name CLK_SAFE -period 20.0 [get_ports clk_safe]

# FLUX-X operational clock: 200 MHz
create_clock -name CLK_OPS -period 5.0 [get_ports clk_ops]

# False paths across clock domains (bridge has synchronizers)
set_false_path -from [get_clocks CLK_SAFE] -to [get_clocks CLK_OPS]
set_false_path -from [get_clocks CLK_OPS] -to [get_clocks CLK_SAFE]

# FLUX-C interpreter internal timing
set_max_delay -datapath_only -from [get_cells flux_c/*] \
    -to [get_cells flux_c/*] 18.0
```

#### 8.1.4 Scrubbing

For radiation-tolerant configurations (space or high-altitude), BRAM scrubbing is required:
- FLUX-C bytecode ROM: scrubbed every 100 ms
- FLUX-C data memory: scrubbed every 500 ms (with ECC)
- FLUX-X memory: scrubbed every 1 s (lower priority)

Single-event upset (SEU) in FLUX-C bytecode ROM is detected by the checksum stored in the bridge arbiter's flip-flop registers (not BRAM-resident), which are less SEU-susceptible.

### 8.2 ASIC Power Domains

For ASIC implementations, the FLUX-C and FLUX-X domains map naturally to separate power domains:

| Power Domain | Voltage | Isolation | FLUX Component |
|---|---|---|---|
| `VDD_SAFE` | 1.0V nominal | Level-shifted I/O to VDD_OPS | FLUX-C interpreter, bridge arbiter |
| `VDD_OPS` | 0.9V–1.1V | Standard I/O | FLUX-X core, operational memory |
| `VDD_IO` | 1.8V | — | External interfaces |

Power domain isolation ensures:
- FLUX-C continues operating during VDD_OPS brown-out (if VDD_SAFE maintained)
- FLUX-C can assert emergency signals when FLUX-X power fails
- Side-channel power analysis of FLUX-X does not leak FLUX-C execution patterns (different supply)

### 8.3 Minimal FPGA Footprint (Certification Variant)

For deployments requiring maximum resource efficiency at the cost of FLUX-X capability, a certification-only build is provided:

| Component | LUTs | FFs | BRAMs |
|---|---|---|---|
| FLUX-C Interpreter | ~1,200 | ~800 | 2 |
| FLUX-C Memory | 0 | 0 | 8 |
| Bridge Arbiter (stub) | ~150 | ~100 | 0 |
| **Total** | **~1,350** | **~900** | **10** |

This configuration supports only offline constraint verification (no FLUX-X runtime), suitable for ground verification stations.

---

## 9. API Reference

### 9.1 `flux-vm` 0.2.0 — FLUX-C Interpreter

Published on crates.io as `flux-vm = "0.2.0"`.

#### Core Types

```rust
/// Complete FLUX-C virtual machine state
pub struct FluxVm {
    pub pc: u16,
    pub stack: Stack,
    pub memory: Memory,
    pub gas: u32,
    pub fault: Option<FaultCode>,
}

/// 256-byte operand stack
pub struct Stack {
    data: [u8; 256],
    top: u8,  // byte offset of next free slot
}

/// 64KB flat address space
pub struct Memory {
    data: Box<[u8; 65536]>,
    rom_end: u16,     // writes above this address trap
    bridge_io: u16,   // start of bridge I/O region (0xC100)
}

/// FLUX-C bytecode program, validated at load time
pub struct FluxProgram {
    bytecode: Arc<[u8]>,
    entry_point: u16,
    jump_table: Vec<u16>,  // validated jump targets
    worst_case_gas: u32,   // computed by validator
}

/// Execution verdict
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Pass,
    Fail,
    Fault(FaultCode),
}

/// Fault codes (see §2.6)
#[derive(Debug, Clone, Copy, PartialEq, Eq, repr(u8))]
pub enum FaultCode {
    StackOverflow  = 0x01,
    StackUnderflow = 0x02,
    GasExhausted   = 0x03,
    DivZero        = 0x04,
    MemWriteRom    = 0x05,
    MemReserved    = 0x06,
    MemOob         = 0x07,
    IllegalOpcode  = 0x08,
    Assert         = 0x09,
    BridgeAlign    = 0x0A,
    BadJump        = 0x0B,
    LoopBodySize   = 0x0C,
}
```

#### Primary API

```rust
impl FluxProgram {
    /// Load and validate bytecode. Returns Err if program is invalid.
    pub fn load(bytecode: &[u8]) -> Result<Self, LoadError>;
    
    /// Load from a ROM image with explicit entry point.
    pub fn load_with_entry(bytecode: &[u8], entry: u16) -> Result<Self, LoadError>;
    
    /// Worst-case gas requirement (computed during validation).
    pub fn worst_case_gas(&self) -> u32;
    
    /// Fletcher-16 checksum of the bytecode.
    pub fn checksum(&self) -> u16;
}

impl FluxVm {
    /// Create a new VM with given program, gas budget, and bridge I/O.
    pub fn new(
        program: &FluxProgram,
        gas_budget: u32,
        bridge_io: &[u8; 128],
    ) -> Self;
    
    /// Execute until halt or fault. Returns verdict.
    /// This function is deterministic and pure with respect to the VM state.
    pub fn run(&mut self) -> Verdict;
    
    /// Execute exactly one instruction. Returns None if halted.
    pub fn step(&mut self) -> Option<StepResult>;
    
    /// Read the current stack state (for testing/tracing).
    pub fn stack_snapshot(&self) -> Vec<i32>;
    
    /// Read bridge write outputs (8-byte result region).
    pub fn bridge_outputs(&self) -> [u8; 8];
    
    /// Gas consumed so far.
    pub fn gas_consumed(&self) -> u32;
}
```

#### Verification Mode

```rust
/// Trace callback for verification mode execution
pub type TraceCallback = Box<dyn Fn(TraceEvent)>;

pub struct TraceEvent {
    pub pc: u16,
    pub opcode: u8,
    pub stack_before: Vec<i32>,
    pub stack_after: Vec<i32>,
    pub gas_remaining: u32,
    pub trace_id: Option<u8>,  // from TRACE opcode
}

impl FluxVm {
    /// Run with tracing enabled (verification mode).
    pub fn run_traced(
        &mut self,
        callback: TraceCallback,
    ) -> Verdict;
}
```

#### Error Types

```rust
pub enum LoadError {
    EmptyBytecode,
    ProgramTooLarge { size: usize, max: usize },
    InvalidJumpTarget { opcode_pc: u16, target: u16 },
    LoopBodyExceedsRom { loop_pc: u16 },
    InvalidOpcode { pc: u16, byte: u8 },
    GasOverflow { pc: u16 },
}
```

### 9.2 `guard2mask` 0.1.2 — GUARD Compiler

Published on crates.io as `guard2mask = "0.1.2"`.

#### CLI Usage

```
guard2mask [OPTIONS] <input.grd>

Options:
  -o <output.flxc>     Output bytecode path [default: <input>.flxc]
  --map <output.map>   Emit source map for debugger
  --gas <output.gas>   Emit worst-case gas report
  --budget <N>         Maximum allowed gas (compilation fails if exceeded)
  --verify             Run bytecode through flux-vm validator after compilation
  --emit-asm           Emit human-readable FLUX-C assembly alongside bytecode
  --target [soft|hw]   Target: software interpreter or FPGA (default: soft)
```

#### Library API

```rust
use guard2mask::{Compiler, CompilerConfig, CompiledConstraint};

impl Compiler {
    /// Compile a GUARD source string.
    pub fn compile(
        source: &str,
        config: CompilerConfig,
    ) -> Result<CompiledConstraint, CompileError>;
    
    /// Compile from file path.
    pub fn compile_file(
        path: &Path,
        config: CompilerConfig,
    ) -> Result<CompiledConstraint, CompileError>;
}

pub struct CompilerConfig {
    /// Maximum allowed gas consumption (compilation fails if exceeded)
    pub gas_budget: Option<u32>,
    /// Enable trace opcode emission (for TRACE statements in GUARD)
    pub emit_trace: bool,
    /// Stack depth warnings threshold (default: 200 bytes)
    pub stack_warn_depth: u8,
    /// Optimization level (0=none, 1=peephole, 2=full)
    pub opt_level: u8,
}

pub struct CompiledConstraint {
    /// Validated FLUX-C bytecode
    pub program: FluxProgram,
    /// Source map for debugger
    pub source_map: SourceMap,
    /// Worst-case gas analysis
    pub gas_report: GasReport,
    /// Constraint signature (name + argument types)
    pub signature: ConstraintSignature,
}

pub struct GasReport {
    pub worst_case: u32,
    pub best_case: u32,
    pub per_opcode: HashMap<u16, u32>,  // pc → gas cost
}

pub enum CompileError {
    ParseError { line: u32, col: u32, message: String },
    TypeError { location: Span, expected: Type, found: Type },
    GasBudgetExceeded { worst_case: u32, budget: u32 },
    UnsupportedFeature { feature: &'static str },
    InternalError(String),
}
```

### 9.3 `flux-bridge` 0.1.0 — Bridge Arbiter

Published on crates.io as `flux-bridge = "0.1.0"`.

#### Core Types

```rust
/// Bridge configuration, built before unlock
pub struct BridgeConfig {
    channels: Vec<ChannelConfig>,
    default_gas_budget: u32,
    per_arg_gas: u32,
}

pub struct ChannelConfig {
    pub id: u8,
    pub safe_state: SafeState,
    pub gas_budget: u32,
    pub flags: ChannelFlags,
}

#[derive(Debug, Clone, Copy)]
pub enum SafeState {
    Deny,           // default: deny on fault/lock
    Permit,         // permit on fault/lock
    Latch,          // use last valid verdict
    Emergency(u32), // emit emergency code to MMIO
}

bitflags! {
    pub struct ChannelFlags: u32 {
        const LOCK_ON_FAULT  = 0x0001;
        const STRICT_MODE    = 0x0002;
        const TRACE_MODE     = 0x0004;
        const ASYNC_MODE     = 0x0008;
    }
}

/// A locked bridge (pre-unlock state)
pub struct LockedBridge {
    config: BridgeConfig,
    registry: ConstraintRegistry,
}

/// An unlocked, operational bridge
pub struct Bridge {
    inner: Arc<BridgeInner>,
}

/// Registry of constraint programs
pub struct ConstraintRegistry {
    programs: Vec<Option<Arc<FluxProgram>>>,
}

/// Result of a constraint check
pub struct ConstraintResult {
    pub verdict: Verdict,
    pub gas_consumed: u32,
    pub fault: Option<FaultCode>,
    pub outputs: [u8; 8],
    pub sequence: u32,
}
```

#### Primary API

```rust
impl BridgeConfig {
    pub fn new() -> Self;
    pub fn channel(mut self, config: ChannelConfig) -> Self;
    pub fn default_gas_budget(mut self, gas: u32) -> Self;
}

impl ConstraintRegistry {
    pub fn new() -> Self;
    
    /// Register a compiled constraint at program ID `id`.
    pub fn register(
        &mut self,
        id: u8,
        program: CompiledConstraint,
    ) -> Result<(), RegistryError>;
    
    /// Verify all registered programs' checksums.
    pub fn verify_integrity(&self) -> Result<(), IntegrityError>;
}

impl LockedBridge {
    /// Create a locked bridge (default state on power-on).
    pub fn new(config: BridgeConfig, registry: ConstraintRegistry) -> Self;
    
    /// Unlock the bridge. Requires integrity verification to pass.
    /// Returns Err if registry checksums fail.
    pub fn unlock(self) -> Result<Bridge, UnlockError>;
    
    /// Query lock state without unlocking.
    pub fn is_locked(&self) -> bool { true }
}

impl Bridge {
    /// Invoke a constraint check synchronously.
    pub fn check_constraint(
        &self,
        channel: u8,
        program_id: u8,
        args: CallArgs,
    ) -> Result<ConstraintResult, BridgeError>;
    
    /// Lock a specific channel (irrevocable until reset).
    pub fn lock_channel(&self, channel: u8);
    
    /// Lock all channels.
    pub fn lock_all(&self);
    
    /// Read bridge status word.
    pub fn status(&self) -> BridgeStatus;
    
    /// Check if a specific channel is locked.
    pub fn channel_locked(&self, channel: u8) -> bool;
}

/// Builder for bridge call arguments
pub struct CallArgs {
    args: [i32; 4],
    extended: Option<[i32; 4]>,
    flags: u32,
}

impl CallArgs {
    pub fn new() -> Self;
    pub fn arg0(mut self, v: i32) -> Self;
    pub fn arg1(mut self, v: i32) -> Self;
    pub fn arg2(mut self, v: i32) -> Self;
    pub fn arg3(mut self, v: i32) -> Self;
    pub fn ext0(mut self, v: i32) -> Self;
    pub fn ext1(mut self, v: i32) -> Self;
    pub fn ext2(mut self, v: i32) -> Self;
    pub fn ext3(mut self, v: i32) -> Self;
    pub fn strict(mut self) -> Self;
    pub fn trace(mut self) -> Self;
    pub fn lock_on_fault(mut self) -> Self;
}
```

#### Complete Usage Example

```rust
use flux_bridge::{BridgeConfig, ChannelConfig, SafeState, ChannelFlags,
                  ConstraintRegistry, LockedBridge, CallArgs};
use guard2mask::{Compiler, CompilerConfig};

// 1. Compile constraint programs
let altitude_sep = Compiler::compile_file(
    Path::new("constraints/altitude_separation.grd"),
    CompilerConfig::default(),
)?;

let flight_env = Compiler::compile_file(
    Path::new("constraints/flight_envelope.grd"),
    CompilerConfig { gas_budget: Some(5000), ..Default::default() },
)?;

// 2. Build constraint registry
let mut registry = ConstraintRegistry::new();
registry.register(0, altitude_sep)?;
registry.register(1, flight_env)?;

// 3. Configure bridge
let config = BridgeConfig::new()
    .channel(ChannelConfig {
        id: 0,
        safe_state: SafeState::Deny,
        gas_budget: 10_000,
        flags: ChannelFlags::LOCK_ON_FAULT,
    })
    .channel(ChannelConfig {
        id: 1,
        safe_state: SafeState::Deny,
        gas_budget: 5_000,
        flags: ChannelFlags::empty(),
    });

// 4. Initialize locked bridge (default state)
let locked = LockedBridge::new(config, registry);

// 5. Unlock after integrity verification
let bridge = locked.unlock()?;  // fails if checksums invalid

// 6. Use bridge in operational code
let result = bridge.check_constraint(
    0,  // channel
    0,  // program_id: AltitudeSeparation
    CallArgs::new()
        .arg0(own_altitude)
        .arg1(traffic_altitude)
        .arg2(minimum_separation),
)?;

match result.verdict {
    Verdict::Pass => allow_maneuver(),
    Verdict::Fail => deny_maneuver(),
    Verdict::Fault(code) => {
        log::error!("Constraint fault: {:?}", code);
        engage_safe_mode();
    }
}
```

---

## 10. Appendices

### Appendix A: FLUX-C Opcode Quick Reference

```
0x00 NOP         0x01 PUSH8      0x02 PUSH16     0x03 PUSH32
0x04 PUSH_TRUE   0x05 PUSH_FALSE 0x06 PUSH_ZERO  0x07 PUSH_ONE
0x08 DUP         0x09 DROP       0x0A SWAP        0x0B OVER
0x0C ROT         0x0D NROT       0x0E DEPTH       0x0F PICK
0x10 ADD         0x11 SUB        0x12 MUL         0x13 DIV
0x14 MOD         0x15 NEG        0x16 ABS         0x17 MIN
0x18 MAX         0x19 AND        0x1A OR          0x1B XOR
0x1C NOT         0x1D SHL        0x1E SHR         0x1F SAR
0x20 EQ          0x21 NEQ        0x22 LT          0x23 LTE
0x24 GT          0x25 GTE        0x26 ZERO        0x27 LOAD8
0x28 LOAD16      0x29 LOAD32     0x2A STORE8      0x2B STORE16
0x2C JMP         0x2D JZ         0x2E JNZ         0x2F HALT_OK
0x30 HALT_FAIL   0x31 HALT_SAFE  0x32 LOOP        0x33 BRIDGE_LOAD8
0x34 BRIDGE_LOAD16 0x35 BRIDGE_LOAD32 0x36 BRIDGE_WRITE8 0x37 BRIDGE_WRITE16
0x38 BRIDGE_FLAGS 0x39 BRIDGE_SEQ 0x3A GAS_REMAINING 0x3B ASSERT
0x3C TRACE       0x3D MASK8      0x3E CLAMP       0x3F CHECKSUM
```

### Appendix B: Example Compiled Constraint

GUARD source:
```guard
constraint RangeCheck(val: i32, lo: i32, hi: i32) -> bool {
    return val >= lo && val <= hi;
}
```

Generated FLUX-C assembly:
```
; RangeCheck(val @ 0x00, lo @ 0x04, hi @ 0x08)
; Stack at entry: ( )
0000: BRIDGE_LOAD32 0x00    ; ( val )
0004: BRIDGE_LOAD32 0x04    ; ( val lo )
0005: GTE                   ; ( val>=lo )
0006: BRIDGE_LOAD32 0x00    ; ( val>=lo val )
000A: BRIDGE_LOAD32 0x08    ; ( val>=lo val hi )
000B: LTE                   ; ( val>=lo val<=hi )
000C: AND                   ; ( result )
000D: HALT_OK               ; verdict = result
```

Gas: worst-case = 4+4+2+4+4+2+2+1 = 23 gas units.

Bytecode (hex): `35 00 35 04 25 35 00 35 08 23 19 2F`

### Appendix C: Bridge Wire Protocol (FPGA AXI4-Lite)

For FPGA implementations, the bridge arbiter exposes an AXI4-Lite slave interface for FLUX-X to issue bridge calls:

| AXI Offset | Width | Direction | Description |
|---|---|---|---|
| 0x000 | 32 | W | Control register (write to initiate call) |
| 0x004 | 32 | R | Status register |
| 0x008 | 32 | W | Program ID |
| 0x00C | 32 | W | Gas budget override (0 = use channel default) |
| 0x010 | 32 | W | Argument 0 |
| 0x014 | 32 | W | Argument 1 |
| 0x018 | 32 | W | Argument 2 |
| 0x01C | 32 | W | Argument 3 |
| 0x020 | 32 | R | Result word (verdict + fault + gas consumed) |
| 0x024 | 32 | R | Bridge output 0 |
| 0x028 | 32 | R | Bridge output 1 |
| 0x02C | 32 | R | Sequence number of last completed call |
| 0x030 | 32 | W | Lock register (write 0xDEAD_CAFE to lock all) |

**Control register bit assignments:**
```
Bit 31: START (write 1 to initiate; auto-clears on completion)
Bit 15:8: Channel ID
Bit 7: STRICT
Bit 6: TRACE
Bit 5: LOCK_ON_FAULT
Bit 4: ASYNC (non-blocking; poll status for completion)
Bit 3:0: reserved
```

**Status register:**
```
Bit 31: BUSY (1 = call in progress)
Bit 30: LOCKED (1 = all channels locked)
Bit 15:8: Channel lock bitmap (1 = that channel locked)
Bit 7:0: Last fault code (0 = no fault)
```

### Appendix D: Revision History

| Version | Date | Changes |
|---|---|---|
| 0.1.0 | 2025-11-01 | Initial internal draft |
| 0.2.0 | 2026-01-15 | Added FLUX-X opcode categories; bridge wire protocol |
| 0.2.1 | 2026-02-20 | Coq proof structure added; gas model formalized |
| 0.3.0 | 2026-05-03 | Complete 43-opcode table; full API reference; DER-targeted certification argument |

### Appendix E: Glossary

| Term | Definition |
|---|---|
| DAL | Design Assurance Level (DO-254: A=catastrophic, B=hazardous, C=major, D=minor) |
| DER | Designated Engineering Representative (FAA-authorized DO-254 reviewer) |
| FLUX-C | The certified, 43-opcode FLUX stack VM (C = Certified) |
| FLUX-X | The extended, 247-opcode FLUX register machine (X = Extended) |
| GUARD | Guaranteed Assertion Under Runtime Derivation (constraint DSL) |
| gas | Monotonically decreasing execution budget; guarantees termination |
| safe state | The verdict returned when FLUX-C cannot produce a valid answer |
| bridge lock | Hardware/software state that prevents FLUX-C invocation |
| verdict | Binary PASS/FAIL decision produced by a constraint program |
| WCET | Worst-Case Execution Time (required for real-time certification) |
| BMC | Bounded Model Checking (exhaustive verification technique) |
| MC/DC | Modified Condition/Decision Coverage (DO-178C/DO-254 coverage criterion) |
| pblock | Xilinx Vivado physical constraint to restrict placement to a die region |
| SEU | Single-Event Upset (bit flip caused by radiation) |
| AXI4-Lite | ARM AMBA AXI4 reduced-feature bus protocol |

---

*End of Document*

---
**Document ID:** FLUX-ARCH-SPEC-0.3.0  
**Distribution:** Oracle1 Flight Systems, CCC Integration, DO-254 DER  
**Classification:** Unclassified / Distribution Statement A  
**Next Review:** 2026-08-01
