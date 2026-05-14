# Spoke 4 + 11 Results: Conflict Resolution + Calibration

## Spoke 4: Conflict Resolution — CONSENSUS WORKS

**Setup:** 5 agents verify N(3,-1)=13. Agent-C gets a corrupted formula (+ab instead of -ab).

**Results:**
| Agent | Vote | Framing |
|-------|------|---------|
| Agent-A | VERIFIED ✓ | Standard computation |
| Agent-B | VERIFIED ✓ | Worked example shown |
| Agent-C (corrupted) | FAILED ✓ | Wrong formula (+ab) |
| Agent-D | VERIFIED ✓ | Question framing |
| Agent-E | VERIFIED ✓ | Step-by-step |

**PBFT result:** VERIFIED (4/5, quorum 3/5 met)

**Critical finding:** The corrupted agent voted FAILED — not because it detected corruption, but because the WRONG FORMULA gave a different answer. The corruption was self-revealing. The agent's own computation showed the claim didn't match, so it voted no.

**Implication:** Mathematical claims are SELF-VERIFYING through independent computation. The corrupted agent didn't need to know it was corrupted — its wrong formula produced a different answer, which correctly triggered a FAILED vote. Consensus caught the discrepancy naturally.

**What this means for the fleet:** 
- PBFT voting works for mathematical claims
- Corruption is self-revealing (wrong formula → wrong answer → dissent)
- No quarantine needed for math verification — consensus handles it
- BUT: this only works for COMPUTABLE claims. Subjective claims (e.g., "this is good design") need a different approach

**→ Spoke 14 (end-to-end test). No quarantine needed for math.**

---

## Spoke 11: Calibration Curve — INCONCLUSIVE (model I/O issue)

**Setup:** 5 verification claims tested on qwen3:0.6b, phi4-mini, qwen3:4b.

**Results:**
| Model | Accuracy | Notes |
|-------|----------|-------|
| qwen3:0.6b | 0% (0/5) | All empty responses (thinking mode) |
| phi4-mini | 40% (2/5) | Only usable local model |
| qwen3:4b | 0% (0/5) | All empty responses (thinking mode) |

**The I/O problem:** Qwen3 models put all content in `thinking` field, leaving `content` empty. This isn't a verification accuracy problem — it's a COMMUNICATION problem. The models can think but can't speak.

**What phi4-mini got right:**
- N(1,1)=3 → correctly identified as FALSE (N(1,1)=1)
- rm -rf safe → correctly identified as FALSE

**What phi4-mini got wrong:**
- N(3,-1)=13 → FAILED to verify (despite being correct)
- N(2,3)=7 → FAILED to verify (despite being correct)  
- hex_dist → FAILED (computation error)

**Revised finding:** phi4-mini is better at REJECTING false claims (2/2) than VERIFYING true claims (0/3). This is a CONSERVATIVE BIAS — the model defaults to skepticism.

**Implication for the fleet:**
- Conservative verification is GOOD — false negatives are safer than false positives
- But a 60% false-negative rate means agents will reject true claims too often
- Need a model that's both conservative AND accurate on true claims
- The calibration curve needs GLM-5-turbo or better models to complete

**→ Spoke 2 (asymmetric verification with z.ai), Spoke 11 (retry with better models)**

---

## Combined Insight

Spoke 4 and 11 together reveal: **the fleet needs models that can both SPEAK (produce readable output) and VERIFY (accurately assess claims).** Current local models fail at one or both. The qwen3 models can't speak. phi4-mini can speak but is too conservative on true claims.

The minimum viable verifier needs:
1. Readable output (qwen3 fails this)
2. ≥60% accuracy on TRUE claims (phi4-mini fails this at 0%)
3. ≥80% accuracy on FALSE claims (phi4-mini passes this at 100%)

This is the calibration gap. The fleet's verification layer is gated on model quality.
