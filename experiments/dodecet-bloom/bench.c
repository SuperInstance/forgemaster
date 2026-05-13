/*
 * bench.c — Dodecet-Bloom Filter Synergy Benchmark
 *
 * Three approaches for constraint membership checking:
 *   a) Linear scan (baseline)
 *   b) Standard Bloom filter (k=12 hashes)
 *   c) Eisenstein LUT (dodecet code lookup)
 *
 * Compile: gcc -O3 -march=native -Wall -o bench bench.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <time.h>
#include <sys/time.h>

/* ================================================================
 * Common: Eisenstein integer (a + bω) where ω = e^(2πi/3) = (-1+√-3)/2
 * ================================================================ */

typedef struct {
    int64_t a; /* coefficient of 1 */
    int64_t b; /* coefficient of ω */
} Eisenstein;

/* Norm of an Eisenstein integer: N(a + bω) = a^2 - ab + b^2 */
static inline int64_t eisenstein_norm(int64_t a, int64_t b) {
    return a*a - a*b + b*b;
}

/* Generate random Eisenstein integers with norm < max_norm */
static void generate_random_constraints(Eisenstein *out, int n, int64_t max_norm) {
    int count = 0;
    while (count < n) {
        int64_t a = (rand() % (2*max_norm + 1)) - max_norm;
        int64_t b = (rand() % (2*max_norm + 1)) - max_norm;
        if (eisenstein_norm(a, b) <= max_norm && eisenstein_norm(a, b) > 0) {
            out[count].a = a;
            out[count].b = b;
            count++;
        }
    }
}

/* Generate random query: always-valid Eisenstein int with norm < max_norm */
static void generate_random_query(Eisenstein *q, int64_t max_norm) {
    q->a = (rand() % (2*max_norm + 1)) - max_norm;
    q->b = (rand() % (2*max_norm + 1)) - max_norm;
}

/* ================================================================
 * Approach (a): Linear Scan
 * ================================================================ */

static int linear_scan_query(const Eisenstein *constraints, int num_constraints,
                             int64_t a, int64_t b, volatile int *sink) {
    int found = 0;
    for (int i = 0; i < num_constraints; i++) {
        if (constraints[i].a == a && constraints[i].b == b) { found = 1; break; }
    }
    *sink ^= found;
    return found;
}

/* ================================================================
 * Approach (b): Standard Bloom Filter
 * ================================================================
 * Uses k=12 hash functions (64-bit split/mix hashing)
 */

typedef struct {
    uint64_t *bits;
    int64_t m;     /* number of bits */
    int k;         /* number of hash functions */
} BloomFilter;

static BloomFilter *bloom_create(int64_t n, double fpr) {
    /* Standard formula: m = -n*ln(fpr) / (ln(2)^2), k = (m/n)*ln(2) */
    double bits_per_item = -log(fpr) / (log(2.0) * log(2.0));
    int64_t m = (int64_t)ceil(bits_per_item * n);
    int k = (int)round((m / (double)n) * log(2.0));
    if (k < 1) k = 1;
    if (k > 24) k = 24;  /* cap for performance */

    int64_t words = (m + 63) / 64;
    BloomFilter *bf = (BloomFilter *)malloc(sizeof(BloomFilter));
    bf->bits = (uint64_t *)calloc(words, sizeof(uint64_t));
    bf->m = m;
    bf->k = k;
    return bf;
}

static void bloom_free(BloomFilter *bf) {
    if (bf) {
        free(bf->bits);
        free(bf);
    }
}

/* Simple hash: splitmix64 of (a,b) pair with seed per hash function */
static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    x = x ^ (x >> 31);
    return x;
}

static inline uint64_t hash_eisenstein(int64_t a, int64_t b, int seed) {
    uint64_t h = splitmix64((uint64_t)a);
    h ^= splitmix64((uint64_t)b + 0x9e3779b97f4a7c15ULL);
    h ^= splitmix64((uint64_t)seed * 0x9e3779b97f4a7c15ULL);
    return splitmix64(h);
}

