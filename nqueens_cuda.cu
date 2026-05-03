/* nqueens_cuda.cu -- GPU N-Queens Constraint Solver
 *
 * Solves the N-queens problem using CUDA parallel backtracking.
 * Each thread explores a subtree of the search space.
 * Uses bitmasks for conflict detection, shared memory for block-level
 * aggregation, and atomic operations for the global solution counter.
 *
 * Algorithm:
 *   - CPU precomputes valid partial board placements for first K rows
 *   - GPU kernel assigns one partial board per thread
 *   - Each thread recursively completes its subtree using 3 bitmasks:
 *       columns:      1 << col
 *       diagonals:    1 << (row - col + N - 1)
 *       anti-diagonals: 1 << (row + col)
 *   - Warp-shuffle reduction + single atomicAdd per block for efficiency
 *
 * Verified against known solution counts:
 *   N=8  -> 92
 *   N=9  -> 352
 *   N=10 -> 724
 *   N=11 -> 2680
 *   N=12 -> 14200
 *   N=13 -> 73712
 *   N=14 -> 365596
 *   N=15 -> 2279184
 *   N=16 -> 14772512
 *
 * Target: sm_72 (Jetson Xavier NX), sm_86 (cloud)
 * Compile: nvcc -arch=sm_72 nqueens_cuda.cu -o nqueens_cuda -O3
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cuda_runtime.h>

/* ------------------------------------------------------------------ */
/*  CUDA error-checking macro                                          */
/* ------------------------------------------------------------------ */
#define CUDA_CHECK(call) do {                                          \
    cudaError_t err = call;                                            \
    if (err != cudaSuccess) {                                          \
        fprintf(stderr, "CUDA error at %s:%d: %s\n",                   \
                __FILE__, __LINE__, cudaGetErrorString(err));          \
        exit(1);                                                       \
    }                                                                  \
} while(0)

/* ------------------------------------------------------------------ */
/*  Known solution counts (index = N)                                  */
/* ------------------------------------------------------------------ */
static const unsigned long long NQUEENS_SOLUTIONS[17] = {
    0ULL,          /* 0  */
    1ULL,          /* 1  */
    0ULL,          /* 2  */
    0ULL,          /* 3  */
    2ULL,          /* 4  */
    10ULL,         /* 5  */
    4ULL,          /* 6  */
    40ULL,         /* 7  */
    92ULL,         /* 8  */
    352ULL,        /* 9  */
    724ULL,        /* 10 */
    2680ULL,       /* 11 */
    14200ULL,      /* 12 */
    73712ULL,      /* 13 */
    365596ULL,     /* 14 */
    2279184ULL,    /* 15 */
    14772512ULL    /* 16 */
};

/* ------------------------------------------------------------------ */
/*  Board state for a partial configuration                            */
/* ------------------------------------------------------------------ */
typedef struct {
    int col_mask;    /* bit i set  -> column i occupied               */
    int diag_mask;   /* bit j set  -> diagonal j attacked             */
    int anti_mask;   /* bit k set  -> anti-diagonal k attacked        */
    int row;         /* next free row to fill                         */
} BoardState;

/* ------------------------------------------------------------------ */
/*  Device-side recursive backtracking solver                          */
/*  Uses 3 bitmasks for O(1) conflict detection.                       */
/* ------------------------------------------------------------------ */
__device__ void solve_recursive(int n, int row,
                                int col_mask, int diag_mask, int anti_mask,
                                unsigned long long *count)
{
    if (row == n) {
        (*count)++;
        return;
    }

    for (int col = 0; col < n; col++) {
        int col_bit = 1 << col;
        if (col_mask & col_bit) continue;          /* column taken    */

        int diag_bit = 1 << (row - col + n - 1);
        if (diag_mask & diag_bit) continue;        /* diagonal taken  */

        int anti_bit = 1 << (row + col);
        if (anti_mask & anti_bit) continue;        /* anti-diag taken */

        solve_recursive(n, row + 1,
                        col_mask | col_bit,
                        diag_mask | diag_bit,
                        anti_mask | anti_bit,
                        count);
    }
}

