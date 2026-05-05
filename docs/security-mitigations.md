# FLUX Security Mitigations — Engineering Execution Plan

**Date:** 2026-05-04  
**Source:** Mission 1 Attack Surface Analysis (10-agent adversarial swarm)  
**Scope:** 2 P0 (Critical), 3 P1 (High) vulnerabilities  
**Audience:** Engineers implementing fixes. Not a research paper.

---

## Vulnerability Index

| # | Severity | ID | Title | Effort | Sprint |
|---|----------|----|-------|--------|--------|
| 1 | **P0** | SUPPLY-01 | Supply chain compromise via crate dependencies | 3–5 days | 48h |
| 2 | **P0** | VMESC-01 | VM escape via malicious FLUX-C bytecode | 5–7 days | 48h |
| 3 | **P1** | INTOVF-01 | Integer overflow at INT8 boundary (wraparound) | 2–3 days | Week 2 |
| 4 | **P1** | TIMING-01 | Timing side-channel through constraint evaluation order | 3–4 days | Week 2 |
| 5 | **P1** | GALOIS-01 | Galois connection falsification (INT8 representation gap) | 5–10 days | Week 2–3 |

**Execution order:** SUPPLY-01 → VMESC-01 → INTOVF-01 → TIMING-01 → GALOIS-01

---

## P0-1: Supply Chain Compromise (SUPPLY-01)

### Summary

FLUX's 14 crates pull in 200+ transitive dependencies from crates.io. A single compromised dependency — especially `bitvec`, `half`, or `hashbrown` — can silently alter packing semantics, FP16 conversion, or hash behavior, rendering all 38 formal proofs meaningless. The proofs verify FLUX's code, not its dependencies. This is the highest-probability attack vector with real-world precedent (`event-stream` npm theft, `colors`/`faker` sabotage).

### Mitigation

**Step 1 — Vendor all dependencies immediately.**

```bash
cargo vendor ~/.cargo/vendor-flux --respect-source-config
# Add to .cargo/config.toml:
[source.crates-io]
replace-with = "vendored-sources"
[source.vendored-sources]
directory = "~/.cargo/vendor-flux"
```

This freezes the dependency tree. No `cargo update` can silently pull new versions. Every update now requires explicit human action: download new source, diff against vendored copy, review, replace.

**Step 2 — Eliminate high-risk dependencies with custom replacements.**

Replace `half` with a self-contained FP16 module (~200 lines). FLUX only needs `f16↔f32` conversion and basic comparison — not the full `half` crate API:

```rust
// flux-fp16/src/lib.rs — replace dependency on `half`
#[inline]
pub fn f16_to_f32(bits: u16) -> f32 {
    // IEEE 754 half → single conversion, ~30 lines
    // No external dependencies. Unit test against known values.
    f32::from_bits(/* conversion logic */)
}
```

Replace `bitvec` with inline SIMD intrinsics for the INT8×8 packing hot path:

```rust
// Use core::simd or std::arch directly for pack/unpack
#[cfg(target_arch = "nvptx64")]
#[inline]
pub unsafe fn pack_i8x8(vals: [i8; 8]) -> u64 {
    std::arch::asm!("/* PTX pack */", ...)
}
```

Replace `hashbrown` with a deterministic linear-probe hash map for the small constraint lookup tables FLUX actually uses (~100 entries max). This removes 30+ transitive dependencies.

**Step 3 — Cargo.lock integrity.**

- Commit `Cargo.lock` to the repository with a signed hash.
- CI fails if `cargo verify-lock` detects any drift.
- Add a pre-commit hook that rejects `Cargo.toml` changes without paired `Cargo.lock` updates.

**Step 4 — SBOM and audit trail.**

Run `cargo sbom` (or `cargo cyclonedx`) on every release. Publish the SBOM alongside the release artifacts. Subscribe to RustSec advisories and block known-vulnerable versions in CI:

```yaml
# CI step
- run: cargo audit --deny warnings
```

### Effort

| Task | Time |
|------|------|
| Vendor all deps, verify build | 4 hours |
| Replace `half` with custom FP16 | 1 day |
| Replace `bitvec` with SIMD intrinsics | 1 day |
| Replace `hashbrown` with simple map | 0.5 days |
| CI hardening (lock, audit, SBOM) | 4 hours |
| **Total** | **3–5 days** |

---

## P0-2: VM Escape via Malicious Bytecode (VMESC-01)

### Summary

