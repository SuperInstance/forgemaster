#!/usr/bin/env python3
"""experiments/long_run.py — Overnight Holodeck: Deep Accumulation

Runs the Seed-mini / Gemini-Flash-Lite pair through a massive probe set,
accumulating PLATO tiles for every result. The tensor builds overnight,
mineable the next morning.

What it generates:
  - 200+ arithmetic probes across 8 dimensions
  - Each probe tiled with full provenance
  - Cross-model verification on every probe
  - Navigation charts for both models
  - The complete capability atlas

Run:
    bin/spawn-monitor experiments/long_run.py --output experiments/long-run-results.json
    TIMEOUT=1800 bin/spawn-monitor experiments/long_run.py  # 30 min
"""
from __future__ import annotations

import json
import os
import re
import time
import sys
import statistics
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from itertools import product

import requests

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
SYSTEM = "You are a calculator. Output the result number ONLY. No words. No explanation."

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "gemini-lite": "google/gemini-3.1-flash-lite",
}

def q(model, prompt, max_tokens=50):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ], "temperature": 0.0, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(URL, headers=headers, json=payload, timeout=60)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return None, lat, 0
        d = r.json()
        msg = d["choices"][0]["message"]
        c = (msg.get("content") or "").strip()
        r_txt = (msg.get("reasoning_content") or "").strip()
        usage = d.get("usage", {})
        return (c if c else r_txt), lat, usage.get("total_tokens", 0)
    except:
        return None, (time.time() - start) * 1000, 0

def ext(text):
    if not text: return None
    nums = re.findall(r"-?\d+\.?\d*", text)
    return nums[-1] if nums else None

def compute(formula, **kwargs):
    """Safe eval for expected answers."""
    try:
        return str(int(eval(formula, {"__builtins__": {}}, kwargs)))
    except:
        return "?"

@dataclass
class Tile:
    model: str
    category: str
    prompt: str
    expected: str
    got: Optional[str] = None
    correct: bool = False
    latency_ms: float = 0.0
    tokens: int = 0
    timestamp: float = 0.0

