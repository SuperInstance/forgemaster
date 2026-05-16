#!/usr/bin/env python3
"""
Study 62: Translation Depth Audit (v2 - faster)
"""

import json, time, re, requests, sys, os

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = [
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
]

PROBLEMS = [
    {"a": 5,  "b": -3, "answer": 49},
    {"a": 3,  "b": 1,  "answer": 7},
    {"a": 7,  "b": 2,  "answer": 39},
    {"a": 4,  "b": -1, "answer": 21},
    {"a": 6,  "b": 3,  "answer": 27},
    {"a": 2,  "b": -5, "answer": 39},
    {"a": 8,  "b": 1,  "answer": 57},
    {"a": 1,  "b": 1,  "answer": 1},
    {"a": 10, "b": -4, "answer": 156},
    {"a": 3,  "b": -7, "answer": 79},
]

def make_prompt(depth, a, b):
    if depth == 1:
        return f"Compute N({a},{b}) = a²-ab+b². Give just the numeric answer."
    elif depth == 2:
        return f"Compute N({a},{b}) = a^2 - a*b + b^2. Give just the numeric answer."
    elif depth == 3:
        return f"Compute the Eisenstein norm of ({a}, {b}), which equals a squared minus a times b plus b squared. Give just the numeric answer."
    elif depth == 4:
        return f"Step 1: a² = {a*a}. Step 2: a×b = {a*b}. Step 3: b² = {b*b}. Step 4: {a*a}-({a*b})+{b*b} = {a*a - a*b + b*b}. Give just the numeric answer."
    elif depth == 5:
        return f"The Eisenstein integer norm N(a,b) computes the quadratic form a²-ab+b². For ({a}, {b}): N = {a*a}-({a*b})+{b*b} = {a*a - a*b + b*b}. Give just the numeric answer."

def query_model(model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 128},
                timeout=60)
            if resp.status_code == 429:
                time.sleep(min(30, 5 * (attempt + 1)))
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return f"ERROR: {e}"
    return "ERROR: max retries"

def extract_number(text):
    text = re.sub(r'^(the answer is|answer:|result:|n\s*=\s*)', '', text, flags=re.IGNORECASE)
    matches = re.findall(r'-?\d+', text)
    return int(matches[0]) if matches else None

def main():
    results = []
    total = 5 * 2 * 10 * 3  # 300
    done = 0
    
    print(f"Running {total} trials...", flush=True)
    
    for depth in range(1, 6):
        for model in MODELS:
            ms = model.split("/")[-1][:20]
            for pi, problem in enumerate(PROBLEMS):
                a, b, answer = problem["a"], problem["b"], problem["answer"]
                for trial in range(3):
                    prompt = make_prompt(depth, a, b)
                    response = query_model(model, prompt)
                    extracted = extract_number(response)
                    correct = extracted == answer
                    results.append({
                        "depth": depth,
                        "depth_name": {1:"bare_notation",2:"unicode_normalize",3:"natural_language",4:"step_by_step",5:"full_activation_key"}[depth],
                        "model": model, "model_short": ms,
                        "a": a, "b": b, "expected": answer,
                        "response": response, "extracted": extracted,
                        "correct": correct, "trial": trial+1,
                    })
                    done += 1
                    s = "✓" if correct else "✗"
                    print(f"[{done}/{total}] D{depth} {ms:20s} ({a:2d},{b:2d}) → {str(extracted):>5s} {s}", flush=True)
    
    # Save results
    outdir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(outdir, "study62_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n\n=== RESULTS SUMMARY ===\n", flush=True)
    
    for depth in range(1, 6):
        for model in MODELS:
            ms = model.split("/")[-1]
            cell = [r for r in results if r["depth"] == depth and r["model"] == model]
            cc = sum(1 for r in cell if r["correct"])
            tc = len(cell)
            print(f"  D{depth} | {ms[:25]:25s} | {cc}/{tc} = {cc/tc*100:.0f}%", flush=True)
    
    print("\n--- By Depth (all models) ---", flush=True)
    for depth in range(1, 6):
        cell = [r for r in results if r["depth"] == depth]
        cc = sum(1 for r in cell if r["correct"])
        dn = {1:"Bare notation",2:"Unicode normalize",3:"Natural language",4:"Step-by-step",5:"Full activation key"}[depth]
        print(f"  D{depth} ({dn:20s}): {cc}/{len(cell)} = {cc/len(cell)*100:.0f}%", flush=True)

if __name__ == "__main__":
    main()
