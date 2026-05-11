#ifndef SNAPKIT_CUDA_H
#define SNAPKIT_CUDA_H

/*
 * snapkit-cuda — GPU tolerance-compressed attention allocation
 *
 * "The snap is the gatekeeper of attention. The delta is the compass.
 *  The lattice is the infrastructure. Attention is the thirst."
 *
 * CUDA/PTX implementation of the snapkit library — GPU-accelerated
 * Eisenstein lattice snapping, batch delta detection, and attention
 * budget allocation for massive parallel workloads.
 *
 * Architecture targets: sm_86 (Ada), sm_89, sm_75 (Turing)
 * CUDA minimum version: 11.5
 */

#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <cstdint>
#include <cstddef>

#ifdef __cplusplus
extern "C" {
#endif

/* ======================================================================
 * Error checking macro — every CUDA call must go through this
 * ====================================================================== */

#ifdef CUDA_CHECK
#define CUDA_SAFE_CALL(call) do {                                       \
    cudaError_t err = call;                                             \
    if (cudaSuccess != err) {                                           \
        fprintf(stderr, "CUDA error at %s:%d: %s\n",                    \
                __FILE__, __LINE__, cudaGetErrorString(err));            \
        exit(EXIT_FAILURE);                                             \
    }                                                                   \
} while (0)
#else
#define CUDA_SAFE_CALL(call) call
#endif

/* ======================================================================
 * Constants
 * ====================================================================== */

#define SNAPKIT_MAX_STREAMS           16
#define SNAPKIT_EISENSTEIN_SQRT3      1.7320508075688772f
#define SNAPKIT_EISENSTEIN_INV_SQRT3  0.5773502691896258f
#define SNAPKIT_WARP_SIZE             32
#define SNAPKIT_DEFAULT_TOLERANCE     0.1f
#define SNAPKIT_MAX_BATCH_SIZE        (1 << 28)  /* 256M points */

/* ======================================================================
 * Enums and types
 * ====================================================================== */

typedef enum {
    SNAPKIT_ADE_A1 = 0,   /* Binary snap */
    SNAPKIT_ADE_A2 = 1,   /* Eisenstein / hexagonal (2D) */
    SNAPKIT_ADE_A3 = 2,   /* Tetrahedral / A₃ (3D) */
    SNAPKIT_ADE_D4 = 3,   /* D₄ triality (4D) */
    SNAPKIT_ADE_E6 = 4,   /* E₆ exceptional (6D) */
    SNAPKIT_ADE_E7 = 5,   /* E₇ exceptional (7D) */
    SNAPKIT_ADE_E8 = 6,   /* E₈ exceptional (8D) */
    SNAPKIT_ADE_CUBIC = 7 /* ℤⁿ cubic grid */
} snapkit_topology_t;

typedef enum {
    SNAPKIT_ALLOC_MIN     = 0,  /* Allocate minimum attention */
    SNAPKIT_ALLOC_WEIGHT  = 1,  /* Proportional to delta magnitude */
    SNAPKIT_ALLOC_ACTION  = 2,  /* Actionability-weighted */
    SNAPKIT_ALLOC_FULL    = 3   /* Full attention to max delta */
} snapkit_allocation_t;

/* ======================================================================
 * Snap result — single point snapped to lattice with delta
 * ====================================================================== */

typedef struct {
    int    a;          /* First lattice coordinate */
    int    b;          /* Second lattice coordinate (for Eisenstein) */
    float  delta;      /* Distance from original to snapped point */
    int    exceeds_tolerance;  /* Whether delta > applied tolerance */
    float  attention_weight;   /* Weighted score for attention allocation */
} snapkit_snap_result_t;

/* ======================================================================
 * Stream configuration — per-stream tolerance and topology
 * ====================================================================== */

typedef struct {
    int                   stream_id;
    snapkit_topology_t    topology;
    float                 tolerance;
    float                 priority_weight;   /* Multiplier for attention */
} snapkit_stream_config_t;

/* ======================================================================
 * Attention allocation — output of the attention budget engine
 * ====================================================================== */

typedef struct {
    int    point_idx;       /* Index of the point in the input batch */
    int    stream_id;       /* Which stream this belongs to */
    float  attention;       /* Amount of attention allocated */
    float  delta;           /* Original delta magnitude */
    float  actionability;   /* Can attention affect this? */
    float  urgency;         /* Does this need attention NOW? */
    int    rank;            /* Priority rank (1 = highest) */
} snapkit_attention_t;

/* ======================================================================
 * Configuration handle
 * ====================================================================== */