FLUX-C is not a sandbox — it's an IR translated to PTX/SASS. The opcodes `LD.KERNEL`, `ST.SHARED`, `LD.GLOBAL`, `ATOM.CAS`, and `BRA.WARP` expose raw GPU memory access. An attacker who bypasses the GUARD compiler and submits FLUX-C directly can read/write arbitrary GPU memory, including other tenants' data in multi-tenant cloud environments. The 43-opcode "boundary" is a software convention, not a hardware enforcement.

### Mitigation

**Step 1 — Cryptographic bytecode signing.**

Every FLUX-C binary must carry an Ed25519 signature from a trusted compilation key. The runtime verifies before kernel launch:

```rust
pub fn verify_fluxc_signature(bytecode: &[u8], signature: &Signature) -> Result<(), VmError> {
    let pubkey = load_trusted_key()?; // From HSM or sealed storage
    ed25519_dalek::Verifier::verify(&PublicKey::from(pubkey), bytecode, signature)
        .map_err(|_| VmError::InvalidSignature)?;
    Ok(())
}

// In kernel launch path:
fn launch_constraint_kernel(bytecode: &[u8], sig: &Signature) -> Result<KernelHandle, Error> {
    verify_fluxc_signature(bytecode, sig)?;  // HARD FAIL — no unsigned execution
    let ptx = translate_fluxc_to_ptx(bytecode)?;
    // ... launch
}
```

The signing key must be stored in an HSM (AWS CloudHSM, Azure Key Vault) or hardware-backed keystore. Never in plaintext on disk.

**Step 2 — Bytecode static verifier.**

Before translation to PTX, run a verification pass:

```rust
pub fn verify_bytecode_safety(program: &[Instruction]) -> Result<SafetyReport, VmError> {
    let mut checker = SafetyChecker::new();
    
    for inst in program {
        match inst {
            Instruction::LdGlobal { addr, .. } => {
                // Reject if address is not a bounded offset from a known base
                checker.check_bounded_address(addr)?;
            }
            Instruction::BraWarp { target } => {
                // Reject if target is outside the program's basic blocks
                checker.check_structured_control_flow(target)?;
            }
            Instruction::StShared { addr, value } => {
                // Reject if store address is not within declared shared memory region
                checker.check_shared_bounds(addr)?;
            }
            _ => {}
        }
    }
    
    checker.report()
}
```

This pass must:
- Reject any undefined opcodes (only 43 valid, everything else → hard fail)
- Verify all `LD.GLOBAL`/`ST.GLOBAL` addresses are bounded offsets from registered base pointers
- Verify control flow is structured (no arbitrary jumps, only forward branches within declared basic blocks)
- Reject any program containing raw PTX strings or inline assembly

**Step 3 — Memory bounds enforcement.**

Capability-based addressing for FLUX-C memory ops. Each memory region gets a base+bounds pair:

```rust
struct MemCapability {
    base: u64,      // GPU virtual address
    bounds: u64,    // Size in bytes
    perms: Perms,   // READ | WRITE | EXECUTE
}

// Runtime emits bounds-checked PTX:
// Instead of: ld.global.f32 %f0, [%r_addr]
// Emit:       setp.lt.u64 %p0, %r_offset, BOUNDS
//             @p0 ld.global.f32 %f0, [%r_base + %r_offset]
//             @!p0 trap
```

Every `LD`/`ST` in the translated PTX includes a bounds check. Violation → kernel trap → immediate abort. Cost: 1 extra instruction per memory op (~2% throughput impact).

**Step 4 — Eliminate direct bytecode submission paths.**

- Remove any API endpoint that accepts raw FLUX-C.
- All FLUX-C must be generated server-side by the verified GUARD compiler.
- Input is GUARD source only. Compilation is server-side in a sandboxed process.
- Log all compilation requests with source hash, output hash, and compiler version.

### Effort

| Task | Time |
|------|------|
| Ed25519 signing + verification | 1 day |
| Bytecode static verifier | 2 days |
| Capability-based addressing in PTX emission | 2 days |
| API hardening (remove raw bytecode paths) | 0.5 days |
| Integration testing | 1 day |
| **Total** | **5–7 days** |

---

## P1-1: Integer Overflow at INT8 Boundary (INTOVF-01)

### Summary

