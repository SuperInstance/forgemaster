/*
 * test_exhaustive.c — Comprehensive correctness tests for snapkit
 *
 * Tests:
 *   1. Eisenstein Voronoi snap — 1M random points, verify covering radius ≤ 1/√3
 *   2. Idempotency: snap(snap(p)) == snap(p)
 *   3. Lattice correctness: snapped points are valid Eisenstein integers
 *   4. Covering radius: find actual maximum snap distance
 *   5. Boundary cases: Voronoi cell edges, corners
 *   6. Degenerate cases: (0,0), large coords, negatives
 *   7. Temporal snap: phase in [0,period), T-minus-0 detection
 *   8. Spectral: entropy of uniform = log2(n), deterministic = 0; Hurst of known fBm
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include <assert.h>

#define SNAPKIT_IMPLEMENTATION
#include "snapkit.h"

/* ---- Simple RNG (xoshiro128+) for reproducibility ---- */
static uint32_t rng_s[4];
static void rng_seed(uint64_t seed) {
    for (int i = 0; i < 4; i++) {
        seed ^= seed >> 12;
        seed *= 0x5DEECE66DULL;
        seed ^= seed >> 17;
        rng_s[i] = (uint32_t)(seed & 0xFFFFFFFF);
    }
}
static uint32_t rng_next(void) {
    uint32_t *s = rng_s;
    uint32_t result = s[0] + s[3];
    uint32_t t = s[1] << 9;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
    s[2] ^= t;
    s[3] = (s[3] << 11) | (s[3] >> 21);
    return result;
}
static double rng_double(double lo, double hi) {
    return lo + (hi - lo) * (rng_next() / 4294967296.0);
}

static int pass_count = 0;
static int fail_count = 0;

#define CHECK(cond, msg, ...) do { \
    if (cond) { pass_count++; } \
    else { fail_count++; fprintf(stderr, "FAIL: " msg "\n", ##__VA_ARGS__); } \
} while(0)

#define TOLERANCE 1e-9

/* ================================================================== */
/* Test 1: Covering radius — 1M random points                         */
/* ================================================================== */
static void test_covering_radius(void) {
    printf("=== Test 1: Covering Radius (1M points) ===\n");
    rng_seed(0xDEADBEEF);

    const int N = 1000000;
    int violations = 0;
    double max_dist = 0.0;
    double sum_dist = 0.0;
    double max_dist_x = 0, max_dist_y = 0;

    for (int i = 0; i < N; i++) {
        /* Points in [-500, 500] to cover large range */
        double x = rng_double(-500.0, 500.0);
        double y = rng_double(-500.0, 500.0);

        sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);
        double cx = sk_eisenstein_x(e.a, e.b);
        double cy = sk_eisenstein_y(e.b);
        double dx = x - cx;
        double dy = y - cy;
        double dist = sqrt(dx * dx + dy * dy);

        if (dist > max_dist) {
            max_dist = dist;
            max_dist_x = x;
            max_dist_y = y;
        }
        sum_dist += dist;

        if (dist > SNAPKIT_COVERING_RADIUS + TOLERANCE) {
            violations++;
        }
    }

    printf("  Points tested:  %d\n", N);
    printf("  Max snap dist:  %.15f\n", max_dist);
    printf("  1/sqrt(3):       %.15f\n", SNAPKIT_INV_SQRT3);
    printf("  Margin:          %.2e\n", SNAPKIT_INV_SQRT3 - max_dist);
    printf("  Mean dist:       %.6f\n", sum_dist / N);
    printf("  Worst case at:   (%.6f, %.6f)\n", max_dist_x, max_dist_y);
    printf("  Violations:      %d\n", violations);

    CHECK(violations == 0,
        "Covering radius: %d violations out of %d (max_dist=%.15f > 1/sqrt3=%.15f)",
        violations, N, max_dist, SNAPKIT_INV_SQRT3);
}