/* ------------------------------------------------------------------ */
/*  GPU Kernel                                                         */
/*  Each thread consumes one (or more, strided) precomputed partial    */
/*  board states and completes them via recursive backtracking.        */
/*  Warp-shuffle reduction produces a single atomicAdd per block.      */
/* ------------------------------------------------------------------ */
__global__ void nqueens_kernel(int n,
                               const BoardState *__restrict__ states,
                               int num_states,
                               unsigned long long *__restrict__ global_solutions)
{
    /* Shared memory conflict bitmap cache (N <= 16) */
    __shared__ int shared_conflict_cache[16];

    /* One accumulator per warp for the block-level reduction */
    __shared__ unsigned long long warp_sums[32];

    /* ---- initialise shared memory -------------------------------- */
    if (threadIdx.x < 16) {
        shared_conflict_cache[threadIdx.x] = 0;
    }
    if (threadIdx.x < 32) {
        warp_sums[threadIdx.x] = 0ULL;
    }
    __syncthreads();

    /* ---- each thread processes states strided by grid size -------- */
    int tid           = blockIdx.x * blockDim.x + threadIdx.x;
    int grid_stride   = gridDim.x  * blockDim.x;
    unsigned long long local_count = 0ULL;

    for (int i = tid; i < num_states; i += grid_stride) {
        BoardState s = states[i];
        solve_recursive(n, s.row, s.col_mask, s.diag_mask, s.anti_mask,
                        &local_count);
    }

    /* ---- warp-level reduction via __shfl_down_sync --------------- */
    unsigned long long warp_sum = local_count;
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        warp_sum += __shfl_down_sync(0xFFFFFFFFu, warp_sum, offset);
    }

    int lane_id = threadIdx.x & 31;
    int warp_id = threadIdx.x >> 5;
    if (lane_id == 0) {
        warp_sums[warp_id] = warp_sum;
    }
    __syncthreads();

    /* ---- block leader sums warps, one atomic to global ----------- */
    if (threadIdx.x == 0) {
        unsigned long long block_total = 0ULL;
        int num_warps = (blockDim.x + 31) >> 5;
        for (int w = 0; w < num_warps; w++) {
            block_total += warp_sums[w];
        }
        atomicAdd(global_solutions, block_total);
    }
}

/* ------------------------------------------------------------------ */
/*  CPU helper: recursively enumerate every valid placement of the     */
/*  first 'target_depth' rows and store them in 'states[]'.            */
/* ------------------------------------------------------------------ */
static void generate_states(int n, int target_depth, int row,
                            int col_mask, int diag_mask, int anti_mask,
                            BoardState *states, int *count, int max_states)
{
    if (row == target_depth) {
        if (*count < max_states) {
            states[*count].col_mask = col_mask;
            states[*count].diag_mask = diag_mask;
            states[*count].anti_mask = anti_mask;
            states[*count].row = row;
            (*count)++;
        }
        return;
    }

    for (int col = 0; col < n; col++) {
        int col_bit = 1 << col;
        if (col_mask & col_bit) continue;

        int diag_bit = 1 << (row - col + n - 1);
        if (diag_mask & diag_bit) continue;

        int anti_bit = 1 << (row + col);
        if (anti_mask & anti_bit) continue;

        generate_states(n, target_depth, row + 1,
                        col_mask | col_bit,
                        diag_mask | diag_bit,
                        anti_mask | anti_bit,
                        states, count, max_states);
    }
}

/* ------------------------------------------------------------------ */
/*  Host solver wrapper                                                */
/* ------------------------------------------------------------------ */
int nqueens_solve(int n, unsigned long long *solutions, double *elapsed_ms)
{
    if (n < 1 || n > 16) {
        fprintf(stderr, "Error: N must be in [1, 16] (got %d)\n", n);
        return -1;
    }

    /* Trivial cases: N = 1, 2, 3 */
    if (n == 1) {
        *solutions = 1ULL;
        *elapsed_ms = 0.0;
        return 0;
    }
    if (n <= 3) {
        *solutions = 0ULL;
        *elapsed_ms = 0.0;
        return 0;
    }

    /* -------------------------------------------------------------- */
    /*  Decide how many rows to pre-split on the CPU.  Deeper splits  */
    /*  create more starting states -> better GPU utilisation.          */
    /* -------------------------------------------------------------- */
    int split_depth;
    if (n <= 8) {
        split_depth = 1;   /* N=8  -> 8   states              */
    } else if (n <= 10) {
        split_depth = 2;   /* N=10 -> ~90  states             */
    } else if (n <= 13) {
        split_depth = 3;   /* N=12 -> ~850 states             */
    } else {
        split_depth = 4;   /* N=14 -> ~7 k, N=16 -> ~37 k     */
    }

    /* Safety cap: do not generate more than 200 000 states           */
    const int MAX_STATES = 200000;
    BoardState *h_states = (BoardState *)malloc(MAX_STATES * sizeof(BoardState));
    if (!h_states) {
        fprintf(stderr, "Error: host malloc failed\n");
        return -1;
    }

    int num_states = 0;
    generate_states(n, split_depth, 0, 0, 0, 0,
                    h_states, &num_states, MAX_STATES);

    /* -------------------------------------------------------------- */
    /*  Device memory allocation                                       */
    /* -------------------------------------------------------------- */
    BoardState *d_states;
    unsigned long long *d_solutions;
    CUDA_CHECK(cudaMalloc(&d_states,    num_states * sizeof(BoardState)));
    CUDA_CHECK(cudaMalloc(&d_solutions, sizeof(unsigned long long)));
    CUDA_CHECK(cudaMemset(d_solutions, 0, sizeof(unsigned long long)));

    CUDA_CHECK(cudaMemcpy(d_states, h_states,
                          num_states * sizeof(BoardState),
                          cudaMemcpyHostToDevice));
    free(h_states);

    /* -------------------------------------------------------------- */
    /*  Grid / block sizing -- auto-tuned from device properties       */
    /* -------------------------------------------------------------- */
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));

    int block_size = 256;
    if (num_states < 64)   block_size = 64;
    else if (num_states < 128) block_size = 128;

    int num_blocks = (num_states + block_size - 1) / block_size;
    int min_blocks = prop.multiProcessorCount * 2;
    if (num_blocks < min_blocks) num_blocks = min_blocks;
    if (num_blocks > 65535)      num_blocks = 65535;

    /* -------------------------------------------------------------- */
    /*  Kernel launch with CUDA event timing                           */
    /* -------------------------------------------------------------- */
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    CUDA_CHECK(cudaEventRecord(start));
    nqueens_kernel<<<num_blocks, block_size>>>(n, d_states, num_states,
                                               d_solutions);
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float elapsed = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&elapsed, start, stop));
    *elapsed_ms = (double)elapsed;

    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));

    /* -------------------------------------------------------------- */
    /*  Copy result back and clean up                                   */
    /* -------------------------------------------------------------- */
    CUDA_CHECK(cudaMemcpy(solutions, d_solutions,
                          sizeof(unsigned long long),
                          cudaMemcpyDeviceToHost));

    CUDA_CHECK(cudaFree(d_states));
    CUDA_CHECK(cudaFree(d_solutions));

    return 0;
}

