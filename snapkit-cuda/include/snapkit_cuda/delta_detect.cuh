#ifndef SNAPKIT_DELTA_DETECT_CUH
#define SNAPKIT_DELTA_DETECT_CUH

/*
 * delta_detect.cuh — Parallel delta detection kernels
 *
 * "The delta is the compass needle. It points attention toward the part
 * of the information landscape where thinking can make the most difference."
 *
 * Implements:
 * - Per-point delta threshold detection (tolerance check)
 * - Warp-level reduction for delta counting
 * - Block-level aggregation for statistics
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* ======================================================================
 * Simple Delta Threshold Detection
 *
 * Marks each point as delta or not based on per-stream tolerance.
 * Memory-bound kernel (~187 GB/s on RTX 4050 → ~3B deltas/sec).
 * ====================================================================== */

__global__ void delta_threshold_kernel(
    const float* __restrict__ deltas,
    const float* __restrict__ tolerances,
    const int*   __restrict__ stream_ids,
    int*  __restrict__ is_delta,
    float* __restrict__ attention_weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        float delta = deltas[idx];
        int sid = stream_ids[idx];
        float tol = tolerances[sid];

        int exceeds = (delta > tol) ? 1 : 0;
        is_delta[idx] = exceeds;

        /* Attention weight = delta (if delta), else 0 */
        attention_weights[idx] = exceeds ? delta : 0.0f;
    }
}

/* ======================================================================
 * Delta Threshold with Actionability and Urgency
 *
 * Weight = delta × actionability × urgency (only if exceeds tolerance)
 * ====================================================================== */

__global__ void delta_threshold_weighted_kernel(
    const float* __restrict__ deltas,
    const float* __restrict__ tolerances,
    const int*   __restrict__ stream_ids,
    const float* __restrict__ actionability,
    const float* __restrict__ urgency,
    int*  __restrict__ is_delta,
    float* __restrict__ attention_weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        float delta = deltas[idx];
        int sid = stream_ids[idx];
        float tol = tolerances[sid];

        int exceeds = (delta > tol) ? 1 : 0;
        is_delta[idx] = exceeds;

        if (exceeds) {
            float w = delta;
            if (actionability) w *= actionability[idx];
            if (urgency)       w *= urgency[idx];
            attention_weights[idx] = w;
        } else {
            attention_weights[idx] = 0.0f;
        }
    }
}

/* ======================================================================
 * Warp-Level Delta Reduction
 *
 * Counts deltas per warp using __shfl_down_sync.
 * Returns tuple: (delta_count, max_delta) for the warp.
 * ====================================================================== */

__device__ __forceinline__
void warp_delta_reduce(
    float delta,
    int   is_delta,
    int*  out_count,
    float* out_max_delta
) {
    unsigned mask = 0xFFFFFFFF;

    /* Warp-level sum for count */
    int count = is_delta;
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        count += __shfl_down_sync(mask, count, offset);
    }

    /* Warp-level max for max delta */
    float max_d = delta * is_delta;
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        float other = __shfl_down_sync(mask, max_d, offset);
        max_d = fmaxf(max_d, other);
    }

    /* Warp lane 0 holds the result */
    if (threadIdx.x % SNAPKIT_WARP_SIZE == 0) {
        *out_count = count;
        *out_max_delta = max_d;
    }
}

/* ======================================================================
 * Block-Level Delta Reduction
 *
 * Aggregates warp results into block-wide totals.
 * Uses shared memory for warp-to-block reduction.
 * ====================================================================== */

__global__ void delta_reduce_kernel(
    const float* __restrict__ deltas,
    const int*   __restrict__ is_delta,
    int    N,
    int*   out_total_deltas,
    float* out_max_delta,
    float* out_sum_delta
) {
    __shared__ int    s_counts[32];     /* Max 32 warps per block (1024 threads) */
    __shared__ float  s_maxes[32];
    __shared__ float  s_sums[32];

    int tid = threadIdx.x;
    int idx = blockIdx.x * blockDim.x + tid;

    float delta = (idx < N) ? deltas[idx] : 0.0f;
    int   is_d  = (idx < N) ? is_delta[idx] : 0;

    /* Warp-level reduction */
    int    warp_count = 0;
    float  warp_max   = 0.0f;
    warp_delta_reduce(delta, is_d, &warp_count, &warp_max);

    /* Warp sum */
    unsigned mask = 0xFFFFFFFF;
    float sum_d = delta * is_d;
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        sum_d += __shfl_down_sync(mask, sum_d, offset);
    }

    /* Lane 0 of each warp writes to shared memory */
    int warp_id = tid / SNAPKIT_WARP_SIZE;
    if (tid % SNAPKIT_WARP_SIZE == 0) {
        s_counts[warp_id] = warp_count;
        s_maxes[warp_id] = warp_max;
        s_sums[warp_id] = sum_d;
    }
    __syncthreads();

    /* Final reduction by first warp */
    if (warp_id == 0) {
        int    total_count = 0;
        float  total_max   = 0.0f;
        float  total_sum   = 0.0f;

        int num_warps = (blockDim.x + SNAPKIT_WARP_SIZE - 1) / SNAPKIT_WARP_SIZE;
        for (int w = 0; w < num_warps; w++) {
            total_count += s_counts[w];
            total_max   = fmaxf(total_max, s_maxes[w]);
            total_sum   += s_sums[w];
        }

        /* Atomic add to global counters */
        if (tid == 0) {
            if (out_total_deltas) atomicAdd(out_total_deltas, total_count);
            if (out_max_delta)    atomicMax((int*)out_max_delta, __float_as_int(total_max));
            if (out_sum_delta)    atomicAdd(out_sum_delta, total_sum);
        }
    }
}

/* ======================================================================
 * Delta Severity Classification
 *
 * Maps delta/tolerance ratio to severity levels.
 * ====================================================================== */

enum DeltaSeverity {
    SEVERITY_NONE     = 0,
    SEVERITY_LOW      = 1,
    SEVERITY_MEDIUM   = 2,
    SEVERITY_HIGH     = 3,
    SEVERITY_CRITICAL = 4
};

__device__ __forceinline__
int delta_severity(float delta, float tolerance) {
    float ratio = delta / tolerance;
    if (ratio <= 1.0f)  return SEVERITY_NONE;
    if (ratio <= 1.5f)  return SEVERITY_LOW;
    if (ratio <= 3.0f)  return SEVERITY_MEDIUM;
    if (ratio <= 5.0f)  return SEVERITY_HIGH;
    return SEVERITY_CRITICAL;
}

#endif /* SNAPKIT_DELTA_DETECT_CUH */
