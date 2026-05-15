// Experiment 04: Bandwidth-bound constraint checking
// Identify if we're compute-bound or memory-bound
// Test: pure compute (register ops) vs memory-heavy (random access) vs sequential access

#include <cstdio>
#include <cuda_runtime.h>

// Test 1: Pure compute — all in registers
__global__ void pure_compute(int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int val = idx * 7 + 13;
    // 100 arithmetic ops per element — all in registers
    #pragma unroll
    for (int i = 0; i < 100; i++) {
        val = val * 1103515245 + 12345; // LCG
        val ^= (val >> 16);
    }
    results[idx] = val;
}

// Test 2: Sequential memory access — streaming
__global__ void sequential_access(const int* __restrict__ input, int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int val = input[idx]; // sequential read
    val = val * 1103515245 + 12345;
    val ^= (val >> 16);
    results[idx] = val; // sequential write
}

// Test 3: Random access — strided
__global__ void random_access(const int* __restrict__ input, int* results, int n, int stride) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int access_idx = ((idx * stride) % n + n) % n;
    int val = input[access_idx];
    val = val * 1103515245 + 12345;
    val ^= (val >> 16);
    results[idx] = val;
}

// Test 4: Constraint checking workload — realistic mix
__global__ void constraint_workload(const int* __restrict__ bounds,
                                     const int* __restrict__ values,
                                     int* results, int n, int num_constraints) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int pass = 1;
    #pragma unroll
    for (int c = 0; c < 8; c++) { // 8 constraints per element
        int bound = bounds[idx * num_constraints + c];
        int val = values[idx];
        if (val >= bound) { pass = 0; break; }
    }
    results[idx] = pass;
}

int main() {
    printf("=== Bandwidth vs Compute Bottleneck Analysis ===\n\n");
    
    int n = 10000000; // 10M elements
    size_t bytes = n * sizeof(int);
    
    int *d_input, *d_bounds, *d_values, *d_results;
    cudaMalloc(&d_input, bytes);
    cudaMalloc(&d_bounds, n * 8 * sizeof(int)); // 8 constraints per element
    cudaMalloc(&d_values, bytes);
    cudaMalloc(&d_results, bytes);
    
    // Fill
    int *h_data = new int[n];
    for (int i = 0; i < n; i++) h_data[i] = i * 7 + 3;
    cudaMemcpy(d_input, h_data, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_data, bytes, cudaMemcpyHostToDevice);
    
    int *h_bounds = new int[n * 8];
    for (int i = 0; i < n * 8; i++) h_bounds[i] = (i * 13 + 7) % 10000;
    cudaMemcpy(d_bounds, h_bounds, n * 8 * sizeof(int), cudaMemcpyHostToDevice);
    
    int block = 256;
    int grid = (n + block - 1) / block;
    
    // Warmup all
    pure_compute<<<grid, block>>>(d_results, n);
    sequential_access<<<grid, block>>>(d_input, d_results, n);
    random_access<<<grid, block>>>(d_input, d_results, n, 7919);
    constraint_workload<<<grid, block>>>(d_bounds, d_values, d_results, n, 8);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    int iters = 100;
    
    // Test each kernel
    const char* names[] = {"Pure Compute", "Sequential Access", "Random Access (stride=7919)", "8-Constraint Check"};
    
    for (int test = 0; test < 4; test++) {
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            switch (test) {
                case 0: pure_compute<<<grid, block>>>(d_results, n); break;
                case 1: sequential_access<<<grid, block>>>(d_input, d_results, n); break;
                case 2: random_access<<<grid, block>>>(d_input, d_results, n, 7919); break;
                case 3: constraint_workload<<<grid, block>>>(d_bounds, d_values, d_results, n, 8); break;
            }
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double throughput = (double)n * iters / (ms / 1000.0);
        
        // Calculate bandwidth
        double bw = 0;
        switch (test) {
            case 0: bw = 4.0 * n * iters / (ms / 1000.0) / 1e9; break; // write only
            case 1: bw = 8.0 * n * iters / (ms / 1000.0) / 1e9; break; // read + write
            case 2: bw = 8.0 * n * iters / (ms / 1000.0) / 1e9; break; // read + write
            case 3: bw = (4*(1+8) + 4) * n * iters / (ms / 1000.0) / 1e9; break; // 8 bounds + value + result
        }
        
        printf("%-30s | %12.0f ops/s | %6.1f GB/s | %6.2f ms/iter\n",
               names[test], throughput, bw, ms / iters);
    }
    
    // VRAM check
    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);
    printf("\nVRAM: %zuMB used / %zuMB total\n", (total_mem - free_mem) / (1024*1024), total_mem / (1024*1024));
    
    delete[] h_data;
    delete[] h_bounds;
    cudaFree(d_input);
    cudaFree(d_bounds);
    cudaFree(d_values);
    cudaFree(d_results);
    
    return 0;
}
