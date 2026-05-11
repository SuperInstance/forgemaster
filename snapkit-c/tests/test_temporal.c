/* test_temporal.c — tests for beat grid and temporal snap */
#include <stdio.h>
#include <math.h>
#include "snapkit.h"

static int tests_run = 0;
static int tests_pass = 0;

#define ASSERT(cond, msg) do { \
    tests_run++; \
    if (cond) { tests_pass++; } \
    else { printf("  FAIL: %s\n", msg); } \
} while(0)

#define ASSERT_FEQ(a, b, eps, msg) ASSERT(fabs((a)-(b)) < (eps), msg)
#define ASSERT_EQ(a, b, msg) ASSERT((a) == (b), msg)

int main(void) {
    printf("Temporal tests\n");

    /* --- Beat grid init --- */
    {
        sk_beat_grid g;
        int rc = sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        ASSERT_EQ(rc, 0, "init success");
        ASSERT_FEQ(g.period, 1.0, 1e-12, "period = 1");
        ASSERT_FEQ(g.inv_period, 1.0, 1e-12, "inv_period = 1");

        rc = sk_beat_grid_init(&g, -1.0, 0.0, 0.0);
        ASSERT_EQ(rc, -1, "negative period rejected");
    }

    /* --- Nearest beat --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        int bi;
        double bt = sk_beat_grid_nearest(&g, 2.3, &bi);
        ASSERT_EQ(bi, 2, "beat index = 2");
        ASSERT_FEQ(bt, 2.0, 1e-12, "beat time = 2.0");
    }

    /* --- Nearest beat with phase --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 0.5, 0.1, 0.0);
        int bi;
        double bt = sk_beat_grid_nearest(&g, 0.35, &bi);
        ASSERT_FEQ(bt, 0.1, 1e-12, "beat with phase: snaps to 0.1");
        ASSERT_EQ(bi, 0, "beat index with phase");
    }

    /* --- Snap on beat --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        sk_temporal_result r = sk_beat_grid_snap(&g, 2.0, 0.1);
        ASSERT(r.is_on_beat, "exactly on beat");
        ASSERT_FEQ(r.offset, 0.0, 1e-12, "offset = 0");
        ASSERT_FEQ(r.beat_phase, 0.0, 1e-9, "phase = 0");
    }

    /* --- Snap off beat --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        sk_temporal_result r = sk_beat_grid_snap(&g, 2.45, 0.1);
        ASSERT(!r.is_on_beat, "too far off beat");
        ASSERT_FEQ(r.offset, 0.45, 1e-9, "offset = 0.45");
    }

    /* --- Snap near beat (within tolerance) --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        sk_temporal_result r = sk_beat_grid_snap(&g, 2.05, 0.1);
        ASSERT(r.is_on_beat, "within tolerance");
        ASSERT_FEQ(r.offset, 0.05, 1e-9, "offset = 0.05");
    }

    /* --- Beat phase --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        sk_temporal_result r = sk_beat_grid_snap(&g, 2.3, 0.1);
        ASSERT_FEQ(r.beat_phase, 0.3, 1e-9, "phase = 0.3");
    }

    /* --- Batch snap --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        double ts[] = {0.0, 0.5, 1.0, 1.5, 2.0};
        sk_temporal_result out[5];
        sk_beat_grid_snap_batch(&g, ts, 5, 0.1, out);
        ASSERT(out[0].is_on_beat, "batch[0] on beat");
        ASSERT(!out[1].is_on_beat, "batch[1] off beat");
        ASSERT(out[2].is_on_beat, "batch[2] on beat");
        ASSERT(!out[3].is_on_beat, "batch[3] off beat");
        ASSERT(out[4].is_on_beat, "batch[4] on beat");
    }

    /* --- Beats in range --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        double beats[10];
        int n = sk_beat_grid_range(&g, 0.5, 3.5, beats, 10);
        ASSERT_EQ(n, 3, "3 beats in [0.5, 3.5]");
        ASSERT_FEQ(beats[0], 1.0, 1e-12, "first beat = 1.0");
        ASSERT_FEQ(beats[2], 3.0, 1e-12, "last beat = 3.0");
    }

    /* --- T-minus-0 detection --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        sk_temporal_snap ts;
        sk_temporal_snap_init(&ts, &g, 0.1, 0.05, 3);

        /* Feed values that cross zero: +0.2, +0.1, -0.1 */
        sk_temporal_result r;
        r = sk_temporal_observe(&ts, 0.0, 0.2);
        ASSERT(!r.is_t_minus_0, "not t0 yet (1st)");

        r = sk_temporal_observe(&ts, 1.0, 0.1);
        ASSERT(!r.is_t_minus_0, "not t0 yet (2nd)");

        r = sk_temporal_observe(&ts, 2.0, -0.1);
        /* Should detect zero crossing: 0.2 → 0.1 → -0.1, last val |−0.1| ≤ 0.05? */
        /* Actually -0.1 > threshold 0.05 in absolute, so no t0 yet */
        ASSERT(!r.is_t_minus_0, "not t0 (value exceeds threshold)");

        r = sk_temporal_observe(&ts, 3.0, -0.03);
        /* Now: 0.1 → -0.1 → -0.03, sign change and |−0.03| ≤ 0.05 */
        ASSERT(r.is_t_minus_0, "t0 detected on sign change + small value");
    }

    /* --- Reset --- */
    {
        sk_beat_grid g;
        sk_beat_grid_init(&g, 1.0, 0.0, 0.0);
        sk_temporal_snap ts;
        sk_temporal_snap_init(&ts, &g, 0.1, 0.05, 3);
        sk_temporal_observe(&ts, 0.0, 0.5);
        sk_temporal_reset(&ts);
        ASSERT_EQ(ts.hist_len, 0, "history cleared after reset");
    }

    printf("  %d/%d passed\n", tests_pass, tests_run);
    return (tests_pass == tests_run) ? 0 : 1;
}
