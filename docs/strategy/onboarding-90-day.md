# FLUX Engineer Onboarding — 90-Day Plan

*Last updated: 2026-05-03*

---

## Overview

This plan takes a new engineer from zero to independently contributing to FLUX in 90 days. It assumes solid programming skills (C or Rust) and general software engineering experience, but no prior formal verification background.

**Pacing:** 40% learning, 40% building, 20% reviewing. The plan accelerates — weeks 1–2 are structured learning, weeks 7–12 are mostly autonomous work with mentor check-ins.

**Mentor:** Every new engineer is assigned a mentor (senior FLUX contributor) for the full 90 days. Daily check-ins during weeks 1–2, three times per week during weeks 3–6, weekly during weeks 7–12.

**Goal:** By day 90, the engineer has merged at least one significant PR (new constraint type, optimization pass, or compilation target) and can independently handle verification issues filed by users.

---

## Phase 1: Foundations (Weeks 1–2)

### Week 1: Environment and First Verification

**Goals:** Working development environment, successful first verification, understand the build.

| Day | Activity | Output |
|-----|----------|--------|
| 1 | Set up dev environment: clone FLUX, build from source, run test suite | Green local build, all tests passing |
| 2 | Read FLUX architecture overview (internal doc), GUARD language spec | Annotated copy with questions for mentor |
| 3 | Complete "thermostat controller" tutorial | Verified tutorial project, tutorial feedback notes |
| 4 | Read proof engine internals: how GUARD → SMT obligations | Diagram of proof pipeline (draw it yourself) |
| 5 | Pair with mentor on a real bug fix or small improvement | First commit (even if trivial) |

**Reading (Week 1):**
- FLUX Language Guide (docs.flux.dev/language-guide) — ~2 hours
- "How to Prove Things with SMT Solvers" (internal tech talk recording) — ~1 hour
- FLUX contributor guide (CONTRIBUTING.md) — ~30 minutes

**Check-in:** Friday — discuss architecture diagram, address questions, set Week 2 goals.

### Week 2: The Math You Need

**Goals:** Understand the formal foundations without getting lost in theory.

| Day | Activity | Output |
|-----|----------|--------|
| 1 | Propositional and first-order logic refresher (self-study) | Completed exercises |
| 2 | SMT solver basics: DPLL(T), theory solvers, quantifier instantiation | Notes on how Z3 works |
| 3 | Constraint systems: how FLUX maps program semantics to logical formulas | Trace through a real constraint end-to-end in debugger |
| 4 | Proof certificates: what they contain, how they're validated, why they matter | Validate a certificate by hand (manual steps) |
| 5 | Codebase deep-dive: proof engine module walkthrough with mentor | Understanding of module boundaries |

**Reading (Week 2):**
- *Logic in Computer Science* (Huth & Ryan), Chapters 1–3 — ~6 hours
- Z3 tutorial (microsoft.github.io/z3guide) — ~2 hours
- "The FLUX Proof Certificate Format" (internal spec) — ~1 hour

**Check-in:** Friday — discuss logic exercises, trace-through findings. Mentor assigns Week 3 project.

---

## Phase 2: First Contributions (Weeks 3–6)

### Week 3: Write Your First Constraint

**Goals:** Write a real constraint for FLUX's own test suite (FLUX verifies itself).

| Day | Activity | Output |
|-----|----------|--------|
| 1 | Study existing test suite constraints | List of coverage gaps |
| 2–3 | Write a new constraint for an uncovered module | `.guard` file + proof |
| 4 | Write the test infrastructure: expected results, regression test | Test case in PR |
| 5 | Submit PR, iterate on review feedback | Merged PR (or close to merge) |

**Deliverable:** Merged PR adding a new constraint to FLUX's self-verification test suite.

**Reading (Week 3):**
- Existing constraint library examples (20+ `.guard` files in the test suite)
- GUARD style guide (internal doc)

### Week 4: Understand a Constraint Type

**Goals:** Pick an existing constraint type and understand it deeply enough to explain it.

| Day | Activity | Output |
|-----|----------|--------|
| 1–2 | Choose a constraint type (e.g., array bounds, overflow, or temporal). Read its implementation end-to-end. | Annotated walkthrough document |
| 3 | Trace how the constraint type generates SMT obligations | Worked example with actual solver output |
| 4 | Find and document edge cases or known limitations | Issue(s) filed with analysis |
| 5 | Propose an improvement (even if small) | RFC comment or issue discussion |

**Deliverable:** Internal tech brief on one constraint type (shared with team for feedback).

**Reading (Week 4):**
- Constraint type implementation files (varies by choice)
- Related academic paper (mentor recommends based on type chosen)

### Week 5–6: Implement a New Constraint Type

