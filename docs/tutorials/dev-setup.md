# Developer Environment Setup Guide

This guide walks you through setting up a complete development environment for the Flux constraint verification system. Follow these steps in order; each builds on the previous.

---

## Prerequisites

### Required Software

| Tool           | Minimum Version | Recommended  | Check Command              |
|----------------|-----------------|--------------|----------------------------|
| Rust           | 1.75.0          | 1.82+        | `rustc --version`          |
| Python         | 3.10            | 3.12+        | `python3 --version`        |
| GCC            | 11              | 13+          | `gcc --version`            |
| Git            | 2.30            | 2.43+        | `git --version`            |
| CMake          | 3.20            | 3.28+        | `cmake --version`          |
| Make           | 4.2             | 4.4+         | `make --version`           |

### Optional Software

| Tool           | Version         | Purpose                              |
|----------------|-----------------|--------------------------------------|
| CUDA Toolkit   | 12.0+           | GPU-accelerated constraint checking  |
| Coq            | 8.18+           | Proof extraction from GUARD specs    |
| Docker         | 24.0+           | Containerized build environment      |
| VS Code        | 1.85+           | IDE with rust-analyzer extension     |

### System Requirements

- **RAM:** 16 GB minimum, 32 GB recommended (Rust compilation is memory-intensive)
- **Disk:** 10 GB free space for full workspace + build artifacts
- **OS:** Linux (Ubuntu 22.04+ recommended), macOS 13+, or WSL2 on Windows 11

---

## Step 1: Install Rust

Install Rust via `rustup` (the official installer):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Select the default installation (option 1). After installation, source your environment:

```bash
source "$HOME/.cargo/env"
```

**Pin to the correct toolchain:**

```bash
rustup default 1.75.0
# Or use a newer version if your project allows:
rustup default stable
rustup update
```

**Install required components:**

```bash
rustup component add rustfmt clippy rust-src llvm-tools
cargo install cargo-nextest cargo-audit cargo-outdated
```

> **Why 1.75.0?** The Flux workspace uses `edition = "2021"` and pins `uuid` to `≤1.4.1` to avoid MSRV issues. If you use a newer rustc, builds will still work but CI pins to 1.75.0 for reproducibility.

---

## Step 2: Install Python and Tools

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# macOS
brew install python@3.12
```

Create a virtual environment in the workspace:

```bash
cd ~/flux-workspace
python3.12 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
```

The `requirements-dev.txt` includes:

```
pytest>=8.0
pytest-benchmark>=4.0
pytest-cov>=5.0
mypy>=1.8
black>=24.0
ruff>=0.4
pyyaml>=6.0
jsonschema>=4.20
```

---

## Step 3: Install GCC and Build Tools

```bash
# Ubuntu/Debian
sudo apt install build-essential gcc-13 g++-13 cmake make pkg-config libssl-dev

# Set GCC 13 as default
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 100

# macOS (Xcode command line tools)
xcode-select --install
```

Verify:

```bash
gcc --version    # Should show 11+ (or 13+)
cmake --version  # Should show 3.20+
```

---

## Step 4: Clone Repositories

The Flux workspace consists of 7 repositories. Clone them all into a single workspace directory:

```bash
mkdir -p ~/flux-workspace && cd ~/flux-workspace

# Core components
git clone https://github.com/SuperInstance/flux-core.git
git clone https://github.com/SuperInstance/flux-hardware.git
git clone https://github.com/SuperInstance/flux-runtime.git

# Compiler and tooling
git clone https://github.com/SuperInstance/guard-compiler.git
git clone https://github.com/SuperInstance/guard-vscode.git

# Test suites and benchmarks
git clone https://github.com/SuperInstance/flux-tests.git
git clone https://github.com/SuperInstance/flux-benchmarks.git
```

Or use the bootstrap script:

```bash
curl -sSL https://raw.githubusercontent.com/SuperInstance/flux-core/main/scripts/bootstrap.sh | bash
```

### Repository Overview

| Repo               | Language   | Description                                      |
|--------------------|------------|--------------------------------------------------|
| `flux-core`        | Rust       | Core constraint engine, type system, IR           |
| `flux-hardware`    | Rust+Py   | Hardware abstraction, sensor drivers, HIL tests   |
| `flux-runtime`     | Rust       | Runtime scheduler, executor, telemetry            |
| `guard-compiler`   | Rust       | GUARD → Rust/Python/Coq compiler (`guardc`)       |
| `guard-vscode`     | TypeScript | VS Code extension for GUARD syntax highlighting   |
| `flux-tests`       | Mixed      | Integration tests, property tests, fuzzing        |
| `flux-benchmarks`  | Rust+Py   | Performance benchmarks, regression detection       |

---

## Step 5: Build the Rust Workspace

The core Rust projects share a workspace. Build from `flux-core`:

```bash
cd ~/flux-workspace/flux-core

