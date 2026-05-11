#include "flux_midi_cuda/snap.cuh"
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

__global__ void eisenstein_rhythmic_snap_kernel(
    const double* interval_a,
    const double* interval_b,
    const double* base_tempo,
    int* snap_a,
    int* snap_b,
    int* shapes,
    double* norms,
    int N
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;

    /* Normalize by base tempo */
    double a = interval_a[i] / base_tempo[0];
    double b = interval_b[i] / base_tempo[0];

    /* Eisenstein coordinates: (a + b/√3, 2b/√3) */
    const double sqrt3 = 1.7320508075688772;
    double af = a + b / sqrt3;
    double bf = 2.0 * b / sqrt3;

    /* Round to nearest lattice point */
    snap_a[i] = (int)round(af);
    snap_b[i] = (int)round(bf);

    /* Eisenstein norm: a² - ab + b² */
    int ea = snap_a[i], eb = snap_b[i];
    norms[i] = (double)(ea * ea - ea * eb + eb * eb);

    /* Classify by ratio b/a */
    double ratio = (a > 1e-10) ? b / a : 999.0;

    if (ratio < 0.3)       shapes[i] = SNAP_SHAPE_COLLAPSE;
    else if (ratio < 0.7)  shapes[i] = SNAP_SHAPE_DECEL;
    else if (ratio < 1.5)  shapes[i] = SNAP_SHAPE_STEADY;
    else if (ratio < 3.0)  shapes[i] = SNAP_SHAPE_ACCEL;
    else                    shapes[i] = SNAP_SHAPE_BURST;
}

void snap_cuda_batch(
    const double* d_interval_a,
    const double* d_interval_b,
    const double* d_base_tempo,
    int* d_snap_a,
    int* d_snap_b,
    int* d_shapes,
    double* d_norms,
    int N,
    cudaStream_t stream
) {
    int block = 256;
    int grid = (N + 255) / 256;
    eisenstein_rhythmic_snap_kernel<<<grid, block, 0, stream>>>(
        d_interval_a, d_interval_b, d_base_tempo,
        d_snap_a, d_snap_b, d_shapes, d_norms, N);
}
