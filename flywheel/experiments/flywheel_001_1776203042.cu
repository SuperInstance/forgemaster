// ct_snap_topology_test.cu
// Compile: nvcc -O3 -arch=sm_86 ct_snap_topology_test.cu -o ct_snap_topology_test
// Run: ./ct_snap_topology_test
#include <cstdio>
#include <cmath>
#include <cuda_runtime.h>

#define N 200                // number of points
#define EPS 0.1f             // connectivity distance
#define GRID_SIZE 1.0f       // snap grid size (round to nearest integer)

// ---------- GPU kernels ----------
__global__ void init_points(float *x) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;
    // Create two clusters connected by a thin bridge
    // Cluster A: points around 0.0
    // Bridge point at 0.49 and 0.51 (within EPS)
    // Cluster B: points around 1.0
    if (i < 80) {
        x[i] = 0.0f + 0.02f * i;                 // spread within [0,1.58)
    } else if (i < 82) {
        x[i] = (i == 80) ? 0.49f : 0.51f;        // bridge points
    } else {
        x[i] = 1.0f + 0.02f * (i - 82);          // spread within [1,2.36)
    }
}

__global__ void snap_points(const float *in, float *out) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;
    out[i] = roundf(in[i] / GRID_SIZE) * GRID_SIZE;
}

// Compute adjacency matrix (upper triangular) as 1 if distance <= EPS
__global__ void compute_adj(const float *x, unsigned char *adj) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;
    if (i >= N || j >= N || i >= j) return;
    float d = fabsf(x[i] - x[j]);
    adj[i * N + j] = (d <= EPS) ? 1 : 0;
}

// Simple Union-Find (path compression) on GPU (one thread per element)
__global__ void uf_init(int *parent) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < N) parent[i] = i;
}

__global__ void uf_union(const unsigned char *adj, int *parent) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;
    for (int j = i + 1; j < N; ++j) {
        if (adj[i * N + j]) {
            // union i and j
            int a = i, b = j;
            // find roots
            while (parent[a] != a) a = parent[a];
            while (parent[b] != b) b = parent[b];
            if (a != b) {
                // attach smaller root to larger (arbitrary)
                if (a < b) parent[b] = a;
                else parent[a] = b;
            }
        }
    }
}

// Path compression pass
__global__ void uf_compress(int *parent) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;
    int p = parent[i];
    while (p != parent[p]) p = parent[p];
    parent[i] = p;
}

// Count components on host
int count_components(int *h_parent) {
    int comps = 0;
    for (int i = 0; i < N; ++i)
        if (h_parent[i] == i) ++comps;
    return comps;
}

// ---------- Main ----------
int main() {
    // Allocate
    float *d_x, *d_xsnap;
    unsigned char *d_adj;
    int *d_parent;
    cudaMalloc(&d_x, N * sizeof(float));
    cudaMalloc(&d_xsnap, N * sizeof(float));
    cudaMalloc(&d_adj, N * N * sizeof(unsigned char));
    cudaMalloc(&d_parent, N * sizeof(int));

    // Init points
    init_points<<<(N+31)/32, 32>>>(d_x);
    cudaDeviceSynchronize();

    // ---- Before snap ----
    compute_adj<<<dim3((N+15)/16, (N+15)/16), dim3(16,16)>>>(d_x, d_adj);
    uf_init<<<(N+31)/32, 32>>>(d_parent);
    uf_union<<<(N+31)/32, 32>>>(d_adj, d_parent);
    // compress a few times to ensure convergence
    for (int it = 0; it < 5; ++it)
        uf_compress<<<(N+31)/32, 32>>>(d_parent);
    cudaDeviceSynchronize();

    int h_parent_before[N];
    cudaMemcpy(h_parent_before, d_parent, N * sizeof(int), cudaMemcpyDeviceToHost);
    int comps_before = count_components(h_parent_before);

    // ---- Snap ----
    snap_points<<<(N+31)/32, 32>>>(d_x, d_xsnap);
    cudaDeviceSynchronize();

    // recompute adjacency on snapped points
    compute_adj<<<dim3((N+15)/16, (N+15)/16), dim3(16,16)>>>(d_xsnap, d_adj);
    uf_init<<<(N+31)/32, 32>>>(d_parent);
    uf_union<<<(N+31)/32, 32>>>(d_adj, d_parent);
    for (int it = 0; it < 5; ++it)
        uf_compress<<<(N+31)/32, 32>>>(d_parent);
    cudaDeviceSynchronize();

    int h_parent_after[N];
    cudaMemcpy(h_parent_after, d_parent, N * sizeof(int), cudaMemcpyDeviceToHost);
    int comps_after = count_components(h_parent_after);

    // Output
    printf("Components before snapping: %d\\n", comps_before);
    printf("Components after  snapping: %d\\n", comps_after);
    if (comps_after > comps_before)
        printf("SUMMARY: Connected components can split after CT snap.\\n");
    else if (comps_after == comps_before)
        printf("SUMMARY: CT snap preserved topology (no split).\\n");
    else
        printf("SUMMARY: CT snap merged components (topology not preserved).\\n");

    // Cleanup
    cudaFree(d_x);
    cudaFree(d_xsnap);
    cudaFree(d_adj);
    cudaFree(d_parent);
    return 0;
}