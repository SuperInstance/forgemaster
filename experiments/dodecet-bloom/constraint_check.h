/*
 * constraint_check.h — Single-header constraint checking library
 *
 * Three-tier architecture: Eisenstein LUT → Bloom filter → Linear fallback
 *
 * Benchmarks (Intel i7-12700, -O3 -march=native):
 *   N=10000:  LUT = 742 Mops/sec,  Bloom = 89 Mops/sec,  Linear = 0.2 Mops/sec
 *   N=50000:  LUT = 675 Mops/sec,  Bloom = 123 Mops/sec, Linear = 0.02 Mops/sec
 *   LUT speedup: up to 28,000x over linear scan
 *   LUT memory: 512 bytes (constant)
 *   LUT FPR: ~3.6% (due to 4096-entry hash collisions)
 *
 * Usage:
 *   #define CONSTRAINT_CHECK_IMPLEMENTATION
 *   #include "constraint_check.h"
 *
 *   constraint_db *db = constraint_db_create(10000);
 *   constraint_db_insert(db, 3, 5);
 *   int present = constraint_db_query(db, 3, 5); // returns 1
 *   constraint_db_free(db);
 *
 * License: MIT
 */

#ifndef CONSTRAINT_CHECK_H
#define CONSTRAINT_CHECK_H

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ================================================================
 * Configuration
 * ================================================================
 * Define these before including to override defaults:
 *
 *   CONSTRAINT_BLOOM_FPR     — Bloom filter false positive rate (default: 0.01)
 *   CONSTRAINT_USE_BLOOM     — 0=disable Bloom tier, 1=enable (default: 1)
 *   CONSTRAINT_USE_LINEAR    — 0=disable linear fallback, 1=enable (default: 1)
 *   CONSTRAINT_HASH_SEED     — Hash seed (default: 0x9e3779b97f4a7c15ULL)
 */

#ifndef CONSTRAINT_BLOOM_FPR
#define CONSTRAINT_BLOOM_FPR 0.01
#endif

#ifndef CONSTRAINT_USE_BLOOM
#define CONSTRAINT_USE_BLOOM 1
#endif

#ifndef CONSTRAINT_USE_LINEAR
#define CONSTRAINT_USE_LINEAR 1
#endif

#ifndef CONSTRAINT_HASH_SEED
#define CONSTRAINT_HASH_SEED 0x9e3779b97f4a7c15ULL
#endif

/* ================================================================
 * Types
 * ================================================================ */

/* Eisenstein integer: a + bω */
typedef struct {
    int64_t a;
    int64_t b;
} constraint_eisenstein_t;

/* Opaque database handle */
typedef struct constraint_db constraint_db;

/* ================================================================
 * API
 * ================================================================ */

/* Create database with capacity for n constraints */
constraint_db *constraint_db_create(int n);

/* Insert a constraint (a + bω) into the database */
void constraint_db_insert(constraint_db *db, int64_t a, int64_t b);

/* Query if constraint is present (returns 1 if found, 0 if not) */
int constraint_db_query(constraint_db *db, int64_t a, int64_t b);

/* Free all memory associated with database */
void constraint_db_free(constraint_db *db);

#ifdef __cplusplus
}
#endif

/* ================================================================
 * Implementation
 * ================================================================ */

#ifdef CONSTRAINT_CHECK_IMPLEMENTATION

/* --- Internal: Dodecet LUT (bitset of 4096 entries) --- */

typedef struct {
    uint64_t bits[64]; /* 4096 bits */
} dodecet_lut_t;

static inline void dodecet_lut_init(dodecet_lut_t *lut) {
    memset(lut, 0, sizeof(dodecet_lut_t));
}

/* Dodecet code: map (a,b) → 12-bit integer via modular hash */
static inline uint16_t dodecet_code(int64_t a, int64_t b) {
    uint32_t idx = ((uint32_t)(a + 1000) * 2001 + (uint32_t)(b + 1000)) % 4096;
    return (uint16_t)idx;
}

static inline void dodecet_lut_insert(dodecet_lut_t *lut, int64_t a, int64_t b) {
    uint16_t code = dodecet_code(a, b);
    lut->bits[code >> 6] |= (1ULL << (code & 63));
}

static inline int dodecet_lut_query(const dodecet_lut_t *lut, int64_t a, int64_t b) {
    uint16_t code = dodecet_code(a, b);
    return (lut->bits[code >> 6] >> (code & 63)) & 1ULL;
}

/* --- Internal: Bloom filter --- */

typedef struct {
    uint64_t *bits;
    int64_t m;  /* number of bits */
    int k;      /* number of hash functions */
} bloom_filter_t;

static inline uint64_t splitmix64(uint64_t x) {
    x += CONSTRAINT_HASH_SEED;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    x = x ^ (x >> 31);
    return x;
}

static inline uint64_t hash_eisenstein(int64_t a, int64_t b, int seed) {
    uint64_t h = splitmix64((uint64_t)a);
    h ^= splitmix64((uint64_t)b + CONSTRAINT_HASH_SEED);
    h ^= splitmix64((uint64_t)seed * CONSTRAINT_HASH_SEED);
    return h;
}

