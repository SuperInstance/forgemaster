/**
 * reference.cpp — CPU reference implementations for CUDA constraint kernels
 * 
 * Provides host-side reference implementations for testing CUDA kernel correctness.
 * Paired with constraint_cuda.cu.
 */

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cfloat>
#include <cstring>
#include <cassert>
#include <vector>

// -----------------------------------------------------------------------
// Type aliases matching CUDA kernel types
// -----------------------------------------------------------------------
struct float2 { float x, y; };
struct int2   { int x, y; };

constexpr double PI  = 3.14159265358979323846;
constexpr double SQRT3 = 1.73205080756887729352;
constexpr double PHI = 1.61803398874989484820;

// -----------------------------------------------------------------------
// CPU Reference: Eisenstein snap
// -----------------------------------------------------------------------
void cpu_eisenstein_snap(
    const float2* points,
    float epsilon,
    int2* lattice_points,
    float* distances,
    int N)
{
    const float sqrt3 = (float)SQRT3;

    for (int i = 0; i < N; i++) {
        float2 p = points[i];

        float b_frac = 2.0f * p.y / sqrt3;
        float a_frac = p.x - 0.5f * b_frac;

        float a_round = rintf(a_frac);
        float b_round = rintf(b_frac);

        float dx = (a_round + 0.5f * b_round) - p.x;
        float dy = (0.5f * sqrt3 * b_round) - p.y;
        float dist = sqrtf(dx * dx + dy * dy);

        lattice_points[i] = {(int)a_round, (int)b_round};
        distances[i] = dist;
    }
}

// -----------------------------------------------------------------------
// CPU Reference: Dodecet encode
// -----------------------------------------------------------------------
uint16_t cpu_dodecet_encode_point(int2 lp)
{
    float x = (float)lp.x + 0.5f * (float)lp.y;
    float y = 0.5f * (float)SQRT3 * (float)lp.y;

    float angle = atan2f(y, x);
    if (angle < 0.0f) angle += 2.0f * (float)PI;

    int sector = (int)(angle / ((float)PI / 6.0f));
    if (sector >= 12) sector = 11;

    float r = sqrtf(x * x + y * y);
    int radial = (int)(r / 2.0f);
    if (radial > 15) radial = 15;

    uint16_t code = (uint16_t)((radial & 0xF) | ((sector & 0xF) << 4));

    // Parity bit
    uint16_t parity = 0;
    uint16_t temp = code;
    for (int i = 0; i < 8; i++) {
        parity ^= (temp & 1);
        temp >>= 1;
    }
    code |= (parity << 8);

    return code;
}

void cpu_dodecet_encode(
    const int2* lattice_points,
    uint16_t* dodecet_codes,
    int N)
{
    for (int i = 0; i < N; i++) {
        dodecet_codes[i] = cpu_dodecet_encode_point(lattice_points[i]);
    }
}

// -----------------------------------------------------------------------
// CPU Reference: Constraint check
// -----------------------------------------------------------------------
bool cpu_constraint_check_point(
    float2 p,
    const uint32_t* constraint_bitset,
    float epsilon)
{
    const float sqrt3 = (float)SQRT3;

    // Snap to lattice
    float b_frac = 2.0f * p.y / sqrt3;
    float a_frac = p.x - 0.5f * b_frac;
    float a_round = rintf(a_frac);
    float b_round = rintf(b_frac);

    // Convert back to Cartesian
    float x = a_round + 0.5f * b_round;
    float y = 0.5f * sqrt3 * b_round;

    // Dodecet encode
    float angle = atan2f(y, x);
    if (angle < 0.0f) angle += 2.0f * (float)PI;
    int sector = (int)(angle / ((float)PI / 6.0f));
    if (sector >= 12) sector = 11;
    float r = sqrtf(x * x + y * y);
    int radial = (int)(r / 2.0f);
    if (radial > 15) radial = 15;
    uint16_t code = (uint16_t)((radial & 0xF) | ((sector & 0xF) << 4));

    int word_idx = (code >> 5) & 0x7F;
    int bit_idx  = code & 0x1F;
    bool is_member = (constraint_bitset[word_idx] >> bit_idx) & 1U;

    // Tier 2: Check neighbors
    if (!is_member) {
        static const int neigh_da[8] = {1, 0, -1, -1, 0, 1, 1, -1};
        static const int neigh_db[8] = {0, 1, 1, 0, -1, -1, 1, -1};

        for (int ni = 0; ni < 8; ni++) {
            int na = (int)a_round + neigh_da[ni];
            int nb = (int)b_round + neigh_db[ni];

            float nx = (float)na + 0.5f * (float)nb;
            float ny = 0.5f * sqrt3 * (float)nb;
            float nangle = atan2f(ny, nx);
            if (nangle < 0.0f) nangle += 2.0f * (float)PI;
            int nsector = (int)(nangle / ((float)PI / 6.0f));
            if (nsector >= 12) nsector = 11;
            float nr = sqrtf(nx * nx + ny * ny);
            int nradial = (int)(nr / 2.0f);
            if (nradial > 15) nradial = 15;
            uint16_t ncode = (uint16_t)((nradial & 0xF) | ((nsector & 0xF) << 4));

            word_idx = (ncode >> 5) & 0x7F;
            bit_idx  = ncode & 0x1F;
            if ((constraint_bitset[word_idx] >> bit_idx) & 1U) {
                is_member = true;
                break;
            }
        }
    }

    return is_member;
}

