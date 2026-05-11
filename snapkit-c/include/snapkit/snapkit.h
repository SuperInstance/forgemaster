/**
 * @file snapkit.h
 * @brief SnapKit — Tolerance-Compressed Attention Allocation Library
 *
 * SnapKit is a C library implementing snap-attention theory: the tolerance
 * compression of context so cognition can focus on where thinking matters.
 *
 * Core concepts:
 *   - SnapFunction: compresses information to "close enough to expected"
 *   - Delta detection: tracks what exceeds snap tolerance
 *   - Attention budget: finite cognition allocation to actionable deltas
 *   - Eisenstein lattice (A₂): optimal 2D snap with H¹=0 guarantee
 *   - Platonic/ADE classification: 5 flavors of randomness
 *
 * Theory: SNAPS-AS-ATTENTION.md (Forgemaster ⚒️ / Casey Digennaro, 2026)
 *
 * @defgroup snapkit SnapKit Public API
 * @{
 */

#ifndef SNAPKIT_H
#define SNAPKIT_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------------------------------------------------------------------
 * Platform detection
 * ------------------------------------------------------------------------- */

#if defined(__ARM_NEON) || defined(__ARM_NEON__)
#  define SNAPKIT_HAVE_NEON 1
#  include <arm_neon.h>
#else
#  define SNAPKIT_HAVE_NEON 0
#endif

#if defined(__SSE4_1__) || defined(__AVX__)
#  define SNAPKIT_HAVE_SSE 1
#  include <immintrin.h>
#else
#  define SNAPKIT_HAVE_SSE 0
#endif

/* ---------------------------------------------------------------------------
 * Version
 * ------------------------------------------------------------------------- */

#define SNAPKIT_VERSION_MAJOR 0
#define SNAPKIT_VERSION_MINOR 2
#define SNAPKIT_VERSION_PATCH 0
#define SNAPKIT_VERSION "0.2.0"

/* ---------------------------------------------------------------------------
 * Configuration constants
 * ------------------------------------------------------------------------- */

/** Maximum number of delta streams in a DeltaDetector. */
#define SNAPKIT_MAX_STREAMS 16

/** Maximum number of scripts in a ScriptLibrary. */
#define SNAPKIT_MAX_SCRIPTS 256

/** Maximum script name length including null terminator. */
#define SNAPKIT_SCRIPT_NAME_MAX 64

/** Maximum script ID length including null terminator. */
#define SNAPKIT_SCRIPT_ID_MAX 16

/** Maximum pattern dimension for script matching. */
#define SNAPKIT_MAX_PATTERN_DIM 64

/** Number of hexagonal Voronoi candidates (center + 6 neighbors). */
#define SNAPKIT_EISENSTEIN_CANDIDATES 7

/** Default snap tolerance. */
#define SNAPKIT_DEFAULT_TOLERANCE 0.1f

/** Default adaptation rate for moving baseline. */
#define SNAPKIT_DEFAULT_ADAPTATION_RATE 0.01f

/** Default attention budget. */
#define SNAPKIT_DEFAULT_BUDGET 100.0f

/** Default script match threshold. */
#define SNAPKIT_DEFAULT_MATCH_THRESHOLD 0.85f

/** Square root of 3 (used in Eisenstein snap). */
#define SNAPKIT_SQRT3 1.7320508075688772935274463415059

/** sqrt(3) / 2 */
#define SNAPKIT_SQRT3_2 0.8660254037844386467637231707529

/** 1 / sqrt(3) */
#define SNAPKIT_INV_SQRT3 0.5773502691896257645091487805019

/** 1/3 as float. */
#define SNAPKIT_ONE_THIRD 0.33333333333333333333333333333333

/* ---------------------------------------------------------------------------
 * Topology types — each a different "flavor of randomness"
 * ------------------------------------------------------------------------- */

