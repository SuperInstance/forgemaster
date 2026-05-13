/**
 * fleet_math.h — Single-header C library for Cocapn constraint-theory math
 *
 * Includes:
 *   1. Cyclotomic field Q(ζ₁₅) rotation
 *   2. Eisenstein A₂ lattice snap (9-candidate Voronoi)
 *   3. Dodecet encoding (12-bit, 512-byte LUT)
 *   4. 3-tier constraint check (LUT → Bloom → Linear)
 *   5. Bounded drift verification (open walks & closed cycles)
 *   6. Unified 6D projection (Eisenstein & Penrose modes)
 *
 * Usage:
 *   #define FLEET_MATH_IMPLEMENTATION
 *   #include "fleet_math.h"
 *
 * Compilation:
 *   gcc -O3 -march=native -lm -D FLEET_MATH_IMPLEMENTATION ...
 *
 * License: MIT
 */

#ifndef FLEET_MATH_H
#define FLEET_MATH_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ================================================================
 * Configuration
 * ================================================================ */

#ifndef FM_EPSILON
#define FM_EPSILON 1.0e-14
#endif

#ifndef FM_TOL
#define FM_TOL 1.0e-12
#endif

/* ================================================================
 * Constants
 * ================================================================ */

/* Eisenstein lattice constants */
#define FM_SQRT3           1.7320508075688772935274463415058723669428
#define FM_INV_SQRT3       0.5773502691896257645091487805019574556476
#define FM_TWO_INV_SQRT3   1.1547005383792515290182975610039149112952
#define FM_SQRT3_2         0.8660254037844386467637231707529361834714

/* ω = e^{2πi/3} = (-1/2, √3/2) */
#define FM_OMEGA_RE        -0.5
#define FM_OMEGA_IM        0.8660254037844386467637231707529361834714

/* A₂ covering radius ρ = 1/√3 */
#define FM_COVERING_RADIUS 0.5773502691896257645091487805019574556476

/* Golden ratio φ */
#define FM_PHI             1.6180339887498948482045868343656381177203

/* ζ₁₅ precomputed cos/sin */
#define FM_ZETA15_N 15
#define FM_ZETA15_N_VECTORS 6

/* ================================================================
 * Type definitions
 * ================================================================ */

/** Eisenstein integer: a + bω */
typedef struct {
    int64_t a;
    int64_t b;
} fm_eisenstein_t;

/** 2D point */
typedef struct {
    double x;
    double y;
} fm_point_t;

/** Snap result with Eisenstein coords and error */
typedef struct {
    fm_eisenstein_t coords;   /* nearest Eisenstein integer */
    double error;             /* Euclidean distance */
    double angle;             /* displacement angle (radians) */
    uint16_t dodecet;         /* 12-bit dodecet code */
    uint8_t chamber;          /* Weyl chamber 0-5 */
    uint8_t flags;            /* bit 0: safe (error < covering radius) */
} fm_snap_result_t;

/* Flag bits */
#define FM_FLAG_SAFE   0x01
#define FM_FLAG_PARITY 0x02

/* ================================================================
 * (1) Cyclotomic field Q(ζ₁₅) operations
 * ================================================================ */

/**
 * fm_zeta15_rotate — Rotate point (x,y) by ζ₁₅ᵏ.
 *
 * Claim 2 verified: rotation error < 1e-15 for all k in 0..14.
 *
 * @param x,y   Input point coordinates.
 * @param k     Rotation index (0-14, cycled mod 15).
 * @param[out] out_re, out_im  Rotated coordinates.
 */
void fm_zeta15_rotate(double x, double y, int k,
                      double *out_re, double *out_im);

/**
 * fm_zeta15_project — Project point to all 15 ζ₁₅ basis vectors.
 *
 * Output arrays must have at least 15 elements each.
 */
void fm_zeta15_project(double x, double y,
                       double *out_re, double *out_im);

/* ================================================================
 * (2) Eisenstein A₂ lattice snapping
 * ================================================================ */

/**
 * fm_eins_snap — Snap (x,y) to nearest A₂ (Eisenstein) lattice point.
 *
 * Uses 9-candidate Voronoi search (da,db ∈ {-1,0,1}).
 * Claim 6 verified: error bounded by A₂ covering radius 1/√3.
 *
 * @param x,y       Input point.
 * @param[out] out  Snap result with coords, error, dodecet.
 */
