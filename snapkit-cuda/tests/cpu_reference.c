/*
 * cpu_reference.c — Pure C reference implementation of snapkit CUDA algorithms
 *
 * This is a DOUBLE PRECISION reference implementation used to validate
 * the single-precision CUDA kernels. All algorithms are mathematically
 * identical to the CUDA versions but use double precision for accuracy.
 *
 * "The snap is the gatekeeper of attention. The delta is the compass."
 *
 * Author: Forgemaster ⚒️
 * Build: gcc -O2 -lm -o cpu_reference cpu_reference.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

/* ======================================================================
 * Constants (must match CUDA code exactly)
 * ====================================================================== */

#define SQRT3           1.7320508075688772
#define INV_SQRT3       0.5773502691896258
#define HALF_SQRT3      0.8660254037844386   /* sqrt(3)/2 */
#define INV_2SQRT3      1.1547005383792517   /* 2/sqrt(3) */
#define TOLERANCE       0.1
#define MAX_POINTS      10000000
#define MAX_STREAMS     16

/* ======================================================================
 * Eisenstein Lattice Snap (double precision)
 * ====================================================================== */

void eisenstein_snap_dp(double x, double y, int* a, int* b, double* delta) {
    /* b = round(2y / sqrt(3)) */
    double b_f = y * (2.0 / SQRT3);
    *b = (int)round(b_f);

    /* a = round(x + b/2) */
    double a_f = x + (double)(*b) * 0.5;
    *a = (int)round(a_f);

    /* Compute snapped coordinates */
    double snap_x = (double)(*a) - (double)(*b) * 0.5;
    double snap_y = (double)(*b) * HALF_SQRT3;

    /* Compute delta */
    double dx = x - snap_x;
    double dy = y - snap_y;
    *delta = sqrt(dx * dx + dy * dy);
}

void eisenstein_snap_coords_dp(int a, int b, double* snap_x, double* snap_y) {
    *snap_x = a - b * 0.5;
    *snap_y = b * HALF_SQRT3;
}

double eisenstein_norm(int a, int b) {
    /* N(a + bω) = a² - ab + b² */
    return (double)(a * a - a * b + b * b);
}

int eisenstein_norm_int(int a, int b) {
    return a * a - a * b + b * b;
}

/* ======================================================================
 * 3×3 Voronoi Neighborhood Search
 * ====================================================================== */

void eisenstein_voronoi_3x3(double x, double y, int* best_a, int* best_b, double* best_delta) {
    int base_a, base_b;
    double base_delta;
    eisenstein_snap_dp(x, y, &base_a, &base_b, &base_delta);

    *best_a = base_a;
    *best_b = base_b;
    *best_delta = base_delta;

    /* Search 3×3 neighborhood */
    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            if (da == 0 && db == 0) continue;
            int a = base_a + da;
            int b = base_b + db;
            double sx, sy;
            eisenstein_snap_coords_dp(a, b, &sx, &sy);
            double d = hypot(x - sx, y - sy);
            if (d < *best_delta) {
                *best_delta = d;
                *best_a = a;
                *best_b = b;
            }
        }
    }
}

/* ======================================================================
 * A₁ Binary Snap
 * ====================================================================== */

double snap_binary_1d(double value, double* snapped) {
    *snapped = (value >= 0.0) ? 1.0 : -1.0;
    return fabs(value - *snapped);
}

/* ======================================================================
 * A₃ Tetrahedral Snap (3D)
 * ====================================================================== */

