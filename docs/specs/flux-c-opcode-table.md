Here is the complete FLUX-C instruction set extracted from `flux_vm.rs`. Note: there are **42** defined opcodes (0x00–0x29); all unknown opcodes fall through as NOP. Gas cost is uniform — the VM decrements by 1 per `step()` call regardless of opcode.

| Opcode | Mnemonic | Stack Effect | Gas Cost | Category |
|--------|----------|--------------|----------|----------|
| `0x00` | `PUSH val` | `( -- v )` | 1 | Stack |
| `0x01` | `POP` | `( v -- )` | 1 | Stack |
| `0x02` | `DUP` | `( v -- v v )` | 1 | Stack |
| `0x03` | `SWAP` | `( a b -- b a )` | 1 | Stack |
| `0x04` | `LOAD addr` | `( -- mem[addr] )` | 1 | Memory |
| `0x05` | `STORE addr` | `( v -- )` | 1 | Memory |
| `0x06` | `ADD` | `( a b -- a+b )` | 1 | Arithmetic |
| `0x07` | `SUB` | `( a b -- a-b )` | 1 | Arithmetic |
| `0x08` | `MUL` | `( a b -- a*b )` | 1 | Arithmetic |
| `0x09` | `AND` | `( a b -- a&b )` | 1 | Bitwise |
| `0x0A` | `OR` | `( a b -- a\|b )` | 1 | Bitwise |
| `0x0B` | `XOR` | `( a b -- a^b )` | 1 | Bitwise |
| `0x0C` | `NOT` | `( a -- ~a )` | 1 | Bitwise |
| `0x0D` | `SHL` | `( a -- a<<1 )` | 1 | Bitwise |
| `0x0E` | `SHR` | `( a -- a>>1 )` | 1 | Bitwise |
| `0x0F` | `EQ` | `( a b -- a==b )` | 1 | Comparison |
| `0x10` | `NEQ` | `( a b -- a!=b )` | 1 | Comparison |
| `0x11` | `LT` | `( a b -- a<b )` | 1 | Comparison |
| `0x12` | `GT` | `( a b -- a>b )` | 1 | Comparison |
| `0x13` | `LTE` | `( a b -- a<=b )` | 1 | Comparison |
| `0x14` | `GTE` | `( a b -- a>=b )` | 1 | Comparison |
| `0x15` | `JUMP addr` | `( -- )` | 1 | Control Flow |
| `0x16` | `JZ addr` | `( v -- )` | 1 | Control Flow |
| `0x17` | `JNZ addr` | `( v -- )` | 1 | Control Flow |
| `0x18` | `CALL addr` | `( -- )` | 1 | Control Flow |
| `0x19` | `RET` | `( -- )` | 1 | Control Flow |
| `0x1A` | `HALT` | `( -- )` | 1 | Exec Control |
| `0x1B` | `ASSERT` | `( v -- )` | 1 | Exec Control |
| `0x1C` | `CHECK_DOMAIN mask` | `( v -- v&mask )` | 1 | Constraint |
| `0x1D` | `BITMASK_RANGE lo hi` | `( v -- bool )` | 1 | Constraint |
| `0x1E` | `LOAD_GUARD` | `( -- guard_reg )` | 1 | Constraint |
| `0x1F` | `MERKLE_VERIFY` | `( b0 b1 b2 b3 -- 1 )` | 1 | Constraint |
| `0x20` | `GUARD_TRAP` | `( -- )` *(fault)* | 1 | Constraint |
| `0x21` | `CRC32` | `( -- xor_fold )` | 1 | Hash/Crypto |
| `0x22` | `PUSH_HASH hi lo` | `( -- hi lo )` | 1 | Hash/Crypto |
| `0x23` | `XNOR_POPCOUNT` | `( a b -- popcount(~(a^b)) )` | 1 | Hash/Crypto |
| `0x24` | `CMP_GE` | `( a b -- a>=b )` | 1 | Ext. Comparison |
| `0x25` | `CARRY_LT` | `( a b -- a<b )` | 1 | Ext. Comparison |
| `0x26` | `JFAIL addr` | `( -- )` | 1 | Ext. Comparison |
| `0x27` | `NOP` | `( -- )` | 1 | Misc |
| `0x28` | `FLUSH` | `( ... -- )` *(clears stack)* | 1 | Misc |
| `0x29` | `YIELD` | `( -- )` | 1 | Misc |

**Notes:**

- The file defines **42 opcodes** (0x00–0x29), not 43. Opcodes above 0x29 are silently treated as NOP per the `_ => {}` arm.
- Gas is flat: 1 unit deducted per `step()` call at line 92, before opcode dispatch — there is no per-opcode differential pricing.
- `CHECK_DOMAIN`, `BITMASK_RANGE`, `ASSERT`, and `MERKLE_VERIFY` all write to `last_check_passed`, which `JFAIL` reads for conditional branching — forming the constraint-checking subsystem.
- `MERKLE_VERIFY` is currently a stub (always passes); `CRC32` is an XOR-fold of the entire stack, not a true CRC-32.
