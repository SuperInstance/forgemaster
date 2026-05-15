#!/usr/bin/env python3
"""Finish remaining 3 calls and generate analysis."""
import json, time, requests
from collections import defaultdict

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

with open("/home/phoenix/.openclaw/workspace/experiments/consensus-rescue-results.json") as f:
    results = json.load(f)

prompt = "How many integer pairs (a,b) satisfy a²-ab+b² ≤ 10? Give ONLY the count."
expected = "31"

def check_fn(r):
    return "31" in r.strip()[:20]

for trial in range(3):
    print(f"Running Seed-2.0-mini q4 stripped trial {trial}...", flush=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "ByteDance/Seed-2.0-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 256,
    }
    resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    correct = check_fn(text)
    results.append({
        "model": "ByteDance/Seed-2.0-mini",
        "question_id": "q4",
        "framing": "stripped",
        "trial": trial,
        "prompt": prompt,
        "expected": expected,
        "response": text,
        "correct": correct,
    })
    print(f"  Response: {text[:80]} | Correct: {correct}")
    time.sleep(1)

# Save complete JSON
with open("/home/phoenix/.openclaw/workspace/experiments/consensus-rescue-results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nTotal results: {len(results)}")

# ---- FULL ANALYSIS ----
MODELS = [
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "ByteDance/Seed-2.0-mini",
]

QUESTIONS = [
    {"id": "q1", "expected": "37"},
    {"id": "q2", "expected": "0.577"},
    {"id": "q3", "expected": "(3,1)"},
    {"id": "q4", "expected": "31"},
]

TRIALS = 3

print("\n=== PER-MODEL ACCURACY ===")
model_q_framing = defaultdict(list)
for r in results:
    key = (r["model"], r["question_id"], r["framing"])
    model_q_framing[key].append(r["correct"])

for model in MODELS:
    short = model.split("/")[-1]
    for framing in ["loaded", "stripped"]:
        accs = []
        for q in QUESTIONS:
            key = (model, q["id"], framing)
            trials = model_q_framing[key]
            acc = sum(trials) / len(trials)
            accs.append(acc)
        avg = sum(accs) / len(accs)
        print(f"  {short:40s} {framing:8s}: {avg:.1%} (per-q: {[f'{a:.0%}' for a in accs]})")

print("\n=== MAJORITY VOTE CONSENSUS ===")
consensus_by_framing = {"loaded": [], "stripped": []}
for q in QUESTIONS:
    for framing in ["loaded", "stripped"]:
        trial_correct = []
        for trial_idx in range(TRIALS):
            votes = []
            for model in MODELS:
                match = [r for r in results if r["model"]==model and r["question_id"]==q["id"] and r["framing"]==framing and r["trial"]==trial_idx]
                if match:
                    votes.append(match[0]["correct"])
            if votes:
                majority = sum(votes) >= 2
                trial_correct.append(majority)
                consensus_by_framing[framing].append(majority)
        acc = sum(trial_correct) / len(trial_correct) if trial_correct else 0
        print(f"  {q['id']} {framing:8s}: {acc:.1%} (trials: {trial_correct})")

print("\n=== VOCAB WALL EFFECT ===")
for model in MODELS:
    short = model.split("/")[-1]
    lc = sum(1 for r in results if r["model"]==model and r["framing"]=="loaded" and r["correct"])
    lt = sum(1 for r in results if r["model"]==model and r["framing"]=="loaded")
    sc = sum(1 for r in results if r["model"]==model and r["framing"]=="stripped" and r["correct"])
    st = sum(1 for r in results if r["model"]==model and r["framing"]=="stripped")
    print(f"  {short:40s}: loaded {lc}/{lt} ({lc/lt:.0%}) vs stripped {sc}/{st} ({sc/st:.0%})")

print("\n=== CONSENSUS vs INDIVIDUAL SUMMARY ===")
for model in MODELS:
    short = model.split("/")[-1]
    tc = sum(1 for r in results if r["model"]==model and r["correct"])
    tt = sum(1 for r in results if r["model"]==model)
    print(f"  {short:40s}: {tc}/{tt} ({tc/tt:.0%})")

# Consensus overall
cc = 0
ct = 0
for q in QUESTIONS:
    for framing in ["loaded", "stripped"]:
        for trial_idx in range(TRIALS):
            votes = []
            for model in MODELS:
                match = [r for r in results if r["model"]==model and r["question_id"]==q["id"] and r["framing"]==framing and r["trial"]==trial_idx]
                if match:
                    votes.append(match[0]["correct"])
            if len(votes) == 3:
                ct += 1
                if sum(votes) >= 2:
                    cc += 1
print(f"  {'CONSENSUS (majority vote)':40s}: {cc}/{ct} ({cc/ct:.0%})")

# Consensus loaded vs stripped
for framing in ["loaded", "stripped"]:
    fc = 0
    ft = 0
    for q in QUESTIONS:
        for trial_idx in range(TRIALS):
            votes = []
            for model in MODELS:
                match = [r for r in results if r["model"]==model and r["question_id"]==q["id"] and r["framing"]==framing and r["trial"]==trial_idx]
                if match:
                    votes.append(match[0]["correct"])
            if len(votes) == 3:
                ft += 1
                if sum(votes) >= 2:
                    fc += 1
    print(f"  {'CONSENSUS '+framing:40s}: {fc}/{ft} ({fc/ft:.0%})")

# Print some representative responses
print("\n=== SAMPLE RESPONSES (q4 loaded) ===")
for model in MODELS:
    short = model.split("/")[-1]
    match = [r for r in results if r["model"]==model and r["question_id"]=="q4" and r["framing"]=="loaded" and r["trial"]==0]
    if match:
        print(f"  {short}: {match[0]['response'][:120]}")

print("\n=== SAMPLE RESPONSES (q2 loaded vs stripped) ===")
for model in MODELS:
    short = model.split("/")[-1]
    for framing in ["loaded", "stripped"]:
        match = [r for r in results if r["model"]==model and r["question_id"]=="q2" and r["framing"]==framing and r["trial"]==0]
        if match:
            print(f"  {short} {framing}: {match[0]['response'][:120]}")

print("\nDone!")
