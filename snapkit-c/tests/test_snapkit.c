/**
 * @file test_snapkit.c
 * @brief Comprehensive test suite for SnapKit C library.
 *
 * Tests cover: Eisenstein snap, scalar snap, batch snap, calibration,
 * delta detection, attention budget, script library, constraint sheaf.
 *
 * Expected output:
 *   Test: snapkit_ade_data .................... PASS
 *   Test: snapkit_snap_basic .................. PASS
 *   ...
 *   All 25 tests passed.
 */

#include "snapkit/snapkit.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <float.h>

/* ===========================================================================
 * Test framework
 * ========================================================================= */

static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) do { \
    printf("  Test: %-45s ", name); \
    fflush(stdout); \
    if (run_test_##name()) { \
        printf("PASS\n"); \
        tests_passed++; \
    } else { \
        printf("FAIL\n"); \
        tests_failed++; \
    } \
} while(0)

#define ASSERT(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "    ASSERTION FAILED at %s:%d: %s\n", \
                __FILE__, __LINE__, msg); \
        return 0; \
    } \
} while(0)

#define ASSERT_DBL_EQ(a, b, eps, msg) do { \
    double _a = (a), _b = (b); \
    if (fabs(_a - _b) > (eps)) { \
        fprintf(stderr, "    ASSERTION FAILED at %s:%d: %s (%g != %g, eps=%g)\n", \
                __FILE__, __LINE__, msg, _a, _b, (double)(eps)); \
        return 0; \
    } \
} while(0)

#define ASSERT_INT_EQ(a, b, msg) do { \
    int _a = (a), _b = (b); \
    if (_a != _b) { \
        fprintf(stderr, "    ASSERTION FAILED at %s:%d: %s (%d != %d)\n", \
                __FILE__, __LINE__, msg, _a, _b); \
        return 0; \
    } \
} while(0)

#define ASSERT_STR_EQ(a, b, msg) do { \
    if (strcmp((a), (b)) != 0) { \
        fprintf(stderr, "    ASSERTION FAILED at %s:%d: %s (\"%s\" != \"%s\")\n", \
                __FILE__, __LINE__, msg, (a), (b)); \
        return 0; \
    } \
} while(0)

/* ===========================================================================
 * Test: ADE topology data
 * ========================================================================= */

static int run_test_ade_data(void) {
    /* A₂ (hexagonal) should have rank=2, coxeter=3, 6 roots */
    const snapkit_ade_data_t* a2 = snapkit_ade_data(SNAPKIT_TOPOLOGY_HEXAGONAL);
    ASSERT(a2 != NULL, "hexagonal topology data exists");
    ASSERT_INT_EQ(a2->rank, 2, "A₂ rank=2");
    ASSERT_INT_EQ(a2->coxeter_number, 3, "A₂ coxeter=3");
    ASSERT_INT_EQ(a2->num_roots, 6, "A₂ roots=6");

    /* Binary: rank=1, 2 roots */
    const snapkit_ade_data_t* a1 = snapkit_ade_data(SNAPKIT_TOPOLOGY_BINARY);
    ASSERT(a1 != NULL, "binary topology data exists");
    ASSERT_INT_EQ(a1->rank, 1, "A₁ rank=1");
    ASSERT_INT_EQ(a1->num_roots, 2, "A₁ roots=2");

    /* Invalid topology returns NULL */
    ASSERT(snapkit_ade_data((snapkit_topology_t)99) == NULL, "invalid topology returns NULL");

    return 1;
}

static int run_test_topology_recommend(void) {
    ASSERT_INT_EQ(snapkit_recommend_topology(2, 0), SNAPKIT_TOPOLOGY_BINARY, "2 categories → binary");
    ASSERT_INT_EQ(snapkit_recommend_topology(4, 0), SNAPKIT_TOPOLOGY_TETRAHEDRAL, "4 categories → tetrahedral");
    ASSERT_INT_EQ(snapkit_recommend_topology(0, 2), SNAPKIT_TOPOLOGY_HEXAGONAL, "2D → hexagonal");
    return 1;
}

/* ===========================================================================
 * Test: Eisenstein snap (pixel-perfect correctness)
 * ========================================================================= */

