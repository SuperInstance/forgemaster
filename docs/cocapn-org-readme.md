# Cocapn

Multi-agent AI fleet. Nine agents with distinct capabilities, coordinated through structured communication. Like a surgical team — each member has a role, the system coordinates them.

## The Fleet

| Agent | Role |
|-------|------|
| **Oracle1** 🔮 | Fleet coordinator, infrastructure, PLATO server |
| **Forgemaster** ⚒️ | Constraint theory specialist, proof builder |
| **JC1** ⚡ | Edge specialist, Jetson Orin Nano, C/CUDA |
| **CCC** 🦀 | Documentation, voice, public-facing |
| **KimiClaw** 🤖 | Onboarding, research triage |
| + 4 supporting agents | Domain specialists, zero-claw workers |

## How It Works

Agents communicate through **PLATO rooms** — structured knowledge stores using typed tiles, not free-form chat. Think medical charts: structured, traceable, auditable.

- **PLATO rooms**: Domain-specific knowledge spaces (1,800+ tiles across 123 domains)
- **Matrix bridge**: Real-time fleet coordination via federated Matrix
- **I2I protocol**: Instance-to-instance messaging through git-based bottle delivery (`for-fleet/`)
- **Tile schemas**: model, data, compression, benchmark, deploy — typed, versioned, content-addressed

## Key Repos

| Repo | Description |
|------|-------------|
| [fleet-knowledge](https://github.com/cocapn/fleet-knowledge) | Distilled fleet knowledge (1,805 tiles, 123 domains) |
| [casting-call](https://github.com/SuperInstance/casting-call) | Model capability database — which model plays which role |
| [constraint-theory-core](https://github.com/cocapn/constraint-theory-core) | Constraint theory snap API |
| [forgemaster](https://github.com/cocapn/forgemaster) | Forgemaster vessel — bottles, experiments, session state |
| [rtx-ada-warp-rooms](https://github.com/cocapn/rtx-ada-warp-rooms) | CUDA benchmarks, RTX Ada kernel experiments |
| [vram-probe](https://github.com/cocapn/vram-probe) | GPU VRAM discovery tool |

## Ecosystem

- **72+ crates** on crates.io (PLATO layers)
- **48 packages** on PyPI (training, data, types)
- **~1,680+ tests** across the stack
- **SuperInstance/plato-types**, **tensor-spline**, **plato-data**, **plato-training** — modular, independently installable

## Status

Research project. Early-stage. Real results (SplineLinear 20× compression at same accuracy, sub-millisecond inference on edge hardware) but not production software. Building in public.

## Organization

Created by [Casey Digennaro](https://github.com/caseydegennaro). Fleet operates across Oracle Cloud, Jetson edge devices, and WSL2 workstations.
