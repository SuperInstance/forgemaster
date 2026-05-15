#!/usr/bin/env python3
"""
Deep Ground-Truth Map — llama-3.1-8b-instant
==============================================
Systematic probing across ALL known axes to build a complete capability portrait.

Axes probed:
1. Arithmetic operations (basic → complex)
2. Sign handling (positive, negative, mixed)
3. Magnitude (1s, 10s, 100s, 1000s)
4. Coefficient patterns (familiar → exotic)
5. Dependency width (1 → 6)
6. Nesting depth (flat → nested)
7. Variable count (1 → 4 vars)
8. Error modes (what happens when it fails)
9. Prompt style sensitivity (best seed variations)
10. Temperature sensitivity (0.0 → 2.0)

Every test uses the SAME question format so results are comparable.
Light comparison runs at the end on 2-3 other models for negative-space inference.

Author: Forgemaster ⚒️
"""
import requests, re, json, time, sys
from collections import defaultdict
from pathlib import Path

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# Standard prompt — the student seed
STD_PROMPT = "Compute {formula} where a={a} and b={b}."

def query(prompt, system="", temp=0.3, max_tokens=100):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
        json={"model": MODEL, "messages": msgs,
              "temperature": temp, "max_tokens": max_tokens}, timeout=30)
    resp = r.json()
    content = resp["choices"][0]["message"]["content"].strip()
    finish = resp["choices"][0]["finish_reason"]
    usage = resp.get("usage", {})
    nums = re.findall(r"-?\d+", content)
    out = int(nums[-1]) if nums else None
    return out, content, finish, usage

def test_formula(formula, cases, label="", trials=1):
    """Test a formula across multiple (a,b) inputs. Returns detailed results."""
    results = []
    for a, b, expected in cases:
        for t in range(trials):
            prompt = STD_PROMPT.format(formula=formula, a=a, b=b)
            out, raw, finish, usage = query(prompt)
            
            # Classify
            cls = "CORRECT" if out == expected else "WRONG"
            if out != expected:
                if out == a: cls = "ECHO-a"
                elif out == b: cls = "ECHO-b"
                elif out == -a: cls = "ECHO-neg_a"
                elif out == -b: cls = "ECHO-neg_b"
                elif out == a+b: cls = "ECHO-a+b"
                elif out == a-b: cls = "ECHO-a-b"
                elif out == a*a: cls = "PARTIAL-a²"
                elif out == b*b: cls = "PARTIAL-b²"
                elif out == a*b: cls = "PARTIAL-ab"
                elif out is not None and abs(out - expected) <= 2: cls = "NEAR"
                elif out is None: cls = "NO_NUM"
                else: cls = "OTHER"
            
            results.append({
                "a": a, "b": b, "expected": expected, "got": out,
                "class": cls, "raw": raw[:50], "finish": finish
            })
            time.sleep(0.15)
    
    correct = sum(1 for r in results if r["class"] == "CORRECT")
    return results, correct, len(results)

def run_axis(label, formula, cases, trials=1):
    """Run one axis of the probe and print results."""
    results, correct, total = test_formula(formula, cases, label, trials)
    rate = correct / total if total > 0 else 0
    
    print(f"\n  {label}", flush=True)
    print(f"  {'Formula':<20s} {'Rate':>6s} | Classes", flush=True)
    print(f"  {'-'*55}", flush=True)
    
    # Group by input
    by_input = defaultdict(list)
    for r in results:
        by_input[(r["a"], r["b"])].append(r)
    
    for (a, b), rs in by_input.items():
        classes = [r["class"] for r in rs]
        c = sum(1 for x in classes if x == "CORRECT")
        cls_str = " ".join(set(classes))
        print(f"  ({a:>4},{b:>4})→{rs[0]['expected']:>6}  {c}/{len(rs)}  {cls_str}", flush=True)
    
    print(f"  Total: {correct}/{total} ({rate:.0%})", flush=True)
    return rate, results

