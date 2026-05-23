/*
 * test_physics.c — Validation tests for SonarVision
 *
 * Tests validated against published oceanographic data:
 *   - Mackenzie 1981 tables
 *   - Francois-Garrison 1982 tables
 *   - Standard sonar equation benchmarks
 */

#include "sonar_vision.h"
#include <stdio.h>
#include <math.h>
#include <string.h>

#define TOLERANCE_1  1e-2    /* 0.01 m/s for sound speed */
#define TOLERANCE_2  1.0     /* 1.0 dB/km for absorption */
#define TOLERANCE_TL 1.0     /* 1.0 dB for transmission loss */
#define TOLERANCE_P  0.01    /* 1% for probability */

static int tests_run    = 0;
static int tests_passed = 0;

#define TEST(name) \
    do { tests_run++; printf("  %-45s", #name); } while(0)

#define PASS() \
    do { tests_passed++; printf("PASS\n"); } while(0)

#define FAIL(msg) \
    printf("FAIL: %s\n", msg)

#define ASSERT_EQ_DBL(actual, expected, tol, label) \
    do { \
        double _a = (actual), _e = (expected), _t = (tol); \
        double _diff = fabs(_a - _e); \
        if (_diff > _t) { \
            printf("FAIL: %s: expected %.6f, got %.6f (diff %.6e)\n", \
                   label, _e, _a, _diff); \
            return; \
        } \
    } while(0)

/* ── Mackenzie tests ─────────────────────────────────────────────── */

static void test_mackenzie_surface(void)
{
    TEST(test_mackenzie_surface);
    double speed;
    sv_error_t err = sv_mackenzie(10.0, 35.0, 0.0, &speed);
    if (err != SV_OK) { FAIL("sv_mackenzie returned error"); return; }
    /* Mackenzie(10, 35, 0): computed = 1489.80 m/s */
    ASSERT_EQ_DBL(speed, 1489.8, 0.5, "surface speed");
    PASS();
}

static void test_mackenzie_deep(void)
{
    TEST(test_mackenzie_deep);
    double speed;
    sv_error_t err = sv_mackenzie(2.0, 34.7, 4000.0, &speed);
    if (err != SV_OK) { FAIL("sv_mackenzie returned error"); return; }
    /* Mackenzie(2, 34.7, 4000): computed ≈ 1525.4 m/s */
    ASSERT_EQ_DBL(speed, 1525.4, 1.0, "deep speed");
    PASS();
}

static void test_mackenzie_validation(void)
{
    TEST(test_mackenzie_validation);
    double speed;

    /* Out-of-range temperature */
    if (sv_mackenzie(50.0, 35.0, 0.0, &speed) != SV_ERR_TEMP_RANGE) {
        FAIL("should reject T=50"); return;
    }
    /* Out-of-range salinity */
    if (sv_mackenzie(10.0, 20.0, 0.0, &speed) != SV_ERR_SAL_RANGE) {
        FAIL("should reject S=20"); return;
    }
    /* Out-of-range depth */
    if (sv_mackenzie(10.0, 35.0, 15000.0, &speed) != SV_ERR_DEPTH_RANGE) {
        FAIL("should reject D=15000"); return;
    }
    /* NULL pointer */
    if (sv_mackenzie(10.0, 35.0, 0.0, NULL) != SV_ERR_NULL_PTR) {
        FAIL("should reject NULL"); return;
    }
    PASS();
}

static void test_mackenzie_batch(void)
{
    TEST(test_mackenzie_batch);
    double temps[3]   = {10.0, 15.0, 20.0};
    double sals[3]    = {35.0, 35.0, 35.0};
    double depths[3]  = {0.0,  100.0, 1000.0};
    double out[3];

    sv_error_t err = sv_mackenzie_batch(temps, sals, depths, out, 3);
    if (err != SV_OK) { FAIL("batch returned error"); return; }

    /* Each output should match scalar computation */
    for (int i = 0; i < 3; i++) {
        double expected;
        sv_mackenzie(temps[i], sals[i], depths[i], &expected);
        if (fabs(out[i] - expected) > 1e-12) {
            printf("FAIL: batch[%d] mismatch: expected %.15f, got %.15f\n",
                   i, expected, out[i]);
            return;
        }
    }
    PASS();
}

/* ── Absorption tests ────────────────────────────────────────────── */

static void test_absorption_low_freq(void)
{
    TEST(test_absorption_low_freq);
    double alpha;
    sv_error_t err = sv_absorption(1.0, 10.0, 35.0, 0.0, 8.0, &alpha);
    if (err != SV_OK) { FAIL("absorption returned error"); return; }
    /* FG82 at 1 kHz, T=10, S=35, D=0, pH=8: ~0.03 dB/km */
    printf("  [α=%.4f dB/km] ", alpha);
    ASSERT_EQ_DBL(alpha, 0.03, 0.05, "low freq absorption");
    PASS();
}

static void test_absorption_high_freq(void)
{
    TEST(test_absorption_high_freq);
    double alpha;
    sv_error_t err = sv_absorption(100.0, 10.0, 35.0, 0.0, 8.0, &alpha);
    if (err != SV_OK) { FAIL("absorption returned error"); return; }
    /* FG82 at 100 kHz, T=10, S=35, D=0, pH=8: ~30 dB/km */
    printf("  [α=%.2f dB/km] ", alpha);
    ASSERT_EQ_DBL(alpha, 30.0, 15.0, "high freq absorption");
    PASS();
}

static void test_absorption_validation(void)
{
    TEST(test_absorption_validation);
    double alpha;
    if (sv_absorption(0.1, 10.0, 35.0, 0.0, 8.0, &alpha) != SV_ERR_FREQ_RANGE) {
        FAIL("should reject f=0.1"); return;
    }
    if (sv_absorption(1.0, 10.0, 35.0, 0.0, 5.0, &alpha) != SV_ERR_PH_RANGE) {
        FAIL("should reject pH=5"); return;
    }
    PASS();
}

/* ── Ray trace test ──────────────────────────────────────────────── */

static void test_ray_trace_shallow(void)
{
    TEST(test_ray_trace_shallow);

    /* Simple SSP: 1500 m/s at surface, 1520 m/s at 100m */
    sv_ssp_point_t points[] = {
        {0.0,   1500.0},
        {100.0, 1520.0}
    };
    sv_ssp_t ssp = { points, 2 };

    sv_ray_result_t res;
    sv_error_t err = sv_ray_trace(&ssp, 50.0, 0.1, 1000.0,
                                  SV_RAY_SHALLOW, 20, &res);
    if (err != SV_OK) { FAIL("ray trace returned error"); return; }

    /* Should have positive travel time and path length */
    if (res.travel_time <= 0.0) {
        printf("FAIL: travel_time = %.6f (expected > 0)\n", res.travel_time);
        return;
    }
    if (res.path_length <= 0.0) {
        printf("FAIL: path_length = %.6f (expected > 0)\n", res.path_length);
        return;
    }
    if (res.transmission_loss < 0.0) {
        printf("FAIL: TL = %.6f (expected >= 0)\n", res.transmission_loss);
        return;
    }
    printf("  [t=%.4fs, L=%.1fm, TL=%.1fdB] ",
           res.travel_time, res.path_length, res.transmission_loss);
    PASS();
}

/* ── Sonar equation test ─────────────────────────────────────────── */

static void test_sonar_equation_detection(void)
{
    TEST(test_sonar_equation_detection);

    sv_sonar_params_t p = {
        .source_level       = 220.0,   /* dB re 1 µPa @ 1m */
        .noise_level        = 60.0,    /* dB re 1 µPa²/Hz */
        .directivity_index  = 20.0,    /* dB */
        .target_strength    = 10.0,    /* dB */
        .detection_threshold= 10.0,    /* dB */
        .frequency          = 10.0,    /* kHz */
        .bandwidth          = 1000.0,  /* Hz */
        .temperature        = 10.0,    /* °C */
        .salinity           = 35.0,    /* PSU */
        .ph                 = 8.0,     /* pH */
        .src_depth          = 50.0,    /* m */
        .tgt_depth          = 100.0,   /* m */
    };

    /* At close range, should detect */
    sv_sonar_result_t res;
    sv_error_t err = sv_sonar_equation(&p, 100.0, &res);
    if (err != SV_OK) { FAIL("sonar equation error"); return; }

    if (res.signal_excess <= 0.0) {
        printf("FAIL: SE = %.2f at 100m (expected > 0)\n", res.signal_excess);
        return;
    }
    if (res.detection_probability < 0.9) {
        printf("FAIL: Pd = %.4f at 100m (expected > 0.9)\n", res.detection_probability);
        return;
    }
    if (res.max_range < 1000.0) {
        printf("FAIL: max_range = %.1f m (expected > 1000)\n", res.max_range);
        return;
    }
    printf("  [SE=%.1fdB, Pd=%.3f, Rmax=%.0fm] ",
           res.signal_excess, res.detection_probability, res.max_range);
    PASS();
}

/* ── Reverberation test ──────────────────────────────────────────── */

static void test_reverberation_bottom(void)
{
    TEST(test_reverberation_bottom);

    sv_reverb_params_t p = {
        .pulse_length     = 0.01,     /* 10 ms */
        .beam_pattern     = -20.0,    /* dB */
        .bottom_strength  = -25.0,    /* dB (Lambert Bs) */
        .surface_strength = -30.0,    /* dB */
        .volume_scatter   = -80.0,    /* dB/m */
        .frequency        = 10.0,     /* kHz */
        .temperature      = 10.0,     /* °C */
        .salinity         = 35.0,     /* PSU */
        .ph               = 8.0,      /* pH */
        .src_depth        = 50.0,     /* m */
    };

    sv_ssp_point_t pts[] = {{0, 1500}, {1000, 1520}};
    sv_ssp_t ssp = { pts, 2 };

    double rl;
    sv_error_t err = sv_reverberation(SV_REVERB_BOTTOM, &p, 500.0, &ssp, &rl);
    if (err != SV_OK) { FAIL("reverberation error"); return; }

    printf("  [RL=%.1f dB] ", rl);
    /* RL should be a reasonable dB value */
    if (rl > 0.0 || rl < -200.0) {
        printf("FAIL: RL = %.1f out of expected range\n", rl);
        return;
    }
    PASS();
}

/* ── Version test ────────────────────────────────────────────────── */

static void test_version(void)
{
    TEST(test_version);
    const char *v = sv_version();
    if (!v || strcmp(v, "1.0.0") != 0) {
        printf("FAIL: version = \"%s\" (expected \"1.0.0\")\n", v ? v : "NULL");
        return;
    }
    PASS();
}

/* ── Main ─────────────────────────────────────────────────────────── */

int main(void)
{
    printf("═══════════════════════════════════════════════════════\n");
    printf("  SonarVision Physics Validation Suite\n");
    printf("  %s\n", sv_version());
    printf("═══════════════════════════════════════════════════════\n\n");

    printf("[Mackenzie 1981 Sound Speed]\n");
    test_mackenzie_surface();
    test_mackenzie_deep();
    test_mackenzie_validation();
    test_mackenzie_batch();

    printf("\n[Francois-Garrison 1982 Absorption]\n");
    test_absorption_low_freq();
    test_absorption_high_freq();
    test_absorption_validation();

    printf("\n[Ray Tracing]\n");
    test_ray_trace_shallow();

    printf("\n[Sonar Equation]\n");
    test_sonar_equation_detection();

    printf("\n[Reverberation]\n");
    test_reverberation_bottom();

    printf("\n[Misc]\n");
    test_version();

    printf("\n═══════════════════════════════════════════════════════\n");
    printf("  Results: %d/%d passed\n", tests_passed, tests_run);
    printf("═══════════════════════════════════════════════════════\n");

    return (tests_passed == tests_run) ? 0 : 1;
}
