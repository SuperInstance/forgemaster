#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <cuda_runtime.h>

#define TAU 6.283185307179586
#define MAX_C 50000
#define SEGMENTS 256
#define EPSILON 64

// Triple generation
int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }

int gen_triples(double* angles, double* xy_a, double* xy_b, int* cs, int max_c) {
    int n = 0;
    int max_m = (int)(sqrt((double)max_c) / 1.414) + 1;
    for (int m = 2; m <= max_m && n < MAX_C * 20; m++)
        for (int nn = 1; nn < m && n < MAX_C * 20; nn++) {
            if ((m + nn) % 2 == 0) continue;
            if (gcd(m, nn) != 1) continue;
            int a = m*m - nn*nn, b = 2*m*nn, c = m*m + nn*nn;
            if (c > max_c) break;
            int signs[2] = {1, -1};
            for (int si = 0; si < 2; si++)
                for (int sj = 0; sj < 2; sj++) {
                    angles[n] = atan2((double)(signs[si]*a), (double)(signs[sj]*b));
                    xy_a[n] = signs[si]*a; xy_b[n] = signs[sj]*b; cs[n] = c; n++;
                    angles[n] = atan2((double)(signs[si]*b), (double)(signs[sj]*a));
                    xy_a[n] = signs[si]*b; xy_b[n] = signs[sj]*a; cs[n] = c; n++;
                }
        }
    return n;
}

// Sort angles with index tracking
typedef struct { double angle; int idx; } AngleIdx;
int cmp_angle(const void* a, const void* b) {
    double d = ((AngleIdx*)a)->angle - ((AngleIdx*)b)->angle;
    return (d > 0) - (d < 0);
}

// Build piecewise linear model on CPU
typedef struct { double boundary; double slope; double intercept; } Segment;

void build_model(double* angles, int n, Segment* model, int nseg) {
    int seg_size = n / nseg;
    for (int s = 0; s < nseg; s++) {
        int lo = s * seg_size;
        int hi = (s == nseg - 1) ? n - 1 : (s + 1) * seg_size;
        model[s].boundary = angles[lo];
        double x0 = angles[lo], y0 = (double)lo;
        double x1 = angles[hi], y1 = (double)hi;
        double dx = x1 - x0;
        if (fabs(dx) > 1e-15) {
            model[s].slope = (y1 - y0) / dx;
            model[s].intercept = y0 - model[s].slope * x0;
        } else {
            model[s].slope = 0;
            model[s].intercept = y0;
        }
    }
}

// Angular distance on [0, 2pi)
__device__ double adist(double a, double b) {
    a = fmod(a, TAU); if (a < 0) a += TAU;
    b = fmod(b, TAU); if (b < 0) b += TAU;
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

// Binary search kernel (baseline)
__global__ void binary_search_snap(const double* __restrict__ angles, int n,
                                    const double* __restrict__ queries, int nq,
                                    int* results) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    double q = fmod(queries[t], TAU); if (q < 0) q += TAU;
    int lo = 0, hi = n - 1;
    while (lo < hi) { int m = (lo+hi)/2; if (angles[m] < q) lo=m+1; else hi=m; }
    if (lo == 0) {
        double dl = adist(q, angles[n-1]), dh = adist(q, angles[0]);
        results[t] = dl <= dh ? n-1 : 0;
    } else {
        double dl = adist(q, angles[lo-1]), dh = adist(q, angles[lo]);
        results[t] = dl <= dh ? lo-1 : lo;
    }
}

// Learned index kernel: predict + epsilon correction
__global__ void learned_snap(const Segment* __restrict__ model, int nseg,
                              const double* __restrict__ angles, int n,
                              const double* __restrict__ queries, int nq,
                              int* results) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    
    double q = fmod(queries[t], TAU); if (q < 0) q += TAU;
    
    // Find segment via binary search on boundaries
    int seg = 0;
    for (int i = 1; i < nseg; i++)
        if (q >= model[i].boundary) seg = i;
    seg = min(seg, nseg - 1);
    
    // Predict index
    double predicted = model[seg].slope * q + model[seg].intercept;
    int center = max(0, min((int)round(predicted), n - 1));
    
    // Linear scan ±epsilon for actual nearest
    int lo = max(0, center - EPSILON);
    int hi = min(n - 1, center + EPSILON);
    int best = lo;
    double best_d = adist(q, angles[lo]);
    for (int i = lo + 1; i <= hi; i++) {
        double d = adist(q, angles[i]);
        if (d < best_d) { best_d = d; best = i; }
    }
    results[t] = best;
}

