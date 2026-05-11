/*
 * examples/topology_compare.cu — Compare ADE topology performance
 *
 * Measures throughput for each ADE topology on random data.
 * Demonstrates that different topologies have different performance
 * characteristics depending on data dimension and kernel complexity.
 *
 * Usage: ./topology_compare [N]
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

double benchmark_topology(snapkit_topology_t topology, const char* name,
                          int N, int dim, cudaStream_t stream) {
    int num_runs = 3;

    /* Generate random points */
    float *h_pts = (float*)malloc(N * dim * sizeof(float));
    assert(h_pts);
    srand(42);
    for (int i = 0; i < N * dim; i++) {
        h_pts[i] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
    }

    float *d_in, *d_out, *d_delta;
    CUDA_SAFE_CALL(cudaMalloc(&d_in, N * dim * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_out, N * dim * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_in, h_pts, N * dim * sizeof(float),
                               cudaMemcpyHostToDevice));

    /* Warmup */
    snapkit_batch_topology_snap(d_in, dim, d_out, d_delta, N, topology, stream);
    CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

    /* Benchmark */
    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    double total_ms = 0.0;
    for (int run = 0; run < num_runs; run++) {
        CUDA_SAFE_CALL(cudaEventRecord(start, stream));
        snapkit_batch_topology_snap(d_in, dim, d_out, d_delta, N, topology, stream);
        CUDA_SAFE_CALL(cudaEventRecord(stop, stream));
        CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

        float ms;
        CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));
        total_ms += ms;
    }

    double avg_ms = total_ms / num_runs;

    free(h_pts);
    CUDA_SAFE_CALL(cudaFree(d_in));
    CUDA_SAFE_CALL(cudaFree(d_out));
    CUDA_SAFE_CALL(cudaFree(d_delta));
    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    return avg_ms;
}

int main(int argc, char** argv) {
    int N = 1000000;  /* 1M points default */
    if (argc > 1) N = atoi(argv[1]);

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  ADE Topology Performance Comparison        ║\n");
    printf("║  %d points per topology                    ║\n", N);
    printf("╚══════════════════════════════════════════════╝\n\n");

    cudaStream_t stream;
    CUDA_SAFE_CALL(cudaStreamCreate(&stream));

    /* Topologies to benchmark */
    struct {
        snapkit_topology_t topo;
        const char* name;
        int dim;
    } tests[] = {
        {SNAPKIT_ADE_A1,  "A₁ (binary)",     1},
        {SNAPKIT_ADE_A2,  "A₂ (Eisenstein)", 2},
        {SNAPKIT_ADE_A3,  "A₃ (tetrahedral)",3},
        {SNAPKIT_ADE_D4,  "D₄ (triality)",   4},
        {SNAPKIT_ADE_E8,  "E₈ (icosahedral)",8},
    };

    int num_tests = sizeof(tests) / sizeof(tests[0]);

    printf("Topology        | Dim | Time (ms) | Mpts/sec\n");
    printf("----------------+-----+-----------+---------\n");

    double a2_time = 0.0;
    for (int i = 0; i < num_tests; i++) {
        double ms = benchmark_topology(tests[i].topo, tests[i].name,
                                       N, tests[i].dim, stream);
        double mpts = (double)N / (ms / 1000.0) / 1e6;

        printf("%-15s | %3d | %9.2f | %7.2f\n",
               tests[i].name, tests[i].dim, ms, mpts);

        if (tests[i].topo == SNAPKIT_ADE_A2) {
            a2_time = ms;
        }
    }

    printf("\n─── Relative Performance ───\n");
    printf("  A₂ baseline:  %.2f ms (%d pts)\n", a2_time, N);
    for (int i = 0; i < num_tests; i++) {
        double ms = benchmark_topology(tests[i].topo, tests[i].name,
                                       N, tests[i].dim, stream);
        double speedup = a2_time / ms;
        printf("  %-15s: %.2f ms (%.2f× vs A₂)\n",
               tests[i].name, ms, speedup);
    }

    CUDA_SAFE_CALL(cudaStreamDestroy(stream));
    printf("\nDone.\n");
    return 0;
}
