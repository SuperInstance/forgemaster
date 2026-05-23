/*
 * host_api.cu — Host-side CUDA interface for SonarVision
 *
 * Memory management, kernel launch, async streams, device selection.
 * Targets Jetson Xavier (sm_72) and discrete GPUs.
 */

#include "sonar_vision.h"
#include <cuda_runtime.h>
#include <stdlib.h>
#include <string.h>

/* ── CUDA context structure ──────────────────────────────────────── */

struct sv_cuda_ctx {
    int         device_id;
    cudaStream_t stream;
    /* Pinned host buffers for async transfer */
    double     *h_mackenzie_in[3];  /* temps, sals, depths */
    double     *h_mackenzie_out;
    double     *d_mackenzie_in[3];
    double     *d_mackenzie_out;
    int         buf_capacity;       /* current allocation size */
};

/* ── Helper: check CUDA errors ───────────────────────────────────── */

static sv_error_t cuda_check(cudaError_t err)
{
    if (err != cudaSuccess) return SV_ERR_CUDA;
    return SV_OK;
}

/* ── Device selection ─────────────────────────────────────────────── */

/**
 * Select best device. Prefers Jetson Xavier (integrated GPU),
 * falls back to first available device.
 */
static int select_device(void)
{
    int n_devices = 0;
    cudaGetDeviceCount(&n_devices);
    if (n_devices == 0) return -1;

    for (int i = 0; i < n_devices; i++) {
        cudaDeviceProp prop;
        cudaGetDeviceProperties(&prop, i);
        /* Jetson Xavier: integrated = 1, name contains "Xavier" or "Tegra" */
        if (prop.integrated ||
            strstr(prop.name, "Xavier") ||
            strstr(prop.name, "Tegra") ||
            strstr(prop.name, "Orin")) {
            return i;
        }
    }

    return 0;  /* default: first GPU */
}

/* ── Buffer management ───────────────────────────────────────────── */

static sv_error_t ensure_buffers(sv_cuda_ctx_t *ctx, int n)
{
    if (n <= ctx->buf_capacity) return SV_OK;

    /* Free old buffers */
    for (int i = 0; i < 3; i++) {
        if (ctx->h_mackenzie_in[i]) cudaFreeHost(ctx->h_mackenzie_in[i]);
        if (ctx->d_mackenzie_in[i]) cudaFree(ctx->d_mackenzie_in[i]);
    }
    if (ctx->h_mackenzie_out) cudaFreeHost(ctx->h_mackenzie_out);
    if (ctx->d_mackenzie_out) cudaFree(ctx->d_mackenzie_out);

    size_t bytes = (size_t)n * sizeof(double);

    for (int i = 0; i < 3; i++) {
        cudaError_t e1 = cudaMallocHost(&ctx->h_mackenzie_in[i], bytes);
        cudaError_t e2 = cudaMalloc(&ctx->d_mackenzie_in[i], bytes);
        if (e1 != cudaSuccess || e2 != cudaSuccess) return SV_ERR_CUDA;
    }

    if (cudaMallocHost(&ctx->h_mackenzie_out, bytes) != cudaSuccess) return SV_ERR_CUDA;
    if (cudaMalloc(&ctx->d_mackenzie_out, bytes) != cudaSuccess) return SV_ERR_CUDA;

    ctx->buf_capacity = n;
    return SV_OK;
}

/* ── Public API ──────────────────────────────────────────────────── */

/* Kernel declarations (defined in sonar_cuda.cu) */
extern "C" {
void mackenzie_kernel(const double*, const double*, const double*,
                      double*, int);
void absorption_kernel(const double*, const double*, const double*,
                       const double*, const double*, double*, int);
}

sv_error_t sv_cuda_create(int device_id, sv_cuda_ctx_t **ctx)
{
    if (!ctx) return SV_ERR_NULL_PTR;

    *ctx = (sv_cuda_ctx_t*)calloc(1, sizeof(sv_cuda_ctx_t));
    if (!*ctx) return SV_ERR_CUDA;

    if (device_id < 0) device_id = select_device();
    if (device_id < 0) { free(*ctx); return SV_ERR_CUDA; }

    cudaError_t err = cudaSetDevice(device_id);
    if (err != cudaSuccess) { free(*ctx); return SV_ERR_CUDA; }

    err = cudaStreamCreate(&(*ctx)->stream);
    if (err != cudaSuccess) { free(*ctx); return SV_ERR_CUDA; }

    (*ctx)->device_id = device_id;
    (*ctx)->buf_capacity = 0;

    return SV_OK;
}

