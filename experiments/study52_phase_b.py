#!/usr/bin/env python3
"""Phase B fix: Translation quality audit (bare vs translated on Tier 2)"""

import json, os, sys, time, traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_router_api import ModelRegistry, ModelTierEnum, CriticalAngleRouter, RoutingStats, DEFAULT_MODELS
from fleet_translator_v2 import FleetRouter, ModelStage, translate, translate_for_stage

DEEPINFRA_KEY = open(os.path.expanduser(
    "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt"
)).read().strip()

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def call_deepinfra(model, prompt, timeout=60):
    import requests
    resp = requests.post(DEEPINFRA_URL, json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 256,
    }, headers={
        "Authorization": f"Bearer {DEEPINFRA_KEY}",
        "Content-Type": "application/json",
    }, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    return {"content": content, "tokens": usage.get("completion_tokens", 0)}

def eisenstein_norm(a, b):
    return a*a - a*b + b*b

def mobius(n):
    factors = []
    d, m = 2, n
    while d*d <= m:
        count = 0
        while m % d == 0:
            m //= d
            count += 1
        if count > 1: return 0
        if count == 1: factors.append(d)
        d += 1
    if m > 1: factors.append(m)
    return (-1) ** len(factors)

def legendre(a, p):
    a_mod = a % p
    if a_mod == 0: return 0
    result = pow(a_mod, (p-1)//2, p)
    return result if result <= 1 else -1

def modular_inverse(a, m):
    import math
    if math.gcd(a, m) != 1: return None
    return pow(a, -1, m)

def extract_number(text):
    import re
    text = text.strip()
    patterns = [
        r'(?:answer|result|value|output)\s*(?:is|=|:)\s*(-?\d+(?:\.\d+)?)',
        r'=\s*(-?\d+(?:\.\d+)?)\s*(?:\.|$)',
        r'(-?\d+(?:\.\d+)?)\s*(?:\.|$)',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            try: return float(matches[-1]) if '.' in matches[-1] else int(matches[-1])
            except: continue
    numbers = re.findall(r'-?\d+(?:\.\d+)?', text)
    if numbers:
        try: return float(numbers[-1]) if '.' in numbers[-1] else int(numbers[-1])
        except: pass
    return None

def score_answer(expected, got_text, tolerance=0.01):
    if expected is None: return "skip"
    got = extract_number(got_text)
    if got is None: return "incorrect"
    if isinstance(expected, float):
        if abs(got - expected) <= tolerance: return "correct"
    else:
        if got == expected: return "correct"
    if str(expected) in got_text: return "partial"
    return "incorrect"

def make_bare_prompt(task_type, params):
    """Build a bare prompt with no activation keys."""
    if task_type == "eisenstein_norm":
        return f"Compute the Eisenstein norm of (a={params['a']}, b={params['b']})."
    elif task_type == "mobius":
        return f"Compute the Möbius function μ({params['n']})."
    elif task_type == "legendre":
        return f"Compute the Legendre symbol ({params['a']}|{params['p']})."
    elif task_type == "modular_inverse":
        return f"Find the modular inverse of {params['a']} mod {params['m']}."
    return str(params)

tests = [
    {"task_type": "eisenstein_norm", "params": {"a": 3, "b": 5}, "expected": eisenstein_norm(3, 5)},
    {"task_type": "mobius", "params": {"n": 30}, "expected": mobius(30)},
    {"task_type": "legendre", "params": {"a": 2, "p": 7}, "expected": legendre(2, 7)},
    {"task_type": "eisenstein_norm", "params": {"a": 7, "b": 4}, "expected": eisenstein_norm(7, 4)},
    {"task_type": "mobius", "params": {"n": 105}, "expected": mobius(105)},
    {"task_type": "legendre", "params": {"a": 5, "p": 13}, "expected": legendre(5, 13)},
    {"task_type": "modular_inverse", "params": {"a": 7, "m": 11}, "expected": modular_inverse(7, 11)},
    {"task_type": "eisenstein_norm", "params": {"a": -2, "b": 6}, "expected": eisenstein_norm(-2, 6)},
    {"task_type": "mobius", "params": {"n": 210}, "expected": mobius(210)},
    {"task_type": "legendre", "params": {"a": 3, "p": 11}, "expected": legendre(3, 11)},
]

model_id = "NousResearch/Hermes-3-Llama-3.1-70B"
results = []

print("=" * 70)
print("PHASE B: Translation Quality Audit")
print(f"Model: {model_id}")
print("=" * 70)

for test in tests:
    print(f"\n--- {test['task_type']} {test['params']} (expected={test['expected']}) ---")

    bare_prompt = make_bare_prompt(test["task_type"], test["params"])
    translated_prompt = translate(test["task_type"], test["params"], ModelStage.CAPABLE)

    print(f"  BARE:       \"{bare_prompt[:80]}\"")
    print(f"  TRANSLATED: \"{translated_prompt[:80]}\"")

    for label, prompt in [("bare", bare_prompt), ("translated", translated_prompt)]:
        try:
            t0 = time.time()
            response = call_deepinfra(model_id, prompt, timeout=45)
            latency = time.time() - t0
            answer_text = response["content"]
            score = score_answer(test["expected"], answer_text)

            result = {
                "task_type": test["task_type"],
                "params": test["params"],
                "expected": test["expected"],
                "model_id": model_id,
                "prompt_type": label,
                "prompt": prompt,
                "response": answer_text[:500],
                "score": score,
                "latency_s": round(latency, 2),
            }
            results.append(result)
            print(f"    [{label}] → {score} | {latency:.2f}s | {answer_text[:100]}")

        except Exception as e:
            print(f"    [{label}] → ERROR: {e}")
            results.append({
                "task_type": test["task_type"],
                "params": test["params"],
                "expected": test["expected"],
                "model_id": model_id,
                "prompt_type": label,
                "prompt": prompt,
                "response": None,
                "score": "error",
                "error": str(e),
                "latency_s": None,
            })

# Save
out = {"phase_b": results}
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study52_phase_b.json")
with open(out_path, "w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n✅ Phase B saved to {out_path}")

# Summary
bare = [r for r in results if r["prompt_type"] == "bare"]
trans = [r for r in results if r["prompt_type"] == "translated"]
bare_correct = sum(1 for r in bare if r["score"] == "correct")
trans_correct = sum(1 for r in trans if r["score"] == "correct")
print(f"\nBare:       {bare_correct}/{len(bare)} correct")
print(f"Translated: {trans_correct}/{len(trans)} correct")
