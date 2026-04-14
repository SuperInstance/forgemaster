#include <stdio.h>
#include <math.h>

__global__ void train(float* weights, float* gradients, float* snapped_weights, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        weights[idx] -= 0.01 * gradients[idx];
        snapped_weights[idx] = roundf(weights[idx] * 1000) / 1000;
    }
}

__global__ void compute_loss(float* weights, float* snapped_weights, float* loss, float* snapped_loss, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        loss[idx] = powf(weights[idx] - 1.0, 2);
        snapped_loss[idx] = powf(snapped_weights[idx] - 1.0, 2);
    }
}

int main() {
    int n = 1000;
    float* weights;
    float* gradients;
    float* snapped_weights;
    float* loss;
    float* snapped_loss;
    cudaMallocManaged(&weights, n * sizeof(float));
    cudaMallocManaged(&gradients, n * sizeof(float));
    cudaMallocManaged(&snapped_weights, n * sizeof(float));
    cudaMallocManaged(&loss, n * sizeof(float));
    cudaMallocManaged(&snapped_loss, n * sizeof(float));

    // Initialize weights and gradients
    for (int i = 0; i < n; i++) {
        weights[i] = 0.5;
        gradients[i] = 1.0;
    }

    // Launch kernels
    int blockSize = 256;
    int numBlocks = (n + blockSize - 1) / blockSize;
    train<<<numBlocks, blockSize>>>(weights, gradients, snapped_weights, n);
    cudaDeviceSynchronize();
    compute_loss<<<numBlocks, blockSize>>>(weights, snapped_weights, loss, snapped_loss, n);
    cudaDeviceSynchronize();

    // Print results
    for (int i = 0; i < 10; i++) {
        printf("Weight: %f, Snapped Weight: %f, Loss: %f, Snapped Loss: %f\n", weights[i], snapped_weights[i], loss[i], snapped_loss[i]);
    }

    // Free memory
    cudaFree(weights);
    cudaFree(gradients);
    cudaFree(snapped_weights);
    cudaFree(loss);
    cudaFree(snapped_loss);

    return 0;
}