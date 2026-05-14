#!/usr/bin/env python3
"""Longitudinal stability study: ask same question 20x, measure answer distribution."""

import requests
import json
import time
import math
from collections import Counter
from datetime import datetime

URL = "http://localhost:11434/api/chat"
MODEL = "phi4-mini"
N = 20

def query(prompt, num_predict=60, timeout=120):
    resp = requests.post(URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": num_predict}
    }, timeout=timeout)
    return resp.json()["message"]["content"].strip()

def entropy(dist):
    """Shannon entropy of a distribution (list of counts)."""
    total = sum(dist)
    if total == 0:
        return 0.0
    return -sum((c/total) * math.log2(c/total) for c in dist if c > 0)

def analyze(answers, label):
    counter = Counter(answers)
    n_unique = len(counter)
    modal, modal_count = counter.most_common(1)[0]
    agreement = modal_count / len(answers) * 100
    ent = entropy(list(counter.values()))
    
    print(f"\n{'='*60}")
    print(f"QUESTION: {label}")
    print(f"{'='*60}")
    print(f"Total trials: {len(answers)}")
    print(f"Unique answers: {n_unique}")
    print(f"Modal answer: '{modal}' ({modal_count}/{len(answers)} = {agreement:.1f}%)")
    print(f"Shannon entropy: {ent:.3f} bits")
    print(f"\nFull distribution:")
    for ans, cnt in counter.most_common():
        bar = '█' * cnt
        print(f"  '{ans}': {cnt:2d} {bar}")
    print()
    
    return {
        "label": label,
        "n": len(answers),
        "unique": n_unique,
        "modal": modal,
        "modal_count": modal_count,
        "agreement_pct": round(agreement, 1),
        "entropy_bits": round(ent, 3),
        "distribution": dict(counter.most_common()),
        "raw_answers": answers
    }

# === QUESTIONS ===
questions = [
    ("Q1: Simple math (3² + (-1)²)", 
     "What is 3² + (-1)²? Reply with ONLY the integer."),
    
    ("Q2: Eisenstein norm (3,-1)",
     "Compute the Eisenstein norm N(3,-1) = a²-ab+b². Reply with ONLY the integer."),
    
    ("Q3: Hex vs Square lattice (subjective)",
     "Is it more efficient to use a hex lattice or square lattice for 2D covering? Reply hex or square."),
    
    ("Q4: Death Zone variant (4,-2)",
     "Compute the Eisenstein norm of (4, -2).\n\nDATA: N(a,b) = a² - ab + b², a=4, b=-2\na² = 16, ab = -8, b² = 4\n\nDONE: Reply with ONLY the integer answer."),
    
    ("Q5: Clean variant (4,-2)",
     "Compute the Eisenstein norm of (4, -2).\n\nDATA: N(a,b) = a² - ab + b², a=4, b=-2\n\nDONE: Reply with ONLY the integer answer."),
]

all_results = []
for label, prompt in questions:
    answers = []
    for i in range(N):
        t0 = time.time()
        try:
            ans = query(prompt)
        except Exception as e:
            ans = f"ERROR: {e}"
        dt = time.time() - t0
        print(f"  [{label}] trial {i+1:2d}/{N}: '{ans}' ({dt:.1f}s)")
        answers.append(ans)
        # Small delay to avoid overwhelming Ollama
        time.sleep(0.5)
    
    result = analyze(answers, label)
    all_results.append(result)

# === COMPARISON: Death Zone vs Clean ===
print(f"\n{'='*60}")
print("DEATH ZONE vs CLEAN COMPARISON")
print(f"{'='*60}")
dz = all_results[3]  # Q4
cl = all_results[4]  # Q5
print(f"Death Zone (with intermediate values):")
print(f"  Distribution: {dz['distribution']}")
print(f"  Entropy: {dz['entropy_bits']} bits, Agreement: {dz['agreement_pct']}%")
print(f"\nClean (no intermediate values):")
print(f"  Distribution: {cl['distribution']}")
print(f"  Entropy: {cl['entropy_bits']} bits, Agreement: {cl['agreement_pct']}%")
print(f"\nCorrect answer for both: 28")
dz_correct = sum(1 for a in dz['raw_answers'] if '28' in a)
cl_correct = sum(1 for a in cl['raw_answers'] if '28' in a)
print(f"Death Zone correct rate: {dz_correct}/{N} = {dz_correct/N*100:.0f}%")
print(f"Clean correct rate: {cl_correct}/{N} = {cl_correct/N*100:.0f}%")
print(f"\nINTERFERENCE PATTERN:")
print(f"  Death Zone is {'DETERMINISTIC' if dz_correct in [0, N] else 'PROBABILISTIC'} failure")
print(f"  Clean is {'DETERMINISTIC' if cl_correct in [0, N] else 'PROBABILISTIC'}")

# Save raw data as JSON
with open("/home/phoenix/.openclaw/workspace/experiments/longitudinal_raw.json", "w") as f:
    # Remove raw_answers for JSON (too verbose)
    for r in all_results:
        r.pop("raw_answers", None)
    json.dump({"timestamp": datetime.now().isoformat(), "results": all_results}, f, indent=2)

print("\nRaw data saved to experiments/longitudinal_raw.json")