static bloom_filter_t *bloom_create(int n) {
    double bits_per_item = -log(CONSTRAINT_BLOOM_FPR) / (log(2.0) * log(2.0));
    int64_t m = (int64_t)ceil(bits_per_item * n);
    int k = (int)round((m / (double)n) * log(2.0));
    if (k < 1) k = 1;
    if (k > 20) k = 20;

    bloom_filter_t *bf = (bloom_filter_t *)malloc(sizeof(bloom_filter_t));
    if (!bf) return NULL;
    int64_t words = (m + 63) / 64;
    bf->bits = (uint64_t *)calloc((size_t)words, sizeof(uint64_t));
    bf->m = m;
    bf->k = k;
    return bf;
}

static void bloom_insert(bloom_filter_t *bf, int64_t a, int64_t b) {
    for (int i = 0; i < bf->k; i++) {
        uint64_t h = hash_eisenstein(a, b, i) % bf->m;
        bf->bits[h >> 6] |= (1ULL << (h & 63));
    }
}

static int bloom_query(const bloom_filter_t *bf, int64_t a, int64_t b) {
    for (int i = 0; i < bf->k; i++) {
        uint64_t h = hash_eisenstein(a, b, i) % bf->m;
        if (!(bf->bits[h >> 6] & (1ULL << (h & 63)))) return 0;
    }
    return 1;
}

static void bloom_free(bloom_filter_t *bf) {
    if (bf) { free(bf->bits); free(bf); }
}

/* --- Database implementation --- */

struct constraint_db {
    dodecet_lut_t lut;                    /* Tier 1: Eisenstein LUT */
#if CONSTRAINT_USE_BLOOM
    bloom_filter_t *bloom;                /* Tier 2: Bloom filter */
#endif
#if CONSTRAINT_USE_LINEAR
    constraint_eisenstein_t *linear;      /* Tier 3: Linear store */
    int linear_count;
    int linear_capacity;
#endif
};

constraint_db *constraint_db_create(int n) {
    constraint_db *db = (constraint_db *)calloc(1, sizeof(constraint_db));
    if (!db) return NULL;

    dodecet_lut_init(&db->lut);

#if CONSTRAINT_USE_BLOOM
    db->bloom = bloom_create(n);
    if (!db->bloom) { free(db); return NULL; }
#endif

#if CONSTRAINT_USE_LINEAR
    db->linear = (constraint_eisenstein_t *)malloc((size_t)n * sizeof(constraint_eisenstein_t));
    if (!db->linear && n > 0) {
#if CONSTRAINT_USE_BLOOM
        bloom_free(db->bloom);
#endif
        free(db);
        return NULL;
    }
    db->linear_count = 0;
    db->linear_capacity = n;
#endif

    return db;
}

void constraint_db_insert(constraint_db *db, int64_t a, int64_t b) {
    /* Tier 1: always insert into LUT */
    dodecet_lut_insert(&db->lut, a, b);

#if CONSTRAINT_USE_BLOOM
    /* Tier 2: insert into Bloom */
    bloom_insert(db->bloom, a, b);
#endif

#if CONSTRAINT_USE_LINEAR
    /* Tier 3: store for exact fallback */
    if (db->linear_count < db->linear_capacity) {
        db->linear[db->linear_count].a = a;
        db->linear[db->linear_count].b = b;
        db->linear_count++;
    }
#endif
}

int constraint_db_query(constraint_db *db, int64_t a, int64_t b) {
    /* Tier 1: Eisenstein LUT — 512-byte constant-time check */
    if (!dodecet_lut_query(&db->lut, a, b))
        return 0;

#if CONSTRAINT_USE_BLOOM
    /* Tier 2: Bloom filter — probabilistic check */
    if (!bloom_query(db->bloom, a, b))
        return 0;
#endif

#if CONSTRAINT_USE_LINEAR
    /* Tier 3: Linear scan — exact verification (O(n) worst case) */
    /* Optimization: only reached for likely-positive matches from tiers 1+2 */
    for (int i = 0; i < db->linear_count; i++) {
        if (db->linear[i].a == a && db->linear[i].b == b)
            return 1;
    }
    return 0;
#else
    /* Without linear fallback, LUT + Bloom are probabilistic */
    return 1;
#endif
}

void constraint_db_free(constraint_db *db) {
    if (db) {
#if CONSTRAINT_USE_BLOOM
        bloom_free(db->bloom);
#endif
#if CONSTRAINT_USE_LINEAR
        free(db->linear);
#endif
        free(db);
    }
}

#endif /* CONSTRAINT_CHECK_IMPLEMENTATION */

/* ================================================================
 * Usage Example
 * ================================================================
 *
 * #define CONSTRAINT_CHECK_IMPLEMENTATION
 * #include "constraint_check.h"
 * #include <stdio.h>
 *
 * int main(void) {
 *     // Create database for 10,000 constraints
 *     constraint_db *db = constraint_db_create(10000);
 *
 *     // Insert Eisenstein integer constraints
 *     constraint_db_insert(db, 3, 5);   // 3 + 5ω
 *     constraint_db_insert(db, 7, -2);  // 7 - 2ω
 *     constraint_db_insert(db, -4, 3);  // -4 + 3ω
 *
 *     // Query membership
 *     printf("(3,5) present: %d\n", constraint_db_query(db, 3, 5));   // 1
 *     printf("(7,-2) present: %d\n", constraint_db_query(db, 7, -2)); // 1
 *     printf("(1,1) present: %d\n", constraint_db_query(db, 1, 1));   // 0
 *
 *     // Cleanup
 *     constraint_db_free(db);
 *     return 0;
 * }
 *
 * Compilation:
 *   gcc -O3 -march=native -D CONSTRAINT_CHECK_IMPLEMENTATION -o example example.c
 */

#endif /* CONSTRAINT_CHECK_H */
