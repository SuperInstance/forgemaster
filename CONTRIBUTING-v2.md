# Contributing to Cocapn FLUX

## Code of Conduct
This project follows a "Be Excellent" code of conduct: treat all community members with respect, avoid harassment, discrimination, or unconstructive behavior. Report unacceptable conduct to maintainers at conduct@cocapn.ai if needed.

## Ways to Contribute
We welcome contributions across multiple categories:
1.  **Code**: Fix bugs, optimize core logic, or add new library features
2.  **Proofs**: Submit formal Coq-verified correctness proofs for critical components
3.  **Docs**: Improve API documentation, tutorials, or project setup guides
4.  **Examples**: Add sample workflows, integration scripts, or end-to-end demos
5.  **Benchmarks**: Contribute standardized performance tests to track FLUX throughput and latency

## Development Setup
1.  Clone the repository: `git clone https://github.com/cocapn/flux.git && cd flux`
2.  Install Rust 1.75+ via [rustup.rs](https://rustup.rs)
3.  Build the core library: `cargo build`
4.  Run the full test suite: `cargo test`
For CUDA kernel development, install the NVIDIA CUDA Toolkit 12.0+ to enable GPU kernel compilation and differential testing against CPU baselines.

## Commit Convention
Follow conventional commits for all commit messages using these required prefixes:
- `feat:`: New user-facing features
- `fix:`: Bug fixes for existing functionality
- `docs:`: Documentation-only changes
- `proof:`: Updates to Coq formal verification proofs
- `test:`: Adds or updates test suites or benchmarking code
Keep messages concise and descriptive, e.g. `feat: add INT8 CUDA matmul kernel`.

## Pull Request Process
1.  Fork the repository and create a feature branch off `main` (name branches like `feat/add-llm-integration` or `fix/issue-42`)
2.  Push your changes to your fork and open a PR against the upstream `main` branch
3.  All CI checks must pass: this includes Rust tests, Coq proof validation, and (for GPU changes) CUDA differential testing
4.  PRs require exactly one approving review from a core maintainer before merging to keep the process lightweight.

## Adding Proofs & CUDA Kernels
- **Proofs**: All submitted proofs must be fully Coq-checkable. Include `.v` files and update the CI pipeline to run `coqc` on new proofs to ensure automated validation.
- **CUDA Kernels**: All new kernels must pass differential testing against the reference CPU implementation. Add a benchmark test to validate numerical consistency and compare latency against the CPU baseline before PR submission.

## Security Vulnerabilities
Do not open public issues for security vulnerabilities. Send a detailed report with reproduction steps and affected components to `security@cocapn.ai`. We will respond within 48 hours to coordinate a coordinated fix.

## License
This project is licensed under the Apache License, Version 2.0. By contributing, you agree your work will be licensed under the same terms.

---
This file has been saved to `/home/phoenix/.openclaw/workspace/CONTRIBUTING-v2.md`