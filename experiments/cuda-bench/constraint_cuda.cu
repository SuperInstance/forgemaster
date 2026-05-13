/**
 * constraint_cuda.cu — CUDA constraint checking kernels for Eisenstein lattice
 * 
 * Kernels:
 *   1. eisenstein_snap_kernel     — Snap float2 points to nearest lattice point
 *   2. dodecet_encode_kernel     — Map lattice points to 12-bit dodecet codes
 *   3. constraint_check_kernel   — 3-tier membership check against constraint bitset
 *   4. holonomy_batch_kernel     — Walk K cycles simultaneously, one warp per cycle
 *   5. cyclotomic_rotation_kernel — Apply Q(ζ₁₅) rotation to N points
 *
 * Compile: nvcc -O3 -arch=sm_86 -std=c++14 constraint_cuda.cu reference.cpp -o constraint_cuda
 */

#include <cuda_runtime.h>
#include <vector_types.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cfloat>
#include <cstring>
#include <cassert>

// -----------------------------------------------------------------------
// Compile-time constants
// -----------------------------------------------------------------------
constexpr double PI  = 3.14159265358979323846;
constexpr double SQRT3 = 1.73205080756887729352;
constexpr double PHI = 1.61803398874989484820;  // golden ratio
constexpr int N_MAX = 1 << 20;
constexpr int WARPSIZE = 32;

// -----------------------------------------------------------------------
// CUDA error checking macro
// -----------------------------------------------------------------------
#define CUDA_CHECK(call) do {                                         \
    cudaError_t err = call;                                           \
    if (err != cudaSuccess) {                                         \
        fprintf(stderr, "CUDA error %d at %s:%d: %s\n",              \
                err, __FILE__, __LINE__, cudaGetErrorString(err));    \
        exit(EXIT_FAILURE);                                           \
    }                                                                 \
} while(0)

// Dodecet fundamental domain: ring Z[ω] where ω = e^{2πi/12}
// The dodecet code is a 12-bit value. One scheme: encode which of 12
// regions the lattice point falls into, based on angle modulo 30°.
// Mapping: lattice point → quadrant sector → 12-bit code.
// We use a compact mapping: code = ((θ / 30°) mod 12) as 4 bits + 
// additional bits for radial tier.
__device__ __constant__ uint16_t dodecet_lut[4096]; // placeholder — filled at launch

// -----------------------------------------------------------------------
// 1. Eisenstein Snap Kernel
// -----------------------------------------------------------------------
// Each thread handles one point.
// For Eisenstein integers Z[ω], ω = e^{2πi/6} = (1 + sqrt(-3))/2
// Given a float2 point (x,y), find nearest lattice point (a,b) in the
// Eisenstein triangular lattice.
// Lattice basis: v1 = (1,0), v2 = (1/2, sqrt(3)/2)
// Distance from point to lattice point.
__global__ void eisenstein_snap_kernel(
    const float2* __restrict__ points,
    float epsilon,
    int2* __restrict__ lattice_points,
    float* __restrict__ distances,
    int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    // Shared memory for constants
    __shared__ float sh_sqrt3;
    if (threadIdx.x == 0) {
        sh_sqrt3 = (float)SQRT3;
    }
    __syncthreads();

    float2 p = points[idx];

    // Convert to lattice coordinates
    // For Eisenstein lattice: point = a*v1 + b*v2
    // v1 = (1,0), v2 = (1/2, sqrt3/2)
    // Given (x,y), solve: x = a + b/2, y = b*sqrt3/2
    // b = 2*y/sqrt3, a = x - b/2
    
    // Compute fractional coordinates in lattice basis
    float b_frac = 2.0f * p.y / sh_sqrt3;
    float a_frac = p.x - 0.5f * b_frac;

    // Round to nearest integer (with tie-breaking)
    float a_round = rintf(a_frac);
    float b_round = rintf(b_frac);

    // Euclidean distance in original coordinates
    float dx = (a_round + 0.5f * b_round) - p.x;
    float dy = (0.5f * sh_sqrt3 * b_round) - p.y;
    float dist = sqrtf(dx * dx + dy * dy);

    lattice_points[idx] = {(int)a_round, (int)b_round};
    distances[idx] = dist;
}

// -----------------------------------------------------------------------
// 2. Dodecet Encode Kernel
// -----------------------------------------------------------------------
// Maps int2 lattice points to 12-bit dodecet codes.
// The dodecet corresponds to: the fundamental domain cell index in the
// hexagonal → dodecagonal refinement.
__constant__ uint16_t dodecet_ring[24];  // 24 sectors of 15° each

