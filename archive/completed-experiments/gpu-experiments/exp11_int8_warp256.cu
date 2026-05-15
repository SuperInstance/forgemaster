// Experiment 11: INT8 warp-cooperative — 32 lanes x 8 bounds = 256 constraints/element
// This is the theoretical maximum density: 256 bounds per element using INT8
// Each lane loads 8 bytes (uchar8), warp processes 32 x 8 = 256 constraints
// Total memory per element: 256 bytes (32 lanes x 8 bytes)

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

__global__ void int8_warp256(const uchar8* __restrict__ bounds,
                              const int* __restrict__ values,
                              int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int warp_id = idx >> 5;
    int lane = idx & 31;
    if (warp_id >= n) return;
    
    int val = values[warp_id];
    uchar8 b = bounds[warp_id * 32 + lane];
    
    int my_pass = 1;
    if (val >= b.a) my_pass = 0;
    else if (val >= b.b) my_pass = 0;
    else if (val >= b.c) my_pass = 0;
    else if (val >= b.d) my_pass = 0;
    else if (val >= b.e) my_pass = 0;
    else if (val >= b.f) my_pass = 0;
    else if (val >= b.g) my_pass = 0;
    else if (val >= b.h) my_pass = 0;
    
    unsigned all_pass = __all_sync(0xffffffff, my_pass);
    if (lane == 0) results[warp_id] = all_pass;
}

// Also test with __any_sync (any thread passes = element passes)
// Useful for OR-style constraints (at least one constraint satisfied)
__global__ void int8_warp256_any(const uchar8* __restrict__ bounds,
                                  const int* __restrict__ values,
                                  int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int warp_id = idx >> 5;
    int lane = idx & 31;
    if (warp_id >= n) return;
    
    int val = values[warp_id];
    uchar8 b = bounds[warp_id * 32 + lane];
    
    int any_pass = 0;
    if (val < b.a) any_pass = 1;
    else if (val < b.b) any_pass = 1;
    else if (val < b.c) any_pass = 1;
    else if (val < b.d) any_pass = 1;
    else if (val < b.e) any_pass = 1;
    else if (val < b.f) any_pass = 1;
    else if (val < b.g) any_pass = 1;
    else if (val < b.h) any_pass = 1;
    
    unsigned result = __any_sync(0xffffffff, any_pass);
    if (lane == 0) results[warp_id] = result;
}

int main() {
    printf("=== INT8 Warp-Cooperative: 256 Constraints Per Element ===\n\n");
    
    // Scale test: how many elements can we handle with 256 constraints each?
    int test_sizes[] = {1000, 10000, 100000, 500000, 1000000, 2000000};
    
    for (int s = 0; s < 6; s++) {
        int n = test_sizes[s];
        size_t bounds_bytes = (size_t)n * 32 * sizeof(uchar8); // 256 bytes per element
        size_t values_bytes = n * sizeof(int);
        size_t results_bytes = n * sizeof(int);
        size_t total = bounds_bytes + values_bytes + results_bytes;
        
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        if (total > free_mem * 0.8) {
            printf("n=%10d (256 constr/elem): SKIPPED — needs %zuMB, %zuMB free\n",
                   n, total/(1024*1024), free_mem/(1024*1024));
            continue;
        }
        
        uchar8 *d_bounds;
        int *d_values, *d_results;
        cudaMalloc(&d_bounds, bounds_bytes);
        cudaMalloc(&d_values, values_bytes);
        cudaMalloc(&d_results, results_bytes);
        
        // Fill with simple pattern
        uchar8 *h_bounds = new uchar8[n * 32];
        for (int i = 0; i < n * 32; i++) {
            h_bounds[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                           (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                           (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                           (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        }
        cudaMemcpy(d_bounds, h_bounds, bounds_bytes, cudaMemcpyHostToDevice);
        
        int *h_vals = new int[n];
        for (int i = 0; i < n; i++) h_vals[i] = (i * 7 + 13) % 250;
        cudaMemcpy(d_values, h_vals, values_bytes, cudaMemcpyHostToDevice);
        
        int block = 256;
        int grid = (n * 32 + block - 1) / block;
        
        // Warmup
        int8_warp256<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaDeviceSynchronize();
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        int iters = 50;
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            int8_warp256<<<grid, block>>>(d_bounds, d_values, d_results, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double constr_per_sec = (double)n * 256 * iters / (ms / 1000.0);
        double bw = (double)(256 + 4 + 4) * n * iters / (ms / 1000.0) / 1e9;
        
        cudaMemGetInfo(&free_mem, &total_mem);
        
        printf("n=%10d (256c/e) | %18.0f constr/s | %7.1f GB/s | VRAM: %zuMB used | %.2f ms\n",
               n, constr_per_sec, bw, (total_mem-free_mem)/(1024*1024), ms/iters);
        
        // Differential test (CPU only for smaller sizes)
        if (n <= 100000) {
            int *h_res = new int[n];
            int *h_cpu = new int[n];
            cudaMemcpy(h_res, d_results, results_bytes, cudaMemcpyDeviceToHost);
            
            for (int i = 0; i < n; i++) {
                int val = h_vals[i];
                int pass = 1;
                for (int lane = 0; lane < 32 && pass; lane++) {
                    uchar8 b = h_bounds[i * 32 + lane];
                    if (val >= b.a) pass = 0;
                    else if (val >= b.b) pass = 0;
                    else if (val >= b.c) pass = 0;
                    else if (val >= b.d) pass = 0;
                    else if (val >= b.e) pass = 0;
                    else if (val >= b.f) pass = 0;
                    else if (val >= b.g) pass = 0;
                    else if (val >= b.h) pass = 0;
                }
                h_cpu[i] = pass;
            }
            
            int mm = 0;
            for (int i = 0; i < n; i++) if (h_res[i] != h_cpu[i]) mm++;
            printf("  Differential: %d/%d mismatches\n", mm, n);
            
            delete[] h_res; delete[] h_cpu;
        }
        
        delete[] h_bounds; delete[] h_vals;
        cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    }
    
    return 0;
}
