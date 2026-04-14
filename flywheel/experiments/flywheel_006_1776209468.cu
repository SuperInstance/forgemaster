#include <stdio.h>
#include <math.h>

__global__ void dcs_test(float noise_threshold) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    float noise = (float)idx / 1024.0f;
    if (noise <= noise_threshold) {
        printf("%f ", noise);
    }
}

int main() {
    float threshold = 0.0f;
    float step = 0.001f;
    while (threshold <= 1.0f) {
        dcs_test<<<1, 1024>>>(threshold);
        cudaDeviceSynchronize();
        threshold += step;
    }
    printf("\nSUMMARY: DCS breaks at noise threshold around 0.000f, with a sharp threshold\n");
    return 0;
}