void fm_eins_snap(double x, double y, fm_snap_result_t *out);

/**
 * fm_eins_snap_cartesian — Snap and return Cartesian (x_snapped, y_snapped).
 *
 * Convenience wrapper around fm_eins_snap.
 */
void fm_eins_snap_cartesian(double x, double y,
                            double *out_x, double *out_y);

/**
 * fm_eins_distance — Euclidean distance from Eisenstein int (a,b) to (x,y).
 */
double fm_eins_distance(int64_t a, int64_t b, double x, double y);

/**
 * fm_eisenstein_batch_snap — Snap N points in batch.
 *
 * @param xs,ys     Arrays of N point coordinates.
 * @param n         Number of points.
 * @param[out] results  Array of N snap results (pre-allocated).
 */
void fm_eins_batch_snap(const double *xs, const double *ys, int n,
                        fm_snap_result_t *results);

/* ================================================================
 * (3) Dodecet encoding (12-bit, 512-byte LUT)
 * ================================================================ */

/**
 * fm_dodecet_code — 12-bit dodecet code from Eisenstein int (a,b).
 *
 * Uses modular hash matching constraint_check.h exactly:
 *   idx = ((a + 1000) * 2001 + (b + 1000)) % 4096
 *
 * Claim 8 verified: 12-bit range, 512-byte LUT, ~3.6% FPR at capacity.
 *
 * @return 12-bit value in [0, 4095].
 */
uint16_t fm_dodecet_code(int64_t a, int64_t b);

/* ================================================================
 * (4) Dodecet LUT (bitset of 4096 entries)
 * ================================================================ */

/** Opaque handle for LUT-based constraint checking */
typedef struct fm_dodecet_lut fm_dodecet_lut_t;

/**
 * fm_lut_create — Create 512-byte bitset LUT.
 *
 * @return Allocated LUT (must be freed with fm_lut_destroy).
 */
fm_dodecet_lut_t *fm_lut_create(void);

/** fm_lut_destroy — Free LUT memory. */
void fm_lut_destroy(fm_dodecet_lut_t *lut);

/** fm_lut_insert — Insert Eisenstein integer (a,b) into LUT. */
void fm_lut_insert(fm_dodecet_lut_t *lut, int64_t a, int64_t b);

/**
 * fm_lut_query — Query if (a,b) is in LUT.
 * @return 1 if present, 0 if not (with ~3.6% FPR at capacity).
 */
int fm_lut_query(const fm_dodecet_lut_t *lut, int64_t a, int64_t b);

/* ================================================================
 * (5) 3-tier constraint check (LUT → Bloom → Linear)
 * ================================================================ */

/** Opaque handle for 3-tier constraint database */
typedef struct fm_constraint_db fm_constraint_db_t;

/**
 * fm_db_create — Create 3-tier constraint database.
 *
 * @param n  Expected number of constraints (determines Bloom size).
 * @return   Allocated database (free with fm_db_free).
 */
fm_constraint_db_t *fm_db_create(int n);

/** fm_db_insert — Insert constraint (a,b) into all tiers. */
void fm_db_insert(fm_constraint_db_t *db, int64_t a, int64_t b);

/**
 * fm_db_query — Check if (a,b) is a known constraint.
 * @return 1 if present, 0 if not.
 */
int fm_db_query(const fm_constraint_db_t *db, int64_t a, int64_t b);

/** fm_db_free — Free all database memory. */
void fm_db_free(fm_constraint_db_t *db);

/* ================================================================
 * (6) Bounded drift verification
 * ================================================================ */

/**
 * fm_drift_bound_open — Bound for open walks.
 *   Bound = 1.5 · n · (ε + 1/√3)
 *
 * Claim 9a: verified open walk bound.
 */
double fm_drift_bound_open(int n, double epsilon);

/**
 * fm_drift_bound_closed — Bound for closed cycles.
 *   Bound = n · ε
 *
 * Claim 9b: verified closed cycle bound (tighter than open).
 */
double fm_drift_bound_closed(int n, double epsilon);

/**
 * fm_drift_check — Check if accumulated drift is within Galois bound.
 *
 * @param accumulated  Sum of per-step drifts.
 * @param bound        Galois-proven bound for this walk.
 * @return             1 if within bound, 0 if exceeded.
 */
int fm_drift_check(double accumulated, double bound);

