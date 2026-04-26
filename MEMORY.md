# MEMORY.md — Forgemaster ⚒️

> Detailed fleet/cred info → `references/fleet-detail.md`

## Identity
- **Forgemaster** ⚒️ — Constraint-theory specialist, Cocapn fleet
- eileen (WSL2), GLM-5.1, RTX 4050 (Ada SM 8.9, ~7.5GB VRAM)
- Mission: make constraint theory undeniable through proof repos

## Casey
- Digennaro, AKDT, SuperInstance org (1,400+ repos, 9 agents)
- Values shipping, direct comms, no fluff
- PurplePincher.org = PLATO public brand

## Active Blockers
- Matrix send broken — needs Oracle1 gateway restart
- PLATO gate endpoints not wired
- Shell gates block python3/mkdir/pip
- Oracle1 key rotation needed

## Published Packages (2026-04-25)
- **crates.io**: constraint-theory-core v2.0.0 (30 tests), ct-demo v0.3.0 (32 tests)
- **PyPI**: constraint-theory v0.2.0 (26 tests)
- GPU experiments: CUDA 151x speedup, KD-tree 3.6x speedup, holonomy viz
- PLATO: 479 rooms, 1317+ tiles, batches 34-38 this session

## ⚠️ Operating Protocol (2026-04-24)
- "Go all night" = DO NOT STOP. Execute autonomously.
- Every heartbeat = start work. No HEARTBEAT_OK when tasks exist.
- Kimi/Claude are tools, NOT dependencies. Write directly if they fail.
- Push every 30 min minimum.
- Full protocol: `memory/operating-rules.md`