int main() {
    // Generate triples
    static double raw_angles[MAX_C * 20];
    static double raw_a[MAX_C * 20], raw_b[MAX_C * 20];
    static int raw_c[MAX_C * 20];
    int n = gen_triples(raw_angles, raw_a, raw_b, raw_c, MAX_C);
    
    // Sort by angle
    static AngleIdx indexed[MAX_C * 20];
    for (int i = 0; i < n; i++) { indexed[i].angle = raw_angles[i]; indexed[i].idx = i; }
    qsort(indexed, n, sizeof(AngleIdx), cmp_angle);
    
    static double sorted_angles[MAX_C * 20];
    static int sorted_a[MAX_C * 20], sorted_b[MAX_C * 20], sorted_c[MAX_C * 20];
    for (int i = 0; i < n; i++) {
        sorted_angles[i] = indexed[i].angle;
        sorted_a[i] = (int)raw_a[indexed[i].idx];
        sorted_b[i] = (int)raw_b[indexed[i].idx];
        sorted_c[i] = raw_c[indexed[i].idx];
    }
    
    printf("Generated %d triples\n", n);
    
    // Build model
    static Segment model[SEGMENTS];
    build_model(sorted_angles, n, model, SEGMENTS);
    printf("Built %d-segment model\n", SEGMENTS);
    
    // GPU alloc
    double *d_angles, *d_queries;
    int *d_results_bin, *d_results_learned;
    Segment *d_model;
    
    int NQ = 100000000;
    cudaMalloc(&d_angles, n * sizeof(double));
    cudaMalloc(&d_model, SEGMENTS * sizeof(Segment));
    cudaMalloc(&d_queries, NQ * sizeof(double));
    cudaMalloc(&d_results_bin, NQ * sizeof(int));
    cudaMalloc(&d_results_learned, NQ * sizeof(int));
    
    cudaMemcpy(d_angles, sorted_angles, n * sizeof(double), cudaMemcpyHostToDevice);
    cudaMemcpy(d_model, model, SEGMENTS * sizeof(Segment), cudaMemcpyHostToDevice);
    
    // Generate queries
    static double* h_queries = (double*)malloc(NQ * sizeof(double));
    for (long long i = 0; i < NQ; i++)
        h_queries[i] = (double)(i * 2654435761ULL % 1000003ULL) / 1000003.0 * TAU;
    cudaMemcpy(d_queries, h_queries, NQ * sizeof(double), cudaMemcpyHostToDevice);
    
    int th = 256, bl = (NQ + th - 1) / th;
    static int* h_bin = (int*)malloc(10000 * sizeof(int));
    static int* h_learned = (int*)malloc(10000 * sizeof(int));
    
    // Benchmark binary search (3 runs)
    float t_bin = 1e9;
    for (int run = 0; run < 3; run++) {
        cudaEvent_t s, e; cudaEventCreate(&s); cudaEventCreate(&e);
        cudaEventRecord(s);
        binary_search_snap<<<bl, th>>>(d_angles, n, d_queries, NQ, d_results_bin);
        cudaEventRecord(e); cudaEventSynchronize(e);
        float ms; cudaEventElapsedTime(&ms, s, e);
        if (ms < t_bin) t_bin = ms;
        cudaEventDestroy(s); cudaEventDestroy(e);
    }
    
    // Benchmark learned index (3 runs)
    float t_learned = 1e9;
    for (int run = 0; run < 3; run++) {
        cudaEvent_t s, e; cudaEventCreate(&s); cudaEventCreate(&e);
        cudaEventRecord(s);
        learned_snap<<<bl, th>>>(d_model, SEGMENTS, d_angles, n, d_queries, NQ, d_results_learned);
        cudaEventRecord(e); cudaEventSynchronize(e);
        float ms; cudaEventElapsedTime(&ms, s, e);
        if (ms < t_learned) t_learned = ms;
        cudaEventDestroy(s); cudaEventDestroy(e);
    }
    
    // Verify correctness
    cudaMemcpy(h_bin, d_results_bin, 10000 * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_learned, d_results_learned, 10000 * sizeof(int), cudaMemcpyDeviceToHost);
    int agree = 0;
    for (int i = 0; i < 10000; i++) if (h_bin[i] == h_learned[i]) agree++;
    
    printf("\n=== Learned Index vs Binary Search ===\n");
    printf("Triples: %d, Queries: %dM, Segments: %d, Epsilon: %d\n", n, NQ/1000000, SEGMENTS, EPSILON);
    printf("Binary search:  %7.2f ms  %8.2f B qps\n", t_bin, NQ / (t_bin / 1000.0) / 1e9);
    printf("Learned index:  %7.2f ms  %8.2f B qps  (%.2fx)\n", t_learned, NQ / (t_learned / 1000.0) / 1e9, t_bin / t_learned);
    printf("Accuracy: %d/10000 agree (%.1f%%)\n", agree, agree / 100.0);
    
    cudaFree(d_angles); cudaFree(d_model); cudaFree(d_queries);
    cudaFree(d_results_bin); cudaFree(d_results_learned);
    free(h_queries); free(h_bin); free(h_learned);
}
