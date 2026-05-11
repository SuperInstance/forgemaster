/*
 * snapkit_cuda.cu — Master API implementation
 *
 * "The snap is the gatekeeper of attention. The delta is the compass.
 *  The lattice is the infrastructure. Attention is the thirst."
 *
 * CUDA/PTX implementation of tolerance-compressed attention allocation.
 * Combines all components into a coherent pipeline API.
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "eisenstein_snap.cuh"
#include "batch_snap.cuh"
#include "delta_detect.cuh"
#include "attention.cuh"
#include "topology.cuh"
#include "reduce.cuh"
#include "kernels/eisenstein_snap_kernel.cuh"
#include "kernels/delta_threshold_kernel.cuh"
#include "kernels/attention_weight_kernel.cuh"
#include "kernels/topology_snap_kernel.cuh"

/* ======================================================================
 * Default configuration
 * ====================================================================== */

void snapkit_create_default_config(snapkit_config_t* config) {
    if (!config) return;

    config->topology = SNAPKIT_ADE_A2;      /* Eisenstein — universal solvent */
    config->default_tolerance = SNAPKIT_DEFAULT_TOLERANCE;
    config->num_streams = 0;
    config->allocation_strategy = SNAPKIT_ALLOC_ACTION;
    config->total_attention_budget = 100.0f;
    config->top_k_deltas = 16;

    memset(config->stream_configs, 0, sizeof(config->stream_configs));
}

void snapkit_configure_stream(
    snapkit_config_t* config,
    int stream_id,
    snapkit_topology_t topology,
    float tolerance,
    float priority_weight
) {
    if (!config || stream_id < 0 || stream_id >= SNAPKIT_MAX_STREAMS) return;

    config->stream_configs[stream_id].stream_id = stream_id;
    config->stream_configs[stream_id].topology = topology;
    config->stream_configs[stream_id].tolerance = tolerance;
    config->stream_configs[stream_id].priority_weight = priority_weight;

    if (stream_id + 1 > config->num_streams) {
        config->num_streams = stream_id + 1;
    }
}

/* ======================================================================
 * Full Pipeline
 * ====================================================================== */

int snapkit_pipeline(
    const snapkit_config_t* config,
    const float* points_x,
    const float* points_y,
    const int*   stream_ids,
    const float* actionability,
    const float* urgency,
    snapkit_attention_t* out_results,
    int    N,
    cudaStream_t stream
) {
    if (!config || N <= 0) return 0;

    /* Allocate device memory for pipeline intermediates */
    int   *d_a, *d_b, *d_is_delta;
    float *d_delta, *d_weights, *d_tolerances;

    CUDA_SAFE_CALL(cudaMallocAsync(&d_a, N * sizeof(int), stream));
    CUDA_SAFE_CALL(cudaMallocAsync(&d_b, N * sizeof(int), stream));
    CUDA_SAFE_CALL(cudaMallocAsync(&d_delta, N * sizeof(float), stream));
    CUDA_SAFE_CALL(cudaMallocAsync(&d_is_delta, N * sizeof(int), stream));
    CUDA_SAFE_CALL(cudaMallocAsync(&d_weights, N * sizeof(float), stream));

    /* Setup tolerances on device */
    CUDA_SAFE_CALL(cudaMallocAsync(&d_tolerances,
                                    config->num_streams * sizeof(float), stream));

    float host_tolerances[SNAPKIT_MAX_STREAMS];
    for (int i = 0; i < config->num_streams; i++) {
        host_tolerances[i] = config->stream_configs[i].tolerance;
    }
    CUDA_SAFE_CALL(cudaMemcpyAsync(d_tolerances, host_tolerances,
                                    config->num_streams * sizeof(float),
                                    cudaMemcpyHostToDevice, stream));

    /* Step 1: Batch Eisenstein snap */
    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    eisenstein_snap_ptx_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y, d_a, d_b, d_delta, N
    );

    /* Step 2: Delta threshold with weighting */
    delta_threshold_weighted_ptx_kernel<<<grid_size, block_size, 0, stream>>>(
        d_delta, d_tolerances, stream_ids,
        actionability, urgency,
        d_is_delta, d_weights, N
    );

    /* Step 3: Top-K delta selection */
    int K = config->top_k_deltas;
    if (K <= 0) K = 16;
    if (K > SNAPKIT_WARP_SIZE) K = SNAPKIT_WARP_SIZE;

    int *d_top_indices;
    float *d_top_weights;

    CUDA_SAFE_CALL(cudaMallocAsync(&d_top_indices, K * sizeof(int), stream));
    CUDA_SAFE_CALL(cudaMallocAsync(&d_top_weights, K * sizeof(float), stream));
    CUDA_SAFE_CALL(cudaMemsetAsync(d_top_indices, -1, K * sizeof(int), stream));

    size_t shared_mem = (K * block_size * (sizeof(float) + sizeof(int)));

    top_k_deltas_kernel<<<grid_size, block_size, shared_mem, stream>>>(
        d_weights, d_top_indices, d_top_weights, K, N
    );

    /* Step 4: Copy results back to host */
    int host_indices[SNAPKIT_WARP_SIZE];
    float host_weights[SNAPKIT_WARP_SIZE];

    CUDA_SAFE_CALL(cudaMemcpyAsync(host_indices, d_top_indices,
                                    K * sizeof(int),
                                    cudaMemcpyDeviceToHost, stream));
    CUDA_SAFE_CALL(cudaMemcpyAsync(host_weights, d_top_weights,
                                    K * sizeof(float),
                                    cudaMemcpyDeviceToHost, stream));

    CUDA_SAFE_CALL(cudaStreamSynchronize(stream));

    /* Copy delta values for top-K points */
    int *d_delta_values = NULL;
    float *host_delta_values = NULL;

    /* For a complete pipeline, we'd also copy deltas for top-K */
    int actual_k = 0;
    for (int i = 0; i < K; i++) {
        if (host_indices[i] >= 0) {
            out_results[actual_k].point_idx = host_indices[i];
            out_results[actual_k].delta = host_weights[i];
            out_results[actual_k].attention = config->total_attention_budget;
            out_results[actual_k].rank = actual_k + 1;
            actual_k++;
        }
    }

    /* Free temporary buffers */
    CUDA_SAFE_CALL(cudaFreeAsync(d_a, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_b, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_delta, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_is_delta, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_weights, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_tolerances, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_top_indices, stream));
    CUDA_SAFE_CALL(cudaFreeAsync(d_top_weights, stream));

    return actual_k;
}

