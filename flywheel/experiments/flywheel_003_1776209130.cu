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

    for (int i = 0; i < n; i++) {
        weights[i] = 2.0;
        gradients[i] = 1.0;
    }

    int blocks = (n + 255) / 256;
    for (int i = 0; i < 100; i++) {
        train<<<blocks, 256>>>(weights, gradients, snapped_weights, n);
        compute_loss<<<blocks, 256>>>(weights, snapped_weights, loss, snapped_loss, n);
    }

    float sum_loss = 0;
    float sum_snapped_loss = 0;
    for (int i = 0; i < n; i++) {
        sum_loss += loss[i];
        sum_snapped_loss += snapped_loss[i];
    }

    printf("Average loss without snapping: %f\n", sum_loss / n);
    printf("Average loss with snapping: %f\n", sum_snapped_loss / n);
    printf("SUMMARY: Snapping weights %s training.\n", sum_snapped_loss < sum_loss? "helps" : "hurts");

    cudaFree(weights);
    cudaFree(gradients);
    cudaFree(snapped_weights);
    cudaFree(loss);
    cudaFree(snapped_loss);

    return 0;
}