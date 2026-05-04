// Experiment 10: CPU vs GPU differential test + INT8 scaling sweep
// Verify INT8 x8 correctness and find scaling limits

#include <cstdio>
#include <cuda_runtime.h>
#include <vector_types.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

__global__ void int8_check8(const uchar8* __restrict__ bounds,
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

int main() {
    printf("=== INT8 x8 Differential Test + Scaling ===\n\n");
    
    int test_sizes[] = {1000, 10000, 100000, 1000000, 10000000, 50000000};
    int num_sizes = 6;
    
    for (int s = 0; s < num_sizes; s++) {
        int n = test_sizes[s];
        
        uchar8 *h_bounds = new uchar8[n];
        int *h_values = new int[n];
        int *h_results = new int[n];
        int *h_cpu_results = new int[n];
        
        // Generate data
        for (int i = 0; i < n; i++) {
            h_bounds[i] = {
                (unsigned char)((i*7+30)%250),
                (unsigned char)((i*11+40)%250),
                (unsigned char)((i*13+50)%250),
                (unsigned char)((i*17+60)%250),
                (unsigned char)((i*19+70)%250),
                (unsigned char)((i*23+80)%250),
                (unsigned char)((i*29+90)%250),
                (unsigned char)((i*31+100)%250)
            };
            h_values[i] = (i * 11 + 37) % 250; // Keep in int8 range
        }
        
        // CPU reference
        for (int i = 0; i < n; i++) {
            int val = h_values[i];
            uchar8 b = h_bounds[i];
            int pass = 1;
            if (val >= b.a) pass = 0;
            else if (val >= b.b) pass = 0;
            else if (val >= b.c) pass = 0;
            else if (val >= b.d) pass = 0;
            else if (val >= b.e) pass = 0;
            else if (val >= b.f) pass = 0;
            else if (val >= b.g) pass = 0;
            else if (val >= b.h) pass = 0;
            h_cpu_results[i] = pass;
        }
        
        // GPU
        uchar8 *d_bounds;
        int *d_values, *d_results;
        cudaMalloc(&d_bounds, n * sizeof(uchar8));
        cudaMalloc(&d_values, n * sizeof(int));
        cudaMalloc(&d_results, n * sizeof(int));
        
        cudaMemcpy(d_bounds, h_bounds, n * sizeof(uchar8), cudaMemcpyHostToDevice);
        cudaMemcpy(d_values, h_values, n * sizeof(int), cudaMemcpyHostToDevice);
        
        int block = 256;
        int grid = (n + block - 1) / block;
        
        // Benchmark
        int iters = (n > 1000000) ? 50 : 100;
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        // Warmup
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaDeviceSynchronize();
        
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        // Differential test
        cudaMemcpy(h_results, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
        int mismatches = 0;
        for (int i = 0; i < n; i++) {
            if (h_results[i] != h_cpu_results[i]) mismatches++;
        }
        
        double constr_per_sec = (double)n * 8 * iters / (ms / 1000.0);
        double bw = (double)(8 + 4 + 4) * n * iters / (ms / 1000.0) / 1e9;
        
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        
        printf("n=%10d | %15.0f constr/s | %6.1f GB/s | mismatches: %d/%d | VRAM free: %zuMB\n",
               n, constr_per_sec, bw, mismatches, n, free_mem/(1024*1024));
        
        delete[] h_bounds; delete[] h_values; delete[] h_results; delete[] h_cpu_results;
        cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    }
    
    return 0;
}
