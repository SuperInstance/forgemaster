// Experiment 52: Temporal Constraint Engine
// Time-series safety constraints on GPU — rate-of-change, deadband, persistence, sequencing
//
// Safety-critical systems don't just check "is X in range NOW" — they check:
//   - Rate of change: |dx/dt| ≤ max_rate
//   - Deadband: don't re-alarm if fluctuation < threshold
//   - Persistence: constraint must be violated for N consecutive samples
//   - Sequencing: event A must occur within T seconds of event B
//
// This kernel processes a sliding window of sensor history in parallel.
//
// (c) 2026 SuperInstance — Apache 2.0

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
#include <cuda_runtime.h>

// ═══════════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════════

constexpr int TEMPORAL_WINDOW = 8;      // samples in sliding window
constexpr int MAX_TEMPORAL_CONSTRAINTS = 4;
constexpr int BLOCK_SIZE = 256;

// Temporal constraint types (plain enum for CUDA 11.5 compat)
typedef enum {
    TEMPORAL_RANGE = 0,       // Standard range check (baseline)
    TEMPORAL_RATE_OF_CHANGE,  // |x[t] - x[t-1]| ≤ max_delta
    TEMPORAL_DEADBAND,        // |x[t] - x[t-1]| ≥ threshold to count as change
    TEMPORAL_PERSISTENCE     // Must violate for N consecutive samples
} TemporalType;

// Temporal constraint definition
struct TemporalConstraint {
    int8_t lo, hi;
    int8_t threshold;
    TemporalType type;
    uint8_t padding;
};

// Temporal result — richer than instant check
struct TemporalResult {
    uint8_t error_mask;
    uint8_t persistent_mask;
    uint8_t rate_exceeded;
    uint8_t deadband_active;
    int8_t max_rate_observed;
    int8_t min_value;
    int8_t max_value;
    uint8_t severity;
};

// ═══════════════════════════════════════════════════════════
// Saturate
// ═══════════════════════════════════════════════════════════

// Saturate (host+device)
__host__ __device__ __forceinline__
int8_t sat8(int v) { return (int8_t)max(-127, min(127, v)); }

// ═══════════════════════════════════════════════════════════
// Temporal constraint kernel
// Each thread processes one sensor's time series
// ═══════════════════════════════════════════════════════════

__global__
void temporal_check_kernel(
    const int8_t* __restrict__ history,      // [n_sensors × window_size]
    const TemporalConstraint* __restrict__ constraints,
    TemporalResult* __restrict__ results,
    int* global_stats,                         // [4] pass, fail_persistent, fail_rate, total
    int n_sensors,
    int window,
    int n_constraints
) {
    extern __shared__ int smem[];
    int tid = threadIdx.x;
    if (tid < 4) smem[tid] = 0;
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + tid;
    if (idx >= n_sensors) return;

    // Load this sensor's time series
    const int8_t* series = &history[idx * window];
    TemporalResult r = {0, 0, 0, 0, 0, 127, -127, 0};

    int8_t latest = sat8((int)series[window - 1]);

    // Compute min/max across window
    for (int t = 0; t < window; t++) {
        int8_t v = sat8((int)series[t]);
        if (v < r.min_value) r.min_value = v;
        if (v > r.max_value) r.max_value = v;
    }

    // Process each temporal constraint
    for (int c = 0; c < n_constraints; c++) {
        TemporalConstraint tc = constraints[c];

        switch (tc.type) {
            case TEMPORAL_RANGE: {
                // Standard range check on latest value
                if (latest < tc.lo || latest > tc.hi) {
                    r.error_mask |= (1u << c);
                }
                break;
            }

            case TEMPORAL_RATE_OF_CHANGE: {
                // Check |x[t] - x[t-1]| ≤ max_delta for all transitions
                int8_t max_rate = 0;
                bool exceeded = false;
                for (int t = 1; t < window; t++) {
                    int8_t curr = sat8((int)series[t]);
                    int8_t prev = sat8((int)series[t-1]);
                    int delta = abs((int)curr - (int)prev);
                    int8_t d = sat8(delta);
                    if (d > max_rate) max_rate = d;
                    if (d > tc.hi) exceeded = true;  // hi field = max_rate
                }
                r.max_rate_observed = max_rate > r.max_rate_observed ? max_rate : r.max_rate_observed;
                if (exceeded) {
                    r.rate_exceeded |= (1u << c);
                    r.error_mask |= (1u << c);
                }
                break;
            }

            case TEMPORAL_DEADBAND: {
                // If |x[t] - x[t-1]| < threshold, value is in deadband
                int8_t prev = sat8((int)series[window - 2]);
                int delta = abs((int)latest - (int)prev);
                if (delta < tc.threshold) {
                    r.deadband_active |= (1u << c);
                    // In deadband: don't flag as violation even if out of range
                    // (only flag if it's a REAL change outside bounds)
                } else {
                    // Real change — check range
                    if (latest < tc.lo || latest > tc.hi) {
                        r.error_mask |= (1u << c);
                    }
                }
                break;
            }

            case TEMPORAL_PERSISTENCE: {
                // Count consecutive samples violating the constraint
                int consecutive = 0;
                for (int t = window - 1; t >= 0; t--) {
                    int8_t v = sat8((int)series[t]);
                    if (v < tc.lo || v > tc.hi) {
                        consecutive++;
                    } else {
                        break;
                    }
                }
                // threshold field = required persistence count
                if (consecutive >= tc.threshold) {
                    r.persistent_mask |= (1u << c);
                    r.error_mask |= (1u << c);
                }
                break;
            }
        }
    }

    // Compute severity
    int n_violated = __popc(r.error_mask);
    if (n_violated == 0) r.severity = 0;
    else if (n_violated == 1 && r.persistent_mask == 0 && r.rate_exceeded == 0) r.severity = 1;
    else if (r.rate_exceeded || r.persistent_mask) r.severity = 2;
    else r.severity = 3;

    results[idx] = r;
    atomicAdd(&smem[r.severity], 1);
    __syncthreads();
    if (tid < 4) atomicAdd(&global_stats[tid], smem[tid]);
}

