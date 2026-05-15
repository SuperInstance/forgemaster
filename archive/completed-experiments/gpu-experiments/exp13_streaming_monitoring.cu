// Experiment 13: Streaming constraint monitoring with CUDA Graphs
// Simulates real-time sensor data at 100Hz — can GPU keep up?
// Uses CUDA Graphs for zero-overhead kernel replay

#include <cstdio>
#include <cuda_runtime.h>

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

int main() {
    printf("=== Streaming Constraint Monitoring Simulation ===\n");
    printf("Simulates real-time sensor data at various rates\n\n");
    
    // Typical eVTOL flight computer: 100 sensors at 100Hz = 10K checks/frame
    // High-end: 1000 sensors at 1000Hz = 1M checks/frame
    int configs[][3] = {
        // {sensors, rate_hz, checks_per_sensor}
        {100, 100, 8},    // Basic eVTOL
        {500, 100, 8},    // Mid-range
        {1000, 100, 8},   // High-end eVTOL
        {1000, 1000, 8},  // Extreme
        {10000, 100, 8},  // Full aircraft
        {10000, 1000, 8}, // Full aircraft fast
    };
    
    for (int c = 0; c < 6; c++) {
        int sensors = configs[c][0];
        int rate_hz = configs[c][1];
        int checks = configs[c][2];
        int n = sensors;
        double frame_budget_ms = 1000.0 / rate_hz;
        
        // Allocate
        uchar8 *d_bounds;
        int *d_values, *d_results;
        cudaMalloc(&d_bounds, n * sizeof(uchar8));
        cudaMalloc(&d_values, n * sizeof(int));
        cudaMalloc(&d_results, n * sizeof(int));
        
        // Fill bounds
        uchar8 *h_b = new uchar8[n];
        for (int i = 0; i < n; i++) {
            h_b[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                      (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                      (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                      (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
        }
        cudaMemcpy(d_bounds, h_b, n * sizeof(uchar8), cudaMemcpyHostToDevice);
        
        int block = 256;
        int grid = (n + block - 1) / block;
        
        // Create CUDA Graph for zero-overhead replay
        cudaGraph_t graph;
        cudaGraphExec_t graph_exec;
        
        // Warmup
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaDeviceSynchronize();
        
        // Capture graph
        cudaStreamBeginCapture(cudaStream_t(cudaStreamPerThread), cudaStreamCaptureModeGlobal);
        int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        cudaStreamEndCapture(cudaStream_t(cudaStreamPerThread), &graph);
        cudaGraphInstantiate(&graph_exec, graph, NULL, NULL, 0);
        
        // Benchmark: 1000 frames without graphs
        int frames = 1000;
        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);
        
        cudaEventRecord(start);
        for (int f = 0; f < frames; f++) {
            int8_check8<<<grid, block>>>(d_bounds, d_values, d_results, n);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_no_graph;
        cudaEventElapsedTime(&ms_no_graph, start, stop);
        
        // Benchmark: 1000 frames with CUDA Graphs
        cudaEventRecord(start);
        for (int f = 0; f < frames; f++) {
            cudaGraphLaunch(graph_exec, cudaStream_t(cudaStreamPerThread));
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms_graph;
        cudaEventElapsedTime(&ms_graph, start, stop);
        
        double per_frame_no_graph = ms_no_graph / frames;
        double per_frame_graph = ms_graph / frames;
        double budget_pct_no = per_frame_no_graph / frame_budget_ms * 100.0;
        double budget_pct_graph = per_frame_graph / frame_budget_ms * 100.0;
        
        const char* status_no = (budget_pct_no < 10.0) ? "✓ GREAT" : (budget_pct_no < 50.0) ? "✓ OK" : "✗ TOO SLOW";
        const char* status_graph = (budget_pct_graph < 10.0) ? "✓ GREAT" : (budget_pct_graph < 50.0) ? "✓ OK" : "✗ TOO SLOW";
        
        printf("Sensors=%5d @ %4dHz (%5.1fms budget)\n", sensors, rate_hz, frame_budget_ms);
        printf("  Without graphs: %7.3f ms/frame (%5.1f%% budget) %s\n", per_frame_no_graph, budget_pct_no, status_no);
        printf("  With graphs:    %7.3f ms/frame (%5.1f%% budget) %s\n", per_frame_graph, budget_pct_graph, status_graph);
        printf("  Graph speedup:  %.2fx\n\n", per_frame_no_graph / per_frame_graph);
        
        cudaGraphDestroy(graph);
        cudaGraphExecDestroy(graph_exec);
        delete[] h_b;
        cudaFree(d_bounds); cudaFree(d_values); cudaFree(d_results);
    }
    
    return 0;
}
