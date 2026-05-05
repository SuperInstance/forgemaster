// ============================================================================
// exp51_csp_solver.cu — GPU-Accelerated CSP Solver with BitmaskDomain
// ============================================================================
// Extends BitmaskDomain concept: each variable's domain is a 64-bit bitmask.
// Bit i set → value i is in the domain. GPU parallelizes backtracking search
// across thousands of search-tree branches simultaneously.
//
// Problems: N-Queens (N=8,10,12), Graph Coloring (Petersen, random graphs)
// Algorithms: AC-3 arc consistency, parallel backtracking with bitmask pruning
//
// Compile: nvcc -arch=sm_86 -O3 -o exp51_csp_solver exp51_csp_solver.cu
// Fallback: nvcc -arch=sm_75 -O3 -o exp51_csp_solver exp51_csp_solver.cu
// ============================================================================

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <chrono>
#include <vector>
#include <algorithm>
#include <bitset>
#include <iostream>

// ============================================================================
// Constants
// ============================================================================
#define MAX_N 16          // Max variables (N-Queens board size)
#define MAX_DOMAIN 64     // 64-bit bitmask supports up to 64 values
#define MAX_THREADS 256   // Threads per block
#define MAX_BLOCKS 1024   // Max blocks
#define WARP_SIZE 32

// ============================================================================
// BitmaskDomain Helpers (CPU)
// ============================================================================
// Cross-platform popcount and ffs
#if defined(__CUDA_ARCH__)
__host__ __device__ __forceinline__ int x_popcll(uint64_t x) { return __popcll(x); }
__host__ __device__ __forceinline__ int x_ffsll(uint64_t x) { return __ffsll(x); }
#else
static inline int x_popcll(uint64_t x) { return __builtin_popcountll(x); }
static inline int x_ffsll(uint64_t x) { return __builtin_ffsll(x); }
#endif

struct BitmaskDomain {
    uint64_t mask;
    int size;

    __host__ __device__ BitmaskDomain() : mask(0), size(0) {}
    __host__ __device__ BitmaskDomain(uint64_t m) : mask(m) { size = x_popcll(m); }

    __host__ __device__ static BitmaskDomain full(int n) {
        return BitmaskDomain((1ULL << n) - 1);
    }

    __host__ __device__ void remove(int val) {
        uint64_t bit = 1ULL << val;
        if (mask & bit) {
            mask &= ~bit;
            size = x_popcll(mask);
        }
    }

    __host__ __device__ bool contains(int val) const {
        return (mask >> val) & 1;
    }

    __host__ __device__ bool isEmpty() const {
        return mask == 0;
    }

    __host__ __device__ int first() const {
        return x_ffsll(mask) - 1;
    }

    __host__ __device__ int popcount() const {
        return x_popcll(mask);
    }
};

// ============================================================================
// N-Queens: Constraint Propagation via Bitmask
// ============================================================================
// Row i queen constraints: columns, major diagonal, minor diagonal
// Each bitmask captures the forbidden positions for subsequent rows.

// CPU sequential N-Queens solver with bitmask domains
uint64_t nqueens_cpu(int n, int row, uint64_t cols, uint64_t diag1, uint64_t diag2) {
    if (row == n) return 1;

    uint64_t occupied = cols | diag1 | diag2;
    uint64_t available = ((1ULL << n) - 1) & ~occupied;

    uint64_t count = 0;
    while (available) {
        int col = __builtin_ffsll(available) - 1;
        available &= available - 1;  // clear lowest set bit

        count += nqueens_cpu(n, row + 1,
            cols | (1ULL << col),
            (diag1 | (1ULL << col)) << 1,
            (diag2 | (1ULL << col)) >> 1);
    }
    return count;
}

// ============================================================================
// GPU N-Queens: Kernel 1 — Generate partial assignments at depth D
// Each thread gets one partial assignment to explore further on GPU
// ============================================================================

// Structure to hold a partial N-Queens assignment state
struct NQueensState {
    uint64_t cols;
    uint64_t diag1;
    uint64_t diag2;
    int row;
    int padding;
};

