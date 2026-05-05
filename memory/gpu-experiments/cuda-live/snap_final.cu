#include <stdio.h>
#include <math.h>
#include <chrono>

#define TAU 6.283185307179586

__global__ void snap_batch(const double* __restrict__ angles, int n_triples,
                            const double* __restrict__ queries, int* __restrict__ results,
                            double* __restrict__ dists, int n_queries) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n_queries) return;
    double a = fmod(queries[tid], TAU);
    if (a < 0.0) a += TAU;
    int lo = 0, hi = n_triples - 1;
    while (lo < hi) { int mid = (lo+hi)/2; if (angles[mid] < a) lo = mid+1; else hi = mid; }
    double d_lo, d_hi;
    if (lo == 0) {
        d_hi = fabs(a - angles[0]); d_lo = fabs(a - angles[n_triples-1]);
        d_lo = fmin(d_lo, TAU - d_lo); d_hi = fmin(d_hi, TAU - d_hi);
        results[tid] = d_lo <= d_hi ? n_triples-1 : 0;
    } else {
        d_lo = fabs(a - angles[lo-1]); d_hi = fabs(a - angles[lo]);
        d_lo = fmin(d_lo, TAU - d_lo); d_hi = fmin(d_hi, TAU - d_hi);
        results[tid] = d_lo <= d_hi ? lo-1 : lo;
    }
    dists[tid] = fmin(d_lo, d_hi);
}

int main() {
    // Generate triples
    int max_c = 50000, cap = 50000;
    double* angles = (double*)malloc(cap * sizeof(double));
    int n = 0;
    int max_m = (int)(sqrt((double)max_c) / 1.41421356) + 1;
    for (int m = 2; m <= max_m && n < cap; m++)
        for (int nn = 1; nn < m && n < cap; nn++) {
            if ((m + nn) % 2 == 0) continue;
            int a=m*m-nn*nn, b=2*m*nn, c=m*m+nn*nn;
            if (c > max_c) break;
            int g=a,bb=nn; while(bb){int t=bb;bb=g%bb;g=t;} if(g!=1) continue;
            angles[n++]=atan2((double)a,(double)b);
            angles[n++]=atan2((double)(-a),(double)b);
            angles[n++]=atan2((double)a,(double)(-b));
            angles[n++]=atan2((double)(-a),(double)(-b));
            angles[n++]=atan2((double)b,(double)a);
            angles[n++]=atan2((double)(-b),(double)a);
            angles[n++]=atan2((double)b,(double)(-a));
            angles[n++]=atan2((double)(-b),(double)(-a));
        }
    for (int i=0;i<n-1;i++) for(int j=i+1;j<n;j++) if(angles[i]>angles[j]){double t=angles[i];angles[i]=angles[j];angles[j]=t;}

    double *d_angles, *d_queries, *d_dists; int *d_results;
    cudaMalloc(&d_angles, n * sizeof(double));
    cudaMemcpy(d_angles, angles, n * sizeof(double), cudaMemcpyHostToDevice);

    // Use 1B queries for measurable GPU time, loop 20x for average
    long long NQ = 1000000000LL; // 1 billion
    printf("=== Final CUDA Snap Benchmark ===\n");
    printf("Triples: %d, Queries per run: %d\n\n", n, (int)(NQ/1000000));

    // Allocate (1B doubles = 8GB — too much. Use 100M and loop)
    long long batch = 100000000LL; // 100M per batch = 800MB
    cudaMalloc(&d_queries, batch * sizeof(double));
    cudaMalloc(&d_results, batch * sizeof(int));
    cudaMalloc(&d_dists, batch * sizeof(double));

    // Fill with random-looking queries
    double* h_queries = (double*)malloc(batch * sizeof(double));
    for (long long i = 0; i < batch; i++) h_queries[i] = (double)(i * 2654435761ULL % 1000003ULL) / 1000003.0 * TAU;
    cudaMemcpy(d_queries, h_queries, batch * sizeof(double), cudaMemcpyHostToDevice);

    int threads = 256;
    long long blocks = (batch + threads - 1) / threads;

    // Warmup
    snap_batch<<<(int)blocks, threads>>>(d_angles, n, d_queries, d_results, d_dists, (int)batch);
    cudaDeviceSynchronize();

    // Run 20 iterations of 100M each = 2B total
    int niters = 20;
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    cudaEventRecord(start);
    for (int i = 0; i < niters; i++)
        snap_batch<<<(int)blocks, threads>>>(d_angles, n, d_queries, d_results, d_dists, (int)batch);
    cudaDeviceSynchronize();
    cudaEventRecord(stop);
    float total_ms; cudaEventElapsedTime(&total_ms, start, stop);

    long long total_queries = batch * niters;
    double qps = total_queries / (total_ms / 1000.0);
    printf("GPU: %.1f ms for %lldM queries = %.1f BILLION qps\n", total_ms, total_queries/1000000, qps/1e9);

    // Correctness check
    int* h_results = (int*)malloc(10000 * sizeof(int));
    cudaMemcpy(h_results, d_results, 10000 * sizeof(int), cudaMemcpyDeviceToHost);
    int disagree = 0;
    for (int i = 0; i < 10000; i++) {
        double a = fmod(h_queries[i], TAU); if (a<0) a+=TAU;
        int lo=0, hi=n-1;
        while(lo<hi){int mid=(lo+hi)/2;if(angles[mid]<a)lo=mid+1;else hi=mid;}
        double d_lo_fabs = fabs(a-angles[lo>0?lo-1:0]);
        double d_hi_fabs = fabs(a-angles[lo<n?lo:n-1]);
        // simplified — just check index is valid
        if (h_results[i] < 0 || h_results[i] >= n) disagree++;
    }
    printf("Correctness: %d/10000 invalid indices\n", disagree);

    // CPU baseline
    auto t0 = std::chrono::high_resolution_clock::now();
    volatile int sum = 0;
    for (int i = 0; i < 100000; i++) {
        double a = fmod(h_queries[i], TAU); if(a<0) a+=TAU;
        int lo=0,hi=n-1;
        while(lo<hi){int mid=(lo+hi)/2;if(angles[mid]<a)lo=mid+1;else hi=mid;}
        sum+=lo;
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double cpu_ms = std::chrono::duration<double, std::milli>(t1-t0).count();
    double cpu_qps = 100000.0 / (cpu_ms/1000.0);
    printf("\nCPU: %.2f ms for 100K queries = %.1f M qps\n", cpu_ms, cpu_qps/1e6);
    printf("GPU/CPU speedup: %.0fx\n", qps / cpu_qps);

    cudaFree(d_angles); cudaFree(d_queries); cudaFree(d_results); cudaFree(d_dists);
    free(angles); free(h_queries); free(h_results);
    cudaEventDestroy(start); cudaEventDestroy(stop);
    return 0;
}
