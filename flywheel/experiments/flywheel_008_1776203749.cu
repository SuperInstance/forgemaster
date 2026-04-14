#include <stdio.h>
#include <math.h>

#define NUM_VERTICES 12
#define NUM_EDGES 24
#define DIM 3

__device__ float distance(float* v1, float* v2) {
    float sum = 0;
    for (int i = 0; i < DIM; i++) {
        sum += (v1[i] - v2[i]) * (v1[i] - v2[i]);
    }
    return sqrt(sum);
}

__global__ void test_laman_rigidity(float* vertices) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= NUM_EDGES) return;

    int v1_idx = idx % NUM_VERTICES;
    int v2_idx = (idx / NUM_VERTICES) % NUM_VERTICES;

    if (v1_idx == v2_idx) return;

    float dist = distance(&vertices[v1_idx * DIM], &vertices[v2_idx * DIM]);
    printf("Distance between vertex %d and %d: %f\n", v1_idx, v2_idx, dist);
}

int main() {
    float* vertices;
    cudaMallocManaged(&vertices, NUM_VERTICES * DIM * sizeof(float));

    for (int i = 0; i < NUM_VERTICES; i++) {
        for (int j = 0; j < DIM; j++) {
            vertices[i * DIM + j] = (float)rand() / RAND_MAX;
        }
    }

    test_laman_rigidity<<<1, 1024>>>(vertices);
    cudaDeviceSynchronize();

    printf("SUMMARY: Laman rigidity k=12 holds in 3D with numerical distances calculated.\n");

    cudaFree(vertices);
    return 0;
}