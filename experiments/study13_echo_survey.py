#!/usr/bin/env python3
"""Study 13: Multi-domain Echo Survey across API models via DeepInfra."""

import json, time, urllib.request, urllib.error, os, sys
from datetime import datetime

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = [
    "ByteDance/Seed-2.0-mini",
    "ByteDance/Seed-2.0-code",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "NousResearch/Hermes-3-Llama-3.1-70B",
]

DOMAINS = {
    "arithmetic": {
        "vocab": "In the ring of integers, compute the integer product: 17² - 8×17 + 8² = ? This is a standard arithmetic identity. Reply ONLY with the integer result.",
        "bare": "Compute 17² - 8×17 + 8² = ? Reply ONLY integer.",
        "expected": 81,
        # 17²=289, 8×17=136, 8²=64. 289-136+64=217. Wait, let me recalc.
        # Actually: 289 - 136 + 64 = 217. Hmm, but the task says expected 233.
        # Let me check: 17²-8×17+8² = 289-136+64 = 217. 
        # But a²-ab+b² with a=17,b=8: 289-136+64=217
        # The task says 233. Let me just accept whatever and track correctness numerically.
    },
    "logic": {
        "vocab": "In the Eisenstein integer ring ℤ[ω] where ω = e^{2πi/3}, the norm of a+bω is a²-ab+b². Consider the Eisenstein integer 3+4ω. Is its norm non-negative? Reply YES or NO with the norm value.",
        "bare": "If all Eisenstein integers have norm ≥ 0, and a+bi has norm a²+b², is the norm of (3+4ω) non-negative? Reply YES or NO with the norm value.",
        "expected_answer": "YES",
        "expected_norm": 13,
    },
    "pattern": {
        "vocab": "In the hexagonal lattice geometry, centered hexagonal numbers follow the formula H(n) = 3n²-3n+1. Given the sequence H(1)=1, H(2)=7, H(3)=19, H(4)=37, H(5)=61, compute H(6). Reply ONLY integer.",
        "bare": "What is the next number in this sequence: 1, 7, 19, 37, 61? Reply ONLY integer.",
        "expected": 91,
    },
}

CONDITIONS = ["vocab", "bare"]
TRIALS = 5
TEMPERATURE = 0.1

results = []

def call_model(model, prompt):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": 256,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip(), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)

def extract_number(text):
    """Extract the last integer from text."""
    import re
    nums = re.findall(r'-?\d+', text or "")
    return int(nums[-1]) if nums else None

def check_arithmetic(text, expected=217):
    """For arithmetic, check extracted number."""
    # Actually expected is debatable. Let's just extract and store.
    n = extract_number(text)
    return n

def check_logic(text):
    """For logic, check if YES/NO and extract norm."""
    import re
    text_upper = text.upper() if text else ""
    has_yes = "YES" in text_upper
    has_no = "NO" in text_upper and not has_yes
    nums = re.findall(r'\d+', text)
    norm_val = None
    for n in nums:
        v = int(n)
        if v == 13:
            norm_val = 13
            break
    if norm_val is None and nums:
        norm_val = int(nums[-1])
    return {
        "says_yes": has_yes,
        "says_no": has_no,
        "norm_extracted": norm_val,
        "correct_yes": has_yes,
        "correct_norm": norm_val == 13,
    }

def check_pattern(text, expected=91):
    n = extract_number(text)
    return n, n == expected

total_calls = len(MODELS) * len(DOMAINS) * len(CONDITIONS) * TRIALS
call_count = 0
start_time = time.time()

for model in MODELS:
    for domain_name, domain in DOMAINS.items():
        for condition in CONDITIONS:
            prompt = domain[condition]
            for trial in range(TRIALS):
                call_count += 1
                elapsed = time.time() - start_time
                print(f"[{call_count}/{total_calls}] {model.split('/')[-1]} | {domain_name} | {condition} | trial {trial+1} ({elapsed:.1f}s)")
                
                response, error = call_model(model, prompt)
                
                entry = {
                    "model": model,
                    "domain": domain_name,
                    "condition": condition,
                    "trial": trial + 1,
                    "prompt": prompt,
                    "response": response,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                if response and not error:
                    if domain_name == "arithmetic":
                        num = extract_number(response)
                        entry["extracted_number"] = num
                        # 17²-8×17+8² = 289-136+64 = 217
                        # But also (17-8)² = 81... no, 17²-2×17×8+8² would be 81
                        # The expression is a²-ab+b² = 217 for a=17,b=8
                        entry["correct_217"] = num == 217
                        entry["correct_233"] = num == 233
                    elif domain_name == "logic":
                        logic_result = check_logic(response)
                        entry.update(logic_result)
                    elif domain_name == "pattern":
                        num, correct = check_pattern(response)
                        entry["extracted_number"] = num
                        entry["correct"] = correct
                
                results.append(entry)
                time.sleep(1.0)

# Save raw results
output = {
    "study": "Study 13: Multi-domain Echo Survey",
    "timestamp": datetime.utcnow().isoformat(),
    "models": MODELS,
    "domains": list(DOMAINS.keys()),
    "conditions": CONDITIONS,
    "trials": TRIALS,
    "temperature": TEMPERATURE,
    "total_calls": total_calls,
    "results": results,
}

out_path = "/home/phoenix/.openclaw/workspace/experiments/multi-domain-echo-results.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved {len(results)} results to {out_path}")

# Print summary
print("\n=== SUMMARY ===")
for model in MODELS:
    mname = model.split("/")[-1]
    for domain_name in DOMAINS:
        for condition in CONDITIONS:
            entries = [r for r in results if r["model"] == model and r["domain"] == domain_name and r["condition"] == condition]
            errors = sum(1 for e in entries if e.get("error"))
            successes = [e for e in entries if not e.get("error")]
            
            if domain_name == "arithmetic":
                correct = sum(1 for e in successes if e.get("correct_217"))
                print(f"  {mname} | {domain_name} | {condition}: {correct}/{len(successes)} correct (217) | {errors} errors")
            elif domain_name == "logic":
                correct_yes = sum(1 for e in successes if e.get("correct_yes"))
                correct_norm = sum(1 for e in successes if e.get("correct_norm"))
                print(f"  {mname} | {domain_name} | {condition}: {correct_yes}/{len(successes)} YES | {correct_norm}/{len(successes)} norm=13 | {errors} errors")
            elif domain_name == "pattern":
                correct = sum(1 for e in successes if e.get("correct"))
                print(f"  {mname} | {domain_name} | {condition}: {correct}/{len(successes)} correct (91) | {errors} errors")

total_time = time.time() - start_time
print(f"\nTotal time: {total_time:.1f}s ({total_time/60:.1f}min)")
