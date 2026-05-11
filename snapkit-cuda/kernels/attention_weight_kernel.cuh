#ifndef SNAPKIT_ATTENTION_WEIGHT_KERNEL_CUH
#define SNAPKIT_ATTENTION_WEIGHT_KERNEL_CUH

/*
 * attention_weight_kernel.cuh — Actionability-weighted scoring
 *
 * "Cognition is finite. Attention is allocated proportionally to
 *  the magnitude of the felt delta AND the actionability of that delta."
 *
 * weight_i = delta_i × actionability_i × urgency_i  (if is_delta)
 *
 * This kernel computes the attention weight for every delta,
 * then selects the top-K for budget allocation.
 *
 * PTX features: fma.rn.f32 for weighted scoring, selp for conditional
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "reduce.cuh"

/* ======================================================================
 * Compute attention weights
 *
 * If a point is a delta, weight = delta × actionability × urgency.
 * If not a delta, weight = 0.
 * ====================================================================== */

__global__ void compute_attention_weights_kernel(
    const float* __restrict__ deltas,
    const int*   __restrict__ is_delta,
    const float* __restrict__ actionability,
    const float* __restrict__ urgency,
    float* __restrict__ weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    if (is_delta[idx]) {
        float w = deltas[idx];
        if (actionability) w *= actionability[idx];
        if (urgency)       w *= urgency[idx];
        weights[idx] = w;
    } else {
        weights[idx] = 0.0f;
    }
}

/* ======================================================================
 * Compute attention weights with PTX FMA
 * ====================================================================== */

__global__ void compute_attention_weights_ptx_kernel(
    const float* __restrict__ deltas,
    const int*   __restrict__ is_delta,
    const float* __restrict__ actionability,
    const float* __restrict__ urgency,
    float* __restrict__ weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    float w;
    int is_d = is_delta[idx];

    if (is_d) {
        float d = deltas[idx];

        /* weight = delta × actionability × urgency */
        if (actionability) {
            asm volatile("fma.rn.f32 %0, %1, %2, %3;"
                        : "=f"(w) : "f"(d), "f"(actionability[idx]), "f"(0.0f));
        } else {
            w = d;
        }

        if (urgency) {
            /* FMA: w = w * urgency + 0 */
            asm volatile("fma.rn.f32 %0, %1, %2, %3;"
                        : "=f"(w) : "f"(w), "f"(urgency[idx]), "f"(0.0f));
        }

        weights[idx] = w;
    } else {
        weights[idx] = 0.0f;
    }
}

/* ======================================================================
 * Attention Budget Allocator
 *
 * Allocates a fixed total budget proportionally to weights.
 *
 *   alloc_i = total_budget × weight_i / sum(weights)
 *
 * Uses a two-pass approach:
 *   1. Compute sum of weights (parallel reduction)
 *   2. Scale each weight by total_budget / sum
 * ====================================================================== */

__global__ void attention_budget_allocator_kernel(
    const float* __restrict__ weights,
    const int*   __restrict__ is_delta,
    float* __restrict__ allocations,
    float   total_budget,
    float   global_sum,
    int     N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    if (is_delta[idx] && global_sum > 0.0f) {
        float alloc = total_budget * weights[idx] / global_sum;
        allocations[idx] = alloc;
    } else {
        allocations[idx] = 0.0f;
    }
}

/* ======================================================================
 * Stream-Level Attention Allocation
 *
 * Allocates budget per stream, then distributes within each stream.
 * ====================================================================== */

__global__ void attention_per_stream_kernel(
    const float* __restrict__ weights,
    const int*   __restrict__ is_delta,
    const int*   __restrict__ stream_ids,
    const float* __restrict__ stream_budgets,
    float* __restrict__ allocations,
    int     N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    if (is_delta[idx]) {
        int sid = stream_ids[idx];
        float w = weights[idx];
        float budget = stream_budgets[sid];
        allocations[idx] = budget * w;  /* Simple: weight × stream budget */
    } else {
        allocations[idx] = 0.0f;
    }
}

/* ======================================================================
 * Top-K Attention Selection (Warp-Level)
 *
 * Finds top-K deltas (by attention weight) using per-thread heaps
 * and warp-level merge. K ≤ 32.
 * ====================================================================== */

