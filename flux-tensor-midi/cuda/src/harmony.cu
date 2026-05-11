#include "flux_midi_cuda/harmony.cuh"
#include <cmath>

__global__ void harmony_batch_jaccard_kernel(
    const double* saliences,
    double* output,
    double threshold,
    int N
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;
    if (i >= N || j >= N) return;

    if (i == j) {
        output[i * N + j] = 1.0;
        return;
    }

    int intersection = 0, union_count = 0;
    for (int c = 0; c < 9; c++) {
        int a_active = saliences[i * 9 + c] > threshold;
        int b_active = saliences[j * 9 + c] > threshold;
        if (a_active || b_active) union_count++;
        if (a_active && b_active) intersection++;
    }
    output[i * N + j] = (union_count == 0) ? 1.0 : (double)intersection / union_count;
}

__global__ void harmony_batch_connectome_kernel(
    const int* listen_matrix,
    double* output,
    int N, int M
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;
    if (i >= N || j >= N) return;

    if (i == j) {
        output[i * N + j] = 1.0;
        return;
    }

    int shared = 0, total_a = 0, total_b = 0;
    for (int k = 0; k < M; k++) {
        int a = listen_matrix[i * M + k];
        int b = listen_matrix[j * M + k];
        if (a) total_a++;
        if (b) total_b++;
        if (a && b) shared++;
    }

    int union_size = total_a + total_b - shared;
    output[i * N + j] = (union_size == 0) ? 1.0 : (double)shared / union_size;
}

void harmony_cuda_batch_jaccard(
    const double* d_saliences, double* d_output,
    double threshold, int N,
    cudaStream_t stream
) {
    dim3 block(16, 16);
    dim3 grid((N + 15) / 16, (N + 15) / 16);
    harmony_batch_jaccard_kernel<<<grid, block, 0, stream>>>(
        d_saliences, d_output, threshold, N);
}

void harmony_cuda_batch_connectome(
    const int* d_listen_matrix, double* d_output,
    int N, int M,
    cudaStream_t stream
) {
    dim3 block(16, 16);
    dim3 grid((N + 15) / 16, (N + 15) / 16);
    harmony_batch_connectome_kernel<<<grid, block, 0, stream>>>(
        d_listen_matrix, d_output, N, M);
}
