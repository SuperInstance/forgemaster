// Experiment 16: Edge case stress tests — adversarial inputs
// Test: all-pass, all-fail, alternating, single-pass, single-fail
// Ensures no shortcuts in early-exit logic

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
    printf("=== Edge Case Stress Tests ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    
    uchar8 *d_bounds;
    int *d_values, *d_results;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    
    // Edge cases
    struct TestCase {
        const char* name;
        int bound_base;
        int value_base;
    };
    
    // All values 0, bounds 255 -> ALL PASS
    // All values 255, bounds 0 -> ALL FAIL
    // Values = bounds -> edge boundary (val >= bound -> FAIL since >=)
    // Every other element fails
    
    TestCase cases[] = {
        {"All PASS (val=10, bound=200)", 200, 10},
        {"All FAIL (val=200, bound=10)", 10, 200},
        {"Boundary (val=100, bound=100)", 100, 100},  // >= means FAIL
        {"Near boundary (val=99, bound=100)", 100, 99},  // PASS
        {"Near boundary (val=100, bound=99)", 99, 100},  // FAIL
        {"Alternating", -1, -1},  // Special case
    };
    
    for (int c = 0; c < 6; c++) {
        int *h_v = new int[n];
        uchar8 *h_b = new uchar8[n];
        
        if (c == 5) {
            // Alternating: even indices pass, odd fail
            for (int i = 0; i < n; i++) {
                h_v[i] = (i % 2 == 0) ? 10 : 200;
                unsigned char bval = (i % 2 == 0) ? 200 : 10;
                h_b[i] = {bval, bval, bval, bval, bval, bval, bval, bval};
            }
        } else {
            for (int i = 0; i < n; i++) h_v[i] = cases[c].value_base;
            for (int i = 0; i < n; i++) {
                unsigned char bv = (unsigned char)cases[c].bound_base;
                h_b[i] = {bv, bv, bv, bv, bv, bv, bv, bv};
            }
        }
        
        cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
        cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
        
        // Run kernel
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaDeviceSynchronize();
        
        // Count results
        int *h_r = new int[n];
        cudaMemcpy(h_r, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
        
        int pass_count = 0;
        for (int i = 0; i < n; i++) if (h_r[i]) pass_count++;
        
        // Benchmark
        int iters = 50;
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++)
            int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double constr_s = (double)n * 8 * iters / (ms / 1000.0);
        
        // CPU reference for first 1000
        int cpu_pass = 0;
        for (int i = 0; i < n; i++) {
            int val = h_v[i];
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
        
        const char* ok = (pass_count == cpu_pass) ? "✓" : "✗ MISMATCH";
        printf("%-40s | pass: %d/%d (expected %d) %s | %.0f c/s\n",
               cases[c].name, pass_count, n, cpu_pass, ok, constr_s);
        
        delete[] h_v; delete[] h_b; delete[] h_r;
    }
    
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    return 0;
}
