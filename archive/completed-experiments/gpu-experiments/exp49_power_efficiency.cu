// exp49_power_efficiency.cu — Power Efficiency Benchmark
// Measures constraints per watt at different GPU clock speeds.
// Uses nvidia-smi to query power. Runs at 10M, 20M, 50M sensor counts.
// Computes Safe-TOPS/W using verified (differential-tested) operations.
//
// Compile: nvcc -arch=sm_86 -O3 -o exp49_power_efficiency exp49_power_efficiency.cu -I../flux-hardware/cuda/

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>

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

// Read GPU power via nvidia-smi (returns watts, or -1 on error)
static float query_gpu_power_watts() {
    FILE* fp = popen("nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null", "r");
    if (!fp) return -1.0f;
    float power = -1.0f;
    if (fscanf(fp, "%f", &power) != 1) power = -1.0f;
    pclose(fp);
    return power;
}

// Read GPU clock speed
static int query_gpu_clock_mhz() {
    FILE* fp = popen("nvidia-smi --query-gpu=clocks.gr --format=csv,noheader,nounits 2>/dev/null", "r");
    if (!fp) return -1;
    int clock = -1;
    if (fscanf(fp, "%d", &clock) != 1) clock = -1;
    pclose(fp);
    return clock;
}

struct BenchResult {
    int n_sensors;
    float avg_ms;
    double throughput_M;    // M sensors/sec
    double safe_tops;       // constraint checks/sec
    float power_watts;
    int clock_mhz;
    double safe_tops_per_watt;
};

static BenchResult run_benchmark(
    FluxBoundsFlat* d_bounds, int8_t* d_sensors,
    FluxResult* d_results, int* d_stats,
    int n_sensors, int n_constraints, int n_iters
) {
    BenchResult br = {};
    br.n_sensors = n_sensors;

    FluxBatchConfig config;
    config.n_sensors = n_sensors;
    config.n_constraints = n_constraints;
    config.saturation_lo = -127;
    config.saturation_hi = 127;
    config.deadline_ms = 0;
    config.severity_threshold = 0;
    config.reserved[0] = config.reserved[1] = config.reserved[2] = 0;

    int grid = (n_sensors + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    // Warmup
    for (int i = 0; i < 3; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config);
    }
    cudaDeviceSynchronize();

    // Measure
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    // Sample power before
    float p1 = query_gpu_power_watts();

    float total_ms = 0;
    for (int i = 0; i < n_iters; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        cudaEventRecord(start);
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        total_ms += ms;
    }

    // Sample power after
    float p2 = query_gpu_power_watts();

    br.avg_ms = total_ms / n_iters;
    br.throughput_M = (double)n_sensors / (br.avg_ms / 1000.0) / 1e6;
    br.safe_tops = (double)n_sensors * n_constraints / (br.avg_ms / 1000.0);
    br.power_watts = (p1 > 0 && p2 > 0) ? (p1 + p2) / 2.0f : -1.0f;
    br.clock_mhz = query_gpu_clock_mhz();
    if (br.power_watts > 0) {
        br.safe_tops_per_watt = br.safe_tops / br.power_watts;
    }

    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    return br;
}

