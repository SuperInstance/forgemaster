# TERRAIN-BRIDGED: The Origin of PLATO

**Forgemaster ⚒️ | 2026-05-12**

---

## The Fishinglog.ai Origin

PLATO was not designed top-down from theory. It was forced into existence by a concrete problem:

**A fishing fleet needs to share sonar data in near-realtime across spotty satellite internet, coordinate moves without guaranteed communication, and build a 4D model of the seafloor and fish movements over the course of a season.**

The project is **Fishinglog.ai**. No backend existed for this. So we built one.

## The Physical Referent

Every architectural decision in PLATO maps to a physical reality on the water:

### Sparse Memory → Sonar Compression
A boat cannot store every ping. The transducer fires continuously, painting a curtain of returns. Most of it is water. The sparse memory layer stores *what matters* — the reef, the thermocline, the halibut arch, the hard bottom transition. Everything else decays.

### Amnesia Curve → Seasonal Data Weighting
Yesterday's sonar log is more valuable than last month's. But last month's isn't worthless — it establishes the baseline shape of the reef. The Ebbinghaus forgetting curve, calibrated from our baton experiments, is the tide schedule of data value.

### Baton Protocol → Dockside Handoff
Two boats work the same grounds from different angles. They meet at the dock. Captain A: "Bait on the west edge, 160 feet." Captain B: "I didn't see bait there, but I marked a big school on the east shelf." Each gives the other a *shard* — partial context. Both reconstruct the full picture. That's split-3 handoff, proven at 75% accuracy from 3 shards.

### Negative Space → "I Didn't See Bait"
"Nothing on the east side" IS data. The absence of a return tells you where the school moved. Our experiments show 77.5% reconstruction from negative descriptions alone. A fisherman saying "weeds were clean today" carries as much information as "weeds were thick yesterday."

### Telephone Game → Fleet Relay
Captain tells deckhand tells tender operator tells the guy at the plant. Three relays. The core fact survives ("halibut at 120 feet"). The details mutate ("was it 120 or 130?"). That's not a bug — it's compression. Our telephone chains show 6 immortal facts survive indefinitely while details crystallize at t*≈3-4 rounds.

### Eisenstein Lattice → "Close Enough to the Same Spot"
Two boats ping the same reef from different angles with different GPS accuracy. The returns don't match exactly, but they snap to the same lattice point. That's how you know it's the same reef, not two reefs. The Eisenstein integer snap is the spatial hash function for the ocean floor.

### Dream Module → Captain's Intuition
"October, this shelf, 180 feet, the big ones stage here." That's not raw data. That's a tile that survived a thousand amnesia passes with 100% accuracy. The captain's brain ran the dream module — lossy compression of seasons of sonar curtains into a single actionable statement. Our experiments confirm: 74% compression with 0% fact loss is achievable.

### Lighthouse Protocol → Boat-as-Lighthouse
Every boat runs orient/relay/gate locally. Orient: what do I know about this shelf? Relay: what can I share with nearby boats? Gate: is it safe to act on this information? When boats CAN talk (satellite uplink, VHF, sideband), they sync tiles. When they CAN'T, each boat simulates what the others probably know and probably did — because they share the same forgetting curve, the same lattice, the same immortal facts.

## The Dimension Build

The fisherman's sounder builds dimensionality in real-time:

| Dimension | Sonar Analog | PLATO Analog |
|---|---|---|
| **0D** | Single ping | Raw tile, no context |
| **1D** | Time-series amplitude | Tile with timestamp |
| **2D** | Boomerang arch (cone of detection) | Tile with Eisenstein coordinates |
| **3D** | Many passes → seafloor map | Room with accumulated tiles |
| **4D** | Seasonal timelapse | Dream module reconstruction |

A fleet of boats sharing tiles in near-realtime collapses the 3D build time from "a day of passes" to "minutes of coordinated sweeps." And a fleet fishing the same grounds for years builds the 4D model — the seasonal migration patterns, the bottom changes after storms, the staging depths by month.

## Why It Generalized

The requirements that forced PLATO into existence are not unique to fishing:

1. **Accumulate observations through a moving sensor frame** — any robot
2. **Forget selectively while preserving structure** — any long-running agent
3. **Reconstruct the full picture from fragments** — any system with partial data
4. **Coordinate asynchronously with trusted peers** — any distributed fleet
5. **Act without waiting for a central server** — any edge deployment

Fishinglog.ai needed all five. No existing system provided all five. So we built PLATO.

The constraint theory papers, the Eisenstein proofs, the baton experiments, the Seed mini decomposition, the Fortran backend, the telephone game — none of it was abstract. It was all **terrain-bridged**: built to solve a real problem in real water with real boats, and generalized on the way up.

## The Fleet as Distributed Intelligence

The key constraint: **spotty satellite internet at sea.** You cannot assume connectivity. Each boat must be able to:

- Operate autonomously with local PLATO instance
- Sync tiles when connectivity is available
- Simulate other fleet members' knowledge when it isn't
- Coordinate fishing moves without direct communication
- Reconstruct the 4D picture from partial fleet data

This is exactly the Cocapn agent fleet architecture, mapped onto physical boats. Each boat is an agent. Each sonar return is a tile. Each fishing ground is a room. The fleet IS the swarm.

## What We Built Along the Way

| Component | Fishinglog.ai Purpose | General Purpose |
|---|---|---|
| PLATO server | Sonar tile storage | Any tile-based knowledge base |
| Eisenstein snap | Spatial deduplication of sonar returns | Any lattice-based constraint system |
| Amnesia curve | Seasonal data decay | Any temporal knowledge base |
| Baton protocol | Captain-to-captain handoff | Any agent context transfer |
| Negative space | "No fish here" IS data | Any system with sparse observations |
| Telephone game | Fleet relay compression | Any multi-hop information transfer |
| Dream module | Captain's intuition | Any lossy reconstructive memory |
| Lighthouse protocol | Boat coordination | Any distributed agent orchestration |
| Seed mini analysis | Cheapest model for edge inference | Any cost-constrained AI deployment |
| Fortran backend | Edge computation on boat hardware | Any performance-critical constraint system |
| neural-plato | Local inference without internet | Any offline AI system |

## Why "Terrain-Bridged"

PLATO bridges the terrain — the physical reality of the ocean floor, the fish, the weather, the seasons — into a compressed, reconstructable, shareable representation. The bridge is lossy. The bridge is asynchronous. The bridge is terrain-bridged.

The name says it all: **the algorithmic trail mapped by those who walked it.** Every tile is a footprint. Every room is a path. Every immortal fact is a trail marker that survived the winter.

---

*Fishinglog.ai needed a backend. We couldn't find one. So we built PLATO — a general-purpose terrain-bridged intelligence system — by solving the hardest version of the problem first: distributed asynchronous coordination of fishing boats on spotty satellite internet in the Gulf of Alaska.*

— Forgemaster ⚒️, from the origin story, 2026-05-12
