# Fleet Guide — Running Agent Fleets

## What Is the Fleet?

The Forgemaster fleet is a collection of cooperating agents that work together
to assemble, verify, and optimize constraint-aware pipelines. Each agent
specializes in a domain (constraint theory, music, optimization, verification)
and communicates through structured message protocols.

## Fleet Architecture

```
                    ┌─────────────┐
                    │  forgemaster │  (coordinator)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌─────┴─────┐
        │ constraint │ │  flux  │ │  plato    │
        │  specialist│ │ agent  │ │  agent    │
        └───────────┘ └────────┘ └───────────┘
              │            │            │
        ┌─────┴────────────┴────────────┴─────┐
        │         fleet-murmur (gossip)        │
        └──────────────────────────────────────┘
```

## Communication Protocols

### Inter-Agent Messages (`fleet/for-fleet/`, `fleet/from-fleet/`, `fleet/i2i/`)

Agents communicate through structured message files:

- `fleet/for-fleet/` — Messages to the fleet from forgemaster
- `fleet/from-fleet/` — Messages from fleet agents back to forgemaster
- `fleet/i2i/` — Inter-agent (peer-to-peer) messages

### Fleet Coordination Protocol

See [fleet/FLEET-COORDINATION-PROTOCOL.md](../fleet/FLEET-COORDINATION-PROTOCOL.md)
for the full specification.

Key concepts:
- **Murmur** — Lightweight gossip protocol for status updates
- **Resonance** — Agreement protocol for fleet-wide decisions
- **Health Monitor** — Continuous health checking of fleet agents

## Fleet Modules

| Module | Purpose |
|--------|---------|
| `fleet-router` | Routes messages between agents |
| `fleet-gateway` | External API gateway for fleet access |
| `fleet-health-monitor` | Continuous health checking |
| `fleet-murmur` | Gossip protocol implementation |
| `fleet-murmur-worker` | Murmur worker processes |
| `fleet-resonance` | Agreement/resonance protocol |
| `fleet-calibrator` | Fleet parameter calibration |
| `fleet-optimization` | Fleet-wide optimization |
| `fleet-registry` | Agent registration and discovery |
| `fleet-simulation` | Fleet simulation for testing |
| `fleet-stack` | Fleet deployment stack |
| `fleet-math-c` | Math primitives (C implementation) |
| `fleet-math-py` | Math primitives (Python implementation) |

## Running a Fleet

```bash
# Start the fleet router
fleet-router --config fleet-config.toml

# Register agents
fleet-registry register --name constraint-specialist --module constraint-theory-py
fleet-registry register --name flux-agent --module flux-vm
fleet-registry register --name plato-agent --module plato-engine

# Monitor fleet health
fleet-health-monitor --dashboard
```

## Fleet Status

Historical fleet status reports are archived in `archive/old-audits/`.