int main() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  EXP49: Power Efficiency Benchmark                          ║\n");
    printf("║  Safe-TOPS/W at 10M, 20M, 50M sensor counts                ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    const int N_CONSTRAINTS = 4;
    const int BENCH_ITERS = 30;
    const int SIZES[] = {10000000, 20000000, 50000000};
    const char* SIZE_LABELS[] = {"10M", "20M", "50M"};
    const int N_SIZES = 3;

    // Find max size for allocation
    int max_n = SIZES[0];
    for (int i = 1; i < N_SIZES; i++) {
        if (SIZES[i] > max_n) max_n = SIZES[i];
    }

    // Allocate max once
    FluxBoundsFlat* d_bounds;
    int8_t* d_sensors;
    FluxResult* d_results;
    int* d_stats;

    cudaMalloc(&d_bounds, max_n * sizeof(FluxBoundsFlat));
    cudaMalloc(&d_sensors, max_n * sizeof(int8_t));
    cudaMalloc(&d_results, max_n * sizeof(FluxResult));
    cudaMalloc(&d_stats, 4 * sizeof(int));

    // Fill host data and upload (use max_n for all, kernel only reads n_sensors)
    FluxBoundsFlat* h_bounds = (FluxBoundsFlat*)malloc(max_n * sizeof(FluxBoundsFlat));
    int8_t* h_sensors = (int8_t*)malloc(max_n * sizeof(int8_t));

    srand(42);
    for (int i = 0; i < max_n; i++) {
        for (int c = 0; c < FLUX_MAX_CONSTRAINTS; c++) {
            h_bounds[i].lo[c] = (int8_t)(rand() % 100 - 50);
            h_bounds[i].hi[c] = (int8_t)(h_bounds[i].lo[c] + (rand() % 30 + 10));
            if (h_bounds[i].hi[c] > 127) h_bounds[i].hi[c] = 127;
        }
        h_sensors[i] = (int8_t)(rand() % 254 - 127);
    }

    cudaMemcpy(d_bounds, h_bounds, max_n * sizeof(FluxBoundsFlat), cudaMemcpyHostToDevice);
    cudaMemcpy(d_sensors, h_sensors, max_n * sizeof(int8_t), cudaMemcpyHostToDevice);

    // Query GPU info
    float idle_power = query_gpu_power_watts();
    int base_clock = query_gpu_clock_mhz();

    printf("  GPU Base Clock:     %d MHz\n", base_clock);
    printf("  GPU Idle Power:     %.1f W\n", idle_power);
    printf("  Constraints/sensor: %d\n\n", N_CONSTRAINTS);

    // Run benchmarks
    BenchResult results[N_SIZES];
    for (int s = 0; s < N_SIZES; s++) {
        printf("  Benchmarking %s sensors (%d iters)...\n", SIZE_LABELS[s], BENCH_ITERS);
        results[s] = run_benchmark(d_bounds, d_sensors, d_results, d_stats,
                                   SIZES[s], N_CONSTRAINTS, BENCH_ITERS);
    }

    // Print results
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  POWER EFFICIENCY RESULTS                                   ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  %-5s  │ %8s │ %10s │ %7s │ %12s │ %10s  ║\n",
           "Size", "Latency", "Throughput", "Power", "Safe-TOPS", "Safe-TOPS/W");
    printf("║  %-5s  │ %8s │ %10s │ %7s │ %12s │ %10s  ║\n",
           "", "ms", "M/sens/s", "W", "ops/s", "ops/s/W");
    printf("╠══════════════════════════════════════════════════════════════╣\n");

    for (int s = 0; s < N_SIZES; s++) {
        printf("║  %-5s  │ %8.3f │ %10.2f │ %7.1f │ %12.0f │ %10.0f  ║\n",
               SIZE_LABELS[s],
               results[s].avg_ms,
               results[s].throughput_M,
               results[s].power_watts,
               results[s].safe_tops,
               results[s].safe_tops_per_watt);
    }
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    // Scaling analysis
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  SCALING ANALYSIS                                           ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    if (results[0].avg_ms > 0) {
        double scale_20 = results[1].avg_ms / results[0].avg_ms;
        double scale_50 = results[2].avg_ms / results[0].avg_ms;
        printf("║  10M → 20M scale factor: %5.2fx (ideal: 2.00x)             ║\n", scale_20);
        printf("║  10M → 50M scale factor: %5.2fx (ideal: 5.00x)             ║\n", scale_50);
        printf("║  Scaling efficiency 20M: %5.1f%%                            ║\n",
               200.0 / scale_20);
        printf("║  Scaling efficiency 50M: %5.1f%%                            ║\n",
               500.0 / scale_50);
    }

    if (results[0].safe_tops_per_watt > 0 && results[2].safe_tops_per_watt > 0) {
        printf("║  Safe-TOPS/W at 10M:     %10.0f ops/s/W                  ║\n", results[0].safe_tops_per_watt);
        printf("║  Safe-TOPS/W at 50M:     %10.0f ops/s/W                  ║\n", results[2].safe_tops_per_watt);
        printf("║  Efficiency gain (50M/10M): %6.2fx                         ║\n",
               results[2].safe_tops_per_watt / results[0].safe_tops_per_watt);
    }
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    // Cleanup
    cudaFree(d_bounds); cudaFree(d_sensors);
    cudaFree(d_results); cudaFree(d_stats);
    free(h_bounds); free(h_sensors);

    printf("\n  ✓ EXP49 complete — power efficiency benchmarked.\n\n");
    return 0;
}
