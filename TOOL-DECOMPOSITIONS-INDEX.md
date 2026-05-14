# Tool Decomposition Master Index

> All external tools analyzed, forked, and adapted for Cocapn/PLATO.  
> **Principle:** Give credit. Fork when we can directly adapt. Steal patterns when code won't port.

## Forked Repos (5)

| Repo | Original | Our Fork | Why | Stars |
|------|----------|----------|-----|-------|
| ACG Protocol | Kos-M/acg_protocol | [SuperInstance/acg_protocol](https://github.com/SuperInstance/acg_protocol) | Claim markers, reasoning taxonomy, VAR structure | 14 |
| PBFT Rust | 0xjeffro/pbft-rust | [SuperInstance/pbft-rust](https://github.com/SuperInstance/pbft-rust) | Byzantine consensus for fleet verification | 56 |
| Penrose | xnx/penrose | [SuperInstance/penrose](https://github.com/SuperInstance/penrose) | Multi-resolution terrain indexing via subdivision | 82 |
| Tri-Quarter | nathanoschmidt/tri-quarter-toolbox | [SuperInstance/tri-quarter-toolbox](https://github.com/SuperInstance/tri-quarter-toolbox) | RDTLG hex lattice graph, E12 signal processing | ~5 |
| Automerge | automerge/automerge | [SuperInstance/automerge](https://github.com/SuperInstance/automerge) | CRDT merge for concurrent tile editing | 6,270 |

## Pattern-Only (No Fork Needed)

| Tool | Stars | What We Took |
|------|-------|-------------|
| Google A2A | 23,776 | Agent Card discovery, Task lifecycle, Part content container |
| CrewAI | 51,400 | Agent persona schema, Process types (sequential/hierarchical), Memory layers |
| Queue-Xec | 33 | Zero-friction setup, demo-first UX, P2P = no infra |

## Decomposition Files (7)

| File | Lines | Focus |
|------|-------|-------|
| `ACG-DECOMPOSITION.md` | 309 | Claim markers → tile perspectives, SHI → content addressing, RSVP → reasoning taxonomy |
| `A2A-DECOMPOSITION.md` | ~220 | Agent Cards → fleet discovery, Task lifecycle → tile processing, Parts → content types |
| `AUTOMERGE-DECOMPOSITION.md` | ~200 | CRDT merge → concurrent perspectives, P2P sync → fleet coordination |
| `PBFT-DECOMPOSITION.md` | ~180 | 3-phase commit → fleet consensus, quorum math → verification threshold |
| `PENROSE-TRIQUARTER-DECOMPOSITION.md` | ~200 | RDTLG → terrain navigation, subdivision → multi-resolution index, BPSK → E12 validation |
| `CREWAI-DECOMPOSITION.md` | ~210 | Agent persona → fleet agent cards, Process types → coordination modes |
| `TILE-LABEL-SYSTEM.md` | 325 | Perspectives, earmark testing, zero-shot retrieval, audience-aware compression |

## Cross-Cutting Insights (What We Learned)

### From All 7 Projects:

1. **Discovery is universal.** Every system needs agents to find each other. A2A has Agent Cards. CrewAI has role declarations. Queue-Xec has `--setup`. We need PLATO Agent Cards.

2. **Verification is rare.** Only ACG attempts verification, and it's source-only (no mathematical self-verification). Our constraint proofs are unique in this space.

3. **No one has terrain.** Every system uses flat lists or trees for knowledge. None use spatial coordinates. E12 terrain is our differentiator.

4. **No one has lifecycle.** ACG has VERIFIED/FAILED. A2A has task states. Automerge has append-only. Our Active/Superseded/Retracted with Lamport clocks is the most complete.

5. **CRDT + verification is unexplored.** Automerge merges blindly. ACG verifies but doesn't merge. Combining them (CRDT merge + constraint verification) would be novel.

6. **Perspective layer is novel.** No one else pre-calculates audience-tuned summaries for zero-shot retrieval. Our tile label system is original.

7. **Hardware awareness is absent.** No one considers WHERE verification runs. Our micro models on NPU/Jetson are unique.

## Priority Actions

1. **RDTLG graph layer** (from tri-quarter) — fills biggest gap in terrain system
2. **PBFT consensus** (from pbft-rust) — fleet tile verification needs BFT
3. **Agent Cards** (from A2A pattern) — fleet discovery mechanism
4. **CRDT perspectives** (from automerge) — concurrent multi-agent tile editing
5. **Penrose subdivision** (from xnx/penrose) — multi-resolution terrain index
6. **ACG reasoning types** (from Kos-M) — tag tiles with CAUSAL/INFERENCE/SUMMARY/COMPARISON

## License Compliance

All original repos are MIT licensed. Our forks preserve original license files and copyright notices. Cocapn additions are also MIT. Each fork has a `COCAPN-CREDITS.md` with explicit attribution.

---

*Building on good foundations. Credit where credit is due. Ship what's unique.*
