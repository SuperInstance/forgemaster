// Experiment 27: Batch Multi-Sensor Evaluation
// Real scenario: evaluate different constraint sets for different sensor groups
// Uses a constraint table (different bounds per sensor group) + sensor values
// Tests realistic workload where not all sensors share the same constraints

#include <cstdio>
#include <cuda_runtime.h>

struct ConstraintSet {
    unsigned char lo[8]; // lower bounds
    unsigned char hi[8]; // upper bounds
};

__global__ void range_check(const ConstraintSet* sets, const int* set_ids,
                             const int* values, int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int sid = set_ids[idx];
    ConstraintSet cs = sets[sid];
    int val = values[idx];
    
    // Check if value is within ALL constraint ranges
    int pass = 1;
    for (int j = 0; j < 8; j++) {
        if (val < cs.lo[j] || val >= cs.hi[j]) {
            pass = 0;
            break;
        }
    }
    results[idx] = pass;
}

// Same but with error mask
__global__ void range_check_masked(const ConstraintSet* sets, const int* set_ids,
                                    const int* values, unsigned char* fail_masks, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int sid = set_ids[idx];
    ConstraintSet cs = sets[sid];
    int val = values[idx];
    
    unsigned char mask = 0;
    for (int j = 0; j < 8; j++) {
        if (val < cs.lo[j] || val >= cs.hi[j]) {
            mask |= (1 << j);
        }
    }
    fail_masks[idx] = mask;
}

// Upper-bound-only (original experiment style) but with per-sensor bounds
__global__ void upper_check_masked(const unsigned char* bounds_data, // [n_constraints][8]
                                    const int* constraint_ids,        // which constraint set per sensor
                                    const int* values, unsigned char* fail_masks, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int cid = constraint_ids[idx];
    int val = values[idx];
    
    // Bounds are at offset cid*8
    const unsigned char* bounds = &bounds_data[cid * 8];
    
    unsigned char mask = 0;
    if (val >= bounds[0]) mask |= 0x01;
    if (val >= bounds[1]) mask |= 0x02;
    if (val >= bounds[2]) mask |= 0x04;
    if (val >= bounds[3]) mask |= 0x08;
    if (val >= bounds[4]) mask |= 0x10;
    if (val >= bounds[5]) mask |= 0x20;
    if (val >= bounds[6]) mask |= 0x40;
    if (val >= bounds[7]) mask |= 0x80;
    fail_masks[idx] = mask;
}

int main() {
    printf("=== Batch Multi-Sensor Constraint Evaluation ===\n\n");
    
    int n = 10000000;
    int n_constraint_sets = 100; // 100 different sensor types
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 100;
    
    // Allocate
    ConstraintSet *d_sets;
    int *d_set_ids, *d_values, *d_results;
    unsigned char *d_fail_masks, *d_bounds_flat;
    
    cudaMalloc(&d_sets, n_constraint_sets * sizeof(ConstraintSet));
    cudaMalloc(&d_set_ids, n * sizeof(int));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    cudaMalloc(&d_fail_masks, n * sizeof(unsigned char));
    cudaMalloc(&d_bounds_flat, n_constraint_sets * 8 * sizeof(unsigned char));
    
    // Generate constraint sets (different bounds for each sensor type)
    ConstraintSet *h_sets = new ConstraintSet[n_constraint_sets];
    unsigned char *h_bounds_flat = new unsigned char[n_constraint_sets * 8];
    for (int s = 0; s < n_constraint_sets; s++) {
        for (int j = 0; j < 8; j++) {
            h_sets[s].lo[j] = (unsigned char)(10 + (s * 3 + j * 7) % 40);
            h_sets[s].hi[j] = (unsigned char)(150 + (s * 5 + j * 11) % 90);
            h_bounds_flat[s * 8 + j] = h_sets[s].hi[j];
        }
    }
    
    int *h_set_ids = new int[n];
    int *h_values = new int[n];
    for (int i = 0; i < n; i++) {
        h_set_ids[i] = i % n_constraint_sets;
        h_values[i] = (i * 7 + 13) % 250;
    }
    
    cudaMemcpy(d_sets, h_sets, n_constraint_sets * sizeof(ConstraintSet), cudaMemcpyHostToDevice);
    cudaMemcpy(d_set_ids, h_set_ids, n * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_values, n * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_bounds_flat, h_bounds_flat, n_constraint_sets * 8 * sizeof(unsigned char), cudaMemcpyHostToDevice);
    
    // Warmup
    range_check<<<grid, block>>>(d_sets, d_set_ids, d_values, d_results, n);
    range_check_masked<<<grid, block>>>(d_sets, d_set_ids, d_values, d_fail_masks, n);
    upper_check_masked<<<grid, block>>>(d_bounds_flat, d_set_ids, d_values, d_fail_masks, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Benchmark 1: Range check (struct-based)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        range_check<<<grid, block>>>(d_sets, d_set_ids, d_values, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_range;
    cudaEventElapsedTime(&ms_range, start, stop);
    
    // Benchmark 2: Range check masked
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        range_check_masked<<<grid, block>>>(d_sets, d_set_ids, d_values, d_fail_masks, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_range_masked;
    cudaEventElapsedTime(&ms_range_masked, start, stop);
    
    // Benchmark 3: Flat bounds (upper-only) masked
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        upper_check_masked<<<grid, block>>>(d_bounds_flat, d_set_ids, d_values, d_fail_masks, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_flat_masked;
    cudaEventElapsedTime(&ms_flat_masked, start, stop);
    
    printf("10M sensors, 100 constraint sets, 8 constraints each, 100 iters:\n\n");
    printf("%-30s %10s %15s\n", "Method", "ms/iter", "c/s");
    printf("%-30s %10.3f %15.0f\n", "Range check (struct, pass/fail)", ms_range/iters, (double)n*8*iters/(ms_range/1000));
    printf("%-30s %10.3f %15.0f  (%.2fx)\n", "Range check (struct, masked)", ms_range_masked/iters, (double)n*8*iters/(ms_range_masked/1000), ms_range/ms_range_masked);
    printf("%-30s %10.3f %15.0f  (%.2fx)\n", "Flat bounds (upper-only, masked)", ms_flat_masked/iters, (double)n*8*iters/(ms_flat_masked/1000), ms_range/ms_flat_masked);
    
    // Verify correctness
    int *h_res = new int[n];
    unsigned char *h_mask = new unsigned char[n];
    range_check<<<grid, block>>>(d_sets, d_set_ids, d_values, d_results, n);
    range_check_masked<<<grid, block>>>(d_sets, d_set_ids, d_values, d_fail_masks, n);
    cudaDeviceSynchronize();
    cudaMemcpy(h_res, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_mask, d_fail_masks, n*sizeof(unsigned char), cudaMemcpyDeviceToHost);
    
    int pass_count = 0, mask_errors = 0;
    for (int i = 0; i < n; i++) {
        if (h_res[i]) pass_count++;
        if ((h_mask[i] == 0) != (h_res[i] == 1)) mask_errors++;
    }
    
    printf("\nPass: %d / %d (%.1f%%)\n", pass_count, n, 100.0*pass_count/n);
    printf("Mask vs pass/fail cross-check: %d errors\n", mask_errors);
    
    delete[] h_sets; delete[] h_set_ids; delete[] h_values; delete[] h_bounds_flat;
    delete[] h_res; delete[] h_mask;
    cudaFree(d_sets); cudaFree(d_set_ids); cudaFree(d_values); cudaFree(d_results);
    cudaFree(d_fail_masks); cudaFree(d_bounds_flat);
    
    return 0;
}
