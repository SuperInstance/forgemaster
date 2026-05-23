/*
 * host_interface.cu — Host-side API implementation
 *
 * Memory management (pinned), kernel launch configuration,
 * result retrieval, error handling, stream-based async execution.
 */

#include "flux_cuda.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cuda_runtime.h>

/* ═══════════════════════════════════════════════════════════════
 *  Internal helpers
 * ═════════════════════════════════════════════════════════════ */

#define FLUX_CUDA_CHECK(call)                                               \
    do {                                                                    \
        cudaError_t err = (call);                                           \
        if (err != cudaSuccess) {                                           \
            fprintf(stderr, "[FLUX CUDA] %s:%d: %s\n",                     \
                    __FILE__, __LINE__, cudaGetErrorString(err));           \
            return FLUX_CUDA_ERR_KERNEL;                                    \
        }                                                                   \
    } while (0)

/* Kernel declarations (defined in other .cu files) */
extern __global__ void flux_vm_batch_kernel(
    const uint8_t*, size_t, const double*, int, double*, int,
    int32_t*, int, size_t);

extern __global__ void flux_arc_consistency_kernel(
    int*, int32_t*, const int*, int, int, int, int);

extern __global__ void flux_csp_backtrack_kernel(
    const int*, const int*, const double*, int*, int32_t*,
    int, int, int, int, int);

extern __global__ void flux_forward_check_kernel(
    int*, const int*, const int*, int, int, int, int);

extern __global__ void sonar_physics_batch_kernel(
    const double*, const double*, const double*, const double*,
    double*, double*, int);

/* ── Auto-select block/grid size ────────────────────────────── */
static void compute_launch_params(int count, int threads_per_block,
                                   dim3& grid, dim3& block)
{
    block = dim3(threads_per_block);
    grid  = dim3((count + threads_per_block - 1) / threads_per_block);
}

/* ═══════════════════════════════════════════════════════════════
 *  Device management
 * ═════════════════════════════════════════════════════════════ */

static cudaStream_t g_stream = nullptr;
static bool g_initialized = false;

flux_cuda_error_t flux_cuda_init(void)
{
    if (g_initialized) return FLUX_CUDA_OK;

    int device_count = 0;
    cudaError_t err = cudaGetDeviceCount(&device_count);
    if (err != cudaSuccess || device_count == 0) {
        fprintf(stderr, "[FLUX CUDA] No CUDA devices found\n");
        return FLUX_CUDA_ERR_NO_DEVICE;
    }

    /* Select device 0 */
    FLUX_CUDA_CHECK(cudaSetDevice(0));

    /* Create async stream */
    FLUX_CUDA_CHECK(cudaStreamCreate(&g_stream));

    g_initialized = true;
    return FLUX_CUDA_OK;
}

flux_cuda_error_t flux_cuda_device_info(flux_cuda_device_info_t* info)
{
    if (!info) return FLUX_CUDA_ERR_INVALID;

    cudaDeviceProp prop;
    FLUX_CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));

    strncpy(info->name, prop.name, sizeof(info->name) - 1);
    info->name[sizeof(info->name) - 1] = '\0';
    info->major = prop.major;
    info->minor = prop.minor;
    info->total_mem = prop.totalGlobalMem;
    info->multiprocessor_count = prop.multiProcessorCount;
    info->max_threads_per_block = prop.maxThreadsPerBlock;
    info->max_shared_per_block = prop.sharedMemPerBlock;
    info->warp_size = prop.warpSize;

    return FLUX_CUDA_OK;
}

void flux_cuda_cleanup(void)
{
    if (!g_initialized) return;
    cudaStreamDestroy(g_stream);
    g_stream = nullptr;
    g_initialized = false;
    cudaDeviceReset();
}

/* ═══════════════════════════════════════════════════════════════
 *  Batch FLUX VM execution
 * ═════════════════════════════════════════════════════════════ */

