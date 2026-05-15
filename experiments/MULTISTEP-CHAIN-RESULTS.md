# Study 37: Multi-Step Computation Chains

**Date:** 2026-05-15  
**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)  
**Temperature:** 0.1 | **Trials:** 5 per condition | **Total calls:** 90  

## Hypothesis

Single-expression pre-computation works (100% accuracy from prior studies). Does it scale to multi-step chains?

## Test Design

6 chains of increasing complexity, each tested in 3 modes:

| Mode | Description |
|------|-------------|
| **vocab** | Domain vocabulary only ("Eisenstein norm N(a,b)=a²-ab+b²") |
| **precomp** | All arithmetic pre-computed, only final sum asked |
| **semi** | Formula given but values NOT substituted (partial translation) |

## Results

### Accuracy by Chain × Mode

| Chain | Steps | Expected | vocab | precomp | semi |
|-------|:-----:|:--------:|:-----:|:-------:|:----:|
| chain1 (2 norms) | 2 | 86 | **0%** | **100%** | **0%** |
| chain2 (3 norms) | 3 | 114 | **0%** | **100%** | **0%** |
| chain3 (domain ω) | 3 | 114 | **0%** | **100%** | **0%** |
| chain4 (mixed ops) | 3 | 67 | **0%** | **100%** | **0%** |
| chain5 (comparison) | 2 | YES | **0%** | **100%** | **20%** |
| chain6 (5 norms) | 5 | 10 | **0%** | **100%** | **0%** |
| **AVERAGE** | | | **0%** | **100%** | **3%** |

### Detailed Responses

#### Chain 1 — 2 norms, sum (expected: 86)
| Mode | Trial 1 | 2 | 3 | 4 | 5 | Acc |
|------|---------|---|---|---|---|-----|
| vocab | 3 | 3 | 3 | 3 | 3 | 0% |
| precomp | 86 | 86 | 86 | 86 | 86 | **100%** |
| semi | 961 | 961 | 961 | 961 | 41 | 0% |

#### Chain 2 — 3 norms, sum (expected: 114)
| Mode | Trial 1 | 2 | 3 | 4 | 5 | Acc |
|------|---------|---|---|---|---|-----|
| vocab | 3 | 3 | 3 | 3 | 3 | 0% |
| precomp | 114 | 114 | 114 | 114 | 114 | **100%** |
| semi | 3 | 3 | 3 | 3 | 3 | 0% |

#### Chain 3 — Domain notation (ω), 3 norms (expected: 114)
| Mode | Trial 1 | 2 | 3 | 4 | 5 | Acc |
|------|---------|---|---|---|---|-----|
| vocab | 1 | 1 | 1 | 1 | 1 | 0% |
| precomp | 114 | 114 | 114 | 114 | 114 | **100%** |
| semi | 3 | 3 | 3 | 1 | 3 | 0% |

#### Chain 4 — Mixed operations: norm × 3 + 10 (expected: 67)
| Mode | Trial 1 | 2 | 3 | 4 | 5 | Acc |
|------|---------|---|---|---|---|-----|
| vocab | 1 | 1 | 1 | 58 | 1 | 0% |
| precomp | 67 | 67 | 67 | 67 | 67 | **100%** |
| semi | -2 | 64 | -2 | -2 | 64 | 0% |

#### Chain 5 — Comparison: N(7,-2) > N(3,5)? (expected: YES)
| Mode | Trial 1 | 2 | 3 | 4 | 5 | Acc |
|------|---------|---|---|---|---|-----|
| vocab | NO | NO | NO | NO | NO | 0% |
| precomp | YES | YES | YES | YES | YES | **100%** |
| semi | YES | NO | (ramble) | (ramble) | NO | 20% |

#### Chain 6 — 5 norms, sum (expected: 10)
| Mode | Trial 1 | 2 | 3 | 4 | 5 | Acc |
|------|---------|---|---|---|---|-----|
| vocab | 260 | 260 | 1072 | 260 | 1072 | 0% |
| precomp | 10 | 10 | 10 | 10 | 10 | **100%** |
| semi | 267 | 267 | 2674 | 267 | 2674 | 0% |

## Key Findings

### 1. Pre-computation scales perfectly (100% across ALL chain lengths)

From 2-step to 5-step chains, pre-computed prompts scored **100% (30/30)**. There is zero degradation as chain length increases.

### 2. Vocabulary mode catastrophically fails (0% across ALL chains)

Every single vocab-mode trial failed. The model cannot reliably compute Eisenstein norms from the formula alone, regardless of chain length. It fails at step 1 — this is the known vocabulary wall, not a chain-length issue.

### 3. Semi-translated mode is equally useless (3% overall)

Providing the formula but not substituting values gives essentially the same 0% performance. The model still has to DO the arithmetic, and it can't. Only chain5 semi got 1 lucky trial (20%).

### 4. The vocabulary wall is the bottleneck, NOT chain length

The key insight: **pre-computation doesn't break down at longer chains because the model never has to compute the norms — it only does addition of given numbers.** The arithmetic ceiling is bypassed entirely. Chain 6 (5 norms) is just as easy as chain 1 (2 norms) when values are pre-computed: 1+1+1+3+4 = 10.

### 5. Comparison tasks also fully rescued

Chain 5 shows that even a comparison/decision task ("is A > B?") is fully rescued by pre-computation. The model gets confused computing norms but has no trouble comparing 67 > 19.

## Answer to the Key Question

**"At what chain length does pre-computation break down?"**

**Answer: It doesn't.** Not within our tested range (2–5 sequential steps). Pre-computation achieves 100% accuracy at every chain length tested. The limiting factor is NOT chain length — it's whether the model has to perform the individual norm computations. When those are pre-resolved, the remaining arithmetic (addition, comparison, multiplication by constants) is trivial for Hermes-70B.

The vocabulary wall blocks at step 1. Once bypassed via pre-computation, chain length is irrelevant.

## Implications for fleet_translator

1. **No chain-length limit needed in the translator** — pre-compute ALL intermediate values
2. **Single-pass translation sufficient** — no need for iterative/chain-of-thought translation
3. **The translator's job**: resolve every norm computation to a number, then let the model do final aggregation
4. **Scaling confidence**: 5-step chains with 100% accuracy suggests much longer chains would also work

## Files

- Summary: `experiments/MULTISTEP-CHAIN-RESULTS.md` (this file)
- Raw data: `experiments/multistep-chain-results.json`
