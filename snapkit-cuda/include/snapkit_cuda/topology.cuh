#ifndef SNAPKIT_TOPOLOGY_CUH
#define SNAPKIT_TOPOLOGY_CUH

/*
 * topology.cuh — ADE topology snap functions
 *
 * The ADE classification is the "periodic table of snap topologies" —
 * a finite classification of fundamental shapes that uncertainty can take.
 *
 * Each ADE type defines a different snap function topology:
 *   A₁: Binary snap (coin flip)
 *   A₂: Eisenstein / hexagonal (densest 2D, PID property)
 *   A₃: Tetrahedral (3D, 4 categories)
 *   D₄: Triality (4D, forked dependencies)
 *   E₆, E₇, E₈: Exceptional groups (maximum symmetries)
 *
 * The topology is the INVARIANT that transfers across domains.
 */

#include <cuda_runtime.h>
#include "snapkit_cuda.h"

/* ======================================================================
 * A₁ — Binary Snap
 *
 * Snaps to the closest of two values: {+1, -1}.
 * The simplest snap: coin flip, true/false, yes/no.
 * ====================================================================== */

__device__ __forceinline__
void snap_binary_1d(
    float value,
    float* out_snapped,
    float* out_delta
) {
    float snapped = (value >= 0.0f) ? 1.0f : -1.0f;
    *out_snapped = snapped;
    *out_delta = fabsf(value - snapped);
}

/* ======================================================================
 * A₂ — Eisenstein Hexagonal Snap (already defined in eisenstein_snap.cuh)
 * ====================================================================== */

/* Refer to eisenstein_snap_point in eisenstein_snap.cuh */

/* ======================================================================
 * A₃ — Tetrahedral Snap
 *
 * Snaps a 3D unit vector to the nearest tetrahedron vertex.
 * The tetrahedron vertices are the 4 permutations of (±1, ±1, ±1)
 * with even number of minus signs.
 *
 * Tetrahedron vertices (normalized):
 *   v₀ = ( 1,  1,  1) / √3
 *   v₁ = ( 1, -1, -1) / √3
 *   v₂ = (-1,  1, -1) / √3
 *   v₃ = (-1, -1,  1) / √3
 * ====================================================================== */

__device__ __forceinline__
void snap_tetrahedral_3d(
    float x, float y, float z,
    float* out_x, float* out_y, float* out_z,
    float* out_delta
) {
    /* Dot products with 4 tetrahedron vertices */
    float d0 =  x + y + z;   /* v₀ · (x,y,z) = (1,1,1) · (x,y,z) */
    float d1 =  x - y - z;   /* v₁ · (x,y,z) = (1,-1,-1) · (x,y,z) */
    float d2 = -x + y - z;   /* v₂ · (x,y,z) = (-1,1,-1) · (x,y,z) */
    float d3 = -x - y + z;   /* v₃ · (x,y,z) = (-1,-1,1) · (x,y,z) */

    /* Find max dot product */
    float max_d = d0;
    int   best  = 0;

    if (d1 > max_d) { max_d = d1; best = 1; }
    if (d2 > max_d) { max_d = d2; best = 2; }
    if (d3 > max_d) { max_d = d3; best = 3; }

    /* Snap to selected vertex (not normalized — magnitude preserved) */
    float inv_sqrt3 = 0.5773502691896258f;
    float norm = sqrtf(x*x + y*y + z*z);
    float mag  = fmaxf(norm, 1e-12f);

    switch (best) {
        case 0: *out_x = mag * inv_sqrt3; *out_y = mag * inv_sqrt3; *out_z = mag * inv_sqrt3; break;
        case 1: *out_x = mag * inv_sqrt3; *out_y = -mag * inv_sqrt3; *out_z = -mag * inv_sqrt3; break;
        case 2: *out_x = -mag * inv_sqrt3; *out_y = mag * inv_sqrt3; *out_z = -mag * inv_sqrt3; break;
        case 3: *out_x = -mag * inv_sqrt3; *out_y = -mag * inv_sqrt3; *out_z = mag * inv_sqrt3; break;
    }

    float dx = x - *out_x;
    float dy = y - *out_y;
    float dz = z - *out_z;
    *out_delta = sqrtf(dx*dx + dy*dy + dz*dz);
}