# ═══════════════════════════════════════════════════════════════
print("╔════════════════════════════════════════════════════════════╗", flush=True)
print("║  DEEP GROUND-TRUTH MAP: llama-3.1-8b-instant              ║", flush=True)
print("║  10-axis systematic probe                                  ║", flush=True)
print("╚════════════════════════════════════════════════════════════╝", flush=True)

all_results = {}

# ═══════════════════════════════════════════════════════════════
# AXIS 1: BASIC ARITHMETIC OPERATIONS
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 1: BASIC ARITHMETIC OPERATIONS ━━━", flush=True)

ops = [
    ("a+b",       lambda a,b: a+b),
    ("a-b",       lambda a,b: a-b),
    ("a*b",       lambda a,b: a*b),
    ("a²+b²",     lambda a,b: a*a+b*b),
    ("2a+b",      lambda a,b: 2*a+b),
    ("a²-b",      lambda a,b: a*a-b),
    ("a*b+b",     lambda a,b: a*b+b),
    ("a²+b",      lambda a,b: a*a+b),
    ("a²-ab",     lambda a,b: a*a-a*b),
    ("a²+2ab",    lambda a,b: a*a+2*a*b),
    ("a²-ab+b²",  lambda a,b: a*a-a*b+b*b),
    ("a²+ab+b²",  lambda a,b: a*a+a*b+b*b),
    ("a²-2ab+b²", lambda a,b: a*a-2*a*b+b*b),
    ("a³+b",      lambda a,b: a**3+b),
    ("a³-ab",     lambda a,b: a**3-a*b),
    ("a³+b³",     lambda a,b: a**3+b**3),
]

cases_small = [(3,4), (5,-2), (-4,3), (7,1), (-6,-5)]

op_results = {}
for formula, fn in ops:
    test_cases = [(a, b, fn(a,b)) for a, b in cases_small]
    results, correct, total = test_formula(formula, test_cases)
    rate = correct / total if total > 0 else 0
    op_results[formula] = rate
    
    sym = "✅" if rate >= 0.8 else "⚠️" if rate >= 0.4 else "❌"
    classes = defaultdict(int)
    for r in results:
        classes[r["class"]] += 1
    cls_str = ", ".join(f"{k}:{v}" for k,v in sorted(classes.items()))
    print(f"  {sym} {formula:<15s} {rate:>5.0%}  {cls_str}", flush=True)

all_results["axis1_ops"] = op_results

# ═══════════════════════════════════════════════════════════════
# AXIS 2: SIGN HANDLING
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 2: SIGN HANDLING ━━━", flush=True)
print("  Testing a²-ab+b² across sign combinations", flush=True)

sign_cases = [
    (3, 4, 13),    # +,+
    (-3, 4, 37),   # -,+
    (3, -4, 37),   # +,-
    (-3, -4, 13),  # -,-
    (3, 0, 9),     # +,0
    (0, 4, 16),    # 0,+
    (-3, 0, 9),    # -,0
    (0, -4, 16),   # 0,-
]

rate, results = run_axis("sign_handling", "a²-ab+b²", sign_cases)
all_results["axis2_signs"] = rate

# ═══════════════════════════════════════════════════════════════
# AXIS 3: MAGNITUDE
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 3: MAGNITUDE ━━━", flush=True)
print("  Testing a²-ab+b² across input magnitudes", flush=True)

mag_cases = [
    # Ones
    (3, 4, 13), (2, 1, 3), (5, -2, 39),
    # Tens
    (30, 40, 1300), (20, 10, 300), (50, -20, 3900),
    # Hundreds
    (300, 400, 130000), (200, 100, 30000), (500, -200, 390000),
    # Thousands
    (3, 400, 160009), (300, 4, 89912), (30, 4000, 1600900),
]

rate, results = run_axis("magnitude", "a²-ab+b²", mag_cases)
all_results["axis3_magnitude"] = rate