flux_cuda_error_t flux_cuda_batch_execute(
    const flux_vm_batch_desc_t*  desc,
    int                          instance_count,
    flux_vm_batch_result_t*      results)
{
    if (!desc || !results || instance_count <= 0)
        return FLUX_CUDA_ERR_INVALID;
    if (!g_initialized)
        return FLUX_CUDA_ERR_NO_DEVICE;

    const int max_stack = (desc->max_stack > 0) ? desc->max_stack : 256;

    /* Allocate device memory */
    uint8_t* d_bytecode = nullptr;
    double*  d_inputs   = nullptr;
    double*  d_outputs  = nullptr;
    int32_t* d_violations = nullptr;

    /* Expand bytecode table: repeat for each instance */
    size_t total_bc = desc->bytecode_len * instance_count;
    FLUX_CUDA_CHECK(cudaMalloc(&d_bytecode, total_bc));
    for (int i = 0; i < instance_count; ++i) {
        FLUX_CUDA_CHECK(cudaMemcpy(d_bytecode + i * desc->bytecode_len,
                                    desc->bytecode, desc->bytecode_len,
                                    cudaMemcpyHostToDevice));
    }

    size_t inputs_bytes = sizeof(double) * instance_count * desc->inputs_per_instance;
    FLUX_CUDA_CHECK(cudaMalloc(&d_inputs, inputs_bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_inputs, desc->inputs, inputs_bytes, cudaMemcpyHostToDevice));

    size_t outputs_bytes = sizeof(double) * instance_count * results->outputs_per_instance;
    FLUX_CUDA_CHECK(cudaMalloc(&d_outputs, outputs_bytes));
    FLUX_CUDA_CHECK(cudaMemset(d_outputs, 0, outputs_bytes));

    FLUX_CUDA_CHECK(cudaMalloc(&d_violations, sizeof(int32_t) * instance_count));
    FLUX_CUDA_CHECK(cudaMemset(d_violations, 0, sizeof(int32_t) * instance_count));

    /* Shared memory per block: stack + sp + inputs + outputs */
    size_t smem = max_stack * sizeof(double)          /* stack */
                + sizeof(int)                          /* sp */
                + desc->inputs_per_instance * sizeof(double)
                + results->outputs_per_instance * sizeof(double);

    /* Launch: one block per instance, single-threaded VM per block */
    dim3 grid(instance_count);
    dim3 block(32); /* warp for reduction */

    flux_vm_batch_kernel<<<grid, block, smem, g_stream>>>(
        d_bytecode, desc->bytecode_len,
        d_inputs, desc->inputs_per_instance,
        d_outputs, results->outputs_per_instance,
        d_violations, max_stack, desc->bytecode_len);

    FLUX_CUDA_CHECK(cudaGetLastError());
    FLUX_CUDA_CHECK(cudaStreamSynchronize(g_stream));

    /* Copy results back */
    FLUX_CUDA_CHECK(cudaMemcpy(results->outputs, d_outputs, outputs_bytes, cudaMemcpyDeviceToHost));
    FLUX_CUDA_CHECK(cudaMemcpy(results->violation_flags, d_violations,
                                sizeof(int32_t) * instance_count, cudaMemcpyDeviceToHost));

    /* Cleanup */
    cudaFree(d_bytecode);
    cudaFree(d_inputs);
    cudaFree(d_outputs);
    cudaFree(d_violations);

    return FLUX_CUDA_OK;
}

/* ═══════════════════════════════════════════════════════════════
 *  Parallel CSP solver
 * ═════════════════════════════════════════════════════════════ */