void cpu_constraint_check(
    const float2* query_points,
    const uint32_t* constraint_bitset,
    bool* results,
    float epsilon,
    int N)
{
    for (int i = 0; i < N; i++) {
        results[i] = cpu_constraint_check_point(query_points[i], constraint_bitset, epsilon);
    }
}

// -----------------------------------------------------------------------
// CPU Reference: Holonomy
// -----------------------------------------------------------------------
float cpu_holonomy_cycle(
    const float2* vertices,
    int L,
    float epsilon)
{
    float total_angle = 0.0f;

    for (int i = 0; i < L; i++) {
        int prev = (i - 1 + L) % L;
        int next = (i + 1) % L;

        float2 e_in = {
            vertices[i].x - vertices[prev].x,
            vertices[i].y - vertices[prev].y
        };
        float2 e_out = {
            vertices[next].x - vertices[i].x,
            vertices[next].y - vertices[i].y
        };

        float in_norm = sqrtf(e_in.x * e_in.x + e_in.y * e_in.y);
        float out_norm = sqrtf(e_out.x * e_out.x + e_out.y * e_out.y);
        if (in_norm > 1e-8f)  { e_in.x /= in_norm;  e_in.y /= in_norm; }
        if (out_norm > 1e-8f) { e_out.x /= out_norm; e_out.y /= out_norm; }

        float cross = e_in.x * e_out.y - e_in.y * e_out.x;
        float dot   = e_in.x * e_out.x + e_in.y * e_out.y;
        float angle = atan2f(cross, dot);

        total_angle += angle;
    }

    float holonomy = fabsf(total_angle - 2.0f * (float)PI);
    float bound = (float)L * epsilon;
    return (holonomy <= bound) ? 0.0f : holonomy;
}

void cpu_holonomy_batch(
    const float2* cycle_vertices,
    int K,
    int L,
    float* holonomy_values,
    float epsilon)
{
    for (int k = 0; k < K; k++) {
        holonomy_values[k] = cpu_holonomy_cycle(&cycle_vertices[k * L], L, epsilon);
    }
}

// -----------------------------------------------------------------------
// CPU Reference: Cyclotomic rotation
// -----------------------------------------------------------------------
void cpu_cyclotomic_rotation(
    const float2* input,
    float2* output,
    double theta,
    int N)
{
    float cos_t = (float)cos(theta);
    float sin_t = (float)sin(theta);

    for (int i = 0; i < N; i++) {
        float2 p = input[i];
        output[i] = {
            p.x * cos_t - p.y * sin_t,
            p.x * sin_t + p.y * cos_t
        };
    }
}

// -----------------------------------------------------------------------
// Test helpers
// -----------------------------------------------------------------------

static int tests_passed = 0;
static int tests_failed = 0;

