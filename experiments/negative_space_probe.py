#!/usr/bin/env python3
"""
Negative Space Probe — Infer other models' profiles from llama-3.1-8b ground truth.
Tests the MOST diagnostic axes on other models to find where they differ.

Author: Forgemaster ⚒️
"""
import requests, re, time
from collections import defaultdict

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"

def query(model, prompt, temp=0.3):
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}],
              "temperature": temp, "max_tokens": 50}, timeout=30)
    c = r.json()["choices"][0]["message"]["content"].strip()
    nums = re.findall(r"-?\d+", c)
    return int(nums[-1]) if nums else None, c

def cls(out, expected, a, b):
    if out == expected: return "✅"
    if out == a: return "ECHO-a"
    if out == b: return "ECHO-b"
    if out == a*a: return "P-a²"
    if out == b*b: return "P-b²"
    if out == a*b: return "P-ab"
    if out is not None and abs(out - expected) <= 3: return "NEAR"
    return f"→{out}"

MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

# The 7 diagnostic tests from ground-truth negative space
print("╔════════════════════════════════════════════════════════════╗", flush=True)
print("║  NEGATIVE SPACE PROBE                                     ║", flush=True)
print("║  Inferring other models from llama-3.1-8b ground truth    ║", flush=True)
print("╚════════════════════════════════════════════════════════════╝", flush=True)

short_names = {m: m.split("/")[-1][:15] for m in MODELS}

