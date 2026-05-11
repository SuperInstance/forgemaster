/*
 * benches/bench_comparison.cu — CPU vs GPU comparison
 *
 * Measures wall-clock time for Eisenstein snap on CPU vs GPU.
 * Demonstrates GPU acceleration factor for different batch sizes.
 *
 * Usage: ./bench_comparison [N]
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <ctime>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* CPU reference benchmark (single-threaded) */
double cpu_benchmark(int N) {
    float *x = (float*)malloc(N * sizeof(float));
    float *y = (float*)malloc(N * sizeof(float));
    float *delta = (float*)malloc(N * sizeof(float));
    int *a = (int*)malloc(N * sizeof(int));
    int *b = (int*)malloc(N * sizeof(int));
    assert(x && y && delta && a && b);

    srand(42);
    for (int i = 0; i < N; i++) {
        x[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
        y[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
    }

    const float sqrt3 = 1.7320508075688772f;

    clock_t start = clock();
    for (int i = 0; i < N; i++) {
        b[i] = (int)roundf(y[i] * 2.0f / sqrt3);
        a[i] = (int)roundf(x[i] + b[i] * 0.5f);
        float sx = a[i] - b[i] * 0.5f;
        float sy = b[i] * sqrt3 * 0.5f;
        float dx = x[i] - sx;
        float dy = y[i] - sy;
        delta[i] = sqrtf(dx * dx + dy * dy);
    }
    clock_t end = clock();

    double ms = (double)(end - start) / CLOCKS_PER_SEC * 1000.0;

    free(x); free(y); free(delta); free(a); free(b);
    return ms;
}

double gpu_benchmark(int N, cudaStream_t stream) {
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

    /* Include copy time to reflect real-world comparison */
    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    CUDA_SAFE_CALL(cudaEventRecord(start, stream));
    snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, stream);
    CUDA_SAFE_CALL(cudaEventRecord(stop, stream));
    CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

    float ms;
    CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));

    free(h_x); free(h_y);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));
    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    return ms;
}

int main(int argc, char** argv) {
    int N = 1000000;  /* 1M default */
    if (argc > 1) N = atoi(argv[1]);

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  CPU vs GPU Performance Comparison           ║\n");
    printf("╚══════════════════════════════════════════════╝\n\n");

    int device;
    CUDA_SAFE_CALL(cudaGetDevice(&device));
    cudaDeviceProp prop;
    CUDA_SAFE_CALL(cudaGetDeviceProperties(&prop, device));

    printf("Device: %s (sm_%d%d)\n\n", prop.name, prop.major, prop.minor);
    printf("Benchmarking %d points (kernel time only)...\n\n", N);

    /* CPU benchmark */
    printf("Running CPU benchmark (single-threaded)...\n");
    double cpu_ms = cpu_benchmark(N);
    printf("  CPU time: %.2f ms\n", cpu_ms);

    /* GPU benchmark */
    printf("Running GPU benchmark...\n");
    cudaStream_t stream;
    CUDA_SAFE_CALL(cudaStreamCreate(&stream));

    const int NUM_RUNS = 5;
    double gpu_min = 1e10, gpu_avg = 0;
    for (int run = 0; run < NUM_RUNS; run++) {
        double ms = gpu_benchmark(N, stream);
        gpu_avg += ms;
        if (ms < gpu_min) gpu_min = ms;
    }
    gpu_avg /= NUM_RUNS;

    printf("  GPU avg time: %.2f ms\n", gpu_avg);
    printf("  GPU min time: %.2f ms\n", gpu_min);

    double cpu_throughput = (double)N / (cpu_ms / 1000.0) / 1e6;
    double gpu_throughput = (double)N / (gpu_avg / 1000.0) / 1e6;
    double speedup = cpu_ms / gpu_min;

    printf("\n─── Results ───\n");
    printf("  CPU throughput:  %.2f M pts/sec\n", cpu_throughput);
    printf("  GPU throughput:  %.2f M pts/sec (%s kern)\n", gpu_throughput,
           prop.name);
    printf("  Speedup (GPU/CPU): %.1f×\n", speedup);
    printf("  Efficiency:       %.1f%% (vs %d SMs)\n",
           gpu_throughput / (prop.multiProcessorCount * 256.0) * 100.0,
           prop.multiProcessorCount);

    CUDA_SAFE_CALL(cudaStreamDestroy(stream));
    printf("\nDone.\n");
    return 0;
}
