// Experiment 23: Sparse constraint workload — most sensors have few active constraints
// Real safety systems: 80% of sensors have 1-2 active constraints, 20% have 8+
// Tests performance with variable constraint count per element

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

// Dense: all 8 constraints checked
__global__ void dense_check(const uchar8* bounds, const int* values, int* results, int n) {
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

// Sparse-aware: only check first N constraints (N per element, encoded in constraint 0)
__global__ void sparse_check(const uchar8* bounds, const int* values, 
                              const unsigned char* active_counts, int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    int count = active_counts[idx]; // 1-8
    int pass = 1;
    
    // Only check active constraints
    if (count >= 1 && val >= b.a) pass = 0;
    else if (count >= 2 && val >= b.b) pass = 0;
    else if (count >= 3 && val >= b.c) pass = 0;
    else if (count >= 4 && val >= b.d) pass = 0;
    else if (count >= 5 && val >= b.e) pass = 0;
    else if (count >= 6 && val >= b.f) pass = 0;
    else if (count >= 7 && val >= b.g) pass = 0;
    else if (count >= 8 && val >= b.h) pass = 0;
    results[idx] = pass;
}

// Sparse with bitmask: each element has a bitmask of which constraints are active
__global__ void bitmask_sparse_check(const uchar8* bounds, const int* values,
                                      const unsigned char* masks, int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    uchar8 b = bounds[idx];
    unsigned char mask = masks[idx];
    
    int pass = 1;
    if ((mask & 0x01) && val >= b.a) pass = 0;
    else if ((mask & 0x02) && val >= b.b) pass = 0;
    else if ((mask & 0x04) && val >= b.c) pass = 0;
    else if ((mask & 0x08) && val >= b.d) pass = 0;
    else if ((mask & 0x10) && val >= b.e) pass = 0;
    else if ((mask & 0x20) && val >= b.f) pass = 0;
    else if ((mask & 0x40) && val >= b.g) pass = 0;
    else if ((mask & 0x80) && val >= b.h) pass = 0;
    results[idx] = pass;
}

int main() {
    printf("=== Sparse Constraint Workload ===\n");
    printf("Realistic: 80%% sensors have 1-2 constraints, 20%% have 8\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 100;
    
    uchar8 *d_bounds;
    int *d_values, *d_results;
    unsigned char *d_counts, *d_masks;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    cudaMalloc(&d_counts, n * sizeof(unsigned char));
    cudaMalloc(&d_masks, n * sizeof(unsigned char));
    
    uchar8 *h_b = new uchar8[n];
    int *h_v = new int[n];
    unsigned char *h_counts = new unsigned char[n];
    unsigned char *h_masks = new unsigned char[n];
    
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        h_v[i] = (i * 7 + 13) % 250;
        
        // 80% have 1-2 constraints, 20% have 8
        int active = (i % 5 == 0) ? 8 : (1 + (i % 2));
        h_counts[i] = (unsigned char)active;
        
        // Bitmask version
        unsigned char mask = 0;
        for (int j = 0; j < active; j++) mask |= (1 << j);
        h_masks[i] = mask;
    }
    
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_counts, h_counts, n * sizeof(unsigned char), cudaMemcpyHostToDevice);
    cudaMemcpy(d_masks, h_masks, n * sizeof(unsigned char), cudaMemcpyHostToDevice);
    
    // Warmup
    dense_check<<<grid, block>>>(d_bounds, d_values, d_results, n);
    sparse_check<<<grid, block>>>(d_bounds, d_values, d_counts, d_results, n);
    bitmask_sparse_check<<<grid, block>>>(d_bounds, d_values, d_masks, d_results, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Dense (all 8 constraints always checked)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        dense_check<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_dense;
    cudaEventElapsedTime(&ms_dense, start, stop);
    
    // Sparse-aware (variable count)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        sparse_check<<<grid, block>>>(d_bounds, d_values, d_counts, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_sparse;
    cudaEventElapsedTime(&ms_sparse, start, stop);
    
    // Bitmask sparse
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        bitmask_sparse_check<<<grid, block>>>(d_bounds, d_values, d_masks, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_bitmask;
    cudaEventElapsedTime(&ms_bitmask, start, stop);
    
    // Count average active constraints
    int total_active = 0;
    for (int i = 0; i < n; i++) total_active += h_counts[i];
    double avg_active = (double)total_active / n;
    
    printf("Average active constraints per element: %.1f (out of 8)\n\n", avg_active);
    printf("Dense (all 8 always):   %.2f ms/iter | %.0f effective c/s\n", ms_dense/iters, (double)n*8*iters/(ms_dense/1000.0));
    printf("Sparse-aware (count):   %.2f ms/iter | %.0f effective c/s | %.2fx\n", ms_sparse/iters, (double)n*avg_active*iters/(ms_sparse/1000.0), ms_dense/ms_sparse);
    printf("Bitmask sparse:         %.2f ms/iter | %.0f effective c/s | %.2fx\n", ms_bitmask/iters, (double)n*avg_active*iters/(ms_bitmask/1000.0), ms_dense/ms_bitmask);
    
    // Differential: compare sparse vs dense (should agree when active==8)
    int *h_dense = new int[n], *h_sparse = new int[n], *h_bitmask = new int[n];
    dense_check<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaMemcpy(h_dense, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    sparse_check<<<grid, block>>>(d_bounds, d_values, d_counts, d_results, n);
    cudaMemcpy(h_sparse, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    bitmask_sparse_check<<<grid, block>>>(d_bounds, d_values, d_masks, d_results, n);
    cudaMemcpy(h_bitmask, d_results, n*sizeof(int), cudaMemcpyDeviceToHost);
    
    int mm1 = 0, mm2 = 0;
    for (int i = 0; i < n; i++) {
        // Sparse should match dense for elements with all 8 active
        if (h_counts[i] == 8 && h_dense[i] != h_sparse[i]) mm1++;
        if (h_sparse[i] != h_bitmask[i]) mm2++;
    }
    printf("\nDense vs Sparse (8-active elements): %d mismatches\n", mm1);
    printf("Sparse vs Bitmask: %d mismatches\n", mm2);
    
    delete[] h_b; delete[] h_v; delete[] h_counts; delete[] h_masks;
    delete[] h_dense; delete[] h_sparse; delete[] h_bitmask;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    cudaFree(d_counts); cudaFree(d_masks);
    
    return 0;
}
