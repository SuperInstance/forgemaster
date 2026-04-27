#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <cuda_runtime.h>

#define TAU 6.283185307179586
#define MAX_C 50000
#define SEGMENTS 256
#define CORRECTION 64  // binary search within ±this window

int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }

int gen_triples(double* angles, int max_c) {
    int n = 0;
    int max_m = (int)(sqrt((double)max_c) / 1.414) + 1;
    for (int m = 2; m <= max_m && n < MAX_C * 20; m++)
        for (int nn = 1; nn < m && n < MAX_C * 20; nn++) {
            if ((m + nn) % 2 == 0) continue;
            if (gcd(m, nn) != 1) continue;
            int a = m*m - nn*nn, b = 2*m*nn, c = m*m + nn*nn;
            if (c > max_c) break;
            for (int si = -1; si <= 1; si += 2)
                for (int sj = -1; sj <= 1; sj += 2) {
                    angles[n++] = atan2((double)(si*a), (double)(sj*b));
                    angles[n++] = atan2((double)(si*b), (double)(sj*a));
                }
        }
    return n;
}

typedef struct { double boundary; double slope; double intercept; } Seg;
typedef struct { double angle; int idx; } AI;
int cmp_ai(const void* a, const void* b) {
    double d = ((AI*)a)->angle - ((AI*)b)->angle;
    return (d > 0) - (d < 0);
}

void build_model(double* angles, int n, Seg* model, int nseg) {
    int ss = n / nseg;
    for (int s = 0; s < nseg; s++) {
        int lo = s * ss, hi = (s == nseg-1) ? n-1 : (s+1)*ss;
        model[s].boundary = angles[lo];
        double x0 = angles[lo], y0 = (double)lo;
        double x1 = angles[hi], y1 = (double)hi;
        double dx = x1 - x0;
        if (fabs(dx) > 1e-15) { model[s].slope = (y1-y0)/dx; model[s].intercept = y0 - model[s].slope*x0; }
        else { model[s].slope = 0; model[s].intercept = y0; }
    }
}

__device__ double adist(double a, double b) {
    a = fmod(a, TAU); if (a < 0) a += TAU;
    b = fmod(b, TAU); if (b < 0) b += TAU;
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

// V1: Pure binary search (baseline)
__global__ void kern_bin(const double* A, int n, const double* Q, int nq, int* R) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    double q = fmod(Q[t], TAU); if (q < 0) q += TAU;
    int lo = 0, hi = n - 1;
    while (lo < hi) { int m = (lo+hi)/2; if (A[m] < q) lo=m+1; else hi=m; }
    if (lo == 0) { double dl=adist(q,A[n-1]),dh=adist(q,A[0]); R[t]=dl<=dh?n-1:0; }
    else { double dl=adist(q,A[lo-1]),dh=adist(q,A[lo]); R[t]=dl<=dh?lo-1:lo; }
}

// V2: Learned prediction + binary search correction (O(log epsilon))
__global__ void kern_learned_bs(const Seg* M, int ns, const double* A, int n,
                                  const double* Q, int nq, int* R) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    double q = fmod(Q[t], TAU); if (q < 0) q += TAU;
    
    // Find segment
    int seg = 0;
    for (int i = 1; i < ns; i++) if (q >= M[i].boundary) seg = i;
    seg = min(seg, ns - 1);
    
    // Predict
    int center = max(0, min((int)round(M[seg].slope * q + M[seg].intercept), n - 1));
    
    // Binary search in ±CORRECTION window
    int lo = max(0, center - CORRECTION);
    int hi = min(n - 1, center + CORRECTION);
    while (lo < hi) { int m = (lo+hi)/2; if (A[m] < q) lo=m+1; else hi=m; }
    if (lo == 0) { double dl=adist(q,A[n-1]),dh=adist(q,A[0]); R[t]=dl<=dh?n-1:0; }
    else { double dl=adist(q,A[lo-1]),dh=adist(q,A[lo]); R[t]=dl<=dh?lo-1:lo; }
}

// V3: Learned prediction + narrow linear scan (O(epsilon), small epsilon)
__global__ void kern_learned_linear(const Seg* M, int ns, const double* A, int n,
                                     const double* Q, int nq, int* R) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    double q = fmod(Q[t], TAU); if (q < 0) q += TAU;
    
    int seg = 0;
    for (int i = 1; i < ns; i++) if (q >= M[i].boundary) seg = i;
    seg = min(seg, ns - 1);
    
    int center = max(0, min((int)round(M[seg].slope * q + M[seg].intercept), n - 1));
    
    // Narrow linear scan ±8
    int lo = max(0, center - 8);
    int hi = min(n - 1, center + 8);
    int best = lo;
    double best_d = adist(q, A[lo]);
    for (int i = lo+1; i <= hi; i++) {
        double d = adist(q, A[i]);
        if (d < best_d) { best_d = d; best = i; }
    }
    R[t] = best;
}

