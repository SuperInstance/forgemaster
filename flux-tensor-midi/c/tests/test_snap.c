#include "flux_midi/snap.h"
#include <stdio.h>
#include <math.h>
#include <assert.h>
#include <string.h>

#define ASSERT_FEQ(a, b, eps) do { \
    double _a = (a), _b = (b), _eps = (eps); \
    if (fabs(_a - _b) > _eps) { \
        fprintf(stderr, "FAIL %s:%d: %.6f != %.6f (eps=%.6f)\n", \
                __FILE__, __LINE__, _a, _b, _eps); \
        return 1; \
    } \
} while(0)

int test_steady(void) {
    SnapResult r;
    /* Equal intervals = steady */
    eisenstein_snap(1.0, 1.0, 1.0, &r);
    assert(r.shape == SNAP_STEADY);
    printf("  PASS test_steady (shape=%s, norm=%.1f)\n",
           snap_shape_name(r.shape), r.norm);
    return 0;
}

int test_burst(void) {
    SnapResult r;
    /* b >> a = burst */
    eisenstein_snap(0.2, 2.0, 1.0, &r);
    assert(r.shape == SNAP_BURST);
    printf("  PASS test_burst (ratio=%.2f)\n", r.ratio);
    return 0;
}

int test_collapse(void) {
    SnapResult r;
    /* b << a = collapse */
    eisenstein_snap(2.0, 0.1, 1.0, &r);
    assert(r.shape == SNAP_COLLAPSE);
    printf("  PASS test_collapse (ratio=%.2f)\n", r.ratio);
    return 0;
}

int test_grid_snap(void) {
    int subs;
    double snapped = snap_to_grid(0.52, 0.25, &subs);
    ASSERT_FEQ(snapped, 0.50, 1e-12);  /* 2 subdivisions of 0.25 */
    assert(subs == 2);

    snapped = snap_to_grid(0.62, 0.25, &subs);
    ASSERT_FEQ(snapped, 0.50, 1e-12);  /* 2.48 rounds to 2 subdivisions */
    assert(subs == 2);
    printf("  PASS test_grid_snap\n");
    return 0;
}

int test_shape_names(void) {
    assert(strcmp(snap_shape_name(SNAP_BURST), "burst") == 0);
    assert(strcmp(snap_shape_name(SNAP_STEADY), "steady") == 0);
    assert(strcmp(snap_shape_name(SNAP_COLLAPSE), "collapse") == 0);
    assert(strcmp(snap_shape_name(SNAP_ACCEL), "accel") == 0);
    assert(strcmp(snap_shape_name(SNAP_DECEL), "decel") == 0);
    printf("  PASS test_shape_names\n");
    return 0;
}

int main(void) {
    printf("=== Eisenstein Snap Tests ===\n");
    int fails = 0;
    fails += test_steady();
    fails += test_burst();
    fails += test_collapse();
    fails += test_grid_snap();
    fails += test_shape_names();
    printf(fails == 0 ? "All tests passed.\n" : "%d test(s) FAILED.\n", fails);
    return fails;
}
