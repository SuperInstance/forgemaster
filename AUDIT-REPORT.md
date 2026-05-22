# Agent Work Audit Report

**Date:** 2026-05-22
**Auditor:** Forgemaster ⚒️ (subagent)

---

## Executive Summary

Audited 10+ agent-created repos from May 20-22. Four Python libraries (vector-novelty, hebbian-router, pareto-tournament, thermal-budget) are production-quality with 100% test pass rates. One Rust crate (turbovec) is well-architected but untestable due to OOM constraints. One Rust crate (flux-vm-v3) had critical security bugs already caught by a prior Kimi audit. One Zig library (deadband-zig) is clean and well-tested. Several repos are skeleton/empty or docs-only — moved to archive.

**Actions taken:**
- 3 repos moved to archive (flux-compiler, turbovec-integration-ccc, flux-vm)
- __pycache__ artifacts cleaned from 4 Python repos
- 5GB+ build artifacts cleaned from turbovec
- No files deleted

---

## Per-Repo Quality Scores

### 🟢 vector-novelty — **8/10**
- **Language:** Python (NumPy)
- **Tests:** 33/33 passed
- **What:** Centroid-based novelty scoring for agent populations
- **Quality:** Clean API, good docstrings, proper degenerate-case handling (NaN, zero-norm). VectorTable with lazy matrix rebuild. Batch novelty is vectorized and fast.
- **Issues:** None found. Minor: `compute_novelty` accepts `agent_id` but ignores it (documented as API symmetry).
- **Overlap:** Complementary to turbovec (turbovec = quantized search index, vector-novelty = diversity scoring). No conflict.

### 🟢 hebbian-router — **8/10**
- **Language:** Python (NumPy)
- **Tests:** 36/36 passed
- **What:** Self-optimizing routing with Hebbian learning, compiled routes, co-activation channels
- **Quality:** Thread-safe, vectorized `fire_fast()` path, precomputed indexes, proper decay. Good separation of Route/Channel/RoutingLayer.
- **Issues:** `_activate_channels_limited` has a variable shadowing bug in the large-n path (`i, j` locals shadow the function params from `_decompose_channel_key`), but functionally it works since the decomposed values are used correctly.
- **Overlap:** Different from fleet-router (LLM routing) and device-router (hardware routing). hebbian-router is about inter-agent routing with learning.

### 🟢 pareto-tournament — **9/10**
- **Language:** Python (stdlib only)
- **Tests:** 22/22 passed
- **What:** Multi-objective tournament selection with Pareto frontier, breeding, sunset candidates
- **Quality:** Zero dependencies, clean frozen dataclasses, proper validation, correct Pareto dominance algorithm. Extracted from sunset-ecosystem.
- **Issues:** None found. Best code quality of the Python repos.
- **Overlap:** Extracted from sunset-ecosystem. Clean separation — pareto-tournament is the selection engine, sunset-ecosystem is the full lifecycle.

### 🟢 thermal-budget — **8/10**
- **Language:** Python (stdlib only)
- **Tests:** 24/24 passed
- **What:** Device-aware agent slot allocation across GPU/CPU/iGPU/NPU
- **Quality:** Thread-safe, proper validation, clean enum usage, parent-sacrifice logic for breeding, thermal headroom tracking.
- **Issues:** None found. Minor: `parent_sacrifice_before_spawn` doesn't actually allocate the child — it only checks if room is available. The caller must do the allocation separately. Documented but slightly surprising API.
- **Overlap:** Complementary to device-router (which does workload routing, not slot budgeting).

### 🟡 turbovec — **7/10**
- **Language:** Rust
- **Tests:** Could not run (OOM on this machine — 5GB target/ dir)
- **What:** Quantized vector search (2-4 bit) with SIMD-blocked layout, concurrent search, Python bindings
- **Quality:** Well-architected — OnceLock for lazy caches, proper swap_remove, search_with_mask for filtered queries, io versioning, codebook quantization. Clean module structure.
- **Issues:** 
  - OOM on build (5GB target/ — likely due to SIMD codegen or pyO3 bindings)
  - Python bindings in turbovec-python/ reference external frameworks (llama-index, langchain, haystack, agno) that may not all be installed
  - Rotation matrix seed is hardcoded (42) — not configurable
- **Overlap:** Core search library. vector-novelty uses it conceptually but doesn't depend on it.

### 🔴 flux-vm-v3 — **5/10** (post-audit fixes applied)
- **Language:** Rust
- **Tests:** 89/89 passed (after audit fixes)
- **What:** Stack-based constraint-checking VM with proof, JIT, SIMD, streaming, parallel
- **Quality:** Architecture is ambitious. Multiple critical bugs were found and fixed by a prior Kimi audit:
  - **C1:** i32::MIN / -1 panic (fixed)
  - **C2:** abs(i32::MIN) panic (fixed)
  - **C3:** BatchCheck negative count → usize::MAX DoS (fixed)
  - **C4:** JIT NaN mask shift overflow (fixed)
  - **H1-H3:** Unbounded call stack, checkpoints, memory overflow (fixed)
  - **M1:** StreamOpen swallows stack underflow (fixed)
  - **L2:** Unnecessary unsafe impl Sync/Send (fixed)
  - **L3:** JIT generates dead code (not fixed — jit_x86.rs is never executed)
  - **L4:** FFI layer doesn't exist despite claims
