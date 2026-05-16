/**
 * @file core_snap.c
 * @brief Snap function implementation — tolerance-based compression.
 */

#include "snapkit/snapkit_internal.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

/* ===========================================================================
 * Snap Function — Implementation
 * ========================================================================= */

snapkit_snap_function_t* snapkit_snap_create(void) {
    return snapkit_snap_create_ex(SNAPKIT_DEFAULT_TOLERANCE,
                                   SNAPKIT_TOPOLOGY_HEXAGONAL,
                                   0.0,
                                   SNAPKIT_DEFAULT_ADAPTATION_RATE);
}

snapkit_snap_function_t* snapkit_snap_create_ex(double tolerance,
                                                  snapkit_topology_t topology,
                                                  double baseline,
                                                  double adaptation_rate) {
    snapkit_snap_function_t* sf = (snapkit_snap_function_t*)
        calloc(1, sizeof(snapkit_snap_function_t));
    if (!sf) return NULL;

    sf->tolerance        = tolerance;
    sf->topology         = topology;
    sf->baseline         = baseline;
    sf->adaptation_rate  = adaptation_rate;

    sf->history.results = (snapkit_snap_result_t*)
        calloc(SNAPKIT_SNAP_HISTORY_MAX, sizeof(snapkit_snap_result_t));
    if (!sf->history.results) {
        free(sf);
        return NULL;
    }

    return sf;
}

void snapkit_snap_free(snapkit_snap_function_t* sf) {
    if (!sf) return;
    free(sf->history.results);
    free(sf);
}

snapkit_error_t snapkit_snap(snapkit_snap_function_t* sf,
                              double value,
                              double expected,
                              snapkit_snap_result_t* out) {
    if (!sf || !out) return SNAPKIT_ERR_NULL;

    double exp_val = isnan(expected) ? sf->baseline : expected;
    double delta = fabs(value - exp_val);
    bool within = delta <= sf->tolerance;
    double snapped = within ? exp_val : value;

    out->original = value;
    out->snapped = snapped;
    out->delta = delta;
    out->within_tolerance = within;
    out->tolerance = sf->tolerance;
    out->topology = sf->topology;

    /* Update history (circular buffer) */
    snapkit_snap_history_t* hist = &sf->history;
    size_t idx = hist->head % SNAPKIT_SNAP_HISTORY_MAX;
    hist->results[idx] = *out;
    hist->head++;
    if (hist->count < SNAPKIT_SNAP_HISTORY_MAX) hist->count++;

    hist->sum_delta += delta;
    if (delta > hist->max_delta) hist->max_delta = delta;

    if (within) hist->snap_cnt++;
    else        hist->delta_cnt++;

    /* Adaptive baseline update */
    if (within && sf->adaptation_rate > 0.0) {
        sf->baseline += sf->adaptation_rate * (value - sf->baseline);
    }

    return SNAPKIT_OK;
}

snapkit_error_t snapkit_snap_eisenstein(snapkit_snap_function_t* sf,
                                         double real,
                                         double imag,
                                         double tolerance,
                                         snapkit_snap_result_t* out) {
    if (!out) return SNAPKIT_ERR_NULL;

    double tol = (tolerance < 0.0 && sf) ? sf->tolerance :
                 (tolerance >= 0.0)      ? tolerance :
                                           SNAPKIT_DEFAULT_TOLERANCE;

    int a, b;
    double snapped_re, snapped_im, dist;
    snapkit_nearest_eisenstein(real, imag, &a, &b, &snapped_re, &snapped_im, &dist);

    out->original = sqrt(real * real + imag * imag);
    out->snapped  = sqrt(snapped_re * snapped_re + snapped_im * snapped_im);
    out->delta    = dist;
    out->within_tolerance = dist <= tol;
    out->tolerance = tol;
    out->topology = SNAPKIT_TOPOLOGY_HEXAGONAL;

    if (sf) {
        snapkit_snap_history_t* hist = &sf->history;
        size_t idx = hist->head % SNAPKIT_SNAP_HISTORY_MAX;
        hist->results[idx] = *out;
        hist->head++;
        if (hist->count < SNAPKIT_SNAP_HISTORY_MAX) hist->count++;
        hist->sum_delta += dist;
        if (dist > hist->max_delta) hist->max_delta = dist;
        if (out->within_tolerance) hist->snap_cnt++;
        else                       hist->delta_cnt++;
    }

    return SNAPKIT_OK;
}

snapkit_error_t snapkit_snap_batch(snapkit_snap_function_t* sf,
                                    const double* values,
                                    size_t n,
                                    snapkit_snap_result_t* out) {
    if (!sf || !values || !out) return SNAPKIT_ERR_NULL;

#if SNAPKIT_HAVE_SSE
    snapkit_snap_batch_sse(sf, values, n, out);
#else
    for (size_t i = 0; i < n; i++) {
        snapkit_snap(sf, values[i], NAN, &out[i]);
    }
#endif

    return SNAPKIT_OK;
}

