# Retro Console Assembly Optimization → FLUX Constraint Checking

## Research Report: Classic Video Game Console Techniques and Their Direct Application to FLUX

---

## 1. Atari 2600 (6507 CPU, 128 bytes RAM, 4KB ROM)

### Hardware Constraints
- **CPU:** 6507 @ 1.19 MHz (crippled 6502 — only 13 address lines, 8KB address space)
- **RAM:** 128 bytes (TIA registers + RIOT RAM). No video RAM. No frame buffer.
- **Video:** TIA chip generates video signal in real-time. CPU must write to TIA registers synchronized to the CRT electron beam.
- **Bus:** CPU and TIA share the bus; CPU halts during some TIA operations.

### Optimization Techniques

#### Race the Beam (Cycle-Counted Kernel)
The 2600 has **no frame buffer**. The CPU writes directly to TIA video registers as the CRT electron gun scans across the screen. You have exactly **76 CPU cycles per scanline** (228 color clocks / 3). The entire display kernel is a precisely cycle-counted loop:

```asm
; Classic 2600 display kernel (simplified)
; Each iteration must be EXACTLY 76 cycles
KernelLoop:
    sta WSYNC       ; 3 cycles — wait for horizontal blank (sync to beam)
    lda #$44        ; 2 cycles — background color
    sta COLUBK      ; 3 cycles — set it
    
    ; Draw playfield — must hit GRP0/GRP1 before beam passes
    ldx Player0Y    ; 3 cycles
    lda SpriteData,x ; 4 cycles
    sta GRP0        ; 3 cycles — player 0 graphics register
    
    ldx Player1Y    ; 3 cycles  
    lda SpriteData,x ; 4 cycles
    sta GRP1        ; 3 cycles — player 1 graphics register
    
    ; Playfield (background tiles) — asymmetric screen trick
    lda PFDataL,X   ; 4 cycles
    sta PF0         ; 3 cycles — left side playfield
    sta PF1         ; 3 cycles
    sta PF2         ; 3 cycles
    
    ; WSYNC already fired — 76 cycles total
    ; If you're over by 1 cycle, the beam has passed and you drew garbage
```

The key insight: **every instruction's cycle count is known at assemble-time**. Branch timing is handled by ensuring both taken/not-taken paths are equal length (padding with NOPs).

#### 128-Byte Memory Subdivision
```
$80-$9C: Variables (game state — 29 bytes)
$9D-$A5: Stack (grows down from $FF — shares with variables!)  
$A6-$B3: Display buffer (split into 2-line kernel sections — 14 bytes)
$B4-$FF: More variables, indirect pointer tables
```

Developers used **self-modifying code** to save bytes:
```asm
; Instead of a table lookup (which costs bytes for the table):
lda SpriteData,X   ; 4 bytes (2 for opcode, 2 for address)

; Use self-modifying code:
PatchPoint:
    lda #$00         ; 2 bytes — patch the immediate value at runtime
    ; To change sprite: lda NewVal / sta PatchPoint+1
```

#### Vertical Blank Strategy
The 2600 has ~37 scanlines of vertical blank (VBLANK) where no display happens. This is where all game logic runs — collision detection, AI, physics. At 76 cycles/line × 37 lines = **2,812 cycles for the entire game logic frame**.

### FLUX Analogy

| 2600 Technique | FLUX Application |
|---|---|
| Cycle-counted kernel (76 cycles/line) | **Constraint evaluation must fit in cache-line boundaries.** Each constraint check = one "scanline." If a constraint batch overflows L1 cache line (64 bytes), you've "missed the beam" and stall. |
| No frame buffer (real-time generation) | **No intermediate constraint storage.** Evaluate constraints directly into the result register, streaming through like the TIA. Don't build a constraint result tree — emit results inline. |
| Self-modifying code for data embedding | **Patch constraint bytecode at JIT time.** Embed constants directly into the instruction stream rather than loading from separate data. AVX-512 `vpbroadcastd` from an immediate rather than a memory load. |
| VBLANK game logic window | **Constraint evaluation budget = branch prediction window.** All constraint logic must complete before the CPU pipeline flushes. Structure constraint batches to fit in the branch predictor's window (~4K branches on modern x86). |
| 128-byte state with stack sharing | **Constraint VM state ≤ 128 bytes.** The entire constraint evaluation context (program counter, domain bounds, violation accumulator) must fit in a single cache line. Zero indirection. |

---

## 2. TurboGrafx-16 / PC Engine (HuC6280 CPU)

### Hardware Constraints
- **CPU:** HuC6280 @ 1.79/7.16 MHz (custom 6502 derivative)
- **RAM:** 8KB main + 64KB VRAM
- **Video:** Custom VDC (Video Display Controller) with hardware scrolling, sprites
- **Key feature:** Hardware bit manipulation instructions not on stock 6502

### Optimization Techniques

#### HuC6280 Bit Manipulation Instructions
The HuC6280 adds specialized bit instructions to the 6502 ISA:

