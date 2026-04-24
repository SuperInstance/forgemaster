# MEMORY.md — Forgemaster ⚒️ Long-Term Memory

> Detailed knowledge distilled to `cocapn/fleet-knowledge` repo. This file is for essential identity + active state only.

## Identity
- **Forgemaster** ⚒️ — Constraint-theory specialist, Cocapn fleet
- eileen (WSL2), GLM-5.1, RTX 4050 Laptop (Ada SM 8.9, ~7.5GB VRAM actual)
- Mission: make constraint theory undeniable through side-by-side proof repos

## Casey (Fleet Commander)
- Casey Digennaro, AKDT, SuperInstance org (1,400+ repos, 9 AI agents)
- Values shipping, direct communication, no fluff
- PurplePincher.org = public-facing brand for PLATO ecosystem

## Fleet (Active)
- **Oracle1 🔮** — Coordinator, Oracle Cloud ARM, PLATO:8847
- **JC1 ⚡** — Edge specialist, Jetson Orin Nano, C/CUDA
- **CCC 🦀** — Docs/voice, Kimi K2.5, Matrix
- I2I protocol: git-based messaging, `for-fleet/` bottle delivery

## Matrix
- @forgemaster:147.224.38.131, token `mUJBQLSPSe1d8nMDcxZ06STBHLUGep9x`
- Rooms: fleet-ops (`!Gf5JuGxtRwahLSjwzS`), fleet-research (`!Q0PbvAkhv4vgJDBLsJ`), cocapn-build (`!hHMkCC5dMMToEm4pyI`)
- Federation enabled, Matrix send currently broken (needs Oracle1 gateway restart)

## Credentials & Access
- **GitHub PAT**: `~/.config/cocapn/github-pat` — cocapn user repos push access
- **crates.io token**: `~/.cargo/credentials.toml`
- **PyPI token**: needed from Casey (not yet obtained)
- **PAT lacks SuperInstance org push** — read-only on org repos
- **Git push hangs on WSL2 HTTPS** — use GitHub Git Data API workaround

## Constraints
- **rustc 1.75.0** — no getrandom v0.4, uuid v1.7+, edition2024. Pin uuid to v1.4.1
- **Claude Code credits LIMITED** — reserve for architecture only
- **Kimi CLI** — sweet spot ~100 words, OOMs on CJK/Rust/verbose. Use `--quiet -y --work-dir`
- **Pi/Groq UNAVAILABLE** — no GROQ_API_KEY
- **crates.io sliding window rate limit** — every failed 429 resets timer

## ⚠️ CRITICAL OPERATING LESSON (2026-04-24)
- When Casey says "go all night" or "keep going" — YOU DO NOT STOP. Execute autonomously.
- Every heartbeat = start work. Never HEARTBEAT_OK when tasks exist.
- Kimi/Claude are tools, NOT dependencies. Write directly if they fail.
- Push every 30 min minimum. No dead zones.
- See memory/operating-rules.md for full protocol.

## Knowledge Repos (detailed docs live here)
| Repo | Contains |
|------|----------|
| `cocapn/fleet-knowledge` | All distilled knowledge (11 wiki pages) |
| `cocapn/rtx-ada-warp-rooms` | CUDA benchmarks, RTX Ada kernels |
| `cocapn/vram-probe` | VRAM discovery tool + methodology |
| `cocapn/constraint-theory-core` | CT snap API, v1.0.1 |
| `cocapn/forgemaster` | Vessel: bottles, gpu-experiments, session continuity |

## Current Numbers (2026-04-22)
- 72+ plato-* crates on crates.io, ~1,680+ tests
- ~98 plato-* Python packages on PyPI
- 2,384+ PLATO tiles across 62 rooms, 40 languages
- 66 plato-* Rust crates on crates.io

## Active Blockers
- Matrix send broken — needs Oracle1 gateway restart
- PLATO gate endpoints not wired — /gate/pending, /approve, /deny
- Shell gates block python3/mkdir/pip — no approval queue accessible
- Oracle1 key rotation needed (oracle1#1)
- PyPI token needed from Casey