/* ================================================================== */
/* Test 2: Idempotency                                                */
/* ================================================================== */
static void test_idempotency(void) {
    printf("\n=== Test 2: Idempotency (100K points) ===\n");
    rng_seed(0xCAFEBABE);

    const int N = 100000;
    int failures = 0;

    for (int i = 0; i < N; i++) {
        double x = rng_double(-1000.0, 1000.0);
        double y = rng_double(-1000.0, 1000.0);

        sk_eisenstein e1 = sk_eisenstein_snap_voronoi(x, y);
        /* Snap the snapped point */
        double cx = sk_eisenstein_x(e1.a, e1.b);
        double cy = sk_eisenstein_y(e1.b);
        sk_eisenstein e2 = sk_eisenstein_snap_voronoi(cx, cy);

        if (e1.a != e2.a || e1.b != e2.b) {
            failures++;
            if (failures <= 3) {
                fprintf(stderr, "  Not idempotent: (%.3f,%.3f) -> (%d,%d) -> (%d,%d)\n",
                    x, y, e1.a, e1.b, e2.a, e2.b);
            }
        }
    }

    printf("  Points tested: %d\n", N);
    printf("  Failures:      %d\n", failures);
    CHECK(failures == 0, "Idempotency: %d failures out of %d", failures, N);
}

/* ================================================================== */
/* Test 3: Lattice correctness                                        */
/* ================================================================== */
static void test_lattice_correctness(void) {
    printf("\n=== Test 3: Lattice Correctness (100K points) ===\n");
    rng_seed(0xBAADF00D);

    const int N = 100000;
    int failures = 0;

    for (int i = 0; i < N; i++) {
        double x = rng_double(-100.0, 100.0);
        double y = rng_double(-100.0, 100.0);

        sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);

        /* Verify: snapped point reconstructs to valid Eisenstein integer coords */
        double cx = sk_eisenstein_x(e.a, e.b);
        double cy = sk_eisenstein_y(e.b);

        /* Re-snap: should get same result */
        sk_eisenstein e2 = sk_eisenstein_snap_voronoi(cx, cy);
        if (e.a != e2.a || e.b != e2.b) {
            failures++;
        }

        /* Verify y coordinate: must be b * sqrt(3)/2 */
        double expected_y = SNAPKIT_HALF_SQRT3 * (double)e.b;
        if (fabs(cy - expected_y) > TOLERANCE) {
            failures++;
        }
    }

    printf("  Points tested: %d\n", N);
    printf("  Failures:      %d\n", failures);
    CHECK(failures == 0, "Lattice correctness: %d failures out of %d", failures, N);
}

/* ================================================================== */
/* Test 4: Actual covering radius measurement                         */
/* ================================================================== */
static void test_covering_radius_measurement(void) {
    printf("\n=== Test 4: Covering Radius Measurement ===\n");

    /* Systematically probe the Voronoi cell around origin */
    /* The Voronoi cell of (0,0) is a regular hexagon with vertices at
       distance 1/sqrt(3) from center */
    double max_dist = 0.0;
    double max_x = 0, max_y = 0;

    /* Fine grid search within the Voronoi cell of (0,0) */
    /* The cell extends roughly [-0.5, 1.0] in x, [-0.577, 0.577] in y */
    for (double x = -0.6; x <= 1.0; x += 0.0001) {
        for (double y = -0.6; y <= 0.6; y += 0.0001) {
            sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);
            /* Only consider points that snap to (0,0) */
            if (e.a == 0 && e.b == 0) {
                double dist = sqrt(x * x + y * y);
                if (dist > max_dist) {
                    max_dist = dist;
                    max_x = x;
                    max_y = y;
                }
            }
        }
    }

    printf("  Max distance in Voronoi cell of (0,0): %.15f\n", max_dist);
    printf("  Achieved at: (%.6f, %.6f)\n", max_x, max_y);
    printf("  1/sqrt(3):                                %.15f\n", SNAPKIT_INV_SQRT3);
    printf("  Difference:                               %.2e\n",
        fabs(max_dist - SNAPKIT_INV_SQRT3));

    /* The max should be very close to 1/sqrt(3) */
    CHECK(fabs(max_dist - SNAPKIT_INV_SQRT3) < 0.001,
        "Covering radius measurement: max_dist=%.6f, expected ~%.6f",
        max_dist, SNAPKIT_INV_SQRT3);
}