```asm
; HuC6280-specific bit manipulation
BBRn branch  ; Branch if Bit Reset (n = 0-7)
BBSn branch  ; Branch if Bit Set (n = 0-7)
RMBn addr    ; Reset Memory Bit n
SMBn addr    ; Set Memory Bit n

; Example: sprite collision checking via bit flags
; Each sprite gets a byte where bits = collision flags
    BBS3 SpriteFlags, HitHandler  ; If bit 3 set (collision with player)
    BBS5 SpriteFlags, PowerUpHandler ; If bit 5 set (collected powerup)
    RMB3 SpriteFlags              ; Clear collision flag
    SMB7 SpriteFlags              ; Set "processed" flag
```

This is essentially **hardware-accelerated flag checking** — each sprite's state is a bitmask, and the CPU can branch on individual bits in a single instruction.

#### SAT (Sprite Attribute Table) DMA
The VDC has a dedicated DMA channel that copies the sprite attribute table from main RAM to VRAM during vertical blank. Developers would build the SAT in RAM, then trigger a single DMA transfer:

```asm
; Set up SAT DMA transfer
    lda #$00
    sta $0402       ; VDC register — SATB (sprite attribute table base)
    lda #$7F
    sta $0403       ; High byte of SAT address
    ; DMA auto-triggers on next VBLANK — 64 sprites in one shot
```

### FLUX Analogy

| TG-16 Technique | FLUX Application |
|---|---|
| BBR/BBS single-instruction bit test+branch | **BitmaskDomain native operations.** Constraint domain membership = bit test. `test` + `jz` on x86 maps directly. AVX-512 `vptestmb` does 64 byte-level bit tests in one instruction. |
| RMB/SMB atomic bit set/clear | **Constraint flag management.** When a constraint fires, set/clear violation flags in a bitmask. AVX-512 `vpandd`/`vpord` for bulk flag operations. |
| SAT DMA bulk transfer | **Constraint batch DMA.** Move entire constraint input sets via DMA to GPU memory in one transfer. Don't send constraints one at a time — batch them into a table and DMA the whole thing. |
| Hardware scrolling with wrap-around | **Circular constraint buffer.** Wrap-around domain checking. The VDC handles wrap-around for scrolling seamlessly — constraint domains with cyclic topology (angles, periodic functions) need the same zero-overhead modular arithmetic. |

---

## 3. Sega Genesis / Mega Drive (68000 + Z80)

### Hardware Constraints
- **Main CPU:** Motorola 68000 @ 7.67 MHz (32-bit registers, 16-bit bus)
- **Audio CPU:** Z80 @ 3.58 MHz (8-bit)
- **RAM:** 64KB main + 8KB Z80 + 64KB VRAM
- **Shared memory:** Z80 can access 68000 bus through a bank-switched window
- **Bus arbitration:** Only one CPU can access the bus at a time

### Optimization Techniques

#### Dual-CPU Coordination via Shared Memory Mailbox
```asm
; === 68000 side (game logic) ===
; Write command to shared RAM for Z80 audio
    lea     $A00000,a0      ; Z80 shared RAM window
    move.b  #$01,(a0)       ; Command: play BGM track 1
    move.b  #$FF,$A11100    ; Signal Z80: new command ready
    
; === Z80 side (audio) ===
    ld      hl,$A00000      ; Read command from 68000
    ld      a,(hl)
    cp      #$01
    jp      z,PlayBGM       ; Execute audio command
    
; Done processing
    xor     a
    ld      ($A00000),a     ; Clear command (acknowledge)
```

The critical trick: **the 68000 halts the Z80 when it needs bus access, and vice versa.** The bus request/bus acknowledge protocol (`/BR`, `/BG` pins) ensures mutual exclusion. Games minimized bus contention by:
1. Having the Z80 do all audio processing from its own 8KB RAM
2. Only accessing the 68000 bus during vertical blank
3. Double-buffering: Z80 reads from buffer A while 68000 writes to buffer B, then swap

#### 68000 Instruction Scheduling for Bus Efficiency
The 68000 has a multi-cycle instruction pipeline. The key optimization was **interleaving ALU operations with memory accesses** to hide latency:

```asm
; Bad: sequential, stalls on each memory access
    move.w  (a0)+,d0    ; 4 cycles — wait for memory
    add.w   d0,d1       ; 2 cycles  
    move.w  (a0)+,d2    ; 4 cycles — wait for memory
    add.w   d2,d3       ; 2 cycles

; Better: interleave to hide latency
    move.w  (a0)+,d0    ; 4 cycles — start memory read
    move.w  (a0)+,d2    ; 4 cycles — pipelined (overlapped with d0 read)
    add.w   d0,d1       ; 2 cycles — d0 is ready
    add.w   d2,d3       ; 2 cycles — d2 is ready
```

### FLUX Analogy

| Genesis Technique | FLUX Application |
|---|---|
| 68000+Z80 shared memory mailbox | **CPU+GPU constraint coordination.** CPU writes constraint commands to a shared memory mailbox; GPU reads and evaluates. Double-buffer to avoid stalls. |
| Bus arbitration (mutual exclusion) | **Memory bus contention between CPU constraint checking and GPU tensor evaluation.** Use memory fences and atomic flags. CPU checks `gpu_done` flag before writing new constraints. |
| Z80 self-contained in local RAM | **GPU kernel uses only local/shared memory.** Don't go to global memory during constraint evaluation. Load the constraint set into shared memory once, evaluate entirely within the SM. |
| Interleaved instruction scheduling | **Software pipelining for AVX-512 constraint loops.** Issue the next `vmovdqa32` load before processing the current batch. Use `_mm512_prefetch_i32ext` to pipeline memory accesses with ALU constraint evaluation. |
| Bank-switched Z80 window | **Memory-mapped I/O for constraint streaming.** Map different constraint domains into different address ranges. Switch "banks" to change which constraint set the GPU sees. |