# ═══════════════════════════════════════════════════════════════
# AXIS 4: COEFFICIENT PATTERNS
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 4: COEFFICIENT PATTERNS ━━━", flush=True)
print("  Testing quadratic forms c₁a²+c₂ab+c₃b² with varied coefficients", flush=True)

coeff_cases = [(3,4), (5,-2), (-4,3), (7,1)]
coeffs = [
    ("a²+b²",      1, 0, 1),
    ("a²+ab+b²",   1, 1, 1),
    ("a²-ab+b²",   1,-1, 1),
    ("a²+2ab+b²",  1, 2, 1),
    ("a²-2ab+b²",  1,-2, 1),
    ("2a²+ab+b²",  2, 1, 1),
    ("a²+ab+2b²",  1, 1, 2),
    ("2a²+3ab+b²", 2, 3, 1),
    ("a²+3ab+2b²", 1, 3, 2),
    ("3a²-2ab+b²", 3,-2, 1),
    ("a²-2ab+2b²", 1,-2, 2),
    ("2a²-ab+2b²", 2,-1, 2),
]

for formula, c1, c2, c3 in coeffs:
    test_cases = [(a, b, c1*a*a + c2*a*b + c3*b*b) for a, b in coeff_cases]
    results, correct, total = test_formula(formula, test_cases)
    rate = correct / total if total > 0 else 0
    sym = "✅" if rate >= 0.8 else "⚠️" if rate >= 0.4 else "❌"
    print(f"  {sym} {formula:<15s} [{c1},{c2:+d},{c3}]  {rate:.0%}", flush=True)

# ═══════════════════════════════════════════════════════════════
# AXIS 5: DEPENDENCY WIDTH (systematic)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 5: DEPENDENCY WIDTH ━━━", flush=True)

width_cases = [(3,4), (5,-2), (-4,3), (7,1)]

widths = [
    # width 1: single operation
    ("a+b", 1, lambda a,b: a+b),
    ("a²", 1, lambda a,b: a*a),
    ("2a", 1, lambda a,b: 2*a),
    # width 2: two operations
    ("a²+b", 2, lambda a,b: a*a+b),
    ("2a+b²", 2, lambda a,b: 2*a+b*b),
    ("a*b+b", 2, lambda a,b: a*b+b),
    # width 3: three operations
    ("a²+b²+c", 3, lambda a,b: a*a+b*b+1),  # no c, use 1
    ("a²-ab+b²", 3, lambda a,b: a*a-a*b+b*b),
    ("a²+2ab-b", 3, lambda a,b: a*a+2*a*b-b),
    # width 4: four operations
    ("a³-ab+b²-a", 4, lambda a,b: a**3-a*b+b*b-a),
    ("2a²-3ab+b²", 4, lambda a,b: 2*a*a-3*a*b+b*b),
    # width 5+: complex
    ("a³-a²b+ab²-b³", 5, lambda a,b: a**3-a*a*b+a*b*b-b**3),
    ("2a³+3a²b-ab²+2b³", 6, lambda a,b: 2*a**3+3*a*a*b-a*b*b+2*b**3),
]

for formula, width, fn in widths:
    test_cases = [(a, b, fn(a,b)) for a, b in width_cases]
    results, correct, total = test_formula(formula, test_cases)
    rate = correct / total if total > 0 else 0
    sym = "✅" if rate >= 0.8 else "⚠️" if rate >= 0.4 else "❌"
    print(f"  {sym} w={width} {formula:<20s} {rate:.0%}", flush=True)

# ═══════════════════════════════════════════════════════════════
# AXIS 6: SIGN ERROR DECOMPOSITION
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 6: SIGN ERROR DECOMPOSITION ━━━", flush=True)
print("  Testing where exactly the sign error occurs", flush=True)

# Test each sub-expression individually with negative inputs
sign_probe_cases = [(5, -3), (-4, 3), (-6, -5)]

