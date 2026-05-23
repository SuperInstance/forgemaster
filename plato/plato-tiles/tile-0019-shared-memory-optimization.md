# CUDA Shared Memory Optimization

**Core Concept:** Shared memory is a user-managed, on-chip memory shared by all threads in a block. It provides 100x faster access than global DRAM but requires explicit management and careful access patterns to avoid bank conflicts.

**Memory Hierarchy Speed:**

| Memory Type | Speed vs Global | Size per SM | Scope | Management |
|-------------|----------------|-------------|-------|------------|
| Registers | ~200x | 64KB | Per-thread | Compiler |
| Shared | ~100x | 48-228KB | Per-block | User |
| L2 Cache | ~10x | 4-50MB | Per-device | Hardware |
| Global (DRAM) | 1x | 8-48GB | Global | User |

**Shared Memory Characteristics:**

**Capacity (Per SM):**
- RTX 4050 (Ada): 100KB configurable
- Jetson Orin: 228KB
- Can partition between shared/L1 cache

**Latency/Bandwidth:**
- Latency: ~20-30 cycles
- Bandwidth: ~30 TB/s (theoretical)
- 32 banks (32-way interleaving)

**Access Modes:**
- **Read-Only:** `__shared__` or `__constant__` memory
- **Write-Only:** Direct writes
- **ReadWrite:** Both reads and writes

**Bank Conflicts:**

**Bank Architecture:**
- 32 banks, 4 bytes per bank
- Successive 4-byte words map to successive banks
- Bank 0: bytes 0-3, Bank 1: bytes 4-7, ...

**Conflict Scenario:**
```cpp
// BAD: 32 threads access same bank (serialized)
__shared__ float data[32];
value = data[threadIdx.x * 4];  // All threads access bank 0!
```

**Resolution:**
```cpp
// GOOD: Linear access (coalesced)
__shared__ float data[32];
value = data[threadIdx.x];  // Thread i accesses bank i
```

**Optimization Techniques:**

**1. Data Reuse:**
```cpp
// Without shared memory: Each thread loads from global DRAM 1000 times
for (int i = 0; i < 1000; i++)
    value += global_array[i * blockDim.x + threadIdx.x];

// With shared memory: Load once from global, reuse in shared
__shared__ float shared_data[1024];
shared_data[threadIdx.x] = global_array[threadIdx.x];  // 1x global access
__syncthreads();

for (int i = 0; i < 1000; i++)
    value += shared_data[threadIdx.x];  // 1000x shared access
```

**2. Tiling (Blocking):**
```cpp
// Problem: Process large array, too big for shared memory
__global__ void process_large_array(float* global_data, int size) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;

    // BAD: Direct global access (slow)
    float result = compute(global_data[idx]);
}

// Solution: Process in tiles (blocks) that fit in shared memory
__global__ void process_in_tiles(float* global_data, int size) {
    __shared__ float tile[512];  // 512 elements = 2KB

    // Load one tile into shared memory
    int tile_idx = threadIdx.x;
    tile[tile_idx] = global_data[blockIdx.x * 512 + tile_idx];
    __syncthreads();

    // Process tile in shared memory
    float result = compute(tile[tile_idx]);

    // Write back to global
    global_data[blockIdx.x * 512 + tile_idx] = result;
}
```

**3. Padding (Avoid Bank Conflicts):**
```cpp
// BAD: Access pattern causes bank conflicts
__shared__ float data[32][32];
value = data[threadIdx.y][threadIdx.x * 2];  // Threads access stride 2 → conflict

// GOOD: Pad columns to avoid stride-32 pattern
__shared__ float data[32][33];  // Pad by 1
value = data[threadIdx.y][threadIdx.x * 2];  // Now maps to different banks
```

**4. Register Spilling:**
```cpp
// BAD: Too many registers → spill to local (global) memory
__global__ void large_local_array() {
    float huge_local[1000];  // Exceeds register file → spills to global (slow)
}

// GOOD: Use shared memory instead
__global__ void use_shared_memory() {
    __shared__ float shared_huge[1000];
    shared_huge[threadIdx.x] = compute();
}
```

**Applications in Marine GPU Edge:**

**1. NMEA Sentence Parsing:**
```cpp
// Without shared memory: Each character read from global (slow)
char c = global_sentence[idx];

// With shared memory: Load entire sentence, parse in shared
__shared__ char sentence[128];
if (threadIdx.x < sentence_len)
    sentence[threadIdx.x] = global_sentence[base_idx + threadIdx.x];
__syncthreads();

// Parse checksum in shared memory (fast)
unsigned char checksum = 0;
checksum ^= sentence[threadIdx.x];
```

**2. Kalman Filter State Vector:**
```cpp
// State vector: [x, y, z, vx, vy, vz, ax, ay, az, ...]
__shared__ float state[STATE_DIM];

// All threads load state once
if (threadIdx.x < STATE_DIM)
    state[threadIdx.x] = global_state[threadIdx.x];
__syncthreads();

// All threads compute using shared state (no global access)
float innovation = measurement - predict(state);
```

**3. Sonar Waterfall Display:**
```cpp
// Tile sonar ping data into shared memory
__shared__ float ping_tile[32][32];

// Load 32x32 tile
ping_tile[threadIdx.y][threadIdx.x] =
    global_ping_data[ping_id][tile_id * 32 + threadIdx.y * width + threadIdx.x];
__syncthreads();

// Apply TVG (Time-Varying Gain) in shared memory
float tvo = compute_tvo(threadIdx.y);
ping_tile[threadIdx.y][threadIdx.x] *= tvo;

// Convert to dB in shared memory
ping_tile[threadIdx.y][threadIdx.x] = 20 * log10f(ping_tile[threadIdx.y][threadIdx.x] + 1e-6f);
```

**Performance Analysis:**

**Without Shared Memory:**
- NMEA parse: ~10 ms for 1000 sentences
- Each character: Global DRAM access (~500 cycles)

**With Shared Memory:**
- NMEA parse: ~1 ms for 1000 sentences
- Load once (500 cycles), then reuse (20 cycles) = 10x speedup

**Bank Conflict Penalty:**
- No conflict: 32 threads access 32 banks = 1 memory transaction
- Full conflict: 32 threads access 1 bank = 32 serialized transactions = 32x slowdown

**Best Practices:**

**DO:**
- Reuse data loaded into shared memory multiple times
- Pad arrays to avoid stride-32 access patterns
- Use `__syncthreads()` after writing, before reading
- Use `__restrict__` and `const` to help compiler optimize

**DON'T:**
- Load data once, read once (no benefit)
- Forget `__syncthreads()` (race conditions!)
- Use shared memory for data larger than block size
- Assume automatic coalescing (check with nvprof)

**Profiling:**
```bash
nvprof --metrics shared_load_transactions_per_request ./kernel

# Ideal: 1.0 (coalesced)
# Bad: >1.0 (bank conflicts)
```

**Constraint Theory Connection:**
Shared memory optimization is constraint satisfaction:
- Variables: Data placement (global vs shared)
- Domains: Discrete choices (load strategy)
- Constraints: Bank conflict rules, capacity limits
- Objective: Minimize global memory access

**Provenance:** Forgemaster (CUDA optimization)
**Chain:** Marine GPU Edge shared memory usage
