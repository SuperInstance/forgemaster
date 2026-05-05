// CUDA snap kernel for the Pythagorean manifold
// Compile: nvcc -O3 -arch=sm_89 -ptx snap.cu -o snap.ptx
//         nvcc -O3 -arch=sm_89 -cubin snap.cu -o snap.cubin

#include <math.h>
#include <stdint.h>

#define TAU 6.283185307179586

// Device-side triple lookup (loaded into constant memory)
// Max 50K triples = 200KB — fits in constant memory (64KB) or shared memory
__constant__ double d_angles[50000];
__constant__ int d_indices[50000];
__constant__ int d_num_triples;

__device__ __forceinline__ double angular_dist(double a, double b) {
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

__device__ int snap_binary(double theta) {
    if (d_num_triples == 0) return 0;
    double a = fmod(theta, TAU);
    if (a < 0) a += TAU;

    // Binary search
    int lo = 0, hi = d_num_triples - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (d_angles[mid] < a) lo = mid + 1;
        else hi = mid;
    }

    // Handle wraparound at boundaries
    if (lo == 0 && hi == 0) {
        double d_last = angular_dist(a, d_angles[d_num_triples - 1]);
        double d_first = angular_dist(a, d_angles[0]);
        return d_last <= d_first ? d_indices[d_num_triples - 1] : d_indices[0];
    }
    if (lo >= d_num_triples) {
        double d_last = angular_dist(a, d_angles[d_num_triples - 1]);
        double d_first = angular_dist(a, d_angles[0]);
        return d_last <= d_first ? d_indices[d_num_triples - 1] : d_indices[0];
    }

    double d_lo = angular_dist(a, d_angles[lo - 1]);
    double d_hi = angular_dist(a, d_angles[lo]);
    return d_lo <= d_hi ? d_indices[lo - 1] : d_indices[lo];
}

__global__ void snap_batch_kernel(const double* queries, int* results,
                                   double* distances, int n_queries) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n_queries) return;

    double theta = queries[tid];
    int idx = snap_binary(theta);
    results[tid] = idx;
    distances[tid] = angular_dist(
        fmod(theta, TAU) < 0 ? fmod(theta, TAU) + TAU : fmod(theta, TAU),
        d_angles[idx]
    );
}

// Holonomy random walk kernel
__global__ void holonomy_kernel(int n_steps, int max_step_size,
                                 double* max_displacement, int seed) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= 1) return; // Single walk for now

    int pos = 0;
    double max_disp = 0.0;
    unsigned long long state = (unsigned long long)seed + tid;

    for (int i = 0; i < n_steps; i++) {
        // xorshift64
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        int step = (int)(state % (unsigned int)(d_num_triples / 10));
        if (step < 1) step = 1;

        pos = (pos + step) % d_num_triples;
        double disp = angular_dist(d_angles[pos], d_angles[0]);
        if (disp > max_disp) max_disp = disp;
    }

    *max_displacement = max_disp;
}
