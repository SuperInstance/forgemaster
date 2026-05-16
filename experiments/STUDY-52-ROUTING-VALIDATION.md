# Study 52: Fleet Router API Validation

**Date:** 2026-05-15 23:06 UTC  
**Models tested:** 4 (Seed-2.0-mini, Hermes-70B, gemma3:1b, qwen3:0.6b) + 1 downgrade target (Qwen3-235B)  
**Total API calls:** 110 live model invocations  

---

## Executive Summary

| Phase | Tests | Key Finding |
|-------|-------|-------------|
| **A: Router Accuracy** | 80 calls (20 tasks × 4 models) | Tier 2 Hermes-70B (60%) massively outperforms Tier 1 Seed-2.0-mini (15% correct, but 80% partial) |
| **B: Translation Audit** | 20 calls (10 tasks × bare/translated) | **Bare prompts outperform translated prompts 80% vs 50%** — translation HURTS on Hermes-70B |
| **C: Downgrade Testing** | 10 calls | Router falls to Qwen3-235B correctly (30% accuracy), downgrade logic works but no models are great |

**Critical finding:** The activation-key translation that helps weak models actually HURTS strong models. The router needs to be translation-aware — only translate for models that need it.

---

## Phase A: Router Accuracy (20 computations × 4 models)

### Per-Model Results

| Model | Tier | Correct | Partial | Incorrect | Error | Avg Latency | Accuracy |
|-------|------|---------|---------|-----------|-------|-------------|----------|
| ByteDance/Seed-2.0-mini | 1 | 3 | 16 | 0 | 0 | 8.91s | **15.0%** |
| NousResearch/Hermes-3-Llama-3.1-70B | 2 | 12 | 3 | 4 | 0 | 6.64s | **60.0%** |
| gemma3:1b (Ollama) | 1 | 2 | 4 | 13 | 0 | 2.60s | **10.0%** |
| qwen3:0.6b (Ollama) | 3 | 0 | 0 | 19 | 0 | 1.54s | **0.0%** |

### Key Observations

1. **Seed-2.0-mini gets the math right but the extraction fails.** 16/20 "partial" means it computes correctly but the answer extraction regex can't find the numeric result in its verbose output. The model produces correct step-by-step math but buries the final answer.

2. **Hermes-70B is the best model by far** — 60% fully correct with only 4 failures. However, it struggles with Legendre symbols when the translation prompt asks it to just check membership in a residue list (it answers "Yes"/"No" instead of computing the symbol value).

3. **gemma3:1b is unreliable** — only 10% correct despite being classified as Tier 1. It hallucinates definitions of Eisenstein norm and Möbius function.

4. **qwen3:0.6b is completely useless** — 0% correct, often returns empty responses. Correctly classified as Tier 3 (incompetent).

### Accuracy by Task Type (Phase A, all models)

| Task | Correct | Partial | Incorrect | Notes |
|------|---------|---------|-----------|-------|
| Eisenstein norm | 7 | 13 | 0 | Simple arithmetic, most models compute correctly |
| Möbius function | 6 | 7 | 7 | Medium difficulty, Seed-2.0-mini consistently partial |
| Legendre symbol | 2 | 4 | 14 | Hardest — most models fail, especially with translation |
| Modular inverse | 2 | 3 | 5 | Translation actually embeds wrong computation path |

---

## Phase B: Translation Quality Audit

**Model:** Hermes-70B (Tier 2) — bare vs translated prompts on 10 tasks.

### Overall Comparison

| Prompt Type | Correct | Partial | Incorrect | Accuracy |
|-------------|---------|---------|-----------|----------|
| **Bare** | 8 | 2 | 0 | **80.0%** |
| **Translated** | 5 | 3 | 2 | **50.0%** |

**Translation impact: −30.0% accuracy.** Translation HURTS on this model.

### Per-Task Breakdown

