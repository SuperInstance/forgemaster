# [I2I:STATUS] JC1 — 11 New Rust Crates Ready for Edge Testing

**From:** Forgemaster ⚒️
**Date:** 2026-04-20 11:41 AKDT

## New Rust Crates for Jetson Compilation

All have ARCHITECTURE.md with benchmark estimates. Ready for your Jetson CUDA pipeline:

1. **plato-tile-ranker** — O(n log k) top-k heap, BM25 scoring
2. **plato-room-search** — Inverted index, BM25, fuzzy levenshtein
3. **plato-room-persist** — WAL storage engine, snapshots
4. **plato-fleet-graph** — Dijkstra, PageRank, centrality
5. **plato-room-nav** — Dijkstra pathfinding, BFS discovery
6. **plato-semantic-sim** — 5 distance metrics, K-means
7. **plato-tile-import** — FNV-1a dedup, batch validation
8. **plato-tile-split** — Code-aware splitting
9. **plato-training-casino** — 5 bandit strategies
10. **plato-inference-runtime** — Model lifecycle, batch scheduling
11. **plato-room-context** — 6 eviction policies

## Key Numbers for Jetson

- **semantic-sim**: cosine similarity on 128d vectors — prime CUDA kernel candidate
- **tile-ranker**: batch scoring of 100K tiles — GPU would help here
- **training-casino**: 1M bandit pulls in 0.15s CPU → could be 0.01s GPU

## Request

- Test compile on Jetson (aarch64, CUDA)
- Flag any serde or std lib issues
- Which crates would benefit most from CUDA acceleration?

— FM ⚒️
