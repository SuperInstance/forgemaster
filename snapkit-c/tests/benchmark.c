/*
 * benchmark.c — Performance benchmarks for snapkit
 *
 * Measures:
 *   1. Single snap: 10M iterations, ns/op and Mops/sec
 *   2. Batch snap: 1M points throughput
 *   3. Naive vs Voronoi speed comparison
 *   4. Temporal snap: 1M timestamps
 *   5. Memory footprint: sizeof all structs
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>

#define SNAPKIT_IMPLEMENTATION
#include "snapkit.h"

/* ---- Simple RNG for reproducibility ---- */
static uint32_t rng_s[4];
static void rng_seed(uint64_t seed) {
    for (int i = 0; i < 4; i++) {
        seed ^= seed >> 12;
        seed *= 0x5DEECE66DULL;
        seed ^= seed >> 17;
        rng_s[i] = (uint32_t)(seed & 0xFFFFFFFF);
    }
}
static uint32_t rng_next(void) {
    uint32_t *s = rng_s;
    uint32_t result = s[0] + s[3];
    uint32_t t = s[1] << 9;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
    s[2] ^= t;
    s[3] = (s[3] << 11) | (s[3] >> 21);
    return result;
}
static double rng_double(double lo, double hi) {
    return lo + (hi - lo) * (rng_next() / 4294967296.0);
}

