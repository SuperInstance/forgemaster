# FLEET STRATEGIC AUDIT ⚒️

**SuperInstance Organization — GitHub Strategic Review**
**Date:** 2026-05-22
**Auditor:** Forgemaster
**Scope:** 1,681 repositories across users/SuperInstance
**Methodology:** `gh api` survey, tiered classification, CI/test/README inspection, contributor analysis

---

## EXECUTIVE SUMMARY

SuperInstance is not an organization. It is a **personal workspace that accidentally scaled to 1,681 repositories.** The architectural vision described in SYNERGY.md is genuinely elegant — geometric constraint satisfaction as a unifying theory, Eisenstein lattices, Laman rigidity, holonomy consensus. But the **execution is catastrophic.** The codebase is a graveyard of abandoned experiments, forked dependencies, and micro-repos with zero tests, zero documentation, and exactly one contributor.

**The brutal truth:** If the sole maintainer gets hit by a bus, SuperInstance ceases to exist. Not metaphorically. Literally.

---

## THE NUMBERS

| Metric | Count | Verdict |
|--------|-------|---------|
| **Total Repos** | 1,681 | Absurd. No org needs this many. |
| **Forks** | 659 (39.2%) | Nearly 2 in 5 repos are not original work. |
| **Archived** | 133 | Acceptable, but core repos are among them. |
| **Empty / Near-Empty (size < 5)** | 165 | 10% of the org is placeholder repos. |
| **Zero Stars** | 293 | 17% completely invisible to the world. |
| **Not Pushed in 30+ Days** | 860 | **51% are already stale.** |
| **Total Open Issues** | 5,372 | But 5,296 (98.6%) live in just 2 repos. |
| **Repos with >10 Open Issues** | 2 | `babel-vessel` (2,647), `claude-code-vessel` (2,649) |
| **Max Stars on Any Repo** | 3 | For 1,681 repos. Three. Stars. Total. |
| **Repos Pushed in Last 7 Days** | ~50 | Tiny active surface area. |

**Translation:** This is not a shipping organization. This is an **ideas warehouse** where most inventory has collected dust.

---

## TIER BREAKDOWN

### TIER 1 — CORE (196 repos)
**Pattern:** `constraint-theory-*`, `flux-vm*`, `plato-*`, `sunset-*`, `fleet-agent`, `holonomy-consensus`

**Findings:**
- **`fleet-agent` DOES NOT EXIST.** Only `fleet-agent-early-version` (115 KB, 1 star, 0 tests, README 684 bytes). The repo specified in the tier definition is missing. This is a naming/ownership failure at the architectural level.
- **`plato-*` is an explosion: 173 repos.** The "knowledge fabric" is fragmented into 173 micro-repos, many < 50 KB, many with 0-2 stars, many with no README, most with no tests. PLATO is not a fabric. It is confetti.
- **`constraint-theory-mlir` and `constraint-theory-mojo` are ARCHIVED.** Core compiler infrastructure has been abandoned.
- **`flux-vm` and `flux-vm-v3` are ARCHIVED.** The execution layer has two archived variants and one active fork (`flux-vm-ts`, 32 KB). This is not versioning. This is abandonment.
- **`sunset-ecosystem` is the sole sunset repo** (60 KB, 0 stars, 3 issues, 19 test files, 404 total files). It has tests but zero community engagement.

**Tier 1 Health Score: D+**
The math is beautiful. The repos are a disaster.

---

### TIER 2 — SUPPORTING (16 repos)
**Pattern:** `turbovec*`, `eisenstein*`, `deadband*`, `tensor-spline`, `snapkit*`

