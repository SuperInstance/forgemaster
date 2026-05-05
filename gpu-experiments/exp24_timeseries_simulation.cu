// Experiment 24: Constraint satisfaction rate tracking — time-series simulation
// Simulates 60 seconds of sensor data, tracking pass/fail rate over time
// Tests: can GPU maintain throughput with changing input data?

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

__global__ void int8_check8(const uchar8* bounds, const int* values, int* results, int n) {
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
    printf("=== Time-Series Constraint Monitoring (60s simulation) ===\n\n");
    
    int n = 1000000; // 1M sensors per frame
    int block = 256;
    int grid = (n + block - 1) / block;
    int total_frames = 600; // 60 seconds at 10 Hz
    int warmup_frames = 10;
    
    uchar8 *d_bounds;
    int *d_values, *d_results;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    
    // Fixed bounds
    uchar8 *h_b = new uchar8[n];
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    
    int *h_v = new int[n];
    int *h_r = new int[n];
    
    cudaEvent_t frame_start, frame_stop;
    cudaEventCreate(&frame_start);
    cudaEventCreate(&frame_stop);
    
    printf("Running %d frames (%d sensors, 8 constraints each)...\n\n", total_frames, n);
    printf("%-8s %-10s %-12s %-12s %-10s\n", "Frame", "Pass%", "Frame ms", "Constr/s", "Status");
    
    double total_time_ms = 0;
    int total_pass = 0, total_checks = 0;
    int min_pass = n, max_pass = 0;
    double min_throughput = 1e18, max_throughput = 0;
    
    for (int f = 0; f < total_frames + warmup_frames; f++) {
        // Simulate changing sensor values (drift over time)
        for (int i = 0; i < n; i++) {
            // Base value + drift + noise
            int base = (i * 7 + 13) % 200;
            int drift = (f * 3) % 50;
            int noise = ((i * f * 7 + 37) % 10) - 5;
            h_v[i] = (base + drift + noise) % 250;
        }
        cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
        
        cudaEventRecord(frame_start);
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaEventRecord(frame_stop);
        cudaEventSynchronize(frame_stop);
        
        float frame_ms;
        cudaEventElapsedTime(&frame_ms, frame_start, frame_stop);
        
        if (f < warmup_frames) continue; // Skip warmup frames
        
        cudaMemcpy(h_r, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
        
        int frame_pass = 0;
        for (int i = 0; i < n; i++) if (h_r[i]) frame_pass++;
        
        total_time_ms += frame_ms;
        total_pass += frame_pass;
        total_checks += n;
        
        if (frame_pass < min_pass) min_pass = frame_pass;
        if (frame_pass > max_pass) max_pass = frame_pass;
        
        double throughput = (double)n * 8 / (frame_ms / 1000.0);
        if (throughput < min_throughput) min_throughput = throughput;
        if (throughput > max_throughput) max_throughput = throughput;
        
        // Print every 60th frame (every 6 simulated seconds)
        if ((f - warmup_frames) % 60 == 0) {
            printf("t=%3ds   %8.1f%%   %8.3f ms   %11.0f   %s\n",
                   (f - warmup_frames) / 10,
                   100.0 * frame_pass / n,
                   frame_ms,
                   throughput,
                   (100.0 * frame_pass / n > 50.0) ? "✓ HEALTHY" : "⚠ DEGRADED");
        }
    }
    
    printf("\n=== 60-Second Summary ===\n");
    printf("Total frames: %d (%d sensors, 8 constraints each)\n", total_frames, n);
    printf("Total constraints checked: %d (%.3e)\n", total_checks * 8, (double)total_checks * 8);
    printf("Total time: %.3f seconds\n", total_time_ms / 1000.0);
    printf("Avg throughput: %.0f constr/s (%.1fB c/s)\n", (double)total_checks * 8 / (total_time_ms / 1000.0), (double)total_checks * 8 / (total_time_ms / 1000.0) / 1e9);
    printf("Pass rate: %.1f%% (min %.1f%%, max %.1f%%)\n",
           100.0 * total_pass / total_checks,
           100.0 * min_pass / n,
           100.0 * max_pass / n);
    printf("Throughput range: %.0f - %.0f c/s\n", min_throughput, max_throughput);
    printf("Frame time range: %.3f - %.3f ms\n", 1000.0 / max_throughput * n * 8, 1000.0 / min_throughput * n * 8);
    
    delete[] h_b; delete[] h_v; delete[] h_r;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    
    return 0;
}
