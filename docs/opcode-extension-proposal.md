# FLUX ISA Extension Proposal: 43 → 51 Opcodes

**Status:** Draft — Based on Kimi 100-Agent Deep Dive (M10 Synthesis)
**Date:** 2026-05-05
**Author:** Forgemaster ⚒️ (from swarm research)

## Motivation

The current 43-opcode ISA requires compound instruction sequences for common safety operations. Across 4 target architectures (x86-64, ARM64, Xtensa LX7, CUDA), these compound sequences take 3-6 cycles but map to single instructions on most platforms. Adding 8 opcodes reduces instruction count by 60-80% on safety-critical workloads.

## Proposed Opcodes

### 1. SATADD (0x2B) — Saturating Add
```
result = min(MAX_INT8, a + b)  // Signed: clamp to [-128, 127]
```
- **x86-64:** `vpaddsb` — 1 cycle (AVX2)
- **ARM64:** `sqadd` — 1 cycle (NEON)
- **CUDA:** `imin(IADD3(a,b), 127)` — 3 cycles
- **ESP32:** `add + min` composite — 2 cycles
- **Replaces:** ADD + CHECK + CLIP (3 instructions → 1)

### 2. SATSUB (0x2C) — Saturating Subtract
```
result = max(MIN_INT8, a - b)  // Signed: clamp to [-128, 127]
```
- **x86-64:** `vpsubsb` — 1 cycle (AVX2)
- **ARM64:** `sqsub` — 1 cycle (NEON)
- **CUDA:** `imax(isub(a,b), -128)` — 3 cycles
- **ESP32:** `sub + max` composite — 2 cycles
- **Replaces:** SUB + CHECK + CLIP (3 instructions → 1)

### 3. CLIP (0x2D) — Clamp to Range
```
result = min(upper, max(lower, value))  // Clamp value to [lower, upper]
```
- **x86-64:** `vpminsb + vpmaxsb` — 2 cycles
- **ARM64:** `smin + smax` — 2 cycles
- **CUDA:** `imin(upper, imax(lower, val))` — 4 cycles
- **ESP32:** `min + max` — 2 cycles
- **Replaces:** LT + JNZ + CONST + GT + JNZ (5 instructions → 1)

### 4. MAD (0x2E) — Multiply-Accumulate
```
result = a * b + c  // Fused multiply-add
```
- **x86-64:** `vpmaddubsw` — 1 cycle (AVX2)
- **ARM64:** `mla` — 1 cycle (NEON)
- **CUDA:** `imad` — 4 cycles
- **ESP32:** `mul + add` — 3 cycles (no hardware mul for INT8)
- **Replaces:** MUL + ADD (2 instructions → 1)

### 5. POPCNT (0x2F) — Population Count
```
result = count_set_bits(value)  // Count 1-bits
```
- **x86-64:** `popcnt` — 1 cycle
- **ARM64:** `cnt` — 1 cycle (NEON)
- **CUDA:** `popc.b32` — 2 cycles
- **ESP32:** 256-byte LUT — ~4 cycles
- **Replaces:** Loop of SHIFT + AND + ADD (8-16 instructions → 1)

### 6. CTZ (0x30) — Count Trailing Zeros
```
result = index_of_lowest_set_bit(value)  // Find first 1-bit from LSB
```
- **x86-64:** `tzcnt` — 1 cycle (BMI1)
- **ARM64:** `rbit + clz` — 2 cycles
- **CUDA:** `ffs + sub` — 4 cycles
- **ESP32:** `clz(reverse_bits(x))` — ~10 cycles
- **Replaces:** Loop of SHIFT + AND + INCR (variable → 1)

### 7. PABS (0x31) — Packed Absolute Value
```
result = |value|  // Absolute value for packed INT8
```
- **x86-64:** `vpabsb` — 1 cycle (SSSE3)
- **ARM64:** `abs` — 1 cycle (NEON)
- **CUDA:** `iabs` / `imax(val, -val)` — 2 cycles
- **ESP32:** `abs` — 1 cycle
- **Replaces:** LT + NEG + SELECT (3 instructions → 1)

### 8. PMIN (0x32) — Packed Minimum
```
result = min(a, b)  // Element-wise minimum
```
- **x86-64:** `vpminsb` — 1 cycle (AVX2)
- **ARM64:** `smin` — 1 cycle (NEON)
- **CUDA:** `imin` — 2 cycles
- **ESP32:** `min` — 1 cycle
- **Replaces:** LT + SELECT (2 instructions → 1)

## Impact Analysis

| Opcode | Instructions Replaced | Cycles Saved (avg) | Safety Relevance |
|--------|----------------------|-------------------|-----------------|
| SATADD | 3 → 1 | 4-8 cycles | Prevents overflow wraparound (P1 vuln) |
| SATSUB | 3 → 1 | 4-8 cycles | Prevents underflow wraparound |
| CLIP | 5 → 1 | 8-15 cycles | Range enforcement (most common op) |
| MAD | 2 → 1 | 2-4 cycles | Weighted constraint evaluation |
| POPCNT | 8-16 → 1 | 12-30 cycles | Violation counting, mask analysis |
| CTZ | variable → 1 | 6-20 cycles | First violation localization |
| PABS | 3 → 1 | 4-8 cycles | Deviation magnitude |
| PMIN | 2 → 1 | 2-4 cycles | Conservative bound selection |

**Total estimated improvement:** 40-97 cycles per constraint evaluation cycle saved.

## Encoding

New opcodes use reserved slots 0x2B-0x32 in the FLUX-C opcode table. All use existing operand encoding formats:
- SATADD/SATSUB/MAD/PMIN: R-type (regA, regB → regDst)
- CLIP: R-type with immediate (reg, lower, upper → regDst)
- POPCNT/CTZ/PABS: R-type unary (regSrc → regDst)

## Compatibility

- **FLUX-C (certified):** Opcodes 0x2B-0x32 are FLUX-X extensions
- **FLUX-X (extended):** All 51 opcodes available
- **FLUX-Mini (embedded):** Only SATADD/SATSUB/CLIP (safety-critical subset)

## References

- Deep dive M10 synthesis: `kimi-swarm-results-2/deepdive_m10_synthesis.md`
- Machine code analysis: `kimi-swarm-results-2/deepdive_m06_machine_code.md`
- Silicon math tables: `kimi-swarm-results-2/deepdive_m04_silicon_math.md`
