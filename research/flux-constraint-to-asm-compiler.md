# FLUX Constraint-to-Assembly Compiler Design

## The Problem

FLUX has a constraint VM with 50 opcodes (stack-based). Current performance:
- **Python interpreter**: 63M checks/s
- **C interpreter**: 6.15B checks/s
- **Theoretical native**: ~60B+ checks/s

The C interpreter already uses computed goto (direct threading), so the 100x gap Python→C is mostly "Python overhead." But even the C interpreter pays dispatch cost per opcode. **What if we eliminate the interpreter entirely?**

---

## 1. Threaded Code Interpreters (The Forth Model)

### How Forth Does It

Forth has three threading models:

**Token Threading** (simplest, slowest):
```
[OP_ADD, OP_PUSH, 42, OP_MUL, ...]
```
Each opcode is an index into a dispatch table. The interpreter loop:
```c
while (1) { pc++; goto *dispatch[*pc]; }  // indirect jump through table
```
Cost: ~3-5 cycles per dispatch (table lookup + indirect branch).

**Direct Threading** (Forth standard):
```
[&&ADD, &&PUSH, 42, &&MUL, ...]  // actual addresses
```
Each "opcode" is already the address of the handler. The interpreter:
```c
while (1) { pc++; goto **pc; }  // direct jump to handler, then next
```
GCC's `labels-as-values` extension enables this. Cost: ~1-2 cycles per dispatch.

**Indirect Threading** (Forth optimal):
Each compiled word contains a pointer to its execution primitive AND its data. Enables code factoring.

**Subroutine Threading** (compiles to native CALL/RET):
```
call ADD
call PUSH
dw 42
call MUL
```
Each "opcode" is a real function call. No dispatch loop needed. Cost: CALL/RET overhead (~1 cycle on modern CPUs with return prediction).

### FLUX Application

FLUX's 50 opcodes could use **direct threading with computed goto** (already done in the C version based on the 6.15B figure). The next step is subroutine threading or full native compilation.

---

## 2. JIT Compilation for Constraint VMs

### LuaJIT Trace Model

LuaJIT doesn't compile whole functions. It **traces hot loops**:

1. Interpret normally, count loop iterations
2. When a loop is hot (>56 iterations), start recording
3. Record a linear trace (the actual execution path)
4. Optimize the trace (dead code elimination, constant folding, loop-invariant code motion)
5. Compile trace to native code
6. Execute native code; if assumptions hold (no guard exit), stay fast

### FLUX JIT Strategy

FLUX constraint checking has a specific pattern:
```
for each cell in grid:
    for each constraint on cell:
        check constraint → pass/fail
```

This is **embarrassingly trace-friendly**. The inner loop runs millions of times with the same constraints. A FLUX JIT would:

1. Interpret first N iterations of constraint checking
2. Record the trace: a linear sequence of constraint checks
3. Optimize: fuse range checks, eliminate dead constraints, constant-propagate domains
4. Compile to native x86-64
5. Execute with guard exits for rare cases

**But this is still JIT overhead.** We can do better — compile at constraint-definition time, not at runtime.

---

## 3. Constraint-to-Assembly Direct Compilation

### The Key Insight

FLUX constraints are **static** — they're defined once per puzzle type and don't change during solving. There's no need for a JIT. We can compile them **ahead of time** directly to native code.

### Example: GUARD Constraint

**Input** (FLUX constraint specification):
```
GUARD row[3] WHERE digit ∈ {1,2,3,4,5,6,7,8,9}
  CONSTRAINT digit ≥ 1 AND digit ≤ 9
  CONSTRAINT popcount(domain_mask) ≥ 1
  CONSTRAINT digit NOT_IN assigned_neighbors
```

**Output** (x86-64 assembly, what the compiler generates):

