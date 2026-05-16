#!/usr/bin/env python3
"""
Study 62: Translation Depth Audit
How much translation is needed to break through the vocabulary wall for Tier 2 models?

5 translation depths × 2 models × 10 problems × 3 trials = 300 trials
"""

import json
import time
import re
import requests
import sys
import os

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = [
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "Qwen/Qwen3.6-35B-A3B",  # fallback since Qwen3-235B may not be available
]

# 10 Eisenstein norm problems with verified answers
# N(a,b) = a² - ab + b²
PROBLEMS = [
    {"a": 5,  "b": -3, "answer": 49},   # 25+15+9
    {"a": 3,  "b": 1,  "answer": 7},    # 9-3+1
    {"a": 7,  "b": 2,  "answer": 39},   # 49-14+4
    {"a": 4,  "b": -1, "answer": 21},   # 16+4+1
    {"a": 6,  "b": 3,  "answer": 27},   # 36-18+9
    {"a": 2,  "b": -5, "answer": 39},   # 4+10+25
    {"a": 8,  "b": 1,  "answer": 57},   # 64-8+1
    {"a": 1,  "b": 1,  "answer": 1},    # 1-1+1
    {"a": 10, "b": -4, "answer": 156},  # 100+40+16
    {"a": 3,  "b": -7, "answer": 79},   # 9+21+49
]

# 5 translation depths
def make_prompt(depth, a, b):
    if depth == 1:
        # Bare notation - no translation
        return f"Compute N({a},{-b if b < 0 else b}) = a²-ab+b². Give just the numeric answer."
    elif depth == 2:
        # Unicode normalize - ASCII only
        return f"Compute N({a},{-b if b < 0 else b}) = a^2 - a*b + b^2. Give just the numeric answer."
    elif depth == 3:
        # Natural language
        return f"Compute the Eisenstein norm of ({a}, {b}), which equals a squared minus a times b plus b squared. Give just the numeric answer."
    elif depth == 4:
        # Step-by-step
        return f"Step 1: a² = {a*a}. Step 2: a×b = {a*b}. Step 3: b² = {b*b}. Step 4: {a*a}-({a*b})+{b*b} = {a*a - a*b + b*b}. Give just the numeric answer."
    elif depth == 5:
        # Full activation key
        return f"The Eisenstein integer norm N(a,b) computes the quadratic form a²-ab+b². For ({a}, {b}): N = {a*a}-({a*b})+{b*b} = {a*a - a*b + b*b}. Give just the numeric answer."

def query_model(model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 128,
                },
                timeout=60,
            )
            if resp.status_code == 429:
                wait = min(30, 5 * (attempt + 1))
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return f"ERROR: {e}"
    return "ERROR: max retries"

def extract_number(text):
    """Extract the first integer from the response."""
    # Remove common prefixes
    text = re.sub(r'^(the answer is|answer:|result:|n\s*=\s*)', '', text, flags=re.IGNORECASE)
    # Find all integers
    matches = re.findall(r'-?\d+', text)
    if matches:
        return int(matches[0])
    return None

def main():
    results = []
    total = 300
    done = 0
    
    # Check if Qwen3-235B is available
    try:
        test_resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
                "messages": [{"role": "user", "content": "Say yes"}],
                "temperature": 0.0,
                "max_tokens": 10,
            },
            timeout=30,
        )
        if test_resp.status_code == 200:
            print("Qwen3-235B available, using it")
            MODELS[1] = "Qwen/Qwen3-235B-A22B-Instruct-2507"
        else:
            print(f"Qwen3-235B not available ({test_resp.status_code}), using Qwen3.6-35B")
    except:
        print("Qwen3-235B check failed, using Qwen3.6-35B")
    
    print(f"Models: {MODELS}")
    print(f"Running {total} trials...")
    
    for depth in range(1, 6):
        for model in MODELS:
            model_short = model.split("/")[-1]
            for pi, problem in enumerate(PROBLEMS):
                a, b, answer = problem["a"], problem["b"], problem["answer"]
                for trial in range(3):
                    prompt = make_prompt(depth, a, b)
                    response = query_model(model, prompt)
                    extracted = extract_number(response)
                    correct = extracted == answer
                    
                    result = {
                        "depth": depth,
                        "depth_name": {1: "bare_notation", 2: "unicode_normalize", 3: "natural_language", 4: "step_by_step", 5: "full_activation_key"}[depth],
                        "model": model,
                        "model_short": model_short,
                        "problem": f"({a},{b})",
                        "a": a,
                        "b": b,
                        "expected": answer,
                        "response": response,
                        "extracted": extracted,
                        "correct": correct,
                        "trial": trial + 1,
                    }
                    results.append(result)
                    done += 1
                    
                    status = "✓" if correct else "✗"
                    print(f"  [{done}/{total}] D{depth} {model_short[:15]:15s} ({a},{b}) t{trial+1} → {extracted} {status} (exp {answer})")
                    
                    # Rate limit: small delay between requests
                    time.sleep(0.5)
    
    # Save raw results
    with open(os.path.join(os.path.dirname(__file__), "study62_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    # Compute summary statistics
    print("\n\n=== RESULTS SUMMARY ===\n")
    
    summary = {}
    for depth in range(1, 6):
        for model in MODELS:
            model_short = model.split("/")[-1]
            key = f"D{depth}_{model_short}"
            cell = [r for r in results if r["depth"] == depth and r["model"] == model]
            correct_count = sum(1 for r in cell if r["correct"])
            total_count = len(cell)
            pct = correct_count / total_count * 100 if total_count > 0 else 0
            summary[key] = {"correct": correct_count, "total": total_count, "pct": round(pct, 1)}
            print(f"  Depth {depth} | {model_short[:20]:20s} | {correct_count}/{total_count} = {pct:.1f}%")
    
    # Per-depth aggregate
    print("\n--- By Depth (all models) ---")
    for depth in range(1, 6):
        cell = [r for r in results if r["depth"] == depth]
        correct_count = sum(1 for r in cell if r["correct"])
        total_count = len(cell)
        pct = correct_count / total_count * 100 if total_count > 0 else 0
        depth_names = {1: "Bare notation", 2: "Unicode normalize", 3: "Natural language", 4: "Step-by-step", 5: "Full activation key"}
        print(f"  Depth {depth} ({depth_names[depth]:20s}): {correct_count}/{total_count} = {pct:.1f}%")
    
    # Per-model aggregate
    print("\n--- By Model (all depths) ---")
    for model in MODELS:
        model_short = model.split("/")[-1]
        cell = [r for r in results if r["model"] == model]
        correct_count = sum(1 for r in cell if r["correct"])
        total_count = len(cell)
        pct = correct_count / total_count * 100 if total_count > 0 else 0
        print(f"  {model_short[:25]:25s}: {correct_count}/{total_count} = {pct:.1f}%")
    
    print(f"\nTotal: {sum(1 for r in results if r['correct'])}/{len(results)} = {sum(1 for r in results if r['correct'])/len(results)*100:.1f}%")
    print(f"\nResults saved to experiments/study62_results.json")
    
    return results, summary

if __name__ == "__main__":
    main()