// Placeholder: partial generation done on CPU (see nqueens_generate_partials)

// ============================================================================
// GPU N-Queens: Parallel Backtracking Kernel
// ============================================================================
// Each thread receives a partial assignment and completes the search.

__global__ void nqueens_gpu_kernel(
    int n,
    const NQueensState* __restrict__ initial_states,
    int num_initial,
    uint64_t* __restrict__ total_solutions,
    uint64_t* __restrict__ total_nodes
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_initial) return;

    uint64_t local_solutions = 0;
    uint64_t local_nodes = 0;

    // Stack-based DFS from the partial assignment
    // Stack entries: (row, cols, diag1, diag2)
    struct StackEntry {
        uint64_t cols, diag1, diag2, available;
        int row;
    };

    // Use local arrays for stack (limited depth for GPU)
    StackEntry stack[MAX_N + 1];
    int sp = 0;

    // Initialize from partial state
    NQueensState init = initial_states[tid];
    uint64_t cols = init.cols;
    uint64_t diag1 = init.diag1;
    uint64_t diag2 = init.diag2;
    int row = init.row;

    // Compute available positions for current row
    uint64_t occupied = cols | diag1 | diag2;
    uint64_t available = ((1ULL << n) - 1) & ~occupied;

    // Push current state
    stack[sp] = {cols, diag1, diag2, available, row};
    sp++;

    while (sp > 0) {
        sp--;
        StackEntry cur = stack[sp];

        if (cur.row == n) {
            local_solutions++;
            continue;
        }

        local_nodes++;

        uint64_t avail = cur.available;
        while (avail) {
            int col = __ffsll(avail) - 1;
            avail &= avail - 1;

            uint64_t new_cols = cur.cols | (1ULL << col);
            uint64_t new_diag1 = (cur.diag1 | (1ULL << col)) << 1;
            uint64_t new_diag2 = (cur.diag2 | (1ULL << col)) >> 1;
            int new_row = cur.row + 1;

            uint64_t new_occupied = new_cols | new_diag1 | new_diag2;
            uint64_t new_available = ((1ULL << n) - 1) & ~new_occupied;

            if (sp < MAX_N) {
                stack[sp] = {new_cols, new_diag1, new_diag2, new_available, new_row};
                sp++;
            }
        }
    }

    // Atomically add to global counters (uint64 atomic via CAS loop)
    unsigned long long* sol_ull = (unsigned long long*)total_solutions;
    unsigned long long* nodes_ull = (unsigned long long*)total_nodes;
    unsigned long long old_val, new_val;
    do {
        old_val = *sol_ull;
        new_val = old_val + local_solutions;
    } while (atomicCAS(sol_ull, old_val, new_val) != old_val);
    do {
        old_val = *nodes_ull;
        new_val = old_val + local_nodes;
    } while (atomicCAS(nodes_ull, old_val, new_val) != old_val);
}

// ============================================================================
// CPU-side N-Queens partial state generator
// Enumerate all valid partial assignments to a given depth
// ============================================================================
std::vector<NQueensState> nqueens_generate_partials(int n, int depth) {
    std::vector<NQueensState> result;

    // Iterative DFS using a stack
    struct StackEntry {
        uint64_t cols, diag1, diag2;
        int row;
    };

    // Use heap-allocated vector for stack (can grow large for N>=10)
    std::vector<StackEntry> stack;
    stack.reserve(4096);
    stack.push_back({0, 0, 0, 0});

    while (!stack.empty()) {
        StackEntry cur = stack.back();
        stack.pop_back();

        if (cur.row == depth) {
            NQueensState s;
            s.cols = cur.cols;
            s.diag1 = cur.diag1;
            s.diag2 = cur.diag2;
            s.row = cur.row;
            s.padding = 0;
            result.push_back(s);
            continue;
        }

        uint64_t occupied = cur.cols | cur.diag1 | cur.diag2;
        uint64_t available = ((1ULL << n) - 1) & ~occupied;

        while (available) {
            int col = __builtin_ffsll(available) - 1;
            available &= available - 1;

            stack.push_back({cur.cols | (1ULL << col),
                             (cur.diag1 | (1ULL << col)) << 1,
                             (cur.diag2 | (1ULL << col)) >> 1,
                             cur.row + 1});
        }
    }

    return result;
}

