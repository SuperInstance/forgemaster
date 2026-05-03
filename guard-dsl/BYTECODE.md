# GUARD → FLUX Bytecode Mapping

This document shows the exact FLUX 43-opcode stack VM bytecode produced by the GUARD compiler for **Example (a): Throttle Limit**.

## Source Module

```guard
module ThrottleLimit
  version "1.0.0"
  for "ECU-320 Throttle Body Authority"
;

dimension Percent is real % from 0 % to 100 %;

state throttle_command has real in [0 % .. 100 %]
  sampled every 10 ms;

invariant ThrottleMustNotExceedMax
  critical
  ensure throttle_command ≤ 100 %
  on_violation halt;

invariant ThrottleMustNotReverse
  critical
  ensure throttle_command ≥ 0 %
  on_violation halt;
```

## Compilation Strategy

The GUARD compiler performs these lowering passes:

1. **Desugar** — Remove syntactic sugar, expand derived rules, normalize temporal operators.
2. **Typecheck** — Verify unit consistency (e.g., `%` is dimensionless scalar 0–100 mapped to 0.0–1.0).
3. **Unit Lowering** — Convert all physical quantities to normalized `f64` values.
   - `throttle_command` → memory slot 0, range [0.0, 1.0]
   - `100 %` → constant `1.0`
   - `0 %` → constant `0.0`
4. **Bytecode Generation** — Emit FLUX instructions with source-location metadata.
5. **Certificate Generation** — Produce proof artifact alongside bytecode.

## Compiled Bytecode

| Offset | Opcode   | Operands      | Source Location          | Semantic Description                              |
|--------|----------|---------------|--------------------------|---------------------------------------------------|
| 0      | `Nop`    | —             | `throttle.guard:1:1`      | Module header padding / alignment                 |
| 1      | `Push`   | `1.0`         | `throttle.guard:13:33`    | Load constant 100 % (normalized)                  |
| 2      | `Store`  | `0`           | `throttle.guard:10:1`     | Initialize upper bound register                   |
| 3      | `Push`   | `0.0`         | `throttle.guard:18:33`    | Load constant 0 % (normalized)                    |
| 4      | `Store`  | `1`           | `throttle.guard:10:1`     | Initialize lower bound register                   |
| 5      | `Push`   | `0.0`         | `throttle.guard:10:1`     | Push default throttle value (cold-start)          |
| 6      | `Store`  | `2`           | `throttle.guard:10:1`     | Store to `throttle_command` slot                  |
| 7      | `Trace`  | —             | `throttle.guard:1:1`      | Mark start of runtime check loop                  |
| 8      | `Load`   | `2`           | `throttle.guard:13:10`    | Push current `throttle_command`                   |
| 9      | `Load`   | `0`           | `throttle.guard:13:33`    | Push upper bound (1.0)                            |
| 10     | `Le`     | —             | `throttle.guard:13:26`    | Compare: `throttle ≤ 1.0`                         |
| 11     | `Assert` | `0`           | `throttle.guard:13:3`     | **Hard constraint** `ThrottleMustNotExceedMax`    |
| 12     | `Load`   | `2`           | `throttle.guard:18:10`    | Push current `throttle_command`                   |
| 13     | `Load`   | `1`           | `throttle.guard:18:33`    | Push lower bound (0.0)                            |
| 14     | `Ge`     | —             | `throttle.guard:18:26`    | Compare: `throttle ≥ 0.0`                         |
| 15     | `Assert` | `1`           | `throttle.guard:18:3`     | **Hard constraint** `ThrottleMustNotReverse`      |
| 16     | `Nop`    | —             | `throttle.guard:1:1`      | Yield / wait for next sample (10 ms)              |
| 17     | `Jump`   | `8`           | `throttle.guard:1:1`      | Loop back to `Trace` at offset 8                  |

### Instruction Encoding (hex dump)

```
Offset  0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
------ -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
0000   70 32 01 3F F0 00 00 00 00 00 00 00 51 00 32 01
0010   00 00 00 00 00 00 00 00 51 01 32 01 00 00 00 00
0020   00 00 00 00 51 02 72 50 02 50 00 34 60 01 50 02
0030   50 01 35 60 01 70 40 08
```

### Byte-by-byte breakdown

- `70` = `Nop`
- `32 01 3F F0 ...` = `Push` with 1 operand (0x3FF0000000000000 = 1.0 in IEEE 754)
- `51 00` = `Store` to slot 0 (operand = 0.0 encoded as slot index)
- `32 01 00 00 ...` = `Push` 0.0
- `51 01` = `Store` to slot 1
- `72` = `Trace`
- `50 02` = `Load` slot 2 (`throttle_command`)
- `50 00` = `Load` slot 0 (upper bound)
- `34` = `Le` (≤)
- `60 01` = `Assert` with constraint ID 1 (`ThrottleMustNotExceedMax`)
- `50 02` = `Load` slot 2
- `50 01` = `Load` slot 1 (lower bound)
- `35` = `Ge` (≥)
- `60 01` = `Assert` with constraint ID 2 (`ThrottleMustNotReverse`)
- `70` = `Nop` (yield)
- `40 08` = `Jump` to offset 8

## Runtime Behavior

1. On power-up, the VM initializes constants and state slots.
2. Enters the **constraint loop** at offset 8.
3. Every 10 ms (driven by external scheduler), the host writes the new sensor value into slot 2, then triggers one VM iteration.
4. If either `Assert` fails, the VM immediately halts with `FluxError::ConstraintViolation`, yielding the source location and constraint name from the instruction metadata.
5. The `Trace` opcode at the loop head captures a Merkle-compatible execution trace for the proof certificate.

## Temporal Expansion Note

For non-temporal invariants like this example, the GUARD compiler emits a **single-step check loop**. Temporal invariants (e.g., `for 3 s`, `always`) are expanded into **history buffer management** before the constraint expression, using additional memory slots and a sub-loop counter.
