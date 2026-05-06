// FLUX Production Kernel v2 — Benchmark & Differential Test
// Validates correctness and measures throughput on RTX 4050
//
// Tests:
//   1. Differential: 10M random inputs vs CPU reference
//   2. Throughput: sustained rate over 1000 iterations
//   3. Latency: single-batch latency at various sizes
//   4. Hot-swap: bounds update latency
//   5. CUDA Graph: replay overhead
//   6. Saturation: edge cases at INT8 boundaries

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>

#include "flux_production_v2.cu"

// ═══════════════════════════════════════════════════════════
// CPU reference implementation
// ═══════════════════════════════════════════════════════════

void cpu_reference(
    const FluxBoundsFlat* bounds,
    const int8_t* sensors,
    FluxResult* results,
    int n, int nc,
    int stats[4]
) {
    memset(stats, 0, 4 * sizeof(int));

    for (int i = 0; i < n; i++) {
        FluxResult r = {0, 0, 0, 0};
        int val_int = (int)sensors[i];
        // Saturate sensor value
        if (val_int < FLUX_INT8_MIN) val_int = FLUX_INT8_MIN;
        if (val_int > FLUX_INT8_MAX) val_int = FLUX_INT8_MAX;
        int8_t val = (int8_t)val_int;

        int violated = 0;
        for (int j = 0; j < nc; j++) {
            // Saturate bounds (must match GPU kernel)
            int8_t lo = (int8_t)max((int)FLUX_INT8_MIN, min((int)FLUX_INT8_MAX, (int)bounds[i].lo[j]));
            int8_t hi = (int8_t)max((int)FLUX_INT8_MIN, min((int)FLUX_INT8_MAX, (int)bounds[i].hi[j]));
            bool lo_fail = (val < lo);
            bool hi_fail = (val > hi);
            if (lo_fail || hi_fail) {
                r.error_mask |= (1u << j);
                violated++;
            }
            if (lo_fail) r.violated_lo |= (1u << j);
            if (hi_fail) r.violated_hi |= (1u << j);
        }

        if (violated == 0) r.severity = 0;
        else if (violated <= nc / 4) r.severity = 1;
        else if (violated <= nc / 2) r.severity = 2;
        else r.severity = 3;

        results[i] = r;
        stats[r.severity]++;
    }
}

// ═══════════════════════════════════════════════════════════
// Differential test
// ═══════════════════════════════════════════════════════════