// ============================================================================
// GPU N-Queens Solver (Full Pipeline)
// ============================================================================
struct SolverResult {
    uint64_t solutions;
    uint64_t nodes;
    double time_ms;
    double throughput;  // nodes/sec
};

SolverResult solve_nqueens_gpu(int n) {
    SolverResult result = {};
    auto t0 = std::chrono::high_resolution_clock::now();

    // Choose split depth: we want enough partials to fill GPU but not too many
    int split_depth = std::min(n / 2, 4);
    if (n <= 8) split_depth = 3;
    if (n <= 4) split_depth = 1;

    // Generate partial assignments on CPU
    auto partials = nqueens_generate_partials(n, split_depth);
    int num_partials = (int)partials.size();

    printf("  N=%d: Generated %d partial assignments at depth %d\n", n, num_partials, split_depth);

    if (num_partials == 0) {
        // Edge case
        result.solutions = nqueens_cpu(n, 0, 0, 0, 0);
        result.time_ms = 0;
        result.throughput = 0;
        result.nodes = 0;
        return result;
    }

    // Allocate GPU memory
    NQueensState* d_states;
    uint64_t* d_solutions;
    uint64_t* d_nodes;

    cudaMalloc(&d_states, num_partials * sizeof(NQueensState));
    cudaMalloc(&d_solutions, sizeof(uint64_t));
    cudaMalloc(&d_nodes, sizeof(uint64_t));

    cudaMemset(d_solutions, 0, sizeof(uint64_t));
    cudaMemset(d_nodes, 0, sizeof(uint64_t));
    cudaMemcpy(d_states, partials.data(), num_partials * sizeof(NQueensState), cudaMemcpyHostToDevice);

    // Launch kernel
    int threads = std::min(MAX_THREADS, num_partials);
    int blocks = (num_partials + threads - 1) / threads;
    blocks = std::min(blocks, MAX_BLOCKS);

    auto kernel_start = std::chrono::high_resolution_clock::now();

    nqueens_gpu_kernel<<<blocks, threads>>>(n, d_states, num_partials, d_solutions, d_nodes);
    cudaDeviceSynchronize();

    auto kernel_end = std::chrono::high_resolution_clock::now();

    // Copy results back
    cudaMemcpy(&result.solutions, d_solutions, sizeof(uint64_t), cudaMemcpyDeviceToHost);
    cudaMemcpy(&result.nodes, d_nodes, sizeof(uint64_t), cudaMemcpyDeviceToHost);

    cudaFree(d_states);
    cudaFree(d_solutions);
    cudaFree(d_nodes);

    result.time_ms = std::chrono::duration<double, std::milli>(kernel_end - kernel_start).count();
    result.throughput = (result.time_ms > 0) ? (result.nodes / (result.time_ms / 1000.0)) : 0;

    auto total_end = std::chrono::high_resolution_clock::now();
    double total_ms = std::chrono::duration<double, std::milli>(total_end - t0).count();

    printf("  GPU kernel: %.3f ms, total (incl CPU partial gen): %.3f ms\n", result.time_ms, total_ms);

    return result;
}

// ============================================================================
// Graph Coloring CSP Solver
// ============================================================================
// Given an adjacency matrix, find the number of valid k-colorings.
// Uses bitmask domains and AC-3 for constraint propagation.

struct GraphColoringInstance {
    int num_vertices;
    int num_colors;
    uint64_t adj_matrix[MAX_N];  // adj_matrix[i] bit j set → edge (i,j)
};

