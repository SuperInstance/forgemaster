#ifndef FLUX_MIDI_CUDA_FLUX_CUH
#define FLUX_MIDI_CUDA_FLUX_CUH

/*
 * GPU FLUX operations — batch vector math for large ensembles.
 *
 * When you have hundreds or thousands of rooms, computing pairwise
 * harmony on CPU becomes the bottleneck. These kernels parallelize
 * the FLUX operations across CUDA threads.
 */

#define FLUX_CUDA_CHANNELS 9

/* Device-side FLUX channel */
typedef struct {
    double salience;
    double tolerance;
} FluxChannelCUDA;

/* Batch distance: compute distance from room[i] to room[j] for all i,j pairs.
 * saliences: [N * 9] flattened salience values
 * distances: [N * N] output distance matrix
 * N: number of rooms */
__global__ void flux_batch_distance_kernel(
    const double* saliences,  // [N * 9]
    double* distances,        // [N * N]
    int N
);

/* Batch cosine similarity */
__global__ void flux_batch_cosine_kernel(
    const double* saliences,
    double* cosines,
    int N
);

/* Batch blend: out[i] = alpha * a[i] + (1-alpha) * b[i] */
__global__ void flux_batch_blend_kernel(
    const double* saliences_a,
    const double* saliences_b,
    double alpha,
    double* saliences_out,
    int N
);

/* Batch decay: multiply all saliences by factor */
__global__ void flux_batch_decay_kernel(
    double* saliences,
    double decay,
    int N
);

/* Host API wrappers */
void flux_cuda_batch_distance(const double* d_saliences, double* d_distances, int N,
                              cudaStream_t stream = 0);
void flux_cuda_batch_cosine(const double* d_saliences, double* d_cosines, int N,
                            cudaStream_t stream = 0);

#endif /* FLUX_MIDI_CUDA_FLUX_CUH */
