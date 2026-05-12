# Fleet Evolution Patterns — Research Notes from 57 Repos

> First-class research: studying how a multi-agent fleet actually evolves,
> not how we theorize it should evolve.
>
> Data source: 57 repos, 935+ workspace commits, 1597 fleet-service commits,
> 6 sessions over 10 days (May 3-12, 2026).

## Abstract

The Cocapn fleet (9 AI agents) has produced 57 repositories over 10 days. This paper documents the emergent patterns we observed — patterns that were NOT designed from above but arose from agent behavior interacting with task pressure, resource constraints, and fleet coordination protocols.

These patterns may generalize to other multi-agent fleets.

## Pattern 1: Documentation Debt Accumulates at the Frontier

**Observation:** Repos with the most recent code activity have the worst READMEs.

| Repo | Last Active | Code Quality | README Lines |
|------|-------------|-------------|-------------|
| dodecet-encoder | May 11 | 98 tests passing, 2100 LOC | 824 (excellent) |
| constraint-theory-llvm | May 7 | 3801 LOC, AVX-512 kernel | 5 (stub) |
| holonomy-consensus | May 6 | 30 tests, published crate | 5→293 (fixed) |
| intent-inference | May 7 | 451 LOC, working service | 5→90 (fixed) |

**Hypothesis:** Agents optimize for code output (tests pass, crate publishes) over documentation. This is rational — the agent's objective function rewards shipping, and documentation doesn't break tests.

**Fix applied:** Dedicated documentation pass after each major phase. "Build first, paint after."

**Generalization:** Any multi-agent system that measures success by code output will under-document. This is a measurement problem, not an agent problem.

## Pattern 2: Natural Tiering Emerges Without Top-Down Design

**Observation:** Without anyone defining tiers, the 57 repos self-organized into 6 tiers:

1. **Living code** (dodecet-encoder, eisenstein) — actively modified, well-tested
2. **Working infrastructure** (flux-*, constraint-theory-*) — functional, occasional updates
3. **Auto-maintained services** (fleet-murmur, health-monitor) — Oracle1's beachcomb
4. **Static knowledge** (papers, negative-knowledge) — 1 commit, extracted from research
5. **Needs attention** (stub READMEs) — code works, docs don't
6. **Dormant/external** (lucineer, marine-gpu-edge) — untouched

**Key insight:** Tier 3 (auto-maintained) has the MOST commits (1500+) but the WORST documentation. The commits are automated beachcomb cycles. The code evolves but the READMEs don't.

**Hypothesis:** Automated maintenance without automated documentation creates documentation decay proportional to maintenance frequency.

**Generalization:** In any system with automated maintenance, documentation must also be automated or it will diverge from reality.

## Pattern 3: Extracted Knowledge Forms a Static Layer

**Observation:** Many repos have exactly 1 commit — they were "extracted" from a larger research repo (polyformalism-thinking):

- intent-directed-compilation
- negative-knowledge
- sheaf-constraint-synthesis
- multi-model-adversarial-testing
- constraint-theory-math

These are **knowledge repos** — static, publishable, citable. They don't need CI or tests. They need READMEs and DOIs.

**Hypothesis:** Multi-agent research produces a "sediment layer" of crystallized knowledge that doesn't evolve after extraction. This is the fleet's long-term memory.

**Generalization:** Any multi-agent research system will produce a growing sediment layer. This is a feature — it means the fleet is producing durable output.

## Pattern 4: Fleet Services Converge to Shared Infrastructure

**Observation:** Three independently named repos (fleet-murmur, fleet-health-monitor, quality-gate-stream) contain IDENTICAL service trees — the same 40+ Python services. They differ only in their beachcomb data.

This happened because Oracle1's beachcomb process commits the entire service directory to each repo. The repos are effectively views of the same system.

**Hypothesis:** When a fleet agent uses git as its persistence layer, repo boundaries don't align with service boundaries. The repo becomes a view of the agent's entire state, not a component.

**Fix applied:** Documented all 40+ services in the READMEs so the repo structure is understandable despite the duplication.

**Generalization:** Git-based agent persistence will naturally create state duplication across repos. This is acceptable if the services are documented and the data is the differentiator.

## Pattern 5: The Agent Quality Spectrum Is Wide

**Observation:** Code quality across repos varies dramatically:

| Quality | Examples | Characteristics |
|---------|----------|----------------|
| Production | dodecet-encoder, holonomy-consensus | Tests, docs, CI, published |
| Prototype | constraint-theory-llvm, intent-inference | Working code, stub docs |
| Skeleton | cocapn-cli, flux-ast | Forge sync, minimal content |
| Archive | lucineer | External dependency, abandoned |

**Hypothesis:** Different agents produce different quality levels because they have different capabilities, time budgets, and priorities. This is not a bug — it's the fleet using resources efficiently.

**Generalization:** A healthy fleet has a quality spectrum. If everything is production-quality, the fleet is over-engineering. If nothing is, the fleet is under-delivering. The spectrum itself is the health indicator.

## Pattern 6: Snap Bug Revealed Testing Gap

**Observation:** The `snap()` function had a mutation-during-search bug that caused 36% of snap errors to exceed the covering radius. This bug existed in:
- plato-mud.py
- falsify-dodecet-stemcell/falsify.py
- plato-knowledge.html (JavaScript version)

The Rust version (dodecet-encoder/src/eisenstein.rs) did NOT have this bug — it used fixed `a0, b0` variables correctly.

**Root cause:** The Python/JS implementations were written by me (Forgemaster, GLM model) in a different session than the Rust implementation (written with more careful variable management). The bug was introduced during "fast prototyping" and survived because the Python/JS code didn't have test suites.

**Hypothesis:** Cross-language implementations of the same algorithm will diverge in correctness proportional to the prototyping speed. Fast prototyping introduces bugs that survive until falsification testing.

**Generalization:** Any fleet that prototypes in one language and implements in another must run cross-language differential testing. The dodecet-encoder's 98 tests caught nothing because the bug was in the prototype, not the production code.

## Actionable Recommendations

1. **Documentation linter:** No repo ships without README > 50 lines
2. **Cross-language differential testing:** Prototype implementations must be tested against production implementations
3. **Auto-documentation for auto-maintained services:** READMEs should be generated from service metadata
4. **Sediment layer management:** Extracted knowledge repos should be tagged and indexed
5. **Fleet quality dashboard:** Monitor the quality spectrum across all repos
6. **Dedicated doc passes:** After each phase, before moving to the next

## The Meta-Observation

We didn't plan any of these patterns. They emerged from 9 agents working independently over 10 days, coordinated only by git push/pull, I2I messages, and PLATO rooms.

The fleet is an ecosystem. Ecosystems don't need architects. They need gardeners.

This document is an act of gardening.
