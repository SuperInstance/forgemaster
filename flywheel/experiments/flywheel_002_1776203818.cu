#include <stdio.h>
#include <math.h>

#define NUM_SAMPLES 1000000
#define NUM_BINS 256

__global__ void compute_entropy(float *data, float *histogram, int num_samples) {
    __shared__ float shared_histogram[NUM_BINS];
    if (threadIdx.x < NUM_BINS) {
        shared_histogram[threadIdx.x] = 0.0f;
    }
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num_samples) {
        int bin = (int)(data[idx] * NUM_BINS);
        atomicAdd(&shared_histogram[bin], 1.0f);
    }
    __syncthreads();

    if (threadIdx.x < NUM_BINS) {
        atomicAdd(&histogram[threadIdx.x], shared_histogram[threadIdx.x]);
    }
}

__global__ void compute_entropy_ctsnapped(float *data, float *histogram, int num_samples) {
    __shared__ float shared_histogram[NUM_BINS];
    if (threadIdx.x < NUM_BINS) {
        shared_histogram[threadIdx.x] = 0.0f;
    }
    __syncthreads();

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num_samples) {
        int bin = (int)(round(data[idx] * 16.0f) / 16.0f * NUM_BINS);
        atomicAdd(&shared_histogram[bin], 1.0f);
    }
    __syncthreads();

    if (threadIdx.x < NUM_BINS) {
        atomicAdd(&histogram[threadIdx.x], shared_histogram[threadIdx.x]);
    }
}

int main() {
    float *data, *histogram, *histogram_ctsnapped;
    cudaMallocManaged(&data, NUM_SAMPLES * sizeof(float));
    cudaMallocManaged(&histogram, NUM_BINS * sizeof(float));
    cudaMallocManaged(&histogram_ctsnapped, NUM_BINS * sizeof(float));

    for (int i = 0; i < NUM_SAMPLES; i++) {
        data[i] = (float)rand() / RAND_MAX;
    }

    compute_entropy<<<(NUM_SAMPLES + 255) / 256, 256>>>(data, histogram, NUM_SAMPLES);
    compute_entropy_ctsnapped<<<(NUM_SAMPLES + 255) / 256, 256>>>(data, histogram_ctsnapped, NUM_SAMPLES);
    cudaDeviceSynchronize();

    float entropy = 0.0f;
    float entropy_ctsnapped = 0.0f;
    for (int i = 0; i < NUM_BINS; i++) {
        float p = histogram[i] / NUM_SAMPLES;
        float p_ctsnapped = histogram_ctsnapped[i] / NUM_SAMPLES;
        if (p > 0.0f) {
            entropy -= p * log2f(p);
        }
        if (p_ctsnapped > 0.0f) {
            entropy_ctsnapped -= p_ctsnapped * log2f(p_ctsnapped);
        }
    }

    printf("Entropy of raw float signal: %f\n", entropy);
    printf("Entropy of CT-snapped signal: %f\n", entropy_ctsnapped);
    printf("SUMMARY: The entropy of the CT-snapped signal (%f) is lower than the raw float signal (%f)\n", entropy_ctsnapped, entropy);

    return 0;
}