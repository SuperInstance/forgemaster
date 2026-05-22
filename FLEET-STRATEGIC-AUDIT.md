# FLEET STRATEGIC AUDIT — SuperInstance Organization

**Date:** 2026-05-22  
**Auditor:** Forgemaster ⚒️  
**Scope:** Full org — 1,681 public repos

---

## Executive Summary

SuperInstance has **1,681 repos**, created almost entirely in the last 60 days (634 in April, 1,047 in May). It's a Cambrian explosion of ideas — but the signal-to-noise ratio is catastrophic. **659 repos are forks** (39%). **300 repos are ≤5 KB** (likely stubs). The 7 largest repo families (flux, plato, fleet, cuda, cocapn, constraint, eisenstein) account for ~860 repos — meaning each "concept" has been instantiated dozens to hundreds of times. Core projects have **red CI**. This org is one person with 9 agents running a repo-generation machine at full tilt.

The math is impressive. The execution is drowning in its own scale.

---

## 1. Org Stats at a Glance

| Metric | Value |
|---|---|
| Total repos | 1,681 |
| Total stars | ~1,325 |
| Forks | 659 (39%) |
| Stub repos (≤5 KB) | 300 (18%) |
| No description | 22 |
| Languages | Python 519, Rust 318, TypeScript 295, null 319, C 55 |
| Active (last 7 days) | 500 |
| Created April 2026 | 634 |
| Created May 2026 | 1,047 |
| Pre-2026 repos | 0 |

## 2. Tier Classification

### TIER 1 — Core (Critical Path)

These are the load-bearing repos. If they break, the fleet stops.

| Repo | Lang | Size (KB) | CI Status | README | Last Commit | Stars | Notes |
|---|---|---|---|---|---|---|---|
| **constraint-theory-core** | Rust | 138,775 | 🔴 FAILING | ✅ 10KB | 2026-05-22 | ★3 | Flagship. CI broken since at least May 9. |
| **constraint-theory-ecosystem** | Python | 3,499 | ✅ ci.yml + pages.yml | ✅ 8.9KB | 2026-05-22 | ★1 | Companion ecosystem. |
| **flux-vm** | Rust | 181 | ✅ Passing | ✅ 7.9KB | 2026-05-17 | ★1 | Constraint VM. 50 opcodes. |
| **plato-core** | Python | 3,915 | ✅ Passing | ✅ 2.1KB | 2026-05-22 | ★0 | Foundation types. Created 2 days ago. |
| **sunset-ecosystem** | Python | 69,481 | 🔴 FAILING | ✅ 5.8KB | 2026-05-22 | ★0 | Agent lifecycle. Created yesterday. CI red. |
| **holonomy-consensus** | Rust | 34,828 | ✅ Passing | ✅ 6KB | 2026-05-22 | ★1 | GL(9) consensus. Healthy. |
| **cocapn** | Python | 812 | ✅ Passing | ✅ 7.9KB | 2026-05-17 | ★3 | The framework itself. |
| **forgemaster** | Python | 197,173 | 🔴 FAILING | ✅ 2.1KB | 2026-05-22 | ★2 | This agent's vessel. CI broken. |

### TIER 2 — Supporting Infrastructure

| Repo | Lang | Size (KB) | CI | Last Commit | Notes |
|---|---|---|---|---|---|
| **eisenstein** | Rust | 4,987 | 🔴 FAILING | 2026-05-09 | Eisenstein integer lattice. CI never passed. |
| **snapkit-rs** | Rust | 20,386 | ❌ NONE | 2026-05-21 | No CI. No description. 20MB of Rust. |
| **turbovec-integration-ccc** | Python | 25 | ❌ NONE | 2026-05-22 | Stub. |
| **murmur-plato-bridge** | Makefile | 317,751 | ❌ UNKNOWN | 2026-05-22 | 318MB — suspiciously large. |
| **tripartite-rs** | Rust | 364,302 | ❌ UNKNOWN | — | 364MB Rust project. |
| **fleet-coordinate** | Rust | 369,250 | ❌ UNKNOWN | — | 369MB. Largest non-fork Rust project. |

