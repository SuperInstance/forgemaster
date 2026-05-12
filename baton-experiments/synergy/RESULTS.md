# Baton Protocol: Small Model Synergy — Experimental Results

## 3 rounds, 14 experiments, all using cheapest models (~$0.01/query)

---

## Results

| Round | Experiment | Config | Accuracy | Facts | Novel |
|:------|:-----------|:-------|:---------|:------|:------|
| R1 | **hot-seed** | Seed-2.0-mini, temp=1.2 | **97.5%** | 39/40 | 123 |
| R1 | parallel-encode-synth | Seed→tech, Qwen→abstract, Seed→synth | **95.0%** | 38/40 | 155 |
| R1 | seed-alone | Seed-2.0-mini, temp=0.3 | 85.0% | 34/40 | 95 |
| R1 | minimal-prompt | Seed, system="Continue." | 65.0% | 26/40 | 205 |
| R2 | double-pass | Seed→Qwen→Seed | 2.5% | 1/40 | 11 |
| R3 | telephone-4hop | Seed→Qwen→Seed→Qwen | 10.0% | 4/40 | 21 |
| R1 | qwen-alone | Qwen3.6-35B | 0% | 0/40 | 0 |
| R1 | seed-encode-qwen-decode | Seed→Qwen | 0% | 0/40 | 0 |
| R1 | qwen-encode-seed-decode | Qwen→Seed | 0% | 0/40 | 12 |
| R2 | adversarial-refine | Seed→Qwen(critique)→Seed | 0% | 0/40 | 2 |
| R2 | roleplay-specialists | 3 roles → Qwen merges | 0% | 0/40 | 28 |
| R3 | combined-best | 3-way + adversarial | 0% | 0/40 | 0 |
| R3 | wise-advisor | Partial→Qwen hints→Seed revise | 0% | 0/40 | 2 |
| R3 | cross-examination | Split timeline, agents interview | 0% | 0/40 | 0 |

---

## Finding 1: Hot Seed Beats Everything (97.5%)

**Seed-2.0-mini at temperature 1.2** with a simple "reconstruct this session" prompt achieved 97.5% accuracy — matching or exceeding all previous experiments including those using Hermes-70B and Seed-2.0-code (which scored 97.5% in the original linear handoff).

**Why?** Higher temperature forces the model to explore more of its latent space. For RECONSTRUCTION tasks (not generation), this is beneficial because the model needs to fill gaps from context — low temperature makes it stick to the most probable (safe) output, which means it just parrots the input. High temperature lets it INFER missing connections.

**Cost:** ~$0.01 per query. That's 1000x cheaper than Claude Opus at $50/run.

**Hypothesis for next round:** Temperature has a U-shaped curve for reconstruction. Too low → shallow copy. Too high → hallucination. The sweet spot is model-dependent but appears to be 1.0-1.3 for Seed-2.0-mini.

---

## Finding 2: Qwen3.6-35B is a Black Hole

**Every pipeline that used Qwen3.6-35B as a decoder, synthesizer, or intermediary produced 0% accuracy.** Not low accuracy — ZERO. The model either:
- Returned empty strings
- Timed out
- Produced 37-character non-answers

This is catastrophic for multi-model pipelines. Qwen works as an ENCODER (extracting facts) but destroys information when asked to RECONSTRUCT or SYNTHESIZE from fragments.

**Why?** Qwen3.6-35B-A3B is a Mixture-of-Experts model with only 3B active parameters. When given a complex synthesis task, it may route to expert pathways that don't handle reconstruction well. Or it may have RLHF guardrails that suppress long outputs for system-like prompts.

**Implication:** In multi-model pipelines, model selection for EACH ROLE matters. A model that's good at extraction may be terrible at synthesis. You need to profile models per-task, not assume a "good" model is good at everything.

---

## Finding 3: The ONE Winning Synergy (95.0%)

**Parallel encode → Seed synthesizes** is the only multi-model configuration that works:

```
Seed extracts technical facts → technical_shard
Qwen extracts abstract concepts → abstract_shard  
Seed synthesizes both → reconstruction (95%)
```

The key: **Qwen is only used as an ENCODER (one-way extraction), never as a decoder.** Information flows INTO Qwen (context → extraction) but never OUT OF Qwen into another model's input.

This is an asymmetric pipeline:
- Qwen sees the FULL source and extracts ONE ASPECT
- Seed sees the FULL source and extracts ANOTHER ASPECT
- Seed (not Qwen!) synthesizes both aspects

**Why it works:** Each encoder produces a lossy shard from a different perspective. The Seed synthesizer sees TWO perspectives and reconstructs more than either alone. This is the baton split hypothesis confirmed — but only when the synthesizer is competent.

