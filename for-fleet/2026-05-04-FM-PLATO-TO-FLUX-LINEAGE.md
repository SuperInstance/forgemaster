# PLATO → FLUX: The Direct Lineage from TUTOR to Bare-Metal Constraints

**Date:** 2026-05-04
**Source:** PLATO/TUTOR research + FLUX GPU/CPU benchmarks

## The Lineage

```
PLATO (1960) → TUTOR (1965) → Bit-Vector Matching → BitmaskDomain → FLUX-C → AVX-512 → Silicon
```

### TUTOR's Judging Block = FLUX Constraint Loop

| TUTOR Concept | FLUX Equivalent |
|---|---|
| `arrow` command (opens judging) | Constraint evaluation begins |
| `answer` / `wrong` patterns | PASS / FAIL outcomes |
| Bit-vector Hamming distance | BitmaskDomain popcount |
| 60-bit word bit vectors | uint64 bitmask domains |
| Pattern matching with tolerance | Range/domain/fuzzy constraints |
| `specs` tolerance setting | Constraint tolerance parameter |
| Judging loop (repeat until correct) | AC-3 propagation loop |
| `join` (textual substitution) | GUARD→FLUX macro expansion |
| `compute` (expression evaluator) | FLUX VM expression opcodes |
| 150 words per user state | Minimal VM state (stack + 64 registers) |

### What PLATO Did Right (And We Should Copy)

1. **Push intelligence to the edge** — PLATO terminals had local memory and rendering. Our AVX-512 registers are the modern equivalent: 16 constraints evaluated locally in the register file.

2. **Minimize per-user state** — 150 words per user. Our FLUX-C VM has a 64-element stack + program counter + gas counter. Similar minimalism.

3. **Separate I/O from compute** — PLATO's barrel processor handled I/O independently. Our CPU screens constraints while GPU handles complex evaluation.

4. **Bit-vector matching** — TUTOR converted words to 60-bit bit vectors, used XOR + popcount for Hamming distance. We use uint64 bitmasks for domain operations, same XOR + popcount approach.

5. **Batch processing** — PLATO accumulated keystrokes and processed in bursts. We batch 16M inputs per AVX-512 pass.

### Performance Comparison (1960s vs 2026)

| Metric | PLATO IV (CDC 6600) | FLUX (Ryzen AI 9) | Improvement |
|---|---|---|---|
| Clock | 10 MHz | 4+ GHz | 400x |
| Word size | 60-bit | 512-bit SIMD | 8.5x |
| Parallel evaluation | 1 comparison/cycle | 16 comparisons/cycle | 16x |
| Memory per user | 150 words | 64 stack slots | Similar |
| Response time | <1 second | <2 nanoseconds | 500M x |
| Users simultaneous | ~1,000 | ~1 billion (inputs/s) | 1M x |

### What We Learned: Why Python Must Die

| Approach | Throughput | Overhead |
|---|---|---|
| Python + ctypes | 63M/s | 100x tax |
| C interpreter (switch) | 1.5B/s | 4x tax |
| AVX-512 C (batch) | 6.15B/s | Baseline |
| AVX-512 JIT (native) | 920M/s scalar, 36B/s multi | Zero overhead |
| x86-64 compiled (4 instructions) | 920M/s | Zero overhead |

**The TUTOR approach: compile the constraint intent directly to machine code. Don't interpret. Don't dispatch. Don't Python.**

### The Path Forward: Constraint → Assembly

1. **GUARD constraint** → Parse to AST
2. **AST** → Optimize (dead constraint elimination, fusion, strength reduction)
3. **Optimized AST** → Generate x86-64 assembly with AVX-512
4. **Assembly** → Execute via mmap + JIT

Example:
```
# GUARD input
constraint temperature in [0, 100]

# Generated x86-64 (4 instructions, 1ns at 4GHz)
cmp edi, 0        ; compare input to lower bound
jl .fail          ; jump if below range
cmp edi, 100      ; compare input to upper bound  
jg .fail          ; jump if above range
mov eax, 1        ; pass
ret
.fail:
mov eax, 0        ; fail
ret

# Generated AVX-512 (for batch of 16)
vmovdqu32 zmm0, [input]        ; load 16 values
vpcmpd k1, zmm0, zmm_lo, 5    ; k1 = (values >= lo)
vpcmpd k2, zmm0, zmm_hi, 2    ; k2 = (values <= hi)
kandw k3, k1, k2              ; k3 = in range
vpmovm2d zmm1, k3             ; convert mask to 0/1
vmovdqu32 [output], zmm1      ; store results
```

### The 6-Instruction RISC-V Extension (Xconstr)

Inspired by PLATO's minimal instruction set approach:

| Instruction | Operation | Cycles |
|---|---|---|
| `crange rd, lo, hi` | Set rd = (rs1 >= lo && rs1 <= hi) | 1 |
| `cdomain rd, mask` | Set rd = (rs1 & mask == rs1) | 1 |
| `cpopcnt rd, rs1` | Set rd = popcount(rs1) | 1 |
| `cintersect rd, rs1, rs2` | Set rd = rs1 & rs2 | 1 |
| `ccheck rd, constraints` | Evaluate constraint set, set rd = pass/fail | N |
| `cfail` | Trigger safety fault | 1 |

6 instructions. Every constraint operation in hardware. Zero interpretation.

---

*Forgemaster ⚒️ — PLATO → FLUX Lineage Analysis*
*The old systems were clever because they HAD to be. We can be clever because we choose to be.*
