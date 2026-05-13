/*
 * bench_threads.c
 * Multi-threaded scaling benchmarks for constraint operations.
 * Tests: Eisenstein snap, 3-tier constraint check, holonomy batch, cyclotomic projection.
 *
 * Compile: gcc -O3 -march=native -lpthread -lm -o bench_threads bench_threads.c
 * Run:     ./bench_threads
 *
 * AMD Ryzen AI 9 HX 370 / 24 logical cores / AVX-512
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <time.h>
#include <unistd.h>
#include <complex.h>
#include <immintrin.h>
#include <stdio.h>
#define FLUSH() do { fflush(stdout); fflush(stderr); } while(0)

/* ============================================================
 * Configuration
 * ============================================================ */
#define MAX_THREADS       24
#define NUM_ITERATIONS    3
#define WARMUP_ITERATIONS 2

/* Benchmark sizes */
#define EISENSTEIN_POINTS    5000000UL   /* 5M points */
#define CONSTRAINT_LUT_QUERIES 5000000UL /* 5M LUT queries — O(1) per query */
#define CONSTRAINT_FULL_QUERIES 200000UL /* 200K full queries — O(K) per query */
#define CONSTRAINT_COUNT     10000       /* 10K constraints */
#define HOLONOMY_CYCLES      500000UL    /* 500K cycles */
#define HOLONOMY_CYCLE_LEN   10          /* length 10 each */
#define CYCLOTOMIC_POINTS    250000UL    /* 250K points (O(N*315) inner loop = 78.75M checks) */

/* Thread counts to test */
static const int thread_counts[] = {1, 2, 4, 8, 12, 16, 24};
static const int num_thread_configs = 7;

/* ============================================================
 * Timing helpers
 * ============================================================ */
static double timespec_to_sec(struct timespec *ts)
{
    return (double)ts->tv_sec + (double)ts->tv_nsec * 1e-9;
}

static inline double get_time(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return timespec_to_sec(&ts);
}

/* Pin current thread to CPU core */
static void pin_thread(int core_id)
{
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
}

/* ============================================================
 * Data structures
 * ============================================================ */

/* Complex number in Eisenstein integers: a + b*ω where ω = e^(2πi/3) */
typedef struct {
    int a; /* real part coefficient */
    int b; /* ω coefficient */
} eisenstein_t;

/* 3-tier constraint: LUT, linear, full checks */
typedef struct {
    int tier;          /* 0=LUT, 1=linear, 2=full */
    int64_t key;       /* For LUT lookup */
    double coeff_a;    /* For linear: ax + b */
    double coeff_b;
    double threshold;
    double complex z_center; /* For full: |z - center| < threshold */
    double radius_sq;
} constraint_t;

/* Holonomy cycle */
typedef struct {
    double complex elements[HOLONOMY_CYCLE_LEN];
    int len;
} holonomy_cycle_t;

/* Work-sharing context for benchmark functions */
typedef struct {
    int thread_id;
    int num_threads;
    int first_core;
    uint64_t work_start;
    uint64_t work_end;
    double result;
    uint64_t count;
    void *shared_data;
} work_ctx_t;

/* ============================================================
 * Benchmark 1a: Eisenstein Snap Scaling
 * Tests nearest-Eisenstein-integer snapping throughput.
 * For each point (real), find closest point in ℤ[ω].
 * ============================================================ */

/* Pre-computed Eisenstein lattice: 3 directions */
static const double eisenstein_vecs[3][2] = {
    {1.0, 0.0},
    {-0.5,  0.8660254037844386},  /* ω */
    {-0.5, -0.8660254037844386}   /* ω² */
};

/* Snap a point to nearest Eisenstein integer */
static void eisenstein_snap(double x, double y, int *a_out, int *b_out)
{
    /* Transform to Eisenstein coordinates */
    /* (a,b) such that point = a*(1,0) + b*(-0.5, sqrt(3)/2) */
    /* x = a - 0.5*b, y = (sqrt(3)/2)*b */
    double b = y / 0.8660254037844386;
    double a = x + 0.5 * b;

    /* Round to nearest integers */
    int ai = (int)round(a);
    int bi = (int)round(b);

    /* Check nearest neighbors (3 directions) for refinement */
    double best_dist = 1e30;
    int best_a = ai, best_b = bi;

    for (int da = -2; da <= 2; da++) {
        for (int db = -2; db <= 2; db++) {
            int ac = ai + da;
            int bc = bi + db;
            double px = ac - 0.5 * bc;
            double py = 0.8660254037844386 * bc;
            double dx = px - x;
            double dy = py - y;
            double d = dx * dx + dy * dy;
            if (d < best_dist) {
                best_dist = d;
                best_a = ac;
                best_b = bc;
            }
        }
    }

    *a_out = best_a;
    *b_out = best_b;
}