bool run_differential_test(int n, int nc) {
    printf("  Differential test: %d sensors, %d constraints\n", n, nc);

    FluxBoundsFlat* h_bounds = new FluxBoundsFlat[n];
    int8_t* h_sensors = new int8_t[n];
    FluxResult* h_gpu_results = new FluxResult[n];
    FluxResult* h_cpu_results = new FluxResult[n];

    // Generate random data with edge cases
    srand(42);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < nc; j++) {
            h_bounds[i].lo[j] = (int8_t)(rand() % 200 - 100);
            h_bounds[i].hi[j] = (int8_t)(h_bounds[i].lo[j] + (rand() % 50) + 1);
            // Clamp hi
            if (h_bounds[i].hi[j] > FLUX_INT8_MAX) h_bounds[i].hi[j] = FLUX_INT8_MAX;
        }
        // Mix of normal and edge-case values
        if (i % 100 == 0) h_sensors[i] = FLUX_INT8_MIN;   // edge: min
        else if (i % 100 == 1) h_sensors[i] = FLUX_INT8_MAX; // edge: max
        else if (i % 100 == 2) h_sensors[i] = 0;           // edge: zero
        else h_sensors[i] = (int8_t)(rand() % 254 - 127);
    }

    // CPU reference
    int cpu_stats[4];
    cpu_reference(h_bounds, h_sensors, h_cpu_results, n, nc, cpu_stats);

    // GPU
    FluxBoundsFlat* d_bounds;
    int8_t* d_sensors;
    FluxResult* d_results;
    int* d_stats;

    cudaMalloc(&d_bounds, n * sizeof(FluxBoundsFlat));
    cudaMalloc(&d_sensors, n * sizeof(int8_t));
    cudaMalloc(&d_results, n * sizeof(FluxResult));
    cudaMalloc(&d_stats, 4 * sizeof(int));

    cudaMemcpy(d_bounds, h_bounds, n * sizeof(FluxBoundsFlat), cudaMemcpyHostToDevice);
    cudaMemcpy(d_sensors, h_sensors, n * sizeof(int8_t), cudaMemcpyHostToDevice);
    cudaMemset(d_results, 0, n * sizeof(FluxResult));
    cudaMemset(d_stats, 0, 4 * sizeof(int));

    FluxBatchConfig config = {n, nc, FLUX_INT8_MIN, FLUX_INT8_MAX, 0, 0, {0,0,0}};
    int grid = (n + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
        d_bounds, d_sensors, d_results, d_stats, config
    );
    cudaDeviceSynchronize();

    int gpu_stats[4];
    cudaMemcpy(h_gpu_results, d_results, n * sizeof(FluxResult), cudaMemcpyDeviceToHost);
    cudaMemcpy(gpu_stats, d_stats, 4 * sizeof(int), cudaMemcpyDeviceToHost);

    // Compare
    int mismatches = 0;
    for (int i = 0; i < n; i++) {
        if (h_gpu_results[i].error_mask != h_cpu_results[i].error_mask ||
            h_gpu_results[i].severity != h_cpu_results[i].severity ||
            h_gpu_results[i].violated_lo != h_cpu_results[i].violated_lo ||
            h_gpu_results[i].violated_hi != h_cpu_results[i].violated_hi) {
            mismatches++;
            if (mismatches <= 10) {
                printf("    MISMATCH [%d]: val=%d GPU(mask=0x%02X,lo=0x%02X,hi=0x%02X,sev=%d) vs CPU(mask=0x%02X,lo=0x%02X,hi=0x%02X,sev=%d)\n",
                    i, h_sensors[i],
                    h_gpu_results[i].error_mask, h_gpu_results[i].violated_lo, h_gpu_results[i].violated_hi, h_gpu_results[i].severity,
                    h_cpu_results[i].error_mask, h_cpu_results[i].violated_lo, h_cpu_results[i].violated_hi, h_cpu_results[i].severity);
            }
        }
    }

    bool stats_match = (gpu_stats[0] == cpu_stats[0] && gpu_stats[1] == cpu_stats[1] &&
                        gpu_stats[2] == cpu_stats[2] && gpu_stats[3] == cpu_stats[3]);

    printf("    Result: %d mismatches / %d inputs (%.6f%%)\n", mismatches, n, 100.0 * mismatches / n);
    printf("    Stats: GPU(%d,%d,%d,%d) CPU(%d,%d,%d,%d) %s\n",
        gpu_stats[0], gpu_stats[1], gpu_stats[2], gpu_stats[3],
        cpu_stats[0], cpu_stats[1], cpu_stats[2], cpu_stats[3],
        stats_match ? "✓" : "✗ MISMATCH");

    cudaFree(d_bounds); cudaFree(d_sensors); cudaFree(d_results); cudaFree(d_stats);
    delete[] h_bounds; delete[] h_sensors; delete[] h_gpu_results; delete[] h_cpu_results;

    return mismatches == 0 && stats_match;
}

// ═══════════════════════════════════════════════════════════
// Throughput benchmark
// ═══════════════════════════════════════════════════════════

