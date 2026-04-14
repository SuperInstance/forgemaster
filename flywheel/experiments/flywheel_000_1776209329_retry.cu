#include <stdio.h>
#include <math.h>

#define NUM_ITERATIONS 100000
#define NUM_DENSITIES 10

// CUDA kernel function to generate random numbers
__global__ void generateRandom(float* randoms, unsigned int* seeds) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_ITERATIONS * NUM_DENSITIES) {
        unsigned int seed = seeds[idx];
        float random = (float)curand_uniform(&seed);
        randoms[idx] = random;
        seeds[idx] = seed;
    }
}

// CUDA kernel function to calculate the pythagorean manifold
__global__ void pythagoreanManifoldKernel(float* errors, float* densities, float* xRandoms, float* yRandoms, unsigned int* seeds) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_ITERATIONS * NUM_DENSITIES) {
        int densityIdx = idx / NUM_ITERATIONS;
        float density = densities[densityIdx];
        float error = 0.0f;
        for (int i = 0; i < NUM_ITERATIONS; i++) {
            float x = xRandoms[idx + i * NUM_DENSITIES];
            float y = yRandoms[idx + i * NUM_DENSITIES];
            float z = sqrt(x * x + y * y);
            float pythagoreanError = fabs(z - sqrt(x * x + y * y + density * density));
            error += pythagoreanError;
        }
        errors[idx] = error / NUM_ITERATIONS;
    }
}

int main() {
    // Initialize CUDA
    cudaDeviceReset();

    // Allocate memory
    float* densities;
    float* errors;
    float* xRandoms;
    float* yRandoms;
    unsigned int* seeds;
    cudaMallocManaged(&densities, NUM_DENSITIES * sizeof(float));
    cudaMallocManaged(&errors, NUM_ITERATIONS * NUM_DENSITIES * sizeof(float));
    cudaMallocManaged(&xRandoms, NUM_ITERATIONS * NUM_DENSITIES * sizeof(float));
    cudaMallocManaged(&yRandoms, NUM_ITERATIONS * NUM_DENSITIES * sizeof(float));
    cudaMallocManaged(&seeds, NUM_ITERATIONS * NUM_DENSITIES * sizeof(unsigned int));

    // Initialize densities
    for (int i = 0; i < NUM_DENSITIES; i++) {
        densities[i] = (float)i;
    }

    // Initialize seeds
    for (int i = 0; i < NUM_ITERATIONS * NUM_DENSITIES; i++) {
        seeds[i] = i;
    }

    // Launch kernel to generate random numbers
    int blockSize = 256;
    int numBlocks = (NUM_ITERATIONS * NUM_DENSITIES + blockSize - 1) / blockSize;
    generateRandom<<<numBlocks, blockSize>>>(xRandoms, seeds);
    cudaDeviceSynchronize();
    generateRandom<<<numBlocks, blockSize>>>(yRandoms, seeds);
    cudaDeviceSynchronize();

    // Launch kernel to calculate the pythagorean manifold
    pythagoreanManifoldKernel<<<numBlocks, blockSize>>>(errors, densities, xRandoms, yRandoms, seeds);
    cudaDeviceSynchronize();

    // Print results
    for (int i = 0; i < NUM_DENSITIES; i++) {
        printf("Density: %f, Error: %f\n", densities[i], errors[i * NUM_ITERATIONS]);
    }

    // Free memory
    cudaFree(densities);
    cudaFree(errors);
    cudaFree(xRandoms);
    cudaFree(yRandoms);
    cudaFree(seeds);

    return 0;
}