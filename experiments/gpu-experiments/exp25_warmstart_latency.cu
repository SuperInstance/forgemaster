// Experiment 25: Warm-start vs cold-start latency
// How many iterations until GPU reaches peak throughput?

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
    printf("=== Warm-Start vs Cold-Start Latency ===\n\n");
    
    int n = 1000000;
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
    
    // Cold start — first 100 iterations with individual timing
    printf("Cold-start ramp (first 100 iterations, 1M sensors, 8 constraints):\n");
    printf("%-6s %-12s %-15s\n", "Iter", "Time (us)", "Constr/s");
    
    double peak = 0;
    int peak_iter = 0;
    int iter_95 = -1;
    
    for (int i = 0; i < 100; i++) {
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        cudaEventRecord(start);
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        
        float us;
        cudaEventElapsedTime(&us, start, stop);
        us *= 1000; // ms -> us
        
        double cps = (double)n * 8 / (us / 1e6);
        
        if (i < 10 || i % 10 == 0 || i == 99) {
            printf("%-6d %10.1f   %15.0f%s\n", i, us, cps, 
                   (cps > peak && i > 0) ? " ← new peak" : "");
        }
        
        if (cps > peak) { peak = cps; peak_iter = i; }
        if (iter_95 < 0 && cps >= peak * 0.95 && peak > 0) { iter_95 = i; }
        
        cudaEventDestroy(start);
        cudaEventDestroy(stop);
    }
    
    // Sustained benchmark (1000 iterations)
    printf("\nSustained (1000 iterations):\n");
    cudaEvent_t s_start, s_stop;
    cudaEventCreate(&s_start);
    cudaEventCreate(&s_stop);
    cudaEventRecord(s_start);
    for (int i = 0; i < 1000; i++)
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
    cudaEventRecord(s_stop);
    cudaEventSynchronize(s_stop);
    float sustained_ms;
    cudaEventElapsedTime(&sustained_ms, s_start, s_stop);
    double sustained_cps = (double)n * 8 * 1000 / (sustained_ms / 1000.0);
    printf("  Avg: %.1fB c/s (%.3f ms/iter)\n", sustained_cps/1e9, sustained_ms/1000);
    
    printf("\n=== Summary ===\n");
    printf("Peak throughput: %.1fB c/s at iteration %d\n", peak/1e9, peak_iter);
    printf("95%% of peak reached at iteration: %d\n", iter_95 >= 0 ? iter_95 : -1);
    printf("Sustained throughput: %.1fB c/s\n", sustained_cps/1e9);
    printf("Cold-start overhead: %.1fx slower than peak (iter 0 vs peak)\n", peak / ((double)n * 8 / 0.001));
    
    delete[] h_b; delete[] h_v;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    
    return 0;
}
