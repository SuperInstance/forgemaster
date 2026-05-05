//! CUDA kernel: nearest manifold point (snap) with shared-memory tiling
//!
//! Each block loads a tile of manifold points into __shared__ memory.
//! Every thread in the block handles one query; all threads scan the tile together.
//! Tiles repeat until the full manifold is covered.

#include <cuda_runtime.h>
#include <float.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>

// ---------------------------------------------------------------------------
// GPU kernel
// ---------------------------------------------------------------------------

/// snap_kernel: each thread finds the nearest manifold point to its query.
///
/// Tiling strategy:
///   - Shared memory holds `blockDim.x` float2 manifold points per iteration.
///   - Threads cooperatively load one tile, then each independently scans it.
///   - Repeated for ceil(n_manifold / blockDim.x) tiles.
///
/// Shared memory limit ≈ 48–128 KB per block; with block_size = 256 threads
/// each tile uses 256 × 8 B = 2 KB — well within budget, leaving room to
/// increase the tile without hitting hardware limits.
__global__ void snap_kernel(
    const float2 *__restrict__ queries,    // [n_queries]  query points
    const float2 *__restrict__ manifold,   // [n_manifold] manifold points
    int    n_manifold,
    float  *__restrict__ out_distances,    // [n_queries]  output distances
    int    *__restrict__ out_indices,      // [n_queries]  output indices
    int    n_queries
) {
    extern __shared__ float2 smem[];  // one tile of manifold points

    int tid = blockIdx.x * blockDim.x + threadIdx.x;

    // Load this thread's query (all threads participate in smem loads below
    // regardless of whether tid is in-range, so keep it outside the guard).
    float qx = 0.0f, qy = 0.0f;
    if (tid < n_queries) {
        float2 q = queries[tid];
        qx = q.x;
        qy = q.y;
    }

    float best_dist_sq = FLT_MAX;
    int   best_idx     = 0;

    int tile_size = blockDim.x;

    for (int tile_start = 0; tile_start < n_manifold; tile_start += tile_size) {
        // ── Cooperative load ──────────────────────────────────────────────
        int manifold_idx = tile_start + threadIdx.x;
        if (manifold_idx < n_manifold) {
            smem[threadIdx.x] = manifold[manifold_idx];
        } else {
            // Pad with a sentinel that will never win
            smem[threadIdx.x] = make_float2(2.0f, 2.0f);
        }
        __syncthreads();

        // ── Each thread scans the tile ────────────────────────────────────
        if (tid < n_queries) {
            int valid = min(tile_size, n_manifold - tile_start);
            for (int i = 0; i < valid; i++) {
                float dx = smem[i].x - qx;
                float dy = smem[i].y - qy;
                float d2 = dx * dx + dy * dy;
                if (d2 < best_dist_sq) {
                    best_dist_sq = d2;
                    best_idx     = tile_start + i;
                }
            }
        }
        __syncthreads();
    }

    if (tid < n_queries) {
        out_distances[tid] = sqrtf(best_dist_sq);
        out_indices[tid]   = best_idx;
    }
}

// ---------------------------------------------------------------------------
// Host-callable C API
// ---------------------------------------------------------------------------

/// Returns number of CUDA-capable devices (0 if none or on error).
extern "C" int cuda_device_count(void) {
    int count = 0;
    cudaError_t err = cudaGetDeviceCount(&count);
    if (err != cudaSuccess) return 0;
    return count;
}

/// Batch snap: find the nearest manifold point for each query on the GPU.
///
/// query_xs / query_ys : arrays of length n_queries  (unit-circle points)
/// manifold_xs / manifold_ys : arrays of length n_manifold (Pythagorean triples normalized)
/// out_distances : caller-allocated float[n_queries]
/// out_indices   : caller-allocated int[n_queries]
///
/// Returns 0 on success, -1 on any CUDA error.
extern "C" int cuda_snap_batch(
    const float *query_xs,    const float *query_ys,    int n_queries,
    const float *manifold_xs, const float *manifold_ys, int n_manifold,
    float *out_distances,     int *out_indices
) {
    // ── Interleave separate x/y arrays into float2 ────────────────────────
    float2 *h_queries  = (float2 *)malloc(n_queries  * sizeof(float2));
    float2 *h_manifold = (float2 *)malloc(n_manifold * sizeof(float2));
    if (!h_queries || !h_manifold) {
        free(h_queries);
        free(h_manifold);
        return -1;
    }
    for (int i = 0; i < n_queries;  i++) { h_queries[i]  = make_float2(query_xs[i],    query_ys[i]);    }
    for (int i = 0; i < n_manifold; i++) { h_manifold[i] = make_float2(manifold_xs[i], manifold_ys[i]); }

    // ── Device allocations ────────────────────────────────────────────────
    float2 *d_queries  = NULL, *d_manifold = NULL;
    float  *d_dist     = NULL;
    int    *d_idx      = NULL;
    int     ret        = -1;

    if (cudaMalloc(&d_queries,  n_queries  * sizeof(float2)) != cudaSuccess) goto cleanup;
    if (cudaMalloc(&d_manifold, n_manifold * sizeof(float2)) != cudaSuccess) goto cleanup;
    if (cudaMalloc(&d_dist,     n_queries  * sizeof(float))  != cudaSuccess) goto cleanup;
    if (cudaMalloc(&d_idx,      n_queries  * sizeof(int))    != cudaSuccess) goto cleanup;

    cudaMemcpy(d_queries,  h_queries,  n_queries  * sizeof(float2), cudaMemcpyHostToDevice);
    cudaMemcpy(d_manifold, h_manifold, n_manifold * sizeof(float2), cudaMemcpyHostToDevice);

    {
        // ── Launch ────────────────────────────────────────────────────────
        int block_size   = 256;
        int grid_size    = (n_queries + block_size - 1) / block_size;
        size_t smem_bytes = (size_t)block_size * sizeof(float2); // 2 KB per block

        snap_kernel<<<grid_size, block_size, smem_bytes>>>(
            d_queries, d_manifold, n_manifold, d_dist, d_idx, n_queries
        );

        if (cudaDeviceSynchronize() != cudaSuccess) goto cleanup;
    }

    cudaMemcpy(out_distances, d_dist, n_queries * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(out_indices,   d_idx,  n_queries * sizeof(int),   cudaMemcpyDeviceToHost);
    ret = 0;

cleanup:
    cudaFree(d_queries);
    cudaFree(d_manifold);
    cudaFree(d_dist);
    cudaFree(d_idx);
    free(h_queries);
    free(h_manifold);
    return ret;
}
