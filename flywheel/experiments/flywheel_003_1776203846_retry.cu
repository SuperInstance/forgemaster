#include <stdio.h>
#include <math.h>

__global__ void train(float *weights, float *grads, int size, float learning_rate, int iterations, float snap_threshold) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= size) return;

    for (int i = 0; i < iterations; i++) {
        float gradient = grads[idx];
        if (snap_threshold!= 0.0f && fabsf(weights[idx]) < snap_threshold) {
            weights[idx] = 0.0f;
        }
        weights[idx] -= learning_rate * gradient;
    }
}

__global__ void compute_loss(float *weights, float *loss, int size) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= size) return;

    loss[idx] = powf(weights[idx], 2);
}

int main() {
    const int size = 1024;
    const int iterations = 100;
    const float learning_rate = 0.01f;
    const float snap_thresholds[] = {0.0f, 0.1f, 0.5f, 1.0f};
    const int num_snap_thresholds = sizeof(snap_thresholds) / sizeof(snap_thresholds[0]);

    float *weights, *grads, *loss;
    cudaMallocManaged(&weights, size * sizeof(float));
    cudaMallocManaged(&grads, size * sizeof(float));
    cudaMallocManaged(&loss, size * sizeof(float));

    for (int i = 0; i < size; i++) {
        weights[i] = 1.0f;
        grads[i] = 1.0f;
    }

    for (int i = 0; i < num_snap_thresholds; i++) {
        train<<<(size + 255) / 256, 256>>>(weights, grads, size, learning_rate, iterations, snap_thresholds[i]);
        cudaDeviceSynchronize();
        compute_loss<<<(size + 255) / 256, 256>>>(weights, loss, size);
        cudaDeviceSynchronize();
    }

    for (int i = 0; i < size; i++) {
        printf("Weight: %f, Loss: %f\n", weights[i], loss[i]);
    }

    cudaFree(weights);
    cudaFree(grads);
    cudaFree(loss);

    return 0;
}