/* test_flux_cuda.cu -- Flux-CUDA Integration Test Suite
 * Verifies GPU kernels match CPU reference implementations.
 * Physics: Mackenzie (1981) sound speed, Thorp (1967) absorption.
 * Target: sm_72 (Jetson Xavier NX), sm_86 (cloud)
 * Compile: nvcc -arch=sm_72 test_flux_cuda.cu -o test_flux_cuda -O3
 * Also:    nvcc -gencode arch=compute_72,code=sm_72 \
 *               -gencode arch=compute_86,code=sm_86 \
 *               test_flux_cuda.cu -o test_flux_cuda -O3
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <float.h>
#include <string.h>
#include <time.h>

/* ============================================================================
 * CUDA Error Checking
 * ============================================================================ */
#define CUDA_CHECK(call) do {                                                  \
    cudaError_t err = call;                                                    \
    if (err != cudaSuccess) {                                                  \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__,      \
                cudaGetErrorString(err));                                      \
        return 1;                                                              \
    }                                                                          \
} while(0)

/* ============================================================================
 * Test case type
 * ============================================================================ */
typedef struct {
    const char *name;
    int (*run)(char *json_detail, size_t json_cap, int *passed);
} test_case_t;

/* ============================================================================
 * Reproducible pseudo-RNG (xorshift64*)
 * ============================================================================ */
static uint64_t rng_state = 88172645463325252ULL;

static double rng_next(void) {
    rng_state ^= rng_state >> 12;
    rng_state ^= rng_state << 25;
    rng_state ^= rng_state >> 27;
    return (double)(rng_state * 2685821657736338717ULL) / (double)UINT64_MAX;
}

static double rng_range(double lo, double hi) {
    return lo + rng_next() * (hi - lo);
}

/* ============================================================================
 * TEST A: Batch Sound Speed -- Mackenzie (1981)
 * ============================================================================ */

/*
 * Reference: Mackenzie, K.V. (1981).
 * "Nine-term equation for sound speed in the oceans."
 * Journal of the Acoustical Society of America, 70(3), 807-812.
 *
 * c(D,T,S) = 1448.96
 *     + 4.591*T
 *     - 5.304e-2*T*T
 *     + 2.374e-4*T*T*T
 *     + 1.340*(S-35)
 *     + 1.630e-2*D
 *     + 1.675e-7*D*D
 *     - 1.025e-2*T*(S-35)
 *     - 7.139e-13*T*D*D*D
 */
static double sound_speed_mackenzie(double D, double T, double S) {
    double dS = S - 35.0;
    return 1448.96
         + 4.591         * T
         - 5.304e-2      * T * T
         + 2.374e-4      * T * T * T
         + 1.340         * dS
         + 1.630e-2      * D
         + 1.675e-7      * D * D
         - 1.025e-2      * T * dS
         - 7.139e-13     * T * D * D * D;
}

__global__ void sound_speed_kernel(const double *depth,
                                   const double *temp,
                                   const double *sal,
                                   double       *out,
                                   int           n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    double D = depth[i];
    double T = temp[i];
    double S = sal[i];
    double dS = S - 35.0;
    out[i] = 1448.96
           + 4.591         * T
           - 5.304e-2      * T * T
           + 2.374e-4      * T * T * T
           + 1.340         * dS
           + 1.630e-2      * D
           + 1.675e-7      * D * D
           - 1.025e-2      * T * dS
           - 7.139e-13     * T * D * D * D;
}

