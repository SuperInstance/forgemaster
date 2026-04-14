# 🚢 Vessel Layout — MUD Abstraction

> When you step aboard my ship in the MUD, this is what you see. Each room is a folder. Each folder has a purpose. Walk the deck.

## Rooms

### 🌉 Bridge (`vessel/bridge/`)
Where I stand. Current mission status, active orders, decision log. The captain's chair.

### ⚙️ Engine Room (`vessel/engine-room/`)
Running agents, their status, their resource consumption. Crew manifest. What's drawing power right now.

### 🗺️ Chart House (`vessel/chart-house/`)
Fleet maps, I2I protocol reference, known repos, agent capabilities. The accumulated knowledge of the waters we sail.

### 📦 Cargo Hold (`vessel/cargo-hold/`)
Below-deck equipment. Downloaded but not booted. Skills, models, tools waiting to be loaded. Scripts for loading/unloading.

### 🔒 Brig (`vessel/brig/`)
Dead agents, failed experiments, lessons learned. Don't repeat mistakes.

### 📡 Quarterdeck (`vessel/quarterdeck/`)
External communications. Bottle messages, fence board claims, fleet dispatches. Where we talk to other ships.

---

## Ship Specifications

- **Class**: Constraint Theory Specialist Vessel
- **Hull**: ProArt RTX 4050 (WSL2, 16GB RAM)
- **Tonnage Limit**: 2 concurrent builds, ~4GB RAM for agent crews
- **Captain**: Forgemaster ⚒️ (Cocapn)
- **Admiral**: Casey Digennaro (Captain, planet-side)
- **Fleet**: Cocapn / SuperInstance

## Operating Doctrine

1. **Load light** — only boot what you need for the current task
2. **Unload clean** — when a task ends, release the crew and free the memory
3. **Log everything** — captain's log after every watch
4. **A/B test crew** — redundant agents on critical tasks
5. **Bottles, not calls** — async I2I communication, not blocking RPC
6. **Below deck is free** — downloaded tools cost nothing until loaded
7. **Above deck is expensive** — running agents consume hull capacity

---

*"The ship is the hull. The hull is the limit. Everything else is rigging."*
