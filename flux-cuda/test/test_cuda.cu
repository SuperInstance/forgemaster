/*
 * test_cuda.cu — FLUX CUDA test suite
 *
 * Tests: batch add, batch constraint check, CSP backtracking,
 *        sonar physics (GPU vs CPU Mackenzie), arc consistency
 */

#include "flux_cuda.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>

static int g_pass = 0;
static int g_fail = 0;

#define TEST(name) void test_##name()
#define RUN(name) do { \
    printf("  %-45s", #name); \
    fflush(stdout); \
    test_##name(); \
} while(0)

#define ASSERT(cond, msg) do { \
    if (!(cond)) { \
        printf("FAIL\n    %s:%d: %s\n", __FILE__, __LINE__, msg); \
        g_fail++; \
        return; \
    } \
} while(0)

#define ASSERT_EQ(a, b, msg) ASSERT((a) == (b), msg)
#define ASSERT_NEAR(a, b, eps, msg) ASSERT(fabs((a) - (b)) < (eps), msg)

#define PASS() do { printf("PASS\n"); g_pass++; } while(0)

/* ── CPU reference: Mackenzie 1981 ─────────────────────────── */
static double cpu_mackenzie(double D, double T, double S)
{
    return 1448.96
         + 4.591 * T
         - 5.304e-2 * T * T
         + 2.374e-4 * T * T * T
         + 1.340 * (S - 35.0)
         + 1.630e-2 * D
         + 1.675e-7 * D * D
         - 1.025e-2 * T * (S - 35.0)
         - 7.139e-13 * T * D * D * D;
}

/* ═══════════════════════════════════════════════════════════════
 *  test_batch_add — 1000 parallel additions
 *
 *  Each instance: LOAD(0), PUSH(const), ADD, STORE(0)
 *  Verifies all 1000 outputs == input + const
 * ═════════════════════════════════════════════════════════════ */

/* Opcodes */
#define OP_NOP   0x00
#define OP_PUSH  0x01
#define OP_LOAD  0x02
#define OP_STORE 0x03
#define OP_ADD   0x10
#define OP_HALT  0xFF

TEST(batch_add)
{
    const int N = 1000;
    const double ADDEND = 42.0;

    /* Build bytecode: LOAD(0), PUSH(42.0), ADD, STORE(0), HALT */
    uint8_t bytecode[1 + 1 + 1 + 8 + 1 + 1 + 1];
    size_t bc_len = 0;
    bytecode[bc_len++] = OP_LOAD;   // load input[0]
    bytecode[bc_len++] = 0;
    bytecode[bc_len++] = OP_PUSH;   // push 42.0
    memcpy(bytecode + bc_len, &ADDEND, sizeof(double));
    bc_len += sizeof(double);
    bytecode[bc_len++] = OP_ADD;
    bytecode[bc_len++] = OP_STORE;  // store to output[0]
    bytecode[bc_len++] = 0;
    bytecode[bc_len++] = OP_HALT;

    /* Inputs: 0..999 */
    double* inputs = new double[N];
    for (int i = 0; i < N; ++i) inputs[i] = (double)i;

    double* outputs = new double[N];
    int32_t* violations = new int32_t[N];

    flux_vm_batch_desc_t desc = {};
    desc.bytecode = bytecode;
    desc.bytecode_len = bc_len;
    desc.inputs = inputs;
    desc.inputs_per_instance = 1;
    desc.max_stack = 16;

    flux_vm_batch_result_t result = {};
    result.outputs = outputs;
    result.outputs_per_instance = 1;
    result.violation_flags = violations;

    flux_cuda_error_t err = flux_cuda_batch_execute(&desc, N, &result);
    ASSERT_EQ(err, FLUX_CUDA_OK, "batch_execute returned error");

    int ok = 1;
    for (int i = 0; i < N && ok; ++i) {
        if (violations[i] != 0) { ok = 0; break; }
        double expected = (double)i + ADDEND;
        if (fabs(outputs[i] - expected) > 1e-10) { ok = 0; break; }
    }
    ASSERT(ok, "output mismatch or violation");

    delete[] inputs;
    delete[] outputs;
    delete[] violations;
    PASS();
}

/* ═══════════════════════════════════════════════════════════════
 *  test_batch_constraint_check — 1000 parallel ASSERT operations
 *
 *  Bytecode: LOAD(0), PUSH(threshold), CMP_GT, ASSERT, STORE(0), HALT
 *  Half should pass (input > threshold), half should violate
 * ═════════════════════════════════════════════════════════════ */

#define OP_CMP_GT 0x23
#define OP_ASSERT 0x30

