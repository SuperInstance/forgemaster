#include <stdio.h>
#include <math.h>

#define BLOCK_SIZE 256
#define NUM_ITERATIONS 1000

__global__ void dcs_breakpoint(float noise, float* result) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    float sum = 0.0f;
    for (int i = 0; i < NUM_ITERATIONS; i++) {
        sum += noise * (float)rand() / RAND_MAX;
    }
    if (sum > 0.5f) {
        result[idx] = 1.0f;
    } else {
        result[idx] = 0.0f;
    }
}

int main() {
    float noise_threshold = 0.0f;
    float step_size = 0.0001f;
    float* d_result;
    cudaMalloc((void**)&d_result, BLOCK_SIZE * sizeof(float));
    float* h_result = (float*)malloc(BLOCK_SIZE * sizeof(float));

    for (int i = 0; i < 10000; i++) {
        dcs_breakpoint<<<1, BLOCK_SIZE>>>(noise_threshold, d_result);
        cudaDeviceSynchronize();
        cudaMemcpy(h_result, d_result, BLOCK_SIZE * sizeof(float), cudaMemcpyDeviceToHost);
        int count = 0;
        for (int j = 0; j < BLOCK_SIZE; j++) {
            count += (int)h_result[j];
        }
        if (count > BLOCK_SIZE / 2) {
            printf("Noise threshold: %f\n", noise_threshold);
            break;
        }
        noise_threshold += step_size;
    }

    cudaFree(d_result);
    free(h_result);

    SUMMARY: printf("SUMMARY: DCS breaks at noise threshold around %f\n", noise_threshold);

    return 0;
}