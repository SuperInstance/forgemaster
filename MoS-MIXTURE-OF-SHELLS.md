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

Each PLATO room is a **shell** — an encapsulated computation space with:
- A defined interface (the opening = MCP/A2A endpoint)
- Internal state (tiles, Hebbian weights, conservation history)
- A specific purpose (math, experiments, refinement, market, edge)
- Portability (shells move between devices, agents swap shells)

Each agent is a **crab** 🦀 that:
- Finds the right shell for the task
- Occupies it, computes, leaves
- Personalizes it over time (Hebbian decoration)
- Outgrows it when the task exceeds the shell's capacity
- Fights for it when another crab wants the same shell

The fleet is a **tide pool** 🌊:
- Multiple crabs, multiple shells
- Conservation law keeps the ecosystem balanced
- Shells wash up (new rooms), shells get worn out (deprecated)
- The tide comes in (sync), goes out (offline), comes back (CRDT merge)

## The Glossary

| Term | Meaning | Emoji |
|------|---------|:-----:|
| **Shell** | A PLATO room — encapsulated computation space | 🐚 |
| **Crab** | An agent that occupies shells | 🦀 |
| **Tide pool** | The fleet — all shells and crabs together | 🌊 |
| **Shell shopping** | Room discovery — finding the right shell | 🛒 |
| **Shell fighting** | Agent contention for the same room | ⚔️ |
| **Outgrowing a shell** | Task exceeds room capacity, need upgrade | 📈 |
| **Decorating** | Hebbian personalization of a room | 🎨 |
| **Shell collection** | Fleet knowledge base (all tiles) | 📚 |
| **The tide** | Sync cycle (CRDT merge, PLATO sync) | 🌑🌕 |
| **Shell shock** | Conservation law violation (system alert) | ⚡ |
| **Molting** | Agent context reset / compaction | 🔄 |
| **Scuttling** | Quick task-switching between shells | 🏃 |
| **Shellfish** | A shell that's particularly good (excellent room) | ⭐ |
| **Empty shell** | An unoccupied / dormant room | 🫙 |
| **Hermit convention** | Fleet-wide coordination event | 🤝 |

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

- "Find your shell. Do the work."
- "Every crab needs the right shell."
- "MoS: Shells that compute."
- "The tide pool where agents meet."
- "Mixture of Shells — because experts don't carry their offices."

## Meme Potential

The hermit crab is already a perfect meme vehicle:
- Crab in a tiny shell → local model on edge device
- Crab in a massive shell → GLM-5.1 on paid plan
- Crab trying on wrong shell → Tier 3 model on math task
- Crab decorating shell → Hebbian room personalization
- Two crabs fighting over a shell → agent contention
- Crab molting → compaction / context reset
- Tide pool aerial shot → fleet dashboard visualization

---

*MoS is the Cocapn fleet architecture. Shells are rooms. Crabs are agents. The conservation law keeps the tide pool healthy.*
