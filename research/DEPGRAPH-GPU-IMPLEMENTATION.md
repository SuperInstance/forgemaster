# DepGraph-GPU Implementation Plan

**Repo:** `SuperInstance/depgraph-gpu`
**Target:** eileen (WSL2, x64, RTX 4050 Ada, CUDA 11.5, sm_86)
**Language:** Rust 1.95.0 + CUDA C kernels via `cudarc`
**Date:** 2026-05-08

---

## 1. File Tree

```
depgraph-gpu/
├── Cargo.toml
├── build.rs
├── README.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── main.rs            # CLI entry point, subcommand dispatch
│   ├── lib.rs             # Public API (for OpenClaw agent use)
│   ├── graph.rs           # Core graph data structure + algorithms
│   ├── parser.rs          # Cargo.toml / package.json / go.mod parsers
│   ├── analysis.rs        # High-level analyses (circular deps, impact, etc.)
│   ├── reporter.rs        # DOT/mermaid/JSON/terminal output
│   ├── plato.rs           # PLATO HTTP client (write dep data to rooms)
│   ├── openclaw.rs        # OpenClaw agent registration + event dispatch
│   └── cuda/
│       ├── mod.rs         # CUDA context init, kernel dispatch, CPU fallback
│       ├── topsort.rs     # Parallel topological sort driver
│       ├── bfs.rs         # Parallel BFS / transitive closure driver
│       └── hash.rs        # Parallel SHA-256 integrity check driver
├── kernels/
│   ├── topsort.cu         # CUDA: parallel Kahn's topological sort
│   ├── bfs.cu             # CUDA: parallel BFS + transitive closure
│   └── hash.cu            # CUDA: SHA-256 batch hash
├── tests/
│   ├── graph_tests.rs     # Unit tests: graph construction, topo sort
│   ├── parser_tests.rs    # Unit tests: manifest parsing
│   ├── cuda_tests.rs      # GPU vs CPU result parity tests
│   └── integration/
│       ├── scan_test.rs   # Full scan against fixture repos
│       └── fixtures/
│           ├── simple/    # 5-node DAG manifests
│           ├── cycle/     # Manifests with circular deps
│           └── large/     # 1K-node synthetic graph
└── benches/
    ├── topsort_bench.rs   # Criterion bench: GPU vs CPU topo sort
    └── scan_bench.rs      # End-to-end scan bench across fixture repos
```

---

## 2. Cargo.toml

```toml
[package]
name = "depgraph-gpu"
version = "0.1.0"
edition = "2021"
rust-version = "1.75"
description = "GPU-accelerated dependency graph analyzer for 1400+ repos"
license = "MIT"

[[bin]]
name = "depgraph"
path = "src/main.rs"

[lib]
name = "depgraph_gpu"
path = "src/lib.rs"

[dependencies]
# CLI
clap = { version = "4.4", features = ["derive", "env"] }

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
toml = "0.8"

# Graph (CPU fallback + comparison)
petgraph = "0.6"

# Async runtime (PLATO HTTP, parallel file I/O)
tokio = { version = "1.35", features = ["full"] }
reqwest = { version = "0.11", features = ["json", "blocking"] }

# File walking
walkdir = "2.4"
ignore = "0.4"   # respects .gitignore

# GPU: cudarc 0.9.x targets CUDA 11.x (0.10+ requires CUDA 12)
cudarc = { version = "0.9", features = ["cuda-11050"], optional = true }

# Hashing (CPU fallback SHA-256)
sha2 = "0.10"

# Error handling
anyhow = "1.0"
thiserror = "1.0"

# Progress display
indicatif = "0.17"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }
tempfile = "3.8"
assert_cmd = "2.0"

[features]
default = ["gpu"]
gpu = ["dep:cudarc"]

[build-dependencies]
cc = "1.0"   # invoke nvcc from build.rs

[[bench]]
name = "topsort_bench"
harness = false

[[bench]]
name = "scan_bench"
harness = false
```

---

## 3. build.rs — Compile CUDA Kernels to PTX

```rust
// build.rs
use std::path::PathBuf;
use std::process::Command;

fn main() {
    // Only compile CUDA kernels when gpu feature is active
    if std::env::var("CARGO_FEATURE_GPU").is_err() {
        return;
    }

    let kernel_dir = PathBuf::from("kernels");
    let out_dir = PathBuf::from(std::env::var("OUT_DIR").unwrap());

    for kernel in &["topsort", "bfs", "hash"] {
        let src = kernel_dir.join(format!("{}.cu", kernel));
        let ptx = out_dir.join(format!("{}.ptx", kernel));

        println!("cargo:rerun-if-changed={}", src.display());

        let status = Command::new("nvcc")
            .args([
                "--ptx",
                "-arch=sm_86",          // RTX 4050 Ada Lovelace
                "--std=c++14",
                "-O3",
                "-o", ptx.to_str().unwrap(),
                src.to_str().unwrap(),
            ])
            .status()
            .expect("nvcc not found — install CUDA 11.5 toolkit");

        if !status.success() {
            panic!("Failed to compile kernel: {}", kernel);
        }
    }
}
```

---

## 4. Module Breakdown

### 4.1 `src/graph.rs` — Core Graph

