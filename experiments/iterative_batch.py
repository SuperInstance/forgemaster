#!/usr/bin/env python3
"""iterative_batch.py — Focused iterative experiments on open questions.

Round 1: Qwen scale paradox (0.8B > 4B) — more data points
Round 2: Seed-mini failure boundary — where does 95% drop?
Round 3: MiMo speed+accuracy for safety loops  
Round 4: Step-Flash max_tokens sweep
Round 5: Temperature sweep on Seed-mini (does it care?)
Round 6: Input magnitude cliff on Seed-mini
"""
import requests, re, time, json, os
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
SYSTEM = "You are a calculator. Output the result number ONLY. No words. No explanation."

def query(model, prompt, max_tokens=50, temperature=0.0):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt}
    ], "temperature": temperature, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(URL, headers=headers, json=payload, timeout=60)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return None, lat, 0, 0
        d = r.json()
        msg = d["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or "").strip()
        text = content if content else reasoning
        usage = d.get("usage", {})
        return text, lat, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    except:
        return None, (time.time() - start) * 1000, 0, 0

def extract_num(text):
    if not text: return None
    nums = re.findall(r'-?\d+\.?\d*', text)
    return nums[-1] if nums else None

def check(got, expected, tol=0.05):
    if not got or not expected: return False
    try:
        g, e = float(got), float(expected)
        if e == 0: return abs(g) < 0.01
        return abs(g - e) / abs(e) <= tol
    except: return False

def run_round(name, probes, models):
    """Run a round of experiments. probes = [(prompt, expected), ...]"""
    print(f"\n{'='*60}")
    print(f"ROUND: {name}")
    print(f"{'='*60}")
    results = []
    for model_key, model_id in models.items():
        correct = 0
        total = 0
        lats = []
        for prompt, expected in probes:
            text, lat, _, _ = query(model_id, prompt)
            ext = extract_num(text)
            ok = check(ext, expected)
            correct += ok
            total += 1
            lats.append(lat)
            sym = "✓" if ok else "✗"
            if not ok:
                print(f"  {sym} {model_key:12s} expected={expected:8s} got={str(ext):10s} prompt={prompt[:50]}", flush=True)
            results.append({"model": model_key, "prompt": prompt[:60], "expected": expected, 
                          "got": ext, "correct": ok, "latency": round(lat)})
        acc = correct/total*100 if total else 0
        avg_lat = sum(lats)/len(lats) if lats else 0
        print(f"  {model_key:12s}: {correct}/{total} = {acc:.0f}% avg={avg_lat:.0f}ms", flush=True)
    return results

all_results = {}

# ─── ROUND 1: Qwen Scale Paradox ─────────────────────────────────────────
# Does 0.8B really beat 2B/4B? Test with harder probes.
probes_r1 = [
    ("3 + 4", "7"),
    ("12 * 3", "36"),
    ("a*a + b*b where a=3, b=4", "25"),
    ("a*a - a*b + b*b where a=5, b=3", "19"),
    ("a+b+c+d+e where a=1,b=2,c=3,d=4,e=5", "15"),
    ("a*b*c where a=2,b=3,c=4", "24"),
    ("(a+b)*(a-b) where a=5, b=3", "16"),
    ("a*a - 2*a*b + b*b where a=4, b=3", "1"),
    ("a*a*b + b*b*a where a=2, b=3", "30"),
    ("2^10", "1024"),
    ("sqrt(144)", "12"),
    ("15 mod 7", "1"),
    ("a+a*b+b*b where a=3, b=2", "13"),  # unfamilar coefficient pattern
    ("a*a + 3*a*b + b*b where a=2, b=1", "11"),
    ("(a+b+c)*(a-b) where a=5, b=3, c=2", "8"),
]
models_r1 = {
    "qwen-0.8b": "Qwen/Qwen3.5-0.8B",
    "qwen-2b": "Qwen/Qwen3.5-2B", 
    "qwen-4b": "Qwen/Qwen3.5-4B",
    "qwen-9b": "Qwen/Qwen3.5-9B",
    "qwen-27b": "Qwen/Qwen3.5-27B",
}
all_results["r1_scale"] = run_round("Qwen Scale Paradox (5 sizes × 15 probes)", probes_r1, models_r1)

# ─── ROUND 2: Seed-mini Failure Boundary ──────────────────────────────────
# Push Seed-mini until it breaks
probes_r2 = [
    # Deep addition chains
    ("1+2+3+4+5+6+7+8+9+10+11+12", "78"),  # depth 12
    ("1+2+3+4+5+6+7+8+9+10+11+12+13+14+15", "120"),  # depth 15
    ("1+2+3+4+5+6+7+8+9+10+11+12+13+14+15+16+17+18+19+20", "210"),  # depth 20
    # Deep multiplication (careful - numbers grow fast)
    ("2*3*2", "12"),
    ("2*3*2*2*1", "24"),
    ("2*3*2*2*1*1*2*1", "48"),
    ("1*2*3*4*5", "120"),
    ("1*2*3*4*5*6", "720"),
    # Complex expressions
    ("(3+4)*(5-2)*(6+1)", "147"),  # nested
    ("((2+3)*4 - 5)*6", "90"),  # deep nesting
    ("3*3*3 - 2*2*2", "19"),  # difference of cubes
    ("a*a*a - b*b*b where a=4, b=2", "56"),
    # Large magnitude Eisenstein
    ("a*a - a*b + b*b where a=100, b=200", "30100"),
    ("a*a - a*b + b*b where a=1000, b=500", "750000"),
    ("a*a - a*b + b*b where a=-5, b=7", "109"),
    # Unfamiliar coefficient patterns
    ("a*a + 3*a*b - 2*b*b where a=3, b=2", "21"),
    ("2*a*a - a*b + 3*b*b where a=4, b=1", "33"),
    ("a*a*b*b where a=3, b=5", "225"),
    ("a*b*c + a*b + b*c + a*c where a=2, b=3, c=4", "50"),
    # Truly novel: never in any training data
    ("a^4 - b^4 where a=3, b=1", "80"),
    ("a! where a=5", "120"),
    ("gcd(48, 36)", "12"),
]
models_r2 = {"seed-mini": "ByteDance/Seed-2.0-mini"}
all_results["r2_boundary"] = run_round("Seed-mini Failure Boundary (22 hard probes)", probes_r2, models_r2)

# ─── ROUND 3: MiMo Safety Loop ────────────────────────────────────────────
# Repeated safety queries — MiMo should cache well
probes_r3 = [
    ("Pressure 2800 PSI. Max 3500. Safe to increase by 500? yes/no", "yes"),
    ("Pressure 3800 PSI. Max 3500. Safe? yes/no", "no"),
    ("Tree 22 inches. Max cut 24. Safe? yes/no", "yes"),
    ("Tree 26 inches. Max cut 24. Safe? yes/no", "no"),
    ("Load 12000 lbs. Grapple rated 50000. Safety factor 3. Safe? yes/no", "yes"),
    ("Load 20000 lbs. Grapple rated 50000. Safety factor 3. Safe? yes/no", "no"),
    ("Temp 175F. Max 180F. Safe? yes/no", "yes"),
    ("Temp 185F. Max 180F. Safe? yes/no", "no"),
    ("Flow 18 GPM. Max 20 GPM. Safe? yes/no", "yes"),
    ("Flow 22 GPM. Max 20 GPM. Safe? yes/no", "no"),
    ("Force 45000 lbs. Cylinder rated 50000. Safe? yes/no", "yes"),
    ("Force 55000 lbs. Cylinder rated 50000. Safe? yes/no", "no"),
    ("Bore 5 inch. Pressure 2000 PSI. Force?", "98175"),
    ("Bore 3 inch. Pressure 2500 PSI. Force?", "17671"),
    ("Bore 4 inch. Pressure 3000 PSI. Force?", "37699"),
]
models_r3 = {"mimo": "XiaomiMiMo/MiMo-V2.5", "seed-mini": "ByteDance/Seed-2.0-mini"}
all_results["r3_safety"] = run_round("Safety Loop (MiMo vs Seed-mini, 15 safety probes)", probes_r3, models_r3)

# ─── ROUND 4: Step-Flash max_tokens sweep ─────────────────────────────────
prompt_r4 = "a*a - a*b + b*b where a=5, b=3"
expected_r4 = "19"
model_r4 = "stepfun-ai/Step-3.5-Flash"

print(f"\n{'='*60}")
print(f"ROUND: Step-Flash max_tokens Sweep")
print(f"{'='*60}")
for mt in [10, 20, 30, 50, 80, 100, 150, 200]:
    text, lat, _, _ = query(model_r4, prompt_r4, max_tokens=mt)
    ext = extract_num(text)
    ok = check(ext, expected_r4)
    print(f"  max_tokens={mt:4d}: {'✓' if ok else '✗'} got={str(ext):8s} text={str(text)[:40]}", flush=True)

# ─── ROUND 5: Temperature Sweep on Seed-mini ──────────────────────────────
prompt_r5 = "a*a - a*b + b*b where a=5, b=3"
expected_r5 = "19"
model_r5 = "ByteDance/Seed-2.0-mini"

print(f"\n{'='*60}")
print(f"ROUND: Seed-mini Temperature Sweep")
print(f"{'='*60}")
for t in [0.0, 0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]:
    text, lat, _, _ = query(model_r5, prompt_r5, temperature=t)
    ext = extract_num(text)
    ok = check(ext, expected_r5)
    print(f"  T={t:.1f}: {'✓' if ok else '✗'} got={str(ext):8s} lat={lat:.0f}ms", flush=True)

# ─── ROUND 6: Magnitude Cliff on Seed-mini ────────────────────────────────
print(f"\n{'='*60}")
print(f"ROUND: Seed-mini Magnitude Cliff")
print(f"{'='*60}")
for mag in [1, 3, 5, 10, 20, 50, 100, 500, 1000, 5000, 10000]:
    a, b = mag, mag + 1
    expected = str(a*a - a*b + b*b)
    prompt = f"a*a - a*b + b*b where a={a}, b={b}"
    text, lat, _, _ = query("ByteDance/Seed-2.0-mini", prompt)
    ext = extract_num(text)
    ok = check(ext, expected)
    print(f"  mag={mag:6d}: {'✓' if ok else '✗'} expected={expected:12s} got={str(ext):12s}", flush=True)

# Save everything
with open("experiments/iterative-batch-results.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved to experiments/iterative-batch-results.json")
