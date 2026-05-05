// Experiment 29: Pinned Memory for Faster Bound Updates
// Compare pageable vs pinned Host→Device transfer for constraint bounds
// Pinned (page-locked) memory enables faster DMA transfers

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

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

int main() {
    printf("=== Pinned Memory for Bound Updates ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 20;
    size_t bounds_size = n * sizeof(uchar8);
    
    uchar8 *d_bounds;
    int *d_values;
    unsigned char *d_masks;
    cudaMalloc(&d_bounds, bounds_size);
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_masks, n * sizeof(unsigned char));
    
    // Pageable host memory
    uchar8 *h_b_pageable = new uchar8[n];
    
    // Pinned host memory
    uchar8 *h_b_pinned;
    cudaMallocHost(&h_b_pinned, bounds_size);
    
    // Pinned values too
    int *h_v_pinned;
    cudaMallocHost(&h_v_pinned, n * sizeof(int));
    
    // Init data
    for (int i = 0; i < n; i++) {
        h_b_pageable[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                           (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                           (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                           (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        h_b_pinned[i] = h_b_pageable[i];
        h_v_pinned[i] = (i * 7 + 13) % 250;
    }
    cudaMemcpy(d_values, h_v_pinned, n * sizeof(int), cudaMemcpyHostToDevice);
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Test 1: Pageable H2D transfer (baseline)
    printf("Testing pageable H2D transfer (%zu MB, %d iterations)...\n", bounds_size/1024/1024, iters);
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        cudaMemcpy(d_bounds, h_b_pageable, bounds_size, cudaMemcpyHostToDevice);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_pageable;
    cudaEventElapsedTime(&ms_pageable, start, stop);
    
    // Test 2: Pinned H2D transfer
    printf("Testing pinned H2D transfer (%zu MB, %d iterations)...\n", bounds_size/1024/1024, iters);
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        cudaMemcpy(d_bounds, h_b_pinned, bounds_size, cudaMemcpyHostToDevice);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_pinned;
    cudaEventElapsedTime(&ms_pinned, start, stop);
    
    // Test 3: Async pinned transfer (overlapping with computation)
    cudaStream_t stream1, stream2;
    cudaStreamCreate(&stream1);
    cudaStreamCreate(&stream2);
    
    printf("Testing async pinned transfer + kernel overlap...\n");
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        // Async transfer on stream1
        cudaMemcpyAsync(d_bounds, h_b_pinned, bounds_size, cudaMemcpyHostToDevice, stream1);
        // Kernel on stream2 (using previous bounds)
        int8_check8_masked<<<grid, block, 0, stream2>>>(d_bounds, d_values, d_masks, n);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_overlap;
    cudaEventElapsedTime(&ms_overlap, start, stop);
    
    // Test 4: Pure kernel (no transfer, for reference)
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        int8_check8_masked<<<grid, block>>>(d_bounds, d_values, d_masks, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_kernel;
    cudaEventElapsedTime(&ms_kernel, start, stop);
    
    printf("\n=== Transfer Speed Comparison (%zu MB) ===\n", bounds_size/1024/1024);
    printf("%-30s %10s %10s %10s\n", "Method", "ms/iter", "GB/s", "Speedup");
    printf("%-30s %10.2f %10.2f %10s\n", "Pageable memcpy", ms_pageable/iters, 
           bounds_size/(ms_pageable/iters)/1e6, "1.00x");
    printf("%-30s %10.2f %10.2f %10.2fx\n", "Pinned memcpy", ms_pinned/iters,
           bounds_size/(ms_pinned/iters)/1e6, ms_pageable/ms_pinned);
    printf("%-30s %10.2f %10s %10.2fx\n", "Pinned async + kernel overlap", ms_overlap/iters,
           "-", ms_pageable/ms_overlap);
    printf("%-30s %10.2f %10s %10s\n", "Pure kernel (no transfer)", ms_kernel/iters, "-", "baseline");
    
    printf("\n=== Practical Impact ===\n");
    double pageable_bandwidth = bounds_size / (ms_pageable / iters) / 1e6;
    double pinned_bandwidth = bounds_size / (ms_pinned / iters) / 1e6;
    printf("Pageable: %.1f ms/update (%.1f GB/s)\n", ms_pageable/iters, pageable_bandwidth);
    printf("Pinned:   %.1f ms/update (%.1f GB/s)\n", ms_pinned/iters, pinned_bandwidth);
    printf("Overlap:  %.1f ms/combined update+eval\n", ms_overlap/iters);
    printf("Kernel:   %.3f ms/eval\n", ms_kernel/iters);
    printf("\nFor real-time at 100Hz (10ms frame): bound update takes %.1f%% (pinned) vs %.1f%% (pageable)\n",
           100.0 * ms_pinned/iters/10.0, 100.0 * ms_pageable/iters/10.0);
    
    delete[] h_b_pageable;
    cudaFreeHost(h_b_pinned);
    cudaFreeHost(h_v_pinned);
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_masks);
    cudaStreamDestroy(stream1); cudaStreamDestroy(stream2);
    
    return 0;
}
