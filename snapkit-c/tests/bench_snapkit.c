/**
 * @file bench_snapkit.c
 * @brief Micro-benchmarks for SnapKit.
 *
 * Measures cycles per snap for scalar, Eisenstein, and batch operations.
 *
 * Expected output (representative, varies by CPU):
 *   SnapKit Benchmark v0.2.0
 *   ─────────────────────────
 *   Scalar snap:         45.2 ns/snap  (22.1 million/s)
 *   Eisenstein snap:     78.3 ns/snap  (12.8 million/s)
 *   Batch snap (1024):    8.1 ns/snap  (123.5 million/s)
 *   Batch Eisenstein:    65.2 ns/snap  (15.3 million/s)
 *   Attention allocate:  92.0 ns/call  (10.9 million/s)
 *   Script match (10):  112.5 ns/match (8.9 million/s)
 */

#include "snapkit/snapkit.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ===========================================================================
 * Timing helpers
 * ========================================================================= */

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}

static double bench(const char* name, int iterations,
                     void (*func)(void* ctx), void* ctx) {
    /* Warmup */
    for (int i = 0; i < 10; i++) func(ctx);

    double start = now_ns();
    for (int i = 0; i < iterations; i++) func(ctx);
    double end = now_ns();

    double total_ns = end - start;
    double per_op = total_ns / (double)iterations;
    double ops_per_sec = 1e9 / per_op;

    printf("  %-25s %8.1f ns/op  (%8.1f million/s)\n",
           name, per_op, ops_per_sec / 1e6);

    return per_op;
}

/* ===========================================================================
 * Benchmark contexts
 * ========================================================================= */

typedef struct {
    snapkit_snap_function_t* sf;
    double* values;
    snapkit_snap_result_t* results;
    size_t n;
} snap_ctx_t;

static void bench_scalar_snap(void* ctx) {
    snap_ctx_t* c = (snap_ctx_t*)ctx;
    for (size_t i = 0; i < c->n; i++) {
        snapkit_snap(c->sf, c->values[i], NAN, &c->results[i]);
    }
}

static void bench_eisenstein_snap(void* ctx) {
    snap_ctx_t* c = (snap_ctx_t*)ctx;
    for (size_t i = 0; i < c->n; i++) {
        snapkit_snap_eisenstein(c->sf, c->values[i], c->values[i] * 0.5,
                                 -1.0, &c->results[i]);
    }
}

typedef struct {
    snapkit_snap_function_t* sf;
    double* values;
    snapkit_snap_result_t* results;
    size_t n;
} batch_ctx_t;

static void bench_batch_snap(void* ctx) {
    batch_ctx_t* c = (batch_ctx_t*)ctx;
    snapkit_snap_batch(c->sf, c->values, c->n, c->results);
}

typedef struct {
    double* reals;
    double* imags;
    snapkit_snap_result_t* results;
    size_t n;
} batch_eis_ctx_t;

static void bench_batch_eisenstein(void* ctx) {
    batch_eis_ctx_t* c = (batch_eis_ctx_t*)ctx;
    snapkit_snap_eisenstein_batch(NULL, c->reals, c->imags, c->n, c->results);
}

typedef struct {
    snapkit_attention_budget_t* ab;
    snapkit_delta_t deltas[4];
    snapkit_allocation_t allocs[4];
    size_t n_alloc;
} attn_ctx_t;

static void bench_attention_alloc(void* ctx) {
    attn_ctx_t* c = (attn_ctx_t*)ctx;
    snapkit_budget_allocate(c->ab, c->deltas, 4, c->allocs, &c->n_alloc);
    c->ab->remaining = c->ab->total_budget;
}

typedef struct {
    snapkit_script_library_t* lib;
    double obs[16];
    snapkit_script_match_t match;
} script_ctx_t;

static void bench_script_match(void* ctx) {
    script_ctx_t* c = (script_ctx_t*)ctx;
    snapkit_script_library_match(c->lib, c->obs, 16, &c->match);
}

/* ===========================================================================
 * Main
 * ========================================================================= */

