# Beta Test Report v2: flux-lib-py
## Second Round — Verifying the Fixes

**Tester profile:** Same Python developer, coming back after fixes were applied.
**Date:** 2026-05-19
**Previous scores:** README clarity 5/10, API discoverability 4/10, Trust 6/10

---

## What Changed Since Last Test

The following fixes were applied based on the first beta test and synthesis:

1. ✅ `check_vector()` and `check_vector_batch()` added to `ConstraintEngine`
2. ✅ `ShadowgapResult.summary()` method implemented
3. ✅ Thermodynamic practical interpretation table added to README
4. ✅ 8-constraint limit stated prominently in README and docstrings
5. ✅ ThermoEngine.summary() convenience method added

---

## Test 1: check_vector()

```python
from flux_lib import ConstraintEngine
engine = ConstraintEngine.from_preset("automotive_can")
result = engine.check_vector([3000, 65, 95, 12.5, 45, 120, 1.0, 50])
print(f"Mask: {result.error_mask:#010b}, Passed: {result.passed}")
```

**Result:** Works immediately. Returns `Mask: 0b01000000, Passed: False` — battery_voltage_v (1.0) violates [9.0, 16.0].

**Experience:** This is EXACTLY what I needed in the first test. Each value maps to its own constraint. No confusion about "why does RPM violate the battery check?" — because now it doesn't. The battery value (1.0V) correctly flags as too low. RPM (3000) correctly passes.

```python
# With a real violation
result = engine.check_vector([3000, 65, 95, 12.5, 45, 120, 1.0, 999])
# → Mask: 0b11000000, 2 violations (battery + fuel)
```

**Batch mode works too:**
```python
samples = np.array([
    [3000, 65, 90, 40, 10, 45, 12.5, 50],
    [9000, 65, 90, 40, 10, 45, 12.5, 50],  # RPM violation
])
masks = engine.check_vector_batch(samples)
# → array([0, 1], dtype=uint8)
```

**Verdict: ✅ This is the killer fix.** It completely solves the "one value against all constraints" confusion. The API is intuitive — you pass an array of sensor readings and get per-constraint pass/fail. The error message when you pass the wrong number of values is clear: `"Expected 8 values (one per constraint), got 5"`.

**Is it in the README?** Yes. The README now has a dedicated `check_vector` section with examples showing both single and batch mode. The section header clearly says "N values against N constraints."

**Score: 9/10** — Only nit: the README example uses `[3000, 65, 90, 40, 10, 45, 12.5, 50]` which is valid for all constraints, so you don't see a violation in action. The second example with `999` for fuel is better. I'd lead with the violating example.

---

## Test 2: ShadowgapResult.summary()

```python
from flux_lib import ShadowgapFinder, MultiChecker
# ... setup ...
result = finder.find_from_checker(checker, values)
print(result.summary())
```

**Result:** Returns a dictionary, not a string. Contents:

```python
{
    "n_points": 200,
    "n_true_violations": 122,
    "n_consensus_catches": 122,
    "n_shadowgap": 0,
    "shadowgap_rate": 0.0,
    "shadowgap_fraction": 0.0,
    "per_constraint": [0, 0, 0],
    "clean": True
}
```

**Experience:** It works. Returns a dict with the key metrics. The `"clean": True` field is nice — I can immediately see if there are problems without parsing the numbers.

**Tested with actual shadowgaps** (using only the severity-weighted strategy):
```python
{
    "n_points": 200,
    "n_true_violations": 122,
    "n_consensus_catches": 56,
    "n_shadowgap": 66,
    "shadowgap_rate": 0.541,
    "shadowgap_fraction": 0.33,
    "per_constraint": [0, 36, 41],
    "clean": False
}
```

**Verdict: ✅ Works as expected.** The dict format is more useful than a string for programmatic use. The `clean` field is a thoughtful addition.

**Minor note:** In the first beta test, I said "README implies a summary method that doesn't exist." The README no longer implies a string summary — the summary() method exists and returns a dict. I'd suggest the README show this usage explicitly, including the `clean` field.

---

## Test 3: Thermodynamic Practical Translations

The README now includes this table:

| Value | Meaning |
|-------|---------|
| Z close to 1.0 | System is over-constrained |
| Z large | System is under-constrained |
| Temperature high | Less strict checking |
| Entropy high | Violations scattered |
| Entropy low | Violations concentrated |
| ... | ... |

**Does it help?** Yes, significantly. Let me verify with actual numbers:

- Equal-weight loose constraints: Z = 173.3, S = 5.5 → "many possible states, violations scattered" ✅
- Equal-weight tight constraints: Z = 1.055, S = 0.32 → "over-constrained, violations concentrated" ✅

**Is "Z close to 1 = over-constrained" clear enough?** Yes, especially now that I can verify it empirically. Z = 1.055 with tight constraints vs Z = 173.3 with loose ones makes the interpretation concrete.

**What's still missing:** A decision procedure. The table tells me what the numbers mean, but not what to DO about it. Something like:
- "If Z < 1.5: Review constraints — you may be over-constraining the system"
- "If S > 4.0: Violations are widespread — look for a systemic issue, not individual bad sensors"
- "If ideal_gas_check() = False: Constraints are coupled — use fracture to find the coupling"

**Score: 7/10** — Big improvement from "what do these numbers even mean?" to "ok, I know what they mean." Still missing the action layer.

---

## Test 4: 8-Constraint Limit

**Is it stated prominently?** Let me check where it appears:

1. ✅ **README header** — "The error mask is uint8, supporting up to 8 constraints." appears in the Constraint Checking section
2. ✅ **Docstring** — `ConstraintEngine.__doc__` says "up to **8 constraints**" in bold
3. ✅ **Constructor error** — `ValueError: Maximum 8 constraints (error_mask is uint8)` with clear explanation
4. ✅ **README workaround** — "For more constraints, use multiple engines."

```python
# Verified:
eng = ConstraintEngine([{'lo': i, 'hi': i+10, 'name': f'c{i}'} for i in range(9)])
# → ValueError: Maximum 8 constraints (error_mask is uint8)
```

**Would I have noticed it before hitting it?** Now yes. The docstring says it in bold. The README states it clearly. The error message is precise.

**Previous answer:** "Not mentioned until you dig in."
**Current answer:** Stated in docstring, README, and error message.

**Score: 8/10** — Could be even more prominent (a warning callout box) but it's now impossible to miss.

---

## Test 5: Build the Sensor Dashboard Again

### First test: 422 false positives, total disaster
### This test: 9 legitimate violations out of 20 readings

```python
eng = ConstraintEngine.from_preset("automotive_can")
# Inject known violations: RPM=9000, battery=7.5, fuel=110
readings = ...  # 20 samples with 3 injected violations
masks = eng.check_vector_batch(readings)
```

**Result:** 9 violations detected. Every single one is legitimate — brake_pressure going negative (sensor noise), fuel exceeding 100%, RPM spike, battery drop. The 3 injected violations are all caught. The additional 6 are real constraint violations from sensor noise in the simulation.

**Is it easier than before?** Night and day difference.

Before:
- Used `check()` — one value against all constraints → 422 false positives
- Had to create 8 separate engines → defeats the library's purpose
- "WTF does RPM have to do with battery voltage?"

After:
- Used `check_vector_batch()` — one call, correct results
- Single engine, single import
- Each reading maps to its own constraint → exactly what you'd expect

**Time to working dashboard:**
- First test: ~2 hours of confusion, then workaround
- This test: ~10 minutes from import to working code

The sediment stack also works well for the "what if we deploy to the arctic?" scenario:
```python
stack = SedimentStack()
stack.add_layer("arctic ops", corrections=[
    ConstraintCorrection("coolant_temp_c", new_lo=-55, reason="arctic ops"),
])
```

**Score: 10/10** — This is the use case the library was missing, and it's now completely solved.

---

## Test 6: Updated Ratings

| Category | Before | After | Change | Notes |
|----------|--------|-------|--------|-------|
| **README clarity** | 5 | 8 | +3 | Practical interpretation table, check_vector docs, limit stated. Still missing a "getting started" walkthrough. |
| **Install experience** | 9 | 9 | = | Already perfect. 95 tests pass in 0.23s. |
| **API discoverability** | 4 | 8 | +4 | check_vector is the natural API. summary() exists. Docstrings are good. Tab-complete reveals everything. |
| **Example quality** | 6 | 7 | +1 | Better examples but still no `examples/` directory referenced in README. |
| **Test coverage** | 9 | 9 | = | 83 → 95 tests. All passing. |
| **Code quality** | 8 | 8 | = | Clean, consistent. New methods follow existing patterns. |

### Bottom Line

| Question | Before | After |
|----------|--------|-------|
| **Would you use this?** | Depends | **Yes** |
| **Trust level** | 6/10 | **8/10** |
| **Biggest blocker** | check_vector missing | Missing time-series features (drift detection, rate-of-change) |

---

## What's Still Confusing / Missing

### Fixed (no longer confusing):
1. ~~check() checks one value against ALL constraints~~ → check_vector solves this
2. ~~What do I DO with Z=2.49?~~ → Practical interpretation table
3. ~~How do I check 8 sensors?~~ → check_vector_batch
4. ~~ShadowgapResult.summary() missing~~ → Now returns dict
5. ~~8-constraint limit hidden~~ → Prominent everywhere

### Still needs work:
1. **No time-series / drift detection.** Sensors produce streams over time. I want rate-of-change bounds, drift detection, sliding windows. This is the next logical feature.

2. **No serialization.** Can't save/load engine configs to JSON. For production deployment, I need to persist my constraint configs and sediment layers.

3. **No logging/callbacks.** No way to attach a callback on violation. For alerting, I need hooks.

4. **Thermodynamic decision procedures.** The interpretation table tells me what numbers mean, but not what to DO. "If Z < 1.5, your system may be over-constrained. Consider: (1) widening bounds, (2) removing redundant constraints, (3) checking if constraints are coupled."

5. **No CLI.** The README mentions `flux-check` as a separate tool but there's no `python -m flux_lib` entry point for quick ad-hoc checks.

6. **No aggregation utilities.** "What's the violation rate per sensor over the last hour?" requires manual numpy. A `ViolationStats` or similar helper would be useful.

7. **examples/ directory exists but isn't mentioned in README.** I didn't explore it this time either.

---

## Summary

The fixes are **genuine and effective**. The `check_vector()` API alone transforms the library from "confusing for sensor monitoring" to "exactly what I need." The practical thermodynamic interpretation table turns opaque physics into actionable information. The 8-constraint limit is now impossible to miss.

The library went from "maybe, depends on use case" to "yes, I'd use this for sensor monitoring." The core checking is solid, the preset system is convenient, and the sediment layer system is genuinely useful for deployment-specific overrides.

**The delta: +3 README clarity, +4 API discoverability, +2 trust. That's a big jump for a focused set of fixes.**