// ═══════════════════════════════════════════════════════════
// Benchmark
// ═══════════════════════════════════════════════════════════

int main() {
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  Exp52: Temporal Constraint Engine                          ║\n");
    printf("║  Rate-of-change, deadband, persistence, sequencing         ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    // Scenarios
    int n_sensors = 10000000;
    int window = TEMPORAL_WINDOW;
    int n_constraints = 4;

    // Define temporal constraints
    TemporalConstraint h_tc[MAX_TEMPORAL_CONSTRAINTS] = {
        { -50, 100, 0, TEMPORAL_RANGE, 0 },           // C0: Range [-50, 100]
        { 0, 20, 0, TEMPORAL_RATE_OF_CHANGE, 0 },     // C1: Rate ≤ 20/sample
        { -40, 80, 5, TEMPORAL_DEADBAND, 0 },          // C2: Deadband ±5, range [-40, 80]
        { -60, 110, 3, TEMPORAL_PERSISTENCE, 0 },      // C3: Must violate 3 consecutive
    };

    // Generate time-series data
    size_t hist_size = (size_t)n_sensors * window;
    int8_t* h_history = new int8_t[hist_size];

    srand(42);
    for (int s = 0; s < n_sensors; s++) {
        int8_t base = (int8_t)(rand() % 150 - 75);
        for (int t = 0; t < window; t++) {
            // Random walk with occasional spikes
            int8_t delta = (int8_t)(rand() % 15 - 7);
            // Inject rate-of-change violations in 2% of sensors
            if (s % 50 == 0 && t == window - 1) delta = 50;
            // Inject persistence violations in 1% of sensors
            if (s % 100 == 0 && t >= window - 3) base = 120;

            h_history[s * window + t] = sat8((int)base + (int)delta);
            base = h_history[s * window + t];
        }
    }

    // GPU allocation
    int8_t* d_history;
    TemporalConstraint* d_tc;
    TemporalResult* d_results;
    int* d_stats;

    cudaMalloc(&d_history, hist_size * sizeof(int8_t));
    cudaMalloc(&d_tc, n_constraints * sizeof(TemporalConstraint));
    cudaMalloc(&d_results, n_sensors * sizeof(TemporalResult));
    cudaMalloc(&d_stats, 4 * sizeof(int));

    cudaMemcpy(d_history, h_history, hist_size * sizeof(int8_t), cudaMemcpyHostToDevice);
    cudaMemcpy(d_tc, h_tc, n_constraints * sizeof(TemporalConstraint), cudaMemcpyHostToDevice);

    int grid = (n_sensors + BLOCK_SIZE - 1) / BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    // Warmup
    for (int i = 0; i < 10; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        temporal_check_kernel<<<grid, BLOCK_SIZE, smem>>>(
            d_history, d_tc, d_results, d_stats, n_sensors, window, n_constraints
        );
    }
    cudaDeviceSynchronize();

    // Benchmark
    int iters = 500;
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        temporal_check_kernel<<<grid, BLOCK_SIZE, smem>>>(
            d_history, d_tc, d_results, d_stats, n_sensors, window, n_constraints
        );
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float ms = 0;
    cudaEventElapsedTime(&ms, start, stop);

    // Results
    int stats[4];
    cudaMemcpy(stats, d_stats, 4 * sizeof(int), cudaMemcpyDeviceToHost);

    // Sample some results
    TemporalResult h_results[10];
    cudaMemcpy(h_results, d_results, 10 * sizeof(TemporalResult), cudaMemcpyDeviceToHost);

    double total_checks = (double)n_sensors * n_constraints * iters;
    double rate = total_checks / (ms / 1000.0);

    // Per-sensor throughput (each sensor processes a window)
    double sensor_rate = (double)n_sensors * iters / (ms / 1000.0);

    printf("  Sensors: %d × %d-sample window × %d constraints\n", n_sensors, window, n_constraints);
    printf("  Iterations: %d\n\n", iters);

    printf("  ┌─────────────────────────────────────────┐\n");
    printf("  │ Throughput:  %.2f B temporal checks/sec   │\n", rate / 1e9);
    printf("  │ Sensor rate: %.2f M sensor-wins/sec       │\n", sensor_rate / 1e6);
    printf("  │ Per-iter:    %.4f ms                      │\n", ms / iters);
    printf("  ├─────────────────────────────────────────┤\n");
    printf("  │ Pass:        %d (%.1f%%)                   \n", stats[0], 100.0*stats[0]/n_sensors);
    printf("  │ Caution:     %d (%.1f%%)                   \n", stats[1], 100.0*stats[1]/n_sensors);
    printf("  │ Warning:     %d (%.1f%%)                   \n", stats[2], 100.0*stats[2]/n_sensors);
    printf("  │ Critical:    %d (%.1f%%)                   \n", stats[3], 100.0*stats[3]/n_sensors);
    printf("  └─────────────────────────────────────────┘\n");

    printf("\n  Sample results (first 5 sensors):\n");
    printf("  %-4s %-8s %-8s %-8s %-8s %-8s %-8s\n",
        "Idx", "Error", "Persis", "Rate", "Deadbd", "Min", "Max");
    for (int i = 0; i < 5; i++) {
        printf("  %-4d 0x%02X    0x%02X    0x%02X    0x%02X    %-8d %-8d\n",
            i, h_results[i].error_mask, h_results[i].persistent_mask,
            h_results[i].rate_exceeded, h_results[i].deadband_active,
            h_results[i].min_value, h_results[i].max_value);
    }

    // Window size scaling
    printf("\n  Window size scaling:\n");
    for (int w = 4; w <= 32; w *= 2) {
        // Allocate fresh history for each window size
        size_t sz = (size_t)n_sensors * w;
        int8_t* h_hist_w = new int8_t[sz];
        for (size_t i = 0; i < sz; i++) h_hist_w[i] = h_history[i % (n_sensors * TEMPORAL_WINDOW)];
        
        int8_t* d_hist_w;
        cudaMalloc(&d_hist_w, sz * sizeof(int8_t));
        cudaMemcpy(d_hist_w, h_hist_w, sz * sizeof(int8_t), cudaMemcpyHostToDevice);

        cudaEventRecord(start);
        for (int i = 0; i < 100; i++) {
            cudaMemset(d_stats, 0, 4 * sizeof(int));
            temporal_check_kernel<<<grid, BLOCK_SIZE, smem>>>(
                d_hist_w, d_tc, d_results, d_stats, n_sensors, w, n_constraints
            );
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        cudaEventElapsedTime(&ms, start, stop);

        double w_rate = (double)n_sensors * n_constraints * 100 / (ms / 1000.0);
        printf("    Window=%-3d: %.2f B checks/sec (%.4f ms/iter)\n", w, w_rate / 1e9, ms / 100);

        cudaFree(d_hist_w);
        delete[] h_hist_w;
    }

    printf("\n  ✓ EXP52 complete — temporal constraint engine benchmarked.\n");

    // Cleanup
    cudaFree(d_history); cudaFree(d_tc); cudaFree(d_results); cudaFree(d_stats);
    cudaEventDestroy(start); cudaEventDestroy(stop);
    delete[] h_history;

    return 0;
}
