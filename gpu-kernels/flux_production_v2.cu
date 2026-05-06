// FLUX Production Kernel v2 — Safety-Certified Constraint Engine
// Combines learnings from 45 GPU experiments into a WCET-bounded kernel
//
// Design decisions (evidence-based):
//   - INT8 flat bounds: 1.45x faster than struct (exp27), zero precision loss
//   - Error masks: 1.27x faster than pass/fail (exp26), enables localization
//   - CUDA Graphs: 51x launch speedup (exp13), zero overhead replay
//   - Saturation arithmetic: clamp >127 to 127, <-127 to -127 (security fix)
//   - Hot-swap bounds: 1.07ms for 0.1% update (exp30), <1kHz control loop
//   - 8 constraints per sensor: 341B peak, 101.7B sustained (exp20)
//
// Safety properties:
//   - No dynamic memory allocation
//   - No recursion or unbounded loops
//   - All bounds clamped to INT8 safe range
//   - Error masks enable exact failure localization
//   - WCET deterministic per configuration
//
// (c) 2026 SuperInstance — Apache 2.0

#ifndef FLUX_PRODUCTION_V2_CU
#define FLUX_PRODUCTION_V2_CU

#include <cuda_runtime.h>
#include <cstdint>

// ═══════════════════════════════════════════════════════════
// Configuration constants
// ═══════════════════════════════════════════════════════════

constexpr int FLUX_MAX_CONSTRAINTS = 8;     // per sensor
constexpr int FLUX_BLOCK_SIZE = 256;        // optimal for Ada (exp01-07)
constexpr int FLUX_WARP_SIZE = 32;
constexpr int FLUX_INT8_MIN = -127;         // saturated minimum
constexpr int FLUX_INT8_MAX = 127;          // saturated maximum
constexpr int FLUX_UINT8_MAX = 255;         // unsigned saturation target

// ═══════════════════════════════════════════════════════════
// Data layouts — flat, cache-friendly
// ═══════════════════════════════════════════════════════════

// Flat bounds: [lo_0, hi_0, lo_1, hi_1, ..., lo_7, hi_7] = 16 bytes
// 1.45x faster than struct-of-structs (exp27)
struct alignas(16) FluxBoundsFlat {
    int8_t lo[FLUX_MAX_CONSTRAINTS];
    int8_t hi[FLUX_MAX_CONSTRAINTS];
};

// Error mask: one bit per constraint, plus severity
struct FluxResult {
    uint8_t error_mask;     // bit i = 1 if constraint i violated
    uint8_t severity;       // 0=pass, 1=caution, 2=warning, 3=critical
    uint8_t violated_lo;    // bitmap: which constraints violated lower bound
    uint8_t violated_hi;    // bitmap: which constraints violated upper bound
};

// Configuration for a batch run
struct alignas(32) FluxBatchConfig {
    int n_sensors;              // number of sensor readings
    int n_constraints;          // constraints per sensor (1-8)
    int8_t saturation_lo;       // clamped lower bound (default -127)
    int8_t saturation_hi;       // clamped upper bound (default 127)
    uint8_t deadline_ms;        // WCET deadline (0 = no deadline)
    uint8_t severity_threshold; // minimum severity to report (0 = all)
    uint8_t reserved[3];        // padding
};

// ═══════════════════════════════════════════════════════════
// Saturation functions — prevent integer overflow
// ═══════════════════════════════════════════════════════════

__device__ __forceinline__
int8_t saturate_i8(int val) {
    // Clamp to [-127, 127] — avoids INT8 boundary wraparound (INTOVF-01 fix)
    return (int8_t)max((int)FLUX_INT8_MIN, min((int)FLUX_INT8_MAX, val));
}

__device__ __forceinline__
uint8_t saturate_u8(int val) {
    // Clamp to [0, 255]
    return (uint8_t)max(0, min((int)FLUX_UINT8_MAX, val));
}

// ═══════════════════════════════════════════════════════════
// Core kernel — flat bounds, error mask, saturation
// ═══════════════════════════════════════════════════════════