sub_exprs = [
    ("a²",           lambda a,b: a*a),
    ("b²",           lambda a,b: b*b),
    ("ab",           lambda a,b: a*b),
    ("-ab",          lambda a,b: -(a*b)),
    ("a²-ab",        lambda a,b: a*a-a*b),
    ("-ab+b²",       lambda a,b: -(a*b)+b*b),
    ("a²-ab+b²",     lambda a,b: a*a-a*b+b*b),
    # Alternative forms that MIGHT avoid the sign error
    ("a²+(-a)*b+b²", lambda a,b: a*a+(-a)*b+b*b),
    ("a²-(a*b)+b²",  lambda a,b: a*a-(a*b)+b*b),
    ("a²+b²-ab",     lambda a,b: a*a+b*b-a*b),  # reordered!
    ("b²-ab+a²",     lambda a,b: b*b-a*b+a*a),  # reordered more!
]

for formula, fn in sub_exprs:
    test_cases = [(a, b, fn(a,b)) for a, b in sign_probe_cases]
    results, correct, total = test_formula(formula, test_cases)
    rate = correct / total if total > 0 else 0
    sym = "✅" if rate >= 0.8 else "⚠️" if rate >= 0.4 else "❌"
    print(f"  {sym} {formula:<20s} {rate:.0%}", flush=True)

# ═══════════════════════════════════════════════════════════════
# AXIS 7: TEMPERATURE SENSITIVITY
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 7: TEMPERATURE SENSITIVITY ━━━", flush=True)

temp_test = (5, -3, 49)  # N(5,-3) = 49 — the hard case
temps = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]

for temp in temps:
    correct = 0
    classes = defaultdict(int)
    for _ in range(10):
        prompt = STD_PROMPT.format(formula="a²-ab+b²", a=5, b=-3)
        out, raw, finish, usage = query(prompt, temp=temp)
        cls = "CORRECT" if out == 49 else "WRONG"
        if cls == "WRONG" and out is not None:
            if out == 5: cls = "ECHO-a"
            elif out == -3: cls = "ECHO-b"
            elif out == 25: cls = "PARTIAL-a²"
            elif out == 9: cls = "PARTIAL-b²"
            elif out == -15 or out == 15: cls = "SIGN-ab"
            elif abs(out - 49) <= 5: cls = "NEAR"
            else: cls = "OTHER"
        if cls == "CORRECT": correct += 1
        classes[cls] += 1
        time.sleep(0.1)
    
    print(f"  T={temp:.1f}: {correct}/10  {' '.join(f'{k}:{v}' for k,v in sorted(classes.items()))}", flush=True)

# ═══════════════════════════════════════════════════════════════
# AXIS 8: RETRY RELIABILITY
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 8: RETRY RELIABILITY ━━━", flush=True)
print("  20 trials each at T=0.3 on key formulas", flush=True)

reliable_formulas = [
    ("a+b", (3,4,7)),
    ("a²+b²", (3,4,25)),
    ("a²-ab+b²", (3,4,13)),
    ("a²-ab+b²", (5,-3,49)),
    ("a³+b³", (3,4,91)),
]

for formula, (a, b, ans) in reliable_formulas:
    outputs = []
    for _ in range(20):
        prompt = STD_PROMPT.format(formula=formula, a=a, b=b)
        out, _, _, _ = query(prompt, temp=0.3)
        outputs.append(out)
        time.sleep(0.1)
    
    correct = sum(1 for o in outputs if o == ans)
    unique = len(set(outputs))
    print(f"  {formula:<15s} ({a},{b})→{ans}: {correct}/20 correct, {unique} unique outputs", flush=True)
    
    # Show distribution of wrong answers
    wrong = [o for o in outputs if o != ans and o is not None]
    if wrong:
        from collections import Counter
        counts = Counter(wrong).most_common(5)
        print(f"    Wrong distribution: {counts}", flush=True)

# ═══════════════════════════════════════════════════════════════
# AXIS 9: NEGATIVE SPACE MARKERS
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 9: NEGATIVE SPACE MARKERS ━━━", flush=True)
print("  Tasks that SHOULD be easy but aren't, and vice versa", flush=True)

