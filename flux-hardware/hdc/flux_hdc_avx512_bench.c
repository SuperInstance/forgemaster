// ============================================================================
// flux_hdc_avx512_bench.c — Benchmark for FLUX HDC AVX-512 XOR Judge
// ============================================================================
// Compile:
//   gcc -O3 -mavx512vpopcntdq -mavx512f -o flux_hdc_bench flux_hdc_avx512_bench.c
//   gcc -O3 -o flux_hdc_bench flux_hdc_avx512_bench.c  (fallback, no AVX-512)
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "flux_hdc_avx512.h"

#define BENCH_ITERATIONS  10000000
#define KB_SIZE           256

// Deterministic PRNG for test data
static uint64_t splitmix64(uint64_t *state) {
    uint64_t z = (*state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

// Generate a deterministic 128-bit hypervector simulating a range constraint
static void generate_test_hv_128(uint64_t out[2], uint64_t seed) {
    out[0] = splitmix64(&seed);
    out[1] = splitmix64(&seed);
}

// Create a related hypervector (flip N bits)
static void flip_bits_128(uint64_t out[2], const uint64_t in[2], int n_bits, uint64_t seed) {
    out[0] = in[0];
    out[1] = in[1];
    for (int i = 0; i < n_bits; i++) {
        int bit_pos = (int)(splitmix64(&seed) % 128);
        int word = bit_pos / 64;
        int bit = bit_pos % 64;
        out[word] ^= (1ULL << bit);
    }
}

int main(void) {
    printf("=== FLUX HDC AVX-512 Benchmark ===\n\n");
    
    // Run self-test first
    int failures = hdc_selftest();
    if (failures > 0) {
        printf("\n⚠️  Self-test had %d failures — results may be unreliable\n", failures);
    }
    printf("\n");
    
    // =========================================================================
    // Benchmark 1: Single 128-bit comparison throughput
    // =========================================================================
    printf("--- Benchmark 1: 128-bit single comparison ---\n");
    hdc_benchmark_128(BENCH_ITERATIONS);
    
    // =========================================================================
    // Benchmark 2: Batch matching (query vs KB)
    // =========================================================================
    printf("\n--- Benchmark 2: Batch 128-bit matching (%d entries) ---\n", KB_SIZE);
    
    // Build knowledge base
    uint64_t *kb = (uint64_t *)aligned_alloc(64, KB_SIZE * 2 * sizeof(uint64_t));
    uint64_t rng_state = 42;
    for (int i = 0; i < KB_SIZE; i++) {
        generate_test_hv_128(&kb[i * 2], rng_state);
        rng_state += 100;
    }
    
    // Query: near match to entry 100 (flip 3 bits)
    uint64_t query[2];
    flip_bits_128(query, &kb[100 * 2], 3, 999);
    
    float best_sim;
    uint64_t t0 = hdc_ns();
    for (int iter = 0; iter < BENCH_ITERATIONS / 10; iter++) {
        best_sim = 0;
        hdc_batch_match_128(query, kb, KB_SIZE, &best_sim);
    }
    uint64_t t1 = hdc_ns();
    
    int iters = BENCH_ITERATIONS / 10;
    double ns_per_batch = (double)(t1 - t0) / iters;
    printf("  Batch (%d comparisons): %.0f ns\n", KB_SIZE, ns_per_batch);
    printf("  Per comparison: %.1f ns\n", ns_per_batch / KB_SIZE);
    printf("  Throughput: %.1f M comparisons/sec\n", KB_SIZE * 1000.0 / ns_per_batch);
    printf("  Best match similarity: %.4f (entry 100 expected)\n", best_sim);
    
    // =========================================================================
    // Benchmark 3: Accuracy test — related vs unrelated
    // =========================================================================
    printf("\n--- Benchmark 3: Discrimination accuracy ---\n");
    
    // Generate base vector and variants
    uint64_t base[2], related_3bit[2], related_10bit[2], related_32bit[2], unrelated[2];
    generate_test_hv_128(base, 12345);
    flip_bits_128(related_3bit, base, 3, 111);
    flip_bits_128(related_10bit, base, 10, 222);
    flip_bits_128(related_32bit, base, 32, 333);
    generate_test_hv_128(unrelated, 99999);  // Completely independent
    
    printf("  Base vs Base+3bit:  sim=%.4f (expected ~0.976)\n", hdc_similarity_128(base, related_3bit));
    printf("  Base vs Base+10bit: sim=%.4f (expected ~0.922)\n", hdc_similarity_128(base, related_10bit));
    printf("  Base vs Base+32bit: sim=%.4f (expected ~0.750)\n", hdc_similarity_128(base, related_32bit));
    printf("  Base vs Unrelated:  sim=%.4f (expected ~0.500)\n", hdc_similarity_128(base, unrelated));
    
    // =========================================================================
    // Benchmark 4: AVX-512 512-bit path (if available)
    // =========================================================================
#ifdef __AVX512VPOPCNTDQ__
    printf("\n--- Benchmark 4: 512-bit AVX-512 VPOPCNTDQ ---\n");
    hdc_benchmark_512(BENCH_ITERATIONS);
#else
    printf("\n--- Benchmark 4: AVX-512 VPOPCNTDQ not available ---\n");
    printf("  Compile with -mavx512vpopcntdq -mavx512f to enable\n");
#endif
    
    printf("\n=== Benchmark Complete ===\n");
    
    free(kb);
    return 0;
}
