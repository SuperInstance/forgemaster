

# Flux Compiler: Unified Rust Cargo Workspace Architecture

This document provides a complete, production-ready Rust workspace design that unifies the legacy `guard2mask`, `guardc`, `guard-dsl`, and Python `compiler/` components into a single, cohesive `flux-compiler` repository. The architecture emphasizes zero-cost abstractions, strict error handling, feature-gated backends, and reproducible builds.

## 1. Complete Directory Tree

```
flux-compiler/
├── Cargo.toml                  # Workspace root
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE-MIT
├── LICENSE-APACHE-2.0
├── docs/
│   ├── book.toml
│   └── src/
│       ├── getting-started.md
│       ├── architecture.md
│       ├── backends.md
│       ├── grammar.md
│       └── contributing.md
├── flux-dsl/
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── grammar.rs
│       └── ast.rs
├── flux-core/
│   ├── Cargo.toml
│   ├── build.rs
│   ├── src/
│   │   ├── lib.rs
│   │   ├── parser.rs
│   │   ├── ast.rs
│   │   ├── bytecode.rs
│   │   ├── compiler.rs
│   │   └── error.rs
│   └── grammar/
│       └── guard.lalrpop
├── flux-backend/
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── llvm.rs
│       ├── ebpf.rs
│       ├── cuda.rs
│       ├── wasm.rs
│       └── riscv.rs
├── fluxc/
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       ├── cli.rs
│       └── config.rs
├── tests/
│   ├── integration.rs
│   └── fixtures/
│       ├── basic.guard
│       ├── complex.guard
│       └── invalid.guard
└── benches/
    ├── compiler_bench.rs
    └── backend_bench.rs
```

## 2. Workspace Root `Cargo.toml`

```toml
[workspace]
members = [
    "flux-dsl",
    "flux-core",
    "flux-backend",
    "fluxc",
]
resolver = "2"
default-members = ["fluxc"]

[workspace.package]
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"
authors = ["Flux Compiler Team"]
repository = "https://github.com/flux-compiler/flux-compiler"
homepage = "https://flux-compiler.dev"
documentation = "https://docs.flux-compiler.dev"
readme = "README.md"

[workspace.dependencies]
thiserror = "1.0"
clap = { version = "4.4", features = ["derive"] }
anyhow = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
log = "0.4"
env_logger = "0.10"
proptest = "1.4"
criterion = "0.5"
object = "0.32"
gimli = "0.28"
hashbrown = "0.14"
smallvec = "1.11"
bitflags = "2.4"
lalrpop = "0.20"
lalrpop-util = "0.20"

[workspace.lints.rust]
unsafe_code = "forbid"
unused_qualifications = "warn"
clippy::all = { level = "warn", priority = -1 }

[workspace.lints.clippy]
all = { level = "warn", priority = -1 }
pedantic = { level = "warn", priority = -1 }
nursery = { level = "warn", priority = -1 }
```

## 3. Crate-Level `Cargo.toml` Files

### `flux-dsl/Cargo.toml`
```toml
[package]
name = "flux-dsl"
version.workspace = true
edition.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
documentation.workspace = true
readme.workspace = true

[dependencies]
serde = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }
thiserror = { workspace = true }

[lints]
workspace = true
```

### `flux-core/Cargo.toml`
```toml
[package]
name = "flux-core"
version.workspace = true
edition.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
documentation.workspace = true
readme.workspace = true

[dependencies]
flux-dsl = { path = "../flux-dsl" }
thiserror = { workspace = true }
serde = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }
hashbrown = { workspace = true }
smallvec = { workspace = true }
bitflags = { workspace = true }
log = { workspace = true }
lalrpop-util = { workspace = true, features = ["lexer"] }

[dev-dependencies]
proptest = { workspace = true }
criterion = { workspace = true }

[build-dependencies]
lalrpop = { workspace = true }

[features]
default = []
avx512 = []
cuda = []
wasm = []
ebpf = []
riscv = []

[lints]
workspace = true
```

### `flux-backend/Cargo.toml`
```toml
[package]
name = "flux-backend"
version.workspace = true
edition.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
documentation.workspace = true
readme.workspace = true

[dependencies]
flux-core = { path = "../flux-core" }
thiserror = { workspace = true }
object = { workspace = true }
gimli = { workspace = true }
log = { workspace = true }

[features]
default = ["llvm"]
llvm = ["llvm-sys"]
avx512 = ["flux-core/avx512"]
cuda = ["flux-core/cuda"]
wasm = ["flux-core/wasm"]
ebpf = ["flux-core/ebpf"]
riscv = ["flux-core/riscv"]

[dependencies.llvm-sys]
version = "0.1"
optional = true

[lints]
workspace = true
```

### `fluxc/Cargo.toml`
```toml
[package]
name = "fluxc"
version.workspace = true
edition.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
documentation.workspace = true
readme.workspace = true

[[bin]]
name = "fluxc"
path = "src/main.rs"

[dependencies]
flux-core = { path = "../flux-core" }
flux-backend = { path = "../flux-backend" }
clap = { workspace = true }
anyhow = { workspace = true }
log = { workspace = true }
env_logger = { workspace = true }
serde_json = { workspace = true }

[lints]
workspace = true
```

## 4. Module Structure & Implementation Details

### `flux-dsl/src/lib.rs`
Re-exports grammar tokens and base AST types. Serves as the canonical specification layer.
```rust
pub mod ast;
pub mod grammar;
pub use ast::*;
pub use grammar::*;
```

### `flux-core/src/lib.rs`
Public API surface. Exposes parser, bytecode encoder, and compiler pipeline.
```rust
pub mod error;
pub mod parser;
pub mod ast;
pub mod bytecode;
pub mod compiler;

pub use error::FluxError;
pub use parser::parse_guard;
pub use compiler::compile_guard_to