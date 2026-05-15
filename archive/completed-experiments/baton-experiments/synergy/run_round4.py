#!/usr/bin/env python3
"""
Baton Protocol Round 4: Hypothesis-driven follow-up
Tests:
  4a: Temperature sweep (0.3, 0.7, 1.0, 1.2, 1.5)
  4b: Extraction diversity (what does each model extract?)
  4c: Three-Seed ensemble (same model, different temps)
  4d: Seed-vs-Seed adversarial (same model, different modes)
"""

import os, json, urllib.request
from pathlib import Path

KEY = Path(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read_text().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OUT = Path("/home/phoenix/.openclaw/workspace/baton-experiments/synergy")

SOURCE = Path("/home/phoenix/.openclaw/workspace/baton-experiments/linear-handoff-reconstruction.txt").read_text()
GROUND_TRUTH = [
    "6 Galois proof parts verified", "1.4M+ total constructive checks",
    "XOR self-adjoint involution", "INT8 reflective subcategory",
    "Bloom filter Heyting algebra", "floor/ceil adjoints",
    "intent alignment tolerance-set", "holonomy cycle/subgraph",
    "14 facts tracked in telephone game", "6 rounds of telephone",
    "MV Epsilon drifted 200 meters east", "Narrows Strait",
    "4200 containers medical supplies", "47000 vessels at risk",
    "Round 2 recovered a lost fact", "crystallization at Round 3-4",
    "6 immortal facts survived", "Lila Marquez invented by Round 1",
    "forgetting-as-feature thesis", "accuracy and utility inversely correlated",
    "Ebbinghaus curve is rate-distortion bound", "lighthouse runtime orient relay gate",
    "first bootstrap 5 seeds at 0.50", "hex grid visualizer built",
    "gate caught credential leaks", "tile-memory Python library",
    "memory-crystal Rust library", "41/41 tests in memory-crystal",
    "collective-recall-demo 33KB HTML", "bridge connects to PLATO",
    "6 fleet services down", "Oracle1 needs console access",
    "Matrix send broken", "210/210 dodecet-encoder tests",
    "snap accuracy 63.9 to 99.4", "17 crates on crates.io",
    "INT8 x8 341B constraints/sec", "RTX 4050 memory-bound at 187 GB/s",
    "z.ai rate limits hit", "npm publish blocked",
]

def call(model, system, user, temp=0.7, max_tok=2000):
    mid = "ByteDance/Seed-2.0-mini" if model == "seed" else "Qwen/Qwen3.6-35B-A3B"
    payload = json.dumps({
        "model": mid, "messages": [
            {"role":"system","content":system},
            {"role":"user","content":user}
        ], "temperature": temp, "max_tokens": max_tok,
    }).encode()
    req = urllib.request.Request(URL, data=payload,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR: {e}]"

def score(text):
    low = text.lower()
    found = []
    for f in GROUND_TRUTH:
        terms = [t.lower() for t in f.split() if len(t) > 3]
        if sum(1 for t in terms if t in low) >= max(len(terms)*0.5, 1):
            found.append(f)
    return len(found), len(GROUND_TRUTH)

# === 4a: Temperature sweep ===
print("=== 4a: TEMPERATURE SWEEP ===")
for temp in [0.3, 0.7, 1.0, 1.2, 1.5]:
    r = call("seed", "Reconstruct this session for the next agent. Be comprehensive.",
             SOURCE, temp=temp)
    f, t = score(r)
    print(f"  temp={temp}: {f}/{t} = {f/t:.1%} | len={len(r)} | novel={len(set(r.lower().split()) - set(SOURCE.lower().split()))}")
    (OUT / f"r4-temp-{temp}.txt").write_text(r)

# === 4b: Extraction diversity ===
print("\n=== 4b: EXTRACTION DIVERSITY ===")
seed_ext = call("seed", "Extract the 20 most important facts as numbered bullet points. Each fact should be one short sentence.", SOURCE, temp=0.3)
qwen_ext = call("qwen", "Extract the 20 most important facts as numbered bullet points. Each fact should be one short sentence.", SOURCE, temp=0.3)

# Score each extraction against ground truth
sf, st = score(seed_ext)
qf, qt = score(qwen_ext)
print(f"  Seed extraction: {sf}/{st} = {sf/st:.1%}")
print(f"  Qwen extraction: {qf}/{qt} = {qf/qt:.1%}")

# What facts does each find that the other misses?
seed_facts = set()
qwen_facts = set()
for f in GROUND_TRUTH:
    terms = [t.lower() for t in f.split() if len(t) > 3]
    if sum(1 for t in terms if t in seed_ext.lower()) >= max(len(terms)*0.5, 1):
        seed_facts.add(f)
    if sum(1 for t in terms if t in qwen_ext.lower()) >= max(len(terms)*0.5, 1):
        qwen_facts.add(f)

print(f"  Seed-only facts: {seed_facts - qwen_facts}")
print(f"  Qwen-only facts: {qwen_facts - seed_facts}")
print(f"  Shared facts: {len(seed_facts & qwen_facts)}")
print(f"  Union: {len(seed_facts | qwen_facts)} / {len(GROUND_TRUTH)}")

(OUT / "r4-seed-extraction.txt").write_text(seed_ext)
(OUT / "r4-qwen-extraction.txt").write_text(qwen_ext)

# === 4c: Three-Seed ensemble ===
print("\n=== 4c: THREE-SEED ENSEMBLE (same model, different temps) ===")
tech = call("seed", "Extract ONLY concrete technical facts: numbers, files, tests, APIs, errors.", SOURCE, temp=0.3)
theory = call("seed", "Extract ONLY abstract concepts: theories, proofs, decisions, philosophy.", SOURCE, temp=0.7)
blocks = call("seed", "Extract ONLY what's blocked: errors, gaps, TODOs, missing items.", SOURCE, temp=1.0)
synth = call("seed", "Three views of the same session. Reconstruct completely for the next agent.",
             f"TECHNICAL:\n{tech}\n\nTHEORY:\n{theory}\n\nBLOCKED:\n{blocks}", temp=1.2)
f, t = score(synth)
print(f"  3-Seed ensemble: {f}/{t} = {f/t:.1%} | len={len(synth)}")
(OUT / "r4-three-seed-ensemble.txt").write_text(synth)

# === 4d: Seed-vs-Seed adversarial ===
print("\n=== 4d: SEED-vs-SEED ADVERSARIAL ===")
recon = call("seed", "Reconstruct this session for the next agent.", SOURCE, temp=0.3)
critique = call("seed",
    "You are an adversarial reviewer. Given the original and a reconstruction, list EVERYTHING missing or wrong. Be harsh and specific.",
    f"ORIGINAL:\n{SOURCE}\n\nRECONSTRUCTION:\n{recon}", temp=1.2)
revised = call("seed",
    "You made a reconstruction. A critic found these issues. Fix ALL of them.",
    f"Your reconstruction:\n{recon}\n\nCritique:\n{critique}", temp=0.7)
f, t = score(revised)
print(f"  Before critique: {score(recon)[0]}/{t} = {score(recon)[0]/t:.1%}")
print(f"  After critique:  {f}/{t} = {f/t:.1%}")
(OUT / "r4-adversarial-before.txt").write_text(recon)
(OUT / "r4-adversarial-critique.txt").write_text(critique)
(OUT / "r4-adversarial-after.txt").write_text(revised)

print("\n=== ROUND 4 COMPLETE ===")
