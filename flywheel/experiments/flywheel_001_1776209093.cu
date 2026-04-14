#include <stdio.h>
#include <math.h>

#define NUM_POINTS 1000
#define NUM_ITERATIONS 100

__global__ void snap(float *points, float *snapped_points, float threshold) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_POINTS) {
        float x = points[idx];
        float snapped_x = round(x / threshold) * threshold;
        snapped_points[idx] = snapped_x;
    }
}

__global__ void check_topology(float *points, float *snapped_points, int *connected_components) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < NUM_POINTS) {
        float x = points[idx];
        float snapped_x = snapped_points[idx];
        if (snapped_x!= round(x / 1.0) * 1.0) {
            connected_components[idx] = 1;
        } else {
            connected_components[idx] = 0;
        }
    }
}

int main() {
    float *points, *snapped_points;
    int *connected_components;
    cudaMallocManaged(&points, NUM_POINTS * sizeof(float));
    cudaMallocManaged(&snapped_points, NUM_POINTS * sizeof(float));
    cudaMallocManaged(&connected_components, NUM_POINTS * sizeof(int));

    for (int i = 0; i < NUM_POINTS; i++) {
        points[i] = (float)rand() / RAND_MAX * 10.0;
    }

    float threshold = 1.0;
    snap<<<(NUM_POINTS + 255) / 256, 256>>>(points, snapped_points, threshold);
    check_topology<<<(NUM_POINTS + 255) / 256, 256>>>(points, snapped_points, connected_components);

    cudaDeviceSynchronize();

    int split_components = 0;
    for (int i = 0; i < NUM_POINTS; i++) {
        if (connected_components[i] == 1) {
            split_components++;
        }
    }

    printf("Number of split components: %d\n", split_components);
    printf("SUMMARY: CT snap does %s preserve topology.\n", split_components > 0? "not" : " ");
    return 0;
}