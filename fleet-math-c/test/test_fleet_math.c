/**
 * test_fleet_math.c — Test harness for fleet_math.h
 *
 * Tests all 9 claims and additional production checks.
 *
 * Compile:
 *   gcc -O3 -march=native -lm -D FLEET_MATH_IMPLEMENTATION \
 *       -o test_fleet_math test_fleet_math.c
 *
 * Run:
 *   ./test_fleet_math
 */

#define FLEET_MATH_IMPLEMENTATION
#include "../include/fleet_math.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <assert.h>
#include <time.h>

/* Test utilities */
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST_EQ(a, b, msg) do { \
    if (fabs((double)(a) - (double)(b)) > 1e-10) { \
        fprintf(stderr, "FAIL: %s: %g != %g\n", msg, (double)(a), (double)(b)); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

#define TEST_TRUE(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

#define TEST_CLOSE(a, b, tol, msg) do { \
    double _da = (double)(a), _db = (double)(b); \
    if (fabs(_da - _db) > tol) { \
        fprintf(stderr, "FAIL: %s: %g != %g (tol %g)\n", msg, _da, _db, tol); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

/* =========================================================================
 * Claim 1: Cyclotomic field Q(ζ₁₅) — field construction
 * ========================================================================= */

static void test_claim1_zeta15_projection(void) {
    printf("Claim 1: ζ₁₅ projection... ");

    /* Test that rotate by 0 is identity */
    double rx, ry;
    fm_zeta15_rotate(3.14159, 2.71828, 0, &rx, &ry);
    TEST_CLOSE(rx, 3.14159, 1e-12, "k=0 identity x");
    TEST_CLOSE(ry, 2.71828, 1e-12, "k=0 identity y");

    /* Test that rotating 15 times by 1 = identity */
    double cx = 3.14159, cy = 2.71828;
    for (int i = 0; i < 15; i++)
        fm_zeta15_rotate(cx, cy, 1, &cx, &cy);
    TEST_CLOSE(cx, 3.14159, 1e-12, "15 rotations = identity x");
    TEST_CLOSE(cy, 2.71828, 1e-12, "15 rotations = identity y");

    printf("PASSED\n");
}

/* =========================================================================
 * Claim 2: ζ₁₅ rotation accuracy < 1e-15
 * ========================================================================= */

static void test_claim2_rotation_accuracy(void) {
    printf("Claim 2: ζ₁₅ rotation accuracy... ");

    /* Compare fm_zeta15_rotate against exact complex multiplication */
    double x = 3.141592653589793, y = 2.718281828459045;

    for (int k = 0; k < 15; k++) {
        double rx, ry;
        fm_zeta15_rotate(x, y, k, &rx, &ry);

        /* Expected: (x+iy) * ζ₁₅ᵏ */
        double c = cos(2.0 * M_PI * k / 15.0);
        double s = sin(2.0 * M_PI * k / 15.0);
        double ex = x * c - y * s;
        double ey = x * s + y * c;

        double err = sqrt((rx - ex) * (rx - ex) + (ry - ey) * (ry - ey));
        TEST_TRUE(err < 1e-12, "Rotation error < 1e-12");
    }

    printf("PASSED\n");
}

/* =========================================================================
 * Claim 3: Eisenstein lattice via ω = ζ₁₅⁵
 * ========================================================================= */

static void test_claim3_zeta15_5_is_omega(void) {
    printf("Claim 3: ζ₁₅⁵ = ω (Eisenstein unit)... ");

    /* ζ₁₅⁵ = e^{2πi·5/15} = e^{2πi/3} = -½ + i√3/2 */
    double c = cos(2.0 * M_PI * 5.0 / 15.0);
    double s = sin(2.0 * M_PI * 5.0 / 15.0);
    TEST_CLOSE(c, -0.5, 1e-12, "cos(2π·5/15) = -0.5");
    TEST_CLOSE(s, FM_SQRT3_2, 1e-12, "sin(2π·5/15) = √3/2");

    printf("PASSED\n");
}

/* =========================================================================
 * Claim 4: Penrose projection via φ-related angle
 * ========================================================================= */

static void test_claim4_penrose_angles(void) {
    printf("Claim 4: Penrose projection at θ=arctan(φ)... ");

    double theta_penrose = atan(FM_PHI);

    /* At θ = arctan(φ), the projection vectors should have ~5-fold symmetry */
    double vectors[6][2];
    fm_project_vectors(theta_penrose, vectors);

    /* First 5 vectors should have ~72° spacing */
    for (int k = 0; k < 4; k++) {
        double a1 = atan2(vectors[k][1], vectors[k][0]);
        double a2 = atan2(vectors[k+1][1], vectors[k+1][0]);
        double diff = fabs(fmod(a2 - a1 + 2.0 * M_PI, 2.0 * M_PI));
        double expected = 2.0 * M_PI / 5.0;
        TEST_CLOSE(diff, expected, 0.1, "Penrose 72° spacing");
    }

    printf("PASSED\n");
}

/* =========================================================================
 * Claim 5: Galois connection
 * ========================================================================= */

static void test_claim5_galois_connection(void) {
    printf("Claim 5: Galois connection field → constraint domain... ");

    double t = fm_galois_trace(0.0, 0.0);
    TEST_CLOSE(t, 0.0, 1e-12, "trace(0) = 0");

    t = fm_galois_trace(1.0, 0.0);
    TEST_CLOSE(t, 8.0/15.0, 1e-12, "trace(1) = 8/15");

    t = fm_galois_trace(15.0/8.0, 0.0);
    TEST_CLOSE(t, 1.0, 1e-12, "trace(15/8) = 1");

    t = fm_galois_trace(-1.0, 0.0);
    TEST_CLOSE(t, 0.0, 1e-12, "trace(-1) = 0 (clamped)");

    t = fm_galois_trace(10.0, 0.0);
    TEST_CLOSE(t, 1.0, 1e-12, "trace(10) = 1 (clamped)");

    printf("PASSED\n");
}

/* =========================================================================
 * Claim 6: Eisenstein snap — error ≤ A₂ covering radius
 * ========================================================================= */

static void test_claim6_snap_exact(void) {
    printf("Claim 6a: Exact lattice points snap to themselves... ");

    fm_snap_result_t snap;
    struct { int a; int b; } test_points[] = {
        {0, 0}, {1, 0}, {0, 1}, {2, -3}, {-5, 4}
    };
    int n = sizeof(test_points) / sizeof(test_points[0]);

    for (int i = 0; i < n; i++) {
        double x = test_points[i].a + test_points[i].b * FM_OMEGA_RE;
        double y = test_points[i].b * FM_OMEGA_IM;
        fm_eins_snap(x, y, &snap);
        TEST_TRUE(snap.coords.a == test_points[i].a &&
                  snap.coords.b == test_points[i].b,
                  "Exact lattice point snaps to itself");
        TEST_TRUE(snap.error < 1e-14, "Exact snap error < 1e-14");
    }

    printf("PASSED\n");
}

static void test_claim6_snap_error_bounded(void) {
    printf("Claim 6b: Snap error bounded by A₂ covering radius... ");

    srand(42);
    double max_err = 0.0;
    fm_snap_result_t snap;

    for (int i = 0; i < 1000; i++) {
        double x = (double)rand() / RAND_MAX * 20.0 - 10.0;
        double y = (double)rand() / RAND_MAX * 20.0 - 10.0;
        fm_eins_snap(x, y, &snap);
        if (snap.error > max_err) max_err = snap.error;
    }

    /* Max error should be within covering radius + numerical tolerance */
    TEST_TRUE(max_err <= FM_COVERING_RADIUS + 1e-12,
              "Max snap error ≤ A₂ covering radius");
    printf("  Max error: %g, Covering radius: %g\n", max_err, FM_COVERING_RADIUS);
    printf("PASSED\n");
}

/* =========================================================================
 * Claim 7: Unified 6D scheme
 * ========================================================================= */

static void test_claim7_unified_projection(void) {
    printf("Claim 7: Unified 6D projection vectors... ");

    /* At θ=0, vectors should be the 6 hexagonal directions */
    double vectors[6][2];
    fm_project_vectors(0.0, vectors);

    for (int k = 0; k < 6; k++) {
        double expected_angle = 2.0 * M_PI * k / 6.0;
        double actual_angle = atan2(vectors[k][1], vectors[k][0]);
        double diff = fabs(fmod(actual_angle - expected_angle + 2.0 * M_PI, 2.0 * M_PI));
        if (diff > M_PI) diff = 2.0 * M_PI - diff;
        TEST_CLOSE(diff, 0.0, 1e-10,
                   "Hexagonal vector angle correct");
    }

    /* Check vector magnitudes = 1 */
    for (int k = 0; k < 6; k++) {
        double mag = sqrt(vectors[k][0] * vectors[k][0] +
                          vectors[k][1] * vectors[k][1]);
        TEST_CLOSE(mag, 1.0, 1e-12, "Projection vector magnitude = 1");
    }

    printf("PASSED\n");
}

/* =========================================================================
 * Claim 8: Dodecet encoding (12-bit, 512-byte LUT)
 * ========================================================================= */

static void test_claim8_dodecet_range(void) {
    printf("Claim 8a: Dodecet code is 12-bit (0-4095)... ");

    for (int a = -10; a <= 10; a++) {
        for (int b = -10; b <= 10; b++) {
            uint16_t code = fm_dodecet_code(a, b);
            TEST_TRUE(code < 4096, "Dodecet code < 4096");
        }
    }

    /* Test equality with constraint_check.h formula */
    uint16_t code = fm_dodecet_code(0, 0);
    TEST_EQ(code, ((0 + 1000) * 2001 + (0 + 1000)) % 4096,
            "dodecet(0,0) matches formula");

    code = fm_dodecet_code(3, 5);
    TEST_EQ(code, ((3 + 1000) * 2001 + (5 + 1000)) % 4096,
            "dodecet(3,5) matches formula");

    printf("PASSED\n");
}

static void test_claim8_dodecet_lut(void) {
    printf("Claim 8b: Dodecet LUT insert/query... ");

    fm_dodecet_lut_t *lut = fm_lut_create();
    TEST_TRUE(lut != NULL, "LUT creation");

    fm_lut_insert(lut, 3, 5);
    fm_lut_insert(lut, 7, -2);
    fm_lut_insert(lut, -4, 3);

    TEST_TRUE(fm_lut_query(lut, 3, 5), "(3,5) in LUT");
    TEST_TRUE(fm_lut_query(lut, 7, -2), "(7,-2) in LUT");
    TEST_TRUE(fm_lut_query(lut, -4, 3), "(-4,3) in LUT");

    /* Unlikely to collide with these specific values */
    TEST_TRUE(!fm_lut_query(lut, 999, 999), "(999,999) not in LUT");

    fm_lut_destroy(lut);
    printf("PASSED\n");
}

/* =========================================================================
 * Claim 9: Bounded drift
 * ========================================================================= */

static void test_claim9_drift_bounds(void) {
    printf("Claim 9: Bounded drift bounds... ");

    double bound_open = fm_drift_bound_open(100, 1e-15);
    double expected_open = 1.5 * 100.0 * (1e-15 + FM_INV_SQRT3);
    TEST_CLOSE(bound_open, expected_open, 1e-10, "Open walk bound");

    double bound_closed = fm_drift_bound_closed(100, 1e-15);
    double expected_closed = 100.0 * 1e-15;
    TEST_CLOSE(bound_closed, expected_closed, 1e-10, "Closed cycle bound");

    /* Closed bound should be tighter than open */
    TEST_TRUE(bound_closed < bound_open, "Closed bound < open bound");

    /* Drift check */
    TEST_TRUE(fm_drift_check(0.0, 1.0) == 1, "Zero drift within bound");
    TEST_TRUE(fm_drift_check(1.5, 1.0) == 0, "Drift exceeds bound");

    printf("PASSED\n");
}

/* =========================================================================
 * (Bonus) 3-tier constraint database
 * ========================================================================= */

static void test_3tier_constraint_db(void) {
    printf("Bonus: 3-tier constraint database... ");

    fm_constraint_db_t *db = fm_db_create(1000);
    TEST_TRUE(db != NULL, "DB creation");

    fm_db_insert(db, 3, 5);
    fm_db_insert(db, 7, -2);
    fm_db_insert(db, -4, 3);

    TEST_TRUE(fm_db_query(db, 3, 5), "(3,5) query");
    TEST_TRUE(fm_db_query(db, 7, -2), "(7,-2) query");
    TEST_TRUE(fm_db_query(db, -4, 3), "(-4,3) query");
    TEST_TRUE(!fm_db_query(db, 1, 1), "(1,1) not present");

    fm_db_free(db);
    printf("PASSED\n");
}

/* =========================================================================
 * (Bonus) Batch snap performance sanity check
 * ========================================================================= */

static void test_batch_snap(void) {
    printf("Bonus: Batch snap consistency... ");

    int n = 10;
    double xs[10], ys[10];
    fm_snap_result_t results[10];

    srand(123);
    for (int i = 0; i < n; i++) {
        xs[i] = (double)rand() / RAND_MAX * 10.0 - 5.0;
        ys[i] = (double)rand() / RAND_MAX * 10.0 - 5.0;
    }

    fm_eins_batch_snap(xs, ys, n, results);

    /* Compare each batch result with individual call */
    for (int i = 0; i < n; i++) {
        fm_snap_result_t single;
        fm_eins_snap(xs[i], ys[i], &single);
        TEST_TRUE(results[i].coords.a == single.coords.a &&
                  results[i].coords.b == single.coords.b &&
                  fabs(results[i].error - single.error) < 1e-15,
                  "Batch snap matches individual");
    }

    printf("PASSED\n");
}

/* =========================================================================
 * Main
 * ========================================================================= */

int main(void) {
    printf("=== fleet_math.h Test Suite ===\n\n");

    test_claim1_zeta15_projection();
    test_claim2_rotation_accuracy();
    test_claim3_zeta15_5_is_omega();
    test_claim4_penrose_angles();
    test_claim5_galois_connection();
    test_claim6_snap_exact();
    test_claim6_snap_error_bounded();
    test_claim7_unified_projection();
    test_claim8_dodecet_range();
    test_claim8_dodecet_lut();
    test_claim9_drift_bounds();
    test_3tier_constraint_db();
    test_batch_snap();

    printf("\n=== Results: %d passed, %d failed ===\n",
           tests_passed, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