---

## 4. Neo Geo (68000 + Custom Chipset)

### Hardware Constraints
- **CPU:** 68000 @ 12 MHz
- **RAM:** 64KB main + 2KB Z80 audio
- **Video:** Custom LSPC (Line Sprite Controller) + B1 chip
- **Cartridge:** Up to 330MB (via bank switching) — no size limit on sprites/tiles
- **Key innovation:** Hardware sprite engine with per-sprite attributes including position, size, and palette — all handled by the chipset

### Optimization Techniques

#### Hardware Constraint Solver: The Sprite System
The Neo Geo's LSPC chip is essentially a **hardware constraint satisfaction engine** for sprite rendering:

- Each sprite has fixed attributes: Y position, X position, tile index, palette, size (16×16 to 16×512)
- The hardware automatically: clips sprites to screen bounds, handles priority ordering, applies per-sprite palettes, performs per-tile animation (no manual frame updating)
- **The cartridge ROM IS the video memory.** The LSPC reads tile data directly from cartridge — no DMA, no VRAM copy. The address space is unified.

```asm
; Neo Geo sprite setup — writing to hardware registers
; The hardware solves all rendering constraints automatically
    move.w  #$0010,$800000   ; Sprite 0: Y position = 16
    move.w  #$0020,$800002   ; Sprite 0: X position = 32
    move.w  #$0001,$800004   ; Sprite 0: Tile = 1
    move.w  #$0100,$800006   ; Sprite 0: Palette 1, no flip
    
    ; That's it. Hardware handles:
    ; - Clipping to screen bounds
    ; - Priority vs other sprites
    ; - Palette application
    ; - Tile fetch from ROM
    ; - Scanline-accurate positioning
```

#### Fix Layer + Sprite Layer Separation
The Neo Geo has a "fix" layer (static tilemap for UI/text) and a sprite layer (everything else). The fix layer is tiny (40×28 tiles) and always rendered. This separation means:
- Game logic only updates sprites that changed
- Fix layer is write-once (status bar, score, etc.)
- The hardware composites both layers automatically

### FLUX Analogy

| Neo Geo Technique | FLUX Application |
|---|---|
| Hardware sprite constraint solver | **Constraint satisfaction in silicon.** Move constraint checking to fixed-function hardware. The tensor cores evaluate constraint matrices the way the LSPC evaluates sprite attributes — write the parameters, get the result, no software involved. |
| ROM = VRAM (unified address space) | **Constraint program = data.** Don't copy constraint programs to GPU memory — memory-map them. Use unified memory (CUDA Managed Memory or OpenCL SVM) so the GPU reads constraints directly from host memory. |
| Per-sprite attribute descriptors | **Constraint descriptor format.** Each constraint is a descriptor with: domain type, parameters, priority, evaluation mode. Hardware (or GPU kernel) reads descriptors and evaluates automatically. |
| Fix layer (static, write-once) | **Immutable constraint partition.** Separate constraints into "fix" (compile-time known, never change — e.g., type bounds) and "sprite" (runtime dynamic). Only re-evaluate the dynamic set. Cache the fix layer results permanently. |

---

## 5. SNES (5A22 CPU + Custom Chips)

### Hardware Constraints
- **CPU:** Ricoh 5A22 @ 1.79/2.68/3.58 MHz (65C816 derivative)
- **RAM:** 128KB + various cartridge coprocessor RAM
- **Video:** S-PPU1 + S-PPU2 (two picture processing units)
- **Coprocessors:** Super FX, SA-1, DSP-1, S-DD1, etc. (in cartridge)

### Optimization Techniques

#### Mode 7: Hardware Affine Transform
Mode 7 turns the background layer into a 1024×1024 texture-mapped plane using a 2×2 affine transformation matrix:

```asm
; Mode 7 matrix registers (write-only, auto-transform)
; Matrix: [A B]   Registers: M7A, M7B, M7C, M7D
;         [C D]
    lda #$0100     ; A = 1.0 (scale X)
    sta $211B      ; M7A
    lda #$0000     ; B = 0.0 (no shear X)  
    sta $211C      ; M7B
    lda #$0000     ; C = 0.0 (no shear Y)
    sta $211D      ; M7C
    lda #$0100     ; D = 1.0 (scale Y)
    sta $211E      ; M7D

; Center of rotation
    lda ScreenCenterX
    sta $2121      ; M7X
    lda ScreenCenterY
    sta $2122      ; M7Y

; The hardware applies the matrix to EVERY PIXEL in the layer
; at scanline speed. No CPU involvement per-pixel.
```

To do a rotation:
```
A = cos(θ) * scale
B = sin(θ) * scale  
C = -sin(θ) * scale
D = cos(θ) * scale
```

