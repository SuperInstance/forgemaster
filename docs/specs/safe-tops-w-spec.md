# Safe-TOPS/W Benchmark Metric — Specification v1.0

## Definition

**Safe-TOPS/W** measures verified inference throughput per watt, weighted by certified correctness coverage:

```
Safe-TOPS/W = (C_certified × TOPS) / W
```

Where:
- `TOPS` — peak tera-operations per second (measured)
- `W` — sustained power draw under load (watts)
- `C_certified ∈ [0, 1]` — proof coverage fraction: proportion of computational paths with machine-verified correctness guarantees

## Axioms

| # | Name | Statement |
|---|------|-----------|
| A1 | **Monotone** | Increasing `C_certified` never decreases Safe-TOPS/W |
| A2 | **Zero-Default** | If `C_certified = 0`, then Safe-TOPS/W = 0, regardless of raw TOPS |
| A3 | **Sound** | `C_certified` may only be claimed via a mechanically checked proof artifact (Coq, Lean, Isabelle, or equivalent) |
| A4 | **Composable** | For a pipeline of `n` stages: `C_certified = ∏ᵢ C_i`; Safe-TOPS/W degrades multiplicatively with uncertified stages |

## Measurement Protocol

**Step 1 — Measure TOPS and W**
Run the target workload (e.g., INT8 matrix multiply, BF16 attention) at sustained throughput. Record peak TOPS and mean power draw W over a 60-second window under thermal steady-state.

**Step 2 — Compute C_certified**
Enumerate all distinct logical paths executed by the workload kernel. For each path, check whether a proof artifact exists that covers it. `C_certified = (certified paths) / (total paths)`. Proofs must be deposited in a verifiable artifact registry with a content-addressed hash.

**Step 3 — Report**
Publish the triple `(TOPS, W, C_certified)` alongside the proof registry URL and hardware revision. Safe-TOPS/W is derived, not self-reported.

## Comparison Table

| Platform | TOPS | W | C_certified | Safe-TOPS/W |
|----------|------|---|-------------|-------------|
| FLUX (verified) | 73 | 15 | 0.97 | 4.73 |
| GPU (uncertified) | 500 | 400 | 0.00 | **0.00** |
| CPU (uncertified) | 8 | 65 | 0.00 | **0.00** |
| GPU + partial proof | 500 | 400 | 0.31 | 0.39 |

A2 (Zero-Default) ensures that raw TOPS claims carry no weight without proof coverage.

## Certification Levels

| Level | Requirement | Badge |
|-------|-------------|-------|
| **Bronze** | `C_certified ≥ 0.50` | Majority of paths covered |
| **Silver** | `C_certified ≥ 0.90` | Near-complete path coverage |
| **Gold** | `C_certified ≥ 0.97` + composable across full stack | End-to-end verified pipeline |

Gold requires that A4 holds across all pipeline stages: the certified fraction of every upstream component multiplies into the final score. No single uncertified layer may be masked by downstream proofs.