sv_error_t sv_cuda_destroy(sv_cuda_ctx_t *ctx)
{
    if (!ctx) return SV_OK;

    /* Free buffers */
    for (int i = 0; i < 3; i++) {
        if (ctx->h_mackenzie_in[i]) cudaFreeHost(ctx->h_mackenzie_in[i]);
        if (ctx->d_mackenzie_in[i]) cudaFree(ctx->d_mackenzie_in[i]);
    }
    if (ctx->h_mackenzie_out) cudaFreeHost(ctx->h_mackenzie_out);
    if (ctx->d_mackenzie_out) cudaFree(ctx->d_mackenzie_out);

    cudaStreamDestroy(ctx->stream);
    free(ctx);

    return SV_OK;
}

sv_error_t sv_cuda_mackenzie(sv_cuda_ctx_t *ctx,
                             const double *temps, const double *sals,
                             const double *depths, double *out, int n)
{
    if (!ctx || !temps || !sals || !depths || !out) return SV_ERR_NULL_PTR;
    if (n <= 0) return SV_ERR_SIZE_ZERO;

    sv_error_t err = ensure_buffers(ctx, n);
    if (err != SV_OK) return err;

    size_t bytes = (size_t)n * sizeof(double);

    /* Copy input to device */
    cudaMemcpy(ctx->d_mackenzie_in[0], temps, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(ctx->d_mackenzie_in[1], sals, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(ctx->d_mackenzie_in[2], depths, bytes, cudaMemcpyHostToDevice);

    /* Launch kernel */
    int block = 256;
    int grid  = (n + block - 1) / block;

    mackenzie_kernel<<<grid, block, 0, ctx->stream>>>(
        ctx->d_mackenzie_in[0], ctx->d_mackenzie_in[1], ctx->d_mackenzie_in[2],
        ctx->d_mackenzie_out, n);

    /* Copy result back */
    cudaMemcpy(out, ctx->d_mackenzie_out, bytes, cudaMemcpyDeviceToHost);

    cudaStreamSynchronize(ctx->stream);

    cudaError_t cerr = cudaGetLastError();
    if (cerr != cudaSuccess) return SV_ERR_CUDA;

    return SV_OK;
}

sv_error_t sv_cuda_absorption(sv_cuda_ctx_t *ctx,
                              const double *freqs, const double *temps,
                              const double *sals, const double *depths,
                              const double *phs, double *out, int n)
{
    if (!ctx || !freqs || !temps || !sals || !depths || !phs || !out)
        return SV_ERR_NULL_PTR;
    if (n <= 0) return SV_ERR_SIZE_ZERO;

    /* Allocate temporary device buffers for 5 inputs + 1 output */
    double *d_in[5], *d_out;
    size_t bytes = (size_t)n * sizeof(double);

    for (int i = 0; i < 5; i++) {
        if (cudaMalloc(&d_in[i], bytes) != cudaSuccess) return SV_ERR_CUDA;
    }
    if (cudaMalloc(&d_out, bytes) != cudaSuccess) {
        for (int i = 0; i < 5; i++) cudaFree(d_in[i]);
        return SV_ERR_CUDA;
    }

    cudaMemcpy(d_in[0], freqs, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_in[1], temps, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_in[2], sals, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_in[3], depths, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_in[4], phs, bytes, cudaMemcpyHostToDevice);

    int block = 256;
    int grid  = (n + block - 1) / block;

    absorption_kernel<<<grid, block, 0, ctx->stream>>>(
        d_in[0], d_in[1], d_in[2], d_in[3], d_in[4], d_out, n);

    cudaMemcpy(out, d_out, bytes, cudaMemcpyDeviceToHost);
    cudaStreamSynchronize(ctx->stream);

    for (int i = 0; i < 5; i++) cudaFree(d_in[i]);
    cudaFree(d_out);

    cudaError_t cerr = cudaGetLastError();
    if (cerr != cudaSuccess) return SV_ERR_CUDA;

    return SV_OK;
}

sv_error_t sv_cuda_ray_trace(sv_cuda_ctx_t *ctx,
                             const sv_ssp_t *ssp,
                             const double *src_depths,
                             const double *angles,
                             double max_range,
                             sv_ray_mode_t mode,
                             int max_bounces,
                             sv_ray_result_t *out, int n)
{
    if (!ctx || !ssp || !src_depths || !angles || !out) return SV_ERR_NULL_PTR;
    if (n <= 0) return SV_ERR_SIZE_ZERO;

    /* Flatten SSP to device arrays */
    size_t ssp_bytes = (size_t)ssp->n * sizeof(double);
    double *d_layer_depths, *d_layer_speeds;
    double *h_depths_flat = (double*)malloc(ssp_bytes);
    double *h_speeds_flat = (double*)malloc(ssp_bytes);

    for (int i = 0; i < ssp->n; i++) {
        h_depths_flat[i] = ssp->points[i].depth;
        h_speeds_flat[i] = ssp->points[i].speed;
    }

    cudaMalloc(&d_layer_depths, ssp_bytes);
    cudaMalloc(&d_layer_speeds, ssp_bytes);
    cudaMemcpy(d_layer_depths, h_depths_flat, ssp_bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_layer_speeds, h_speeds_flat, ssp_bytes, cudaMemcpyHostToDevice);

    /* Ray inputs */
    size_t ray_bytes = (size_t)n * sizeof(double);
    double *d_src_depths, *d_angles;
    double *d_out_time, *d_out_path, *d_out_tl;
    int    *d_out_surf, *d_out_bot;

    cudaMalloc(&d_src_depths, ray_bytes);
    cudaMalloc(&d_angles, ray_bytes);
    cudaMemcpy(d_src_depths, src_depths, ray_bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_angles, angles, ray_bytes, cudaMemcpyHostToDevice);

    cudaMalloc(&d_out_time, ray_bytes);
    cudaMalloc(&d_out_path, ray_bytes);
    cudaMalloc(&d_out_tl, ray_bytes);
    cudaMalloc(&d_out_surf, (size_t)n * sizeof(int));
    cudaMalloc(&d_out_bot, (size_t)n * sizeof(int));

    /* Kernel declaration */
    extern "C" void ray_trace_kernel(
        const double*, const double*, int,
        const double*, const double*, double, int,
        double*, double*, double*, int*, int*, int);

    int block = 256;
    int grid  = (n + block - 1) / block;

    int mb = (mode == SV_RAY_SHALLOW) ? 20 : 50;
    if (max_bounces > 0) mb = max_bounces;

    ray_trace_kernel<<<grid, block, 0, ctx->stream>>>(
        d_layer_depths, d_layer_speeds, ssp->n,
        d_src_depths, d_angles, max_range, mb,
        d_out_time, d_out_path, d_out_tl, d_out_surf, d_out_bot, n);

    /* Copy results back */
    double *h_time = (double*)malloc(ray_bytes);
    double *h_path = (double*)malloc(ray_bytes);
    double *h_tl   = (double*)malloc(ray_bytes);
    int    *h_surf = (int*)malloc((size_t)n * sizeof(int));
    int    *h_bot  = (int*)malloc((size_t)n * sizeof(int));

    cudaMemcpy(h_time, d_out_time, ray_bytes, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_path, d_out_path, ray_bytes, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_tl, d_out_tl, ray_bytes, cudaMemcpyDeviceToHost);
    cudaMemcpy(h_surf, d_out_surf, (size_t)n * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_bot, d_out_bot, (size_t)n * sizeof(int), cudaMemcpyDeviceToHost);

    cudaStreamSynchronize(ctx->stream);

    for (int i = 0; i < n; i++) {
        out[i].travel_time       = h_time[i];
        out[i].path_length       = h_path[i];
        out[i].transmission_loss = h_tl[i];
        out[i].surface_bounces   = h_surf[i];
        out[i].bottom_bounces    = h_bot[i];
    }

    /* Cleanup */
    free(h_depths_flat); free(h_speeds_flat);
    free(h_time); free(h_path); free(h_tl); free(h_surf); free(h_bot);
    cudaFree(d_layer_depths); cudaFree(d_layer_speeds);
    cudaFree(d_src_depths); cudaFree(d_angles);
    cudaFree(d_out_time); cudaFree(d_out_path); cudaFree(d_out_tl);
    cudaFree(d_out_surf); cudaFree(d_out_bot);

    cudaError_t cerr = cudaGetLastError();
    if (cerr != cudaSuccess) return SV_ERR_CUDA;

    return SV_OK;
}
