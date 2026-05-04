# flux-docs: Documentation for the FLUX Constraint Compiler
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This repository is the official single-source documentation hub for the FLUX constraint compiler, an open-source tool for declarative constraint specification, formal verification, and deployment across hardware, embedded systems, and security compliance workflows. Designed for hardware engineers, formal verification specialists, security teams, and DevOps engineers building reliable, auditable constraint pipelines, this repo aggregates all official learning materials, reference guides, and workflow resources.

## Tutorials
Hands-on guided learning paths to master FLUX’s full feature set:
- **Quickstart**: Get up and running in 10 minutes, including installing the FLUX CLI, writing your first hardware constraint, and running a basic formal verification check.
- **Hardware Constraint Design**: Build and validate constraints for custom RTL IP blocks and system-on-chip integrations.
- **Temporal Constraints**: Write and validate safety and liveness specifications for real-time embedded systems.
- **Security Compliance**: Map FLUX constraints to GDPR, PCI DSS, and ISO 27001 requirements for auditable system policy enforcement.
- **Formal Verification**: Integrate FLUX with SMT solvers to prove design correctness and eliminate edge-case bugs.
- **AST Deep Dive**: Inspect and manipulate FLUX’s abstract syntax tree to build custom tooling and extend the compiler’s functionality.

## Practical Resources
### Cookbooks
Reusable, production-ready workflows: Package FLUX constraints in CI/CD pipelines, generate Verilog assertion files, migrate legacy constraint sets, and integrate FLUX with industry tools like Verilator and Cadence JasperGold.
### Runbooks
Step-by-step incident response playbooks for common FLUX tooling issues: solver timeouts, syntax errors, cross-compilation failures, and more.
### Error Guides
Comprehensive reference for every FLUX CLI error code, with troubleshooting tips and root-cause analysis for pitfalls like over-constraining designs or missing type annotations.

## Get Started & Contribute
Clone this repo locally to browse documentation offline, or serve it via MkDocs with `mkdocs serve` after installing dependencies. Start with the [Quickstart Tutorial](./tutorials/quickstart.md) for immediate hands-on practice. All community contributions—typo fixes, new cookbooks, expanded error guides—are welcome under the Apache 2.0 License; see [CONTRIBUTING.md](./CONTRIBUTING.md) for submission guidelines.

## License & Pairings
This project is licensed under the Apache License 2.0; see the [LICENSE](./LICENSE) file for full terms. This documentation pairs with the official [FLUX compiler repository](https://github.com/flux-constraint-compiler/flux) for tooling downloads and source code.

(Word count: 397)