#include "flux_midi/clock.h"
#include <math.h>

void tzero_init(TZeroClock* clk, double interval, double ewma_alpha, int adaptive) {
    clk->interval = interval;
    clk->t_last = 0.0;
    clk->t_zero = 0.0;
    clk->ewma_alpha = ewma_alpha;
    clk->ewma_interval = interval;
    clk->adaptive = adaptive;
    clk->tick_count = 0;
    clk->missed_count = 0;
}

void tzero_observe(TZeroClock* clk, double t_now) {
    if (clk->tick_count == 0) {
        /* First observation — set reference point */
        clk->t_zero = t_now;
        clk->t_last = t_now;
    } else {
        double observed_interval = t_now - clk->t_last;
        if (observed_interval > 0.0 && clk->adaptive) {
            clk->ewma_interval = clk->ewma_alpha * observed_interval +
                                 (1.0 - clk->ewma_alpha) * clk->ewma_interval;
        }
        clk->t_last = t_now;
    }
    clk->tick_count++;
    clk->missed_count = 0;
}

TZeroState tzero_check(const TZeroClock* clk, double t_now) {
    if (clk->tick_count == 0) return TZERO_DEAD;

    double elapsed = t_now - clk->t_last;
    double eff = tzero_effective_interval(clk);
    if (eff <= 0.0) return TZERO_DEAD;

    double ratio = elapsed / eff;

    if (ratio < 1.5)       return TZERO_ON_TIME;
    else if (ratio < 3.0)  return TZERO_LATE;
    else if (ratio < 10.0) return TZERO_SILENT;
    else                    return TZERO_DEAD;
}

double tzero_delta(const TZeroClock* clk, double t_now) {
    if (clk->tick_count == 0) return 0.0;
    double eff = tzero_effective_interval(clk);
    double expected = clk->t_last + eff;
    return t_now - expected;
}

int tzero_missed_ticks(const TZeroClock* clk, double t_now) {
    if (clk->tick_count == 0) return 0;
    double eff = tzero_effective_interval(clk);
    if (eff <= 0.0) return 0;
    double elapsed = t_now - clk->t_last;
    int total_missed = (int)(elapsed / eff) - 1;
    return total_missed > 0 ? total_missed : 0;
}

double tzero_effective_interval(const TZeroClock* clk) {
    return clk->adaptive ? clk->ewma_interval : clk->interval;
}

void tzero_reset(TZeroClock* clk) {
    double interval = clk->interval;
    double alpha = clk->ewma_alpha;
    int adaptive = clk->adaptive;
    tzero_init(clk, interval, alpha, adaptive);
}