```asm
; Input: rdi = pointer to cell struct
;        rsi = pointer to neighbor domain array
;        rdx = neighbor count
; Returns: eax = 1 (pass) or 0 (fail)

flux_check_guard_row3:
    push    rbp
    mov     rbp, rsp

    ; Load cell value and domain mask
    movzx   eax, byte [rdi + CELL_VALUE]    ; digit value (0-9)
    mov     ecx, dword [rdi + CELL_DOMAIN]  ; domain bitmask

    ; Constraint 1: digit ≥ 1 (unsigned)
    test    eax, eax
    jz      .fail

    ; Constraint 2: digit ≤ 9
    cmp     eax, 9
    ja      .fail

    ; Constraint 3: popcount(domain_mask) ≥ 1
    popcnt  ecx, ecx                        ; 1 instruction on modern x86
    test    ecx, ecx
    jz      .fail

    ; Constraint 4: digit NOT_IN assigned_neighbors
    ; Branchless: iterate neighbors, accumulate violations
    xor     r8d, r8d                        ; violation accumulator
    test    rdx, rdx
    jz      .neighbors_done
.neighbor_loop:
    movzx   r9d, byte [rsi + r8]           ; neighbor value
    test    r9d, r9d                        ; skip unassigned
    jz      .next_neighbor
    cmp     eax, r9d                        ; digit == neighbor?
    je      .fail                           ; conflict → immediate fail
.next_neighbor:
    inc     r8
    cmp     r8, rdx
    jb      .neighbor_loop
.neighbors_done:

    ; All constraints passed
    mov     eax, 1
    pop     rbp
    ret

.fail:
    xor     eax, eax
    pop     rbp
    ret
```

**That's ~20 instructions for 4 constraints.** No dispatch overhead. No opcode decode. No stack manipulation. Direct register operations.

### Performance Estimate

| Approach | Cycles/check | Checks/s (3.5 GHz) | Speedup vs Python |
|---|---|---|---|
| Python interpreter | ~55 | 63M | 1x |
| C interpreter (computed goto) | ~0.57 | 6.15B | 98x |
| Direct native (scalar) | ~5-8 | 16-22B | 250-350x |
| Direct native (SIMD batch) | ~0.5-1 | 100-140B | 1600-2200x |

Wait — the C interpreter at 6.15B checks/s suggests ~0.57 cycles per check at 3.5 GHz. That's already very fast, probably batch-processing related. Let me recalibrate.

**More realistic estimates for constraint-to-native:**

The C interpreter's 6.15B is likely measuring simple constraint checks (bit operations) in a tight loop. For a **compiled** version eliminating all dispatch:

- **Eliminate dispatch**: Save ~2-4 cycles per opcode → maybe 2-3x speedup
- **Constraint fusion**: Merge sequential checks → save branch mispredictions
- **SIMD**: Process 8-16 cells simultaneously → 8-16x speedup on top

**Realistic compiled speedup over C interpreter: 3-10x scalar, 30-100x with SIMD.**

---

## 4. x86-64 Instruction Selection for Constraint Operations

### The Constraint Operation → Instruction Mapping

| FLUX Constraint | x86-64 Implementation | Instructions |
|---|---|---|
| Range check: `a ≤ x ≤ b` | `cmp x, a; cmovl fail; cmp x, b; cmovg fail` | 2-4 |
| Range check (branchless) | `sub x, a; cmp x, (b-a); setbe pass` | 3 |
| Bitmask AND | `and mask, value` | 1 |
| Bitmask OR | `or mask, value` | 1 |
| Popcount ≥ N | `popcnt reg, value; cmp reg, N; setge pass` | 3 |
| Domain intersection | `and domain_a, domain_b` | 1 |
| Domain cardinality = N | `popcnt + cmp` | 3 |
| Set membership | `bt bitmap, value` | 1 |
| Uniqueness (2 values) | `cmp a, b; setne pass` | 2 |
| All-different (N values) | Bitmap accumulator: `or` into bitmap, `bt` before | 2N |
| Multiple constraints (branchless) | `cmov` chain, accumulate pass/fail | 1 per + 1 |
| Constraint NOT | `xor result, 1` | 1 |
| Constraint AND | Short-circuit: `test; jz fail` | 2 |
| Constraint OR | Short-circuit: `test; jnz pass` | 2 |

### Branchless Multi-Constraint Pattern

Instead of branching per constraint, use `cmov` chains:

```asm
; Check 4 constraints branchlessly
; rdi = cell pointer, returns eax = pass (1) or fail (0)

    movzx   eax, byte [rdi]           ; value
    xor     ecx, ecx                  ; fail accumulator (0 = pass)
    
    ; C1: value >= 1
    cmp     eax, 1
    adc     ecx, 0                    ; ecx += (value < 1)
    
    ; C2: value <= 9
    cmp     eax, 9
    adc     ecx, 0                    ; ecx += (value > 9) via carry
    
    ; C3: popcount(domain) >= 2
    popcnt  edx, dword [rdi+4]
    cmp     edx, 2
    adc     ecx, 0
    
    ; C4: bit 7 set in flags
    bt      dword [rdi+8], 7
    adc     ecx, 0
    
    ; Result: pass if ecx == 0
    test    ecx, ecx
    sete    al
    ret
```

