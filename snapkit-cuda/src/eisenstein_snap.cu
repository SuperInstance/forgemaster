/*
 * eisenstein_snap.cu — GPU Eisenstein lattice snap implementation
 *
 * "The snap is the gatekeeper of attention. The Eisenstein lattice is
 *  the optimal attention compressor — densest packing, isotropic,
 *  PID property (H¹ = 0 guarantee)."
 *
 * Implements the host API for the batch Eisenstein snap kernels.
 */

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "eisenstein_snap.cuh"
#include "batch_snap.cuh"
#include "kernels/eisenstein_snap_kernel.cuh"

/* ======================================================================
 * Host API: Batch Eisenstein Snap
 * ====================================================================== */

void snapkit_batch_eisenstein_snap(
    const float* points_x,
    const float* points_y,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    /* Use PTX-optimized kernel */
    eisenstein_snap_ptx_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y, out_a, out_b, out_delta, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Quick snap (single point, synchronous)
 * ====================================================================== */

void snapkit_eisenstein_snap_single(
    float x, float y,
    int* a, int* b, float* delta
) {
    /* Allocate device memory for single point */
    float *d_x, *d_y;
    int   *d_a, *d_b;
    float *d_delta;

    CUDA_SAFE_CALL(cudaMalloc(&d_x, sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_y, sizeof(float)));
    CUDA_SAFE_CALL(cudaMalloc(&d_a, sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_b, sizeof(int)));
    CUDA_SAFE_CALL(cudaMalloc(&d_delta, sizeof(float)));

    CUDA_SAFE_CALL(cudaMemcpy(d_x, &x, sizeof(float), cudaMemcpyHostToDevice));
    CUDA_SAFE_CALL(cudaMemcpy(d_y, &y, sizeof(float), cudaMemcpyHostToDevice));

    snapkit_batch_eisenstein_snap(d_x, d_y, d_a, d_b, d_delta, 1, 0);

    CUDA_SAFE_CALL(cudaMemcpy(a, d_a, sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(b, d_b, sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_SAFE_CALL(cudaMemcpy(delta, d_delta, sizeof(float), cudaMemcpyDeviceToHost));

    CUDA_SAFE_CALL(cudaFree(d_x));
    CUDA_SAFE_CALL(cudaFree(d_y));
    CUDA_SAFE_CALL(cudaFree(d_a));
    CUDA_SAFE_CALL(cudaFree(d_b));
    CUDA_SAFE_CALL(cudaFree(d_delta));
}

/* ======================================================================
 * Host API: Batch snap with integrated threshold (for fused pipeline)
 * ====================================================================== */

void snapkit_batch_snap_threshold(
    const float* points_x,
    const float* points_y,
    const float* tolerances,
    const int*   stream_ids,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int*   is_delta,
    float  default_tolerance,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    eisenstein_snap_threshold_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y,
        tolerances, stream_ids,
        out_a, out_b, out_delta, is_delta,
        default_tolerance, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Set up tolerances in constant memory
 * ====================================================================== */

void snapkit_set_stream_tolerances(
    const float* tolerances,
    int num_streams
) {
    float host_tolerances[SNAPKIT_MAX_STREAMS];
    for (int i = 0; i < SNAPKIT_MAX_STREAMS; i++) {
        host_tolerances[i] = (i < num_streams) ? tolerances[i] : SNAPKIT_DEFAULT_TOLERANCE;
    }

    CUDA_SAFE_CALL(cudaMemcpyToSymbol(
        snapkit_stream_tolerances,
        host_tolerances,
        SNAPKIT_MAX_STREAMS * sizeof(float)
    ));
}

/* ======================================================================
 * Host API: Set stream priorities in constant memory
 * ====================================================================== */

void snapkit_set_stream_priorities(
    const float* priorities,
    int num_streams
) {
    float host_priorities[SNAPKIT_MAX_STREAMS];
    for (int i = 0; i < SNAPKIT_MAX_STREAMS; i++) {
        host_priorities[i] = (i < num_streams) ? priorities[i] : 1.0f;
    }

    CUDA_SAFE_CALL(cudaMemcpyToSymbol(
        snapkit_stream_priorities,
        host_priorities,
        SNAPKIT_MAX_STREAMS * sizeof(float)
    ));
}
