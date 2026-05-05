// Experiment 31: Saturation Semantics — Fix for INT8 Boundary Vulnerability
// The swarm found that values > 255 wrap to 0, bypassing safety constraints
// This tests: what is the performance cost of saturation (clamping to 255)?
// Key question: does __saturate_p or manual clamping add overhead?

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

// Original: no protection (vulnerable to wraparound)
__global__ void int8_check8_unsafe(const uchar8* bounds, const int* values, 
                                    unsigned char* fail_masks, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];  // Could be > 255!
    uchar8 b = bounds[idx];
    unsigned char mask = 0;
    if (val >= b.a) mask |= 0x01;
    if (val >= b.b) mask |= 0x02;
    if (val >= b.c) mask |= 0x04;
    if (val >= b.d) mask |= 0x08;
    if (val >= b.e) mask |= 0x10;
    if (val >= b.f) mask |= 0x20;
    if (val >= b.g) mask |= 0x40;
    if (val >= b.h) mask |= 0x80;
    fail_masks[idx] = mask;
}

// Safe: saturate input to 255 (clamp)
__global__ void int8_check8_saturate(const uchar8* bounds, const int* values, 
                                      unsigned char* fail_masks, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    // Saturate: clamp to [0, 255]
    unsigned char val_sat = (unsigned char)(val > 255 ? 255 : (val < 0 ? 0 : val));
    uchar8 b = bounds[idx];
    unsigned char mask = 0;
    if (val_sat >= b.a) mask |= 0x01;
    if (val_sat >= b.b) mask |= 0x02;
    if (val_sat >= b.c) mask |= 0x04;
    if (val_sat >= b.d) mask |= 0x08;
    if (val_sat >= b.e) mask |= 0x10;
    if (val_sat >= b.f) mask |= 0x20;
    if (val_sat >= b.g) mask |= 0x40;
    if (val_sat >= b.h) mask |= 0x80;
    fail_masks[idx] = mask;
}

// Safe + overflow flag: set bit 7 on overflow
__global__ void int8_check8_saturate_flag(const uchar8* bounds, const int* values, 
                                            unsigned char* fail_masks, int* overflow_count, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    bool overflow = (val > 255 || val < 0);
    unsigned char val_sat = (unsigned char)(val > 255 ? 255 : (val < 0 ? 0 : val));
    uchar8 b = bounds[idx];
    unsigned char mask = 0;
    if (val_sat >= b.a) mask |= 0x01;
    if (val_sat >= b.b) mask |= 0x02;
    if (val_sat >= b.c) mask |= 0x04;
    if (val_sat >= b.d) mask |= 0x08;
    if (val_sat >= b.e) mask |= 0x10;
    if (val_sat >= b.f) mask |= 0x20;
    if (val_sat >= b.g) mask |= 0x40;
    if (overflow) mask |= 0x80;  // Bit 7 = overflow flag
    fail_masks[idx] = mask;
    if (overflow) atomicAdd(overflow_count, 1);
}