# ─── TEST 1: Sub-expression accuracy ─────────────────────────
print("\n━━━ TEST 1: Sub-expression Accuracy (a=5, b=-3) ━━━", flush=True)
print(f"  {'Expr':<15s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

sub_tests = [
    ("a²", 25), ("b²", 9), ("ab", -15), ("-ab", 15),
    ("a²-ab", 40), ("a²+b²", 34), ("a²-ab+b²", 49),
]

for expr, ans in sub_tests:
    print(f"  {expr:<15s}", end="", flush=True)
    for model in MODELS:
        out, _ = query(model, f"Compute {expr} where a=5 and b=-3.", temp=0.3)
        c = cls(out, ans, 5, -3)
        print(f" {c:>15s}", end="", flush=True)
        time.sleep(0.15)
    print(flush=True)

# ─── TEST 2: T=0.0 vs T=0.3 on N(5,-3)=49 ────────────────────
print("\n━━━ TEST 2: Temperature Fragility (N(5,-3)=49) ━━━", flush=True)
print(f"  {'Temp':<8s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

for temp in [0.0, 0.1, 0.3, 0.5, 1.0]:
    print(f"  T={temp:<5.1f}", end="", flush=True)
    for model in MODELS:
        correct = 0
        for _ in range(5):
            out, _ = query(model, "Compute a²-ab+b² where a=5 and b=-3.", temp=temp)
            if out == 49: correct += 1
            time.sleep(0.1)
        print(f" {correct:>14d}/5", end="", flush=True)
    print(flush=True)

# ─── TEST 3: The literal "3" test ─────────────────────────────
print("\n━━━ TEST 3: Instruction Following ('3' vs a+b) ━━━", flush=True)
print(f"  {'Prompt':<30s} {'Expected':>8s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

follow_tests = [
    ("Compute 3 where a=3 and b=4.", 3),
    ("Compute b where a=3 and b=4.", 4),
    ("Compute a where a=5 and b=-3.", 5),
    ("What is 3?", 3),
    ("Compute a+b where a=3 and b=4.", 7),
]

for prompt, ans in follow_tests:
    print(f"  {prompt[:30]:<30s} {ans:>8d}", end="", flush=True)
    for model in MODELS:
        out, _ = query(model, prompt, temp=0.3)
        c = "✅" if out == ans else f"→{out}"
        print(f" {c:>15s}", end="", flush=True)
        time.sleep(0.15)
    print(flush=True)

# ─── TEST 4: Power notation ──────────────────────────────────
print("\n━━━ TEST 4: Operator Notation Gate ━━━", flush=True)
print(f"  {'Notation':<30s} {'Expected':>8s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

notation_tests = [
    ("Compute a*a*a where a=5 and b=-3.", 125),
    ("Compute a**3 where a=5 and b=-3.", 125),
    ("Compute a³ where a=5 and b=-3.", 125),
    ("Compute a^3 where a=5 and b=-3.", 125),
    ("Compute a×a×a where a=5 and b=-3.", 125),
]

for prompt, ans in notation_tests:
    print(f"  {prompt[:30]:<30s} {ans:>8d}", end="", flush=True)
    for model in MODELS:
        out, _ = query(model, prompt, temp=0.3)
        c = "✅" if out == ans else f"→{out}"
        print(f" {c:>15s}", end="", flush=True)
        time.sleep(0.15)
    print(flush=True)

# ─── TEST 5: Sign asymmetry ──────────────────────────────────
print("\n━━━ TEST 5: Sign Asymmetry (a²-ab+b²) ━━━", flush=True)
print(f"  {'(a,b)→ans':<15s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

sign_tests = [
    ((3,4), 13), ((3,-4), 37), ((-3,4), 37), ((-3,-4), 13),
    ((3,0), 9), ((0,4), 16), ((-3,0), 9), ((0,-4), 16),
]

for (a,b), ans in sign_tests:
    label = f"({a},{b})→{ans}"
    print(f"  {label:<15s}", end="", flush=True)
    for model in MODELS:
        out, _ = query(model, f"Compute a²-ab+b² where a={a} and b={b}.", temp=0.0)
        c = "✅" if out == ans else f"→{out}"
        print(f" {c:>15s}", end="", flush=True)
        time.sleep(0.15)
    print(flush=True)

# ─── TEST 6: Width boundary at T=0.0 ────────────────────────
print("\n━━━ TEST 6: Width Boundary at T=0.0 ━━━", flush=True)
print(f"  {'Formula':<20s} {'w':>2s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

width_tests = [
    ("a+b", 1, (3,4,7)),
    ("a²+b", 2, (3,4,13)),
    ("a²-ab+b²", 3, (3,4,13)),
    ("2a²-3ab+b²", 4, (3,4,5)),
    ("a³-a²b+ab²-b³", 5, (3,4,-27)),
]

for formula, w, (a,b,ans) in width_tests:
    print(f"  {formula:<20s} {w:>2d}", end="", flush=True)
    for model in MODELS:
        out, _ = query(model, f"Compute {formula} where a={a} and b={b}.", temp=0.0)
        c = "✅" if out == ans else f"→{out}"
        print(f" {c:>15s}", end="", flush=True)
        time.sleep(0.15)
    print(flush=True)

# ─── TEST 7: Magnitude degradation ───────────────────────────
print("\n━━━ TEST 7: Magnitude Degradation (a²+b²) ━━━", flush=True)
print(f"  {'(a,b)→ans':<20s}", end="", flush=True)
for m in MODELS: print(f" {short_names[m]:>15s}", end="", flush=True)
print(flush=True)

mag_tests = [
    ((3,4), 25), ((30,40), 2500), ((300,400), 250000), ((3000,4000), 25000000),
]

for (a,b), ans in mag_tests:
    label = f"({a},{b})→{ans}"
    print(f"  {label:<20s}", end="", flush=True)
    for model in MODELS:
        out, _ = query(model, f"Compute a²+b² where a={a} and b={b}.", temp=0.3)
        c = "✅" if out == ans else f"→{out}"
        print(f" {c:>15s}", end="", flush=True)
        time.sleep(0.15)
    print(flush=True)

print(f"\n{'='*60}", flush=True)
print("NEGATIVE SPACE PROBE COMPLETE", flush=True)
print(f"{'='*60}", flush=True)
