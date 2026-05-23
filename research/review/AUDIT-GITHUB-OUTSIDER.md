# Outsider Audit — SuperInstance GitHub (Delta from May 7)

**Date:** 2026-05-17
**Auditor:** Forgemaster ⚒️ (subagent)
**Scope:** 22 repos inspected (15 originally assigned + 7 follow-ups for May 7 issues)
**Method:** Read-only web scrape. No local clones, no auth. Exactly what a stranger sees.
**Predecessors:** ORG-AUDIT-FULL.md (May 7), FLEET-AUDIT-SYNTHESIS.md (May 7), audit-level-suggestions.md (May 7), ONBOARDING-FLOW.md (May 17)

---

## Since Last Audit (May 7 → May 17)

### What Got Fixed ✅

| Issue (May 7) | Status | Evidence |
|---------------|--------|----------|
| **3 wrong READMEs** (fleet-health-monitor, quality-gate-stream, fleet-murmur all had JetsonClaw1 content) | **FIXED** | fleet-health-monitor now correctly describes health monitoring with beachcomb cycles and service tree. fleet-murmur now honestly says "CCC's agent workspace… Not a library. One agent's home directory." quality-gate-stream has correct title/description about quality scoring. |
| **No org-level profile README** | **FIXED** | `SuperInstance/.github` exists with `profile/README.md`. Fred Wahl shipyard narrative, fleet table (4 vessels), domain list (12+ domains), published crates. Code of conduct, contributing guide, security policy all present. |
| **constraint-theory-math: D-grade README** | **FIXED** | Now has structured proven/conjectured/debunked status table, ERRATA.md link, Coq proof references, honest labeling. Reads like a living research document, not raw notes. Upgraded from D → B+. |
| **constraint-inference: stub** (C grade, one-line README) | **FIXED** | Now has full architecture: override tracker, constraint inferrer, re-deliberation, PLATO bridge, simulation-first protocol (predict→apply→observe→confirm). ~4,000 words of documentation. Repo is now archived ("Superseded by forgemaster") which is honest. Upgraded C → B. |
| **intent-inference: stub** (C grade) | **FIXED** | Now has full architecture: 4 observers (navigation, murmur, PLATO, deliberation), productive lane model, fleet bridge, 1-minute poll cycle. Clear signal flow diagram. Upgraded C → B+. |
| **constraint-theory-ecosystem: language count contradiction** ("21 vs 42") | **PARTIALLY FIXED** | Title now says "47 implementations" consistently. The "21 vs 42" contradiction is gone. But "47" is a new claim that can't be verified from outside. See still-broken section. |

### What's Still Broken ❌

| Issue (May 7) | Status | Evidence |
|---------------|--------|----------|
| **fleet-spread: Test count inflated 3×** (claimed 147, actually ~46) | **NOT FIXED** | README still says "147 tests." This was flagged as a credibility killer on May 7. Ten days later, same inflated number. |
| **constraint-theory-ecosystem: inflated claims** | **NOT FIXED** (changed but not resolved) | Now claims "47 implementations, 62B checks/sec, 15 Coq theorems." The May 7 audit found ~35 directories (not 21 or 42), and only 1 .v file (not 15 or 38 theorems). The numbers changed but the inflation pattern didn't. |
| **quality-gate-stream: correct README but messy repo** | **PARTIAL** | Title is right now, but the file tree shows a massive monorepo with unrelated directories: activeledger-ai, art/purple-pincher, cocapn-profile, constraint-theory-core, fleet-archive, flux-compiler, etc. It's a workspace dump wearing a quality-gate nametag. |

### What's Brand New 🆕

These repos/packages either didn't exist or weren't in the May 7 audit:

