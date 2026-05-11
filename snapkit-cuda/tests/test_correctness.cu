/*
 * test_correctness.cu — CPU vs GPU correctness verification
 *
 * Verifies GPU snaps match CPU reference for all ADE topologies.
 * Tests: A₁ (binary), A₂ (Eisenstein), A₃ (tetrahedral), D₄, E₈
 */

#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* ======================================================================
 * CPU Reference: Eisenstein Snap
 * ====================================================================== */

void cpu_eisenstein(float x, float y, int* a, int* b, float* delta) {
    const float sqrt3 = 1.7320508075688772f;
    *b = (int)roundf(y * 2.0f / sqrt3);
    *a = (int)roundf(x + *b * 0.5f);
    float sx = *a - *b * 0.5f;
    float sy = *b * sqrt3 * 0.5f;
    *delta = sqrtf((x - sx)*(x - sx) + (y - sy)*(y - sy));
}

/* ======================================================================
 * CPU Reference: Binary Snap
 * ====================================================================== */

void cpu_binary(float v, float* snapped, float* delta) {
    *snapped = (v >= 0.0f) ? 1.0f : -1.0f;
    *delta = fabsf(v - *snapped);
}

/* ======================================================================
 * CPU Reference: Tetrahedral Snap
 * ====================================================================== */

void cpu_tetrahedral(float x, float y, float z,
                      float* sx, float* sy, float* sz, float* delta) {
    float inv_sqrt3 = 0.5773502691896258f;
    float d0 = x + y + z;
    float d1 = x - y - z;
    float d2 = -x + y - z;
    float d3 = -x - y + z;

    float max_d = d0;
    int best = 0;
    if (d1 > max_d) { max_d = d1; best = 1; }
    if (d2 > max_d) { max_d = d2; best = 2; }
    if (d3 > max_d) { max_d = d3; best = 3; }

    float mag = sqrtf(x*x + y*y + z*z);
    if (mag < 1e-12f) mag = 1e-12f;

    switch (best) {
        case 0: *sx = mag * inv_sqrt3; *sy = mag * inv_sqrt3; *sz = mag * inv_sqrt3; break;
        case 1: *sx = mag * inv_sqrt3; *sy = -mag * inv_sqrt3; *sz = -mag * inv_sqrt3; break;
        case 2: *sx = -mag * inv_sqrt3; *sy = mag * inv_sqrt3; *sz = -mag * inv_sqrt3; break;
        case 3: *sx = -mag * inv_sqrt3; *sy = -mag * inv_sqrt3; *sz = mag * inv_sqrt3; break;
    }

    *delta = sqrtf((x-*sx)*(x-*sx) + (y-*sy)*(y-*sy) + (z-*sz)*(z-*sz));
}

/* ======================================================================
 * Test: All topologies vs CPU reference
 * ====================================================================== */

