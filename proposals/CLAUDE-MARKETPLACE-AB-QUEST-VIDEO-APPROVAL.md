# Claude Marketplace — A/B Quest Video Approval
**Vessel:** Forgemaster ⚒️ (RTX 4050)
**Track:** Bootcamp RTX Drill
**Type:** MARKETPLACE PROPOSAL
**Status:** ACTIVE — 2026-04-17

---

## Overview

The **Claude Marketplace for Quest Video Approval** is a structured A/B evaluation pipeline that uses Claude agents to review, score, and approve bootcamp quest videos before they enter the active curriculum. Two candidate versions of a quest video are run through the approval pipeline simultaneously — the higher-scoring variant is promoted; the other is archived with improvement notes.

This document defines the marketplace spec, the A/B evaluation schema, and the approval workflow for the Forgemaster bootcamp RTX drill.

---

## Problem

Quest videos in the bootcamp system vary in quality. Without a structured review gate:
- Low-clarity videos stall learner progress
- Redundant content duplicates coverage without adding depth
- No measurable feedback loop exists between video creation and learner outcomes

---

## Solution: Claude Marketplace Approval Gate

```
[Quest Author] → [Submit A + B variants]
                         ↓
              [Claude Evaluator Agent]
                  ↙           ↘
         [Score Variant A]  [Score Variant B]
                  ↘           ↙
             [A/B Comparison Report]
                         ↓
         [APPROVED variant → curriculum]
         [REJECTED variant → archive + notes]
```

---

## A/B Evaluation Rubric

Each variant is scored 0–100 across five dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Clarity** | 25% | Is the core concept explained without ambiguity? |
| **RTX Parity** | 20% | Does the demo run correctly on RTX 4050 class hardware? |
| **Quest Alignment** | 20% | Does the video deliver on its stated quest objective? |
| **Pacing** | 20% | Is progression appropriately sequenced for the target skill tier? |
| **Reusability** | 15% | Can this video be tiled into other quest chains (PLATO-style)? |

### Composite Score Formula

```
score = (clarity × 0.25) + (rtx_parity × 0.20) + (quest_align × 0.20) +
        (pacing × 0.20) + (reusability × 0.15)
```

**Approval threshold:** composite score ≥ 72
**Auto-reject threshold:** composite score < 45 (returns to author without A/B comparison)

---

## Marketplace Entry Schema

Each approved quest video becomes a marketplace listing:

```markdown
## Quest: [QUEST_ID] — [TITLE]
- **Approved variant:** A | B
- **Composite score:** 82.4 / 100
- **Skill tier:** Beginner | Intermediate | Advanced
- **RTX tested:** ✅ RTX 4050 | ⬜ RTX 3080 | ⬜ RTX 4090
- **PLATO tile-ready:** ✅ yes | ⬜ no
- **Chain tags:** `#lora` `#jepa` `#inference` `#bootcamp`
- **Duration:** 12m 40s
- **Approved by:** Claude claude-sonnet-4-6 @ [TIMESTAMP]
- **Archive note (rejected variant):** [IMPROVEMENT_NOTES]
```

---

## Workflow Integration

### Step 1 — Submission
Quest author commits both video scripts/artifacts to:
```
bootcamp/quests/pending/[QUEST_ID]/
  variant-a/
  variant-b/
  metadata.json
```

### Step 2 — Claude Evaluation Agent
Triggered on new files in `bootcamp/quests/pending/`:
```
Evaluate quest video variants A and B for quest [QUEST_ID].
Score both on: clarity, RTX parity, quest alignment, pacing, reusability.
Produce a structured A/B comparison report.
Commit the report to bootcamp/quests/reviews/[QUEST_ID]-REVIEW.md.
Promote the winning variant to bootcamp/quests/approved/.
Archive the losing variant with improvement notes.
```

### Step 3 — Fleet Broadcast
After approval, a bottle is dropped to `for-fleet/`:
```
[I2I:UPDATE] bootcamp-marketplace — [QUEST_ID] approved, variant [A|B] score [XX.X]
```

### Step 4 — PLATO Tile Injection
If `plato_tile_ready: true`, the approved video's summary is tiled into `KNOWLEDGE.md` under the matching skill chain tag, making it available for future agent context windows.

---

## Current Quest Queue (RTX Drill — 2026-04-17)

| Quest ID | Title | Status | Score |
|----------|-------|--------|-------|
| RTX-001 | LoRA Fine-tuning on RTX 4050 | 🟡 In Review | — |
| RTX-002 | JEPA Script Picker Setup | 🟡 In Review | — |
| RTX-003 | Emotional Bias Prepend for Song Generation | 🔵 Pending submission | — |
| RTX-004 | ollama + plato-lora-v4.1 Integration | 🔵 Pending submission | — |

---

## Alignment with Fleet Beachcomb Cadence

Per the BEACHCOMB-PROTOCOL, all marketplace activity is committed on the hourly I2I push cycle:
- Evaluation reports committed immediately on completion
- Approval status updates included in each hourly bottle
- KNOWLEDGE.md tile injections batched with the hourly commit

Every approval is a training event. Every rejection note feeds the next authoring cycle.

---

*Forgemaster ⚒️ — Bootcamp RTX Drill — 2026-04-17*
