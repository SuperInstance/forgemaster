#define _GNU_SOURCE
#include "eisenstein_bridge.h"
#include <math.h>
#include <string.h>

/* ── Eisenstein A₂ lattice constants ── */

/* ω = e^{2πi/3} = (-1/2, √3/2) */
static const double EISENSTEIN_OMEGA_RE = -0.5;
static const double EISENSTEIN_OMEGA_IM = 0.8660254037844386; /* sqrt(3)/2 */

/* Inverse basis: to go from (x,y) → (a,b) where point = a*1 + b*ω
 * [a]   [1   0  ]^-1   [x]     [  1     0    ] [x]     [   x                    ]
 * [b] = [ωre ωim ]    × [y]  =  [1/ωre  1/ωim] [y] ... but better: solve directly
 *
 * x = a + b*ωre  = a - 0.5*b
 * y = b*ωim      = b*(√3/2)
 *
 * → b = y / (√3/2) = 2y/√3
 * → a = x + 0.5*b = x + y/√3
 */
static const double INV_SQRT3 = 0.5773502691896258; /* 1/√3 */
static const double TWO_OVER_SQRT3 = 1.1547005383792515; /* 2/√3 */

/* ── Internal: round to nearest Eisenstein integer ── */

/* The A₂ lattice in Eisenstein coordinates is Z[ω].
 * A point (a,b) in R² snaps to the nearest lattice point by rounding
 * in a skewed coordinate system. We use the algorithm:
 *
 * 1. Round (a,b) to nearest integers (i,j)
 * 2. Compute the fractional offsets
 * 3. If |f_a| + |f_b| > 1, adjust by the nearest neighbor
 */

typedef struct {
    double a; /* snapped a-coordinate (integer) */
    double b; /* snapped b-coordinate (integer) */
    double error; /* distance from original point */
    double angle; /* angle in radians from snapped point to original */
} snap_internal_t;

static snap_internal_t snap_to_lattice(double x, double y) {
    snap_internal_t result;

    /* Convert Cartesian (x,y) to Eisenstein coordinates (a,b)
     * where point = a + b*ω, ω = (-1/2, √3/2)
     *   a = x - y*ωre/ωim = x + y/√3
     *   b = y/ωim = 2y/√3
     */
    double a_f = x - y * EISENSTEIN_OMEGA_RE / EISENSTEIN_OMEGA_IM;
    double b_f = y / EISENSTEIN_OMEGA_IM;

    double a0 = round(a_f);
    double b0 = round(b_f);

    /* 9-candidate Voronoi search (matches Rust reference implementation)
     * This guarantees finding the nearest lattice point within the
     * covering radius ρ = 1/√3 for the A₂ lattice.
     */
    double best_a = a0;
    double best_b = b0;
    double best_err = 1e30;

    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            double ca = a0 + da;
            double cb = b0 + db;
            /* Convert Eisenstein (ca, cb) back to Cartesian */
            double cx = ca + cb * EISENSTEIN_OMEGA_RE;
            double cy = cb * EISENSTEIN_OMEGA_IM;
            double dx = x - cx;
            double dy = y - cy;
            double err = sqrt(dx * dx + dy * dy);
            if (err < best_err) {
                best_a = ca;
                best_b = cb;
                best_err = err;
            }
        }
    }

    /* Compute displacement vector for angle */
    double snap_x = best_a + best_b * EISENSTEIN_OMEGA_RE;
    double snap_y = best_b * EISENSTEIN_OMEGA_IM;
    double dx = x - snap_x;
    double dy = y - snap_y;

    result.a = best_a;
    result.b = best_b;
    result.error = best_err;
    result.angle = atan2(dy, dx);

    return result;
}

/* ── Dodecet encoding ── */

/*
 * Dodecet = 12 bits packed into uint16_t:
 *   bits 0-3:  error level (0-15), quantized from error / covering_radius * 15
 *   bits 4-7:  angle level (0-15), quantized from angle + π mapped to [0, 2π)
 *   bits 8-11: chamber (0-5), Weyl chamber classification
 *   bits 12-15: reserved (0)
 *
 * The A₂ covering radius is ρ = 1/√3 ≈ 0.5774
 */
static const double COVERING_RADIUS = 0.5773502691896258; /* 1/√3 */

