# Changelog

All notable changes to Forgemaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-06-18

### Added
- **Recipe** — Declarative build specification with topological sorting, cycle detection, and content-addressable fingerprints.
- **Step** — Individual build unit with dependency tracking, configurable retries, and timeout support.
- **BuildQueue** — Priority queue with `CRITICAL`/`HIGH`/`NORMAL`/`LOW`/`BACKGROUND` levels, FIFO within each priority.
- **Forge** — Top-level orchestrator binding recipes, queue, artifacts, and monitoring into a single API.
- **Artifact** — Build output tracking with SHA-256 content digests, state machine (`UNKNOWN → BUILDING → READY/STALE/FAILED`), and metadata.
- **BuildMonitor** — Ring-buffer event log with per-recipe event lookup, step timing, and build summaries.
- **Dockerfile** and **Makefile** for reproducible builds.
- PLATO bridge for curriculum-aware compilation.
- Flux ISA and CUDA experiment harnesses.
- CT-demo constraint solver in Rust.
- 36 tests covering recipes, artifacts, queue, monitor, and forge integration.

### Known Limitations
- `max_workers` is accepted but execution is currently sequential.
- No persistent storage — queue and monitor state are in-memory only.
- No timeout enforcement on `Step.action`.
