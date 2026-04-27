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
    double*da,*dq;int*dr;
    cudaMalloc(&da,n*8);cudaMemcpy(da,a,n*8,cudaMemcpyHostToDevice);
    
    int th=256;
    cudaEvent_t s,e;cudaEventCreate(&s);cudaEventCreate(&e);
    
    // Test at multiple scales to find measurable time for V2
    long long scales[] = {100000000LL, 500000000LL, 1000000000LL, 2000000000LL, 5000000000LL};
    char* labels[] = {"100M", "500M", "1B", "2B", "5B"};
    
    printf("Triples: %d | RTX 4050 Laptop GPU\n\n", n);
    printf("%-6s  %10s  %12s  %12s\n", "Scale", "V1 (ms)", "V2 (ms)", "V2 qps");
    printf("------  ----------  ------------  ------------\n");
    
    for(int si=0;si<5;si++){
        long long NQ=scales[si];
        // Check if fits in VRAM (need NQ*12 bytes)
        if(NQ*12LL > 5500000000LL){printf("%-6s  (exceeds VRAM)\n",labels[si]);continue;}
        
        cudaMalloc(&dq,NQ*8);cudaMalloc(&dr,NQ*4);
        double*hq=(double*)malloc(NQ*8);
        for(long long i=0;i<NQ;i++)hq[i]=(double)(i*2654435761ULL%1000003ULL)/1000003.0*TAU;
        cudaMemcpy(dq,hq,NQ*8,cudaMemcpyHostToDevice);
        int bl=(int)((NQ+th-1)/th);
        
        // Warmup
        v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);cudaDeviceSynchronize();
        
        // V1
        float t1=9e9;for(int i=0;i<5;i++){
            cudaEventRecord(s);v1<<<bl,th>>>(da,n,dq,dr,(int)NQ);
            cudaDeviceSynchronize();cudaEventRecord(e);float ms;cudaEventElapsedTime(&ms,s,e);if(ms<t1)t1=ms;
        }
        
        // V2
        float t2=9e9;for(int i=0;i<5;i++){
            cudaEventRecord(s);v2<<<bl,th>>>(da,n,dq,dr,(int)NQ);
            cudaDeviceSynchronize();cudaEventRecord(e);float ms;cudaEventElapsedTime(&ms,s,e);if(ms<t2)t2=ms;
        }
        
        double q2 = (t2>0.001) ? NQ/(t2/1000.0) : 0;
        printf("%-6s  %10.2f  %12.2f  ", labels[si], t1, t2);
        if(q2>0) printf("%10.1f B\n", q2/1e9); else printf("  too fast\n");
        
        cudaFree(dq);cudaFree(dr);free(hq);
    }
    
    cudaFree(da);cudaEventDestroy(s);cudaEventDestroy(e);
}
