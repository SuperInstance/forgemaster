// Experiment 44: Timing Jitter — Deterministic Latency Measurement
// For safety-critical systems, jitter matters more than average throughput
// Measures min/max/mean/stddev of individual kernel launches

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
    printf("=== Exp44: Timing Jitter — Deterministic Latency ===\n\n");
    
    int n = 1000000; // 1M sensors for per-launch timing resolution
    int nc = 8, nsets = 50;
    int block = 256;
    int grid = (n + block - 1) / block;
    int N = 1000; // 1000 individual launches
    
    unsigned char *d_b, *d_m; int *d_s, *d_v;
    cudaMalloc(&d_b, nsets*nc); cudaMalloc(&d_s, n*sizeof(int));
    cudaMalloc(&d_v, n*sizeof(int)); cudaMalloc(&d_m, n);
    
    unsigned char hb[400]; int* hs = new int[n]; int* hv = new int[n];
    for (int i = 0; i < 400; i++) hb[i] = 100+i%140;
    for (int i = 0; i < n; i++) { hs[i] = i%50; hv[i] = (i*7)%250; }
    cudaMemcpy(d_b, hb, nsets*nc, cudaMemcpyHostToDevice);
    cudaMemcpy(d_s, hs, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_v, hv, n*sizeof(int), cudaMemcpyHostToDevice);
    
    // Warmup
    check8<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
    cudaDeviceSynchronize();
    
    // Measure individual launch times
    float* times = new float[N];
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    for (int i = 0; i < N; i++) {
        cudaEventRecord(start);
        check8<<<grid,block>>>(d_b,d_s,d_v,d_m,n,nc);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        cudaEventElapsedTime(&times[i], start, stop);
    }
    
    // Stats
    float min_t = times[0], max_t = times[0], sum = 0, sum2 = 0;
    for (int i = 0; i < N; i++) {
        if (times[i] < min_t) min_t = times[i];
        if (times[i] > max_t) max_t = times[i];
        sum += times[i];
        sum2 += times[i] * times[i];
    }
    float mean = sum / N;
    float var = sum2/N - mean*mean;
    float stddev = sqrtf(var > 0 ? var : 0);
    
    // Percentiles
    // Simple sort for percentiles
    for (int i = 0; i < N-1; i++)
        for (int j = i+1; j < N; j++)
            if (times[j] < times[i]) { float t = times[i]; times[i] = times[j]; times[j] = t; }
    
    float p50 = times[N/2];
    float p90 = times[(int)(N*0.9)];
    float p95 = times[(int)(N*0.95)];
    float p99 = times[(int)(N*0.99)];
    float p999 = times[(int)(N*0.999)];
    
    printf("1M sensors, 8 constraints, %d individual launches:\n\n", N);
    printf("  Min:      %.4f ms\n", min_t);
    printf("  P50:      %.4f ms\n", p50);
    printf("  P90:      %.4f ms\n", p90);
    printf("  P95:      %.4f ms\n", p95);
    printf("  P99:      %.4f ms\n", p99);
    printf("  P99.9:    %.4f ms\n", p999);
    printf("  Max:      %.4f ms\n", max_t);
    printf("  Mean:     %.4f ms\n", mean);
    printf("  Stddev:   %.4f ms\n", stddev);
    printf("  Jitter:   %.4f ms (max-min)\n", max_t - min_t);
    printf("  CV:       %.2f%%\n", 100.0 * stddev / mean);
    
    printf("\n  Throughput at P50: %.1fB c/s\n", (double)n*nc/(p50/1000)/1e9);
    printf("  Throughput at P99: %.1fB c/s\n", (double)n*nc/(p99/1000)/1e9);
    
    // Safety assessment
    printf("\n=== Safety Timing Assessment ===\n");
    float p99_hz = 1000.0 / p99;
    printf("  P99 frame rate: %.0f Hz\n", p99_hz);
    printf("  1KHz real-time: %s (P99 = %.3f ms, budget = 1.000 ms)\n",
           p99 < 1.0 ? "PASS ✓" : "FAIL ✗", p99);
    printf("  100Hz control:  %s (P99 = %.3f ms, budget = 10.00 ms)\n",
           p99 < 10.0 ? "PASS ✓" : "FAIL ✗", p99);
    printf("  10Hz monitoring: %s (P99 = %.3f ms, budget = 100.0 ms)\n",
           p99 < 100.0 ? "PASS ✓" : "FAIL ✗", p99);
    
    delete[] hs; delete[] hv; delete[] times;
    return 0;
}