/** @brief Snap topology enum — the ADE/Platonic classification of snap shapes. */
typedef enum {
    SNAPKIT_TOPOLOGY_BINARY      = 0, /**< Coin flip — 2 outcomes (A₁) */
    SNAPKIT_TOPOLOGY_TETRAHEDRAL = 1, /**< 4 categories (A₃) */
    SNAPKIT_TOPOLOGY_HEXAGONAL   = 2, /**< Eisenstein lattice (A₂) — optimal 2D snap */
    SNAPKIT_TOPOLOGY_CUBIC       = 3, /**< ℤⁿ — standard uniform grid */
    SNAPKIT_TOPOLOGY_OCTAHEDRAL  = 4, /**< 8 directions, ±axes */
    SNAPKIT_TOPOLOGY_DODECAHEDRAL = 5,/**< 20-category combinatorial */
    SNAPKIT_TOPOLOGY_ICOSAHEDRAL = 6, /**< 12-direction golden-ratio clusters */
    SNAPKIT_TOPOLOGY_GRADIENT    = 7, /**< Near-continuous (d100 style) */

    SNAPKIT_TOPOLOGY_COUNT       = 8
} snapkit_topology_t;

/* ---------------------------------------------------------------------------
 * Status / severity enumerations
 * ------------------------------------------------------------------------- */

/** @brief Delta severity levels. */
typedef enum {
    SNAPKIT_SEVERITY_NONE     = 0, /**< Within tolerance — no delta */
    SNAPKIT_SEVERITY_LOW      = 1, /**< Just outside tolerance */
    SNAPKIT_SEVERITY_MEDIUM   = 2, /**< Clearly exceeds tolerance */
    SNAPKIT_SEVERITY_HIGH     = 3, /**< Far from expected */
    SNAPKIT_SEVERITY_CRITICAL = 4, /**< Extremely far — possible system failure */
    SNAPKIT_SEVERITY_COUNT    = 5
} snapkit_severity_t;

/** @brief Script status. */
typedef enum {
    SNAPKIT_SCRIPT_DRAFT    = 0, /**< Not yet verified */
    SNAPKIT_SCRIPT_ACTIVE   = 1, /**< Verified and in use */
    SNAPKIT_SCRIPT_DEGRADED = 2, /**< Partially failing */
    SNAPKIT_SCRIPT_ARCHIVED = 3  /**< No longer used */
} snapkit_script_status_t;

/** @brief Allocation strategy for attention budget. */
typedef enum {
    SNAPKIT_STRATEGY_ACTIONABILITY = 0, /**< Weighted by actionability × urgency × magnitude */
    SNAPKIT_STRATEGY_REACTIVE      = 1, /**< Attend to biggest deltas first */
    SNAPKIT_STRATEGY_UNIFORM       = 2  /**< Equal attention to all deltas */
} snapkit_strategy_t;

/* ---------------------------------------------------------------------------
 * Error codes
 * ------------------------------------------------------------------------- */

typedef enum {
    SNAPKIT_OK           =  0,
    SNAPKIT_ERR_NULL     = -1, /**< Null pointer argument */
    SNAPKIT_ERR_SIZE     = -2, /**< Size/overflow error */
    SNAPKIT_ERR_STATE    = -3, /**< Invalid state */
    SNAPKIT_ERR_DIM      = -4, /**< Dimension mismatch */
    SNAPKIT_ERR_TOPOLOGY = -5, /**< Invalid topology for operation */
    SNAPKIT_ERR_BUDGET   = -6, /**< Budget exhausted */
    SNAPKIT_ERR_MATH     = -7  /**< Numerical error */
} snapkit_error_t;

/* ---------------------------------------------------------------------------
 * Opaque type declarations — full definitions in snapkit_internal.h
 * ------------------------------------------------------------------------- */

typedef struct snapkit_snap_function  snapkit_snap_function_t;
typedef struct snapkit_delta_detector snapkit_delta_detector_t;
typedef struct snapkit_attention_budget snapkit_attention_budget_t;
typedef struct snapkit_script_library snapkit_script_library_t;
typedef struct snapkit_constraint_sheaf snapkit_constraint_sheaf_t;

/* ---------------------------------------------------------------------------
 * Result structures
 * ------------------------------------------------------------------------- */

/** @brief Result of snapping a value to the expected/lattice. */
typedef struct {
    double           original;          /**< The observed value */
    double           snapped;           /**< Value after snapping to nearest lattice */
    double           delta;             /**< |original - snapped| */
    bool             within_tolerance;  /**< true if delta ≤ tolerance */
    double           tolerance;         /**< The tolerance that was applied */
    snapkit_topology_t topology;        /**< Which topology was used */
} snapkit_snap_result_t;