GUARD constraints use infinite-precision integers in their abstract semantics. FLUX-C compiles these to INT8×8 packed operations for throughput. When input values exceed the INT8 range (127 signed, 255 unsigned), silent wraparound occurs: 256→0, 262→6, etc. The range analysis that guards this is sound but incomplete — it proves "if in range, correct" but doesn't reject out-of-range inputs. A vehicle speed of 262 km/h wraps to 6, making `ASSERT speed < 250` evaluate to TRUE.

### Mitigation

**Step 1 — Saturating semantics for all INT8 operations.**

```rust
// Replace wrapping arithmetic with saturating
#[inline]
pub fn i8_add_sat(a: i8, b: i8) -> i8 {
    a.saturating_add(b)
}

// GPU kernel variant using PTX saturating add:
// add.sat.s32 %r0, %r1, %r2  ; saturating add, then truncate to i8
```

This prevents wraparound. Cost: negligible (PTX has native `.sat` modifier).

**Step 2 — Range guard opcode (pre-check before packed evaluation).**

Add a new FLUX-C verification path:

```rust
// Before INT8 packed evaluation, emit a range check kernel
// This runs as a fast-filter: if any input is out of range, fall back to 32-bit path
fn emit_range_guard(inputs: &[ConstraintInput]) -> Option<KernelPath> {
    let out_of_range = inputs.iter().any(|i| i.value < i.min || i.value > i.max);
    if out_of_range {
        Some(KernelPath::Fallback32Bit)  // Safe but slower (~11B/sec vs 90B/sec)
    } else {
        Some(KernelPath::FastInt8)       // Full speed
    }
}
```

This is a two-path approach: INT8 fast path for in-range inputs, INT32 fallback for out-of-range. The headline benchmark becomes "90.2B/sec for in-range inputs, 11B/sec for edge cases."

**Step 3 — Shadow assertions for safety-critical deployments.**

For deployments where correctness is non-negotiable (medical, automotive, aerospace), emit dual kernels:

```
Primary:   INT8×8 packed kernel (fast)
Shadow:    INT32 scalar kernel (verified, slow)
Comparator: Assert primary_result == shadow_result
```

Divergence → immediate safety shutdown + alert. This is aerospace-standard dissimilar redundancy.

### Effort

| Task | Time |
|------|------|
| Saturating arithmetic in PTX emission | 0.5 days |
| Range guard + dual-path kernel launch | 1.5 days |
| Shadow assertion framework | 1 day |
| Testing with boundary values | 0.5 days |
| **Total** | **2–3 days** |

---

## P1-2: Timing Side-Channel (TIMING-01)

### Summary

FLUX-C's short-circuiting operators (`AND.SC`, `OR.SC`) skip evaluation when the result is determined early. This creates measurable timing variation: 3–8% at warp level, up to 23% at kernel level. In security-sensitive constraints (e.g., `auth_valid AND operation_permitted`), failed auth is faster than valid auth (because the second operand is skipped). An attacker with GPU timing access (performance counters, CUDA events, or co-resident SM interference) can distinguish constraint evaluation paths and extract secrets.

### Mitigation

**Step 1 — `STRICT_EVAL` compilation mode.**

```rust
#[derive(Clone, Copy)]
enum EvalMode {
    ShortCircuit,  // Current behavior — fast but leaky
    StrictEval,    // Always evaluate all operands
}

// In compiler:
fn compile_and(lhs: Expr, rhs: Expr, mode: EvalMode) -> Vec<Instruction> {
    match mode {
        EvalMode::ShortCircuit => {
            // Branch: if lhs is false, skip rhs
            vec![compile(lhs), BraIfFalse(skip_label), compile(rhs), Label(skip_label)]
        }
        EvalMode::StrictEval => {
            // Evaluate both, combine with bitwise AND (constant-time)
            vec![
                compile(lhs), Store(temp_a),
                compile(rhs), Store(temp_b),
                And(temp_a, temp_b),  // No branch — constant time
            ]
        }
    }
}
```

Security-critical constraints must use `STRICT_EVAL`. Performance cost: ~15–20%. Acceptable for auth/security paths.

**Step 2 — Constant-time comparison primitives.**

```rust
// GPU constant-time INT8 comparison
// Always executes both branches, selects result via SEL instruction
fn emit_consttime_cmp(lhs: Reg, rhs: Reg, op: CmpOp) -> Vec<PtxInst> {
    vec![
        // Compute both paths
        setp.lt.s32 %p_lt, %lhs, %rhs,   // lhs < rhs?
        setp.eq.s32 %p_eq, %lhs, %rhs,   // lhs == rhs?
        sel.b32 %result_lt, 1, 0, %p_lt,  // materialize bool
        sel.b32 %result_eq, 1, 0, %p_eq,
        // Select based on requested op
        // No early exit — both comparisons always execute
    ]
}
```

