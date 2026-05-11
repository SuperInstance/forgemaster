/*
 * snapkit.h — single-header C library for Eisenstein lattice snapping,
 *            temporal beat grids, and spectral analysis.
 *
 * C99-compatible, zero dependencies, no malloc.
 *
 * USAGE (single header):
 *   #define SNAPKIT_IMPLEMENTATION
 *   #include "snapkit.h"
 *
 * USAGE (linked library):
 *   #include "snapkit.h"
 *   link with -lsnapkit
 *
 * Covering radius guaranteed ≤ 1/√3.
 */

#ifndef SNAPKIT_H
#define SNAPKIT_H

#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

#define SNAPKIT_SQRT3        1.7320508075688772
#define SNAPKIT_INV_SQRT3    0.5773502691896258
#define SNAPKIT_HALF_SQRT3   0.8660254037844386
#define SNAPKIT_COVERING_RADIUS 0.5773502691896258  /* 1/√3 */

/* ------------------------------------------------------------------ */
/* Eisenstein integer                                                  */
/* ------------------------------------------------------------------ */

typedef struct sk_eisenstein {
    int a;
    int b;
} sk_eisenstein;

/* Convert Eisenstein integer (a, b) → Cartesian (x, y) */
static inline double sk_eisenstein_x(int a, int b) {
    return (double)a - 0.5 * (double)b;
}
static inline double sk_eisenstein_y(int b) {
    return SNAPKIT_HALF_SQRT3 * (double)b;
}

/* Eisenstein norm squared: a² - ab + b² (always ≥ 0) */
static inline int sk_eisenstein_norm2(int a, int b) {
    return a * a - a * b + b * b;
}

/* ------------------------------------------------------------------ */
/* Eisenstein snap result                                              */
/* ------------------------------------------------------------------ */

typedef struct sk_snap_result {
    sk_eisenstein nearest;   /* nearest Eisenstein integer */
    double        distance;  /* Euclidean distance to nearest */
    bool          is_snap;   /* distance ≤ tolerance */
} sk_snap_result;

/* ------------------------------------------------------------------ */
/* Eisenstein API                                                      */
/* ------------------------------------------------------------------ */

/* Naive snap: round (x,y) to nearest Eisenstein integer */
sk_eisenstein sk_eisenstein_snap_naive(double x, double y);

/* Voronoi snap: exact nearest-neighbor via 3×3 local search */
sk_eisenstein sk_eisenstein_snap_voronoi(double x, double y);

/* Snap with tolerance check */
sk_snap_result sk_eisenstein_snap(double x, double y, double tolerance);

/* Batch Voronoi snap. Caller provides output array of length n. */
void sk_eisenstein_snap_batch(
    const double *x, const double *y, int n,
    sk_eisenstein *out
);

/* Batch snap with tolerance. Caller provides output array of length n. */
void sk_eisenstein_snap_batch_full(
    const double *x, const double *y, int n,
    double tolerance, sk_snap_result *out
);

/* Eisenstein lattice distance between two points */
double sk_eisenstein_distance(double x1, double y1, double x2, double y2);

/* ------------------------------------------------------------------ */
/* Temporal — Beat grid                                                */
/* ------------------------------------------------------------------ */

typedef struct sk_temporal_result {
    double original_time;
    double snapped_time;
    double offset;
    bool   is_on_beat;
    bool   is_t_minus_0;
    int    beat_index;
    double beat_phase;
} sk_temporal_result;

typedef struct sk_beat_grid {
    double period;
    double phase;
    double t_start;
    double inv_period;
} sk_beat_grid;

/* Initialize a beat grid. Returns 0 on success, -1 if period ≤ 0. */
int sk_beat_grid_init(sk_beat_grid *g, double period, double phase, double t_start);

/* Find nearest beat: returns beat time and sets *beat_index */
double sk_beat_grid_nearest(const sk_beat_grid *g, double t, int *beat_index);

