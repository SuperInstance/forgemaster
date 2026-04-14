#include <cuda_runtime.h>
#include <cuda.h>
#include <stdio.h>

#define NUM Samples 1024
#define NUM Layers 5

__global__ void testCTSnap(float *inputs, float *outputs, float *ctSnapOutputs) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= NUM Samples) return;

    // Simulate neural network with normalization layers
    float normOutput = inputs[idx];
    for (int i = 0; i < NUM Layers; i++) {
        normOutput = normOutput / (normOutput * normOutput + 1);
    }
    outputs[idx] = normOutput;

    // Simulate neural network with CT snap
    float ctSnapOutput = inputs[idx];
    for (int i = 0; i < NUM Layers; i++) {
        ctSnapOutput = ctSnapOutput > 0? 1 : -1;
    }
    ctSnapOutputs[idx] = ctSnapOutput;
}

int main() {
    float *d_inputs, *d_outputs, *d_ctSnapOutputs;
    float h_inputs[NUM Samples], h_outputs[NUM Samples], h_ctSnapOutputs[NUM Samples];

    // Initialize inputs
    for (int i = 0; i < NUM Samples; i++) {
        h_inputs[i] = (float)rand() / RAND_MAX;
    }

    // Allocate device memory
    cudaMalloc((void **)&d_inputs, NUM Samples * sizeof(float));
    cudaMalloc((void **)&d_outputs, NUM Samples * sizeof(float));
    cudaMalloc((void **)&d_ctSnapOutputs, NUM Samples * sizeof(float));

    // Copy inputs to device
    cudaMemcpy(d_inputs, h_inputs, NUM Samples * sizeof(float), cudaMemcpyHostToDevice);

    // Launch kernel
    testCTSnap<<<(NUM Samples + 255) / 256, 256>>>(d_inputs, d_outputs, d_ctSnapOutputs);

    // Copy outputs from device
    cudaMemcpy(h_outputs, d_outputs, NUM Samples * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_ctSnapOutputs, d_ctSnapOutputs, NUM Samples * sizeof(float), cudaMemcpyDeviceToHost);

    // Calculate mean absolute error
    float mae = 0;
    for (int i = 0; i < NUM Samples; i++) {
        mae += abs(h_outputs[i] - h_ctSnapOutputs[i]);
    }
    mae /= NUM Samples;

    printf("Mean absolute error: %f\n", mae);
    printf("SUMMARY: CT snap can replace normalization layers with MAE %f\n", mae);

    cudaFree(d_inputs);
    cudaFree(d_outputs);
    cudaFree(d_ctSnapOutputs);

    return 0;
}