# Contributing to FLUX

Thank you for your interest in contributing to FLUX — a safety-critical constraint compilation system targeting GPU and FPGA pipelines. Whether you're fixing a typo, writing differential tests for GPU kernels, or proposing changes to the GUARD language spec, this document has you covered.

> **Safety note:** Several crates in this repository target aviation, marine, and autonomous-system domains where incorrect code can have real consequences. Please read [Safety-Critical Coding Guidelines](#11-safety-critical-coding-guidelines) before touching any crate marked `safety-critical`.

---

## Table of Contents

1. [Code of Conduct](#1-code-of-conduct)
2. [How to Contribute](#2-how-to-contribute)
3. [Development Setup](#3-development-setup)
4. [Code Style](#4-code-style)
5. [Commit Message Format](#5-commit-message-format)
6. [Pull Request Review Process](#6-pull-request-review-process)
7. [Testing Requirements](#7-testing-requirements)
8. [Documentation Requirements](#8-documentation-requirements)
9. [Release Process](#9-release-process)
10. [Architecture Overview](#10-architecture-overview)
11. [Safety-Critical Coding Guidelines](#11-safety-critical-coding-guidelines)
12. [License and CLA](#12-license-and-cla)

---

## 1. Code of Conduct

FLUX follows the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

### Our Pledge

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, color, religion, or sexual identity and orientation.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the project maintainers at **conduct@superinstance.com**. All complaints will be reviewed and investigated promptly and fairly.

Enforcement follows the standard Contributor Covenant graduated response: correction → warning → temporary ban → permanent ban.

---

## 2. How to Contribute

### Bug Reports

Before filing a bug, search [existing issues](https://github.com/SuperInstance/forgemaster/issues) to avoid duplicates.

A good bug report includes:

```
**FLUX version / crate + version:**
**Rust toolchain:** (output of `rustup show`)
**OS / target triple:**
**Minimal reproducer:**
**Expected behavior:**
**Actual behavior:**
**Backtrace (RUST_BACKTRACE=1):**
```

For bugs in safety-critical crates (`guardc`, `flux-verify-api`, `flux-isa-*`), prefix the issue title with `[SAFETY]` — these are triaged within 48 hours.

### Feature Requests

Open a [GitHub Discussion](https://github.com/SuperInstance/forgemaster/discussions) before filing a feature issue. This lets the community validate the direction before anyone writes code.

For substantial changes (new ISA instructions, compiler passes, hardware targets), write an RFC in `docs/rfcs/` and open a PR for review. See `docs/rfcs/0000-template.md` for the format.

### Pull Requests

1. **Fork** the repository and create a branch from `master`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Link your PR** to the relevant issue using `Closes #123` in the PR description.

3. **Keep PRs focused.** One logical change per PR. Refactors and feature additions should be separate PRs.

4. **Don't mix** formatting-only commits with logic changes — reviewers need to see the diff clearly.

5. **Safety-critical PRs** require the checklist in `.github/PULL_REQUEST_TEMPLATE_SAFETY.md` to be completed in full.

---

## 3. Development Setup

### Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| Rust | **1.75** | `rustup update stable` |
| cargo | comes with Rust | — |
| rustfmt | stable channel | `rustup component add rustfmt` |
| clippy | stable channel | `rustup component add clippy` |
| CUDA Toolkit | 12.x (optional, GPU crates only) | [developer.nvidia.com](https://developer.nvidia.com/cuda-toolkit) |
| cargo-insta | latest | `cargo install cargo-insta` |
| cargo-deny | latest | `cargo install cargo-deny` |

### Clone and Build

```bash
git clone https://github.com/SuperInstance/forgemaster.git
cd forgemaster

# Build the full workspace
cargo build --workspace

# Build a specific crate
cargo build -p guardc

# Build with all features
cargo build --workspace --all-features
```

### Workspace Layout

```
forgemaster/
├── flux-isa/                  # Core ISA bytecode definitions
├── flux-isa-std/              # Standard instruction profile
├── flux-isa-mini/             # Embedded/minimal instruction profile
├── flux-isa-edge/             # Edge-optimised instruction profile
├── flux-isa-thor/             # High-performance THOR profile
├── flux-ast/                  # GUARD language AST
├── flux-provenance/           # Compilation provenance tracking
├── flux-hardware/
│   ├── bridge/                # GPU/FPGA bridge layer (flux-bridge)
│   └── hdc/flux-hdc-rust/    # Hyperdimensional computing runtime
├── flux-compiler-workspace/   # Full compiler pipeline (fluxc-*)
├── flux-verify-api/           # Formal verification interface
├── guardc/                    # GUARD → FLUX-C verified compiler
├── guard2mask/                # Guard condition → bitmask lowering
├── cocapn-glue-core/          # CoCAPN protocol integration
└── docs/                      # RFCs, specs, architecture docs
```

### Running Tests

```bash
# All tests
cargo test --workspace

# Single crate
cargo test -p flux-isa

# With output for failing tests
cargo test --workspace -- --nocapture

# GPU kernel tests (requires CUDA device)
cargo test --workspace --features cuda -- --test-threads=1
```

### Checking Dependency Licenses and Advisories

```bash
cargo deny check
```

---

## 4. Code Style

### rustfmt

All code must be formatted with `rustfmt` before committing. The workspace uses the default stable configuration.

```bash
# Format everything
cargo fmt --all

# Check without modifying (CI does this)
cargo fmt --all -- --check
```

Do not add a custom `rustfmt.toml` to individual crates without discussion — workspace-wide consistency is preferred.

### clippy

All clippy lints must pass at the `deny(warnings)` level:

```bash
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

For lint suppressions that are genuinely necessary, add a `#[allow(...)]` attribute with an explanatory comment:

```rust
// ALLOW: sha2 requires this layout for zero-copy hashing
#[allow(clippy::large_stack_arrays)]
const PADDING: [u8; 64] = [0u8; 64];
```

Never use `#![allow(warnings)]` at the crate root.

### No `unsafe` in Safety-Critical Crates

The following crates must contain **zero `unsafe` blocks**:

- `guardc`
- `flux-verify-api`
- `flux-isa` (core definitions)
- `flux-isa-std`
- `flux-isa-mini`
- `flux-isa-edge`
- `flux-isa-thor`
- `flux-provenance`

CI enforces this with `cargo geiger`. If a dependency introduces `unsafe`, open an issue before accepting it.

`unsafe` is permitted in `flux-bridge`, `flux-hdc`, and the CUDA codegen crates, but every `unsafe` block must carry a `// SAFETY:` comment explaining the invariant being upheld:

```rust
// SAFETY: ptr is aligned to T's alignment and points into a live CUDA allocation
// whose lifetime is tied to `self.buffer` which outlives this reference.
let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
```

### Naming Conventions

- Types and traits: `UpperCamelCase`
- Functions, methods, variables: `snake_case`
- Constants and statics: `SCREAMING_SNAKE_CASE`
- ISA opcodes: `UpperCamelCase` with an `Op` prefix (e.g., `OpPush`, `OpConstraint`)

---

## 5. Commit Message Format

FLUX uses [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

### Format

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

### Types

| Type | Use for |
|------|---------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `perf` | Performance improvement (no behavior change) |
| `refactor` | Code restructuring (no behavior change) |
| `test` | Adding or fixing tests |
| `docs` | Documentation only |
| `chore` | Build system, CI, tooling |
| `safety` | Safety-critical change — **always requires body** |

### Scopes

Use the crate name as scope: `flux-isa`, `guardc`, `flux-bridge`, `flux-verify-api`, etc. For cross-crate changes, use `workspace`.

### Examples

```
feat(guardc): add constraint negation lowering pass

Implements the logical NOT operator for guard conditions, lowering
`!expr` to its De Morgan equivalent at the FLUX-C IR level.

Closes #47
```

```
safety(flux-isa-std): restrict LOAD instruction to aligned addresses

MISRA-C:2012 Rule 11.3 prohibits casts between pointer types with
differing alignment requirements. This change adds an alignment check
to the LOAD opcode handler.

SAFETY-REVIEW: required before merge
Closes #112
```

```
fix(flux-bridge): correct CUDA stream synchronisation ordering

Stream S1 was being released before the kernel on S2 that consumed
its output had completed. Adds explicit cudaStreamWaitEvent barrier.
```

### Breaking Changes

Append `!` after the type/scope and add a `BREAKING CHANGE:` footer:

```
feat(flux-isa)!: rename OpJmpIf to OpBranchIf

BREAKING CHANGE: All downstream assemblers and disassemblers referencing
OpJmpIf must be updated to OpBranchIf. Bytecode encoding is unchanged.
```

---

## 6. Pull Request Review Process

### Standard PRs (non-safety-critical)

- **1 approving review** from a core maintainer required
- CI must be green: `cargo fmt`, `cargo clippy`, `cargo test`, `cargo deny`
- Reviewer has 5 business days to respond before the author may ping again

### Safety-Critical PRs

Any PR touching a crate marked `safety-critical` (see §4) or changing compiler semantics that affect generated FLUX bytecode **requires**:

- **2 approving reviews**, at least one from the `@flux/safety-reviewers` team
- The completed safety checklist in the PR description (`.github/PULL_REQUEST_TEMPLATE_SAFETY.md`)
- Traceability comment linking to the requirement or specification section being satisfied
- No unresolved review comments at merge time

Safety PRs should not be merged by the author, even if they have merge access.

### Review Etiquette

- Use **[NIT]** for optional style suggestions that should not block merge
- Use **[MUST]** for blocking issues
- Use **[QUESTION]** for clarifying questions that don't block but deserve discussion
- Prefer suggesting specific code via GitHub's suggestion feature over vague requests

### Merging

We use **squash merges** for feature branches to keep `master` history readable. Commit the squashed message in Conventional Commits format. For long-running branches (RFCs, large features), a merge commit is used to preserve the branch history — request this explicitly in the PR.

---

## 7. Testing Requirements

### Unit and Integration Tests

Every PR must include tests that cover new behavior. Aim for tests at the lowest level that meaningfully validates the change:

```bash
# Run all tests with coverage report (requires cargo-llvm-cov)
cargo llvm-cov --workspace --lcov --output-path lcov.info

# Open HTML report
cargo llvm-cov --workspace --open
```

Minimum coverage for new code in core crates (`flux-isa`, `guardc`, `flux-ast`): **80%** line coverage.

### Snapshot Tests

`guardc` and `flux-ast` use [insta](https://insta.rs) for snapshot testing of compiler output:

```bash
# Run and review new/changed snapshots
cargo insta test --workspace
cargo insta review
```

When adding a new compiler pass, add a snapshot test that captures the before/after IR. Snapshot files live alongside tests in `src/tests/snapshots/`.

### Differential Testing for GPU Kernels

GPU kernel changes in `flux-bridge` and `constraint-theory-core-cuda` require differential tests that compare output against a reference CPU implementation:

```rust
#[cfg(test)]
mod differential {
    use super::*;

    /// Differential test: GPU result must match CPU reference within tolerance.
    ///
    /// # Panics
    /// Panics if max absolute difference between GPU and CPU outputs exceeds
    /// `TOLERANCE` for any element in the test vector.
    #[test]
    #[cfg(feature = "cuda")]
    fn kernel_output_matches_cpu_reference() {
        let inputs = generate_test_vectors(SEED, 1024);
        let cpu_out = cpu_reference_impl(&inputs);
        let gpu_out = gpu_kernel_impl(&inputs).unwrap();
        assert_outputs_within_tolerance(&cpu_out, &gpu_out, TOLERANCE);
    }
}
```

For non-deterministic kernels (e.g., reduction with floating-point reassociation), document the expected tolerance in a `// TOLERANCE:` comment explaining the ULP budget.

### Property-Based Tests

For constraint solving and ISA encode/decode round-trips, use [proptest](https://proptest-rs.github.io/proptest/):

```rust
proptest! {
    #[test]
    fn encode_decode_roundtrip(opcode in any::<Opcode>(), operand in 0u32..=0xFFFF) {
        let encoded = opcode.encode(operand);
        let (decoded_op, decoded_operand) = Opcode::decode(encoded).unwrap();
        prop_assert_eq!(opcode, decoded_op);
        prop_assert_eq!(operand, decoded_operand);
    }
}
```

### Running the Full CI Suite Locally

```bash
# Mirrors what CI runs
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
cargo deny check
cargo doc --workspace --no-deps 2>&1 | grep -E "^error" && exit 1 || true
```

---

## 8. Documentation Requirements

### rustdoc

Every public item in every crate must have a rustdoc comment. CI fails on missing docs:

```bash
RUSTDOCFLAGS="-D missing_docs" cargo doc --workspace --no-deps
```

Minimum doc comment structure for functions:

```rust
/// Lowers a GUARD constraint expression to FLUX-C IR instructions.
///
/// # Arguments
///
/// * `expr` — the parsed constraint AST node
/// * `ctx` — mutable lowering context carrying the current basic block
///
/// # Returns
///
/// Returns the `IrValue` representing the lowered expression, or a
/// [`LowerError`] describing why lowering failed.
///
/// # Errors
///
/// Returns [`LowerError::UnsupportedExpr`] if `expr` contains a language
/// construct not yet implemented in the lowering pass.
pub fn lower_expr(expr: &Expr, ctx: &mut LowerCtx) -> Result<IrValue, LowerError> {
```

### Safety Properties

For any function that imposes invariants on callers or relies on them from callees, add a `# Safety` section (even in safe Rust, when the function is part of a safety-critical path):

```rust
/// Emits a FLUX-C STORE instruction for a memory-mapped FPGA register.
///
/// # Safety Properties
///
/// - The `addr` must be 4-byte aligned (hardware requirement, DO-254 §4.3.2)
/// - The caller is responsible for ensuring `addr` is within the MMIO window
///   declared in the hardware configuration manifest before calling this
///   function. Writes outside this range have undefined hardware behavior.
pub fn emit_mmio_store(addr: u32, value: u32, ctx: &mut CodegenCtx) {
```

### Inline Comments

Prefer self-documenting code. Add inline comments only where the logic is non-obvious or where a specific standard/specification section justifies a decision:

```rust
// Constraint propagation follows AC-3 algorithm (Mackworth 1977).
// We use a VecDeque as the worklist to get FIFO ordering, which gives
// better empirical performance on structured CSPs than LIFO (stack).
let mut worklist: VecDeque<Arc> = all_arcs(csp).collect();
```

Avoid comments that restate what the code does:

```rust
// BAD: increments i
i += 1;

// GOOD: skip the sentinel byte at the start of each FLUX-C frame
i += 1;
```

### CHANGELOG

Maintain `CHANGELOG.md` per crate in [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format. The `[Unreleased]` section is updated with each merged PR. Maintainers promote it to a version entry at release time.

---

## 9. Release Process

### Version Policy

FLUX crates follow [Semantic Versioning 2.0.0](https://semver.org/). While in `0.x`, breaking changes may appear in minor releases; document them clearly in the `CHANGELOG.md` and `BREAKING CHANGE:` commit footer.

### Bumping Versions

1. Update `version` in the affected crate's `Cargo.toml`.
2. Update any internal workspace dependency pin if the change is breaking.
3. Promote `[Unreleased]` in `CHANGELOG.md` to the new version with today's date.
4. Open a PR titled `chore(release): flux-isa v0.2.0` (or the relevant crate/version).

```bash
# Verify the package manifest and included files before publishing
cargo package -p flux-isa --list

# Dry run to catch any publish issues early
cargo publish -p flux-isa --dry-run
```

### Publishing to crates.io

Only maintainers with crates.io publish rights may publish. After the release PR merges to `master`:

```bash
# Publish in dependency order — dependencies before dependents
cargo publish -p flux-isa
sleep 30  # wait for crates.io index propagation
cargo publish -p flux-ast
cargo publish -p flux-provenance
cargo publish -p flux-bridge
# ... and so on for each crate in the release
```

Tag the release commit immediately after publishing:

```bash
git tag flux-isa-v0.2.0
git push origin flux-isa-v0.2.0
```

### GitHub Release

Create a GitHub Release from the tag. Paste the relevant `CHANGELOG.md` section as the release notes. Attach the `cargo package` tarball for auditing purposes.

---

## 10. Architecture Overview

FLUX is a constraint compilation toolchain. The high-level pipeline is:

```
  GUARD language source
         │
         ▼
  ┌─────────────┐
  │   guardc    │  GUARD → FLUX-C compiler
  │  (Rust)     │  Parsing, type-checking, lowering,
  └──────┬──────┘  provenance tracking (flux-provenance)
         │ FLUX-C IR (flux-ast)
         ▼
  ┌─────────────┐
  │  FLUX-C     │  Optimisation passes
  │  optimizer  │  (fluxc-optimize)
  └──────┬──────┘
         │ Optimised IR
         ▼
  ┌──────────────────────────────────────┐
  │          Code generation             │
  │  ┌───────────────┐  ┌─────────────┐ │
  │  │  flux-bridge  │  │  FPGA path  │ │
  │  │  (CUDA/GPU)   │  │ (DO-254)    │ │
  │  └───────┬───────┘  └──────┬──────┘ │
  └──────────┼─────────────────┼────────┘
             │                 │
             ▼                 ▼
       GPU kernels        FPGA bitstream
       (PTX/SASS)         (netlist)
```

### Key Crates

| Crate | Role |
|-------|------|
| `flux-isa` | Bytecode instruction set — the lingua franca between compiler and runtime |
| `flux-isa-{std,mini,edge,thor}` | ISA profiles for different deployment targets |
| `flux-ast` | GUARD language AST and FLUX-C IR types |
| `flux-provenance` | Tracks which source expressions produced which IR nodes — required for certification traceability |
| `guardc` | The primary GUARD→FLUX-C compiler; uses `winnow` for parsing |
| `guard2mask` | Lowers guard condition predicates to bitmask operations for SIMD/GPU execution |
| `flux-bridge` | Unsafe bridge to GPU runtimes (CUDA, Vulkan compute); owns all `unsafe` for GPU paths |
| `flux-hdc` | Hyperdimensional computing runtime for associative memory operations |
| `flux-verify-api` | Interface to external formal verification tools (SMT solvers, model checkers) |
| `cocapn-glue-core` | CoCAPN protocol integration for distributed constraint solving |

### Compiler Passes (flux-compiler-workspace)

```
fluxc-parser → fluxc-ast → fluxc-ir → fluxc-optimize → fluxc-codegen
                                    ↗
                         fluxc-verify (optional formal verification gate)
```

The verification gate is skipped by default but required for any output targeting a certification path (DO-254 FPGA bitstream, IEC 61508 runtime). Enable it with `--verify` on the `fluxc` CLI.

---

## 11. Safety-Critical Coding Guidelines

Several crates target aviation (DO-178C/DO-254), marine (IEC 61508), and autonomous systems where software errors can cause physical harm. These guidelines apply to any crate with a `# Safety Classification` section in its README.

### MISRA-C:2012 Compliance Target

The ARM runtime components (targeting `flux-isa-edge` on embedded ARM) aim for MISRA-C:2012 compliance in their **generated output**. The Rust source need not be MISRA-C itself, but the generated FLUX-C IR and any C shim layer must comply. Key rules:

- **Rule 14.4** (controlling expression of `if` must be essentially Boolean): do not generate integer-valued conditions; always emit explicit comparisons in codegen.
- **Rule 11.3** (no casts between pointer and integer types): all pointer arithmetic must go through `flux-bridge`'s typed handle API.
- **Rule 15.5** (functions with non-void return must have a single exit point): structure generated control flow accordingly in `fluxc-codegen`.
- **Rule 17.2** (no recursive functions): the constraint solver must not generate recursive call chains in FLUX-C output.

### Defensive Coding

In safety-critical crates:

- **No panicking code.** Replace `unwrap()`, `expect()`, `panic!()`, and `unreachable!()` with `Result` / `Option` propagation or a custom `FluxError` type. CI runs a custom lint to detect panics in safety-critical crate paths.

- **No floating-point in control paths.** Constraint predicates must use integer or fixed-point arithmetic. Floating-point is only permitted in GPU kernel bodies and HDC operations, not in code that decides control flow.

- **Explicit overflow handling.** Use `checked_add`, `saturating_add`, or `wrapping_add` — never rely on debug-mode overflow detection. Rust's release-mode integer overflow is undefined behavior under most safety standards.

```rust
// SAFETY-CRITICAL: use checked arithmetic; overflow must not silently wrap
let next_pc = current_pc
    .checked_add(offset)
    .ok_or(FluxError::PcOverflow { current_pc, offset })?;
```

### Traceability

Every function that implements a requirement traceable to a certification document must carry a `// REQ:` comment citing the document and requirement ID:

```rust
// REQ: DO-254 §4.5.1 — each FPGA configuration word must be checksummed
// before transmission to the target device.
pub fn checksum_config_word(word: u32) -> u32 {
    crc32_mpeg2(word)
}
```

### Formal Verification Gates

Changes to constraint-solving algorithms or ISA semantics may require a formal verification pass through `flux-verify-api`. The safety PR template will prompt for this. If you are unsure whether your change requires formal verification, ask in the PR and a safety reviewer will advise.

### Code Review for Safety-Critical Changes

In addition to the standard 2-reviewer requirement (§6), safety-critical PRs must:

- Document the failure mode of the code being changed and the new code's handling of it
- Include a regression test for the specific failure mode
- Be approved by at least one reviewer listed in `SAFETY-REVIEWERS.md`
- Not be merged by the PR author, regardless of merge permissions

---

## 12. License and CLA

### License

FLUX crates are dual-licensed under **MIT OR Apache-2.0** at your option.

- [`LICENSE-MIT`](./LICENSE-MIT) — [MIT License](https://opensource.org/licenses/MIT)
- [`LICENSE-APACHE`](./LICENSE-APACHE) — [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

When you contribute, you agree that your contributions will be licensed under the same terms.

### Contributor License Agreement (CLA)

To protect contributors, users, and the project's ability to remain open source, we require a signed CLA before merging contributions.

**Individual contributors:** Sign the Individual CLA once. The CLA bot on GitHub will prompt you automatically on your first PR.

**Corporate contributors:** If you are contributing on behalf of your employer (i.e., your employment contract assigns IP to your employer), your company must sign the Corporate CLA. Contact **legal@superinstance.com** to arrange this.

The CLA grants the project a perpetual, royalty-free license to use your contributions under the project's current and future licenses. It does **not** transfer copyright — you retain ownership of your work.

### Third-Party Dependencies

All dependencies must have licenses compatible with MIT/Apache-2.0. GPL, LGPL, AGPL, and SSPL licensed dependencies are **not permitted** in the dependency graph of any publishable FLUX crate. `cargo deny check` enforces the allowlist defined in `deny.toml`.

If you need to add a new dependency, verify its license before opening the PR, and add it to `deny.toml` if it is not already listed.

---

## Getting Help

- **GitHub Discussions** — architecture questions, RFC feedback, general discussion
- **GitHub Issues** — bug reports and concrete feature requests
- **Email** — casey@superinstance.com for security disclosures and CLA questions

We look forward to your contributions. Welcome to FLUX.
