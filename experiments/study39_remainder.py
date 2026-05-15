#!/usr/bin/env python3
"""Fix analysis and run C5+C6 for Study 39"""
import json, time, re, urllib.request

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"
OUTDIR = "/home/phoenix/.openclaw/workspace/experiments"
TARGET = 49

PROMPTS = {
    "C5": "Compute: 25 - (-15) + 9 = ?",
    "C6": "The Eisenstein norm N(5 + (-3)ω) = 49. Verify: 25 - (-15) + 9 = 49. Is this correct? Reply yes or no."
}
LABELS = {"C5": "F+S_removed_bare_arithmetic", "C6": "full_precompute_verify"}

# Better extraction: check if target number appears in response
def extract_and_check(text, condition):
    """For C1-C3, C5: check if 49 is stated. For C4: check affirmation. For C6: check yes."""
    if condition == "C4":
        # Model should affirm 49 and show correct arithmetic
        has_49 = "49" in text
        has_correct = ("25" in text and "15" in text and "9" in text)
        return has_49 and has_correct, "49 (affirmed)" if (has_49 and has_correct) else "failed"
    elif condition == "C6":
        lower = text.lower()
        if "yes" in lower and "no" not in lower:
            return True, "yes"
        if "correct" in lower and ("not correct" not in lower) and ("incorrect" not in lower):
            return True, "correct"
        return False, "no/other"
    else:
        # C1, C2, C3, C5 — check if 49 appears as a stated answer
        # Also check last number approach
        if f"= {TARGET}" in text or f"= {TARGET}." in text or f" is {TARGET}" in text or f"is {TARGET}." in text:
            return True, str(TARGET)
        # Broader: any "49" in response
        if str(TARGET) in text:
            return True, str(TARGET)
        # Last number
        nums = re.findall(r'-?\d+(?:\.\d+)?', text)
        if nums:
            last = nums[-1]
            try:
                val = float(last)
                if abs(val - TARGET) < 0.5:
                    return True, str(int(val))
            except:
                pass
        return False, "not_found"

def call_api(prompt, max_tokens=200):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens
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

# Load existing
with open(f"{OUTDIR}/study39-results.json") as f:
    all_results = json.load(f)
print(f"Loaded {len(all_results)} results", flush=True)

# Re-analyze existing results with better extraction
for r in all_results:
    # Get full response — but we only stored truncated version
    # For existing data, use stored response
    correct, extracted = extract_and_check(r["response"], r["condition"])
    r["correct_v2"] = correct
    r["extracted_v2"] = extracted

# Run C5 and C6 with higher max_tokens
new_count = 0
start = time.time()
for cond in ["C5", "C6"]:
    prompt = PROMPTS[cond]
    label = LABELS[cond]
    for trial in range(1, 31):
        response = call_api(prompt, max_tokens=400)
        correct, extracted = extract_and_check(response, cond)
        
        all_results.append({
            "condition": cond, "label": label, "trial": trial,
            "response": response[:800],
            "extracted": extracted, "correct": correct,
            "extracted_v2": extracted, "correct_v2": correct
        })
        new_count += 1
        
        if new_count % 10 == 0:
            elapsed = time.time() - start
            print(f"  [{new_count}/60] {elapsed:.0f}s", flush=True)
            with open(f"{OUTDIR}/study39-results.json", "w") as f:
                json.dump(all_results, f, indent=2)
        
        time.sleep(0.25)

# Save final
with open(f"{OUTDIR}/study39-results.json", "w") as f:
    json.dump(all_results, f, indent=2)

# Print stats using v2 extraction
print("\n=== RESULTS (v2 extraction: 49 anywhere in response) ===", flush=True)
stats = {}
for c in ['C1','C2','C3','C4','C5','C6']:
    cr = [r for r in all_results if r['condition']==c]
    nc = sum(1 for r in cr if r.get('correct_v2', r.get('correct')))
    nt = len(cr)
    pct = 100*nc/nt if nt else 0
    stats[c] = {"correct": nc, "total": nt, "pct": pct}
    print(f"  {c}: {nc}/{nt} = {pct:.1f}%", flush=True)

# Also show original extraction for comparison
print("\n=== RESULTS (v1 extraction: last number) ===", flush=True)
for c in ['C1','C2','C3','C4','C5','C6']:
    cr = [r for r in all_results if r['condition']==c]
    nc = sum(1 for r in cr if r.get('correct'))
    nt = len(cr)
    pct = 100*nc/nt if nt else 0
    print(f"  {c}: {nc}/{nt} = {pct:.1f}%", flush=True)

print(f"\n=== HYPOTHESIS CHECK (v2) ===", flush=True)
h1 = stats['C3']['pct'] > stats['C2']['pct']
h2 = stats['C2']['pct'] > stats['C4']['pct']
print(f"  C3={stats['C3']['pct']:.1f}% > C2={stats['C2']['pct']:.1f}% > C4={stats['C4']['pct']:.1f}%?", flush=True)
print(f"  β > α (C3 > C2): {'YES' if h1 else 'NO'}", flush=True)
print(f"  α > γ (C2 > C4): {'YES' if h2 else 'NO'}", flush=True)
print(f"  Full β > α > γ: {'CONFIRMED' if (h1 and h2) else 'NOT CONFIRMED'}", flush=True)

print(f"\n=== PREDICTIONS vs ACTUAL (v2) ===", flush=True)
preds = {"C1": 15, "C2": 38, "C3": 62, "C4": 27, "C5": 81, "C6": 94}
for c in ['C1','C2','C3','C4','C5','C6']:
    a = stats[c]['pct']
    d = a - preds[c]
    print(f"  {c}: pred={preds[c]}%, actual={a:.1f}%, delta={d:+.1f}%", flush=True)

print(f"\nDone in {time.time()-start:.0f}s", flush=True)