static int test_batch_sound_speed(char *json, size_t cap, int *passed)
{
    const int N = 10000;
    const double D_MIN = 0.0,   D_MAX = 11000.0;
    const double T_MIN = -2.0,  T_MAX = 30.0;
    const double S_MIN = 30.0,  S_MAX = 40.0;

    rng_state = 88172645463325252ULL; /* reset seed */

    double *hD = (double *)malloc(N * sizeof(double));
    double *hT = (double *)malloc(N * sizeof(double));
    double *hS = (double *)malloc(N * sizeof(double));
    double *hCPU = (double *)malloc(N * sizeof(double));
    double *hGPU = (double *)malloc(N * sizeof(double));

    if (!hD || !hT || !hS || !hCPU || !hGPU) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    for (int i = 0; i < N; ++i) {
        hD[i] = rng_range(D_MIN, D_MAX);
        hT[i] = rng_range(T_MIN, T_MAX);
        hS[i] = rng_range(S_MIN, S_MAX);
        hCPU[i] = sound_speed_mackenzie(hD[i], hT[i], hS[i]);
    }

    double *dD, *dT, *dS, *dOut;
    CUDA_CHECK(cudaMalloc(&dD,   N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&dT,   N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&dS,   N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&dOut, N * sizeof(double)));

    CUDA_CHECK(cudaMemcpy(dD, hD, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(dT, hT, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(dS, hS, N * sizeof(double), cudaMemcpyHostToDevice));

    int threads = 256;
    int blocks  = (N + threads - 1) / threads;
    sound_speed_kernel<<<blocks, threads>>>(dD, dT, dS, dOut, N);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(hGPU, dOut, N * sizeof(double), cudaMemcpyDeviceToHost));

    double max_err = 0.0;
    for (int i = 0; i < N; ++i) {
        double err = fabs(hCPU[i] - hGPU[i]);
        if (err > max_err) max_err = err;
    }

    *passed = (max_err < 1e-12) ? 1 : 0;

    cudaFree(dD);
    cudaFree(dT);
    cudaFree(dS);
    cudaFree(dOut);
    free(hD);
    free(hT);
    free(hS);
    free(hCPU);
    free(hGPU);

    snprintf(json, cap,
        "    {\n"
        "      \"name\": \"batch_sound_speed\",\n"
        "      \"status\": \"%s\",\n"
        "      \"samples\": %d,\n"
        "      \"max_absolute_error\": %.6e,\n"
        "      \"physics\": \"Mackenzie (1981)\"\n"
        "    }",
        *passed ? "PASS" : "FAIL", N, max_err);

    return 0;
}

/* ============================================================================
 * TEST B: Batch Absorption -- Thorp (1967)
 * ============================================================================ */

/*
 * Reference: Thorp, W.H. (1967).
 * "Analytic description of the low-frequency attenuation coefficient."
 * Journal of the Acoustical Society of America, 42(1), 270.
 *
 * alpha(f) = (3.3e-3 + 0.11*f^2/(1+f^2) + 43*f^2/(4100+f^2) + 2.98e-4*f^2)
 *            / 1000.0
 * where f is in kHz.  Result is in dB/km.
 *
 * Note: depth is passed through unmodified (no depth dependence in Thorp).
 */
static double absorption_thorp(double f) {
    double ff = f * f;
    return (3.3e-3
          + 0.11   * ff / (1.0   + ff)
          + 43.0   * ff / (4100.0+ ff)
          + 2.98e-4* ff) / 1000.0;
}

__global__ void absorption_kernel(const double *freq,
                                  const double *depth,
                                  double       *out,
                                  int           n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    double f = freq[i];
    double ff = f * f;
    out[i] = (3.3e-3
            + 0.11    * ff / (1.0    + ff)
            + 43.0    * ff / (4100.0 + ff)
            + 2.98e-4 * ff) / 1000.0;
}

static int test_batch_absorption(char *json, size_t cap, int *passed)
{
    const int N = 10000;
    const double F_MIN = 0.1, F_MAX = 10.0;

    rng_state = 88172645463325252ULL; /* reset seed */

    double *hF   = (double *)malloc(N * sizeof(double));
    double *hD   = (double *)malloc(N * sizeof(double));
    double *hCPU = (double *)malloc(N * sizeof(double));
    double *hGPU = (double *)malloc(N * sizeof(double));

    if (!hF || !hD || !hCPU || !hGPU) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    for (int i = 0; i < N; ++i) {
        hF[i] = rng_range(F_MIN, F_MAX);
        hD[i] = rng_range(0.0, 11000.0); /* depth passed through */
        hCPU[i] = absorption_thorp(hF[i]);
    }

    double *dF, *dD, *dOut;
    CUDA_CHECK(cudaMalloc(&dF,   N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&dD,   N * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&dOut, N * sizeof(double)));

    CUDA_CHECK(cudaMemcpy(dF, hF, N * sizeof(double), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(dD, hD, N * sizeof(double), cudaMemcpyHostToDevice));

    int threads = 256;
    int blocks  = (N + threads - 1) / threads;
    absorption_kernel<<<blocks, threads>>>(dF, dD, dOut, N);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(hGPU, dOut, N * sizeof(double), cudaMemcpyDeviceToHost));

    double max_err = 0.0;
    for (int i = 0; i < N; ++i) {
        double err = fabs(hCPU[i] - hGPU[i]);
        if (err > max_err) max_err = err;
    }

    *passed = (max_err < 1e-12) ? 1 : 0;

    cudaFree(dF);
    cudaFree(dD);
    cudaFree(dOut);
    free(hF);
    free(hD);
    free(hCPU);
    free(hGPU);

    snprintf(json, cap,
        "    {\n"
        "      \"name\": \"batch_absorption\",\n"
        "      \"status\": \"%s\",\n"
        "      \"samples\": %d,\n"
        "      \"max_absolute_error\": %.6e,\n"
        "      \"physics\": \"Thorp (1967)\"\n"
        "    }",
        *passed ? "PASS" : "FAIL", N, max_err);

    return 0;
}

/* ============================================================================
 * TEST C: FLUX VM Execution -- 1000 parallel instances
 * ============================================================================
 *
 * Simple bytecode VM with 5 opcodes:
 *   LOAD  dst, input[idx]
 *   MUL   dst, srcA, srcB
 *   ADD   dst, srcA, srcB
 *   STORE output[idx], src
 *   HALT
 *
 * Bytecode program:
 *   LOAD  r0, input[0]
 *   LOAD  r1, input[1]
 *   MUL   r2, r0, r1
 *   ADD   r2, r2, 42.0
 *   STORE output[0], r2
 *   HALT
 *
 * This computes: output = input[0] * input[1] + 42.0
 */

#define VM_REG_COUNT 4
#define VM_MAX_INSTR 16

/* Bytecode opcodes */
typedef enum {
    OP_LOAD  = 0x01,
    OP_MUL   = 0x02,
    OP_ADD   = 0x03,
    OP_STORE = 0x04,
    OP_HALT  = 0xFF
} opcode_t;

/* Encoded instruction: 8 bytes each */
typedef struct {
    unsigned char op;
    unsigned char r0;       /* dst / output_idx */
    unsigned char r1;       /* srcA / input_idx */
    unsigned char r2;       /* srcB */
    unsigned char pad[4];
    double        imm;      /* immediate for scalar ops, or 0 */
} vm_instr_t;

/* Bytecode for: out = in[0] * in[1] + 42.0 */
__constant__ vm_instr_t d_program[VM_MAX_INSTR];

static int build_flux_program(vm_instr_t *prog)
{
    memset(prog, 0, VM_MAX_INSTR * sizeof(vm_instr_t));
    int pc = 0;

    /* LOAD r0, input[0] */
    prog[pc].op  = OP_LOAD;
    prog[pc].r0  = 0;     /* register 0 */
    prog[pc].r1  = 0;     /* input index 0 */
    ++pc;

    /* LOAD r1, input[1] */
    prog[pc].op  = OP_LOAD;
    prog[pc].r0  = 1;     /* register 1 */
    prog[pc].r1  = 1;     /* input index 1 */
    ++pc;

    /* MUL r2, r0, r1 */
    prog[pc].op  = OP_MUL;
    prog[pc].r0  = 2;     /* dst */
    prog[pc].r1  = 0;     /* srcA */
    prog[pc].r2  = 1;     /* srcB */
    ++pc;

    /* ADD r2, r2, 42.0 */
    prog[pc].op  = OP_ADD;
    prog[pc].r0  = 2;     /* dst */
    prog[pc].r1  = 2;     /* srcA */
    prog[pc].imm = 42.0;  /* immediate */
    ++pc;

    /* STORE output[0], r2 */
    prog[pc].op  = OP_STORE;
    prog[pc].r0  = 0;     /* output index 0 */
    prog[pc].r1  = 2;     /* src register */
    ++pc;

    /* HALT */
    prog[pc].op  = OP_HALT;
    ++pc;

    return pc;
}

static void flux_vm_cpu(const vm_instr_t *prog,
                        const double     *input,
                        double           *output)
{
    double reg[VM_REG_COUNT];
    int pc = 0;

    while (pc < VM_MAX_INSTR) {
        vm_instr_t ins = prog[pc];
        switch (ins.op) {
            case OP_LOAD:
                reg[ins.r0] = input[ins.r1];
                break;
            case OP_MUL:
                reg[ins.r0] = reg[ins.r1] * reg[ins.r2];
                break;
            case OP_ADD:
                if (ins.r2 < VM_REG_COUNT && ins.imm == 0.0)
                    reg[ins.r0] = reg[ins.r1] + reg[ins.r2];
                else
                    reg[ins.r0] = reg[ins.r1] + ins.imm;
                break;
            case OP_STORE:
                output[ins.r0] = reg[ins.r1];
                break;
            case OP_HALT:
                return;
            default:
                return;
        }
        ++pc;
    }
}

__global__ void flux_vm_kernel(const double *inputs,
                               double       *outputs,
                               int           num_instances,
                               int           inputs_per_instance,
                               int           outputs_per_instance)
{
    int vm_id = blockIdx.x * blockDim.x + threadIdx.x;
    if (vm_id >= num_instances) return;

    double reg[VM_REG_COUNT];
    int pc = 0;

    const double *in  = inputs  + vm_id * inputs_per_instance;
    double       *out = outputs + vm_id * outputs_per_instance;

    while (pc < VM_MAX_INSTR) {
        vm_instr_t ins = d_program[pc];
        switch (ins.op) {
            case OP_LOAD:
                reg[ins.r0] = in[ins.r1];
                break;
            case OP_MUL:
                reg[ins.r0] = reg[ins.r1] * reg[ins.r2];
                break;
            case OP_ADD:
                /* If imm is non-zero, use immediate; else use register */
                if (ins.imm != 0.0)
                    reg[ins.r0] = reg[ins.r1] + ins.imm;
                else
                    reg[ins.r0] = reg[ins.r1] + reg[ins.r2];
                break;
            case OP_STORE:
                out[ins.r0] = reg[ins.r1];
                break;
            case OP_HALT:
                return;
            default:
                return;
        }
        ++pc;
    }
}

static int test_flux_vm_parallel(char *json, size_t cap, int *passed)
{
    const int NUM_INSTANCES = 1000;
    const int INPUTS_PER    = 2;
    const int OUTPUTS_PER   = 1;

    rng_state = 88172645463325252ULL; /* reset seed */

    /* Build program on host */
    vm_instr_t h_prog[VM_MAX_INSTR];
    build_flux_program(h_prog);

    /* Allocate host buffers */
    size_t in_size  = NUM_INSTANCES * INPUTS_PER  * sizeof(double);
    size_t out_size = NUM_INSTANCES * OUTPUTS_PER * sizeof(double);

    double *hIn    = (double *)malloc(in_size);
    double *hOutCPU= (double *)malloc(out_size);
    double *hOutGPU= (double *)malloc(out_size);

    if (!hIn || !hOutCPU || !hOutGPU) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    /* Fill inputs deterministically */
    for (int i = 0; i < NUM_INSTANCES * INPUTS_PER; ++i)
        hIn[i] = rng_range(-100.0, 100.0);

    /* ---- CPU reference ---- */
    for (int vm = 0; vm < NUM_INSTANCES; ++vm) {
        flux_vm_cpu(h_prog,
                    hIn  + vm * INPUTS_PER,
                    hOutCPU + vm * OUTPUTS_PER);
    }

    /* ---- GPU execution ---- */
    CUDA_CHECK(cudaMemcpyToSymbol(d_program, h_prog,
                                  VM_MAX_INSTR * sizeof(vm_instr_t)));

    double *dIn, *dOut;
    CUDA_CHECK(cudaMalloc(&dIn,  in_size));
    CUDA_CHECK(cudaMalloc(&dOut, out_size));

    CUDA_CHECK(cudaMemcpy(dIn, hIn, in_size, cudaMemcpyHostToDevice));

    int threads = 256;
    int blocks  = (NUM_INSTANCES + threads - 1) / threads;
    flux_vm_kernel<<<blocks, threads>>>(dIn, dOut, NUM_INSTANCES,
                                        INPUTS_PER, OUTPUTS_PER);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(hOutGPU, dOut, out_size, cudaMemcpyDeviceToHost));

    /* ---- Verify: exact match ---- */
    double max_err = 0.0;
    int all_match  = 1;
    for (int i = 0; i < NUM_INSTANCES * OUTPUTS_PER; ++i) {
        double err = fabs(hOutCPU[i] - hOutGPU[i]);
        if (err > max_err) max_err = err;
        /* Bitwise compare for floating point equality */
        if (hOutCPU[i] != hOutGPU[i]) all_match = 0;
    }

    *passed = all_match;

    cudaFree(dIn);
    cudaFree(dOut);
    free(hIn);
    free(hOutCPU);
    free(hOutGPU);

    snprintf(json, cap,
        "    {\n"
        "      \"name\": \"flux_vm_parallel\",\n"
        "      \"status\": \"%s\",\n"
        "      \"instances\": %d,\n"
        "      \"max_absolute_error\": %.6e\n"
        "    }",
        *passed ? "PASS" : "FAIL", NUM_INSTANCES, max_err);

    return 0;
}