```rust
//! graph.rs — Core dependency graph data structure.
//!
//! Uses a CSR (Compressed Sparse Row) representation because:
//! 1. Cache-friendly for CPU graph traversals
//! 2. Directly uploadable to CUDA global memory without transformation
//! 3. Trivially serializable for PLATO persistence

use std::collections::{HashMap, HashSet, VecDeque};

/// A node in the dependency graph.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Node {
    pub id: u32,
    pub name: String,       // "serde", "@babel/core", "github.com/foo/bar"
    pub version: String,    // "1.0.0"
    pub lang: Lang,
    pub repo: Option<String>, // Which of our 1400 repos declared this dep
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
pub enum Lang {
    Rust,
    JavaScript,
    Go,
    Maven,
    Unknown,
}

/// Compact graph representation suitable for GPU upload.
///
/// CSR layout:
///   edges[csr_offsets[i] .. csr_offsets[i+1]] = successors of node i
#[derive(Debug, Default)]
pub struct Graph {
    pub nodes: Vec<Node>,
    pub name_to_id: HashMap<String, u32>,
    // CSR adjacency (directed: A→B means A depends on B)
    pub csr_offsets: Vec<u32>,   // len = nodes.len() + 1
    pub csr_edges: Vec<u32>,     // len = total_edges
    pub in_degrees: Vec<u32>,    // per-node in-degree for Kahn's
}

impl Graph {
    pub fn new() -> Self {
        Self::default()
    }

    /// Get or create a node by name+version.
    pub fn get_or_insert(&mut self, name: &str, version: &str, lang: Lang) -> u32 {
        let key = format!("{}@{}", name, version);
        if let Some(&id) = self.name_to_id.get(&key) {
            return id;
        }
        let id = self.nodes.len() as u32;
        self.nodes.push(Node {
            id,
            name: name.to_string(),
            version: version.to_string(),
            lang,
            repo: None,
        });
        self.name_to_id.insert(key, id);
        id
    }

    /// Add a directed edge: `from` depends on `to`.
    ///
    /// Edges are collected in a temporary adjacency list;
    /// call `finalize()` to build CSR before running algorithms.
    pub fn add_edge(&mut self, from: u32, to: u32) {
        // Store as a raw edge for later CSR construction.
        // We abuse csr_edges as a flat edge list until finalize() is called.
        self.csr_edges.push(from);
        self.csr_edges.push(to);
    }

    /// Build CSR from the flat edge list.
    /// Must be called before `topological_sort`, `transitive_closure`, or GPU upload.
    pub fn finalize(&mut self) {
        let n = self.nodes.len();
        if n == 0 { return; }

        // csr_edges is currently [from0, to0, from1, to1, ...]
        // Build proper CSR from this.
        let raw_edges: Vec<(u32, u32)> = self.csr_edges
            .chunks_exact(2)
            .map(|c| (c[0], c[1]))
            .collect();
        self.csr_edges.clear();

        let mut adj: Vec<Vec<u32>> = vec![vec![]; n];
        self.in_degrees = vec![0u32; n];

        for (from, to) in &raw_edges {
            adj[*from as usize].push(*to);
            self.in_degrees[*to as usize] += 1;
        }

        self.csr_offsets = Vec::with_capacity(n + 1);
        self.csr_offsets.push(0);
        for neighbors in &adj {
            let prev = *self.csr_offsets.last().unwrap();
            self.csr_offsets.push(prev + neighbors.len() as u32);
            self.csr_edges.extend_from_slice(neighbors);
        }
    }

    /// CPU topological sort (Kahn's algorithm).
    ///
    /// Returns `Ok(order)` with node IDs in topological order,
    /// or `Err(cycle_members)` if a cycle is detected.
    pub fn topological_sort(&self) -> Result<Vec<u32>, Vec<u32>> {
        let n = self.nodes.len();
        let mut in_deg = self.in_degrees.clone();
        let mut queue: VecDeque<u32> = (0..n as u32)
            .filter(|&i| in_deg[i as usize] == 0)
            .collect();
        let mut order = Vec::with_capacity(n);

        while let Some(node) = queue.pop_front() {
            order.push(node);
            let start = self.csr_offsets[node as usize] as usize;
            let end = self.csr_offsets[node as usize + 1] as usize;
            for &neighbor in &self.csr_edges[start..end] {
                in_deg[neighbor as usize] -= 1;
                if in_deg[neighbor as usize] == 0 {
                    queue.push_back(neighbor);
                }
            }
        }

        if order.len() == n {
            Ok(order)
        } else {
            // Remaining nodes with in_deg > 0 are cycle members
            let cycle: Vec<u32> = (0..n as u32)
                .filter(|&i| in_deg[i as usize] > 0)
                .collect();
            Err(cycle)
        }
    }

    /// CPU BFS transitive closure: returns all transitive dependencies of `start`.
    pub fn transitive_closure(&self, start: u32) -> HashSet<u32> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        queue.push_back(start);

        while let Some(node) = queue.pop_front() {
            let s = self.csr_offsets[node as usize] as usize;
            let e = self.csr_offsets[node as usize + 1] as usize;
            for &neighbor in &self.csr_edges[s..e] {
                if visited.insert(neighbor) {
                    queue.push_back(neighbor);
                }
            }
        }
        visited
    }

    /// Impact analysis: which nodes (transitively) depend on `changed`?
    ///
    /// This is transitive closure on the REVERSE graph — i.e., which nodes
    /// would break if `changed` changed its API.
    pub fn impact_of(&self, changed: u32) -> HashSet<u32> {
        // Build reverse adjacency on the fly (cheaper than storing two graphs)
        let n = self.nodes.len();
        let mut rev_adj: Vec<Vec<u32>> = vec![vec![]; n];
        for from in 0..n as u32 {
            let s = self.csr_offsets[from as usize] as usize;
            let e = self.csr_offsets[from as usize + 1] as usize;
            for &to in &self.csr_edges[s..e] {
                rev_adj[to as usize].push(from);
            }
        }

        let mut impacted = HashSet::new();
        let mut queue = VecDeque::new();
        queue.push_back(changed);

        while let Some(node) = queue.pop_front() {
            for &dep in &rev_adj[node as usize] {
                if impacted.insert(dep) {
                    queue.push_back(dep);
                }
            }
        }
        impacted
    }

    pub fn node_count(&self) -> usize { self.nodes.len() }
    pub fn edge_count(&self) -> usize { self.csr_edges.len() }
}
```

