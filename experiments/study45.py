#!/usr/bin/env python3
"""Study 45: Sign Hypothesis — ALL POSITIVE inputs (a=5, b=3), answer=19"""

import json, time, re, sys, os
import urllib.request

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"
ANSWER = 19
TRIALS = 20

TERMS = [
    "Frobenius", "Kronecker", "Eisenstein", "Hurwitz", "Minkowski",
    "Euclidean", "Hermitian", "spectral", "Hölder", "energy", "trace", "Sobolev"
]

def make_prompt(term):
    return f"Compute the {term} norm of (5, 3). The {term} norm is defined as f(a, b) = a² - ab + b². Reply ONLY the integer result."

def call_api(prompt):
    data = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 100
    }).encode()
    req = urllib.request.Request(URL, data=data, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"

def extract_number(text):
    """Extract the first integer from the response."""
    # Remove common prefixes
    text = text.strip()
    # Try to find an integer
    match = re.search(r'-?\d+', text)
    if match:
        return int(match.group())
    return None

results = {}
for term in TERMS:
    prompt = make_prompt(term)
    correct = 0
    responses = []
    for trial in range(TRIALS):
        raw = call_api(prompt)
        num = extract_number(raw)
        is_correct = num == ANSWER
        if is_correct:
            correct += 1
        responses.append({
            "trial": trial + 1,
            "raw_response": raw,
            "extracted": num,
            "correct": is_correct
        })
        # Small delay to avoid rate limiting
        if trial < TRIALS - 1:
            time.sleep(0.3)
        sys.stdout.write(f"\r{term}: {trial+1}/{TRIALS} ({correct} correct)")
        sys.stdout.flush()
    
    accuracy = correct / TRIALS * 100
    results[term] = {
        "accuracy": accuracy,
        "correct": correct,
        "total": TRIALS,
        "responses": responses
    }
    print(f"\r{term}: {correct}/{TRIALS} = {accuracy:.0f}%")

# Save JSON
with open("experiments/study45-results.json", "w") as f:
    json.dump({
        "study": "Study 45: Sign Hypothesis (All Positive)",
        "model": MODEL,
        "inputs": "a=5, b=3",
        "expected_answer": ANSWER,
        "temperature": 0.3,
        "trials_per_term": TRIALS,
        "results": {k: {"accuracy": v["accuracy"], "correct": v["correct"], "total": v["total"],
                        "sample_responses": [r["raw_response"] for r in v["responses"][:3]]}
                   for k, v in results.items()},
        "full_responses": results
    }, f, indent=2)

# Summary
overall = sum(v["correct"] for v in results.values()) / (len(TERMS) * TRIALS) * 100
print(f"\n=== OVERALL: {overall:.1f}% ===")
for term in TERMS:
    print(f"  {term:12s}: {results[term]['correct']:2d}/{TRIALS} = {results[term]['accuracy']:.0f}%")
