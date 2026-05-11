#ifndef SNAPKIT_TOPOLOGY_SNAP_KERNEL_CUH
#define SNAPKIT_TOPOLOGY_SNAP_KERNEL_CUH

/*
 * topology_snap_kernel.cuh — ADE root lattice snaps
 *
 * Batch kernels for all ADE topology snap functions:
 *   A₁ (binary), A₂ (Eisenstein), A₃ (tetrahedral),
 *   D₄ (triality), E₈ (exceptional)
 *
 * Each kernel processes N points in parallel, one per thread.
 * The batch dispatch route is handled at the host API level.
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "topology.cuh"

/* ======================================================================
 * A₁ Binary Snap Batch
 * ====================================================================== */

__global__ void snap_a1_batch_kernel(
    const float* __restrict__ points,    /* N x 1 */
    float* __restrict__ out_snapped,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        snap_binary_1d(points[idx], &out_snapped[idx], &out_delta[idx]);
    }
}

/* ======================================================================
 * A₂ Eisenstein Snap Batch
 * ====================================================================== */

__global__ void snap_a2_batch_kernel(
    const float* __restrict__ points_x,
    const float* __restrict__ points_y,
    float* __restrict__ out_x,
    float* __restrict__ out_y,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        int a, b;
        float delta;
        eisenstein_snap_point(points_x[idx], points_y[idx], &a, &b, &delta);
        out_x[idx] = a - b * 0.5f;
        out_y[idx] = b * SNAPKIT_EISENSTEIN_SQRT3 * 0.5f;
        out_delta[idx] = delta;
    }
}

/* ======================================================================
 * A₃ Tetrahedral Snap Batch
 * ====================================================================== */

__global__ void snap_a3_batch_kernel(
    const float* __restrict__ points_x,
    const float* __restrict__ points_y,
    const float* __restrict__ points_z,
    float* __restrict__ out_x,
    float* __restrict__ out_y,
    float* __restrict__ out_z,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        snap_tetrahedral_3d(
            points_x[idx], points_y[idx], points_z[idx],
            &out_x[idx], &out_y[idx], &out_z[idx],
            &out_delta[idx]
        );
    }
}

/* ======================================================================
 * D₄ Triality Snap Batch (4D)
 * ====================================================================== */

__global__ void snap_d4_batch_kernel(
    const float* __restrict__ points,
    float* __restrict__ out_snapped,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        const float* p = &points[idx * 4];
        float* o = &out_snapped[idx * 4];
        snap_d4_4d(p[0], p[1], p[2], p[3], o, &out_delta[idx]);
    }
}

/* ======================================================================
 * E₈ Exceptional Snap Batch (8D)
 * ====================================================================== */

__global__ void snap_e8_batch_kernel(
    const float* __restrict__ points,
    float* __restrict__ out_snapped,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        const float* p = &points[idx * 8];
        float* o = &out_snapped[idx * 8];
        snap_e8_8d(p, o, &out_delta[idx]);
    }
}

/* ======================================================================
 * Generic Topology Dispatch Kernel
 *
 * Routes each point to the appropriate topology snap.
 * All topologies return deltas; snapped coordinates are flattened.
 * ====================================================================== */

__global__ void topology_snap_dispatch_kernel(
    const float* __restrict__ points,      /* N x max_dim, row-major */
    int    dim,
    float* __restrict__ out_snapped,
    float* __restrict__ out_delta,
    int    N,
    snapkit_topology_t topology
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    const float* p = &points[idx * dim];
    float* o = &out_snapped[idx * dim];

    snap_to_topology(p, o, &out_delta[idx], dim, topology);
}

#endif /* SNAPKIT_TOPOLOGY_SNAP_KERNEL_CUH */
