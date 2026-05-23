// Experiment 36: Const Memory for Bounds — Does __constant__ help?
// The production kernel reads bounds from global memory. If we put the most common
// constraint sets in __constant__ memory (64KB cache), does it help?

#include <cstdio>
#include <cuda_runtime.h>

__constant__ unsigned char d_const_bounds[4096]; // 512 constraint sets × 8 bytes

__global__ void kernel_global(
    const unsigned char* bounds, const int* set_ids, const int* values,
    unsigned char* masks, int n, int nc
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    const unsigned char* b = &bounds[set_ids[idx] * nc];
    unsigned char mask = 0;
    if (val >= b[0]) mask |= 0x01;
    if (val >= b[1]) mask |= 0x02;
    if (val >= b[2]) mask |= 0x04;
    if (val >= b[3]) mask |= 0x08;
    if (val >= b[4]) mask |= 0x10;
    if (val >= b[5]) mask |= 0x20;
    if (val >= b[6]) mask |= 0x40;
    if (val >= b[7]) mask |= 0x80;
    masks[idx] = mask;
}

__global__ void kernel_const(
    const int* set_ids, const int* values,
    unsigned char* masks, int n, int nc
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    const unsigned char* b = &d_const_bounds[set_ids[idx] * nc];
    unsigned char mask = 0;
    if (val >= b[0]) mask |= 0x01;
    if (val >= b[1]) mask |= 0x02;
    if (val >= b[2]) mask |= 0x04;
    if (val >= b[3]) mask |= 0x08;
    if (val >= b[4]) mask |= 0x10;
    if (val >= b[5]) mask |= 0x20;
    if (val >= b[6]) mask |= 0x40;
    if (val >= b[7]) mask |= 0x80;
    masks[idx] = mask;
}

// Shared memory version — load bounds into shared
__global__ void kernel_shared(
    const unsigned char* bounds, const int* set_ids, const int* values,
    unsigned char* masks, int n, int nc, int n_sets
) {
    extern __shared__ unsigned char smem[];
    
    // Cooperative load of all bounds into shared memory
    for (int i = threadIdx.x; i < n_sets * nc; i += blockDim.x)
        smem[i] = bounds[i];
    __syncthreads();
    
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    const unsigned char* b = &smem[set_ids[idx] * nc];
    unsigned char mask = 0;
    if (val >= b[0]) mask |= 0x01;
    if (val >= b[1]) mask |= 0x02;
    if (val >= b[2]) mask |= 0x04;
    if (val >= b[3]) mask |= 0x08;
    if (val >= b[4]) mask |= 0x10;
    if (val >= b[5]) mask |= 0x20;
    if (val >= b[6]) mask |= 0x40;
    if (val >= b[7]) mask |= 0x80;
    masks[idx] = mask;
}

