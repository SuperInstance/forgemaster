/*
 * CUDA batch test — validates GPU kernels against known inputs.
 * Compiles with nvcc, requires CUDA-capable GPU to run.
 */

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cmath>

#include "flux_midi_cuda/clock.cuh"
#include "flux_midi_cuda/snap.cuh"
#include "flux_midi_cuda/flux.cuh"
#include "flux_midi_cuda/harmony.cuh"

#define CUDA_CHECK(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA error: %s\n", cudaGetErrorString(err)); \
        return 1; \
    } \
} while(0)

#define ASSERT_FEQ(a, b, eps) do { \
    double _a = (a), _b = (b); \
    if (fabs(_a - _b) > eps) { \
        fprintf(stderr, "FAIL: %.6f != %.6f\n", _a, _b); \
        return 1; \
    } \
} while(0)

int test_tzero_kernel(void) {
    const int N = 4;
    /* Room 0: just observed at t=0, check at t=0.5 → on_time */
    /* Room 1: observed at t=0, interval=1.0, check at t=2.0 → late */
    /* Room 2: observed at t=0, interval=1.0, check at t=5.0 → silent */
    /* Room 3: observed at t=0, interval=1.0, check at t=20.0 → dead */

    double h_t_last[] = {0.0, 0.0, 0.0, 0.0};
    double h_intervals[] = {1.0, 1.0, 1.0, 1.0};
    double h_t_now[] = {0.5};
    double h_deltas[4];
    int h_missed[4];
    int h_states[4];

    double *d_t_last, *d_intervals, *d_t_now, *d_deltas;
    int *d_missed, *d_states;

    CUDA_CHECK(cudaMalloc(&d_t_last, N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_intervals, N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_t_now, sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_deltas, N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_missed, N * sizeof(int)));
    CUDA_CHECK(cudaMalloc(&d_states, N * sizeof(int)));

    /* First test: t_now = 0.5 — all on_time */
    CUDA_CHECK(cudaMemcpy(d_t_last, h_t_last, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_intervals, h_intervals, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_t_now, h_t_now, sizeof(double), cudaMemcpyHostToDevice));

    clock_cuda_batch_check(d_t_last, d_intervals, d_t_now, d_deltas, d_missed, d_states, N);
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_states, d_states, N * sizeof(int), cudaMemcpyDeviceToHost));
    for (int i = 0; i < N; i++) {
        if (h_states[i] != 0) {
            fprintf(stderr, "FAIL: room %d expected on_time(0), got %d\n", i, h_states[i]);
            return 1;
        }
    }
    printf("  PASS t_now=0.5 all on_time\n");

    /* Test: t_now = 2.0 — room 0 on_time (ratio=2.0, late) */
    h_t_now[0] = 2.0;
    CUDA_CHECK(cudaMemcpy(d_t_now, h_t_now, sizeof(double), cudaMemcpyHostToDevice));
    clock_cuda_batch_check(d_t_last, d_intervals, d_t_now, d_deltas, d_missed, d_states, N);
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaMemcpy(h_states, d_states, N * sizeof(int), cudaMemcpyDeviceToHost));
    if (h_states[0] != 1) {
        fprintf(stderr, "FAIL: room 0 expected late(1), got %d\n", h_states[0]);
        return 1;
    }
    printf("  PASS t_now=2.0 room 0 is late\n");

    /* Test: t_now = 5.0 — silent */
    h_t_now[0] = 5.0;
    CUDA_CHECK(cudaMemcpy(d_t_now, h_t_now, sizeof(double), cudaMemcpyHostToDevice));
    clock_cuda_batch_check(d_t_last, d_intervals, d_t_now, d_deltas, d_missed, d_states, N);
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaMemcpy(h_states, d_states, N * sizeof(int), cudaMemcpyDeviceToHost));
    if (h_states[0] != 2) {
        fprintf(stderr, "FAIL: expected silent(2), got %d\n", h_states[0]);
        return 1;
    }
    printf("  PASS t_now=5.0 room 0 is silent\n");

    /* Test: t_now = 20.0 — dead */
    h_t_now[0] = 20.0;
    CUDA_CHECK(cudaMemcpy(d_t_now, h_t_now, sizeof(double), cudaMemcpyHostToDevice));
    clock_cuda_batch_check(d_t_last, d_intervals, d_t_now, d_deltas, d_missed, d_states, N);
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaMemcpy(h_states, d_states, N * sizeof(int), cudaMemcpyDeviceToHost));
    if (h_states[0] != 3) {
        fprintf(stderr, "FAIL: expected dead(3), got %d\n", h_states[0]);
        return 1;
    }
    printf("  PASS t_now=20.0 room 0 is dead\n");

    CUDA_CHECK(cudaFree(d_t_last));
    CUDA_CHECK(cudaFree(d_intervals));
    CUDA_CHECK(cudaFree(d_t_now));
    CUDA_CHECK(cudaFree(d_deltas));
    CUDA_CHECK(cudaFree(d_missed));
    CUDA_CHECK(cudaFree(d_states));

    return 0;
}

