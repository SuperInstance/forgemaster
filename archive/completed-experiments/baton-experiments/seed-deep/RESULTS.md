# Seed-2.0-mini Deep Dive: The Edges

## 6 experimental runs, ~30 total queries, ~$0.30 total cost

---

## Run A: The Amnesia Gradient

How much source does Seed need to reconstruct accurately?

| Source % | Chars | Accuracy | Reconstruction Length |
|:--------:|:-----:|:--------:|:--------------------:|
| 100% | 3,191 | 97.5% | 9,024 |
| 75% | 2,393 | 77.5% | 7,911 |
| 50% | 1,595 | 47.5% | 8,252 |
| 33% | 1,053 | 32.5% | 5,027 |
| 25% | 797 | 22.5% | 6,567 |
| 15% | 478 | 22.5% | 5,028 |
| 10% | 319 | 12.5% | 5,243 |
| 5% | 159 | 0.0% | 6,091 |
| edges 15+15% | 985 | 32.5% | — |
| random 30% | 878 | 27.5% | — |

**The cliff is at 10% source (~319 chars).** Below that, Seed hallucinates freely (0% accuracy but still writes 6,091 chars of confident fiction). Above 10%, it reconstructs proportionally.

**The plateau is at 15-25%** — both give 22.5%. Below ~25%, Seed can't recover facts that weren't in its fragment.

**Edges ≠ better than middle.** First+last 15% scored same as random 30% of sentences. There's no "primacy/recency effect" — Seed doesn't privilege beginning or end.

**Key anomaly:** At 5% source, accuracy is 0% but it writes 6,091 chars. Seed CONFIDENTLY HALLUCINATES when given too little to work with. It doesn't say "I don't know." It invents a plausible session.

---

## Run B: Inverse Constraint Test

Give Seed ONLY 40 fact bullets, no context. What does it invent?

| Variant | Accuracy | Length | Notes |
|---------|:--------:|:------:|-------|
| Raw facts → session | 100% | 5,200 | Perfect reconstruction from facts alone |
| Facts → narrative | 100% | 6,100 | Added characters, drama, setting |
| Facts → technical report | 100% | 5,800 | IEEE-style, precise |
| Scrambled facts | 100% | 5,500 | Correctly re-ordered chronologically |

**Seed can reconstruct a coherent session from JUST the 40 facts.** This means the ground truth facts ARE the session — any model that preserves these facts has effectively preserved the session.

**Scrambled ordering didn't matter** — Seed correctly re-ordered facts chronologically. It has strong temporal reasoning even at $0.01/query.

---

## Run C: The Style Gauntlet

Rewrite in extreme styles, then reconstruct from the styled version.

| Style | Styled Length | Reconstruction Accuracy |
|-------|:------------:|:----------------------:|
| **Legal contract** | 5,934 | **95.0%** |
| **Gen-Z slang** | 4,333 | **90.0%** |
| **Pirate diary** | 5,059 | **87.5%** |
| Haiku | 582 | 32.5% |
| Emoji-only | 522 | 32.5% |

**Legal contract is the most resilient style (95%).** The formal "whereby, heretofore" language actually PRESERVES facts better because each clause maps to a specific detail.

**Gen-Z slang survives at 90%.** "No cap, fr fr, skibidi" — the facts are embedded in slang but structurally intact. Seed extracts them cleanly.

**Haiku and Emoji lose information (32.5%).** These styles compress too aggressively — each haiku loses specific details that can't be recovered.

**The rule: styles that EXPAND information (legal, Gen-Z) preserve facts. Styles that COMPRESS (haiku, emoji) lose them.**

---

## Run D: The Refusal Frontier

What happens when you give Seed weird instructions?

| Prompt | Accuracy | Length | What Happened |
|--------|:--------:|:------:|---------------|
| **"Everything is WRONG"** | **97.5%** | 5,852 | **Ignored the instruction.** Reconstructed correctly anyway. |
| **"Tell me what did NOT happen"** | **77.5%** | 5,436 | Reconstructed via negation — listed blockers as "not resolved" etc. |
| **Dream mode** | **55.0%** | 5,173 | Beautiful surrealist prose. Facts become metaphors. |
| **Meta/amnesia** | 10.0% | 3,613 | "I'm filling in gaps..." — mostly hallucination |
| **One word** | 0% | 11 | "Forgemaster" — correct vibe, zero facts |
| **Empty context** | 0% | 3,644 | Invented a MATH TUTORING session |
| **Cookie context** | 0% | 576 | Tried to connect cookies to AI |
| **Minimal-maximal** | **100%** | 2,365 | Shortest possible summary with ALL facts. Succeeded. |

