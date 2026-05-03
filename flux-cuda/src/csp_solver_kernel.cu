/*
 * csp_solver_kernel.cu — GPU-accelerated CSP solver
 *
 * Parallel backtracking with each thread exploring a different branch.
 * Domain pruning in shared memory. Arc consistency via parallel message
 * passing between constraint threads. Forward checking with GPU-parallel
 * domain reduction. Solutions written to global results atomically.
 */

#include "flux_cuda.h"

/* ═══════════════════════════════════════════════════════════════
 *  Constants
 * ═════════════════════════════════════════════════════════════ */
#define CSP_MAX_VARS         64
#define CSP_MAX_DOMAIN_SIZE  128
#define CSP_MAX_CONSTRAINTS  512
#define CSP_MAX_BRANCH_DEPTH 64

/* ═══════════════════════════════════════════════════════════════
 *  Arc consistency kernel — parallel AC-3
 *
 *  Each thread handles one arc (xi, xj). Prunes domain of xi.
 *  Repeat until fixed point.
 * ═════════════════════════════════════════════════════════════ */

__global__ void flux_arc_consistency_kernel(
    int*    __restrict__ domains,        /* [problem_count * vars * max_dom] -1 terminated */
    int32_t* __restrict__ pruned,        /* [problem_count * vars] pruned counts */
    const int* __restrict__ constraints, /* [problem_count * constraints * 2] (i,j) pairs */
    int     var_count,
    int     max_domain_size,
    int     constraint_count,
    int     problem_count)
{
    const int pid = blockIdx.x;  /* problem id */
    const int tid = threadIdx.x; /* arc id within problem */
    if (pid >= problem_count) return;

    /* Shared: local copy of domains for this problem */
    extern __shared__ int s_domains[];
    int* s_pruned = s_domains + var_count * max_domain_size;

    /* Thread 0 initializes shared domains */
    if (tid == 0) {
        const int* p_domains = domains + pid * var_count * max_domain_size;
        for (int v = 0; v < var_count; ++v)
            for (int d = 0; d < max_domain_size; ++d)
                s_domains[v * max_domain_size + d] = p_domains[v * max_domain_size + d];
        for (int v = 0; v < var_count; ++v)
            s_pruned[v] = 0;
    }
    __syncthreads();

    /* Iterate AC-3 until no changes */
    const int MAX_AC3_ITER = 100;
    for (int iter = 0; iter < MAX_AC3_ITER; ++iter) {
        int local_changed = 0;

        if (tid < constraint_count) {
            const int* con = constraints + pid * constraint_count * 2 + tid * 2;
            int xi = con[0];
            int xj = con[1];
            if (xi < 0 || xi >= var_count || xj < 0 || xj >= var_count) continue;

            /* For each value in domain of xi, check if there's a supporting value in xj */
            for (int di = 0; di < max_domain_size; ++di) {
                int vi = s_domains[xi * max_domain_size + di];
                if (vi < 0) break; /* -1 = sentinel */

                int has_support = 0;
                for (int dj = 0; dj < max_domain_size; ++dj) {
                    int vj = s_domains[xj * max_domain_size + dj];
                    if (vj < 0) break;
                    /* Binary constraint: xi ≠ xj (default alldiff) */
                    if (vi != vj) { has_support = 1; break; }
                }

                if (!has_support) {
                    /* Remove vi from domain of xi by shifting */
                    s_domains[xi * max_domain_size + di] = -1;
                    atomicAdd(&s_pruned[xi], 1);
                    local_changed = 1;
                }
            }
        }

        /* Warp-level OR to check if anything changed */
        for (int off = 16; off > 0; off >>= 1)
            local_changed |= __shfl_down_sync(0xFFFFFFFF, local_changed, off);

        /* Broadcast: if thread 0 says no change, all exit */
        __syncthreads();
        if (local_changed == 0) break;
        __syncthreads();
    }

    /* Write back domains */
    __syncthreads();
    if (tid == 0) {
        int* p_domains = domains + pid * var_count * max_domain_size;
        for (int v = 0; v < var_count; ++v)
            for (int d = 0; d < max_domain_size; ++d)
                p_domains[v * max_domain_size + d] = s_domains[v * max_domain_size + d];
        int32_t* p_pruned = pruned + pid * var_count;
        for (int v = 0; v < var_count; ++v)
            p_pruned[v] = s_pruned[v];
    }
}

/* ═══════════════════════════════════════════════════════════════
 *  Backtracking CSP solver kernel
 *
 *  Each thread explores a different initial assignment branch.
 *  Uses shared memory for domain copies. Forward checking prunes.
 *  First solution found is written atomically.
 * ═════════════════════════════════════════════════════════════ */

