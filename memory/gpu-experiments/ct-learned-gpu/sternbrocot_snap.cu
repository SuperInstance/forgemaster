#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <cuda_runtime.h>

#define TAU 6.283185307179586

// Stern-Brocot snap on GPU: each thread does an independent Stern-Brocot walk
// to find the best rational approximation of tan(theta) with a^2+b^2 <= max_c^2.
// No precomputed array needed — works at max_c = 10^9.

__device__ long long sb_gcd(long long a, long long b) {
    while (b) { long long t = b; b = a % b; a = t; }
    return a;
}

__device__ double sb_adist(double a, double b) {
    a = fmod(a, TAU); if (a < 0) a += TAU;
    b = fmod(b, TAU); if (b < 0) b += TAU;
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

// Stern-Brocot snap: find best (a,b) with a^2+b^2 <= max_c^2
// Returns the angle of the best triple and the distance
__global__ void sternbrocot_snap_kernel(const double* queries, int nq,
                                         long long max_c, long long max_c_sq,
                                         double* out_angles, double* out_dists,
                                         long long* out_a, long long* out_b, long long* out_c) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    
    double theta = fmod(queries[t], TAU);
    if (theta < 0) theta += TAU;
    double tan_t = tan(theta);
    
    // Handle special cases
    if (tan_t <= 0.0) {
        out_angles[t] = 0.0; out_dists[t] = sb_adist(theta, 0.0);
        out_a[t] = 0; out_b[t] = 1; out_c[t] = 1;
        return;
    }
    
    // Stern-Brocot descent
    long long la = 0, lb = 1;  // left bound 0/1
    long long ra = 1, rb = 0;  // right bound 1/0 (infinity)
    
    // Track best candidate
    long long best_a = 0, best_b = 1, best_c = 1;
    double best_dist = TAU;
    
    for (int step = 0; step < 200; step++) {
        long long ma = la + ra;
        long long mb = lb + rb;
        
        // Check hypotenuse constraint
        double c_sq = (double)ma * ma + (double)mb * mb;
        if (c_sq > (double)max_c_sq) break;
        
        long long c = (long long)sqrt(c_sq);
        if (c * c == ma * ma + mb * mb) {
            // Valid Pythagorean triple!
            double ang1 = atan2((double)ma, (double)mb);
            double d1 = sb_adist(theta, ang1);
            if (d1 < best_dist) {
                best_dist = d1; best_a = ma; best_b = mb; best_c = c;
            }
            double ang2 = atan2((double)mb, (double)ma);
            double d2 = sb_adist(theta, ang2);
            if (d2 < best_dist) {
                best_dist = d2; best_a = mb; best_b = ma; best_c = c;
            }
        }
        
        double mediant = (double)ma / (double)mb;
        if (mediant < tan_t) { la = ma; lb = mb; }
        else { ra = ma; rb = mb; }
    }
    
    out_angles[t] = atan2((double)best_a, (double)best_b);
    out_dists[t] = best_dist;
    out_a[t] = best_a; out_b[t] = best_b; out_c[t] = best_c;
}

// Binary search snap (baseline for comparison)
__global__ void binary_snap_kernel(const double* angles, int n,
                                    const double* queries, int nq,
                                    int* results) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nq) return;
    double q = fmod(queries[t], TAU); if (q < 0) q += TAU;
    int lo = 0, hi = n - 1;
    while (lo < hi) { int m = (lo+hi)/2; if (angles[m] < q) lo=m+1; else hi=m; }
    if (lo == 0) { double dl=sb_adist(q,angles[n-1]),dh=sb_adist(q,angles[0]); results[t]=dl<=dh?n-1:0; }
    else { double dl=sb_adist(q,angles[lo-1]),dh=sb_adist(q,angles[lo]); results[t]=dl<=dh?lo-1:lo; }
}