/** @brief A felt delta — information that exceeded snap tolerance. */
typedef struct {
    double              value;            /**< The observed value */
    double              expected;         /**< What was expected */
    double              magnitude;        /**< |value - expected| */
    double              tolerance;        /**< Threshold that was exceeded */
    snapkit_severity_t  severity;         /**< How significant */
    uint64_t            timestamp;        /**< Monotonic tick count */
    char                stream_id[32];    /**< Source stream identifier */
    double              actionability;    /**< Can thinking change this? [0..1] */
    double              urgency;          /**< Does this need attention NOW? [0..1] */
} snapkit_delta_t;

/** @brief Allocation of attention budget to a specific delta. */
typedef struct {
    snapkit_delta_t delta;     /**< The delta being attended to */
    double           allocated; /**< Amount of attention allocated */
    int              priority;  /**< Priority rank (1 = highest) */
    char             reason[48];/**< Why this allocation was made */
} snapkit_allocation_t;

/** @brief Result of matching an observation against the script library. */
typedef struct {
    char   script_id[SNAPKIT_SCRIPT_ID_MAX];  /**< Best matching script ID */
    double confidence;                          /**< Match confidence [0..1] */
    bool   is_match;                            /**< ≥ match threshold */
    double delta_from_template;                 /**< Euclidean distance from pattern */
} snapkit_script_match_t;

/** @brief Consistency report from constraint sheaf check. */
typedef struct {
    int    num_constraints;    /**< Number of constraints checked */
    double max_delta;          /**< Maximum delta across all constraints */
    double mean_delta;         /**< Mean delta across all constraints */
    int    h1_analog;          /**< Number of constraints exceeding tolerance (H¹ analog) */
    bool   delta_detected;     /**< true if any delta exceeded tolerance */
    double tolerance;          /**< The tolerance used */
    int    topology;           /**< Topology type used */
} snapkit_consistency_report_t;

/* ---------------------------------------------------------------------------
 * ADE topology data (read-only, pre-computed)
 * ------------------------------------------------------------------------- */

/** @brief ADE topology metadata. */
typedef struct {
    snapkit_topology_t type;       /**< Topology enum value */
    const char*        name;       /**< Human-readable name (e.g., "A₂") */
    int                rank;       /**< Rank of the root system */
    int                dimension;  /**< Embedding dimension */
    int                num_roots;  /**< Number of roots */
    int                coxeter_number; /**< Coxeter number */
    const char*        platonic_solid; /**< Associated Platonic solid, or NULL */
    const char*        description;    /**< Short description */
    double             quality_score;  /**< Lattice quality (density × symmetry) */
} snapkit_ade_data_t;

/** @brief Get ADE configuration data for a topology type.
 *  @param type  The topology type to query.
 *  @return Pointer to ADE data, or NULL if type is invalid. */
const snapkit_ade_data_t* snapkit_ade_data(snapkit_topology_t type);

/** @brief Get recommended topology based on requirements.
 *  @param num_categories  Number of categories, or 0 if not applicable.
 *  @param dimension       Ambient dimension, or 0 if unknown.
 *  @return The recommended topology. For 2D, returns HEXAGONAL (A₂ is optimal). */
snapkit_topology_t snapkit_recommend_topology(int num_categories, int dimension);

/* ---------------------------------------------------------------------------
 * Snap Function API
 * ------------------------------------------------------------------------- */

/** @brief Create a snap function with default parameters (tolerance=0.1, HEXAGONAL topology).
 *  @return New snap function, or NULL on allocation failure. Caller must free with snapkit_snap_free(). */
snapkit_snap_function_t* snapkit_snap_create(void);

/** @brief Create a snap function with explicit parameters.
 *  @param tolerance  Maximum distance within which values snap to the expected point.
 *  @param topology   Snap topology (determines lattice shape).
 *  @param baseline   Initial expected value.
 *  @param adaptation_rate How fast baseline adapts to observations [0..1], 0 = never.
 *  @return New snap function, or NULL on allocation failure. */
snapkit_snap_function_t* snapkit_snap_create_ex(double tolerance,
                                                  snapkit_topology_t topology,
                                                  double baseline,
                                                  double adaptation_rate);

/** @brief Free a snap function allocated by snapkit_snap_create*(). */
void snapkit_snap_free(snapkit_snap_function_t* sf);

/** @brief Snap a value to the nearest expected point.
 *  @param sf        Snap function (must be valid).
 *  @param value     The observed value to snap.
 *  @param expected  Override baseline expected value, or NaN to use baseline.
 *  @param[out] out  Where to write the result (must not be NULL).
 *  @return SNAPKIT_OK on success, or an error code. */