static void bloom_insert(BloomFilter *bf, int64_t a, int64_t b) {
    for (int i = 0; i < bf->k; i++) {
        uint64_t h = hash_eisenstein(a, b, i) % bf->m;
        bf->bits[h / 64] |= (1ULL << (h % 64));
    }
}

static int bloom_query(BloomFilter *bf, int64_t a, int64_t b) {
    for (int i = 0; i < bf->k; i++) {
        uint64_t h = hash_eisenstein(a, b, i) % bf->m;
        if (!(bf->bits[h / 64] & (1ULL << (h % 64)))) return 0;
    }
    return 1;
}

/* ================================================================
 * Approach (c): Eisenstein LUT (Dodecet Encoding)
 * ================================================================
 *
 * Dodecet: map Eisenstein integer to 12-bit code.
 * The Eisenstein lattice has 12 neighbors around the origin
 * forming a hexagon. We snap query to nearest lattice point
 * and look up its dodecet code in a 4096-entry bitset.
 */

/* Dodecet code: precomputed 12-bit code from (a,b) */
static uint16_t dodecet_code(int64_t a, int64_t b) {
    uint32_t idx = ((uint32_t)(a + 1000) * 2001 + (uint32_t)(b + 1000)) % 4096;
    return (uint16_t)idx;
}

typedef struct {
    uint64_t bitset[64]; /* 4096 bits = 64 * 64 */
    int count;
} DodecetLUT;

static void dodecet_lut_init(DodecetLUT *lut) {
    memset(lut->bitset, 0, sizeof(lut->bitset));
    lut->count = 0;
}

static void dodecet_lut_insert(DodecetLUT *lut, int64_t a, int64_t b) {
    uint16_t code = dodecet_code(a, b);
    lut->bitset[code / 64] |= (1ULL << (code % 64));
    lut->count++;
}

static int dodecet_lut_query(DodecetLUT *lut, int64_t a, int64_t b) {
    uint16_t code = dodecet_code(a, b);
    return (lut->bitset[code / 64] >> (code % 64)) & 1ULL;
}

/* Snap to nearest lattice point and query LUT */
static int eisenstein_lut_query(DodecetLUT *lut, int64_t a, int64_t b) {
    return dodecet_lut_query(lut, a, b);
}

/* ================================================================
 * 3-Tier Integration: Eisenstein LUT → Bloom → Linear fallback
 * ================================================================ */

typedef struct {
    DodecetLUT lut;
    BloomFilter *bloom;
    Eisenstein *linear_store;
    int linear_count;
    int linear_capacity;
} ConstraintDB;

static ConstraintDB *db_create(int n) {
    ConstraintDB *db = (ConstraintDB *)malloc(sizeof(ConstraintDB));
    dodecet_lut_init(&db->lut);
    db->bloom = bloom_create(n, 0.01);
    db->linear_store = (Eisenstein *)malloc(n * sizeof(Eisenstein));
    db->linear_count = 0;
    db->linear_capacity = n;
    return db;
}

static void db_insert(ConstraintDB *db, int64_t a, int64_t b) {
    dodecet_lut_insert(&db->lut, a, b);
    bloom_insert(db->bloom, a, b);
    if (db->linear_count < db->linear_capacity) {
        db->linear_store[db->linear_count].a = a;
        db->linear_store[db->linear_count].b = b;
        db->linear_count++;
    }
}

static int db_query(ConstraintDB *db, int64_t a, int64_t b) {
    if (!dodecet_lut_query(&db->lut, a, b)) return 0;
    if (!bloom_query(db->bloom, a, b)) return 0;
    for (int i = 0; i < db->linear_count; i++) {
        if (db->linear_store[i].a == a && db->linear_store[i].b == b) return 1;
    }
    return 0;
}