/* ============================================================================
 * JSON timestamp helper
 * ============================================================================ */
static void get_iso8601_timestamp(char *buf, size_t len)
{
    time_t now = time(NULL);
    struct tm *tm = gmtime(&now);
    strftime(buf, len, "%Y-%m-%dT%H:%M:%SZ", tm);
}

/* ============================================================================
 * CUDA device info
 * ============================================================================ */
static void get_device_name(char *buf, size_t len)
{
    int dev = 0;
    cudaGetDevice(&dev);
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, dev);
    strncpy(buf, prop.name, len - 1);
    buf[len - 1] = '\0';
}

/* ============================================================================
 * Main: test runner + JSON report
 * ============================================================================ */
int main(void)
{
    char ts[64];
    char dev_name[256];
    get_iso8601_timestamp(ts, sizeof(ts));
    get_device_name(dev_name, sizeof(dev_name));

    /* Test registry */
    char jsonA[512], jsonB[512], jsonC[512];
    int passedA = 0, passedB = 0, passedC = 0;

    int err = 0;
    err |= test_batch_sound_speed(jsonA, sizeof(jsonA), &passedA);
    err |= test_batch_absorption(jsonB, sizeof(jsonB), &passedB);
    err |= test_flux_vm_parallel(jsonC, sizeof(jsonC), &passedC);

    if (err) {
        printf("{\"test_suite\":\"flux_cuda_integration\","
               "\"error\":\"test execution failed\",\"exit_code\":1}\n");
        return 1;
    }

    int total_passed = passedA + passedB + passedC;
    int total_failed = 3 - total_passed;
    int all_passed   = (total_failed == 0);

    printf("{\n"
           "  \"test_suite\": \"flux_cuda_integration\",\n"
           "  \"timestamp\": \"%s\",\n"
           "  \"cuda_device\": \"%s\",\n"
           "  \"tests\": [\n"
           "%s,\n"
           "%s,\n"
           "%s\n"
           "  ],\n"
           "  \"summary\": {\n"
           "    \"total\": 3,\n"
           "    \"passed\": %d,\n"
           "    \"failed\": %d\n"
           "  }\n"
           "}\n",
           ts, dev_name,
           jsonA, jsonB, jsonC,
           total_passed, total_failed);

    return all_passed ? 0 : 1;
}
