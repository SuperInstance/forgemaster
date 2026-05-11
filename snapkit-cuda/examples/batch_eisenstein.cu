/*
 * examples/batch_eisenstein.cu — Snap 100M points on GPU
 *
 * Demonstrates the core batch Eisenstein snap at scale.
 * Measures throughput in billions of points per second.
 *
 * Usage: ./batch_eisenstein [N]
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

int main(int argc, char** argv) {
    int N = 100000000;  /* 100M points default */
    if (argc > 1) N = atoi(argv[1]);
    if (N <= 0 || N > SNAPKIT_MAX_BATCH_SIZE) {
        fprintf(stderr, "N must be 1-%d\n", SNAPKIT_MAX_BATCH_SIZE);
        return 1;
    }

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  Batch Eisenstein Snap                      ║\n");
    printf("║  %d points                               ║\n", N);
    printf("╚══════════════════════════════════════════════╝\n\n");

    /* Allocate host memory */
    float *h_x = (float*)malloc(N * sizeof(float));
    float *h_y = (float*)malloc(N * sizeof(float));
    assert(h_x && h_y);

    /* Generate random points */
    printf("Generating %d random points...\n", N);
    srand(42);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
    }

    /* Allocate device memory */
    float *d_x, *d_y, *d_delta;
    int *d_a, *d_b;

    printf("Allocating device memory...\n");
    CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

    /* Copy to device */
    printf("Copying to GPU...\n");
    CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));

    /* Warmup run */
    printf("Warmup...\n");
    snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, 0);
    CUDA_SAFE_CALL(cudaDeviceSynchronize());

    /* Benchmark runs */
    const int NUM_RUNS = 5;
    float min_ms = 1e10f, max_ms = 0.0f, avg_ms = 0.0f;

    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    printf("\nRunning %d benchmark iterations...\n", NUM_RUNS);
    for (int run = 0; run < NUM_RUNS; run++) {
        CUDA_SAFE_CALL(cudaEventRecord(start));
        snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, 0);
        CUDA_SAFE_CALL(cudaEventRecord(stop));
        CUDA_SAFE_CALL(cudaEventSynchronize(stop));

        float ms;
        CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));

        if (ms < min_ms) min_ms = ms;
        if (ms > max_ms) max_ms = ms;
        avg_ms += ms;

        double gpts = (double)N / (ms / 1000.0) / 1e9;
        printf("  Run %d: %.2f ms = %.3f Gpts/sec\n", run + 1, ms, gpts);
    }

    avg_ms /= NUM_RUNS;
    double avg_gpts = (double)N / (avg_ms / 1000.0) / 1e9;
    double peak_gpts = (double)N / (min_ms / 1000.0) / 1e9;

    printf("\n─── Results ───\n");
    printf("  Points:     %d\n", N);
    printf("  Min time:   %.2f ms\n", min_ms);
    printf("  Max time:   %.2f ms\n", max_ms);
    printf("  Avg time:   %.2f ms\n", avg_ms);
    printf("  Avg throughput: %.3f Gpts/sec (%.1f B snaps/sec)\n",
           avg_gpts, avg_gpts);
    printf("  Peak throughput: %.3f Gpts/sec (%.1f B snaps/sec)\n",
           peak_gpts, peak_gpts);

    /* Verify first few results */
    {
        int *h_a = (int*)malloc(10 * sizeof(int));
        int *h_b = (int*)malloc(10 * sizeof(int));
        float *h_delta = (float*)malloc(10 * sizeof(float));
        assert(h_a && h_b && h_delta);

        CUDA_SAFE_CALL(cudaMemcpy(h_a, d_a, 10 * sizeof(int), cudaMemcpyDeviceToHost));
        CUDA_SAFE_CALL(cudaMemcpy(h_b, d_b, 10 * sizeof(int), cudaMemcpyDeviceToHost));
        CUDA_SAFE_CALL(cudaMemcpy(h_delta, d_delta, 10 * sizeof(float), cudaMemcpyDeviceToHost));

        printf("\n  First 10 results:\n");
        printf("    [idx]  (x, y) → (a, b)  delta\n");
        for (int i = 0; i < 10; i++) {
            printf("    [%4d] (%.3f, %.3f) → (%d, %d)  %.6f\n",
                   i, h_x[i], h_y[i], h_a[i], h_b[i], h_delta[i]);
        }

        free(h_a); free(h_b); free(h_delta);
    }

    /* Cleanup */
    free(h_x); free(h_y);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));
    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    printf("\nDone.\n");
    return 0;
}