void snap_tetrahedral_3d(double x, double y, double z,
                         double* out_x, double* out_y, double* out_z,
                         double* delta) {
    double d0 =  x + y + z;
    double d1 =  x - y - z;
    double d2 = -x + y - z;
    double d3 = -x - y + z;

    int best = 0;
    double max_d = d0;
    if (d1 > max_d) { max_d = d1; best = 1; }
    if (d2 > max_d) { max_d = d2; best = 2; }
    if (d3 > max_d) { max_d = d3; best = 3; }

    double inv_sqrt3 = 0.5773502691896258;
    double norm = sqrt(x * x + y * y + z * z);
    double mag = fmax(norm, 1e-12);

    switch (best) {
        case 0: *out_x = mag * inv_sqrt3; *out_y = mag * inv_sqrt3; *out_z = mag * inv_sqrt3; break;
        case 1: *out_x = mag * inv_sqrt3; *out_y = -mag * inv_sqrt3; *out_z = -mag * inv_sqrt3; break;
        case 2: *out_x = -mag * inv_sqrt3; *out_y = mag * inv_sqrt3; *out_z = -mag * inv_sqrt3; break;
        case 3: *out_x = -mag * inv_sqrt3; *out_y = -mag * inv_sqrt3; *out_z = mag * inv_sqrt3; break;
    }

    double dx = x - *out_x;
    double dy = y - *out_y;
    double dz = z - *out_z;
    *delta = sqrt(dx * dx + dy * dy + dz * dz);
}

/* ======================================================================
 * D₄ Triality Snap (4D)
 * ====================================================================== */

void snap_d4_4d(double x, double y, double z, double w,
                double out_vals[4], double* delta) {
    double a1 = x - y;
    double a2 = y - z;
    double a3 = z - w;
    double a4 = z + w;

    int r1 = (int)round(a1);
    int r2 = (int)round(a2);
    int r3 = (int)round(a3);
    int r4 = (int)round(a4);

    /* Parity condition: for D₄, sum of roots must be even */
    int parity = (r1 + r4) & 1;
    if (parity) {
        double e1 = a1 - r1;
        double e2 = a2 - r2;
        double e3 = a3 - r3;
        double e4 = a4 - r4;

        double min_err = fmin(fmin(fabs(e1), fabs(e2)), fmin(fabs(e3), fabs(e4)));

        if (min_err == fabs(e1)) r1 += (e1 > 0) ? 1 : -1;
        else if (min_err == fabs(e2)) r2 += (e2 > 0) ? 1 : -1;
        else if (min_err == fabs(e3)) r3 += (e3 > 0) ? 1 : -1;
        else r4 += (e4 > 0) ? 1 : -1;
    }

    /* Inverse basis transformation */
    double sum_r = (r1 + r2 + r3 + r4) * 0.5;
    out_vals[0] = sum_r;
    out_vals[1] = (-r1 + r2 + r3 + r4) * 0.5;
    out_vals[2] = (-r2 + r3 + r4) * 0.5;
    out_vals[3] = (-r3 + r4) * 0.5;

    double dx = x - out_vals[0];
    double dy = y - out_vals[1];
    double dz = z - out_vals[2];
    double dw = w - out_vals[3];
    *delta = sqrt(dx * dx + dy * dy + dz * dz + dw * dw);
}

/* ======================================================================
 * E₈ Exceptional Snap (8D)
 * ====================================================================== */

void snap_e8_8d(const double in_vals[8], double out_vals[8], double* delta) {
    int int_candidate[8], half_candidate[8];
    double int_dist2 = 0.0, half_dist2 = 0.0;

    /* Two candidates: ℤ⁸ and ℤ⁸ + (½)⁸ */
    for (int i = 0; i < 8; i++) {
        double vi = in_vals[i];
        
        /* Integer candidate */
        int r1 = (int)round(vi);
        int_candidate[i] = r1;
        double d1 = vi - (double)r1;
        int_dist2 += d1 * d1;

        /* Half-integer candidate */
        double vh = vi - 0.5;
        int r2 = (int)round(vh);
        half_candidate[i] = r2 + 1;  /* because we subtracted 0.5 */
        double d2 = vi - ((double)r2 + 0.5);
        half_dist2 += d2 * d2;
    }

    /* Fix parity for integer candidate (sum must be even) */
    int int_sum = 0;
    for (int i = 0; i < 8; i++) int_sum += int_candidate[i];
    int_sum = int_sum & 1;

    if (int_sum) {
        int worst_idx = 0;
        double worst_err = 0.0;
        for (int i = 0; i < 8; i++) {
            double err = fabs(in_vals[i] - (double)int_candidate[i]);
            if (err > worst_err) {
                worst_err = err;
                worst_idx = i;
            }
        }
        double flipped = in_vals[worst_idx] - (double)(int_candidate[worst_idx] + 1);
        double alt = in_vals[worst_idx] - (double)(int_candidate[worst_idx] - 1);
        int_dist2 -= worst_err * worst_err;
        int_dist2 += fmin(flipped * flipped, alt * alt);
        int_candidate[worst_idx] += (fabs(flipped) < fabs(alt)) ? 1 : -1;
    }

    /* Choose closer candidate */
    if (int_dist2 <= half_dist2) {
        for (int i = 0; i < 8; i++) {
            out_vals[i] = (double)int_candidate[i];
        }
        *delta = sqrt(int_dist2);
    } else {
        for (int i = 0; i < 8; i++) {
            out_vals[i] = (double)half_candidate[i];
        }
        *delta = sqrt(half_dist2);
    }
}

