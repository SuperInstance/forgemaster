// Eisenstein Kernel Benchmark — C
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

typedef long long i64;

static inline i64 eisenstein_norm(i64 a, i64 b) {
    return a * a - a * b + b * b;
}

typedef struct { i64 a; i64 b; } IntPair;
typedef struct { double x; double y; } DblPair;

IntPair eisenstein_snap(double x, double y) {
    double q = (2.0/3.0 * x - 1.0/3.0 * y);
    double r = (2.0/3.0 * y);
    double rq = round(q);
    double rr = round(r);
    double rs = round(-q - r);
    double diff = fabs(rq + rr + rs);
    if (diff == 2.0) {
        if (fabs(rq - q) > fabs(rr - r)) {
            rq = -rr - rs;
        } else {
            rr = -rq - rs;
        }
    }
    IntPair result = {(i64)rq, (i64)rr};
    return result;
}

double eisenstein_distance(double x, double y, i64 a, i64 b) {
    double px = a - 0.5 * b;
    double py = b * 0.8660254037844386; // sqrt(3)/2
    double dx = x - px;
    double dy = y - py;
    return sqrt(dx*dx + dy*dy);
}

int constraint_check(i64 a, i64 b, double radius) {
    return eisenstein_norm(a, b) <= (i64)(radius * radius);
}

#define N 10000000

int main() {
    srand(42);

    // Generate data
    i64 *norm_a = malloc(N * sizeof(i64));
    i64 *norm_b = malloc(N * sizeof(i64));
    double *snap_x = malloc(N * sizeof(double));
    double *snap_y = malloc(N * sizeof(double));
    i64 *con_a = malloc(N * sizeof(i64));
    i64 *con_b = malloc(N * sizeof(i64));
    double *con_r = malloc(N * sizeof(double));

    for (int i = 0; i < N; i++) {
        norm_a[i] = (rand() % 2001) - 1000;
        norm_b[i] = (rand() % 2001) - 1000;
        snap_x[i] = ((double)rand() / RAND_MAX) * 200.0 - 100.0;
        snap_y[i] = ((double)rand() / RAND_MAX) * 200.0 - 100.0;
        con_a[i] = (rand() % 201) - 100;
        con_b[i] = (rand() % 201) - 100;
        con_r[i] = ((double)rand() / RAND_MAX) * 49.0 + 1.0;
    }

    struct timespec t0, t1;
    i64 norm_sum = 0;
    IntPair snap_first = {0, 0};
    i64 con_pass = 0;

    // Benchmark norm
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int i = 0; i < N; i++) {
        norm_sum += eisenstein_norm(norm_a[i], norm_b[i]);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double norm_time = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;

    // Benchmark snap
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int i = 0; i < N; i++) {
        IntPair s = eisenstein_snap(snap_x[i], snap_y[i]);
        if (i == 0) snap_first = s;
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double snap_time = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;

    // Benchmark constraint
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int i = 0; i < N; i++) {
        con_pass += constraint_check(con_a[i], con_b[i], con_r[i]);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double con_time = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;

    printf("C Results (N=%d):\n", N);
    printf("  eisenstein_norm:  %.3fs  (sum=%lld)\n", norm_time, norm_sum);
    printf("  eisenstein_snap:  %.3fs  (first=(%lld,%lld))\n", snap_time, snap_first.a, snap_first.b);
    printf("  constraint_check: %.3fs  (pass=%lld)\n", con_time, con_pass);
    printf("  TOTAL: %.3fs\n", norm_time + snap_time + con_time);

    free(norm_a); free(norm_b); free(snap_x); free(snap_y);
    free(con_a); free(con_b); free(con_r);
    return 0;
}
