/*
 * test_eisenstein.cu — Unit tests for Eisenstein snap
 *
 * Tests correctness of the core Eisenstein lattice snap.
 * Compares GPU results against CPU reference implementation.
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* CPU reference Eisenstein snap */
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

int test_single_point() {
    printf("  Single point snap...\n");

    /* Test vectors: (x, y, expected_a, expected_b)*/
    struct {
        float x, y;
        int exp_a, exp_b;
    } tests[] = {
        {0.0f, 0.0f, 0, 0},           /* Origin */
        {1.0f, 0.0f, 1, 0},           /* Integer X */
        {0.0f, 1.0f, 0, 1},           /* Unit Y (maps to b=1) */
        {0.5f, 0.5f, 1, 1},           /* Midpoint */
        {-1.0f, 0.0f, -1, 0},          /* Negative X */
        {0.0f, -1.732f, 0, -2},        /* Negative Y (≈ -√3) */
        {1.0f, 1.732f, 1, 2},          /* (1, √3) → (1, 2) */
        {2.0f, 3.464f, 2, 4},          /* (2, 2√3) → (2, 4) */
        {1.5f, 0.866f, 2, 1},          /* (1.5, √3/2) → (2, 1) */
        {0.1f, 0.05f, 0, 0},          /* Very close to origin */
    };

    int num_tests = sizeof(tests) / sizeof(tests[0]);

    for (int i = 0; i < num_tests; i++) {
        int gpu_a, gpu_b, cpu_a, cpu_b;
        float gpu_delta, cpu_delta;

        /* CPU reference */
        cpu_eisenstein_snap(tests[i].x, tests[i].y, &cpu_a, &cpu_b, &cpu_delta);

        /* GPU */
        snapkit_eisenstein_snap_single(tests[i].x, tests[i].y,
                                       &gpu_a, &gpu_b, &gpu_delta);

        /* Compare */
        if (gpu_a != cpu_a || gpu_b != cpu_b) {
            printf("    FAIL: (%.3f, %.3f): GPU=(%d,%d) CPU=(%d,%d) expected=(%d,%d)\n",
                   tests[i].x, tests[i].y,
                   gpu_a, gpu_b, cpu_a, cpu_b,
                   tests[i].exp_a, tests[i].exp_b);
            return 1;
        }

        float delta_diff = fabsf(gpu_delta - cpu_delta);
        if (delta_diff > 1e-5f) {
            printf("    FAIL: (%.3f, %.3f): delta GPU=%.6f CPU=%.6f diff=%.6f\n",
                   tests[i].x, tests[i].y, gpu_delta, cpu_delta, delta_diff);
            return 1;
        }
    }

    printf("    PASSED (%d tests)\n", num_tests);
    return 0;
}

int test_batch_snap() {
    printf("  Batch snap correctness (100K points)...\n");

    const int N = 100000;

    /* Generate random points */
    float *h_x = (float*)malloc(N * sizeof(float));
    float *h_y = (float*)malloc(N * sizeof(float));
    assert(h_x && h_y);

    srand(42);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 100.0f;
    }

    /* GPU memory */
    float *d_x, *d_y, *d_delta;
    int *d_a, *d_b;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));

    /* Run GPU batch snap */
    snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, 0);
    CUDA_SAFE_CALL(cudaDeviceSynchronize());

    /* Copy results back */
    int *gpu_a = (int*)malloc(N * sizeof(int));
    int *gpu_b = (int*)malloc(N * sizeof(int));
    float *gpu_delta = (float*)malloc(N * sizeof(float));
    assert(gpu_a && gpu_b && gpu_delta);

    CUDA_SAFE_CALL(cudaMemcpy(gpu_a, d_a, N * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(gpu_b, d_b, N * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(gpu_delta, d_delta, N * sizeof(float), cudaMemcpyDeviceToHost));

    /* Verify against CPU */
    int errors = 0;
    float max_delta_diff = 0.0f;
    for (int i = 0; i < N; i++) {
        int cpu_a, cpu_b;
        float cpu_delta;
        cpu_eisenstein_snap(h_x[i], h_y[i], &cpu_a, &cpu_b, &cpu_delta);

        if (gpu_a[i] != cpu_a || gpu_b[i] != cpu_b) {
            if (errors < 5) {
                printf("    MISMATCH [%d]: (%.3f, %.3f) GPU=(%d,%d) CPU=(%d,%d)\n",
                       i, h_x[i], h_y[i], gpu_a[i], gpu_b[i], cpu_a, cpu_b);
            }
            errors++;
        }

        float diff = fabsf(gpu_delta[i] - cpu_delta);
        if (diff > max_delta_diff) max_delta_diff = diff;
    }

    printf("    Errors: %d / %d\n", errors, N);
    printf("    Max delta diff: %.8f\n", max_delta_diff);

    if (errors > 0) {
        printf("    FAILED\n");
    } else {
        printf("    PASSED\n");
    }

    /* Cleanup */
    free(h_x); free(h_y);
    free(gpu_a); free(gpu_b); free(gpu_delta);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));

    return errors > 0 ? 1 : 0;
}

