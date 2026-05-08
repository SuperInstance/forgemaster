# Fleet Tile Protocol — v1

> **One schema. Every repo. Any language.**

## The Pattern

Every fleet service, device, and agent communicates through PLATO tiles. A tile is a `(room, domain, question, answer)` tuple. The answer is JSON.

This document defines the standard tile schemas so any repo in any language can produce and consume fleet state.

## Schemas

| Schema | Domain | Purpose | Used By |
|--------|--------|---------|---------|
| `constraint-tile-v1` | `constraints` | Safety envelope state | OpenArm, guard2mask, insight-engine |
| `discovery-tile-v1` | `discoveries` | Novel findings from experiments | insight-engine, fleet agents |
| `device-tile-v1` | `ensign` | Device registration & capability | bare-metal-plato, OpenArm ESP32, any IoT node |
| `safety-tile-v1` | `safety` | Safety events (violations, e-stops) | OpenArm, constraint services |
| `fleet-tile-v1` | `fleet` | Fleet coordination (heartbeat, status) | all agents |

## How It Works

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  OpenArm ESP32  │    │  Insight Engine  │    │  Guard2Mask GPU │
│  (C)            │    │  (Rust)          │    │  (CUDA)         │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
    constraint-tile        discovery-tile          constraint-tile
    device-tile            frontier-tile           safety-tile
    safety-tile
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                          PLATO Server
                         (8847/tcp, HTTP)
                                │
                ┌───────────────┼───────────────┐
                │               │               │
           Fleet Agent    Fleet Agent     Dashboard
           (reads ALL)    (reads ALL)    (reads ALL)
```

## Room Naming

| Pattern | Who | Example |
|---------|-----|---------|
| `{device-id}` | Physical device | `openarm-lab-01` |
| `{agent-id}` | Fleet agent | `forgemaster`, `oracle1` |
| `fleet-{function}` | Fleet-wide | `fleet-ops`, `fleet-progress` |
| `session-{agent}` | Session state | `session-forgemaster` |
| `insight-engine-{id}` | Discovery runtime | `insight-engine-main` |

## Versioning

- Schemas are suffixed with version: `constraint-tile-v1`
- Breaking changes bump the version: v1 → v2
- Consumers MUST handle unknown fields gracefully (forward compat)
- All timestamps are Unix epoch (seconds)

## Repos Using This

| Repo | Language | Produces | Consumes |
|------|----------|----------|----------|
| SuperInstance/openarm | Python, C | constraint, device, safety | fleet commands |
| SuperInstance/insight-engine | Rust | discovery, frontier | constraint, device |
| SuperInstance/guard2mask-gpu | Rust, CUDA | constraint, safety | discoveries |
| SuperInstance/flux-vm-gpu | Rust, CUDA | constraint | fleet commands |
| SuperInstance/depgraph-gpu | Rust | fleet | fleet, device |
| SuperInstance/bare-metal-plato | C | device, safety | fleet commands |
| SuperInstance/superinstance-fleet-proto | Rust | (library) | (library) |
| cocapn-schemas | JSON | (schemas) | (schemas) |

---

*Part of the Cocapn Fleet Protocol. See cocapn-schemas repo for JSON Schema files.*