typedef struct {
    snapkit_topology_t     topology;
    float                  default_tolerance;
    int                    num_streams;
    snapkit_stream_config_t stream_configs[SNAPKIT_MAX_STREAMS];
    snapkit_allocation_t   allocation_strategy;
    float                  total_attention_budget;
    int                    top_k_deltas;   /* Return top-K sorted deltas */
} snapkit_config_t;

/* ======================================================================
 * API — Core Snap Functions
 * ====================================================================== */

/**
 * Create a default configuration for the snapkit pipeline.
 * topology: SNAPKIT_ADE_A2 (Eisenstein) by default
 * tolerance: 0.1
 */
void snapkit_create_default_config(snapkit_config_t* config);

/**
 * Set up a per-stream configuration.
 */
void snapkit_configure_stream(
    snapkit_config_t* config,
    int stream_id,
    snapkit_topology_t topology,
    float tolerance,
    float priority_weight
);

/* ======================================================================
 * API — Eisenstein Snap (the core kernel)
 * ====================================================================== */

/**
 * Batch Eisenstein snap: snaps N (x,y) points to the ℤ[ω] lattice.
 *
 * This is the CORE kernel — each thread snaps one point in O(1) with
 * no divergence. Input in SoA format (separate x, y arrays).
 *
 * @param  points_x    Input x coordinates (device, N floats)
 * @param  points_y    Input y coordinates (device, N floats)
 * @param  out_a       Output lattice coordinate a (device, N ints)
 * @param  out_b       Output lattice coordinate b (device, N ints)
 * @param  out_delta   Output delta magnitudes (device, N floats)
 * @param  N           Number of points
 */
void snapkit_batch_eisenstein_snap(
    const float* points_x,
    const float* points_y,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int    N,
    cudaStream_t stream
);

/* ======================================================================
 * API — Delta Detection
 * ====================================================================== */

/**
 * Parallel threshold detection: marks deltas exceeding per-stream tolerance.
 *
 * @param  deltas        Delta magnitudes (device, N floats)
 * @param  tolerances    Per-stream tolerances (device, num_streams floats)
 * @param  stream_ids    Per-point stream assignment (device, N ints)
 * @param  is_delta      Output: 1 if delta exceeds tolerance (device, N bools as ints)
 * @param  attention_weights Output: weighted scores (device, N floats)
 * @param  N             Number of points
 */
void snapkit_delta_threshold(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    int*   is_delta,
    float* attention_weights,
    int    N,
    cudaStream_t stream
);

/* ======================================================================
 * API — Attention Weighted Scoring
 * ====================================================================== */

/**
 * Actionability-weighted attention scoring.
 * Weight = delta * actionability * urgency
 *
 * @param  deltas        Delta magnitudes (device, N floats)
 * @param  is_delta      Which points are deltas (device, N ints)
 * @param  actionability Per-point actionability (device, N floats)
 * @param  urgency       Per-point urgency (device, N floats)
 * @param  weights       Output: weighted scores (device, N floats)
 * @param  N             Number of points
 */
void snapkit_compute_attention_weights(
    const float* deltas,
    const int*   is_delta,
    const float* actionability,
    const float* urgency,
    float* weights,
    int    N,
    cudaStream_t stream
);

/* ======================================================================
 * API — Top-K Delta Reduction
 * ====================================================================== */

/**
 * Top-K delta selection: finds the K largest deltas by attention weight.
 * Uses warp-level reduction followed by block-level reduction.
 *
 * @param  weights       Attention weights (device, N floats)
 * @param  point_ids     Output: indices of top-K points (device, K ints)
 * @param  top_weights   Output: weights of top-K points (device, K floats)
 * @param  K             Number of top deltas to return
 * @param  N             Number of points
 * @return               Number of actual deltas found (may be < K)
 */
int snapkit_top_k_deltas(
    const float* weights,
    int*   point_ids,
    float* top_weights,
    int    K,
    int    N,
    cudaStream_t stream
);

/* ======================================================================
 * API — Topology Snap (ADE variants)
 * ====================================================================== */

/**
 * Batch snap to any ADE topology.
 *
 * @param  points        Input points (device, N * dim floats)
 * @param  dim           Dimension of the topology (2 for A₂, 3 for A₃, etc.)
 * @param  out_snapped   Output: snapped points (device, N * dim floats)
 * @param  out_deltas    Output: delta magnitudes (device, N floats)
 * @param  N             Number of points
 * @param  topology      ADE topology to snap to
 * @param  stream        CUDA stream
 */