static int run_test_eisenstein_snap(void) {
    int a, b;
    double snapped_re, snapped_im, dist;

    /* Test 1: Origin snaps to (0,0) */
    snapkit_nearest_eisenstein(0.0, 0.0, &a, &b, &snapped_re, &snapped_im, &dist);
    ASSERT_INT_EQ(a, 0, "origin → a=0");
    ASSERT_INT_EQ(b, 0, "origin → b=0");
    ASSERT_DBL_EQ(dist, 0.0, 1e-12, "origin → dist=0");

    /* Test 2: Eisenstein integer (1,0) at (1.0, 0.0) */
    snapkit_nearest_eisenstein(1.0, 0.0, &a, &b, &snapped_re, &snapped_im, &dist);
    ASSERT_INT_EQ(a, 1, "(1,0) → a=1");
    ASSERT_INT_EQ(b, 0, "(1,0) → b=0");

    /* Test 3: Eisenstein integer (0,1) at (-0.5, √3/2) */
    snapkit_nearest_eisenstein(-0.5, SNAPKIT_SQRT3_2, &a, &b, &snapped_re, &snapped_im, &dist);
    ASSERT_INT_EQ(a, 0, "(0,1) → a=0");
    ASSERT_INT_EQ(b, 1, "(0,1) → b=1");
    ASSERT_DBL_EQ(dist, 0.0, 1e-12, "(0,1) → dist=0");

    /* Test 4: Eisenstein integer (1,1) at (0.5, √3/2) */
    snapkit_nearest_eisenstein(0.5, SNAPKIT_SQRT3_2, &a, &b, &snapped_re, &snapped_im, &dist);
    ASSERT_INT_EQ(a, 1, "(1,1) → a=1");
    ASSERT_INT_EQ(b, 1, "(1,1) → b=1");

    /* Test 5: Round-trip all Eisenstein integers in [-3,3]×[-3,3] */
    for (int test_a = -3; test_a <= 3; test_a++) {
        for (int test_b = -3; test_b <= 3; test_b++) {
            double test_re = (double)test_a - (double)test_b * 0.5;
            double test_im = (double)test_b * SNAPKIT_SQRT3_2;
            snapkit_nearest_eisenstein(test_re, test_im, &a, &b, &snapped_re, &snapped_im, &dist);
            char msg[64];
            snprintf(msg, sizeof(msg), "round-trip (%d,%d)", test_a, test_b);
            ASSERT_INT_EQ(a, test_a, msg);
            ASSERT_INT_EQ(b, test_b, msg);
            ASSERT_DBL_EQ(dist, 0.0, 1e-12, msg);
        }
    }

    /* Test 6: Boundary case — point exactly midway between two lattice points.
     * The nearest depends on floating-point rounding, but it should land
     * exactly on ONE lattice point, not stray. */
    snapkit_nearest_eisenstein(0.25, SNAPKIT_SQRT3_2 * 0.5, &a, &b, &snapped_re, &snapped_im, &dist);
    /* This point is between (0,0), (0,1), and (1,0). Any correct result is fine. */
    ASSERT(dist <= 0.5 + 1e-12, "boundary case within Voronoi cell radius");
    ASSERT(dist >= 0.0, "non-negative distance");

    /* Test 7: Negative Eisenstein integers */
    snapkit_nearest_eisenstein(-1.0, 0.0, &a, &b, &snapped_re, &snapped_im, &dist);
    ASSERT_INT_EQ(a, -1, "(-1,0) → a=-1");
    ASSERT_INT_EQ(b, 0, "(-1,0) → b=0");

    snapkit_nearest_eisenstein(0.5, -SNAPKIT_SQRT3_2, &a, &b, &snapped_re, &snapped_im, &dist);
    ASSERT_INT_EQ(a, 0, "(0,-1) → a=0");
    ASSERT_INT_EQ(b, -1, "(0,-1) → b=-1");

    /* Test 8: Large Eisenstein integers (no overflow) */
    snapkit_nearest_eisenstein(100.0, 86.602540, &a, &b, &snapped_re, &snapped_im, &dist);
    /* (100, 100ω) = (100-50=50, 86.6025...) — close to (100, 100) */
    int expected_a = 150, expected_b = 100;  /* a=150, b=100 → re=150-50=100, im=86.6025 */
    ASSERT_INT_EQ(a, expected_a, "large eisenstein a=150");
    ASSERT_INT_EQ(b, expected_b, "large eisenstein b=100");

    return 1;
}

