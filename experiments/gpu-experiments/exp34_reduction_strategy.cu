// Experiment 34: Warp-Cooperative Constraint Reduction
// Tests whether cooperative warp reduction for violation counts is faster than atomic-based
// This addresses the block-reduce in the production kernel — is warp-level reduction worth it?

#include <cstdio>
#include <cuda_runtime.h>

__global__ void kernel_atomic_reduce(
    const unsigned char* bounds, const int* set_ids, const int* values,
    unsigned char* masks, int* counts, int n, int nc
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
    
    __shared__ int smem[8];
    if (threadIdx.x < 8) smem[threadIdx.x] = 0;
    __syncthreads();
    if (mask) {
        for (int j = 0; j < 8; j++)
            if (mask & (1 << j)) atomicAdd(&smem[j], 1);
    }
    __syncthreads();
    if (threadIdx.x < 8 && smem[threadIdx.x] > 0)
        atomicAdd(&counts[threadIdx.x], smem[threadIdx.x]);
}

// Warp-level reduction using __ballot_sync
__global__ void kernel_warp_reduce(
    const unsigned char* bounds, const int* set_ids, const int* values,
    unsigned char* masks, int* counts, int n, int nc
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int lane = threadIdx.x & 31;
    int warp_id = threadIdx.x >> 5;
    
    unsigned char mask = 0;
    if (idx < n) {
        int val = values[idx];
        const unsigned char* b = &bounds[set_ids[idx] * nc];
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
    
    // Warp-level: count violations per constraint using ballot
    for (int j = 0; j < 8; j++) {
        unsigned has_violation = (mask & (1 << j)) ? 1 : 0;
        unsigned ballot = __ballot_sync(0xFFFFFFFF, has_violation);
        int warp_count = __popc(ballot);
        // Lane 0 of each warp accumulates
        if (lane == 0 && warp_count > 0) {
            atomicAdd(&counts[j], warp_count);
        }
    }
}

// Skip reduction entirely — just write masks, no counting
__global__ void kernel_no_reduce(
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
    printf("=== Exp34: Reduction Strategy Comparison ===\n\n");
    
    int n = 10000000;
    int nc = 8, nsets = 50, block = 256;
    int grid = (n + block - 1) / block;
    int iters = 200;
    
    unsigned char *d_b, *d_m; int *d_s, *d_v, *d_c;
    cudaMalloc(&d_b, nsets*nc); cudaMalloc(&d_s, n*sizeof(int));
    cudaMalloc(&d_v, n*sizeof(int)); cudaMalloc(&d_m, n);
    cudaMalloc(&d_c, nc*sizeof(int));
    
    unsigned char* hb = new unsigned char[nsets*nc];
    int* hs = new int[n]; int* hv = new int[n];
    for (int i = 0; i < nsets*nc; i++) hb[i] = 100+i%140;
    for (int i = 0; i < n; i++) { hs[i] = i%50; hv[i] = (i*7)%250; }
    cudaMemcpy(d_b, hb, nsets*nc, cudaMemcpyHostToDevice);
    cudaMemcpy(d_s, hs, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_v, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    
    // Warmup
    kernel_atomic_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,d_c,n,nc);
    kernel_warp_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,d_c,n,nc);
    kernel_no_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    // Atomic reduce
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemsetAsync(d_c, 0, nc*sizeof(int));
        kernel_atomic_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,d_c,n,nc);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_atomic;
    cudaEventElapsedTime(&ms_atomic, start, stop);
    
    // Warp reduce
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemsetAsync(d_c, 0, nc*sizeof(int));
        kernel_warp_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,d_c,n,nc);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_warp;
    cudaEventElapsedTime(&ms_warp, start, stop);
    
    // No reduce (baseline — just constraint checking)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        kernel_no_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_noreduce;
    cudaEventElapsedTime(&ms_noreduce, start, stop);
    
    printf("10M sensors, 50 sets, 8 constraints, %d iters:\n\n", iters);
    printf("%-30s %10s %15s %10s\n", "Method", "ms/iter", "c/s", "Overhead");
    printf("%-30s %10.3f %15.0f %10s\n", "No reduce (baseline)", ms_noreduce/iters,
           (double)n*nc*iters/(ms_noreduce/1000), "baseline");
    printf("%-30s %10.3f %15.0f %10.2fx\n", "Atomic block reduce", ms_atomic/iters,
           (double)n*nc*iters/(ms_atomic/1000), ms_noreduce/ms_atomic);
    printf("%-30s %10.3f %15.0f %10.2fx\n", "Warp ballot reduce", ms_warp/iters,
           (double)n*nc*iters/(ms_warp/1000), ms_noreduce/ms_warp);
    
    // Correctness: compare counts
    int c_atomic[8], c_warp[8];
    cudaMemset(d_c, 0, nc*sizeof(int));
    kernel_atomic_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,d_c,n,nc);
    cudaDeviceSynchronize();
    cudaMemcpy(c_atomic, d_c, nc*sizeof(int), cudaMemcpyDeviceToHost);
    
    cudaMemset(d_c, 0, nc*sizeof(int));
    kernel_warp_reduce<<<grid,block>>>(d_b,d_s,d_v,d_m,d_c,n,nc);
    cudaDeviceSynchronize();
    cudaMemcpy(c_warp, d_c, nc*sizeof(int), cudaMemcpyDeviceToHost);
    
    int mismatches = 0;
    for (int j = 0; j < 8; j++) {
        if (c_atomic[j] != c_warp[j]) mismatches++;
    }
    printf("\nCorrectness: %d count mismatches between atomic and warp\n", mismatches);
    for (int j = 0; j < 8; j++)
        printf("  Constraint %d: atomic=%d, warp=%d\n", j, c_atomic[j], c_warp[j]);
    
    float reduce_overhead_atomic = (ms_atomic - ms_noreduce) / ms_noreduce * 100;
    float reduce_overhead_warp = (ms_warp - ms_noreduce) / ms_noreduce * 100;
    printf("\nReduction overhead: atomic=%.1f%%, warp=%.1f%%\n", 
           reduce_overhead_atomic, reduce_overhead_warp);
    printf("Warp vs atomic speedup: %.2fx\n", ms_atomic/ms_warp);
    
    delete[] hb; delete[] hs; delete[] hv;
    return 0;
}