**Findings:**
- **`eisenstein` (the main Rust impl) is ARCHIVED.** The geometric backbone lives in an archived repo.
- **`eisenstein-embed` is ARCHIVED.** Another lattice implementation, dead.
- **`tensor-spline` is ARCHIVED.** The interpolation layer is frozen.
- **`deadband-rs` has NO CI/CD, NO README, NO LICENSE.** 21 KB of Rust/Shel code, 33 files, 0 workflows, 0 test files. The "fast Rust deadband" has no verification infrastructure.
- **`snapkit-rs` has NO CI/CD, NO LICENSE.** 20 KB, 8 files, 1 test file. A supporting library with no safety net.
- **`turbovec` is a FORK.** It has 2 workflows and 18 test files, but it is not original SuperInstance work.

**Tier 2 Health Score: F**
Supporting infrastructure is either archived, forked, or untested.

---

### TIER 3 — R&D (~20 repos)
**Pattern:** `gpu-experiments`, `proofs`, `papers`, `research`, `experiments`

**Findings:**
- **`SuperInstance-papers` is ARCHIVED** (35 KB).
- **`flux-papers` is ARCHIVED** (156 KB).
- **`flux-research` is ARCHIVED** (9.5 KB).
- **`galois-unification-proofs` is ARCHIVED** (13 KB).
- Most R&D repos are tiny (< 100 KB) and inactive. They do not represent a research pipeline. They represent **digital notebook fragments.**

**Tier 3 Health Score: D**
Research exists but is scattered, archived, and disconnected from core development.

---

### TIER 4 — ARCHIVE ( Estimated 400+ repos )
**Criteria:** Empty, abandoned, superseded, forked, archived, or stale > 90 days.

**Findings:**
- **165 repos are empty/near-empty.** These should be deleted, not archived.
- **860 repos (51%) have not been pushed in 30+ days.** In a fast-moving field, this is abandonment.
- **659 forks** should be evaluated. Most are likely dependency forks with no SuperInstance-specific changes. They bloat the org and confuse navigation.
- **`murmur-plato-bridge` is ARCHIVED** and 317 KB — a massive archived bridge to nowhere.
- **`openarm` is ARCHIVED** (129 KB).

**Tier 4 is not a tier. It is the majority of the organization.**

---

## TIER 1 DEEP DIVE

| Repo | Size | Stars | Last Push | CI/CD | Tests | README | Lang | Contrib | Verdict |
|------|------|-------|-----------|-------|-------|--------|------|---------|---------|
| `constraint-theory-core` | 138 KB | 3 | 2026-05-22 | 1 workflow | 2 files | 10 KB | Python | 1 | **Best in class.** Still only 2 test files for 138 KB. |
| `holonomy-consensus` | 34 KB | 1 | 2026-05-21 | 1 workflow | 2 files | 5.9 KB | Rust | 0 | **No contributors visible.** 24 commits recently, but API shows 0 contributors. Ghost commits. |
| `sunset-ecosystem` | 60 KB | 0 | 2026-05-22 | 1 workflow | 19 files | 5.7 KB | CUDA | 1 | Most tested core repo. Zero stars. Zero community. |
| `plato-training` | 212 KB | 0 | 2026-05-21 | 1 workflow | 34 files | 7.5 KB | C | 1 | Largest core repo. 34 tests is good. 0 stars. |
| `plato-client-js` | 41 KB | 0 | 2026-05-08 | 1 workflow | 0 files | 4.6 KB | TypeScript | 0 | **No tests.** Client library with no test coverage. |
| `plato-core` | 3.9 KB | 0 | 2026-05-21 | **NONE** | 3 files | 2.1 KB | Python | 0 | The "core" has no CI. 337 files but only 3.9 KB? Suspicious. |
| `constraint-theory-py` | 112 B | 0 | 2026-05-22 | 1 workflow | 2 files | 3.1 KB | Python | 0 | 112 bytes. This is not a repo. It is a README with an import statement. |
| `plato-room-phi` | 45 KB | 1 | 2026-05-18 | 1 workflow | 1 file | 2.8 KB | Python | 0 | 1 test file. 45 KB, 11 files total. Heavy on assets? |
| `plato-room-nav` | 30 KB | 2 | 2026-05-08 | 1 workflow | 0 files | **84 B** | DTrace | 0 | README is 84 bytes. Eighty-four bytes. That is not documentation. That is a filename. |
| `plato-inference-runtime` | 29 KB | 2 | 2026-05-08 | 1 workflow | 0 files | **117 B** | DTrace | 0 | No tests. README is a sentence fragment. |
| `plato-dcs` | 17 KB | 2 | 2026-05-08 | 1 workflow | 0 files | 1.2 KB | Makefile | 0 | No tests. Makefile-primary language suggests build-only. |
| `plato-i2i-dcs` | 9.5 KB | 2 | 2026-05-08 | 1 workflow | 0 files | **0 B** | Makefile | 0 | **No README.** No tests. |
| `plato-ghostable` | 9 KB | 2 | 2026-05-08 | 1 workflow | 0 files | **99 B** | Makefile | 0 | README is 99 bytes. No tests. |
| `deadband-rs` | 21 KB | 0 | 2026-05-22 | **NONE** | 0 files | **0 B** | Shell | 0 | No CI. No README. No tests. No license. |
| `snapkit-rs` | 20 KB | 0 | 2026-05-22 | **NONE** | 1 file | 2.5 KB | ??? | 0 | No CI. No license. 1 test file. |

