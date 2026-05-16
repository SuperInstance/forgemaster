/**
 * @file snapkit_internal.h
 * @brief Internal/private type definitions for SnapKit.
 *
 * This header is NOT part of the public API. It defines the actual struct
 * layouts for the opaque types declared in snapkit.h. Users should not
 * include this file directly.
 *
 * @cond INTERNAL
 */

#ifndef SNAPKIT_INTERNAL_H
#define SNAPKIT_INTERNAL_H

#include "snapkit.h"
#include <string.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------------------------------------------------------------------
 * Snap Function (internal)
 * ------------------------------------------------------------------------- */

/** Maximum number of historical results kept for statistics. */
#define SNAPKIT_SNAP_HISTORY_MAX 4096

typedef struct {
    snapkit_snap_result_t* results;   /**< Circular buffer of results */
    size_t                 head;      /**< Write index in circular buffer */
    size_t                 count;     /**< Number of valid entries */
    double                 sum_delta; /**< Running sum of deltas (for mean) */
    double                 max_delta; /**< Running maximum delta */
    size_t                 snap_cnt;  /**< Count of snaps (within tolerance) */
    size_t                 delta_cnt; /**< Count of deltas (exceeded tolerance) */
} snapkit_snap_history_t;

struct snapkit_snap_function {
    double                tolerance;
    snapkit_topology_t    topology;
    double                baseline;
    double                adaptation_rate;
    snapkit_snap_history_t history;
};

/* ---------------------------------------------------------------------------
 * Delta Detector (internal)
 * ------------------------------------------------------------------------- */

typedef struct {
    char                    stream_id[32];
    snapkit_snap_function_t snap;        /**< Per-stream snap function */
    double                  actionability;
    double                  urgency;
    snapkit_delta_t         current;     /**< Most recent result */
    bool                    has_current; /**< True after first observation */
} snapkit_delta_stream_t;

struct snapkit_delta_detector {
    snapkit_delta_stream_t streams[SNAPKIT_MAX_STREAMS];
    int                    num_streams;
    uint64_t               tick;
};

/* ---------------------------------------------------------------------------
 * Attention Budget (internal)
 * ------------------------------------------------------------------------- */

struct snapkit_attention_budget {
    double             total_budget;
    double             remaining;
    snapkit_strategy_t strategy;
    size_t             exhaustion_count;
    size_t             cycle_count;
};

/* ---------------------------------------------------------------------------
 * Script Library (internal)
 * ------------------------------------------------------------------------- */

typedef struct {
    char                    id[SNAPKIT_SCRIPT_ID_MAX];
    char                    name[SNAPKIT_SCRIPT_NAME_MAX];
    double                  trigger[SNAPKIT_MAX_PATTERN_DIM];
    size_t                  trigger_dim;
    double                  response;          /**< Opaque response value */
    double                  match_threshold;
    snapkit_script_status_t status;
    size_t                  use_count;
    size_t                  success_count;
    size_t                  fail_count;
    uint64_t                last_used;
    uint64_t                created_at;
    double                  confidence;
} snapkit_script_t;

struct snapkit_script_library {
    snapkit_script_t scripts[SNAPKIT_MAX_SCRIPTS];
    int              num_scripts;
    double           match_threshold;
    size_t           hit_count;
    size_t           miss_count;
    uint64_t         tick;
};

/* ---------------------------------------------------------------------------
 * Constraint Sheaf (internal)
 * ------------------------------------------------------------------------- */

#define SNAPKIT_MAX_CONSTRAINTS 64
#define SNAPKIT_MAX_DEPENDENCIES 128
#define SNAPKIT_CONSTRAINT_NAME_MAX 32

typedef struct {
    char   name[SNAPKIT_CONSTRAINT_NAME_MAX];
    double value;
    double expected;
    bool   has_expected;
} snapkit_constraint_node_t;

typedef struct {
    char source[SNAPKIT_CONSTRAINT_NAME_MAX];
    char target[SNAPKIT_CONSTRAINT_NAME_MAX];
} snapkit_dependency_t;

struct snapkit_constraint_sheaf {
    snapkit_topology_t           topology;
    double                       tolerance;
    snapkit_constraint_node_t    constraints[SNAPKIT_MAX_CONSTRAINTS];
    int                          num_constraints;
    snapkit_dependency_t         dependencies[SNAPKIT_MAX_DEPENDENCIES];
    int                          num_dependencies;
};

/* ---------------------------------------------------------------------------
 * Internal helper functions
 * ------------------------------------------------------------------------- */

/** @brief Convert topology enum to string for diagnostics. */
const char* snapkit_topology_name(snapkit_topology_t t);

/** @brief Convert severity enum to string. */
const char* snapkit_severity_name(snapkit_severity_t s);

/** @brief Compute severity from magnitude/tolerance ratio. */
snapkit_severity_t snapkit_compute_severity(double magnitude, double tolerance);

/** @brief Cosine similarity between two double arrays. */
double snapkit_cosine_similarity(const double* a, const double* b, size_t n);

/** @brief Vector L2 norm. */
double snapkit_l2_norm(const double* v, size_t n);

/** @brief Compute the nearest Eisenstein integer to (real, imag).
 *  Uses 7-candidate Voronoi cell search.
 *  @param[out] a  Eisenstein coordinate a.
 *  @param[out] b  Eisenstein coordinate b.
 *  @param[out] snapped_re  Real part of snapped point.
 *  @param[out] snapped_im  Imag part of snapped point.
 *  @param[out] dist  Euclidean distance from original to snapped point. */
void snapkit_nearest_eisenstein(double real, double imag,
                                 int* a, int* b,
                                 double* snapped_re, double* snapped_im,
                                 double* dist);

/** @brief NEON batch implementation of nearest Eisenstein (processes 2 at a time). */
void snapkit_nearest_eisenstein_neon(const double* reals, const double* imags,
                                      int* a_out, int* b_out,
                                      double* snapped_re_out, double* snapped_im_out,
                                      double* dist_out, size_t n);

/** @brief SSE batch implementation for scalar snaps. */
void snapkit_snap_batch_sse(snapkit_snap_function_t* sf,
                             const double* values, size_t n,
                             snapkit_snap_result_t* out);

#ifdef __cplusplus
}
#endif

/** @endcond */

#endif /* SNAPKIT_INTERNAL_H */
