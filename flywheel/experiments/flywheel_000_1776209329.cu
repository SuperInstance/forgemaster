#include <stdio.h>
#include <math.h>

#define NUM_ITERATIONS 100000
#define NUM_DENSITIES 10

__global__ void pythagoreanManifoldKernel(float* errors, float* densities) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_ITERATIONS * NUM_DENSITIES) {
        int densityIdx = idx / NUM_ITERATIONS;
        float density = densities[densityIdx];
        float error = 0.0f;
        for (int i = 0; i < NUM_ITERATIONS; i++) {
            float x = (float)rand() / RAND_MAX;
            float y = (float)rand() / RAND_MAX;
            float z = sqrt(x * x + y * y);
            float pythagoreanError = fabs(z - sqrt(x * x + y * y + density * density));
            error += pythagoreanError;
        }
        errors[idx] = error / NUM_ITERATIONS;
    }
}

int main() {
    float* densities;
    float* errors;
    cudaMallocManaged(&densities, NUM_DENSITIES * sizeof(float));
    cudaMallocManaged(&errors, NUM_ITERATIONS * NUM_DENSITIES * sizeof(float));

    for (int i = 0; i < NUM_DENSITIES; i++) {
        densities[i] = (float)i / 1000.0f;
    }

    pythagoreanManifoldKernel<<<(NUM_ITERATIONS * NUM_DENSITIES + 255) / 256, 256>>>(errors, densities);

    cudaDeviceSynchronize();

    float minError = 1e10f;
    int optimalDensityIdx = -1;
    for (int i = 0; i < NUM_DENSITIES; i++) {
        float error = 0.0f;
        for (int j = 0; j < NUM_ITERATIONS; j++) {
            error += errors[i * NUM_ITERATIONS + j];
        }
        error /= NUM_ITERATIONS;
        if (error < minError) {
            minError = error;
            optimalDensityIdx = i;
        }
    }

    printf("Optimal Pythagorean manifold density: %f\n", densities[optimalDensityIdx]);
    printf("SUMMARY: Optimal Pythagorean manifold density for robotics (sub-millimeter precision) is %f\n", densities[optimalDensityIdx]);

    cudaFree(densities);
    cudaFree(errors);

    return 0;
}