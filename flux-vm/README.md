# flux-vm: A 50-Opcode Stack-Based Constraint Checking Virtual Machine

## Overview
flux-vm is a minimal, stack-only virtual machine designed exclusively for formal constraint validation, runtime policy enforcement, and bounded formal verification. Unlike general-purpose VMs such as WASM or Lua, it ships with exactly 50 standardized opcodes grouped into 9 functional categories, with no dynamic memory allocation, unbounded loops, or side effects outside its fixed stack frame. It is purpose-built for use cases where strict safety, determinism, and computable worst-case execution time (WCET) are non-negotiable: zero-knowledge proof constraint checking, embedded system policy enforcement, and smart contract input validation.

## Opcodes
All opcodes use standard stack effect notation, grouped by functional category:

| Mnemonic | Description | Category | Stack Effect |
|---------|-------------|----------|--------------|
| **Stack Operations** | | | |
| `PUSH(n)` | Push 64-bit integer literal `n` to stack | Stack | → `[n]` |
| `POP` | Remove top stack element | Stack | `[a]` → ∅ |
| `DUP` | Duplicate top stack element | Stack | `[a]` → `[a, a]` |
| `SWAP` | Swap top two stack elements | Stack | `[a, b]` → `[b, a]` |
| `OVER` | Copy second-to-top element to top | Stack | `[a, b]` → `[a, b, a]` |
| `ROT` | Rotate top three stack elements left | Stack | `[a, b, c]` → `[b, c, a]` |
| `CLEAR` | Empty entire stack | Stack | `[any...]` → ∅ |
| `PEEK(n)` | Copy `n`th stack element (0 = top) | Stack | `[..., x]` → `[..., x, x]` |
| `DEPTH` | Push current stack depth to top | Stack | → `[d]` |
| `NOP` | No-operation | Stack | ∅ → ∅ |
| **Arithmetic Operations** | | | |
| `ADD` | Pop `a, b`, push `a + b` | Arithmetic | `[a, b]` → `[a+b]` |
| `SUB` | Pop `a, b`, push `a - b` | Arithmetic | `[a, b]` → `[a-b]` |
| `MUL` | Pop `a, b`, push `a * b` | Arithmetic | `[a, b]` → `[a*b]` |
| `DIV` | Pop `a, b`, push `a // b` (signed) | Arithmetic | `[a, b]` → `[a//b]` |
| `MOD` | Pop `a, b`, push `a % b` (signed remainder) | Arithmetic | `[a, b]` → `[a%b]` |
| `EXP` | Pop `a, b`, push `a^b` | Arithmetic | `[a, b]` → `[a^b]` |
| `NEG` | Pop `a`, push `-a` | Arithmetic | `[a]` → `[-a]` |
| `INC` | Pop `a`, push `a + 1` | Arithmetic | `[a]` → `[a+1]` |
| `DEC` | Pop `a`, push `a - 1` | Arithmetic | `[a]` → `[a-1]` |
| `ABS` | Pop `a`, push `\|a\|` | Arithmetic | `[a]` → `[\|a\|]` |
| **Comparison Operations** | | | |
| `EQ` | Pop `a, b`, push 1 if equal, 0 otherwise | Comparison | `[a, b]` → `[1/0]` |
| `NEQ` | Pop `a, b`, push 1 if not equal, 0 otherwise | Comparison | `[a, b]` → `[1/0]` |
| `LT` | Pop `a, b`, push 1 if `a < b`, 0 otherwise | Comparison | `[a, b]` → `[1/0]` |
| `GT` | Pop `a, b`, push 1 if `a > b`, 0 otherwise | Comparison | `[a, b]` → `[1/0]` |
| `LTE` | Pop `a, b`, push 1 if `a ≤ b`, 0 otherwise | Comparison | `[a, b]` → `[1/0]` |
| `GTE` | Pop `a, b`, push 1 if `a ≥ b`, 0 otherwise | Comparison | `[a, b]` → `[1/0]` |
| `ISZERO` | Pop `a`, push 1 if `a = 0`, 0 otherwise | Comparison | `[a]` → `[1/0]` |
| `WITHIN` | Pop `val, min, max`, push 1 if `min ≤ val ≤ max` | Comparison | `[val, min, max]` → `[1/0]` |
| **Range Operations** | | | |
| `SET_RANGE_MIN(n)` | Set global range lower bound to `n` | Range | ∅ → ∅ |
| `SET_RANGE_MAX(n)` | Set global range upper bound to `n` | Range | ∅ → ∅ |
| `CHECK_RANGE` | Pop `val`, trap if outside global range | Range | `[val]` → `[val]` |
| `CLEAR_RANGE` | Reset global range bounds | Range | ∅ → ∅ |
| `GET_RANGE_MIN` | Push current lower bound to stack | Range | → `[min]` |
| `GET_RANGE_MAX` | Push current upper bound to stack | Range | → `[max]` |
| **Domain Operations** | | | |
| `SET_DOMAIN(s)` | Define allowed value set of size `s` | Domain | ∅ → ∅ |
| `CHECK_DOMAIN` | Pop `val`, trap if not in allowed set | Domain | `[val]` → `[val]` |
| `IS_IN_DOMAIN` | Pop `val`, push 1 if in allowed set, 0 otherwise | Domain | `[val]` → `[1/0]` |
| `CLEAR_DOMAIN` | Reset allowed value set | Domain | ∅ → ∅ |
| **Logical Operations** | | | |
| `AND` | Pop `a, b`, push bitwise AND | Logical | `[a, b]` → `[a&b]` |
| `OR` | Pop `a, b`, push bitwise OR | Logical | `[a, b]` → `[a\|b]` |
| `XOR` | Pop `a, b`, push bitwise XOR | Logical | `[a, b]` → `[a^b]` |
| `NOT` | Pop `a`, push bitwise NOT | Logical | `[a]` → `[~a]` |
| **Temporal Operations** | | | |
| `TIMESTAMP_PUSH` | Push current system timestamp to stack | Temporal | → `[ts]` |
| `TIME_COMPARE` | Pop `a, b`, push 1 if `a` precedes `b` | Temporal | `[a, b]` → `[1/0]` |
| `TIME_WINDOW_VALID` | Pop `start, end`, trap if current ts outside window | Temporal | `[start, end]` → `[ts]` |
| **Security Operations** | | | |
| `VERIFY_HASH(hash)` | Pop `data`, trap if hash mismatch | Security | `[data]` → `[data]` |
| `CHECK_SIGNATURE(pubkey)` | Pop `sig, msg`, trap if invalid | Security | `[sig, msg]` → `[sig, msg]` |
| `RESTRICT_EXEC(addr)` | Lock execution to opcode at `addr` | Security | ∅ → ∅ |
| **Control Operations** | | | |
| `JMP(addr)` | Jump to fixed opcode offset | Control | ∅ → ∅ |
| `HALT` | Halt and return stack top | Control | ∅ → ∅ |

## Safety Properties
flux-vm is engineered for strict, verifiable safety:
1.  **Turing-Incomplete**: No unbounded loops or dynamic recursion, with all control flow bounded by fixed offsets