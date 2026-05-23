#ifndef FLUX_CUDA_H
#define FLUX_CUDA_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>

/* ── Error codes ─────────────────────────────────────────────── */
typedef enum {
    FLUX_CUDA_OK              = 0,
    FLUX_CUDA_ERR_NO_DEVICE   = 1,
    FLUX_CUDA_ERR_MALLOC      = 2,
    FLUX_CUDA_ERR_COPY        = 3,
    FLUX_CUDA_ERR_KERNEL      = 4,
    FLUX_CUDA_ERR_INVALID     = 5,
    FLUX_CUDA_ERR_UNSUPPORTED = 6,
} flux_cuda_error_t;

/* ── Device info ─────────────────────────────────────────────── */
typedef struct {
    char name[256];
    int  major;           /* compute capability major */
    int  minor;           /* compute capability minor */
    size_t total_mem;     /* global memory bytes      */
    int  multiprocessor_count;
    int  max_threads_per_block;
    int  max_shared_per_block;
    int  warp_size;
} flux_cuda_device_info_t;

/* ── FLUX VM bytecode blob ───────────────────────────────────── */
typedef struct {
    const uint8_t*  bytecode;     /* flat instruction stream          */
    size_t          bytecode_len; /* bytes                            */
    const double*   inputs;       /* instance_count * inputs_per_inst */
    int             inputs_per_instance;
    int             max_stack;    /* max stack depth (≤256 doubles)   */
} flux_vm_batch_desc_t;

/* ── Batch VM result ─────────────────────────────────────────── */
typedef struct {
    double*   outputs;        /* instance_count * outputs_per_inst */
    int       outputs_per_instance;
    int32_t*  violation_flags;/* per-instance: 0=ok, nonzero=violation */
} flux_vm_batch_result_t;

/* ── CSP problem descriptor ──────────────────────────────────── */
typedef struct {
    int   var_count;          /* number of variables per problem      */
    int   max_domain_size;    /* max values in any domain             */
    int   constraint_count;   /* binary constraints per problem       */
} flux_csp_problem_desc_t;

typedef struct {
    const int*    domains;    /* [problem_count * var_count * max_domain_size] -1 terminated */
    const int*    constraints;/* [problem_count * constraint_count * 2] (var_i, var_j) pairs */
    const double* weights;    /* optional constraint weights, NULL for unweighted */
    int*          solutions;  /* [problem_count * var_count] output assignments */
    int32_t*      solved;     /* per-problem: 1=solved, 0=no solution */
} flux_csp_batch_t;

/* ── Arc consistency ─────────────────────────────────────────── */
typedef struct {
    int*    domains;      /* in/out: flattened domain arrays    */
    int32_t* pruned;      /* out: per-variable count of pruned  */
} flux_arc_batch_t;

/* ── Sonar physics ───────────────────────────────────────────── */
typedef struct {
    const double* depths;      /* count values, meters         */
    const double* temps;       /* count values, °C             */
    const double* salinities;  /* count values, PSU            */
    const double* freqs;       /* count values, kHz            */
    double*       sound_speeds;/* out: count values, m/s       */
    double*       absorptions; /* out: count values, dB/km     */
    int           count;       /* number of samples            */
} flux_sonar_batch_t;

/* ════════════════════════════════════════════════════════════════
 *  PUBLIC API
 * ══════════════════════════════════════════════════════════════ */

/* ── Device management ───────────────────────────────────────── */
flux_cuda_error_t flux_cuda_init(void);
flux_cuda_error_t flux_cuda_device_info(flux_cuda_device_info_t* info);
void              flux_cuda_cleanup(void);

/* ── Batch FLUX VM execution ─────────────────────────────────── */
flux_cuda_error_t flux_cuda_batch_execute(
    const flux_vm_batch_desc_t*  desc,
    int                          instance_count,
    flux_vm_batch_result_t*      results);

/* ── Parallel CSP solver ─────────────────────────────────────── */
flux_cuda_error_t flux_cuda_csp_solve(
    const flux_csp_problem_desc_t* problem_desc,
    const flux_csp_batch_t*        batch,
    int                            problem_count);

/* ── Arc consistency pruning ─────────────────────────────────── */
flux_cuda_error_t flux_cuda_arc_consistency(
    const flux_csp_problem_desc_t* problem_desc,
    flux_arc_batch_t*              batch,
    int                            problem_count);

/* ── Batch sonar physics ─────────────────────────────────────── */
flux_cuda_error_t flux_cuda_sonar_physics(flux_sonar_batch_t* batch);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_CUDA_H */
