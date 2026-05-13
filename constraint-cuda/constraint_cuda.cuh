/**
 * constraint_cuda.cuh — Production CUDA header for Eisenstein constraint checking
 *
 * Single-include header providing:
 *   - Device functions callable from user kernels
 *   - Host-side launch wrappers with configurable block/grid sizes
 *   - Error checking macros
 *
 * Supports 5 constraint-checking operations:
 *   1. Eisenstein snap      — float2 → nearest lattice point + distance
 *   2. Dodecet encode       — int2 lattice → 12-bit dodecet code
 *   3. Constraint check     — float2 query → member? (3-tier)
 *   4. Holonomy batch       — K cycles of length L → holonomy values
 *   5. Cyclotomic rotation  — Apply Q(ζ₁₅) rotation via FP32 RN arithmetic
 *
 * Compile with: nvcc -O3 -arch=sm_86 -std=c++14 ...
 * Fat binary:    nvcc -O3 -gencode arch=compute_70,code=sm_70 \
 *                              -gencode arch=compute_75,code=sm_75 \
 *                              -gencode arch=compute_80,code=sm_80 \
 *                              -gencode arch=compute_86,code=sm_86
 *
 * Target GPU: RTX 4050 Laptop (compute capability 8.6, sm_86)
 *
 * Usage:
 *   #include "constraint_cuda.cuh"
 *   // call device functions from kernels, use launch wrappers from host
 */

#ifndef CONSTRAINT_CUDA_CUH
#define CONSTRAINT_CUDA_CUH

#include <cuda_runtime.h>
#include <vector_types.h>
#include <cstdint>
#include <cmath>

// -----------------------------------------------------------------------
// Compile-time constants
// -----------------------------------------------------------------------
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#ifndef SQRT3
#define SQRT3 1.73205080756887729352
#endif

// -----------------------------------------------------------------------
// Error checking macro (host-side only)
// -----------------------------------------------------------------------
#ifndef CUDA_CHECK_HOST
#define CUDA_CHECK_HOST(call) do {                                      \
    cudaError_t err = call;                                             \
    if (err != cudaSuccess) {                                           \
        fprintf(stderr, "CUDA error %d at %s:%d: %s\n",                \
                err, __FILE__, __LINE__, cudaGetErrorString(err));      \
        exit(EXIT_FAILURE);                                             \
    }                                                                   \
} while(0)
#endif

#ifdef __cplusplus
extern "C" {
#endif

// -----------------------------------------------------------------------
// Host-side launch wrappers (declared extern, defined in constraint_cuda.cu)
// -----------------------------------------------------------------------

void launch_eisenstein_snap(
    const float2* d_points,
    float epsilon,
    int2* d_lattice,
    float* d_distances,
    int N,
    int block_size,
    cudaStream_t stream);

void launch_dodecet_encode(
    const int2* d_lattice,
    uint16_t* d_codes,
    int N,
    int block_size,
    cudaStream_t stream);

void launch_constraint_check(
    const float2* d_queries,
    const uint32_t* d_bitset,
    bool* d_results,
    float epsilon,
    int N,
    int block_size,
    cudaStream_t stream);

void launch_holonomy_batch(
    const float2* d_cycle_vertices,
    int K,
    int L,
    float* d_holonomy,
    float epsilon,
    cudaStream_t stream);

void launch_cyclotomic_rotation(
    const float2* d_input,
    float2* d_output,
    double theta,
    int N,
    int block_size,
    cudaStream_t stream);

#ifdef __cplusplus
} // extern "C"
#endif

// -----------------------------------------------------------------------
// Device functions — callable from user kernels
// -----------------------------------------------------------------------

/**
 * snap_to_eisenstein_lattice: Snap a float2 point to nearest Eisenstein lattice point.
 * Returns lattice coordinates (a,b) and Euclidean distance.
 *
 * The Eisenstein lattice Z[ω] has basis vectors:
 *   v1 = (1, 0)
 *   v2 = (1/2, √3/2)
 *
 * For a point (x,y):
 *   b = 2y/√3
 *   a = x - b/2
 *
 * Round (a,b) to nearest integers → lattice point in basis coordinates.
 * Euclidean distance = sqrt((a+b/2 - x)² + (b√3/2 - y)²)
 */
__device__ inline void snap_to_eisenstein_lattice(
    float2 p,
    int& a_out,
    int& b_out,
    float& dist_out)
{
    float sqrt3 = (float)SQRT3;
    float b_frac = 2.0f * p.y / sqrt3;
    float a_frac = p.x - 0.5f * b_frac;

    float a_round = rintf(a_frac);
    float b_round = rintf(b_frac);

    float dx = (a_round + 0.5f * b_round) - p.x;
    float dy = (0.5f * sqrt3 * b_round) - p.y;

    a_out = (int)a_round;
    b_out = (int)b_round;
    dist_out = sqrtf(dx * dx + dy * dy);
}

