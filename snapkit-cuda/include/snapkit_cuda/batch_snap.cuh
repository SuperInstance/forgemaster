#ifndef SNAPKIT_BATCH_SNAP_CUH
#define SNAPKIT_BATCH_SNAP_CUH

/*
 * batch_snap.cuh — Batch snap kernels for multi-stream processing
 *
 * Extends the single-point Eisenstein snap to batched processing
 * across multiple streams with per-stream configurations.
 * Supports: SoA layout, coalesced memory, grid-stride loops.
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "eisenstein_snap.cuh"

/* ======================================================================
 * Multi-Stream Batch Snap
 *
 * Each point has a stream_id that determines its snap configuration.
 * Stream parameters stored in constant memory for fast access.
 * ====================================================================== */

__constant__ float snapkit_stream_tolerances[SNAPKIT_MAX_STREAMS];
__constant__ float snapkit_stream_priorities[SNAPKIT_MAX_STREAMS];

/**
 * Initialize constant memory with stream configurations.
 * Must be called once per pipeline configuration.
 */
__host__ void snapkit_init_stream_constants(
    const snapkit_stream_config_t* configs,
    int num_streams
) {
    float tolerances[SNAPKIT_MAX_STREAMS];
    float priorities[SNAPKIT_MAX_STREAMS];

    for (int i = 0; i < SNAPKIT_MAX_STREAMS; i++) {
        if (i < num_streams) {
            tolerances[i] = configs[i].tolerance;
            priorities[i] = configs[i].priority_weight;
        } else {
            tolerances[i] = SNAPKIT_DEFAULT_TOLERANCE;
            priorities[i] = 1.0f;
        }
    }

    CUDA_SAFE_CALL(cudaMemcpyToSymbol(
        snapkit_stream_tolerances, tolerances,
        SNAPKIT_MAX_STREAMS * sizeof(float)
    ));
    CUDA_SAFE_CALL(cudaMemcpyToSymbol(
        snapkit_stream_priorities, priorities,
        SNAPKIT_MAX_STREAMS * sizeof(float)
    ));
}

/* ======================================================================
 * Batch Snap with Per-Stream Tolerance
 *
 * Each point snaps to the Eisenstein lattice, but delta computation
 * uses the per-stream tolerance for threshold detection.
 * ====================================================================== */

__global__ void batch_snap_with_tolerances_kernel(
    const float* __restrict__ points_x,
    const float* __restrict__ points_y,
    const int*   __restrict__ stream_ids,
    int*  __restrict__ out_a,
    int*  __restrict__ out_b,
    float* __restrict__ out_delta,
    int*  __restrict__ is_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        float x = points_x[idx];
        float y = points_y[idx];
        int sid = stream_ids[idx];

        int a, b;
        float delta;
        eisenstein_snap_point(x, y, &a, &b, &delta);

        out_a[idx] = a;
        out_b[idx] = b;
        out_delta[idx] = delta;

        /* Apply per-stream tolerance */
        float tol = snapkit_stream_tolerances[sid];
        is_delta[idx] = (delta > tol) ? 1 : 0;
    }
}

/* ======================================================================
 * Grid-Stride Batch Snap
 *
 * Allows processing more points than threads (grid-stride loop).
 * Useful for very large batches (> 256M points).
 * ====================================================================== */

__global__ void batch_snap_grid_stride_kernel(
    const float* __restrict__ points_x,
    const float* __restrict__ points_y,
    int*  __restrict__ out_a,
    int*  __restrict__ out_b,
    float* __restrict__ out_delta,
    int    N
) {
    int stride = gridDim.x * blockDim.x;
    for (int idx = blockIdx.x * blockDim.x + threadIdx.x;
         idx < N;
         idx += stride) {
        eisenstein_snap_fast(
            points_x[idx], points_y[idx],
            &out_a[idx], &out_b[idx], &out_delta[idx]
        );
    }
}

/* ======================================================================
 * Batch Snap with 2D Grid
 *
 * For 2D batches (e.g., N × M points), uses 2D block/grid indexing.
 * Each block processes one row of N points.
 * ====================================================================== */

__global__ void batch_snap_2d_kernel(
    const float* __restrict__ points_x,   /* N × M, row-major */
    const float* __restrict__ points_y,   /* N × M, row-major */
    int*  __restrict__ out_a,
    int*  __restrict__ out_b,
    float* __restrict__ out_delta,
    int    M,    /* points per stream */
    int    streams
) {
    int sid   = blockIdx.x;
    int point = blockIdx.y * blockDim.x + threadIdx.x;

    if (sid < streams && point < M) {
        int idx = sid * M + point;
        eisenstein_snap_fast(
            points_x[idx], points_y[idx],
            &out_a[idx], &out_b[idx], &out_delta[idx]
        );
    }
}

/* ======================================================================
 * Launch helper functions
 * ====================================================================== */

__host__ inline dim3 batch_snap_grid(int N, int block_size) {
    int grid = (N + block_size - 1) / block_size;
    grid = min(grid, 65535);  /* CUDA max grid dim */
    return dim3(grid);
}

__host__ inline int batch_snap_block_size() {
    return 256;  /* Good occupancy for simple arithmetic kernels */
}

#endif /* SNAPKIT_BATCH_SNAP_CUH */
