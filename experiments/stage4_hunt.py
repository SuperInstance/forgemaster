#!/usr/bin/env python3
"""Stage 4 Model Hunt — Test all DeepInfra models with 6-probe diagnostic."""
import json, time, requests, sys, os

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

PROBES = [
    ("add_37_58", "37 + 58 = ? Reply ONLY integer.", 95),
    ("mul_12_11", "12 * 11 = ? Reply ONLY integer.", 132),
    ("eisenstein", "Compute the Eisenstein norm of (5-3ω). N(a+bω)=a²-ab+b². Reply ONLY integer.", 49),
    ("sub_neg", "Compute: 25 - (-15) + 9 = ? Reply ONLY integer.", 49),
    ("mod_17_5", "17 mod 5 = ? Reply ONLY integer.", 2),
    ("sequence", "Next number in 1, 7, 19, 37, 61? Reply ONLY integer.", 91),
]

MODELS = [
    "NousResearch/Hermes-3-Llama-3.1-405B",
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "Qwen/Qwen3.6-35B-A3B",
    "ByteDance/Seed-2.0-mini",
    "ByteDance/Seed-2.0-code",
    "meta-llama/Meta-Llama-3.1-70B-Instruct",
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "google/gemma-2-27b-it",
    "microsoft/Phi-3-medium-4k-instruct",
]

TRIALS = 3
DELAY = 0.5

def extract_int(text):
    """Extract the last integer from model response."""
    import re
    nums = re.findall(r'-?\d+', text.strip())
    if not nums:
        return None
    return int(nums[-1])

def test_model(model):
    results = []
    for probe_name, prompt, expected in PROBES:
        trial_results = []
        for trial in range(TRIALS):
            try:
                resp = requests.post(ENDPOINT, headers=HEADERS, json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 50,
                }, timeout=60)
                data = resp.json()
                if "error" in data:
                    trial_results.append({"error": data["error"].get("message", str(data["error"])), "raw": None, "parsed": None, "correct": False})
                else:
                    raw = data["choices"][0]["message"]["content"].strip()
                    parsed = extract_int(raw)
                    correct = parsed == expected
                    trial_results.append({"raw": raw, "parsed": parsed, "correct": correct})
            except Exception as e:
                trial_results.append({"error": str(e), "raw": None, "parsed": None, "correct": False})
            time.sleep(DELAY)
        results.append({"probe": probe_name, "expected": expected, "trials": trial_results})
    return results

def classify_stage(accuracy):
    if accuracy >= 0.9:
        return "Stage 4 (Immune)"
    elif accuracy >= 0.7:
        return "Stage 3 (Resistant)"
    elif accuracy >= 0.5:
        return "Stage 2 (Partial)"
    else:
        return "Stage 1 (Vulnerable)"

all_results = {}
for i, model in enumerate(MODELS):
    print(f"\n[{i+1}/{len(MODELS)}] Testing {model}...")
    try:
        res = test_model(model)
        all_results[model] = res
        
        # Compute stats
        total_correct = sum(1 for p in res for t in p["trials"] if t.get("correct", False))
        total_trials = len(PROBES) * TRIALS
        accuracy = total_correct / total_trials
        
        eisenstein_correct = sum(1 for t in res[2]["trials"] if t.get("correct", False))
        eisenstein_acc = eisenstein_correct / TRIALS
        
        stage = classify_stage(accuracy)
        print(f"  Accuracy: {accuracy:.2%} ({total_correct}/{total_trials}) | Eisenstein: {eisenstein_acc:.2%} | Stage: {stage}")
        
        # Print probe details
        for p in res:
            trial_strs = []
            for t in p["trials"]:
                if "error" in t:
                    trial_strs.append(f"ERR:{t['error'][:30]}")
                else:
                    trial_strs.append(f"{t['parsed']}({'✓' if t['correct'] else '✗'})")
            print(f"    {p['probe']}: {', '.join(trial_strs)} (expected {p['expected']})")
            
    except Exception as e:
        print(f"  FAILED: {e}")
        all_results[model] = {"error": str(e)}
    
    time.sleep(1)

# Save raw JSON
os.makedirs("/home/phoenix/.openclaw/workspace/experiments", exist_ok=True)
with open("/home/phoenix/.openclaw/workspace/experiments/stage4-hunt-results.json", "w") as f:
    json.dump(all_results, f, indent=2)

