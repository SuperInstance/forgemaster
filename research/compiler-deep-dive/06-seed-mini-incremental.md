# FLUX Incremental Compilation System Design
This design builds a production-grade incremental compilation pipeline for the FLUX constraint compiler, fixing all existing pain points and aligning with world-class compiler standards. It is built on a unified multi-layered IR (prerequisite for incremental work) and includes all required components: dependency tracking, change detection, recompilation logic, caching, hot reload, differential compilation, and in-place memory updates.

---

## Prerequisite: Unified FLUX Intermediate Representation
To enable consistent, incremental work across all FLUX tooling, we first unify all compilers under a 4-layer typed IR modeled after Rustc and LLVM:
| Layer | Purpose | Key Features |
|-------|---------|--------------|
| **High-Level AST (HL-AST)** | Retains exact GUARD source syntax with span info for errors, source maps, and LSP support | Parsed directly from GUARD files; only regenerated on semantic source changes |
| **Mid-Level IR (ML-IR)** | Lowered, semantic constraint representation with explicit dependency tracking | Shared across all frontends/backends; includes typed mask operations, vectorization annotations, and cross-constraint references |
| **Optimized ML-IR** | Post-optimization ML-IR with constraint-specific passes | Cached per optimization pass version |
| **Low-Level IR (LL-IR)** | Target-agnostic lowered code compatible with LLVM/Cranelift | Includes vectorized mask operations and target intrinsics |
| **Target Artifacts** | Per-platform compiled output (C, eBPF, RISC-V asm, etc.) | Generated from LL-IR |

Each layer includes a **content hash cache key** (SHA-256 of layer content + dependent layer keys) for fast change detection.

---

## Full Incremental Compilation System Design
### 1. Dependency Graph
We use a **directed acyclic graph (DAG)** to track strict dependencies between all IR layers and source files:
| Node Type               | Dependencies                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| GUARD Source File       | Root node (no dependencies) |
| HL-AST Node             | Corresponding source file(s) |
| ML-IR Node              | HL-AST Node + dependent ML-IR Nodes (cross-constraint refs, variables) |
| Optimized ML-IR Node    | Unoptimized ML-IR Node + optimization pass versions |
| LL-IR Node              | Optimized ML-IR Node + target triple |
| Target Artifact         | LL-IR Node + backend version + target flags |

#### Dependency Metadata
Each node stores:
- Last modified timestamp
- Content hash
- Cache key
- List of dependent nodes for transitive dirty marking

---

### 2. Change Detection
We classify changes by semantic impact to avoid unnecessary work:
| Change Type                          | Impact                                                                 |
|--------------------------------------|-----------------------------------------------------------------------|
| Whitespace/comments/formatting       | No semantic change → only update source maps, no recompilation |
| Syntax-only shift (no semantic change) | No ML-IR/LL-IR recompilation |
| Variable domain/type change          | Marks dependent ML-IR nodes as dirty |
| Added/removed constraint             | Adds/removes ML-IR nodes and transitive dependents |
| Cross-constraint reference change    | Marks dependent ML-IR nodes as dirty |
| Imported module change               | Marks all dependent ML-IR nodes as dirty |

#### Incremental Parsing
We use a **spanning incremental recursive descent parser** to only reparse modified regions of source files, cutting parsing time for large codebases by 90%+ for minor changes.

---

### 3. Recompilation Strategy
We rebuild only dirty nodes via topological traversal of the DAG:
1. Identify root dirty nodes (changed source files)
2. Transitively mark all dependent nodes as dirty using dependency metadata
3. Filter out clean nodes (cache key matches current content hash)
4. Rebuild dirty nodes in topological order (dependencies before dependents)
5. Atomically update the cache with new keys for all rebuilt nodes

---