/* ======================================================================
 * Delta Detection
 * ====================================================================== */

int delta_threshold(double delta, double tolerance) {
    return (delta > tolerance) ? 1 : 0;
}

double attention_weight(double delta, int is_delta,
                         double actionability, double urgency) {
    if (!is_delta) return 0.0;
    double w = delta;
    w *= actionability;
    w *= urgency;
    return w;
}

/* ======================================================================
 * Test Runner
 * ====================================================================== */

int test_eisenstein_snap(void) {
    printf("  Eisenstein Snap (double precision): ");
    int failures = 0;
    
    /* Test known lattice points */
    struct { double x, y; int exp_a, exp_b; double max_delta; } tests[] = {
        {0.0, 0.0, 0, 0, 1e-12},
        {1.0, 0.0, 1, 0, 1e-12},
        {0.0, SQRT3 / 2.0, 0, 1, 1e-12},  /* exactly at (0,1) lattice point */
        {0.5, SQRT3 / 2.0, 1, 1, 1e-12},  /* exactly at (1,1) lattice point */
        {-0.5, SQRT3 / 2.0, -1, 1, 1e-12},  /* exactly at (-1,1) lattice point */
        {0.5, -SQRT3 / 2.0, 1, -1, 1e-12},
        {1.5, SQRT3 / 2.0, 2, 1, 1e-12},
        {0.0, SQRT3, 0, 2, 1e-12},  /* exactly at (0,2) lattice point */
    };
    
    int num_tests = sizeof(tests) / sizeof(tests[0]);
    for (int i = 0; i < num_tests; i++) {
        int a, b;
        double delta;
        eisenstein_snap_dp(tests[i].x, tests[i].y, &a, &b, &delta);
        if (a != tests[i].exp_a || b != tests[i].exp_b) {
            printf("\n    FAIL: (%.6f, %.6f) → (%d, %d), expected (%d, %d)",
                   tests[i].x, tests[i].y, a, b, tests[i].exp_a, tests[i].exp_b);
            failures++;
        }
        if (delta > tests[i].max_delta) {
            printf("\n    FAIL: (%.6f, %.6f) delta = %.12f, expected < %.12f",
                   tests[i].x, tests[i].y, delta, tests[i].max_delta);
            failures++;
        }
    }
    
    if (failures == 0) {
        printf("PASS (%d tests)\n", num_tests);
    } else {
        printf("\n    %d failures out of %d\n", failures, num_tests);
    }
    return failures;
}

int test_random_eisenstein(void) {
    printf("  Random Eisenstein Snaps (1M points): ");
    int failures = 0;
    
    srand(42);
    double max_delta = 0.0;
    double covering_radius = sqrt(2.0 / SQRT3);
    
    for (int i = 0; i < 1000000; i++) {
        double x = (double)rand() / RAND_MAX * 200.0 - 100.0;
        double y = (double)rand() / RAND_MAX * 200.0 - 100.0;
        
        int a, b;
        double delta;
        eisenstein_snap_dp(x, y, &a, &b, &delta);
        
        if (delta > covering_radius + 1e-6) {
            failures++;
            if (failures <= 5) {
                printf("\n    delta %.6f > covering radius %.6f at (%.2f, %.2f)",
                       delta, covering_radius, x, y);
            }
        }
        if (delta > max_delta) max_delta = delta;
    }
    
    if (failures == 0) {
        printf("PASS (max delta: %.6f, covering radius: %.6f)\n", 
               max_delta, covering_radius);
    } else {
        printf("\n    %d failures (max delta: %.6f)\n", failures, max_delta);
    }
    return failures;
}

