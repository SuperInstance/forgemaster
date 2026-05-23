/*
 * reverberation.c — Volume, surface, and bottom reverberation models
 *
 * References:
 *   Urick, R.J. (1983). "Principles of Underwater Sound." 3rd ed.
 *   Chapters 8–9: Reverberation.
 *
 *   Lambert's law for bottom backscatter:
 *     BS = Bs · sin²θ
 *   where Bs is the Lambert parameter (typically -10 to -40 dB).
 *
 *   Volume reverberation:
 *     RL = SL − 2TL + 10·log₁₀(sv · V)
 *   where sv is volume scattering strength and V is insonified volume.
 *
 *   Surface reverberation:
 *     RL = SL − 2TL + SS + 10·log₁₀(A)
 *   Chapman-Harris (1962) surface scattering model.
 */

#include "sonar_vision.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ── Helper: spherical spreading TL ──────────────────────────────── */

static double simple_tl(double range)
{
    if (range < 1.0) return 0.0;
    return 20.0 * log10(range);
}

/* ── Volume reverberation ────────────────────────────────────────── */

/**
 * Volume reverberation level.
 *
 * RL_vol = SL − 2TL + sv + 10·log₁₀( (c·τ/2) · R · θ_bw )
 *
 * where:
 *   c·τ/2 = effective pulse length in range
 *   R     = range
 *   θ_bw  = equivalent beam width (radians)
 */
static double reverb_volume(const sv_reverb_params_t *p, double range)
{
    if (range < 1.0) return -999.0;

    double c;
    sv_mackenzie(p->temperature, p->salinity, p->src_depth, &c);

    double pulse_range = c * p->pulse_length / 2.0;
    double theta_bw = pow(10.0, p->beam_pattern / 10.0); /* dB -> linear */
    /* Convert beam_pattern from dB to radians approximately */
    theta_bw = pow(10.0, p->beam_pattern / 10.0);

    double vol = pulse_range * range * theta_bw;
    double vol_dB = 10.0 * log10(vol + 1e-30);

    double tl = simple_tl(range);

    /* SL − 2TL + sv + 10·log₁₀(V) */
    /* Assume SL = 220 dB (typical) — caller should factor SL separately */
    /* We return RL relative to source: -2TL + sv + 10·log₁₀(V) */
    return -2.0 * tl + p->volume_scatter + vol_dB;
}

/* ── Surface reverberation ───────────────────────────────────────── */

/**
 * Surface reverberation level (Chapman-Harris model).
 *
 * RL_surf = SL − 2TL + SS + 10·log₁₀(A)
 *
 * where A = (c·τ/2) · R · θ_bw is the insonified area
 * and SS is the surface scattering strength.
 */
static double reverb_surface(const sv_reverb_params_t *p, double range)
{
    if (range < 1.0) return -999.0;

    double c;
    sv_mackenzie(p->temperature, p->salinity, p->src_depth, &c);

    double pulse_range = c * p->pulse_length / 2.0;
    double theta_bw = pow(10.0, p->beam_pattern / 10.0);
    double area = pulse_range * range * theta_bw;
    double area_dB = 10.0 * log10(area + 1e-30);

    double tl = simple_tl(range);

    return -2.0 * tl + p->surface_strength + area_dB;
}

/* ── Bottom reverberation (Lambert's law) ────────────────────────── */

/**
 * Bottom reverberation level using Lambert's law.
 *
 * Lambert's law:
 *   BS(θ) = Bs · sin²θ
 *
 * RL_bottom = SL − 2TL + Bs + 10·log₁₀( A · sin²θ )
 *
 * where A is the insonified area on the seafloor.
 */
static double reverb_bottom(const sv_reverb_params_t *p, double range,
                            const sv_ssp_t *ssp)
{
    if (range < 1.0) return -999.0;

    double c;
    sv_mackenzie(p->temperature, p->salinity, p->src_depth, &c);

    /* Estimate grazing angle from geometry */
    double bottom_depth = (ssp && ssp->n >= 2) ? ssp->points[ssp->n - 1].depth : 1000.0;
    double theta_grazing;
    if (range > bottom_depth) {
        theta_grazing = atan2(bottom_depth - p->src_depth, range);
    } else {
        theta_grazing = M_PI / 4.0; /* 45° default */
    }
    if (theta_grazing < 0.01) theta_grazing = 0.01;

    double pulse_range = c * p->pulse_length / 2.0;
    double theta_bw = pow(10.0, p->beam_pattern / 10.0);
    double area = pulse_range * range * theta_bw;

    /* Lambert's law: Bs · sin²θ */
    double sin2_theta = sin(theta_grazing) * sin(theta_grazing);
    double sin2_dB = 10.0 * log10(sin2_theta + 1e-30);
    double area_dB = 10.0 * log10(area + 1e-30);

    double tl = simple_tl(range);

    return -2.0 * tl + p->bottom_strength + sin2_dB + area_dB;
}

/* ── Public API ──────────────────────────────────────────────────── */

sv_error_t sv_reverberation(sv_reverb_type_t type,
                            const sv_reverb_params_t *p,
                            double range, const sv_ssp_t *ssp,
                            double *rl)
{
    if (!p || !rl) return SV_ERR_NULL_PTR;
    if (range < 0.0) return SV_ERR_PARAM;

    switch (type) {
    case SV_REVERB_VOLUME:
        *rl = reverb_volume(p, range);
        break;
    case SV_REVERB_SURFACE:
        *rl = reverb_surface(p, range);
        break;
    case SV_REVERB_BOTTOM:
        *rl = reverb_bottom(p, range, ssp);
        break;
    default:
        return SV_ERR_PARAM;
    }

    return SV_OK;
}