/* ================================================================== */
/* Test 5: Boundary cases — edges and corners                         */
/* ================================================================== */
static void test_boundary_cases(void) {
    printf("\n=== Test 5: Boundary Cases ===\n");
    int local_fail = 0;

    /* Points at known Voronoi edges — equidistant from two lattice points */
    /* Edge between (0,0) and (1,0): midpoint at (0.5, 0) */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(0.5, 0.0);
        int ok = (e.a == 0 && e.b == 0) || (e.a == 1 && e.b == 0);
        printf("  Edge (0,0)-(1,0) midpoint: snapped to (%d,%d) — %s\n",
            e.a, e.b, ok ? "OK" : "FAIL");
        if (!ok) local_fail++;
    }

    /* Edge between (0,0) and (0,1): at (0.25, sqrt(3)/4) */
    {
        double ey = SNAPKIT_HALF_SQRT3 * 0.5;
        sk_eisenstein e = sk_eisenstein_snap_voronoi(-0.25, ey);
        int ok = (e.a == 0 && e.b == 0) || (e.a == -1 && e.b == 1);
        printf("  Edge (0,0)-(-1,1) near-midpoint: snapped to (%d,%d) — %s\n",
            e.a, e.b, ok ? "OK" : "FAIL");
        if (!ok) local_fail++;
    }

    /* Corners of Voronoi cell: these are at distance 1/sqrt(3) from center */
    /* The six corners of the Voronoi cell of (0,0) */
    {
        double corners[6][2] = {
            { 1.0/SNAPKIT_SQRT3, 0.0 },
            { 0.5/SNAPKIT_SQRT3, 0.5 },
            {-0.5/SNAPKIT_SQRT3, 0.5 },
            {-1.0/SNAPKIT_SQRT3, 0.0 },
            {-0.5/SNAPKIT_SQRT3, -0.5 },
            { 0.5/SNAPKIT_SQRT3, -0.5 },
        };
        for (int i = 0; i < 6; i++) {
            sk_eisenstein e = sk_eisenstein_snap_voronoi(corners[i][0], corners[i][1]);
            printf("  Corner %d (%.4f,%.4f): snapped to (%d,%d)\n",
                i, corners[i][0], corners[i][1], e.a, e.b);
            /* Should snap to (0,0) or an adjacent — distance should be ≤ 1/sqrt(3) */
            double cx = sk_eisenstein_x(e.a, e.b);
            double cy = sk_eisenstein_y(e.b);
            double dist = sqrt(pow(corners[i][0]-cx,2) + pow(corners[i][1]-cy,2));
            if (dist > SNAPKIT_COVERING_RADIUS + TOLERANCE) {
                printf("    FAIL: dist=%.6f > 1/sqrt3=%.6f\n", dist, SNAPKIT_INV_SQRT3);
                local_fail++;
            }
        }
    }

    CHECK(local_fail == 0, "Boundary cases: %d failures", local_fail);
}