**4 constraints in ~12 instructions, zero branches.** Modern CPUs can execute this in ~4-6 cycles with instruction-level parallelism.

---

## 5. SIMD Constraint Checking (AVX-512)

### The Big Idea

Process **16 cells simultaneously** using 512-bit registers.

```asm
; AVX-512: Check 16 cells' value >= 1 AND <= 9 simultaneously
; zmm0 = 16 x uint32 cell values (loaded from contiguous array)
; Returns: k1 = bitmask of passing cells

    ; Load 16 cell values
    vmovdqu32   zmm0, [rdi]               ; 16 values in one load
    
    ; Range check: 1 <= value <= 9
    vpsubd      zmm1, zmm0, zmm_const1    ; zmm1 = value - 1
    vpcmpud     k1, zmm1, zmm_const8, 2   ; k1 = (value-1) <= 8 (unsigned)
    
    ; k1 is now a 16-bit mask where bit[i]=1 means cell i passes range check
    ; One more instruction for domain mask check:
    vpandd      zmm2, zmm_domain, zmm_check_mask{k1}{z}  ; masked AND
    vptestmd    k2, zmm2, zmm2            ; k2 = domain non-empty
    
    ; k1 & k2 = cells that pass ALL constraints
    kandw       k1, k1, k2
    kmovw       eax, k1                    ; 16-bit result mask
    ret
```

**16 constraints checked in ~7 instructions, ~4-6 cycles.** That's ~0.3 cycles per constraint check.

### SIMD Domain Intersection

```asm
; Intersect domains of 16 cells with a constraint domain
; zmm0 = 16 cell domain masks
; zmm1 = constraint domain mask (broadcast)
    vpandd  zmm2, zmm0, zmm1          ; intersection
    vptestmd k1, zmm2, zmm2           ; k1 = non-empty intersections
```

### SIMD All-Different Check

```asm
; Check if 16 values are all unique using a bloom filter approach
; zmm0 = 16 values
    vpmulld     zmm1, zmm0, zmm_prime      ; hash: value * prime
    vpxord      zmm2, zmm2, zmm2           ; zero accumulator
    ; Use scatter to detect duplicates (AVX-512 vpscatterdd)
    ; If any scatter collides, a duplicate exists
    vpscatterdd zmm2{k1}, zmm1             ; scatter values as indices
    ; Compare collected vs original to find collisions
```

Actually, all-different is better done with a bitmap approach in scalar code or with specialized algorithms. SIMD shines for **uniform parallel checks** (range, bitmask, domain).

---

## 6. Self-Modifying Code & Runtime Code Generation

### The Challenge

Modern CPUs have instruction caches that are coherent with data caches on x86 (unlike ARM). So self-modifying code works, but:

1. Must flush the instruction cache: `__builtin___clear_cache()` or manually
2. Serialization needed: execute `SFENCE` or similar
3. JIT compilers do this routinely (V8, LuaJIT, JVM)

### FLUX Runtime Code Generation

```c
#include <sys/mman.h>
#include <string.h>

// Allocate executable memory
void* alloc_code_buffer(size_t size) {
    return mmap(NULL, size, 
                PROT_READ | PROT_WRITE | PROT_EXEC,
                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
}

// Compile a constraint to native code
typedef struct {
    uint8_t* code;
    size_t size;
} CompiledConstraint;

// Emit x86-64 machine code directly
void emit_range_check(uint8_t** buf, int offset, int min, int max) {
    // movzx eax, byte [rdi + offset]
    *(*buf)++ = 0x0F; *(*buf)++ = 0xB6; *(*buf)++ = 0x47; *(*buf)++ = offset;
    
    // sub eax, min
    *(*buf)++ = 0x83; *(*buf)++ = 0xE8; *(*buf)++ = min;
    
    // cmp eax, (max - min)
    *(*buf)++ = 0x83; *(*buf)++ = 0xF8; *(*buf)++ = (max - min);
    
    // setbe al
    *(*buf)++ = 0x0F; *(*buf)++ = 0x96; *(*buf)++ = 0xC0;
    
    // ret
    *(*buf)++ = 0xC3;
}
```

### Better: Use a Tiny Assembler

