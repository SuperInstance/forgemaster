# fleet-math-c

Single-header C library for Cocapn constraint-theory math: Q(ζ₁₅) cyclotomic
field operations, Eisenstein lattice snapping, and 3-tier constraint checking.

## Features

1. **Cyclotomic field Q(ζ₁₅)** — ζ₁₅ rotation (verified error < 1e-15)
2. **Eisenstein A₂ lattice snap** — 9-candidate Voronoi search, error ≤ 1/√3
3. **Dodecet encoding** — 12-bit modular hash (512-byte LUT, ~3.6% FPR)
4. **3-tier constraint check** — LUT → Bloom filter → Linear fallback
5. **Bounded drift verification** — Galois-proven bounds for open/closed walks
6. **Unified 6D projection** — Eisenstein (θ=0) and Penrose (θ=arctan(φ)) modes
7. **Galois connection** — maps cyclotomic field to constraint domain [0,1]

## Quick Start

```c
#define FLEET_MATH_IMPLEMENTATION
#include "fleet_math.h"
#include <stdio.h>

int main(void) {
    // Snap to nearest A₂ lattice point
    fm_snap_result_t snap;
    fm_eins_snap(1.5, 2.3, &snap);
    printf("Snapped to: (%ld, %ld), error=%f\n",
           (long)snap.coords.a, (long)snap.coords.b, snap.error);

    // Dodecet encoding
    uint16_t code = fm_dodecet_code(snap.coords.a, snap.coords.b);

    // LUT-based constraint check
    fm_dodecet_lut_t *lut = fm_lut_create();
    fm_lut_insert(lut, 3, 5);
    printf("(3,5) in LUT: %d\n", fm_lut_query(lut, 3, 5));
    fm_lut_destroy(lut);

    // 3-tier database
    fm_constraint_db_t *db = fm_db_create(1000);
    fm_db_insert(db, 3, 5);
    printf("Query: %d\n", fm_db_query(db, 3, 5));
    fm_db_free(db);

    // ζ₁₅ rotation
    double rx, ry;
    fm_zeta15_rotate(1.0, 0.0, 3, &rx, &ry);

    // Drift bounds
    double bound = fm_drift_bound_open(100, 1e-15);
    printf("Open walk bound: %g\n", bound);

    return 0;
}
```

## Compilation

```bash
gcc -O3 -march=native -lm -D FLEET_MATH_IMPLEMENTATION -o my_prog my_prog.c
```

Or use the Makefile:
```bash
make          # Build test binary
make test     # Build and run tests
```

## API Reference

### Cyclotomic Field
- `fm_zeta15_rotate(x, y, k, *out_re, *out_im)` — Rotate by ζ₁₅ᵏ (Claim 2)
- `fm_zeta15_project(x, y, *out_re, *out_im)` — Project to all 15 basis vectors

### Eisenstein Snap
- `fm_eins_snap(x, y, *out)` — Snap to nearest A₂ lattice point (Claim 6)
- `fm_eins_snap_cartesian(x, y, *out_x, *out_y)` — Convenience wrapper
- `fm_eins_distance(a, b, x, y)` — Distance from Eisenstein int to point
- `fm_eins_batch_snap(xs, ys, n, results)` — Batch snap N points

### Dodecet
- `fm_dodecet_code(a, b)` — 12-bit hash code (Claim 8)
- `fm_lut_create/destroy/insert/query` — 512-byte bitset LUT

### Constraint Check
- `fm_db_create/insert/query/free` — 3-tier (LUT→Bloom→Linear)

### Drift
- `fm_drift_bound_open(n, epsilon)` — Open walk bound (Claim 9a)
- `fm_drift_bound_closed(n, epsilon)` — Closed cycle bound (Claim 9b)
- `fm_drift_check(accumulated, bound)` — Check against Galois bound

### Projection
- `fm_project_vectors(theta, out[6][2])` — Unified 6D projection vectors (Claim 7)

### Galois
- `fm_galois_trace(x, y)` — Trace to constraint domain [0,1] (Claim 5)

## License

MIT

## Repository

https://github.com/SuperInstance/fleet-math-c
