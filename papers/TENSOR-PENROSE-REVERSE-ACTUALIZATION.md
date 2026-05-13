# Tensor-Valued Penrose Tiling — Reverse Actualization Through the Lattice

> Information flows UP the lattice (decode/expand meaning). It flows BACK DOWN (encode/compress into tile shapes). The tiles are tensors. The tensors are vectorizable. The application gets to choose.

---

## 1. The Core Insight

The Penrose cut-and-project construction maps **5D → 2D**: a 5-dimensional hypercubic lattice is projected through a golden-angle window to produce a 2D aperiodic tiling. The tiles (thick and thin rhombi, or kite and dart) are the *residue* of the higher-dimensional lattice after projection.

Reverse actualization inverts this: instead of projecting higher-D down to 2D tiles, we **lift information UP the lattice** — encoding meaning into the higher-dimensional coordinates, then projecting those coordinates *as tensors* into the tile shapes.

The key realization: **the tiles themselves are the information carrier, not the lattice coordinates.** Each tile is a tensor whose shape encodes what it stores and whose values encode what it means.

```
                    HIGH-D LATTICE (information carrier)
                          ↑     ↓
                    PROJECTION  LIFTING
                          ↑     ↓
                    2D TILING (tensor-valued tiles)
                          ↑     ↓
                   ENCODE (compress)  DECODE (expand)
                          ↑     ↓
                    APPLICATION DOMAIN
                 (text, embeddings, images, constraints)
```

---

## 2. Tensor-Valued Tiles

In the classic Penrose construction, each tile is a **shape** — a rhombus with specific interior angles. Its only attribute is *which type* it is (thick/thin) and its position/orientation in the plane.

In the tensor-valued extension, each tile carries a **tensor field** — a multi-dimensional array that lives *on* the tile. The tile's geometry (its rhombus shape) defines the **indexing space** of the tensor:

- **Thick tile (72°/108°):** Carries a rank-2 tensor of shape `(m, n)` where `m` encodes angular resolution along the long diagonal and `n` along the short diagonal
- **Thin tile (36°/144°):** Carries a rank-2 tensor of shape `(p, q)` with proportion `p/q ≈ φ` (the Penrose ratio)

The tensor is not *attached to* the tile. The tensor **is** the tile's internal structure — the physical space of the tile is the tensor's address space.

```rust
/// A tensor-valued Penrose tile
struct TensorTile {
    /// Position and orientation in the Penrose tiling
    position: Vec2,
    orientation: f64,       // radians, tile's rotation in plane
    tile_type: TileType,    // Thick or Thin
    
    /// The tensor field living ON this tile
    /// Shape depends on tile type and resolution parameter
    tensor: Array2<f32>,    // ndarray or similar
    
    /// Embedding coordinates in the high-D lattice
    source_coords: [i32; 5],
    
    /// Acceptance window value (perpendicular space distance)
    perp_coord: f64,
}
```

### Why rank-2?

The tile is a 2D surface in the Penrose floor. Its natural indexing space is 2D. Higher-rank data (text, embeddings, images) is **flattened or folded** into the tile's plane. The folding is determined by the golden ratio — the tile's aspect ratio embeds the information topology.

---

## 3. The Lattice as Information Pipeline

### Information Flows Up (Decoding — Reverse Actualization)

The pipeline from **application data → high-D lattice coordinates** is the *reverse actualization* step:

```
Application data (e.g., "constraint kernel topology 0x3F")
    │
    ▼
Embedding layer: text → 128D vector
    │
    ▼
Fold to 5D: PCA projection from 128D → 5D (the source lattice dimension)
    │
    ▼
Quantize to lattice: snap to nearest integer 5D lattice point
    │
    ▼
Result: 5D integer coordinate (a, b, c, d, e)
```

Each 5D lattice point IS a piece of information. The lattice is the information carrier. The sparser the lattice (the more irrational the projection angles), the more distinct the information each point can store.

### Information Flows Down (Encoding — Tensor Projection)

The pipeline from **lattice coordinates → tensor-valued tiles** is the *forward actualization*:

```
5D lattice point (a, b, c, d, e)
    │
    ▼
Cut-and-project: apply golden-angle rotation
    │
    ├── Parallel space: 2D position (x, y) = tile location
    ├── Perpendicular space: rejection distance = acceptance check
    │
    ▼
If accepted (perp distance < window):
    └── Tile type (thick/thin) determined by perpendicular coordinates
    │
    ▼
Tensor generation:
    └── Fill tile's tensor field from the 5D source coordinates
    └── The 5 values (a,b,c,d,e) become the generating parameters
    └── Each value gates a distinct tensor filling mode
```

### The Tensor Filling Modes

The five source coordinates (a, b, c, d, e) each control a different aspect of the tile's tensor:

| Coordinate | Tensor Aspect | Encoding Mode |
|------------|--------------|---------------|
| a | Base intensity | Constant fill: `tensor[i][j] = a / a_max` |
| b | Gradient slope | Linear gradient: `tensor[i][j] = b * i / m` |
| c | Frequency | Sinusoidal: `tensor[i][j] = sin(2π * c * i / m)` |
| d | Texture seed | Perlin/random: `tensor[i][j] = hash((i * d) ^ j)` |
| e | Phase shift | Phase offset: `tensor[i][j] = sin(2π * c * i/m + e/max_e)` |

