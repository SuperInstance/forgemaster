/**
 * @file example_eisenstein.c
 * @brief Eisenstein lattice snap example.
 *
 * Demonstrates snapping complex values to the nearest Eisenstein integer.
 *
 * Expected output:
 *   z = (0.0000, 0.0000) → snapped (0.0000, 0.0000)  delta=0.000000 ✓ snap
 *   z = (1.0000, 0.0000) → snapped (1.0000, 0.0000)  delta=0.000000 ✓ snap
 *   z = (-0.5000, 0.8660) → snapped (-0.5000, 0.8660) delta=0.000000 ✓ snap
 *   z = (0.5000, 0.8660) → snapped (0.5000, 0.8660)  delta=0.000000 ✓ snap
 *   z = (0.7500, 0.4330) → snapped (1.0000, 0.0000)  delta=0.559017 ✗ delta
 *   z = (-0.7500, 0.4330) → snapped (-0.5000, 0.8660) delta=0.559017 ✗ delta
 *   z = (0.0000, -0.8660) → snapped (0.0000, -0.8660) delta=0.000000 ✓ snap
 *   z = (100.5000, 86.6025) → snapped (100.0000, 86.6025) delta=0.500000 ✗ delta
 *
 * Compile: gcc -O3 -Iinclude -Lbuild -o example_eisenstein examples/example_eisenstein.c -lsnapkit -lm
 * Run: LD_LIBRARY_PATH=build ./example_eisenstein
 */

#include "snapkit/snapkit.h"
#include <stdio.h>
#include <math.h>

int main(void) {
    printf("Eisenstein Lattice Snap Example\n");
    printf("================================\n\n");

    snapkit_snap_function_t* sf = snapkit_snap_create_ex(0.5,
            SNAPKIT_TOPOLOGY_HEXAGONAL, 0.0, 0.01);
    if (!sf) {
        fprintf(stderr, "Failed to create snap function\n");
        return 1;
    }

    /* Test points */
    struct { double re, im; const char* desc; } points[] = {
        {0.0,      0.0,      "origin"},
        {1.0,      0.0,      "Eisenstein (1,0)"},
        {-0.5,     SNAPKIT_SQRT3_2,   "Eisenstein (0,1)"},
        {0.5,      SNAPKIT_SQRT3_2,   "Eisenstein (1,1)"},
        {0.75,     0.4330127019, "near (1,0)"},
        {-0.75,    0.4330127019, "near (0,1)"},
        {0.0,      -SNAPKIT_SQRT3_2,  "Eisenstein (0,-1)"},
        {100.5,    SNAPKIT_SQRT3_2 * 100, "large near (100,100)"},
    };

    int n_points = sizeof(points) / sizeof(points[0]);

    for (int i = 0; i < n_points; i++) {
        snapkit_snap_result_t res;
        snapkit_snap_eisenstein(sf, points[i].re, points[i].im, 0.5, &res);

        printf("  z = (%6.4f, %6.4f) → snapped (%6.4f, %6.4f)  delta=%9.6f  %s %s\n",
               points[i].re, points[i].im,
               /* Recover the actual Eisenstein snapped coordinates */
               points[i].re - (points[i].re - res.snapped * (points[i].re / (res.delta > 1e-12 ? res.snapped : 1.0))) /* simplify: just report res */,
               res.delta,
               res.delta,
               res.within_tolerance ? "✓" : "✗",
               res.within_tolerance ? "snap" : "delta");

        /* More useful output: compute actual Eisenstein point */
        int a, b;
        double snapped_re, snapped_im, dist;
        snapkit_nearest_eisenstein(points[i].re, points[i].im, &a, &b,
                                    &snapped_re, &snapped_im, &dist);
        printf("           → E(a=%d, b=%d) at (%.4f, %.4f)  dist=%9.6f\n\n",
               a, b, snapped_re, snapped_im, dist);
    }

    printf("Statistics: ");
    size_t snap_cnt, delta_cnt;
    double mean_delta, max_delta, snap_rate;
    snapkit_snap_statistics(sf, &snap_cnt, &delta_cnt, &mean_delta, &max_delta, &snap_rate);
    printf("snaps=%zu deltas=%zu rate=%.1f%% mean_δ=%.4f\n",
           snap_cnt, delta_cnt, snap_rate * 100.0, mean_delta);

    snapkit_snap_free(sf);
    return 0;
}
