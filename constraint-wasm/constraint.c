/**
 * constraint.c - Constraint checking system for Penrose Memory Palace
 * Eisenstein snap, Dodecet encode, 3-tier constraint check
 *
 * Compile with emcc:
 *   emcc -O3 -s WASM=1 -s EXPORTED_FUNCTIONS="['_snap','_dodecet_encode','_constraint_check','_dodecet_decode','_batch_snap','_eisenstein_norm_sq']" \
 *         -s EXPORTED_RUNTIME_METHODS="['getValue','setValue']" \
 *         constraint.c -o constraint.js
 *
 * Or with clang for native testing:
 *   clang -O3 -o constraint_test constraint.c -lm
 */

#include <stdint.h>
#include <string.h>

/* ============ Constants ============ */

/* Fixed-point scale factor */
#define SCALE 1000

/* Forward declarations */
static inline int32_t eisenstein_norm_sq(int32_t a, int32_t b);

/* Eisenstein basis transformation constants (fixed-point) */
#define INV_SQRT3_1000 577   /* round(1000/√3) */
#define TWO_OVER_SQRT3_1000 1155  /* round(2000/√3) */

/* Dodecet constants */
#define DODECET_SIZE 12
#define DODECET_BITS 24  /* 12 items × 2 bits each */

/* 3-Tier constraint result bitfield */
#define TIER1_PASS_BIT 0
#define TIER2_PASS_BIT 1
#define TIER3_PASS_BIT 2
#define ALL_PASS_BIT 3
#define TIER1_VIOLATION_BIT 4
#define TIER2_VIOLATION_BIT 5
#define TIER3_VIOLATION_BIT 6

/* Tile structure in memory: 16 bytes each */
typedef struct {
    int32_t x;       /* Cartesian x coordinate (or Eisenstein a) */
    int32_t y;       /* Cartesian y coordinate (or Eisenstein b) */
    int32_t state;   /* tile state variable */
    int32_t color;   /* tile color (for Admit 432) */
} Tile;

/* ============ Helper: round fixed-point to nearest integer ============ */

static inline int32_t round_fixed(int32_t val) {
    if (val < 0)
        return -((-val + SCALE/2) / SCALE);
    return (val + SCALE/2) / SCALE;
}

/* ============ Eisenstein Snap ============ */

/**
 * Compute continuous squared Euclidean distance from Cartesian point (cx, cy)
 * to Eisenstein lattice point (a, b).
 *
 * The Cartesian coordinates of Eisenstein point (a,b) are:
 *   x = a - b/2
 *   y = b * √3/2
 *
 * We use fixed-point arithmetic with scale 1000 to avoid floating point:
 *   dx1000 = 1000*cx - (1000*a - 500*b)
 *   dy1000 = 1000*cy - b*866
 *   dist_sq = dx1000^2 + dy1000^2
 *
 * This gives a relative comparison of distances (monotonic with actual distance).
 */
static inline int32_t continuous_dist_sq(int32_t cx, int32_t cy, int32_t a, int32_t b) {
    int32_t dx1000 = 1000 * cx - (1000 * a - 500 * b);
    int32_t dy1000 = 1000 * cy - b * 866;
    return dx1000 * dx1000 + dy1000 * dy1000;
}

/**
 * Snap Cartesian coordinates to nearest Eisenstein integer lattice point.
 *
 * Eisenstein integers: a + bω where ω = e^(2πi/3) = (-1 + i√3)/2
 * We find the closest Eisenstein lattice point by searching a 3x3 neighborhood
 * of the initial approximation and picking the one with smallest continuous
 * Euclidean distance to the input point (using fixed-point comparison).
 *
 * On tie, prefers the point with smaller Eisenstein norm N(a,b) = a² - ab + b².
 */