int main() {
    static double raw[MAX_C * 20];
    int n = gen_triples(raw, MAX_C);
    
    static AI idx[MAX_C * 20];
    for (int i = 0; i < n; i++) { idx[i].angle = raw[i]; idx[i].idx = i; }
    qsort(idx, n, sizeof(AI), cmp_ai);
    
    static double sorted[MAX_C * 20];
    for (int i = 0; i < n; i++) sorted[i] = idx[i].angle;
    
    static Seg model[SEGMENTS];
    build_model(sorted, n, model, SEGMENTS);
    
    double *dA, *dQ; Seg *dM;
    int *dR1, *dR2, *dR3;
    int NQ = 100000000;
    cudaMalloc(&dA, n*8); cudaMalloc(&dM, SEGMENTS*sizeof(Seg));
    cudaMalloc(&dQ, NQ*8);
    cudaMalloc(&dR1, NQ*4); cudaMalloc(&dR2, NQ*4); cudaMalloc(&dR3, NQ*4);
    cudaMemcpy(dA, sorted, n*8, cudaMemcpyHostToDevice);
    cudaMemcpy(dM, model, SEGMENTS*sizeof(Seg), cudaMemcpyHostToDevice);
    
    double* hQ = (double*)malloc(NQ*8);
    for (long long i = 0; i < NQ; i++)
        hQ[i] = (double)(i * 2654435761ULL % 1000003ULL) / 1000003.0 * TAU;
    cudaMemcpy(dQ, hQ, NQ*8, cudaMemcpyHostToDevice);
    
    int th = 256, bl = (NQ+th-1)/th;
    int *h1 = (int*)malloc(10000*4), *h2 = (int*)malloc(10000*4), *h3 = (int*)malloc(10000*4);
    
    float t1=1e9, t2=1e9, t3=1e9;
    for (int r = 0; r < 3; r++) {
        cudaEvent_t s,e;
        cudaEventCreate(&s); cudaEventCreate(&e);
        cudaEventRecord(s);
        kern_bin<<<bl,th>>>(dA,n,dQ,NQ,dR1);
        cudaEventRecord(e); cudaEventSynchronize(e);
        float ms; cudaEventElapsedTime(&ms,s,e);
        if(ms<t1)t1=ms;
        cudaEventDestroy(s); cudaEventDestroy(e);
    }
    for (int r = 0; r < 3; r++) {
        cudaEvent_t s,e;
        cudaEventCreate(&s); cudaEventCreate(&e);
        cudaEventRecord(s);
        kern_learned_bs<<<bl,th>>>(dM,(int)SEGMENTS,dA,n,dQ,NQ,dR2);
        cudaEventRecord(e); cudaEventSynchronize(e);
        float ms; cudaEventElapsedTime(&ms,s,e);
        if(ms<t2)t2=ms;
        cudaEventDestroy(s); cudaEventDestroy(e);
    }
    for (int r = 0; r < 3; r++) {
        cudaEvent_t s,e;
        cudaEventCreate(&s); cudaEventCreate(&e);
        cudaEventRecord(s);
        kern_learned_linear<<<bl,th>>>(dM,(int)SEGMENTS,dA,n,dQ,NQ,dR3);
        cudaEventRecord(e); cudaEventSynchronize(e);
        float ms; cudaEventElapsedTime(&ms,s,e);
        if(ms<t3)t3=ms;
        cudaEventDestroy(s); cudaEventDestroy(e);
    }
    
    cudaMemcpy(h1,dR1,10000*4,cudaMemcpyDeviceToHost);
    cudaMemcpy(h2,dR2,10000*4,cudaMemcpyDeviceToHost);
    cudaMemcpy(h3,dR3,10000*4,cudaMemcpyDeviceToHost);
    int agree2=0, agree3=0;
    for (int i = 0; i < 10000; i++) {
        if (h1[i]==h2[i]) agree2++;
        if (h1[i]==h3[i]) agree3++;
    }
    
    printf("=== Learned Index GPU Benchmarks ===\n");
    printf("Triples: %d, Queries: 100M, Segments: %d\n\n", n, SEGMENTS);
    printf("V1 Binary search:         %7.2f ms  %8.2f B qps  (baseline)\n", t1, NQ/(t1/1000.0)/1e9);
    printf("V2 Learned+BS(±%d):       %7.2f ms  %8.2f B qps  (%.2fx)  %d%% agree\n", CORRECTION, t2, NQ/(t2/1000.0)/1e9, t1/t2, agree2/100);
    printf("V3 Learned+Linear(±8):    %7.2f ms  %8.2f B qps  (%.2fx)  %d%% agree\n", t3, NQ/(t3/1000.0)/1e9, t1/t3, agree3/100);
    
    cudaFree(dA); cudaFree(dM); cudaFree(dQ); cudaFree(dR1); cudaFree(dR2); cudaFree(dR3);
    free(hQ); free(h1); free(h2); free(h3);
}
