/*
 * mackenzie.c — Mackenzie 1981 sound speed equation
 *
 * Reference:
 *   Mackenzie, K.V. (1981). "Nine-term equation for sound speed in the
 *   oceans." J. Acoust. Soc. Am. 70(3), 807–812. Eq. (1).
 *
 * c = 1448.96 + 4.591T - 5.304e-2 T² + 2.374e-4 T³
 *     + 1.340 (S - 35) + 1.630e-2 D + 1.675e-7 D²
 *     - 1.025e-2 T (S - 35) - 7.139e-13 T D³
 *
 * Valid ranges: T = -2..30 °C, S = 30..40 PSU, D = 0..12000 m
 * Claimed accuracy: ±0.07 m/s over valid ranges.
 */

#include "sonar_vision.h"
#include <math.h>

/* ── Validation helpers ──────────────────────────────────────────── */

static int valid_temp(double T)    { return T >= -2.0  && T <= 30.0;   }
static int valid_sal(double S)     { return S >= 30.0  && S <= 40.0;   }
static int valid_depth(double D)   { return D >= 0.0   && D <= 12000.0; }

/* ── Core computation (no validation — used internally) ──────────── */

static inline double mackenzie_raw(double T, double S, double D)
{
    double T2  = T * T;
    double T3  = T2 * T;
    double D2  = D * D;
    double D3  = D2 * D;
    double S35 = S - 35.0;

    return 1448.96
         + 4.591 * T
         - 5.304e-2 * T2
         + 2.374e-4 * T3
         + 1.340 * S35
         + 1.630e-2 * D
         + 1.675e-7 * D2
         - 1.025e-2 * T * S35
         - 7.139e-13 * T * D3;
}

/* ── Public API ──────────────────────────────────────────────────── */

sv_error_t sv_mackenzie(double temp, double salinity, double depth, double *speed)
{
    if (!speed)              return SV_ERR_NULL_PTR;
    if (!valid_temp(temp))   return SV_ERR_TEMP_RANGE;
    if (!valid_sal(salinity))return SV_ERR_SAL_RANGE;
    if (!valid_depth(depth)) return SV_ERR_DEPTH_RANGE;

    *speed = mackenzie_raw(temp, salinity, depth);
    return SV_OK;
}

sv_error_t sv_mackenzie_batch(const double *temps, const double *sals,
                              const double *depths, double *out, int n)
{
    if (!temps || !sals || !depths || !out) return SV_ERR_NULL_PTR;
    if (n <= 0)                            return SV_ERR_SIZE_ZERO;

    for (int i = 0; i < n; i++) {
        if (!valid_temp(temps[i]))   return SV_ERR_TEMP_RANGE;
        if (!valid_sal(sals[i]))     return SV_ERR_SAL_RANGE;
        if (!valid_depth(depths[i])) return SV_ERR_DEPTH_RANGE;
    }

    for (int i = 0; i < n; i++) {
        out[i] = mackenzie_raw(temps[i], sals[i], depths[i]);
    }

    return SV_OK;
}
