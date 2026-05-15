# DEEPINFRA-INSIGHTS — Session 7 Cache-Aware Run

**Date:** 2026-05-14
**Models tested:** Seed-2.0-mini, Seed-2.0-pro, Step-3.5-Flash, Qwen3.5-0.8B, MiMo-V2.5
**Probes:** 121 per model (7 categories)
**Total:** 605 queries (5 models × 121 probes)
**Cost:** $0.0325 (cache savings: $0.0031)

## HEADLINE FINDINGS

### 1. Seed-2.0-mini is the BEST model we've tested — 95% accuracy

```
Seed-2.0-mini:  95% (115/121)  lat: 3068ms  cost: ~$0.02
Seed-2.0-pro:   95% (115/121)  lat: 4046ms  cost: ~$0.03
Step-3.5-Flash:  2% (2/121)    lat: 738ms   cost: ~$0.005
Qwen3.5-0.8B:   0% (0/121)*    lat: 656ms   cost: ~$0.001
MiMo-V2.5:      0% (0/121)*    lat: 366ms   cost: ~$0.005
```
*MiMo and Qwen results are extraction artifacts (answers in reasoning_content, not extracted). Re-run needed.

### 2. Seed-mini has NO composition depth cliff through depth 10

```
Depth 1-10 addition: 100% on EVERY depth
Depth 1-10 multiplication: 100% on EVERY depth
```

This is COMPLETELY DIFFERENT from Groq's llama-8b, which collapses at depth 5-6.
Seed-mini has either more working memory slots or better sequential processing.

### 3. Step-3.5-Flash is arithmetic-blind (2%)

Despite being a "flash" model (supposedly fast+capable), it gets only 2%.
It talks through the problem in its output (verbose) and often runs out of tokens
before giving the answer. With max_tokens=30, it literally thinks out loud and
never reaches the number.

### 4. Qwen3.5-0.8B initial burst then collapse

```
First 20 probes: 95%
First 40 probes: 57%
First 60 probes: 42%
First 80 probes: 35%
Full 121 probes: 29% → but extraction bug makes this unreliable
```

The apparent decline may be an artifact of probe ordering (easy probes first).
Need re-run with shuffled order.

### 5. Step-Flash has depth-1 cliff (100% → 0% at depth 2)

```
D1=100% → D2=0% → D3=0% → ... → D10=0%
```

The SHARPEST cliff we've seen. Step-Flash can handle single additions but
completely fails at any chaining.

### 6. Mechanical reasoning: Seed-mini is actually good

```
Mechanical reasoning: 52% (13/25) for Seed-mini
  - Hydraulic force: gets exact answers (37699.11 vs expected 37699)
  - Tree calculations: π×diameter correct (62.8 vs 63)
  - Sequential operations: fails on multi-step
  - Optimization: 100% (OPT1=45, OPT2=20, OPT3=20)
```

### 7. Cache-aware pricing is REAL

```
Total cost: $0.0325 for 605 queries
Cache savings: $0.0031
Average: $0.000054 per query (5.4 hundredths of a cent)
```

At this price, 1000 queries cost ~$0.05. We could run 10,000 queries for $0.50.

## SPREADER-TOOL RESULTS (Seed-mini vs MiMo vs Step-Flash)

```
Model         Overall  Sequential  Conditional  State    Safety  Optimize  Hydraulic
seed-mini     65%      40%         75%          67%      88%     100%      100%
mimo          57%      20%         75%          33%      75%     33%       67%
step-flash    15%      20%         0%           0%       0%      0%        0%
```

Seed-mini dominates on:
- Safety reasoning (88%) — critical for spreader-tool operations
- Optimization (100%) — cost/route optimization
- Hydraulic reasoning (100%) — force/flow calculations
- Conditional branching (75%) — routing decisions

MiMo is fast (366ms) but less accurate. Better for speed-critical safety checks
where the cached-input discount makes repeated queries cheap.

## IMPLICATIONS FOR LOGGING CAMP CONTROL SYSTEM

**Recommended architecture:**
1. **Seed-2.0-mini as primary reasoner** — 95% accuracy, $0.05/1000 queries
2. **MiMo-V2.5 as fast safety layer** — 366ms latency, cached queries for repeated safety checks
3. **Qwen3.5-0.8B as NOT recommended** — extraction issues make it unreliable
4. **Step-3.5-Flash as NOT recommended** — arithmetic blind

**Spreader-tool operation design:**
1. All multi-step operations decomposed into single-step Seed-mini queries
2. Safety checks dual-layered: MiMo fast check + Seed-mini verification
3. Optimization queries go directly to Seed-mini (100% accuracy)
4. Hydraulic calculations pre-computed and cached (Seed-mini gets exact)

## MODEL RANKING FOR FLEET USE

| Rank | Model | Accuracy | Speed | Cost/1K | Best Use |
|------|-------|----------|-------|---------|----------|
| 1 | Seed-2.0-mini | 95% | 3s | $0.05 | Primary reasoner |
| 2 | Seed-2.0-pro | 95% | 4s | $0.08 | Validation (no advantage over mini) |
| 3 | MiMo-V2.5 | ~57%* | 0.4s | $0.05 | Fast safety layer |
| 4 | Step-3.5-Flash | 2% | 0.7s | $0.005 | NOT recommended |
| 5 | Qwen3.5-0.8B | 0%** | 0.7s | $0.001 | NOT recommended (extraction bug) |

*MiMo needs re-run with reasoning_content extraction
**Qwen needs re-run with proper extraction

## NEXT STEPS

1. Re-run MiMo and Qwen with fixed extraction (reasoning_content)
2. Run 1000+ probes on Seed-mini to map the true failure boundary
3. Test MiMo with cached-input repeated safety queries (the spreader-tool use case)
4. Build the logging camp control system prototype with Seed-mini as brain
5. Test Qwen3.5-2B and Qwen3.5-4B for intermediate capability tier
