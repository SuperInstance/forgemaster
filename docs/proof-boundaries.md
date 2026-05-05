# FLUX Proof Boundaries — What is Verified vs. What is Assumed

**Document Purpose:** Required for DO-330 Tool Qualification Evidence (TOR-4: Tool Verification)
**Date:** 2026-05-05
**Author:** Forgemaster ⚒️, informed by 100-agent Kimi swarm adversarial analysis

---

## Statement of Scope

FLUX has 38 formal proofs (30 English + 8 Coq) that establish mathematical properties of the constraint compilation and verification system. This document explicitly states what these proofs cover and what they do not.

**Critical for certification:** Any gap between "proven" and "assumed" is a safety claim that requires independent verification.

---

## What the 38 Proofs Cover (Verified)

### Compiler Correctness
- **Galois connection F ⊣ G** between GUARD source and FLUX-C bytecode
- Forward compilation F preserves ALL safety constraints in the abstract domain
- Backward decompilation G recovers the abstract meaning from bytecode
- This is stronger than bisimulation — it's an adjunction

### VM Properties
- **Safety confluence:** All 4 VM properties (determinism, termination, safety monotonicity, composability) compose correctly
- **Timing side-channel freedom:** WCET bounds hold for all execution paths through the 43-opcode FLUX-C subset
- **Score preservation:** Constraint evaluation scores are preserved across compilation

### Algorithm Correctness
- **AC-3 termination:** Arc consistency algorithm terminates on all finite constraint graphs
- **Bitmask functor:** FinSet → BoolAlg is fully faithful (proves N-Queens optimization)
- **P2 invariant:** Second-order invariant holds across all resolution steps
- **INT8 differential correctness:** For values 0-255, GPU and CPU produce identical results (10M+ inputs tested)

---

## What the 38 Proofs DO NOT Cover (Assumed)

### 1. INT8 Boundary Behavior (Representation Gap)
**Status:** UNVERIFIED at boundaries

The Galois connection proof operates in the abstract domain of ℤ (integers). The concrete implementation operates in ℤ/256ℤ (modular 8-bit arithmetic). The proof assumes that:
- All constraint values fit within [0, 255]
- No wraparound occurs during compilation or evaluation
- The representation function `γ: concrete → abstract` is total and well-defined

**Gap:** Values near 255 that wrap to 0 are indistinguishable from legitimate zero values in the concrete domain. The abstract proof cannot detect this.

**Mitigation (required):**
- Compile-time range analysis that rejects constraints with bounds > 255
- Runtime saturation semantics (255 is max, values > 255 clamp to 255)
- Shadow assertions in 32-bit for boundary cases
- Explicit documentation: "FLUX-C guarantees correctness for values in [0, 254] only"

### 2. Compiler Dependency Chain (Supply Chain)
**Status:** UNVERIFIED

The proofs verify the mathematical model of compilation. They do not verify that the Rust implementation matches the model. The implementation depends on:
- 14 crates.io crates (direct dependencies)
- ~200 transitive dependencies
- Rust compiler (rustc 1.75+)
- LLVM backend
- OS-level memory safety (Linux kernel, WSL2)

**Gap:** A compromised dependency, compiler bug, or OS-level vulnerability can bypass all proofs without detection.

**Mitigation (required):**
- Vendor and pin all direct dependencies
- Audit critical path dependencies (bitvec, half, hashbrown)
- Build reproducibility verification
- Consider formally verified compiler (future: Rust → Vellvm path)

### 3. GPU Execution Correctness (Hardware Gap)
**Status:** PARTIALLY VERIFIED (empirical only)

The 30 GPU experiments with zero differential mismatches provide strong empirical evidence. However:
- No formal model of GPU execution exists
- CUDA compiler (nvcc) is not formally verified
- GPU hardware may have undocumented behaviors (e.g., Titan X ECC bug)
- WSL2 virtualization layer may affect timing/reproducibility

**Gap:** The proofs cover the mathematical model, not the physical GPU execution.

**Mitigation (required):**
- Differential testing framework (CPU reference vs GPU) — ongoing
- Periodic re-verification with updated drivers
- Target certified GPU hardware (NVIDIA A100 with ECC, not RTX 4050)
- Document: "GPU verification is empirical, not formal"

### 4. Runtime Environment (OS/Hardware Gap)
**Status:** UNVERIFIED

The proofs assume a correct execution environment:
- Memory is not corrupted (cosmic rays, Rowhammer, bit flips)
- Timing is deterministic (no DVFS throttling, no thermal throttling)
- I/O is correct (sensor values are authentic, not spoofed)

**Gap:** No proof addresses physical-world attacks on the execution environment.

**Mitigation (required):**
- ECC memory for production deployments
- Temperature monitoring and thermal throttling detection
- Sensor authentication (cryptographic signing of sensor values)
- Watchdog timer with independent clock

### 5. Bytecode Authenticity (Trust Chain Gap)
**Status:** UNVERIFIED

The Galois connection proves that correct compilation preserves safety. It does not prove that the bytecode being executed was produced by the compiler.

**Gap:** An attacker who injects arbitrary FLUX-C bytecode bypasses all proofs. The 43-opcode VM is not a sandbox — certain opcode combinations (LD/ST to shared memory + warp-level branching) can escape the constraint evaluation abstraction.

**Mitigation (required):**
- Cryptographic signing of compiled FLUX-C bytecode (Ed25519)
- Bytecode static verifier (bounds checking, opcode validation, control flow analysis)
- Load-time integrity check before GPU upload

---

## Proof Boundary Summary Table

| Boundary | Verified? | Evidence | Gap | Mitigation Status |
|----------|-----------|----------|-----|-------------------|
| Abstract→Abstract compilation | ✅ Yes | Galois connection proof | None | Complete |
| Abstract→Concrete representation | ⚠️ Partial | INT8 differential tests (0-255) | Wraparound at boundaries | **Needs work** |
| Compiler implementation | ❌ No | Rust type safety, tests | Dependency chain | **Needs work** |
| GPU execution | ⚠️ Empirical | 30 experiments, 10M+ inputs | No formal GPU model | **Needs work** |
| Runtime environment | ❌ No | Assumes correct hardware | Physical attacks | **Needs work** |
| Bytecode authenticity | ❌ No | Assumes compiler output | Injection attacks | **Needs work** |
| Sensor input validity | ❌ No | Assumes authentic data | Spoofing | Out of scope |

---

## Certification Implications

For DO-330 TQL1 qualification, each gap requires:
1. **Explicit statement** in the Tool Qualification Plan (what is assumed)
2. **Independent verification** of the assumption (test, analysis, or inspection)
3. **Residual risk acceptance** by the certification authority

The representation gap (boundary #1) is the most critical because it directly undermines the headline safety claim. The swarm's adversarial analysis showed that a single CAN frame can cause INT8 wraparound that silently bypasses a speed constraint.

**Recommended priority:** Representation gap > Bytecode authenticity > Supply chain > GPU execution > Runtime

---

## Revision History
- **v1.0** (2026-05-05) — Initial document from swarm adversarial analysis
- Next: Add formal model gap analysis, vendor dependency audit, bytecode verifier design