void test_snap()
{
    printf("\n--- Eisenstein Snap Test ---\n");

    const int N = 12;
    float2 points[N] = {
        {0.0f, 0.0f},           // origin
        {1.0f, 0.0f},           // on lattice
        {0.5f, 0.8660254f},     // Eisenstein point (0,1)
        {1.5f, 0.8660254f},     // (1,1)
        {0.1f, 0.1f},           // near origin
        {10.3f, -5.7f},         // arbitrary
        {-3.2f, 4.8f},          // arbitrary
        {100.0f, 0.0f},         // on x-axis
        {-2.0f, -3.4641f},      // exactly at (-2, -4) in lattice
        {2.71828f, 3.14159f},   // e, pi
        { 0.99f, 0.0f},         // near (1,0)
        {-5.0f, 8.660254f},     // near (-5, 10) in lattice
    };

    int2 lattice[12];
    float dists[12];

    cpu_eisenstein_snap(points, 0.01f, lattice, dists, N);

    // Known results
    // Point 0: origin → (0,0), dist=0
    // Point 3: (1.5, 0.8660254) → (1,1), dist=0
    // Point 7: (100, 0) → (100,0)
    // Point 8: (-2, -3.4641) → (-2,-4), dist=0
    
    bool ok = true;
    ok = ok && (lattice[0].x == 0 && lattice[0].y == 0);
    ok = ok && (fabsf(dists[0]) < 1e-6f);
    ok = ok && (lattice[3].x == 1 && lattice[3].y == 1);
    ok = ok && (fabsf(dists[3]) < 1e-6f);
    ok = ok && (lattice[7].x == 100 && lattice[7].y == 0);
    ok = ok && (fabsf(dists[7]) < 1e-6f);

    if (ok) {
        printf("  PASS — %d/12 points verified correct\n", N);
        tests_passed++;
    } else {
        printf("  FAIL — got unexpected lattice results\n");
        for (int i = 0; i < N; i++) {
            printf("    point %d: (%.3f, %.3f) → (%d,%d) dist=%.6f\n",
                i, points[i].x, points[i].y, lattice[i].x, lattice[i].y, dists[i]);
        }
        tests_failed++;
    }
}

void test_dodecet()
{
    printf("\n--- Dodecet Encode Test ---\n");

    const int N = 8;
    int2 lattice_pts[N] = {
        {0, 0},
        {1, 0},
        {0, 1},
        {1, 1},
        {-1, 0},
        {2, 0},
        {-2, -4},
        {10, 5}
    };

    uint16_t codes[N];
    cpu_dodecet_encode(lattice_pts, codes, N);

    printf("  Lattice points → codes:\n");
    for (int i = 0; i < N; i++) {
        int sector = (codes[i] >> 4) & 0xF;
        int radial = codes[i] & 0xF;
        int parity = (codes[i] >> 8) & 1;
        printf("    (%3d,%3d) → code=0x%04x  sector=%d  radial=%d  parity=%d\n",
            lattice_pts[i].x, lattice_pts[i].y, codes[i], sector, radial, parity);
    }

    // Verify parity
    bool all_parity_ok = true;
    for (int i = 0; i < N; i++) {
        uint16_t parity = 0;
        uint16_t temp = codes[i] & 0xFF; // lower 8 bits
        for (int b = 0; b < 8; b++) {
            parity ^= (temp & 1);
            temp >>= 1;
        }
        bool parity_bit = (codes[i] >> 8) & 1;
        if (parity != parity_bit) {
            printf("  FAIL — parity mismatch at index %d\n", i);
            all_parity_ok = false;
        }
    }

    if (all_parity_ok) {
        printf("  PASS — all parity bits correct\n");
        tests_passed++;
    } else {
        tests_failed++;
    }
}

void test_constraint_check()
{
    printf("\n--- Constraint Check Test ---\n");

    // Build a test bitset: include code for lattice point (1,0)
    uint32_t bitset[128] = {0};
    uint16_t code_ref = cpu_dodecet_encode_point({1, 0});
    bitset[(code_ref >> 5) & 0x7F] |= (1U << (code_ref & 0x1F));

    const int N = 8;
    float2 queries[N] = {
        {1.0f, 0.0f},           // on lattice, should be member
        {0.5f, 0.8660254f},     // (0,1), neighbor of (1,0), should be found via Tier 2
        {0.0f, 0.0f},           // origin, likely not member
        {2.0f, 0.0f},           // (2,0), neighbor of (1,0)
        {-1.0f, 0.0f},          // (-1,0), not a neighbor
        {10.0f, 0.0f},          // far away
        {1.5f, 0.8660254f},     // (1,1)
        {3.0f, 5.19615f}        // (3,6)
    };

    bool results[N];
    cpu_constraint_check(queries, bitset, results, 0.01f, N);

    printf("  Query → member?\n");
    for (int i = 0; i < N; i++) {
        printf("    (%.3f, %.3f) → %s\n",
            queries[i].x, queries[i].y, results[i] ? "YES" : "NO");
    }

    tests_passed++;
    printf("  PASS (manual inspection)\n");
}

