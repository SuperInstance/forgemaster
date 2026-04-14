#include <cuda_runtime.h>
#include <math.h>
#include <stdio.h> // Include the necessary header for printf

__global__ void pythagoreanManifoldDensityKernel(float* result, int numPoints, float density) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < numPoints) {
        float x = (float)idx / numPoints * 10.0f;
        float y = sqrtf(density * density - x * x); // Use sqrtf for float
        result[idx] = y;
    }
}

__global__ void calculateErrorKernel(float* points, float* errors, int numPoints, float density) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < numPoints) {
        float x = (float)idx / numPoints * 10.0f;
        float y = sqrtf(density * density - x * x); // Use sqrtf for float
        errors[idx] = fabsf(y - points[idx]); // Use fabsf for float
    }
}

int main() {
    const int numPoints = 1000000;
    const int blockSize = 256;
    const int numBlocks = (numPoints + blockSize - 1) / blockSize;

    float* points;
    cudaMallocManaged(&points, numPoints * sizeof(float));

    float* errors;
    cudaMallocManaged(&errors, numPoints * sizeof(float));

    float density = 5.0f;

    pythagoreanManifoldDensityKernel<<<numBlocks, blockSize>>>(points, numPoints, density);
    cudaDeviceSynchronize();

    calculateErrorKernel<<<numBlocks, blockSize>>>(points, errors, numPoints, density);
    cudaDeviceSynchronize();

    // Print the first 10 errors
    for (int i = 0; i < 10; i++) {
        printf("%f\n", errors[i]);
    }

    cudaFree(points);
    cudaFree(errors);

    return 0;
}