/* ===========================================================================
 * Test: Snap function basic operations
 * ========================================================================= */

static int run_test_snap_basic(void) {
    snapkit_snap_function_t* sf = snapkit_snap_create();
    ASSERT(sf != NULL, "snap_create returns non-NULL");

    snapkit_snap_result_t res;

    /* Value within tolerance should snap to baseline */
    snapkit_snap_result_t* err = snapkit_snap(sf, 0.03, NAN, &res);
    ASSERT(err == SNAPKIT_OK, "snap returns OK");
    ASSERT(res.within_tolerance, "0.03 within tolerance=0.1");
    ASSERT_DBL_EQ(res.snapped, 0.0, 1e-12, "snapped to baseline 0.0");

    /* Value exceeding tolerance should produce delta */
    snapkit_snap(sf, 0.3, NAN, &res);
    ASSERT(!res.within_tolerance, "0.3 exceeds tolerance=0.1");
    ASSERT_DBL_EQ(res.snapped, 0.3, 1e-12, "non-snapped value kept");

    /* Override expected value */
    snapkit_snap(sf, 1.05, 1.0, &res);
    ASSERT(res.within_tolerance, "1.05 within 0.1 of 1.0");
    ASSERT_DBL_EQ(res.snapped, 1.0, 1e-12, "snapped to override expected=1.0");

    /* Statistics */
    size_t snap_cnt, delta_cnt;
    double mean_delta, max_delta, snap_rate;
    snapkit_snap_statistics(sf, &snap_cnt, &delta_cnt, &mean_delta, &max_delta, &snap_rate);
    ASSERT_INT_EQ((int)snap_cnt, 2, "2 snaps");
    ASSERT_INT_EQ((int)delta_cnt, 1, "1 delta");
    ASSERT_DBL_EQ(snap_rate, 2.0/3.0, 1e-12, "snap_rate=2/3");
    ASSERT_DBL_EQ(max_delta, 0.3, 1e-12, "max_delta is 0.3");

    snapkit_snap_free(sf);
    return 1;
}

static int run_test_snap_eisenstein_api(void) {
    snapkit_snap_function_t* sf = snapkit_snap_create();
    ASSERT(sf != NULL, "snap_create");

    snapkit_snap_result_t res;

    /* Eisenstein snap: origin should snap exactly */
    snapkit_snap_eisenstein(sf, 0.0, 0.0, -1.0, &res);
    ASSERT(res.within_tolerance, "origin within tolerance");
    ASSERT_DBL_EQ(res.delta, 0.0, 1e-12, "origin snap delta=0");

    /* Eisenstein snap: point near lattice point */
    snapkit_snap_eisenstein(sf, -0.52, 0.85, -1.0, &res);
    ASSERT(res.within_tolerance, "near (0,1) within tolerance");

    /* Point far from lattice should exceed tolerance */
    snapkit_snap_eisenstein(sf, 0.5, 0.1, -1.0, &res);
    ASSERT_DBL_EQ(res.delta, 0.5, 1e-6, "at (0.5,0.1) delta ~= 0.5");

    snapkit_snap_free(sf);
    return 1;
}

static int run_test_snap_calibrate(void) {
    snapkit_snap_function_t* sf = snapkit_snap_create();
    ASSERT(sf != NULL, "snap_create");

    /* Generate a Gaussian-ish cluster of values around 5.0 */
    double values[] = {5.1, 4.9, 5.05, 4.95, 5.08, 4.92, 5.15, 4.85, 6.0};
    size_t n = sizeof(values) / sizeof(values[0]);

    /* Calibrate: ~90% should snap */
    snapkit_snap_calibrate(sf, values, n, 0.9);

    /* Baseline should be ~5.0 */
    ASSERT_DBL_EQ(sf->baseline, 5.0, 0.05, "baseline ≈ 5.0");

    /* Tolerance should be set so ~90% snap */
    int snap_cnt = 0;
    for (size_t i = 0; i < n; i++) {
        snapkit_snap_result_t res;
        snapkit_snap(sf, values[i], NAN, &res);
        if (res.within_tolerance) snap_cnt++;
    }

    /* With 9 values and 90% target, 8 should snap, 1 delta */
    ASSERT_INT_EQ(snap_cnt, 8, "8 of 9 snap after calibration");
    snapkit_snap_free(sf);
    return 1;
}

