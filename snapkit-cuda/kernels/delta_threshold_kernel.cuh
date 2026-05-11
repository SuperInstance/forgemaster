#ifndef SNAPKIT_DELTA_THRESHOLD_KERNEL_CUH
#define SNAPKIT_DELTA_THRESHOLD_KERNEL_CUH

/*
 * delta_threshold_kernel.cuh — Parallel threshold detection
 *
 * "The delta is the compass needle. It points attention toward the part
 * of the information landscape where thinking can make the most difference."
 *
 * Each thread: checks one delta against its per-stream tolerance.
 * Memory-bound at ~187 GB/s → ~3B deltas/sec on RTX 4050.
 *
 * PTX features: ld.global.ca (coalesced L1), fma.rn.f32, setp (comparison)
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* ======================================================================
 * Simple Threshold: delta > tolerance → delta flag
 * ====================================================================== */

__global__ void delta_threshold_basic_kernel(
    const float* __restrict__ deltas,
    const float* __restrict__ tolerances,
    const int*   __restrict__ stream_ids,
    int*  __restrict__ is_delta,
    float* __restrict__ attention_weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    float delta = deltas[idx];
    int   sid   = stream_ids[idx];
    float tol   = tolerances[sid];

    int exceeds = (delta > tol) ? 1 : 0;
    is_delta[idx] = exceeds;
    attention_weights[idx] = exceeds ? delta : 0.0f;
}

/* ======================================================================
 * Threshold with Actionability and Urgency weighting
 *
 * weight = delta × actionability × urgency  (if exceeds tolerance, else 0)
 * ====================================================================== */

__global__ void delta_threshold_weighted_ptx_kernel(
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
    if (idx >= N) return;

    float delta = deltas[idx];
    int   sid   = stream_ids[idx];
    float tol   = tolerances[sid];

    int exceeds;
    asm volatile(
        "setp.gt.f32    %%p1, %1, %2;  \n\t"
        "selp.s32       %0,  1,  0, %%p1; \n\t"
        : "=r"(exceeds)
        : "f"(delta), "f"(tol)
        : "%p1"
    );

    is_delta[idx] = exceeds;

    /* Compute weight */
    if (exceeds) {
        float w = delta;
        if (actionability) {
            asm volatile("mul.f32 %0, %1, %2;" : "=f"(w) : "f"(w), "f"(actionability[idx]));
        }
        if (urgency) {
            asm volatile("mul.f32 %0, %1, %2;" : "=f"(w) : "f"(w), "f"(urgency[idx]));
        }
        attention_weights[idx] = w;
    } else {
        attention_weights[idx] = 0.0f;
    }
}

/* ======================================================================
 * Stream-Aware Delta Counting
 *
 * Counts deltas per stream in parallel. Uses atomic add per stream.
 * Good for streams ≤ 16 (atomic contention is low).
 * ====================================================================== */

__global__ void delta_count_per_stream_kernel(
    const float* __restrict__ deltas,
    const float* __restrict__ tolerances,
    const int*   __restrict__ stream_ids,
    int*  __restrict__ stream_delta_counts,
    float* __restrict__ stream_delta_sums,
    int    N,
    int    num_streams
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    float delta = deltas[idx];
    int   sid   = stream_ids[idx];
    float tol   = tolerances[sid];

    if (delta > tol) {
        atomicAdd(&stream_delta_counts[sid], 1);
        atomicAdd(&stream_delta_sums[sid], delta);
    }
}

/* ======================================================================
 * Adaptive Threshold: adjusts tolerance based on recent delta rate
 *
 * High delta rate → tighten tolerance (more attention)
 * Low delta rate → loosen tolerance (less attention)
 * ====================================================================== */

__constant__ float snapkit_adaptation_rates[SNAPKIT_MAX_STREAMS];
__constant__ float snapkit_target_delta_rates[SNAPKIT_MAX_STREAMS];

__global__ void delta_adaptive_threshold_kernel(
    const float* __restrict__ deltas,
    float* __restrict__ tolerances,        /* Writable — tolerance adaptation */
    const int*   __restrict__ stream_ids,
    const float* __restrict__ recent_delta_rates,
    int*  __restrict__ is_delta,
    float* __restrict__ attention_weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    float delta = deltas[idx];
    int   sid   = stream_ids[idx];
    float current_tol = tolerances[sid];
    float delta_rate  = recent_delta_rates[sid];
    float target_rate = snapkit_target_delta_rates[sid];
    float adapt_rate  = snapkit_adaptation_rates[sid];

    /* Adjust tolerance based on delta rate */
    if (delta_rate > target_rate * 1.5f) {
        /* Too many deltas → tighten tolerance */
        current_tol *= (1.0f - adapt_rate * 0.5f);
    } else if (delta_rate < target_rate * 0.5f) {
        /* Too few deltas → loosen tolerance */
        current_tol *= (1.0f + adapt_rate * 0.2f);
    }

    current_tol = fmaxf(current_tol, 1e-6f);
    tolerances[sid] = current_tol;

    int exceeds = (delta > current_tol) ? 1 : 0;
    is_delta[idx] = exceeds;
    attention_weights[idx] = exceeds ? delta : 0.0f;
}

/* ======================================================================
 * Multi-Severity Delta Classification
 *
 * Classifies each delta by severity: none/low/medium/high/critical
 * ====================================================================== */

__global__ void delta_severity_classify_kernel(
    const float* __restrict__ deltas,
    const float* __restrict__ tolerances,
    const int*   __restrict__ stream_ids,
    int*  __restrict__ is_delta,
    int*  __restrict__ severity,
    float* __restrict__ attention_weights,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    float delta = deltas[idx];
    int   sid   = stream_ids[idx];
    float tol   = tolerances[sid];

    float ratio = delta / fmaxf(tol, 1e-10f);

    int sev;
    if (ratio <= 1.0f) {
        sev = 0;  /* NONE */
        is_delta[idx] = 0;
        attention_weights[idx] = 0.0f;
    } else {
        is_delta[idx] = 1;
        if (ratio <= 1.5f)      sev = 1;  /* LOW */
        else if (ratio <= 3.0f) sev = 2;  /* MEDIUM */
        else if (ratio <= 5.0f) sev = 3;  /* HIGH */
        else                    sev = 4;  /* CRITICAL */

        attention_weights[idx] = delta * (1.0f + (float)sev * 0.25f);
    }

    severity[idx] = sev;
}

#endif /* SNAPKIT_DELTA_THRESHOLD_KERNEL_CUH */
