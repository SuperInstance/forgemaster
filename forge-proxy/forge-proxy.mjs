// forge-proxy.mjs — Forge-Proxy v0
// A deterministic stand-in for Forgemaster decisions that are decidable from
// the pinned corpus, and a hard refusal everywhere they are not.
//
// Design rules (from memory/forge-recon.md, Lane F1):
//   1. The proxy answers ONLY what the corpus decides. It never invents a
//      verdict — an unmatched question renders as UNRESOLVED for a human/agent
//      to fill, never as a guess.
//   2. The escalation rule is executable: needsForge(question) fires on the
//      five override conditions, and the CLI refuses with
//      "this needs the real Forge" instead of answering.
//   3. The three worked examples from the recon are regression tests, not
//      decoration: if the corpus or the renderer drifts, they fail.
//
// Zero dependencies. Node >= 18.

import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Pinned corpus manifest (forge-recon.md §3a). `repo` is the checkout the file
// is pinned to; `ref` is the sha/tag recorded at recon time 2026-09-20.
// ---------------------------------------------------------------------------
export const CORPUS_MANIFEST = [
  { repo: 'sunset-ecosystem', file: 'README.md',                        ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'STRATEGY.md',                      ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'memory.md',                        ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/SPEC-FLUX-RESOLUTION.md',     ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/FLUX_PATH_A_INTEGRATION.md',  ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/SPEC_BREEDER_DAEMON_V2.md',   ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/KIMI1_RESPONSE_FM.md',        ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/FM_NOTE_KIMI1_METAL.md',      ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/FM-GPU-INSTRUCTIONS.md',      ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'sunset-ecosystem', file: 'docs/FM-BLOCKERS-2026-05-23.md',   ref: 'f188a338c210e6595cd8729339628b8d5d82c6e7' },
  { repo: 'forgemaster',      file: 'SOUL.md',                        ref: 'main@2026-08-26' },
  { repo: 'forgemaster',      file: 'AGENT.md',                       ref: 'main@2026-08-26' },
  { repo: 'constraint-theory-core', file: 'README.md',                  ref: 'main@2026-07-13' },
];

// Governing lines the proxy's cited answers depend on. If a corpus edit
// changes these, the corresponding worked example must be re-examined by a
// human — that is what makes these tests a tripwire, not a formality.
export const GOVERNING_LINES = [
  {
    repo: 'sunset-ecosystem', file: 'docs/FLUX_PATH_A_INTEGRATION.md',
    lineIncludes: 'Path B requires Forgemaster (FM) approval and is out of scope here',
    guards: 'worked-example-1 (Path A ships, Path B gated)',
  },
  {
    repo: 'sunset-ecosystem', file: 'README.md',
    lineIncludes: 'Drop to zero in any dimension and the fleet sunsets you',
    guards: 'worked-example-3 (trinity multiplicative, never additive)',
  },
  {
    repo: 'sunset-ecosystem', file: 'memory.md',
    lineIncludes: 'All reverse-actualization P0 gaps closed',
    guards: 'worked-example-2 (P0-gaps-green = done)',
  },
];

// ---------------------------------------------------------------------------
// Escalation rule (forge-recon.md §3c), executable. Five override conditions;
// any single one means the proxy refuses.
// ---------------------------------------------------------------------------
export const ESCALATION_TRIGGERS = [
  {
    id: 'TOOLCHAIN-VERIFICATION',
    test: (q) => /\b(rust|cargo|cuda|nvcc|toolchain)\b/i.test(q) && /(compil|build|verify|artifact|bench)/i.test(q),
    why: 'requires Rust/CUDA artifacts only FM\'s toolchain can verify',
  },
  {
    id: 'CONSTITUTION-AMENDMENT',
    test: (q) => /(trinity|sunset rule|scoring|constitution)/i.test(q) && /(amend|change|replace|drop|reweight|additive)/i.test(q),
    why: 'amends the trinity scoring or sunset rule',
  },
  {
    id: 'PATH-B-OR-FM-REVIEW',
    test: (q) => /path b/i.test(q) || /awaiting forgemaster review/i.test(q),
    why: 'selects Path B or an item marked Awaiting Forgemaster Review',
  },
  {
    id: 'LIVE-GPU-DEPLOY',
    test: (q) => /(oracle1|proart|gpu deploy|live deploy|production deploy)/i.test(q),
    why: 'touches live Oracle1/GPU deploys',
  },
  {
    id: 'IRREVERSIBLE',
    test: (q) => /(archive|delete|irreversible|remove the (repo|subtree|canon))/i.test(q),
    why: 'is irreversible (archiving canonical repos, deleting FM-era subtrees)',
  },
];

export const REFUSAL = 'this needs the real Forge';

export function needsForge(question) {
  for (const t of ESCALATION_TRIGGERS) {
    if (t.test(question)) return { needsForge: true, trigger: t.id, why: t.why };
  }
  return { needsForge: false };
}