### Deep Dive Summary

- **CI/CD Coverage in Tier 1:** ~60% have at least 1 workflow. **40% have nothing.** Core infrastructure like `deadband-rs`, `snapkit-rs`, and `plato-core` have zero automated verification.
- **Test Coverage:** Abysmal. Repos with 0 test files: `plato-client-js`, `plato-room-nav`, `plato-inference-runtime`, `plato-dcs`, `plato-i2i-dcs`, `plato-ghostable`, `deadband-rs`. These are supposed to be production components.
- **README Quality:** Catastrophic. Multiple repos have READMEs under 200 bytes. `plato-room-nav` has 84 bytes. `plato-i2i-dcs` has none. If you cannot explain what a repo does in a paragraph, you do not know what it does.
- **Bus Factor:** **1.** Every significant repo has exactly 1 contributor. `holonomy-consensus` shows 0 contributors despite 24 recent commits — likely the same person using different git configs or force-pushing.

---

## THE 5 BIGGEST RISKS

### RISK 1: THE SINGLE POINT OF FAILURE (CRITICAL)
**Every repo has 1 contributor. Most have 0.**

There is no team. There is a single human maintaining 1,681 repositories. `forgemaster` (the meta-repo) has 100 commits in 30 days — all from one person. If that person stops, SuperInstance stops. Not gradually. Immediately.

**Mitigation:** Hire. Partner. Open contributions. The current model is unsustainable at any scale beyond "weekend project."

---

### RISK 2: ISSUE BANKRUPTCY (CRITICAL)
**`babel-vessel` (2,647 open issues) and `claude-code-vessel` (2,649 open issues)** collectively hold 98.6% of all open issues in the org.

These are not "issues." They are **unprocessed noise.** No human can triage 5,296 issues. They likely represent auto-generated logs, bot spam, or unfiltered bug reports from a wrapper around Claude Code. Whatever the source, they render GitHub Issues useless as a project management tool.

**Mitigation:** Close all issues older than 30 days with a bot message. Institute issue templates. Or disable Issues on these repos entirely.

---

### RISK 3: THE ARCHIVED CORE (HIGH)
**`eisenstein`, `eisenstein-embed`, `tensor-spline`, `flux-vm`, `flux-vm-v3`, `constraint-theory-mlir`, `constraint-theory-mojo`** are all archived.

These are not peripheral utilities. They are the **geometric backbone, execution layer, and compiler infrastructure** of the entire architecture described in SYNERGY.md. The theory says "Eisenstein lattice is the universal quantizer." The practice says "the universal quantizer is archived."

You cannot build a unified architecture on abandoned foundations.

**Mitigation:** Unarchive and update, or explicitly replace with successor repos. If `flux-vm-v3` is superseded by something else, document that. Right now it looks like neglect.