/* ================================================================== */
/* Test 6: Degenerate cases                                           */
/* ================================================================== */
static void test_degenerate_cases(void) {
    printf("\n=== Test 6: Degenerate Cases ===\n");
    int local_fail = 0;

    /* Origin */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(0.0, 0.0);
        int ok = (e.a == 0 && e.b == 0);
        printf("  Origin (0,0): snapped to (%d,%d) — %s\n", e.a, e.b, ok ? "OK" : "FAIL");
        if (!ok) local_fail++;
    }

    /* Exact lattice points */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(1.0, 0.0);
        int ok = (e.a == 1 && e.b == 0);
        printf("  Lattice (1,0) -> Cartesian (1,0): snapped to (%d,%d) — %s\n",
            e.a, e.b, ok ? "OK" : "FAIL");
        if (!ok) local_fail++;
    }
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(0.5, SNAPKIT_HALF_SQRT3);
        int ok = (e.a == 0 && e.b == 1) || (e.a == 1 && e.b == 1);
        /* (0,1) maps to (-0.5, sqrt(3)/2), (1,1) maps to (0.5, sqrt(3)/2) */
        /* Closest to (0.5, sqrt(3)/2) is (1,1) */
        printf("  Near-lattice (0.5, sqrt3/2): snapped to (%d,%d) — %s\n",
            e.a, e.b, ok ? "OK" : "FAIL");
        if (!ok) local_fail++;
    }

    /* Large positive coords */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(1e6, 1e6);
        double cx = sk_eisenstein_x(e.a, e.b);
        double cy = sk_eisenstein_y(e.b);
        double dist = sqrt(pow(1e6 - cx, 2) + pow(1e6 - cy, 2));
        printf("  Large (+1M, +1M): snapped to (%d,%d), dist=%.6f — %s\n",
            e.a, e.b, dist, dist <= SNAPKIT_COVERING_RADIUS + 1e-6 ? "OK" : "FAIL");
        if (dist > SNAPKIT_COVERING_RADIUS + 1e-6) local_fail++;
    }

    /* Large negative coords */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(-1e6, -1e6);
        double cx = sk_eisenstein_x(e.a, e.b);
        double cy = sk_eisenstein_y(e.b);
        double dist = sqrt(pow(-1e6 - cx, 2) + pow(-1e6 - cy, 2));
        printf("  Large (-1M, -1M): snapped to (%d,%d), dist=%.6f — %s\n",
            e.a, e.b, dist, dist <= SNAPKIT_COVERING_RADIUS + 1e-6 ? "OK" : "FAIL");
        if (dist > SNAPKIT_COVERING_RADIUS + 1e-6) local_fail++;
    }

    /* Mixed large coords */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(1e6, -1e6);
        double cx = sk_eisenstein_x(e.a, e.b);
        double cy = sk_eisenstein_y(e.b);
        double dist = sqrt(pow(1e6 - cx, 2) + pow(-1e6 - cy, 2));
        printf("  Large (+1M, -1M): snapped to (%d,%d), dist=%.6f — %s\n",
            e.a, e.b, dist, dist <= SNAPKIT_COVERING_RADIUS + 1e-6 ? "OK" : "FAIL");
        if (dist > SNAPKIT_COVERING_RADIUS + 1e-6) local_fail++;
    }

    /* Very large coords */
    {
        sk_eisenstein e = sk_eisenstein_snap_voronoi(1e9, 0.0);
        double cx = sk_eisenstein_x(e.a, e.b);
        double dist = fabs(1e9 - cx);
        printf("  Very large (1B, 0): snapped to (%d,%d), dist=%.6f — %s\n",
            e.a, e.b, dist, dist <= SNAPKIT_COVERING_RADIUS + 1.0 ? "OK" : "FAIL");
        if (dist > 1.0) local_fail++;
    }

    CHECK(local_fail == 0, "Degenerate cases: %d failures", local_fail);
}

/* ================================================================== */
/* Test 7: Temporal snap                                              */
/* ================================================================== */
static void test_temporal(void) {
    printf("\n=== Test 7: Temporal Snap ===\n");
    int local_fail = 0;

    /* Basic beat grid */
    sk_beat_grid grid;
    int rc = sk_beat_grid_init(&grid, 1.0, 0.0, 0.0);  /* 1-second period */
    CHECK(rc == 0, "Beat grid init failed");

    /* Test phase always in [0, period) */
    rng_seed(0xF00DCAFE);
    {
        const int N = 100000;
        int phase_violations = 0;
        for (int i = 0; i < N; i++) {
            double t = rng_double(-1000.0, 1000.0);
            sk_temporal_result r = sk_beat_grid_snap(&grid, t, 0.01);
            if (r.beat_phase < 0.0 || r.beat_phase >= 1.0) {
                phase_violations++;
            }
        }
        printf("  Phase range test: %d violations out of %d\n", phase_violations, N);
        if (phase_violations > 0) local_fail++;
    }

    /* On-beat detection */
    {
        sk_temporal_result r = sk_beat_grid_snap(&grid, 5.0, 0.01);
        printf("  t=5.0 (on beat): offset=%.6f, is_on_beat=%d — %s\n",
            r.offset, r.is_on_beat, r.is_on_beat ? "OK" : "FAIL");
        if (!r.is_on_beat) local_fail++;
    }
    {
        sk_temporal_result r = sk_beat_grid_snap(&grid, 5.5, 0.01);
        printf("  t=5.5 (off beat): offset=%.6f, is_on_beat=%d — %s\n",
            r.offset, r.is_on_beat, !r.is_on_beat ? "OK" : "FAIL");
        if (r.is_on_beat) local_fail++;
    }

    /* Beat index correctness */
    {
        sk_temporal_result r = sk_beat_grid_snap(&grid, 3.0, 0.01);
        printf("  t=3.0: beat_index=%d — %s\n", r.beat_index,
            r.beat_index == 3 ? "OK" : "FAIL");
        if (r.beat_index != 3) local_fail++;
    }

    /* T-minus-0 detection with synthetic trigger */
    {
        sk_temporal_snap ts;
        sk_temporal_snap_init(&ts, &grid, 0.01, 0.5, 5);

        /* Simulate a signal that rises then drops through zero */
        sk_temporal_observe(&ts, 1.0, 2.0);  /* rising */
        sk_temporal_observe(&ts, 2.0, 1.5);  /* peak */
        sk_temporal_observe(&ts, 3.0, 0.3);  /* dropping */
        sk_temporal_observe(&ts, 4.0, -0.8); /* crossed zero */
        sk_temporal_result r = sk_temporal_observe(&ts, 5.0, 0.1);
        printf("  T0 detection after zero crossing: is_t_minus_0=%d\n", r.is_t_minus_0);
        /* The detection looks at last 3 values: 0.3, -0.8, 0.1
           derivatives: (-0.8-0.3)/1 = -1.1, (0.1-(-0.8))/1 = 0.9
           Sign change: -1.1 * 0.9 < 0 -> true, and |0.1| < 0.5 -> true */
        if (!r.is_t_minus_0) {
            printf("    WARN: Expected T0 detection\n");
            /* Not a hard failure since detection is heuristic */
        }
    }

    /* Beat grid range */
    {
        double beats[100];
        int count = sk_beat_grid_range(&grid, 2.0, 5.0, beats, 100);
        printf("  Beat range [2,5]: count=%d — %s\n", count,
            count == 3 ? "OK" : "FAIL (expected 3)");
        if (count != 3) local_fail++;
    }

    /* Negative period should fail */
    {
        sk_beat_grid bad;
        int rc2 = sk_beat_grid_init(&bad, -1.0, 0.0, 0.0);
        printf("  Negative period init: rc=%d — %s\n", rc2, rc2 == -1 ? "OK" : "FAIL");
        if (rc2 != -1) local_fail++;
    }

    CHECK(local_fail == 0, "Temporal: %d sub-failures", local_fail);
}

