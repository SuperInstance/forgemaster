/*
 * test_delta.cu — Delta detection and attention weight tests
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

int test_delta_threshold() {
    printf("  Delta threshold detection...\n");

    const int N = 10;

    /* Test data */
    float h_deltas[N]    = {0.01f, 0.05f, 0.1f, 0.15f, 0.2f,
                            0.5f, 1.0f, 2.0f, 5.0f, 10.0f};
    int   h_streams[N]   = {0, 0, 0, 0, 0, 1, 1, 1, 1, 1};
    float tolerances[2]  = {0.1f, 1.0f};

    /* Expected results */
    int expected_delta[N] = {0, 0, 1, 1, 1, 0, 1, 1, 1, 1};

    float *d_deltas, *d_tols, *d_weights;
    int *d_streams, *d_is_delta;

    CUDA_SAFE_CALL(cudaMalloc(&d_deltas, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_tols, 2 * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_streams, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_is_delta, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_weights, N * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_deltas, h_deltas, N * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_tols, tolerances, 2 * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_streams, h_streams, N * sizeof(int),
                               cudaMemcpyHostToDevice));

    snapkit_delta_threshold(d_deltas, d_tols, d_streams,
                            d_is_delta, d_weights, N, 0);
    CUDA_SAFE_CALL(cudaDeviceSynchronize());

    int *h_is_delta = (int*)malloc(N * sizeof(int));
    float *h_weights = (float*)malloc(N * sizeof(float));
    assert(h_is_delta && h_weights);

    CUDA_SAFE_CALL(cudaMemcpy(h_is_delta, d_is_delta, N * sizeof(int),
                               cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(h_weights, d_weights, N * sizeof(float),
                               cudaMemcpyDeviceToHost));

    int failures = 0;
    for (int i = 0; i < N; i++) {
        if (h_is_delta[i] != expected_delta[i]) {
            printf("    FAIL [%d]: delta=%.3f stream=%d expected=%d got=%d\n",
                   i, h_deltas[i], h_streams[i], expected_delta[i], h_is_delta[i]);
            failures++;
        }

        if (expected_delta[i]) {
            if (h_weights[i] != h_deltas[i]) {
                printf("    FAIL [%d]: weight=%.3f expected=%.3f\n",
                       i, h_weights[i], h_deltas[i]);
                failures++;
            }
        } else {
            if (h_weights[i] != 0.0f) {
                printf("    FAIL [%d]: weight=%.3f expected=0.0\n", i, h_weights[i]);
                failures++;
            }
        }
    }

    free(h_is_delta); free(h_weights);
    CUDA_SAFE_CALL(cudaFree(d_deltas)); CUDA_SAFE_CALL(cudaFree(d_tols));
    CUDA_SAFE_CALL(cudaFree(d_streams));
    CUDA_SAFE_CALL(cudaFree(d_is_delta)); CUDA_SAFE_CALL(cudaFree(d_weights));

    if (failures > 0) {
        printf("    FAILED (%d errors)\n", failures);
        return 1;
    }

    printf("    PASSED\n");
    return 0;
}

int test_attention_weights() {
    printf("  Attention weight scoring...\n");

    const int N = 8;

    float h_deltas[N]  = {0.5f, 0.3f, 0.0f, 0.8f, 1.0f, 0.2f, 0.6f, 0.0f};
    int   h_is_delta[N] = {1, 1, 0, 1, 1, 1, 1, 0};
    float h_action[N]  = {1.0f, 0.5f, 0.0f, 0.8f, 1.0f, 0.3f, 0.7f, 0.0f};
    float h_urgent[N]  = {1.0f, 1.0f, 0.0f, 0.5f, 0.8f, 0.2f, 0.9f, 0.0f};

    float *d_deltas, *d_weights, *d_action, *d_urgent;
    int *d_is_delta;

    CUDA_SAFE_CALL(cudaMalloc(&d_deltas, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_is_delta, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_action, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_urgent, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_weights, N * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_deltas, h_deltas, N * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_is_delta, h_is_delta, N * sizeof(int),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_action, h_action, N * sizeof(float),
                               cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_urgent, h_urgent, N * sizeof(float),
                               cudaMemcpyHostToDevice));

    snapkit_compute_attention_weights(
        d_deltas, d_is_delta, d_action, d_urgent, d_weights, N, 0
    );
    CUDA_SAFE_CALL(cudaDeviceSynchronize());

    float *h_weights = (float*)malloc(N * sizeof(float));
    assert(h_weights);
    CUDA_SAFE_CALL(cudaMemcpy(h_weights, d_weights, N * sizeof(float),
                               cudaMemcpyDeviceToHost));

    int failures = 0;
    for (int i = 0; i < N; i++) {
        float expected = h_is_delta[i]
            ? h_deltas[i] * h_action[i] * h_urgent[i]
            : 0.0f;

        if (fabsf(h_weights[i] - expected) > 1e-5f) {
            printf("    FAIL [%d]: weight=%.4f expected=%.4f\n",
                   i, h_weights[i], expected);
            failures++;
        }
    }

    free(h_weights);
    CUDA_SAFE_CALL(cudaFree(d_deltas)); CUDA_SAFE_CALL(cudaFree(d_is_delta));
    CUDA_SAFE_CALL(cudaFree(d_action)); CUDA_SAFE_CALL(cudaFree(d_urgent));
    CUDA_SAFE_CALL(cudaFree(d_weights));

    if (failures > 0) {
        printf("    FAILED (%d errors)\n", failures);
        return 1;
    }

    printf("    PASSED\n");
    return 0;
}

int test_top_k() {
    printf("  Top-K delta selection...\n");

    const int N = 100;
    const int K = 5;

    float *h_weights = (float*)malloc(N * sizeof(float));
    assert(h_weights);

    srand(777);
    for (int i = 0; i < N; i++) {
        h_weights[i] = ((float)rand() / RAND_MAX) * 10.0f;
    }

    float *d_weights;
    CUDA_SAFE_CALL(cudaMalloc(&d_weights, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMemcpy(d_weights, h_weights, N * sizeof(float),
                               cudaMemcpyHostToDevice));

    int indices[K];
    float top_weights[K];

    int actual_k = snapkit_top_k_deltas(
        d_weights, indices, top_weights, K, N, 0
    );

    printf("    Top-K found %d deltas\n", actual_k);

    /* Sort weights to verify */
    float sorted[N];
    memcpy(sorted, h_weights, N * sizeof(float));
    for (int i = 0; i < N - 1; i++) {
        for (int j = 0; j < N - 1 - i; j++) {
            if (sorted[j] < sorted[j + 1]) {
                float t = sorted[j];
                sorted[j] = sorted[j + 1];
                sorted[j + 1] = t;
            }
        }
    }

    int failures = 0;
    for (int i = 0; i < actual_k; i++) {
        if (fabsf(top_weights[i] - sorted[i]) > 1e-4f) {
            printf("    FAIL [%d]: got %.4f expected %.4f\n",
                   i, top_weights[i], sorted[i]);
            failures++;
        }
    }

    free(h_weights);
    CUDA_SAFE_CALL(cudaFree(d_weights));

    printf("    %s\n", failures > 0 ? "FAILED" : "PASSED");
    return failures;
}

int main() {
    printf("\n=== Delta Detection Tests ===\n\n");

    int failures = 0;
    failures += test_delta_threshold();
    failures += test_attention_weights();
    failures += test_top_k();

    printf("\n=== Results: %s ===\n\n",
           failures == 0 ? "ALL PASSED" : "SOME FAILED");
    return failures;
}