__launch_bounds__(256, 4)
__global__ void flux_csp_backtrack_kernel(
    const int*    __restrict__ domains,      /* [problems * vars * max_dom] */
    const int*    __restrict__ constraints,   /* [problems * cons * 2] */
    const double* __restrict__ weights,       /* optional, may be NULL */
    int*          __restrict__ solutions,     /* [problems * vars] */
    int32_t*      __restrict__ solved,        /* per-problem flag */
    int           var_count,
    int           max_domain_size,
    int           constraint_count,
    int           problem_count,
    int           branch_factor)
{
    const int pid = blockIdx.x;
    const int tid = threadIdx.x;
    if (pid >= problem_count) return;

    /* Shared memory for this problem's domains */
    extern __shared__ char smem[];
    int* s_domains = reinterpret_cast<int*>(smem);
    /* Stack for backtracking: (var_index, domain_index, value) */
    struct BTEntry { int var; int di; int val; };
    BTEntry* bt_stack = reinterpret_cast<BTEntry*>(
        smem + var_count * max_domain_size * sizeof(int));

    /* Only active threads search */
    /* Each thread gets a starting branch = tid */
    int assignment[CSP_MAX_VARS];
    for (int v = 0; v < var_count; ++v) assignment[v] = -1;

    /* Local domain copy for forward checking */
    int local_domains[CSP_MAX_VARS * CSP_MAX_DOMAIN_SIZE]; /* stack-allocated */

    const int* p_domains = domains + pid * var_count * max_domain_size;
    const int* p_constraints = constraints + pid * constraint_count * 2;

    /* Copy initial domains */
    for (int v = 0; v < var_count; ++v)
        for (int d = 0; d < max_domain_size; ++d)
            local_domains[v * max_domain_size + d] = p_domains[v * max_domain_size + d];

    /* Starting branch: pick a value from domain of first variable */
    int start_var = 0;
    int start_val_idx = tid % max_domain_size;
    int start_val = local_domains[start_var * max_domain_size + start_val_idx];
    if (start_val < 0) return; /* no value at this index */

    assignment[start_var] = start_val;

    /* Backtracking search from var 1 */
    int current_var = 1;
    int depth = 0;

    while (current_var < var_count && depth < CSP_MAX_BRANCH_DEPTH) {
        /* Find next valid value for current_var */
        int found = 0;
        for (int d = 0; d < max_domain_size; ++d) {
            int candidate = local_domains[current_var * max_domain_size + d];
            if (candidate < 0) break;

            /* Forward check against constraints */
            int consistent = 1;
            for (int c = 0; c < constraint_count && consistent; ++c) {
                int ci = p_constraints[c * 2];
                int cj = p_constraints[c * 2 + 1];
                if (ci == current_var && assignment[cj] >= 0) {
                    if (candidate == assignment[cj]) consistent = 0;
                } else if (cj == current_var && assignment[ci] >= 0) {
                    if (candidate == assignment[ci]) consistent = 0;
                }
            }

            if (consistent) {
                assignment[current_var] = candidate;
                current_var++;
                found = 1;
                depth++;
                break;
            }
        }

        if (!found) {
            /* Backtrack */
            assignment[current_var] = -1;
            current_var--;
            depth++;
            if (current_var <= start_var) break; /* exhausted */
        }

        /* Check if someone already solved this */
        if (__ldg(solved + pid) != 0) return;
    }

    /* If all variables assigned, write solution */
    if (current_var >= var_count) {
        int32_t expected = 0;
        if (atomicCAS(solved + pid, 0, 1) == 0) {
            int* p_sol = solutions + pid * var_count;
            for (int v = 0; v < var_count; ++v)
                p_sol[v] = assignment[v];
        }
    }
}

/* ═══════════════════════════════════════════════════════════════
 *  Forward checking kernel — parallel domain reduction
 *
 *  Given partial assignments, prune domains for unassigned variables.
 * ═════════════════════════════════════════════════════════════ */

__global__ void flux_forward_check_kernel(
    int*          __restrict__ domains,
    const int*    __restrict__ constraints,
    const int*    __restrict__ assignments, /* -1 for unassigned */
    int           var_count,
    int           max_domain_size,
    int           constraint_count,
    int           problem_count)
{
    const int pid = blockIdx.x;
    const int tid = threadIdx.x; /* variable index */
    if (pid >= problem_count || tid >= var_count) return;

    /* Don't prune already-assigned variables */
    const int* p_assign = assignments + pid * var_count;
    if (p_assign[tid] >= 0) return;

    int* p_domains = domains + pid * var_count * max_domain_size;
    const int* p_constraints = constraints + pid * constraint_count * 2;

    /* For each value in this variable's domain, check consistency */
    for (int d = 0; d < max_domain_size; ++d) {
        int val = p_domains[tid * max_domain_size + d];
        if (val < 0) break;

        for (int c = 0; c < constraint_count; ++c) {
            int ci = p_constraints[c * 2];
            int cj = p_constraints[c * 2 + 1];

            int other = -1;
            if (ci == tid) other = cj;
            else if (cj == tid) other = ci;
            else continue;

            if (other < var_count && p_assign[other] >= 0) {
                if (val == p_assign[other]) {
                    /* Conflict: remove this value */
                    p_domains[tid * max_domain_size + d] = -1;
                    break;
                }
            }
        }
    }
}