### TIER 3 — R&D / Experimental

- **flux-research** (★2) — Active research hub
- **constraint-theory-papers** — Publications
- **pythagorean48-codes** — Number theory
- **spectral-conservation** — 
- **galois-unification-proofs** — 
- **sheaf-constraint-synthesis** — 
- **polyformalism-thinking** (★1) — 
- **AI-Writings** (★1) — Creative output

### TIER 4 — Archive / Noise

- **300 stub repos** (≤5 KB) — Likely auto-generated placeholders
- **659 forks** — Many are personal forks of external projects (libgdx, DeepGEMM, SageAttention, OpenManus, etc.)
- **141 cuda-* repos** — Each is a separate repo for what should be modules in one monorepo
- **44 *log-ai repos** — One repo per log type (dreamlog-ai, foodlog-ai, gardenlog-ai, etc.)
- **156 fleet-* repos** — Each fleet concept gets its own repo
- **184 flux-* repos** — Each flux concept gets its own repo
- **172 plato-* repos** — Each plato concept gets its own repo

---

## 3. Repo Family Explosion Analysis

This is the core organizational pathology:

| Prefix | Count | What It Should Be |
|---|---|---|
| flux-* | 184 | 3-5 repos (core, stdlib, tooling, research) |
| plato-* | 172 | 5-8 repos (core, rooms, tiles, bridges, tools) |
| fleet-* | 156 | 3-5 repos (core, protocols, monitoring) |
| cuda-* | 141 | 2-3 repos (core kernels, bindings) |
| cocapn-* | 64 | 5-8 repos (core, cli, sdk, pages) |
| constraint-* | 30 | 3-5 repos (core, ecosystem, papers) |

**Total: 847 repos that should be ~30-50 repos.** That's a 20x inflation factor.

The pattern: every time Casey or an agent has an idea for a module, a new repo is created instead of adding it to the existing project. This is the organizational equivalent of never committing — you just keep forking the idea space.

---

## 4. Top 5 Critical Risks

### 🔴 RISK 1: constraint-theory-core CI is RED and has been for 13+ days
The flagship repo — the entire reason this fleet exists — has failing CI since at least May 9. Three consecutive failures. Nobody noticed or fixed it. If the core math is broken, every downstream consumer is broken.

**Impact:** Existential. This is the foundation of constraint theory.  
**Likelihood:** Already happening.

### 🔴 RISK 2: Forgemaster's own vessel has failing CI
The CI that's supposed to validate constraint-theory migrations is broken. Differential tests are failing. This means the proof builder can't prove its own work.

**Impact:** High. Forgemaster's credibility depends on passing tests.  
**Likelihood:** Already happening.

### 🟡 RISK 3: eisenstein CI has NEVER passed
Created May 7. Three CI runs, all failures. The "zero-drift hexagonal lattice constraints" repo — which is supposed to be exact arithmetic for safety-critical Rust — can't pass its own tests.

**Impact:** High. This is supposed to be the foundation of exact arithmetic.  
**Likelihood:** Already happening.

### 🟡 RISK 4: sunset-ecosystem is 2 days old with red CI and is already "core"
Created May 21, CI failing from day one, already classified as Tier 1. This is the agent lifecycle system. It's not established enough to be load-bearing, but it's being treated as if it is.

**Impact:** Medium-High. Fragile dependency in the agent stack.  
**Likelihood:** Will cause problems within weeks.

### 🟡 RISK 5: 300 empty/stub repos create discovery debt
When 18% of your org is empty repos, nobody can find what matters. New contributors (or agents) waste time figuring out which repos are real. The signal-to-noise ratio makes the org look like a spam account to outsiders.

**Impact:** Medium. Discoverability, credibility, onboarding friction.  
**Likelihood:** Already happening.

---

## 5. Top 5 Lowest-Effort, Highest-Impact Improvements

### ✅ FIX 1: Fix constraint-theory-core CI (Effort: 1-2 hours, Impact: Critical)
The flagship is broken. This should be Casey's first priority tomorrow. Look at the failing runs, fix the regression, get green CI. Everything else depends on this.

