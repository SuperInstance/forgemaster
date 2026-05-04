// Experiment 05: Compact constraint encoding — pack 8 bounds into 32 bytes
// Instead of 8 separate int reads, pack as 8x uint16 or 4x uint32 pairs
// Test memory layout impact on constraint checking throughput

#include <cstdio>
#include <cuda_runtime.h>
#include <stdint.h>

// Layout A: 8 separate int32 bounds (32 bytes per element)
__global__ void check_loose(const int* __restrict__ bounds,
                             const int* __restrict__ values,
                             int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    int pass = 1;
    for (int c = 0; c < 8; c++) {
        if (val >= bounds[idx * 8 + c]) { pass = 0; break; }
    }
    results[idx] = pass;
}

// Layout B: 8x uint16 packed into 128 bits (16 bytes per element)
// Max bound value = 65535, sufficient for many safety constraints
__global__ void check_packed_u16(const uint16_t* __restrict__ packed_bounds,
                                  const int* __restrict__ values,
                                  int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    int pass = 1;
    const uint16_t* b = packed_bounds + idx * 8;
    #pragma unroll
    for (int c = 0; c < 8; c++) {
        if (val >= (int)b[c]) { pass = 0; break; }
    }
    results[idx] = pass;
}

// Layout C: 4x uint2 (each uint2 = {lo, hi} pair, checked with val >= lo && val <= hi)
// Range constraints are the most common type in safety systems
struct RangeConstraint { int lo; int hi; };
__global__ void check_ranges(const RangeConstraint* __restrict__ ranges,
                              const int* __restrict__ values,
                              int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    int pass = 1;
    #pragma unroll
    for (int c = 0; c < 4; c++) {
        RangeConstraint r = ranges[idx * 4 + c];
        if (val < r.lo || val > r.hi) { pass = 0; break; }
    }
    results[idx] = pass;
}

// Layout D: Float4 vectorized load (128-bit single transaction)
// 4 constraints packed into float4 = 16 bytes
#include <vector_types.h>
__global__ void check_float4(const float4* __restrict__ packed4,
                              const float* __restrict__ values,
                              int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    float val = values[idx];
    float4 b = packed4[idx]; // single 128-bit load
    int pass = 1;
    if (val >= b.x) pass = 0;
    else if (val >= b.y) pass = 0;
    else if (val >= b.z) pass = 0;
    else if (val >= b.w) pass = 0;
    results[idx] = pass;
}

