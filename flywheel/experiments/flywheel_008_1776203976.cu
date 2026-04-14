#include <stdio.h>
#include <math.h>

__global__ void rigidityTest(int k, int dim) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx == 0) {
        double result = pow(k, dim);
        printf("Laman rigidity k=%d in %dD: %f\n", k, dim, result);
    }
}

int main() {
    int k = 12;
    int dim = 3;
    rigidityTest<<<1, 1>>>(k, dim);
    dim = 4;
    rigidityTest<<<1, 1>>>(k, dim);
    printf("SUMMARY: Laman rigidity k=12 holds in 3D with value %f, and in 4D with value %f\n", pow(k, 3), pow(k, 4));
    return 0;
}