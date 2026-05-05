// Experiment 08: Half-precision (FP16) constraint checking
// If we're memory-bound, halving the data size should nearly double throughput
// Risk: FP16 only has 11-bit mantissa (max precise integer = 2048)
// Test: Is FP16 sufficient for safety constraint bounds?

#include <cstdio>
#include <cuda_fp16.h>
#include <cuda_runtime.h>

__global__ void fp32_check(const float* __restrict__ bounds,
                            const float* __restrict__ values,
                            int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    results[idx] = (values[idx] < bounds[idx]) ? 1 : 0;
}

__global__ void fp16_check(const half* __restrict__ bounds,
                            const half* __restrict__ values,
                            int* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    results[idx] = (float(values[idx]) < float(bounds[idx])) ? 1 : 0;
}

__global__ void fp16_vectorized(const half2* __restrict__ bounds_pairs,
                                 const half2* __restrict__ value_pairs,
                                 int2* results, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    half2 b = bounds_pairs[idx];
    half2 v = value_pairs[idx];
    // Check 2 constraints per load
    results[idx].x = (float(v.x) < float(b.x)) ? 1 : 0;
    results[idx].y = (float(v.y) < float(b.y)) ? 1 : 0;
}

// FP16 with float4-like packing: 4 half bounds = 8 bytes = single load
struct half4 { half x, y, z, w; };
__global__ void fp16_packed4(const half4* __restrict__ bounds,
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
    printf("=== Half-Precision Constraint Checking ===\n\n");
    
    int n = 10000000;
    int iters = 100;
    
    // FP32 test
    float *d_bounds_f32, *d_values_f32;
    int *d_results;
    cudaMalloc(&d_bounds_f32, n * sizeof(float));
    cudaMalloc(&d_values_f32, n * sizeof(float));
    cudaMalloc(&d_results, n * sizeof(int));
    
    float *h_data = new float[n];
    for (int i = 0; i < n; i++) h_data[i] = (float)((i * 7 + 13) % 2000); // Keep < 2048 for FP16 precision
    cudaMemcpy(d_bounds_f32, h_data, n * sizeof(float), cudaMemcpyHostToDevice);
    for (int i = 0; i < n; i++) h_data[i] = (float)((i * 11 + 37) % 2000);
    cudaMemcpy(d_values_f32, h_data, n * sizeof(float), cudaMemcpyHostToDevice);
    
    // FP16 test
    half *d_bounds_f16, *d_values_f16;
    cudaMalloc(&d_bounds_f16, n * sizeof(half));
    cudaMalloc(&d_values_f16, n * sizeof(half));
    half *h_half = new half[n];
    for (int i = 0; i < n; i++) h_half[i] = __float2half((float)((i * 7 + 13) % 2000));
    cudaMemcpy(d_bounds_f16, h_half, n * sizeof(half), cudaMemcpyHostToDevice);
    for (int i = 0; i < n; i++) h_half[i] = __float2half((float)((i * 11 + 37) % 2000));
    cudaMemcpy(d_values_f16, h_half, n * sizeof(half), cudaMemcpyHostToDevice);
    
    // FP16 packed4 test (4 half bounds per element = 8 bytes)
    half4 *d_bounds_packed;
    cudaMalloc(&d_bounds_packed, n * sizeof(half4));
    half4 *h_packed = new half4[n];
    for (int i = 0; i < n; i++) {
        h_packed[i].x = __float2half((float)((i * 7 + 100) % 2000));
        h_packed[i].y = __float2half((float)((i * 11 + 200) % 2000));
        h_packed[i].z = __float2half((float)((i * 13 + 300) % 2000));
        h_packed[i].w = __float2half((float)((i * 17 + 400) % 2000));
    }
    cudaMemcpy(d_bounds_packed, h_packed, n * sizeof(half4), cudaMemcpyHostToDevice);
    
    int block = 256;
    int grid = (n + block - 1) / block;
    
    // Warmup
    fp32_check<<<grid, block>>>(d_bounds_f32, d_values_f32, d_results, n);
    fp16_check<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n);
    fp16_packed4<<<grid, block>>>(d_bounds_packed, d_values_f16, d_results, n);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // Test 1: FP32 single constraint
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) fp32_check<<<grid, block>>>(d_bounds_f32, d_values_f32, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_f32;
    cudaEventElapsedTime(&ms_f32, start, stop);
    
    // Test 2: FP16 single constraint
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) fp16_check<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_f16;
    cudaEventElapsedTime(&ms_f16, start, stop);
    
    // Test 3: FP16 packed 4 constraints
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) fp16_packed4<<<grid, block>>>(d_bounds_packed, d_values_f16, d_results, n);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_packed;
    cudaEventElapsedTime(&ms_packed, start, stop);
    
    double f32_checks = (double)n * iters / (ms_f32 / 1000.0);
    double f16_checks = (double)n * iters / (ms_f16 / 1000.0);
    double packed_checks = (double)n * 4 * iters / (ms_packed / 1000.0);
    
    printf("FP32 1-constraint:  %14.0f checks/s (%6.1f GB/s) | %.2f ms/iter\n",
           f32_checks, 12.0 * n * iters / (ms_f32/1000.0) / 1e9, ms_f32/iters);
    printf("FP16 1-constraint:  %14.0f checks/s (%6.1f GB/s) | %.2f ms/iter\n",
           f16_checks, 6.0 * n * iters / (ms_f16/1000.0) / 1e9, ms_f16/iters);
    printf("FP16 4-constraint:  %14.0f checks/s (%6.1f GB/s) | %.2f ms/iter\n",
           packed_checks, 12.0 * n * iters / (ms_packed/1000.0) / 1e9, ms_packed/iters);
    
    printf("\nSpeedup FP16 vs FP32 (single): %.2fx\n", f32_checks / f16_checks > 0 ? f16_checks / f32_checks : 0);
    printf("Throughput ratio (4-constr packed vs 1-constr FP32): %.2fx\n", packed_checks / f32_checks);
    
    // FP16 precision test
    printf("\n=== FP16 Precision Analysis ===\n");
    int *h_res_f32 = new int[n];
    int *h_res_f16 = new int[n];
    cudaMemcpy(d_results, h_res_f32, 0, cudaMemcpyHostToDevice); // reset
    
    // Run FP32
    fp32_check<<<grid, block>>>(d_bounds_f32, d_values_f32, d_results, n);
    cudaMemcpy(h_res_f32, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
    
    // Run FP16
    fp16_check<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n);
    cudaMemcpy(h_res_f16, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
    
    int mismatches = 0;
    for (int i = 0; i < n; i++) {
        if (h_res_f32[i] != h_res_f16[i]) mismatches++;
    }
    printf("FP32 vs FP16 mismatches (values < 2048): %d / %d (%.4f%%)\n",
           mismatches, n, 100.0 * mismatches / n);
    
    // Now test with values > 2048 to check FP16 precision loss
    for (int i = 0; i < n; i++) h_data[i] = (float)((i * 7 + 13) % 10000);
    cudaMemcpy(d_bounds_f32, h_data, n * sizeof(float), cudaMemcpyHostToDevice);
    for (int i = 0; i < n; i++) h_half[i] = __float2half(h_data[i]);
    cudaMemcpy(d_bounds_f16, h_half, n * sizeof(half), cudaMemcpyHostToDevice);
    
    for (int i = 0; i < n; i++) h_data[i] = (float)((i * 11 + 37) % 10000);
    cudaMemcpy(d_values_f32, h_data, n * sizeof(float), cudaMemcpyHostToDevice);
    for (int i = 0; i < n; i++) h_half[i] = __float2half(h_data[i]);
    cudaMemcpy(d_values_f16, h_half, n * sizeof(half), cudaMemcpyHostToDevice);
    
    fp32_check<<<grid, block>>>(d_bounds_f32, d_values_f32, d_results, n);
    cudaMemcpy(h_res_f32, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
    fp16_check<<<grid, block>>>(d_bounds_f16, d_values_f16, d_results, n);
    cudaMemcpy(h_res_f16, d_results, n * sizeof(int), cudaMemcpyDeviceToHost);
    
    mismatches = 0;
    for (int i = 0; i < n; i++) {
        if (h_res_f32[i] != h_res_f16[i]) mismatches++;
    }
    printf("FP32 vs FP16 mismatches (values < 10000): %d / %d (%.4f%%)\n",
           mismatches, n, 100.0 * mismatches / n);
    
    delete[] h_data; delete[] h_half; delete[] h_packed;
    delete[] h_res_f32; delete[] h_res_f16;
    cudaFree(d_bounds_f32); cudaFree(d_values_f32);
    cudaFree(d_bounds_f16); cudaFree(d_values_f16);
    cudaFree(d_bounds_packed); cudaFree(d_results);
    
    return 0;
}