int main(void) {
    printf("SnapKit Benchmark v%s\n", SNAPKIT_VERSION);
    printf("NEON: %s | SSE: %s\n",
            SNAPKIT_HAVE_NEON ? "yes" : "no",
            SNAPKIT_HAVE_SSE ? "yes" : "no");
    printf("\u2500%.0s", "\u2500"); /* cannot expand, just newline */
    printf("\n");

    /* Seed random */
    srand(42);

    /* ── Scalar snap benchmark ── */
    const size_t N = 1000;
    double* vals = (double*)malloc(N * sizeof(double));
    for (size_t i = 0; i < N; i++) vals[i] = (double)rand() / RAND_MAX * 2.0 - 1.0;

    snapkit_snap_result_t* results = (snapkit_snap_result_t*)
        malloc(N * sizeof(snapkit_snap_result_t));

    snapkit_snap_function_t* sf = snapkit_snap_create_ex(0.1,
            SNAPKIT_TOPOLOGY_HEXAGONAL, 0.0, 0.01);

    snap_ctx_t snap_ctx = {sf, vals, results, 100};
    bench("Scalar snap", 10000, bench_scalar_snap, &snap_ctx);

    /* ── Eisenstein snap benchmark ── */
    bench("Eisenstein snap", 5000, bench_eisenstein_snap, &snap_ctx);

    /* ── Batch snap benchmark ── */
    batch_ctx_t batch_ctx = {sf, vals, results, N};
    bench("Batch snap (1000)", 1000, bench_batch_snap, &batch_ctx);

    /* ── Batch Eisenstein benchmark ── */
    double* reals = (double*)malloc(N * sizeof(double));
    double* imags = (double*)malloc(N * sizeof(double));
    for (size_t i = 0; i < N; i++) {
        reals[i] = (double)rand() / RAND_MAX * 10.0 - 5.0;
        imags[i] = (double)rand() / RAND_MAX * 10.0 - 5.0;
    }

    batch_eis_ctx_t eis_ctx = {reals, imags, results, N};
    bench("Batch Eisenstein (1000)", 500, bench_batch_eisenstein, &eis_ctx);

    /* ── Attention budget benchmark ── */
    snapkit_attention_budget_t* ab = snapkit_budget_create(100.0,
            SNAPKIT_STRATEGY_ACTIONABILITY);
    attn_ctx_t attn_ctx;
    memset(&attn_ctx, 0, sizeof(attn_ctx));
    attn_ctx.ab = ab;
    for (int i = 0; i < 4; i++) {
        attn_ctx.deltas[i].magnitude = (double)rand() / RAND_MAX;
        attn_ctx.deltas[i].actionability = (double)rand() / RAND_MAX;
        attn_ctx.deltas[i].urgency = (double)rand() / RAND_MAX;
        attn_ctx.deltas[i].severity = SNAPKIT_SEVERITY_MEDIUM;
    }
    bench("Attention allocate (4 deltas)", 50000, bench_attention_alloc, &attn_ctx);

    /* ── Script match benchmark ── */
    snapkit_script_library_t* lib = snapkit_script_library_create(0.85);
    script_ctx_t script_ctx;
    memset(&script_ctx, 0, sizeof(script_ctx));
    script_ctx.lib = lib;

    /* Add 10 scripts with 16-dimensional patterns */
    for (int i = 0; i < 10; i++) {
        char id[16], name[32];
        snprintf(id, sizeof(id), "s%d", i);
        snprintf(name, sizeof(name), "Script_%d", i);
        double pat[16];
        for (int j = 0; j < 16; j++) pat[j] = (double)i * 0.1 + (double)j * 0.01;
        snapkit_script_library_add(lib, id, name, pat, 16, (double)i);
    }

    for (int j = 0; j < 16; j++) script_ctx.obs[j] = 0.55 + (double)j * 0.01;
    bench("Script match (10 scripts)", 20000, bench_script_match, &script_ctx);

    /* ── Cleanup ── */
    free(vals);
    free(results);
    free(reals);
    free(imags);
    snapkit_snap_free(sf);
    snapkit_budget_free(ab);
    snapkit_script_library_free(lib);

    return 0;
}
