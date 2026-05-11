/*
 * delta_detect.cu — Parallel delta detection implementation
 *
 * "The delta is the compass needle. It points attention toward the part
 * of the information landscape where thinking can make the most difference."
 *
 * Implements host API for threshold detection, severity classification,
 * and stream-level delta counting.
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "delta_detect.cuh"
#include "kernels/delta_threshold_kernel.cuh"

/* ======================================================================
 * Host API: Delta threshold detection
 * ====================================================================== */

void snapkit_delta_threshold(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    int*   is_delta,
    float* attention_weights,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_threshold_kernel<<<grid_size, block_size, 0, stream>>>(
        deltas, tolerances, stream_ids,
        is_delta, attention_weights, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Delta threshold with actionability & urgency weighting
 * ====================================================================== */

void snapkit_delta_threshold_weighted(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    const float* actionability,
    const float* urgency,
    int*   is_delta,
    float* attention_weights,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_threshold_weighted_ptx_kernel<<<grid_size, block_size, 0, stream>>>(
        deltas, tolerances, stream_ids,
        actionability, urgency,
        is_delta, attention_weights, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Delta reduction (count, max, sum)
 * ====================================================================== */

void snapkit_delta_reduce(
    const float* deltas,
    const int*   is_delta,
    int    N,
    int*   total_deltas,
    float* max_delta,
    float* sum_delta,
    cudaStream_t stream
) {
    if (N <= 0) {
        if (total_deltas) *total_deltas = 0;
        if (max_delta)    *max_delta = 0.0f;
        if (sum_delta)    *sum_delta = 0.0f;
        return;
    }

    /* Allocate device outputs */
    int   *d_total = NULL;
    float *d_max   = NULL;
    float *d_sum   = NULL;

    if (total_deltas) CUDA_SAFE_CALL(cudaMallocAsync(&d_total, sizeof(int), stream));
    if (max_delta)    CUDA_SAFE_CALL(cudaMallocAsync(&d_max, sizeof(float), stream));
    if (sum_delta)    CUDA_SAFE_CALL(cudaMallocAsync(&d_sum, sizeof(float), stream));

    if (d_total) CUDA_SAFE_CALL(cudaMemsetAsync(d_total, 0, sizeof(int), stream));
    if (d_max)   CUDA_SAFE_CALL(cudaMemsetAsync(d_max, 0, sizeof(float), stream));
    if (d_sum)   CUDA_SAFE_CALL(cudaMemsetAsync(d_sum, 0, sizeof(float), stream));

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_reduce_kernel<<<grid_size, block_size, 0, stream>>>(
        deltas, is_delta, N, d_total, d_max, d_sum
    );

    if (total_deltas) {
        CUDA_SAFE_CALL(cudaMemcpyAsync(total_deltas, d_total, sizeof(int),
                                        cudaMemcpyDeviceToHost, stream));
    }
    if (max_delta) {
        int tmp_int;
        CUDA_SAFE_CALL(cudaMemcpyAsync(&tmp_int, d_max, sizeof(int),
                                        cudaMemcpyDeviceToHost, stream));
        /* Need to sync to read max correctly */
        CUDA_SAFE_CALL(cudaStreamSynchronize(stream));
        *max_delta = __int_as_float(tmp_int);
    } else {
        CUDA_SAFE_CALL(cudaStreamSynchronize(stream));
    }
    if (sum_delta) {
        CUDA_SAFE_CALL(cudaMemcpyAsync(sum_delta, d_sum, sizeof(float),
                                        cudaMemcpyDeviceToHost, stream));
    }

    if (d_total) CUDA_SAFE_CALL(cudaFreeAsync(d_total, stream));
    if (d_max)   CUDA_SAFE_CALL(cudaFreeAsync(d_max, stream));
    if (d_sum)   CUDA_SAFE_CALL(cudaFreeAsync(d_sum, stream));
}

/* ======================================================================
 * Host API: Count deltas per stream
 * ====================================================================== */

void snapkit_delta_stream_counts(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    int*   stream_delta_counts,
    float* stream_delta_sums,
    int    N,
    int    num_streams,
    cudaStream_t stream
) {
    if (N <= 0 || num_streams <= 0) return;

    /* Initialize output arrays */
    CUDA_SAFE_CALL(cudaMemsetAsync(stream_delta_counts, 0,
                                    num_streams * sizeof(int), stream));
    if (stream_delta_sums) {
        CUDA_SAFE_CALL(cudaMemsetAsync(stream_delta_sums, 0,
                                        num_streams * sizeof(float), stream));
    }

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_count_per_stream_kernel<<<grid_size, block_size, 0, stream>>>(
        deltas, tolerances, stream_ids,
        stream_delta_counts, stream_delta_sums,
        N, num_streams
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Delta stream summary (aggregated statistics)
 * ====================================================================== */

void snapkit_delta_stream_summary(
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
    if (N <= 0) return;

    CUDA_SAFE_CALL(cudaMemsetAsync(stream_counts, 0, num_streams * sizeof(int), stream));
    if (stream_sums)  CUDA_SAFE_CALL(cudaMemsetAsync(stream_sums, 0, num_streams * sizeof(float), stream));
    if (stream_maxes) CUDA_SAFE_CALL(cudaMemsetAsync(stream_maxes, 0, num_streams * sizeof(float), stream));

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_stream_summary_kernel<<<grid_size, block_size, 0, stream>>>(
        deltas, is_delta, stream_ids,
        stream_counts, stream_sums, stream_maxes,
        N, num_streams
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Delta severity classification
 * ====================================================================== */

void snapkit_delta_classify_severity(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    int*   is_delta,
    int*   severity,
    float* attention_weights,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    delta_severity_classify_kernel<<<grid_size, block_size, 0, stream>>>(
        deltas, tolerances, stream_ids,
        is_delta, severity, attention_weights, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}
