#include <cuda_runtime.h>
#include <cmath>
#include <cstdio> // Include this for printf function

#define NUM_ITERATIONS 100
#define LEARNING_RATE 0.01
#define WEIGHT_SNAP 0.5

__global__ void train(float *weights, float *gradient, bool snap) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < 1000) {
        float weight = weights[idx];
        float grad = gradient[idx];
        for (int i = 0; i < NUM_ITERATIONS; i++) {
            weight -= LEARNING_RATE * grad;
            if (snap && weight > WEIGHT_SNAP) weight = WEIGHT_SNAP;
            weights[idx] = weight;
        }
    }
}

int main() {
    float *weights, *gradient;
    cudaMalloc((void **)&weights, 1000 * sizeof(float));
    cudaMalloc((void **)&gradient, 1000 * sizeof(float));

    float h_weights[1000], h_gradient[1000];
    for (int i = 0; i < 1000; i++) {
        h_weights[i] = 1.0f;
        h_gradient[i] = -0.1f;
    }
    cudaMemcpy(weights, h_weights, 1000 * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(gradient, h_gradient, 1000 * sizeof(float), cudaMemcpyHostToDevice);

    train<<<1, 1000>>>(weights, gradient, true);

    float result[1000];
    cudaMemcpy(result, weights, 1000 * sizeof(float), cudaMemcpyDeviceToHost);

    // Print the results
    for (int i = 0; i < 1000; i++) {
        printf("%f ", result[i]);
    }
    printf("\n");

    cudaFree(weights);
    cudaFree(gradient);

    return 0;
}