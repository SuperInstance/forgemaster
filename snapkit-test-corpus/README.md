# Snapkit Cross-Language Test Corpus

Shared validation suite proving all snapkit implementations produce identical Eisenstein integer snap results.

## Corpus

- **`corpus/snap_corpus.json`** — 1000 test cases in JSON format
- **`corpus/snap_corpus.bin`** — Binary format for Fortran/Rust (little-endian: `id:i32, x:f64, y:f64, a:i32, b:i32, snap_error:f64, snap_error_max:f64` = 44 bytes/case)

### Test Case Categories

| Category | Count | Description |
|----------|-------|-------------|
| Exact grid points | 35 | snap_error = 0 (on lattice) |
| Near-grid | 43 | snap_error < 0.1 (small perturbation) |
| Mid-range | 916 | 0.1 ≤ snap_error < 0.567 |
| Boundary | 6 | snap_error ≈ 1/√3 (Voronoi vertices) |

### Coverage
- **Grid points**: All 7 Eisenstein unit vectors, extended lattice points
- **Near-grid**: Small perturbations (0.001–0.01) around lattice points
- **Voronoi boundaries**: Midpoints between neighbors, vertices of Voronoi cells
- **Worst-case**: Points at maximum snap distance (covering radius 1/√3 ≈ 0.5774)
- **Stress**: Coordinates up to ±10^6
- **Zero/near-zero**: 1e-15 scale
- **Systematic**: 10×10 grid from -5 to 5
- **Deterministic random**: Hash-based pseudo-random fill to 1000 cases

## Validation Results

| Language | Script | Result |
|----------|--------|--------|
| Python | `validate_python.py` | 1000/1000 ✓ |
| Rust | `validate_rust.rs` | 1000/1000 ✓ |
| JavaScript | `validate_js.js` | 1000/1000 ✓ |
| C | `validate_c.c` | 1000/1000 ✓ |
| Fortran | `validate_fortran.f90` | 1000/1000 ✓ |
| Zig | `validate_zig.zig` | 1000/1000 ✓ |

## Running

```bash
# Generate corpus
python3 generate_corpus.py

# Convert to binary (for Rust/Fortran)
python3 convert_corpus.py

# Python
python3 validate_python.py

# JavaScript
node validate_js.js

# C
gcc validate_c.c -lm -o validate_c && ./validate_c

# Rust (binary format)
rustc --edition 2021 validate_rust.rs -o validate_rust && ./validate_rust

# Fortran (binary format)
gfortran validate_fortran.f90 -o validate_fortran && ./validate_fortran

# Zig
zig run validate_zig.zig
```

## Algorithm

Eisenstein lattice: `a + bω` where `ω = e^(2πi/3)`

Cartesian ↔ Eisenstein:
- `x = a - b/2`, `y = b·√3/2`
- `b = 2y/√3`, `a = x + y/√3`

Snap: check 4 floor/ceil candidates + ±1 neighborhood, pick minimum distance. Tie-break: prefer smaller `(a, b)`.

Covering radius: `1/√3 ≈ 0.5774` (all cases verified ≤ this bound).
