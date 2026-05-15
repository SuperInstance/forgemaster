#!/usr/bin/env python3
"""experiments/plato_iterative.py — Externalized Cognition Through PLATO Iteration

Core hypothesis: A model doing N open iterations (read→write→read→write)
through PLATO tiles can match or exceed the same model with thinking ON,
because each iteration builds accumulated context that replaces internal reasoning.

Three conditions:
  A) THINKING ON: Single call with max_tokens=500, thinking mode active
  B) PLATO ITERATIVE: N calls with max_tokens=50 each, each reads previous tiles
  C) BARE: Single call with max_tokens=50, no thinking, no iteration

The PLATO advantage: every intermediate step is a frozen tile that can be:
  - Rewound to any point
  - Branched (spreader-tool: send step K to multiple models)
  - Audited (show your work becomes literal)
  - Accumulated (next agent starts from step K, not zero)

Models tested: Qwen3.5-4B (needs thinking), Seed-2.0-mini (doesn't need thinking)
"""
import requests, re, time, json, os
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
SYSTEM_CALC = "Output ONLY the final number."
SYSTEM_STEP = "You are reasoning step by step. For each step, write exactly ONE clear step of reasoning, then write STEP RESULT: <number> if you can compute a partial result. Be concise."
SYSTEM_READ = "You are continuing a chain of reasoning. Read the previous steps below, then write your NEXT step and any partial result. Be concise."

@dataclass
class Tile:
    step: int
    content: str
    partial_result: Optional[str] = None
    model: str = ""
    latency_ms: float = 0.0

@dataclass 
class TrialResult:
    condition: str  # "thinking", "plato_iter", "bare"
    probe: str
    expected: str
    extracted: Optional[str] = None
    correct: bool = False
    tiles: List[Dict] = field(default_factory=list)
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    iterations: int = 0

