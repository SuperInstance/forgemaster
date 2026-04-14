#include <stdio.h>
#include <math.h>

#define NUM_AGENTS 1000
#define NUM_STEPS 100
#define NUM_THREADS 256

__global__ void stigmergy_simulation(int* shared_state) {
    int agent_id = blockIdx.x * blockDim.x + threadIdx.x;
    if (agent_id >= NUM_AGENTS) return;

    for (int step = 0; step < NUM_STEPS; step++) {
        int current_state = shared_state[agent_id];
        int next_state = (current_state + 1) % 2; // Simplest form of stigmergy
        shared_state[agent_id] = next_state;
    }
}

__global__ void ct_snap_simulation(int* shared_state) {
    int agent_id = blockIdx.x * blockDim.x + threadIdx.x;
    if (agent_id >= NUM_AGENTS) return;

    for (int step = 0; step < NUM_STEPS; step++) {
        int current_state = shared_state[agent_id];
        int next_state = (current_state + 1) % 2; // Simplest form of CT snap
        shared_state[agent_id] = next_state;
    }
}

int main() {
    int* d_shared_state;
    cudaMalloc((void**)&d_shared_state, NUM_AGENTS * sizeof(int));

    // Initialize shared state
    int* h_shared_state = (int*)malloc(NUM_AGENTS * sizeof(int));
    for (int i = 0; i < NUM_AGENTS; i++) {
        h_shared_state[i] = 0; // Initialize to 0
    }
    cudaMemcpy(d_shared_state, h_shared_state, NUM_AGENTS * sizeof(int), cudaMemcpyHostToDevice);
    free(h_shared_state);

    int num_blocks = (NUM_AGENTS + NUM_THREADS - 1) / NUM_THREADS;
    stigmergy_simulation<<<num_blocks, NUM_THREADS>>>(d_shared_state);
    cudaDeviceSynchronize();

    ct_snap_simulation<<<num_blocks, NUM_THREADS>>>(d_shared_state);
    cudaDeviceSynchronize();

    // Print the results
    h_shared_state = (int*)malloc(NUM_AGENTS * sizeof(int));
    cudaMemcpy(h_shared_state, d_shared_state, NUM_AGENTS * sizeof(int), cudaMemcpyDeviceToHost);
    for (int i = 0; i < NUM_AGENTS; i++) {
        printf("%d ", h_shared_state[i]);
    }
    printf("\n");
    free(h_shared_state);

    cudaFree(d_shared_state);

    return 0;
}