// CPU Graph Coloring solver with bitmask backtracking
uint64_t graph_coloring_cpu(const GraphColoringInstance& inst, int vertex, uint64_t* colors_used) {
    if (vertex == inst.num_vertices) return 1;

    uint64_t forbidden = 0;
    for (int i = 0; i < vertex; i++) {
        if (inst.adj_matrix[vertex] & (1ULL << i)) {
            forbidden |= (1ULL << colors_used[i]);
        }
    }

    uint64_t available = ((1ULL << inst.num_colors) - 1) & ~forbidden;
    uint64_t count = 0;

    while (available) {
        int color = __builtin_ffsll(available) - 1;
        available &= available - 1;
        colors_used[vertex] = color;
        count += graph_coloring_cpu(inst, vertex + 1, colors_used);
    }

    return count;
}

// ============================================================================
// AC-3 Arc Consistency for Graph Coloring (CPU)
// ============================================================================
struct AC3Domain {
    uint64_t domains[MAX_N];  // domain bitmask for each variable
};

bool ac3(GraphColoringInstance& inst, AC3Domain& ac3d) {
    // Initialize domains from adjacency
    // For graph coloring, domains start as full (all colors available)
    // Arc consistency: for each edge (i,j), remove color c from i's domain
    //   if j has only color c available

    // Worklist: pairs (i,j) where i and j are adjacent
    struct Arc { int i, j; };
    std::vector<Arc> worklist;

    for (int i = 0; i < inst.num_vertices; i++) {
        ac3d.domains[i] = (1ULL << inst.num_colors) - 1;
        for (int j = 0; j < inst.num_vertices; j++) {
            if (inst.adj_matrix[i] & (1ULL << j)) {
                worklist.push_back({i, j});
            }
        }
    }

    while (!worklist.empty()) {
        Arc arc = worklist.back();
        worklist.pop_back();

        int i = arc.i, j = arc.j;
        uint64_t di = ac3d.domains[i];
        uint64_t dj = ac3d.domains[j];

        // For each value in di, check if there exists a supporting value in dj
        uint64_t new_di = 0;
        uint64_t temp = di;
        while (temp) {
            int ci = __builtin_ffsll(temp) - 1;
            temp &= temp - 1;

            // Value ci is supported if dj has any value != ci
            uint64_t supporting = dj & ~(1ULL << ci);
            if (supporting) {
                new_di |= (1ULL << ci);
            }
        }

        if (new_di != di) {
            ac3d.domains[i] = new_di;
            if (new_di == 0) return false;  // Domain wipeout

            // Add all neighbors of i (except j) to worklist
            uint64_t neighbors = inst.adj_matrix[i];
            while (neighbors) {
                int k = __builtin_ffsll(neighbors) - 1;
                neighbors &= neighbors - 1;
                if (k != j) {
                    worklist.push_back({k, i});
                }
            }
        }
    }

    return true;
}

// ============================================================================
// Graph Coloring with AC-3 + Backtracking (CPU)
// ============================================================================
uint64_t graph_coloring_ac3_cpu(const GraphColoringInstance& inst, int vertex,
                                 uint64_t* colors_used, uint64_t* domains) {
    if (vertex == inst.num_vertices) return 1;

    // Compute current domain for this vertex
    uint64_t forbidden = 0;
    for (int i = 0; i < vertex; i++) {
        if (inst.adj_matrix[vertex] & (1ULL << i)) {
            forbidden |= (1ULL << colors_used[i]);
        }
    }

    uint64_t available = domains[vertex] & ~forbidden;
    uint64_t count = 0;

    while (available) {
        int color = __builtin_ffsll(available) - 1;
        available &= available - 1;
        colors_used[vertex] = color;
        count += graph_coloring_ac3_cpu(inst, vertex + 1, colors_used, domains);
    }

    return count;
}

// ============================================================================
// GPU Graph Coloring Kernel
// ============================================================================

struct GCState {
    uint64_t colors_used;  // packed: 4 bits per vertex, max 16 vertices
    int vertex;
    int padding;
};

