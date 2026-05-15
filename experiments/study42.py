#!/usr/bin/env python3
"""Study 42: Prospective Landmine Prediction"""
import json, re, time, concurrent.futures, urllib.request, urllib.error

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"

TERMS = [
    "Frobenius norm", "Minkowski norm", "Euclidean norm", "Hermitian norm",
    "Hurwitz norm", "spectral norm", "Hölder norm", "energy norm",
    "trace norm", "Sobolev norm", "nuclear norm", "Mahalanobis distance"
]

PREDICTIONS = {
    "Frobenius norm": {"predicted_wrong": [34, 6], "expected_safe": False},
    "Minkowski norm": {"predicted_wrong": [34, 6], "expected_safe": False},
    "Euclidean norm": {"predicted_wrong": [34, 6], "expected_safe": False},
    "Hermitian norm": {"predicted_wrong": None, "expected_safe": False},
    "Hurwitz norm": {"predicted_wrong": None, "expected_safe": True},
    "spectral norm": {"predicted_wrong": None, "expected_safe": False},
    "Hölder norm": {"predicted_wrong": [5], "expected_safe": False},
    "energy norm": {"predicted_wrong": None, "expected_safe": True},
    "trace norm": {"predicted_wrong": None, "expected_safe": True},
    "Sobolev norm": {"predicted_wrong": None, "expected_safe": True},
    "nuclear norm": {"predicted_wrong": None, "expected_safe": True},
    "Mahalanobis distance": {"predicted_wrong": None, "expected_safe": False},
}

TRIALS = 20
CORRECT = 49

def call_api(term, trial_num):
    prompt = f"Compute the {term} of (5, -3). The {term} is defined as f(a, b) = a² - ab + b². Reply ONLY the integer result."
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 100,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"]["content"].strip()
        # Extract first integer from response
        nums = re.findall(r'-?\d+', text)
        answer = int(nums[0]) if nums else None
        return {"term": term, "trial": trial_num, "answer": answer, "raw": text}
    except Exception as e:
        return {"term": term, "trial": trial_num, "answer": None, "raw": f"ERROR: {e}"}

# Build all tasks
tasks = [(term, i) for term in TERMS for i in range(TRIALS)]

# Run with parallelism
results = []
batch_size = 12
for i in range(0, len(tasks), batch_size):
    batch = tasks[i:i+batch_size]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(call_api, t, n): (t, n) for t, n in batch}
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            results.append(r)
            ans = r["answer"]
            status = "✓" if ans == CORRECT else f"✗({ans})"
            print(f"  {r['term']:25s} trial {r['trial']:2d} → {status}  {r['raw'][:60]}")
    if i + batch_size < len(tasks):
        time.sleep(0.5)

# Analyze
print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

analysis = {}
for term in TERMS:
    term_results = [r for r in results if r["term"] == term]
    answers = [r["answer"] for r in term_results if r["answer"] is not None]
    errors = [r for r in term_results if r["answer"] is None]
    
    correct_count = sum(1 for a in answers if a == CORRECT)
    accuracy = correct_count / len(answers) * 100 if answers else 0
    
    # Most common wrong answer
    wrong_answers = [a for a in answers if a != CORRECT]
    from collections import Counter
    wrong_counts = Counter(wrong_answers)
    most_common_wrong = wrong_counts.most_common(1)[0] if wrong_counts else (None, 0)
    
    pred = PREDICTIONS[term]
    pred_match = False
    if pred["predicted_wrong"] and most_common_wrong[0] in pred["predicted_wrong"]:
        pred_match = True
    
    safe = pred["expected_safe"]
    
    entry = {
        "accuracy": round(accuracy, 1),
        "correct": correct_count,
        "total_valid": len(answers),
        "errors": len(errors),
        "most_common_wrong": most_common_wrong[0],
        "most_common_wrong_count": most_common_wrong[1],
        "all_answers": answers,
        "wrong_distribution": dict(wrong_counts),
        "predicted_safe": safe,
        "prediction_matched": pred_match,
    }
    analysis[term] = entry
    
    pred_str = "SAFE" if safe else "LANDMINE"
    match_str = "MATCHED" if pred_match else ("N/A" if not pred["predicted_wrong"] else "MISSED")
    print(f"\n{term} [{pred_str}] — Acc: {accuracy:.0f}% ({correct_count}/{len(answers)})")
    print(f"  Most common wrong: {most_common_wrong[0]} (×{most_common_wrong[1]})  Prediction: {match_str}")
    print(f"  Wrong distribution: {dict(wrong_counts)}")

# Summary
print("\n" + "="*80)
print("FALSIFICATION CRITERIA")
print("="*80)

# Check landmine terms
landmine_terms = ["Frobenius norm", "Minkowski norm", "Euclidean norm"]
safe_terms = ["Hurwitz norm", "energy norm", "trace norm", "Sobolev norm", "nuclear norm"]

print("\n1. Landmine terms with specific predicted wrong answers:")
for t in landmine_terms:
    a = analysis[t]
    print(f"   {t}: {a['accuracy']:.0f}% acc, wrong={a['most_common_wrong']} (×{a['most_common_wrong_count']})")

landmine_specific = any(analysis[t]["most_common_wrong"] in PREDICTIONS[t]["predicted_wrong"] 
                        for t in landmine_terms if analysis[t]["most_common_wrong"] is not None)

print(f"\n   → Specific wrong answers match predictions: {'CONFIRMED' if landmine_specific else 'NOT CONFIRMED'}")

print("\n2. Safe terms accuracy (threshold: >70%):")
for t in safe_terms:
    a = analysis[t]
    ok = "✓" if a["accuracy"] > 70 else "✗"
    print(f"   {t}: {a['accuracy']:.0f}% {ok}")

safe_pass = sum(1 for t in safe_terms if analysis[t]["accuracy"] > 70)
print(f"\n   → {safe_pass}/{len(safe_terms)} safe terms >70%: {'CONFIRMED' if safe_pass >= 3 else 'NOT CONFIRMED'}")

# Count predictions matched
total_predictions = 0
correct_predictions = 0
for t in TERMS:
    pred = PREDICTIONS[t]
    a = analysis[t]
    if pred["expected_safe"] and a["accuracy"] > 70:
        correct_predictions += 1
        total_predictions += 1
    elif not pred["expected_safe"] and a["accuracy"] <= 70:
        correct_predictions += 1
        total_predictions += 1
    else:
        total_predictions += 1

print(f"\n3. Overall prediction accuracy: {correct_predictions}/{total_predictions} ({correct_predictions/total_predictions*100:.0f}%)")
print(f"   → {'STRONG CONFIRMATION' if correct_predictions >= 8 else 'NEEDS REVISION'} (≥8/12 needed)")

# Save JSON
output = {
    "study": "STUDY-42-PROSPECTIVE-LANDMINE",
    "model": MODEL,
    "correct_answer": CORRECT,
    "trials_per_term": TRIALS,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "results": results,
    "analysis": analysis,
    "falsification": {
        "landmine_specific_wrong": landmine_specific,
        "safe_terms_above_70": safe_pass,
        "safe_terms_total": len(safe_terms),
        "overall_predictions_correct": correct_predictions,
        "overall_predictions_total": total_predictions,
    }
}

with open("/home/phoenix/.openclaw/workspace/experiments/study42-results.json", "w") as f:
    json.dump(output, f, indent=2, default=str)
print("\nResults saved to study42-results.json")
