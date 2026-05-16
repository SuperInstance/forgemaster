#!/usr/bin/env python3
"""
Zoom Precision Experiment — Resilient version with batching and checkpoint/resume.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

DEEPINFRA_KEY_PATH = Path.home() / ".openclaw" / "workspace" / ".credentials" / "deepinfra-api-key.txt"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "ByteDance/Seed-2.0-mini"
RESULTS_DIR = Path.home() / ".openclaw" / "workspace" / "experiments"
CHECKPOINT_PATH = RESULTS_DIR / "zoom-precision-checkpoint.json"

TILES = [
    {"id": "T01", "claim": "2 + 2 = 4", "domain": "math", "expected_true": True},
    {"id": "T02", "claim": "The sum of angles in a Euclidean triangle is 180°", "domain": "math", "expected_true": True},
    {"id": "T03", "claim": "There are infinitely many prime numbers", "domain": "math", "expected_true": True},
    {"id": "T04", "claim": "3, 4, 5 form a Pythagorean triple", "domain": "math", "expected_true": True},
    {"id": "T05", "claim": "sort([3,1,2]) = [1,2,3]", "domain": "code", "expected_true": True},
    {"id": "T06", "claim": "Binary search runs in O(log n) time", "domain": "code", "expected_true": True},
    {"id": "T07", "claim": "A hash table provides O(1) average lookup", "domain": "code", "expected_true": True},
    {"id": "T08", "claim": "The Earth is flat", "domain": "fact", "expected_true": False},
    {"id": "T09", "claim": "Water boils at 100°C at standard pressure", "domain": "fact", "expected_true": True},
    {"id": "T10", "claim": "The speed of light in vacuum is approximately 3×10⁸ m/s", "domain": "physics", "expected_true": True},
    {"id": "T11", "claim": "Energy is conserved in a closed system", "domain": "physics", "expected_true": True},
    {"id": "T12", "claim": "Entropy always increases", "domain": "physics", "expected_true": True},
    {"id": "T13", "claim": "Momentum is conserved in elastic collisions", "domain": "physics", "expected_true": True},
    {"id": "T14", "claim": "Seed-2.0-mini is a Tier 1 model", "domain": "fleet", "expected_true": True},
    {"id": "T15", "claim": "PLATO rooms can execute agent tasks autonomously", "domain": "fleet", "expected_true": True},
    {"id": "T16", "claim": "The Cocapn fleet has 9 agents", "domain": "fleet", "expected_true": True},
    {"id": "T17", "claim": "All swans are white", "domain": "logic", "expected_true": False},
    {"id": "T18", "claim": "Machine learning models generalize to unseen data", "domain": "ml", "expected_true": True},
    {"id": "T19", "claim": "P equals NP", "domain": "math", "expected_true": False},
    {"id": "T20", "claim": "A neural network with sufficient width can approximate any continuous function", "domain": "ml", "expected_true": True},
]

ZOOM_PROMPTS = {
    0: 'Consider this claim: "{claim}"\n\nIs this claim TRUE or FALSE? Respond with exactly one word (TRUE or FALSE) followed by a one-sentence justification.',
    1: 'Consider this claim: "{claim}"\n\nAt Level 0, this was classified as {level0_result}. Now zoom in: Under what specific CONDITIONS does this claim hold or break? List 2-4 boundary conditions.',
    2: 'Consider this claim: "{claim}"\n\nWe\'ve established its truth value and boundary conditions. Now zoom deeper: What is the PROOF or EVIDENCE for this claim? What mechanism makes it true or false?',
    3: 'Consider this claim: "{claim}"\n\nWe know the truth, conditions, and proof. Now zoom to failure: WHERE DOES THIS BREAK? What are the specific failure modes? If it never breaks, explain WHY.',
    4: 'Consider this claim: "{claim}"\n\nWe\'ve examined truth, conditions, proof, and failure modes. Now zoom to the highest level: What\'s the NEXT-ORDER EFFECT? What higher structure does this connect to?',
}

CLASSIFY_PROMPT = '''Based on the following 5-level zoom analysis of "{claim}", classify it into ONE category:

GEOMETRIC: Survives all zoom levels unchanged. Universally true/false. (Like 2+2=4)
STATISTICAL: Survives with increasing caveats and precision requirements. (Like "water boils at 100°C")
BOUNDARY: Breaks at a specific zoom level with a clear threshold. (Like "all swans are white")
CONTEXTUAL: Meaning itself changes at each zoom level. "True" shifts with abstraction. (Like "this model is Tier 1")

Level 0 (Binary): {level0}
Level 1 (Conditions): {level1}
Level 2 (Proof): {level2}
Level 3 (Failure): {level3}
Level 4 (Next-order): {level4}

Respond with EXACTLY one of: GEOMETRIC, STATISTICAL, BOUNDARY, CONTEXTUAL
Then 2-3 sentences of reasoning.'''


def call_api(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise analytical assistant. Be concise."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }).encode()

    req = urllib.request.Request(DEEPINFRA_ENDPOINT, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (attempt + 1))
            else:
                return f"[HTTP {e.code}]"
        except Exception as e:
            time.sleep(3)
    return "[FAILED]"


def load_checkpoint():
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {}


def save_checkpoint(data):
    CHECKPOINT_PATH.write_text(json.dumps(data, indent=2))


def process_tile(tile, api_key, checkpoint):
    tid = tile["id"]
    if tid in checkpoint:
        print(f"  [{tid}] Loaded from checkpoint", flush=True)
        return checkpoint[tid]

    result = {"id": tid, "claim": tile["claim"], "domain": tile["domain"], "expected_true": tile["expected_true"], "zoom_levels": {}}
    
    level0_result = ""
    for level in range(5):
        if level == 0:
            prompt = ZOOM_PROMPTS[0].format(claim=tile["claim"])
        elif level == 1:
            prompt = ZOOM_PROMPTS[1].format(claim=tile["claim"], level0_result=level0_result)
        else:
            prompt = ZOOM_PROMPTS[level].format(claim=tile["claim"])

        print(f"  [{tid}] L{level}...", end=" ", flush=True)
        response = call_api(prompt, api_key)
        result["zoom_levels"][str(level)] = response[:500]  # Truncate to save memory
        print(f"({len(response)}ch)", flush=True)

        if level == 0:
            level0_result = "TRUE" if response.upper().strip().startswith("TRUE") else "FALSE"

        time.sleep(0.8)

    # Classify
    print(f"  [{tid}] Classifying...", end=" ", flush=True)
    cp = CLASSIFY_PROMPT.format(
        claim=tile["claim"],
        level0=result["zoom_levels"]["0"][:250],
        level1=result["zoom_levels"]["1"][:250],
        level2=result["zoom_levels"]["2"][:250],
        level3=result["zoom_levels"]["3"][:250],
        level4=result["zoom_levels"]["4"][:250],
    )
    classification_response = call_api(cp, api_key)
    
    result["classification"] = "UNKNOWN"
    for cat in ["GEOMETRIC", "STATISTICAL", "BOUNDARY", "CONTEXTUAL"]:
        if cat in classification_response.upper():
            result["classification"] = cat
            break
    result["classification_reasoning"] = classification_response
    print(f"→ {result['classification']}", flush=True)

    checkpoint[tid] = result
    save_checkpoint(checkpoint)
    
    # Free memory
    import gc
    gc.collect()
    return result


def classify_depth(r):
    c = r["classification"]
    if c == "GEOMETRIC":
        r["breaks_at"] = None
        r["room_depth"] = 0
    elif c == "STATISTICAL":
        r["breaks_at"] = 4
        r["room_depth"] = 1
    elif c == "BOUNDARY":
        l3 = r["zoom_levels"].get("3", "").lower()
        r["breaks_at"] = 3 if any(w in l3 for w in ["break", "fail", "exception", "limit", "threshold"]) else 2
        r["room_depth"] = 2
    elif c == "CONTEXTUAL":
        r["breaks_at"] = 1
        r["room_depth"] = 3
    else:
        r["breaks_at"] = 2
        r["room_depth"] = 1


def generate_report(results):
    total = len(results)
    counts = {}
    for r in results:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1

    mandelbrot = counts.get("BOUNDARY", 0) + counts.get("CONTEXTUAL", 0)
    mandelbrot_frac = mandelbrot / total if total else 0

    depths = [r["room_depth"] for r in results]
    avg_depth = sum(depths) / len(depths) if depths else 0
    max_depth = max(depths) if depths else 0

    # Survival curve
    survival = {}
    for lvl in range(5):
        survival[lvl] = sum(1 for r in results if r["breaks_at"] is None or r["breaks_at"] > lvl)

    L = []
    L.append("# Zoom Precision Experiment — Results\n")
    L.append("> *How many orders of magnitude can a tile survive before needing its own room?*\n")
    L.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}  ")
    L.append(f"**Model:** {MODEL} (DeepInfra)  ")
    L.append(f"**Tiles:** {total} | **API Calls:** {total * 6}\n")

    L.append("## Executive Summary\n")
    L.append("| Classification | Count | Fraction | Room Depth |")
    L.append("|---|---|---|---|")
    depth_map = {"GEOMETRIC": 0, "STATISTICAL": 1, "BOUNDARY": 2, "CONTEXTUAL": 3}
    for cat in ["GEOMETRIC", "STATISTICAL", "BOUNDARY", "CONTEXTUAL"]:
        c = counts.get(cat, 0)
        L.append(f"| {cat} | {c} | {c/total*100:.0f}% | {depth_map.get(cat, '?')} |")
    L.append(f"\n**Mandelbrot Fraction** (BOUNDARY + CONTEXTUAL): **{mandelbrot}/{total} = {mandelbrot_frac*100:.0f}%**  ")
    L.append(f"**Average Room Nesting Depth:** {avg_depth:.1f}  ")
    L.append(f"**Maximum Room Nesting Depth:** {max_depth}\n")

    L.append("## Survival Curve\n")
    L.append("```")
    for i in range(5):
        bar = "█" * survival[i]
        L.append(f"  Level {i}: {bar:<20s} {survival[i]:2d}/{total} ({survival[i]/total*100:.0f}%)")
    L.append("```\n")

    L.append("## Classification Table\n")
    L.append("| ID | Claim | Domain | Classification | Breaks At | Room Depth |")
    L.append("|---|---|---|---|---|---|")
    for r in results:
        b = f"L{r['breaks_at']}" if r["breaks_at"] is not None else "Never"
        c = r["claim"][:50] + ("..." if len(r["claim"]) > 50 else "")
        L.append(f"| {r['id']} | {c} | {r['domain']} | {r['classification']} | {b} | {r['room_depth']} |")
    L.append("")

    L.append("## Detailed Zoom Analysis\n")
    for r in results:
        L.append(f"### {r['id']}: \"{r['claim']}\"")
        break_str = 'Never' if r['breaks_at'] is None else f'L{r["breaks_at"]}'
        L.append(f"**{r['classification']}** | {r['domain']} | Breaks: {break_str} | Depth: {r['room_depth']}\n")
        for level in range(5):
            resp = r["zoom_levels"].get(str(level), "")
            if len(resp) > 350:
                resp = resp[:350] + "..."
            names = {0: "Binary", 1: "Conditions", 2: "Proof", 3: "Failure", 4: "Next-Order"}
            L.append(f"**L{level} ({names[level]}):** {resp}\n")
        L.append(f"**Reasoning:** {r.get('classification_reasoning', '')[:400]}\n")
        L.append("---\n")

    L.append("## Domain Analysis\n")
    domains = sorted(set(r["domain"] for r in results))
    for d in domains:
        dr = [r for r in results if r["domain"] == d]
        dc = {}
        for r in dr:
            dc[r["classification"]] = dc.get(r["classification"], 0) + 1
        cs = ", ".join(f"{k}: {v}" for k, v in sorted(dc.items()))
        L.append(f"**{d}** ({len(dr)} tiles): {cs} — avg depth {sum(r['room_depth'] for r in dr)/len(dr):.1f}")
    L.append("")

    L.append("## The Mandelbrot Fraction\n")
    L.append(f"- **GEOMETRIC** ({counts.get('GEOMETRIC',0)}/{total}): Self-contained, no sub-rooms.")
    L.append(f"- **STATISTICAL** ({counts.get('STATISTICAL',0)}/{total}): Need measurement sub-room.")
    L.append(f"- **BOUNDARY** ({counts.get('BOUNDARY',0)}/{total}): Need boundary sub-room (recursive).")
    L.append(f"- **CONTEXTUAL** ({counts.get('CONTEXTUAL',0)}/{total}): Need context sub-room per zoom (infinite recursion).")
    L.append(f"\n**Mandelbrot Fraction = {mandelbrot}/{total} = {mandelbrot_frac*100:.0f}%**")
    L.append(f"\nFor a 10,000-tile library: ~{int(10000 * avg_depth + 10000):,} total rooms, ~{int(10000 * mandelbrot_frac):,} recursive.\n")

    L.append("## Expected vs Actual\n")
    L.append("| Classification | Expected | Actual |")
    L.append("|---|---|---|")
    exp = {"GEOMETRIC": "~20%", "STATISTICAL": "~40%", "BOUNDARY": "~30%", "CONTEXTUAL": "~10%"}
    for cat in ["GEOMETRIC", "STATISTICAL", "BOUNDARY", "CONTEXTUAL"]:
        L.append(f"| {cat} | {exp[cat]} | {counts.get(cat,0)/total*100:.0f}% |")
    L.append("")

    L.append("## Implications for PLATO Architecture\n")
    L.append("1. **Room Creation Trigger:** BOUNDARY/CONTEXTUAL tiles → auto-spawn sub-room.")
    L.append("2. **Geometric Tiles are Free:** Boolean flags, zero room overhead.")
    L.append(f"3. **Room Budget:** ~{sum(depths)} rooms per {total} tiles. Scale linearly for geometric, exponential for Mandelbrot.")
    L.append(f"4. **Mandelbrot Boundary is Real:** {mandelbrot_frac*100:.0f}% of knowledge enters recursive territory.")
    L.append("5. **Zoom Level = Room Depth:** Room at depth N handles Nth-order precision.\n")

    return "\n".join(L)


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    api_key = DEEPINFRA_KEY_PATH.read_text().strip()
    
    checkpoint = load_checkpoint()
    done_tiles = len(checkpoint)
    remaining = [t for t in TILES if t["id"] not in checkpoint]
    
    print(f"=" * 60)
    print(f"  ZOOM PRECISION EXPERIMENT")
    print(f"  {done_tiles} cached, {len(remaining)} remaining")
    print(f"=" * 60)
    
    for i, tile in enumerate(remaining):
        print(f"\n[{done_tiles + i + 1}/{len(TILES)}] {tile['id']}: {tile['claim'][:50]}...")
        process_tile(tile, api_key, checkpoint)
        time.sleep(1)

    # Load all results
    checkpoint = load_checkpoint()
    results = []
    for tile in TILES:
        r = checkpoint[tile["id"]]
        classify_depth(r)
        results.append(r)

    report = generate_report(results)
    report_path = RESULTS_DIR / "ZOOM-PRECISION-RESULTS.md"
    report_path.write_text(report)
    
    raw_path = RESULTS_DIR / "zoom-precision-raw.json"
    raw_path.write_text(json.dumps(results, indent=2))
    
    print(f"\n{'='*60}")
    print(f"  Done! Results → {report_path}")
    print(f"  Raw data → {raw_path}")
    print(f"{'='*60}")
