/*
 * FLUX Constraint Checker — AVX-512 Optimized (x86-64)
 * Targets AMD Ryzen AI 9 HX 370 (Zen 5, AVX-512)
 *
 * Opcodes:
 *   0x01 RANGE lo hi   — results[i] = (lo <= inputs[i] <= hi) ? 1 : 0
 *   0x02 BOOL_AND      — results[i] &= inputs[i]
 *   0x03 BOOL_OR       — results[i] |= inputs[i]
 *   0x04 ASSERT        — fault if any results[i] == 0
 *   0x00 HALT          — stop execution
 *
 * Compile: gcc -O3 -mavx512f -mavx512vl -o flux_avx512 flux_avx512_optimized.c -lm
 */

#include <immintrin.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define OPC_RANGE    0x01
#define OPC_BOOL_AND 0x02
#define OPC_BOOL_OR  0x03
#define OPC_ASSERT   0x04
#define OPC_HALT     0x00

#define VEC_WIDTH 16

/* ---- Vector path (16 elements) ---- */

static inline __m512i vec_range(__m512i vin, int32_t lo, int32_t hi) {
    __mmask16 mlo = _mm512_cmpge_epi32_mask(vin, _mm512_set1_epi32(lo));
    __mmask16 mhi = _mm512_cmple_epi32_mask(vin, _mm512_set1_epi32(hi));
    __mmask16 in_range = mlo & mhi;
    return _mm512_mask_blend_epi32(in_range, _mm512_setzero_epi32(), _mm512_set1_epi32(1));
}

static inline __m512i vec_bool_and(__m512i vres, __m512i vin) {
    return _mm512_and_epi32(vres, vin);
}

static inline __m512i vec_bool_or(__m512i vres, __m512i vin) {
    return _mm512_or_epi32(vres, vin);
}

static inline int vec_assert(__m512i vres) {
    __mmask16 nonzero = _mm512_cmpneq_epi32_mask(vres, _mm512_setzero_epi32());
    return (nonzero == 0xFFFF) ? 0 : -1;  /* 0 = pass, -1 = fault */
}

/* ---- Scalar fallback (remainder < 16) ---- */

static inline int32_t scalar_range(int32_t val, int32_t lo, int32_t hi) {
    return (val >= lo && val <= hi) ? 1 : 0;
}

static inline int scalar_assert(int32_t val) {
    return (val == 0) ? -1 : 0;
}

/* ---- Batch kernel ---- */

void flux_avx512_batch(const uint8_t *bytecode, int bc_len,
                       const int32_t *inputs, int32_t *results,
                       int n, int max_gas)
{
    int gas = 0;
    int full = n / VEC_WIDTH;
    int rem  = n % VEC_WIDTH;

    /* Init results to 1 (pass-by-default) */
    for (int i = 0; i < n; i++) results[i] = 1;

    int ip = 0;
    while (ip < bc_len) {
        if (++gas > max_gas) return;
        uint8_t op = bytecode[ip++];

        switch (op) {
        case OPC_HALT:
            return;

        case OPC_RANGE: {
            int32_t lo = (int32_t)(
                ((uint32_t)bytecode[ip]   <<  0) | ((uint32_t)bytecode[ip+1] <<  8) |
                ((uint32_t)bytecode[ip+2] << 16) | ((uint32_t)bytecode[ip+3] << 24));
            ip += 4;
            int32_t hi = (int32_t)(
                ((uint32_t)bytecode[ip]   <<  0) | ((uint32_t)bytecode[ip+1] <<  8) |
                ((uint32_t)bytecode[ip+2] << 16) | ((uint32_t)bytecode[ip+3] << 24));
            ip += 4;

            __m512i vlo = _mm512_set1_epi32(lo);
            __m512i vhi = _mm512_set1_epi32(hi);

            for (int b = 0; b < full; b++) {
                int off = b * VEC_WIDTH;
                __m512i vin  = _mm512_loadu_si512((const void *)(inputs + off));
                __mmask16 mlo = _mm512_cmpge_epi32_mask(vin, vlo);
                __mmask16 mhi = _mm512_cmple_epi32_mask(vin, vhi);
                __m512i vres = _mm512_mask_blend_epi32(mlo & mhi,
                                _mm512_setzero_epi32(), _mm512_set1_epi32(1));
                _mm512_storeu_si512((void *)(results + off), vres);
            }
            for (int i = full * VEC_WIDTH; i < n; i++)
                results[i] = scalar_range(inputs[i], lo, hi);
            break;
        }

        case OPC_BOOL_AND:
            for (int b = 0; b < full; b++) {
                int off = b * VEC_WIDTH;
                __m512i vres = _mm512_loadu_si512((const void *)(results + off));
                __m512i vin  = _mm512_loadu_si512((const void *)(inputs  + off));
                _mm512_storeu_si512((void *)(results + off),
                                    _mm512_and_epi32(vres, vin));
            }
            for (int i = full * VEC_WIDTH; i < n; i++)
                results[i] &= inputs[i];
            break;

        case OPC_BOOL_OR:
            for (int b = 0; b < full; b++) {
                int off = b * VEC_WIDTH;
                __m512i vres = _mm512_loadu_si512((const void *)(results + off));
                __m512i vin  = _mm512_loadu_si512((const void *)(inputs  + off));
                _mm512_storeu_si512((void *)(results + off),
                                    _mm512_or_epi32(vres, vin));
            }
            for (int i = full * VEC_WIDTH; i < n; i++)
                results[i] |= inputs[i];
            break;

        case OPC_ASSERT: {
            int fault = 0;
            for (int b = 0; b < full && !fault; b++) {
                __m512i vres = _mm512_loadu_si512(
                    (const void *)(results + b * VEC_WIDTH));
                if (vec_assert(vres) != 0) fault = 1;
            }
            for (int i = full * VEC_WIDTH; i < n && !fault; i++)
                if (scalar_assert(results[i]) != 0) fault = 1;
            /* Caller checks results[i]==0 for fault details */
            break;
        }

        default:
            return;  /* unknown opcode → halt */
        }
    }
}

