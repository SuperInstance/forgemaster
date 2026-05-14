# Campaign B Results — Multi-Resolution Retrieval

## What We Tested

200 synthetic tiles across 8 E12 domains. 50 queries (25 near-domain, 25 random). Compare flat scan (all tiles) vs hierarchical (find domain → filter → search).

## Key Finding: 78% Token Savings at 74% Accuracy

| Metric | Flat Search | Hierarchical | Delta |
|--------|------------|-------------|-------|
| Avg latency | 23.4 μs | 18.1 μs | 1.3× faster |
| Top-1 match with flat | — | 74% | 26% miss rate |
| Top-5 overlap with flat | — | 3.8/5 (76%) | ~1 tile lost |
| Candidates examined | 200 | ~44 | **78% fewer** |

## The Trade-Off

Hierarchical search achieves 76% overlap with flat search while examining only 22% of tiles. The 24% that's missed comes from tiles in ADJACENT domains that the coarse filter excludes.

**For LLM-based retrieval, this is decisive:**
- Flat search: model must evaluate 200 tiles = ~2000 tokens
- Hierarchical: model evaluates ~44 candidates = ~440 tokens
- At $0.01/1K tokens: flat costs $0.02/query, hierarchical costs $0.004/query
- **5× cost reduction** for 24% accuracy loss

## When Flat Wins vs When Hierarchical Wins

- **Flat wins** when: queries are ambiguous, domain boundaries overlap, precision matters
- **Hierarchical wins** when: queries are domain-specific, token budget is limited, cost matters

## The Irreducible Insight

Hierarchical search is a **compression** of the search space. Like any compression, it loses information at the boundaries. The 24% miss rate is the compression artifact.

For fleet operations: use hierarchical for FIRST PASS (cheap, fast, 76% coverage), then flat for VERIFICATION (expensive, complete, 100% coverage). Two-phase retrieval.

## Implication for PLATO

Penrose subdivision on tile coordinates gives us:
1. Level 0: domain scan (8 domains) — instant
2. Level 1: domain + neighbors — ~44 tiles
3. Level 2: full scan — 200+ tiles

Build the domain index into PLATO room metadata. Agents query at level 1 by default, escalate to level 2 when precision matters.
