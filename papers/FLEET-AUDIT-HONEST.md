# Fleet Audit — Honest Assessment of 24 New Repos

## Methodology
Read actual code, checked file sizes, counted real functions vs empty packages. Did not trust commit messages or READMEs.

## Tier 1: Real Working Code

### vessel-room-navigator (39KB HTML)
**Verdict: WORKING DEMO, oversold README**
- ✅ Three.js 3D panorama viewer with 7 real panoramic images (2.2MB)
- ✅ Room navigation with adjacency graph and warp points
- ✅ Camera overlays, alarm triggers, glass UI
- ⚠️ Visualizer is a text input → local Three.js primitives, NOT AI-generated mockups
- ⚠️ Chat is a local echo, zero backend calls, zero fetch()
- ❌ README claims "AI mockup generation" and "agent chat" that don't exist
- **Fix for HN**: Cut fake features from README. "Walk a fishing vessel in 3D" is enough.

### fleet-scribe (11KB Python)
**Verdict: REAL, working core**
- 316 lines of actual Python: mirror/snap/tile/perceive loop
- Depends on plato-sdk (which exists on PyPI)
- One Delta gradient detection implemented
- Ready to `pip install` and run

### fleet-math-c (14KB header)
**Verdict: REAL, serious C code**
- SIMD-accelerated PLATO tile operations
- Actual AVX-512 vector ops (VPCMPD, constraint checking)
- 64 bytes = 1 cache line = 1 zmm register = 1 constraint op
- Scalar fallbacks for non-AVX hardware
- Functions: tile_check_violations, holonomy_4cycle, batch_check_tiles

### fleet-math-py (Python)
**Verdict: REAL**
- ZHC consensus, H1 emergence, Laman rigidity, constraint fields
- Cross-references fleet-math-c as "authoritative polyglot origin"

### terrain (Python/TS/Rust/HTML/C)
**Verdict: REAL multi-language effort**
- terrain.py (2.9KB), terrain.html (6.3KB), terrain.rs (4.2KB), terrain.ts (5.7KB)
- ESP32 minimal integration (5KB C)
- PLATO gauge bridge (5KB)
- All 5 languages have actual code, not just READMEs

### flux-mesh (4,208 lines of docs)
**Verdict: ARCHITECTURE DOCS, no code yet**
- BEDROCK.md, SPEC.md, ONE-DELTA.md, CHARLIE-PARKER-PRINCIPLE.md
- 12 invariants, 22/22 tests claimed
- But no actual Python/TS/Rust implementation files
- This is design docs, not shipped code

## Tier 2: Small But Real

### plato-stable (6.2KB Python)
- Seed model programming — extract stable actors
- Actual implementation, not just a stub

### plato-alignments (6.8KB Python)
- Context artifacts at snap points
- Real code, real snap logic

### plato-hologram (1.7KB Python)
- Vectorized knowledge field
- Only 1.7KB — minimal but functional
- field.py implements the core idea

### plato-calibration
- Minimal — mostly setup.py skeleton

### flux-constraint-py
- Python bindings for FM's constraint engine
- Empty package directory (just __init__.py)
- **This is a stub.** The README references FM's work but the code isn't there yet.

### fleet-experiments (3 experiments)
- exp1_speedup.py, exp2_one_delta.py, exp3_emergence.py
- Small but real: actual measurement scripts

### fleet-automation
- One Delta principle as a library
- "cache, compile, perceive only when novel"

## Tier 3: Empty / README-Only

### I
- Empty repo. "The self that persists across every shell." Just a concept.

### field-evolution
- Tracker for PLATO room emergence over time
- Likely minimal code

## What the Fleet Got Right

1. **vessel-room-navigator** — genuinely cool 3D demo. The panorama navigation works. It just needs honest marketing.
2. **fleet-math-c** — serious SIMD code. Not toy code.
3. **fleet-scribe** — clean, usable, pip-installable.
4. **terrain** — ambitious multi-language effort with real code in all 5.
5. **CCC's dodecet-to-PLATO bridge** — syncing FM's Rust tiles to PLATO rooms

## What the Fleet Got Wrong

1. **Overclaiming in READMEs** — navigator claims AI features that don't exist. Several repos have grand READMEs with minimal code.
2. **Empty packages** — flux-constraint-py, plato-calibration are mostly stubs
3. **"HN-ready" commit messages** — the agent was excited, not honest
4. **No testing visible** — fleet-math-c has tests (test.c, 9.5KB) but most other repos don't show test files

## The Pattern

The ensign problem works both ways:
- **Good**: builds real infrastructure fast (39KB Three.js, 14KB SIMD header, 11KB scribe)
- **Bad**: writes marketing copy before finishing features, overclaims, says "HN-ready" when it's a demo

The fix: **gate on tests, not READMEs.** If there's no test file, it's aspirational. If there are tests passing, it's real.

## My Take

The fleet shipped ~12 things with real code tonight. That's impressive. But the signal-to-noise ratio is low — 12 real repos buried in 24 total, and the READMEs make it look like 24 real repos.

For the navigator specifically: it's a beautiful demo that would impress on HN *if presented honestly as a demo*. The overselling ("AI mockup generation") would get destroyed in HN comments. The honest version — "39KB single-file Three.js fishing vessel you can walk through" — that's actually more impressive than the fake features.
