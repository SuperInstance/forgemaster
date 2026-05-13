#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <stdint.h>

#define COVERING_RADIUS 0.5773502691896258  /* 1/sqrt(3) */
#define N_POINTS 1000000

/* 9-candidate search: da = [-1,0,1], db = [-1,0,1] */
static double snap_9candidates(double x, double y,
                               int *out_a, int *out_b) {
    double best_a = round(x - y * (-0.5) / (0.8660254037844386));
    double best_b = round(y / 0.8660254037844386);
    double best_err = 1e30;

    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            double ca = best_a + da;
            double cb = best_b + db;
            double cx = ca + cb * (-0.5);
            double cy = cb * 0.8660254037844386;
            double dx = x - cx;
            double dy = y - cy;
            double err = sqrt(dx*dx + dy*dy);
            if (err < best_err) {
                best_err = err;
                *out_a = (int)ca;
                *out_b = (int)cb;
            }
        }
    }
    return best_err;
}

/* N-candidate search: use first n values from the 9-candidate grid */
static double snap_ncandidates(double x, double y, int n,
                               int *out_a, int *out_b) {
    double a0 = round(x - y * (-0.5) / 0.8660254037844386);
    double b0 = round(y / 0.8660254037844386);
    double best_err = 1e30;
    int best_a = (int)a0, best_b = (int)b0;

    int das[] = {-1, -1, -1, 0, 0, 0, 1, 1, 1};
    int dbs[] = {-1, 0, 1, -1, 0, 1, -1, 0, 1};

    for (int i = 0; i < n; i++) {
        double ca = a0 + das[i];
        double cb = b0 + dbs[i];
        double cx = ca + cb * (-0.5);
        double cy = cb * 0.8660254037844386;
        double dx = x - cx;
        double dy = y - cy;
        double err = sqrt(dx*dx + dy*dy);
        if (err < best_err) {
            best_err = err;
            best_a = (int)ca;
            best_b = (int)cb;
        }
    }
    *out_a = best_a;
    *out_b = best_b;
    return best_err;
}

int main(int argc, char **argv) {
    int n = argc > 1 ? atoi(argv[1]) : N_POINTS;
    if (n < 1) n = 1000;

    srand(42);

    /* Allocate points */
    double *xs = malloc(n * sizeof(double));
    double *ys = malloc(n * sizeof(double));
    for (int i = 0; i < n; i++) {
        xs[i] = ((double)rand() / RAND_MAX) * 10.0 - 5.0;
        ys[i] = ((double)rand() / RAND_MAX) * 10.0 - 5.0;
    }

    printf("=== Voronoi Candidate Count Experiment ===\n");
    printf("Points: %d\n\n", n);

    /* Test candidate counts from 2 to 9 */
    for (int k = 2; k <= 9; k++) {
        int violations = 0;
        double max_err = 0.0;
        double total_time = 0.0;
        int mismatches = 0;

        clock_t start = clock();
        for (int i = 0; i < n; i++) {
            int a, b;
            double err = snap_ncandidates(xs[i], ys[i], k, &a, &b);
            if (err > COVERING_RADIUS + 0.001) violations++;
            if (err > max_err) max_err = err;
            total_time += err; /* synthetic load to prevent optimization */
        }
        clock_t end = clock();
        double elapsed = (double)(end - start) / CLOCKS_PER_SEC;

        /* Compare against 9-candidate reference */
        for (int i = 0; i < n; i++) {
            int a9, b9, ak, bk;
            double e9 = snap_ncandidates(xs[i], ys[i], 9, &a9, &b9);
            double ek = snap_ncandidates(xs[i], ys[i], k, &ak, &bk);
            if (a9 != ak || b9 != bk) mismatches++;
        }

        printf("  %d candidates: max_err=%.6f violations=%d (%.2f%%) mismatches=%d (%.2f%%) time=%.3fs\n",
               k, max_err, violations, 100.0*violations/n,
               mismatches, 100.0*mismatches/n, elapsed);
    }

    free(xs);
    free(ys);
    return 0;
}
