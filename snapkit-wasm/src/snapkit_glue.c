/**
 * @file snapkit_glue.c
 * @brief WebAssembly exports for snapkit — Eisenstein lattice snap operations.
 *
 * Pure math, no libc dependencies beyond what the WASM runtime provides.
 * Compiles with: clang --target=wasm32 -nostdlib -O3 -Wl,--no-entry
 *                -Wl,--export=... -Wl,--import-memory -o snapkit.wasm
 *
 * All WASM-exported functions use the linear memory for batch/compound results.
 * Simple scalar returns use the two-return-value pattern via pointers or
 * encode results into a single f64 where needed.
 *
 * Memory layout (imported from JS):
 *   [0x0000 .. 0x00FF] — scratch / temp area
 *   [0x0100 .. ]       — batch input/output buffers
 *
 * Coordinate convention:
 *   Eisenstein integer (a, b) maps to Cartesian (a - b/2, b·√3/2)
 *   ω = e^(2πi/3) = -1/2 + i√3/2
 */

#include <math.h>

/* ---------------------------------------------------------------------------
 * Constants (precomputed)
 * ------------------------------------------------------------------------- */

#define SQRT3       1.7320508075688772
#define INV_SQRT3   0.5773502691896258
#define HALF_SQRT3  0.8660254037844386
#define COVERING_R  0.5773502691896258  /* 1/√3 */

/* Imported linear memory — JS allocates and passes this */
extern char __heap_base;

/* ---------------------------------------------------------------------------
 * Internal: Optimal O(1) Eisenstein snap (branchless Voronoi correction)
 *
 * After rounding to the nearest Eisenstein integer, we extract the
 * fractional parts (u, v) ∈ [-0.5, 0.5]² and check 4 Voronoi
 * boundary conditions plus 2 corner cases.
 *
 * The 6 correction regions are mutually exclusive (they partition the
 * 6 triangular corners of the hexagonal Voronoi cell that extend beyond
 * the rounding square).
 * ------------------------------------------------------------------------- */

static void _eisenstein_snap_internal(double x, double y,
                                       int* out_a, int* out_b,
                                       double* out_dist) {
    /* Basis conversion: z = x+iy = a + bω */
    double b_float = 2.0 * y * INV_SQRT3;
    double a_float = x + y * INV_SQRT3;

    int ia = (int)round(a_float);
    int ib = (int)round(b_float);

    double u = a_float - (double)ia;
    double v = b_float - (double)ib;

    /* Voronoi boundary conditions */
    double c1 = 2.0 * u - v;          /* > 1 → correct +1,0 */
    double c2 = v - 2.0 * u;          /* > 1 → correct -1,0 */
    double c3 = 2.0 * v - u;          /* > 1 → correct 0,+1 */
    double c4 = u - 2.0 * v;          /* > 1 → correct 0,-1 */
    double uv = u + v;

    int da = 0, db = 0;

    if (c1 > 1.0 && c4 > 1.0) {
        /* Corner near (0.5, -0.5) */
        if (uv > 0.0) { da =  1; db =  0; }
        else          { da =  0; db = -1; }
    } else if (c2 > 1.0 && c3 > 1.0) {
        /* Corner near (-0.5, 0.5) */
        if (uv > 0.0) { da =  0; db =  1; }
        else          { da = -1; db =  0; }
    } else if (c1 > 1.0) { da =  1; db =  0; }
    else if (c2 > 1.0)   { da = -1; db =  0; }
    else if (c3 > 1.0)   { da =  0; db =  1; }
    else if (c4 > 1.0)   { da =  0; db = -1; }

    ia += da;
    ib += db;

    /* Distance via Eisenstein norm of residual (avoids Cartesian remap) */
    double uc = u - (double)da;
    double vc = v - (double)db;
    double d2 = uc * uc - uc * vc + vc * vc;

    *out_a = ia;
    *out_b = ib;
    *out_dist = sqrt(d2);
}

/* ---------------------------------------------------------------------------
 * Internal: 3×3 neighborhood snap (guaranteed nearest, used for Voronoï)
 * ------------------------------------------------------------------------- */

static void _eisenstein_snap_voronoi_internal(double x, double y,
                                                int* out_a, int* out_b,
                                                double* out_dist) {
    double b0 = round(2.0 * y * INV_SQRT3);
    double a0 = round(x + b0 * 0.5);

    int best_a = (int)a0, best_b = (int)b0;
    double best_d2 = 1e300;

    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            int ca = (int)a0 + da;
            int cb = (int)b0 + db;
            double cx = (double)ca - (double)cb * 0.5;
            double cy = (double)cb * HALF_SQRT3;
            double dx = x - cx;
            double dy = y - cy;
            double d2 = dx * dx + dy * dy;
            if (d2 < best_d2) {
                best_d2 = d2;
                best_a = ca;
                best_b = cb;
            }
        }
    }

    *out_a = best_a;
    *out_b = best_b;
    *out_dist = sqrt(best_d2);
}

/* ===========================================================================
 * WASM EXPORTED FUNCTIONS
 *
 * Return convention: for functions returning (a, b) pairs, we write the
 * result to a caller-provided pointer in linear memory. The JS wrapper
 * handles reading from the shared buffer.
 *
 * All pointers are byte offsets into WASM linear memory.
 * =========================================================================== */

/**
 * Eisenstein snap (optimal O(1) Voronoi correction).
 * Writes {a: i32, b: i32, snapped_x: f64, snapped_y: f64, dist: f64}
 * to result_ptr (28 bytes).
 */
