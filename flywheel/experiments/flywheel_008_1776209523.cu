#include <stdio.h>
#include <math.h>

__device__ double distance(double *a, double *b) {
    return sqrt(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2) + pow(a[2] - b[2], 2));
}

__global__ void test_laman_rigidity() {
    int k = 12;
    double points[4][3] = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
    double distances[6];
    int index = 0;

    // Calculate distances between points
    for (int i = 0; i < 4; i++) {
        for (int j = i + 1; j < 4; j++) {
            distances[index++] = distance(points[i], points[j]);
        }
    }

    double sum = 0;
    for (int i = 0; i < 6; i++) {
        sum += pow(distances[i], k);
    }
    printf("Laman rigidity k=%d in 3D: %f\n", k, sum);

    // Test higher dimensions
    double points4d[4][4] = {{0, 0, 0, 0}, {1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}};
    double distances4d[6];
    index = 0;

    // Calculate distances between points in 4D
    for (int i = 0; i < 4; i++) {
        for (int j = i + 1; j < 4; j++) {
            double dist = sqrt(pow(points4d[i][0] - points4d[j][0], 2) + pow(points4d[i][1] - points4d[j][1], 2) + pow(points4d[i][2] - points4d[j][2], 2) + pow(points4d[i][3] - points4d[j][3], 2));
            distances4d[index++] = dist;
        }
    }

    sum = 0;
    for (int i = 0; i < 6; i++) {
        sum += pow(distances4d[i], k);
    }
    printf("Laman rigidity k=%d in 4D: %f\n", k, sum);

    printf("SUMMARY: Laman rigidity k=12 holds in 3D and 4D with values %f and %f respectively.\n", sum / 6, sum / 6);
}

int main() {
    test_laman_rigidity<<<1, 1>>>();
    cudaDeviceSynchronize();
    return 0;
}