int main() {
    printf("=== Constraint Memory Layout Comparison ===\n\n");
    
    int n = 10000000;
    size_t bytes = n * sizeof(int);
    
    // Layout A: 8x int32
    int *d_bounds_a, *d_values, *d_results;
    cudaMalloc(&d_bounds_a, n * 8 * sizeof(int));
    cudaMalloc(&d_values, bytes);
    cudaMalloc(&d_results, bytes);
    
    int *h_values = new int[n];
    for (int i = 0; i < n; i++) h_values[i] = (i * 7 + 13) % 50000;
    cudaMemcpy(d_values, h_values, bytes, cudaMemcpyHostToDevice);
    
    int *h_bounds = new int[n * 8];
    for (int i = 0; i < n * 8; i++) h_bounds[i] = (i * 13 + 7) % 65000;
    cudaMemcpy(d_bounds_a, h_bounds, n * 8 * sizeof(int), cudaMemcpyHostToDevice);
    
    // Layout B: 8x uint16
    uint16_t *d_bounds_b;
    cudaMalloc(&d_bounds_b, n * 8 * sizeof(uint16_t));
    uint16_t *h_bounds_b = new uint16_t[n * 8];
    for (int i = 0; i < n * 8; i++) h_bounds_b[i] = (uint16_t)((i * 13 + 7) % 65000);
    cudaMemcpy(d_bounds_b, h_bounds_b, n * 8 * sizeof(uint16_t), cudaMemcpyHostToDevice);
    
    // Layout C: 4x RangeConstraint
    RangeConstraint *d_ranges;
    cudaMalloc(&d_ranges, n * 4 * sizeof(RangeConstraint));
    RangeConstraint *h_ranges = new RangeConstraint[n * 4];
    for (int i = 0; i < n * 4; i++) {
        h_ranges[i].lo = (i * 17) % 20000;
        h_ranges[i].hi = h_ranges[i].lo + 10000 + (i * 23) % 30000;
    }
    cudaMemcpy(d_ranges, h_ranges, n * 4 * sizeof(RangeConstraint), cudaMemcpyHostToDevice);
    
    // Layout D: float4
    float4 *d_packed4;
    cudaMalloc(&d_packed4, n * sizeof(float4));
    float4 *h_packed4 = new float4[n];
    for (int i = 0; i < n; i++) {
        h_packed4[i] = make_float4(
            (float)((i * 7 + 100) % 50000),
            (float)((i * 11 + 200) % 50000),
            (float)((i * 13 + 300) % 50000),
            (float)((i * 17 + 400) % 50000)
        );
    }
    cudaMemcpy(d_packed4, h_packed4, n * sizeof(float4), cudaMemcpyHostToDevice);
    
    // Also float values for layout D
    float *d_fvalues;
    cudaMalloc(&d_fvalues, n * sizeof(float));
    float *h_fvalues = new float[n];
    for (int i = 0; i < n; i++) h_fvalues[i] = (float)h_values[i];
    cudaMemcpy(d_fvalues, h_fvalues, n * sizeof(float), cudaMemcpyHostToDevice);
    
    int block = 256;
    int grid = (n + block - 1) / block;
    
    // Warmup
    check_loose<<<grid, block>>>(d_bounds_a, d_values, d_results, n);
    check_packed_u16<<<grid, block>>>(d_bounds_b, d_values, d_results, n);
    check_ranges<<<grid, block>>>(d_ranges, d_values, d_results, n);
    check_float4<<<grid, block>>>(d_packed4, d_fvalues, d_results, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    int iters = 100;
    
    struct Test { const char* name; size_t bytes_per_elem; };
    Test tests[] = {
        {"8x int32 (32B/elem)", 32},
        {"8x uint16 (16B/elem)", 16},
        {"4x Range{lo,hi} (32B/elem)", 32},
        {"float4 (16B/elem)", 16},
    };
    
    for (int t = 0; t < 4; t++) {
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            switch (t) {
                case 0: check_loose<<<grid, block>>>(d_bounds_a, d_values, d_results, n); break;
                case 1: check_packed_u16<<<grid, block>>>(d_bounds_b, d_values, d_results, n); break;
                case 2: check_ranges<<<grid, block>>>(d_ranges, d_values, d_results, n); break;
                case 3: check_float4<<<grid, block>>>(d_packed4, d_fvalues, d_results, n); break;
            }
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double throughput = (double)n * iters / (ms / 1000.0);
        double bw = (double)(tests[t].bytes_per_elem + 4 + 4) * n * iters / (ms / 1000.0) / 1e9;
        
        printf("%-30s | %12.0f checks/s | %6.1f GB/s | %.2f ms/iter\n",
               tests[t].name, throughput, bw, ms / iters);
    }
    
    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);
    printf("\nVRAM: %zuMB used / %zuMB total (%zuMB free)\n",
           (total_mem - free_mem) / (1024*1024), total_mem / (1024*1024), free_mem / (1024*1024));
    
    delete[] h_values; delete[] h_bounds; delete[] h_bounds_b;
    delete[] h_ranges; delete[] h_packed4; delete[] h_fvalues;
    cudaFree(d_bounds_a); cudaFree(d_bounds_b); cudaFree(d_ranges);
    cudaFree(d_packed4); cudaFree(d_values); cudaFree(d_fvalues); cudaFree(d_results);
    
    return 0;
}
