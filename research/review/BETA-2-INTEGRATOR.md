# BETA-2: Spreader-Tool Integration Review

**Reviewed:** 2026-05-17  
**Repo:** https://github.com/SuperInstance/spreader-tool  
**Version:** 0.1.0  
**Tests:** 241 passing (1 warning — `TestResult` dataclass picked up by pytest collector)

---

## 1. Can you actually use this tool on a real project?

**Yes, with caveats.**

The core library works. Deadband detection, FCW lifecycle, seed state machines, content-addressed store — all solid, well-tested, zero external deps. You can pip install and go.

**But the README is aspirational in places.** The pattern library example in the README calls `lib.patterns` directly and iterates `.name`/`.success_rate` — the actual internal storage is string IDs (`_patterns`), and you need `find_for_context()` to get real objects. Minor API surface issue, but it'll confuse anyone following the README.

The `pyproject.toml` has a wrong build backend (`setuptools.backends._legacy:_Backend` instead of `setuptools.build_meta`). Had to patch it to install. That's a real friction point for anyone trying to use this.

**Verdict:** Usable today for deadband detection + seed lifecycle. The self-optimizer and pattern library are interesting but feel like prototypes bolted onto a solid core.

---

## 2. Does self-optimization produce actionable insights?

**Partially.**

The `SelfOptimizer` does three real things:
1. **Collects KPIs** from the repo — test pass rate, test timing, module coverage gaps, function complexity
2. **Detects deadband** — correctly flagged `inference_mae` (coverage gap at 16.7%) as breached
3. **Generates improvement report** — found 15 concrete optimization opportunities (missing test file for `development_patterns.py`, 12 functions over 50 lines, one import duplication)

The improvement report is genuinely useful. It's basically a static analysis pass that identifies:
- **Coverage gaps** — modules without test files
- **Complexity hotspots** — functions exceeding line thresholds
- **Duplication** — repeated imports across modules

The development cycle (`run_development_cycle`) works but is circular — it detects the same deadband each cycle and doesn't actually change anything. It's a simulation loop, not a real optimizer. The "locked seed" it produces is just a checkpoint of the current state, not an improvement.

**Verdict:** The *analysis* is actionable (I'd fix those 12 long functions and add the missing test file). The *cycle* is theater — it runs ticks but doesn't improve anything.

---

## 3. Is the pattern library useful or just a catalog?

**It's a curated catalog, but a genuinely useful one.**

7 patterns loaded:
- `frozen_dataclass_with_transition` — state machine pattern
- `hysteresis_guard` — threshold with duration gates
- `content_addressed_dedup` — hash-based dedup
- `in_memory_store_adapter` — duck-typed testing adapter
- `kpi_space_distance` — Euclidean distance in KPI space
- `episode_boundary_tracking` — transition detection
- `cleanup_bug_pattern` — specific ordering bug (don't delete state before duration check)

The `cleanup_bug_pattern` is genuinely interesting — it's a real bug pattern extracted from actual development, with wrong-vs-right code. That's the kind of thing that saves hours.

The `find_for_context()` search works — "bug fix" correctly returns the cleanup pattern. But it's keyword matching on `applies_when` and `tags`, not semantic search.

**What's missing:** No mechanism to add patterns from your own project. No learning from successes/failures (the `use_count` and `success_rate` fields exist but aren't wired to anything). No persistence — patterns are loaded fresh each time.

**Verdict:** Good catalog of PLATO-specific patterns. Not yet a living system that learns from your project. Use it as a reference, not a tool.

---

## 4. What would you need to adopt this?

1. **Fix the build backend** — `setuptools.build_meta`, not `setuptools.backends._legacy`. Without this, nobody can install it.

2. **Stabilize the public API** — `lib.patterns` vs `lib._patterns`, `r['deadband_state']` vs `r['tick_result']['deadband_state']`. The README examples should run as-is.

3. **Make the self-optimizer do something** — Right now `run_development_cycle` is a loop that ticks but doesn't change state. Either:
   - Wire it to actually fix the issues it finds (auto-split long functions, generate test stubs)
   - Or document it as a "monitoring loop" that just reports

4. **Pattern persistence** — Save/load patterns from disk. Let projects grow their own pattern libraries.

5. **Integration hooks** — How does this plug into a real agent room? The `SpreaderRoom` class exists but it's unclear how it connects to PLATO's actual room protocol.

6. **Remove `from __future__ import annotations` from 8 modules** — it flagged this as duplication but it's standard practice. The duplication detector needs a whitelist.

---

## 5. Score: 6/10

**What earns points:**
- Solid core (deadband, FCW, seeds, store) — well-designed, well-tested, zero deps
- 241 tests passing — serious test coverage
- The improvement report genuinely identifies real issues
- Clean state machine patterns with immutable dataclasses
- The cleanup_bug_pattern is a real extracted bug pattern

**What costs points:**
- Broken build backend (can't install without patching)
- README examples don't match actual API
- Self-optimizer is analysis theater — it reports but doesn't improve
- Pattern library is read-only, no persistence, no learning
- The "locked seed" from development cycles doesn't mean anything — it's just a snapshot

**Bottom line:** The deadband detection and seed lifecycle are production-ready. The self-optimizer and pattern library are interesting prototypes that need another iteration before they're genuinely useful. Worth integrating the core, worth watching the rest.