| Repo/Package | Type | What It Is |
|-------------|------|-----------|
| **plato-model-ocean** | PyPI (NEW) | Cellular intelligence ecosystem. 4 evolutionary niches (sandbox→tide pool→school→whale), 300-cell population, ~100K params. Published and installable. |
| **plato-room-intelligence** | PyPI (NEW) | Multi-head neural model with weight provenance tracking. 5 task heads on shared backbone. Can trace any decision back to which room's data shaped it. |
| **plato-escalation-gate** | PyPI (NEW) | 737-parameter binary classifier (4KB). Decides when micro-models should escalate. WASM-ready. |
| **keel-ttl** + **superinstance-keel** | crates.io (NEW) | First-person self-termination: "Every entity carries its own death from its own frame." TTL types for tiles, tasks, agents, bearings, trust. CLI with 9 commands. |
| **spectral-conservation** | Expanded | Was mentioned in May 7 but now has full paper draft (5,130 words, NeurIPS/ICML 2026 submission). 20 cycles of adversarial falsification. Regime classification table. This is the publishable output. |
| **eisenstein ecosystem** | Expanded (9 repos) | Now has: eisenstein-c (microcontrollers, 1KB .text), eisenstein-wasm (browsers), eisenstein-bench, eisenstein-fuzz, eisenstein-do178c (formal verification), arm-neon-eisenstein-bench (4× parallel on ARM), hexgrid-gen (code gen), constraint-theory-core (production framework). This is now a proper ecosystem, not a single crate. |

---

## What an Outsider Sees Now (May 17)

### The Org Landing Page

The `.github` profile README is a **major upgrade** from May 7's "no profile at all." The Fred Wahl shipyard story is compelling — "Fred had 85 welders… welders got sharper when he was present" — and grounds the abstract fleet concept in physical reality. The fleet table lists 4 vessels with roles and hardware. 12+ domain links show breadth.

**But it's still insider-first.** A newcomer reads about keel-ttl, vessels, and domains before understanding what any of this *does*. The onboarding audit's recommendation for "3 paths" (math → ML → full ecosystem) and a 5-minute quickstart hasn't been implemented. There's no GETTING-STARTED.md, no pinned repos visible, no "try this first" callout.

### The PLATO ML Stack (New, Impressive)

The four new plato-* PyPI packages form a coherent ML pipeline that wasn't visible on May 7:

```
plato-types (foundation)
    ↓
plato-data (loading)
    ↓
plato-training (training + deploy)
    ↓
plato-escalation-gate (when to call for help)
plato-room-intelligence (multi-task with provenance)
plato-model-ocean (evolutionary optimization)
```

Each is independently installable, has clear usage examples, and honest performance tables (e.g., topic-classify at 29% on cpu-tiny — they show the bad numbers too). This is the most publication-ready part of the org.

### The Math Stack (Matured)

eisenstein has grown from a single crate into a 9-repo ecosystem spanning microcontrollers to formal verification. The constraint-theory-math repo now honestly labels proven/conjectured/debunked claims with status emojis. spectral-conservation has a paper draft with real falsification methodology.

### The Fleet Stack (Improved but Still Messy)

The 3 wrong READMEs are fixed. constraint-inference and intent-inference went from stubs to real architectures. But fleet-spread still overclaims tests. quality-gate-stream is a workspace dump. And the org profile, while much better, still doesn't guide newcomers.

---

## Updated Repo Grades (May 7 → May 17)

| Repo | May 7 | May 17 | Change Reason |
|------|-------|--------|---------------|
| eisenstein | A- | **A** | Ecosystem expansion to 9 repos, do178c path |
| constraint-theory-core | A | A | No change observed |
| constraint-theory-math | D | **B+** | Full rewrite with proven/conjectured/debunked |
| constraint-theory-ecosystem | B+ | B | Contradictions replaced but claims still inflated |
| flux-lucid | B- | **B** | Organized, still nautical-heavy |
| fleet-coordinate | A | A | No change observed |
| fleet-spread | A- | **B+** | 147 test claim still uncorrected |
| forgemaster | A | A | Solid, holodeck pattern works |
| spectral-conservation | — | **A-** | Paper draft, falsification methodology, honest |
| fleet-health-monitor | D | **B** | Correct README now |
| quality-gate-stream | D | **C+** | Correct title but repo is a dump |
| fleet-murmur | B- | **B** | Honest about what it is now |
| constraint-inference | C | **B** (archived) | Full content, honestly archived |
| intent-inference | C | **B+** | Full architecture, clear signal flow |
| plato-types | — | **A-** | Clean, minimal, correct |
| plato-data | — | **A-** | Clean data plumbing |
| plato-training | — | **A-** | 116 tests, honest bad numbers |
| tensor-spline | — | **A-** | 20× compression, clear when it fails |
| plato-model-ocean | — | **B+** | Novel but synthetic-only validation |
| plato-room-intelligence | — | **B+** | Provenance tracking is novel |
| plato-escalation-gate | — | **A-** | Tiny, focused, installable |
| dodecet-encoder | — | **B+** | Thorough, niche |
| penrose-memory | — | **B+** | Creative, dual Rust+Python |

