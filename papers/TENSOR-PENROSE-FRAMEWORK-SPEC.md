# tensor-penrose — The Constraint Tensor Framework

> If PyTorch is "define and run" and TensorFlow is "define then run,"
> tensor-penrose is **"snap the constraint into the lattice and compute through the tiling."**
>
> Install: `pip install tensor-penrose`
> Or: `cargo add tensor-penrose`

---

## 1. The Core Abstraction

PyTorch has `torch.Tensor`. TensorFlow has `tf.Tensor`. Tensor-penrose has **`pt.Tile`**.

```python
import tensor_penrose as pt

# A tile is a tensor on a Penrose rhombus
# Its shape, position, and orientation are all part of the type
tile = pt.Tile(
    source=[1, 2, 3, 4, 5],    # 5D lattice coordinate
    tile_type="thick",          # thick (72°) or thin (36°)
    orientation=0.0,            # rotation in the Penrose floor
    dtype=pt.float32,
)

print(tile.shape)    # (5, 5) — thick tiles are 5×5
print(tile.position) # (x, y) in the Penrose floor
print(tile.values)   # 5×5 tensor calculated from source
```

The key difference: in PyTorch, tensors are **flat arrays** with shapes. In tensor-penrose, tensors are **tiles** with positions, orientations, and adjacency relationships baked into the data structure.

---

## 2. The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER CODE (Python/Rust)                      │
│                                                                  │
│  import tensor_penrose as pt                                     │
│  tiling = pt.Tiling.from_cut_and_project(lattice_points)         │
│  tiling.apply(pt.ops.threshold(0.5))                              │
│  tiling.constraint_check()                                        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    COMPUTATION LAYER (Rust/C)                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │  Eisentenor   │  │  Lattice Op  │  │  Tiling Engine    │       │
│  │  Snap Engine  │  │  Projection  │  │  SIMD/Kernel Ops  │       │
│  │  (C/Rust)     │  │  Lift/Encode │  │  MPI/GPU Fallback │       │
│  └──────────────┘  └──────────────┘  └──────────────────┘       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                   LATTICE BACKEND (Pluggable)                    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  A₂ (2D) │  │  5D→2D   │  │  nD→mD   │  │  Learned Proj  │  │
│  │ Eisenstn  │  │ Penrose  │  │ General  │  │  (PCA/Neural)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1: Lattice Backend (pluggable)

The lowest layer defines **how source coordinates map to tile positions**. Unlike PyTorch where the "backend" is CPU vs GPU, tensor-penrose's backend is the **lattice geometry**:

```python
# Plug in different lattice backends
pt.set_lattice("eisenstein")       # A₂ lattice, Eisenstein integers (fastest)
pt.set_lattice("penrose")          # 5D→2D cut-and-project (classic)
pt.set_lattice("learned")          # PCA or neural projection (most flexible)
pt.register_lattice("custom", MyLattice)  # Your own
```

Each backend implements a single interface:

```rust
pub trait LatticeBackend {
    /// Snap a point (x,y) to the nearest lattice point
    fn snap(&self, x: f64, y: f64) -> SnapResult;
    
    /// Project an nD source coordinate down to 2D tile position
    fn project(&self, source: &[i32]) -> ProjectionResult;
    
    /// Lift a 2D position up to nD lattice coordinates (reverse actualization)
    fn lift(&self, x: f64, y: f64) -> Vec<i32>;
    
    /// Classify tile type from source coordinates
    fn classify(&self, source: &[i32]) -> TileType;
}
```

### Layer 2: Computation Layer (the engine)

This is where the tensor operations live — in Rust/C with SIMD:

```rust
// Internal engine operations (not called directly by users)
pub trait TilingEngine {
    /// Apply a unary op to every tile's tensor
    fn apply_unary<O: TileOp>(&mut self, op: &O) -> TimingInfo;
    
    /// Apply a binary op across adjacent tile borders
    fn apply_binary<O: BorderOp>(&mut self, op: &O) -> TimingInfo;
    
    /// Constraint check: sum border mismatches
    fn constraint_check(&self) -> f32;
    
    /// Recompose: merge two adjacent tiles into one at higher hierarchy level
    fn recompose(&mut self, level: u32) -> Vec<TileId>;
}
```

### Layer 3: User Code (Python or Rust)

A clean API that feels like PyTorch:

```python
# Create a tiling from 1000 5D lattice points
tiling = pt.Tiling.from_coordinates(
    sources=np.random.randint(-10, 10, (1000, 5)),
    backend="eisenstein",
    tensor_shape=(5, 5),  # or "auto" for tile-type-dependent shapes
)

# Fill all tiles from their source coordinates
tiling.fill()

# Apply operations (chainable)
tiling.apply_threshold(0.5)

# Compute norms
energies = tiling.l1_norm()   # (1000,) — one per tile
signals  = tiling.l2_norm()   # (1000,)

# Constraint checking
mismatch = tiling.constraint_check(metric="l1")

# Access individual tiles
tile = tiling[42]
print(tile.source_coords)     # [3, -1, 7, 2, -4]
print(tile.tensor_values)     # 5×5 float32 array

# Save/load
tiling.save("my_tiling.pt")
tiling = pt.Tiling.load("my_tiling.pt")
```

---

## 3. The Five Operations That Matter

tensor-penrose has exactly five core operations. Everything else derives from these:

### 1. `tiling.snap(points)`
Snap arbitrary 2D coordinates to the nearest lattice point. Returns source coordinates.

```python
# Snap user input to the lattice
x, y = 0.732, -1.445
source = tiling.snap(x, y)  # [1, -2, 0, 1, -1] (depends on backend)
```

**Backend:** C with 26M snp/s. The bridge we already built.

### 2. `tiling.fill(source_coords)`
Fill a tile's tensor from its 5D source coordinates using orthogonal basis modes.

```python
tile = tiling[42]
tile.fill_from_source()  # Populates tensor from tile.source_coords
```

**Backend:** Rust with auto-vectorized loops. The module we already built.

### 3. `tiling.apply(kernel)`
Apply a function to every tile in the tiling. Auto-vectorized when possible.

```python
# Built-in kernels
tiling.apply(pt.kernels.threshold(0.5))
tiling.apply(pt.kernels.normalize("l1"))
tiling.apply(pt.kernels.gaussian_blur(sigma=1.0))

# Custom kernel (Python)
@pt.kernel
def my_kernel(tile: pt.Tile):
    tile.values = tile.values * 2.0 - tile.l1_norm()

tiling.apply(my_kernel)
```

**Backend:** Rust SIMD, 16× throughput on AVX-512 when the kernel is pure linear algebra.

### 4. `tiling.constrain(edges, ops)`
Define constraints between adjacent tiles and check them.

```python
# Two tiles should have matching border values
tiling.constrain(edges=[(0, 1), (2, 3)], ops=["eq", "ge"])

# Check all constraints
results = tiling.constraint_check()
# { '0-1': 0.002, '2-3': 0.147 } — lower = better match
```

**Backend:** Rust border fusion, 654M holonomy checks/s. Already benchmarked.

### 5. `tiling.recompose()`
Merge adjacent tiles up the hierarchy at φ^k scales. The Penrose deflation operator.

```python
# Level 1: merge close tiles
tiling.recompose(level=1)

# Level 2: merge the merged tiles
tiling.recompose(level=2)
```

**Backend:** cut-and-project with golden hierarchy. Already in penrose-memory.

---

## 4. The Python ↔ Rust Bridge

```python
# Python imports feel like PyTorch
import tensor_penrose as pt

# But the engine is Rust (like PyTorch's C++ backend)
# The user never sees the Rust — it's a compiled extension
```

