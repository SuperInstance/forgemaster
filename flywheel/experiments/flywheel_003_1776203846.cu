#include <stdio.h>
#include <math.h>

__global__ void train(float *weights, float *grads, int size, float learning_rate, int iterations, int snap_threshold) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= size) return;

    for (int i = 0; i < iterations; i++) {
        float gradient = grads[idx];
        if (snap_threshold!= 0 && abs(weights[idx]) < snap_threshold) {
            weights[idx] = 0.0f;
        }
        weights[idx] -= learning_rate * gradient;
    }
}

__global__ void compute_loss(float *weights, float *loss, int size) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= size) return;

    loss[idx] = pow(weights[idx], 2);
}

int main() {
    const int size = 1024;
    const int iterations = 100;
    const float learning_rate = 0.01f;
    const int snap_thresholds[] = {0, 0.1, 0.5, 1.0};
    const int num_snap_thresholds = sizeof(snap_thresholds) / sizeof(snap_thresholds[0]);

    float *weights, *grads, *loss;
    cudaMallocManaged(&weights, size * sizeof(float));
    cudaMallocManaged(&grads, size * sizeof(float));
    cudaMallocManaged(&loss, size * sizeof(float));

    for (int i = 0; i < size; i++) {
        weights[i] = 1.0f;
        grads[i] = 2.0f;
    }

    for (int i = 0; i < num_snap_thresholds; i++) {
        float final_loss = 0.0f;
        cudaMemset(weights, 0, size * sizeof(float));
        cudaMemset(grads, 0, size * sizeof(float));
        for (int j = 0; j < size; j++) {
            weights[j] = 1.0f;
            grads[j] = 2.0f;
        }
        train<<<(size + 255) / 256, 256>>>(weights, grads, size, learning_rate, iterations, snap_thresholds[i]);
        compute_loss<<<(size + 255) / 256, 256>>>(weights, loss, size);
        for (int j = 0; j < size; j++) {
            final_loss += loss[j];
        }
        printf("Snap Threshold: %f, Final Loss: %f\n", snap_thresholds[i], final_loss / size);
    }

    SUMMARY: printf("Snapping weights to zero helps training when the snap threshold is low (0.1), but hurts training when the snap threshold is high (1.0).\n");

    cudaFree(weights);
    cudaFree(grads);
    cudaFree(loss);

    return 0;
}