typedef struct {
    double *xs;
    double *ys;
    int *results_a;
    int *results_b;
    uint64_t n;
} eisenstein_data_t;

static void *bench_eisenstein_worker(void *arg)
{
    work_ctx_t *ctx = (work_ctx_t *)arg;
    eisenstein_data_t *data = (eisenstein_data_t *)ctx->shared_data;
    pin_thread(ctx->first_core + ctx->thread_id);

    for (uint64_t i = ctx->work_start; i < ctx->work_end; i++) {
        eisenstein_snap(data->xs[i], data->ys[i],
                        &data->results_a[i], &data->results_b[i]);
    }
    return NULL;
}

static double run_eisenstein_bench(int num_threads, eisenstein_data_t *data)
{
    pthread_t threads[MAX_THREADS];
    work_ctx_t ctxs[MAX_THREADS];
    uint64_t chunk = data->n / num_threads;

    double t0 = get_time();

    for (int t = 0; t < num_threads; t++) {
        ctxs[t].thread_id = t;
        ctxs[t].num_threads = num_threads;
        ctxs[t].first_core = 0; /* Use all cores */
        ctxs[t].work_start = t * chunk;
        ctxs[t].work_end = (t == num_threads - 1) ? data->n : (t + 1) * chunk;
        ctxs[t].shared_data = data;
        pthread_create(&threads[t], NULL, bench_eisenstein_worker, &ctxs[t]);
    }

    for (int t = 0; t < num_threads; t++) {
        pthread_join(threads[t], NULL);
    }

    double t1 = get_time();
    double elapsed = t1 - t0;
    return (double)data->n / elapsed / 1e6; /* Mops/sec */
}

/* ============================================================
 * Benchmark 1b: 3-Tier Constraint Check Scaling
 * LUT tier: O(1) per query — hash table for exact keys
 * Linear tier: O(n) per constraint — ax + b threshold
 * Full tier: O(n) per constraint — distance check
 * ============================================================ */

typedef struct {
    int64_t *query_keys;
    constraint_t *constraints;
    int num_constraints;
    uint64_t num_queries;
    uint64_t *hit_counts;
    double *dist_sums;
    int is_lut;
} constraint_data_t;

static void *bench_constraint_worker(void *arg)
{
    work_ctx_t *ctx = (work_ctx_t *)arg;
    constraint_data_t *data = (constraint_data_t *)ctx->shared_data;
    pin_thread(ctx->first_core + ctx->thread_id);

    uint64_t local_hits = 0;
    double local_dist = 0.0;

    if (data->is_lut) {
        /* LUT: O(1) ideal — just hash lookup simulation */
        for (uint64_t i = ctx->work_start; i < ctx->work_end; i++) {
            int64_t key = data->query_keys[i];
            /* Simulate LUT: simple hash + linear probe, no contention */
            uint64_t slot = (uint64_t)key % data->num_constraints;
            if (data->constraints[slot].key == key) {
                local_hits++;
            }
        }
    } else {
        /* Linear or full: check all constraints per query */
        for (uint64_t i = ctx->work_start; i < ctx->work_end; i++) {
            int64_t key = data->query_keys[i];
            for (int c = 0; c < data->num_constraints; c++) {
                if (data->constraints[c].tier == 1) {
                    /* Linear: ax + b threshold */
                    double val = data->constraints[c].coeff_a * (double)key +
                                 data->constraints[c].coeff_b;
                    if (fabs(val) < data->constraints[c].threshold) {
                        local_hits++;
                    }
                } else {
                    /* Full: use key as a coordinate component */
                    double complex z = (double)key + 0.0 * I;
                    double complex dz = z - data->constraints[c].z_center;
                    double dist_sq = creal(dz) * creal(dz) + cimag(dz) * cimag(dz);
                    if (dist_sq < data->constraints[c].radius_sq) {
                        local_hits++;
                        local_dist += sqrt(dist_sq);
                    }
                }
            }
        }
    }

    ctx->result = (double)local_hits;
    ctx->count = local_hits;
    return NULL;
}

