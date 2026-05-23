# Beta Test Synthesis — FLUX Ecosystem

4 outsider testers (Python, Rust, JS, Newcomer). All documented their journey.

## Aggregate Scores

| Metric | Python | Rust | JS | Newcomer | Avg |
|--------|--------|------|----|----------|-----|
| README clarity | 5 | 8 | 8 | 5 | 6.5 |
| Install experience | 9 | 9 | 8 | — | 8.7 |
| API discoverability | 4 | 6 | — | 5 | 5 |
| Would use | depends | maybe | yes | bookmark | — |
| Trust | 6 | 7 | 7 | — | 6.7 |

## Critical Issues (Must Fix)

### 1. `check_vector()` API missing
**Who found it:** Python tester
**What:** `check(3000)` checks ONE value against ALL constraints. Real sensor systems need to check [temp, pressure, voltage, ...] where each value maps to its own constraint.
**Fix:** Add `check_vector(values: list[float]) → int` that maps value[i] to constraint[i].

### 2. Not published to package registries
**Who found it:** JS tester, Newcomer
**What:** `@flux/check` not on npm. `flux-lib` not on PyPI. Can only install via git URL.
**Fix:** Publish to npm and PyPI. This is a prerequisite for anyone actually using these.

### 3. 5-minute quickstart broken
**Who found it:** Newcomer
**What:** Links to nonexistent repos. Concept pages may 404 in docs site rendering.
**Fix:** Audit every link in getting-started.md and flux-docs.

### 4. Eisenstein / hex arithmetic never explained
**Who found it:** Newcomer
**What:** The main ecosystem README mentions Eisenstein integers and hex arithmetic without explaining what they are. Visitors hit Wikipedia to understand the core math.
**Fix:** Add a "Background" section to the main README or link to a concepts page.

## High-Priority Issues (Should Fix)

### 5. 8-constraint hard limit not prominent
**Who found it:** Python tester
**What:** uint8 error mask = max 8 constraints. Not mentioned until you dig in.
**Fix:** State the limit prominently. Explain how to work around it (multiple engines).

### 6. Thermodynamics jargon needs practical translation
**Who found it:** Python tester
**What:** "Partition function Z = 2.49" means nothing without context. "Close to 1 = over-constrained, large = many possible states" needed.
**Fix:** Add practical interpretation guide after each theoretical concept.

### 7. Rust crate is fracture-only, no bounds checking
**Who found it:** Rust tester
**What:** `flux-fracture` only does dependency graph fracture. No actual constraint checking. You need a separate library for that.
**Fix:** Either add checking to the crate or prominently link to the C header / Python lib for complete checking.

### 8. No `no_std` support in Rust
**Who found it:** Rust tester
**What:** Embedded CAN bus projects need `no_std`. Current crate uses `Vec`, `String`.
**Fix:** Add `no_std` feature flag with core-only types.

### 9. Fracture `dims` parameter unexplained
**Who found it:** JS tester
**What:** The dimension mapping is unclear. When/why do you set dims?
**Fix:** Add a practical example showing why dims matter.

### 10. ShadowgapResult.summary() doesn't exist
**Who found it:** Python tester
**What:** README implies a summary method that doesn't exist.
**Fix:** Add the method or fix the README.

## Nice-to-Have

- Add `exports` map to JS package.json
- Add `engines` field to JS package.json
- JS only has 6 presets (Python has 10)
- C header's "3 lines" claim is slightly misleading (per-value, not per-array)
- Python needs `requirements.txt` for non-pip users

## What Worked Well

1. **Install experience** — consistently rated 8-9/10 across all languages
2. **Zero dependencies** — JS tester loved it, Rust tester loved it
3. **TypeScript types** — rated 9/10
4. **Old language repos** — newcomer found COBOL/RPG/MUMPS "genuinely educational"
5. **Test suites** — all passed, all fast, all discoverable
6. **Honest negative results** — FP16 row in benchmarks builds credibility
7. **Sediment layers** — all testers understood and valued this feature

## Priority Order for Fixes

1. Add `check_vector()` to Python + JS APIs
2. Publish to npm + PyPI
3. Audit all links in docs/getting-started
4. Explain Eisenstein in main README or link to concepts
5. Add practical translations for thermodynamic concepts
6. Prominently state 8-constraint limit
7. Add `no_std` support to Rust crate
8. Fix ShadowgapResult.summary()
