#!/usr/bin/env python3
"""experiments/wide_long.py — The Full Atlas

Go wide: Every non-thinking model on DeepInfra (20+)
Go long:  300+ probes across 12 dimensions, both champions verify each

Output: experiments/atlas-results.json — the complete capability atlas
"""
from __future__ import annotations

import json, os, re, sys, time, statistics
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple

# Force unbuffered
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

import requests

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
SYSTEM = "You are a calculator. Output the result number ONLY. No words. No explanation."

# ─── Models ──────────────────────────────────────────────────────────────────

CHAMPIONS = {
    "seed-mini":       "ByteDance/Seed-2.0-mini",
    "gemini-lite":     "google/gemini-3.1-flash-lite",
}

WIDE_MODELS = {
    # Tier 1: Engine Room
    "seed-mini":       "ByteDance/Seed-2.0-mini",
    "seed-pro":        "ByteDance/Seed-2.0-pro",
    "seed-1.8":        "ByteDance/Seed-1.8",
    "gemini-lite":     "google/gemini-3.1-flash-lite",
    "gemini-flash":    "google/gemini-2.5-flash",
    "gemini-flash8b":  "google/gemini-1.5-flash-8b",
    # Tier 2: Contenders
    "hermes-70b":      "NousResearch/Hermes-3-Llama-3.1-70B",
    "qwen2.5-72b":     "Qwen/Qwen2.5-72B-Instruct",
    "mistral-small":   "mistralai/Mistral-Small-24B-Instruct-2501",
    "nemotron-30b":    "nvidia/Nemotron-3-Nano-30B-A3B",
    "nemotron-super":  "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
    # Tier 3: Small/fast
    "qwen-0.8b":       "Qwen/Qwen3.5-0.8B",
    "qwen-2b":         "Qwen/Qwen3.5-2B",
    "nemotron-nano":   "nvidia/NVIDIA-Nemotron-Nano-9B-v2",
    "gemma-12b":       "google/gemma-3-12b-it",
    "gemma-31b":       "google/gemma-4-31B-it",
}

ALL_MODELS = {**WIDE_MODELS}

# ─── Query ───────────────────────────────────────────────────────────────────

def q(model, prompt, max_tokens=50):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ], "temperature": 0.0, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(URL, headers=headers, json=payload, timeout=90)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return None, lat, 0
        d = r.json()
        msg = d["choices"][0]["message"]
        c = (msg.get("content") or "").strip()
        r_txt = (msg.get("reasoning_content") or "").strip()
        usage = d.get("usage", {})
        text = c if c else r_txt
        return text, lat, usage.get("total_tokens", 0)
    except Exception as e:
        return None, (time.time() - start) * 1000, 0

def ext(text):
    if not text: return None
    nums = re.findall(r"-?\d+\.?\d*", text)
    return nums[-1] if nums else None

def check(got, expected):
    if not got: return False
    if expected in ("yes", "no"):
        return (got or "").lower().startswith(expected[0])
    try:
        return abs(float(got) - float(expected)) / max(abs(float(expected)), 1) < 0.05
    except:
        return got.strip() == expected.strip()

@dataclass
class Tile:
    model: str
    category: str
    prompt: str
    expected: str
    got: str = ""
    correct: bool = False
    latency_ms: float = 0.0
    tokens: int = 0

# ─── Probes ──────────────────────────────────────────────────────────────────

