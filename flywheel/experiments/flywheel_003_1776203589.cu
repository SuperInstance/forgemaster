#include <stdio.h>
#include <math.h>

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

__global__ void compute_loss(float *weights, float *loss) {
    __shared__ float sum;
    if (threadIdx.x == 0) {
        sum = 0.0f;
    }
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < 100) {
        float weight = weights[idx];
        sum += weight * weight;
    }
    __syncthreads();

    if (threadIdx.x == 0) {
        *loss = sum;
    }
}

int main() {
    const int num_weights = 100;
    const int num_iterations = 100;
    const float learning_rate = 0.01f;

    float *weights;
    float *gradients;
    float *loss;

    cudaMalloc((void **)&weights, num_weights * sizeof(float));
    cudaMalloc((void **)&gradients, num_weights * sizeof(float));
    cudaMalloc((void **)&loss, sizeof(float));

    for (int i = 0; i < num_weights; i++) {
        weights[i] = 1.0f;
        gradients[i] = 2.0f;
    }

    float *weights_snap;
    cudaMalloc((void **)&weights_snap, num_weights * sizeof(float));
    cudaMemcpy(weights_snap, weights, num_weights * sizeof(float), cudaMemcpyDeviceToDevice);

    train<<<(num_weights + 255) / 256, 256>>>(weights, gradients, learning_rate, num_weights, num_iterations, 0);
    train<<<(num_weights + 255) / 256, 256>>>(weights_snap, gradients, learning_rate, num_weights, num_iterations, 1);

    float loss_no_snap;
    compute_loss<<<(num_weights + 255) / 256, 256>>>(weights, &loss_no_snap);
    float loss_snap;
    compute_loss<<<(num_weights + 255) / 256, 256>>>(weights_snap, &loss_snap);

    printf("Loss without snapping: %f\n", loss_no_snap);
    printf("Loss with snapping: %f\n", loss_snap);

    SUMMARY: printf("Snapping weights %s training\n", loss_no_snap < loss_snap? "hurts" : "helps");

    cudaFree(weights);
    cudaFree(gradients);
    cudaFree(loss);
    cudaFree(weights_snap);

    return 0;
}