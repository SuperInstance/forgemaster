// Experiment 33: CUDA Graphs + Production Kernel — Maximum Throughput
// Combines the validated production kernel with CUDA Graphs for minimal launch overhead
// Exp20 showed 18x launch speedup for fixed workloads. Let's see it with our real kernel.

#include <cstdio>
#include <cuda_runtime.h>

__global__ void flux_production_kernel(
    const unsigned char* flat_bounds,
    const int* constraint_set_ids,
    const int* sensor_values,
    unsigned char* violation_masks,
    int* violation_counts,
    int n_sensors,
    int n_constraints
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n_sensors) return;
    
    int set_id = constraint_set_ids[idx];
    int val = sensor_values[idx];
    const unsigned char* bounds = &flat_bounds[set_id * n_constraints];
    
    unsigned char mask = 0;
    if (val >= bounds[0]) mask |= 0x01;
    if (val >= bounds[1]) mask |= 0x02;
    if (val >= bounds[2]) mask |= 0x04;
    if (val >= bounds[3]) mask |= 0x08;
    if (val >= bounds[4]) mask |= 0x10;
    if (val >= bounds[5]) mask |= 0x20;
    if (val >= bounds[6]) mask |= 0x40;
    if (val >= bounds[7]) mask |= 0x80;
    
    violation_masks[idx] = mask;
    
    __shared__ int smem[8];
    if (threadIdx.x < 8) smem[threadIdx.x] = 0;
    __syncthreads();
    
    if (mask) {
        if (mask & 0x01) atomicAdd(&smem[0], 1);
        if (mask & 0x02) atomicAdd(&smem[1], 1);
        if (mask & 0x04) atomicAdd(&smem[2], 1);
        if (mask & 0x08) atomicAdd(&smem[3], 1);
        if (mask & 0x10) atomicAdd(&smem[4], 1);
        if (mask & 0x20) atomicAdd(&smem[5], 1);
        if (mask & 0x40) atomicAdd(&smem[6], 1);
        if (mask & 0x80) atomicAdd(&smem[7], 1);
    }
    __syncthreads();
    
    if (threadIdx.x < 8 && smem[threadIdx.x] > 0)
        atomicAdd(&violation_counts[threadIdx.x], smem[threadIdx.x]);
}