void snapkit_batch_topology_snap(
    const float* points,
    int    dim,
    float* out_snapped,
    float* out_deltas,
    int    N,
    snapkit_topology_t topology,
    cudaStream_t stream
);

/* ======================================================================
 * API — Multi-Stream Processing Pipeline
 * ====================================================================== */

/**
 * Full pipeline: snap → delta detect → attention weight → top-K reduction.
 * Runs entirely on GPU with minimal host synchronization.
 *
 * @param  config        Pipeline configuration
 * @param  points_x      Input x coords (device, N floats)
 * @param  points_y      Input y coords (device, N floats)
 * @param  stream_ids    Per-point stream assignment (device, N ints)
 * @param  actionability Per-point actionability (device, N floats, may be NULL)
 * @param  urgency       Per-point urgency (device, N floats, may be NULL)
 * @param  out_results   Output: top-K deltas with attention (host or device)
 * @param  N             Number of points
 * @param  stream        CUDA stream
 * @return               Number of deltas found
 */
int snapkit_pipeline(
    const snapkit_config_t* config,
    const float* points_x,
    const float* points_y,
    const int*   stream_ids,
    const float* actionability,
    const float* urgency,
    snapkit_attention_t* out_results,
    int    N,
    cudaStream_t stream
);

/* ======================================================================
 * API — CUDA Graphs Support
 * ====================================================================== */

/**
 * Capture the full pipeline as a CUDA Graph for fixed-topology workloads.
 * Reuse the graph for ~18x launch overhead reduction.
 */
cudaGraphExec_t snapkit_capture_graph(
    const snapkit_config_t* config,
    cudaStream_t stream
);

/**
 * Launch a previously captured CUDA Graph.
 */
void snapkit_launch_graph(cudaGraphExec_t graphExec, cudaStream_t stream);

/**
 * Destroy a captured CUDA Graph.
 */
void snapkit_destroy_graph(cudaGraphExec_t graphExec);

/* ======================================================================
 * API — Utility
 * ====================================================================== */

/**
 * Print snapkit CUDA device properties.
 */
void snapkit_print_device_info(int device_id);

/**
 * Returns the CUDA compute capability as an integer (e.g., 86 for sm_86).
 */
int snapkit_compute_capability(int device_id);

/**
 * Get human-readable topology name.
 */
const char* snapkit_topology_name(snapkit_topology_t topology);

/**
 * Get recommended grid/block sizes for given kernel.
 */
void snapkit_recommended_launch_params(
    int N,
    int* grid_size,
    int* block_size
);

/* ======================================================================
 * Additional API — Extended operations
 * ====================================================================== */

/* ---- Single-point snap ---- */

/**
 * Snap a single (x,y) point to the Eisenstein lattice (host-side helper).
 * Uses the same formula as the GPU kernel.
 */
void snapkit_eisenstein_snap_single(
    float x, float y,
    int* out_a, int* out_b,
    float* out_delta
);

/* ---- Grid-stride batch snap ---- */

/**
 * Grid-stride loop batch Eisenstein snap for arbitrarily large N.
 * Each thread processes multiple points via grid-stride pattern.
 */
void snapkit_batch_snap_grid_stride(
    const float* points_x,
    const float* points_y,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int    N,
    cudaStream_t stream
);

/* ---- FP16 batch snap ---- */

/**
 * FP16 batch Eisenstein snap. Input as half precision, output in int32.
 * Higher throughput when precision requirements are moderate.
 */
void snapkit_batch_snap_fp16(
    const half* points_x,
    const half* points_y,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int    N,
    cudaStream_t stream
);

/* ---- Multi-stream snap ---- */

/**
 * Multi-stream batch Eisenstein snap with per-stream tolerance.
 * Each point assigned to a stream; streams have independent tolerances.
 */
void snapkit_batch_snap_multi_stream(
    const float* points_x,
    const float* points_y,
    const int*   stream_ids,
    int*   out_a,
    int*   out_b,
    float* out_delta,
    int*   out_is_delta,
    int    N,
    cudaStream_t stream
);

/* ---- Weighted delta threshold ---- */

/**
 * Delta threshold with actionability and urgency weighting.
 * weight = is_delta * delta * actionability * urgency
 */
void snapkit_delta_threshold_weighted(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    const float* actionability,
    const float* urgency,
    int*   is_delta,
    float* attention_weights,
    int    N,
    cudaStream_t stream
);

/* ---- Classify by severity ---- */

