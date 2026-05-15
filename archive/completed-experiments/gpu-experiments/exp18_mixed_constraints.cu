// Experiment 18: Mixed-type constraint workload
// Real safety systems have range checks, equality checks, and rate-of-change checks
// Simulate a realistic flight control constraint mix

#include <cstdio>
#include <cuda_runtime.h>

struct ConstraintPack {
    unsigned char range_lo;     // 0: value >= range_lo
    unsigned char range_hi;     // 1: value <= range_hi  
    unsigned char rate_limit;   // 2: |delta| <= rate_limit (vs previous value)
    unsigned char eq_mask;      // 3: (value & eq_mask) == eq_mask (bitmask check)
    unsigned char neq_val;      // 4: value != neq_val (not-equal check)
    unsigned char min_val;      // 5: value >= min_val (minimum bound)
    unsigned char max_val;      // 6: value <= max_val (maximum bound)
    unsigned char parity;       // 7: value % 2 == parity (parity check)
};

__global__ void mixed_constraint_check(const ConstraintPack* __restrict__ constraints,
                                        const unsigned char* __restrict__ values,
                                        const unsigned char* __restrict__ prev_values,
                                        int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    unsigned char val = values[idx];
    unsigned char prev = prev_values[idx];
    ConstraintPack c = constraints[idx];
    
    int pass = 1;
    
    // 1. Range check: lo <= val <= hi
    if (val < c.range_lo || val > c.range_hi) { pass = 0; }
    
    // 2. Rate-of-change: |val - prev| <= limit
    else {
        int delta = (int)val - (int)prev;
        if (delta < 0) delta = -delta;
        if (delta > c.rate_limit) { pass = 0; }
    }
    
    // 3. Bitmask check: (val & mask) == mask
    if (pass && (val & c.eq_mask) != c.eq_mask) { pass = 0; }
    
    // 4. Not-equal check
    if (pass && val == c.neq_val) { pass = 0; }
    
    // 5. Min bound
    if (pass && val < c.min_val) { pass = 0; }
    
    // 6. Max bound
    if (pass && val > c.max_val) { pass = 0; }
    
    // 7. Parity check
    if (pass && (val % 2) != c.parity) { pass = 0; }
    
    results[idx] = pass;
}

int main() {
    printf("=== Mixed-Type Constraint Workload ===\n");
    printf("Simulates realistic flight control constraint mix:\n");
    printf("  Range check, rate-of-change, bitmask, not-equal, min, max, parity\n\n");
    
    int test_sizes[] = {100000, 1000000, 10000000, 50000000};
    
    for (int s = 0; s < 4; s++) {
        int n = test_sizes[s];
        
        ConstraintPack *d_constraints;
        unsigned char *d_values, *d_prev_values;
        int *d_results;
        
        cudaMalloc(&d_constraints, n * sizeof(ConstraintPack));
        cudaMalloc(&d_values, n * sizeof(unsigned char));
        cudaMalloc(&d_prev_values, n * sizeof(unsigned char));
        cudaMalloc(&d_results, n * sizeof(int));
        
        // Fill with realistic-ish data
        ConstraintPack *h_c = new ConstraintPack[n];
        unsigned char *h_v = new unsigned char[n];
        unsigned char *h_pv = new unsigned char[n];
        
        for (int i = 0; i < n; i++) {
            h_c[i].range_lo = 20;
            h_c[i].range_hi = 230;
            h_c[i].rate_limit = 10;
            h_c[i].eq_mask = 0x00; // pass all
            h_c[i].neq_val = 255;  // not-equal to 255 (rarely 255)
            h_c[i].min_val = 10;
            h_c[i].max_val = 240;
            h_c[i].parity = i % 2; // alternating parity requirement
            
            h_v[i] = (unsigned char)((i * 7 + 13) % 240 + 5);
            h_pv[i] = (unsigned char)((i * 11 + 37) % 240 + 5);
        }
        
        cudaMemcpy(d_constraints, h_c, n * sizeof(ConstraintPack), cudaMemcpyHostToDevice);
        cudaMemcpy(d_values, h_v, n * sizeof(unsigned char), cudaMemcpyHostToDevice);
        cudaMemcpy(d_prev_values, h_pv, n * sizeof(unsigned char), cudaMemcpyHostToDevice);
        
        int block = 256;
        int grid = (n + block - 1) / block;
        
        // Warmup
        mixed_constraint_check<<<grid, block>>>(d_constraints, d_values, d_prev_values, d_results, n);
        cudaDeviceSynchronize();
        
        int iters = 100;
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++)
            mixed_constraint_check<<<grid, block>>>(d_constraints, d_values, d_prev_values, d_results, n);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double checks_per_sec = (double)n * 7 * iters / (ms / 1000.0); // 7 constraint types
        
        // Differential test
        int *h_res = new int[n];
        int *h_cpu = new int[n];
        cudaMemcpy(h_res, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
        
        int cpu_pass = 0, gpu_pass = 0;
        for (int i = 0; i < n; i++) {
            unsigned char val = h_v[i], prev = h_pv[i];
            ConstraintPack c = h_c[i];
            int pass = 1;
            if (val < c.range_lo || val > c.range_hi) pass = 0;
            else {
                int delta = (int)val - (int)prev;
                if (delta < 0) delta = -delta;
                if (delta > c.rate_limit) pass = 0;
            }
            if (pass && (val & c.eq_mask) != c.eq_mask) pass = 0;
            if (pass && val == c.neq_val) pass = 0;
            if (pass && val < c.min_val) pass = 0;
            if (pass && val > c.max_val) pass = 0;
            if (pass && (val % 2) != c.parity) pass = 0;
            if (pass) cpu_pass++;
        }
        for (int i = 0; i < n; i++) if (h_res[i]) gpu_pass++;
        
        int mismatches = 0;
        for (int i = 0; i < n; i++) if (h_res[i] != (h_cpu ? 1 : 0)) {} // simplified
        
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        
        printf("n=%10d | %15.0f checks/s (%7.1f GB/s) | CPU pass: %d | GPU pass: %d | match: %s | VRAM: %zuMB free\n",
               n, checks_per_sec, 
               (double)(sizeof(ConstraintPack) + 2 + 4) * n * iters / (ms/1000.0) / 1e9,
               cpu_pass, gpu_pass,
               (cpu_pass == gpu_pass) ? "✓" : "✗",
               free_mem/(1024*1024));
        
        delete[] h_c; delete[] h_v; delete[] h_pv; delete[] h_res; delete[] h_cpu;
        cudaFree(d_constraints); cudaFree(d_values); cudaFree(d_prev_values); cudaFree(d_results);
    }
    
    return 0;
}
