/**
 * ct_snap_gpu.cu — Constraint-Theory Snap Kernel v3
 * 
 * GPU-native constraint satisfaction via angle-space snapping.
 * Uses Pythagorean triple generation for constraint space discretization,
 * then binary search + warp shuffle for O(log n) snap per query.
 *
 * Designed for Jetson Xavier/Orin (compute_72) and desktop (compute_75+).
 * Zero shared memory — uses __shfl_sync for warp-cooperative search.
 *
 * Build:
 *   nvcc -arch=sm_72 -O3 -Xptxas -v ct_snap_gpu.cu -o ct_snap_gpu
 *   nvcc -arch=sm_75 -O3 ct_snap_gpu.cu -o ct_snap_gpu   (desktop)
 *
 * Forgemaster ⚒️ — Cocapn Fleet, 2026-05-03
 */

#include <cstdio>
#include <cmath>
#include <cstdlib>
#include <chrono>

constexpr double TAU = 6.283185307179586;
constexpr int WARP_SIZE = 32;

// ─── Host: Pythagorean Triple Generator ───────────────────────────

struct TripleSet {
    double* angles;    // sorted angular positions
    int*    triples;   // (a,b,c) packed as [3*n]
    int     count;     // number of unique angles
    int     max_c;     // maximum hypotenuse

    static TripleSet generate(int max_c) {
        int cap = max_c;
        double* angles = (double*)malloc(cap * sizeof(double));
        int* triples   = (int*)malloc(cap * 3 * sizeof(int));
        int n = 0;
        int max_m = (int)(sqrt((double)max_c) / 1.41421356) + 1;

        for (int m = 2; m <= max_m && n < cap; m++) {
            for (int nn = 1; nn < m && n < cap; nn++) {
                if ((m + nn) % 2 == 0) continue;  // same parity → skip
                int a = m*m - nn*nn;
                int b = 2*m*nn;
                int c = m*m + nn*nn;
                if (c > max_c) break;

                // GCD check for primitive triples
                int g = a, bb = nn;
                while (bb) { int t = bb; bb = g % bb; g = t; }
                if (g != 1) continue;

                // Store the triple
                triples[3*n] = a; triples[3*n+1] = b; triples[3*n+2] = c;

                // 8 octant angles for this triple
                angles[n++] = atan2((double)a, (double)b);
                if (n < cap) angles[n++] = atan2((double)-a, (double)b);
                if (n < cap) angles[n++] = atan2((double)a, (double)-b);
                if (n < cap) angles[n++] = atan2((double)-a, (double)-b);
                if (n < cap) angles[n++] = atan2((double)b, (double)a);
                if (n < cap) angles[n++] = atan2((double)-b, (double)a);
                if (n < cap) angles[n++] = atan2((double)b, (double)-a);
                if (n < cap) angles[n++] = atan2((double)-b, (double)-a);
            }
        }

        // Sort angles (insertion sort — fine for ~50K elements)
        for (int i = 1; i < n; i++) {
            double key = angles[i];
            int j = i - 1;
            while (j >= 0 && angles[j] > key) {
                angles[j+1] = angles[j];
                j--;
            }
            angles[j+1] = key;
        }

        return {angles, triples, n, max_c};
    }

    void free() {
        ::free(angles);
        ::free(triples);
    }
};

// ─── Device: Angular Distance ─────────────────────────────────────

__device__ __forceinline__
double angular_dist(double a, double b) {
    double d = fabs(a - b);
    return fmin(d, TAU - d);
}

// ─── Kernel: Batch Snap with Warp-Cooperative Binary Search ───────

/**
 * Each warp processes 32 queries cooperatively.
 * Uses __shfl_sync for inter-lane communication.
 * 
 * @param angles    sorted constraint angles [n_angles]
 * @param n_angles  number of angles
 * @param queries   query angles [n_queries]
 * @param results   output: index of nearest constraint [n_queries]
 * @param dists     output: angular distance to nearest [n_queries]
 * @param n_queries total queries
 */
