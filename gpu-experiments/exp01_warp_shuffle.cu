// Experiment 01: Warp-level shuffle for constraint reduction
// Tests __shfl_down_sync for parallel constraint aggregation
// Goal: Can we beat ballot_sync for boolean reduction?

#include <cstdio>
#include <cuda_runtime.h>

__global__ void warp_shuffle_reduce(const int* __restrict__ constraints,
                                     const int* __restrict__ values,
                                     int* __restrict__ results,
                                     int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    // Each thread evaluates one constraint: value < threshold
    int pass = (values[idx] < constraints[idx]) ? 1 : 0;
    
    // Warp-level reduction using shuffle down
    unsigned mask = 0xffffffff;
    for (int offset = 16; offset > 0; offset >>= 1) {
        pass += __shfl_down_sync(mask, pass, offset);
    }
    
    // Lane 0 writes the warp result
    if ((threadIdx.x & 31) == 0) {
        int warp_id = idx >> 5;
        results[warp_id] = pass; // number of passing constraints in this warp
    }
}

__global__ void ballot_reduce(const int* __restrict__ constraints,
                               const int* __restrict__ values,
                               int* __restrict__ results,
                               int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    int pass = (values[idx] < constraints[idx]) ? 1 : 0;
    unsigned ballot = __ballot_sync(0xffffffff, pass);
    
    if ((threadIdx.x & 31) == 0) {
        int warp_id = idx >> 5;
        results[warp_id] = __popc(ballot); // count bits
    }
}

int main() {
    // Test sizes: 1K, 10K, 100K, 1M, 10M
    int sizes[] = {1000, 10000, 100000, 1000000, 10000000};
    int num_sizes = 5;
    
    for (int s = 0; s < num_sizes; s++) {
        int n = sizes[s];
        size_t bytes = n * sizeof(int);
        
        // Allocate
        int *d_constraints, *d_values, *d_results_shuffle, *d_results_ballot;
        cudaMalloc(&d_constraints, bytes);
        cudaMalloc(&d_values, bytes);
        int num_warps = (n + 31) / 32;
        cudaMalloc(&d_results_shuffle, num_warps * sizeof(int));
        cudaMalloc(&d_results_ballot, num_warps * sizeof(int));
        
        // Generate random data on GPU
        
        
        // Simple seed - use time
        for (int i = 0; i < 256; i++) {
        }
        
        // Fill with host random data instead (simpler)
        int *h_constraints = new int[n];
        int *h_values = new int[n];
        for (int i = 0; i < n; i++) {
            h_constraints[i] = (i * 7 + 13) % 1000;
            h_values[i] = (i * 11 + 37) % 1000;
        }
        cudaMemcpy(d_constraints, h_constraints, bytes, cudaMemcpyHostToDevice);
        cudaMemcpy(d_values, h_values, bytes, cudaMemcpyHostToDevice);
        
        int block = 256;
        int grid = (n + block - 1) / block;
        
        // Warmup
        warp_shuffle_reduce<<<grid, block>>>(d_constraints, d_values, d_results_shuffle, n);
        ballot_reduce<<<grid, block>>>(d_constraints, d_values, d_results_ballot, n);
        cudaDeviceSynchronize();
        
        // Benchmark shuffle
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        int iters = 100;
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            warp_shuffle_reduce<<<grid, block>>>(d_constraints, d_values, d_results_shuffle, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_shuffle;
        cudaEventElapsedTime(&ms_shuffle, start, stop);
        
        // Benchmark ballot
        cudaEventRecord(start);
        for (int i = 0; i < iters; i++) {
            ballot_reduce<<<grid, block>>>(d_constraints, d_values, d_results_ballot, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_ballot;
        cudaEventElapsedTime(&ms_ballot, start, stop);
        
        // Verify correctness
        int *h_results_shuffle = new int[num_warps];
        int *h_results_ballot = new int[num_warps];
        cudaMemcpy(h_results_shuffle, d_results_shuffle, num_warps * sizeof(int), cudaMemcpyDeviceToHost);
        cudaMemcpy(h_results_ballot, d_results_ballot, num_warps * sizeof(int), cudaMemcpyDeviceToHost);
        
        int mismatches = 0;
        for (int i = 0; i < num_warps; i++) {
            if (h_results_shuffle[i] != h_results_ballot[i]) mismatches++;
        }
        
        double checks_per_sec_shuffle = (double)n * iters / (ms_shuffle / 1000.0);
        double checks_per_sec_ballot = (double)n * iters / (ms_ballot / 1000.0);
        
        printf("n=%10d | shuffle: %10.0f c/s | ballot: %10.0f c/s | ratio: %.2fx | mismatches: %d\n",
               n, checks_per_sec_shuffle, checks_per_sec_ballot,
               checks_per_sec_shuffle / checks_per_sec_ballot, mismatches);
        
        delete[] h_constraints;
        delete[] h_values;
        delete[] h_results_shuffle;
        delete[] h_results_ballot;
        cudaFree(d_constraints);
        cudaFree(d_values);
        cudaFree(d_results_shuffle);
        cudaFree(d_results_ballot);
    }
    
    return 0;
}
