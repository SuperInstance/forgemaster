/**
 * spectral_integrity_kernel.h — Spectral First Integral I(x) = γ + H
 *
 * Real-time INT8 conservation tracker for PLATO rooms.
 * Monitors spectral shape stability of tanh-coupled nonlinear dynamics.
 *
 * Theory: I(x) = spectral_gap + participation_entropy is conserved
 * along trajectories of x_{t+1} = tanh(C(x) · x), with CV ≈ 0.0003.
 * Substrate-invariant — works in INT8 fixed-point.
 *
 * Forgemaster ⚒️ | 2026-05-17 | Cocapn Fleet
 * Reference: MATH-SPECTRAL-FIRST-INTEGRAL.md
 */

#ifndef SPECTRAL_INTEGRITY_KERNEL_H
#define SPECTRAL_INTEGRITY_KERNEL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/*  Compile-time configuration                                        */
/* ------------------------------------------------------------------ */

#ifndef SIK_MAX_DIM
#define SIK_MAX_DIM       32     /* max state dimension N              */
#endif

#ifndef SIK_POWER_ITERS
#define SIK_POWER_ITERS   8      /* power-iteration count (5–10)       */
#endif

#ifndef SIK_RING_SIZE
#define SIK_RING_SIZE     64     /* CV ring-buffer depth                */
#endif

#ifndef SIK_Q            /* fixed-point Q format: Q15.16 */
#define SIK_Q             16
#endif

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

/** Alert levels for the conservation monitor */
typedef enum {
    SIK_ALERT_NONE       = 0,    /* CV well below threshold            */
    SIK_ALERT_WARNING    = 1,    /* CV approaching threshold           */
    SIK_ALERT_CHOP       = 2     /* CV exceeded — spectral shape broke */
} sik_alert_t;

/** Status returned by spectral_integrity_status() */
typedef struct {
    int32_t  I_current;          /* current I(x) in Q format           */
    int32_t  I_mean;             /* running mean of I                  */
    int32_t  I_std;              /* running std dev of I               */
    uint32_t cv_q16;             /* CV × 65536 (≈ CV in Q16)          */
    uint32_t step_count;         /* total steps processed              */
    sik_alert_t alert;           /* current alert level                */
    int32_t  lambda1;            /* top eigenvalue estimate (Q format) */
    int32_t  lambda2;            /* 2nd eigenvalue estimate (Q)        */
    int32_t  gamma;              /* spectral gap λ1 - λ2 (Q)           */
    int32_t  entropy;            /* participation entropy H (Q)        */
} sik_status_t;

/** Per-instance state (stack-allocated, no malloc) */
typedef struct {
    /* configuration */
    uint16_t N;                  /* actual state dimension (≤ SIK_MAX_DIM) */
    uint16_t ring_mask;          /* SIK_RING_SIZE - 1 (must be pow2)  */
    uint32_t cv_threshold_q16;   /* alert threshold × 65536            */

    /* eigenvector estimates for power iteration */
    int32_t  v1[SIK_MAX_DIM];   /* dominant eigenvector (Q)           */
    int32_t  v2[SIK_MAX_DIM];   /* 2nd eigenvector estimate (Q)      */

    /* ring buffer for CV computation */
    int32_t  ring[SIK_RING_SIZE];
    uint32_t ring_head;
    uint32_t ring_count;

    /* running accumulators for mean/std */
    int64_t  sum_I;              /* sum of all I values                */
    int64_t  sum_I2;             /* sum of I² values                   */

    /* step counter */
    uint32_t step_count;

    /* latest computed values */
    int32_t  last_I;
    int32_t  last_gamma;
    int32_t  last_entropy;
    int32_t  last_lambda1;
    int32_t  last_lambda2;
} sik_state_t;

/* ------------------------------------------------------------------ */
/*  Public API                                                         */
/* ------------------------------------------------------------------ */

/**
 * Initialize the spectral integrity monitor.
 *
 * @param state    Pre-allocated state struct (stack or static).
 * @param N        State dimension (2..SIK_MAX_DIM).
 * @param cv_thresh  CV alert threshold, e.g. 0.01 → 10 (×65536 → 655).
 *                   Stored as cv_threshold_q16 = cv_thresh × 65536.
 */
void spectral_integrity_init(sik_state_t *state, uint16_t N, uint16_t cv_thresh_hundredths);

/**
 * Process one timestep: apply coupling, compute I(x), update tracker.
 *
 * @param state     Initialized state.
 * @param state_vec Current state vector x_t, INT8 values [-127,127].
 * @param coupling  Coupling matrix C(x), INT8 row-major, N×N.
 *                  For state-dependent C, caller computes C(x_t) first.
 * @return          Current alert level.
 *
 * Side effects: updates all internal trackers, ring buffer, CV estimate.
 */
sik_alert_t spectral_integrity_step(sik_state_t *state,
                                    const int8_t *state_vec,
                                    const int8_t *coupling);

/**
 * Query current status without advancing the state.
 *
 * @param state  Initialized state.
 * @param out    Filled with current metrics.
 */
void spectral_integrity_status(const sik_state_t *state, sik_status_t *out);

/* ------------------------------------------------------------------ */
/*  Utility helpers (public for testing)                               */
/* ------------------------------------------------------------------ */

/** INT8 tanh: input raw INT8, output tanh(x) as INT8 via 256-entry LUT. */
int8_t sik_tanh_lut(int8_t x);

/** Saturating INT8 × INT8 → INT32 (no overflow). */
static inline int32_t sik_mul_q7(int8_t a, int8_t b) {
    return ((int32_t)a) * ((int32_t)b);
}

/** INT8 matrix-vector multiply: out[i] = saturating Σ A[i][j] * x[j]. */
void sik_matvec(const int8_t *A, const int8_t *x, int32_t *out, uint16_t N);

#ifdef __cplusplus
}
#endif

#endif /* SPECTRAL_INTEGRITY_KERNEL_H */
