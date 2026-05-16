#!/usr/bin/env python3
"""Study 51 - Minimal memory version: one Ollama model at a time, explicit unload"""
import requests, json, time, sys, os, subprocess

DEEPINFRA_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
OLLAMA = "http://localhost:11434/api/chat"
DI_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

test_problems = [(5,-3,49), (7,2,39), (4,-6,76), (6,-5,91)]

tier1_exemplars = """Example 1: For z = (4, -6), a=4, b=-6.
Step 1: a^2 = 16
Step 2: -ab = 24
Step 3: b^2 = 36
Step 4: a^2 - ab + b^2 = 16 + 24 + 36 = 76
Answer: 76

Example 2: For z = (2, 3), a=2, b=3.
Step 1: a^2 = 4
Step 2: -ab = -6
Step 3: b^2 = 9
Step 4: a^2 - ab + b^2 = 4 - 6 + 9 = 7
Answer: 7

Example 3: For z = (1, -1), a=1, b=-1.
Step 1: a^2 = 1
Step 2: -ab = 1
Step 3: b^2 = 1
Step 4: a^2 - ab + b^2 = 1 + 1 + 1 = 3
Answer: 3

Example 4: For z = (3, 0), a=3, b=0.
Step 1: a^2 = 9
Step 2: -ab = 0
Step 3: b^2 = 0
Step 4: a^2 - ab + b^2 = 9
Answer: 9

Example 5: For z = (0, 2), a=0, b=2.
Step 1: a^2 = 0
Step 2: -ab = 0
Step 3: b^2 = 4
Step 4: a^2 - ab + b^2 = 4
Answer: 4"""

generic_exemplars = """Example 1: What is 15 x 13?
Step 1: 15 x 10 = 150
Step 2: 15 x 3 = 45
Step 3: 150 + 45 = 195
Answer: 195

Example 2: What is sqrt(144) + 7?
Step 1: sqrt(144) = 12
Step 2: 12 + 7 = 19
Answer: 19

Example 3: What is (23 - 8) x 4?
Step 1: 23 - 8 = 15
Step 2: 15 x 4 = 60
Answer: 60

Example 4: What is 2^5 + 10?
Step 1: 2^5 = 32
Step 2: 32 + 10 = 42
Answer: 42

Example 5: What is 17^2?
Step 1: 17 x 17
Step 2: 170 + 119 = 289
Answer: 289"""

base_q = "Compute the Eisenstein integer norm for z = a + bw where w = e^(2pi*i/3). The norm is |z|^2 = a^2 - ab + b^2. Compute for z = ({a}, {b})."
cell_names = {"A":"Baseline","B":"Tier1-Fewshot","C":"Generic-Fewshot","D":"Self-Scaffold"}

def make_prompt(cell, a, b):
    q = base_q.format(a=a, b=b)
    if cell == "A":
        return [{"role":"user","content":q}]
    elif cell == "B":
        return [{"role":"system","content":f"Math assistant. Examples of Eisenstein norm computation:\n\n{tier1_exemplars}"},{"role":"user","content":q}]
    elif cell == "C":
        return [{"role":"system","content":f"Math assistant. Solve step by step:\n\n{generic_exemplars}"},{"role":"user","content":q}]
    elif cell == "D":
        return [{"role":"user","content":q+"\n\nShow step-by-step: identify a,b, compute a^2, -ab, b^2, sum them."}]

def ollama_query(model, messages):
    r = requests.post(OLLAMA, json={"model":model,"messages":messages,"stream":False,"options":{"temperature":0.3}}, timeout=180)
    return r.json()["message"]["content"]

def di_query(model, messages):
    r = requests.post(DI_URL, headers={"Authorization":f"Bearer {DEEPINFRA_KEY}"}, json={"model":model,"messages":messages,"temperature":0.3,"max_tokens":1024}, timeout=180)
    return r.json()["choices"][0]["message"]["content"]

outdir = os.path.dirname(os.path.abspath(__file__))
results_file = os.path.join(outdir, "study51_results.json")
results = []
if os.path.exists(results_file):
    with open(results_file) as f:
        results = json.load(f)
    print(f"Loaded {len(results)} existing results")

def done(model, cell, pt):
    return any(r["model"]==model and r["cell"]==cell and r["point"]==pt for r in results)

def save():
    with open(results_file,"w") as f:
        json.dump(results, f, indent=2)

def add_result(model, model_id, cell, a, b, expected, resp, error=None):
    correct = str(expected) in resp if not error else False
    results.append({
        "model":model,"model_id":model_id,"cell":cell,"cell_name":cell_names[cell],
        "point":[a,b],"expected":expected,"correct":correct,"error":error,
        "response_preview":resp[:300]
    })
    tag = "OK" if correct else f"WRONG(exp={expected})"
    print(f"  {tag}")
    return correct