__global__ void graph_coloring_gpu_kernel(
    int num_vertices, int num_colors,
    const uint64_t* __restrict__ adj_matrix,
    const GCState* __restrict__ initial_states,
    int num_initial,
    uint64_t* __restrict__ total_solutions,
    uint64_t* __restrict__ total_nodes
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_initial) return;

    uint64_t local_solutions = 0;
    uint64_t local_nodes = 0;
    uint64_t full_mask = (1ULL << num_colors) - 1;

    // Stack for DFS
    struct SE {
        uint64_t colors_used;
        int vertex;
        uint64_t available;
    };

    SE stack[MAX_N + 1];
    int sp = 0;

    GCState init = initial_states[tid];

    // Compute available colors for current vertex
    uint64_t forbidden = 0;
    for (int i = 0; i < init.vertex; i++) {
        int c = (init.colors_used >> (i * 4)) & 0xF;
        if (adj_matrix[init.vertex] & (1ULL << i)) {
            forbidden |= (1ULL << c);
        }
    }
    uint64_t available = full_mask & ~forbidden;

    stack[sp++] = {init.colors_used, init.vertex, available};

    while (sp > 0) {
        SE cur = stack[--sp];

        if (cur.vertex == num_vertices) {
            local_solutions++;
            continue;
        }

        local_nodes++;

        uint64_t avail = cur.available;
        while (avail) {
            int color = __ffsll(avail) - 1;
            avail &= avail - 1;

            uint64_t new_colors = cur.colors_used | ((uint64_t)color << (cur.vertex * 4));
            int next = cur.vertex + 1;

            // Compute forbidden for next vertex
            uint64_t next_forbidden = 0;
            for (int j = 0; j < next; j++) {
                int c = (new_colors >> (j * 4)) & 0xF;
                if (adj_matrix[next] & (1ULL << j)) {
                    next_forbidden |= (1ULL << c);
                }
            }
            uint64_t next_avail = full_mask & ~next_forbidden;

            if (sp < MAX_N) {
                stack[sp++] = {new_colors, next, next_avail};
            }
        }
    }

    // Atomically add to global counters
    unsigned long long* sol_ull = (unsigned long long*)total_solutions;
    unsigned long long* nodes_ull = (unsigned long long*)total_nodes;
    unsigned long long old_val, new_val;
    do {
        old_val = *sol_ull;
        new_val = old_val + local_solutions;
    } while (atomicCAS(sol_ull, old_val, new_val) != old_val);
    do {
        old_val = *nodes_ull;
        new_val = old_val + local_nodes;
    } while (atomicCAS(nodes_ull, old_val, new_val) != old_val);
}

// CPU partial state generator for graph coloring
std::vector<GCState> gc_generate_partials(const GraphColoringInstance& inst, int depth) {
    std::vector<GCState> result;

    struct SE {
        uint64_t colors_used;
        int vertex;
    };

    std::vector<SE> vstack;
    vstack.reserve(4096);
    vstack.push_back({0, 0});

    while (!vstack.empty()) {
        SE cur = vstack.back();
        vstack.pop_back();

        if (cur.vertex == depth) {
            GCState s;
            s.colors_used = cur.colors_used;
            s.vertex = cur.vertex;
            s.padding = 0;
            result.push_back(s);
            continue;
        }

        uint64_t forbidden = 0;
        for (int i = 0; i < cur.vertex; i++) {
            int c = (cur.colors_used >> (i * 4)) & 0xF;
            if (inst.adj_matrix[cur.vertex] & (1ULL << i)) {
                forbidden |= (1ULL << c);
            }
        }

        uint64_t available = ((1ULL << inst.num_colors) - 1) & ~forbidden;

        while (available) {
            int color = __builtin_ffsll(available) - 1;
            available &= available - 1;

            uint64_t new_colors = cur.colors_used | ((uint64_t)color << (cur.vertex * 4));
            vstack.push_back({new_colors, cur.vertex + 1});
        }
    }

    return result;
}

// ============================================================================
// Problem Instances
// ============================================================================

