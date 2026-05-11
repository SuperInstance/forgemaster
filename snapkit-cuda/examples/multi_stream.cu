/*
 * examples/multi_stream.cu — Multi-stream attention budget on GPU
 *
 * Demonstrates the full attention pipeline:
 * - 16 streams with independent tolerance and priority
 * - Per-stream delta detection and attention weighting
 * - Top-K delta ranking across all streams
 * - Attention budget allocation based on delta severity
 *
 * Usage: ./multi_stream [num_streams] [points_per_stream]
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

int main(int argc, char** argv) {
    int NUM_STREAMS = 16;
    int POINTS_PER_STREAM = 100000;
    if (argc > 1) NUM_STREAMS = atoi(argv[1]);
    if (argc > 2) POINTS_PER_STREAM = atoi(argv[2]);

    if (NUM_STREAMS > SNAPKIT_MAX_STREAMS) {
        fprintf(stderr, "Max %d streams\n", SNAPKIT_MAX_STREAMS);
        return 1;
    }

    int TOTAL_POINTS = NUM_STREAMS * POINTS_PER_STREAM;

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  Multi-Stream Attention Budget              ║\n");
    printf("║  %d streams × %d points = %d total         ║\n",
           NUM_STREAMS, POINTS_PER_STREAM, TOTAL_POINTS);
    printf("╚══════════════════════════════════════════════╝\n\n");

    /* Create config and configure streams */
    snapkit_config_t config;
    snapkit_create_default_config(&config);
    config.topology = SNAPKIT_ADE_A2;
    config.top_k_deltas = 16;
    config.total_attention_budget = 1000.0f;
    config.allocation_strategy = SNAPKIT_ALLOC_ACTION;

    srand(456);
    for (int s = 0; s < NUM_STREAMS; s++) {
        float tol = 0.01f + ((float)rand() / RAND_MAX) * 1.0f;
        float pri = 0.1f + ((float)rand() / RAND_MAX) * 0.9f;
        snapkit_configure_stream(&config, s, SNAPKIT_ADE_A2, tol, pri);
    }

    /* Generate data */
    float *h_x = (float*)malloc(TOTAL_POINTS * sizeof(float));
    float *h_y = (float*)malloc(TOTAL_POINTS * sizeof(float));
    int   *h_sid = (int*)malloc(TOTAL_POINTS * sizeof(int));
    float *h_action = (float*)malloc(TOTAL_POINTS * sizeof(float));
    float *h_urgent = (float*)malloc(TOTAL_POINTS * sizeof(float));
    assert(h_x && h_y && h_sid && h_action && h_urgent);

    for (int s = 0; s < NUM_STREAMS; s++) {
        float center_x = ((float)rand() / RAND_MAX - 0.5f) * 20.0f;
        float center_y = ((float)rand() / RAND_MAX - 0.5f) * 20.0f;
        float spread = 0.1f + ((float)rand() / RAND_MAX) * 5.0f;
        float action = 0.3f + ((float)rand() / RAND_MAX) * 0.7f;
        float urgency = 0.3f + ((float)rand() / RAND_MAX) * 0.7f;

        for (int p = 0; p < POINTS_PER_STREAM; p++) {
            int idx = s * POINTS_PER_STREAM + p;
            h_x[idx] = center_x + ((float)rand() / RAND_MAX - 0.5f) * 2 * spread;
            h_y[idx] = center_y + ((float)rand() / RAND_MAX - 0.5f) * 2 * spread;
            h_sid[idx] = s;
            h_action[idx] = action;
            h_urgent[idx] = urgency;
        }
    }

    /* Run pipeline */
    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    printf("Running attention pipeline...\n");

    /* Use all-at-once pipeline API */
    float *d_x, *d_y;
    int   *d_sid;
    float *d_action, *d_urgent;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_sid, TOTAL_POINTS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_action, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_urgent, TOTAL_POINTS * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, TOTAL_POINTS * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, TOTAL_POINTS * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_sid, h_sid, TOTAL_POINTS * sizeof(int),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_action, h_action, TOTAL_POINTS * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_urgent, h_urgent, TOTAL_POINTS * sizeof(float),
                               cudaMemcpyHostToDevice));

    snapkit_attention_t results[16];
    CUDA_SAFE_CALL(cudaEventRecord(start));

    int actual_k = snapkit_pipeline(
        &config, d_x, d_y, h_sid,
        d_action, d_urgent, results, TOTAL_POINTS, 0
    );

    CUDA_SAFE_CALL(cudaEventRecord(stop));
    CUDA_SAFE_CALL(cudaEventSynchronize(stop));

    float ms;
    CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));

    /* Print stream configs */
    printf("\n─── Stream Configurations ───\n");
    printf("  Stream | Tolerance | Priority\n");
    printf("  -------+-----------+---------\n");
    for (int s = 0; s < NUM_STREAMS; s++) {
        printf("  %6d |     %.3f |    %.2f\n",
               s,
               config.stream_configs[s].tolerance,
               config.stream_configs[s].priority_weight);
    }

    /* Print attention allocation */
    printf("\n─── Attention Budget Allocation ───\n");
    printf("  Pipeline time: %.2f ms\n", ms);
    printf("  Throughput:    %.2f M pts/sec\n",
           (double)TOTAL_POINTS / (ms / 1000.0) / 1e6);
    printf("  Budget:        %.1f\n", config.total_attention_budget);
    printf("  Top-K found:   %d\n", actual_k);

    printf("\n  Rank | Point   | Stream | Delta   | Attention\n");
    printf("  -----+---------+--------+---------+----------\n");
    for (int i = 0; i < actual_k && i < 16; i++) {
        printf("  %4d | %7d | %6d | %.4f |     %.2f\n",
               results[i].rank, results[i].point_idx,
               h_sid[results[i].point_idx],
               results[i].delta, results[i].attention);
    }

    /* Calculate budget distribution */
    if (config.total_attention_budget > 0) {
        float *stream_budget = (float*)calloc(NUM_STREAMS, sizeof(float));
        int *stream_count = (int*)calloc(NUM_STREAMS, sizeof(int));

        for (int i = 0; i < actual_k; i++) {
            int sid = h_sid[results[i].point_idx];
            float alloc = config.total_attention_budget / actual_k;
            stream_budget[sid] += alloc;
            stream_count[sid]++;
        }

        printf("\n─── Per-Stream Budget ───\n");
        printf("  Stream | Deltas | Budget  | Share\n");
        printf("  -------+--------+---------+-------\n");

        int total_delta_count = 0;
        for (int i = 0; i < actual_k; i++) total_delta_count++;

        for (int s = 0; s < NUM_STREAMS; s++) {
            if (stream_count[s] > 0) {
                float share = (float)stream_count[s] / total_delta_count * 100.0f;
                printf("  %6d | %6d | %7.1f | %5.1f%%\n",
                       s, stream_count[s], stream_budget[s], share);
            }
        }

        free(stream_budget);
        free(stream_count);
    }

    /* Cleanup */
    free(h_x); free(h_y); free(h_sid);
    free(h_action); free(h_urgent);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_sid));
    CUDA_SAFE_CALL(cudaFree(d_action)); CUDA_SAFE_CALL(cudaFree(d_urgent));
    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    printf("\nDone.\n");
    return 0;
}
