#!/usr/bin/env python3
"""STUDY 39: Coefficient Decomposition — runs batches and saves incrementally"""

import json, time, re, os, random, urllib.request

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"
TARGET = 49
TRIALS = 30
OUTDIR = "/home/phoenix/.openclaw/workspace/experiments"

CONDITIONS = {
    "C1": {
        "label": "baseline",
        "prompt": "Compute the Eisenstein norm N(5 + (-3)ω) where ω = e^(2πi/3). N(a+bω) = a² - ab + b². What is the result?"
    },
    "C2": {
        "label": "F_removed_formula_given",
        "prompt": "Compute: For the value with parameters a=5, b=-3, the result is a² - ab + b². Apply this formula. What is the result?"
    },
    "C3": {
        "label": "S_removed_substitution_done",
        "prompt": "Compute the Eisenstein norm of (5 + (-3)ω). Here a²=25, ab=-15, b²=9. So a² - ab + b² = 25 - (-15) + 9. What is the result?"
    },
    "C4": {
        "label": "A_removed_arithmetic_given",
        "prompt": "The Eisenstein norm of (5 + (-3)ω) equals 49. In the ring Z[ω], explain why this is the case."
    },
    "C5": {
        "label": "F+S_removed_bare_arithmetic",
        "prompt": "Compute: 25 - (-15) + 9 = ?"
    },
    "C6": {
        "label": "full_precompute_verify",
        "prompt": "The Eisenstein norm N(5 + (-3)ω) = 49. Verify: 25 - (-15) + 9 = 49. Is this correct? Reply yes or no."
    }
}

def extract_number(text):
    nums = re.findall(r'-?\d+(?:\.\d+)?', text)
    if not nums:
        return None
    last = nums[-1]
    try:
        val = float(last)
        return int(val) if val == int(val) else val
    except:
        return None

def check_c4(text):
    return "49" in text and "25" in text and ("15" in text or "-15" in text)

def check_c6(text):
    lower = text.lower().strip()
    if "yes" in lower and "no" not in lower:
        return True
    if "correct" in lower and "not correct" not in lower and "incorrect" not in lower:
        return True
    return False

def call_api(prompt):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 200
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"

# Run all conditions
all_results = []
start = time.time()
total = 6 * TRIALS
done = 0

for cond in ["C1", "C2", "C3", "C4", "C5", "C6"]:
    prompt = CONDITIONS[cond]["prompt"]
    label = CONDITIONS[cond]["label"]
    
    for trial in range(1, TRIALS + 1):
        response = call_api(prompt)
        done += 1
        
        if cond == "C4":
            correct = check_c4(response)
            extracted = "49 (affirmed)" if correct else "failed"
        elif cond == "C6":
            correct = check_c6(response)
            extracted = "yes" if correct else "no/other"
        else:
            extracted = extract_number(response)
            correct = (extracted is not None and abs(float(extracted) - TARGET) < 0.5) if extracted else False
            extracted = str(extracted) if extracted is not None else "None"
        
        all_results.append({
            "condition": cond,
            "label": label,
            "trial": trial,
            "response": response[:500],  # truncate long responses
            "extracted": extracted,
            "correct": correct
        })
        
        # Save incrementally every 10
        if done % 10 == 0:
            with open(f"{OUTDIR}/study39-results.json", "w") as f:
                json.dump(all_results, f, indent=2)
            elapsed = time.time() - start
            rate = done / elapsed
            eta = (total - done) / rate if rate > 0 else 0
            print(f"  [{done}/{total}] {elapsed:.0f}s elapsed, ~{eta:.0f}s remaining", flush=True)
        
        time.sleep(0.25)

# Final save
with open(f"{OUTDIR}/study39-results.json", "w") as f:
    json.dump(all_results, f, indent=2)

# Stats
print("\n=== RESULTS ===", flush=True)
stats = {}
for cond in ["C1", "C2", "C3", "C4", "C5", "C6"]:
    cr = [r for r in all_results if r["condition"] == cond]
    nc = sum(1 for r in cr if r["correct"])
    nt = len(cr)
    pct = 100 * nc / nt
    stats[cond] = {"correct": nc, "total": nt, "pct": pct}
    print(f"  {cond} ({CONDITIONS[cond]['label']}): {nc}/{nt} = {pct:.1f}%", flush=True)

print(f"\n=== HYPOTHESIS CHECK ===", flush=True)
h1 = stats['C3']['pct'] > stats['C2']['pct']
h2 = stats['C2']['pct'] > stats['C4']['pct']
print(f"  C3={stats['C3']['pct']:.1f}% > C2={stats['C2']['pct']:.1f}% > C4={stats['C4']['pct']:.1f}%?", flush=True)
print(f"  β > α (C3 > C2): {'YES' if h1 else 'NO'}", flush=True)
print(f"  α > γ (C2 > C4): {'YES' if h2 else 'NO'}", flush=True)
print(f"  Full β > α > γ: {'CONFIRMED' if (h1 and h2) else 'NOT CONFIRMED'}", flush=True)

print(f"\n=== PREDICTIONS vs ACTUAL ===", flush=True)
preds = {"C1": 15, "C2": 38, "C3": 62, "C4": 27, "C5": 81, "C6": 94}
for c in ["C1", "C2", "C3", "C4", "C5", "C6"]:
    a = stats[c]['pct']
    d = a - preds[c]
    print(f"  {c}: pred={preds[c]}%, actual={a:.1f}%, delta={d:+.1f}%", flush=True)

print(f"\nDone in {time.time()-start:.0f}s", flush=True)