// Petersen Graph: 10 vertices, 15 edges
GraphColoringInstance make_petersen_graph(int num_colors) {
    GraphColoringInstance inst = {};
    inst.num_vertices = 10;
    inst.num_colors = num_colors;

    // Petersen graph edges (0-indexed)
    int edges[][2] = {
        {0,1}, {1,2}, {2,3}, {3,4}, {4,0},  // outer pentagon
        {5,7}, {7,9}, {9,6}, {6,8}, {8,5},  // inner pentagram
        {0,5}, {1,6}, {2,7}, {3,8}, {4,9}   // spokes
    };

    for (auto& e : edges) {
        inst.adj_matrix[e[0]] |= (1ULL << e[1]);
        inst.adj_matrix[e[1]] |= (1ULL << e[0]);
    }

    return inst;
}

// Random graph generator
GraphColoringInstance make_random_graph(int n, int num_colors, double density, unsigned seed = 42) {
    GraphColoringInstance inst = {};
    inst.num_vertices = n;
    inst.num_colors = num_colors;

    srand(seed);
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            if ((double)rand() / RAND_MAX < density) {
                inst.adj_matrix[i] |= (1ULL << j);
                inst.adj_matrix[j] |= (1ULL << i);
            }
        }
    }

    return inst;
}

// ============================================================================
// GPU Graph Coloring Full Solver
// ============================================================================
SolverResult solve_graph_coloring_gpu(GraphColoringInstance& inst) {
    SolverResult result = {};
    auto t0 = std::chrono::high_resolution_clock::now();

    int split_depth = std::min(inst.num_vertices / 2, 4);
    if (inst.num_vertices <= 6) split_depth = 2;

    auto partials = gc_generate_partials(inst, split_depth);
    int num_partials = (int)partials.size();

    printf("  Graph %dV/%dC: Generated %d partials at depth %d\n",
           inst.num_vertices, inst.num_colors, num_partials, split_depth);

    if (num_partials == 0) {
        uint64_t colors[MAX_N] = {};
        result.solutions = graph_coloring_cpu(inst, 0, colors);
        result.time_ms = 0;
        return result;
    }

    // Allocate GPU memory
    uint64_t* d_adj;
    GCState* d_states;
    uint64_t* d_solutions;
    uint64_t* d_nodes;

    cudaMalloc(&d_adj, inst.num_vertices * sizeof(uint64_t));
    cudaMalloc(&d_states, num_partials * sizeof(GCState));
    cudaMalloc(&d_solutions, sizeof(uint64_t));
    cudaMalloc(&d_nodes, sizeof(uint64_t));

    cudaMemset(d_solutions, 0, sizeof(uint64_t));
    cudaMemset(d_nodes, 0, sizeof(uint64_t));
    cudaMemcpy(d_adj, inst.adj_matrix, inst.num_vertices * sizeof(uint64_t), cudaMemcpyHostToDevice);
    cudaMemcpy(d_states, partials.data(), num_partials * sizeof(GCState), cudaMemcpyHostToDevice);

    int threads = std::min(MAX_THREADS, num_partials);
    int blocks = (num_partials + threads - 1) / threads;
    blocks = std::min(blocks, MAX_BLOCKS);

    auto kernel_start = std::chrono::high_resolution_clock::now();

    graph_coloring_gpu_kernel<<<blocks, threads>>>(
        inst.num_vertices, inst.num_colors, d_adj, d_states, num_partials,
        d_solutions, d_nodes);
    cudaDeviceSynchronize();

    auto kernel_end = std::chrono::high_resolution_clock::now();

    cudaMemcpy(&result.solutions, d_solutions, sizeof(uint64_t), cudaMemcpyDeviceToHost);
    cudaMemcpy(&result.nodes, d_nodes, sizeof(uint64_t), cudaMemcpyDeviceToHost);

    cudaFree(d_adj);
    cudaFree(d_states);
    cudaFree(d_solutions);
    cudaFree(d_nodes);

    result.time_ms = std::chrono::duration<double, std::milli>(kernel_end - kernel_start).count();
    result.throughput = (result.time_ms > 0) ? (result.nodes / (result.time_ms / 1000.0)) : 0;

    return result;
}

