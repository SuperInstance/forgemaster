# Contributing to FLUX Constraint Compiler

Welcome to the FLUX open-source formal constraint compiler project! FLUX verifies safety and correctness properties of systems code, and we welcome contributions of all skill levels and types—from bug reports to core proof improvements—to make the tool more reliable and useful for the formal verification community.

## Code of Conduct
This project follows the [Contributor Covenant v2.1](https://contributor-covenant.org/version/2/1/). All participants must treat others with respect, avoid harassment or discriminatory language, and prioritize inclusivity. To report unacceptable behavior, contact project maintainers at flux-maintainers@googlegroups.com.

## How to Contribute
### Bug Reports
File bugs via GitHub Issues: include a clear description, reproduction steps, expected vs. actual behavior, and your environment (Rust toolchain version, FLUX commit SHA). Link relevant issues in any fix pull requests.
### Feature Requests
Open a draft issue first to discuss proposed features, outlining your use case and intended functionality to avoid misaligned work.
### Code & Documentation
Follow Rust community conventions for code style and documentation. Fix typos, clarify workflows, or add tutorials in the `/docs` directory or inline code comments. For code changes, add tests covering your new functionality or bug fix.
### Proof Contributions
Critical for verifying FLUX’s own correctness and user-facing safety properties; see the dedicated Adding Proofs section below.

## Development Setup
Prerequisites: Rust 1.75+ (install via [rustup](https://rustup.rs/)) and the Z3 SMT solver (install via your system package manager, e.g. `apt install z3` or `brew install z3`).
1. Clone your forked repo: `git clone https://github.com/YOUR-USERNAME/flux-compiler.git`
2. Build the compiler: `cargo build`
3. Run the full test suite: `cargo test`
4. Run lint checks: `cargo clippy --all-targets --all-features -- -D warnings`

## PR Process
1. Fork the upstream FLUX repo and create a descriptive feature branch off `main` (e.g. `fix/user-id-validation`, `docs/setup-guide`).
2. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages: prefix with `fix:`, `feat:`, `docs:`, or `chore:`.
3. Push your branch to your fork and open a pull request against upstream `main`. Link related issues in your PR description.
4. All PRs must pass CI lint and test checks, and receive approval from at least one maintainer before merging.

## Adding GUARD Examples
GUARD examples showcase real-world FLUX constraint specifications for common validation tasks. Use this template for new examples:
```rust
// GUARD Example: [Short Descriptive Name]
// Use Case: 1-sentence explanation of the real-world scenario
// Constraints:
// - Formal constraint 1 (e.g. "Input length must be 5-20 characters")
// - Formal constraint 2 (e.g. "Input only contains alphanumeric characters")
fn example_fn(params: Type) -> ReturnType { /* implementation with embedded constraints */ }
```
Add your file to `examples/guard/`, update `examples/README.md` if required to link your new example, then submit a PR.

## Adding Proofs
Proofs verify FLUX’s core correctness and user safety properties. Requirements:
1. Write proofs using FLUX’s formal proof DSL or SMT-LIB compatible syntax in the `proofs/` directory.
2. Include a formal specification of the property being verified, step-by-step proof script, and validation test cases.
3. Document your proof’s purpose and scope in `proofs/README.md`.
4. All proof PRs require review from a formal verification maintainer.

## Safety Requirements
Any changes to the FLUX VM or core compiler logic—including constraint emission, type checking rules, or IR transformations—require an accompanying formal safety proof to merge. This ensures no unsoundness or verification gaps are introduced into the tool.

(Word count: ~598)