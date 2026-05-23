/*
 * sonar_cuda.cu — GPU kernels for SonarVision
 *
 * CUDA kernels for batch-accelerated acoustic physics on Jetson Xavier (sm_72).
 *
 * Kernels:
 *   mackenzie_kernel    — batch sound speed (10K+ points)
 *   absorption_kernel   — batch Francois-Garrison absorption
 *   ray_trace_kernel    — one ray per thread
 *   sonar_image_kernel  — generate sonar image from acoustic model
 */

#include <cuda_runtime.h>
#include <math.h>

/* ── Device-side Mackenzie 1981 ──────────────────────────────────── */

__device__ __forceinline__
double mackenzie_device(double T, double S, double D)
{
    double T2  = T * T;
    double T3  = T2 * T;
    double D2  = D * D;
    double D3  = D2 * D;
    double S35 = S - 35.0;

    return 1448.96
         + 4.591 * T
         - 5.304e-2 * T2
         + 2.374e-4 * T3
         + 1.340 * S35
         + 1.630e-2 * D
         + 1.675e-7 * D2
         - 1.025e-2 * T * S35
         - 7.139e-13 * T * D3;
}

/* ── Device-side Francois-Garrison 1982 ──────────────────────────── */

__device__ __forceinline__
double absorption_device(double f, double T, double S, double D, double pH)
{
    double f2 = f * f;

    /* Boric acid relaxation frequency (kHz) */
    double f1 = 0.78 * sqrt(S / 35.0) * pow(10.0, T / 26.0);

    /* pH-dependent coefficient */
    double pH_term = pow(10.0, pH - 8.0);
    double A1 = 0.106 * (pH_term / (1.0 + pH_term));

    /* Magnesium sulfate relaxation frequency (kHz) */
    double f2relax = 42.0 * pow(10.0, T / 17.0);

    /* MgSO4 coefficient */
    double A2 = 0.52 * (1.0 + T / 43.0) * (S / 35.0);

    /* Pressure correction for MgSO4 */
    double P2 = 1.0 - 2.36e-2 * D + 5.22e-7 * D * D;

    /* Pure water coefficient */
    double A3;
    if (T < 20.0) {
        A3 = 4.937e-4 - 2.59e-5 * T + 9.11e-7 * T * T - 1.50e-8 * T * T * T;
    } else {
        A3 = 3.964e-4 - 1.146e-5 * T + 1.45e-7 * T * T - 6.5e-10 * T * T * T;
    }

    double P3 = 1.0 - 3.83e-5 * D + 4.90e-10 * D * D;

    /* Total absorption (dB/km) */
    double f1sq = f1 * f1;
    double f2sq = f2relax * f2relax;
    return A1 * f1 * f2 / (f1sq + f2)
         + A2 * P2 * f2relax * f2 / (f2sq + f2)
         + A3 * P3 * f2;
}

/* ── Kernel: batch Mackenzie ─────────────────────────────────────── */

extern "C"
__global__
void mackenzie_kernel(const double * __restrict__ temps,
                      const double * __restrict__ sals,
                      const double * __restrict__ depths,
                      double * __restrict__ out,
                      int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        out[idx] = mackenzie_device(temps[idx], sals[idx], depths[idx]);
    }
}

/* ── Kernel: batch absorption ────────────────────────────────────── */

extern "C"
__global__
void absorption_kernel(const double * __restrict__ freqs,
                       const double * __restrict__ temps,
                       const double * __restrict__ sals,
                       const double * __restrict__ depths,
                       const double * __restrict__ phs,
                       double * __restrict__ out,
                       int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        out[idx] = absorption_device(freqs[idx], temps[idx], sals[idx],
                                     depths[idx], phs[idx]);
    }
}

/* ── Kernel: batch ray trace (simplified — step-based) ───────────── */

/*
 * Each thread traces one ray through a layered SSP.
 * The SSP is stored in constant memory or passed as flat arrays.
 * This simplified version uses a uniform-gradient approximation.
 */

