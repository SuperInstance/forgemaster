/**
 * Poker Attention Engine Example
 *
 * Demonstrates snap-attention applied to poker tells:
 * - Snap function tolerances filter out false tells
 * - Delta detector flags real deviations (bet sizing, timing)
 * - Attention budget allocates cognitive energy to actionable tells
 *
 * @example
 * ```bash
 * npx tsx examples/poker.ts
 * ```
 */

import {
  SnapFunction,
  DeltaDetector,
  AttentionBudget,
  ScriptLibrary,
  formatPipelineSnapshot,
} from '../src/index.js';

// ─── Setup ───────────────────────────────────────────────────────────────────

// Each stream represents a potential tell source
const detector = new DeltaDetector();

// Bet sizing tell: small deviations from expected bet pattern
detector.addStream(
  'bet_sizing',
  new SnapFunction({ tolerance: 0.05 }),
  {
    actionabilityFn: (d) =>
      Math.min(1, d.magnitude > 0.1 ? 0.7 : 0.1),
  }
);

// Timing tell: how long player takes to act
detector.addStream(
  'timing',
  new SnapFunction({ tolerance: 0.2 }),
  {
    actionabilityFn: (d) =>
      Math.min(1, d.magnitude > 0.3 ? 0.8 : 0.2),
  }
);

// Table talk: what players say
detector.addStream(
  'table_talk',
  new SnapFunction({ tolerance: 0.15 }),
  {
    actionabilityFn: (d) =>
      Math.min(1, d.magnitude > 0.2 ? 0.5 : 0.1),
  }
);

// Chip handling
detector.addStream(
  'chip_handling',
  new SnapFunction({ tolerance: 0.1 }),
  {
    actionabilityFn: (d) =>
      Math.min(1, d.magnitude > 0.2 ? 0.9 : 0.1),
  }
);

const budget = new AttentionBudget({
  totalBudget: 100,
  strategy: 'actionability',
});

// Script library for common patterns
const scripts = new ScriptLibrary({ matchThreshold: 0.85 });

// ─── Simulate a Poker Hand ───────────────────────────────────────────────────

interface HandAction {
  street: 'preflop' | 'flop' | 'turn' | 'river';
  player: string;
  action: 'fold' | 'check' | 'call' | 'bet' | 'raise' | 'all-in';
  betSize: number; // Pot fraction (0-1)
  timing: number; // Seconds to act (normalized 0-1)
  chipHandlingScore: number; // 0 = calm, 1 = shaky
}

function simulateHand(): HandAction[] {
  return [
    {
      street: 'preflop',
      player: 'Villain',
      action: 'raise',
      betSize: 0.35,
      timing: 0.7, // Quick raise
      chipHandlingScore: 0.31, // Slightly nervous
    },
    {
      street: 'flop',
      player: 'Villain',
      action: 'bet',
      betSize: 0.75, // Large bet (overbet — aggressive)
      timing: 0.9, // Very quick
      chipHandlingScore: 0.41, // Shaky
    },
    {
      street: 'turn',
      player: 'Villain',
      action: 'check',
      betSize: 0.0,
      timing: 0.2, // Very slow (deliberate)
      chipHandlingScore: 0.22, // Calm
    },
    {
      street: 'river',
      player: 'Villain',
      action: 'bet',
      betSize: 0.5,
      timing: 0.85, // Quick
      chipHandlingScore: 0.71, // Very shaky (nervous on river?)
    },
  ];
}

console.log('╔══════════════════════════════════════════╗');
console.log('║     SnapKit Poker Tell Analyzer          ║');
console.log('╚══════════════════════════════════════════╝');
console.log('');

const hand = simulateHand();

for (const action of hand) {
  console.log(
    `[${action.street.toUpperCase()}] ${action.player} ${action.action}` +
      ` (bet: ${(action.betSize * 100).toFixed(0)}%, timing: ${action.timing.toFixed(2)})`
  );

  // Observe all tell streams
  const deltas = detector.observe({
    bet_sizing: action.betSize,
    timing: action.timing,
    table_talk: 0, // No talk in this simulation
    chip_handling: action.chipHandlingScore,
  });

  // Print deltas
  for (const [, delta] of Object.entries(deltas)) {
    if (delta.magnitude > delta.tolerance) {
      console.log(
        `  ⚡ ${delta.streamId}: Δ=${delta.magnitude.toFixed(3)} ` +
          `(act=${delta.actionability.toFixed(2)})`
      );
    }
  }

  // Allocate attention
  const prioritized = detector.prioritize(4);
  const allocations = budget.allocate(prioritized);

  if (allocations.length > 0) {
    console.log('  Attention allocation:');
    for (const alloc of allocations) {
      console.log(
        `    #${alloc.priority} ${alloc.delta.streamId}: ${alloc.allocated.toFixed(1)} units`
      );
    }
  }

  console.log('');
}

// ─── Analysis ────────────────────────────────────────────────────────────────

console.log('╔══════════════════════════════════════════╗');
console.log('║           Session Summary                 ║');
console.log('╚══════════════════════════════════════════╝');
console.log('');

console.log(
  `Budget remaining: ${budget.remaining.toFixed(1)} / ${budget.totalBudget}`
);
console.log(
  `Utilization: ${(budget.utilization * 100).toFixed(1)}%`
);
console.log(`Exhaustion rate: ${budget.exhaustionRate}`);
console.log('');

const stats = detector.statistics;
console.log('Detector stats:');
console.log(`  Streams: ${stats.numStreams}`);
console.log(`  Observations: ${stats.totalObservations}`);
console.log(`  Total deltas: ${stats.totalDeltas}`);

// ─── Decision ────────────────────────────────────────────────────────────────

console.log('');
console.log('══════════ Decision ══════════');
console.log(
  'Based on attention allocation: call if budget > 50% remains, fold otherwise.'
);
console.log(
  budg.remaining > 50
    ? '✅ CALL — Enough attention to track the hand'
    : '❌ FOLD — Attention exhausted, too risky'
);
