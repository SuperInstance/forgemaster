/*
 * ray_trace.c — Acoustic ray tracing via Snell's law
 *
 * Traces rays through a layered medium with constant-gradient sound speed
 * interpolation within each layer. Supports surface and bottom reflections.
 *
 * Reference:
 *   Jensen, F.B., Kuperman, W.A., Porter, M.B., Schmidt, H. (2011).
 *   "Computational Ocean Acoustics." Springer, 2nd ed.
 *   Chapter 2: Propagation of Sound in the Ocean.
 */

#include "sonar_vision.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define EPS 1e-12

/* ── Interpolate sound speed and gradient in a layer ─────────────── */

/**
 * Linear interpolation of sound speed in a layer.
 * Returns gradient (dc/dz) in [0] and speed at depth z in [1].
 */
static void layer_interp(const sv_ssp_t *ssp, double z,
                         double *c_at_z, double *dc_dz)
{
    int n = ssp->n;
    if (n < 2) {
        *c_at_z = ssp->points[0].speed;
        *dc_dz  = 0.0;
        return;
    }

    /* Clamp to profile bounds */
    if (z <= ssp->points[0].depth) {
        *c_at_z = ssp->points[0].speed;
        *dc_dz  = (ssp->points[1].speed - ssp->points[0].speed) /
                  (ssp->points[1].depth - ssp->points[0].depth + EPS);
        return;
    }
    if (z >= ssp->points[n - 1].depth) {
        *c_at_z = ssp->points[n - 1].speed;
        *dc_dz  = (ssp->points[n - 1].speed - ssp->points[n - 2].speed) /
                  (ssp->points[n - 1].depth - ssp->points[n - 2].depth + EPS);
        return;
    }

    /* Binary search for the right layer */
    int lo = 0, hi = n - 2;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (ssp->points[mid + 1].depth < z)
            lo = mid + 1;
        else
            hi = mid;
    }

    double z0 = ssp->points[lo].depth;
    double z1 = ssp->points[lo + 1].depth;
    double c0 = ssp->points[lo].speed;
    double c1 = ssp->points[lo + 1].speed;

    double t   = (z - z0) / (z1 - z0 + EPS);
    *c_at_z    = c0 + t * (c1 - c0);
    *dc_dz     = (c1 - c0) / (z1 - z0 + EPS);
}

/* ── Trace through a constant-gradient layer ─────────────────────── */

/**
 * Trace a ray through one layer with constant sound-speed gradient.
 *
 * In a layer where c(z) = c₀ + g·(z - z₀):
 *   Ray path is an arc of a circle with radius R = c₀ / (g · cos θ₀)
 *   Horizontal range increment: Δr = R · (sin θ₂ - sin θ₁)
 *   Travel time: Δt = (1/g) · ln(c₂/c₁) / cos θ₀  (if g ≠ 0)
 *
 * Returns: range increment, time increment, depth at exit.
 */


/* ── Public API ──────────────────────────────────────────────────── */

sv_error_t sv_ray_trace(const sv_ssp_t *ssp, double src_depth,
                        double angle, double max_range,
                        sv_ray_mode_t mode, int max_bounces,
                        sv_ray_result_t *res)
{
    if (!ssp || !res)                  return SV_ERR_NULL_PTR;
    if (ssp->n < 2)                    return SV_ERR_SSP_SHORT;
    if (max_range <= 0.0)              return SV_ERR_PARAM;

    (void)mode;
    memset(res, 0, sizeof(*res));

    double max_depth = ssp->points[ssp->n - 1].depth;
    int unlimited = (max_bounces <= 0);
    int total_bounces = 0;
    int max_iter = 100000;  /* safety limit */

    double z = src_depth;
    double c, dc;
    layer_interp(ssp, z, &c, &dc);

    /* angle is from horizontal, positive downward */
    double theta = angle;
    double total_range = 0.0;
    double total_time  = 0.0;
    double path_length = 0.0;

    /* Step-based tracing */
    double dr_step = 10.0;  /* 10 m range step */

    while (total_range < max_range && max_iter-- > 0) {
        if (!unlimited && total_bounces >= max_bounces) break;

        /* Current sound speed and gradient */
        layer_interp(ssp, z, &c, &dc);

        double cos_theta = cos(theta);
        double sin_theta = sin(theta);

        /* Vertical increment for this range step */
        double dz;
        if (fabs(sin_theta) < EPS) {
            dz = 0.0;
        } else {
            /* dz = dr · tan(θ) = dr · cos(θ)/sin(θ) ... wait, θ from horizontal */
            /* θ from horizontal: horizontal = dr, vertical = dr · tan(θ) */
            dz = dr_step * tan(theta);
        }

        double z_new = z + dz;

        /* Check surface reflection */
        if (z_new < 0.0) {
            z_new = -z_new;  /* reflect */
            theta = -theta;
            res->surface_bounces++;
            total_bounces++;
        }

        /* Check bottom reflection */
        if (z_new > max_depth) {
            z_new = 2.0 * max_depth - z_new;
            theta = -theta;
            res->bottom_bounces++;
            total_bounces++;
        }

        /* Clamp just in case */
        if (z_new < 0.0) z_new = 0.0;
        if (z_new > max_depth) z_new = max_depth;

        /* Travel distance */
        double ds = sqrt(dr_step * dr_step + dz * dz);
        double c_mid;
        double dc_mid;
        layer_interp(ssp, (z + z_new) * 0.5, &c_mid, &dc_mid);

        total_time  += ds / (c_mid + EPS);
        path_length += ds;
        total_range += dr_step;

        /* Snell's law: update angle for new sound speed */
        double c_new, dc_unused;
        layer_interp(ssp, z_new, &c_new, &dc_unused);
        /* cos(θ_new)/c_new = cos(θ)/c */
        double cos_new = cos_theta * c_new / (c + EPS);
        if (cos_new > 1.0) cos_new = 1.0;
        if (cos_new < -1.0) cos_new = -1.0;
        theta = acos(cos_new);
        /* Preserve vertical direction sign */
        if (dz < 0) theta = -theta;

        z = z_new;
    }

    /* Transmission loss: cylindrical spreading + absorption */
    /* TL = 15·log₁₀(R) + α·R/1000  (approx for mixed spreading) */
    /* For now use spherical: TL = 20·log₁₀(R) + α·R/1000 */
    /* We compute a simplified TL without absorption (absorption needs frequency) */
    if (total_range > 1.0) {
        res->transmission_loss = 20.0 * log10(total_range);
    } else {
        res->transmission_loss = 0.0;
    }

    res->travel_time  = total_time;
    res->path_length  = path_length;

    return SV_OK;
}