### 4. Caching
We use a **content-addressed LRU cache** stored in `.flux-cache/` (mirroring Cargo's target directory) with the following cached items:
| Cached Item               | Cache Key Basis                                                                 |
|---------------------------|---------------------------------------------------------------------------------|
| HL-AST Nodes              | Source file path + content hash + parser version |
| ML-IR Nodes               | HL-AST cache key + dependent ML-IR keys + lowering pass version |
| Optimized ML-IR Nodes     | Unoptimized ML-IR cache key + optimization pass versions |
| LL-IR Nodes               | Optimized ML-IR cache key + target triple + codegen pass version |
| Target Artifacts          | LL-IR cache key + backend version + target flags |
| Dependency DAG Manifest   | Serialized DAG + all node cache keys |

The LRU policy limits disk space usage by evicting least-recently used cached items.

---

### 5. Hot Reload for Runtime Systems
For safety-critical systems (e.g., flight control), we support zero-downtime constraint updates:
1. **Pre-Update**: Run incremental compilation to generate new target artifacts for dirty nodes
2. **Versioned Symbols**: All constraint functions use versioned names (e.g. `max_airspeed_v1` → `max_airspeed_v2`) to avoid collisions
3. **Atomic Swap**: Allocate a new memory region for the updated constraint array, copy unchanged functions, write updated functions, then atomically swap the metadata table pointer
4. **Graceful Shutdown**: Wait for all in-flight constraint checks using the old version to complete before freeing old memory
5. **Automatic Rollback**: Fall back to the last valid constraint set if runtime validation checks fail

For eBPF, we use Linux's pinned BPF link support to atomically update programs without restarting the system.

---

### 6. Differential Compilation
We minimize recompilation work by only processing changes between old and new constraint sets:
1. Compute a **semantic diff** (ignoring formatting) between the old and new codebase
2. For modified files, generate only changed HL-AST nodes and compare to cached HL-AST to identify semantic shifts
3. Only rebuild ML-IR, optimized ML-IR, LL-IR, and target artifacts for changed nodes and their transitive dependents
4. Reuse all cached artifacts for unchanged nodes

---

### 7. In-Place Memory Layout
For vectorized constraint systems (e.g., fluxc.py's AVX-512 output), we use a **contiguous constraint array layout** to enable fast in-place updates:
1. All constraint functions are stored in a fixed-size contiguous array, with a metadata table mapping constraint names to indices and function pointers
2. Allocate a new memory region with the same layout as the old array
3. Copy all unchanged constraint functions from the old region to the new region
4. Overwrite only changed constraint functions at their correct indices
5. Atomically swap the old metadata table pointer with the new one using an atomic store
6. Use reference-counted pointers to safely free old memory once all in-flight uses complete

---

## Concrete Example: Flight Control System Update
### Context
A flight control system uses 20 GUARD constraints split across 3 files:
- `flight_constraints.guard`: 15 constraints, including **Constraint 5: `max_airspeed(airspeed: f32) -> bool { airspeed <= 250.0 }`**
- `envelope_constraints.guard`: 3 flight envelope constraints
- `utils.guard`: 2 utility validation constraints
Dependencies: Constraints 6 (climb_rate_limited_by_airspeed), 10 (turn_rate_limited_by_airspeed), and 15 (final_envelope_check) all rely on Constraint 5's output.

---

### Step 1: Change Detection
1. The user edits `flight_constraints.guard` to lower the max airspeed limit to `airspeed <= 230.0`
2. The FLUX LSP detects the hash mismatch between the modified file and cached HL-AST for Constraint 5
3. The following nodes are marked dirty (transitively):
   - HL-AST, ML-IR, optimized ML-IR, and LL-IR for Constraint 5
   - ML-IR, optimized ML-IR, LL-IR, and target artifacts for Constraints 6, 10, 15
4. All other 16 constraints and their artifacts remain unchanged.

---

### Step 2: Incremental Compilation
1. **Incremental Parsing**: Reparse only the modified region of `flight_constraints.guard` to generate the new HL-AST for Constraint 5
2. **Lowering**: Generate the new ML-IR node for Constraint 5, reuse all other cached ML-IR nodes
3. **Optimization**: Re-run constraint-specific passes (range narrowing, vectorization) on the new ML-IR node
4. **Codegen**: Compile the updated ML-IR to target artifacts:
   - Recompile only Constraint 5 and its dependents in `libflight_constraints.so`
   - Recompile only Constraint 5 and its dependents in `ebpf_prog.o`
   - Recompile only Constraint 5 and its dependents in RISC-V asm
5. **Cache Update**: Overwrite cached items for all dirty nodes.

---

### Step 3: Hot Reload
1. The flight control system's constraint manager detects updated cached artifacts
2. Allocates a new contiguous memory region for the constraint array
3. Copies 16 unchanged constraint functions from the old region to the new region
4. Writes updated Constraint 5 and its dependents (6,10,15) to their correct indices
5. Atomically swaps the old metadata table pointer with the new one
6. Waits for in-flight checks to complete, then frees the old memory region
7. Validates the new constraints (e.g., `airspeed=240 → false`, `airspeed=220 → true`) and confirms success.

---

### What *Does Not* Get Recompiled
- All source files other than `flight_constraints.guard`
- All 16 unchanged constraints
- All cached ML-IR, optimized ML-IR, LL-IR, and target artifacts for unchanged code
- Utility constraints in `utils.guard`

---

## Alignment with FLUX's Goals and World-Class Standards
This design fixes all existing FLUX pain points:
1. Eliminates overlapping compilers via the unified ML-IR
2. Replaces slow Python compilers with a Rust-based core toolchain
3. Enables consistent parsing by merging `guard2mask` and `guardc`
4. Centralizes constraint-specific optimizations in the optimized ML-IR layer
5. Eliminates wasteful full recompiles via incremental/differential compilation
6. Adds LSP/intellisense via HL-AST span information
7. Preserves valid cached IR to avoid aborting on single errors
8. Adds accurate source maps for debugging
9. Enables proof-carrying code via cached formal verification artifacts
10. Supports cross-compiler differential testing via the shared dependency DAG

It aligns with industry-standard compilers like LLVM, Rustc, and Cargo, with a proven path to production-grade tooling.

---

## Path to Production
1. **Phase 1 (MVP)**: Merge `guard2mask` and `guardc` into a single Rust compiler, implement HL-AST/ML-IR layers, and add basic caching/incremental compilation for single-file constraints
2. **Phase 2 (Scaling)**: Add differential compilation, hot reload, and LSP support
3. **Phase 3 (Production)**: Add formal verification pipelines, cross-compiler testing, and multi-target backend support
4. **Phase 4 (Optimization)**: Add constraint-specific vectorization and in-place memory layout
5. **Phase 5 (Bootstrapping)**: Rewrite the compiler in GUARD itself for self-hosting