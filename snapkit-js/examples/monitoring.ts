/**
 * Stream Monitoring Example
 *
 * Shows how to use snap-attention for real-time system monitoring.
 * Snap function tolerances filter out benign fluctuations while
 * flagging real anomalies as deltas.
 *
 * @example
 * ```bash
 * npx tsx examples/monitoring.ts
 * ```
 */

import {
  SnapFunction,
  DeltaDetector,
  AttentionBudget,
  LearningCycle,
  SnapStream,
  DeltaStreamer,
  formatDelta,
} from '../src/index.js';

// ─── Metrics ─────────────────────────────────────────────────────────────────

interface Metric {
  cpu: number;
  memory: number;
  latency: number;
  errorRate: number;
}

function generateMetric(): Metric {
  return {
    cpu: Math.random() * 0.8,
    memory: 0.5 + Math.random() * 0.15,
    latency: Math.random() * 200,
    errorRate: Math.random() * 0.01,
  };
}

// ─── Setup ───────────────────────────────────────────────────────────────────

console.log('╔══════════════════════════════════════════╗');
console.log('║    SnapKit System Monitor                ║');
console.log('╚══════════════════════════════════════════╝');
console.log('');

const detector = new DeltaDetector();

detector.addStream(
  'cpu',
  new SnapFunction({ tolerance: 0.05 }),
  { actionabilityFn: (d) => Math.min(1, d.magnitude * 2) }
);

detector.addStream(
  'memory',
  new SnapFunction({ tolerance: 0.03 }),
  { actionabilityFn: (d) => Math.min(1, d.magnitude * 3) }
);

detector.addStream(
  'latency',
  new SnapFunction({ tolerance: 15 }),
  { actionabilityFn: (d) => Math.min(1, d.magnitude / 100) }
);

detector.addStream(
  'error_rate',
  new SnapFunction({ tolerance: 0.002 }),
  { actionabilityFn: (d) => Math.min(1, d.magnitude * 50) }
);

const budget = new AttentionBudget({
  totalBudget: 100,
  strategy: 'actionability',
});

const learning = new LearningCycle();

// ─── Simulate ────────────────────────────────────────────────────────────────

console.log('Monitoring system metrics (10 ticks):\n');

for (let tick = 0; tick < 10; tick++) {
  const metric = generateMetric();

  // Occasionally inject an anomaly
  if (tick === 3) metric.cpu = 0.95; // CPU spike
  if (tick === 5) metric.errorRate = 0.05; // Error burst

  // Observe
  const deltas = detector.observe({
    cpu: metric.cpu,
    memory: metric.memory,
    latency: metric.latency,
    error_rate: metric.errorRate,
  });

  // Process through learning cycle
  learning.experience({ value: metric.cpu });

  // Get significant deltas
  const significant = Object.entries(deltas)
    .filter(([, d]) => d.magnitude > d.tolerance)
    .map(([, d]) => d);

  if (significant.length > 0) {
    console.log(`Tick ${tick}:`);
    for (const d of significant) {
      console.log(`  ${formatDelta(d)}`);
    }

    // Allocate
    const prioritized = detector.prioritize(3);
    const allocations = budget.allocate(prioritized);

    if (allocations.length > 0) {
      console.log(`  Allocated: ${allocations[0].allocated.toFixed(1)} units → ${allocations[0].delta.streamId}`);
    }

    console.log('');
  }
}

console.log('══════════ Summary ══════════');
console.log('');
console.log(`Budget remaining: ${budget.remaining.toFixed(1)}`);
console.log(`Learning phase: ${learning.phase}`);
console.log(`Scripts learned: ${learning.currentState.scriptsActive}`);
console.log(`Cognitive load remaining: ${((1 - learning.currentState.cognitiveLoad) * 100).toFixed(1)}%`);
