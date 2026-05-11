# @snapkit/core

**Tolerance-Compressed Attention Allocation**

A TypeScript library implementing snap-attention theory — the systematic compression of context through tolerance boundaries so cognition can focus on where thinking actually matters.

> *"The snap doesn't tell you what's true. The snap tells you what you can safely ignore."*

## Core Concepts

### SnapFunction
The primary compression mechanism. Defines a tolerance window around an expected baseline. Values within tolerance are "snapped" to the baseline (ignored). Values outside tolerance are "deltas" — signals that demand attention.

```typescript
import { SnapFunction } from '@snapkit/core';

const snap = new SnapFunction({ tolerance: 0.1 });

// Within tolerance → compression
const result1 = snap.snap(0.05);  // { snapped: 0, withinTolerance: true  }

// Outside tolerance → delta
const result2 = snap.snap(0.5);   // { snapped: 0.5, withinTolerance: false }
```

### DeltaDetector
Multi-stream delta monitoring with adaptive prioritization. Tracks deltas across independent channels, computes attention weights from actionability and urgency.

### AttentionBudget
Finite cognition allocation. Distributes a limited budget across competing deltas using one of three strategies (actionability, reactive, uniform).

### ScriptLibrary
Pattern recognition and automation. Learns frequently-occurring patterns, builds scripts that fire automatically, freeing attention for novel situations.

### SnapTopology
Mathematical classification of snap "shapes" based on ADE Lie theory. Each topology provides a different flavor of randomness:
- **A₁**: Binary (coin flip)
- **A₂**: Hexagonal (Eisenstein integers, densest 2D)
- **D₄**: Octahedral (8 directions)
- **E₆/E₇/E₈**: Exceptional (maximum rank for given dimension)

### LearningCycle
The experience → pattern → script → automation cycle. Moves through phases:
1. **Delta flood** — Everything demands attention, cognitive load spikes
2. **Script burst** — Library learns patterns, scripts form
3. **Smooth running** — Most signals handled automatically

### Adversarial Layer
For multi-agent contexts where other minds generate fake deltas:
- `FakeDeltaGenerator` — Manufacture plausible-but-false deltas
- `AdversarialDetector` — Bayesian classification of real vs fake signals
- `CamouflageEngine` — Mask attention allocation from observers
- `BluffCalibration` — Nth-order theory of mind (I know you know I know...)

### Stream Processing
Async iterable support for processing continuous data streams.

### Eisenstein Integers
Optimal 2D snap using the A₂ Eisenstein lattice (6-fold symmetry, densest packing).

## Installation

```bash
npm install @snapkit/core
```

## Usage

### Basic Snap Pipeline

```typescript
import { SnapFunction, DeltaDetector, AttentionBudget } from '@snapkit/core';

// 1. Configure snap tolerance
const snap = new SnapFunction({ tolerance: 0.1 });

// 2. Set up delta detection across streams
const detector = new DeltaDetector();
detector.addStream('market_data', snap, {
  actionabilityFn: (delta) => delta.magnitude > 0.1 ? 0.8 : 0.2,
  urgencyFn: (delta) => delta.magnitude * 10,
});

// 3. Allocate attention budget
const budget = new AttentionBudget({
  totalBudget: 100,
  strategy: 'actionability',
});

// 4. Process incoming data
function processTick(value: number) {
  const deltas = detector.observe({ market_data: value });
  const allocations = budget.allocate(detector.prioritize(3));
  return { deltas, allocations };
}
```

### Learning Automation

```typescript
import { LearningCycle } from '@snapkit/core';

const cycle = new LearningCycle();

// Feed experiences to build scripts
for (const tick of marketData) {
  cycle.experience({
    value: tick.price,
    expected: previousPrice,
    reward: outcome,
  });
}

// Check learning state
const state = cycle.currentState;
console.log(`Phase: ${state.phase}, ${state.scriptsActive} scripts active`);
```

## Package Structure

```
dist/            — Compiled JavaScript
src/
  index.ts       — Public API re-exports
  snap.ts        — SnapFunction core
  delta.ts       — DeltaDetector, DeltaStream
  attention.ts   — AttentionBudget
  scripts.ts     — ScriptLibrary
  topology.ts    — ADE snap topologies
  learning.ts    — LearningCycle
  adversarial.ts — Adversarial detection + camouflage
  streaming.ts   — Async iterable stream processing
  pipeline.ts    — Composable pipeline builder
  eisenstein.ts  — Eisenstein integer snap
  visualization.ts — Terminal + HTML visualization
  types.ts       — TypeScript interfaces
test/            — Test suite (node:test)
```

## Development

```bash
git clone https://github.com/SuperInstance/snapkit-js
cd snapkit-js
npm install
npm test        # Run test suite
npx tsc         # Type-check + build
```

## API

Full API documentation is available from TypeScript type definitions.

## License

MIT

---

*Built for the Cocapn fleet. From poker tells to planetary-scale attention allocation.*
