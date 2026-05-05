// Experiment 02: Shared memory bank conflict analysis for constraint tables
// Tests whether padding shared memory to avoid bank conflicts helps
// RTX 4050 has 32 shared memory banks, 4 bytes per bank

#include <cstdio>
#include <cuda_runtime.h>

#define BANKS 32
#define WARP_SIZE 32

// Naive: direct indexed access (potential bank conflicts)
__global__ void naive_shared_access(const int* __restrict__ lookup_table,
                                     const int* __restrict__ indices,
                                     int* __restrict__ results,
                                     int table_size, int n) {
    __shared__ int smem[256]; // max table size
    int tid = threadIdx.x;
    
    // Load table into shared memory
    for (int i = tid; i < table_size; i += blockDim.x) {
        smem[i] = lookup_table[i];
    }
    __syncthreads();
    
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    results[idx] = smem[indices[idx] % table_size];
}

// Padded: add 1 element per row to avoid bank conflicts
__global__ void padded_shared_access(const int* __restrict__ lookup_table,
                                      const int* __restrict__ indices,
                                      int* __restrict__ results,
                                      int table_size, int n) {
    __shared__ int smem[256 + 8]; // padded to avoid bank conflicts
    int tid = threadIdx.x;
    
    for (int i = tid; i < table_size; i += blockDim.x) {
        int bank = i % BANKS;
        int padded_idx = i + (i / BANKS); // skip one per bank group
        smem[padded_idx] = lookup_table[i];
    }
    __syncthreads();
    
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int i = indices[idx] % table_size;
    int padded_idx = i + (i / BANKS);
    results[idx] = smem[padded_idx];
}

int main() {
    printf("=== Shared Memory Bank Conflict Analysis ===\n");
    printf("RTX 4050: 32 banks, 4 bytes/bank\n\n");
    
    int table_sizes[] = {16, 32, 64, 128, 256};
    int n = 1000000; // 1M lookups
    
    for (int t = 0; t < 5; t++) {
        int table_size = table_sizes[t];
        
        int *h_table = new int[table_size];
        int *h_indices = new int[n];
        
        for (int i = 0; i < table_size; i++) h_table[i] = i * 7 + 3;
        // Generate adversarial indices — all targeting same bank
        for (int i = 0; i < n; i++) h_indices[i] = (i % BANKS) * (table_size / BANKS);
        
        int *d_table, *d_indices, *d_results_naive, *d_results_padded;
        cudaMalloc(&d_table, table_size * sizeof(int));
        cudaMalloc(&d_indices, n * sizeof(int));
        cudaMalloc(&d_results_naive, n * sizeof(int));
        cudaMalloc(&d_results_padded, n * sizeof(int));
        
        cudaMemcpy(d_table, h_table, table_size * sizeof(int), cudaMemcpyHostToDevice);
        cudaMemcpy(d_indices, h_indices, n * sizeof(int), cudaMemcpyHostToDevice);
        
        int block = 256;
        int grid = (n + block - 1) / block;
        
        // Warmup
        naive_shared_access<<<grid, block>>>(d_table, d_indices, d_results_naive, table_size, n);
        padded_shared_access<<<grid, block>>>(d_table, d_indices, d_results_padded, table_size, n);
        cudaDeviceSynchronize();
        
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        int iters = 1000;
        
        // Benchmark naive
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            naive_shared_access<<<grid, block>>>(d_table, d_indices, d_results_naive, table_size, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_naive;
        cudaEventElapsedTime(&ms_naive, start, stop);
        
        // Benchmark padded
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            padded_shared_access<<<grid, block>>>(d_table, d_indices, d_results_padded, table_size, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_padded;
        cudaEventElapsedTime(&ms_padded, start, stop);
        
        // Verify
        int *h_results_naive = new int[n];
        int *h_results_padded = new int[n];
        cudaMemcpy(h_results_naive, d_results_naive, n * sizeof(int), cudaMemcpyDeviceToHost);
        cudaMemcpy(h_results_padded, d_results_padded, n * sizeof(int), cudaMemcpyDeviceToHost);
        
        int mismatches = 0;
        for (int i = 0; i < n; i++) {
            if (h_results_naive[i] != h_results_padded[i]) mismatches++;
        }
        
        double lookups_naive = (double)n * iters / (ms_naive / 1000.0);
        double lookups_padded = (double)n * iters / (ms_padded / 1000.0);
        
        printf("table=%3d | naive: %12.0f L/s | padded: %12.0f L/s | speedup: %.2fx | mismatches: %d\n",
               table_size, lookups_naive, lookups_padded,
               lookups_padded / lookups_naive, mismatches);
        
        delete[] h_table;
        delete[] h_indices;
        delete[] h_results_naive;
        delete[] h_results_padded;
        cudaFree(d_table);
        cudaFree(d_indices);
        cudaFree(d_results_naive);
        cudaFree(d_results_padded);
    }
    
    return 0;
}
