// Experiment 03: Tensor Core constraint checking via WMMA
// Can we repurpose tensor cores (FP16 matmul) for constraint satisfaction?
// Idea: encode constraint matrix as FP16, multiply by variable vector, check thresholds
// This tests whether tensor cores can accelerate batch constraint evaluation

#include <cstdio>
#include <cuda_runtime.h>
#include <mma.h>

using namespace nvcuda;

// Baseline: standard CUDA core constraint evaluation
__global__ void cuda_core_check(const half* __restrict__ constraints,
                                 const half* __restrict__ values,
                                 half* __restrict__ results,
                                 int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    // Simple: result = (value < constraint) ? 1.0 : 0.0
    results[idx] = (float(values[idx]) < float(constraints[idx])) ? __float2half(1.0f) : __float2half(0.0f);
}

// Tensor core approach: batch 16x16 constraint matrix multiply
// Constraints encoded as 16x16 matrix, values as 16x1 vector
// Result vector checked against threshold
__global__ void tensor_core_check(const half* __restrict__ constraint_matrix,
                                   const half* __restrict__ value_vectors,
                                   half* __restrict__ output,
                                   int num_batches) {
    wmma::fragment<wmma::matrix_a, 16, 16, 16, half, wmma::row_major> a_frag;
    wmma::fragment<wmma::matrix_b, 16, 16, 16, half, wmma::col_major> b_frag;
    wmma::fragment<wmma::accumulator, 16, 16, 16, half> c_frag;
    
    int batch = blockIdx.x;
    if (batch >= num_batches) return;
    
    // Load 16x16 constraint matrix
    wmma::load_matrix_sync(a_frag, constraint_matrix + batch * 256, 16);
    // Load 16x16 value matrix (tiled value vector)
    wmma::load_matrix_sync(b_frag, value_vectors + batch * 256, 16);
    
    wmma::fill_fragment(c_frag, __float2half(0.0f));
    wmma::mma_sync(c_frag, a_frag, b_frag, c_frag);
    
    wmma::store_matrix_sync(output + batch * 256, c_frag, 16, wmma::mem_row_major);
}

int main() {
    printf("=== Tensor Core vs CUDA Core Constraint Checking ===\n");
    printf("RTX 4050: 3rd-gen tensor cores (Ada Lovelace)\n\n");
    
    // Test with 16x16 batches (tensor core native size)
    int batch_sizes[] = {64, 256, 1024, 4096, 16384};
    int tile = 16;
    
    for (int b = 0; b < 5; b++) {
        int num_batches = batch_sizes[b];
        int total_elements = num_batches * tile * tile; // 16x16 per batch
        int simple_n = total_elements; // same element count for fair comparison
        
        // Allocate for tensor core test
        half *d_constraint_matrix, *d_value_vectors, *d_tensor_output;
        cudaMalloc(&d_constraint_matrix, total_elements * sizeof(half));
        cudaMalloc(&d_value_vectors, total_elements * sizeof(half));
        cudaMalloc(&d_tensor_output, total_elements * sizeof(half));
        
        // Fill with data
        half *h_data = new half[total_elements];
        for (int i = 0; i < total_elements; i++) {
            h_data[i] = __float2half((float)(i % 1000) / 1000.0f);
        }
        cudaMemcpy(d_constraint_matrix, h_data, total_elements * sizeof(half), cudaMemcpyHostToDevice);
        cudaMemcpy(d_value_vectors, h_data, total_elements * sizeof(half), cudaMemcpyHostToDevice);
        
        // Allocate for simple CUDA core test
        half *d_simple_constraints, *d_simple_values, *d_simple_results;
        cudaMalloc(&d_simple_constraints, simple_n * sizeof(half));
        cudaMalloc(&d_simple_values, simple_n * sizeof(half));
        cudaMalloc(&d_simple_results, simple_n * sizeof(half));
        cudaMemcpy(d_simple_constraints, h_data, simple_n * sizeof(half), cudaMemcpyHostToDevice);
        cudaMemcpy(d_simple_values, h_data, simple_n * sizeof(half), cudaMemcpyHostToDevice);
        
        // Warmup
        tensor_core_check<<<num_batches, 32>>>(d_constraint_matrix, d_value_vectors, d_tensor_output, num_batches);
        cuda_core_check<<<(simple_n + 255) / 256, 256>>>(d_simple_constraints, d_simple_values, d_simple_results, simple_n);
        cudaDeviceSynchronize();
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        int iters = 100;
        
        // Benchmark tensor cores
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            tensor_core_check<<<num_batches, 32>>>(d_constraint_matrix, d_value_vectors, d_tensor_output, num_batches);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_tensor;
        cudaEventElapsedTime(&ms_tensor, start, stop);
        
        // Benchmark CUDA cores
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            cuda_core_check<<<(simple_n + 255) / 256, 256>>>(d_simple_constraints, d_simple_values, d_simple_results, simple_n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_cuda;
        cudaEventElapsedTime(&ms_cuda, start, stop);
        
        double ops_tensor = (double)total_elements * iters / (ms_tensor / 1000.0);
        double ops_cuda = (double)simple_n * iters / (ms_cuda / 1000.0);
        
        // Check VRAM usage
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        
        printf("batches=%5d (elements=%8d) | tensor: %12.0f ops/s | cuda: %12.0f ops/s | ratio: %.2fx | VRAM free: %zuMB\n",
               num_batches, total_elements, ops_tensor, ops_cuda,
               ops_tensor / ops_cuda, free_mem / (1024*1024));
        
        delete[] h_data;
        cudaFree(d_constraint_matrix);
        cudaFree(d_value_vectors);
        cudaFree(d_tensor_output);
        cudaFree(d_simple_constraints);
        cudaFree(d_simple_values);
        cudaFree(d_simple_results);
    }
    
    return 0;
}
