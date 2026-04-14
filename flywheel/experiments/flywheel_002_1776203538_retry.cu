#include <stdio.h>
#include <math.h>
#include <curand.h>
#include <curand_kernel.h>

#define NUM_SAMPLES 1000000

__global__ void calculateEntropy(float *data, float *snappedData, int numSamples, curandState *states) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= numSamples) return;

    curandState localState = states[idx];
    float randomFloat = curand_uniform(&localState);
    data[idx] = randomFloat; // generate random float
    snappedData[idx] = round(data[idx] * 1000) / 1000; // CT-snapped signal
    states[idx] = localState;
}

__global__ void calculateEntropyValues(float *data, float *snappedData, int numSamples, float *entropy, float *snappedEntropy) {
    __shared__ float hist[1024];
    __shared__ float snappedHist[1024];

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= numSamples) return;

    if (threadIdx.x < 1024) {
        hist[threadIdx.x] = 0;
        snappedHist[threadIdx.x] = 0;
    }
    __syncthreads();

    int bin = (int)(data[idx] * 1000);
    int snappedBin = (int)(snappedData[idx] * 1000);

    atomicAdd(&hist[bin], 1);
    atomicAdd(&snappedHist[snappedBin], 1);

    __syncthreads();

    if (threadIdx.x < 1024) {
        entropy[threadIdx.x] = hist[threadIdx.x];
        snappedEntropy[threadIdx.x] = snappedHist[threadIdx.x];
    }
}

__global__ void initializeCurandStates(curandState *states, int numSamples, unsigned long seed) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= numSamples) return;

    curand_init(seed, idx, 0, &states[idx]);
}

int main() {
    int numSamples = NUM_SAMPLES;
    int blockSize = 256;
    int numBlocks = (numSamples + blockSize - 1) / blockSize;

    float *data, *snappedData, *entropy, *snappedEntropy;
    curandState *states;

    cudaMalloc((void **)&data, numSamples * sizeof(float));
    cudaMalloc((void **)&snappedData, numSamples * sizeof(float));
    cudaMalloc((void **)&entropy, 1024 * sizeof(float));
    cudaMalloc((void **)&snappedEntropy, 1024 * sizeof(float));
    cudaMalloc((void **)&states, numSamples * sizeof(curandState));

    initializeCurandStates<<<numBlocks, blockSize>>>(states, numSamples, 1234);
    calculateEntropy<<<numBlocks, blockSize>>>(data, snappedData, numSamples, states);
    calculateEntropyValues<<<numBlocks, blockSize>>>(data, snappedData, numSamples, entropy, snappedEntropy);

    float *hostEntropy = (float *)malloc(1024 * sizeof(float));
    float *hostSnappedEntropy = (float *)malloc(1024 * sizeof(float));

    cudaMemcpy(hostEntropy, entropy, 1024 * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(hostSnappedEntropy, snappedEntropy, 1024 * sizeof(float), cudaMemcpyDeviceToHost);

    for (int i = 0; i < 1024; i++) {
        printf("Entropy: %f, Snapped Entropy: %f\n", hostEntropy[i], hostSnappedEntropy[i]);
    }

    free(hostEntropy);
    free(hostSnappedEntropy);

    cudaFree(data);
    cudaFree(snappedData);
    cudaFree(entropy);
    cudaFree(snappedEntropy);
    cudaFree(states);

    return 0;
}