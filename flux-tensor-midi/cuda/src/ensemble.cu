#include "flux_midi_cuda/ensemble.cuh"
#include "flux_midi_cuda/clock.cuh"
#include "flux_midi_cuda/harmony.cuh"
#include <cstdio>
#include <cuda_runtime.h>

#define CUDA_CHECK(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", \
                __FILE__, __LINE__, cudaGetErrorString(err)); \
    } \
} while(0)

void ensemble_cuda_init(EnsembleGPU* ens, int n_rooms) {
    ens->n_rooms = n_rooms;

    size_t flux_bytes = n_rooms * 9 * sizeof(double);
    size_t room_bytes = n_rooms * sizeof(double);
    size_t matrix_bytes = n_rooms * n_rooms * sizeof(double);
    size_t state_bytes = n_rooms * sizeof(int);

    CUDA_CHECK(cudaMalloc(&ens->d_saliences, flux_bytes));
    CUDA_CHECK(cudaMalloc(&ens->d_intervals, room_bytes));
    CUDA_CHECK(cudaMalloc(&ens->d_t_last, room_bytes));
    CUDA_CHECK(cudaMalloc(&ens->d_tzero_states, state_bytes));
    CUDA_CHECK(cudaMalloc(&ens->d_tzero_deltas, room_bytes));
    CUDA_CHECK(cudaMalloc(&ens->d_harmony_matrix, matrix_bytes));

    /* Zero-initialize */
    CUDA_CHECK(cudaMemset(ens->d_tzero_states, 0, state_bytes));
    CUDA_CHECK(cudaMemset(ens->d_tzero_deltas, 0, room_bytes));
}

void ensemble_cuda_free(EnsembleGPU* ens) {
    CUDA_CHECK(cudaFree(ens->d_saliences));
    CUDA_CHECK(cudaFree(ens->d_intervals));
    CUDA_CHECK(cudaFree(ens->d_t_last));
    CUDA_CHECK(cudaFree(ens->d_tzero_states));
    CUDA_CHECK(cudaFree(ens->d_tzero_deltas));
    CUDA_CHECK(cudaFree(ens->d_harmony_matrix));
}

void ensemble_cuda_tick(EnsembleGPU* ens, double t_now, cudaStream_t stream) {
    /* Allocate temporary t_now on device */
    double* d_t_now;
    CUDA_CHECK(cudaMalloc(&d_t_now, sizeof(double)));
    CUDA_CHECK(cudaMemcpy(d_t_now, &t_now, sizeof(double), cudaMemcpyHostToDevice));

    /* Allocate temp missed_ticks */
    int* d_missed;
    CUDA_CHECK(cudaMalloc(&d_missed, ens->n_rooms * sizeof(int)));

    /* Batch T-0 check */
    clock_cuda_batch_check(
        ens->d_t_last, ens->d_intervals, d_t_now,
        ens->d_tzero_deltas, d_missed, ens->d_tzero_states,
        ens->n_rooms, stream);

    /* Batch harmony (Jaccard with threshold 0.5) */
    harmony_cuda_batch_jaccard(
        ens->d_saliences, ens->d_harmony_matrix,
        0.5, ens->n_rooms, stream);

    CUDA_CHECK(cudaFree(d_t_now));
    CUDA_CHECK(cudaFree(d_missed));
}

void ensemble_cuda_download_tzero(const EnsembleGPU* ens, int* h_states, double* h_deltas) {
    int n = ens->n_rooms;
    CUDA_CHECK(cudaMemcpy(h_states, ens->d_tzero_states, n * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(h_deltas, ens->d_tzero_deltas, n * sizeof(double), cudaMemcpyDeviceToHost));
}

void ensemble_cuda_download_harmony(const EnsembleGPU* ens, double* h_matrix) {
    int n = ens->n_rooms;
    CUDA_CHECK(cudaMemcpy(h_matrix, ens->d_harmony_matrix,
                          n * n * sizeof(double), cudaMemcpyDeviceToHost));
}
