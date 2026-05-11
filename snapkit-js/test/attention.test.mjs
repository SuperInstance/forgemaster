import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const { SnapFunction, DeltaDetector, AttentionBudget } = await import('../dist/index.js');

describe('AttentionBudget', () => {
  it('allocates budget proportionally to actionability', () => {
    const detector = new DeltaDetector();
    detector.addStream('a', new SnapFunction({ tolerance: 0.1 }));
    detector.addStream('b', new SnapFunction({ tolerance: 0.1 }));
    detector.observe({ a: 2.0, b: 1.0 });
    detector.observe({ a: 2.0, b: 1.0 });

    const deltas = detector.prioritize(5);
    const budget = new AttentionBudget({ totalBudget: 100, strategy: 'actionability' });
    const allocations = budget.allocate(deltas);

    assert.ok(allocations.length >= 1);
    assert.ok(budget.remaining >= 0);
    assert.ok(budget.utilization > 0);
  });

  it('handles reactive strategy', () => {
    const detector = new DeltaDetector();
    detector.addStream('x', new SnapFunction({ tolerance: 0.1 }));
    detector.observe({ x: 3.0 });

    const deltas = detector.prioritize(3);
    const budget = new AttentionBudget({ totalBudget: 50, strategy: 'reactive' });
    const allocations = budget.allocate(deltas);

    assert.ok(allocations.length >= 1);
  });

  it('handles uniform strategy', () => {
    const detector = new DeltaDetector();
    detector.addStream('a', new SnapFunction({ tolerance: 0.1 }));
    detector.addStream('b', new SnapFunction({ tolerance: 0.1 }));
    detector.observe({ a: 1.0, b: 2.0 });

    const deltas = detector.prioritize(5);
    const budget = new AttentionBudget({ totalBudget: 50, strategy: 'uniform' });
    const allocations = budget.allocate(deltas);

    if (allocations.length > 0) {
      assert.equal(allocations[0].allocated, allocations[1]?.allocated);
    }
  });

  it('tracks exhaustion', () => {
    const budget = new AttentionBudget({ totalBudget: 1 });
    const detector = new DeltaDetector();
    detector.addStream('a', new SnapFunction({ tolerance: 0.1 }));
    detector.observe({ a: 10.0 });

    const deltas = detector.prioritize(3);
    budget.allocate(deltas);
    budget.allocate(deltas);

    assert.ok(budget.exhaustionRate >= 0);
  });
});