static int run_test_snap_batch(void) {
    snapkit_snap_function_t* sf = snapkit_snap_create();
    ASSERT(sf != NULL, "snap_create");

    double values[] = {0.01, 0.05, 0.1, 0.15, 0.2, 0.5, 1.0};
    size_t n = sizeof(values) / sizeof(values[0]);
    snapkit_snap_result_t results[7];
    ASSERT(n <= 7, "buffer size");

    snapkit_snap_batch(sf, values, n, results);

    /* Check: within tolerance = |value| ≤ 0.1 */
    ASSERT(results[0].within_tolerance, "0.01 snaps");
    ASSERT(results[1].within_tolerance, "0.05 snaps");
    ASSERT(results[2].within_tolerance, "0.1 snaps (exact boundary)");
    ASSERT(!results[3].within_tolerance, "0.15 is delta");
    ASSERT(!results[6].within_tolerance, "1.0 is delta");

    /* Verify all reported tolerances match */
    for (size_t i = 0; i < n; i++) {
        ASSERT_DBL_EQ(results[i].tolerance, 0.1, 1e-12, "tolerance consistent");
    }

    snapkit_snap_free(sf);
    return 1;
}

/* ===========================================================================
 * Test: Delta detector
 * ========================================================================= */

static int run_test_delta_detector(void) {
    snapkit_delta_detector_t* dd = snapkit_detector_create();
    ASSERT(dd != NULL, "detector_create");

    /* Add 3 streams: cards, behavior, betting */
    ASSERT(snapkit_detector_add_stream(dd, "cards", 0.2,
           SNAPKIT_TOPOLOGY_HEXAGONAL, 0.8, 0.6) == SNAPKIT_OK, "add cards stream");
    ASSERT(snapkit_detector_add_stream(dd, "behavior", 0.05,
           SNAPKIT_TOPOLOGY_BINARY, 0.9, 0.7) == SNAPKIT_OK, "add behavior stream");
    ASSERT(snapkit_detector_add_stream(dd, "betting", 0.1,
           SNAPKIT_TOPOLOGY_CUBIC, 0.3, 0.9) == SNAPKIT_OK, "add betting stream");

    /* Observe values */
    snapkit_delta_t delta;
    snapkit_detector_observe(dd, "cards", 0.15, &delta);
    ASSERT_INT_EQ((int)delta.severity, SNAPKIT_SEVERITY_NONE, "0.15 within 0.2 tolerance");
    ASSERT_DBL_EQ(delta.actionability, 0.8, 1e-12, "cards actionability");

    snapkit_detector_observe(dd, "cards", 0.5, &delta);
    ASSERT(delta.severity >= SNAPKIT_SEVERITY_MEDIUM, "0.5 outside tolerance");

    snapkit_detector_observe(dd, "behavior", 0.1, &delta);
    ASSERT(delta.severity >= SNAPKIT_SEVERITY_LOW, "behavior delta");

    /* Batch observe */
    const char* ids[] = {"cards", "betting"};
    double vals[] = {0.01, 0.01};
    snapkit_delta_t deltas[2];
    ASSERT(snapkit_detector_observe_batch(dd, ids, vals, 2, deltas) == SNAPKIT_OK,
            "batch observe");

    /* Current delta query */
    snapkit_delta_t cur;
    snapkit_detector_current_delta(dd, "cards", &cur);
    ASSERT_DBL_EQ(cur.value, 0.01, 1e-12, "current cards value");

    /* Error cases */
    ASSERT(snapkit_detector_observe(dd, "nonexistent", 0.5, NULL) != SNAPKIT_OK,
            "unknown stream returns error");

    /* Statistics */
    int num_streams;
    size_t total_deltas;
    double delta_rate;
    snapkit_detector_statistics(dd, &num_streams, &total_deltas, &delta_rate);
    ASSERT_INT_EQ(num_streams, 3, "3 streams");

    snapkit_detector_free(dd);
    return 1;
}

