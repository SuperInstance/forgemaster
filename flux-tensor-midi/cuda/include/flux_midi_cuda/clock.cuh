#ifndef FLUX_MIDI_CUDA_CLOCK_CUH
#define FLUX_MIDI_CUDA_CLOCK_CUH

/*
 * Batch T-Zero Check — the killer GPU use case.
 *
 * Check timing state for N rooms simultaneously. This is what makes
 * GPU acceleration worthwhile: a 1000-room ensemble needs 1000 timing
 * checks per tick, all embarrassingly parallel.
 *
 * States:
 *   0 = ON_TIME  (< 1.5x interval elapsed)
 *   1 = LATE     (1.5x - 3.0x)
 *   2 = SILENT   (3.0x - 10.0x)
 *   3 = DEAD     (> 10.0x)
 */

__global__ void check_t_zero_kernel(
    const double* t_last,      // [N] last observation time
    const double* intervals,   // [N] expected intervals
    const double* t_now,       // [1] current time
    double* deltas,            // [N] output: delta from T-0
    int* missed_ticks,         // [N] output: number of missed ticks
    int* states,               // [N] output: 0=on_time, 1=late, 2=silent, 3=dead
    int N
);

/* Host wrapper */
void clock_cuda_batch_check(
    const double* d_t_last,
    const double* d_intervals,
    const double* d_t_now,
    double* d_deltas,
    int* d_missed_ticks,
    int* d_states,
    int N,
    cudaStream_t stream = 0
);

#endif /* FLUX_MIDI_CUDA_CLOCK_CUH */
