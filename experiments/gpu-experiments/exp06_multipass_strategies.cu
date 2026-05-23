// Experiment 06: Multi-pass constraint checking — warp-aggregated float4
// Combine the best of exp05 (float4 layout) with warp-level voting (exp01)
// Each warp processes 32 elements, each with 4-constraint float4
// Then warp-vote to see if ALL 32 elements pass (compound constraint)

#include <cstdio>
#include <cuda_runtime.h>
#include <vector_types.h>

// Single-pass: 4 constraints per element, individual results
__global__ void single_pass_check(const float4* __restrict__ bounds,
                                   const float* __restrict__ values,
                                   int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    float val = values[idx];
    float4 b = bounds[idx];
    results[idx] = (val < b.x && val < b.y && val < b.z && val < b.w) ? 1 : 0;
}

// Warp-aggregated: 32 elements, each with 4 constraints, warp-vote ALL must pass
__global__ void warp_aggregated_check(const float4* __restrict__ bounds,
                                       const float* __restrict__ values,
                                       int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    float val = values[idx];
    float4 b = bounds[idx];
    int my_pass = (val < b.x && val < b.y && val < b.z && val < b.w) ? 1 : 0;
    
    // Warp vote: ALL threads in warp must pass
    unsigned all_pass = __all_sync(0xffffffff, my_pass);
    
    // Lane 0 writes result
    if ((threadIdx.x & 31) == 0) {
        results[idx >> 5] = all_pass;
    }
}

// Chained constraints: 2 rounds of 4 constraints (8 total), with early exit
// Round 1 checks float4 A, Round 2 checks float4 B (only if A passed)
__global__ void chained_8constraint(const float4* __restrict__ bounds_a,
                                     const float4* __restrict__ bounds_b,
                                     const float* __restrict__ values,
                                     int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    float val = values[idx];
    
    // Round 1
    float4 ba = bounds_a[idx];
    if (val >= ba.x || val >= ba.y || val >= ba.z || val >= ba.w) {
        results[idx] = 0;
        return;
    }
    
    // Round 2 (only reached if round 1 passed)
    float4 bb = bounds_b[idx];
    results[idx] = (val < bb.x && val < bb.y && val < bb.z && val < bb.w) ? 1 : 0;
}

// Warp-cooperative: Each warp processes 1 element with 32*4 = 128 constraints
// Thread T in warp checks constraint T*4..T*4+3
__global__ void warp_cooperative_128(const float4* __restrict__ all_bounds,
                                      const float* __restrict__ values,
                                      int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int warp_id = idx >> 5;
    int lane = idx & 31;
    if (warp_id >= n) return;
    
    float val = values[warp_id];
    float4 b = all_bounds[warp_id * 32 + lane]; // 128 constraints per element
    
    int my_pass = (val < b.x && val < b.y && val < b.z && val < b.w) ? 1 : 0;
    
    unsigned all_pass = __all_sync(0xffffffff, my_pass);
    if (lane == 0) results[warp_id] = all_pass;
}

int main() {
    printf("=== Multi-Pass Constraint Checking Strategies ===\n\n");
    
    int n = 10000000;
    int iters = 100;
    
    // Allocate float4 bounds for all tests
    float4 *d_bounds_a, *d_bounds_b;
    float *d_values;
    int *d_results;
    cudaMalloc(&d_bounds_a, n * sizeof(float4));
    cudaMalloc(&d_bounds_b, n * sizeof(float4));
    cudaMalloc(&d_values, n * sizeof(float));
    cudaMalloc(&d_results, n * sizeof(int));
    
    // For warp_cooperative_128: n * 32 float4s
    float4 *d_128_bounds;
    cudaMalloc(&d_128_bounds, n * 32 * sizeof(float4));
    
    // Fill
    float4 *h_ba = new float4[n], *h_bb = new float4[n];
    float *h_val = new float[n];
    for (int i = 0; i < n; i++) {
        h_ba[i] = make_float4(i*0.7f+100, i*1.1f+200, i*1.3f+300, i*1.7f+400);
        h_bb[i] = make_float4(i*0.3f+50, i*0.9f+150, i*1.1f+250, i*1.9f+350);
        h_val[i] = (float)(i % 1000);
    }
    cudaMemcpy(d_bounds_a, h_ba, n * sizeof(float4), cudaMemcpyHostToDevice);
    cudaMemcpy(d_bounds_b, h_bb, n * sizeof(float4), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_val, n * sizeof(float), cudaMemcpyHostToDevice);
    
    float4 *h_128 = new float4[n * 32];
    for (int i = 0; i < n * 32; i++) h_128[i] = make_float4(i*0.5f+10, i*0.7f+20, i*0.9f+30, i*1.1f+40);
    cudaMemcpy(d_128_bounds, h_128, n * 32 * sizeof(float4), cudaMemcpyHostToDevice);
    
    int block = 256;
    int grid = (n + block - 1) / block;
    int grid_warp = ((n + 31) / 32 + block - 1) / block;
    
    // Warmup
    single_pass_check<<<grid, block>>>(d_bounds_a, d_values, d_results, n);
    warp_aggregated_check<<<grid, block>>>(d_bounds_a, d_values, d_results, n);
    chained_8constraint<<<grid, block>>>(d_bounds_a, d_bounds_b, d_values, d_results, n);
    warp_cooperative_128<<<grid, block>>>(d_128_bounds, d_values, d_results, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    struct Test { const char* name; int constraints_per_elem; int grid_sz; };
    Test tests[] = {
        {"4-constraint single pass", 4, grid},
        {"4-constraint warp-aggregated (32->1)", 4, grid},
        {"8-constraint chained (2x float4)", 8, grid},
        {"128-constraint warp-cooperative", 128, grid},
    };
    
    for (int t = 0; t < 4; t++) {
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            switch (t) {
                case 0: single_pass_check<<<tests[t].grid_sz, block>>>(d_bounds_a, d_values, d_results, n); break;
                case 1: warp_aggregated_check<<<tests[t].grid_sz, block>>>(d_bounds_a, d_values, d_results, n); break;
                case 2: chained_8constraint<<<tests[t].grid_sz, block>>>(d_bounds_a, d_bounds_b, d_values, d_results, n); break;
                case 3: warp_cooperative_128<<<tests[t].grid_sz, block>>>(d_128_bounds, d_values, d_results, n); break;
            }
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double elem_per_sec = (double)n * iters / (ms / 1000.0);
        double constraints_per_sec = elem_per_sec * tests[t].constraints_per_elem;
        
        printf("%-40s | %12.0f elem/s | %15.0f constr/s | %.2f ms\n",
               tests[t].name, elem_per_sec, constraints_per_sec, ms / iters);
    }
    
    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);
    printf("\nVRAM: %zuMB used / %zuMB total\n", (total_mem - free_mem)/(1024*1024), total_mem/(1024*1024));
    
    delete[] h_ba; delete[] h_bb; delete[] h_val; delete[] h_128;
    cudaFree(d_bounds_a); cudaFree(d_bounds_b); cudaFree(d_values);
    cudaFree(d_results); cudaFree(d_128_bounds);
    
    return 0;
}
