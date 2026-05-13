/**
 * constraint_avx512.c — AVX-512 Optimized Constraint Checking Engine
 *
 * Benchmarks 5 operations on AMD Ryzen AI 9 HX 370 (full AVX-512):
 *   a) Eisenstein snap (scalar / AVX2 / AVX-512)
 *   b) Dodecet encoding (scalar / AVX-512)
 *   c) Bounded drift holonomy check (scalar / AVX-512)
 *   d) Cyclotomic field projection (scalar / AVX-512)
 *   e) 3-tier constraint checking (Eisenstein LUT -> Bloom -> Linear cascade)
 *
 * Compile:
 *   gcc -O3 -march=native -o constraint_avx512 constraint_avx512.c -lm
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>
#include <stdalign.h>
#include <immintrin.h>

/* ===== Configuration ===== */
#define WARMUP_OPS      100000
#define EISENSTEIN_OPS  10000000
#define DODECET_OPS     10000000
#define HOLONOMY_CYCLES 100000
#define HOLONOMY_LEN    10
#define PROJECTION_OPS  10000000
#define CONSTRAINT_OPS  10000000
#define CONSTRAINT_NUM  10000

/* ===== Aligned allocator ===== */
static inline void *aligned_alloc64(size_t bytes) {
    void *p;
    if (posix_memalign(&p, 64, bytes)) return NULL;
    memset(p, 0, bytes);
    return p;
}

/* ===== Random helpers ===== */
static uint64_t rng_state = 0xDEADBEEFCAFEBABEULL;
static inline uint64_t rng_u64(void) {
    rng_state ^= rng_state >> 12;
    rng_state ^= rng_state << 25;
    rng_state ^= rng_state >> 27;
    return rng_state * 0x2545F4914F6CDD1DULL;
}
static inline double rng_double(void) {
    return (double)(rng_u64() >> 11) / (double)(1ULL << 53);
}
static inline double rng_signed(void) {
    return rng_double() * 2.0 - 1.0;
}

/* ===== Timer ===== */
static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

/* =========================================================================
 * (a) Eisenstein Snap
 * ========================================================================= */

static void eisenstein_snap_scalar(double x, double y,
                                    double *out_x, double *out_y) {
    const double inv_sqrt3 = 0.5773502691896257645091487805019574556476;
    const double sqrt3_2 = 0.8660254037844386467637231707529361834714;
    double a = x - y * inv_sqrt3;
    double b = y * 2.0 * inv_sqrt3;
    long ai = (long)round(a);
    long bi = (long)round(b);

    if (((ai ^ bi) & 1) != 0) {
        double da1 = a - (ai + 1); double db1 = b - bi;
        double d1 = da1*da1 + db1*db1;
        double da2 = a - (ai - 1); double db2 = b - bi;
        double d2 = da2*da2 + db2*db2;
        double da3 = a - ai; double db3 = b - (bi + 1);
        double d3 = da3*da3 + db3*db3;
        double da4 = a - ai; double db4 = b - (bi - 1);
        double d4 = da4*da4 + db4*db4;

        double min_d = d1;
        long best_a = ai + 1, best_b = bi;
        if (d2 < min_d) { min_d = d2; best_a = ai - 1; best_b = bi; }
        if (d3 < min_d) { min_d = d3; best_a = ai; best_b = bi + 1; }
        if (d4 < min_d) { min_d = d4; best_a = ai; best_b = bi - 1; }
        ai = best_a; bi = best_b;
    }
    *out_x = (double)ai + (double)bi * 0.5;
    *out_y = (double)bi * sqrt3_2;
}