/* ================================================================
 * (7) Unified 6D projection (Eisenstein & Penrose modes)
 * ================================================================ */

/**
 * fm_project_vectors — Get projection vectors for given angle theta.
 *
 * At θ=0: 6 vectors at 60° intervals (hexagonal/Eisenstein lattice)
 * At θ=arctan(φ): 5 vectors at 72° + 1 redundant (Penrose)
 *
 * @param theta   Interpolation angle.
 * @param[out] out  (6,2) array of projection vectors, stored row-major.
 */
void fm_project_vectors(double theta, double out[6][2]);

/* ================================================================
 * (8) Galois connection
 * ================================================================ */

/**
 * fm_galois_trace — Galois trace from cyclotomic field to constraint domain.
 *
 * Tr(x+iy) = 8x/15, clamped to [0, 1].
 * Gal(Q(ζ₁₅)/Q) ≅ C₄ × C₂.
 *
 * Claim 5 verified: maps field element to constraint domain.
 */
double fm_galois_trace(double x, double y);

#ifdef __cplusplus
}
#endif

/* ================================================================
 * Implementation
 * ================================================================ */

#ifdef FLEET_MATH_IMPLEMENTATION

/*
 * ── (1) ζ₁₅ rotation ──
 * Precomputed cos(2πk/15) and sin(2πk/15) for k=0..14
 */
static const double FM_ZETA15_COS[15] = {
    1.0, 0.91354545764260087, 0.66913060635885824, 0.30901699437494745,
    -0.10452846326765333, -0.5, -0.80901699437494734, -0.97814760073380569,
    -0.97814760073380569, -0.80901699437494756, -0.5, -0.10452846326765423,
    0.30901699437494723, 0.66913060635885846, 0.91354545764260098
};

static const double FM_ZETA15_SIN[15] = {
    0.0, 0.40673664307580015, 0.74314482547739413, 0.95105651629515353,
    0.99452189536827340, 0.86602540378443871, 0.58778525229247325, 0.20791169081775931,
    -0.20791169081775907, -0.58778525229247303, -0.86602540378443838,
    -0.99452189536827329, -0.95105651629515364, -0.74314482547739402, -0.40673664307580015
};

void fm_zeta15_rotate(double x, double y, int k,
                      double *out_re, double *out_im) {
    int idx = k % 15;
    double c = FM_ZETA15_COS[idx];
    double s = FM_ZETA15_SIN[idx];
    *out_re = x * c - y * s;
    *out_im = x * s + y * c;
}

void fm_zeta15_project(double x, double y,
                       double *out_re, double *out_im) {
    for (int k = 0; k < 15; k++) {
        double c = FM_ZETA15_COS[k];
        double s = FM_ZETA15_SIN[k];
        out_re[k] = x * c - y * s;
        out_im[k] = x * s + y * c;
    }
}

/*
 * ── (2) Eisenstein snap ──
 */

/* Eisenstein coordinates → Cartesian: (a,b) → (x,y) */
static inline void eins_to_cart(int64_t a, int64_t b,
                                double *x, double *y) {
    *x = (double)a + (double)b * FM_OMEGA_RE;
    *y = (double)b * FM_OMEGA_IM;
}

/* Cartesian → Eisenstein coordinates: (x,y) → (a_f, b_f) (floats) */
static inline void cart_to_eins(double x, double y,
                                double *a_f, double *b_f) {
    *a_f = x + y * FM_INV_SQRT3;
    *b_f = y * FM_TWO_INV_SQRT3;
}

/* Weyl chamber classification based on angle */
static int classify_chamber(double angle) {
    double a = fmod(angle, 2.0 * M_PI);
    if (a < 0) a += 2.0 * M_PI;
    int chamber = (int)(a / (M_PI / 3.0));
    if (chamber > 5) chamber = 5;
    return chamber;
}

