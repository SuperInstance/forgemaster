#ifndef FLUX_MIDI_CUDA_ENSEMBLE_CUH
#define FLUX_MIDI_CUDA_ENSEMBLE_CUH

/*
 * GPU Ensemble Simulation — run the full ensemble on GPU.
 *
 * Combines batch T-0 check, batch harmony, and batch snap
 * into a single pass that processes all rooms simultaneously.
 */

typedef struct {
    int    n_rooms;
    double master_tempo;
    double t_now;
    /* Device pointers — set before launch */
    double* d_saliences;      // [n_rooms * 9]
    double* d_intervals;      // [n_rooms]
    double* d_t_last;         // [n_rooms]
    /* Output device pointers */
    int*    d_tzero_states;   // [n_rooms]
    double* d_tzero_deltas;   // [n_rooms]
    double* d_harmony_matrix; // [n_rooms * n_rooms]
} EnsembleGPU;

/* Initialize GPU ensemble (allocate device memory) */
void ensemble_cuda_init(EnsembleGPU* ens, int n_rooms);

/* Free GPU ensemble */
void ensemble_cuda_free(EnsembleGPU* ens);

/* Run one tick: T-0 check + harmony computation */
void ensemble_cuda_tick(EnsembleGPU* ens, double t_now, cudaStream_t stream = 0);

/* Copy results back to host */
void ensemble_cuda_download_tzero(const EnsembleGPU* ens, int* h_states, double* h_deltas);
void ensemble_cuda_download_harmony(const EnsembleGPU* ens, double* h_matrix);

#endif /* FLUX_MIDI_CUDA_ENSEMBLE_CUH */