**Goals:** Add a genuinely new constraint type to FLUX. This is the main technical ramp-up milestone.

| Day | Activity | Output |
|-----|----------|--------|
| 1–2 | Design the constraint type with mentor: syntax, semantics, proof strategy | Design doc (1–2 pages) |
| 3–4 | Implement GUARD parser extension | Parser changes passing tests |
| 5–7 | Implement SMT obligation generation | Proof engine producing correct obligations |
| 8–9 | Implement proof certificate generation and validation | End-to-end: constraint → proof → validation |
| 10 | Testing, documentation, PR submission | PR with tests, docs, and examples |

**Deliverable:** PR implementing a new constraint type. Mentor and one additional reviewer must approve.

**Reading (Weeks 5–6):**
- Relevant domain literature (depends on constraint type chosen)
- FLUX internal: "Adding a New Constraint Type" guide (internal wiki)

**Mentor check-in:** Three times per week during implementation. Blockers escalate immediately.

---

## Phase 3: Deepening (Weeks 7–9)

### Week 7: Optimization Pass

**Goals:** Understand and contribute to FLUX's proof optimization — making verification faster.

| Day | Activity | Output |
|-----|----------|--------|
| 1 | Study existing optimization passes: lemma caching, obligation pruning, solver hint generation | Notes on current optimizations |
| 2–3 | Profile a real-world verification workload (FLUX team provides benchmark) | Performance profile with bottleneck identification |
| 4–5 | Implement an improvement (new optimization, better heuristic, or cache improvement) | PR with benchmark results showing improvement |

**Deliverable:** Merged optimization PR with measurable performance improvement.

**Reading (Week 7):**
- "Scaling SMT-Based Verification" (FLUX internal tech report)
- Relevant papers on SMT solver performance (mentor recommends)

### Week 8: New Compilation Target

**Goals:** Add or improve support for a compilation target, understanding the proof preservation pipeline.

| Day | Activity | Output |
|-----|----------|--------|
| 1 | Study target-independent IR and how targets plug in | Architecture notes |
| 2 | Study an existing target implementation (e.g., ARM Thumb-2) | Annotated code walkthrough |
| 3–5 | Implement or improve a target (options: new backend, bug fix, or missing preservation proof for an existing target) | PR with target changes |

**Deliverable:** Target-related PR. Could be new target, new preservation proof, or significant bug fix.

**Reading (Week 8):**
- "Proof Preservation Across Compilation" (FLUX design doc)
- Target-specific documentation (ARM/RISC-V/LLVM references)

### Week 9: Formal Proof Component

**Goals:** Work on the formally verified core of FLUX — the components whose correctness is proved in Coq or Lean.

| Day | Activity | Output |
|-----|----------|--------|
| 1 | Introduction to FLUX's formal proof infrastructure | Understanding of what's proved and what isn't |
| 2–3 | Study one proved component (e.g., certificate validator, obligation generator) | Walkthrough document |
| 4–5 | Extend a proof or add a new lemma (with mentor guidance) | PR updating formal proof |

**Deliverable:** PR extending a formal proof. Even a small lemma extension is valuable — this is the hardest part of FLUX.

**Reading (Week 9):**
- *Certified Programming with Dependent Types* (Chlipakaa), relevant chapters
- FLUX Coq/Lean library documentation (internal)

---

## Phase 4: Independence (Weeks 10–12)

### Week 10: Qualification Package Contribution

**Goals:** Understand the certification side of FLUX and contribute to the tool qualification kit.

| Day | Activity | Output |
|-----|----------|--------|
| 1–2 | Study DO-330 tool qualification requirements and FLUX's TQK structure | Understanding of TQK components |
| 3–5 | Contribute to the TQK: add test cases, update evidence, or improve traceability | TQK PR |

**Deliverable:** Contribution to the tool qualification kit.

**Reading (Week 10):**
- DO-330 overview (internal summary, ~30 pages)
- FLUX TQK structure guide (internal)

### Week 11: User-Facing Issue Resolution

**Goals:** Handle real user issues independently (with mentor review before responding).

| Day | Activity | Output |
|-----|----------|--------|
| 1–2 | Shadow mentor handling 2–3 open GitHub issues | Understanding of common user problems |
| 3–5 | Take ownership of 2–3 issues: reproduce, diagnose, fix | PRs fixing user-reported issues |

**Deliverable:** 2+ resolved user issues with PRs merged.

### Week 12: Capstone and Review

**Goals:** Deliver a significant independent contribution and complete the onboarding review.

