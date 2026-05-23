# Org Profile Fix — Review

**Date:** 2026-05-17
**What:** Rewrote `SuperInstance/.github` profile README to be newcomer-first
**Commit:** `2b66cc0` on both `main` and `master` branches

---

## What Changed

### Before (Problems)
- First paragraph: Fred Wahl shipyard story (insider narrative, no clue what we build)
- Second paragraph: "agent fleets that learn like fishing crews on a floating dojo" — jargon wall
- Listed fleet vessels, domains, philosophy before any useful content
- No install commands, no "what to do first", no paths for different audiences
- A newcomer couldn't figure out what we build in 5 seconds, let alone 5 minutes

### After (Fix)
1. **First 3 lines**: "We build tiny AI models that know when to ask for help. Everything is open source, modular, and runs anywhere." Plain English. No jargon.
2. **Quick link**: Direct link to GETTING-STARTED.md with "pick a path, run code in 2 minutes"
3. **3-path onboarding**: Math/Constraints, Intelligent Models, Full Ecosystem — each with install commands and copy-paste examples
4. **Published packages table**: 7 packages (3 Rust crates, 4 Python) with one-line descriptions and install commands
5. **Key repos**: Top 5 repos with one-line descriptions (eisenstein, constraint-theory-core, plato-training, spectral-conservation, forgemaster)
6. **Stats**: 655+ tests, 80+ repos, 7 published packages — credibility markers up front
7. **Fred Wahl story**: Preserved below the fold. It's great narrative but newcomers need to understand the product first.

### Removed from top section
- Fleet vessel table (Oracle1, Forgemaster, JetsonClaw1, CCC) — internal infra
- 20-row domain table (cocapn.ai, purplepincher.org, etc.) — overwhelming for newcomers
- "The Philosophy" section (constraints breed clarity, first-person time, tabula plena) — belongs in docs, not landing page
- "The Math" section (Laman's theorem, H¹ cohomology, zero-holonomy) — too deep for first visit
- PLATO tile explanation — internal architecture detail
- keel-ttl CLI instructions — secondary to the main packages

### Preserved
- Fred Wahl shipyard story (moved to bottom section — still great narrative)
- Link to cocapn.ai and Casey's GitHub
- Apache-2.0 license mention
- The "constraints breed clarity" ethos (kept in the shipyard section)

---

## What This Fixes (from outsider audit)

| Audit Finding | Fix |
|---------------|-----|
| "Insider-first — newcomer can't figure out what we do in 5 seconds" | First 3 lines are plain English |
| "No 3-path quickstart" | 3 paths with install commands |
| "No GETTING-STARTED.md link" | Direct link at top |
| "Published packages buried" | Full table with install commands |
| "Fred Wahl story first thing" | Moved below onboarding |
| "No credibility markers visible" | Stats section: 655+ tests, 80+ repos |

---

## What Still Needs Doing (not in this task)

- Pin repos on org page (eisenstein, spectral-conservation, plato-training, constraint-theory-core)
- Add repo descriptions to repos missing them
- Fix fleet-spread test count inflation (147 → actual count)
- Audit constraint-theory-ecosystem inflated claims
- Clean up quality-gate-stream monorepo dump