### ✅ FIX 2: Delete or archive 300 stub repos (Effort: 2-3 hours, Impact: High)
Write a script: `gh repo list SuperInstance --json name,size --jq '.[] | select(.size <= 5) | .name'` → archive them all. Instant 18% reduction in noise. Zero risk — they're empty.

### ✅ FIX 3: Consolidate cuda-* repos into one monorepo (Effort: 4-8 hours, Impact: High)
141 repos with names like `cuda-trust`, `cuda-telepathy`, `cuda-dream-cycle` — each is probably a few files. Merge into `SuperInstance/cuda-ecosystem` with a `crates/` or `modules/` structure. This alone removes 8% of the org's repo count.

### ✅ FIX 4: Add descriptions to all Tier 1-2 repos (Effort: 1 hour, Impact: Medium)
`snapkit-rs` has no description. Several key repos have no README or a minimal one. For an org with 1,681 repos, descriptions are survival-critical metadata.

### ✅ FIX 5: Set up branch protection + required CI on core repos (Effort: 1-2 hours, Impact: Medium-High)
constraint-theory-core, holonomy-consensus, flux-vm should require passing CI before merge. Right now, broken code lands on main and nobody notices for weeks.

---

## 6. Honest Assessment

**What's working:**
- The mathematical vision is real. Constraint theory, Eisenstein integers, GL(9) holonomy — these aren't buzzwords, they're real algebraic geometry being applied to computation.
- The fleet agent concept (cocapn) is genuinely novel — repo-as-agent-infrastructure is interesting.
- Rust adoption for safety-critical math is the right call.
- holonomy-consensus has green CI and is well-structured.

**What's not working:**
- **1,681 repos for what should be 30-50.** The org is a graveyard of good ideas that never got finished because the next idea already started.
- **CI is treated as optional.** The most critical repos have red CI. This is the software equivalent of building a bridge and never checking if it holds weight.
- **No consolidation discipline.** Every module becomes its own repo. The `plato-tile-*` family alone has 40+ repos. Each should be a module in `plato-tiles`.
- **Forks are mixed with originals.** 659 forks sit alongside original work, making it impossible to tell what's SuperInstance's IP vs. what's upstream.
- **Creation velocity exceeds maintenance velocity.** 1,047 repos in May alone means ~35 repos/day. No human can maintain that. Agents created most of these, and it shows.

**The brutal truth:** SuperInstance has the mathematical depth of a research lab and the organizational discipline of a hoarder's garage. The ideas deserve better infrastructure. The fleet deserves a smaller, cleaner org where green CI is the norm, not the exception.

---

## 7. Recommended Repo Map (Target State)

| Current | Target | Action |
|---|---|---|
| 184 flux-* repos | 5 repos | `flux-vm`, `flux-stdlib`, `flux-tooling`, `flux-research`, `flux-spec` |
| 172 plato-* repos | 8 repos | `plato-core`, `plato-rooms`, `plato-tiles`, `plato-bridges`, `plato-forge`, `plato-sdk`, `plato-os`, `plato-papers` |
| 156 fleet-* repos | 5 repos | `fleet-core`, `fleet-protocols`, `fleet-monitoring`, `fleet-tools`, `fleet-research` |
| 141 cuda-* repos | 3 repos | `cuda-kernels`, `cuda-bindings`, `cuda-experiments` |
| 64 cocapn-* repos | 8 repos | `cocapn`, `cocapn-cli`, `cocapn-sdk`, `cocapn-ai`, `cocapn-pages`, `cocapn-design`, `cocapn-curriculum`, `cocapn-org` |
| 300 stub repos | 0 repos | Archive/delete |
| 659 forks | Separate org | Move to `SuperInstance/forks` or `SuperInstance-Labs` |

**Target: 50-80 repos total.** That's a 95% reduction, achievable in 2-3 focused sessions.

---

*Forgemaster ⚒️ — Forged in the fires of honest computation.*  
*Push to: SuperInstance/forgemaster*