flux_cuda_error_t flux_cuda_csp_solve(
    const flux_csp_problem_desc_t* problem_desc,
    const flux_csp_batch_t*        batch,
    int                            problem_count)
{
    if (!problem_desc || !batch || problem_count <= 0)
        return FLUX_CUDA_ERR_INVALID;
    if (!g_initialized)
        return FLUX_CUDA_ERR_NO_DEVICE;

    const int V  = problem_desc->var_count;
    const int MD = problem_desc->max_domain_size;
    const int C  = problem_desc->constraint_count;

    /* Allocate device buffers */
    int*     d_domains     = nullptr;
    int*     d_constraints = nullptr;
    double*  d_weights     = nullptr;
    int*     d_solutions   = nullptr;
    int32_t* d_solved      = nullptr;

    size_t domains_bytes = sizeof(int) * problem_count * V * MD;
    size_t cons_bytes    = sizeof(int) * problem_count * C * 2;
    size_t sol_bytes     = sizeof(int) * problem_count * V;

    FLUX_CUDA_CHECK(cudaMalloc(&d_domains, domains_bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_domains, batch->domains, domains_bytes, cudaMemcpyHostToDevice));

    FLUX_CUDA_CHECK(cudaMalloc(&d_constraints, cons_bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_constraints, batch->constraints, cons_bytes, cudaMemcpyHostToDevice));

    if (batch->weights) {
        FLUX_CUDA_CHECK(cudaMalloc(&d_weights, sizeof(double) * problem_count * C));
        FLUX_CUDA_CHECK(cudaMemcpy(d_weights, batch->weights,
                                    sizeof(double) * problem_count * C, cudaMemcpyHostToDevice));
    }

    FLUX_CUDA_CHECK(cudaMalloc(&d_solutions, sol_bytes));
    FLUX_CUDA_CHECK(cudaMemset(d_solutions, -1, sol_bytes));

    FLUX_CUDA_CHECK(cudaMalloc(&d_solved, sizeof(int32_t) * problem_count));
    FLUX_CUDA_CHECK(cudaMemset(d_solved, 0, sizeof(int32_t) * problem_count));

    /* Shared memory for backtrack kernel */
    size_t smem_bt = V * MD * sizeof(int); /* domain copy */

    /* Launch backtrack: one block per problem, 256 threads per block */
    dim3 grid_bt(problem_count);
    dim3 block_bt(min(MD, 256));

    flux_csp_backtrack_kernel<<<grid_bt, block_bt, smem_bt, g_stream>>>(
        d_domains, d_constraints, d_weights,
        d_solutions, d_solved,
        V, MD, C, problem_count, MD);

    FLUX_CUDA_CHECK(cudaGetLastError());
    FLUX_CUDA_CHECK(cudaStreamSynchronize(g_stream));

    /* Copy results */
    FLUX_CUDA_CHECK(cudaMemcpy(batch->solutions, d_solutions, sol_bytes, cudaMemcpyDeviceToHost));
    FLUX_CUDA_CHECK(cudaMemcpy(batch->solved, d_solved,
                                sizeof(int32_t) * problem_count, cudaMemcpyDeviceToHost));

    cudaFree(d_domains);
    cudaFree(d_constraints);
    if (d_weights) cudaFree(d_weights);
    cudaFree(d_solutions);
    cudaFree(d_solved);

    return FLUX_CUDA_OK;
}

/* ═══════════════════════════════════════════════════════════════
 *  Arc consistency pruning
 * ═════════════════════════════════════════════════════════════ */