snapkit_error_t snapkit_snap(snapkit_snap_function_t* sf,
                              double value,
                              double expected,
                              snapkit_snap_result_t* out);

/** @brief Snap a complex value to the nearest Eisenstein integer (A₂ lattice).
 *  Uses 7-candidate Voronoi cell search for mathematically correct nearest point.
 *
 *  The Eisenstein lattice ℤ[ω] (ω = e^(2πi/3)) provides:
 *    - Densest packing in 2D
 *    - 6-fold symmetry (isotropic compression)
 *    - PID property → H¹ = 0 guarantee
 *
 *  @param sf         Snap function (or NULL to use default tolerance).
 *  @param real       Real part of the complex value.
 *  @param imag       Imaginary part.
 *  @param tolerance  Snap tolerance. If < 0, uses sf's tolerance (if sf not NULL).
 *  @param[out] out   Where to write the result (must not be NULL).
 *  @return SNAPKIT_OK on success, or an error code. */
snapkit_error_t snapkit_snap_eisenstein(snapkit_snap_function_t* sf,
                                         double real,
                                         double imag,
                                         double tolerance,
                                         snapkit_snap_result_t* out);

/** @brief Batch snap an array of doubles. Efficient SIMD path when available.
 *  @param sf         Snap function.
 *  @param values     Array of double values.
 *  @param n          Number of values.
 *  @param[out] out   Output array of snapkit_snap_result_t (must have room for n).
 *  @return SNAPKIT_OK on success. */
snapkit_error_t snapkit_snap_batch(snapkit_snap_function_t* sf,
                                    const double* values,
                                    size_t n,
                                    snapkit_snap_result_t* out);

/** @brief Batch snap Eisenstein (complex) values using NEON SIMD when available.
 *  @param sf         Snap function.
 *  @param real_vals  Array of real components.
 *  @param imag_vals  Array of imag components.
 *  @param n          Number of complex values.
 *  @param[out] out   Output array of snapkit_snap_result_t (must have room for n).
 *  @return SNAPKIT_OK on success. */
snapkit_error_t snapkit_snap_eisenstein_batch(snapkit_snap_function_t* sf,
                                               const double* real_vals,
                                               const double* imag_vals,
                                               size_t n,
                                               snapkit_snap_result_t* out);

/** @brief Reset snap function state.
 *  @param sf        Snap function.
 *  @param baseline  New baseline, or NaN to keep current. */
void snapkit_snap_reset(snapkit_snap_function_t* sf, double baseline);

/** @brief Auto-calibrate tolerance to achieve a target snap rate.
 *
 *  The snap rate is the fraction of observations that fall within tolerance.
 *  A well-calibrated snap function should snap ~90% of observations, leaving
 *  10% as deltas demanding attention.
 *
 *  @param sf              Snap function.
 *  @param values          Array of sample values to calibrate on.
 *  @param n               Number of values.
 *  @param target_rate     Desired snap rate [0..1] (0.9 recommended).
 *  @return SNAPKIT_OK on success. */
snapkit_error_t snapkit_snap_calibrate(snapkit_snap_function_t* sf,
                                        const double* values,
                                        size_t n,
                                        double target_rate);

/** @brief Get statistics from a snap function.
 *  @param sf  Snap function.
 *  @param[out] snap_count    Total number of observations that snapped within tolerance.
 *  @param[out] delta_count   Total number of observations that exceeded tolerance.
 *  @param[out] mean_delta    Mean delta magnitude across all observations.
 *  @param[out] max_delta     Maximum delta magnitude observed.
 *  @param[out] snap_rate     Fraction of observations that snapped [0..1]. */
void snapkit_snap_statistics(const snapkit_snap_function_t* sf,
                              size_t* snap_count,
                              size_t* delta_count,
                              double* mean_delta,
                              double* max_delta,
                              double* snap_rate);

/* ---------------------------------------------------------------------------
 * Delta Detector API
 * ------------------------------------------------------------------------- */

/** @brief Create a delta detector.
 *  @return New detector, or NULL on failure. */
snapkit_delta_detector_t* snapkit_detector_create(void);

/** @brief Free a delta detector. */
void snapkit_detector_free(snapkit_delta_detector_t* dd);