/* ======================================================================
 * D₄ — Triality Snap (4D)
 *
 * D₄ root system: 24 roots in 4D. The simple roots are:
 *   α₁ = (1, -1, 0, 0)
 *   α₂ = (0, 1, -1, 0)
 *   α₃ = (0, 0, 1, -1)
 *   α₄ = (0, 0, 1, 1)
 *
 * D₄ has triality symmetry: the 3 leaves are permutable.
 * ====================================================================== */

__device__ __forceinline__
void snap_d4_4d(
    float x, float y, float z, float w,
    float* out_vals,
    float* out_delta
) {
    /* Project to D₄ root coordinates */
    /* D₄ has 24 roots: all (±1, ±1, 0, 0) permutations */
    /* We snap to nearest root set by rounding in D₄ basis */

    float a1 = x - y;   /* α₁ */
    float a2 = y - z;   /* α₂ */
    float a3 = z - w;   /* α₃ */
    float a4 = z + w;   /* α₄ */

    /* Round to nearest integer roots */
    int r1 = __float2int_rn(a1);
    int r2 = __float2int_rn(a2);
    int r3 = __float2int_rn(a3);
    int r4 = __float2int_rn(a4);

    /* Check parity condition for D₄: sum of coordinates must be even */
    int parity = (r1 + r4) & 1;
    if (parity) {
        /* Adjust nearest root to fix parity */
        float e1 = a1 - r1;
        float e2 = a2 - r2;
        float e3 = a3 - r3;
        float e4 = a4 - r4;

        float min_err = fminf(fminf(fabsf(e1), fabsf(e2)), fminf(fabsf(e3), fabsf(e4)));

        if (min_err == fabsf(e1)) r1 += (e1 > 0) ? 1 : -1;
        else if (min_err == fabsf(e2)) r2 += (e2 > 0) ? 1 : -1;
        else if (min_err == fabsf(e3)) r3 += (e3 > 0) ? 1 : -1;
        else r4 += (e4 > 0) ? 1 : -1;
    }

    /* Convert back to ambient coordinates */
    /* x = (a1 + a2 + a3 + a4) / 4 → approximate from roots */
    float sx, sy, sz, sw;

    /* We need to solve the inverse basis. For D₄ in our representation: */
    /* α = (x-y, y-z, z-w, z+w) */
    /* This gives: x = (α₁ + α₂ + α₃ + α₄) / 2 */
    /*              y = (-α₁ + α₂ + α₃ + α₄) / 2 */
    /*              z = (-α₂ + α₃ + α₄) / 2 */
    /*              w = (-α₃ + α₄) / 2 */

    float sum_r = (float)(r1 + r2 + r3 + r4) * 0.5f;
    sx = sum_r;
    sy = (-r1 + r2 + r3 + r4) * 0.5f;
    sz = (-r2 + r3 + r4) * 0.5f;
    sw = (-r3 + r4) * 0.5f;

    out_vals[0] = sx;
    out_vals[1] = sy;
    out_vals[2] = sz;
    out_vals[3] = sw;

    float dx = x - sx;
    float dy = y - sy;
    float dz = z - sz;
    float dw = w - sw;
    *out_delta = sqrtf(dx*dx + dy*dy + dz*dz + dw*dw);
}

/* ======================================================================
 * E₈ — Exceptional Snap (8D)
 *
 * E₈ is the largest exceptional Lie group: 240 roots in 8D.
 * The roots are:
 *   (±1, ±1, 0, 0, 0, 0, 0, 0) — all permutations (112 roots)
 *   (±½, ±½, ±½, ±½, ±½, ±½, ±½, ±½) with even number of minus signs (128 roots)
 *
 * E₈ has the highest symmetry and finest angular resolution.
 * ====================================================================== */

