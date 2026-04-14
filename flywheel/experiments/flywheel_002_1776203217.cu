#include <stdio.h>
#include <math.h>

#define NUM_SAMPLES 1000000

__device__ float entropy(float* data, int size) {
    float entropy = 0.0f;
    for (int i = 0; i < size; i++) {
        float p = data[i] / size;
        if (p > 0) {
            entropy -= p * log2(p);
        }
    }
    return entropy;
}

__global__ void compute_entropy(float* raw_data, float* snapped_data, float* raw_entropy, float* snapped_entropy) {
    __shared__ float raw_entropy_block[256];
    __shared__ float snapped_entropy_block[256];

    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= NUM_SAMPLES) return;

    float raw_value = raw_data[idx];
    float snapped_value = snapped_data[idx];

    raw_entropy_block[threadIdx.x] = raw_value;
    snapped_entropy_block[threadIdx.x] = snapped_value;

    __syncthreads();

    if (threadIdx.x == 0) {
        float raw_entropy_block_sum = 0.0f;
        float snapped_entropy_block_sum = 0.0f;
        for (int i = 0; i < blockDim.x; i++) {
            raw_entropy_block_sum += raw_entropy_block[i];
            snapped_entropy_block_sum += snapped_entropy_block[i];
        }

        raw_entropy[blockIdx.x] = raw_entropy_block_sum;
        snapped_entropy[blockIdx.x] = snapped_entropy_block_sum;
    }
}

int main() {
    float* raw_data;
    float* snapped_data;
    float* raw_entropy;
    float* snapped_entropy;

    cudaMallocManaged(&raw_data, NUM_SAMPLES * sizeof(float));
    cudaMallocManaged(&snapped_data, NUM_SAMPLES * sizeof(float));
    cudaMallocManaged(&raw_entropy, 256 * sizeof(float));
    cudaMallocManaged(&snapped_entropy, 256 * sizeof(float));

    for (int i = 0; i < NUM_SAMPLES; i++) {
        raw_data[i] = (float)rand() / RAND_MAX;
        snapped_data[i] = round(raw_data[i] * 100.0f) / 100.0f;
    }

    compute_entropy<<<256, 256>>>(raw_data, snapped_data, raw_entropy, snapped_entropy);
    cudaDeviceSynchronize();

    float raw_entropy_sum = 0.0f;
    float snapped_entropy_sum = 0.0f;
    for (int i = 0; i < 256; i++) {
        raw_entropy_sum += raw_entropy[i];
        snapped_entropy_sum += snapped_entropy[i];
    }

    float raw_entropy_value = entropy(raw_data, NUM_SAMPLES);
    float snapped_entropy_value = entropy(snapped_data, NUM_SAMPLES);

    printf("Entropy of raw signal: %f\n", raw_entropy_value);
    printf("Entropy of CT-snapped signal: %f\n", snapped_entropy_value);
    printf("SUMMARY: CT-snapped signal has %s entropy than raw signal\n", snapped_entropy_value < raw_entropy_value? "lower" : "higher");

    cudaFree(raw_data);
    cudaFree(snapped_data);
    cudaFree(raw_entropy);
    cudaFree(snapped_entropy);

    return 0;
}