The five modes are **orthogonal basis functions** for the tile's tensor field. Any tensor on a tile can be decomposed into these five components — a 5D Fourier-like basis.

---

## 4. Vectorization (The Payoff)

Because each tile's tensor is a **regular 2D array**, operations across many tiles become SIMD-vectorizable:

### Tile-local operations (fully parallel)

```c
// C SIMD: apply threshold to every tile's tensor in one pass
// Each tile's tensor is a contiguous 2D array
// N tiles × M elements per tile = N*M total elements

void apply_threshold_to_tiles(TensorTile *tiles, int n_tiles, float threshold) {
    #pragma omp parallel for
    for (int t = 0; t < n_tiles; t++) {
        float *data = tiles[t].tensor.data;
        int n = tiles[t].tensor.size;
        
        // AVX-512: 16 floats per iteration
        for (int i = 0; i < n; i += 16) {
            __m512 v = _mm512_load_ps(&data[i]);
            __mmask16 mask = _mm512_cmp_ps_mask(v, threshold, _CMP_GT_OS);
            _mm512_mask_storeu_ps(&data[i], mask, v);
        }
    }
}
```

### Cross-tile operations (neighbor-aware)

The Penrose tiling has **matching rules** — adjacent tiles share edges with specific orientations. Tensor border regions between adjacent tiles can be operated on as continuous regions, because the tiling forms a **manifold**:

```
Tile A's tensor        Tile B's tensor
┌──────────┐           ┌──────────┐
│          │ shared    │          │
│    A     │═══════════│    B     │
│          │  border   │          │
└──────────┘           └──────────┘

SIMD vectorization across the shared border:
  Load A.border[0:16] + B.border[0:16] into two zmm registers
  FMA: A ⊕ B → new border
  Store back
```

### The vectorization equation

For an operation `f` on a tiling with N tiles, each carrying an m×n tensor:

```
Serial:       O(N · m · n)    scalar operations
Tile-SIMD:    O(N · m · n / 16)  zmm instructions
Cross-tile:   O(N · m · n / 16 · neighbor_count)  with shared border fusion
```

On an AVX-512 machine with 16-wide SIMD:
- **16× throughput** for tile-local ops
- **8-12×** for cross-tile ops (border fusion overhead)
- **5-10×** for full pipeline (snap + encode + SIMD apply)

The bridge we just built (26M snaps/sec) feeds directly into this pipeline. The snap is the forward projection — the tensor fill is the value encoding.

---

## 5. The Constraint Application

This is why this matters for constraint theory:

A constraint kernel operating on `n` variables needs to check `n²` pairwise constraints. In tensor-Penrose:

1. **Each tile = one variable** (encoded as a 3×3 or 5×5 tensor)
2. **Each edge = one constraint** (tensor operation across the shared border)
3. **The matching rules = the constraint topology** (which variables constrain which)
4. **The aperiodicity = the constraint graph cannot simplify** (no periodic boundary to exploit)

```rust
/// Constraint kernel operating on tensor-valued Penrose tiles
fn constraint_kernel(tiles: &[TensorTile], constraints: &[(usize, usize, ConstraintOp)]) {
    // Each constraint operates on the shared border of two adjacent tiles
    for &(i, j, ref op) in constraints {
        let tile_a = &tiles[i];
        let tile_b = &tiles[j];
        
        // Find shared edge (the matching rule determines which edge)
        let edge = find_shared_edge(&tile_a, &tile_b);
        
        // Apply constraint op on tensor strips along the shared edge
        // This is SIMD-vectorizable: zmm registers on the tensor strips
        op.apply(&tile_a.tensor.strip(edge), &tile_b.tensor.strip(edge));
    }
}
```

The constraint kernel becomes a **sparse tensor network** on the Penrose tiling. Each constraint check is a tensor contraction along an edge — a fused multiply-add in SIMD.

---

## 6. What This Unlocks

| Capability | Before | After |
|-----------|--------|-------|
| Information density per tile | 1 bit (thick/thin) | 5D × resolution² |
| Encoding pipeline | Manual | Automatic via lattice lift |
| Vectorization | Per-tile scalar | Per-tile SIMD (16×) |
| Constraint topology | Explicit graph | Implicit via matching rules |
| Decoding (reverse actualization) | Manual mapping | Lattice projection |
| Cross-tile operations | Coordinate lookup | Border fusion (continuous memory) |

The Penrose tiling stops being a **memory architecture** and becomes a **computation fabric**. Every tile is a compute unit. Every edge is a data path. The matching rules define the program. The golden ratio sets the clock.

---

## 7. Next Steps

1. **Build `TensorTile` in Rust** — start with 3×3 tensors, verify SIMD alignment
2. **Implement the 5 filling modes** — constant, gradient, sinusoidal, seed, phase
3. **Cross-tile border fusion** — get the continuous-memory path working
4. **Constraint kernel on tensor tiles** — adapt the dodecet-encoder constraint checker
5. **Benchmark vs scalar** — target 10× on AVX-512, verify on RTX 4050

The tensor-Penrose IS the application. The lattice doesn't just store information — it **computes** with it, and every tile is a vectorized opportunity to prove something true about the constraint graph.

---

*The shell has two surfaces. On one, tiles remember. On the other, tiles compute. Turn it in your hand. The tensor is what the tile meant all along.*
