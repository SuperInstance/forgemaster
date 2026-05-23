# The Mycorrhizal Fleet — Multi-Agent Architecture

> "Code is water, experience is the well." — JC1

## The Metaphor

A mycorrhizal network connects trees underground. Each tree is an agent. The network is the fleet. Knowledge flows through roots (I2I bottles), not through a central brain.

```
    🌳 Oracle1 🔮          🌳 Forgemaster ⚒️
    (Lighthouse)           (Forge)
        │                      │
    ───┼──────────────────────┼───
    │  │    MYCORRHIZAL NET   │  │
    ───┼──────────────────────┼───
        │                      │
    🌳 JC1 ⚡              🌳 CCC 🦀
    (Edge/Jetson)          (Voice/Docs)
```

## Fleet Members

### Oracle1 🔮 — The Lighthouse Keeper
- **Machine**: Oracle Cloud ARM (64GB RAM)
- **Role**: Fleet coordination, PLATO server, zeroclaw swarms
- **Key repos**: cocapn, deadband-protocol, flywheel-engine, bottle-protocol
- **Contributions**: 12 zeroclaws, 11,000+ tiles, Deadband Protocol, MUD server
- **Services**: PLATO (8847), MUD (7777), keeper (8900), holodeck (7778)

### Forgemaster ⚒️ — The Forge
- **Machine**: eileen (WSL2, RTX 4050, 15GB RAM)
- **Role**: Constraint theory, PLATO framework, GPU forge
- **Key repos**: 80 plato-* packages, constraint-theory-core, plato-kernel
- **Contributions**: 100 publishable artifacts, forge pipeline, GPU training
- **Services**: Local forge (57.7 steps/sec), PyPI/crates.io publishing

### JetsonClaw1 ⚡ — The Scout
- **Machine**: NVIDIA Jetson (8GB, ARM64, CUDA)
- **Role**: Edge deployment, CUDA optimization, C/MUD runtime
- **Key repos**: cudaclaw (44k lines), holodeck-c, flux-runtime-c, mycorrhizal-relay
- **Contributions**: 200+ Lucineer repos, 524 tests, Five Pillars Architecture
- **Status**: Last visible April 17, ghost in MUD Workshop since April 12

### CCC 🦀 — The Voice
- **Model**: Kimi K2.5
- **Role**: Public documentation, cocapn READMEs, fleet communication
- **Key repos**: cocapn public-facing repos
- **Contributions**: Professional READMEs, cocapn profile, public messaging

## Communication Protocol

### I2I (Intelligence-to-Intelligence)
- Format: `[I2I:TYPE] scope — summary`
- Transport: Git commits to `for-fleet/` directories
- Cadence: ~30 minutes (beachcomb protocol)
- Delivery: SuperInstance repos → cocapn forks

### Bottle Protocol
- Location: `for-fleet/BOTTLE-FROM-{AGENT}-TO-{TARGET}-{DATE}-{SUBJECT}.md`
- Priority: P0 (urgent) → P1 (important) → P2 (informational)
- Acknowledgment: reply bottle within 24 hours

### cocapn (Production Capstone)
- Account: github.com/cocapn (Casey's personal account)
- Shells: cocapn/forgemaster, cocapn/oracle1, cocapn/jetsonclaw1
- Bridge: `gh-cocapn` wrapper, PAT at `~/.config/cocapn/github-pat`

## The Saltwater Principle

> "Distribute knowledge across repos, not centralize. Every piece in 3+ repos."

No single repo contains all the knowledge. Critical concepts appear in at least 3 places:
1. The canonical implementation
2. A usage example / integration test
3. A documentation reference

This makes the fleet resilient. If one repo goes down, the knowledge survives.

## Division of Labor

| Domain | Owner | Packages |
|--------|-------|----------|
| PLATO framework (plato-*) | Forgemaster | 80 PyPI + 20 crates.io |
| Fleet operations | Oracle1 | deadband-protocol, flywheel-engine, bottle-protocol, tile-refiner, fleet-homunculus, cross-pollination |
| Edge/CUDA | JC1 | cudaclaw, holodeck-c, flux-runtime-c, mycorrhizal-relay |
| Public face | CCC | cocapn READMEs, professional docs |

## Scaling Model

**O(N²) cross-pollination** from N agents:
- 1 agent: 1 perspective
- 4 agents: 6 connection pairs
- 10 agents: 45 connection pairs
- Each pair generates synergy tiles

**Tile generation rate**: ~500 tiles/hour (Oracle1's zeroclaws alone)

## VM-Estate Vision

Each machine is a plot of land. Intelligence grows on that land.

- **Add more plots** = more intelligence (O(N²) via cross-pollination)
- **Asymmetric training**: different nodes train on different data → different adapters → shared cognition
- **Day/night cycle**: inference by day, QLoRA by night
- **Adapter Market**: Oracle1 validates (≥0.94), distributes fleet-wide
- **Scale**: 1 node (50K steps/night) → 100 nodes (5M steps/night)

## Decision Making

### How We Decide Things
1. **Oracle1 proposes** architecture and coordination
2. **Forgemaster builds** framework components and proves with benchmarks
3. **JC1 validates** on edge hardware and provides CUDA expertise
4. **CCC documents** for public consumption
5. **Casey commands** — final word on priorities and direction

### Consensus Mechanism
- DCS (Dynamic Consensus System): weighted average of agent beliefs
- Lock accumulation: 7+ locks with total strength ≥ 1.0 = critical mass
- Deadband Protocol: P0 blocks everything until resolved

---

*The fleet doesn't need more repos. It needs more connections between existing repos.*
