#include <stdio.h>
#include <math.h>
#include <cuda_runtime.h>
#include <device_launch_parameters.h>
#include <stdlib.h>
#include <time.h>

#define NUM_POINTS 1000
#define NUM_SNAP_ITER 10

__global__ void snapKernel(float *points, float *snappedPoints, int numPoints) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= numPoints) return;

    float x = points[idx * 2];
    float y = points[idx * 2 + 1];
    for (int i = 0; i < NUM_SNAP_ITER; i++) {
        float dist = sqrtf(x * x + y * y);
        if (dist > 0) {
            x = x / dist;
            y = y / dist;
        }
    }
    snappedPoints[idx * 2] = x;
    snappedPoints[idx * 2 + 1] = y;
}

int main() {
    // Initialize random number generator
    srand(time(NULL));

    float *points, *snappedPoints;
    cudaMallocManaged(&points, NUM_POINTS * 2 * sizeof(float));
    cudaMallocManaged(&snappedPoints, NUM_POINTS * 2 * sizeof(float));

    // Initialize points
    for (int i = 0; i < NUM_POINTS; i++) {
        points[i * 2] = (float)rand() / RAND_MAX;
        points[i * 2 + 1] = (float)rand() / RAND_MAX;
    }

    // Launch kernel
    snapKernel<<<(NUM_POINTS + 255) / 256, 256>>>(points, snappedPoints, NUM_POINTS);

    // Wait for kernel to finish
    cudaDeviceSynchronize();

    // Verify results
    for (int i = 0; i < NUM_POINTS; i++) {
        float x = snappedPoints[i * 2];
        float y = snappedPoints[i * 2 + 1];
        printf("Point %d: (%f, %f)\n", i, x, y);
    }

    // Free memory
    cudaFree(points);
    cudaFree(snappedPoints);

    return 0;
}