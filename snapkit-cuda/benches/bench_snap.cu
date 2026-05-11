/*
 * benches/bench_snap.cu — Snap throughput benchmark
 *
 * Comprehensive throughput benchmark for Eisenstein batch snap.
 * Tests scaling behavior across multiple batch sizes.
 * Reports Gpts/sec (billions of points per second).
 *
 * Usage: ./bench_snap [--quick]
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

double bench_size(int N, cudaStream_t stream) {
    const int NUM_ITERS = 5;

    float *h_x = (float*)malloc(N * sizeof(float));
    float *h_y = (float*)malloc(N * sizeof(float));
    assert(h_x && h_y);
    srand(42);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
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

    /* Warmup */
    for (int i = 0; i < 3; i++) {
        snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, stream);
    }
    CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

    /* Benchmark */
    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    double total_ms = 0.0;
    for (int i = 0; i < NUM_ITERS; i++) {
        CUDA_SAFE_CALL(cudaEventRecord(start, stream));
        snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, stream);
        CUDA_SAFE_CALL(cudaEventRecord(stop, stream));
        CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

        float ms;
        CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));
        total_ms += ms;
    }

    double avg_ms = total_ms / NUM_ITERS;

    free(h_x); free(h_y);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));
    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    return avg_ms;
}

int main(int argc, char** argv) {
    int quick = (argc > 1 && strcmp(argv[1], "--quick") == 0);

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  Snap Throughput Benchmark                   ║\n");
    printf("╚══════════════════════════════════════════════╝\n\n");

    int device;
    CUDA_SAFE_CALL(cudaGetDevice(&device));
    cudaDeviceProp prop;
    CUDA_SAFE_CALL(cudaGetDeviceProperties(&prop, device));
    printf("Device: %s (sm_%d%d)\n", prop.name, prop.major, prop.minor);
    printf("SMs: %d, Warp: %d\n\n", prop.multiProcessorCount, prop.warpSize);

    cudaStream_t stream;
    CUDA_SAFE_CALL(cudaStreamCreate(&stream));

    /* Batch sizes */
    int sizes[] = {1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 50000000};
    int num_sizes = sizeof(sizes) / sizeof(sizes[0]);
    if (quick) num_sizes = 5;  /* Skip largest in quick mode */

    printf("Batch Size   | Time (ms)  | Throughput   | Efficiency\n");
    printf("-------------+------------+--------------+-----------\n");

    for (int i = 0; i < num_sizes; i++) {
        int N = sizes[i];
        double ms = bench_size(N, stream);
        double pts_per_sec = (double)N / (ms / 1000.0);
        double gpts = pts_per_sec / 1e9;
        double efficiency = pts_per_sec / (prop.multiProcessorCount * 256);

        printf("%11d | %10.4f | %8.3f G/s | %9.0f\n",
               N, ms, gpts, efficiency);
    }

    CUDA_SAFE_CALL(cudaStreamDestroy(stream));
    printf("\nDone.\n");
    return 0;
}
