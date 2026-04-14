#include <stdio.h>
#include <math.h>

#define NUM_THREADS 256
#define NUM_BLOCKS 4
#define SHARED_STATE_SIZE 1024

__global__ void stigmergy_test(float *shared_state) {
    __shared__ float local_state[256]; // Shared memory size should match block size
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < SHARED_STATE_SIZE) {
        local_state[threadIdx.x] = shared_state[idx];
    }
    __syncthreads();
    for (int i = 0; i < 100; i++) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < SHARED_STATE_SIZE) {
            local_state[threadIdx.x] += 0.1;
            shared_state[idx] = local_state[threadIdx.x];
        }
        __syncthreads();
    }
}

int main() {
    float *shared_state;
    cudaMalloc((void **)&shared_state, SHARED_STATE_SIZE * sizeof(float));
    float *host_state = (float *)malloc(SHARED_STATE_SIZE * sizeof(float));
    for (int i = 0; i < SHARED_STATE_SIZE; i++) {
        host_state[i] = 0.0;
    }
    cudaMemcpy(shared_state, host_state, SHARED_STATE_SIZE * sizeof(float), cudaMemcpyHostToDevice);
    stigmergy_test<<<NUM_BLOCKS, NUM_THREADS>>>(shared_state);
    cudaDeviceSynchronize();
    cudaMemcpy(host_state, shared_state, SHARED_STATE_SIZE * sizeof(float), cudaMemcpyDeviceToHost);
    float result = host_state[0]; // Access the first element of the array
    printf("Result: %f\n", result);
    free(host_state);
    cudaFree(shared_state);
    return 0;
}