/* ======================================================================
 * CUDA Graphs Support
 * ====================================================================== */

cudaGraphExec_t snapkit_capture_graph(
    const snapkit_config_t* config,
    cudaStream_t stream
) {
    cudaGraph_t graph;
    cudaGraphExec_t graphExec;

    /* Begin graph capture */
    CUDA_SAFE_CALL(cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal));

    /* Execute a representative pipeline — captured by CUDA Graphs */
    /* For actual usage, the caller would provide the data pointers */
    /* Here we set up the pipeline structure */

    /* We need actual device pointers for capture — caller must provide them */
    /* This is a placeholder that shows the pattern */

    CUDA_SAFE_CALL(cudaStreamEndCapture(stream, &graph));
    CUDA_SAFE_CALL(cudaGraphInstantiate(&graphExec, graph, NULL, NULL, 0));
    CUDA_SAFE_CALL(cudaGraphDestroy(graph));

    return graphExec;
}

void snapkit_launch_graph(cudaGraphExec_t graphExec, cudaStream_t stream) {
    CUDA_SAFE_CALL(cudaGraphLaunch(graphExec, stream));
}

void snapkit_destroy_graph(cudaGraphExec_t graphExec) {
    CUDA_SAFE_CALL(cudaGraphExecDestroy(graphExec));
}

/* ======================================================================
 * Utilities
 * ====================================================================== */

void snapkit_print_device_info(int device_id) {
    cudaDeviceProp prop;
    CUDA_SAFE_CALL(cudaGetDeviceProperties(&prop, device_id));

    printf("=== CUDA Device %d: %s ===\n", device_id, prop.name);
    printf("  Compute Capability:  %d.%d\n", prop.major, prop.minor);
    printf("  SMs:                 %d\n", prop.multiProcessorCount);
    printf("  Warp Size:           %d\n", prop.warpSize);
    printf("  Max Threads/Block:   %d\n", prop.maxThreadsPerBlock);
    printf("  Max Threads Dim:     %d x %d x %d\n",
           prop.maxThreadsDim[0], prop.maxThreadsDim[1], prop.maxThreadsDim[2]);
    printf("  Max Grid Dim:        %d x %d x %d\n",
           prop.maxGridSize[0], prop.maxGridSize[1], prop.maxGridSize[2]);
    printf("  Shared Mem/Block:    %zu bytes\n", prop.sharedMemPerBlock);
    printf("  Global Mem:          %.2f GB\n",
           (double)prop.totalGlobalMem / (1024.0 * 1024.0 * 1024.0));
    printf("  L2 Cache:            %d bytes\n", prop.l2CacheSize);
    printf("  Memory Clock:        %d MHz\n", prop.memoryClockRate / 1000);
    printf("  Memory Bus Width:    %d bits\n", prop.memoryBusWidth);
    printf("  Peak Memory BW:      %.1f GB/s\n",
           2.0 * prop.memoryClockRate * (prop.memoryBusWidth / 8) / 1e6);
    printf("  Async Engines:       %d\n", prop.asyncEngineCount);
    printf("  Concurrent Kernels:  %s\n",
           prop.concurrentKernels ? "Yes" : "No");
    printf("  Unified Addressing:  %s\n",
           prop.unifiedAddressing ? "Yes" : "No");
    printf("  Managed Memory:      %s\n",
           prop.managedMemory ? "Yes" : "No");
    printf("===============================\n");
}

int snapkit_compute_capability(int device_id) {
    cudaDeviceProp prop;
    CUDA_SAFE_CALL(cudaGetDeviceProperties(&prop, device_id));
    return prop.major * 10 + prop.minor;
}

void snapkit_recommended_launch_params(
    int N,
    int* grid_size,
    int* block_size
) {
    *block_size = 256;
    *grid_size = (N + *block_size - 1) / *block_size;
    *grid_size = min(*grid_size, 65535);
}
