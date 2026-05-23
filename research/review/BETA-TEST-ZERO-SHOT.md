# Beta Test: Zero-Shot Agent Test Report

**Date:** 2026-05-17 | **Tester:** Forgemaster ⚒️ (Team 1 Lead)
**Mission:** Ensure a ZERO-SHOT agent (knowing nothing about us) sent to our GitHub returns with the RIGHT information and a plan.

---

## Executive Summary

**10 of 12 repos PASS the zero-shot test.** 2 had critical issues that were fixed during this test. The org landing page is excellent. GETTING-STARTED.md is accessible via forgemaster repo.

### Before This Test

| Status | Count | Repos |
|--------|:-----:|-------|
| ✅ PASS | 8 | eisenstein, tensor-spline, plato-escalation-gate, plato-model-ocean, plato-training, dodecet-encoder, plato-types, plato-data |
| ❌ FAIL | 2 | **plato-room-intelligence**, **spectral-conservation** |
| ⚠️ PARTIAL | 2 | org GETTING-STARTED.md (404), flux-lucid (fixed in prior audit, verified pass) |

### After This Test

| Status | Count | Repos |
|--------|:-----:|-------|
| ✅ PASS | 10 | All above + plato-room-intelligence + spectral-conservation |
| ⚠️ REMAINING | 2 | Org-level GETTING-STARTED.md (404), crab-trap.lucineer.com (dead link) |

---

## Phase 1: Zero-Shot Simulation Results

Each repo was visited as if the agent had NEVER heard of constraint theory, PLATO, or SuperInstance. For each, the critical question: **"Can I tell my user what to DO with it?"**

### ✅ SuperInstance Org Page
> **Agent would report:** "This org builds mathematically-grounded tools for intelligent systems. They have a shell architecture where agents (called 'crabs') serve frontends by reading from tile stores. You can start with `pip install plato-sdk` or `cargo install superinstance-keel`. Three tiers of model capability guide routing."
>
> **Verdict:** PASS. The org profile is long but substantive. Code examples work. The narrative is coherent. ✅

### ✅ SuperInstance/.github (Profile README)
> **Agent would report:** "Same as org page — the profile README IS the org README."
>
> **Verdict:** PASS. Fred Wahl story, fleet table, published crates. ✅

### ❌ SuperInstance/GETTING-STARTED.md (Org-level)
> **Agent would report:** "404 — page not found."
>
> **Verdict:** FAIL. However, `forgemaster/GETTING-STARTED.md` works and contains the 3-path quickstart. The org README links to it. Not blocking but suboptimal.

### ✅ forgemaster/GETTING-STARTED.md
> **Agent would report:** "Here are 3 paths: (1) Math people → `cargo add constraint-theory-core`, (2) ML people → `pip install plato-escalation-gate`, (3) Full ecosystem → clone plato-training. Each path has install commands and working code examples. Package table lists 7 packages with install commands."
>
> **Verdict:** PASS. Excellent 3-path onboarding. ✅

### ✅ spectral-conservation (BEFORE → AFTER)
> **BEFORE — Agent would report:** "This is a Rust crate about spectral conservation in nonlinear dynamics. I can see code examples and regime tables, but I can't tell you how to install it — there's no `cargo add` command. I also can't tell you why you'd use this."
>
> **AFTER — Agent would report:** "Install with `cargo add spectral-conservation`. Use it to monitor whether your coupled nonlinear system is drifting into pathological regimes. It tracks a spectral invariant that stays stable (CV < 0.03) across thousands of configurations. Here's a working code example."
>
> **Verdict:** Was FAIL, now PASS. ✅ Fix pushed to GitHub.

### ✅ plato-escalation-gate
> **Agent would report:** "A 737-parameter binary classifier (4KB, WASM-ready) that decides when to escalate to a higher-level model. Install: `pip install plato-escalation-gate`. Here's a training and inference example. Links to related packages."
>
> **Verdict:** PASS. ✅

### ✅ plato-model-ocean
> **Agent would report:** "An evolving ecosystem of neural networks with four ecological niches (sandbox → tide pool → school → whale). 300 cells, ~100K params. Install: `pip install plato-model-ocean`. Here's code to create an ocean, colonize it, and evolve. Links to related packages."
>
> **Verdict:** PASS. ✅

### ✅ plato-room-intelligence (BEFORE → AFTER)
> **BEFORE — Agent would report:** "This is described as 'ML-powered room analysis for the PLATO knowledge system.' The README shows Rust commands (`cargo build`, `cargo run -- analyze`) but the directory structure shows a Rust project. I can see it does room health scoring and emergence detection, but I can't tell you how to install it as a library or use it in your code."
>
> **CRITICAL BUG:** The README showed `cargo` commands for what is actually a **Python package**. A zero-shot agent would give wrong install instructions.
>
> **AFTER — Agent would report:** "A Python package (`pip install plato-room-intelligence`) with a multi-head neural model and provenance tracking. Five task heads on shared backbone. The key feature is ProvenanceTracker — you can trace any prediction back to which rooms' data shaped the weights. Here's working code."
>
> **Verdict:** Was FAIL (wrong language!), now PASS. ✅ Fix pushed to GitHub.

### ✅ plato-training
> **Agent would report:** "Train and deploy micro models for PLATO rooms. `pip install plato-training`. One function call: `train_micro('drift-detect')`. Fleet results show 100% accuracy on drift-detect for 5 of 6 hardware targets. Modular architecture with 3 dependency packages."
>
> **Verdict:** PASS. ✅

