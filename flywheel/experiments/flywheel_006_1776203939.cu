#include <stdio.h>
#include <math.h>

#define NUM_ITERATIONS 1000000
#define NUM_STEPS 100

__device__ double dcs(double x, double noise) {
    return x * x + noise * (rand() % 1000 - 500) / 500.0;
}

__global__ void experiment(double *result) {
    double x = 1.0;
    double noise = 0.0;
    int step = blockIdx.x;

    noise = (double)step / NUM_STEPS;

    for (int i = 0; i < NUM_ITERATIONS; i++) {
        x = dcs(x, noise);
        if (x > 1000.0) {
            result[step] = noise;
            return;
        }
    }
}

int main() {
    double *result;
    cudaMallocManaged(&result, NUM_STEPS * sizeof(double));

    experiment<<<NUM_STEPS, 1>>>(result);
    cudaDeviceSynchronize();

    double noise_threshold = 1.0;
    for (int i = 0; i < NUM_STEPS; i++) {
        if (result[i]!= 0.0) {
            noise_threshold = (double)i / NUM_STEPS;
            break;
        }
    }

    printf("Noise threshold where DCS breaks: %f\n", noise_threshold);
    printf("SUMMARY: The noise threshold where DCS breaks is approximately %f\n", noise_threshold);

    cudaFree(result);
    return 0;
}