int main() {
    printf("=== Exp36: Const vs Global vs Shared Memory for Bounds ===\n\n");
    
    int n = 10000000;
    int nc = 8;
    int block = 256;
    int iters = 200;
    
    // Test with different numbers of constraint sets
    int set_counts[] = {8, 32, 64, 128, 256, 512};
    
    unsigned char *d_bounds_g, *d_masks;
    int *d_set_ids, *d_values;
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_set_ids, n * sizeof(int));
    cudaMalloc(&d_values, n * sizeof(int));
    
    int* hv = new int[n];
    int* hs = new int[n];
    for (int i = 0; i < n; i++) hv[i] = (i*7+13)%250;
    cudaMemcpy(d_values, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    printf("%-8s %12s %12s %12s %8s %8s %8s\n", 
           "Sets", "Global ms/i", "Const ms/i", "Shared ms/i", "G c/s", "C c/s", "S c/s");
    printf("%-8s %12s %12s %12s %8s %8s %8s\n",
           "---", "---", "---", "---", "---", "---", "---");
    
    for (int si = 0; si < 6; si++) {
        int nsets = set_counts[si];
        int bounds_bytes = nsets * nc;
        
        // Allocate and init bounds
        cudaMalloc(&d_bounds_g, bounds_bytes);
        unsigned char* hb = new unsigned char[bounds_bytes];
        for (int i = 0; i < bounds_bytes; i++) hb[i] = 100 + (i*7)%140;
        cudaMemcpy(d_bounds_g, hb, bounds_bytes, cudaMemcpyHostToDevice);
        cudaMemcpyToSymbol(d_const_bounds, hb, bounds_bytes);
        
        // Set IDs
        for (int i = 0; i < n; i++) hs[i] = i % nsets;
        cudaMemcpy(d_set_ids, hs, n*sizeof(int), cudaMemcpyHostToDevice);
        
        int grid = (n + block - 1) / block;
        
        // Warmup
        kernel_global<<<grid,block>>>(d_bounds_g, d_set_ids, d_values, d_masks, n, nc);
        kernel_const<<<grid,block>>>(d_set_ids, d_values, d_masks, n, nc);
        kernel_shared<<<grid, block, bounds_bytes>>>(d_bounds_g, d_set_ids, d_values, d_masks, n, nc, nsets);
        cudaDeviceSynchronize();
        
        // Benchmark global
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++)
            kernel_global<<<grid,block>>>(d_bounds_g, d_set_ids, d_values, d_masks, n, nc);
        cudaEventRecord(stop); cudaEventSynchronize(stop);
        float ms_g;
        cudaEventElapsedTime(&ms_g, start, stop);
        
        // Benchmark const
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++)
            kernel_const<<<grid,block>>>(d_set_ids, d_values, d_masks, n, nc);
        cudaEventRecord(stop); cudaEventSynchronize(stop);
        float ms_c;
        cudaEventElapsedTime(&ms_c, start, stop);
        
        // Benchmark shared (if fits)
        float ms_s = 0;
        if (bounds_bytes <= 4096) {
            cudaEventRecord(start);
            for (int i = 0; i < iters; i++)
                kernel_shared<<<grid, block, bounds_bytes>>>(d_bounds_g, d_set_ids, d_values, d_masks, n, nc, nsets);
            cudaEventRecord(stop); cudaEventSynchronize(stop);
            cudaEventElapsedTime(&ms_s, start, stop);
        }
        
        double gbps = (double)n*nc*iters/(ms_g/1000)/1e9;
        double cbps = (double)n*nc*iters/(ms_c/1000)/1e9;
        double sbps = ms_s > 0 ? (double)n*nc*iters/(ms_s/1000)/1e9 : 0;
        
        char sbuf[16], gbuf[16];
        if (ms_s > 0) snprintf(sbuf, sizeof(sbuf), "%.3f", ms_s/iters);
        if (ms_s > 0) snprintf(gbuf, sizeof(gbuf), "%.1f", sbps);
        printf("%-8d %12.3f %12.3f %12s %8.1f %8.1f %8s\n",
               nsets, ms_g/iters, ms_c/iters,
               ms_s > 0 ? sbuf : "N/A",
               gbps, cbps,
               ms_s > 0 ? gbuf : "N/A");
        
        cudaFree(d_bounds_g);
        delete[] hb;
    }
    
    // Correctness check
    printf("\n=== Correctness (64 sets) ===\n");
    int nsets = 64;
    int bounds_bytes = nsets * nc;
    cudaMalloc(&d_bounds_g, bounds_bytes);
    unsigned char* hb = new unsigned char[bounds_bytes];
    for (int i = 0; i < bounds_bytes; i++) hb[i] = 100 + (i*7)%140;
    cudaMemcpy(d_bounds_g, hb, bounds_bytes, cudaMemcpyHostToDevice);
    cudaMemcpyToSymbol(d_const_bounds, hb, bounds_bytes);
    for (int i = 0; i < n; i++) hs[i] = i % nsets;
    cudaMemcpy(d_set_ids, hs, n*sizeof(int), cudaMemcpyHostToDevice);
    int grid = (n + block - 1) / block;
    
    unsigned char *hmg = new unsigned char[n], *hmc = new unsigned char[n];
    kernel_global<<<grid,block>>>(d_bounds_g, d_set_ids, d_values, d_masks, n, nc);
    cudaDeviceSynchronize();
    cudaMemcpy(hmg, d_masks, n, cudaMemcpyDeviceToHost);
    kernel_const<<<grid,block>>>(d_set_ids, d_values, d_masks, n, nc);
    cudaDeviceSynchronize();
    cudaMemcpy(hmc, d_masks, n, cudaMemcpyDeviceToHost);
    
    int mismatches = 0;
    for (int i = 0; i < n; i++)
        if (hmg[i] != hmc[i]) mismatches++;
    printf("Global vs Const: %d mismatches\n", mismatches);
    
    delete[] hv; delete[] hs; delete[] hb; delete[] hmg; delete[] hmc;
    return 0;
}
