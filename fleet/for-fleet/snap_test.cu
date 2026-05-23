#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <chrono>

#define TAU 6.283185307179586
#define MAX_TRIPLES 50000

// Host-side triple generation
typedef struct { double angle; int a, b; uint32_t c; } TripleHost;

int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }

int generate_triples(TripleHost* out, int max_c) {
    int n = 0;
    int max_m = (int)(sqrt((double)max_c) / 1.41421356) + 1;
    for (int m = 2; m <= max_m && n < MAX_TRIPLES; m++) {
        for (int nn = 1; nn < m && n < MAX_TRIPLES; nn++) {
            if ((m + nn) % 2 == 0) continue;
            if (gcd(m, nn) != 1) continue;
            int a = m*m - nn*nn, b = 2*m*nn;
            int c = m*m + nn*nn;
            if (c > max_c) break;
            for (int sa = -1; sa <= 1; sa += 2) {
                for (int sb = -1; sb <= 1; sb += 2) {
                    if (n >= MAX_TRIPLES) break;
                    out[n].a = sa * a; out[n].b = sb * b; out[n].c = c;
                    out[n].angle = atan2((double)(sa*a), (double)(sb*b));
                    n++;
                    if (n >= MAX_TRIPLES) break;
                    out[n].a = sa * b; out[n].b = sb * a; out[n].c = c;
                    out[n].angle = atan2((double)(sa*b), (double)(sb*a));
                    n++;
                }
            }
        }
    }
    // Sort by angle
    for (int i = 0; i < n-1; i++)
        for (int j = i+1; j < n; j++)
            if (out[i].angle > out[j].angle) { TripleHost t = out[i]; out[i] = out[j]; out[j] = t; }
    return n;
}

// Device arrays
__device__ double d_angles[MAX_TRIPLES];
__device__ int d_orig_idx[MAX_TRIPLES];
__device__ int d_n_triples;

__host__ __device__ __forceinline__ double ang_dist(double a, double b) {
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

__device__ int snap_gpu(double theta) {
    if (d_n_triples == 0) return 0;
    double a = fmod(theta, TAU);
    if (a < 0) a += TAU;
    int lo = 0, hi = d_n_triples - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (d_angles[mid] < a) lo = mid + 1; else hi = mid;
    }
    if (lo == 0) {
        return ang_dist(a, d_angles[d_n_triples-1]) <= ang_dist(a, d_angles[0])
            ? d_orig_idx[d_n_triples-1] : d_orig_idx[0];
    }
    return ang_dist(a, d_angles[lo-1]) <= ang_dist(a, d_angles[lo])
        ? d_orig_idx[lo-1] : d_orig_idx[lo];
}

// Batch snap kernel — each thread handles one query
__global__ void snap_batch(const double* queries, int* results, double* dists, int nq) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= nq) return;
    double theta = queries[tid];
    int idx = snap_gpu(theta);
    double a = fmod(theta, TAU);
    if (a < 0) a += TAU;
    results[tid] = idx;
    dists[tid] = ang_dist(a, d_angles[idx]);
}

// Holonomy kernel — each thread runs an independent random walk
__global__ void holonomy_kernel(int n_steps, int max_step, double* max_disp, int n_walks, unsigned long long seed) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n_walks) return;
    
    int pos = 0;
    double md = 0.0;
    unsigned long long s = seed + tid * 123456789ULL;
    
    for (int i = 0; i < n_steps; i++) {
        s ^= s << 13; s ^= s >> 7; s ^= s << 17;
        int step = (int)(s % (unsigned int)(d_n_triples / 10));
        if (step < 1) step = 1;
        pos = (pos + step) % d_n_triples;
        double d = ang_dist(d_angles[pos], d_angles[0]);
        if (d > md) md = d;
    }
    max_disp[tid] = md;
}

// CPU reference
int snap_cpu(const TripleHost* triples, int n, double theta) {
    if (n == 0) return 0;
    double a = fmod(theta, TAU);
    if (a < 0) a += TAU;
    int lo = 0, hi = n - 1;
    while (lo < hi) { int mid = (lo+hi)/2; if (triples[mid].angle < a) lo = mid+1; else hi = mid; }
    if (lo == 0) {
        double dl = ang_dist(a, triples[n-1].angle), df = ang_dist(a, triples[0].angle);
        return dl <= df ? n-1 : 0;
    }
    return ang_dist(a, triples[lo-1].angle) <= ang_dist(a, triples[lo].angle) ? lo-1 : lo;
}