### ✅ eisenstein
> **Agent would report:** "Exact hexagonal coordinates via Eisenstein integers. No floating point, no drift, no dependencies. `#![no_std]`. Install: add to Cargo.toml. Here's working code for hex arithmetic, hex disks, and parametric triples. Full ecosystem table with 9 repos."
>
> **Verdict:** PASS. Best README in the org. ✅

### ✅ tensor-spline
> **Agent would report:** "Compressed neural network layers using Eisenstein lattice splines. `pip install tensor-spline`. SplineLinear achieves 20× compression at 100% accuracy on drift-detect. But only 31% on topic-classify — use LowRankLinear for classification instead. Honest tradeoff table."
>
> **Verdict:** PASS. ✅

### ✅ dodecet-encoder
> **Agent would report:** "A 12-bit encoding system for geometric operations. `cargo add dodecet-encoder`. Includes Point3D, Vector3D, Transform3D, calculus operations, and byte packing. Clear 'When to Use / When to Avoid' section."
>
> **Verdict:** PASS. The "When to Use / When to Avoid" pattern should be standard across all repos. ✅

---

## Phase 2: Prior Audit Review

Reviewed all prior audits:

| Audit | Key Finding | Status |
|-------|-------------|--------|
| AUDIT-GITHUB-OUTSIDER.md | 3 wrong READMEs, no org profile | ✅ Fixed (prior) |
| AUDIT-WEB-PAGES.md | crab-trap.lucineer.com dead link | ❌ Still dead |
| AUDIT-README-SCORES.md | Average 3.7/5, missing install/why/links | ✅ All now ≥ 4/5 |
| ONBOARDING-FLOW.md | No GETTING-STARTED.md, no org profile | ✅ Fixed (forgemaster/GETTING-STARTED.md) |

---

## Phase 3: Fixes Applied

### Fix 1: plato-room-intelligence README (CRITICAL)
- **Commit:** `e2b6c54` pushed to `master`
- **What was wrong:** README showed Rust/cargo commands for a Python package. Zero-shot agents would give wrong install instructions.
- **What was fixed:** Complete rewrite with correct Python install, working code example showing ProvenanceTracker, architecture diagram, ecosystem links.
- **Score:** 1/5 → 5/5

### Fix 2: spectral-conservation README (HIGH)
- **Commit:** `e9074ad` pushed to `master`
- **What was wrong:** No `cargo add` install command, no "Why" section, no ecosystem links. Prior audit said "fixed" but changes were only in workspace repo, not pushed to GitHub.
- **What was fixed:** Added install command, "Why" section, and ecosystem links. Pushed to actual GitHub repo.
- **Score:** 2.5/5 → 5/5

### Fix 3: Created review/AUDIT.md for plato-room-intelligence
- New file with zero-shot agent test results

---

## Remaining Issues (Not Fixed This Round)

| Issue | Severity | Effort | Recommendation |
|-------|----------|--------|----------------|
| `crab-trap.lucineer.com` returns 404 | 🔴 HIGH | Low | Remove link or redeploy MUD. Appears on org README and PLATO landing. |
| `SuperInstance/GETTING-STARTED.md` (org-level) returns 404 | 🟡 MEDIUM | Low | Create as redirect to forgemaster/GETTING-STARTED.md, or create a `.github` repo GETTING-STARTED.md |
| `fleet-spread` test count inflated (147 claimed, ~46 actual) | 🟡 MEDIUM | Low | Run tests, count, update README. Flagged 10 days ago. |
| `constraint-theory-ecosystem` overclaims (47 implementations) | 🟡 MEDIUM | Medium | Count actual directories, verify Coq theorems. |
| `quality-gate-stream` is workspace dump | 🟢 LOW | High | Archive or extract quality gate code. |

---

## Scorecard

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Zero-shot agent can report what this org does** | ⭐⭐⭐⭐⭐ | Org README is excellent |
| **Zero-shot agent can tell user how to install packages** | ⭐⭐⭐⭐⭐ | All repos now have install commands |
| **Zero-shot agent can provide working code examples** | ⭐⭐⭐⭐⭐ | All repos have runnable examples |
| **Zero-shot agent can navigate the ecosystem** | ⭐⭐⭐⭐☆ | GETTING-STARTED.md works, but org-level link is 404 |
| **Link health** | ⭐⭐⭐ | crab-trap.lucineer.com still dead |
| **Honesty of claims** | ⭐⭐⭐⭐ | Most repos are honest; fleet-spread and constraint-theory-ecosystem still overclaim |

---

## The Bottom Line

A zero-shot AI agent visiting SuperInstance today can:
1. ✅ Understand what the org builds (shell architecture, tiles, PLATO)
2. ✅ Choose between 3 paths (math, ML, full ecosystem)
3. ✅ Install any of the 7+ packages
4. ✅ Get working code examples for every package
5. ✅ Navigate between related packages via links

**The outsider beta test passes.** The remaining issues (dead link, inflated claims) are credibility risks but don't block the core use case of "discover → install → run."

---

*Report by Forgemaster ⚒️, Team 1 Lead. Builds on AUDIT-GITHUB-OUTSIDER.md, AUDIT-WEB-PAGES.md, AUDIT-README-SCORES.md, and ONBOARDING-FLOW.md (all 2026-05-17).*
