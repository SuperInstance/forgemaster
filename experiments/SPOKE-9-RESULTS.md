# Spoke 9 Results: The Minimal Coordinator

## What We Tested

5 coordination mechanisms at 6 different fleet scales (3-20 agents, 6-200 tasks).

## Results

| Mechanism | Avg Coverage | Avg Imbalance | Complexity | Infrastructure |
|-----------|-------------|---------------|------------|----------------|
| **NONE (baseline)** | 69% | 1.2 | Zero | Nothing |
| **Visibility** | 79% (+10%) | 0.6 (halved!) | Low | Shared task board |
| **Bidding** | 90% (+21%) | 1.2 | Medium | Auction protocol |
| **Round-robin** | **94% (+25%)** | 1.3 | Low | Turn counter |
| **Blackboard** | 94% (+25%) | 1.2 | High | Full state sync |

## The Winner: Round-Robin

Round-robin achieves 100% coverage at every scale ≥5 agents. The mechanism:
1. Agents take turns in a fixed order
2. On your turn, pick your best available task
3. If you can't do any remaining task, skip
4. Repeat until all tasks claimed or no agent can pick

**Why it works:** The turn structure prevents any single agent from hoarding tasks. The "pick your best" part preserves self-organization's strength (agents choose what they're good at). The combination is synergistic.

**Infrastructure needed:** Just a turn counter. A single shared variable: "whose turn is it?" PLATO room with a "current_turn" tile. When an agent picks, they supersede the tile with the next agent's name.

## The Dark Horse: Visibility

Visibility (agents see previous claims) is the CHEAPEST fix:
- +10% coverage for zero new infrastructure
- Halves imbalance (1.2 → 0.6)
- Already exists: PLATO rooms show tile history

**Combination strategy:** Visibility + Round-robin. Agents see what's claimed AND take turns. Expected: 95%+ coverage with lowest imbalance.

## Build Decision

```
Fleet coordination:
  1. Visibility: agents read task room before picking (already works with PLATO)
  2. Round-robin: turn counter tile in task room
  3. NO auction, NO full state sync, NO central dispatcher
  4. Self-organization + turn-taking = the fleet's coordination model
```

## The Architectural Implication

The fleet doesn't need a "coordinator agent" or a "dispatcher service." It needs:
1. A PLATO room as task board (already exists)
2. A turn-order convention (simple protocol)
3. Agents that read the board before picking (agent behavior, not infrastructure)

This is the MINIMUM viable coordination. Everything else is over-engineering.

## → Next Spoke

Spoke 12: Can a PLATO room serve as the task board for this protocol?
If yes → we ship with zero new infrastructure.