extern "C"
__global__
void ray_trace_kernel(const double * __restrict__ layer_depths,
                      const double * __restrict__ layer_speeds,
                      int n_layers,
                      const double * __restrict__ src_depths,
                      const double * __restrict__ angles,
                      double max_range,
                      int max_bounces,
                      /* outputs: travel_time, path_length, tl, surf, bottom */
                      double * __restrict__ out_time,
                      double * __restrict__ out_path,
                      double * __restrict__ out_tl,
                      int    * __restrict__ out_surf,
                      int    * __restrict__ out_bot,
                      int n_rays)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n_rays) return;

    double z = src_depths[idx];
    double theta = angles[idx];
    double max_depth = layer_depths[n_layers - 1];

    double total_range = 0.0;
    double total_time  = 0.0;
    double path_length = 0.0;
    int surf_bounces = 0;
    int bot_bounces  = 0;
    int bounces = 0;

    double dr = 10.0; /* 10 m step */

    int max_iter = 100000;
    while (total_range < max_range && max_iter-- > 0) {
        if (max_bounces > 0 && bounces >= max_bounces) break;

        /* Find layer */
        double c = layer_speeds[0];
        for (int i = 0; i < n_layers - 1; i++) {
            if (z >= layer_depths[i] && z < layer_depths[i + 1]) {
                double t = (z - layer_depths[i]) /
                           (layer_depths[i + 1] - layer_depths[i] + 1e-12);
                c = layer_speeds[i] + t * (layer_speeds[i + 1] - layer_speeds[i]);
                break;
            }
        }
        if (z >= layer_depths[n_layers - 1])
            c = layer_speeds[n_layers - 1];

        /* Step */
        double dz = dr * tan(theta);
        double z_new = z + dz;

        if (z_new < 0.0) {
            z_new = -z_new;
            theta = -theta;
            surf_bounces++;
            bounces++;
        }
        if (z_new > max_depth) {
            z_new = 2.0 * max_depth - z_new;
            theta = -theta;
            bot_bounces++;
            bounces++;
        }
        if (z_new < 0.0) z_new = 0.0;
        if (z_new > max_depth) z_new = max_depth;

        double ds = sqrt(dr * dr + dz * dz);
        total_time  += ds / (c + 1e-12);
        path_length += ds;
        total_range += dr;

        /* Snell update */
        double c_new = layer_speeds[0];
        for (int i = 0; i < n_layers - 1; i++) {
            if (z_new >= layer_depths[i] && z_new < layer_depths[i + 1]) {
                double t = (z_new - layer_depths[i]) /
                           (layer_depths[i + 1] - layer_depths[i] + 1e-12);
                c_new = layer_speeds[i] + t * (layer_speeds[i + 1] - layer_speeds[i]);
                break;
            }
        }
        if (z_new >= layer_depths[n_layers - 1])
            c_new = layer_speeds[n_layers - 1];

        double cos_new = cos(theta) * c_new / (c + 1e-12);
        if (cos_new > 1.0) cos_new = 1.0;
        if (cos_new < -1.0) cos_new = -1.0;
        theta = acos(cos_new);
        if (dz < 0) theta = -theta;

        z = z_new;
    }

    double tl = (total_range > 1.0) ? 20.0 * log10(total_range) : 0.0;

    out_time[idx] = total_time;
    out_path[idx] = path_length;
    out_tl[idx]   = tl;
    out_surf[idx] = surf_bounces;
    out_bot[idx]  = bot_bounces;
}

/* ── Kernel: sonar image generation ──────────────────────────────── */

/*
 * Generates a 2D sonar image (range × bearing) from acoustic model.
 * Each pixel (r, b) contains the expected reverberation + target return.
 *
 * Output: float image [height × width] in dB.
 */

extern "C"
__global__
void sonar_image_kernel(const double * __restrict__ ranges,     /* [n_range] */
                        const double * __restrict__ bearings,   /* [n_bearing] */
                        double source_level,
                        double target_strength,
                        const double * __restrict__ absorption, /* [n_range] */
                        int n_range, int n_bearing,
                        float * __restrict__ image)
{
    int ir = blockIdx.x * blockDim.x + threadIdx.x;
    int ib = blockIdx.y * blockDim.y + threadIdx.y;

    if (ir >= n_range || ib >= n_bearing) return;

    double R = ranges[ir];
    double alpha = absorption[ir];  /* dB/km at this range */

    /* Spherical spreading + absorption */
    double tl = 20.0 * log10(R + 1e-30) + alpha * R / 1000.0;

    /* Background reverberation (simplified Lambert) */
    double reverb = -2.0 * tl - 40.0;  /* floor */

    /* Signal: SL + TS − 2TL */
    double signal = source_level + target_strength - 2.0 * tl;

    /* Image pixel: max of signal and reverberation */
    float pixel = (float)fmax(signal, reverb);

    image[ib * n_range + ir] = pixel;
}
