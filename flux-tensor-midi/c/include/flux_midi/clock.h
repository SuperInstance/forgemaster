#ifndef FLUX_MIDI_CLOCK_H
#define FLUX_MIDI_CLOCK_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * T-Zero Clock — adaptive interval clock with EWMA smoothing.
 *
 * Each RoomMusician maintains a T-0 clock. The clock ticks at a nominal
 * interval, but adapts to observed behavior via exponentially weighted
 * moving average (EWMA).
 *
 * States:
 *   ON_TIME  — last tick was within tolerance
 *   LATE     — missed 1-2 ticks
 *   SILENT   — missed 3-9 ticks
 *   DEAD     — no tick for 10+ intervals
 */

typedef enum {
    TZERO_ON_TIME = 0,
    TZERO_LATE    = 1,
    TZERO_SILENT  = 2,
    TZERO_DEAD    = 3
} TZeroState;

typedef struct {
    double interval;      /* Expected tick interval (seconds) */
    double t_last;        /* Time of last observation */
    double t_zero;        /* Phase reference point */
    double ewma_alpha;    /* Smoothing factor [0..1], 0=no adapt */
    double ewma_interval; /* EWMA-smoothed interval estimate */
    int    adaptive;      /* 1 = update interval via EWMA */
    int    tick_count;    /* Total ticks observed */
    int    missed_count;  /* Consecutive missed ticks */
} TZeroClock;

/* Initialize clock with nominal interval and EWMA alpha */
void tzero_init(TZeroClock* clk, double interval, double ewma_alpha, int adaptive);

/* Observe a tick at time t_now. Updates EWMA interval if adaptive. */
void tzero_observe(TZeroClock* clk, double t_now);

/* Check current state relative to t_now */
TZeroState tzero_check(const TZeroClock* clk, double t_now);

/* Compute delta from expected T-0 (negative = early, positive = late) */
double tzero_delta(const TZeroClock* clk, double t_now);

/* Compute how many ticks have been missed */
int tzero_missed_ticks(const TZeroClock* clk, double t_now);

/* Get effective interval (EWMA if adaptive, else nominal) */
double tzero_effective_interval(const TZeroClock* clk);

/* Reset clock, preserving interval settings */
void tzero_reset(TZeroClock* clk);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_CLOCK_H */