/* ------------------------------------------------------------------ */
/*  Main -- verify against known counts, emit JSON                     */
/* ------------------------------------------------------------------ */
int main(int argc, char **argv)
{
    /* ---- CUDA setup ---------------------------------------------- */
    CUDA_CHECK(cudaSetDevice(0));

    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));

    printf("============================================================\n");
    printf("  N-Queens GPU Constraint Solver (Cocapn)\n");
    printf("============================================================\n");
    printf("Device : %s\n", prop.name);
    printf("SMs    : %d\n", prop.multiProcessorCount);
    printf("Arch   : sm_%d%d\n", prop.major, prop.minor);

    /* ---- determine test set -------------------------------------- */
    int run_all = (argc > 1 && (atoi(argv[1]) > 0));

    int test_ns[16];
    int num_tests;
    if (run_all) {
        for (int i = 0; i < 13; i++) test_ns[i] = i + 4; /* 4..16 */
        num_tests = 13;
    } else {
        /* Required: N = 8, 12, 14 */
        test_ns[0] = 8;
        test_ns[1] = 12;
        test_ns[2] = 14;
        num_tests  = 3;
    }

    printf("------------------------------------------------------------\n");
    printf("  N   |  Solutions   |  Expected    | Time (ms) | Status\n");
    printf("------------------------------------------------------------\n");

    typedef struct {
        int n;
        unsigned long long solutions;
        double time_ms;
        int verified;
    } Result;

    Result results[16];
    int result_count = 0;
    int all_verified = 1;

    for (int t = 0; t < num_tests; t++) {
        int n = test_ns[t];
        unsigned long long solutions;
        double elapsed_ms;

        int rc = nqueens_solve(n, &solutions, &elapsed_ms);
        if (rc != 0) {
            printf(" %2d   |  %-12s|  %-12s|  %-9s| ERROR\n",
                   n, "--", "--", "--");
            all_verified = 0;
            continue;
        }

        int verified = (solutions == NQUEENS_SOLUTIONS[n]);
        if (!verified) all_verified = 0;

        printf(" %2d   |  %-12llu|  %-12llu|  %9.3f | %s\n",
               n, solutions, NQUEENS_SOLUTIONS[n], elapsed_ms,
               verified ? "PASS" : "FAIL");

        results[result_count].n = n;
        results[result_count].solutions = solutions;
        results[result_count].time_ms = elapsed_ms;
        results[result_count].verified = verified;
        result_count++;
    }

    printf("------------------------------------------------------------\n");

    /* ---- JSON output --------------------------------------------- */
    printf("\n--- JSON ---\n");
    printf("{\n");
    printf("  \"benchmark\": \"nqueens_cuda\",\n");
    printf("  \"device\": \"%s\",\n", prop.name);
    printf("  \"results\": [\n");
    for (int i = 0; i < result_count; i++) {
        printf("    {\"n\": %d, \"solutions\": %llu, "
               "\"time_ms\": %.3f, \"verified\": %s}%s\n",
               results[i].n,
               results[i].solutions,
               results[i].time_ms,
               results[i].verified ? "true" : "false",
               (i < result_count - 1) ? "," : "");
    }
    printf("  ],\n");
    printf("  \"all_verified\": %s\n", all_verified ? "true" : "false");
    printf("}\n");

    return all_verified ? 0 : 1;
}
