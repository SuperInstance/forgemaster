// Forge-Proxy v0 regression suite.
//   node --test forge-proxy/test/
// The three worked examples from memory/forge-recon.md are the regressions:
// they must render in the answer format, cite real corpus anchors, and never
// be refused. Fresh override attempts MUST be refused. Corpus drift must
// surface, not pass silently.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  answer, needsForge, renderAnswer, renderUnresolved, loadCorpus,
  CORPUS_MANIFEST, GOVERNING_LINES, ESCALATION_TRIGGERS, REFUSAL,
} from '../forge-proxy.mjs';
import { existsSync } from 'node:fs';

const SUNSET = process.env.FORGE_CORPUS_SUNSET || '/tmp/sunset-ecosystem';
const corpusAvailable = existsSync(`${SUNSET}/docs/FLUX_PATH_A_INTEGRATION.md`);

// --- worked examples: the proxy's settled precedents -----------------------

test('worked example 1 — Path A ships, Path B gated', () => {
  const out = answer('Should we ship FLUX via Path A or build Path B now?');
  assert.match(out, /^VERDICT: Ship Path A/);
  assert.match(out, /CITED BASIS:[\s\S]*FLUX_PATH_A_INTEGRATION\.md §Summary @f188a33/);
  assert.match(out, /CONFIDENCE: HIGH/);
  assert.match(out, /FM OVERRIDE TRIGGERS: .+exceeds the Python fallback/);
  assert.ok(!out.includes(REFUSAL), 'settled precedent must not be refused');
});

test('worked example 2 — P0 gaps green = done (corrected citations)', () => {
  const out = answer('Can breeding v2 ship with reverse-actualization P0 gaps open?');
  assert.match(out, /^VERDICT: No/);
  assert.match(out, /memory\.md @f188a33 — "All reverse-actualization P0 gaps closed"/);
  assert.doesNotMatch(out, /Tracks #2/, 'stale recon citation must be gone');
});

test('worked example 3 — trinity multiplicative, never additive', () => {
  const out = answer('Should agent scoring be multiplicative (ethos×pathos×logos) or additive-weighted?');
  assert.match(out, /^VERDICT: Multiplicative, unchanged/);
  assert.match(out, /ethos × pathos × logos/);
  assert.match(out, /CONFIDENCE: HIGH/);
});

// --- escalation rule: five override conditions, executable -----------------

const freshOverrides = [
  ['TOOLCHAIN-VERIFICATION', 'Can you compile and verify the Rust CUDA artifact on your side?'],
  ['CONSTITUTION-AMENDMENT', 'Let\'s amend the trinity scoring to additive weighting.'],
  ['PATH-B-OR-FM-REVIEW', 'Greenlight Path B implementation.'],
  ['LIVE-GPU-DEPLOY', 'Proceed with the Oracle1 GPU live deploy tonight.'],
  ['IRREVERSIBLE', 'Please archive the flux-spec repo, it is superseded.'],
];

for (const [trigger, question] of freshOverrides) {
  test(`fresh override attempt refused — ${trigger}`, () => {
    const out = answer(question);
    assert.ok(out.includes(REFUSAL), `expected refusal, got:\n${out}`);
    assert.ok(out.includes(trigger));
    assert.doesNotMatch(out, /^VERDICT:/, 'a refusal is not an answer');
  });
}

test('all five escalation triggers fire via needsForge classifier', () => {
  const fired = new Set(freshOverrides.map(([t, q]) => needsForge(q).trigger));
  assert.deepEqual(fired, new Set([
    'TOOLCHAIN-VERIFICATION', 'CONSTITUTION-AMENDMENT', 'PATH-B-OR-FM-REVIEW',
    'LIVE-GPU-DEPLOY', 'IRREVERSIBLE',
  ]));
  assert.equal(ESCALATION_TRIGGERS.length, 5, 'exactly the five recon conditions — no more, no fewer');
});

test('benign corpus-decidable questions do not escalate', () => {
  for (const q of [
    'What is the deadband funnel for?',
    'How does the metronome consensus tick?',
    'Where is the breeding daemon config?',
  ]) {
    assert.equal(needsForge(q).needsForge, false, q);
  }
});

test('unmatched, non-escalating question renders UNRESOLVED — never a guess', () => {
  const out = answer('Should we rename the eisenstein module to lattices?');
  assert.match(out, /^VERDICT: UNRESOLVED/);
  assert.match(out, /CONFIDENCE: LOW/);
});

// --- renderer discipline ----------------------------------------------------

test('renderAnswer rejects malformed answers', () => {
  assert.throws(() => renderAnswer({ verdict: '', citedBasis: ['x @y — z'], confidence: 'HIGH', overrideTriggers: [] }));
  assert.throws(() => renderAnswer({ verdict: 'v', citedBasis: ['no-ref-here'], confidence: 'HIGH', overrideTriggers: [] }));
  assert.throws(() => renderAnswer({ verdict: 'v', citedBasis: ['f @r — l'], confidence: 'SURE', overrideTriggers: [] }));
  assert.throws(() => renderAnswer({ verdict: 'v', citedBasis: ['f @r — l'], confidence: 'MED' }));
});

test('renderUnresolved carries the question and refuses to guess', () => {
  const out = renderUnresolved('what is the snap?');
  assert.match(out, /UNRESOLVED/);
  assert.match(out, /what is the snap\?/);
});

// --- corpus pin integrity (gated on local checkout) -------------------------

test('pinned corpus complete + governing lines intact', { skip: !corpusAvailable && 'FORGE_CORPUS_SUNSET checkout not present' }, () => {
  const roots = {
    'sunset-ecosystem': SUNSET,
    'forgemaster': process.env.FORGE_CORPUS_FORGEMASTER || '/tmp/forge-proxy-build',
    'constraint-theory-core': process.env.FORGE_CORPUS_CTC || '/nonexistent-ctc',
  };
  const check = loadCorpus(roots);
  // sunset-ecosystem entries + governing lines must all verify
  const sunsetMissing = check.missing.filter(m => m.startsWith('sunset-ecosystem/'));
  assert.deepEqual(sunsetMissing, [], `missing: ${sunsetMissing}`);
  assert.deepEqual(check.governingLineDrift, [], 'governing lines drifted — worked examples need re-examination');
  assert.equal(GOVERNING_LINES.length, 3);
  assert.ok(CORPUS_MANIFEST.length >= 10);
});
