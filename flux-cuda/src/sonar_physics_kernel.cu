/*
 * sonar_physics_kernel.cu — Batch sonar physics kernels
 *
 * - Mackenzie 1981 sound speed equation (vectorized)
 * - Francois-Garrison 1982 absorption calculation
 * - Simple ray tracing kernel for multi-path sonar simulation
 * - All double precision
 */

#include "flux_cuda.h"
#include <math.h>

/* ═══════════════════════════════════════════════════════════════
 *  Mackenzie 1981 sound speed equation
 *
 *  c(D,T,S) = 1448.96 + 4.591T - 5.304e-2 T² + 2.374e-4 T³
 *             + 1.340(S-35) + 1.630e-2 D + 1.675e-7 D²
 *             - 1.025e-2 T(S-35) - 7.139e-13 T D³
 *
 *  D = depth (m), T = temperature (°C), S = salinity (PSU)
 * ═════════════════════════════════════════════════════════════ */

__device__ __forceinline__
double mackenzie_sound_speed(double D, double T, double S)
{
    return 1448.96
         + 4.591 * T
         - 5.304e-2 * T * T
         + 2.374e-4 * T * T * T
         + 1.340 * (S - 35.0)
         + 1.630e-2 * D
         + 1.675e-7 * D * D
         - 1.025e-2 * T * (S - 35.0)
         - 7.139e-13 * T * D * D * D;
}

/* ═══════════════════════════════════════════════════════════════
 *  Francois-Garrison 1982 absorption
 *
 *  α(f) = A1P1f1f²/(f1²+f²) + A2P2f2f²/(f2²+f²) + A3P3f²
 *
 *  Simplified for typical ocean conditions.
 *  f in kHz, returns dB/km
 * ═════════════════════════════════════════════════════════════ */

__device__ __forceinline__
double francois_garrison_absorption(double f, double T, double D, double S)
{
    /* Boric acid relaxation frequency (kHz) */
    double f1 = 0.78 * sqrt(S / 35.0) * pow(10.0, T / 26.0);
    /* Magnesium sulfate relaxation frequency (kHz) */
    double f2 = 42.0 * pow(10.0, T / 17.0);

    /* Pressure corrections (depth in meters) */
    double P = 1.0 + D / 10.0; /* approximate pressure in atm */

    /* Temperature-dependent coefficients */
    double A1 = 0.106 * pow((1.0 + T) / (1.0 + T + 3.85e-4 * S), 0.5);
    double A2 = 0.52 * (1.0 + T / 43.0) * pow(S / 35.0, 0.5);
    double A3 = 0.00049;

    double P1 = 1.0;
    double P2 = 1.0 - 1.26e-2 * D / 1000.0; /* depth correction */
    double P3 = 1.0 - 3.0e-3 * D / 1000.0;

    double f2_sq = f * f;
    double alpha = A1 * P1 * f1 * f2_sq / (f1 * f1 + f2_sq)
                 + A2 * P2 * f2 * f2_sq / (f2 * f2 + f2_sq)
                 + A3 * P3 * f2_sq;

    return alpha; /* dB/km */
}

/* ═══════════════════════════════════════════════════════════════
 *  Batch sound speed + absorption kernel
 *
 *  Each thread processes one sample.
 * ═════════════════════════════════════════════════════════════ */

__launch_bounds__(256, 8)
__global__ void sonar_physics_batch_kernel(
    const double* __restrict__ depths,
    const double* __restrict__ temps,
    const double* __restrict__ salinities,
    const double* __restrict__ freqs,
    double*       __restrict__ sound_speeds,
    double*       __restrict__ absorptions,
    int count)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;

    double D = depths[idx];
    double T = temps[idx];
    double S = salinities[idx];
    double f = freqs[idx];

    sound_speeds[idx] = mackenzie_sound_speed(D, T, S);
    absorptions[idx]  = francois_garrison_absorption(f, T, D, S);
}

/* ═══════════════════════════════════════════════════════════════
 *  Ray tracing kernel — multi-path sonar simulation
 *
 *  Simple ray tracer using Snell's law in a layered medium.
 *  Each thread traces one ray. Layers defined by sound speed profile.
 *  Inputs: source depth, receiver depth, range, sound speed profile
 *  Outputs: travel time, arrival amplitude, path length
 * ═════════════════════════════════════════════════════════════ */

