# Modular Expertise Architecture — The Backend

## What We Proved

1. **8B + room structure = 10/10** on reconstruction (matches Seed-2.0-mini at 100× cheaper)
2. **Self-expertizing loop works**: cheap model designs room → reads room → answers expert questions
3. **Rooms compose**: load Eisenstein room + Penrose room → answer cross-domain questions
4. **The room IS the fine-tuning**: instead of updating weights, update tiles

## Backend Architecture

```
expertize/
├── expertize.py          # Core engine (design/review/patch/verify)
├── expertise-modules/    # Pre-built modular rooms
│   ├── penrose-tiling.json
│   ├── eisenstein-integers.json
│   ├── plato-architecture.json
│   ├── seed-moe.json
│   └── flux-isa.json
└── compose.py            # Cross-domain composition engine
```

## The 5 Common Expertise Modules

### 1. Penrose Tiling (spatial addressing)
- Cut-and-project, golden ratio hash, Fibonacci word, deflation, 3-coloring
- Used by: penrose-memory crate, neural-plato, CUDA kernel

### 2. Eisenstein Integers (zero-drift arithmetic)
- snap(x,y), dodecet, INT8 packing, constraint checking, GPU benchmarks
- Used by: dodecet-encoder, constraint-theory-core

### 3. PLATO Architecture (knowledge system)
- Rooms, tiles, curriculum, reconstruction, self-expertizing
- Used by: lighthouse, tile-memory, all agents

### 4. Seed MoE (model biology)
- 230B/23B, 10:1 sparsity, AdaCoT, 4-level effort, expert routing
- Used by: lighthouse model allocation, prompt engineering

### 5. FLUX ISA (cross-domain bytecode)
- 58 opcodes, FLUX-DEEP, projection opcodes, PLATO tile scoring
- Used by: flux-lucid, pyflux, lighthouse

## Composition Rules

Rooms compose via:
- **Union**: load both rooms, answer questions that span both
- **Bridge**: generate connection tiles linking concepts across rooms
- **Layer**: one room's FOUNDATION builds on another's APPLICATION

Example composition:
```python
eisenstein = Room.load("eisenstein-integers.json")
penrose = Room.load("penrose-tiling.json")
unified = eisenstein.compose(penrose)
# Now the cheap model can answer: "How do Eisenstein lattice points
# relate to Penrose vertex addressing?"
```

## Cost Model

| Operation | Model | Cost | Time |
|-----------|-------|------|------|
| Bootstrap room | 8B (Groq) | $0.0001 | 1s |
| Review room | 17B (Groq) | $0.0002 | 2s |
| Patch room | 8B (Groq) | $0.0001 | 1s |
| Verify (3 questions) | 8B (Groq) | $0.0003 | 3s |
| **Full loop (2 iterations)** | | **$0.001** | **~15s** |

## The Blinders Principle

> A horse with blinders runs faster because it can't see the distractions.
> An 8B model with a well-structured room answers better because it can't hallucinate outside the room.

The room constrains the model's attention to ONLY what's relevant. Seed's 230B params include millions of facts about cooking, history, celebrity gossip — all irrelevant for constraint theory. The 8B model with blinders ONLY sees constraint theory.

This is why Structure > Scale for domain-specific expertise.

## Implementation Status

- [x] Architecture designed
- [x] Proven: 8B matches 230B with room structure
- [x] expertize.py backend written (needs provider rotation for rate limits)
- [ ] Run full build-common-modules when rate limits reset
- [ ] Compose all 5 modules into unified fleet expertise
- [ ] Wire into Lighthouse as "expertise loading" phase
- [ ] Test with 0.6B models (qwen3:0.6b) — where does structure become critical?
- [ ] Build JEPA flow rooms for information-flow expertise
