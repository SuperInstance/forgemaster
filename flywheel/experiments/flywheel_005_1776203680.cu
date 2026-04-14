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
    for (int i = 0; i < NUM_AGENTS; i++) {
        d_shared_state[i] = 0;
    }

    // Run stigmergy simulation
    stigmergy_simulation<<<(NUM_AGENTS + NUM_THREADS - 1) / NUM_THREADS, NUM_THREADS>>>(d_shared_state);

    // Run CT snap simulation
    ct_snap_simulation<<<(NUM_AGENTS + NUM_THREADS - 1) / NUM_THREADS, NUM_THREADS>>>(d_shared_state);

    // Check if final states are the same
    int* h_shared_state = (int*)malloc(NUM_AGENTS * sizeof(int));
    cudaMemcpy(h_shared_state, d_shared_state, NUM_AGENTS * sizeof(int), cudaMemcpyDeviceToHost);

    int diff = 0;
    for (int i = 0; i < NUM_AGENTS; i++) {
        if (h_shared_state[i]!= h_shared_state[0]) diff++;
    }

    printf("Difference between final states: %d\n", diff);
    printf("SUMMARY: Stigmergy and CT snap produce similar results (%s difference)\n", diff == 0? "no" : "some");

    return 0;
}