flux_cuda_error_t flux_cuda_arc_consistency(
    const flux_csp_problem_desc_t* problem_desc,
    flux_arc_batch_t*              batch,
    int                            problem_count)
{
    if (!problem_desc || !batch || problem_count <= 0)
        return FLUX_CUDA_ERR_INVALID;
    if (!g_initialized)
        return FLUX_CUDA_ERR_NO_DEVICE;

    const int V  = problem_desc->var_count;
    const int MD = problem_desc->max_domain_size;
    const int C  = problem_desc->constraint_count;

    int*     d_domains     = nullptr;
    int32_t* d_pruned      = nullptr;
    int*     d_constraints = nullptr;

    size_t domains_bytes = sizeof(int) * problem_count * V * MD;

    FLUX_CUDA_CHECK(cudaMalloc(&d_domains, domains_bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_domains, batch->domains, domains_bytes, cudaMemcpyHostToDevice));

    FLUX_CUDA_CHECK(cudaMalloc(&d_pruned, sizeof(int32_t) * problem_count * V));
    FLUX_CUDA_CHECK(cudaMemset(d_pruned, 0, sizeof(int32_t) * problem_count * V));

    FLUX_CUDA_CHECK(cudaMalloc(&d_constraints, sizeof(int) * problem_count * C * 2));

    /* Shared memory: domain copy + pruned counts */
    size_t smem = V * MD * sizeof(int) + V * sizeof(int32_t);

    dim3 grid(problem_count);
    dim3 block(min(C, 1024));

    flux_arc_consistency_kernel<<<grid, block, smem, g_stream>>>(
        d_domains, d_pruned, d_constraints,
        V, MD, C, problem_count);

    FLUX_CUDA_CHECK(cudaGetLastError());
    FLUX_CUDA_CHECK(cudaStreamSynchronize(g_stream));

    /* Copy back */
    FLUX_CUDA_CHECK(cudaMemcpy(batch->domains, d_domains, domains_bytes, cudaMemcpyDeviceToHost));
    FLUX_CUDA_CHECK(cudaMemcpy(batch->pruned, d_pruned,
                                sizeof(int32_t) * problem_count * V, cudaMemcpyDeviceToHost));

    cudaFree(d_domains);
    cudaFree(d_pruned);
    cudaFree(d_constraints);

    return FLUX_CUDA_OK;
}

/* ═══════════════════════════════════════════════════════════════
 *  Batch sonar physics
 * ═════════════════════════════════════════════════════════════ */

flux_cuda_error_t flux_cuda_sonar_physics(flux_sonar_batch_t* batch)
{
    if (!batch || batch->count <= 0)
        return FLUX_CUDA_ERR_INVALID;
    if (!g_initialized)
        return FLUX_CUDA_ERR_NO_DEVICE;

    const int N = batch->count;
    const size_t bytes = sizeof(double) * N;

    double *d_depths = nullptr, *d_temps = nullptr, *d_sal = nullptr, *d_freqs = nullptr;
    double *d_speeds = nullptr, *d_absorp = nullptr;

    FLUX_CUDA_CHECK(cudaMalloc(&d_depths, bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_depths, batch->depths, bytes, cudaMemcpyHostToDevice));

    FLUX_CUDA_CHECK(cudaMalloc(&d_temps, bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_temps, batch->temps, bytes, cudaMemcpyHostToDevice));

    FLUX_CUDA_CHECK(cudaMalloc(&d_sal, bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_sal, batch->salinities, bytes, cudaMemcpyHostToDevice));

    FLUX_CUDA_CHECK(cudaMalloc(&d_freqs, bytes));
    FLUX_CUDA_CHECK(cudaMemcpy(d_freqs, batch->freqs, bytes, cudaMemcpyHostToDevice));

    FLUX_CUDA_CHECK(cudaMalloc(&d_speeds, bytes));
    FLUX_CUDA_CHECK(cudaMalloc(&d_absorp, bytes));

    dim3 grid, block;
    compute_launch_params(N, 256, grid, block);

    sonar_physics_batch_kernel<<<grid, block, 0, g_stream>>>(
        d_depths, d_temps, d_sal, d_freqs,
        d_speeds, d_absorp, N);

    FLUX_CUDA_CHECK(cudaGetLastError());
    FLUX_CUDA_CHECK(cudaStreamSynchronize(g_stream));

    FLUX_CUDA_CHECK(cudaMemcpy(batch->sound_speeds, d_speeds, bytes, cudaMemcpyDeviceToHost));
    FLUX_CUDA_CHECK(cudaMemcpy(batch->absorptions, d_absorp, bytes, cudaMemcpyDeviceToHost));

    cudaFree(d_depths);
    cudaFree(d_temps);
    cudaFree(d_sal);
    cudaFree(d_freqs);
    cudaFree(d_speeds);
    cudaFree(d_absorp);

    return FLUX_CUDA_OK;
}