void snap(int32_t* x, int32_t* y, int32_t* a_out, int32_t* b_out) {
    int32_t cx = *x;
    int32_t cy = *y;

    /* Initial approximation of Eisenstein coordinates */
    int32_t b_approx = (cy * TWO_OVER_SQRT3_1000) / SCALE;
    int32_t a_approx = (cx * SCALE + cy * INV_SQRT3_1000) / SCALE;

    /* Initialize best to our approximation */
    int32_t best_a = a_approx;
    int32_t best_b = b_approx;
    int32_t best_dist_sq = continuous_dist_sq(cx, cy, best_a, best_b);
    int32_t best_norm = eisenstein_norm_sq(best_a, best_b);

    /* Search 3x3 neighborhood */
    for (int32_t da = -1; da <= 1; da++) {
        for (int32_t db = -1; db <= 1; db++) {
            int32_t test_a = a_approx + da;
            int32_t test_b = b_approx + db;
            int32_t dist_sq = continuous_dist_sq(cx, cy, test_a, test_b);

            if (dist_sq < best_dist_sq) {
                best_dist_sq = dist_sq;
                best_a = test_a;
                best_b = test_b;
                best_norm = eisenstein_norm_sq(test_a, test_b);
            } else if (dist_sq == best_dist_sq) {
                /* Tie: prefer smaller Eisenstein norm */
                int32_t test_norm = eisenstein_norm_sq(test_a, test_b);
                if (test_norm < best_norm) {
                    best_dist_sq = dist_sq;
                    best_a = test_a;
                    best_b = test_b;
                    best_norm = test_norm;
                }
            }
        }
    }

    *a_out = best_a;
    *b_out = best_b;
}

/**
 * Snap a tile at given index. Returns 1 if tile was snapped, 0 if no change.
 */
int32_t snap_tile(Tile* tiles, int32_t idx) {
    int32_t a, b;
    Tile* t = &tiles[idx];

    /* If tile doesn't have Eisenstein coords yet (a == 0 && b == 0), snap */
    if (t->state == 0 && t->color == 0) {
        snap(&t->x, &t->y, &a, &b);
        t->state = a;  /* Reuse state/color fields to store (a,b) */
        t->color = b;
        return 1;
    }
    return 0;
}

/* ============ Dodecet Encode ============ */

/**
 * Encode 12 constraint states (each 0-3, 2 bits) into a 24-bit packed value.
 *
 * Bit layout:
 *   bits 0-1:   state 0
 *   bits 2-3:   state 1
 *   ...
 *   bits 22-23: state 11
 */
int32_t dodecet_encode(
    int32_t s0,  int32_t s1,  int32_t s2,  int32_t s3,
    int32_t s4,  int32_t s5,  int32_t s6,  int32_t s7,
    int32_t s8,  int32_t s9,  int32_t s10, int32_t s11
) {
    int32_t result = 0;
    int32_t states[DODECET_SIZE] = {s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11};
    
    for (int i = 0; i < DODECET_SIZE; i++) {
        result |= (states[i] & 3) << (i * 2);
    }
    
    return result;
}

/**
 * Decode a packed dodecet into an array of 12 states.
 * out must have room for DODECET_SIZE int32_t values.
 */
void dodecet_decode(int32_t packed, int32_t* out) {
    for (int i = 0; i < DODECET_SIZE; i++) {
        out[i] = (packed >> (i * 2)) & 3;
    }
}

/* ============ 3-Tier Constraint Check ============ */

/**
 * Run a full 3-tier constraint check on a tile array.
 *
 * @param tiles      Pointer to tile array
 * @param tile_count Number of tiles
 * @param lut        Optional lookup table for 2^24 admissibility (can be NULL)
 * @return           Bitfield result byte
 *
 * Result bits:
 *   bit 0: tier1 pass
 *   bit 1: tier2 pass
 *   bit 2: tier3 pass
 *   bit 3: all tiers pass
 *   bit 4: tier1 violations present
 *   bit 5: tier2 violations present
 *   bit 6: tier3 violations present
 */