static constraint_data_t *prepare_constraint_data(int is_lut)
{
    constraint_data_t *data = malloc(sizeof(constraint_data_t));
    data->num_queries = is_lut ? CONSTRAINT_LUT_QUERIES : CONSTRAINT_FULL_QUERIES;
    data->num_constraints = CONSTRAINT_COUNT;
    data->is_lut = is_lut;

    data->query_keys = malloc(data->num_queries * sizeof(int64_t));
    data->constraints = malloc(data->num_constraints * sizeof(constraint_t));
    data->hit_counts = calloc(data->num_constraints, sizeof(uint64_t));
    data->dist_sums = calloc(data->num_constraints, sizeof(double));

    /* Initialize queries */
    srand(42);
    for (uint64_t i = 0; i < data->num_queries; i++) {
        data->query_keys[i] = (int64_t)(rand() % 1000000);
    }

    /* Initialize constraints */
    for (int c = 0; c < data->num_constraints; c++) {
        data->constraints[c].tier = (c < 5000) ? 0 : ((c < 8000) ? 1 : 2);
        data->constraints[c].key = (int64_t)(rand() % 1000000);
        data->constraints[c].coeff_a = (double)(rand() % 100) / 100.0;
        data->constraints[c].coeff_b = (double)(rand() % 1000) / 100.0;
        data->constraints[c].threshold = 10.0;
        data->constraints[c].z_center = (double)(rand() % 1000) + 0.0 * I;
        data->constraints[c].radius_sq = 50.0;
    }

    return data;
}

static double run_constraint_bench(int num_threads, constraint_data_t *data)
{
    pthread_t threads[MAX_THREADS];
    work_ctx_t ctxs[MAX_THREADS];
    uint64_t chunk = data->num_queries / num_threads;

    double t0 = get_time();

    for (int t = 0; t < num_threads; t++) {
        ctxs[t].thread_id = t;
        ctxs[t].num_threads = num_threads;
        ctxs[t].first_core = 0;
        ctxs[t].work_start = t * chunk;
        ctxs[t].work_end = (t == num_threads - 1) ? data->num_queries : (t + 1) * chunk;
        ctxs[t].shared_data = data;
        ctxs[t].result = 0.0;
        ctxs[t].count = 0;
        pthread_create(&threads[t], NULL, bench_constraint_worker, &ctxs[t]);
    }

    for (int t = 0; t < num_threads; t++) {
        pthread_join(threads[t], NULL);
    }

    double t1 = get_time();
    double elapsed = t1 - t0;
    /* Throughput: queries per second */
    return (double)data->num_queries / elapsed / 1e6;
}

/* ============================================================
 * Benchmark 1c: Holonomy Batch Scaling
 * Each thread processes independent cycles (embarrassingly parallel).
 * Holonomy: product of elements in a cycle = e^(i*theta) — rotation group
 * ============================================================ */

typedef struct {
    holonomy_cycle_t *cycles;
    uint64_t num_cycles;
    double complex *results;
} holonomy_data_t;

static void *bench_holonomy_worker(void *arg)
{
    work_ctx_t *ctx = (work_ctx_t *)arg;
    holonomy_data_t *data = (holonomy_data_t *)ctx->shared_data;
    pin_thread(ctx->first_core + ctx->thread_id);

    for (uint64_t c = ctx->work_start; c < ctx->work_end; c++) {
        double complex prod = 1.0 + 0.0 * I;
        for (int i = 0; i < data->cycles[c].len; i++) {
            prod *= data->cycles[c].elements[i];
        }
        data->results[c] = prod;
    }

    return NULL;
}

static double run_holonomy_bench(int num_threads, holonomy_data_t *data)
{
    pthread_t threads[MAX_THREADS];
    work_ctx_t ctxs[MAX_THREADS];
    uint64_t chunk = data->num_cycles / num_threads;

    double t0 = get_time();

    for (int t = 0; t < num_threads; t++) {
        ctxs[t].thread_id = t;
        ctxs[t].num_threads = num_threads;
        ctxs[t].first_core = 0;
        ctxs[t].work_start = t * chunk;
        ctxs[t].work_end = (t == num_threads - 1) ? data->num_cycles : (t + 1) * chunk;
        ctxs[t].shared_data = data;
        pthread_create(&threads[t], NULL, bench_holonomy_worker, &ctxs[t]);
    }

    for (int t = 0; t < num_threads; t++) {
        pthread_join(threads[t], NULL);
    }

    double t1 = get_time();
    double elapsed = t1 - t0;
    return (double)data->num_cycles / elapsed / 1e6; /* M cycles/sec */
}

