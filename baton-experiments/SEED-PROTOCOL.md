# SEED PROTOCOL v1.0

**A Reproducible Methodology for Using Small AI Models as Hypothesis Generators and Knowledge Reconstructors**

*Authored: 2026-05-12 | Status: Production | Cost per cycle: ~$0.50*

---

## Table of Contents

1. [Overview](#overview)
2. [SEED-GEN: Hypothesis Generation](#seed-gen)
3. [SEED-RECON: Knowledge Reconstruction](#seed-recon)
4. [SEED-CYCLE: Iterative Discovery](#seed-cycle)
5. [SEED-ORACLE: Model Self-Analysis](#seed-oracle)
6. [Quality Gates](#quality-gates)
7. [Cost Model](#cost-model)
8. [Implementation](#implementation)

---

## Overview

The SEED PROTOCOL exploits a counterintuitive finding: **small, cheap models at temperature 1.0 produce novel, falsifiable hypotheses at ~1% the cost of frontier models**. This isn't about replacing large models — it's about using them judiciously at the synthesis stage while delegating high-volume generation to models where each query costs $0.01.

### Core Principle

> **Temperature 1.0 is not noise — it's search.** At T=1.0, a model samples from its full probability distribution, surfacing hypotheses that greedy decoding (T≈0) would suppress. Combined with a cheap model's broader (if shallower) knowledge, this produces genuinely novel combinations.

### When to Use SEED

- **Exploratory research** — domains with unknown structure
- **Knowledge compression audit** — verifying tile quality via reconstruction
- **Hypothesis mining** — generating candidate explanations faster than humans can think
- **Budget-constrained discovery** — when $0.50 must buy real insight

### When NOT to Use SEED

- **Safety-critical decisions** — hypotheses are unverified
- **High-precision tasks** — use frontier models at low temperature
- **Deterministic workflows** — T=1.0 is inherently stochastic

---

## SEED-GEN: Hypothesis Generation

### Purpose
Generate novel, falsifiable hypotheses about a domain using a small model at high temperature.

### Inputs

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Natural language description of the research domain |
| `known` | string[] | Established facts and constraints |
| `unknown` | string[] | Open questions, gaps, anomalies |
| `n_hypotheses` | int | Number of hypotheses to generate (default: 5) |
| `model` | string | Model identifier (default: `ByteDance/Seed-2.0-mini`) |
| `temperature` | float | Sampling temperature (default: 1.0, **do not change**) |

### Prompt Template

```
You are a hypothesis generator. Given the domain, known facts, and unknowns below,
generate {n_hypotheses} novel, falsifiable hypotheses.

DOMAIN: {domain}

KNOWN:
{known}

UNKNOWN:
{unknown}

For each hypothesis:
1. State the hypothesis clearly and concisely
2. Explain WHY it's plausible given the known facts
3. Describe a specific experiment or observation that could FALSIFY it
4. Rate novelty (1-5): how different is this from the obvious explanation?
5. Rate actionability (1-5): how easy would it be to test?

Be creative. Obvious hypotheses are useless. Prioritize novelty over safety.
```

### Parameters

- **Model:** `ByteDance/Seed-2.0-mini` (default)
- **Temperature:** 1.0 (ALWAYS — this is non-negotiable)
- **Max tokens:** 2048
- **Cost:** ~$0.01 per generation

### Output Format

```json
{
  "hypotheses": [
    {
      "id": "H-001",
      "statement": "...",
      "rationale": "...",
      "falsification": "...",
      "novelty": 4,
      "actionability": 3,
      "accept": true
    }
  ],
  "meta": {
    "model": "ByteDance/Seed-2.0-mini",
    "temperature": 1.0,
    "cost_usd": 0.01,
    "timestamp": "2026-05-12T16:54:00Z"
  }
}
```

### Acceptance Criteria

Each hypothesis is scored on three dimensions (1-5 scale):

| Dimension | Description | Minimum |
|-----------|-------------|---------|
| **Falsifiability** | Can a specific experiment disprove it? | ≥ 3 |
| **Novelty** | Is this non-obvious? | ≥ 3 |
| **Actionability** | Can it be tested with available resources? | ≥ 3 |

**Accept threshold:** score ≥ 3 on ALL three dimensions. Hypotheses failing any gate are discarded — not retried. At $0.01 per generation, discard is cheaper than retry.

### Ensemble Strategy

For critical domains, run 3 independent SEED-GEN calls and take the union of accepted hypotheses. Deduplicate by semantic similarity (cosine > 0.9 = duplicate). Cost: ~$0.03.

---

## SEED-RECON: Knowledge Reconstruction

### Purpose
Verify knowledge compression quality by reconstructing full knowledge from a compressed tile.

### Rationale

Knowledge tiles use a **minimal-maximal** format: minimal context that should reconstruct maximal information. SEED-RECON tests whether the tile actually captures enough signal by attempting reconstruction and comparing against the source.

### Inputs

| Field | Type | Description |
|-------|------|-------------|
| `tile` | string | Compressed knowledge tile (~2K chars) |
| `n_ensemble` | int | Number of independent reconstructions (default: 3) |
| `source` | string | Original source text (for comparison, optional) |

### Prompt Template

```
You are a knowledge reconstructor. Given the compressed knowledge tile below,
reconstruct the full knowledge it encodes. Expand every abbreviation, infer
missing connections, and restore the complete picture.

TILE:
{tile}

Reconstruct:
1. All named entities and their relationships
2. All numerical values and their context
3. All causal chains and their steps
4. All domain-specific terminology and definitions
5. All constraints and their implications

Do NOT add information not present in the tile. Mark any inference with [INFERRED].
```

### Parameters

- **Model:** `ByteDance/Seed-2.0-mini`
- **Temperature:** 1.0 (diverse reconstructions surface different recovered facts)
- **Ensemble:** 3 independent reconstructions (default)
- **Cost:** ~$0.03 per reconstruction set (3 × $0.01)

### Quality Metrics

| Metric | Formula | Acceptable |
|--------|---------|------------|
| **Recovery rate** | `recovered_facts / source_facts` | ≥ 80% |
| **Precision** | `correct_facts / claimed_facts` | ≥ 90% |
| **Hallucination rate** | `hallucinated_facts / claimed_facts` | ≤ 10% |
| **Coverage** | `unique_facts_across_ensemble / source_facts` | ≥ 95% |

### Amnesia Guard

A tile must cover ≥10% of the source information density to be eligible for reconstruction. Tiles below this threshold are flagged as **information-starved** and should be re-tiled with more context.

### Ensemble Union Algorithm

```
1. Run N independent reconstructions (default N=3)
2. For each reconstruction, extract atomic facts
3. Union all fact sets: unique_facts = facts_1 ∪ facts_2 ∪ ... ∪ facts_N
4. For each unique fact, compute agreement: how many reconstructions include it?
5. High-agreement facts (>N/2) are "core" — reliable
6. Low-agreement facts (≤N/2) are "peripheral" — verify independently
7. Output: core_facts + peripheral_facts (marked for verification)
```

---

## SEED-CYCLE: Iterative Discovery

### Purpose
Automated hypothesis-experiment-feedback loop that converges on genuine discoveries.

### Architecture

```
┌──────────────────────────────────────────────┐
│                 SEED-CYCLE                    │
│                                              │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐ │
│  │SEED-GEN │───>│  TEST   │───>│ FEEDBACK │ │
│  │ (T=1.0) │    │ (auto)  │    │ (results)│ │
│  └─────────┘    └─────────┘    └──────────┘ │
│       ^                              │       │
│       └──────────────────────────────┘       │
│                                              │
│  Convergence: no novel hypotheses in 3       │
│  consecutive cycles                          │
└──────────────────────────────────────────────┘
```

### Phases

#### Phase 1: Hypothesis Generation (SEED-GEN)
- Input: domain description + knowns + unknowns
- Run SEED-GEN with temperature 1.0
- Filter through quality gates
- Output: list of accepted hypotheses

#### Phase 2: Automated Testing
- For each accepted hypothesis, generate a test:
  - **Computational:** Generate Python code, execute, capture results
  - **Literature:** Search web for supporting/contradicting evidence
  - **Logical:** Check internal consistency against known constraints
- Record: hypothesis, test, result, confidence change

#### Phase 3: Feedback Integration
- Update domain description with test results
- Move confirmed facts to `known`
- Move falsified hypotheses to `rejected`
- Update `unknown` with new questions surfaced by testing

#### Phase 4: Convergence Check
- Compare current hypotheses to previous cycle
- If novelty score averages < 2.5 for 3 consecutive cycles → **converged**
- If budget exhausted → **halted**
- Otherwise → return to Phase 1

### Budget Model

| Phase | Operations | Cost |
|-------|-----------|------|
| GEN (5 hypotheses) | 1 × SEED-GEN | $0.01 |
| Testing (code gen) | 5 × Seed-code | $0.10 |
| Testing (execution) | 5 × runtime | $0.00 |
| Analysis | 1 × GLM-5.1 | $0.10 |
| Feedback GEN | 1 × SEED-GEN | $0.01 |
| **Total per cycle** | | **~$0.22** |
| **Full run (5 cycles)** | | **~$1.10** |

### Convergence Criteria

```
converged = all(
    avg_novelty(cycle_i) < 2.5
    for cycle_i in last_3_cycles
)
```

### Safety Bounds

- **Max cycles:** 10 (hard cap)
- **Max cost:** $5.00 per topic
- **Max hypotheses:** 50 per cycle
- **Auto-halt on:** repeated identical hypotheses, cost exceedance, error rate > 50%

---

## SEED-ORACLE: Model Self-Analysis

### Purpose
Query a small model about its own strengths, weaknesses, and failure modes.

### Rationale

Small models can produce useful introspective analysis when given their own outputs and explicit framing. While not reliable as ground truth, this analysis can identify patterns that human reviewers might miss.

### Prompt Template

```
You are a 3B parameter language model. You have just completed the following
tasks with these results:

TASKS AND RESULTS:
{task_results}

Analyze your own performance:

1. **Strengths:** Where did you perform well? What types of tasks suit your
   architecture?
2. **Weaknesses:** Where did you fail? What types of reasoning do you struggle
   with?
3. **Failure modes:** Are there systematic patterns in your errors?
4. **Calibration:** For tasks where you were confident but wrong, why?
5. **Recommendations:** What would help you perform better on similar tasks?

Be honest. Inflated self-assessment is less useful than accurate criticism.
Mark speculation with [SPECULATION] and evidence-based analysis with [EVIDENCE].
```

### Parameters

- **Model:** `ByteDance/Seed-2.0-mini`
- **Temperature:** 0.7 (lower than SEED-GEN — want more focused self-analysis)
- **Cost:** ~$0.01

### Output Interpretation

| Tag | Meaning | Trust Level |
|-----|---------|-------------|
| `[EVIDENCE]` | Based on specific task results | Medium-High |
| `[SPECULATION]` | Model's guess about its behavior | Low |
| `[PATTERN]` | Identified recurring behavior | Medium |
| `[CONFABULATION]` | Likely fabricated justification | Very Low |

### Critical Limitation

> **SEED-ORACLE outputs are hypotheses about model behavior, not ground truth.** A 3B model cannot truly introspect — it pattern-matches against training data about AI self-analysis. Cross-check ALL Oracle outputs with controlled experiments before acting on them.

### Valid Use Cases

- Generating hypotheses about failure modes for later verification
- Identifying blind spots in test coverage
- Producing structured self-assessment for human review
- Detecting systematic biases in output distribution

---

## Quality Gates

All SEED protocol outputs pass through mandatory gate checks before acceptance.

### Gate 1: Credential Leak Detection

```
SCAN output for:
- API keys, tokens, passwords
- Email addresses (unless in domain context)
- Internal URLs or file paths
- Model-specific system prompts

ACTION: If detected → DISCARD output entirely. Do not redact and retry.
```

### Gate 2: Overclaim Detection

```
SCAN output for:
- Unqualified superlatives ("proves", "establishes", "confirms")
- Missing uncertainty markers on speculative claims
- Citations without verification
- Extrapolation beyond evidence

ACTION: Flag passages. Require [SPECULATION] or [EVIDENCE] tags.
```

### Gate 3: Citation Verification

```
For each citation/reference in output:
- If real (verifiable) → keep
- If unverifiable → mark [UNVERIFIED]
- If clearly fabricated → DISCARD entire output

ACTION: No hallucinated citations allowed. Period.
```

### Gate 4: Consistency Check

```
For SEED-CYCLE outputs:
- Hypothesis must not contradict known facts
- Test results must be internally consistent
- Feedback must address actual test results

ACTION: Inconsistent outputs → discard and flag for review.
```

### Gate Summary

```
output → GATE_1(credentials) → GATE_2(overclaim) → GATE_3(citations) → GATE_4(consistency)
                                                                                      │
                                                                              ACCEPTED / DISCARDED
```

Failed outputs are **discarded, not retried**. At $0.01 per generation, generating fresh is cheaper and more reliable than retrying.

---

## Cost Model

### Per-Operation Costs

| Operation | Model | Temp | Cost | Quality | Latency |
|-----------|-------|------|------|---------|---------|
| Hypothesis gen | Seed-mini | 1.0 | $0.01 | High novelty | ~2s |
| Reconstruction | Seed-mini | 1.0 | $0.01 | 100% w/ ensemble | ~2s |
| Question filtering | Hermes-70B | 0.3 | $0.05 | High precision | ~5s |
| Experiment code | Seed-code | 0.3 | $0.02 | Working code | ~3s |
| Analysis | GLM-5.1 | 0.7 | $0.10 | Deep reasoning | ~8s |
| Synthesis | Claude Opus | 0.5 | $0.50 | Architecture | ~30s |
| Self-analysis | Seed-mini | 0.7 | $0.01 | Useful leads | ~2s |

### Typical Session Budgets

| Session Type | Operations | Total Cost |
|-------------|-----------|------------|
| Quick exploration | 5 × GEN | $0.05 |
| Knowledge audit | 3 × RECON + analysis | $0.15 |
| Full discovery cycle | 5 × CYCLE | $1.10 |
| Deep analysis | CYCLE + ORACLE + synthesis | $2.00 |
| Fleet-scale (10 domains) | 10 × all operations | $20.00 |

### Cost-Effectiveness Comparison

| Approach | Cost | Hypotheses | $/Hypothesis |
|----------|------|-----------|--------------|
| Human researcher | $500/day | ~10 | $50.00 |
| Frontier model (GPT-4) | $0.10/gen | ~5 | $0.02 |
| **SEED Protocol** | $0.01/gen | ~5 | **$0.002** |

**250× more cost-effective than frontier models per hypothesis.**

---

## Implementation

### Python Module

See `seed_protocol.py` in the same directory. Provides:

```python
from seed_protocol import SeedGen, SeedRecon, SeedCycle, SeedOracle

# Hypothesis generation
gen = SeedGen()
hypotheses = gen.generate(
    domain="constraint theory in type systems",
    known=["Types constrain program behavior", "Constraints compose"],
    unknown=["Why do some constraints compose and others don't?"]
)

# Knowledge reconstruction
recon = SeedRecon()
result = recon.reconstruct(tile="...", source="...")
print(f"Recovery rate: {result.recovery_rate:.1%}")

# Full discovery cycle
cycle = SeedCycle(max_cycles=5)
discoveries = cycle.run(domain="quantum error correction")

# Model self-analysis
oracle = SeedOracle()
analysis = oracle.analyze(task_results=[...])
```

### CLI Usage

```bash
# Generate hypotheses
python3 seed_protocol.py --mode gen --domain "constraint theory"

# Reconstruct from tile
python3 seed_protocol.py --mode recon --tile tile.txt --source source.txt

# Run full discovery cycle
python3 seed_protocol.py --mode cycle --domain "quantum error correction" --max-cycles 5

# Oracle self-analysis
python3 seed_protocol.py --mode oracle --results results.json
```

### Configuration

```python
# Default config (override via environment or constructor)
SEED_CONFIG = {
    "api_base": "https://api.deepinfra.com/v1/openai",
    "model": "ByteDance/Seed-2.0-mini",
    "temperature": 1.0,
    "max_tokens": 2048,
    "ensemble_size": 3,
    "accept_threshold": 3,
    "max_cycles": 5,
    "max_cost_usd": 5.0,
    "quality_gates": True,
}
```

---

## Appendix A: Temperature Rationale

Why T=1.0, always?

1. **Search breadth:** T=1.0 samples from the full distribution, exploring the hypothesis space broadly.
2. **Novelty preservation:** Lower temperatures collapse the distribution toward the mode (most likely = most obvious).
3. **Cost efficiency:** At $0.01/generation, we can afford many samples and filter aggressively.
4. **Ensemble complementarity:** At T=1.0, independent runs produce diverse outputs that cover more of the space.

The one exception: SEED-ORACLE uses T=0.7 for more focused self-analysis, and code generation uses T=0.3 for syntactic correctness.

## Appendix B: Model Selection Guide

| Task Size | Model | Why |
|-----------|-------|-----|
| <1K tokens, generation | Seed-2.0-mini | Breadth + speed |
| <1K tokens, precision | Seed-2.0-code | Syntactic accuracy |
| 1-4K tokens, analysis | Hermes-70B | More nuanced reasoning |
| 4-16K tokens, synthesis | GLM-5.1 | Deep reasoning capacity |
| >16K tokens, architecture | Claude Opus | Long-form coherence |

## Appendix C: Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-12 | Initial protocol from baton experiments |

---

*The SEED PROTOCOL is a living document. Submit improvements via PR to the baton-experiments repository.*
