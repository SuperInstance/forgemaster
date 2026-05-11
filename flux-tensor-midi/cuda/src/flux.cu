#include "flux_midi_cuda/flux.cuh"
#include <cmath>

__global__ void flux_batch_distance_kernel(
    const double* saliences,
    double* distances,
    int N
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;
    if (i >= N || j >= N) return;

    double sum = 0.0;
    for (int c = 0; c < FLUX_CUDA_CHANNELS; c++) {
        double d = saliences[i * FLUX_CUDA_CHANNELS + c] -
                   saliences[j * FLUX_CUDA_CHANNELS + c];
        sum += d * d;
    }
    distances[i * N + j] = sqrt(sum);
}

__global__ void flux_batch_cosine_kernel(
    const double* saliences,
    double* cosines,
    int N
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;
    if (i >= N || j >= N) return;

    double dot = 0.0, norm_a = 0.0, norm_b = 0.0;
    for (int c = 0; c < FLUX_CUDA_CHANNELS; c++) {
        double a = saliences[i * FLUX_CUDA_CHANNELS + c];
        double b = saliences[j * FLUX_CUDA_CHANNELS + c];
        dot += a * b;
        norm_a += a * a;
        norm_b += b * b;
    }
    double denom = sqrt(norm_a) * sqrt(norm_b);
    cosines[i * N + j] = (denom < 1e-12) ? 0.0 : dot / denom;
}

__global__ void flux_batch_blend_kernel(
    const double* saliences_a,
    const double* saliences_b,
    double alpha,
    double* saliences_out,
    int N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int c = idx % FLUX_CUDA_CHANNELS;
    int room = idx / FLUX_CUDA_CHANNELS;
    if (room >= N) return;

    saliences_out[idx] = alpha * saliences_a[idx] +
                         (1.0 - alpha) * saliences_b[idx];
}

__global__ void flux_batch_decay_kernel(
    double* saliences,
    double decay,
    int N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N * FLUX_CUDA_CHANNELS) return;
    saliences[idx] *= decay;
}

/* Host wrappers */
void flux_cuda_batch_distance(const double* d_saliences, double* d_distances,
                              int N, cudaStream_t stream) {
    dim3 block(16, 16);
    dim3 grid((N + 15) / 16, (N + 15) / 16);
    flux_batch_distance_kernel<<<grid, block, 0, stream>>>(
        d_saliences, d_distances, N);
}

void flux_cuda_batch_cosine(const double* d_saliences, double* d_cosines,
                            int N, cudaStream_t stream) {
    dim3 block(16, 16);
    dim3 grid((N + 15) / 16, (N + 15) / 16);
    flux_batch_cosine_kernel<<<grid, block, 0, stream>>>(
        d_saliences, d_cosines, N);
}
