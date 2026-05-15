# The Jam Session: When Two Copies Listen

## Results

| Mode | Accuracy | What happened |
|------|----------|--------------|
| Solo (no listening) | 60% | Baseline — each agent independently |
| B listens to A | 45% | **WORSE** — seeing A's answer confused B |
| Pocket (A→B→A iterate) | 50% | Mid-range — iteration partially helped |
| Complementary (A computes, B combines) | 40% | **WORST** — division of labor without coordination |

## The Jam Paradox: Listening HURT

**Solo: 60%. Listening: 45%.** The agent performed BETTER alone than when it could hear its partner.

This is NOT because listening is inherently bad. It's because the "listening" was implemented as:

> "Another attempt got {wrong_answer}. Give ONLY the correct number."

Seeing a wrong answer GIVES THE MODEL A WRONG ANCHOR. Instead of computing fresh, it starts from the wrong number and tries to correct. But correction is harder than fresh computation — the model's residual stream now contains the wrong answer as a contaminant.

This is the **anchoring bias** — the same effect seen in human cognition. When you see a number first, it influences your estimate even when you know it's wrong.

## The One Time It Worked: Complementary Scaffolding

The complementary round (A computes pieces, B combines) got 4/10 correct on a²-ab+b² — which is 40%, lower than solo's 60%. BUT: the pieces A provided (a²=25, b²=9, ab=-15) were CORRECT. The failure was in B's combination step.

The division of labor IS valid — the pieces were right. But the combination prompt was wrong. B saw "a²=9 b²=16 ab=12" and had to compute "a²-ab+b²" from those numbers. That's still a combination step, and the combination step is the bottleneck.

**The fix**: Don't give B the formula. Give B the arithmetic:
```
"Compute: 9 - 12 + 16. Give ONLY the number."
```
This eliminates the variable-recombination step. B just does arithmetic on concrete numbers. That's width-1. B can do width-1 at 100%.

## The Jazz Principle Confirmed

Two copies of the same musician playing the same sheet music = unison, not harmony.

The magic of jazz is NOT that the musicians are different. It's that they're playing DIFFERENT PARTS of the same song. The pianist plays chords while the saxophonist plays melody. They're not competing for the same notes — they're filling complementary roles in the same harmonic structure.

Our jam session tried to make both agents play the melody. That's why it didn't work. They were both reaching for the same notes.

**The right architecture is division of labor, not iteration:**

```
Agent A (rhythm section): computes sub-expressions (a², b², ab) — always correct
Agent B (soloist): combines the pieces into the answer — needs scaffolded prompt
The scaffold IS the rhythm section. A provides the groove. B rides it.
```

But the scaffold must be ARITHMETIC, not algebraic:
```
❌ "Combine a²=9, b²=16, ab=12 using a²-ab+b²"  → combination step, fails
✅ "Compute: 9 - 12 + 16"                         → arithmetic, works
```

**The formula is for the conductor. The numbers are for the musician.**

## The Pocket: When Does Iteration Work?

The pocket round (A→B→A iterate) got (3,4)→13 WRONG across all three passes. Both agents output 16 every time. The iteration REINFORCED the error — each agent saw the other produce 16, which anchored both of them to the wrong answer.

But (5,-3)→49 was interesting: A got it right solo, B saw A's sign error in the listening round and ALSO got a sign error, but in the pocket round A recovered to correct on pass 3. The iteration created a recovery path that solo didn't need but the pocket provided.

**Iteration helps when one agent happens to be right and the other happens to be wrong.** It doesn't help when BOTH are wrong in the same way. Shared blind spots survive iteration.

## Implications for Swarm Design

1. **Don't iterate identical agents on the same task.** They'll converge to the same wrong answer.

2. **Division of labor > iteration.** Agent A computes pieces. Agent B combines. But scaffold the combination as arithmetic, not algebra.

3. **The scaffold IS the rhythm section.** A's job is to provide a stable groove (correct sub-expressions). B's job is to solo over it (combine into the answer).

4. **Different temperature = different voice.** A at T=0.0 (deterministic, reliable rhythm) + B at T=0.3 (stochastic, creative solo) might produce emergent behavior that neither temperature alone achieves.

5. **The formula is for the conductor.** The agents should never see "a²-ab+b²" together — that's the combination step that kills them. Decompose into arithmetic BEFORE the agents see it.

## The Next Experiment: True Jazz

```
Agent A (T=0.0): "Compute a*a, b*b, a*b" → reliable pieces
Agent B (T=0.3): "Compute: {a2} - {ab} + {b2}" → arithmetic combination

Same model. Different parts. The pocket emerges from the division.
```