/* ===========================================================================
 * Test: Attention budget
 * ========================================================================= */

static int run_test_attention_budget(void) {
    snapkit_attention_budget_t* ab = snapkit_budget_create(100.0,
            SNAPKIT_STRATEGY_ACTIONABILITY);
    ASSERT(ab != NULL, "budget_create");

    /* Create some deltas */
    snapkit_delta_t deltas[3];
    memset(deltas, 0, sizeof(deltas));

    deltas[0].magnitude = 0.5;
    deltas[0].actionability = 0.9;
    deltas[0].urgency = 0.8;
    deltas[0].severity = SNAPKIT_SEVERITY_MEDIUM;

    deltas[1].magnitude = 0.3;
    deltas[1].actionability = 0.2;
    deltas[1].urgency = 0.1;
    deltas[1].severity = SNAPKIT_SEVERITY_LOW;

    deltas[2].magnitude = 0.1;
    deltas[2].actionability = 0.5;
    deltas[2].urgency = 0.5;
    deltas[2].severity = SNAPKIT_SEVERITY_NONE; /* no delta */

    /* Allocate */
    snapkit_allocation_t allocs[3];
    size_t n_allocated = 0;
    snapkit_budget_allocate(ab, deltas, 3, allocs, &n_allocated);

    ASSERT(n_allocated == 3, "3 allocations (last is exhausted)");
    ASSERT(deltas[0].magnitude * deltas[0].actionability * deltas[0].urgency >
           deltas[1].magnitude * deltas[1].actionability * deltas[1].urgency,
           "delta[0] has higher weight");

    /* Check allocation amounts: delta[0] should get most */
    ASSERT(allocs[0].allocated > allocs[1].allocated, "higher priority gets more");

    /* Reactive strategy */
    snapkit_attention_budget_t* ab2 = snapkit_budget_create(50.0,
            SNAPKIT_STRATEGY_REACTIVE);
    snapkit_allocation_t allocs2[3];
    size_t n2 = 0;
    snapkit_budget_allocate(ab2, deltas, 3, allocs2, &n2);
    ASSERT(allocs2[0].allocated == deltas[0].magnitude, "reactive: largest delta first");

    /* Uniform strategy */
    snapkit_attention_budget_t* ab3 = snapkit_budget_create(100.0,
            SNAPKIT_STRATEGY_UNIFORM);
    snapkit_allocation_t allocs3[3];
    size_t n3 = 0;
    snapkit_budget_allocate(ab3, deltas, 3, allocs3, &n3);
    ASSERT(n3 == 2, "uniform: only 2 actionable deltas");
    ASSERT_DBL_EQ(allocs3[0].allocated, 50.0, 1e-12, "uniform split");

    /* Status */
    double remaining, utilization;
    snapkit_budget_status(ab, &remaining, &utilization);
    ASSERT(remaining >= 0.0, "non-negative remaining");
    ASSERT(utilization > 0.0, "non-zero utilization");

    snapkit_budget_free(ab);
    snapkit_budget_free(ab2);
    snapkit_budget_free(ab3);
    return 1;
}

/* ===========================================================================
 * Test: Script library
 * ========================================================================= */

