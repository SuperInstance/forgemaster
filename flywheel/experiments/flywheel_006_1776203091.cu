// dcs_noise_test.cu
// Compile: nvcc -O3 -arch=sm_86 dcs_noise_test.cu -o dcs_noise_test -lcurand
#include <cstdio>
#include <curand_kernel.h>
#include <cuda_runtime.h>

#define TOTAL_BITS (1<<24)          // ~16 million bits
#define THREADS_PER_BLOCK 256
#define BLOCKS ((TOTAL_BITS + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK)

__global__ void dcs_kernel(float sigma, unsigned int *d_err) {
    unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned int stride = gridDim.x * blockDim.x;
    curandStatePhilox4_32_10_t state;
    curand_init(1234ULL, idx, 0, &state);
    unsigned int local_err = 0;
    for (unsigned int i = idx; i < TOTAL_BITS; i += stride) {
        // original bit: +1 for 0, -1 for 1 (random)
        int bit = (curand(&state) & 1) ? -1 : 1;
        float noise = sigma * curand_normal(&state);
        float received = (float)bit + noise;
        int detected = (received >= 0.f) ? 1 : -1;
        if (detected != bit) local_err++;
    }
    atomicAdd(d_err, local_err);
}

int main() {
    unsigned int *d_err;
    cudaMalloc(&d_err, sizeof(unsigned int));
    const float sigma_start = 0.0f;
    const float sigma_end   = 1.0f;
    const float sigma_step  = 0.01f;
    float threshold_sigma = -1.0f;
    float prev_err_rate = 0.0f;
    bool sharp = true;

    for (float sigma = sigma_start; sigma <= sigma_end + 1e-6f; sigma += sigma_step) {
        cudaMemset(d_err, 0, sizeof(unsigned int));
        dcs_kernel<<<BLOCKS, THREADS_PER_BLOCK>>>(sigma, d_err);
        cudaDeviceSynchronize();
        unsigned int h_err;
        cudaMemcpy(&h_err, d_err, sizeof(unsigned int), cudaMemcpyDeviceToHost);
        float err_rate = (float)h_err / (float)TOTAL_BITS;
        printf("Sigma = %.4f, ErrorRate = %.8f\n", sigma, err_rate);
        if (threshold_sigma < 0.0f && h_err > 0) {
            threshold_sigma = sigma;
        }
        if (prev_err_rate == 0.0f && err_rate > 0.0f && sigma - sigma_step > 0.0f) {
            // transition from zero to non‑zero
            if (sigma - sigma_step > 0.0f) sharp = false;
        }
        prev_err_rate = err_rate;
    }

    if (threshold_sigma < 0.0f) threshold_sigma = 0.0f; // never broke
    printf("SUMMARY: ThresholdSigma = %.4f, TransitionIsSharp = %s\n",
           threshold_sigma, sharp ? "YES" : "NO");

    cudaFree(d_err);
    return 0;
}