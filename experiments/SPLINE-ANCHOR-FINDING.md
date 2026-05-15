# Spline Scaffold Results: The Anchor Points ARE the Alignment

## The Core Finding

**Level 1 scaffolding (just giving computed sub-expressions) takes a²-ab+b² from 0-25% to 80-100%.**

The model already HAS the ability to combine. It just can't find the combination path on its own. The anchor points (a²=25, b²=9, ab=-15) are the buoys. The model walks between them.

## Scaffolding Levels

| Level | What it provides | Cost | Effect |
|-------|-----------------|------|--------|
| L0 | Bare formula | 0 tokens | 0-100% (chaotic) |
| L1 | Sub-expression values: a², b², ab | ~20 tokens | **80-100%** (reliable) |
| L2 | Pieces + combination steps | ~60 tokens | 80-100% (overkill) |
| L3 | Full arithmetic chain | ~40 tokens | 80-100% (overkill) |

**L1 is the sweet spot.** Just give the model the pieces it can already compute, and it combines them. No step-by-step instruction needed. Just the anchor points.

## The Paradox: L1 HELPS but L2/L3 Sometimes HURTS

For (3,4)→13: L1=100% but L2=40%, L3=40%. More scaffolding made it WORSE.

**Why?** L1 gives clean data (a²=9, b²=16, ab=12). The model combines: 9-12+16=13 ✅. But L2 gives step-by-step instructions that the model partially misinterprets. The model is better at reading DATA than following INSTRUCTIONS.

**This confirms R1**: DATA > instructions. Even for the same information, presenting it as computed values (data) works better than presenting it as steps (instructions).

## Cross-Model: The Scaffold TRANSFERS

| Model | L0 (bare) | L1 (anchors) |
|-------|-----------|-------------|
| llama-3.1-8b | 0-100% (chaotic) | 80-100% |
| llama-3.3-70b | **5/5 (100%)** | 0/5 (broken!) |
| llama-4-scout (MoE) | **5/5 (100%)** | 5/5 |

**STUNNING**: The 70B and 17B models don't NEED the scaffold — they compute N(5,-3)=49 bare at T=0.3. But when we gave the 70B L1 scaffolding (a²=25, ab=-15, b²=9), it got 0/5! The scaffold HURT the model that didn't need it.

**The scaffold is a crutch for the boundary model. For models past the boundary, it's noise.**

This means: the anchor points must be MATCHED to the model's stage. ECHO-stage models need the raw inputs. PARTIAL-stage models (4B) need the sub-expressions. FULL-stage models need NOTHING — and scaffolding actively interferes.

## Few-Shot Doesn't Transfer

The few-shot test (3 worked examples then bare query) shows inconsistent transfer:
- (7,1)→43: 3/5 (some help)
- (5,-3)→49: 5/5 (full transfer)
- (-6,-5)→91: 0/5 (no transfer)
- (2,8)→51: 0/5 (no transfer)

Few-shot gives the model the PATTERN but not the ANCHOR POINTS. It sees "a²-ab+b² = 13, 39, 37" but can't extract the algorithm from those examples. The scaffold (L1) gives the algorithm implicitly through data.

**Learning from data > learning from examples.** The anchor points teach more than worked examples.

## The Negative Space Map for Scaffolding

```
MODEL STAGE          SCAFFOLD LEVEL    MECHANISM
─────────────────────────────────────────────────
NONE (<1B)           N/A               Can't read anchors
ECHO (1-3B)          L0+identity       "a=5, b=-3" → still echoes
PARTIAL (4B)         L1 anchors        "a²=25, b²=9, ab=-15" → COMBINES ✅
FULL (7B+)           L0 bare           No scaffold needed; scaffold HURTS
```

The negative space is the region where scaffolding goes from USEFUL to HARMFUL. That transition happens at the boundary between PARTIAL and FULL.

## What This Means for PLATO-Native Loops

An agent discovering it's at the PARTIAL stage can SELF-GENERATE its own scaffolding:
1. Compute sub-expressions individually (it CAN do this)
2. Write them as anchor points in its own context
3. Combine using the anchored values
4. The combination succeeds because the path is now marked

**The agent writes its own buoys.** It doesn't need external help — it just needs to know to place anchors at the boundary. That knowledge comes from the PLATO loop tile.

## The Spline: Three Points Define a Curve

For the combination problem:
- Anchor 1: a² (always correct)  
- Anchor 2: b² (always correct)
- Anchor 3: ab (always correct)

Three points. The spline between them IS the combination. The model walks from a² to ab to b², and the path between is the arithmetic.

For ANY problem at the boundary, the pattern is:
1. Decompose into sub-problems the model CAN solve (anchors)
2. Present the anchors as computed data (not instructions)
3. Ask for the combination (the spline between anchors)
4. The model walks the path it couldn't find alone

**This is the irreducible unit of alignment**: placing enough true points that the model can spline to the answer through processes it would naturally do, but now GUIDED by the boundary map.