# Debug build (fast compilation, slower runtime)
cargo build

# Release build (for benchmarks and production testing)
cargo build --release

# Run all unit tests
cargo test

# Run with nextest (better output, parallel test execution)
cargo nextest run
```

### Build Order Matters

If you're building individual crates:

```bash
# 1. Core types and IR (no dependencies)
cargo build -p flux-types -p flux-ir

# 2. Compiler frontend
cargo build -p guard-parser -p guard-typecheck

# 3. Compiler backend (code generation)
cargo build -p guard-codegen-rust -p guard-codegen-python

# 4. Runtime
cargo build -p flux-runtime

# 5. Hardware abstraction
cargo build -p flux-hardware

# 6. CLI tools
cargo build -p guardc -p flux-cli
```

### Handling OOM During Build

Rust compilation can use a lot of memory. If builds fail with OOM:

```bash
# Limit parallel codegen units
CARGO_BUILD_JOBS=2 cargo build

# Reduce debug info (saves ~30% memory)
CARGO_PROFILE_DEV_DEBUG=1 cargo build

# Clean and rebuild (frees stale artifacts)
cargo clean && cargo build
```

> **Rule of thumb:** Max 2 concurrent `cargo check/build` on a 16 GB machine. Serialize Rust builds.

---

## Step 6: Run Tests

### Rust Tests

```bash
# All tests
cargo nextest run --workspace

# Specific crate
cargo nextest run -p flux-core

# With coverage
cargo llvm-cov --html

# Doc tests
cargo test --doc

# Clippy lints
cargo clippy --workspace --all-targets -- -D warnings

# Format check
cargo fmt --check
```

### Python Tests

```bash
cd ~/flux-workspace/flux-hardware
source ~/flux-workspace/.venv/bin/activate

# Run test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=flux_hardware --cov-report=html

# Specific test file
pytest tests/test_perf_regression.py -v --benchmark-only
```

### Integration Tests

```bash
cd ~/flux-workspace/flux-tests

# Run GUARD compiler test suite
cargo nextest run --features integration

# Property-based tests (proptest)
cargo nextest run --features property

# Fuzzing (optional, long-running)
cargo +nightly fuzz run guard_parser
```

---

## Step 7: Pre-Commit Hooks

Install git hooks for code quality:

```bash
cd ~/flux-workspace/flux-core

# Install pre-commit (Python-based framework)
pip install pre-commit
pre-commit install

# Run against all files (initial check)
pre-commit run --all-files
```

The `.pre-commit-config.yaml` includes:

- **rustfmt** — Rust code formatting
- **clippy** — Rust lints
- **black** — Python formatting
- **ruff** — Python lints
- **mypy** — Python type checking
- **trailing whitespace** — General cleanup
- **yaml/toml validation** — Config file checks
- **conventional commits** — Commit message format

If a hook fails, fix the issue and re-stage:

```bash
# Auto-fix what's possible
pre-commit run --all-files
git add -u
git commit
```

---

## Step 8: VS Code Setup

### Recommended Extensions

Install these extensions for the best development experience:

```
# From the command line:
code --install-extension rust-lang.rust-analyzer
code --install-extension vadimcn.vscode-lldb
code --install-extension tamasfe.even-better-toml
code --install-extension ms-python.python
code --install-extension ms-python.debugpy
code --install-extension charliermarsh.ruff
code --install-extension usernamehw.errorlens
code --install-extension superinstance.guard-vscode
```

### Workspace Settings

Create `.vscode/settings.json` in the workspace root:

```json
{
  "rust-analyzer.check.command": "clippy",
  "rust-analyzer.cargo.features": "all",
  "rust-analyzer.procMacro.enable": true,
  "python.defaultInterpreterPath": "${workspaceFolder}/../.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.associations": {
    "*.guard": "guard"
  },
  "[rust]": {
    "editor.defaultFormatter": "rust-lang.rust-analyzer"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

### Launch Configurations

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug guardc",
      "type": "lldb",
      "request": "launch",
      "cargo": {
        "args": ["build", "-p", "guardc", "--bin=guardc"]
      },
      "program": "${workspaceFolder}/target/debug/guardc",
      "args": ["compile", "examples/thermostat.guard"],
      "cwd": "${workspaceFolder}"
    },
    {
      "name": "Debug Tests (flux-core)",
      "type": "lldb",
      "request": "launch",
      "cargo": {
        "args": ["test", "-p", "flux-core", "--no-run"]
      },
      "program": "${workspaceFolder}/target/debug/deps/flux_core-*
    }
  ]
}
```

---

## Step 9: Docker Alternative (Optional)

If you prefer containerized development:

```bash
cd ~/flux-workspace/flux-core