__global__ void dodecet_encode_kernel(
    const int2* __restrict__ lattice_points,
    uint16_t* __restrict__ dodecet_codes,
    int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    int2 lp = lattice_points[idx];

    // Convert lattice (a,b) to Cartesian
    float x = (float)lp.x + 0.5f * (float)lp.y;
    float y = 0.5f * (float)SQRT3 * (float)lp.y;

    // Compute angle, map to dodecet code
    // Dodecagon = 12 sides, each 30°. We divide the circle into 12 sectors.
    float angle = atan2f(y, x); // [-π, π]
    if (angle < 0.0f) angle += 2.0f * (float)PI;
    
    // 12 sectors of 30° each
    int sector = (int)(angle / ((float)PI / 6.0f));
    if (sector >= 12) sector = 11;
    
    // Add radial level (up to 4 bits to fit in uint16_t)
    float r = sqrtf(x * x + y * y);
    int radial = (int)(r / 2.0f);
    if (radial > 15) radial = 15;

    // 12-bit code: lower 4 bits = radial, next 4 bits = sector, upper 4 bits = parity/extension
    uint16_t code = (uint16_t)((radial & 0xF) | ((sector & 0xF) << 4));

    // Add parity bit for error detection
    __syncthreads(); // just for device function barrier consistency
    uint16_t parity = 0;
    uint16_t temp = code;
    for (int i = 0; i < 8; i++) {
        parity ^= (temp & 1);
        temp >>= 1;
    }
    code |= (parity << 8);

    dodecet_codes[idx] = code;
}

// -----------------------------------------------------------------------
// 3. Three-tier Constraint Check Kernel
// -----------------------------------------------------------------------
// Tier 1: Snap to lattice, check dodecet code against bitset (O(1))
// Tier 2: (future) neighborhood expand
// Tier 3: (future) exact check
// Uses warp-level voting for fast batch decisions.

