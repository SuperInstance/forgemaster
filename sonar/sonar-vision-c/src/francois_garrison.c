/*
 * francois_garrison.c — Francois-Garrison 1982 absorption model
 *
 * References:
 *   Francois, R.E. & Garrison, G.R. (1982). "Sound absorption based
 *   on ocean measurements: Part I: Pure water and magnesium sulfate
 *   contributions." J. Acoust. Soc. Am. 72(6), 1879–1890.
 *
 *   Francois, R.E. & Garrison, G.R. (1982). "Sound absorption based
 *   on ocean measurements: Part II: Boric acid contribution and
 *   equation for total absorption." J. Acoust. Soc. Am. 72(6),
 *   1890–1891 (Erratum: JASA 73(3), 1983, p. 938).
 *
 * Three-relaxation model:
 *   α = (A₁·P₁·f₁·f²)/(f²+f₁²) + (A₂·P₂·f₂·f²)/(f²+f₂²) + A₃·P₃·f²
 *
 * Relaxation frequencies:
 *   f₁ = 0.78√S · 10^(T/26) kHz        (boric acid)
 *   f₂ = 42·10^(T/17) kHz              (magnesium sulfate)
 *
 * Valid ranges: f = 0.4..1000 kHz, T = -2..30 °C, S = 30..40 PSU,
 *               D = 0..12000 m, pH = 7..9
 */

#include "sonar_vision.h"
#include <math.h>

static int valid_freq(double f)  { return f >= 0.4  && f <= 1000.0; }
static int valid_temp(double T)  { return T >= -2.0  && T <= 30.0;  }
static int valid_sal(double S)   { return S >= 30.0  && S <= 40.0;  }
static int valid_depth(double D) { return D >= 0.0   && D <= 12000.0; }
static int valid_ph(double pH)   { return pH >= 7.0  && pH <= 9.0;  }

/**
 * Core Francois-Garrison absorption (dB/km).
 *
 * All three terms computed per the 1982 paper with 1983 erratum corrections.
 */
static inline double fg_absorption(double f, double T, double S,
                                   double D, double pH)
{
    double f2 = f * f;

    /* ── Boric acid relaxation (relaxation 1) ─────────────────── */
    /* f₁ in kHz — FG82 Part II Eq.(12) */
    double f1 = 0.78 * sqrt(S / 35.0) * pow(10.0, T / 26.0);

    /* A₁: pH-dependent — FG82 Part II Eq.(9) */
    double pH_term = pow(10.0, pH - 8.0);
    double A1 = 0.106 * (pH_term / (1.0 + pH_term));

    /* P₁ = 1.0 (no depth correction for boric acid) */

    /* ── Magnesium sulfate relaxation (relaxation 2) ─────────── */
    /* f₂ in kHz — FG82 Part I Eq.(13) */
    double f2relax = 42.0 * pow(10.0, T / 17.0);

    /* A₂ — FG82 Part I Eq.(10) */
    double A2 = 0.52 * (1.0 + T / 43.0) * (S / 35.0);

    /* Pressure correction P₂ — FG82 Part I Eq.(11) */
    double P2 = 1.0 - 2.36e-2 * D + 5.22e-7 * D * D;

    /* ── Pure water absorption (relaxation 3) ─────────────────── */
    /* A₃ — FG82 Part I Eq.(14-15) */
    double A3;
    if (T < 20.0) {
        A3 = 4.937e-4 - 2.59e-5 * T + 9.11e-7 * T * T - 1.50e-8 * T * T * T;
    } else {
        A3 = 3.964e-4 - 1.146e-5 * T + 1.45e-7 * T * T - 6.5e-10 * T * T * T;
    }

    /* Pressure correction P₃ — FG82 Part I Eq.(16) */
    double P3 = 1.0 - 3.83e-5 * D + 4.90e-10 * D * D;

    /* ── Total absorption α (dB/km) — FG82 Part II Eq.(8) ─── */
    double f1sq = f1 * f1;
    double f2sq = f2relax * f2relax;
    double alpha = A1 * f1 * f2 / (f1sq + f2)
                 + A2 * P2 * f2relax * f2 / (f2sq + f2)
                 + A3 * P3 * f2;

    return alpha;
}

/* ── Public API ──────────────────────────────────────────────────── */

sv_error_t sv_absorption(double freq, double temp, double salinity,
                         double depth, double ph, double *alpha)
{
    if (!alpha)                return SV_ERR_NULL_PTR;
    if (!valid_freq(freq))     return SV_ERR_FREQ_RANGE;
    if (!valid_temp(temp))     return SV_ERR_TEMP_RANGE;
    if (!valid_sal(salinity))  return SV_ERR_SAL_RANGE;
    if (!valid_depth(depth))   return SV_ERR_DEPTH_RANGE;
    if (!valid_ph(ph))         return SV_ERR_PH_RANGE;

    *alpha = fg_absorption(freq, temp, salinity, depth, ph);
    return SV_OK;
}

sv_error_t sv_absorption_batch(const double *freqs, const double *temps,
                               const double *sals, const double *depths,
                               const double *phs, double *out, int n)
{
    if (!freqs || !temps || !sals || !depths || !phs || !out)
        return SV_ERR_NULL_PTR;
    if (n <= 0) return SV_ERR_SIZE_ZERO;

    for (int i = 0; i < n; i++) {
        if (!valid_freq(freqs[i]))    return SV_ERR_FREQ_RANGE;
        if (!valid_temp(temps[i]))    return SV_ERR_TEMP_RANGE;
        if (!valid_sal(sals[i]))      return SV_ERR_SAL_RANGE;
        if (!valid_depth(depths[i]))  return SV_ERR_DEPTH_RANGE;
        if (!valid_ph(phs[i]))        return SV_ERR_PH_RANGE;
    }

    for (int i = 0; i < n; i++) {
        out[i] = fg_absorption(freqs[i], temps[i], sals[i],
                               depths[i], phs[i]);
    }

    return SV_OK;
}
