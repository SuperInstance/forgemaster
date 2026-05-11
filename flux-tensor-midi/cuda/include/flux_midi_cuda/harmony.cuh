#ifndef FLUX_MIDI_CUDA_HARMONY_CUH
#define FLUX_MIDI_CUDA_HARMONY_CUH

/*
 * Batch Harmony — pairwise Jaccard, cosine, and connectome on GPU.
 *
 * For N rooms, we compute N*(N-1)/2 pairwise harmony scores.
 * The GPU parallelizes across all pairs.
 */

/* Batch Jaccard: compute pairwise Jaccard similarity for N rooms.
 * saliences: [N * 9] flattened
 * output: [N * N] matrix (upper triangle filled, diagonal = 1.0) */
__global__ void harmony_batch_jaccard_kernel(
    const double* saliences,
    double* output,
    double threshold,
    int N
);

/* Batch connectome alignment: compare listening sets.
 * listen_matrix: [N * M] binary matrix (room i listens to target j)
 * output: [N * N] alignment scores */
__global__ void harmony_batch_connectome_kernel(
    const int* listen_matrix,  // [N * M] binary
    double* output,            // [N * N]
    int N, int M
);

/* Host wrappers */
void harmony_cuda_batch_jaccard(
    const double* d_saliences, double* d_output,
    double threshold, int N,
    cudaStream_t stream = 0
);

void harmony_cuda_batch_connectome(
    const int* d_listen_matrix, double* d_output,
    int N, int M,
    cudaStream_t stream = 0
);

#endif /* FLUX_MIDI_CUDA_HARMONY_CUH */
