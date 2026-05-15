// Experiment 43: Error Propagation — How Fast Can We Detect Cascading Failures?
// Simulates a scenario where one sensor failure cascades to related sensors
// Tests: can we detect correlated violations across domains in a single kernel pass?

#include <cstdio>
#include <cuda_runtime.h>

__global__ void cascade_check(
    const unsigned char* bounds,
    const int* sensor_groups,  // sensors in same group share fate
    const unsigned char* values,
    unsigned char* masks,
    int* group_violations,     // per-group violation count
    int n, int nc, int n_groups
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int gid = sensor_groups[idx];
    int val = values[idx];
    const unsigned char* b = &bounds[gid * nc];
    
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
    
    // Track group-level violations for cascade detection
    __shared__ int smem[64];
    if (threadIdx.x < 64 && threadIdx.x < n_groups) smem[threadIdx.x] = 0;
    __syncthreads();
    
    if (mask && gid < 64)
        atomicAdd(&smem[gid], 1);
    __syncthreads();
    
    if (threadIdx.x < 64 && threadIdx.x < n_groups && smem[threadIdx.x] > 0)
        atomicAdd(&group_violations[threadIdx.x], smem[threadIdx.x]);
}

int main() {
    printf("=== Exp43: Cascade Failure Detection ===\n\n");
    
    int n = 10000000;
    int nc = 8;
    int n_groups = 50; // 50 subsystems
    int sensors_per_group = n / n_groups;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 200;
    
    unsigned char* d_bounds;
    int* d_groups;
    unsigned char* d_values, *d_masks;
    int* d_group_violations;
    cudaMalloc(&d_bounds, n_groups * nc);
    cudaMalloc(&d_groups, n * sizeof(int));
    cudaMalloc(&d_values, n);
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_group_violations, n_groups * sizeof(int));
    
    // Init bounds
    unsigned char* hb = new unsigned char[n_groups * nc];
    for (int g = 0; g < n_groups; g++)
        for (int j = 0; j < nc; j++)
            hb[g*nc+j] = 100 + (g*3+j*7)%140;
    cudaMemcpy(d_bounds, hb, n_groups*nc, cudaMemcpyHostToDevice);
    
    // Assign sensors to groups
    int* hg = new int[n];
    unsigned char* hv = new unsigned char[n];
    for (int i = 0; i < n; i++) {
        hg[i] = i % n_groups;
        hv[i] = (i * 7 + 13) % 200;
    }
    
    // Inject cascade: group 5 fails at iteration 50% — all sensors in group get bad values
    int cascade_start = n / 2;
    int cascade_group = 5;
    for (int i = cascade_start; i < cascade_start + sensors_per_group; i++) {
        if (hg[i] == cascade_group) hv[i] = 255; // Max violation
    }
    
    cudaMemcpy(d_groups, hg, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, hv, n, cudaMemcpyHostToDevice);
    
    // Warmup
    cudaMemset(d_group_violations, 0, n_groups * sizeof(int));
    cascade_check<<<grid, block>>>(d_bounds, d_groups, d_values, d_masks, d_group_violations, n, nc, n_groups);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemsetAsync(d_group_violations, 0, n_groups * sizeof(int));
        cascade_check<<<grid, block>>>(d_bounds, d_groups, d_values, d_masks, d_group_violations, n, nc, n_groups);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    
    printf("Cascade detection: 10M sensors, 50 subsystem groups, 8 constraints\n\n");
    printf("Throughput: %.1fB checks/sec\n", (double)n*nc*iters/(ms/1000)/1e9);
    printf("Latency:    %.3f ms per frame\n", ms/iters);
    printf("Frame rate: %.0f Hz\n\n", 1000.0/(ms/iters));
    
    // Analyze cascade
    cudaMemset(d_group_violations, 0, n_groups * sizeof(int));
    cascade_check<<<grid, block>>>(d_bounds, d_groups, d_values, d_masks, d_group_violations, n, nc, n_groups);
    cudaDeviceSynchronize();
    
    int* h_gv = new int[n_groups];
    cudaMemcpy(h_gv, d_group_violations, n_groups*sizeof(int), cudaMemcpyDeviceToHost);
    
    printf("Per-Group Violations (cascade in group %d):\n", cascade_group);
    int total_v = 0;
    for (int g = 0; g < n_groups; g++) {
        int expected = sensors_per_group;
        float rate = 100.0 * h_gv[g] / expected;
        if (g == cascade_group || rate > 5.0) {
            printf("  Group %2d: %d violations (%.1f%%) %s\n", g, h_gv[g], rate,
                   g == cascade_group ? "← CASCADE DETECTED" : "");
        }
        total_v += h_gv[g];
    }
    
    printf("\n  Total violations: %d (%.3f%%)\n", total_v, 100.0*total_v/n);
    
    // Cascade detection metric
    float cascade_rate = 100.0 * h_gv[cascade_group] / sensors_per_group;
    float normal_avg = (float)(total_v - h_gv[cascade_group]) / (n_groups - 1) / sensors_per_group * 100;
    float signal_ratio = cascade_rate / (normal_avg > 0 ? normal_avg : 0.001);
    
    printf("\n  Cascade group rate: %.1f%%\n", cascade_rate);
    printf("  Normal group avg:   %.2f%%\n", normal_avg);
    printf("  Signal ratio:       %.0fx above normal\n", signal_ratio);
    
    printf("\n=== Cascade detection at %.0fB c/s with %.0fx signal ratio ===\n",
           (double)n*nc*iters/(ms/1000)/1e9, signal_ratio);
    
    delete[] hb; delete[] hg; delete[] hv; delete[] h_gv;
    return 0;
}