int test_edge_cases() {
    printf("  Edge cases...\n");

    struct {
        float x, y;
        const char* name;
    } edge_tests[] = {
        {0.0f, 0.0f, "origin"},
        {1e-10f, 1e-10f, "near-zero"},
        {1e10f, 1e10f, "large"},
        {-1e10f, 1e10f, "large mixed"},
        {0.5f, 0.8660254f, "hex cell center"},
        {0.25f, 0.4330127f, "near hex center"},
        {1.0f / 3.0f, 1.0f / 3.0f, "third-third"},
    };

    int num_tests = sizeof(edge_tests) / sizeof(edge_tests[0]);

    for (int i = 0; i < num_tests; i++) {
        int gpu_a, gpu_b, cpu_a, cpu_b;
        float gpu_delta, cpu_delta;

        cpu_eisenstein_snap(edge_tests[i].x, edge_tests[i].y,
                           &cpu_a, &cpu_b, &cpu_delta);
        snapkit_eisenstein_snap_single(edge_tests[i].x, edge_tests[i].y,
                                       &gpu_a, &gpu_b, &gpu_delta);

        /* Check delta is non-negative */
        if (gpu_delta < 0.0f) {
            printf("    FAIL: %s: negative delta %.6f\n",
                   edge_tests[i].name, gpu_delta);
            return 1;
        }

        /* Check delta is sane (should be < 1.0 for these tests) */
        if (gpu_delta > 1.0f) {
            printf("    WARN: %s: large delta %.6f\n",
                   edge_tests[i].name, gpu_delta);
        }

        /* Check CPU/GPU match */
        float diff = fabsf(gpu_delta - cpu_delta);
        if (diff > 1e-5f) {
            printf("    FAIL: %s: delta GPU=%.6f CPU=%.6f\n",
                   edge_tests[i].name, gpu_delta, cpu_delta);
            return 1;
        }
    }

    printf("    PASSED (%d edge cases)\n", num_tests);
    return 0;
}

int test_determinism() {
    printf("  Determinism (same input → same output)...\n");

    const int N = 1000;
    float h_x[N], h_y[N];
    srand(12345);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
    }

    float *d_x, *d_y, *d_delta;
    int *d_a, *d_b;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, N * sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

    int *run1_a = (int*)malloc(N * sizeof(int));
    int *run2_a = (int*)malloc(N * sizeof(int));
    assert(run1_a && run2_a);

    for (int run = 0; run < 2; run++) {
        CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
        CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));

        snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, 0);
        CUDA_SAFE_CALL(cudaDeviceSynchronize());

        CUDA_SAFE_CALL(cudaMemcpy(run1_a, d_a, N * sizeof(int), cudaMemcpyDeviceToHost));

        /* Run again */
        CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
        CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));

        snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, 0);
        CUDA_SAFE_CALL(cudaDeviceSynchronize());

        CUDA_SAFE_CALL(cudaMemcpy(run2_a, d_a, N * sizeof(int), cudaMemcpyDeviceToHost));

        /* Compare */
        int mismatches = 0;
        for (int i = 0; i < N; i++) {
            if (run1_a[i] != run2_a[i]) mismatches++;
        }

        if (mismatches > 0) {
            printf("    FAIL: run %d: %d mismatches\n", run, mismatches);
            free(run1_a); free(run2_a);
            CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
            CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
            CUDA_SAFE_CALL(cudaFree(d_delta));
            return 1;
        }
    }

    free(run1_a); free(run2_a);
    CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));

    printf("    PASSED\n");
    return 0;
}

int main() {
    printf("\n=== Eisenstein Snap Tests ===\n\n");

    int failures = 0;

    failures += test_single_point();
    failures += test_batch_snap();
    failures += test_edge_cases();
    failures += test_determinism();

    printf("\n=== Results: %s ===\n\n",
           failures == 0 ? "ALL PASSED" : "SOME FAILED");

    return failures;
}