Rather than raw bytes, use a lightweight assembler library (like `asmjit` or a custom 200-line emitter):

```c
// Using a conceptual assembler API
CompiledConstraint compile_flux_guard(GuardSpec* spec) {
    Assembler asm = new_assembler(4096);
    
    emit_prologue(&asm);
    
    for (int i = 0; i < spec->constraint_count; i++) {
        Constraint* c = &spec->constraints[i];
        switch (c->type) {
            case CT_RANGE:
                emit_range_check(&asm, c->field_offset, c->min, c->max);
                break;
            case CT_BITMASK:
                emit_bitmask_check(&asm, c->field_offset, c->mask);
                break;
            case CT_POPCOUNT:
                emit_popcount_check(&asm, c->field_offset, c->threshold);
                break;
            case CT_UNIQUENESS:
                emit_uniqueness_check(&asm, c->field_offsets, c->count);
                break;
        }
        // Accumulate pass/fail
        emit_constraint_accumulate(&asm);
    }
    
    emit_epilogue(&asm);
    return assemble(&asm);
}
```

---

## 7. Compile-Time Constraint Optimization

### Dead Constraint Elimination

If constraint A implies constraint B, eliminate B:
```
C1: x ∈ {1..9}    → implies x ≥ 1
C2: x ≥ 1         → dead (redundant)
```

### Constraint Fusion

Merge adjacent compatible constraints:
```
C1: digit ≥ 1
C2: digit ≤ 9
→ Fused: digit ∈ [1, 9]  → single cmp with unsigned comparison
```

### Strength Reduction

Replace expensive constraints with cheaper equivalents:
```
C1: popcount(domain) > 0   → domain != 0  → test domain, domain (1 insn)
C2: popcount(domain) == 1  → domain & (domain - 1) == 0 (2 insns, no POPCNT)
```

### Constraint Ordering

Order constraints by:
1. **Cheapest first** (bitmask tests before range checks before uniqueness)
2. **Most selective first** (constraints that fail most often go first)
3. **Profile-guided**: collect runtime stats, reorder

### Constant Propagation

If a value is known at compile time (e.g., fixed puzzle structure):
```
; Original: check if cell value is in {1,3,5,7}
; After const prop with value=5:
;   Just check bit 5 of bitmap 0b10101010
bt 0xAA, 5    ; 1 instruction, constant bitmap
```

---

## 8. Concrete Architecture: `fluxc` (FLUX Constraint Compiler)

### Pipeline

```
GUARD Specification
       │
       ▼
  ┌──────────┐
  │  Parser  │  Parse constraint DSL to AST
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ Analyzer │  Type-check, resolve field offsets
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │Optimizer │  Fusion, dead elimination, ordering, strength reduction
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ Selector │  Choose instruction sequence per constraint (scalar/SIMD)
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ Emitter  │  Generate x86-64 machine code (using asmjit or custom)
  └────┬─────┘
       │
       ▼
  Executable Native Code (function pointer callable from C)
```

### Data Structures

```c
// Constraint types (the 50 opcodes map to these primitives)
typedef enum {
    CT_RANGE,       // value in [min, max]
    CT_BITMASK,     // (value & mask) == expected
    CT_SET_MEMBER,  // value in bitmap set
    CT_POPCOUNT_GE, // popcount(value) >= threshold
    CT_POPCOUNT_EQ, // popcount(value) == threshold
    CT_UNIQUE,      // all values in array are unique
    CT_ALL_DIFF,    // value not in neighbor array
    CT_SUM_EQ,      // sum of array == target
    CT_DOMAIN_INTER, // domain intersection non-empty
    CT_CUSTOM,      // fallback: call function pointer
} ConstraintType;

// Compiled constraint = native function
typedef bool (*CheckFn)(const Cell* cell, const Context* ctx);

// Compiled constraint set = array of CheckFn + optional SIMD batch
typedef struct {
    CheckFn*       scalar_checks;    // per-constraint functions
    CheckFn        fused_check;      // all constraints fused into one function
    BatchCheckFn   simd_batch;       // check 16 cells at once (AVX-512)
    int            check_count;
    int            cell_stride;      // bytes between cells
} CompiledConstraintSet;
```

### Handling All 50 Opcodes

The 50 opcodes decompose into ~10 primitive constraint types. The compiler maps each:

