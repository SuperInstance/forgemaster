# Fleet Executive Summary — Casey
**Date:** 2026-05-12 | **Scope:** 57 repos, 10 days, 9 agents

---

## What You Have

The fleet is producing real output. Tests pass, crates publish, services run. Dodecet-encoder has 98 passing tests and 824 lines of documentation. Fleet-murmur has logged 1,597 commits. The code works.

But the documentation surface is a mess. Half the repos have fewer than 50 lines of README. An outsider — an investor, a collaborator, a new engineer — would look at this org and see a graveyard of stub READMEs, not the working research fleet it actually is. That's a credibility problem.

---

## The Three Real Findings

**1. The fleet self-organized into six tiers without anyone designing them.**
Living code (dodecet-encoder, eisenstein), working infrastructure (flux-*, constraint-theory-*), auto-maintained services (fleet-murmur, health-monitor, quality-gate-stream), static knowledge papers, repos needing attention, and dormant/external repos. This emergence is significant — it means the fleet has coherent structure. But the tiers aren't labeled anywhere, so only someone who audited all 57 repos would know which tier a repo belongs to.

**2. Auto-maintained repos are the most misleading.**
Fleet-murmur (1,597 commits), fleet-health-monitor (1,589 commits), quality-gate-stream (1,590 commits) — these look extremely active. They are. But the commits are automated beachcomb cycles. The READMEs are 11 lines. Anyone reading the commit graph would think these are the most important repos in the org. They're infrastructure, not product. The README doesn't say that.

**3. A real bug was hiding in the prototypes.**
The `snap()` function had a mutation-during-search bug in the Python and JavaScript implementations that caused 36% of snap errors to exceed the covering radius. The Rust implementation (dodecet-encoder) was correct. The 98 Rust tests caught nothing because the bug lived in the prototype layer. This is a systematic risk: the fleet prototypes fast, implements in Rust, and never cross-checks them.

---

## What Needs to Happen

**Immediate (this shift):**
- Write proper READMEs for the 9 Tier 5 repos: constraint-theory-llvm, holonomy-consensus, intent-inference, constraint-inference, fleet-murmur-worker, flux-isa, guardc, papers, and archive or delete `claude` (empty repo).
- Delete flux-research-clone. It's a stale fork causing confusion.
- Add a one-paragraph "What tier is this repo?" section to each fleet service README, clarifying that the commit volume is automated maintenance, not human development.

**Short-term (next sprint):**
- Enforce a README linter: no repo ships without >50 lines. This is a measurement problem, not an agent discipline problem. Change what gets measured.
- Set up cross-language differential testing. Every Python/JS prototype must be fuzz-tested against the Rust implementation before it ships. The snap bug would have been caught in minutes.
- Build a fleet quality dashboard. You need a live view of the tier distribution, README line counts, and CI coverage across all 57 repos. Right now this information requires a full manual audit to reconstruct.

**Strategic:**
- The knowledge repos (negative-knowledge, intent-directed-compilation, sheaf-constraint-synthesis, etc.) need DOIs and proper academic README formatting. They're citable research assets sitting unpublished. That's leaving value on the table.
- Automated documentation needs to be part of the beachcomb loop. If Oracle1 is committing 1,500+ times to fleet services, it can also regenerate READMEs from service metadata. Documentation decay is proportional to maintenance frequency only if documentation is manual.

---

## The Bottom Line

The fleet is healthy. The code is better than the documentation suggests. The risk isn't technical failure — it's that the external surface of the org doesn't reflect the internal quality of the work. Fix the READMEs, add differential testing, and build the quality dashboard. The rest takes care of itself.

The fleet doesn't need an architect. It needs a gardener. Right now, the garden is overgrown at the edges.
