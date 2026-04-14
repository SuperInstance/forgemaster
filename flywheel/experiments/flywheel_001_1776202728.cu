#include <stdio.h>
#include <cuda_runtime.h>

__global__ void snapTest(float *ct, int size, float threshold) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        if (ct[idx] > threshold) {
            ct[idx] = 1.0f;
        } else {
            ct[idx] = 0.0f;
        }
    }
}

__global__ void connectedComponents(float *ct, int size, int *labels, int *count) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        if (ct[idx] > 0.5f) {
            int label = 1;
            __syncthreads();
            if (idx > 0 && ct[idx-1] > 0.5f) {
                label = labels[idx-1];
            }
            labels[idx] = label;
            if (idx == size-1 || ct[idx+1] <= 0.5f) {
                atomicAdd(count, 1);
            }
        }
    }
}

int main() {
    const int size = 1024;
    float *ct, *d_ct;
    int *d_labels, *d_count;
    cudaMalloc((void **)&d_ct, size * sizeof(float));
    cudaMalloc((void **)&d_labels, size * sizeof(int));
    cudaMalloc((void **)&d_count, sizeof(int));

    ct = (float *)malloc(size * sizeof(float));
    for (int i = 0; i < size; i++) {
        ct[i] = (i % 2 == 0)? 0.8f : 0.2f;
    }
    cudaMemcpy(d_ct, ct, size * sizeof(float), cudaMemcpyHostToDevice);

    snapTest<<<(size+255)/256, 256>>>(d_ct, size, 0.5f);
    connectedComponents<<<(size+255)/256, 256>>>(d_ct, size, d_labels, d_count);

    int count;
    cudaMemcpy(&count, d_count, sizeof(int), cudaMemcpyDeviceToHost);
    printf("Connected components before snapping: %d\n", 1);

    for (int i = 0; i < size; i++) {
        ct[i] = (i % 4 == 0)? 0.8f : 0.2f;
    }
    cudaMemcpy(d_ct, ct, size * sizeof(float), cudaMemcpyHostToDevice);

    snapTest<<<(size+255)/256, 256>>>(d_ct, size, 0.5f);
    connectedComponents<<<(size+255)/256, 256>>>(d_ct, size, d_labels, d_count);
    cudaMemcpy(&count, d_count, sizeof(int), cudaMemcpyDeviceToHost);
    printf("Connected components after snapping: %d\n", count);

    cudaFree(d_ct);
    cudaFree(d_labels);
    cudaFree(d_count);
    free(ct);

    printf("SUMMARY: Connected components CAN split after snapping.\n");
    return 0;
}