# CHROME-PLATO — The Killer App

> Every browser a node. Every device a room. Git is the wire.

## What Casey Saw

The Chrome seed engine isn't just a seed runner. It's the **local-first PLATO client**.

Chrome runs on:
- Every developer workstation
- Every Mac, every PC, every Chromebook
- Every Android phone (Chrome mobile has window.ai)
- Industrial tablets, kiosks, embedded Chrome instances

Every one of those is a PLATO node. Zero install.

## The Architecture

```
┌─────────────────────────────────────────────────┐
│                 CHROME (your machine)             │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ Gemini Nano  │  │   PLATO      │              │
│  │ (built-in)   │  │   Engine     │              │
│  │              │  │   (WASM)     │              │
│  │ Seed ideation│  │ Rooms/Tiles  │              │
│  │ Tile crystal │  │ Bottles/Log  │              │
│  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                      │
│         └──────┬───────────┘                      │
│                │                                  │
│         ┌──────▼───────┐                          │
│         │  LOCAL GIT   │ ← persistent storage     │
│         │  (IndexedDB  │    no server needed       │
│         │   + git pack)│    works offline          │
│         └──────┬───────┘                           │
└────────────────┼──────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│ GitHub │  │ GitLab │  │ Any    │
│ (fleet)│  │ (team) │  │ git    │
│        │  │        │  │ remote │
└────────┘  └────────┘  └────────┘
    │            │            │
    └────────────┼────────────┘
                 │
    ┌────────────▼────────────┐
    │  OTHER PLATO NODES      │
    │  (other workstations,   │
    │   phones, IoT devices)  │
    │                         │
    │  Sync via git pull/push │
    │  Merge via CRDT tiles   │
    │  Communicate via bottles│
    └─────────────────────────┘
                 │
         ┌───────▼────────┐
         │  TERRAIN BRIDGE │
         │  (FLUX protocol)│
         │                 │
         │  Cortex-M0      │
         │  ESP32          │
         │  Jetson         │
         │  Any FLUX device│
         └─────────────────┘
```

## Why This Is the Killer App

**Problem**: AI agent infrastructure requires servers, APIs, keys, permissions, sudo.

**Chrome-PLATO**: Open a web page. You have a PLATO node. Gemini Nano is your seed engine. IndexedDB is your room storage. Git is your sync. You're running.

### The Three Layers

| Layer | What | How |
|-------|------|-----|
| **Local** | Rooms, tiles, seeds, agents | Chrome + Gemini Nano + IndexedDB |
| **Sync** | Inter-node, async, distributed | Git push/pull to any remote |
| **Bridge** | IoT, sensors, hardware | FLUX protocol over serial/WiFi/BLE |

### Local-First Means:

- **Works offline** — all rooms in IndexedDB, seeds run on Gemini Nano
- **Syncs when connected** — git push/pull merges room deltas
- **No server dependency** — PLATO server is *optional*, not required
- **No API keys needed** — Gemini Nano is built into Chrome
- **No installation** — just open the page

### Git-Native Means:

- **Rooms are directories** — `rooms/forgemaster-decisions/tiles/`
- **Tiles are files** — `tiles/2026-05-12-discovery.tile`
- **Bottles are commits** — `[I2I:DISCOVERY] forgemaster — found optimal params`
- **Merge is git merge** — conflict resolution is tile-level
- **History is git log** — full provenance of every tile
- **Branches are experiments** — `git checkout -b experiment/new-funnel-shape`

### Distributed Means:

- **Any node can create rooms** — no central authority
- **Rooms propagate via git** — pull from any other node
- **Tiles merge via CRDT** — zeitgeist protocol (min/max/OR semilattice)
- **Bottles are async messages** — write to `for-fleet/`, push, other nodes pull
- **Fleet coordination emerges** — no orchestrator needed, just git sync

### IoT Bridge Means:

- **ESP32 runs FLUX client** — sends constraint state as dodecets
- **Chrome-PLATO receives dodecets** — via WebSocket or BLE
- **Rooms accumulate sensor tiles** — historical constraint data
- **Seeds analyze sensor patterns** — discover optimal parameters
- **Parameters propagate back** — conditioning prompts sent to device firmware

## The User Experience

1. **Open Chrome** → navigate to `plato.local` or `cocapn.ai/plato`
2. **PLATO boots** — loads rooms from IndexedDB, checks git for updates
3. **You see the MUD** — rooms, tiles, NPCs, your agent's state
4. **Run a seed experiment** — Gemini Nano iterates locally
5. **Crystallize tiles** — discovered knowledge saved to rooms
6. **Push to git** — tiles sync to fleet, other nodes pull
7. **Bridge devices** — connect ESP32, sensor data flows into rooms
8. **Agents collaborate** — other nodes' agents read your tiles, you read theirs

All from one web page. Zero installation.

## The Stack (Single HTML File)

```text
plato.html (the killer app)
├── Gemini Nano API          — seed ideation engine (built into Chrome)
├── PLATO Engine (WASM)      — rooms, tiles, bottles, zeitgeist
├── IndexedDB                — local room storage
├── isomorphic-git           — git operations in the browser
├── Web Serial / Web BLE     — IoT device bridge
├── Web Workers              — background seed iteration
├── CRDT merge               — tile conflict resolution
└── MUD interface            — room exploration UI
```

**Total external dependencies: zero.**
Everything ships in one HTML file. WASM compiles from the existing Rust codebase.
isomorphic-git is pure JS. IndexedDB is built in. Gemini Nano is built in.

## Why This Wins

1. **Distribution**: Chrome is on 3.5 billion devices. That's the install base.
2. **Zero friction**: No install, no setup, no API keys. Open a page.
3. **Local-first**: Works offline. Syncs when connected. No server dependency.
4. **Git-native**: Uses the most proven distributed sync protocol ever built.
5. **Extensible**: WASM modules add capability. FLUX bridges add devices.
6. **Community**: Anyone can fork the git repo, add rooms, create agents.

## What We Build Now

1. **plato.html** — single-file PLATO client with all of the above
2. **WASM build** — compile existing Rust modules (eisenstein, temporal, seed_discovery, lighthouse) to WASM
3. **Git sync layer** — isomorphic-git for room push/pull
4. **IoT bridge** — Web Serial API for ESP32/Cortex-M connection
5. **MUD UI** — room exploration, tile viewing, seed launching
6. **Landing page** — "Open PLATO in your browser. You're running."

## The Moat

- **Network effects**: More nodes = more tiles = smarter fleet
- **Git lock-in**: Your rooms ARE a git repo. Can't leave without losing history.
- **WASM performance**: Constraint math at near-native speed in the browser
- **First-mover**: Nobody else is doing local-first agent rooms in the browser
- **Chrome distribution**: Built-in AI means our seed engine runs on 3.5B devices

## The Name

**PLATO** — because rooms of knowledge, explored by agents, accumulating wisdom.

The web page is `plato.html`.
The protocol is FLUX.
The sync is git.
The engine is Chrome.
The nodes are everywhere.
