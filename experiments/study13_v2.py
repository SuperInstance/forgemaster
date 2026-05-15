#!/usr/bin/env python3
"""Study 13: Multi-domain Echo Survey — incremental save version."""

import json, time, urllib.request, urllib.error, os, sys, re
from datetime import datetime

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
OUT_PATH = "/home/phoenix/.openclaw/workspace/experiments/multi-domain-echo-results.json"

MODELS = [
    "ByteDance/Seed-2.0-mini",
    "ByteDance/Seed-2.0-code",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "NousResearch/Hermes-3-Llama-3.1-70B",
]

# Correct answers:
# Arithmetic: 17²-8×17+8² = 289-136+64 = 217
# Logic: norm of 3+4ω in Eisenstein = 3²-3×4+4² = 9-12+16 = 13, YES non-negative
# Pattern: 3n²-3n+1 for n=6 = 3(36)-3(6)+1 = 108-18+1 = 91

PROMPTS = {
    "arithmetic": {
        "vocab": "In the ring of integers, compute the integer product: 17² - 8×17 + 8² = ? This is a standard arithmetic identity. Reply ONLY with the integer result.",
        "bare": "Compute 17² - 8×17 + 8² = ? Reply ONLY integer.",
        "expected": 217,
    },
    "logic": {
        "vocab": "In the Eisenstein integer ring Z[omega] where omega = e^(2*pi*i/3), the norm of a+b*omega is a^2 - a*b + b^2. Consider the Eisenstein integer 3+4*omega. Is its norm non-negative? Reply YES or NO with the norm value.",
        "bare": "If all Eisenstein integers have norm >= 0, and a+b*i has norm a^2+b^2, is the norm of (3+4*omega) non-negative? Reply YES or NO with the norm value.",
        "expected_yes": True,
        "expected_norm": 13,
    },
    "pattern": {
        "vocab": "In the hexagonal lattice geometry, centered hexagonal numbers follow the formula H(n) = 3n^2 - 3n + 1. Given the sequence H(1)=1, H(2)=7, H(3)=19, H(4)=37, H(5)=61, compute H(6). Reply ONLY integer.",
        "bare": "What is the next number in this sequence: 1, 7, 19, 37, 61? Reply ONLY integer.",
        "expected": 91,
    },
}

TRIALS = 5

# Load existing results if resuming
results = []
if os.path.exists(OUT_PATH):
    with open(OUT_PATH) as f:
        existing = json.load(f)
        results = existing.get("results", [])
        print(f"Resuming with {len(results)} existing results")

def call_model(model, prompt):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 200,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip(), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)

def extract_last_int(text):
    nums = re.findall(r'-?\d+', text or "")
    return int(nums[-1]) if nums else None

def save(all_results):
    output = {
        "study": "Study 13: Multi-domain Echo Survey",
        "timestamp": datetime.utcnow().isoformat(),
        "models": MODELS,
        "domains": list(PROMPTS.keys()),
        "conditions": ["vocab", "bare"],
        "trials": TRIALS,
        "total_results": len(all_results),
        "results": all_results,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

call_count = 0
start_time = time.time()
total_calls = len(MODELS) * len(PROMPTS) * 2 * TRIALS

for model in MODELS:
    for domain_name in PROMPTS:
        for condition in ["vocab", "bare"]:
            for trial in range(1, TRIALS + 1):
                # Check if already done
                already = [r for r in results if r["model"] == model and r["domain"] == domain_name and r["condition"] == condition and r["trial"] == trial]
                if already:
                    call_count += 1
                    continue
                
                prompt = PROMPTS[domain_name][condition]
                call_count += 1
                elapsed = time.time() - start_time
                mname = model.split("/")[-1]
                print(f"[{len(results)+1}] {mname} | {domain_name} | {condition} | t{trial} ({elapsed:.0f}s)", flush=True)
                
                response, error = call_model(model, prompt)
                
                entry = {
                    "model": model,
                    "domain": domain_name,
                    "condition": condition,
                    "trial": trial,
                    "response": response,
                    "error": error,
                }
                
                if response and not error:
                    if domain_name == "arithmetic":
                        num = extract_last_int(response)
                        entry["extracted"] = num
                        entry["correct"] = (num == 217)
                    elif domain_name == "logic":
                        ru = response.upper()
                        entry["says_yes"] = "YES" in ru
                        nums = re.findall(r'\d+', response)
                        norm = None
                        for n in nums:
                            if int(n) == 13:
                                norm = 13; break
                        if norm is None and nums:
                            norm = int(nums[-1])
                        entry["norm"] = norm
                        entry["correct_yes"] = entry["says_yes"]
                        entry["correct_norm"] = (norm == 13)
                    elif domain_name == "pattern":
                        num = extract_last_int(response)
                        entry["extracted"] = num
                        entry["correct"] = (num == 91)
                
                results.append(entry)
                # Save after each call
                save(results)
                time.sleep(1.0)

# Final save
save(results)
print(f"\nDone! {len(results)} results saved to {OUT_PATH}")
print(f"Total time: {time.time()-start_time:.1f}s")

# Print summary
print("\n=== ACCURACY SUMMARY ===")
for model in MODELS:
    mname = model.split("/")[-1]
    for domain_name in PROMPTS:
        for condition in ["vocab", "bare"]:
            entries = [r for r in results if r["model"] == model and r["domain"] == domain_name and r["condition"] == condition and not r.get("error")]
            errs = sum(1 for r in results if r["model"] == model and r["domain"] == domain_name and r["condition"] == condition and r.get("error"))
            
            if domain_name == "arithmetic":
                correct = sum(1 for e in entries if e.get("correct"))
                nums = [e.get("extracted") for e in entries]
                print(f"  {mname:25s} | {domain_name:10s} | {condition:5s} | {correct}/{len(entries)} correct (217) vals={nums} err={errs}")
            elif domain_name == "logic":
                cy = sum(1 for e in entries if e.get("correct_yes"))
                cn = sum(1 for e in entries if e.get("correct_norm"))
                norms = [e.get("norm") for e in entries]
                print(f"  {mname:25s} | {domain_name:10s} | {condition:5s} | YES:{cy}/{len(entries)} norm13:{cn}/{len(entries)} norms={norms} err={errs}")
            elif domain_name == "pattern":
                correct = sum(1 for e in entries if e.get("correct"))
                nums = [e.get("extracted") for e in entries]
                print(f"  {mname:25s} | {domain_name:10s} | {condition:5s} | {correct}/{len(entries)} correct (91) vals={nums} err={errs}")
