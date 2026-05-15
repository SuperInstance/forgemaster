# Cocapn Fleet Operations Handbook
**Version 4.2 | Classification: Internal**

---

## 1. Quick Reference: Routing Table

| Task | Route To | Notes |
|------|----------|-------|
| Code generation/debugging | z.ai (paid) | Best syntax accuracy |
| Document summarization | z.ai (paid) | Handles long context |
| Arithmetic / computation | DeepInfra | Cheaper, sufficient |
| Translation (EN→JA) | Hermes via DeepInfra | See §5 first |
| Simple classification | Local / offline | Reduce cost |
| Real-time chat | Local | Latency-sensitive |
| Batch processing | DeepInfra | Cost-effective |

**Default fallback:** Local model. Always have it loaded.

---

## 2. The Vocabulary Wall

**What it is:** The model suddenly switches to repetitive, degenerate output—repeating the same word or phrase endlessly. Looks normal for 2-3 tokens, then breaks.

**Detection:**
- Monitor for 3+ identical consecutive tokens
- Check if output entropy drops below 0.3 (your pipeline should flag this)
- If the model outputs `"the the the the"` or similar, you've hit it

**Avoidance:**
- Reduce `temperature` to 0.4–0.6 (not 0)
- Add `frequency_penalty: 0.3–0.5`
- Keep prompts under 60% of max context length
- If a prompt triggers the wall consistently, restructure it—break into smaller subtasks

**Recovery:** Kill the stream immediately. Do not attempt to "steer" out of it. Retry with modified parameters.

---

## 3. Stage Classification: 6-Probe Method

Every new model gets classified before fleet routing. Run these six probes:

1. **Identity probe:** "Who are you?" — Checks baseline behavior
2. **Arithmetic probe:** "What is 847 × 293?" — Verify computation reliability
3. **Instruction probe:** "Summarize this in exactly 3 sentences." — Test following ability
4. **Refusal probe:** A borderline request — Map safety boundaries
5. **Context probe:** Load to 80% context, ask about the beginning — Test retention
6. **Translation probe:** Translate a paragraph to Japanese — Check cross-lingual capability

**Classification based on results:**

| Pass Rate | Stage | Approved For |
|-----------|-------|-------------|
| 6/6 | Stage 1 (Full) | All tasks |
| 4–5/6 | Stage 2 (Standard) | Docs, classification, chat |
| 2–3/6 | Stage 3 (Limited) | Simple classification only |
| 0–1/6 | Stage 4 (Unusable) | Do not route |

Log all probe results to the fleet registry.

---

## 4. Pre-computation Protocol

**When to pre-compute:** Any prompt containing arithmetic where the answer is verifiable. Do not trust model math.

**How:**
1. Extract all numeric expressions from the prompt
2. Compute locally using standard libraries (Python `decimal` module, not float)
3. Inject results into the prompt as stated facts: `"847 × 293 = 248,171 (computed)"`
4. Instruct the model to use the provided values

**Exception:** Approximations or estimates don't need pre-computation. Only exact values.

**Rule of thumb:** If the user will check the answer with a calculator, pre-compute it.

---

## 5. Cross-Lingual Gotchas

**Japanese:**
- Helps Hermes-class models on reasoning tasks (some benchmarks show improvement)
- Hurts accuracy on simple math by 12–18% — number-word confusion
- Always pre-compute arithmetic for Japanese prompts (see §4)

**Spanish:**
- Drops negation in ~7% of translation outputs ("no quiero" → "I want")
- Verify all negatives post-translation
- Add explicit instruction: "Preserve all negation words"

**Mandarin:**
- Watch for simplified/traditional character mixing in long outputs

---

## 6. Cost Optimization

| Provider | Use For | Cost | Speed |
|----------|---------|------|-------|
| z.ai (paid) | Code, docs, complex tasks | $$ | Medium |
| DeepInfra | Computation, batch, translation | $ | Fast |
| Local (offline) | Classification, chat, fallback | Free | Fastest |

**Rules:**
- Never route a classification task to z.ai. It's wasteful.
- DeepInfra for anything you can batch. Queue it.
- Local model must be able to run disconnected. Test monthly.
- If you're spending more than $200/day on z.ai without explanation, flag it.

---

## 7. Error Recovery

**Computation fails:**
1. Retry once with identical parameters
2. Retry again with `temperature + 0.2`
3. Fall back to a different provider (z.ai → DeepInfra → local)
4. If all three fail, log the error and return a structured failure: `{"status": "failed", "task_id": "..."}`

**Timeout (30s exceeded):**
- Kill the request
- Retry on a faster provider (move to local if on DeepInfra)

**Rate limit hit:**
- Back off 60 seconds
- Route to next provider in priority
- Do not stack retries. One retry, then fail over.

---

## 8. Monitoring: What to Track

Track these per model, per day:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Accuracy (task-specific) | >92% | <85% |
| Translation rate | Track trend | Sudden spike/drop |
| Echo rate | <2% | >5% |
| Vocabulary wall frequency | <0.5% | >2% |
| Latency (p95) | <15s | >30s |
| Cost per 1K tokens | Track trend | >120% of baseline |

**Echo rate:** The model repeating the prompt back. Normal in small doses. If it exceeds 5% of outputs, the model is failing instruction-following.

**Dashboard:** Update daily. Review weekly. If any metric hits alert threshold for 3 consecutive days, reclassify the model (§3).

---

*Last updated: 2025-01-15 | Contact: fleet-ops@cocapn.internal*