# Workshop Pipeline: Show Your Work, Backtest, Feed Back

## What We Built

A 5-step pipeline that forces non-thinking models to show reasoning as JSON:

1. **FORK** — Generate N competing reconstructions with structured reasoning
2. **RUN** — Execute validation code from each reconstruction
3. **SCORE** — Backtest facts against ground truth (recall, confidence)
4. **ANALYZE** — 4D ranking (cost, quality, speed, coverage)
5. **FEED** — Generate room improvement patches from gaps

## Results: Hermes-70B Workshop on Constraint Theory Tile

### 3 Competing Approaches

| Approach | Recall | Confidence | Uncertain | Strategy |
|----------|--------|-----------|-----------|----------|
| Literal | **70%** | 0.7 | 6 | Safe, recovers obvious facts |
| Systematic | 60% | 0.6 | 7 | Structured, over-constrains |
| Creative | 30% | 0.4 | 8 | Speculative, generates novel but wrong |

### What the Workshop Revealed

**The literal approach wins.** When a model doesn't deeply know a domain, the safest strategy is to expand only what it's certain about. Creative approaches hallucinate.

**21 uncertain facts identified.** The model marked facts it wasn't sure about with `?` prefix. These are EXACTLY the tiles we need to add to the room for better zero-shot.

**3 missed facts consistently.** All approaches missed the same 3 facts — these are outside the model's training data entirely.

### The Feed-Back Loop

The workshop generated 10 patches, ranked by criticality:

1. **(5/5) 230B/23B MoE integration** → application layer — highest priority
2. **(4/5) Penrose P3 5D cut-and-project** → foundation — prerequisite knowledge
3. **(4/5) Golden-ratio hash vertex IDs** → foundation — prerequisite knowledge
4. **(4/5) Fibonacci word encoding** → structure — key algorithm
5. **(4/5) 3-color baton sharding** → structure — key protocol
6. **(4/5) PCA 1.7x projection** → application — benchmark result
7. **(3/5) Dead-reckoning nav** → application — use case
8. **(3/5) Deflation consolidation** → structure — optimization
9. **(3/5) C9 locality failure** → structure — negative result
10. **(3/5) Recall@20 metrics** → application — benchmark

Add these patches to the room → run workshop again → score should jump from 70% to 90%+.

## Why Non-Thinking Models Are Better for This

| Aspect | Thinking Model | Non-Thinking + Workshop |
|--------|---------------|------------------------|
| Reasoning visibility | Hidden in reasoning_content | Visible in JSON |
| Auditable | No | Yes |
| Backtestable | Can't extract claims | Claims in facts_recovered |
| Confidence calibration | Internal, invisible | Explicit 0.0-1.0 per approach |
| Validation | Can't run their code | validation_code is executable |
| Patch generation | Can't see what they missed | facts_uncertain feeds patches |

Thinking models are black boxes. Non-thinking models with forced JSON are glass boxes.

## The 4D Filtering UX

After running the workshop across N models:

```
          COST →
   ┌─────────────────────┐
   │ 8B: $0.0001, 10/10  │ ← BEST (cheap + perfect)
   │                      │
 Q │ 17B: $0.0002, 9/10  │ ← Good
 U │                      │
 A │ 70B: $0.03, 10/10*  │ ← Overkill (*needs room)
 L │                      │
   │ 230B: $0.01, 10/10  │ ← Expensive, not better
   │                      │
   └─────────────────────┘
          ↑ SPEED
```

The workshop output lets us build a filtering UX:
- **For reconstruction**: Use 8B (cheapest perfect score)
- **For hypothesis generation**: Use Seed (best novel insights)
- **For domain coverage**: Use Hermes + room (most uncertain facts found)
- **For validation**: Run the code snippets from workshop

## Back-Testing Power

Each workshop run produces:
- N reconstructions × M models = NM data points
- Each with: recall, confidence, uncertain facts, validation result
- Feed patches back → run again → measure delta

**This is gradient descent on room quality.** Each iteration makes the zero-shot better.

Cost per iteration: ~$0.05 (3 models × ~$0.015 each)
Expected iterations to 95% recall: 3-5
Total cost: $0.15-0.25 for a production-quality expertise room.

## Next: Build the 4D Dashboard

```
expertize/
├── workshop.py         # The 5-step pipeline (DONE)
├── expertize.py        # Room builder (DONE)
├── dashboard.py        # 4D analysis visualization
├── expertise-modules/  # Pre-built rooms
└── backtest/           # Historical workshop runs for trend analysis
```

The dashboard should show:
1. Cost × Quality scatter per model
2. Recall improvement per workshop iteration
3. Patch criticality heatmap
4. Model ranking per domain
5. Convergence prediction (when to stop iterating)