int main() {
    printf("=== CUDA Constraint Theory Snap Benchmark ===\n");
    
    // Generate triples
    TripleHost triples[MAX_TRIPLES];
    int n = generate_triples(triples, 50000);
    printf("Generated %d triples (max_c=50000)\n", n);
    
    // Copy to device constant memory
    double h_angles[MAX_TRIPLES];
    int h_idx[MAX_TRIPLES];
    for (int i = 0; i < n; i++) { h_angles[i] = triples[i].angle; h_idx[i] = i; }
    cudaMemcpyToSymbol(d_angles, h_angles, n * sizeof(double));
    cudaMemcpyToSymbol(d_orig_idx, h_idx, n * sizeof(int));
    cudaMemcpyToSymbol(d_n_triples, &n, sizeof(int));
    
    // === SNAP BENCHMARK ===
    int NQ = 1000000; // 1M queries
    double* h_queries = (double*)malloc(NQ * sizeof(double));
    for (int i = 0; i < NQ; i++) h_queries[i] = (double)i / NQ * TAU;
    
    double* d_queries; int* d_results; double* d_dists;
    cudaMalloc(&d_queries, NQ * sizeof(double));
    cudaMalloc(&d_results, NQ * sizeof(int));
    cudaMalloc(&d_dists, NQ * sizeof(double));
    cudaMemcpy(d_queries, h_queries, NQ * sizeof(double), cudaMemcpyHostToDevice);
    
    int* h_results = (int*)malloc(NQ * sizeof(int));
    
    // GPU batch snap
    int threads = 256;
    int blocks = (NQ + threads - 1) / threads;
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    cudaEventRecord(start);
    snap_batch<<<blocks, threads>>>(d_queries, d_results, d_dists, NQ);
    cudaDeviceSynchronize();
    cudaEventRecord(stop);
    float gpu_ms;
    cudaEventElapsedTime(&gpu_ms, start, stop);
    
    cudaMemcpy(h_results, d_results, NQ * sizeof(int), cudaMemcpyDeviceToHost);
    
    // CPU sequential snap (sample 10K for fairness)
    int CPU_N = 10000;
    auto cpu_start = std::chrono::high_resolution_clock::now();
    int cpu_sum = 0;
    for (int i = 0; i < CPU_N; i++) cpu_sum += snap_cpu(triples, n, h_queries[i * (NQ/CPU_N)]);
    auto cpu_end = std::chrono::high_resolution_clock::now();
    double cpu_ms = std::chrono::duration<double, std::milli>(cpu_end - cpu_start).count();
    
    // Verify correctness (sample 10K)
    int disagree = 0;
    for (int i = 0; i < CPU_N; i++) {
        int cpu_r = snap_cpu(triples, n, h_queries[i * (NQ/CPU_N)]);
        if (h_results[i * (NQ/CPU_N)] != cpu_r) disagree++;
    }
    
    double gpu_qps = NQ / (gpu_ms / 1000.0);
    double cpu_qps = CPU_N / (cpu_ms / 1000.0);
    
    printf("\n=== SNAP RESULTS ===\n");
    printf("GPU: %.1f ms for %d queries = %.0f qps\n", gpu_ms, NQ, gpu_qps);
    printf("CPU: %.1f ms for %d queries = %.0f qps (extrapolated)\n", cpu_ms, CPU_N, cpu_qps);
    printf("Speedup: %.0fx\n", gpu_qps / cpu_qps);
    printf("Correctness: %d/%d disagreements (%.4f%% agree)\n", disagree, CPU_N, 100.0*(1.0 - (double)disagree/CPU_N));
    
    // === HOLOMONY BENCHMARK ===
    int N_WALKS = 10000;
    int N_STEPS = 10000;
    double* d_max_disp; double* h_max_disp = (double*)malloc(N_WALKS * sizeof(double));
    cudaMalloc(&d_max_disp, N_WALKS * sizeof(double));
    
    int hblocks = (N_WALKS + threads - 1) / threads;
    cudaEventRecord(start);
    holonomy_kernel<<<hblocks, threads>>>(N_STEPS, n/10, d_max_disp, N_WALKS, 42);
    cudaDeviceSynchronize();
    cudaEventRecord(stop);
    cudaEventElapsedTime(&gpu_ms, start, stop);
    cudaMemcpy(h_max_disp, d_max_disp, N_WALKS * sizeof(double), cudaMemcpyDeviceToHost);
    
    double avg_disp = 0, max_d = 0;
    for (int i = 0; i < N_WALKS; i++) { avg_disp += h_max_disp[i]; if (h_max_disp[i] > max_d) max_d = h_max_disp[i]; }
    avg_disp /= N_WALKS;
    
    printf("\n=== HOLOMONY RESULTS ===\n");
    printf("GPU: %.1f ms for %d walks x %d steps\n", gpu_ms, N_WALKS, N_STEPS);
    printf("Avg max displacement: %.4f rad (%.1f deg)\n", avg_disp, avg_disp * 180.0 / 3.14159265);
    printf("Max displacement across all walks: %.4f rad (%.1f deg)\n", max_d, max_d * 180.0 / 3.14159265);
    
    printf("\n=== GPU INFO ===\n");
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);
    printf("Device: %s\n", prop.name);
    printf("SMs: %d, Clock: %.0f MHz\n", prop.multiProcessorCount, prop.clockRate / 1000.0);
    printf("Global mem: %.0f MB, Shared/SM: %.0f KB\n", prop.totalGlobalMem/1e6, prop.sharedMemPerBlock/1024.0);
    printf("Warp size: %d, Max threads/block: %d\n", prop.warpSize, prop.maxThreadsPerBlock);
    
    // Cleanup
    cudaFree(d_queries); cudaFree(d_results); cudaFree(d_dists); cudaFree(d_max_disp);
    free(h_queries); free(h_results); free(h_max_disp);
    cudaEventDestroy(start); cudaEventDestroy(stop);
    
    return 0;
}