/* Snap a timestamp to the grid */
sk_temporal_result sk_beat_grid_snap(const sk_beat_grid *g, double t, double tolerance);

/* Batch snap. Caller provides output array of length n. */
void sk_beat_grid_snap_batch(
    const sk_beat_grid *g,
    const double *timestamps, int n,
    double tolerance, sk_temporal_result *out
);

/* Enumerate beats in [t_start, t_end]. Caller provides buffer of max_out.
   Returns number of beats written. */
int sk_beat_grid_range(
    const sk_beat_grid *g,
    double t_start, double t_end,
    double *out, int max_out
);

/* ------------------------------------------------------------------ */
/* Temporal — T-minus-0 detector                                       */
/* ------------------------------------------------------------------ */

#define SK_T0_MAX_HISTORY 64

typedef struct sk_temporal_snap {
    sk_beat_grid grid;
    double       tolerance;
    double       t0_threshold;
    int          t0_window;
    /* circular buffer */
    double       hist_t[SK_T0_MAX_HISTORY];
    double       hist_v[SK_T0_MAX_HISTORY];
    int          hist_idx;
    int          hist_len;
    int          hist_cap;
} sk_temporal_snap;

/* Initialize temporal snap with T-minus-0 detection */
int sk_temporal_snap_init(
    sk_temporal_snap *ts,
    const sk_beat_grid *grid,
    double tolerance,
    double t0_threshold,
    int t0_window
);

/* Observe a (time, value) pair, returns snap result with t0 detection */
sk_temporal_result sk_temporal_observe(sk_temporal_snap *ts, double t, double value);

/* Reset T0 detection history */
void sk_temporal_reset(sk_temporal_snap *ts);

/* ------------------------------------------------------------------ */
/* Spectral — entropy, Hurst, autocorrelation                          */
/* ------------------------------------------------------------------ */

/* Shannon entropy via histogram binning. Caller provides counts buffer of length bins. */
double sk_entropy(const double *data, int n, int bins);

/* Shannon entropy with caller-provided scratch buffer (counts, length=bins) */
double sk_entropy_with_buf(const double *data, int n, int bins, int *counts);

/* Normalized autocorrelation. Caller provides output buffer of length max_lag+1.
   Returns actual number of lags written. */
int sk_autocorrelation(
    const double *data, int n,
    int max_lag,
    double *out
);

/* Hurst exponent via R/S analysis */
double sk_hurst_exponent(const double *data, int n);

typedef struct sk_spectral_summary {
    double entropy_bits;
    double hurst;
    double autocorr_lag1;
    double autocorr_decay;
    bool   is_stationary;
} sk_spectral_summary;

/* Full spectral summary. Caller provides acf_buf of length max_lag+1 and
   counts_buf of length bins. If max_lag ≤ 0, defaults to n/2. */
sk_spectral_summary sk_spectral_analyze(
    const double *data, int n,
    int bins, int max_lag,
    double *acf_buf, int *counts_buf
);

/* Batch spectral analysis. Caller provides output array of length n_series,
   plus per-series buffers. acf_buf/count_buf are reused across series. */
void sk_spectral_batch(
    const double **series, const int *lengths, int n_series,
    int bins, int max_lag,
    sk_spectral_summary *out,
    double *acf_buf, int acf_buf_len,
    int *counts_buf
);

#ifdef __cplusplus
}
#endif

/* ------------------------------------------------------------------ */
/* Implementation                                                      */
/* ------------------------------------------------------------------ */

#ifdef SNAPKIT_IMPLEMENTATION

#include <stdlib.h>
#include <string.h>

/* ================================================================== */
/* eisenstein.c                                                        */
/* ================================================================== */

