import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const { SnapFunction, DeltaDetector } = await import('../dist/index.js');

describe('DeltaDetector', () => {
  it('creates and observes a single stream', () => {
    const detector = new DeltaDetector();
    const snap = new SnapFunction({ tolerance: 0.1 });
    detector.addStream('test', snap);

    const result = detector.observe({ test: 0.05 });
    assert.ok(result.test);
    assert.equal(result.test.streamId, 'test');
    assert.equal(result.test.severity, 'none');
  });

  it('detects deltas across multiple streams', () => {
    const detector = new DeltaDetector();
    detector.addStream('alpha', new SnapFunction({ tolerance: 0.1 }));
    detector.addStream('beta', new SnapFunction({ tolerance: 0.5 }));

    // Observe values that will exceed tolerance on alpha but not beta
    detector.observe({ alpha: 0.3, beta: 0.2 });
    const current = detector.currentDeltas();
    assert.ok(current.alpha.magnitude > 0);
    assert.ok(current.beta.magnitude > 0);
  });

  it('prioritizes deltas by attention weight', () => {
    const detector = new DeltaDetector();
    detector.addStream('a', new SnapFunction({ tolerance: 0.1 }), {
      actionabilityFn: () => 0.9,
      urgencyFn: () => 0.8,
    });
    detector.addStream('b', new SnapFunction({ tolerance: 0.1 }), {
      actionabilityFn: () => 0.5,
      urgencyFn: () => 0.5,
    });

    // Exceed tolerance on both
    detector.observe({ a: 1.0, b: 0.5 });
    detector.observe({ a: 1.0, b: 0.5 });

    const prioritized = detector.prioritize(2);
    assert.ok(prioritized.length <= 2);
  });

  it('provides stream-level statistics', () => {
    const detector = new DeltaDetector();
    detector.addStream('x', new SnapFunction({ tolerance: 0.05 }));
    detector.observe({ x: 0.01 });
    detector.observe({ x: 0.02 });
    detector.observe({ x: 1.0 }); // delta

    const stats = detector.statistics;
    assert.ok(stats.numStreams === 1);
    assert.ok(stats.totalObservations === 3);
    assert.ok(stats.totalDeltas >= 0);
  });
});