# Build the development container
docker build -t flux-dev -f Dockerfile.dev .

# Run with workspace mounted
docker run -it --rm \
  -v $(pwd):/workspace \
  -v ~/flux-workspace:/flux-workspace \
  -p 9229:9229 \
  flux-dev \
  bash

# Inside container, build normally
cargo build && cargo nextest run
```

The dev container includes all prerequisites pre-installed (Rust 1.75, Python 3.12, GCC 13, Coq 8.18).

---

## Step 10: Install Coq (Optional)

For proof extraction from GUARD specifications:

```bash
# Ubuntu/Debian
sudo apt install coq opam

# Or via opam (recommended for latest version)
opam init
opam switch create coq 4.14.1
eval $(opam env)
opam install coq.8.18.0

# Verify
coqc --version
```

Compile extracted proofs:

```bash
cd ~/flux-workspace/flux-core/proofs
make all
```

---

## Troubleshooting

### "linker 'cc' not found"

Install build essentials:
```bash
sudo apt install build-essential
```

### "cargo: rustc 1.75.0 is not installed"

```bash
rustup install 1.75.0
rustup default 1.75.0
```

### Rust build OOM / killed

```bash
# Reduce parallelism
CARGO_BUILD_JOBS=2 cargo build

# Or add to .cargo/config.toml:
[build]
jobs = 2
```

### Python "ModuleNotFoundError"

Ensure your virtual environment is active:
```bash
source ~/flux-workspace/.venv/bin/activate
which python3  # Should point to .venv/bin/python3
```

### "uuid v1.6.0 requires rustc 1.78+"

Pin uuid to compatible version:
```bash
# In Cargo.toml:
uuid = { version = "1.4.1", features = ["v4"] }
```

### Clippy warnings treated as errors

This is intentional. Fix the warnings:
```bash
cargo clippy --fix --allow-dirty
```

### Pre-commit hook fails on existing code

Run the auto-fix:
```bash
pre-commit run --all-files
# Fix remaining issues manually, then:
git add -u && git commit
```

### Docker container can't access USB devices

For hardware-in-the-loop tests, pass USB through:
```bash
docker run --privileged -v /dev/bus/usb:/dev/bus/usb ...
```

### CUDA not detected

Ensure the CUDA toolkit is installed and `nvcc` is in PATH:
```bash
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
nvcc --version
```

---

## Quick Verification

Run this to verify your complete setup:

```bash
#!/bin/bash
echo "=== Flux Dev Environment Check ==="
echo "Rust:     $(rustc --version)"
echo "Python:   $(python3 --version)"
echo "GCC:      $(gcc --version | head -1)"
echo "CMake:    $(cmake --version | head -1)"
echo "Git:      $(git --version)"
echo "Cargo:    $(cargo --version)"
echo ""
echo "=== Build Check ==="
cd ~/flux-workspace/flux-core && cargo check --quiet && echo "✅ Rust workspace compiles"
cd ~/flux-workspace/flux-hardware && python3 -c "import flux_hardware" && echo "✅ Python module loads"
echo ""
echo "=== Test Check ==="
cd ~/flux-workspace/flux-core && cargo test --quiet && echo "✅ Rust tests pass"
echo ""
echo "🎉 Environment ready!"
```

Save as `verify-setup.sh` and run:
```bash
chmod +x verify-setup.sh
./verify-setup.sh
```

---

*Last updated: 2026-05-03 — Forgemaster ⚒️*