---

### 4.2 `src/parser.rs` — Manifest Parsers

```rust
//! parser.rs — Parse dependency manifests into (name, version, lang) triples.
//!
//! Supports: Cargo.toml, package.json, go.mod, pom.xml (basic).
//! Each parser returns a Vec<Dep> which the caller adds to the Graph.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;
use crate::graph::Lang;

#[derive(Debug, Clone)]
pub struct Dep {
    pub name: String,
    pub version: String,
    pub lang: Lang,
    pub dev: bool,   // dev/test dependency — skip in critical path analysis
}

// ── Cargo.toml ──────────────────────────────────────────────────────────────

#[derive(Deserialize, Debug)]
struct CargoManifest {
    dependencies: Option<HashMap<String, CargoDepValue>>,
    #[serde(rename = "dev-dependencies")]
    dev_dependencies: Option<HashMap<String, CargoDepValue>>,
    workspace: Option<CargoWorkspace>,
}

#[derive(Deserialize, Debug)]
#[serde(untagged)]
enum CargoDepValue {
    Simple(String),                          // dep = "1.0"
    Detailed(HashMap<String, toml::Value>),  // dep = { version = "1.0", features = [...] }
}

#[derive(Deserialize, Debug)]
struct CargoWorkspace {
    members: Option<Vec<String>>,
}

impl CargoDepValue {
    fn version(&self) -> String {
        match self {
            Self::Simple(v) => v.clone(),
            Self::Detailed(map) => map
                .get("version")
                .and_then(|v| v.as_str())
                .unwrap_or("*")
                .to_string(),
        }
    }
}

pub fn parse_cargo_toml(path: &Path) -> Result<Vec<Dep>> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("reading {}", path.display()))?;
    let manifest: CargoManifest = toml::from_str(&content)
        .with_context(|| format!("parsing {}", path.display()))?;

    let mut deps = Vec::new();

    if let Some(d) = manifest.dependencies {
        for (name, val) in d {
            deps.push(Dep {
                name,
                version: val.version(),
                lang: Lang::Rust,
                dev: false,
            });
        }
    }
    if let Some(d) = manifest.dev_dependencies {
        for (name, val) in d {
            deps.push(Dep {
                name,
                version: val.version(),
                lang: Lang::Rust,
                dev: true,
            });
        }
    }
    Ok(deps)
}

// ── package.json ─────────────────────────────────────────────────────────────

#[derive(Deserialize, Debug)]
struct PackageJson {
    dependencies: Option<HashMap<String, String>>,
    #[serde(rename = "devDependencies")]
    dev_dependencies: Option<HashMap<String, String>>,
    #[serde(rename = "peerDependencies")]
    peer_dependencies: Option<HashMap<String, String>>,
}

pub fn parse_package_json(path: &Path) -> Result<Vec<Dep>> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("reading {}", path.display()))?;
    let pkg: PackageJson = serde_json::from_str(&content)
        .with_context(|| format!("parsing {}", path.display()))?;

    let mut deps = Vec::new();

    let mut push_deps = |map: HashMap<String, String>, dev: bool| {
        for (name, version) in map {
            deps.push(Dep {
                name,
                version: version.trim_start_matches('^')
                              .trim_start_matches('~')
                              .to_string(),
                lang: Lang::JavaScript,
                dev,
            });
        }
    };

    if let Some(d) = pkg.dependencies { push_deps(d, false); }
    if let Some(d) = pkg.dev_dependencies { push_deps(d, true); }
    if let Some(d) = pkg.peer_dependencies { push_deps(d, false); }

    Ok(deps)
}

// ── go.mod ────────────────────────────────────────────────────────────────────

pub fn parse_go_mod(path: &Path) -> Result<Vec<Dep>> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("reading {}", path.display()))?;
    let mut deps = Vec::new();
    let mut in_require = false;

    for line in content.lines() {
        let line = line.trim();
        if line.starts_with("require (") || line == "require (" {
            in_require = true;
            continue;
        }
        if in_require && line == ")" {
            in_require = false;
            continue;
        }
        if in_require || line.starts_with("require ") {
            let parts: Vec<&str> = line
                .trim_start_matches("require ")
                .split_whitespace()
                .collect();
            if parts.len() >= 2 && !parts[0].starts_with("//") {
                deps.push(Dep {
                    name: parts[0].to_string(),
                    version: parts[1].trim_start_matches('v').to_string(),
                    lang: Lang::Go,
                    dev: false,
                });
            }
        }
    }
    Ok(deps)
}

// ── Dispatcher ──────────────────────────────────────────────────────────────

pub fn parse_manifest(path: &Path) -> Result<Option<Vec<Dep>>> {
    match path.file_name().and_then(|n| n.to_str()) {
        Some("Cargo.toml") => Ok(Some(parse_cargo_toml(path)?)),
        Some("package.json") => Ok(Some(parse_package_json(path)?)),
        Some("go.mod") => Ok(Some(parse_go_mod(path)?)),
        _ => Ok(None),
    }
}
```

---

### 4.3 `src/cuda/mod.rs` — GPU Dispatch + CPU Fallback