snapkit_error_t snapkit_snap_eisenstein_batch(snapkit_snap_function_t* sf,
                                               const double* real_vals,
                                               const double* imag_vals,
                                               size_t n,
                                               snapkit_snap_result_t* out) {
    if (!real_vals || !imag_vals || !out) return SNAPKIT_ERR_NULL;

    if (n > 0 && SNAPKIT_HAVE_NEON) {
        int* a_vals    = (int*)malloc(n * sizeof(int));
        int* b_vals    = (int*)malloc(n * sizeof(int));
        double* snap_re = (double*)malloc(n * sizeof(double));
        double* snap_im = (double*)malloc(n * sizeof(double));
        double* dists  = (double*)malloc(n * sizeof(double));

        if (!a_vals || !b_vals || !snap_re || !snap_im || !dists) {
            free(a_vals); free(b_vals); free(snap_re); free(snap_im); free(dists);
            return SNAPKIT_ERR_NULL;
        }

        snapkit_nearest_eisenstein_neon(real_vals, imag_vals,
                                         a_vals, b_vals,
                                         snap_re, snap_im,
                                         dists, n);

        double tol = sf ? sf->tolerance : SNAPKIT_DEFAULT_TOLERANCE;
        for (size_t i = 0; i < n; i++) {
            out[i].original = sqrt(real_vals[i] * real_vals[i] + imag_vals[i] * imag_vals[i]);
            out[i].snapped  = sqrt(snap_re[i] * snap_re[i] + snap_im[i] * snap_im[i]);
            out[i].delta    = dists[i];
            out[i].within_tolerance = dists[i] <= tol;
            out[i].tolerance = tol;
            out[i].topology = SNAPKIT_TOPOLOGY_HEXAGONAL;
        }

        free(a_vals); free(b_vals); free(snap_re); free(snap_im); free(dists);
    } else {
        for (size_t i = 0; i < n; i++) {
            snapkit_snap_eisenstein(sf, real_vals[i], imag_vals[i], -1.0, &out[i]);
        }
    }

    return SNAPKIT_OK;
}

void snapkit_snap_reset(snapkit_snap_function_t* sf, double baseline) {
    if (!sf) return;
    if (!isnan(baseline)) sf->baseline = baseline;
    sf->history.head = 0;
    sf->history.count = 0;
    sf->history.sum_delta = 0.0;
    sf->history.max_delta = 0.0;
    sf->history.snap_cnt = 0;
    sf->history.delta_cnt = 0;
}

snapkit_error_t snapkit_snap_calibrate(snapkit_snap_function_t* sf,
                                        const double* values,
                                        size_t n,
                                        double target_rate) {
    if (!sf || !values) return SNAPKIT_ERR_NULL;
    if (n == 0 || target_rate <= 0.0) return SNAPKIT_OK;

    /* Set baseline to mean */
    double sum = 0.0;
    for (size_t i = 0; i < n; i++) sum += values[i];
    sf->baseline = sum / (double)n;

    /* Compute distances from baseline */
    double* distances = (double*)malloc(n * sizeof(double));
    if (!distances) return SNAPKIT_ERR_NULL;

    for (size_t i = 0; i < n; i++) {
        distances[i] = fabs(values[i] - sf->baseline);
    }

    /* Sort distances (insertion sort — n is typically small) */
    for (size_t i = 1; i < n; i++) {
        double key = distances[i];
        size_t j = i;
        while (j > 0 && distances[j-1] > key) {
            distances[j] = distances[j-1];
            j--;
        }
        distances[j] = key;
    }

    /* Set tolerance at target_rate percentile */
    size_t idx = (size_t)(n * target_rate);
    if (idx >= n) idx = n - 1;
    sf->tolerance = distances[idx];

    free(distances);
    return SNAPKIT_OK;
}

void snapkit_snap_statistics(const snapkit_snap_function_t* sf,
                              size_t* snap_count,
                              size_t* delta_count,
                              double* mean_delta,
                              double* max_delta,
                              double* snap_rate) {
    if (!sf) return;
    if (snap_count)  *snap_count  = sf->history.snap_cnt;
    if (delta_count) *delta_count = sf->history.delta_cnt;
    if (mean_delta) {
        size_t total = sf->history.snap_cnt + sf->history.delta_cnt;
        *mean_delta = total > 0 ? sf->history.sum_delta / (double)total : 0.0;
    }
    if (max_delta)   *max_delta   = sf->history.max_delta;
    if (snap_rate) {
        size_t total = sf->history.snap_cnt + sf->history.delta_cnt;
        *snap_rate = total > 0 ? (double)sf->history.snap_cnt / (double)total : 0.0;
    }
}

#if SNAPKIT_HAVE_SSE
void snapkit_snap_batch_sse(snapkit_snap_function_t* sf,
                             const double* values, size_t n,
                             snapkit_snap_result_t* out) {
    __m128d tol_v = _mm_set1_pd(sf->tolerance);
    __m128d base_v = _mm_set1_pd(sf->baseline);

    size_t i = 0;
    for (; i + 1 < n; i += 2) {
        __m128d val = _mm_loadu_pd(&values[i]);
        __m128d delta = _mm_sub_pd(val, base_v);
        __m128d abs_delta = _mm_andnot_pd(
            _mm_set1_pd(-0.0), delta); /* fabs via sign bit mask */
        __m128d cmp = _mm_cmple_pd(abs_delta, tol_v);

        __m128d snapped = _mm_blendv_pd(val, base_v, cmp);

        double deltas_arr[2], snappeds_arr[2];
        _mm_storeu_pd(deltas_arr, abs_delta);
        _mm_storeu_pd(snappeds_arr, snapped);
        int mask = _mm_movemask_pd(cmp);

        for (int j = 0; j < 2 && (i + j) < n; j++) {
            size_t idx = i + j;
            bool within = (mask >> j) & 1;
            out[idx].original = values[idx];
            out[idx].snapped = snappeds_arr[j];
            out[idx].delta = deltas_arr[j];
            out[idx].within_tolerance = within;
            out[idx].tolerance = sf->tolerance;
            out[idx].topology = sf->topology;
        }
    }

    for (; i < n; i++) {
        snapkit_snap(sf, values[i], NAN, &out[i]);
    }
}
#endif /* SNAPKIT_HAVE_SSE */
