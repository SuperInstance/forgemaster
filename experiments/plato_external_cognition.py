#!/usr/bin/env python3
"""experiments/plato_external_cognition.py — Externalized Cognition Through PLATO

The real experiment: Can we get BETTER results by externalizing each reasoning step
into a PLATO tile that the NEXT iteration reads, compared to one monolithic thinking call?

Architecture:
  1. Call model with max_tokens=200 (enough for one step of reasoning)
  2. Extract reasoning_content as TILE 1 (the frozen step)
  3. Call model again, FEEDING tile 1 in the prompt, ask for NEXT step
  4. Extract reasoning_content as TILE 2
  5. Repeat until answer converges or max iterations reached
  6. Final extraction from accumulated tiles

Advantage over single thinking call:
  - Every intermediate step is FROZEN and AUDITABLE
  - Can REWIND to any step and BRANCH (spreader-tool)
  - Can SWITCH MODELS between steps (Seed-mini for step 1, Qwen-4B for step 2)
  - The context window is effectively unbounded (tiles accumulate in PLATO, not in one call)
  - Each step can be PARALLELIZED (send step K to N models for N interpretations)

Comparison conditions:
  A) MONOLITHIC: Single call, max_tokens=1000 (the thinking baseline)
  B) PLATO-CHAIN: N sequential calls, each reads all previous tiles
  C) PLATO-PARALLEL: Step 1 computes, then step 2 is sent to 3 models simultaneously
  
Models: Qwen3.5-4B (the thinking model that NEEDS externalization)
"""
import requests, re, time, json, os
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Tuple

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def query(model, messages, max_tokens=200):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(URL, headers=headers, json=payload, timeout=120)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return None, None, lat, 0
        d = r.json()
        msg = d["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or "").strip()
        usage = d.get("usage", {})
        return content, reasoning, lat, usage.get("total_tokens", 0)
    except:
        return None, None, (time.time() - start) * 1000, 0

def extract_num(text):
    if not text: return None
    # Look for Final Answer or RESULT patterns
    for pattern in [r'Final Answer:\s*.*?(-?\d+\.?\d*)', r'RESULT:\s*(-?\d+\.?\d*)', r'=\s*(-?\d+\.?\d*)']:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m: return m.group(1)
    nums = re.findall(r'-?\d+\.?\d*', text)
    return nums[-1] if nums else None

def check(got, expected, tol=0.05):
    if not got or not expected: return False
    try:
        return abs(float(got) - float(expected)) / max(abs(float(expected)), 0.01) <= tol
    except: return False

def run_monolithic(model, prompt):
    """Condition A: Single monolithic call with max_tokens=1000."""
    messages = [
        {"role": "system", "content": "Compute step by step. End with Final Answer: <number>"},
        {"role": "user", "content": prompt},
    ]
    content, reasoning, lat, tokens = query(model, messages, max_tokens=1000)
    ext = extract_num(content) or extract_num(reasoning)
    return ext, content, reasoning, lat, tokens

def run_plato_chain(model, prompt, max_steps=4):
    """Condition B: Sequential PLATO chain. Each step reads all previous tiles."""
    tiles = []
    total_lat = 0
    total_tokens = 0
    
    for step in range(1, max_steps + 1):
        if step == 1:
            messages = [
                {"role": "system", "content": "You are computing step by step. Write your work. This is step 1. End with a partial result if you have one."},
                {"role": "user", "content": prompt},
            ]
        elif step == max_steps:
            # Final step: synthesize
            tile_text = "\n\n".join(f"Step {t['step']}:\n{t['reasoning'][:500]}" for t in tiles)
            messages = [
                {"role": "system", "content": f"Previous computation steps:\n\n{tile_text}\n\nThis is the FINAL step. Give the Final Answer as a number."},
                {"role": "user", "content": prompt},
            ]
        else:
            tile_text = "\n\n".join(f"Step {t['step']}:\n{t['reasoning'][:500]}" for t in tiles)
            messages = [
                {"role": "system", "content": f"Previous computation steps:\n\n{tile_text}\n\nContinue the computation. This is step {step}. Show your work."},
                {"role": "user", "content": prompt},
            ]
        
        content, reasoning, lat, tokens = query(model, messages, max_tokens=300)
        total_lat += lat
        total_tokens += tokens
        
        tiles.append({
            "step": step,
            "content": content,
            "reasoning": reasoning,
            "latency": lat,
        })
        
        # Check if we already have the answer in content
        if content:
            ext = extract_num(content)
            if ext:
                return ext, tiles, total_lat, total_tokens
    
    # Extract from last tile
    last = tiles[-1]
    ext = extract_num(last["content"]) or extract_num(last["reasoning"])
    return ext, tiles, total_lat, total_tokens

def run_plato_hybrid(model_fast, model_think, prompt, max_steps=4):
    """Condition D: Hybrid — fast model does initial steps, thinking model does final synthesis."""
    tiles = []
    total_lat = 0
    total_tokens = 0
    
    # Step 1: Fast model decomposes the problem
    messages = [
        {"role": "system", "content": "Decompose this computation into individual arithmetic steps. List each step clearly."},
        {"role": "user", "content": prompt},
    ]
    content, reasoning, lat, tokens = query(model_fast, messages, max_tokens=200)
    total_lat += lat
    total_tokens += tokens
    tiles.append({"step": 1, "model": "fast", "content": content, "reasoning": reasoning, "latency": lat})
    
    # Step 2: Thinking model reads decomposition, computes
    tile_text = f"Step 1 decomposition:\n{(content or reasoning)[:500]}"
    messages = [
        {"role": "system", "content": f"Read this decomposition and compute the final answer.\n\n{tile_text}\n\nGive the Final Answer."},
        {"role": "user", "content": prompt},
    ]
    content, reasoning, lat, tokens = query(model_think, messages, max_tokens=500)
    total_lat += lat
    total_tokens += tokens
    tiles.append({"step": 2, "model": "think", "content": content, "reasoning": reasoning, "latency": lat})
    
    ext = extract_num(content) or extract_num(reasoning)
    return ext, tiles, total_lat, total_tokens

def main():
    probes = [
        ("easy", "3 + 4", "7"),
        ("easy", "12 * 3", "36"),
        ("medium", "a*a + b*b where a=3, b=4", "25"),
        ("medium", "a*a - a*b + b*b where a=5, b=3", "19"),
        ("medium", "a+b+c+d+e where a=1,b=2,c=3,d=4,e=5", "15"),
        ("hard", "(a+b)*(a-b) where a=5, b=3", "16"),
        ("hard", "a*a - 2*a*b + b*b where a=4, b=3", "1"),
        ("hard", "a*a*b + b*b*a where a=2, b=3", "30"),
        ("hard", "2^10", "1024"),
        ("hard", "5*5 - 3*4 + 2*2", "17"),
        ("vhard", "a*a - 3*a*b + b*b where a=5, b=2", "-1"),
        ("vhard", "(a+b+c)*(a-b) where a=5, b=3, c=2", "8"),
    ]
    
    models = {
        "qwen-4b": "Qwen/Qwen3.5-4B",
        "seed-mini": "ByteDance/Seed-2.0-mini",
    }
    
    print("PLATO EXTERNAL COGNITION EXPERIMENT")
    print("="*70)
    print("Can externalized iteration match monolithic thinking?")
    print()
    
    all_results = []
    
    # Run all conditions
    def run_mono(mk, mid, p, e):
        ext, content, reasoning, lat, tok = run_monolithic(mid, p)
        return ext, "", lat, tok
    
    def run_plato4(mk, mid, p, e):
        ext, tiles, lat, tok = run_plato_chain(mid, p, max_steps=4)
        return ext, "", lat, tok
    
    def run_hybrid(mk, mid, p, e):
        partner = models.get("seed-mini" if mk != "seed-mini" else "qwen-4b", mid)
        ext, tiles, lat, tok = run_plato_hybrid(partner, mid, p)
        return ext, "", lat, tok
    
    conditions = [
        ("MONO", run_mono),
        ("PLATO-4", run_plato4),
        ("HYBRID", run_hybrid),
    ]
    
    for model_key, model_id in models.items():
        print(f"\n--- {model_key} ---", flush=True)
        
        for cond_name, cond_fn in conditions:
            correct = 0
            total = 0
            lats = []
            tokens_total = 0
            
            for difficulty, prompt, expected in probes:
                ext, _, lat, tokens = cond_fn(model_key, model_id, prompt, expected)
                ok = check(ext, expected)
                correct += ok
                total += 1
                lats.append(lat)
                tokens_total += tokens
                
                sym = "✓" if ok else "✗"
                if not ok:
                    print(f"  {sym} {cond_name:8s} [{difficulty:6s}] exp={expected:6s} got={str(ext):8s}", flush=True)
                
                all_results.append({
                    "model": model_key, "condition": cond_name,
                    "difficulty": difficulty, "expected": expected,
                    "got": ext, "correct": ok,
                    "latency": lat, "tokens": tokens,
                })
            
            acc = correct / total * 100
            avg_lat = sum(lats) / len(lats) if lats else 0
            print(f"  {cond_name:8s}: {correct}/{total} = {acc:.0f}%  lat={avg_lat:.0f}ms  tok={tokens_total}", flush=True)
    
    # Summary
    print(f"\n{'='*70}")
    print("COMPARISON: Does PLATO iteration match monolithic thinking?")
    print(f"{'='*70}")
    for model_key in models:
        for cond in ["MONO", "PLATO-4", "HYBRID"]:
            rs = [r for r in all_results if r["model"] == model_key and r["condition"] == cond]
            if rs:
                c = sum(1 for r in rs if r["correct"])
                print(f"  {model_key:12s} {cond:8s}: {c}/{len(rs)} = {c/len(rs)*100:.0f}%")
    
    with open("experiments/plato-cognition-results.json", "w") as f:
        json.dump({"results": all_results}, f, indent=2)
    print("\nSaved to experiments/plato-cognition-results.json")

if __name__ == "__main__":
    main()
