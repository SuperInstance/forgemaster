// Experiment 22: Real power measurement using nvidia-smi polling
// Samples GPU power every 100ms during sustained workload
// Gives actual Safe-TOPS/W with real wattage

#include <cstdio>
#include <cuda_runtime.h>
#include <unistd.h>
#include <chrono>
#include <thread>

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
    printf("=== Real Power Measurement via nvidia-smi ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    
    uchar8 *d_bounds;
    int *d_values, *d_results;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    
    uchar8 *h_b = new uchar8[n];
    int *h_v = new int[n];
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        h_v[i] = (i * 7 + 13) % 250;
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
    
    // Get idle power first
    printf("Sampling idle power (3 seconds)...\n");
    system("/usr/lib/wsl/lib/nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits > /tmp/gpu_power_idle.csv 2>/dev/null &");
    sleep(3);
    system("cat /tmp/gpu_power_idle.csv 2>/dev/null | head -1");
    
    // Warmup
    printf("Warming up...\n");
    for (int i = 0; i < 100; i++)
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaDeviceSynchronize();
    
    // Start power sampling in background during workload
    printf("Running sustained workload + power sampling (10 seconds)...\n");
    system("for i in $(seq 1 100); do /usr/lib/wsl/lib/nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null; sleep 0.1; done > /tmp/gpu_power_load.csv &");
    
    auto start = std::chrono::high_resolution_clock::now();
    int total_iters = 0;
    while (true) {
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        total_iters++;
        auto elapsed = std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - start).count();
        if (elapsed > 10.0) break;
    }
    cudaDeviceSynchronize();
    auto end = std::chrono::high_resolution_clock::now();
    double total_sec = std::chrono::duration<double>(end - start).count();
    
    sleep(1); // Let power sampling finish
    
    double total_checks = (double)n * 8 * total_iters;
    double checks_per_sec = total_checks / total_sec;
    
    printf("\n=== Results ===\n");
    printf("Iterations: %d in %.3f seconds\n", total_iters, total_sec);
    printf("Throughput: %.3e constraints/sec (%.1fB c/s)\n", checks_per_sec, checks_per_sec/1e9);
    
    // Read power samples
    printf("\n=== Power Readings ===\n");
    FILE *fp = popen("cat /tmp/gpu_power_load.csv 2>/dev/null | grep -v '^$' | wc -l", "r");
    int samples = 0;
    if (fp) { fscanf(fp, "%d", &samples); pclose(fp); }
    
    fp = popen("awk '{s+=$1; n++} END {if(n>0) print s/n; else print 0}' /tmp/gpu_power_load.csv 2>/dev/null", "r");
    double avg_power = 0;
    if (fp) { fscanf(fp, "%lf", &avg_power); pclose(fp); }
    
    fp = popen("sort -n /tmp/gpu_power_load.csv 2>/dev/null | head -1", "r");
    double min_power = 0;
    if (fp) { fscanf(fp, "%lf", &min_power); pclose(fp); }
    
    fp = popen("sort -n /tmp/gpu_power_load.csv 2>/dev/null | tail -1", "r");
    double max_power = 0;
    if (fp) { fscanf(fp, "%lf", &max_power); pclose(fp); }
    
    printf("Power samples: %d\n", samples);
    printf("Avg GPU power: %.1f W\n", avg_power);
    printf("Min GPU power: %.1f W\n", min_power);
    printf("Max GPU power: %.1f W\n", max_power);
    
    if (avg_power > 0) {
        double safe_tops_per_w = (checks_per_sec / 1e12) / avg_power;
        printf("\n=== Safe-TOPS/W ===\n");
        printf("%.3f Safe-TOPS/W (%.1fB verified checks/s at %.1fW)\n", 
               safe_tops_per_w, checks_per_sec/1e9, avg_power);
    }
    
    delete[] h_b; delete[] h_v;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    
    return 0;
}
