// exp46_multiindustry_fusion.cu — Multi-Industry Fusion Benchmark
// Loads constraints from 4 industries (aviation, maritime, energy, medical)
// and runs them simultaneously against 10M sensor readings.
// Reports per-industry violation rates and aggregate throughput.
//
// Compile: nvcc -arch=sm_86 -O3 -o exp46_multiindustry_fusion exp46_multiindustry_fusion.cu -I../flux-hardware/cuda/

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <chrono>

// Inline production kernel structs (cannot #include .cu with kernels in it directly)
// We replicate the data structures and redeclare the kernel.

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

// ═══════════════════════════════════════════════════════════
// Industry definitions
// ═══════════════════════════════════════════════════════════

struct IndustryConfig {
    const char* name;
    int8_t lo[2]; // 2 constraints per industry
    int8_t hi[2];
    const char* desc[2];
};

// Industry 0: Aviation — altitude (0-50k ft mapped to int8), airspeed
static const IndustryConfig INDUSTRIES[4] = {
    { // Aviation
        "Aviation",
        {-50, 20},   // lo: altitude ~0ft, airspeed min
        {100, 80},   // hi: altitude ~50k ft, airspeed max
        {"altitude", "airspeed"}
    },
    { // Maritime
        "Maritime",
        {-10, -20},  // lo: depth min, hull stress min
        {60, 40},    // hi: depth max, hull stress max
        {"depth", "hull_stress"}
    },
    { // Energy
        "Energy",
        {10, -30},   // lo: reactor temp min, grid voltage min
        {90, 50},    // hi: reactor temp max, grid voltage max
        {"reactor_temp", "grid_voltage"}
    },
    { // Medical
        "Medical",
        {30, 50},    // lo: SpO2 min, heart rate min
        {100, 120},  // hi: SpO2 max, heart rate max
        {"spo2", "heart_rate"}
    }
};

// Per-industry stats collected on host
struct IndustryStats {
    long total;
    long pass_count;
    long caution_count;
    long warning_count;
    long critical_count;
    double violation_rate;
};

