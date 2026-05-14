/*
 * bench_zeta12.c — Benchmark Z[ζ₁₂] vs Eisenstein snap
 * Compile: gcc -O3 -mavx512f -ffast-math -o bench_zeta12 bench_zeta12.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "zeta12_snap.h"

#define N_POINTS 10000

/* Simple xoshiro128+ for fast random numbers */
static unsigned long rng_state[2] = {0x1234567890ABCDEF, 0xFEDCBA0987654321};

static inline double rng_gauss(void) {
    /* Box-Muller */
    double u1 = ((rng_state[0] ^= rng_state[0] << 13, rng_state[0] ^= rng_state[0] >> 7,
                  rng_state[0] ^= rng_state[0] << 17) & 0xFFFFFFFF) / 4294967296.0;
    double u2 = ((rng_state[1] ^= rng_state[1] << 13, rng_state[1] ^= rng_state[1] >> 7,
                  rng_state[1] ^= rng_state[1] << 17) & 0xFFFFFFFF) / 4294967296.0;
    if (u1 < 1e-10) u1 = 1e-10;
    return sqrt(-2.0 * log(u1)) * cos(2.0 * 3.14159265358979 * u2);
}

int main(void) {
    double *x = malloc(N_POINTS * sizeof(double));
    double *y = malloc(N_POINTS * sizeof(double));
    double *d_z12 = malloc(N_POINTS * sizeof(double));
    double *d_eis = malloc(N_POINTS * sizeof(double));

    /* Generate random points */
    for (int i = 0; i < N_POINTS; i++) {
        x[i] = rng_gauss() * 10.0;
        y[i] = rng_gauss() * 10.0;
    }

    /* Benchmark Z[ζ₁₂] */
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int rep = 0; rep < 10; rep++) {
        zeta12_snap_batch(x, y, d_z12, N_POINTS);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double z12_ns = ((t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec)) / (N_POINTS * 10.0);

    /* Benchmark Eisenstein */
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int rep = 0; rep < 100; rep++) {
        eisenstein_snap_batch(x, y, d_eis, N_POINTS);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double eis_ns = ((t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec)) / (N_POINTS * 100.0);

    /* Statistics */
    double z12_max = 0, z12_mean = 0, eis_max = 0, eis_mean = 0;
    int z12_wins = 0, eis_wins = 0;
    for (int i = 0; i < N_POINTS; i++) {
        if (d_z12[i] > z12_max) z12_max = d_z12[i];
        if (d_eis[i] > eis_max) eis_max = d_eis[i];
        z12_mean += d_z12[i];
        eis_mean += d_eis[i];
        if (d_z12[i] < d_eis[i]) z12_wins++;
        else if (d_eis[i] < d_z12[i]) eis_wins++;
    }
    z12_mean /= N_POINTS;
    eis_mean /= N_POINTS;

    printf("╔════════════════════════════════════════════════════════════╗\n");
    printf("║  Z[ζ₁₂] vs Eisenstein Snap Benchmark (%d points)      ║\n", N_POINTS);
    printf("╚════════════════════════════════════════════════════════════╝\n\n");
    printf("  %-20s  %12s  %12s  %8s\n", "Metric", "Z[ζ₁₂]", "Eisenstein", "Ratio");
    printf("  %-20s  %12s  %12s  %12s\n", "────────────────────", "────────────", "────────────", "────────────");
    printf("  %-20s  %12.6f  %12.6f  %10.2f×\n", "Max (covering)", z12_max, eis_max, eis_max/z12_max);
    printf("  %-20s  %12.6f  %12.6f  %10.2f×\n", "Mean distance", z12_mean, eis_mean, eis_mean/z12_mean);
    printf("  %-20s  %12.1fns  %10.1fns  %10.2f×\n", "Time per snap", z12_ns, eis_ns, eis_ns/z12_ns);
    printf("  %-20s  %12d  %12d  (%d ties)\n\n", "Wins", z12_wins, eis_wins, N_POINTS - z12_wins - eis_wins);
    printf("  Z[ζ₁₂] is %.2f× tighter and %.1f× %s than Eisenstein\n",
           eis_max / z12_max,
           z12_ns > eis_ns ? z12_ns/eis_ns : eis_ns/z12_ns,
           z12_ns > eis_ns ? "slower" : "faster");
    printf("  Covering improvement: %.3f → %.3f\n", eis_max, z12_max);

    free(x); free(y); free(d_z12); free(d_eis);
    return 0;
}