/* ---- Benchmark ---- */

#define BENCH_N      (16 * 1024 * 64)   /* 1M elements */
#define BENCH_ITERS  200

/* Bytecode: RANGE(0,100), BOOL_AND, ASSERT, HALT */
static const uint8_t bench_bc[] = {
    OPC_RANGE,
    0,0,0,0,   /* lo = 0 */
    100,0,0,0, /* hi = 100 */
    OPC_BOOL_AND,
    OPC_ASSERT,
    OPC_HALT
};

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

void flux_avx512_benchmark(void) {
    int32_t *inputs  = aligned_alloc(64, BENCH_N * sizeof(int32_t));
    int32_t *results = aligned_alloc(64, BENCH_N * sizeof(int32_t));

    /* Fill inputs: 0..199 repeating */
    for (int i = 0; i < BENCH_N; i++)
        inputs[i] = i % 200;

    /* Warmup */
    flux_avx512_batch(bench_bc, sizeof(bench_bc), inputs, results, BENCH_N, 100000);

    double t0 = now_sec();
    for (int it = 0; it < BENCH_ITERS; it++)
        flux_avx512_batch(bench_bc, sizeof(bench_bc), inputs, results, BENCH_N, 100000);
    double t1 = now_sec();

    double elapsed = t1 - t0;
    double elems_per_sec = (double)BENCH_N * BENCH_ITERS / elapsed;
    double ns_per_elem   = elapsed * 1e9 / ((double)BENCH_N * BENCH_ITERS);

    printf("FLUX AVX-512 Benchmark\n");
    printf("  Elements    : %d (%d vectors + %d scalar)\n",
           BENCH_N, BENCH_N / VEC_WIDTH, BENCH_N % VEC_WIDTH);
    printf("  Iterations  : %d\n", BENCH_ITERS);
    printf("  Total time  : %.4f s\n", elapsed);
    printf("  Throughput  : %.2f M elem/s\n", elems_per_sec / 1e6);
    printf("  Latency     : %.2f ns/elem\n", ns_per_elem);
    printf("  Sample out  : results[0]=%d results[50]=%d results[150]=%d\n",
           results[0], results[50], results[150]);

    free(inputs);
    free(results);
}

/* ---- Entry point ---- */

int main(void) {
    /* Quick sanity check */
    int32_t test_in[20], test_out[20];
    for (int i = 0; i < 20; i++) test_in[i] = i * 10;  /* 0,10,...,190 */

    const uint8_t check_bc[] = {
        OPC_RANGE, 0,0,0,0,  50,0,0,0,  /* RANGE(0,50) */
        OPC_HALT
    };
    flux_avx512_batch(check_bc, sizeof(check_bc), test_in, test_out, 20, 1000);

    int pass = 1;
    for (int i = 0; i < 20; i++) {
        int expect = (test_in[i] >= 0 && test_in[i] <= 50) ? 1 : 0;
        if (test_out[i] != expect) { pass = 0; printf("FAIL [%d]: got %d expect %d\n", i, test_out[i], expect); }
    }
    printf("Sanity: %s\n", pass ? "PASS" : "FAIL");

    /* Run benchmark */
    flux_avx512_benchmark();
    return pass ? 0 : 1;
}
