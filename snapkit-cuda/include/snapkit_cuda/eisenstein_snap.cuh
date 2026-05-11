#ifndef SNAPKIT_EISENSTEIN_SNAP_CUH
#define SNAPKIT_EISENSTEIN_SNAP_CUH

/*
 * eisenstein_snap.cuh — GPU Eisenstein lattice snap functions
 *
 * The Eisenstein lattice ℤ[ω] (A₂ root lattice) provides:
 * - Densest packing in 2D (maximum information per snap)
 * - Isotropic snap (no directional bias)  
 * - PID property → H¹ = 0 guarantee (no obstructions to composition)
 * - 6-fold symmetry (hexagonal attention field)
 *
 * Core formula:
 *   x + y*i  →  a + b*ω,  ω = (-1 + √3 i)/2
 *   x = a - b/2,  y = b*√3/2
 *   b = round(2y/√3),  a = round(x + b/2)
 *
 * See: SNAPS-AS-ATTENTION.md
 */

#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <math.h>
#include "snapkit_cuda.h"

/* ======================================================================
 * Device Constants
 * ====================================================================== */

__constant__ float snapkit_eisenstein_sqrt3  = SNAPKIT_EISENSTEIN_SQRT3;
__constant__ float snapkit_eisenstein_inv_s3 = SNAPKIT_EISENSTEIN_INV_SQRT3;
__constant__ float snapkit_eisenstein_tolerance = 0.1f;

/* ======================================================================
 * Core Snap: Single Point to Eisenstein Lattice
 *
 * Each thread: one snap, O(1), no divergence.
 * Uses PTX intrinsics for hardware rounding and FMA.
 * ====================================================================== */

__device__ __forceinline__
void eisenstein_snap_point(
    const float x,
    const float y,
    int* out_a,
    int* out_b,
    float* out_delta
) {
    /* ---- Step 1: Convert (x,y) to lattice coordinates ---- */
    /* b = round(2y / √3)  — using PTX cvt.rni for hardware rounding */
    float b_f = y * (2.0f * __frcp_rn(SNAPKIT_EISENSTEIN_SQRT3));
    int b;

    /* PTX: cvt.rni.s32.f32 — round-to-nearest-even hardware instruction */
    asm volatile("cvt.rni.s32.f32 %0, %1;" : "=r"(b) : "f"(b_f));

    /* a = round(x + b/2) — using FMA for precision */
    float a_f;
    asm volatile("fma.rn.f32 %0, %1, %2, %3;"
                 : "=f"(a_f)
                 : "f"((float)b), "f"(0.5f), "f"(x));

    int a;
    asm volatile("cvt.rni.s32.f32 %0, %1;" : "=r"(a) : "f"(a_f));

    /* ---- Step 2: Compute snapped point coordinates ---- */
    /* snap_x = a - b/2, snap_y = b * √3 / 2 */
    float snap_x, snap_y;

    /* snap_y = b * (√3/2) */
    asm volatile("mul.f32 %0, %1, %2;"
                 : "=f"(snap_y)
                 : "f"((float)b), "f"(SNAPKIT_EISENSTEIN_SQRT3 * 0.5f));

    /* snap_x = a - b/2 */
    float half_b;
    asm volatile("mul.f32 %0, %1, %2;"
                 : "=f"(half_b)
                 : "f"((float)b), "f"(0.5f));
    snap_x = a - half_b;

    /* ---- Step 3: Compute delta (distance from original) ---- */
    float dx = x - snap_x;
    float dy = y - snap_y;

    /* delta = sqrt(dx² + dy²)  — using FMA for dx² and dy² */
    float dx2, dy2;
    asm volatile("fma.rn.f32 %0, %1, %1, %2;"
                 : "=f"(dx2)
                 : "f"(dx), "f"(0.0f));
    asm volatile("fma.rn.f32 %0, %1, %1, %2;"
                 : "=f"(dy2)
                 : "f"(dy), "f"(0.0f));

    *out_delta = sqrtf(dx2 + dy2);
    *out_a = a;
    *out_b = b;
}

