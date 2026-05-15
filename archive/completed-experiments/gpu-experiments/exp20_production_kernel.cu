// Experiment 20: Grand Finale — Optimal FLUX Production Kernel
// Combines ALL learnings from experiments 1-19 into a single optimized kernel:
// - INT8 packed constraints (exp09-11)
// - Block-reduce atomic aggregation (exp12)
// - CUDA Graph replay (exp13)
// - Mixed constraint types (exp18)
// - Branchless evaluation (exp19)

#include <cstdio>
#include <cuda_runtime.h>

struct FluxConstraint {
    unsigned char bounds[8]; // 8 INT8 constraint bounds
};

// The OPTIMAL kernel based on all experiments
__global__ void flux_production_kernel(const FluxConstraint* __restrict__ constraints,
                                        const unsigned char* __restrict__ sensor_values,
                                        int* pass_count,    // atomic counter
                                        int* fail_count,    // atomic counter  
                                        int* results,       // per-element results
                                        int n) {
    extern __shared__ int smem[]; // [0] = shared pass, [1] = shared fail
    int tid = threadIdx.x;
    
    if (tid < 2) smem[tid] = 0;
    __syncthreads();
    
    int idx = blockIdx.x * blockDim.x + tid;
    if (idx >= n) return;
    
    unsigned char val = sensor_values[idx];
    FluxConstraint c = constraints[idx];
    
    // Branchless: check all 8 simultaneously
    unsigned char mask = 0xFF;
    #pragma unroll
    for (int i = 0; i < 8; i++) {
        if (val >= c.bounds[i]) mask &= ~(1 << i);
    }
    
    int pass = (mask == 0xFF) ? 1 : 0;
    results[idx] = pass;
    
    // Block-level reduce (exp12 winner)
    atomicAdd(&smem[pass], 1);
    __syncthreads();
    
    // One thread per block updates global counters
    if (tid == 0) {
        atomicAdd(pass_count, smem[1]);
        atomicAdd(fail_count, smem[0]);
    }
}