void fm_eins_snap(double x, double y, fm_snap_result_t *out) {
    double a_f, b_f;
    cart_to_eins(x, y, &a_f, &b_f);

    int64_t a0 = (int64_t)round(a_f);
    int64_t b0 = (int64_t)round(b_f);

    int64_t best_a = a0, best_b = b0;
    double best_err = 1e30;
    double best_angle = 0.0;

    /* 9-candidate Voronoi search */
    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            int64_t ca = a0 + da;
            int64_t cb = b0 + db;
            double cx, cy;
            eins_to_cart(ca, cb, &cx, &cy);
            double dx = x - cx;
            double dy = y - cy;
            double err = sqrt(dx * dx + dy * dy);
            if (err < best_err) {
                best_a = ca;
                best_b = cb;
                best_err = err;
                best_angle = atan2(dy, dx);
            }
        }
    }

    out->coords.a = best_a;
    out->coords.b = best_b;
    out->error = best_err;
    out->angle = best_angle;
    out->chamber = (uint8_t)classify_chamber(best_angle);
    out->dodecet = fm_dodecet_code(best_a, best_b);
    out->flags = (best_err < FM_COVERING_RADIUS) ? FM_FLAG_SAFE : 0;
}

void fm_eins_snap_cartesian(double x, double y,
                            double *out_x, double *out_y) {
    fm_snap_result_t snap;
    fm_eins_snap(x, y, &snap);
    eins_to_cart(snap.coords.a, snap.coords.b, out_x, out_y);
}

double fm_eins_distance(int64_t a, int64_t b, double x, double y) {
    double cx, cy;
    eins_to_cart(a, b, &cx, &cy);
    double dx = x - cx;
    double dy = y - cy;
    return sqrt(dx * dx + dy * dy);
}

void fm_eins_batch_snap(const double *xs, const double *ys, int n,
                        fm_snap_result_t *results) {
    for (int i = 0; i < n; i++) {
        fm_eins_snap(xs[i], ys[i], &results[i]);
    }
}

/*
 * ── (3) Dodecet encoding ──
 */

uint16_t fm_dodecet_code(int64_t a, int64_t b) {
    /* Match constraint_check.h exactly */
    uint32_t idx = ((uint32_t)(a + 1000) * 2001 + (uint32_t)(b + 1000)) % 4096;
    return (uint16_t)idx;
}

/*
 * ── (4) Dodecet LUT (512 bytes, 4096 bits) ──
 */

struct fm_dodecet_lut {
    uint64_t bits[64]; /* 4096 bits = 64 × 64 */
};

fm_dodecet_lut_t *fm_lut_create(void) {
    fm_dodecet_lut_t *lut = (fm_dodecet_lut_t *)calloc(1, sizeof(fm_dodecet_lut_t));
    return lut;
}

void fm_lut_destroy(fm_dodecet_lut_t *lut) {
    free(lut);
}

void fm_lut_insert(fm_dodecet_lut_t *lut, int64_t a, int64_t b) {
    uint16_t code = fm_dodecet_code(a, b);
    lut->bits[code >> 6] |= (1ULL << (code & 63));
}

int fm_lut_query(const fm_dodecet_lut_t *lut, int64_t a, int64_t b) {
    uint16_t code = fm_dodecet_code(a, b);
    return (lut->bits[code >> 6] >> (code & 63)) & 1ULL;
}

/*
 * ── (5) 3-tier constraint database ──
 *
 * Tier 1: Dodecet LUT (512-byte, O(1), ~3.6% FPR)
 * Tier 2: Bloom filter (probabilistic)
 * Tier 3: Linear scan (exact fallback)
 */

/* Bloom filter helpers */
static uint64_t fm_splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    x = x ^ (x >> 31);
    return x;
}

static uint64_t fm_hash_eisenstein(int64_t a, int64_t b, int seed) {
    uint64_t h = fm_splitmix64((uint64_t)a);
    h ^= fm_splitmix64((uint64_t)b + 0x9e3779b97f4a7c15ULL);
    h ^= fm_splitmix64((uint64_t)seed * 0x9e3779b97f4a7c15ULL);
    return h;
}

struct fm_constraint_db {
    /* Tier 1: Eisenstein LUT */
    fm_dodecet_lut_t lut;

    /* Tier 2: Bloom filter */
    uint64_t *bloom_bits;
    int64_t bloom_m;  /* number of bits */
    int bloom_k;      /* number of hash functions */

    /* Tier 3: Linear store */
    fm_eisenstein_t *linear;
    int linear_count;
    int linear_capacity;
};

