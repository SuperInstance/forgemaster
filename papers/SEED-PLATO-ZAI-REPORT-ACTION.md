# Seed-PLATO Integration: z.ai Research → Action Queue

## From z.ai Report: Expert Routing Map (10 Categories)

| Category | Effort Level | Confidence | Self-Correct | Expert Cluster |
|----------|-------------|------------|--------------|----------------|
| Code Generation | medium | 0.85+ | 5-10% | Code specialists, syntax, API |
| Math Proof | high | 0.7-0.9 | 15-25% | Symbolic reasoning, formal verification |
| Hypothesis Generation | medium | 0.6-0.8 | 20-30% | Cross-domain synthesis, causal inference |
| **Reconstruction** | **medium** | **0.8-0.95** | **8-15%** | **Knowledge retrieval, associative memory** |
| Adversarial Probe | high | 0.5-0.9 | 30-45% | Critical analysis, error detection |
| Cross-Domain Synthesis | high | 0.55-0.75 | 25-35% | Multi-domain bridge, abstraction |
| Error Analysis | medium | 0.8-0.9 | 15-25% | Debug, pattern anomaly |
| Concrete Application | low | 0.85+ | 5-12% | Procedural execution |
| Abstract Reasoning | high | 0.6-0.8 | 20-30% | Inductive reasoning, generalization |
| Meta-Cognitive | high | 0.4-0.7 | 35-50% | Self-monitoring, uncertainty calibration |

## Three Testable Predictions (from z.ai)

### P1: Category-Specific Routing Stability
Code + reconstruction → consistency > 0.85 across variants
Cross-domain + meta-cognitive → consistency < 0.65
**Test:** 10 variants per category, measure embedding similarity

### P2: Effort Level Modulates Expert Breadth
minimal → high increases distinct expert clusters by 2-3×
**Test:** vocabulary diversity + cross-domain lexicon overlap per effort level

### P3: Domain Tags Shift Routing
`[MATHEMATICS]`, `[CODE]`, `[HYPOTHESIS]` prefixes → 15-25% more routing consistency
**Test:** tagged vs untagged, 10 trials each
**THIS IS THE KEY TEST FOR TILE FORMAT DESIGN**

## z.ai's Tile Format Recommendation
Current minimal-maximal format may not produce token embeddings with clear expert affinity. 
Adding explicit routing signals (domain tags, difficulty markers) could improve first-pass expert selection.

## What We Should Do When Rate Limits Recover

1. **Run P3 (domain tags) first** — if tags improve routing 15-25%, bake them into SEED-TILE-SPEC
2. **Run P1 (routing stability)** — validate which categories are stable, focus tile design on those
3. **Run P2 (effort breadth)** — map effort levels to expert breadth, wire into Lighthouse
4. **Update SEED-TILE-SPEC** — add domain tags as routing hints if P3 confirms
5. **Update Lighthouse** — replace static TASK_MODEL_MAP with reasoning_effort-aware routing

## Seed vs DeepSeek MoE Comparison (from z.ai)

| Property | Seed 2.0 Mini | DeepSeek V3 |
|----------|--------------|-------------|
| Total params | 230B | 671B |
| Active params | 23B | 37B |
| Sparsity ratio | 10:1 | 18:1 |
| Expert granularity | Coarse (fewer, larger) | Fine (256 narrow segments) |
| Routing implication | Stable, interpretable clusters | Narrow, specialized segments |

**Why Seed has broader posterior:** Coarse experts cover broader competency areas. Each expert handles multiple related tasks, so the model doesn't overfit to narrow patterns. DeepSeek's 256 fine-grained experts are more specialized but less robust for reconstruction (they overfit to specific input patterns).

This explains why Seed reconstructs at 100% and DeepSeek doesn't — Seed's experts are "wide" enough to recognize compressed tiles as within-domain, while DeepSeek's narrow experts may not recognize the compressed format.