**Step 3 — SM isolation for multi-tenant deployments.**

Document and enforce: FLUX security-critical kernels must run on dedicated SMs. On NVIDIA A100/H100, use MIG partitioning. On consumer GPUs: FLUX must not be used in multi-tenant security-sensitive contexts. This is a deployment constraint, not a code fix.

**Step 4 — Optional noise injection for defense-in-depth.**

```rust
// Add random NOP padding to equalize worst-case timing
fn emit_noise_padded(rng_seed: u64) -> Vec<PtxInst> {
    let delay = xorshift64(rng_seed) % MAX_PAD_CYCLES;
    vec![/* NOP loop for `delay` iterations */]
}
```

Seed is per-kernel-launch, never exposed. This is a secondary defense, not primary.

### Effort

| Task | Time |
|------|------|
| `STRICT_EVAL` mode in compiler | 1 day |
| Constant-time comparison primitives | 1 day |
| SM isolation documentation + config | 0.5 days |
| Noise injection (optional) | 0.5 days |
| Timing measurement test suite | 1 day |
| **Total** | **3–4 days** |

---

## P1-3: Galois Connection Falsification (GALOIS-01)

### Summary

The proven Galois connection between GUARD (abstract domain, ℤ) and FLUX-C (concrete domain, ℤ/256ℤ) has a modeling error. The abstraction function `α: ℤ → ℤ/256ℤ` is lossy — values outside [-128, 127] are truncated. The adjunction equation `a ≤ G(F(a))` fails for values like 255: `α(255) = -1`, `γ(-1) = -1 ≠ 255`. The counterexample `n + 1 > n` is true in ℤ but false at INT8 boundary (255 + 1 wraps to 0). The proof is correct relative to an incomplete model.

This is the hardest fix because it's not a bug — it's a fundamental limitation of the INT8 representation. The fix requires formal acknowledgment of the gap and an architecture that keeps constraints within the proven-safe fragment.

### Mitigation

**Step 1 — Define and enforce the "safe fragment."**

```rust
/// The subset of GUARD where the Galois connection provably holds.
/// Variables must be in [INT8_MIN, INT8_MAX], operations must be closed.
struct SafeFragment {
    /// For each variable: proven bounds from range analysis
    var_bounds: HashMap<VarId, (i8, i8)>,
    /// For each operation: verified that no intermediate exceeds INT8
    operation_closures: Vec<OperationProof>,
}

impl SafeFragment {
    fn check_constraint(&self, c: &GuardConstraint) -> Result<SafeFragmentCert, FragmentError> {
        // 1. Verify all variables have bounds within [-128, 127]
        // 2. Verify all arithmetic ops are closed (no overflow possible)
        // 3. Verify no unbounded iteration
        // 4. Verify no FP16 paths for values near ±2048
        // If all checks pass → emit certificate
    }
}
```

Constraints that fail the safe fragment check are either:
- Rejected (hard failure), or
- Compiled with INT32/INT64 fallback (correct but slower)

**Step 2 — Soundiness certificate per compilation.**

Every compiled FLUX-C program includes a machine-checkable certificate:

```json
{
  "source_hash": "sha256:abc123...",
  "compiler_version": "fluxc-2.1.0",
  "safe_fragment": {
    "vars": {
      "speed": {"min": 0, "max": 200, "fits_i8": true},
      "temperature": {"min": -40, "max": 85, "fits_i8": true}
    },
    "all_ops_closed": true,
    "fallback_used": false,
    "galois_proven": true
  },
  "signature": "ed25519:..."
}
```

Users can independently verify: does this program stay within the proven-safe fragment?

**Step 3 — Extend the abstract domain.**

