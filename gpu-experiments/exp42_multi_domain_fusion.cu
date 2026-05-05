// Experiment 42: Multi-Domain Fusion — All Safety Domains Simultaneously
// The real production use case: monitor aviation + nuclear + automotive + space at once
// Each "sensor" belongs to a different domain with different constraint sets

#include <cstdio>
#include <cuda_runtime.h>

// Universal constraint set — 8 constraints per sensor, domain-tagged
struct DomainBounds {
    unsigned char b0, b1, b2, b3, b4, b5, b6, b7; // 8 bounds
};

__global__ void fusion_check(
    const unsigned char* flat_bounds,    // [domain][constraint]
    const int* domain_ids,               // which domain each sensor belongs to
    const unsigned char* values,
    unsigned char* masks,
    int* domain_violations,              // per-domain violation count
    int n, int nc, int n_domains
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int did = domain_ids[idx];
    int val = values[idx];
    const unsigned char* b = &flat_bounds[did * nc];
    
    unsigned char mask = 0;
    if (val >= b[0]) mask |= 0x01;
    if (val >= b[1]) mask |= 0x02;
    if (val >= b[2]) mask |= 0x04;
    if (val >= b[3]) mask |= 0x08;
    if (val >= b[4]) mask |= 0x10;
    if (val >= b[5]) mask |= 0x20;
    if (val >= b[6]) mask |= 0x40;
    if (val >= b[7]) mask |= 0x80;
    
    masks[idx] = mask;
    
    // Domain-specific violation counting
    __shared__ int smem[32]; // Max 32 domains
    int n_banks = min(n_domains, 32);
    if (threadIdx.x < n_banks) smem[threadIdx.x] = 0;
    __syncthreads();
    
    if (mask && did < n_banks)
        atomicAdd(&smem[did], 1);
    __syncthreads();
    
    if (threadIdx.x < n_banks && smem[threadIdx.x] > 0)
        atomicAdd(&domain_violations[threadIdx.x], smem[threadIdx.x]);
}

int main() {
    printf("=== Exp42: Multi-Domain Safety Fusion ===\n\n");
    
    int n = 10000000;
    int nc = 8;
    int n_domains = 5; // aviation, nuclear, automotive, space, maritime
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 200;
    
    // Create domain-specific bounds
    // [domain][8 constraints] — each domain has different safety thresholds
    unsigned char h_bounds[5][8] = {
        {100, 200,  50, 220,  80, 180, 120, 190}, // Aviation
        {130, 210, 180, 230,  30, 200,   0,  50}, // Nuclear
        {  0, 230,  20, 200,  30, 225,  40, 200}, // Automotive
        { 40, 220, 160, 240,  20, 200,   0, 180}, // Space
        { 60, 200,  40, 180,  80, 220,  50, 190}, // Maritime
    };
    const char* domain_names[] = {"Aviation", "Nuclear", "Automotive", "Space", "Maritime"};
    
    unsigned char* d_bounds;
    int* d_domain_ids;
    unsigned char* d_values, *d_masks;
    int* d_violations;
    cudaMalloc(&d_bounds, n_domains * nc);
    cudaMalloc(&d_domain_ids, n * sizeof(int));
    cudaMalloc(&d_values, n);
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_violations, n_domains * sizeof(int));
    cudaMemcpy(d_bounds, h_bounds, n_domains * nc, cudaMemcpyHostToDevice);
    
    // Assign sensors to domains (equal split)
    int* h_dids = new int[n];
    unsigned char* h_vals = new unsigned char[n];
    for (int i = 0; i < n; i++) {
        h_dids[i] = i % n_domains;
        // Generate domain-appropriate values with occasional violations
        int d = h_dids[i];
        int baseline = h_bounds[d][0] + 20;
        if (i % 2000 == 0) h_vals[i] = 250; // Violation
        else if (i % 3000 == 0) h_vals[i] = 10; // Underflow
        else h_vals[i] = baseline + (i * 7) % (h_bounds[d][1] - baseline);
    }
    cudaMemcpy(d_domain_ids, h_dids, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_vals, n, cudaMemcpyHostToDevice);
    
    // Warmup
    cudaMemset(d_violations, 0, n_domains * sizeof(int));
    fusion_check<<<grid, block>>>(d_bounds, d_domain_ids, d_values, d_masks, d_violations, n, nc, n_domains);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemsetAsync(d_violations, 0, n_domains * sizeof(int));
        fusion_check<<<grid, block>>>(d_bounds, d_domain_ids, d_values, d_masks, d_violations, n, nc, n_domains);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    
    printf("Multi-domain fusion: 5 domains × 8 constraints, 10M sensors\n");
    printf("Domains: Aviation (DO-178C), Nuclear (NRC), Automotive (ISO 26262),\n");
    printf("         Space (ECSS), Maritime (SOLAS)\n\n");
    printf("Throughput: %.1fB checks/sec\n", (double)n*nc*iters/(ms/1000)/1e9);
    printf("Latency:    %.3f ms per 10M-sensor frame\n", ms/iters);
    printf("Frame rate: %.0f Hz\n", 1000.0/(ms/iters));
    
    // Per-domain violation report
    int h_violations[5];
    cudaMemcpy(h_violations, d_violations, n_domains*sizeof(int), cudaMemcpyDeviceToHost);
    
    printf("\nPer-Domain Violations:\n");
    int total_v = 0;
    for (int d = 0; d < n_domains; d++) {
        printf("  %-12s: %d violations (%.2f%%)\n", domain_names[d], h_violations[d], 100.0*h_violations[d]/(n/n_domains));
        total_v += h_violations[d];
    }
    printf("  %-12s: %d total (%.3f%%)\n", "TOTAL", total_v, 100.0*total_v/n);
    
    // Total constraint checks per second across all domains
    printf("\n=== Multi-domain safety fusion at %.0fB c/s across 5 safety standards ===\n",
           (double)n*nc*iters/(ms/1000)/1e9);
    printf("Single GPU monitoring aviation + nuclear + automotive + space + maritime\n");
    printf("simultaneously at %.0f Hz with per-domain violation tracking.\n", 1000.0/(ms/iters));
    
    delete[] h_dids; delete[] h_vals;
    return 0;
}
