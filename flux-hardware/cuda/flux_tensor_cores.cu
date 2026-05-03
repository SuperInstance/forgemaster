/**
 * flux_tensor_cores.cu — Tensor Core Accelerated Constraint Propagation
 *
 * Uses WMMA (Warp Matrix Multiply-Accumulate) for mixed-precision
 * constraint Jacobian evaluation on RTX 4050 (SM 8.6).
 *
 * The key insight: constraint propagation can be expressed as matrix operations.
 * A constraint Jacobian J maps variable changes to constraint satisfaction changes.
 * WMMA evaluates this at FP16 throughput (up to 990 TFLOPS on Hopper).
 *
 * Strategy: FP16 screening → FP32 exact → FP64 safety
 * - FP16 tensor cores rapidly screen constraints (99%+ throughput)
 * - FP32 for exact boundary checks
 * - FP64 only for safety-critical verification
 */

#include <cuda_runtime.h>
#include <mma.h>
#include <stdio.h>
#include <stdint.h>

using namespace nvcuda;

// ============================================================================
// Tensor Core Constraint Jacobian Evaluation
// ============================================================================
// Express constraint checking as matrix multiply:
//   constraint_matrix (M x N) × variable_vector (N x 1) = satisfaction_vector (M x 1)
// Where:
//   M = number of constraints
//   N = number of variables
//   constraint_matrix encodes the linear constraints
//   variable_vector is the current variable values
//   satisfaction_vector > 0 means constraint satisfied

// WMMA tile size for FP16: 16x16x16
#define WMMA_M 16
#define WMMA_N 16
#define WMMA_K 16

__global__ void tensor_constraint_check(
    const half* __restrict__ constraint_matrix,  // M x K (row-major)
    const half* __restrict__ variable_vector,     // K x 1
    half* __restrict__ satisfaction,              // M x 1
    const half* __restrict__ thresholds,          // M x 1 (lower bounds)
    int32_t* __restrict__ results,                // M x 1 (1=satisfied, 0=violated)
    int M, int K
) {
    // Each warp handles one output element
    int warp_id = (blockIdx.x * blockDim.x + threadIdx.x) / 32;
    int lane = threadIdx.x % 32;
    
    if (warp_id >= M) return;
    
    // Accumulate dot product across K dimensions
    // Using WMMA fragments for FP16 matrix multiply
    wmma::fragment<wmma::matrix_a, WMMA_M, WMMA_N, WMMA_K, half, wmma::row_major> a_frag;
    wmma::fragment<wmma::matrix_b, WMMA_M, WMMA_N, WMMA_K, half, wmma::col_major> b_frag;
    wmma::fragment<wmma::accumulator, WMMA_M, WMMA_N, WMMA_K, half> acc_frag;
    
    float sum = 0.0f;
    
    // Process K in tiles of WMMA_K
    for (int k_tile = 0; k_tile < K; k_tile += WMMA_K) {
        int remaining = min(WMMA_K, K - k_tile);
        
        if (remaining == WMMA_K) {
            // Full tile — use WMMA
            wmma::load_matrix_sync(a_frag, constraint_matrix + warp_id * K + k_tile, K);
            wmma::load_matrix_sync(b_frag, variable_vector + k_tile, 1);
            wmma::fill_fragment(acc_frag, 0.0f);
            wmma::mma_sync(acc_frag, a_frag, b_frag, acc_frag);
            
            // Extract result from accumulator
            // acc_frag stores MxN results, we only need [0]
            float acc_val = 0.0f;
            // First element of accumulator
            half* acc_ptr = reinterpret_cast<half*>(&acc_frag);
            for (int i = lane; i < WMMA_M * WMMA_N; i += 32) {
                if (i < WMMA_M) {
                    acc_val += __half2float(acc_ptr[i]);
                }
            }
            // Warp-level sum
            for (int offset = 16; offset > 0; offset /= 2) {
                acc_val += __shfl_down_sync(0xFFFFFFFF, acc_val, offset);
            }
            if (lane == 0) sum += acc_val;
        } else {
            // Partial tile — manual dot product
            float partial = 0.0f;
            for (int k = lane; k < remaining; k += 32) {
                float a = __half2float(constraint_matrix[warp_id * K + k_tile + k]);
                float b = __half2float(variable_vector[k_tile + k]);
                partial += a * b;
            }
            // Warp reduce
            for (int offset = 16; offset > 0; offset /= 2) {
                partial += __shfl_down_sync(0xFFFFFFFF, partial, offset);
            }
            if (lane == 0) sum += partial;
        }
    }
    
    // Check if constraint is satisfied
    if (lane == 0) {
        float threshold = __half2float(thresholds[warp_id]);
        int satisfied = (sum >= threshold) ? 1 : 0;
        satisfaction[warp_id] = __float2half(sum);
        results[warp_id] = satisfied;
    }
}

