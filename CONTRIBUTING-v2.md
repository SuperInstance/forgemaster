# Contributing to FLUX Constraint System

Thank you for considering contributing to FLUX! FLUX is a formal constraint solving and verification system, and we welcome all types of contributions: bug fixes, new features, documentation improvements, tests, and more.

---

## Code of Conduct
We follow a "be excellent to each other" policy for all community interactions, whether on GitHub, in discussions, or at community events. This means:
- Respect all contributors, regardless of background, experience level, or perspective.
- Avoid harassment, discrimination, or harmful language of any kind.
- Assume good faith: disagree with ideas, not people.
- Report unacceptable behavior to the project maintainers promptly, and we will review and address violations appropriately.

For security-sensitive issues (e.g., vulnerabilities), do **not** open a public issue — instead contact maintainers directly via [security@fluxconstraint.org] (replace with your official contact email).

---

## How to Contribute

### Bug Reports
Found a bug? Open a GitHub issue with these details:
1. Steps to reproduce the bug (include a minimal, self-contained FLUX program example if possible)
2. Expected behavior vs. actual observed behavior
3. Your environment: OS version, Rust toolchain version, GCC version, and Python version
4. Relevant logs, error output, or screenshots

Use the pre-built bug report template to streamline your submission!

### Feature Requests
Have an idea for a new feature or improvement? Open a GitHub issue with:
1. A clear description of the feature and its real-world use case
2. Why this would benefit the FLUX community
3. Draft implementation ideas or existing references if you have them

For small, low-risk changes (typo fixes, minor documentation tweaks) you can skip opening an issue and go straight to a pull request.

### Pull Requests
Ready to submit changes? Follow this workflow:
1. Fork the FLUX repository and clone your local copy:
   ```bash
   git clone https://github.com/FLUX-Constraint-System/flux.git
   cd flux
   ```
2. Create a descriptive branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # Or for bug fixes: git checkout -b fix/your-bug-fix
   ```
3. Make changes following the code style and testing guidelines below.
4. Commit with clear, conventional messages: `[component]: Short description of changes` (e.g. `[cli]: Add --target-boogie flag`).
5. Push your branch to your forked repo and open a pull request against the main `flux` repository:
   - Include a clear title and detailed description of your changes
   - Link to any related issues
   - Open a **draft PR** early for larger changes to gather feedback and avoid rework later

> Note: No Contributor License Agreement (CLA) is required. By submitting a PR, you agree your contributions will be licensed under the Apache 2.0 License, and you retain copyright for your original work.

---

## Development Setup

First install the required core dependencies:
1. **Rust Toolchain**: We use Rust for the core FLUX backend and CLI. Install via [rustup](https://rustup.rs/):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```
   The project includes a `rust-toolchain.toml` file to pin the exact Rust version we use — run `rustup show` in the repo root to activate the correct toolchain.
