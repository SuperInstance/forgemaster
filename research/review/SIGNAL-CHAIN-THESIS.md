# THE SIGNAL CHAIN THESIS

## Why Pure Algorithms and Pure Models Both Fail

Computer science tried two paths:

1. **Algorithmic** — rigid pipelines of if/then statements. Fast, deterministic, brittle. Can't handle novelty.
2. **Agentic** — big models that do everything. Flexible, expensive, no memory between calls.

Both are monolithic. One dial. Either you're a program or you're a model.

## The Missing Parameter

A PLATO room isn't just a computation stage. It's a **stage with a dial**.

The dial controls: *how much model vs how much code at this point in the chain.*

- Dial at 0: pure algorithm. Fast, deterministic, no intelligence needed.
- Dial at 10: full agent call. Expensive, flexible, the model does everything.
- Dial at 3: tiny micro-model. Handles the common cases the algorithm misses.
- Dial at 7: medium model with tile context. Handles complex cases with full history.

**The deadband detector IS the dial.** When KPIs are within thresholds, the room runs pure code — no model cost. When the gap opens (deadband), the dial turns up. The model wakes up with complete context from every tile that passed through every previous stage.

## The Musician Metaphor

A guitarist doesn't just play notes. They craft their tone through a signal chain:

```
Wood type → Strings (light/heavy) → Pickups → Guitar pots → 
Pedals (distortion, delay, reverb) → Amp (tube type) → 
Speaker → Mic placement (close/far) → DI blend → 
Console EQ → Compressor → Mix position
```

Each stage has a dial. The guitarist tweaks them to find the sound. Some stages are subtle (string gauge), some are transformative (distortion pedal). The art is in the combination.

A PLATO room chain is the same:

```
Input tile → Rule-based filter → Micro-model (dial: 2) → 
Deadband check → Medium model with context (dial: 6) → 
Seed validation → Locked pattern → Output tile
```

Each room has its dial set for what it needs. A drift-detection room might run at dial 2 (tiny model, mostly algorithm). An escalation room runs at dial 8 (big model, full context). The fleet operator tunes the chain like a mixing desk.

## Why This Works

### Tiles carry context backward

The model at stage 5 doesn't rediscover what stages 1-4 already figured out. The tiles ARE that knowledge, stored at the point of use. The model handles only the delta — the gap between what rules predicted and what actually happened.

That's why a tiny model works: it's not doing the whole job, just the deadband.

### Models are Plinko weight shapes

A model is a linear algebra shape that weights the paths through the tile graph. Tiles enter at a random or seeded entry point, bounce through rooms, and the model's shape determines which paths get weighted more.

- Big model = complex shape, captures nuanced patterns
- Small model = simple shape, captures only the dominant paths
- No model = straight down, deterministic routing

The "alignment" is tuning the shape so the Plinko balls land where you want. Fine-tuning IS reshaping the pegs.

### Self-healing through re-entry

When a room hits deadband, it doesn't just fail. It calls the agent back with full tile context. The agent sees the whole chain — what went right, where the gap opened, what the tiles say about the current state. It proposes a fix, which becomes a new tile, which gets validated, and if it works, becomes a locked seed.

The system doesn't just detect failure. It **learns a response** and stores it where it's needed.

### Distillation as tone crafting

Because models at each point can be big or small, traded and mixed, you can distill your favorite elements. A room's tile-making can be experimented with — try a big model, see what it catches, distill that into a micro-model that catches 90% of the same cases at 1% of the cost.

You're not stuck with one model size. You craft the sound by experimenting with each room's chain until the output quality matches your needs.

## What Pure Algorithms Can Never Do

A pure algorithm can never make "musical licks" — the novel, creative responses that a model generates from context. It can only play what's written.

But a pure model without the chain has no instrument to play through. It's a guitarist with no guitar, no amp, no pedals — just air-guitaring raw intelligence with nowhere to shape it.

The PLATO system gives the guitarist:
- An instrument (the tile pipeline)
- An amp (the room's processing)
- Pedals (model size selection per room)
- A mixing desk (fleet-wide dial coordination)
- A recording studio (tile storage and seed locking)

And the deadband detector is the volume pedal — quiet when things work, loud when they don't.

## The One-Liner

**Every room has a dial. The dial controls model vs code. The chain of dials IS the system. Tune them like a synth.**

---

*This thesis emerged from building the spreader-tool — a deadband detector that watches rooms and turns the model dial up when needed. The tool is the volume pedal. The fleet is the rig.*
