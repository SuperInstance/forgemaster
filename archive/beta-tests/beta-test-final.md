# Beta Test Report — Total Newcomer Perspective

**Tester:** Fresh eyes, no prior exposure to SuperInstance  
**Date:** 2026-05-19  
**Environment:** WSL2, Python 3.10, pip install flux-lib (already cached)

---

## Step 1: Discover — github.com/SuperInstance

**Time to understand:** ~90 seconds (slightly over the 60-second target)

The org README is a *story*, not a README. It explains the shell architecture (inner shell → agent → outer shell), tiles, PLATO, rooms, and the conservation law. It's compelling writing with genuine intellectual depth.

**What I understood in 60s:**
- This is an agent framework with a novel architecture (shells + tiles)
- Tiles are Q&A pairs with confidence scores, stored in rooms
- PLATO is the filesystem, FLUX is the constraint engine
- There's a conservation law (γ + H = 1.283 − 0.159 · ln(V)) that ensures coherence
- Small models in structured rooms > big models with no structure

**What I didn't understand in 60s:**
- How to actually *use* any of this. The README is 90% philosophy, 10% code
- What "constraint theory" means in practice — it's mentioned everywhere but not defined until you dig deeper
- The relationship between PLATO/FLUX/tiles/rooms — too many concepts introduced simultaneously

**Impression:** "This is either the most interesting org on GitHub or the most elaborate art project." Compelling but disorienting.

---

## Step 2: Quick Start — flux-lib-py

**Time to first working code:** ~2 minutes (pip already installed)

```bash
pip install flux-lib
```

✅ Install worked instantly.  
✅ `ConstraintEngine.from_preset("automotive_can")` — clean, discoverable.  
✅ `engine.check(9000)` — returns result with `.passed`, `.severity` — intuitive.

**Hiccup:** The org README shows `check_vector()` and `check_vector_batch()` which **don't exist in the actual package**. This was confusing. The actual API has `check()` (one value against all constraints) and `check_batch()` (array of values against all constraints).

There is NO per-sensor vector check. For 8 sensors, you'd need 8 separate engines or manual bounds checking. The README promises something the package doesn't deliver.

---

## Step 3: 5-Minute Tutorial — getting-started.md

The tutorial is **excellent**. Multi-language (Python, Rust, JS, C), each showing the same 8-constraint example with the same error mask. I could follow it immediately.

**Time:** 3 minutes to read and understand.

**Score for the tutorial itself: 9/10.** Clean, consistent, teaches the error mask visually.

**Gap:** The tutorial shows the *result* but doesn't explain *how to install* for each language. It shows `pip install flux-lib` and `cargo add flux-fracture` but the JS version says "may not yet be published" — which is honest but not confidence-inspiring.

---

## Step 4: Concept Pages — Rated

### Error Mask (9/10)
Best concept page. Crystal clear. The comparison tables (boolean list vs mask, set vs mask, enum vs mask) are devastating — you walk away convinced the error mask is obviously correct. The "one CPU instruction" argument is compelling.

### NaN Trap (10/10)
The standout piece. Starts with a real bug ("the bug that started FLUX"), shows exactly how IEEE 754 silently passes NaN, and explains why `isnan()` must come first. This is the page that makes you *trust* the project. "If your comparison doesn't handle NaN, it's not a comparison — it's a lie." Chef's kiss.

### Fracture-Coalesce (8/10)
Solid technical explanation with a proof. The dependency graph visualization is clear. The performance table is useful. Loses a point because it assumes you'll have GPU hardware — the CPU path isn't as well motivated.

### Sediment (9/10)
Beautiful metaphor (geological layers, fossil record). The frozen core / open edges pattern is genuinely novel. The COBOL comparison is earned, not forced. "Never delete. Only supersede." — this sticks.

### Thermodynamics (7/10)
The weakest concept page. The math is presented without enough motivation. "Why do I need a partition function for bounds checking?" isn't answered until the end. The precision class section (INT8/FP16/FP32/FP64) feels bolted on. If I weren't committed to reading everything, I'd have skimmed this.

**Average concept rating: 8.6/10**

---

## Step 5: Build Something Real — Sensor Validator

### What I Built
Using ONLY the docs, I attempted to build a sensor validator with:
- 8 sensors using automotive preset
- Per-sensor validation
- Sediment layer
- Batch validation on 100 readings
- Aggregated results
- Save/load config
- Drift detection

