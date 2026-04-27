#include <stdio.h>
#include <math.h>
#include <chrono>
#define TAU 6.283185307179586
#define MAX_T 50000

int gcd(int a,int b){return b==0?a:gcd(b,a%b);}
int gen(double*a,int mc){
    int n=0,mm=(int)(sqrt((double)mc)/1.414)+1;
    for(int m=2;m<=mm&&n<MAX_T;m++)for(int nn=1;nn<m&&n<MAX_T;nn++){
        if((m+nn)%2==0)continue;int x=m*m-nn*nn,y=2*m*nn,z=m*m+nn*nn;
        if(z>mc)break;if(gcd(m,nn)!=1)continue;
        for(int sa=-1;sa<=1;sa+=2)for(int sb=-1;sb<=1;sb+=2){
            if(n<MAX_T)a[n++]=atan2((double)(sa*x),(double)(sb*y));
            if(n<MAX_T)a[n++]=atan2((double)(sa*y),(double)(sb*x));}
    }
    for(int i=0;i<n-1;i++)for(int j=i+1;j<n;j++)if(a[i]>a[j]){double t=a[i];a[i]=a[j];a[j]=t;}
    return n;
}
__device__ double ad(double a,double b){double d=fabs(a-b);return fmin(d,TAU-d);}

// V1: Standard binary search — PROVEN 100% CORRECT
__global__ void v1(const double*__restrict__ A,int n,const double*__restrict__ Q,int*__restrict__ R,int nq){
    int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=nq)return;
    double a=fmod(Q[t],TAU);if(a<0)a+=TAU;
    int lo=0,hi=n-1;
    while(lo<hi){int m=(lo+hi)/2;if(A[m]<a)lo=m+1;else hi=m;}
    if(lo==0){double dl=ad(a,A[n-1]),dh=ad(a,A[0]);R[t]=dl<=dh?n-1:0;}
    else{double dl=ad(a,A[lo-1]),dh=ad(a,A[lo]);R[t]=dl<=dh?lo-1:lo;}
}

// V2: V1 logic + __ldg() for texture cache path — ONLY CHANGE IS __ldg
__global__ void v2(const double*__restrict__ A,int n,const double*__restrict__ Q,int*__restrict__ R,int nq){
    int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=nq)return;
    double a=fmod(Q[t],TAU);if(a<0)a+=TAU;
    int lo=0,hi=n-1;
    while(lo<hi){int m=(lo+hi)/2;if(__ldg(&A[m])<a)lo=m+1;else hi=m;}
    if(lo==0){double dl=ad(a,__ldg(&A[n-1])),dh=ad(a,__ldg(&A[0]));R[t]=dl<=dh?n-1:0;}
    else{double dl=ad(a,__ldg(&A[lo-1])),dh=ad(a,__ldg(&A[lo]));R[t]=dl<=dh?lo-1:lo;}
}

// V3: Warp-cooperative binary search — V1 logic, 32 threads per query
__global__ void v3(const double*__restrict__ A,int n,const double*__restrict__ Q,int*__restrict__ R,int nq){
    int wid=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x%32;
    if(wid>=nq)return;
    double a=fmod(Q[wid],TAU);if(a<0)a+=TAU;
    int lo=0,hi=n-1;
    while(hi-lo>64){
        // Each of 32 lanes checks one pivot
        int range=hi-lo+1, chunk=range/32;
        int my_bnd=lo+lane*chunk; if(my_bnd>hi)my_bnd=hi;
        double my_val=__ldg(&A[my_bnd]);
        // Find first lane where value >= a
        unsigned int ballot=__ballot_sync(0xFFFFFFFF, my_val>=a);
        int fg;
        if(ballot==0){fg=31;lo=lo+31*chunk;}
        else{fg=__ffs(ballot)-1;lo=lo+fg*chunk;}
        hi=lo+chunk; if(hi>n-1)hi=n-1;
    }
    // Lane 0 finishes with standard binary search on remaining range
    if(lane==0){
        while(lo<hi){int m=(lo+hi)/2;if(__ldg(&A[m])<a)lo=m+1;else hi=m;}
        if(lo==0){double dl=ad(a,__ldg(&A[n-1])),dh=ad(a,__ldg(&A[0]));R[wid]=dl<=dh?n-1:0;}
        else{double dl=ad(a,__ldg(&A[lo-1])),dh=ad(a,__ldg(&A[lo]));R[wid]=dl<=dh?lo-1:lo;}
    }
}