| Day | Activity | Output |
|-----|----------|--------|
| 1–3 | Capstone project: choose from a curated list of medium-complexity tasks | PR (or near-complete PR) on a substantial feature |
| 4 | Write onboarding retrospective: what worked, what didn't, suggestions for improving this plan | Retrospective document (shared with team) |
| 5 | Onboarding review with mentor and engineering manager | 360° feedback, goal-setting for next quarter |

**Deliverable:** Capstone PR + retrospective document.

---

## Reading List

### Required (completed during 90 days)

| Resource | Topics | Time |
|----------|--------|------|
| FLUX Language Guide | GUARD syntax, proof strategies | 2 hours |
| *Logic in Computer Science* (Huth & Ryan), Ch. 1–5 | Propositional logic, predicate logic, verification | 12 hours |
| Z3 Tutorial | SMT solving basics | 2 hours |
| "CompCert: A CompCert-Verified Compiler" (Leroy, 2009) | Verified compilation principles | 3 hours |
| "seL4: Formal Verification of an OS Kernel" (Klein et al., 2009) | Large-scale verification | 3 hours |
| DO-330 Overview (internal) | Tool qualification for safety-critical systems | 4 hours |
| FLUX Internal Docs (architecture, constraint types, proof preservation) | FLUX-specific | 8 hours |

**Total: ~34 hours of structured reading over 90 days (~4 hours/week).**

### Recommended (ongoing, beyond 90 days)

| Resource | Why |
|----------|-----|
| *Certified Programming with Dependent Types* (Chlipala) | Coq proofs, dependent types |
| *Software Foundations* (Pierce et al.) | Interactive theorem proving |
| *Handbook of Satisfiability* (Biere et al.) | SAT/SMT solver internals |
| DO-178C / DO-330 full standard | Aerospace certification details |
| ISO 26262 Part 6 (Product Development — Software) | Automotive software safety |
| "The Meaning of GIGO" (internal FLUX essay) | Why proof integrity matters |

### Domain Background (pick based on your focus area)

| Domain | Resource |
|--------|----------|
| Automotive | ISO 26262 summary, AUTOSAR documentation |
| Aerospace | DO-178C overview, ARP4754A |
| Medical | IEC 62304 summary, FDA guidance on software |
| Industrial | IEC 61508 summary, machinery directive |

---

## Milestones and Checkpoints

| Week | Milestone | Success Criteria |
|------|-----------|-----------------|
| 1 | Environment set up | Build from source, tests pass, first commit |
| 2 | Foundations complete | Logic exercises done, can explain proof pipeline |
| 3 | First constraint written | `.guard` file PR merged |
| 6 | New constraint type | Full implementation PR merged |
| 7 | Optimization pass | Performance improvement PR merged |
| 8 | Target work | Target-related PR merged |
| 9 | Formal proof | Proof extension PR merged (or in review) |
| 10 | Qualification contribution | TQK PR merged |
| 11 | User issue resolution | 2+ user issues resolved |
| 12 | Capstone complete | Substantial PR + retrospective |

**Escalation triggers** (mentor should flag these):
- Week 2: Can't explain proof pipeline → additional pairing sessions
- Week 4: Haven't found a constraint type to study → mentor assigns one
- Week 6: Constraint type PR stuck → pair programming sprint
- Week 9: Formal proof too challenging → switch to proof testing infrastructure

---

## First PR Expectations

The Week 3 "first constraint" PR sets the tone for the rest of onboarding. Here's what a good first PR looks like:

**Required:**
- `.guard` file with correct syntax and semantics
- Proof passes (`flux verify` reports success)
- Test case with expected results
- Brief description of what the constraint verifies and why it's useful

**Nice to have:**
- Edge case considerations in the constraint (documented)
- Performance observation (how long does proof take?)
- Comparison with alternative constraint formulations

**Not expected:**
- Perfect style on the first attempt (mentor will guide)
- Deep solver understanding (that comes later)
- Formal proof of the constraint itself (Week 9 territory)

---

## Mentoring Guidelines

For mentors assigned to new engineers:

1. **Block your calendar.** Daily 30-minute check-ins during weeks 1–2 are non-negotiable. Cancel only for emergencies.
2. **Review quickly.** New engineers are blocked on review feedback. First PR should get review within 4 hours.
3. **Explain the why.** "Add a `severity` field" is less useful than "We need severity because the DO-330 evidence generator categorizes constraints by criticality — without it, we can't produce DAL-A evidence."
4. **Don't rescue too early.** Let them struggle for 30–60 minutes before stepping in. The struggle is where learning happens.
5. **Celebrate milestones.** First merged PR, first constraint type, first formal proof — these matter. Acknowledge them publicly.

---

*Questions about this plan? Reach out to the engineering team at eng@flux.dev or open a discussion at [github.com/flux-framework/flux/discussions](https://github.com/flux-framework/flux/discussions).*
