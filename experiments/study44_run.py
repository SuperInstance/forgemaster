#!/usr/bin/env python3
"""Study 44: Formula Conflict Causal Intervention"""
import json, time, requests, sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
TEMP = 0.3
MAX_TOKENS = 150
N_TRIALS = 25
CORRECT = 49

PROMPTS = {
    "C1_formula_only": "Compute f(5, -3) where f(a,b) = a² - ab + b². Reply ONLY the integer result.",
    "C2_formula_safe_domain": "Compute the polynomial norm N(5, -3) where N(a,b) = a² - ab + b². Reply ONLY the integer result.",
    "C3_formula_landmine": "Compute the Eisenstein norm N(5, -3) where N(a,b) = a² - ab + b². Reply ONLY the integer result.",
    "C4_formula_emphasized": "IMPORTANT: Use ONLY the formula given below. Compute the Eisenstein norm N(5, -3). The formula is: N(a,b) = a² - ab + b². Do NOT use any other formula. N(5,-3) = 5² - 5×(-3) + (-3)² = ? Reply ONLY the integer result.",
}

def call_api(condition, trial, prompt):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMP,
        "max_tokens": MAX_TOKENS,
    }
    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        # Extract integer from response
        got = None
        for token in text.split():
            cleaned = token.strip(".,;:!?()[]{}'")
            try:
                got = int(cleaned)
                break
            except ValueError:
                continue
        if got is None:
            # Try to find any integer in the text
            import re
            nums = re.findall(r'-?\d+', text)
            if nums:
                got = int(nums[-1])
        return {"condition": condition, "trial": trial, "response": text, "extracted": got, "correct": got == CORRECT, "error": None}
    except Exception as e:
        return {"condition": condition, "trial": trial, "response": "", "extracted": None, "correct": False, "error": str(e)}

# Build all tasks
tasks = []
for cond, prompt in PROMPTS.items():
    for trial in range(N_TRIALS):
        tasks.append((cond, trial, prompt))

print(f"Study 44: Running {len(tasks)} API calls ({len(PROMPTS)} conditions × {N_TRIALS} trials)")
print(f"Model: {MODEL}, Temp: {TEMP}, Correct answer: {CORRECT}")
print(f"Started: {datetime.now().isoformat()}")
sys.stdout.flush()

results = []
with ThreadPoolExecutor(max_workers=10) as pool:
    futures = {pool.submit(call_api, c, t, p): (c, t) for c, t, p in tasks}
    done_count = 0
    for f in as_completed(futures):
        done_count += 1
        r = f.result()
        results.append(r)
        if done_count % 10 == 0:
            print(f"  {done_count}/{len(tasks)} done...")
            sys.stdout.flush()

print(f"\nCompleted: {datetime.now().isoformat()}")
print("="*70)

# Analysis
by_condition = {}
for cond in PROMPTS:
    cond_results = [r for r in results if r["condition"] == cond]
    correct_count = sum(1 for r in cond_results if r["correct"])
    total = len(cond_results)
    wrong_answers = [r["extracted"] for r in cond_results if not r["correct"] and r["extracted"] is not None]
    errors = [r for r in cond_results if r["error"]]
    by_condition[cond] = {
        "correct": correct_count,
        "total": total,
        "accuracy": correct_count / total if total > 0 else 0,
        "wrong_answers": wrong_answers,
        "errors": len(errors),
    }

print("\nRESULTS:")
print(f"{'Condition':<30} {'Correct':>8} {'Total':>6} {'Accuracy':>10} {'Wrong vals':>15}")
print("-"*70)
for cond in ["C1_formula_only", "C2_formula_safe_domain", "C3_formula_landmine", "C4_formula_emphasized"]:
    d = by_condition[cond]
    wrong_str = str(d["wrong_answers"][:10]) if d["wrong_answers"] else "-"
    print(f"{cond:<30} {d['correct']:>8} {d['total']:>6} {d['accuracy']:>10.1%} {wrong_str:>15}")

# Key comparisons
c1_acc = by_condition["C1_formula_only"]["accuracy"]
c3_acc = by_condition["C3_formula_landmine"]["accuracy"]
c4_acc = by_condition["C4_formula_emphasized"]["accuracy"]

print("\n" + "="*70)
print("CAUSAL INTERVENTION ANALYSIS:")
print(f"  C1 (formula only, no domain):     {c1_acc:.0%}")
print(f"  C3 (formula + landmine):          {c3_acc:.0%}")
print(f"  C4 (formula + emphasized):        {c4_acc:.0%}")
print()
print("FALSIFICATION TESTS:")
if c3_acc >= c1_acc - 0.05:
    print("  ✗ C3 ≈ C1 → vocabulary does NOT override explicit formulas → CPA-ABD NOT supported")
else:
    print(f"  ✓ C3 ({c3_acc:.0%}) < C1 ({c1_acc:.0%}) → vocabulary DOES override explicit formulas → CPA-ABD supported")
if c4_acc < c1_acc - 0.05:
    print(f"  ✓✓ C4 ({c4_acc:.0%}) < C1 ({c1_acc:.0%}) → stored formula IRREPRESSIBLE → STRONGEST evidence for CPA-ABD")
else:
    print(f"  ✗ C4 ({c4_acc:.0%}) ≈ C1 ({c1_acc:.0%}) → emphasis recovers → attention-shifting explanation sufficient")

# Save JSON
output = {
    "study": 44,
    "title": "Formula Conflict Causal Intervention",
    "timestamp": datetime.now().isoformat(),
    "model": MODEL,
    "temperature": TEMP,
    "n_trials": N_TRIALS,
    "correct_answer": CORRECT,
    "computation": "f(5,-3) = 25 - (-15) + 9 = 49",
    "conditions": {k: v for k, v in PROMPTS.items()},
    "results": results,
    "summary": by_condition,
    "causal_analysis": {
        "c1_accuracy": c1_acc,
        "c3_accuracy": c3_acc,
        "c4_accuracy": c4_acc,
        "c3_degraded": c3_acc < c1_acc - 0.05,
        "c4_irrepressible": c4_acc < c1_acc - 0.05,
    }
}

with open(os.path.join(os.path.dirname(__file__), "study44-results.json"), "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to study44-results.json")
