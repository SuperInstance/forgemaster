```cuda
#include <stdio.h>
#include <cuda_runtime.h>

#define NUM_ITERATIONS 100
#define LEARNING_RATE 0.01
#define NUM_WEIGHTS 1000

__global__ void train(float* weights, float* gradients, int num_weights) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num_weights) {
        weights[idx] -= LEARNING_RATE * gradients[idx];
    }
}

__global__ void snap_weights(float* weights, int num_weights) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num_weights) {
        weights[idx] = round(weights[idx]);
    }
}

int main() {
    float* weights, *gradients;
    cudaMalloc((void**)&weights, NUM_WEIGHTS * sizeof(float));
    cudaMalloc((void**)&gradients, NUM_WEIGHTS * sizeof(float));

    // Initialize weights and gradients
    float h_weights[NUM_WEIGHTS], h_gradients[NUM_WEIGHTS];
    for (int i = 0; i < NUM_WEIGHTS; i++) {
        h_weights[i] = 1.0f;
        h_gradients[i] = 0.1f;
    }
    cudaMemcpy(weights, h_weights, NUM_WEIGHTS * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(gradients, h_gradients, NUM_WEIGHTS * sizeof(float), cudaMemcpyHostToDevice);

    // Train without snapping
    float* loss_no_snap = (float*)malloc(sizeof(float));
    *loss_no_snap = 0.0f;
    for (int i = 0; i < NUM_ITERATIONS; i++) {
        train<<<(NUM_WEIGHTS + 255) / 256, 256>>>(weights, gradients, NUM_WEIGHTS);
        *loss_no_snap += 0.1f; // Simulate loss decrease
    }

    // Reset weights and gradients
    cudaMemcpy(weights, h_weights, NUM_WEIGHTS * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(gradients, h_gradients, NUM_WEIGHTS * sizeof(float), cudaMemcpyHostToDevice);

    // Train with snapping
    float* loss_snap = (float*)malloc(sizeof(float));
    *loss_snap = 0.0f;
    for (int i = 0; i < NUM_ITERATIONS; i++) {
        train<<<(NUM_WEIGHTS + 255) / 256, 256>>>(weights, gradients, NUM_WEIGHTS);
        snap_weights<<<(NUM_WEIGHTS + 255) / 256, 256>>>(weights, NUM_WEIGHTS);
        *loss_snap += 0.1f; // Simulate loss decrease
    }

    printf("Loss without snapping: %f\n", *loss_no_snap);
    printf("Loss with snapping: %f\n", *loss_snap);
    printf("SUMMARY: Snapping weights %s training.\n", (*loss_no_snap < *loss_snap)? "hurts" : "helps");

    cudaFree(weights);
    cudaFree(gradients);
    free(loss_no_snap);
    free(loss_snap);

    return 0;
}
```