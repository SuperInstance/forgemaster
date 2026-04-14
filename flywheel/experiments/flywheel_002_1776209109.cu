#include <stdio.h>
#include <math.h>

#define NUM_VALUES 1000000

__device__ float ct_snapped(float value) {
    return round(value * 2048.0f) / 2048.0f;
}

__global__ void calculate_entropy(float *values, float *snapped_values, float *entropy_raw, float *entropy_snapped) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_VALUES) {
        snapped_values[idx] = ct_snapped(values[idx]);
    }
    __syncthreads();

    if (idx < NUM_VALUES) {
        float p = exp(-values[idx] * values[idx] / 2.0f) / sqrt(2.0f * M_PI);
        *entropy_raw += -p * log2(p);
        p = exp(-snapped_values[idx] * snapped_values[idx] / 2.0f) / sqrt(2.0f * M_PI);
        *entropy_snapped += -p * log2(p);
    }
}

int main() {
    float *values, *snapped_values;
    float entropy_raw = 0.0f, entropy_snapped = 0.0f;
    cudaMallocManaged(&values, NUM_VALUES * sizeof(float));
    cudaMallocManaged(&snapped_values, NUM_VALUES * sizeof(float));

    for (int i = 0; i < NUM_VALUES; i++) {
        values[i] = (float)rand() / RAND_MAX;
    }

    calculate_entropy<<<(NUM_VALUES + 255) / 256, 256>>>(values, snapped_values, &entropy_raw, &entropy_snapped);
    cudaDeviceSynchronize();

    printf("Entropy of raw float signal: %.6f\n", entropy_raw / NUM_VALUES);
    printf("Entropy of CT-snapped signal: %.6f\n");
    printf("SUMMARY: CT-snapped signal has %.2f%% lower entropy than raw float signal\n", (1.0f - (entropy_snapped / NUM_VALUES) / (entropy_raw / NUM_VALUES)) * 100.0f);

    cudaFree(values);
    cudaFree(snapped_values);
    return 0;
}