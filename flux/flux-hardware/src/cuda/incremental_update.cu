/**
 * FLUX Incremental Bounds Update Kernel — Scatter Update
 *
 * Updates only changed constraint sets in the flat bounds array.
 * This avoids re-uploading the entire bounds array when only a few constraints change.
 *
 * Design: one thread per update, scatter-write to flat_bounds at indices[i] * 8.
 */

#include <cstdint>

/**
 * Update n_updates constraint sets in-place.
 *
 * @param bounds      Flat bounds array [n_constraint_sets * 8]
 * @param new_bounds  New bounds data [n_updates * 8] — the replacement values
 * @param indices     Which constraint sets to update [n_updates]
 * @param n_updates   Number of constraint sets to update
 */
__global__ void flux_update_bounds_kernel(
    unsigned char*       __restrict__ bounds,
    const unsigned char* __restrict__ new_bounds,
    const int*           __restrict__ indices,
    int n_updates)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;

    if (idx < n_updates) {
        int set_idx = indices[idx];
        unsigned char* dst = &bounds[set_idx * 8];
        const unsigned char* src = &new_bounds[idx * 8];

        // Coalesced 8-byte write — fits in a single cache line
        dst[0] = src[0];
        dst[1] = src[1];
        dst[2] = src[2];
        dst[3] = src[3];
        dst[4] = src[4];
        dst[5] = src[5];
        dst[6] = src[6];
        dst[7] = src[7];
    }
}

/**
 * Convenience wrapper for the update kernel.
 */
extern "C" void launch_flux_update_bounds(
    unsigned char*       bounds,
    const unsigned char* new_bounds,
    const int*           indices,
    int n_updates,
    cudaStream_t stream)
{
    const int BLOCK_SIZE = 256;
    int grid = (n_updates + BLOCK_SIZE - 1) / BLOCK_SIZE;

    flux_update_bounds_kernel<<<grid, BLOCK_SIZE, 0, stream>>>(
        bounds, new_bounds, indices, n_updates);
}