# === OLLAMA MODELS (one at a time) ===
ollama_models = [("qwen3:4b","qwen3:4b"),("phi4-mini:latest","phi4-mini")]

for omodel, olabel in ollama_models:
    print(f"\n=== {olabel} ===")
    # Unload previous
    subprocess.run(["ollama","keep-alive","0m"], capture_output=True)
    time.sleep(3)
    # Load this model
    print(f"Loading {omodel}...")
    ollama_query(omodel, [{"role":"user","content":"hi"}])
    
    for cell in ["A","B","C","D"]:
        for a,b,exp in test_problems:
            pt = [a,b]
            if done(olabel, cell, pt):
                print(f"  {olabel} Cell {cell} ({a},{b}) SKIP")
                continue
            sys.stdout.write(f"  {olabel} Cell {cell} ({a},{b})...")
            sys.stdout.flush()
            try:
                resp = ollama_query(omodel, make_prompt(cell, a, b))
                add_result(olabel, f"ollama:{omodel}", cell, a, b, exp, resp)
            except Exception as e:
                add_result(olabel, f"ollama:{omodel}", cell, a, b, exp, f"ERROR: {e}", str(e))
            save()
            time.sleep(0.5)
    
    # Unload
    subprocess.run(["ollama","keep-alive","0m"], capture_output=True)
    time.sleep(3)

# === DEEPINFRA MODELS ===
di_models = [("NousResearch/Hermes-3-Llama-3.1-70B","Hermes-70B"),("Qwen/Qwen3-235B-A22B-Instruct-2507","Qwen3-235B")]

for dmodel, dlabel in di_models:
    print(f"\n=== {dlabel} (DeepInfra) ===")
    for cell in ["A","B","C","D"]:
        for a,b,exp in test_problems:
            pt = [a,b]
            if done(dlabel, cell, pt):
                print(f"  {dlabel} Cell {cell} ({a},{b}) SKIP")
                continue
            sys.stdout.write(f"  {dlabel} Cell {cell} ({a},{b})...")
            sys.stdout.flush()
            try:
                resp = di_query(dmodel, make_prompt(cell, a, b))
                add_result(dlabel, dmodel, cell, a, b, exp, resp)
            except Exception as e:
                add_result(dlabel, dmodel, cell, a, b, exp, f"ERROR: {e}", str(e))
            save()
            time.sleep(1)

# === ANALYSIS ===
print("\n" + "="*60)
print("RESULTS SUMMARY")
print("="*60)

all_models = [m[1] for m in ollama_models] + [m[1] for m in di_models]
for ml in all_models:
    print(f"\n{ml}:")
    for cell in ["A","B","C","D"]:
        cr = [r for r in results if r["model"]==ml and r["cell"]==cell]
        ok = sum(1 for r in cr if r["correct"])
        n = len(cr)
        pct = ok/n*100 if n else 0
        print(f"  Cell {cell} ({cell_names[cell]}): {ok}/{n} = {pct:.0f}%")

print(f"\nAGGREGATE:")
for cell in ["A","B","C","D"]:
    cr = [r for r in results if r["cell"]==cell]
    ok = sum(1 for r in cr if r["correct"])
    n = len(cr)
    print(f"  Cell {cell} ({cell_names[cell]}): {ok}/{n} = {ok/n*100:.1f}%")

a_ok = sum(1 for r in results if r["cell"]=="A" and r["correct"])
a_n = sum(1 for r in results if r["cell"]=="A")
b_ok = sum(1 for r in results if r["cell"]=="B" and r["correct"])
b_n = sum(1 for r in results if r["cell"]=="B")
d_ok = sum(1 for r in results if r["cell"]=="D" and r["correct"])
d_n = sum(1 for r in results if r["cell"]=="D")
a_pct = a_ok/a_n*100 if a_n else 0
b_pct = b_ok/b_n*100 if b_n else 0
d_pct = d_ok/d_n*100 if d_n else 0

print(f"\nKEY FINDING:")
if b_pct > a_pct + 10:
    print(f"  Cell B ({b_pct:.0f}%) >> Cell A ({a_pct:.0f}%) — Tier 1 IS transferable via few-shot!")
elif b_pct > a_pct:
    print(f"  Cell B ({b_pct:.0f}%) > Cell A ({a_pct:.0f}%) — Partially transferable")
else:
    print(f"  Cell B ({b_pct:.0f}%) <= Cell A ({a_pct:.0f}%) — NOT transferable")

if d_pct > b_pct + 5:
    print(f"  Cell D ({d_pct:.0f}%) > Cell B ({b_pct:.0f}%) — Self-scaffolding wins")
elif b_pct > d_pct + 5:
    print(f"  Cell B ({b_pct:.0f}%) > Cell D ({d_pct:.0f}%) — Few-shot wins")
else:
    print(f"  Cell D ({d_pct:.0f}%) ~ Cell B ({b_pct:.0f}%) — Comparable")

print(f"\nDone. {len(results)} results saved.")