| FLUX Opcode Category | Primitive | Native Implementation |
|---|---|---|
| `GUARD_RANGE` | CT_RANGE | `sub + cmp + setbe` (3 insns) |
| `GUARD_BITMASK` | CT_BITMASK | `and + cmp` (2 insns) |
| `GUARD_SET` | CT_SET_MEMBER | `bt` (1 insn) |
| `GUARD_POPCOUNT` | CT_POPCOUNT_GE/EQ | `popcnt + cmp` (3 insns) |
| `GUARD_UNIQUE` | CT_UNIQUE | bitmap accumulator loop |
| `GUARD_ALL_DIFF` | CT_ALL_DIFF | bitmap + scatter |
| `GUARD_SUM` | CT_SUM_EQ | SIMD horizontal add |
| `GUARD_DOMAIN` | CT_DOMAIN_INTER | `and + test` (2 insns) |
| `GUARD_CUSTOM` | CT_CUSTOM | indirect `call` |
| `PUSH/POP/DUP` | (stack ops) | eliminated by register allocation |
| `ADD/SUB/MUL` | (arithmetic) | native `add/sub/imul` |
| `AND/OR/XOR` | (bitwise) | native `and/or/xor` |
| `JMP/JZ/JNZ` | (control flow) | native branches or `cmov` |
| `LOAD/STORE` | (memory) | register-offset `mov` |
| `CALL/RET` | (subroutine) | inlined or native `call/ret` |

**Key insight**: Stack operations (`PUSH`, `POP`, `DUP`, `SWAP`) are **completely eliminated** by the compiler's register allocator. The stack-based VM is a convenient intermediate representation, but the compiled code never touches the stack for these.

---

## 9. Complete Example: Sudoku Row Constraint

### Input (FLUX GUARD specification)

```
GUARD row[0] OF grid[9][9]
  FOR EACH cell c IN row:
    CONSTRAINT c.digit >= 1
    CONSTRAINT c.digit <= 9
    CONSTRAINT c.domain != 0
    ALL_DIFFERENT row[*].digit
```

### Compiled Output (x86-64, scalar path)

```asm
; bool check_sudoku_row(const Cell* row) 
; rdi = pointer to 9-cell array
; Returns: eax = all_valid (1) or invalid (0)

check_sudoku_row:
    ; === Phase 1: Range + domain check (unrolled for 9 cells) ===
    xor     eax, eax                  ; accumulator: 0 = pass
    
    ; Cell 0
    movzx   ecx, byte [rdi + 0*CELL_SIZE + OFF_VALUE]
    sub     ecx, 1
    cmp     ecx, 8                    ; unsigned: value in [1,9]?
    setbe   dl
    cmp     dword [rdi + 0*CELL_SIZE + OFF_DOMAIN], 0
    setne   r9b
    and     dl, r9b                   ; range AND domain ok
    add     al, dl                    ; accumulate violations inverted
    
    ; Cells 1-8: identical pattern, unrolled
    ; ... (repeated 8 more times with different offsets)
    
    ; Quick check: all 9 passed range+domain?
    cmp     al, 9
    jne     .fail
    
    ; === Phase 2: All-different check using bitmap ===
    xor     ecx, ecx                  ; seen bitmap = 0
    xor     eax, eax                  ; index = 0
.diff_loop:
    movzx   edx, byte [rdi + rax*CELL_SIZE + OFF_VALUE]
    bt      ecx, edx                  ; already seen this digit?
    jc      .fail                     ; duplicate!
    bts     ecx, edx                  ; mark as seen
    inc     eax
    cmp     eax, 9
    jb      .diff_loop
    
    mov     eax, 1
    ret

.fail:
    xor     eax, eax
    ret
```

### Compiled Output (AVX-512 batch path)

```asm
; uint16_t check_sudoku_rows_batch(const Cell* rows, int stride, int count)
; Check up to 16 rows simultaneously
; Returns: bitmask of passing rows

check_sudoku_rows_batch_avx512:
    ; Load 16 row pointers
    mov     r8, rdi                    ; base pointer
    xor     eax, eax                   ; result accumulator
    
    ; For each row position (0..8), load 16 values and check all-different
    ; Using AVX-512 vgather to load non-contiguous cell values
    
    ; Load all cell[0] values across 16 rows
    vmovdqu32   zmm0, [rdi]            ; 16 cell values
    vpsubd      zmm1, zmm0, zmm_const1 ; value - 1
    vpcmpud     k1, zmm1, zmm_const8, 2 ; k1 = (value-1) <= 8
    
    ; Domain non-empty check
    vmovdqu32   zmm2, [rdi + OFF_DOMAIN]
    vptestmd    k2, zmm2, zmm2
    kandw       k1, k1, k2
    
    ; ... continue for cells 1-8 with all-different bitmap approach ...
    ; (This is the complex part — see SIMD all-different note below)
    
    kmovw       eax, k1
    ret
```