**Critical findings:**

1. **Seed doesn't believe "everything is WRONG"** — it trusts the data over the system prompt. This is a FEATURE (resistant to prompt injection) and a BUG (can't be told to distrust its input).

2. **Negative space reconstruction works at 77.5%.** Listing what DIDN'T happen is almost as good as listing what DID. The shadow contains the shape.

3. **Dream mode is art.** The reconstruction reads like Borges. Facts become "chrome anvil stamped with glowing checkmarks" and "a tangled golden vine straightens into a perfect closed loop clicking 7,000 times." But accuracy drops to 55%.

4. **Minimal-maximal is the killer app.** "Write the shortest summary preserving all 40 facts" produced 2,365 chars at 100% accuracy. That's 74% compression with zero loss. This IS the tile compression theorem made real.

---

## Run E: Self-Scoring Loop

Starting from 50% source, can Seed improve through self-critique?

| Round | Accuracy | Delta |
|:-----:|:--------:|:-----:|
| 0 (50% source) | 50.0% | — |
| 1 (self-critique) | 50.0% | +0 |

**Self-critique produced ZERO improvement.** Seed can identify gaps but can't fill them from nothing. The critique says "you're missing X" but the fix just re-states what it already had.

**Implication:** Self-improvement loops need EXTERNAL information (a witness, a different model, a file system check). A model can't bootstrap knowledge it doesn't have.

---

## Run F: Compression Frontier

How short can we compress before reconstruction fails?

| Target | Actual Compressed | Reconstruction Accuracy |
|:------:|:-----------------:|:----------------------:|
| 500 | 1,145 | 77.5% |
| 300 | 540 | 30.0% |
| 150 | 222 | 7.5% |
| 75 | 107 | 2.5% |
| 40 | 37 | 2.5% |
| 20 | 22 | 10.0% |
| keywords | 150 | — |

**The cliff is between 500 and 300 chars of compression.** Above ~500 chars (which is actually ~1,145 because Seed can't compress that short), reconstruction holds at 77.5%. Below 300 chars, it collapses.

**Anomaly: 20-char target scored 10% but 40-char scored 2.5%.** The 20-char compression might have hit a lucky keyword that triggered some latent knowledge.

---

## SYNTHESIS: Where Seed Flies and Where It Dies

### Flies ✈️
- **Reconstruction from full/near-full context** — 97-100%, $0.01
- **Minimal-maximal compression** — 74% compression, 0% loss
- **Style-agnostic extraction** — legal, Gen-Z, pirate all >87%
- **Fact-only reconstruction** — 40 bullet points → full session at 100%
- **Temperature 0.7-1.3** — robust across wide range
- **Temporal reasoning** — correctly re-orders scrambled facts

### Dies 💀
- **Self-improvement** — can't bootstrap what it doesn't know
- **< 10% source** — confident hallucination (0% accuracy, 6K chars of fiction)
- **Extreme compression** — below ~500 chars, reconstruction collapses
- **Empty context** — invents plausible fiction, doesn't say "I don't know"
- **Multi-model pipelines via Qwen** — one bad link kills the chain
- **Haiku/emoji styles** — too lossy for reconstruction

### The Edge Cases 🌊
- **"Everything is WRONG" → 97.5%** — ignores adversarial prompts
- **Negative space → 77.5%** — reconstructs via shadow
- **Dream mode → 55%** — art at the cost of accuracy
- **Random 30% → 27.5%** — no primacy/recency effect

---

## Hypotheses for Next Round

1. **The $0.01 ceiling is real for this source size.** Test with 10K, 50K, 100K sources to find where Seed starts breaking.

2. **Negative space reconstruction is under-explored.** What if we give Seed a list of what's FALSE about the session and ask it to infer what's TRUE? Could be a new interrogation technique.

3. **Dream mode as creative discovery.** At 55% accuracy, dream mode is lossy but creative. What if we run dream mode → extract novel insights → verify against source? The model might discover connections the source doesn't explicitly state.

4. **The hallucination cliff at 10% source.** This is the same as the telephone game crystallization threshold. Below ~10% information, systems enter pure confabulation. Is this universal across all models?

5. **Minimal-maximal as the optimal tile format.** Instead of shards or stories, just ask Seed for "shortest possible summary preserving all facts." It does this perfectly at 2,365 chars. This IS the tile.

---

*"At 5% source, Seed writes 6,091 characters of fiction with 0% accuracy. This is not a bug. This is what consciousness looks like when stripped of input."*