__device__ __forceinline__
void snap_e8_8d(
    const float* in_vals,
    float* out_vals,
    float* out_delta
) {
    /* Step 1: Snap to ℤ⁸ shifted by (½, ½, ½, ½, ½, ½, ½, ½) */
    float half_sum = 0.0f;
    #pragma unroll
    for (int i = 0; i < 8; i++) {
        half_sum += in_vals[i];
    }

    /* Two lattice candidates: ℤ⁸ and ℤ⁸ + (½)⁸ */
    /* Round each coordinate to nearest integer */
    int   int_candidate[8], half_candidate[8];
    float int_dist2 = 0.0f, half_dist2 = 0.0f;

    #pragma unroll
    for (int i = 0; i < 8; i++) {
        float vi = in_vals[i];

        /* Candidate 1: nearest integer */
        int r1 = __float2int_rn(vi);
        int_candidate[i] = r1;
        float d1 = vi - (float)r1;
        int_dist2 += d1 * d1;

        /* Candidate 2: nearest half-integer */
        float vh = vi - 0.5f;
        int r2 = __float2int_rn(vh);
        half_candidate[i] = r2 + 1;  /* because we subtracted 0.5 */
        float d2 = vi - ((float)r2 + 0.5f);
        half_dist2 += d2 * d2;
    }

    /* Also need parity condition for the ℤ⁸ candidate */
    /* E₈ requires sum of coordinates be even for ℤ⁸ part */
    int int_sum = 0;
    #pragma unroll
    for (int i = 0; i < 8; i++) int_sum += int_candidate[i];
    int_sum = int_sum & 1;  /* parity of sum */

    if (int_sum) {
        /* Flip the coordinate with largest rounding error */
        int  worst_idx = 0;
        float worst_err = 0.0f;
        for (int i = 0; i < 8; i++) {
            float err = fabsf(in_vals[i] - (float)int_candidate[i]);
            if (err > worst_err) {
                worst_err = err;
                worst_idx = i;
            }
        }
        /* Flip: add ±1 to minimize increase in distance */
        float flipped = in_vals[worst_idx] - (float)(int_candidate[worst_idx] + 1);
        float alt = in_vals[worst_idx] - (float)(int_candidate[worst_idx] - 1);
        int_dist2 -= worst_err * worst_err;
        int_dist2 += fminf(flipped * flipped, alt * alt);
        int_candidate[worst_idx] += (fabsf(flipped) < fabsf(alt)) ? 1 : -1;
    }

    /* Choose the closer candidate */
    if (int_dist2 <= half_dist2) {
        #pragma unroll
        for (int i = 0; i < 8; i++) {
            out_vals[i] = (float)int_candidate[i];
        }
        *out_delta = sqrtf(int_dist2);
    } else {
        #pragma unroll
        for (int i = 0; i < 8; i++) {
            out_vals[i] = (float)half_candidate[i];
        }
        *out_delta = sqrtf(half_dist2);
    }
}

/* ======================================================================
 * Generic Topology Snap Dispatch
 *
 * Routes to the appropriate snap function based on topology type.
 * ====================================================================== */

__device__ void snap_to_topology(
    const float* point,
    float* out_snapped,
    float* out_delta,
    int    dim,
    snapkit_topology_t topology
) {
    switch (topology) {
        case SNAPKIT_ADE_A1: {
            /* 1D binary */
            snap_binary_1d(point[0], &out_snapped[0], out_delta);
            break;
        }
        case SNAPKIT_ADE_A2: {
            /* 2D Eisenstein — need x, y */
            int a, b;
            eisenstein_snap_point(point[0], point[1], &a, &b, out_delta);
            out_snapped[0] = a - b * 0.5f;
            out_snapped[1] = b * SNAPKIT_EISENSTEIN_SQRT3 * 0.5f;
            break;
        }
        case SNAPKIT_ADE_A3: {
            /* 3D tetrahedral */
            snap_tetrahedral_3d(point[0], point[1], point[2],
                               &out_snapped[0], &out_snapped[1], &out_snapped[2],
                               out_delta);
            break;
        }
        case SNAPKIT_ADE_D4: {
            /* 4D D₄ */
            snap_d4_4d(point[0], point[1], point[2], point[3],
                      out_snapped, out_delta);
            break;
        }
        case SNAPKIT_ADE_E8: {
            /* 8D E₈ */
            snap_e8_8d(point, out_snapped, out_delta);
            break;
        }
        default: {
            /* Default to A₂ / Eisenstein */
            int a, b;
            eisenstein_snap_point(point[0], point[1], &a, &b, out_delta);
            out_snapped[0] = a - b * 0.5f;
            out_snapped[1] = b * SNAPKIT_EISENSTEIN_SQRT3 * 0.5f;
            break;
        }
    }
}

#endif /* SNAPKIT_TOPOLOGY_CUH */