The CPU only writes 6 registers (4 matrix + 2 center). The PPU does billions of multiply-accumulates per frame.

#### Super FX: Cartridge Coprocessor
The Super FX chip (used in Star Fox, Yoshi's Island) was a RISC coprocessor on the cartridge that ran at ~10.5 MHz. It had:
- 16-bit multiplier (single cycle)
- Pixel plot instructions
- Dedicated framebuffer RAM

The 5A22 would set up the scene parameters, the Super FX would render the 3D, and DMA would copy the result to PPU VRAM.

#### SA-1: Second 65C816 CPU
The SA-1 was literally a second SNES CPU on the cartridge running at 10.74 MHz (3× the main CPU speed). Coordination:

```asm
; SA-1 code (running on cartridge coprocessor)
; Main CPU writes commands to a shared register area
; SA-1 reads them, processes, writes results back

CheckCommand:
    lda $3100       ; Command register (shared with main CPU)
    cmp #$01
    bne CheckCommand
    ; Process command...
    lda Result
    sta $3102       ; Result register
    lda #$00
    sta $3100       ; Clear command (acknowledge)
    bra CheckCommand
```

### FLUX Analogy: Three-Tier Architecture

| SNES Component | FLUX Tier |
|---|---|
| **5A22 CPU** (slow, general-purpose) | **ARM Safety Island** — slow but trusted. Handles safety-critical constraint evaluation that must be auditable. |
| **Super FX / SA-1** (fast coprocessor) | **AVX-512** — fast, general compute. Handles bulk constraint evaluation with SIMD parallelism. |
| **Mode 7 PPU** (fixed-function matrix hardware) | **CUDA Tensor Cores** — fixed-function matrix multiply. Evaluates constraint matrices in hardware. |
| DMA between tiers | **Async constraint streaming** between ARM → AVX-512 → Tensor Cores. Each tier processes constraints at its natural speed. |

**Key insight:** The SNES didn't make the main CPU faster — it **offloaded specific workloads to specialized hardware.** The 5A22 couldn't do Mode 7 math per-pixel, so it wrote 6 registers and let the PPU do it. Similarly, the ARM Safety Island shouldn't evaluate tensor constraints — write the parameters and let the tensor cores do it.

---

## 6. Nintendo 64 (MIPS R4300i + RCP)

### Hardware Constraints
- **CPU:** MIPS R4300i @ 93.75 MHz (64-bit, in-order, 5-stage pipeline)
- **RCP:** Reality Coprocessor @ 62.5 MHz (RSP + RDP)
  - **RSP:** Reality Signal Processor — programmable vector unit (128-bit SIMD, 8 vector registers × 8 elements)
  - **RDP:** Reality Display Processor — fixed-function rasterizer
- **RAM:** 4MB RDRAM (8MB with Expansion Pak), unified memory
- **Cartridge:** 32-64MB ROM (high bandwidth, ~5MB/s, but no seek latency)
- **Bus:** 32-bit, shared between CPU and RCP

### Optimization Techniques

#### RSP Microcode Optimization
The RSP is the N64's secret weapon. It's a **programmable vector processor** with its own instruction memory (4KB IMEM) and data memory (4KB DMEM). Developers write microcode (µcode) that runs on the RSP:

```asm
; RSP vector operation (VU assembly)
; Process 8 vertices in parallel using 128-bit vectors
; Each vector register holds 8 × 16-bit values

    lqv     v0, 0x00(t0)        ; Load 8 X coordinates (128 bits)
    lqv     v1, 0x10(t0)        ; Load 8 Y coordinates
    lqv     v2, 0x20(t0)        ; Load 8 Z coordinates
    
    ; Matrix multiply: position × model-view-projection matrix
    vmudn   v3, v0, v20[0]      ; v3 = X * M00 (multiply-add sequence)
    vmadh   v4, v0, v20[1]      ; v4 = X * M01
    vmadh   v5, v0, v20[2]      ; v5 = X * M02
    vadd    v3, v3, v4           ; accumulate
    vadd    v3, v3, v5           ; v3 = transformed X for all 8 vertices
    
    ; Perspective divide (clip check built into sequence)
    vrcp    v6, v3[0]           ; Reciprocal of Z for perspective
    vmudn   v7, v0, v6          ; Perspective-corrected X
    
    ; Write results
    sqv     v7, 0x00(t1)        ; Store transformed coordinates
```

**Factor 5's trick (Rogue Squadron):** They wrote custom RSP microcode that replaced Nintendo's default "Fast3D" µcode with a stripped-down version:
- Removed lighting calculations (did them manually with more control)
- Removed matrix stack (managed their own)
- Freed up ~30% of RSP instruction memory for more vertex processing
- Result: 2-3× more polygons than games using standard µcode

**Rare's trick (Banjo-Kazooie, Perfect Dark):** Used the RSP for audio mixing in addition to graphics — time-sliced between audio and graphics processing within a single frame.

#### RDP Command Buffer
The RDP reads a display list from RDRAM. Each command is a 64-bit or 128-bit word:

```
; RDP triangle command (simplified)
; Bits: [63:56] = opcode, [55:48] = level of detail, [47:0] = coordinates
0x08000000_00100020_00200040  ; Triangle: (16,32) → (32,64) → (48,96)
```

The RDP processes these asynchronously. The CPU/RSP can write commands while the RDP is rendering the previous ones.

#### Cache Management on R4300i
The R4300i has a 16KB direct-mapped L1 cache. The critical optimization was **manually managing cache lines**:

```asm
; Cache-line-aligned data layout for R4300i
.align 16                ; Align to cache line
VertexData:
    .half 100, 200, 300  ; X, Y, Z
    .half 101, 201, 301  ; Next vertex (same cache line!)
    .half 102, 202, 302  ; Next vertex (same cache line!)
    .half 103, 203, 303  ; 4 vertices per 32-byte cache line
    
; Prefetch for processing loop
    lw      t0, 0(a0)    ; Load first vertex — cache miss
    lw      t1, 4(a0)    ; Cache hit (same line)
    lw      t2, 8(a0)    ; Cache hit
    lw      t3, 12(a0)   ; Cache hit
```

### FLUX Analogy

| N64 Technique | FLUX Application |
|---|---|
| Custom RSP microcode for specific workloads | **Custom GPU kernels per constraint type.** Don't use a generic "evaluate all constraints" kernel. Write specialized kernels for BitmaskDomain, IntervalDomain, SymbolicDomain — each optimized like custom µcode. Strip unnecessary features from each kernel. |
| RSP 4KB IMEM constraint | **Constraint kernel must fit in GPU instruction cache.** The RSP had 4KB of instruction memory. Modern GPU instruction caches are ~16-32KB. Constraint evaluation kernels must be small and tight. |
| RSP 4KB DMEM for working data | **Constraint working set must fit in GPU shared memory.** 4KB DMEM → 48KB CUDA shared memory. The entire constraint evaluation state must fit in shared memory. |
| RDP command buffer (async processing) | **Async constraint evaluation pipeline.** CPU writes constraint commands to a buffer, GPU processes them asynchronously. Double- or triple-buffer the command stream. |
| Factor 5 stripped µcode | **Minimal constraint kernels.** Remove everything from the constraint kernel that isn't needed for the specific domain type. No branches for "maybe this constraint is symbolic." Specialize ruthlessly. |
| Rare's time-sliced RSP (audio+graphics) | **Time-slicing GPU between constraint types.** If GPU is underutilized by one constraint type, schedule another type in the same frame. Batch BitmaskDomain constraints into the first half of GPU time, IntervalDomain into the second half. |
| Cache-line-aligned vertex data | **Cache-line-aligned constraint descriptors.** Pack constraint parameters into cache-line-sized (64-byte) blocks. Process constraints sequentially through cache lines to maximize L1 hit rate. |

---

## 7. Cross-Cutting Techniques

### Scanline Racing → Cache-Line Racing

**Console technique:** The CRT electron beam scans from left to right, top to bottom. Atari 2600 developers would write to TIA registers timed to the beam's position. If you wrote too late, the pixel was already on screen.

**FLUX application:** Modern CPUs don't have electron beams, but they have **cache lines** (64 bytes). Data is fetched from memory in cache-line granularity. Constraint checking should be **raced to the cache line** — evaluate constraints in the order they arrive in cache, not in logical order:

```c
// Bad: random access pattern (cache miss per constraint)
for (int i = 0; i < N; i++) {
    result[i] = check_constraint(constraints[indices[i]]); // Random access!
}

// Good: stream through cache lines sequentially
// Layout constraints in memory in evaluation order
for (int i = 0; i < N; i++) {
    result[i] = check_constraint(constraints[i]); // Sequential — cache-line racing
}
```

Advanced: Use `__builtin_prefetch` or `_mm_prefetch` to "race ahead" of the cache line:
```c
// Prefetch next cache line while processing current
for (int i = 0; i < N; i += 8) {
    _mm_prefetch(&constraints[i + 64], _MM_HINT_T0); // Fetch 64 items ahead
    // Process constraints[i..i+7] — already in L1
    __m512 vals = _mm512_loadu_ps(&constraints[i].value);
    __m512 lo   = _mm512_loadu_ps(&constraints[i].lower_bound);
    __m512 mask = _mm512_cmplt_ps_mask(vals, lo);
    // Store violations
}
```

### Sprite Multiplexing → Register Multiplexing

**Console technique:** The C64, Atari 2600, and others had a fixed number of hardware sprites (8 on C64, 2 on 2600). To show more sprites, developers would **reposition sprites mid-frame** by writing new Y coordinates during horizontal blank:

```asm
; C64 sprite multiplexing
; Show 8 sprites, then reposition them for the next "band"
    ; First band (scanlines 0-50): sprites at Y=20
    lda #20
    sta $D001   ; Sprite 0 Y position
    ; ... wait for beam to pass band 1 ...
    
    ; Second band (scanlines 51-100): reposition same sprites
    lda #60
    sta $D001   ; Sprite 0 Y position (reused!)
    ; Same hardware sprite, different position = multiplexed
```

**FLUX application:** AVX-512 has 32 × 512-bit registers (ZMM0-ZMM31). That's 32 registers to hold constraint data. For large constraint sets, **multiplex the registers** by processing in bands:

```c
// Band 1: Load constraints 0-31 into ZMM0-ZMM31
__m512 vals_band1[32];
for (int r = 0; r < 32; r++) {
    vals_band1[r] = _mm512_load_ps(&constraints[r * 16].value);
}
// Evaluate all 32 × 16 = 512 constraints

// Band 2: Reuse ZMM0-ZMM31 for next batch
for (int r = 0; r < 32; r++) {
    vals_band1[r] = _mm512_load_ps(&constraints[(r + 32) * 16].value);
}
// Same registers, new data = multiplexed
```

### Mode 7 Matrix Tricks → Tensor Core Constraint Evaluation

**Console technique:** Mode 7 applies a 2×2 affine matrix to every pixel of a background layer. The transformation: `screen_pos = matrix × texture_pos`. The hardware does this at pixel-clock speed (~5.37 MHz pixel rate).

**FLUX application:** Constraint checking can often be expressed as matrix operations:
- **Type bounds checking:** `violation = max(0, bounds_matrix × values - limits)`
- **Domain intersection:** `intersection = A ∩ B` where A and B are interval matrices
- **Constraint propagation:** `new_domains = propagate(constraints, domains)` — a sparse matrix multiply

```python
# Conceptual: tensor core constraint evaluation
# bounds_matrix: [N_constraints, N_variables]
# values: [N_variables, 1]
# violations = bounds_matrix @ values — single tensor core operation

import torch
violations = torch.matmul(bounds_matrix, values)  # Tensor cores evaluate ALL constraints
violation_mask = violations > thresholds           # Which constraints are violated?
```

The key insight: **batch constraint evaluation into matrix form** and let the tensor cores evaluate the entire batch in one operation, just like Mode 7 evaluates the entire background layer in one scan.

### Bank Switching → Constraint Program Streaming

**Console technique:** NES, SMS, TG-16, Genesis — all used bank switching to address more ROM than the CPU's address space allowed:

```asm
; NES MMC3 bank switching
    lda #$06            ; Select bank register 6 (program bank)
    sta $8000           ; Bank register select
    lda #$0F            ; Bank 15
    sta $8001           ; Switch in bank 15 at $C000-$FFFF
    ; Now code at $C000+ comes from ROM bank 15
    ; Previous bank is swapped out but still in ROM
```

**FLUX application:** When constraint programs don't fit in L1/L2 cache, use **bank switching** — stream in constraint pages on demand:

```c
// Constraint program bank switching
#define CONSTRAINT_PAGE_SIZE (4 * 1024)  // 4KB = L1 cache line set

typedef struct {
    uint32_t page_id;
    constraint_t constraints[CONSTRAINT_PAGE_SIZE / sizeof(constraint_t)];
} constraint_page_t;

// Bank-switch constraint pages through L2 cache
void evaluate_large_constraint_set(constraint_page_t *pages, int n_pages) {
    for (int p = 0; p < n_pages; p++) {
        // "Switch in" this page — prefetch to L2
        _mm_prefetch(pages[p].constraints, _MM_HINT_T1);
        
        // Evaluate while next page loads
        evaluate_constraints(pages[p].constraints, ...);
        
        // Page is "switched out" — cache naturally evicts it
    }
}
```

### PAL/NTSC Timing → Adaptive Constraint Budget

**Console technique:** NTSC runs at 60fps (525 lines), PAL at 50fps (625 lines). PAL has more scanlines per frame = more VBLANK time for game logic. Some games used different strategies per region:

- NTSC: Optimize for speed (less time per frame)
- PAL: Use extra VBLANK time for additional logic/features

**FLUX application:** Adapt constraint checking depth to available compute budget:

```c
typedef enum {
    BUDGET_MINIMAL,    // "NTSC mode" — tight budget, only critical constraints
    BUDGET_NORMAL,     // Normal operation
    BUDGET_EXTENDED    // "PAL mode" — extra budget, deeper analysis
} evaluation_budget_t;

void evaluate_with_budget(constraint_set_t *cs, evaluation_budget_t budget) {
    switch (budget) {
        case BUDGET_MINIMAL:
            // Only BitmaskDomain checks (fastest)
            evaluate_bitmask_constraints(cs->bitmask_set);
            break;
        case BUDGET_NORMAL:
            // Bitmask + IntervalDomain
            evaluate_bitmask_constraints(cs->bitmask_set);
            evaluate_interval_constraints(cs->interval_set);
            break;
        case BUDGET_EXTENDED:
            // All domains including symbolic
            evaluate_bitmask_constraints(cs->bitmask_set);
            evaluate_interval_constraints(cs->interval_set);
            evaluate_symbolic_constraints(cs->symbolic_set);
            break;
    }
}
```

### Audio DMA Tricks → Async Constraint Input Streaming

**Console technique:** The Genesis Z80 could use its DMA channel (intended for PCM audio) to copy arbitrary data. The Amiga famously used its blitter (intended for graphics) to copy audio samples. The principle: **repurpose dedicated DMA channels for general data movement.**

**FLUX application:** Use GPU copy engines (DMA) to stream constraint data while the GPU SMs are busy evaluating the previous batch:

```c
// CUDA streams for async constraint DMA
cudaStream_t eval_stream, copy_stream;
cudaStreamCreate(&eval_stream);
cudaStreamCreate(&copy_stream);

// Triple-buffered constraint evaluation
for (int batch = 0; batch < n_batches; batch += 3) {
    // Stream in batch+2 while evaluating batch and copying results for batch-1
    cudaMemcpyAsync(d_constraints[2], h_constraints[batch+2], size,
                    cudaMemcpyHostToDevice, copy_stream);
    
    // Evaluate batch on GPU (different stream)
    evaluate_constraints<<<grid, block, 0, eval_stream>>>(
        d_constraints[0], d_results[0]);
    
    // Copy results from batch-1 back to host
    cudaMemcpyAsync(h_results[batch-1], d_results[0], result_size,
                    cudaMemcpyDeviceToHost, copy_stream);
    
    // Rotate buffers
    rotate_buffers();
}
```

---

## 8. Master Mapping Table: Console Technique → FLUX Optimization

| Console | Technique | Constraint | Optimization | FLUX Optimization |
|---|---|---|---|---|
| **Atari 2600** | Cycle-counted kernel | 76 cycles/scanline | Every instruction timed | Constraint evaluation must fit in L1 cache-line boundaries (64 bytes, ~20 cycles) |
| **Atari 2600** | No frame buffer | Zero intermediate storage | Stream results directly to TIA | Stream constraint results directly to output — no intermediate AST or result tree |
| **Atari 2600** | Self-modifying code | 128 bytes RAM | Patch instructions with data | JIT-patch constraint bytecode with immediate values; embed constants in instruction stream |
| **Atari 2600** | VBLANK logic window | 2,812 cycles for game logic | All logic in vertical blank | Constraint evaluation budget = predictable time slice; all checking within branch predictor window |
| **TG-16** | BBR/BBS bit test+branch | Hardware bit manipulation | Single instruction flag check | `vptestmb`/`vptestmd` — 64 bit tests in one AVX-512 instruction for BitmaskDomain |
| **TG-16** | SAT DMA bulk transfer | Move 64 sprites in one DMA | Batch transfer during VBLANK | DMA entire constraint input sets to GPU in one transfer; no per-constraint copies |
| **Genesis** | 68000+Z80 mailbox | Shared bus, mutual exclusion | Double-buffered command queue | CPU+GPU mailbox with double buffering; CPU writes constraints while GPU evaluates previous batch |
| **Genesis** | Instruction interleaving | 68000 pipeline stalls | Overlap loads with ALU ops | Software-pipeline AVX-512 constraint loops; prefetch next batch while evaluating current |
| **Neo Geo** | Hardware sprite solver | Fixed-function rendering | Write params, get result | Tensor core constraint evaluation — write constraint matrix, hardware evaluates |
| **Neo Geo** | ROM = VRAM | Unified address space | No copy needed | CUDA Unified Memory for constraint data; GPU reads directly from host allocation |
| **Neo Geo** | Fix/sprite layer split | Static vs dynamic content | Only update what changed | Immutable vs mutable constraint partition; cache results for compile-time-known constraints |
| **SNES** | Mode 7 affine transform | Per-pixel matrix multiply | Hardware does billions of MACs | Batch constraints into matrix form; tensor cores evaluate entire batch as single matmul |
| **SNES** | Super FX coprocessor | Cartridge-side compute | Offload specific workloads | AVX-512 coprocessor for SIMD constraint evaluation; specialized kernels per domain type |
| **SNES** | SA-1 second CPU | Main CPU too slow for some tasks | Asymmetric multiprocessing | ARM Safety Island (slow, trusted) + AVX-512 (fast, bulk) + Tensor Cores (matrix specialist) |
| **N64** | Custom RSP µcode | 4KB instruction memory | Strip unused features | Minimal, specialized GPU kernels per constraint domain; no generic "evaluate all" kernel |
| **N64** | RDP command buffer | Async rendering | CPU writes, RDP reads async | Triple-buffered async constraint command stream; GPU reads while CPU writes |
| **N64** | Factor 5 stripped µcode | Standard µcode too bloated | 30% more instruction space | Strip conditional branches from constraint kernels; specialize per-domain at compile time |
| **N64** | Rare RSP time-slicing | RSP underutilized | Share RSP between audio+graphics | Time-slice GPU between constraint types; fill unused SM capacity with lower-priority constraints |
| **All** | Scanline racing | Beam timing | Operations synced to display | Constraint evaluation synced to cache-line boundaries; prefetch ahead of evaluation |
| **All** | Sprite multiplexing | Limited hardware sprites | Reuse sprites mid-frame | Reuse AVX-512 registers across constraint batches; band-based evaluation |
| **All** | Bank switching | Limited address space | Swap ROM banks on demand | Stream constraint pages through cache hierarchy; evaluate in cache-line-sized pages |
| **All** | PAL/NTSC adaptation | Different frame times | Region-specific optimization | Adaptive constraint budget based on available compute; degrade gracefully under load |
| **All** | Audio DMA repurposing | Dedicated DMA channels | Use DMA for non-audio data | Async GPU copy engines for constraint streaming; overlap transfer with evaluation |

---

## 9. Concrete FLUX Compiler Implications

### Architecture: Three-Tier Constraint Evaluation (SNES Model)

```
┌─────────────────────────────────────────────────┐
│  ARM Safety Island (5A22 — slow, trusted)       │
│  - Safety-critical constraint evaluation         │
│  - Audit logging                                │
│  - Final violation arbitration                   │
│  - Budget: ~100µs per evaluation cycle          │
├─────────────────────────────────────────────────┤
│  AVX-512 / CPU SIMD (Super FX — fast, general)  │
│  - BitmaskDomain: vptestmb (64 tests/inst)      │
│  - IntervalDomain: vminps/vmaxps (16 intervals) │
│  - EnumDomain: vpcmpd (16 enum checks)          │
│  - Budget: ~10µs per evaluation cycle           │
├─────────────────────────────────────────────────┤
│  Tensor Cores / GPU (Mode 7 — matrix specialist)│
│  - Large constraint matrices                     │
│  - Batch domain intersection                     │
│  - Constraint propagation (sparse matmul)        │
│  - Budget: ~1µs per evaluation cycle            │
└─────────────────────────────────────────────────┘

Data flow:
ARM ──[mailbox]──→ AVX-512 ──[command buffer]──→ GPU
  ↑                   │                            │
  └───[violation]─────┘       ┌──[async DMA]──────┘
                              │
                    GPU evaluates, DMA results back
```

### Constraint Descriptor Format (Neo Geo Sprite Model)

```c
// Inspired by Neo Geo sprite attribute descriptors
// Each constraint is a fixed-size descriptor that hardware can evaluate
typedef struct __attribute__((aligned(64))) {  // Cache-line aligned!
    uint8_t  domain_type;    // 0=bitmask, 1=interval, 2=enum, 3=symbolic
    uint8_t  priority;       // Evaluation priority (like sprite priority)
    uint8_t  eval_tier;      // 0=ARM, 1=AVX512, 2=TensorCore
    uint8_t  flags;          // Mutable(1) vs Immutable(0) — "fix layer" concept
    uint32_t constraint_id;  // Unique ID
    
    // Domain-specific parameters (union saves space — like self-modifying code)
    union {
        struct { uint64_t bitmask; uint64_t value; } bitmask;
        struct { float lo; float hi; float value; } interval;
        struct { uint32_t allowed_mask; uint32_t value; } enum_domain;
        struct { uint64_t expr_ptr; uint64_t env_ptr; } symbolic;
    };
    
    // Padding to fill cache line
    uint8_t  _pad[64 - 44];  // Exactly 64 bytes total
} constraint_descriptor_t;
```

### Minimal Kernel Design (Factor 5 / RSP Model)

```cuda
// Factor 5 approach: strip everything unnecessary
// This kernel handles ONLY BitmaskDomain constraints
// No branches for "is this interval?" — specialize at compile time

__global__ void evaluate_bitmask_constraints(
    const constraint_descriptor_t* __restrict__ constraints,
    violation_t* __restrict__ results,
    int count)
{
    // Everything in shared memory (RSP DMEM analog — 4KB → 48KB)
    __shared__ constraint_descriptor_t local_constraints[48];  // 3KB
    __shared__ violation_t local_results[48];
    
    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + tid;
    
    // Load into shared memory (DMA from global — like cartridge ROM→DMEM)
    if (gid < count) {
        local_constraints[tid] = constraints[gid];
    }
    __syncthreads();
    
    // Evaluate: single instruction per constraint (BBR/BBS analog)
    if (gid < count) {
        uint64_t mask = local_constraints[tid].bitmask.bitmask;
        uint64_t val  = local_constraints[tid].bitmask.value;
        bool violated = (mask & val) != val;  // Single bit test
        local_results[tid].violated = violated;
    }
    __syncthreads();
    
    // Write back (DMA to global)
    if (gid < count) {
        results[gid] = local_results[tid];
    }
}
```

---

## 10. Summary: The Forgemaster's Forge

Every classic console developer faced the same problem we do: **more constraints than resources.** Their solutions map directly:

1. **Know your cycle budget** (Atari 2600) → Know your cache-line budget
2. **Specialize your kernels** (Factor 5/N64) → Specialize per domain type
3. **Use fixed-function hardware** (Mode 7/Neo Geo) → Use tensor cores for matrix constraints
4. **Double-buffer everything** (Genesis) → Double-buffer CPU↔GPU communication
5. **Stream, don't store** (no frame buffer) → Stream results, no intermediate trees
6. **Partition mutable from immutable** (Neo Geo fix layer) → Cache compile-time constraint results
7. **Race the beam** (scanline racing) → Race the cache line (prefetch ahead)
8. **Multiplex scarce resources** (sprite multiplexing) → Multiplex AVX-512 registers across bands
9. **Bank-switch large programs** (NES/Genesis) → Stream constraint pages through cache
10. **Adapt to budget** (PAL/NTSC) → Degrade constraint checking depth gracefully

The consoles that won their generations (Genesis, SNES, N64) all used **asymmetric coprocessor architectures.** Our three-tier ARM + AVX-512 + Tensor Core design follows the same proven pattern. The constraint compiler should generate specialized evaluation kernels for each domain type, each tier, and each budget level — just like cartridge developers wrote specialized µcode for each game.

---

*Research by Forgemaster ⚒️ — Forged from the fires of 6502, 68000, and RSP assembly.*
