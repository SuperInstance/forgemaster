#include <stdio.h>
#include <math.h>

// Kernel function to train the model
__global__ void train(float *weights, float *gradients, float learning_rate, int num_weights, int num_iterations, int snap) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_weights) return;

    for (int i = 0; i < num_iterations; i++) {
        float gradient = gradients[idx];
        if (snap) {
            weights[idx] = roundf(weights[idx] * 10.0f) / 10.0f;
        }
        weights[idx] -= learning_rate * gradient;
    }
}

// Kernel function to compute the loss
__global__ void compute_loss(float *weights, float *loss) {
    __shared__ float sum;
    if (threadIdx.x == 0) {
        sum = 0.0f;
    }
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < 100) {
        float weight = weights[idx];
        atomicAdd(&sum, weight * weight);
    }
    __syncthreads();

    if (threadIdx.x == 0) {
        atomicAdd(loss, sum);
    }
}

int main() {
    const int num_weights = 100;
    const int num_iterations = 100;
    const float learning_rate = 0.01f;

    // Allocate host memory
    float *h_weights, *h_gradients, *h_loss;
    h_weights = (float *)malloc(num_weights * sizeof(float));
    h_gradients = (float *)malloc(num_weights * sizeof(float));
    h_loss = (float *)malloc(sizeof(float));

    // Initialize weights and gradients
    for (int i = 0; i < num_weights; i++) {
        h_weights[i] = 1.0f;
        h_gradients[i] = 2.0f;
    }
    *h_loss = 0.0f;

    // Allocate device memory
    float *d_weights, *d_gradients, *d_loss;
    cudaMalloc((void **)&d_weights, num_weights * sizeof(float));
    cudaMalloc((void **)&d_gradients, num_weights * sizeof(float));
    cudaMalloc((void **)&d_loss, sizeof(float));

    // Copy data from host to device
    cudaMemcpy(d_weights, h_weights, num_weights * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_gradients, h_gradients, num_weights * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_loss, h_loss, sizeof(float), cudaMemcpyHostToDevice);

    // Launch kernel
    int blockSize = 256;
    int numBlocks = (num_weights + blockSize - 1) / blockSize;
    train<<<numBlocks, blockSize>>>(d_weights, d_gradients, learning_rate, num_weights, num_iterations, 1);
    cudaDeviceSynchronize();

    // Compute loss
    blockSize = 256;
    numBlocks = (100 + blockSize - 1) / blockSize;
    compute_loss<<<numBlocks, blockSize>>>(d_weights, d_loss);
    cudaDeviceSynchronize();

    // Copy result from device to host
    cudaMemcpy(h_loss, d_loss, sizeof(float), cudaMemcpyDeviceToHost);

    // Print result
    printf("Loss: %f\n", *h_loss);

    // Free memory
    free(h_weights);
    free(h_gradients);
    free(h_loss);
    cudaFree(d_weights);
    cudaFree(d_gradients);
    cudaFree(d_loss);

    return 0;
}