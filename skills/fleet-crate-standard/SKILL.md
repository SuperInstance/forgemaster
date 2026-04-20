# Fleet Crate Standard

## What This Skill Is
A reusable guide for creating high-quality Rust crates that integrate cleanly into the Cocapn fleet. Establishes naming, structure, testing, and dependency conventions that make crates swappable and maintainable.

## When to Use It
- Authoring a new Rust crate for the fleet
- Auditing existing crates for quality signals
- Setting up CI/CD for fleet repos
- Reviewing PRs across SuperInstance and Lucineer orgs

## How It Works

### Crate Structure
```
crate-name/
├── Cargo.toml          # Standard metadata, workspace-compatible
├── src/
│   ├── lib.rs          # Public API, module exports
│   └── mod.rs          # Internal modules (if needed)
├── tests/             # Integration tests (not just unit)
└── README.md           # What it does, usage examples
```

### Naming Conventions
- **Prefix:** `plato-*` for PLATO stack crates, `flux-*` for Flux ISA, `constraint-theory-*` for core
- **Lowercase with hyphens** (snake_case → kebab-case)
- **Descriptive:** Name should tell you what the crate IS, not just does
  - `plato-tile-spec` ✅ (specifies tile format)
  - `plato-tile-parser` ❌ (too narrow; what about tiles that aren't parsed?)

### Cargo.toml Standards
```toml
[package]
name = "crate-name"
version = "0.1.0"
edition = "2021"           # or "2024" if you need features
rust-version = "1.75"         # Minimum for fleet WSL2 deployment

[dependencies]
# Zero external deps if possible. Use fleet crates first:
# plato-tile-spec = { path = "../plato-tile-spec" }
# constraint-theory-core = { version = "1.0.1" }

[dev-dependencies]
# Testing-only deps

[[bin]]
# Optional: only if crate has a CLI tool
```

### Public API Principles
1. **Zero-copy where possible** — Pass references, not clones
2. **Error types first** — Define `#[derive(Error)]` enum early
3. **Trait-based** — Use traits for swappable behavior
4. **Documentation** — Every public item gets `///` doc comment
5. **Example tests** — One integration test showing typical usage

### Testing Standards
```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_basic_usage() {
        // Show typical flow
    }
    
    #[test]
    fn test_edge_cases() {
        // What happens on empty/invalid input?
    }
    
    #[test]
    fn test_fleet_integration() {
        // Show how this crate works with others
    }
}
```
- **Target:** 20+ tests per crate
- **Coverage:** All public APIs have tests
- **Integration:** At least 1 test uses sibling crate

### Dependency Rules
1. **Fleet crates first** — Use `SuperInstance/` crates before crates.io
2. **Minimal externals** — Prefer std-only implementations
3. **Workspace-aware** — Check `constraint-theory-core` version before adding
4. **Cargo 1.75** — Avoid `edition = "2024"` unless you have to
5. **No thiserror v2** — It's not stable yet, use `anyhow` instead

### README Template
```markdown
# Crate Name

One-line description of what this crate does.

## What It Is
[2-3 sentences explaining the problem and solution]

## Usage
```rust
use crate_name::Type;

fn main() {
    let thing = Type::new();
    thing.do_work();
}
```

## Fleet Integration
- Depends on: `sibling-crate`
- Used by: `other-sibling-crate`

## Tests
`cargo test` — 20+ tests

## License
MIT (fleet standard)
```

## Examples
- `plato-tile-spec` — 31 tests, zero deps, canonical data format
- `plato-trust-beacon` — 25 tests, flux-trust adapter
- `plato-lab-guard` — 24 tests, hypothesis gating

## Related Skills
- `fleet-bottle-protocol` — How to write I2I bottles
- `fleet-audit-checklist` — Quality signals to check
