#define _POSIX_C_SOURCE 199309L
#include "eisenstein_bridge.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>

/* ── Timing helpers ── */

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}

/* ── Simple xorshift64 PRNG ── */

static uint64_t rng_state = 123456789012345ULL;

static float rand_float(float lo, float hi) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    /* Map to [0, 1) */
    double d = (double)(rng_state >> 11) / (double)(1ULL << 53);
    return (float)(lo + d * (hi - lo));
}

/* ── Benchmarks ── */

#define N_POINTS 1000000
#define BATCH_SIZE 1000
#define N_HOLONOMY (N_POINTS / 4)

int main(void) {
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  fleet-math-c Eisenstein Bridge Benchmark\n");
    printf("  %d points | batch size %d | %d holonomy cycles\n",
           N_POINTS, BATCH_SIZE, N_HOLONOMY);
    printf("═══════════════════════════════════════════════════════════════\n\n");

    /* Allocate arrays */
    float *points = (float *)malloc(2 * N_POINTS * sizeof(float));
    eisenstein_result_t *results = (eisenstein_result_t *)malloc(N_POINTS * sizeof(eisenstein_result_t));

    if (!points || !results) {
        fprintf(stderr, "Allocation failed\n");
        return 1;
    }

    /* Generate random points in [-5, 5] × [-5, 5] */
    printf("Generating %d random points in [-5, 5] × [-5, 5]...\n", N_POINTS);
    for (int i = 0; i < N_POINTS; i++) {
        points[2*i]     = rand_float(-5.0f, 5.0f);
        points[2*i + 1] = rand_float(-5.0f, 5.0f);
    }
    printf("Done.\n\n");

    /* ── Benchmark 1: Single snap ── */
    printf("── Benchmark 1: Single eisenstein_snap() ──\n");
    {
        /* Warm up */
        for (int i = 0; i < 1000; i++) {
            eisenstein_snap(points[2*i], points[2*i+1]);
        }

        double t0 = now_ns();
        for (int i = 0; i < N_POINTS; i++) {
            results[i] = eisenstein_snap(points[2*i], points[2*i+1]);
        }
        double t1 = now_ns();

        double elapsed_ns = t1 - t0;
        double ns_per_op = elapsed_ns / N_POINTS;
        double ops_per_sec = 1e9 / ns_per_op;

        printf("  Total: %.2f ms for %d snaps\n", elapsed_ns / 1e6, N_POINTS);
        printf("  Avg:   %.1f ns/op\n", ns_per_op);
        printf("  Rate:  %.2f M ops/sec\n", ops_per_sec / 1e6);
    }
    printf("\n");

    /* ── Verify some results ── */
    printf("── Spot check (first 5 results) ──\n");
    for (int i = 0; i < 5; i++) {
        printf("  [%d] (%.3f, %.3f) → error=%.6f dodecet=0x%03X chamber=%d flags=0x%02X%s\n",
               i, points[2*i], points[2*i+1],
               results[i].error, results[i].dodecet,
               results[i].chamber, results[i].flags,
               (results[i].flags & EISENSTEIN_FLAG_SAFE) ? " SAFE" : "");
    }
    printf("\n");

    /* ── Benchmark 2: Batch snap ── */
    printf("── Benchmark 2: eisenstein_batch_snap() [%d at a time] ──\n", BATCH_SIZE);
    {
        /* Warm up */
        eisenstein_batch_snap(points, 1000, results);

        double t0 = now_ns();
        for (int offset = 0; offset < N_POINTS; offset += BATCH_SIZE) {
            int count = BATCH_SIZE;
            if (offset + count > N_POINTS) count = N_POINTS - offset;
            eisenstein_batch_snap(&points[2 * offset], count, &results[offset]);
        }
        double t1 = now_ns();

        double elapsed_ns = t1 - t0;
        double ns_per_op = elapsed_ns / N_POINTS;
        double ops_per_sec = 1e9 / ns_per_op;

        printf("  Total: %.2f ms for %d snaps (%d batches)\n",
               elapsed_ns / 1e6, N_POINTS, N_POINTS / BATCH_SIZE);
        printf("  Avg:   %.1f ns/op (batch overhead included)\n", ns_per_op);
        printf("  Rate:  %.2f M ops/sec\n", ops_per_sec / 1e6);
    }
    printf("\n");

    /* ── Benchmark 3: Holonomy 4-cycle ── */
    printf("── Benchmark 3: eisenstein_holonomy_4cycle() [%d cycles] ──\n", N_HOLONOMY);
    {
        float *holonomy = (float *)malloc(N_HOLONOMY * sizeof(float));
        if (!holonomy) {
            fprintf(stderr, "Allocation failed for holonomy\n");
            return 1;
        }

        /* Warm up */
        for (int i = 0; i < 100; i++) {
            eisenstein_holonomy_4cycle(&results[4 * i]);
        }

        double t0 = now_ns();
        for (int i = 0; i < N_HOLONOMY; i++) {
            holonomy[i] = eisenstein_holonomy_4cycle(&results[4 * i]);
        }
        double t1 = now_ns();

        double elapsed_ns = t1 - t0;
        double ns_per_op = elapsed_ns / N_HOLONOMY;
        double ops_per_sec = 1e9 / ns_per_op;

        printf("  Total: %.2f ms for %d 4-cycles\n", elapsed_ns / 1e6, N_HOLONOMY);
        printf("  Avg:   %.1f ns/op\n", ns_per_op);
        printf("  Rate:  %.2f M ops/sec\n", ops_per_sec / 1e6);

        /* Stats */
        double sum = 0, max_h = 0;
        int consistent = 0;
        for (int i = 0; i < N_HOLONOMY; i++) {
            sum += holonomy[i];
            if (holonomy[i] > max_h) max_h = holonomy[i];
            if (holonomy[i] < 0.1) consistent++;
        }
        printf("  Avg holonomy: %.6f\n", sum / N_HOLONOMY);
        printf("  Max holonomy: %.6f\n", max_h);
        printf("  Consistent (< 0.1): %d / %d (%.1f%%)\n",
               consistent, N_HOLONOMY, 100.0 * consistent / N_HOLONOMY);

        free(holonomy);
    }
    printf("\n");

    /* ── Benchmark 4: Batch holonomy ── */
    printf("── Benchmark 4: eisenstein_batch_holonomy() [%d cycles] ──\n", N_HOLONOMY);
    {
        float *holonomy = (float *)malloc(N_HOLONOMY * sizeof(float));
        if (!holonomy) {
            fprintf(stderr, "Allocation failed\n");
            return 1;
        }

        /* Warm up */
        eisenstein_batch_holonomy(results, 100, holonomy);

        double t0 = now_ns();
        eisenstein_batch_holonomy(results, N_HOLONOMY, holonomy);
        double t1 = now_ns();

        double elapsed_ns = t1 - t0;
        double ns_per_op = elapsed_ns / N_HOLONOMY;
        double ops_per_sec = 1e9 / ns_per_op;

        printf("  Total: %.2f ms for %d 4-cycles\n", elapsed_ns / 1e6, N_HOLONOMY);
        printf("  Avg:   %.1f ns/op\n", ns_per_op);
        printf("  Rate:  %.2f M ops/sec\n", ops_per_sec / 1e6);

        free(holonomy);
    }
    printf("\n");

    /* ── Benchmark 5: Full pipeline (snap + holonomy) ── */
    printf("── Benchmark 5: Full pipeline (snap + holonomy) ──\n");
    {
        int pipeline_n = 100000;
        float *holonomy = (float *)malloc((pipeline_n / 4) * sizeof(float));
        eisenstein_result_t *pipe_results = (eisenstein_result_t *)malloc(pipeline_n * sizeof(eisenstein_result_t));

        double t0 = now_ns();
        eisenstein_batch_snap(points, pipeline_n, pipe_results);
        eisenstein_batch_holonomy(pipe_results, pipeline_n / 4, holonomy);
        double t1 = now_ns();

        double elapsed_ns = t1 - t0;
        printf("  Total: %.2f ms for %d snaps + %d holonomy checks\n",
               elapsed_ns / 1e6, pipeline_n, pipeline_n / 4);
        printf("  Avg per point: %.1f ns (snap + check)\n", elapsed_ns / pipeline_n);

        free(holonomy);
        free(pipe_results);
    }
    printf("\n");

    /* ── Summary ── */
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  Benchmark complete.\n");
    printf("═══════════════════════════════════════════════════════════════\n");

    /* Cleanup */
    free(points);
    free(results);

    return 0;
}