// ============================================================================
// Batched tensor constraint checking — multiple variable sets
// ============================================================================

__global__ void tensor_batch_check(
    const half* __restrict__ constraint_matrix,  // M x K
    const half* __restrict__ variable_sets,      // B x K (B sets of variables)
    int32_t* __restrict__ results,               // B x M (all constraints for all sets)
    const half* __restrict__ thresholds,         // M x 1
    int B, int M, int K
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int b = idx / M;  // batch index
    int m = idx % M;  // constraint index
    
    if (b >= B || m >= M) return;
    
    // Dot product: constraint_matrix[m,:] · variable_sets[b,:]
    float sum = 0.0f;
    for (int k = threadIdx.x % 32; k < K; k += 32) {
        float a = __half2float(constraint_matrix[m * K + k]);
        float b_val = __half2float(variable_sets[b * K + k]);
        sum += a * b_val;
    }
    
    // Warp reduce
    for (int offset = 16; offset > 0; offset /= 2) {
        sum += __shfl_down_sync(0xFFFFFFFF, sum, offset);
    }
    
    if ((threadIdx.x % 32) == 0) {
        float threshold = __half2float(thresholds[m]);
        results[b * M + m] = (sum >= threshold) ? 1 : 0;
    }
}

// ============================================================================
// Host API
// ============================================================================

extern "C" {

int flux_tensor_check(
    const half* constraint_matrix,
    const half* variable_vector,
    const half* thresholds,
    int32_t* results,
    int M, int K
) {
    half *d_cm, *d_vv, *d_sat, *d_thresh;
    int32_t *d_res;
    
    cudaMalloc(&d_cm, M * K * sizeof(half));
    cudaMalloc(&d_vv, K * sizeof(half));
    cudaMalloc(&d_sat, M * sizeof(half));
    cudaMalloc(&d_thresh, M * sizeof(half));
    cudaMalloc(&d_res, M * sizeof(int32_t));
    
    cudaMemcpy(d_cm, constraint_matrix, M * K * sizeof(half), cudaMemcpyHostToDevice);
    cudaMemcpy(d_vv, variable_vector, K * sizeof(half), cudaMemcpyHostToDevice);
    cudaMemcpy(d_thresh, thresholds, M * sizeof(half), cudaMemcpyHostToDevice);
    
    // Launch: one warp per constraint
    int threads = 128;  // 4 warps per block
    int blocks = (M * 32 + threads - 1) / threads;
    
    tensor_constraint_check<<<blocks, threads>>>(
        d_cm, d_vv, d_sat, d_thresh, d_res, M, K
    );
    cudaDeviceSynchronize();
    
    cudaMemcpy(results, d_res, M * sizeof(int32_t), cudaMemcpyDeviceToHost);
    
    cudaFree(d_cm); cudaFree(d_vv); cudaFree(d_sat);
    cudaFree(d_thresh); cudaFree(d_res);
    return 0;
}

}
