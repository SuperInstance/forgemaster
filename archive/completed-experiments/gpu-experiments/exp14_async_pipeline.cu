// Experiment 14: Async pipelined constraint checking with host pinned memory
// Overlaps host->device transfer with kernel execution
// Simulates continuous sensor stream: host writes new values while GPU checks previous batch

#include <cstdio>
#include <cuda_runtime.h>

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
    printf("=== Async Pipelined Constraint Checking ===\n\n");
    
    int n = 1000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    
    // Allocate pinned host memory for async transfer
    int *h_values_0, *h_values_1, *h_results_0, *h_results_1;
    cudaHostAlloc(&h_values_0, n * sizeof(int), cudaHostAllocDefault);
    cudaHostAlloc(&h_values_1, n * sizeof(int), cudaHostAllocDefault);
    cudaHostAlloc(&h_results_0, n * sizeof(int), cudaHostAllocDefault);
    cudaHostAlloc(&h_results_1, n * sizeof(int), cudaHostAllocDefault);
    
    // Fill host buffers with different data patterns
    for (int i = 0; i < n; i++) {
        h_values_0[i] = (i * 7 + 13) % 250;
        h_values_1[i] = (i * 11 + 37) % 250;
    }
    
    // Device buffers (double-buffered)
    int *d_values_0, *d_values_1, *d_results_0, *d_results_1;
    uchar8 *d_bounds;
    cudaMalloc(&d_values_0, n * sizeof(int));
    cudaMalloc(&d_values_1, n * sizeof(int));
    cudaMalloc(&d_results_0, n * sizeof(int));
    cudaMalloc(&d_results_1, n * sizeof(int));
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    
    // Fill bounds
    uchar8 *h_b = new uchar8[n];
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    
    // Create streams
    cudaStream_t stream_0, stream_1;
    cudaStreamCreate(&stream_0);
    cudaStreamCreate(&stream_1);
    
    // Test 1: Naive sequential (H2D, kernel, D2H per batch)
    printf("--- Naive Sequential ---\n");
    int batches = 100;
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int b = 0; b < batches; b++) {
        int *h_v = (b % 2 == 0) ? h_values_0 : h_values_1;
        cudaMemcpy(d_values_0, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
        int8_check8<<<grid, block>>>(d_bounds, d_values_0, d_results_0, n);
        cudaMemcpy(h_results_0, d_results_0, n * sizeof(int), cudaMemcpyDeviceToHost);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_naive;
    cudaEventElapsedTime(&ms_naive, start, stop);
    
    printf("  %d batches of %d elements: %.2f ms total, %.3f ms/batch\n",
           batches, n, ms_naive, ms_naive/batches);
    
    // Test 2: Async with streams and double buffering
    printf("--- Async Double-Buffered ---\n");
    
    cudaEventRecord(start);
    for (int b = 0; b < batches; b++) {
        int *h_v = (b % 2 == 0) ? h_values_0 : h_values_1;
        int *h_r = (b % 2 == 0) ? h_results_0 : h_results_1;
        int *d_v = (b % 2 == 0) ? d_values_0 : d_values_1;
        int *d_r = (b % 2 == 0) ? d_results_0 : d_results_1;
        cudaStream_t stream = (b % 2 == 0) ? stream_0 : stream_1;
        
        // Wait for previous operation on this buffer to complete
        cudaStreamSynchronize(stream);
        
        cudaMemcpyAsync(d_v, h_v, n * sizeof(int), cudaMemcpyHostToDevice, stream);
        int8_check8<<<grid, block, 0, stream>>>(d_bounds, d_v, d_r, n);
        cudaMemcpyAsync(h_r, d_r, n * sizeof(int), cudaMemcpyDeviceToHost, stream);
    }
    cudaStreamSynchronize(stream_0);
    cudaStreamSynchronize(stream_1);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_async;
    cudaEventElapsedTime(&ms_async, start, stop);
    
    printf("  %d batches of %d elements: %.2f ms total, %.3f ms/batch\n",
           batches, n, ms_async, ms_async/batches);
    
    // Test 3: Overlapped — transfer batch N+1 while kernel runs on batch N
    printf("--- Overlapped (Transfer || Kernel) ---\n");
    
    cudaEventRecord(start);
    // Prefetch first batch
    cudaMemcpyAsync(d_values_0, h_values_0, n * sizeof(int), cudaMemcpyHostToDevice, stream_0);
    
    for (int b = 0; b < batches; b++) {
        int next_b = b + 1;
        int *d_v = (b % 2 == 0) ? d_values_0 : d_values_1;
        int *d_r = (b % 2 == 0) ? d_results_0 : d_results_1;
        int *h_r = (b % 2 == 0) ? h_results_0 : h_results_1;
        cudaStream_t k_stream = (b % 2 == 0) ? stream_0 : stream_1;
        
        // Launch kernel on current batch
        int8_check8<<<grid, block, 0, k_stream>>>(d_bounds, d_v, d_r, n);
        cudaMemcpyAsync(h_r, d_r, n * sizeof(int), cudaMemcpyDeviceToHost, k_stream);
        
        // Start transferring next batch on other stream (overlaps!)
        if (next_b < batches) {
            int *d_v_next = (next_b % 2 == 0) ? d_values_0 : d_values_1;
            int *h_v_next = (next_b % 2 == 0) ? h_values_0 : h_values_1;
            cudaStream_t t_stream = (next_b % 2 == 0) ? stream_0 : stream_1;
            cudaMemcpyAsync(d_v_next, h_v_next, n * sizeof(int), cudaMemcpyHostToDevice, t_stream);
        }
    }
    cudaStreamSynchronize(stream_0);
    cudaStreamSynchronize(stream_1);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_overlap;
    cudaEventElapsedTime(&ms_overlap, start, stop);
    
    printf("  %d batches of %d elements: %.2f ms total, %.3f ms/batch\n",
           batches, n, ms_overlap, ms_overlap/batches);
    
    printf("\n=== Summary ===\n");
    printf("Naive:    %.3f ms/batch (baseline)\n", ms_naive/batches);
    printf("Async:    %.3f ms/batch (%.2fx)\n", ms_async/batches, ms_naive/ms_async);
    printf("Overlap:  %.3f ms/batch (%.2fx)\n", ms_overlap/batches, ms_naive/ms_overlap);
    
    printf("\nThroughput (Naive):    %.0f elem/s\n", (double)n * batches / (ms_naive/1000.0));
    printf("Throughput (Overlap):  %.0f elem/s\n", (double)n * batches / (ms_overlap/1000.0));
    
    // Verify correctness
    int cpu_pass = 0;
    for (int i = 0; i < n; i++) {
        int val = h_values_0[i];
        uchar8 b = h_b[i];
        int pass = 1;
        if (val >= b.a) pass = 0;
        else if (val >= b.b) pass = 0;
        else if (val >= b.c) pass = 0;
        else if (val >= b.d) pass = 0;
        else if (val >= b.e) pass = 0;
        else if (val >= b.f) pass = 0;
        else if (val >= b.g) pass = 0;
        else if (val >= b.h) pass = 0;
        if (pass) cpu_pass++;
    }
    
    int gpu_pass = 0;
    for (int i = 0; i < n; i++) if (h_results_0[i]) gpu_pass++;
    printf("\nVerification: CPU pass=%d, GPU pass=%d %s\n",
           cpu_pass, gpu_pass, cpu_pass == gpu_pass ? "✓" : "✗ MISMATCH");
    
    delete[] h_b;
    cudaFreeHost(h_values_0); cudaFreeHost(h_values_1);
    cudaFreeHost(h_results_0); cudaFreeHost(h_results_1);
    cudaFree(d_values_0); cudaFree(d_values_1);
    cudaFree(d_results_0); cudaFree(d_results_1);
    cudaFree(d_bounds);
    cudaStreamDestroy(stream_0); cudaStreamDestroy(stream_1);
    
    return 0;
}
