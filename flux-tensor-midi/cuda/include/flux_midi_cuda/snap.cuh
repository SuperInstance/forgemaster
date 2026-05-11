#ifndef FLUX_MIDI_CUDA_SNAP_CUH
#define FLUX_MIDI_CUDA_SNAP_CUH

/*
 * Batch Eisenstein Rhythmic Snap — classify N interval pairs in parallel.
 *
 * This is the bread and butter of GPU-accelerated ensemble analysis.
 * Each thread processes one interval pair, projecting onto the Eisenstein
 * lattice and classifying the rhythmic shape.
 */

/* Snap shapes */
#define SNAP_SHAPE_BURST    0
#define SNAP_SHAPE_STEADY   1
#define SNAP_SHAPE_COLLAPSE 2
#define SNAP_SHAPE_ACCEL    3
#define SNAP_SHAPE_DECEL    4

/* Batch snap kernel */
__global__ void eisenstein_rhythmic_snap_kernel(
    const double* interval_a,  // [N] first interval
    const double* interval_b,  // [N] second interval
    const double* base_tempo,  // [1] reference tempo
    int* snap_a,               // [N] snapped Eisenstein a
    int* snap_b,               // [N] snapped Eisenstein b
    int* shapes,               // [N] shape classification
    double* norms,             // [N] Eisenstein norm
    int N
);

/* Host wrapper */
void snap_cuda_batch(
    const double* d_interval_a,
    const double* d_interval_b,
    const double* d_base_tempo,
    int* d_snap_a,
    int* d_snap_b,
    int* d_shapes,
    double* d_norms,
    int N,
    cudaStream_t stream = 0
);

#endif /* FLUX_MIDI_CUDA_SNAP_CUH */