sk_eisenstein sk_eisenstein_snap_naive(double x, double y) {
    double b_float = 2.0 * y / SNAPKIT_SQRT3;
    double a_float = x + b_float * 0.5;

    int a_floor = (int)floor(a_float);
    int b_floor = (int)floor(b_float);

    sk_eisenstein best = {a_floor, b_floor};
    double best_dist = 1e30;

    for (int da = 0; da <= 1; da++) {
        for (int db = 0; db <= 1; db++) {
            int a = a_floor + da;
            int b = b_floor + db;
            double cx = sk_eisenstein_x(a, b);
            double cy = sk_eisenstein_y(b);
            double dx = x - cx;
            double dy = y - cy;
            double dist = dx * dx + dy * dy;
            if (dist < best_dist - 1e-18) {
                best_dist = dist;
                best.a = a;
                best.b = b;
            } else if (fabs(dist - best_dist) < 1e-18) {
                /* tiebreak: prefer smaller |a|,|b| */
                if (abs(a) + abs(b) < abs(best.a) + abs(best.b)) {
                    best.a = a;
                    best.b = b;
                }
            }
        }
    }
    return best;
}

sk_eisenstein sk_eisenstein_snap_voronoi(double x, double y) {
    double b0 = round(2.0 * y * SNAPKIT_INV_SQRT3);
    double a0 = round(x + b0 * 0.5);

    int ia0 = (int)a0;
    int ib0 = (int)b0;

    double best_dist = 1e30;
    int best_a = ia0, best_b = ib0;

    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            int a = ia0 + da;
            int b = ib0 + db;
            double dx = x - sk_eisenstein_x(a, b);
            double dy = y - sk_eisenstein_y(b);
            double d2 = dx * dx + dy * dy;
            if (d2 < best_dist - 1e-24) {
                best_dist = d2;
                best_a = a;
                best_b = b;
            } else if (fabs(d2 - best_dist) < 1e-24) {
                if (abs(a) + abs(b) < abs(best_a) + abs(best_b)) {
                    best_a = a;
                    best_b = b;
                }
            }
        }
    }

    sk_eisenstein r = {best_a, best_b};
    return r;
}

sk_snap_result sk_eisenstein_snap(double x, double y, double tolerance) {
    sk_eisenstein nearest = sk_eisenstein_snap_voronoi(x, y);
    double cx = sk_eisenstein_x(nearest.a, nearest.b);
    double cy = sk_eisenstein_y(nearest.b);
    double dx = x - cx;
    double dy = y - cy;
    double dist = sqrt(dx * dx + dy * dy);

    sk_snap_result r;
    r.nearest = nearest;
    r.distance = dist;
    r.is_snap = (dist <= tolerance);
    return r;
}

void sk_eisenstein_snap_batch(
    const double *x, const double *y, int n,
    sk_eisenstein *out
) {
    for (int i = 0; i < n; i++) {
        out[i] = sk_eisenstein_snap_voronoi(x[i], y[i]);
    }
}

void sk_eisenstein_snap_batch_full(
    const double *x, const double *y, int n,
    double tolerance, sk_snap_result *out
) {
    for (int i = 0; i < n; i++) {
        out[i] = sk_eisenstein_snap(x[i], y[i], tolerance);
    }
}

double sk_eisenstein_distance(double x1, double y1, double x2, double y2) {
    double dx = x1 - x2;
    double dy = y1 - y2;
    sk_eisenstein n = sk_eisenstein_snap_voronoi(dx, dy);
    double cx = sk_eisenstein_x(n.a, n.b);
    double cy = sk_eisenstein_y(n.b);
    double rx = dx - cx;
    double ry = dy - cy;
    double residual = sqrt(rx * rx + ry * ry);
    return sqrt((double)sk_eisenstein_norm2(n.a, n.b)) + residual;
}

/* ================================================================== */
/* temporal.c                                                          */
/* ================================================================== */

int sk_beat_grid_init(sk_beat_grid *g, double period, double phase, double t_start) {
    if (period <= 0.0) return -1;
    g->period = period;
    g->phase = phase;
    g->t_start = t_start;
    g->inv_period = 1.0 / period;
    return 0;
}

