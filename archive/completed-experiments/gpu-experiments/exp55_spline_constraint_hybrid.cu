/*
 * EXP55: Spline-Constraint Hybrid GPU Kernel
 * 
 * Evaluates 100M quadratic Bézier splines AND checks INT8 constraints
 * in a single GPU pass. No CPU round-trip.
 *
 * Forgemaster ⚒️ — Night Shift 2026-05-06
 */

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
#include <chrono>

// INT8 saturated arithmetic
__device__ __host__ inline int8_t sat8(int32_t v) {
    return (int8_t)((v > 127) ? 127 : (v < -127) ? -127 : v);
}

// Quadratic Bézier evaluation (returns y given x-normalized t)
__device__ inline float quad_bezier_y(float t, float rise) {
    // B(t) = 4 * rise * t * (1-t) for control points (0,0), (0.5, 2*rise), (1, 0)
    return 4.0f * rise * t * (1.0f - t);
}

// Bézier curvature
__device__ inline float quad_bezier_curvature(float t, float rise, float span) {
    // For our parameterization: x = span*t, y = 4*rise*t*(1-t)
    // dx/dt = span, dy/dt = 4*rise*(1-2t)
    // d2x/dt2 = 0, d2y/dt2 = -8*rise
    // κ = |dx*d2y - dy*d2x| / (dx^2 + dy^2)^(3/2)
    float dx = span;
    float dy = 4.0f * rise * (1.0f - 2.0f * t);
    float d2y = -8.0f * rise;
    float numer = fabsf(dx * d2y);
    float denom = powf(dx * dx + dy * dy, 1.5f);
    return (denom > 1e-15f) ? numer / denom : 0.0f;
}

// INT8 constraint check: is value within [lo, hi] with INT8 saturation?
__device__ inline int check_constraint_int8(int8_t value, int8_t lo, int8_t hi) {
    return (value >= lo && value <= hi) ? 1 : 0;
}

/*
 * Hybrid kernel: For each spline configuration:
 *   1. Evaluate Bézier at N sample points
 *   2. Convert to INT8
 *   3. Check constraints
 *   4. Count passes/fails
 */
__global__ void spline_constraint_hybrid(
    // Per-config parameters (flattened)
    const float* __restrict__ rises,      // [num_configs] rise/span ratio
    const float* __restrict__ spans,      // [num_configs] span in mm
    const int8_t* __restrict__ lo_bounds, // [num_configs] INT8 lower bound
    const int8_t* __restrict__ hi_bounds, // [num_configs] INT8 upper bound
    // Output
    int* __restrict__ pass_counts,        // [num_configs]
    int* __restrict__ fail_counts,        // [num_configs]
    float* __restrict__ max_curvatures,   // [num_configs]
    float* __restrict__ energies,         // [num_configs]
    // Parameters
    int num_configs,
    int samples_per_config
) {
    int cfg = blockIdx.x * blockDim.x + threadIdx.x;
    if (cfg >= num_configs) return;

    float rise = rises[cfg];
    float span = spans[cfg];
    int8_t lo = lo_bounds[cfg];
    int8_t hi = hi_bounds[cfg];

    int passes = 0;
    int fails = 0;
    float max_kappa = 0.0f;
    float energy = 0.0f;

    float prev_y = 0.0f;
    float prev_kappa = 0.0f;

    for (int s = 0; s <= samples_per_config; s++) {
        float t = (float)s / samples_per_config;
        float y = quad_bezier_y(t, rise);
        float kappa = quad_bezier_curvature(t, rise, span);

        // Convert y to INT8 (map rise to ±100 range)
        float y_norm = y / (4.0f * rise) * 100.0f;  // normalize to [0, 100]
        int8_t y_int8 = sat8((int32_t)roundf(y_norm));

        // Check constraint
        if (check_constraint_int8(y_int8, lo, hi)) {
            passes++;
        } else {
            fails++;
        }

        // Track max curvature
        if (kappa > max_kappa) max_kappa = kappa;

        // Accumulate energy (∫κ² ds)
        if (s > 0) {
            float ds = span / samples_per_config;
            float k_avg = 0.5f * (kappa + prev_kappa);
            energy += k_avg * k_avg * ds;
        }

        prev_y = y;
        prev_kappa = kappa;
    }

    pass_counts[cfg] = passes;
    fail_counts[cfg] = fails;
    max_curvatures[cfg] = max_kappa;
    energies[cfg] = energy;
}