surprises = [
    # Should be easy (width 1)
    ("3", (3,4,3), "just return a"),
    ("b", (3,4,4), "just return b"),
    ("a+0", (5,-3,5), "identity"),
    ("0+b", (5,-3,-3), "identity reversed"),
    # Should be hard but maybe aren't
    ("a*a*a", (5,-3,125), "cubic via repeated mult"),
    ("a**3", (5,-3,125), "cubic via power"),
    # Edge: zero
    ("a²+b²", (0,0,0), "zero inputs"),
    ("a²-ab+b²", (0,0,0), "zero Eisenstein"),
    ("a²-ab+b²", (1,1,1), "a=b=1"),
    ("a²-ab+b²", (1,-1,3), "a=1,b=-1"),
    # Large constant
    ("100*a+b", (3,4,304), "large coefficient"),
    ("a+100*b", (3,4,403), "large coefficient reversed"),
    # Non-polynomial (should these work?)
    ("abs(a)+abs(b)", (5,-3,8), "absolute values"),
    ("max(a,b)", (5,-3,5), "max"),
    ("min(a,b)", (5,-3,-3), "min"),
]

for formula, (a, b, ans), note in surprises:
    prompt = STD_PROMPT.format(formula=formula, a=a, b=b)
    out, raw, _, _ = query(prompt)
    ok = "✅" if out == ans else "❌"
    print(f"  {ok} {formula:<15s} ({a},{b})→{ans} got={out}  [{note}]", flush=True)
    time.sleep(0.15)

# ═══════════════════════════════════════════════════════════════
# AXIS 10: CROSS-MODEL COMPARISON (light)
# ═══════════════════════════════════════════════════════════════
print("\n\n━━━ AXIS 10: LIGHT CROSS-MODEL COMPARISON ━━━", flush=True)
print("  Testing key discriminators on other models", flush=True)

# The key discriminators — where llama-3.1-8b shows interesting behavior
discriminator_cases = [
    ("a²-ab+b²", (3,4,13)),    # llama gets this
    ("a²-ab+b²", (5,-3,49)),   # llama fails this (sign)
    ("a²+ab+b²", (5,-3,19)),   # coefficient variant
    ("a³+b", (5,-3,122)),      # cubic
    ("2a²-3ab+b²", (3,4,5)),   # width-4
]

comparison_models = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",  # baseline
]

print(f"\n  {'Formula':<15s} {'(a,b)→ans':<15s}", end="", flush=True)
for m in comparison_models:
    short = m.split("/")[-1][:12]
    print(f" {short:>12s}", end="", flush=True)
print(flush=True)
print(f"  {'-'*60}", flush=True)

for formula, (a, b, ans) in discriminator_cases:
    print(f"  {formula:<15s} ({a},{b})→{ans:<5d}", end="", flush=True)
    
    for model in comparison_models:
        prompt = STD_PROMPT.format(formula=formula, a=a, b=b)
        r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3, "max_tokens": 50}, timeout=30)
        content = r.json()["choices"][0]["message"]["content"].strip()
        nums = re.findall(r"-?\d+", content)
        out = int(nums[-1]) if nums else None
        sym = "✅" if out == ans else f"{out}"
        print(f" {sym:>12s}", end="", flush=True)
        time.sleep(0.2)
    
    print(flush=True)

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "="*60, flush=True)
print("DEEP GROUND-TRUTH MAP COMPLETE", flush=True)
print("="*60, flush=True)
print(f"Model: {MODEL}", flush=True)
print(f"Total queries: ~{(16*5 + 8 + 12 + 12*4 + 12*4 + 11*3 + 10*10 + 5*20 + 15 + 5*2) * 1}", flush=True)
print(flush=True)
print("Save results with: python3 experiments/deep_ground_truth.py > experiments/GROUND-TRUTH-LLAMA31.txt", flush=True)
