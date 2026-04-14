#include <stdio.h>
#include <math.h>
#include <curand.h>
#include <curand_kernel.h>

#define NUM_ITERATIONS 1000000
#define NUM_STEPS 100

__device__ double dcs(double x, double noise, curandState *state) {
    double random = curand_uniform(state) * 2.0 - 1.0;
    return x * x + noise * random;
}

__global__ void experiment(double *result) {
    double x = 1.0;
    double noise = 0.0;
    int step = blockIdx.x;

    noise = (double)step / NUM_STEPS;

    curandState state;
    curand_init(1234, step, 0, &state);

    for (int i = 0; i < NUM_ITERATIONS; i++) {
        x = dcs(x, noise, &state);
        if (x > 1000.0) {
            result[step] = noise;
            return;
        }
    }
    result[step] = -1.0; // indicate that x never exceeded 1000.0
}

int main() {
    double *result;
    cudaMallocManaged(&result, NUM_STEPS * sizeof(double));

    experiment<<<NUM_STEPS, 1>>>(result);
    cudaDeviceSynchronize();

    double noise_threshold = 1.0;
    for (int i = 0; i < NUM_STEPS; i++) {
        if (result[i]!= -1.0) {
            noise_threshold = (double)i / NUM_STEPS;
            break;
        }
    }

    printf("Noise threshold where DCS breaks: %f\n", noise_threshold);
    printf("SUMMARY: The noise threshold where DCS breaks is %f\n", noise_threshold);

    cudaFree(result);
    return 0;
}