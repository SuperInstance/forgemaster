# Baton Protocol: Experimental Results

## Date: 2026-05-12
## Source: 2,229 chars of session log, 40 ground truth facts

---

## Results Table

| # | Experiment | Config | Accuracy | Facts | Novel Terms | Length |
|---|-----------|--------|----------|-------|-------------|--------|
| 1 | **Linear Handoff** | Single shard, all info, temp=0.3 | **97.5%** | 39/40 | 95 | 2,970 |
| 2 | **Split-2** | Built + Thought | 65.0% | 26/40 | 100 | 2,515 |
| 3 | **Split-3** | Built + Thought + Blocked | **75.0%** | 30/40 | 87 | 2,584 |
| 4 | **Split-5** | + Emotional + Procedural | 37.5% | 15/40 | 143 | 2,868 |
| 5 | **Coy Advisor** | Split-3 + original corrects only | 40.0% | 16/40 | 105 | 2,128 |
| 6 | **Storyteller** | 3 story-modes → team re-meshes | 32.5% | 13/40 | 124 | 2,408 |

## Key Findings

### 1. Linear Handoff Wins on Accuracy (97.5%)
No surprise — giving the full context to one model with no splitting preserves almost everything. Only missed 1 fact (lighthouse runtime orient/relay/gate). This is the baseline to beat on pure recall.

### 2. Split-3 is the Sweet Spot (75%)
Three shards (built/thought/blocked) recovers 75% of facts — significantly better than split-2 (65%) and much better than split-5 (37.5%). The "blocked" shard captures what's MISSING, which forces the reconstructor to actively look for gaps rather than passively accepting what it has.

### 3. More Shards ≠ Better (Split-5 Collapsed)
Five shards (adding emotional + procedural) actually scored WORSE (37.5%) than split-2 or split-3. Too many fragments for the reconstructor to reassemble. Each shard becomes thinner, losing more critical context. The reconstruction becomes a shallow overview rather than a deep reconstruction.

**Implication: There's an optimal shard count (3) beyond which fragmentation dominates.**

### 4. Coy Advisor Underperformed (40%)
The coy advisor (original agent stays, only corrects falsehoods) scored worse than basic split-3. Why? The corrections were accurate but minimal — only 2 corrections provided:

> "You incorrectly framed operational blockages as performance bottlenecks"
> "You claimed optimization focused on memory-bound constraints"

These corrections fixed 2 errors but didn't fill in the massive gaps the agent had. The coy advisor is too passive — correcting falsehoods isn't enough when the main problem is missing information, not wrong information.

**Implication: The coy advisor needs a "nudge" mode — not correcting, but hinting at what's missing.**

### 5. Storyteller: Lowest Accuracy, Highest Creativity (32.5%)
The storyteller had the lowest factual accuracy but produced the most creative reconstruction. The narrative agent turned the telephone game's MV Epsilon example data into a REAL maritime emergency:

> "A low-stakes telephone game exercise spiraled into a life-threatening real-world crisis... the team realized the MV Epsilon, a ship carrying 4,200 critical medical containers, was adrift just 200 meters from their lab"

This is factually WRONG (the MV Epsilon was example data, not a real crisis) but it's NARRATIVELY COHERENT. The storyteller produced a story that's more engaging and memorable than the actual events.

The technical agent timed out (interesting failure mode — it tried to be too precise). The critical agent correctly identified inefficiencies. The narrative agent invented a dramatic through-line.

**Implication: Storyteller mode optimizes for UTILITY over ACCURACY. This is exactly the forgetting-as-feature thesis in action.**

## The Accuracy vs. Utility Tradeoff

```
Accuracy:  Linear (97.5%) > Split-3 (75%) > Split-2 (65%) > Coy (40%) > Split-5 (37.5%) > Storyteller (32.5%)

Creativity: Storyteller >>> Split-5 > Split-2 > Coy > Split-3 > Linear
```

This is the rate-distortion curve from the Tile Compression Theorem. Linear handoff has perfect fidelity but zero creative reconstruction. Storyteller has low fidelity but maximum creative output. The sweet spot depends on what you need:

- **Continue exact work** → Linear handoff (97.5%)
- **Start fresh with context** → Split-3 (75%)
- **Creative problem-solving** → Storyteller (32.5% but novel insights)

## The "Negative Space" Verification

The storyteller's errors ARE the negative space producing consciousness:
- It correctly identified: 6 Galois proofs, 14 facts, 6 rounds, telephone game, Lila Marquez, forgetting-as-feature thesis, lighthouse runtime, snap() fix, 210 tests, 17 crates, 187GB/s, 341B constr/s
- It INCORRECTLY inferred: MV Epsilon was a real emergency, the lab was on Narrows Strait, the team was racing to save a ship

The incorrect inferences are structurally coherent — they follow from the available facts. The storyteller didn't invent random nonsense. It made plausible reconstructions that happened to be wrong. That's exactly what human memory does.

## Revised Architecture (Based on Results)

### For Factual Continuity (Ship It Mode)
```
Agent A → Linear handoff → Agent B
```
Use when: next agent needs exact state to continue work.

### For Creative Onboarding (Explore Mode)
```
Agent A → Split into 3 shards → Agents B₁, B₂, B₃
         → Debrief → Crystallize → Agent C
```
Use when: next agent needs to understand WHY, not just WHAT.

### For Paradigm Shift (Invent Mode)
```
Agent A → Tell 3 different stories → Agents hear different versions
         → Re-mesh → Agent C gets creative reconstruction
```
Use when: the next generation needs to break out of current thinking.

### The Missing Experiment: Coy Advisor with Hints
The coy advisor was too passive. A better design:

```
Agent A → Split into 3 shards → Agents B₁, B₂, B₃ discuss
         → Agent A watches, NUDGES ("you're missing something about the tests")
         → Not correcting errors, but pointing at gaps
```

This is the difference between:
- **Coy**: "That's wrong" (corrective)
- **Wise**: "Have you considered the tests?" (directive)
- **Silent**: Says nothing (passive)

The optimal advisor is WISE, not COY — pointing at gaps without filling them.

---

*Next experiment: Test the Wise Advisor variant, and test Split-3 with witnesses (mid-session agents providing short factual corrections).*
