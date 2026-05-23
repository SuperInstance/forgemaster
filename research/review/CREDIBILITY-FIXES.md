# Credibility Fixes Report — 2026-05-17

## Task 1: fleet-spread test inflation ✅ FIXED

**Repo:** https://github.com/SuperInstance/fleet-spread
**Claim:** 147 tests
**Actual:** 133 `#[test]` annotations (counted via `grep -c "#\[test\]" tests/*.rs src/*.rs`)
**Action:** Updated README.md (2 occurrences) from 147 → 133
**Commit:** `4bbd6b0` — pushed to `main`

Could not `cargo test` to confirm (missing `fleet-coordinate` dependency), but source-level count is definitive.

## Task 2: Published package verification ✅ DONE

| Package | Registry | Status |
|---------|----------|--------|
| `constraint-theory-core` v2.0.0 | crates.io | ✅ Published (library crate, no binary) |
| `spectral-conservation` v0.1.0 | crates.io | ✅ Published (library crate, no binary) |
| `constraint-theory` v1.0.1 | PyPI | ✅ Published and importable (imports verified) |
| `plato-model-ocean` | PyPI | ❌ NOT FOUND |
| `plato-escalation-gate` | PyPI | ❌ NOT FOUND |
| `plato-room-intelligence` | PyPI | ❌ NOT FOUND |

**Action needed:** Remove claims about plato-model-ocean, plato-escalation-gate, and plato-room-intelligence from any README/wiki that says they're published packages. They don't exist on PyPI.

## Task 3: keel command count discrepancy — N/A

Both keel repos are **archived stubs** with no actual CLI or commands:
- `SuperInstance/keel` — archived, points to itself circularly
- `SuperInstance/keel-early-version` — archived, "benchmarks were fabricated"

No command count claims exist to fix. These are dead repos.

## Summary

| Task | Status | Action Taken |
|------|--------|-------------|
| fleet-spread tests | ✅ Fixed | 147 → 133, pushed |
| Package verification | ✅ Verified | 3/6 confirmed, 3 don't exist on PyPI |
| keel commands | ⚠️ N/A | Repos are archived stubs, nothing to fix |
