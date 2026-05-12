/**
 * Tests for Zeitgeist Protocol — TypeScript implementation
 * Run with: npx tsx test_zeitgeist.ts
 */

import {
  Zeitgeist, PrecisionState, ConfidenceState, TrajectoryState,
  ConsensusState, TemporalState, Trend, Phase,
} from "./zeitgeist.ts";

function randRange(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

function randomZeitgeist(): Zeitgeist {
  const bloom = new Uint8Array(32);
  for (let i = 0; i < 32; i++) bloom[i] = Math.floor(Math.random() * 256);

  const crdt = new Map<number, number>();
  for (let i = 0; i < Math.floor(Math.random() * 5); i++) {
    crdt.set(Math.floor(Math.random() * 1e18), Math.floor(Math.random() * 1e18));
  }

  return new Zeitgeist(
    new PrecisionState(randRange(0.001, 99999), randRange(0, 1), Math.random() > 0.5),
    new ConfidenceState(bloom, Math.floor(Math.random() * 256), randRange(0, 1)),
    new TrajectoryState(
      randRange(0, 1),
      [Trend.STABLE, Trend.RISING, Trend.FALLING, Trend.CHAOTIC][Math.floor(Math.random() * 4)],
      randRange(-10, 10),
    ),
    new ConsensusState(randRange(0, 1), randRange(0, 1), crdt),
    new TemporalState(
      randRange(0, 1),
      [Phase.IDLE, Phase.APPROACHING, Phase.SNAP, Phase.HOLD][Math.floor(Math.random() * 4)],
      randRange(0, 1),
    ),
  );
}

// ── Merge law tests ────────────────────────────────────────

let passed = 0;
let failed = 0;

function assert(condition: boolean, msg: string) {
  if (!condition) {
    console.error(`FAIL: ${msg}`);
    failed++;
  } else {
    passed++;
  }
}

// Commutativity: 100 iterations
for (let i = 0; i < 100; i++) {
  const a = randomZeitgeist();
  const b = randomZeitgeist();
  assert(a.merge(b).equals(b.merge(a)), `Commutativity violated at iteration ${i}`);
}

// Associativity: 100 iterations
for (let i = 0; i < 100; i++) {
  const a = randomZeitgeist();
  const b = randomZeitgeist();
  const c = randomZeitgeist();
  assert(
    a.merge(b).merge(c).equals(a.merge(b.merge(c))),
    `Associativity violated at iteration ${i}`,
  );
}

// Idempotency: 100 iterations
for (let i = 0; i < 100; i++) {
  const a = randomZeitgeist();
  assert(a.merge(a).equals(a), `Idempotency violated at iteration ${i}`);
}

// JSON roundtrip: 50 iterations
for (let i = 0; i < 50; i++) {
  const zg = randomZeitgeist();
  const encoded = zg.encode();
  const decoded = Zeitgeist.decode(encoded);
  assert(decoded.equals(zg), `JSON roundtrip failed at iteration ${i}`);
}

// Alignment valid
{
  const zg = randomZeitgeist();
  const report = zg.checkAlignment();
  assert(report.aligned, `Random ZG should be aligned: ${report.violations.join(", ")}`);
}

// Alignment detects violations
{
  const zg = randomZeitgeist();
  zg.precision.deadband = -1;
  zg.confidence.certainty = 2;
  zg.trajectory.hurst = 1.5;
  zg.temporal.beat_pos = -0.5;
  const report = zg.checkAlignment();
  assert(!report.aligned, "Should detect violations");
  assert(report.violations.length >= 4, `Expected 4+ violations, got ${report.violations.length}`);
}

console.log(`\nResults: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
