# Changelog

All notable changes to Forgemaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-08-07

### Fixed
- **Stale error on retry success** — `_execute_step` now clears `step.error` when a retry succeeds, preventing stale error messages from earlier attempts. (queue.py)
- **Uninformative error on False return** — When a step's action returns `False` instead of raising, `step.error` is now set to a descriptive message instead of remaining `None`. (queue.py)
- **Transitive dependency execution** — `Forge.build_one` and `BuildQueue.execute_one` now check for both `FAILED` and `SKIPPED` upstream steps, preventing execution of steps whose dependencies were transitively skipped due to upstream failures. (forge.py, queue.py)

### Added
- 27 new tests covering bug fixes, transitive dependency skipping, error propagation, empty recipe handling, and more. (tests/test_bugfixes.py)
- CI now runs the full pytest suite in addition to the differential test harness. (.github/workflows/ci.yml)

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