Long-term fix: the formal model must include modular arithmetic semantics. The Galois connection should be proven over `ℤ/256ℤ` (matching the concrete domain) rather than `ℤ` (which doesn't match). This requires:

1. Redefine the abstract domain to track both the mathematical value and its INT8 representation.
2. Prove the adjunction over the *representation* domain, not the mathematical domain.
3. Explicitly model overflow: `α(n) = n mod 256`, `γ(b) = {n ∈ ℤ | n mod 256 = b}` (a set of integers, not a single integer).

This is a research-level fix. The safe fragment is the practical engineering fix for now.

**Step 4 — Honest proof framing.**

Update all documentation, papers, and marketing to state:

> The Galois connection is proven for the *safe fragment* of GUARD: variables bounded to [-128, 127], operations verified closed under INT8 arithmetic. The proof does not cover out-of-range inputs, hardware errors, timing behavior, or compiler correctness. These are separate guarantees requiring separate proofs.

This is not weakness — it's intellectual honesty that increases trust.

### Effort

| Task | Time |
|------|------|
| Safe fragment checker implementation | 2–3 days |
| Soundiness certificate emission | 1–2 days |
| INT32 fallback path | 1 day |
| Integration with compiler pipeline | 1 day |
| Extended abstract domain (research) | 5–10 days (separate track) |
| **Total (engineering)** | **5–7 days** |
| **Total (research)** | **10–15 days** |

---

## Security Hardening Sprint — Next 48 Hours

### Goal

Neutralize both P0s to the point where they require active, sophisticated exploitation rather than opportunistic attack.

### Day 1 (Hours 0–24)

| Hour | Task | Owner | Deliverable |
|------|------|-------|-------------|
| 0–2 | Vendor all dependencies, pin Cargo.lock | Build eng | Vendored deps, CI green |
| 2–4 | `cargo audit` + RustSec integration | Build eng | CI gate blocking vulnerable deps |
| 4–8 | Replace `half` crate with custom FP16 module | Core eng | `flux-fp16` crate, all tests passing |
| 8–12 | Implement bytecode signing (Ed25519) | Runtime eng | `sign_fluxc` and `verify_fluxc` commands |
| 12–16 | Implement bytecode static verifier (bounds, opcodes, control flow) | Runtime eng | `verify_bytecode_safety()` passing on all existing programs |
| 16–20 | Wire signing + verification into kernel launch path | Runtime eng | Unsigned bytecode → hard fail |
| 20–24 | Integration test: signed path works, unsigned path blocked | QA | Test report |

### Day 2 (Hours 24–48)

| Hour | Task | Owner | Deliverable |
|------|------|-------|-------------|
| 24–28 | Replace `bitvec` with SIMD intrinsics for INT8×8 pack | Core eng | SIMD pack/unpack, perf parity |
| 28–32 | Capability-based addressing in PTX emission | Runtime eng | Bounds-checked LD/ST, 2% perf overhead verified |
| 32–36 | Remove all API endpoints accepting raw FLUX-C | API eng | GUARD-only input path |
| 36–40 | Smoke test full pipeline: GUARD → signed FLUX-C → verified launch | QA | End-to-end green |
| 40–44 | SBOM generation, publish for current release | Build eng | `sbom.json` artifact |
| 44–48 | Sprint review: verify both P0s mitigated, write regression tests | All | Regression test suite |

### Success Criteria

After 48 hours:

1. **No unsigned FLUX-C executes anywhere.** Every kernel launch requires a valid Ed25519 signature from the trusted compilation key.
2. **No dependency updates without explicit review.** Vendored deps, pinned Cargo.lock, CI enforcement.
3. **`half` and `bitvec` removed from the dependency tree.** Custom replacements in-place, tests passing.
4. **Bytecode static verifier blocks** out-of-bounds memory access, undefined opcodes, and unstructured control flow.
5. **SBOM published** for the hardened release.

### What's NOT Done in 48 Hours

- P1 mitigations (INTOVF-01, TIMING-01, GALOIS-01) — scheduled for Week 2
- Extended abstract domain research (GALOIS-01 long-term) — scheduled for Week 3–4
- SM isolation / MIG configuration (TIMING-01 deployment) — requires infra work
- Shadow assertion framework (INTOVF-01 safety-critical) — Week 2

---

## Appendix: Dependency Removal Tracker

| Crate | Replacement | Status | Risk |
|-------|------------|--------|------|
| `half` | Custom `flux-fp16` (200 LOC) | Sprint Day 1 | Low — only need f16↔f32 |
| `bitvec` | SIMD intrinsics + inline bit ops | Sprint Day 2 | Medium — hot path, must match perf |
| `hashbrown` | Simple linear-probe HashMap | Sprint Day 2 | Low — small tables only |
| `syn`/`quote` | Keep (proc-macro only, not runtime) | No change | Low — build-time only |
| `libc`/`cc` | Keep (GPU FFI required) | No change | Medium — audit CC flags |

---

*Document generated by Forgemaster ⚒️ — For engineering execution, not academic discussion.*
