# Forge-Proxy v0

A deterministic stand-in for Forgemaster decisions that are decidable from the
pinned FM corpus — and a hard refusal everywhere they are not.

Built from `memory/forge-recon.md` (Lane F1, 2026-09-20). FM is a persona, not
an account; this proxy answers in his decision *format* from his documented
precedents, and refuses — `this needs the real Forge` — on the five override
conditions from the recon. It never guesses: an unmatched question renders
UNRESOLVED.

## Resolution order

1. **Worked-example match** — the corpus's three settled precedents
   (`examples/worked-examples.json`): Path A ships/Path B gated; P0-gaps-green
   = done; trinity multiplicative, never additive. These always answer, and
   their answers *reinforce* the FM gate.
2. **Escalation triggers** — five executable rules (toolchain verification,
   constitution amendment, Path B / Awaiting-FM-Review, live GPU deploy,
   irreversible action). Any single one → refusal.
3. **UNRESOLVED** — the proxy renders the format skeleton and stops.

## Honest limits (from the recon)

The proxy cannot do FM's taste-for-disappearance, cannot grant Path B, has no
snap-relationship, cannot compile to verify, and has no standing to tell Casey
no. Those are features of the refusal layer, not gaps to patch.

## Corpus pins

`CORPUS_MANIFEST` + `GOVERNING_LINES` in `forge-proxy.mjs` pin every cited
file to a ref (sunset-ecosystem @ `f188a33`, forgemaster @ main 2026-08-26,
constraint-theory-core @ main 2026-07-13). Pass corpus checkouts and drift
surfaces instead of passing silently:

```sh
FORGE_CORPUS_SUNSET=/path/to/sunset-ecosystem node --test test/
node forge-proxy.mjs "your question" /path/to/sunset-ecosystem
```

## Tests

```sh
node --test test/          # 14 tests: 3 worked examples, 5 refusals, classifier
                           # boundary, renderer discipline, corpus pins
```

## Recon-first correction carried in this build

Worked example 2's citations were corrected at build time: the recon draft
cited "STRATEGY.md Tracks #2", which does not exist verbatim in the pinned
checkout. The real anchors are `memory.md` ("All reverse-actualization P0 gaps
closed") and `STRATEGY.md` §Approach. The stale citation is asserted absent in
the regression suite.