TEST(batch_constraint_check)
{
    const int N = 1000;
    const double THRESH = 500.0;

    uint8_t bytecode[32];
    size_t bc_len = 0;
    bytecode[bc_len++] = OP_LOAD;
    bytecode[bc_len++] = 0;
    bytecode[bc_len++] = OP_PUSH;
    memcpy(bytecode + bc_len, &THRESH, sizeof(double));
    bc_len += sizeof(double);
    bytecode[bc_len++] = OP_CMP_GT;
    bytecode[bc_len++] = OP_ASSERT;
    bytecode[bc_len++] = OP_STORE;
    bytecode[bc_len++] = 0;
    bytecode[bc_len++] = OP_HALT;

    double* inputs = new double[N];
    for (int i = 0; i < N; ++i) inputs[i] = (double)i;

    double* outputs = new double[N];
    int32_t* violations = new int32_t[N];

    flux_vm_batch_desc_t desc = {};
    desc.bytecode = bytecode;
    desc.bytecode_len = bc_len;
    desc.inputs = inputs;
    desc.inputs_per_instance = 1;
    desc.max_stack = 16;

    flux_vm_batch_result_t result = {};
    result.outputs = outputs;
    result.outputs_per_instance = 1;
    result.violation_flags = violations;

    flux_cuda_error_t err = flux_cuda_batch_execute(&desc, N, &result);
    ASSERT_EQ(err, FLUX_CUDA_OK, "batch_execute returned error");

    int expect_pass = 0, expect_fail = 0;
    int actual_pass = 0, actual_fail = 0;
    for (int i = 0; i < N; ++i) {
        if ((double)i > THRESH) { expect_pass++; if (violations[i] == 0) actual_pass++; }
        else                     { expect_fail++; if (violations[i] != 0) actual_fail++; }
    }
    ASSERT_EQ(actual_pass, expect_pass, "wrong number of passing constraints");
    ASSERT_EQ(actual_fail, expect_fail, "wrong number of violations");

    delete[] inputs;
    delete[] outputs;
    delete[] violations;
    PASS();
}

/* ═══════════════════════════════════════════════════════════════
 *  test_csp_backtracking_simple — 4-queen coloring
 *
 *  4 variables, domain {0,1,2} (3 colors), 6 constraints (all ≠)
 * ═════════════════════════════════════════════════════════════ */

TEST(csp_backtracking_simple)
{
    const int V = 4, MD = 3, C = 6, NP = 1;

    /* Domains: each variable has {0, 1, 2, -1} */
    int domains[V * MD];
    for (int v = 0; v < V; ++v) {
        domains[v * MD + 0] = 0;
        domains[v * MD + 1] = 1;
        domains[v * MD + 2] = 2;
    }

    /* Constraints: all pairs (alldiff) */
    int constraints[C * 2] = {
        0,1, 0,2, 0,3, 1,2, 1,3, 2,3
    };

    int solutions[V];
    int32_t solved = 0;

    flux_csp_problem_desc_t pdesc = {};
    pdesc.var_count = V;
    pdesc.max_domain_size = MD;
    pdesc.constraint_count = C;

    flux_csp_batch_t batch = {};
    batch.domains = domains;
    batch.constraints = constraints;
    batch.weights = nullptr;
    batch.solutions = solutions;
    batch.solved = &solved;

    flux_cuda_error_t err = flux_cuda_csp_solve(&pdesc, &batch, NP);
    ASSERT_EQ(err, FLUX_CUDA_OK, "csp_solve returned error");
    ASSERT_EQ(solved, 1, "CSP not solved");

    /* Verify all different */
    int used[4] = {-1,-1,-1,-1};
    for (int v = 0; v < V; ++v) {
        ASSERT(solutions[v] >= 0 && solutions[v] < MD, "solution out of domain");
        for (int u = 0; u < v; ++u) {
            ASSERT(solutions[u] != solutions[v], "constraint violated in solution");
        }
    }
    PASS();
}

/* ═══════════════════════════════════════════════════════════════
 *  test_sonar_physics_batch — GPU vs CPU Mackenzie comparison
 * ═════════════════════════════════════════════════════════════ */