#define MAX_LAYERS 256
#define MAX_RAY_STEPS 10000
#define RAY_TRACE_DT 0.001 /* seconds */

typedef struct {
    double travel_time;    /* seconds */
    double amplitude;      /* relative (0-1) */
    double path_length;    /* meters */
    int    surface_bounces;
    int    bottom_bounces;
} ray_trace_result_t;

__device__ double interpolate_sound_speed(
    double depth,
    const double* layer_depths,
    const double* layer_speeds,
    int num_layers)
{
    if (depth <= layer_depths[0]) return layer_speeds[0];
    if (depth >= layer_depths[num_layers - 1]) return layer_speeds[num_layers - 1];

    /* Binary search for layer */
    int lo = 0, hi = num_layers - 2;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (layer_depths[mid + 1] < depth) lo = mid + 1;
        else hi = mid;
    }

    double d0 = layer_depths[lo], d1 = layer_depths[lo + 1];
    double c0 = layer_speeds[lo], c1 = layer_speeds[lo + 1];
    double t = (depth - d0) / (d1 - d0);
    return c0 + t * (c1 - c0);
}

__global__ void ray_trace_kernel(
    const double* __restrict__ source_depths,
    const double* __restrict__ receiver_depths,
    const double* __restrict__ ranges,
    const double* __restrict__ launch_angles, /* degrees from horizontal */
    const double* __restrict__ layer_depths,  /* [num_layers] shared profile */
    const double* __restrict__ layer_speeds,  /* [num_layers] shared profile */
    int           num_layers,
    double        max_depth,
    ray_trace_result_t* __restrict__ results,
    int           count)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;

    double src_depth = source_depths[idx];
    double rcv_depth = receiver_depths[idx];
    double range     = ranges[idx];
    double angle_deg = launch_angles[idx];

    /* Initial conditions */
    double angle = angle_deg * M_PI / 180.0; /* radians */
    double c0 = interpolate_sound_speed(src_depth, layer_depths, layer_speeds, num_layers);

    double x = 0.0;     /* horizontal distance */
    double z = src_depth; /* current depth */
    double vx = c0 * cos(angle);
    double vz = c0 * sin(angle);
    double time = 0.0;
    double path_len = 0.0;
    int surf_bounces = 0, bot_bounces = 0;

    double ds = 1.0; /* step size in meters */

    for (int step = 0; step < MAX_RAY_STEPS && x < range; ++step) {
        double c = interpolate_sound_speed(z, layer_depths, layer_speeds, num_layers);
        double speed = sqrt(vx * vx + vz * vz);

        /* Snell's law: constant c*cos(theta) along ray */
        double snell_const = c0 * cos(angle);

        /* Step */
        double dt = ds / fmax(speed, 1.0);
        x += vx * dt;
        z += vz * dt;
        time += dt;
        path_len += ds;

        /* Update velocity with local sound speed gradient */
        double c_new = interpolate_sound_speed(z, layer_depths, layer_speeds, num_layers);
        double grad = (c_new - c) / fmax(ds, 1e-10);
        vz += grad * sin(angle) * dt;
        vx = sqrt(fmax(c_new * c_new - vz * vz, 0.0));
        angle = atan2(vz, vx);

        /* Boundary reflections */
        if (z <= 0.0) {
            z = -z;
            vz = fabs(vz);
            surf_bounces++;
        }
        if (z >= max_depth) {
            z = 2.0 * max_depth - z;
            vz = -fabs(vz);
            bot_bounces++;
        }
    }

    /* Check if ray reached the receiver */
    double depth_error = fabs(z - rcv_depth);
    double range_error = fabs(x - range);

    results[idx].travel_time    = time;
    results[idx].amplitude      = exp(-path_len * 0.001); /* simple spreading loss */
    results[idx].path_length    = path_len;
    results[idx].surface_bounces = surf_bounces;
    results[idx].bottom_bounces  = bot_bounces;
}