/** @brief Add an information stream to monitor.
 *  @param dd              Delta detector.
 *  @param stream_id       Unique identifier for the stream.
 *  @param tolerance       Snap tolerance for this stream.
 *  @param topology        Snap topology for this stream.
 *  @param actionability   Default actionability [0..1] (NaN = auto-compute).
 *  @param urgency         Default urgency [0..1].
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_SIZE if max streams reached. */
snapkit_error_t snapkit_detector_add_stream(snapkit_delta_detector_t* dd,
                                             const char* stream_id,
                                             double tolerance,
                                             snapkit_topology_t topology,
                                             double actionability,
                                             double urgency);

/** @brief Observe a value on a specific stream.
 *  @param dd         Delta detector.
 *  @param stream_id  Which stream to observe.
 *  @param value      The observed value.
 *  @param[out] out   Where to write the resulting delta (may be NULL).
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_NULL if stream not found. */
snapkit_error_t snapkit_detector_observe(snapkit_delta_detector_t* dd,
                                          const char* stream_id,
                                          double value,
                                          snapkit_delta_t* out);

/** @brief Observe values across all registered streams.
 *  @param dd            Delta detector.
 *  @param stream_ids    Array of stream ID strings.
 *  @param values        Array of values to observe (parallel to stream_ids).
 *  @param n             Number of observations.
 *  @param[out] deltas   Output array for results (may be NULL if not needed).
 *  @return SNAPKIT_OK on success, or an error code if any stream is unknown. */
snapkit_error_t snapkit_detector_observe_batch(snapkit_delta_detector_t* dd,
                                                const char** stream_ids,
                                                const double* values,
                                                size_t n,
                                                snapkit_delta_t* deltas);

/** @brief Query the most recent delta for a stream.
 *  @param dd         Delta detector.
 *  @param stream_id  Which stream to query.
 *  @param[out] out   Where to write the most recent delta.
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_NULL if none observed. */
snapkit_error_t snapkit_detector_current_delta(snapkit_delta_detector_t* dd,
                                                const char* stream_id,
                                                snapkit_delta_t* out);

/** @brief Get detector statistics.
 *  @param dd                 Detector.
 *  @param[out] num_streams   Number of registered streams.
 *  @param[out] total_deltas  Total nontrivial deltas across all streams.
 *  @param[out] delta_rate    Overall delta rate [0..1]. */
void snapkit_detector_statistics(const snapkit_delta_detector_t* dd,
                                  int* num_streams,
                                  size_t* total_deltas,
                                  double* delta_rate);

/* ---------------------------------------------------------------------------
 * Attention Budget API
 * ------------------------------------------------------------------------- */

/** @brief Create an attention budget.
 *  @param total_budget  Maximum attention units available per cycle.
 *  @param strategy      Allocation strategy.
 *  @return New budget, or NULL on failure. */
snapkit_attention_budget_t* snapkit_budget_create(double total_budget,
                                                    snapkit_strategy_t strategy);

/** @brief Free an attention budget. */
void snapkit_budget_free(snapkit_attention_budget_t* ab);

/** @brief Allocate attention to a set of deltas.
 *  @param ab        Attention budget.
 *  @param deltas    Array of deltas (already prioritized by caller).
 *  @param n         Number of deltas.
 *  @param[out] allocs Output array for allocations (must have room for n).
 *  @param[out] n_allocated Number of allocations actually made (may be < n if budget exhausted).
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_BUDGET if budget was exhausted. */
snapkit_error_t snapkit_budget_allocate(snapkit_attention_budget_t* ab,
                                         const snapkit_delta_t* deltas,
                                         size_t n,
                                         snapkit_allocation_t* allocs,
                                         size_t* n_allocated);

/** @brief Query budget state.
 *  @param ab               Budget.
 *  @param[out] remaining   Remaining budget (output, may be NULL).
 *  @param[out] utilization Utilization fraction [0..1] (output, may be NULL). */
void snapkit_budget_status(const snapkit_attention_budget_t* ab,
                            double* remaining,
                            double* utilization);

/* ---------------------------------------------------------------------------
 * Script Library API
 * ------------------------------------------------------------------------- */

/** @brief Create a script library.
 *  @param match_threshold  Minimum similarity to activate a script [0..1].
 *  @return New library, or NULL on failure. */
snapkit_script_library_t* snapkit_script_library_create(double match_threshold);