int main() {
    printf("=== Saturation Semantics: Fixing the INT8 Boundary Vulnerability ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 100;
    
    uchar8 *d_bounds;
    int *d_values;
    unsigned char *d_masks_unsafe, *d_masks_saturate, *d_masks_flag;
    int *d_overflow_count;
    
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_masks_unsafe, n * sizeof(unsigned char));
    cudaMalloc(&d_masks_saturate, n * sizeof(unsigned char));
    cudaMalloc(&d_masks_flag, n * sizeof(unsigned char));
    cudaMalloc(&d_overflow_count, sizeof(int));
    
    uchar8 *h_b = new uchar8[n];
    int *h_v = new int[n];
    unsigned char *h_m_unsafe = new unsigned char[n];
    unsigned char *h_m_sat = new unsigned char[n];
    unsigned char *h_m_flag = new unsigned char[n];
    
    // Create test data: 90% normal (0-249), 5% at boundary (250-255), 5% overflow (256-300)
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        
        if (i % 20 == 0) {
            h_v[i] = 256 + (i % 45);  // Overflow: 256-300
        } else if (i % 20 < 2) {
            h_v[i] = 250 + (i % 6);  // Boundary: 250-255
        } else {
            h_v[i] = (i * 7 + 13) % 250;  // Normal: 0-249
        }
    }
    
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
    
    // Warmup
    int8_check8_unsafe<<<grid, block>>>(d_bounds, d_values, d_masks_unsafe, n);
    int8_check8_saturate<<<grid, block>>>(d_bounds, d_values, d_masks_saturate, n);
    cudaMemset(d_overflow_count, 0, sizeof(int));
    int8_check8_saturate_flag<<<grid, block>>>(d_bounds, d_values, d_masks_flag, d_overflow_count, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Benchmark unsafe
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        int8_check8_unsafe<<<grid, block>>>(d_bounds, d_values, d_masks_unsafe, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_unsafe;
    cudaEventElapsedTime(&ms_unsafe, start, stop);
    
    // Benchmark saturate
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        int8_check8_saturate<<<grid, block>>>(d_bounds, d_values, d_masks_saturate, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_saturate;
    cudaEventElapsedTime(&ms_saturate, start, stop);
    
    // Benchmark saturate + flag
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemset(d_overflow_count, 0, sizeof(int));
        int8_check8_saturate_flag<<<grid, block>>>(d_bounds, d_values, d_masks_flag, d_overflow_count, n);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_flag;
    cudaEventElapsedTime(&ms_flag, start, stop);
    
    printf("10M sensors (90%% normal, 5%% boundary, 5%% overflow), 100 iters:\n\n");
    printf("%-25s %10s %15s %10s\n", "Method", "ms/iter", "c/s", "Overhead");
    printf("%-25s %10.3f %15.0f %10s\n", "Unsafe (no protection)", ms_unsafe/iters, 
           (double)n*8*iters/(ms_unsafe/1000), "baseline");
    printf("%-25s %10.3f %15.0f %10.2fx\n", "Saturate (clamp to 255)", ms_saturate/iters,
           (double)n*8*iters/(ms_saturate/1000), ms_unsafe/ms_saturate);
    printf("%-25s %10.3f %15.0f %10.2fx\n", "Saturate + overflow flag", ms_flag/iters,
           (double)n*8*iters/(ms_flag/1000), ms_unsafe/ms_flag);
    
    // Correctness check
    int8_check8_unsafe<<<grid, block>>>(d_bounds, d_values, d_masks_unsafe, n);
    int8_check8_saturate<<<grid, block>>>(d_bounds, d_values, d_masks_saturate, n);
    cudaMemset(d_overflow_count, 0, sizeof(int));
    int8_check8_saturate_flag<<<grid, block>>>(d_bounds, d_values, d_masks_flag, d_overflow_count, n);
    cudaDeviceSynchronize();
    
    cudaMemcpy(h_m_unsafe, d_masks_unsafe, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_m_sat, d_masks_saturate, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_m_flag, d_masks_flag, n, cudaMemcpyDeviceToHost);
    int h_overflow;
    cudaMemcpy(&h_overflow, d_overflow_count, sizeof(int), cudaMemcpyDeviceToHost);
    
    int unsafe_all_pass = 0, sat_all_pass = 0, flag_all_pass = 0;
    int overflow_bypass = 0;  // Cases where unsafe gives FALSE PASS
    
    for (int i = 0; i < n; i++) {
        if (h_m_unsafe[i] == 0) unsafe_all_pass++;
        if (h_m_sat[i] == 0) sat_all_pass++;
        // Flag version: bit 7 = overflow, bits 0-6 = constraint violations
        unsigned char flag_constraints = h_m_flag[i] & 0x7F;
        bool flag_overflow = (h_m_flag[i] & 0x80) != 0;
        if (flag_constraints == 0 && !flag_overflow) flag_all_pass++;
        
        // Detect bypass: value > 255 but unsafe says "all constraints pass"
        if (h_v[i] > 255 && h_m_unsafe[i] == 0) overflow_bypass++;
    }
    
    printf("\n=== Correctness ===\n");
    printf("Unsafe all-pass: %d / %d (%.1f%%)\n", unsafe_all_pass, n, 100.0*unsafe_all_pass/n);
    printf("Saturate all-pass: %d / %d (%.1f%%)\n", sat_all_pass, n, 100.0*sat_all_pass/n);
    printf("Flag all-pass (no overflow + no violation): %d / %d (%.1f%%)\n", flag_all_pass, n, 100.0*flag_all_pass/n);
    printf("Overflow count: %d (%.1f%%)\n", h_overflow, 100.0*h_overflow/n);
    printf("\n*** OVERFLOW BYPASS (false negatives in unsafe): %d ***\n", overflow_bypass);
    printf("This is the P1 vulnerability the swarm found!\n");
    
    delete[] h_b; delete[] h_v; delete[] h_m_unsafe; delete[] h_m_sat; delete[] h_m_flag;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_masks_unsafe);
    cudaFree(d_masks_saturate); cudaFree(d_masks_flag); cudaFree(d_overflow_count);
    
    return 0;
}
