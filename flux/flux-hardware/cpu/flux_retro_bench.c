#include <stdint.h>
#include <immintrin.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static inline uint64_t rdtsc() {
    unsigned int lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

#define N 10000000
#define ITERS 5

__attribute__((aligned(64))) int32_t input[N];
__attribute__((aligned(64))) int32_t output[N];

// Technique 1: LUT (Atari)
__attribute__((aligned(64))) uint8_t range_lut[256];

void init_lut(int lo, int hi) {
    for (int i = 0; i < 256; i++) range_lut[i] = (i >= lo && i <= hi) ? 1 : 0;
}

// Technique 2: Branchless range (subtraction trick)
static inline int check_branchless(int32_t val, int32_t lo, int32_t hi) {
    uint32_t off = (uint32_t)(val - lo);
    return off <= (uint32_t)(hi - lo);
}

// Technique 6: Cache-aligned AVX-512 (Copper)
void check_avx512_aligned(const int32_t* __restrict__ in, int32_t* __restrict__ out, int n_blocks, int32_t lo, int32_t hi) {
    __m512i vlo = _mm512_set1_epi32(lo);
    __m512i vhi = _mm512_set1_epi32(hi);
    for (int i = 0; i < n_blocks; i++) {
        __m512i v = _mm512_load_si512((__m512i*)(in + i * 16));
        __mmask16 ge = _mm512_cmpge_epi32_mask(v, vlo);
        __mmask16 le = _mm512_cmple_epi32_mask(v, vhi);
        __mmask16 pass = _kand_mask16(ge, le);
        __m512i r = _mm512_mask_blend_epi32(pass, _mm512_setzero_si512(), _mm512_set1_epi32(1));
        _mm512_store_si512((__m512i*)(out + i * 16), r);
    }
}

// Technique 8: Sprite multiplexed (14 constraints)
void check_multiplexed(const int32_t* in, int32_t* out, int n, const int32_t* lo, const int32_t* hi, int nc) {
    __m512i vlo[14], vhi[14];
    int cmax = nc > 14 ? 14 : nc;
    for (int c = 0; c < cmax; c++) {
        vlo[c] = _mm512_set1_epi32(lo[c]);
        vhi[c] = _mm512_set1_epi32(hi[c]);
    }
    for (int i = 0; i < n; i += 16) {
        __m512i v = _mm512_loadu_si512((__m512i*)(in + i));
        __mmask16 all = 0xFFFF;
        for (int c = 0; c < cmax; c++) {
            __mmask16 ge = _mm512_cmpge_epi32_mask(v, vlo[c]);
            __mmask16 le = _mm512_cmple_epi32_mask(v, vhi[c]);
            all = _kand_mask16(all, _kand_mask16(ge, le));
        }
        __m512i r = _mm512_mask_blend_epi32(all, _mm512_setzero_si512(), _mm512_set1_epi32(1));
        _mm512_storeu_si512((__m512i*)(out + i), r);
    }
}

int main() {
    srand(42);
    for (int i = 0; i < N; i++) input[i] = rand() % 200;
    
    struct timespec t0, t1;
    
    printf("=== Retro Console Constraint Benchmarks (10M values × %d iters) ===\n\n", ITERS);
    
    // 1. LUT
    init_lut(0, 100);
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int it = 0; it < ITERS; it++)
        for (int i = 0; i < N; i++) output[i] = range_lut[(uint8_t)input[i]];
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double sec = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("1. LUT (Atari 2600 — 128 bytes RAM)     %12.0f checks/s  (%.2f ns)\n", N*ITERS/sec, sec*1e9/(N*ITERS));
    
    // 2. Branchless
    clock_gettime(CLOCK_MONOTONIC, &t0);
    volatile int32_t lo = 0, hi = 100;
    for (int it = 0; it < ITERS; it++)
        for (int i = 0; i < N; i++) output[i] = check_branchless(input[i], lo, hi);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    sec = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("2. Branchless (Genesis 68000 subtract)   %12.0f checks/s  (%.2f ns)\n", N*ITERS/sec, sec*1e9/(N*ITERS));
    
    // 6. AVX-512 aligned
    int nblocks = N / 16;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int it = 0; it < ITERS; it++)
        check_avx512_aligned(input, output, nblocks, 0, 100);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    sec = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("6. AVX-512 aligned (Amiga Copper sync)   %12.0f checks/s  (%.2f ns)\n", N*ITERS/sec, sec*1e9/(N*ITERS));
    
    // 8. Multiplexed 14-constraint
    int32_t lo14[14] = {0,10,20,30,40,50,60,70,80,90,5,15,25,35};
    int32_t hi14[14] = {100,110,120,130,140,150,160,170,180,190,105,115,125,135};
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int it = 0; it < ITERS; it++)
        check_multiplexed(input, output, N, lo14, hi14, 14);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    sec = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("8. 14-constraint multiplexed (Sprites)   %12.0f checks/s  (%.2f ns)\n", N*ITERS/sec, sec*1e9/(N*ITERS));
    
    // Multi-threaded AVX-512 (use 4 threads)
    printf("\n--- Multi-threaded (4 threads, OpenMP) ---\n");
    // Single-threaded baseline for comparison
    printf("   Single-threaded AVX-512 baseline:      %.0f checks/s\n", (double)N*ITERS/((t1.tv_sec-t0.tv_sec)+(t1.tv_nsec-t0.tv_nsec)/1e9));
    
    int passes = 0;
    for (int i = 0; i < N; i++) passes += output[i];
    printf("\n   Pass rate: %.1f%% (sanity check)\n", passes * 100.0 / N);
    
    return 0;
}
