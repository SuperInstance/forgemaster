/* test_spectral.c — tests for entropy, Hurst, autocorrelation */
#include <stdio.h>
#include <math.h>
#include "snapkit.h"

static int tests_run = 0;
static int tests_pass = 0;

#define ASSERT(cond, msg) do { \
    tests_run++; \
    if (cond) { tests_pass++; } \
    else { printf("  FAIL: %s\n", msg); } \
} while(0)

#define ASSERT_FEQ(a, b, eps, msg) ASSERT(fabs((a)-(b)) < (eps), msg)
#define ASSERT_EQ(a, b, msg) ASSERT((a) == (b), msg)

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int main(void) {
    printf("Spectral tests\n");

    /* --- Entropy: uniform distribution --- */
    {
        double data[100];
        for (int i = 0; i < 100; i++) data[i] = (double)i;
        double h = sk_entropy(data, 100, 10);
        /* Uniform: entropy ≈ log2(10) ≈ 3.32 */
        printf("  Uniform entropy: %.4f (expected ~3.32)\n", h);
        ASSERT(h > 3.0 && h < 3.5, "uniform entropy ≈ log2(bins)");
    }

    /* --- Entropy: constant signal --- */
    {
        double data[50];
        for (int i = 0; i < 50; i++) data[i] = 5.0;
        double h = sk_entropy(data, 50, 10);
        ASSERT_FEQ(h, 0.0, 1e-12, "constant signal has zero entropy");
    }

    /* --- Entropy: single value dominates --- */
    {
        double data[10] = {0,0,0,0,0,0,0,0,0,1};
        double h = sk_entropy(data, 10, 2);
        ASSERT(h < 1.0, "skewed distribution has low entropy");
    }

    /* --- Autocorrelation: lag-0 is always 1 --- */
    {
        double data[50];
        for (int i = 0; i < 50; i++) data[i] = sin(i * 0.1);
        double acf[26];
        int len = sk_autocorrelation(data, 50, 25, acf);
        ASSERT_EQ(len, 26, "acf length = max_lag+1");
        ASSERT_FEQ(acf[0], 1.0, 1e-9, "acf[0] = 1.0");
    }

    /* --- Autocorrelation: constant signal --- */
    {
        double data[20];
        for (int i = 0; i < 20; i++) data[i] = 3.0;
        double acf[11];
        int len = sk_autocorrelation(data, 20, 10, acf);
        ASSERT_FEQ(acf[0], 1.0, 1e-12, "constant acf[0] = 1.0");
        /* All other lags should be 0 */
        bool all_zero = true;
        for (int i = 1; i < len; i++) {
            if (fabs(acf[i]) > 1e-12) all_zero = false;
        }
        ASSERT(all_zero, "constant acf: all lags > 0 are 0");
    }

    /* --- Autocorrelation: periodic signal has peaks at period --- */
    {
        double data[200];
        int period = 10;
        for (int i = 0; i < 200; i++) data[i] = sin(2.0 * M_PI * i / period);
        double acf[51];
        sk_autocorrelation(data, 200, 50, acf);
        /* At lag=period, should be close to 1.0 */
        ASSERT(acf[period] > 0.8, "periodic acf peaks at period");
    }

    /* --- Hurst: trended signal (should be > 0.5) --- */
    {
        /* Generate a trending series */
        double data[200];
        for (int i = 0; i < 200; i++) {
            data[i] = (double)i * 0.1 + sin(i * 0.3);
        }
        double h = sk_hurst_exponent(data, 200);
        printf("  Hurst (trending): %.4f\n", h);
        ASSERT(h > 0.5, "trending series Hurst > 0.5");
    }

    /* --- Hurst: short data returns 0.5 --- */
    {
        double data[5] = {1,2,3,4,5};
        double h = sk_hurst_exponent(data, 5);
        ASSERT_FEQ(h, 0.5, 1e-12, "short data Hurst = 0.5");
    }

    /* --- Spectral summary --- */
    {
        double data[100];
        for (int i = 0; i < 100; i++) data[i] = sin(i * 0.3) + 0.1 * sin(i * 2.7);
        double acf_buf[51];
        int counts_buf[10];
        sk_spectral_summary s = sk_spectral_analyze(data, 100, 10, 50,
                                                     acf_buf, counts_buf);
        printf("  Summary: entropy=%.3f hurst=%.3f lag1=%.3f decay=%.1f stationary=%d\n",
               s.entropy_bits, s.hurst, s.autocorr_lag1,
               s.autocorr_decay, s.is_stationary);
        ASSERT(s.entropy_bits > 0, "entropy > 0");
        ASSERT(s.hurst >= 0.0 && s.hurst <= 1.0, "Hurst in [0,1]");
    }

    /* --- Batch spectral --- */
    {
        double s1[50], s2[50];
        for (int i = 0; i < 50; i++) {
            s1[i] = sin(i * 0.2);
            s2[i] = cos(i * 0.3);
        }
        const double *series[] = {s1, s2};
        int lengths[] = {50, 50};
        sk_spectral_summary out[2];
        double acf_buf[26];
        int counts_buf[10];
        sk_spectral_batch(series, lengths, 2, 10, 25,
                          out, acf_buf, 26, counts_buf);
        ASSERT(out[0].hurst >= 0.0 && out[0].hurst <= 1.0, "batch[0] hurst valid");
        ASSERT(out[1].hurst >= 0.0 && out[1].hurst <= 1.0, "batch[1] hurst valid");
    }

    printf("  %d/%d passed\n", tests_pass, tests_run);
    return (tests_pass == tests_run) ? 0 : 1;
}
