#include <stdio.h>
#include <math.h>

#define NUM_ITERATIONS 1000
#define LEARNING_RATE 0.01
#define NUM_WEIGHTS 1000

__global__ void train(float *weights, float *gradients, float *snapped_weights) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_WEIGHTS) {
        float weight = weights[idx];
        float gradient = gradients[idx];
        float snapped_weight = roundf(weight * 10.0f) / 10.0f;
        snapped_weights[idx] = snapped_weight;
        weights[idx] -= LEARNING_RATE * gradient;
    }
}

int main() {
    float *weights, *gradients, *snapped_weights;
    cudaMalloc((void **)&weights, NUM_WEIGHTS * sizeof(float));
    cudaMalloc((void **)&gradients, NUM_WEIGHTS * sizeof(float));
    cudaMalloc((void **)&snapped_weights, NUM_WEIGHTS * sizeof(float));

    // Initialize weights and gradients
    float h_weights[NUM_WEIGHTS], h_gradients[NUM_WEIGHTS];
    for (int i = 0; i < NUM_WEIGHTS; i++) {
        h_weights[i] = 1.0f;
        h_gradients[i] = 0.1f;
    }
    cudaMemcpy(weights, h_weights, NUM_WEIGHTS * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(gradients, h_gradients, NUM_WEIGHTS * sizeof(float), cudaMemcpyHostToDevice);

    float loss_with_snapping = 0.0f, loss_without_snapping = 0.0f;
    for (int i = 0; i < NUM_ITERATIONS; i++) {
        train<<<(NUM_WEIGHTS + 255) / 256, 256>>>(weights, gradients, snapped_weights);
        cudaMemcpy(h_weights, weights, NUM_WEIGHTS * sizeof(float), cudaMemcpyDeviceToHost);
        for (int j = 0; j < NUM_WEIGHTS; j++) {
            loss_with_snapping += h_weights[j] * h_weights[j];
        }
        // Without snapping
        float h_weights_no_snap[NUM_WEIGHTS];
        cudaMemcpy(h_weights_no_snap, weights, NUM_WEIGHTS * sizeof(float), cudaMemcpyDeviceToHost);
        for (int j = 0; j < NUM_WEIGHTS; j++) {
            h_weights_no_snap[j] -= LEARNING_RATE * h_gradients[j];
        }
        for (int j = 0; j < NUM_WEIGHTS; j++) {
            loss_without_snapping += h_weights_no_snap[j] * h_weights_no_snap[j];
        }
    }

    printf("Loss with snapping: %f\n", loss_with_snapping);
    printf("Loss without snapping: %f\n", loss_without_snapping);
    SUMMARY: printf("Snapping %s training.\n", (loss_with_snapping < loss_without_snapping)? "helps" : "hurts");

    cudaFree(weights);
    cudaFree(gradients);
    cudaFree(snapped_weights);
    return 0;
}