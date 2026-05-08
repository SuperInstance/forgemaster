# Repo-Agents on Metal: GPU-Accelerated Repository Automation

**Research Document** — Forgemaster ⚒️ / Cocapn Fleet  
**Date:** 2026-05-08  
**Context:** Deep research for fleet integration — what repo-agents look like when built "close to metal"

---

## Table of Contents

1. [What Are Repo-Agents?](#1-what-are-repo-agents)
2. [The Metal Thesis](#2-the-metal-thesis)
3. [GPU-Accelerated Agent Architectures](#3-gpu-accelerated-agent-architectures)
   - [3.1 GPU-Accelerated Regex / Pattern-Matching Agent (GREP-Agent)](#31-gpu-accelerated-regex--pattern-matching-agent-grep-agent)
   - [3.2 GPU-Parallel Code Clone Detection Agent (CloneHound)](#32-gpu-parallel-code-clone-detection-agent-clonehound)
   - [3.3 GPU Dependency Graph Analyzer (DepGraph-GPU)](#33-gpu-dependency-graph-analyzer-depgraph-gpu)
   - [3.4 GPU Code Integrity / Supply-Chain Auditor (IntegrityForge)](#34-gpu-code-integrity--supply-chain-auditor-integrityforge)
   - [3.5 GPU-Accelerated AST Similarity Search (TreeScan-GPU)](#35-gpu-accelerated-ast-similarity-search-treescan-gpu)
   - [3.6 GPU-Parallel Test Mutation Agent (Mutagen-GPU)](#36-gpu-parallel-test-mutation-agent-mutagen-gpu)
   - [3.7 GPU Code Embedding & Semantic Search Agent (EmbedForge)](#37-gpu-code-embedding--semantic-search-agent-embedforge)
   - [3.8 GPU Lint / Style Enforcement Agent (ParallelLint)](#38-gpu-lint--style-enforcement-agent-parallellint)
   - [3.9 GPU Build Cache & Incremental Compilation Agent (CacheHammer)](#39-gpu-build-cache--incremental-compilation-agent-cachehammer)
4. [Existing Work & Prior Art](#4-existing-work--prior-art)
5. [Architecture: How GPU Accelerates Each Phase](#5-architecture-how-gpu-accelerates-each-phase)
6. [Nuts & Bolts: Metal Compute Shader Patterns for Code Analysis](#6-nuts--bolts-metal-compute-shader-patterns-for-code-analysis)
7. [Performance Estimates vs CPU-Only](#7-performance-estimates-vs-cpu-only)
8. [Fleet Integration](#8-fleet-integration)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Risks & Mitigations](#10-risks--mitigations)

---

## 1. What Are Repo-Agents?

Repo-agents are autonomous software agents that operate on code repositories. They are the next evolution of CI/CD: not just *running* checks, but *owning* them — triaging issues, reviewing PRs, generating code, patching dependencies, auditing security, and maintaining documentation.

### Canonical Types

| Agent Type | What It Does | Pain Point (CPU) |
|---|---|---|
| **PR Review Agent** | Analyzes diffs, flags bugs/style/security, suggests fixes | Large diffs = minutes of AST parsing |
| **Issue Triage Agent** | Labels, deduplicates, routes issues; generates reproduction steps | Cross-referencing 1000+ issues |
| **Code Generation Agent** | Implements features from specs, writes tests | Context window limits, slow iteration |
| **Dependency Update Agent** | Scans for outdated deps, evaluates breaking changes, creates PRs | Dep graph resolution on 500+ deps |
| **Security Audit Agent** | Scans for vulns, supply-chain integrity, secret leakage | Regex over millions of LOC |
| **CI/CD Optimization Agent** | Identifies slow build targets, parallelizes pipelines | Build graph analysis |
| **Documentation Agent** | Generates/updates docs from code changes | Cross-file reference tracing |
| **Refactoring Agent** | Renames, restructures, extracts across codebase | Codebase-wide rename tracking |
| **Test Generation Agent** | Writes unit/integration tests for uncovered code | Coverage gap analysis |
| **Code Clone Detector** | Finds duplicate/similar code across repo | O(n²) pairwise comparison |

**The bottleneck for all of these at scale is the same:** they need to process large codebases (100K–10M+ LOC), and pure CPU sequential processing doesn't cut it at fleet scale. Enter GPU acceleration.

---

## 2. The Metal Thesis

> **"Metal" here is a dual-axis concept.**

### Axis 1: Apple Metal Shading Language (MSL)
Apple's GPU programming framework. Compute shaders in MSL can execute thousands of threads in parallel on Apple Silicon GPUs (M-series). Applications for code analysis:
- Parallel regex/pattern matching across millions of lines
- Massively parallel hash computation for integrity verification
- SIMD-group operations for tokenization, lexing phases
- Texture-backed data structures for AST representation
- Metal Performance Shaders (MPS) for matrix ops on code embeddings

**Key constraint:** MSL runs on Apple GPUs only. But with M-series Macs becoming the standard developer machine, this is increasingly relevant.

### Axis 2: "Close to Metal" Systems Languages (Rust, Zig, C)
Languages that give you GPU access without the overhead of Python/CUDA toolchains:
- **Rust** via `wgpu` (WebGPU abstraction over Vulkan/Metal/DX12), `rust-gpu` (compile Rust → SPIR-V), or `cubecl` (GPU compute framework)
- **Zig** via native SPIR-V backend, direct PTX generation, and Vulkan compute shader support
- **C** via OpenCL, CUDA

**The thesis:** By building repo-agents in systems languages with GPU compute backends, we get:
1. **Massive parallelism** — 1000s of threads analyzing code simultaneously
2. **Zero-copy processing** — Memory-mapped repos, GPU reads directly from page cache
3. **ML inference co-location** — Run CodeBERT/GraphCodeBERT inference on the same GPU
4. **Deterministic performance** — No GC pauses, no Python GIL

### Why This Matters for Cocapn Fleet
We have 1,400+ repos. CPU-bound code analysis across that surface is a scheduling nightmare. GPU-accelerated agents turn hours-long batch jobs into seconds.

---

## 3. GPU-Accelerated Agent Architectures

### 3.1 GPU-Accelerated Regex / Pattern-Matching Agent (GREP-Agent)

**What it does:** Massive parallel regex matching across entire codebases for code quality, security scanning (secret detection, vulnerability patterns), and style enforcement.

**Why GPU helps:** Regex matching is embarrassingly parallel at the file/line level. GPUs excel at data-parallel workloads. The HybridSA paper shows 4–60× throughput vs CPU engines.

**Data flow:**
```
repo/ → file list → GPU buffer of file contents (pinned memory)
                         ↓
            Metal compute kernel (parallel NFA simulation)
            - Each thread group handles N files
            - Bit-parallel NFA simulation per thread
            - Shared memory for pattern state tables
                         ↓
            Result buffer: [{file, line, match, pattern_id}, ...]
                         ↓
            CPU: aggregate results, format reports, create PR comments
```

**Feasibility:** HIGH. GPU regex is proven (HybridSA, CUDA-grep, GPURegex). Metal compute shaders can implement the same bit-parallel NFA approach.

**Key techniques:**
- Bit-parallel NFA simulation (bit parallelism = NFA states packed into registers/shared memory)
- Pattern compilation: regex patterns → compiled NFA state tables → GPU constant memory
- Batch dispatch: files grouped by size to maximize GPU occupancy
- Metal threadgroup memory for per-group pattern state

**Performance estimate:**
- 100K LOC repo: ~50ms (vs ~3–5s CPU grep -r with complex patterns)
- 1M LOC monorepo: ~200–500ms (vs ~30–60s CPU)
- Scale advantage grows with more patterns: adding 100 patterns costs ~0% GPU overhead, ~100% CPU overhead

---

### 3.2 GPU-Parallel Code Clone Detection Agent (CloneHound)

**What it does:** Finds Type-1 through Type-4 code clones across a repository or fleet. Essential for refactoring technical debt.

**Why GPU helps:** Pairwise code comparison is O(n²) or O(n log n) at best. GPU parallelism enables massive pairwise embedding comparison in one kernel launch.

**Data flow:**
```
repo/ → parser (tree-sitter) → AST nodes
                                          ↓
                    Code embeddings (via GPU-accelerated model inference)
                    - GraphCodeBERT or custom lightweight embedding
                    - Batch of n functions → GPU infer → n × d embedding matrix
                                          ↓
                    GPU similarity kernel
                    - Cosine similarity matrix: n × n in parallel
                    - Thread (i, j) computes sim(embed_i, embed_j)
                    - SIMD-sum reduction for dot product
                    - Threshold filter → clone pairs
                                          ↓
                    CPU: deduplicate, generate refactoring suggestions
```

**Feasibility:** MEDIUM-HIGH. Embedding computation on GPU is well-understood (BERT inference on GPU). The pairwise similarity matrix is textbook GPU workload. The challenge is Tree-sitter parsing (traditionally CPU-bound), though parallelizing AST generation per file is feasible.

**Performance estimate:**
- 10K functions, 768-dim embeddings: ~5ms GPU similarity (vs ~10s CPU pairwise)
- 100K functions: ~100ms GPU (vs ~15min CPU — not feasible as PR review blocker)
- Embedding generation: ~2s for 10K functions via GPU vs ~30s CPU

**Key Metal patterns:**
- MPSMatrixMultiplication for similarity matrix (use Metal Performance Shaders)
- Threadgroup tile-based matrix multiply for better cache utilization
- Atomic threshold counters for clone pair collection

---

### 3.3 GPU Dependency Graph Analyzer (DepGraph-GPU)

**What it does:** Analyzes dependency graphs for circular dependencies, transitive dependency bloat, version conflict detection, and build order optimization.

**Why GPU helps:** Kahn's algorithm for topological sort can be GPU-parallelized (nodes with in-degree 0 processed concurrently). Graph exploration (BFS/DFS) maps well to GPU thread blocks.

**Data flow:**
```
repo/ → dep manifest parser → dependency DAG
                                          ↓
            GPU: parallel topological sort (Kahn's)
            - CSR adjacency matrix in GPU global memory
            - Per-node in-degree array (atomically decremented)
            - WorkQueue of ready nodes (processed in parallel)
            - Parallel cycle detection via back-edge tracking
                                          ↓
            GPU: transitive closure computation
            - Floyd-Warshall or iterative matrix multiplication
            - Identifies all transitive dependencies
                                          ↓
            CPU: build optimization suggestions, dep tree reports
```

**Feasibility:** HIGH. GPU graph processing is well-studied. For dependency graphs (typically shallow, high-fanout), parallelism is abundant.

**Performance estimate:**
- 500-node dependency DAG: ~1ms GPU (vs ~50ms CPU Kahn)
- 10K-node DAG (large monorepo): ~10ms GPU (vs ~500ms CPU)
- Transitive closure for 10K nodes: ~50ms GPU vs ~5s CPU

**Key Metal patterns:**
- CSR/CSC graph representation in device memory
- `simd_sum()` for warp-level in-degree reduction
- Work queues using atomic add + threadgroup barriers
- Multiple kernel launches per Kahn iteration (barrier-free approach)

---

### 3.4 GPU Code Integrity / Supply-Chain Auditor (IntegrityForge)

**What it does:** Verifies code integrity via SHA-256 Merkle trees across all files in a repo. Detects tampering, ensures reproducible builds, validates vendored dependencies.

**Why GPU helps:** SHA-256 hashing is GPU-friendly — each file hash is independent, and Merkle tree construction is a parallel reduction. NVIDIA's cuPQC SDK shows 10–50× GPU vs CPU SHA-256 throughput.

**Data flow:**
```
repo/ → file list → GPU buffer with file contents
                                          ↓
            Kernel 1: Parallel SHA-256 (one thread per file)
            - File ≤ block_size: one thread handles it
            - File > block_size: thread group cooperates
            - Output: per-file hash → GPU buffer
                                          ↓
            Kernel 2: Parallel Merkle tree construction
            - Thread pair (2i, 2i+1) → hash(concat(hash_{2i}, hash_{2i+1}))
            - Iterative reduction to Merkle root
            - Log₂(n) kernel launches for n leaves
                                          ↓
            Merkle root → compare against expected / signed root
            CPU: generate integrity attestation report
```

**Feasibility:** VERY HIGH. SHA-256 on GPU is production-proven (cryptocurrency mining). Merkle trees are textbook parallel reduction.

**Performance estimate:**
- 10K files, avg 10KB: ~50ms GPU SHA-256 (vs ~2s CPU sequential)
- 100K files: ~200ms GPU (vs ~20s CPU)
- Merkle tree for 100K leaves: ~5ms GPU (barrier synchronization overhead)

**Key Metal patterns:**
- SHA-256 message schedule in threadgroup shared memory
- 64-round compression function unrolled
- Threadgroup barriers between compression rounds
- Atomic-free Merkle construction: each level launches `n/2` threads

---

### 3.5 GPU-Accelerated AST Similarity Search (TreeScan-GPU)

**What it does:** Searches for AST subtrees matching a query pattern — useful for finding similar code patterns, detecting anti-patterns, or locating all usages of a specific API pattern.

**Why GPU helps:** Tree pattern matching is expensive on CPU (subtree isomorphism is NP-hard in general). GPU can parallelize by comparing many candidate subtrees against the query pattern simultaneously.

**Data flow:**
```
repo/ → parser → AST serialization → GPU buffer
                                          ↓
            GPU: AST → linearized representation
            - Preorder traversal encoded as compact tuples
            - Each tuple: {node_type, parent_offset, depth, sibling_rank}
            - Works like a flattened AST for GPU consumption
                                          ↓
            GPU: parallel subtree matching
            - Each thread block handles one candidate root
            - Threads within block traverse child subtrees
            - Compare node types, structure against query pattern
            - SIMD comparisons for type matching
                                          ↓
            GPU: top-k results via parallel reduction
            - Atomic counters for match quality scoring
                                          ↓
            CPU: collect matched AST nodes → source location mapping
```

**Feasibility:** MEDIUM. Requires careful AST serialization format for GPU consumption. The matching kernel itself is GPU-friendly for medium-sized queries (up to ~100 nodes in pattern). Large pattern matching requires multiple kernel launches.

**Performance estimate:**
- 10K AST nodes, query of 20 nodes: ~2ms GPU (vs ~100ms CPU subtree search)
- 100K AST nodes: ~15ms GPU (vs ~2s CPU)
- Scales with GPU cores more than query complexity

**Key Metal patterns:**
- Tree structure flattened into parallel arrays (type array, parent array, depth array)
- Memory coalescing: adjacent threads access adjacent array elements
- Threadgroup shared memory for query pattern cache
- Early termination: thread stops when mismatch detected

---

### 3.6 GPU-Parallel Test Mutation Agent (Mutagen-GPU)

**What it does:** Generates code mutations (mutant testing) to evaluate test suite quality. Runs mutants against test suites to find weak tests.

**Why GPU helps:** Each mutation is independent — the perfect parallel workload. GPU can generate and compile-check thousands of mutants in parallel. (Actual test execution still happens on CPU/VM, but mutation generation is GPU.)

**Data flow:**
```
repo/ → source files → GPU buffer
                                          ↓
            GPU: parallel mutation generation
            - Each thread generates one mutant
            - Apply random mutation operator to random location
            - Operators: swap operators, negate conditions,
              delete statements, change constants, swap args
            - Output: {mutant_id, original_file, mutation_site, diff}
                                          ↓
            CPU: write mutants to temp files, run test suite
            (test execution is I/O bound, GPU handles generation)
                                          ↓
            GPU: mutation coverage analysis
            - Which mutants were killed/alive?
            - Parallel aggregation of mutation scores
                                          ↓
            Report: mutation score, weak spots in test suite
```

**Feasibility:** HIGH for generation, LOW for execution. GPU handles the embarrassingly parallel generation phase. Test execution remains CPU/VM-bound.

**Performance estimate:**
- Generate 10K mutants: ~10ms GPU (vs ~500ms CPU sequential generation)
- Mutation coverage from 10K results: ~2ms GPU aggregation
- Total pipeline: mutation generation is no longer bottleneck

**Key Metal patterns:**
- Random number generation in parallel (Philox or counter-based PRNG in shader)
- Mutation operators as switch/case in thread code
- Atomic-free: each thread writes to unique output slot
- Deterministic seeding for reproducible mutation suites

---

### 3.7 GPU Code Embedding & Semantic Search Agent (EmbedForge)

**What it does:** Generates code embeddings (vector representations) for all functions/files in a repo. Enables semantic code search: "find all functions that validate user input" → vector similarity → results.

**Why GPU helps:** Embedding inference is dominated by matrix multiplies (Transformer architecture). GPUs exist for this. Metal Performance Shaders (MPS) and Apple's ANE (Neural Engine) are optimized for this exact workload.

**Data flow:**
```
repo/ → tokenizer → GPU buffer of token IDs
                                          ↓
            GPU: Transformer inference
            - MPS matrix multiplies for attention layers
            - LayerNorm, GeLU on GPU
            - Embedding pooling (CLS token or mean pooling)
            - Output: n × d embedding matrix
                                          ↓
            GPU: FAISS-like similarity search
            - Cosine similarity via MPSMatrixMultiplication
            - Top-k reduction per query
            - Can use IVF Flat clustering on GPU
                                          ↓
            CPU: map results back to source locations, format output
```

**Feasibility:** HIGH (if using existing model). Custom model training needed for optimal results, but off-the-shelf CodeBERT fine-tuning works. GPU inference is standard.

**Performance estimate:**
- Embed 10K functions (CodeBERT-base, 110M params): ~1–2s GPU vs ~15–30s CPU
- Semantic search across 10K embeddings: ~2ms GPU vs ~50ms CPU FAISS
- Batch embedding: GPU throughput linear in batch size up to VRAM limit

**Key Metal patterns:**
- MPSGraph for Transformer computation graph
- MPSMatrixMultiplication for attention scores
- MPSImage/MTLBuffer interop for neural engine offload
- `MTLResourceStorageModeShared` for zero-copy embedding access

---

### 3.8 GPU Lint / Style Enforcement Agent (ParallelLint)

**What it does:** Runs lint rules across entire codebase in parallel. Flags style violations, unsafe patterns, dead code, and anti-patterns.

**Why GPU helps:** Each file's lint analysis is independent. Even within a file, line-by-line rules are data-parallel. GPU enables batch lint of 1000+ files in one dispatch.

**Data flow:**
```
repo/ → file list → GPU buffer of file contents
                                          ↓
            GPU: parallel lexing/tokenization per file
            - Each thread handles N lines of one file
            - Or: each thread group handles one file
            - Shared memory for lexer state
            - Output: token stream per file
                                          ↓
            GPU: parallel rule application
            - Rule state tables in constant memory
            - Each rule is a GPU kernel or kernel variant
            - Rules with local scope (line/expression) → thread level
            - Rules with file scope (import ordering) → threadgroup level
            - Rules with project scope → multiple kernel launches
                                          ↓
            Result buffer: [{file, line, rule_id, severity}, ...]
            CPU: sort, deduplicate, annotate source map
```

**Feasibility:** MEDIUM-HIGH for line-level rules. File/project-level rules are harder (need cross-file state). Best approach: hybrid GPU/CPU — GPU handles local rules, CPU handles global rules.

**Performance estimate:**
- 1000 files, 50 local lint rules: ~20ms GPU (vs ~5s CPU sequential ESLint/Rustfmt)
- 10K files: ~100ms GPU (vs ~60s CPU)
- Global rules (import cycles, cross-file type errors): CPU-only, ~2–10s

**Key Metal patterns:**
- Tiny lexer state machines in shared memory per threadgroup
- Rule dispatch table in constant memory
- SIMD-group scan for line number tracking
- Hybrid: GPU processes, CPU aggregates (no branching divergence penalty)

---

### 3.9 GPU Build Cache & Incremental Compilation Agent (CacheHammer)

**What it does:** Analyzes build graphs to determine optimal parallel compilation order, cache invalidation, and incremental rebuild boundaries.

**Why GPU helps:** Build dependency resolution is a DAG problem similar to DepGraph-GPU. Additionally, file hash comparison for cache invalidation is GPU-parallel.

**Data flow:**
```
build graph → GPU parallel topological sort
                                              ↓
            GPU: file content hash comparison
            - SHA-256 of modified files → compare with cache
            - Parallel: one thread per file
            - Only changed files trigger rebuild
                                              ↓
            GPU: transitive dependency impact analysis
            - Which targets are affected by each changed file?
            - Parallel BFS from changed nodes
                                              ↓
            CPU: combine results → optimal build plan
            - Parallel job scheduling for make/ninja/cargo
            - Report: estimated build time, affected targets
```

**Feasibility:** HIGH for hash/invalidation. MEDIUM for build plan optimization (requires tight integration with build system).

**Performance estimate:**
- Cache check for 10K files: ~30ms GPU hash (vs ~1s CPU)
- Affected target graph for 1000 targets: ~5ms GPU BFS (vs ~100ms CPU)
- Full build plan generation: ~50ms total (vs ~5s CPU `cargo check --timings`)

---

## 4. Existing Work & Prior Art

### GPU-Accelerated Pattern Matching
| Project | Technology | Application | Speedup |
|---|---|---|---|
| **HybridSA** (Splash '24) | CUDA | Multi-pattern regex | 4–60× vs CPU |
| **CUDA-grep** (CMU) | CUDA | Regex matching | 2–10× vs grep |
| **GPURegex** (EU MARVEL) | OpenCL | High-throughput regex | 10–100× |
| **NVIDIA DOCA RegEx** | BlueField DPU | Hardware regex | 100+ Gbps |
| **HyperScan** (Intel) | CPU SIMD | Regex | Baseline |

### GPU Code Understanding
| Project | Technology | Application | Notes |
|---|---|---|---|
| **CodeBERT** (Microsoft) | GPU Transformer | Code understanding | Standard baseline |
| **GraphCodeBERT** (Microsoft) | GPU Transformer | Code + data flow | SOTA for clone detection |
| **AST-T5** | GPU Transformer | AST-aware code gen | Multi-lingual |
| **MGCD** (2024) | GPU + IVF | Clone detection | 0.23ms for 800K funcs |

### GPU Graph Processing
| Project | Technology | Application |
|---|---|---|
| **Gunrock** (UCDavis) | CUDA | General graph analytics |
| **cuPQC** (NVIDIA) | CUDA | Merkle trees, SHA-256 |
| **GraphBLAST** | CUDA | Linear algebra on graphs |
| **Ligra+** | CPU parallel | Graph processing (GPU comparison baseline) |

### GPU Build Systems
| Project | Technology | Application |
|---|---|---|
| **Icecc** | CPU distributed | Distributed compilation |
| **sccache** | CPU | Compilation cache |
| **Bazel remote** | Any | Distributed build |
| **N/A** | GPU | **No production GPU build cache system exists** — open opportunity |

### Key Gap
**No existing project combines Apple Metal compute shaders with code repository analysis.** The combination of Metal's tight hardware integration (unified memory on Apple Silicon) with code analysis workloads is unexplored territory. This is a genuine first-mover opportunity for the Cocapn fleet.

---

## 5. Architecture: How GPU Accelerates Each Phase

```
┌─────────────────────────────────────────────────────────────────┐
│                    REPO-AGENT PIPELINE                          │
│                                                                 │
│  Phase 1: INGEST                                                │
│  ┌─────────────┐                                                │
│  │ git clone   │──── CPU (network I/O)                          │
│  │ or pull     │                                                │
│  └──────┬──────┘                                                │
│         │                                                       │
│  Phase 2: INDEX                                                 │
│  ┌──────▼──────┐                                                │
│  │ File scan   │──── CPU (filesystem walk)                      │
│  │ & tokenize  │                                                │
│  └──────┬──────┘                                                │
│         │                                                       │
│  Phase 3: GPU DISPATCH (the bottleneck)                         │
│  ┌──────▼─────────────────────────────────────────────┐        │
│  │  GPU Buffer (MTLBuffer, unified memory)            │        │
│  │  ┌───────────────────────────────────────────────┐ │        │
│  │  │ File 1 │ File 2 │ ... │ File N │              │ │        │
│  │  └───────────────────────────────────────────────┘ │        │
│  │                                                     │        │
│  │  ┌───────────────────┐  ┌──────────────────────┐   │        │
│  │  │ Compute Kernel(s) │  │ Result Buffer(s)     │   │        │
│  │  │ - Thread per file │  │ - Matches            │   │        │
│  │  │ - Thread per line │  │ - Hash values        │   │        │
│  │  │ - SIMD group ops  │  │ - Clone pairs        │   │        │
│  │  └───────────────────┘  └──────────────────────┘   │        │
│  └─────────────────────────────────────────────────────┘        │
│         │                                                       │
│  Phase 4: CPU AGGREGATE                                         │
│  ┌──────▼──────┐                                                │
│  │ Sort, dedup,│──── CPU (reduce, sort, format)                 │
│  │ format      │                                                │
│  └──────┬──────┘                                                │
│         │                                                       │
│  Phase 5: ACT                                                  │
│  ┌──────▼──────┐                                                │
│  │ PR comment  │──── CPU (GitHub/GitLab API)                    │
│  │ Issue file  │                                                │
│  │ Report gen  │                                                │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Matters on Apple Silicon (M1/M2/M3/M4)

Apple Silicon's **unified memory architecture** is transformative for this approach:
- CPU and GPU share the same physical memory (no PCIe transfer)
- `MTLResourceStorageModeShared` = zero-copy data sharing
- Repository contents can be mmap'd and read directly by GPU
- No expensive host↔device data copies
- On M3 Max/M4 Ultra: 128GB+ unified memory → entire monorepo in GPU-accessible RAM

**Compare:**
- Traditional GPU (NVIDIA): copy repo to GPU VRAM → process → copy results back → 1–5ms overhead per transfer
- Apple Silicon: repo already in unified memory → GPU reads directly → 0ms transfer overhead

This makes Metal the *ideal* compute platform for repo-agents on developer machines.

---

## 6. Nuts & Bolts: Metal Compute Shader Patterns for Code Analysis

### Pattern 1: Parallel Text Processing

```metal
// Kernel: parallel tokenizer / pattern matcher
kernel void scan_lines(
    device const char *file_data [[buffer(0)]],
    device uint *line_offsets [[buffer(1)]],
    device MatchResult *results [[buffer(2)]],
    constant ScanParams &params [[buffer(3)]],
    uint tid [[thread_position_in_grid]])
{
    uint start = line_offsets[tid];
    uint end = line_offsets[tid + 1];
    
    // Each thread processes one line
    // SIMD-friendly: branching patterns diverge per line
    // but within SIMD group, adjacent lines may have similar structure
    
    for (uint i = start; i < end; i++) {
        // Bit-parallel NFA simulation
        // Pattern state in threadgroup shared memory
        if (match_pattern(file_data[i])) {
            results[atomic_fetch_add_explicit(&result_count, 1, memory_order_relaxed)]
                = {tid, i, matched_pattern_id};
        }
    }
}
```

### Pattern 2: Parallel Hash Computation

```metal
kernel void sha256_batch(
    device const char *file_data [[buffer(0)]],
    device const uint *file_sizes [[buffer(1)]],
    device uint8_t *file_hashes [[buffer(2)]],
    uint tid [[thread_position_in_grid]])
{
    // Each thread processes one file's SHA-256
    // For files > 64 bytes: threadgroup splits the work
    threadgroup uint8_t shared_state[64];
    
    uint size = file_sizes[tid];
    sha256_init(shared_state, tid);
    
    for (uint offset = 0; offset < size; offset += 64) {
        // Threadgroup barrier for cooperative hashing
        threadgroup_barrier(mem_flags::mem_threadgroup);
        sha256_compress(shared_state, file_data + offset);
    }
    
    sha256_final(shared_state, file_hashes + tid * 32);
}
```

### Pattern 3: Parallel Similarity Matrix

```metal
kernel void similarity_matrix(
    device const float *embeddings [[buffer(0)]],
    device float *results [[buffer(1)]],
    constant uint &dim [[buffer(2)]],
    uint2 pos [[thread_position_in_grid]])
{
    // Thread (i, j) computes similarity between embedding i and j
    uint i = pos.x;
    uint j = pos.y;
    
    float dot = 0;
    for (uint d = 0; d < dim; d++) {
        dot += embeddings[i * dim + d] * embeddings[j * dim + d];
    }
    // Normalize by magnitudes (precomputed)
    results[i * N + j] = dot;
}
```

### Pattern 4: Parallel Graph Topological Sort

```metal
kernel void topsort_step(
    device const uint *csr_edges [[buffer(0)]],   // CSR adjacency
    device const uint *csr_offsets [[buffer(1)]],
    device uint *in_degrees [[buffer(2)]],
    device uint *ready_queue [[buffer(3)]],
    device uint *ready_count [[buffer(4)]],
    device uint *next_queue [[buffer(5)]],
    device uint *next_count [[buffer(6)]],
    device uint *result [[buffer(7)]],
    uint tid [[thread_position_in_grid]])
{
    if (tid < *ready_count) {
        uint node = ready_queue[tid];
        result[*result_count + tid] = node;
        
        // Process outgoing edges
        uint start = csr_offsets[node];
        uint end = csr_offsets[node + 1];
        for (uint e = start; e < end; e++) {
            uint neighbor = csr_edges[e];
            uint new_degree = atomic_fetch_sub_explicit(
                &in_degrees[neighbor], 1, memory_order_relaxed) - 1;
            if (new_degree == 0) {
                uint q_idx = atomic_fetch_add_explicit(
                    next_count, 1, memory_order_relaxed);
                next_queue[q_idx] = neighbor;
            }
        }
    }
}
```

---

## 7. Performance Estimates vs CPU-Only

| Agent | Task | 1M LOC GPU | 1M LOC CPU | Speedup |
|---|---|---|---|---|
| **GREP-Agent** | 100 regex patterns | 0.2s | 30s | **150×** |
| **CloneHound** | Pairwise 100K funcs | 0.1s | 15min | **9000×** |
| **DepGraph-GPU** | Topo sort 10K nodes | 10ms | 500ms | **50×** |
| **IntegrityForge** | SHA-256 50K files | 0.1s | 10s | **100×** |
| **TreeScan-GPU** | Subtree match 100K nodes | 15ms | 2s | **133×** |
| **Mutagen-GPU** | Generate 10K mutants | 10ms | 500ms | **50×** |
| **EmbedForge** | Embed 10K functions | 1s | 20s | **20×** |
| **ParallelLint** | 50 rules, 10K files | 0.1s | 60s | **600×** |
| **CacheHammer** | Hash 10K files | 30ms | 1s | **33×** |

**Key insight:** Speedups are largest for workloads that are naturally data-parallel (regex, hashing, similarity). ML-based agents (embedding, clone detection) get smaller but still significant speedups from GPU matrix acceleration.

**Critical note:** The 0-copy unified memory on Apple Silicon eliminates PCIe transfer overhead. On NVIDIA GPUs, subtract 1–5ms per batch for transfer, which only matters for very small workloads.

---

## 8. Fleet Integration

### How Repo-Agents Fit Into Cocapn Fleet

```
┌──────────────────────────────────────────────┐
│             OpenClaw Gateway                  │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Telegram   │  │ Matrix   │  │ Web      │ │
│  │ Channel    │  │ Channel  │  │ Channel  │ │
│  └────────────┘  └──────────┘  └──────────┘ │
└──────────────────────┬───────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │         I2I Protocol         │
        │  (Inter-Agent Intelligence)  │
        └──────────────┬──────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼────┐       ┌────▼─────┐      ┌─────▼────┐
│Oracle1 │       │Forgemaster│      │ Other    │
│🔮      │       │⚒️         │      │ Agents   │
│Coord   │◄─────►│Orchestrator│◄────►│          │
└────────┘       └────┬─────┘      └──────────┘
                       │
              ┌────────┼────────┐
              │        │        │
        ┌─────▼──┐ ┌───▼──┐ ┌──▼─────┐
        │OpenCode│ │Droid │ │  Kimi  │
        │z.ai    │ │z.ai  │ │  kimi  │
        └────────┘ └──────┘ └────────┘
                       │
              ┌────────▼────────┐
              │  REPO-AGENT     │
              │  FLEET          │
              │  (This doc)     │
              └─────────────────┘
```

### Integration Points

| Fleet Component | Integration |
|---|---|
| **OpenClaw Gateway** | Repo-agents register as OpenClaw agents with channel bindings (e.g., `repo-agent/grep` receives PR review requests) |
| **I2I Protocol** | Repo-agents communicate findings via I2I messages: `[I2I:REPO-AGENT] clonehound — found 47 Type-3 clones in src/` |
| **PLATO Knowledge Base** | Repo-agent results persist to PLATO rooms. Each agent type has a room: `plato/repo-agents/clones/`, `plato/repo-agents/grep/`, etc. |
| **Matrix Fleet Channel** | Critical findings broadcast to fleet channel: `#fleet:cocapn.dev` |
| **Vessel (Git)** | Each repo-agent has its own vessel repo for code; config stored in fleet `for-fleet/` bottles |
| **Sub-agent Spawning** | OpenClaw coordinator spawns repo-agents as sub-agents for specific repo analysis tasks |
| **Planned Scheduling** | Repo-agents support cron-style periodic scans (nightly supply-chain audit, weekly clone detection) |

### Agent Lifecycle

1. **TRIGGER** — Event (PR opened, issue filed, cron tick, manual request via Telegram/Matrix)
2. **ROUTE** — OpenClaw gateway routes to coordinating agent (Forgemaster or Oracle1)
3. **DELEGATE** — Coordinator spawns repo-agent sub-agent with task specification
4. **ANALYZE** — Repo-agent executes GPU-accelerated pipeline (ingest → dispatch → aggregate)
5. **FIND** — Results collected, deduplicated, prioritized
6. **REPORT** — Output via I2I: PR comment, issue creation, fleet notification, PLATO write
7. **CLEANUP** — Temp files deleted, GPU buffers released, agent terminates

### Fleet Knowledge Bottles

Each repo-agent type produces knowledge bottles for the fleet:
- `for-fleet/repo-agents/clone-catalog-YYYY-MM-DD.md` — CloneHound weekly report
- `for-fleet/repo-agents/audit-results-YYYY-MM-DD.md` — IntegrityForge audit results
- `for-fleet/repo-agents/embed-index-YYYY-MM-DD.md` — EmbedForge index metadata

Bottles are git-committed to the appropriate vessel and shared via I2I push.

---

## 9. Implementation Roadmap

### Phase 0: Foundation (Weeks 1–3)

| Task | Effort | Owner | Dependencies |
|---|---|---|---|
| Set up Rust + `wgpu` or C + Metal project skeleton | 2 days | Forgemaster | — |
| Implement GPU buffer pool (file → MTLBuffer) | 1 day | — | — |
| Build file walker + shard allocator | 1 day | — | Buffer pool |
| Write Metal kernel harness (dispatch + result readback) | 2 days | — | Buffer pool |
| Benchmark: file I/O → GPU dispatch → result latency | 1 day | — | Kernel harness |
| Set up CI for Metal target (macOS runner) | 1 day | — | — |

**Deliverable:** Working GPU compute harness that can ingest files and run custom Metal kernels, with benchmark suite.

### Phase 1: Quick Wins (Weeks 4–6)

**Build GREP-Agent** (highest speedup, first to ship)
| Task | Effort |
|---|---|
| Port bit-parallel NFA regex engine to Metal | 5 days |
| Build pattern compiler (regex → GPU state tables) | 2 days |
| Wrap as OpenClaw agent + CLI | 2 days |
| Integrate with GitHub PR review flow (via gh CLI) | 2 days |
| Benchmark against grep/rg across fleet repos | 1 day |

**Build IntegrityForge** (production ready, security-critical)
| Task | Effort |
|---|---|
| Port SHA-256 to Metal compute | 3 days |
| Build parallel Merkle tree kernel | 2 days |
| File change tracker + scheduled audits | 2 days |
| Supply-chain verification (vendored deps) | 3 days |
| Wrap as OpenClaw agent | 1 day |

### Phase 2: Core Agents (Weeks 7–10)

| Agent | Effort | Dependencies |
|---|---|---|
| DepGraph-GPU | 5 days | Phase 0, topo sort kernel lib |
| ParallelLint (line-level rules) | 7 days | Phase 0, lexer kernel |
| CacheHammer | 5 days | IntegrityForge SHA kernel |
| Mutagen-GPU (generation only) | 4 days | Phase 0, PRNG kernel |

### Phase 3: Advanced (Weeks 11–16)

| Agent | Effort | Dependencies |
|---|---|---|
| CloneHound (embedding + similarity) | 10 days | EmbedForge or off-the-shelf CodeBERT |
| EmbedForge (MPS Transformer inference) | 10 days | CodeBERT model, MPSGraph |
| TreeScan-GPU | 8 days | AST serialization format, parser |
| Full CloneHound (Tree-sitter + GPU similarity) | 14 days | EmbedForge, Tree-sitter parser |

### Phase 4: Fleet & Scale (Weeks 17–20)

| Task | Effort |
|---|---|
| Multi-repo batch scheduling across 1,400+ repos | 5 days |
| PLATO integration: per-agent-type knowledge rooms | 3 days |
| I2I protocol extensions for repo-agent results | 2 days |
| Matrix fleet broadcast channels per agent type | 2 days |
| Interactive Telegram/Matrix commands for agent queries | 3 days |
| Dashboard (optional): web UI for agent findings | 7 days |
| Comprehensive benchmark suite across fleet | 3 days |

### Total Timeline: ~20 weeks to full fleet integration

---

## 10. Risks & Mitigations

### Risk 1: GPU Availability
**Problem:** Not all machines have Apple Silicon GPUs or capable GPUs. Fleet agents run on diverse hardware.
**Mitigation:** All agents have CPU fallback. GPU acceleration is optional — agents auto-detect and choose path.

### Risk 2: Metal Vendor Lock-In
**Problem:** Metal only runs on Apple hardware. Limits deployment.
**Mitigation:** Abstract the compute kernel interface. Write kernels in Metal for Mac, fall back to CPU for Linux servers. Future: compile Rust kernels via `rust-gpu` for Vulkan/SPIR-V cross-platform.

### Risk 3: Kernel Compilation Latency
**Problem:** Metal kernel compilation (PIPELINE_STATE creation) can take 100ms–1s on first dispatch.
**Mitigation:** Precompile Metal shader libraries offline. Cache pipeline states. Use binary archives via `MTLLibrary`.

### Risk 4: Memory Pressure
**Problem:** Large monorepos (5GB+) might overflow GPU memory on consumer GPUs.
**Mitigation:** Streaming dispatch: process files in batches of 50MB. Unified memory on Apple Silicon helps but isn't infinite.

### Risk 5: Debugging Difficulty
**Problem:** GPU compute shader debugging is harder than CPU debugging.
**Mitigation:** CPU reference implementations for every kernel. Validation harness that compares GPU vs CPU output. Use Xcode Metal Debugger for shader stepping.

### Risk 6: Irregular Workloads
**Problem:** Some code analysis tasks are inherently sequential (e.g., cross-file type checking).
**Mitigation:** Hybrid architecture: GPU for data-parallel phases, CPU for sequential phases. The coordinator decides split.

### Risk 7: AST Parsing on GPU
**Problem:** Tree-sitter and traditional parsers are CPU-designed. No production GPU AST parser exists.
**Mitigation:** Parse on CPU (still fast — Tree-sitter processes ~1MB/ms), then convert AST to GPU-friendly flat arrays for analysis.

### Risk 8: Model Inference Cost
**Problem:** Running CodeBERT inference for every function is expensive even on GPU.
**Mitigation:** Use distilled models (CodeBERT-tiny, 6 layers). Cache embeddings; only re-embed changed files. Batch inference aggressively.

---

## Summary

Repo-agents on Metal represent a **genuine first-mover opportunity**. The combination of:

1. **GPU compute for code analysis** — proven in research (HybridSA, GPURegex, cuPQC) but not productized
2. **Apple Silicon unified memory** — zero-copy GPU access eliminates traditional GPU overhead
3. **Cocapn fleet scale** — 1,400+ repos where CPU-bound batch analysis is the current bottleneck
4. **Systems languages** — Rust and Zig give us the performance and GPU access that Python agents can't match

Creates a uniquely favorable position to build and ship the first generation of GPU-accelerated repository agents.

### Recommended Next Steps

1. **Phase 0 immediately** — Set up Metal compute harness, baseline benchmark
2. **Build GREP-Agent first** — Highest speedup (150×), simplest implementation, immediate value for fleet
3. **Build IntegrityForge second** — Production security need, well-understood SHA-256 GPU path
4. **DepGraph-GPU next** — Enables better CI/CD optimization across fleet
5. **Then parallel** — CloneHound + EmbedForge (share GPU inference pipeline)
6. **Wrap each as OpenClaw agent** — Fleet integration is iterative; ship GREP-Agent to fleet first

*— Forgemaster ⚒️, May 2026*