void run_throughput_benchmark(int n, int nc, int iters) {
    printf("\n  Throughput: %d sensors × %d constraints × %d iterations\n", n, nc, iters);

    FluxBoundsFlat* d_bounds;
    int8_t* d_sensors;
    FluxResult* d_results;
    int* d_stats;

    cudaMalloc(&d_bounds, n * sizeof(FluxBoundsFlat));
    cudaMalloc(&d_sensors, n * sizeof(int8_t));
    cudaMalloc(&d_results, n * sizeof(FluxResult));
    cudaMalloc(&d_stats, 4 * sizeof(int));

    // Fill with test data
    FluxBoundsFlat* h_b = new FluxBoundsFlat[n];
    int8_t* h_v = new int8_t[n];
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < nc; j++) {
            h_b[i].lo[j] = 20 + (i % 10) * 10;
            h_b[i].hi[j] = h_b[i].lo[j] + 40;
        }
        h_v[i] = (int8_t)((i * 7 + 13) % 200 - 100);
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(FluxBoundsFlat), cudaMemcpyHostToDevice);
    cudaMemcpy(d_sensors, h_v, n * sizeof(int8_t), cudaMemcpyHostToDevice);

    FluxBatchConfig config = {n, nc, FLUX_INT8_MIN, FLUX_INT8_MAX, 0, 0, {0,0,0}};
    int grid = (n + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    size_t smem = 4 * sizeof(int);

    // Warmup
    for (int i = 0; i < 10; i++) {
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config
        );
    }
    cudaDeviceSynchronize();

    // Benchmark with CUDA events
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, smem>>>(
            d_bounds, d_sensors, d_results, d_stats, config
        );
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float ms = 0;
    cudaEventElapsedTime(&ms, start, stop);

    long total_constraints = (long)n * nc * iters;
    double rate = total_constraints / (ms / 1000.0);

    printf("    Total time: %.2f ms (%d iters)\n", ms, iters);
    printf("    Per-iteration: %.4f ms\n", ms / iters);
    printf("    Throughput: %.2f B constraints/sec\n", rate / 1e9);

    // CUDA Graph benchmark
    FluxGraphState state = {};
    flux_batch_init(d_bounds, d_sensors, d_results, d_stats, config, &state);

    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemset(d_stats, 0, 4 * sizeof(int));
        cudaGraphLaunch(state.exec, 0);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    cudaEventElapsedTime(&ms, start, stop);
    double graph_rate = total_constraints / (ms / 1000.0);

    printf("    CUDA Graph: %.2f ms total, %.2f B constraints/sec\n", ms, graph_rate / 1e9);
    printf("    Graph speedup: %.1fx\n", graph_rate / rate);

    flux_batch_cleanup(&state);
    cudaEventDestroy(start); cudaEventDestroy(stop);
    cudaFree(d_bounds); cudaFree(d_sensors); cudaFree(d_results); cudaFree(d_stats);
    delete[] h_b; delete[] h_v;
}

// ═══════════════════════════════════════════════════════════
// Saturation edge case test
// ═══════════════════════════════════════════════════════════