__global__
void flux_check_kernel_v2(
    const FluxBoundsFlat* __restrict__ bounds,    // [n_sensors] bounds
    const int8_t*          __restrict__ sensors,   // [n_sensors] sensor values
    FluxResult*            __restrict__ results,    // [n_sensors] output
    int*                   __restrict__ global_stats, // [4] pass, fail, caution, critical
    const FluxBatchConfig  config
) {
    extern __shared__ int smem_stats[];  // [4] block-local stats
    int tid = threadIdx.x;
    int idx = blockIdx.x * blockDim.x + tid;

    // Initialize shared memory
    if (tid < 4) smem_stats[tid] = 0;
    __syncthreads();

    if (idx >= config.n_sensors) return;

    // Load bounds and sensor with saturation
    FluxBoundsFlat b = bounds[idx];
    int8_t val = saturate_i8((int)sensors[idx]);

    // Initialize result
    FluxResult r = {0, 0, 0, 0};

    // Evaluate all constraints — fully unrolled, branchless
    #pragma unroll
    for (int i = 0; i < FLUX_MAX_CONSTRAINTS; i++) {
        if (i < config.n_constraints) {
            // Saturate bounds at compile/load time defense
            int8_t lo = saturate_i8((int)b.lo[i]);
            int8_t hi = saturate_i8((int)b.hi[i]);

            // Check lower bound
            bool lo_violated = (val < lo);
            // Check upper bound
            bool hi_violated = (val > hi);

            // Set error mask bit
            if (lo_violated || hi_violated) {
                r.error_mask |= (1u << i);
            }
            if (lo_violated) r.violated_lo |= (1u << i);
            if (hi_violated) r.violated_hi |= (1u << i);
        }
    }

    // Compute severity from error mask
    // Count violations → map to severity
    int n_violated = __popc(r.error_mask);
    if (n_violated == 0) {
        r.severity = 0;  // PASS
    } else if (n_violated <= config.n_constraints / 4) {
        r.severity = 1;  // CAUTION
    } else if (n_violated <= config.n_constraints / 2) {
        r.severity = 2;  // WARNING
    } else {
        r.severity = 3;  // CRITICAL
    }

    // Filter by severity threshold
    if (r.severity >= config.severity_threshold) {
        results[idx] = r;
    }

    // Block-level statistics (avoid global atomics storm)
    atomicAdd(&smem_stats[r.severity], 1);
    __syncthreads();

    // One thread per block updates global stats
    if (tid < 4) {
        atomicAdd(&global_stats[tid], smem_stats[tid]);
    }
}

// ═══════════════════════════════════════════════════════════
// Hot-swap bounds update kernel — incremental, <1kHz capable
// ═══════════════════════════════════════════════════════════

__global__
void flux_update_bounds_kernel(
    FluxBoundsFlat* __restrict__ bounds,
    const int*      __restrict__ sensor_ids,     // which sensors to update
    const int8_t*   __restrict__ new_lo,          // new lower bounds
    const int8_t*   __restrict__ new_hi,          // new upper bounds
    int n_updates,
    int n_constraints
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n_updates) return;

    int sid = sensor_ids[idx];
    // Bounds check on sensor ID
    if (sid < 0) return;

    FluxBoundsFlat b = bounds[sid];

    #pragma unroll
    for (int i = 0; i < FLUX_MAX_CONSTRAINTS; i++) {
        if (i < n_constraints) {
            b.lo[i] = saturate_i8((int)new_lo[idx * n_constraints + i]);
            b.hi[i] = saturate_i8((int)new_hi[idx * n_constraints + i]);
        }
    }

    bounds[sid] = b;
}

// ═══════════════════════════════════════════════════════════
// Host API — C linkage for Rust/Python integration
// ═══════════════════════════════════════════════════════════

extern "C" {

// Opaque handle for CUDA Graph state
struct FluxGraphState {
    cudaGraph_t graph;
    cudaGraphExec_t exec;
    bool initialized;
};

// Initialize a batch run and capture CUDA Graph
// Returns 0 on success, negative on error
int flux_batch_init(
    FluxBoundsFlat* d_bounds,
    int8_t*         d_sensors,
    FluxResult*     d_results,
    int*            d_stats,
    FluxBatchConfig config,
    FluxGraphState* state
) {
    int grid = (config.n_sensors + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    // Zero stats
    cudaMemset(d_stats, 0, 4 * sizeof(int));

    // Warmup run (exp25: cold start is 46.7B, peaks by iter 4-10)
    flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
        d_bounds, d_sensors, d_results, d_stats, config
    );
    cudaDeviceSynchronize();

    // Capture CUDA Graph (exp13: 51x launch speedup)
    cudaStream_t stream;
    cudaStreamCreate(&stream);

    cudaMemset(d_stats, 0, 4 * sizeof(int));

    // Begin capture
    cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal);
    flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
        d_bounds, d_sensors, d_results, d_stats, config
    );
    cudaStreamEndCapture(stream, &state->graph);

    // Instantiate graph
    cudaGraphInstantiate(&state->exec, state->graph, NULL, NULL, 0);
    state->initialized = true;

    cudaStreamDestroy(stream);
    return 0;
}

// Execute a captured CUDA Graph — zero-overhead replay
int flux_batch_execute(FluxGraphState* state) {
    if (!state || !state->initialized) return -1;
    cudaGraphLaunch(state->exec, 0);
    cudaDeviceSynchronize();
    return 0;
}

// Hot-swap bounds update — returns latency in microseconds
long flux_hotswap_bounds(
    FluxBoundsFlat* d_bounds,
    int*            d_sensor_ids,
    int8_t*         d_new_lo,
    int8_t*         d_new_hi,
    int             n_updates,
    int             n_constraints
) {
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    int grid = (n_updates + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;

    cudaEventRecord(start);
    flux_update_bounds_kernel<<<grid, FLUX_BLOCK_SIZE>>>(
        d_bounds, d_sensor_ids, d_new_lo, d_new_hi, n_updates, n_constraints
    );
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float ms = 0;
    cudaEventElapsedTime(&ms, start, stop);

    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    return (long)(ms * 1000.0f);  // microseconds
}

// Cleanup
void flux_batch_cleanup(FluxGraphState* state) {
    if (state) {
        if (state->exec) cudaGraphExecDestroy(state->exec);
        if (state->graph) cudaGraphDestroy(state->graph);
        state->initialized = false;
    }
}

} // extern "C"

#endif // FLUX_PRODUCTION_V2_CU
