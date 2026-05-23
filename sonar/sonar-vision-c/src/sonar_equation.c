/*
 * sonar_equation.c — Full sonar equation with detection modeling
 *
 * Signal excess:
 *   SE = SL − TL − (NL − DI) + TS − DT
 *
 * Detection probability (Rice model, simplified for large SNR):
 *   P_d ≈ 1 − Φ( DT − SE )
 * where Φ is the standard-normal CDF.
 *
 * References:
 *   Urick, R.J. (1983). "Principles of Underwater Sound." 3rd ed.,
 *   McGraw-Hill. Chapters 2, 7, 12.
 *
 *   Rice, S.O. (1944). "Mathematical analysis of random noise."
 *   Bell Syst. Tech. J. 23, 282–332.
 *
 *   Bowen, L. & G., "Signal Detection," in Underwater Acoustics
 *   and Signal Processing, NATO ASI Series, 1981.
 */

#include "sonar_vision.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ── Standard normal CDF (Abramowitz & Stegun approximation) ────── */

static double normal_cdf(double x)
{
    /* Approximation 26.2.17 from Abramowitz & Stegun (1964) */
    /* Maximum |ε| < 7.5e-8 */
    double sign = 1.0;
    if (x < 0.0) { sign = -1.0; x = -x; }

    double t = 1.0 / (1.0 + 0.2316419 * x);
    double d = 0.3989422804014327; /* 1/√(2π) */

    double poly = t * (0.319381530 +
                t * (-0.356563782 +
                t * (1.781477937 +
                t * (-1.821255978 +
                t * 1.330274429))));

    double cdf = 1.0 - d * exp(-0.5 * x * x) * poly;
    return (sign > 0) ? cdf : (1.0 - cdf);
}

/* ── Transmission loss model ─────────────────────────────────────── */

/**
 * Compute transmission loss (dB) at given range.
 * Uses spherical spreading + absorption.
 *
 * TL = 20·log₁₀(R) + α·R/1000
 *
 * where α is the Francois-Garrison absorption in dB/km.
 */
static double compute_tl(const sv_sonar_params_t *p, double range_m)
{
    if (range_m < 1.0) return 0.0;

    double alpha;
    sv_error_t err = sv_absorption(p->frequency, p->temperature,
                                   p->salinity, p->src_depth, 8.0, &alpha);
    if (err != SV_OK) alpha = 0.0;

    return 20.0 * log10(range_m) + alpha * range_m / 1000.0;
}

/* ── Public API ──────────────────────────────────────────────────── */

sv_error_t sv_sonar_equation(const sv_sonar_params_t *p, double range,
                             sv_sonar_result_t *res)
{
    if (!p || !res) return SV_ERR_NULL_PTR;
    if (range < 0.0) return SV_ERR_PARAM;

    /* Transmission loss at specified range */
    double tl = compute_tl(p, range);

    /* Signal excess */
    double se = p->source_level
              - tl
              - (p->noise_level - p->directivity_index)
              + p->target_strength
              - p->detection_threshold;

    /* Detection probability (Rice model) */
    double pd = 1.0 - normal_cdf(-se);
    if (pd < 0.0) pd = 0.0;
    if (pd > 1.0) pd = 1.0;

    /* Maximum detection range: bisection for SE = 0 */
    double max_range = 0.0;
    {
        double lo = 1.0, hi = 200000.0; /* 1 m .. 200 km */
        for (int iter = 0; iter < 60; iter++) {
            double mid = (lo + hi) * 0.5;
            double tl_mid = compute_tl(p, mid);
            double se_mid = p->source_level
                          - tl_mid
                          - (p->noise_level - p->directivity_index)
                          + p->target_strength
                          - p->detection_threshold;
            if (se_mid > 0.0) {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        max_range = (lo + hi) * 0.5;
        /* If SE is still positive at hi, max_range is beyond 200 km */
        {
            double tl_hi = compute_tl(p, hi);
            double se_hi = p->source_level - tl_hi
                         - (p->noise_level - p->directivity_index)
                         + p->target_strength - p->detection_threshold;
            if (se_hi > 0.0) max_range = hi;
        }
    }

    res->signal_excess        = se;
    res->detection_probability = pd;
    res->max_range            = max_range;
    res->transmission_loss    = tl;

    return SV_OK;
}