### What Actually Worked
✅ Loading the automotive preset — trivial, one line  
✅ SedimentStack and ConstraintCorrection — API matches docs  
✅ check_batch() for batch validation  
✅ Save/load config with JSON — outside the lib but natural  
✅ Drift detection — computed manually from batch results

### What Broke
❌ **`check_vector()` does not exist.** The README and docs show it. The package doesn't have it. This is the biggest issue — the docs describe a feature that isn't implemented. I had to fall back to checking each sensor individually with `check()`.

❌ **`check()` checks ONE value against ALL constraints.** This means for per-sensor validation (each sensor has its own bounds), there's no built-in API. You'd need 8 separate engines or manual bounds checking.

❌ **100% violation rate in batch mode.** Because `check()` tests one value against all 8 constraints, generating "in range" readings for all sensors at once is impossible with a single engine. Every value fails at least one constraint.

### Workaround
I built a manual per-sensor validator by iterating over each reading and each sensor index separately. It works but defeats the purpose of a "5-minute build."

### Time to Working Solution: ~12 minutes (exceeding the 10-minute target, largely due to the missing `check_vector`)

---

## Step 6: Final Scores

| Category | Score (1-10) | Notes |
|----------|:---:|-------|
| 10-second first impression | 7 | Org README is visually clean but walls of text. No "what is this in one sentence?" |
| 60-second understanding | 6 | Too many concepts (PLATO, tiles, shells, rooms, FLUX, conservation law) introduced at once. Philosophy before function. |
| 5-minute tutorial | 9 | Multi-language, consistent example, error mask is intuitive. Near-perfect. |
| API discoverability | 5 | `check_vector` in docs doesn't exist. `check()` does something unexpected (one value vs ALL constraints). No `help()` friendly docstrings discovered. |
| README clarity | 7 | Well-written but more manifesto than reference. "What does this do for me?" is buried. |
| Install experience | 9 | `pip install flux-lib` — one line, works, no config. Excellent. |
| Documentation depth | 8 | Concept pages are genuinely excellent. NaN Trap and Error Mask are reference-quality. Thermodynamics needs more "why." |
| Would use in production | 6 | The API mismatch between docs and reality is a trust issue. Sediment layers are great. Fracture-coalesce is sound. But I'd need to verify every claim against the source. |
| Trust level | 7 | The NaN Trap page *built* trust. The missing `check_vector` *destroyed* some of it. The mathematical proofs help. The conservation law is intriguing but I can't verify it from the README. |
| Would recommend | 7 | "The ideas are brilliant but the implementation is catching up to the documentation." |

**Overall: 7.1/10**

---

## Step 7: The ONE Thing

**Fix the API-documentation mismatch.**

The docs show `check_vector()` and `check_vector_batch()`. The package has neither. This is the single biggest trust killer. A newcomer reads the README, tries the code, and it fails with `AttributeError`. That's the moment they close the tab.

**The fix:** Either implement `check_vector` (check N values against N constraints, one-to-one) or remove it from all documentation. If it's a planned feature, mark it as "coming soon" — don't present it as working.

This one change would push:
- API discoverability: 5 → 9
- Trust level: 7 → 9  
- Would use in production: 6 → 8
- Would recommend: 7 → 9

Because the ideas underneath are genuinely strong. The error mask, NaN trap, sediment layers, fracture-coalesce — these are real contributions. But none of that matters if the first code a newcomer writes throws `AttributeError`.

---

## Appendix: What the Docs Promise vs What Exists

| Feature | In Docs | In Package | Status |
|---------|:-------:|:----------:|--------|
| `ConstraintEngine` | ✅ | ✅ | Works |
| `from_preset()` | ✅ | ✅ | Works (10 presets) |
| `check()` | ✅ | ✅ | Works |
| `check_batch()` | ✅ | ✅ | Works |
| `check_vector()` | ✅ | ❌ | **Missing** |
| `check_vector_batch()` | ✅ | ❌ | **Missing** |
| `SedimentStack` | ✅ | ✅ | Works |
| `ConstraintCorrection` | ✅ | ✅ | Works |
| `fracture()` / `coalesce()` | ✅ | ✅ | Importable |
| `DependencyGraph` | ✅ | ✅ | Importable |
| `ShadowgapFinder` | ✅ | ✅ | Importable |
| `ThermoEngine` | ✅ | ✅ | Importable |
| Save/load engine state | ✅ | ❌ | No serialization API |
| Preset discovery (`available_presets`) | ✅ | ✅ | Works |