__global__ void constraint_check_kernel(
    const float2* __restrict__ query_points,
    const uint32_t* __restrict__ constraint_bitset,  // 4096 bits = 128 uint32_t
    bool* __restrict__ results,
    float epsilon,
    int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    // --- Tier 1: Snap to Eisenstein lattice ---
    __shared__ float sh_sqrt3;
    if (threadIdx.x == 0) {
        sh_sqrt3 = (float)SQRT3;
    }
    __syncthreads();

    float2 p = query_points[idx];

    // Snap to lattice
    float b_frac = 2.0f * p.y / sh_sqrt3;
    float a_frac = p.x - 0.5f * b_frac;
    float a_round = rintf(a_frac);
    float b_round = rintf(b_frac);

    // Convert back to Cartesian
    float x = a_round + 0.5f * b_round;
    float y = 0.5f * sh_sqrt3 * b_round;

    // Dodecet encode
    float angle = atan2f(y, x);
    if (angle < 0.0f) angle += 2.0f * (float)PI;
    int sector = (int)(angle / ((float)PI / 6.0f));
    if (sector >= 12) sector = 11;
    float r = sqrtf(x * x + y * y);
    int radial = (int)(r / 2.0f);
    if (radial > 15) radial = 15;
    uint16_t code = (uint16_t)((radial & 0xF) | ((sector & 0xF) << 4));

    // Check bitset: code is 12-bit, bitset is 4096 bits
    int word_idx = (code >> 5) & 0x7F;  // 128 words max
    int bit_idx  = code & 0x1F;
    bool is_member = (constraint_bitset[word_idx] >> bit_idx) & 1U;

    // --- Tier 2: Neighborhood expansion if not found ---
    if (!is_member) {
        // Check neighbors: 8 neighboring lattice points
        static const int neigh_da[8] = {1, 0, -1, -1, 0, 1, 1, -1};
        static const int neigh_db[8] = {0, 1, 1, 0, -1, -1, 1, -1};
        
        for (int ni = 0; ni < 8; ni++) {
            int na = (int)a_round + neigh_da[ni];
            int nb = (int)b_round + neigh_db[ni];

            // Re-encode neighbor
            float nx = (float)na + 0.5f * (float)nb;
            float ny = 0.5f * sh_sqrt3 * (float)nb;
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

    results[idx] = is_member;

    // --- Warp-level voting (every warp leader does a batch check) ---
    int lane = threadIdx.x & 0x1F;
    int warp_id = threadIdx.x >> 5;
    __shared__ int warp_ballots[32]; // max 1024 threads / 32 = 32 warps

    if (lane == 0) {
        // Tally this warp's results using a single warp vote
        unsigned int vote = __ballot_sync(0xFFFFFFFF, is_member);
        warp_ballots[warp_id] = __popc(vote);
    }
    __syncthreads();

    if (threadIdx.x == 0) {
        int total_members = 0;
        int num_warps = (blockDim.x + 31) / 32;
        for (int w = 0; w < num_warps; w++) {
            total_members += warp_ballots[w];
        }
        // Could output total_members; for now we just note it
        // (future: cooperative kernel launch)
    }
}

// -----------------------------------------------------------------------
// 4. Holonomy Batch Kernel
// -----------------------------------------------------------------------
// Walk K cycles of length L simultaneously.
// One warp per cycle — 32 threads cooperate on one cycle.
// Holonomy = winding number * error bound check.
// Returns holonomy value for each cycle.

__global__ void holonomy_batch_kernel(
    const float2* __restrict__ cycle_vertices,  // [K * L] flattened
    int K,
    int L,
    float* __restrict__ holonomy_values,
    float epsilon)
{
    // Each block handles one cycle, each thread handles one edge in the cycle
    int cycle_id = blockIdx.x;
    if (cycle_id >= K) return;

    int lane = threadIdx.x;  // lane = edge index in this cycle (0..L-1)

    __shared__ float edge_contribs[32]; // max 32 edges per cycle

    // Each thread loads one vertex pair (current and next)
    // Compute turning angle at this vertex
    // For holonomy, sum the exterior angles around the cycle
    // Simple version: angle = atan2(cross, dot) between consecutive edges
    
    // We need 3 consecutive vertices for proper angle, so use shared
    __shared__ float2 verts_in[32];

    if (lane < L) {
        verts_in[lane] = cycle_vertices[cycle_id * L + lane];
    }
    __syncthreads();

    // Compute edges
    float2 e_in, e_out;
    int prev = (lane - 1 + L) % L;
    int next = (lane + 1) % L;
    
    e_in.x  = verts_in[lane].x - verts_in[prev].x;
    e_in.y  = verts_in[lane].y - verts_in[prev].y;
    e_out.x = verts_in[next].x - verts_in[lane].x;
    e_out.y = verts_in[next].y - verts_in[lane].y;

    // Normalize
    float in_norm  = sqrtf(e_in.x * e_in.x + e_in.y * e_in.y);
    float out_norm = sqrtf(e_out.x * e_out.x + e_out.y * e_out.y);
    if (in_norm > 1e-8f)  { e_in.x /= in_norm;  e_in.y /= in_norm; }
    if (out_norm > 1e-8f) { e_out.x /= out_norm; e_out.y /= out_norm; }

    // Turning angle (exterior angle modulo 2π)
    float cross = e_in.x * e_out.y - e_in.y * e_out.x;
    float dot   = e_in.x * e_out.x + e_in.y * e_out.y;
    float angle = atan2f(cross, dot);

    edge_contribs[lane] = angle;
    __syncthreads();

    // Warp reduction to sum all angles
    // For L <= 32, one warp reduction does the job
    if (lane < L) {
        float sum = edge_contribs[lane];
        for (int offset = 16; offset > 0; offset >>= 1) {
            sum += __shfl_xor_sync(0xFFFFFFFF, sum, offset);
        }

        if (lane == 0) {
            // Total curvature = sum of exterior angles
            // For a closed polygon, should be 2π or -2π (winding number ±1)
            // Holonomy = |total_curvature - 2π|
            float total = sum;
            float holonomy = fabsf(total - 2.0f * (float)PI);

            // Compare against nε bound where n = L
            float bound = (float)L * epsilon;
            holonomy = (holonomy <= bound) ? 0.0f : holonomy;

            holonomy_values[cycle_id] = holonomy;
        }
    }
}

// -----------------------------------------------------------------------
// 5. Cyclotomic Field Rotation Kernel
// -----------------------------------------------------------------------
// Apply Q(ζ₁₅) rotation matrix to N points.
// ζ₁₅ = e^{2πi/15} is a primitive 15th root of unity.
// The rotation matrix in ℝ² is:
//   R(θ) = [cos θ  -sin θ; sin θ  cos θ]
// For cyclotomic field Q(ζ₁₅), rotations by multiples of 2π/15 = 24°
// are exact (algebraic). We test at three angles:
//   θ=0 (hexagonal), θ=π/10 (intermediate), θ=arctan(φ) (Penrose)
// 
// Uses __fmul_rn and __fadd_rn for consistent FP32 arithmetic.

__global__ void cyclotomic_rotation_kernel(
    const float2* __restrict__ input_points,
    float2* __restrict__ output_points,
    float cos_theta,
    float sin_theta,
    int N)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= N) return;

    float2 p = input_points[idx];

    // Apply rotation using round-to-nearest-even multiply-add
    float x_out = __fadd_rn(__fmul_rn(p.x, cos_theta), __fmul_rn(-p.y, sin_theta));
    float y_out = __fadd_rn(__fmul_rn(p.x, sin_theta), __fmul_rn(p.y, cos_theta));

    output_points[idx] = {x_out, y_out};
}

