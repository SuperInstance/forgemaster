/*
 * sonar_vision.h — SonarVision Public C API
 *
 * Real-time underwater acoustic physics engine.
 * C99 + CUDA, targeting Jetson Xavier (sm_72).
 *
 * Physics models:
 *   Sound speed:     Mackenzie 1981  (JASA 70(3), 1981)
 *   Absorption:      Francois-Garrison 1982  (JASA 72(6), 1982)
 *   Ray tracing:     Snell's law, constant-gradient layers
 *   Sonar equation:  Signal excess with Rice detection model
 *   Reverberation:   Volume / surface / bottom (Lambert's law)
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 SuperInstance
 */

#ifndef SONAR_VISION_H
#define SONAR_VISION_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Error codes ─────────────────────────────────────────────────── */

typedef enum sv_error {
    SV_OK              = 0,
    SV_ERR_TEMP_RANGE  = -1,   /* temperature outside -2..30 °C       */
    SV_ERR_SAL_RANGE   = -2,   /* salinity outside 30..40 PSU         */
    SV_ERR_DEPTH_RANGE = -3,   /* depth outside 0..12000 m            */
    SV_ERR_FREQ_RANGE  = -4,   /* frequency outside valid range        */
    SV_ERR_PH_RANGE    = -5,   /* pH outside 7..9                      */
    SV_ERR_NULL_PTR    = -6,   /* NULL pointer argument                */
    SV_ERR_SIZE_ZERO   = -7,   /* batch size == 0                      */
    SV_ERR_SSP_SHORT   = -8,   /* sound-speed profile too short        */
    SV_ERR_CUDA        = -9,   /* CUDA runtime error                   */
    SV_ERR_PARAM       = -10,  /* generic invalid parameter            */
} sv_error_t;

/* ── Mackenzie 1981 sound speed ──────────────────────────────────── */

/**
 * Compute sound speed (m/s) from temperature, salinity, depth.
 *
 * Mackenzie, K.V. (1981). "Nine-term equation for sound speed in the
 * oceans." J. Acoust. Soc. Am. 70(3), 807–812.
 *
 * c = 1448.96 + 4.591T - 5.304e-2 T² + 2.374e-4 T³
 *     + 1.340 (S - 35) + 1.630e-2 D + 1.675e-7 D²
 *     - 1.025e-2 T (S - 35) - 7.139e-13 T D³
 *
 * @param temp     Temperature (°C), range -2..30
 * @param salinity Salinity (PSU), range 30..40
 * @param depth    Depth (m), range 0..12000
 * @param[out] speed Sound speed (m/s)
 * @return SV_OK or error code
 */
sv_error_t sv_mackenzie(double temp, double salinity, double depth, double *speed);

/**
 * Vectorized Mackenzie sound speed.
 * All arrays must be length n. Output may alias input arrays.
 */
sv_error_t sv_mackenzie_batch(const double *temps, const double *sals,
                              const double *depths, double *out, int n);

/* ── Francois-Garrison 1982 absorption ───────────────────────────── */

/**
 * Compute acoustic absorption coefficient (dB/km).
 *
 * Francois, R.E. & Garrison, G.R. (1982). "Sound absorption based on
 * ocean measurements: Part I & II." J. Acoust. Soc. Am. 72(6), 1879–1890.
 *
 * Three-relaxation model:
 *   α = (A₁P₁f₁f²)/(f²+f₁²) + (A₂P₂f₂f²)/(f²+f₂²) + A₃P₃f²
 * Relaxations: boric acid (f₁), magnesium sulfate (f₂), pure water.
 *
 * @param freq     Frequency (kHz), range 0.4..1000
 * @param temp     Temperature (°C), range -2..30
 * @param salinity Salinity (PSU), range 30..40
 * @param depth    Depth (m), range 0..12000
 * @param ph       pH, range 7..9
 * @param[out] alpha Absorption (dB/km)
 * @return SV_OK or error code
 */
sv_error_t sv_absorption(double freq, double temp, double salinity,
                         double depth, double ph, double *alpha);

/** Vectorized absorption. */
sv_error_t sv_absorption_batch(const double *freqs, const double *temps,
                               const double *sals, const double *depths,
                               const double *phs, double *out, int n);

/* ── Sound-speed profile ─────────────────────────────────────────── */

/** Single point in a sound-speed profile. */
typedef struct sv_ssp_point {
    double depth;   /* m   */
    double speed;   /* m/s */
} sv_ssp_point_t;

/** Sound-speed profile (layered, must be sorted by increasing depth). */
typedef struct sv_ssp {
    const sv_ssp_point_t *points;
    int n;
} sv_ssp_t;

/* ── Ray tracing ─────────────────────────────────────────────────── */

/** Ray trace mode selector. */
typedef enum sv_ray_mode {
    SV_RAY_SHALLOW = 0,   /* Shallow water, surface-bounce emphasis */
    SV_RAY_DEEP    = 1,   /* Deep water, bottom-bounce / SOFAR       */
} sv_ray_mode_t;

/** Result of a single ray trace. */
typedef struct sv_ray_result {
    double travel_time;       /* seconds        */
    double path_length;       /* meters         */
    double transmission_loss; /* dB             */
    int    surface_bounces;
    int    bottom_bounces;
} sv_ray_result_t;

/**
 * Trace a single acoustic ray through a layered medium.
 *
 * Uses Snell's law with constant-gradient interpolation within each
 * layer. The SSP defines layer boundaries; sound speed varies linearly
 * between consecutive points.
 *
 * @param ssp       Sound-speed profile
 * @param src_depth Source depth (m)
 * @param angle     Launch angle (radians from horizontal, positive down)
 * @param max_range Maximum range to trace (m)
 * @param mode      Shallow / deep water mode
 * @param max_bounces Stop after this many total bounces (0 = unlimited)
 * @param[out] res  Ray trace result
 * @return SV_OK or error code
 */