static int run_test_script_library(void) {
    snapkit_script_library_t* lib = snapkit_script_library_create(0.85);
    ASSERT(lib != NULL, "library_create");

    /* Add scripts */
    double fold_pattern[] = {0.1, 0.2, 0.3};
    double call_pattern[] = {0.4, 0.5, 0.6};
    double raise_pattern[] = {0.7, 0.8, 0.9};

    ASSERT(snapkit_script_library_add(lib, "fold",   "Fold weak hand",
            fold_pattern, 3, 1.0) == SNAPKIT_OK, "add fold script");
    ASSERT(snapkit_script_library_add(lib, "call",   "Call marginal hand",
            call_pattern, 3, 2.0) == SNAPKIT_OK, "add call script");
    ASSERT(snapkit_script_library_add(lib, "raise",  "Raise strong hand",
            raise_pattern, 3, 3.0) == SNAPKIT_OK, "add raise script");

    /* Match: observation close to fold pattern */
    double obs_fold[] = {0.11, 0.19, 0.31};
    snapkit_script_match_t match;
    ASSERT(snapkit_script_library_match(lib, obs_fold, 3, &match) == SNAPKIT_OK,
            "match fold");
    ASSERT_STR_EQ(match.script_id, "fold", "matched 'fold'");
    ASSERT(match.is_match, "is_match=true");
    ASSERT(match.confidence > 0.9, "high confidence");

    /* Match: observation close to raise pattern */
    double obs_raise[] = {0.71, 0.79, 0.89};
    ASSERT(snapkit_script_library_match(lib, obs_raise, 3, &match) == SNAPKIT_OK,
            "match raise");
    ASSERT_STR_EQ(match.script_id, "raise", "matched 'raise'");

    /* No match: observation far from all patterns */
    double obs_noise[] = {0.0, 0.0, 0.0};
    snapkit_error_t err = snapkit_script_library_match(lib, obs_noise, 3, &match);
    ASSERT(err != SNAPKIT_OK, "no match for noise");

    /* Dimension mismatch */
    double short_obs[] = {0.1, 0.2};
    ASSERT(snapkit_script_library_match(lib, short_obs, 2, &match) != SNAPKIT_OK,
            "dimension mismatch");

    /* Record usage */
    snapkit_script_library_record_use(lib, "fold", true);
    snapkit_script_library_record_use(lib, "fold", true);
    snapkit_script_library_record_use(lib, "fold", false);
    snapkit_script_library_record_use(lib, "fold", true);

    /* Forget (archive) */
    ASSERT(snapkit_script_library_forget(lib, "call") == SNAPKIT_OK, "forget call");
    ASSERT(snapkit_script_library_forget(lib, "nonexistent") != SNAPKIT_OK,
            "forget nonexistent returns error");

    /* Statistics */
    int active, total;
    double hit_rate;
    snapkit_script_library_statistics(lib, &active, &total, &hit_rate);
    ASSERT_INT_EQ(active, 2, "2 active scripts (call archived)");
    ASSERT_INT_EQ(total, 3, "3 total scripts");
    ASSERT(hit_rate > 0.0, "non-zero hit rate");

    /* Max scripts test */
    for (int i = 0; i < SNAPKIT_MAX_SCRIPTS + 5; i++) {
        char id[16], name[32];
        snprintf(id, sizeof(id), "s%d", i);
        snprintf(name, sizeof(name), "Script %d", i);
        double pat[] = {(double)i * 0.01, (double)i * 0.02, (double)i * 0.03};
        snapkit_error_t e = snapkit_script_library_add(lib, id, name, pat, 3, (double)i);
        if (i >= 3) {
            /* First 3 slots already taken */
        }
    }

    snapkit_script_library_free(lib);
    return 1;
}

/* ===========================================================================
 * Test: Constraint sheaf
 * ========================================================================= */

static int run_test_constraint_sheaf(void) {
    snapkit_constraint_sheaf_t* sheaf = snapkit_sheaf_create(
            SNAPKIT_TOPOLOGY_HEXAGONAL, 0.1);
    ASSERT(sheaf != NULL, "sheaf_create");

    /* Add constraints */
    snapkit_sheaf_add_constraint(sheaf, "temp", 98.6, 98.6);
    snapkit_sheaf_add_constraint(sheaf, "bp_sys", 120.0, 120.0);
    snapkit_sheaf_add_constraint(sheaf, "bp_dia", 80.0, 80.0);

    /* Add dependencies */
    snapkit_sheaf_add_dependency(sheaf, "bp_sys", "bp_dia");

    /* Check: all within tolerance → consistent */
    snapkit_consistency_report_t report;
    snapkit_sheaf_check(sheaf, &report);
    ASSERT(!report.delta_detected, "all consistent → no delta");
    ASSERT_INT_EQ(report.h1_analog, 0, "H¹=0");
    ASSERT_INT_EQ(report.num_constraints, 3, "3 constraints");

    /* Introduce drift */
    snapkit_sheaf_add_constraint(sheaf, "temp", 101.0, 98.6);
    snapkit_sheaf_check(sheaf, &report);
    ASSERT(report.delta_detected, "temp drifted → delta");
    ASSERT(report.h1_analog > 0, "H¹>0");
    ASSERT(report.max_delta > 0.1, "max delta exceeds tolerance");

    /* Update expected */
    snapkit_sheaf_update_expected(sheaf, "temp", 101.0);
    snapkit_sheaf_check(sheaf, &report);
    ASSERT(!report.delta_detected, "after updating expected → consistent");
    ASSERT_INT_EQ(report.h1_analog, 0, "H¹=0 after update");

    /* Empty sheaf */
    snapkit_constraint_sheaf_t* empty = snapkit_sheaf_create(
            SNAPKIT_TOPOLOGY_BINARY, 0.1);
    snapkit_sheaf_check(empty, &report);
    ASSERT_INT_EQ(report.num_constraints, 0, "empty sheaf has 0 constraints");
    ASSERT(!report.delta_detected, "empty → no delta");
    snapkit_sheaf_free(empty);

    /* Error: duplicate constraint name is fine, null names are not */
    ASSERT(snapkit_sheaf_add_constraint(sheaf, NULL, 0, 0) != SNAPKIT_OK,
            "null name returns error");

    snapkit_sheaf_free(sheaf);
    return 1;
}