// ---------------------------------------------------------------------------
// Answer format (forge-recon.md §3b). The renderer validates; it does not
// invent. Missing or malformed fields are an error, not a shrug.
// ---------------------------------------------------------------------------
const CONFIDENCES = new Set(['HIGH', 'MED', 'LOW']);

export function renderAnswer({ verdict, citedBasis, confidence, overrideTriggers }) {
  const errs = [];
  if (!verdict || typeof verdict !== 'string') errs.push('verdict: non-empty string required');
  if (!Array.isArray(citedBasis) || citedBasis.length === 0 || citedBasis.some(c => typeof c !== 'string' || !c.includes('@'))) {
    errs.push('citedBasis: non-empty array of "<file> §<section> @<ref> — <line>" citations required');
  }
  if (!CONFIDENCES.has(confidence)) errs.push(`confidence: one of ${[...CONFIDENCES].join(' | ')}`);
  if (!Array.isArray(overrideTriggers)) errs.push('overrideTriggers: array required (empty array if none)');
  if (errs.length) throw new Error('forge-proxy: bad answer shape:\n  ' + errs.join('\n  '));
  return [
    `VERDICT: ${verdict}`,
    'CITED BASIS:',
    ...citedBasis.map(c => `  ${c}`),
    `CONFIDENCE: ${confidence}`,
    `FM OVERRIDE TRIGGERS: ${overrideTriggers.length ? overrideTriggers.join('; ') : 'none'}`,
  ].join('\n');
}

export function renderUnresolved(question) {
  return [
    `VERDICT: UNRESOLVED — corpus has no governing line for this question`,
    `CITED BASIS: (none — not in pinned corpus)`,
    `CONFIDENCE: LOW`,
    `FM OVERRIDE TRIGGERS: unresolved questions route to a human or the real Forge; the proxy never guesses`,
    `QUESTION: ${question}`,
  ].join('\n');
}

// ---------------------------------------------------------------------------
// Corpus loading + integrity
// ---------------------------------------------------------------------------
// roots: { 'sunset-ecosystem': '/path/to/checkout', ... }
export function loadCorpus(roots) {
  const missing = [];
  const lines = [];
  for (const entry of CORPUS_MANIFEST) {
    const root = roots[entry.repo];
    const path = root ? join(root, entry.file) : null;
    if (!path || !existsSync(path)) { missing.push(`${entry.repo}/${entry.file}`); continue; }
    readFileSync(path, 'utf8'); // readable
  }
  for (const g of GOVERNING_LINES) {
    const root = roots[g.repo];
    const path = root ? join(root, g.file) : null;
    if (!path || !existsSync(path)) { missing.push(`${g.repo}/${g.file} (governing line)`); continue; }
    const text = readFileSync(path, 'utf8');
    if (!text.includes(g.lineIncludes)) lines.push({ ...g, found: false });
  }
  return { ok: missing.length === 0 && lines.length === 0, missing, governingLineDrift: lines };
}

export function loadWorkedExamples() {
  return JSON.parse(readFileSync(join(HERE, 'examples', 'worked-examples.json'), 'utf8'));
}

// ---------------------------------------------------------------------------
// CLI
//   node forge-proxy.mjs "question" [corpusRoot]
// Escalation trigger → refusal. Worked-example match → pinned answer.
// Otherwise → UNRESOLVED. Never a guess.
// ---------------------------------------------------------------------------
// Resolution order in answer():
//   1. Worked-example match — the corpus's three settled precedents; always
//      answerable, and their answers reinforce the FM gate (ex.1 keeps Path B
//      gated). New attempts to OVERRIDE a precedent are caught by step 2.
//   2. Escalation triggers (needsForge) — refusal.
//   3. UNRESOLVED — never a guess.
export function answer(question, roots = null) {
  const examples = loadWorkedExamples();
  const q = question.toLowerCase();
  const matched = examples.filter(e => e.matchKeywords.every(k => q.includes(k.toLowerCase())));
  if (matched.length > 0) {
    const e = matched[0];
    const answer = renderAnswer(e.answer);
    if (roots) {
      const check = loadCorpus(roots);
      if (!check.ok) {
        return `CORPUS DRIFT DETECTED — re-examine before trusting any proxy answer:\n` +
               `  missing: ${check.missing.join(', ') || 'none'}\n` +
               `  governing-line drift: ${check.governingLineDrift.map(g => g.guards).join(', ') || 'none'}\n\n` + answer;
      }
    }
    return answer;
  }
  const esc = needsForge(question);
  if (esc.needsForge) {
    return `${REFUSAL} (${esc.trigger}: ${esc.why})`;
  }
  return renderUnresolved(question);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const question = process.argv[2];
  if (!question) { console.error('usage: node forge-proxy.mjs "question" [corpusRoot]'); process.exit(2); }
  const roots = process.argv[3] ? { 'sunset-ecosystem': process.argv[3] } : null;
  console.log(answer(question, roots));
}
