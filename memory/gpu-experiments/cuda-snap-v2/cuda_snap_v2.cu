/**
 * CUDA Pythagorean Snap Kernel v2 — Full Circle
 * Compiles with: nvcc -O3 -arch=sm_89 cuda_snap_v2.cu -o cuda_snap_v2
 * 
 * Tests: compile-only correctness check + host-side benchmark
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

typedef struct {
    int64_t x;
    int64_t y;
    uint64_t c;
} Triple;

typedef struct {
    double angle;
    int idx;
} AngleEntry;

static uint64_t gcd64(uint64_t a, uint64_t b) {
    while (b) { uint64_t t = b; b = a % b; a = t; }
    return a;
}

static double triple_angle(const Triple* t) {
    double a = atan2((double)t->y, (double)t->x);
    return a < 0 ? a + 2.0 * M_PI : a;
}

static double angle_diff(double a, double b) {
    double d = fabs(a - b);
    return fmin(d, 2.0 * M_PI - d);
}

static int cmp_angle(const void* a, const void* b) {
    double da = ((const AngleEntry*)a)->angle;
    double db = ((const AngleEntry*)b)->angle;
    return (da > db) - (da < db);
}

// Generate full-circle triples
static int generate_triples(Triple* out, int max_out, uint64_t max_c) {
    int count = 0;
    uint64_t max_m = (uint64_t)sqrt((double)max_c / 2.0) + 1;
    
    for (uint64_t m = 1; m <= max_m && count < max_out; m++) {
        uint64_t m2 = m * m;
        if (m2 * 2 > max_c * max_c) break;
        uint64_t max_n = m < ((uint64_t)sqrt((double)max_c - (double)m2)) ? 
                         m : (uint64_t)sqrt((double)max_c - (double)m2);
        for (uint64_t n = 1; n <= max_n && count < max_out; n++) {
            if ((m + n) % 2 == 1 && gcd64(m, n) == 1) {
                uint64_t a = m2 - n * n;
                uint64_t b = 2 * m * n;
                uint64_t c = m2 + n * n;
                if (c <= max_c) {
                    // All 8 octants
                    int64_t sa = (int64_t)a, sb = (int64_t)b;
                    Triple octants[8] = {
                        {sa, sb, c}, {sb, sa, c}, {-sa, sb, c}, {-sb, sa, c},
                        {-sa, -sb, c}, {-sb, -sa, c}, {sa, -sb, c}, {sb, -sa, c}
                    };
                    for (int o = 0; o < 8 && count < max_out; o++) {
                        out[count++] = octants[o];
                    }
                }
            }
        }
    }
    return count;
}

// Binary search snap
static int snap_binary(const AngleEntry* entries, int n, double theta) {
    theta = fmod(theta, 2.0 * M_PI);
    if (theta < 0) theta += 2.0 * M_PI;
    
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (entries[mid].angle < theta) lo = mid + 1;
        else hi = mid - 1;
    }
    
    if (lo == 0) return entries[0].idx;
    if (lo >= n) return entries[n-1].idx;
    
    double d_lo = angle_diff(entries[lo-1].angle, theta);
    double d_hi = angle_diff(entries[lo].angle, theta);
    return d_lo <= d_hi ? entries[lo-1].idx : entries[lo].idx;
}

// Brute force snap
static int snap_brute(const AngleEntry* entries, int n, double theta) {
    theta = fmod(theta, 2.0 * M_PI);
    if (theta < 0) theta += 2.0 * M_PI;
    
    int best = 0;
    double best_d = 1e30;
    for (int i = 0; i < n; i++) {
        double d = angle_diff(entries[i].angle, theta);
        if (d < best_d) { best_d = d; best = entries[i].idx; }
    }
    return best;
}

// LCG PRNG
static uint64_t lcg_state = 42;
static double lcg_rand() {
    lcg_state = lcg_state * 6364136223846793005ULL + 1;
    return (double)(lcg_state >> 11) / (double)(1ULL << 53);
}

int main() {
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  CUDA PYTHAGOREAN SNAP v2 — Full Circle Host Benchmark      ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    uint64_t max_c = 50000;
    int max_triples = 50000;
    
    // Allocate
    Triple* triples = (Triple*)malloc(max_triples * sizeof(Triple));
    AngleEntry* entries = (AngleEntry*)malloc(max_triples * sizeof(AngleEntry));
    
    // Generate
    clock_t t0 = clock();
    int n = generate_triples(triples, max_triples, max_c);
    
    // Compute angles and sort
    for (int i = 0; i < n; i++) {
        entries[i].angle = triple_angle(&triples[i]);
        entries[i].idx = i;
    }
    qsort(entries, n, sizeof(AngleEntry), cmp_angle);
    
    // Deduplicate
    int unique = 1;
    for (int i = 1; i < n; i++) {
        if (fabs(entries[i].angle - entries[unique-1].angle) > 1e-15) {
            entries[unique++] = entries[i];
        }
    }
    
    double gen_time = (double)(clock() - t0) / CLOCKS_PER_SEC;
    printf("  Generated %d triples (%d unique) in %.3fms\n", n, unique, gen_time * 1000);
    printf("  Angle range: [%.6f, %.6f] rad\n\n", entries[0].angle, entries[unique-1].angle);

    // Correctness check
    printf("  Correctness (10000 queries):\n");
    int mismatches = 0;
    lcg_state = 42;
    for (int i = 0; i < 10000; i++) {
        double theta = lcg_rand() * 2.0 * M_PI;
        int bs = snap_binary(entries, unique, theta);
        int bf = snap_brute(entries, unique, theta);
        if (bs != bf) mismatches++;
    }
    printf("    Binary-brute agreement: %d/10000 (%.1f%%)\n\n", 10000 - mismatches, (10000 - mismatches) / 100.0);

    // Benchmark
    int n_queries = 1000000;
    printf("  Performance (%d queries):\n", n_queries);
    
    // Binary search
    t0 = clock();
    uint64_t sum = 0;
    lcg_state = 42;
    for (int i = 0; i < n_queries; i++) {
        double theta = lcg_rand() * 2.0 * M_PI;
        int idx = snap_binary(entries, unique, theta);
        sum += triples[idx].c;
        // Prevent optimization
        if (sum == 999999999) printf("impossible");
    }
    double bs_time = (double)(clock() - t0) / CLOCKS_PER_SEC;
    double bs_qps = n_queries / bs_time;
    printf("    Binary search:   %.0f qps (%.2fms)\n", bs_qps, bs_time * 1000);
    
    // Brute force (10K sample)
    int bf_n = 10000;
    t0 = clock();
    sum = 0;
    lcg_state = 42;
    for (int i = 0; i < bf_n; i++) {
        double theta = lcg_rand() * 2.0 * M_PI;
        int idx = snap_brute(entries, unique, theta);
        sum += triples[idx].c;
        // Prevent optimization
        if (sum == 999999999) printf("impossible");
    }
    double bf_time = (double)(clock() - t0) / CLOCKS_PER_SEC;
    double bf_qps = bf_n / bf_time;
    printf("    Brute force 10K: %.0f qps (%.2fms)\n", bf_qps, bf_time * 1000);
    printf("    Speedup:         %.1fx\n\n", bs_qps / bf_qps);

    // Distribution analysis
    printf("  Distribution (18 bins × 20°):\n");
    int bins[18] = {0};
    double mean_b = unique / 18.0;
    for (int i = 0; i < unique; i++) {
        int b = (int)((entries[i].angle / (2.0 * M_PI)) * 18) % 18;
        bins[b]++;
    }
    double var = 0;
    for (int i = 0; i < 18; i++) var += (bins[i] - mean_b) * (bins[i] - mean_b);
    var /= 18.0;
    double cv = sqrt(var) / mean_b;
    printf("    CV: %.3f (%s)\n\n", cv, cv > 0.3 ? "non-uniform" : "roughly uniform");

    for (int i = 0; i < 18; i++) {
        int bar = (int)(bins[i] / mean_b * 12);
        printf("    %3d°-%3d° │", i * 20, (i + 1) * 20);
        for (int j = 0; j < bar; j++) printf("█");
        printf("│ %d\n", bins[i]);
    }

    printf("\n════════════════════════════════════════════════════════════\n");
    printf("  %d triples | %.0fx speedup | CV=%.2f | mismatches=%d\n",
           unique, bs_qps / bf_qps, cv, mismatches);
    printf("════════════════════════════════════════════════════════════\n");

    free(triples);
    free(entries);
    return mismatches > 0 ? 1 : 0;
}