static void eisenstein_snap_avx2(const double *xs, const double *ys,
                                  double *out_xs, double *out_ys, int n) {
    const double inv_sqrt3 = 0.5773502691896257645091487805019574556476;
    const double sqrt3_2 = 0.8660254037844386467637231707529361834714;
    const double two_inv_sqrt3 = 2.0 * inv_sqrt3;
    __m256d inv_sqrt3_v = _mm256_set1_pd(inv_sqrt3);
    __m256d sqrt3_2_v = _mm256_set1_pd(sqrt3_2);
    __m256d two_inv_sqrt3_v = _mm256_set1_pd(two_inv_sqrt3);
    __m256d half_v = _mm256_set1_pd(0.5);

    int i = 0;
    for (; i + 4 <= n; i += 4) {
        __m256d xv = _mm256_loadu_pd(&xs[i]);
        __m256d yv = _mm256_loadu_pd(&ys[i]);

        __m256d a_v = _mm256_sub_pd(xv, _mm256_mul_pd(yv, inv_sqrt3_v));
        __m256d b_v = _mm256_mul_pd(yv, two_inv_sqrt3_v);

        /* Round to nearest int32, store as packed int64 */
        __m128i ai32 = _mm256_cvtpd_epi32(_mm256_round_pd(a_v, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC));
        __m128i bi32 = _mm256_cvtpd_epi32(_mm256_round_pd(b_v, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC));
        __m256i ai = _mm256_cvtepi32_epi64(ai32);
        __m256i bi = _mm256_cvtepi32_epi64(bi32);

        /* Parity check */
        __m256i par = _mm256_and_si256(_mm256_xor_si256(ai, bi), _mm256_set1_epi64x(1));
        int need_fix = _mm256_movemask_pd(_mm256_castsi256_pd(_mm256_cmpeq_epi64(par, _mm256_set1_epi64x(1))));

        if (need_fix) {
            for (int j = 0; j < 4; j++)
                eisenstein_snap_scalar(xs[i+j], ys[i+j], &out_xs[i+j], &out_ys[i+j]);
        } else {
            /* Convert int64 back to double */
            alignas(32) int64_t ai_a[4], bi_a[4];
            _mm256_store_si256((__m256i*)ai_a, ai);
            _mm256_store_si256((__m256i*)bi_a, bi);
            for (int j = 0; j < 4; j++) {
                out_xs[i+j] = (double)ai_a[j] + (double)bi_a[j] * 0.5;
                out_ys[i+j] = (double)bi_a[j] * sqrt3_2;
            }
        }
    }
    for (; i < n; i++)
        eisenstein_snap_scalar(xs[i], ys[i], &out_xs[i], &out_ys[i]);
}

