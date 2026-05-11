/*
 * topology.cu — ADE topology snap function implementations
 *
 * Each ADE type defines a different snap function topology.
 * This file implements batch kernels for all supported topologies
 * and the generic dispatch function.
 *
 * "The topology is the INVARIANT that transfers across domains."
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"
#include "topology.cuh"
#include "kernels/topology_snap_kernel.cuh"

/* ======================================================================
 * Host API: Batch topology snap
 * ====================================================================== */

void snapkit_batch_topology_snap(
    const float* points,
    int    dim,
    float* out_snapped,
    float* out_deltas,
    int    N,
    snapkit_topology_t topology,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    /* Dispatch to appropriate kernel */
    switch (topology) {
        case SNAPKIT_ADE_A1: {
            snap_a1_batch_kernel<<<grid_size, block_size, 0, stream>>>(
                points, out_snapped, out_deltas, N
            );
            break;
        }
        case SNAPKIT_ADE_A2: {
            /* A₂ is 2D — use separate x,y buffers */
            /* The caller provides points as flat [x1,y1,x2,y2,...] */
            /* But for A₂ we have eisenstein_snap which handles SoA */
            /* Fall through to dispatch in case of SoA layout */
            topology_snap_dispatch_kernel<<<grid_size, block_size, 0, stream>>>(
                points, dim, out_snapped, out_deltas, N, topology
            );
            break;
        }
        case SNAPKIT_ADE_A3: {
            /* 3D tetrahedral */
            /* For SoA layout, use the 3D kernel. For generic, use dispatch */
            topology_snap_dispatch_kernel<<<grid_size, block_size, 0, stream>>>(
                points, dim, out_snapped, out_deltas, N, topology
            );
            break;
        }
        case SNAPKIT_ADE_D4: {
            snap_d4_batch_kernel<<<grid_size, block_size, 0, stream>>>(
                points, out_snapped, out_deltas, N
            );
            break;
        }
        case SNAPKIT_ADE_E8: {
            snap_e8_batch_kernel<<<grid_size, block_size, 0, stream>>>(
                points, out_snapped, out_deltas, N
            );
            break;
        }
        default: {
            /* Default to A₂ dispatch */
            topology_snap_dispatch_kernel<<<grid_size, block_size, 0, stream>>>(
                points, dim, out_snapped, out_deltas, N, topology
            );
            break;
        }
    }

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Snap A₁ binary (1D)
 * ====================================================================== */

void snapkit_snap_a1(
    const float* points,
    float* out_snapped,
    float* out_deltas,
    int    N,
    cudaStream_t stream
) {
    snapkit_batch_topology_snap(points, 1, out_snapped, out_deltas,
                                 N, SNAPKIT_ADE_A1, stream);
}

/* ======================================================================
 * Host API: Snap A₃ tetrahedral (3D, SoA)
 * ====================================================================== */

void snapkit_snap_a3(
    const float* points_x,
    const float* points_y,
    const float* points_z,
    float* out_x,
    float* out_y,
    float* out_z,
    float* out_deltas,
    int    N,
    cudaStream_t stream
) {
    if (N <= 0) return;

    int block_size = 256;
    int grid_size  = (N + block_size - 1) / block_size;
    grid_size = min(grid_size, 65535);

    snap_a3_batch_kernel<<<grid_size, block_size, 0, stream>>>(
        points_x, points_y, points_z,
        out_x, out_y, out_z, out_deltas, N
    );

#ifdef CUDA_CHECK
    CUDA_SAFE_CALL(cudaGetLastError());
#endif
}

/* ======================================================================
 * Host API: Snap D₄ (4D, interleaved)
 * ====================================================================== */

void snapkit_snap_d4(
    const float* points,
    float* out_snapped,
    float* out_deltas,
    int    N,
    cudaStream_t stream
) {
    snapkit_batch_topology_snap(points, 4, out_snapped, out_deltas,
                                 N, SNAPKIT_ADE_D4, stream);
}

/* ======================================================================
 * Host API: Snap E₈ (8D, interleaved)
 * ====================================================================== */

void snapkit_snap_e8(
    const float* points,
    float* out_snapped,
    float* out_deltas,
    int    N,
    cudaStream_t stream
) {
    snapkit_batch_topology_snap(points, 8, out_snapped, out_deltas,
                                 N, SNAPKIT_ADE_E8, stream);
}

/* ======================================================================
 * Host API: Topology name utility
 * ====================================================================== */

const char* snapkit_topology_name(snapkit_topology_t topology) {
    switch (topology) {
        case SNAPKIT_ADE_A1:  return "A₁ (binary)";
        case SNAPKIT_ADE_A2:  return "A₂ (Eisenstein/hexagonal)";
        case SNAPKIT_ADE_A3:  return "A₃ (tetrahedral)";
        case SNAPKIT_ADE_D4:  return "D₄ (triality)";
        case SNAPKIT_ADE_E6:  return "E₆ (tetrahedral group)";
        case SNAPKIT_ADE_E7:  return "E₇ (octahedral group)";
        case SNAPKIT_ADE_E8:  return "E₈ (icosahedral group)";
        case SNAPKIT_ADE_CUBIC: return "Cubic (ℤⁿ)";
        default:              return "Unknown";
    }
}