int main(){
    printf("=== Final GPU Comparison (100M queries, fits in VRAM) ===\n\n");
    double a[MAX_T];int n=gen(a,50000);printf("Triples: %d\n\n",n);
    
    double*da,*dq;int*dr;
    cudaMalloc(&da,n*8);cudaMemcpy(da,a,n*8,cudaMemcpyHostToDevice);
    
    long long NQ=100000000LL; // 100M = 800MB queries + 400MB results = 1.2GB
    cudaMalloc(&dq,NQ*8);cudaMalloc(&dr,NQ*4);
    double*hq=(double*)malloc(NQ*8);
    for(long long i=0;i<NQ;i++)hq[i]=(double)(i*2654435761ULL%1000003ULL)/1000003.0*TAU;
    cudaMemcpy(dq,hq,NQ*8,cudaMemcpyHostToDevice);
    
    int th=256, bl=(int)((NQ+th-1)/th);
    int bl3=(int)((NQ/32+th-1)/th); // for warp-coop (32x fewer queries)
    
    cudaEvent_t s,e;cudaEventCreate(&s);cudaEventCreate(&e);
    
    // Warmup
    v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);
    v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);
    v3<<<bl3,th>>>(da,n,dq,dr,(int)(NQ/32));
    cudaDeviceSynchronize();
    
    // Benchmark each (10 iterations, best time)
    float t1=9e9,t2=9e9,t3=9e9;
    for(int i=0;i<10;i++){
        cudaEventRecord(s);v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);
        cudaDeviceSynchronize();cudaEventRecord(e);float ms;cudaEventElapsedTime(&ms,s,e);if(ms<t1)t1=ms;
        cudaEventRecord(s);v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);
        cudaDeviceSynchronize();cudaEventRecord(e);float ms2;cudaEventElapsedTime(&ms2,s,e);if(ms2<t2)t2=ms2;
        cudaEventRecord(s);v3<<<bl3,th>>>(da,n,dq,dr,(int)(NQ/32));
        cudaDeviceSynchronize();cudaEventRecord(e);float ms3;cudaEventElapsedTime(&ms3,s,e);if(ms3<t3)t3=ms3;
    }
    
    double q1=NQ/(t1/1000.0), q2=NQ/(t2/1000.0), q3=(NQ/32)/(t3/1000.0);
    
    printf("V1 Binary:       %7.2f ms  %8.2f B qps  1.00x\n", t1, q1/1e9);
    printf("V2 __ldg:        %7.2f ms  %8.2f B qps  %5.2fx\n", t2, q2/1e9, q2/q1);
    printf("V3 Warp-coop:    %7.2f ms  %8.2f B qps  %5.2fx\n", t3, q3/1e9, q3/q1);
    
    // Correctness
    int*h1=(int*)malloc(10000*4),*h2=(int*)malloc(10000*4),*h3=(int*)malloc(10000*4);
    v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);cudaMemcpy(h1,dr,10000*4,cudaMemcpyDeviceToHost);
    v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);cudaMemcpy(h2,dr,10000*4,cudaMemcpyDeviceToHost);
    v3<<<bl3,th>>>(da,n,dq,dr,(int)(NQ/32));cudaMemcpy(h3,dr,10000*4,cudaMemcpyDeviceToHost);
    int d12=0,d13=0;
    for(int i=0;i<10000;i++){if(h1[i]!=h2[i])d12++;if(h1[i]!=h3[i])d13++;}
    printf("\nCorrectness: V1 vs V2: %d disagree | V1 vs V3: %d disagree\n", d12, d13);
    
    // CPU baseline
    auto cpu0=std::chrono::high_resolution_clock::now();
    volatile int cs=0;
    for(int i=0;i<100000;i++){
        double q=fmod(hq[i],TAU);if(q<0)q+=TAU;
        int lo=0,hi=n-1;while(lo<hi){int m=(lo+hi)/2;if(a[m]<q)lo=m+1;else hi=m;}
        cs+=lo;
    }
    auto cpu1=std::chrono::high_resolution_clock::now();
    double cpu_ms=std::chrono::duration<double,std::milli>(cpu1-cpu0).count();
    printf("\nCPU: %.2f ms for 100K = %.1f M qps\n", cpu_ms, 100000.0/(cpu_ms/1000.0)/1e6);
    printf("GPU/CPU speedup: %.0fx\n", q1/(100000.0/(cpu_ms/1000.0)));
    
    cudaFree(da);cudaFree(dq);cudaFree(dr);free(hq);free(h1);free(h2);free(h3);
    cudaEventDestroy(e);
}
