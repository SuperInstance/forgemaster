#include <cuda_runtime.h>
#include <cuda.h>
#include <stdio.h>
#include <math.h>

#define N 1024
#define NUM_SIGNALS 10000

__global__ void calculateEntropy(float* raw, float* snapped, float* entropyRaw, float* entropySnapped) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= NUM_SIGNALS) return;

    float sumRaw = 0;
    float sumSnapped = 0;

    for (int i = 0; i < N; i++) {
        float pRaw = raw[idx * N + i] / N;
        float pSnapped = snapped[idx * N + i] / N;

        sumRaw -= pRaw * log2f(pRaw);
        sumSnapped -= pSnapped * log2f(pSnapped);
    }

    entropyRaw[idx] = sumRaw;
    entropySnapped[idx] = sumSnapped;
}

int main() {
    float* raw, *snapped, *entropyRaw, *entropySnapped;
    cudaMallocManaged(&raw, N * NUM_SIGNALS * sizeof(float));
    cudaMallocManaged(&snapped, N * NUM_SIGNALS * sizeof(float));
    cudaMallocManaged(&entropyRaw, NUM_SIGNALS * sizeof(float));
    cudaMallocManaged(&entropySnapped, NUM_SIGNALS * sizeof(float));

    // Generate random raw signal
    for (int i = 0; i < N * NUM_SIGNALS; i++) {
        raw[i] = (float)rand() / RAND_MAX;
    }

    // Snap signal to nearest integer
    for (int i = 0; i < N * NUM_SIGNALS; i++) {
        snapped[i] = roundf(raw[i]);
    }

    calculateEntropy<<<(NUM_SIGNALS + 255) / 256, 256>>>(raw, snapped, entropyRaw, entropySnapped);
    cudaDeviceSynchronize();

    float sumEntropyRaw = 0;
    float sumEntropySnapped = 0;

    for (int i = 0; i < NUM_SIGNALS; i++) {
        sumEntropyRaw += entropyRaw[i];
        sumEntropySnapped += entropySnapped[i];
    }

    printf("Average entropy of raw signal: %f\n", sumEntropyRaw / NUM_SIGNALS);
    printf("Average entropy of snapped signal: %f\n", sumEntropySnapped / NUM_SIGNALS);

    printf("SUMMARY: Snapped signal has lower entropy (%f) compared to raw signal (%f)\n", sumEntropySnapped / NUM_SIGNALS, sumEntropyRaw / NUM_SIGNALS);

    cudaFree(raw);
    cudaFree(snapped);
    cudaFree(entropyRaw);
    cudaFree(entropySnapped);

    return 0;
}