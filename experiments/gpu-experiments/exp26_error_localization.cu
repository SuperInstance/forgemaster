// Experiment 26: Error Localization — which constraint failed?
// In safety systems, knowing WHICH constraint failed is critical
// Tests: can we track individual constraint violations without performance loss?

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

// Returns bitmask of failed constraints (bit i set = constraint i failed)
__global__ void int8_check8_masked(const uchar8* bounds, const int* values, 
                                    unsigned char* fail_masks, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    unsigned char mask = 0;
    if (val >= b.a) mask |= 0x01;
    if (val >= b.b) mask |= 0x02;
    if (val >= b.c) mask |= 0x04;
    if (val >= b.d) mask |= 0x08;
    if (val >= b.e) mask |= 0x10;
    if (val >= b.f) mask |= 0x20;
    if (val >= b.g) mask |= 0x40;
    if (val >= b.h) mask |= 0x80;
    fail_masks[idx] = mask;
}

// Original: just pass/fail
__global__ void int8_check8(const uchar8* bounds, const int* values, int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    int pass = 1;
    if (val >= b.a) pass = 0;
    else if (val >= b.b) pass = 0;
    else if (val >= b.c) pass = 0;
    else if (val >= b.d) pass = 0;
    else if (val >= b.e) pass = 0;
    else if (val >= b.f) pass = 0;
    else if (val >= b.g) pass = 0;
    else if (val >= b.h) pass = 0;
    results[idx] = pass;
}

// Count violations per constraint (8 counters for 8 constraints)
__global__ void count_violations(const uchar8* bounds, const int* values, 
                                  int* violation_counts, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    
    // Each thread atomically increments violation counter
    if (val >= b.a) atomicAdd(&violation_counts[0], 1);
    if (val >= b.b) atomicAdd(&violation_counts[1], 1);
    if (val >= b.c) atomicAdd(&violation_counts[2], 1);
    if (val >= b.d) atomicAdd(&violation_counts[3], 1);
    if (val >= b.e) atomicAdd(&violation_counts[4], 1);
    if (val >= b.f) atomicAdd(&violation_counts[5], 1);
    if (val >= b.g) atomicAdd(&violation_counts[6], 1);
    if (val >= b.h) atomicAdd(&violation_counts[7], 1);
}

int main() {
    printf("=== Error Localization: Which Constraint Failed? ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 100;
    
    uchar8 *d_bounds;
    int *d_values, *d_results;
    unsigned char *d_fail_masks;
    int *d_violation_counts;
    
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    cudaMalloc(&d_fail_masks, n * sizeof(unsigned char));
    cudaMalloc(&d_violation_counts, 8 * sizeof(int));
    
    uchar8 *h_b = new uchar8[n];
    int *h_v = new int[n];
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        h_v[i] = (i * 7 + 13) % 250;
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
    
    // Warmup
    int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
    int8_check8_masked<<<grid, block>>>(d_bounds, d_values, d_fail_masks, n);
    cudaMemset(d_violation_counts, 0, 8 * sizeof(int));
    count_violations<<<grid, block>>>(d_bounds, d_values, d_violation_counts, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Benchmark 1: Simple pass/fail
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_simple;
    cudaEventElapsedTime(&ms_simple, start, stop);
    
    // Benchmark 2: Full error mask (which constraints failed per element)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        int8_check8_masked<<<grid, block>>>(d_bounds, d_values, d_fail_masks, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_masked;
    cudaEventElapsedTime(&ms_masked, start, stop);
    
    // Benchmark 3: Violation counting (aggregated)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemset(d_violation_counts, 0, 8 * sizeof(int));
        count_violations<<<grid, block>>>(d_bounds, d_values, d_violation_counts, n);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_counting;
    cudaEventElapsedTime(&ms_counting, start, stop);
    
    printf("10M elements, 8 constraints, 100 iterations each:\n\n");
    printf("%-25s %10s %15s\n", "Method", "ms/iter", "c/s");
    printf("%-25s %10.3f %15.0f\n", "Simple pass/fail", ms_simple/iters, (double)n*8*iters/(ms_simple/1000));
    printf("%-25s %10.3f %15.0f  (%.2fx)\n", "Full error mask", ms_masked/iters, (double)n*8*iters/(ms_masked/1000), ms_simple/ms_masked);
    printf("%-25s %10.3f %15.0f  (%.2fx)\n", "Violation counting", ms_counting/iters, (double)n*8*iters/(ms_counting/1000), ms_simple/ms_counting);
    
    // Verify error localization correctness
    int *h_results = new int[n];
    unsigned char *h_masks = new unsigned char[n];
    int h_counts[8] = {0};
    
    int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
    int8_check8_masked<<<grid, block>>>(d_bounds, d_values, d_fail_masks, n);
    cudaMemset(d_violation_counts, 0, 8 * sizeof(int));
    count_violations<<<grid, block>>>(d_bounds, d_values, d_violation_counts, n);
    cudaDeviceSynchronize();
    
    cudaMemcpy(h_results, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_masks, d_fail_masks, n*sizeof(unsigned char), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_counts, d_violation_counts, 8*sizeof(int), cudaMemcpyDeviceToHost);
    
    // Cross-check: mask==0 iff pass==1
    int cross_errors = 0;
    int total_fails = 0;
    int per_constraint[8] = {0};
    for (int i = 0; i < n; i++) {
        bool mask_fail = (h_masks[i] != 0);
        bool res_fail = (h_results[i] == 0);
        if (mask_fail != res_fail) cross_errors++;
        if (mask_fail) {
            total_fails++;
            for (int j = 0; j < 8; j++)
                if (h_masks[i] & (1 << j)) per_constraint[j]++;
        }
    }
    
    printf("\n=== Error Localization Results ===\n");
    printf("Cross-check errors (mask vs pass/fail): %d\n", cross_errors);
    printf("Total failures: %d / %d (%.1f%%)\n", total_fails, n, 100.0*total_fails/n);
    printf("\nPer-constraint violations:\n");
    for (int j = 0; j < 8; j++) {
        printf("  Constraint %d: %8d violations (%.1f%%)  [atomic count: %d]\n",
               j, per_constraint[j], 100.0*per_constraint[j]/n, h_counts[j]);
    }
    
    // Check atomic counts match
    int count_errors = 0;
    for (int j = 0; j < 8; j++)
        if (per_constraint[j] != h_counts[j]) count_errors++;
    printf("\nAtomic count mismatches: %d\n", count_errors);
    
    delete[] h_b; delete[] h_v; delete[] h_results; delete[] h_masks;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    cudaFree(d_fail_masks); cudaFree(d_violation_counts);
    
    return 0;
}
