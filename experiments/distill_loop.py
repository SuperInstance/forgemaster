#!/usr/bin/env python3
"""
PLATO Distillation Loop — Groq-Powered
========================================
Uses the student seed (role + named operation + code notation) to decompose
repo functions into PLATO tiles at ~26ms per query.

The loop:
1. Read a Python function from the codebase
2. Prompt llama-3.1-8b-instant with the student seed
3. Extract decomposition tiles
4. Classify output quality (tile vs noise)
5. Push valid tiles to PLATO server
6. Iterate across the repo

This is the bootstrap: agents get PLATO tiles as first-class knowledge.
"""
import requests, re, json, time, os, sys
from pathlib import Path

GROQ_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
PLATO_URL = "http://147.224.38.131:8847"

MODEL = "llama-3.1-8b-instant"

# The student seed — proven to evoke computation
DISTILL_SYSTEM = """You are a student software architect documenting code. Output ONLY valid JSON, no other text.
Format: {"tiles": [{"id": "func-topic", "type": "knowledge|operation|verification", "content": "description", "deps": []}]}
Produce 1-3 tiles per function. Be precise about what, how, and edge cases."""

def groq_distill(prompt):
    """Distill a function into PLATO tiles using the student seed."""
    r = requests.post(GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={"model": MODEL, "messages": [
            {"role": "system", "content": DISTILL_SYSTEM},
            {"role": "user", "content": prompt}
        ], "temperature": 0.1, "max_tokens": 500},
        timeout=30)
    
    content = r.json()["choices"][0]["message"]["content"].strip()
    usage = r.json().get("usage", {})
    
    # Try to extract JSON from response
    text = content.strip()
    # Strip markdown code blocks
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```', '', text)
    
    # Strategy 1: Direct parse
    try:
        data = json.loads(text)
        return data.get("tiles", []), content, usage
    except:
        pass
    
    # Strategy 2: Find ALL {"tiles":...} blocks and merge
    all_tiles = []
    for m in re.finditer(r'\{"tiles"\s*:\s*\[', text):
        start = m.start()
        # Find matching closing bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            if depth == 0:
                try:
                    block = json.loads(text[start:i+1])
                    all_tiles.extend(block.get("tiles", []))
                except:
                    pass
                break
    
    if all_tiles:
        return all_tiles, content, usage
    
    # Strategy 3: Brace range
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            return data.get("tiles", []), content, usage
    except:
        pass
    
    return [], content, usage

def extract_functions(filepath):
    """Extract Python function signatures + docstrings from a file."""
    with open(filepath) as f:
        source = f.read()
    
    # Find function definitions
    funcs = []
    lines = source.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('def ') or line.startswith('async def '):
            # Capture the full function
            func_lines = [line]
            indent = len(line) - len(line.lstrip())
            j = i + 1
            while j < len(lines):
                if lines[j].strip() == '' or (lines[j].strip() and not lines[j].startswith(' ' * (indent + 1)) and not lines[j].startswith('\t' * (indent + 1)) and lines[j][0] != '#'):
                    if lines[j].startswith('def ') or lines[j].startswith('class ') or lines[j].startswith('async def '):
                        break
                    if lines[j].strip() == '' and j + 1 < len(lines) and (lines[j+1].startswith('def ') or lines[j+1].startswith('class ')):
                        break
                    func_lines.append(lines[j])
                else:
                    func_lines.append(lines[j])
                j += 1
            
            func_source = '\n'.join(func_lines)
            if len(func_source) > 50:  # Skip trivial functions
                funcs.append(func_source)
            i = j
        else:
            i += 1
    
    return funcs

def classify_tile_quality(tiles, original_func):
    """Rate tile quality 0-3."""
    if not tiles:
        return 0, "No tiles extracted"
    
    score = 0
    reasons = []
    
    # Has at least one tile
    score += 1
    reasons.append("Has tiles")
    
    # Tiles have meaningful content (>20 chars)
    if any(len(t.get("content", "")) > 20 for t in tiles):
        score += 1
        reasons.append("Meaningful content")
    
    # Tiles reference the actual function
    func_name = original_func.split('(')[0].replace('def ', '').strip()
    if any(func_name in t.get("id", "") or func_name in t.get("content", "") for t in tiles):
        score += 1
        reasons.append(f"References {func_name}")
    
    return score, "; ".join(reasons)

def distill_file(filepath):
    """Distill a Python file into PLATO tiles."""
    print(f"\n{'='*60}", flush=True)
    print(f"  DISTILLING: {filepath}", flush=True)
    print(f"{'='*60}", flush=True)
    
    funcs = extract_functions(filepath)
    print(f"  Found {len(funcs)} functions", flush=True)
    
    all_tiles = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    
    for i, func in enumerate(funcs):
        func_name = func.split('(')[0].replace('def ', '').replace('async ', '').strip()
        if func_name.startswith('_'):
            print(f"  [{i+1}/{len(funcs)}] {func_name} — skipped (private)", flush=True)
            continue
        
        # Truncate long functions
        if len(func) > 2000:
            func = func[:2000] + "\n    # ... (truncated)"
        
        prompt = f"""Analyze this Python function and produce PLATO tiles:

```python
{func}
```

The function is from file: {filepath}
Produce tiles covering: what it does, how it works, edge cases, constraints, dependencies."""
        
        tiles, raw, usage = groq_distill(prompt)
        quality, reason = classify_tile_quality(tiles, func)
        
        total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        
        quality_sym = "✅" if quality >= 2 else "⚠️" if quality >= 1 else "❌"
        print(f"  [{i+1}/{len(funcs)}] {func_name:<30s} → {len(tiles)} tiles {quality_sym} ({reason})", flush=True)
        
        if quality >= 2:
            all_tiles.extend(tiles)
        
        time.sleep(0.3)
    
    print(f"\n  TOTAL: {len(all_tiles)} quality tiles from {len(funcs)} functions", flush=True)
    print(f"  Usage: {total_usage['prompt_tokens']} prompt + {total_usage['completion_tokens']} completion tokens", flush=True)
    
    return all_tiles

def main():
    """Distill the key Cocapn repos into PLATO tiles."""
    
    workspace = Path("/home/phoenix/.openclaw/workspace")
    
    # Priority files for distillation (the core infrastructure)
    target_files = [
        "bin/decomp.py",
        "bin/lighthouse.py",
        "bin/fleet-navigator.py",
        "experiments/percolation_model.py",
        "experiments/wheel_of_discovery.py",
        "experiments/prompt_sensitivity.py",
        "experiments/rapid_loop.py",
        "experiments/echo_analysis.py",
        "experiments/reverse_actualization.py",
    ]
    
    print("╔════════════════════════════════════════════════════════╗", flush=True)
    print("║  PLATO DISTILLATION LOOP — Groq-Powered               ║", flush=True)
    print("║  Student seed → repo functions → PLATO tiles           ║", flush=True)
    print("╚════════════════════════════════════════════════════════╝", flush=True)
    
    total_tiles = []
    total_files = 0
    
    for filepath in target_files:
        full_path = workspace / filepath
        if not full_path.exists():
            print(f"  SKIP: {filepath} not found", flush=True)
            continue
        
        tiles = distill_file(str(full_path))
        total_tiles.extend(tiles)
        total_files += 1
        
        # Rate limit
        time.sleep(1)
    
    print(f"\n\n{'='*60}", flush=True)
    print(f"  DISTILLATION COMPLETE", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"  Files processed: {total_files}", flush=True)
    print(f"  Total tiles: {len(total_tiles)}", flush=True)
    
    # Save tiles
    output = {
        "source": "rapid-distillation-loop",
        "model": MODEL,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tiles": total_tiles,
    }
    
    outpath = workspace / "experiments" / "distilled-tiles.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"  Saved to: {outpath}", flush=True)
    
    # Show tile types
    types = {}
    for t in total_tiles:
        ty = t.get("type", "unknown")
        types[ty] = types.get(ty, 0) + 1
    print(f"  Tile types: {types}", flush=True)

if __name__ == "__main__":
    main()