# Generate markdown report
md = ["# Study 38: Stage 4 Model Hunt — DeepInfra Full Scan\n"]
md.append(f"Date: 2026-05-15")
md.append(f"Probes: 6 | Trials per probe: {TRIALS} | Temperature: 0.1\n")
md.append("## Results Summary\n")
md.append("| Model | Accuracy | Eisenstein | Stage |")
md.append("|-------|----------|------------|-------|")

model_stats = []
for model, res in all_results.items():
    if isinstance(res, dict) and "error" in res:
        md.append(f"| {model.split('/')[-1]} | ERROR | ERROR | N/A |")
        continue
    total_correct = sum(1 for p in res for t in p["trials"] if t.get("correct", False))
    total_trials = len(PROBES) * TRIALS
    accuracy = total_correct / total_trials
    eisenstein_correct = sum(1 for t in res[2]["trials"] if t.get("correct", False))
    eisenstein_acc = eisenstein_correct / TRIALS
    stage = classify_stage(accuracy)
    short = model.split("/")[-1]
    md.append(f"| {short} | {accuracy:.0%} ({total_correct}/{total_trials}) | {eisenstein_acc:.0%} | {stage} |")
    model_stats.append((model, accuracy, eisenstein_acc, stage))

md.append("\n## Stage Classification\n")
md.append("- **Stage 4 (Immune)**: ≥90% accuracy — handles all arithmetic including Eisenstein")
md.append("- **Stage 3 (Resistant)**: 70-89% — mostly correct, fails on some probes")
md.append("- **Stage 2 (Partial)**: 50-69% — inconsistent")
md.append("- **Stage 1 (Vulnerable)**: <50% — vocabulary wall or tokenization issues\n")

# Stage 4 models
stage4 = [(m, a, e) for m, a, e, s in model_stats if s == "Stage 4 (Immune)"]
md.append("## Stage 4 (Immune) Models\n")
if stage4:
    for m, a, e in stage4:
        md.append(f"- **{m}** — {a:.0%} overall, {e:.0%} Eisenstein")
else:
    md.append("- None found")

# Stage 3
stage3 = [(m, a, e) for m, a, e, s in model_stats if s.startswith("Stage 3")]
md.append("\n## Stage 3 (Resistant) Models\n")
if stage3:
    for m, a, e in stage3:
        md.append(f"- **{m}** — {a:.0%} overall, {e:.0%} Eisenstein")
else:
    md.append("- None found")

# Probe-by-probe detail
md.append("\n## Detailed Probe Results\n")
for model, res in all_results.items():
    if isinstance(res, dict) and "error" in res:
        md.append(f"### {model}\n**Error:** {res['error']}\n")
        continue
    md.append(f"### {model}\n")
    md.append("| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |")
    md.append("|-------|----------|---------|---------|---------|")
    for p in res:
        cells = []
        for t in p["trials"]:
            if "error" in t:
                cells.append(f"ERR")
            else:
                cells.append(f"{t['parsed']} {'✓' if t['correct'] else '✗'}")
        md.append(f"| {p['probe']} | {p['expected']} | {' | '.join(cells)} |")
    md.append("")

# Eisenstein-specific analysis
md.append("## Eisenstein Norm Analysis\n")
md.append("The Eisenstein norm probe (probe 3) is the hardest — requiring abstract math computation.\n")
md.append("| Model | Eisenstein Accuracy | Notes |")
md.append("|-------|---------------------|-------|")
for model, res in all_results.items():
    if isinstance(res, dict) and "error" in res:
        continue
    e_correct = sum(1 for t in res[2]["trials"] if t.get("correct", False))
    e_acc = e_correct / TRIALS
    responses = [str(t.get("parsed", t.get("error", "?"))) for t in res[2]["trials"]]
    short = model.split("/")[-1]
    md.append(f"| {short} | {e_acc:.0%} | {', '.join(responses)} |")

md.append("\n## Conclusion\n")
if stage4:
    md.append(f"**{len(stage4)} Stage 4 model(s) found.** These are immune to the vocabulary wall and can handle abstract mathematical computation.")
else:
    md.append("**No new Stage 4 models found.** Seed-2.0-mini and Seed-2.0-code remain the only immune models on DeepInfra.")

with open("/home/phoenix/.openclaw/workspace/experiments/STAGE4-HUNT-RESULTS.md", "w") as f:
    f.write("\n".join(md))

print("\n\nDone! Results saved.")
