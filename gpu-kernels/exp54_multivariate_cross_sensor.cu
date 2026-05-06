// Experiment 54: Multivariate Cross-Sensor Constraint Engine
// Constraints involving relationships BETWEEN sensors, not just individual ranges
//
// Example: "if turbine_temp > 80 AND shaft_vibration > 30 THEN emergency_shutdown"
// This requires evaluating sensor PAIRS (or tuples) against compound constraints.
//
// Architecture: group sensors into logical tuples, evaluate cross-constraints per tuple
// Each tuple can have up to 4 sensors with compound boolean logic

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cuda_runtime.h>

#define SAT8(v) ((int8_t)max(-127, min(127, (int)(v))))
#define BLOCK 256
#define MAX_SENSORS_PER_CONSTRAINT 4

// Cross-sensor constraint: involves indices into a sensor group
struct CrossConstraint {
    int8_t thresholds[MAX_SENSORS_PER_CONSTRAINT]; // Threshold per sensor
    int8_t sensor_offsets[MAX_SENSORS_PER_CONSTRAINT]; // Offset within group (0-3)
    uint8_t logic_mask;   // Which sensors are ANDed (bit = 1 means AND)
    uint8_t comp_mask;    // Comparison: 0 = less than threshold, 1 = greater than
    uint8_t n_sensors;    // How many sensors involved
    uint8_t padding;
};

struct CrossResult {
    uint8_t error_mask;
    uint8_t severity;
    uint8_t triggered_mask;  // Which individual thresholds triggered
    uint8_t padding;
};

// Sensor group: 4 sensors that share cross-constraints
struct SensorGroup {
    int8_t values[MAX_SENSORS_PER_CONSTRAINT];
};

__global__
void cross_sensor_check_kernel(
    const SensorGroup* __restrict__ groups,
    const CrossConstraint* __restrict__ constraints,
    CrossResult* __restrict__ results,
    int* stats,
    int n_groups,
    int n_constraints
) {
    extern __shared__ int smem[];
    if (threadIdx.x < 4) smem[threadIdx.x] = 0;
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n_groups) return;

    SensorGroup g = groups[idx];
    CrossResult r = {0, 0, 0, 0};

    for (int c = 0; c < n_constraints; c++) {
        CrossConstraint cc = constraints[c];
        bool all_triggered = true;
        bool any_triggered = false;
        uint8_t triggered = 0;

        for (int s = 0; s < cc.n_sensors; s++) {
            int off = cc.sensor_offsets[s];
            int8_t val = SAT8(g.values[off]);
            int8_t thr = SAT8(cc.thresholds[s]);

            bool triggered_s;
            if (cc.comp_mask & (1u << s)) {
                triggered_s = (val > thr);  // Greater than threshold
            } else {
                triggered_s = (val < thr);  // Less than threshold
            }

            if (triggered_s) {
                triggered |= (1u << s);
                any_triggered = true;
            } else {
                all_triggered = false;
            }
        }

        // Apply logic: if logic_mask says AND, require all; else OR
        bool constraint_violated;
        if (cc.logic_mask == 0xFF) {
            constraint_violated = all_triggered;  // AND all
        } else {
            constraint_violated = any_triggered;  // OR any
        }

        if (constraint_violated) {
            r.error_mask |= (1u << c);
            r.triggered_mask |= triggered;
        }
    }

    int nv = __popc(r.error_mask);
    if (nv == 0) r.severity = 0;
    else if (nv <= n_constraints / 4) r.severity = 1;
    else if (nv <= n_constraints / 2) r.severity = 2;
    else r.severity = 3;

    results[idx] = r;
    atomicAdd(&smem[r.severity], 1);
    __syncthreads();
    if (threadIdx.x < 4) atomicAdd(&stats[threadIdx.x], smem[threadIdx.x]);
}

