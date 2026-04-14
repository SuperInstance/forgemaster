// optimal_density.cu
// Compile: nvcc -O3 -arch=sm_86 optimal_density.cu -o optimal_density
#include <cstdio>
#include <cmath>
#include <float.h>

#define N_DENSITY 1000   // number of density samples
#define BLOCK_SIZE 256

// Simulated "precision error" function for a given density.
// In a real scenario this would be derived from robotics kinematics.
__device__ float error_func(float density) {
    // Example: error = |sin(pi * density) - 0.5| + small noise
    float err = fabsf(sinf(3.14159265f * density) - 0.5f);
    // Add a tiny deterministic term to break ties
    err += 0.0001f * density;
    return err;
}

__global__ void evaluate_density(const float *densities, float *errors) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N_DENSITY) {
        errors[idx] = error_func(densities[idx]);
    }
}

int main() {
    // Allocate host arrays
    float *h_densities = new float[N_DENSITY];
    float *h_errors   = new float[N_DENSITY];

    // Fill densities from 0.01 to 1.00 (sub‑millimeter relevant range)
    for (int i = 0; i < N_DENSITY; ++i) {
        h_densities[i] = 0.01f + 0.99f * i / (N_DENSITY - 1);
    }

    // Allocate device memory
    float *d_densities, *d_errors;
    cudaMalloc(&d_densities, N_DENSITY * sizeof(float));
    cudaMalloc(&d_errors,   N_DENSITY * sizeof(float));

    // Copy densities to device
    cudaMemcpy(d_densities, h_densities, N_DENSITY * sizeof(float), cudaMemcpyHostToDevice);

    // Launch kernel
    int grid = (N_DENSITY + BLOCK_SIZE - 1) / BLOCK_SIZE;
    evaluate_density<<<grid, BLOCK_SIZE>>>(d_densities, d_errors);
    cudaDeviceSynchronize();

    // Retrieve errors
    cudaMemcpy(h_errors, d_errors, N_DENSITY * sizeof(float), cudaMemcpyDeviceToHost);

    // Find minimal error and corresponding density
    float best_error = FLT_MAX;
    float best_density = 0.0f;
    for (int i = 0; i < N_DENSITY; ++i) {
        if (h_errors[i] < best_error) {
            best_error = h_errors[i];
            best_density = h_densities[i];
        }
    }

    // Output result
    printf("Optimal Pythagorean manifold density (simulated) = %.6f\n", best_density);
    printf("Corresponding simulated error = %.6e\n", best_error);
    printf("SUMMARY: optimal Pythagorean manifold density = %.6f\n", best_density);

    // Clean up
    delete[] h_densities;
    delete[] h_errors;
    cudaFree(d_densities);
    cudaFree(d_errors);
    return 0;
}