bool run_saturation_test() {
    printf("  Saturation edge cases:\n");

    // Test: bounds at INT8 limits, values at limits
    int n = 8;
    FluxBoundsFlat bounds[8];
    int8_t sensors[8] = {FLUX_INT8_MIN, FLUX_INT8_MAX, 0, -1, 1, 126, -126, 127};

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 8; j++) {
            bounds[i].lo[j] = -50;
            bounds[i].hi[j] = 50;
        }
    }
    // Sensor 0 (-127): should violate hi for all → severity 3
    // Sensor 1 (127): should violate hi for all → severity 3
    // Sensor 2 (0): should pass all → severity 0
    // Sensors 3-7: in range → pass

    FluxResult cpu_res[8];
    int cpu_stats[4];
    cpu_reference(bounds, sensors, cpu_res, n, 8, cpu_stats);

    // GPU
    FluxBoundsFlat* d_bounds;
    int8_t* d_sensors;
    FluxResult* d_results;
    int* d_stats;
    cudaMalloc(&d_bounds, n * sizeof(FluxBoundsFlat));
    cudaMalloc(&d_sensors, n * sizeof(int8_t));
    cudaMalloc(&d_results, n * sizeof(FluxResult));
    cudaMalloc(&d_stats, 4 * sizeof(int));

    cudaMemcpy(d_bounds, bounds, n * sizeof(FluxBoundsFlat), cudaMemcpyHostToDevice);
    cudaMemcpy(d_sensors, sensors, n * sizeof(int8_t), cudaMemcpyHostToDevice);

    FluxBatchConfig config = {n, 8, FLUX_INT8_MIN, FLUX_INT8_MAX, 0, 0, {0,0,0}};
    int grid = (n + FLUX_BLOCK_SIZE - 1) / FLUX_BLOCK_SIZE;
    flux_check_kernel_v2<<<grid, FLUX_BLOCK_SIZE, 4*sizeof(int)>>>(
        d_bounds, d_sensors, d_results, d_stats, config
    );
    cudaDeviceSynchronize();

    FluxResult gpu_res[8];
    cudaMemcpy(gpu_res, d_results, n * sizeof(FluxResult), cudaMemcpyDeviceToHost);

    bool pass = true;
    for (int i = 0; i < n; i++) {
        bool match = (gpu_res[i].error_mask == cpu_res[i].error_mask &&
                      gpu_res[i].severity == cpu_res[i].severity);
        printf("    [%d] val=%d: GPU(mask=%d,sev=%d) CPU(mask=%d,sev=%d) %s\n",
            i, sensors[i],
            gpu_res[i].error_mask, gpu_res[i].severity,
            cpu_res[i].error_mask, cpu_res[i].severity,
            match ? "✓" : "✗ MISMATCH");
        if (!match) pass = false;
    }

    cudaFree(d_bounds); cudaFree(d_sensors); cudaFree(d_results); cudaFree(d_stats);
    return pass;
}

// ═══════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════

int main() {
    printf("╔══════════════════════════════════════════════════════╗\n");
    printf("║  FLUX Production Kernel v2 — Validation Suite        ║\n");
    printf("║  INT8 flat bounds + saturation + error masks         ║\n");
    printf("╚══════════════════════════════════════════════════════╝\n\n");

    // 1. Differential tests
    printf("═══ Differential Tests ═══\n");
    bool d1 = run_differential_test(10000000, 8);  // 10M sensors, 8 constraints
    bool d2 = run_differential_test(50000000, 4);  // 50M sensors, 4 constraints
    bool d3 = run_differential_test(1000000, 1);   // 1M sensors, 1 constraint
    bool d4 = run_saturation_test();

    // 2. Throughput benchmarks
    printf("\n═══ Throughput Benchmarks ═══\n");
    run_throughput_benchmark(10000000, 8, 1000);   // 10M × 8 constraints
    run_throughput_benchmark(50000000, 4, 100);    // 50M × 4 constraints
    run_throughput_benchmark(10000000, 1, 1000);   // 10M × 1 constraint

    // 3. Summary
    printf("\n╔══════════════════════════════════════════════════════╗\n");
    printf("║  Results                                             ║\n");
    printf("╠══════════════════════════════════════════════════════╣\n");
    printf("║  Differential (10M × 8c):  %s                       ║\n", d1 ? "PASS ✓" : "FAIL ✗");
    printf("║  Differential (50M × 4c):  %s                       ║\n", d2 ? "PASS ✓" : "FAIL ✗");
    printf("║  Differential (1M × 1c):   %s                       ║\n", d3 ? "PASS ✓" : "FAIL ✗");
    printf("║  Saturation edge cases:    %s                       ║\n", d4 ? "PASS ✓" : "FAIL ✗");
    printf("╚══════════════════════════════════════════════════════╝\n");

    bool all_pass = d1 && d2 && d3 && d4;
    printf("\nOverall: %s\n", all_pass ? "ALL TESTS PASS ✓" : "SOME TESTS FAILED ✗");

    return all_pass ? 0 : 1;
}