/** @brief Free a script library. */
void snapkit_script_library_free(snapkit_script_library_t* lib);

/** @brief Add a script to the library.
 *  @param lib            Script library.
 *  @param id             Unique script ID.
 *  @param name           Human-readable name.
 *  @param trigger        Trigger pattern (double array).
 *  @param trigger_dim    Dimension of trigger pattern.
 *  @param response       Opaque response value (stored as double, e.g., enum cast).
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_SIZE if library full. */
snapkit_error_t snapkit_script_library_add(snapkit_script_library_t* lib,
                                            const char* id,
                                            const char* name,
                                            const double* trigger,
                                            size_t trigger_dim,
                                            double response);

/** @brief Find the best matching script for an observation.
 *  @param lib          Script library.
 *  @param observation  Observed pattern (double array).
 *  @param obs_dim      Dimension of observation.
 *  @param[out] match   Best match result.
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_DIM on dimension mismatch,
 *          SNAPKIT_ERR_NULL if no match found above threshold. */
snapkit_error_t snapkit_script_library_match(snapkit_script_library_t* lib,
                                              const double* observation,
                                              size_t obs_dim,
                                              snapkit_script_match_t* match);

/** @brief Record a use of a script (for confidence tracking).
 *  @param lib       Script library.
 *  @param script_id ID of the script used.
 *  @param success   Whether the script was successful. */
void snapkit_script_library_record_use(snapkit_script_library_t* lib,
                                        const char* script_id,
                                        bool success);

/** @brief Archive a script (deactivate without deleting).
 *  @param lib       Script library.
 *  @param script_id ID of the script to archive.
 *  @return SNAPKIT_OK on success, SNAPKIT_ERR_NULL if not found. */
snapkit_error_t snapkit_script_library_forget(snapkit_script_library_t* lib,
                                               const char* script_id);

/** @brief Get library statistics.
 *  @param lib              Library.
 *  @param[out] active      Number of active scripts.
 *  @param[out] total       Total scripts.
 *  @param[out] hit_rate    Hit rate [0..1]. */
void snapkit_script_library_statistics(const snapkit_script_library_t* lib,
                                        int* active,
                                        int* total,
                                        double* hit_rate);

/* ---------------------------------------------------------------------------
 * Constraint Sheaf (sheaf-theoretic consistency checking)
 * ------------------------------------------------------------------------- */

/** @brief Create a constraint sheaf for H¹ consistency checking.
 *  @param topology  Snap topology for the constraint lattice.
 *  @param tolerance Maximum drift before delta is detected.
 *  @return New sheaf, or NULL on failure. */
snapkit_constraint_sheaf_t* snapkit_sheaf_create(snapkit_topology_t topology,
                                                   double tolerance);

/** @brief Free a constraint sheaf. */
void snapkit_sheaf_free(snapkit_constraint_sheaf_t* sheaf);

/** @brief Add a constraint node to the sheaf.
 *  @param sheaf     Constraint sheaf.
 *  @param name      Constraint name (unique).
 *  @param value     Current value.
 *  @param expected  Expected value (NaN = set to value). */
snapkit_error_t snapkit_sheaf_add_constraint(snapkit_constraint_sheaf_t* sheaf,
                                              const char* name,
                                              double value,
                                              double expected);

/** @brief Add a dependency between constraints.
 *  @param sheaf   Constraint sheaf.
 *  @param source  Source constraint name.
 *  @param target  Target constraint name. */
snapkit_error_t snapkit_sheaf_add_dependency(snapkit_constraint_sheaf_t* sheaf,
                                              const char* source,
                                              const char* target);

/** @brief Check global consistency of all constraints.
 *  @param sheaf    Constraint sheaf.
 *  @param[out] report Consistency report.
 *  @return SNAPKIT_OK on success. */
snapkit_error_t snapkit_sheaf_check(snapkit_constraint_sheaf_t* sheaf,
                                     snapkit_consistency_report_t* report);

/** @brief Update the expected value for a constraint.
 *  @param sheaf    Constraint sheaf.
 *  @param name     Constraint name.
 *  @param expected New expected value. */
snapkit_error_t snapkit_sheaf_update_expected(snapkit_constraint_sheaf_t* sheaf,
                                               const char* name,
                                               double expected);

#ifdef __cplusplus
}
#endif

/** @} */ /* end defgroup snapkit */

#endif /* SNAPKIT_H */
