#include "flux_midi/clock.h"
#include <stdio.h>
#include <math.h>
#include <assert.h>

#define ASSERT_FEQ(a, b, eps) do { \
    double _a = (a), _b = (b), _eps = (eps); \
    if (fabs(_a - _b) > _eps) { \
        fprintf(stderr, "FAIL %s:%d: %.6f != %.6f (eps=%.6f)\n", \
                __FILE__, __LINE__, _a, _b, _eps); \
        return 1; \
    } \
} while(0)

int test_init(void) {
    TZeroClock clk;
    tzero_init(&clk, 1.0, 0.3, 1);
    ASSERT_FEQ(clk.interval, 1.0, 1e-12);
    ASSERT_FEQ(clk.ewma_alpha, 0.3, 1e-12);
    assert(clk.adaptive == 1);
    assert(clk.tick_count == 0);
    printf("  PASS test_init\n");
    return 0;
}

int test_observe(void) {
    TZeroClock clk;
    tzero_init(&clk, 1.0, 0.3, 1);

    tzero_observe(&clk, 0.0);
    assert(clk.tick_count == 1);
    ASSERT_FEQ(clk.t_last, 0.0, 1e-12);

    tzero_observe(&clk, 1.1);
    assert(clk.tick_count == 2);
    ASSERT_FEQ(clk.t_last, 1.1, 1e-12);
    /* EWMA should have adapted: 0.3 * 1.1 + 0.7 * 1.0 = 1.03 */
    ASSERT_FEQ(clk.ewma_interval, 1.03, 1e-10);
    printf("  PASS test_observe\n");
    return 0;
}

int test_check_states(void) {
    TZeroClock clk;
    tzero_init(&clk, 1.0, 0.3, 0); /* non-adaptive */

    tzero_observe(&clk, 0.0);

    assert(tzero_check(&clk, 0.5) == TZERO_ON_TIME);
    assert(tzero_check(&clk, 1.0) == TZERO_ON_TIME);
    assert(tzero_check(&clk, 1.4) == TZERO_ON_TIME);
    assert(tzero_check(&clk, 2.0) == TZERO_LATE);
    assert(tzero_check(&clk, 4.0) == TZERO_SILENT);
    assert(tzero_check(&clk, 15.0) == TZERO_DEAD);
    printf("  PASS test_check_states\n");
    return 0;
}

int test_delta(void) {
    TZeroClock clk;
    tzero_init(&clk, 1.0, 0.3, 0);

    tzero_observe(&clk, 0.0);
    ASSERT_FEQ(tzero_delta(&clk, 0.5), -0.5, 1e-12);  /* early */
    ASSERT_FEQ(tzero_delta(&clk, 1.5),  0.5, 1e-12);  /* late */
    printf("  PASS test_delta\n");
    return 0;
}

int test_missed_ticks(void) {
    TZeroClock clk;
    tzero_init(&clk, 1.0, 0.3, 0);

    tzero_observe(&clk, 0.0);
    assert(tzero_missed_ticks(&clk, 0.5) == 0);
    assert(tzero_missed_ticks(&clk, 2.5) == 1);
    assert(tzero_missed_ticks(&clk, 5.5) == 4);
    printf("  PASS test_missed_ticks\n");
    return 0;
}

int test_effective_interval(void) {
    TZeroClock clk;
    tzero_init(&clk, 1.0, 0.3, 0);
    ASSERT_FEQ(tzero_effective_interval(&clk), 1.0, 1e-12);

    clk.adaptive = 1;
    clk.ewma_interval = 1.05;
    ASSERT_FEQ(tzero_effective_interval(&clk), 1.05, 1e-12);
    printf("  PASS test_effective_interval\n");
    return 0;
}

int main(void) {
    printf("=== T-Zero Clock Tests ===\n");
    int fails = 0;
    fails += test_init();
    fails += test_observe();
    fails += test_check_states();
    fails += test_delta();
    fails += test_missed_ticks();
    fails += test_effective_interval();
    printf(fails == 0 ? "All tests passed.\n" : "%d test(s) FAILED.\n", fails);
    return fails;
}