double sk_beat_grid_nearest(const sk_beat_grid *g, double t, int *beat_index) {
    double adjusted = t - g->t_start - g->phase;
    int idx = (int)round(adjusted * g->inv_period);
    if (beat_index) *beat_index = idx;
    return g->t_start + g->phase + idx * g->period;
}

sk_temporal_result sk_beat_grid_snap(const sk_beat_grid *g, double t, double tolerance) {
    int bi;
    double bt = sk_beat_grid_nearest(g, t, &bi);
    double offset = t - bt;
    double phase = fmod(t - g->t_start - g->phase, g->period) * g->inv_period;
    if (phase < 0.0) phase += 1.0;

    sk_temporal_result r;
    r.original_time = t;
    r.snapped_time  = bt;
    r.offset        = offset;
    r.is_on_beat    = (fabs(offset) <= tolerance);
    r.is_t_minus_0  = false;
    r.beat_index    = bi;
    r.beat_phase    = phase;
    return r;
}

void sk_beat_grid_snap_batch(
    const sk_beat_grid *g,
    const double *timestamps, int n,
    double tolerance, sk_temporal_result *out
) {
    for (int i = 0; i < n; i++) {
        out[i] = sk_beat_grid_snap(g, timestamps[i], tolerance);
    }
}

int sk_beat_grid_range(
    const sk_beat_grid *g,
    double t0, double t1,
    double *out, int max_out
) {
    if (t1 <= t0) return 0;
    int first = (int)ceil((t0 - g->t_start - g->phase) * g->inv_period);
    int last  = (int)floor((t1 - g->t_start - g->phase) * g->inv_period);
    int count = 0;
    for (int i = first; i <= last && count < max_out; i++) {
        out[count++] = g->t_start + g->phase + i * g->period;
    }
    return count;
}

int sk_temporal_snap_init(
    sk_temporal_snap *ts,
    const sk_beat_grid *grid,
    double tolerance,
    double t0_threshold,
    int t0_window
) {
    ts->grid = *grid;
    ts->tolerance = tolerance;
    ts->t0_threshold = t0_threshold;
    ts->t0_window = t0_window < 2 ? 2 : t0_window;
    ts->hist_cap = ts->t0_window * 2;
    if (ts->hist_cap > SK_T0_MAX_HISTORY) ts->hist_cap = SK_T0_MAX_HISTORY;
    ts->hist_idx = 0;
    ts->hist_len = 0;
    return 0;
}

static bool sk_detect_t0(const sk_temporal_snap *ts) {
    if (ts->hist_len < 3) return false;
    int cap = ts->hist_cap;
    int idx = ts->hist_idx;

    double curr_t = ts->hist_t[(idx - 1 + cap) % cap];
    double curr_v = ts->hist_v[(idx - 1 + cap) % cap];
    double mid_t  = ts->hist_t[(idx - 2 + cap) % cap];
    double mid_v  = ts->hist_v[(idx - 2 + cap) % cap];
    double prev_t = ts->hist_t[(idx - 3 + cap) % cap];
    double prev_v = ts->hist_v[(idx - 3 + cap) % cap];

    if (fabs(curr_v) > ts->t0_threshold) return false;

    double dt1 = mid_t - prev_t;
    double dt2 = curr_t - mid_t;
    if (dt1 == 0.0 || dt2 == 0.0) return false;

    double d1 = (mid_v - prev_v) / dt1;
    double d2 = (curr_v - mid_v) / dt2;

    return d1 * d2 < 0.0;
}

sk_temporal_result sk_temporal_observe(sk_temporal_snap *ts, double t, double value) {
    ts->hist_t[ts->hist_idx] = t;
    ts->hist_v[ts->hist_idx] = value;
    ts->hist_idx = (ts->hist_idx + 1) % ts->hist_cap;
    if (ts->hist_len < ts->hist_cap) ts->hist_len++;

    bool is_t0 = sk_detect_t0(ts);
    sk_temporal_result r = sk_beat_grid_snap(&ts->grid, t, ts->tolerance);
    r.is_t_minus_0 = is_t0;
    return r;
}

