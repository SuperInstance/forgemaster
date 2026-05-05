#include <stdio.h>
#include <math.h>
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

__global__ void v1(const double*__restrict__ A,int n,const double*__restrict__ Q,int*__restrict__ R,int nq){
    int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=nq)return;
    double a=fmod(Q[t],TAU);if(a<0)a+=TAU;
    int lo=0,hi=n-1;
    while(lo<hi){int m=(lo+hi)/2;if(A[m]<a)lo=m+1;else hi=m;}
    if(lo==0){double dl=ad(a,A[n-1]),dh=ad(a,A[0]);R[t]=dl<=dh?n-1:0;}
    else{double dl=ad(a,A[lo-1]),dh=ad(a,A[lo]);R[t]=dl<=dh?lo-1:lo;}
}

__global__ void v2(const double*__restrict__ A,int n,const double*__restrict__ Q,int*__restrict__ R,int nq){
    int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=nq)return;
    double a=fmod(Q[t],TAU);if(a<0)a+=TAU;
    int lo=0,hi=n-1;
    while(lo<hi){int m=(lo+hi)/2;if(__ldg(&A[m])<a)lo=m+1;else hi=m;}
    if(lo==0){double dl=ad(a,__ldg(&A[n-1])),dh=ad(a,__ldg(&A[0]));R[t]=dl<=dh?n-1:0;}
    else{double dl=ad(a,__ldg(&A[lo-1])),dh=ad(a,__ldg(&A[lo]));R[t]=dl<=dh?lo-1:lo;}
}

int main(){
    double a[MAX_T];int n=gen(a,50000);
    double*da,*dq;int*dr,*hr;
    cudaMalloc(&da,n*8);cudaMemcpy(da,a,n*8,cudaMemcpyHostToDevice);
    
    long long NQ=100000000LL;
    cudaMalloc(&dq,NQ*8);cudaMalloc(&dr,NQ*4);
    hr=(int*)malloc(NQ*4);
    double*hq=(double*)malloc(NQ*8);
    for(long long i=0;i<NQ;i++)hq[i]=(double)(i*2654435761ULL%1000003ULL)/1000003.0*TAU;
    cudaMemcpy(dq,hq,NQ*8,cudaMemcpyHostToDevice);
    int th=256,bl=(int)((NQ+th-1)/th);
    
    printf("=== Precise measurement with cudaMemcpy forced ===\n");
    printf("Triples: %d, Queries: 100M\n\n", n);
    
    // V1: 10 runs with cudaMemcpy to force completion
    float t1_min=9e9;
    for(int run=0;run<10;run++){
        cudaEvent_t s,e;cudaEventCreate(&s);cudaEventCreate(&e);
        cudaEventRecord(s);
        v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);
        cudaMemcpy(hr,dr,NQ*4,cudaMemcpyDeviceToHost);
        cudaEventRecord(e);cudaEventSynchronize(e);
        float ms;cudaEventElapsedTime(&ms,s,e);
        if(ms<t1_min)t1_min=ms;
        cudaEventDestroy(s);cudaEventDestroy(e);
    }
    
    // V2: 10 runs
    float t2_min=9e9;
    for(int run=0;run<10;run++){
        cudaEvent_t s,e;cudaEventCreate(&s);cudaEventCreate(&e);
        cudaEventRecord(s);
        v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);
        cudaMemcpy(hr,dr,NQ*4,cudaMemcpyDeviceToHost);
        cudaEventRecord(e);cudaEventSynchronize(e);
        float ms;cudaEventElapsedTime(&ms,s,e);
        if(ms<t2_min)t2_min=ms;
        cudaEventDestroy(s);cudaEventDestroy(e);
    }
    
    // Verify correctness one more time
    int*h1=(int*)malloc(10000*4),*h2=(int*)malloc(10000*4);
    v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);cudaMemcpy(h1,dr,10000*4,cudaMemcpyDeviceToHost);
    v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);cudaMemcpy(h2,dr,10000*4,cudaMemcpyDeviceToHost);
    int dg=0;for(int i=0;i<10000;i++)if(h1[i]!=h2[i])dg++;
    
    printf("V1 Binary:  %7.2f ms  %8.2f B qps\n", t1_min, NQ/(t1_min/1000.0)/1e9);
    printf("V2 __ldg:   %7.2f ms  %8.2f B qps  (%.1fx)\n", t2_min, NQ/(t2_min/1000.0)/1e9, t1_min/t2_min);
    printf("Correctness: %d/10000 disagree\n", dg);
    
    cudaFree(da);cudaFree(dq);cudaFree(dr);free(hr);free(hq);free(h1);free(h2);
}
