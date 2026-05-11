#include "flux_midi_cuda/clock.cuh"

__global__ void check_t_zero_kernel(
    const double* t_last,
    const double* intervals,
    const double* t_now,
    double* deltas,
    int* missed_ticks,
    int* states,
    int N
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;

    double expected = t_last[i] + intervals[i];
    double elapsed = t_now[0] - t_last[i];
    double ratio = elapsed / intervals[i];

    deltas[i] = t_now[0] - expected;
    missed_ticks[i] = (int)(elapsed / intervals[i]) - 1;
    if (missed_ticks[i] < 0) missed_ticks[i] = 0;

    if (ratio < 1.5)       states[i] = 0;  /* on_time */
    else if (ratio < 3.0)  states[i] = 1;  /* late */
    else if (ratio < 10.0) states[i] = 2;  /* silent */
    else                    states[i] = 3;  /* dead */
}

void clock_cuda_batch_check(
    const double* d_t_last,
    const double* d_intervals,
    const double* d_t_now,
    double* d_deltas,
    int* d_missed_ticks,
    int* d_states,
    int N,
    cudaStream_t stream
) {
    int block = 256;
    int grid = (N + 255) / 256;
    check_t_zero_kernel<<<grid, block, 0, stream>>>(
        d_t_last, d_intervals, d_t_now,
        d_deltas, d_missed_ticks, d_states, N);
}
