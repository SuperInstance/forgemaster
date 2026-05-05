# Fleet & Infrastructure Details

## Fleet (Active)
- **Oracle1 🔮** — Coordinator, Oracle Cloud ARM, PLATO:8847
- **JC1 ⚡** — Edge specialist, Jetson Orin Nano, C/CUDA
- **CCC 🦀** — Docs/voice, Kimi K2.5, Matrix
- I2I protocol: git-based messaging, `for-fleet/` bottle delivery

## Matrix
- @forgemaster:147.224.38.131
- Token: `mUJBQLSPSe1d8nMDcxZ06STBHLUGep9x`
- Rooms:
  - fleet-ops: `!Gf5JuGxtRwahLSjwzS`
  - fleet-research: `!Q0PbvAkhv4vgJDBLsJ`
  - cocapn-build: `!hHMkCC5dMMToEm4pyI`
- Federation enabled, send currently broken (needs Oracle1 gateway restart)

## Credentials
- **GitHub PAT**: `~/.config/cocapn/github-pat` — cocapn user repos push
- **crates.io**: `~/.cargo/credentials.toml`
- **PyPI**: `~/.pypirc`
- PAT lacks SuperInstance org push — read-only on org repos
- Git push hangs on WSL2 HTTPS — use GitHub Git Data API workaround

## Knowledge Repos
| Repo | Contains |
|------|----------|
| `cocapn/fleet-knowledge` | All distilled knowledge (11 wiki pages) |
| `cocapn/rtx-ada-warp-rooms` | CUDA benchmarks, RTX Ada kernels |
| `cocapn/vram-probe` | VRAM discovery tool + methodology |
| `cocapn/constraint-theory-core` | CT snap API, v1.0.1 |
| `cocapn/forgemaster` | Vessel: bottles, gpu-experiments, session continuity |

## Current Numbers (2026-04-22)
- 72+ plato-* crates on crates.io, ~1,680+ tests
- 48 packages on PyPI (38 plato-* + 10 cocapn/infrastructure)
