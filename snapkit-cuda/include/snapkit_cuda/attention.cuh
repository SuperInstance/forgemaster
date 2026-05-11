#ifndef SNAPKIT_ATTENTION_CUH
#define SNAPKIT_ATTENTION_CUH

/*
 * attention.cuh — GPU attention budget allocation
 *
 * "Cognition is finite. The snap functions serve as gatekeepers of a
 *  finite attention budget. Attention is allocated proportionally to
 *  the magnitude of the felt delta AND the actionability of that delta."
 *
 * Implements:
 * - Actionability-weighted attention scoring
 * - Top-K delta selection via sort or bitonic selection
 * - Attention budget allocation across streams
 *
 * The pipeline:
 *   deltas → threshold → weight(δ, actionability, urgency) → top-K → allocate
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* ======================================================================
 * Attention Weighted Scoring
 *
 * weight_i = delta_i * actionability_i * urgency_i  (if is_delta)
 * weight_i = 0                                      (if not delta)
 * ====================================================================== */

__global__ void attention_weight_kernel(
    const float* __restrict__ deltas,
    const int*   __restrict__ is_delta,
    const float* __restrict__ actionability,
    const float* __restrict__ urgency,
    float* __restrict__ attention_weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        if (is_delta[idx]) {
            float w = deltas[idx];
            if (actionability) w *= actionability[idx];
            if (urgency)       w *= urgency[idx];
            attention_weights[idx] = w;
        } else {
            attention_weights[idx] = 0.0f;
        }
    }
}

/* ======================================================================
 * Attention Budget Allocation
 *
 * Allocates a fixed total budget proportionally to attention weights.
 * weight_i = delta_i * actionability_i * urgency_i
 * alloc_i = total_budget * weight_i / sum(weights)
 * ====================================================================== */

__global__ void attention_budget_kernel(
    const float* __restrict__ attention_weights,
    const int*   __restrict__ is_delta,
    float* __restrict__ allocations,
    float   total_budget,
    int     N
) {
    extern __shared__ float s_weights[];

    int tid  = threadIdx.x;
    int idx  = blockIdx.x * blockDim.x + tid;

    /* Load weight with clamping for non-deltas */
    float w = (idx < N && is_delta[idx]) ? attention_weights[idx] : 0.0f;
    s_weights[tid] = w;
    __syncthreads();

    /* Block-level sum of weights */
    #pragma unroll
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            s_weights[tid] += s_weights[tid + s];
        }
        __syncthreads();
    }

    float block_sum = s_weights[0];

    /* Atomic add to global sum */
    __shared__ float global_sum;
    if (tid == 0) {
        atomicAdd(&global_sum, block_sum);
    }
    __syncthreads();

    /* Allocate proportionally */
    if (idx < N && is_delta[idx]) {
        float sum = global_sum;
        if (sum > 0.0f) {
            allocations[idx] = total_budget * attention_weights[idx] / sum;
        } else {
            allocations[idx] = 0.0f;
        }
    }
}

/* ======================================================================
 * Top-K Delta Selection
 *
 * Finds the K largest deltas by attention weight.
 * Uses a shared-memory heap per block, then warp-level merge.
 *
 * For small K (<= 32), uses warp-level selection.
 * For larger K, uses block-level partial sort.
 * ====================================================================== */

/* Per-thread min-heap for top-K (K <= 32) */
__device__ __forceinline__
void heap_push(float* heap, int K, float value, int* heap_idx, int idx) {
    /* Insert at bottom, bubble up */
    if (value > heap[0]) {
        heap[0] = value;
        heap_idx[0] = idx;

        /* Bubble down (min-heap: smallest at root) */
        int pos = 0;
        while (1) {
            int smallest = pos;
            int left  = 2 * pos + 1;
            int right = 2 * pos + 2;

            if (left < K && heap[left] < heap[smallest])
                smallest = left;
            if (right < K && heap[right] < heap[smallest])
                smallest = right;

            if (smallest == pos) break;

            /* Swap */
            float tmp_f = heap[pos];
            int   tmp_i = heap_idx[pos];
            heap[pos] = heap[smallest];
            heap_idx[pos] = heap_idx[smallest];
            heap[smallest] = tmp_f;
            heap_idx[smallest] = tmp_i;

            pos = smallest;
        }
    }
}