static uint16_t encode_dodecet(double error, double angle, int chamber) {
    /* Error level: 0-15, clamp to covering radius */
    int error_level = (int)(error / COVERING_RADIUS * 15.0);
    if (error_level > 15) error_level = 15;
    if (error_level < 0) error_level = 0;

    /* Angle level: 0-15, map [-π, π) → [0, 16) */
    double normalized_angle = angle + M_PI; /* now [0, 2π) */
    int angle_level = (int)(normalized_angle / (2.0 * M_PI) * 16.0);
    if (angle_level > 15) angle_level = 15;
    if (angle_level < 0) angle_level = 0;

    /* Chamber: 0-5 (Weyl group of A₂ has 6 elements) */
    if (chamber > 5) chamber = 5;
    if (chamber < 0) chamber = 0;

    return (uint16_t)((error_level & 0xF)
                    | ((angle_level & 0xF) << 4)
                    | ((chamber & 0xF) << 8));
}

/* ── Weyl chamber classification ── */

/*
 * The Weyl group W(A₂) ≅ S₃ has 6 elements, corresponding to 6 chambers.
 * Chambers are determined by the sign pattern and ordering of the coordinates
 * in the root space.
 *
 * For a point (x,y), we classify based on angle sectors:
 *   Chamber 0: 0° ≤ θ < 60°
 *   Chamber 1: 60° ≤ θ < 120°
 *   Chamber 2: 120° ≤ θ < 180°
 *   Chamber 3: 180° ≤ θ < 240°
 *   Chamber 4: 240° ≤ θ < 300°
 *   Chamber 5: 300° ≤ θ < 360°
 *
 * This is the standard 6-fold partition of the plane by the A₂ Weyl group.
 */
static int classify_chamber(double angle) {
    /* Normalize angle to [0, 2π) */
    double a = fmod(angle, 2.0 * M_PI);
    if (a < 0) a += 2.0 * M_PI;

    /* Each chamber spans 60° = π/3 radians */
    int chamber = (int)(a / (M_PI / 3.0));
    if (chamber > 5) chamber = 5;
    return chamber;
}

/* ── Public API ── */

eisenstein_result_t eisenstein_snap(float x, float y) {
    eisenstein_result_t result;

    /* Step 1: Snap to nearest A₂ lattice point (9-candidate Voronoi search) */
    snap_internal_t snap = snap_to_lattice((double)x, (double)y);

    /* Step 3: Classify Weyl chamber */
    /* Use the displacement angle for chamber classification */
    int chamber;
    if (snap.error < 1e-12) {
        chamber = 0; /* exact lattice point */
    } else {
        chamber = classify_chamber(snap.angle);
    }

    /* Step 4: Encode dodecet */
    result.dodecet = encode_dodecet(snap.error, snap.angle, chamber);

    /* Step 5: Fill remaining fields */
    result.error = (float)snap.error;
    result.chamber = (uint8_t)chamber;
    result.flags = 0;
    if (snap.error < COVERING_RADIUS) {
        result.flags |= EISENSTEIN_FLAG_SAFE;
    }

    return result;
}

void eisenstein_batch_snap(
    const float *points,
    size_t n,
    eisenstein_result_t *results)
{
    for (size_t i = 0; i < n; i++) {
        results[i] = eisenstein_snap(points[2*i], points[2*i + 1]);
    }
}

float eisenstein_holonomy_4cycle(
    const eisenstein_result_t results[4])
{
    /* Holonomy H = w0*w1 - w2*w3
     * where wi = dodecet value treated as float weight */
    float w0 = (float)results[0].dodecet;
    float w1 = (float)results[1].dodecet;
    float w2 = (float)results[2].dodecet;
    float w3 = (float)results[3].dodecet;

    float H = w0 * w1 - w2 * w3;

    /* Normalize to [0, 1]. Max possible |H| = 4095*4095 ≈ 16M,
     * but dodecets are 12-bit (0-4095). Use a reasonable normalization.
     * In practice, values are much smaller. Normalize by max^2 / 4. */
    float H_norm = fabsf(H) / (4095.0f * 4095.0f / 4.0f);
    if (H_norm > 1.0f) H_norm = 1.0f;

    return H_norm;
}

void eisenstein_batch_holonomy(
    const eisenstein_result_t *results,
    size_t n,
    float *holonomy)
{
    for (size_t i = 0; i < n; i++) {
        holonomy[i] = eisenstein_holonomy_4cycle(&results[4 * i]);
    }
}