```rust
//! cuda/mod.rs — GPU context management and dispatch.
//!
//! Architecture decision: the GPU path and CPU path share the same
//! Graph struct (CSR layout). The GPU code uploads CSR directly —
//! no re-encoding needed. CPU fallback runs petgraph or our own
//! BFS/Kahn when CUDA is unavailable.

use crate::graph::Graph;
use anyhow::Result;
use std::collections::HashSet;

#[cfg(feature = "gpu")]
use cudarc::driver::{CudaDevice, CudaFunction, LaunchAsync, LaunchConfig};

pub struct GpuContext {
    #[cfg(feature = "gpu")]
    device: std::sync::Arc<CudaDevice>,
    pub available: bool,
}

impl GpuContext {
    /// Try to initialize CUDA. Falls back gracefully if no GPU.
    pub fn new() -> Self {
        #[cfg(feature = "gpu")]
        {
            match CudaDevice::new(0) {
                Ok(dev) => {
                    tracing::info!("CUDA device 0 initialized: {:?}", dev.name());
                    return GpuContext { device: dev, available: true };
                }
                Err(e) => {
                    tracing::warn!("CUDA unavailable ({}), using CPU fallback", e);
                }
            }
        }
        GpuContext {
            #[cfg(feature = "gpu")]
            device: unreachable!(),
            available: false,
        }
    }

    /// Topological sort — GPU if available, else CPU Kahn's.
    pub fn topological_sort(&self, graph: &Graph) -> Result<Vec<u32>> {
        #[cfg(feature = "gpu")]
        if self.available {
            return crate::cuda::topsort::gpu_topsort(&self.device, graph);
        }
        graph.topological_sort().map_err(|cycle| {
            anyhow::anyhow!("Cycle detected in nodes: {:?}", cycle)
        })
    }

    /// Transitive closure via BFS — GPU if available, else CPU BFS.
    pub fn transitive_closure(&self, graph: &Graph, start: u32) -> Result<HashSet<u32>> {
        #[cfg(feature = "gpu")]
        if self.available {
            return crate::cuda::bfs::gpu_bfs(&self.device, graph, start);
        }
        Ok(graph.transitive_closure(start))
    }

    /// SHA-256 hashes of all nodes (for integrity/cache checking).
    pub fn hash_nodes(&self, data: &[Vec<u8>]) -> Result<Vec<[u8; 32]>> {
        #[cfg(feature = "gpu")]
        if self.available {
            return crate::cuda::hash::gpu_sha256_batch(&self.device, data);
        }
        // CPU fallback
        use sha2::{Sha256, Digest};
        Ok(data.iter().map(|d| {
            let mut h = Sha256::new();
            h.update(d);
            h.finalize().into()
        }).collect())
    }
}
```

---

## 5. CUDA Kernel Designs

### 5.1 `kernels/topsort.cu` — Parallel Kahn's

```c
// topsort.cu — Parallel topological sort (Kahn's algorithm)
// Target: sm_86 (RTX 4050 Ada), CUDA 11.5
//
// Algorithm: multi-wave Kahn's.
// Each wave processes all nodes with in_degree == 0 in parallel.
// After each wave, atomically decrement in-degrees of successors.
// Nodes that reach in_degree == 0 join the next wave.
// A cycle exists if total processed < num_nodes after all waves complete.

#include <cuda_runtime.h>
#include <stdint.h>

extern "C" __global__ void topsort_init_queue(
    const uint32_t* in_degrees,
    uint32_t* ready_queue,
    uint32_t* ready_count,
    uint32_t  num_nodes)
{
    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_nodes) return;

    if (in_degrees[tid] == 0) {
        uint32_t pos = atomicAdd(ready_count, 1u);
        ready_queue[pos] = tid;
    }
}

extern "C" __global__ void topsort_step(
    const uint32_t* csr_offsets,
    const uint32_t* csr_edges,
    uint32_t*       in_degrees,
    const uint32_t* current_wave,
    const uint32_t  wave_size,
    uint32_t*       next_wave,
    uint32_t*       next_wave_size,
    uint32_t*       result,
    uint32_t*       result_count)
{
    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= wave_size) return;

    uint32_t node = current_wave[tid];

    // Append to result in order-stable position
    uint32_t out_pos = atomicAdd(result_count, 1u);
    result[out_pos] = node;

    // Decrement in-degrees of all successors
    uint32_t edge_start = csr_offsets[node];
    uint32_t edge_end   = csr_offsets[node + 1];

    for (uint32_t e = edge_start; e < edge_end; e++) {
        uint32_t neighbor = csr_edges[e];
        // atomicSub returns old value; new value = old - 1
        uint32_t old_deg = atomicSub(&in_degrees[neighbor], 1u);
        if (old_deg == 1) {
            // This neighbor just reached 0 — add to next wave
            uint32_t q_pos = atomicAdd(next_wave_size, 1u);
            next_wave[q_pos] = neighbor;
        }
    }
}
```

### 5.2 `kernels/bfs.cu` — Parallel BFS / Transitive Closure

```c
// bfs.cu — Parallel BFS for transitive closure
// Each frontier node fans out its edges in parallel.
// Uses a visited bitset (one bit per node) for O(n/32) memory.

#include <cuda_runtime.h>
#include <stdint.h>

// Atomically set bit `node` in the visited bitset.
// Returns 1 if this was the first visit, 0 if already visited.
__device__ int mark_visited(uint32_t* visited, uint32_t node) {
    uint32_t word = node / 32;
    uint32_t bit  = 1u << (node % 32);
    uint32_t old  = atomicOr(&visited[word], bit);
    return (old & bit) == 0 ? 1 : 0;
}

extern "C" __global__ void bfs_frontier_expand(
    const uint32_t* csr_offsets,
    const uint32_t* csr_edges,
    const uint32_t* frontier,
    const uint32_t  frontier_size,
    uint32_t*       next_frontier,
    uint32_t*       next_frontier_size,
    uint32_t*       visited,
    uint32_t        num_nodes)
{
    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= frontier_size) return;

    uint32_t node = frontier[tid];
    uint32_t edge_start = csr_offsets[node];
    uint32_t edge_end   = csr_offsets[node + 1];

    for (uint32_t e = edge_start; e < edge_end; e++) {
        uint32_t neighbor = csr_edges[e];
        if (mark_visited(visited, neighbor)) {
            uint32_t pos = atomicAdd(next_frontier_size, 1u);
            next_frontier[pos] = neighbor;
        }
    }
}
```