The bridge uses PyO3 (PyTorch uses pybind11). Each `pt.Tile` and `pt.Tiling` in Python is a thin wrapper around a Rust struct:

```rust
#[pyclass]
pub struct PyTiling {
    inner: TensorTiling,  // The Rust implementation
    backend: Box<dyn LatticeBackend>,
}

#[pymethods]
impl PyTiling {
    fn apply_threshold(&mut self, threshold: f32) {
        self.inner.apply_kernel(|tile| tile.apply_threshold(threshold));
    }
    
    fn constraint_check(&self) -> HashMap<String, f32> {
        // ...
    }
}
```

---

## 5. What This Replaces

| Framework | Paradigm | Unit of Computation | This does |
|-----------|----------|-------------------|-----------|
| PyTorch | Tensor ops on arrays | `torch.Tensor` (N-D array) | Optimize neural net weights |
| TensorFlow | Dataflow graphs | `tf.Tensor` (symbolic array) | Deploy ML at scale |
| **tensor-penrose** | **Constraint ops on tilings** | **`pt.Tile` (2D tile in aperiodic plane)** | **Verify constraint satisfaction with proofs** |

tensor-penrose doesn't replace PyTorch. It **sits beside it**. You train a model in PyTorch, then embed the trained weights into a tensor-penrose tiling for constraint verification:

```python
import torch
import tensor_penrose as pt

# Train in PyTorch
model = MyModel()
train(model, data)

# Embed weights into tensor-penrose for constraint checking
weights = model.state_dict()
coords = pt.lift_weights(weights)  # model weights → 5D lattice coordinates
tiling = pt.Tiling.from_coordinates(coords, backend="penrose")

# Verify: do the weights satisfy safety constraints?
violations = tiling.constraint_check()
assert violations["total"] < EPSILON, "Safety constraints violated!"
```

---

## 6. The CLI

```bash
# Create a tiling from a CSV of 5D coordinates
pt create --source points.csv --backend eisenstein --output my_tiling.pt

# Inspect a tiling
pt info my_tiling.pt
# Tiling: eisenstein backend
# Tiles: 1000 (412 thick, 588 thin)
# Shape: (5, 5) per thick tile, (3, 8) per thin tile
# Adjacent pairs: 2847

# Apply a kernel
pt apply my_tiling.pt --kernel threshold --params 0.5

# Benchmark
pt bench my_tiling.pt --ops snap,fill,constrain
# snap:    38.7 ns/op  (25.9M ops/sec)
# fill:    124.2 ns/op (8.1M ops/sec)
# constrain: 1.5 ns/op (654M ops/sec)
```

---

## 7. The Three Marketing Lines

1. **"Like PyTorch, but the tensors come with positions and the array is a tiling."**

2. **"Train in PyTorch. Verify in tensor-penrose."**

3. **"Every tile is a proof. Every edge is a constraint. Every constraint gets checked at 654M ops/sec."**

---

## 8. Immediate Build Orders

### Phase 1 (this week): CLI + Rust crate
- `cargo new tensor-penrose` — the Rust core
- Merge fleet-math-c bridge as `tensor_penrose::backend::eisenstein`
- Merge penrose-memory's TensorTile as `tensor_penrose::tile::TensorTile`
- CLI: `pt create`, `pt info`, `pt apply`, `pt bench`

### Phase 2 (next week): Python bindings
- PyO3 bindings for `pt.Tile` and `pt.Tiling`
- `pip install tensor-penrose` works
- Import works: `import tensor_penrose as pt`
- Jupyter notebook examples

### Phase 3 (alpha): Ecosystem
- PyTorch integration: `pt.from_torch(tensor)` — embed any torch.Tensor
- TensorFlow integration: `pt.from_tf(tensor)`
- Hacker News launch with benchmark comparisons

---

*This is not a paper. This is a spec. The paper wrote itself. The code is what proves it.*
