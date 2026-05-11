import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const { ScriptLibrary } = await import('../dist/index.js');

describe('ScriptLibrary', () => {
  it('learns and matches a script', () => {
    const lib = new ScriptLibrary({ matchThreshold: 0.85 });
    lib.learn([0.1, 0.2, 0.3], 'fold', 'fold_weak_hand');

    const match = lib.findBestMatch([0.12, 0.19, 0.31]);
    assert.ok(match);
    assert.ok(match.isMatch);
    assert.ok(match.confidence >= 0.85);
  });

  it('returns null when no script matches', () => {
    const lib = new ScriptLibrary({ matchThreshold: 0.9 });
    lib.learn([1, 0, -1], 'response_a');

    const match = lib.findBestMatch([100, 200, 300]);
    assert.ok(!match || !match.isMatch);
  });

  it('lists all matches above a threshold', () => {
    const lib = new ScriptLibrary({ matchThreshold: 0.8 });
    lib.learn([1, 0], 'script1', 'first');
    lib.learn([0, 1], 'script2', 'second');

    const matches = lib.findAllMatches([1, 0], 0.5);
    assert.ok(matches.length >= 1);
    assert.equal(matches[0].scriptId, lib['_scripts'].keys().next().value);
  });

  it('archives scripts via forget', () => {
    const lib = new ScriptLibrary();
    const script = lib.learn([1, 2, 3], 'response', 'test_script');
    assert.ok(lib.forget(script.id));
    assert.ok(!lib.forget('nonexistent'));
  });

  it('degrades failing scripts via prune', () => {
    const lib = new ScriptLibrary();
    const script = lib.learn([0.5, 0.5], 'bad_response', 'bad_script');

    // Simulate failures
    for (let i = 0; i < 10; i++) {
      lib.recordUse(script.id, false);
    }

    lib.prune(5, 0.3);

    const retrieved = lib.get(script.id);
    assert.ok(retrieved);
    assert.equal(retrieved.status, 'degraded');
  });
});
