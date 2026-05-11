/*
 * batch_snap.cu — Batch snap kernel implementations
 *
 * Implements multi-stream batch snap processing.
 * Each point has a stream_id that determines its snap configuration.
 * Supports: SoA layout, coalesced memory, grid-stride loops, 2D batches.
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "batch_snap.cuh"
#include "kernels/eisenstein_snap_kernel.cuh"

/* ======================================================================
 * Host API: Multi-stream batch snap
 * ====================================================================== */

void snapkit_batch_snap_multi_stream(
    const float* points_x,
    const float* points_y,
    const int*   stream_ids,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int*   is_delta,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    batch_snap_with_tolerances_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y, stream_ids,
        out_a, out_b, out_delta, is_delta,
        N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Grid-stride batch snap for very large batches
 * ====================================================================== */

void snapkit_batch_snap_grid_stride(
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
    int grid_size  = min(512, (N + block_size - 1) / block_size);

    batch_snap_grid_stride_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y, out_a, out_b, out_delta, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: FP16 batch snap (half-precision input)
 * ====================================================================== */

void snapkit_batch_snap_fp16(
    const half* points_x,
    const half* points_y,
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

    eisenstein_snap_batch_fp16_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y, out_a, out_b, out_delta, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: 2D batch snap (streams × points)
 * ====================================================================== */

void snapkit_batch_snap_2d(
    const float* points_x,
    const float* points_y,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int    M,          /* Points per stream */
    int    num_streams,
    cudaStream_t stream
) {
    if (M <= 0 || num_streams <= 0) return;

    dim3 block(256);
    dim3 grid(num_streams, (M + 256 - 1) / 256);
    grid.y = min(grid.y, 65535u);

    batch_snap_2d_kernel<<<grid, block, 0, stream>>>(
        points_x, points_y, out_a, out_b, out_delta,
        M, num_streams
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}