sv_error_t sv_ray_trace(const sv_ssp_t *ssp, double src_depth,
                        double angle, double max_range,
                        sv_ray_mode_t mode, int max_bounces,
                        sv_ray_result_t *res);

/* ── Sonar equation ──────────────────────────────────────────────── */

/** Full sonar equation parameters. */
typedef struct sv_sonar_params {
    double source_level;      /* SL  (dB re 1 µPa at 1 m)     */
    double noise_level;       /* NL  (dB re 1 µPa²/Hz)        */
    double directivity_index; /* DI  (dB)                      */
    double target_strength;   /* TS  (dB re 1 m²)              */
    double detection_threshold;/* DT (dB)                      */
    double frequency;         /* kHz                           */
    double bandwidth;         /* Hz                            */
    double temperature;       /* °C                            */
    double salinity;          /* PSU                           */
    double ph;                /* pH                            */
    double src_depth;         /* m                             */
    double tgt_depth;         /* m                             */
} sv_sonar_params_t;

/** Sonar equation result. */
typedef struct sv_sonar_result {
    double signal_excess;         /* dB                          */
    double detection_probability; /* 0..1  (Rice model)          */
    double max_range;             /* m  (first range where SE≤0) */
    double transmission_loss;     /* dB at max_range or tgt range*/
} sv_sonar_result_t;

/**
 * Evaluate the full sonar equation at a given range.
 *
 * Signal excess = SL − TL − (NL − DI) + TS − DT
 *
 * Detection probability uses the Rice (1944, 1945) model:
 *   P_d ≈ 1 − Φ( DT − SE )
 * where Φ is the standard-normal CDF.
 *
 * Range prediction uses bisection search for SE = 0 crossing.
 */
sv_error_t sv_sonar_equation(const sv_sonar_params_t *p, double range,
                             sv_sonar_result_t *res);

/* ── Reverberation ───────────────────────────────────────────────── */

/** Reverberation type. */
typedef enum sv_reverb_type {
    SV_REVERB_VOLUME  = 0,
    SV_REVERB_SURFACE = 1,
    SV_REVERB_BOTTOM  = 2,
} sv_reverb_type_t;

/** Reverberation parameters. */
typedef struct sv_reverb_params {
    double pulse_length;       /* s     */
    double beam_pattern;       /* dB    (equivalent beam width) */
    double bottom_strength;    /* dB    (Lambert's law Bs)      */
    double surface_strength;   /* dB    (surface scatter)       */
    double volume_scatter;     /* dB/m  (sv, volume scatter)    */
    double frequency;          /* kHz   */
    double temperature;        /* °C    */
    double salinity;           /* PSU   */
    double ph;                 /* pH    */
    double src_depth;          /* m     */
} sv_reverb_params_t;

/**
 * Compute reverberation level (dB re 1 µPa) at given range.
 *
 * Bottom reverberation uses Lambert's law:
 *   RL = SL + 10 log₁₀( A Bs sin²θ / (2π R⁴) ) − 2TL
 * where A is the insonified area and Bs is the Lambert parameter.
 *
 * @param type Volume / surface / bottom
 * @param p    Parameters
 * @param range Range (m)
 * @param ssp  Sound-speed profile for TL
 * @param[out] rl Reverberation level (dB)
 */
sv_error_t sv_reverberation(sv_reverb_type_t type,
                            const sv_reverb_params_t *p,
                            double range, const sv_ssp_t *ssp,
                            double *rl);

/* ── CUDA batch API ──────────────────────────────────────────────── */

/** Opaque handle for a CUDA processing context. */
typedef struct sv_cuda_ctx sv_cuda_ctx_t;

/**
 * Create a CUDA context. Selects device (Jetson Xavier preferred).
 * Set device_id < 0 for automatic selection.
 */
sv_error_t sv_cuda_create(int device_id, sv_cuda_ctx_t **ctx);

/** Destroy a CUDA context and free all associated GPU memory. */
sv_error_t sv_cuda_destroy(sv_cuda_ctx_t *ctx);

/**
 * GPU-accelerated batch Mackenzie sound speed.
 * Returns results via host-side output array.
 */
sv_error_t sv_cuda_mackenzie(sv_cuda_ctx_t *ctx,
                             const double *temps, const double *sals,
                             const double *depths, double *out, int n);

/**
 * GPU-accelerated batch absorption (Francois-Garrison).
 */
sv_error_t sv_cuda_absorption(sv_cuda_ctx_t *ctx,
                              const double *freqs, const double *temps,
                              const double *sals, const double *depths,
                              const double *phs, double *out, int n);

/**
 * GPU-accelerated batch ray tracing.
 * Each ray is independent — one thread per ray.
 */
sv_error_t sv_cuda_ray_trace(sv_cuda_ctx_t *ctx,
                             const sv_ssp_t *ssp,
                             const double *src_depths,
                             const double *angles,
                             double max_range,
                             sv_ray_mode_t mode,
                             int max_bounces,
                             sv_ray_result_t *out, int n);

/* ── Version ─────────────────────────────────────────────────────── */

#define SV_VERSION_MAJOR 1
#define SV_VERSION_MINOR 0
#define SV_VERSION_PATCH 0

/** Returns version string "major.minor.patch". */
const char *sv_version(void);

#ifdef __cplusplus
}
#endif

#endif /* SONAR_VISION_H */