__global__ void top_k_attention_kernel(
    const float* __restrict__ weights,
    const int*   __restrict__ is_delta,
    int*  __restrict__ top_indices,
    float* __restrict__ top_weights,
    int*  __restrict__ top_stream_ids,
    const int* __restrict__ stream_ids,
    int    K,
    int    N
) {
    if (K > SNAPKIT_WARP_SIZE) return;

    extern __shared__ float s_heap[];
    int* s_heap_idx = (int*)&s_heap[K * blockDim.x];

    int tid = threadIdx.x;

    /* Per-thread min-heap */
    float local_heap[SNAPKIT_WARP_SIZE];
    int   local_idx[SNAPKIT_WARP_SIZE];
    #pragma unroll
    for (int i = 0; i < K; i++) {
        local_heap[i] = -1e10f;
        local_idx[i]  = -1;
    }

    /* Grid-stride loop */
    int stride = gridDim.x * blockDim.x;
    for (int idx = blockIdx.x * blockDim.x + tid;
         idx < N;
         idx += stride) {
        if (is_delta[idx]) {
            float w = weights[idx];
            /* Heap push */
            if (w > local_heap[0]) {
                local_heap[0] = w;
                local_idx[0] = idx;
                /* Bubble down (min-heap) */
                int pos = 0;
                while (1) {
                    int smallest = pos;
                    int left  = 2 * pos + 1;
                    int right = 2 * pos + 2;
                    if (left < K && local_heap[left] < local_heap[smallest])
                        smallest = left;
                    if (right < K && local_heap[right] < local_heap[smallest])
                        smallest = right;
                    if (smallest == pos) break;
                    float tf = local_heap[pos];
                    int   ti = local_idx[pos];
                    local_heap[pos] = local_heap[smallest];
                    local_idx[pos] = local_idx[smallest];
                    local_heap[smallest] = tf;
                    local_idx[smallest] = ti;
                    pos = smallest;
                }
            }
        }
    }

    /* Store in shared memory */
    for (int i = 0; i < K; i++) {
        s_heap[tid * K + i] = local_heap[i];
        s_heap_idx[tid * K + i] = local_idx[i];
    }
    __syncthreads();

    /* Block-level merge (first warp) */
    int num_threads = min(blockDim.x, (N - blockIdx.x * blockDim.x));
    int lane = tid % SNAPKIT_WARP_SIZE;
    int warp_id = tid / SNAPKIT_WARP_SIZE;

    if (warp_id == 0) {
        float global_heap[SNAPKIT_WARP_SIZE];
        int   global_idx[SNAPKIT_WARP_SIZE];
        #pragma unroll
        for (int i = 0; i < K; i++) {
            global_heap[i] = s_heap[lane * K + i];
            global_idx[i]  = s_heap_idx[lane * K + i];
        }

        for (int t = SNAPKIT_WARP_SIZE; t < num_threads; t++) {
            for (int i = 0; i < K; i++) {
                float val = s_heap[t * K + i];
                int   idx = s_heap_idx[t * K + i];
                if (idx >= 0 && val > global_heap[0]) {
                    global_heap[0] = val;
                    global_idx[0] = idx;
                    int pos = 0;
                    while (1) {
                        int smallest = pos;
                        int left  = 2 * pos + 1;
                        int right = 2 * pos + 2;
                        if (left < K && global_heap[left] < global_heap[smallest])
                            smallest = left;
                        if (right < K && global_heap[right] < global_heap[smallest])
                            smallest = right;
                        if (smallest == pos) break;
                        float tf = global_heap[pos];
                        int   ti = global_idx[pos];
                        global_heap[pos] = global_heap[smallest];
                        global_idx[pos] = global_idx[smallest];
                        global_heap[smallest] = tf;
                        global_idx[smallest] = ti;
                        pos = smallest;
                    }
                }
            }
        }

        /* Sort descending */
        for (int i = 0; i < K - 1; i++) {
            for (int j = 0; j < K - 1 - i; j++) {
                if (global_heap[j] < global_heap[j + 1]) {
                    float tf = global_heap[j];
                    int ti   = global_idx[j];
                    global_heap[j] = global_heap[j + 1];
                    global_idx[j] = global_idx[j + 1];
                    global_heap[j + 1] = tf;
                    global_idx[j + 1] = ti;
                }
            }
        }

        if (lane == 0) {
            for (int i = 0; i < K; i++) {
                top_indices[i] = global_idx[i];
                top_weights[i] = global_heap[i];
                if (top_stream_ids && global_idx[i] >= 0) {
                    top_stream_ids[i] = stream_ids[global_idx[i]];
                }
            }
        }
    }
}

#endif /* SNAPKIT_ATTENTION_WEIGHT_KERNEL_CUH */
