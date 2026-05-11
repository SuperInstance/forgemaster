/**
 * Node.js Quick Demo
 *
 * A simple end-to-end demo of the snap-attention pipeline.
 *
 * @example
 * ```bash
 * npx tsx examples/node-demo.ts
 * ```
 */

import {
  SnapFunction,
  DeltaDetector,
  AttentionBudget,
  ScriptLibrary,
  formatPipelineSnapshot,
  deltaBarChart,
} from '../src/index.js';

console.log('');
console.log('╔══════════════════════════════════════════╗');
console.log('║   SnapKit — Tolerance Compression Demo   ║');
console.log('╚══════════════════════════════════════════╝');
console.log('');

// ─── Snap ────────────────────────────────────────────────────────────────────

const snap = new SnapFunction({ tolerance: 0.1 });
console.log('Snapping values with tolerance=0.1...');
console.log('');

const testValues = [0.05, 0.03, 0.42, -0.02, 0.38, 0.5, 0.01, -0.08, 0.0];

for (const v of testValues) {
  const result = snap.snap(v);
  const icon = result.withinTolerance ? '✓' : 'Δ';
  console.log(
    `  ${icon} ${v.toFixed(4)} → ${result.snapped.toFixed(4)}` +
      ` (δ=${result.delta.toFixed(4)})`
  );
}

console.log('');
console.log(`  Snap rate: ${(snap.statistics.snapRate * 100).toFixed(1)}%`);
console.log(`  Calibration: ${snap.statistics.calibration.toFixed(2)}`);
console.log('');

// ─── Delta Detection ─────────────────────────────────────────────────────────

const detector = new DeltaDetector();
detector.addStream('alpha', new SnapFunction({ tolerance: 0.1 }));
detector.addStream('beta', new SnapFunction({ tolerance: 0.2 }));
detector.addStream('gamma', new SnapFunction({ tolerance: 0.5 }));

console.log('Observing multi-stream deltas...');
console.log('');

for (let i = 0; i < 5; i++) {
  const deltas = detector.observe({
    alpha: Math.random() * 0.5,
    beta: Math.random() * 0.3,
    gamma: Math.random() * 1.0,
  });

  for (const [, d] of Object.entries(deltas)) {
    const status = d.magnitude > d.tolerance ? 'Δ DELTA' : '· snap';
    console.log(`  [${d.streamId}] ${status} (δ=${d.magnitude.toFixed(4)})`);
  }
  console.log('');
}

// ─── Bar Chart ───────────────────────────────────────────────────────────────

const currentDeltas = detector.currentDeltas();
console.log(deltaBarChart(currentDeltas, 30));
console.log('');

// ─── Attention Budget ────────────────────────────────────────────────────────

const budget = new AttentionBudget({
  totalBudget: 100,
  strategy: 'actionability',
});

const prioritized = detector.prioritize(3);
const allocations = budget.allocate(prioritized);

console.log('Attention allocations:');
for (const a of allocations) {
  console.log(`  #${a.priority} ${a.delta.streamId}: ${a.allocated.toFixed(1)} units (${a.reason})`);
}
console.log('');
console.log(`Budget remaining: ${budget.remaining.toFixed(1)}`);
console.log('');

// ─── Script Learning ─────────────────────────────────────────────────────────

const library = new ScriptLibrary({ matchThreshold: 0.85 });

// Learn some patterns
library.learn([0.1, 0.2, 0.3], 'fold', 'pattern_fold_weak');
library.learn([0.8, 0.2, 0.7], 'raise', 'pattern_raise_strong');
library.learn([0.4, 0.4, 0.4], 'check', 'pattern_check_medium');

console.log('Script library:');
console.log(`  Scripts: ${library.statistics.totalScripts}`);
console.log(`  Hit rate: ${(library.statistics.hitRate * 100).toFixed(1)}%`);
console.log('');

// ─── Final Snapshot ──────────────────────────────────────────────────────────

const latest = snap.snap(testValues[testValues.length - 1]);
console.log(
  formatPipelineSnapshot(
    latest,
    allocations.map((a) => a.delta),
    allocations
  )
);