static void eisenstein_snap_avx512(const double *xs, const double *ys,
                                    double *out_xs, double *out_ys, int n) {
    const double inv_sqrt3 = 0.5773502691896257645091487805019574556476;
    const double sqrt3_2 = 0.8660254037844386467637231707529361834714;
    const double two_inv_sqrt3 = 2.0 * inv_sqrt3;

    int i = 0;
    for (; i + 8 <= n; i += 8) {
        __m512d xv = _mm512_loadu_pd(&xs[i]);
        __m512d yv = _mm512_loadu_pd(&ys[i]);

        __m512d a_v = _mm512_sub_pd(xv, _mm512_mul_pd(yv, _mm512_set1_pd(inv_sqrt3)));
        __m512d b_v = _mm512_mul_pd(yv, _mm512_set1_pd(two_inv_sqrt3));

        __m512i ai = _mm512_cvt_roundpd_epi64(a_v, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
        __m512i bi = _mm512_cvt_roundpd_epi64(b_v, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);

        __m512i parity = _mm512_and_epi64(_mm512_xor_epi64(ai, bi), _mm512_set1_epi64(1));
        __mmask8 need_fix = _mm512_cmpneq_epi64_mask(parity, _mm512_setzero_si512());

        if (need_fix) {
            for (int j = 0; j < 8; j++) {
                if ((need_fix >> j) & 1)
                    eisenstein_snap_scalar(xs[i+j], ys[i+j], &out_xs[i+j], &out_ys[i+j]);
                else {
                    int64_t aij = ((int64_t*)&ai)[j];
                    int64_t bij = ((int64_t*)&bi)[j];
                    out_xs[i+j] = (double)aij + (double)bij * 0.5;
                    out_ys[i+j] = (double)bij * sqrt3_2;
                }
            }
        } else {
            __m512d outx = _mm512_add_pd(_mm512_cvtepi64_pd(ai),
                            _mm512_mul_pd(_mm512_cvtepi64_pd(bi), _mm512_set1_pd(0.5)));
            __m512d outy = _mm512_mul_pd(_mm512_cvtepi64_pd(bi), _mm512_set1_pd(sqrt3_2));
            _mm512_storeu_pd(&out_xs[i], outx);
            _mm512_storeu_pd(&out_ys[i], outy);
        }
    }
    for (; i < n; i++)
        eisenstein_snap_scalar(xs[i], ys[i], &out_xs[i], &out_ys[i]);
}

/* =========================================================================
 * (b) Dodecet encoding — compute 12-element code
 * ========================================================================= */
static const double dodecet_phases[12] = {
    0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0
};

static void dodecet_scalar(double x, double y, uint8_t code[12]) {
    for (int j = 0; j < 12; j++) {
        int64_t v = (int64_t)(x + dodecet_phases[j]) ^ (int64_t)(y + dodecet_phases[j]);
        int64_t m = v % 12;
        if (m < 0) m += 12;
        code[j] = (uint8_t)m;
    }
}

/* Compute abs(xor) mod 12 using Goldberg division by invariant integer */
static inline int32_t mod12_int32(int32_t v) {
    int32_t ax = (v < 0) ? -v : v;
    /* ax / 12 using multiply-high: (ax * 0xAAAAAAAB) >> 33 */
    uint32_t q = ((uint64_t)(uint32_t)ax * (uint64_t)0xAAAAAAABULL) >> 33;
    return ax - q * 12;
}

static void dodecet_avx512(const double *xs, const double *ys,
                            uint8_t *codes, int n) {
    /* Batch across 8 points for each of the 12 phases */
    for (int j = 0; j < 12; j++) {
        double phase = dodecet_phases[j];
        __m512d phasev = _mm512_set1_pd(phase);
        int i = 0;
        for (; i + 8 <= n; i += 8) {
            __m512d xp = _mm512_add_pd(_mm512_loadu_pd(&xs[i]), phasev);
            __m512d yp = _mm512_add_pd(_mm512_loadu_pd(&ys[i]), phasev);
            __m512i xi = _mm512_cvttpd_epi64(xp);
            __m512i yi = _mm512_cvttpd_epi64(yp);
            __m512i xo = _mm512_xor_epi64(xi, yi);

            /* Narrow to 32-bit lane SIMD mod 12 */
            alignas(64) int64_t xo_arr[8];
            _mm512_store_epi64(xo_arr, xo);
            for (int k = 0; k < 8; k++) {
                int64_t v = xo_arr[k];
                int64_t m = v % 12;
                if (m < 0) m += 12;
                codes[(i+k)*12 + j] = (uint8_t)m;
            }
        }
        for (; i < n; i++) {
            int64_t v = (int64_t)(xs[i] + phase) ^ (int64_t)(ys[i] + phase);
            int64_t m = v % 12;
            if (m < 0) m += 12;
            codes[i*12 + j] = (uint8_t)m;
        }
    }
}

/* =========================================================================
 * (c) Bounded drift holonomy check
 *     Walk HOLONOMY_LEN steps per cycle. Store drifts in SIMD-friendly
 *     layout: array of HOLONOMY_LEN x [ncycles doubles].
 * ========================================================================= */

/* Scalar: drifts[c*len + t] — one cycle's data contiguous */
static int holonomy_scalar(const double *drifts, int len, double bound) {
    double angle = 0.0;
    for (int i = 0; i < len; i++) {
        angle += drifts[i];
        if (fabs(angle) > bound) return 0;
    }
    return 1;
}

/* AVX-512: drifts[t * ncycles + c] — SIMD-friendly: one step of all cycles contiguous.
 * batch 8 cycles. */
static void holonomy_avx512(const double *drifts, int len, int ncycles,
                             double bound, int *results) {
    __m512d bound_v = _mm512_set1_pd(bound);
    int i = 0;
    for (; i + 8 <= ncycles; i += 8) {
        __m512d angles = _mm512_setzero_pd();
        __mmask8 failed = 0;
        for (int t = 0; t < len; t++) {
            __m512d dr = _mm512_loadu_pd(&drifts[t * ncycles + i]);
            angles = _mm512_add_pd(angles, dr);
            __mmask8 exceeded = _mm512_cmp_pd_mask(_mm512_abs_pd(angles), bound_v, _CMP_GT_OQ);
            failed |= exceeded;
        }
        for (int k = 0; k < 8; k++)
            results[i + k] = ((failed >> k) & 1) ? 0 : 1;
    }
    for (; i < ncycles; i++) {
        double angle = 0.0;
        int ok = 1;
        for (int t = 0; t < len && ok; t++) {
            angle += drifts[t * ncycles + i];
            if (fabs(angle) > bound) ok = 0;
        }
        results[i] = ok;
    }
}

/* =========================================================================
 * (d) Cyclotomic field projection
 * ========================================================================= */
#define ZETA15_N 15

static const double zeta15_cos[15] = {
    1.0, 0.91354546, 0.66913061, 0.30901699, -0.10452846,
    -0.5, -0.80901699, -0.9781476, -0.9781476, -0.80901699,
    -0.5, -0.10452846, 0.30901699, 0.66913061, 0.91354546
};
static const double zeta15_sin[15] = {
    0.0, 0.40673664, 0.74314483, 0.95105652, 0.9945219,
    0.8660254, 0.58778525, 0.20791169, -0.20791169, -0.58778525,
    -0.8660254, -0.9945219, -0.95105652, -0.74314483, -0.40673664
};

static void projection_scalar(const double *xs, const double *ys,
                               double *out_re, double *out_im, int n) {
    for (int i = 0; i < n; i++) {
        double x = xs[i], y = ys[i];
        for (int k = 0; k < ZETA15_N; k++) {
            out_re[k * n + i] = x * zeta15_cos[k] - y * zeta15_sin[k];
            out_im[k * n + i] = x * zeta15_sin[k] + y * zeta15_cos[k];
        }
    }
}

static void projection_avx512(const double *xs, const double *ys,
                               double *out_re, double *out_im, int n) {
    int i = 0;
    for (; i + 8 <= n; i += 8) {
        __m512d xv = _mm512_loadu_pd(&xs[i]);
        __m512d yv = _mm512_loadu_pd(&ys[i]);
        for (int k = 0; k < ZETA15_N; k++) {
            __m512d cosk = _mm512_set1_pd(zeta15_cos[k]);
            __m512d sink = _mm512_set1_pd(zeta15_sin[k]);
            __m512d re = _mm512_sub_pd(_mm512_mul_pd(xv, cosk), _mm512_mul_pd(yv, sink));
            __m512d im = _mm512_add_pd(_mm512_mul_pd(xv, sink), _mm512_mul_pd(yv, cosk));
            _mm512_storeu_pd(&out_re[k * n + i], re);
            _mm512_storeu_pd(&out_im[k * n + i], im);
        }
    }
    for (; i < n; i++) {
        double x = xs[i], y = ys[i];
        for (int k = 0; k < ZETA15_N; k++) {
            out_re[k * n + i] = x * zeta15_cos[k] - y * zeta15_sin[k];
            out_im[k * n + i] = x * zeta15_sin[k] + y * zeta15_cos[k];
        }
    }
}

/* =========================================================================
 * (e) 3-tier constraint checking
 * ========================================================================= */
typedef struct {
    uint64_t *bloom_filter;
    int bloom_size;
    int num_hash;
    double *linear_coeffs;
    int linear_n;
} ConstraintSet;

static ConstraintSet *constraint_create(int n, int bloom_size_bits) {
    ConstraintSet *cs = calloc(1, sizeof(ConstraintSet));
    cs->bloom_size = 1 << bloom_size_bits;
    cs->bloom_filter = aligned_alloc64(cs->bloom_size / 8);
    cs->num_hash = 4;
    cs->linear_coeffs = aligned_alloc64(n * sizeof(double));
    cs->linear_n = n;

    for (int i = 0; i < n; i++)
        cs->linear_coeffs[i] = rng_signed();

    for (int i = 0; i < n; i++) {
        double c = cs->linear_coeffs[i];
        uint64_t h = (uint64_t)(fabs(c) * 1e15);
        for (int hc = 0; hc < cs->num_hash; hc++) {
            uint64_t bit = (h ^ (hc * 0x9E3779B97F4A7C15ULL)) & (cs->bloom_size - 1);
            cs->bloom_filter[bit / 64] |= (1ULL << (bit % 64));
        }
    }
    return cs;
}

static inline int constraint_check_scalar(ConstraintSet *cs, double x, double y) {
    uint64_t h = (uint64_t)(fabs(x + y * 1337.0) * 1e12);
    uint64_t h0 = h ^ 0xDEADBEEF;
    for (int hc = 0; hc < cs->num_hash; hc++) {
        uint64_t bit = (h0 ^ (hc * 0x9E3779B97F4A7C15ULL)) & (cs->bloom_size - 1);
        if (!(cs->bloom_filter[bit / 64] & (1ULL << (bit % 64))))
            return 0;
    }
    for (int i = 0; i < cs->linear_n; i++) {
        double dx = x - cs->linear_coeffs[i];
        double dy = y - cs->linear_coeffs[(i + 1) % cs->linear_n];
        if (dx * dx + dy * dy < 0.01) return 1;
    }
    return 0;
}

static void constraint_check_avx512(ConstraintSet *cs,
                                     const double *xs, const double *ys,
                                     int *results, int n) {
    int i = 0;
    for (; i + 8 <= n; i += 8) {
        int pass[8];
        for (int j = 0; j < 8; j++) pass[j] = 1;
        for (int hc = 0; hc < cs->num_hash; hc++) {
            uint64_t h0_arr[8];
            for (int j = 0; j < 8; j++) {
                uint64_t h = (uint64_t)(fabs(xs[i+j] + ys[i+j] * 1337.0) * 1e12);
                h0_arr[j] = h ^ 0xDEADBEEF;
            }
            /* Compute 8 bit indices at once with xor and AND mask */
            alignas(64) uint64_t bits[8];
            for (int j = 0; j < 8; j++)
                bits[j] = (h0_arr[j] ^ (hc * 0x9E3779B97F4A7C15ULL)) & (cs->bloom_size - 1);
            /* Check bloom filter */
            for (int j = 0; j < 8; j++) {
                if (!pass[j]) continue;
                uint64_t w = bits[j] / 64;
                uint64_t b = bits[j] % 64;
                if (!(cs->bloom_filter[w] & (1ULL << b)))
                    pass[j] = 0;
            }
        }
        for (int j = 0; j < 8; j++) {
            if (pass[j])
                results[i+j] = constraint_check_scalar(cs, xs[i+j], ys[i+j]);
            else
                results[i+j] = 0;
        }
    }
    for (; i < n; i++)
        results[i] = constraint_check_scalar(cs, xs[i], ys[i]);
}

/* =========================================================================
 * Benchmark harness
 * ========================================================================= */

static double run_benchmark(const char *name, void (*func)(void),
                             int ops, int warmup) {
    for (int i = 0; i < warmup; i++) func();
    double t0 = now_seconds();
    for (int i = 0; i < ops; i++) func();
    double t1 = now_seconds();
    double elapsed = t1 - t0;
    double throughput = (double)ops / elapsed;
    printf("  %-45s  %8.2f ms  %12.0f ops/sec\n",
           name, elapsed * 1000.0, throughput);
    return throughput;
}

/* Global test data */
static double *g_xs, *g_ys, *g_ox, *g_oy;
static int g_n;
static uint8_t *g_codes;
static double *g_drifts;
static int *g_results;
static ConstraintSet *g_cs;

/* --- Eisenstein snap wrappers --- */
static void wrap_eisen_scalar(void) {
    for (int i = 0; i < g_n; i++)
        eisenstein_snap_scalar(g_xs[i], g_ys[i], &g_ox[i], &g_oy[i]);
}
static void wrap_eisen_avx2(void) {
    eisenstein_snap_avx2(g_xs, g_ys, g_ox, g_oy, g_n);
}
static void wrap_eisen_avx512(void) {
    eisenstein_snap_avx512(g_xs, g_ys, g_ox, g_oy, g_n);
}

/* --- Dodecet wrappers --- */
static void wrap_dodecet_scalar(void) {
    uint8_t code[12];
    for (int i = 0; i < g_n; i++) {
        dodecet_scalar(g_xs[i], g_ys[i], code);
        memcpy(&g_codes[i*12], code, 12);
    }
}
static void wrap_dodecet_avx512(void) {
    dodecet_avx512(g_xs, g_ys, g_codes, g_n);
}

/* --- Holonomy wrappers --- */
static void wrap_holo_scalar(void) {
    for (int i = 0; i < HOLONOMY_CYCLES; i++)
        g_results[i] = holonomy_scalar(&g_drifts[i * HOLONOMY_LEN], HOLONOMY_LEN, 1.0);
}
static void wrap_holo_avx512(void) {
    holonomy_avx512(g_drifts, HOLONOMY_LEN, HOLONOMY_CYCLES, 1.0, g_results);
}

/* --- Projection wrappers --- */
static void wrap_proj_scalar(void) {
    projection_scalar(g_xs, g_ys, g_ox, g_oy, g_n);
}
static void wrap_proj_avx512(void) {
    projection_avx512(g_xs, g_ys, g_ox, g_oy, g_n);
}

/* --- Constraint checking wrappers --- */
static void wrap_con_scalar(void) {
    for (int i = 0; i < g_n; i++)
        g_results[i] = constraint_check_scalar(g_cs, g_xs[i], g_ys[i]);
}
static void wrap_con_avx512(void) {
    constraint_check_avx512(g_cs, g_xs, g_ys, g_results, g_n);
}

/* =========================================================================
 * Main
 * ========================================================================= */

int main(void) {
    printf("\n=== AVX-512 Constraint Checking Benchmark ===\n");
    printf("CPU: AMD Ryzen AI 9 HX 370\n");
    printf("Flags: AVX512F AVX512BW AVX512DQ AVX512VL AVX512_VNNI AVX512_BF16\n\n");

    /* Allocate global test data */
    g_n = 100000;
    g_xs = aligned_alloc64(g_n * sizeof(double));
    g_ys = aligned_alloc64(g_n * sizeof(double));
    g_ox = aligned_alloc64(g_n * sizeof(double));
    g_oy = aligned_alloc64(g_n * sizeof(double));
    g_codes = aligned_alloc64(g_n * 12);
    g_results = aligned_alloc64((g_n > HOLONOMY_CYCLES ? g_n : HOLONOMY_CYCLES) * sizeof(int));
    g_cs = constraint_create(CONSTRAINT_NUM, 20);

    for (int i = 0; i < g_n; i++) {
        g_xs[i] = rng_signed() * 100.0;
        g_ys[i] = rng_signed() * 100.0;
    }

    double t_scalar, t_avx2, t_avx512;

    /* (a) Eisenstein snap */
    printf("--- (a) Eisenstein Snap (%d pts x %d reps) ---\n", g_n, EISENSTEIN_OPS / g_n);
    t_scalar = run_benchmark("Eisenstein snap (scalar)", wrap_eisen_scalar,
                              EISENSTEIN_OPS / g_n, WARMUP_OPS / g_n);
    t_avx2 = run_benchmark("Eisenstein snap (AVX2)", wrap_eisen_avx2,
                            EISENSTEIN_OPS / g_n, WARMUP_OPS / g_n);
    t_avx512 = run_benchmark("Eisenstein snap (AVX-512)", wrap_eisen_avx512,
                              EISENSTEIN_OPS / g_n, WARMUP_OPS / g_n);

    /* (b) Dodecet encoding */
    printf("\n--- (b) Dodecet Encoding (%d pts) ---\n", DODECET_OPS);
    g_n = 10000;
    for (int i = 0; i < g_n; i++) {
        g_xs[i] = rng_signed() * 100.0;
        g_ys[i] = rng_signed() * 100.0;
    }
    double t_d_scalar = run_benchmark("Dodecet (scalar)", wrap_dodecet_scalar,
                                       DODECET_OPS / g_n, WARMUP_OPS / g_n);
    double t_d_avx512 = run_benchmark("Dodecet (AVX-512)", wrap_dodecet_avx512,
                                       DODECET_OPS / g_n, WARMUP_OPS / g_n);

    /* (c) Holonomy — SIMD-friendly layout: [step0_cycle0..step0_cycleN, step1_cycle0..] */
    printf("\n--- (c) Bounded Drift Holonomy (%d cycles x %d steps) ---\n",
           HOLONOMY_CYCLES, HOLONOMY_LEN);
    g_drifts = aligned_alloc64(HOLONOMY_CYCLES * HOLONOMY_LEN * sizeof(double));
    for (int t = 0; t < HOLONOMY_LEN; t++)
        for (int c = 0; c < HOLONOMY_CYCLES; c++)
            g_drifts[t * HOLONOMY_CYCLES + c] = rng_signed() * 0.2;
    double t_h_scalar = run_benchmark("Holonomy (scalar)", wrap_holo_scalar, 1, 1);
    double t_h_avx512 = run_benchmark("Holonomy (AVX-512)", wrap_holo_avx512, 1, 1);

    /* (d) Cyclotomic projection */
    printf("\n--- (d) Cyclotomic Field Projection (%d pts) ---\n", PROJECTION_OPS);
    g_n = 10000;
    for (int i = 0; i < g_n; i++) {
        g_xs[i] = rng_signed() * 10.0;
        g_ys[i] = rng_signed() * 10.0;
    }
    /* Need larger output buffers for projection (15 * n) */
    free(g_ox); free(g_oy);
    g_ox = aligned_alloc64(ZETA15_N * g_n * sizeof(double));
    g_oy = aligned_alloc64(ZETA15_N * g_n * sizeof(double));

    double t_p_scalar = run_benchmark("Projection (scalar)", wrap_proj_scalar,
                                       PROJECTION_OPS / g_n, WARMUP_OPS / g_n);
    double t_p_avx512 = run_benchmark("Projection (AVX-512)", wrap_proj_avx512,
                                       PROJECTION_OPS / g_n, WARMUP_OPS / g_n);

    /* (e) 3-tier constraint checking */
    printf("\n--- (e) 3-Tier Constraint Checking (%d queries against %d constraints) ---\n",
           CONSTRAINT_OPS, CONSTRAINT_NUM);
    g_n = 10000;
    for (int i = 0; i < g_n; i++) {
        g_xs[i] = rng_signed() * 10.0;
        g_ys[i] = rng_signed() * 10.0;
    }
    double t_c_scalar = run_benchmark("Constraint check (scalar)", wrap_con_scalar,
                                       CONSTRAINT_OPS / g_n, WARMUP_OPS / g_n);
    double t_c_avx512 = run_benchmark("Constraint check (AVX-512)", wrap_con_avx512,
                                       CONSTRAINT_OPS / g_n, WARMUP_OPS / g_n);

    /* Convert to points/sec throughput */
    /* Each Eisenstein wrapper call processes 100000 points.
     * Each dodecet/projection/constraint call processes 10000.
     * Each holonomy call processes 100000 cycles. */
    double eis_pts_per_call = 100000.0;
    double dod_pts_per_call = 10000.0;
    double proj_pts_per_call = 10000.0;
    double con_pts_per_call = 10000.0;

    double eis_s = t_scalar * eis_pts_per_call;
    double eis_2 = t_avx2 * eis_pts_per_call;
    double eis_5 = t_avx512 * eis_pts_per_call;
    double dod_s = t_d_scalar * dod_pts_per_call;
    double dod_5 = t_d_avx512 * dod_pts_per_call;
    double hol_s = t_h_scalar * (double)HOLONOMY_CYCLES;
    double hol_5 = t_h_avx512 * (double)HOLONOMY_CYCLES;
    double proj_s = t_p_scalar * proj_pts_per_call;
    double proj_5 = t_p_avx512 * proj_pts_per_call;
    double con_s = t_c_scalar * con_pts_per_call;
    double con_5 = t_c_avx512 * con_pts_per_call;

    printf("\n\n=== RESULTS (points/sec) ===\n");
    printf("%-40s %12s %12s %12s   %s\n",
           "Operation", "Scalar", "AVX2", "AVX-512", "Speedup");
    printf("%-40s %12s %12s %12s   %s\n",
           "-", "--------", "--------", "--------", "-------");
    printf("%-40s %12.0f %12.0f %12.0f   x%.2f\n",
           "Eisenstein Snap", eis_s, eis_2, eis_5, eis_5 / eis_s);
    printf("%-40s %12.0f %12s %12.0f   x%.2f\n",
           "Dodecet Encoding", dod_s, "N/A", dod_5, dod_5 / dod_s);
    printf("%-40s %12.0f %12s %12.0f   x%.2f\n",
           "Bounded Drift Holonomy", hol_s, "N/A", hol_5, hol_5 / hol_s);
    printf("%-40s %12.0f %12s %12.0f   x%.2f\n",
           "Cyclotomic Projection", proj_s, "N/A", proj_5, proj_5 / proj_s);
    printf("%-40s %12.0f %12s %12.0f   x%.2f\n",
           "3-Tier Constraint Check", con_s, "N/A", con_5, con_5 / con_s);
    printf("\n");

    free(g_xs); free(g_ys); free(g_ox); free(g_oy);
    free(g_codes); free(g_results); free(g_drifts);
    free(g_cs->bloom_filter); free(g_cs->linear_coeffs); free(g_cs);

    return 0;
}
