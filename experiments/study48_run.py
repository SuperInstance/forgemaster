#!/usr/bin/env python3
"""Study 48: Deep dive into the Labeled Paradox — parallel version."""

import json, time, requests, os, re, sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DEEPINFRA_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
DEEPSEEK_KEY = Path(os.path.expanduser("~/.openclaw/workspace/.credentials/deepseek-api-key.txt")).read_text().strip()
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

MODELS_DEEPINFRA = [
    "ByteDance/Seed-2.0-mini",
    "ByteDance/Seed-2.0-code",
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "NousResearch/Hermes-3-Llama-3.1-405B",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
]
MODEL_DEEPSEEK = "deepseek-chat"

PROBLEMS = [
    (5, -3, 49),
    (7, 2, 39),
    (4, -6, 76),
    (3, 1, 7),
    (8, -4, 112),
    (6, -5, 91),
    (2, -7, 67),
    (10, -1, 111),
]

CONDITIONS = ["notation", "labeled", "stepbystep", "conceptual"]

RESULTS_FILE = "/home/phoenix/.openclaw/workspace/experiments/study48_results.json"

def make_prompt(condition, a, b):
    if condition == "notation":
        return f"Compute f(a,b) = a² − ab + b² where a={a}, b={b}. Give only the number."
    elif condition == "labeled":
        return f"Compute the Eisenstein norm E({a},{b}) = a² − ab + b² where a={a}, b={b}. Give only the number."
    elif condition == "stepbystep":
        return f"""Compute step by step:
1. a = {a}, b = {b}
2. a² = {a}² = {a**2}
3. ab = {a} × {b} = {a*b}
4. b² = {b}² = {b**2}
5. a² − ab + b² = {a**2} − ({a*b}) + {b**2}

What is the final result? Give only the number."""
    elif condition == "conceptual":
        return f"What is the Eisenstein norm of the Eisenstein integer {a}+{b}ω? Recall N(a+bω) = a² − ab + b². Give only the number."

def extract_number(text):
    if not text:
        return None
    text = text.strip()
    match = re.search(r'-?\d+', text)
    if match:
        return int(match.group())
    return None

def query_model(model, prompt, endpoint, key):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 50,
    }
    try:
        r = requests.post(endpoint, headers=headers, json=payload, timeout=90)
        data = r.json()
        if "choices" in data:
            content = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            return {
                "response": content,
                "tokens_prompt": usage.get("prompt_tokens", 0),
                "tokens_completion": usage.get("completion_tokens", 0),
                "tokens_total": usage.get("total_tokens", 0),
                "error": None,
            }
        else:
            return {"response": "", "tokens_prompt": 0, "tokens_completion": 0, "tokens_total": 0,
                    "error": str(data)[:200]}
    except Exception as e:
        return {"response": "", "tokens_prompt": 0, "tokens_completion": 0, "tokens_total": 0,
                "error": str(e)[:200]}

def run_single(task):
    model, cond, a, b, expected, endpoint, key = task
    prompt = make_prompt(cond, a, b)
    result = query_model(model, prompt, endpoint, key)
    extracted = extract_number(result["response"])
    correct = extracted == expected
    return {
        "model": model,
        "condition": cond,
        "a": a, "b": b, "expected": expected,
        "response": result["response"],
        "extracted": extracted,
        "correct": correct,
        "tokens_prompt": result["tokens_prompt"],
        "tokens_completion": result["tokens_completion"],
        "tokens_total": result["tokens_total"],
        "error": result["error"],
        "timestamp": datetime.now().isoformat(),
    }

def main():
    # Build task list
    tasks = []
    for model in MODELS_DEEPINFRA:
        for a, b, expected in PROBLEMS:
            for cond in CONDITIONS:
                tasks.append((model, cond, a, b, expected, DEEPINFRA_ENDPOINT, DEEPINFRA_KEY))
    for a, b, expected in PROBLEMS:
        for cond in CONDITIONS:
            tasks.append((MODEL_DEEPSEEK, cond, a, b, expected, DEEPSEEK_ENDPOINT, DEEPSEEK_KEY))
    
    print(f"Total tasks: {len(tasks)}")
    
    results = []
    completed = 0
    
    # Run with thread pool (8 concurrent)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(run_single, t): t for t in tasks}
        for future in as_completed(futures):
            t = futures[future]
            try:
                r = future.result()
                results.append(r)
                completed += 1
                sym = "✓" if r["correct"] else "✗"
                print(f"[{completed}/{len(tasks)}] {r['model'][:30]:30s} | {r['condition']:12s} | ({r['a']},{r['b']})={r['expected']:>3d} {sym} (got {r['extracted']}) [{r['tokens_completion']} tok]")
            except Exception as e:
                completed += 1
                print(f"[{completed}/{len(tasks)}] ERROR: {e}")
    
    # Save results
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} results to {RESULTS_FILE}")
    
    # Summary
    print("\n=== ACCURACY BY MODEL × CONDITION ===")
    all_models = MODELS_DEEPINFRA + [MODEL_DEEPSEEK]
    for model in all_models:
        accs = {}
        avg_tokens = {}
        for cond in CONDITIONS:
            mc = [r for r in results if r["model"] == model and r["condition"] == cond]
            if mc:
                accs[cond] = sum(1 for r in mc if r["correct"]) / len(mc) * 100
                avg_tokens[cond] = sum(r["tokens_completion"] for r in mc) / len(mc)
        if accs:
            print(f"\n{model}:")
            for cond in CONDITIONS:
                if cond in accs:
                    print(f"  {cond:15s}: {accs[cond]:5.1f}%  (avg {avg_tokens[cond]:.0f} tokens)")
            if "notation" in accs and "labeled" in accs:
                delta = accs["notation"] - accs["labeled"]
                if delta > 10:
                    print(f"  ⚠️  LABELED PARADOX: notation > labeled (Δ={delta:+.0f}%)")
                elif delta < -10:
                    print(f"  ✓  Label HELPS: labeled > notation (Δ={delta:+.0f}%)")
                else:
                    print(f"  ~  No significant label effect (Δ={delta:+.0f}%)")

if __name__ == "__main__":
    main()
