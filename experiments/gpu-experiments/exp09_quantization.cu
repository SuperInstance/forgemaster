// Experiment 09: Int8 quantized constraint checking
// If FP16 gave 3.63x, can int8 give even more?
// Pack 4 bounds into 4 bytes (vs 8 bytes for FP16, 16 for float4)
// Tradeoff: range limited to 0-255

#include <cstdio>
#include <cuda_fp16.h>
#include <cuda_runtime.h>

// INT8: 4 constraints in 4 bytes (char4)
#include <vector_types.h>

__global__ void int8_check(const char4* __restrict__ bounds,
                            const int* __restrict__ values,
                            int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    char4 b = bounds[idx];
    int pass = 1;
    if (val >= (int)b.x) pass = 0;
    else if (val >= (int)b.y) pass = 0;
    else if (val >= (int)b.z) pass = 0;
    else if (val >= (int)b.w) pass = 0;
    results[idx] = pass;
}

// INT8: 8 constraints via uchar8 (8 bytes)
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

// UINT16: 4 constraints in 8 bytes (ushort4)
struct ushort4_custom { unsigned short x, y, z, w; };
__global__ void uint16_check(const ushort4_custom* __restrict__ bounds,
                              const int* __restrict__ values,
                              int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    int val = values[idx];
    ushort4_custom b = bounds[idx];
    int pass = 1;
    if (val >= (int)b.x) pass = 0;
    else if (val >= (int)b.y) pass = 0;
    else if (val >= (int)b.z) pass = 0;
    else if (val >= (int)b.w) pass = 0;
    results[idx] = pass;
}

// FP16 4-constraint (baseline from exp08)
struct half4 { half x, y, z, w; };
__global__ void fp16_check4(const half4* __restrict__ bounds,
                              const half* __restrict__ values,
                              int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    float val = float(values[idx]);
    half4 b = bounds[idx];
    int pass = 1;
    if (val >= float(b.x)) pass = 0;
    else if (val >= float(b.y)) pass = 0;
    else if (val >= float(b.z)) pass = 0;
    else if (val >= float(b.w)) pass = 0;
    results[idx] = pass;
}