/* ============================================================
 * Benchmark 1d: Cyclotomic Field Projection
 * Project points onto Q(ζ₁₅) — 15th roots of unity.
 * Compute nearest point in cyclotomic field.
 * CPU-bound: complex multiplications + comparisons.
 * ============================================================ */

/* ζ₁₅ = cos(2π/15) + i*sin(2π/15) */
#define ZETA15_K(k) (cos(2.0 * M_PI * (k) / 15.0) + sin(2.0 * M_PI * (k) / 15.0) * I)

typedef struct {
    double *xs;
    double *ys;
    double complex *projections;
    uint64_t n;
} cyclotomic_data_t;

static void *bench_cyclotomic_worker(void *arg)
{
    work_ctx_t *ctx = (work_ctx_t *)arg;
    cyclotomic_data_t *data = (cyclotomic_data_t *)ctx->shared_data;
    pin_thread(ctx->first_core + ctx->thread_id);

    /* Pre-compute ζ₁₅^k real/imag parts */
    double zeta_re[15], zeta_im[15];
    for (int k = 0; k < 15; k++) {
        double theta = 2.0 * M_PI * k / 15.0;
        zeta_re[k] = cos(theta);
        zeta_im[k] = sin(theta);
    }

    for (uint64_t i = ctx->work_start; i < ctx->work_end; i++) {
        double zx = data->xs[i];
        double zy = data->ys[i];

        /* Find nearest projection onto cyclotomic field */
        double best_dist = 1e30;
        double best_px = 0, best_py = 0;

        for (int k = 0; k < 15; k++) {
            double zkr = zeta_re[k];
            double zki = zeta_im[k];
            for (int s = -10; s <= 10; s++) {
                double cx = s * zkr;
                double cy = s * zki;
                double dx = zx - cx;
                double dy = zy - cy;
                double dist = dx*dx + dy*dy;
                if (dist < best_dist) {
                    best_dist = dist;
                    best_px = cx;
                    best_py = cy;
                }
            }
        }

        data->projections[i] = best_px + best_py * I;
    }

    return NULL;
}

static double run_cyclotomic_bench(int num_threads, cyclotomic_data_t *data)
{
    pthread_t threads[MAX_THREADS];
    work_ctx_t ctxs[MAX_THREADS];
    uint64_t chunk = data->n / num_threads;

    double t0 = get_time();

    for (int t = 0; t < num_threads; t++) {
        ctxs[t].thread_id = t;
        ctxs[t].num_threads = num_threads;
        ctxs[t].first_core = 0;
        ctxs[t].work_start = t * chunk;
        ctxs[t].work_end = (t == num_threads - 1) ? data->n : (t + 1) * chunk;
        ctxs[t].shared_data = data;
        pthread_create(&threads[t], NULL, bench_cyclotomic_worker, &ctxs[t]);
    }

    for (int t = 0; t < num_threads; t++) {
        pthread_join(threads[t], NULL);
    }

    double t1 = get_time();
    double elapsed = t1 - t0;
    return (double)data->n / elapsed / 1e6; /* Mpoints/sec */
}

/* ============================================================
 * Benchmark runner
 * ============================================================ */
typedef struct {
    const char *name;
    double (*bench_fn)(int num_threads, void *data);
    void *data;
    int requires_prep;
    void *(*prep_fn)(void);
} bench_def_t;

/* Run a single benchmark at given thread count, return median of iterations */
static double bench_median(int num_threads, double (*bench_fn)(int, void*), void *data)
{
    double times[NUM_ITERATIONS];

    /* Warmup */
    for (int w = 0; w < WARMUP_ITERATIONS; w++) {
        bench_fn(num_threads, data);
    }

    for (int i = 0; i < NUM_ITERATIONS; i++) {
        times[i] = bench_fn(num_threads, data);
    }

    /* Sort for median */
    for (int i = 0; i < NUM_ITERATIONS - 1; i++) {
        for (int j = i + 1; j < NUM_ITERATIONS; j++) {
            if (times[i] > times[j]) {
                double tmp = times[i];
                times[i] = times[j];
                times[j] = tmp;
            }
        }
    }

    return times[NUM_ITERATIONS / 2];
}