### 5.3 `kernels/hash.cu` — Parallel SHA-256 Batch

```c
// hash.cu — Parallel SHA-256 for up to 65535 small files/blobs
// Each thread block processes one file independently.
// Files are assumed to be <= 4KB each (dependency manifest files).
// Larger files are split on the CPU before dispatch.

#include <cuda_runtime.h>
#include <stdint.h>
#include <string.h>

// SHA-256 constants
__constant__ uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

#define ROTR(x,n) (((x) >> (n)) | ((x) << (32 - (n))))
#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define S0(x) (ROTR(x,2)  ^ ROTR(x,13) ^ ROTR(x,22))
#define S1(x) (ROTR(x,6)  ^ ROTR(x,11) ^ ROTR(x,25))
#define s0(x) (ROTR(x,7)  ^ ROTR(x,18) ^ ((x) >> 3))
#define s1(x) (ROTR(x,17) ^ ROTR(x,19) ^ ((x) >> 10))

__device__ void sha256_block(uint32_t* state, const uint8_t* block) {
    uint32_t W[64];
    for (int i = 0; i < 16; i++) {
        W[i] = ((uint32_t)block[i*4]   << 24) |
               ((uint32_t)block[i*4+1] << 16) |
               ((uint32_t)block[i*4+2] <<  8) |
               ((uint32_t)block[i*4+3]);
    }
    for (int i = 16; i < 64; i++)
        W[i] = s1(W[i-2]) + W[i-7] + s0(W[i-15]) + W[i-16];

    uint32_t a=state[0], b=state[1], c=state[2], d=state[3],
             e=state[4], f=state[5], g=state[6], h=state[7];

    for (int i = 0; i < 64; i++) {
        uint32_t T1 = h + S1(e) + CH(e,f,g) + K[i] + W[i];
        uint32_t T2 = S0(a) + MAJ(a,b,c);
        h=g; g=f; f=e; e=d+T1;
        d=c; c=b; b=a; a=T1+T2;
    }
    state[0]+=a; state[1]+=b; state[2]+=c; state[3]+=d;
    state[4]+=e; state[5]+=f; state[6]+=g; state[7]+=h;
}

// Entry point: one thread per file, files <= 4096 bytes
extern "C" __global__ void sha256_batch(
    const uint8_t* __restrict__ file_data,   // packed: all files concatenated
    const uint32_t* __restrict__ offsets,    // offsets[i] = start of file i in file_data
    const uint32_t* __restrict__ sizes,      // sizes[i] = byte length of file i
    uint8_t* __restrict__ hashes,            // output: 32 bytes per file
    uint32_t num_files)
{
    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_files) return;

    const uint8_t* data = file_data + offsets[tid];
    uint32_t size = sizes[tid];

    uint32_t state[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    // Process 64-byte blocks (simplified — no padding for manifests < 4KB)
    // Production version would add proper SHA-256 padding.
    uint8_t block[64];
    for (uint32_t off = 0; off < size; off += 64) {
        uint32_t block_len = min(64u, size - off);
        memset(block, 0, 64);
        memcpy(block, data + off, block_len);
        if (block_len < 64) {
            block[block_len] = 0x80; // padding sentinel
        }
        sha256_block(state, block);
    }

    uint8_t* out = hashes + tid * 32;
    for (int i = 0; i < 8; i++) {
        out[i*4+0] = (state[i] >> 24) & 0xFF;
        out[i*4+1] = (state[i] >> 16) & 0xFF;
        out[i*4+2] = (state[i] >>  8) & 0xFF;
        out[i*4+3] = (state[i]      ) & 0xFF;
    }
}
```

---

## 6. `src/main.rs` — CLI Skeleton

