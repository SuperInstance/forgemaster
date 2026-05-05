// Experiment 07: VRAM-scaling sweep — find the sweet spot for constraint density
// Systematically vary: number of elements, constraints per element
// Track: throughput, VRAM usage, bandwidth utilization

#include <cstdio>
#include <cuda_runtime.h>
#include <vector_types.h>

__global__ void warp_cooperative_check(const float4* __restrict__ bounds,
                                        const float* __restrict__ values,
                                        int* results, int n, int warp_bounds) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int warp_id = idx >> 5;
    int lane = idx & 31;
    if (warp_id >= n) return;
    
    float val = values[warp_id];
    float4 b = bounds[warp_id * warp_bounds + lane];
    int my_pass = (val < b.x && val < b.y && val < b.z && val < b.w) ? 1 : 0;
    unsigned all_pass = __all_sync(0xffffffff, my_pass);
    if (lane == 0) results[warp_id] = all_pass;
}

int main() {
    printf("=== VRAM-Scaling Sweep: Warp-Cooperative Constraint Checking ===\n");
    printf("RTX 4050 Laptop: 6GB VRAM\n\n");
    printf("%-12s %-12s %-18s %-18s %-12s %-10s\n", 
           "Elements", "Constr/elem", "Throughput (c/s)", "BW (GB/s)", "VRAM (MB)", "ms/iter");
    printf("%-12s %-12s %-18s %-18s %-12s %-10s\n",
           "--------", "-----------", "----------------", "---------", "---------", "--------");
    
    int elem_counts[] = {1000, 10000, 100000, 1000000, 2000000, 5000000};
    int constraints_per_elem[] = {4, 16, 32, 64, 128};
    int warp_bounds = 32; // each lane loads 1 float4 = 4 constraints, 32 lanes = 128 constraints
    
    for (int e = 0; e < 6; e++) {
        int n = elem_counts[e];
        size_t bounds_bytes = (size_t)n * warp_bounds * sizeof(float4);
        size_t values_bytes = n * sizeof(float);
        size_t results_bytes = n * sizeof(int);
        size_t total_bytes = bounds_bytes + values_bytes + results_bytes;
        
        // Check if it fits in VRAM
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        if (total_bytes > free_mem * 0.8) { // leave 20% headroom
            printf("%-12d %-12d (skipped — needs %zuMB, only %zuMB free)\n",
                   n, 128, total_bytes/(1024*1024), free_mem/(1024*1024));
            continue;
        }
        
        float4 *d_bounds;
        float *d_values;
        int *d_results;
        cudaMalloc(&d_bounds, bounds_bytes);
        cudaMalloc(&d_values, values_bytes);
        cudaMalloc(&d_results, results_bytes);
        
        // Quick fill
        float4 h_b = make_float4(100.0f, 200.0f, 300.0f, 400.0f);
        float h_v = 50.0f;
        int h_r = 0;
        
        // Initialize with cudaMemset for speed, then set a few values
        cudaMemset(d_bounds, 0x42, bounds_bytes); // sets to some float value
        cudaMemset(d_results, 0, results_bytes);
        cudaMemcpy(d_values, &h_v, sizeof(float), cudaMemcpyHostToDevice);
        // Fill values array
        float *h_vals = new float[n];
        for (int i = 0; i < n; i++) h_vals[i] = 50.0f;
        cudaMemcpy(d_values, h_vals, values_bytes, cudaMemcpyHostToDevice);
        delete[] h_vals;
        
        int block = 256;
        int grid = (n * 32 + block - 1) / block; // each element uses 32 threads
        
        // Warmup
        warp_cooperative_check<<<grid, block>>>(d_bounds, d_values, d_results, n, warp_bounds);
        cudaDeviceSynchronize();
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        int iters = 50;
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            warp_cooperative_check<<<grid, block>>>(d_bounds, d_values, d_results, n, warp_bounds);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double elem_per_sec = (double)n * iters / (ms / 1000.0);
        double constr_per_sec = elem_per_sec * 128; // 128 constraints per element
        double total_ops = (double)(bounds_bytes + values_bytes + results_bytes) * iters;
        double bw = total_ops / (ms / 1000.0) / 1e9;
        
        cudaMemGetInfo(&free_mem, &total_mem);
        size_t used_mb = (total_mem - free_mem) / (1024*1024);
        
        printf("%-12d %-12d %-18.0f %-18.1f %-12zu %-10.2f\n",
               n, 128, constr_per_sec, bw, used_mb, ms / iters);
        
        cudaFree(d_bounds);
        cudaFree(d_values);
        cudaFree(d_results);
    }
    
    // Also test scaling constraints per element at fixed 1M elements
    printf("\n=== Constraint Density Scaling (1M elements) ===\n");
    printf("%-20s %-18s %-12s %-10s\n", "Constr/elem", "Throughput (c/s)", "VRAM (MB)", "ms/iter");
    
    // Re-run with variable warp_bounds by using different kernel configs
    int n = 1000000;
    int bounds_configs[] = {1, 2, 4, 8, 16, 32}; // float4 per warp = 4*32 = 128 max
    
    for (int c = 0; c < 6; c++) {
        int num_float4 = bounds_configs[c];
        int constr = num_float4 * 4;
        size_t bounds_bytes = (size_t)n * num_float4 * sizeof(float4);
        size_t total_alloc = bounds_bytes + n * sizeof(float) + n * sizeof(int);
        
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        if (total_alloc > free_mem * 0.8) {
            printf("%-20d (skipped)\n", constr);
            continue;
        }
        
        float4 *d_bounds;
        float *d_values;
        int *d_results;
        cudaMalloc(&d_bounds, bounds_bytes);
        cudaMalloc(&d_values, n * sizeof(float));
        cudaMalloc(&d_results, n * sizeof(int));
        
        cudaMemset(d_bounds, 0x42, bounds_bytes);
        float *h_v = new float[n];
        for (int i = 0; i < n; i++) h_v[i] = 50.0f;
        cudaMemcpy(d_values, h_v, n * sizeof(float), cudaMemcpyHostToDevice);
        delete[] h_v;
        
        int block = 256;
        int grid;
        
        // Use appropriate kernel based on num_float4
        if (num_float4 == 1) {
            // Simple: 1 thread per element, 1 float4
            grid = (n + block - 1) / block;
        } else {
            // Warp-cooperative: 32 threads per element
            grid = (n * 32 + block - 1) / block;
        }
        
        // Warmup
        if (num_float4 <= 32) {
            warp_cooperative_check<<<grid, block>>>(d_bounds, d_values, d_results, n, num_float4);
        }
        cudaDeviceSynchronize();
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        int iters = 50;
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            warp_cooperative_check<<<grid, block>>>(d_bounds, d_values, d_results, n, num_float4);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double constr_per_sec = (double)n * constr * iters / (ms / 1000.0);
        
        cudaMemGetInfo(&free_mem, &total_mem);
        printf("%-20d %-18.0f %-12zu %-10.2f\n",
               constr, constr_per_sec, (total_mem - free_mem)/(1024*1024), ms/iters);
        
        cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    }
    
    return 0;
}