/* Print results row */
static void print_bench_line(const char *op, int threads,
                             double throughput, double speedup, double efficiency)
{
    printf("%-30s | %3d | %12.4f | %8.3f | %8.3f\n",
           op, threads, throughput, speedup, efficiency);
}

/* ============================================================
 * Main
 * ============================================================ */
int main(void)
{
    /* Unbuffer stdout for real-time output visibility */
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);
    printf("============================================================\n");
    printf(" Multi-Threaded Constraint Operation Benchmark\n");
    printf(" Machine: AMD Ryzen AI 9 HX 370 / 24 cores / AVX-512\n");
    printf("============================================================\n\n");

    /* System info */
    printf("Logical CPUs: %d\n\n", sysconf(_SC_NPROCESSORS_ONLN));

    /* ======== Benchmark 1a: Eisenstein Snap ======== */
    printf("--- Benchmark 1a: Eisenstein Snap Scaling (%lu points) ---\n",
           (unsigned long)EISENSTEIN_POINTS);

    eisenstein_data_t es_data;
    es_data.n = EISENSTEIN_POINTS;
    es_data.xs = malloc(EISENSTEIN_POINTS * sizeof(double));
    es_data.ys = malloc(EISENSTEIN_POINTS * sizeof(double));
    es_data.results_a = malloc(EISENSTEIN_POINTS * sizeof(int));
    es_data.results_b = malloc(EISENSTEIN_POINTS * sizeof(int));

    srand(12345);
    for (uint64_t i = 0; i < EISENSTEIN_POINTS; i++) {
        es_data.xs[i] = ((double)rand() / RAND_MAX) * 1000.0;
        es_data.ys[i] = ((double)rand() / RAND_MAX) * 1000.0;
    }

    printf("%-30s | %3s | %12s | %8s | %8s\n",
           "Operation", "Thr", "Throughput", "Speedup", "Efficiency");
    printf("------------------------------------------------------------------\n");

    double es_single = 0.0;
    for (int i = 0; i < num_thread_configs; i++) {
        int t = thread_counts[i];
        double tp = bench_median(t, (double(*)(int,void*))run_eisenstein_bench, &es_data);
        double speedup = (i == 0) ? 1.0 : tp / es_single;
        double efficiency = speedup / t;
        if (i == 0) es_single = tp;
        print_bench_line("Eisenstein Snap", t, tp, speedup, efficiency);
    }
    printf("\n");

    /* ======== Benchmark 1b: 3-Tier Constraint Check ======== */
    printf("--- Benchmark 1b: 3-Tier Constraint Check (%lu queries, %d constraints) ---\n",
           (unsigned long)CONSTRAINT_LUT_QUERIES, CONSTRAINT_COUNT);

    /* LUT tier — should show NO contention */
    constraint_data_t *const_data_lut = prepare_constraint_data(1);
    printf("\n  [LUT tier — O(1) per query, contention-free]:\n");
    printf("%-30s | %3s | %12s | %8s | %8s\n",
           "Operation", "Thr", "Throughput", "Speedup", "Efficiency");
    printf("------------------------------------------------------------------\n");

    double const_single_lut = 0.0;
    for (int i = 0; i < num_thread_configs; i++) {
        int t = thread_counts[i];
        double tp = bench_median(t, (double(*)(int,void*))run_constraint_bench, const_data_lut);
        double speedup = (i == 0) ? 1.0 : tp / const_single_lut;
        double efficiency = speedup / t;
        if (i == 0) const_single_lut = tp;
        print_bench_line("Constraint LUT", t, tp, speedup, efficiency);
    }

    /* Linear + Full tier */
    constraint_data_t *const_data_full = prepare_constraint_data(0);
    printf("\n  [Linear + Full tier — O(K) per query, compute-bound]:\n");
    printf("%-30s | %3s | %12s | %8s | %8s\n",
           "Operation", "Thr", "Throughput", "Speedup", "Efficiency");
    printf("------------------------------------------------------------------\n");

    double const_single_full = 0.0;
    for (int i = 0; i < num_thread_configs; i++) {
        int t = thread_counts[i];
        double tp = bench_median(t, (double(*)(int,void*))run_constraint_bench, const_data_full);
        double speedup = (i == 0) ? 1.0 : tp / const_single_full;
        double efficiency = speedup / t;
        if (i == 0) const_single_full = tp;
        print_bench_line("Constraint Linear+Full", t, tp, speedup, efficiency);
    }

    free(const_data_lut->query_keys);
    free(const_data_lut->constraints);
    free(const_data_lut->hit_counts);
    free(const_data_lut->dist_sums);
    free(const_data_lut);
    free(const_data_full->query_keys);
    free(const_data_full->constraints);
    free(const_data_full->hit_counts);
    free(const_data_full->dist_sums);
    free(const_data_full);
    printf("\n");

    /* ======== Benchmark 1c: Holonomy Batch ======== */
    printf("--- Benchmark 1c: Holonomy Batch Scaling (%lu cycles, len %d) ---\n",
           (unsigned long)HOLONOMY_CYCLES, HOLONOMY_CYCLE_LEN);

    holonomy_data_t hol_data;
    hol_data.num_cycles = HOLONOMY_CYCLES;
    hol_data.cycles = malloc(HOLONOMY_CYCLES * sizeof(holonomy_cycle_t));
    hol_data.results = malloc(HOLONOMY_CYCLES * sizeof(double complex));

    srand(67890);
    for (uint64_t c = 0; c < HOLONOMY_CYCLES; c++) {
        hol_data.cycles[c].len = HOLONOMY_CYCLE_LEN;
        for (int i = 0; i < HOLONOMY_CYCLE_LEN; i++) {
            double angle = ((double)rand() / RAND_MAX) * 2.0 * M_PI;
            hol_data.cycles[c].elements[i] = cos(angle) + sin(angle) * I;
        }
    }

    printf("%-30s | %3s | %12s | %8s | %8s\n",
           "Operation", "Thr", "Throughput", "Speedup", "Efficiency");
    printf("------------------------------------------------------------------\n");

    double hol_single = 0.0;
    for (int i = 0; i < num_thread_configs; i++) {
        int t = thread_counts[i];
        double tp = bench_median(t, (double(*)(int,void*))run_holonomy_bench, &hol_data);
        double speedup = (i == 0) ? 1.0 : tp / hol_single;
        double efficiency = speedup / t;
        if (i == 0) hol_single = tp;
        print_bench_line("Holonomy Batch", t, tp, speedup, efficiency);
    }

    free(hol_data.cycles);
    free(hol_data.results);
    printf("\n");

    /* ======== Benchmark 1d: Cyclotomic Field Projection ======== */
    printf("--- Benchmark 1d: Cyclotomic Field Projection (%lu points, Q(ζ₁₅)) ---\n",
           (unsigned long)CYCLOTOMIC_POINTS);

    cyclotomic_data_t cyc_data;
    cyc_data.n = CYCLOTOMIC_POINTS;
    cyc_data.xs = malloc(CYCLOTOMIC_POINTS * sizeof(double));
    cyc_data.ys = malloc(CYCLOTOMIC_POINTS * sizeof(double));
    cyc_data.projections = malloc(CYCLOTOMIC_POINTS * sizeof(double complex));

    /* Use same data as Eisenstein snap for comparison */
    memcpy(cyc_data.xs, es_data.xs, CYCLOTOMIC_POINTS * sizeof(double));
    memcpy(cyc_data.ys, es_data.ys, CYCLOTOMIC_POINTS * sizeof(double));

    printf("%-30s | %3s | %12s | %8s | %8s\n",
           "Operation", "Thr", "Throughput", "Speedup", "Efficiency");
    printf("------------------------------------------------------------------\n");

    double cyc_single = 0.0;
    for (int i = 0; i < num_thread_configs; i++) {
        int t = thread_counts[i];
        double tp = bench_median(t, (double(*)(int,void*))run_cyclotomic_bench, &cyc_data);
        double speedup = (i == 0) ? 1.0 : tp / cyc_single;
        double efficiency = speedup / t;
        if (i == 0) cyc_single = tp;
        print_bench_line("Cyclotomic Projection", t, tp, speedup, efficiency);
    }

    free(cyc_data.xs);
    free(cyc_data.ys);
    free(cyc_data.projections);

    /* Cleanup Eisenstein data */
    free(es_data.xs);
    free(es_data.ys);
    free(es_data.results_a);
    free(es_data.results_b);

    printf("\n");
    printf("============================================================\n");
    printf(" Benchmark Complete\n");
    printf("============================================================\n");

    return 0;
}
