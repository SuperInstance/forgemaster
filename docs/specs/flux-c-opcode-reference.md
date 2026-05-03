# FLUX-C Opcode Reference Card

## Stack Operations
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x00 | PUSH | val | 1 | Push val onto stack |
| 0x01 | POP | — | 1 | Discard top of stack |
| 0x02 | DUP | — | 1 | Duplicate top of stack |
| 0x03 | SWAP | — | 1 | Swap top two elements |

## Memory
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x10 | LOAD | addr | 2 | Load from memory address |
| 0x11 | STORE | addr | 2 | Store to memory address |

## Arithmetic
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x08 | IADD | — | 1 | a + b → result |
| 0x09 | ISUB | — | 1 | a - b → result |
| 0x0A | IMUL | — | 2 | a × b → result |
| 0x0B | IDIV | — | 3 | a ÷ b → result |

## Bitwise
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x12 | AND | — | 1 | a AND b |
| 0x13 | OR | — | 1 | a OR b |
| 0x14 | XOR | — | 1 | a XOR b |
| 0x15 | NOT | — | 1 | NOT a |

## Comparison
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x24 | CMP_GE | — | 1 | a ≥ b → 1/0 |
| 0x25 | CMP_EQ | — | 1 | a = b → 1/0 |
| 0x26 | CMP_LT | — | 1 | a < b → 1/0 |
| 0x27 | NOP | — | 1 | No operation |

## Control Flow
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x1A | HALT | — | 1 | Normal termination (pass) |
| 0x1B | ASSERT | — | 1 | Pop; fault if 0 |
| 0x20 | GUARD_TRAP | — | 1 | Immediate fault |
| 0x21 | JMP | addr | 1 | Unconditional jump |
| 0x22 | JNZ | addr | 2 | Jump if top ≠ 0 |
| 0x23 | CALL | addr | 3 | Call subroutine |

## Constraint Checks
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x1C | CHECK_DOMAIN | mask | 3 | v AND mask = v → 1/0 |
| 0x1D | BITMASK_RANGE | lo hi | 3 | lo ≤ v ≤ hi → 1/0 |

## Temporal (v3.0)
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x2A | TICK | — | 1 | Push cycle counter |
| 0x2B | DEADLINE | lo hi | 2 | Set absolute deadline |
| 0x2C | CHECKPOINT | — | 3 | Save VM state → cp_id |
| 0x2D | REVERT | cp_id | 3 | Restore from checkpoint |
| 0x2E | WATCH | addr delta | 3 | Register memory watch |
| 0x2F | WAIT | delta | 2 | Suspend for delta cycles |
| 0x30 | ELAPSED | — | 1 | Time since last tick |
| 0x31 | DRIFT | — | 2 | |target - actual| |

## Security (v3.0)
| Hex | Name | Operands | Gas | Effect |
|-----|------|----------|-----|--------|
| 0x32 | SANDBOX_ENTER | domain | 3 | Enter isolated domain |
| 0x33 | SANDBOX_EXIT | — | 2 | Exit sandbox |
| 0x34 | CAP_GRANT | target perms | 5 | Grant capability |
| 0x35 | CAP_REVOKE | cap_id | 3 | Revoke capability |
| 0x36 | MEM_GUARD | addr size perms | 5 | Set memory protection |
| 0x37 | PROVE | assertion | 10 | Zero-knowledge proof |
| 0x38 | AUDIT_PUSH | event | 2 | Log audit event |
| 0x39 | SEAL | addr size | 5 | Permanently seal memory |

## Fault Types
| Fault | Trigger | Recovery |
|-------|---------|----------|
| AssertFailed | ASSERT pops 0 | Latching — reset required |
| GuardTrap | GUARD_TRAP opcode | Latching — reset required |
| DeadlineExceeded | Cycle > deadline | Latching — reset required |
| GasExhausted | Gas = 0 | Latching — reset required |
| CoIterateDivergence | Max rounds exceeded | Latching — reset required |
| CapRevoked | Revoked capability used | Latching — reset required |
| MemViolation | MEM_GUARD violation | Latching — reset required |

## Gas Costs (Reference)

**Simple operations:** 1-2 gas (PUSH, POP, DUP, SWAP, arithmetic, bitwise, comparison)
**Memory operations:** 2-3 gas (LOAD, STORE)
**Constraint checks:** 3 gas (BITMASK_RANGE, CHECK_DOMAIN)
**Temporal:** 2-3 gas (DEADLINE, CHECKPOINT, REVERT)
**Security:** 2-10 gas (SANDBOX=3, CAP_GRANT=5, PROVE=10)
**Control flow:** 1-3 gas (HALT=1, ASSERT=1, CALL=3)

**Default gas limit:** 1000 (sufficient for ~500 simple constraint checks)

## FLUX-X Extension Opcodes (0x40-0xF7)

These are in the FLUX-X general ISA, not FLUX-C certified enclave:

| Hex Range | Category | Key Opcodes |
|-----------|----------|-------------|
| 0x40-0x46 | Agent Communication | TELL, ASK, BRANCH, FORK, JOIN, YIELD, MERGE |
| 0x50-0x6F | Tensor Operations | TMATMUL, TCONV, TACTIVATE, TPOOL, TNORM |
| 0x70-0x8F | PLATO Bridge | PCONNECT, PQUERY, PSUBMIT, PROOMS, PSEARCH |
| 0x90-0xAF | Extended Arithmetic | FMUL, FDIV, FSQRT, FSIN, FCOS |
| 0xB0-0xCF | String/Data | SLEN, SCAT, SSPLIT, PACK, UNPACK |
| 0xD0-0xEF | System | SYSCALL, PORTIO, IRQ, DMACTL |
| 0xF0-0xF7 | Reserved | Future expansion |

## Quick Reference: GUARD → FLUX Compilation

| GUARD | FLUX-C Bytecode |
|-------|----------------|
| `range(0, 150)` | `1D 00 96` (BITMASK_RANGE 0 150) |
| `range(0, 50)` | `1D 00 32` (BITMASK_RANGE 0 50) |
| `bitmask(63)` | `1C 3F` (CHECK_DOMAIN 63) |
| `thermal(5)` | `00 05 24` (PUSH 5, CMP_GE) |
| `whitelist([0,1,2])` | `00 00 25 00 01 25 00 02 25` (EQ chain) |

---

*FLUX-C Reference v3.0 — 50 opcodes, Apache 2.0*
*forge: github.com/SuperInstance/JetsonClaw1-vessel*
