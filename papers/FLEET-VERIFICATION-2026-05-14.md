# Fleet Verification Report — 2026-05-14

## Executive Summary

Ran full verification on all 13 upgraded repos + 3 TypeScript repos.
**8 repos clean, 3 rocks found.**

## Results

### ✅ Clean (all tests pass)

| # | Repo | Lang | Tests | Notes |
|---|------|------|-------|-------|
| 1 | folding-order | Rust | 20/20 | Simulation-first predictions |
| 2 | fleet-memory | Rust | 43/43 | Lifecycle-aware distributed memory |
| 3 | holonomy-consensus | Rust | 49/49 | Trust tile lifecycle |
| 4 | penrose-memory | Rust | 51/51 | Aperiodic memory with lifecycle |
| 5 | flux-lucid | Rust | 103/103 | Simulation-first intent alignment |
| 6 | dodecet-encoder | Rust | 106/106 | Agent lifecycle + predict_gate |
| 7 | constraint-flow-protocol | Python | 26/26 | CFP v2 with predict/confirm |
| 8 | neural-plato | Python | 20/20 | All claims survive falsification |
| 9 | plato-sdk | Python | 19/19 | Fixed pytest pythonpath ✅ |

### ⚠️ Rocks Found

| # | Repo | Rock | Severity | Fix |
|---|------|------|----------|-----|
| 1 | **constraint-inference** | Zero tests. No test files at all. | HIGH | Need to write tests for simulation_first.ts, plato_bridge.ts |
| 2 | **intent-inference** | Zero tests. No test files at all. | HIGH | Need to write tests for inferrer.ts, fleet_bridge.ts |
| 3 | **plato-sdk** (fixed) | `pip install -e .` fails; tests only work with `PYTHONPATH=src` | MEDIUM | Fixed pyproject.toml with `[tool.pytest.ini_options]` |

### ℹ️ Notes (not rocks, but notable)

- **neural-plato**: Falsification suite is a standalone script, not pytest-compatible. Works fine as `python3 experiments/falsification_suite.py`. Not a rock, just unusual test style.
- **plato-sdk**: Has duplicate package in `python/` (old v0.1.0) and `src/` (v3.0.0). Should remove `python/` to avoid confusion.

## Archived Repo Verification

All 22 archived repos verified:
- Renamed with `-early-version` or `-old` suffix ✅
- Description prefixed `[ARCHIVED]` with successor link ✅
- README.md with explanation, "why archived", "where to go now", "can I use this" ✅
- Set to read-only on GitHub ✅

## Fleet Test Score

- **Total tests passing**: 437
- **Total repos verified**: 13
- **Rocks found**: 3 (1 fixed, 2 need test suites)
- **Rocks remaining**: 2 (constraint-inference, intent-inference — no tests)

## Recommendations

1. **Write tests for constraint-inference and intent-inference** — these are TypeScript repos with functional code but zero tests. High priority.
2. **Remove `python/` dir from plato-sdk** — stale v0.1.0 duplicate causing confusion.
3. **Add `npm test` script** to both TS repos with a basic test runner (vitest or jest).