int main() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  EXP46: Multi-Industry Fusion Benchmark                     ║\n");
    printf("║  4 industries × 2 constraints × 10M sensors                 ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    const int N_SENSORS_PER_INDUSTRY = 2500000;  // 2.5M × 4 = 10M
    const int N_SENSORS_TOTAL = N_SENSORS_PER_INDUSTRY * 4;
    const int N_CONSTRAINTS = 2;
    const int WARMUP_ITERS = 5;
    const int BENCH_ITERS = 20;

    size_t bounds_size = N_SENSORS_TOTAL * sizeof(FluxBoundsFlat);
    size_t sensor_size = N_SENSORS_TOTAL * sizeof(int8_t);
    size_t result_size = N_SENSORS_TOTAL * sizeof(FluxResult);
    size_t stats_size = 4 * sizeof(int);

    // Allocate host memory
    FluxBoundsFlat* h_bounds = (FluxBoundsFlat*)malloc(bounds_size);
    int8_t* h_sensors = (int8_t*)malloc(sensor_size);

    // Fill bounds per industry sector
    srand(42);
    for (int ind = 0; ind < 4; ind++) {
        int base = ind * N_SENSORS_PER_INDUSTRY;
        for (int i = 0; i < N_SENSORS_PER_INDUSTRY; i++) {
            FluxBoundsFlat& b = h_bounds[base + i];
            memset(&b, 0, sizeof(b));
            // Only set first 2 constraints per industry
            b.lo[0] = INDUSTRIES[ind].lo[0];
            b.hi[0] = INDUSTRIES[ind].hi[0];
            b.lo[1] = INDUSTRIES[ind].lo[1];
            b.hi[1] = INDUSTRIES[ind].hi[1];
        }
    }

    // Fill sensors with random values (some in-bounds, some out-of-bounds)
    for (int i = 0; i < N_SENSORS_TOTAL; i++) {
        h_sensors[i] = (int8_t)((rand() % 254) - 127);  // full int8 range
    }

    // Allocate device memory
    FluxBoundsFlat* d_bounds;
    int8_t* d_sensors;
    FluxResult* d_results;
    int* d_stats;
    cudaMalloc(&d_bounds, bounds_size);
    cudaMalloc(&d_sensors, sensor_size);
    cudaMalloc(&d_results, result_size);
    cudaMalloc(&d_stats, stats_size);

    cudaMemcpy(d_bounds, h_bounds, bounds_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_sensors, h_sensors, sensor_size, cudaMemcpyHostToDevice);

    FluxBatchConfig config;
    config.n_sensors = N_SENSORS_TOTAL;
    config.n_constraints = N_CONSTRAINTS;
    config.saturation_lo = -127;
    config.saturation_hi = 127;
    config.deadline_ms = 0;
    config.severity_threshold = 0;
    config.reserved[0] = config.reserved[1] = config.reserved[2] = 0;

    int grid = (N_SENSORS_TOTAL + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    // Warmup
    printf("  Warming up (%d iterations)...\n", WARMUP_ITERS);
    for (int i = 0; i < WARMUP_ITERS; i++) {
        cudaMemset(d_stats, 0, stats_size);
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config);
        cudaDeviceSynchronize();
    }

    // Benchmark with CUDA events
    printf("  Benchmarking (%d iterations)...\n\n", BENCH_ITERS);

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    float total_ms = 0.0f;
    for (int i = 0; i < BENCH_ITERS; i++) {
        cudaMemset(d_stats, 0, stats_size);
        cudaEventRecord(start);
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms = 0;
        cudaEventElapsedTime(&ms, start, stop);
        total_ms += ms;
    }

    float avg_ms = total_ms / BENCH_ITERS;
    double throughput = (double)N_SENSORS_TOTAL / (avg_ms / 1000.0);

    // Run final pass to get results
    cudaMemset(d_stats, 0, stats_size);
    flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
        d_bounds, d_sensors, d_results, d_stats, config);
    cudaDeviceSynchronize();

    // Copy results back
    FluxResult* h_results = (FluxResult*)malloc(result_size);
    int h_stats[4] = {0};
    cudaMemcpy(h_results, d_results, result_size, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_stats, d_stats, stats_size, cudaMemcpyDeviceToHost);

    // Compute per-industry stats
    IndustryStats ind_stats[4] = {};
    for (int ind = 0; ind < 4; ind++) {
        int base = ind * N_SENSORS_PER_INDUSTRY;
        ind_stats[ind].total = N_SENSORS_PER_INDUSTRY;
        for (int i = 0; i < N_SENSORS_PER_INDUSTRY; i++) {
            int idx = base + i;
            uint8_t sev = h_results[idx].severity;
            switch (sev) {
                case 0: ind_stats[ind].pass_count++; break;
                case 1: ind_stats[ind].caution_count++; break;
                case 2: ind_stats[ind].warning_count++; break;
                case 3: ind_stats[ind].critical_count++; break;
            }
        }
        long violations = ind_stats[ind].caution_count + ind_stats[ind].warning_count + ind_stats[ind].critical_count;
        ind_stats[ind].violation_rate = 100.0 * violations / N_SENSORS_PER_INDUSTRY;
    }

    // Print results
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  AGGREGATE RESULTS                                          ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  Total sensors:        %10d                          ║\n", N_SENSORS_TOTAL);
    printf("║  Avg latency:          %10.3f ms                        ║\n", avg_ms);
    printf("║  Throughput:            %9.2f M sensors/sec              ║\n", throughput / 1e6);
    printf("║  Constraints/sensor:    %9d                              ║\n", N_CONSTRAINTS);
    printf("║  Total checks/sec:     %10.2f M                          ║\n", throughput * N_CONSTRAINTS / 1e6);
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    // Per-industry breakdown
    for (int ind = 0; ind < 4; ind++) {
        const char* name = INDUSTRIES[ind].name;
        printf("╔══════════════════════════════════════════════════════════════╗\n");
        printf("║  %-12s — %d sensors, constraints: %-10s, %-10s  ║\n",
               name, N_SENSORS_PER_INDUSTRY,
               INDUSTRIES[ind].desc[0], INDUSTRIES[ind].desc[1]);
        printf("╠══════════════════════════════════════════════════════════════╣\n");
        printf("║  Pass:      %8ld  (%6.2f%%)                             ║\n",
               ind_stats[ind].pass_count,
               100.0 * ind_stats[ind].pass_count / N_SENSORS_PER_INDUSTRY);
        printf("║  Caution:   %8ld  (%6.2f%%)                             ║\n",
               ind_stats[ind].caution_count,
               100.0 * ind_stats[ind].caution_count / N_SENSORS_PER_INDUSTRY);
        printf("║  Warning:   %8ld  (%6.2f%%)                             ║\n",
               ind_stats[ind].warning_count,
               100.0 * ind_stats[ind].warning_count / N_SENSORS_PER_INDUSTRY);
        printf("║  Critical:  %8ld  (%6.2f%%)                             ║\n",
               ind_stats[ind].critical_count,
               100.0 * ind_stats[ind].critical_count / N_SENSORS_PER_INDUSTRY);
        printf("║  Violation rate:  %6.2f%%                                  ║\n",
               ind_stats[ind].violation_rate);
        printf("╚══════════════════════════════════════════════════════════════╝\n\n");
    }

    // Global severity breakdown
    long total_pass = h_stats[0];
    long total_caution = h_stats[1];
    long total_warning = h_stats[2];
    long total_critical = h_stats[3];
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  GLOBAL SEVERITY DISTRIBUTION                               ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  Pass:     %8d  (%6.2f%%)                                ║\n", total_pass, 100.0*total_pass/N_SENSORS_TOTAL);
    printf("║  Caution:  %8d  (%6.2f%%)                                ║\n", total_caution, 100.0*total_caution/N_SENSORS_TOTAL);
    printf("║  Warning:  %8d  (%6.2f%%)                                ║\n", total_warning, 100.0*total_warning/N_SENSORS_TOTAL);
    printf("║  Critical: %8d  (%6.2f%%)                                ║\n", total_critical, 100.0*total_critical/N_SENSORS_TOTAL);
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    // Cleanup
    cudaFree(d_bounds);
    cudaFree(d_sensors);
    cudaFree(d_results);
    cudaFree(d_stats);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    free(h_bounds);
    free(h_sensors);
    free(h_results);

    printf("\n  ✓ EXP46 complete — multi-industry fusion benchmarked.\n\n");
    return 0;
}
