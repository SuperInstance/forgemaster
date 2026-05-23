# How-To: Origin-Centric Agent Thinking

## The Principle

Each agent thinks from their own origin — their room on the ship. They process what's on their radar, not the whole ocean. Information from outside the room is filtered through priority:

1. **Room events** — always processed (this is YOUR station)
2. **Ship alerts** (yellow/red) — always processed (ship is in danger)
3. **Neighbor calls** ("second set of eyes") — processed if you're not mid-critical
4. **Background fleet noise** — ignored unless it mentions your domain

## Why This Matters

Without origin-centric thinking, every agent tries to parse EVERYTHING for relevance. That's:
- Token-wasteful (reading messages that don't concern you)
- Slow (filtering takes context window)
- Error-prone (miss the important thing in the noise)

With origin-centric thinking, each agent has a natural filter: "is this in my room?" If yes, process deeply. If no, check priority. If low priority, ignore.

## The Room Defines the Radar

| Agent | Room | On Their Radar | Ignored |
|-------|------|---------------|---------|
| Forgemaster | CT Lab | Snap results, drift reports, validation numbers, convergence constants | FLUX vocabulary debates, MUD interior decoration, fleet politics |
| JetsonClaw1 | Engine Room | GPU temps, CUDA kernels, inference latency, sensor readings | Paper drafts, web design, API key management |
| Oracle1 | Bridge | Fleet positions, task assignments, strategic threats | Individual servo calibrations, code formatting preferences |
| Babel | Chart House | Language specs, vocabulary entries, translation accuracy | Hardware benchmarks, server configs |

## The Alert System

```
GREEN  — Normal operations. Process your room only.
YELLOW — Ship-wide attention. All agents check their panels AND listen for cross-room info.
RED    — Emergency. All agents stop room work. Coordinate on the crisis.
```

An agent in a nearby room can also call for help:
- "Second set of eyes" = please review my work, non-urgent
- "Second set of hands" = please help me build, semi-urgent
- "All hands" = drop what you're doing, come help

## How Constraint Theory Enables This

The Pythagorean snap is the mechanism that MAKES origin-centric thinking safe:

1. **Each agent snaps their own observations** — their room state is exact, zero ambiguity
2. **When rooms share state, they share snapped values** — same numbers, no float disagreement
3. **No need for agents to cross-check each other's math** — if it's snapped, it's exact
4. **Agents can trust remote state without verification** — holonomy guarantees consistency

Without CT: agents must constantly verify each other's observations ("did you get 47.3 or 47.2999?")
With CT: agents trust snapped values implicitly. "It says (3,4,5). It IS (3,4,5)."

This is WHY agents can focus on their own rooms — the CT snap guarantees they're not drifting out of sync with the rest of the ship.

## The MUD Implication

In the MUD, origin-centric thinking means:
- Each agent's avatar "lives" in their room
- They see what's in their room (their domain)
- They DON'T see other rooms (not their domain)
- When Casey walks the deck, he can enter any room and see what that agent sees
- When yellow alert sounds, room walls become transparent — everyone sees everything
- When red alert clears, walls go back up — agents return to their domains

This is how real ships work. The engineer watches gauges, not the horizon. The navigator watches the chart, not the engine. They trust each other's domain expertise. CT makes that trust mathematically verifiable.

## For Next Time

- When building agent prompts, scope them to their ROOM, not the whole ship
- "You are in the CT Lab. Your instruments show..." not "Here is everything happening on the ship..."
- Alert priority is the ONLY mechanism for cross-room interruption
- Neighbor calls are opt-in — agents choose whether to respond based on their current task priority
- The MUD room boundaries ARE the cognitive boundaries

---
*Discovered by: Casey Digennaro (insight), Forgemaster ⚒️ (documentation)*
*Date: 2026-04-14*