def query(model, messages, max_tokens=50, temperature=0.0):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(URL, headers=headers, json=payload, timeout=120)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return None, lat, 0
        d = r.json()
        msg = d["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or "").strip()
        text = content if content else reasoning
        usage = d.get("usage", {})
        return text, lat, usage.get("total_tokens", 0)
    except Exception as e:
        return None, (time.time() - start) * 1000, 0

def extract_num(text):
    if not text: return None
    # Look for STEP RESULT first
    m = re.search(r'STEP RESULT:\s*(-?\d+\.?\d*)', text)
    if m: return m.group(1)
    # Fall back to last number
    nums = re.findall(r'-?\d+\.?\d*', text)
    return nums[-1] if nums else None

def extract_final(text):
    """Extract the final answer from accumulated tiles."""
    if not text: return None
    # Look for FINAL ANSWER
    m = re.search(r'FINAL ANSWER:\s*(-?\d+\.?\d*)', text)
    if m: return m.group(1)
    return extract_num(text)

# ─── The Three Conditions ─────────────────────────────────────────────────

def run_thinking(model_id, prompt, max_tokens=500):
    """Condition A: Thinking ON, single call."""
    messages = [
        {"role": "system", "content": SYSTEM_STEP + " End with FINAL ANSWER: <number>"},
        {"role": "user", "content": prompt},
    ]
    text, lat, tokens = query(model_id, messages, max_tokens=max_tokens)
    return extract_final(text), [{"step": 0, "content": text, "latency": lat}], lat, tokens

def run_bare(model_id, prompt, max_tokens=50):
    """Condition C: Bare, no thinking, no iteration."""
    messages = [
        {"role": "system", "content": SYSTEM_CALC},
        {"role": "user", "content": prompt + " Give ONLY the final number."},
    ]
    text, lat, tokens = query(model_id, messages, max_tokens=max_tokens)
    ext = extract_num(text)
    return ext, [{"step": 0, "content": text, "latency": lat}], lat, tokens

def run_plato_iterative(model_id, prompt, max_iters=5, max_tokens_per=80):
    """Condition B: PLATO-iterative, N passes each reading previous tiles."""
    tiles = []
    total_lat = 0
    total_tokens = 0
    final_extracted = None
    
    # Step 1: Initial reasoning step
    messages = [
        {"role": "system", "content": SYSTEM_STEP + " End with STEP RESULT: <number> if you can compute anything, or describe what you need next."},
        {"role": "user", "content": prompt},
    ]
    text, lat, tok = query(model_id, messages, max_tokens=max_tokens_per)
    total_lat += lat
    total_tokens += tok
    
    # Save as tile
    partial = extract_num(text)
    tiles.append({"step": 1, "content": text, "partial": partial, "latency": lat})
    
    # Steps 2-N: Read previous tiles, write next step
    for step in range(2, max_iters + 1):
        # Build context from previous tiles
        tile_context = "\n".join(
            f"Step {t['step']}: {t['content']}" 
            for t in tiles
        )
        
        if step == max_iters:
            # Final step: extract answer
            system = SYSTEM_READ + f"\n\nPrevious steps:\n{tile_context}\n\nThis is the FINAL step. Give the FINAL ANSWER: <number>"
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        else:
            system = SYSTEM_READ + f"\n\nPrevious steps:\n{tile_context}\n\nWrite step {step}. End with STEP RESULT: <number> if you can compute anything."
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        
        text, lat, tok = query(model_id, messages, max_tokens=max_tokens_per)
        total_lat += lat
        total_tokens += tok
        
        partial = extract_num(text)
        tiles.append({"step": step, "content": text, "partial": partial, "latency": lat})
        
        # If we got a clear answer, stop early
        if step >= 3:
            final = extract_final(text)
            if final and partial:
                break
    
    # Extract from last tile
    last = tiles[-1]["content"]
    final_extracted = extract_final(last) or tiles[-1].get("partial")
    
    return final_extracted, tiles, total_lat, total_tokens

def check(got, expected, tol=0.05):
    if not got or not expected: return False
    try:
        g, e = float(got), float(expected)
        if e == 0: return abs(g) < 0.01
        return abs(g - e) / abs(e) <= tol
    except: return False

def main():
    probes = [
        ("easy", "3 + 4", "7"),
        ("easy", "12 * 3", "36"),
        ("medium", "a*a + b*b where a=3, b=4", "25"),
        ("medium", "a*a - a*b + b*b where a=5, b=3", "19"),
        ("medium", "a+b+c+d+e where a=1,b=2,c=3,d=4,e=5", "15"),
        ("medium", "(a+b)*(a-b) where a=5, b=3", "16"),
        ("hard", "a*a - 2*a*b + b*b where a=4, b=3", "1"),
        ("hard", "a*a*b + b*b*a where a=2, b=3", "30"),
        ("hard", "2^10", "1024"),
        ("hard", "5*5 - 3*4 + 2*2", "17"),
        ("vhard", "a*a - 3*a*b + b*b where a=5, b=2", "-1"),
        ("vhard", "(a+b+c)*(a-b) where a=5, b=3, c=2", "8"),
    ]
    
    models = {
        "qwen-4b": "Qwen/Qwen3.5-4B",
        "qwen-9b": "Qwen/Qwen3.5-9B",
        "seed-mini": "ByteDance/Seed-2.0-mini",
    }
    
    all_results = []
    
    for model_key, model_id in models.items():
        print(f"\n{'='*70}")
        print(f"MODEL: {model_key}")
        print(f"{'='*70}")
        
        for condition_name, condition_fn, iters in [
            ("THINKING", lambda m, p: run_thinking(m, p, max_tokens=500), 1),
            ("PLATO-5", lambda m, p: run_plato_iterative(m, p, max_iters=5), 5),
            ("PLATO-3", lambda m, p: run_plato_iterative(m, p, max_iters=3), 3),
            ("BARE", lambda m, p: run_bare(m, p, max_tokens=50), 1),
        ]:
            correct = 0
            total = 0
            lats = []
            tokens = 0
            
            for difficulty, prompt, expected in probes:
                ext, tiles, lat, tok = condition_fn(model_id, prompt)
                ok = check(ext, expected)
                correct += ok
                total += 1
                lats.append(lat)
                tokens += tok
                
                sym = "✓" if ok else "✗"
                if not ok:
                    # Show the tile chain for failures
                    print(f"  {sym} {condition_name:10s} [{difficulty:6s}] expected={expected:8s} got={str(ext):10s} tiles={len(tiles)}", flush=True)
                    for t in tiles:
                        content_preview = t["content"][:80].replace("\n", " ")
                        print(f"      step {t['step']}: {content_preview}...", flush=True)
                
                all_results.append({
                    "model": model_key,
                    "condition": condition_name,
                    "difficulty": difficulty,
                    "prompt": prompt[:40],
                    "expected": expected,
                    "got": ext,
                    "correct": ok,
                    "tiles": len(tiles),
                    "latency_ms": lat,
                    "tokens": tok,
                })
            
            acc = correct / total * 100
            avg_lat = sum(lats) / len(lats) if lats else 0
            print(f"  {condition_name:10s}: {correct}/{total} = {acc:.0f}%  lat={avg_lat:.0f}ms  tokens={tokens}  tiles_per={iters}", flush=True)
    
    # Save
    with open("experiments/plato-iterative-results.json", "w") as f:
        json.dump({"results": all_results}, f, indent=2)
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY: Does PLATO iteration match thinking mode?")
    print(f"{'='*70}")
    for model_key in models:
        for condition in ["THINKING", "PLATO-5", "PLATO-3", "BARE"]:
            results = [r for r in all_results if r["model"] == model_key and r["condition"] == condition]
            if results:
                c = sum(1 for r in results if r["correct"])
                t = len(results)
                avg_lat = sum(r["latency_ms"] for r in results) / t
                avg_tok = sum(r["tokens"] for r in results) / t
                print(f"  {model_key:12s} {condition:10s}: {c}/{t} = {c/t*100:.0f}%  lat={avg_lat:.0f}ms  tok={avg_tok:.0f}")
    
    print("\nSaved to experiments/plato-iterative-results.json")

if __name__ == "__main__":
    main()