int main() {
    // Generate precomputed triples for binary search baseline
    static double raw[50000 * 20];
    int n = 0;
    for (int m = 2; m <= 354 && n < 50000*20; m++)
        for (int nn = 1; nn < m && n < 50000*20; nn++) {
            if ((m+nn)%2==0) continue;
            int g=m; int b2=nn; while(b2){int t=b2;b2=g%b2;g=t;} if(g!=1) continue;
            int a=m*m-nn*nn, b=2*m*nn, c=m*m+nn*nn;
            if (c>50000) break;
            for (int si=-1;si<=1;si+=2) for(int sj=-1;sj<=1;sj+=2) {
                raw[n++]=atan2((double)(si*a),(double)(sj*b));
                raw[n++]=atan2((double)(si*b),(double)(sj*a));
            }
        }
    
    typedef struct { double angle; int idx; } AI;
    static AI idx[50000*20];
    for (int i=0;i<n;i++){idx[i].angle=raw[i];idx[i].idx=i;}
    // Simple sort
    for (int i=0;i<n-1;i++) for (int j=i+1;j<n;j++)
        if (idx[i].angle>idx[j].angle){AI t=idx[i];idx[i]=idx[j];idx[j]=t;}
    
    static double sorted[50000*20];
    for (int i=0;i<n;i++) sorted[i]=idx[i].angle;
    
    int NQ = 10000000; // 10M (SB is slower, use fewer)
    
    double *d_sorted, *d_queries, *d_sb_angles, *d_sb_dists;
    long long *d_sb_a, *d_sb_b, *d_sb_c;
    int *d_results;
    
    cudaMalloc(&d_sorted, n*8);
    cudaMalloc(&d_queries, NQ*8);
    cudaMalloc(&d_sb_angles, NQ*8);
    cudaMalloc(&d_sb_dists, NQ*8);
    cudaMalloc(&d_sb_a, NQ*8);
    cudaMalloc(&d_sb_b, NQ*8);
    cudaMalloc(&d_sb_c, NQ*8);
    cudaMalloc(&d_results, NQ*4);
    
    cudaMemcpy(d_sorted, sorted, n*8, cudaMemcpyHostToDevice);
    
    double* hQ = (double*)malloc(NQ*8);
    for (long long i=0;i<NQ;i++)
        hQ[i]=(double)(i*2654435761ULL%1000003ULL)/1000003.0*TAU;
    cudaMemcpy(d_queries, hQ, NQ*8, cudaMemcpyHostToDevice);
    
    int th=256, bl=(NQ+th-1)/th;
    
    // Benchmark binary search
    float t_bin = 1e9;
    for (int r=0;r<3;r++) {
        cudaEvent_t s,e; cudaEventCreate(&s); cudaEventCreate(&e);
        cudaEventRecord(s);
        binary_snap_kernel<<<bl,th>>>(d_sorted,n,d_queries,NQ,d_results);
        cudaEventRecord(e); cudaEventSynchronize(e);
        float ms; cudaEventElapsedTime(&ms,s,e);
        if(ms<t_bin)t_bin=ms;
        cudaEventDestroy(s); cudaEventDestroy(e);
    }
    
    // Benchmark Stern-Brocot (different max_c values)
    long long max_cs[] = {100, 1000, 10000, 50000};
    const char* labels[] = {"100", "1K", "10K", "50K"};
    
    printf("=== Stern-Brocot GPU Snap (10M queries) ===\n");
    printf("Binary baseline: %.2f ms  %.2f M qps\n\n", t_bin, NQ/(t_bin/1000.0)/1e6);
    
    for (int mc = 0; mc < 4; mc++) {
        long long max_c = max_cs[mc];
        long long max_c_sq = max_c * max_c;
        
        float t_sb = 1e9;
        for (int r=0;r<3;r++) {
            cudaEvent_t s,e; cudaEventCreate(&s); cudaEventCreate(&e);
            cudaEventRecord(s);
            sternbrocot_snap_kernel<<<bl,th>>>(d_queries,NQ,max_c,max_c_sq,
                                                d_sb_angles,d_sb_dists,d_sb_a,d_sb_b,d_sb_c);
            cudaEventRecord(e); cudaEventSynchronize(e);
            float ms; cudaEventElapsedTime(&ms,s,e);
            if(ms<t_sb)t_sb=ms;
            cudaEventDestroy(s); cudaEventDestroy(e);
        }
        
        // Verify a sample
        long long ha[100], hb[100], hc[100];
        double hd[100];
        cudaMemcpy(ha, d_sb_a, 100*8, cudaMemcpyDeviceToHost);
        cudaMemcpy(hb, d_sb_b, 100*8, cudaMemcpyDeviceToHost);
        cudaMemcpy(hc, d_sb_c, 100*8, cudaMemcpyDeviceToHost);
        cudaMemcpy(hd, d_sb_dists, 100*8, cudaMemcpyDeviceToHost);
        
        int valid = 0;
        for (int i=0;i<100;i++) if (ha[i]*ha[i]+hb[i]*hb[i]==hc[i]*hc[i]) valid++;
        
        printf("SB max_c=%-5s: %7.2f ms  %8.2f M qps  (%.2fx vs bin)  %d/100 valid triples\n",
            labels[mc], t_sb, NQ/(t_sb/1000.0)/1e6, t_bin/t_sb, valid);
    }
    
    cudaFree(d_sorted); cudaFree(d_queries); cudaFree(d_sb_angles);
    cudaFree(d_sb_dists); cudaFree(d_sb_a); cudaFree(d_sb_b); cudaFree(d_sb_c);
    cudaFree(d_results); free(hQ);
}