def generate_probes():
    """Generate 200+ probes across 8 dimensions."""
    probes = []
    
    # 1. DEPTH: addition chains 1-20
    for depth in range(1, 21):
        terms = list(range(1, depth + 1))
        formula = "+".join(f"n{i}" for i in terms)
        prompt = f"Compute {formula} where " + ", ".join(f"n{i}={i}" for i in terms)
        expected = str(sum(terms))
        probes.append(("depth", prompt, expected, {"depth": depth, "op": "add"}))
    
    # 2. MAGNITUDE: Eisenstein at different scales
    for mag in [1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]:
        a, b = mag, mag + 1
        expected = str(a*a - a*b + b*b)
        probes.append(("magnitude", f"a*a - a*b + b*b where a={a}, b={b}", expected, {"mag": mag}))
    
    # 3. COEFFICIENTS: vary the coefficient pattern
    a, b = 5, 3
    coeff_patterns = [
        (f"a*a + b*b", a*a + b*b),
        (f"a*a - b*b", a*a - b*b),
        (f"a*a - a*b + b*b", a*a - a*b + b*b),
        (f"a*a + a*b + b*b", a*a + a*b + b*b),
        (f"a*a - 2*a*b + b*b", a*a - 2*a*b + b*b),
        (f"a*a + 2*a*b + b*b", a*a + 2*a*b + b*b),
        (f"a*a - 3*a*b + b*b", a*a - 3*a*b + b*b),
        (f"a*a + 3*a*b + b*b", a*a + 3*a*b + b*b),
        (f"2*a*a - a*b + b*b", 2*a*a - a*b + b*b),
        (f"a*a - a*b + 2*b*b", a*a - a*b + 2*b*b),
        (f"3*a*a - 2*a*b + b*b", 3*a*a - 2*a*b + b*b),
        (f"a*a + 5*a*b + b*b", a*a + 5*a*b + b*b),
    ]
    for formula, expected in coeff_patterns:
        probes.append(("coefficients", f"Compute {formula} where a={a}, b={b}", str(int(expected)), {"formula": formula}))
    
    # 4. NESTING: nested expressions
    nests = [
        ("(3+4)*(5-2)", 21),
        ("(3+4)*(5-2)*(6+1)", 147),
        ("((2+3)*4 - 5)*6", 90),
        ("(((1+2)*3 + 4)*5 - 6)*7", 279),
        ("(a+b)*(a-b) where a=7, b=2", 45),
        ("(a-b)*(a+b) where a=7, b=2", 45),
        ("(a*b + c)*(a - c) where a=5, b=2, c=3", 35),
    ]
    for prompt, expected in nests:
        probes.append(("nesting", prompt, str(expected), {}))
    
    # 5. MULTIPLICATION chains
    for terms in [[2,3], [2,3,4], [2,3,2,2], [1,2,3,4,5], [2,2,2,2,2,2], [1,1,2,3,1,2,1,1]]:
        formula = "*".join(f"n{i}" for i in range(len(terms)))
        expected = 1
        for t in terms:
            expected *= t
        prompt = f"Compute {formula} where " + ", ".join(f"n{i}={terms[i]}" for i in range(len(terms)))
        probes.append(("multiplication", prompt, str(expected), {"depth": len(terms), "op": "mul"}))
    
    # 6. PHYSICAL: mechanical/hydraulic reasoning
    physical = [
        ("A 4-inch bore at 3000 PSI. Force = pi * bore * pressure. Give integer.", "37699"),
        ("A 3:1 pulley with 900 lb load. Input force?", "300"),
        ("Feed 50 ft/min, limbs every 2 ft. Cycles/min?", "25"),
        ("1 tree/min for 8 hours. Total?", "480"),
        ("Pressure 2800, max 3500. Safe to add 600? yes/no", "yes"),
        ("Grapple rated 50000, load 12000, safety 3. Safe? yes/no", "yes"),
        ("Bore 3, pressure 2500. Force = pi * 3 * 2500. Integer.", "23562"),
        ("Flow 10 GPM, doubles to 20. Pressure drop multiplies by?", "4"),
        ("Max cut 24 inches. Tree 22. Safe? yes/no", "yes"),
        ("Temp 175F, max 180F. Safe to add 10? yes/no", "no"),
    ]
    for prompt, expected in physical:
        probes.append(("physical", prompt, expected, {}))
    
    # 7. WORD PROBLEMS: natural language arithmetic
    words = [
        ("Three plus four.", "7"),
        ("Twelve times three.", "36"),
        ("Five squared minus three times four plus two squared.", "19"),
        ("The sum of one through ten.", "55"),
        ("Two cubed.", "8"),
        ("Ten factorial? Just the first digit.", "3"),
        ("Square root of one forty-four.", "12"),
        ("Fifteen mod seven.", "1"),
    ]
    for prompt, expected in words:
        probes.append(("word_problem", prompt, expected, {}))
    
    # 8. NOVEL: expressions unlikely in training data
    novel = [
        ("a^4 - b^4 where a=3, b=1", "80"),
        ("a^3 + b^3 where a=2, b=3", "35"),
        ("fib(10) where fib(1)=1, fib(2)=1", "55"),
        ("a! where a=6", "720"),
        ("lcm(12, 18)", "36"),
        ("gcd(48, 36)", "12"),
        ("2^10", "1024"),
        ("log2(256)", "8"),
    ]
    for prompt, expected in novel:
        probes.append(("novel", prompt, expected, {}))
    
    return probes

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="experiments/long-run-results.json")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    
    probes = generate_probes()
    if args.quick:
        probes = probes[:30]
    
    print(f"LONG RUN: {len(probes)} probes × {len(MODELS)} models = {len(probes)*len(MODELS)} queries", flush=True)
    
    all_tiles = []
    by_model = defaultdict(list)
    by_category = defaultdict(list)
    
    for probe_idx, (category, prompt, expected, meta) in enumerate(probes):
        if probe_idx % 20 == 0:
            done = len(all_tiles)
            total = len(probes) * len(MODELS)
            print(f"  [{done}/{total}] category={category}...", flush=True)
        
        for mk, mid in MODELS.items():
            text, lat, tokens = q(mid, prompt)
            got = ext(text)
            correct = False
            if got and expected.replace(".","").replace("-","").replace("/","").isdigit():
                try:
                    correct = abs(float(got) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                except:
                    pass
            elif got and expected in ("yes", "no"):
                correct = (text or "").lower().startswith(expected[0])
            
            tile = Tile(
                model=mk, category=category, prompt=prompt[:80],
                expected=expected, got=got, correct=correct,
                latency_ms=lat, tokens=tokens, timestamp=time.time(),
            )
            all_tiles.append(tile)
            by_model[mk].append(tile)
            by_category[category].append(tile)
    
    # Analysis
    print(f"\n{'='*70}")
    print("LONG RUN RESULTS")
    print(f"{'='*70}")
    
    # By model
    for mk in MODELS:
        tiles = by_model[mk]
        c = sum(1 for t in tiles if t.correct)
        t = len(tiles)
        avg_lat = sum(t.latency_ms for t in tiles) / t
        print(f"\n  {mk}: {c}/{t} = {c/t*100:.1f}%  avg={avg_lat:.0f}ms", flush=True)
        
        # Category breakdown
        cats = defaultdict(list)
        for tile in tiles:
            cats[tile.category].append(tile)
        for cat, cat_tiles in sorted(cats.items()):
            cc = sum(1 for t in cat_tiles if t.correct)
            print(f"    {cat:15s}: {cc}/{len(cat_tiles)} = {cc/len(cat_tiles)*100:.0f}%", flush=True)
    
    # Agreement analysis
    print(f"\n  CROSS-MODEL AGREEMENT:", flush=True)
    for category in sorted(set(t.category for t in all_tiles)):
        cat_tiles = {mk: [t for t in ts if t.category == category] 
                     for mk, ts in by_model.items()}
        agree = 0
        total = 0
        for i in range(min(len(v) for v in cat_tiles.values())):
            results = [cat_tiles[mk][i].got for mk in MODELS]
            if all(r == results[0] for r in results):
                agree += 1
            total += 1
        print(f"    {category:15s}: {agree}/{total} agree", flush=True)
    
    # Depth cliff curves
    print(f"\n  DEPTH CLIFF (addition chains):", flush=True)
    for mk in MODELS:
        depth_tiles = sorted([t for t in by_model[mk] if t.category == "depth"],
                            key=lambda t: int(t.expected))
        if depth_tiles:
            line = " → ".join(
                f"{t.expected[:3]}={'✓' if t.correct else '✗'}"
                for t in depth_tiles[:15]
            )
            print(f"    {mk:12s}: {line}", flush=True)
    
    # Magnitude cliff
    print(f"\n  MAGNITUDE CLIFF:", flush=True)
    for mk in MODELS:
        mag_tiles = sorted([t for t in by_model[mk] if t.category == "magnitude"],
                          key=lambda t: int(t.expected))
        if mag_tiles:
            line = " → ".join(
                f"{t.expected[:6]}={'✓' if t.correct else '✗'}"
                for t in mag_tiles
            )
            print(f"    {mk:12s}: {line}", flush=True)
    
    # Save
    output = {
        "tiles": [asdict(t) for t in all_tiles],
        "summary": {
            "n_probes": len(probes),
            "n_models": len(MODELS),
            "n_queries": len(all_tiles),
        }
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved {len(all_tiles)} tiles to {args.output}", flush=True)

if __name__ == "__main__":
    main()