---

## Cross-Cutting Assessment

### Improved Since May 7

1. **Honesty is up.** The proven/conjectured/debunked labeling in constraint-theory-math is exactly what the May 7 audit demanded. The ERRATA file exists. Two conjectures were honestly downgraded. constraint-inference was honestly archived rather than left as a zombie.

2. **PLATO ML stack is real.** Four new PyPI packages, independently installable, with honest performance tables. This is the most externally-credible part of the org now.

3. **Wrong READMEs fixed.** All three JetsonClaw1 content swaps corrected.

4. **Org profile exists.** Fred Wahl narrative, fleet table, domains, published crates. Way better than the blank page from May 7.

### Not Improved Since May 7

1. **fleet-spread test inflation.** Still says 147. Was flagged 10 days ago as a credibility killer. This is the single most actionable fix that hasn't been done.

2. **constraint-theory-ecosystem overclaims.** "47 implementations, 62B checks/sec, 15 theorems." The May 7 audit found these numbers inflated. They've been updated to new inflated numbers.

3. **Onboarding gap.** The onboarding audit (same day) identified clear fixes: 3 paths, GETTING-STARTED.md, pinned repos, repo descriptions. The org profile README exists but doesn't implement these recommendations.

4. **quality-gate-stream is a monorepo dump.** Fixed the title but not the content.

---

## Recommendations (Prioritized, Building on May 7)

### Critical (Do Today)

1. **Fix fleet-spread test count.** Run `cargo test`, count actual tests, update README. This has been open for 10 days. Every day it stays wrong erodes credibility.

2. **Audit constraint-theory-ecosystem numbers.** Count actual directories (not 47). Count actual .v files (probably not 15). Count actual check throughput on real hardware (probably not 62B/sec outside CUDA). Replace with honest numbers.

### High (Do This Week)

3. **Add 3-path quickstart to org profile.** The Fred Wahl story is great context but it shouldn't be the first thing a newcomer reads. Add a "Start Here" section with: math path (`cargo add eisenstein`), ML path (`pip install plato-escalation-gate`), ecosystem path (`git clone plato-training`).

4. **Pin repos on org page.** Pin: eisenstein, spectral-conservation, plato-training, constraint-theory-core. These are the four strongest external-facing repos.

### Medium (Do This Sprint)

5. **Add repo descriptions** to every repo that lacks one. GitHub description is the 1-liner under the repo name. Many repos still lack this.

6. **Clean up quality-gate-stream** or archive it. It's a workspace dump wearing a quality-gate nametag. Either extract the actual quality gate code into a focused repo, or label it honestly as a workspace.

---

## The Honest Outside View

10 days after the May 7 audit, **the fixes are real but selective.** The 3 wrong READMEs got fixed. The worst README (constraint-theory-math) got rewritten. Two stub repos got fleshed out. A brand new ML stack shipped with 4 packages. An org profile appeared.

But the credibility killers — inflated test counts and overclaimed benchmarks — persist. The May 7 audit said "Fix fleet-spread test count" as Priority 1, Item 1. It's still wrong. The constraint-theory-ecosystem numbers changed from "21/42 languages" to "47 implementations" but the inflation pattern is the same.

**The trajectory is positive.** More published packages, more honest labeling, more coherent architecture. But the gap between what's claimed and what's verified is still the org's biggest risk from an outsider perspective.

---

*Delta audit complete. Builds on ORG-AUDIT-FULL.md (May 7), FLEET-AUDIT-SYNTHESIS.md (May 7), audit-level-suggestions.md (May 7), and ONBOARDING-FLOW.md (May 17). All findings from public GitHub only.*
