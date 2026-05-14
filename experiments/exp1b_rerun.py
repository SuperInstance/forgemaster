#!/usr/bin/env python3
"""Rerun the two timed-out decompositions from Experiment 1"""
import requests, json, time, os

KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

decompositions = {
    "tile_with_perspective": {
        "name": "PLATO tile + perspectives",
        "prompt": "DO: Verify SplineLinear achieves 20x compression on drift-detect with 100% accuracy.\n\nNEED: SplineLinear stores Eisenstein int16 pairs instead of float64 weights. 16K parameters. Dense=8B/weight, SplineLinear=4B/weight.\n\nDONE WHEN: State compression ratio and accuracy.",
    },
    "jipr_atom": {
        "name": "JIPR atom (Intent+Context+Accept)",
        "prompt": "DO: Verify SplineLinear achieves 20x compression on drift-detect with 100% accuracy.\n\nNEED: SplineLinear replaces float64 weights with int16 Eisenstein pairs. 16K params. Compression = 8B/4B per weight.\n\nDONE WHEN: You state the compression ratio and accuracy.",
    },
}

def query(prompt):
    resp = requests.post(URL,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": "ByteDance/Seed-2.0-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0},
        timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

def score(r):
    s = 0
    r = r.lower()
    if any(x in r for x in ["2x","4x","8x","16x","20x"]): s += 1
    elif "compression" in r: s += 0.5
    if "100%" in r or "accuracy" in r: s += 1
    if any(x in r for x in ["eisenstein","int16","lattice","parameter"]): s += 0.5
    if "2x" in r or "20x" in r: s += 0.5
    return min(s, 3)

for key, d in decompositions.items():
    print(f"Testing: {d['name']}...", end=" ", flush=True)
    try:
        start = time.time()
        r = query(d["prompt"])
        elapsed = time.time() - start
        s = score(r)
        print(f"score={s:.1f} time={elapsed:.1f}s")
        print(f"  Response: {r[:200]}")
    except Exception as e:
        print(f"ERROR: {e}")