int test_snap_kernel(void) {
    const int N = 3;
    double h_a[] = {1.0, 0.2, 2.0};
    double h_b[] = {1.0, 2.0, 0.1};
    double h_tempo[] = {1.0};
    int h_snap_a[3], h_snap_b[3], h_shapes[3];
    double h_norms[3];

    double *d_a, *d_b, *d_tempo;
    int *d_snap_a, *d_snap_b, *d_shapes;
    double *d_norms;

    CUDA_CHECK(cudaMalloc(&d_a, N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_b, N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_tempo, sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_snap_a, N * sizeof(int)));
    CUDA_CHECK(cudaMalloc(&d_snap_b, N * sizeof(int)));
    CUDA_CHECK(cudaMalloc(&d_shapes, N * sizeof(int)));
    CUDA_CHECK(cudaMalloc(&d_norms, N * sizeof(double)));

    CUDA_CHECK(cudaMemcpy(d_a, h_a, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_tempo, h_tempo, sizeof(double), cudaMemcpyHostToDevice));

    snap_cuda_batch(d_a, d_b, d_tempo, d_snap_a, d_snap_b, d_shapes, d_norms, N);
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_shapes, d_shapes, N * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(h_norms, d_norms, N * sizeof(double), cudaMemcpyDeviceToHost));

    /* (1.0, 1.0) → steady */
    if (h_shapes[0] != SNAP_SHAPE_STEADY) {
        fprintf(stderr, "FAIL: pair 0 expected steady(%d), got %d\n",
                SNAP_SHAPE_STEADY, h_shapes[0]);
        return 1;
    }
    /* (0.2, 2.0) → burst */
    if (h_shapes[1] != SNAP_SHAPE_BURST) {
        fprintf(stderr, "FAIL: pair 1 expected burst(%d), got %d\n",
                SNAP_SHAPE_BURST, h_shapes[1]);
        return 1;
    }
    /* (2.0, 0.1) → collapse */
    if (h_shapes[2] != SNAP_SHAPE_COLLAPSE) {
        fprintf(stderr, "FAIL: pair 2 expected collapse(%d), got %d\n",
                SNAP_SHAPE_COLLAPSE, h_shapes[2]);
        return 1;
    }

    printf("  PASS snap: steady/burst/collapse classified correctly\n");
    printf("  Norms: %.1f, %.1f, %.1f\n", h_norms[0], h_norms[1], h_norms[2]);

    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_tempo));
    CUDA_CHECK(cudaFree(d_snap_a));
    CUDA_CHECK(cudaFree(d_snap_b));
    CUDA_CHECK(cudaFree(d_shapes));
    CUDA_CHECK(cudaFree(d_norms));

    return 0;
}

int test_flux_cosine_kernel(void) {
    const int N = 2;
    /* Room 0: channels [1,0,0,0,0,0,0,0,0] */
    /* Room 1: channels [1,0,0,0,0,0,0,0,0] → cosine should be 1.0 */
    double h_sal[] = {
        1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  /* room 0 */
        1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0   /* room 1 */
    };
    double h_cos[4];

    double *d_sal, *d_cos;
    CUDA_CHECK(cudaMalloc(&d_sal, N * 9 * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_cos, N * N * sizeof(double)));

    CUDA_CHECK(cudaMemcpy(d_sal, h_sal, N * 9 * sizeof(double), cudaMemcpyHostToDevice));

    flux_cuda_batch_cosine(d_sal, d_cos, N);
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_cos, d_cos, N * N * sizeof(double), cudaMemcpyDeviceToHost));

    /* Self-similarity should be 1.0 */
    ASSERT_FEQ(h_cos[0], 1.0, 1e-10);
    ASSERT_FEQ(h_cos[3], 1.0, 1e-10);
    /* Cross-similarity: identical vectors */
    ASSERT_FEQ(h_cos[1], 1.0, 1e-10);
    ASSERT_FEQ(h_cos[2], 1.0, 1e-10);

    printf("  PASS flux cosine: identical vectors = 1.0\n");

    /* Now test orthogonal vectors */
    h_sal[9] = 0.0;  /* room 1, channel 0 = 0 */
    h_sal[10] = 1.0; /* room 1, channel 1 = 1 */
    CUDA_CHECK(cudaMemcpy(d_sal, h_sal, N * 9 * sizeof(double), cudaMemcpyHostToDevice));
    flux_cuda_batch_cosine(d_sal, d_cos, N);
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaMemcpy(h_cos, d_cos, N * N * sizeof(double), cudaMemcpyDeviceToHost));
    ASSERT_FEQ(h_cos[1], 0.0, 1e-10);
    printf("  PASS flux cosine: orthogonal vectors = 0.0\n");

    CUDA_CHECK(cudaFree(d_sal));
    CUDA_CHECK(cudaFree(d_cos));
    return 0;
}

int main(void) {
    printf("=== FLUX-Tensor-MIDI CUDA Tests ===\n");

    int device_count;
    cudaGetDeviceCount(&device_count);
    if (device_count == 0) {
        printf("No CUDA devices found. Skipping GPU tests.\n");
        return 0;
    }

    int fails = 0;
    fails += test_tzero_kernel();
    fails += test_snap_kernel();
    fails += test_flux_cosine_kernel();

    printf(fails == 0 ? "\nAll CUDA tests passed.\n" : "\n%d CUDA test(s) FAILED.\n", fails);
    return fails;
}
