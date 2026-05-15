// exp48_cascade_propagation.cu — Cascade Failure Propagation
// Simulates cascade failure: when one constraint violates, propagate
// severity to neighboring sensors. 1M sensors in a grid topology,
// cascade within 3 hops. Measures cascade detection latency and throughput.
//
// Compile: nvcc -arch=sm_86 -O3 -o exp48_cascade_propagation exp48_cascade_propagation.cu -I../flux-hardware/cuda/

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <cmath>

// Inline production kernel structs
constexpr int FLUX_MAX_CONSTRAINTS = 8;
constexpr int FLUX_BLOCK_SIZE = 256;
constexpr int FLUX_INT8_MIN = -127;
constexpr int FLUX_INT8_MAX = 127;

struct alignas(16) FluxBoundsFlat {
    int8_t lo[FLUX_MAX_CONSTRAINTS];
    int8_t hi[FLUX_MAX_CONSTRAINTS];
};

struct FluxResult {
    uint8_t error_mask;
    uint8_t severity;
    uint8_t violated_lo;
    uint8_t violated_hi;
};

struct alignas(32) FluxBatchConfig {
    int n_sensors;
    int n_constraints;
    int8_t saturation_lo;
    int8_t saturation_hi;
    uint8_t deadline_ms;
    uint8_t severity_threshold;
    uint8_t reserved[3];
};

__device__ __forceinline__
int8_t saturate_i8(int val) {
    return (int8_t)max((int)FLUX_INT8_MIN, min((int)FLUX_INT8_MAX, val));
}

// Phase 1: Standard constraint check
__global__
void flux_check_kernel_v2(
    const FluxBoundsFlat* __restrict__ bounds,
    const int8_t*          __restrict__ sensors,
    FluxResult*            __restrict__ results,
    int*                   __restrict__ global_stats,
    const FluxBatchConfig  config
) {
    extern __shared__ int smem_stats[];
    int tid = threadIdx.x;
    int idx = blockIdx.x * blockDim.x + tid;

    if (tid < 4) smem_stats[tid] = 0;
    __syncthreads();

    if (idx >= config.n_sensors) return;

    FluxBoundsFlat b = bounds[idx];
    int8_t val = saturate_i8((int)sensors[idx]);

    FluxResult r = {0, 0, 0, 0};

    #pragma unroll
    for (int i = 0; i < FLUX_MAX_CONSTRAINTS; i++) {
        if (i < config.n_constraints) {
            int8_t lo = saturate_i8((int)b.lo[i]);
            int8_t hi = saturate_i8((int)b.hi[i]);
            bool lo_violated = (val < lo);
            bool hi_violated = (val > hi);
            if (lo_violated || hi_violated) r.error_mask |= (1u << i);
            if (lo_violated) r.violated_lo |= (1u << i);
            if (hi_violated) r.violated_hi |= (1u << i);
        }
    }

    int n_violated = __popc(r.error_mask);
    if (n_violated == 0) r.severity = 0;
    else if (n_violated <= config.n_constraints / 4) r.severity = 1;
    else if (n_violated <= config.n_constraints / 2) r.severity = 2;
    else r.severity = 3;

    if (r.severity >= config.severity_threshold) {
        results[idx] = r;
    }

    atomicAdd(&smem_stats[r.severity], 1);
    __syncthreads();
    if (tid < 4) {
        atomicAdd(&global_stats[tid], smem_stats[tid]);
    }
}

// Phase 2: Cascade propagation — elevate severity of neighbors
// Grid topology: sensor (x,y) = (idx % GRID_W, idx / GRID_W)
// Cascade: for each sensor with severity >= threshold, propagate to neighbors
// within MAX_HOPS hops. Neighbors get severity elevated by cascading rule.
constexpr int CASCADE_MAX_HOPS = 3;

