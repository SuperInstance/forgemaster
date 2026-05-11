/*
 * examples/stream_monitor.cu — Real-time stream monitoring on GPU
 *
 * Demonstrates multi-stream delta detection and attention allocation
 * on synthetic data streams.
 *
 * Each stream has its own tolerance and data distribution.
 * The pipeline: snap → delta threshold → attention weight → top-K
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

int main() {
    const int NUM_STREAMS = 4;
    const int POINTS_PER_STREAM = 100000;
    const int TOTAL_POINTS = NUM_STREAMS * POINTS_PER_STREAM;

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  Multi-Stream Delta Monitor                ║\n");
    printf("║  %d streams × %d points = %d total         ║\n",
           NUM_STREAMS, POINTS_PER_STREAM, TOTAL_POINTS);
    printf("╚══════════════════════════════════════════════╝\n\n");

    /* Generate synthetic multi-stream data */
    float *h_x = (float*)malloc(TOTAL_POINTS * sizeof(float));
    float *h_y = (float*)malloc(TOTAL_POINTS * sizeof(float));
    int   *h_sid = (int*)malloc(TOTAL_POINTS * sizeof(int));
    float *h_action = (float*)malloc(TOTAL_POINTS * sizeof(float));
    float *h_urgent = (float*)malloc(TOTAL_POINTS * sizeof(float));
    assert(h_x && h_y && h_sid && h_action && h_urgent);

    /* Stream configurations */
    struct {
        float mean_x, mean_y;
        float noise;
        float tolerance;
        float actionability;
        float urgency;
    } streams[NUM_STREAMS] = {
        {0.0f, 0.0f, 0.05f, 0.1f,  0.5f, 1.0f},  /* Low noise, sensor */
        {1.0f, 1.0f, 0.5f,  0.3f,  1.0f, 0.8f},  /* High noise, behavioral */
        {5.0f, 5.0f, 2.0f,  1.0f,  0.3f, 0.5f},  /* Very high noise, market */
        {-2.0f, 3.0f, 1.0f, 0.5f, 0.8f, 0.3f},  /* Medium noise, social */
    };

    srand(123);
    for (int s = 0; s < NUM_STREAMS; s++) {
        for (int p = 0; p < POINTS_PER_STREAM; p++) {
            int idx = s * POINTS_PER_STREAM + p;
            h_x[idx] = streams[s].mean_x + ((float)rand() / RAND_MAX - 0.5f) * 2 * streams[s].noise;
            h_y[idx] = streams[s].mean_y + ((float)rand() / RAND_MAX - 0.5f) * 2 * streams[s].noise;
            h_sid[idx] = s;
            h_action[idx] = streams[s].actionability;
            h_urgent[idx] = streams[s].urgency;
        }
    }

    /* Allocate device memory */
    float *d_x, *d_y, *d_delta, *d_weights, *d_action, *d_urgent, *d_tols;
    int   *d_a, *d_b, *d_sid, *d_is_delta, *d_top_idx;
    float *d_top_w;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, TOTAL_POINTS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, TOTAL_POINTS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_sid, TOTAL_POINTS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_is_delta, TOTAL_POINTS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_weights, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_action, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_urgent, TOTAL_POINTS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_tols, NUM_STREAMS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_top_idx, 16 * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_top_w, 16 * sizeof(float)));

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

    float host_tols[NUM_STREAMS];
    for (int s = 0; s < NUM_STREAMS; s++) {
        host_tols[s] = streams[s].tolerance;
    }
    CUDA_SAFE_CALL(cudaMemcpy(d_tols, host_tols, NUM_STREAMS * sizeof(float),
                               cudaMemcpyHostToDevice));

    /* Run the full pipeline */
    cudaEvent_t start, stop;
    CUDA_SAFE_CALL(cudaEventCreate(&start));
    CUDA_SAFE_CALL(cudaEventCreate(&stop));

    printf("Running pipeline: snap → threshold → weight → top-K\n");

    CUDA_SAFE_CALL(cudaEventRecord(start));

    /* Step 1: Batch Eisenstein snap */
    snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, TOTAL_POINTS, 0);

    /* Step 2: Delta threshold with actionability & urgency */
    snapkit_delta_threshold_weighted(
        d_delta, d_tols, d_sid, d_action, d_urgent,
        d_is_delta, d_weights, TOTAL_POINTS, 0
    );

    /* Step 3: Top-16 deltas */
    int top_k = snapkit_top_k_deltas(d_weights, d_top_idx, d_top_w, 16,
                                     TOTAL_POINTS, 0);

    CUDA_SAFE_CALL(cudaEventRecord(stop));
    CUDA_SAFE_CALL(cudaEventSynchronize(stop));

    float ms;
    CUDA_SAFE_CALL(cudaEventElapsedTime(&ms, start, stop));

    /* Get stream-level statistics */
    int *h_stream_counts = (int*)calloc(NUM_STREAMS, sizeof(int));
    float *h_stream_sums = (float*)calloc(NUM_STREAMS, sizeof(float));
    assert(h_stream_counts && h_stream_sums);

    int *d_stream_counts, *d_stream_sums;
    CUDA_SAFE_CALL(cudaMalloc(&d_stream_counts, NUM_STREAMS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_stream_sums, NUM_STREAMS * sizeof(float)));
    CUDA_SAFE_CALL(cudaMemset(d_stream_counts, 0, NUM_STREAMS * sizeof(int)));
    CUDA_SAFE_CALL(cudaMemset(d_stream_sums, 0, NUM_STREAMS * sizeof(float)));

    snapkit_delta_stream_counts(
        d_delta, d_tols, d_sid,
        d_stream_counts, d_stream_sums,
        TOTAL_POINTS, NUM_STREAMS, 0
    );
    CUDA_SAFE_CALL(cudaDeviceSynchronize());

    CUDA_SAFE_CALL(cudaMemcpy(h_stream_counts, d_stream_counts,
                               NUM_STREAMS * sizeof(int),
                               cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(h_stream_sums, d_stream_sums,
                               NUM_STREAMS * sizeof(float),
                               cudaMemcpyDeviceToHost));

    /* Print results */
    printf("\n─── Results ───\n");
    printf("  Pipeline time: %.2f ms\n", ms);
    printf("  Total points:  %d\n", TOTAL_POINTS);
    printf("  Throughput:    %.2f M pts/sec\n",
           (double)TOTAL_POINTS / (ms / 1000.0) / 1e6);

    printf("\n─── Per-Stream Delta Report ───\n");
    printf("  Stream | Points | Deltas | Rate   | Tol   | Action | Urgency\n");
    printf("  -------+--------+--------+--------+-------+--------+--------\n");
    for (int s = 0; s < NUM_STREAMS; s++) {
        float rate = (float)h_stream_counts[s] / POINTS_PER_STREAM * 100.0f;
        printf("  %6d | %6d | %6d | %5.1f%% | %.2f |  %.2f  |  %.2f\n",
               s, POINTS_PER_STREAM, h_stream_counts[s], rate,
               streams[s].tolerance,
               streams[s].actionability, streams[s].urgency);
    }

    printf("\n─── Top-%d Deltas (by attention weight) ───\n", top_k);
    int *h_top_idx = (int*)malloc(16 * sizeof(int));
    float *h_top_w = (float*)malloc(16 * sizeof(float));
    assert(h_top_idx && h_top_w);

    CUDA_SAFE_CALL(cudaMemcpy(h_top_idx, d_top_idx, 16 * sizeof(int),
                               cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(h_top_w, d_top_w, 16 * sizeof(float),
                               cudaMemcpyDeviceToHost));

    printf("  Rank | Point   | Stream | Weight\n");
    printf("  -----+---------+--------+--------\n");
    for (int i = 0; i < top_k && i < 16; i++) {
        if (h_top_idx[i] >= 0) {
            int sid = h_sid[h_top_idx[i]];
            printf("  %4d | %7d | %6d | %.4f\n",
                   i + 1, h_top_idx[i], sid, h_top_w[i]);
        }
    }

    /* Cleanup */
    free(h_x); free(h_y); free(h_sid);
    free(h_action); free(h_urgent);
    free(h_stream_counts); free(h_stream_sums);
    free(h_top_idx); free(h_top_w);

    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta)); CUDA_SAFE_CALL(cudaFree(d_sid));
    CUDA_SAFE_CALL(cudaFree(d_is_delta)); CUDA_SAFE_CALL(cudaFree(d_weights));
    CUDA_SAFE_CALL(cudaFree(d_action)); CUDA_SAFE_CALL(cudaFree(d_urgent));
    CUDA_SAFE_CALL(cudaFree(d_tols));
    CUDA_SAFE_CALL(cudaFree(d_top_idx)); CUDA_SAFE_CALL(cudaFree(d_top_w));
    CUDA_SAFE_CALL(cudaFree(d_stream_counts)); CUDA_SAFE_CALL(cudaFree(d_stream_sums));

    CUDA_SAFE_CALL(cudaEventDestroy(start));
    CUDA_SAFE_CALL(cudaEventDestroy(stop));

    printf("\nDone.\n");
    return 0;
}