int main() {
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  Exp54: Multivariate Cross-Sensor Constraint Engine         ║\n");
    printf("║  Constraints between sensors: AND/OR compound logic         ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    int n_groups = 10000000;  // 10M sensor groups (40M individual sensors)
    int n_constraints = 4;

    // Define cross-sensor constraints (industrial turbine monitoring)
    // Group layout: [turbine_temp, shaft_vibration, oil_pressure, rpm]
    CrossConstraint h_cc[4] = {
        // C0: IF temp > 80 AND vibration > 30 THEN emergency (both must trigger)
        { .thresholds = {80, 30, 0, 0},
          .sensor_offsets = {0, 1, 0, 0},
          .logic_mask = 0xFF, .comp_mask = 0x03, .n_sensors = 2, .padding = 0 },
        // C1: IF oil_pressure < 20 OR rpm > 120 THEN warning (either triggers)
        { .thresholds = {20, 120, 0, 0},
          .sensor_offsets = {2, 3, 0, 0},
          .logic_mask = 0x00, .comp_mask = 0x02, .n_sensors = 2, .padding = 0 },
        // C2: IF temp > 60 AND oil_pressure < 40 AND vibration > 15 THEN caution
        { .thresholds = {60, 40, 15, 0},
          .sensor_offsets = {0, 2, 1, 0},
          .logic_mask = 0xFF, .comp_mask = 0x05, .n_sensors = 3, .padding = 0 },
        // C3: IF rpm > 100 AND vibration > 25 AND oil_pressure < 30 THEN critical
        { .thresholds = {100, 25, 30, 0},
          .sensor_offsets = {3, 1, 2, 0},
          .logic_mask = 0xFF, .comp_mask = 0x07, .n_sensors = 3, .padding = 0 },
    };

    // Generate sensor group data
    SensorGroup* h_groups = new SensorGroup[n_groups];
    srand(42);
    for (int i = 0; i < n_groups; i++) {
        // Normal operating range with occasional excursions
        h_groups[i].values[0] = SAT8(40 + (rand() % 80) - 20);   // temp: 20-100
        h_groups[i].values[1] = SAT8(10 + (rand() % 40) - 5);    // vibration: 5-45
        h_groups[i].values[2] = SAT8(30 + (rand() % 40));         // oil pressure: 30-70
        h_groups[i].values[3] = SAT8(50 + (rand() % 80));         // rpm: 50-130

        // Inject emergency conditions in 0.5% of groups
        if (i % 200 == 0) {
            h_groups[i].values[0] = 90;  // high temp
            h_groups[i].values[1] = 40;  // high vibration
        }
    }

    // GPU
    SensorGroup* d_groups;
    CrossConstraint* d_cc;
    CrossResult* d_results;
    int* d_stats;

    cudaMalloc(&d_groups, n_groups * sizeof(SensorGroup));
    cudaMalloc(&d_cc, n_constraints * sizeof(CrossConstraint));
    cudaMalloc(&d_results, n_groups * sizeof(CrossResult));
    cudaMalloc(&d_stats, 4 * sizeof(int));

    cudaMemcpy(d_groups, h_groups, n_groups * sizeof(SensorGroup), cudaMemcpyHostToDevice);
    cudaMemcpy(d_cc, h_cc, n_constraints * sizeof(CrossConstraint), cudaMemcpyHostToDevice);

    int grid = (n_groups + BLOCK - 1) / BLOCK;
    size_t smem = 4 * sizeof(int);

    // Warmup
    for (int i = 0; i < 10; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        cross_sensor_check_kernel<<<grid, BLOCK, smem>>>(d_groups, d_cc, d_results, d_stats, n_groups, n_constraints);
    }
    cudaDeviceSynchronize();

    // Benchmark
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    int iters = 500;
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        cross_sensor_check_kernel<<<grid, BLOCK, smem>>>(d_groups, d_cc, d_results, d_stats, n_groups, n_constraints);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float ms = 0;
    cudaEventElapsedTime(&ms, start, stop);

    int stats[4];
    cudaMemcpy(stats, d_stats, 4 * sizeof(int), cudaMemcpyDeviceToHost);

    // Sample results
    CrossResult h_res[10];
    cudaMemcpy(h_res, d_results, 10 * sizeof(CrossResult), cudaMemcpyDeviceToHost);

    double total_checks = (double)n_groups * n_constraints * iters;
    double rate = total_checks / (ms / 1000.0);
    // Each group has 4 sensors → total individual sensor checks
    double sensor_checks = (double)n_groups * MAX_SENSORS_PER_CONSTRAINT * iters;
    double sensor_rate = sensor_checks / (ms / 1000.0);

    printf("  Groups: %d (40M individual sensors, 4 per group)\n", n_groups);
    printf("  Cross-constraints: %d (2-3 sensors each, AND/OR logic)\n\n", n_constraints);

    printf("  ┌──────────────────────────────────────────────────────────┐\n");
    printf("  │ Cross-constraint throughput:  %.2f B constraint checks/s │\n", rate / 1e9);
    printf("  │ Equivalent sensor rate:       %.2f B sensor checks/s     │\n", sensor_rate / 1e9);
    printf("  │ Per-iteration:                %.4f ms                    │\n", ms / iters);
    printf("  ├──────────────────────────────────────────────────────────┤\n");
    printf("  │ Pass:     %8d (%5.1f%%)                               \n", stats[0], 100.0*stats[0]/n_groups);
    printf("  │ Caution:  %8d (%5.1f%%)                               \n", stats[1], 100.0*stats[1]/n_groups);
    printf("  │ Warning:  %8d (%5.1f%%)                               \n", stats[2], 100.0*stats[2]/n_groups);
    printf("  │ Critical: %8d (%5.1f%%)                               \n", stats[3], 100.0*stats[3]/n_groups);
    printf("  └──────────────────────────────────────────────────────────┘\n");

    printf("\n  Sample cross-sensor results:\n");
    printf("  %-4s %-10s %-10s %-10s\n", "Idx", "Error", "Triggered", "Severity");
    for (int i = 0; i < 5; i++) {
        printf("  %-4d 0x%02X      0x%02X       %d\n",
            i, h_res[i].error_mask, h_res[i].triggered_mask, h_res[i].severity);
    }

    // Compare with individual sensor checking
    printf("\n  Comparison: cross-sensor vs individual sensor checking\n");
    printf("    Individual (10M × 8c):  62.2 B c/s (exp20 production kernel)\n");
    printf("    Cross-sensor (10M × 4c × 4s): %.2f B c/s (this experiment)\n", rate / 1e9);
    printf("    Overhead of cross-sensor logic: %.1f%%\n",
        100.0 * (1.0 - rate / (62.2e9 * iters / (double)iters)));

    printf("\n  ✓ EXP54 complete — multivariate cross-sensor constraints benchmarked.\n");

    cudaFree(d_groups); cudaFree(d_cc); cudaFree(d_results); cudaFree(d_stats);
    cudaEventDestroy(start); cudaEventDestroy(stop);
    delete[] h_groups;
    return 0;
}