2. **GCC**: Required for compiling native C bindings and target-specific native code:
   - Debian/Ubuntu: `sudo apt install gcc`
   - macOS: `brew install gcc`
   - Windows: Use [MinGW-w64](https://www.mingw-w64.org/) or WSL2
3. **Python 3**: Required for auxiliary tooling, testing scripts, and differential testing. Ensure Python 3.8+ is installed, then install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

### Optional Target Dependencies
Some solver backends require additional tools:
- Z3 backend: Install libz3 via your package manager or the [Z3 official releases](https://github.com/Z3Prover/z3)

Finally, build the full project:
```bash
cargo build
```

---

## Code Style
Consistent style keeps the codebase readable and maintainable. Follow these rules for all contributions:

### Rust
- All Rust code **must be formatted with `rustfmt`**: Run `cargo fmt --all` before committing.
- We enforce clippy lints to catch bugs and style issues: Run `cargo clippy --all-targets --all-features` and fix all warnings before submitting.
- Follow official Rust API guidelines, use clear, descriptive names for functions, types, and variables.

### C
- All C code follows the [Linux Kernel Coding Style](https://www.kernel.org/doc/html/latest/process/coding-style.html).
- Use the included `.clang-format` config to auto-format C code: `clang-format -i path/to/your/c/file.c`
- Avoid non-standard C extensions; target C11 for broad compatibility.

### Python
- All Python code **must be formatted with `black`**: Run `black .` in the repo root to format all files.
- Follow PEP 8 for all other style rules (indentation, line length, naming conventions).
- Remove unused imports and variables.

---

## Testing
All contributions must pass existing tests and include new tests for new features or bug fixes.

### Rust Tests
Run the full Rust test suite:
```bash
cargo test --all --all-features
```
This includes unit, integration, and doctests for all workspace crates.

### Python Tests
First build the Rust backend, then run the Python test suite:
```bash
cargo build
pytest tests/
```

### Differential Testing
Differential testing ensures FLUX produces consistent, correct output across all backends and target formats. Run differential tests with:
```bash
# Rust-based differential tests
cargo test --features differential
# Python-based differential tests
pytest tests/differential/
```
When adding new targets or constraint types, add new differential tests to validate consistent cross-backend behavior.

---

## Adding a New Target
FLUX supports multiple constraint solver backends and output formats. To add a new target:
1. **Implement the Emitter Trait**: Add a new module in `crates/flux-backends/src/emitters/` for your target. Implement the `Emitter` trait defined in `crates/flux-backends/src/lib.rs`, which handles translating FLUX's core IR to your target format.
2. **Update the CLI**: Add a new command-line flag (e.g. `--target <your-target-name>`) in `flux-cli/src/cli.rs` and register your emitter with the CLI's target resolver.
3. **Add Unit Tests**: Write tests for your emitter in `crates/flux-backends/tests/` to validate correct output for sample constraints.
4. **Add Integration Tests**: Add a new directory in `tests/` for your target with sample FLUX programs and expected output.
5. **Update Documentation**: Add your target to the CLI help text, man pages, and target-specific docs in the `docs/` folder.

---

## Adding a New Constraint Type
To add a new formal constraint type to FLUX:
1. **Update the Core IR**: Add a new variant to the `Constraint` enum in `crates/flux-core/src/ir/mod.rs`, including any required fields (operands, attributes, metadata).
2. **Extend the Parser**: Update the FLUX frontend parser in `crates/flux-frontend/src/parser.rs` to recognize the new constraint syntax in the input language, and deserialize inputs to your new IR variant.
3. **Update All Emitters**: Modify every existing target emitter to handle the new constraint variant. For backends that do not support the constraint, add a clear user warning or fallback error.
4. **Prove Correctness**: Write unit tests to validate parsing and emission, plus differential tests to ensure cross-backend consistency. For formal verification constraints, use FLUX itself to prove the constraint's semantic correctness.
5. **Update Documentation**: Add the new constraint to the language reference, man pages, and tutorial content, including usage examples.

---

## Documentation
High-quality documentation is critical for making FLUX accessible to all users. We welcome:
- Typo fixes and clarity improvements
- New tutorials and how-to guides
- Updates to man pages and API references
- Formal specifications for core system components

### Documentation Guidelines
- Use clear, concise language and avoid unnecessary jargon
- Include tested code examples for all new features
- Follow the existing prose style and structure in the `docs/` folder
- Regenerate man pages after modifying CLI flags:
  ```bash
  cargo run -- build-man
  ```
  Commit the updated man pages with your changes.

---

## License
FLUX Constraint System is licensed under the Apache License, Version 2.0. You may obtain a copy of the License at [https://www.apache.org/licenses/LICENSE-2.0](https://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the `LICENSE` file for full details.

---

## Thank You!
We're thrilled you're interested in contributing to FLUX. If you have questions or need guidance, open a draft PR or start a GitHub Discussion. We can't wait to see what you build!