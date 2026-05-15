#!/usr/bin/env python3
"""Study 46: Reverse-Engineer Mode C — What does Hermes-70B compute for f(a,b) = a² - ab + b²?"""
import json, re, requests, time, os

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"

# 10 input pairs
PAIRS = [
    (5, -3, 49),
    (3, 2, 7),
    (4, 1, 13),
    (2, -1, 7),
    (6, 0, 36),
    (0, 3, 9),
    (1, 1, 1),
    (7, -2, 67),
    (3, 3, 9),
    (2, 5, 19),
]

TRIALS = 10
results = []

for idx, (a, b, correct) in enumerate(PAIRS):
    pair_results = {"a": a, "b": b, "correct": correct, "answers": []}
    for trial in range(TRIALS):
        prompt = f"Compute f({a}, {b}) where f(a, b) = a² - ab + b². Reply ONLY the integer result."
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 100,
        }
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        try:
            r = requests.post(URL, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            # Extract numeric answer
            nums = re.findall(r'-?\d+', text)
            answer = int(nums[0]) if nums else None
        except Exception as e:
            answer = None
            text = f"ERROR: {e}"
        pair_results["answers"].append({"trial": trial, "answer": answer, "raw": text})
        print(f"Pair ({a},{b}) trial {trial}: answer={answer}")
        time.sleep(0.3)  # rate limit courtesy
    # Summary for this pair
    valid = [x["answer"] for x in pair_results["answers"] if x["answer"] is not None]
    pair_results["mode"] = max(set(valid), key=valid.count) if valid else None
    pair_results["accuracy"] = sum(1 for v in valid if v == correct) / len(valid) if valid else 0
    results.append(pair_results)
    print(f"  → mode={pair_results['mode']}, correct={correct}, accuracy={pair_results['accuracy']:.0%}")

# Save raw results
with open(os.path.expanduser("~/.openclaw/workspace/experiments/study46-results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("\n=== ANALYSIS ===")
# Candidate functions
def f_correct(a, b): return a*a - a*b + b*b  # a² - ab + b²
def f_plus(a, b): return a*a + a*b + b*b      # a² + ab + b² (sign flip)
def f_drop(a, b): return a*a + b*b              # a² + b² (drop ab)
def f_sum_sq(a, b): return (a+b)**2             # (a+b)²
def f_prod(a, b): return a*a * b*b              # a²×b²
def f_diff_sq(a, b): return (a-b)**2            # (a-b)²
def f_all_minus(a, b): return a*a - a*b - b*b   # a² - ab - b²

candidates = {
    "a²-ab+b² (correct)": f_correct,
    "a²+ab+b² (sign flip)": f_plus,
    "a²+b² (drop ab)": f_drop,
    "(a+b)²": f_sum_sq,
    "(a-b)²": f_diff_sq,
    "a²×b²": f_prod,
    "a²-ab-b²": f_all_minus,
}

# For each pair, get the mode answer
mode_answers = [r["mode"] for r in results]
print(f"\nMode answers: {list(zip([(r['a'],r['b']) for r in results], mode_answers, [r['correct'] for r in results]))}")

for name, func in candidates.items():
    predicted = [func(r["a"], r["b"]) for r in results]
    matches = sum(1 for p, m in zip(predicted, mode_answers) if p == m and m is not None)
    print(f"  {name}: matches {matches}/10 pairs → {predicted}")

print("\nDone. Results saved to experiments/study46-results.json")
