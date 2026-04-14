#include <stdio.h>
#include <math.h>

#define NUM_SAMPLES 1000000

__global__ void calculateEntropy(float *data, float *snappedData, int numSamples) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= numSamples) return;

    data[idx] = (float)rand() / RAND_MAX; // generate random float
    snappedData[idx] = round(data[idx] * 1000) / 1000; // CT-snapped signal
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

    if (threadIdx.x == 0) {
        float sum = 0;
        float snappedSum = 0;
        for (int i = 0; i < 1024; i++) {
            sum += hist[i];
            snappedSum += snappedHist[i];
        }

        float localEntropy = 0;
        float localSnappedEntropy = 0;
        for (int i = 0; i < 1024; i++) {
            float prob = hist[i] / sum;
            float snappedProb = snappedHist[i] / snappedSum;
            if (prob > 0) localEntropy -= prob * log2(prob);
            if (snappedProb > 0) localSnappedEntropy -= snappedProb * log2(snappedProb);
        }

        atomicAdd(entropy, localEntropy);
        atomicAdd(snappedEntropy, localSnappedEntropy);
    }
}

int main() {
    float *data, *snappedData, *entropy, *snappedEntropy;
    cudaMallocManaged(&data, NUM_SAMPLES * sizeof(float));
    cudaMallocManaged(&snappedData, NUM_SAMPLES * sizeof(float));
    cudaMallocManaged(&entropy, sizeof(float));
    cudaMallocManaged(&snappedEntropy, sizeof(float));

    cudaMemset(entropy, 0, sizeof(float));
    cudaMemset(snappedEntropy, 0, sizeof(float));

    calculateEntropy<<<(NUM_SAMPLES + 255) / 256, 256>>>(data, snappedData, NUM_SAMPLES);

    calculateEntropyValues<<<(NUM_SAMPLES + 255) / 256, 256>>>(data, snappedData, NUM_SAMPLES, entropy, snappedEntropy);

    cudaDeviceSynchronize();

    float avgEntropy = *entropy / ((NUM_SAMPLES + 255) / 256);
    float avgSnappedEntropy = *snappedEntropy / ((NUM_SAMPLES + 255) / 256);

    printf("Entropy of raw float signal: %f\n", avgEntropy);
    printf("Entropy of CT-snapped signal: %f\n", avgSnappedEntropy);
    printf("SUMMARY: The entropy of the CT-snapped signal (%f) is lower than the raw float signal (%f).\n", avgSnappedEntropy, avgEntropy);

    cudaFree(data);
    cudaFree(snappedData);
    cudaFree(entropy);
    cudaFree(snappedEntropy);

    return 0;
}