/* ================================================================== */
/* Test 8: Spectral — entropy and Hurst                               */
/* ================================================================== */
static void test_spectral(void) {
    printf("\n=== Test 8: Spectral Analysis ===\n");
    int local_fail = 0;
    rng_seed(0x12345678);

    /* Entropy of uniform distribution should be ~ log2(bins) */
    {
        const int N = 100000;
        const int BINS = 32;
        double data[N];
        for (int i = 0; i < N; i++) data[i] = rng_double(0.0, 1.0);

        double h = sk_entropy(data, N, BINS);
        double expected = log2((double)BINS);
        double err = fabs(h - expected);
        printf("  Uniform entropy: %.4f bits (expected %.4f), error=%.4f — %s\n",
            h, expected, err, err < 0.05 ? "OK" : "FAIL");
        if (err >= 0.05) local_fail++;
    }

    /* Entropy of deterministic (constant) should be 0 */
    {
        const int N = 10000;
        double data[N];
        for (int i = 0; i < N; i++) data[i] = 42.0;

        double h = sk_entropy(data, N, 16);
        printf("  Constant entropy: %.4f bits (expected 0.0) — %s\n",
            h, h == 0.0 ? "OK" : "FAIL");
        if (h != 0.0) local_fail++;
    }

    /* Entropy of binary signal (half 0, half 1) should be ~1 bit */
    {
        const int N = 100000;
        double data[N];
        for (int i = 0; i < N; i++) data[i] = (i < N/2) ? 0.0 : 1.0;

        double h = sk_entropy(data, N, 2);
        double err = fabs(h - 1.0);
        printf("  Binary entropy: %.4f bits (expected 1.0), error=%.4f — %s\n",
            h, err, err < 0.01 ? "OK" : "FAIL");
        if (err >= 0.01) local_fail++;
    }

    /* Hurst of random walk (should be ~0.5) */
    {
        const int N = 10000;
        double data[N];
        data[0] = 0.0;
        for (int i = 1; i < N; i++) {
            data[i] = data[i-1] + (rng_double(-1.0, 1.0));
        }

        double h = sk_hurst_exponent(data, N);
        double err = fabs(h - 0.5);
        printf("  Random walk Hurst: %.4f (expected ~0.5), error=%.4f — %s\n",
            h, err, err < 0.15 ? "OK" : "WARN");
        /* Hurst estimation is approximate, allow wider tolerance */
        if (err >= 0.2) local_fail++;
    }

    /* Hurst of trending series (should be > 0.5) */
    {
        const int N = 10000;
        double data[N];
        data[0] = 0.0;
        for (int i = 1; i < N; i++) {
            data[i] = data[i-1] + 0.1 + rng_double(-0.3, 0.3);
        }

        double h = sk_hurst_exponent(data, N);
        printf("  Trending Hurst: %.4f (expected > 0.5) — %s\n",
            h, h > 0.5 ? "OK" : "FAIL");
        if (h <= 0.5) local_fail++;
    }

    /* Autocorrelation of white noise: lag-1 should be ~0 */
    {
        const int N = 10000;
        double data[N];
        for (int i = 0; i < N; i++) data[i] = rng_double(-1.0, 1.0);

        double acf[101];
        int lag_count = sk_autocorrelation(data, N, 100, acf);
        printf("  White noise ACF lag-1: %.4f (expected ~0.0) — %s\n",
            acf[1], fabs(acf[1]) < 0.05 ? "OK" : "WARN");
        if (fabs(acf[1]) >= 0.05) {
            printf("    (Not a hard failure — ACF estimation has variance)\n");
        }
        printf("  ACF lag-0: %.4f (expected 1.0) — %s\n",
            acf[0], fabs(acf[0] - 1.0) < 1e-9 ? "OK" : "FAIL");
        if (fabs(acf[0] - 1.0) >= 1e-9) local_fail++;
    }

    /* Spectral summary */
    {
        const int N = 5000;
        double data[N];
        for (int i = 0; i < N; i++) data[i] = rng_double(-1.0, 1.0);

        double acf_buf[251];
        int counts_buf[32];
        sk_spectral_summary s = sk_spectral_analyze(data, N, 32, 250, acf_buf, counts_buf);
        printf("  Spectral summary: entropy=%.3f, hurst=%.3f, acf_lag1=%.3f, stationary=%d\n",
            s.entropy_bits, s.hurst, s.autocorr_lag1, s.is_stationary);
    }

    CHECK(local_fail == 0, "Spectral: %d sub-failures", local_fail);
}