// ============================================================================
// Main
// ============================================================================
int main() {
    cudaDeviceProp prop;
    int device;
    cudaGetDevice(&device);
    cudaGetDeviceProperties(&prop, device);

    printf("================================================================\n");
    printf("  GPU-Accelerated CSP Solver — BitmaskDomain Extensions\n");
    printf("================================================================\n");
    printf("  Device: %s\n", prop.name);
    printf("  SMs: %d, Warp: %d, Max threads/SM: %d\n",
           prop.multiProcessorCount, prop.warpSize, prop.maxThreadsPerMultiProcessor);
    printf("  Shared mem/block: %zu bytes\n", prop.sharedMemPerBlock);
    printf("  Global mem: %.1f GB\n", prop.totalGlobalMem / 1e9);
    printf("================================================================\n\n");

    // ========================================================================
    // N-Queens Benchmarks
    // ========================================================================
    printf("--- N-Queens ---\n");
    printf("%-6s %-12s %-12s %-16s %-16s %-12s %-12s\n",
           "N", "Solutions", "Nodes", "CPU (ms)", "GPU (ms)", "Speedup", "GPU Mnodes/s");
    printf("%s\n", std::string(86, '-').c_str());

    int nqueens_sizes[] = {8, 10, 12};

    // Test with N=8 first
    for (int n : nqueens_sizes) {
        printf("  Solving N=%d...\n", n);
        fflush(stdout);
        // CPU solve
        auto cpu_start = std::chrono::high_resolution_clock::now();
        uint64_t cpu_solutions = nqueens_cpu(n, 0, 0, 0, 0);
        auto cpu_end = std::chrono::high_resolution_clock::now();
        double cpu_ms = std::chrono::duration<double, std::milli>(cpu_end - cpu_start).count();

        // GPU solve
        auto gpu_result = solve_nqueens_gpu(n);

        double speedup = (gpu_result.time_ms > 0) ? cpu_ms / gpu_result.time_ms : 0;
        double mnodes = gpu_result.throughput / 1e6;

        // Verify correctness
        bool correct = (cpu_solutions == gpu_result.solutions);

        printf("%-6d %-12lu %-12lu %-16.3f %-16.3f %-12.2fx %-12.2f",
               n, cpu_solutions, gpu_result.nodes, cpu_ms, gpu_result.time_ms, speedup, mnodes);

        if (!correct) {
            printf(" *** MISMATCH (GPU=%lu, CPU=%lu) ***", gpu_result.solutions, cpu_solutions);
        } else {
            printf(" ✓");
        }
        printf("\n");
    }

    printf("\n");

    // ========================================================================
    // Graph Coloring Benchmarks
    // ========================================================================
    printf("--- Graph Coloring ---\n");
    printf("%-20s %-6s %-6s %-12s %-16s %-16s %-12s %-12s\n",
           "Graph", "V", "Colors", "Solutions", "CPU (ms)", "GPU (ms)", "Speedup", "GPU Mnodes/s");
    printf("%s\n", std::string(110, '-').c_str());

    // Petersen graph with 3 colors only (4 colors takes too long for CPU)
    for (int k = 3; k <= 3; k++) {
        auto inst = make_petersen_graph(k);

        // CPU solve
        uint64_t colors[MAX_N] = {};
        auto cpu_start = std::chrono::high_resolution_clock::now();
        uint64_t cpu_solutions = graph_coloring_cpu(inst, 0, colors);
        auto cpu_end = std::chrono::high_resolution_clock::now();
        double cpu_ms = std::chrono::duration<double, std::milli>(cpu_end - cpu_start).count();

        // GPU solve
        auto gpu_result = solve_graph_coloring_gpu(inst);

        double speedup = (gpu_result.time_ms > 0) ? cpu_ms / gpu_result.time_ms : 0;
        double mnodes = gpu_result.throughput / 1e6;

        bool correct = (cpu_solutions == gpu_result.solutions);

        printf("%-20s %-6d %-6d %-12lu %-16.3f %-16.3f %-12.2fx %-12.2f",
               "Petersen", inst.num_vertices, k, cpu_solutions, cpu_ms, gpu_result.time_ms, speedup, mnodes);
        if (!correct) printf(" *** MISMATCH ***");
        else printf(" ✓");
        printf("\n");
    }

    // Random graphs
    struct RTest { int n; int k; double density; const char* name; };
    RTest rtests[] = {
        {10, 3, 0.3, "Random-10-30%"},
        {12, 3, 0.25, "Random-12-25%"},
    };

    for (auto& t : rtests) {
        auto inst = make_random_graph(t.n, t.k, t.density);

        uint64_t colors[MAX_N] = {};
        auto cpu_start = std::chrono::high_resolution_clock::now();
        uint64_t cpu_solutions = graph_coloring_cpu(inst, 0, colors);
        auto cpu_end = std::chrono::high_resolution_clock::now();
        double cpu_ms = std::chrono::duration<double, std::milli>(cpu_end - cpu_start).count();

        auto gpu_result = solve_graph_coloring_gpu(inst);

        double speedup = (gpu_result.time_ms > 0) ? cpu_ms / gpu_result.time_ms : 0;
        double mnodes = gpu_result.throughput / 1e6;

        bool correct = (cpu_solutions == gpu_result.solutions);

        printf("%-20s %-6d %-6d %-12lu %-16.3f %-16.3f %-12.2fx %-12.2f",
               t.name, inst.num_vertices, t.k, cpu_solutions, cpu_ms, gpu_result.time_ms, speedup, mnodes);
        if (!correct) printf(" *** MISMATCH ***");
        else printf(" ✓");
        printf("\n");
    }

    // ========================================================================
    // AC-3 Demo
    // ========================================================================
    printf("\n--- AC-3 Arc Consistency Demo (Petersen, 3 colors) ---\n");
    auto petersen = make_petersen_graph(3);
    AC3Domain ac3d;
    bool consistent = ac3(petersen, ac3d);
    printf("  Consistent: %s\n", consistent ? "yes" : "no");
    if (consistent) {
        printf("  Domain sizes after AC-3:\n");
        for (int i = 0; i < petersen.num_vertices; i++) {
            printf("    Vertex %d: %d colors {", i, __builtin_popcountll(ac3d.domains[i]));
            uint64_t d = ac3d.domains[i];
            bool first = true;
            while (d) {
                int c = __builtin_ffsll(d) - 1;
                d &= d - 1;
                if (!first) printf(", ");
                printf("%d", c);
                first = false;
            }
            printf("}\n");
        }

        // Count solutions with AC-3 pruned domains
        uint64_t colors[MAX_N] = {};
        uint64_t domains[MAX_N];
        memcpy(domains, ac3d.domains, sizeof(domains));
        auto ac3_start = std::chrono::high_resolution_clock::now();
        uint64_t ac3_solutions = graph_coloring_ac3_cpu(petersen, 0, colors, domains);
        auto ac3_end = std::chrono::high_resolution_clock::now();
        double ac3_ms = std::chrono::duration<double, std::milli>(ac3_end - ac3_start).count();

        uint64_t colors2[MAX_N] = {};
        auto naive_start = std::chrono::high_resolution_clock::now();
        uint64_t naive_solutions = graph_coloring_cpu(petersen, 0, colors2);
        auto naive_end = std::chrono::high_resolution_clock::now();
        double naive_ms = std::chrono::duration<double, std::milli>(naive_end - naive_start).count();

        printf("  AC-3 + BT: %lu solutions in %.3f ms\n", ac3_solutions, ac3_ms);
        printf("  Naive BT:  %lu solutions in %.3f ms\n", naive_solutions, naive_ms);
        printf("  AC-3 speedup: %.2fx\n", (ac3_ms > 0) ? naive_ms / ac3_ms : 0.0);
    }

    printf("\n================================================================\n");
    printf("  Done. BitmaskDomain → GPU = CSP at scale.\n");
    printf("================================================================\n");

    return 0;
}