int main() {
    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  FLUX Production Kernel — Grand Finale       ║\n");
    printf("║  Combines all 19 experiments of optimization  ║\n");
    printf("╚══════════════════════════════════════════════╝\n\n");
    
    int n = 10000000;
    int block = 256;
    int grid = (n + block - 1) / block;
    size_t smem_size = 2 * sizeof(int);
    
    FluxConstraint *d_constraints;
    unsigned char *d_values;
    int *d_results, *d_pass_count, *d_fail_count;
    
    cudaMalloc(&d_constraints, n * sizeof(FluxConstraint));
    cudaMalloc(&d_values, n * sizeof(unsigned char));
    cudaMalloc(&d_results, n * sizeof(int));
    cudaMalloc(&d_pass_count, sizeof(int));
    cudaMalloc(&d_fail_count, sizeof(int));
    
    // Generate realistic sensor data
    FluxConstraint *h_c = new FluxConstraint[n];
    unsigned char *h_v = new unsigned char[n];
    
    for (int i = 0; i < n; i++) {
        // Safety bounds: vary per sensor (some tight, some loose)
        unsigned char base = 20 + (i % 10) * 20;
        for (int j = 0; j < 8; j++) {
            h_c[i].bounds[j] = base + j * 5;
        }
        h_v[i] = (unsigned char)((i * 7 + 13) % 220 + 10);
    }
    cudaMemcpy(d_constraints, h_c, n * sizeof(FluxConstraint), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n * sizeof(unsigned char), cudaMemcpyHostToDevice);
    
    // Create CUDA Graph for production replay
    int zero = 0;
    cudaMemcpy(d_pass_count, &zero, sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_fail_count, &zero, sizeof(int), cudaMemcpyHostToDevice);
    
    flux_production_kernel<<<grid, block, smem_size>>>(d_constraints, d_values, d_pass_count, d_fail_count, d_results, n);
    cudaDeviceSynchronize();
    
    cudaGraph_t graph;
    cudaGraphExec_t graph_exec;
    cudaStreamBeginCapture(cudaStream_t(cudaStreamPerThread), cudaStreamCaptureModeGlobal);
    cudaMemcpy(d_pass_count, &zero, sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_fail_count, &zero, sizeof(int), cudaMemcpyHostToDevice);
    flux_production_kernel<<<grid, block, smem_size>>>(d_constraints, d_values, d_pass_count, d_fail_count, d_results, n);
    cudaStreamEndCapture(cudaStream_t(cudaStreamPerThread), &graph);
    cudaGraphInstantiate(&graph_exec, graph, NULL, NULL, 0);
    
    // Benchmark: 1000 iterations
    int iters = 1000;
    
    // Without graphs
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemcpy(d_pass_count, &zero, sizeof(int), cudaMemcpyHostToDevice);
        cudaMemcpy(d_fail_count, &zero, sizeof(int), cudaMemcpyHostToDevice);
        flux_production_kernel<<<grid, block, smem_size>>>(d_constraints, d_values, d_pass_count, d_fail_count, d_results, n);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_normal;
    cudaEventElapsedTime(&ms_normal, start, stop);
    
    // With CUDA Graphs
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaGraphLaunch(graph_exec, cudaStream_t(cudaStreamPerThread));
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float ms_graph;
    cudaEventElapsedTime(&ms_graph, start, stop);
    
    // Final results
    int gpu_pass, gpu_fail;
    cudaMemcpy(&gpu_pass, d_pass_count, sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(&gpu_fail, d_fail_count, sizeof(int), cudaMemcpyDeviceToHost);
    
    // CPU reference
    int cpu_pass = 0;
    for (int i = 0; i < n; i++) {
        unsigned char val = h_v[i];
        int pass = 1;
        for (int j = 0; j < 8; j++) {
            if (val >= h_c[i].bounds[j]) { pass = 0; break; }
        }
        if (pass) cpu_pass++;
    }
    
    printf("Results (n=%d, 8 constraints each):\n", n);
    printf("  Total constraints: %d\n", n * 8);
    printf("  CPU reference: %d pass / %d fail\n", cpu_pass, n - cpu_pass);
    printf("  GPU result:    %d pass / %d fail %s\n\n", gpu_pass, gpu_fail,
           (gpu_pass + gpu_fail == n && gpu_pass == cpu_pass) ? "✓" : "✗");
    
    printf("Performance:\n");
    printf("  Normal:     %.3f ms/iter | %.0f constr/s\n", ms_normal/iters, (double)n*8*iters/(ms_normal/1000.0));
    printf("  CUDA Graph: %.3f ms/iter | %.0f constr/s\n", ms_graph/iters, (double)n*8*iters/(ms_graph/1000.0));
    printf("  Graph speedup: %.1fx\n\n", ms_normal/ms_graph);
    
    printf("Scaling estimate (CUDA Graph):\n");
    double base_constr = (double)n*8*iters/(ms_graph/1000.0);
    for (int sensors = 100; sensors <= 100000; sensors *= 10) {
        double rate = sensors * 8 * base_constr / (double)(n * 8); // proportional
        // But actually just use per-element time
        double elem_time_us = ms_graph / iters * 1000.0 / n; // microseconds per element
        double frame100hz = elem_time_us * sensors; // us for all sensors at 100Hz
        double frame1khz = frame100hz * 10;
        printf("  %6d sensors: %.1f us/frame @100Hz (%.1f%% budget), %.1f us @1KHz (%.1f%% budget)\n",
               sensors, frame100hz, frame100hz/10000.0*100, frame1khz, frame1khz/1000.0*100);
    }
    
    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);
    printf("\nVRAM: %zuMB used / %zuMB total (%.0f%% free)\n",
           (total_mem-free_mem)/(1024*1024), total_mem/(1024*1024), 100.0*free_mem/total_mem);
    
    delete[] h_c; delete[] h_v;
    cudaFree(d_constraints); cudaFree(d_values); cudaFree(d_results);
    cudaFree(d_pass_count); cudaFree(d_fail_count);
    cudaGraphDestroy(graph); cudaGraphExecDestroy(graph_exec);
    
    return 0;
}
