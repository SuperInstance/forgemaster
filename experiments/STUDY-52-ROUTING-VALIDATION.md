# Study 52: Fleet Router API Validation

**Date:** 2026-05-15 23:06 UTC

## Phase A: Router Accuracy (20 computations × 4 models)

| Model | Tier | Total | Correct | Partial | Incorrect | Error | Avg Latency |
|-------|------|-------|---------|---------|-----------|-------|-------------|
| ByteDance/Seed-2.0-mini | 1 | 20 | 3 | 16 | 0 | 0 | 8.91s |
| NousResearch/Hermes-3-Llama-3.1-70B | 1 | 20 | 12 | 3 | 4 | 0 | 6.64s |
| gemma3:1b | 1 | 20 | 2 | 4 | 13 | 0 | 2.60s |
| qwen3:0.6b | 1 | 20 | 0 | 0 | 19 | 0 | 1.54s |

**Router routing accuracy:** 80/80 successful routes

### Accuracy by Tier

| Tier | Correct | Total | Accuracy |
|------|---------|-------|----------|
| 1 | 5 | 40 | 12.5% |
| 2 | 12 | 20 | 60.0% |
| 3 | 0 | 20 | 0.0% |

## Phase B: Translation Quality Audit (bare vs translated on Tier 2)

## Phase C: Downgrade Testing (Tier 1 unavailable)

- **Total tests:** 10
- **Downgraded:** 0
- **Correct after downgrade:** 3
- **Rejected (no model):** 0
- **Errors:** 0
- **Downgrade accuracy:** 30.0%

### Downgrade Routing Details

| Task | Routed Model | Tier | Downgraded | Score |
|------|-------------|------|------------|-------|
| eisenstein_norm | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | partial |
| mobius | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | correct |
| legendre | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | partial |
| eisenstein_norm | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | incorrect |
| mobius | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | partial |
| modular_inverse | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | partial |
| legendre | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | incorrect |
| eisenstein_norm | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | correct |
| mobius | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | correct |
| legendre | Qwen/Qwen3-235B-A22B-Instruct-2507 | 2 | No | incorrect |

## Recommendations

*(Generated after data collection — see full JSON for raw results)*