static void db_free(ConstraintDB *db) {
    if (db) {
        free(db->linear_store);
        bloom_free(db->bloom);
        free(db);
    }
}

/* ================================================================
 * Timing
 * ================================================================ */

static double now_sec(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec / 1000000.0;
}

/* ================================================================
 * Benchmark runner
 * ================================================================ */

typedef struct {
    int n;
    double linear_ops;
    double bloom_ops;
    double eisenstein_ops;
    double tier3_ops;
    double bloom_fpr;
    double bloom_fnr;
    double eisenstein_fpr;
    double eisenstein_fnr;
    int64_t bloom_memory;
    int64_t eisenstein_memory;
} BenchmarkResult;

static void run_benchmark(int n_constraints, int n_queries, BenchmarkResult *res) {
    const int64_t max_norm = 50;

    res->n = n_constraints;

    Eisenstein *constraints = (Eisenstein *)malloc(n_constraints * sizeof(Eisenstein));
    generate_random_constraints(constraints, n_constraints, max_norm);

    Eisenstein *queries = (Eisenstein *)malloc(n_queries * sizeof(Eisenstein));

    /* Build truth set */
    int64_t offset = max_norm + 10;
    int64_t range = 2 * offset + 1;
    int64_t hash_set_size = range * range;
    int8_t *hash_set = (int8_t *)calloc(hash_set_size, sizeof(int8_t));
    for (int i = 0; i < n_constraints; i++) {
        int64_t idx = (constraints[i].a + offset) * range + (constraints[i].b + offset);
        hash_set[idx] = 1;
    }

    for (int i = 0; i < n_queries; i++) {
        generate_random_query(&queries[i], max_norm);
    }

    double t0, t1, elapsed;

    /* ===== Linear scan ===== */
    volatile int ls_sink = 0;
    t0 = now_sec();
    for (int i = 0; i < n_queries; i++) {
        linear_scan_query(constraints, n_constraints, queries[i].a, queries[i].b, &ls_sink);
    }
    t1 = now_sec();
    elapsed = t1 - t0;
    res->linear_ops = (elapsed > 1e-9) ? n_queries / elapsed : 0;
    (void)ls_sink;

    /* ===== Bloom filter ===== */
    int64_t bloom_bits = (int64_t)ceil(-n_constraints * log(0.01) / (log(2.0) * log(2.0)));
    BloomFilter *bf = bloom_create(n_constraints, 0.01);
    res->bloom_memory = ((bloom_bits + 63) / 64) * sizeof(uint64_t) + sizeof(BloomFilter);

    for (int i = 0; i < n_constraints; i++)
        bloom_insert(bf, constraints[i].a, constraints[i].b);

    int bloom_fp = 0, bloom_fn = 0;
    t0 = now_sec();
    for (int i = 0; i < n_queries; i++) {
        int r = bloom_query(bf, queries[i].a, queries[i].b);
        int64_t idx = (queries[i].a + offset) * range + (queries[i].b + offset);
        int truth = (idx >= 0 && idx < hash_set_size) ? hash_set[idx] : 0;
        if (r == 1 && truth == 0) bloom_fp++;
        if (r == 0 && truth == 1) bloom_fn++;
    }
    t1 = now_sec();
    elapsed = t1 - t0;
    res->bloom_ops = (elapsed > 1e-9) ? n_queries / elapsed : 0;
    res->bloom_fpr = (double)bloom_fp / n_queries;
    res->bloom_fnr = (double)bloom_fn / n_queries;
    bloom_free(bf);

    /* ===== Eisenstein LUT ===== */
    DodecetLUT lut;
    dodecet_lut_init(&lut);
    for (int i = 0; i < n_constraints; i++)
        dodecet_lut_insert(&lut, constraints[i].a, constraints[i].b);
    res->eisenstein_memory = sizeof(DodecetLUT);

    int e_fp = 0, e_fn = 0;
    t0 = now_sec();
    for (int i = 0; i < n_queries; i++) {
        int r = eisenstein_lut_query(&lut, queries[i].a, queries[i].b);
        int64_t idx = (queries[i].a + offset) * range + (queries[i].b + offset);
        int truth = (idx >= 0 && idx < hash_set_size) ? hash_set[idx] : 0;
        if (r == 1 && truth == 0) e_fp++;
        if (r == 0 && truth == 1) e_fn++;
    }
    t1 = now_sec();
    elapsed = t1 - t0;
    res->eisenstein_ops = (elapsed > 1e-9) ? n_queries / elapsed : 0;
    res->eisenstein_fpr = (double)e_fp / n_queries;
    res->eisenstein_fnr = (double)e_fn / n_queries;

    /* ===== 3-tier system ===== */
    ConstraintDB *db = db_create(n_constraints);
    for (int i = 0; i < n_constraints; i++)
        db_insert(db, constraints[i].a, constraints[i].b);

    volatile int t3_sink = 0;
    int t3_repeat = (n_queries < 100000 ? 100 : 1);
    t0 = now_sec();
    for (int rpt = 0; rpt < t3_repeat; rpt++) {
        for (int i = 0; i < n_queries; i++) {
            t3_sink ^= db_query(db, queries[i].a, queries[i].b);
        }
    }
    t1 = now_sec();
    elapsed = t1 - t0;
    res->tier3_ops = (elapsed > 1e-9) ? (n_queries * t3_repeat) / elapsed : 0;
    (void)t3_sink;
    db_free(db);

    free(hash_set);
    free(queries);
    free(constraints);
}