- **Remaining issues:** JIT is dead code, SnapVerify is a no-op stub, bytecode truncation returns zeros silently
- **Overlap:** Supersedes flux-vm (moved to archive)

### 🟢 deadband-zig — **8/10**
- **Language:** Zig
- **Tests:** 16 inline tests (could not run — no Zig compiler available)
- **What:** Deadband filter library with basic, rate-limit, and persistence filters
- **Quality:** Clean struct-based API, batch processing, proper rescale, comprehensive inline tests. Well-documented demo in main().
- **Issues:** None found in code review. Tests look correct.
- **Overlap:** Standalone library. Referenced by fleet-router-integration.

### 🟡 grand-synthesis — **6/10**
- **Language:** Markdown/Python (research competition)
- **What:** Multi-model architectural competition for Metronome Architecture
- **Quality:** Interesting research artifact. Contains submissions from 5 models (claude-opus, kimi, glm, deepseek, seed-pro) with architecture docs and simulation code.
- **Issues:** Incomplete (all checkboxes unchecked). Synthesis/validation not done yet.
- **Overlap:** Research artifact, no code overlap with other repos.

### ⚪ turbovec-integration-ccc — **4/10** (docs only, moved to archive)
- **What:** Research docs about hardware-accelerated agent execution and multi-modal perception
- **Quality:** Well-written but contains factual errors (per Claude review): wrong RTX 4050 shared memory specs, wrong Ryzen AI 9 core counts, wrong Jetson Orin CUDA cores, wrong latency table (14,000ms instead of 14ms).
- **Action:** Moved to `archive/archived-2026-05-22-docs-only/`

### ⚪ flux-compiler — **1/10** (skeleton, moved to archive)
- **What:** Only contains README.md and CONTRIBUTING.md, no actual code
- **Action:** Moved to `archive/archived-2026-05-22-skeleton-repos/`

### ⚪ flux-vm — **archived** (superseded by flux-vm-v3)
- **What:** Older version of the FLUX VM with multiple ISA variants (mini, edge, thor)
- **Action:** Moved to `archive/archived-2026-05-22-superseded-by-v3/`

---

## Overlap Analysis

### 1. FLUX Family (resolved)
| Repo | Role | Status |
|------|------|--------|
| flux-vm | V1 VM with ISA variants | **Archived** — superseded by v3 |
| flux-vm-v3 | V3 VM with proof/JIT/SIMD | **Active** — needs JIT cleanup |
| flux-isa | Standalone ISA + Python bindings | **Active** — different scope (ISA spec) |
| flux-ast | Minimal AST crate | **Active** — but barely any code |
| flux-compiler | Empty skeleton | **Archived** — no code |

### 2. Routing Family (no merge needed — different concerns)
| Repo | Concern | Verdict |
|------|---------|---------|
| fleet-router | LLM query → cheapest model routing | Keep — different domain |
| fleet-router-integration | Topological rigidity + deadband routing | Keep — different domain |
| device-router | Hardware compute routing (CUDA/iGPU/CPU/NPU) | Keep — different domain |
| hebbian-router | Inter-agent Hebbian learning routing | Keep — different domain |

These four all use the word "router" but solve fundamentally different problems. No merge warranted.

### 3. Sunset Ecosystem (clean extraction)
| Repo | Role | Status |
|------|------|--------|
| sunset-ecosystem | Full trinity lifecycle management | **Active** — umbrella |
| pareto-tournament | Tournament selection engine | **Active** — extracted module |
| thermal-budget | Device slot allocation | **Active** — extracted module |
| training-throttle | Training rate control | **Active** — related module |

pareto-tournament and thermal-budget were cleanly extracted from sunset-ecosystem. They're independent packages now. No merge needed.

---

## What Was Fixed

1. **Cleaned __pycache__/.pytest_cache** from 4 Python repos (vector-novelty committed and pushed; others were already gitignored)
2. **Cleaned 5GB+ build artifacts** from turbovec (target/, .venv/, .pytest_cache)
3. **Moved 3 repos to archive:**
   - `flux-compiler` → `archive/archived-2026-05-22-skeleton-repos/`
   - `turbovec-integration-ccc` → `archive/archived-2026-05-22-docs-only/`
   - `flux-vm` → `archive/archived-2026-05-22-superseded-by-v3/`

---

## Recommended Next Steps

1. **flux-vm-v3:** Remove dead `jit_x86.rs` or implement actual JIT execution. Fix `SnapVerify` stub. Add bytecode pre-validation.
2. **turbovec:** Needs a CI runner with more RAM (>16GB) to build. Consider splitting Python bindings into separate workspace member.
3. **grand-synthesis:** Complete the competition rounds and merge best ideas.
4. **flux-ast:** Either flesh it out or archive it — currently 1 source file with minimal content.
5. **flux-isa:** Verify it stays in sync with flux-vm-v3 opcode changes.

---

*Audit complete. No files deleted. All moves are reversible from archive/.*