__global__
void cascade_propagate_kernel(
    const FluxResult* __restrict__ initial_results,
    FluxResult*       __restrict__ cascade_results,
    int*              __restrict__ cascade_count,  // total cascaded
    int*              __restrict__ hop_counts,     // [MAX_HOPS] count per hop
    int               grid_w,
    int               grid_h,
    int               n_sensors,
    int               max_hops,
    uint8_t           cascade_threshold  // min severity to cascade from
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n_sensors) return;

    // Start with initial result
    FluxResult r = initial_results[idx];
    uint8_t orig_severity = r.severity;

    // Find grid position
    int my_x = idx % grid_w;
    int my_y = idx / grid_w;

    // Check if any neighbor within max_hops has severity >= cascade_threshold
    // and would cascade to us
    int my_hops_to_source = max_hops + 1;  // infinity

    // Search neighborhood (only within max_hops)
    for (int dy = -max_hops; dy <= max_hops; dy++) {
        for (int dx = -max_hops; dx <= max_hops; dx++) {
            if (dx == 0 && dy == 0) continue;
            int hops = abs(dx) + abs(dy);  // Manhattan distance
            if (hops > max_hops) continue;

            int nx = my_x + dx;
            int ny = my_y + dy;
            if (nx < 0 || nx >= grid_w || ny < 0 || ny >= grid_h) continue;

            int nidx = ny * grid_w + nx;
            if (initial_results[nidx].severity >= cascade_threshold) {
                if (hops < my_hops_to_source) {
                    my_hops_to_source = hops;
                }
            }
        }
    }

    // If a nearby source was found, potentially elevate our severity
    if (my_hops_to_source <= max_hops) {
        // Cascade rule: severity decays with distance
        // Source severity / hops
        uint8_t cascade_severity = (uint8_t)max(1, (int)(3 / my_hops_to_source));

        // Elevate if cascade_severity > original
        if (cascade_severity > r.severity) {
            r.severity = cascade_severity;
            r.error_mask |= 0x80;  // mark as cascade-elevated (top bit)
            atomicAdd(&cascade_count[0], 1);
            atomicAdd(&hop_counts[my_hops_to_source - 1], 1);
        }
    }

    // Keep original if higher
    if (orig_severity > r.severity) {
        r.severity = orig_severity;
    }

    cascade_results[idx] = r;
}

