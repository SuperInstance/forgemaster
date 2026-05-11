/*
 * reduce.cu — Custom reduction kernels for delta aggregation
 *
 * Implements parallel reduction and top-K selection:
 * - Warp-level shuffle reduction (fastest path)
 * - Shared memory block reduction
 * - Bitonic sort for top-K
 * - Stream-level delta aggregation
 *
 * All operations are deterministic.
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "reduce.cuh"

/* ======================================================================
 * Host API: Delta sum reduction
 * ====================================================================== */

void snapkit_reduce_sum(
    const float* values,
    float* sum_out,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) {
        *sum_out = 0.0f;
        return;
    }

    float *d_sum;
    CUDA_SAFE_CALL(cudaMallocAsync(&d_sum, sizeof(float), stream));
    CUDA_SAFE_CALL(cudaMemsetAsync(d_sum, 0, sizeof(float), stream));

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_sum_kernel<<<grid_size, block_size, 0, stream>>>(
        values, NULL, d_sum, NULL, NULL, N
    );

    CUDA_SAFE_CALL(cudaMemcpyAsync(sum_out, d_sum, sizeof(float),
                                    cudaMemcpyDeviceToHost, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_sum, stream));
    CUDA_SAFE_CALL(cudaStreamSynchronize(stream));
}

/* ======================================================================
 * Host API: Argmax (find index of maximum value)
 * ====================================================================== */

int snapkit_argmax(
    const float* values,
    float* max_value,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) {
        if (max_value) *max_value = 0.0f;
        return -1;
    }

    int *d_idx;
    float *d_val;

    CUDA_SAFE_CALL(cudaMallocAsync(&d_idx, sizeof(int), stream));
    CUDA_SAFE_CALL(cudaMallocAsync(&d_val, sizeof(float), stream));

    int block_size = 1024;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    argmax_kernel<<<grid_size, block_size, 0, stream>>>(
        values, d_idx, d_val, N
    );

    int result_idx;
    float result_val;

    CUDA_SAFE_CALL(cudaMemcpyAsync(&result_idx, d_idx, sizeof(int),
                                    cudaMemcpyDeviceToHost, stream));
    CUDA_SAFE_CALL(cudaMemcpyAsync(&result_val, d_val, sizeof(float),
                                    cudaMemcpyDeviceToHost, stream));

    CUDA_SAFE_CALL(cudaFreeAsync(d_idx, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_val, stream));
    CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

    if (max_value) *max_value = result_val;
    return result_idx;
}

/* ======================================================================
 * Host API: Stream-level delta summary
 * ====================================================================== */

void snapkit_stream_delta_summary(
    const float* deltas,
    const int*   is_delta,
    const int*   stream_ids,
    int*   stream_counts,
    float* stream_sums,
    float* stream_maxes,
    int    N,
    int    num_streams,
    cudaStream_t stream
) {
    snapkit_delta_stream_summary(
        deltas, is_delta, stream_ids,
        stream_counts, stream_sums, stream_maxes,
        N, num_streams, stream
    );
}