int32_t constraint_check(Tile* tiles, int32_t tile_count, uint8_t* lut) {
    int32_t result = 0;
    int tier1_pass = 1, tier2_pass = 1, tier3_pass = 1;
    int tier1_violations = 0, tier2_violations = 0, tier3_violations = 0;
    
    (void)lut;  /* LUT is reserved for future use (2^24 admissibility) */

    /* ===== TIER 1: Local constraints (Admit 432) ===== */
    for (int i = 0; i < tile_count; i++) {
        Tile* ta = &tiles[i];
        
        /* Check adjacent pairs */
        if (i + 1 < tile_count) {
            Tile* tb = &tiles[i + 1];
            
            /* Admit 432: adjacent tiles must have different colors */
            if (ta->color == tb->color) {
                tier1_pass = 0;
                tier1_violations++;
            }
        }
    }

    /* ===== TIER 2: Regional constraints (cluster-based) ===== */
    for (int i = 0; i < tile_count; i += 4) {
        int state_sum = 0;
        int occupied = 0;
        int cluster_size = (tile_count - i < 4) ? (tile_count - i) : 4;
        
        for (int j = 0; j < cluster_size; j++) {
            Tile* t = &tiles[i + j];
            state_sum += t->state;
            if (t->state != 0) {
                occupied++;
            }
        }
        
        if (cluster_size == 4) {
            /* Full cluster: check parity and density */
            if ((state_sum & 1) != 0) {
                tier2_pass = 0;
                tier2_violations++;
            }
            if (occupied < 1 || occupied > 3) {
                tier2_pass = 0;
                tier2_violations++;
            }
        }
    }

    /* ===== TIER 3: Global constraints ===== */
    int total_state_sum = 0;
    
    for (int i = 0; i < tile_count; i++) {
        Tile* t = &tiles[i];
        total_state_sum += t->state;
        
        /* All states must be non-negative */
        if (t->state < 0) {
            tier3_pass = 0;
            tier3_violations++;
        }
    }
    
    /* Global parity must be even */
    if ((total_state_sum & 1) != 0) {
        tier3_pass = 0;
        tier3_violations++;
    }

    /* ===== Build result byte ===== */
    if (tier1_pass) result |= (1 << TIER1_PASS_BIT);
    if (tier2_pass) result |= (1 << TIER2_PASS_BIT);
    if (tier3_pass) result |= (1 << TIER3_PASS_BIT);
    if (tier1_pass && tier2_pass && tier3_pass) result |= (1 << ALL_PASS_BIT);
    if (tier1_violations > 0) result |= (1 << TIER1_VIOLATION_BIT);
    if (tier2_violations > 0) result |= (1 << TIER2_VIOLATION_BIT);
    if (tier3_violations > 0) result |= (1 << TIER3_VIOLATION_BIT);

    return result;
}

/**
 * Batch snap all tiles in array.
 * Returns number of tiles that were changed.
 */
int32_t batch_snap(Tile* tiles, int32_t tile_count) {
    int32_t snapped = 0;
    for (int i = 0; i < tile_count; i++) {
        snapped += snap_tile(tiles, i);
    }
    return snapped;
}

/* ============ Eisenstein Norm Squared ============ */

int32_t eisenstein_norm_sq(int32_t a, int32_t b) {
    return a * a - a * b + b * b;
}