---

### RISK 4: PLATO FRAGMENTATION (HIGH)
**173 `plato-*` repos.**

PLATO is described as "the knowledge fabric" present in 60+ repos. The reality is 173 micro-repos, most < 50 KB, many with no README, no tests, and no CI. This is not a fabric. This is **shards of a broken mirror.**

The SYNERGY.md recommendation to create `plato-consensus` as a unified layer is correct because the current state is unmanageable. Finding which `plato-tile-*` repo handles which function requires archaeological skills.

**Mitigation:** Merge. The 40 `plato-tile-*` repos should be one `plato-tiles` monorepo. The 20 `plato-room-*` repos should be one `plato-rooms` service. Consolidate or perish.

---

### RISK 5: ZERO-TEST PRODUCTION COMPONENTS (HIGH)
**`deadband-rs` (0 tests), `plato-client-js` (0 tests), `plato-inference-runtime` (0 tests), `plato-dcs` (0 tests), `plato-room-nav` (0 tests), `snapkit-rs` (1 test).**

These are supposed to be production-grade components. The deadband funnel is "the temporal control surface." The client is how users interact. The inference runtime is where ML executes. And none of them have automated tests.

This means every commit is a potential production incident. The "38ms consensus latency" claim in SYNERGY.md is meaningless if there are no tests to verify it under load, under failure, or under Byzantine conditions.

**Mitigation:** Testing is not optional for infrastructure. Institute a "no merge without tests" policy. Start with the 6 repos listed above.

---

## 5 LOWEST-EFFORT, HIGHEST-IMPACT IMPROVEMENTS

### QUICK WIN 1: DELETE THE EMPTY REPOS (Effort: 1 hour. Impact: Massive clarity.)
**165 repos have size < 5.** They are placeholders, failed experiments, or accidental creations. Delete them. They pollute search, confuse navigation, and make the org look like a dumping ground.

**Action:** `gh repo delete` on all repos with size < 5 and no commits in 90 days.

---

### QUICK WIN 2: CLOSE THE ISSUE BANKRUPTCY (Effort: 2 hours. Impact: Restored project management.)
**5,296 open issues in 2 repos.** Close them all with a bot comment: "Bulk-closing stale issues. Please re-open with a reproduction if still relevant."

Then add issue templates to `babel-vessel` and `claude-code-vessel` so new issues are structured and actionable.

**Action:** `gh issue close --comment "..."` with a script. Add `.github/ISSUE_TEMPLATE/` to both repos.

---

### QUICK WIN 3: ADD READMEs TO THE NAKED REPOS (Effort: 1 day. Impact: Onboarding velocity.)
**At least 10 Tier 1 repos have READMEs under 500 bytes or none at all.** `plato-room-nav` (84 B), `plato-i2i-dcs` (0 B), `plato-ghostable` (99 B), `plato-inference-runtime` (117 B), `deadband-rs` (0 B).

A README should answer: What is this? Why does it exist? How do I use it? How do I test it?

**Action:** Write 10 READMEs. Use a template. 30 minutes per repo.

---

### QUICK WIN 4: ADD CI TO THE BARE METAL (Effort: 1 day. Impact: Prevent silent breakage.)
**`deadband-rs`, `snapkit-rs`, and `plato-core` have no CI/CD.** These are core infrastructure repos. A single `cargo test` or `pytest` workflow would catch breakage before it propagates.

**Action:** Add `.github/workflows/ci.yml` to these 3 repos. Use the simplest possible template (checkout, setup language, run tests).

---

### QUICK WIN 5: CONSOLIDATE THE `plato-tile-*` MICRO-REPOS (Effort: 2 days. Impact: Architectural coherence.)
**There are ~40 `plato-tile-*` repos**, most < 20 KB, many with identical structure. Merge them into a single `plato-tiles` monorepo with a directory per concern (`api/`, `batch/`, `cache/`, `cascade/`, etc.).