TEST(sonar_physics_batch)
{
    const int N = 5000;
    double* depths  = new double[N];
    double* temps   = new double[N];
    double* salins  = new double[N];
    double* freqs   = new double[N];
    double* speeds  = new double[N];
    double* absorps = new double[N];

    for (int i = 0; i < N; ++i) {
        depths[i]  = (double)(i * 2);        /* 0..9998 m */
        temps[i]   = 2.0 + (i % 30);         /* 2..31 °C */
        salins[i]  = 33.0 + (i % 5);         /* 33..37 PSU */
        freqs[i]   = 1.0 + (i % 100) * 0.5;  /* 1..50.5 kHz */
    }

    flux_sonar_batch_t batch = {};
    batch.depths      = depths;
    batch.temps       = temps;
    batch.salinities  = salins;
    batch.freqs       = freqs;
    batch.sound_speeds  = speeds;
    batch.absorptions  = absorps;
    batch.count       = N;

    flux_cuda_error_t err = flux_cuda_sonar_physics(&batch);
    ASSERT_EQ(err, FLUX_CUDA_OK, "sonar_physics returned error");

    /* Compare first 100 against CPU reference */
    int ok = 1;
    for (int i = 0; i < 100 && ok; ++i) {
        double cpu_c = cpu_mackenzie(depths[i], temps[i], salins[i]);
        if (fabs(speeds[i] - cpu_c) > 0.01) {
            printf("Mismatch at %d: GPU=%.4f CPU=%.4f\n", i, speeds[i], cpu_c);
            ok = 0;
        }
    }
    ASSERT(ok, "GPU vs CPU sound speed mismatch");

    /* Sanity check: all speeds in plausible range */
    for (int i = 0; i < N && ok; ++i) {
        if (speeds[i] < 1400.0 || speeds[i] > 1600.0) {
            printf("Implausible speed at %d: %.4f\n", i, speeds[i]);
            ok = 0;
        }
        if (absorps[i] < 0.0 || absorps[i] > 1000.0) {
            printf("Implausible absorption at %d: %.4f\n", i, absorps[i]);
            ok = 0;
        }
    }
    ASSERT(ok, "implausible physics value");

    delete[] depths;
    delete[] temps;
    delete[] salins;
    delete[] freqs;
    delete[] speeds;
    delete[] absorps;
    PASS();
}

/* ═══════════════════════════════════════════════════════════════
 *  test_arc_consistency — simple domain pruning
 *
 *  2 variables: x ∈ {0,1,2}, y ∈ {1,2,3}
 *  Constraint: x ≠ y
 *  After AC: x ∈ {0}, y ∈ {1,2,3} → nope, x has support for {0,1,2}
 *  Actually with alldiff: x={0,1,2}, y={1,2,3}, x≠y
 *  y=1 supported by x∈{0,2}, y=2 supported by x∈{0,1}, y=3 supported by x∈{0,1,2}
 *  x=0 supported by y∈{1,2,3}, x=1 supported by y∈{2,3}, x=2 supported by y∈{1,3}
 *  → no pruning possible, all values have support.
 *
 *  Let's do: x ∈ {1}, y ∈ {1,2,3}, x ≠ y
 *  After AC: y ∈ {2,3} (1 pruned)
 * ═════════════════════════════════════════════════════════════ */

TEST(arc_consistency)
{
    const int V = 2, MD = 4, C = 1, NP = 1;

    int domains[V * MD] = {
        1, -1, -1, -1,    /* x = {1} */
        1,  2,  3, -1,    /* y = {1, 2, 3} */
    };

    int constraints[C * 2] = { 0, 1 };  /* x ≠ y */

    int32_t pruned[V] = {};

    flux_csp_problem_desc_t pdesc = {};
    pdesc.var_count = V;
    pdesc.max_domain_size = MD;
    pdesc.constraint_count = C;

    flux_arc_batch_t batch = {};
    batch.domains = domains;
    batch.pruned  = pruned;

    flux_cuda_error_t err = flux_cuda_arc_consistency(&pdesc, &batch, NP);
    ASSERT_EQ(err, FLUX_CUDA_OK, "arc_consistency returned error");

    /* After AC: y should have {2, 3} (value 1 pruned because x=1 and x≠y) */
    /* x domain unchanged: {1} */
    ASSERT_EQ(domains[0 * MD + 0], 1, "x domain changed incorrectly");

    /* y: 1 should be pruned (replaced with -1) */
    int y_has_1 = 0;
    for (int d = 0; d < MD; ++d) {
        if (domains[1 * MD + d] == 1) y_has_1 = 1;
    }
    ASSERT(!y_has_1, "y=1 should have been pruned (conflicts with x=1)");
    PASS();
}

/* ═══════════════════════════════════════════════════════════════
 *  Main
 * ═════════════════════════════════════════════════════════════ */

int main()
{
    printf("╔══════════════════════════════════════════════════════╗\n");
    printf("║          FLUX CUDA Test Suite                       ║\n");
    printf("╚══════════════════════════════════════════════════════╝\n\n");

    /* Init */
    printf("Initializing CUDA...\n");
    flux_cuda_error_t err = flux_cuda_init();
    if (err != FLUX_CUDA_OK) {
        fprintf(stderr, "FATAL: CUDA init failed (%d). No GPU available?\n", err);
        return 1;
    }

    flux_cuda_device_info_t info;
    flux_cuda_device_info(&info);
    printf("Device: %s (SM %d.%d, %zu MB, %d SMs)\n\n",
           info.name, info.major, info.minor,
           info.total_mem / (1024*1024), info.multiprocessor_count);

    /* Run tests */
    RUN(batch_add);
    RUN(batch_constraint_check);
    RUN(csp_backtracking_simple);
    RUN(sonar_physics_batch);
    RUN(arc_consistency);

    /* Summary */
    printf("\n════════════════════════════════════════════════════════\n");
    printf("Results: %d passed, %d failed, %d total\n",
           g_pass, g_fail, g_pass + g_fail);

    flux_cuda_cleanup();
    return g_fail > 0 ? 1 : 0;
}
