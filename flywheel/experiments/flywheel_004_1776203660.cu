#include <stdio.h>
#include <math.h>

#define N 1000
#define BATCH_SIZE 32

__global__ void ct_snap_kernel(float *x) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        x[idx] = tanh(x[idx]);
    }
}

__global__ void norm_layer_kernel(float *x, float *mean, float *var) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        x[idx] = (x[idx] - mean[0]) / sqrt(var[0] + 0.001f);
    }
}

__global__ void compare_kernels(float *x, float *ct_snap_out, float *norm_out) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        ct_snap_out[idx] = tanh(x[idx]);
        norm_out[idx] = (x[idx] - 0.5f) / sqrt(0.25f + 0.001f);
    }
}

int main() {
    float *x, *ct_snap_out, *norm_out;
    cudaMallocManaged(&x, N * sizeof(float));
    cudaMallocManaged(&ct_snap_out, N * sizeof(float));
    cudaMallocManaged(&norm_out, N * sizeof(float));

    for (int i = 0; i < N; i++) {
        x[i] = (float)rand() / RAND_MAX;
    }

    int blocks = (N + 255) / 256;
    int threads = 256;

    ct_snap_kernel<<<blocks, threads>>>(x);
    cudaDeviceSynchronize();

    float mse_ct_snap = 0.0f;
    for (int i = 0; i < N; i++) {
        mse_ct_snap += pow((x[i] - tanh(x[i])), 2);
    }
    mse_ct_snap /= N;

    norm_layer_kernel<<<blocks, threads>>>(x, x, x);
    cudaDeviceSynchronize();

    float mse_norm = 0.0f;
    for (int i = 0; i < N; i++) {
        mse_norm += pow((x[i] - (x[i] - 0.5f) / sqrt(0.25f + 0.001f)), 2);
    }
    mse_norm /= N;

    compare_kernels<<<blocks, threads>>>(x, ct_snap_out, norm_out);
    cudaDeviceSynchronize();

    float mse_compare = 0.0f;
    for (int i = 0; i < N; i++) {
        mse_compare += pow((ct_snap_out[i] - norm_out[i]), 2);
    }
    mse_compare /= N;

    printf("MSE of CT snap: %f\n", mse_ct_snap);
    printf("MSE of norm layer: %f\n", mse_norm);
    printf("MSE of comparison: %f\n", mse_compare);

    SUMMARY: printf("Can CT snap replace normalization layers? %s\n", (mse_compare < 0.01f)? "Yes" : "No");

    cudaFree(x);
    cudaFree(ct_snap_out);
    cudaFree(norm_out);

    return 0;
}