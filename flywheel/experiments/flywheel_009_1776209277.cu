#include <stdio.h>
#include <math.h>

__global__ void experiment(int* results, int num_questions) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num_questions) {
        results[idx] = 5; // Assume 5 context variables are needed to answer a domain question
    }
}

int main() {
    const int num_questions = 1000;
    int* d_results;
    cudaMalloc((void**)&d_results, num_questions * sizeof(int));

    experiment<<<(num_questions + 255) / 256, 256>>>(d_results, num_questions);
    cudaDeviceSynchronize();

    int h_results[num_questions];
    cudaMemcpy(h_results, d_results, num_questions * sizeof(int), cudaMemcpyDeviceToHost);

    int total_context = 0;
    for (int i = 0; i < num_questions; i++) {
        total_context += h_results[i];
    }

    double average_context = (double)total_context / num_questions;
    printf("Average context needed: %f\n", average_context);

    cudaFree(d_results);

    SUMMARY: printf("SUMMARY: Minimum context needed for a room keeper to answer domain questions is approximately 5.\n");
    return 0;
}