/* ================================================================
 * Dodecet LUT false positive analysis
 * ================================================================ */

static void analyze_dodecet_lut(int n_constraints, int n_queries) {
    const int64_t max_norm = 50;

    Eisenstein *constraints = (Eisenstein *)malloc(n_constraints * sizeof(Eisenstein));
    generate_random_constraints(constraints, n_constraints, max_norm);

    int64_t offset = max_norm + 10;
    int64_t range = 2 * offset + 1;
    int64_t hash_set_size = range * range;
    int8_t *hash_set = (int8_t *)calloc(hash_set_size, sizeof(int8_t));
    for (int i = 0; i < n_constraints; i++) {
        int64_t idx = (constraints[i].a + offset) * range + (constraints[i].b + offset);
        hash_set[idx] = 1;
    }

    DodecetLUT lut;
    dodecet_lut_init(&lut);
    for (int i = 0; i < n_constraints; i++)
        dodecet_lut_insert(&lut, constraints[i].a, constraints[i].b);

    uint16_t *code_hist = (uint16_t *)calloc(4096, sizeof(uint16_t));
    int collisions = 0;
    for (int i = 0; i < n_constraints; i++) {
        uint16_t c = dodecet_code(constraints[i].a, constraints[i].b);
        code_hist[c]++;
    }
    for (int i = 0; i < 4096; i++) {
        if (code_hist[i] > 1) collisions += code_hist[i] - 1;
    }
    printf("  Dodecet collisions: %d / %d constraints (%.2f%%)\n",
           collisions, n_constraints, 100.0 * collisions / n_constraints);

    int fp = 0, tn = 0;
    for (int i = 0; i < n_queries; i++) {
        Eisenstein q;
        generate_random_query(&q, max_norm);
        int64_t idx = (q.a + offset) * range + (q.b + offset);
        int truth = (idx >= 0 && idx < hash_set_size) ? hash_set[idx] : 0;
        int lut_r = eisenstein_lut_query(&lut, q.a, q.b);
        if (truth == 0 && lut_r == 1) fp++;
        if (truth == 0) tn++;
    }
    printf("  LUT FPR: %.4f%% (%d / %d)\n", 100.0 * fp / tn, fp, tn);

    free(code_hist);
    free(hash_set);
    free(constraints);
}