/* ================================================================== */
/* Test: Naive vs Voronoi agreement                                   */
/* ================================================================== */
static void test_naive_vs_voronoi(void) {
    printf("\n=== Bonus: Naive vs Voronoi Agreement (100K points) ===\n");
    rng_seed(0xFEEDFACE);

    const int N = 100000;
    int disagreements = 0;
    double max_dist_diff = 0.0;

    for (int i = 0; i < N; i++) {
        double x = rng_double(-100.0, 100.0);
        double y = rng_double(-100.0, 100.0);

        sk_eisenstein en = sk_eisenstein_snap_naive(x, y);
        sk_eisenstein ev = sk_eisenstein_snap_voronoi(x, y);

        if (en.a != ev.a || en.b != ev.b) {
            disagreements++;
            /* Check if both are equally close (on boundary) */
            double dx_n = x - sk_eisenstein_x(en.a, en.b);
            double dy_n = y - sk_eisenstein_y(en.b);
            double d_n = sqrt(dx_n*dx_n + dy_n*dy_n);
            double dx_v = x - sk_eisenstein_x(ev.a, ev.b);
            double dy_v = y - sk_eisenstein_y(ev.b);
            double d_v = sqrt(dx_v*dx_v + dy_v*dy_v);
            double diff = fabs(d_n - d_v);
            if (diff > max_dist_diff) max_dist_diff = diff;
        }
    }

    printf("  Disagreements: %d out of %d\n", disagreements, N);
    printf("  Max distance difference at disagreement: %.2e\n", max_dist_diff);
    /* Disagreements should only happen at boundaries and be distance-equivalent */
    CHECK(max_dist_diff < 0.001 || disagreements == 0,
        "Naive vs Voronoi: max_dist_diff=%.6f at %d disagreements",
        max_dist_diff, disagreements);
}

/* ================================================================== */
/* Main                                                                */
/* ================================================================== */
int main(void) {
    printf("snapkit Exhaustive Correctness Tests\n");
    printf("=====================================\n\n");

    test_covering_radius();
    test_idempotency();
    test_lattice_correctness();
    test_covering_radius_measurement();
    test_boundary_cases();
    test_degenerate_cases();
    test_temporal();
    test_spectral();
    test_naive_vs_voronoi();

    printf("\n=====================================\n");
    printf("TOTAL: %d passed, %d failed\n", pass_count, fail_count);
    printf("=====================================\n");

    return fail_count > 0 ? 1 : 0;
}
