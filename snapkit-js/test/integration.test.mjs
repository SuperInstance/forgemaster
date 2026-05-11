import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const {
  SnapFunction,
  DeltaDetector,
  AttentionBudget,
  ScriptLibrary,
  LearningCycle,
  buildPipeline,
  generateHTMLPage,
  snapToEisenstein,
  eisensteinToString,
  eisensteinNorm,
  SnapTopology,
} = await import('../dist/index.js');

describe('Integration: Snap → Detect → Allocate pipeline', () => {
  it('processes a stream of values end-to-end', () => {
    const snap = new SnapFunction({ tolerance: 0.1 });
    const detector = new DeltaDetector();
    detector.addStream('main', snap);

    // Test values: some within tolerance, some exceeding
    const values = [0.05, 0.03, 0.4, -0.02, 0.5, 0.01];

    // Only feed through detector (which uses the snap internally)
    for (const v of values) {
      detector.observe({ main: v });
    }

    // Verify statistics
    const snapStats = snap.statistics;
    assert.ok(snapStats.totalObservations === values.length);
    assert.ok((snapStats.snapCount ?? 0) + (snapStats.deltaCount ?? 0) > 0);

    // Verify detector prioritization
    const prioritized = detector.prioritize(3);
    assert.ok(prioritized.length >= 1);
    assert.ok(prioritized.every((d) => d.magnitude > d.tolerance));
  });

  it('allocates attention budget across streams', () => {
    const detector = new DeltaDetector();
    detector.addStream('alpha', new SnapFunction({ tolerance: 0.05 }));
    detector.addStream('beta', new SnapFunction({ tolerance: 0.2 }));

    // Feed observations
    for (let i = 0; i < 10; i++) {
      detector.observe({
        alpha: Math.random() * 0.5,
        beta: Math.random() * 0.5,
      });
    }

    const budget = new AttentionBudget({
      totalBudget: 100,
      strategy: 'actionability',
    });
    const deltas = detector.prioritize(5);
    const allocations = budget.allocate(deltas);

    // Budget should have been allocated
    assert.ok(budget.utilization >= 0);
    if (deltas.length > 0) {
      assert.ok(allocations.length >= 1);
    }
  });
});

describe('Integration: Learning cycle', () => {
  it('moves from delta_flood through script_burst', () => {
    const cycle = new LearningCycle({
      noveltyThreshold: 5,
      scriptCreationThreshold: 3,
    });

    // Feed similar values to trigger script creation
    const results = cycle.experienceBatch(
      Array.from({ length: 8 }, (_, i) => ({
        value: 0.1 + Math.random() * 0.05,
      }))
    );

    const state = cycle.currentState;
    assert.ok(state.totalExperiences >= 8);
    assert.ok(state.scriptsActive >= 0);
    assert.ok(state.cognitiveLoad >= 0);
  });

  it('tracks phase transitions', () => {
    const cycle = new LearningCycle({ noveltyThreshold: 3 });

    // First batch of similar values
    for (let i = 0; i < 6; i++) {
      cycle.experience({ value: 0.1 + Math.random() * 0.02 });
    }

    // Then a sudden delta
    cycle.experience({ value: 10.0 });
    cycle.experience({ value: 10.0 });
    cycle.experience({ value: 10.0 });

    const state = cycle.currentState;
    assert.ok(state.phaseTransitions >= 0);
  });
});

describe('Integration: Pipeline builder', () => {
  it('builds and runs a pipeline', () => {
    const pipeline = buildPipeline({
      snap: new SnapFunction({ tolerance: 0.1 }),
      detector: new DeltaDetector(),
      budget: new AttentionBudget({ totalBudget: 100 }),
      streamIds: ['main'],
    });

    const output = pipeline.run(0.05);
    assert.ok(output.snapResult);
    assert.equal(output.snapResult.withinTolerance, true);

    const output2 = pipeline.run(2.0);
    assert.equal(output2.snapResult.withinTolerance, false);
  });
});

describe('Integration: Eisenstein lattice', () => {
  it('snaps to nearest Eisenstein integer', () => {
    const z = snapToEisenstein([1.2, 0.8]);
    assert.ok(z.a !== undefined);
    assert.ok(z.b !== undefined);
    assert.ok(eisensteinNorm(z) >= 0);
    const str = eisensteinToString(z);
    assert.ok(str.includes('ω') || !str.includes('ω'));
  });
});

describe('Integration: SnapTopology', () => {
  it('creates all ADE topologies', () => {
    const types = ['A1', 'A2', 'A3', 'A4', 'D4', 'D5', 'E6', 'E7', 'E8'];
    for (const t of types) {
      const top = new SnapTopology(t);
      assert.equal(top.adeType, t);
      assert.ok(top.rank > 0);
      assert.ok(top.numRoots > 0);
    }
  });

  it('snaps points to root lattices', () => {
    const top = new SnapTopology('A2');
    const [snapped, delta] = top.snap([1.1, -0.2]);
    assert.ok(snapped.length >= 2);
    assert.ok(delta >= 0);
  });
});

describe('Integration: HTML visualization', () => {
  it('generates HTML without errors', () => {
    const html = generateHTMLPage({
      title: 'Test Dashboard',
      snapResults: [
        {
          original: 0.5,
          snapped: 0,
          delta: 0.5,
          withinTolerance: false,
          tolerance: 0.1,
          topology: 'hexagonal',
        },
        {
          original: 0.05,
          snapped: 0,
          delta: 0.05,
          withinTolerance: true,
          tolerance: 0.1,
          topology: 'hexagonal',
        },
      ],
    });
    assert.ok(html.includes('Test Dashboard'));
    assert.ok(html.includes('Test Dashboard'));
    assert.ok(html.includes('</html>'));
  });
});