int main() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  EXP48: Cascade Failure Propagation                         ║\n");
    printf("║  1M sensors, grid topology, 3-hop cascade                   ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    const int N_SENSORS = 1000000;  // 1M
    const int GRID_W = 1000;
    const int GRID_H = 1000;
    const int N_CONSTRAINTS = 4;
    const int MAX_HOPS = CASCADE_MAX_HOPS;
    const uint8_t CASCADE_THRESHOLD = 3;  // only CRITICAL triggers cascade
    const int WARMUP = 5;
    const int BENCH_ITERS = 10;

    size_t bounds_size = N_SENSORS * sizeof(FluxBoundsFlat);
    size_t sensor_size = N_SENSORS * sizeof(int8_t);
    size_t result_size = N_SENSORS * sizeof(FluxResult);

    // Host alloc
    FluxBoundsFlat* h_bounds = (FluxBoundsFlat*)malloc(bounds_size);
    int8_t* h_sensors = (int8_t*)malloc(sensor_size);

    srand(42);
    // Create some tight bounds to generate violations
    for (int i = 0; i < N_SENSORS; i++) {
        for (int c = 0; c < FLUX_MAX_CONSTRAINTS; c++) {
            // Tight bounds: narrow range = more violations
            h_bounds[i].lo[c] = (int8_t)(rand() % 40 - 20);
            h_bounds[i].hi[c] = (int8_t)(h_bounds[i].lo[c] + (rand() % 10 + 5));
        }
        // Some sensors get extreme values to trigger critical
        if (rand() % 100 < 5) {
            // 5% extreme values
            h_sensors[i] = (int8_t)((rand() % 2 == 0) ? 127 : -127);
        } else {
            h_sensors[i] = (int8_t)(rand() % 80 - 40);
        }
    }

    // Device alloc
    FluxBoundsFlat* d_bounds;
    int8_t* d_sensors;
    FluxResult* d_results;
    FluxResult* d_cascade_results;
    int* d_stats;
    int* d_cascade_count;
    int* d_hop_counts;

    cudaMalloc(&d_bounds, bounds_size);
    cudaMalloc(&d_sensors, sensor_size);
    cudaMalloc(&d_results, result_size);
    cudaMalloc(&d_cascade_results, result_size);
    cudaMalloc(&d_stats, 4 * sizeof(int));
    cudaMalloc(&d_cascade_count, sizeof(int));
    cudaMalloc(&d_hop_counts, MAX_HOPS * sizeof(int));

    cudaMemcpy(d_bounds, h_bounds, bounds_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_sensors, h_sensors, sensor_size, cudaMemcpyHostToDevice);

    FluxBatchConfig config;
    config.n_sensors = N_SENSORS;
    config.n_constraints = N_CONSTRAINTS;
    config.saturation_lo = -127;
    config.saturation_hi = 127;
    config.deadline_ms = 0;
    config.severity_threshold = 0;
    config.reserved[0] = config.reserved[1] = config.reserved[2] = 0;

    int grid = (N_SENSORS + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    int cascade_grid = (N_SENSORS + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    // Warmup both phases
    for (int i = 0; i < WARMUP; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config);
        cudaDeviceSynchronize();

        cudaMemset(d_cascade_count, 0, sizeof(int));
        cudaMemset(d_hop_counts, 0, MAX_HOPS * sizeof(int));
        cascade_propagate_kernel<<<cascade_grid, FLUX_BLOCK_SIZE>>>(
            d_results, d_cascade_results, d_cascade_count, d_hop_counts,
            GRID_W, GRID_H, N_SENSORS, MAX_HOPS, CASCADE_THRESHOLD);
        cudaDeviceSynchronize();
    }

    // Benchmark Phase 1: constraint check
    cudaEvent_t p1_start, p1_stop, p2_start, p2_stop, total_start, total_stop;
    cudaEventCreate(&p1_start); cudaEventCreate(&p1_stop);
    cudaEventCreate(&p2_start); cudaEventCreate(&p2_stop);
    cudaEventCreate(&total_start); cudaEventCreate(&total_stop);

    float p1_total = 0, p2_total = 0, pipeline_total = 0;

    for (int i = 0; i < BENCH_ITERS; i++) {
        cudaEventRecord(total_start);

        // Phase 1
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        cudaEventRecord(p1_start);
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config);
        cudaEventRecord(p1_stop);
        cudaEventSynchronize(p1_stop);

        // Phase 2
        cudaMemset(d_cascade_count, 0, sizeof(int));
        cudaMemset(d_hop_counts, 0, MAX_HOPS * sizeof(int));
        cudaEventRecord(p2_start);
        cascade_propagate_kernel<<<cascade_grid, FLUX_BLOCK_SIZE>>>(
            d_results, d_cascade_results, d_cascade_count, d_hop_counts,
            GRID_W, GRID_H, N_SENSORS, MAX_HOPS, CASCADE_THRESHOLD);
        cudaEventRecord(p2_stop);
        cudaEventSynchronize(p2_stop);

        cudaEventRecord(total_stop);
        cudaEventSynchronize(total_stop);

        float ms;
        cudaEventElapsedTime(&ms, p1_start, p1_stop); p1_total += ms;
        cudaEventElapsedTime(&ms, p2_start, p2_stop); p2_total += ms;
        cudaEventElapsedTime(&ms, total_start, total_stop); pipeline_total += ms;
    }

    float p1_avg = p1_total / BENCH_ITERS;
    float p2_avg = p2_total / BENCH_ITERS;
    float pipeline_avg = pipeline_total / BENCH_ITERS;

    // Get final cascade results
    cudaMemset(d_cascade_count, 0, sizeof(int));
    cudaMemset(d_hop_counts, 0, MAX_HOPS * sizeof(int));
    cudaMemset(d_stats, 0, 4 * sizeof(int));

    flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
        d_bounds, d_sensors, d_results, d_stats, config);
    cudaDeviceSynchronize();

    cascade_propagate_kernel<<<cascade_grid, FLUX_BLOCK_SIZE>>>(
        d_results, d_cascade_results, d_cascade_count, d_hop_counts,
        GRID_W, GRID_H, N_SENSORS, MAX_HOPS, CASCADE_THRESHOLD);
    cudaDeviceSynchronize();

    // Read back stats
    int h_stats[4], h_cascade_count = 0, h_hop_counts[MAX_HOPS] = {};
    cudaMemcpy(h_stats, d_stats, 4 * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_cascade_count, d_cascade_count, sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_hop_counts, d_hop_counts, MAX_HOPS * sizeof(int), cudaMemcpyDeviceToHost);

    FluxResult* h_initial = (FluxResult*)malloc(result_size);
    FluxResult* h_cascade = (FluxResult*)malloc(result_size);
    cudaMemcpy(h_initial, d_results, result_size, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_cascade, d_cascade_results, result_size, cudaMemcpyDeviceToHost);

    // Count initial critical (cascade sources)
    int initial_critical = 0;
    int total_elevated = 0;
    int severity_after[4] = {};
    for (int i = 0; i < N_SENSORS; i++) {
        if (h_initial[i].severity == 3) initial_critical++;
        severity_after[h_cascade[i].severity]++;
        if (h_cascade[i].error_mask & 0x80) total_elevated++;
    }

    // Print results
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  CASCADE PROPAGATION RESULTS                                ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  Grid:              %d × %d (1M sensors)                 ║\n", GRID_W, GRID_H);
    printf("║  Max cascade hops:  %d                                     ║\n", MAX_HOPS);
    printf("║  Cascade threshold: CRITICAL (severity 3)                  ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  INITIAL (Phase 1 — constraint check):                      ║\n");
    printf("║    Pass:     %8d (%6.2f%%)                               ║\n", h_stats[0], 100.0*h_stats[0]/N_SENSORS);
    printf("║    Caution:  %8d (%6.2f%%)                               ║\n", h_stats[1], 100.0*h_stats[1]/N_SENSORS);
    printf("║    Warning:  %8d (%6.2f%%)                               ║\n", h_stats[2], 100.0*h_stats[2]/N_SENSORS);
    printf("║    Critical: %8d (%6.2f%%)                               ║\n", h_stats[3], 100.0*h_stats[3]/N_SENSORS);
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  CASCADE (Phase 2 — propagation):                           ║\n");
    printf("║    Cascade sources (critical):  %8d                      ║\n", initial_critical);
    printf("║    Sensors elevated by cascade: %8d                      ║\n", total_elevated);
    printf("║    Cascade ratio:               %8.3f sensors/source      ║\n",
           initial_critical > 0 ? (double)total_elevated / initial_critical : 0.0);
    printf("║                                                              ║\n");
    printf("║    Hop distribution:                                         ║\n");
    for (int h = 0; h < MAX_HOPS; h++) {
        printf("║      Hop %d: %8d sensors elevated                        ║\n", h+1, h_hop_counts[h]);
    }
    printf("║                                                              ║\n");
    printf("║    Severity after cascade:                                   ║\n");
    printf("║      Pass:     %8d                                         ║\n", severity_after[0]);
    printf("║      Caution:  %8d                                         ║\n", severity_after[1]);
    printf("║      Warning:  %8d                                         ║\n", severity_after[2]);
    printf("║      Critical: %8d                                         ║\n", severity_after[3]);
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  PERFORMANCE                                                ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  Phase 1 (check):          %8.3f ms                        ║\n", p1_avg);
    printf("║  Phase 2 (cascade):        %8.3f ms                        ║\n", p2_avg);
    printf("║  Total pipeline:           %8.3f ms                        ║\n", pipeline_avg);
    printf("║  Throughput:               %8.2f M sensors/sec             ║\n",
           (double)N_SENSORS / (pipeline_avg / 1000.0) / 1e6);
    printf("║  Cascade detection latency:%8.3f ms (Phase 2)             ║\n", p2_avg);
    printf("║  Safe-TOPS:                %8.2f M checks/sec              ║\n",
           (double)N_SENSORS * N_CONSTRAINTS / (pipeline_avg / 1000.0) / 1e6);
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    // Cleanup
    cudaFree(d_bounds); cudaFree(d_sensors);
    cudaFree(d_results); cudaFree(d_cascade_results);
    cudaFree(d_stats); cudaFree(d_cascade_count); cudaFree(d_hop_counts);
    cudaEventDestroy(p1_start); cudaEventDestroy(p1_stop);
    cudaEventDestroy(p2_start); cudaEventDestroy(p2_stop);
    cudaEventDestroy(total_start); cudaEventDestroy(total_stop);
    free(h_bounds); free(h_sensors);
    free(h_initial); free(h_cascade);

    printf("\n  ✓ EXP48 complete — cascade propagation measured.\n\n");
    return 0;
}