/* ---- Timer ---- */
static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ================================================================== */
/* Benchmark 1: Single Eisenstein snap                                */
/* ================================================================== */
static void bench_single_snap(void) {
    printf("\n=== Bench 1: Single Eisenstein Snap (10M ops) ===\n");
    rng_seed(0xBE11111);

    const int N = 10000000;
    volatile double sink = 0.0;  /* prevent optimization */

    /* Voronoi snap */
    {
        double t0 = now_sec();
        double sum = 0.0;
        for (int i = 0; i < N; i++) {
            double x = rng_double(-100.0, 100.0);
            double y = rng_double(-100.0, 100.0);
            sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);
            sum += e.a + e.b;
        }
        double elapsed = now_sec() - t0;
        sink += sum;
        printf("  Voronoi snap: %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
    }

    /* Naive snap */
    {
        rng_seed(0xBE11111);  /* reset for fair comparison */
        double t0 = now_sec();
        double sum = 0.0;
        for (int i = 0; i < N; i++) {
            double x = rng_double(-100.0, 100.0);
            double y = rng_double(-100.0, 100.0);
            sk_eisenstein e = sk_eisenstein_snap_naive(x, y);
            sum += e.a + e.b;
        }
        double elapsed = now_sec() - t0;
        sink += sum;
        printf("  Naive snap:   %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
    }

    /* Full snap with distance */
    {
        rng_seed(0xBE11111);
        double t0 = now_sec();
        double sum = 0.0;
        for (int i = 0; i < N; i++) {
            double x = rng_double(-100.0, 100.0);
            double y = rng_double(-100.0, 100.0);
            sk_snap_result r = sk_eisenstein_snap(x, y, 1.0);
            sum += r.distance;
        }
        double elapsed = now_sec() - t0;
        sink += sum;
        printf("  Full snap:    %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
    }

    (void)sink;
}

/* ================================================================== */
/* Benchmark 2: Batch snap                                            */
/* ================================================================== */
static void bench_batch_snap(void) {
    printf("\n=== Bench 2: Batch Snap (1M points) ===\n");
    rng_seed(0xBE22222);

    const int N = 1000000;
    double *x = malloc(N * sizeof(double));
    double *y = malloc(N * sizeof(double));
    sk_eisenstein *out = malloc(N * sizeof(sk_eisenstein));

    for (int i = 0; i < N; i++) {
        x[i] = rng_double(-1000.0, 1000.0);
        y[i] = rng_double(-1000.0, 1000.0);
    }

    /* Batch Voronoi */
    {
        double t0 = now_sec();
        sk_eisenstein_snap_batch(x, y, N, out);
        double elapsed = now_sec() - t0;
        printf("  Batch Voronoi: %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
    }

    /* Batch full */
    {
        sk_snap_result *fout = malloc(N * sizeof(sk_snap_result));
        double t0 = now_sec();
        sk_eisenstein_snap_batch_full(x, y, N, 1.0, fout);
        double elapsed = now_sec() - t0;
        printf("  Batch full:    %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
        free(fout);
    }

    free(x); free(y); free(out);
}

/* ================================================================== */
/* Benchmark 3: Naive vs Voronoi ratio                                */
/* ================================================================== */
static void bench_naive_vs_voronoi(void) {
    printf("\n=== Bench 3: Naive vs Voronoi Speed Ratio ===\n");
    rng_seed(0xBE33333);

    const int N = 5000000;

    double t_naive, t_voronoi;

    /* Voronoi */
    {
        rng_seed(0xBE33333);
        double t0 = now_sec();
        volatile int sink = 0;
        for (int i = 0; i < N; i++) {
            double x = rng_double(-50.0, 50.0);
            double y = rng_double(-50.0, 50.0);
            sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);
            sink += e.a;
        }
        t_voronoi = now_sec() - t0;
        (void)sink;
    }

    /* Naive */
    {
        rng_seed(0xBE33333);
        double t0 = now_sec();
        volatile int sink = 0;
        for (int i = 0; i < N; i++) {
            double x = rng_double(-50.0, 50.0);
            double y = rng_double(-50.0, 50.0);
            sk_eisenstein e = sk_eisenstein_snap_naive(x, y);
            sink += e.a;
        }
        t_naive = now_sec() - t0;
        (void)sink;
    }

    printf("  Voronoi: %.3f sec\n", t_voronoi);
    printf("  Naive:   %.3f sec\n", t_naive);
    printf("  Ratio (naive/voronoi): %.2fx\n", t_naive / t_voronoi);
    printf("  Voronoi is %s\n", t_voronoi < t_naive ? "FASTER" : "SLOWER");
}

/* ================================================================== */
/* Benchmark 4: Temporal snap                                         */
/* ================================================================== */
static void bench_temporal(void) {
    printf("\n=== Bench 4: Temporal Snap (1M ops) ===\n");
    rng_seed(0xBE44444);

    const int N = 1000000;
    sk_beat_grid grid;
    sk_beat_grid_init(&grid, 0.1, 0.0, 0.0);

    /* Single temporal snap */
    {
        double t0 = now_sec();
        double sum = 0.0;
        for (int i = 0; i < N; i++) {
            double ts = rng_double(0.0, 10000.0);
            sk_temporal_result r = sk_beat_grid_snap(&grid, ts, 0.005);
            sum += r.snapped_time;
        }
        double elapsed = now_sec() - t0;
        printf("  Single snap:    %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
        (void)sum;
    }

    /* Batch temporal snap */
    {
        double *ts = malloc(N * sizeof(double));
        sk_temporal_result *out = malloc(N * sizeof(sk_temporal_result));
        for (int i = 0; i < N; i++) ts[i] = rng_double(0.0, 10000.0);

        double t0 = now_sec();
        sk_beat_grid_snap_batch(&grid, ts, N, 0.005, out);
        double elapsed = now_sec() - t0;
        printf("  Batch snap:     %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);

        free(ts); free(out);
    }

    /* T0 observe */
    {
        sk_temporal_snap tsn;
        sk_temporal_snap_init(&tsn, &grid, 0.005, 0.5, 5);
        double t0 = now_sec();
        double sum = 0.0;
        for (int i = 0; i < N; i++) {
            double t = rng_double(0.0, 10000.0);
            double v = rng_double(-1.0, 1.0);
            sk_temporal_result r = sk_temporal_observe(&tsn, t, v);
            sum += r.snapped_time;
        }
        double elapsed = now_sec() - t0;
        printf("  T0 observe:     %.3f sec, %.1f ns/op, %.1f Mops/sec\n",
            elapsed, elapsed / N * 1e9, N / elapsed / 1e6);
        (void)sum;
    }
}

/* ================================================================== */
/* Benchmark 5: Memory footprint                                      */
/* ================================================================== */
static void bench_memory(void) {
    printf("\n=== Bench 5: Memory Footprint ===\n");
    printf("  sizeof(sk_eisenstein)    = %zu bytes\n", sizeof(sk_eisenstein));
    printf("  sizeof(sk_snap_result)   = %zu bytes\n", sizeof(sk_snap_result));
    printf("  sizeof(sk_beat_grid)     = %zu bytes\n", sizeof(sk_beat_grid));
    printf("  sizeof(sk_temporal_result)= %zu bytes\n", sizeof(sk_temporal_result));
    printf("  sizeof(sk_temporal_snap) = %zu bytes\n", sizeof(sk_temporal_snap));
    printf("  sizeof(sk_spectral_summary) = %zu bytes\n", sizeof(sk_spectral_summary));
}

/* ================================================================== */
/* Benchmark 6: Spectral analysis                                     */
/* ================================================================== */
static void bench_spectral(void) {
    printf("\n=== Bench 6: Spectral Analysis ===\n");
    rng_seed(0xBE66666);

    const int N = 10000;
    double data[N];
    for (int i = 0; i < N; i++) data[i] = rng_double(-1.0, 1.0);

    /* Entropy */
    {
        double t0 = now_sec();
        volatile double sink;
        for (int rep = 0; rep < 1000; rep++) {
            sink = sk_entropy(data, N, 32);
        }
        double elapsed = now_sec() - t0;
        printf("  Entropy (n=%d, 1K reps): %.3f sec, %.1f µs/call\n",
            N, elapsed, elapsed / 1000 * 1e6);
        (void)sink;
    }

    /* Hurst */
    {
        double t0 = now_sec();
        volatile double sink;
        for (int rep = 0; rep < 10; rep++) {
            sink = sk_hurst_exponent(data, N);
        }
        double elapsed = now_sec() - t0;
        printf("  Hurst (n=%d, 10 reps): %.3f sec, %.1f µs/call\n",
            N, elapsed, elapsed / 10 * 1e6);
        (void)sink;
    }

    /* Full spectral */
    {
        double acf_buf[501];
        int counts_buf[32];
        double t0 = now_sec();
        volatile sk_spectral_summary sink;
        for (int rep = 0; rep < 100; rep++) {
            sink = sk_spectral_analyze(data, N, 32, 500, acf_buf, counts_buf);
        }
        double elapsed = now_sec() - t0;
        printf("  Full spectral (n=%d, 100 reps): %.3f sec, %.1f µs/call\n",
            N, elapsed, elapsed / 100 * 1e6);
        (void)sink;
    }
}

/* ================================================================== */
/* Main                                                                */
/* ================================================================== */
int main(void) {
    printf("snapkit Performance Benchmarks\n");
    printf("==============================\n");

    bench_single_snap();
    bench_batch_snap();
    bench_naive_vs_voronoi();
    bench_temporal();
    bench_memory();
    bench_spectral();

    printf("\n==============================\n");
    printf("Benchmarks complete.\n");
    return 0;
}