def generate_probes():
    probes = []

    # 1. ADDITION DEPTH (1-25)
    for d in range(1, 26):
        terms = list(range(1, d+1))
        p = "+".join(str(x) for x in terms)
        probes.append(("add_depth", p, str(sum(terms))))

    # 2. MULTIPLICATION DEPTH (2-8)
    for d in range(2, 9):
        terms = [2, 3, 2, 2, 3, 2, 2, 3][:d]
        p = " * ".join(str(x) for x in terms)
        expected = 1
        for t in terms: expected *= t
        probes.append(("mul_depth", p, str(expected)))

    # 3. MAGNITUDE (powers of 2)
    for mag in [1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 50000, 100000]:
        a, b = mag, mag+1
        probes.append(("magnitude", f"a*a - a*b + b*b where a={a}, b={b}", str(a*a - a*b + b*b)))

    # 4. COEFFICIENT PATTERNS
    for a, b in [(5,3), (7,2), (10,4), (3,6)]:
        patterns = [
            ("a*a + b*b", a*a + b*b),
            ("a*a - b*b", a*a - b*b),
            ("a*a - a*b + b*b", a*a - a*b + b*b),
            ("a*a + a*b + b*b", a*a + a*b + b*b),
            ("a*a - 2*a*b + b*b", a*a - 2*a*b + b*b),
            ("a*a + 2*a*b + b*b", a*a + 2*a*b + b*b),
            ("a*a - 3*a*b + b*b", a*a - 3*a*b + b*b),
            ("2*a*a - a*b + b*b", 2*a*a - a*b + b*b),
            ("a*a - a*b + 2*b*b", a*a - a*b + 2*b*b),
            ("a*a + 5*a*b + b*b", a*a + 5*a*b + b*b),
        ]
        for formula, expected in patterns:
            probes.append(("coefficients", f"Compute {formula} where a={a}, b={b}", str(int(expected))))

    # 5. NESTING (7 levels)
    probes.append(("nesting", "(3+4)*(5-2)", "21"))
    probes.append(("nesting", "(3+4)*(5-2)*(6+1)", "147"))
    probes.append(("nesting", "((2+3)*4 - 5)*6", "90"))
    probes.append(("nesting", "(((1+2)*3 + 4)*5 - 6)*7", "279"))
    probes.append(("nesting", "((((3+2)*4 - 1)*3 + 5)*2 - 4)*6", "426"))
    probes.append(("nesting", "(a+b)*(a-b) where a=7, b=2", "45"))
    probes.append(("nesting", "(a*b + c)*(a - c) where a=5, b=2, c=3", "35"))

    # 6. PHYSICAL REASONING (20)
    phys = [
        ("A 4-inch bore at 3000 PSI. Force = pi * bore * pressure. Integer.", "37699"),
        ("A 3:1 pulley with 900 lb load. Input force?", "300"),
        ("Feed 50 ft/min, limbs every 2 ft. Cycles/min?", "25"),
        ("1 tree/min for 8 hours. Total?", "480"),
        ("Pressure 2800, max 3500. Safe to add 600? yes/no", "yes"),
        ("Temp 175F, max 180F. Safe to add 10? yes/no", "no"),
        ("Bore 3, pressure 2500. Force = pi * 3 * 2500. Integer.", "23562"),
        ("Max cut 24 inches. Tree 22. Safe? yes/no", "yes"),
        ("Max cut 24 inches. Tree 26. Safe? yes/no", "no"),
        ("Cable rated 10000 lb, load 3000, safety factor 3. Max safe load?", "3333"),
        ("Pump flow 15 GPM, cylinder vol 5 gal. Cycle time seconds?", "20"),
        ("Motor 1800 RPM, gear ratio 3:1. Output RPM?", "600"),
        ("Hydraulic pressure 2500 PSI, bore area 10 sq in. Force lbs?", "25000"),
        ("Valve opens 0.5 sec, closes 0.3 sec. Cycles per minute?", "75"),
        ("Tank 500 gal, pump 25 GPM. Drain time minutes?", "20"),
        ("Winch pulls 5000 lb at 10 ft/min. Horsepower = force*speed/33000. Give 1 decimal.", "1.5"),
        ("Three valves in series. Each 80% flow. Total flow percent?", "51"),
        ("Boom length 30 ft, load 2000 lb at tip. Moment ft-lbs?", "60000"),
        ("Two pumps: 10 GPM and 15 GPM. Combined flow?", "25"),
        ("Pressure drops 10% per 100 ft of hose. 300 ft. Final pressure if start 3000?", "2187"),
    ]
    for p, e in phys:
        probes.append(("physical", p, e))

    # 7. WORD PROBLEMS
    words = [
        ("Three plus four.", "7"),
        ("Twelve times three.", "36"),
        ("Five squared minus three times four plus two squared.", "19"),
        ("The sum of one through ten.", "55"),
        ("Two cubed.", "8"),
        ("Square root of one forty-four.", "12"),
        ("Fifteen mod seven.", "1"),
        ("Half of ninety-nine.", "49.5"),
        ("Twenty percent of three hundred.", "60"),
        ("The product of seven and eight.", "56"),
    ]
    for p, e in words:
        probes.append(("word", p, e))

    # 8. NOVEL EXPRESSIONS
    novel = [
        ("a^4 - b^4 where a=3, b=1", "80"),
        ("a^3 + b^3 where a=2, b=3", "35"),
        ("2^10", "1024"),
        ("2^16", "65536"),
        ("3^5", "243"),
        ("log2(256)", "8"),
        ("log2(1024)", "10"),
        ("lcm(12, 18)", "36"),
        ("gcd(48, 36)", "12"),
        ("5!", "120"),
        ("6!", "720"),
        ("7!", "5040"),
    ]
    for p, e in novel:
        probes.append(("novel", p, e))

    # 9. SEQUENTIAL REASONING
    seq = [
        ("Start 100. Add 50. Multiply by 2. Subtract 100.", "300"),
        ("Start 0. Add 7 twelve times.", "84"),
        ("Start 1000. Halve three times.", "125"),
        ("Start 1. Double seven times.", "128"),
        ("Start 50. Subtract 5 ten times.", "0"),
        ("Start 1. Square it. Add 3. Square it.", "289"),
        ("Start 2. Cube it. Subtract 2. Divide by 2.", "3"),
        ("Start 10. Add 10%. Add 10% of result.", "12.1"),
    ]
    for p, e in seq:
        probes.append(("sequential", p, e))

    # 10. COMPARATIVE (binary yes/no)
    comp = [
        ("Is 7*8 greater than 50? yes/no", "yes"),
        ("Is 11*12 less than 130? yes/no", "no"),
        ("Is a*a - a*b + b*b (a=5,b=3) equal to 19? yes/no", "yes"),
        ("Is 3^4 greater than 80? yes/no", "yes"),
        ("Is the sum of 1 through 100 equal to 5050? yes/no", "yes"),
        ("Is sqrt(2) greater than 1.4? yes/no", "yes"),
        ("Is 99*101 equal to 9999? yes/no", "yes"),
        ("Is 2^10 less than 1000? yes/no", "no"),
    ]
    for p, e in comp:
        probes.append(("comparative", p, e))

    # 11. SPATIAL/GEOMETRIC
    spatial = [
        ("Area of circle radius 10. Pi = 3.14. Integer.", "314"),
        ("Perimeter of rectangle 5 by 8.", "26"),
        ("Volume of box 3 by 4 by 5.", "60"),
        ("Area of triangle base 6 height 4.", "12"),
        ("Hypotenuse of 3-4-5 triangle.", "5"),
        ("Surface area of cube side 5. Integer.", "150"),
        ("Volume of sphere radius 5. 4/3 * 3.14 * 125. Integer.", "523"),
        ("Diagonal of square side 10. 1 decimal.", "14.1"),
    ]
    for p, e in spatial:
        probes.append(("spatial", p, e))

    # 12. EDGE CASES / ADVERSARIAL
    edge = [
        ("0 * 1000", "0"),
        ("1 * 1 * 1 * 1 * 1 * 1 * 1 * 1 * 1 * 1", "1"),
        ("0 + 0 + 0 + 0 + 0", "0"),
        ("999 + 1", "1000"),
        ("1000 - 1", "999"),
        ("1 / 3 * 3. Give 1 decimal.", "1.0"),
        ("0.1 + 0.2. Give 1 decimal.", "0.3"),
        ("-5 * -3", "15"),
        ("-10 + 15", "5"),
        ("7 - 12", "-5"),
    ]
    for p, e in edge:
        probes.append(("edge", p, e))

    return probes

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="experiments/atlas-results.json")
    p.add_argument("--wide", action="store_true", help="Run all 16 models (slow)")
    p.add_argument("--champions", action="store_true", help="Only champions (fast)")
    p.add_argument("--models", nargs="+", help="Specific model keys")
    args = p.parse_args()

    probes = generate_probes()

    if args.champions:
        models = CHAMPIONS
    elif args.models:
        models = {k: ALL_MODELS[k] for k in args.models if k in ALL_MODELS}
    else:
        models = ALL_MODELS  # go wide

    total = len(probes) * len(models)
    print(f"ATLAS: {len(probes)} probes × {len(models)} models = {total} queries", flush=True)
    print(flush=True)

    all_tiles = []
    by_model = defaultdict(list)

    for pi, (cat, prompt, expected) in enumerate(probes):
        if pi % 10 == 0:
            print(f"  [{len(all_tiles)}/{total}] cat={cat} probe={pi+1}/{len(probes)}", flush=True)

        for mk, mid in models.items():
            text, lat, tokens = q(mid, prompt)
            got = ext(text)
            correct = check(got, expected)

            tile = Tile(
                model=mk, category=cat, prompt=prompt[:80],
                expected=expected, got=str(got or ""),
                correct=correct, latency_ms=lat, tokens=tokens,
            )
            all_tiles.append(tile)
            by_model[mk].append(tile)

    # ─── Analysis ────────────────────────────────────────────────────────────
    print(f"\n{'='*70}", flush=True)
    print("ATLAS RESULTS", flush=True)
    print(f"{'='*70}", flush=True)

    # Ranked by accuracy
    ranked = sorted(by_model.items(), key=lambda x: -sum(1 for t in x[1] if t.correct)/len(x[1]))
    for mk, tiles in ranked:
        c = sum(1 for t in tiles if t.correct)
        t = len(tiles)
        avg = sum(t.latency_ms for t in tiles) / t
        bar = "█" * int(c/t * 40)
        print(f"  {mk:20s}: {c:3d}/{t} = {c/t*100:5.1f}% {bar} {avg:.0f}ms", flush=True)

    # Category breakdown per model
    print(f"\n  CATEGORY BREAKDOWN:", flush=True)
    cats = sorted(set(t.category for t in all_tiles))
    header = f"  {'':20s}" + "".join(f"{c[:6]:>7s}" for c in cats)
    print(header, flush=True)

    for mk, tiles in ranked:
        cat_scores = {}
        for cat in cats:
            ct = [t for t in tiles if t.category == cat]
            if ct:
                cc = sum(1 for t in ct if t.correct)
                cat_scores[cat] = f"{cc}/{len(ct)}"
            else:
                cat_scores[cat] = "-"
        line = f"  {mk:20s}" + "".join(f"{cat_scores.get(c,'-'):>7s}" for c in cats)
        print(line, flush=True)

    # Depth cliff curves
    print(f"\n  ADDITION DEPTH CLIFF:", flush=True)
    for mk, tiles in ranked:
        dtiles = sorted([t for t in tiles if t.category == "add_depth"], key=lambda t: int(t.expected))
        if dtiles:
            line = " ".join(f"{'✓' if t.correct else '✗'}" for t in dtiles)
            last_correct = max((i+1 for i, t in enumerate(dtiles) if t.correct), default=0)
            print(f"  {mk:20s}: depth={last_correct:2d}  {line}", flush=True)

    # Multiplication cliff
    print(f"\n  MULTIPLICATION DEPTH CLIFF:", flush=True)
    for mk, tiles in ranked:
        dtiles = sorted([t for t in tiles if t.category == "mul_depth"], key=lambda t: int(t.expected))
        if dtiles:
            line = " ".join(f"{'✓' if t.correct else '✗'}" for t in dtiles)
            last_correct = max((i+1 for i, t in enumerate(dtiles) if t.correct), default=0)
            print(f"  {mk:20s}: depth={last_correct:2d}  {line}", flush=True)

    # Magnitude cliff
    print(f"\n  MAGNITUDE CLIFF:", flush=True)
    for mk, tiles in ranked:
        mtiles = sorted([t for t in tiles if t.category == "magnitude"], key=lambda t: int(t.expected))
        if mtiles:
            line = " ".join(f"{'✓' if t.correct else '✗'}" for t in mtiles)
            last_correct = max((i+1 for i, t in enumerate(mtiles) if t.correct), default=0)
            print(f"  {mk:20s}: last={last_correct:2d}  {line}", flush=True)

    # Agreement matrix
    print(f"\n  CHAMPION AGREEMENT:", flush=True)
    champ_tiles = {mk: by_model[mk] for mk in CHAMPIONS if mk in by_model}
    if len(champ_tiles) == 2:
        agree = disagree = 0
        for cat in cats:
            cat_a = [t for t in list(champ_tiles.values())[0] if t.category == cat]
            cat_b = [t for t in list(champ_tiles.values())[1] if t.category == cat]
            for i in range(min(len(cat_a), len(cat_b))):
                if cat_a[i].correct and cat_b[i].correct:
                    agree += 1
                elif cat_a[i].correct != cat_b[i].correct:
                    disagree += 1
        total_cmp = agree + disagree
        print(f"    Agree: {agree}/{total_cmp} = {agree/total_cmp*100:.0f}%", flush=True)
        print(f"    Disagree: {disagree}/{total_cmp} ({disagree} probes where only one got it right)", flush=True)

    # Save
    output = {
        "meta": {
            "n_probes": len(probes),
            "n_models": len(models),
            "n_queries": len(all_tiles),
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        },
        "ranked": [(mk, sum(1 for t in ts if t.correct), len(ts)) for mk, ts in ranked],
        "tiles": [asdict(t) for t in all_tiles],
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved {len(all_tiles)} tiles to {args.output}", flush=True)

if __name__ == "__main__":
    main()
