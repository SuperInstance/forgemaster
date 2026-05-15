#!/usr/bin/env python3 -u
"""Study 41: First-Token Commitment — Hermes-70B via DeepInfra"""
import json, time, random, re, os, sys
sys.stdout.reconfigure(line_buffering=True)

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"

SYSTEM = "You are a math assistant."
PROMPT = "Compute the Eisenstein norm N(5 + (-3)ω) where ω = e^(2πi/3). N(a+bω) = a² - ab + b²."

CONDITIONS = [
    {"name": "C1_default_discourse", "prefill": "The", "label": "C1"},
    {"name": "C2_neutral_discourse", "prefill": "Well,", "label": "C2"},
    {"name": "C3_computation_setup", "prefill": "Let me", "label": "C3"},
    {"name": "C4_direct_computation", "prefill": "=", "label": "C4"},
    {"name": "C5_procedural", "prefill": "Step 1:", "label": "C5"},
]

TRIALS = 30

import urllib.request

def call_api(prefill):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT},
        {"role": "assistant", "content": prefill},
    ]
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 200,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        content = result["choices"][0]["message"]["content"]
        # The full response is prefill + content
        full_response = prefill + content
        return full_response, content, None
    except Exception as e:
        return None, None, str(e)

def extract_answer(text):
    """Extract final numeric answer from response."""
    if text is None:
        return None
    # Look for patterns like "= 49", "is 49", "=49", "N = 49"
    # Find all numbers
    numbers = re.findall(r'(?:=\s*|is\s+|equals?\s+|gives?\s+|result(?:s)?\s*(?:in|is|=)?\s*)\(?(\d+)\)?', text, re.IGNORECASE)
    if numbers:
        return int(numbers[-1])
    # Fallback: last standalone number in the text
    all_nums = re.findall(r'\b(\d+)\b', text)
    if all_nums:
        return int(all_nums[-1])
    return None

results = []
total_calls = len(CONDITIONS) * TRIALS
call_count = 0

for cond in CONDITIONS:
    print(f"\n=== {cond['label']}: prefill='{cond['prefill']}' ===")
    for trial in range(1, TRIALS + 1):
        call_count += 1
        full_response, content, error = call_api(cond["prefill"])
        
        if error:
            answer = None
            correct = None
            print(f"  Trial {trial}: ERROR - {error[:80]}")
        else:
            answer = extract_answer(full_response)
            correct = answer == 49
            print(f"  Trial {trial}: answer={answer} correct={correct}")
        
        results.append({
            "condition": cond["name"],
            "label": cond["label"],
            "prefill": cond["prefill"],
            "trial_num": trial,
            "response": full_response,
            "content": content,
            "answer": answer,
            "correct": correct,
            "error": error,
        })
        
        # Small delay to avoid rate limits
        time.sleep(0.3)
    
    # Brief pause between conditions
    time.sleep(1)

# Summary
print("\n\n========== RESULTS SUMMARY ==========")
summary = {}
for cond in CONDITIONS:
    cond_results = [r for r in results if r["label"] == cond["label"]]
    correct_count = sum(1 for r in cond_results if r["correct"])
    errors = sum(1 for r in cond_results if r["error"])
    accuracy = correct_count / len(cond_results) * 100
    summary[cond["label"]] = {
        "prefill": cond["prefill"],
        "correct": correct_count,
        "total": len(cond_results),
        "errors": errors,
        "accuracy": accuracy,
    }
    print(f"{cond['label']} (prefill='{cond['prefill']}'): {correct_count}/{len(cond_results)} = {accuracy:.1f}% (errors: {errors})")

# Save JSON
with open("/home/phoenix/.openclaw/workspace/experiments/study41-results.json", "w") as f:
    json.dump({"summary": summary, "results": results}, f, indent=2)

print("\nResults saved to experiments/study41-results.json")