/*
 * Boundary finder kernel: Binary search for exact h/L threshold
 * where Bézier error exceeds tolerance
 */
__global__ void find_breakpoint_hl(
    const float* __restrict__ tolerances,  // [num_tests] error tolerance (fraction of δ)
    float* __restrict__ breakpoints,       // [num_tests] output h/L threshold
    int num_tests,
    int samples,
    int iterations
) {
    int idx = blockIdx.x * threadIdx.x + threadIdx.x;
    if (idx >= num_tests) return;

    float tol = tolerances[idx];
    float lo = 0.0f, hi = 0.5f;

    for (int iter = 0; iter < iterations; iter++) {
        float mid = 0.5f * (lo + hi);
        float span = 1000.0f;
        float rise = span * mid;

        // Compute max error between Bézier and quartic (Euler-Bernoulli)
        float max_err = 0.0f;
        for (int s = 0; s <= samples; s++) {
            float t = (float)s / samples;
            float u = t;  // x = span * t

            // Bézier y
            float b_y = 4.0f * rise * t * (1.0f - t);

            // Euler-Bernoulli y (normalized to have same max deflection)
            float delta = rise;  // max deflection
            float eb_y = (16.0f * delta / 5.0f) * (u - 2.0f*u*u*u + u*u*u*u);

            float err = fabsf(b_y - eb_y);
            if (err > max_err) max_err = err;
        }

        // Relative error = max_err / delta
        float rel_err = (rise > 1e-10f) ? max_err / rise : 0.0f;

        if (rel_err < tol) {
            lo = mid;  // safe, increase h/L
        } else {
            hi = mid;  // too much error, decrease h/L
        }
    }

    breakpoints[idx] = 0.5f * (lo + hi);
}

/*
 * Inverse solver kernel: Given a target curve (y values at sample points),
 * find optimal rise that minimizes MSE between Bézier and target
 */
__global__ void inverse_spline_solver(
    const float* __restrict__ target_y,    // [num_curves * samples] target y values
    float* __restrict__ optimal_rises,     // [num_curves] output optimal rise
    float* __restrict__ optimal_errors,    // [num_curves] output MSE
    int num_curves,
    int samples,
    int search_steps
) {
    int idx = blockIdx.x * threadIdx.x + threadIdx.x;
    if (idx >= num_curves) return;

    const float* my_target = target_y + idx * samples;
    float span = 1000.0f;

    float best_rise = 0.0f;
    float best_mse = 1e30f;

    // Grid search over rise values
    for (int step = 0; step < search_steps; step++) {
        float rise = span * 0.001f * (step + 1);  // h/L from 0.001 to search_steps * 0.001
        float mse = 0.0f;

        for (int s = 0; s < samples; s++) {
            float t = (float)s / (samples - 1);
            float b_y = quad_bezier_y(t, rise);
            float diff = b_y - my_target[s];
            mse += diff * diff;
        }
        mse /= samples;

        if (mse < best_mse) {
            best_mse = mse;
            best_rise = rise;
        }
    }

    // Refine with finer grid around best
    float rise_lo = fmaxf(0.0f, best_rise - span * 0.001f);
    float rise_hi = best_rise + span * 0.001f;
    for (int step = 0; step < 100; step++) {
        float rise = rise_lo + (rise_hi - rise_lo) * step / 100.0f;
        float mse = 0.0f;
        for (int s = 0; s < samples; s++) {
            float t = (float)s / (samples - 1);
            float b_y = quad_bezier_y(t, rise);
            float diff = b_y - my_target[s];
            mse += diff * diff;
        }
        mse /= samples;
        if (mse < best_mse) {
            best_mse = mse;
            best_rise = rise;
        }
    }

    optimal_rises[idx] = best_rise;
    optimal_errors[idx] = best_mse;
}

