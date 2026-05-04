// Experiment 15: Multi-stream concurrent execution — simulates isolated safety domains
// Each stream handles a different safety domain (flight controls, thermal, power, navigation)
// Tests whether concurrent streams actually parallelize on RTX 4050

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
    printf("=== Multi-Stream Concurrent Safety Domains ===\n\n");
    
    int n = 1000000; // 1M constraints per domain
    int block = 256;
    int grid = (n + block - 1) / block;
    
    const char* domain_names[] = {"Flight Controls", "Thermal Management", "Power Systems", "Navigation"};
    int num_domains = 4;
    
    // Allocate per-domain buffers
    uchar8* d_bounds[4];
    int* d_values[4], *d_results[4];
    cudaStream_t streams[4];
    
    for (int d = 0; d < num_domains; d++) {
        cudaMalloc(&d_bounds[d], n * sizeof(uchar8));
        cudaMalloc(&d_values[d], n * sizeof(int));
        cudaMalloc(&d_results[d], n * sizeof(int));
        cudaStreamCreate(&streams[d]);
        
        // Fill bounds with domain-specific patterns
        uchar8 *h_b = new uchar8[n];
        for (int i = 0; i < n; i++) {
            unsigned char base = 50 + d * 50;
            h_b[i] = {(unsigned char)(base + (i*7)%100), (unsigned char)(base + (i*11)%100),
                      (unsigned char)(base + (i*13)%100), (unsigned char)(base + (i*17)%100),
                      (unsigned char)(base + (i*19)%100), (unsigned char)(base + (i*23)%100),
                      (unsigned char)(base + (i*29)%100), (unsigned char)(base + (i*31)%100)};
        }
        cudaMemcpy(d_bounds[d], h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
        delete[] h_b;
        
        int *h_v = new int[n];
        for (int i = 0; i < n; i++) h_v[i] = (i * 7 + d * 13) % 250;
        cudaMemcpy(d_values[d], h_v, n * sizeof(int), cudaMemcpyHostToDevice);
        delete[] h_v;
    }
    
    int iters = 100;
    
    // Test 1: All domains on default stream (sequential)
    printf("--- Sequential (default stream) ---\n");
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        for (int d = 0; d < num_domains; d++) {
            int8_check8<<<grid, block>>>(d_bounds[d], d_values[d], d_results[d], n);
        }
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_seq;
    cudaEventElapsedTime(&ms_seq, start, stop);
    
    double total_constraints = (double)n * num_domains * 8 * iters;
    printf("  %.2f ms total, %.3f ms/iter, %.0f constr/s\n",
           ms_seq, ms_seq/iters, total_constraints / (ms_seq/1000.0));
    
    // Test 2: Each domain on separate stream (concurrent)
    printf("--- Concurrent (4 streams) ---\n");
    
    // Warmup
    for (int d = 0; d < num_domains; d++)
        int8_check8<<<grid, block, 0, streams[d]>>>(d_bounds[d], d_values[d], d_results[d], n);
    for (int d = 0; d < num_domains; d++) cudaStreamSynchronize(streams[d]);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        for (int d = 0; d < num_domains; d++) {
            int8_check8<<<grid, block, 0, streams[d]>>>(d_bounds[d], d_values[d], d_results[d], n);
        }
    }
    for (int d = 0; d < num_domains; d++) cudaStreamSynchronize(streams[d]);
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_conc;
    cudaEventElapsedTime(&ms_conc, start, stop);
    
    printf("  %.2f ms total, %.3f ms/iter, %.0f constr/s\n",
           ms_conc, ms_conc/iters, total_constraints / (ms_conc/1000.0));
    
    printf("\n=== Results ===\n");
    printf("Sequential: %.3f ms/iter (%.0f constr/s)\n", ms_seq/iters, total_constraints/(ms_seq/1000.0));
    printf("Concurrent: %.3f ms/iter (%.0f constr/s)\n", ms_conc/iters, total_constraints/(ms_conc/1000.0));
    printf("Speedup: %.2fx\n", ms_seq/ms_conc);
    
    // Verify each domain independently
    printf("\n=== Verification ===\n");
    for (int d = 0; d < num_domains; d++) {
        int8_check8<<<grid, block, 0, streams[d]>>>(d_bounds[d], d_values[d], d_results[d], n);
        cudaStreamSynchronize(streams[d]);
        
        int *h_r = new int[n];
        cudaMemcpy(h_r, d_results[d], n * sizeof(int), cudaMemcpyDeviceToHost);
        
        int pass = 0;
        for (int i = 0; i < n; i++) if (h_r[i]) pass++;
        printf("  %s: %d/%d pass (%.1f%%)\n", domain_names[d], pass, n, 100.0*pass/n);
        
        delete[] h_r;
    }
    
    // VRAM usage
    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);
    printf("\nVRAM: %zuMB used / %zuMB total\n", (total_mem-free_mem)/(1024*1024), total_mem/(1024*1024));
    
    for (int d = 0; d < num_domains; d++) {
        cudaFree(d_bounds[d]); cudaFree(d_values[d]); cudaFree(d_results[d]);
        cudaStreamDestroy(streams[d]);
    }
    
    return 0;
}
