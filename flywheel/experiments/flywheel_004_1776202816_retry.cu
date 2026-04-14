#include <cuda_runtime.h>
#include <cuda.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define NUM_SAMPLES 1024
#define NUM_LAYERS 5

__global__ void testCTSnap(float *inputs, float *outputs, float *ctSnapOutputs) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= NUM_SAMPLES) return;

    // Simulate neural network with normalization layers
    float normOutput = inputs[idx];
    for (int i = 0; i < NUM_LAYERS; i++) {
        normOutput = normOutput / (normOutput * normOutput + 1);
    }
    outputs[idx] = normOutput;

    // Simulate neural network with CT snap
    float ctSnapOutput = inputs[idx];
    for (int i = 0; i < NUM_LAYERS; i++) {
        ctSnapOutput = ctSnapOutput > 0? 1.0f : -1.0f;
    }
    ctSnapOutputs[idx] = ctSnapOutput;
}

int main() {
    float *d_inputs, *d_outputs, *d_ctSnapOutputs;
    float h_inputs[NUM_SAMPLES], h_outputs[NUM_SAMPLES], h_ctSnapOutputs[NUM_SAMPLES];

    // Initialize inputs
    srand(time(NULL));
    for (int i = 0; i < NUM_SAMPLES; i++) {
        h_inputs[i] = (float)rand() / RAND_MAX;
    }

    // Allocate device memory
    cudaMalloc((void **)&d_inputs, NUM_SAMPLES * sizeof(float));
    cudaMalloc((void **)&d_outputs, NUM_SAMPLES * sizeof(float));
    cudaMalloc((void **)&d_ctSnapOutputs, NUM_SAMPLES * sizeof(float));

    // Copy inputs to device
    cudaMemcpy(d_inputs, h_inputs, NUM_SAMPLES * sizeof(float), cudaMemcpyHostToDevice);

    // Launch kernel
    int blockSize = 256;
    int numBlocks = (NUM_SAMPLES + blockSize - 1) / blockSize;
    testCTSnap<<<numBlocks, blockSize>>>(d_inputs, d_outputs, d_ctSnapOutputs);

    // Copy outputs from device
    cudaMemcpy(h_outputs, d_outputs, NUM_SAMPLES * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_ctSnapOutputs, d_ctSnapOutputs, NUM_SAMPLES * sizeof(float), cudaMemcpyDeviceToHost);

    // Print outputs
    for (int i = 0; i < NUM_SAMPLES; i++) {
        printf("Input: %f, Output: %f, CT Snap Output: %f\n", h_inputs[i], h_outputs[i], h_ctSnapOutputs[i]);
    }

    // Free device memory
    cudaFree(d_inputs);
    cudaFree(d_outputs);
    cudaFree(d_ctSnapOutputs);

    return 0;
}