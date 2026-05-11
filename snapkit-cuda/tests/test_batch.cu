/*
 * test_batch.cu — Batch snap and multi-stream tests
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

void cpu_eisenstein_snap(float x, float y, int* a, int* b, float* delta) {
    const float sqrt3 = 1.7320508075688772f;
    float b_f = y * (2.0f / sqrt3);
    *b = (int)roundf(b_f);
    float a_f = x + *b * 0.5f;
    *a = (int)roundf(a_f);
    float snap_x = *a - *b * 0.5f;
    float snap_y = *b * sqrt3 * 0.5f;
    float dx = x - snap_x;
    float dy = y - snap_y;
    *delta = sqrtf(dx * dx + dy * dy);
}

int test_multi_stream() {
    printf("  Multi-stream batch snap...\n");

    const int N = 100000;
    const int NUM_STREAMS = 4;

    /* Generate data */
    float *h_x = (float*)malloc(N * sizeof(float));
    float *h_y = (float*)malloc(N * sizeof(float));
    int   *h_sid = (int*)malloc(N * sizeof(int));
    assert(h_x && h_y && h_sid);

    srand(42);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 50.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 50.0f;
        h_sid[i] = rand() % NUM_STREAMS;
    }

    /* GPU memory */
    float *d_x, *d_y, *d_delta;
    int *d_a, *d_b, *d_sid, *d_is_delta, *d_counts;
    float *d_tols;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_sid, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_is_delta, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_counts, NUM_STREAMS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_tols, NUM_STREAMS * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_sid, h_sid, N * sizeof(int), cudaMemcpyHostToDevice));

    /* Set stream tolerances */
    float host_tols[NUM_STREAMS] = {0.05f, 0.1f, 0.5f, 1.0f};
    CUDA_SAFE_CALL(cudaMemcpy(d_tols, host_tols, NUM_STREAMS * sizeof(float),
                               cudaMemcpyHostToDevice));

    /* Run batch snap with per-stream tolerances */
    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    /* Launch multi-stream batch snap kernel */
    {
        extern __shared__ char _[];
        extern __host__ void batch_snap_with_tolerances_kernel(
            const float*, const float*, const int*,
            int*, int*, float*, int*, int);
    }

    /* Use the direct API */
    snapkit_batch_snap_multi_stream(
        d_x, d_y, d_sid, d_a, d_b, d_delta, d_is_delta, N, 0
    );
    CUDA_SAFE_CALL(cudaDeviceSynchronize());

    /* Verify against CPU */
    int *gpu_a = (int*)malloc(N * sizeof(int));
    int *gpu_b = (int*)malloc(N * sizeof(int));
    float *gpu_delta = (float*)malloc(N * sizeof(float));
    int *gpu_is_delta = (int*)malloc(N * sizeof(int));
    assert(gpu_a && gpu_b && gpu_delta && gpu_is_delta);

    CUDA_SAFE_CALL(cudaMemcpy(gpu_a, d_a, N * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(gpu_b, d_b, N * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(gpu_delta, d_delta, N * sizeof(float), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(gpu_is_delta, d_is_delta, N * sizeof(int), cudaMemcpyDeviceToHost));

    int errors = 0;
    int stream_counts[NUM_STREAMS] = {0};
    int stream_deltas[NUM_STREAMS] = {0};
    float stream_errors[NUM_STREAMS] = {0.0f};

    for (int i = 0; i < N; i++) {
        int cpu_a, cpu_b;
        float cpu_delta;
        cpu_eisenstein_snap(h_x[i], h_y[i], &cpu_a, &cpu_b, &cpu_delta);

        if (gpu_a[i] != cpu_a || gpu_b[i] != cpu_b) {
            if (errors < 5) {
                printf("    MISMATCH [%d]: GPU=(%d,%d) CPU=(%d,%d)\n",
                       i, gpu_a[i], gpu_b[i], cpu_a, cpu_b);
            }
            errors++;
        }

        /* Check delta threshold */
        stream_counts[h_sid[i]]++;
        int expected_delta = (gpu_delta[i] > host_tols[h_sid[i]]) ? 1 : 0;
        if (gpu_is_delta[i] != expected_delta) {
            stream_errors[h_sid[i]]++;
        }
        if (gpu_is_delta[i]) stream_deltas[h_sid[i]]++;
    }

    printf("    Snap errors: %d\n", errors);
    for (int s = 0; s < NUM_STREAMS; s++) {
        printf("    Stream %d: %d points, %d deltas (tol=%.2f), threshold errors: %.0f\n",
               s, stream_counts[s], stream_deltas[s],
               host_tols[s], stream_errors[s]);
    }

    int has_errors = (errors > 0);
    for (int s = 0; s < NUM_STREAMS; s++) {
        if (stream_errors[s] > 0) has_errors = 1;
    }

    free(h_x); free(h_y); free(h_sid);
    free(gpu_a); free(gpu_b); free(gpu_delta); free(gpu_is_delta);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta)); CUDA_SAFE_CALL(cudaFree(d_sid));
    CUDA_SAFE_CALL(cudaFree(d_is_delta));
    CUDA_SAFE_CALL(cudaFree(d_counts)); CUDA_SAFE_CALL(cudaFree(d_tols));

    printf("    %s\n", has_errors ? "FAILED" : "PASSED");
    return has_errors;
}

int test_grid_stride() {
    printf("  Grid-stride batch (large N)...\n");

    const int N = 5000000;  /* 5M points */

    float *h_x = (float*)malloc(N * sizeof(float));
    float *h_y = (float*)malloc(N * sizeof(float));
    assert(h_x && h_y);

    srand(99);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 20.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 20.0f;
    }

    float *d_x, *d_y, *d_delta;
    int *d_a, *d_b;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));

    /* Time the execution */
    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    CUDA_SAFE_CALL(cudaEventRecord(start));
    snapkit_batch_snap_grid_stride(d_x, d_y, d_a, d_b, d_delta, N, 0);
    CUDA_SAFE_CALL(cudaEventRecord(stop));
    CUDA_SAFE_CALL(cudaEventSynchronize(stop));

    float ms;
    CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));

    double pts_per_sec = (double)N / (ms / 1000.0);
    printf("    5M points: %.2f ms = %.2f M pts/sec\n", ms, pts_per_sec / 1e6);

    /* Verify first few */
    int *gpu_a = (int*)malloc(100 * sizeof(int));
    CUDA_SAFE_CALL(cudaMemcpy(gpu_a, d_a, 100 * sizeof(int), cudaMemcpyDeviceToHost));
    for (int i = 0; i < 100; i++) {
        int cpu_a, cpu_b;
        float cpu_delta;
        cpu_eisenstein_snap(h_x[i], h_y[i], &cpu_a, &cpu_b, &cpu_delta);
        if (gpu_a[i] != cpu_a) {
            printf("    FAIL: point %d: GPU=%d CPU=%d\n", i, gpu_a[i], cpu_a);
            free(h_x); free(h_y); free(gpu_a);
            CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
            CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
            CUDA_SAFE_CALL(cudaFree(d_delta));
            return 1;
        }
    }

    free(h_x); free(h_y); free(gpu_a);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));
    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    printf("    PASSED\n");
    return 0;
}

int main() {
    printf("\n=== Batch Snap Tests ===\n\n");

    int failures = 0;
    failures += test_multi_stream();
    failures += test_grid_stride();

    printf("\n=== Results: %s ===\n\n",
           failures == 0 ? "ALL PASSED" : "SOME FAILED");
    return failures;
}
