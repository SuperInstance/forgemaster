// Experiment 12: Atomic aggregation — multi-block constraint counting
// Count total passing/failing constraints across entire dataset atomically
// Tests: atomicAdd vs warp-reduce-then-atomic vs block-reduce-then-atomic

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

// Method 1: Every thread does atomicAdd
__global__ void count_atomic_per_thread(const uchar8* __restrict__ bounds,
                                         const int* __restrict__ values,
                                         int* total_pass, int* total_fail, int n) {
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
    
    if (pass) atomicAdd(total_pass, 1);
    else atomicAdd(total_fail, 1);
}

// Method 2: Warp reduce then atomicAdd
__global__ void count_warp_reduce(const uchar8* __restrict__ bounds,
                                   const int* __restrict__ values,
                                   int* total_pass, int* total_fail, int n) {
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
    
    // Warp reduce using ballot
    unsigned ballot = __ballot_sync(0xffffffff, pass);
    if ((threadIdx.x & 31) == 0) {
        int warp_pass = __popc(ballot);
        atomicAdd(total_pass, warp_pass);
        atomicAdd(total_fail, 32 - warp_pass);
    }
}

// Method 3: Block reduce then atomicAdd
__global__ void count_block_reduce(const uchar8* __restrict__ bounds,
                                    const int* __restrict__ values,
                                    int* total_pass, int* total_fail, int n) {
    __shared__ int s_pass, s_fail;
    int tid = threadIdx.x;
    
    if (tid == 0) { s_pass = 0; s_fail = 0; }
    __syncthreads();
    
    int idx = blockIdx.x * blockDim.x + tid;
    if (idx < n) {
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
        
        atomicAdd(&s_pass, pass);
        atomicAdd(&s_fail, 1 - pass);
    }
    __syncthreads();
    
    if (tid == 0) {
        atomicAdd(total_pass, s_pass);
        atomicAdd(total_fail, s_fail);
    }
}

int main() {
    printf("=== Atomic Aggregation Strategies ===\n\n");
    
    int n = 10000000;
    uchar8 *d_bounds;
    int *d_values, *d_total_pass, *d_total_fail;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_total_pass, sizeof(int));
    cudaMalloc(&d_total_fail, sizeof(int));
    
    uchar8 *h_bounds = new uchar8[n];
    int *h_vals = new int[n];
    for (int i = 0; i < n; i++) {
        h_bounds[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                       (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                       (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                       (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        h_vals[i] = (i * 7 + 13) % 250;
    }
    cudaMemcpy(d_bounds, h_bounds, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_vals, n * sizeof(int), cudaMemcpyHostToDevice);
    
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 100;
    
    // CPU reference count
    int cpu_pass = 0, cpu_fail = 0;
    for (int i = 0; i < n; i++) {
        int val = h_vals[i];
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
        if (pass) cpu_pass++; else cpu_fail++;
    }
    
    const char* names[] = {"Per-thread atomic", "Warp reduce + atomic", "Block reduce + atomic"};
    
    for (int t = 0; t < 3; t++) {
        int zero = 0;
        cudaMemcpy(d_total_pass, &zero, sizeof(int), cudaMemcpyHostToDevice);
        cudaMemcpy(d_total_fail, &zero, sizeof(int), cudaMemcpyHostToDevice);
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            cudaMemcpy(d_total_pass, &zero, sizeof(int), cudaMemcpyHostToDevice);
            cudaMemcpy(d_total_fail, &zero, sizeof(int), cudaMemcpyHostToDevice);
            switch (t) {
                case 0: count_atomic_per_thread<<<grid, block>>>(d_bounds, d_values, d_total_pass, d_total_fail, n); break;
                case 1: count_warp_reduce<<<grid, block>>>(d_bounds, d_values, d_total_pass, d_total_fail, n); break;
                case 2: count_block_reduce<<<grid, block>>>(d_bounds, d_values, d_total_pass, d_total_fail, n); break;
            }
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        int gpu_pass, gpu_fail;
        cudaMemcpy(&gpu_pass, d_total_pass, sizeof(int), cudaMemcpyDeviceToHost);
        cudaMemcpy(&gpu_fail, d_total_fail, sizeof(int), cudaMemcpyDeviceToHost);
        
        int pass_ok = (gpu_pass == cpu_pass);
        int fail_ok = (gpu_fail == cpu_fail);
        
        printf("%-25s | %8.2f ms/iter | pass: %d/%d %s | fail: %d/%d %s\n",
               names[t], ms/iters,
               gpu_pass, cpu_pass, pass_ok ? "✓" : "✗",
               gpu_fail, cpu_fail, fail_ok ? "✓" : "✗");
    }
    
    delete[] h_bounds; delete[] h_vals;
    cudaFree(d_bounds); cudaFree(d_values);
    cudaFree(d_total_pass); cudaFree(d_total_fail);
    
    return 0;
}