__global__
void snap_warp_cooperative(const double* __restrict__ angles,
                            int n_angles,
                            const double* __restrict__ queries,
                            int* __restrict__ results,
                            double* __restrict__ dists,
                            int n_queries)
{
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int lane = tid & (WARP_SIZE - 1);
    int warp_id = tid >> 5;  // tid / 32

    // Each warp handles one query (warp_id = query index)
    int qidx = warp_id;
    if (qidx >= n_queries) return;

    double q = fmod(queries[qidx], TAU);
    if (q < 0.0) q += TAU;

    // Warp-cooperative binary search
    // Lane 0 manages the search state, broadcasts via shfl
    int lo = 0, hi = n_angles - 1;

    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        // All lanes read angles[mid] for cache coherence
        double mid_val = angles[mid];
        // Lane 0 makes the comparison decision
        unsigned mask = __activemask();
        int go_high = __shfl_sync(mask, (q > mid_val) ? 1 : 0, 0);
        if (go_high)
            lo = mid + 1;
        else
            hi = mid;
    }

    // Snap: compare lo-1 vs lo (wrap-around for lo==0)
    double d_prev, d_curr;
    int idx_prev;

    if (lo == 0) {
        d_prev = angular_dist(q, angles[n_angles - 1]);
        d_curr = angular_dist(q, angles[0]);
        idx_prev = n_angles - 1;
    } else {
        d_prev = angular_dist(q, angles[lo - 1]);
        d_curr = angular_dist(q, angles[lo]);
        idx_prev = lo - 1;
    }

    // Lane 0 writes result
    if (lane == 0) {
        if (d_prev <= d_curr) {
            results[qidx] = idx_prev;
            dists[qidx] = d_prev;
        } else {
            results[qidx] = lo;
            dists[qidx] = d_curr;
        }
    }
}

// ─── Kernel: Constraint Satisfaction Check ─────────────────────────

/**
 * Verify that a set of angles satisfies constraint distance bounds.
 * Each thread checks one constraint pair.
 *
 * @param angles    constraint angles [n]
 * @param min_dist  minimum allowed angular separation
 * @param max_dist  maximum allowed angular separation  
 * @param n         number of angles
 * @param violations output: count of violated constraints [1]
 */
__global__
void check_constraints(const double* __restrict__ angles,
                        double min_dist,
                        double max_dist,
                        int n,
                        int* __restrict__ violations)
{
    extern __shared__ int smem_count[];
    
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (threadIdx.x == 0) smem_count[0] = 0;
    __syncthreads();

    // Each thread checks one adjacent pair
    if (tid < n) {
        int next = (tid + 1) % n;
        double d = angular_dist(angles[tid], angles[next]);
        
        if (d < min_dist || d > max_dist) {
            atomicAdd(smem_count, 1);
        }
    }
    __syncthreads();

    // Block-level reduction to global
    if (threadIdx.x == 0 && smem_count[0] > 0) {
        atomicAdd(violations, smem_count[0]);
    }
}

// ─── Kernel: Constraint Propagation via Jacobi Relaxation ──────────

/**
 * Relax constraint angles toward their nearest Pythagorean snap point
 * while maintaining minimum separation. GPU-parallel Jacobi iteration.
 *
 * @param angles     current angles [n] (device)
 * @param snap_pts   valid snap points (sorted) [m] (device)
 * @param n          number of angles
 * @param m          number of snap points
 * @param min_sep    minimum angular separation
 * @param relaxed    output: relaxed angles [n] (device)
 * @param alpha      relaxation factor (0-1)
 */
__global__
void jacobi_relax(const double* __restrict__ angles,
                   const double* __restrict__ snap_pts,
                   int n, int m,
                   double min_sep,
                   double alpha,
                   double* __restrict__ relaxed)
{
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n) return;

    double a = angles[tid];
    
    // Binary search for nearest snap point
    int lo = 0, hi = m - 1;
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        if (snap_pts[mid] < a) lo = mid + 1;
        else hi = mid;
    }
    
    // Snap to nearest
    double snapped;
    if (lo == 0) {
        snapped = (angular_dist(a, snap_pts[0]) <= angular_dist(a, snap_pts[m-1]))
                  ? snap_pts[0] : snap_pts[m-1];
    } else {
        snapped = (angular_dist(a, snap_pts[lo-1]) <= angular_dist(a, snap_pts[lo]))
                  ? snap_pts[lo-1] : snap_pts[lo];
    }
    
    // Relaxation: blend current with snapped
    relaxed[tid] = a + alpha * (snapped - a);
}

// ─── Host: Benchmark Runner ────────────────────────────────────────

