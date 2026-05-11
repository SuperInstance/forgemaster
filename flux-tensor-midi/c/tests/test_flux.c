#include "flux_midi/flux.h"
#include <stdio.h>
#include <math.h>
#include <assert.h>

#define ASSERT_FEQ(a, b, eps) do { \
    double _a = (a), _b = (b), _eps = (eps); \
    if (fabs(_a - _b) > _eps) { \
        fprintf(stderr, "FAIL %s:%d: %.6f != %.6f (eps=%.6f)\n", \
                __FILE__, __LINE__, _a, _b, _eps); \
        return 1; \
    } \
} while(0)

int test_zero(void) {
    FluxVector v;
    flux_zero(&v);
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        ASSERT_FEQ(v.channels[i].salience, 0.0, 1e-12);
        ASSERT_FEQ(v.channels[i].tolerance, 0.0, 1e-12);
    }
    printf("  PASS test_zero\n");
    return 0;
}

int test_uniform(void) {
    FluxVector v;
    flux_uniform(&v, 0.5, 0.8);
    for (int i = 0; i < FLUX_CHANNELS; i++) {
        ASSERT_FEQ(v.channels[i].salience, 0.5, 1e-12);
        ASSERT_FEQ(v.channels[i].tolerance, 0.8, 1e-12);
    }
    printf("  PASS test_uniform\n");
    return 0;
}

int test_distance(void) {
    FluxVector a, b;
    flux_zero(&a);
    flux_zero(&b);
    ASSERT_FEQ(flux_distance(&a, &b), 0.0, 1e-12);

    a.channels[0].salience = 1.0;
    ASSERT_FEQ(flux_distance(&a, &b), 1.0, 1e-12);

    b.channels[0].salience = 1.0;
    ASSERT_FEQ(flux_distance(&a, &b), 0.0, 1e-12);
    printf("  PASS test_distance\n");
    return 0;
}

int test_jaccard(void) {
    FluxVector a, b;
    flux_zero(&a);
    flux_zero(&b);
    /* Both all-zero = 1.0 (no active channels = perfect match by convention) */
    ASSERT_FEQ(flux_jaccard(&a, &b, 0.5), 1.0, 1e-12);

    a.channels[0].salience = 0.8;
    a.channels[1].salience = 0.9;
    b.channels[0].salience = 0.7;
    b.channels[2].salience = 0.6;
    /* a active: {0,1}, b active: {0,2}, intersection: {0}, union: {0,1,2} */
    ASSERT_FEQ(flux_jaccard(&a, &b, 0.5), 1.0 / 3.0, 1e-12);
    printf("  PASS test_jaccard\n");
    return 0;
}

int test_cosine(void) {
    FluxVector a, b;
    flux_zero(&a);
    flux_zero(&b);
    a.channels[0].salience = 1.0;
    b.channels[0].salience = 1.0;
    ASSERT_FEQ(flux_cosine(&a, &b), 1.0, 1e-12);

    b.channels[0].salience = 0.0;
    b.channels[1].salience = 1.0;
    ASSERT_FEQ(flux_cosine(&a, &b), 0.0, 1e-12);
    printf("  PASS test_cosine\n");
    return 0;
}

int test_blend(void) {
    FluxVector a, b, out;
    flux_zero(&a);
    flux_zero(&b);
    a.channels[0].salience = 1.0;
    b.channels[0].salience = 0.0;
    flux_blend(&a, &b, 0.5, &out);
    ASSERT_FEQ(out.channels[0].salience, 0.5, 1e-12);
    printf("  PASS test_blend\n");
    return 0;
}

int test_decay(void) {
    FluxVector v;
    flux_uniform(&v, 1.0, 1.0);
    flux_decay(&v, 0.9);
    ASSERT_FEQ(v.channels[0].salience, 0.9, 1e-12);
    printf("  PASS test_decay\n");
    return 0;
}

int test_set_get(void) {
    FluxVector v;
    flux_zero(&v);
    assert(flux_set(&v, 0, 0.7, 0.3) == 0);
    assert(flux_set(&v, -1, 0.0, 0.0) == -1);
    assert(flux_set(&v, 9, 0.0, 0.0) == -1);

    FluxChannel ch;
    assert(flux_get(&v, 0, &ch) == 0);
    ASSERT_FEQ(ch.salience, 0.7, 1e-12);
    ASSERT_FEQ(ch.tolerance, 0.3, 1e-12);
    assert(flux_get(&v, 9, &ch) == -1);
    printf("  PASS test_set_get\n");
    return 0;
}

int main(void) {
    printf("=== FLUX Vector Tests ===\n");
    int fails = 0;
    fails += test_zero();
    fails += test_uniform();
    fails += test_distance();
    fails += test_jaccard();
    fails += test_cosine();
    fails += test_blend();
    fails += test_decay();
    fails += test_set_get();
    printf(fails == 0 ? "All tests passed.\n" : "%d test(s) FAILED.\n", fails);
    return fails;
}