```rust
//! main.rs — depgraph CLI
//!
//! Subcommands:
//!   scan     — Walk repos, build graph, save to PLATO
//!   check    — Detect circular deps, outdated versions, dupes
//!   impact   — "If X changes, what breaks?" transitive impact analysis
//!   visualize — Generate DOT/mermaid graph output

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use tracing_subscriber::EnvFilter;

mod graph;
mod parser;
mod analysis;
mod reporter;
mod plato;
mod openclaw;
pub mod cuda;

#[derive(Parser)]
#[command(name = "depgraph", version, about = "GPU-accelerated dependency graph analyzer")]
struct Cli {
    /// Enable verbose logging
    #[arg(short, long, global = true)]
    verbose: bool,

    /// PLATO base URL (default: http://147.224.38.131:8847)
    #[arg(long, global = true, env = "PLATO_URL",
          default_value = "http://147.224.38.131:8847")]
    plato_url: String,

    /// Disable GPU acceleration (force CPU path)
    #[arg(long, global = true)]
    no_gpu: bool,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Scan repos and build dependency graph
    Scan {
        /// Root directory containing repos (or a single repo)
        #[arg(value_name = "PATH")]
        path: PathBuf,

        /// Output format: json, dot, mermaid, summary
        #[arg(short, long, default_value = "summary")]
        output: String,

        /// Write results to PLATO room
        #[arg(long)]
        plato: bool,

        /// Maximum depth for recursive repo discovery
        #[arg(long, default_value = "3")]
        depth: usize,
    },

    /// Check for problems: circular deps, version conflicts, duplicates
    Check {
        #[arg(value_name = "PATH")]
        path: PathBuf,

        /// Exit code 1 if any issues found (for CI use)
        #[arg(long)]
        strict: bool,
    },

    /// Compute transitive impact of changing a dependency
    Impact {
        #[arg(value_name = "PATH")]
        path: PathBuf,

        /// Dependency name (e.g., "serde", "react", "github.com/foo/bar")
        #[arg(value_name = "DEP")]
        dep: String,

        /// Version of the dep (default: match any)
        #[arg(short, long)]
        version: Option<String>,
    },

    /// Generate visualization (DOT or mermaid)
    Visualize {
        #[arg(value_name = "PATH")]
        path: PathBuf,

        /// Output format: dot or mermaid
        #[arg(short, long, default_value = "dot")]
        format: String,

        /// Output file (default: stdout)
        #[arg(short, long)]
        output: Option<PathBuf>,

        /// Only include nodes reachable from this dep
        #[arg(long)]
        focus: Option<String>,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    let log_level = if cli.verbose { "debug" } else { "info" };
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::new(log_level))
        .init();

    let gpu = if cli.no_gpu {
        cuda::GpuContext { available: false }
    } else {
        cuda::GpuContext::new()
    };

    if gpu.available {
        tracing::info!("GPU acceleration: ENABLED (sm_86)");
    } else {
        tracing::info!("GPU acceleration: DISABLED (CPU fallback)");
    }

    match cli.command {
        Commands::Scan { path, output, plato, depth } => {
            cmd_scan(&gpu, &path, &output, plato, depth, &cli.plato_url).await?;
        }
        Commands::Check { path, strict } => {
            let exit_code = cmd_check(&gpu, &path, strict).await?;
            std::process::exit(exit_code);
        }
        Commands::Impact { path, dep, version } => {
            cmd_impact(&gpu, &path, &dep, version.as_deref()).await?;
        }
        Commands::Visualize { path, format, output, focus } => {
            cmd_visualize(&gpu, &path, &format, output.as_deref(), focus.as_deref()).await?;
        }
    }

    Ok(())
}

async fn cmd_scan(
    gpu: &cuda::GpuContext,
    path: &PathBuf,
    output: &str,
    write_plato: bool,
    depth: usize,
    plato_url: &str,
) -> Result<()> {
    use indicatif::{ProgressBar, ProgressStyle};

    tracing::info!("Scanning: {}", path.display());
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::default_spinner()
        .template("{spinner} {msg}")?);
    pb.set_message("Walking manifests...");

    let mut g = graph::Graph::new();
    let manifests = analysis::discover_manifests(path, depth)?;
    pb.set_length(manifests.len() as u64);

    for manifest_path in &manifests {
        pb.inc(1);
        pb.set_message(format!("{}", manifest_path.display()));
        if let Some(deps) = parser::parse_manifest(manifest_path)? {
            let repo_name = manifest_path
                .parent()
                .and_then(|p| p.file_name())
                .and_then(|n| n.to_str())
                .unwrap_or("unknown")
                .to_string();

            let parent_id = g.get_or_insert(
                &repo_name,
                "local",
                graph::Lang::Unknown,
            );
            g.nodes[parent_id as usize].repo = Some(repo_name);

            for dep in deps {
                if dep.dev { continue; }
                let dep_id = g.get_or_insert(&dep.name, &dep.version, dep.lang);
                g.add_edge(parent_id, dep_id);
            }
        }
    }

    g.finalize();
    pb.finish_with_message(format!(
        "Built graph: {} nodes, {} edges",
        g.node_count(), g.edge_count()
    ));

    reporter::render(&g, output, &mut std::io::stdout())?;

    if write_plato {
        plato::write_graph_snapshot(&g, plato_url).await?;
    }

    Ok(())
}

async fn cmd_check(
    gpu: &cuda::GpuContext,
    path: &PathBuf,
    strict: bool,
) -> Result<i32> {
    let mut g = graph::Graph::new();
    let manifests = analysis::discover_manifests(path, 3)?;
    for manifest_path in &manifests {
        if let Some(deps) = parser::parse_manifest(manifest_path)? {
            let parent = manifest_path
                .parent()
                .and_then(|p| p.file_name())
                .and_then(|n| n.to_str())
                .unwrap_or("unknown")
                .to_string();
            let pid = g.get_or_insert(&parent, "local", graph::Lang::Unknown);
            for dep in deps.into_iter().filter(|d| !d.dev) {
                let did = g.get_or_insert(&dep.name, &dep.version, dep.lang);
                g.add_edge(pid, did);
            }
        }
    }
    g.finalize();

    let issues = analysis::check_all(&g, gpu)?;
    let has_issues = !issues.is_empty();

    for issue in &issues {
        println!("{}", issue);
    }

    if !has_issues {
        println!("No issues found.");
    }

    Ok(if strict && has_issues { 1 } else { 0 })
}

async fn cmd_impact(
    gpu: &cuda::GpuContext,
    path: &PathBuf,
    dep: &str,
    version: Option<&str>,
) -> Result<()> {
    let mut g = graph::Graph::new();
    let manifests = analysis::discover_manifests(path, 3)?;
    for mp in &manifests {
        if let Some(deps) = parser::parse_manifest(mp)? {
            let parent = mp.parent()
                .and_then(|p| p.file_name())
                .and_then(|n| n.to_str()).unwrap_or("unknown").to_string();
            let pid = g.get_or_insert(&parent, "local", graph::Lang::Unknown);
            for d in deps.into_iter().filter(|d| !d.dev) {
                let did = g.get_or_insert(&d.name, &d.version, d.lang);
                g.add_edge(pid, did);
            }
        }
    }
    g.finalize();

    let ver = version.unwrap_or("*");
    let key = format!("{}@{}", dep, ver);
    let target_id = g.name_to_id.iter()
        .find(|(k, _)| k.starts_with(&format!("{}@", dep)))
        .map(|(_, &id)| id);

    match target_id {
        None => println!("Dependency '{}' not found in graph.", dep),
        Some(id) => {
            let impacted = g.impact_of(id);
            println!("Changing '{}' affects {} packages:", dep, impacted.len());
            let mut names: Vec<&str> = impacted.iter()
                .map(|&i| g.nodes[i as usize].name.as_str())
                .collect();
            names.sort();
            for name in names {
                println!("  - {}", name);
            }
        }
    }
    Ok(())
}

async fn cmd_visualize(
    _gpu: &cuda::GpuContext,
    path: &PathBuf,
    format: &str,
    output: Option<&std::path::Path>,
    focus: Option<&str>,
) -> Result<()> {
    let mut g = graph::Graph::new();
    let manifests = analysis::discover_manifests(path, 3)?;
    for mp in &manifests {
        if let Some(deps) = parser::parse_manifest(mp)? {
            let parent = mp.parent()
                .and_then(|p| p.file_name())
                .and_then(|n| n.to_str()).unwrap_or("unknown").to_string();
            let pid = g.get_or_insert(&parent, "local", graph::Lang::Unknown);
            for d in deps.into_iter().filter(|d| !d.dev) {
                let did = g.get_or_insert(&d.name, &d.version, d.lang);
                g.add_edge(pid, did);
            }
        }
    }
    g.finalize();

    let mut out: Box<dyn std::io::Write> = match output {
        Some(p) => Box::new(std::fs::File::create(p)?),
        None => Box::new(std::io::stdout()),
    };

    reporter::render_viz(&g, format, focus, &mut out)?;
    Ok(())
}
```

