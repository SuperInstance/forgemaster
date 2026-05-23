# README Quality Scorecard — Cocapn Ecosystem

**Date:** 2026-05-17 | **Reviewer:** Forgemaster ⚒️

## Criteria (1 point each)

| # | Criterion | What it looks like |
|---|-----------|-------------------|
| 1 | **WHAT** | One-sentence description a newcomer can understand |
| 2 | **WHY** | 1-2 sentences explaining when/why you'd use this |
| 3 | **Install** | Copy-paste command (`cargo add`, `pip install`, or Cargo.toml snippet) |
| 4 | **Code** | Working code example (5-10 lines minimum) |
| 5 | **Links** | Related repos, docs, or ecosystem pointer |

## Scores

| Repo | What | Why | Install | Code | Links | **Total** | Status |
|------|:----:|:---:|:-------:|:----:|:-----:|:---------:|--------|
| dodecet-encoder | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ✅ No changes |
| ASSEMBLY-GUIDE | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ✅ No changes |
| ECOSYSTEM-MAP | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ✅ No changes |
| plato-escalation-gate | ✅ | ✅ | ✅ | ✅ | ❌ | **4/5** | 🔧 Links added |
| plato-types | ✅ | ⚠️ | ✅ | ✅ | ✅ | **4/5** | 🔧 Why added |
| tensor-spline | ✅ | ✅ | ✅ | ✅ | ❌ | **4/5** | 🔧 Links added |
| plato-training | ✅ | ⚠️ | ❌ | ✅ | ⚠️ | **3.5/5** | 🔧 Rewritten |
| plato-model-ocean | ✅ | ⚠️ | ✅ | ✅ | ❌ | **3.5/5** | 🔧 Rewritten |
| plato-room-intelligence | ✅ | ⚠️ | ✅ | ✅ | ❌ | **3.5/5** | 🔧 Rewritten |
| plato-data | ✅ | ⚠️ | ❌ | ✅ | ❌ | **3/5** | 🔧 Rewritten |
| flux-lucid | ✅ | ❌ | ❌ | ✅ | ⚠️ | **3/5** | 🔧 Rewritten |
| spectral-conservation | ✅ | ❌ | ❌ | ✅ | ❌ | **2.5/5** | 🔧 Rewritten |

## Summary

- **Average before:** 3.7/5
- **After fixes:** All ≥ 4/5
- **Biggest pattern:** Missing install commands and missing "why use this" sections
- **Best README:** dodecet-encoder — the "When to Use / When to Avoid" pattern should be standard
- **Per-repo audits:** Each repo's `review/AUDIT.md` has detailed notes

## Common Fixes Applied

1. Added `cargo add` or `pip install` to every repo missing it
2. Added "Why use this?" section (2-3 sentences) where missing
3. Added "Related" links section pointing to ecosystem repos
4. Moved jargon-heavy descriptions after a newcomer-friendly intro
