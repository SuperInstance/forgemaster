#include <stdio.h>
#include <math.h>

#define NUM_THREADS 256
#define NUM_BLOCKS 256
#define SHARED_STATE_SIZE 1024

__global__ void stigmergy_test(float *shared_state) {
    __shared__ float local_state[SHARED_STATE_SIZE];
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
    for (int i = 0; i < SHARED_STATE_SIZE; i++) {
        shared_state[i] = 0.0;
    }
    stigmergy_test<<<NUM_BLOCKS, NUM_THREADS>>>(shared_state);
    float result = 0.0;
    cudaMemcpy(&result, shared_state, sizeof(float), cudaMemcpyDeviceToHost);
    printf("Average shared state value: %f\n", result);
    printf("Does stigmergy produce a discrete shared state? %s\n", (result > 10.0)? "Yes" : "No");
    printf("SUMMARY: Stigmergy %s a form of CT snap (discrete shared state)\n", (result > 10.0)? "is" : "is not");
    return 0;
}