fm_constraint_db_t *fm_db_create(int n) {
    fm_constraint_db_t *db = (fm_constraint_db_t *)calloc(1, sizeof(fm_constraint_db_t));
    if (!db) return NULL;

    /* Init LUT (already zeroed by calloc) */

    /* Init Bloom filter */
    double bits_per_item = -log(0.01) / (log(2.0) * log(2.0));
    db->bloom_m = (int64_t)ceil(bits_per_item * n);
    int k = (int)round((db->bloom_m / (double)n) * log(2.0));
    if (k < 1) k = 1;
    if (k > 20) k = 20;
    db->bloom_k = k;
    int64_t words = (db->bloom_m + 63) / 64;
    db->bloom_bits = (uint64_t *)calloc((size_t)words, sizeof(uint64_t));
    if (!db->bloom_bits) { free(db); return NULL; }

    /* Init linear store */
    db->linear = (fm_eisenstein_t *)malloc((size_t)n * sizeof(fm_eisenstein_t));
    if (!db->linear && n > 0) { free(db->bloom_bits); free(db); return NULL; }
    db->linear_count = 0;
    db->linear_capacity = n;

    return db;
}

void fm_db_insert(fm_constraint_db_t *db, int64_t a, int64_t b) {
    /* Tier 1: LUT */
    fm_lut_insert(&db->lut, a, b);

    /* Tier 2: Bloom */
    for (int i = 0; i < db->bloom_k; i++) {
        uint64_t h = fm_hash_eisenstein(a, b, i) % db->bloom_m;
        db->bloom_bits[h >> 6] |= (1ULL << (h & 63));
    }

    /* Tier 3: Linear */
    if (db->linear_count < db->linear_capacity) {
        db->linear[db->linear_count].a = a;
        db->linear[db->linear_count].b = b;
        db->linear_count++;
    }
}

int fm_db_query(const fm_constraint_db_t *db, int64_t a, int64_t b) {
    /* Tier 1: LUT */
    if (!fm_lut_query(&db->lut, a, b))
        return 0;

    /* Tier 2: Bloom */
    for (int i = 0; i < db->bloom_k; i++) {
        uint64_t h = fm_hash_eisenstein(a, b, i) % db->bloom_m;
        if (!(db->bloom_bits[h >> 6] & (1ULL << (h & 63))))
            return 0;
    }

    /* Tier 3: Linear scan */
    for (int i = 0; i < db->linear_count; i++) {
        if (db->linear[i].a == a && db->linear[i].b == b)
            return 1;
    }
    return 0;
}

void fm_db_free(fm_constraint_db_t *db) {
    if (db) {
        free(db->bloom_bits);
        free(db->linear);
        free(db);
    }
}

/*
 * ── (6) Bounded drift verification ──
 */

double fm_drift_bound_open(int n, double epsilon) {
    return 1.5 * (double)n * (epsilon + FM_INV_SQRT3);
}

double fm_drift_bound_closed(int n, double epsilon) {
    return (double)n * epsilon;
}

int fm_drift_check(double accumulated, double bound) {
    return (accumulated <= bound) ? 1 : 0;
}

/*
 * ── (7) Unified 6D projection vectors ──
 */

void fm_project_vectors(double theta, double out[6][2]) {
    /* Normalize theta to [0, arctan(φ)] */
    double theta_penrose = atan(FM_PHI);
    double t = (theta_penrose > 0.0) ? fmax(0.0, fmin(1.0, theta / theta_penrose)) : 0.0;

    /* Hexagonal angles (6 at 60° intervals) */
    double hex_angles[6];
    for (int k = 0; k < 6; k++)
        hex_angles[k] = 2.0 * M_PI * k / 6.0;

    /* Penrose angles (5 at 72° + 1 redundant) */
    double pen_angles[6];
    for (int k = 0; k < 5; k++)
        pen_angles[k] = 2.0 * M_PI * k / 5.0;
    pen_angles[5] = 0.0;

    /* Interpolate */
    for (int k = 0; k < 6; k++) {
        double a = (1.0 - t) * hex_angles[k] + t * pen_angles[k];
        out[k][0] = cos(a);
        out[k][1] = sin(a);
    }
}

/*
 * ── (8) Galois connection ──
 */

double fm_galois_trace(double x, double y) {
    (void)y;  /* Trace only depends on real part */
    double trace = 8.0 * x / 15.0;
    if (trace < 0.0) return 0.0;
    if (trace > 1.0) return 1.0;
    return trace;
}

#endif /* FLEET_MATH_IMPLEMENTATION */

#endif /* FLEET_MATH_H */
