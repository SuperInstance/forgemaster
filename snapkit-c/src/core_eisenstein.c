/**
 * @file core_eisenstein.c
 * @brief Eisenstein lattice snap (A₂) — the core geometric primitive.
 *
 * The Eisenstein lattice ℤ[ω] (ω = e^(2πi/3)) provides optimal 2D
 * information compression: densest packing, isotropic (6-fold symmetry),
 * and PID property guaranteeing H¹ = 0 (local → global consistency).
 */

#include "snapkit/snapkit_internal.h"
#include <math.h>
#include <stdlib.h>
#include <float.h>

/* ===========================================================================
 * Eisenstein snap (core math)
 * ========================================================================= */

void snapkit_nearest_eisenstein(double real, double imag,
                                 int* a, int* b,
                                 double* snapped_re, double* snapped_im,
                                 double* dist) {
    /*
     * Step 1: Compute floating-point (a, b) coordinates in basis (1, ω)
     * where ω = e^(2πi/3) = -1/2 + i√3/2
     *
     * z = x + iy
     *   = a + b·ω
     *   = a + b·(-1/2 + i√3/2)
     *   = (a - b/2) + i(b√3/2)
     *
     * Therefore:
     *   y = b·√3/2  →  b = 2y/√3
     *   x = a - b/2 →  a = x + b/2 = x + y/√3
     */

    double b_float = 2.0 * imag * SNAPKIT_INV_SQRT3;
    double a_float = real + imag * SNAPKIT_INV_SQRT3;

    /* Step 2: Get initial integer candidate via rounding */
    int a0 = (int)round(a_float);
    int b0 = (int)round(b_float);

    /* Step 3: Check all 9 candidates (3x3 neighborhood)
     * The Voronoi cell of a 2D hexagonal lattice has 6 neighbors,
     * so a 3x3 sweep finds the true nearest Eisenstein integer.
     * Direct rounding alone fails on ~3-5% of boundary cases.
     */
    int best_a = a0, best_b = b0;
    double best_d2 = DBL_MAX;

    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            int ca = a0 + da;
            int cb = b0 + db;
            /* Map Eisenstein integer (ca, cb) back to Cartesian:
             *   x = ca - cb/2
             *   y = cb·√3/2
             */
            double cx = (double)ca - (double)cb * 0.5;
            double cy = (double)cb * SNAPKIT_SQRT3_2;
            double dx = real - cx;
            double dy = imag - cy;
            double d2 = dx * dx + dy * dy;
            if (d2 < best_d2) {
                best_d2 = d2;
                best_a = ca;
                best_b = cb;
            }
        }
    }

    *a = best_a;
    *b = best_b;
    *snapped_re = (double)best_a - (double)best_b * 0.5;
    *snapped_im = (double)best_b * SNAPKIT_SQRT3_2;
    *dist = sqrt(best_d2);
}

#if SNAPKIT_HAVE_NEON
void snapkit_nearest_eisenstein_neon(const double* reals, const double* imags,
                                      int* a_out, int* b_out,
                                      double* snapped_re_out, double* snapped_im_out,
                                      double* dist_out, size_t n) {
    /*
     * NEON batch Eisenstein snap — processes 2 double-precision values
     * per iteration using SIMD for the coordinate transformation step.
     *
     * The 3x3 Voronoi search remains scalar for correctness (NEON's
     * pairwise min would be fragile around boundary decisions).
     */

    size_t i = 0;
    for (; i + 1 < n; i += 2) {
        /* Load 2 reals and 2 imags */
        float64x2_t re = vld1q_f64(&reals[i]);
        float64x2_t im = vld1q_f64(&imags[i]);
        float64x2_t inv_sqrt3_v = vdupq_n_f64(SNAPKIT_INV_SQRT3);

        /* b_float = 2.0 * imag * inv_sqrt3 */
        float64x2_t b_float = vmulq_f64(im, inv_sqrt3_v);
        b_float = vaddq_f64(b_float, b_float); /* multiply by 2 */

        /* a_float = real + imag * inv_sqrt3 */
        float64x2_t a_float = vmulq_f64(im, inv_sqrt3_v);
        a_float = vaddq_f64(re, a_float);

        /* Store to temp and round (NEON A32/T32 lacks vrndnq_f64) */
        double a_vals[2], b_vals[2];
        vst1q_f64(a_vals, a_float);
        vst1q_f64(b_vals, b_float);

        int a0[2], b0[2];
        for (int j = 0; j < 2; j++) {
            a0[j] = (int)round(a_vals[j]);
            b0[j] = (int)round(b_vals[j]);
        }

        /* Scalar 3x3 Voronoi search per element (correctness > throughput) */
        for (int j = 0; j < 2; j++) {
            int best_a = a0[j], best_b = b0[j];
            double best_d2 = DBL_MAX;
            for (int da = -1; da <= 1; da++) {
                for (int db = -1; db <= 1; db++) {
                    int ca = a0[j] + da;
                    int cb = b0[j] + db;
                    double cx = (double)ca - (double)cb * 0.5;
                    double cy = (double)cb * SNAPKIT_SQRT3_2;
                    double dx = reals[i+j] - cx;
                    double dy = imags[i+j] - cy;
                    double d2 = dx * dx + dy * dy;
                    if (d2 < best_d2) {
                        best_d2 = d2;
                        best_a = ca;
                        best_b = cb;
                    }
                }
            }
            a_out[i+j] = best_a;
            b_out[i+j] = best_b;
            snapped_re_out[i+j] = (double)best_a - (double)best_b * 0.5;
            snapped_im_out[i+j] = (double)best_b * SNAPKIT_SQRT3_2;
            dist_out[i+j] = sqrt(best_d2);
        }
    }

    /* Handle remaining odd element */
    for (; i < n; i++) {
        snapkit_nearest_eisenstein(reals[i], imags[i],
                                    &a_out[i], &b_out[i],
                                    &snapped_re_out[i], &snapped_im_out[i],
                                    &dist_out[i]);
    }
}
#else
void snapkit_nearest_eisenstein_neon(const double* reals, const double* imags,
                                      int* a_out, int* b_out,
                                      double* snapped_re_out, double* snapped_im_out,
                                      double* dist_out, size_t n) {
    for (size_t i = 0; i < n; i++) {
        snapkit_nearest_eisenstein(reals[i], imags[i],
                                    &a_out[i], &b_out[i],
                                    &snapped_re_out[i], &snapped_im_out[i],
                                    &dist_out[i]);
    }
}
#endif /* SNAPKIT_HAVE_NEON */
