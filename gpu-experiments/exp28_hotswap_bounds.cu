// Experiment 28: In-place Constraint Update — Hot-Swap Bounds
// Real scenario: constraint bounds change at runtime (e.g., adaptive safety margins)
// Tests: can we update bounds on GPU without stopping the monitoring loop?

#include <cstdio>
#include <cuda_runtime.h>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

__global__ void int8_check8_masked(const uchar8* bounds, const int* values, 
                                    unsigned char* fail_masks, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
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

int main() {
    printf("=== Hot-Swap Constraint Bounds Update ===\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    int frames = 600;
    int update_every = 60; // update bounds every 60 frames
    
    uchar8 *d_bounds;
    int *d_values;
    unsigned char *d_masks;
    cudaMalloc(&d_bounds, n * sizeof(uchar8));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_masks, n * sizeof(unsigned char));
    
    uchar8 *h_b = new uchar8[n];
    int *h_v = new int[n];
    unsigned char *h_m = new unsigned char[n];
    
    // Initial bounds
    for (int i = 0; i < n; i++) {
        h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                  (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                  (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                  (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        h_v[i] = (i * 7 + 13) % 250;
    }
    cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
    
    cudaEvent_t frame_start, frame_stop, update_start, update_stop;
    cudaEventCreate(&frame_start);
    cudaEventCreate(&frame_stop);
    cudaEventCreate(&update_start);
    cudaEventCreate(&update_stop);
    
    printf("Running %d frames, updating bounds every %d frames\n\n", frames, update_every);
    printf("%-8s %-12s %-14s %-14s %-10s\n", "Frame", "Bound Upd", "Kernel", "Total", "Pass%");
    
    double total_kernel_ms = 0, total_update_ms = 0;
    int total_pass = 0, total_n = 0;
    
    for (int f = 0; f < frames; f++) {
        // Hot-swap bounds periodically
        float update_ms = 0;
        if (f % update_every == 0 && f > 0) {
            cudaEventRecord(update_start);
            // Simulate new bounds from host
            for (int i = 0; i < n; i++) {
                h_b[i] = {(unsigned char)((i*3+f*7+30)%250), (unsigned char)((i*5+f*11+40)%250),
                          (unsigned char)((i*7+f*13+50)%250), (unsigned char)((i*11+f*17+60)%250),
                          (unsigned char)((i*13+f*19+70)%250), (unsigned char)((i*17+f*23+80)%250),
                          (unsigned char)((i*19+f*29+90)%250), (unsigned char)((i*23+f*31+100)%250)};
            }
            cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
            cudaEventRecord(update_stop);
            cudaEventSynchronize(update_stop);
            cudaEventElapsedTime(&update_ms, update_start, update_stop);
            total_update_ms += update_ms;
        }
        
        // Also vary sensor values each frame
        for (int i = 0; i < n; i++) {
            h_v[i] = (i * 7 + 13 + f * 3) % 250;
        }
        cudaMemcpy(d_values, h_v, n * sizeof(int), cudaMemcpyHostToDevice);
        
        // Run constraint check
        cudaEventRecord(frame_start);
        int8_check8_masked<<<grid, block>>>(d_bounds, d_values, d_masks, n);
        cudaEventRecord(frame_stop);
        cudaEventSynchronize(frame_stop);
        
        float kernel_ms;
        cudaEventElapsedTime(&kernel_ms, frame_start, frame_stop);
        total_kernel_ms += kernel_ms;
        
        // Sample pass rate every 60 frames
        if (f % 60 == 0) {
            cudaMemcpy(h_m, d_masks, n * sizeof(unsigned char), cudaMemcpyDeviceToHost);
            int pass = 0;
            for (int i = 0; i < n; i++) if (h_m[i] == 0) pass++;
            total_pass += pass;
            total_n += n;
            
            printf("f=%4d   %8.3f ms  %10.3f ms  %10.3f ms  %5.1f%%\n",
                   f, update_ms, kernel_ms, update_ms + kernel_ms, 100.0 * pass / n);
        }
    }
    
    printf("\n=== Summary ===\n");
    printf("Total frames: %d\n", frames);
    printf("Bound updates: %d (%.1f MB each)\n", frames / update_every, n * 8 / 1e6);
    printf("Total kernel time: %.1f ms (%.3f ms/frame avg)\n", total_kernel_ms, total_kernel_ms/frames);
    printf("Total update time: %.1f ms (%.3f ms/update avg)\n", total_update_ms, total_update_ms/(frames/update_every));
    printf("Update overhead: %.1f%% of frame time\n", 100.0 * total_update_ms / (total_kernel_ms + total_update_ms));
    printf("Avg pass rate: %.1f%%\n", 100.0 * total_pass / total_n);
    
    double avg_cps = (double)n * 8 * frames / (total_kernel_ms / 1000.0);
    printf("Avg throughput: %.1fB c/s (kernel only)\n", avg_cps / 1e9);
    printf("Avg throughput: %.1fB c/s (with updates)\n", (double)n * 8 * frames / ((total_kernel_ms + total_update_ms) / 1000.0) / 1e9);
    
    delete[] h_b; delete[] h_v; delete[] h_m;
    cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_masks);
    
    return 0;
}