---

## 7. `src/plato.rs` — PLATO Integration

```rust
//! plato.rs — Write dependency graph data to PLATO knowledge base.
//!
//! PLATO rooms used:
//!   depgraph/snapshots/{YYYY-MM-DD}   — Full graph JSON
//!   depgraph/checks/latest            — Latest check results
//!   depgraph/impact/{dep_name}        — Per-dep impact reports

use anyhow::Result;
use crate::graph::Graph;

const PLATO_ROOM_PREFIX: &str = "depgraph";

pub async fn write_graph_snapshot(graph: &Graph, base_url: &str) -> Result<()> {
    let today = chrono::Utc::now().format("%Y-%m-%d");
    let room = format!("{}/snapshots/{}", PLATO_ROOM_PREFIX, today);

    let payload = serde_json::json!({
        "node_count": graph.node_count(),
        "edge_count": graph.edge_count(),
        "nodes": graph.nodes,
        "timestamp": chrono::Utc::now().to_rfc3339(),
    });

    let client = reqwest::Client::new();
    let url = format!("{}/rooms/{}", base_url, room);
    client.post(&url)
        .json(&payload)
        .send()
        .await?
        .error_for_status()?;

    tracing::info!("Wrote graph snapshot to PLATO room: {}", room);
    Ok(())
}

pub async fn write_check_results(
    results: &[String],
    base_url: &str,
) -> Result<()> {
    let room = format!("{}/checks/latest", PLATO_ROOM_PREFIX);
    let payload = serde_json::json!({
        "issues": results,
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "issue_count": results.len(),
    });

    let client = reqwest::Client::new();
    client.post(&format!("{}/rooms/{}", base_url, room))
        .json(&payload)
        .send()
        .await?
        .error_for_status()?;
    Ok(())
}
```

---

## 8. OpenClaw Agent Registration

```rust
//! openclaw.rs — Register depgraph as an OpenClaw agent.
//!
//! When invoked as an agent (not via CLI), listens for:
//!   - "scan <path>" — full scan + PLATO write
//!   - "check <path>" — check for problems
//!   - "impact <dep>" — impact analysis
//!
//! Agent ID: depgraph-gpu
//! Channel: agent/depgraph-gpu

use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct AgentRequest {
    pub action: String,       // "scan" | "check" | "impact" | "visualize"
    pub path: Option<String>,
    pub dep: Option<String>,
    pub options: Option<serde_json::Value>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AgentResponse {
    pub success: bool,
    pub data: serde_json::Value,
    pub issues: Vec<String>,
    pub plato_room: Option<String>,
}

/// Entry point when invoked as OpenClaw agent (receives JSON on stdin)
pub async fn run_as_agent() -> Result<()> {
    let stdin = std::io::stdin();
    let req: AgentRequest = serde_json::from_reader(stdin)?;
    tracing::info!("Agent request: {:?}", req);

    // Dispatch to the same logic as the CLI subcommands
    let response = dispatch_agent_request(req).await?;
    println!("{}", serde_json::to_string_pretty(&response)?);
    Ok(())
}

async fn dispatch_agent_request(req: AgentRequest) -> Result<AgentResponse> {
    match req.action.as_str() {
        "scan" => {
            // ... call cmd_scan logic
            Ok(AgentResponse {
                success: true,
                data: serde_json::json!({"status": "scan complete"}),
                issues: vec![],
                plato_room: Some("depgraph/snapshots/latest".to_string()),
            })
        }
        _ => Ok(AgentResponse {
            success: false,
            data: serde_json::Value::Null,
            issues: vec![format!("Unknown action: {}", req.action)],
            plato_room: None,
        })
    }
}
```

---

## 9. PLATO Room Structure

```
depgraph/
├── snapshots/
│   ├── 2026-05-08     ← Full graph JSON (nodes, edges, metadata)
│   ├── 2026-05-09
│   └── latest         ← Symlink/alias to most recent
├── checks/
│   ├── latest         ← Most recent check results
│   └── history/       ← Archived check runs
├── impact/
│   ├── serde          ← "If serde changes, X/Y/Z repos break"
│   ├── tokio
│   └── ...
└── fleet-overview/
    └── 2026-05-08     ← Cross-repo dependency heatmap, circular dep list
```