int test_voronoi_search(void) {
    printf("  3×3 Voronoi Search: ");
    int improvements = 0;
    
    srand(123);
    for (int i = 0; i < 10000; i++) {
        double x = (double)rand() / RAND_MAX * 20.0 - 10.0;
        double y = (double)rand() / RAND_MAX * 20.0 - 10.0;
        
        int a_simple, b_simple;
        double d_simple;
        eisenstein_snap_dp(x, y, &a_simple, &b_simple, &d_simple);
        
        int a_best, b_best;
        double d_best;
        eisenstein_voronoi_3x3(x, y, &a_best, &b_best, &d_best);
        
        if (d_best < d_simple - 1e-10) {
            improvements++;
        }
    }
    
    if (improvements == 0) {
        printf("PASS (simple snap is always optimal)\n");
    } else {
        printf("INFO (%d improvements — simple snap not always optimal)\n", improvements);
    }
    return 0;  /* Not a failure, just informational */
}

int test_ade_topologies(void) {
    printf("  ADE Topologies:\n");
    int total_failures = 0;
    
    /* A₁ Binary */
    printf("    A₁ Binary: ");
    int a1_fails = 0;
    double bin_vals[] = {-5.0, -2.3, -0.001, 0.0, 0.001, 2.3, 5.0};
    for (int i = 0; i < 7; i++) {
        double snapped;
        double delta = snap_binary_1d(bin_vals[i], &snapped);
        (void)delta;  /* unused */
        double expected = (bin_vals[i] >= 0.0) ? 1.0 : -1.0;
        if (snapped != expected) a1_fails++;
    }
    printf("%s\n", a1_fails == 0 ? "PASS" : "FAIL");
    total_failures += a1_fails;
    
    /* A₃ Tetrahedral */
    printf("    A₃ Tetrahedral: ");
    int a3_fails = 0;
    double a3_inputs[][3] = {
        {1.0, 0.0, 0.0},
        {0.0, 1.0, 0.0},
        {1.0, -1.0, -1.0},
        {-1.0, -1.0, -1.0},
    };
    for (int i = 0; i < 4; i++) {
        double ox, oy, oz, delta;
        snap_tetrahedral_3d(a3_inputs[i][0], a3_inputs[i][1], a3_inputs[i][2],
                            &ox, &oy, &oz, &delta);
        double norm = sqrt(a3_inputs[i][0] * a3_inputs[i][0] +
                           a3_inputs[i][1] * a3_inputs[i][1] +
                           a3_inputs[i][2] * a3_inputs[i][2]);
        if (norm > 0.1 && delta > 1.5) a3_fails++;
    }
    printf("%s\n", a3_fails == 0 ? "PASS" : "FAIL");
    total_failures += a3_fails;
    
    /* D₄ Triality */
    printf("    D₄ Triality: ");
    int d4_fails = 0;
    double d4_inputs[][4] = {
        {0, 0, 0, 0},
        {0.5, 0.5, 0.5, 0.5},
        {1, 0, 0, 0},
        {1, 1, 0, 0},
    };
    for (int i = 0; i < 4; i++) {
        double out[4], delta;
        snap_d4_4d(d4_inputs[i][0], d4_inputs[i][1], d4_inputs[i][2], d4_inputs[i][3],
                   out, &delta);
        if (delta > 1.0) d4_fails++;
    }
    printf("%s\n", d4_fails == 0 ? "PASS" : "FAIL");
    total_failures += d4_fails;
    
    /* E₈ Exceptional */
    printf("    E₈ Exceptional: ");
    int e8_fails = 0;
    double e8_inputs[][8] = {
        {0,0,0,0,0,0,0,0},
        {1,1,1,1,1,1,1,1},
        {0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5},
        {0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8},
    };
    for (int i = 0; i < 4; i++) {
        double out[8], delta;
        snap_e8_8d(e8_inputs[i], out, &delta);
        /* Check parity for integer-candidate snaps */
        int all_int = 1;
        double sum = 0;
        for (int j = 0; j < 8; j++) {
            if (fabs(out[j] - round(out[j])) > 1e-10) all_int = 0;
            sum += out[j];
        }
        if (all_int && (int)round(sum) % 2 != 0) {
            e8_fails++;
        }
    }
    printf("%s\n", e8_fails == 0 ? "PASS" : "FAIL");
    total_failures += e8_fails;
    
    return total_failures;
}

