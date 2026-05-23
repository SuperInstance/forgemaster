#ifndef EISENSTEIN_BRIDGE_H
#define EISENSTEIN_BRIDGE_H

#include <stdint.h>
#include <stddef.h>

/**
 * eisenstein_result_t — Compact Eisenstein snap result for SIMD consumption
 *
 * Packed into 8 bytes so 4 results fit in one zmm register (AVX-512).
 *
 * Layout (8 bytes):
 *   [0..3]  float error        — snap distance from nearest lattice point
 *   [4..5]  uint16_t dodecet   — 12-bit constraint state (nibble-packed)
 *            bits 0-3:  error level (0-15)
 *            bits 4-7:  angle level (0-15)
 *            bits 8-11: chamber (0-5, fits in 3 bits)
 *            bits 12-15: reserved
 *   [6]    uint8_t chamber     — Weyl chamber 0-5
 *   [7]    uint8_t flags       — bit0: is_safe, bit1: parity
 */
typedef struct __attribute__((packed, aligned(8))) {
    float    error;
    uint16_t dodecet;
    uint8_t  chamber;
    uint8_t  flags;
    int32_t  snap_a;     // Eisenstein a-coordinate of snapped point
    int32_t  snap_b;     // Eisenstein b-coordinate of snapped point
} eisenstein_result_t;

_Static_assert(sizeof(eisenstein_result_t) == 16,
    "eisenstein_result_t must be exactly 16 bytes for AVX-512 pairing");

/* flags bits */
#define EISENSTEIN_FLAG_SAFE    0x01
#define EISENSTEIN_FLAG_PARITY  0x02

/**
 * eisenstein_snap — Snap a point (x,y) to the nearest Eisenstein A₂ lattice point.
 *
 * The A₂ lattice is spanned by 1 and ω = e^{2πi/3} = (-1/2, √3/2).
 * The algorithm:
 *   1. Convert (x,y) to Eisenstein coordinates (a,b) where point = a + b*ω
 *   2. Round (a,b) to nearest integer pair — this gives the closest lattice point
 *   3. Compute error = distance from original point to snapped lattice point
 *   4. Encode error level, angle, and Weyl chamber into dodecet
 *
 * Returns: eisenstein_result_t with all fields populated.
 */
eisenstein_result_t eisenstein_snap(float x, float y);

/**
 * eisenstein_batch_snap — Snap N points in batch.
 *
 * For each input point (points[2*i], points[2*i+1]), computes the snap
 * and stores the result in results[i].
 *
 * @param points    Interleaved x,y pairs (length 2*n)
 * @param n         Number of points
 * @param results   Output array (length n), pre-allocated
 */
void eisenstein_batch_snap(
    const float *points,
    size_t n,
    eisenstein_result_t *results
);

/**
 * eisenstein_holonomy_4cycle — Check constraint consistency around a 4-cycle.
 *
 * Given 4 Eisenstein results (representing 4 tiles in a cycle),
 * computes the holonomy H = w0*w1 - w2*w3 where wi are the dodecet values
 * treated as edge weights.
 *
 * Returns: |H| normalized to [0, 1]. Closer to 0 = more consistent.
 */
float eisenstein_holonomy_4cycle(
    const eisenstein_result_t results[4]
);

/**
 * eisenstein_batch_holonomy — Check N 4-cycles in batch.
 *
 * @param results    Array of 4*N results (4 consecutive per cycle)
 * @param n          Number of 4-cycles
 * @param holonomy   Output array of N float holonomy values
 */
void eisenstein_batch_holonomy(
    const eisenstein_result_t *results,
    size_t n,
    float *holonomy
);

#endif /* EISENSTEIN_BRIDGE_H */