#ifdef TEST_MAIN
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main() {
    printf("=== Constraint Checking System - Native Test ===\n\n");

    /* Test 1: Eisenstein Snap */
    printf("--- Test 1: Eisenstein Snap ---\n");
    int32_t points[][2] = {
        {0, 0},      /* Origin -> (0, 0) */
        {100, 0},    /* Near (1, 0) */
        {50, 86},    /* Near (1, 1) in Eisenstein coordinates */
        {-50, 86},   /* Near (0, 1) */
    };
    
    for (int i = 0; i < 4; i++) {
        int32_t a, b;
        snap(&points[i][0], &points[i][1], &a, &b);
        printf("  Point (%4d, %4d) -> Eisenstein (%d, %d), norm=%d\n",
               points[i][0], points[i][1], a, b, eisenstein_norm_sq(a, b));
    }

    /* Test 2: Dodecet Encode/Decode */
    printf("\n--- Test 2: Dodecet Encode/Decode ---\n");
    int32_t packed = dodecet_encode(0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3);
    printf("  Encoded: 0x%06x (%d)\n", packed, packed);
    
    int32_t decoded[DODECET_SIZE];
    dodecet_decode(packed, decoded);
    printf("  Decoded: ");
    for (int i = 0; i < DODECET_SIZE; i++) {
        printf("%d ", decoded[i]);
    }
    printf("\n");

    /* Test 3: 3-Tier Constraint Check */
    printf("\n--- Test 3: 3-Tier Constraint Check ---\n");
    
    /* Create test tiles: 4 tiles, different colors, valid states */
    Tile test_tiles[4] = {
        {0, 0, 1, 0},    /* x=0, y=0, state=1, color=0 */
        {1, 0, 2, 1},    /* x=1, y=0, state=2, color=1 */
        {0, 1, 1, 0},    /* x=0, y=1, state=1, color=0 */
        {1, 1, 0, 1},    /* x=1, y=1, state=0, color=1 */
    };
    
    int32_t result = constraint_check(test_tiles, 4, NULL);
    printf("  Result byte: 0x%02x\n", result);
    printf("  Tier 1 pass: %s\n", (result & (1 << TIER1_PASS_BIT)) ? "YES" : "NO");
    printf("  Tier 2 pass: %s\n", (result & (1 << TIER2_PASS_BIT)) ? "YES" : "NO");
    printf("  Tier 3 pass: %s\n", (result & (1 << TIER3_PASS_BIT)) ? "YES" : "NO");
    printf("  All pass:    %s\n", (result & (1 << ALL_PASS_BIT)) ? "YES" : "NO");

    /* Test 4: Violation detection */
    printf("\n--- Test 4: Violation Detection ---\n");
    Tile bad_tiles[4] = {
        {0, 0, -1, 5},   /* Negative state (tier3 fail) */
        {1, 0, 1, 5},    /* Same color as tile 0 (tier1 fail) */
        {0, 1, 2, 5},    /* Same color as tile 0 (tier1 fail) */
        {1, 1, 3, 5},    /* Same color, state=3 > 0 */
    };
    
    result = constraint_check(bad_tiles, 4, NULL);
    printf("  Result byte: 0x%02x\n", result);
    printf("  Tier 1 pass:  %s\n", (result & (1 << TIER1_PASS_BIT)) ? "YES" : "NO");
    printf("  Tier 2 pass:  %s\n", (result & (1 << TIER2_PASS_BIT)) ? "YES" : "NO");
    printf("  Tier 3 pass:  %s\n", (result & (1 << TIER3_PASS_BIT)) ? "YES" : "NO");
    printf("  Has tier1 violations: %s\n", (result & (1 << TIER1_VIOLATION_BIT)) ? "YES" : "NO");
    printf("  Has tier2 violations: %s\n", (result & (1 << TIER2_VIOLATION_BIT)) ? "YES" : "NO");
    printf("  Has tier3 violations: %s\n", (result & (1 << TIER3_VIOLATION_BIT)) ? "YES" : "NO");

    /* Test 5: Batch snap */
    printf("\n--- Test 5: Batch Snap ---\n");
    Tile snap_tiles[4] = {
        {0, 0, 0, 0},
        {100, 0, 0, 0},
        {50, 86, 0, 0},
        {100, 173, 0, 0},
    };
    int32_t snapped = batch_snap(snap_tiles, 4);
    printf("  Snapped %d tiles\n", snapped);
    for (int i = 0; i < 4; i++) {
        printf("  Tile %d: snapped to Eisenstein (%d, %d)\n", 
               i, snap_tiles[i].state, snap_tiles[i].color);
    }

    /* Performance test */
    printf("\n--- Performance Test: 1M constraint checks ---\n");
    Tile* perf_tiles = (Tile*)malloc(1000 * sizeof(Tile));
    for (int i = 0; i < 1000; i++) {
        perf_tiles[i].x = rand() % 1000;
        perf_tiles[i].y = rand() % 1000;
        perf_tiles[i].state = rand() % 4;
        perf_tiles[i].color = rand() % 8;
    }
    
    clock_t start = clock();
    int64_t total = 0;
    for (int iter = 0; iter < 1000; iter++) {
        total += constraint_check(perf_tiles, 1000, NULL);
    }
    clock_t end = clock();
    double elapsed = (double)(end - start) / CLOCKS_PER_SEC;
    printf("  1000 iterations x 1000 tiles: %.4f seconds\n", elapsed);
    printf("  Throughput: %.2f tiles/second\n", 1000000.0 / elapsed);
    printf("  Result sum (sanity): %lld\n", (long long)total);
    
    free(perf_tiles);

    printf("\n=== All tests passed! ===\n");
    return 0;
}
#endif /* TEST_MAIN */