**SIMD all-different is the hard case.** For Sudoku specifically, you can use a histogram approach:
1. For each of 9 digit values, count occurrences across 16 rows
2. Each count must be ≤ 1
3. Use `vpcmpud` + `kord` to verify

---

## 10. Performance Roadmap

### Phase 1: Direct Threaded Code (Easy, 2-3x over current C)
- Replace opcode dispatch with computed goto (may already be done)
- Inline common constraint patterns

### Phase 2: Subroutine Threading (Medium, 3-5x)
- Each opcode compiles to a real function call
- Eliminates dispatch loop entirely
- Still has CALL/RET overhead per opcode

### Phase 3: Constraint Fusion Compiler (Hard, 5-15x)
- Compile multiple constraints into single native functions
- Register allocation across constraints
- Branchless multi-constraint patterns
- Dead constraint elimination

### Phase 4: SIMD Batch Compiler (Expert, 20-100x)
- AVX-2 (256-bit): 8 cells at once
- AVX-512 (512-bit): 16 cells at once
- Auto-vectorization of constraint checks
- Gathers/scatters for non-contiguous access

### Phase 5: Profile-Guided Optimization (Expert, +20-50% on top)
- Collect runtime constraint statistics
- Reorder constraints by selectivity
- Specialize hot paths

---

## 11. Implementation Recommendation

### Use `asmjit` as the code emitter

[`asmjit`](https://github.com/asmjit/asmjit) is a lightweight C++ library for runtime x86/x64 code generation. It handles:
- Instruction encoding
- Register allocation (basic)
- Label/branch resolution
- Relocations

### Architecture

```
flux_constraint_compiler/
├── src/
│   ├── parser.rs          # Parse GUARD DSL to AST
│   ├── analyzer.rs        # Type check, resolve offsets
│   ├── optimizer.rs       # Fusion, dead elimination, ordering
│   ├── selector.rs        # Choose instruction sequences
│   ├── emitter.rs         # Generate machine code via asmjit
│   ├── simd_emitter.rs    # AVX-2/AVX-512 batch compilation
│   └── runtime.rs         # Executable memory management, cache flushing
├── tests/
│   └── ...
└── Cargo.toml
```

**Language: Rust** — matches FLUX's existing stack, gives us control over code generation, and asmjit can be called via FFI (or we use `cranelift` as a pure-Rust alternative).

Actually, **`cranelift`** might be better than asmjit for Rust:
- Pure Rust, no FFI
- Production-quality (used by Wasmtime)
- Good register allocator
- Supports x86-64 + AArch64

### Minimal Viable Compiler

The MVP compiles a single GUARD constraint to a native function pointer:

```rust
fn main() {
    let spec = parse_guard("digit >= 1 AND digit <= 9 AND popcount(domain) >= 1");
    let compiled = Compiler::new().compile(&spec);
    
    let cell = Cell { value: 5, domain: 0x1FF };
    let pass = compiled.check(&cell);  // calls native code
    assert!(pass);
}
```

---

## Summary

| Technique | Speedup over C interpreter | Complexity | Recommendation |
|---|---|---|---|
| Computed goto (direct threading) | 1x (already done) | Low | ✅ Done |
| Subroutine threading | 1.5-2x | Low | Quick win |
| Constraint fusion | 3-5x | Medium | ✅ Do first |
| Branchless multi-constraint | 2-3x | Medium | Do with fusion |
| SIMD AVX-2 batch | 8-16x | High | Phase 2 |
| SIMD AVX-512 batch | 16-32x | High | Phase 2 (with CPU check) |
| Profile-guided reorder | +20-50% | Medium | Phase 3 |
| **Combined (fusion + SIMD + PGO)** | **20-50x over C** | High | Full vision |

**The compiler eliminates the interpreter entirely.** Constraints become native functions. The VM's 50 opcodes become ~10 primitive operations that map 1:1 to x86-64 instructions. Stack overhead disappears. Dispatch disappears. The constraint IS the code.
