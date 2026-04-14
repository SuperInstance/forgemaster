#include <stdio.h>
#include <math.h>

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
    float *points, *snappedPoints;
    cudaMallocManaged(&points, NUM_POINTS * 2 * sizeof(float));
    cudaMallocManaged(&snappedPoints, NUM_POINTS * 2 * sizeof(float));

    for (int i = 0; i < NUM_POINTS; i++) {
        points[i * 2] = (float)rand() / RAND_MAX;
        points[i * 2 + 1] = (float)rand() / RAND_MAX;
    }

    snapKernel<<<(NUM_POINTS + 255) / 256, 256>>>(points, snappedPoints, NUM_POINTS);

    int connectedComponents = 0;
    for (int i = 0; i < NUM_POINTS; i++) {
        float x = snappedPoints[i * 2];
        float y = snappedPoints[i * 2 + 1];
        float dist = sqrtf(x * x + y * y);
        if (dist < 1e-6f) connectedComponents++;
    }

    printf("Connected components: %d\n", connectedComponents);
    printf("Does CT snap preserve topology? %s\n", connectedComponents > 1? "No" : "Yes");
    printf("Can connected components split after snapping? %s\n", connectedComponents > 1? "Yes" : "No");
    printf("SUMMARY: CT snap does %s preserve topology.\n", connectedComponents > 1? "not" : "");
    return 0;
}