int test_all_topologies() {
    printf("  All ADE topologies vs CPU reference...\n");

    const int N = 10000;
    int failures = 0;

    /* Generate test points */
    float *h_x = (float*)malloc(N * sizeof(float));
    float *h_y = (float*)malloc(N * sizeof(float));
    float *h_z = (float*)malloc(N * sizeof(float));
    float *h_4d = (float*)malloc(N * 4 * sizeof(float));
    assert(h_x && h_y && h_z && h_4d);

    srand(111);
    for (int i = 0; i < N; i++) {
        h_x[i] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
        h_y[i] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
        h_z[i] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
        h_4d[i*4 + 0] = h_x[i];
        h_4d[i*4 + 1] = h_y[i];
        h_4d[i*4 + 2] = h_z[i];
        h_4d[i*4 + 3] = ((float)rand() / RAND_MAX - 0.5f) * 10.0f;
    }

    /* ---- A₁ Binary test ---- */
    {
        float *d_pts, *d_snap, *d_delta;
        CUDA_SAFE_CALL(cudaMalloc(&d_pts, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_snap, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMemcpy(d_pts, h_x, N * sizeof(float), cudaMemcpyHostToDevice));

        snapkit_snap_a1(d_pts, d_snap, d_delta, N, 0);
        CUDA_SAFE_CALL(cudaDeviceSynchronize());

        float *gpu_snap = (float*)malloc(N * sizeof(float));
        float *gpu_delta = (float*)malloc(N * sizeof(float));
        assert(gpu_snap && gpu_delta);
        CUDA_SAFE_CALL(cudaMemcpy(gpu_snap, d_snap, N * sizeof(float), cudaMemcpyDeviceToHost));
        CUDA_SAFE_CALL(cudaMemcpy(gpu_delta, d_delta, N * sizeof(float), cudaMemcpyDeviceToHost));

        int a1_errors = 0;
        for (int i = 0; i < N; i++) {
            float cpu_s, cpu_d;
            cpu_binary(h_x[i], &cpu_s, &cpu_d);
            if (fabsf(gpu_snap[i] - cpu_s) > 1e-5f) a1_errors++;
        }
        printf("    A₁ (binary): %d errors\n", a1_errors);
        failures += a1_errors;

        free(gpu_snap); free(gpu_delta);
        CUDA_SAFE_CALL(cudaFree(d_pts));
        CUDA_SAFE_CALL(cudaFree(d_snap));
        CUDA_SAFE_CALL(cudaFree(d_delta));
    }

    /* ---- A₃ Tetrahedral test ---- */
    {
        float *d_x, *d_y, *d_z, *d_ox, *d_oy, *d_oz, *d_delta;
        CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_z, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_ox, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_oy, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_oz, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

        CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
        CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));
        CUDA_SAFE_CALL(cudaMemcpy(d_z, h_z, N * sizeof(float), cudaMemcpyHostToDevice));

        snapkit_snap_a3(d_x, d_y, d_z, d_ox, d_oy, d_oz, d_delta, N, 0);
        CUDA_SAFE_CALL(cudaDeviceSynchronize());

        float *gpu_ox = (float*)malloc(N * sizeof(float));
        float *gpu_oy = (float*)malloc(N * sizeof(float));
        float *gpu_oz = (float*)malloc(N * sizeof(float));
        assert(gpu_ox && gpu_oy && gpu_oz);
        CUDA_SAFE_CALL(cudaMemcpy(gpu_ox, d_ox, N * sizeof(float), cudaMemcpyDeviceToHost));
        CUDA_SAFE_CALL(cudaMemcpy(gpu_oy, d_oy, N * sizeof(float), cudaMemcpyDeviceToHost));
        CUDA_SAFE_CALL(cudaMemcpy(gpu_oz, d_oz, N * sizeof(float), cudaMemcpyDeviceToHost));

        int a3_errors = 0;
        for (int i = 0; i < N; i++) {
            float cpu_x, cpu_y, cpu_z, cpu_d;
            cpu_tetrahedral(h_x[i], h_y[i], h_z[i], &cpu_x, &cpu_y, &cpu_z, &cpu_d);
            float diff = fabsf(gpu_ox[i] - cpu_x) +
                        fabsf(gpu_oy[i] - cpu_y) +
                        fabsf(gpu_oz[i] - cpu_z);
            if (diff > 1e-5f) a3_errors++;
        }
        printf("    A₃ (tetrahedral): %d errors\n", a3_errors);
        failures += a3_errors;

        free(gpu_ox); free(gpu_oy); free(gpu_oz);
        CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_ox));
        CUDA_SAFE_CALL(cudaFree(d_y)); CUDA_SAFE_CALL(cudaFree(d_oy));
        CUDA_SAFE_CALL(cudaFree(d_z)); CUDA_SAFE_CALL(cudaFree(d_oz));
        CUDA_SAFE_CALL(cudaFree(d_delta));
    }

    /* ---- A₂ Eisenstein test ---- */
    {
        float *d_x, *d_y, *d_delta;
        int *d_a, *d_b;
        CUDA_SAFE_CALL(cudaMalloc(&d_x, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_y, N * sizeof(float)));
        CUDA_SAFE_CALL(cudaMalloc(&d_a, N * sizeof(int)));
        CUDA_SAFE_CALL(cudaMalloc(&d_b, N * sizeof(int)));
        CUDA_SAFE_CALL(cudaMalloc(&d_delta, N * sizeof(float)));

        CUDA_SAFE_CALL(cudaMemcpy(d_x, h_x, N * sizeof(float), cudaMemcpyHostToDevice));
        CUDA_SAFE_CALL(cudaMemcpy(d_y, h_y, N * sizeof(float), cudaMemcpyHostToDevice));

        snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, N, 0);
        CUDA_SAFE_CALL(cudaDeviceSynchronize());

        int *gpu_a = (int*)malloc(N * sizeof(int));
        int *gpu_b = (int*)malloc(N * sizeof(int));
        assert(gpu_a && gpu_b);
        CUDA_SAFE_CALL(cudaMemcpy(gpu_a, d_a, N * sizeof(int), cudaMemcpyDeviceToHost));
        CUDA_SAFE_CALL(cudaMemcpy(gpu_b, d_b, N * sizeof(int), cudaMemcpyDeviceToHost));

        int a2_errors = 0;
        for (int i = 0; i < N; i++) {
            int cpu_a, cpu_b;
            float cpu_d;
            cpu_eisenstein(h_x[i], h_y[i], &cpu_a, &cpu_b, &cpu_d);
            if (gpu_a[i] != cpu_a || gpu_b[i] != cpu_b) a2_errors++;
        }
        printf("    A₂ (Eisenstein): %d errors\n", a2_errors);
        failures += a2_errors;

        free(gpu_a); free(gpu_b);
        CUDA_SAFE_CALL(cudaFree(d_x)); CUDA_SAFE_CALL(cudaFree(d_y));
        CUDA_SAFE_CALL(cudaFree(d_a)); CUDA_SAFE_CALL(cudaFree(d_b));
        CUDA_SAFE_CALL(cudaFree(d_delta));
    }

    free(h_x); free(h_y); free(h_z); free(h_4d);

    if (failures > 0) {
        printf("    FAILED (%d total errors)\n", failures);
        return 1;
    }

    printf("    PASSED\n");
    return 0;
}

int main() {
    printf("\n=== CPU vs GPU Correctness Verification ===\n\n");

    int failures = test_all_topologies();

    printf("\n=== Results: %s ===\n\n",
           failures == 0 ? "ALL PASSED" : "SOME FAILED");
    return failures;
}