/* ======================================================================
 * PTX-Optimized Snap with Reduced Precision (fast path)
 *
 * For use when FP32 precision is acceptable but latency-critical.
 * Uses __fsqrt_rn for fast inverse square root.
 * ====================================================================== */

__device__ __forceinline__
void eisenstein_snap_fast(
    const float x,
    const float y,
    int* out_a,
    int* out_b,
    float* out_delta
) {
    int b = __float2int_rn(y * (2.0f / SNAPKIT_EISENSTEIN_SQRT3));
    int a = __float2int_rn(x + b * 0.5f);

    float snap_x = __fmaf_rn(-0.5f, (float)b, (float)a);
    float snap_y = (float)b * (SNAPKIT_EISENSTEIN_SQRT3 * 0.5f);

    float dx = x - snap_x;
    float dy = y - snap_y;
    float dist2 = __fmaf_rn(dx, dx, dy * dy);
    *out_delta = __fsqrt_rn(dist2);
    *out_a = a;
    *out_b = b;
}

/* ======================================================================
 * Batch Snap Kernel
 *
 * Process N (x,y) points in parallel, one per thread.
 * SoA layout ensures coalesced memory access.
 * ====================================================================== */

__global__ void eisenstein_snap_batch_kernel(
    const float* __restrict__ points_x,
    const float* __restrict__ points_y,
    int*  __restrict__ out_a,
    int*  __restrict__ out_b,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        float x = points_x[idx];
        float y = points_y[idx];
        eisenstein_snap_point(x, y, &out_a[idx], &out_b[idx], &out_delta[idx]);
    }
}

/* ======================================================================
 * Batch Snap Kernel — Fast Path (uses eisenstein_snap_fast)
 * ====================================================================== */

__global__ void eisenstein_snap_batch_fast_kernel(
    const float* __restrict__ points_x,
    const float* __restrict__ points_y,
    int*  __restrict__ out_a,
    int*  __restrict__ out_b,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        float x = points_x[idx];
        float y = points_y[idx];
        eisenstein_snap_fast(x, y, &out_a[idx], &out_b[idx], &out_delta[idx]);
    }
}

/* ======================================================================
 * Batch Snap Kernel — FP16 Input (for half-precision throughput)
 *
 * Input in FP16 halves, output in FP32. Doubles throughput on
 * hardware with FP16 tensor core support.
 * ====================================================================== */

__global__ void eisenstein_snap_batch_fp16_kernel(
    const half* __restrict__ points_x,
    const half* __restrict__ points_y,
    int*  __restrict__ out_a,
    int*  __restrict__ out_b,
    float* __restrict__ out_delta,
    int    N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        float x = __half2float(points_x[idx]);
        float y = __half2float(points_y[idx]);
        eisenstein_snap_fast(x, y, &out_a[idx], &out_b[idx], &out_delta[idx]);
    }
}

/* ======================================================================
 * Helper: Check if a lattice point is valid Eisenstein
 * (for debugging / correctness verification)
 * ====================================================================== */

__device__ __forceinline__
int eisenstein_check_lattice(int a, int b) {
    /* All (a,b) ∈ ℤ² are valid Eisenstein lattice points */
    return 1;
}

/* ======================================================================
 * Helper: Snap point and return snapped coordinates
 * ====================================================================== */

__device__ __forceinline__
void eisenstein_snap_to_coords(
    float x, float y,
    float* snap_x, float* snap_y
) {
    int a, b;
    float delta;
    eisenstein_snap_point(x, y, &a, &b, &delta);
    *snap_x = a - b * 0.5f;
    *snap_y = b * SNAPKIT_EISENSTEIN_SQRT3 * 0.5f;
}

#endif /* SNAPKIT_EISENSTEIN_SNAP_CUH */
