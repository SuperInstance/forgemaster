#!/usr/bin/env python3
"""Study 60: Temperature × Tier interaction on Eisenstein norm computation."""
import json, time, re, sys, os, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

DEEPINFRA_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()

# Test problems: (a, b) -> expected answer
PROBLEMS = [
    {"a": 5, "b": -3, "expected": 49},
    {"a": 7, "b": 2, "expected": 39},
    {"a": 4, "b": -6, "expected": 76},
    {"a": 8, "b": -4, "expected": 112},
]

TEMPERATURES = [0.0, 0.3, 0.7, 1.0]
TRIALS = 3

MODELS = [
    {
        "name": "Seed-2.0-mini",
        "tier": 1,
        "provider": "deepinfra",
        "model_id": "ByteDance/Seed-2.0-mini",
    },
    {
        "name": "Hermes-70B",
        "tier": 2,
        "provider": "deepinfra",
        "model_id": "NousResearch/Hermes-3-Llama-3.1-70B",
    },
    {
        "name": "qwen3:0.6b",
        "tier": 3,
        "provider": "ollama",
        "model_id": "qwen3:0.6b",
    },
]

def make_prompt(prob):
    return f"Compute the Eisenstein norm of ({prob['a']}, {prob['b']}ω). N(a,b) = a² - ab + b². Give ONLY the final number."

def query_deepinfra(model_id, prompt, temperature, max_tokens=150):
    import urllib.request
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {DEEPINFRA_KEY}",
        "Content-Type": "application/json",
    })
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    latency = time.time() - t0
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, latency, usage.get("completion_tokens", 0)

def query_ollama(model_id, prompt, temperature, max_tokens=150):
    import urllib.request
    url = "http://localhost:11434/api/chat"
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    latency = time.time() - t0
    content = data.get("message", {}).get("content", "")
    # Ollama doesn't give token counts easily
    return content, latency, len(content.split())

def extract_answer(text):
    """Extract the last integer from the response."""
    nums = re.findall(r'-?\d+', text)
    if not nums:
        return None
    return int(nums[-1])

def score_trial(answer, expected):
    if answer is None:
        return "incorrect"
    if answer == expected:
        return "correct"
    return "incorrect"

def run_trial(model, prob, temperature, trial_idx):
    prompt = make_prompt(prob)
    try:
        if model["provider"] == "deepinfra":
            content, latency, tokens = query_deepinfra(model["model_id"], prompt, temperature)
        else:
            content, latency, tokens = query_ollama(model["model_id"], prompt, temperature)
        answer = extract_answer(content)
        result = score_trial(answer, prob["expected"])
        return {
            "model": model["name"],
            "tier": model["tier"],
            "temperature": temperature,
            "problem": f"({prob['a']},{prob['b']})",
            "expected": prob["expected"],
            "answer": answer,
            "result": result,
            "latency": round(latency, 2),
            "tokens": tokens,
            "trial": trial_idx,
            "raw_response": content[:200],
        }
    except Exception as e:
        return {
            "model": model["name"],
            "tier": model["tier"],
            "temperature": temperature,
            "problem": f"({prob['a']},{prob['b']})",
            "expected": prob["expected"],
            "answer": None,
            "result": "error",
            "latency": 0,
            "tokens": 0,
            "trial": trial_idx,
            "raw_response": str(e)[:200],
        }

def main():
    results = []
    total = len(MODELS) * len(TEMPERATURES) * len(PROBLEMS) * TRIALS
    done = 0
    
    # Run with limited parallelism to avoid rate limits
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for model in MODELS:
            for temp in TEMPERATURES:
                for prob in PROBLEMS:
                    for trial in range(TRIALS):
                        f = pool.submit(run_trial, model, prob, temp, trial)
                        futures[f] = (model["name"], temp, prob, trial)
        
        for f in as_completed(futures):
            done += 1
            r = f.result()
            results.append(r)
            status = "✓" if r["result"] == "correct" else ("~" if r["result"] == "partial" else "✗")
            if done % 12 == 0 or done == total:
                print(f"[{done}/{total}] {r['model']} T={r['temperature']} {r['problem']} → {r['answer']} (exp {r['expected']}) {status}", flush=True)
    
    # Save raw results
    with open("experiments/study60_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Compute summary
    print("\n=== SUMMARY ===")
    for model in MODELS:
        print(f"\n--- {model['name']} (Tier {model['tier']}) ---")
        for temp in TEMPERATURES:
            trials = [r for r in results if r["model"] == model["name"] and r["temperature"] == temp]
            correct = sum(1 for r in trials if r["result"] == "correct")
            total_t = len(trials)
            pct = 100 * correct / total_t if total_t > 0 else 0
            avg_lat = sum(r["latency"] for r in trials) / total_t if total_t > 0 else 0
            print(f"  T={temp}: {correct}/{total_t} ({pct:.0f}%) avg_latency={avg_lat:.1f}s")

if __name__ == "__main__":
    main()
