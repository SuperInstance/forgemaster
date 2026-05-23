# Penrose + Tri-Quarter Decomposition

> **Penrose:** [xnx/penrose](https://github.com/xnx/penrose) — 82 stars, Python, MIT  
> **Tri-Quarter:** [nathanoschmidt/tri-quarter-toolbox](https://github.com/nathanoschmidt/tri-quarter-toolbox) — MIT, Python  
> **Why both:** Penrose handles tiling generation. Tri-Quarter handles Eisenstein integer computation + hexagonal lattice graphs. Together they cover 2/3 of our terrain system.

## 1. What These Libraries Do

### xnx/penrose
Python package for generating Penrose P3 tilings (kite-and-dart, rhombi). Provides subdivision-based generation: start with a few tiles, subdivide repeatedly to get arbitrary precision. Used in physics, crystallography, and artistic applications.

### tri-quarter-toolbox
Nathan Schmidt's research framework for "upgrading the complex numbers" with:
- **Eisenstein integer arithmetic** (our E12, their "tri-quarter numbers")
- **Radial Dual Triangular Lattice Graph (RDTLG)** — hexagonal lattice with graph structure
- **Inversive geometry** — Möbius transformations on the hexagonal lattice
- **Signal processing** — BPSK case study using Eisenstein integers
- **Geometric deep learning** — equivariant neural network benchmarks
- **Theorem animations** — visual proofs of foundational results

This is the closest external project to our work. Period.

## 2. What's Insightful

### 2.1 🏆 RDTLG — Radial Dual Triangular Lattice Graph (Tri-Quarter)

A hexagonal lattice WITH GRAPH STRUCTURE. Not just points — vertices, edges, and a coordinate system. The "radial dual" means the graph is organized radially from the origin, with each ring being a hexagonal shell.

**Why it matters:** Our E12 coordinates are just (a, b) pairs — points without connectivity. RDTLG adds the GRAPH: which points are adjacent, what's the shortest path, how many hops between two coordinates. This is exactly what our terrain system needs for "nearest neighbor" lookups.

**What we should take:** Implement RDTLG-style graph connectivity on top of our E12 coordinates. E12 gives us the coordinate system; RDTLG gives us the navigation.

### 2.2 🏆 BPSK Case Study — Eisenstein Integer Signal Processing

They implemented Binary Phase Shift Keying (BPSK) using Eisenstein integers instead of real/complex numbers. The key insight: E12 lattice points serve as signal constellation points with hexagonal symmetry.

**Why it matters:** This proves E12 integers work for real signal processing, not just abstract math. Their BER (Bit Error Rate) results could validate our approach.

**What we should take:** Their simulation framework for benchmarking. If E12 works for BPSK, it works for our constraint verification signals.

### 2.3 🏆 Equivariant Neural Network Benchmarks

They benchmark neural networks with E12-equivariant layers. The hexagonal symmetry (C6 group) provides rotational equivariance that standard networks lack.

**What we should take:** Our SplineLinear uses Eisenstein lattice weight parameterization. Tri-Quarter's equivariant layers are a different approach to the same idea. Comparing them could yield insights.

### 2.4 🏆 Penrose Subdivision Algorithm (xnx/penrose)

Start with initial tiles → subdivide each tile into smaller tiles → repeat. The subdivision is deterministic and generates the same tiling regardless of how many times you subdivide.

**Why it matters for us:** Our Penrose Memory Palace uses cut-and-project (higher-dimensional projection). Subdivision is a DIFFERENT way to generate the same tilings. Cut-and-project gives exact coordinates; subdivision gives hierarchical structure.

**What we should take:** Subdivision gives us a natural multi-resolution index. Level 0 = coarse (one tile per domain). Level 5 = fine (many tiles per domain). This is EXACTLY what our terrain needs — zoom in for detail, zoom out for overview.

### 2.5 🏆 Inversive Geometry — Möbius on Hex Lattice

Tri-Quarter implements Möbius transformations on the hexagonal lattice. These preserve circles and lines, mapping the lattice onto itself in useful ways.

**What we should take:** If our E12 terrain needs to "rotate" (reorganize knowledge domains), Möbius transformations would remap coordinates while preserving adjacency relationships.

## 3. What We Already Do Better

| Aspect | Tri-Quarter | Cocapn |
|--------|------------|--------|
| E12 arithmetic | ✅ Has it | ✅ Has it (our `eisenstein.rs`) |
| Graph structure | ✅ RDTLG | ❌ Missing (just coordinates) |
| Rust implementation | ❌ Python only | ✅ Rust crate |
| Hardware targets | ❌ None | ✅ 8 targets |
| Content addressing | ❌ None | ✅ Tile hashes |
| Verification | ❌ None | ✅ Constraint proofs |
| Fleet integration | ❌ None | ✅ PLATO + Matrix |
| Multi-resolution index | ❌ None | ❌ Missing (could use subdivision) |
| Signal processing | ✅ BPSK study | ❌ Not yet |
| Geometric deep learning | ✅ Equivariant NN | ✅ SplineLinear (different approach) |

## 4. Negative Space

### 4.1 🕳️ Both Lack Distributed Architecture

Penrose generates tilings locally. Tri-Quarter processes locally. Neither knows about multi-agent systems or distributed knowledge.

**Our opportunity:** E12 terrain + RDTLG graph + PLATO distributed tiles = spatial knowledge network that actually works.

### 4.2 🕳️ No Content Addressing or Verification

Neither library hashes its outputs or verifies correctness beyond unit tests.

**Our opportunity:** Every generated tiling should be content-addressed. Every lattice computation should be constraint-verified.

### 4.3 🕳️ No Interactive Visualization

Both are library-only. No demos, no interactive exploration.

**Our opportunity:** Our HTML demos (hex-snap-playground, penrose-memory-palace) already provide this. Adding RDTLG graph navigation would be a killer feature.

## 5. Direct Adaptations

### 5.1 Fork penrose → Multi-Resolution Terrain Index

Use subdivision levels as terrain zoom:
- Level 0: 10 domains (coarse)
- Level 3: ~600 tiles (medium)
- Level 6: ~150K tiles (fine)

Each level is a valid tiling. Search starts at level 0, zooms into the matching domain.

### 5.2 Fork tri-quarter → RDTLG Navigation Layer

Add their graph structure to our E12 coordinates:
```rust
// In eisenstein.rs
fn neighbors(a: i32, b: i32) -> [(i32, i32); 6] {
    E12_DIRECTIONS.map(|(da, db)| (a + da, b + da)) // hex neighbors
}

fn hop_distance(a1: i32, b1: i32, a2: i32, b2: i32) -> u32 {
    // Shortest path on hex lattice (no need for Dijkstra — closed form)
    let da = a1 - a2;
    let db = b1 - b2;
    // Hex distance formula
    if (da > 0) == (db > 0) {
        (da.abs() + db.abs()) as u32
    } else {
        da.abs().max(db.abs()) as u32
    }
}
```

### 5.3 BPSK Benchmark for E12 Validation

Run their BPSK simulation with our E12 implementation. If BER matches, our arithmetic is correct.

## 6. Credit & Fork Status

| Repo | Forked To | Status |
|------|----------|--------|
| xnx/penrose | SuperInstance/penrose | ✅ Forked, needs CREDITS + adaptations |
| nathanoschmidt/tri-quarter-toolbox | SuperInstance/tri-quarter-toolbox | ✅ Forked, needs CREDITS + adaptations |

**Both are MIT licensed.** Our adaptations will also be MIT. Clear attribution in CREDITS files.

**Priority:** RDTLG graph layer is highest value — it fills the biggest gap in our terrain system. Penrose subdivision is second — multi-resolution indexing.

---

*This is the most exciting find. Someone else is working on Eisenstein integer frameworks independently. Different goals, different approach, but same mathematical foundation. The RDTLG graph structure is something we don't have and desperately need.*
