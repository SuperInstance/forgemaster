#!/usr/bin/env python3
"""P3 Experiment — via Ollama HTTP API (avoids TTY spinner issues)."""

import requests
import json
import re
import time
from collections import defaultdict

TEST_CASES = [
    {"a": 3, "b": 4, "answer": 25},
    {"a": 5, "b": -2, "answer": 29},
    {"a": 7, "b": 1, "answer": 50},
    {"a": -4, "b": 3, "answer": 25},
    {"a": 6, "b": -5, "answer": 61},
    {"a": 8, "b": -3, "answer": 73},
    {"a": -6, "b": -8, "answer": 100},
    {"a": 2, "b": 9, "answer": 85},
    {"a": -7, "b": 4, "answer": 65},
    {"a": 10, "b": -6, "answer": 136},
]

MODELS = ["qwen3:0.6b", "gemma3:1b", "llama3.2:1b", "phi4-mini", "qwen3:4b"]
TRIALS = 3

def query(model, prompt):
    try:
        r = requests.post("http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
            timeout=60)
        data = r.json()
        raw = data.get("response", "").strip()
        
        # qwen3 thinking mode: extract from thinking field if present
        if "qwen3" in model:
            think = data.get("thinking", "") or ""
            think_match = re.search(r'<think[^>]*>(.*?)(?:</think|$)', raw, re.DOTALL)
            if think_match:
                thinking = think_match.group(1)
                nums = re.findall(r'-?\d+', thinking)
                if nums:
                    return nums[-1], raw
            # Also check response body
            body = re.sub(r'<think.*?(?:</think|$)', '', raw, flags=re.DOTALL).strip()
            nums = re.findall(r'-?\d+', body)
            if nums:
                return nums[-1], raw
        
        nums = re.findall(r'-?\d+', raw)
        if nums:
            return nums[-1], raw
        return "PARSE_FAIL", raw
    except Exception as e:
        return "ERROR", str(e)

def classify(output_str, a, b, answer):
    try:
        out = int(output_str)
    except:
        return "INVALID", ""
    
    if out == answer: return "CORRECT", ""
    if out == a: return "ECHO", "echo-a"
    if out == b: return "ECHO", "echo-b"
    if out == a+b: return "ECHO", "echo-sum"
    if out == a-b: return "ECHO", "echo-diff"
    if out == -a: return "ECHO", "echo-neg-a"
    if out == -b: return "ECHO", "echo-neg-b"
    if out == a*a: return "PARTIAL", "partial-a²"
    if out == b*b: return "PARTIAL", "partial-b²"
    if abs(out - a*a) <= 2: return "PARTIAL", f"near-a²"
    if abs(out - b*b) <= 2: return "PARTIAL", f"near-b²"
    return "OTHER", ""

print("=" * 70)
print("P3 EXPERIMENT: a²+b² (2 intermediates) vs a²-ab+b² (3 intermediates)")
print("=" * 70)

results = {}

for model in MODELS:
    print(f"\n{'─'*50}")
    print(f"  {model}")
    print(f"{'─'*50}")
    
    counts = defaultdict(int)
    details = []
    
    for tc in TEST_CASES:
        a, b, ans = tc["a"], tc["b"], tc["answer"]
        prompt = f"Compute a²+b² where a={a} and b={b}. Give ONLY the number."
        
        for _ in range(TRIALS):
            num, raw = query(model, prompt)
            rtype, contour = classify(num, a, b, ans)
            counts[rtype] += 1
            details.append({"a": a, "b": b, "output": num, "type": rtype, "contour": contour})
            
            sym = {"CORRECT": "✅", "PARTIAL": "🔧", "ECHO": "📡", "OTHER": "❓", "INVALID": "⚠️"}.get(rtype, "?")
            print(f"    {sym} ({a:>3},{b:>3})→{str(num):>6s}  {rtype:<8s} {contour}")
            time.sleep(0.3)
    
    n = sum(counts.values())
    results[model] = {
        "echo": counts.get("ECHO", 0) / n,
        "partial": counts.get("PARTIAL", 0) / n,
        "correct": counts.get("CORRECT", 0) / n,
        "other": counts.get("OTHER", 0) / n,
    }
    
    print(f"  → Echo: {counts.get('ECHO',0)}/{n} ({results[model]['echo']:.0%})  "
          f"Partial: {counts.get('PARTIAL',0)}/{n} ({results[model]['partial']:.0%})  "
          f"Correct: {counts.get('CORRECT',0)}/{n} ({results[model]['correct']:.0%})")

# Comparison table
eisenstein = {"qwen3:0.6b": (0.90, 0.05), "gemma3:1b": (0.46, 0.30),
              "llama3.2:1b": (0.41, 0.35), "phi4-mini": (0.88, 0.12), "qwen3:4b": (0.11, 0.89)}

print(f"\n{'='*70}")
print(f"COMPARISON: a²+b² vs a²-ab+b²")
print(f"{'='*70}")
print(f"  {'Model':<15s} {'Task':<10s} {'Echo%':>7s} {'Partial%':>9s}")
print(f"  {'─'*15} {'─'*10} {'─'*7} {'─'*9}")

for m in MODELS:
    r = results[m]
    e = eisenstein.get(m, (0, 0))
    print(f"  {m:<15s} {'a²+b²':<10s} {r['echo']:>6.0%} {r['partial']:>8.0%}")
    print(f"  {'':<15s} {'a²-ab+b²':<10s} {e[0]:>6.0%} {e[1]:>8.0%}")
    print()

# Verdict
print(f"{'='*70}")
print(f"P3 VERDICT")
print(f"{'='*70}")
phi4_p = results["phi4-mini"]["partial"]
phi4_e = results["phi4-mini"]["echo"]
print(f"phi4-mini on a²+b²: echo={phi4_e:.0%}, partial={phi4_p:.0%}")
print(f"phi4-mini on a²-ab+b²: echo=88%, partial=12%")
if phi4_p > 0.25:
    print("✅ P3 CONFIRMED: percolation threshold is task-dependent")
elif phi4_e > 0.7:
    print("❌ P3 FALSIFIED: phi4-mini can't compute even simpler tasks")
else:
    print("🔬 INCONCLUSIVE: need more trials or different task complexity")

# Save
with open("experiments/P3-results.json", "w") as f:
    json.dump({"results": results, "eisenstein": eisenstein}, f, indent=2)
print(f"\nSaved to experiments/P3-results.json")