void sk_temporal_reset(sk_temporal_snap *ts) {
    ts->hist_idx = 0;
    ts->hist_len = 0;
}

/* ================================================================== */
/* spectral.c                                                          */
/* ================================================================== */

double sk_entropy_with_buf(const double *data, int n, int bins, int *counts) {
    if (n < 2 || bins < 1) return 0.0;

    double min_val = data[0], max_val = data[0];
    for (int i = 1; i < n; i++) {
        if (data[i] < min_val) min_val = data[i];
        else if (data[i] > max_val) max_val = data[i];
    }
    if (max_val == min_val) return 0.0;

    double inv_range = (double)bins / (max_val - min_val);
    memset(counts, 0, (size_t)bins * sizeof(int));

    for (int i = 0; i < n; i++) {
        int idx = (int)((data[i] - min_val) * inv_range);
        if (idx >= bins) idx = bins - 1;
        counts[idx]++;
    }

    double inv_n = 1.0 / n;
    double h = 0.0;
    double inv_log2 = 1.0 / log(2.0);
    for (int i = 0; i < bins; i++) {
        if (counts[i] > 0) {
            double p = counts[i] * inv_n;
            h -= p * log(p) * inv_log2;
        }
    }
    return h;
}

double sk_entropy(const double *data, int n, int bins) {
    /* Stack allocation for reasonable bin counts; caller can use
       sk_entropy_with_buf for larger bins to avoid stack overflow. */
    if (bins > 256) bins = 256;
    int counts[256];
    return sk_entropy_with_buf(data, n, bins, counts);
}

int sk_autocorrelation(
    const double *data, int n,
    int max_lag,
    double *out
) {
    if (n < 2) { out[0] = 1.0; return 1; }
    if (max_lag <= 0) max_lag = n / 2;
    if (max_lag >= n) max_lag = n - 1;

    double inv_n = 1.0 / n;
    double mean = 0.0;
    for (int i = 0; i < n; i++) mean += data[i];
    mean *= inv_n;

    /* We need centered data — allocate on stack if small, else caller
       should pre-center. For single-header simplicity, we use a VLA or
       recompute inline. */
    double r0 = 0.0;
    for (int i = 0; i < n; i++) {
        double d = data[i] - mean;
        r0 += d * d;
    }
    r0 *= inv_n;

    if (r0 == 0.0) {
        out[0] = 1.0;
        for (int i = 1; i <= max_lag; i++) out[i] = 0.0;
        return max_lag + 1;
    }

    double inv_r0 = 1.0 / r0;
    for (int lag = 0; lag <= max_lag; lag++) {
        double rk = 0.0;
        int limit = n - lag;
        for (int t = 0; t < limit; t++) {
            double d1 = data[t] - mean;
            double d2 = data[t + lag] - mean;
            rk += d1 * d2;
        }
        out[lag] = rk * inv_n * inv_r0;
    }
    return max_lag + 1;
}

