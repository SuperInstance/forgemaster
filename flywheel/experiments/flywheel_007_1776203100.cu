// convergence_search.cu
// Compile: nvcc -O3 -arch=sm_86 convergence_search.cu -o convergence_search
#include <cstdio>
#include <cmath>

#define MAX_DEN 20000          // search denominator up to this
#define MAX_NUM MAX_DEN        // numerator up to this
#define EPS    1e-6f           // tolerance for a match
#define MAX_MATCHES 1000       // store up to this many matches per constant

// Five known convergence constants (example values)
__constant__ float d_consts[5] = {
    4.669201609102990f,   // Feigenbaum delta
    2.502907875095892f,   // Feigenbaum alpha (inverse)
    0.7390851332151607f,  // Dottie number
    1.618033988749895f,   // Golden ratio
    0.5671432904097838f   // Omega constant
};

struct Match {
    int num;
    int den;
    float value;
};

__global__ void search_kernel(Match *matches, unsigned int *counters) {
    // each thread handles a unique denominator
    int den = blockIdx.x * blockDim.x + threadIdx.x + 1; // den >=1
    if (den > MAX_DEN) return;

    for (int num = 1; num <= MAX_NUM; ++num) {
        float val = (float)num / (float)den;
        // compare against each constant
        #pragma unroll
        for (int c = 0; c < 5; ++c) {
            float diff = fabsf(val - d_consts[c]);
            if (diff < EPS) {
                // record match if we have space
                unsigned int idx = atomicAdd(&counters[c], 1);
                if (idx < MAX_MATCHES) {
                    Match *m = &matches[c * MAX_MATCHES + idx];
                    m->num = num;
                    m->den = den;
                    m->value = val;
                }
            }
        }
    }
}

int main() {
    // allocate storage for matches and counters
    Match *d_matches;
    unsigned int *d_counters;
    cudaMalloc(&d_matches, 5 * MAX_MATCHES * sizeof(Match));
    cudaMalloc(&d_counters, 5 * sizeof(unsigned int));
    cudaMemset(d_counters, 0, 5 * sizeof(unsigned int));

    // launch kernel
    int threads = 256;
    int blocks = (MAX_DEN + threads - 1) / threads;
    search_kernel<<<blocks, threads>>>(d_matches, d_counters);
    cudaDeviceSynchronize();

    // copy results back
    unsigned int h_counters[5];
    Match h_matches[5 * MAX_MATCHES];
    cudaMemcpy(h_counters, d_counters, 5 * sizeof(unsigned int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_matches, d_matches, 5 * MAX_MATCHES * sizeof(Match), cudaMemcpyDeviceToHost);

    // print results
    int total_new = 0;
    for (int c = 0; c < 5; ++c) {
        printf("Constant %d (%.12f): %u matches found (showing up to 5):\n",
               c, d_consts[c], h_counters[c]);
        int limit = min((unsigned int)5, h_counters[c]);
        for (unsigned int i = 0; i < limit; ++i) {
            Match m = h_matches[c * MAX_MATCHES + i];
            printf("  %d/%d = %.12f (diff %.2e)\n",
                   m.num, m.den, m.value, fabsf(m.value - d_consts[c]));
        }
        total_new += h_counters[c];
    }

    printf("SUMMARY: Total new rational matches within %.0e tolerance = %d\n",
           (double)EPS, total_new);

    // cleanup
    cudaFree(d_matches);
    cudaFree(d_counters);
    return 0;
}