int main() {
    printf("=== Quantization Level Comparison (4 constraints/element) ===\n\n");
    
    int n = 10000000;
    int iters = 100;
    int block = 256;
    int grid = (n + block - 1) / block;
    
    int *d_values, *d_results;
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_results, n * sizeof(int));
    
    int *h_vals = new int[n];
    // Keep values in int8 range for fair comparison
    for (int i = 0; i < n; i++) h_vals[i] = (i * 7 + 13) % 200;
    cudaMemcpy(d_values, h_vals, n * sizeof(int), cudaMemcpyHostToDevice);
    
    // INT8 bounds
    char4 *d_bounds_i8;
    cudaMalloc(&d_bounds_i8, n * sizeof(char4));
    char4 *h_i8 = new char4[n];
    for (int i = 0; i < n; i++) {
        h_i8[i].x = (char)((i * 7 + 30) % 200);
        h_i8[i].y = (char)((i * 11 + 50) % 200);
        h_i8[i].z = (char)((i * 13 + 70) % 200);
        h_i8[i].w = (char)((i * 17 + 90) % 200);
    }
    cudaMemcpy(d_bounds_i8, h_i8, n * sizeof(char4), cudaMemcpyHostToDevice);
    
    // INT8x8 bounds
    uchar8 *d_bounds_i8x8;
    cudaMalloc(&d_bounds_i8x8, n * sizeof(uchar8));
    uchar8 *h_i8x8 = new uchar8[n];
    for (int i = 0; i < n; i++) {
        h_i8x8[i] = {(unsigned char)((i*7+30)%200), (unsigned char)((i*11+40)%200),
                      (unsigned char)((i*13+50)%200), (unsigned char)((i*17+60)%200),
                      (unsigned char)((i*19+70)%200), (unsigned char)((i*23+80)%200),
                      (unsigned char)((i*29+90)%200), (unsigned char)((i*31+100)%200)};
    }
    cudaMemcpy(d_bounds_i8x8, h_i8x8, n * sizeof(uchar8), cudaMemcpyHostToDevice);
    
    // UINT16 bounds
    ushort4_custom *d_bounds_u16;
    cudaMalloc(&d_bounds_u16, n * sizeof(ushort4_custom));
    ushort4_custom *h_u16 = new ushort4_custom[n];
    for (int i = 0; i < n; i++) {
        h_u16[i].x = (unsigned short)((i * 7 + 300) % 65535);
        h_u16[i].y = (unsigned short)((i * 11 + 400) % 65535);
        h_u16[i].z = (unsigned short)((i * 13 + 500) % 65535);
        h_u16[i].w = (unsigned short)((i * 17 + 600) % 65535);
    }
    cudaMemcpy(d_bounds_u16, h_u16, n * sizeof(ushort4_custom), cudaMemcpyHostToDevice);
    
    // FP16 bounds
    half4 *d_bounds_f16;
    cudaMalloc(&d_bounds_f16, n * sizeof(half4));
    half4 *h_f16 = new half4[n];
    for (int i = 0; i < n; i++) {
        h_f16[i].x = __float2half((float)((i * 7 + 300) % 65000));
        h_f16[i].y = __float2half((float)((i * 11 + 400) % 65000));
        h_f16[i].z = __float2half((float)((i * 13 + 500) % 65000));
        h_f16[i].w = __float2half((float)((i * 17 + 600) % 65000));
    }
    cudaMemcpy(d_bounds_f16, h_f16, n * sizeof(half4), cudaMemcpyHostToDevice);
    
    // Also FP16 values
    half *d_values_f16;
    cudaMalloc(&d_values_f16, n * sizeof(half));
    half *h_vf16 = new half[n];
    for (int i = 0; i < n; i++) h_vf16[i] = __float2half((float)((i * 11 + 37) % 65000));
    cudaMemcpy(d_values_f16, h_vf16, n * sizeof(half), cudaMemcpyHostToDevice);
    
    // Warmup
    int8_check<<<grid, block>>>(d_bounds_i8, d_values, d_results, n);
    int8_check8<<<grid, block>>>(d_bounds_i8x8, d_values, d_results, n);
    uint16_check<<<grid, block>>>(d_bounds_u16, d_values, d_results, n);
    fp16_check4<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    struct Test { const char* name; int bytes_per_elem; int constraints; };
    Test tests[] = {
        {"INT8 x4 (4B/elem)", 4, 4},
        {"INT8 x8 (8B/elem)", 8, 8},
        {"UINT16 x4 (8B/elem)", 8, 4},
        {"FP16 x4 (8B/elem)", 8, 4},
    };
    
    printf("%-25s | %15s | %15s | %6s | %6s\n", "Layout", "Elem/s", "Constr/s", "GB/s", "ms");
    
    for (int t = 0; t < 4; t++) {
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            switch (t) {
                case 0: int8_check<<<grid, block>>>(d_bounds_i8, d_values, d_results, n); break;
                case 1: int8_check8<<<grid, block>>>(d_bounds_i8x8, d_values, d_results, n); break;
                case 2: uint16_check<<<grid, block>>>(d_bounds_u16, d_values, d_results, n); break;
                case 3: fp16_check4<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n); break;
            }
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        
        double elem_s = (double)n * iters / (ms / 1000.0);
        double constr_s = elem_s * tests[t].constraints;
        double bw = (double)(tests[t].bytes_per_elem + 4) * n * iters / (ms / 1000.0) / 1e9;
        
        printf("%-25s | %15.0f | %15.0f | %6.1f | %6.2f\n",
               tests[t].name, elem_s, constr_s, bw, ms/iters);
    }
    
    // Precision check INT8 vs UINT16 vs FP16
    printf("\n=== Precision Analysis ===\n");
    int *h_res = new int[n];
    int *h_res_ref = new int[n];
    
    // Use UINT16 as reference (exact for integers < 65535)
    uint16_check<<<grid, block>>>(d_bounds_u16, d_values, d_results, n);
    cudaMemcpy(h_res_ref, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
    
    // Compare FP16 (with FP16 values)
    fp16_check4<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n);
    cudaMemcpy(h_res, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
    
    int mm_fp16 = 0;
    for (int i = 0; i < n; i++) if (h_res[i] != h_res_ref[i]) mm_fp16++;
    printf("FP16 vs UINT16 mismatches: %d / %d (%.4f%%)\n", mm_fp16, n, 100.0*mm_fp16/n);
    
    delete[] h_vals; delete[] h_i8; delete[] h_i8x8;
    delete[] h_u16; delete[] h_f16; delete[] h_vf16;
    delete[] h_res; delete[] h_res_ref;
    cudaFree(d_values); cudaFree(d_results);
    cudaFree(d_bounds_i8); cudaFree(d_bounds_i8x8);
    cudaFree(d_bounds_u16); cudaFree(d_bounds_f16); cudaFree(d_values_f16);
    
    return 0;
}
