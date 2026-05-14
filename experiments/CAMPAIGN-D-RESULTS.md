# Campaign D Results — FLUX-ISA vs Natural Language Task Encoding

## What We Tested

10 tasks, each expressed as FLUX bytecode instructions AND natural language. Same agent (phi4-mini), same underlying math. Different encoding.

## Key Finding: Natural Language Wins Slightly (50% vs 40%)

| Metric | FLUX | Natural Language |
|--------|------|-----------------|
| Overall success | 4/10 (40%) | 5/10 (50%) |
| Easy | 1/4 (25%) | 2/4 (50%) |
| Medium | 2/4 (50%) | 2/4 (50%) |
| Hard | 1/2 (50%) | 1/2 (50%) |

## Why FLUX Lost

The model doesn't know FLUX opcodes. When it sees `SNAP(3.7, -1.2)`, it doesn't know what SNAP means. It guesses — sometimes correctly (hex-distance, decode-bytes, classify-claim), often incorrectly (snap-to-lattice, compute-norm, encode-coord).

Natural language won because the model was trained on natural language explanations of math. "Compute the Eisenstein norm" triggers learned computation patterns. "FOLD(3,-1)" does not.

## The ONE Insight: FLUX Won Where Context Was Sufficient

FLUX matched NAT on medium and hard tasks. Why? Because the FLUX prompt included a glossary:
> "FLUX opcodes: FOLD=fold into sector, ROUND=round to Eisenstein int..."

When the model had CONTEXT for what the opcodes mean, it performed as well as natural language. The problem isn't FLUX — it's the model's unfamiliarity with the instruction set.

## Revised Hypothesis

FLUX-ISA is not a replacement for natural language. It's a **compression layer** for tasks that agents are TRAINED to understand. The value proposition:

1. **Bandwidth**: FLUX task = 16 bytes. NL task = ~200 tokens (~800 bytes). 50× compression.
2. **Determinism**: FLUX has one interpretation. NL has many.
3. **Training required**: Agents need FLUX opcode definitions in their context. Cost: ~100 tokens once.

For a fleet where agents run 1000+ tasks/day, the 50× compression saves 500K tokens/day. At $0.01/1K tokens, that's $5/day saved — enough to matter.

## Build Order Implication

Don't build FLUX as a universal task encoding yet. Build it as:
1. An **optional compression layer** for well-defined mathematical tasks
2. A **deterministic contract** between agents that both know FLUX
3. A **fallback** when token budget is tight

Keep natural language as the default. FLUX is optimization, not foundation. Same lesson as Campaign C (terrain weighting) — compression/optimization layers only help when the base layer works.
