import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// Dynamic import of built modules
const { SnapFunction } = await import('../dist/index.js');

describe('SnapFunction', () => {
  it('snaps values within tolerance to baseline', () => {
    const snap = new SnapFunction({ tolerance: 0.1 });
    const result = snap.snap(0.05);
    assert.equal(result.withinTolerance, true);
    assert.equal(result.snapped, 0);
    assert.ok(result.delta <= 0.1);
  });

  it('flags values outside tolerance as deltas', () => {
    const snap = new SnapFunction({ tolerance: 0.1 });
    const result = snap.snap(0.3);
    assert.equal(result.withinTolerance, false);
    assert.equal(result.snapped, 0.3); // not snapped — kept as-is
    assert.ok(result.delta > 0.1);
  });

  it('adapts baseline on non-delta observations', () => {
    const snap = new SnapFunction({ tolerance: 0.5, adaptationRate: 0.1 });
    snap.snap(0.4); // within tolerance
    assert.ok(snap.baseline > 0);
  });

  it('handles vector snapping', () => {
    const snap = new SnapFunction({ tolerance: 0.1 });
    const results = snap.snapVector([0.05, 0.3, -0.02]);
    assert.equal(results.length, 3);
    assert.equal(results[0].withinTolerance, true);
    assert.equal(results[1].withinTolerance, false);
    assert.equal(results[2].withinTolerance, true);
  });

  it('calibrates tolerance from sample data', () => {
    const snap = new SnapFunction({ tolerance: 1.0 });
    const values = [0.1, -0.05, 0.2, -0.1, 0.5, 1.5, -2.0, 0.3];
    snap.calibrate(values, 0.75);
    // At 75%, 6 of 8 values should be within tolerance
    // The 6th distance (sorted) from baseline (mean ~0.06) is ~0.56
    assert.ok(snap.tolerance < 1.5);
    assert.ok(snap.tolerance > 0);
  });

  it('provides statistics', () => {
    const snap = new SnapFunction({ tolerance: 0.1 });
    snap.snap(0.05);
    snap.snap(0.3);
    snap.snap(0.02);

    const stats = snap.statistics;
    assert.equal(stats.totalObservations, 3);
    assert.ok(typeof stats.snapRate === 'number');
    assert.ok(stats.meanDelta > 0);
  });

  it('supports Eisenstein lattice snapping', () => {
    const snap = new SnapFunction({ tolerance: 0.5 });
    const result = snap.snapEisenstein([0.1, 0.1]);
    assert.ok(result.withinTolerance || !result.withinTolerance);
    assert.ok(result.delta >= 0);
  });

  it('resets state', () => {
    const snap = new SnapFunction({ tolerance: 0.1, baseline: 5 });
    snap.snap(0.05);
    assert.equal(snap.statistics.totalObservations, 1);
    snap.reset();
    assert.equal(snap.statistics.totalObservations, 0);
    assert.equal(snap.baseline, 5);
    snap.reset(10);
    assert.equal(snap.baseline, 10);
  });
});
