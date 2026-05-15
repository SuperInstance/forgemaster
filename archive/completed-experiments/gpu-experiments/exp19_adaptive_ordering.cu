// Experiment 19: Adaptive constraint ordering — sort by failure rate
// Idea: put the most-likely-to-fail constraints first in the chain
// Tests whether constraint reordering improves throughput

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

// Standard: constraints in declaration order
__global__ void check_standard(const uchar8* __restrict__ bounds,
                                const int* __restrict__ values,
                                int* results, int n) {
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

// Reordered: tightest constraints first (most likely to fail)
// b.a is hardest to pass (smallest value), b.h is easiest
__global__ void check_reordered(const uchar8* __restrict__ bounds,
                                 const int* __restrict__ values,
                                 int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    
    // Sort: put smallest bounds first (hardest to pass)
    unsigned char sorted[8] = {b.a, b.b, b.c, b.d, b.e, b.f, b.g, b.h};
    // Bubble sort 8 elements — 28 comparisons, all in registers
    for (int i = 0; i < 7; i++)
        for (int j = i+1; j < 8; j++)
            if (sorted[j] < sorted[i]) { unsigned char t = sorted[i]; sorted[i] = sorted[j]; sorted[j] = t; }
    
    // Check hardest first
    int pass = 1;
    for (int i = 0; i < 8 && pass; i++) {
        if (val >= sorted[i]) pass = 0;
    }
    results[idx] = pass;
}

// Branchless version using ballot
__global__ void check_branchless(const uchar8* __restrict__ bounds,
                                  const int* __restrict__ values,
                                  int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    
    // Check all 8 simultaneously (no early exit)
    int mask = 0;
    if (val < b.a) mask |= 1;
    if (val < b.b) mask |= 2;
    if (val < b.c) mask |= 4;
    if (val < b.d) mask |= 8;
    if (val < b.e) mask |= 16;
    if (val < b.f) mask |= 32;
    if (val < b.g) mask |= 64;
    if (val < b.h) mask |= 128;
    
    results[idx] = (mask == 255) ? 1 : 0; // all 8 must pass
}

int main() {
    printf("=== Adaptive Constraint Ordering ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    
    uchar8 *d_bounds;
    int *d_values, *d_results;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    
    // Generate data where ~80% fail on first constraint (realistic for safety systems)
    uchar8 *h_b = new uchar8[n];
    int *h_v = new int[n];
    for (int i = 0; i < n; i++) {
        // Make first constraint very tight (hard to pass)
        h_b[i].a = 10;  // Only pass if val < 10
        h_b[i].b = 50;
        h_b[i].c = 100;
        h_b[i].d = 150;
        h_b[i].e = 180;
        h_b[i].f = 200;
        h_b[i].g = 220;
        h_b[i].h = 240;
        h_v[i] = (i * 7 + 13) % 250; // 0-249, so ~96% fail first constraint
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
    
    int iters = 100;
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Standard
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        check_standard<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_std;
    cudaEventElapsedTime(&ms_std, start, stop);
    
    // Reordered (with sort)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        check_reordered<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_reord;
    cudaEventElapsedTime(&ms_reord, start, stop);
    
    // Branchless
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        check_branchless<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_branchless;
    cudaEventElapsedTime(&ms_branchless, start, stop);
    
    printf("Workload: 96%% fail first constraint (tight safety bounds)\n\n");
    printf("Standard (declaration order):  %.2f ms | %.0f constr/s\n", ms_std/iters, (double)n*8*iters/(ms_std/1000.0));
    printf("Reordered (sort+hardest first): %.2f ms | %.0f constr/s (%.2fx)\n", ms_reord/iters, (double)n*8*iters/(ms_reord/1000.0), ms_std/ms_reord);
    printf("Branchless (all-check):         %.2f ms | %.0f constr/s (%.2fx)\n", ms_branchless/iters, (double)n*8*iters/(ms_branchless/1000.0), ms_std/ms_branchless);
    
    // Verify all three produce same results
    int *h_std = new int[n], *h_reord = new int[n], *h_branchless = new int[n];
    check_standard<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaMemcpy(h_std, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    check_reordered<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaMemcpy(h_reord, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    check_branchless<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaMemcpy(h_branchless, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    
    int mm1 = 0, mm2 = 0;
    for (int i = 0; i < n; i++) {
        if (h_std[i] != h_reord[i]) mm1++;
        if (h_std[i] != h_branchless[i]) mm2++;
    }
    printf("\nStandard vs Reordered mismatches: %d\n", mm1);
    printf("Standard vs Branchless mismatches: %d\n", mm2);
    
    delete[] h_b; delete[] h_v; delete[] h_std; delete[] h_reord; delete[] h_branchless;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    
    return 0;
}
