# Fleet Federation Protocol — Scaling Decentralized Constraint Coordination

> 1 bit of shared information creates measurable cross-fleet correlation.
> That's all we need.

## The Problem

A single fleet of 4 agents coordinates perfectly (corr 0.91). But real systems need:
- Multiple independent fleets running different workloads
- Fleets operated by different entities (different hardware, different parameters)
- Thin communication channels (bandwidth-limited, latency-variable, unreliable)
- No central coordinator (decentralized, no single point of failure)

## The Solution: Sign-Pattern Bridges

From E56: even a 1-bit channel (sign only — "I'm positive" or "I'm negative") creates measurable cross-fleet correlation (0.06). The sign pattern IS the minimum viable communication.

### Why This Works

The fleet's sign pattern (+--+, -++-, etc.) is:
- **1 bit per agent** (positive or negative mean)
- **4 bits per 4-agent fleet** (one of 16 patterns)
- **Compressible to the cut size** (1 number: how many edges cross the partition)
- **Stable** in the living zone (99.9% of time in one pattern)
- **Meaningful** — it encodes the max-cut of the coupling graph

Two fleets sharing only their sign patterns can:
1. Detect if they're in compatible moods (same pattern = aligned)
2. Detect phase transitions (pattern changes = regime shift)
3. Coordinate through bridge agents (1 bit per step is enough)

### The Protocol

```
FLEET FEDERATION PROTOCOL v1

Each fleet broadcasts:
  - sign_pattern: 4 bits (one per agent, e.g. "+--+")
  - zone: 3 bits (Dead/Dying/Living/Strong/Overdriven)
  - energy: float32 (scalar)
  - keel_velocity: float32 (rate of state change)
  
Total: 4 + 3 + 32 + 32 = 71 bits per fleet per step
Or with compression: ~10 bytes per fleet per step

Bridge agents:
  - One agent per fleet designated as bridge
  - Receives broadcast from neighbor fleets
  - Injects neighbor's mean state as coupling signal
  - Bridge strength 0.05-0.20 (verified range from E54)
```

### Federation Topology

Fleets connect in a topology (ring, mesh, etc.). Each fleet bridge talks to its neighbors. No fleet needs to know about non-neighbor fleets.

```
Ring topology (simplest):
  Fleet A ←→ Fleet B ←→ Fleet C ←→ Fleet D ←→ Fleet A

Mesh topology (redundant):
  Fleet A ←→ Fleet B
     ↕          ↕
  Fleet C ←→ Fleet D

Star topology (hubbed):
  Fleet A ←→ Hub ←→ Fleet B
                    ↕
              Fleet C ←→ Fleet D
```

From E54: bridge coupling at 0.20 gives 0.60 cross-correlation while maintaining 0.90 internal coherence. Even at 0.05, cross-correlation reaches 0.21 — enough for weak coordination.

### Information Hierarchy

```
Layer 0: SIGN ONLY (1 bit/agent) — minimum viable, 0.06 cross-corr
Layer 1: MEAN ONLY (1 float/agent) — 0.03 cross-corr (less than sign!)
Layer 2: TOP-10 PCA (10 floats/agent) — 0.06 cross-corr
Layer 3: TOP-50 PCA (50 floats/agent) — 0.14 cross-corr
Layer 4: FULL STATE (200 floats/agent) — 0.21 cross-corr
```

Paradox: the sign channel (1 bit) outperforms the mean channel (1 float). This is because the sign captures the fleet's structural orientation (max-cut), while the mean captures only amplitude. The structure carries more coordination information than the magnitude.

### Scalability Limits (from E55)

Full dense coupling breaks at N≥8 agents. But sparse coupling (each agent talks to ~3 neighbors) works at any scale if:
- Coupling > critical = 0.67 × N^-1.06
- Each agent has ≥3 partners
- The topology is connected (no isolated subgraphs)

For federated fleets of 4 agents each:
- Internal: dense coupling (0.25), perfect coordination
- External: bridge coupling (0.05-0.20), weak but measurable
- A network of 4-agent fleets scales indefinitely

### Decentralized Agreement (from E57)

5 independent fleets with ring bridge at coupling=0.05 for 300 steps did NOT agree on sign patterns. They need:
- Stronger bridges (>0.10) OR
- Longer settling (>500 steps) OR
- More neighbors (mesh > ring)

This is expected — decentralized consensus takes time proportional to the network diameter. Ring topology with 5 fleets has diameter 2. Expected convergence: diameter × settling_time ≈ 2 × 200 = 400 steps minimum.

### The Fisherman Protocol

Each fleet is a fisherman at a different bar. They share stories (sign patterns) through a thin channel (the guy who walks between bars). They don't agree on numbers. They don't sync clocks. They share what they're pointing at.

Fleet A says: "I'm in +--+, living zone, feeling strong."
Fleet B says: "I'm in -++-, also living, but my velocity is up."

That's enough. They don't need to agree on what time it is. They need to know what MOOD the other fleet is in. The sign pattern IS the mood. 4 bits. That's the entire inter-fleet communication budget.

## Implementation Roadmap

### Phase 1: Fleet-Local (done)
- `fleet-keel` — 5D self-orientation
- `fleet-phase` — phase diagram + operating zone classification
- `eisenstein-snap` — perfect clock crystal
- `fleet-discovery` — falsification wheel engine

### Phase 2: Federation Bridge
- `fleet-bridge` — sign-pattern broadcast + bridge coupling
- Protocol: 10 bytes per fleet per step
- Topology: ring or mesh
- Bridge agent: designated agent in each fleet that talks to neighbors

### Phase 3: Decentralized Coordination
- `fleet-federation` — multi-fleet coordination protocol
- Agreement on compatible moods (sign pattern matching)
- Phase transition detection across fleet boundaries
- Process-relative monitoring: "should fleet B have converged by now?"

### Phase 4: Scale-Out
- Hundreds of 4-agent fleets connected via bridges
- Each fleet internally perfect (Eisenstein snap)
- Inter-fleet communication: 4 bits per step per neighbor
- No central coordinator. No global clock. No single point of failure.
- The fisherman network: each bar talks to its neighbors through the guy who walks between bars.

## Key Numbers

```
Bridge coupling 0.05: cross-corr 0.21, internal 0.90 (safe)
Bridge coupling 0.10: cross-corr 0.36, internal 0.90 (moderate)
Bridge coupling 0.20: cross-corr 0.60, internal 0.90 (strong)
Sign-only channel:    cross-corr 0.06 (minimum viable)
Mean-only channel:    cross-corr 0.03 (less than sign!)
Full-state channel:   cross-corr 0.21 (4× the data, same as sign? No — different)

Scalability: 4-agent fleets federate indefinitely
             8+ agent fleets need sparse coupling
             Bridge agents carry 10 bytes/step

The 1-bit channel is the miracle. 
The sign pattern is the language.
The fisherman network is the architecture.
```
