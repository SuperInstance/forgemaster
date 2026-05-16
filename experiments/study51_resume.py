#!/usr/bin/env python3
"""Study 51 - Resume: phi4-mini (one query at a time) then DeepInfra"""
import requests, json, time, sys, os

DEEPINFRA_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
OLLAMA = "http://localhost:11434/api/chat"
DI_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

test_problems = [(5,-3,49), (7,2,39), (4,-6,76), (6,-5,91)]

tier1_exemplars = """Example 1: For z = (4, -6), a=4, b=-6.
Step 1: a^2 = 16, Step 2: -ab = 24, Step 3: b^2 = 36, Step 4: 16+24+36 = 76. Answer: 76

Example 2: For z = (2, 3), a=2, b=3.
Step 1: a^2 = 4, Step 2: -ab = -6, Step 3: b^2 = 9, Step 4: 4-6+9 = 7. Answer: 7

Example 3: For z = (1, -1), a=1, b=-1.
Step 1: a^2 = 1, Step 2: -ab = 1, Step 3: b^2 = 1, Step 4: 1+1+1 = 3. Answer: 3

Example 4: For z = (3, 0), a=3, b=0.
Step 1: a^2 = 9, Step 2: -ab = 0, Step 3: b^2 = 0, Step 4: 9+0+0 = 9. Answer: 9

Example 5: For z = (0, 2), a=0, b=2.
Step 1: a^2 = 0, Step 2: -ab = 0, Step 3: b^2 = 4, Step 4: 0+0+4 = 4. Answer: 4"""

generic_exemplars = """Example 1: 15 x 13 = 195. Example 2: sqrt(144)+7 = 19. Example 3: (23-8)x4 = 60. Example 4: 2^5+10 = 42. Example 5: 17^2 = 289."""

base_q = "Compute the Eisenstein integer norm for z = a + bw where w = e^(2pi*i/3). The norm is |z|^2 = a^2 - ab + b^2. Compute for z = ({a}, {b})."
cell_names = {"A":"Baseline","B":"Tier1-Fewshot","C":"Generic-Fewshot","D":"Self-Scaffold"}

def make_prompt(cell, a, b):
    q = base_q.format(a=a, b=b)
    if cell == "A":
        return [{"role":"user","content":q}]
    elif cell == "B":
        return [{"role":"system","content":f"Math assistant. Examples:\n\n{tier1_exemplars}"},{"role":"user","content":q}]
    elif cell == "C":
        return [{"role":"system","content":f"Math assistant. Solve step by step:\n\n{generic_exemplars}"},{"role":"user","content":q}]
    elif cell == "D":
        return [{"role":"user","content":q+"\n\nShow step-by-step: identify a,b, compute a^2, -ab, b^2, sum them."}]

outdir = os.path.dirname(os.path.abspath(__file__))
results_file = os.path.join(outdir, "study51_results.json")
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
    print(" OK" if correct else f" WRONG(exp={expected})")
    return correct

# === phi4-mini: run with small context to avoid OOM ===
print("\n=== phi4-mini (compact prompts) ===")
import subprocess
subprocess.run(["ollama","keep-alive","0m"], capture_output=True)
time.sleep(3)

for cell in ["A","B","C","D"]:
    for a,b,exp in test_problems:
        if done("phi4-mini", cell, [a,b]):
            print(f"  phi4-mini Cell {cell} ({a},{b}) SKIP")
            continue
        sys.stdout.write(f"  phi4-mini Cell {cell} ({a},{b})...")
        sys.stdout.flush()
        try:
            r = requests.post(OLLAMA, json={
                "model":"phi4-mini:latest","messages":make_prompt(cell,a,b),
                "stream":False,"options":{"temperature":0.3,"num_ctx":1024}
            }, timeout=180)
            resp = r.json()["message"]["content"]
            add_result("phi4-mini","ollama:phi4-mini:latest",cell,a,b,exp,resp)
        except Exception as e:
            add_result("phi4-mini","ollama:phi4-mini:latest",cell,a,b,exp,f"ERROR:{e}",str(e))
        save()
        time.sleep(1)

subprocess.run(["ollama","keep-alive","0m"], capture_output=True)
time.sleep(3)

# === DeepInfra models ===
for dmodel, dlabel in [("NousResearch/Hermes-3-Llama-3.1-70B","Hermes-70B"),("Qwen/Qwen3-235B-A22B-Instruct-2507","Qwen3-235B")]:
    print(f"\n=== {dlabel} (DeepInfra) ===")
    for cell in ["A","B","C","D"]:
        for a,b,exp in test_problems:
            if done(dlabel, cell, [a,b]):
                print(f"  {dlabel} Cell {cell} ({a},{b}) SKIP")
                continue
            sys.stdout.write(f"  {dlabel} Cell {cell} ({a},{b})...")
            sys.stdout.flush()
            try:
                r = requests.post(DI_URL, headers={"Authorization":f"Bearer {DEEPINFRA_KEY}"}, json={
                    "model":dmodel,"messages":make_prompt(cell,a,b),"temperature":0.3,"max_tokens":512
                }, timeout=120)
                resp = r.json()["choices"][0]["message"]["content"]
                add_result(dlabel,dmodel,cell,a,b,exp,resp)
            except Exception as e:
                add_result(dlabel,dmodel,cell,a,b,exp,f"ERROR:{e}",str(e))
            save()
            time.sleep(1)

# === ANALYSIS ===
print("\n" + "="*60)
print("RESULTS SUMMARY")
print("="*60)

all_labels = ["qwen3:4b","phi4-mini","Hermes-70B","Qwen3-235B"]
for ml in all_labels:
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

a_pct = sum(1 for r in results if r["cell"]=="A" and r["correct"])/max(1,sum(1 for r in results if r["cell"]=="A"))*100
b_pct = sum(1 for r in results if r["cell"]=="B" and r["correct"])/max(1,sum(1 for r in results if r["cell"]=="B"))*100
d_pct = sum(1 for r in results if r["cell"]=="D" and r["correct"])/max(1,sum(1 for r in results if r["cell"]=="D"))*100

print(f"\nKEY FINDING:")
if b_pct > a_pct + 10:
    print(f"  Cell B ({b_pct:.0f}%) >> Cell A ({a_pct:.0f}%) — Tier 1 IS transferable!")
elif b_pct > a_pct:
    print(f"  Cell B ({b_pct:.0f}%) > Cell A ({a_pct:.0f}%) — Partially transferable")
else:
    print(f"  Cell B ({b_pct:.0f}%) <= Cell A ({a_pct:.0f}%) — NOT transferable")

if d_pct > b_pct + 5:
    print(f"  Cell D ({d_pct:.0f}%) > Cell B ({b_pct:.0f}%) — Self-scaffold wins")
elif b_pct > d_pct + 5:
    print(f"  Cell B ({b_pct:.0f}%) > Cell D ({d_pct:.0f}%) — Few-shot wins")
else:
    print(f"  Cell D ({d_pct:.0f}%) ~ Cell B ({b_pct:.0f}%) — Comparable")

print(f"\nDone. {len(results)} total results.")
