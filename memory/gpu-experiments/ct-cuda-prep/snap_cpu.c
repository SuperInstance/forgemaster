// CPU reference implementation — must produce identical results to snap.cu
// This is the verification target for the CUDA kernel

#include <math.h>
#include <stdint.h>
#include <stdlib.h>

#define TAU 6.283185307179586

static double angular_dist(double a, double b) {
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

typedef struct { double angle; int index; } AnglePair;

static int cmp_angle(const void* a, const void* b) {
    double da = ((const AnglePair*)a)->angle;
    double db = ((const AnglePair*)b)->angle;
    return (da > db) - (da < db);
}

int snap_binary_cpu(const double* angles, const int* indices, int n, double theta) {
    if (n == 0) return 0;
    double a = fmod(theta, TAU);
    if (a < 0) a += TAU;

    int lo = 0, hi = n - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (angles[mid] < a) lo = mid + 1;
        else hi = mid;
    }

    if (lo == 0) {
        double d_last = angular_dist(a, angles[n - 1]);
        double d_first = angular_dist(a, angles[0]);
        return d_last <= d_first ? indices[n - 1] : indices[0];
    }

    double d_lo = angular_dist(a, angles[lo - 1]);
    double d_hi = angular_dist(a, angles[lo]);
    return d_lo <= d_hi ? indices[lo - 1] : indices[lo];
}