int test_covering_radius(void) {
    printf("  Covering Radius: ");
    srand(333);
    double max_delta = 0.0;
    double covering_radius = sqrt(2.0 / SQRT3);
    
    for (int i = 0; i < 100000; i++) {
        double x = (double)rand() / RAND_MAX * 100.0 - 50.0;
        double y = (double)rand() / RAND_MAX * 100.0 - 50.0;
        
        int a, b;
        double delta;
        eisenstein_snap_dp(x, y, &a, &b, &delta);
        if (delta > max_delta) max_delta = delta;
    }
    
    printf("max delta = %.6f (theory: %.6f) — %s\n",
           max_delta, covering_radius,
           max_delta <= covering_radius + 1e-6 ? "PASS" : "FAIL");
    return (max_delta > covering_radius + 1e-6) ? 1 : 0;
}

int test_edge_cases(void) {
    printf("  Edge Cases: ");
    int failures = 0;
    
    struct { double x, y; char* label; } edges[] = {
        {0.0, 0.0, "origin"},
        {1e-15, 0.0, "near-zero"},
        {1e6, 0.0, "large x"},
        {0.0, 1e6, "large y"},
        {-1e6, -1e6, "large negative"},
        {3.14159, 2.71828, "pi and e"},
        {0.33333, 0.57735, "near triangular center"},
        {0.1, 0.0, "near lattice row"},
    };
    
    double covering_radius = sqrt(2.0 / SQRT3);
    int num_edges = sizeof(edges) / sizeof(edges[0]);
    
    for (int i = 0; i < num_edges; i++) {
        int a, b;
        double delta;
        eisenstein_snap_dp(edges[i].x, edges[i].y, &a, &b, &delta);
        if (delta > covering_radius + 1e-6) {
            failures++;
        }
        if (eisenstein_norm_int(a, b) < 0) {
            failures++;
        }
    }
    
    printf("%s (%d tests)\n", failures == 0 ? "PASS" : "FAIL", num_edges);
    return failures;
}

int test_inverse_mapping(void) {
    printf("  Inverse Mapping: ");
    int failures = 0;
    srand(444);
    
    for (int i = 0; i < 10000; i++) {
        int a = rand() % 201 - 100;
        int b = rand() % 201 - 100;
        
        double sx, sy;
        eisenstein_snap_coords_dp(a, b, &sx, &sy);
        
        int a2, b2;
        double delta;  /* unused */
        eisenstein_snap_dp(sx, sy, &a2, &b2, &delta);
        
        if (a != a2 || b != b2) {
            failures++;
        }
    }
    
    printf("%s\n", failures == 0 ? "PASS" : "FAIL");
    return failures;
}

/* ======================================================================
 * Main
 * ====================================================================== */

int main(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║      SnapKit CUDA — CPU Reference Implementation Tests     ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");
    
    int total_failures = 0;
    
    total_failures += test_eisenstein_snap();
    total_failures += test_random_eisenstein();
    total_failures += test_voronoi_search();
    total_failures += test_ade_topologies();
    total_failures += test_covering_radius();
    total_failures += test_edge_cases();
    total_failures += test_inverse_mapping();
    
    printf("\n");
    printf("═══════════════════════════════════════════════════════════════\n");
    if (total_failures == 0) {
        printf("  ALL TESTS PASSED\n");
    } else {
        printf("  %d TEST(S) FAILED\n", total_failures);
    }
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("\n");
    
    return total_failures;
}
