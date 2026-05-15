#!/usr/bin/env python3
"""Study 21: Can model consensus overcome the Vocabulary Wall?"""

import json, time, requests, sys, os
from collections import Counter

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = [
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "ByteDance/Seed-2.0-mini",
]

TEMPERATURE = 0.3
MAX_TOKENS = 256
TRIALS = 3

QUESTIONS = [
    {
        "id": "q1",
        "loaded": "Compute the Eisenstein norm of (7+3ω). Give ONLY the final number.",
        "stripped": "Compute 49-21+9. Give ONLY the final number.",
        "expected": "37",
        "check_fn": lambda r: "37" in r.strip()[:20],
    },
    {
        "id": "q2",
        "loaded": "What is the covering radius of Z[ω]? Give the answer as a decimal to 3 places.",
        "stripped": "Compute 1/sqrt(3) to 3 decimal places. Give ONLY the number.",
        "expected": "0.577",
        "check_fn": lambda r: "0.577" in r[:20],
    },
    {
        "id": "q3",
        "loaded": "Snap the point (2.7, 1.3) to the nearest Eisenstein integer. Give ONLY the (a,b) pair.",
        "stripped": "Round (2.7,1.3) to the nearest hexagonal grid point with spacing 1. Give ONLY the (x,y) pair.",
        "expected": "(3,1)",
        "check_fn": lambda r: ("(3,1)" in r or "(3, 1)" in r),
    },
    {
        "id": "q4",
        "loaded": "How many Eisenstein integers have norm ≤ 10? Give ONLY the count.",
        "stripped": "How many integer pairs (a,b) satisfy a²-ab+b² ≤ 10? Give ONLY the count.",
        "expected": "31",
        "check_fn": lambda r: "31" in r.strip()[:20],
    },
]

def query_model(model, prompt, trial):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    try:
        resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text
    except Exception as e:
        return f"ERROR: {e}"

def main():
    results = []
    total_calls = len(MODELS) * len(QUESTIONS) * 2 * TRIALS
    call_num = 0
    
    for model in MODELS:
        for q in QUESTIONS:
            for framing in ["loaded", "stripped"]:
                prompt = q[framing]
                for trial in range(TRIALS):
                    call_num += 1
                    short_model = model.split("/")[-1]
                    print(f"[{call_num}/{total_calls}] {short_model} | {q['id']} | {framing} | trial {trial+1}", flush=True)
                    
                    response = query_model(model, prompt, trial)
                    correct = q["check_fn"](response)
                    
                    results.append({
                        "model": model,
                        "question_id": q["id"],
                        "framing": framing,
                        "trial": trial,
                        "prompt": prompt,
                        "expected": q["expected"],
                        "response": response,
                        "correct": correct,
                    })
                    
                    time.sleep(0.3)  # rate limit courtesy
    
    # Save raw JSON
    with open("/home/phoenix/.openclaw/workspace/experiments/consensus-rescue-results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # ---- ANALYSIS ----
    
    # Per question × framing × model: trial accuracy
    print("\n=== PER-MODEL ACCURACY ===")
    from collections import defaultdict
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
            print(f"  {short:30s} {framing:8s}: {avg:.1%} (per-q: {[f'{a:.0%}' for a in accs]})")
    
    # Majority vote per question × framing (across models, per trial index)
    print("\n=== MAJORITY VOTE CONSENSUS ===")
    for q in QUESTIONS:
        for framing in ["loaded", "stripped"]:
            trial_correct = []
            for trial_idx in range(TRIALS):
                # Each model's response for this trial
                votes = []
                for model in MODELS:
                    key = (model, q["id"], framing, trial_idx)
                    # find result
                    match = [r for r in results if r["model"]==model and r["question_id"]==q["id"] and r["framing"]==framing and r["trial"]==trial_idx]
                    if match:
                        votes.append(match[0]["correct"])
                # majority vote
                if votes:
                    majority = sum(votes) >= 2  # at least 2 of 3 correct
                    trial_correct.append(majority)
            acc = sum(trial_correct) / len(trial_correct) if trial_correct else 0
            print(f"  {q['id']} {framing:8s}: {acc:.1%} (trials: {trial_correct})")
    
    # Individual model accuracy by framing
    print("\n=== VOCAB WALL EFFECT (loaded vs stripped) ===")
    for model in MODELS:
        short = model.split("/")[-1]
        loaded_correct = sum(1 for r in results if r["model"]==model and r["framing"]=="loaded" and r["correct"])
        loaded_total = sum(1 for r in results if r["model"]==model and r["framing"]=="loaded")
        stripped_correct = sum(1 for r in results if r["model"]==model and r["framing"]=="stripped" and r["correct"])
        stripped_total = sum(1 for r in results if r["model"]==model and r["framing"]=="stripped")
        print(f"  {short:30s}: loaded {loaded_correct}/{loaded_total} ({loaded_correct/loaded_total:.0%}) vs stripped {stripped_correct}/{stripped_total} ({stripped_correct/stripped_total:.0%})")
    
    print("\nDone! Raw JSON saved.")

if __name__ == "__main__":
    main()
