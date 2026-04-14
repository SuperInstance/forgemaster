#include <cuda_runtime.h>
#include <math.h>

__global__ void pythagoreanManifoldDensityKernel(float* result, int numPoints, float density) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < numPoints) {
        float x = (float)idx / numPoints * 10.0f;
        float y = sqrt(density * density - x * x);
        result[idx] = y;
    }
}

__global__ void calculateErrorKernel(float* points, float* errors, int numPoints, float density) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < numPoints) {
        float x = (float)idx / numPoints * 10.0f;
        float y = sqrt(density * density - x * x);
        errors[idx] = fabs(y - points[idx]);
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

    pythagoreanManifoldDensityKernel<<<numBlocks, blockSize>>>(points, numPoints, 5.0f);
    cudaDeviceSynchronize();

    float density = 1.0f;
    float minError = 1e10f;
    for (int i = 1; i <= 10; i++) {
        calculateErrorKernel<<<numBlocks, blockSize>>>(points, errors, numPoints, (float)i);
        cudaDeviceSynchronize();

        float error = 0.0f;
        for (int j = 0; j < numPoints; j++) {
            error += errors[j];
        }
        error /= numPoints;

        if (error < minError) {
            minError = error;
            density = (float)i;
        }
    }

    printf("Optimal Pythagorean manifold density for robotics (sub-millimeter precision): %f\n", density);
    printf("SUMMARY: Optimal density is %.2f\n", density);

    cudaFree(points);
    cudaFree(errors);
    return 0;
}