#define SNAPKIT_SEVERITY_MINIMAL 0
#define SNAPKIT_SEVERITY_MILD    1
#define SNAPKIT_SEVERITY_MODERATE 2
#define SNAPKIT_SEVERITY_SEVERE  3
#define SNAPKIT_SEVERITY_CRITICAL 4

/**
 * Classify deltas by severity level relative to tolerance.
 * Returns severity index 0-4 for each point.
 */
void snapkit_delta_classify_severity(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    float* severity,
    float* severity_max,
    int    N,
    int    num_streams,
    cudaStream_t stream
);

/* ---- Reduction ---- */

/**
 * Reduce deltas: compute sum and store per-stream counts.
 */
void snapkit_delta_reduce(
    const float* deltas,
    const int*   is_delta,
    const int*   stream_ids,
    int*   stream_counts,
    float* stream_sums,
    float* stream_maxes,
    int    N,
    int    num_streams,
    cudaStream_t stream
);

/**
 * Compute stream-level delta summaries (count, sum per stream).
 */
void snapkit_delta_stream_counts(
    const float* deltas,
    const float* tolerances,
    const int*   stream_ids,
    int*   out_counts,
    float* out_sums,
    int    N,
    int    num_streams,
    cudaStream_t stream
);

/**
 * Full stream delta summary: counts, sums, and max per stream.
 */
void snapkit_delta_stream_summary(
    const float* deltas,
    const int*   is_delta,
    const int*   stream_ids,
    int*   stream_counts,
    float* stream_sums,
    float* stream_maxes,
    int    N,
    int    num_streams,
    cudaStream_t stream
);

/* ---- Stream tolerances & priorities ---- */

/**
 * Set per-stream tolerances on device (copy from host array).
 */
void snapkit_set_stream_tolerances(
    const float* host_tolerances,
    float* device_tolerances,
    int    num_streams,
    cudaStream_t stream
);

/**
 * Set per-stream priority weights on device (copy from host array).
 */
void snapkit_set_stream_priorities(
    const float* host_priorities,
    float* device_priorities,
    int    num_streams,
    cudaStream_t stream
);

/**
 * Top-K selection with per-stream filtering.
 * Finds top-K deltas for each stream independently.
 */
int snapkit_top_k_with_streams(
    const float* weights,
    const int*   stream_ids,
    int*   point_ids,
    float* top_weights,
    int    K,
    int    target_stream,
    int    N,
    cudaStream_t stream
);

/* ---- Reduction utilities ---- */

/**
 * Parallel reduction: sum all values.
 */
void snapkit_reduce_sum(
    const float* values,
    float* sum_out,
    int    N,
    cudaStream_t stream
);

/**
 * Find argmax (index of maximum value).
 */
int snapkit_argmax(
    const float* values,
    float* max_value,
    int    N,
    cudaStream_t stream
);

/* ---- Stream delta summary (alternate naming for backward compat) ---- */

void snapkit_stream_delta_summary(
    const float* deltas,
    const int*   is_delta,
    const int*   stream_ids,
    int*   stream_counts,
    float* stream_sums,
    float* stream_maxes,
    int    N,
    int    num_streams,
    cudaStream_t stream
);

/* ---- Topology convenience functions ---- */

/**
 * Snap A₁ (binary/1D).
 */
void snapkit_snap_a1(
    const float* points,
    float* out_snapped,
    float* out_deltas,
    int    N,
    cudaStream_t stream
);

/**
 * Snap A₃ (tetrahedral/3D). Points as SoA.
 */
void snapkit_snap_a3(
    const float* points_x,
    const float* points_y,
    const float* points_z,
    float* out_x,
    float* out_y,
    float* out_z,
    float* out_deltas,
    int    N,
    cudaStream_t stream
);

/**
 * Snap D₄ (4D triality).
 */
void snapkit_snap_d4(
    const float* points,
    float* out_snapped,
    float* out_deltas,
    int    N,
    cudaStream_t stream
);

/**
 * Snap E₈ (8D icosahedral).
 */
void snapkit_snap_e8(
    const float* points,
    float* out_snapped,
    float* out_deltas,
    int    N,
    cudaStream_t stream
);

/* ---- Attention allocation ---- */

/**
 * Allocate attention budget to top-K deltas.
 * Allocation strategy determined by config.
 */
void snapkit_allocate_attention(
    const snapkit_config_t* config,
    const int*   top_indices,
    const float* top_weights,
    const int*   stream_ids,
    snapkit_attention_t* results,
    int    actual_k
);

#ifdef __cplusplus
}   /* extern "C" */
#endif

#endif /* SNAPKIT_CUDA_H */