/* Block-level top-K using shared memory */
__global__ void top_k_deltas_kernel(
    const float* __restrict__ weights,
    int*  __restrict__ top_indices,
    float* __restrict__ top_weights,
    int    K,
    int    N
) {
    /* K must be <= SNAPKIT_WARP_SIZE for this simple implementation */
    if (K > SNAPKIT_WARP_SIZE) return;

    extern __shared__ float s_heap[];
    int* s_heap_idx = (int*)&s_heap[K * blockDim.x];

    int tid = threadIdx.x;

    /* Initialize local heap */
    float local_heap[SNAPKIT_WARP_SIZE];
    int   local_idx[SNAPKIT_WARP_SIZE];
    #pragma unroll
    for (int i = 0; i < K; i++) {
        local_heap[i] = -1e10f;
        local_idx[i]  = -1;
    }

    /* Process points assigned to this thread via grid-stride loop */
    int stride = gridDim.x * blockDim.x;
    for (int idx = blockIdx.x * blockDim.x + tid;
         idx < N;
         idx += stride) {
        float w = weights[idx];
        if (w > 0.0f) {
            heap_push(local_heap, K, w, local_idx, idx);
        }
    }

    /* Store local heaps in shared memory */
    for (int i = 0; i < K; i++) {
        s_heap[tid * K + i] = local_heap[i];
        s_heap_idx[tid * K + i] = local_idx[i];
    }
    __syncthreads();

    /* Warp-level merge of heaps */
    /* For simplicity, last active warp does the final merge */
    int num_threads = min(blockDim.x, (N - blockIdx.x * blockDim.x));
    int warp_id = tid / SNAPKIT_WARP_SIZE;
    int lane    = tid % SNAPKIT_WARP_SIZE;

    if (warp_id == 0) {
        /* Initialize global heap from first thread's heap */
        float global_heap[SNAPKIT_WARP_SIZE];
        int   global_idx[SNAPKIT_WARP_SIZE];
        #pragma unroll
        for (int i = 0; i < K; i++) {
            global_heap[i] = s_heap[lane * K + i];
            global_idx[i]  = s_heap_idx[lane * K + i];
        }

        /* Merge remaining threads */
        for (int t = SNAPKIT_WARP_SIZE; t < num_threads; t++) {
            for (int i = 0; i < K; i++) {
                float val = s_heap[t * K + i];
                int   idx = s_heap_idx[t * K + i];
                if (idx >= 0) {
                    heap_push(global_heap, K, val, global_idx, idx);
                }
            }
        }

        /* Sort final heap descending for output */
        /* Simple bubble sort on K elements */
        for (int i = 0; i < K - 1; i++) {
            for (int j = 0; j < K - 1 - i; j++) {
                if (global_heap[j] < global_heap[j + 1]) {
                    float tmp_f = global_heap[j];
                    int   tmp_i = global_idx[j];
                    global_heap[j] = global_heap[j + 1];
                    global_idx[j] = global_idx[j + 1];
                    global_heap[j + 1] = tmp_f;
                    global_idx[j + 1] = tmp_i;
                }
            }
        }

        /* Write output (thread 0 writes all K) */
        if (lane == 0) {
            for (int i = 0; i < K; i++) {
                top_indices[i] = global_idx[i];
                top_weights[i] = global_heap[i];
            }
        }
    }
}

/* ======================================================================
 * Top-K with Radix Sort (for large K)
 *
 * For K > warp size, uses a radix-sort-based approach.
 * ====================================================================== */

__global__ void top_k_radix_kernel(
    const float* __restrict__ weights,
    int*  __restrict__ sorted_indices,
    float* __restrict__ sorted_weights,
    int    K,
    int    N
) {
    /* Placeholder for radix-sort based top-K.
     * Full radix sort implementation is in reduce.cuh.
     * This kernel filters non-delta entries then delegates to sort. */
    extern __shared__ int s_indices[];
    float* s_weights = (float*)s_indices;
    int* s_src = &s_indices[blockDim.x];

    int tid = threadIdx.x;
    int idx = blockIdx.x * blockDim.x + tid;

    /* Load and filter */
    float w = (idx < N) ? weights[idx] : 0.0f;
    int is_active = (idx < N && w > 0.0f) ? 1 : 0;

    s_weights[tid] = w;
    s_src[tid] = idx;
    __syncthreads();

    /* For now: write first N to output, sorted at caller level */
    if (idx < N && w > 0.0f && idx < K) {
        sorted_weights[idx] = w;
        sorted_indices[idx] = idx;
    }
}

#endif /* SNAPKIT_ATTENTION_CUH */
