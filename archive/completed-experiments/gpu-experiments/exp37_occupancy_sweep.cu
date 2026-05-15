// Experiment 37: Occupancy Sweep — Finding Optimal Block Size for Production Kernel
// Tests block sizes from 32 to 1024 to find the sweet spot

#include <cstdio>
#include <cuda_runtime.h>

__global__ void flux_check(
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

int main() {
    printf("=== Exp37: Occupancy Sweep — Optimal Block Size ===\n\n");
    
    int n = 10000000;
    int nc = 8, nsets = 50;
    int iters = 200;
    
    unsigned char *d_b, *d_m; int *d_s, *d_v;
    cudaMalloc(&d_b, nsets*nc); cudaMalloc(&d_s, n*sizeof(int));
    cudaMalloc(&d_v, n*sizeof(int)); cudaMalloc(&d_m, n);
    
    unsigned char hb[400]; int* hs = new int[n]; int* hv = new int[n];
    for (int i = 0; i < 400; i++) hb[i] = 100+i%140;
    for (int i = 0; i < n; i++) { hs[i] = i%50; hv[i] = (i*7)%250; }
    cudaMemcpy(d_b, hb, nsets*nc, cudaMemcpyHostToDevice);
    cudaMemcpy(d_s, hs, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_v, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    int blocks[] = {32, 64, 96, 128, 192, 256, 384, 512, 768, 1024};
    
    printf("%-8s %10s %10s %15s %10s\n", "Block", "Grid", "ms/iter", "c/s", "vs 256");
    printf("%-8s %10s %10s %15s %10s\n", "-----", "----", "-------", "---", "------");
    
    float ms_256 = 0;
    
    for (int bi = 0; bi < 10; bi++) {
        int block = blocks[bi];
        int grid = (n + block - 1) / block;
        
        // Warmup
        flux_check<<<grid, block>>>(d_b, d_s, d_v, d_m, n, nc);
        cudaDeviceSynchronize();
        
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++)
            flux_check<<<grid, block>>>(d_b, d_s, d_v, d_m, n, nc);
        cudaEventRecord(stop); cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double cps = (double)n*nc*iters/(ms/1000);
        
        if (block == 256) ms_256 = ms;
        
        printf("%-8d %10d %10.3f %15.0f %10.2fx\n",
               block, grid, ms/iters, cps,
               ms_256 > 0 ? ms_256/ms : 0);
    }
    
    printf("\n=== Recommendation ===\n");
    printf("Use the block size with lowest ms/iter for production.\n");
    printf("If multiple are close, prefer 256 (standard) for compatibility.\n");
    
    delete[] hs; delete[] hv;
    return 0;
}
