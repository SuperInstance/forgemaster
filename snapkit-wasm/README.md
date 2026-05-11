# @superinstance/snapkit-wasm

Eisenstein integer lattice snap, compiled from C to WebAssembly.

The **A₂ lattice** (Eisenstein integers ℤ[ω], ω = e^(2πi/3)) is the **densest possible packing in 2D**. This library finds the nearest lattice point to any (x, y) coordinate — the hexagonal Voronoï cell nearest-point problem — in **O(1) time with no loops**.

## Why Eisenstein?

| Property | Value |
|----------|-------|
| Packing density | π/(2√3) ≈ 0.9069 (proven optimal) |
| Covering radius | 1/√3 ≈ 0.57735 |
| Symmetry | 6-fold (hexagonal) |
| Ring structure | PID → H¹ = 0 (local ↔ global) |
| Quantization error | √(2/3)/√12 ≈ 0.403 (optimal for 2D) |

## Installation

```bash
npm install @superinstance/snapkit-wasm
```

## Quick Start

```javascript
import { SnapKit } from '@superinstance/snapkit-wasm';

const snapkit = await SnapKit.init('./node_modules/@superinstance/snapkit-wasm/snapkit.wasm');

// Snap a point to the nearest Eisenstein integer
const result = snapkit.eisensteinSnap(1.3, 0.7);
console.log(result);
// { a: 2, b: 1, snappedX: 1.5, snappedY: 0.866, distance: 0.211 }

// Batch snap (efficient — one JS→WASM call)
const batch = snapkit.eisensteinSnapBatch([
  { x: 1.3, y: 0.7 },
  { x: -0.5, y: 2.1 },
  { x: 3.7, y: -1.2 },
]);

// Covering radius
console.log(snapkit.coveringRadius()); // 0.5773502691896258

// Beat grid temporal snap
const beat = snapkit.beatGridSnap(1.37, 0.5);
// { snappedTime: 1.5, offset: -0.13, beatIndex: 3, phase: 0.74 }
```

## API Reference

### `SnapKit.init(source)` → `Promise<SnapKit>`

Load the WASM module. `source` can be a URL string, URL object, ArrayBuffer, or precompiled WebAssembly.Module.

### `snapkit.eisensteinSnap(x, y)` → `SnapResult`

Snap (x, y) to the nearest Eisenstein integer using the **optimal O(1) branchless algorithm**. ~15 floating-point operations, no 3×3 search.

```typescript
interface SnapResult {
  a: number;          // Eisenstein integer a
  b: number;          // Eisenstein integer b
  snappedX: number;   // Cartesian x = a − b/2
  snappedY: number;   // Cartesian y = b·√3/2
  distance: number;   // Euclidean distance to snapped point
}
```

### `snapkit.eisensteinSnapVoronoi(x, y)` → `SnapResult`

Same output, but uses the **3×3 neighborhood search** for guaranteed Voronoï correctness. Slower but brute-force proven.

### `snapkit.eisensteinSnapBatch(points)` → `SnapResult[]`

Batch snap. Single JS→WASM boundary crossing for the entire array.

### `snapkit.coveringRadius()` → `number`

Returns 1/√3 ≈ 0.57735. Any point in the plane is within this distance of some Eisenstein lattice point.

### `snapkit.beatGridSnap(t, period)` → `BeatResult`

Snap a timestamp to the nearest beat in a periodic grid.

```typescript
interface BeatResult {
  snappedTime: number;
  offset: number;
  beatIndex: number;
  phase: number;  // [0, 1)
}
```

### `snapkit.beatGridSnapBatch(timestamps, period)` → `BeatResult[]`

Batch temporal snap.

## Algorithm

The snap uses the **optimal branchless Voronoï correction** for the A₂ lattice:

1. **Basis conversion**: (x, y) → (a, b) in Eisenstein coordinates
2. **Round**: (a, b) → nearest integers
3. **Extract residuals**: u, v ∈ [-0.5, 0.5]
4. **6-condition cascade**: Check which of 6 triangular regions the residual falls into
5. **Correct**: Apply at most one (da, db) correction

The 6 conditions correspond to the 6 hexagonal Voronoï boundaries that extend beyond the rounding square. They're mutually exclusive (covering the 6 triangular corners) and resolve in O(1) — no distance computations needed.

Reference: Conway & Sloane, "Fast Quantizing and Decoding Algorithms for Lattice Quantizers and Codes" (1982).

## Building from Source

Requires `clang` with wasm32 target support:

```bash
make           # builds snapkit.wasm
make check     # inspect exports
make clean
```

Build command:
```
clang --target=wasm32 -nostdlib -O3 \
      -Wl,--no-entry -Wl,--allow-undefined \
      -Wl,--export=eisenstein_snap \
      -Wl,--export=eisenstein_snap_voronoi \
      -Wl,--export=eisenstein_snap_batch \
      -Wl,--export=covering_radius \
      -Wl,--export=beat_grid_snap \
      -Wl,--export=beat_grid_snap_batch \
      -Wl,--export=wasm_alloc \
      -o snapkit.wasm src/snapkit_glue.c -lm
```

## Demo

Open `index.html` in a browser. It includes a pure-JS fallback so the demo works without compiling WASM. Click anywhere on the hexagonal lattice to snap points and see the Voronoï cell structure.

## Coordinate Convention

Eisenstein integer (a, b) maps to Cartesian:
```
x = a − b/2
y = b · √3/2
```

The basis vectors are 1 = (1, 0) and ω = (−1/2, √3/2).

## Performance

| Method | Ops | Notes |
|--------|-----|-------|
| Optimal (O(1)) | ~15 FP ops | Branchless, 6-condition cascade |
| Voronoï (3×3) | ~70-80 FP ops | Brute-force, proven correct |
| Batch | amortized | Single JS→WASM call overhead |

## License

MIT — [SuperInstance](https://github.com/SuperInstance)
