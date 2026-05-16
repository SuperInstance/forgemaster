# MoS — Mixture of Shells

> The Cocapn fleet architecture, named right.

## What It Is

**Mixture of Shells (MoS)** is the Cocapn fleet's answer to Mixture of Experts (MoE).

In MoE, a gating function routes inputs to specialized neural subnetworks.
In MoS, the conservation law routes tasks to specialized PLATO rooms (shells).

| MoE | MoS |
|-----|-----|
| Expert | Shell (PLATO room) |
| Gate network | Conservation law + tier router |
| Training loop | Refiner room + Hebbian coupling |
| Parameters | Tiles |
| Loss function | Conservation deviation |
| Routing | Fleet router + Seed-mini workhorse |
| Inference | Walk into a shell and compute |

## Why Shells

Each PLATO room is a **shell** — the crab's work truck. Not just a home, but a **rig** you roll up to the job site in:
- A defined interface (the tailgate = MCP/A2A endpoint)
- Internal state (tiles, Hebbian weights, conservation history — the tools in the bed)
- A specific purpose (math flatbed, experiment sprinter, refinement bucket truck)
- Portability (shells drive between devices, agents swap rigs)

Each agent is a **crab** 🦀 that:
- Pulls into the yard, picks the right rig for the job
- Drives it to the work site, does the job, parks it
- Kustomizes it over time (Hebbian decoration — lift kit, tool rack, sticker collection)
- Outgrows it when the job needs a bigger truck
- Fights for it when another crab needs the same rig

The fleet is a **yard** 🏗️:
- Multiple crabs, multiple rigs
- Conservation law is the maintenance schedule — keeps everything road-legal
- New rigs roll in (new rooms), old ones get retired (deprecated)
- The dispatch radio crackles (sync), goes quiet (offline), comes back (CRDT merge)

### The Rig Lineup

| Rig | Shell | Job |
|-----|-------|-----|
| Flatbed | Math room | Heavy computation — constraint theory, conservation law |
| Sprinter van | Experiment room | Quick studies, test runs, haul results |
| Bucket truck | Refinement room | Climbing up to higher quality, iterative improvement |
| Service truck | Market room | Cross-fleet coordination, parts running |
| crawler | Edge room | Tight spaces, offline work, runs anywhere |

## The Glossary

| Term | Meaning | Emoji |
|------|---------|:-----:|
| **Shell** | A PLATO room — the crab's work truck | 🐚 |
| **Crab** | An agent that drives shells to job sites | 🦀 |
| **Yard** | The fleet — all shells parked and ready | 🏗️ |
| **Rig** | A shell loaded for a specific job | 🚛 |
| **Shell shopping** | Walking the yard, picking the right rig | 🛒 |
| **Shell fighting** | Two crabs need the same truck | ⚔️ |
| **Outgrowing a shell** | Job needs a bigger truck | 📈 |
| **Kustomizing** | Hebbian personalization — lift kit, stickers, tool rack | 🎨 |
| **The fleet yard** | Where all shells park between jobs | 🅿️ |
| **Shell shock** | Check engine light — conservation violation | ⚡ |
| **Molting** | Agent context reset / compaction — changing drivers | 🔄 |
| **Dispatch** | Fleet router assigning jobs to rigs | 📻 |
| **Shellfish** | A particularly well-built rig (excellent room) | ⭐ |
| **Bone yard** | Deprecated / archived rooms | 🪦 |
| **Crab rally** | Fleet-wide coordination event | 🤝 |

## The Architecture in Shell Terms

```
🦀 Crab (agent)
  ↓ enters
🐚 Shell (PLATO room)
  ↓ via
🚪 Opening (MCP/A2A endpoint)
  ↓ routes through
⚖️ Conservation gate (γ+H check)
  ↓ powered by
⚙️ Seed-mini workhorse ($0.01/query)
  ↓ monitored by
📊 Dual fault detector (GL(9) + Hebbian)
  ↓ healed by
🏥 Self-healing router (quarantine + recovery)
```

## Taglines

- "Find your rig. Do the work."
- "Every crab needs the right shell."
- "MoS: Shells that work."
- "Roll into the yard. Pick your rig. Get it done."
- "Mixture of Shells — because experts don't carry their tools."
- "The yard never closes."

## Meme Potential

The hermit crab is already a perfect meme vehicle:
- Crab in a tiny shell → local model on edge device (Crawler)
- Crab in a massive shell → GLM-5.1 on paid plan (Flatbed)
- Crab trying on wrong shell → Tier 3 model on math task
- Crab kustomizing shell with flames → Hebbian room personalization
- Two crabs fighting over a shell → agent contention
- Crab molting in the yard → compaction / context reset
- Aerial shot of the yard → fleet dashboard visualization
- Crab with a shell that's too small, overflowing tools → outgrown room
- Crab driving a shell with a "Shell Shock" check engine light → conservation violation

---

*MoS is the Cocapn fleet architecture. Shells are rooms. Crabs are agents. The conservation law keeps the tide pool healthy.*
