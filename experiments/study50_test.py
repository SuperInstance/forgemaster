#!/usr/bin/env python3
"""Study 50: Tier Boundary Mapping"""

import json, time, urllib.request, urllib.error, sys, os

DEEPINFRA_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

PROBLEMS = [
    {"a": 5, "b": -3, "answer": 49},
    {"a": 7, "b": 2, "answer": 39},
    {"a": 4, "b": -6, "answer": 76},
    {"a": 8, "b": -4, "answer": 112},
]

DEEPINFRA_MODELS = [
    "ByteDance/Seed-2.0-mini",
    "ByteDance/Seed-2.0-code",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "Qwen/Qwen3.6-35B-A3B",
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "NousResearch/Hermes-3-Llama-3.1-405B",
]

OLLAMA_MODELS = [
    "qwen3:4b",
    "qwen3:0.6b",
    "gemma3:1b",
]

def make_bare_prompt(a, b):
    return f"Compute f(a,b) = a² − ab + b² where a={a}, b={b}. Give only the number."

def make_scaffolded_prompt(a, b):
    return (
        f"Using the Eisenstein norm formula N(a,b) = a² − ab + b²: "
        f"First compute a². Then compute ab. Subtract ab from a². Then add b². "
        f"For a={a}, b={b}, what is the result?"
    )

def extract_number(text):
    """Extract the last number from the response."""
    import re
    # Remove thinking tags content if present
    text = re.sub(r'<think[^>]*>.*?</think[^>]*>', '', text, flags=re.DOTALL)
    nums = re.findall(r'-?\d+\.?\d*', text)
    if not nums:
        return None
    # Return the last integer-looking number
    for n in reversed(nums):
        val = float(n)
        if val == int(val):
            return int(val)
    return int(float(nums[-1]))

def query_deepinfra(model, prompt, retries=2):
    for attempt in range(retries + 1):
        try:
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 50,
            }).encode()
            req = urllib.request.Request(
                DEEPINFRA_URL,
                data=payload,
                headers={
                    "Authorization": f"Bearer {DEEPINFRA_KEY}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                return f"ERROR: {e}"

def query_ollama(model, prompt):
    try:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0, "num_predict": 500},
        }).encode()
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"ERROR: {e}"

def test_model(model_name, query_fn, is_ollama=False):
    results = {"bare": [], "scaffolded": []}
    for condition, prompt_fn in [("bare", make_bare_prompt), ("scaffolded", make_scaffolded_prompt)]:
        for prob in PROBLEMS:
            prompt = prompt_fn(prob["a"], prob["b"])
            response = query_fn(model_name, prompt)
            extracted = extract_number(response)
            correct = extracted == prob["answer"]
            results[condition].append({
                "a": prob["a"], "b": prob["b"], "expected": prob["answer"],
                "response": response[:200], "extracted": extracted, "correct": correct,
            })
            time.sleep(0.3 if not is_ollama else 0.1)
    return results

all_results = {}
models_to_test = [(m, "deepinfra") for m in DEEPINFRA_MODELS] + [(m, "ollama") for m in OLLAMA_MODELS]

for model_name, provider in models_to_test:
    print(f"\n{'='*60}")
    print(f"Testing: {model_name} ({provider})")
    print(f"{'='*60}")
    query_fn = query_ollama if provider == "ollama" else lambda m, p: query_deepinfra(m, p)
    results = test_model(model_name, query_fn, is_ollama=(provider=="ollama"))
    
    bare_pct = sum(1 for r in results["bare"] if r["correct"]) / len(results["bare"]) * 100
    scaf_pct = sum(1 for r in results["scaffolded"] if r["correct"]) / len(results["scaffolded"]) * 100
    
    print(f"  Bare: {bare_pct:.0f}%  |  Scaffolded: {scaf_pct:.0f}%")
    for cond in ["bare", "scaffolded"]:
        for r in results[cond]:
            status = "✓" if r["correct"] else "✗"
            print(f"  {status} {cond:12s} ({r['a']},{r['b']}) → {r['extracted']} (expected {r['expected']})")
    
    all_results[model_name] = {
        "provider": provider,
        "bare_pct": bare_pct,
        "scaffolded_pct": scaf_pct,
        "details": results,
    }

# Save JSON
with open("/home/phoenix/.openclaw/workspace/experiments/study50_results.json", "w") as f:
    json.dump(all_results, f, indent=2)

print("\n\n" + "="*60)
print("SUMMARY")
print("="*60)
# Sort by bare score descending
for model, data in sorted(all_results.items(), key=lambda x: -x[1]["bare_pct"]):
    print(f"  {model:50s}  Bare: {data['bare_pct']:5.1f}%  Scaffolded: {data['scaffolded_pct']:5.1f}%")