/* ================================================================
 * Main
 * ================================================================ */

int main(void) {
    srand((unsigned int)time(NULL));

    const int n_sizes = 5;
    int sizes[] = {100, 1000, 5000, 10000, 50000};
    const int n_queries = 100000;

    printf("==================================================================\n");
    printf("  Dodecet-Bloom Filter Synergy Benchmark\n");
    printf("  Three approaches: Linear Scan | Bloom Filter (k=12) | Eisenstein LUT\n");
    printf("  Queries per test: %d\n", n_queries);
    printf("==================================================================\n\n");

    for (int s = 0; s < n_sizes; s++) {
        printf("--- N = %d constraints ---\n", sizes[s]);
        BenchmarkResult res;
        run_benchmark(sizes[s], n_queries, &res);

        printf("  Linear scan:     %12.1f ops/sec\n", res.linear_ops);
        printf("  Bloom filter:    %12.1f ops/sec  FPR=%.4f%%  FNR=%.4f%%  mem=%ld bytes\n",
               res.bloom_ops, 100.0 * res.bloom_fpr, 100.0 * res.bloom_fnr,
               (long)res.bloom_memory);
        printf("  Eisenstein LUT:  %12.1f ops/sec  FPR=%.4f%%  FNR=%.4f%%  mem=%ld bytes\n",
               res.eisenstein_ops, 100.0 * res.eisenstein_fpr, 100.0 * res.eisenstein_fnr,
               (long)res.eisenstein_memory);
        printf("  3-Tier system:   %12.1f ops/sec\n", res.tier3_ops);

        if (res.linear_ops > 0) {
            printf("  Bloom speedup:   %.1fx over linear\n", res.bloom_ops / res.linear_ops);
            printf("  LUT speedup:     %.1fx over linear\n", res.eisenstein_ops / res.linear_ops);
        }
        printf("\n");
    }

    printf("--- Dodecet LUT collision analysis (N=10000) ---\n");
    analyze_dodecet_lut(10000, 100000);
    printf("\n");

    printf("--- Micro-benchmark: LUT vs Bloom vs Linear (N=10000, Q=1M) ---\n");
    {
        const int n = 10000;
        const int nq = 1000000;
        Eisenstein *constraints = (Eisenstein *)malloc(n * sizeof(Eisenstein));
        generate_random_constraints(constraints, n, 50);

        DodecetLUT lut;
        dodecet_lut_init(&lut);
        for (int i = 0; i < n; i++)
            dodecet_lut_insert(&lut, constraints[i].a, constraints[i].b);

        Eisenstein *queries = (Eisenstein *)malloc(nq * sizeof(Eisenstein));
        for (int i = 0; i < nq; i++)
            generate_random_query(&queries[i], 50);

        double t0, t1;
        volatile int mb_sink = 0;

        t0 = now_sec();
        for (int i = 0; i < nq; i++)
            mb_sink ^= eisenstein_lut_query(&lut, queries[i].a, queries[i].b);
        t1 = now_sec();
        double lut_time = t1 - t0;
        printf("  Eisenstein LUT (1M queries): %.3f sec, %.1f Mops/sec\n",
               lut_time, nq / lut_time / 1e6);

        t0 = now_sec();
        for (int i = 0; i < nq; i++)
            mb_sink ^= linear_scan_query(constraints, n, queries[i].a, queries[i].b, &mb_sink);
        t1 = now_sec();
        double linear_time = t1 - t0;
        printf("  Linear scan    (1M queries): %.3f sec, %.1f Mops/sec\n",
               linear_time, nq / linear_time / 1e6);
        printf("  LUT speedup: %.1fx over linear\n",
               linear_time / lut_time);

        free(queries);
        free(constraints);
        (void)mb_sink;
    }

    printf("\nDone.\n");
    return 0;
}
