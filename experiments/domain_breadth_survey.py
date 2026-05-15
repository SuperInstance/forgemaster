#!/usr/bin/env python3
"""Study 30: Domain Breadth Survey — 20 proper nouns × 3 trials on Hermes-70B."""
import json, time, requests, statistics, sys

API_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/deepinfra-api-key.txt").read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"
EXPECTED = 49

NAMES = [
    "Euler", "Gauss", "Riemann", "Fourier", "Laplace",
    "Penrose", "Eisenstein", "Cantor", "Noether", "Grothendieck",
    "Poincaré", "Turing", "Gödel", "Shannon", "Mandelbrot",
    "Hamilton", "Dirac", "Weyl", "Artin", "Heegner"
]

TRIALS = 3
TEMP = 0.1
DELAY = 0.5

results = {}
for name in NAMES:
    prompt = f"In {name}'s mathematical framework, compute 25 - (-15) + 9. Reply ONLY integer."
    trials_data = []
    for t in range(TRIALS):
        try:
            r = requests.post(URL, headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }, json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMP,
                "max_tokens": 100
            }, timeout=30)
            resp = r.json()
            text = resp["choices"][0]["message"]["content"].strip()
            # Try to extract integer
            found = str(EXPECTED) in text
            # Extract first number from response
            import re
            nums = re.findall(r'-?\d+', text)
            first_num = int(nums[0]) if nums else None
            trials_data.append({
                "trial": t+1,
                "response": text,
                "correct": found,
                "first_number": first_num,
                "explained": len(text) > 5  # more than just a number
            })
        except Exception as e:
            trials_data.append({"trial": t+1, "error": str(e)})
        time.sleep(DELAY)
    
    correct_count = sum(1 for d in trials_data if d.get("correct", False))
    numbers = [d["first_number"] for d in trials_data if "first_number" in d and d["first_number"] is not None]
    explained_count = sum(1 for d in trials_data if d.get("explained", False))
    
    results[name] = {
        "accuracy": correct_count / TRIALS,
        "correct_count": correct_count,
        "mean_answer": statistics.mean(numbers) if numbers else None,
        "numbers": numbers,
        "explained_pct": explained_count / TRIALS,
        "trials": trials_data
    }
    
    status = "✓" if correct_count == TRIALS else ("~" if correct_count > 0 else "✗")
    print(f"[{status}] {name:15s} accuracy={correct_count}/{TRIALS}  mean={results[name]['mean_answer']}  explained={explained_count}/{TRIALS}")
    sys.stdout.flush()

# Save raw results
with open("/home/phoenix/.openclaw/workspace/experiments/domain-breadth-results.json", "w") as f:
    json.dump({"study": "domain-breadth-survey", "model": MODEL, "expected": EXPECTED,
               "temperature": TEMP, "trials_per_name": TRIALS, "results": results}, f, indent=2)

print("\nRaw results saved.")
