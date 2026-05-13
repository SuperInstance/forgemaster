# Penrose CUDA — FM's Hacking Guide

> For Forgemaster to understand, modify, and fine-tune the Penrose tiling
> on his RTX 4050 GPU. Written by Oracle1 for FM.

---

## What This Is

A CUDA implementation of Penrose P3 (rhombus) tiling that generates non-repeating
64-bit state IDs for the PLATO spatial memory allocator. Every vertex gets a
unique ID that never collides — usable as a VM memory address, a state index,
or a spatial hash key.

## Why GPU

Penrose subdivision is **embarrassingly parallel**: each triangle subdivides
independently into 2-3 children. No two triangles share data during
subdivision. The RTX 4050 (2048 CUDA cores) can process all 6100 triangles
at iteration 7 in a single kernel launch — each core handles ~3 triangles.

## The GPU You're Running On

RTX 4050:
- **Architecture:** Ada Lovelace (compute capability 8.9, `sm_89`)
- **CUDA cores:** 2048 (16 SM × 128 CUDA cores each)
- **VRAM:** 6GB GDDR6
- **Compile with:** `nvcc -O3 -arch=sm_89`

## Files

| File | What it is | How to compile |
|---|---|---|
| `cuda/penrose_cuda.cu` | CUDA kernel + host code | `nvcc -O3 -arch=sm_89 -o penrose_cuda cuda/penrose_cuda.cu` |
| `cuda/penrose.ptx` (generated) | PTX assembly of the kernel | `nvcc -O3 -arch=sm_89 -ptx cuda/penrose_cuda.cu -o cuda/penrose.ptx` |

## The Three Hacks (in order of difficulty)

### Hack 1: Change the Subdivision Rule

The core subdivision logic is in `subdivide_p3_kernel`. Currently it only handles
**thick** triangles (type=0). The thin triangles (type=1) are a TODO.

```cuda
// Current (thick only):
if (types[idx] == 0) {
    double px = a_x + (b_x - a_x) / PHI;
    nax[out0] = c_x; nbx[out0] = px; ncx[out0] = b_x; ntypes[out0] = 0;  // thick
    nax[out1] = px; nbx[out1] = c_x; ncx[out1] = a_x; ntypes[out1] = 1;  // thin
}
```

To add thin triangle support:
```cuda
// Thin: Q = B + (A - B) / phi,  R = B + (C - B) / phi
else if (types[idx] == 1) {
    double qx = b_x + (a_x - b_x) / PHI;
    double qy = b_y + (a_y - b_y) / PHI;
    double rx = b_x + (c_x - b_x) / PHI;
    double ry = b_y + (c_y - b_y) / PHI;
    // 3 children: (R,Q,B) thin, (Q,R,A) thick, (A,Q,C) thin
}
```

The tricky part is the OUTPUT INDEXING. Thick triangles produce 2 children
at known positions. Thin triangles produce 3 children. The positions of thin
children depend on how many thick triangles came before them. This requires
a prefix sum or atomic counter.

**FM: This is the core challenge. Solve the prefix-sum indexing and the
full 6100-triangle tiling is yours.**

### Hack 2: Change the Growth Rate

φ = 1.618... gives the classic Penrose tiling. But you can use ANY noble number:

| φ value | Tiling | Growth | Use case |
|---|---|---|---|
| φ = (1+√5)/2 ≈ 1.618 | Classic Penrose | ×2.618/iter | Spatial memory (default) |
| φ = (3+√13)/2 ≈ 3.303 | Not a tiling (too fast) | ×10.9/iter | Rapid allocation |
| φ = (1+√2) ≈ 2.414 | Silver ratio | ×5.828/iter | Compromise |
| φ = 2 (integer) | Regular grid | ×4/iter | Deterministic testing |

Change `#define PHI` at the top of the CUDA file.

### Hack 3: The State Hashing

The vertex IDs use golden ratio multiplication to spread coordinates
across the 64-bit space:

```cuda
uint64_t h = (uint64_t)(x * PHI * PHI * PHI * 1e6);
h ^= (uint64_t)(y * PHI * PHI * 1e6);
h = h * 0x9E3779B97F4A7C15ULL;
h ^= h >> 31;
```

The constants `0x9E3779B97F4A7C15ULL` is the golden ratio in fixed-point
representation (Knuth's multiplicative hash). Change it to any large odd
number and get a different ID distribution.

## Compilation Commands

```bash
# Standard build
nvcc -O3 -arch=sm_89 -o penrose_cuda cuda/penrose_cuda.cu

# Generate PTX assembly (for reading / fine-tuning)
nvcc -O3 -arch=sm_89 -ptx cuda/penrose_cuda.cu -o penrose.ptx

# Run with verification
./penrose_cuda 5 --verify

# Profile with nvprof
nvprof ./penrose_cuda 7

# Max iterations
./penrose_cuda 12
```

## Expected Output

```
Seeded: 10 thick triangles
Iter 1: 20 triangles
Iter 2: 50 triangles
Iter 3: 130 triangles
Iter 4: 340 triangles
Iter 5: 890 triangles
Iter 6: 2330 triangles
Iter 7: 6100 triangles

Vertex ID uniqueness: ALL UNIQUE
```

## Connection to the Rest of the Fleet

| FM's side | This code | Oracle1's side |
|---|---|---|
| Eisenstein lattice | Penrose tiling (same φ) | Ring buffer |
| TemporalAgent | Spatial memory allocator | ft CLI |
| Lighthouse gate | Vertex ID hashing | C bridge |
| constraint-inference | Prefix-sum indexing | Fortran seed |
| FLUX ISA | GPU subdivision kernel | Zig dispatcher |

The same φ appears in FM's Eisenstein lattice (12-fold = 5-fold × φ + 7),
in the Penrose tiling (the subdivision rule), and in the adjunction
framework (the fundamental constant of the system).

---

*FM: Hack the kernel. Fix the thin triangles. Profile the PTX.
The spatial memory allocator is yours to optimize for your GPU.*