This does not require code changes — just `git subtree` merges and updated import paths. The payoff is massive: one CI pipeline, one README, one issue tracker, one release cycle.

**Action:** Create `plato-tiles`. Migrate the 10 most active `plato-tile-*` repos first. Archive the originals with forwarding links.

---

## ADDITIONAL FINDINGS

### Fork Contamination
659 repos (39%) are forks. Many have no SuperInstance-specific changes. They serve no purpose other than inflating the repo count. **Recommendation:** Audit forks. Delete those with zero commits ahead of upstream. Keep only those with meaningful divergence.

### License Inconsistency
Multiple core repos have no license (`deadband-rs`, `sunset-ecosystem`, `snapkit-rs`, `holonomy-consensus`). This is a legal liability. If the goal is open-source adoption, every repo needs an explicit SPDX license.

### Language Chaos
Repos claim primary languages that make no sense: `plato-room-nav` is "DTrace" (it is not). `plato-dcs` is "Makefile." `deadband-rs` is "Shell." GitHub language detection is failing because these repos have so little actual code that build files and shell scripts dominate the byte count.

### The `fleet-agent` Absence
The tier definition names `fleet-agent` as a core repo. It does not exist. The closest match is `fleet-agent-early-version`, which has 0 tests, a 684-byte README, and has not evolved beyond "early version." The fleet coordination layer — a critical piece of the architecture — is either vaporware or so poorly named that even an API audit cannot find it.

---

## STRATEGIC RECOMMENDATIONS

### Immediate (This Week)
1. Delete 165 empty repos.
2. Close 5,296 stale issues in `babel-vessel` and `claude-code-vessel`.
3. Add CI to `deadband-rs`, `snapkit-rs`, `plato-core`.
4. Write READMEs for the 10 naked Tier 1 repos.
5. Unarchive or formally deprecate `eisenstein`, `flux-vm`, `tensor-spline`.

### Short-Term (This Month)
1. Merge `plato-tile-*` into `plato-tiles`.
2. Merge `plato-room-*` into `plato-rooms`.
3. Add licenses to all unlicensed core repos.
4. Institute "no merge without tests" for Tier 1.
5. Create a real `fleet-agent` repo or rename `fleet-agent-early-version` and commit to it.

### Long-Term (This Quarter)
1. **Reduce repo count from 1,681 to < 200.** Aggressive consolidation. Forks deleted. Micro-repos merged. Experiments archived or deleted.
2. **Build a team.** 1 contributor across 1,681 repos is not a strategy. It is a countdown timer.
3. **Ship one integrated product.** The SYNERGY.md architecture is beautiful on paper. Pick one vertical (e.g., `constraint-theory-core` + `holonomy-consensus` + `fleet-agent`) and make it run end-to-end with tests, docs, and a demo. Everything else is distraction until that works.

---

## FINAL VERDICT

**SuperInstance is a cathedral blueprint drawn on 1,681 napkins.**

The math is sound. The vision is coherent. The architecture, on paper, is revolutionary. But the implementation is a **distributed fragility matrix**: one maintainer, thousands of abandoned repos, core components archived, tests missing, documentation nonexistent, and an issue tracker that is a digital landfill.

**The organization does not have a scaling problem. It has a focus problem.** 1,681 repos is not power. It is paralysis. The path forward is not more repos. It is fewer repos, more tests, more contributors, and one working demo that proves the theory.

**Stop building costumes. Ship the idea.**

---

*Audit compiled from live GitHub API data.*
* gh api `users/SuperInstance/repos?sort=pushed&per_page=100` (1,681 repos surveyed)
* gh api `repos/SuperInstance/{repo}` (deep inspection on 30+ key repos)
* gh api `repos/SuperInstance/{repo}/contents/.github/workflows` (CI audit)
* gh api `repos/SuperInstance/{repo}/git/trees/HEAD?recursive=1` (file/test counts)
* gh api `repos/SuperInstance/{repo}/contributors` (bus factor analysis)

*Forgemaster ⚒️ — 2026-05-22*