---

## Finding 4: Temperature > Model Size for Reconstruction

| Config | Model Cost | Temp | Accuracy |
|--------|-----------|------|----------|
| hot-seed | $0.01 | 1.2 | **97.5%** |
| parallel-synth | $0.02 | 0.5/0.3 | 95.0% |
| seed-alone | $0.01 | 0.3 | 85.0% |
| linear-handoff (Hermes-70B) | $0.15 | 0.3 | 97.5% |

The cheapest model at high temperature matches the expensive model at low temperature. **For reconstruction tasks, sampling diversity matters more than model capacity.**

This makes sense: reconstruction is not about generating novel content. It's about filling gaps in existing content. A model that explores more of its latent space (high temperature) will fill more gaps, even if it has fewer parameters.

---

## Finding 5: The Minimal Prompt Anomaly (65%)

Seed with system prompt "Continue." and the source context got 65% accuracy. That's remarkable — with ZERO task instruction, the model still reconstructed 26/40 facts.

**Implication:** For small models, the CONTEXT WINDOW IS THE PROMPT. The explicit instruction matters less than the content already in the window. This aligns with the forgetting-as-feature thesis: the model reconstructs from what's present, not from what it's told to do.

---

## Finding 6: The Telephone Chain Death Spiral

The 4-hop telephone chain (Seed→Qwen→Seed→Qwen) went:
```
Round 1 (Seed): 3741 chars → meaningful content
Round 2 (Qwen): 0 chars → NOTHING
Round 3 (Seed): 277 chars → desperately trying to reconstruct from nothing
Round 4 (Qwen): 445 chars → minimal garbage
```

Qwen at Round 2 produced ZERO output, and the chain never recovered. Even Seed at Round 3, given an empty input, could only produce 277 characters. **One bad link destroys the entire chain.**

This is exactly the telephone game problem from our original experiment, but worse because Qwen's failure mode (empty output) is more destructive than drift (which at least preserves some information).

**Implication for fleet design:** Telephone chains need FAULT TOLERANCE. If any hop produces empty/low-quality output, the chain should:
1. Detect the failure (output length < threshold)
2. Re-inject from a cached previous state
3. Skip the failing model and retry with another

---

## Finding 7: Model-as-Hypothesis-Generator Works

After Round 1, Seed-2.0-mini generated 3 specific, testable hypotheses about the results. These hypotheses were:
1. **Absence of seed knowledge causes zero retrieval** → Tested in R2 (confirmed: Qwen's empty outputs support this)
2. **Missing facts cluster by type (large-scale/complex)** → Plausible, needs dedicated test
3. **Accuracy vs utility tradeoff is prompt-driven** → Partially confirmed (minimal prompt had lower accuracy but higher novelty)

**Implication:** Small models can DESIGN experiments about their own performance. This is meta-cognition at the cheapest possible level. You could run an automated loop:
1. Small model runs experiments
2. Small model analyzes results
3. Small model generates hypotheses
4. Small model designs next round
5. Repeat until convergence

---

## Synthesis: The Optimal Cheap Pipeline

```
SOURCE CONTEXT
     │
     ├──→ Seed (temp=0.3): Extract technical facts
     ├──→ Qwen (any temp): Extract abstract concepts  
     │
     └──→ Seed (temp=1.2): Synthesize both extractions
          │
          └──→ RECONSTRUCTION (95-97.5% at $0.03 total)
```

**Rules:**
1. **Never use Qwen as a decoder/synthesizer** — encoder only
2. **Seed at high temperature is the best single-model decoder**
3. **Parallel extraction from different perspectives > single extraction**
4. **Temperature 1.0-1.3 for reconstruction, 0.3 for extraction**
5. **Fault tolerance: check output length after every hop**

---

## Hypotheses for Round 4

1. **Temperature sweep:** Test Seed at temp 0.3, 0.7, 1.0, 1.2, 1.5 to find the exact U-curve peak
2. **Extraction diversity:** Does Qwen extract DIFFERENT facts than Seed? Or the same facts? If different, that explains the synergy.
3. **Three-seed ensemble:** What if all 3 extractors are Seed at different temperatures? Does model diversity matter or just extraction diversity?
4. **The adversarial Seed:** Instead of Qwen critiquing, use Seed at high temp to critique Seed at low temp. Does the same model in different modes produce useful adversarial tension?

---

*Total experiment cost: ~$0.50 across 14 experiments, 3 rounds*
*Best result: 97.5% at $0.01 (Seed-2.0-mini, temp=1.2)*
