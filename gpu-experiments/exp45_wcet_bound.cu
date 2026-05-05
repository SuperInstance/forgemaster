// Experiment 45: WCET Bound Measurement — Worst-Case Execution Time
// Safety certification requires WCET, not just average/P99
// This measures the absolute worst case across 10,000 launches with varying data

#include <cstdio>
#include <cuda_runtime.h>

__global__ void check8(const unsigned char* bounds, const int* set_ids,
                        const int* values, unsigned char* masks, int n, int nc) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    const unsigned char* b = &bounds[set_ids[idx] * nc];
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
}

int main() {
    printf("=== Exp45: WCET Bound Measurement ===\n\n");
    
    int n = 1000000;
    int nc = 8, nsets = 50;
    int block = 256;
    int grid = (n + block - 1) / block;
    int N = 10000;
    
    unsigned char *d_b, *d_m; int *d_s, *d_v;
    cudaMalloc(&d_b, nsets*nc); cudaMalloc(&d_s, n*sizeof(int));
    cudaMalloc(&d_v, n*sizeof(int)); cudaMalloc(&d_m, n);
    
    unsigned char hb[400]; int* hs = new int[n]; int* hv = new int[n];
    for (int i = 0; i < 400; i++) hb[i] = 100+i%140;
    cudaMemcpy(d_b, hb, nsets*nc, cudaMemcpyHostToDevice);
    
    // Warmup
    for (int i = 0; i < n; i++) { hs[i] = i%50; hv[i] = (i*7)%250; }
    cudaMemcpy(d_s, hs, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_v, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    check8<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
    cudaDeviceSynchronize();
    
    // Test 1: WCET with constant data
    float* times_const = new float[N];
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    for (int i = 0; i < N; i++) {
        cudaEventRecord(start);
        check8<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        cudaEventElapsedTime(&times_const[i], start, stop);
    }
    
    // Test 2: WCET with varying data (worst case: all values at boundary)
    float* times_boundary = new float[N];
    for (int i = 0; i < n; i++) hv[i] = 99; // All at boundary (just below bounds)
    cudaMemcpy(d_v, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    
    for (int i = 0; i < N; i++) {
        cudaEventRecord(start);
        check8<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        cudaEventElapsedTime(&times_boundary[i], start, stop);
    }
    
    // Test 3: WCET with all violations
    float* times_violate = new float[N];
    for (int i = 0; i < n; i++) hv[i] = 255; // All violate
    cudaMemcpy(d_v, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    
    for (int i = 0; i < N; i++) {
        cudaEventRecord(start);
        check8<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        cudaEventElapsedTime(&times_violate[i], start, stop);
    }
    
    // Find WCET for each
    auto find_wcet = [](float* t, int n) -> float {
        float wcet = t[0];
        for (int i = 1; i < n; i++) if (t[i] > wcet) wcet = t[i];
        return wcet;
    };
    
    float wcet_const = find_wcet(times_const, N);
    float wcet_boundary = find_wcet(times_boundary, N);
    float wcet_violate = find_wcet(times_violate, N);
    float wcet_overall = wcet_const;
    if (wcet_boundary > wcet_overall) wcet_overall = wcet_boundary;
    if (wcet_violate > wcet_overall) wcet_overall = wcet_violate;
    
    printf("1M sensors, 8 constraints, 10,000 launches per scenario:\n\n");
    printf("%-25s %10s %10s %10s\n", "Scenario", "WCET (ms)", "Min (ms)", "Hz");
    printf("%-25s %10.4f %10.4f %10.0f\n", "Normal data", wcet_const, 
           times_const[0] < wcet_const ? times_const[0] : wcet_const, 1000.0/wcet_const);
    printf("%-25s %10.4f %10.4f %10.0f\n", "All at boundary", wcet_boundary,
           times_boundary[0], 1000.0/wcet_boundary);
    printf("%-25s %10.4f %10.4f %10.0f\n", "All violations", wcet_violate,
           times_violate[0], 1000.0/wcet_violate);
    printf("%-25s %10.4f\n", "OVERALL WCET", wcet_overall);
    
    printf("\n=== WCET Safety Assessment ===\n");
    printf("WCET: %.4f ms\n", wcet_overall);
    printf("WCET frame rate: %.0f Hz\n", 1000.0/wcet_overall);
    printf("1KHz real-time: %s (WCET=%.3fms, budget=1.0ms)\n",
           wcet_overall < 1.0 ? "PASS ✓" : "FAIL ✗", wcet_overall);
    printf("100Hz control:  %s (WCET=%.3fms, budget=10ms)\n",
           wcet_overall < 10.0 ? "PASS ✓" : "FAIL ✗", wcet_overall);
    printf("WCET headroom:  %.1fx (vs 1ms budget)\n", 1.0 / wcet_overall);
    
    delete[] hs; delete[] hv;
    delete[] times_const; delete[] times_boundary; delete[] times_violate;
    return 0;
}