Each room is a JSON document. The PLATO HTTP API (147.224.38.131:8847) is used:
- `POST /rooms/{room}` — write/overwrite
- `GET /rooms/{room}` — read
- `GET /rooms/depgraph/` — list sub-rooms

---

## 10. Test Strategy

### Unit Tests

```rust
// tests/graph_tests.rs
#[cfg(test)]
mod tests {
    use depgraph_gpu::graph::{Graph, Lang};

    #[test]
    fn test_topsort_simple() {
        let mut g = Graph::new();
        let a = g.get_or_insert("a", "1.0", Lang::Rust);
        let b = g.get_or_insert("b", "1.0", Lang::Rust);
        let c = g.get_or_insert("c", "1.0", Lang::Rust);
        g.add_edge(a, b);  // a → b
        g.add_edge(b, c);  // b → c
        g.finalize();

        let order = g.topological_sort().unwrap();
        // a must come before b, b before c
        let pos: std::collections::HashMap<u32, usize> = order.iter()
            .enumerate().map(|(i, &n)| (n, i)).collect();
        assert!(pos[&a] < pos[&b]);
        assert!(pos[&b] < pos[&c]);
    }

    #[test]
    fn test_topsort_detects_cycle() {
        let mut g = Graph::new();
        let a = g.get_or_insert("a", "1.0", Lang::Rust);
        let b = g.get_or_insert("b", "1.0", Lang::Rust);
        g.add_edge(a, b);
        g.add_edge(b, a);  // cycle!
        g.finalize();
        assert!(g.topological_sort().is_err());
    }

    #[test]
    fn test_transitive_closure() {
        let mut g = Graph::new();
        let a = g.get_or_insert("a", "1.0", Lang::Rust);
        let b = g.get_or_insert("b", "1.0", Lang::Rust);
        let c = g.get_or_insert("c", "1.0", Lang::Rust);
        g.add_edge(a, b);
        g.add_edge(b, c);
        g.finalize();
        let closure = g.transitive_closure(a);
        assert!(closure.contains(&b));
        assert!(closure.contains(&c));
    }

    #[test]
    fn test_impact_of() {
        let mut g = Graph::new();
        let a = g.get_or_insert("a", "1.0", Lang::Rust);
        let b = g.get_or_insert("b", "1.0", Lang::Rust);
        let c = g.get_or_insert("c", "1.0", Lang::Rust);
        g.add_edge(a, b);
        g.add_edge(c, b);
        g.finalize();
        // Both a and c depend on b — changing b impacts both
        let impact = g.impact_of(b);
        assert!(impact.contains(&a));
        assert!(impact.contains(&c));
    }
}
```

### GPU Parity Tests

```rust
// tests/cuda_tests.rs
#[cfg(all(test, feature = "gpu"))]
mod cuda_parity_tests {
    use depgraph_gpu::{cuda::GpuContext, graph::{Graph, Lang}};

    fn build_test_graph(n: u32) -> Graph {
        let mut g = Graph::new();
        for i in 0..n {
            g.get_or_insert(&format!("node{}", i), "1.0", Lang::Rust);
        }
        for i in 0..n-1 {
            g.add_edge(i, i+1);
        }
        g.finalize();
        g
    }

    #[test]
    fn gpu_topsort_matches_cpu() {
        let g = build_test_graph(1000);
        let cpu = g.topological_sort().unwrap();
        let gpu_ctx = GpuContext::new();
        if !gpu_ctx.available { return; } // skip on CPU-only machines
        let gpu = gpu_ctx.topological_sort(&g).unwrap();
        // Both should produce valid topological orderings
        // (may differ in tie-breaking, so verify ordering property not equality)
        let cpu_pos: std::collections::HashMap<u32, usize> = cpu.iter()
            .enumerate().map(|(i, &n)| (n, i)).collect();
        let gpu_pos: std::collections::HashMap<u32, usize> = gpu.iter()
            .enumerate().map(|(i, &n)| (n, i)).collect();
        for i in 0..999u32 {
            assert!(cpu_pos[&i] < cpu_pos[&(i+1)]);
            assert!(gpu_pos[&i] < gpu_pos[&(i+1)]);
        }
    }
}
```

---

## 11. Performance Targets

| Operation | Nodes | CPU Target | GPU Target | Speedup |
|---|---|---|---|---|
| Topological sort | 10K | ~500ms | ~10ms | 50× |
| Transitive closure (single node) | 10K | ~200ms | ~5ms | 40× |
| Full scan (1400 repos) | ~50K deps | ~30s | ~2s | 15× |
| SHA-256 batch (manifest files) | 10K files | ~1s | ~30ms | 33× |

The scan speedup is lower than the algorithmic speedups because I/O (walking 1400 repos) dominates — `walkdir` + `tokio::spawn` handles that with Rayon-style parallelism on the CPU regardless.

---

## 12. Implementation Order

1. `graph.rs` + `parser.rs` — pure Rust, no GPU, tests first
2. `src/main.rs` scan + check subcommands (CPU path only)
3. `build.rs` + `kernels/topsort.cu` — first GPU kernel
4. `cuda/topsort.rs` — cudarc driver for topsort kernel
5. `cuda/bfs.rs` + `kernels/bfs.cu`
6. `plato.rs` — PLATO writes
7. `kernels/hash.cu` + `cuda/hash.rs`
8. `reporter.rs` — DOT/mermaid output
9. `openclaw.rs` — agent registration
10. Benchmarks + CI

The whole thing compiles and runs useful scan+check without the GPU feature enabled. GPU is an enhancement that you opt into — no CUDA toolkit required for basic usage.