double sk_hurst_exponent(const double *data, int n) {
    if (n < 20) return 0.5;

    double inv_n = 1.0 / n;
    double mean = 0.0;
    for (int i = 0; i < n; i++) mean += data[i];
    mean *= inv_n;

    /* Build centered data on stack (VLA, C99) */
    double centered[n];
    for (int i = 0; i < n; i++) centered[i] = data[i] - mean;

    /* Geometric progression of test sizes */
    int test_sizes[32];
    int n_sizes = 0;
    int s = 16;
    while (s <= n / 2 && n_sizes < 32) {
        test_sizes[n_sizes++] = s;
        int next = s * 2;
        if (next > n / 2) next = (int)(s * 1.5);
        if (next <= s) break;
        s = next;
    }
    if (n_sizes == 0) {
        if (n >= 8) { test_sizes[0] = n / 4; n_sizes = 1; }
    }

    double log_sizes[32], log_rs[32];
    int n_pts = 0;

    for (int si = 0; si < n_sizes; si++) {
        int size = test_sizes[si];
        if (size < 4 || size > n) continue;

        int num_sub = n / size;
        if (num_sub < 1) continue;

        double inv_size = 1.0 / size;
        double rs_sum = 0.0;
        int rs_count = 0;

        for (int i = 0; i < num_sub; i++) {
            int start = i * size;
            double sub_mean = 0.0;
            for (int j = 0; j < size; j++) sub_mean += centered[start + j];
            sub_mean *= inv_size;

            double running = 0.0, cum_min = 0.0, cum_max = 0.0;
            for (int j = 0; j < size; j++) {
                running += centered[start + j] - sub_mean;
                if (running < cum_min) cum_min = running;
                else if (running > cum_max) cum_max = running;
            }
            double R = cum_max - cum_min;

            double var = 0.0;
            for (int j = 0; j < size; j++) {
                double d = centered[start + j] - sub_mean;
                var += d * d;
            }
            var *= inv_size;

            if (var > 1e-20) {
                rs_sum += R / sqrt(var);
                rs_count++;
            }
        }

        if (rs_count > 0) {
            double avg_rs = rs_sum / rs_count;
            if (avg_rs > 0.0) {
                log_sizes[n_pts] = log((double)size);
                log_rs[n_pts] = log(avg_rs);
                n_pts++;
            }
        }
    }

    if (n_pts < 2) return 0.5;

    /* Linear regression on log-log */
    double sx = 0, sy = 0, sxy = 0, sx2 = 0;
    for (int i = 0; i < n_pts; i++) {
        sx  += log_sizes[i];
        sy  += log_rs[i];
        sxy += log_sizes[i] * log_rs[i];
        sx2 += log_sizes[i] * log_sizes[i];
    }
    double denom = n_pts * sx2 - sx * sx;
    if (denom == 0.0) return 0.5;

    double h = (n_pts * sxy - sx * sy) / denom;
    if (h < 0.0) h = 0.0;
    if (h > 1.0) h = 1.0;
    return h;
}

sk_spectral_summary sk_spectral_analyze(
    const double *data, int n,
    int bins, int max_lag,
    double *acf_buf, int *counts_buf
) {
    sk_spectral_summary s;
    s.entropy_bits = sk_entropy_with_buf(data, n, bins, counts_buf);
    s.hurst = sk_hurst_exponent(data, n);

    int actual_lag = (max_lag > 0) ? max_lag : n / 2;
    int acf_len = sk_autocorrelation(data, n, actual_lag, acf_buf);

    s.autocorr_lag1 = (acf_len > 1) ? acf_buf[1] : 0.0;

    /* Find decay lag (where |acf| < 1/e) */
    double threshold = 0.36787944117144233; /* 1/e */
    s.autocorr_decay = (double)acf_len;
    for (int i = 1; i < acf_len; i++) {
        if (fabs(acf_buf[i]) < threshold) {
            s.autocorr_decay = (double)i;
            break;
        }
    }

    s.is_stationary = (s.hurst >= 0.4 && s.hurst <= 0.6) && fabs(s.autocorr_lag1) < 0.3;
    return s;
}

void sk_spectral_batch(
    const double **series, const int *lengths, int n_series,
    int bins, int max_lag,
    sk_spectral_summary *out,
    double *acf_buf, int acf_buf_len,
    int *counts_buf
) {
    for (int i = 0; i < n_series; i++) {
        int ml = (max_lag > 0) ? max_lag : lengths[i] / 2;
        if (ml >= acf_buf_len) ml = acf_buf_len - 1;
        out[i] = sk_spectral_analyze(series[i], lengths[i], bins, ml,
                                     acf_buf, counts_buf);
    }
}

#endif /* SNAPKIT_IMPLEMENTATION */

#endif /* SNAPKIT_H */