/**
 * dodecet_encode: Encode an Eisenstein lattice point to 12-bit dodecet code.
 *
 * The dodecagon has 12 sides, each spanning 30° of the circle.
 * Code layout:
 *   bits 0-3:  radial level (0-15, radius/2)
 *   bits 4-7:  sector (0-11, 30° sectors)
 *   bit  8:    even parity over bits 0-7
 *   bits 9-15: reserved
 */
__device__ inline uint16_t dodecet_encode(int a, int b)
{
    float x = (float)a + 0.5f * (float)b;
    float y = 0.5f * (float)SQRT3 * (float)b;

    // Compute angle in [0, 2π)
    float angle = atan2f(y, x);
    if (angle < 0.0f) angle += 2.0f * (float)M_PI;

    // Map to one of 12 sectors (30° each)
    int sector = (int)(angle / ((float)M_PI / 6.0f));
    if (sector >= 12) sector = 11;

    // Radial level: floor(radius/2), clamped to 0-15
    float r = sqrtf(x * x + y * y);
    int radial = (int)(r / 2.0f);
    if (radial > 15) radial = 15;

    // Assemble 8-bit code: [3:0] = radial, [7:4] = sector
    uint16_t code = (uint16_t)((radial & 0xF) | ((sector & 0xF) << 4));

    // Even parity over bits 0-7
    // Use popcount for efficiency: parity = __popc(code) & 1
    uint16_t parity = (uint16_t)(__popc(code) & 1U);
    // ^ corrected: __popc counts bits set to 1. Even parity means
    //   parity bit = 0 if popcount even, 1 if popcount odd.
    //   So parity = popc(code) & 1.

    return code | (parity << 8);
}

/**
 * check_dodecet_membership: O(1) lookup in constraint bitset.
 * Returns true if dodecet code is set in the 4096-bit constraint bitset.
 *
 * The bitset is an array of 128 uint32_t words (128*32 = 4096 bits).
 * A 12-bit code maps to word index = code >> 5, bit index = code & 0x1F.
 */
__device__ inline bool check_dodecet_membership(
    uint16_t code,
    const uint32_t* __restrict__ constraint_bitset)
{
    // Strip parity bit (bit 8) for lookup; only bits 0-7 are used
    uint16_t lookup_code = code & 0xFF;
    int word_idx = (lookup_code >> 5) & 0x7F;  // 0-127
    int bit_idx  = lookup_code & 0x1F;          // 0-31
    return (constraint_bitset[word_idx] >> bit_idx) & 1U;
}

/**
 * is_point_constrained: Full 3-tier constraint check for a single float2 query.
 *
 * Tier 1: Snap to lattice → encode → O(1) bitset lookup
 * Tier 2: If Tier 1 misses, check 8 neighboring lattice points
 * Tier 3: (placeholder for exact holonomy check)
 *
 * Returns true if the point (or any of its lattice neighbors) maps
 * to a dodecet code present in the constraint bitset.
 */
__device__ inline bool is_point_constrained(
    float2 p,
    const uint32_t* __restrict__ constraint_bitset)
{
    // --- Tier 1 ---
    int a, b;
    float dist;
    snap_to_eisenstein_lattice(p, a, b, dist);
    uint16_t code = dodecet_encode(a, b);

    if (check_dodecet_membership(code, constraint_bitset)) {
        return true;
    }

    // --- Tier 2: neighborhood expansion ---
    // Check 8 neighbors in the triangular lattice
    // Neighbor offsets in lattice basis coordinates
    static const int neigh_da[8] = {1, 0, -1, -1, 0, 1, 1, -1};
    static const int neigh_db[8] = {0, 1, 1, 0, -1, -1, 1, -1};

    for (int ni = 0; ni < 8; ni++) {
        int na = a + neigh_da[ni];
        int nb = b + neigh_db[ni];
        uint16_t ncode = dodecet_encode(na, nb);
        if (check_dodecet_membership(ncode, constraint_bitset)) {
            return true;
        }
    }

    return false;
}

/**
 * apply_cyclotomic_rotation: Apply rotation by theta using RN FP32 arithmetic.
 *
 * Uses __fmul_rn (round-to-nearest-even multiply) and __fadd_rn
 * (round-to-nearest-even add) for deterministic IEEE 754 arithmetic
 * across GPU generations.
 *
 * The rotation matrix is:
 *   [cos θ  -sin θ]
 *   [sin θ   cos θ]
 *
 * Returns the rotated point.
 */
__device__ inline float2 apply_cyclotomic_rotation(float2 p, float cos_theta, float sin_theta)
{
    float2 result;
    result.x = __fadd_rn(__fmul_rn(p.x, cos_theta), __fmul_rn(-p.y, sin_theta));
    result.y = __fadd_rn(__fmul_rn(p.x, sin_theta), __fmul_rn(p.y, cos_theta));
    return result;
}

#endif // CONSTRAINT_CUDA_CUH