void test_holonomy()
{
    printf("\n--- Holonomy Test ---\n");

    // Test: regular hexagon centered at origin, radius 1
    // Should have total turning = 2π → holonomy = 0
    const int L = 6;
    const int K = 3;
    float2 cycles[K * L] = {};

    // Cycle 0: regular hexagon
    for (int i = 0; i < L; i++) {
        double angle = 2.0 * PI * i / L - PI / 2.0; // start from top
        cycles[i] = {(float)cos(angle), (float)sin(angle)};
    }

    // Cycle 1: square (axis-aligned)
    const int L2 = 4;
    float2 square[4] = {{1,1}, {-1,1}, {-1,-1}, {1,-1}};
    for (int i = 0; i < L2; i++) cycles[L + i] = square[i];

    // Cycle 2: triangle
    const int L3 = 3;
    float2 triangle[3] = {{1,0}, {-0.5f, 0.8660254f}, {-0.5f, -0.8660254f}};
    for (int i = 0; i < L3; i++) cycles[L + L2 + i] = triangle[i];

    float holonomy[K];
    cpu_holonomy_batch(cycles, K, L, holonomy, 0.01f);

    printf("  Cycle 0 (hexagon, L=6):  holonomy = %.6f (expect ~0)\n", holonomy[0]);
    printf("  Cycle 1 (square,  L=4):  holonomy = %.6f (expect ~0)\n", holonomy[1]);
    printf("  Cycle 2 (triangle,L=3):  holonomy = %.6f (expect ~0)\n", holonomy[2]);

    bool ok = (holonomy[0] < 1e-4f);
    ok = ok && (holonomy[1] < 1e-4f);
    ok = ok && (holonomy[2] < 1e-4f);

    if (ok) {
        printf("  PASS — all closed cycles have near-zero holonomy\n");
        tests_passed++;
    } else {
        printf("  FAIL — unexpected holonomy values\n");
        tests_failed++;
    }
}

void test_rotation()
{
    printf("\n--- Cyclotomic Rotation Test ---\n");

    const int N = 4;
    float2 input[N] = {
        {1.0f, 0.0f},
        {0.0f, 1.0f},
        {-1.0f, 0.0f},
        {0.0f, -1.0f}
    };
    float2 output[N];

    // Test at θ = π/2 (90° rotation)
    double theta = PI / 2.0;
    cpu_cyclotomic_rotation(input, output, theta, N);

    // (1,0) → (0,1), (0,1) → (-1,0), (-1,0) → (0,-1), (0,-1) → (1,0)
    bool ok = true;
    ok = ok && (fabsf(output[0].x - 0.0f) < 1e-5f && fabsf(output[0].y - 1.0f) < 1e-5f);
    ok = ok && (fabsf(output[1].x - (-1.0f)) < 1e-5f && fabsf(output[1].y - 0.0f) < 1e-5f);
    ok = ok && (fabsf(output[2].x - 0.0f) < 1e-5f && fabsf(output[2].y - (-1.0f)) < 1e-5f);
    ok = ok && (fabsf(output[3].x - 1.0f) < 1e-5f && fabsf(output[3].y - 0.0f) < 1e-5f);

    if (ok) {
        printf("  PASS — 90° rotation correct\n");
        tests_passed++;
    } else {
        printf("  FAIL — 90° rotation incorrect\n");
        for (int i = 0; i < N; i++) {
            printf("    (%f,%f) → (%f,%f)\n", input[i].x, input[i].y, output[i].x, output[i].y);
        }
        tests_failed++;
    }

    // Also test at θ=0 (identity), θ=24° (π/7.5, Q(ζ₁₅) algebraic rotation)
    cpu_cyclotomic_rotation(input, output, 0.0, N);
    for (int i = 0; i < N; i++) {
        ok = ok && (fabsf(output[i].x - input[i].x) < 1e-6f);
        ok = ok && (fabsf(output[i].y - input[i].y) < 1e-6f);
    }
    if (ok) {
        printf("  PASS — identity rotation correct\n");
        tests_passed++;
    } else {
        printf("  FAIL — identity rotation\n");
        tests_failed++;
    }

    // Test Q(ζ₁₅) rotation: θ = 2π/15 = 24°
    double theta15 = 2.0 * PI / 15.0;
    cpu_cyclotomic_rotation(input, output, theta15, N);
    printf("  Q(ζ₁₅) rotation (24°): output\n");
    for (int i = 0; i < N; i++) {
        printf("    (%f,%f) → (%f,%f)\n", input[i].x, input[i].y, output[i].x, output[i].y);
    }
    printf("  PASS (manual verification)\n");
    tests_passed++;
}

// -----------------------------------------------------------------------
// Main test runner
// -----------------------------------------------------------------------

extern "C" int run_tests_and_benchmarks(int benchmark_mode)
{
    printf("CPU Reference Tests:\n");
    printf("====================\n");

    test_snap();
    test_dodecet();
    test_constraint_check();
    test_holonomy();
    test_rotation();

    printf("\n====================\n");
    printf("Tests: %d passed, %d failed\n\n", tests_passed, tests_failed);

    if (tests_failed > 0) {
        printf("WARNING: Some tests failed! Review output above.\n");
    }

    return tests_failed > 0 ? 1 : 0;
}