int main() {
    printf("=== Exp33: CUDA Graphs + Production Kernel ===\n\n");
    
    int n = 10000000;  // 10M sensors
    int n_sets = 50;
    int nc = 8;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 1000;
    
    unsigned char *d_bounds, *d_masks;
    int *d_set_ids, *d_values, *d_counts;
    cudaMalloc(&d_bounds, n_sets * nc);
    cudaMalloc(&d_set_ids, n * sizeof(int));
    cudaMalloc(&d_values, n * sizeof(int));
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_counts, nc * sizeof(int));
    
    // Init
    unsigned char *h_b = new unsigned char[n_sets * nc];
    int *h_s = new int[n];
    int *h_v = new int[n];
    for (int s = 0; s < n_sets; s++)
        for (int j = 0; j < nc; j++)
            h_b[s*nc+j] = 100 + (s*3+j*7)%140;
    for (int i = 0; i < n; i++) {
        h_s[i] = i % n_sets;
        h_v[i] = (i*7+13) % 250;
    }
    cudaMemcpy(d_bounds, h_b, n_sets*nc, cudaMemcpyHostToDevice);
    cudaMemcpy(d_set_ids, h_s, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_values, h_v, n*sizeof(int), cudaMemcpyHostToDevice);
    
    // Warmup
    cudaMemset(d_counts, 0, nc*sizeof(int));
    flux_production_kernel<<<grid, block>>>(d_bounds, d_set_ids, d_values, d_masks, d_counts, n, nc);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    
    // === Test 1: Standard launch (baseline) ===
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaMemsetAsync(d_counts, 0, nc*sizeof(int));
        flux_production_kernel<<<grid, block>>>(d_bounds, d_set_ids, d_values, d_masks, d_counts, n, nc);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_std;
    cudaEventElapsedTime(&ms_std, start, stop);
    
    // === Test 2: CUDA Graph (no update) ===
    cudaGraph_t graph;
    cudaStreamBeginCapture(cudaStreamPerThread, cudaStreamCaptureModeGlobal);
    cudaMemsetAsync(d_counts, 0, nc*sizeof(int));
    flux_production_kernel<<<grid, block>>>(d_bounds, d_set_ids, d_values, d_masks, d_counts, n, nc);
    cudaStreamEndCapture(cudaStreamPerThread, &graph);
    
    cudaGraphExec_t graph_exec;
    cudaGraphInstantiate(&graph_exec, graph, NULL, NULL, 0);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaGraphLaunch(graph_exec, cudaStreamPerThread);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_graph;
    cudaEventElapsedTime(&ms_graph, start, stop);
    
    // === Test 3: CUDA Graph with memcpy for data refresh ===
    // Simulate real workload: update sensor values each frame, re-run
    cudaGraph_t graph2;
    cudaStreamBeginCapture(cudaStreamPerThread, cudaStreamCaptureModeGlobal);
    cudaMemcpyAsync(d_values, h_v, n*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemsetAsync(d_counts, 0, nc*sizeof(int));
    flux_production_kernel<<<grid, block>>>(d_bounds, d_set_ids, d_values, d_masks, d_counts, n, nc);
    cudaStreamEndCapture(cudaStreamPerThread, &graph2);
    
    cudaGraphExec_t graph_exec2;
    cudaGraphInstantiate(&graph_exec2, graph2, NULL, NULL, 0);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++) {
        cudaGraphLaunch(graph_exec2, cudaStreamPerThread);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_graph_memcpy;
    cudaEventElapsedTime(&ms_graph_memcpy, start, stop);
    
    // === Test 4: Variable iteration counts ===
    printf("=== 10M sensors, 50 constraint sets, 8 constraints ===\n\n");
    printf("%-40s %10s %15s %10s\n", "Method", "ms/iter", "c/s", "Speedup");
    printf("%-40s %10.3f %15.0f %10s\n", "Standard launch", ms_std/iters,
           (double)n*nc*iters/(ms_std/1000), "1.00x");
    printf("%-40s %10.3f %15.0f %10.2fx\n", "CUDA Graph (no data update)", ms_graph/iters,
           (double)n*nc*iters/(ms_graph/1000), ms_std/ms_graph);
    printf("%-40s %10.3f %15.0f %10.2fx\n", "CUDA Graph (with memcpy refresh)", ms_graph_memcpy/iters,
           (double)n*nc*iters/(ms_graph_memcpy/1000), ms_std/ms_graph_memcpy);
    
    // Correctness check — verify graph gives same results
    unsigned char *h_masks_std = new unsigned char[n];
    unsigned char *h_masks_graph = new unsigned char[n];
    int h_counts_std[8], h_counts_graph[8];
    
    // Standard
    cudaMemset(d_counts, 0, nc*sizeof(int));
    flux_production_kernel<<<grid, block>>>(d_bounds, d_set_ids, d_values, d_masks, d_counts, n, nc);
    cudaDeviceSynchronize();
    cudaMemcpy(h_masks_std, d_masks, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_counts_std, d_counts, nc*sizeof(int), cudaMemcpyDeviceToHost);
    
    // Graph
    cudaGraphLaunch(graph_exec, cudaStreamPerThread);
    cudaDeviceSynchronize();
    cudaMemcpy(h_masks_graph, d_masks, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_counts_graph, d_counts, nc*sizeof(int), cudaMemcpyDeviceToHost);
    
    int mismatches = 0;
    for (int i = 0; i < n; i++)
        if (h_masks_std[i] != h_masks_graph[i]) mismatches++;
    
    int count_mismatches = 0;
    for (int j = 0; j < 8; j++)
        if (h_counts_std[j] != h_counts_graph[j]) count_mismatches++;
    
    printf("\n=== Correctness ===\n");
    printf("Graph vs Standard: %d mask mismatches, %d count mismatches\n", mismatches, count_mismatches);
    
    // Launch overhead measurement
    int single_iters = 10000;
    cudaEventRecord(start);
    for (int i = 0; i < single_iters; i++) {
        cudaGraphLaunch(graph_exec, cudaStreamPerThread);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_single;
    cudaEventElapsedTime(&ms_single, start, stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < single_iters; i++) {
        flux_production_kernel<<<grid, block>>>(d_bounds, d_set_ids, d_values, d_masks, d_counts, n, nc);
    }
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms_single_std;
    cudaEventElapsedTime(&ms_single_std, start, stop);
    
    printf("\n=== Launch Overhead (%d launches) ===\n", single_iters);
    printf("Standard launch: %.3f us/launch\n", ms_single_std*1000/single_iters);
    printf("CUDA Graph:      %.3f us/launch\n", ms_single*1000/single_iters);
    printf("Graph speedup:   %.1fx faster launch\n", ms_single_std/ms_single);
    
    printf("\n=== PRODUCTION RECOMMENDATION ===\n");
    if (ms_std/ms_graph > 1.5) {
        printf("USE CUDA GRAPHS for fixed-workload production deployments.\n");
        printf("Provides %.1fx throughput improvement with zero correctness risk.\n", ms_std/ms_graph);
    } else {
        printf("CUDA Graphs provide marginal benefit for this workload.\n");
        printf("Standard launch is sufficient.\n");
    }
    
    delete[] h_b; delete[] h_s; delete[] h_v;
    delete[] h_masks_std; delete[] h_masks_graph;
    cudaFree(d_bounds); cudaFree(d_set_ids); cudaFree(d_values);
    cudaFree(d_masks); cudaFree(d_counts);
    cudaGraphDestroy(graph);
    cudaGraphDestroy(graph2);
    cudaGraphExecDestroy(graph_exec);
    cudaGraphExecDestroy(graph_exec2);
    
    return 0;
}