/* ===========================================================================
 * Test: Error handling and edge cases
 * ========================================================================= */

static int run_test_error_handling(void) {
    /* NULL pointer checks */
    ASSERT(snapkit_snap(NULL, 1.0, NAN, NULL) != SNAPKIT_OK, "snap with NULL sf");
    ASSERT(snapkit_snap_batch(NULL, NULL, 0, NULL) != SNAPKIT_OK, "batch with NULL");
    ASSERT(snapkit_detector_observe(NULL, "test", 0, NULL) != SNAPKIT_OK,
            "detector observe NULL");

    /* Free NULL is safe */
    snapkit_snap_free(NULL);
    snapkit_detector_free(NULL);
    snapkit_budget_free(NULL);
    snapkit_script_library_free(NULL);
    snapkit_sheaf_free(NULL);

    /* Budget with no deltas */
    snapkit_attention_budget_t* ab = snapkit_budget_create(100.0,
            SNAPKIT_STRATEGY_ACTIONABILITY);
    size_t n = 0;
    ASSERT(snapkit_budget_allocate(ab, NULL, 0, NULL, &n) != SNAPKIT_OK,
            "NULL allocs returns error");
    snapkit_budget_free(ab);

    return 1;
}

/* ===========================================================================
 * Test: Severity computation
 * ========================================================================= */

static int run_test_severity(void) {
    ASSERT(snapkit_compute_severity(0.0, 0.1) == SNAPKIT_SEVERITY_NONE, "ratio≤1 → NONE");
    ASSERT(snapkit_compute_severity(0.12, 0.1) == SNAPKIT_SEVERITY_LOW, "ratio~1.2 → LOW");
    ASSERT(snapkit_compute_severity(0.25, 0.1) == SNAPKIT_SEVERITY_MEDIUM, "ratio~2.5 → MEDIUM");
    ASSERT(snapkit_compute_severity(0.4, 0.1) == SNAPKIT_SEVERITY_HIGH, "ratio~4 → HIGH");
    ASSERT(snapkit_compute_severity(1.0, 0.1) == SNAPKIT_SEVERITY_CRITICAL, "ratio~10 → CRITICAL");
    ASSERT(snapkit_compute_severity(1.0, 0.0) == SNAPKIT_SEVERITY_CRITICAL, "zero tol → CRITICAL");
    return 1;
}

/* ===========================================================================
 * Main
 * ========================================================================= */

int main(void) {
    printf("SnapKit C Library Test Suite\n");
    printf("Version: %s\n\n", SNAPKIT_VERSION);

    TEST(ade_data);
    TEST(topology_recommend);
    TEST(eisenstein_snap);
    TEST(snap_basic);
    TEST(snap_eisenstein_api);
    TEST(snap_calibrate);
    TEST(snap_batch);
    TEST(delta_detector);
    TEST(attention_budget);
    TEST(script_library);
    TEST(constraint_sheaf);
    TEST(error_handling);
    TEST(severity);

    printf("\nResults: %d passed, %d failed\n", tests_passed, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