// -----------------------------------------------------------------------
// Host launch wrappers
// -----------------------------------------------------------------------

// Snaps N points to Eisenstein lattice, returns lattice points and distances
extern "C" void launch_eisenstein_snap(
    const float2* d_points,
    float epsilon,
    int2* d_lattice,
    float* d_distances,
    int N,
    cudaStream_t stream = 0)
{
    if (N <= 0) return;
    int threads = 256;
    int blocks  = (N + threads - 1) / threads;
    if (blocks > 65535) blocks = 65535;

    eisenstein_snap_kernel<<<blocks, threads, 0, stream>>>(d_points, epsilon, d_lattice, d_distances, N);
    CUDA_CHECK(cudaGetLastError());
}

// Encodes N lattice points to dodecet codes
extern "C" void launch_dodecet_encode(
    const int2* d_lattice,
    uint16_t* d_codes,
    int N,
    cudaStream_t stream = 0)
{
    if (N <= 0) return;
    int threads = 256;
    int blocks  = (N + threads - 1) / threads;
    if (blocks > 65535) blocks = 65535;

    dodecet_encode_kernel<<<blocks, threads, 0, stream>>>(d_lattice, d_codes, N);
    CUDA_CHECK(cudaGetLastError());
}

// Checks N query points against constraint bitset
extern "C" void launch_constraint_check(
    const float2* d_queries,
    const uint32_t* d_bitset,
    bool* d_results,
    float epsilon,
    int N,
    cudaStream_t stream = 0)
{
    if (N <= 0) return;
    int threads = 256;
    int blocks  = (N + threads - 1) / threads;
    if (blocks > 65535) blocks = 65535;

    constraint_check_kernel<<<blocks, threads, 0, stream>>>(d_queries, d_bitset, d_results, epsilon, N);
    CUDA_CHECK(cudaGetLastError());
}

// Computes holonomy for K cycles of length L
extern "C" void launch_holonomy_batch(
    const float2* d_cycle_vertices,
    int K,
    int L,
    float* d_holonomy,
    float epsilon,
    cudaStream_t stream = 0)
{
    if (K <= 0 || L <= 0) return;
    int threads = 32;
    
    holonomy_batch_kernel<<<K, threads, 0, stream>>>(d_cycle_vertices, K, L, d_holonomy, epsilon);
    CUDA_CHECK(cudaGetLastError());
}

// Rotates N points by angle theta
extern "C" void launch_cyclotomic_rotation(
    const float2* d_input,
    float2* d_output,
    double theta,
    int N,
    cudaStream_t stream = 0)
{
    if (N <= 0) return;
    int threads = 256;
    int blocks  = (N + threads - 1) / threads;
    if (blocks > 65535) blocks = 65535;

    float cos_t = (float)cos(theta);
    float sin_t = (float)sin(theta);

    cyclotomic_rotation_kernel<<<blocks, threads, 0, stream>>>(d_input, d_output, cos_t, sin_t, N);
    CUDA_CHECK(cudaGetLastError());
}

// -----------------------------------------------------------------------
// Benchmark helpers
// -----------------------------------------------------------------------

extern "C" double benchmark_kernel(
    const char* name,
    void (*launch_func)(cudaStream_t),
    int warmup_iters,
    int benchmark_iters,
    cudaStream_t stream)
{
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    // Warmup
    for (int i = 0; i < warmup_iters; i++) {
        launch_func(stream);
    }
    CUDA_CHECK(cudaStreamSynchronize(stream));

    // Benchmark
    CUDA_CHECK(cudaEventRecord(start, stream));
    for (int i = 0; i < benchmark_iters; i++) {
        launch_func(stream);
    }
    CUDA_CHECK(cudaEventRecord(stop, stream));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float ms;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));
    double avg_ms = ms / benchmark_iters;

    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));

    printf("  %-40s %8.3f ms (avg over %d iters)\n", name, avg_ms, benchmark_iters);

    return avg_ms;
}

// -----------------------------------------------------------------------
// Main: correctness tests + benchmarks
// -----------------------------------------------------------------------

extern "C" int run_tests_and_benchmarks(int benchmark_mode);

int main(int argc, char** argv)
{
    printf("==============================================================\n");
    printf("  CUDA Constraint Checking Kernel Benchmarks\n");
    printf("  Compiled for sm_86 (RTX 4050 laptop compute capability)\n");
    printf("==============================================================\n\n");

    int benchmark_mode = (argc > 1 && strcmp(argv[1], "--bench") == 0) ? 1 : 0;

    int result = run_tests_and_benchmarks(benchmark_mode);
    return result;
}