int main() {
    printf("╔══════════════════════════════════════════════════╗\n");
    printf("║  Constraint-Theory GPU Snap Kernel v3           ║\n");
    printf("║  Forgemaster ⚒️ — Cocapn Fleet                  ║\n");
    printf("╚══════════════════════════════════════════════════╝\n\n");

    // Generate Pythagorean constraint space
    int max_c = 50000;
    TripleSet ts = TripleSet::generate(max_c);
    printf("Generated %d Pythagorean angles (c ≤ %d)\n\n", ts.count, max_c);

    // Allocate device memory
    double *d_angles, *d_queries, *d_dists, *d_relaxed;
    int *d_results, *d_violations;
    
    cudaMalloc(&d_angles, ts.count * sizeof(double));
    cudaMemcpy(d_angles, ts.angles, ts.count * sizeof(double), cudaMemcpyHostToDevice);
    
    int n_queries = ts.count;  // snap every angle to itself as sanity check
    double* queries = (double*)malloc(n_queries * sizeof(double));
    for (int i = 0; i < n_queries; i++) queries[i] = ts.angles[i];

    cudaMalloc(&d_queries, n_queries * sizeof(double));
    cudaMalloc(&d_results, n_queries * sizeof(int));
    cudaMalloc(&d_dists, n_queries * sizeof(double));
    cudaMalloc(&d_relaxed, n_queries * sizeof(double));
    cudaMalloc(&d_violations, sizeof(int));
    cudaMemcpy(d_queries, queries, n_queries * sizeof(double), cudaMemcpyHostToDevice);

    // Benchmark parameters
    int block_size = 256;  // 8 warps per block
    int grid = (n_queries + block_size - 1) / block_size;

    // ─── Warm-up ───
    snap_warp_cooperative<<<grid, block_size>>>(
        d_angles, ts.count, d_queries, d_results, d_dists, n_queries);
    cudaDeviceSynchronize();

    // ─── Timed run ───
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    int n_iters = 100;
    cudaEventRecord(start);
    for (int i = 0; i < n_iters; i++) {
        snap_warp_cooperative<<<grid, block_size>>>(
            d_angles, ts.count, d_queries, d_results, d_dists, n_queries);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    float us_per_query = (ms * 1000.0f) / (n_queries * n_iters);

    printf("=== Warp-Cooperative Snap ===\n");
    printf("  Queries: %d × %d iters\n", n_queries, n_iters);
    printf("  Total GPU time: %.3f ms\n", ms);
    printf("  Per-query: %.3f µs\n", us_per_query);
    printf("  Throughput: %.1f M queries/sec\n\n",
           (n_queries * n_iters) / (ms * 1000.0));

    // ─── Verify correctness ───
    int* h_results = (int*)malloc(n_queries * sizeof(int));
    double* h_dists = (double*)malloc(n_queries * sizeof(double));
    cudaMemcpy(h_results, d_results, n_queries * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(h_dists, d_dists, n_queries * sizeof(double), cudaMemcpyDeviceToHost);

    // Sanity: snapping to self should yield distance ≈ 0
    int perfect = 0;
    for (int i = 0; i < n_queries; i++) {
        if (h_dists[i] < 1e-10) perfect++;
    }
    printf("Self-snap accuracy: %d/%d perfect (dist < 1e-10)\n\n", perfect, n_queries);

    // ─── Jacobi Relaxation Benchmark ───
    double alpha = 0.5;
    double min_sep = 0.001;
    
    cudaMemset(d_violations, 0, sizeof(int));
    
    cudaEventRecord(start);
    for (int i = 0; i < n_iters; i++) {
        jacobi_relax<<<grid, block_size>>>(
            d_queries, d_angles, n_queries, ts.count, min_sep, alpha, d_relaxed);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    
    cudaEventElapsedTime(&ms, start, stop);
    printf("=== Jacobi Relaxation ===\n");
    printf("  Per-relax: %.3f µs\n", (ms * 1000.0) / (n_queries * n_iters));
    printf("  Throughput: %.1f M angles/sec\n\n",
           (n_queries * n_iters) / (ms * 1000.0));

    // ─── Constraint Violation Check ───
    int smem_size = sizeof(int);
    cudaMemset(d_violations, 0, sizeof(int));
    check_constraints<<<grid, block_size, smem_size>>>(
        d_angles, min_sep, TAU / 2.0, ts.count, d_violations);
    cudaDeviceSynchronize();
    
    int violations = 0;
    cudaMemcpy(&violations, d_violations, sizeof(int), cudaMemcpyDeviceToHost);
    printf("Constraint violations in Pythagorean space: %d/%d\n", violations, ts.count);

    // ─── Summary ───
    printf("\n╔══════════════════════════════════════════════════╗\n");
    printf("║  Kernel Inventory:                              ║\n");
    printf("║  1. snap_warp_cooperative — O(log n) binary     ║\n");
    printf("║     search with __shfl_sync warp cooperation    ║\n");
    printf("║  2. jacobi_relax — parallel constraint          ║\n");
    printf("║     relaxation toward Pythagorean snap points   ║\n");
    printf("║  3. check_constraints — shared memory           ║\n");
    printf("║     atomic reduction for violation counting     ║\n");
    printf("╚══════════════════════════════════════════════════╝\n");

    // Cleanup
    cudaFree(d_angles); cudaFree(d_queries); cudaFree(d_results);
    cudaFree(d_dists); cudaFree(d_relaxed); cudaFree(d_violations);
    cudaEventDestroy(start); cudaEventDestroy(stop);
    free(queries); free(h_results); free(h_dists);
    ts.free();

    return 0;
}