__attribute__((visibility("default")))
void eisenstein_snap(double x, double y, int result_ptr) {
    int* out_a  = (int*)(result_ptr);
    int* out_b  = (int*)(result_ptr + 4);
    double* out_sx = (double*)(result_ptr + 8);   /* 8-byte aligned after 8 bytes */
    double* out_sy = (double*)(result_ptr + 16);
    double* out_d  = (double*)(result_ptr + 24);

    int a, b;
    double dist;
    _eisenstein_snap_internal(x, y, &a, &b, &dist);

    *out_a = a;
    *out_b = b;
    *out_sx = (double)a - (double)b * 0.5;
    *out_sy = (double)b * HALF_SQRT3;
    *out_d = dist;
}

/**
 * Eisenstein snap with guaranteed Voronoï nearest neighbor (3×3 search).
 * Same output layout as eisenstein_snap.
 */
__attribute__((visibility("default")))
void eisenstein_snap_voronoi(double x, double y, int result_ptr) {
    int* out_a  = (int*)(result_ptr);
    int* out_b  = (int*)(result_ptr + 4);
    double* out_sx = (double*)(result_ptr + 8);
    double* out_sy = (double*)(result_ptr + 16);
    double* out_d  = (double*)(result_ptr + 24);

    int a, b;
    double dist;
    _eisenstein_snap_voronoi_internal(x, y, &a, &b, &dist);

    *out_a = a;
    *out_b = b;
    *out_sx = (double)a - (double)b * 0.5;
    *out_sy = (double)b * HALF_SQRT3;
    *out_d = dist;
}

/**
 * Batch Eisenstein snap.
 * Input:  interleaved [x0, y0, x1, y1, ...] at in_ptr, len points (2*len f64s)
 * Output: at out_ptr, len × {i32 a, i32 b, f64 sx, f64 sy, f64 d} = 32 bytes each
 *         (padded to 32 for alignment)
 */
__attribute__((visibility("default")))
void eisenstein_snap_batch(int in_ptr, int len, int out_ptr) {
    double* in  = (double*)in_ptr;
    /* Each output: a(i32) b(i32) pad(i32,i32) sx(f64) sy(f64) d(f64) = 32 bytes */
    /* Simpler: a(i32) b(i32) then f64 sx, sy, d = 28 bytes, but let's use 32 for alignment */
    for (int i = 0; i < len; i++) {
        double x = in[i * 2];
        double y = in[i * 2 + 1];

        int base = out_ptr + i * 32;
        int a, b;
        double dist;
        _eisenstein_snap_internal(x, y, &a, &b, &dist);

        *(int*)(base)      = a;
        *(int*)(base + 4)  = b;
        *(double*)(base + 8)  = (double)a - (double)b * 0.5;
        *(double*)(base + 16) = (double)b * HALF_SQRT3;
        *(double*)(base + 24) = dist;
    }
}

/**
 * Returns the covering radius of the A₂ (Eisenstein) lattice: 1/√3 ≈ 0.57735.
 */
__attribute__((visibility("default")))
double covering_radius(void) {
    return COVERING_R;
}

/**
 * Beat grid temporal snap.
 * Snaps time t to the nearest beat in a periodic grid defined by period.
 * Result written to result_ptr: {snapped_t: f64, offset: f64, beat_index: i32, phase: f64}
 * = 28 bytes.
 */
__attribute__((visibility("default")))
void beat_grid_snap(double t, double period, int result_ptr) {
    double inv_period = 1.0 / period;
    double adjusted = t * inv_period;
    int beat_index = (int)round(adjusted);
    double snapped_t = (double)beat_index * period;
    double offset = t - snapped_t;

    /* Phase in [0, 1) */
    double phase = adjusted - floor(adjusted);
    if (phase < 0.0) phase += 1.0;

    *(double*)(result_ptr)      = snapped_t;
    *(double*)(result_ptr + 8)  = offset;
    *(int*)(result_ptr + 16)    = beat_index;
    *(double*)(result_ptr + 20) = phase;
}

/**
 * Batch beat grid snap.
 * Input:  [t0, t1, ...] at in_ptr, len f64s
 * Output: at out_ptr, len × {f64 snapped, f64 offset, i32 index, f64 phase} = 24 bytes each
 */
__attribute__((visibility("default")))
void beat_grid_snap_batch(int in_ptr, int len, double period, int out_ptr) {
    double* in = (double*)in_ptr;
    double inv_period = 1.0 / period;

    for (int i = 0; i < len; i++) {
        double t = in[i];
        double adjusted = t * inv_period;
        int beat_index = (int)round(adjusted);
        double snapped_t = (double)beat_index * period;
        double offset = t - snapped_t;
        double phase = adjusted - floor(adjusted);
        if (phase < 0.0) phase += 1.0;

        int base = out_ptr + i * 24;
        *(double*)(base)      = snapped_t;
        *(double*)(base + 8)  = offset;
        *(int*)(base + 16)    = beat_index;
        *(double*)(base + 20) = phase;
    }
}

/**
 * Allocate memory (simple bump allocator for WASM).
 * Returns pointer to len bytes of linear memory.
 */
__attribute__((visibility("default")))
int wasm_alloc(int len) {
    static int heap_offset = 65536; /* Start after 64KB */
    int ptr = heap_offset;
    heap_offset += len;
    /* Align to 8 bytes */
    heap_offset = (heap_offset + 7) & ~7;
    return ptr;
}