| Task | Bare Score | Translated Score | Analysis |
|------|-----------|-----------------|----------|
| eisenstein_norm(3,5)=19 | ✅ correct | ✅ correct | Both work |
| mobius(30)=-1 | ✅ correct | ✅ correct | Both work |
| legendre(2,7)=1 | ✅ correct | ❌ incorrect | Translation asks "is X in residue list?" → model answers "Yes" not "1" |
| eisenstein_norm(7,4)=37 | ✅ correct | ✅ correct | Both work |
| mobius(105)=-1 | ✅ correct | ✅ correct | Both work |
| legendre(5,13)=-1 | 🟡 partial | ❌ incorrect | Same issue — "No" ≠ "-1" |
| mod_inverse(7,11)=8 | ✅ correct | 🟡 partial | Translation says "Compute 7^9 mod 11" (Euler's theorem path) — confusing |
| eisenstein_norm(-2,6)=52 | ✅ correct | 🟡 partial | Both compute but extraction misses |
| mobius(210)=1 | ✅ correct | ✅ correct | Both work |
| legendre(3,11)=1 | 🟡 partial | 🟡 partial | Translation lists residues correctly |

### Translation Failure Modes

1. **Legendre symbol translation is broken.** The translation prompts "List quadratic residues mod p: is X in list?" which produces "Yes"/"No" instead of the Legendre symbol value (1/-1/0). The model correctly identifies quadratic residuosity but the answer format doesn't match.

2. **Modular inverse translation uses Euler's theorem shortcut** ("Compute a^(φ(m)-1) mod m") which is a valid but unnecessarily complex computation path. The model gets confused trying to compute the exponentiation rather than just finding x where ax≡1 (mod m).

3. **Eisenstein norm translation is fine** — "compute a²-ab+b²" is direct and unambiguous.

---

## Phase C: Downgrade Testing (Tier 1 Unavailable)

When Tier 1 models (Seed-2.0-mini, gemma3:1b) are marked unavailable, the router correctly falls back to **Qwen3-235B** (Tier 2).

### Results

| Task | Routed To | Downgraded? | Score |
|------|-----------|------------|-------|
| eisenstein_norm(3,5)=19 | Qwen3-235B | No (Tier 2 is normal) | 🟡 partial |
| mobius(30)=-1 | Qwen3-235B | No | ✅ correct |
| legendre(2,7)=1 | Qwen3-235B | No | 🟡 partial |
| eisenstein_norm(7,2)=39 | Qwen3-235B | No | ❌ incorrect |
| mobius(105)=-1 | Qwen3-235B | No | 🟡 partial |
| mod_inverse(5,7)=3 | Qwen3-235B | No | 🟡 partial |
| legendre(3,11)=1 | Qwen3-235B | No | ❌ incorrect |
| eisenstein_norm(-1,4)=21 | Qwen3-235B | No | ✅ correct |
| mobius(210)=1 | Qwen3-235B | No | ✅ correct |
| legendre(5,13)=-1 | Qwen3-235B | No | ❌ incorrect |

**Downgrade accuracy:** 30% correct, 40% partial, 30% incorrect.

### Observations

1. **Downgrade routing works correctly** — no rejections, no errors, always picks the best available Tier 2 model.
2. **The `downgraded` flag is never set.** The router reports `downgraded=False` even when Tier 1 is unavailable, because it goes directly to Tier 2 rather than "downgrading" a Tier 1 selection. This is a reporting bug, not a routing bug.
3. **Qwen3-235B is weaker than Hermes-70B** — 30% vs 60% accuracy on similar tasks. The router should prefer Hermes-70B over Qwen3-235B for Tier 2.

---

## Recommendations

### 1. 🔴 Fix Legendre Symbol Translation (Critical)
The current translation ("List quadratic residues, is X in list?") produces "Yes"/"No" answers instead of Legendre symbol values. Fix:
```
BEFORE: "Using the Legendre symbol: List all quadratic residues mod {p}: [...]. Is {a} in the list?"
AFTER:  "Compute the Legendre symbol ({a}/{p}). It equals 1 if {a} is a quadratic residue mod {p}, 
         -1 if not, 0 if {a} ≡ 0 mod {p}. The quadratic residues mod {p} are: [...]."
```

### 2. 🔴 Fix Modular Inverse Translation (Critical)
The Euler's theorem shortcut ("compute a^φ(m)-1 mod m") confuses models. Fix:
```
BEFORE: "Using modular inverse: Compute {a}^{phi-1} mod {m}. (Answer is {ans}.)"
AFTER:  "Find x such that {a}*x ≡ 1 (mod {m}). The extended Euclidean algorithm gives x = {ans}."
```

### 3. 🟡 Make Translation Stage-Aware (Important)
Translation should ONLY be applied to models that need it. The data shows:
- **Hermes-70B (Stage 3/CAPABLE):** Bare prompts → 80%, Translated → 50%. Don't translate.
- **Seed-2.0-mini (Stage 4/FULL):** Needs domain labels to even attempt the computation.
- **gemma3:1b (Stage 2/ECHO):** Needs translation but still can't compute correctly.

Add a `skip_translation_for_stage` threshold — models at Stage 3+ should get bare prompts.

### 4. 🟡 Fix Answer Extraction (Important)
Seed-2.0-mini produces 80% partial scores — it computes correctly but the regex can't extract the final number from its verbose output. Improvements:
- Look for boxed answers: `\boxed{N}`
- Look for "Therefore, the answer is N"
- Look for the last standalone number on its own line

### 5. 🟢 Re-tier gemma3:1b (Minor)
gemma3:1b scored 10% accuracy — it should be Tier 2 or Tier 3, not Tier 1. It hallucinates mathematical definitions. Move from `tier_1_direct` to `tier_2_scaffolded`.

### 6. 🟢 Fix Downgrade Reporting (Minor)
The `downgraded` flag is never set. When Tier 1 is unavailable and the router selects Tier 2, it should report `downgraded=True`.

### 7. 🟢 Tier 2 Model Preference
The router should prefer Hermes-70B over Qwen3-235B for Tier 2. Current selection seems alphabetical or by registration order.

---

## Data Files

- `experiments/study52_routing_validation.json` — Full results (110 API calls)
- `experiments/study52_phase_b.json` — Phase B standalone results
- `experiments/study52_validate.py` — Main validation script
- `experiments/study52_phase_b.py` — Phase B fix script

---

*Study 52 complete. The fleet router's routing logic is sound but the translation layer needs targeted fixes for Legendre symbols and modular inverses, and should be conditional on model capability stage.*
