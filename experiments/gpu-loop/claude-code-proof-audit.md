# Proof Audit: Spectral First Integral Theory

You are a mathematical proof auditor. Read ALL of the following documents in order, then produce a rigorous audit of every theorem, lemma, conjecture, and claim.

## Files to Read (in this directory)

1. `MATH-SPECTRAL-FIRST-INTEGRAL.md` — Core theory (12 theorems, 5 conjectures)
2. `MATH-KOOPMAN-EIGENFUNCTION.md` — Koopman eigenfunction analysis
3. `MATH-JAZZ-THEOREM.md` — Spectral shape conservation under trajectory divergence
4. `MATH-TEMPORAL-GEOMETRY.md` — Temporal geometry and spectral conservation
5. `MATH-LATTICE-SPLINE.md` — Lattice-spline interpretation
6. `MATH-LYAPUNOV-MONOTONICITY.md` — Lyapunov monotonicity analysis
7. `MATH-DIMENSION-SCALING.md` — Dimensional scaling experiments
8. `METAL-TO-PLATO.md` — Implementation layers (skip code, focus on math claims)

## Audit Instructions

For EVERY theorem/lemma/proposition/conjecture/claim across all 8 documents, provide:

### 1. THEOREM STATUS Classification

Assign one of:
- **PROVED** — Complete, rigorous proof with no gaps
- **PROVABLE** — Proof sketch is correct and can be made rigorous with standard techniques; specify what's needed
- **CONJECTURE** — Supported by evidence but proof sketch has fundamental gaps or unjustified steps
- **WRONG** — Counterexample exists or logical error identified

### 2. For each theorem, analyze:

a) **Statement clarity**: Is the statement precise? Are all assumptions explicit? Are quantifiers correct?
b) **Proof completeness**: Is the proof complete? If a "proof sketch," what steps are missing?
c) **Logical gaps**: Any circular reasoning, unstated assumptions, or jumps?
d) **Rigor level**: On a scale of 1-5 (1=handwaving, 5=Lean-verifiable)
e) **Dependencies**: What other results does this proof rely on? Are those dependencies solid?

### 3. Cross-document consistency

Check for contradictions or tensions between documents. For example:
- Does the Koopman eigenfunction result conflict with the Lyapunov monotonicity findings?
- Are the scaling laws consistent across documents?
- Do the three conservation regimes (structural/dynamical/transitional) have consistent definitions?

### 4. Identify the STRONGEST honest claim

Given the audit results, what is the strongest theorem that can be honestly claimed with full rigor? What would need to change for the next strongest claim?

### 5. Prioritized list of proofs to formalize

Rank by: (a) mathematical importance, (b) feasibility, (c) gap size

## Output Format

Produce a structured report with:

```
# PROOF AUDIT REPORT

## Executive Summary
[3-5 sentences: overall rigor level, strongest honest claim, biggest gaps]

## Document-by-Document Audit

### MATH-SPECTRAL-FIRST-INTEGRAL
[For each numbered theorem/proposition/conjecture]

#### Theorem X.Y: [Title]
- **Status:** PROVED / PROVABLE / CONJECTURE / WRONG
- **Statement clarity:** [assessment]
- **Proof completeness:** [assessment]
- **Logical gaps:** [list]
- **Rigor level:** 1-5
- **Dependencies:** [list]
- **Notes:** [anything else]

[Repeat for all results]

### MATH-KOOPMAN-EIGENFUNCTION
[Same format]
...

## Cross-Document Issues
[List contradictions, tensions, or inconsistencies]

## The Strongest Honest Claim
[What can be claimed with full rigor right now]

## Proof Formalization Priority List
| Priority | Theorem | Why | Gap Size | Feasibility |
|----------|---------|-----|----------|-------------|
| 1 | ... | ... | ... | ... |
...

## Key Definitions That Need Tightening
[List definitions that are imprecise or have hidden assumptions]

## Summary Statistics
- Total theorems/propositions audited: N
- PROVED: N
- PROVABLE: N
- CONJECTURE: N
- WRONG: N
- Average rigor level: X.X / 5
```

Be brutally honest. Mathematical reputation depends on not claiming more than is proved.