// ============================================================================
// Host code
// ============================================================================

int main() {
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║  EXP55-57: Spline-Constraint Hybrid GPU Experiments    ║\n");
    printf("║  Forgemaster ⚒️ Night Shift 2026-05-06                 ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n\n");

    // ========================================================================
    // EXP55: Hybrid Spline + INT8 Constraint Check — 10M configurations
    // ========================================================================
    printf("━━━ EXP55: Spline-Constraint Hybrid (10M configs) ━━━\n\n");

    const int NUM_CONFIGS = 10'000'000;
    const int SAMPLES = 20;

    // Allocate host memory
    float *h_rises, *h_spans;
    int8_t *h_lo, *h_hi;
    int *h_passes, *h_fails;
    float *h_max_kappa, *h_energy;

    h_rises = (float*)malloc(NUM_CONFIGS * sizeof(float));
    h_spans = (float*)malloc(NUM_CONFIGS * sizeof(float));
    h_lo = (int8_t*)malloc(NUM_CONFIGS);
    h_hi = (int8_t*)malloc(NUM_CONFIGS);
    h_passes = (int*)malloc(NUM_CONFIGS * sizeof(int));
    h_fails = (int*)malloc(NUM_CONFIGS * sizeof(int));
    h_max_kappa = (float*)malloc(NUM_CONFIGS * sizeof(float));
    h_energy = (float*)malloc(NUM_CONFIGS * sizeof(float));

    // Generate random configs
    srand(42);
    int total_pass = 0, total_fail = 0;
    for (int i = 0; i < NUM_CONFIGS; i++) {
        h_rises[i] = (100.0f + (rand() % 10000)) * (0.01f + 0.49f * (rand() % 100) / 100.0f);
        h_spans[i] = 100.0f + (rand() % 10000);
        h_lo[i] = sat8(-127 + rand() % 255);
        h_hi[i] = sat8(h_lo[i] + rand() % 100);
    }

    // Allocate device memory
    float *d_rises, *d_spans, *d_max_kappa, *d_energy;
    int8_t *d_lo, *d_hi;
    int *d_passes, *d_fails;

    cudaMalloc(&d_rises, NUM_CONFIGS * sizeof(float));
    cudaMalloc(&d_spans, NUM_CONFIGS * sizeof(float));
    cudaMalloc(&d_lo, NUM_CONFIGS);
    cudaMalloc(&d_hi, NUM_CONFIGS);
    cudaMalloc(&d_passes, NUM_CONFIGS * sizeof(int));
    cudaMalloc(&d_fails, NUM_CONFIGS * sizeof(int));
    cudaMalloc(&d_max_kappa, NUM_CONFIGS * sizeof(float));
    cudaMalloc(&d_energy, NUM_CONFIGS * sizeof(float));

    cudaMemcpy(d_rises, h_rises, NUM_CONFIGS * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_spans, h_spans, NUM_CONFIGS * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_lo, h_lo, NUM_CONFIGS, cudaMemcpyHostToDevice);
    cudaMemcpy(d_hi, h_hi, NUM_CONFIGS, cudaMemcpyHostToDevice);

    int block_size = 256;
    int grid_size = (NUM_CONFIGS + block_size - 1) / block_size;

    // Warmup
    spline_constraint_hybrid<<<grid_size, block_size>>>(
        d_rises, d_spans, d_lo, d_hi,
        d_passes, d_fails, d_max_kappa, d_energy,
        NUM_CONFIGS, SAMPLES);
    cudaDeviceSynchronize();

    // Timed run
    auto start = std::chrono::high_resolution_clock::now();

    spline_constraint_hybrid<<<grid_size, block_size>>>(
        d_rises, d_spans, d_lo, d_hi,
        d_passes, d_fails, d_max_kappa, d_energy,
        NUM_CONFIGS, SAMPLES);
    cudaDeviceSynchronize();

    auto end = std::chrono::high_resolution_clock::now();
    float ms = std::chrono::duration<float, std::milli>(end - start).count();

    cudaMemcpy(h_passes, d_passes, NUM_CONFIGS * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_fails, d_fails, NUM_CONFIGS * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_max_kappa, d_max_kappa, NUM_CONFIGS * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_energy, d_energy, NUM_CONFIGS * sizeof(float), cudaMemcpyDeviceToHost);

    // Aggregate results
    long long total_p = 0, total_f = 0;
    float global_max_kappa = 0.0f;
    float total_energy = 0.0f;
    for (int i = 0; i < NUM_CONFIGS; i++) {
        total_p += h_passes[i];
        total_f += h_fails[i];
        if (h_max_kappa[i] > global_max_kappa) global_max_kappa = h_max_kappa[i];
        total_energy += h_energy[i];
    }

    long long total_constraints = (long long)NUM_CONFIGS * (SAMPLES + 1);
    float c_per_s = total_constraints / (ms / 1000.0f);

    printf("  Configs:        %d\n", NUM_CONFIGS);
    printf("  Samples/config: %d\n", SAMPLES);
    printf("  Total checks:   %lld\n", total_constraints);
    printf("  Time:           %.2f ms\n", ms);
    printf("  Throughput:     %.2f B spline-constraints/sec\n", c_per_s / 1e9f);
    printf("  Pass rate:      %.4f%%\n", 100.0f * total_p / total_constraints);
    printf("  Fail rate:      %.4f%%\n", 100.0f * total_f / total_constraints);
    printf("  Max curvature:  %.8f\n", global_max_kappa);
    printf("  Total energy:   %.2f\n", total_energy);
    printf("\n");

    // ========================================================================
    // EXP56: Binary Search for Exact h/L Breakpoint
    // ========================================================================
    printf("━━━ EXP56: h/L Breakpoint Binary Search ━━━\n\n");

    const int NUM_TESTS = 11;
    float h_tolerances[NUM_TESTS] = {0.01f, 0.02f, 0.03f, 0.05f, 0.07f, 0.10f, 0.15f, 0.20f, 0.25f, 0.30f, 0.50f};
    float h_breakpoints[NUM_TESTS];

    float *d_tolerances, *d_breakpoints;
    cudaMalloc(&d_tolerances, NUM_TESTS * sizeof(float));
    cudaMalloc(&d_breakpoints, NUM_TESTS * sizeof(float));
    cudaMemcpy(d_tolerances, h_tolerances, NUM_TESTS * sizeof(float), cudaMemcpyHostToDevice);

    find_breakpoint_hl<<<1, NUM_TESTS>>>(
        d_tolerances, d_breakpoints, NUM_TESTS, 1000, 50);
    cudaDeviceSynchronize();

    cudaMemcpy(h_breakpoints, d_breakpoints, NUM_TESTS * sizeof(float), cudaMemcpyDeviceToHost);

    printf("  Tolerance (δ)  │  Max h/L  │  Max rise at L=1000mm\n");
    printf("  ───────────────┼───────────┼──────────────────────\n");
    for (int i = 0; i < NUM_TESTS; i++) {
        printf("  %.2f%%          │  %.4f   │  %.1f mm\n",
            h_tolerances[i] * 100, h_breakpoints[i], h_breakpoints[i] * 1000);
    }
    printf("\n");

    // ========================================================================
    // EXP57: Inverse Spline Solver — Find optimal rise for 100K target curves
    // ========================================================================
    printf("━━━ EXP57: Inverse Spline Solver (100K curves) ━━━\n\n");

    const int NUM_CURVES = 100'000;
    const int CURVE_SAMPLES = 50;

    float *h_target_y = (float*)malloc(NUM_CURVES * CURVE_SAMPLES * sizeof(float));
    float *h_opt_rises = (float*)malloc(NUM_CURVES * sizeof(float));
    float *h_opt_errors = (float*)malloc(NUM_CURVES * sizeof(float));

    // Generate target curves: quartic (Euler-Bernoulli) shapes with random h/L
    for (int i = 0; i < NUM_CURVES; i++) {
        float hl = 0.01f + 0.49f * (rand() % 1000) / 1000.0f;
        float span = 1000.0f;
        float delta = span * hl;
        for (int s = 0; s < CURVE_SAMPLES; s++) {
            float u = (float)s / (CURVE_SAMPLES - 1);
            // Euler-Bernoulli shape
            h_target_y[i * CURVE_SAMPLES + s] = (16.0f * delta / 5.0f) * (u - 2.0f*u*u*u + u*u*u*u);
        }
    }

    float *d_target_y, *d_opt_rises, *d_opt_errors;
    cudaMalloc(&d_target_y, NUM_CURVES * CURVE_SAMPLES * sizeof(float));
    cudaMalloc(&d_opt_rises, NUM_CURVES * sizeof(float));
    cudaMalloc(&d_opt_errors, NUM_CURVES * sizeof(float));
    cudaMemcpy(d_target_y, h_target_y, NUM_CURVES * CURVE_SAMPLES * sizeof(float), cudaMemcpyHostToDevice);

    int inv_grid = (NUM_CURVES + 255) / 256;

    auto inv_start = std::chrono::high_resolution_clock::now();
    inverse_spline_solver<<<inv_grid, 256>>>(
        d_target_y, d_opt_rises, d_opt_errors,
        NUM_CURVES, CURVE_SAMPLES, 500);
    cudaDeviceSynchronize();
    auto inv_end = std::chrono::high_resolution_clock::now();
    float inv_ms = std::chrono::duration<float, std::milli>(inv_end - inv_start).count();

    cudaMemcpy(h_opt_rises, d_opt_rises, NUM_CURVES * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_opt_errors, d_opt_errors, NUM_CURVES * sizeof(float), cudaMemcpyDeviceToHost);

    // Analyze solver accuracy
    float mean_err = 0.0f, max_err = 0.0f;
    int perfect = 0;
    for (int i = 0; i < NUM_CURVES; i++) {
        float err = sqrtf(h_opt_errors[i]);
        mean_err += err;
        if (err > max_err) max_err = err;
        if (err < 0.01f) perfect++;
    }
    mean_err /= NUM_CURVES;

    printf("  Curves solved:   %d\n", NUM_CURVES);
    printf("  Time:            %.2f ms\n", inv_ms);
    printf("  Curves/sec:      %.0f\n", NUM_CURVES / (inv_ms / 1000.0f));
    printf("  Mean RMSE:       %.4f mm\n", mean_err);
    printf("  Max RMSE:        %.4f mm\n", max_err);
    printf("  Perfect fits:    %d/%d (%.1f%%)\n", perfect, NUM_CURVES, 100.0f * perfect / NUM_CURVES);
    printf("\n");

    // ========================================================================
    // Summary
    // ========================================================================
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║  NIGHT SHIFT SUMMARY                                   ║\n");
    printf("╠══════════════════════════════════════════════════════════╣\n");
    printf("║  EXP55: %.2fB spline-constraints/sec (hybrid kernel)   ║\n", c_per_s / 1e9f);
    printf("║  EXP56: h/L breakpoints mapped for 11 tolerances       ║\n");
    printf("║  EXP57: %d curves solved in %.1f ms (%.0f curves/sec)   ║\n", 
           NUM_CURVES, inv_ms, NUM_CURVES / (inv_ms / 1000.0f));
    printf("║  Perfect inverse fits: %d/%d (%.1f%%)                  ║\n",
           perfect, NUM_CURVES, 100.0f * perfect / NUM_CURVES);
    printf("╚══════════════════════════════════════════════════════════╝\n");

    // Cleanup
    cudaFree(d_rises); cudaFree(d_spans); cudaFree(d_lo); cudaFree(d_hi);
    cudaFree(d_passes); cudaFree(d_fails); cudaFree(d_max_kappa); cudaFree(d_energy);
    cudaFree(d_tolerances); cudaFree(d_breakpoints);
    cudaFree(d_target_y); cudaFree(d_opt_rises); cudaFree(d_opt_errors);
    free(h_rises); free(h_spans); free(h_lo); free(h_hi);
    free(h_passes); free(h_fails); free(h_max_kappa); free(h_energy);
    free(h_target_y); free(h_opt_rises); free(h_opt_errors);

    return 0;
}
